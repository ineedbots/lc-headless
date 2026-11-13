#pragma once

#include "../../../Accounts/Type/ProgressReport_s.hpp"
#include "../../../Accounts/Type/AccountLogout_s.hpp"

using ApplicationEventPayload = std::variant<ProgressReport_s, AccountLogout_s>;

struct ApplicationEvent_s
{
    std::string account;
    ApplicationEventPayload payload;
    std::chrono::system_clock::time_point timestamp = std::chrono::system_clock::now();
};
