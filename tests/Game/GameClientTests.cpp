#include "pch.hpp"
#include "../Support/Game/FakeGameServer.hpp"
#include "../Support/Game/BitWriter.hpp"
#include "../Support/Game/Fixtures.hpp"
#include "../Support/Game/TestWorld.hpp"
#include "../Support/Io/FakeSocks5Proxy.hpp"
#include "../Support/Io/TestServer.hpp"
#include "../Support/LogCapture.hpp"

#include "Cache/GameCache_s.hpp"
#include "Config/Config_s.hpp"
#include "Config/ProxySettings_s.hpp"
#include "Config/Revision_e.hpp"
#include "Config/Transport_e.hpp"
#include "Console/LogLevel_e.hpp"
#include "Console/Logger.hpp"
#include "Game/GameActions.hpp"
#include "Game/GameClient.hpp"
#include "Game/Error/ProtocolError.hpp"
#include "Game/Error/ConnectionLostError.hpp"
#include "Game/InputTracker.hpp"
#include "Game/Net/Error/LoginError.hpp"
#include "Game/Net/LoginQueue.hpp"
#include "Game/Protocol/ClientProt.hpp"
#include "Game/Protocol/Base37.hpp"
#include "Game/Protocol/WordPack.hpp"
#include "Game/Protocol/ServerProt.hpp"
#include "Game/State/GameEvent_s.hpp"
#include "Game/State/GameState_s.hpp"
#include "Game/Tile_s.hpp"
#include "Io/Packet.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/generators/catch_generators.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>

namespace
{
    using Clock = std::chrono::steady_clock;

    constexpr auto WAIT = 5s;
    constexpr auto PUMP_STEP = 20ms;
    constexpr auto NPC_INDEX = TestWorld::NPC_INDEX;
    constexpr auto INVENTORY = TestWorld::INVENTORY;

    GameClientOptions_s FastOptions()
    {
        return {
            .retryDelay = 50ms,
            .loginTimeout = 5s,
            .keepaliveInterval = 50ms,
        };
    }

    template <typename TCondition>
    bool PumpUntil(GameClient& client, TCondition condition)
    {
        const auto deadline = Clock::now() + WAIT;
        while (Clock::now() < deadline)
        {
            client.Pump(PUMP_STEP);

            if (condition())
            {
                return true;
            }
        }

        return false;
    }

    std::shared_ptr<const Config_s> MakeConfig(const FakeGameServer& server)
    {
        return std::make_shared<const Config_s>(server.MakeConfig());
    }
}

TEST_CASE("GameClient cleans up a login that fails before connecting", "[GameClient][ClientFailureCoverage]")
{
    auto capture = LogCapture{};
    auto server = FakeGameServer{};
    auto config = server.MakeConfig();
    config.server.port = 0;
    auto client = GameClient{std::make_shared<const Config_s>(config), FakeGameServer::MakeCache(), FakeGameServer::MakeAccount(), capture.GetLogger()};
    CHECK_THROWS_AS(client.BeginLogin(), std::invalid_argument);
    CHECK(client.GetStatus() == ClientStatus_e::Disconnected);
    CHECK(client.GetLoginCount() == 0);
    CHECK_NOTHROW(client.Pump());
    CHECK_NOTHROW(client.RequestLogout());
    CHECK(server.GetLoginOpcodes().empty());
}

TEST_CASE("GameClient abandons a login when its transport closes before the seed arrives", "[GameClient][ClientFailureCoverage]")
{
    const auto reset = GENERATE(false, true);
    auto capture = LogCapture{};
    auto server = TestServer{[reset](ServerSession& session) -> boost::asio::awaitable<void>
    {
        static_cast<void>(co_await session.Receive());
        if (reset) session.Reset();
        else session.Drop();
    }, ServerMode_e::Tcp};
    auto config = Config_s{};
    config.server = {.transport = Transport_e::Tcp, .host = "127.0.0.1", .port = server.GetPort()};
    auto options = FastOptions();
    options.connectAttempts = 0;
    auto client = GameClient{std::make_shared<const Config_s>(config), FakeGameServer::MakeCache(), FakeGameServer::MakeAccount(), capture.GetLogger(), options};
    client.BeginLogin();
    const auto advance = [&]
    {
        const auto deadline = Clock::now() + WAIT;
        while (client.GetStatus() == ClientStatus_e::Connecting && Clock::now() < deadline)
        {
            client.Pump();
            std::this_thread::sleep_for(1ms);
        }
    };
    if (reset) CHECK_THROWS_AS(advance(), std::runtime_error);
    else CHECK_THROWS_WITH(advance(), Catch::Matchers::ContainsSubstring("The connection closed during login"));
    CHECK(client.GetStatus() == ClientStatus_e::Disconnected);
    CHECK(client.GetLoginCount() == 0);
    CHECK(server.GetRecord().accepted == 1);
    CHECK_NOTHROW(client.Pump());
}

TEST_CASE("GameClient disconnects and propagates a malformed server packet", "[GameClient][ClientFailureCoverage]")
{
    auto capture = LogCapture{};
    auto server = FakeGameServer{TestWorld::Send};
    auto client = GameClient{MakeConfig(server), FakeGameServer::MakeCache(), FakeGameServer::MakeAccount(), capture.GetLogger(), FastOptions()};
    client.Login();
    REQUIRE(PumpUntil(client, [&] { return client.GetState().IsSettled(); }));
    server.Send(ServerProt_e::PlayerInfo, {});
    CHECK_THROWS_AS(PumpUntil(client, [] { return false; }), ProtocolError);
    CHECK(client.GetStatus() == ClientStatus_e::Disconnected);
    CHECK(client.GetLoginCount() == 1);
    CHECK_NOTHROW(client.Pump());
    CHECK_NOTHROW(client.RequestLogout());
    CHECK_THROWS_AS(client.Send(client.GetPackets().NoTimeout()), std::runtime_error);
}

TEST_CASE("GameClient detects a silent server while the transport remains open", "[GameClient][ClientFailureCoverage]")
{
    auto capture = LogCapture{};
    auto server = FakeGameServer{TestWorld::Send};
    auto options = FastOptions();
    options.autoReconnect = false;
    options.serverSilenceTimeout = 100ms;
    auto client = GameClient{MakeConfig(server), FakeGameServer::MakeCache(), FakeGameServer::MakeAccount(), capture.GetLogger(), options};
    client.Login();
    REQUIRE(PumpUntil(client, [&] { return client.GetState().IsSettled(); }));
    CHECK_THROWS_WITH(PumpUntil(client, [] { return false; }), Catch::Matchers::ContainsSubstring("nothing from the server for 100 ms"));
    CHECK(client.GetStatus() == ClientStatus_e::Disconnected);
    CHECK(client.GetLoginCount() == 1);
    CHECK(server.GetLoginOpcodes() == std::vector<u8>{16});
}

TEST_CASE("GameClient reports a permanent rejection during reconnect", "[GameClient][ClientFailureCoverage]")
{
    auto capture = LogCapture{};
    auto server = FakeGameServer{TestWorld::Send};
    auto client = GameClient{MakeConfig(server), FakeGameServer::MakeCache(), FakeGameServer::MakeAccount(), capture.GetLogger(), FastOptions()};
    client.Login();
    REQUIRE(PumpUntil(client, [&] { return client.GetState().IsSettled(); }));
    server.SetLoginStatus(3);
    server.Close();
    CHECK_THROWS_WITH(PumpUntil(client, [] { return false; }), Catch::Matchers::ContainsSubstring("and reconnecting failed"));
    CHECK(client.GetStatus() == ClientStatus_e::Disconnected);
    CHECK(client.GetLoginCount() == 1);
    CHECK(server.GetLoginOpcodes() == std::vector<u8>{16, 18});
}

TEST_CASE("GameClient treats a lost connection during logout as a completed session", "[GameClient][ClientFailureCoverage]")
{
    const auto transport = GENERATE(Transport_e::Ws, Transport_e::Tcp);
    auto capture = LogCapture{};
    auto server = FakeGameServer{TestWorld::Send, Revision_e::Rev289, transport};
    server.SetIgnoreLogout(true);
    auto client = GameClient{MakeConfig(server), FakeGameServer::MakeCache(), FakeGameServer::MakeAccount(), capture.GetLogger(), FastOptions()};
    client.Login();
    REQUIRE(PumpUntil(client, [&] { return client.GetState().IsSettled(); }));
    client.RequestLogout();
    client.Flush();
    REQUIRE(server.WaitForPacket(ClientProt_e::IfButton));
    server.Close();
    REQUIRE(PumpUntil(client, [&] { return client.GetStatus() == ClientStatus_e::LoggedOut; }));
    CHECK(client.GetLoginCount() == 1);
    CHECK(server.GetLoginOpcodes() == std::vector<u8>{16});
}

TEST_CASE("GameClient logs each kind of incoming chat once with its sender", "[GameClient][ClientFailureCoverage]")
{
    auto capture = LogCapture{};
    auto server = FakeGameServer{TestWorld::Send};
    auto client = GameClient{MakeConfig(server), FakeGameServer::MakeCache(), FakeGameServer::MakeAccount(), capture.GetLogger(), FastOptions()};
    client.Login();
    REQUIRE(PumpUntil(client, [&] { return client.GetState().IsSettled(); }));
    const auto before = client.GetState().messageCount;
    server.Send(ServerProt_e::MessageGame, Fixtures::MessageGame("Mule:tradereq:"));
    server.Send(ServerProt_e::MessageGame, Fixtures::MessageGame("Rival:duelreq:"));
    auto privateMessage = Packet{};
    privateMessage.P8(std::bit_cast<s64>(Base37::Encode("friend")));
    privateMessage.P4(123);
    privateMessage.P1(0);
    privateMessage.PData(WordPack::Pack("hi"));
    server.Send(ServerProt_e::MessagePrivate, Fixtures::ToBytes(privateMessage));
    auto bits = BitWriter{};
    bits.Put(1, 1).Put(2, 0).Put(8, 0).Put(11, 2047);
    auto extended = Packet{};
    extended.P1(0x08 | 0x40);
    extended.PJStr("Ouch!");
    extended.P1(0);
    extended.P1(0);
    extended.P1(0);
    const auto chat = WordPack::Pack("hello");
    extended.P1(static_cast<s32>(chat.size()));
    extended.PData(chat);
    server.Send(ServerProt_e::PlayerInfo, Fixtures::Concat(bits.GetBytes(), Fixtures::ToBytes(extended)));
    REQUIRE(PumpUntil(client, [&] { return client.GetState().messageCount == before + 5; }));
    const auto messages = std::array{
        "[trade request] Mule: wishes to trade with you.",
        "[duel request] Rival: wishes to duel with you.",
        "[private] Friend: Hi",
        "[say] Bot: Ouch!",
        "[public] Bot: Hello ",
    };
    client.Pump();
    for (const auto* message : messages)
    {
        INFO(message);
        CHECK(std::ranges::count_if(capture.GetEntries(), [message](const auto& entry) { return entry.message == message; }) == 1);
    }
    CHECK(client.GetState().messageCount == before + 5);
}

TEST_CASE("GameClient logs in, tracks the world and logs out", "[GameClient]")
{
    const auto transport = GENERATE(Transport_e::Ws, Transport_e::Tcp);
    auto capture = LogCapture{LogLevel_e::Info};
    auto server = FakeGameServer{TestWorld::Send, Revision_e::Rev289, transport};
    auto client = GameClient{MakeConfig(server), FakeGameServer::MakeCache(), FakeGameServer::MakeAccount(), capture.GetLogger(), FastOptions()};

    client.Login();
    REQUIRE(client.IsInGame());
    REQUIRE(PumpUntil(client, [&client]
    {
        return !client.GetState().messages.empty();
    }));

    const auto snapshot = client.TakeSnapshot();
    CHECK(snapshot.pid == Fixtures::PID);
    CHECK(snapshot.members);
    CHECK(snapshot.placed);
    CHECK(snapshot.localPlayer.tile == Tile_s{.x = Fixtures::HOME, .z = Fixtures::HOME, .level = 0});
    REQUIRE(snapshot.localPlayer.appearance.has_value());
    CHECK(snapshot.localPlayer.appearance->name == "Bot");
    REQUIRE(snapshot.npcs.size() == 1);
    CHECK(snapshot.npcs[0].tile == Tile_s{.x = Fixtures::HOME + 2, .z = Fixtures::HOME, .level = 0});
    REQUIRE(snapshot.groundItems.size() == 1);
    CHECK(snapshot.groundItems[0].tile == Tile_s{.x = Fixtures::HOME + 1, .z = Fixtures::HOME + 1, .level = 0});
    REQUIRE(snapshot.FindInventory(INVENTORY) != nullptr);
    CHECK(snapshot.FindInventory(INVENTORY)->slots[0].id == 1511);
    CHECK(snapshot.messages.back().text == "Welcome to RuneScape.");
    CHECK(std::ranges::any_of(snapshot.events, [](const GameEvent_s& event)
    {
        const auto* added = std::get_if<NpcAdded_s>(&event.data);
        return added != nullptr && added->npc.index == NPC_INDEX;
    }));
    CHECK(std::ranges::any_of(snapshot.events, [](const GameEvent_s& event)
    {
        const auto* changed = std::get_if<InventoryChanged_s>(&event.data);
        return changed != nullptr && changed->com == INVENTORY;
    }));

    SECTION("an NPC interaction walks to beside it, then sends the option, in one flush")
    {
        auto actions = GameActions{client};
        actions.InteractNpc(NPC_INDEX, 1);
        client.Pump();

        REQUIRE(server.WaitForPacket(ClientProt_e::OpNpc1));

        const auto moves = server.GetPackets(ClientProt_e::MoveOpClick);
        REQUIRE(moves.size() == 1);
        CHECK(moves[0].payload == std::vector<u8>{0, 0x0C, 0x81, 0x0C, 0x80});
        CHECK(server.GetPackets(ClientProt_e::OpNpc1)[0].payload == std::vector<u8>{0, 100});
        REQUIRE(client.GetState().walkDestination.has_value());
        CHECK(client.GetState().walkDestination->x == Fixtures::HOME + 1);

        CHECK_THROWS_AS(actions.InteractNpc(static_cast<u16>(NPC_INDEX + 1), 1), std::invalid_argument);
    }

    SECTION("an idle session sends keepalives")
    {
        REQUIRE(PumpUntil(client, [&server]
        {
            return !server.GetPackets(ClientProt_e::NoTimeout).empty();
        }));
    }

    SECTION("logout clicks the logout button and waits for the server")
    {
        client.Logout(WAIT);
        CHECK(client.GetStatus() == ClientStatus_e::LoggedOut);

        const auto buttons = server.GetPackets(ClientProt_e::IfButton);
        REQUIRE(buttons.size() == 1);
        REQUIRE(buttons[0].payload.size() == sizeof(u16));
        CHECK(Packet{buttons[0].payload}.G2() == FakeGameServer::LOGOUT_COMPONENT);
    }

    CHECK(server.GetErrors().empty());
}

TEST_CASE("GameClient identifies which 225 map file differs from the server", "[GameClient][CompletionCoverage]")
{
    const auto landDiffers = GENERATE(false, true);
    auto capture = LogCapture{};
    auto server = FakeGameServer{TestWorld::Send, Revision_e::Rev225};
    auto cache = std::make_shared<GameCache_s>();
    cache->revision = Revision_e::Rev225;
    cache->mapCrcs[u16{(50 << 8) | 50}] = {.land = landDiffers ? 99 : TestWorld::SQUARE_225.landCrc, .locs = landDiffers ? TestWorld::SQUARE_225.locCrc : 99};
    auto client = GameClient{MakeConfig(server), cache, FakeGameServer::MakeAccount(), capture.GetLogger(), FastOptions()};
    client.Login();
    REQUIRE(PumpUntil(client, [&] { return !client.GetState().messages.empty(); }));
    const auto expected = std::format("Map square 50_50's {} differ from the server's; walks there may route through changed scenery", landDiffers ? "land" : "locs");
    CHECK(std::ranges::any_of(capture.GetEntries(), [&](const CapturedLog_s& entry) { return entry.level == LogLevel_e::Warning && entry.message == expected; }));
    CHECK(client.IsInGame());
}

TEST_CASE("GameClient logs in to a 225 server and answers each rebuild", "[GameClient]")
{
    const auto transport = GENERATE(Transport_e::Ws, Transport_e::Tcp);
    auto capture = LogCapture{LogLevel_e::Info};
    auto server = FakeGameServer{TestWorld::Send, Revision_e::Rev225, transport};
    auto client = GameClient{MakeConfig(server), FakeGameServer::MakeCache(Revision_e::Rev225), FakeGameServer::MakeAccount(), capture.GetLogger(), FastOptions()};

    client.Login();
    REQUIRE(client.IsInGame());
    REQUIRE(PumpUntil(client, [&client]
    {
        return !client.GetState().messages.empty();
    }));

    const auto& state = client.GetState();
    CHECK(state.staffLevel == 0);
    CHECK(state.pid == Fixtures::PID);
    CHECK_FALSE(state.members);
    CHECK(state.localPlayer.tile == Tile_s{.x = Fixtures::HOME, .z = Fixtures::HOME, .level = 0});
    REQUIRE(state.localPlayer.appearance.has_value());
    CHECK(state.localPlayer.appearance->name == "Bot");
    REQUIRE(state.npcs.size() == 1);
    CHECK(state.npcs[0].tile == Tile_s{.x = Fixtures::HOME + 2, .z = Fixtures::HOME, .level = 0});
    REQUIRE(state.FindInventory(INVENTORY) != nullptr);
    CHECK(state.FindInventory(INVENTORY)->slots[0].id == TestWorld::LOGS);
    REQUIRE(state.buildArea.squares.size() == 1);

    // The square's CRCs are ones the empty cache doesn't have, so it's warned about once.
    REQUIRE(server.WaitForPacket(ClientProt_e::RebuildGetMaps));
    CHECK(server.GetPackets(ClientProt_e::RebuildGetMaps)[0].payload.empty());
    const auto warnings = std::ranges::count_if(capture.GetEntries(), [](const CapturedLog_s& entry)
    {
        return entry.level == LogLevel_e::Warning && entry.message == "Map square 50_50's land and locs differ from the server's; walks there may route through changed scenery";
    });
    CHECK(warnings == 1);

    SECTION("another rebuild is answered too, without warning again")
    {
        const auto square = TestWorld::SQUARE_225;
        server.Send(ServerProt_e::RebuildNormal, Fixtures::Rebuild225(std::span{&square, 1}));
        REQUIRE(PumpUntil(client, [&server]
        {
            return server.GetPackets(ClientProt_e::RebuildGetMaps).size() == 2;
        }));
        CHECK(std::ranges::count_if(capture.GetEntries(), [](const CapturedLog_s& entry)
        {
            return entry.level == LogLevel_e::Warning;
        }) == 1);
    }

    SECTION("an action is sent with 225's opcodes")
    {
        auto actions = GameActions{client};
        actions.InteractNpc(TestWorld::NPC_INDEX, 1);
        client.Pump();
        REQUIRE(server.WaitForPacket(ClientProt_e::OpNpc1));
        CHECK(server.GetPackets(ClientProt_e::OpNpc1)[0].payload == std::vector<u8>{0, 100});
    }

    CHECK(server.GetErrors().empty());
}

TEST_CASE("GameClient logs in to a 274 server and owes no replies", "[GameClient]")
{
    const auto transport = GENERATE(Transport_e::Ws, Transport_e::Tcp);
    auto capture = LogCapture{LogLevel_e::Info};
    auto server = FakeGameServer{TestWorld::Send, Revision_e::Rev274, transport};
    auto client = GameClient{MakeConfig(server), FakeGameServer::MakeCache(Revision_e::Rev274), FakeGameServer::MakeAccount(), capture.GetLogger(), FastOptions()};

    client.Login();
    REQUIRE(client.IsInGame());
    REQUIRE(PumpUntil(client, [&client]
    {
        return !client.GetState().messages.empty();
    }));

    const auto& state = client.GetState();
    CHECK(state.pid == Fixtures::PID);
    CHECK(state.members);
    REQUIRE(state.localPlayer.appearance.has_value());
    CHECK(state.localPlayer.appearance->totalLevel == 32);
    REQUIRE(state.npcs.size() == 1);
    REQUIRE(state.FindInventory(INVENTORY) != nullptr);
    CHECK(state.FindInventory(INVENTORY)->slots[0].id == TestWorld::LOGS);
    CHECK(state.buildArea.loaded);
    CHECK(state.buildArea.squares.empty());

    auto actions = GameActions{client};
    actions.InteractNpc(TestWorld::NPC_INDEX, 1);
    client.Pump();
    REQUIRE(server.WaitForPacket(ClientProt_e::OpNpc1));
    CHECK(server.GetPackets(ClientProt_e::OpNpc1)[0].payload == std::vector<u8>{0, 100});
    CHECK(server.GetPackets(ClientProt_e::RebuildGetMaps).empty());
    CHECK(server.GetPackets(ClientProt_e::EventTracking).empty());
    CHECK(server.GetErrors().empty());
}

TEST_CASE("GameClient reports a 225 server's input tracking windows", "[GameClient]")
{
    auto capture = LogCapture{LogLevel_e::Info};
    auto server = FakeGameServer{TestWorld::Send, Revision_e::Rev225};
    auto client = GameClient{MakeConfig(server), FakeGameServer::MakeCache(Revision_e::Rev225), FakeGameServer::MakeAccount(), capture.GetLogger(), FastOptions()};

    client.Login();
    REQUIRE(PumpUntil(client, [&client]
    {
        return !client.GetState().messages.empty();
    }));

    const auto reportCount = [&server]
    {
        return server.GetPackets(ClientProt_e::EventTracking).size();
    };

    SECTION("a window with no actions still reports a move")
    {
        server.Send(ServerProt_e::EnableTracking);
        server.Send(ServerProt_e::FinishTracking);
        REQUIRE(PumpUntil(client, [&reportCount]
        {
            return reportCount() == 1;
        }));

        const auto report = server.GetPackets(ClientProt_e::EventTracking)[0].payload;
        REQUIRE(report.size() == 5);
        CHECK(report[0] == InputTracker::ABSOLUTE_MOVE);
    }

    SECTION("each action records a click, and keepalives record nothing")
    {
        server.Send(ServerProt_e::EnableTracking);
        REQUIRE(PumpUntil(client, [&server]
        {
            return server.GetPackets(ClientProt_e::NoTimeout).size() >= 2;
        }));

        client.Send(client.GetPackets().CloseModal());
        client.Send(client.GetPackets().CloseModal());
        client.Flush();
        server.Send(ServerProt_e::FinishTracking);
        REQUIRE(PumpUntil(client, [&reportCount]
        {
            return reportCount() == 1;
        }));

        const auto report = server.GetPackets(ClientProt_e::EventTracking)[0].payload;
        REQUIRE(report.size() == 24);
        CHECK(report[0] == InputTracker::ABSOLUTE_MOVE);
        CHECK(report[5] == InputTracker::LEFT_PRESS);
        CHECK(report[10] == InputTracker::LEFT_RELEASE);
        CHECK(report[12] == InputTracker::ABSOLUTE_MOVE);
    }

    SECTION("a report that fills up is sent before the window finishes")
    {
        server.Send(ServerProt_e::EnableTracking);
        REQUIRE(PumpUntil(client, [&server]
        {
            return !server.GetPackets(ClientProt_e::NoTimeout).empty();
        }));

        for (auto click = 0; click < 45; ++click)
        {
            client.Send(client.GetPackets().CloseModal());
        }

        client.Flush();
        REQUIRE(server.WaitForPacket(ClientProt_e::EventTracking));
        CHECK(server.GetPackets(ClientProt_e::EventTracking)[0].payload.size() < InputTracker::MAX_REPORT_SIZE);

        server.Send(ServerProt_e::FinishTracking);
        REQUIRE(PumpUntil(client, [&reportCount]
        {
            return reportCount() == 2;
        }));

        const auto reports = server.GetPackets(ClientProt_e::EventTracking);
        CHECK(reports[0].payload.size() + reports[1].payload.size() == 45 * 12);
    }

    SECTION("a report isn't sent outside a window")
    {
        client.Send(client.GetPackets().CloseModal());
        server.Send(ServerProt_e::FinishTracking);
        REQUIRE(PumpUntil(client, [&server]
        {
            return server.GetPackets(ClientProt_e::NoTimeout).size() >= 2;
        }));

        CHECK(reportCount() == 0);
    }

    CHECK(server.GetErrors().empty());
}

TEST_CASE("GameClient logs a 225 staff account in with status 18", "[GameClient]")
{
    auto capture = LogCapture{LogLevel_e::Info};
    auto server = FakeGameServer{TestWorld::Send, Revision_e::Rev225};
    server.SetLoginStatus(18);

    auto client = GameClient{MakeConfig(server), FakeGameServer::MakeCache(Revision_e::Rev225), FakeGameServer::MakeAccount(), capture.GetLogger(), FastOptions()};
    client.Login();
    REQUIRE(client.IsInGame());
    CHECK(client.GetState().staffLevel == 1);
    CHECK(server.GetErrors().empty());
}

TEST_CASE("GameClient reconnects when the connection drops", "[GameClient]")
{
    const auto transport = GENERATE(Transport_e::Ws, Transport_e::Tcp);
    auto capture = LogCapture{LogLevel_e::Info};
    auto server = FakeGameServer{TestWorld::Send, Revision_e::Rev289, transport};
    auto client = GameClient{MakeConfig(server), FakeGameServer::MakeCache(), FakeGameServer::MakeAccount(), capture.GetLogger(), FastOptions()};

    client.Login();
    REQUIRE(PumpUntil(client, [&client]
    {
        return !client.GetState().npcs.empty();
    }));

    server.SetLoginStatus(15);
    server.Close();
    REQUIRE(PumpUntil(client, [&server]
    {
        return server.GetLoginOpcodes().size() == 2;
    }));

    REQUIRE(PumpUntil(client, [&client]
    {
        return client.GetState().tick >= 2;
    }));

    CHECK(client.IsInGame());
    CHECK(server.GetLoginOpcodes() == std::vector<u8>{16, 18});
    CHECK(client.GetState().pid == Fixtures::PID);
    CHECK(client.GetState().npcs.size() == 1);
    CHECK(server.GetErrors().empty());
}

TEST_CASE("GameClient with zero connect attempts tries the initial login only once", "[GameClient]")
{
    auto capture = LogCapture{LogLevel_e::Info};
    auto server = FakeGameServer{};
    server.SetLoginStatus(5);
    auto options = FastOptions();
    options.connectAttempts = 0;
    auto client = GameClient{MakeConfig(server), FakeGameServer::MakeCache(), FakeGameServer::MakeAccount(), capture.GetLogger(), options};

    CHECK_THROWS_AS(client.Login(), LoginError);
    CHECK(client.GetStatus() == ClientStatus_e::Disconnected);
    CHECK(server.GetLoginOpcodes() == std::vector<u8>{16});
}

TEST_CASE("GameClient keeps trying past the unlimited attempt setting", "[GameClient]")
{
    const auto reconnect = GENERATE(false, true);
    auto capture = LogCapture{LogLevel_e::Info};
    auto server = FakeGameServer{TestWorld::Send, Revision_e::Rev289, Transport_e::Tcp};
    auto options = FastOptions();
    options.connectAttempts = ScriptingSettings_s::MAX_CONNECT_ATTEMPTS;
    options.retryDelay = 0ms;
    options.maxRetryDelay = 0ms;
    auto client = GameClient{MakeConfig(server), FakeGameServer::MakeCache(), FakeGameServer::MakeAccount(), capture.GetLogger(), options};

    if (reconnect)
    {
        client.Login();
        server.SetLoginStatus(5);
        server.Close();
    }
    else
    {
        server.SetLoginStatus(5);
        client.BeginLogin();
    }

    const auto deadline = Clock::now() + 30s;
    while (Clock::now() < deadline && server.GetLoginOpcodes().size() <= ScriptingSettings_s::MAX_CONNECT_ATTEMPTS + 1)
    {
        client.Pump(1ms);
    }

    REQUIRE(server.GetLoginOpcodes().size() > ScriptingSettings_s::MAX_CONNECT_ATTEMPTS + 1);
    CHECK(client.GetStatus() == ClientStatus_e::Connecting);

    server.SetLoginStatus(2);
    REQUIRE(PumpUntil(client, [&client]
    {
        return client.IsInGame();
    }));
    CHECK(client.GetLoginCount() == (reconnect ? u32{2} : u32{1}));
    CHECK(server.GetErrors().empty());
}

TEST_CASE("GameClient takes turns reconnecting with the clients that share its login queue", "[GameClient]")
{
    constexpr auto INTERVAL = 300ms;

    auto capture = LogCapture{LogLevel_e::Info};
    auto firstServer = FakeGameServer{TestWorld::Send};
    auto secondServer = FakeGameServer{TestWorld::Send};
    auto options = FastOptions();
    options.loginQueue = std::make_shared<LoginQueue>(INTERVAL);

    auto first = GameClient{MakeConfig(firstServer), FakeGameServer::MakeCache(), FakeGameServer::MakeAccount(), capture.GetLogger(), options};
    auto second = GameClient{MakeConfig(secondServer), FakeGameServer::MakeCache(), FakeGameServer::MakeAccount(), capture.GetLogger(), options};

    // Pumps both clients until each server has seen count logins, and returns when each saw its last.
    const auto pumpUntilLogins = [&](std::size_t count)
    {
        auto firstAt = std::optional<Clock::time_point>{};
        auto secondAt = std::optional<Clock::time_point>{};
        const auto deadline = Clock::now() + WAIT;
        while (Clock::now() < deadline && !(firstAt && secondAt))
        {
            first.Pump(5ms);
            second.Pump(5ms);

            if (!firstAt && firstServer.GetLoginOpcodes().size() == count)
            {
                firstAt = Clock::now();
            }

            if (!secondAt && secondServer.GetLoginOpcodes().size() == count)
            {
                secondAt = Clock::now();
            }
        }

        REQUIRE(firstAt.has_value());
        REQUIRE(secondAt.has_value());
        return std::pair{*firstAt, *secondAt};
    };

    first.BeginLogin();
    second.BeginLogin();
    const auto [firstLogin, secondLogin] = pumpUntilLogins(1);
    CHECK(secondLogin - firstLogin >= INTERVAL - 50ms);

    REQUIRE(PumpUntil(second, [&]
    {
        first.Pump();
        return first.GetState().placed && second.GetState().placed;
    }));

    firstServer.SetLoginStatus(15);
    secondServer.SetLoginStatus(15);
    firstServer.Close();
    secondServer.Close();
    const auto [firstReconnect, secondReconnect] = pumpUntilLogins(2);
    const auto gap = firstReconnect > secondReconnect ? firstReconnect - secondReconnect : secondReconnect - firstReconnect;
    CHECK(gap >= INTERVAL - 50ms);

    CHECK(firstServer.GetLoginOpcodes() == std::vector<u8>{16, 18});
    CHECK(secondServer.GetLoginOpcodes() == std::vector<u8>{16, 18});
}

TEST_CASE("GameClient logs in and reconnects through a SOCKS5 proxy", "[GameClient][Socks5]")
{
    const auto transport = GENERATE(Transport_e::Ws, Transport_e::Tcp);
    auto capture = LogCapture{LogLevel_e::Info};
    auto server = FakeGameServer{TestWorld::Send, Revision_e::Rev289, transport};
    auto proxy = FakeSocks5Proxy{};
    proxy.SetCredentials("proxyuser", "proxypass");

    auto config = server.MakeConfig();
    config.proxy = ProxySettings_s{.host = "127.0.0.1", .port = proxy.GetPort(), .username = "proxyuser", .password = "proxypass"};
    auto client = GameClient{std::make_shared<const Config_s>(config), FakeGameServer::MakeCache(), FakeGameServer::MakeAccount(), capture.GetLogger(), FastOptions()};

    client.Login();
    REQUIRE(PumpUntil(client, [&client]
    {
        return client.GetState().placed;
    }));

    const auto record = proxy.GetRecord();
    CHECK(record.accepted == 1);
    REQUIRE(record.requests.size() == 1);
    CHECK(record.requests[0].port == config.server.port);

    // A reconnect builds its options again, so it goes through the proxy too.
    server.SetLoginStatus(15);
    server.Close();
    REQUIRE(PumpUntil(client, [&server]
    {
        return server.GetLoginOpcodes().size() == 2;
    }));

    CHECK(proxy.GetRecord().accepted == 2);
    CHECK(server.GetErrors().empty());
}

TEST_CASE("GameClient reports a rejected login", "[GameClient]")
{
    auto capture = LogCapture{LogLevel_e::Info};
    auto server = FakeGameServer{};
    server.SetLoginStatus(3);

    auto options = FastOptions();
    options.connectAttempts = GENERATE(0u, 10u, static_cast<u32>(ScriptingSettings_s::MAX_CONNECT_ATTEMPTS));
    auto client = GameClient{MakeConfig(server), FakeGameServer::MakeCache(), FakeGameServer::MakeAccount(), capture.GetLogger(), options};

    try
    {
        client.Login();
        FAIL("Login should have thrown");
    }
    catch (const LoginError& e)
    {
        CHECK(e.GetStatus() == 3);
    }

    CHECK(client.GetStatus() == ClientStatus_e::Disconnected);
    CHECK_THROWS_AS(client.Send(client.GetPackets().NoTimeout()), std::runtime_error);
    CHECK(server.GetLoginOpcodes() == std::vector<u8>{16});
}

TEST_CASE("GameClient ends the session when the server logs it out", "[GameClient]")
{
    const auto transport = GENERATE(Transport_e::Ws, Transport_e::Tcp);
    auto capture = LogCapture{LogLevel_e::Info};
    auto server = FakeGameServer{TestWorld::Send, Revision_e::Rev289, transport};
    auto client = GameClient{MakeConfig(server), FakeGameServer::MakeCache(), FakeGameServer::MakeAccount(), capture.GetLogger(), FastOptions()};

    client.Login();
    REQUIRE(PumpUntil(client, [&client]
    {
        return client.GetState().placed;
    }));

    server.Send(ServerProt_e::Logout);
    REQUIRE(PumpUntil(client, [&client]
    {
        return client.GetStatus() == ClientStatus_e::LoggedOut;
    }));

    CHECK_FALSE(client.IsInGame());
}

TEST_CASE("GameClient reconnects without making Pump wait", "[GameClient]")
{
    auto capture = LogCapture{LogLevel_e::Info};
    auto server = FakeGameServer{TestWorld::Send};
    auto options = FastOptions();
    options.loginTimeout = 300ms;
    options.retryDelay = 100ms;

    auto client = GameClient{MakeConfig(server), FakeGameServer::MakeCache(), FakeGameServer::MakeAccount(), capture.GetLogger(), options};

    client.Login();
    REQUIRE(PumpUntil(client, [&client]
    {
        return client.GetState().placed;
    }));

    // The first reconnect attempt meets a stalled server and times out; the next one gets through.
    server.SetLoginStatus(15);
    server.SetStalled(true);
    server.Close();

    auto longestPump = 0ms;
    const auto deadline = Clock::now() + WAIT;
    auto unstalled = false;
    while (Clock::now() < deadline && client.GetLoginCount() < 2)
    {
        const auto start = Clock::now();
        client.Pump();
        longestPump = std::max(longestPump, std::chrono::duration_cast<std::chrono::milliseconds>(Clock::now() - start));

        if (!unstalled && client.GetStatus() == ClientStatus_e::Connecting && capture.GetEntries().back().message.starts_with("Trying again"))
        {
            server.SetStalled(false);
            unstalled = true;
        }

        std::this_thread::sleep_for(5ms);
    }

    REQUIRE(client.GetLoginCount() == 2);
    CHECK(client.IsInGame());
    CHECK(unstalled);
    CHECK(longestPump < 100ms);
    CHECK(server.GetLoginOpcodes() == std::vector<u8>{16, 18});
}

TEST_CASE("GameClient clicks logout again until the server agrees", "[GameClient]")
{
    auto capture = LogCapture{LogLevel_e::Info};
    auto server = FakeGameServer{TestWorld::Send};
    auto client = GameClient{MakeConfig(server), FakeGameServer::MakeCache(), FakeGameServer::MakeAccount(), capture.GetLogger(), FastOptions()};
    client.Login();
    REQUIRE(PumpUntil(client, [&client]
    {
        return client.GetState().placed;
    }));

    server.SetIgnoreLogout(true);

    SECTION("a later click is answered")
    {
        client.RequestLogout(WAIT);
        CHECK(client.GetStatus() == ClientStatus_e::LoggingOut);
        REQUIRE(PumpUntil(client, [&server]
        {
            return server.GetPackets(ClientProt_e::IfButton).size() >= 2;
        }));

        server.SetIgnoreLogout(false);
        REQUIRE(PumpUntil(client, [&client]
        {
            return client.GetStatus() == ClientStatus_e::LoggedOut;
        }));

        CHECK(server.GetPackets(ClientProt_e::IfButton).size() == 3);
    }

    SECTION("the connection closes when the deadline passes")
    {
        client.Logout(300ms);
        CHECK(client.GetStatus() == ClientStatus_e::Disconnected);
        CHECK(std::ranges::any_of(capture.GetEntries(), [](const CapturedLog_s& entry)
        {
            return entry.level == LogLevel_e::Warning && entry.message.find("didn't confirm the logout") != std::string::npos;
        }));
    }
}

TEST_CASE("GameClient retries a login the server can't take yet", "[GameClient]")
{
    auto capture = LogCapture{LogLevel_e::Info};
    auto server = FakeGameServer{TestWorld::Send};
    server.SetLoginStatus(5);

    auto client = GameClient{MakeConfig(server), FakeGameServer::MakeCache(), FakeGameServer::MakeAccount(), capture.GetLogger(), FastOptions()};

    client.BeginLogin();
    REQUIRE(PumpUntil(client, [&capture]
    {
        return std::ranges::any_of(capture.GetEntries(), [](const CapturedLog_s& entry)
        {
            return entry.message.starts_with("Login attempt 1 of") && entry.message.find("already logged in") != std::string::npos;
        });
    }));

    CHECK(client.GetStatus() == ClientStatus_e::Connecting);
    server.SetLoginStatus(2);
    REQUIRE(PumpUntil(client, [&client]
    {
        return client.IsInGame();
    }));

    CHECK(server.GetLoginOpcodes() == std::vector<u8>{16, 16});
    CHECK(client.GetLoginCount() == 1);
}

TEST_CASE("GameClient reconnects when a send meets a dropped connection", "[GameClient]")
{
    const auto transport = GENERATE(Transport_e::Ws, Transport_e::Tcp);
    auto capture = LogCapture{LogLevel_e::Info};
    auto server = FakeGameServer{TestWorld::Send, Revision_e::Rev289, transport};
    auto client = GameClient{MakeConfig(server), FakeGameServer::MakeCache(), FakeGameServer::MakeAccount(), capture.GetLogger(), FastOptions()};
    client.Login();
    REQUIRE(PumpUntil(client, [&client]
    {
        return client.GetState().placed;
    }));

    // Sending without pumping finds the closed connection before Pump can.
    server.SetLoginStatus(15);
    server.Close();

    const auto deadline = Clock::now() + WAIT;
    while (Clock::now() < deadline && client.IsInGame())
    {
        client.Send(client.GetPackets().NoTimeout());
        REQUIRE_NOTHROW(client.Flush());
        std::this_thread::sleep_for(10ms);
    }

    CHECK(client.GetStatus() == ClientStatus_e::Connecting);
    REQUIRE(PumpUntil(client, [&client]
    {
        return client.GetLoginCount() == 2;
    }));

    CHECK(client.IsInGame());
    CHECK(server.GetLoginOpcodes() == std::vector<u8>{16, 18});
}
