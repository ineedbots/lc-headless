#include "pch.hpp"
#include "../LogCapture.hpp"
#include "BitWriter.hpp"
#include "Fixtures.hpp"

#include "Core/Logger.hpp"
#include "Game/Decode/ServerPacketDecoder.hpp"
#include "Game/Protocol/Base37.hpp"
#include "Game/Protocol/ServerProt.hpp"
#include "Game/Protocol/WordPack.hpp"
#include "Game/ProtocolError.hpp"
#include "Game/State/GameState_s.hpp"
#include "Game/State/Social_s.hpp"
#include "Game/State/Zone_s.hpp"
#include "Game/Tile_s.hpp"
#include "Io/Packet.hpp"

#include <catch2/catch_test_macros.hpp>

namespace
{
    constexpr auto INVENTORY = u16{3214};
    constexpr auto HOME_ZONE_LOCAL = Fixtures::HOME_LOCAL & ~7;

    class DecoderFixture
    {
    public:
        DecoderFixture()
            : decoder{capture.GetLogger()}
            , state{Fixtures::PlacedState()}
        {
        }

        void Decode(ServerProt_e prot, const Packet& packet)
        {
            decoder.Decode(prot, packet.GetData(), state);
        }

        void Decode(ServerProt_e prot, const std::vector<u8>& payload = {})
        {
            decoder.Decode(prot, payload, state);
        }

        LogCapture capture;
        ServerPacketDecoder decoder;
        GameState_s state;
    };

    Tile_s HomeOffset(s32 dx, s32 dz)
    {
        return {.x = Fixtures::HOME + dx, .z = Fixtures::HOME + dz, .level = 0};
    }

    u8 ToPos(s32 dx, s32 dz)
    {
        return static_cast<u8>((dx << 4) | dz);
    }

    void PutItem(Packet& packet, s32 id, s32 count)
    {
        packet.P2(id + 1);
        if (count >= 255)
        {
            packet.P1(255);
            packet.P4(count);
            return;
        }

        packet.P1(count);
    }
}

TEST_CASE("ServerPacketDecoder tracks inventories", "[ServerPacketDecoder]")
{
    auto fixture = DecoderFixture{};
    auto& state = fixture.state;

    auto full = Packet{};
    full.P2(INVENTORY);
    full.P2(3);
    PutItem(full, 995, 100000);
    full.P2(0);
    full.P1(0);
    PutItem(full, 1511, 1);
    fixture.Decode(ServerProt_e::UpdateInvFull, full);

    const auto* inventory = state.FindInventory(INVENTORY);
    REQUIRE(inventory != nullptr);
    REQUIRE(inventory->slots.size() == 3);
    CHECK(inventory->slots[0].id == 995);
    CHECK(inventory->slots[0].count == 100000);
    CHECK(inventory->slots[1].id == -1);
    CHECK(inventory->slots[2].id == 1511);

    SECTION("a partial update changes and adds slots")
    {
        auto partial = Packet{};
        partial.P2(INVENTORY);
        partial.P1(1);
        PutItem(partial, 1512, 5);
        partial.P2(0x8000 + 200);
        PutItem(partial, 4151, 1);
        fixture.Decode(ServerProt_e::UpdateInvPartial, partial);

        REQUIRE(inventory->slots.size() == 201);
        CHECK(inventory->slots[1].id == 1512);
        CHECK(inventory->slots[1].count == 5);
        CHECK(inventory->slots[200].id == 4151);
        CHECK(inventory->slots[0].id == 995);
    }

    SECTION("a full update replaces every slot")
    {
        auto empty = Packet{};
        empty.P2(INVENTORY);
        empty.P2(0);
        fixture.Decode(ServerProt_e::UpdateInvFull, empty);
        CHECK(state.FindInventory(INVENTORY)->slots.empty());
    }

    SECTION("stopping the transmit forgets the inventory")
    {
        auto stop = Packet{};
        stop.P2(INVENTORY);
        fixture.Decode(ServerProt_e::UpdateInvStopTransmit, stop);
        CHECK(state.FindInventory(INVENTORY) == nullptr);
    }
}

TEST_CASE("ServerPacketDecoder tracks varps, stats and player state", "[ServerPacketDecoder]")
{
    auto fixture = DecoderFixture{};
    auto& state = fixture.state;

    auto small = Packet{};
    small.P2(173);
    small.P1(-5);
    fixture.Decode(ServerProt_e::VarpSmall, small);

    auto large = Packet{};
    large.P2(281);
    large.P4(100000);
    fixture.Decode(ServerProt_e::VarpLarge, large);

    CHECK(state.GetVarp(173) == -5);
    CHECK(state.GetVarp(281) == 100000);
    CHECK(state.GetVarp(1) == 0);

    const auto setStat = [&fixture](u8 stat, s32 xp, u8 level)
    {
        auto packet = Packet{};
        packet.P1(stat);
        packet.P4(xp);
        packet.P1(level);
        fixture.Decode(ServerProt_e::UpdateStat, packet);
    };

    setStat(3, 1154, 8);
    CHECK(state.stats[3].xp == 1154);
    CHECK(state.stats[3].level == 8);
    CHECK(state.stats[3].baseLevel == 10);

    setStat(3, 1153, 9);
    CHECK(state.stats[3].baseLevel == 9);
    setStat(0, 0, 1);
    CHECK(state.stats[0].baseLevel == 1);
    setStat(0, 83, 2);
    CHECK(state.stats[0].baseLevel == 2);
    setStat(0, 13034431, 99);
    CHECK(state.stats[0].baseLevel == 99);
    setStat(0, 200000000, 99);
    CHECK(state.stats[0].baseLevel == 99);

    fixture.Decode(ServerProt_e::UpdateRunEnergy, std::vector<u8>{87});
    fixture.Decode(ServerProt_e::UpdateRunWeight, std::vector<u8>{0xFF, 0xFE});
    fixture.Decode(ServerProt_e::UpdatePid, Fixtures::UpdatePid(9, false));
    CHECK(state.runEnergy == 87);
    CHECK(state.runWeight == -2);
    CHECK(state.pid == 9);
    CHECK(state.localPlayer.index == 9);
    CHECK_FALSE(state.members);

    SECTION("a stat past the table is skipped with a warning")
    {
        setStat(40, 1, 1);
        CHECK(std::ranges::any_of(fixture.capture.GetEntries(), [](const CapturedLog_s& entry)
        {
            return entry.level == LogLevel_e::Warning;
        }));
    }
}

TEST_CASE("ServerPacketDecoder tracks modal interfaces", "[ServerPacketDecoder]")
{
    auto fixture = DecoderFixture{};
    const auto& interfaces = fixture.state.interfaces;
    const auto com = [](u16 id)
    {
        auto packet = Packet{};
        packet.P2(id);
        return Fixtures::ToBytes(packet);
    };

    fixture.Decode(ServerProt_e::IfOpenMain, com(5));
    CHECK(interfaces.mainModal == 5);

    fixture.Decode(ServerProt_e::IfOpenChat, com(6));
    CHECK(interfaces.chatModal == 6);
    CHECK(interfaces.mainModal == -1);

    fixture.Decode(ServerProt_e::IfOpenSide, com(7));
    CHECK(interfaces.sideModal == 7);
    CHECK(interfaces.chatModal == -1);

    fixture.Decode(ServerProt_e::IfOpenMainSide, Fixtures::Concat(com(8), com(9)));
    CHECK(interfaces.mainModal == 8);
    CHECK(interfaces.sideModal == 9);

    fixture.Decode(ServerProt_e::PCountDialog);
    CHECK(interfaces.countDialogOpen);

    fixture.Decode(ServerProt_e::IfClose);
    CHECK(interfaces.mainModal == -1);
    CHECK(interfaces.sideModal == -1);
    CHECK_FALSE(interfaces.countDialogOpen);

    fixture.Decode(ServerProt_e::IfOpenOverlay, std::vector<u8>{0xFF, 0xFF});
    CHECK(interfaces.overlay == -1);

    fixture.Decode(ServerProt_e::IfSetTab, std::vector<u8>{0x0F, 0xA0, 3});
    CHECK(interfaces.tabs[3] == 4000);
    fixture.Decode(ServerProt_e::IfSetTab, std::vector<u8>{0xFF, 0xFF, 3});
    CHECK(interfaces.tabs[3] == -1);
    fixture.Decode(ServerProt_e::IfSetTabActive, std::vector<u8>{6});
    CHECK(interfaces.activeTab == 6);
}

TEST_CASE("ServerPacketDecoder records component changes", "[ServerPacketDecoder]")
{
    auto fixture = DecoderFixture{};
    const auto& components = fixture.state.interfaces.components;

    auto text = Packet{};
    text.P2(100);
    text.PJStr("Click here to continue");
    fixture.Decode(ServerProt_e::IfSetText, text);
    fixture.Decode(ServerProt_e::IfSetHide, std::vector<u8>{0, 100, 1});
    fixture.Decode(ServerProt_e::IfSetColour, std::vector<u8>{0, 100, 0x7C, 0x00});
    fixture.Decode(ServerProt_e::IfSetNpcHead, std::vector<u8>{0, 100, 0, 50});
    fixture.Decode(ServerProt_e::IfSetPosition, std::vector<u8>{0, 100, 0xFF, 0xF6, 0, 20});

    const auto& component = components.at(100);
    CHECK(component.text == "Click here to continue");
    CHECK(component.hidden == true);
    CHECK(component.colour == 0xF80000u);
    REQUIRE(component.model.has_value());
    CHECK(component.model->kind == ComponentModelKind_e::NpcHead);
    CHECK(component.model->id == 50);
    REQUIRE(component.position.has_value());
    CHECK(component.position->x == -10);
    CHECK(component.position->y == 20);
}

TEST_CASE("ServerPacketDecoder records messages", "[ServerPacketDecoder]")
{
    auto fixture = DecoderFixture{};
    const auto& messages = fixture.state.messages;

    fixture.Decode(ServerProt_e::MessageGame, Fixtures::MessageGame("Welcome to RuneScape."));
    fixture.Decode(ServerProt_e::MessageGame, Fixtures::MessageGame("Zezima:tradereq:"));
    fixture.Decode(ServerProt_e::MessageGame, Fixtures::MessageGame("Zezima:duelreq:"));

    REQUIRE(messages.size() == 3);
    CHECK(messages[0].type == MessageType_e::Game);
    CHECK(messages[0].text == "Welcome to RuneScape.");
    CHECK(messages[1].type == MessageType_e::TradeRequest);
    CHECK(messages[1].sender == "Zezima");
    CHECK(messages[1].sender37 == Base37::Encode("zezima"));
    CHECK(messages[2].type == MessageType_e::DuelRequest);
    CHECK(fixture.state.GetMessagesAfter(1).size() == 2);

    SECTION("private messages are decoded once per message ID")
    {
        auto packet = Packet{};
        packet.P8(std::bit_cast<s64>(Base37::Encode("zezima")));
        packet.P4(77);
        packet.P1(2);
        packet.PData(WordPack::Pack("hi"));
        fixture.Decode(ServerProt_e::MessagePrivate, packet);
        fixture.Decode(ServerProt_e::MessagePrivate, packet);

        REQUIRE(messages.size() == 4);
        CHECK(messages[3].type == MessageType_e::Private);
        CHECK(messages[3].sender == "Zezima");
        CHECK(messages[3].rights == 2);
        CHECK(messages[3].text == "Hi");
        CHECK(fixture.state.messageCount == 4);
    }
}

TEST_CASE("ServerPacketDecoder tracks friends and ignores", "[ServerPacketDecoder]")
{
    auto fixture = DecoderFixture{};
    const auto& social = fixture.state.social;
    const auto friendUpdate = [](std::string_view name, u8 world)
    {
        auto packet = Packet{};
        packet.P8(std::bit_cast<s64>(Base37::Encode(name)));
        packet.P1(world);
        return Fixtures::ToBytes(packet);
    };

    fixture.Decode(ServerProt_e::UpdateFriendList, friendUpdate("zezima", 0));
    fixture.Decode(ServerProt_e::UpdateFriendList, friendUpdate("zezima", 2));
    fixture.Decode(ServerProt_e::UpdateFriendList, friendUpdate("bot", 1));
    REQUIRE(social.friends.size() == 2);
    CHECK(social.friends[0].name == "Zezima");
    CHECK(social.friends[0].world == 2);

    auto ignores = Packet{};
    ignores.P8(std::bit_cast<s64>(Base37::Encode("a")));
    ignores.P8(std::bit_cast<s64>(Base37::Encode("b")));
    fixture.Decode(ServerProt_e::UpdateIgnoreList, ignores);
    CHECK(social.ignores == std::vector<u64>{1, 2});

    fixture.Decode(ServerProt_e::ChatFilterSettings, std::vector<u8>{1, 2, 0});
    fixture.Decode(ServerProt_e::FriendListLoaded, std::vector<u8>{2});
    CHECK(social.publicMode == 1);
    CHECK(social.privateMode == 2);
    CHECK(social.friendServerStatus == 2);
}

TEST_CASE("ServerPacketDecoder applies zone updates", "[ServerPacketDecoder]")
{
    auto fixture = DecoderFixture{};
    auto& state = fixture.state;
    const auto zone = Fixtures::Zone(HOME_ZONE_LOCAL, HOME_ZONE_LOCAL);
    const auto itemTile = Tile_s{.x = Fixtures::BASE + HOME_ZONE_LOCAL + 2, .z = Fixtures::BASE + HOME_ZONE_LOCAL + 3, .level = 0};

    fixture.Decode(ServerProt_e::UpdateZonePartialFollows, zone);
    fixture.Decode(ServerProt_e::ObjAdd, Fixtures::ObjAdd(ToPos(2, 3), 995, 50));
    REQUIRE(state.groundItems.size() == 1);
    CHECK(state.groundItems[0].tile == itemTile);
    CHECK(state.groundItems[0].id == 995);
    CHECK(state.GetGroundItemsAt(itemTile).size() == 1);

    SECTION("an enclosed update applies every sub-packet")
    {
        auto enclosed = Packet{};
        enclosed.PData(zone);
        enclosed.P1(117);
        enclosed.P1(ToPos(2, 3));
        enclosed.P2(995);
        enclosed.P2(50);
        enclosed.P2(75);
        enclosed.P1(90);
        enclosed.P1(ToPos(1, 1));
        enclosed.P1((10 << 2) | 1);
        enclosed.P2(1276);
        enclosed.P1(87);
        enclosed.P1(ToPos(0, 0));
        enclosed.P1(3);
        enclosed.P1(-2);
        enclosed.P2(-(Fixtures::PID + 1));
        enclosed.P2(18);
        enclosed.P1(43);
        enclosed.P1(31);
        enclosed.P2(51);
        enclosed.P2(80);
        enclosed.P1(16);
        enclosed.P1(64);
        fixture.Decode(ServerProt_e::UpdateZonePartialEnclosed, enclosed);

        CHECK(state.groundItems[0].count == 75);
        REQUIRE(state.locChanges.size() == 1);
        CHECK(state.locChanges[0].id == 1276);
        CHECK(state.locChanges[0].layer == LocLayer_e::Ground);
        CHECK(state.locChanges[0].shape == 10);
        CHECK(state.locChanges[0].angle == 1);
        REQUIRE(state.projectiles.size() == 1);
        const auto& projectile = state.projectiles[0];
        CHECK(projectile.destination.x == projectile.source.x + 3);
        CHECK(projectile.destination.z == projectile.source.z - 2);
        REQUIRE(projectile.target.has_value());
        CHECK(projectile.target->type == EntityType_e::Player);
        CHECK(projectile.target->index == Fixtures::PID);

        auto del = Packet{};
        del.P1(ToPos(1, 1));
        del.P1((10 << 2) | 1);
        fixture.Decode(ServerProt_e::LocDel, del);
        REQUIRE(state.locChanges.size() == 1);
        CHECK(state.locChanges[0].id == -1);
    }

    SECTION("a full update resets the zone")
    {
        fixture.Decode(ServerProt_e::UpdateZoneFullFollows, zone);
        CHECK(state.groundItems.empty());
    }

    SECTION("deleting matches the object ID on the tile")
    {
        auto del = Packet{};
        del.P1(ToPos(2, 3));
        del.P2(995 | 0x8000);
        fixture.Decode(ServerProt_e::ObjDel, del);
        CHECK(state.groundItems.empty());
    }

    SECTION("a reveal to this player is skipped")
    {
        auto reveal = Packet{};
        reveal.P1(ToPos(4, 4));
        reveal.P2(526);
        reveal.P2(1);
        reveal.P2(Fixtures::PID);
        fixture.Decode(ServerProt_e::ObjReveal, reveal);
        CHECK(state.groundItems.size() == 1);
    }

    SECTION("a rebuild clears zone state")
    {
        fixture.Decode(ServerProt_e::RebuildNormal, Fixtures::Rebuild(401, 399));
        CHECK(state.groundItems.empty());
        CHECK(state.buildArea.baseX == (401 - 6) * 8);
        CHECK(state.buildArea.baseZ == (399 - 6) * 8);
    }

    SECTION("zones that leave the active area are pruned after PLAYER_INFO")
    {
        state.groundItems.push_back({.tile = HomeOffset(4 * 8, 0), .id = 1});
        state.groundItems.push_back({.tile = HomeOffset(0, 0), .id = 2, .count = 1});

        auto bits = BitWriter{};
        bits.Put(1, 0).Put(8, 0);
        fixture.Decode(ServerProt_e::PlayerInfo, bits.GetBytes());

        REQUIRE(state.groundItems.size() == 2);
        CHECK(state.groundItems[0].id == 995);
        CHECK(state.groundItems[1].id == 2);
    }

    SECTION("a loc shape past 22 is a protocol error")
    {
        auto add = Packet{};
        add.P1(0);
        add.P1(23 << 2);
        add.P2(1);
        CHECK_THROWS_AS(fixture.Decode(ServerProt_e::LocAddChange, add), ProtocolError);
    }
}

TEST_CASE("ServerPacketDecoder tracks hints, options and the map flag", "[ServerPacketDecoder]")
{
    auto fixture = DecoderFixture{};
    auto& state = fixture.state;

    fixture.Decode(ServerProt_e::HintArrow, std::vector<u8>{2, 0x0C, 0x80, 0x0C, 0x81, 30});
    REQUIRE(state.hintArrow.has_value());
    CHECK(state.hintArrow->kind == HintArrowKind_e::Tile);
    CHECK(state.hintArrow->tile == Tile_s{.x = 3200, .z = 3201, .level = 0});

    fixture.Decode(ServerProt_e::HintArrow, std::vector<u8>{1, 0, 100, 0, 0, 0});
    REQUIRE(state.hintArrow.has_value());
    CHECK(state.hintArrow->kind == HintArrowKind_e::Npc);
    CHECK(state.hintArrow->index == 100);

    fixture.Decode(ServerProt_e::HintArrow, std::vector<u8>{255, 0, 0, 0, 0, 0});
    CHECK_FALSE(state.hintArrow.has_value());

    auto op = Packet{};
    op.P1(4);
    op.P1(0);
    op.PJStr("Trade with");
    fixture.Decode(ServerProt_e::SetPlayerOp, op);
    REQUIRE(state.playerOps[3].has_value());
    CHECK(state.playerOps[3]->text == "Trade with");
    CHECK(state.playerOps[3]->deprioritised);

    auto removeOp = Packet{};
    removeOp.P1(4);
    removeOp.P1(1);
    removeOp.PJStr("NULL");
    fixture.Decode(ServerProt_e::SetPlayerOp, removeOp);
    CHECK_FALSE(state.playerOps[3].has_value());

    state.walkDestination = HomeOffset(5, 5);
    fixture.Decode(ServerProt_e::UnsetMapFlag);
    CHECK_FALSE(state.walkDestination.has_value());
}

TEST_CASE("ServerPacketDecoder rejects payloads that don't fit the layout", "[ServerPacketDecoder]")
{
    auto fixture = DecoderFixture{};
    CHECK_THROWS_AS(fixture.Decode(ServerProt_e::UpdateRunEnergy, std::vector<u8>{1, 2}), ProtocolError);
    CHECK_THROWS_AS(fixture.Decode(ServerProt_e::UpdateStat, std::vector<u8>{1, 2}), ProtocolError);
    CHECK_THROWS_AS(fixture.Decode(ServerProt_e::UpdateInvFull, std::vector<u8>{0, 1, 0, 2, 0, 1}), ProtocolError);
}
