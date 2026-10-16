#include "pch.hpp"
#include "LogLevelNames.hpp"

#include "LogLevel_e.hpp"

namespace
{
    struct LogLevelName_s
    {
        LogLevel_e level;
        std::string_view name;
    };

    constexpr auto NAMES = std::array{
        LogLevelName_s{LogLevel_e::Verbose, "verbose"},
        LogLevelName_s{LogLevel_e::Info, "info"},
        LogLevelName_s{LogLevel_e::Warning, "warning"},
        LogLevelName_s{LogLevel_e::Error, "error"},
    };
}

std::optional<LogLevel_e> LogLevelNames::Find(std::string_view name)
{
    const auto entry = std::ranges::find(NAMES, name, &LogLevelName_s::name);
    if (entry == NAMES.end())
    {
        return std::nullopt;
    }

    return entry->level;
}

std::string_view LogLevelNames::GetName(LogLevel_e level)
{
    const auto entry = std::ranges::find(NAMES, level, &LogLevelName_s::level);
    assert(entry != NAMES.end() && "LogLevel_e value missing from LogLevelNames");
    return entry->name;
}
