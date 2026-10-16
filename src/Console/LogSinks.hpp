#pragma once

#include "ConsoleInput.hpp"
#include "LogFile.hpp"
#include "Logger.hpp"

class LogSinks
{
public:
    LogSinks() = delete;

    // Each entry goes to the file, when there is one, then to the console: above the prompt of an interactive
    // console, plain for a raw one, and otherwise colored where the terminal shows colors. A console that
    // isn't interactive counts as none.
    [[nodiscard]] static Logger::Sink Make(std::shared_ptr<LogFile> file, std::shared_ptr<ConsoleInput> console, bool rawConsole);
};
