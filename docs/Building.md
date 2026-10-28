# Building

[Back to README](../README.md) · [Features](Features.md) · [Requirements](Requirements.md) · [Configuration](Configuration.md) · [Running](Running.md)

Build commands below run from the repository root. The project uses C++20, CMake presets and vcpkg manifest dependencies. You do not need a running game server to build or run the ordinary tests.

## Windows toolchain

Install Visual Studio 2022 with the **Desktop development with C++** workload, including MSVC and CMake 3.25 or newer. The Windows presets select the `Visual Studio 17 2022` generator. Ensure `git`, `cmake`, `ctest` and `cpack` are available in the shell; a Visual Studio developer PowerShell supplies its installed build tools.

You can use an existing vcpkg checkout, including Visual Studio's, by setting `VCPKG_ROOT` to it. To create a separate checkout in PowerShell:

```powershell
git clone https://github.com/microsoft/vcpkg "$env:USERPROFILE/vcpkg"
& "$env:USERPROFILE/vcpkg/bootstrap-vcpkg.bat"
$env:VCPKG_ROOT = "$env:USERPROFILE/vcpkg"
```

This sets the variable for the current shell. If using a persistent user environment variable, open a new terminal afterward. The x86 preset requires the x86 MSVC tools and uses a separate build directory and dependency triplet.

## Linux toolchain

Install Clang, CMake 3.25 or newer and Ninja. The standard library must support C++20 `<format>`: libstdc++ 13 or newer, or libc++ 17 or newer. The supplied Linux preset selects `clang++` and uses its default standard library. Builds are tested on Ubuntu 24.04 and Arch, on x64 and arm64.

Ubuntu 24.04:

```sh
sudo apt install build-essential clang cmake ninja-build git curl zip unzip tar pkg-config perl
```

Arch:

```sh
sudo pacman -S --needed base-devel clang cmake ninja git curl zip unzip tar perl
```

Set up vcpkg if it is not already available:

```sh
git clone https://github.com/microsoft/vcpkg "$HOME/vcpkg"
"$HOME/vcpkg/bootstrap-vcpkg.sh"
export VCPKG_ROOT="$HOME/vcpkg"
```

Add the export to your shell startup file to retain it for future terminals. Do not shallow-clone vcpkg: [vcpkg.json](../vcpkg.json) pins a historical baseline and requires the corresponding Git history.

Ubuntu 22.04's default libstdc++ is too old for `<format>`. Installing a newer Clang alone does not replace that standard library. Use a toolchain with a supported library or a newer distribution.

## Dependencies

CMake reads the vcpkg toolchain from `$VCPKG_ROOT/scripts/buildsystems/vcpkg.cmake` (`$env:VCPKG_ROOT` in PowerShell). Configure installs these dependencies automatically:

| Dependency | Use |
|---|---|
| Boost.Asio and Boost.Beast | TCP, WebSocket and asynchronous networking. |
| OpenSSL | TLS for `wss`. |
| bzip2 and zlib | Compressed game-cache archives and maps. |
| nlohmann/json | Configuration and JSON data. |
| pocketpy | Embedded Python interpreter. |
| Catch2 | Native test runner. |

[vcpkg-configuration.json](../vcpkg-configuration.json) enables the [pocketpy overlay port](../ports/pocketpy), which supplies version 2.2.0 rather than the registry's older 1.x versions. Keep the overlay and manifest with the source tree. CPython is not needed for the normal build: CMake embeds the project's Python standard library using [EmbedStdlib.cmake](../cmake/EmbedStdlib.cmake).

## Configure, build and test

The first configure can take a while because it builds dependencies. Run one platform's sequence:

| Target | Configure | Build Release | Test Release | Output directory |
|---|---|---|---|---|
| Windows x64 | `cmake --preset windows-msvc` | `cmake --build --preset windows-release --parallel` | `ctest --preset windows-release` | `build/windows-msvc/Release/` |
| Windows x86 | `cmake --preset windows-msvc-x86` | `cmake --build --preset windows-x86-release --parallel` | `ctest --preset windows-x86-release` | `build/windows-msvc-x86/Release/` |
| Linux x64 or arm64 | `cmake --preset linux-clang` | `cmake --build --preset linux-release --parallel` | `ctest --preset linux-release` | `build/linux-clang/Release/` |

The Linux build is native to the host architecture; these presets do not cross-compile. Windows selects `x64-windows-static-md` or `x86-windows-static-md` for vcpkg.

For Debug, keep the configure preset and replace `release` with `debug` in the build and test presets. The output moves to `Debug/`. The generators support multiple configurations in the same build directory; there is no need to set `CMAKE_BUILD_TYPE`. Release builds treat compiler warnings as errors.

Each build produces `Rs2004Headless` and `Rs2004HeadlessTests` (with `.exe` on Windows). Everything under `src/` except `main.cpp` builds into `Rs2004HeadlessLib`, which both executables link. Windows also produces `Rs2004Headless.sln` in the build directory for Visual Studio.

To run a source-built client, keep the repository root as the working directory and invoke the executable by its output path. See the [running guide](Running.md#first-login).

## Test data

The Catch2 suite uses fake game servers on loopback ports and does not require a live server. It also loads the example Python scripts, so changes that break an example are detected.

Tests needing real cache data skip when their environment variable is absent. Set any caches you have before running CTest:

| Environment variable | Cache directory |
|---|---|
| `RS2004_CACHE_DIR` | Revision 289, typically `<289 server>/engine/data/pack`. |
| `RS2004_CACHE_DIR_274` | Revision 274, typically `<274 server>/engine/data/pack`. |
| `RS2004_CACHE_DIR_225` | Revision 225, typically `<225 server>/engine/data/pack/client`. |

For example, in PowerShell use `$env:RS2004_CACHE_DIR = 'C:/servers/289/engine/data/pack'`; in a POSIX shell use `export RS2004_CACHE_DIR=/path/to/289/engine/data/pack`. Test caches are controlled by these variables, independently of `client.jsonc`.

## Coverage

Coverage uses dedicated presets and additional tools; normal build presets do not enable instrumentation. For account scripts' line timings, see [Script profiling](Running.md#script-profiling).

### Native code coverage

Native coverage uses a separate Linux Clang Debug build. Install Python 3 and LLVM's coverage tools
(`sudo apt install python3 llvm libclang-rt-dev` on Ubuntu 24.04), with `llvm-cov` and `llvm-profdata` matching the compiler's
major version. Keep `VCPKG_ROOT` set as for a normal build, then run from the repository root:

```sh
python3 tools/coverage/native.py
```

To include real-cache tests with revision 289 in `data/cache` and the older revisions in its `225` and
`274` subdirectories, set their paths before collecting coverage:

```sh
export RS2004_CACHE_DIR="$PWD/data/cache"
export RS2004_CACHE_DIR_225="$PWD/data/cache/225"
export RS2004_CACHE_DIR_274="$PWD/data/cache/274"
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

### Stdlib script coverage

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

## Package a release archive

Build and test Release first, then run the matching CPack preset:

```powershell
cpack --preset windows-release
# For x86: cpack --preset windows-x86-release
```

```sh
cpack --preset linux-release
```

Archives go to `build/packages/`: ZIP on Windows and TGZ on Linux. Packaging includes the client, README, sample configs, example scripts, type stubs, navigation data and third-party licenses. It omits the test executable, private account files and server cache. The [install rules](../CMakeLists.txt) define the archive's contents.

The [release workflow](../.github/workflows/release.yml) builds and tests Windows x64/x86 and Linux x64/arm64 before packaging. A version tag must match the version in `CMakeLists.txt`; an optional prerelease suffix marks a prerelease. Running CPack locally creates an archive without publishing it.

## Project layout

```
src/
├── main.cpp
├── Application/              startup, the command line, Ctrl+C
├── Accounts/                 each account's lifecycle, the main loop over all accounts, console commands, progress reports
├── Config/                   client.jsonc and the account files: the structs, parsing, rules, the JSONC editor
├── Console/                  the logger, log files and console output, console input and its commands
├── Script/
│   ├── (root)                pocketpy runtime and interpreters, what the bindings reach, messages between scripts
│   ├── Bindings/             the _core functions, one class per area
│   ├── Convert/              Python values to and from C++
│   └── Host/                 one account's script: its schedule, hooks and events
├── Cache/                    reading the server's cache: the store, archives, definitions, map squares, login CRCs, the logout button
├── Game/
│   ├── GameClient            login, reconnects, logout, polling the connection
│   ├── Map/                  each account's collision map and scenery, and the route search
│   ├── Nav/                  the world graph and the long-distance walker's data
│   ├── Query/                searches over the game state: entities, inventories, the player, reachability
│   ├── Menu/, Interface/     menu ops, interfaces and dialogue
│   ├── Net/                  login handshake, reading and writing packets
│   ├── Protocol/             opcodes, client packet builders, text encodings
│   ├── Decode/               turns server packets (including player, NPC and zone updates) into game state
│   └── State/                the game state, and the event log that script hooks receive
├── Io/                       network transport, packet buffer, ISAAC cipher
└── Utils/                    shared helpers: strings, files, big integers for RSA, file watcher
tests/                        Catch2 tests in the same folders as src/; Support/ holds the fake game server and other helpers
scripts/                      bot scripts: bots/, examples/, and typings/ for editors
accounts/                     account files (ignored by git) and the sample file
ports/pocketpy/               vcpkg overlay port for pocketpy 2.2.0
docs/                         user guides, scripting reference, and design/ for designs and protocol references
tools/                        data exporters for rs2b0t's walker and catalogs, and docker/ for the Linux build check
thirdparty/                   licenses of the projects code was ported from
```

Everything in `src/` except `main.cpp` builds into a static library. The client and the tests both link that library, so the tests run the same code that ships.

## Build troubleshooting

| Failure | Check |
|---|---|
| vcpkg toolchain file not found | Set `VCPKG_ROOT` to the checkout containing `scripts/buildsystems/vcpkg.cmake` in the same shell used for configure. |
| vcpkg cannot find the baseline | Use a full checkout with the pinned commit's history, not a shallow clone. |
| Visual Studio generator unavailable | Install Visual Studio 2022 and its C++ workload; the presets name that generator explicitly. |
| `cmake`, `ctest` or `cpack` not found | Use the developer shell or add the installed CMake tools to PATH. |
| Missing `<format>` on Linux | Check the standard library selected by Clang as well as the compiler version. |
| Wrong cached generator or toolchain | Configure a fresh build directory or use `cmake --fresh --preset <configure-preset>` after correcting the setup. |
| Release fails on a warning | Fix the warning; non-Debug configurations enable warnings as errors. |
| Cache tests skip | Set the corresponding `RS2004_CACHE_DIR*` variable to a matching cache layout before invoking CTest. |
| Built client cannot find data | Launch from the repository root or extracted package directory; relative paths use the working directory. |
