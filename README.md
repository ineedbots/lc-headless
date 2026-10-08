# rs2004-headless

A headless game client for revision-289 (2004-era RuneScape) servers, such as the 289server engine. It logs in over WebSocket, decodes the server's packets into game state, and runs Python bot scripts against that state. It has no graphics and no game cache, and one process runs up to 16 scripted accounts.

## Features

- **The 289 protocol.** It does the RSA and ISAAC login handshake and decodes every server packet into state: players, NPCs, ground items, scenery changes, inventories, stats, interfaces and chat. It can also build every request the webclient sends.
- **Python scripting** on an embedded [pocketpy](https://github.com/pocketpy/pocketpy) interpreter. A script defines `loop()` and the `on_*` hooks it needs, and calls a flat API such as `get_nearest_npc_by_id(41)`, `attack_npc(npc)` and `walk_to(x, z)`.
- **Several accounts per process.** Each account has its own interpreter and its own log name, and logins are spaced a few seconds apart. An account can log into a different world from the others.
- **Survives server restarts.** A dropped connection reconnects on its own, with up to 10 attempts over about four minutes. The other accounts keep playing in the meantime.
- **Clean shutdown.** Ctrl+C gives each script time to finish what it's doing, then logs every account out.
- **Tools for script authors:**
  - progress reports written to a file
  - messages between scripts
  - reloading a script when it's saved (`--watch`)
  - a VS Code debugger (`--debugger`)
  - type stubs for Pylance and Pyright

## Requirements

- Windows 10 or 11 (x64), with Visual Studio 2022 and its *Desktop development with C++* workload. MSVC, CMake 3.25+ and Ninja all come with that workload.
- [vcpkg](https://github.com/microsoft/vcpkg), with the `VCPKG_ROOT` environment variable set to its folder.
- A revision-289 server to connect to, plus its login CRCs and RSA public key (see [Configuration](#configuration)).

The project is developed on Windows. `linux-clang` presets are also defined; `<format>` there needs libstdc++ 13+ or libc++ 17+.

vcpkg installs the dependencies from `vcpkg.json`: Catch2, IXWebSocket (with OpenSSL, for `wss://`), nlohmann/json and pocketpy 2.2.0. pocketpy comes from an overlay port in [ports/pocketpy](ports/pocketpy), because the vcpkg registry only has its older 1.x versions.

## Building

Run these from an **x64** developer prompt, such as *x64 Native Tools Command Prompt for VS 2022* or a prompt where `vcvars64.bat` has run:

```sh
cmake --preset windows-msvc
cmake --build --preset windows-release      # or windows-debug
```

The `windows-msvc` preset doesn't set up the compiler environment itself, so the prompt has to. The default *Developer Command Prompt* targets x86, which is the wrong architecture. Visual Studio 2022's Open Folder sets up the environment for you.

The first configure builds every dependency through vcpkg, so it takes a while. The build writes these files to `build/windows-msvc/<Config>/`:

- `Rs2004Headless.exe`: the client
- `Rs2004HeadlessTests.exe`: the tests

Release builds treat warnings as errors (`/W4 /WX`). Debug builds report warnings without failing.

### Tests

```sh
ctest --preset windows-debug
```

The Catch2 tests don't need a server. The network tests run against a fake game server on loopback ports. The tests also load the scripts in `scripts/examples/`, so an example that no longer loads fails them.

## Configuration

The client reads two kinds of file. Both are JSON and allow `//` and `/* */` comments. Paths are relative to the working directory, so run the client from the repository root.

### `client.jsonc`: the server and process-wide settings

If `client.jsonc` doesn't exist, the client writes a sample there and exits. In that sample, fill in at least these keys:

| Key | Meaning |
|---|---|
| `server.url` | The server's WebSocket URL, `ws://` or `wss://`. For a local engine on Windows, it's `ws://localhost:80` |
| `server.origin` | The `Origin` header to send. A server that sets `WEB_ALLOWED_ORIGIN` requires it; an empty string sends no header |
| `login.crcs` | The nine cache CRCs that the server checks, as `"0x..."` strings |
| `login.rsaModulus`, `login.rsaExponent` | The server's RSA public key, as decimal or `0x` hex strings |

The CRCs and the RSA key come from the server's deployment and cache, not from the protocol, so take them from the server you're connecting to. Its webclient uses the same values. If they're wrong, the server rejects the login with status 6.

Every other key has a default. These are the ones you're most likely to change:

| Key | Default | Meaning |
|---|---|---|
| `client.logLevel` | `info` | `verbose`, `info`, `warning` or `error` |
| `scripting.accountsDirectory` | `accounts` | The folder of account files |
| `scripting.scriptsDirectory` | `scripts` | The folder of scripts and the modules they import |
| `scripting.loginIntervalSeconds` | `2` | The time between one account's login and the next |
| `scripting.callTimeoutMs` | `1000` | How long one call into a script may run |
| `scripting.killGraceSeconds` | `30` | How long scripts have to finish after Ctrl+C |
| `scripting.progressDirectory` | `progress` | Where progress reports are written |

[docs/ConfigDesign.md §3](docs/ConfigDesign.md#3-file-format) lists every key and its rules. An error message names the key that's wrong but never shows its value, so a mistyped password doesn't end up in the log.

### `accounts/<name>.jsonc`: one file per account

Copy [accounts/example.jsonc.sample](accounts/example.jsonc.sample) to `accounts/<name>.jsonc`. The file name, without `.jsonc`, is the account's name in log lines.

```jsonc
{
    "username": "myuser",
    "password": "mypass",
    "enabled": true,
    "script": {
        "file": "examples/chicken_killer.py",   // relative to scripts/
        "progressReportMinutes": 20,           // 0, or no key at all, means no reports
        "settings": { "loot_goal": 3 }          // read by the script as its settings object
    }
}
```

- An account with no `script` logs in and idles, and logs a summary of its surroundings every 10 seconds. This is a quick way to check a new server config.
- `"enabled": false` keeps the file but doesn't run the account.
- A `server` section, with the same keys as the one in `client.jsonc`, logs this account into a different world.

Git ignores `client*.jsonc`, `accounts/*.jsonc` and `progress/`, so credentials stay out of the repository.

## Running

```
Rs2004Headless.exe [client.jsonc] [--account accounts/<name>.jsonc] [--watch] [--debugger]
```

| Argument | Effect |
|---|---|
| `client.jsonc` | The config file to use. Defaults to `client.jsonc` in the working directory |
| `--account <file>` | Runs only this account. Without it, every enabled file in the accounts folder runs |
| `--watch` | Reloads a script, without logging out, whenever the script or a module it imports is saved. A script that fails stays logged in and idle until the next save |
| `--debugger` | Waits for VS Code's pocketpy debugger to attach on `127.0.0.1:6110` before logging in. Needs `--account`, and can't be used with `--watch` |

From the repository root:

```powershell
# Every enabled account
.\build\windows-msvc\Release\Rs2004Headless.exe

# One account, reloading its script on save
.\build\windows-msvc\Release\Rs2004Headless.exe --account accounts\bot1.jsonc --watch
```

Every script loads before the first login, so a script that fails to load stops the run before any account logs in. pocketpy has 16 interpreter slots, so one process runs at most 16 scripted accounts. Start more processes to run more accounts. No two account files may share a username.

**Stopping.** Ctrl+C works in three steps:

1. The first Ctrl+C calls `on_kill_signal()` in each script that defines it, so the script can stop at a safe point. Every other account logs out straight away. Any account still logged in after `killGraceSeconds` is logged out.
2. A second Ctrl+C logs every account out at once.
3. A third Ctrl+C closes any connection whose logout the server is still refusing. The server refuses a logout during combat and for 10 seconds after it.

The exit code is 0 only when every account logged out cleanly and no script failed.

## Writing scripts

A script is a `.py` file under `scripts/` that defines `loop()`. `loop()` returns how many milliseconds to wait before it's called again; a game tick is 600 ms. A script can also define any of the `on_*` hooks:

```python
CHICKEN = 41

def on_start():
    log('Starting at', get_x(), get_z())

def loop():
    if in_combat():
        return 600

    chicken = get_nearest_npc_by_id(CHICKEN, radius=8, in_combat=False)
    if chicken is not None:
        attack_npc(chicken)
        return 1200

    return 600

def on_server_message(msg):
    if msg.startswith('Oh dear'):
        stop_account()
```

- [docs/ScriptingApi.md](docs/ScriptingApi.md) is the full reference. It covers every function, object and hook, how scripts are scheduled, progress reports, messages between scripts and setting up the debugger.
- [scripts/examples/](scripts/examples) has two complete scripts. `walker.py` walks a loop of tiles, and `chicken_killer.py` kills chickens, picks up the bones and logs out.
- `import name` loads `scripts/name.py`, or `scripts/lib/name.py` if the first doesn't exist.
- If you open the repository in VS Code, the stubs in [scripts/typings/\_\_builtins\_\_.pyi](scripts/typings/__builtins__.pyi) give scripts completion and type checking.

Before you write one, know these limits:

- **Scripts run on pocketpy, not CPython.** pocketpy implements a subset of Python 3: there's no `finally`, no generator expressions, no `re` module and no pip packages. [ScriptingApi.md](docs/ScriptingApi.md#python-dialect) lists all the differences.
- **One thread runs every script.** A call that runs longer than `callTimeoutMs` raises `TimeoutError`, and `time.sleep()` raises an error immediately. To wait, return a delay from `loop()`.
- **The client knows only what the server sends.** Without the game cache:
  - There's no pathfinding. Walks go in straight lines and stop at the first obstacle.
  - Scenery that the server never changed is unknown, so scripts supply the loc id and tile.
  - NPCs and items have ids but no names.
- **Scripts aren't sandboxed.** Run only scripts you trust.

## Project layout

```
src/
├── main.cpp, Application     command line, config loading, Ctrl+C
├── Accounts/                 each account's lifecycle, the main loop over all accounts, progress report files
├── Script/                   pocketpy runtime and interpreters, the Python API and its bindings, messages between scripts
├── Game/
│   ├── GameClient            login, reconnects, logout, polling the connection
│   ├── Net/                  login handshake, reading and writing packets
│   ├── Protocol/             opcodes, client packet builders, text encodings
│   ├── Decode/               turns server packets (including player, NPC and zone updates) into game state
│   └── State/                the game state, and the event log that script hooks receive
├── Io/                       WebSocket transport, packet buffer, ISAAC cipher
└── Core/                     config files, logger, big integers for RSA, file watcher
tests/                        Catch2 tests in the same folders as src/, plus a fake game server
scripts/                      bot scripts: examples/, lib/ for shared modules, typings/ for editors
accounts/                     account files (ignored by git) and the sample file
ports/pocketpy/               vcpkg overlay port for pocketpy 2.2.0
docs/                         design documents and protocol reference
```

Everything in `src/` except `main.cpp` builds into a static library. The client and the tests both link that library, so the tests run the same code that ships.

## Documentation

| Document | Covers |
|---|---|
| [ScriptingApi.md](docs/ScriptingApi.md) | How to write scripts: the API, hooks and tools |
| [ScriptingDesign.md](docs/ScriptingDesign.md) | How scripting works inside: the runtime, events, the main loop and accounts |
| [tcp-protocol-289.md](docs/tcp-protocol-289.md) | The revision-289 wire protocol: login, framing and the payload of every opcode |
| [ConfigDesign.md](docs/ConfigDesign.md) | The formats of the config and account files, with every key and rule |
| [WebSocketDesign.md](docs/WebSocketDesign.md) | The non-blocking WebSocket transport |
| [PacketDesign.md](docs/PacketDesign.md) | The packet buffer, the ISAAC cipher and `BigUInt` |
| [LoggerDesign.md](docs/LoggerDesign.md) | The logger |
| [CONVENTIONS.md](CONVENTIONS.md) | C++ code style and project setup |

## Contributing

Code follows [CONVENTIONS.md](CONVENTIONS.md) (C++20, Allman braces, `PascalCase_s` structs, exceptions for errors) and `.clang-format`. Files use LF line endings, which `.gitattributes` enforces. The build finds `.cpp` and `.hpp` files under `src/` and `tests/` on its own, so a new file doesn't need to be added to `CMakeLists.txt`.

## Credits

- LostCity - https://github.com/LostCityRS
- Plutonium (OpenRSC) - https://gitlab.com/openrsc/plutonium
- rs2b2t - https://github.com/rs2b2t/rs2b0t
