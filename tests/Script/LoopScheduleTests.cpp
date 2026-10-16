#include "pch.hpp"

#include "Game/State/GameState_s.hpp"
#include "Script/Host/LoopSchedule.hpp"

#include <catch2/catch_test_macros.hpp>

namespace
{
    using Clock = LoopSchedule::Clock;
}

TEST_CASE("LoopSchedule waits a number of milliseconds", "[LoopSchedule]")
{
    const auto now = Clock::now();
    auto state = GameState_s{};
    auto schedule = LoopSchedule{};

    schedule.Schedule(now, LoopSchedule::WAIT_MS, 600, state);
    CHECK_FALSE(schedule.IsDue(now + 599ms, state));
    CHECK(schedule.IsDue(now + 600ms, state));
    CHECK(schedule.GetNextTime() == now + 600ms);
}

TEST_CASE("LoopSchedule waits for the next update, with or without a timeout", "[LoopSchedule]")
{
    const auto now = Clock::now();
    auto state = GameState_s{.updateCount = 10};
    auto schedule = LoopSchedule{};

    SECTION("without a timeout, only an update ends the wait, and there's no time to wake at")
    {
        schedule.Schedule(now, LoopSchedule::WAIT_UPDATE, -1, state);
        CHECK_FALSE(schedule.IsDue(now + 1h, state));
        CHECK_FALSE(schedule.GetNextTime().has_value());

        ++state.updateCount;
        CHECK(schedule.IsDue(now, state));
    }

    SECTION("with a timeout, whichever comes first ends it")
    {
        schedule.Schedule(now, LoopSchedule::WAIT_UPDATE, 300, state);
        CHECK_FALSE(schedule.IsDue(now + 299ms, state));
        CHECK(schedule.IsDue(now + 300ms, state));
        CHECK(schedule.GetNextTime() == now + 300ms);
    }
}

TEST_CASE("LoopSchedule waits for the tick to reach a number", "[LoopSchedule]")
{
    const auto now = Clock::now();
    auto state = GameState_s{.tick = 40};
    auto schedule = LoopSchedule{};

    schedule.Schedule(now, "ticks", 2, state);
    CHECK_FALSE(schedule.GetNextTime().has_value());
    state.tick = 41;
    CHECK_FALSE(schedule.IsDue(now, state));
    state.tick = 42;
    CHECK(schedule.IsDue(now, state));
}

TEST_CASE("LoopSchedule runs at a time it's given", "[LoopSchedule]")
{
    const auto now = Clock::now();
    const auto state = GameState_s{};
    auto schedule = LoopSchedule{};

    schedule.Schedule(now, "ticks", 5, state);
    schedule.RunAt(now);
    CHECK(schedule.IsDue(now, state));
    CHECK(schedule.GetNextTime() == now);
}
