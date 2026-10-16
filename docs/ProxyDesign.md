# Proxy Design

Design and test plan for connecting through a SOCKS5 proxy. A `proxy` section in `client.jsonc` sends every account's connection through one proxy, and an account file's own `proxy` replaces it for that account, so each bot can have its own IP. Without either, the client connects directly, as today. Code style follows [CONVENTIONS.md](CONVENTIONS.md). It changes the config ([ConfigDesign.md](ConfigDesign.md)) and the WebSocket transport ([WebSocketDesign.md](WebSocketDesign.md)), and patches IXWebSocket the way `ports/pocketpy` patches pocketpy.

Reference sources:

- RFC 1928, SOCKS Protocol Version 5, and RFC 1929, Username/Password Authentication for SOCKS V5
- IXWebSocket 12.0.1: `IXSocketConnect.cpp`, `IXSocket.cpp`, `IXSocketOpenSSL.cpp`, `IXWebSocketHandshake.cpp` (`clientHandshake`), `IXWebSocketTransport.cpp` (`connectToUrl`) and `IXWebSocket.cpp` (`connect`). §4 was read from these
- curl's `lib/socks.c`: how a widely used client treats replies that bend the RFCs (§5)

---

## 1. Decisions

| Topic | Decision |
|---|---|
| Protocol | SOCKS5 only, with no authentication or with username and password (RFC 1929). Only the `CONNECT` command is used |
| Where it hooks in | IXWebSocket has no proxy support. An overlay port adds a connect hook to it: a function that replaces `SocketConnect::connect`, the call that opens the TCP connection. Everything after that call is unchanged, so TLS still checks the certificate against, and sends the name of, the host in the `wss://` URL |
| What the patch holds | Only the hook, which knows nothing about SOCKS. The protocol is our code, under CONVENTIONS and covered by tests |
| DNS | The server's host name is sent to the proxy, which resolves it, so no DNS lookup for the game server leaves this machine. An IPv4 literal is sent as an address. The proxy's own host is resolved locally, as it must be |
| Timeout and cancellation | IXWebSocket already passes the connect step a cancel check that is true once `handshakeTimeout` has passed or `Close()` was called. Every wait in the SOCKS5 exchange polls in 10 ms slices and checks it, as `SocketConnect::connectToAddress` does, so a stalled proxy times out and `Close()` works as before. The one `handshakeTimeout` covers the proxy connection, the SOCKS5 exchange and the WebSocket upgrade together |
| Config | A top-level `proxy` section in `client.jsonc`, and an optional `proxy` object in account files that replaces it. An empty `host` means a direct connection |
| Retries | A proxy failure is a failed connection attempt like any other. `GameClient` retries it with the usual backoff from its `RetrySchedule`, up to `scripting.connectAttempts`. Nothing new is needed |
| Errors | The SOCKS5 code throws `std::runtime_error`. The hook's lambda is the boundary into IXWebSocket: it catches the exception and returns IXWebSocket's `-1` and `errMsg` (CONVENTIONS §8, callbacks invoked by third-party code) |
| Platform code | Only `TcpConnection.cpp` calls the socket API, through `<ixwebsocket/IXNetSystem.h>`, as `NetSystem.cpp` already does (CONVENTIONS §9) |
| Secrets | `proxy.username` and `proxy.password` never appear in an exception message or a log line. The proxy's host and port may, as `server.url` does |
| Threading | The hook runs on IXWebSocket's I/O thread. It holds its own copy of the proxy settings and touches nothing else, so it needs no locking and doesn't log |

Rejected:

- **A local relay**: a loopback listener that the WebSocket connects to, forwarding through the proxy, with the URL rewritten to `127.0.0.1`. It needs no patch, but it breaks `wss`: the certificate would be checked against `127.0.0.1`, and the `Host` header would name it too.
- **The whole SOCKS5 client inside the patch.** It would be more third-party code to carry across IXWebSocket upgrades, outside our conventions and tests.
- **Replacing IXWebSocket** with our own WebSocket and TLS code. That is far more work than this feature.
- **A global or thread-local hook** in `SocketConnect`. Accounts in one process have different proxies, and the connect runs on a thread IXWebSocket creates, so only a hook on each `ix::WebSocket` can tell them apart.
- **The proxy inside `server`.** An account's `server` section replaces `client.jsonc`'s whole section ([ConfigDesign.md](ConfigDesign.md) §3, Account files). An account that changed world would silently lose the proxy, or have to repeat it.
- **A URL string**, such as `socks5://user:pass@host:1080`. The password would have to be percent-encoded and would sit inside a string that is easy to log whole. Separate keys follow the config's struct-per-section shape.
- **`"proxy": null` in an account file meaning a direct connection.** In an account file, `null` already means "use `client.jsonc`'s" for `server` and `script`. `{"host": ""}` turns the proxy off for one account instead.

Not included:

- HTTP `CONNECT` proxies, SOCKS4 and SOCKS4a. A `type` key with the default `"socks5"` can be added later without breaking existing files.
- Resolving the server's host locally (curl's `socks5://` as opposed to `socks5h://`).
- A server URL whose host is an IPv6 literal. It's sent as a name, which most proxies won't resolve. TODO: address type 4, if a server ever needs it.
- GSSAPI authentication, proxy chains, and choosing a proxy at random from a list.

---

## 2. Layout

```
rs2004-headless/
├── client.jsonc.sample                  the proxy section
├── accounts/example.jsonc.sample        a commented-out proxy override
├── ports/
│   └── ixwebsocket/
│       ├── vcpkg.json                   upstream's, unchanged
│       ├── portfile.cmake               upstream's, plus PATCHES
│       └── connect-function.patch
├── src/
│   ├── Config/
│   │   ├── ProxySettings_s.hpp          ProxySettings_s
│   │   ├── Config_s.hpp                 Config_s::proxy
│   │   ├── AccountConfig_s.hpp          the account key
│   │   ├── ConfigJson.cpp               the macros
│   │   ├── ConfigValidator.cpp          its rules
│   │   └── ConfigOverrides.cpp          ForAccount applies the proxy override too
│   ├── Game/GameClient.cpp              passes the proxy to Connect
│   └── Io/
│       ├── Socks5Handshake.hpp / .cpp   messages built and parsed; no I/O
│       ├── Socks5Connector.hpp / .cpp   Socks5Proxy_s, and the exchange over a TcpConnection
│       ├── TcpConnection.hpp / .cpp     an owned socket with cancellable sends and receives
│       └── WebSocketClient.hpp / .cpp   WebSocketOptions_s::proxy, and the hook
└── tests/
    ├── Support/Io/FakeSocks5Proxy.hpp / .cpp
    ├── Io/
    │   ├── Socks5HandshakeTests.cpp
    │   └── WebSocketClientTests.cpp     proxy cases
    ├── Config/
    │   ├── ConfigFileTests.cpp          proxy cases
    │   └── ConfigOverridesTests.cpp     the account override
    ├── Game/GameClientTests.cpp         a login through the proxy
    └── Accounts/AccountTests.cpp        an account through its own proxy
```

- `vcpkg-configuration.json` already lists `ports` as an overlay folder, so `ports/ixwebsocket` takes the place of the registry's port with no other change.
- The overlay copies `ports/ixwebsocket/` from microsoft/vcpkg at the `builtin-baseline` in `vcpkg.json` (`3cbc1db4d867ec83c89fba4c461321c11f78b5e3`), version 12.0.1, with the same features. The patch is part of the port's ABI hash, so the binary cache builds it afresh.
- The patch is a `.patch` file applied through `vcpkg_from_github(... PATCHES connect-function.patch)`, not `vcpkg_replace_string` as in `ports/pocketpy`. Pocketpy's edits each swap one line. This one adds declarations to three headers and their definitions, which a diff shows in context. A comment in `portfile.cmake` says why the patch exists.
- `Socks5Proxy_s` lives in `Socks5Connector.hpp`, the header of the class that uses it. `WebSocketClient.hpp` includes that header, because `WebSocketOptions_s` has a `Socks5Proxy_s` member.
- `ProxySettings_s` has a header of its own in `Config/`, since both `Config_s` and `AccountConfig_s` hold one, as with `ServerSettings_s`. It has the member names of `Socks5Proxy_s`, as `ServerSettings_s` mirrors `WebSocketOptions_s`.

---

## 3. Config

### `client.jsonc`

A new section after `server`. The default serialization ([ConfigDesign.md](ConfigDesign.md) §3) gains:

```jsonc
    "proxy": {
        "host": "",
        "port": 1080,
        "username": "",
        "password": ""
    },
```

`client.jsonc.sample` adds a comment above it: `// Optional SOCKS5 proxy for every account; an empty host connects directly.`

| Key | Type | Default | Rule |
|---|---|---|---|
| `proxy.host` | string | `""`: connect directly | Empty, or 1 to 255 printable ASCII characters with no spaces. A host name or an IP address |
| `proxy.port` | integer | `1080` | 1 to 65535 |
| `proxy.username` | string | `""`: no authentication | Empty, or 1 to 255 printable ASCII characters |
| `proxy.password` | string | `""` | 1 to 255 printable ASCII characters when `proxy.username` is set, and empty when it isn't |

- **The port is an `s32`**, as `connectAttempts` is, and becomes a `u16` only when `Socks5Proxy_s` is built. A `u16` member would wrap ([ConfigDesign.md](ConfigDesign.md) §3, Rules), so `70000` would read as port 4464 and pass.
- **255** is the length limit of RFC 1929's fields. The same limit on the host keeps the rule simple, although only the server's host goes into a SOCKS5 field.
- **Unused keys are still checked.** With an empty host, `port`, `username` and `password` are unused, but their rules still apply, as `server.tlsCaFile`'s does with a `ws` URL.
- **Printable ASCII** for the credentials, as for the account's own. RFC 1929 allows any bytes, but the symbols proxy providers use are all printable ASCII.
- `ConfigValidator` gains `MAX_PROXY_FIELD_LENGTH = 255` and `MAX_PORT = 65535`, and a `ValidateProxy(const ProxySettings_s&)` beside `ValidateServer`. `Validate` and `ValidateAccount` both call it, with the paths `proxy.host` and so on, as both call `ValidateServer` with `server.url`.

```cpp
struct ProxySettings_s
{
    // Empty connects directly.
    std::string host;
    s32 port = 1080;
    // Empty offers no authentication.
    std::string username;
    std::string password;
};

struct Config_s
{
    ServerSettings_s server;
    ProxySettings_s proxy;
    LoginSettings_s login;
    ClientSettings_s client;
    ScriptingSettings_s scripting;
};
```

```cpp
NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT(ProxySettings_s, host, port, username, password)
NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT(Config_s, server, proxy, login, client, scripting)
```

### Account files

| Key | Type | Default | Rule |
|---|---|---|---|
| `proxy` | object or `null` | none: `client.jsonc`'s | The keys and rules of `client.jsonc`'s `proxy` section. Replaces it for this account. `{"host": ""}` connects this account directly |

- **The object replaces the whole section**, as `server` does. A key it leaves out takes its default, not `client.jsonc`'s value. `{"host": "10.0.0.2"}` therefore means port 1080 and no authentication, even when `client.jsonc` sets a username.
- `AccountConfig_s` gains `std::optional<ProxySettings_s> proxy`, after `server`. `from_json` for `AccountConfig_s` reads it exactly as it reads `server`: missing or `null` leaves it empty, an object converts, and anything else throws `must be an object`.
- `accounts/example.jsonc.sample` gains, after the commented-out `server` line:

    ```jsonc
    // Uncomment to send this account through its own SOCKS5 proxy instead of client.jsonc's.
    // {"host": ""} connects it directly.
    // "proxy": {"host": "127.0.0.1", "port": 1080, "username": "user", "password": "pass"},
    ```

### Applying the override

`ConfigOverrides::ForAccount` applies both overrides with one copy of the config:

```cpp
std::shared_ptr<const Config_s> ConfigOverrides::ForAccount(std::shared_ptr<const Config_s> config, const AccountConfig_s& account)
{
    if (!account.server && !account.proxy)
    {
        return config;
    }

    auto own = *config;
    if (account.server)
    {
        own.server = *account.server;
    }

    if (account.proxy)
    {
        own.proxy = *account.proxy;
    }

    return std::make_shared<const Config_s>(std::move(own));
}
```

`GameClient` reads `m_config->proxy` and never sees where it came from.

---

## 4. The IXWebSocket connect hook

`connect-function.patch`, against IXWebSocket 12.0.1:

| File | Change |
|---|---|
| `IXSocket.h` | `using ConnectFunction = std::function<int(const std::string& host, int port, std::string& errMsg, const CancellationRequest& isCancellationRequested)>;`, the signature of `SocketConnect::connect`. `Socket` gains `void setConnectFunction(ConnectFunction connectFunction)`, a protected `int connectToHost(host, port, errMsg, isCancellationRequested)`, and a protected `ConnectFunction _connectFunction` |
| `IXSocket.cpp` | `connectToHost` calls `_connectFunction` when it's set, and `SocketConnect::connect` otherwise. `Socket::connect` calls `connectToHost` |
| `IXSocketOpenSSL.cpp`, `IXSocketMbedTLS.cpp`, `IXSocketAppleSSL.cpp` | Their `connect` calls `connectToHost` instead of `SocketConnect::connect`. Only OpenSSL is built, but changing all three keeps the hook working whichever TLS feature is chosen |
| `IXWebSocketTransport.h` / `.cpp` | `setConnectFunction` stores it. `connectToUrl` passes it to each socket it creates, right after `createSocket`, so a redirect goes through the proxy too |
| `IXWebSocket.h` / `.cpp` | `setConnectFunction` stores it with the other settings. `WebSocket::connect` passes it to the transport beside the client's `_ws.configure(...)` call |

- **No hook set, no change.** Every existing caller, including `ix::HttpClient` and the server classes, connects exactly as before.
- **The hook returns the socket in the state IXWebSocket expects:** connected, non-blocking and with `TCP_NODELAY`. `Socks5Connector` gets it from `ix::SocketConnect::connect`, which sets both, and returns it after the exchange.
- **The cancel check passed to the hook** is the one `clientHandshake` makes with `makeCancellationRequestWithTimeout(handshakeTimeout, _requestInitCancellation)`. It covers `handshakeTimeout` and `Close()`.
- **The error message reaches the user** through IXWebSocket's own: `Unable to connect to w1.example.com on port 443, error: SOCKS5 proxy 10.0.0.5:1080: host unreachable (reply 4)`. `WebSocketClient` reports it as the connection's failure reason, as it does any other.

---

## 5. Socks5Handshake

Builds the client's messages and parses the proxy's replies. It does no I/O, so its tests are byte arrays.

```cpp
#pragma once

enum class Socks5Method_e : u8
{
    NoAuthentication = 0x00,
    UsernamePassword = 0x02,
};

enum class Socks5AddressType_e : u8
{
    Ipv4 = 0x01,
    DomainName = 0x03,
    Ipv6 = 0x04,
};

class Socks5Handshake
{
public:
    static constexpr u8 VERSION = 0x05;
    static constexpr u8 PASSWORD_VERSION = 0x01;
    static constexpr u8 CONNECT_COMMAND = 0x01;
    static constexpr u8 NO_ACCEPTABLE_METHOD = 0xFF;
    static constexpr u8 SUCCEEDED = 0x00;
    static constexpr std::size_t METHOD_REPLY_SIZE = 2;
    static constexpr std::size_t PASSWORD_REPLY_SIZE = 2;
    static constexpr std::size_t CONNECT_REPLY_SIZE = 4;
    static constexpr std::size_t MAX_FIELD_LENGTH = 255;

    Socks5Handshake() = delete;

    [[nodiscard]] static std::vector<u8> BuildGreeting(bool withPassword);
    [[nodiscard]] static Socks5Method_e ParseMethodReply(std::span<const u8, METHOD_REPLY_SIZE> reply, bool withPassword);
    [[nodiscard]] static std::vector<u8> BuildPasswordRequest(std::string_view username, std::string_view password);
    static void ParsePasswordReply(std::span<const u8, PASSWORD_REPLY_SIZE> reply);
    // An IPv4 literal goes as an address, and any other host as a name for the proxy to resolve.
    [[nodiscard]] static std::vector<u8> BuildConnectRequest(std::string_view host, u16 port);
    [[nodiscard]] static Socks5AddressType_e ParseConnectReply(std::span<const u8, CONNECT_REPLY_SIZE> reply);
    // The bound address and port after the reply. domainLength is the byte after the reply, read only for a name.
    [[nodiscard]] static std::size_t GetBoundAddressSize(Socks5AddressType_e type, u8 domainLength);
};
```

| Message | Bytes |
|---|---|
| Greeting | `05 01 00`, or `05 02 00 02` with a username |
| Method reply | `05 MM` |
| Password request | `01 ULEN UNAME PLEN PASSWD` |
| Password reply | `VV SS`; `SS` = 0 is success |
| Connect request | `05 01 00 03 LEN HOST PORT`, or `05 01 00 01 A B C D PORT` for an IPv4 literal. The port is big-endian |
| Connect reply | `05 REP 00 ATYP`, then the bound address (4 bytes, 16 bytes, or a length byte and a name) and a 2-byte port |

- **Offering both methods with a username.** The proxy may choose no authentication. That's accepted, as curl accepts it.
- **Method reply errors.** A version other than 5 throws `not a SOCKS5 proxy`. `FF` throws `accepts none of the offered authentication methods`, adding `; it may need a username and password` when none was offered. A method that wasn't offered throws `chose an authentication method that wasn't offered`.
- **The password reply's version byte isn't checked**, only its status. Some proxies answer with 5 instead of RFC 1929's 1, and curl accepts them too. A status other than 0 throws `rejected the username or password`, without either value.
- **Connect reply errors.**
    - A version other than 5 throws.
    - A `REP` other than 0 throws its RFC 1928 meaning and the number, such as `host unreachable (reply 4)`. The names come from one `constexpr` table for codes 1 to 8, and other codes read `unknown reply (reply 9)`.
    - An `ATYP` other than 1, 3 or 4 throws.
- **IPv4 literals** are four decimal parts of 0 to 255, read with `std::from_chars`, with nothing else in the string. Anything else is a name.
- **Field lengths.** A name or credential that is empty or longer than 255 bytes throws `std::invalid_argument`. Config validation prevents it from a file, but the URL comes from the caller too.
- **The port** is written through `Endian::ToBig` (CONVENTIONS §9).
- **Messages** are lowercase without a trailing period, as everywhere else. They never contain the username or the password.

---

## 6. TcpConnection

Owns one connected, non-blocking socket, and sends and receives with waits that the cancel check can end. It is the only class that calls the socket API.

```cpp
#pragma once

#include <ixwebsocket/IXCancellationRequest.h>

// Not movable: Open returns a prvalue, so the guaranteed elision of C++17 is enough, and a move would only add a
// moved-from state to guard against.
class TcpConnection
{
public:
    [[nodiscard]] static TcpConnection Open(const std::string& host, u16 port, const ix::CancellationRequest& isCancelled);
    ~TcpConnection();

    TcpConnection(const TcpConnection&) = delete;
    TcpConnection& operator=(const TcpConnection&) = delete;

    void Send(std::span<const u8> bytes, const ix::CancellationRequest& isCancelled);
    // Fills all of destination, and never reads past it.
    void Receive(std::span<u8> destination, const ix::CancellationRequest& isCancelled);
    // The caller owns the socket afterwards, and closes it.
    [[nodiscard]] int Release() noexcept;

private:
    explicit TcpConnection(int socket);

    int m_socket;
};
```

- **`Open`** calls `ix::SocketConnect::connect`, which resolves the host, tries each address in turn, sets `TCP_NODELAY` and non-blocking mode, and honours the cancel check. It throws `std::runtime_error` with IXWebSocket's message when that fails.
- **`Send` and `Receive`** loop over `ix::Socket::poll(readyToRead, POLL_SLICE_MS, m_socket, nullptr)` with `POLL_SLICE_MS = 10`. They check `isCancelled` before each wait, and send or receive what the socket will take.
    - A would-block result (`ix::Socket::isWaitNeeded()`) waits again.
    - `recv` returning 0 throws `the proxy closed the connection`.
    - A socket error throws with `ix::Socket::getErrno()`'s code.
    - Cancellation throws `cancelled (timed out or closed)`.
- **`SEND_FLAGS`** is `MSG_NOSIGNAL` on Linux, so a proxy that hangs up can't kill the process with `SIGPIPE`, and 0 elsewhere. It is a `constexpr` in the anonymous namespace, chosen by `#ifdef __linux__` (CONVENTIONS §8, Preprocessor). IXWebSocket's own sends do the same.
- **The destructor** closes the socket with `ix::Socket::closeSocket` unless `Release` was called, which sets `m_socket` to -1.

---

## 7. Socks5Connector

```cpp
#pragma once

#include <ixwebsocket/IXCancellationRequest.h>

struct Socks5Proxy_s
{
    std::string host;
    u16 port = 1080;
    // Empty offers no authentication.
    std::string username;
    std::string password;
};

class Socks5Connector
{
public:
    Socks5Connector() = delete;

    // Runs on IXWebSocket's thread. The socket returned is connected to host through the proxy, and IXWebSocket owns it.
    [[nodiscard]] static int Open(const Socks5Proxy_s& proxy, const std::string& host, u16 port, const ix::CancellationRequest& isCancelled);
};
```

`Open`, with each step's reply read to its exact length, so not one byte of the TLS or WebSocket stream that follows is consumed:

1. `TcpConnection::Open(proxy.host, proxy.port, isCancelled)`.
2. Send `BuildGreeting(!proxy.username.empty())`, receive `METHOD_REPLY_SIZE` bytes, and `ParseMethodReply`.
3. If the method is `UsernamePassword`: send `BuildPasswordRequest`, receive `PASSWORD_REPLY_SIZE` bytes, and `ParsePasswordReply`.
4. Send `BuildConnectRequest(host, port)`, receive `CONNECT_REPLY_SIZE` bytes, and `ParseConnectReply`. For a name, receive its length byte. Then receive and discard `GetBoundAddressSize(...)` bytes.
5. `return connection.Release();`

Any throw on the way closes the socket through `TcpConnection`'s destructor.

---

## 8. Wiring

**`WebSocketOptions_s`** gains `std::optional<Socks5Proxy_s> proxy`.

**`WebSocketClient::Connect`:**

- **Checks.** With a proxy, an empty `host` or a zero `port` throws `std::invalid_argument`, beside the existing URL check.
- **The hook.** It's installed before `start()`, and captures a copy of the proxy:

    ```cpp
    if (options.proxy)
    {
        m_socket->setConnectFunction([proxy = *options.proxy](const std::string& host, int port, std::string& errMsg, const ix::CancellationRequest& isCancelled)
        {
            // IXWebSocket's thread: nothing may be thrown back into it.
            try
            {
                return Socks5Connector::Open(proxy, host, static_cast<u16>(port), isCancelled);
            }
            catch (const std::exception& e)
            {
                errMsg = std::format("SOCKS5 proxy {}:{}: {}", proxy.host, proxy.port, e.what());
                return -1;
            }
        });
    }
    ```

- **Logging.** The connect line becomes `WebSocket connecting to {url} through SOCKS5 proxy {host}:{port}` when there is a proxy, and is unchanged when there isn't. It runs on the owner thread, like the existing line. The credentials are never logged.

**`GameClient`'s connect** passes `.proxy = MakeProxy(m_config->proxy)` ([GameClient.cpp:396](../src/Game/GameClient.cpp#L396)). `MakeProxy`, in `GameClient.cpp`'s anonymous namespace, returns `std::nullopt` for an empty host, and otherwise copies the members, casting the validated port to `u16`.

**Every reconnect** builds a new `ix::WebSocket` with the same hook, so reconnects go through the proxy too.

**Docs.**

- [README.md](../README.md): a `proxy` row in the `client.jsonc` table, and a line in the account section beside the one about `server`.
- [ConfigDesign.md](ConfigDesign.md):
    - §3: the keys, the account row, and the default serialization.
    - §4: the interface.
    - §6: the cases.
- [WebSocketDesign.md](WebSocketDesign.md) §3: the option, the check, the hook, and the log line.

---

## 9. Test plan

All new cases are tagged `[Socks5]`. Those that open sockets are also tagged `[network]`, like the existing loopback cases.

### 9.1 FakeSocks5Proxy

A test helper in `tests/Io/`, built on `ix::SocketServer`, so the tests call no platform socket API. It takes a free loopback port with `LoopbackPort::IsFree`, as `FakeGameServer` does.

- **Settings.**
    - `SetCredentials(username, password)` requires those credentials; without it, only no authentication is offered.
    - `SetReply(code)` sets the connect reply, success by default.
    - `SetBoundAddress(type)` sets the address type of the success reply, IPv4 by default, so tests can make it send a name or an IPv6 address.
    - `SetStalled(true)` makes it accept the connection and never answer the greeting.
- **Records.** It records each connect request's address type, host and port, and the credentials each client sent.
- **Relaying.** After a success reply, it connects to the target with `ix::SocketConnect::connect` and relays bytes both ways until either side closes or the proxy stops.
- **`Url()`-style accessors** give its host and port.

### 9.2 Socks5HandshakeTests

| Case | Expected |
|---|---|
| Greeting with and without a username | `05 02 00 02` and `05 01 00` |
| Password request | `01 04 u s e r 04 p a s s`; 255-byte fields accepted. Empty or 256-byte fields throw, and the message has neither value |
| Connect request for `example.com:443` | `05 01 00 03 0B example.com 01 BB` |
| Connect request for `127.0.0.1:80` | `05 01 00 01 7F 00 00 01 00 50` |
| Hosts that look like, but aren't, IPv4 literals: `1.2.3`, `1.2.3.4.5`, `256.1.1.1`, `1.2.3.x`, ` 1.2.3.4` | Sent as names |
| Method replies `05 00`, and `05 02` with a username | `NoAuthentication`, `UsernamePassword` |
| Method replies `04 00`, `05 FF`, `05 02` without a username, `05 01` | Each throws its §5 message. `05 FF` without a username says a username and password may be needed |
| Password replies `01 00` and `05 00` | Accepted |
| Password reply `01 01` | Throws, without the credentials |
| Connect replies with `REP` 1 to 8, and 9 | Each throws its name and number |
| Connect replies with `ATYP` 1, 3 and 4 | Return the type. `ATYP` 2 throws. A version of 4 throws |
| `GetBoundAddressSize` | IPv4 6, IPv6 18, a name of length 7 gives 9 |

### 9.3 WebSocketClientTests

These run against the existing loopback WebSocket server, through `FakeSocks5Proxy`.

| Case | Expected |
|---|---|
| `ws://127.0.0.1` through the proxy, without credentials | Opens and exchanges data. The proxy recorded one IPv4 connect request to the server's port |
| `ws://localhost` through the proxy | Opens. The proxy recorded a name request for `localhost`, so the name was sent, not resolved locally |
| With credentials the proxy requires | Opens. The proxy recorded them |
| Wrong password | Fails. The failure reason contains `SOCKS5` and `rejected`. No log line and no reason contains the username or the password |
| The proxy replies `REP` 5 | Fails with `connection refused (reply 5)` |
| The proxy's success reply carries a name, or an IPv6 address | Opens and exchanges data, which shows the reply was read to its exact end |
| A stalled proxy, with a 1 s `handshakeTimeout` | Fails within about 1 s |
| `Close()` while the proxy is stalled, once the proxy has received the greeting | Returns within the usual close bound, not after the timeout. Waiting for the greeting keeps the case clear of the race in [WebSocketDesign.md](WebSocketDesign.md) §3, `Close`, where a cancellation made before the handshake starts is cleared |
| Nothing listening on the proxy port | Fails, and the reason names the proxy's host and port |
| `proxy` with an empty host, or port 0 | `Connect` throws `std::invalid_argument` |
| The connect log line | Names the proxy's host and port, and not its credentials |

### 9.4 ConfigFileTests

- **The sample.** `Serialize(Config_s{})` matches the new default serialization exactly.
- **Defaults.** A file without `proxy` has an empty host.
- **Accepted values.**
    - `proxy.host`: `""`, `127.0.0.1`, `proxy.example.com`, and 255 characters.
    - `proxy.port`: 1 and 65535.
    - Credentials of 1 and 255 characters.
- **Rejected values.** Each is a `ConfigError` containing the key's path.
    - `proxy.host`: a host with a space, 256 characters, `é`, and `5`.
    - `proxy.port`: 0, 65536, -1, `"1080"`, and `true`.
    - `proxy.username`: 256 characters.
    - `proxy.password`: a password without a username, a username without a password, and 256 characters.
- **Wrong types.** `"proxy": []`, and each key set to `null`.
- **Secrets.** No message from the rejected credentials, and no captured log entry, contains them.
- **Round trip.** `Parse(Serialize(...))` keeps all four members.
- **Account files.**
    - `proxy` missing, or `null`, leaves the account's proxy empty.
    - An object is read with its own defaults.
    - `"proxy": 5` throws containing `proxy`.
    - `{"host": "", ...}` is accepted.
    - A bad `proxy.port` in an account file throws containing `proxy.port`.

### 9.5 GameClientTests, ConfigOverridesTests and AccountTests

- **GameClient.** A login to `FakeGameServer` through `FakeSocks5Proxy` reaches the game. The proxy saw exactly one connection.
- **Proxy from `client.jsonc`.** An account with no override goes through `client.jsonc`'s proxy.
- **The account's own proxy.** An account with its own proxy goes through that one, and the `client.jsonc` proxy sees nothing.
- **Direct override.** An account with `{"host": ""}` connects directly while `client.jsonc` has a proxy.
- **Both overrides.** `ConfigOverrides::ForAccount` with both a `server` and a `proxy` override gives a config with both, and with neither returns the same config.

### 9.6 Done when

- **Tests.** All tests pass on `windows-debug` and `windows-release`, and on the `linux-*` presets, with zero warnings.
- **Live run.** One account logs in through a real SOCKS5 proxy, both to a `ws://` and to a `wss://` server. For example, use `ssh -D 1080` or microsocks, a scratch `client.jsonc` and `--account`.
    - Each log shows the proxy line.
    - The server sees the proxy's address.
    - A second account with `{"host": ""}` connects directly.

---

## 10. Implementation order

1. **Overlay port.**
    - Copy upstream's `ports/ixwebsocket` at the baseline and add `connect-function.patch`.
    - Build both presets. Every existing test passes unchanged, since no hook is set.
2. **`Socks5Handshake`**, with the §9.2 tests.
3. **`TcpConnection` and `Socks5Connector`.** Add `FakeSocks5Proxy`, `WebSocketOptions_s::proxy` and the hook in `WebSocketClient::Connect`, with the §9.3 tests.
4. **Config.**
    - `ProxySettings_s`, the macros, `ValidateProxy`, and the account key.
    - The samples, with the §9.4 tests.
5. **Wiring.**
    - `MakeProxy` in `GameClient` and the proxy in `ConfigOverrides::ForAccount`, with the §9.5 tests.
6. **Docs.** README, ConfigDesign and WebSocketDesign, as in §8. Then the live run in §9.6.

This plan doesn't depend on [RevisionDesign.md](RevisionDesign.md). Both add to `Config_s`, so whichever lands second updates the default serialization and the sample once more.
