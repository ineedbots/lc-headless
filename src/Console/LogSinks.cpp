#include "pch.hpp"
#include "LogSinks.hpp"

#include "ConsoleInput.hpp"
#include "ConsoleOutput.hpp"
#include "LogEntry_s.hpp"
#include "LogFile.hpp"
#include "Logger.hpp"

Logger::Sink LogSinks::Make(std::shared_ptr<LogFile> file, std::shared_ptr<ConsoleInput> console, bool rawConsole)
{
    if (console && !console->IsInteractive())
    {
        console.reset();
    }

    return [file = std::move(file), console = std::move(console), rawConsole](const LogEntry_s& entry)
    {
        if (file)
        {
            file->Write(entry);
        }

        if (console)
        {
            console->Print(ConsoleOutput::GetStream(entry.level), ConsoleOutput::FormatLine(entry));
        }
        else if (rawConsole)
        {
            ConsoleOutput::WritePlain(entry);
        }
        else
        {
            ConsoleOutput::Write(entry);
        }
    };
}
