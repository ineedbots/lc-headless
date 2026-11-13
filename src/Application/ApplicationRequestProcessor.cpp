#include "pch.hpp"
#include "ApplicationRequestProcessor.hpp"

#include "ApplicationRequestBridge.hpp"
#include "Type/RequestControl_s.hpp"
#include "Type/CompletedApplicationRequest_s.hpp"
#include "Type/ApplicationRequest_s.hpp"
#include "Type/ConsoleCommandResult_s.hpp"
#include "../Console/CommandExecution.hpp"
#include "../Console/ConsoleCapture.hpp"
#include "Type/ApplicationOperations_s.hpp"
#include "Type/ApplicationRequestContext_s.hpp"

ApplicationRequestProcessor::ApplicationRequestProcessor(AccountRunner& runner, std::shared_ptr<ApplicationRequestBridge> bridge,
                                                         std::chrono::steady_clock::time_point started)
    : m_runner{runner}
    , m_bridge{std::move(bridge)}
    , m_started{started}
{
}

void ApplicationRequestProcessor::Dispatch()
{
    const auto until = std::chrono::steady_clock::now() + 2ms;
    for (auto count = 0; count < 8 && std::chrono::steady_clock::now() < until; ++count)
    {
        auto request = m_bridge->Take();
        if (!request)
        {
            break;
        }

        auto control = request->control;
        if (control->abandoned || std::chrono::steady_clock::now() >= control->deadline)
        {
            m_bridge->Complete({.id = control->id, .outcome = "cancelled", .errorCode = "request_cancelled"});
            continue;
        }

        std::visit([&](const auto& payload)
        {
            const auto context = ApplicationRequestContext_s{m_runner, m_started, static_cast<std::size_t>(m_bridge->GetSettings().maxOutputBytes)};
            auto result = ApplicationOperations_s::Execute(context, control, payload);
            if (result)
            {
                m_bridge->Complete({.id = control->id, .payload = std::move(*result)});
            }
            else
            {
                assert(control->execution && "Deferred operations must install command execution state");
                m_executing.push_back(control);
            }
        }, request->payload);
    }
}

void ApplicationRequestProcessor::Finalize()
{
    for (const auto& control : m_executing)
    {
        auto& execution = *control->execution;
        if (control->abandoned || std::chrono::steady_clock::now() >= control->deadline || m_bridge->IsClosing())
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
            continue;
        }

        auto result = CompletedApplicationRequest_s{.id = control->id};
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
        m_bridge->Complete(std::move(result));
    }

    std::erase_if(m_executing, [](const auto& control)
    {
        return control->engineDone;
    });
}

void ApplicationRequestProcessor::Stop()
{
    m_bridge->Close();

    while (const auto request = m_bridge->Take())
    {
        m_bridge->Complete({.id = request->control->id, .outcome = "cancelled", .errorCode = "stopping"});
    }

    Finalize();
}
