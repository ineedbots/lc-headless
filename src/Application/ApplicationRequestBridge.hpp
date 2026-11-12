#pragma once

#include "../Console/CommandExecution.hpp"
#include "../Config/Type/HttpSettings_s.hpp"

struct ExecuteConsoleCommand_s
{
    std::string command;
};

struct GetApplicationStatus_s
{
};

struct AccountStatus_s
{
    std::string name;
    bool started;
    bool finished;
    std::string status;
};

struct ApplicationStatus_s
{
    std::string state = "running";
    s64 uptimeMs = 0;
    std::vector<AccountStatus_s> accounts;
};

struct ConsoleCommandResult_s
{
    std::string output;
    bool outputTruncated = false;
    bool executionStarted = false;
    std::vector<CommandRecipient_s> recipients;
};

struct RequestControl_s
{
    u64 id;
    std::chrono::steady_clock::time_point deadline;
    bool engineDone = false;
    bool httpDone = false;
    bool abandoned = false;
    std::shared_ptr<CommandExecution> execution;
};
using ApplicationRequestPayload = std::variant<ExecuteConsoleCommand_s, GetApplicationStatus_s>;

struct ApplicationRequest_s
{
    std::shared_ptr<RequestControl_s> control;
    ApplicationRequestPayload payload;
};

struct CompletedApplicationRequest_s
{
    u64 id;
    std::string outcome = "completed";
    std::string errorCode;
    std::variant<ConsoleCommandResult_s, ApplicationStatus_s> payload;
};

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
