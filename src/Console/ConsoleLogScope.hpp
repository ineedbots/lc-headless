#pragma once

#include "ConsoleInput.hpp"

// Installs a log sink that writes around the console's prompt for as long as the scope lasts, then closes
// the console and installs one without it.
class ConsoleLogScope
{
public:
    using Install = std::function<void(std::shared_ptr<ConsoleInput>)>;

    ConsoleLogScope(Install install, std::shared_ptr<ConsoleInput> console);
    ~ConsoleLogScope();

    ConsoleLogScope(const ConsoleLogScope&) = delete;
    ConsoleLogScope& operator=(const ConsoleLogScope&) = delete;

private:
    Install m_install;
    std::shared_ptr<ConsoleInput> m_console;
};
