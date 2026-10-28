#include "pch.hpp"
#include "../Support/Cache/TestCache.hpp"
#include "../Support/Game/FakeGameServer.hpp"
#include "../Support/Game/Fixtures.hpp"
#include "../Support/Game/TestWorld.hpp"
#include "../Support/LogCapture.hpp"

#include "Cache/GameCache_s.hpp"
#include "Config/Config_s.hpp"
#include "Game/GameActions.hpp"
#include "Game/GameClient.hpp"
#include "Game/Map/WorldMap.hpp"
#include "Game/Protocol/ClientProt.hpp"
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
    constexpr auto DOOR = u16{1530};
    constexpr auto WALL = u8{0};
    constexpr auto EAST = u8{2};

    Tile_s Offset(s32 dx, s32 dz)
    {
        return {.x = Fixtures::HOME + dx, .z = Fixtures::HOME + dz, .level = 0};
    }

    // The test world's NPC, two tiles east, is penned in; a door faces west three tiles west; and a
    // short wall stands three tiles north.
    std::shared_ptr<const GameCache_s> MakeCache()
    {
        auto cache = GameCache_s{};
        TestCache::AddLoc(cache, DOOR, "Door", {"Open"});

        auto blocked = std::vector<Tile_s>{};
        for (auto dx = 1; dx <= 3; ++dx)
        {
            for (auto dz = -1; dz <= 1; ++dz)
            {
                if (dx != 2 || dz != 0)
                {
                    blocked.push_back(Offset(dx, dz));
                }
            }
        }

        for (auto dx = -1; dx <= 1; ++dx)
        {
            blocked.push_back(Offset(dx, 3));
        }

        const auto locs = std::to_array<TestLoc_s>({{.id = DOOR, .tile = Offset(-3, 0), .shape = WALL, .angle = EAST}});
        TestCache::SetMap(cache, locs, blocked);
        return std::make_shared<const GameCache_s>(std::move(cache));
    }

    // The waypoints in a move packet's payload: run, the first as an absolute tile, then offsets from it.
    std::vector<Tile_s> ReadWaypoints(std::span<const u8> payload)
    {
        auto packet = Packet{payload};
        static_cast<void>(packet.G1());

        const auto start = Tile_s{.x = packet.G2(), .z = packet.G2()};
        auto waypoints = std::vector<Tile_s>{start};
        while (packet.GetAvailable() >= 2)
        {
            const auto dx = packet.G1B();
            const auto dz = packet.G1B();
            waypoints.push_back({.x = start.x + dx, .z = start.z + dz});
        }

        return waypoints;
    }

    class ActionsFixture
    {
    public:
        ActionsFixture()
            : server{TestWorld::Send}
            , client{std::make_shared<const Config_s>(server.MakeConfig()), MakeCache(), FakeGameServer::MakeAccount(), capture.GetLogger(), GameClientOptions_s{.keepaliveInterval = 10s}}
            , actions{client}
        {
            client.Login();

            const auto deadline = Clock::now() + WAIT;
            while (Clock::now() < deadline && client.GetState().messages.empty())
            {
                client.Pump(PUMP_STEP);
            }

            REQUIRE(client.GetMap().IsLoaded());
        }

        [[nodiscard]] std::vector<Tile_s> GetMove(ClientProt_e prot)
        {
            REQUIRE(server.WaitForPacket(prot));
            return ReadWaypoints(server.GetPackets(prot).front().payload);
        }

        LogCapture capture;
        FakeGameServer server;
        GameClient client;
        GameActions actions;
    };
}

TEST_CASE("GameActions walks routes around obstacles", "[GameActions]")
{
    auto fixture = ActionsFixture{};
    CHECK(fixture.actions.WalkTo(Offset(0, 5)));
    fixture.client.Pump();

    const auto waypoints = fixture.GetMove(ClientProt_e::MoveGameClick);
    CHECK(waypoints.size() > 1);
    CHECK(waypoints.back() == Tile_s{.x = Fixtures::HOME, .z = Fixtures::HOME + 5});
    CHECK(fixture.client.GetState().walkDestination == Offset(0, 5));
}

TEST_CASE("GameActions doesn't walk to a tile it can't reach, but walks straight beyond the area", "[GameActions]")
{
    auto fixture = ActionsFixture{};
    CHECK_FALSE(fixture.actions.WalkTo(Offset(2, 0)));
    CHECK(fixture.actions.WalkTo(Offset(200, 0)));
    fixture.client.Pump();

    // Both went out in one flush, so the second walk's arrival shows the first sent nothing.
    REQUIRE(fixture.server.WaitForPacket(ClientProt_e::MoveGameClick));

    const auto moves = fixture.server.GetPackets(ClientProt_e::MoveGameClick);
    REQUIRE(moves.size() == 1);
    CHECK(ReadWaypoints(moves[0].payload) == std::vector<Tile_s>{{.x = Fixtures::HOME + 200, .z = Fixtures::HOME}});
}

TEST_CASE("GameActions routes to a loc, then uses it", "[GameActions]")
{
    auto fixture = ActionsFixture{};
    fixture.actions.InteractLoc(Offset(-3, 0), DOOR, 1);
    fixture.client.Pump();

    REQUIRE(fixture.server.WaitForPacket(ClientProt_e::OpLoc1));
    CHECK(fixture.GetMove(ClientProt_e::MoveOpClick) == std::vector<Tile_s>{{.x = Fixtures::HOME - 2, .z = Fixtures::HOME}});
}

TEST_CASE("GameActions sends the op alone when there's no route", "[GameActions]")
{
    auto fixture = ActionsFixture{};
    fixture.actions.InteractNpc(TestWorld::NPC_INDEX, 2);
    fixture.client.Pump();

    REQUIRE(fixture.server.WaitForPacket(ClientProt_e::OpNpc2));
    CHECK(fixture.server.GetPackets(ClientProt_e::MoveOpClick).empty());
}

TEST_CASE("GameActions follows explicit loc waypoints before sending the interaction", "[GameActionsCoverage]")
{
    auto fixture = ActionsFixture{};
    const auto waypoints = std::to_array<Tile_s>({Offset(0, -2), Offset(-4, -2), Offset(-4, 0)});
    fixture.actions.InteractLocVia(waypoints, Offset(-3, 0), DOOR, 1);
    fixture.client.Pump();

    REQUIRE(fixture.server.WaitForPacket(ClientProt_e::OpLoc1));
    CHECK(fixture.GetMove(ClientProt_e::MoveOpClick) == std::vector<Tile_s>{waypoints.begin(), waypoints.end()});
    CHECK(fixture.client.GetState().walkDestination == waypoints.back());
    const auto packets = fixture.server.GetPackets(ClientProt_e::OpLoc1);
    REQUIRE(packets.size() == 1);
    auto packet = Packet{packets.front().payload};
    CHECK(packet.G2() == Fixtures::HOME - 3);
    CHECK(packet.G2() == Fixtures::HOME);
    CHECK(packet.G2() == DOOR);
    CHECK(packet.GetAvailable() == 0);
}

TEST_CASE("GameActions follows explicit ground item waypoints before sending the interaction", "[GameActionsCoverage]")
{
    auto fixture = ActionsFixture{};
    const auto waypoints = std::to_array<Tile_s>({Offset(0, -2), Offset(4, -2)});
    const auto target = Offset(4, -1);
    fixture.actions.InteractGroundItemVia(waypoints, target, TestWorld::COINS, 3);
    fixture.client.Pump();

    REQUIRE(fixture.server.WaitForPacket(ClientProt_e::OpObj3));
    CHECK(fixture.GetMove(ClientProt_e::MoveOpClick) == std::vector<Tile_s>{waypoints.begin(), waypoints.end()});
    CHECK(fixture.client.GetState().walkDestination == waypoints.back());
    const auto packets = fixture.server.GetPackets(ClientProt_e::OpObj3);
    REQUIRE(packets.size() == 1);
    auto packet = Packet{packets.front().payload};
    CHECK(packet.G2() == target.x);
    CHECK(packet.G2() == target.z);
    CHECK(packet.G2() == TestWorld::COINS);
    CHECK(packet.GetAvailable() == 0);
}

TEST_CASE("GameActions rejects invalid explicit interactions before walking or sending an op", "[GameActionsCoverage]")
{
    const auto groundItem = GENERATE(false, true);
    auto fixture = ActionsFixture{};
    const auto before = fixture.client.GetState().walkDestination;
    const auto waypoints = std::to_array<Tile_s>({Offset(0, -2)});
    SECTION("an invalid operation cannot start an approach")
    {
        if (groundItem)
        {
            CHECK_THROWS_AS(fixture.actions.InteractGroundItemVia(waypoints, Offset(1, 1), TestWorld::COINS, 0), std::invalid_argument);
        }
        else
        {
            CHECK_THROWS_AS(fixture.actions.InteractLocVia(waypoints, Offset(-3, 0), DOOR, 0), std::invalid_argument);
        }
    }
    SECTION("an empty path cannot send an interaction")
    {
        if (groundItem)
        {
            CHECK_THROWS_AS(fixture.actions.InteractGroundItemVia({}, Offset(1, 1), TestWorld::COINS, 1), std::invalid_argument);
        }
        else
        {
            CHECK_THROWS_AS(fixture.actions.InteractLocVia({}, Offset(-3, 0), DOOR, 1), std::invalid_argument);
        }
    }
    CHECK(fixture.client.GetState().walkDestination == before);
    // A following button packet is a barrier: all preceding actions have reached the server.
    fixture.actions.ClickButton(700);
    fixture.client.Pump();
    REQUIRE(fixture.server.WaitForPacket(ClientProt_e::IfButton));
    CHECK(fixture.server.GetPackets(ClientProt_e::MoveOpClick).empty());
    CHECK(fixture.server.GetPackets(ClientProt_e::OpLoc1).empty());
    CHECK(fixture.server.GetPackets(ClientProt_e::OpObj1).empty());
}

TEST_CASE("GameActions rejects interactions with players outside the view", "[GameActionsCoverage]")
{
    auto fixture = ActionsFixture{};
    const auto before = fixture.client.GetState().walkDestination;
    const auto absent = u16{1000};
    const auto item = ItemRef_s{.obj = TestWorld::LOGS, .slot = 0, .com = TestWorld::INVENTORY};
    const auto reason = Catch::Matchers::ContainsSubstring("Player 1000 isn't in view");
    CHECK_THROWS_WITH(fixture.actions.InteractPlayer(absent, 1), reason);
    CHECK_THROWS_WITH(fixture.actions.UseItemOnPlayer(item, absent), reason);
    CHECK_THROWS_WITH(fixture.actions.CastOnPlayer(1152, absent), reason);
    CHECK(fixture.client.GetState().walkDestination == before);
    fixture.actions.ClickButton(700);
    fixture.client.Pump();
    REQUIRE(fixture.server.WaitForPacket(ClientProt_e::IfButton));
    CHECK(fixture.server.GetPackets(ClientProt_e::MoveOpClick).empty());
    CHECK(fixture.server.GetPackets(ClientProt_e::OpPlayer1).empty());
    CHECK(fixture.server.GetPackets(ClientProt_e::OpPlayerU).empty());
    CHECK(fixture.server.GetPackets(ClientProt_e::OpPlayerT).empty());
}

TEST_CASE("GameActions ignores components without an immediate button action", "[GameActionsCoverage]")
{
    const auto type = GENERATE(ButtonType_e::None, ButtonType_e::Target);
    auto fixture = ActionsFixture{};
    fixture.actions.ClickComponent(701, type);
    fixture.actions.ClickButton(700);
    fixture.client.Pump();
    REQUIRE(fixture.server.WaitForPacket(ClientProt_e::IfButton));
    const auto packets = fixture.server.GetPackets(ClientProt_e::IfButton);
    REQUIRE(packets.size() == 1);
    auto packet = Packet{packets.front().payload};
    CHECK(packet.G2() == 700);
    CHECK(fixture.server.GetPackets(ClientProt_e::ResumePauseButton).empty());
    CHECK(fixture.server.GetPackets(ClientProt_e::CloseModal).empty());
}

TEST_CASE("GameActions closes interfaces without adding a movement request", "[GameActionsCoverage]")
{
    auto fixture = ActionsFixture{};
    const auto before = fixture.client.GetState().walkDestination;
    fixture.actions.CloseInterfaces();
    fixture.client.Pump();
    REQUIRE(fixture.server.WaitForPacket(ClientProt_e::CloseModal));
    const auto packets = fixture.server.GetPackets(ClientProt_e::CloseModal);
    REQUIRE(packets.size() == 1);
    CHECK(packets.front().payload.empty());
    CHECK(fixture.client.GetState().walkDestination == before);
}

TEST_CASE("GameActions finds inventory items and distinguishes absent items from absent inventories", "[GameActionsCoverage]")
{
    auto fixture = ActionsFixture{};
    CHECK_FALSE(fixture.actions.FindItem(999, TestWorld::LOGS));
    CHECK_FALSE(fixture.actions.FindItem(TestWorld::INVENTORY, TestWorld::COINS));
    const auto logs = fixture.actions.FindItem(TestWorld::INVENTORY, TestWorld::LOGS);
    REQUIRE(logs);
    CHECK(logs->obj == TestWorld::LOGS);
    CHECK(logs->com == TestWorld::INVENTORY);
    CHECK(logs->slot == 0);
}

TEST_CASE("GameActions inventory lookup selects the first matching slot and follows server updates", "[GameActionsCoverage]")
{
    auto fixture = ActionsFixture{};
    const auto items = std::to_array<std::pair<u16, s32>>({{0, 0}, {TestWorld::COINS, 10}, {TestWorld::COINS, 20}});
    fixture.server.Send(ServerProt_e::UpdateInvFull, Fixtures::UpdateInvFull(TestWorld::INVENTORY, items));
    const auto deadline = Clock::now() + WAIT;
    while (Clock::now() < deadline && !fixture.actions.FindItem(TestWorld::INVENTORY, TestWorld::COINS))
    {
        fixture.client.Pump(PUMP_STEP);
    }
    const auto coins = fixture.actions.FindItem(TestWorld::INVENTORY, TestWorld::COINS);
    REQUIRE(coins);
    CHECK(coins->obj == TestWorld::COINS);
    CHECK(coins->com == TestWorld::INVENTORY);
    CHECK(coins->slot == 1);
    CHECK_FALSE(fixture.actions.FindItem(TestWorld::INVENTORY, TestWorld::LOGS));

    fixture.server.Send(ServerProt_e::UpdateInvFull, Fixtures::UpdateInvFull(TestWorld::INVENTORY, {}));
    const auto clearDeadline = Clock::now() + WAIT;
    while (Clock::now() < clearDeadline && fixture.actions.FindItem(TestWorld::INVENTORY, TestWorld::COINS))
    {
        fixture.client.Pump(PUMP_STEP);
    }
    CHECK_FALSE(fixture.actions.FindItem(TestWorld::INVENTORY, TestWorld::COINS));
    REQUIRE(fixture.client.GetState().FindInventory(TestWorld::INVENTORY) != nullptr);
    CHECK(fixture.client.GetState().FindInventory(TestWorld::INVENTORY)->slots.empty());
}
