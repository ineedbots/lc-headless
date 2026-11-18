#pragma once

#include "Database/Type/FleetAccountDataLog_s.hpp"
#include "Websockets/Events/FleetEventPayload.hpp"
#include "Websockets/Events/EventLimits.hpp"
#include "Websockets/Events/Type/EventScope_e.hpp"

class FleetAccountDataEvent : public FleetEventPayload<FleetAccountDataLog_s>
{
public:
    FleetAccountDataEvent() = delete;

    using Payload = FleetAccountDataLog_s;

    static constexpr std::string_view NAME = "fleet.account-data";
    static constexpr EventScope_e SCOPE = EventScope_e::Account;
    static constexpr bool RETAINS_LATEST = false;
    static constexpr std::size_t MAX_ENVELOPE_BYTES = EventLimits::MAX_EVENT_ENVELOPE_BYTES;
};
