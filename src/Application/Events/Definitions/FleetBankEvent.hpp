#pragma once

#include "../../../Accounts/Type/FleetBankLog_s.hpp"
#include "../FleetLogEvent.hpp"
#include "../EventLimits.hpp"
#include "../Type/EventScope_e.hpp"

#include <nlohmann/json.hpp>

class FleetBankEvent
{
public:
    FleetBankEvent() = delete;
    using Payload = FleetBankLog_s;
    static constexpr std::string_view NAME = "fleet.bank";
    static constexpr EventScope_e SCOPE = EventScope_e::Account;
    static constexpr bool RETAINS_LATEST = false;
    static constexpr std::size_t MAX_SERIALIZED_BYTES = EventLimits::MAX_EVENT_BYTES;
    static std::optional<std::size_t> Measure(const Payload& payload)
    {
        const auto record = nlohmann::ordered_json(payload);
        const auto bytes = FleetLogEvent::Measure(record);
        return bytes ? std::optional{*bytes + sizeof(Payload)} : std::nullopt;
    }

    static nlohmann::json Serialize(const Payload& payload)
    {
        return FleetLogEvent::Serialize(nlohmann::ordered_json(payload));
    }
};
