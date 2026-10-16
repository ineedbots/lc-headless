#pragma once

#include "LogEntry_s.hpp"
#include "LogLevel_e.hpp"

// Warnings and errors go to stderr, everything else to stdout.
class ConsoleOutput
{
public:
    ConsoleOutput() = delete;

    // Colored where the terminal shows colors.
    static void Write(const LogEntry_s& entry);
    static void WritePlain(const LogEntry_s& entry);
    // Colored only on a terminal that shows VT100 colors, and only when NO_COLOR isn't set.
    [[nodiscard]] static std::string FormatLine(const LogEntry_s& entry);
    [[nodiscard]] static std::FILE* GetStream(LogLevel_e level);
};
