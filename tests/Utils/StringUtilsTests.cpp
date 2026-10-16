#include "pch.hpp"

#include "Utils/StringUtils.hpp"

#include <catch2/catch_test_macros.hpp>

TEST_CASE("StringUtils::ToLower lowers ASCII letters only", "[StringUtils]")
{
    CHECK(StringUtils::ToLower("Bob The BUILDER 42") == "bob the builder 42");
    CHECK(StringUtils::ToLower("") == "");
    CHECK(StringUtils::ToLower("\xC3\x89t\xC3\xA9") == "\xC3\x89t\xC3\xA9");
}

TEST_CASE("StringUtils::EqualsIgnoringCase", "[StringUtils]")
{
    CHECK(StringUtils::EqualsIgnoringCase("Take", "tAKE"));
    CHECK(StringUtils::EqualsIgnoringCase("", ""));
    CHECK_FALSE(StringUtils::EqualsIgnoringCase("Take", "Taken"));
    CHECK_FALSE(StringUtils::EqualsIgnoringCase("Take", "Tale"));
}

TEST_CASE("StringUtils::Trim takes every kind of whitespace off both ends", "[StringUtils]")
{
    CHECK(StringUtils::Trim("  say hi \t") == "say hi");
    CHECK(StringUtils::Trim("\n\v\f\rname\r\n") == "name");
    CHECK(StringUtils::Trim(" \t ") == "");
    CHECK(StringUtils::Trim("") == "");
    CHECK(StringUtils::Trim("a  b") == "a  b");
}

TEST_CASE("StringUtils::TrimTrailingNewlines", "[StringUtils]")
{
    CHECK(StringUtils::TrimTrailingNewlines("Traceback\r\n\n") == "Traceback");
    CHECK(StringUtils::TrimTrailingNewlines("\nline ") == "\nline ");
}

TEST_CASE("StringUtils::SplitFirstWord", "[StringUtils]")
{
    CHECK(StringUtils::SplitFirstWord("  say  hello there ") == std::pair{"say"sv, "hello there"sv});
    CHECK(StringUtils::SplitFirstWord("status") == std::pair{"status"sv, ""sv});
    CHECK(StringUtils::SplitFirstWord("say\thi") == std::pair{"say"sv, "hi"sv});
    CHECK(StringUtils::SplitFirstWord("   ") == std::pair{""sv, ""sv});
}

TEST_CASE("StringUtils::SplitWords splits at runs of whitespace", "[StringUtils]")
{
    CHECK(StringUtils::SplitWords("Make  5\tbronze bars ") == std::vector{"Make"sv, "5"sv, "bronze"sv, "bars"sv});
    CHECK(StringUtils::SplitWords("one") == std::vector{"one"sv});
    CHECK(StringUtils::SplitWords("").empty());
    CHECK(StringUtils::SplitWords(" \t ").empty());
}

TEST_CASE("StringUtils::Join", "[StringUtils]")
{
    CHECK(StringUtils::Join(std::vector<std::string>{"script", "settings", "Chicken killer"}, ".") == "script.settings.Chicken killer");
    CHECK(StringUtils::Join(std::vector<std::string>{"only"}, ", ") == "only");
    CHECK(StringUtils::Join(std::vector<std::string>{}, ", ") == "");
    CHECK(StringUtils::Join(std::vector<std::string>{"", "b"}, ", ") == ", b");
}

TEST_CASE("StringUtils::IsPrintableAscii", "[StringUtils]")
{
    CHECK(StringUtils::IsPrintableAscii("hunter2 ~!"));
    CHECK(StringUtils::IsPrintableAscii(""));
    CHECK_FALSE(StringUtils::IsPrintableAscii("tab\there"));
    CHECK_FALSE(StringUtils::IsPrintableAscii("caf\xC3\xA9"));
    CHECK_FALSE(StringUtils::IsPrintableAscii("\x7F"));
}
