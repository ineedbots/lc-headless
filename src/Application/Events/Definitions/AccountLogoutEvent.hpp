#pragma once

#include "../../../Accounts/Type/AccountLogout_s.hpp"
#include "../EventLimits.hpp"
#include <nlohmann/json.hpp>

class AccountLogoutEvent
{
public:
    AccountLogoutEvent() = delete;
    using Payload = AccountLogout_s;
    static constexpr std::string_view NAME = "account.logout";
    static constexpr bool RETAINS_LATEST = false;
    static constexpr std::size_t MAX_SERIALIZED_BYTES = EventLimits::MAX_EVENT_BYTES;
    static std::optional<std::size_t> Measure(const Payload& payload);
    static nlohmann::json Serialize(const Payload& payload);
};
