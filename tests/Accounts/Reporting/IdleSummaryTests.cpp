#include "pch.hpp"
#include "../../Support/LogCapture.hpp"

#include "Accounts/Reporting/IdleSummary.hpp"
#include "Accounts/Reporting/Type/IdleSummaryNpc_s.hpp"
#include "Accounts/Reporting/Type/IdleSummary_s.hpp"
#include "Console/Type/LogLevel_e.hpp"
#include "Game/State/Type/GameState_s.hpp"
#include "Game/State/Type/Npc_s.hpp"
#include "Game/State/Type/Stat_e.hpp"
#include "Game/State/Type/Stat_s.hpp"

#include <catch2/catch_test_macros.hpp>

namespace
{
    Npc_s MakeNpc(u16 index, u16 type, s32 x)
    {
        auto npc = Npc_s{};
        npc.index = index;
        npc.type = type;
        npc.tile = {.x = x, .z = 3200};
        return npc;
    }
}

TEST_CASE("IdleSummary logs where the player is and the nearest NPCs first", "[IdleSummary]")
{
    auto capture = LogCapture{LogLevel_e::Info};
    auto state = GameState_s{.tick = 7, .pid = 5};
    state.localPlayer.tile = {.x = 3200, .z = 3200};
    state.stats[static_cast<std::size_t>(Stat_e::Hitpoints)] = Stat_s{.level = 8, .baseLevel = 10};
    state.npcs = {MakeNpc(1, 41, 3210), MakeNpc(2, 81, 3202)};

    IdleSummary::Log(*capture.GetLogger(), IdleSummary::Capture(state));

    const auto entries = capture.GetEntries();
    REQUIRE(entries.size() == 4);
    CHECK(entries[0].message.starts_with("Tick 7: player 5 at (3200, 3200, 0), hitpoints 8/10"));
    CHECK(entries[1].message.starts_with("In view: 0 players, 2 NPCs"));
    CHECK(entries[2].message == "Nearest NPCs: #2 type 81 at 2 tiles, #1 type 41 at 10 tiles");
    CHECK(entries[3].message.starts_with("Interfaces: main "));
}

TEST_CASE("IdleSummary says when no NPC is in view", "[IdleSummary]")
{
    auto capture = LogCapture{LogLevel_e::Info};
    IdleSummary::Log(*capture.GetLogger(), IdleSummary::Capture(GameState_s{}));
    CHECK(capture.GetEntries()[2].message == "Nearest NPCs: none");
}

TEST_CASE("IdleSummary captures owned values and only the five nearest NPCs", "[IdleSummary]")
{
    auto state = GameState_s{.tick = 7, .pid = 5};
    state.localPlayer.tile = {.x = 3200, .z = 3200, .level = 1};
    state.stats[static_cast<std::size_t>(Stat_e::Hitpoints)] = Stat_s{.level = 8, .baseLevel = 10};
    state.runEnergy = 75;
    state.runWeight = -2;

    for (u16 i = 7; i > 0; --i)
    {
        state.npcs.push_back(MakeNpc(i, 81, 3200 + i));
    }

    const auto summary = IdleSummary::Capture(state);
    state.npcs.clear();
    state.localPlayer.tile.x = 0;
    CHECK(summary.tick == 7);
    CHECK(summary.pid == 5);
    CHECK(summary.tile.x == 3200);
    CHECK(summary.tile.level == 1);
    CHECK(summary.hitpoints == 8);
    CHECK(summary.baseHitpoints == 10);
    CHECK(summary.runEnergy == 75);
    CHECK(summary.weight == -2);
    CHECK(summary.npcs == 7);
    REQUIRE(summary.nearestNpcs.size() == IdleSummary_s::MAX_NEAREST_NPCS);

    for (std::size_t i = 0; i < summary.nearestNpcs.size(); ++i)
    {
        CHECK(summary.nearestNpcs[i].index == i + 1);
        CHECK(summary.nearestNpcs[i].type == 81);
        CHECK(summary.nearestNpcs[i].distance == i + 1);
    }
}
