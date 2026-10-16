#include "pch.hpp"

#include "Console/ConsoleCommandParser.hpp"
#include "Console/ConsoleCommand_s.hpp"

#include <catch2/catch_test_macros.hpp>

TEST_CASE("ConsoleCommandParser reads a command for every account", "[ConsoleCommandParser]")
{
    const auto parsed = ConsoleCommandParser::Parse("  Say  hello   there ");

    REQUIRE(parsed);
    CHECK_FALSE(parsed->target);
    CHECK(parsed->command.name == "say");
    CHECK(parsed->command.text == "hello   there");
    CHECK(parsed->command.args == std::vector<std::string>{"hello", "there"});
}

TEST_CASE("ConsoleCommandParser reads a command without arguments", "[ConsoleCommandParser]")
{
    const auto parsed = ConsoleCommandParser::Parse("status");

    REQUIRE(parsed);
    CHECK(parsed->command.name == "status");
    CHECK(parsed->command.text.empty());
    CHECK(parsed->command.args.empty());
}

TEST_CASE("ConsoleCommandParser reads the target of a line sent to one account", "[ConsoleCommandParser]")
{
    const auto parsed = ConsoleCommandParser::Parse("@Bob\tloglevel  info");

    REQUIRE(parsed);
    CHECK(parsed->target == "Bob");
    CHECK(parsed->command.name == "loglevel");
    CHECK(parsed->command.args == std::vector<std::string>{"info"});
}

TEST_CASE("ConsoleCommandParser leaves the command empty after a lone target", "[ConsoleCommandParser]")
{
    const auto parsed = ConsoleCommandParser::Parse(" @bob ");

    REQUIRE(parsed);
    CHECK(parsed->target == "bob");
    CHECK(parsed->command.name.empty());
}

TEST_CASE("ConsoleCommandParser ignores a blank line", "[ConsoleCommandParser]")
{
    CHECK_FALSE(ConsoleCommandParser::Parse(""));
    CHECK_FALSE(ConsoleCommandParser::Parse(" \t "));
}
