#include "pch.hpp"
#include "../Support/Io/TestServer.hpp"
#include "../Support/LogCapture.hpp"

#include "Game/Net/LoginHandshake.hpp"
#include "Game/Net/Error/LoginError.hpp"
#include "Io/Packet.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/generators/catch_generators.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>
#include <numeric>

namespace
{
    using Bytes = std::vector<u8>;
    constexpr auto WAIT = 5s;

    LoginSettings_s LoginSettings()
    {
        return {.rsaModulus = BigUInt::Parse("0x" + std::string(1024, 'f')), .rsaExponent = BigUInt::Parse("1")};
    }

    TestServer::Script ReplyScript(Revision_e revision, Bytes reply)
    {
        return [revision, reply = std::move(reply)](ServerSession& session) -> boost::asio::awaitable<void>
        {
            if (revision >= Revision_e::Rev274)
            {
                co_await session.Receive();
                co_await session.Send(Bytes(9, 0));
            }
            co_await session.Send(Bytes{1, 2, 3, 4, 5, 6, 7, 8});
            co_await session.Receive();
            co_await session.Send(reply);
            co_await session.ReceiveUntilClosed();
        };
    }

    class HandshakeFixture
    {
    public:
        HandshakeFixture(Revision_e revision, TestServer::Script script, bool reconnect = false)
            : server{std::move(script)}
            , connection{*loop, {.host = "127.0.0.1", .port = server.GetPort()}, capture.GetLogger()}
            , handshake{Protocol{revision}, account, login, crcs, reconnect}
        {
            REQUIRE(connection.WaitOpen(WAIT));
        }

        void Begin(Revision_e revision)
        {
            if (revision >= Revision_e::Rev274)
            {
                CHECK_FALSE(handshake.Advance(connection));
                REQUIRE(connection.WaitAvailable(17, WAIT));
            }
            else
            {
                REQUIRE(connection.WaitAvailable(8, WAIT));
            }
            CHECK_FALSE(handshake.Advance(connection));
            CHECK(handshake.GetWaitingFor() == "login response");
        }

        void Acknowledge()
        {
            const auto ack = std::array<u8, 1>{0};
            connection.Send(ack);
        }

        LogCapture capture;
        std::shared_ptr<NetLoop> loop = NetLoop::Create();
        TestServer server;
        Connection connection;
        AccountSettings_s account{.username = "bot", .password = "secret"};
        LoginSettings_s login = LoginSettings();
        std::array<s32, GameCache_s::CRC_COUNT> crcs{};
        LoginHandshake handshake;
    };
}

TEST_CASE("LoginHandshake waits for complete seed and login details without consuming game bytes", "[LoginHandshakeCoverage]")
{
    const auto revision = GENERATE(Revision_e::Rev274, Revision_e::Rev289);
    auto fixture = HandshakeFixture{revision, [](ServerSession& session) -> boost::asio::awaitable<void>
    {
        co_await session.Receive(); // seed request
        co_await session.Send(Bytes(8, 0));
        co_await session.Receive(); // release final header byte and partial seed
        co_await session.Send(Bytes{0, 1, 2, 3, 4, 5, 6, 7});
        co_await session.Receive(); // release final seed byte
        co_await session.Send(Bytes{8});
        co_await session.Receive(); // login request
        co_await session.Send(Bytes{2});
        co_await session.Receive(); // release partial login details
        co_await session.Send(Bytes{3});
        co_await session.Receive(); // release tracking flag and game bytes
        co_await session.Send(Bytes{1, 0xAB, 0xCD});
        co_await session.ReceiveUntilClosed();
    }};
    CHECK(fixture.handshake.GetWaitingFor() == "seed response");
    CHECK_FALSE(fixture.handshake.Advance(fixture.connection));
    REQUIRE(fixture.connection.WaitAvailable(8, WAIT));
    CHECK_FALSE(fixture.handshake.Advance(fixture.connection));
    CHECK(fixture.connection.Available() == 8);
    fixture.Acknowledge();
    REQUIRE(fixture.connection.WaitAvailable(16, WAIT));
    CHECK_FALSE(fixture.handshake.Advance(fixture.connection));
    CHECK(fixture.handshake.GetWaitingFor() == "server seed");
    CHECK(fixture.connection.Available() == 7);
    fixture.Acknowledge();
    REQUIRE(fixture.connection.WaitAvailable(8, WAIT));
    CHECK_FALSE(fixture.handshake.Advance(fixture.connection));
    CHECK(fixture.handshake.GetWaitingFor() == "login response");
    REQUIRE(fixture.connection.WaitAvailable(1, WAIT));
    CHECK_FALSE(fixture.handshake.Advance(fixture.connection));
    CHECK(fixture.handshake.GetWaitingFor() == "staff level and mouse tracking flag");
    fixture.Acknowledge();
    REQUIRE(fixture.connection.WaitAvailable(1, WAIT));
    CHECK_FALSE(fixture.handshake.Advance(fixture.connection));
    CHECK(fixture.connection.Available() == 1);
    fixture.Acknowledge();
    REQUIRE(fixture.connection.WaitAvailable(4, WAIT));
    const auto result = fixture.handshake.Advance(fixture.connection);
    REQUIRE(result);
    CHECK(result->staffLevel == 3);
    CHECK(result->mouseTracking);
    CHECK_FALSE(result->reconnected);
    CHECK(result->seed[2] == 0x01020304);
    CHECK(result->seed[3] == 0x05060708);
    CHECK(fixture.handshake.GetWaitingFor() == "nothing");
    const auto repeated = fixture.handshake.Advance(fixture.connection);
    REQUIRE(repeated);
    CHECK(repeated->seed == result->seed);
    CHECK(fixture.connection.Available() == 2);
    auto trailing = std::array<u8, 2>{};
    fixture.connection.Read(trailing);
    CHECK(trailing == std::array<u8, 2>{0xAB, 0xCD});
}

TEST_CASE("LoginHandshake reads revision 225 success without later revision details", "[LoginHandshakeCoverage]")
{
    const auto status = GENERATE(u8{2}, u8{18});
    auto fixture = HandshakeFixture{Revision_e::Rev225, ReplyScript(Revision_e::Rev225, {status, 0xAB})};
    CHECK(fixture.handshake.GetWaitingFor() == "server seed");
    fixture.Begin(Revision_e::Rev225);
    REQUIRE(fixture.connection.WaitAvailable(2, WAIT));
    const auto result = fixture.handshake.Advance(fixture.connection);
    REQUIRE(result);
    CHECK(result->staffLevel == (status == 18 ? 1 : 0));
    CHECK_FALSE(result->mouseTracking);
    CHECK_FALSE(result->reconnected);
    CHECK(fixture.connection.Available() == 1);
}

TEST_CASE("LoginHandshake reconnect success leaves the following game bytes unread", "[LoginHandshakeCoverage]")
{
    const auto revision = GENERATE(Revision_e::Rev225, Revision_e::Rev274, Revision_e::Rev289);
    auto fixture = HandshakeFixture{revision, ReplyScript(revision, {15, 0xAB}), true};
    fixture.Begin(revision);
    REQUIRE(fixture.connection.WaitAvailable(2, WAIT));
    const auto result = fixture.handshake.Advance(fixture.connection);
    REQUIRE(result);
    CHECK(result->reconnected);
    CHECK(fixture.handshake.GetWaitingFor() == "nothing");
    CHECK(fixture.connection.Available() == 1);
    const auto record = fixture.server.GetRecord();
    REQUIRE_FALSE(record.messages.empty());
    CHECK(record.messages.back().front() == LoginHandshake::RECONNECT_LOGIN);
}

TEST_CASE("LoginHandshake rejects a seed response before sending credentials", "[LoginHandshakeCoverage]")
{
    auto fixture = HandshakeFixture{Revision_e::Rev289, [](ServerSession& session) -> boost::asio::awaitable<void>
    {
        co_await session.Receive();
        auto header = Bytes(9, 0);
        header.back() = 7;
        co_await session.Send(std::move(header));
        co_await session.ReceiveUntilClosed();
    }};
    CHECK_FALSE(fixture.handshake.Advance(fixture.connection));
    REQUIRE(fixture.connection.WaitAvailable(9, WAIT));
    CHECK_THROWS_WITH(fixture.handshake.Advance(fixture.connection), Catch::Matchers::ContainsSubstring("world full"));
    const auto record = fixture.server.GetRecord();
    REQUIRE(record.messages.size() == 1);
    CHECK(record.messages.front().front() == LoginHandshake::SEED_REQUEST);
}

TEST_CASE("LoginHandshake waits for a hop timer and includes its seconds in the error", "[LoginHandshakeCoverage]")
{
    const auto revision = GENERATE(Revision_e::Rev274, Revision_e::Rev289);
    auto fixture = HandshakeFixture{revision, [](ServerSession& session) -> boost::asio::awaitable<void>
    {
        co_await session.Receive();
        co_await session.Send(Bytes(17, 0));
        co_await session.Receive();
        co_await session.Send(Bytes{21});
        co_await session.Receive();
        co_await session.Send(Bytes{42});
        co_await session.ReceiveUntilClosed();
    }};
    fixture.Begin(revision);
    REQUIRE(fixture.connection.WaitAvailable(1, WAIT));
    CHECK_FALSE(fixture.handshake.Advance(fixture.connection));
    CHECK(fixture.handshake.GetWaitingFor() == "hop timer");
    fixture.Acknowledge();
    REQUIRE(fixture.connection.WaitAvailable(1, WAIT));
    CHECK_THROWS_WITH(fixture.handshake.Advance(fixture.connection), Catch::Matchers::ContainsSubstring("42 seconds left"));
}

TEST_CASE("LoginHandshake rejects unsupported success and hop statuses in their revision", "[LoginHandshakeCoverage]")
{
    const auto [revision, status] = GENERATE(std::pair{Revision_e::Rev225, u8{21}}, std::pair{Revision_e::Rev274, u8{18}}, std::pair{Revision_e::Rev289, u8{3}});
    auto fixture = HandshakeFixture{revision, ReplyScript(revision, {status})};
    fixture.Begin(revision);
    REQUIRE(fixture.connection.WaitAvailable(1, WAIT));
    try
    {
        static_cast<void>(fixture.handshake.Advance(fixture.connection));
        FAIL("Expected the server's login rejection");
    }
    catch (const LoginError& error)
    {
        CHECK(error.GetStatus() == status);
    }
}

TEST_CASE("LoginHandshake treats only one as an enabled mouse tracking flag", "[LoginHandshakeCoverage]")
{
    const auto tracking = GENERATE(u8{0}, u8{2}, u8{255});
    auto fixture = HandshakeFixture{Revision_e::Rev289, ReplyScript(Revision_e::Rev289, {2, 0, tracking})};
    fixture.Begin(Revision_e::Rev289);
    REQUIRE(fixture.connection.WaitAvailable(3, WAIT));
    const auto result = fixture.handshake.Advance(fixture.connection);
    REQUIRE(result);
    CHECK_FALSE(result->mouseTracking);
}

TEST_CASE("LoginHandshake offsets inbound cipher seeds with unsigned wraparound", "[LoginHandshakeCoverage]")
{
    const auto seed = std::array<s32, 4>{0, -1, std::numeric_limits<s32>::max(), -50};
    CHECK(LoginHandshake::GetInboundSeed(seed) == std::array<s32, 4>{50, 49, std::numeric_limits<s32>::min() + 49, 0});
}

TEST_CASE("LoginHandshake builds revision-specific login bodies with credentials and cache CRCs", "[LoginHandshakeCoverage]")
{
    const auto revision = GENERATE(Revision_e::Rev225, Revision_e::Rev274, Revision_e::Rev289);
    const auto reconnect = GENERATE(false, true);
    const auto lowMemory = GENERATE(false, true);
    const auto protocol = Protocol{revision};
    const auto account = AccountSettings_s{.username = "bot", .password = "secret"};
    auto login = LoginSettings();
    login.lowMemory = lowMemory;
    auto crcs = std::array<s32, GameCache_s::CRC_COUNT>{};
    std::iota(crcs.begin(), crcs.end(), -4);
    const auto seed = std::array<s32, 4>{1, -1, 0x01020304, std::numeric_limits<s32>::min()};
    const auto bytes = LoginHandshake::BuildLoginRequest(protocol, account, login, crcs, seed, reconnect);
    auto packet = Packet{bytes};
    CHECK(packet.G1() == (reconnect ? 18 : 16));
    CHECK(packet.G1() == bytes.size() - 2);
    if (revision >= Revision_e::Rev274)
    {
        CHECK(packet.G1() == 0xFF);
        CHECK(packet.G2() == static_cast<u16>(revision));
    }
    else
    {
        CHECK(packet.G1() == 225);
    }
    CHECK(packet.G1() == (lowMemory ? 1 : 0));
    for (const auto crc : crcs)
    {
        CHECK(packet.G4() == crc);
    }
    const auto rsaLength = packet.G1();
    CHECK(rsaLength == packet.GetAvailable());
    // Exponent one keeps this test's RSA payload readable on the wire.
    CHECK(packet.G1() == 10);
    for (const auto word : seed)
    {
        CHECK(packet.G4() == word);
    }
    CHECK(packet.G4() == 1337);
    CHECK(packet.GJStr() == account.username);
    CHECK(packet.GJStr() == account.password);
    CHECK(packet.GetAvailable() == 0);
}

TEST_CASE("LoginHandshake rejects bodies beyond the one-byte length boundary", "[LoginHandshakeCoverage]")
{
    const auto revision = GENERATE(Revision_e::Rev225, Revision_e::Rev274, Revision_e::Rev289);
    const auto protocol = Protocol{revision};
    auto account = AccountSettings_s{.username = "bot", .password = "secret"};
    const auto login = LoginSettings();
    const auto crcs = std::array<s32, GameCache_s::CRC_COUNT>{};
    const auto seed = std::array<s32, 4>{1, 2, 3, 4};
    const auto original = LoginHandshake::BuildLoginRequest(protocol, account, login, crcs, seed, false);
    account.password.append(255 - (original.size() - 2), 'x');
    const auto largest = LoginHandshake::BuildLoginRequest(protocol, account, login, crcs, seed, false);
    CHECK(largest.size() == 257);
    CHECK(largest[1] == 255);
    account.password += 'x';
    CHECK_THROWS_WITH(LoginHandshake::BuildLoginRequest(protocol, account, login, crcs, seed, false),
                      Catch::Matchers::ContainsSubstring("Login body is 256 bytes"));
}
