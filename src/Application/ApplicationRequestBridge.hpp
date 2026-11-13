#pragma once

#include "Type/ApplicationRequest_s.hpp"
#include "Type/CompletedApplicationRequest_s.hpp"
#include "Type/RequestControl_s.hpp"
#include "../Config/Type/HttpSettings_s.hpp"

class ApplicationRequestBridge
{
public:
    explicit ApplicationRequestBridge(HttpSettings_s settings);
    std::shared_ptr<RequestControl_s> Reserve();
    void Commit(ApplicationRequest_s request);
    std::optional<ApplicationRequest_s> Take();
    void Complete(CompletedApplicationRequest_s result);
    std::vector<CompletedApplicationRequest_s> TakeCompleted();
    void Abandon(u64 id);
    void RetireHttp(u64 id);
    void Close();
    bool IsClosing() const
    {
        return m_closing;
    }

    bool HasIncoming() const
    {
        return !m_incoming.empty();
    }

    std::size_t Outstanding() const
    {
        return m_active.size();
    }

    const HttpSettings_s& GetSettings() const
    {
        return m_settings;
    }

private:
    void Retire(u64 id);
    HttpSettings_s m_settings;
    u64 m_nextId = 0;
    bool m_closing = false;
    std::unordered_map<u64, std::shared_ptr<RequestControl_s>> m_active;
    std::deque<ApplicationRequest_s> m_incoming;
    std::vector<CompletedApplicationRequest_s> m_completed;
};
