#pragma once

#include "Accounts/Reporting/Type/IdleSummary_s.hpp"
#include "Websockets/Events/Type/EventScope_e.hpp"

#include <nlohmann/json.hpp>

class AccountIdleSummaryEvent
{
public:
    AccountIdleSummaryEvent() = delete;
    using Payload = IdleSummary_s;
    static constexpr std::string_view NAME = "account.idle-summary";
    static constexpr EventScope_e SCOPE = EventScope_e::Account;
    static constexpr bool RETAINS_LATEST = true;
    static constexpr std::size_t MAX_ENVELOPE_BYTES = 4096;

    static std::optional<std::size_t> ValidateAndMeasureOwnedBytes(const Payload& payload);
    static nlohmann::json Serialize(const Payload& payload);
};
