#include "pch.hpp"
#include "Utils/JsonUtils.hpp"

#include <catch2/catch_test_macros.hpp>
#include <nlohmann/json.hpp>

TEST_CASE("JsonUtils escapes control characters and preserves UTF-8", "[JsonUtils]")
{
    auto text = std::string{"quotes\" and slash\\"};
    for (auto value = 0; value < 32; ++value)
    {
        text += static_cast<char>(value);
    }

    text += "\xc3\xa9";
    const auto escaped = JsonUtils::EscapeString(text);
    CHECK(escaped.find('\n') == std::string::npos);
    CHECK(escaped.find('\r') == std::string::npos);
    CHECK(nlohmann::json::parse("\"" + escaped + "\"").get<std::string>() == text);
    CHECK(JsonUtils::EscapeString("").empty());
}
