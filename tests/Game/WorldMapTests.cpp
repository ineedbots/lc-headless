#include "pch.hpp"
#include "../Cache/TestCache.hpp"
#include "Fixtures.hpp"

#include "Cache/GameCache_s.hpp"
#include "Core/Logger.hpp"
#include "Game/Decode/ServerPacketDecoder.hpp"
#include "Game/Map/CollisionFlag.hpp"
#include "Game/Map/WorldMap.hpp"
#include "Game/Protocol/ServerProt.hpp"
#include "Game/State/GameState_s.hpp"
#include "Game/State/Zone_s.hpp"
#include "Game/Tile_s.hpp"
#include "Io/Packet.hpp"

#include <catch2/catch_test_macros.hpp>

namespace
{
    constexpr auto DOOR = u16{1530};
    constexpr auto GATE = u16{1551};
    constexpr auto TREE = u16{1276};
    constexpr auto ROCK = u16{2000};
    constexpr auto PEBBLE = u16{2001};
    constexpr auto WALL = u8{0};
    constexpr auto WEST = u8{0};
    constexpr auto NORTH = u8{1};
    constexpr auto CENTREPIECE = u8{10};
    constexpr auto GROUND_DECOR = u8{22};
    constexpr auto LAST_LOCAL = BuildArea_s::SIZE - 1;
    constexpr auto WALL_FLAGS = CollisionFlag::WALL_WEST | CollisionFlag::RANGE_WALL_WEST;

    Tile_s Local(s32 x, s32 z)
    {
        return {.x = Fixtures::BASE + x, .z = Fixtures::BASE + z, .level = 0};
    }

    const auto DOOR_TILE = Local(Fixtures::HOME_LOCAL + 1, Fixtures::HOME_LOCAL);

    std::shared_ptr<const GameCache_s> MakeCache()
    {
        auto cache = GameCache_s{};
        TestCache::AddLoc(cache, DOOR, "Door", {"Open"});
        TestCache::AddLoc(cache, GATE, "Gate", {"Open"});
        auto& tree = TestCache::AddLoc(cache, TREE, "Tree", {"Chop down"});
        tree.width = 2;
        tree.length = 2;
        TestCache::AddLoc(cache, ROCK, "Rock").active = true;
        TestCache::AddLoc(cache, PEBBLE, "Pebble");

        const auto locs = std::to_array<TestLoc_s>({
            {.id = DOOR, .tile = DOOR_TILE, .shape = WALL, .angle = WEST},
            {.id = TREE, .tile = Local(0, 50), .shape = CENTREPIECE},
            {.id = TREE, .tile = Local(1, 60), .shape = CENTREPIECE},
            {.id = ROCK, .tile = Local(30, 30), .shape = GROUND_DECOR},
            {.id = PEBBLE, .tile = Local(31, 30), .shape = GROUND_DECOR},
        });

        const auto blocked = std::to_array<Tile_s>({Local(1, 1), Local(LAST_LOCAL - 1, LAST_LOCAL - 1), Local(10, 10)});
        TestCache::SetMap(cache, locs, blocked);
        return std::make_shared<const GameCache_s>(std::move(cache));
    }

    class MapFixture
    {
    public:
        MapFixture()
            : map{MakeCache()}
        {
            state.sceneChangeCount = 1;
            map.Update(state);
        }

        [[nodiscard]] u32 GetFlags(const Tile_s& tile) const
        {
            return map.GetCollision(tile.level).GetFlags(tile.x - Fixtures::BASE, tile.z - Fixtures::BASE);
        }

        void SetChange(s32 id, u8 shape, u8 angle)
        {
            state.locChanges = {{.tile = DOOR_TILE, .layer = LocLayer_e::Wall, .id = id, .shape = shape, .angle = angle}};
            ++state.sceneChangeCount;
            map.Update(state);
        }

        GameState_s state = Fixtures::PlacedState();
        WorldMap map;
    };
}

TEST_CASE("WorldMap builds collision from the cache", "[WorldMap]")
{
    auto fixture = MapFixture{};
    const auto& map = fixture.map;
    REQUIRE(map.IsLoaded());
    CHECK(map.GetBuildArea().baseX == Fixtures::BASE);
    CHECK(map.Contains(Local(0, 0)));
    CHECK(map.Contains(Local(LAST_LOCAL, LAST_LOCAL)));
    CHECK_FALSE(map.Contains(Local(-1, 0)));
    CHECK_FALSE(map.Contains(Tile_s{.x = Fixtures::HOME, .z = Fixtures::HOME, .level = 4}));

    CHECK(fixture.GetFlags(DOOR_TILE) == WALL_FLAGS);
    CHECK(fixture.GetFlags(Local(10, 10)) == CollisionFlag::GROUND);
    CHECK(fixture.GetFlags(Local(30, 30)) == CollisionFlag::GROUND);
    CHECK(fixture.GetFlags(Local(31, 30)) == CollisionFlag::OPEN);

    SECTION("squares at the area's corners count, and locs on its outer ring don't")
    {
        CHECK(fixture.GetFlags(Local(1, 1)) == CollisionFlag::GROUND);
        CHECK(fixture.GetFlags(Local(LAST_LOCAL - 1, LAST_LOCAL - 1)) == CollisionFlag::GROUND);
        CHECK(fixture.GetFlags(Local(1, 50)) == CollisionFlag::OPEN);
        CHECK_FALSE(map.GetLoc(Local(0, 50), LocLayer_e::Ground).has_value());
        CHECK(fixture.GetFlags(Local(2, 61)) == (CollisionFlag::LOC | CollisionFlag::RANGE_LOC));
        CHECK(map.GetLoc(Local(1, 60), LocLayer_e::Ground)->id == TREE);
    }
}

TEST_CASE("WorldMap puts the server's changes in place of the cache's locs", "[WorldMap]")
{
    auto fixture = MapFixture{};
    const auto& map = fixture.map;

    const auto door = map.GetLoc(DOOR_TILE, LocLayer_e::Wall);
    REQUIRE(door.has_value());
    CHECK(door->id == DOOR);
    CHECK_FALSE(door->changed);
    CHECK_FALSE(map.GetLoc(DOOR_TILE, LocLayer_e::Ground).has_value());

    SECTION("only once the scene count moves")
    {
        fixture.state.locChanges = {{.tile = DOOR_TILE, .layer = LocLayer_e::Wall, .id = -1}};
        fixture.map.Update(fixture.state);
        CHECK(fixture.GetFlags(DOOR_TILE) == WALL_FLAGS);
        CHECK(map.GetLoc(DOOR_TILE, LocLayer_e::Wall)->id == DOOR);
    }

    SECTION("a removed door opens")
    {
        fixture.SetChange(-1, WALL, WEST);
        CHECK(fixture.GetFlags(DOOR_TILE) == CollisionFlag::OPEN);
        const auto removed = map.GetLoc(DOOR_TILE, LocLayer_e::Wall);
        REQUIRE(removed.has_value());
        CHECK(removed->id == -1);
        CHECK(removed->changed);
        CHECK(std::ranges::none_of(map.GetLocs(0), [](const SceneLoc_s& loc)
        {
            return loc.tile == DOOR_TILE;
        }));
    }

    SECTION("a door replaced by another type takes that type's collision")
    {
        fixture.SetChange(GATE, WALL, NORTH);
        CHECK(fixture.GetFlags(DOOR_TILE) == (CollisionFlag::WALL_NORTH | CollisionFlag::RANGE_WALL_NORTH));
        CHECK(map.GetLoc(DOOR_TILE, LocLayer_e::Wall)->id == GATE);

        const auto locs = map.GetLocs(0);
        const auto gate = std::ranges::find_if(locs, [](const SceneLoc_s& loc)
        {
            return loc.tile == DOOR_TILE;
        });

        REQUIRE(gate != locs.end());
        CHECK(gate->id == GATE);
        CHECK(gate->changed);
        CHECK(std::ranges::count(locs, DOOR_TILE, &SceneLoc_s::tile) == 1);
    }

    SECTION("Clear forgets the area until the next update")
    {
        fixture.map.Clear();
        CHECK_FALSE(map.IsLoaded());
        CHECK_FALSE(map.Contains(DOOR_TILE));
        CHECK(map.GetLocs(0).empty());
        fixture.map.Update(fixture.state);
        CHECK(map.IsLoaded());
    }
}

TEST_CASE("WorldMap follows the decoders' zone resets", "[WorldMap]")
{
    auto fixture = MapFixture{};
    auto decoder = ServerPacketDecoder{};
    const auto zone = Fixtures::Zone(Fixtures::HOME_LOCAL, Fixtures::HOME_LOCAL);
    const auto doorPos = static_cast<u8>(1 << 4);

    decoder.Decode(ServerProt_e::UpdateZonePartialFollows, zone, fixture.state);
    auto del = Packet{};
    del.P1(doorPos);
    del.P1((WALL << 2) | WEST);
    decoder.Decode(ServerProt_e::LocDel, Fixtures::ToBytes(del), fixture.state);
    fixture.map.Update(fixture.state);
    CHECK(fixture.GetFlags(DOOR_TILE) == CollisionFlag::OPEN);

    decoder.Decode(ServerProt_e::UpdateZoneFullFollows, zone, fixture.state);
    fixture.map.Update(fixture.state);
    CHECK(fixture.GetFlags(DOOR_TILE) == WALL_FLAGS);
    CHECK_FALSE(fixture.map.GetLoc(DOOR_TILE, LocLayer_e::Wall)->changed);
}
