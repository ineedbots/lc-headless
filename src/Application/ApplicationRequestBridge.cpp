#include "pch.hpp"
#include "ApplicationRequestBridge.hpp"
ApplicationRequestBridge::ApplicationRequestBridge(HttpSettings_s settings)
    : m_settings{std::move(settings)}
{
    m_completed.reserve(static_cast<std::size_t>(m_settings.maxPendingRequests));
}
std::shared_ptr<RequestControl_s> ApplicationRequestBridge::Reserve()
{
    if (m_closing || m_active.size() >= static_cast<std::size_t>(m_settings.maxPendingRequests))
    {
        return {};
    }
    auto control = std::make_shared<RequestControl_s>();
    control->id = ++m_nextId;
    control->deadline = std::chrono::steady_clock::now() + m_settings.requestTimeoutMs;
    m_active.emplace(control->id, control);
    return control;
}
void ApplicationRequestBridge::Commit(ApplicationRequest_s request)
{
    m_incoming.push_back(std::move(request));
}
std::optional<ApplicationRequest_s> ApplicationRequestBridge::Take()
{
    if (m_incoming.empty())
    {
        return {};
    }
    auto request = std::move(m_incoming.front());
    m_incoming.pop_front();
    return request;
}
void ApplicationRequestBridge::Complete(CompletedApplicationRequest_s result)
{
    const auto it = m_active.find(result.id);
    if (it == m_active.end() || it->second->engineDone)
    {
        return;
    }
    if (!it->second->httpDone)
    {
        m_completed.push_back(std::move(result));
    }
    it->second->engineDone = true;
    Retire(it->first);
}
std::vector<CompletedApplicationRequest_s> ApplicationRequestBridge::TakeCompleted()
{
    if (m_completed.empty())
    {
        return {};
    }
    auto result = std::vector<CompletedApplicationRequest_s>{};
    result.swap(m_completed);
    m_completed.reserve(static_cast<std::size_t>(m_settings.maxPendingRequests));
    return result;
}
void ApplicationRequestBridge::Abandon(u64 id)
{
    const auto it = m_active.find(id);
    if (it == m_active.end())
    {
        return;
    }
    it->second->abandoned = true;
    if (it->second->execution)
    {
        it->second->execution->abandoned = true;
    }
}
void ApplicationRequestBridge::RetireHttp(u64 id)
{
    const auto it = m_active.find(id);
    if (it == m_active.end())
    {
        return;
    }
    it->second->httpDone = true;
    std::erase_if(m_completed, [id](const auto& result)
    {
        return result.id == id;
    });
    Retire(id);
}
void ApplicationRequestBridge::Retire(u64 id)
{
    const auto it = m_active.find(id);
    if (it != m_active.end() && it->second->engineDone && it->second->httpDone)
    {
        m_active.erase(it);
    }
}
void ApplicationRequestBridge::Close()
{
    m_closing = true;
    for (const auto& [id, control] : m_active)
    {
        static_cast<void>(control);
        Abandon(id);
    }
}
