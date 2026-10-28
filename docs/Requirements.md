# Requirements

[Back to README](../README.md) · [Features](Features.md) · [Configuration](Configuration.md) · [Running](Running.md) · [Building](Building.md)

## Choose a client build

Release archives are available from [GitHub releases](../../../releases). Extract the complete archive into a writable folder, keeping its directory structure. Choose the archive for your operating system and CPU architecture.

| Platform | Release architectures | Runtime requirements |
|---|---|---|
| Windows 10 or 11 | x64, x86 | The [Visual C++ redistributable](https://learn.microsoft.com/cpp/windows/latest-supported-vc-redist) matching the executable's architecture. An x86 client needs the x86 runtime even on x64 Windows. |
| Linux | x64, arm64 | glibc 2.38 or newer and libstdc++ providing `GLIBCXX_3.4.32` (GCC 13.2 or newer), such as Ubuntu 24.04 or later. |

The Linux release targets glibc systems. For another toolchain or runtime environment, use the [build guide](Building.md) and verify compatibility there. The build presets cover Windows MSVC and Linux Clang; other platforms do not have supplied presets.

A release archive includes the client, sample configuration files, example scripts, type stubs and navigation data. It does not contain the server's game cache or a configured account. The interpreter is embedded, so running bot scripts does not require CPython, pip, Node.js or a separate pocketpy installation.

## Gather server details

You need a compatible private server and the following values from its deployment:

| Detail | What to obtain |
|---|---|
| Revision | `289`, `274` or `225`. This selects the login and packet protocol for the whole process. |
| Endpoint | A hostname or IPv4 address, transport (`ws`, `wss` or `tcp`) and the corresponding port. |
| Origin | The expected WebSocket origin when the server restricts it. |
| RSA public key | The server's modulus and exponent, matching those used by its webclient. |
| Game cache | A copy from the same server deployment and revision. The client computes login CRCs from it. |
| Credentials | An account accepted by that server, with a username of 1–12 printable ASCII characters and password of 1–20. |

Use a hostname without a scheme, port or path: `localhost`, for example, rather than `ws://localhost:80`. IPv6 literals are not accepted by the configuration validator. See [transport configuration](Configuration.md#transports-and-tls) for examples.

Accounts using different revisions require separate processes. Per-account world overrides still use the process-wide RSA key and cache, so the target worlds must be compatible with them.

## Cache layout

| Revision | Typical source directory in the server | Client expects |
|---|---|---|
| 289 or 274 | `engine/data/pack` | `main_file_cache.dat` and `main_file_cache.idx0` through `main_file_cache.idx4`. |
| 225 | `engine/data/pack/client` | The archive files and `maps/` directory in the server's 225 layout. |

Set `client.cacheDirectory` to the directory holding those files. You can point to an existing directory or copy the files into `data/cache`. Preserve the layout; do not point at the parent of the directory containing the expected files. Cache and revision mismatches can reject login even when credentials and networking are correct.

The [configuration guide](Configuration.md#rsa-public-key) explains how to read the public key and prepare the configuration.

## Filesystem and network access

Run from the extracted release folder or repository root so the default relative paths resolve correctly. The executable's directory does not determine the working directory. The client needs to read its configuration, cache, navigation data and scripts, and write configured logs, progress reports and profiling reports. Bot settings defaults can also be written back to account files.

The selected game endpoint must be reachable. When using SOCKS5, the proxy must be reachable and able to resolve the server hostname. For `wss`, use the platform trust store or supply the CA bundle required by the server.

To confirm setup, start with one account without a `script` section. It will log in and report its surroundings every ten seconds; follow the [first-login walkthrough](Running.md#first-login).
