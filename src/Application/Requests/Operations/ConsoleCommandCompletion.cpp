#include "pch.hpp"
#include "ConsoleCommandCompletion.hpp"

#include "Application/Requests/Type/CompletedApplicationRequest_s.hpp"
#include "Application/Requests/Type/ConsoleCommandResult_s.hpp"
#include "Application/Requests/Type/RequestControl_s.hpp"
#include "Console/CommandExecution.hpp"
#include "Console/ConsoleCapture.hpp"
#include "Console/Type/CommandRecipient_s.hpp"

std::optional<CompletedApplicationRequest_s> ConsoleCommandCompletion::TryComplete(RequestControl_s& control, bool stopping)
{
    auto& execution = *control.execution;
    if (control.abandoned || std::chrono::steady_clock::now() >= control.deadline || stopping)
    {
        execution.abandoned = true;

        for (auto& recipient : execution.recipients)
        {
            if (recipient.outcome == "pending")
            {
                recipient.outcome = "cancelled";
                recipient.errorCode = "request_cancelled";
            }
        }
    }

    if (!execution.IsComplete())
    {
        return {};
    }

    auto result = CompletedApplicationRequest_s{.id = control.id};
    const auto succeeded = std::ranges::count(execution.recipients, "completed", &CommandRecipient_s::outcome);
    const auto failed = std::ranges::count(execution.recipients, "failed", &CommandRecipient_s::outcome);
    const auto cancelled = std::ranges::count(execution.recipients, "cancelled", &CommandRecipient_s::outcome);
    if (succeeded > 0 && static_cast<std::size_t>(succeeded) != execution.recipients.size())
    {
        result.outcome = "partial";
    }
    else if (failed > 0 || execution.errorCode == "internal_failure")
    {
        result.outcome = "failed";
    }
    else if (cancelled > 0 || execution.abandoned)
    {
        result.outcome = "cancelled";
    }
    else if (!execution.errorCode.empty() || (!execution.recipients.empty() && succeeded == 0))
    {
        result.outcome = "rejected";
    }

    result.errorCode = execution.errorCode;
    if (result.errorCode.empty())
    {
        if (result.outcome == "failed")
        {
            result.errorCode = "handler_failed";
        }
        else if (result.outcome == "cancelled")
        {
            result.errorCode = "invocation_cancelled";
        }
        else if (result.outcome == "rejected")
        {
            result.errorCode = "command_rejected";
        }
    }

    result.payload = ConsoleCommandResult_s{std::move(execution.capture.output), execution.capture.truncated, execution.started, execution.recipients};
    return result;
}
