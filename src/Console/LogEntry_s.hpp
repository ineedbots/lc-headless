#pragma once

#include "LogLevel_e.hpp"

struct LogEntry_s
{
    LogLevel_e level;
    std::chrono::system_clock::time_point time;
    std::optional<std::source_location> location;
    std::string_view message;
    // Empty for an unnamed logger.
    std::string_view source;
};
