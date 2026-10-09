#include "pch.hpp"
#include "../Cache/TestCache.hpp"
#include "../LogCapture.hpp"
#include "FakeGameServer.hpp"
#include "Fixtures.hpp"
#include "TestWorld.hpp"

#include "Cache/GameCache_s.hpp"
#include "Core/ConfigFile.hpp"
#include "Game/GameActions.hpp"
#include "Game/GameClient.hpp"
#include "Game/Map/WorldMap.hpp"
#include "Game/Protocol/ClientProt.hpp"
#include "Game/Tile_s.hpp"
#include "Io/Packet.hpp"

#include <catch2/catch_test_macros.hpp>

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
