#include "pch.hpp"
#include "ConsoleCommandOperation.hpp"

#include "../Type/ConsoleCommandResult_s.hpp"
#include "../../Console/ConsoleCapture.hpp"
#include "../../Console/CommandExecution.hpp"
#include "../../Accounts/AccountControl.hpp"
#include "../Type/RequestControl_s.hpp"
#include "../Type/ExecuteConsoleCommand_s.hpp"
#include "../Type/ApplicationRequestContext_s.hpp"

std::optional<ConsoleCommandResult_s> ConsoleCommandOperation::Execute(const ApplicationRequestContext_s& context, const std::shared_ptr<RequestControl_s>& control, const ExecuteConsoleCommand_s& command)
{
    auto execution = std::make_shared<CommandExecution>(static_cast<std::size_t>(context.maxOutputBytes), control->deadline);
    control->execution = execution;

    try
    {
        const auto capture = ConsoleCaptureScope{&execution->capture};
        context.runner.HandleCommand(command.command, execution);
    }
    catch (const std::exception&)
    {
        execution->errorCode = "internal_failure";
    }

    execution->dispatched = true;
    return {};
}
