#pragma once

#include "EventCatalog_s.hpp"
#include "Websockets/Events/Definitions/AccountIdleSummaryEvent.hpp"
#include "Websockets/Events/Definitions/AccountProgressEvent.hpp"
#include "Websockets/Events/Definitions/AccountLogoutEvent.hpp"
#include "Websockets/Events/Definitions/ApplicationStartedEvent.hpp"
#include "Websockets/Events/Definitions/ScriptPublishedEvent.hpp"

#include "Websockets/Events/Definitions/FleetExperienceEvent.hpp"
#include "Websockets/Events/Definitions/FleetBankEvent.hpp"
#include "Websockets/Events/Definitions/FleetInventoryEvent.hpp"
#include "Websockets/Events/Definitions/FleetAccountDataEvent.hpp"
#include "Websockets/Events/Definitions/FleetEquipmentEvent.hpp"

using ApplicationEvents_s = EventCatalog_s<AccountProgressEvent, AccountIdleSummaryEvent, AccountLogoutEvent, ApplicationStartedEvent, ScriptPublishedEvent, FleetExperienceEvent, FleetBankEvent, FleetInventoryEvent, FleetEquipmentEvent, FleetAccountDataEvent>;
static_assert(ApplicationEvents_s::IsValid(), "Event names must be unique and event bounds must fit the protocol");
using ApplicationEventPayload = ApplicationEvents_s::Payload;
