#include "pch.hpp"
#include "WebSocketClient.hpp"

#include "../Core/Logger.hpp"
#include "NetSystem.hpp"
#include "WebSocketClosedError.hpp"
#include "WebSocketError.hpp"

#include <ixwebsocket/IXSocketTLSOptions.h>
#include <ixwebsocket/IXUrlParser.h>
#include <ixwebsocket/IXWebSocket.h>
#include <ixwebsocket/IXWebSocketCloseInfo.h>
#include <ixwebsocket/IXWebSocketErrorInfo.h>
#include <ixwebsocket/IXWebSocketMessage.h>
#include <ixwebsocket/IXWebSocketMessageType.h>
#include <ixwebsocket/IXWebSocketSendData.h>
#include <ixwebsocket/IXWebSocketSendInfo.h>

namespace
{
    constexpr auto COMPACT_THRESHOLD = std::size_t{4096};
    constexpr auto TRAILING_WHITESPACE = "\r\n "sv;

    using SteadyTime = std::chrono::steady_clock::time_point;

    bool IsWebSocketUrl(const std::string& url)
    {
        auto protocol = std::string{};
        auto host = std::string{};
        auto path = std::string{};
        auto query = std::string{};
        auto port = 0;
        if (!ix::UrlParser::parse(url, protocol, host, path, query, port))
        {
            return false;
        }

        return protocol == "ws" || protocol == "wss";
    }

    std::optional<SteadyTime> MakeDeadline(std::chrono::milliseconds timeout)
    {
        const auto now = std::chrono::steady_clock::now();
        if (timeout <= 0ms)
        {
            return now;
        }

        // Compared in milliseconds: converting milliseconds::max() to the clock's ticks would overflow.
        const auto untilClockEnds = std::chrono::floor<std::chrono::milliseconds>(SteadyTime::max() - now);
        if (timeout >= untilClockEnds)
        {
            return std::nullopt;
        }

        return now + timeout;
    }

    bool IsPast(const std::optional<SteadyTime>& deadline)
    {
        return deadline && std::chrono::steady_clock::now() >= *deadline;
    }

    std::string DescribeErrorInfo(const ix::WebSocketErrorInfo& errorInfo)
    {
        // A failed handshake's reason ends with the server's raw status line, line break included.
        auto description = errorInfo.reason;
        const auto end = description.find_last_not_of(TRAILING_WHITESPACE);
        description.erase(end == std::string::npos ? 0 : end + 1);
        if (errorInfo.http_status != 0)
        {
            std::format_to(std::back_inserter(description), " (HTTP {})", errorInfo.http_status);
        }

        return description;
    }

    void AppendBytes(std::vector<u8>& destination, const std::string& text)
    {
        const auto* const bytes = reinterpret_cast<const u8*>(text.data());
        destination.insert(destination.end(), bytes, bytes + text.size());
    }

    void LogEvent(Logger& logger, const ix::WebSocketMessage& message)
    {
        switch (message.type)
        {
        case ix::WebSocketMessageType::Open:
            logger.Info("WebSocket open");
            return;
        case ix::WebSocketMessageType::Close:
            logger.Info("WebSocket closed (code {}: {})", message.closeInfo.code, message.closeInfo.reason);
            return;
        case ix::WebSocketMessageType::Error:
            logger.Verbose("WebSocket error event: {}", DescribeErrorInfo(message.errorInfo));
            return;
        case ix::WebSocketMessageType::Message:
            if (message.binary)
            {
                logger.Verbose("WebSocket received {} bytes", message.str.size());
                return;
            }

            logger.Verbose("WebSocket received a {}-byte text message", message.str.size());
            return;
        default:
            return;
        }
    }
}

WebSocketClient::WebSocketClient(std::shared_ptr<Logger> logger)
    : m_logger{std::move(logger)}
{
    assert(m_logger && "WebSocketClient needs a logger");
}

WebSocketClient::~WebSocketClient()
{
    Stop();
}

void WebSocketClient::Connect(const WebSocketOptions_s& options)
{
    if (!IsWebSocketUrl(options.url))
    {
        throw std::invalid_argument{"WebSocket options: url must be a ws:// or wss:// URL"};
    }

    if (options.handshakeTimeout <= 0s)
    {
        throw std::invalid_argument{"WebSocket options: handshakeTimeout must be positive"};
    }

    Stop();
    Clear();

    m_socket = std::make_unique<ix::WebSocket>();
    m_socket->setUrl(options.url);
    m_socket->addSubProtocol(options.subprotocol);
    if (!options.origin.empty())
    {
        m_socket->setExtraHeaders({{"Origin", options.origin}});
    }

    auto tlsOptions = ix::SocketTLSOptions{};
    tlsOptions.caFile = options.tlsCaFile;
    m_socket->setTLSOptions(tlsOptions);
    m_socket->setHandshakeTimeout(static_cast<int>(options.handshakeTimeout.count()));
    m_socket->disableAutomaticReconnection();
    m_socket->disablePerMessageDeflate();
    m_socket->setOnMessageCallback([this](const ix::WebSocketMessagePtr& message)
    {
        OnMessage(*message);
    });

    m_logger->Info("WebSocket connecting to {}", options.url);

    // start() and the move to Connecting happen under one lock. Setting Connecting first
    // would leave it stuck if start() throws; setting it after the unlock lets a fast first
    // event arrive while the state is still Closed, where OnMessage ignores it. start()
    // only creates the thread, which waits here for the lock, so holding it is safe.
    {
        const auto lock = std::scoped_lock{m_mutex};
        m_socket->start();
        m_ioStatus = Status_s{.state = WebSocketState_e::Connecting};
    }
}

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

    // During Connecting, IXWebSocket's close() waits for the connection attempt to notice the
    // cancellation. The handshake clears a cancellation that arrives before it starts, so in
    // that race the attempt, and this call, can run until the handshake timeout.
    if (m_socket && m_status.state == WebSocketState_e::Closing)
    {
        m_socket->close();
    }

    SyncSocket();
}

void WebSocketClient::Stop() noexcept
{
    Close();
    m_socket.reset();

    // Set here rather than waiting for the thread's last event: a stop that lands before
    // the thread's first connection attempt ends the thread without any event.
    const auto lock = std::scoped_lock{m_mutex};
    m_ioStatus = Status_s{};
    m_incoming.clear();
    m_status = m_ioStatus;
}

void WebSocketClient::Send(std::span<const u8> data)
{
    {
        const auto lock = std::scoped_lock{m_mutex};
        ThrowIfEnded(m_ioStatus);
        assert(m_ioStatus.state == WebSocketState_e::Open && "Send called before the socket opened");
    }

    m_logger->Verbose("WebSocket sending {} bytes", data.size());
    const auto sendInfo = m_socket->sendBinary(ix::IXWebSocketSendData{reinterpret_cast<const char*>(data.data()), data.size()});
    if (sendInfo.success)
    {
        return;
    }

    {
        const auto lock = std::scoped_lock{m_mutex};
        ThrowIfEnded(m_ioStatus);
    }

    throw WebSocketError{"WebSocket send failed"};
}

WebSocketState_e WebSocketClient::Pump()
{
    Drain();
    if (m_status.failed)
    {
        throw WebSocketError{m_status.reason};
    }

    return m_status.state;
}

std::size_t WebSocketClient::Available() const
{
    return m_received.size() - m_readOffset;
}

void WebSocketClient::Peek(std::span<u8> destination) const
{
    if (destination.size() > Available())
    {
        throw std::out_of_range{std::format("WebSocket has {} bytes available, but {} were requested", Available(), destination.size())};
    }

    std::ranges::copy(std::span{m_received}.subspan(m_readOffset, destination.size()), destination.begin());
}

void WebSocketClient::Read(std::span<u8> destination)
{
    Peek(destination);
    m_readOffset += destination.size();
    if (m_readOffset == m_received.size())
    {
        Clear();
        return;
    }

    if (m_readOffset >= COMPACT_THRESHOLD && m_readOffset * 2 >= m_received.size())
    {
        m_received.erase(m_received.begin(), m_received.begin() + static_cast<std::ptrdiff_t>(m_readOffset));
        m_readOffset = 0;
    }
}

void WebSocketClient::Clear()
{
    m_received.clear();
    m_readOffset = 0;
}

void WebSocketClient::Append(std::span<const u8> bytes)
{
    m_received.insert(m_received.end(), bytes.begin(), bytes.end());
}

void WebSocketClient::WaitAvailable(std::size_t count)
{
    WaitAvailableUntil(count, std::nullopt);
}

bool WebSocketClient::WaitAvailable(std::size_t count, std::chrono::milliseconds timeout)
{
    return WaitAvailableUntil(count, MakeDeadline(timeout));
}

void WebSocketClient::WaitOpen()
{
    WaitOpenUntil(std::nullopt);
}

bool WebSocketClient::WaitOpen(std::chrono::milliseconds timeout)
{
    return WaitOpenUntil(MakeDeadline(timeout));
}

void WebSocketClient::WaitClosed()
{
    WaitClosedUntil(std::nullopt);
}

bool WebSocketClient::WaitClosed(std::chrono::milliseconds timeout)
{
    return WaitClosedUntil(MakeDeadline(timeout));
}

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

void WebSocketClient::Drain()
{
    auto arrived = std::vector<u8>{};
    {
        const auto lock = std::scoped_lock{m_mutex};
        arrived.swap(m_incoming);
        m_status = m_ioStatus;
        m_seenEventCount = m_ioEventCount;
    }

    Append(arrived);
    SyncSocket();
}

void WebSocketClient::SyncSocket()
{
    if (!m_socket)
    {
        return;
    }

    // Closed means the I/O thread has delivered its last event and is exiting, so freeing
    // the socket joins it without waiting.
    if (m_status.state == WebSocketState_e::Closed)
    {
        m_socket.reset();
        return;
    }

    // Closing while IXWebSocket still reports Open happens when a handshake finished despite
    // a Close() during Connecting, or after a text message failed the connection.
    if (m_status.state == WebSocketState_e::Closing && m_socket->getReadyState() == ix::ReadyState::Open)
    {
        m_socket->close();
    }
}

void WebSocketClient::OnMessage(const ix::WebSocketMessage& message) noexcept
{
    LogEvent(*m_logger, message);

    {
        const auto lock = std::scoped_lock{m_mutex};
        ++m_ioEventCount;

        const auto state = m_ioStatus.state;
        switch (message.type)
        {
        case ix::WebSocketMessageType::Open:
            if (state == WebSocketState_e::Connecting)
            {
                m_ioStatus.state = WebSocketState_e::Open;
            }
            break;

        case ix::WebSocketMessageType::Message:
            if (state != WebSocketState_e::Open)
            {
                break;
            }

            if (!message.binary)
            {
                m_ioStatus = Status_s{.state = WebSocketState_e::Closing, .failed = true, .reason = "WebSocket received a text message"};
                break;
            }

            AppendBytes(m_incoming, message.str);
            break;

        case ix::WebSocketMessageType::Close:
            if (state == WebSocketState_e::Connecting)
            {
                m_ioStatus = Status_s{
                    .state = WebSocketState_e::Closed,
                    .failed = true,
                    .reason = std::format("WebSocket closed during handshake (code {}: {})", message.closeInfo.code, message.closeInfo.reason),
                };
            }
            else if (state == WebSocketState_e::Open)
            {
                m_ioStatus = Status_s{
                    .state = WebSocketState_e::Closed,
                    .reason = std::format("WebSocket closed by peer (code {}: {})", message.closeInfo.code, message.closeInfo.reason),
                };
            }
            else if (state == WebSocketState_e::Closing)
            {
                m_ioStatus.state = WebSocketState_e::Closed;
            }
            break;

        case ix::WebSocketMessageType::Error:
            if (state == WebSocketState_e::Connecting || state == WebSocketState_e::Open)
            {
                m_ioStatus = Status_s{
                    .state = WebSocketState_e::Closed,
                    .failed = true,
                    .reason = std::format("WebSocket error: {}", DescribeErrorInfo(message.errorInfo)),
                };
            }
            else if (state == WebSocketState_e::Closing)
            {
                m_ioStatus.state = WebSocketState_e::Closed;
            }
            break;

        default:
            break;
        }
    }

    m_ioEvent.notify_one();
}
