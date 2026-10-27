"""Report checks independent of pocketpy; interpreter semantics are tested in ScriptCoverageTests.cpp."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import script


class ScriptReportTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="script coverage ")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.stdlib = self.root / "stdlib"
        (self.stdlib / "rs2004").mkdir(parents=True)
        self.sources = {
            "rs2004/called.py": "def called():\n    return '<unsafe>'\n",
            "rs2004/never_imported.py": "def never():\n    return 42\n",
            "rs2004/__init__.py": "",
        }
        for name, text in self.sources.items():
            (self.stdlib / name).write_bytes(text.encode("utf-8"))
        self.manifest = self.root / "manifest.json"
        self.manifest.write_text(json.dumps({"version": 1, "files": {
            name: {"source": text, "lines": [1, 2] if text else []}
            for name, text in self.sources.items()
        }}), encoding="utf-8")
        self.raw = self.root / "raw"
        self.raw.mkdir()
        for index, count in enumerate((1, 2)):
            self.profile(index, {"version": 1, "failed": False,
                                 "files": {"rs2004/called.py": {"1": count}}})
        self.addCleanup(patch.stopall)
        patch.object(script, "STDLIB", self.stdlib).start()

    def profile(self, index, value):
        (self.raw / f"{index}.json").write_text(json.dumps(value), encoding="utf-8")

    def test_merges_processes_and_reports_never_imported_files_and_uncalled_bodies(self):
        counts = script.merge(self.manifest, self.raw)
        self.assertEqual(counts["rs2004/called.py"], {1: 3, 2: 0})
        self.assertEqual(counts["rs2004/never_imported.py"], {1: 0, 2: 0})
        script.report(counts, self.root, partial=True)
        summary = json.loads((self.root / "summary.json").read_text())
        self.assertTrue(summary["partial"])
        self.assertEqual(summary["totals"], {"covered": 1, "executable": 4, "percent": 25.0})
        lcov = (self.root / "coverage.lcov").read_text()
        self.assertIn("SF:src/Script/Stdlib/rs2004/never_imported.py\nDA:1,0\nDA:2,0", lcov)
        self.assertIn("DA:1,3\nDA:2,0", lcov)
        source = (self.root / "html/files/rs2004/called.py.html").read_text()
        self.assertIn("&lt;unsafe&gt;", source)
        self.assertIn('class="miss" id="L2"', source)
        self.assertIn("PARTIAL", (self.root / "html/index.html").read_text())

    def test_rejects_stale_sources_and_missing_modules(self):
        (self.stdlib / "rs2004/called.py").write_text("changed = True\n", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "Embedded source differs"):
            script.merge(self.manifest, self.raw)
        (self.stdlib / "rs2004/new.py").write_text("value = 1\n", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "Embedded stdlib files differ"):
            script.merge(self.manifest, self.raw)

    def test_rejects_failed_traces_and_impossible_line_numbers(self):
        for profile, message in (
            ({"version": 1, "failed": True, "files": {}}, "failed script coverage profile"),
            ({"version": 1, "failed": False, "files": {"rs2004/called.py": {"99": 1}}}, "Trace does not match"),
            ({"version": 1, "failed": False, "files": {"test.py": {"1": 1}}}, "non-stdlib file"),
        ):
            with self.subTest(message=message):
                self.profile(0, profile)
                with self.assertRaisesRegex(RuntimeError, message):
                    script.merge(self.manifest, self.raw)

    def test_rejects_empty_or_missing_trace_data(self):
        for path in self.raw.glob("*.json"):
            path.unlink()
        with self.assertRaisesRegex(RuntimeError, "no script coverage profiles"):
            script.merge(self.manifest, self.raw)
        self.profile(0, {"version": 1, "failed": False, "files": {}})
        with self.assertRaisesRegex(RuntimeError, "no executed stdlib lines"):
            script.merge(self.manifest, self.raw)


if __name__ == "__main__":
    unittest.main()
