"""CPython regressions for the export audit: python -I tools/port/test_coverage.py."""

import contextlib
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('port_coverage', Path(__file__).with_name('coverage.py'))
coverage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coverage)


class CoverageTests(unittest.TestCase):
    def test_native_replacement_does_not_hide_new_exports(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'src/bot/event/webwalk/PathFinder.ts'
            source.parent.mkdir(parents=True)
            source.write_text('export class PathFinder {}\nexport function futureUnportedRoute() {}\n')
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                missing = coverage.check_modules(folder, set(), ['event/webwalk'])
            self.assertEqual(missing, 1)
            self.assertIn('futureUnportedRoute', output.getvalue())
            self.assertNotIn('missing PathFinder', output.getvalue())

    def test_all_checks_every_surface_and_propagates_missing(self):
        with patch.object(coverage.os.path, 'isfile', return_value=True), \
                patch.object(coverage, 'haystack', return_value=set()), \
                patch.object(coverage, 'check_dts', return_value=0) as dts, \
                patch.object(coverage, 'check_modules', return_value=1) as modules, \
                patch.object(coverage, 'check_bots', return_value=0) as bots, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(coverage.main(['coverage.py', 'upstream', '--all']), 1)
            dts.assert_called_once()
            modules.assert_called_once_with('upstream', set(), ['api', 'event', 'runtime', 'data'])
            bots.assert_called_once()

    def test_missing_anchor_fails_the_audit(self):
        row = {'module': 'test.ts', 'exports': ['Test'], 'implementation': 'missing.py', 'anchor': 'absent'}
        with patch.object(coverage.json, 'load', return_value=[row]), \
                patch('builtins.open', unittest.mock.mock_open(read_data='other code')):
            with self.assertRaisesRegex(ValueError, 'missing port anchor'):
                coverage.replacements()

    def test_invalid_path_cannot_report_success(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, 'does not exist'):
                coverage.check_modules(folder, set(), ['--typo'])


if __name__ == '__main__':
    unittest.main()
