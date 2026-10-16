#include "pch.hpp"

#include "Console/LogLevelNames.hpp"
#include "Console/LogLevel_e.hpp"

#include <catch2/catch_test_macros.hpp>

TEST_CASE("LogLevelNames names every level both ways", "[LogLevelNames]")
{
    for (const auto level : {LogLevel_e::Verbose, LogLevel_e::Info, LogLevel_e::Warning, LogLevel_e::Error})
    {
        CHECK(LogLevelNames::Find(LogLevelNames::GetName(level)) == level);
    }

    CHECK(LogLevelNames::GetName(LogLevel_e::Warning) == "warning");
}

TEST_CASE("LogLevelNames finds a name only as written", "[LogLevelNames]")
{
    CHECK(LogLevelNames::Find("info") == LogLevel_e::Info);
    CHECK_FALSE(LogLevelNames::Find("Info"));
    CHECK_FALSE(LogLevelNames::Find("debug"));
    CHECK_FALSE(LogLevelNames::Find(""));
}
