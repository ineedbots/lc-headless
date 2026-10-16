#include "pch.hpp"
#include "ConsoleOutput.hpp"

#include "LogEntry_s.hpp"
#include "LogFormatter.hpp"
#include "LogLevel_e.hpp"
#include "Terminal.hpp"

namespace
{
    void WriteLine(std::FILE* stream, std::string line)
    {
        line += '\n';
        std::fwrite(line.data(), 1, line.size(), stream);
        std::fflush(stream);
    }

    // Checked once per stream, the first time something is written to the console.
    bool CanColorStream(std::FILE* stream)
    {
        static const auto output = Terminal::CanColor(stdout);
        static const auto error = Terminal::CanColor(stderr);
        return stream == stderr ? error : output;
    }
}

void ConsoleOutput::Write(const LogEntry_s& entry)
{
    WriteLine(GetStream(entry.level), FormatLine(entry));
}

void ConsoleOutput::WritePlain(const LogEntry_s& entry)
{
    WriteLine(GetStream(entry.level), LogFormatter::FormatLine(entry));
}

std::string ConsoleOutput::FormatLine(const LogEntry_s& entry)
{
    return CanColorStream(GetStream(entry.level)) ? LogFormatter::FormatColoredLine(entry) : LogFormatter::FormatLine(entry);
}

std::FILE* ConsoleOutput::GetStream(LogLevel_e level)
{
    return level >= LogLevel_e::Warning ? stderr : stdout;
}
