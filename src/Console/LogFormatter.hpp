#pragma once

#include "LogEntry_s.hpp"

class LogFormatter
{
public:
    LogFormatter() = delete;

    [[nodiscard]] static std::string FormatLine(const LogEntry_s& entry);
    // FormatLine in the level's VT100 color; info keeps the terminal's own.
    [[nodiscard]] static std::string FormatColoredLine(const LogEntry_s& entry);
};
