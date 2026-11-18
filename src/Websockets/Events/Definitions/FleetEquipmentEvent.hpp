#pragma once

#include "Accounts/Reporting/Type/FleetEquipmentLog_s.hpp"
#include "Websockets/Events/FleetEventPayload.hpp"
#include "Websockets/Events/EventLimits.hpp"
#include "Websockets/Events/Type/EventScope_e.hpp"

class FleetEquipmentEvent : public FleetEventPayload<FleetEquipmentLog_s>
{
public:
    FleetEquipmentEvent() = delete;
    using Payload = FleetEquipmentLog_s;
    static constexpr std::string_view NAME = "fleet.equipment";
    static constexpr EventScope_e SCOPE = EventScope_e::Account;
    static constexpr bool RETAINS_LATEST = false;
    static constexpr std::size_t MAX_ENVELOPE_BYTES = EventLimits::MAX_EVENT_ENVELOPE_BYTES;
};
