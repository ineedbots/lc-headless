#pragma once

#include "EventCatalog_s.hpp"
#include "../Definitions/AccountProgressEvent.hpp"
#include "../Definitions/AccountLogoutEvent.hpp"

using ApplicationEvents_s = EventCatalog_s<AccountProgressEvent, AccountLogoutEvent>;
static_assert(ApplicationEvents_s::IsValid(), "Event names must be unique and event bounds must fit the protocol");
using ApplicationEventPayload = ApplicationEvents_s::Payload;
