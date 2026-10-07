# WebSocket Transport Design

Design and test plan for `WebSocketClient`, the binary WebSocket transport under the client's packet I/O. It is non-blocking at its core, with blocking helpers that pump it until a condition holds. Code style follows [CONVENTIONS.md](../CONVENTIONS.md). It builds on the project setup in [PacketDesign.md](PacketDesign.md) §7.5 and §8: the static library, Catch2, and the test presets. It logs through `Logger` from [LoggerDesign.md](LoggerDesign.md).

Reference sources:

- `rs2004-headless - Copy/headless-client/src/websocket_client.hpp` / `.cpp`: the previous IXWebSocket transport
- `rs2b0t/289server/webclient/src/io/ClientStream.ts`: the TS stream it replaces
- IXWebSocket 11.4.6, `IXWebSocket.cpp` and `IXWebSocketTransport.cpp`: the close and thread behaviour in §3 was read from these

---

## 1. Decisions

| Topic | Decision |
|---|---|
| Library | IXWebSocket from vcpkg (`openssl` feature), as in the reference. It can't be stepped from the caller's loop, so each connection runs one IXWebSocket I/O thread. The class hides that thread |
| Shape | A single class, `WebSocketClient`, that combines connection control with a receive buffer |
| Threading | Each instance has one owner thread. The I/O thread writes only to a mailbox guarded by a mutex, and the owner moves the mailbox contents into the receive buffer when it pumps. Only the owner touches the IXWebSocket object |
| Non-blocking core | `Connect`, `Send`, `Close`, `Pump`, `Available`, `Peek`, `Read`, `Clear` and `Append` never wait on the network. Waiting, for up to about 300 ms while IXWebSocket's thread finishes a close, is limited to `Stop`, the destructor (which calls it), and a `Connect` that replaces a connection that is still open or closing. One exception comes from IXWebSocket itself: during `Connecting`, a race can make `Close`, `Stop`, the destructor and a replacing `Connect` wait for the whole connection attempt, up to `handshakeTimeout` (see `Close`) |
| Closing | `Close` starts IXWebSocket's own close, which doesn't block, and the state reads `Closing` until the I/O thread finishes. That thread then exits on its own, so freeing the socket afterwards doesn't wait. `Stop` is the blocking form: it closes, joins the thread, and returns with the state `Closed` |
| Blocking helpers | `WaitAvailable`, `WaitOpen` and `WaitClosed` pump in a loop and sleep on a condition variable between pumps, so there is no polling interval. Each has two overloads: one takes a timeout and returns `bool`, the other waits forever |
| Framing | Incoming data is a byte stream, and message boundaries are discarded. Each `Send` is exactly one binary message |
| Errors | `WebSocketError` reports failures and `WebSocketClosedError` (derived from it) reports a clean close. A timeout returns `false` and never throws. A short `Peek` or `Read` throws `std::out_of_range`, as `Packet` does |
| Logging | Through the `std::shared_ptr<Logger>` passed to the constructor ([LoggerDesign.md](LoggerDesign.md)). The connection's lifecycle (connecting, open, closing, closed) is `Info`; traffic and IXWebSocket errors are `Verbose`. Nothing is logged at `Warning` or `Error`: every problem reaches the caller as an exception or a state, and the caller logs it where it handles it |
| Network startup | A `NetSystem` RAII member wraps `ix::initNetSystem` (Winsock on Windows), so there is no global init call to forget |
| Header | `WebSocketClient.hpp` includes `../Core/Logger.hpp`, `<ixwebsocket/IXWebSocket.h>` and `<ixwebsocket/IXWebSocketMessage.h>`, because `Logger`, `ix::WebSocket` and `ix::WebSocketMessage` appear in its declarations |

Rejected:

- **A hand-written client** on non-blocking sockets plus OpenSSL. `Pump` would then do the I/O itself without a thread, but the project would have to own the handshake, the framing and the TLS plumbing. That isn't worth it while IXWebSocket does the job.
- **Closing on a separate thread of our own.** IXWebSocket's I/O thread already does the closing work. Any extra thread would still have to be joined before destruction, because the callback captures `this`.

---

## 2. Layout

```
rs2004-headless/
├── vcpkg.json
├── docs/
│   ├── LoggerDesign.md
│   ├── PacketDesign.md
│   └── WebSocketDesign.md
├── src/
│   └── Io/
│       ├── NetSystem.hpp
│       ├── NetSystem.cpp
│       ├── WebSocketClient.hpp
│       ├── WebSocketClient.cpp
│       ├── WebSocketClosedError.hpp
│       └── WebSocketError.hpp
└── tests/
    └── Io/
        └── WebSocketClientTests.cpp
```

- `WebSocketState_e` and `WebSocketOptions_s` live in `WebSocketClient.hpp`, the header of the class that owns them.
- The two error types are header-only, one per file, like `ConfigError` in CONVENTIONS §8. `WebSocketClient.hpp` doesn't include them, because no prototype in it uses them. `WebSocketClient.cpp` throws both, so it includes both, even though `WebSocketClosedError.hpp` already brings in `WebSocketError.hpp`. Code that catches them includes each one it names.
- `pch.hpp` gains `<condition_variable>` for the class members. `<mutex>`, which the class also uses, and `<thread>`, which the test fixtures use, are already there from [LoggerDesign.md](LoggerDesign.md).
- `vcpkg.json` gains:
    ```json
    {
        "name": "ixwebsocket",
        "default-features": false,
        "features": ["openssl"]
    }
    ```
- CMake: `find_package(ixwebsocket CONFIG REQUIRED)`. The library target links `ixwebsocket::ixwebsocket` publicly, because a public header includes it. The app and the test executable then get its include path through the library, and the test fixtures can use `ix::WebSocketServer` directly.

---

## 3. WebSocketClient

### Interface

```cpp
#pragma once

#include "../Core/Logger.hpp"
#include "NetSystem.hpp"

#include <ixwebsocket/IXWebSocket.h>
#include <ixwebsocket/IXWebSocketMessage.h>

enum class WebSocketState_e : u8
{
    Closed,
    Connecting,
    Open,
    Closing,
};

struct WebSocketOptions_s
{
    std::string url;
    std::string origin;
    std::string tlsCaFile = "SYSTEM";
    std::string subprotocol = "binary";
    std::chrono::seconds handshakeTimeout = 10s;
};

class WebSocketClient
{
public:
    explicit WebSocketClient(std::shared_ptr<Logger> logger = Logger::GetDefault());
    ~WebSocketClient();

    WebSocketClient(const WebSocketClient&) = delete;
    WebSocketClient& operator=(const WebSocketClient&) = delete;

    void Connect(const WebSocketOptions_s& options);
    void Close() noexcept;
    void Stop() noexcept;
    void Send(std::span<const u8> data);
    WebSocketState_e Pump();

    [[nodiscard]] std::size_t Available() const;
    void Peek(std::span<u8> destination) const;
    void Read(std::span<u8> destination);
    void Clear();
    void Append(std::span<const u8> bytes);

    void WaitAvailable(std::size_t count);
    [[nodiscard]] bool WaitAvailable(std::size_t count, std::chrono::milliseconds timeout);
    void WaitOpen();
    [[nodiscard]] bool WaitOpen(std::chrono::milliseconds timeout);
    void WaitClosed();
    [[nodiscard]] bool WaitClosed(std::chrono::milliseconds timeout);

private:
    using Clock = std::chrono::steady_clock;
    using Deadline = std::optional<Clock::time_point>;

    struct Status_s
    {
        WebSocketState_e state = WebSocketState_e::Closed;
        bool failed = false;
        std::string reason = "WebSocket is not connected";
    };

    static void ThrowIfEnded(const Status_s& status);

    bool WaitAvailableUntil(std::size_t count, Deadline deadline);
    bool WaitOpenUntil(Deadline deadline);
    bool WaitClosedUntil(Deadline deadline);
    void WaitForEvent(Deadline deadline);
    void Drain();
    void SyncSocket();
    void OnMessage(const ix::WebSocketMessage& message) noexcept;

    NetSystem m_netSystem;
    std::shared_ptr<Logger> m_logger;

    std::vector<u8> m_received;
    std::size_t m_readOffset = 0;
    Status_s m_status;
    u64 m_seenEventCount = 0;

    std::mutex m_mutex;
    std::condition_variable m_ioEvent;
    Status_s m_ioStatus;
    u64 m_ioEventCount = 0;
    std::vector<u8> m_incoming;

    std::unique_ptr<ix::WebSocket> m_socket;
};
```

- The header includes `<ixwebsocket/IXWebSocketMessage.h>` itself, even though `<ixwebsocket/IXWebSocket.h>` already brings it in.
- `WebSocketClient.cpp` uses `Logger`, `ix::WebSocket` and `ix::WebSocketMessage`, so it includes all three headers again. It also includes `<ixwebsocket/IXUrlParser.h>`, `<ixwebsocket/IXWebSocketMessageType.h>`, `<ixwebsocket/IXWebSocketSendData.h>`, `<ixwebsocket/IXWebSocketCloseInfo.h>` and `<ixwebsocket/IXWebSocketErrorInfo.h>`, which only the implementation uses. `OnMessage` reads `message.closeInfo` and `message.errorInfo` without naming their types, and that still counts as using them.
- The constructor defaults the logger to `Logger::GetDefault()`, moves it into `m_logger` and asserts it isn't null ([LoggerDesign.md](LoggerDesign.md) §3 Usage). It is defined in `WebSocketClient.cpp`.
- The destructor stays user-declared, because it calls `Stop()`. That joins the I/O thread before any member its callback uses is destroyed, whatever order the members are declared in.

### Usage

Blocking, as in the login exchange:

```cpp
auto socket = WebSocketClient{logger};
socket.Connect({.url = "ws://localhost:43594/", .origin = "http://localhost"});
if (!socket.WaitOpen(10s))
{
    throw std::runtime_error{"Timed out connecting"};
}

socket.Send(seedRequest);

auto response = std::array<u8, SEED_RESPONSE_LENGTH>{};
if (!socket.WaitAvailable(response.size(), 30s))
{
    throw std::runtime_error{"Timed out waiting for the seed response"};
}

socket.Read(response);
```

Non-blocking, once per frame of the game loop:

```cpp
void Client::Update()
{
    const auto state = m_socket.Pump();
    while (TryReadPacket())
    {
        HandlePacket();
    }

    if (state == WebSocketState_e::Closed)
    {
        OnDisconnected();
    }
}
```

Logging out, when the server confirms by closing the connection:

```cpp
socket.Send(logoutRequest);
if (!socket.WaitClosed(5s))
{
    logger->Warning("Logout not confirmed within 5 s; closing the connection");
    socket.Close();
}
```

Closing locally and waiting for the close to finish, for example before reconnecting:

```cpp
socket.Close();
if (!socket.WaitClosed(5s))
{
    throw std::runtime_error{"Timed out closing the connection"};
}

socket.Connect(options);
```

When a short block is fine, `Stop()` does the same in one call, with no timeout to handle:

```cpp
socket.Stop();
socket.Connect(options);
```

Handling a failure. `WebSocketClient` doesn't log failures, so the code that handles one logs it ([LoggerDesign.md](LoggerDesign.md) §4):

```cpp
try
{
    Login();
}
catch (const WebSocketError& e)
{
    logger->Error("Login failed: {}", e.what());
    ScheduleReconnect();
}
```

- `TryReadPacket` checks `Available()` and reads straight into a `Packet`: `m_socket.Read(m_in.GetData().first(size))`, then `m_in.SetPos(0)`.
- Handle the buffered bytes before reacting to `Closed`, because bytes that arrived before the close are still in the buffer.
- To reconnect without `Connect` waiting, call `Close()` first. Then either keep pumping until `Pump()` returns `Closed`, or call `WaitClosed` as above.
- `Close()` forgets any failure, so `WaitClosed` after it never throws. It can only time out. The I/O thread normally finishes within about 300 ms of an open connection's `Close()`, or as soon as a connection attempt notices the cancellation. If IXWebSocket loses the cancellation (see `Close` below), the attempt ends when it opens, fails or reaches `handshakeTimeout`.
- Both styles can be mixed on one client. Login can use the waits and the game loop can use `Pump`.

### Behaviour

- **Threading.**
    - Public members are called from one thread at a time, the owner. Concurrent calls from the owner side are not synchronized.
    - IXWebSocket calls `OnMessage` on its I/O thread. It can also call it on the owner thread, from inside `sendBinary` when a socket write fails.
    - Apart from logging, `OnMessage` touches only the mailbox (`m_ioStatus`, `m_ioEventCount` and `m_incoming`), and only while holding `m_mutex`. `Logger` is thread-safe.
    - The constructor sets `m_logger` and nothing reassigns it, so the I/O thread reads it without the lock. Because the client holds a reference, the logger outlives the I/O thread, which the destructor joins.
    - Neither thread logs while holding `m_mutex`. A console write is slow, and the other thread would wait on it.
    - Because of that second case, the owner never calls into IXWebSocket while holding `m_mutex`. `std::mutex` isn't recursive, so doing so would deadlock. The one exception is `start()`, which can't call back (see `Connect` step 4).
    - Only the owner touches `m_socket`.
    - The receive buffer (`m_received`, `m_readOffset`), `m_status` and `m_seenEventCount` belong to the owner. New data reaches them only through `Drain`, which `Pump` and the waits call. `Available`, `Peek` and `Read` therefore never see bytes arrive between two pumps.
    - The class can be neither copied nor moved, because the I/O callback captures `this`. Hold it by value, or in a `std::unique_ptr` when it has to move.
- **What can block.**
    - `Connect` never waits on the network. The DNS lookup, TCP connect, TLS and the HTTP upgrade all run on the I/O thread. `Connect` only waits when it replaces a connection that is still `Open` or `Closing` (step 2 below).
    - `Send` never waits on the network either. `sendBinary` writes what the non-blocking socket accepts at once, and the I/O thread flushes the rest.
    - `Close` never waits on the network. During `Connecting` it usually takes up to about 10 ms, but in one race it waits for the whole connection attempt, up to `handshakeTimeout` (see `Close` below).
    - `Pump` and the waits join the I/O thread when they free a closed socket. They only do this after the thread has delivered its last event, so the join returns at once.
    - `Stop` waits up to about 300 ms (`kClosingMaximumWaitingDelayInMs`) if the connection is still `Open` or `Closing`. During `Connecting` it waits until the attempt ends, which in the cancellation race is the handshake timeout. It returns at once otherwise.
    - The destructor calls `Stop`, because it has to join a thread whose callback uses `this`.
- **Options.**
    - `url`: `ws://` or `wss://`.
    - `origin`: sent as the `Origin` header when it isn't empty. When it is empty, IXWebSocket sends its own default, `{scheme}://{host}:{port}` taken from the URL; it has no way to send no `Origin` at all. The engine rejects a mismatch when `WEB_ALLOWED_ORIGIN` is configured.
    - `tlsCaFile`: used for `wss` only. It is a path to a PEM CA bundle, `"SYSTEM"` for the platform trust store, or `"NONE"` to turn off peer verification.
    - `subprotocol`: `"binary"`, as TS does with `new WebSocket(url, 'binary')`.
    - `handshakeTimeout`: bounds the whole connection attempt on the I/O thread. `WaitOpen`'s timeout is a separate bound, set by the caller, and it does not cancel the attempt.
- **`Connect`.**
    1. Validate the options. The URL must parse with `ix::UrlParser` and its scheme must be `ws` or `wss`, and `handshakeTimeout` must be positive. If either check fails, throw `std::invalid_argument` naming the field. Nothing changes, and an existing connection stays up.
    2. `Stop()` any previous connection, then `Clear()` the receive buffer. When the previous connection is still `Open` or `Closing`, `Stop()` waits up to about 300 ms; calling `Close()` and `WaitClosed` beforehand avoids the wait.
    3. Create `m_socket` and configure it: URL, subprotocol, `Origin` when it isn't empty, TLS `caFile`, handshake timeout, automatic reconnection off, per-message deflate off, and a message callback that forwards to `OnMessage`. Then log `WebSocket connecting to {url}` at `Info`. It is logged before `start()`, so it always comes before the I/O thread's first event in the log.
    4. While holding `m_mutex`, call `m_socket->start()` and then set `m_ioStatus` to `Connecting`:

        ```cpp
        {
            const auto lock = std::scoped_lock{m_mutex};
            m_socket->start();
            m_ioStatus = Status_s{.state = WebSocketState_e::Connecting};
        }
        ```

        Without the lock, either order can lose an update:

        - **`Connecting` first, then `start()`.** `start()` creates a `std::thread`, which can throw `std::system_error`. The state would then read `Connecting` with no thread to ever change it. `Pump()` would report `Connecting` forever, and `WaitOpen()` without a timeout would hang.
        - **`start()` first, then `Connecting`.** The new thread can run at once, and on a fast connection its `Open` or `Error` event can arrive before the state is set. `OnMessage` would find `Closed` and ignore the event, because it only accepts `Open` while `Connecting`. `Connect` would then set `Connecting` over it, and the client would stay `Connecting` on a socket that is actually open.

        Holding the lock fixes both. `OnMessage` must take `m_mutex` before touching the state, so the thread's first event waits until the state is `Connecting`. And because `Connecting` is set only after `start()` returns, a throw from `start()` leaves the state `Closed` while `scoped_lock` releases the lock during unwinding.

        This is a deliberate exception to "never call into IXWebSocket while holding `m_mutex`". It is safe because `start()` only creates the thread (`_thread = std::thread(&WebSocket::run, this)`). It never waits for that thread and never calls `OnMessage` itself, so the new thread just blocks on `m_mutex` until `Connect` releases it.

        This step gets a "why" comment in the code. Without one, moving `start()` out of the lock looks like a harmless tidy-up, but it brings back the second bug.
- **`OnMessage`.**
    - It first logs the event (see Logging), before it takes `m_mutex`.
    - Every event, including ones it otherwise ignores, increments `m_ioEventCount` while holding the lock and then calls `notify_one` on `m_ioEvent`.
    - It is `noexcept`, because an exception must never escape into IXWebSocket's thread.

    | Event | In state | Effect |
    |---|---|---|
    | `Open` | `Connecting` | → `Open` |
    | `Message`, binary | `Open` | Bytes appended to `m_incoming` |
    | `Message`, text | `Open` | → `Closing`, failed: `WebSocket received a text message`. The next `SyncSocket` closes the socket |
    | `Close` | `Connecting` | → `Closed`, failed: `WebSocket closed during handshake (code {}: {})` |
    | `Close` | `Open` | → `Closed`: `WebSocket closed by peer (code {}: {})` |
    | `Error` | `Connecting`, `Open` | → `Closed`, failed: `WebSocket error: {reason}`, plus ` (HTTP {status})` when the status is not zero. Trailing CR, LF and spaces are trimmed from the reason, because a handshake failure ends with the server's raw status line |
    | `Close`, `Error` | `Closing` | → `Closed`. `failed` and the reason are kept |
    | Any other event, or any event in another state | | Ignored |

    - With automatic reconnection off, a `Close` or `Error` event is always the last event IXWebSocket delivers for a connection. Its I/O thread exits right after delivering one.
    - A failed connection attempt ends in `Error`. Every other ending, including an abnormal one, ends in `Close`.
    - After open, IXWebSocket raises no `Error` events, so every move to `Closed` comes from the thread's last event. Reaching `Closed` therefore means the thread is finishing.
- **`Pump` and `Drain`.**
    - `Drain` does three things while holding the lock. It swaps `m_incoming` out, copies `m_ioStatus` into `m_status`, and copies `m_ioEventCount` into `m_seenEventCount`.
    - After releasing the lock, it calls `Append` on the swapped-out bytes and then `SyncSocket`.
    - If `m_status.failed` is set, `Pump` throws `WebSocketError`. It throws only after appending, so bytes received before a failure stay readable. It throws again on every later call until `Close`, `Stop` or `Connect`.
    - Otherwise `Pump` returns the state, which can be `Closing` after a `Close()`. A clean close returns `Closed` without throwing, and a client that never connected also returns `Closed`.
    - The return value isn't `[[nodiscard]]`, because pumping only to receive data is normal.
- **`SyncSocket`** keeps the IXWebSocket object in step with the state. It runs on the owner thread at the end of `Drain` and `Close`:

    ```cpp
    void WebSocketClient::SyncSocket()
    {
        if (!m_socket)
        {
            return;
        }

        if (m_status.state == WebSocketState_e::Closed)
        {
            m_socket.reset();
            return;
        }

        if (m_status.state == WebSocketState_e::Closing && m_socket->getReadyState() == ix::ReadyState::Open)
        {
            m_socket->close();
        }
    }
    ```

    - When the state is `Closed`, the I/O thread has delivered its last event and is exiting. `reset()` (IXWebSocket's destructor calls `stop()`) therefore joins it without waiting. This gets a "why" comment in the code.
    - When the state is `Closing` but IXWebSocket still reports `Open`, the socket has to be closed again. This gets a "why" comment in the code. There are two causes:
        - A `Close()` during `Connecting` only cancels the handshake. A handshake that has already passed IXWebSocket's last cancellation check opens anyway.
        - A text-message failure leaves the socket open.
    - `close()` can safely be called more than once and doesn't block.
- **Receive buffer.**
    - Bytes before `m_readOffset` have already been read.
    - `Peek` and `Read` check the full size first. If fewer bytes are available, they throw `std::out_of_range`, consume nothing, and leave the destination untouched. An empty span is a no-op.
    - When `Read` consumes everything, the vector is cleared and keeps its capacity. Otherwise the buffer is compacted lazily, once the offset reaches `COMPACT_THRESHOLD` (4096) and at least half the vector has been read. A `Read` therefore never shifts the buffer on every call.
    - `Append` is public, so tests and tools can feed bytes in without a network. `Drain` uses it as well.
    - `Clear` drops only bytes that have already been pumped. Bytes still in the mailbox arrive on the next pump. `Connect` clears both.
    - The buffer has no size limit, so the owner must pump and read regularly.
- **`Send`.**
    - While holding the lock, it calls `ThrowIfEnded(m_ioStatus)`. Because that checks the live state, a peer close is reported even before the next pump.
    - Then it runs `assert(m_ioStatus.state == WebSocketState_e::Open && "Send called before the socket opened")`. Sending while `Connecting` is a bug: call `WaitOpen` first, or wait for `Pump` to return `Open`.
    - After releasing the lock, it logs `WebSocket sending {n} bytes` at `Verbose`, then makes one `sendBinary` call with an `IXWebSocketSendData` over the span, so one `Send` is one binary message.
    - If `sendBinary` fails, it checks the live state again. If the connection ended in the meantime, it throws that ending. Otherwise it throws `WebSocketError` with `WebSocket send failed`.
- **`Close`.**
    - `Close` is `noexcept`, never waits on the network, and can be called in any state, any number of times:

    ```cpp
    void WebSocketClient::Close() noexcept
    {
        auto isStartingClose = false;
        {
            const auto lock = std::scoped_lock{m_mutex};
            const auto isClosed = m_ioStatus.state == WebSocketState_e::Closed;
            isStartingClose = m_ioStatus.state == WebSocketState_e::Connecting || m_ioStatus.state == WebSocketState_e::Open;
            m_ioStatus = isClosed ? Status_s{} : Status_s{.state = WebSocketState_e::Closing};
            m_incoming.clear();
            m_status = m_ioStatus;
        }

        if (isStartingClose)
        {
            m_logger->Info("WebSocket closing");
        }

        if (m_socket && m_status.state == WebSocketState_e::Closing)
        {
            m_socket->close();
        }

        SyncSocket();
    }
    ```

    - Any recorded failure is forgotten. Bytes that haven't been pumped are dropped, and bytes already pumped stay readable.
    - It logs `WebSocket closing` at `Info` only when it starts a close, from `Connecting` or `Open`, so repeated calls log nothing. The line is written before `close()`, so it comes before the I/O thread's `WebSocket closed`.
    - IXWebSocket's `close()` doesn't block:
        - From `Open`, it marks the connection closing, writes the close frame to the non-blocking socket and wakes the I/O thread. The I/O thread waits up to about 300 ms for the peer's reply and then delivers `Close`.
        - From `Connecting`, it flags the connection attempt for cancellation. The attempt fails when it next checks the flag and delivers `Error`.
        - Either way, the state then moves from `Closing` to `Closed`.
    - One exception: IXWebSocket holds an internal lock for a whole connection attempt, and its `close()` takes that lock. During `Connecting`, `Close()` therefore waits until the attempt notices the cancellation. Every stage checks for it at least every 10 ms (DNS every 1 ms, TCP connect every 10 ms, TLS and HTTP reads every 1 ms), so the wait is usually short and doesn't depend on the network.
    - **The cancellation race.** IXWebSocket's client handshake clears the cancellation flag as it starts (`_requestInitCancellation = false` at the top of `WebSocketHandshake::clientHandshake`, in 11.4.6 and 12.0.1 alike). A `Close()` that lands after `start()` but before the handshake begins is therefore lost:
        - The attempt runs on until it opens, fails, or reaches `handshakeTimeout`. Against a responsive server it opens within milliseconds, and `SyncSocket` closes it. Against a silent one it ends at the handshake timeout.
        - If the I/O thread already holds the lock when `Close()` arrives, `Close()` itself waits that long. So do `Stop()`, the destructor and a replacing `Connect`, because they call `Close()` and then join the thread.
        - Closing promptly in every case would need a patched IXWebSocket. The stock library was kept instead, so this race is accepted, and the code gets a "why" comment at the `close()` call.
    - When the state was already `Closed`, `SyncSocket` frees the socket at once.
- **`Stop`.**
    - `Stop` is `noexcept` and can be called in any state, any number of times. It returns once IXWebSocket's thread has finished, with the state `Closed`:

    ```cpp
    void WebSocketClient::Stop() noexcept
    {
        Close();
        m_socket.reset();

        const auto lock = std::scoped_lock{m_mutex};
        m_ioStatus = Status_s{};
        m_incoming.clear();
        m_status = m_ioStatus;
    }
    ```

    - `Close()` comes first, so the close has started and any failure is forgotten.
    - `m_socket.reset()` joins the I/O thread, because IXWebSocket's destructor calls `stop()`. `m_mutex` isn't held there, because `OnMessage` may run during the join.
    - How long the join takes depends on the state:
        - `Open` or `Closing`: up to about 300 ms, for the peer's close reply.
        - `Connecting`: until the attempt notices the cancellation, or, if IXWebSocket lost it, until the attempt ends on its own, at the latest at `handshakeTimeout` (see `Close`).
        - `Closed`: no wait, because `SyncSocket` has usually freed the socket already.
    - The state is set to `Closed` afterwards rather than waiting for the thread's last event. If `stop()` lands before the thread's first connection attempt, the thread exits without delivering any event. This gets a "why" comment in the code.
    - `Stop` doesn't pump. As with `Close()`, bytes already pumped stay readable and unpumped bytes are dropped.
    - It has no timeout: IXWebSocket bounds the join itself, by about 300 ms for a close and by `handshakeTimeout` for a connection attempt.
- **Destruction.**
    - The destructor calls `Stop()`. It waits only if the connection is still `Connecting`, `Open` or `Closing` (see "What can block").
    - `m_netSystem` is declared first, so it is destroyed last, after the socket. This gets a "why" comment in the code.

### Waiting

`WaitAvailable`, `WaitOpen` and `WaitClosed` convert their timeout to a `Deadline` and call the matching `...Until` helper. The overload without a timeout passes `std::nullopt`.

```cpp
void WebSocketClient::ThrowIfEnded(const Status_s& status)
{
    if (status.state != WebSocketState_e::Closing && status.state != WebSocketState_e::Closed)
    {
        return;
    }

    if (status.failed)
    {
        throw WebSocketError{status.reason};
    }

    throw WebSocketClosedError{status.reason};
}

bool WebSocketClient::WaitOpenUntil(Deadline deadline)
{
    while (true)
    {
        Drain();
        if (m_status.state == WebSocketState_e::Open)
        {
            return true;
        }

        ThrowIfEnded(m_status);
        if (IsPast(deadline))
        {
            return false;
        }

        WaitForEvent(deadline);
    }
}

bool WebSocketClient::WaitAvailableUntil(std::size_t count, Deadline deadline)
{
    while (true)
    {
        Drain();
        if (Available() >= count)
        {
            return true;
        }

        ThrowIfEnded(m_status);
        if (IsPast(deadline))
        {
            return false;
        }

        WaitForEvent(deadline);
    }
}

bool WebSocketClient::WaitClosedUntil(Deadline deadline)
{
    while (true)
    {
        Drain();
        if (m_status.state == WebSocketState_e::Closed)
        {
            if (m_status.failed)
            {
                throw WebSocketError{m_status.reason};
            }

            return true;
        }

        if (IsPast(deadline))
        {
            return false;
        }

        WaitForEvent(deadline);
    }
}

void WebSocketClient::WaitForEvent(Deadline deadline)
{
    auto lock = std::unique_lock{m_mutex};
    const auto hasEvent = [this]
    {
        return m_ioEventCount != m_seenEventCount;
    };

    if (!deadline)
    {
        m_ioEvent.wait(lock, hasEvent);
        return;
    }

    m_ioEvent.wait_until(lock, *deadline, hasEvent);
}
```

- **`ThrowIfEnded(status)`** does nothing unless the state is `Closing` or `Closed`. In those states it throws `WebSocketError` if the status is marked failed, and `WebSocketClosedError` otherwise, each carrying the status reason.
    - It treats `Closing` as already ended, because neither wait can succeed from there. `Close()` drops unpumped bytes, `OnMessage` ignores data while `Closing`, and a connection never goes from `Closing` back to `Open`.
    - `Send` uses the same check on the live state (`m_ioStatus`).
- **`WaitOpen`.**
    - It succeeds as soon as a pump sees `Open`.
    - While `Connecting`, it keeps waiting.
    - It throws as soon as a pump sees `Closing` or `Closed`. That covers a failed handshake, a `Close()` or `Stop()` while connecting, a peer that closes right after opening, and a client that never connected.
    - A failure throws `WebSocketError`. Anything else throws `WebSocketClosedError`.
    - It reports the state as of its latest pump, not whether the socket was ever open. If the connection opens and ends before a pump sees `Open`, `WaitOpen` throws. Any bytes received in between stay readable.
- **Success comes first in `WaitAvailable`.** Buffered bytes satisfy it even after the connection has closed or failed. `ThrowIfEnded` runs only when they can't.
- **`WaitClosed`.**
    - It succeeds once the state is `Closed`, whether the peer closed, `Close()` was called, or the client never connected.
    - If the connection ended in failure, it throws `WebSocketError` once the state reaches `Closed`.
    - It never throws `WebSocketClosedError`.
    - After `Close()`, no failure is recorded, so `Close()` followed by `WaitClosed` never throws.
    - When it returns `true`, `SyncSocket` has already freed the socket, so a following `Connect` doesn't wait.
- **No lost wakeups.**
    - `OnMessage` counts every event, and `Drain` records the count it has seen. `wait` checks `hasEvent` while holding the lock before it sleeps, so an event that lands between `Drain` and the sleep is seen at once.
    - Events are counted even when `OnMessage` otherwise ignores them. That way `WaitClosed` also wakes for an `Open` that arrives during `Closing`, which `SyncSocket` must answer with another `close()`.
- **Bounded by the deadline.** The deadline is checked on every pass, so a trickle of events that never meets the condition can't stretch the wait. When the deadline wakes the thread, the loop pumps once more before returning `false`, so an event that arrives right at the deadline still counts.
- **Timeouts.**
    - `timeout <= 0` pumps once and returns at once, making the call a poll.
    - A timeout too large for the clock, such as `std::chrono::milliseconds::max()`, saturates to waiting forever. `MakeDeadline`, in the anonymous namespace, compares the timeout against `time_point::max() - now` after converting both to milliseconds, because converting `milliseconds::max()` to the clock's nanoseconds would overflow. This gets a "why" comment in the code.
    - Timeouts are measured on `std::chrono::steady_clock`.
- **A timeout changes nothing.**
    - If `WaitOpen` times out, the connection stays `Connecting`, and its `handshakeTimeout` still applies.
    - If `WaitAvailable` times out, the partial bytes stay buffered.
    - If `WaitClosed` times out, the connection is left as it was. Waiting doesn't start a close; only `Close()` does.
- **The overload without a timeout** returns `void`, because it can only end in success or a throw. The timed overloads are `[[nodiscard]]`, because ignoring a timeout is almost always a bug.
- **`WaitAvailable(0)`** always succeeds at once, even when the client is closed.
- **Not included:** a combined blocking read. `WaitAvailable` followed by `Read` covers it in two lines and keeps the timeout result in plain view.

### Errors

| Situation | Reported by | As | Message |
|---|---|---|---|
| Never connected, after `Close()` or `Stop()`, or while `Closing` after `Close()` | `WaitAvailable`, `WaitOpen`, `Send` | `WebSocketClosedError` | `WebSocket is not connected` |
| Peer closed an open connection | `WaitAvailable`, `WaitOpen`, `Send` | `WebSocketClosedError` | `WebSocket closed by peer (code 1000: ...)` |
| Peer closed during the handshake | `Pump`, all waits, `Send` | `WebSocketError` | `WebSocket closed during handshake (code ...)` |
| IXWebSocket error (DNS, refused, TLS, HTTP rejection) | `Pump`, all waits, `Send` | `WebSocketError` | `WebSocket error: <reason> (HTTP 403)` |
| Text message received | `Pump`, all waits, `Send` | `WebSocketError` | `WebSocket received a text message` |
| `sendBinary` fails while the connection is still up | `Send` | `WebSocketError` | `WebSocket send failed` |
| Bad options | `Connect` | `std::invalid_argument` | Names the field |
| Short `Peek` or `Read` | `Peek`, `Read` | `std::out_of_range` | Requested and available counts |
| Wait timed out | All waits | Returns `false` | |

- A clean close is not an error for `Pump`, which returns `Closing` or `Closed`, or for `WaitClosed`, which returns `true`.
- `WaitClosed` reports a failure once the state reaches `Closed`. `WaitAvailable` and `WaitOpen` report it as soon as it is known.
- Messages are built with `std::format`. Callers that need to know whether the connection ended normally (for example, a close that confirms a logout) catch `WebSocketClosedError` before `WebSocketError`, or use `WaitClosed`.
- `WebSocketClient` doesn't log any of these at `Warning` or `Error` (see Logging).

### Logging

| Where | Thread | Level | Message |
|---|---|---|---|
| `Connect`, just before `start()` | Owner | `Info` | `WebSocket connecting to {url}` |
| `Close`, when it starts a close | Owner | `Info` | `WebSocket closing` |
| `Send`, just before `sendBinary` | Owner | `Verbose` | `WebSocket sending {n} bytes` |
| `OnMessage`, `Open` | I/O | `Info` | `WebSocket open` |
| `OnMessage`, `Close` | I/O | `Info` | `WebSocket closed (code {code}: {reason})` |
| `OnMessage`, `Error` | I/O | `Verbose` | `WebSocket error event: {reason}`, plus ` (HTTP {status})` when the status is not zero |
| `OnMessage`, binary `Message` | I/O | `Verbose` | `WebSocket received {n} bytes` |
| `OnMessage`, text `Message` | I/O | `Verbose` | `WebSocket received a {n}-byte text message` |
| `OnMessage`, any other event | | | Not logged |

- **Events, not transitions.**
    - `OnMessage` logs each event as IXWebSocket delivers it, whatever the state, through `LogEvent(Logger& logger, const ix::WebSocketMessage& message)` in the anonymous namespace, called with `*m_logger`.
    - An event that the `OnMessage` table ignores is still logged. That keeps the races above visible: an `Open` that lands during `Closing` shows as `WebSocket open` followed by `WebSocket closed`.
- **Logged before it takes effect.**
    - `OnMessage` logs before it takes `m_mutex`, so an event's line is written before any pump can see the event. When `WaitOpen`, `WaitAvailable` or `WaitClosed` returns, the line for the event that satisfied it is already in the log. The §6.4 logging tests rely on this.
    - `Connect`, `Close` and `Send` likewise log before they call into IXWebSocket, so their lines come before the events they cause.
- **No `Warning` or `Error` lines.**
    - A failure is reported once, by the exception, and logged once, by the code that handles it ([LoggerDesign.md](LoggerDesign.md) §4). The same goes for a close the caller didn't expect: `Pump` or a wait reports it, and the caller decides whether it deserves a `Warning`.
    - The `Error` event is still logged at `Verbose`. A failure that `Close()`, `Stop()` or `Connect()` discards before any pump reports it can then still be found.
- **Byte counts, never bytes.** The login block carries the password.
- **`Stop` logs nothing of its own.**
    - Its `Close()` logs `closing`, and the I/O thread logs `closed` as it finishes.
    - A `Stop()` that lands before the I/O thread's first connection attempt leaves no `closed` line, because the thread exits without an event.
    - A `Close()` during `Connecting` ends in an `Error` event, so the end of that attempt shows only at `Verbose`.
- **Cost.** At the default `Info` threshold, each per-message `Verbose` call costs one atomic load and formats nothing.

---

## 4. NetSystem and the error types

```cpp
#pragma once

class NetSystem
{
public:
    NetSystem();
    ~NetSystem();

    NetSystem(const NetSystem&) = delete;
    NetSystem& operator=(const NetSystem&) = delete;
};
```

- The constructor calls `ix::initNetSystem()`. If that returns `false`, it throws `std::runtime_error`. The destructor calls `ix::uninitNetSystem()`.
- On Windows these calls are `WSAStartup`/`WSACleanup`, which count references, so every client and every test server fixture can hold its own `NetSystem`. On POSIX they do nothing.
- Only `NetSystem.cpp` includes `<ixwebsocket/IXNetSystem.h>`. The project never includes `<winsock2.h>`.

```cpp
#pragma once

class WebSocketError : public std::runtime_error
{
public:
    using std::runtime_error::runtime_error;
};
```

```cpp
#pragma once

#include "WebSocketError.hpp"

class WebSocketClosedError : public WebSocketError
{
public:
    using WebSocketError::WebSocketError;
};
```

---

## 5. Differences

### From the reference `WebSocketClient`

| Reference | Here | Why |
|---|---|---|
| `ReceiveBuffer` public base class | Folded into the class, with `Append` still public | One class with the requested API. `Append` still lets tests feed bytes without a network |
| `peek`/`read` return `false` when short | Throw `std::out_of_range` and consume nothing | Conventions: failures aren't `bool` returns. Matches `Packet` |
| `TransportState::failed`, which `update()` never returned | Removed: a failure is `Closing` or `Closed` plus a reason. `Closing` added | The enum lists only states `Pump` can return |
| `close()` calls `stop()` and waits up to 300 ms | `Close()` returns at once, and the thread is joined after it has finished. `Stop()` keeps the blocking behaviour | Requested. IXWebSocket's own `close()` doesn't block, and its thread exits on its own |
| Throws `std::runtime_error` | `WebSocketError` and `WebSocketClosedError` | Callers can tell a clean close, such as after a logout, from a failure |
| `initialize_network()`/`shutdown_network()` statics, using `<winsock2.h>` | A `NetSystem` member wrapping `ix::initNetSystem` | Nothing to forget, and no platform code in the project |
| The URL is only checked with `UrlParser::parse`, after closing the old connection | The scheme must also be `ws`/`wss`, and validation runs first | Its comment promised the scheme check, and a bad call shouldn't drop a live connection |
| Text messages are appended | A text message fails the connection | The protocol is binary, so a text frame means the wrong endpoint |
| No blocking calls | `WaitAvailable`, `WaitOpen`, `WaitClosed` | Requested |
| No logging; `protocol.cpp` logged `Connecting to {url}...` and `WebSocket connection established.` | The class logs its lifecycle at `Info`, and its traffic and IXWebSocket events at `Verbose` | Only the class sees every event, including ones on the I/O thread that the caller never pumps |

### From TS `ClientStream`

| TS | C++ |
|---|---|
| `await ClientStream.openSocket(host, secured)` | `Connect(options)`, then `WaitOpen(timeout)` |
| `available` | `Pump()`, then `Available()` |
| `await read()` | `WaitAvailable(1, timeout)`, then `Read` one byte |
| `await readBytes(dst, off, len)` | `WaitAvailable(len, timeout)`, then `Read(dst.subspan(off, len))` |
| `read()` returns -1 after a remote close | `WebSocketClosedError` |
| `write(src, len)` | `Send(src.first(len))` |
| A failed `write` throws on the next `write` | `Send` throws immediately |
| `close()` | `Close()`, which also doesn't block. `WaitClosed` waits for the close to finish, or `Stop()` closes and waits in one call |
| `WebSocketReader`'s fixed 30 s read timeout | The caller's timeout |
| `WebSocketWriter`'s 5000-byte `bufferedAmount` limit | Not ported. TODO: cap `bufferedAmount()` if a stalled server becomes a problem |

---

## 6. Test plan

### 6.1 Strategy

- The receive buffer and the client's behaviour before a connection are tested without a network, using `Append`.
- Everything else runs against an `ix::WebSocketServer` on `127.0.0.1` inside the test process. Each test scripts what the server does when a client opens.
- Timing checks use loose bounds, so they test the mechanism (a wake-up versus a deadline, returning at once versus waiting for a close) rather than the scheduler.
- Every client is built with a logger. The logging cases pass the logger of a `LogCapture` at `Verbose` ([LoggerDesign.md](LoggerDesign.md) §6.1) and check the level and order of the entries, and a fragment of each message, such as the URL or a byte count. The other cases pass a console logger at `Info`.

Out of scope, as in PacketDesign:

- `assert`-guarded bugs, such as `Send` while `Connecting`.
- Exception message text. Tests check only the exception type. Log text is checked only through the fragments in §6.4.
- `wss`. It needs certificates, so it is checked by hand against the live server.
- A handshake that completes after `Close()` has cancelled it. That race can't be triggered on demand, so `SyncSocket`'s second `close()` is covered by review.
- Prompt cancellation of a connection attempt. IXWebSocket can lose it (§3 `Close`), so the cases that close or stop while `Connecting` bound the wait by a short handshake timeout instead.

### 6.2 Receive buffer

Each case uses a fresh client that has never connected.

| Setup | Call | Result |
|---|---|---|
| None | `Available` | 0 |
| `Append({01 02 03})` | `Available` | 3 |
| `Append({01 02})`, `Append({03})`, `Append({})` | `Read` 3 bytes | `01 02 03`; available 0 |
| `Append({01 02 03})` | `Peek` 2 bytes | `01 02`; available still 3 |
| `Append({01 02 03})` | `Peek` 2, then `Read` 2 | Both give `01 02`; available 1 |
| `Append({01 02 03})` | `Read` 2, then `Read` 1 | `01 02`, then `03`; available 0 |
| `Append({01 02 03})` | `Read` 4 bytes | Throws `std::out_of_range`; destination untouched; available 3 |
| `Append({01 02 03})` | `Peek` 4 bytes | Throws `std::out_of_range`; destination untouched |
| None | `Read` and `Peek` with an empty span | No-op |
| `Append({01 02 03})`, `Read` 1 | `Clear`, `Append({09})`, `Read` 1 | `09` |

**Compaction:** pass 20 000 bytes through the buffer, appending 1000-byte chunks while reading 7 bytes at a time, then read the rest. Byte `i` is `i & 0xFF`, and every byte read must equal its index. This crosses the compaction threshold many times, with reads and appends interleaved.

### 6.3 Before connecting

| Call | Result |
|---|---|
| `Pump()` | `Closed` |
| `WaitOpen()`, `WaitOpen(1s)` | Throw `WebSocketClosedError` |
| `WaitAvailable(1)`, `WaitAvailable(1, 1s)` | Throw `WebSocketClosedError` |
| `WaitAvailable(0)`, `WaitAvailable(0, 0ms)` | Return; `true` |
| `Append({01})`, then `WaitAvailable(1, 0ms)` | `true`: buffered bytes satisfy a wait without a connection |
| `WaitClosed()`, `WaitClosed(0ms)` | Return; `true` |
| `Send({01})` | Throws `WebSocketClosedError` |
| `Close()`, twice | No-op; `Pump()` still returns `Closed` |
| `Stop()`, twice | No-op; `Pump()` still returns `Closed` |
| `Connect` with url `""`, `"localhost:43594"`, `"http://localhost/"` or `"ftp://localhost/"`, or with `handshakeTimeout = 0s` | Throws `std::invalid_argument`; `Pump()` still returns `Closed` |

`static_assert(std::derived_from<WebSocketClosedError, WebSocketError>)`.

### 6.4 Loopback

Fixtures:

- `LoopbackServer` wraps `ix::WebSocketServer` and holds its own `NetSystem`.
    - It tries ports 47000 to 47099 until `listen()` succeeds, and exposes `Url()`.
    - It records each message it receives, the handshake's `openInfo` (headers and subprotocol), and whether the client's connection has closed.
    - It runs a per-test `onOpen` script on its connection thread, where delays are `std::this_thread::sleep_for`.
- `SilentServer` is an `ix::SocketServer` subclass. It accepts TCP connections and never answers them. Clients connect to it with `handshakeTimeout = 1s` unless a row says otherwise, so a lost cancellation costs at most a second.

**Connecting and data**

| Server | Client | Expected |
|---|---|---|
| Idle | `Connect`, `WaitOpen(5s)` | `true`; `Pump()` returns `Open` |
| Idle | `Connect` with origin `"http://test"` | Server sees `Origin: http://test` and subprotocol `binary` |
| Idle | `Connect` with an empty origin | Server sees IXWebSocket's default, `Origin: ws://127.0.0.1:{port}` |
| Echoes | `Send({01 02 03})`, `WaitAvailable(3, 5s)`, `Read` 3 | `true`; `01 02 03` |
| Echoes | `Send` 65 536 bytes, byte `i` = `i & 0xFF` | Read back intact (64-bit length frame) |
| Records | `Send({01 02})`, `Send({03})` | Server has exactly two messages, `01 02` and `03` |
| Sends `01 02`, `03 04`, `05 06` as three messages | `WaitAvailable(6, 5s)`, `Read` 6 | `01 02 03 04 05 06`; boundaries discarded |
| Started, then stopped, so nothing listens on its port | `Connect`, `WaitOpen(5s)` | Throws `WebSocketError`, not `WebSocketClosedError` |
| `SilentServer` | `WaitOpen(200ms)` | `false`; `Pump()` returns `Connecting` |
| `SilentServer` | `handshakeTimeout = 1s`, `WaitOpen(5s)` | Throws `WebSocketError` within 3 s |

**Timeouts and wake-ups**

| Server | Client | Expected |
|---|---|---|
| Idle | `WaitAvailable(1, 200ms)` | `false`, after at least 200 ms and under 2 s; `Pump()` still returns `Open` |
| Idle | `WaitAvailable(1, 0ms)`, `WaitAvailable(1, -5ms)` | `false` at once |
| Idle | `WaitClosed(200ms)` | `false`; `Pump()` still returns `Open` |
| Sends `01 02 03 04` after 300 ms | `WaitAvailable(4, 5s)` | `true` in under 1.5 s: the event woke it, not the deadline |
| Sends `01 02 03 04` after 300 ms | `WaitAvailable(4, milliseconds::max())` | `true`: the deadline saturates instead of overflowing |
| Sends `01 02 03 04` after 300 ms | `WaitAvailable(4)` | Returns |

**Peer close and failure**

When the server ends the connection as soon as it opens, the client calls `Connect` and goes straight to the wait under test, without `WaitOpen`. The end can arrive before the first pump sees `Open`, and `WaitOpen` would then throw, as §3 Waiting specifies. This applies to the rows here and to `Stop` after a text message.

| Server | Client | Expected |
|---|---|---|
| Sends `01 02 03 04`, then closes (1000) | `WaitAvailable(5, 5s)` | Throws `WebSocketClosedError`. Afterwards `Available()` is 4, `WaitAvailable(4, 0ms)` is `true`, `Pump()` returns `Closed` without throwing, and `Send` throws `WebSocketClosedError` |
| Closes 300 ms after open | `WaitClosed(5s)` | `true` in under 1.5 s; `Pump()` returns `Closed` |
| Sends `01 02 03 04`, then a text message | `WaitAvailable(5, 5s)` | Throws `WebSocketError`, not `WebSocketClosedError`. `Available()` is 4, `Pump()` throws `WebSocketError` on every call, and `Read` 4 still works |
| Sends a text message | `WaitClosed(5s)` | Throws `WebSocketError`. The server sees the client close the connection |

**Local close and reconnect**

| Server | Client | Expected |
|---|---|---|
| Echoes | `Close()` | Returns in under 50 ms. `Pump()` returns `Closing` or `Closed`, and `WaitOpen(0ms)` and `Send` throw `WebSocketClosedError` |
| Echoes | `Close()`, then `WaitClosed(5s)` | `true`; `Pump()` returns `Closed`; the server sees the close |
| Echoes | `Close()`, then `Pump()` every 10 ms | `Closed` within 1 s, without `WaitClosed` |
| `SilentServer` | `Close()` while `Connecting`, then `WaitClosed(5s)` | `Close()` returns in under 3 s; `WaitClosed` is `true`: the cancellation, or the handshake timeout when the cancellation is lost, ends the attempt |
| `SilentServer` | `Close()` while `Connecting`, then `WaitOpen(5s)` | `WaitOpen` throws `WebSocketClosedError` at once (under 50 ms), without waiting for `Closed` |
| Closes right after open | `Connect`, wait 500 ms without pumping, then `WaitOpen(5s)` | Throws `WebSocketClosedError`: the first pump already sees `Closed` |
| `SilentServer` | Destroy the client while it is `Connecting` | Returns without crashing |
| Echoes | `Stop()` | Returns in under 1 s. `Pump()` returns `Closed` straight away, and the server sees the close |
| Echoes | `Close()`, then `Stop()` | `Stop()` returns in under 1 s; `Pump()` returns `Closed` |
| `SilentServer` | `Stop()` while `Connecting` | Returns in under 3 s, within the handshake timeout; `Pump()` returns `Closed` |
| `SilentServer` | `Connect` then `Stop()` immediately, 20 times. Some of these land before the I/O thread starts its attempt, so the thread exits without an event | Every `Stop()` returns, and `Pump()` returns `Closed` each time |
| Closes 300 ms after open | `WaitClosed(5s)`, then `Stop()` | `Stop()` returns at once |
| Sends a text message | `WaitAvailable(1, 5s)` throws, then `Stop()` | `Pump()` returns `Closed` without throwing: `Stop()` forgot the failure |
| Echoes | `Connect`, exchange, `Stop`, `Connect` again, exchange | The second `Connect` returns in under 50 ms; the second session works |
| Sends `01 02` | `WaitAvailable(2, 5s)`, then `Close()` | `Available()` still 2 |
| Echoes | `Connect`, exchange, `Close`, `WaitClosed(5s)`, `Connect` again, exchange | The second `Connect` returns in under 50 ms; the second session works; `Available()` is 0 right after it |
| Echoes | `Connect`, exchange, then `Connect` again without `Close` | The second `Connect` returns in under 1 s; the second session works |
| Echoes | `Connect`, `WaitOpen`, then `Connect` with `"http://x"` | Throws `std::invalid_argument`; the first connection still echoes |

**Logging** (each client built with the logger of a `LogCapture` at `Verbose`)

| Server | Client | Expected |
|---|---|---|
| Echoes | `Connect`, `WaitOpen(5s)`, `Send({01 02 03})`, `WaitAvailable(3, 5s)`, `Close()`, `WaitClosed(5s)` | `Info` entries in this order: `connecting to` with the URL, `open`, `closing`, `closed (code 1000`. `Verbose` entries include `sending 3 bytes` and `received 3 bytes`. No `Warning` or `Error` entries |
| Echoes | The same sequence, checking the capture after each wait | `open` is captured by the time `WaitOpen` returns, `received 3 bytes` by the time `WaitAvailable` returns, and `closed` by the time `WaitClosed` returns |
| Closes (1000) 300 ms after open | `Connect`, `WaitClosed(5s)` | `Info` entries: `connecting to`, `open`, `closed (code 1000`. No `closing` entry |
| Started, then stopped, so nothing listens on its port | `Connect`, then `WaitOpen(5s)`, which throws `WebSocketError` | A `Verbose` `error event` entry. No `Warning` or `Error` entries |
| Sends a text message | `WaitClosed(5s)`, which throws `WebSocketError` | A `Verbose` `text message` entry. No `Warning` or `Error` entries |
| Echoes | `Close()` twice, then `Stop()` | Exactly one `closing` entry |

### 6.5 Tooling

- The test executable gets IXWebSocket through the library for the server fixtures.
- Tags are `[WebSocketClient]`, plus `[network]` on the §6.4 cases.
- The logging cases use `LogCapture` from `tests/LogCapture.hpp`. The other cases' console loggers print as usual, and ctest shows that output only for a failing test, which is where it helps.
- Each test gets a 60 s ctest `TIMEOUT`, as a backstop for the waits with no timeout.

### 6.6 Done when

- All tests pass on `windows-debug` and `windows-release` (and on the `linux-*` presets once available), with zero warnings.
- The `[network]` cases pass 50 times in a row (`ctest --preset windows-debug --repeat until-fail:50`), which shows the timing bounds aren't flaky.

---

## 7. Implementation order

`Logger` ([LoggerDesign.md](LoggerDesign.md)) is already in place: it comes right after the project setup.

1. **Dependencies:** add `ixwebsocket` to `vcpkg.json`. Add `find_package` and link it publicly to the library target. Add `<condition_variable>` to `pch.hpp`.
2. **`NetSystem`, `WebSocketError`, `WebSocketClosedError`.**
3. **Receive buffer half:** implement `Available`, `Peek`, `Read`, `Clear` and `Append`, plus the §6.2 tests.
4. **Connection half:** implement `Connect`, `OnMessage`, `Drain`, `SyncSocket`, `Pump`, `Send`, `Close`, `Stop` and the three waits, with their logging (§3 Logging), plus the §6.3 and §6.4 tests.
