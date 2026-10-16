#include "pch.hpp"

#include "Console/LogEntry_s.hpp"
#include "Console/LogFormatter.hpp"
#include "Console/LogLevel_e.hpp"

#include <catch2/catch_test_macros.hpp>

namespace
{
    std::chrono::system_clock::time_point GetSampleTime()
    {
        return std::chrono::sys_days{2026y / std::chrono::October / 5} + 18h + 34min + 12s + 345ms;
    }

    LogEntry_s MakeEntry(LogLevel_e level, std::chrono::system_clock::time_point time, std::optional<std::source_location> location = std::nullopt)
    {
        return {.level = level, .time = time, .location = location, .message = "hello"};
    }
}

TEST_CASE("LogFormatter::FormatLine", "[LogFormatter]")
{
    const auto time = GetSampleTime();

    CHECK(LogFormatter::FormatLine(MakeEntry(LogLevel_e::Info, time)) == "2026-10-05T18:34:12.345Z INFO    hello");
    CHECK(LogFormatter::FormatLine(MakeEntry(LogLevel_e::Verbose, time)) == "2026-10-05T18:34:12.345Z VERBOSE hello");
    CHECK(LogFormatter::FormatLine(MakeEntry(LogLevel_e::Warning, time)) == "2026-10-05T18:34:12.345Z WARNING hello");
    CHECK(LogFormatter::FormatLine(MakeEntry(LogLevel_e::Error, time)) == "2026-10-05T18:34:12.345Z ERROR   hello");

    const auto wholeSecond = std::chrono::sys_days{2026y / std::chrono::January / 2} + 3h + 4min + 5s;
    CHECK(LogFormatter::FormatLine(MakeEntry(LogLevel_e::Info, wholeSecond)) == "2026-01-02T03:04:05.000Z INFO    hello");

    const auto almostNextMillisecond = std::chrono::sys_days{2026y / std::chrono::October / 5} + 18h + 34min + 12s + 345999us;
    CHECK(LogFormatter::FormatLine(MakeEntry(LogLevel_e::Info, almostNextMillisecond)) == "2026-10-05T18:34:12.345Z INFO    hello");

    const auto location = std::source_location::current();
    const auto expected = std::format("2026-10-05T18:34:12.345Z INFO    hello [LogFormatterTests.cpp:{}]", location.line());
    CHECK(LogFormatter::FormatLine(MakeEntry(LogLevel_e::Info, time, location)) == expected);

    auto named = MakeEntry(LogLevel_e::Warning, time);
    named.source = "bot1";
    CHECK(LogFormatter::FormatLine(named) == "2026-10-05T18:34:12.345Z WARNING [bot1] hello");
}

TEST_CASE("LogFormatter::FormatColoredLine colors each level but info", "[LogFormatter]")
{
    const auto time = GetSampleTime();

    CHECK(LogFormatter::FormatColoredLine(MakeEntry(LogLevel_e::Verbose, time)) == "\x1B[36m2026-10-05T18:34:12.345Z VERBOSE hello\x1B[0m");
    CHECK(LogFormatter::FormatColoredLine(MakeEntry(LogLevel_e::Info, time)) == "2026-10-05T18:34:12.345Z INFO    hello");
    CHECK(LogFormatter::FormatColoredLine(MakeEntry(LogLevel_e::Warning, time)) == "\x1B[33m2026-10-05T18:34:12.345Z WARNING hello\x1B[0m");
    CHECK(LogFormatter::FormatColoredLine(MakeEntry(LogLevel_e::Error, time)) == "\x1B[31m2026-10-05T18:34:12.345Z ERROR   hello\x1B[0m");
}
