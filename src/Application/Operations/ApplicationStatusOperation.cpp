#include "pch.hpp"
#include "ApplicationStatusOperation.hpp"

#include "../../Accounts/Type/AccountStatus_s.hpp"
#include "../../Accounts/AccountControl.hpp"
#include "../Type/ApplicationStatus_s.hpp"
#include "../Type/GetApplicationStatus_s.hpp"
#include "../Type/RequestControl_s.hpp"
#include "../Type/ApplicationRequestContext_s.hpp"

std::optional<ApplicationStatus_s> ApplicationStatusOperation::Execute(const ApplicationRequestContext_s& context, const std::shared_ptr<RequestControl_s>&, const GetApplicationStatus_s&)
{
    auto status = ApplicationStatus_s{};
    status.uptimeMs = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - context.started).count();

    for (std::size_t i = 0; i < context.runner.GetAccountCount(); ++i)
    {
        status.accounts.push_back(context.runner.GetAccountStatus(i));
    }

    return status;
}
