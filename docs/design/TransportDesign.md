# Transport Design

Plan for the client's network transport. Boost.Beast and Asio replace IXWebSocket, `server.url` becomes three keys (`transport`, `host`, `port`), and two features follow: raw TCP to the engine's node port, and SOCKS5 proxies. The work ships in three phases (§12):

1. Beast for `ws` and `wss`, with nothing new. Removes IXWebSocket.
2. Raw TCP (`tcp`).
3. SOCKS5, for all three transports.

All three phases are built.

This plan replaces two documents. WebSocketDesign.md describes the IXWebSocket transport built today; it is deleted when phase 1 lands. ProxyDesign.md planned SOCKS5 as a patch to IXWebSocket and was never built; its config, message and test decisions carry over into §2 and §9, and the file is deleted with this plan. Both stay readable in git history: where this plan says "WebSocketDesign §n", it means `git show 878e4dd:docs/WebSocketDesign.md`. Code style follows [CONVENTIONS.md](CONVENTIONS.md). The transport logs through `Logger` ([LoggerDesign.md](LoggerDesign.md)) and is configured through `ConfigFile` ([ConfigDesign.md](ConfigDesign.md)).

Reference sources:

- Boost 1.92 (the `builtin-baseline` in `vcpkg.json`): Asio's `io_context`, `co_spawn` and `ssl::stream`, and Beast's `websocket::stream`
- OpenSSL 3.6.5, from the same baseline
- RFC 6455 (WebSocket), RFC 1928 (SOCKS5), RFC 1929 (SOCKS5 username and password)
- [tcp-protocol-289.md](tcp-protocol-289.md), Endpoints and Transport, and [tcp-protocol-225.md](tcp-protocol-225.md): what the engine expects of a WebSocket client and a TCP client
- curl's `lib/socks.c`: how a widely used client treats replies that bend the RFCs (§9)

---

## 1. Decisions

| Topic | Decision |
|---|---|
| Library | Boost.Beast for WebSocket, over Boost.Asio for TCP and Asio's `ssl::stream` for TLS. IXWebSocket, `NetSystem` and `WebSocketUrl` are removed |
| Threading | One `NetLoop` (an `io_context`) runs every connection's I/O on the thread that runs it. No connection has a thread of its own. `AccountRunner` makes one loop and gives it to every account, so a packet for any account wakes the runner. A `GameClient` made on its own gets a loop of its own |
| Ownership | The owner holds a `Connection`, a handle that is neither copied nor moved. The I/O state lives in a `Link` that the handle and the link's pending handlers share. Destroying the handle starts a close, and the link finishes it on the loop while nothing waits. `GameClient`'s `m_closingSockets` goes away |
| Headers | No header that the rest of the code includes names an Asio, Beast or OpenSSL type. `NetLoop` and `Link` are abstract classes, and `AsioNetLoop` and `AsioLink` implement them in headers that only `Io/` `.cpp` files and the test servers include. That keeps `<winsock2.h>` and `<windows.h>` out of every file that includes `GameClient.hpp`, which IXWebSocket's headers bring in today |
| Config | `server.transport` (`ws` or `wss`; `tcp` from phase 2), `server.host` and `server.port` replace `server.url`. There is no URL to parse, so nothing replaces `ix::UrlParser`. `origin` and `tlsCaFile` stay |
| Connect sequence | One C++20 coroutine per link: resolve, TCP connect, the SOCKS5 exchange (phase 3), the TLS handshake (`wss`), then the WebSocket upgrade. Then it reads until the connection ends |
| Timeouts | Every bound is a timer the link owns. `connectTimeout` covers everything before the connection opens. `CLOSE_TIMEOUT` (1 s) bounds a close. Beast's own websocket timeouts stay off (their default), and the socket is a plain `tcp::socket`, not `beast::tcp_stream`. The server-silence timeout stays in `GameClient` |
| Closing | `Close()` never waits, in any state. During `Connecting` it cancels the attempt at once, which removes IXWebSocket's lost-cancellation race. From `Open` it sends a close frame and the link waits up to `CLOSE_TIMEOUT` for the peer's reply before it drops the socket |
| TLS | The peer's certificate is verified against `tlsCaFile`: a PEM bundle, `SYSTEM` or `NONE`. Asio's `host_name_verification` checks it against `server.host`, and SNI sends that name. On Windows, `SYSTEM` loads the Windows root store into OpenSSL, because OpenSSL's default paths are empty there. TLS 1.2 or newer |
| Framing | Unchanged. Incoming data is a byte stream that discards message boundaries. Each `Send` is exactly one binary WebSocket message. Over raw TCP, sends are written in order with no boundaries |
| Errors | `ConnectionError` reports failures and `ConnectionClosedError` (derived from it) a clean close. They replace `WebSocketError` and `WebSocketClosedError`. A timeout returns `false`. A short `Peek` or `Read` throws `std::out_of_range` |
| Logging | Lifecycle at `Info`, traffic and failures at `Verbose`, never `Warning` or `Error`: as before, the caller logs a failure where it handles it ([LoggerDesign.md](LoggerDesign.md) §4) |
| Proxy (phase 3) | ProxyDesign's decisions, without the patch: SOCKS5 with no authentication or a username and password, the server's name resolved by the proxy, a top-level `proxy` section that an account file can replace. The exchange is a step of the connect coroutine |
| Raw TCP (phase 2) | The same link without TLS or the upgrade. A peer's FIN is a clean close. `Close()` sends a FIN and waits up to `CLOSE_TIMEOUT` for the peer's |

Rejected:

- **Keeping IXWebSocket and patching it**, as ProxyDesign planned. It still needs a thread per connection, the mailbox between that thread and the owner, and a vendored patch to carry across upgrades, and it can't speak raw TCP at all.
- **Asio types in public headers.** Every file that includes `GameClient.hpp` would compile Asio and Beast, and with them `<winsock2.h>` and `<windows.h>`, which CONVENTIONS §4 keeps out of shared headers.
- **A pimpl.** It needs a forward declaration, which CONVENTIONS forbids.
- **A shared `std::shared_ptr<Connection>` for the owner.** An owner that dropped its pointer without closing would leave the connection open for as long as the loop runs. The `Connection` handle closes in its destructor.
- **A `server.url` key.** It needs a URL parser, and its parts can only be checked as a whole.
- **Beast's own timeouts** (`beast::tcp_stream`'s expiry, the websocket timeout option). They don't cover the lookup or the SOCKS5 exchange, so the link would need its own timers anyway. Two mechanisms for one bound would be one too many.
- **A loop per connection, on a thread of its own.** That brings back the hand-off between threads that this plan removes.
- **Callback chains for the connect sequence.** The coroutine reads in the order things happen, and a failure anywhere in it ends at one `catch`.
- **Asio's and Beast's separate compilation** (`BOOST_ASIO_SEPARATE_COMPILATION`). Only a handful of `.cpp` files include them, so the build cost is already contained. Revisit only if a measured build says so.

Not included:

- An IPv6 literal as `server.host` (§2). TODO: brackets in the `Host` header and SOCKS5 address type 4, if a server ever needs it.
- A WebSocket path other than `/`. Every engine serves `GET /`.
- Per-message deflate. The engine turns it off, and Beast leaves it off by default.
- A limit on the send queue. As before, TODO if a stalled server becomes a problem.
- Catching Ctrl+C with Asio's `signal_set`. The runner still checks the interrupt count once per pass, at least every `scripting.pollIntervalMs`.

---

## 2. Configuration

### `server`

```jsonc
"server": {
    // ws or wss. A local engine serves ws on port 80 on Windows, and on 8888 on Linux.
    "transport": "ws",
    "host": "localhost",
    "port": 80,
    "origin": "http://localhost",
    "tlsCaFile": "SYSTEM"
},
```

| Key | Type | Default | Rule |
|---|---|---|---|
| `server.transport` | string | `"ws"` | `ws` or `wss`; `tcp` from phase 2. Written exactly, in lowercase |
| `server.host` | string | `""` | 1 to 253 characters, each an ASCII letter, a digit, `-` or `.`: a host name or an IPv4 address. A scheme, a port, a path or a space all fail it |
| `server.port` | integer | `0` | 1 to 65535. It has no working default: the engine's WebSocket port depends on its platform |
| `server.origin` | string | `""`: no `Origin` header | Empty, or printable ASCII. WebSocket only. Unchanged |
| `server.tlsCaFile` | string | `"SYSTEM"` | Not empty: a PEM CA bundle's path, `SYSTEM` or `NONE`. `wss` only. Unchanged |

- **`ServerSettings_s`** becomes:

    ```cpp
    struct ServerSettings_s
    {
        Transport_e transport = Transport_e::Ws;
        std::string host;
        s32 port = 0;
        std::string origin;
        std::string tlsCaFile = "SYSTEM";
    };
    ```

- **The port is an `s32`**, as ProxyDesign decided for `proxy.port`, and becomes a `u16` only in `ConnectionOptions_s`. A `u16` member would wrap ([ConfigDesign.md](ConfigDesign.md) §3, Rules), so `70000` would read as port 4464 and pass.
- **`Transport_e`** lives in `Config/Transport_e.hpp`, because it is a setting that `Io/` reads, as `Revision_e` is for `Game/Protocol`. `TransportNames`, beside it, mirrors `LogLevelNames`: `CHOICES` (`"ws or wss"`, then `"ws, wss or tcp"`), `Find(std::string_view)` and `GetName(Transport_e)`.
- **It is read through an `adl_serializer<Transport_e>`** in `ConfigJson.cpp`, like `LogLevel_e`'s. An unknown name throws `must be ws or wss`, which `ConfigFile` reports as `server.transport: must be ws or wss`. `NLOHMANN_JSON_SERIALIZE_ENUM` isn't used: it turns an unknown string into the enum's first value without a word, so `"wws"` would quietly connect over `ws`.
- **`ValidateServer`** checks `host` with `IsHost`, a helper in `ConfigValidator`'s anonymous namespace that phase 3's `proxy.host` reuses, and `port` against `MAX_PORT = 65535`. `MAX_HOST_LENGTH = 253`, the longest DNS name.
- **Keys that don't apply are still checked** and then ignored: `origin` with `tcp`, and `tlsCaFile` with anything but `wss`. That matches how `tlsCaFile` already works with a `ws` URL.
- **`ConfigValidator::Warn`** warns when `transport` is `wss` and `tlsCaFile` is `NONE`, with the same message as today.
- **Account files.** `server` still replaces the whole section. An account's own world is now `"server": {"transport": "wss", "host": "w2.example.com", "port": 443, "origin": "https://w2.example.com"}`.
- **Old files.** The loader ignores keys it doesn't know, so a file that still has only `url` fails with `server.host: must be ...`, which names the key that's missing. `client.jsonc.sample` and `accounts/example.jsonc.sample` change in the repository. Untracked files (`client.jsonc`, `client225.jsonc`, `client274.jsonc` and the account files) are updated by hand.

`client.jsonc.sample`'s first line becomes `// Sample config. Copy it to client.jsonc, set server.host and server.port and the login RSA key, ...`, and `accounts/example.jsonc.sample`'s commented-out server line uses the new keys.

---

## 3. Layout and build

### Files, phase 1

```
rs2004-headless/
├── vcpkg.json                            boost-asio, boost-beast and openssl in place of ixwebsocket
├── CMakeLists.txt
├── client.jsonc.sample                   the new server keys
├── accounts/example.jsonc.sample
├── docs/
│   ├── TransportDesign.md                this plan
│   ├── ProxyDesign.md                    deleted with this plan
│   └── WebSocketDesign.md                deleted in phase 1
├── src/
│   ├── Config/
│   │   ├── Transport_e.hpp               new
│   │   ├── TransportNames.hpp / .cpp     new
│   │   ├── ServerSettings_s.hpp          transport, host, port in place of url
│   │   ├── ConfigJson.cpp                the Transport_e serializer, the macro
│   │   └── ConfigValidator.cpp           the server rules
│   ├── Console/ConsoleInput.hpp / .cpp   SetOnArrived in place of WaitUntil (§7)
│   ├── Game/
│   │   ├── GameClient.hpp / .cpp         a NetLoop, and a Connection in place of the sockets (§7)
│   │   └── Net/LoginHandshake.hpp / .cpp Advance takes a Connection
│   ├── Accounts/
│   │   ├── Account.hpp / .cpp            passes a NetLoop on to its GameClient
│   │   └── AccountRunner.hpp / .cpp      owns the shared NetLoop and waits on it
│   └── Io/
│       ├── NetLoop.hpp / .cpp            new: the abstract loop, and Create()
│       ├── AsioNetLoop.hpp / .cpp        new
│       ├── Connection.hpp / .cpp         new: the owner's handle
│       ├── ConnectionOptions_s.hpp       new
│       ├── Link.hpp / .cpp               new: one connection's state and received bytes
│       ├── AsioLink.hpp / .cpp           new: the socket, TLS and WebSocket
│       ├── ReceiveBuffer.hpp / .cpp      new: taken out of WebSocketClient
│       ├── TrustStore.hpp / .cpp         new: tlsCaFile into OpenSSL
│       ├── Error/ConnectionError.hpp     renamed from WebSocketError.hpp
│       ├── Error/ConnectionClosedError.hpp
│       ├── WebSocketClient.hpp / .cpp    deleted
│       ├── WebSocketUrl.hpp / .cpp       deleted
│       └── NetSystem.hpp / .cpp          deleted: Asio starts Winsock itself
└── tests/
    ├── Support/
    │   ├── Io/ServerThread.hpp / .cpp    new: an io_context on a thread of its own, for test servers
    │   ├── Io/TestCertificate.hpp / .cpp new: a self-signed certificate made at run time
    │   ├── Io/TestServer.hpp / .cpp      new: a scripted server, WebSocket (plain or TLS) or raw TCP, for ConnectionTests
    │   ├── Game/FakeGameServer.hpp / .cpp on Beast, over WebSocket or raw TCP
    │   └── LoopbackPort.hpp / .cpp       deleted: test servers bind port 0
    └── Io/
        ├── ConnectionTests.cpp           replaces WebSocketClientTests.cpp
        ├── ReceiveBufferTests.cpp        new
        ├── TrustStoreTests.cpp           new
        └── WebSocketUrlTests.cpp         deleted
```

- `ConnectionState_e` and `LinkStatus_s` live in `Link.hpp`, the header of the class that owns them. `Connection.hpp` includes it, because its member and its `Pump` name them.
- `NetLoop.hpp` includes `Link.hpp` and `ConnectionOptions_s.hpp`. `Connection.hpp` includes `NetLoop.hpp`. Nothing includes `Connection.hpp` from `Io/`, so there is no include cycle.
- `NetLoop::Create` is defined in `NetLoop.cpp`, which is the one file outside the `Asio*` pair that includes `AsioNetLoop.hpp`.
- The headers that name Asio, Beast or OpenSSL types are `AsioNetLoop.hpp`, `AsioLink.hpp` and `TrustStore.hpp`. They're included by `NetLoop.cpp`, `AsioNetLoop.cpp`, `AsioLink.cpp`, `TrustStore.cpp` and the test servers, and by nothing else.

### vcpkg and CMake

`vcpkg.json` drops `ixwebsocket` and gains `boost-asio`, `boost-beast` and `openssl`. `boost-beast` already depends on `boost-asio`, but the code includes Asio directly, so the manifest names both. `openssl` is named because the code calls OpenSSL itself, for SNI, the trust store and the test certificate.

```cmake
find_package(boost_asio CONFIG REQUIRED)
find_package(boost_beast CONFIG REQUIRED)
find_package(OpenSSL REQUIRED)

target_link_libraries(${PROJECT_NAME}Lib
    PUBLIC pocketpy::pocketpy
    PRIVATE Boost::asio Boost::beast OpenSSL::SSL OpenSSL::Crypto nlohmann_json::nlohmann_json BZip2::BZip2 ZLIB::ZLIB
            $<$<PLATFORM_ID:Windows>:crypt32>)

target_link_libraries(${PROJECT_NAME}Tests PRIVATE Boost::asio Boost::beast OpenSSL::SSL OpenSSL::Crypto)
```

- The targets and package names are what vcpkg's usage text gives for Boost 1.92; confirm them against the text it prints on install (CONVENTIONS §3).
- **Private, not public.** No public header includes Boost or OpenSSL now. The test executable links them itself for its servers.
- **`configure_project_target`** gains `BOOST_ASIO_NO_DEPRECATED`, and on Windows `_WIN32_WINNT=0x0A00` (Windows 10), which Asio otherwise warns about. MSVC also gets `/bigobj`, because a `.cpp` with Beast's templates and coroutines can exceed the default section count in Debug (Beast's own build sets it too).
- **Warnings.** Boost and OpenSSL come in through imported targets, so CMake passes their include directories as external, and MSVC's `/external:W0` keeps their warnings out of `/W4 /WX`. If a warning still escapes from an instantiation, it's silenced with a push and pop around the one `#include` that causes it, with a comment saying why.
- **`crypt32`** is for `TrustStore.cpp`'s Windows store calls.
- `pch.hpp` doesn't change. Boost stays out of it, since only a handful of files include it.

---

## 4. NetLoop

```cpp
#pragma once

#include "../Console/Logger.hpp"
#include "ConnectionOptions_s.hpp"
#include "Link.hpp"

// Every link a loop opens does its I/O on the thread that runs the loop: in Poll, Wait and Settle, and so in a
// Connection's Pump and waits. Wake is the only member another thread may call.
class NetLoop
{
public:
    using Clock = std::chrono::steady_clock;
    using Deadline = std::optional<Clock::time_point>;

    [[nodiscard]] static std::shared_ptr<NetLoop> Create();

    virtual ~NetLoop() = default;

    // Starts connecting and returns at once, Connecting. Connection's constructor is the caller.
    [[nodiscard]] virtual std::shared_ptr<Link> Open(const ConnectionOptions_s& options, std::shared_ptr<Logger> logger) = 0;
    // Runs what is ready, without waiting.
    virtual void Poll() = 0;
    // Waits until something happens or the deadline passes, then runs whatever is ready. Nullopt waits for something to happen.
    virtual void Wait(Deadline deadline) = 0;
    // Runs the loop until every link it opened has finished, or the deadline passes.
    virtual void Settle(Clock::time_point deadline) = 0;
    // Ends a Wait early. Safe from any thread.
    virtual void Wake() noexcept = 0;

protected:
    NetLoop() = default;
};
```

- **Shared ownership is real here.** `AccountRunner` and each of its accounts' `GameClient`s hold the same loop, and a `GameClient` made alone holds its own. So `GameClient` and `Account` take a `std::shared_ptr<NetLoop>` parameter that defaults to `NetLoop::Create()`, as their logger defaults to `Logger::GetDefault()`.
- **`Wait` returns after the first batch of handlers**, not at the deadline. A caller that waits for a condition re-checks it after every return, and every handler that could change any connection's state wakes it. That replaces the old event counter and condition variable, so there's nothing to lose a wakeup to.
- **`Wake`** posts an empty handler, which ends a `Wait` on the loop's thread. `ConsoleInput` calls it from its reader thread (§7).

### AsioNetLoop

```cpp
class AsioNetLoop : public NetLoop
{
public:
    AsioNetLoop();

    [[nodiscard]] std::shared_ptr<Link> Open(const ConnectionOptions_s& options, std::shared_ptr<Logger> logger) override;
    void Poll() override;
    void Wait(Deadline deadline) override;
    void Settle(Clock::time_point deadline) override;
    void Wake() noexcept override;

    // AsioLink's constructor and destructor, so Settle knows when every link has finished.
    void AddLink();
    void RemoveLink() noexcept;

private:
    std::size_t m_linkCount = 0;
    boost::asio::io_context m_io{1};
    boost::asio::executor_work_guard<boost::asio::io_context::executor_type> m_work;
};
```

- **`m_io{1}`** tells Asio that one thread runs the loop. `post` from another thread, which `Wake` uses, stays safe with that hint.
- **The work guard** keeps the loop from running out of work, so `Wait` blocks until the deadline even when no I/O is pending, and the loop never stops and never needs `restart()`.
- **`Wait`** is `m_io.run_one()` for no deadline, or `m_io.run_one_until(*deadline)`, followed by `m_io.poll()`. A deadline in the past makes it a `Poll`.
- **`Settle`** calls `Wait(deadline)` while `m_linkCount > 0` and the deadline hasn't passed.
- **`Wake`** is `boost::asio::post(m_io, [] {})`, inside a `try`, because `post` may allocate and `Wake` is `noexcept`.
- **No handler throws.** Every completion handler and the coroutine's completion catch what they must (§6), so `run_one`, `run_one_until` and `poll` never rethrow. A handler that threw would be a bug, and the completion handlers assert that none did.
- **Member order matters, and gets a "why" comment.** `m_work` is destroyed first, while `m_io` still exists. Destroying `m_io` destroys the handlers that keep lingering links alive, without calling them. Each link's destructor then counts down `m_linkCount`, which is declared first so that it's still there.
- **What destruction does to lingering links.** A link still closing when its loop is destroyed loses its sockets in the handlers' destructors: the peer sees the TCP connection end without a close frame. Only a loop that dies with links still in flight does this. `AccountRunner` calls `Settle` before it returns (§7), so a normal run closes cleanly.

---

## 5. Connection and Link

### Connection

```cpp
#pragma once

#include "../Console/Logger.hpp"
#include "ConnectionOptions_s.hpp"
#include "Link.hpp"
#include "NetLoop.hpp"

// The owner's handle on one connection. Constructing it starts connecting. Destroying it closes the connection,
// and the close finishes on the loop without anything waiting for it. Bytes and state change only while the loop
// runs: in Pump or a wait, in another connection's, or in the loop's own Poll, Wait or Settle.
class Connection
{
public:
    Connection(NetLoop& loop, const ConnectionOptions_s& options, std::shared_ptr<Logger> logger);
    ~Connection();

    Connection(const Connection&) = delete;
    Connection& operator=(const Connection&) = delete;

    void Close() noexcept;
    void Send(std::span<const u8> data);
    ConnectionState_e Pump();

    [[nodiscard]] std::size_t Available() const;
    void Peek(std::span<u8> destination) const;
    std::span<u8> Read(std::span<u8> destination);

    void WaitAvailable(std::size_t count);
    [[nodiscard]] bool WaitAvailable(std::size_t count, std::chrono::milliseconds timeout);
    void WaitOpen();
    [[nodiscard]] bool WaitOpen(std::chrono::milliseconds timeout);
    void WaitClosed();
    [[nodiscard]] bool WaitClosed(std::chrono::milliseconds timeout);

private:
    bool WaitAvailableUntil(std::size_t count, NetLoop::Deadline deadline);
    bool WaitOpenUntil(NetLoop::Deadline deadline);
    bool WaitClosedUntil(NetLoop::Deadline deadline);

    NetLoop& m_loop;
    std::shared_ptr<Link> m_link;
};
```

`ConnectionOptions_s`, in its own header since both `NetLoop` and `Connection` take it:

```cpp
#pragma once

#include "../Config/Transport_e.hpp"

struct ConnectionOptions_s
{
    Transport_e transport = Transport_e::Ws;
    std::string host;
    u16 port = 0;
    // WebSocket only. Empty sends no Origin header.
    std::string origin;
    // wss only: a PEM bundle's path, SYSTEM or NONE.
    std::string tlsCaFile = "SYSTEM";
    std::string subprotocol = "binary";
    // Everything before the connection opens: the lookup, the TCP connect, TLS and the upgrade.
    std::chrono::milliseconds connectTimeout = 10s;
};
```

**Behaviour.** What isn't listed here works as WebSocketDesign §3 specified, with `Connection` in place of `WebSocketClient`.

- **The constructor** checks the options and throws `std::invalid_argument` naming the field: an empty `host`, a zero `port`, a `connectTimeout` that isn't positive, or an empty `tlsCaFile` with `wss`. Then it calls `m_loop.Open(...)`. There's no `Connect` method: a new connection is a new `Connection`, so `GameClient` holds a `std::optional<Connection>` and calls `emplace` for each attempt.
- **The loop must outlive the handle.** `GameClient` declares its `std::shared_ptr<NetLoop>` before the connection. The link may outlive both handle and owner; it holds only what its handlers need (§6).
- **`~Connection`** calls `Close()`. That never waits, so destroying a handle never waits either. `Stop()` is gone: closing and then waiting is `Close()` and `WaitClosed`, or nothing at all.
- **`Pump`** runs `m_loop.Poll()`, then throws `ConnectionError` if the link has failed, or returns its state. As before, it throws on every call until `Close()`, and a clean close returns `Closed` without throwing.
- **`Pump` runs every connection's handlers, not just its own.** That is harmless: a handler only touches its own link's state and buffer, and never calls into a `Connection`, `GameClient` or script. This rule is what makes the shared loop safe, and §6 keeps it.
- **The waits** keep their meanings, timeouts and edge cases: `timeout <= 0` polls once, a timeout too large for the clock saturates to forever (`MakeDeadline` as today), success comes first in `WaitAvailable`, `WaitClosed` never throws `ConnectionClosedError`, and a timeout changes nothing. Each loop checks its condition, then `ThrowIfEnded`, then the deadline, then calls `m_loop.Wait(deadline)`. The condition variable, the event counter and the mailbox are gone.
- **`Close`** is `noexcept`, never waits, and can be called in any state, any number of times. It forgets any failure, so `Close()` followed by `WaitClosed` never throws. Bytes already received stay readable, and nothing more is received after it.
- **`Send`** polls the loop first, then throws if the connection has ended (as `ThrowIfEnded`) and asserts that it isn't `Connecting`, as before. The poll keeps the old promise that a send reports a peer's close without a pump first; IXWebSocket's thread kept the state live for it. It never waits on the network: the bytes go on the link's queue (§6).
- **`Available`, `Peek` and `Read`** go to the link's `ReceiveBuffer`. Nothing arrives between two of these calls, because nothing runs the loop between them.

### Link

```cpp
#pragma once

#include "ReceiveBuffer.hpp"

enum class ConnectionState_e : u8
{
    Connecting,
    Open,
    Closing,
    Closed,
};

struct LinkStatus_s
{
    ConnectionState_e state = ConnectionState_e::Connecting;
    bool failed = false;
    std::string reason;
};

// One connection's I/O side and what it has received. Its pending handlers share it with its Connection, so it
// can finish closing after the Connection is gone.
class Link
{
public:
    virtual ~Link() = default;

    Link(const Link&) = delete;
    Link& operator=(const Link&) = delete;

    virtual void Close() noexcept = 0;
    virtual void Send(std::span<const u8> data) = 0;

    [[nodiscard]] const LinkStatus_s& GetStatus() const;
    [[nodiscard]] ReceiveBuffer& GetReceived();

protected:
    Link() = default;

    void MarkOpen();
    void MarkClosing();
    void MarkFailed(std::string reason);
    void MarkEnded(std::string reason);
    void MarkClosed();
    void ForgetFailure();
    void Receive(std::span<const u8> bytes);

private:
    LinkStatus_s m_status;
    ReceiveBuffer m_received;
};
```

The transitions, which `Link.cpp` enforces so `AsioLink` can call them without checking the state first:

| Call | From | Effect |
|---|---|---|
| `MarkOpen` | `Connecting` | → `Open` |
| `MarkClosing` | `Connecting`, `Open` | → `Closing`, clean, reason `Connection closed` |
| `MarkFailed(reason)` | `Connecting`, `Open` | → `Closing`, failed, with the reason |
| `MarkEnded(reason)` | `Open` | → `Closing`, clean, with the peer's reason |
| `MarkClosed` | any | → `Closed`, keeping `failed` and the reason |
| `ForgetFailure` | any | `failed` cleared and the reason set to `Connection closed` |
| `Receive(bytes)` | `Open` | Appended to the buffer |
| Any other call, or any call from another state | | Ignored: the first ending wins |

- **`Closed` means the link's coroutine has finished**, so nothing more will be read. A write still in flight completes on its own and changes nothing. The link object itself goes away when its last handler finishes and its `Connection` is gone.
- **`Closing` is brief for an ending the peer causes.** `MarkFailed` or `MarkEnded` from the read loop is followed by `MarkClosed` in the same handler, as the coroutine returns.

### ReceiveBuffer

`WebSocketClient`'s receive buffer, moved out unchanged: `Append`, `Available`, `Peek` and `Read`, with lazy compaction at `COMPACT_THRESHOLD` (4096). `Clear` goes, because a new connection gets a new buffer. Its tests are WebSocketDesign §6.2's, against `ReceiveBuffer` instead of a client that never connected.

### Errors

| Situation | Reported by | As | Message |
|---|---|---|---|
| After `Close()` | `WaitAvailable`, `WaitOpen`, `Send` | `ConnectionClosedError` | `Connection closed` |
| The peer closed the WebSocket | Those three | `ConnectionClosedError` | `Server closed the connection (code 1000: ...)` |
| The peer ended TCP without a close frame, or with a FIN over `tcp` | Those three | `ConnectionClosedError` | `Server closed the connection without a close frame`, or over `tcp`, `Server closed the connection` |
| A step before open failed | `Pump`, all waits, `Send` | `ConnectionError` | `{step} failed: {message}`, such as `Looking up w1.example.com failed: No such host is known` or `TLS handshake failed: certificate verify failed (unable to get local issuer certificate)` |
| The upgrade was refused | Those | `ConnectionError` | `WebSocket upgrade refused (HTTP 403)` |
| `connectTimeout` passed | Those | `ConnectionError` | `Timed out after 10000 ms during the TLS handshake` |
| A text message arrived | Those | `ConnectionError` | `Received a text message` |
| A read or write failed after open | Those | `ConnectionError` | `Read failed: {message}` or `Send failed: {message}` |
| Bad options | The constructor | `std::invalid_argument` | Names the field |
| Short `Peek` or `Read` | `Peek`, `Read` | `std::out_of_range` | Requested and available counts |
| A wait timed out | All waits | Returns `false` | |

- `{message}` is the `boost::system::error_code`'s own message. On Windows that is the system's text.
- `ConnectionError` derives from `std::runtime_error`, and `ConnectionClosedError` from `ConnectionError`, so `GameClient`'s `catch (const std::runtime_error&)` around a login attempt still covers them.
- No message contains a credential. Phase 3 keeps the proxy's credentials out of them too (§9).

---

## 6. AsioLink

```cpp
#pragma once

#include "../Console/Logger.hpp"
#include "AsioNetLoop.hpp"
#include "ConnectionOptions_s.hpp"
#include "Link.hpp"

#include <boost/asio/awaitable.hpp>
#include <boost/asio/io_context.hpp>
#include <boost/asio/ip/tcp.hpp>
#include <boost/asio/ssl/context.hpp>
#include <boost/asio/ssl/stream.hpp>
#include <boost/asio/steady_timer.hpp>
#include <boost/beast/core/flat_buffer.hpp>
#include <boost/beast/websocket/stream.hpp>

class AsioLink : public Link, public std::enable_shared_from_this<AsioLink>
{
public:
    AsioLink(AsioNetLoop& loop, boost::asio::io_context& io, ConnectionOptions_s options, std::shared_ptr<Logger> logger);
    ~AsioLink() override;

    // Not in the constructor: the coroutine holds a shared_ptr to the link, which shared_from_this can't give yet.
    void Start();
    void Close() noexcept override;
    void Send(std::span<const u8> data) override;

private:
    using PlainWebSocket = boost::beast::websocket::stream<boost::asio::ip::tcp::socket>;
    using SecureWebSocket = boost::beast::websocket::stream<boost::asio::ssl::stream<boost::asio::ip::tcp::socket>>;

    static boost::asio::awaitable<void> Run(std::shared_ptr<AsioLink> self);
    template <typename TSocket>
    boost::asio::awaitable<void> RunWebSocket(TSocket& socket);
    void StartWrite();
    void OnWrite(boost::system::error_code error);
    void StartClose();
    void ArmTimer(std::chrono::milliseconds timeout, std::string_view stage);
    void Abort() noexcept;

    AsioNetLoop& m_loop;
    ConnectionOptions_s m_options;
    std::shared_ptr<Logger> m_logger;
    boost::asio::ip::tcp::resolver m_resolver;
    boost::asio::steady_timer m_timer;
    std::string_view m_stage;
    // Before the socket, which holds a reference to it.
    std::optional<boost::asio::ssl::context> m_tls;
    std::variant<PlainWebSocket, SecureWebSocket> m_socket;
    boost::beast::flat_buffer m_frame;
    std::deque<std::vector<u8>> m_outgoing;
    bool m_writing = false;
};
```

`AsioNetLoop::Open` makes the link with `std::make_shared`, calls `Start()`, and returns it. The constructor builds `m_tls` (for `wss`, through `TrustStore`, §6.3) and the socket alternative that `transport` names, and calls `m_loop.AddLink()`. The destructor calls `RemoveLink()`.

### 6.1 Lifetime

- **The coroutine holds the link.** `Start` calls `co_spawn(io, Run(shared_from_this()), ...)`. `Run` is a static coroutine whose `std::shared_ptr<AsioLink>` parameter is copied into the coroutine frame, so the link outlives every suspension. A member coroutine called on `this`, or a lambda capture, would leave that to luck; this gets a "why" comment.
- **Every completion handler holds the link too**, capturing `self = shared_from_this()`. Asio requires a socket's buffers to stay valid until each pending operation's handler runs, even after a close, because Windows overlapped I/O may still write to them. Holding the link holds `m_frame` and `m_outgoing`.
- **The co_spawn completion** takes the `std::exception_ptr` and asserts it's null, because `Run` catches everything itself.
- **The handlers' rule** (§5): they touch only this link and its logger. They never call into a `Connection`, a `GameClient` or a script.

### 6.2 The connect sequence

`Run`:

```cpp
boost::asio::awaitable<void> AsioLink::Run(std::shared_ptr<AsioLink> self)
{
    try
    {
        if (auto* plain = std::get_if<PlainWebSocket>(&self->m_socket))
        {
            co_await self->RunWebSocket(*plain);
        }
        else
        {
            co_await self->RunWebSocket(std::get<SecureWebSocket>(self->m_socket));
        }
    }
    catch (const std::exception& e)
    {
        self->MarkFailed(e.what());
        self->Abort();
    }

    self->m_timer.cancel();
    self->MarkClosed();
}
```

The variant is resolved once here, so the rest is a function template over the socket type, with `if constexpr` for the TLS steps. Phase 2 adds a third alternative and a third branch (§8).

`RunWebSocket` runs these steps in order. Each awaits with `as_tuple(use_awaitable)`, so it gets an `error_code` instead of an exception. After each, it checks the state first: if `Close()` has made it `Closing`, the error is the cancellation it caused, and the coroutine `co_return`s without a failure. Otherwise a non-zero code throws `ConnectionError{"{step} failed: {message}"}`, which ends at `Run`'s `catch`.

1. **Log** `Connecting to {transport}://{host}:{port}` at `Info`, and `ArmTimer(connectTimeout, ...)` for the whole sequence. When the timer fires during `Connecting`, it calls `MarkFailed("Timed out after {n} ms {stage}")` and `Abort()`. `m_stage` names the step it's on: `looking up the host`, `connecting`, `during the TLS handshake`, `during the WebSocket upgrade`, and in phase 3, `during the SOCKS5 exchange`.
2. **Look up** `host` and `port` with `m_resolver.async_resolve`. Step name `Looking up {host}`.
3. **Connect** with `boost::asio::async_connect` over the results, which tries each address in turn, then set `tcp::no_delay`. Step name `Connecting to {host}:{port}`.
4. **TLS**, `wss` only:
    - Set SNI with `SSL_set_tlsext_host_name(native_handle, host)`. It returns 1 on success; anything else throws.
    - Unless `tlsCaFile` is `NONE`, set the verify callback to `boost::asio::ssl::host_name_verification(host)`, so the certificate must name `host`.
    - `async_handshake(client)`. Step name `TLS handshake`. When it fails on verification, the message gets the reason from `X509_verify_cert_error_string(SSL_get_verify_result(...))` in parentheses, because OpenSSL's own message only says `certificate verify failed`.
5. **The WebSocket upgrade:**
    - A decorator sets `Sec-WebSocket-Protocol` to `subprotocol`, and `Origin` when it isn't empty. With an empty origin, no `Origin` header is sent at all, which is what the README has always said and IXWebSocket couldn't do.
    - The `Host` header is `host` for the transport's default port (80 for `ws`, 443 for `wss`), and `host:port` otherwise, as browsers send it.
    - `binary(true)`, so every write is a binary message.
    - `async_handshake(response, hostHeader, "/")`. Step name `WebSocket upgrade`. Beast's `websocket::error::upgrade_declined` becomes `WebSocket upgrade refused (HTTP {status})`, from `response`.
6. **Open:** cancel the timer, `MarkOpen()`, log `Connection open` at `Info`.
7. **The read loop** (§6.4).

### 6.3 TrustStore

```cpp
#pragma once

#include <boost/asio/ssl/context.hpp>

class TrustStore
{
public:
    TrustStore() = delete;

    // SYSTEM trusts the platform's roots, NONE verifies nothing, and anything else is a PEM bundle's path.
    static void Configure(boost::asio::ssl::context& context, const std::string& caFile);
    // How many roots it added: the Windows store's count, or 0 where OpenSSL finds them itself.
    [[nodiscard]] static std::size_t LoadSystemRoots(boost::asio::ssl::context& context);
};
```

- **The context** is `ssl::context{ssl::context::tls_client}` with `SSL_CTX_set_min_proto_version(..., TLS1_2_VERSION)`. Each `wss` link makes its own. A reconnect is rare enough that sharing one isn't worth the bookkeeping.
- **`NONE`**: `verify_none`. **A path**: `load_verify_file`, which throws if it can't, ending the attempt with that message. **`SYSTEM`**: `verify_peer` and `LoadSystemRoots`.
- **`LoadSystemRoots` on Windows** opens the current user's `ROOT` system store read-only (`CertOpenStore` with `CERT_SYSTEM_STORE_CURRENT_USER`, which includes the machine's roots), converts each certificate with `d2i_X509`, and adds it to the context's `X509_STORE`. A certificate the store already has is skipped. No roots at all throws `found no root certificates in the Windows store`. Elsewhere it calls `set_default_verify_paths()` and returns 0.
- **The Windows store fills in lazily.** Windows fetches some roots only when its own certificate code first needs them, so a root that no browser on the machine has used yet may be missing. The failure then reads `... (unable to get local issuer certificate)`. The fix is a PEM bundle in `tlsCaFile`. IXWebSocket loaded the store the same way and had the same gap.
- **Platform code.** Only `TrustStore.cpp` includes `<windows.h>` and `<wincrypt.h>`, under `#ifdef _WIN32` (CONVENTIONS §9).

### 6.4 Reading

```cpp
while (true)
{
    const auto [error, size] = co_await socket.async_read(m_frame, as_tuple(use_awaitable));
    if (error)
    {
        EndRead(error);
        co_return;
    }

    if (!socket.got_binary())
    {
        // The protocol is binary, so a text frame means the wrong endpoint.
        MarkFailed("Received a text message");
        StartClose(close_code::unknown_data);
        continue;
    }

    m_logger->Verbose("Received {} bytes", size);
    Receive(...m_frame's bytes...);
    m_frame.consume(size);
}
```

- **Reading continues while `Closing`**, because the peer's reply to a close frame arrives through it. `Receive` drops data while `Closing`.
- **`EndRead`** maps the ending:

    | Error | In state | Effect |
    |---|---|---|
    | `websocket::error::closed` (the peer's close frame) | `Open` | `MarkEnded("Server closed the connection (code {code}: {reason})")`, from `socket.reason()`. Beast answers the close frame itself |
    | `asio::error::eof`, or `ssl::error::stream_truncated` (TCP ended without a close frame or TLS close_notify) | `Open` | `MarkEnded("Server closed the connection without a close frame")`. IXWebSocket reported this as a clean close too |
    | Anything else | `Open` | `MarkFailed("Read failed: {message}")` |
    | Anything | `Closing` | Nothing: the close has finished, or `Abort` ended it |

  `Run` then calls `MarkClosed`.
- **Beast answers pings** while a read is pending, so a server that pings is kept happy without code here.
- **Message size.** Beast's default `read_message_max` (16 MiB) stays. The engine's messages are far smaller.

### 6.5 Writing

- **`Send`** logs `Sending {n} bytes` at `Verbose`, copies the bytes onto `m_outgoing`, and calls `StartWrite()` unless a write is in flight.
- **`StartWrite`** sets `m_writing` and starts `async_write` of the front item, with a handler that holds the link and calls `OnWrite`. Beast allows only one write in flight, which the queue enforces.
- **`OnWrite`** clears `m_writing`. On an error while `Open`, it calls `MarkFailed("Send failed: {message}")` and `Abort()`, and the read loop then ends. Otherwise it pops the front and, while `Open` and the queue isn't empty, starts the next.
- **One `Send` is one binary message**, as before.

### 6.6 Closing

`Close()`:

| State | Effect |
|---|---|
| `Connecting` | `MarkClosing()`, log `Connection closing` at `Info`, `Abort()`. The step in progress completes with `operation_aborted`, the coroutine sees `Closing` and returns, and the link is `Closed`. This happens on the next pump, with no network wait |
| `Open` | `MarkClosing()`, log `Connection closing`, then `StartClose(close_code::normal)` |
| `Closing`, `Closed` | Only `ForgetFailure()` |

- **`StartClose(code)`** drops the queued writes that haven't started, starts `socket.async_close(code)`, and arms the timer for `CLOSE_TIMEOUT` (1 s). Beast lets the close run alongside the pending read and a write already in flight. The read loop ends once the peer's close frame arrives and Beast has torn the connection down. If the timer fires first, `Abort()` drops the socket, and the read ends with an error that changes nothing because the state is `Closing`.
- **`Abort()`** cancels the resolver and the timer and closes the lowest-layer socket, ignoring errors. It's `noexcept` and safe to call repeatedly.
- **A text message** closes with 1003 (unsupported data) through the same `StartClose`. Its failure is kept, so `Pump` throws `Received a text message` until the owner calls `Close()`.
- **`CLOSE_TIMEOUT`** is a `constexpr` in `AsioLink.cpp`. IXWebSocket waited about 300 ms. A second covers a TLS shutdown to a distant server, and nobody waits for it.

### 6.7 Logging

| Where | Level | Message |
|---|---|---|
| The sequence starts | `Info` | `Connecting to {transport}://{host}:{port}` |
| Open | `Info` | `Connection open` |
| `Close()` from `Connecting` or `Open` | `Info` | `Connection closing` |
| The peer ended it | `Info` | The `MarkEnded` reason, such as `Server closed the connection (code 1000: )` |
| A failure | `Verbose` | `Connection failed: {reason}`, once, when `MarkFailed` takes effect |
| `Send` | `Verbose` | `Sending {n} bytes` |
| A binary message | `Verbose` | `Received {n} bytes` |
| A text message | `Verbose` | `Received a {n}-byte text message` |

- **Lines come before what they cause.** `Connecting to` is logged before the lookup starts, `Connection closing` before the close frame is sent, and each event's line before the state changes that a wait could return on. When a wait returns, the line for what satisfied it is already in the log.
- **No `Warning` or `Error`.** A failure reaches the owner through `Pump` or a wait, and `GameClient` logs it where it handles it, as today.
- **Byte counts, never bytes.** The login block carries the password.

---

## 7. Wiring

### GameClient

- **Members.** `std::shared_ptr<NetLoop> m_net` is declared before `std::optional<Connection> m_connection`, which replaces `m_socket`. `m_closingSockets`, `ReleaseSocket`'s swap, `FreeClosedSockets` and the anonymous `IsClosed` are deleted: closing is `m_connection.reset()`.
- **The constructor** gains `std::shared_ptr<NetLoop> net = NetLoop::Create()` as its last parameter.
- **`StartAttempt`** does `m_connection.reset()`, then `m_connection.emplace(*m_net, MakeOptions(m_config->server), m_logger)`. `MakeOptions`, in the anonymous namespace, copies the server settings and casts the validated port to `u16`.
- **The retry wait.** `PumpConnecting`'s `std::this_thread::sleep_for` becomes `m_net->Wait(Clock::now() + std::min(maxWait, remaining))`, so a close still in progress keeps moving while a retry is due.
- **Names.** `WebSocketError` becomes `ConnectionError`, `WebSocketState_e` becomes `ConnectionState_e`, and `throw WebSocketError{"The connection closed during login"}` becomes `throw ConnectionError{...}`.
- **`LoginHandshake`.** `Advance` and `TryReceive` take a `Connection&`.

### Account and AccountRunner

- **`Account`** gains a `std::shared_ptr<NetLoop> net = NetLoop::Create()` last parameter, which it passes to its `GameClient`.
- **`AccountRunner`** owns `std::shared_ptr<NetLoop> m_net = NetLoop::Create()` and passes it to every `Account` it makes.
- **`AccountRunner::Wait`** computes `wake` as today and calls `m_net->Wait(wake)` in place of `sleep_until` or `console->WaitUntil`. A packet for any account now wakes the runner at once, instead of at the next `pollIntervalMs`. The interval stays as the longest wait, because nothing wakes the runner for an interrupt. Logins that are due and scripts' next loops are already folded into `wake`.
- **The console.** At the start of `Run`, `console->SetOnArrived([net = m_net] { net->Wake(); })`, and `SetOnArrived({})` at the end.
- **Before returning**, `Run` calls `m_net->Settle(Clock::now() + SETTLE_TIMEOUT)` (2 s, a little over `CLOSE_TIMEOUT`), so every account's last close finishes with a close frame.

### ConsoleInput

- **`SetOnArrived(std::function<void()> onArrived)`** stores the callback under `m_mutex`. `Push` copies it under the lock and calls it after releasing the lock, because it runs on the reader thread and `Wake` takes Asio's own lock.
- **`WaitUntil`** and `m_arrived` are deleted. The runner was their only user.

---

## 8. Phase 2: raw TCP

### What the engine expects

From [tcp-protocol-289.md](tcp-protocol-289.md), Endpoints and Transport, and the same for 225 and 274:

- The node port is 43594 by default. The client sends no upgrade and no frames, and the login and game bytes are exactly those it sends over WebSocket.
- **Login requests must not share a read.** The server processes one negotiation request per socket data callback, so the client must send each request only after the reply to the one before. `LoginHandshake` already does: it sends the seed request, waits for the seed, then sends the login. This becomes a requirement, written in the class's comment, rather than a side effect.
- The listener sets `TCP_NODELAY` and drops a socket idle for 30 s. The client sets `no_delay` too (§6.2 step 3), so a short request goes out as one segment, and `GameClient`'s 1 s keepalive is far inside the 30 s.

### Config

`Transport_e::Tcp` and `"tcp"` in `TransportNames`. `TransportNames::CHOICES` becomes `"ws, wss or tcp"`. `origin` and `tlsCaFile` are checked and ignored (§2).

### AsioLink

- **A third alternative**, `boost::asio::ip::tcp::socket`, and `RunTcp(socket)` beside `RunWebSocket`. `Run` picks the alternative with a `switch` on `transport`. `RunTcp` runs steps 1 to 3 of §6.2 and step 6 (open, which both share as `FinishConnecting`), then its own read loop, `ReadStream`.
- **Reading:** `async_read_some` into `m_chunk`, a `std::array<u8, READ_CHUNK_SIZE>` member (4096), so it lives as long as the link. Each read is passed to `Receive` while `Open`, and dropped while `Closing`.
- **Writing:** `boost::asio::async_write` of the front item, which writes all of it. The same queue and `OnWrite`. `StartWrite` and `StartClose` visit the socket with `if constexpr` on `IS_TCP`, because a `tcp::socket` has neither `async_write` as a member nor `async_close`.
- **Ending:**

    | Error | In state | Effect |
    |---|---|---|
    | `asio::error::eof` | `Open` | `MarkEnded("Server closed the connection")` |
    | Anything else | `Open` | `MarkFailed("Read failed: {message}")` |
    | Anything, including `eof` | `Closing` | Nothing |

- **Closing:** `StartClose` drops the unsent writes as before, then `ShutdownTcp()` sends a FIN (`shutdown(shutdown_send)`), and the read loop keeps reading, and dropping, until the server's FIN, which the engine sends when it sees the client's. The same `CLOSE_TIMEOUT` timer bounds it, then `Abort()`.
- **A write in flight finishes first.** A FIN sent while `async_write` is part-way through a large buffer would fail the rest of it, so when a write is in flight `StartClose` leaves the FIN to `OnWrite`, which sends it once that write is done and the link is no longer `Open`. A logout click queued just before `Close()` still reaches the server whole.
- **No message boundaries.** Each `Send` is one `async_write`, but the server may read two as one or one as two. `GameClient::Flush` already sends a pass's packets in one `Send`.
- **The WebSocket message limit doesn't apply.** The engine caps WebSocket messages at 1600 bytes (289) and 2000 (225). Nothing caps a TCP write.

### Docs

The README's `server` rows and the config section of [ConfigDesign.md](ConfigDesign.md) list `tcp` and its port. The tcp-protocol pages already describe the TCP endpoint.

---

## 9. Phase 3: SOCKS5

ProxyDesign's plan, with the IXWebSocket hook replaced by a step in the connect coroutine. Its config, its `Socks5Handshake` and its tests carry over, and are written out here in full.

### Decisions

| Topic | Decision |
|---|---|
| Protocol | SOCKS5 only, with no authentication or with a username and password (RFC 1929). Only `CONNECT` |
| Where it runs | Between the TCP connect and TLS (§6.2): the link connects to the proxy, runs the exchange, and carries on with TLS and the upgrade, or with nothing for `tcp`. TLS still checks the certificate against, and sends SNI for, the server's host |
| DNS | The server's host name is sent to the proxy to resolve, so no lookup of it leaves this machine. An IPv4 literal is sent as an address. The proxy's own host is resolved locally |
| Exact reads | Each reply is read to its exact length with `boost::asio::async_read` into a buffer of that size, which completes only when the buffer is full and never reads past it. Not one byte of the TLS, WebSocket or game stream that follows is consumed |
| Timeout and cancellation | The same `connectTimeout` covers the proxy connection, the exchange and what follows, with the stage `during the SOCKS5 exchange`. `Close()` cancels it like any other step |
| Config | A top-level `proxy` section in `client.jsonc`, and an optional `proxy` object in account files that replaces it. An empty `host` means a direct connection |
| Retries | A proxy failure is a failed attempt like any other, retried by `GameClient`'s `RetrySchedule` |
| Errors | `Socks5Handshake` throws `std::runtime_error`, and the step wraps it as `ConnectionError{"SOCKS5 proxy {host}:{port}: {message}"}` |
| Secrets | `proxy.username` and `proxy.password` never appear in a message or a log line. The proxy's host and port may |

Rejected, from ProxyDesign: a local relay (it breaks `wss`), the proxy inside `server` (an account that changed world would lose it), a URL string (the password would sit inside a string that's easy to log whole), and `"proxy": null` meaning direct (in account files, `null` means "use `client.jsonc`'s").

Not included: HTTP `CONNECT`, SOCKS4 and SOCKS4a (a `type` key can be added later), resolving the server's host locally, GSSAPI, chains, and picking a proxy from a list.

### Config

A new section after `server`, with `server`'s host rule:

```jsonc
    // Optional SOCKS5 proxy for every account; an empty host connects directly.
    "proxy": {
        "host": "",
        "port": 1080,
        "username": "",
        "password": ""
    },
```

| Key | Type | Default | Rule |
|---|---|---|---|
| `proxy.host` | string | `""`: connect directly | Empty, or `IsHost` (§2) |
| `proxy.port` | integer | `1080` | 1 to 65535 |
| `proxy.username` | string | `""`: no authentication | Empty, or 1 to 255 printable ASCII characters |
| `proxy.password` | string | `""` | 1 to 255 printable ASCII characters when `proxy.username` is set, and empty when it isn't |

- `ProxySettings_s` in `Config/ProxySettings_s.hpp`, `Config_s::proxy` after `server`, the macro, `ValidateProxy` beside `ValidateServer`, and `AccountConfig_s`'s `std::optional<ProxySettings_s> proxy`, read as `server` is.
- **The account object replaces the whole section**, and a key it leaves out takes its default, not `client.jsonc`'s. `{"host": ""}` connects that account directly.
- **The port is an `s32`**, like `server.port`. **255** is the length limit of RFC 1929's fields. **Printable ASCII** for the credentials, as for the account's own: RFC 1929 allows any bytes, but the symbols proxy providers use are all printable ASCII.
- **`ConfigOverrides::ForAccount`** applies both overrides with one copy of the config:

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

- `accounts/example.jsonc.sample` gains, after the commented-out `server` line:

    ```jsonc
    // Uncomment to send this account through its own SOCKS5 proxy instead of client.jsonc's.
    // {"host": ""} connects it directly.
    // "proxy": {"host": "127.0.0.1", "port": 1080, "username": "user", "password": "pass"},
    ```

### Socks5Handshake

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
- **Connect reply errors.** A version other than 5 throws. A `REP` other than 0 throws its RFC 1928 meaning and the number, such as `host unreachable (reply 4)`, from one `constexpr` table for codes 1 to 8; other codes read `unknown reply (reply 9)`. An `ATYP` other than 1, 3 or 4 throws.
- **IPv4 literals** are four decimal parts of 0 to 255, read with `std::from_chars`, with nothing else in the string. Anything else is a name.
- **Field lengths.** A name or credential that is empty or longer than 255 bytes throws `std::invalid_argument`.
- **The port** is written through `Endian::ToBig` (CONVENTIONS §9).
- **Messages** are lowercase without a trailing period, because they follow `SOCKS5 proxy {host}:{port}: `. They never contain the username or the password.

### The exchange

`Socks5Proxy_s` (host, `u16` port, username, password) goes in `ConnectionOptions_s.hpp`, and `ConnectionOptions_s` gains `std::optional<Socks5Proxy_s> proxy`. The `Connection` constructor rejects a proxy with an empty host or a zero port. With a proxy, §6.2 becomes:

1. Log `Connecting to {transport}://{host}:{port} through SOCKS5 proxy {proxyHost}:{proxyPort}`.
2. Look up and connect to the **proxy's** host and port, then `no_delay`.
3. Write `BuildGreeting(!username.empty())`, read `METHOD_REPLY_SIZE` bytes, `ParseMethodReply`.
4. For `UsernamePassword`: write `BuildPasswordRequest`, read `PASSWORD_REPLY_SIZE` bytes, `ParsePasswordReply`.
5. Write `BuildConnectRequest(host, port)`, read `CONNECT_REPLY_SIZE` bytes, `ParseConnectReply`. For a name, read its length byte. Then read and discard `GetBoundAddressSize(...)` bytes.
6. Carry on with TLS (`wss`), the upgrade (`ws`, `wss`) or open (`tcp`).

The reads and writes are on the lowest-layer `tcp::socket`, before any TLS or WebSocket layer is used.

As built:

- **The step names** for the proxy's own lookup and connect name it as the proxy: `Looking up SOCKS5 proxy {host} failed: ...` and `Connecting to SOCKS5 proxy {host}:{port} failed: ...`.
- **I/O during the exchange.** `WriteToProxy` and `ReadFromProxy` return `false` once `Close()` or the timer has ended the attempt, and the exchange returns at once. A proxy that closes mid-exchange reads `closed the connection during the exchange`; any other error reads as its system message. Both get the `SOCKS5 proxy {host}:{port}: ` prefix, like the parse errors.
- **`FakeSocks5Proxy`** resolves its targets over IPv4 only, so a test that sends `localhost` doesn't wait for `::1` to be refused. `GameClient`'s `MakeOptions` adds `MakeProxy(m_config->proxy)`: `std::nullopt` for an empty host, otherwise the members with the port cast to `u16`. Every reconnect builds its options again, so it goes through the proxy too.

---

## 10. Tests

### 10.1 Test servers

- **`ServerThread`** owns an `io_context` with a work guard and a `std::jthread` that runs it. Test servers live on one, so they answer while the test's own thread waits in a client, as a real server would. Its destructor stops the context and joins. It has `GetContext()` and `Invoke(f)`, which runs `f` on the server thread and waits for its result, for setup and inspection.
- **Ports.** Every test server binds `127.0.0.1:0` and reads back the port the system chose. There's no port range and no `LoopbackPort`. The SO_REUSEADDR trouble that `LoopbackPort` worked around came from IXWebSocket's server. A refused connection uses a port taken the same way and closed at once.
- **`FakeGameServer`** keeps its public interface and behaviour, rebuilt on Beast: an acceptor on a `ServerThread`, `websocket::stream::async_accept` with a decorator that answers `Sec-WebSocket-Protocol: binary`, and a write queue on its thread. `Send` and `Close` from the test thread post to it. Its recorded state stays under a plain `std::mutex` (the recursive one was for IXWebSocket's callbacks). `Url()` becomes `GetHost()` and `GetPort()`, and `MakeConfig` sets the three keys. Phase 2 gives its constructor a `Transport_e`, and a TCP mode that reads the same requests from a byte stream.
- **`TestCertificate`** makes an RSA key and a self-signed certificate for `localhost` at run time with OpenSSL, with the subject alternative name `DNS:localhost` only, and writes the PEM files into a `TempFolder`. The TLS test server loads them. Because the certificate doesn't name `127.0.0.1`, connecting to that address tests the name check.

### 10.2 Phase 1

**ReceiveBufferTests**: WebSocketDesign §6.2's table and the 20 000-byte compaction case, against `ReceiveBuffer`.

**ConnectionTests**, tagged `[Connection]`, and `[network]` where they open sockets. Each test makes its own `NetLoop::Create()` unless it says otherwise. They keep WebSocketDesign §6.4's cases where they still apply: connecting and data, the 65 536-byte message, message boundaries, timeouts and wake-ups, the deadline that saturates, peer close and failure, local close, and logging. These rows are new or changed:

| Server | Client | Expected |
|---|---|---|
| None | `Connection` with an empty host, port 0, `connectTimeout = 0ms`, or `wss` with an empty `tlsCaFile` | Throws `std::invalid_argument`; nothing was opened |
| Records the handshake | Connect with an empty origin | No `Origin` header at all. `Sec-WebSocket-Protocol: binary`. `Host: 127.0.0.1:{port}` |
| Silent (accepts, never answers) | `Close()` while `Connecting`, then `WaitClosed(5s)` | `Close()` returns in under 50 ms and `WaitClosed` is `true` in under 100 ms: no race and no handshake timeout |
| Silent | Destroy the `Connection` while `Connecting`, 20 times, then `Settle(now + 1s)` | Each returns at once; `Settle` returns at once with nothing left |
| Silent | `connectTimeout = 300ms`, `WaitOpen(5s)` | Throws `ConnectionError` within 1 s; the message names the stage, `during the WebSocket upgrade` |
| Answers the upgrade with HTTP 403 | `WaitOpen(5s)` | Throws `ConnectionError` containing `HTTP 403` |
| Closes TCP without a close frame | `WaitAvailable(1, 5s)` | Throws `ConnectionClosedError`; `Pump()` returns `Closed` without throwing |
| Resets the connection (`SO_LINGER` 0, then close) | `WaitAvailable(1, 5s)` | Throws `ConnectionError`, not `ConnectionClosedError` |
| Sends a text message | `WaitClosed(5s)` | Throws `ConnectionError`. The server saw a close frame with code 1003 |
| Echoes | Destroy the open `Connection`, then `Settle(now + 2s)` | The server saw a close frame with code 1000: the close finished after the handle was gone |
| Never answers the close frame | `Close()`, then `WaitClosed(5s)` | `true` after about `CLOSE_TIMEOUT`, between 0.8 s and 2 s |
| Two echo servers | Two connections on one loop; send on both, then `WaitAvailable` on the first | Both have their bytes afterwards: waiting on one ran the other's I/O |
| None | `NetLoop::Wait(now + 5s)` while another thread calls `Wake()` after 200 ms | Returns in under 1 s |

**TLS** (TestCertificate, tagged `[tls]`):

| Server | Client | Expected |
|---|---|---|
| TLS, certificate for `localhost` | `wss`, host `localhost`, `tlsCaFile` = the certificate's PEM | Opens and echoes. The server saw SNI `localhost` |
| The same | `tlsCaFile = "SYSTEM"` | Throws `ConnectionError` containing `TLS handshake` and a verify reason |
| The same | Host `127.0.0.1`, `tlsCaFile` = the PEM | Throws: the certificate doesn't name the host |
| The same | Host `127.0.0.1`, `tlsCaFile = "NONE"` | Opens |
| The same | `tlsCaFile` = a path that doesn't exist | Throws `ConnectionError`; the attempt failed, not the constructor |
| The same | `Close()` when open, then `WaitClosed(5s)` | `true` in under 2 s, through the TLS shutdown |
| Ends TCP without close_notify or a close frame | `WaitAvailable(1, 5s)` | Throws `ConnectionClosedError`: `stream_truncated` counts as a clean end |

**TrustStoreTests**: on Windows only (`#ifdef _WIN32`), `LoadSystemRoots` adds at least one root to a fresh context.

**Config**: `ConfigFileTests` and `AccountFileTests` get the three keys in place of `url`.

- Accepted: `transport` `ws` and `wss`; `host` `localhost`, `127.0.0.1`, `w1.2004scape.org` and 253 characters; `port` 1 and 65535.
- Rejected, each naming its key: `transport` `WS`, `wws`, `tcp` (until phase 2), `""` and `5`; `host` `""`, `ws://localhost`, `localhost:80`, `local host`, `::1`, `é` and 254 characters; `port` 0, 65536, -1 and `"80"` (nlohmann reads `true` as 1, a valid port, as it does for every integer key).
- A file with only `url` fails on `server.host`. The sample loads. `Warn` warns for `wss` with `NONE`, and not for `ws` with `NONE`.

**GameClient, Account, AccountRunner and the script tests** pass with `FakeGameServer` on Beast and the new config, with the log fragments they check updated. Two more:

- **The runner wakes on I/O.** With `pollIntervalMs = 1000`, one account with `idleSeconds = 1` finishes its run in under 3 s. Login takes several round trips, and at one poll interval each it would take over 4 s.
- **The console wakes it.** `ConsoleInput::Push` calls the `SetOnArrived` callback.

### 10.3 Phase 2

- **`TestServer`** (renamed from `TestWebSocketServer`) gains `ServerMode_e::Tcp`: no upgrade, and the script's session reads with `async_read_some`, so each recorded message is one read. `Close(code)` sends a FIN and ignores the code, and a read that ends at the client's FIN counts in `ServerRecord_s::fins`.
- **`FakeGameServer`** takes a `Transport_e` after the revision. Over TCP it uses the WebSocket stream's socket without upgrading it, takes each read during login as one request, as the engine does, and parses game packets from a buffer, so a packet split across reads waits for its end. Its close is a FIN.
- **ConnectionTests over `tcp`**: open and echo; no upgrade, only the bytes sent; two sends arrive in order as one stream; three server writes read as one stream; a 65 536-byte send arrives whole; a FIN is `ConnectionClosedError` and keeps the data before it; a reset is `ConnectionError`; `Close()` sends a FIN (the server reads EOF) and finishes in under 800 ms when the server closes; a 4 MiB write in flight at `Close()` reaches the server whole before the FIN; a server that never closes ends after `CLOSE_TIMEOUT`; `Close()` while connecting is immediate; a destroyed open connection still sends its FIN; nothing listening is a failure; the log lines, with `Connecting to tcp://` and `Server closed the connection`.
- **GameClient over both.** The login, reconnect and logout cases for each revision run with `GENERATE(Transport_e::Ws, Transport_e::Tcp)`.
- **Config**: `tcp` accepted.

### 10.4 Phase 3

New cases are tagged `[Socks5]`, and also `[network]` where they open sockets.

**`FakeSocks5Proxy`**, in `tests/Support/Io/`, on a `ServerThread`:

- `SetCredentials(username, password)` requires those credentials; without it, only no authentication is offered.
- `SetReply(code)` sets the connect reply, success by default. `SetBoundAddress(type)` sets the success reply's address type, IPv4 by default.
- `SetStalled(true)` accepts the connection and never answers the greeting.
- `SetGreetingWithReply(bytes)` makes it send those bytes in the same write as its success reply, standing in for a server that speaks first.
- It records each connect request's address type, host and port, and the credentials each client sent. After a success reply, it connects to the target and relays bytes both ways until either side closes.

**Socks5HandshakeTests:**

| Case | Expected |
|---|---|
| Greeting with and without a username | `05 02 00 02` and `05 01 00` |
| Password request | `01 04 u s e r 04 p a s s`; 255-byte fields accepted. Empty or 256-byte fields throw, and the message has neither value |
| Connect request for `example.com:443` | `05 01 00 03 0B example.com 01 BB` |
| Connect request for `127.0.0.1:80` | `05 01 00 01 7F 00 00 01 00 50` |
| Hosts that look like, but aren't, IPv4 literals: `1.2.3`, `1.2.3.4.5`, `256.1.1.1`, `1.2.3.x`, ` 1.2.3.4` | Sent as names |
| Method replies `05 00`, and `05 02` with a username | `NoAuthentication`, `UsernamePassword` |
| Method replies `04 00`, `05 FF`, `05 02` without a username, `05 01` | Each throws its message. `05 FF` without a username says a username and password may be needed |
| Password replies `01 00` and `05 00` | Accepted |
| Password reply `01 01` | Throws, without the credentials |
| Connect replies with `REP` 1 to 8, and 9 | Each throws its name and number |
| Connect replies with `ATYP` 1, 3 and 4 | Return the type. `ATYP` 2 throws. A version of 4 throws |
| `GetBoundAddressSize` | IPv4 6, IPv6 18, a name of length 7 gives 9 |

**ConnectionTests through the proxy:**

| Case | Expected |
|---|---|
| `ws` to `127.0.0.1`, no credentials | Opens and exchanges data. The proxy recorded one IPv4 connect request to the server's port |
| `ws` to `localhost` | Opens. The proxy recorded a name request for `localhost`: the name was sent, not resolved here |
| `wss` to `localhost`, `tlsCaFile` = the test certificate | Opens: the certificate was checked against `localhost`, not the proxy |
| `tcp` to `127.0.0.1` | Opens and exchanges data |
| With the credentials the proxy requires | Opens. The proxy recorded them |
| Wrong password | Fails. The reason contains `SOCKS5` and `rejected`. No log line and no reason contains the username or the password |
| The proxy replies `REP` 5 | Fails with `connection refused (reply 5)` |
| The success reply carries a name, or an IPv6 address, with the server's first bytes in the same write (`tcp` to a 225 server, which speaks first) | Opens, and those bytes are the first read: the reply was read to its exact end |
| A stalled proxy, `connectTimeout = 1s` | Fails within about 1 s; the reason says `during the SOCKS5 exchange` |
| `Close()` while the proxy is stalled | Returns at once; `WaitClosed` is `true` in under 100 ms |
| Nothing listening on the proxy port | Fails, and the reason names the proxy's host and port |
| A proxy with an empty host, or port 0 | The `Connection` constructor throws `std::invalid_argument` |
| The connect log line | Names the proxy's host and port, and not its credentials |

**Config** (`ConfigFileTests`, `AccountFileTests`):

- The default serialization and the sample have the `proxy` section. A file without it has an empty host.
- Accepted: `proxy.host` `""`, `127.0.0.1`, `proxy.example.com` and 253 characters; `proxy.port` 1 and 65535; credentials of 1 and 255 characters.
- Rejected, each naming its key: `proxy.host` with a space, `é` and `5`; `proxy.port` 0, 65536, -1 and `"1080"`; a 256-character username; a password without a username, a username without a password, and a 256-character password. `"proxy": []`, and each key set to `null`.
- No message from rejected credentials, and no captured log entry, contains them.
- Account files: `proxy` missing or `null` leaves the account's proxy empty; an object is read with its own defaults; `"proxy": 5` throws containing `proxy`; `{"host": ""}` is accepted; a bad `proxy.port` throws containing `proxy.port`.

**GameClient, ConfigOverrides and Account:**

- A login to `FakeGameServer` through `FakeSocks5Proxy` reaches the game, and the proxy saw exactly one connection.
- An account with no override goes through `client.jsonc`'s proxy. An account with its own goes through that one, and `client.jsonc`'s sees nothing. An account with `{"host": ""}` connects directly while `client.jsonc` has a proxy.
- `ConfigOverrides::ForAccount` with both overrides gives a config with both, and with neither returns the same config.

### 10.5 Tooling

- Each test keeps the 60 s ctest `TIMEOUT` backstop.
- The `[network]` and `[tls]` cases pass 50 times in a row (`ctest --preset windows-debug --repeat until-fail:50`), which shows the timing bounds aren't flaky.

---

## 11. Docs

Phase 1:

- [README.md](../../README.md): the `server` rows (transport, host, port), the dependency line (Boost.Beast and Asio, OpenSSL), the `Io/` line in the source tree, and the documents table: `TransportDesign.md` in place of `WebSocketDesign.md`.
- [ConfigDesign.md](ConfigDesign.md): the opening paragraph, the layout note about `WebSocketUrl`, the `server` rows, the default serialization, the validation code, the TLS note, and the implementation-order line that names IXWebSocket.
- [LoggerDesign.md](LoggerDesign.md): its opening line's mention of IXWebSocket's I/O thread, and the `WebSocketClient` case in its tests.
- [CONVENTIONS.md](CONVENTIONS.md):
    - §5: an abstract class may stand in front of an implementation whose header must stay out of shared headers, because a forward declaration isn't allowed. `NetLoop` and `Link` are the examples.
    - §8: coroutines are for Asio I/O sequences only, and one that outlives its caller takes a `std::shared_ptr` to what it uses as a by-value parameter, never as `this` or a lambda capture.
- WebSocketDesign.md is deleted.

Phases 2 and 3: README and ConfigDesign for `tcp` and the `proxy` section.

---

## 12. Phases

Each phase builds on both presets and passes every test before the next starts. On this machine that means Windows Debug and Release, where warnings are errors. linux-clang can't be built here, so keep the code within what both compilers accept, as Revision274Design §11 says.

### Phase 1: Beast for ws and wss

1. **Dependencies.** `vcpkg.json`, CMake (§3), `ReceiveBuffer` with its tests. IXWebSocket stays until step 5, so everything still builds.
2. **Config.** `Transport_e`, `TransportNames`, `ServerSettings_s`, the serializer and the rules, the samples, and the config tests. `GameClient` builds a URL from the three keys for now (`{transport}://{host}:{port}/`), so the old transport keeps working.
3. **The loop and the link.** `NetLoop`, `AsioNetLoop`, `Link`, `AsioLink`, `Connection`, `TrustStore`, the errors, `ServerThread`, `TestCertificate`, and the `ConnectionTests`, `TrustStoreTests` and TLS tests.
4. **Wiring.** `GameClient`, `LoginHandshake`, `Account`, `AccountRunner` and `ConsoleInput` (§7), `FakeGameServer` on Beast, and the runner and console tests.
5. **Removal.** `WebSocketClient`, `WebSocketUrl`, `NetSystem`, `LoopbackPort`, their tests, and `ixwebsocket` from `vcpkg.json` and CMake. `ix::` and `ixwebsocket` appear nowhere.
6. **Docs** (§11).

Done when:

- The tests pass as §10.5 says, with zero warnings.
- **Live runs**, with a scratch `client.jsonc` and `--account`, leaving any client already running alone:
    - The local 289 engine over `ws`: log in, walk, and log out cleanly. The log shows `Connecting to ws://localhost:80`, `Connection open`, and on logout `Connection closing` or the server's close.
    - A public `wss` world, such as the one in `accounts/example.jsonc.sample`'s comment: log in and log out. `tlsCaFile` stays `SYSTEM`, so this checks the Windows root store.
    - The 225 and 274 engines over `ws`, with their own config files.
    - Two accounts side by side on the local engine. Restart the server: both reconnect without blocking each other.

### Phase 2: raw TCP

§8 and §10.3. Done when its tests pass, and a live run logs in to the local 289 engine over `tcp` on 43594, walks, stays logged in for five minutes, and logs out cleanly. The same for 225 and 274 on their node ports.

### Phase 3: SOCKS5

§9 and §10.4, in this order: `Socks5Handshake` and its tests, then the exchange in `AsioLink` with `FakeSocks5Proxy`, then the config, then the wiring in `GameClient` and `ConfigOverrides`. Done when its tests pass and one account logs in through a real SOCKS5 proxy (`ssh -D 1080` or microsocks) over `ws`, `wss` and `tcp`, each log shows the proxy line, the server sees the proxy's address, and a second account with `{"host": ""}` connects directly.

---

## 13. Risks

- **The Windows root store** may lack a root that no other program on the machine has needed yet (§6.3). A `wss` server that fails with `unable to get local issuer certificate` needs a PEM bundle in `tlsCaFile`.
- **A login request split across TCP segments** would break the engine's one-request-per-read rule (§8). With `no_delay` and requests of a few hundred bytes, each goes out in one segment, but TCP doesn't promise it. If it happens, the engine rejects the login and `GameClient` retries.
- **Build time.** Beast and Asio are heavy, but only four library files and the test servers include them. If the Debug build grows by more than it should, separate compilation is the next step (§1, Rejected).
- **Abandoned closes.** A `GameClient` made on its own, with its own loop, drops a close still in progress when it's destroyed (§4). Only tests and tools do that. `AccountRunner` settles first.
