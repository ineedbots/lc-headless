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

    // Declared first so it's destroyed last, after the socket that needs it.
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
