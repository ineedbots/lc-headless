# Running

[Back to README](../README.md) · [Features](Features.md) · [Requirements](Requirements.md) · [Configuration](Configuration.md) · [Building](Building.md)

## First login

Start from the extracted release directory or repository root. Prepare `client.jsonc`, the matching server cache and an account file as described in [Configuration](Configuration.md). For an initial connection check, omit the account's `script` section and set `idleSeconds` to `30`.

From an extracted Windows release, run in PowerShell:

```powershell
.\Rs2004Headless.exe client.jsonc --account accounts/main.jsonc
```

From an extracted Linux release:

```sh
./Rs2004Headless client.jsonc --account accounts/main.jsonc
```

From a Windows source checkout, keep the repository root as the working directory and use the build output's path:

```powershell
.\build\windows-msvc\Release\Rs2004Headless.exe client.jsonc --account accounts/main.jsonc
```

On Linux, the equivalent source-build path is `./build/linux-clang/Release/Rs2004Headless`. Debug builds use `Debug/`.

An account without a script logs a summary of its surroundings every ten seconds. With `idleSeconds: 30`, it then requests logout. With `idleSeconds: 0`, it stays until interrupted. Confirm the connection this way before adding a `script` section, so configuration errors are easier to isolate.

## Command line

```text
Rs2004Headless [client.jsonc] [--account <file>] [--watch] [--debugger] [--profile] [--raw-console]
```

| Argument | Behavior |
|---|---|
| Positional config path | Defaults to `client.jsonc` in the working directory. Relative paths in it still resolve from the working directory. |
| `--account <file>` | Load exactly this account file, bypassing normal directory discovery and its enabled filter. |
| `--watch` | Reload a script when it or an imported module is saved, without logging out. |
| `--debugger` | Wait for a pocketpy debugger on `127.0.0.1:6110` before login. Requires `--account` with a scripted account. |
| `--profile` | Collect Python line profiling separately for each scripted account. |
| `--raw-console` | Plain log output without colors, prompt or console input. Ctrl+C remains available. |

`--debugger` cannot be combined with `--watch` or `--profile`. `--watch` and `--profile` can be combined. Unknown `--` options fail startup; `help` is an interactive console command, not a `--help` option.

Without `--account`, the client loads enabled `.jsonc` files in the configured accounts directory. Use a different file for each account, up to 16, with unique usernames. Files ending in `.sample` are ignored by discovery. Accounts share one revision, cache and login key, even when using separate world endpoints.

## Interactive console

Type commands into the running client:

| Command | Effect |
|---|---|
| `help` | List built-in and script-provided commands. |
| `status` | Show connection, position and script state for each account. |
| `quit` or `exit` | Request shutdown as with Ctrl+C. Repeating it advances the shutdown stages. |
| `loglevel` | Show the current process log level. |
| `loglevel verbose` | Set all accounts' log level; accepts `verbose`, `info`, `warning`, `error`. |
| `say <text>` | Send public chat from accounts in game, limited to 80 characters. |
| `pause` | Pause scripts while upkeep continues, including random events and run energy management. |
| `resume` | Resume scripts, starting their loop afresh. |

Prefix an applicable command with `@<account>` to target an account by its filename stem or username, without regard to case:

```text
@main status
@main help
@main pause
@main resume
```

`loglevel` applies to every account and does not accept a target. Untargeted script commands go to every running script that registered them. The [console API](scripting/console-and-messages.md#console-commands) documents custom handlers and message routing.

## Retries and reconnects

The process spaces accounts' login attempts using `scripting.loginIntervalSeconds`. A failure can also impose a retry delay; both scheduling constraints apply.

Temporary login or reconnect failures wait `minRetryDelaySeconds`, doubling on later failures up to `maxRetryDelaySeconds`. With defaults, the delay grows through 2, 4, 8, 16 and 30 seconds, then stays at 30. Set minimum and maximum equal for a fixed delay.

`connectAttempts` controls the attempt budget for a login or reconnect. Its special values are:

- `0`: one initial login attempt, with retries and reconnects disabled.
- `100`: retry temporary failures indefinitely.

Other accepted values provide a finite attempt budget. An unexpected session ending, such as a server logout, uses `reloginDelaySeconds` before logging in again. Permanent failures are not made recoverable by enabling infinite retries. See the [configuration reference](Configuration.md#process-scheduling-and-retries) for defaults and ranges.

## Script development

Run one account with automatic reloads:

```powershell
.\Rs2004Headless.exe client.jsonc --account accounts/main.jsonc --watch
```

On Linux, use `./Rs2004Headless` with the same arguments. Saving the main script or an imported module recreates the script's interpreter state: globals start fresh and `on_start()` runs again. Previous game events are skipped, while queued bot messages are kept. If a script fails, watch mode keeps the account logged in and idle until a later save fixes it. Account-file changes require a client restart.

For breakpoints, run with `--debugger` instead and follow the [VS Code attach instructions](scripting/python-dialect.md#debugging-in-vs-code). Debugging pauses the process, and a long pause can cause a server disconnect. The ordinary Python call watchdog does not apply under the debugger.

For timing, add `--profile`; see [Script profiling](#script-profiling) below.

## Script profiling

Start with `Rs2004Headless client.jsonc --profile`, optionally adding `--account accounts/<name>.jsonc` to select one account. Reports go under `profiles/<run-id>/<account>/load-001/profiler_report.json`, relative to the working directory. The log gives the report path. Each watched reload creates a new `load-*` folder so results from different source versions stay separate.

Measurements accumulate across imports, initialization, loops, resumed generators, and hooks. Profiling stops between calls into Python, excluding the account loop's idle waits. Reports are saved every 60 seconds while the application steps accounts, on Python errors, when the script stops, and before its VM is destroyed. A forced process termination can lose results since the last save. Write failures are logged and retried on the next save.

To view a report, install the [PocketPy VS Code extension](https://pocketpy.github.io/features/profiling/) and run **pocketpy: Load Line Profiler Report**. Select the JSON report, then its sibling `sources/` folder as the source root. This contains snapshots of the script and imported modules, including the embedded `rs2004` library. Synthetic interpreter filenames such as `<bootstrap>` have no source snapshot.

Profiling adds overhead and leaves `scripting.callTimeoutMs` unchanged, so an account close to its watchdog limit may time out while profiling. Use the report to find expensive lines, then measure again without `--profile`. PocketPy 2.2.0 uses `clock()` for timings: Windows measures elapsed time and Linux measures process CPU time, including native bindings accordingly. These are line timings, not a breakdown inside C++ bindings or directly comparable cross-platform benchmarks.

## Logs and unattended runs

Set `client.logFile` to append plain log lines to a file as well as console output. The sample config uses `rs2004-headless.log`; the built-in default is no file log. `client.logLevel` sets the initial verbosity, which the interactive `loglevel` command can change.

Use `--raw-console` when a service or another program consumes stdout. It disables interactive commands, so configure the working directory and account files before launch and use the process's supported shutdown signal to stop it. Keep the extracted release's supporting folders available even if the executable is launched by an absolute path.

Progress reports are separate from logs. They require `script.progressReportMinutes` and an `on_progress_report()` hook; see [progress reports](scripting/console-and-messages.md#progress-reports).

## Stopping and exit status

Ctrl+C advances through three stages:

1. Call each script's `on_kill_signal()` if defined, allowing it to stop at a safe point. Other accounts request logout immediately. After `scripting.killGraceSeconds`, remaining accounts request logout too.
2. A second signal requests logout for all accounts immediately.
3. A third signal closes connections still waiting for the server to accept logout.

The server refuses logout during combat and for ten seconds afterward, so requesting logout may not end the connection immediately. Console `quit` and `exit` use the same staged shutdown.

The process returns 0 only when every account logged out cleanly and no script failed. Startup errors, account failures and forced disconnections can produce a nonzero exit. If startup fails, use the [configuration troubleshooting table](Configuration.md#troubleshooting-configuration) before changing script code.
