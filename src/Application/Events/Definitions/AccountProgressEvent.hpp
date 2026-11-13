#pragma once

#include "../../../Accounts/Type/ProgressReport_s.hpp"
#include "../EventLimits.hpp"
#include "../Type/EventScope_e.hpp"
#include <nlohmann/json.hpp>

class AccountProgressEvent
{
public:
    AccountProgressEvent() = delete;
    using Payload = ProgressReport_s;
    static constexpr std::string_view NAME = "account.progress";
    static constexpr EventScope_e SCOPE = EventScope_e::Account;
    static constexpr bool RETAINS_LATEST = true;
    static constexpr std::size_t MAX_SERIALIZED_BYTES = EventLimits::MAX_EVENT_BYTES;
    static std::optional<std::size_t> Measure(const Payload& payload);
    static nlohmann::json Serialize(const Payload& payload);
};
