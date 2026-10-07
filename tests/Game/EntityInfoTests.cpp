#include "pch.hpp"
#include "BitWriter.hpp"
#include "Fixtures.hpp"

#include "Game/Decode/NpcInfoDecoder.hpp"
#include "Game/Decode/PlayerInfoDecoder.hpp"
#include "Game/Protocol/Base37.hpp"
#include "Game/Protocol/WordPack.hpp"
#include "Game/ProtocolError.hpp"
#include "Game/State/Entity_s.hpp"
#include "Game/State/GameState_s.hpp"
#include "Game/State/Npc_s.hpp"
#include "Game/State/Player_s.hpp"
#include "Game/State/Social_s.hpp"
#include "Game/Tile_s.hpp"
#include "Io/Packet.hpp"

#include <catch2/catch_test_macros.hpp>

namespace
{
    constexpr auto HOME = Tile_s{.x = Fixtures::HOME, .z = Fixtures::HOME, .level = 0};

    Tile_s Offset(s32 dx, s32 dz)
    {
        return {.x = HOME.x + dx, .z = HOME.z + dz, .level = HOME.level};
    }

    Player_s MakePlayer(u16 index, const Tile_s& tile)
    {
        auto player = Player_s{};
        player.index = index;
        player.tile = tile;
        return player;
    }

    Npc_s MakeNpc(u16 index, u16 type, const Tile_s& tile)
    {
        auto npc = Npc_s{};
        npc.index = index;
        npc.type = type;
        npc.tile = tile;
        return npc;
    }

    std::vector<u16> GetIndices(const auto& entities)
    {
        auto indices = std::vector<u16>{};
        for (const auto& entity : entities)
        {
            indices.push_back(entity.index);
        }

        return indices;
    }

    std::vector<u8> WithExtended(const BitWriter& bits, const Packet& extended)
    {
        return Fixtures::Concat(bits.GetBytes(), Fixtures::ToBytes(extended));
    }
}

TEST_CASE("PLAYER_INFO places the local player", "[PlayerInfoDecoder]")
{
    auto state = GameState_s{};
    state.buildArea = BuildArea_s{.loaded = true, .baseX = Fixtures::BASE, .baseZ = Fixtures::BASE};
    state.pid = Fixtures::PID;

    auto decoder = PlayerInfoDecoder{};
    decoder.Decode(Fixtures::PlaceLocalPlayer(48, 52, 1, Fixtures::Appearance("bot")), state);

    CHECK(state.tick == 1);
    CHECK(state.placed);
    CHECK(state.localPlayer.tile == Tile_s{.x = Fixtures::BASE + 48, .z = Fixtures::BASE + 52, .level = 1});
    CHECK(state.localPlayer.lastMovement == Movement_e::Teleport);
    REQUIRE(state.localPlayer.appearance.has_value());
    CHECK(state.localPlayer.appearance->name == "Bot");

    SECTION("placing before any rebuild is a protocol error")
    {
        auto unbuilt = GameState_s{};
        CHECK_THROWS_AS(decoder.Decode(Fixtures::PlaceLocalPlayer(), unbuilt), ProtocolError);
    }
}

TEST_CASE("PLAYER_INFO moves the local player", "[PlayerInfoDecoder]")
{
    auto state = Fixtures::PlacedState();
    auto decoder = PlayerInfoDecoder{};

    SECTION("a walk step")
    {
        auto bits = BitWriter{};
        bits.Put(1, 1).Put(2, 1).Put(3, 4).Put(1, 0).Put(8, 0);
        decoder.Decode(bits.GetBytes(), state);
        CHECK(state.localPlayer.tile == Offset(1, 0));
        CHECK(state.localPlayer.lastMovement == Movement_e::Walk);
        CHECK(state.localPlayer.movedTick == state.tick);
    }

    SECTION("a run of two steps")
    {
        auto bits = BitWriter{};
        bits.Put(1, 1).Put(2, 2).Put(3, 0).Put(3, 5).Put(1, 0).Put(8, 0);
        decoder.Decode(bits.GetBytes(), state);
        CHECK(state.localPlayer.tile == Offset(-2, 0));
        CHECK(state.localPlayer.lastMovement == Movement_e::Run);
    }

    SECTION("no update leaves the player where it was")
    {
        auto bits = BitWriter{};
        bits.Put(1, 0).Put(8, 0);
        decoder.Decode(bits.GetBytes(), state);
        CHECK(state.localPlayer.tile == HOME);
        CHECK(state.tick == 1);
    }
}

TEST_CASE("PLAYER_INFO keeps the tracked list in server order", "[PlayerInfoDecoder]")
{
    auto state = Fixtures::PlacedState();
    state.players = {MakePlayer(7, Offset(1, 1)), MakePlayer(8, Offset(2, 2)), MakePlayer(9, Offset(3, 3))};
    auto decoder = PlayerInfoDecoder{};

    SECTION("unchanged, removed and walking entries")
    {
        auto bits = BitWriter{};
        bits.Put(1, 0).Put(8, 3);
        bits.Put(1, 0);
        bits.Put(1, 1).Put(2, 3);
        bits.Put(1, 1).Put(2, 1).Put(3, 6).Put(1, 0);
        decoder.Decode(bits.GetBytes(), state);

        CHECK(GetIndices(state.players) == std::vector<u16>{7, 9});
        CHECK(state.players[1].tile == Offset(3, 2));
    }

    SECTION("a short count removes the rest of the list")
    {
        auto bits = BitWriter{};
        bits.Put(1, 0).Put(8, 1).Put(1, 0);
        decoder.Decode(bits.GetBytes(), state);
        CHECK(GetIndices(state.players) == std::vector<u16>{7});
    }

    SECTION("a count past the tracked list is a desync")
    {
        auto bits = BitWriter{};
        bits.Put(1, 0).Put(8, 4);
        CHECK_THROWS_AS(decoder.Decode(bits.GetBytes(), state), ProtocolError);
    }
}

TEST_CASE("PLAYER_INFO adds new players relative to the local player", "[PlayerInfoDecoder]")
{
    auto state = Fixtures::PlacedState();
    auto decoder = PlayerInfoDecoder{};

    const auto appearance = Fixtures::Appearance("zezima");
    auto bits = BitWriter{};
    bits.Put(1, 0).Put(8, 0);
    bits.Put(11, 7).Put(5, -3).Put(5, 2).Put(1, 1).Put(1, 1);
    bits.Put(11, 12).Put(5, 15).Put(5, -16).Put(1, 0).Put(1, 0);
    bits.Put(11, 2047);

    auto extended = Packet{};
    extended.P1(0x01 | 0x20);
    extended.P1(static_cast<s32>(appearance.size()));
    extended.PData(appearance);
    extended.P2(6401);
    extended.P2(6403);
    decoder.Decode(WithExtended(bits, extended), state);

    REQUIRE(GetIndices(state.players) == std::vector<u16>{7, 12});
    const auto& zezima = state.players[0];
    CHECK(zezima.tile == Offset(-3, 2));
    CHECK(zezima.addedTick == 1);
    REQUIRE(zezima.appearance.has_value());
    CHECK(zezima.appearance->name == "Zezima");
    CHECK(zezima.appearance->wear[3].kind == WearKind_e::Object);
    CHECK(zezima.appearance->wear[3].id == Fixtures::WEAPON);
    CHECK(zezima.appearance->wear[4].kind == WearKind_e::BodyKit);
    CHECK(zezima.appearance->wear[4].id == Fixtures::TORSO_KIT);
    CHECK(zezima.appearance->wear[0].kind == WearKind_e::Empty);
    CHECK(zezima.appearance->walkAnim == 819);
    CHECK(zezima.appearance->totalLevel == 32);
    REQUIRE(zezima.faceCoord.has_value());
    CHECK(zezima.faceCoord->x == 6401);
    CHECK(zezima.faceCoord->z == 6403);

    CHECK(state.players[1].tile == Offset(15, -16));
    CHECK_FALSE(state.players[1].appearance.has_value());
    CHECK(state.FindPlayerByName("ZEZIMA") == &state.players[0]);

    SECTION("a re-added player gets its cached appearance back")
    {
        auto removeAll = BitWriter{};
        removeAll.Put(1, 0).Put(8, 0);
        decoder.Decode(removeAll.GetBytes(), state);
        CHECK(state.players.empty());

        auto readd = BitWriter{};
        readd.Put(1, 0).Put(8, 0).Put(11, 7).Put(5, 1).Put(5, 1).Put(1, 1).Put(1, 0);
        decoder.Decode(readd.GetBytes(), state);
        REQUIRE(state.players.size() == 1);
        REQUIRE(state.players[0].appearance.has_value());
        CHECK(state.players[0].appearance->name == "Zezima");
    }

    SECTION("adding a player that's already tracked is a desync")
    {
        auto duplicate = BitWriter{};
        duplicate.Put(1, 0).Put(8, 2).Put(1, 0).Put(1, 0).Put(11, 7).Put(5, 0).Put(5, 0).Put(1, 1).Put(1, 0);
        CHECK_THROWS_AS(decoder.Decode(duplicate.GetBytes(), state), ProtocolError);
    }
}

TEST_CASE("PLAYER_INFO reads extended blocks", "[PlayerInfoDecoder]")
{
    auto state = Fixtures::PlacedState();
    state.players = {MakePlayer(7, Offset(1, 1))};
    state.players[0].appearance = PlayerInfoDecoder::ReadAppearance(Fixtures::Appearance("zezima"));
    auto decoder = PlayerInfoDecoder{};

    auto bits = BitWriter{};
    bits.Put(1, 1).Put(2, 0).Put(8, 1).Put(1, 1).Put(2, 0).Put(11, 2047);

    SECTION("a mask above 0xff, on the local player and a tracked one")
    {
        auto extended = Packet{};
        extended.P1(0x80 | 0x02);
        extended.P1(0x01);
        extended.P2(866);
        extended.P1(5);
        extended.P2(0x0099);
        extended.P4((92 << 16) | 30);

        extended.P1(0x80 | 0x04 | 0x10);
        extended.P1(0x04);
        extended.P2(32768 + Fixtures::PID);
        extended.P1(3);
        extended.P1(1);
        extended.P1(7);
        extended.P1(10);
        extended.P1(4);
        extended.P1(1);
        extended.P1(3);
        extended.P1(10);
        decoder.Decode(WithExtended(bits, extended), state);

        const auto& local = state.localPlayer;
        CHECK(local.animation.id == 866);
        CHECK(local.animation.delay == 5);
        CHECK(local.spotAnim.id == 0x99);
        CHECK(local.spotAnim.height == 92);
        CHECK(local.spotAnim.delay == 30);

        const auto& other = state.players[0];
        REQUIRE(other.faceEntity.has_value());
        CHECK(other.faceEntity->type == EntityType_e::Player);
        CHECK(other.faceEntity->index == Fixtures::PID);
        REQUIRE(other.hits.size() == 2);
        CHECK(other.hits[0].damage == 3);
        CHECK(other.hits[1].damage == 4);
        CHECK(other.hits[1].health == 3);
        CHECK(other.hits[1].maxHealth == 10);
    }

    SECTION("public chat and forced text become messages")
    {
        const auto packed = WordPack::Pack("hello");
        auto extended = Packet{};
        extended.P1(0x08);
        extended.PJStr("Ouch!");

        extended.P1(0x40);
        extended.P1(1);
        extended.P1(2);
        extended.P1(0);
        extended.P1(static_cast<s32>(packed.size()));
        extended.PData(packed);
        decoder.Decode(WithExtended(bits, extended), state);

        REQUIRE(state.localPlayer.say.has_value());
        CHECK(state.localPlayer.say->text == "Ouch!");

        const auto& other = state.players[0];
        REQUIRE(other.chat.has_value());
        CHECK(other.chat->text == "Hello ");
        CHECK(other.chat->colour == 1);
        CHECK(other.chat->effect == 2);

        REQUIRE(state.messages.size() == 1);
        CHECK(state.messages[0].type == MessageType_e::Public);
        CHECK(state.messages[0].sender == "Zezima");
        CHECK(state.messages[0].sender37 == Base37::Encode("zezima"));
        CHECK(state.messages[0].sequence == 1);
    }

    SECTION("bytes after the last block are a decoder mismatch")
    {
        auto extended = Packet{};
        extended.P1(0);
        extended.P1(0);
        extended.P1(0);
        CHECK_THROWS_AS(decoder.Decode(WithExtended(bits, extended), state), ProtocolError);
    }
}

TEST_CASE("PLAYER_INFO reads an NPC-transformed appearance", "[PlayerInfoDecoder]")
{
    const auto appearance = PlayerInfoDecoder::ReadAppearance(Fixtures::Appearance("frog", 18));
    REQUIRE(appearance.npcTransform.has_value());
    CHECK(*appearance.npcTransform == 18);
    CHECK(std::ranges::all_of(appearance.wear, [](const WearSlot_s& slot)
    {
        return slot.kind == WearKind_e::Empty;
    }));
    CHECK(appearance.colours[4] == 4);
    CHECK(appearance.runAnim == 824);
    CHECK(appearance.name == "Frog");
    CHECK(appearance.combatLevel == 3);
}

TEST_CASE("PLAYER_INFO hits from a later tick replace the earlier ones", "[PlayerInfoDecoder]")
{
    auto state = Fixtures::PlacedState();
    auto decoder = PlayerInfoDecoder{};
    const auto hitLocal = [&decoder, &state](u8 damage)
    {
        auto bits = BitWriter{};
        bits.Put(1, 1).Put(2, 0).Put(8, 0).Put(11, 2047);
        auto extended = Packet{};
        extended.P1(0x10);
        extended.P1(damage);
        extended.P1(1);
        extended.P1(5);
        extended.P1(10);
        decoder.Decode(WithExtended(bits, extended), state);
    };

    hitLocal(2);
    hitLocal(3);
    REQUIRE(state.localPlayer.hits.size() == 1);
    CHECK(state.localPlayer.hits[0].damage == 3);
    CHECK(state.localPlayer.hits[0].tick == 2);
}

TEST_CASE("NPC_INFO adds, moves and removes NPCs", "[NpcInfoDecoder]")
{
    auto state = Fixtures::PlacedState();

    NpcInfoDecoder::Decode(Fixtures::AddNpc(100, 50, 2, -1), state);
    REQUIRE(state.npcs.size() == 1);
    CHECK(state.npcs[0].index == 100);
    CHECK(state.npcs[0].type == 50);
    CHECK(state.npcs[0].tile == Offset(2, -1));
    CHECK(state.FindNpc(100) == &state.npcs[0]);

    SECTION("a walk step, then removal")
    {
        auto walk = BitWriter{};
        walk.Put(8, 1).Put(1, 1).Put(2, 1).Put(3, 2).Put(1, 0);
        NpcInfoDecoder::Decode(walk.GetBytes(), state);
        CHECK(state.npcs[0].tile == Offset(3, 0));

        auto remove = BitWriter{};
        remove.Put(8, 1).Put(1, 1).Put(2, 3);
        NpcInfoDecoder::Decode(remove.GetBytes(), state);
        CHECK(state.npcs.empty());
    }

    SECTION("a teleport removes and re-adds the same index in one packet")
    {
        auto teleport = BitWriter{};
        teleport.Put(8, 1).Put(1, 1).Put(2, 3);
        teleport.Put(14, 100).Put(11, 50).Put(5, -10).Put(5, 10).Put(1, 1).Put(1, 0);
        NpcInfoDecoder::Decode(teleport.GetBytes(), state);
        REQUIRE(state.npcs.size() == 1);
        CHECK(state.npcs[0].tile == Offset(-10, 10));
        CHECK(state.npcs[0].lastMovement == Movement_e::Teleport);
    }
}

TEST_CASE("NPC_INFO reads extended blocks in mask order", "[NpcInfoDecoder]")
{
    auto state = Fixtures::PlacedState();
    state.npcs = {MakeNpc(100, 50, Offset(1, 0)), MakeNpc(101, 51, Offset(0, 1))};

    auto bits = BitWriter{};
    bits.Put(8, 2).Put(1, 1).Put(2, 0).Put(1, 1).Put(2, 0);
    bits.Put(14, 16383);

    auto extended = Packet{};
    extended.P1(0x01 | 0x02 | 0x04 | 0x10);
    extended.P1(1);
    extended.P1(0);
    extended.P1(9);
    extended.P1(10);
    extended.P2(0xFFFF);
    extended.P1(0);
    extended.P2(Fixtures::PID + 32768);
    extended.P1(2);
    extended.P1(1);
    extended.P1(7);
    extended.P1(10);

    extended.P1(0x08 | 0x20 | 0x40 | 0x80);
    extended.PJStr("Graaagh!");
    extended.P2(77);
    extended.P2(0xFFFF);
    extended.P4(0);
    extended.P2(6403);
    extended.P2(6405);

    NpcInfoDecoder::Decode(WithExtended(bits, extended), state);

    const auto& first = state.npcs[0];
    REQUIRE(first.hits.size() == 2);
    CHECK(first.hits[0].damage == 1);
    CHECK(first.hits[1].damage == 2);
    CHECK(first.hits[1].health == 7);
    CHECK(first.animation.id == -1);
    REQUIRE(first.faceEntity.has_value());
    CHECK(first.faceEntity->type == EntityType_e::Player);
    CHECK(first.faceEntity->index == Fixtures::PID);

    const auto& second = state.npcs[1];
    REQUIRE(second.say.has_value());
    CHECK(second.say->text == "Graaagh!");
    CHECK(second.type == 77);
    CHECK(second.spotAnim.id == -1);
    REQUIRE(second.faceCoord.has_value());
    CHECK(second.faceCoord->x == 6403);
}
