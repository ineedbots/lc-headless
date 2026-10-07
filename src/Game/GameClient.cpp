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
    constexpr auto LOGOUT_POLL = 100ms;

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
}

GameClient::GameClient(std::shared_ptr<const Config_s> config, std::shared_ptr<Logger> logger, GameClientOptions_s options)
    : m_config{std::move(config)}
    , m_logger{std::move(logger)}
    , m_options{options}
    , m_socket{m_logger}
    , m_decoder{m_logger}
{
    assert(m_config && "GameClient needs a config");
    assert(m_logger && "GameClient needs a logger");
}

void GameClient::Login()
{
    assert(m_status != ClientStatus_e::InGame && m_status != ClientStatus_e::LoggingOut && "Login called during a session");
    try
    {
        Connect(false);
    }
    catch (const std::exception&)
    {
        Disconnect();
        throw;
    }
}

void GameClient::Pump(std::chrono::milliseconds maxWait)
{
    if (m_status != ClientStatus_e::InGame && m_status != ClientStatus_e::LoggingOut)
    {
        return;
    }

    auto lostReason = std::optional<std::string>{};
    try
    {
        if (maxWait > 0ms && m_socket.Available() == 0)
        {
            static_cast<void>(m_socket.WaitAvailable(1, maxWait));
        }

        const auto socketState = m_socket.Pump();
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

    Reconnect(*lostReason);
}

void GameClient::Logout(std::chrono::milliseconds timeout)
{
    if (m_status != ClientStatus_e::InGame)
    {
        return;
    }

    m_logger->Info("Logging out");
    Send(ClientPackets::IfButton(m_config->client.logoutComponent));
    m_status = ClientStatus_e::LoggingOut;

    const auto deadline = Clock::now() + timeout;
    while (m_status == ClientStatus_e::LoggingOut && Clock::now() < deadline)
    {
        Pump(std::min(GetRemaining(deadline), LOGOUT_POLL));
    }

    if (m_status != ClientStatus_e::LoggedOut)
    {
        m_logger->Warning("The server didn't confirm the logout within {} ms; closing the connection anyway", timeout.count());
    }

    Disconnect();
}

void GameClient::Disconnect() noexcept
{
    m_socket.Stop();
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
    m_socket.Send(bytes);
}

void GameClient::Connect(bool reconnect)
{
    const auto& server = m_config->server;
    const auto& account = m_config->account;
    if (reconnect)
    {
        m_logger->Info("Reconnecting as {}", account.username);
    }
    else
    {
        m_logger->Info("Logging in as {}", account.username);
    }

    m_reader.reset();
    m_writer.reset();
    m_outgoing.clear();
    m_socket.Connect({.url = server.url, .origin = server.origin, .tlsCaFile = server.tlsCaFile});
    if (!m_socket.WaitOpen(m_options.loginTimeout))
    {
        throw WebSocketError{std::format("Timed out after {} ms opening the connection", m_options.loginTimeout.count())};
    }

    const auto result = LoginHandshake::Run(m_socket, account, m_config->login, reconnect, m_options.loginTimeout);
    if (!result.reconnected)
    {
        m_state = GameState_s{};
        m_decoder.Reset();
        m_loggedMessageCount = 0;
        m_state.staffLevel = result.staffLevel;
    }

    m_state.walkDestination.reset();
    m_writer.emplace(result.seed);
    m_reader.emplace(LoginHandshake::GetInboundSeed(result.seed));
    m_status = ClientStatus_e::InGame;
    m_lastReceive = Clock::now();
    m_lastSend = m_lastReceive;

    if (result.reconnected)
    {
        m_logger->Info("Reconnected to the existing session");
        return;
    }

    m_logger->Info("Logged in (staff level {})", result.staffLevel);
}

void GameClient::ProcessInput()
{
    const auto available = m_socket.Available();
    if (available > 0)
    {
        auto bytes = std::vector<u8>(available);
        m_socket.Read(bytes);
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

void GameClient::Reconnect(std::string_view reason)
{
    Disconnect();
    m_logger->Warning("Connection lost: {}", reason);
    if (!m_options.autoReconnect)
    {
        throw ConnectionLostError{std::format("Connection lost: {}", reason)};
    }

    for (auto attempt = u32{1}; attempt <= m_options.reconnectAttempts; ++attempt)
    {
        if (attempt > 1)
        {
            std::this_thread::sleep_for(m_options.reconnectDelay);
        }

        try
        {
            Connect(true);
            return;
        }
        catch (const LoginError& e)
        {
            Disconnect();
            if (!e.IsRetryable())
            {
                throw ConnectionLostError{std::format("Connection lost ({}), and reconnecting failed: {}", reason, e.what())};
            }

            m_logger->Warning("Reconnect attempt {} of {} failed: {}", attempt, m_options.reconnectAttempts, e.what());
        }
        catch (const std::runtime_error& e)
        {
            Disconnect();
            m_logger->Warning("Reconnect attempt {} of {} failed: {}", attempt, m_options.reconnectAttempts, e.what());
        }
    }

    throw ConnectionLostError{std::format("Connection lost ({}), and {} reconnect attempts failed", reason, m_options.reconnectAttempts)};
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
