#pragma once

#include "LogLevel_e.hpp"

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
