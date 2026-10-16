#include "pch.hpp"
#include "../Support/Cache/TestCache.hpp"
#include "../Support/Game/QueryWorld.hpp"

#include "Game/Query/PlayerQuery.hpp"
#include "Game/State/EntityStatus.hpp"
#include "Game/State/GameState_s.hpp"
#include "Game/State/Stat_s.hpp"

#include <catch2/catch_test_macros.hpp>

TEST_CASE("PlayerQuery reads stats, modals and run mode", "[PlayerQuery]")
{
    auto world = QueryWorld{};
    auto& state = world.state;
    const auto query = PlayerQuery{state, *world.cache};

    state.stats[3] = Stat_s{.xp = 1154, .level = 7, .baseLevel = 10};
    CHECK(query.GetStat(3).level == 7);
    CHECK_THROWS_AS(query.GetStat(-1), std::invalid_argument);
    CHECK_THROWS_AS(query.GetStat(static_cast<s32>(GameState_s::STAT_COUNT)), std::invalid_argument);

    state.interfaces.mainModal = 5292;
    CHECK(query.IsInterfaceOpen(5292));
    CHECK_FALSE(query.IsInterfaceOpen(-1));

    CHECK_FALSE(query.IsRunning());
    state.varps[TestCache::RUN_VARP] = 1;
    CHECK(query.IsRunning());
}

TEST_CASE("PlayerQuery counts a walk the client asked for as moving", "[PlayerQuery]")
{
    auto world = QueryWorld{};
    auto& state = world.state;
    const auto query = PlayerQuery{state, *world.cache};

    CHECK_FALSE(query.IsMoving());
    state.walkDestination = QueryWorld::Offset(0, 5);
    CHECK(query.IsMoving());

    CHECK_FALSE(query.InCombat());
    state.localPlayer.hits.push_back({.damage = 1, .tick = state.tick - EntityStatus::COMBAT_TICKS});
    CHECK(query.InCombat());
}
