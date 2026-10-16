#include "pch.hpp"

#include "Console/ConsoleOutput.hpp"
#include "Console/LogLevel_e.hpp"

#include <catch2/catch_test_macros.hpp>

TEST_CASE("ConsoleOutput writes warnings and errors to stderr", "[ConsoleOutput]")
{
    CHECK(ConsoleOutput::GetStream(LogLevel_e::Verbose) == stdout);
    CHECK(ConsoleOutput::GetStream(LogLevel_e::Info) == stdout);
    CHECK(ConsoleOutput::GetStream(LogLevel_e::Warning) == stderr);
    CHECK(ConsoleOutput::GetStream(LogLevel_e::Error) == stderr);
}
