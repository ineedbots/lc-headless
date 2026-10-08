#include "pch.hpp"

#include "Application.hpp"
#include "Core/ConfigFile.hpp"

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

        return Application::ParseCommandLine(pointers);
    }
}

TEST_CASE("Application reads its command line", "[Application]")
{
    const auto defaults = Parse({});
    CHECK(defaults.configPath == ConfigFile::DEFAULT_PATH);
    CHECK_FALSE(defaults.accountPath.has_value());
    CHECK_FALSE(defaults.watch);
    CHECK_FALSE(defaults.debugger);

    const auto everything = Parse({"live.jsonc", "--account", "accounts/bot1.jsonc", "--debugger"});
    CHECK(everything.configPath == "live.jsonc");
    CHECK(everything.accountPath == std::filesystem::path{"accounts/bot1.jsonc"});
    CHECK(everything.debugger);

    CHECK(Parse({"--watch"}).watch);
    CHECK(Parse({"--watch", "--account", "accounts/bot1.jsonc"}).watch);
}

TEST_CASE("Application rejects a command line it can't use", "[Application]")
{
    CHECK_THROWS_WITH(Parse({"--account"}), ContainsSubstring("needs an account file path"));
    CHECK_THROWS_WITH(Parse({"--wtach"}), ContainsSubstring("Unknown option --wtach") && ContainsSubstring("usage:"));
    CHECK_THROWS_WITH(Parse({"--debugger"}), ContainsSubstring("--debugger needs --account"));
    CHECK_THROWS_WITH(Parse({"--account", "a.jsonc", "--watch", "--debugger"}), ContainsSubstring("can't be combined"));
    CHECK_THROWS_AS(Parse({"--debugger"}), std::invalid_argument);
}
