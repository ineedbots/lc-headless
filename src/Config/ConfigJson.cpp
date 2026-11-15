#include "pch.hpp"
#include "ConfigJson.hpp"

#include "../Utils/StringUtils.hpp"
#include "Error/ConfigError.hpp"

#include <nlohmann/json.hpp>

namespace
{
    constexpr auto INDENT = 4;
    constexpr auto ALLOW_EXCEPTIONS = true;
    constexpr auto IGNORE_COMMENTS = true;

    struct TextPosition_s
    {
        std::size_t line;
        std::size_t column;
    };

    TextPosition_s GetTextPosition(std::string_view text, std::size_t byte)
    {
        // nlohmann's byte is 1-based and counts the end of input, so it can be one past the text.
        const auto offset = std::min(byte > 0 ? byte - 1 : 0, text.size());
        const auto before = text.substr(0, offset);
        const auto line = 1 + static_cast<std::size_t>(std::ranges::count(before, '\n'));
        const auto lineStart = before.find_last_of('\n');
        const auto column = lineStart == std::string_view::npos ? offset + 1 : offset - lineStart;
        return {.line = line, .column = column};
    }

    nlohmann::json ParseJson(std::string_view text)
    {
        try
        {
            return nlohmann::json::parse(text, nullptr, ALLOW_EXCEPTIONS, IGNORE_COMMENTS);
        }
        catch (const nlohmann::json::parse_error& e)
        {
            // Not e.what(): lexer errors quote the text they stopped in, which can be part of the password.
            const auto position = GetTextPosition(text, e.byte);
            throw ConfigError{std::format("invalid JSON at line {}, column {}", position.line, position.column)};
        }
    }

    std::string DescribeConversionError(const nlohmann::json::exception& e)
    {
        auto message = std::string_view{e.what()};
        const auto idEnd = message.find("] ");
        if (idEnd != std::string_view::npos)
        {
            message.remove_prefix(idEnd + 2);
        }

        const auto pointerEnd = message.find(") ");
        if (!message.starts_with('(') || pointerEnd == std::string_view::npos)
        {
            return std::string{message};
        }

        auto path = std::string{message.substr(1, pointerEnd - 1)};
        if (path.starts_with('/'))
        {
            path.erase(0, 1);
        }

        std::ranges::replace(path, '/', '.');
        return std::format("{}: {}", path, message.substr(pointerEnd + 2));
    }

    nlohmann::json ParseRootObject(std::string_view text)
    {
        auto root = ParseJson(text);
        if (!root.is_object())
        {
            throw ConfigError{"the top level must be an object"};
        }

        return root;
    }
}

Config_s ConfigJson::ParseConfig(std::string_view text)
{
    const auto root = ParseRootObject(text);
    if (root.contains("http"))
    {
        const auto& http = root.at("http");
        if (!http.is_object())
        {
            throw ConfigError{"http: must be an object"};
        }

        for (const auto& [key, low, high] : std::vector<std::tuple<std::string, s64, s64>>{
                 {"port", 1, 65535}, {"requestTimeoutMs", 100, 120000}, {"maxPendingRequests", 1, 1024}, {"maxRequestBodyBytes", 1, 1048576}, {"maxOutputBytes", 1, 16777216}})
        {
            if (!http.contains(key))
            {
                continue;
            }

            const auto& value = http.at(key);
            if (!value.is_number_integer() || value < low || value > high)
            {
                throw ConfigError{std::format("http.{}: must be an integer from {} to {}", key, low, high)};
            }
        }
    }

    auto config = Config_s{};
    try
    {
        root.get_to(config);
    }
    catch (const nlohmann::json::exception& e)
    {
        throw ConfigError{DescribeConversionError(e)};
    }

    config.http.host = std::string{StringUtils::Trim(config.http.host, " \t\r\n")};
    return config;
}

AccountConfig_s ConfigJson::ParseAccount(std::string_view text)
{
    const auto root = ParseRootObject(text);
    auto account = AccountConfig_s{};
    try
    {
        root.get_to(account);
    }
    catch (const nlohmann::json::exception& e)
    {
        throw ConfigError{DescribeConversionError(e)};
    }

    return account;
}

std::string ConfigJson::SerializeConfig(const Config_s& config)
{
    // Parentheses, not braces: a braced ordered_json is an array holding the config.
    const auto document = nlohmann::ordered_json(config);
    return document.dump(INDENT) + '\n';
}

void ConfigJson::CheckObject(std::string_view text)
{
    static_cast<void>(ParseRootObject(text));
}
