#pragma once
#include "ApplicationRequestBridge.hpp"
#include "../Accounts/AccountRunner.hpp"
class ApplicationRequestProcessor
{
public:
    ApplicationRequestProcessor(AccountRunner& runner, std::shared_ptr<ApplicationRequestBridge> bridge,
                                std::chrono::steady_clock::time_point started);
    void Dispatch();
    void Finalize();
    void Stop();

private:
    void Process(const std::shared_ptr<RequestControl_s>& control, const ExecuteConsoleCommand_s& command);
    void Process(const std::shared_ptr<RequestControl_s>& control, const GetApplicationStatus_s& request);
    AccountRunner& m_runner;
    std::shared_ptr<ApplicationRequestBridge> m_bridge;
    std::chrono::steady_clock::time_point m_started;
    std::vector<std::shared_ptr<RequestControl_s>> m_executing;
};
