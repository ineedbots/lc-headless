#include "pch.hpp"
#include "GameClient.hpp"

#include "../Core/ConfigFile.hpp"
#include "../Core/Logger.hpp"
#include "../Io/WebSocketClient.hpp"
#include "../Io/WebSocketError.hpp"
#include "ConnectionLostError.hpp"
#include "Decode/ServerPacketDecoder.hpp"
#include "Net/ClientPacketWriter.hpp"
#include "Net/LoginError.hpp"
#include "Net/LoginHandshake.hpp"
#include "Net/ServerPacketReader.hpp"
#include "Protocol/ClientPacket_s.hpp"
#include "Protocol/ClientPackets.hpp"
#include "Protocol/ClientProt.hpp"
#include "Protocol/ServerProt.hpp"
#include "ProtocolError.hpp"
#include "State/GameState_s.hpp"
#include "State/Social_s.hpp"
#include "Tile_s.hpp"

namespace
{
    constexpr auto LOGIN_POLL = 10ms;
    constexpr auto LOGOUT_POLL = 100ms;
    constexpr auto LOGOUT_RETRY = 2s;

    std::string_view DescribeMessageType(MessageType_e type)
    {
        switch (type)
        {
        case MessageType_e::Game:
            return "game";
        case MessageType_e::Public:
            return "public";
        case MessageType_e::Say:
            return "say";
        case MessageType_e::Private:
            return "private";
        case MessageType_e::TradeRequest:
            return "trade request";
        case MessageType_e::DuelRequest:
            return "duel request";
        }

        assert(false && "Unhandled MessageType_e");
        return "message";
    }

    std::chrono::milliseconds GetRemaining(std::chrono::steady_clock::time_point deadline)
    {
        const auto remaining = std::chrono::duration_cast<std::chrono::milliseconds>(deadline - std::chrono::steady_clock::now());
        return std::max(remaining, 0ms);
    }

    // A failed connection has also delivered its last event, so freeing it doesn't wait either.
    bool IsClosed(WebSocketClient& socket) noexcept
    {
        try
        {
            return socket.Pump() == WebSocketState_e::Closed;
        }
        catch (const std::exception&)
        {
            return true;
        }
    }

    // The wait before a reconnect attempt: none before the first, then the delay, doubling each time up to the cap.
    std::chrono::milliseconds GetRetryDelay(const GameClientOptions_s& options, u32 failedAttempts)
    {
        auto delay = options.retryDelay;
        for (auto i = u32{1}; i < failedAttempts && delay < options.maxRetryDelay; ++i)
        {
            delay *= 2;
        }

        return std::min(delay, options.maxRetryDelay);
    }
}

GameClient::GameClient(std::shared_ptr<const Config_s> config, AccountSettings_s account, std::shared_ptr<Logger> logger, GameClientOptions_s options)
    : m_config{std::move(config)}
    , m_account{std::move(account)}
    , m_logger{std::move(logger)}
    , m_options{options}
    , m_socket{std::make_unique<WebSocketClient>(m_logger)}
    , m_decoder{m_logger}
{
    assert(m_config && "GameClient needs a config");
    assert(m_logger && "GameClient needs a logger");
}

void GameClient::BeginLogin()
{
    assert((m_status == ClientStatus_e::Disconnected || m_status == ClientStatus_e::LoggedOut) && "BeginLogin called during a session");
    m_reconnecting = false;
    m_attempt = 0;
    m_retryAt.reset();
    m_status = ClientStatus_e::Connecting;
    try
    {
        StartAttempt();
    }
    catch (const std::exception&)
    {
        Disconnect();
        throw;
    }
}

void GameClient::Login()
{
    BeginLogin();
    while (m_status == ClientStatus_e::Connecting)
    {
        Pump(LOGIN_POLL);
    }
}

void GameClient::Pump(std::chrono::milliseconds maxWait)
{
    FreeClosedSockets();
    switch (m_status)
    {
    case ClientStatus_e::Connecting:
        PumpConnecting(maxWait);
        return;
    case ClientStatus_e::InGame:
    case ClientStatus_e::LoggingOut:
        PumpSession(maxWait);
        return;
    case ClientStatus_e::Disconnected:
    case ClientStatus_e::LoggedOut:
        return;
    }
}

void GameClient::RequestLogout(std::chrono::milliseconds timeout)
{
    if (m_status == ClientStatus_e::Connecting)
    {
        m_logger->Info("Login abandoned");
        Disconnect();
        return;
    }

    if (m_status != ClientStatus_e::InGame)
    {
        return;
    }

    m_logger->Info("Logging out");
    Send(ClientPackets::IfButton(m_config->client.logoutComponent));
    m_status = ClientStatus_e::LoggingOut;
    m_logoutTimeout = timeout;
    m_logoutDeadline = Clock::now() + timeout;
    m_nextLogoutClick = Clock::now() + LOGOUT_RETRY;
}

void GameClient::Logout(std::chrono::milliseconds timeout)
{
    RequestLogout(timeout);
    while (m_status == ClientStatus_e::LoggingOut)
    {
        Pump(std::min(GetRemaining(m_logoutDeadline), LOGOUT_POLL));
    }

    Disconnect();
}

void GameClient::Disconnect() noexcept
{
    ReleaseSocket();
    m_handshake.reset();
    m_reader.reset();
    m_writer.reset();
    m_outgoing.clear();
    if (m_status != ClientStatus_e::LoggedOut)
    {
        m_status = ClientStatus_e::Disconnected;
    }
}

ClientStatus_e GameClient::GetStatus() const
{
    return m_status;
}

bool GameClient::IsInGame() const
{
    return m_status == ClientStatus_e::InGame;
}

u32 GameClient::GetLoginCount() const
{
    return m_loginCount;
}

const GameState_s& GameClient::GetState() const
{
    return m_state;
}

GameState_s GameClient::TakeSnapshot() const
{
    return m_state;
}

void GameClient::Send(ClientPacket_s packet)
{
    if (m_status != ClientStatus_e::InGame)
    {
        throw std::runtime_error{std::format("Can't send {} while not in game", ClientProt::GetName(static_cast<u8>(packet.prot)))};
    }

    ClientPacketWriter::Validate(packet);
    m_outgoing.push_back(std::move(packet));
}

void GameClient::SendMove(MoveKind_e kind, std::span<const Tile_s> waypoints, bool run)
{
    Send(ClientPackets::Move(kind, waypoints, run));

    auto destination = waypoints.back();
    destination.level = m_state.localPlayer.tile.level;
    m_state.walkDestination = destination;
    m_state.walkRequestTick = m_state.tick;
}

void GameClient::Flush()
{
    if (m_outgoing.empty() || !m_writer)
    {
        return;
    }

    auto bytes = std::vector<u8>{};
    for (const auto& packet : m_outgoing)
    {
        m_writer->Write(packet, bytes);
        m_logger->Verbose("Sending {} ({} bytes)", ClientProt::GetName(static_cast<u8>(packet.prot)), packet.payload.size());
    }

    m_outgoing.clear();
    m_lastSend = Clock::now();
    m_socket->Send(bytes);
}

void GameClient::PumpSession(std::chrono::milliseconds maxWait)
{
    auto lostReason = std::optional<std::string>{};
    try
    {
        if (maxWait > 0ms && m_socket->Available() == 0)
        {
            static_cast<void>(m_socket->WaitAvailable(1, maxWait));
        }

        const auto socketState = m_socket->Pump();
        ProcessInput();
        if (m_status == ClientStatus_e::LoggedOut)
        {
            Disconnect();
            return;
        }

        if (socketState != WebSocketState_e::Open)
        {
            lostReason = "the server closed the connection";
        }
        else if (Clock::now() - m_lastReceive > m_options.serverSilenceTimeout)
        {
            lostReason = std::format("nothing from the server for {} ms", m_options.serverSilenceTimeout.count());
        }
        else
        {
            if (m_status == ClientStatus_e::LoggingOut && !ContinueLogout())
            {
                return;
            }

            SendKeepaliveIfIdle();
            Flush();
        }
    }
    catch (const WebSocketError& e)
    {
        lostReason = e.what();
    }
    catch (const ProtocolError&)
    {
        // The ciphers are out of step with the server, so this connection can't continue.
        Disconnect();
        throw;
    }

    if (!lostReason)
    {
        return;
    }

    if (m_status == ClientStatus_e::LoggingOut)
    {
        m_status = ClientStatus_e::LoggedOut;
        Disconnect();
        return;
    }

    BeginReconnect(*lostReason);
}

// The server refuses a logout during combat and for 10 seconds after it, so the button is clicked again
// every few seconds until the server agrees, as a player would, or the deadline passes.
bool GameClient::ContinueLogout()
{
    const auto now = Clock::now();
    if (now >= m_logoutDeadline)
    {
        m_logger->Warning("The server didn't confirm the logout within {} ms; closing the connection anyway", m_logoutTimeout.count());
        Disconnect();
        return false;
    }

    if (now >= m_nextLogoutClick)
    {
        m_outgoing.push_back(ClientPackets::IfButton(m_config->client.logoutComponent));
        m_nextLogoutClick = now + LOGOUT_RETRY;
    }

    return true;
}

void GameClient::StartAttempt()
{
    ++m_attempt;
    if (m_reconnecting)
    {
        m_logger->Info("Reconnecting as {} (attempt {} of {})", m_account.username, m_attempt, m_options.connectAttempts);
    }
    else if (m_attempt > 1)
    {
        m_logger->Info("Logging in as {} (attempt {} of {})", m_account.username, m_attempt, m_options.connectAttempts);
    }
    else
    {
        m_logger->Info("Logging in as {}", m_account.username);
    }

    const auto& server = m_config->server;
    m_reader.reset();
    m_writer.reset();
    m_outgoing.clear();
    m_socket->Connect({.url = server.url, .origin = server.origin, .tlsCaFile = server.tlsCaFile});
    m_handshake.emplace(m_account, m_config->login, m_reconnecting);
    m_attemptDeadline = Clock::now() + m_options.loginTimeout;
}

void GameClient::PumpConnecting(std::chrono::milliseconds maxWait)
{
    if (m_retryAt)
    {
        const auto remaining = GetRemaining(*m_retryAt);
        if (remaining > 0ms)
        {
            std::this_thread::sleep_for(std::min(maxWait, remaining));
            return;
        }

        m_retryAt.reset();
        StartAttempt();
    }

    try
    {
        AdvanceAttempt(maxWait);
    }
    catch (const LoginError& e)
    {
        Disconnect();
        if (!ScheduleRetry(e.what(), e.IsRetryable()))
        {
            throw;
        }
    }
    catch (const std::runtime_error& e)
    {
        Disconnect();
        if (!ScheduleRetry(e.what(), true))
        {
            throw;
        }
    }
}

void GameClient::AdvanceAttempt(std::chrono::milliseconds maxWait)
{
    const auto wait = std::min(maxWait, GetRemaining(m_attemptDeadline));
    if (wait > 0ms && m_socket->Available() == 0)
    {
        static_cast<void>(m_socket->WaitAvailable(1, wait));
    }

    const auto socketState = m_socket->Pump();
    if (socketState != WebSocketState_e::Connecting)
    {
        // A server that refuses a login closes the connection straight after the status, so what
        // arrived is read before the close counts as the failure.
        if (const auto result = m_handshake->Advance(*m_socket))
        {
            FinishLogin(*result);
            return;
        }

        if (socketState != WebSocketState_e::Open)
        {
            throw WebSocketError{"The connection closed during login"};
        }
    }

    if (Clock::now() >= m_attemptDeadline)
    {
        const auto waitingFor = socketState == WebSocketState_e::Open ? m_handshake->GetWaitingFor() : "connection to open"sv;
        throw std::runtime_error{std::format("Login timed out after {} ms waiting for the {}", m_options.loginTimeout.count(), waitingFor)};
    }
}

void GameClient::FinishLogin(const LoginResult_s& result)
{
    if (!result.reconnected)
    {
        m_state = GameState_s{};
        m_decoder.Reset();
        m_loggedMessageCount = 0;
        m_state.staffLevel = result.staffLevel;
    }

    m_handshake.reset();
    m_state.walkDestination.reset();
    m_writer.emplace(result.seed);
    m_reader.emplace(LoginHandshake::GetInboundSeed(result.seed));
    m_status = ClientStatus_e::InGame;
    m_reconnecting = false;
    m_attempt = 0;
    ++m_loginCount;
    m_lastReceive = Clock::now();
    m_lastSend = m_lastReceive;

    if (result.reconnected)
    {
        m_logger->Info("Reconnected to the existing session");
        return;
    }

    m_logger->Info("Logged in (staff level {})", result.staffLevel);
}

void GameClient::BeginReconnect(std::string_view reason)
{
    Disconnect();
    m_logger->Warning("Connection lost: {}", reason);
    if (!m_options.autoReconnect)
    {
        throw ConnectionLostError{std::format("Connection lost: {}", reason)};
    }

    m_lostReason = reason;
    m_reconnecting = true;
    m_attempt = 0;
    m_retryAt = Clock::now();
    m_status = ClientStatus_e::Connecting;
}

// Schedules the next attempt, or returns false so a failed login rethrows its error. A reconnect that
// gives up throws ConnectionLostError instead, because the session it was restoring is gone.
bool GameClient::ScheduleRetry(std::string_view error, bool retryable)
{
    const auto attemptsLeft = m_attempt < m_options.connectAttempts;
    if (m_reconnecting)
    {
        m_logger->Warning("Reconnect attempt {} of {} failed: {}", m_attempt, m_options.connectAttempts, error);
        if (!retryable)
        {
            throw ConnectionLostError{std::format("Connection lost ({}), and reconnecting failed: {}", m_lostReason, error)};
        }

        if (!attemptsLeft)
        {
            throw ConnectionLostError{std::format("Connection lost ({}), and {} reconnect attempts failed", m_lostReason, m_options.connectAttempts)};
        }
    }
    else
    {
        if (!retryable || !attemptsLeft)
        {
            return false;
        }

        m_logger->Warning("Login attempt {} of {} failed: {}", m_attempt, m_options.connectAttempts, error);
    }

    const auto delay = GetRetryDelay(m_options, m_attempt);
    m_logger->Info("Trying again in {} ms", delay.count());
    m_retryAt = Clock::now() + delay;
    m_status = ClientStatus_e::Connecting;
    return true;
}

void GameClient::ReleaseSocket() noexcept
{
    if (IsClosed(*m_socket))
    {
        return;
    }

    m_socket->Close();
    m_closingSockets.push_back(std::move(m_socket));
    m_socket = std::make_unique<WebSocketClient>(m_logger);
}

void GameClient::FreeClosedSockets() noexcept
{
    std::erase_if(m_closingSockets, [](const std::unique_ptr<WebSocketClient>& socket)
    {
        return IsClosed(*socket);
    });
}

void GameClient::ProcessInput()
{
    const auto available = m_socket->Available();
    if (available > 0)
    {
        auto bytes = std::vector<u8>(available);
        m_socket->Read(bytes);
        m_reader->Append(bytes);
    }

    while (const auto packet = m_reader->Next())
    {
        m_lastReceive = Clock::now();
        m_logger->Verbose("Received {} ({} bytes)", ServerProt::GetName(static_cast<u8>(packet->prot)), packet->payload.size());
        if (packet->prot == ServerProt_e::Logout)
        {
            m_logger->Info("The server ended the session");
            m_status = ClientStatus_e::LoggedOut;
            break;
        }

        m_decoder.Decode(packet->prot, packet->payload, m_state);
    }

    LogNewMessages();
}

void GameClient::SendKeepaliveIfIdle()
{
    if (!m_outgoing.empty() || Clock::now() - m_lastSend < m_options.keepaliveInterval)
    {
        return;
    }

    m_outgoing.push_back(ClientPackets::NoTimeout());
}

void GameClient::LogNewMessages()
{
    for (const auto* const message : m_state.GetMessagesAfter(m_loggedMessageCount))
    {
        if (message->sender.empty())
        {
            m_logger->Info("[{}] {}", DescribeMessageType(message->type), message->text);
            continue;
        }

        m_logger->Info("[{}] {}: {}", DescribeMessageType(message->type), message->sender, message->text);
    }

    m_loggedMessageCount = m_state.messageCount;
}
