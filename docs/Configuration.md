# Configuration

[Back to README](../README.md) · [Features](Features.md) · [Requirements](Requirements.md) · [Running](Running.md) · [Building](Building.md)

The client reads a process configuration and one JSONC file per account. JSONC accepts `//` and `/* ... */` comments; keep normal JSON quoting, types and comma rules. Windows paths can use forward slashes, or escaped backslashes such as `C:\\servers\\cache`.

## Initial setup and paths

Copy [client.jsonc.sample](../client.jsonc.sample) to `client.jsonc`, and [accounts/example.jsonc.sample](../accounts/example.jsonc.sample) to `accounts/main.jsonc`. The samples are templates; the placeholder RSA key must be replaced before startup.

Paths in the process configuration resolve from the **working directory**, including when an alternative config file is passed on the command line. They do not resolve from that config file's folder. `script.file` instead resolves under `scripting.scriptsDirectory`.

A minimal process configuration looks like this; replace both RSA placeholders with the server's actual values:

```jsonc
{
    "server": {"transport": "ws", "host": "localhost", "port": 80, "origin": "http://localhost"},
    "login": {
        "revision": 289,
        "rsaModulus": "<server modulus as decimal or 0x hex>",
        "rsaExponent": "<server exponent as decimal or 0x hex>"
    },
    "client": {"cacheDirectory": "data/cache"}
}
```

Omitted settings use the defaults below. A missing process config is an error. Account discovery scans the accounts directory's immediate `.jsonc` files in sorted order, loads them, and runs enabled accounts. Sample files ending in `.sample` are not discovered. Enabled usernames must be unique without regard to case. Up to 16 accounts can run in one process.

## Server and login reference

| Key | Default | Accepted value or purpose |
|---|---|---|
| `server.transport` | `ws` | `ws`, `wss` or `tcp`. |
| `server.host` | empty; must be set | Hostname or IPv4 address, 1–253 letters, digits, hyphens or dots. No URL scheme, port, path or IPv6 literal. |
| `server.port` | `0`; must be set | Integer from 1 to 65535. |
| `server.origin` | empty | WebSocket `Origin` header; empty sends no header. Must be printable ASCII when set. |
| `server.tlsCaFile` | `SYSTEM` | `SYSTEM`, `NONE` or a PEM CA bundle path; used for `wss`. Must not be empty. |
| `login.revision` | `289` | `289`, `274` or `225`, shared by all accounts. |
| `login.rsaModulus` | invalid until set | Decimal or `0x` hex string representing an integer greater than 1. |
| `login.rsaExponent` | invalid until set | Decimal or `0x` hex string representing an integer greater than 0. |
| `login.lowMemory` | `false` | Low-memory flag sent in the login packet. |

### Transports and TLS

Choose the port for the selected transport. A local engine normally serves WebSocket on port 80 on Windows or 8888 on Linux, and raw TCP on 43594. A deployed server may use different ports.

```jsonc
// Raw TCP: the WebSocket Origin and TLS settings do not apply.
"server": {"transport": "tcp", "host": "localhost", "port": 43594}
```

```jsonc
// Secure WebSocket: use the hostname covered by the server's certificate.
"server": {
    "transport": "wss",
    "host": "world.example.com",
    "port": 443,
    "origin": "https://world.example.com",
    "tlsCaFile": "SYSTEM"
}
```

These fragments replace the `server` member of the process config. `SYSTEM` uses the operating system's trust store. A path selects a PEM CA bundle. `NONE` disables certificate verification and produces a warning. An origin-restricted server requires the origin expected by its `WEB_ALLOWED_ORIGIN` setting.

### RSA public key

Read the public key from the server deployment, for example:

```sh
openssl rsa -pubin -in <server_path>/engine/data/config/public.pem -text -noout
```

For the modulus, join the colon-separated hexadecimal bytes, remove the formatting and prefix with `0x`. A leading sign-padding byte `00` can be omitted: `00:91:e3:80:...` becomes `0x91e380...`. The ellipsis here represents the remaining bytes; it is not part of the configured value. Copy the exponent as a quoted decimal string or `0x` hex string. Both values must match the server's key.

### Cache and navigation

| Key | Default | Purpose |
|---|---|---|
| `client.cacheDirectory` | `data/cache` | Nonempty path to the server's game cache. See [cache layouts](Requirements.md#cache-layout). |
| `client.navDirectory` | `data/nav` | Nonempty path to the world walker's data. The repository includes exported data; see [navigation notes](../data/nav/README.md). |
| `client.logLevel` | `info` | `verbose`, `info`, `warning` or `error`. |
| `client.logFile` | empty | Append plain log lines to this file as well as the console; empty disables the file log. The sample sets `rs2004-headless.log`. |

The cache is shared and loaded at startup. Changing only the revision number cannot convert a cache to another revision. Cache CRCs, the RSA key and the configured revision must all agree with the server.

## SOCKS5 proxy

| Key | Default | Rules |
|---|---|---|
| `proxy.host` | empty | Empty connects directly; otherwise the same hostname rules as `server.host`. |
| `proxy.port` | `1080` | 1–65535. |
| `proxy.username` | empty | Empty for no authentication, or 1–255 printable ASCII characters. |
| `proxy.password` | empty | Must be empty when username is empty; otherwise 1–255 printable ASCII characters. |

The proxy resolves the server hostname. Proxy settings apply to all three transports. Proxy credentials are not logged.

## Process scheduling and retries

All values below are integers except directory paths. Units are part of each key's name.

| Key under `scripting` | Default | Range and behavior |
|---|---|---|
| `accountsDirectory` | `accounts` | Nonempty path to account files. |
| `scriptsDirectory` | `scripts` | Nonempty path to scripts and imported modules. |
| `progressDirectory` | `progress` | Nonempty path to progress reports. |
| `callTimeoutMs` | `1000` | 10–60000; watchdog limit for a call into Python. |
| `pollIntervalMs` | `10` | 1–1000; longest main-loop wait between passes. |
| `loginIntervalSeconds` | `2` | 0–60; spacing between accounts' login attempts, including retries. |
| `killGraceSeconds` | `30` | 0–600; grace period after the first stop signal. |
| `connectAttempts` | `10` | 0–100; `0` allows one initial attempt and disables retries/reconnects, `100` retries temporary failures indefinitely. |
| `minRetryDelaySeconds` | `2` | 1–3600; initial retry wait. |
| `maxRetryDelaySeconds` | `30` | 1–3600 and at least the minimum; cap on doubled retry waits. |
| `reloginDelaySeconds` | `60` | 0–3600; wait before logging back in after an unexpected session end. |

For a fixed retry delay, set the minimum and maximum equal. See [retry behavior](Running.md#retries-and-reconnects) for how these waits interact.

## Account reference

The account file's stem is its log name: `accounts/main.jsonc` appears as `main`. To check a server without starting a bot, use:

```json
{
    "username": "myuser",
    "password": "mypass",
    "idleSeconds": 30
}
```

| Key | Default | Rules and behavior |
|---|---|---|
| `username` | required | 1–12 printable ASCII characters. |
| `password` | required | 1–20 printable ASCII characters. |
| `enabled` | `true` | `false` excludes the account from normal directory discovery. |
| `server` | process section | Optional replacement server section; see below. |
| `proxy` | process section | Optional replacement proxy section; see below. |
| `idleSeconds` | `0` | 0–86400; with no script, 0 idles until interrupted. |
| `randomEvents` | `true` | Enable automatic random-event solvers while scripting. |
| `stallMinutes` | `10` | 0–1440; 0 disables the script stall guard. |
| `runAuto` | `true` | Enable automatic run energy management. |
| `runEnergyMin` | `20` | 0–100; energy threshold for turning run back on. |
| `script` | absent | Absent or `null` logs in without a script. |
| `script.file` | required when scripting | Nonempty filename relative to `scripting.scriptsDirectory`. |
| `script.progressReportMinutes` | `0` | 0–1440; 0 disables reports. |
| `script.settings` | `{}` | A JSON object passed to the script. |

`--account accounts/main.jsonc` explicitly loads that file instead of directory discovery, including when its `enabled` value is `false`.

### Account overrides

An absent or `null` `server` or `proxy` section inherits the corresponding process section. An object replaces the **whole section**. Omitted fields in that object use built-in defaults, not values from `client.jsonc`.

```jsonc
// Members of an account file:
"server": {
    "transport": "wss",
    "host": "world2.example.com",
    "port": 443,
    "origin": "https://world2.example.com",
    "tlsCaFile": "SYSTEM"
},
"proxy": {"host": ""}
```

This account connects directly to another world. Specify `host` and `port` in a server override, and repeat any nondefault transport, origin or CA setting it needs. The process's login revision, RSA key and cache remain shared.

### Script settings and reports

With `BOT = define_bot(name='Fighter', ...)`, settings belong under the bot name:

```json
"script": {
    "file": "fighter.py",
    "progressReportMinutes": 20,
    "settings": {"Fighter": {"npc": "Chicken"}}
}
```

When the bot loads, declared missing settings are added to its object in the account file using their defaults. The name must match the bot definition exactly. A plain `loop()` script reads the entire `script.settings` object through `settings`, including `settings.get(...)`; it does not receive the bot-specific default insertion. See [typed settings](scripting/settings.md).

Reports require an `on_progress_report()` hook returning a dictionary. They are written to `<progressDirectory>/<account>.txt`; each run starts the report file afresh. See the [report format](scripting/console-and-messages.md#progress-reports).

## Troubleshooting configuration

| Symptom | Check |
|---|---|
| Config or cache file not found | Working directory and configured path; the config file's own folder is not the path base. |
| `invalid JSON at line ..., column ...` | Quoting, commas and Windows backslash escaping at the indicated location. |
| A field fails validation | Value type, range and unit in the tables above. The error names the field. |
| No enabled account files | Files must end in `.jsonc`, be in the immediate accounts directory and have `enabled` true. |
| WebSocket rejected or connection refused | Transport, port and expected origin; the engine TCP and WebSocket ports differ. |
| TLS verification fails | Server hostname, certificate trust and configured CA bundle. |
| Login rejected despite correct credentials | Server revision, RSA public key and cache from the same deployment. |
| Account override loses a setting | Repeat it in the replacement section; override objects do not merge. |
| Saving an account setting has no effect | Restart the client; `--watch` reloads Python source, not account configuration. |
