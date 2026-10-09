"""Public documentation archives preserve committed-source bytes across checkouts."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
COMPLETE_SNAPSHOT = '2026-10-09-pre-refresh-e9d71b8'


class DocumentationArchiveTests(unittest.TestCase):
    def archive_file(self, folder: Path, relative: str) -> Path:
        self.assertIsInstance(relative, str, 'Invalid archive path')
        self.assertTrue(relative and '\\' not in relative and ':' not in relative
                        and all(part not in ('', '.', '..') for part in relative.split('/')),
                        'Invalid archive path')
        path = (folder/relative).resolve()
        self.assertTrue(path.is_relative_to(folder.resolve()), 'Archive path escapes containment')
        return path

    def git_source(self, *arguments: str) -> bytes:
        result = subprocess.run(['git', *arguments], cwd=ROOT, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0,
                         'Git source unavailable or invalid. Use a full-history checkout '
                         '(CI fetch-depth: 0); no network fetch is performed by this test. '
                         + result.stderr.decode('utf-8', errors='replace'))
        return result.stdout

    def verify_snapshot(self, manifest: Path, *, complete: bool = False) -> None:
        data = json.loads(manifest.read_text(encoding='utf-8'))
        self.assertEqual(data['source_kind'], 'git-blob')
        self.assertRegex(data['source_revision'], r'^[0-9a-f]{40}$')
        revision = data['source_revision']
        self.assertEqual(self.git_source('cat-file', '-t', revision).strip(), b'commit')
        self.assertTrue(data['files'], 'Snapshot manifest must contain source files')
        source_paths = [row['source_path'] for row in data['files']]
        self.assertEqual(len(source_paths), len(set(source_paths)), 'Duplicate source paths')
        if complete:
            inventory = self.git_source('ls-tree', '-r', '-z', '--name-only', revision).decode('utf-8')
            markdown = {path for path in inventory.split('\0') if path.endswith('.md')}
            self.assertEqual(set(source_paths), markdown, 'Complete snapshot Markdown inventory differs from Git')
        expected_files = {'manifest.json', 'README.md'}
        for row in data['files']:
            self.assertEqual(row['source_commit'], data['source_revision'])
            self.assertIsNone(row.get('local_base_commit'))
            for field, digest in [('original_path', 'original_sha256'), ('reading_path', 'reading_sha256')]:
                expected_files.add(row[field])
                path = self.archive_file(manifest.parent, row[field])
                raw = path.read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), row[digest])
                if field == 'original_path':
                    self.assertEqual(len(raw), row['original_bytes'])
                    expected = self.git_source('show', f'{revision}:{row["source_path"]}')
                    self.assertEqual(raw, expected, f'Archived original differs from Git blob: {row["source_path"]}')
        actual_files = {path.relative_to(manifest.parent).as_posix()
                        for path in manifest.parent.rglob('*') if path.is_file()}
        self.assertEqual(actual_files, expected_files, 'Unmanifested or missing archive files')

    def verify_archive(self, archive: Path) -> None:
        manifests = sorted(archive.glob('*/manifest.json'))
        self.assertIn(archive/COMPLETE_SNAPSHOT/'manifest.json', manifests,
                      'Required complete snapshot is missing')
        expected_files = {archive/'README.md'}
        for manifest in manifests:
            self.verify_snapshot(manifest, complete=manifest.parent.name == COMPLETE_SNAPSHOT)
            expected_files.update(path for path in manifest.parent.rglob('*') if path.is_file())
        self.assertEqual({path for path in archive.rglob('*') if path.is_file()}, expected_files,
                         'Unmanifested archive files outside recorded snapshots')

    def fixture(self, folder: Path, *, complete: bool = False) -> Path:
        source = ROOT/'archive'/COMPLETE_SNAPSHOT
        self.assertTrue(source.resolve().is_relative_to(ROOT.resolve()), 'Archive source escapes containment')
        snapshot = folder/'snapshot'
        data = json.loads((source/'manifest.json').read_text(encoding='utf-8'))
        if not complete:
            data['files'] = data['files'][:2]
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
                self.verify_snapshot(manifest, complete=True)

    def test_unmanifested_archive_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = self.fixture(Path(directory))
            (manifest.parent/'originals'/'unexpected.txt').write_bytes(b'unmanifested')
            with self.assertRaisesRegex(AssertionError, 'Unmanifested or missing archive files'):
                self.verify_snapshot(manifest)

    def test_unmanifested_directory_is_not_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            manifest = self.fixture(folder, complete=True)
            manifest.parent.rename(folder/COMPLETE_SNAPSHOT)
            (folder/'README.md').write_text('# Archive\n', encoding='utf-8')
            (folder/'unrecorded').mkdir()
            (folder/'unrecorded'/'report.md').write_bytes(b'Not in a snapshot')
            with self.assertRaisesRegex(AssertionError, 'Unmanifested archive files outside'):
                self.verify_archive(folder)

    def test_complete_snapshot_cannot_be_removed_entirely(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            self.fixture(folder)
            (folder/'README.md').write_text('# Archive\n', encoding='utf-8')
            with self.assertRaisesRegex(AssertionError, 'Required complete snapshot is missing'):
                self.verify_archive(folder)

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

    def test_originals_are_not_subject_to_git_newline_conversion(self):
        paths = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT/'archive').glob('*/originals/*'))
        self.assertTrue(paths)
        result = subprocess.run(['git','check-attr','--stdin','text'], input='\n'.join(paths)+'\n',
                                cwd=ROOT, capture_output=True, text=True, timeout=20, check=True)
        self.assertEqual(len(result.stdout.splitlines()), len(paths))
        self.assertTrue(all(line.endswith(': text: unset') for line in result.stdout.splitlines()))


if __name__ == '__main__':
    unittest.main()
