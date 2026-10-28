#include "pch.hpp"
#include "../Support/Game/Fixtures.hpp"
#include "../Support/LogCapture.hpp"

#include "Game/Decode/ServerPacketDecoder.hpp"
#include "Game/Decode/ZoneDecoder.hpp"
#include "Game/Error/ProtocolError.hpp"
#include "Game/Protocol/Protocol.hpp"
#include "Game/Protocol/ServerProt.hpp"
#include "Game/State/GameState_s.hpp"
#include "Io/Packet.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/generators/catch_generators.hpp>

namespace
{
    class SceneFixture
    {
    public:
        explicit SceneFixture(Revision_e revision = Revision_e::Rev289)
            : decoder{Protocol{revision}, capture.GetLogger()}
            , state{Fixtures::PlacedState()}
        {
            Decode(ServerProt_e::UpdateZonePartialFollows, Fixtures::Zone(48, 48));
            state.tick = 42;
        }

        void Decode(ServerProt_e prot, std::span<const u8> bytes = {})
        {
            decoder.Decode(prot, bytes, state);
        }

        void Decode(ServerProt_e prot, const Packet& packet)
        {
            Decode(prot, packet.GetData());
        }

        LogCapture capture;
        ServerPacketDecoder decoder;
        GameState_s state;
    };

    Packet Projectile(s16 target, s8 dx = 3, s8 dz = -2)
    {
        auto packet = Packet{};
        packet.P1(0x12);
        packet.P1(dx);
        packet.P1(dz);
        packet.P2(target);
        packet.P2(18);
        packet.P1(43);
        packet.P1(31);
        packet.P2(51);
        packet.P2(80);
        packet.P1(16);
        packet.P1(64);
        return packet;
    }
}

TEST_CASE("Active zones include the radius boundary and exclude other levels", "[SceneZonePackets][ZoneCleanupCoverage]")
{
    const auto state = Fixtures::PlacedState();
    const auto [dx, dz, level, expected] = GENERATE(
        std::tuple{-24, -24, 0, true}, std::tuple{31, 31, 0, true},
        std::tuple{-25, 0, 0, false}, std::tuple{32, 0, 0, false},
        std::tuple{0, -25, 0, false}, std::tuple{0, 32, 0, false},
        std::tuple{0, 0, 1, false});
    CAPTURE(dx, dz, level);
    CHECK(ZoneDecoder::IsActive(state, {.x = Fixtures::HOME + dx, .z = Fixtures::HOME + dz, .level = level}) == expected);
}

TEST_CASE("Active zones stop at the build area even near its edges", "[SceneZonePackets][ZoneCleanupCoverage]")
{
    auto state = Fixtures::PlacedState();
    const auto local = GENERATE(0, BuildArea_s::SIZE - 1);
    state.localPlayer.tile = {.x = Fixtures::BASE + local, .z = Fixtures::BASE + local};
    CHECK(ZoneDecoder::IsActive(state, state.localPlayer.tile));
    const auto outside = local == 0 ? Fixtures::BASE - 1 : Fixtures::BASE + BuildArea_s::SIZE;
    CHECK_FALSE(ZoneDecoder::IsActive(state, {.x = outside, .z = state.localPlayer.tile.z}));
    CHECK_FALSE(ZoneDecoder::IsActive(state, {.x = state.localPlayer.tile.x, .z = outside}));
}

TEST_CASE("Zone pruning removes stale state once and waits for placement and loading", "[SceneZonePackets][ZoneCleanupCoverage]")
{
    auto state = Fixtures::PlacedState();
    const auto home = state.localPlayer.tile;
    const auto far = Tile_s{.x = home.x + 32, .z = home.z};
    const auto upstairs = Tile_s{.x = home.x, .z = home.z, .level = 1};
    state.groundItems = {{.tile = home, .id = 995}, {.tile = far, .id = 526}, {.tile = upstairs, .id = 1511}};
    state.locChanges = {{.tile = home, .id = 1530}, {.tile = far, .id = -1}, {.tile = upstairs, .id = 1276}};
    state.sceneChangeCount = 10;
    const auto ready = GENERATE(0, 1, 2);
    state.placed = ready != 0;
    state.buildArea.loaded = ready != 1;
    ZoneDecoder::PruneInactive(state);
    if (ready != 2)
    {
        CHECK(state.groundItems.size() == 3);
        CHECK(state.locChanges.size() == 3);
        CHECK(state.sceneChangeCount == 10);
        state.placed = true;
        state.buildArea.loaded = true;
        ZoneDecoder::PruneInactive(state);
    }
    REQUIRE(state.groundItems.size() == 1);
    CHECK(state.groundItems.front().id == 995);
    REQUIRE(state.locChanges.size() == 1);
    CHECK(state.locChanges.front().id == 1530);
    CHECK(state.sceneChangeCount == 11);
    ZoneDecoder::PruneInactive(state);
    CHECK(state.sceneChangeCount == 11);
    state.groundItems.push_back({.tile = far, .id = 526});
    ZoneDecoder::PruneInactive(state);
    CHECK(state.groundItems.size() == 1);
    CHECK(state.sceneChangeCount == 11);
}

TEST_CASE("Zone resets preserve neighboring zones and other floors", "[SceneZonePackets][ZoneCleanupCoverage]")
{
    auto state = Fixtures::PlacedState();
    auto decoder = ZoneDecoder{Protocol{Revision_e::Rev289}};
    const auto bytes = Fixtures::Zone(48, 48);
    auto zone = Packet{bytes};
    decoder.SetZone(zone);
    const auto home = state.localPlayer.tile;
    const auto edge = Tile_s{.x = home.x + 7, .z = home.z + 7};
    const auto next = Tile_s{.x = home.x + 8, .z = home.z};
    const auto upstairs = Tile_s{.x = home.x, .z = home.z, .level = 1};
    for (const auto& tile : {home, edge, next, upstairs})
    {
        state.groundItems.push_back({.tile = tile, .id = 995});
        state.locChanges.push_back({.tile = tile, .id = 1530});
    }
    state.sceneChangeCount = 12;
    decoder.ResetZone(state);
    REQUIRE(state.groundItems.size() == 2);
    REQUIRE(state.locChanges.size() == 2);
    CHECK(state.groundItems[0].tile == next);
    CHECK(state.groundItems[1].tile == upstairs);
    CHECK(state.locChanges[0].tile == next);
    CHECK(state.locChanges[1].tile == upstairs);
    CHECK(state.sceneChangeCount == 13);
    decoder.ResetZone(state);
    CHECK(state.sceneChangeCount == 13);
}

TEST_CASE("Scene animation resets affect every entity and preserve their other state", "[SceneZonePackets]")
{
    const auto revision = GENERATE(Revision_e::Rev225, Revision_e::Rev274, Revision_e::Rev289);
    auto fixture = SceneFixture{revision};
    auto& state = fixture.state;
    state.localPlayer.animation.id = 879;
    state.players.resize(2);
    state.players[0].animation.id = 123;
    state.players[1].animation.id = -1;
    state.npcs.resize(2);
    state.npcs[0].animation.id = 456;
    state.npcs[1].animation.id = 789;
    state.npcs[0].type = 50;
    const auto tile = state.localPlayer.tile;
    const auto events = state.eventCount;

    fixture.Decode(ServerProt_e::ResetAnims);
    CHECK(state.localPlayer.animation.id == -1);
    REQUIRE(state.players.size() == 2);
    REQUIRE(state.npcs.size() == 2);
    CHECK(state.players[0].animation.id == -1);
    CHECK(state.players[1].animation.id == -1);
    CHECK(state.npcs[0].animation.id == -1);
    CHECK(state.npcs[1].animation.id == -1);
    CHECK(state.npcs[0].type == 50);
    CHECK(state.localPlayer.tile == tile);
    CHECK(state.eventCount == events);
}

TEST_CASE("Scene camera shaking preserves camera mode until a reset", "[SceneZonePackets]")
{
    auto fixture = SceneFixture{};
    auto camera = Packet{};
    camera.P1(50);
    camera.P1(51);
    camera.P2(300);
    camera.P1(5);
    camera.P1(100);
    auto shake = Packet{};
    shake.P1(1);
    shake.P1(2);
    shake.P1(3);
    shake.P1(4);

    fixture.Decode(ServerProt_e::CamShake, shake);
    CHECK_FALSE(fixture.state.cinematicCamera);
    const auto prot = GENERATE(ServerProt_e::CamMoveTo, ServerProt_e::CamLookAt);
    fixture.Decode(prot, camera);
    CHECK(fixture.state.cinematicCamera);
    fixture.Decode(ServerProt_e::CamShake, shake);
    CHECK(fixture.state.cinematicCamera);
    fixture.Decode(ServerProt_e::CamReset);
    CHECK_FALSE(fixture.state.cinematicCamera);
}

TEST_CASE("Scene sound packets retain the newest effects with tick and playback parameters", "[SceneZonePackets]")
{
    auto fixture = SceneFixture{};
    for (auto i = 0u; i < GameState_s::MAX_EFFECTS + 2; ++i)
    {
        fixture.state.tick = i;
        auto packet = Packet{};
        packet.P2(300 + i);
        packet.P1(3);
        packet.P2(500);
        fixture.Decode(ServerProt_e::SynthSound, packet);
    }
    const auto& sounds = fixture.state.sounds;
    REQUIRE(sounds.size() == GameState_s::MAX_EFFECTS);
    CHECK(sounds.front().id == 302);
    CHECK(sounds.front().tick == 2);
    CHECK(sounds.back().id == 301 + GameState_s::MAX_EFFECTS);
    CHECK(sounds.back().tick == GameState_s::MAX_EFFECTS + 1);
    CHECK(sounds.back().loops == 3);
    CHECK(sounds.back().delay == 500);
}

TEST_CASE("Scene music can be stopped without changing the current jingle", "[SceneZonePackets]")
{
    const auto revision = GENERATE(Revision_e::Rev274, Revision_e::Rev289);
    auto fixture = SceneFixture{revision};
    const auto song = std::to_array<u8>({0, 62});
    const auto jingle = std::to_array<u8>({0, 9, 0, 80});
    fixture.Decode(ServerProt_e::MidiSong, song);
    fixture.Decode(ServerProt_e::MidiJingle, jingle);
    fixture.Decode(ServerProt_e::MidiSong, std::to_array<u8>({0xFF, 0xFF}));
    CHECK(fixture.state.audio.song == -1);
    CHECK(fixture.state.audio.jingle == 9);
}

TEST_CASE("Zone loc merges normalise signed bounds and preserve placement parameters", "[SceneZonePackets]")
{
    const auto revision = GENERATE(Revision_e::Rev225, Revision_e::Rev274, Revision_e::Rev289);
    auto fixture = SceneFixture{revision};
    fixture.state.localPlayer.tile.level = 2;
    auto packet = Packet{};
    packet.P1(0x12);
    packet.P1((10 << 2) | 3);
    packet.P2(1276);
    packet.P2(15);
    packet.P2(30);
    packet.P2(Fixtures::PID);
    const auto reverse = GENERATE(false, true);
    packet.P1(reverse ? -4 : 3);
    packet.P1(reverse ? 5 : -2);
    packet.P1(reverse ? 3 : -4);
    packet.P1(reverse ? -2 : 5);
    fixture.Decode(ServerProt_e::LocMerge, packet);

    REQUIRE(fixture.state.locMerges.size() == 1);
    const auto& merge = fixture.state.locMerges.front();
    CHECK(merge.tile == Tile_s{.x = Fixtures::HOME + 1, .z = Fixtures::HOME + 2, .level = 2});
    CHECK(merge.min == Tile_s{.x = Fixtures::HOME - 3, .z = Fixtures::HOME, .level = 2});
    CHECK(merge.max == Tile_s{.x = Fixtures::HOME + 4, .z = Fixtures::HOME + 7, .level = 2});
    CHECK(merge.loc == 1276);
    CHECK(merge.shape == 10);
    CHECK(merge.angle == 3);
    CHECK(merge.startCycle == 15);
    CHECK(merge.endCycle == 30);
    CHECK(merge.player == Fixtures::PID);
    CHECK(merge.tick == 42);
}

TEST_CASE("Zone map and loc animations retain their coordinates and playback parameters", "[SceneZonePackets]")
{
    auto fixture = SceneFixture{};
    auto loc = Packet{};
    loc.P1(0x12);
    loc.P1((22 << 2) | 2);
    loc.P2(879);
    fixture.Decode(ServerProt_e::LocAnim, loc);
    REQUIRE(fixture.state.locAnims.size() == 1);
    const auto& animation = fixture.state.locAnims.front();
    CHECK(animation.tile == Tile_s{.x = Fixtures::HOME + 1, .z = Fixtures::HOME + 2, .level = 0});
    CHECK(animation.layer == LocLayer_e::GroundDecor);
    CHECK(animation.shape == 22);
    CHECK(animation.angle == 2);
    CHECK(animation.seq == 879);
    CHECK(animation.tick == 42);

    auto map = Packet{};
    map.P1(0x12);
    map.P2(18);
    map.P1(43);
    map.P2(500);
    fixture.Decode(ServerProt_e::MapAnim, map);
    REQUIRE(fixture.state.mapAnims.size() == 1);
    const auto& effect = fixture.state.mapAnims.front();
    CHECK(effect.tile == animation.tile);
    CHECK(effect.spotAnim == 18);
    CHECK(effect.height == 43);
    CHECK(effect.delay == 500);
    CHECK(effect.tick == 42);
}

TEST_CASE("Zone projectiles decode optional targets and emit the same launch snapshot", "[SceneZonePackets]")
{
    auto fixture = SceneFixture{};
    const auto target = GENERATE(s16{0}, s16{101}, s16{-6});
    fixture.Decode(ServerProt_e::MapProjAnim, Projectile(target));
    REQUIRE(fixture.state.projectiles.size() == 1);
    const auto& projectile = fixture.state.projectiles.front();
    CHECK(projectile.source == Tile_s{.x = Fixtures::HOME + 1, .z = Fixtures::HOME + 2, .level = 0});
    CHECK(projectile.destination == Tile_s{.x = Fixtures::HOME + 4, .z = Fixtures::HOME, .level = 0});
    if (target == 0)
    {
        CHECK_FALSE(projectile.target.has_value());
    }
    else
    {
        REQUIRE(projectile.target.has_value());
        CHECK(projectile.target->type == (target > 0 ? EntityType_e::Npc : EntityType_e::Player));
        CHECK(projectile.target->index == (target > 0 ? 100 : 5));
    }
    CHECK(projectile.spotAnim == 18);
    CHECK(projectile.sourceHeight == 43);
    CHECK(projectile.destinationHeight == 31);
    CHECK(projectile.startDelay == 51);
    CHECK(projectile.endDelay == 80);
    CHECK(projectile.peak == 16);
    CHECK(projectile.arc == 64);
    CHECK(projectile.tick == 42);
    REQUIRE_FALSE(fixture.state.events.empty());
    const auto* event = std::get_if<ProjectileLaunched_s>(&fixture.state.events.back().data);
    REQUIRE(event != nullptr);
    CHECK(event->projectile.source == projectile.source);
    CHECK(event->projectile.destination == projectile.destination);
    CHECK(event->projectile.target == projectile.target);
    CHECK(event->projectile.spotAnim == projectile.spotAnim);
    CHECK(event->projectile.tick == projectile.tick);
}

TEST_CASE("Zone projectiles outside either map boundary are discarded without launch events", "[SceneZonePackets]")
{
    auto fixture = SceneFixture{};
    const auto events = fixture.state.eventCount;
    SECTION("source outside the build area")
    {
        fixture.Decode(ServerProt_e::UpdateZonePartialFollows, Fixtures::Zone(104, 48));
        fixture.Decode(ServerProt_e::MapProjAnim, Projectile(0, -3, 0));
    }
    SECTION("destination before the west edge")
    {
        fixture.Decode(ServerProt_e::MapProjAnim, Projectile(0, -50, 0));
    }
    SECTION("destination after the east edge")
    {
        fixture.Decode(ServerProt_e::MapProjAnim, Projectile(0, 55, 0));
    }
    SECTION("destination before the south edge")
    {
        fixture.Decode(ServerProt_e::MapProjAnim, Projectile(0, 0, -51));
    }
    SECTION("destination after the north edge")
    {
        fixture.Decode(ServerProt_e::MapProjAnim, Projectile(0, 0, 54));
    }
    CHECK(fixture.state.projectiles.empty());
    CHECK(fixture.state.eventCount == events);
}

TEST_CASE("Zone projectiles can land on the first and last tiles of the build area", "[SceneZonePackets]")
{
    auto fixture = SceneFixture{};
    SECTION("first tile")
    {
        fixture.Decode(ServerProt_e::MapProjAnim, Projectile(0, -49, -50));
        REQUIRE(fixture.state.projectiles.size() == 1);
        CHECK(fixture.state.projectiles.front().destination == Tile_s{.x = Fixtures::BASE, .z = Fixtures::BASE, .level = 0});
    }
    SECTION("last tile")
    {
        fixture.Decode(ServerProt_e::MapProjAnim, Projectile(0, 54, 53));
        REQUIRE(fixture.state.projectiles.size() == 1);
        CHECK(fixture.state.projectiles.front().destination == Tile_s{.x = Fixtures::BASE + 103, .z = Fixtures::BASE + 103, .level = 0});
    }
}

TEST_CASE("Zone updates beyond the build area consume their fields without changing state", "[SceneZonePackets]")
{
    auto fixture = SceneFixture{};
    const auto prot = GENERATE(ServerProt_e::LocAddChange, ServerProt_e::LocDel,
        ServerProt_e::LocAnim, ServerProt_e::ObjAdd, ServerProt_e::ObjDel,
        ServerProt_e::ObjCount, ServerProt_e::ObjReveal, ServerProt_e::MapAnim);
    CAPTURE(static_cast<int>(prot));
    auto packet = Packet{};
    packet.P1(0x12);
    switch (prot)
    {
    case ServerProt_e::LocAddChange:
    case ServerProt_e::LocAnim:
        packet.P1((10 << 2) | 1);
        packet.P2(1276);
        break;
    case ServerProt_e::LocDel:
        packet.P1((10 << 2) | 1);
        break;
    case ServerProt_e::ObjAdd:
        packet.P2(995);
        packet.P2(10);
        break;
    case ServerProt_e::ObjDel:
        packet.P2(995);
        break;
    case ServerProt_e::ObjCount:
        packet.P2(995);
        packet.P2(10);
        packet.P2(20);
        break;
    case ServerProt_e::ObjReveal:
        packet.P2(995);
        packet.P2(10);
        packet.P2(Fixtures::PID + 1);
        break;
    case ServerProt_e::MapAnim:
        packet.P2(18);
        packet.P1(43);
        packet.P2(500);
        break;
    default:
        FAIL("Unexpected test packet");
    }
    fixture.Decode(prot, packet);
    const auto items = fixture.state.groundItems.size();
    const auto locs = fixture.state.locChanges.size();
    const auto locAnims = fixture.state.locAnims.size();
    const auto mapAnims = fixture.state.mapAnims.size();
    const auto events = fixture.state.eventCount;
    const auto sceneChanges = fixture.state.sceneChangeCount;
    const auto east = GENERATE(false, true);
    fixture.Decode(ServerProt_e::UpdateZonePartialFollows, Fixtures::Zone(east ? 104 : 48, east ? 48 : 104));
    fixture.Decode(prot, packet);
    CHECK(fixture.state.groundItems.size() == items);
    CHECK(fixture.state.locChanges.size() == locs);
    CHECK(fixture.state.locAnims.size() == locAnims);
    CHECK(fixture.state.mapAnims.size() == mapAnims);
    CHECK(fixture.state.eventCount == events);
    CHECK(fixture.state.sceneChangeCount == sceneChanges);
}

TEST_CASE("Zone counts select the matching stack and ignore stale counts", "[SceneZonePackets]")
{
    auto fixture = SceneFixture{};
    fixture.Decode(ServerProt_e::ObjAdd, Fixtures::ObjAdd(0x12, 995, 10));
    fixture.Decode(ServerProt_e::ObjAdd, Fixtures::ObjAdd(0x12, 995, 20));
    fixture.Decode(ServerProt_e::ObjAdd, Fixtures::ObjAdd(0x13, 995, 20));
    auto count = Packet{};
    count.P1(0x12);
    count.P2(995 | 0x8000);
    count.P2(20);
    count.P2(30);
    fixture.Decode(ServerProt_e::ObjCount, count);
    REQUIRE(fixture.state.groundItems.size() == 3);
    CHECK(fixture.state.groundItems[0].count == 10);
    CHECK(fixture.state.groundItems[1].count == 30);
    CHECK(fixture.state.groundItems[2].count == 20);
    const auto* event = std::get_if<GroundItemCountChanged_s>(&fixture.state.events.back().data);
    REQUIRE(event != nullptr);
    CHECK(event->previousCount == 20);
    CHECK(event->item.count == 30);
    CHECK(event->item.tile == fixture.state.groundItems[1].tile);
    const auto events = fixture.state.eventCount;
    fixture.Decode(ServerProt_e::ObjCount, count);
    CHECK(fixture.state.eventCount == events);
    CHECK(fixture.state.groundItems[1].count == 30);
    auto missing = Packet{};
    missing.P1(0x12);
    missing.P2(1511);
    fixture.Decode(ServerProt_e::ObjDel, missing);
    CHECK(fixture.state.groundItems.size() == 3);
    CHECK(fixture.state.eventCount == events);
}

TEST_CASE("Enclosed zone updates reject unknown and non zone opcodes in every revision", "[SceneZonePackets]")
{
    const auto revision = GENERATE(Revision_e::Rev225, Revision_e::Rev274, Revision_e::Rev289);
    auto fixture = SceneFixture{revision};
    const auto protocol = Protocol{revision};
    auto unknown = std::optional<u8>{};
    auto nonZone = std::optional<u8>{};
    for (auto opcode = 0; opcode < 256; ++opcode)
    {
        const auto prot = protocol.FindServerProt(static_cast<u8>(opcode));
        if (!prot)
        {
            unknown = static_cast<u8>(opcode);
        }
        else if (!ServerProt::IsZoneProt(*prot))
        {
            nonZone = static_cast<u8>(opcode);
        }
    }
    REQUIRE(unknown.has_value());
    REQUIRE(nonZone.has_value());
    const auto invalid = GENERATE_COPY(*unknown, *nonZone);
    auto enclosed = Packet{};
    enclosed.P1(48);
    enclosed.P1(48);
    enclosed.P1(invalid);
    const auto events = fixture.state.eventCount;
    CHECK_THROWS_AS(fixture.Decode(ServerProt_e::UpdateZonePartialEnclosed, enclosed), ProtocolError);
    CHECK(fixture.state.eventCount == events);
    CHECK(fixture.state.groundItems.empty());
    CHECK(fixture.state.locChanges.empty());
}
