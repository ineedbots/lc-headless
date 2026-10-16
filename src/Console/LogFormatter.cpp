#include "pch.hpp"
#include "LogFormatter.hpp"

#include "LogEntry_s.hpp"
#include "LogLevel_e.hpp"

namespace
{
    constexpr auto COLOR_RESET = "\x1B[0m"sv;

    // Empty for the terminal's own color.
    std::string_view GetLevelColor(LogLevel_e level)
    {
        switch (level)
        {
        case LogLevel_e::Verbose:
            return "\x1B[36m";
        case LogLevel_e::Info:
            return {};
        case LogLevel_e::Warning:
            return "\x1B[33m";
        case LogLevel_e::Error:
            return "\x1B[31m";
        }

        return {};
    }

    std::string_view GetLevelName(LogLevel_e level)
    {
        switch (level)
        {
        case LogLevel_e::Verbose:
            return "VERBOSE";
        case LogLevel_e::Info:
            return "INFO";
        case LogLevel_e::Warning:
            return "WARNING";
        case LogLevel_e::Error:
            return "ERROR";
        }

        assert(false && "Unknown log level");
        return "UNKNOWN";
    }

    std::string_view GetFileName(std::string_view path)
    {
        const auto separator = path.find_last_of("/\\");
        if (separator == std::string_view::npos)
        {
            return path;
        }

        return path.substr(separator + 1);
    }
}

std::string LogFormatter::FormatLine(const LogEntry_s& entry)
{
    const auto time = std::chrono::floor<std::chrono::milliseconds>(entry.time);
    auto line = std::format("{:%FT%T}Z {:<7} ", time, GetLevelName(entry.level));
    if (!entry.source.empty())
    {
        std::format_to(std::back_inserter(line), "[{}] ", entry.source);
    }

    line += entry.message;
    if (entry.location)
    {
        std::format_to(std::back_inserter(line), " [{}:{}]", GetFileName(entry.location->file_name()), entry.location->line());
    }

    return line;
}

std::string LogFormatter::FormatColoredLine(const LogEntry_s& entry)
{
    const auto color = GetLevelColor(entry.level);
    if (color.empty())
    {
        return FormatLine(entry);
    }

    auto line = std::string{color};
    line += FormatLine(entry);
    line += COLOR_RESET;
    return line;
}
