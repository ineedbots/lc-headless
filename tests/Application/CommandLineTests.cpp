#include "pch.hpp"

#include "Application/CommandLine.hpp"
#include "Config/ConfigFile.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>

using Catch::Matchers::ContainsSubstring;

namespace
{
    CommandLine_s Parse(std::vector<std::string> args)
    {
        auto pointers = std::vector<char*>{};
        for (auto& arg : args)
        {
            pointers.push_back(arg.data());
        }

        return CommandLine::Parse(pointers);
    }
}

TEST_CASE("CommandLine reads its command line", "[CommandLine]")
{
    const auto defaults = Parse({});
    CHECK(defaults.configPath == ConfigFile::DEFAULT_PATH);
    CHECK_FALSE(defaults.accountPath.has_value());
    CHECK_FALSE(defaults.watch);
    CHECK_FALSE(defaults.debugger);
    CHECK_FALSE(defaults.rawConsole);

    const auto everything = Parse({"live.jsonc", "--account", "accounts/bot1.jsonc", "--debugger"});
    CHECK(everything.configPath == "live.jsonc");
    CHECK(everything.accountPath == std::filesystem::path{"accounts/bot1.jsonc"});
    CHECK(everything.debugger);

    CHECK(Parse({"--watch"}).watch);
    CHECK(Parse({"--raw-console", "--watch"}).rawConsole);
    CHECK(Parse({"--watch", "--account", "accounts/bot1.jsonc"}).watch);
}

TEST_CASE("CommandLine rejects a command line it can't use", "[CommandLine]")
{
    CHECK_THROWS_WITH(Parse({"--account"}), ContainsSubstring("needs an account file path"));
    CHECK_THROWS_WITH(Parse({"--wtach"}), ContainsSubstring("Unknown option --wtach") && ContainsSubstring("usage:"));
    CHECK_THROWS_WITH(Parse({"--debugger"}), ContainsSubstring("--debugger needs --account"));
    CHECK_THROWS_WITH(Parse({"--account", "a.jsonc", "--watch", "--debugger"}), ContainsSubstring("can't be combined"));
    CHECK_THROWS_AS(Parse({"--debugger"}), std::invalid_argument);
}
