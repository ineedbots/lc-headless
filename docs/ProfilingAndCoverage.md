# Profiling and coverage

## Script profiling

Start with `Rs2004Headless client.jsonc --profile`, optionally adding `--account accounts/<name>.jsonc` to select one account. Reports go under `profiles/<run-id>/<account>/load-001/profiler_report.json`, relative to the working directory. The log gives the report path. Each watched reload creates a new `load-*` folder so results from different source versions stay separate.

Measurements accumulate across imports, initialization, loops, resumed generators, and hooks. Profiling stops between calls into Python, excluding the account loop's idle waits. Reports are saved every 60 seconds while the application steps accounts, on Python errors, when the script stops, and before its VM is destroyed. A forced process termination can lose results since the last save. Write failures are logged and retried on the next save.

To view a report, install the [PocketPy VS Code extension](https://pocketpy.github.io/features/profiling/) and run **pocketpy: Load Line Profiler Report**. Select the JSON report, then its sibling `sources/` folder as the source root. This contains snapshots of the script and imported modules, including the embedded `rs2004` library. Synthetic interpreter filenames such as `<bootstrap>` have no source snapshot.

Profiling adds overhead and leaves `scripting.callTimeoutMs` unchanged, so an account close to its watchdog limit may time out while profiling. Use the report to find expensive lines, then measure again without `--profile`. PocketPy 2.2.0 uses `clock()` for timings: Windows measures elapsed time and Linux measures process CPU time, including native bindings accordingly. These are line timings, not a breakdown inside C++ bindings or directly comparable cross-platform benchmarks.

## Native code coverage

Native coverage uses a separate Linux Clang Debug build. Install Python 3 and LLVM's coverage tools
(`sudo apt install python3 llvm libclang-rt-dev` on Ubuntu 24.04), with `llvm-cov` and `llvm-profdata` matching the compiler's
major version. Keep `VCPKG_ROOT` set as for a normal build, then run from the repository root:

```sh
python3 tools/coverage/native.py
```

The command configures and builds the `linux-coverage` preset, runs CTest with four parallel workers, and writes
`build/linux-coverage/coverage/html/index.html`, `coverage.lcov`, `summary.txt`, and `summary.json`. Use
`--parallel N` to change build and test parallelism, or `--no-build` to collect from an existing coverage build.
Each run clears its previous reports and profiles. Test failures still fail the command; any reports produced
from a failed run are partial.

The report includes authored C++ under `src/`, including headers and code not referenced by the tests.
Tests, dependencies, and generated embedded Python are excluded. The application binary supplies coverage
mappings for `main.cpp`, but is not run, so its entry point starts at zero coverage. C++ exercised by the
embedded script tests contributes to native coverage. Python source coverage has its own report below.

CI uploads the same report as the `native-coverage-linux-x64` artifact and publishes a summary. Coverage
percentages are informational; test or collection failures fail the job. Real-cache tests skip without their
cache environment variables, and hidden `[Slow]` tests are excluded from this baseline. Reports from runs with
cache data can therefore differ from CI. Normal build and test presets do not enable instrumentation.

## Stdlib script coverage

Run with CPython on Linux or Windows (with the normal CMake/vcpkg build environment available):

```sh
python3 tools/coverage/script.py       # Windows: python tools/coverage/script.py
```

This uses the separate `linux-script-coverage` or `windows-script-coverage` Debug preset, builds the tests, and
collects line trace events from the application's pocketpy VM while running the full CTest suite. LLVM tools
are not required. Reports are written under `build/<preset>/script-coverage/`: `html/index.html`,
`coverage.lcov`, `summary.txt`, and `summary.json`. Use `--parallel N` to change build/test parallelism or
`--no-build` to reuse that build. Each collection clears its previous script profiles and reports.

The denominator comes from compiling every embedded stdlib file and walking its bytecode and nested
function declarations without executing them. Unimported modules and uncalled function bodies therefore
remain uncovered. Compiler-generated implicit returns are excluded, matching pocketpy's trace events.
The runner checks embedded sources against the checkout and fails if a rebuild is needed. Only
`src/Script/Stdlib/**/*.py` contributes; script tests, example/account scripts and pocketpy's own modules are
excluded. Counts represent line trace events, which pocketpy can coalesce, rather than exact statement counts.
Script branch coverage is not collected.

Tracing is test-only and opt-in through the runner. Normal application builds do not include the collector.
Coverage presets allow 300 seconds per test instead of 60 to accommodate tracing overhead. Script fixtures
also allow five times their normal VM watchdog duration while collecting coverage; VM deadline tests retain
their original limits. Cache-dependent tests still skip without cache data, and hidden `[Slow]` tests are
excluded. Test or collection errors fail the
command; reports from failed test runs are marked partial. Percentages are informational.

CI reuses the native coverage build with `python3 tools/coverage/script.py --preset linux-coverage --no-build`
and uploads a separate `stdlib-coverage-linux-x64` artifact. Native and script percentages stay separate.
