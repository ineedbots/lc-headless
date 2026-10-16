#include "pch.hpp"

#include "Config/Error/ConfigError.hpp"
#include "Config/JsoncScanner.hpp"
#include "Config/JsoncValue_s.hpp"

#include <catch2/catch_test_macros.hpp>

TEST_CASE("JsoncScanner finds each member and where its value sits", "[JsoncScanner]")
{
    const auto text = R"json({
    // A comment.
    "a": 1,
    "b": {"c": [1, {"d": 2}], /* inline */ "e": "x\"y"}
})json"sv;

    const auto root = JsoncScanner{text}.ScanDocument();

    CHECK(root.isObject);
    CHECK(root.begin == 0);
    CHECK(root.end == text.size());
    REQUIRE(root.members.size() == 2);
    REQUIRE(root.values.size() == 2);
    CHECK(root.members[0].key == "a");
    CHECK(text.substr(root.members[0].keyBegin, 3) == "\"a\"");
    CHECK(text.substr(root.values[0].begin, root.values[0].end - root.values[0].begin) == "1");

    const auto& b = root.values[1];
    CHECK(b.isObject);
    REQUIRE(b.members.size() == 2);
    CHECK(b.members[0].key == "c");
    CHECK_FALSE(b.values[0].isObject);
    CHECK(b.members[1].key == "e");
    CHECK(text.substr(b.values[1].begin, b.values[1].end - b.values[1].begin) == R"("x\"y")");
}

TEST_CASE("JsoncScanner skips a byte order mark", "[JsoncScanner]")
{
    const auto root = JsoncScanner{"\xEF\xBB\xBF{\"a\": true}"}.ScanDocument();

    CHECK(root.begin == 3);
    REQUIRE(root.members.size() == 1);
    CHECK(root.members[0].key == "a");
}

TEST_CASE("JsoncScanner rejects what it doesn't expect", "[JsoncScanner]")
{
    for (const auto text : {"", "{", "{\"a\" 1}", "{\"a\": 1,}", "{} extra", "/* unclosed {}", "[1 2]"})
    {
        CAPTURE(text);
        CHECK_THROWS_AS(JsoncScanner{text}.ScanDocument(), ConfigError);
    }
}
