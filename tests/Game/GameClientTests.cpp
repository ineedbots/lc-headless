#include "pch.hpp"
#include "../LogCapture.hpp"
#include "FakeGameServer.hpp"
#include "Fixtures.hpp"
#include "TestWorld.hpp"

#include "Cache/GameCache_s.hpp"
#include "Core/ConfigFile.hpp"
#include "Core/Logger.hpp"
#include "Game/GameActions.hpp"
#include "Game/GameClient.hpp"
#include "Game/Net/LoginError.hpp"
#include "Game/Protocol/ClientProt.hpp"
#include "Game/Protocol/ServerProt.hpp"
#include "Game/State/GameEvent_s.hpp"
#include "Game/State/GameState_s.hpp"
#include "Game/Tile_s.hpp"
#include "Io/Packet.hpp"

#include <catch2/catch_test_macros.hpp>

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

TEST_CASE("GameClient logs in, tracks the world and logs out", "[GameClient]")
{
    auto capture = LogCapture{LogLevel_e::Info};
    auto server = FakeGameServer{TestWorld::Send};
    auto client = GameClient{MakeConfig(server), std::make_shared<const GameCache_s>(), FakeGameServer::MakeAccount(), capture.GetLogger(), FastOptions()};

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
        CHECK(buttons[0].payload == std::vector<u8>{0x09, 0x9A});
    }

    CHECK(server.GetErrors().empty());
}

TEST_CASE("GameClient reconnects when the connection drops", "[GameClient]")
{
    auto capture = LogCapture{LogLevel_e::Info};
    auto server = FakeGameServer{TestWorld::Send};
    auto client = GameClient{MakeConfig(server), std::make_shared<const GameCache_s>(), FakeGameServer::MakeAccount(), capture.GetLogger(), FastOptions()};

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

TEST_CASE("GameClient reports a rejected login", "[GameClient]")
{
    auto capture = LogCapture{LogLevel_e::Info};
    auto server = FakeGameServer{};
    server.SetLoginStatus(3);
    auto client = GameClient{MakeConfig(server), std::make_shared<const GameCache_s>(), FakeGameServer::MakeAccount(), capture.GetLogger(), FastOptions()};

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
    CHECK_THROWS_AS(client.Send(ClientPackets::NoTimeout()), std::runtime_error);
}

TEST_CASE("GameClient ends the session when the server logs it out", "[GameClient]")
{
    auto capture = LogCapture{LogLevel_e::Info};
    auto server = FakeGameServer{TestWorld::Send};
    auto client = GameClient{MakeConfig(server), std::make_shared<const GameCache_s>(), FakeGameServer::MakeAccount(), capture.GetLogger(), FastOptions()};

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
    auto client = GameClient{MakeConfig(server), std::make_shared<const GameCache_s>(), FakeGameServer::MakeAccount(), capture.GetLogger(), options};

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
    auto client = GameClient{MakeConfig(server), std::make_shared<const GameCache_s>(), FakeGameServer::MakeAccount(), capture.GetLogger(), FastOptions()};
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
    auto client = GameClient{MakeConfig(server), std::make_shared<const GameCache_s>(), FakeGameServer::MakeAccount(), capture.GetLogger(), FastOptions()};

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
