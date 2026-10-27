"""Exercise collection with real LLVM profiles: python3 -m unittest discover -s tools/coverage.

Uses a small independent CMake project; no vcpkg dependencies or game cache required.
Requires clang++, llvm-cov, llvm-profdata, CMake and Ninja on PATH.
"""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import native


class NativeCoverageTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == "linux", "Native coverage targets Linux Clang")
    def test_reports_unlinked_code_filters_sources_and_preserves_failures(self):
        compiler = shutil.which("clang++")
        if not compiler or not shutil.which("ninja"):
            self.skipTest("Clang and Ninja are required")
        with tempfile.TemporaryDirectory(prefix="native-coverage-") as temporary:
            root = Path(temporary)
            (root / "src").mkdir()
            (root / "src" / "called.cpp").write_text(
                'int called(int x) { if (x) return 1; return 0; }\n', encoding="utf-8")
            (root / "src" / "unused.cpp").write_text('int unused() { return 42; }\n', encoding="utf-8")
            (root / "src" / "detail.hpp").write_text('inline int header() { return 7; }\n', encoding="utf-8")
            (root / "src" / "main.cpp").write_text(
                'int called(int);\nint main() { return called(0); }\n', encoding="utf-8")
            (root / "test.cpp").write_text(
                'int run_test();\nint main() { return run_test(); }\n', encoding="utf-8")
            (root / "test_cases.cpp").write_text(
                '#include "src/detail.hpp"\nint called(int);\n'
                'int run_test() { return called(1) == 1 && header() == 7 ? 0 : 1; }\n', encoding="utf-8")
            (root / "generated.cpp").write_text('int generated() { return 3; }\n', encoding="utf-8")
            (root / "CMakeLists.txt").write_text(r'''
cmake_minimum_required(VERSION 3.25)
project(CoverageFixture LANGUAGES CXX)
include("${COVERAGE_HELPER}")
add_library(fixture STATIC src/called.cpp src/unused.cpp generated.cpp)
add_executable(application src/main.cpp)
target_link_libraries(application PRIVATE fixture)
add_executable(tests test.cpp test_cases.cpp)
# Match Catch2WithMain: the test runner's main comes from an uninstrumented dependency.
set_source_files_properties(test.cpp PROPERTIES COMPILE_OPTIONS "-fno-profile-instr-generate;-fno-coverage-mapping")
target_link_libraries(tests PRIVATE fixture)
enable_testing()
add_test(NAME first COMMAND tests)
add_test(NAME second COMMAND tests)
configure_native_coverage(fixture application tests)
''', encoding="utf-8")
            (root / "CMakePresets.json").write_text(json.dumps({
                "version": 6,
                "configurePresets": [{"name": "linux-coverage", "generator": "Ninja",
                                      "binaryDir": "${sourceDir}/build"}],
                "testPresets": [{"name": "linux-coverage", "configurePreset": "linux-coverage",
                                 "output": {"outputOnFailure": True}}],
            }), encoding="utf-8")
            subprocess.run(["cmake", "--preset", "linux-coverage", f"-DCMAKE_CXX_COMPILER={compiler}",
                            "-DCMAKE_BUILD_TYPE=Debug", "-DRS2004_ENABLE_COVERAGE=ON",
                            f"-DCOVERAGE_HELPER={native.ROOT / 'cmake' / 'Coverage.cmake'}"],
                           cwd=root, check=True)
            subprocess.run(["cmake", "--build", "build"], cwd=root, check=True)
            manifest = json.loads((root / "build" / "coverage-Debug.json").read_text(encoding="utf-8"))
            output = root / "build" / "coverage"
            with patch.object(native, "ROOT", root):
                self.assertEqual(native.collect(manifest, output, 2), 0)
                report = (output / "coverage.lcov").read_text(encoding="utf-8")
                data = json.loads((output / "summary.json").read_text(encoding="utf-8"))["data"]
                files = {Path(item["filename"]).name: item["summary"]
                         for section in data for item in section["files"]}
                self.assertEqual(set(files), {"called.cpp", "unused.cpp", "detail.hpp", "main.cpp"})
                self.assertEqual(sum(section["totals"]["lines"]["count"] for section in data),
                                 sum(item["lines"]["count"] for item in files.values()))
                self.assertGreater(files["called.cpp"]["lines"]["covered"], 0)
                self.assertGreater(files["detail.hpp"]["lines"]["covered"], 0)
                self.assertEqual(files["unused.cpp"]["lines"]["covered"], 0)
                self.assertEqual(files["main.cpp"]["lines"]["covered"], 0)
                self.assertGreater(files["called.cpp"]["branches"]["count"],
                                   files["called.cpp"]["branches"]["covered"])
                self.assertTrue((output / "html" / "index.html").is_file())
                called_record = next(record for record in report.split("end_of_record")
                                     if "src/called.cpp" in record)
                # Two processes called it once each. Mappings shared by app and tests must not double-count.
                self.assertIn("FNDA:2,", called_record)

                # Old or corrupted profiles must not contaminate a subsequent run.
                (output / "raw" / "stale.profraw").write_text("invalid", encoding="utf-8")
                self.assertEqual(native.collect(manifest, output, 2), 0)
                self.assertEqual((output / "coverage.lcov").read_text(encoding="utf-8"), report)
                self.assertFalse((output / "raw" / "stale.profraw").exists())

                with (root / "build" / "CTestTestfile.cmake").open("a", encoding="utf-8") as tests:
                    tests.write('\nadd_test(failure "${CMAKE_COMMAND}" "-E" "false")\n'.replace(
                        "${CMAKE_COMMAND}", shutil.which("cmake").replace("\\", "/")))
                self.assertNotEqual(native.collect(manifest, output, 2), 0)
                self.assertTrue((output / "html" / "index.html").is_file())

                (root / "build" / "CTestTestfile.cmake").write_text("", encoding="utf-8")
                with self.assertRaisesRegex(RuntimeError, "produced no coverage profiles"):
                    native.collect(manifest, output, 2)


if __name__ == "__main__":
    unittest.main()
