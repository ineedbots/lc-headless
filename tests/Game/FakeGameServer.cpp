#include "pch.hpp"
#include "FakeGameServer.hpp"
#include "../LoopbackPort.hpp"

#include "Core/BigUInt.hpp"
#include "Core/ConfigFile.hpp"
#include "Game/Protocol/ClientProt.hpp"
#include "Game/Protocol/ServerProt.hpp"
#include "Io/Isaac.hpp"
#include "Io/Packet.hpp"

#include <ixwebsocket/IXConnectionState.h>
#include <ixwebsocket/IXWebSocket.h>
#include <ixwebsocket/IXWebSocketMessage.h>
#include <ixwebsocket/IXWebSocketMessageType.h>
#include <ixwebsocket/IXWebSocketServer.h>

namespace
{
    constexpr auto FIRST_PORT = 47100;
    constexpr auto LAST_PORT = 47199;
    constexpr auto LOOPBACK_HOST = "127.0.0.1";
    constexpr auto WAIT = 5s;
    constexpr auto SERVER_SEED = s64{0x0123456789ABCDEF};
    constexpr auto SEED_REQUEST_SIZE = std::size_t{2};
    constexpr auto LOGIN_HEADER_SIZE = std::size_t{2};
    constexpr auto CRC_BYTES = std::size_t{36};
    constexpr auto LOGGED_IN = u8{2};
    constexpr auto RECONNECTED = u8{15};
    constexpr auto SERVER_SEED_OFFSET = u32{50};
    constexpr auto RSA_MODULUS_HEX_DIGITS = std::size_t{128};

    std::span<const u8> AsBytes(const std::string& text)
    {
        return {reinterpret_cast<const u8*>(text.data()), text.size()};
    }

    std::string ToText(std::span<const u8> bytes)
    {
        return {reinterpret_cast<const char*>(bytes.data()), bytes.size()};
    }
}

FakeGameServer::FakeGameServer(Script onLogin)
    : m_onLogin{std::move(onLogin)}
{
    for (auto port = FIRST_PORT; port <= LAST_PORT; ++port)
    {
        if (!LoopbackPort::IsFree(port))
        {
            continue;
        }

        auto server = std::make_unique<ix::WebSocketServer>(port, LOOPBACK_HOST);
        server->disablePerMessageDeflate();
        server->setOnClientMessageCallback([this](std::shared_ptr<ix::ConnectionState>, ix::WebSocket& connection, const ix::WebSocketMessagePtr& message)
        {
            OnMessage(connection, *message);
        });

        if (!server->listen().first)
        {
            continue;
        }

        server->start();
        m_server = std::move(server);
        return;
    }

    throw std::runtime_error{"No free port for the fake game server"};
}

template <typename TCondition>
bool FakeGameServer::WaitFor(TCondition condition)
{
    auto lock = std::unique_lock{m_mutex};
    return m_changed.wait_for(lock, WAIT, condition);
}

FakeGameServer::~FakeGameServer()
{
    m_server->stop();
}

std::string FakeGameServer::Url() const
{
    return std::format("ws://{}:{}/", LOOPBACK_HOST, m_server->getPort());
}

Config_s FakeGameServer::MakeConfig() const
{
    auto config = Config_s{};
    config.server.url = Url();
    config.login.rsaModulus = BigUInt::Parse("0x" + std::string(RSA_MODULUS_HEX_DIGITS, 'f'));
    config.login.rsaExponent = BigUInt::Parse("1");
    config.client.logoutComponent = LOGOUT_COMPONENT;
    return config;
}

AccountSettings_s FakeGameServer::MakeAccount()
{
    return {.username = USERNAME, .password = PASSWORD};
}

void FakeGameServer::SetLoginStatus(u8 status)
{
    const auto lock = std::scoped_lock{m_mutex};
    m_loginStatus = status;
}

void FakeGameServer::SetStalled(bool stalled)
{
    const auto lock = std::scoped_lock{m_mutex};
    m_stalled = stalled;
}

void FakeGameServer::SetIgnoreLogout(bool ignore)
{
    const auto lock = std::scoped_lock{m_mutex};
    m_ignoreLogout = ignore;
}

void FakeGameServer::Send(ServerProt_e prot, std::span<const u8> payload)
{
    const auto lock = std::scoped_lock{m_mutex};
    SendLocked(prot, payload);
}

void FakeGameServer::Close()
{
    auto* connection = static_cast<ix::WebSocket*>(nullptr);
    {
        const auto lock = std::scoped_lock{m_mutex};
        connection = m_connection;
    }

    if (connection != nullptr)
    {
        connection->close();
    }
}

bool FakeGameServer::WaitForPacket(ClientProt_e prot, std::size_t count)
{
    return WaitFor([this, prot, count]
    {
        return static_cast<std::size_t>(std::ranges::count(m_packets, prot, &ReceivedPacket_s::prot)) >= count;
    });
}

bool FakeGameServer::WaitForLogins(std::size_t count)
{
    return WaitFor([this, count]
    {
        return m_loginOpcodes.size() >= count;
    });
}

std::vector<ReceivedPacket_s> FakeGameServer::GetPackets(ClientProt_e prot) const
{
    const auto lock = std::scoped_lock{m_mutex};
    auto packets = std::vector<ReceivedPacket_s>{};
    for (const auto& packet : m_packets)
    {
        if (packet.prot == prot)
        {
            packets.push_back(packet);
        }
    }

    return packets;
}

std::vector<u8> FakeGameServer::GetLoginOpcodes() const
{
    const auto lock = std::scoped_lock{m_mutex};
    return m_loginOpcodes;
}

std::vector<std::string> FakeGameServer::GetErrors() const
{
    const auto lock = std::scoped_lock{m_mutex};
    return m_errors;
}

void FakeGameServer::OnMessage(ix::WebSocket& connection, const ix::WebSocketMessage& message)
{
    if (message.type == ix::WebSocketMessageType::Open)
    {
        const auto lock = std::scoped_lock{m_mutex};
        m_connection = &connection;
        m_stage = Stage_e::SeedRequest;
        m_fromClient.reset();
        m_toClient.reset();
        return;
    }

    if (message.type == ix::WebSocketMessageType::Close)
    {
        {
            const auto lock = std::scoped_lock{m_mutex};
            if (m_connection == &connection)
            {
                m_connection = nullptr;
            }
        }

        m_changed.notify_all();
        return;
    }

    if (message.type != ix::WebSocketMessageType::Message)
    {
        return;
    }

    const auto bytes = AsBytes(message.str);
    auto stage = Stage_e::SeedRequest;
    {
        const auto lock = std::scoped_lock{m_mutex};
        stage = m_stage;
    }

    switch (stage)
    {
    case Stage_e::SeedRequest:
        HandleSeedRequest(connection, bytes);
        return;
    case Stage_e::Login:
        HandleLogin(connection, bytes);
        return;
    case Stage_e::InGame:
        HandleGamePackets(connection, bytes);
        return;
    }
}

void FakeGameServer::HandleSeedRequest(ix::WebSocket& connection, std::span<const u8> bytes)
{
    if (bytes.size() != SEED_REQUEST_SIZE || bytes[0] != 14)
    {
        AddError("The first message wasn't a 2-byte seed request");
        return;
    }

    auto response = Packet{};
    response.P8(0);
    response.P1(0);
    response.P8(SERVER_SEED);
    {
        const auto lock = std::scoped_lock{m_mutex};
        if (m_stalled)
        {
            return;
        }

        m_stage = Stage_e::Login;
    }

    connection.sendBinary(ToText(response.GetData()));
}

void FakeGameServer::HandleLogin(ix::WebSocket& connection, std::span<const u8> bytes)
{
    auto packet = Packet{bytes};
    const auto opcode = packet.G1();
    const auto bodySize = packet.G1();
    if (bytes.size() != LOGIN_HEADER_SIZE + bodySize || packet.G1() != 0xFF || packet.G2() != LoginSettings_s::SUPPORTED_REVISION)
    {
        AddError("The login request's length, marker or revision is wrong");
        return;
    }

    packet.G1();
    packet.SetPos(packet.GetPos() + CRC_BYTES);
    const auto blockSize = packet.G1();
    if (packet.GetAvailable() != blockSize || packet.G1() != 10)
    {
        AddError("The login block's length or marker is wrong");
        return;
    }

    auto seed = std::array<s32, 4>{};
    for (auto& word : seed)
    {
        word = packet.G4();
    }

    auto inbound = seed;
    for (auto& word : inbound)
    {
        word = static_cast<s32>(static_cast<u32>(word) + SERVER_SEED_OFFSET);
    }

    auto status = u8{0};
    {
        const auto lock = std::scoped_lock{m_mutex};
        m_loginOpcodes.push_back(opcode);
        m_fromClient.emplace(seed);
        m_toClient.emplace(inbound);
        m_stage = Stage_e::InGame;
        status = m_loginStatus;

        auto response = Packet{};
        response.P1(status);
        if (status == LOGGED_IN)
        {
            response.P1(0);
            response.P1(1);
        }

        connection.sendBinary(ToText(response.GetData()));
    }

    m_changed.notify_all();
    if (status != LOGGED_IN && status != RECONNECTED)
    {
        connection.close();
        return;
    }

    if (m_onLogin)
    {
        m_onLogin(*this, opcode == 18);
    }
}

void FakeGameServer::HandleGamePackets(ix::WebSocket& connection, std::span<const u8> bytes)
{
    auto loggedOut = false;
    {
        const auto lock = std::scoped_lock{m_mutex};
        auto packet = Packet{bytes};
        while (packet.GetAvailable() > 0)
        {
            const auto opcode = static_cast<u8>(packet.G1() - static_cast<u32>(m_fromClient->NextInt()));
            const auto size = ClientProt::GetSize(opcode);
            if (!size)
            {
                m_errors.push_back(std::format("Client sent unknown opcode {}", opcode));
                break;
            }

            const auto length = *size == ClientProt::VAR_BYTE ? std::size_t{packet.G1()} : static_cast<std::size_t>(*size);
            auto payload = std::vector<u8>(length);
            packet.GData(payload);

            const auto prot = static_cast<ClientProt_e>(opcode);
            loggedOut = loggedOut || (!m_ignoreLogout && prot == ClientProt_e::IfButton && Packet{payload}.G2() == LOGOUT_COMPONENT);
            m_packets.push_back({.prot = prot, .payload = std::move(payload)});
        }

        if (loggedOut)
        {
            SendLocked(ServerProt_e::Logout, {});
        }
    }

    m_changed.notify_all();
    if (loggedOut)
    {
        connection.close();
    }
}

void FakeGameServer::SendLocked(ServerProt_e prot, std::span<const u8> payload)
{
    if (m_connection == nullptr || !m_toClient)
    {
        m_errors.push_back(std::format("Send of {} with no client in game", ServerProt::GetName(static_cast<u8>(prot))));
        return;
    }

    auto packet = Packet{};
    packet.P1(static_cast<s32>(static_cast<u32>(prot) + static_cast<u32>(m_toClient->NextInt())));
    const auto size = ServerProt::GetSize(static_cast<u8>(prot));
    if (size == ServerProt::VAR_BYTE)
    {
        packet.P1(static_cast<s32>(payload.size()));
    }
    else if (size == ServerProt::VAR_SHORT)
    {
        packet.P2(static_cast<s32>(payload.size()));
    }

    packet.PData(payload);
    m_connection->sendBinary(ToText(packet.GetData()));
}

void FakeGameServer::AddError(std::string error)
{
    {
        const auto lock = std::scoped_lock{m_mutex};
        m_errors.push_back(std::move(error));
    }

    m_changed.notify_all();
}
