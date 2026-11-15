#pragma once

#include "Type/LogLevel_e.hpp"

#include <nlohmann/json.hpp>

// The names client.jsonc and the console's loglevel command use.
class LogLevelNames
{
public:
    static constexpr auto CHOICES = "verbose, info, warning or error"sv;

    LogLevelNames() = delete;

    // Exactly as written; the console lower-cases what was typed first.
    [[nodiscard]] static std::optional<LogLevel_e> Find(std::string_view name);
    [[nodiscard]] static std::string_view GetName(LogLevel_e level);
};

namespace nlohmann
{
    template <>
    struct adl_serializer<LogLevel_e>
    {
        static void from_json(const json& value, LogLevel_e& result)
        {
            const auto level = LogLevelNames::Find(value.get<std::string>());
            if (!level)
            {
                throw json::type_error::create(302, std::format("must be {}", LogLevelNames::CHOICES), &value);
            }

            result = *level;
        }

        static void to_json(ordered_json& value, LogLevel_e level)
        {
            value = std::string{LogLevelNames::GetName(level)};
        }
    };
}
