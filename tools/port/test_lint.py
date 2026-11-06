"""CPython regressions for pocketpy porting rules: python -I tools/port/test_lint.py."""

import ast
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('port_lint', Path(__file__).with_name('lint.py'))
lint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lint)


class LintTests(unittest.TestCase):
    def membership(self, source):
        tree = ast.parse(source)
        lint.link_parents(tree)
        return lint.none_set_membership(tree)

    def generators(self, modules):
        trees = {str(Path('/stdlib') / name): ast.parse(source) for name, source in modules.items()}
        return lint.undriven_generators(trees, [str(Path('/stdlib'))])

    def test_none_in_known_sets_and_aliases(self):
        cases = [
            'None in {1, 2}', 'None not in set()',
            'values = {1}\nNone in values',
            'values = set([1])\nalias = values\nNone in alias',
            'values = {n for n in [1]}\nNone not in values',
            'values = {1}\ndef f():\n    return None in values',
            'values = {1}\ndef f():\n    local = values\n    return None in local',
        ]
        for source in cases:
            with self.subTest(source=source):
                self.assertEqual(len(self.membership(source)), 1)

    def test_none_set_literals_are_rejected(self):
        self.assertEqual(len(self.membership('values = {None, 1}')), 1)

    def test_none_in_other_collections_and_shadowed_sets_is_valid(self):
        cases = [
            'None in [None]', 'None not in (1, 2)', 'None in {None: 1}',
            'values = [None]\nNone in values',
            'values = {1}\ndef f(values):\n    return None in values',
            'values = {1}\ndef f():\n    values = [None]\n    return None in values',
            'from somewhere import values\nNone in values',
            'def set():\n    return [None]\nNone in set()',
            'alias = alias\nNone in alias',
        ]
        for source in cases:
            with self.subTest(source=source):
                self.assertEqual(self.membership(source), [])

    def test_membership_is_integrated_into_file_lint(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'test.py'
            path.write_text('values = {1}\nNone in values\n', encoding='utf-8')
            self.assertTrue(any('unhashable' in message for _, message in lint.lint(path)))

    def test_conditional_generator_returns_are_reported(self):
        for expression in ['work() if flag else work()', 'None if flag else work()', 'work() if flag else (work() if flag else None)']:
            source = 'def work():\n    yield 1\ndef wrapper(flag):\n    return ' + expression
            with self.subTest(expression=expression):
                self.assertTrue(self.generators({'tasks.py': source}))

    def test_imported_generators_and_long_wrapper_chains_are_tracked(self):
        modules = {
            'tasks.py': 'def work():\n    yield 1',
            'client.py': 'from tasks import work as step\ndef a(flag):\n    return step() if flag else None\ndef b():\n    return a(True)\ndef c():\n    return b()\ndef d():\n    return c()\ndef e():\n    return d()\nif e():\n    pass',
        }
        findings = self.generators(modules)
        self.assertTrue(any('e()' in message for rows in findings.values() for _, message in rows))

    def test_driven_generators_and_plain_conditional_results_are_valid(self):
        source = 'def work():\n    yield 1\ndef wrapper(flag):\n    return (yield from work()) if flag else None\ndef value():\n    return 1\ndef plain(flag):\n    return value() if flag else None\ndef outer():\n    def inner():\n        return work()\n    return False\nif outer():\n    pass'
        self.assertEqual(self.generators({'tasks.py': source}), {})


if __name__ == '__main__':
    unittest.main()
