#include "pch.hpp"
#include "ApplicationRequestProcessor.hpp"

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
            Process(control, payload);
        }, request->payload);
    }
}

void ApplicationRequestProcessor::Process(const std::shared_ptr<RequestControl_s>& control, const ExecuteConsoleCommand_s& command)
{
    auto execution = std::make_shared<CommandExecution>(static_cast<std::size_t>(m_bridge->GetSettings().maxOutputBytes), control->deadline);
    control->execution = execution;
    m_executing.push_back(control);

    try
    {
        const auto capture = ConsoleCaptureScope{&execution->capture};
        m_runner.HandleCommand(command.command, execution);
    }
    catch (const std::exception&)
    {
        execution->errorCode = "internal_failure";
    }

    execution->dispatched = true;
}

void ApplicationRequestProcessor::Process(const std::shared_ptr<RequestControl_s>& control, const GetApplicationStatus_s&)
{
    auto status = ApplicationStatus_s{};
    status.uptimeMs = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - m_started).count();
    for (std::size_t i = 0; i < m_runner.GetAccountCount(); ++i)
    {
        const auto& account = m_runner.GetAccount(i);
        status.accounts.push_back({account.GetName(), account.IsStarted(), account.IsFinished(), account.DescribeStatus()});
    }

    m_bridge->Complete({.id = control->id, .payload = std::move(status)});
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
