"""Behavioral probes for the formatter configuration used by CI."""

from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[2]


class FormatTests(unittest.TestCase):
    def format(self, source, check=False):
        command = ['clang-format', '--style=file', '--assume-filename=probe.cpp']
        if check:
            command += ['--dry-run', '--Werror']
        result = subprocess.run(command, input=source.encode(), capture_output=True, cwd=ROOT)
        result.stdout = result.stdout.decode()
        result.stderr = result.stderr.decode()
        return result

    def test_missing_loop_braces_fail_with_diagnostics(self):
        source = 'void F()\n{\n    while (Ready())\n        Step();\n}\n'
        result = self.format(source, check=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('code should be clang-formatted', result.stderr)
        self.assertIn(':4:', result.stderr)
        fixed = self.format(source)
        self.assertEqual(fixed.returncode, 0, fixed.stderr)
        self.assertIn('while (Ready())\n    {\n        Step();\n    }', fixed.stdout)
        self.assertEqual(self.format(fixed.stdout, check=True).returncode, 0)

    def test_if_for_and_else_bodies_receive_braces(self):
        result = self.format('void F() { if (Ready()) Step(); else for (;;) Step(); }')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('if (Ready())\n    {', result.stdout)
        self.assertIn('else\n    {', result.stdout)
        self.assertIn('for (;;)\n        {', result.stdout)


if __name__ == '__main__':
    unittest.main()
