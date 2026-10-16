#include "pch.hpp"
#include "../Support/TempFolder.hpp"

#include "Console/LogEntry_s.hpp"
#include "Console/LogFile.hpp"
#include "Console/LogLevel_e.hpp"
#include "Console/Logger.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>

using Catch::Matchers::ContainsSubstring;

namespace
{
    std::string ReadAll(const std::filesystem::path& path)
    {
        auto stream = std::ifstream{path, std::ios::binary};
        return {std::istreambuf_iterator<char>{stream}, std::istreambuf_iterator<char>{}};
    }

    LogEntry_s MakeEntry(LogLevel_e level, std::string_view message, std::string_view source = {})
    {
        const auto time = std::chrono::sys_days{2026y / std::chrono::October / 13} + 1h + 2min + 3s;
        return LogEntry_s{.level = level, .time = time, .message = message, .source = source};
    }
}

TEST_CASE("LogFile appends plain lines, making its folder", "[LogFile]")
{
    const auto folder = TempFolder{"rs2004-log-file-tests"};
    const auto path = folder.GetPath() / "logs" / "bots.log";
    {
        auto file = LogFile{path};
        CHECK(file.GetPath() == path);
        file.Write(MakeEntry(LogLevel_e::Error, "it broke", "bot1"));
        // Flushed as it's written, so it's there before the file closes.
        CHECK(ReadAll(path) == "2026-10-13T01:02:03.000Z ERROR   [bot1] it broke\n");
    }

    // A second run adds to the end.
    auto file = LogFile{path};
    file.Write(MakeEntry(LogLevel_e::Warning, "again"));
    CHECK(ReadAll(path) == "2026-10-13T01:02:03.000Z ERROR   [bot1] it broke\n2026-10-13T01:02:03.000Z WARNING again\n");
}

TEST_CASE("LogFile says which file it can't open", "[LogFile]")
{
    const auto folder = TempFolder{"rs2004-log-file-tests"};
    // A folder where the file should be.
    std::filesystem::create_directories(folder.GetPath() / "taken.log");
    CHECK_THROWS_WITH(LogFile{folder.GetPath() / "taken.log"}, ContainsSubstring("taken.log: the log file can't be opened"));
}
