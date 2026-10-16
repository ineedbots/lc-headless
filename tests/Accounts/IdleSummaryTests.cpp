#include "pch.hpp"
#include "../Support/LogCapture.hpp"

#include "Accounts/IdleSummary.hpp"
#include "Console/LogLevel_e.hpp"
#include "Game/State/GameState_s.hpp"
#include "Game/State/Npc_s.hpp"
#include "Game/State/Stat_e.hpp"
#include "Game/State/Stat_s.hpp"

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

    IdleSummary::Log(*capture.GetLogger(), state);

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
    IdleSummary::Log(*capture.GetLogger(), GameState_s{});
    CHECK(capture.GetEntries()[2].message == "Nearest NPCs: none");
}
