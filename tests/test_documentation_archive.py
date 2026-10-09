"""Public documentation archives preserve committed-source bytes across checkouts."""
import hashlib
import json
from pathlib import Path
import posixpath
import re
import shutil
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from research.evidence.render_documentation_archive import parse_manifest, render_reading_copy, render_snapshot_index

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
# Reviewed prose is pinned independently of the archive's own metadata.
ARCHIVE_CATALOGUE_SHA256 = 'e885b273d376d52b6bc8e0830b0d702b603058c2010301d314d6c766a2a037f9'


class DocumentationArchiveTests(unittest.TestCase):
    def archive_inventory(self, folder: Path) -> tuple[set[str], set[str]]:
        files: set[str] = set()
        directories: set[str] = set()
        def visit(path: Path) -> None:
            info = path.lstat()
            self.assertFalse(stat.S_ISLNK(info.st_mode) or
                             getattr(info, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400),
                             'Archive link or non-regular entry')
            if stat.S_ISDIR(info.st_mode):
                if path != folder:
                    directories.add(path.relative_to(folder).as_posix())
                for child in sorted(path.iterdir()):
                    visit(child)
            elif stat.S_ISREG(info.st_mode) and path != folder:
                files.add(path.relative_to(folder).as_posix())
            else:
                self.fail('Archive link or non-regular entry')
        visit(folder)
        return files, directories

    def expected_directories(self, files: set[str]) -> set[str]:
        return {parent.as_posix() for file in files for parent in Path(file).parents if parent != Path('.')}

    def manifest_data(self, path: Path) -> dict:
        return parse_manifest(self.archive_file(path.parent, path.name).read_text(encoding='utf-8'))

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
        actual_files, actual_directories = self.archive_inventory(manifest.parent)
        name = manifest.parent.name
        self.assertIn(name, EXPECTED_SNAPSHOTS, 'Unexpected snapshot directory')
        expected_revision, selected_sources = EXPECTED_SNAPSHOTS[name]
        self.assertTrue(expected_revision.startswith(name.rsplit('-', 1)[-1]),
                        'Snapshot directory suffix differs from its pinned revision')
        data = self.manifest_data(manifest)
        self.assertEqual(data['schema'], 'wht/documentation-archive-v1')
        self.assertEqual(data['captured_date'], '2026-10-09')
        self.assertEqual(data['timezone'], 'America/New_York')
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
            self.assertEqual(row['last_change'], self.git_source(
                'log', '-1', '--format=%H%x09%cI', revision, '--', row['source_path']).decode('utf-8').strip(),
                'Recorded last-change history differs from Git')
            self.assertIsNone(row.get('local_base_commit'))
            expected = self.git_source('show', f'{revision}:{row["source_path"]}')
            for field, digest in [('original_path', 'original_sha256'), ('reading_path', 'reading_sha256')]:
                expected_files.add(row[field])
                path = self.archive_file(manifest.parent, row[field])
                raw = path.read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), row[digest])
                if field == 'original_path':
                    self.assertIs(type(row['original_bytes']), int, 'Original byte length must be an integer')
                    self.assertEqual(len(raw), row['original_bytes'])
                    self.assertEqual(raw, expected, f'Archived original differs from Git blob: {row["source_path"]}')
                else:
                    self.assertEqual(raw, render_reading_copy(row['source_path'], revision, expected, objects),
                                     f'Readable copy differs from Git-source transformation: {row["source_path"]}')
        self.assertEqual(actual_files, expected_files, 'Unmanifested or missing archive files')
        self.assertEqual(actual_directories, self.expected_directories(expected_files),
                         'Unmanifested or missing archive directories')
        self.assertEqual((manifest.parent/'README.md').read_bytes(), render_snapshot_index(name, data),
                         'Snapshot index differs from its complete manifest-derived rendering')

    def verify_archive(self, archive: Path) -> None:
        actual_files, actual_directories = self.archive_inventory(archive)
        manifests = sorted(archive/path for path in actual_files
                           if path.count('/') == 1 and path.endswith('/manifest.json'))
        self.assertIn(archive/COMPLETE_SNAPSHOT/'manifest.json', manifests,
                      'Required complete snapshot is missing')
        self.assertEqual({manifest.parent.name for manifest in manifests}, set(EXPECTED_SNAPSHOTS),
                         'Expected snapshot set differs from recorded directories')
        catalogue = (archive/'README.md').read_text(encoding='utf-8')
        entries = re.findall(r'\]\((\d{4}-\d{2}-\d{2}-[^/()]+)/README\.md\)', catalogue)
        self.assertEqual(len(entries), len(set(entries)), 'Archive catalogue contains duplicate snapshots')
        self.assertEqual(set(entries), set(EXPECTED_SNAPSHOTS), 'Archive catalogue differs from pinned snapshots')
        self.assertEqual(hashlib.sha256(catalogue.encode('utf-8')).hexdigest(), ARCHIVE_CATALOGUE_SHA256,
                         'Archive catalogue differs from reviewed content')
        expected_files = {'README.md'}
        for manifest in manifests:
            self.verify_snapshot(manifest)
            files, _ = self.archive_inventory(manifest.parent)
            expected_files.update(manifest.parent.name+'/'+path for path in files)
        self.assertEqual(actual_files, expected_files,
                         'Unmanifested archive files outside recorded snapshots')
        self.assertEqual(actual_directories, self.expected_directories(expected_files),
                         'Unmanifested archive directories outside recorded snapshots')

    def fixture(self, folder: Path, *, complete: bool = False,
                snapshot_name: str | None = None) -> Path:
        self.archive_inventory(ROOT/'archive')
        if snapshot_name is None:
            snapshot_name = COMPLETE_SNAPSHOT if complete else FIXTURE_SNAPSHOT
        source = self.archive_file(ROOT/'archive', snapshot_name)
        self.assertTrue(source.resolve().is_relative_to(ROOT.resolve()), 'Archive source escapes containment')
        snapshot = self.archive_file(folder, snapshot_name)
        data = self.manifest_data(source/'manifest.json')
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
        self.archive_inventory(ROOT/'archive')
        archive = folder/'archive'
        archive.mkdir()
        shutil.copyfile(self.archive_file(ROOT/'archive', 'README.md'), archive/'README.md')
        for source in sorted((ROOT/'archive').glob('*/manifest.json')):
            self.fixture(archive, complete=True, snapshot_name=source.parent.name)
        return archive

    def test_public_snapshots_exclude_uncommitted_private_reports_and_match_hashes(self):
        self.verify_archive(ROOT/'archive')

    def test_last_change_revision_and_timestamp_are_verified(self):
        for value in ('0'*40+'\t2026-10-01T23:18:25-04:00',
                      '5a4228690106469944510d19e0bd1331388dd008\t2000-01-01T00:00:00Z'):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as directory:
                manifest = self.fixture(Path(directory), snapshot_name='2026-10-01-initial-5a42286')
                data = self.manifest_data(manifest)
                data['files'][0]['last_change'] = value
                manifest.write_text(json.dumps(data), encoding='utf-8')
                with self.assertRaisesRegex(AssertionError, 'last-change history'):
                    self.verify_snapshot(manifest)

    def test_catalogue_cannot_discard_its_guidance(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = self.archive_fixture(Path(directory))
            (archive/'README.md').write_text('\n'.join(
                f'[x]({name}/README.md)' for name in EXPECTED_SNAPSHOTS)+'\n', encoding='utf-8')
            with self.assertRaisesRegex(AssertionError, 'catalogue differs from reviewed content'):
                self.verify_archive(archive)

    def verify_source_map(self, text: str) -> None:
        baseline = EXPECTED_SNAPSHOTS[COMPLETE_SNAPSHOT][0]
        inventory = self.git_source('ls-tree', '-r', '-z', '--name-only', baseline).decode('utf-8')
        expected = {posixpath.relpath(path, 'docs/research-history'): path
                    for path in inventory.split('\0') if path.endswith('.md')}
        # This authored catalogue uses canonical four-cell rows. Inspect all
        # pipe-bearing lines so indentation or omitted outer pipes cannot hide rows.
        rows = [line.strip() for line in text.splitlines() if '|' in line
                and line.strip() != '| Document | Disposition | Last baseline change | Previous version |'
                and line.strip() != '|---|---|---|---|']
        seen = []
        pattern = (r'\| \[[^\[\]\n|]+\]\(([^)]+)\) \| [^|\n]+ \| (\d{4}-\d{2}-\d{2}) / '
                   r'\[([0-9a-f]{7})\]\(https://github.com/Protonmatter/wifi-hardware-time/commit/([0-9a-f]{40})\) '
                   r'\| \[Archive\]\(([^)]+)\) \|')
        for line in rows:
            row = re.fullmatch(pattern, line)
            self.assertIsNotNone(row, 'Malformed source-map inventory row')
            current, date, short_revision, revision, previous = row.groups()
            self.assertIn(current, expected, 'Source-map current link is not a baseline document')
            path = expected[current]
            seen.append(path)
            self.assertEqual(previous, f'../../archive/{COMPLETE_SNAPSHOT}/pages/{path.replace("/", "__")}',
                             'Source-map previous link differs from baseline archive')
            change, timestamp = self.git_source('log', '-1', '--format=%H%x09%cI', baseline, '--', path).decode().strip().split('\t')
            self.assertEqual((revision, short_revision, date), (change, change[:7], timestamp[:10]),
                             'Source-map history differs from Git')
        self.assertEqual(len(seen), len(set(seen)), 'Duplicate source-map document')
        self.assertEqual(set(seen), set(expected.values()), 'Source-map Markdown inventory differs from Git')

    def test_source_map_covers_every_baseline_document_once(self):
        self.verify_source_map((ROOT/'docs/research-history/source-map.md').read_text(encoding='utf-8'))

    def test_source_map_rejects_missing_duplicate_and_wrong_links(self):
        text = (ROOT/'docs/research-history/source-map.md').read_text(encoding='utf-8')
        row = next(line for line in text.splitlines() if line.startswith('| [Wi-Fi Hardware Time]'))
        changes = {
            'missing': text.replace(row+'\n', '', 1),
            'duplicate': text.replace(row, row+'\n'+row, 1),
            'indented-duplicate': text.replace(row, row+'\n '+row, 1),
            'missing-outer-pipe': text.replace(row, row+'\n'+row.lstrip('|'), 1),
            'wrong-current': text.replace('(../../README.md)', '(../../missing.md)', 1),
            'extra-link': text.replace('[Wi-Fi Hardware Time](../../README.md)',
                                       '[Wi-Fi Hardware Time](README.md) [Fallback](../../README.md)', 1),
            'wrong-previous': text.replace(f'({"../../archive/"+COMPLETE_SNAPSHOT}/pages/README.md)', '(README.md)', 1),
            'wrong-history': text.replace('/commit/e2798bd9244cf0b2d27f7bb5f9c0961146bc795f)', '/commit/'+'0'*40+')', 1),
        }
        for change, changed in changes.items():
            with self.subTest(change=change):
                self.assertNotEqual(changed, text)
                with self.assertRaises(AssertionError):
                    self.verify_source_map(changed)

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

    def verify_parent_overlay(self, archive: Path) -> None:
        self.archive_inventory(archive)
        overlay = {}
        for name in (COMPLETE_SNAPSHOT, PARENT_SNAPSHOT):
            manifest = archive/name/'manifest.json'
            if manifest.exists():
                data = self.manifest_data(manifest)
                overlay.update({row['source_path']: self.archive_file(manifest.parent, row['original_path'])
                                for row in data['files']})
        inventory = self.git_source('ls-tree', '-r', '-z', '--name-only', PUBLICATION_PARENT).decode('utf-8')
        markdown = {path for path in inventory.split('\0') if path.endswith('.md')}
        self.assertEqual(set(overlay), markdown, 'Publication-parent Markdown inventory is incomplete')
        for source_path, original in overlay.items():
            self.assertEqual(original.read_bytes(), self.git_source('show', f'{PUBLICATION_PARENT}:{source_path}'),
                             f'Publication-parent original differs: {source_path}')

    def test_actual_publication_parent_markdown_can_be_restored(self):
        self.verify_parent_overlay(ROOT/'archive')

    def test_parent_restore_rejects_nonregular_entries_before_reading(self):
        archive = ROOT/'archive'
        target = archive/COMPLETE_SNAPSHOT/'originals/docs__glossary.md.txt'
        original_lstat = Path.lstat
        def fifo_lstat(path: Path, *args, **kwargs):
            if path == target:
                return type('FifoStat', (), {'st_mode': stat.S_IFIFO})()
            return original_lstat(path, *args, **kwargs)
        with patch.object(Path, 'lstat', fifo_lstat), \
             patch.object(Path, 'read_text') as read_text, \
             patch.object(Path, 'read_bytes') as read_bytes:
            with self.assertRaisesRegex(AssertionError, 'Archive link or non-regular entry'):
                self.verify_parent_overlay(archive)
            read_text.assert_not_called()
            read_bytes.assert_not_called()

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

    def test_snapshot_index_cannot_be_truncated_or_redirected(self):
        for change in ('truncated', 'wrong-link'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                manifest = self.fixture(Path(directory))
                index = manifest.parent/'README.md'
                text = index.read_text(encoding='utf-8')
                changed = '# wrong\n' if change == 'truncated' else text.replace(
                    '(pages/README.md)', '(originals/README.md.txt)', 1)
                self.assertNotEqual(changed, text)
                index.write_text(changed, encoding='utf-8')
                with self.assertRaisesRegex(AssertionError, 'Snapshot index differs'):
                    self.verify_snapshot(manifest)

    def test_duplicate_manifest_keys_are_rejected(self):
        for key, discarded in (('source_revision', '"'+'0'*40+'"'), ('files', '[]'),
                               ('source_path', '"wrong.md"'), ('original_sha256', '"wrong"')):
            with self.subTest(key=key), tempfile.TemporaryDirectory() as directory:
                manifest = self.fixture(Path(directory))
                raw = manifest.read_text(encoding='utf-8')
                needle = json.dumps(key)+':'
                self.assertIn(needle, raw)
                manifest.write_text(raw.replace(needle, needle+discarded+','+needle, 1), encoding='utf-8')
                with self.assertRaisesRegex(ValueError, 'Duplicate JSON key'):
                    self.verify_snapshot(manifest)
        with self.assertRaisesRegex(ValueError, 'Duplicate JSON key'):
            parse_manifest('{"source_revision":"x","\\u0073ource_revision":"y"}')
        for raw in ('{"ignored":NaN}', '{"ignored":Infinity}'):
            with self.subTest(raw=raw), self.assertRaisesRegex(ValueError, 'Non-standard JSON constant'):
                parse_manifest(raw)

    def test_unmanifested_link_and_nonregular_entries_are_rejected(self):
        cases = ((stat.S_IFLNK, 0, False), (stat.S_IFLNK, 0, True),
                 (stat.S_IFDIR, 0x400, True), (stat.S_IFIFO, 0, False))
        for mode, attributes, directory_link in cases:
            with self.subTest(mode=mode, attributes=attributes), tempfile.TemporaryDirectory() as directory:
                archive = self.archive_fixture(Path(directory))
                link = archive/'unmanifested-link'
                if directory_link:
                    link.mkdir()
                else:
                    link.write_bytes(b'link fixture')
                original_lstat, original_is_file = Path.lstat, Path.is_file
                def link_lstat(path: Path, *args, **kwargs):
                    if path == link:
                        return type('LinkStat', (), {'st_mode':mode, 'st_file_attributes':attributes})()
                    return original_lstat(path, *args, **kwargs)
                def no_regular_file(path: Path, *args, **kwargs):
                    return False if path == link else original_is_file(path, *args, **kwargs)
                # Match is_file() semantics for dangling and directory symlinks,
                # without requiring a Windows symlink privilege in this unit test.
                with patch.object(Path, 'lstat', link_lstat), patch.object(Path, 'is_file', no_regular_file):
                    with self.assertRaisesRegex(AssertionError, 'Archive link or non-regular entry'):
                        self.verify_archive(archive)

    def test_unmanifested_empty_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = self.archive_fixture(Path(directory))
            (archive/'unrecorded-empty').mkdir()
            with self.assertRaisesRegex(AssertionError, 'Unmanifested archive directories outside'):
                self.verify_archive(archive)

    def test_fixture_rejects_unsafe_paths_before_any_writes(self):
        self.archive_inventory(ROOT/'archive')
        original = self.manifest_data(ROOT/'archive'/COMPLETE_SNAPSHOT/'manifest.json')
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
        self.archive_inventory(ROOT/'archive')
        paths = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT/'archive').glob('*/originals/*'))
        self.assertTrue(paths)
        result = subprocess.run(['git','check-attr','--stdin','text'], input='\n'.join(paths)+'\n',
                                cwd=ROOT, capture_output=True, text=True, timeout=20, check=True)
        self.assertEqual(len(result.stdout.splitlines()), len(paths))
        self.assertTrue(all(line.endswith(': text: unset') for line in result.stdout.splitlines()))


if __name__ == '__main__':
    unittest.main()
