import os
from pathlib import Path
import subprocess
import unittest


@unittest.skipUnless(os.name=='nt','Requires Windows PowerShell 5.1')
class LogParserTests(unittest.TestCase):
    def test_actual_powershell_parser_rejects_malformed_target_messages(self):
        result=subprocess.run(['powershell.exe','-NoProfile','-File',str(Path(__file__).with_name('Test-FtmDeltaLogParser.ps1'))],
                              capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('regressions passed',result.stdout)


if __name__=='__main__':unittest.main()
