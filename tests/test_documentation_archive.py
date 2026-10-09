"""Public documentation archives preserve committed-source bytes across checkouts."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from research.evidence.render_documentation_archive import render_reading_copy

ROOT = Path(__file__).resolve().parents[1]
COMPLETE_SNAPSHOT = '2026-10-09-pre-refresh-e9d71b8'
PUBLICATION_PARENT = 'da4f55e48a368f59ed68ee4427013a83b5c06070'
PARENT_SNAPSHOT = '2026-10-09-publication-parent-da4f55e'
ENTRY_POINTS = frozenset({'README.md', 'docs/knowledge/current-findings.md',
                          'docs/overview/gap-closure-ledger.md'})
# Independent of archive manifests/catalogue: changing preserved scope requires review.
# None means the full Markdown inventory at the pinned revision, obtained from Git.
EXPECTED_SNAPSHOTS: dict[str, tuple[str, frozenset[str] | None]] = {
    '2026-10-01-initial-5a42286': ('5a4228690106469944510d19e0bd1331388dd008', frozenset({'README.md'})),
    '2026-10-03-quarantine-and-scan-fdcc22f': ('fdcc22f80ad173a2f4f2844c0f6b666794fda54a', frozenset({'README.md'})),
    '2026-10-06-complete-event-d1055a1': ('d1055a1078456a5ef9e98fcee476d68ac6db38fb', ENTRY_POINTS),
    '2026-10-08-persistent-baseline-02459e7': ('02459e780f9912b31c2ece951cf824d941972156', ENTRY_POINTS),
    '2026-10-08-integrated-review-1fc9bed': ('1fc9bed58df4abd6fc28ae883670d05adff47cd0', ENTRY_POINTS),
    COMPLETE_SNAPSHOT: ('e9d71b84365122ff2640e240b20fc1dbb834388a', None),
    PARENT_SNAPSHOT: (PUBLICATION_PARENT, frozenset({
        'README.md', 'docs/knowledge/reference-index.md',
        'docs/knowledge/workflow-diagrams.md', 'docs/overview/archify-studio/README.md'})),
}
FIXTURE_SNAPSHOT = '2026-10-06-complete-event-d1055a1'


class DocumentationArchiveTests(unittest.TestCase):
    def archive_file(self, folder: Path, relative: str) -> Path:
        self.assertIsInstance(relative, str, 'Invalid archive path')
        self.assertTrue(relative and '\\' not in relative and ':' not in relative
                        and all(part not in ('', '.', '..') for part in relative.split('/')),
                        'Invalid archive path')
        path = (folder/relative).resolve()
        self.assertTrue(path.is_relative_to(folder.resolve()), 'Archive path escapes containment')
        self.assertEqual(path, folder.resolve()/relative, 'Archive path aliases another location')
        return path

    def git_source(self, *arguments: str) -> bytes:
        result = subprocess.run(['git', *arguments], cwd=ROOT, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0,
                         'Git source unavailable or invalid. Use a full-history checkout '
                         '(CI fetch-depth: 0); no network fetch is performed by this test. '
                         + result.stderr.decode('utf-8', errors='replace'))
        return result.stdout

    def git_objects(self, revision: str) -> dict[str, str]:
        entries = self.git_source('ls-tree', '-r', '-t', '-z', revision).split(b'\0')
        return {entry.split(b'\t', 1)[1].decode('utf-8'): entry.split(b' ', 2)[1].decode('ascii')
                for entry in entries if entry}

    def verify_snapshot(self, manifest: Path) -> None:
        name = manifest.parent.name
        self.assertIn(name, EXPECTED_SNAPSHOTS, 'Unexpected snapshot directory')
        expected_revision, selected_sources = EXPECTED_SNAPSHOTS[name]
        self.assertTrue(expected_revision.startswith(name.rsplit('-', 1)[-1]),
                        'Snapshot directory suffix differs from its pinned revision')
        data = json.loads(manifest.read_text(encoding='utf-8'))
        self.assertEqual(data['source_kind'], 'git-blob')
        self.assertRegex(data['source_revision'], r'^[0-9a-f]{40}$')
        revision = data['source_revision']
        self.assertEqual(self.git_source('cat-file', '-t', revision).strip(), b'commit')
        self.assertEqual(revision, expected_revision, 'Snapshot recorded revision differs from its pinned identity')
        self.assertTrue(data['files'], 'Snapshot manifest must contain source files')
        source_paths = [row['source_path'] for row in data['files']]
        self.assertEqual(len(source_paths), len(set(source_paths)), 'Duplicate source paths')
        if selected_sources is None:
            inventory = self.git_source('ls-tree', '-r', '-z', '--name-only', revision).decode('utf-8')
            markdown = {path for path in inventory.split('\0') if path.endswith('.md')}
            self.assertEqual(set(source_paths), markdown, 'Complete snapshot Markdown inventory differs from Git')
        else:
            self.assertEqual(set(source_paths), selected_sources, 'Milestone source inventory differs from its pinned scope')
        storage_paths = []
        for row in data['files']:
            stem = row['source_path'].replace('/', '__')
            expected_paths = (f'originals/{stem}.txt', f'pages/{stem}')
            actual_paths = (row['original_path'], row['reading_path'])
            self.assertEqual(actual_paths, expected_paths, 'Canonical archive storage paths are required')
            storage_paths.extend(actual_paths)
        self.assertEqual(len(storage_paths), len({path.casefold() for path in storage_paths}),
                         'Duplicate archive storage paths')
        expected_files = {'manifest.json', 'README.md'}
        objects = self.git_objects(revision)
        for row in data['files']:
            self.assertEqual(row['source_commit'], data['source_revision'])
            self.assertIsNone(row.get('local_base_commit'))
            expected = self.git_source('show', f'{revision}:{row["source_path"]}')
            for field, digest in [('original_path', 'original_sha256'), ('reading_path', 'reading_sha256')]:
                expected_files.add(row[field])
                path = self.archive_file(manifest.parent, row[field])
                raw = path.read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), row[digest])
                if field == 'original_path':
                    self.assertEqual(len(raw), row['original_bytes'])
                    self.assertEqual(raw, expected, f'Archived original differs from Git blob: {row["source_path"]}')
                else:
                    self.assertEqual(raw, render_reading_copy(row['source_path'], revision, expected, objects),
                                     f'Readable copy differs from Git-source transformation: {row["source_path"]}')
        actual_files = {path.relative_to(manifest.parent).as_posix()
                        for path in manifest.parent.rglob('*') if path.is_file()}
        self.assertEqual(actual_files, expected_files, 'Unmanifested or missing archive files')

    def verify_archive(self, archive: Path) -> None:
        manifests = sorted(archive.glob('*/manifest.json'))
        self.assertIn(archive/COMPLETE_SNAPSHOT/'manifest.json', manifests,
                      'Required complete snapshot is missing')
        self.assertEqual({manifest.parent.name for manifest in manifests}, set(EXPECTED_SNAPSHOTS),
                         'Expected snapshot set differs from recorded directories')
        catalogue = (archive/'README.md').read_text(encoding='utf-8')
        entries = re.findall(r'\]\((\d{4}-\d{2}-\d{2}-[^/()]+)/README\.md\)', catalogue)
        self.assertEqual(len(entries), len(set(entries)), 'Archive catalogue contains duplicate snapshots')
        self.assertEqual(set(entries), set(EXPECTED_SNAPSHOTS), 'Archive catalogue differs from pinned snapshots')
        expected_files = {archive/'README.md'}
        for manifest in manifests:
            self.verify_snapshot(manifest)
            expected_files.update(path for path in manifest.parent.rglob('*') if path.is_file())
        self.assertEqual({path for path in archive.rglob('*') if path.is_file()}, expected_files,
                         'Unmanifested archive files outside recorded snapshots')

    def fixture(self, folder: Path, *, complete: bool = False,
                snapshot_name: str | None = None) -> Path:
        if snapshot_name is None:
            snapshot_name = COMPLETE_SNAPSHOT if complete else FIXTURE_SNAPSHOT
        source = self.archive_file(ROOT/'archive', snapshot_name)
        self.assertTrue(source.resolve().is_relative_to(ROOT.resolve()), 'Archive source escapes containment')
        snapshot = self.archive_file(folder, snapshot_name)
        data = json.loads((source/'manifest.json').read_text(encoding='utf-8'))
        copies = [(self.archive_file(source, 'README.md'), self.archive_file(snapshot, 'README.md'))]
        for row in data['files']:
            for field in ('original_path', 'reading_path'):
                copies.append((self.archive_file(source, row[field]), self.archive_file(snapshot, row[field])))
        # Validate every source and destination before any directory or file write.
        snapshot.mkdir()
        for original, target in copies:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(original, target)
        manifest = snapshot/'manifest.json'
        manifest.write_text(json.dumps(data), encoding='utf-8')
        return manifest

    def archive_fixture(self, folder: Path) -> Path:
        archive = folder/'archive'
        archive.mkdir()
        shutil.copyfile(self.archive_file(ROOT/'archive', 'README.md'), archive/'README.md')
        for source in sorted((ROOT/'archive').glob('*/manifest.json')):
            self.fixture(archive, complete=True, snapshot_name=source.parent.name)
        return archive

    def test_public_snapshots_exclude_uncommitted_private_reports_and_match_hashes(self):
        self.verify_archive(ROOT/'archive')

    def test_changed_original_with_recomputed_manifest_hash_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = self.fixture(Path(directory))
            data = json.loads(manifest.read_text(encoding='utf-8'))
            row = data['files'][0]
            path = self.archive_file(manifest.parent, row['original_path'])
            changed = path.read_bytes() + b'\nUncommitted replacement text.\n'
            path.write_bytes(changed)
            row['original_sha256'] = hashlib.sha256(changed).hexdigest()
            row['original_bytes'] = len(changed)
            manifest.write_text(json.dumps(data), encoding='utf-8')
            with self.assertRaisesRegex(AssertionError, 'Git blob'):
                self.verify_snapshot(manifest)

    def test_nonexistent_source_revision_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = self.fixture(Path(directory))
            data = json.loads(manifest.read_text(encoding='utf-8'))
            data['source_revision'] = '0'*40
            for row in data['files']:
                row['source_commit'] = data['source_revision']
            manifest.write_text(json.dumps(data), encoding='utf-8')
            with self.assertRaisesRegex(AssertionError, 'Git source unavailable'):
                self.verify_snapshot(manifest)

    def test_complete_snapshot_cannot_drop_a_document_and_its_files(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = self.fixture(Path(directory), complete=True)
            data = json.loads(manifest.read_text(encoding='utf-8'))
            removed = data['files'].pop()
            paths = [self.archive_file(manifest.parent, removed[field])
                     for field in ('original_path', 'reading_path')]
            for path in paths:
                path.unlink()
            manifest.write_text(json.dumps(data), encoding='utf-8')
            with self.assertRaisesRegex(AssertionError, 'Markdown inventory'):
                self.verify_snapshot(manifest)

    def test_unmanifested_archive_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = self.fixture(Path(directory))
            (manifest.parent/'originals'/'unexpected.txt').write_bytes(b'unmanifested')
            with self.assertRaisesRegex(AssertionError, 'Unmanifested or missing archive files'):
                self.verify_snapshot(manifest)

    def test_unmanifested_directory_is_not_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = self.archive_fixture(Path(directory))
            (folder/'unrecorded').mkdir()
            (folder/'unrecorded'/'report.md').write_bytes(b'Not in a snapshot')
            with self.assertRaisesRegex(AssertionError, 'Unmanifested archive files outside'):
                self.verify_archive(folder)

    def test_complete_snapshot_cannot_be_removed_entirely(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            self.fixture(folder, snapshot_name='2026-10-01-initial-5a42286')
            shutil.copyfile(ROOT/'archive'/'README.md', folder/'README.md')
            with self.assertRaisesRegex(AssertionError, 'Required complete snapshot is missing'):
                self.verify_archive(folder)

    def test_selective_milestone_and_catalogue_row_cannot_disappear(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            archive = self.archive_fixture(folder)
            name = '2026-10-01-initial-5a42286'
            source = self.archive_file(archive, name)
            destination = self.archive_file(folder, 'withdrawn-milestone')
            self.assertFalse(destination.exists())
            source.rename(destination)
            readme = archive/'README.md'
            readme.write_text('\n'.join(line for line in readme.read_text(encoding='utf-8').splitlines()
                                        if f'({name}/README.md)' not in line)+'\n', encoding='utf-8')
            with self.assertRaisesRegex(AssertionError, 'Expected snapshot set'):
                self.verify_archive(archive)

    def test_selective_milestone_cannot_drop_one_selected_document(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = self.archive_fixture(Path(directory))
            manifest = archive/'2026-10-06-complete-event-d1055a1'/'manifest.json'
            data = json.loads(manifest.read_text(encoding='utf-8'))
            removed = data['files'].pop()
            paths = [self.archive_file(manifest.parent, removed[field])
                     for field in ('original_path', 'reading_path')]
            for path in paths:
                path.unlink()
            manifest.write_text(json.dumps(data), encoding='utf-8')
            with self.assertRaisesRegex(AssertionError, 'Milestone source inventory'):
                self.verify_archive(archive)

    def test_catalogue_cannot_omit_a_retained_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = self.archive_fixture(Path(directory))
            readme = archive/'README.md'
            readme.write_text('\n'.join(line for line in readme.read_text(encoding='utf-8').splitlines()
                                        if '(2026-10-01-initial-5a42286/README.md)' not in line)+'\n',
                              encoding='utf-8')
            with self.assertRaisesRegex(AssertionError, 'Archive catalogue'):
                self.verify_archive(archive)

    def test_readable_copy_cannot_alias_the_exact_original(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = self.fixture(Path(directory))
            data = json.loads(manifest.read_text(encoding='utf-8'))
            row = data['files'][0]
            self.archive_file(manifest.parent, row['reading_path']).unlink()
            row['reading_path'] = row['original_path']
            row['reading_sha256'] = row['original_sha256']
            manifest.write_text(json.dumps(data), encoding='utf-8')
            with self.assertRaisesRegex(AssertionError, 'Canonical archive storage paths'):
                self.verify_snapshot(manifest)

    def test_readable_copy_cannot_reuse_another_rows_file(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = self.fixture(Path(directory))
            data = json.loads(manifest.read_text(encoding='utf-8'))
            first, second = data['files'][:2]
            self.archive_file(manifest.parent, second['reading_path']).unlink()
            second['reading_path'] = first['reading_path']
            second['reading_sha256'] = first['reading_sha256']
            manifest.write_text(json.dumps(data), encoding='utf-8')
            with self.assertRaisesRegex(AssertionError, 'Canonical archive storage paths'):
                self.verify_snapshot(manifest)

    def test_storage_namespaces_cannot_be_swapped(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = self.fixture(Path(directory))
            data = json.loads(manifest.read_text(encoding='utf-8'))
            row = data['files'][0]
            original = self.archive_file(manifest.parent, row['original_path'])
            reading = self.archive_file(manifest.parent, row['reading_path'])
            original_bytes, reading_bytes = original.read_bytes(), reading.read_bytes()
            original.write_bytes(reading_bytes)
            reading.write_bytes(original_bytes)
            row['original_path'], row['reading_path'] = row['reading_path'], row['original_path']
            manifest.write_text(json.dumps(data), encoding='utf-8')
            with self.assertRaisesRegex(AssertionError, 'Canonical archive storage paths'):
                self.verify_snapshot(manifest)

    def test_snapshot_cannot_be_replaced_by_a_different_valid_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = self.fixture(Path(directory), complete=True)
            data = json.loads(manifest.read_text(encoding='utf-8'))
            replacement = self.git_source('rev-parse', 'e2798bd^{commit}').decode().strip()
            data['source_revision'] = replacement
            for row in data['files']:
                raw = self.git_source('show', f'{replacement}:{row["source_path"]}')
                self.archive_file(manifest.parent, row['original_path']).write_bytes(raw)
                row['source_commit'] = replacement
                row['original_sha256'] = hashlib.sha256(raw).hexdigest()
                row['original_bytes'] = len(raw)
            manifest.write_text(json.dumps(data), encoding='utf-8')
            with self.assertRaisesRegex(AssertionError, 'recorded revision'):
                self.verify_snapshot(manifest)

    def test_changed_reading_copy_with_recomputed_hash_is_rejected(self):
        for change in ('warning', 'link'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                manifest = self.fixture(Path(directory))
                data = json.loads(manifest.read_text(encoding='utf-8'))
                row = data['files'][0]
                path = self.archive_file(manifest.parent, row['reading_path'])
                original = path.read_text(encoding='utf-8')
                if change == 'warning':
                    changed = original.replace('**Archive — not current operating instructions.**', 'Current instructions', 1)
                else:
                    changed = original.replace(f'/blob/{data["source_revision"]}/', '/blob/'+'0'*40+'/', 1)
                self.assertNotEqual(changed, original)
                raw = changed.encode('utf-8')
                path.write_bytes(raw)
                row['reading_sha256'] = hashlib.sha256(raw).hexdigest()
                manifest.write_text(json.dumps(data), encoding='utf-8')
                with self.assertRaisesRegex(AssertionError, 'Readable copy differs'):
                    self.verify_snapshot(manifest)

    def test_actual_publication_parent_markdown_can_be_restored(self):
        archive = ROOT/'archive'
        overlay = {}
        for name in (COMPLETE_SNAPSHOT, PARENT_SNAPSHOT):
            manifest = archive/name/'manifest.json'
            if manifest.exists():
                data = json.loads(manifest.read_text(encoding='utf-8'))
                overlay.update({row['source_path']: self.archive_file(manifest.parent, row['original_path'])
                                for row in data['files']})
        inventory = self.git_source('ls-tree', '-r', '-z', '--name-only', PUBLICATION_PARENT).decode('utf-8')
        markdown = {path for path in inventory.split('\0') if path.endswith('.md')}
        self.assertEqual(set(overlay), markdown, 'Publication-parent Markdown inventory is incomplete')
        for source_path, original in overlay.items():
            self.assertEqual(original.read_bytes(), self.git_source('show', f'{PUBLICATION_PARENT}:{source_path}'),
                             f'Publication-parent original differs: {source_path}')

    def test_reading_transform_handles_multiline_links_images_and_directories(self):
        revision = EXPECTED_SNAPSHOTS[COMPLETE_SNAPSHOT][0]
        original = (b'# Guide\r\n\r\n[Two\r\nlines](../README.md#part)\r\n'
                    b'[![Preview](images/pic.svg)](../research/)\r\n'
                    b'[Local](#part) [External](https://example.test/reference)\r\n')
        objects = {'docs/guide.md':'blob', 'README.md':'blob', 'docs/images/pic.svg':'blob', 'research':'tree'}
        rendered = render_reading_copy('docs/guide.md', revision, original, objects).decode('utf-8')
        self.assertIn('Archive — not current operating instructions.', rendered)
        self.assertIn(f'/blob/{revision}/README.md#part)', rendered)
        self.assertIn(f'/blob/{revision}/docs/images/pic.svg)', rendered)
        self.assertIn(f'/tree/{revision}/research)', rendered)
        self.assertIn('[Local](#part) [External](https://example.test/reference)', rendered)
        self.assertNotIn('\r', rendered)
        with self.assertRaisesRegex(ValueError, 'absent from pinned Git tree'):
            render_reading_copy('docs/guide.md', revision, b'# Guide\n\n[Missing](missing.md)\n', objects)

    def test_fixture_rejects_unsafe_paths_before_any_writes(self):
        original = json.loads((ROOT/'archive'/COMPLETE_SNAPSHOT/'manifest.json').read_text(encoding='utf-8'))
        for field in ('original_path', 'reading_path'):
            for invalid in ('../../README.md', '/outside.md', 'C:/outside.md',
                            '..\\outside.md', 'originals/../README.md', '//server/share/file.md'):
                with self.subTest(field=field, path=invalid), tempfile.TemporaryDirectory() as directory:
                    data = json.loads(json.dumps(original))
                    data['files'][0][field] = invalid
                    with patch.object(Path, 'read_text', return_value=json.dumps(data)), \
                         patch.object(Path, 'mkdir') as mkdir, \
                         patch.object(shutil, 'copyfile') as copy, \
                         patch.object(Path, 'write_text') as write:
                        with self.assertRaisesRegex(AssertionError, 'archive path'):
                            self.fixture(Path(directory))
                        mkdir.assert_not_called()
                        copy.assert_not_called()
                        write.assert_not_called()

    def test_contained_path_alias_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory).resolve()
            requested = folder/'pages'/'README.md'
            target = folder/'originals'/'README.md.txt'
            resolve = Path.resolve
            def alias(path: Path, *args, **kwargs):
                return target if path == requested else resolve(path, *args, **kwargs)
            with patch.object(Path, 'resolve', alias), self.assertRaisesRegex(AssertionError, 'aliases another location'):
                self.archive_file(folder, 'pages/README.md')

    def test_originals_are_not_subject_to_git_newline_conversion(self):
        paths = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT/'archive').glob('*/originals/*'))
        self.assertTrue(paths)
        result = subprocess.run(['git','check-attr','--stdin','text'], input='\n'.join(paths)+'\n',
                                cwd=ROOT, capture_output=True, text=True, timeout=20, check=True)
        self.assertEqual(len(result.stdout.splitlines()), len(paths))
        self.assertTrue(all(line.endswith(': text: unset') for line in result.stdout.splitlines()))


if __name__ == '__main__':
    unittest.main()
