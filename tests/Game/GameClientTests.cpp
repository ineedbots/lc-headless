#include "pch.hpp"
#include "../LogCapture.hpp"
#include "FakeGameServer.hpp"
#include "Fixtures.hpp"

#include "Core/ConfigFile.hpp"
#include "Core/Logger.hpp"
#include "Game/GameActions.hpp"
#include "Game/GameClient.hpp"
#include "Game/Net/LoginError.hpp"
#include "Game/Protocol/ClientProt.hpp"
#include "Game/Protocol/ServerProt.hpp"
#include "Game/State/GameState_s.hpp"
#include "Game/Tile_s.hpp"
#include "Io/Packet.hpp"

#include <catch2/catch_test_macros.hpp>

namespace
{
    using Clock = std::chrono::steady_clock;

    constexpr auto WAIT = 5s;
    constexpr auto PUMP_STEP = 20ms;
    constexpr auto NPC_INDEX = u16{100};
    constexpr auto NPC_TYPE = u16{50};
    constexpr auto INVENTORY = u16{3214};

    GameClientOptions_s FastOptions()
    {
        return {
            .reconnectDelay = 50ms,
            .loginTimeout = 5s,
            .keepaliveInterval = 50ms,
        };
    }

    void SendWorld(FakeGameServer& server, bool reconnect)
    {
        server.Send(ServerProt_e::RebuildNormal, Fixtures::Rebuild());
        if (!reconnect)
        {
            server.Send(ServerProt_e::UpdatePid, Fixtures::UpdatePid());
        }

        server.Send(ServerProt_e::PlayerInfo, Fixtures::PlaceLocalPlayer(Fixtures::HOME_LOCAL, Fixtures::HOME_LOCAL, 0, Fixtures::Appearance(FakeGameServer::USERNAME)));
        if (reconnect)
        {
            return;
        }

        server.Send(ServerProt_e::NpcInfo, Fixtures::AddNpc(NPC_INDEX, NPC_TYPE, 2, 0));
        server.Send(ServerProt_e::UpdateZoneFullFollows, Fixtures::Zone(Fixtures::HOME_LOCAL, Fixtures::HOME_LOCAL));
        server.Send(ServerProt_e::ObjAdd, Fixtures::ObjAdd(0x11, 995, 10));

        auto inventory = Packet{};
        inventory.P2(INVENTORY);
        inventory.P2(1);
        inventory.P2(1512);
        inventory.P1(3);
        server.Send(ServerProt_e::UpdateInvFull, Fixtures::ToBytes(inventory));
        server.Send(ServerProt_e::MessageGame, Fixtures::MessageGame("Welcome to RuneScape."));
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
    auto server = FakeGameServer{SendWorld};
    auto client = GameClient{MakeConfig(server), capture.GetLogger(), FastOptions()};

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

    SECTION("an NPC interaction walks toward it, then sends the option, in one flush")
    {
        auto actions = GameActions{client};
        actions.InteractNpc(NPC_INDEX, 1);
        client.Pump();

        REQUIRE(server.WaitForPacket(ClientProt_e::OpNpc1));
        const auto moves = server.GetPackets(ClientProt_e::MoveOpClick);
        REQUIRE(moves.size() == 1);
        CHECK(moves[0].payload == std::vector<u8>{0, 0x0C, 0x82, 0x0C, 0x80});
        CHECK(server.GetPackets(ClientProt_e::OpNpc1)[0].payload == std::vector<u8>{0, 100});
        REQUIRE(client.GetState().walkDestination.has_value());
        CHECK(client.GetState().walkDestination->x == Fixtures::HOME + 2);

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
    auto server = FakeGameServer{SendWorld};
    auto client = GameClient{MakeConfig(server), capture.GetLogger(), FastOptions()};

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
    auto client = GameClient{MakeConfig(server), capture.GetLogger(), FastOptions()};

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
    auto server = FakeGameServer{SendWorld};
    auto client = GameClient{MakeConfig(server), capture.GetLogger(), FastOptions()};

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
