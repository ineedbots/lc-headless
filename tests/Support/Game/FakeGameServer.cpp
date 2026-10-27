#include "pch.hpp"
#include "FakeGameServer.hpp"
#include "../Cache/TestCache.hpp"
#include "../Io/ServerThread.hpp"

#include "Cache/GameCache_s.hpp"
#include "Config/AccountConfig_s.hpp"
#include "Config/Config_s.hpp"
#include "Config/Revision_e.hpp"
#include "Config/ServerSettings_s.hpp"
#include "Config/Transport_e.hpp"
#include "Game/Protocol/ClientProt.hpp"
#include "Game/Protocol/ServerProt.hpp"
#include "Io/Isaac.hpp"
#include "Io/Packet.hpp"
#include "Utils/BigUInt.hpp"

#include <boost/asio/as_tuple.hpp>
#include <boost/asio/buffer.hpp>
#include <boost/asio/co_spawn.hpp>
#include <boost/asio/detached.hpp>
#include <boost/asio/ip/address.hpp>
#include <boost/asio/post.hpp>
#include <boost/asio/use_awaitable.hpp>
#include <boost/asio/write.hpp>
#include <boost/beast/core/flat_buffer.hpp>
#include <boost/beast/http/field.hpp>
#include <boost/beast/websocket/rfc6455.hpp>
#include <boost/beast/websocket/stream.hpp>

namespace
{
    namespace asio = boost::asio;
    namespace websocket = boost::beast::websocket;
    using Tcp = asio::ip::tcp;

    constexpr auto LOOPBACK_HOST = "127.0.0.1";
    constexpr auto SUBPROTOCOL = "binary";
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
    constexpr auto READ_SIZE = std::size_t{4096};

    const auto AS_TUPLE = asio::as_tuple(asio::use_awaitable);

    std::vector<u8> ToBytes(const Packet& packet)
    {
        const auto data = packet.GetData();
        return {data.begin(), data.end()};
    }
}

FakeServerClient_s::FakeServerClient_s(Tcp::socket tcp, bool rawSocket)
    : socket{std::move(tcp)}
    , raw{rawSocket}
{
}

FakeGameServer::FakeGameServer(Script onLogin, Revision_e revision, Transport_e transport)
    : m_onLogin{std::move(onLogin)}
    , m_revision{revision}
    , m_transport{transport}
    , m_acceptor{m_thread.GetContext(), Tcp::endpoint{asio::ip::make_address(LOOPBACK_HOST), 0}}
    , m_port{m_acceptor.local_endpoint().port()}
{
    asio::co_spawn(m_thread.GetContext(), Accept(), asio::detached);
}

template <typename TCondition>
bool FakeGameServer::WaitFor(TCondition condition)
{
    auto lock = std::unique_lock{m_mutex};
    return m_changed.wait_for(lock, WAIT, condition);
}

FakeGameServer::~FakeGameServer()
{
    m_thread.Stop();
}

ServerSettings_s FakeGameServer::MakeServerSettings() const
{
    return {.transport = m_transport, .host = LOOPBACK_HOST, .port = m_port};
}

Revision_e FakeGameServer::GetRevision() const
{
    return m_revision;
}

Config_s FakeGameServer::MakeConfig() const
{
    auto config = Config_s{};
    config.server = MakeServerSettings();
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
    TestCache::AddObj(cache, 385, "Shark").cost = 200;
    TestCache::AddObj(cache, 563, "Law rune").cost = 240;
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
    const auto lock = std::scoped_lock{m_mutex};
    if (m_client)
    {
        Write(m_client, std::nullopt);
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

asio::awaitable<void> FakeGameServer::Accept()
{
    while (true)
    {
        auto [error, socket] = co_await m_acceptor.async_accept(AS_TUPLE);
        if (error)
        {
            co_return;
        }

        asio::co_spawn(m_acceptor.get_executor(), Serve(std::move(socket)), asio::detached);
    }
}

asio::awaitable<void> FakeGameServer::Serve(Tcp::socket socket)
{
    const auto client = std::make_shared<FakeServerClient_s>(std::move(socket), m_transport == Transport_e::Tcp);
    if (!client->raw)
    {
        client->socket.set_option(websocket::stream_base::decorator([](websocket::response_type& response)
        {
            response.set(boost::beast::http::field::sec_websocket_protocol, SUBPROTOCOL);
        }));

        const auto [acceptError] = co_await client->socket.async_accept(AS_TUPLE);
        if (acceptError)
        {
            co_return;
        }

        client->socket.binary(true);
    }

    {
        const auto lock = std::scoped_lock{m_mutex};
        m_client = client;
        m_stage = Stage_e::SeedRequest;
        m_fromClient.reset();
        m_toClient.reset();
        m_gameBytes.clear();
        m_partialProt.reset();
    }

    if (m_revision < Revision_e::Rev274)
    {
        SendSeed(client, false);
    }

    if (client->raw)
    {
        co_await ReadStream(client);
    }
    else
    {
        co_await ReadMessages(client);
    }

    {
        const auto lock = std::scoped_lock{m_mutex};
        if (m_client == client)
        {
            m_client.reset();
        }
    }

    m_changed.notify_all();
}

asio::awaitable<void> FakeGameServer::ReadMessages(Client client)
{
    auto buffer = boost::beast::flat_buffer{};
    while (true)
    {
        const auto [error, size] = co_await client->socket.async_read(buffer, AS_TUPLE);
        if (error)
        {
            co_return;
        }

        const auto* const data = static_cast<const u8*>(buffer.cdata().data());
        const auto message = std::vector<u8>(data, data + size);
        buffer.consume(size);
        OnMessage(client, message);
    }
}

asio::awaitable<void> FakeGameServer::ReadStream(Client client)
{
    auto buffer = std::array<u8, READ_SIZE>{};
    while (true)
    {
        const auto [error, size] = co_await client->socket.next_layer().async_read_some(asio::buffer(buffer), AS_TUPLE);
        if (error)
        {
            co_return;
        }

        OnMessage(client, std::span{buffer}.first(size));
    }
}

void FakeGameServer::OnMessage(const Client& client, std::span<const u8> bytes)
{
    auto stage = Stage_e::SeedRequest;
    {
        const auto lock = std::scoped_lock{m_mutex};
        stage = m_stage;
    }

    switch (stage)
    {
    case Stage_e::SeedRequest:
        HandleSeedRequest(client, bytes);
        return;
    case Stage_e::Login:
        HandleLogin(client, bytes);
        return;
    case Stage_e::InGame:
        HandleGamePackets(client, bytes);
        return;
    }
}

void FakeGameServer::HandleSeedRequest(const Client& client, std::span<const u8> bytes)
{
    if (m_revision < Revision_e::Rev274)
    {
        AddError("A 225 client sent something before its seed arrived");
        return;
    }

    if (bytes.size() != SEED_REQUEST_SIZE || bytes[0] != 14)
    {
        AddError("The first message wasn't a 2-byte seed request");
        return;
    }

    SendSeed(client, true);
}

// Later revisions put 8 zero bytes and a status of 0 before the seed.
void FakeGameServer::SendSeed(const Client& client, bool withHeader)
{
    auto response = Packet{};
    if (withHeader)
    {
        response.P8(0);
        response.P1(0);
    }

    response.P8(SERVER_SEED);

    const auto lock = std::scoped_lock{m_mutex};
    if (m_stalled)
    {
        return;
    }

    m_stage = Stage_e::Login;
    Write(client, ToBytes(response));
}

void FakeGameServer::HandleLogin(const Client& client, std::span<const u8> bytes)
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
        if (status == LOGGED_IN && m_revision >= Revision_e::Rev274)
        {
            response.P1(0);
            response.P1(1);
        }

        Write(client, ToBytes(response));
        if (!IsLoggedIn(status) && status != RECONNECTED)
        {
            Write(client, std::nullopt);
        }
    }

    m_changed.notify_all();

    if (!IsLoggedIn(status) && status != RECONNECTED)
    {
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
    if (m_revision < Revision_e::Rev274)
    {
        return packet.G1() == revision;
    }

    return packet.G1() == REVISION_MARKER && packet.G2() == revision;
}

bool FakeGameServer::IsLoggedIn(u8 status) const
{
    return status == LOGGED_IN || (m_revision < Revision_e::Rev274 && status == LOGGED_IN_STAFF_225);
}

void FakeGameServer::HandleGamePackets(const Client& client, std::span<const u8> bytes)
{
    auto loggedOut = false;
    {
        const auto lock = std::scoped_lock{m_mutex};
        m_gameBytes.insert(m_gameBytes.end(), bytes.begin(), bytes.end());

        // A packet can end in a later read, so each is taken only once it's whole. Its opcode is read once, because
        // reading it steps the cipher.
        const auto& table = ClientProt::GetTable(m_revision);
        auto packet = Packet{m_gameBytes};
        auto used = std::size_t{0};
        while (true)
        {
            if (!m_partialProt)
            {
                if (packet.GetAvailable() == 0)
                {
                    break;
                }

                const auto opcode = static_cast<u8>(packet.G1() - static_cast<u32>(m_fromClient->NextInt()));
                const auto found = table.byOpcode[opcode];
                if (!found)
                {
                    m_errors.push_back(std::format("Client sent unknown opcode {}", opcode));
                    used = m_gameBytes.size();
                    break;
                }

                m_partialProt = *found;
                used = packet.GetPos();
            }

            const auto prot = *m_partialProt;
            const auto size = table.byProt[static_cast<std::size_t>(prot)]->size;
            auto lengthSize = std::size_t{0};
            if (size == ClientProt::VAR_BYTE)
            {
                lengthSize = 1;
            }
            else if (size == ClientProt::VAR_SHORT)
            {
                lengthSize = 2;
            }

            if (packet.GetAvailable() < lengthSize)
            {
                break;
            }

            auto length = static_cast<std::size_t>(size);
            if (lengthSize == 1)
            {
                length = packet.G1();
            }
            else if (lengthSize == 2)
            {
                length = packet.G2();
            }

            if (packet.GetAvailable() < length)
            {
                break;
            }

            auto payload = std::vector<u8>(length);
            packet.GData(payload);
            used = packet.GetPos();
            m_partialProt.reset();

            loggedOut = loggedOut || (!m_ignoreLogout && prot == ClientProt_e::IfButton && Packet{payload}.G2() == LOGOUT_COMPONENT);
            m_packets.push_back({.prot = prot, .payload = std::move(payload)});
        }

        m_gameBytes.erase(m_gameBytes.begin(), m_gameBytes.begin() + static_cast<std::ptrdiff_t>(used));

        if (loggedOut)
        {
            SendLocked(ServerProt_e::Logout, {});
            Write(client, std::nullopt);
        }
    }

    m_changed.notify_all();
}

void FakeGameServer::SendLocked(ServerProt_e prot, std::span<const u8> payload)
{
    if (!m_client || !m_toClient)
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
    Write(m_client, ToBytes(packet));
}

void FakeGameServer::Write(const Client& client, std::optional<std::vector<u8>> bytes)
{
    asio::post(m_thread.GetContext(), [client, bytes = std::move(bytes)]() mutable
    {
        client->outgoing.push_back(std::move(bytes));
        WriteNext(client);
    });
}

// One write at a time, as Beast requires. A close waits for the writes queued before it.
void FakeGameServer::WriteNext(const Client& client)
{
    if (client->writing || client->outgoing.empty())
    {
        return;
    }

    client->writing = true;
    auto& next = client->outgoing.front();
    if (!next)
    {
        if (client->raw)
        {
            // A FIN, as the engine ends a TCP connection. The read goes on until the client closes too.
            auto ignored = boost::system::error_code{};
            client->socket.next_layer().shutdown(Tcp::socket::shutdown_send, ignored);
            client->outgoing.clear();
            return;
        }

        client->socket.async_close(websocket::close_code::normal, [client](boost::system::error_code)
        {
            client->outgoing.clear();
        });
        return;
    }

    auto onWrite = [client](boost::system::error_code error, std::size_t)
    {
        client->writing = false;
        client->outgoing.pop_front();
        if (error)
        {
            client->outgoing.clear();
            return;
        }

        WriteNext(client);
    };

    if (client->raw)
    {
        asio::async_write(client->socket.next_layer(), asio::buffer(*next), std::move(onWrite));
        return;
    }

    client->socket.async_write(asio::buffer(*next), std::move(onWrite));
}

void FakeGameServer::AddError(std::string error)
{
    {
        const auto lock = std::scoped_lock{m_mutex};
        m_errors.push_back(std::move(error));
    }

    m_changed.notify_all();
}
