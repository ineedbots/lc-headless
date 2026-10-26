#include "pch.hpp"

#include "Config/Config_s.hpp"
#include "Game/Net/RetrySchedule.hpp"

#include <catch2/catch_test_macros.hpp>

namespace
{
    using Clock = RetrySchedule::Clock;
}

TEST_CASE("RetrySchedule doubles the delay after each failed attempt up to the cap", "[RetrySchedule]")
{
    auto schedule = RetrySchedule{10, 2s, 30s};
    auto delays = std::vector<std::chrono::milliseconds>{};
    for (auto i = 0; i < 6; ++i)
    {
        schedule.BeginAttempt();
        delays.push_back(schedule.GetDelay());
    }

    CHECK(delays == std::vector<std::chrono::milliseconds>{2s, 4s, 8s, 16s, 30s, 30s});
}

TEST_CASE("RetrySchedule caps a first delay that is over the cap", "[RetrySchedule]")
{
    auto schedule = RetrySchedule{3, 10s, 5s};
    schedule.BeginAttempt();
    CHECK(schedule.GetDelay() == 5s);
}

TEST_CASE("RetrySchedule counts attempts up to the maximum", "[RetrySchedule]")
{
    auto schedule = RetrySchedule{2, 1s, 1s};
    CHECK(schedule.GetMaxAttempts() == 2);
    CHECK(schedule.GetAttempt() == 0);
    CHECK(schedule.HasAttemptsLeft());

    schedule.BeginAttempt();
    CHECK(schedule.GetAttempt() == 1);
    CHECK(schedule.HasAttemptsLeft());

    schedule.BeginAttempt();
    CHECK(schedule.GetAttempt() == 2);
    CHECK_FALSE(schedule.HasAttemptsLeft());
}

TEST_CASE("RetrySchedule never exhausts the unlimited attempt setting", "[RetrySchedule]")
{
    auto schedule = RetrySchedule{ScriptingSettings_s::MAX_CONNECT_ATTEMPTS, 2s, 30s};
    for (auto i = 0; i < ScriptingSettings_s::MAX_CONNECT_ATTEMPTS * 3; ++i)
    {
        schedule.BeginAttempt();
        CHECK(schedule.HasAttemptsLeft());
    }

    CHECK(schedule.GetDelay() == 30s);
    schedule.Reset();
    CHECK(schedule.GetAttempt() == 0);
    CHECK(schedule.HasAttemptsLeft());
    CHECK(schedule.GetDelay() == 2s);
}

TEST_CASE("RetrySchedule with zero attempts never schedules a retry", "[RetrySchedule]")
{
    auto schedule = RetrySchedule{0, 2s, 30s};
    CHECK_FALSE(schedule.HasAttemptsLeft());
    schedule.BeginAttempt();
    CHECK_FALSE(schedule.HasAttemptsLeft());
}

TEST_CASE("RetrySchedule holds the scheduled attempt until it begins", "[RetrySchedule]")
{
    auto schedule = RetrySchedule{3, 1s, 1s};
    CHECK_FALSE(schedule.GetScheduled().has_value());

    const auto time = Clock::now() + 1s;
    schedule.ScheduleAt(time);
    CHECK(schedule.GetScheduled() == time);

    schedule.BeginAttempt();
    CHECK_FALSE(schedule.GetScheduled().has_value());
}

TEST_CASE("RetrySchedule starts over on Reset", "[RetrySchedule]")
{
    auto schedule = RetrySchedule{3, 1s, 8s};
    schedule.BeginAttempt();
    schedule.BeginAttempt();
    schedule.ScheduleAt(Clock::now());

    schedule.Reset();
    CHECK(schedule.GetAttempt() == 0);
    CHECK_FALSE(schedule.GetScheduled().has_value());
    CHECK(schedule.GetDelay() == 1s);
}
