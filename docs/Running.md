# Running

[Back to README](../README.md) Â· [Features](Features.md) Â· [Requirements](Requirements.md) Â· [Configuration](Configuration.md) Â· [Building](Building.md)

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
| `say <text>` | Send public chat from accounts in game, limited to 80 characters. Use `say ::<command>` to send a server command (up to 80 characters after `::`). |
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

The shared account loop logs a warning when an account step takes at least 100 ms,
including the account name and elapsed milliseconds. Warnings are limited to once
per account every 10 seconds. The measurement covers packet processing, script
work and reporting within the step, including disk waits and time when the OS
does not schedule the process. It does not identify the cause or interrupt the
step; the warning appears after the step returns. Account scheduling and script
watchdog limits are unchanged.

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

## Live progress events

Native operator clients can connect to `ws://127.0.0.1:8080/api/v1/events` on the
configured HTTP listener. The `account.progress` event is emitted when
ProgressReporter obtains an `on_progress_report()` result. The account must have
`script.progressReportMinutes` enabled. File-write failures do not prevent events.

Send JSON text:

```json
{"version":1,"type":"subscribe","id":"progress","events":["account.progress"],"accounts":["bot1"]}
```

Subscribe to logout completion on the same endpoint:

```json
{"version":1,"type":"subscribe","id":"logout","events":["account.logout"],"accounts":["bot1"]}
```

`account.logout` carries `payload: {"confirmed": true}` when the client observes
server logout completion, including temporary relogs and server-initiated logout.
A timeout or forced closure during an in-progress logout emits `confirmed: false`.
Requesting logout alone does not emit an event, and unrelated connection drops do
not emit logout events. Each completion emits once. Logout events are live only;
they are absent from snapshots and are not replayed after reconnect. They do not
require progress reporting or a script. Both event names may share a subscription.

To watch logout events with the [Python test client](../tools/events/logout.py),
run `python -m pip install websockets`, then
`python tools/events/logout.py --account bot1`. Omit `--account` to watch all
accounts, use `--url` for another listener, or add `--progress` to watch reports too.
After the subscription acknowledgement, interrupt an account or run a script that
calls `stop_account()` or `relog()`. The client prints the received JSON envelopes.
Press Ctrl+C in the Python terminal to stop watching.

The server acknowledges, sends a snapshot of the latest available progress report for each
matching account, then sends ordered live reports. Empty/omitted `accounts` means
all configured accounts. Names are exact account config names. Empty snapshots
are normal before the first report. Subscribing never invokes a script hook.

```json
{"version":1,"type":"unsubscribe","id":"progress"}
```

Unsubscribe is effective at its acknowledgement. Reconnect and subscribe again
after disconnect; there is no replay. Compare `instance` to detect process
restarts; global sequence gaps can arise from filtering. Slow subscribers and
publisher overflow close with 1013 and require a fresh subscription/snapshot.

Reports expose script-provided data. Browser Origin headers are rejected; the
service has no authentication or native TLS. Use a private bind and a controlled
proxy for remote access. The [native Python example](../tools/events/progress.py)
subscribes and reconnects using the separately installed `websockets` package.
The [protocol design](design/WebSocketEventsDesign.md) defines exact schemas,
limits, ordering, extension steps, and shutdown behavior.

## HTTP API

Enable `http.host` in `client.jsonc` as described in [Configuration](Configuration.md#http-operator-api).
The API supports HTTP/1.1 and sequential keep-alive, including buffered pipelined requests.

```sh
curl http://127.0.0.1:8080/api/v1/status
curl -H 'Content-Type: application/json' --data '{"command":"@main status"}' http://127.0.0.1:8080/api/v1/console/commands
```

`GET /api/v1/status` queues a fresh main-thread snapshot, returning a decimal-string `requestId`,
`application` (`state`, `uptimeMs`), and `accounts` (`name`, `started`, `finished`, `status`).
It excludes configuration and credentials. Status text is descriptive and may evolve.

`POST /api/v1/console/commands` accepts exactly one nonempty string field, `command`, using the
same syntax and dispatcher as stdin. Embedded CR, LF and NUL are rejected. This executes the
application's console language. The original connection waits for the handler to return,
including every accepted script recipient of a broadcast. Completion acknowledges a handler's
return; later walking, bot activity, logout and packet delivery may still be in progress.

Command responses include `requestId`, `outcome`, `output`, `outputTruncated`, `executionStarted`,
and `recipients` (each with `account`, `outcome`, and optional `errorCode`). Mixed broadcast results
return HTTP 200 with `outcome: "partial"`; inspect recipients. Captured output preserves the console
log threshold and ordered plain lines, including script logs and partial Python print lines.
It tees to the existing terminal and file output. Unrelated account steps, local commands,
other threads, and nested network callbacks are excluded. Captured UTF-8 is truncated at a codepoint
boundary when full; execution and normal logging continue. Invalid log bytes are replaced during
JSON serialization. Direct third-party `printf` output is outside this contract.

| HTTP status | Meaning |
|---|---|
| 200 | Handler/snapshot completed; inspect outcome for partial results |
| 400 | Malformed HTTP/JSON or invalid request envelope |
| 404 / 405 | Unknown route / unsupported method (`Allow` lists the accepted method) |
| 413 / 415 / 417 / 431 | Body limit / content type / expectation / header limit |
| 422 | Console command rejected |
| 500 | Internal or script handler failure without a successful recipient |
| 503 | Capacity exhausted or application stopping/cancellation |
| 504 | Admitted request deadline elapsed |

Errors include `error.code`, `error.message`, and a request ID after admission. Finalized command
output is included when available. Routes support literal paths and registered `{name}` path templates. Query parameters are URL-decoded and passed to the endpoint alongside path values and the request body.
Bodies are limited while reading both fixed-length and chunked requests. Headers and receive
buffers are capped at 16 KiB, active connections at 128, receive operations at ten seconds, and
response writes at five seconds. `Expect: 100-continue` is supported after header validation.
Capacity covers queued work, deferred handlers, completed results and response delivery.

Deadlines are checked before dispatch, before each script recipient, and before delivery.
Expired or disconnected work that has not started is cancelled. A handler already running finishes;
its effects may have occurred even when the response is 504. Do not automatically retry commands.
HTTP shares the main thread: a long handler stalls requests and timer delivery alongside game I/O.
The request timeout is eligibility for execution/success, not a hard client response-time bound.
`scripting.callTimeoutMs: 0` disables the Python watchdog. Shutdown closes admission, cancels pending
work, and drains response writes and network cancellation for a bounded period. `quit` acknowledges
its handler before teardown. Delivery still depends on a connected client and a responsive main loop.

### Endpoint parameters

A route registered as `/api/v1/status/{id}` can match
`/api/v1/status/1?something=1&tag=one&tag=two`. Its decoder receives
`pathParameters["id"] == "1"`, `queryParameters["something"] == ["1"]`, and
`queryParameters["tag"] == ["one", "two"]` in an owned `HttpEndpointRequest_s`.
Use `?` before the first query parameter and `&` between later parameters.
An ampersand before `?` is part of the path.

The built-in application snapshot remains at `/api/v1/status`; registering a template defines a new
endpoint and its decoder defines the meaning and validation of its values. Existing endpoints do not
use query values. Numeric conversion and endpoint-specific validation belong in the decoder.

Path parameters match one nonempty segment and use identifier names such as `{id}` or `{account_name}`.
Literal segments take priority over parameter segments; the router selects a full path before selecting
a method. Trailing slashes are significant. Percent escapes are decoded once as UTF-8 after splitting
path/query delimiters, so `%2F` within a path value stays within that value. Query `+` becomes a space;
path `+` and encoded `%2B` stay plus signs. Repeated query keys preserve all their values in arrival order.
Flags (`?flag`) and empty values (`?flag=`) produce an empty string; empty `&` fields are ignored.
Malformed escapes, invalid UTF-8, control bytes, empty query names and URL fragments return `400`.
