#include "pch.hpp"
#include "FakeGameServer.hpp"
#include "../Cache/TestCache.hpp"
#include "../LoopbackPort.hpp"

#include "Cache/GameCache_s.hpp"
#include "Config/AccountConfig_s.hpp"
#include "Config/Config_s.hpp"
#include "Config/Revision_e.hpp"
#include "Game/Protocol/ClientProt.hpp"
#include "Game/Protocol/ServerProt.hpp"
#include "Io/Isaac.hpp"
#include "Io/Packet.hpp"
#include "Utils/BigUInt.hpp"

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
    constexpr auto LOGGED_IN_STAFF_225 = u8{18};
    constexpr auto REVISION_MARKER = u8{0xFF};
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

FakeGameServer::FakeGameServer(Script onLogin, Revision_e revision)
    : m_onLogin{std::move(onLogin)}
    , m_revision{revision}
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

Revision_e FakeGameServer::GetRevision() const
{
    return m_revision;
}

Config_s FakeGameServer::MakeConfig() const
{
    auto config = Config_s{};
    config.server.url = Url();
    config.login.rsaModulus = BigUInt::Parse("0x" + std::string(RSA_MODULUS_HEX_DIGITS, 'f'));
    config.login.rsaExponent = BigUInt::Parse("1");
    config.login.revision = m_revision;
    return config;
}

AccountSettings_s FakeGameServer::MakeAccount()
{
    return {.username = USERNAME, .password = PASSWORD};
}

std::shared_ptr<const GameCache_s> FakeGameServer::MakeCache(Revision_e revision)
{
    auto cache = GameCache_s{};
    cache.revision = revision;
    TestCache::SetComponents(cache);
    cache.logoutComponent = LOGOUT_COMPONENT;
    // The NPC TestWorld sends, so scripts can use its options by name.
    TestCache::AddNpc(cache, 50, "Goblin", {"Talk-to", "Attack"});
    TestCache::SetTradeScreen(cache);
    TestCache::SetChatInterfaces(cache);
    TestCache::SetBankScreen(cache);
    TestCache::SetShop(cache);
    TestCache::AddObj(cache, 995, "Coins").stackable = true;
    TestCache::AddObj(cache, 1511, "Logs");
    TestCache::AddObj(cache, 526, "Bones", {}, {"Bury"});
    return std::make_shared<const GameCache_s>(std::move(cache));
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
    // Held across close(), as SendLocked holds it across a send: the server frees a connection once
    // its Close callback returns, and that callback waits for this lock to clear m_connection.
    const auto lock = std::scoped_lock{m_mutex};

    if (m_connection != nullptr)
    {
        m_connection->close();
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
        {
            const auto lock = std::scoped_lock{m_mutex};
            m_connection = &connection;
            m_stage = Stage_e::SeedRequest;
            m_fromClient.reset();
            m_toClient.reset();
        }

        if (m_revision < Revision_e::Rev289)
        {
            SendSeed(connection, false);
        }

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
    if (m_revision < Revision_e::Rev289)
    {
        AddError("A 225 client sent something before its seed arrived");
        return;
    }

    if (bytes.size() != SEED_REQUEST_SIZE || bytes[0] != 14)
    {
        AddError("The first message wasn't a 2-byte seed request");
        return;
    }

    SendSeed(connection, true);
}

// 289 puts 8 zero bytes and a status of 0 before the seed.
void FakeGameServer::SendSeed(ix::WebSocket& connection, bool withHeader)
{
    auto response = Packet{};
    if (withHeader)
    {
        response.P8(0);
        response.P1(0);
    }

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
    if (bytes.size() != LOGIN_HEADER_SIZE + bodySize || !ReadRevision(packet))
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
        if (status == LOGGED_IN && m_revision >= Revision_e::Rev289)
        {
            response.P1(0);
            response.P1(1);
        }

        connection.sendBinary(ToText(response.GetData()));
    }

    m_changed.notify_all();

    if (!IsLoggedIn(status) && status != RECONNECTED)
    {
        connection.close();
        return;
    }

    if (m_onLogin)
    {
        m_onLogin(*this, opcode == 18);
    }
}

bool FakeGameServer::ReadRevision(Packet& packet) const
{
    const auto revision = static_cast<u16>(m_revision);
    if (m_revision < Revision_e::Rev289)
    {
        return packet.G1() == revision;
    }

    return packet.G1() == REVISION_MARKER && packet.G2() == revision;
}

bool FakeGameServer::IsLoggedIn(u8 status) const
{
    return status == LOGGED_IN || (m_revision < Revision_e::Rev289 && status == LOGGED_IN_STAFF_225);
}

void FakeGameServer::HandleGamePackets(ix::WebSocket& connection, std::span<const u8> bytes)
{
    auto loggedOut = false;
    {
        const auto lock = std::scoped_lock{m_mutex};
        auto packet = Packet{bytes};
        while (packet.GetAvailable() > 0)
        {
            const auto& table = ClientProt::GetTable(m_revision);
            const auto opcode = static_cast<u8>(packet.G1() - static_cast<u32>(m_fromClient->NextInt()));
            const auto found = table.byOpcode[opcode];
            if (!found)
            {
                m_errors.push_back(std::format("Client sent unknown opcode {}", opcode));
                break;
            }

            const auto prot = *found;
            const auto size = table.byProt[static_cast<std::size_t>(prot)]->size;
            auto length = static_cast<std::size_t>(size);
            if (size == ClientProt::VAR_BYTE)
            {
                length = packet.G1();
            }
            else if (size == ClientProt::VAR_SHORT)
            {
                length = packet.G2();
            }

            auto payload = std::vector<u8>(length);
            packet.GData(payload);

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
        m_errors.push_back(std::format("Send of {} with no client in game", ServerProt::GetName(prot)));
        return;
    }

    const auto& wire = ServerProt::GetTable(m_revision).byProt[static_cast<std::size_t>(prot)];
    if (!wire)
    {
        m_errors.push_back(std::format("Send of {}, which revision {} doesn't have", ServerProt::GetName(prot), static_cast<u16>(m_revision)));
        return;
    }

    auto packet = Packet{};
    packet.P1(static_cast<s32>(u32{wire->opcode} + static_cast<u32>(m_toClient->NextInt())));

    const auto size = wire->size;
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
