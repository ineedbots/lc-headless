# Agent guide

This file is the entry point for agents working in this repository. Use the linked
guides for detailed rules and read the design documents relevant to the task.

## Start here

1. Read [README.md](README.md) for the project overview and documentation index.
   This is a C++20 headless LostCity client supporting revisions 289, 274 and 225,
   with an embedded pocketpy scripting runtime.
2. Follow [CONVENTIONS.md](docs/design/CONVENTIONS.md) for C++ style, naming,
   ownership, error handling, includes and project layout. Standalone `_s` and `_e`
   types and their companion implementations live in subsystem `Type/` folders;
   exception types live in `Error/` folders.
3. Follow [DevelopmentWorkflow.md](docs/design/DevelopmentWorkflow.md) for issue
   tracking, feature branches, pull requests, commit messages and release policy.
   Feature branches start from `develop` and target `develop`; authored commit
   subjects use `type(scope): description`.
4. Read [Building.md](docs/Building.md) before configuring, testing, collecting
   coverage or packaging. It documents toolchains, vcpkg, presets, test data and
   stdlib runtime specs.

GitHub Issues are the current backlog, as described in DevelopmentWorkflow.
Design documents contain implementation context and historical decisions; some
retain completed phase plans, old class names and superseded examples. Check the
current source, tests and user guides before treating a design example as current
behavior. Update the relevant documentation when changing its contract.

## Documentation by task

| Task or subsystem | Read |
|---|---|
| Configuration, JSONC, defaults and account overrides | [Configuration](docs/Configuration.md), [Config design](docs/design/ConfigDesign.md) |
| Startup, account lifecycle, console commands and shutdown | [Running](docs/Running.md), [Scripting design](docs/design/ScriptingDesign.md) |
| TCP, WebSocket, TLS, SOCKS5 and the shared network loop | [Transport design](docs/design/TransportDesign.md) |
| Packet buffers, ISAAC and RSA support | [Packet I/O design](docs/design/PacketDesign.md) |
| Opcodes, login and wire payloads | Protocol references for [289](docs/design/tcp-protocol-289.md), [274](docs/design/tcp-protocol-274.md) and [225](docs/design/tcp-protocol-225.md) |
| Revision differences across protocol and cache | [Revision design (225)](docs/design/RevisionDesign.md), [Revision 274 design](docs/design/Revision274Design.md) |
| Cache loading, definitions, maps, collision and local pathfinding | [Cache design](docs/design/CacheDesign.md) |
| World navigation, transport edges and exported walker data | [Bot API design](docs/design/BotApiDesign.md), [Walking API](docs/scripting/walking.md), [Walker data](data/nav/README.md) |
| Script runtime, interpreters, scheduling, hooks and events | [Scripting design](docs/design/ScriptingDesign.md), [Script structure](docs/scripting/script-structure.md), [Events](docs/scripting/events.md) |
| Script bindings, facades, queries, bots and embedded stdlib | [Bot API design](docs/design/BotApiDesign.md), [Scripting reference index](docs/scripting/README.md) |
| Python compatibility, imports and porting scripts | [Python dialect and porting](docs/scripting/python-dialect.md), [Writing stdlib runtime specs](docs/Building.md#writing-stdlib-runtime-specs) |
| Logging, sinks and console output | [Logger design](docs/design/LoggerDesign.md) |
| HTTP routing, console command execution and application status | [HTTP REST design](docs/design/HttpRestDesign.md) |
| Account progress, experience and item logs, fleet view | [Fleet tracking](docs/FleetTracking.md) |
| Supported features, runtime prerequisites and release history | [Features](docs/Features.md), [Requirements](docs/Requirements.md), [Changelog](CHANGELOG.md) |

The [scripting reference index](docs/scripting/README.md) links to individual API
guides for items, interfaces, banks, shops, quests, clues, hunting and other script
features. Use those pages for the current script-facing contract.

## Source map

- `src/Application/`, `src/Accounts/`: process startup, account lifecycles and the
  main loop.
- `src/Config/`, `src/Console/`, `src/Http/`: settings, logging, console and HTTP.
- `src/Io/`: transport, packet buffers and ISAAC.
- `src/Cache/`: cache stores, archives, definitions and map decoding.
- `src/Game/`: game state, protocol, packet decoding, queries, interactions,
  collision and navigation; subfolders group each responsibility.
- `src/Script/`: C++ runtime, bindings and conversions; `Host/` holds scheduling,
  hooks and events; `Stdlib/` holds embedded Python modules.
- `scripts/`: runnable bots, examples and editor type stubs in `typings/`.
- `tests/`: Catch2 tests grouped by subsystem; `Support/` contains fixtures and
  fake servers; `Stdlib/` contains Python specs exercised by the embedded runtime.
- `tools/`: coverage, porting checks, data exporters and platform checks.
- `data/nav/`: exported navigation data; see its README before regenerating it.

## Build and validation entry points

Run commands from the repository root. Use the setup and dependency instructions
in [Building.md](docs/Building.md) and presets in
[CMakePresets.json](CMakePresets.json).

| Platform | Configure | Build Debug | Test Debug |
|---|---|---|---|
| Windows x64 | `cmake --preset windows-msvc` | `cmake --build --preset windows-debug --parallel` | `ctest --preset windows-debug --output-on-failure` |
| Linux | `cmake --preset linux-clang` | `cmake --build --preset linux-debug --parallel` | `ctest --preset linux-debug --output-on-failure` |

For test selection, real-cache environment variables, native coverage, stdlib
coverage and Python lint commands, use [Building.md](docs/Building.md). Ordinary
tests use fake servers; real-cache tests can skip when their cache variables are
absent. For live acceptance, follow the guide's scratch configuration and account
instructions.

Check [CI](.github/workflows/ci.yml) for enforced platform and coverage checks, and
the [release workflow](.github/workflows/release.yml) alongside DevelopmentWorkflow
when working on packaging or publication.
