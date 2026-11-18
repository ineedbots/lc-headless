#include "pch.hpp"
#include "ApplicationRequestProcessor.hpp"

#include "ApplicationRequestBridge.hpp"
#include "Operations/ConsoleCommandCompletion.hpp"
#include "Type/RequestControl_s.hpp"
#include "Type/CompletedApplicationRequest_s.hpp"
#include "Type/ApplicationRequest_s.hpp"
#include "../../Accounts/AccountRunner.hpp"
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
        auto result = ConsoleCommandCompletion::TryComplete(*control, m_bridge->IsClosing());
        if (result)
        {
            m_bridge->Complete(std::move(*result));
        }
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
