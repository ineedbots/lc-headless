#pragma once

#include "ConsoleCommand_s.hpp"
#include "../CommandExecution.hpp"
struct QueuedCommand_s
{
    ConsoleCommand_s command;
    std::shared_ptr<CommandRecipient> recipient;
};
