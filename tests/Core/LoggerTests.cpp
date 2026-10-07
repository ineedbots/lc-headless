#include "pch.hpp"
#include "../LogCapture.hpp"

#include "Core/Logger.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/catch_tostring.hpp>
#include <catch2/generators/catch_generators.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>

namespace
{
    constexpr auto ALL_LEVELS = std::array{LogLevel_e::Verbose, LogLevel_e::Info, LogLevel_e::Warning, LogLevel_e::Error};

    struct CountingArg_s
    {
        int* formatCount;
    };

    struct ThrowingArg_s
    {
    };

    struct ExpectedLog_s
    {
        LogLevel_e level;
        std::string message;
    };

    void LogWithLevelFunction(Logger& logger, LogLevel_e level)
    {
        switch (level)
        {
        case LogLevel_e::Verbose:
            logger.Verbose("message");
            return;
        case LogLevel_e::Info:
            logger.Info("message");
            return;
        case LogLevel_e::Warning:
            logger.Warning("message");
            return;
        case LogLevel_e::Error:
            logger.Error("message");
            return;
        }
    }

    std::vector<LogLevel_e> GetLevels(const std::vector<CapturedLog_s>& entries)
    {
        auto levels = std::vector<LogLevel_e>{};
        for (const auto& entry : entries)
        {
            levels.push_back(entry.level);
        }

        return levels;
    }

    std::vector<LogLevel_e> GetLevelsAtOrAbove(LogLevel_e threshold)
    {
        auto levels = std::vector<LogLevel_e>{};
        for (const auto level : ALL_LEVELS)
        {
            if (level >= threshold)
            {
                levels.push_back(level);
            }
        }

        return levels;
    }

    std::chrono::system_clock::time_point GetSampleTime()
    {
        return std::chrono::sys_days{2026y / std::chrono::October / 5} + 18h + 34min + 12s + 345ms;
    }

    LogEntry_s MakeEntry(LogLevel_e level, std::chrono::system_clock::time_point time, std::optional<std::source_location> location = std::nullopt)
    {
        return {.level = level, .time = time, .location = location, .message = "hello"};
    }

    int ParseInt(std::string_view text)
    {
        auto value = -1;
        const auto result = std::from_chars(text.data(), text.data() + text.size(), value);
        if (result.ec != std::errc{} || result.ptr != text.data() + text.size())
        {
            return -1;
        }

        return value;
    }

    std::pair<int, int> ParseThreadMessage(std::string_view message)
    {
        const auto separator = message.find(' ');
        if (separator == std::string_view::npos)
        {
            return {-1, -1};
        }

        return {ParseInt(message.substr(0, separator)), ParseInt(message.substr(separator + 1))};
    }
}

template <>
struct std::formatter<CountingArg_s>
{
    constexpr auto parse(std::format_parse_context& context)
    {
        return context.begin();
    }

    auto format(const CountingArg_s& arg, std::format_context& context) const
    {
        ++*arg.formatCount;
        return std::format_to(context.out(), "counted");
    }
};

template <>
struct std::formatter<ThrowingArg_s>
{
    constexpr auto parse(std::format_parse_context& context)
    {
        return context.begin();
    }

    std::format_context::iterator format(const ThrowingArg_s&, std::format_context&) const
    {
        throw std::runtime_error{"formatter failed"};
    }
};

CATCH_REGISTER_ENUM(LogLevel_e, LogLevel_e::Verbose, LogLevel_e::Info, LogLevel_e::Warning, LogLevel_e::Error)

static_assert(noexcept(std::declval<Logger&>().Verbose("x")));
static_assert(noexcept(std::declval<Logger&>().Info("x")));
static_assert(noexcept(std::declval<Logger&>().Warning("x")));
static_assert(noexcept(std::declval<Logger&>().Error("x")));
static_assert(noexcept(std::declval<Logger&>().Log(LogLevel_e::Error, "x")));

TEST_CASE("Logger writes messages at or above its threshold", "[Logger]")
{
    const auto threshold = GENERATE(LogLevel_e::Verbose, LogLevel_e::Info, LogLevel_e::Warning, LogLevel_e::Error);
    auto capture = LogCapture{threshold};
    const auto logger = capture.GetLogger();

    SECTION("through the function for each level")
    {
        for (const auto level : ALL_LEVELS)
        {
            LogWithLevelFunction(*logger, level);
        }

        CHECK(GetLevels(capture.GetEntries()) == GetLevelsAtOrAbove(threshold));
    }

    SECTION("through Log")
    {
        for (const auto level : ALL_LEVELS)
        {
            logger->Log(level, "message");
        }

        CHECK(GetLevels(capture.GetEntries()) == GetLevelsAtOrAbove(threshold));
    }

    SECTION("as IsEnabled reports")
    {
        CHECK(logger->GetLevel() == threshold);
        for (const auto level : ALL_LEVELS)
        {
            CHECK(logger->IsEnabled(level) == (level >= threshold));
        }
    }
}

TEST_CASE("Logger SetLevel changes the threshold", "[Logger]")
{
    auto capture = LogCapture{LogLevel_e::Verbose};
    const auto logger = capture.GetLogger();

    logger->SetLevel(LogLevel_e::Warning);
    logger->Info("filtered");
    logger->Warning("kept");

    CHECK(logger->GetLevel() == LogLevel_e::Warning);
    CHECK_FALSE(logger->IsEnabled(LogLevel_e::Info));
    const auto entries = capture.GetEntries();
    REQUIRE(entries.size() == 1);
    CHECK(entries[0].message == "kept");
}

TEST_CASE("A default Logger writes to the console at Info", "[Logger]")
{
    auto logger = Logger{};

    CHECK(logger.GetLevel() == LogLevel_e::Info);
    CHECK(static_cast<bool>(logger.SetSink(nullptr)));
}

TEST_CASE("Logger doesn't format filtered messages", "[Logger]")
{
    auto capture = LogCapture{LogLevel_e::Info};
    const auto logger = capture.GetLogger();
    auto formatCount = 0;

    logger->Verbose("{}", CountingArg_s{&formatCount});
    CHECK(formatCount == 0);

    logger->Info("{}", CountingArg_s{&formatCount});
    CHECK(formatCount == 1);
}

TEST_CASE("Logger formats messages", "[Logger]")
{
    auto capture = LogCapture{};
    const auto logger = capture.GetLogger();
    const auto longText = std::string(100'000, 'a');

    logger->Info("plain");
    logger->Info("{} + {} = {}", 1, 2, 3);
    logger->Error("{{}} {}", "x");
    logger->Verbose("{:>4}", 7);
    logger->Warning("{} left", 3);
    logger->Info("{}", "{}");
    logger->Info("{}", longText);
    logger->Log(LogLevel_e::Error, "{}", 5);

    const auto expected = std::vector<ExpectedLog_s>{
        {LogLevel_e::Info, "plain"},
        {LogLevel_e::Info, "1 + 2 = 3"},
        {LogLevel_e::Error, "{} x"},
        {LogLevel_e::Verbose, "   7"},
        {LogLevel_e::Warning, "3 left"},
        {LogLevel_e::Info, "{}"},
        {LogLevel_e::Info, longText},
        {LogLevel_e::Error, "5"},
    };

    const auto entries = capture.GetEntries();
    REQUIRE(entries.size() == expected.size());
    for (std::size_t i = 0; i < entries.size(); ++i)
    {
        CAPTURE(i);
        CHECK(entries[i].level == expected[i].level);
        CHECK(entries[i].message == expected[i].message);
    }
}

TEST_CASE("Logger stamps entries with the time of the call", "[Logger]")
{
    auto capture = LogCapture{};
    const auto logger = capture.GetLogger();

    const auto before = std::chrono::system_clock::now();
    logger->Info("x");
    const auto after = std::chrono::system_clock::now();

    const auto entries = capture.GetEntries();
    REQUIRE(entries.size() == 1);
    CHECK(entries[0].time >= before);
    CHECK(entries[0].time <= after);
}

TEST_CASE("Logger records the call site in Debug builds only", "[Logger]")
{
    auto capture = LogCapture{};
    const auto logger = capture.GetLogger();

    const auto infoLine = std::source_location::current().line() + 1;
    logger->Info("x");
    const auto warningLine = std::source_location::current().line() + 1;
    logger->Warning("{}", 1);
    const auto logLine = std::source_location::current().line() + 1;
    logger->Log(LogLevel_e::Error, "x");

    const auto expectedLines = std::array{infoLine, warningLine, logLine};
    const auto entries = capture.GetEntries();
    REQUIRE(entries.size() == expectedLines.size());
    for (std::size_t i = 0; i < entries.size(); ++i)
    {
        CAPTURE(i);
#ifdef NDEBUG
        CHECK_FALSE(entries[i].location.has_value());
#else
        REQUIRE(entries[i].location.has_value());
        CHECK_THAT(std::string{entries[i].location->file_name()}, Catch::Matchers::EndsWith("LoggerTests.cpp"));
        CHECK(entries[i].location->line() == expectedLines[i]);
#endif
    }
}

TEST_CASE("Logger drops a message that can't be formatted", "[Logger]")
{
    auto capture = LogCapture{};
    const auto logger = capture.GetLogger();

    logger->Info("{}", ThrowingArg_s{});
    CHECK(capture.GetEntries().empty());

    logger->Info("ok");
    const auto entries = capture.GetEntries();
    REQUIRE(entries.size() == 1);
    CHECK(entries[0].message == "ok");
}

TEST_CASE("Logger drops a message whose sink throws", "[Logger]")
{
    auto received = std::vector<std::string>{};
    auto logger = Logger{LogLevel_e::Verbose, [&received](const LogEntry_s& entry)
    {
        received.emplace_back(entry.message);
        if (entry.message == "x")
        {
            throw std::runtime_error{"sink failed"};
        }
    }};

    logger.Info("x");
    logger.Info("y");

    CHECK(received == std::vector<std::string>{"x", "y"});
}

TEST_CASE("Logger SetSink returns the sink it replaces", "[Logger]")
{
    auto firstCalls = 0;
    auto secondCalls = 0;
    auto logger = Logger{LogLevel_e::Verbose, [&firstCalls](const LogEntry_s&)
    {
        ++firstCalls;
    }};

    const auto previous = logger.SetSink([&secondCalls](const LogEntry_s&)
    {
        ++secondCalls;
    });

    REQUIRE(static_cast<bool>(previous));
    previous(MakeEntry(LogLevel_e::Info, GetSampleTime()));
    CHECK(firstCalls == 1);

    logger.Info("x");
    CHECK(secondCalls == 1);
    CHECK(firstCalls == 1);
}

TEST_CASE("Logger without a sink discards messages", "[Logger]")
{
    auto calls = 0;
    const auto countCall = [&calls](const LogEntry_s&)
    {
        ++calls;
    };

    auto logger = Logger{LogLevel_e::Verbose, countCall};
    logger.SetSink(nullptr);
    logger.Info("x");
    CHECK(calls == 0);

    logger.SetSink(countCall);
    logger.Info("y");
    CHECK(calls == 1);
}

TEST_CASE("Loggers are independent", "[Logger]")
{
    auto verboseCapture = LogCapture{LogLevel_e::Verbose};
    auto errorCapture = LogCapture{LogLevel_e::Error};

    verboseCapture.GetLogger()->Info("first");
    errorCapture.GetLogger()->Error("second");

    REQUIRE(verboseCapture.GetEntries().size() == 1);
    CHECK(verboseCapture.GetEntries()[0].message == "first");
    REQUIRE(errorCapture.GetEntries().size() == 1);
    CHECK(errorCapture.GetEntries()[0].message == "second");

    verboseCapture.GetLogger()->SetLevel(LogLevel_e::Warning);
    CHECK(errorCapture.GetLogger()->GetLevel() == LogLevel_e::Error);
}

TEST_CASE("A logger outlives its LogCapture", "[Logger]")
{
    auto logger = std::shared_ptr<Logger>{};
    {
        auto capture = LogCapture{};
        logger = capture.GetLogger();
        logger->Info("captured");
        CHECK(capture.GetEntries().size() == 1);
    }

    logger->Info("after");
    CHECK_FALSE(static_cast<bool>(logger->SetSink(nullptr)));
}

TEST_CASE("Logger::FormatLine", "[Logger]")
{
    const auto time = GetSampleTime();

    CHECK(Logger::FormatLine(MakeEntry(LogLevel_e::Info, time)) == "2026-10-05T18:34:12.345Z INFO    hello");
    CHECK(Logger::FormatLine(MakeEntry(LogLevel_e::Verbose, time)) == "2026-10-05T18:34:12.345Z VERBOSE hello");
    CHECK(Logger::FormatLine(MakeEntry(LogLevel_e::Warning, time)) == "2026-10-05T18:34:12.345Z WARNING hello");
    CHECK(Logger::FormatLine(MakeEntry(LogLevel_e::Error, time)) == "2026-10-05T18:34:12.345Z ERROR   hello");

    const auto wholeSecond = std::chrono::sys_days{2026y / std::chrono::January / 2} + 3h + 4min + 5s;
    CHECK(Logger::FormatLine(MakeEntry(LogLevel_e::Info, wholeSecond)) == "2026-01-02T03:04:05.000Z INFO    hello");

    const auto almostNextMillisecond = std::chrono::sys_days{2026y / std::chrono::October / 5} + 18h + 34min + 12s + 345999us;
    CHECK(Logger::FormatLine(MakeEntry(LogLevel_e::Info, almostNextMillisecond)) == "2026-10-05T18:34:12.345Z INFO    hello");

    const auto location = std::source_location::current();
    const auto expected = std::format("2026-10-05T18:34:12.345Z INFO    hello [LoggerTests.cpp:{}]", location.line());
    CHECK(Logger::FormatLine(MakeEntry(LogLevel_e::Info, time, location)) == expected);
}

TEST_CASE("Logger never interleaves writes from several threads", "[Logger][threads]")
{
    constexpr auto THREAD_COUNT = 8;
    constexpr auto ENTRIES_PER_THREAD = 1000;

    auto messages = std::vector<std::string>{};
    auto isInSink = std::atomic<bool>{false};
    auto hasOverlapped = std::atomic<bool>{false};
    const auto logger = std::make_shared<Logger>(LogLevel_e::Verbose, [&](const LogEntry_s& entry)
    {
        if (isInSink.exchange(true))
        {
            hasOverlapped = true;
        }

        messages.emplace_back(entry.message);
        isInSink = false;
    });

    auto threads = std::vector<std::thread>{};
    for (auto thread = 0; thread < THREAD_COUNT; ++thread)
    {
        threads.emplace_back([logger, thread]
        {
            for (auto index = 0; index < ENTRIES_PER_THREAD; ++index)
            {
                logger->Info("{} {}", thread, index);
            }
        });
    }

    for (auto& thread : threads)
    {
        thread.join();
    }

    CHECK_FALSE(hasOverlapped);
    REQUIRE(messages.size() == THREAD_COUNT * ENTRIES_PER_THREAD);

    auto nextIndex = std::array<int, THREAD_COUNT>{};
    for (const auto& message : messages)
    {
        const auto [thread, index] = ParseThreadMessage(message);
        REQUIRE(thread >= 0);
        REQUIRE(thread < THREAD_COUNT);
        REQUIRE(index == nextIndex[thread]);
        REQUIRE(message == std::format("{} {}", thread, index));
        ++nextIndex[thread];
    }
}

TEST_CASE("Logger SetSink is safe while other threads log", "[Logger][threads]")
{
    constexpr auto THREAD_COUNT = 4;
    constexpr auto SWAP_COUNT = std::size_t{100};

    auto sinkCounts = std::array<std::atomic<u64>, SWAP_COUNT + 1>{};
    const auto makeSink = [&sinkCounts](std::size_t index)
    {
        return [&sinkCounts, index](const LogEntry_s&)
        {
            sinkCounts[index].fetch_add(1, std::memory_order_relaxed);
        };
    };

    const auto logger = std::make_shared<Logger>(LogLevel_e::Verbose, makeSink(0));
    auto isStopping = std::atomic<bool>{false};
    auto callCounts = std::array<u64, THREAD_COUNT>{};

    auto threads = std::vector<std::thread>{};
    for (auto thread = 0; thread < THREAD_COUNT; ++thread)
    {
        threads.emplace_back([logger, &isStopping, &callCount = callCounts[thread]]
        {
            while (!isStopping)
            {
                logger->Info("x");
                ++callCount;
            }
        });
    }

    auto countsWhenReplaced = std::array<u64, SWAP_COUNT>{};
    for (std::size_t i = 0; i < SWAP_COUNT; ++i)
    {
        std::this_thread::sleep_for(1ms);
        logger->SetSink(makeSink(i + 1));
        countsWhenReplaced[i] = sinkCounts[i].load();
    }

    isStopping = true;
    for (auto& thread : threads)
    {
        thread.join();
    }

    for (std::size_t i = 0; i < SWAP_COUNT; ++i)
    {
        CAPTURE(i);
        CHECK(sinkCounts[i].load() == countsWhenReplaced[i]);
    }

    auto delivered = u64{0};
    for (const auto& count : sinkCounts)
    {
        delivered += count.load();
    }

    auto made = u64{0};
    for (const auto count : callCounts)
    {
        made += count;
    }

    CHECK(made > 0);
    CHECK(delivered == made);
}
