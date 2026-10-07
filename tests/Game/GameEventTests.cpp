#include "pch.hpp"
#include "../LogCapture.hpp"
#include "BitWriter.hpp"
#include "Fixtures.hpp"

#include "Core/Logger.hpp"
#include "Game/Decode/NpcInfoDecoder.hpp"
#include "Game/Decode/PlayerInfoDecoder.hpp"
#include "Game/Decode/ServerPacketDecoder.hpp"
#include "Game/Protocol/ServerProt.hpp"
#include "Game/State/Entity_s.hpp"
#include "Game/State/GameEvent_s.hpp"
#include "Game/State/GameState_s.hpp"
#include "Game/State/Npc_s.hpp"
#include "Game/State/Player_s.hpp"
#include "Game/Tile_s.hpp"
#include "Io/Packet.hpp"

#include <catch2/catch_test_macros.hpp>

namespace
{
    constexpr auto INVENTORY = u16{3214};
    constexpr auto HOME_ZONE_LOCAL = Fixtures::HOME_LOCAL & ~7;

    Tile_s Offset(s32 dx, s32 dz)
    {
        return {.x = Fixtures::HOME + dx, .z = Fixtures::HOME + dz, .level = 0};
    }

    Tile_s ZoneOffset(s32 dx, s32 dz)
    {
        return {.x = Fixtures::BASE + HOME_ZONE_LOCAL + dx, .z = Fixtures::BASE + HOME_ZONE_LOCAL + dz, .level = 0};
    }

    u8 ToPos(s32 dx, s32 dz)
    {
        return static_cast<u8>((dx << 4) | dz);
    }

    Npc_s MakeNpc(u16 index, u16 type, const Tile_s& tile)
    {
        auto npc = Npc_s{};
        npc.index = index;
        npc.type = type;
        npc.tile = tile;
        return npc;
    }

    Player_s MakePlayer(u16 index, const Tile_s& tile)
    {
        auto player = Player_s{};
        player.index = index;
        player.tile = tile;
        return player;
    }

    void PutHit(Packet& packet, s32 damage, s32 health)
    {
        packet.P1(damage);
        packet.P1(1);
        packet.P1(health);
        packet.P1(10);
    }

    struct EventDescriber
    {
        std::string operator()(const NpcAdded_s& event) const
        {
            return std::format("npc added {} type {}", event.npc.index, event.npc.type);
        }

        std::string operator()(const NpcRemoved_s& event) const
        {
            return std::format("npc removed {}", event.npc.index);
        }

        std::string operator()(const NpcHit_s& event) const
        {
            return std::format("npc hit {} damage {}", event.index, event.hit.damage);
        }

        std::string operator()(const PlayerAdded_s& event) const
        {
            return std::format("player added {} {}", event.player.index, event.player.appearance ? event.player.appearance->name : "?");
        }

        std::string operator()(const PlayerRemoved_s& event) const
        {
            return std::format("player removed {}", event.player.index);
        }

        std::string operator()(const PlayerHit_s& event) const
        {
            return std::format("player hit {} damage {}", event.index, event.hit.damage);
        }

        std::string operator()(const LocalHit_s& event) const
        {
            return std::format("local hit damage {}", event.hit.damage);
        }

        std::string operator()(const GroundItemAdded_s& event) const
        {
            return std::format("item added {} x{}", event.item.id, event.item.count);
        }

        std::string operator()(const GroundItemRemoved_s& event) const
        {
            return std::format("item removed {} x{}", event.item.id, event.item.count);
        }

        std::string operator()(const GroundItemCountChanged_s& event) const
        {
            return std::format("item count {} {} -> {}", event.item.id, event.previousCount, event.item.count);
        }

        std::string operator()(const LocChanged_s& event) const
        {
            return std::format("loc {}", event.change.id);
        }

        std::string operator()(const InventoryChanged_s& event) const
        {
            return std::format("inventory {}", event.com);
        }

        std::string operator()(const StatChanged_s& event) const
        {
            return std::format("stat {} xp {} -> {}", event.stat, event.previous.xp, event.current.xp);
        }

        std::string operator()(const VarpChanged_s& event) const
        {
            return std::format("varp {} {} -> {}", event.varp, event.previous, event.value);
        }

        std::string operator()(const ModalChanged_s& event) const
        {
            return std::format("modals {} {} {}", event.mainModal, event.sideModal, event.chatModal);
        }

        std::string operator()(const RebootStarted_s& event) const
        {
            return std::format("reboot {}", event.ticks);
        }
    };

    std::vector<std::string> DescribeEventsAfter(const GameState_s& state, u64 sequence)
    {
        auto lines = std::vector<std::string>{};
        for (const auto* event : state.GetEventsAfter(sequence))
        {
            lines.push_back(std::visit(EventDescriber{}, event->data));
        }

        return lines;
    }

    template <typename TEvent>
    const TEvent& GetEvent(const GameState_s& state, u64 sequence)
    {
        const auto events = state.GetEventsAfter(sequence - 1);
        REQUIRE_FALSE(events.empty());
        REQUIRE(events[0]->sequence == sequence);
        REQUIRE(std::holds_alternative<TEvent>(events[0]->data));
        return std::get<TEvent>(events[0]->data);
    }

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
}

TEST_CASE("NPC_INFO reports removals, then additions, then hits", "[GameEvents]")
{
    auto state = Fixtures::PlacedState();
    state.npcs = {MakeNpc(100, 50, Offset(1, 0)), MakeNpc(101, 51, Offset(0, 1)), MakeNpc(102, 52, Offset(2, 2))};
    const auto before = state.eventCount;

    auto bits = BitWriter{};
    bits.Put(8, 2);
    bits.Put(1, 1).Put(2, 3);
    bits.Put(1, 1).Put(2, 0);
    bits.Put(14, 103).Put(11, 53).Put(5, 3).Put(5, 0).Put(1, 0).Put(1, 1);
    bits.Put(14, 16383);

    auto extended = Packet{};
    extended.P1(0x10);
    PutHit(extended, 4, 6);
    extended.P1(0x01 | 0x02);
    PutHit(extended, 2, 8);
    extended.P2(808);
    extended.P1(0);
    NpcInfoDecoder::Decode(Fixtures::Concat(bits.GetBytes(), Fixtures::ToBytes(extended)), state);

    CHECK(DescribeEventsAfter(state, before) == std::vector<std::string>{
        "npc removed 100",
        "npc removed 102",
        "npc added 103 type 53",
        "npc hit 101 damage 4",
        "npc hit 103 damage 2",
    });

    const auto& removed = GetEvent<NpcRemoved_s>(state, before + 1);
    CHECK(removed.npc.type == 50);
    CHECK(removed.npc.tile == Offset(1, 0));

    const auto& added = GetEvent<NpcAdded_s>(state, before + 3);
    CHECK(added.npc.tile == Offset(3, 0));
    CHECK(added.npc.animation.id == 808);

    const auto& hit = GetEvent<NpcHit_s>(state, before + 4);
    CHECK(hit.hit.health == 6);
    CHECK(hit.hit.maxHealth == 10);

    for (const auto* event : state.GetEventsAfter(before))
    {
        CHECK(event->tick == state.tick);
    }
}

TEST_CASE("PLAYER_INFO reports players, and hits on the local player apart from others", "[GameEvents]")
{
    auto state = Fixtures::PlacedState();
    state.players = {MakePlayer(7, Offset(1, 1)), MakePlayer(8, Offset(2, 2))};
    const auto before = state.eventCount;
    auto decoder = PlayerInfoDecoder{};

    auto bits = BitWriter{};
    bits.Put(1, 1).Put(2, 0);
    bits.Put(8, 2);
    bits.Put(1, 1).Put(2, 3);
    bits.Put(1, 1).Put(2, 0);
    bits.Put(11, 9).Put(5, 1).Put(5, 1).Put(1, 0).Put(1, 1);
    bits.Put(11, 2047);

    const auto appearance = Fixtures::Appearance("zezima");
    auto extended = Packet{};
    extended.P1(0x10);
    PutHit(extended, 5, 5);
    extended.P1(0x80);
    extended.P1(0x04);
    PutHit(extended, 2, 8);
    extended.P1(0x01);
    extended.P1(static_cast<s32>(appearance.size()));
    extended.PData(appearance);
    decoder.Decode(Fixtures::Concat(bits.GetBytes(), Fixtures::ToBytes(extended)), state);

    CHECK(DescribeEventsAfter(state, before) == std::vector<std::string>{
        "player removed 7",
        "player added 9 Zezima",
        "local hit damage 5",
        "player hit 8 damage 2",
    });

    CHECK(GetEvent<PlayerRemoved_s>(state, before + 1).player.tile == Offset(1, 1));
    CHECK(GetEvent<PlayerAdded_s>(state, before + 2).player.tile == Offset(1, 1));
}

TEST_CASE("Zone packets report ground items and scenery, but not resets", "[GameEvents]")
{
    auto fixture = DecoderFixture{};
    auto& state = fixture.state;
    const auto zone = Fixtures::Zone(HOME_ZONE_LOCAL, HOME_ZONE_LOCAL);
    const auto before = state.eventCount;

    fixture.Decode(ServerProt_e::UpdateZonePartialFollows, zone);
    fixture.Decode(ServerProt_e::ObjAdd, Fixtures::ObjAdd(ToPos(2, 3), 995, 50));

    auto count = Packet{};
    count.P1(ToPos(2, 3));
    count.P2(995);
    count.P2(50);
    count.P2(75);
    fixture.Decode(ServerProt_e::ObjCount, count);

    auto revealToOther = Packet{};
    revealToOther.P1(ToPos(4, 4));
    revealToOther.P2(526);
    revealToOther.P2(1);
    revealToOther.P2(Fixtures::PID + 1);
    fixture.Decode(ServerProt_e::ObjReveal, revealToOther);

    auto revealToSelf = Packet{};
    revealToSelf.P1(ToPos(5, 5));
    revealToSelf.P2(526);
    revealToSelf.P2(1);
    revealToSelf.P2(Fixtures::PID);
    fixture.Decode(ServerProt_e::ObjReveal, revealToSelf);

    auto del = Packet{};
    del.P1(ToPos(2, 3));
    del.P2(995 | 0x8000);
    fixture.Decode(ServerProt_e::ObjDel, del);

    auto delUnknown = Packet{};
    delUnknown.P1(ToPos(6, 6));
    delUnknown.P2(1);
    fixture.Decode(ServerProt_e::ObjDel, delUnknown);

    auto addLoc = Packet{};
    addLoc.P1(ToPos(1, 1));
    addLoc.P1((10 << 2) | 1);
    addLoc.P2(1276);
    fixture.Decode(ServerProt_e::LocAddChange, addLoc);

    auto delLoc = Packet{};
    delLoc.P1(ToPos(1, 1));
    delLoc.P1((10 << 2) | 1);
    fixture.Decode(ServerProt_e::LocDel, delLoc);

    CHECK(DescribeEventsAfter(state, before) == std::vector<std::string>{
        "item added 995 x50",
        "item count 995 50 -> 75",
        "item added 526 x1",
        "item removed 995 x75",
        "loc 1276",
        "loc -1",
    });

    CHECK(GetEvent<GroundItemAdded_s>(state, before + 1).item.tile == ZoneOffset(2, 3));
    CHECK(GetEvent<LocChanged_s>(state, before + 5).change.tile == ZoneOffset(1, 1));

    const auto afterChanges = state.eventCount;
    fixture.Decode(ServerProt_e::UpdateZoneFullFollows, zone);
    fixture.Decode(ServerProt_e::RebuildNormal, Fixtures::Rebuild());
    CHECK(state.groundItems.empty());
    CHECK(state.eventCount == afterChanges);
}

TEST_CASE("Server packets report inventories, stats, varps, modals and reboots", "[GameEvents]")
{
    auto fixture = DecoderFixture{};
    auto& state = fixture.state;
    const auto before = state.eventCount;

    auto full = Packet{};
    full.P2(INVENTORY);
    full.P2(1);
    full.P2(1512);
    full.P1(3);
    fixture.Decode(ServerProt_e::UpdateInvFull, full);

    auto partial = Packet{};
    partial.P2(INVENTORY);
    partial.P1(0);
    partial.P2(0);
    partial.P1(0);
    fixture.Decode(ServerProt_e::UpdateInvPartial, partial);

    auto stop = Packet{};
    stop.P2(INVENTORY);
    fixture.Decode(ServerProt_e::UpdateInvStopTransmit, stop);

    auto stat = Packet{};
    stat.P1(3);
    stat.P4(1154);
    stat.P1(10);
    fixture.Decode(ServerProt_e::UpdateStat, stat);

    auto statAgain = Packet{};
    statAgain.P1(3);
    statAgain.P4(1300);
    statAgain.P1(9);
    fixture.Decode(ServerProt_e::UpdateStat, statAgain);

    auto varpSmall = Packet{};
    varpSmall.P2(173);
    varpSmall.P1(1);
    fixture.Decode(ServerProt_e::VarpSmall, varpSmall);

    auto varpLarge = Packet{};
    varpLarge.P2(173);
    varpLarge.P4(70000);
    fixture.Decode(ServerProt_e::VarpLarge, varpLarge);

    auto openMain = Packet{};
    openMain.P2(5292);
    fixture.Decode(ServerProt_e::IfOpenMain, openMain);
    fixture.Decode(ServerProt_e::PCountDialog);
    fixture.Decode(ServerProt_e::IfClose);

    auto openChat = Packet{};
    openChat.P2(356);
    fixture.Decode(ServerProt_e::IfOpenChat, openChat);

    auto reboot = Packet{};
    reboot.P2(500);
    fixture.Decode(ServerProt_e::UpdateRebootTimer, reboot);

    CHECK(DescribeEventsAfter(state, before) == std::vector<std::string>{
        "inventory 3214",
        "inventory 3214",
        "inventory 3214",
        "stat 3 xp 0 -> 1154",
        "stat 3 xp 1154 -> 1300",
        "varp 173 0 -> 1",
        "varp 173 1 -> 70000",
        "modals 5292 -1 -1",
        "modals 5292 -1 -1",
        "modals -1 -1 -1",
        "modals -1 -1 356",
        "reboot 500",
    });

    const auto& levelDrop = GetEvent<StatChanged_s>(state, before + 5);
    CHECK(levelDrop.previous.level == 10);
    CHECK(levelDrop.current.level == 9);
    CHECK(levelDrop.current.baseLevel == 10);
}

TEST_CASE("The event log keeps the newest events, numbered in arrival order", "[GameEvents]")
{
    auto fixture = DecoderFixture{};
    auto& state = fixture.state;
    const auto before = state.eventCount;
    constexpr auto EXTRA = std::size_t{76};
    constexpr auto TOTAL = GameState_s::MAX_EVENTS + EXTRA;

    for (std::size_t i = 0; i < TOTAL; ++i)
    {
        auto varp = Packet{};
        varp.P2(static_cast<s32>(i % 100));
        varp.P1(static_cast<s32>(i % 50));
        fixture.Decode(ServerProt_e::VarpSmall, varp);
    }

    CHECK(state.eventCount == before + TOTAL);
    REQUIRE(state.events.size() == GameState_s::MAX_EVENTS);
    CHECK(state.events.front().sequence == before + EXTRA + 1);
    CHECK(state.events.back().sequence == state.eventCount);

    const auto recent = state.GetEventsAfter(state.eventCount - 10);
    REQUIRE(recent.size() == 10);
    CHECK(recent.front()->sequence == state.eventCount - 9);

    CHECK(state.GetEventsAfter(0).size() == GameState_s::MAX_EVENTS);
    CHECK(state.GetEventsAfter(state.eventCount).empty());
}
