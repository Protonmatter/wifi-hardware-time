import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import contextlib
import io
import unittest
from research.acquisition.run_bound_campaign import parse, sampler_plan

BASE = ['--if-index', '5', '--condition', 'idle']


class CampaignFlushTests(unittest.TestCase):
    def test_flush_is_opt_in_and_recorded_in_the_plan(self):
        self.assertEqual(sampler_plan(parse(BASE)), {})
        plain = sampler_plan(parse(BASE + ['--sampler', 'persistent']))
        flushed = sampler_plan(parse(BASE + ['--sampler', 'persistent', '--etw-flush']))
        self.assertIs(plain['etw_flush_after_completion'], False)
        self.assertIs(flushed['etw_flush_after_completion'], True)
        self.assertEqual(plain['identity_check_mode'], 'background')
        self.assertEqual(plain['identity_max_age_s'], 60.0)
        self.assertEqual({k: v for k, v in flushed.items() if k != 'etw_flush_after_completion'},
                         {k: v for k, v in plain.items() if k != 'etw_flush_after_completion'})

    def test_flush_requires_the_persistent_sampler(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            parse(BASE + ['--etw-flush'])


if __name__ == '__main__':
    unittest.main()
