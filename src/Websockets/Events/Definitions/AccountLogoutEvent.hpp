#pragma once

#include "Accounts/Type/AccountLogout_s.hpp"
#include "Websockets/Events/EventLimits.hpp"
#include "Websockets/Events/Type/EventScope_e.hpp"
#include <nlohmann/json.hpp>

class AccountLogoutEvent
{
public:
    AccountLogoutEvent() = delete;
    using Payload = AccountLogout_s;
    static constexpr std::string_view NAME = "account.logout";
    static constexpr EventScope_e SCOPE = EventScope_e::Account;
    static constexpr bool RETAINS_LATEST = false;
    static constexpr std::size_t MAX_ENVELOPE_BYTES = EventLimits::MAX_EVENT_ENVELOPE_BYTES;
    static std::optional<std::size_t> ValidateAndMeasureOwnedBytes(const Payload& payload);
    static nlohmann::json Serialize(const Payload& payload);
};
