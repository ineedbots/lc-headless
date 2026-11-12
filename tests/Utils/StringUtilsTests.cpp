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

TEST_CASE("StringUtils preserves non-ASCII bytes when lowercasing characters", "[StringUtils]")
{
    CHECK(StringUtils::ToLowerChar('A') == 'a');
    CHECK(StringUtils::ToLowerChar('Z') == 'z');
    CHECK(StringUtils::ToLowerChar('a') == 'a');
    for (auto value = 0x80; value <= 0xff; ++value)
    {
        const auto byte = static_cast<char>(value);
        CHECK(StringUtils::ToLowerChar(byte) == byte);
    }
}

TEST_CASE("StringUtils trimming respects custom character sets and keeps leading text", "[StringUtils]")
{
    CHECK(StringUtils::Trim("\v name \f", " \t\r\n") == "\v name \f");
    CHECK(StringUtils::Trim("..name..", ".") == "name");
    CHECK(StringUtils::Trim(" name ", "") == " name ");
    CHECK(StringUtils::TrimEnd(" name \t") == " name");
    CHECK(StringUtils::TrimEnd("name\t ", " ") == "name\t");
    CHECK(StringUtils::TrimEnd(" \t").empty());
    CHECK(StringUtils::TrimEnd("").empty());
    CHECK(StringUtils::TrimEnd(" name ", "") == " name ");
}

TEST_CASE("StringUtils hex digits accept both cases and reject other bytes", "[StringUtils]")
{
    const auto digits = "0123456789abcdef"sv;
    for (auto i = std::size_t{0}; i < digits.size(); ++i)
    {
        CHECK(StringUtils::HexDigitValue(static_cast<unsigned char>(digits[i])) == static_cast<int>(i));
    }

    CHECK(StringUtils::HexDigitValue('A') == 10);
    CHECK(StringUtils::HexDigitValue('F') == 15);
    CHECK(StringUtils::HexDigitValue('/') == -1);
    CHECK(StringUtils::HexDigitValue(':') == -1);
    CHECK(StringUtils::HexDigitValue('G') == -1);
    CHECK(StringUtils::HexDigitValue('g') == -1);
    CHECK(StringUtils::HexDigitValue(0xff) == -1);
}

TEST_CASE("StringUtils identifiers use ASCII letters digits and underscores", "[StringUtils]")
{
    CHECK(StringUtils::IsIdentifierAscii("_account_42"));
    CHECK(StringUtils::IsIdentifierAscii("Name"));
    CHECK_FALSE(StringUtils::IsIdentifierAscii(""));
    CHECK_FALSE(StringUtils::IsIdentifierAscii("42name"));
    CHECK_FALSE(StringUtils::IsIdentifierAscii("account-name"));
    CHECK_FALSE(StringUtils::IsIdentifierAscii("caf\xc3\xa9"));
}

TEST_CASE("StringUtils UTF-8 validation rejects noncanonical and incomplete sequences", "[StringUtils]")
{
    for (const auto text : {""sv, "ASCII"sv, "\0"sv, "\xc2\x80"sv, "\xe0\xa0\x80"sv, "\xf0\x90\x80\x80"sv, "\xf4\x8f\xbf\xbf"sv})
    {
        CHECK(StringUtils::IsUtf8(text));
    }

    for (const auto text : {"\x80"sv, "\xc0\x80"sv, "\xe0\x80\x80"sv, "\xed\xa0\x80"sv, "\xf0\x80\x80\x80"sv, "\xf4\x90\x80\x80"sv, "\xff"sv, "\xe2\x82"sv, "\xc2x"sv})
    {
        CHECK_FALSE(StringUtils::IsUtf8(text));
    }
}
