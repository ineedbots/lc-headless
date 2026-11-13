#pragma once

#include "../Type/ExecuteConsoleCommand_s.hpp"
#include "../Type/ConsoleCommandResult_s.hpp"
#include "../Type/RequestControl_s.hpp"
#include "../Type/ApplicationRequestContext_s.hpp"

class ConsoleCommandOperation
{
public:
    ConsoleCommandOperation() = delete;
    using Payload = ExecuteConsoleCommand_s;
    using Result = ConsoleCommandResult_s;
    // A missing result leaves completion with RequestControl_s::execution.
    static std::optional<Result> Execute(const ApplicationRequestContext_s& context, const std::shared_ptr<RequestControl_s>& control, const Payload& request);
};
