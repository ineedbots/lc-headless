"""Check the public dialect-linter CLI's failure and success contracts."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class DialectTests(unittest.TestCase):
    def test_dialect_violation_reports_path_line_and_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'probe.py'
            path.write_text('values = (x for x in [1])\n', encoding='utf-8')
            command = [sys.executable, '-I', str(ROOT / 'tools/port/lint.py'), str(path)]
            result = subprocess.run(command, capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertIn(f'{path}:1:', result.stdout)
            self.assertIn('generator expression', result.stdout)
            path.write_text('values = [x for x in [1]]\n', encoding='utf-8')
            result = subprocess.run(command, capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
