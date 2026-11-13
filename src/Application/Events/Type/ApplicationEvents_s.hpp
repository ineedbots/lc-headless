#pragma once

#include "EventCatalog_s.hpp"
#include "../Definitions/AccountProgressEvent.hpp"
#include "../Definitions/AccountLogoutEvent.hpp"
#include "../Definitions/ApplicationStartedEvent.hpp"
#include "../Definitions/ScriptPublishedEvent.hpp"

#include "../Definitions/FleetExperienceEvent.hpp"
#include "../Definitions/FleetBankEvent.hpp"
#include "../Definitions/FleetInventoryEvent.hpp"
#include "../Definitions/FleetEquipmentEvent.hpp"

using ApplicationEvents_s = EventCatalog_s<AccountProgressEvent, AccountLogoutEvent, ApplicationStartedEvent, ScriptPublishedEvent, FleetExperienceEvent, FleetBankEvent, FleetInventoryEvent, FleetEquipmentEvent>;
static_assert(ApplicationEvents_s::IsValid(), "Event names must be unique and event bounds must fit the protocol");
using ApplicationEventPayload = ApplicationEvents_s::Payload;
