#pragma once

#include "Accounts/Reporting/Type/ProgressReport_s.hpp"
#include "Websockets/Events/EventLimits.hpp"
#include "Websockets/Events/Type/EventScope_e.hpp"
#include <nlohmann/json.hpp>

class AccountProgressEvent
{
public:
    AccountProgressEvent() = delete;
    using Payload = ProgressReport_s;
    static constexpr std::string_view NAME = "account.progress";
    static constexpr EventScope_e SCOPE = EventScope_e::Account;
    static constexpr bool RETAINS_LATEST = true;
    static constexpr std::size_t MAX_ROWS = 64;
    static constexpr std::size_t MAX_TOTAL_ROW_TEXT_BYTES = 4096;
    static constexpr std::size_t MAX_ENVELOPE_BYTES = EventLimits::MAX_EVENT_ENVELOPE_BYTES;
    static std::optional<std::size_t> ValidateAndMeasureOwnedBytes(const Payload& payload);
    static nlohmann::json Serialize(const Payload& payload);
};
