"""Scriptify preview/apply/repeat/failure checks using authored files only."""
import os
import json
import hashlib
import ctypes
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'research/adapters/Invoke-QualcommStaticInspection.ps1'


class ScriptCatalogTests(unittest.TestCase):
    def test_registered_entry_points_match_recorded_hashes(self):
        catalog=json.loads((ROOT/'catalog/scripts.json').read_text(encoding='utf-8-sig'))
        for item in catalog['scripts']:
            with self.subTest(script=item['path']):
                self.assertEqual(hashlib.sha256((ROOT/item['path']).read_bytes()).hexdigest(),
                                 item['sha256'].lower())


@unittest.skipUnless(os.name == 'nt' and shutil.which('pwsh'), 'Windows PowerShell 7.4+ required')
class StaticInspectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base / 'source'
        self.source.mkdir()
        (self.source / 'authored.txt').write_text('fixture', encoding='utf-8')
        self.output = self.base / 'result'

    def run_tool(self, *extra, operation='Files', source=None):
        return subprocess.run([shutil.which('pwsh'), '-NoProfile', '-File', str(SCRIPT),
                               '-Operation', operation, '-InputPath', str(source or self.source),
                               '-OutputDirectory', str(self.output), '-Python', sys.executable,
                               *extra], capture_output=True, text=True, timeout=40)

    def test_preview_is_nonmutating(self):
        result = self.run_tool()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('WouldInspect', result.stdout)
        self.assertFalse(self.output.exists())

    def test_apply_and_second_apply_converge(self):
        first = self.run_tool('-Apply')
        self.assertEqual(first.returncode, 0, first.stderr)
        before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns)
                  for p in self.output.iterdir()}
        second = self.run_tool('-Apply')
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertIn('Unchanged', second.stdout)
        self.assertEqual(before, {p.name: (p.read_bytes(), p.stat().st_mtime_ns)
                                 for p in self.output.iterdir()})

    def test_invalid_hash_fails_before_mutation(self):
        result = self.run_tool('-ExpectedSha256', '0' * 64,
                               source=self.source / 'authored.txt')
        self.assertEqual(result.returncode, 1)
        self.assertFalse(self.output.exists())

    def test_whatif_does_not_mutate(self):
        result = self.run_tool('-Apply', '-WhatIf')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.output.exists())

    def test_changed_output_is_not_accepted_as_unchanged(self):
        self.assertEqual(self.run_tool('-Apply').returncode, 0)
        (self.output / 'result.json').write_text('{}')
        result = self.run_tool('-Apply')
        self.assertEqual(result.returncode, 1)
        self.assertEqual((self.output / 'result.json').read_text(), '{}')

    def test_worker_failure_is_not_complete(self):
        result = self.run_tool('-Apply', operation='QikInventory')
        self.assertEqual(result.returncode, 1)
        self.assertFalse((self.output / 'receipt.json').exists())
        self.assertTrue((self.output / 'failure.json').exists())

    def test_binary_operation_requires_pin(self):
        result = self.run_tool('-Apply', operation='QccExtract',
                               source=self.source / 'authored.txt')
        self.assertEqual(result.returncode, 1)
        self.assertFalse(self.output.exists())

    def test_nested_output_rejected(self):
        self.output = self.source / 'output'
        result = self.run_tool('-Apply')
        self.assertEqual(result.returncode, 1)
        self.assertFalse(self.output.exists())

    def test_short_path_alias_cannot_hide_nested_output(self):
        folder=self.base/'long input directory'
        folder.mkdir();(folder/'fixture.txt').write_text('fixture')
        buffer=ctypes.create_unicode_buffer(32768)
        length=ctypes.windll.kernel32.GetShortPathNameW(str(folder),buffer,len(buffer))
        if not length or buffer.value.casefold()==str(folder).casefold():
            self.skipTest('8.3 names unavailable on this volume')
        short=Path(buffer.value)
        self.output=short/'nested'
        result=self.run_tool('-Apply',source=short)
        self.assertEqual(result.returncode,1,result.stderr)
        self.assertFalse(self.output.exists())

    def test_extended_namespace_alias_is_rejected_before_mutation(self):
        normal=self.source/'nested'
        self.output=Path('\\\\?\\'+str(normal))
        result=self.run_tool('-Apply')
        self.assertEqual(result.returncode,1)
        self.assertFalse(normal.exists())
        self.output=self.base/'outside'
        result=self.run_tool('-Apply',source=Path('\\\\?\\'+str(self.source)))
        self.assertEqual(result.returncode,1)
        self.assertFalse(self.output.exists())

    def test_junction_ancestor_cannot_hide_nested_output(self):
        link=self.base/'alias'
        command="$ErrorActionPreference='Stop'; New-Item -ItemType Junction -Path $env:WHT_LINK -Target $env:WHT_TARGET | Out-Null"
        subprocess.run([shutil.which('pwsh'),'-NoProfile','-Command',command],
                       env={**os.environ,'WHT_LINK':str(link),'WHT_TARGET':str(self.source)},
                       capture_output=True,check=True)
        self.output=self.source/'new-output'
        try:
            result=self.run_tool('-Apply',source=link/'authored.txt')
            self.assertEqual(result.returncode,1)
            self.assertFalse(self.output.exists())
        finally:
            os.rmdir(link)

    def test_msi_bound_is_a_failure_not_an_absent_optional_table(self):
        path=self.base/'authored.msi'
        setup="""$ErrorActionPreference='Stop'
$installer=New-Object -ComObject WindowsInstaller.Installer
$db=$installer.OpenDatabase($env:WHT_TEST_MSI,3)
foreach($sql in @('CREATE TABLE `File` (`File` CHAR(72) NOT NULL PRIMARY KEY `File`)',
'CREATE TABLE `Registry` (`Registry` CHAR(72) NOT NULL PRIMARY KEY `Registry`)',
'INSERT INTO `Registry` (`Registry`) VALUES (''one'')',
'INSERT INTO `Registry` (`Registry`) VALUES (''two'')')){
 $view=$db.OpenView($sql);$view.Execute();$view.Close()
}
$db.Commit()
"""
        made=subprocess.run([shutil.which('pwsh'),'-NoProfile','-Command',setup],
                            env={**os.environ,'WHT_TEST_MSI':str(path)},capture_output=True,text=True,timeout=20)
        self.assertEqual(made.returncode,0,made.stderr)
        worker=ROOT/'research/adapters/package_tools/Read-MsiTables.ps1'
        limited=subprocess.run([shutil.which('pwsh'),'-NoProfile','-File',str(worker),'-Path',str(path),'-MaxRows','1'],capture_output=True,text=True,timeout=20)
        self.assertNotEqual(limited.returncode,0)
        self.assertIn('row bound',limited.stderr)
        valid=subprocess.run([shutil.which('pwsh'),'-NoProfile','-File',str(worker),'-Path',str(path)],capture_output=True,text=True,timeout=20)
        self.assertEqual(valid.returncode,0,valid.stderr)
        data=json.loads(valid.stdout)
        self.assertEqual(len(data['tables']['Registry']),2)
        self.assertEqual(data['tables']['TypeLib']['status'],'Absent')


if __name__ == '__main__':
    unittest.main()
