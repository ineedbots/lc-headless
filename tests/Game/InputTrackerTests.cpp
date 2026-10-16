#include "pch.hpp"

#include "Game/InputTracker.hpp"

#include <catch2/catch_test_macros.hpp>

namespace
{
    using Clock = InputTracker::Clock;

    constexpr auto CLICK_SIZE = std::size_t{12};

    struct Event_s
    {
        u8 code = 0;
        u8 delta = 0;
        std::optional<std::pair<s32, s32>> position;
    };

    // Reads a report as the 225 engine would store it: each event's code, delta, and position if it has one.
    std::vector<Event_s> ReadEvents(std::span<const u8> report)
    {
        auto events = std::vector<Event_s>{};
        for (auto i = std::size_t{0}; i < report.size();)
        {
            auto event = Event_s{.code = report[i], .delta = report[i + 1]};
            if (event.code == InputTracker::LEFT_RELEASE)
            {
                i += 2;
                events.push_back(event);
                continue;
            }

            REQUIRE(i + 5 <= report.size());
            const auto packed = (s32{report[i + 2]} << 16) | (s32{report[i + 3]} << 8) | s32{report[i + 4]};
            event.position = std::pair{packed & 0x3FF, packed >> 10};
            events.push_back(event);
            i += 5;
        }

        return events;
    }

    void CheckInGameView(const Event_s& event)
    {
        REQUIRE(event.position.has_value());

        const auto [x, y] = *event.position;
        CHECK(x >= InputTracker::VIEW_X);
        CHECK(x < InputTracker::VIEW_X + InputTracker::VIEW_WIDTH);
        CHECK(y >= InputTracker::VIEW_Y);
        CHECK(y < InputTracker::VIEW_Y + InputTracker::VIEW_HEIGHT);
    }
}

TEST_CASE("InputTracker records nothing until tracking starts", "[InputTracker]")
{
    auto tracker = InputTracker{};
    CHECK_FALSE(tracker.IsActive());

    tracker.RecordClick(Clock::now());
    CHECK(tracker.TakeFullReports().empty());
    CHECK(tracker.Finish(Clock::now()).empty());
}

TEST_CASE("InputTracker records a click as a move, a press and a release", "[InputTracker]")
{
    const auto start = Clock::time_point{};
    auto tracker = InputTracker{};
    tracker.Start(start);
    REQUIRE(tracker.IsActive());

    tracker.RecordClick(start + 300ms);
    const auto reports = tracker.Finish(start + 10s);
    CHECK_FALSE(tracker.IsActive());

    REQUIRE(reports.size() == 1);
    REQUIRE(reports[0].size() == CLICK_SIZE);

    const auto events = ReadEvents(reports[0]);
    REQUIRE(events.size() == 3);
    CHECK(events[0].code == InputTracker::ABSOLUTE_MOVE);
    CHECK(events[0].delta == 30);
    CheckInGameView(events[0]);
    CHECK(events[1].code == InputTracker::LEFT_PRESS);
    CHECK(events[1].position == events[0].position);
    CHECK((events[1].delta >= 4 && events[1].delta <= 12));
    CHECK(events[2].code == InputTracker::LEFT_RELEASE);
    CHECK((events[2].delta >= 6 && events[2].delta <= 14));

    SECTION("a delta is capped, and never counts back past an event placed ahead of the clock")
    {
        tracker.Start(start);
        tracker.RecordClick(start + 5s);
        tracker.RecordClick(start + 5s);

        const auto later = ReadEvents(tracker.Finish(start + 6s)[0]);
        REQUIRE(later.size() == 6);
        CHECK(later[0].delta == InputTracker::MAX_DELTA);
        CHECK(later[3].delta == 0);
    }
}

TEST_CASE("InputTracker reports one move for a window with no actions", "[InputTracker]")
{
    const auto start = Clock::time_point{};
    auto tracker = InputTracker{};
    tracker.Start(start);

    const auto reports = tracker.Finish(start + 1s);
    REQUIRE(reports.size() == 1);

    const auto events = ReadEvents(reports[0]);
    REQUIRE(events.size() == 1);
    CHECK(events[0].code == InputTracker::ABSOLUTE_MOVE);
    CHECK(events[0].delta == 100);
    CheckInGameView(events[0]);
}

TEST_CASE("InputTracker sets a report aside before it reaches 500 bytes", "[InputTracker]")
{
    const auto start = Clock::time_point{};
    auto tracker = InputTracker{};
    tracker.Start(start);

    // 41 clicks fill 492 bytes, so the 42nd's press is the first event that doesn't fit.
    for (auto click = 0; click < 41; ++click)
    {
        tracker.RecordClick(start + click * 1s);
    }

    CHECK(tracker.TakeFullReports().empty());

    tracker.RecordClick(start + 41s);
    const auto full = tracker.TakeFullReports();
    REQUIRE(full.size() == 1);
    CHECK(full[0].size() == 41 * CLICK_SIZE + 5);
    CHECK(full[0].size() < InputTracker::MAX_REPORT_SIZE);
    CHECK(ReadEvents(full[0]).back().code == InputTracker::ABSOLUTE_MOVE);

    const auto rest = tracker.Finish(start + 50s);
    REQUIRE(rest.size() == 1);

    const auto events = ReadEvents(rest[0]);
    REQUIRE(events.size() == 2);
    CHECK(events[0].code == InputTracker::LEFT_PRESS);
    CHECK(events[1].code == InputTracker::LEFT_RELEASE);
}
