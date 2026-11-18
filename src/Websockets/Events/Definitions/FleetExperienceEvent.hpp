#pragma once

#include "Accounts/Reporting/Type/FleetExperienceLog_s.hpp"
#include "Websockets/Events/FleetEventPayload.hpp"
#include "Websockets/Events/EventLimits.hpp"
#include "Websockets/Events/Type/EventScope_e.hpp"

class FleetExperienceEvent : public FleetEventPayload<FleetExperienceLog_s>
{
public:
    FleetExperienceEvent() = delete;
    using Payload = FleetExperienceLog_s;
    static constexpr std::string_view NAME = "fleet.experience";
    static constexpr EventScope_e SCOPE = EventScope_e::Account;
    static constexpr bool RETAINS_LATEST = false;
    static constexpr std::size_t MAX_ENVELOPE_BYTES = EventLimits::MAX_EVENT_ENVELOPE_BYTES;
};
