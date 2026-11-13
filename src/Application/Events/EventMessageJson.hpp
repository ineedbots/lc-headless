#pragma once

#include "Type/EventAck_s.hpp"
#include "Type/EventEnvelope_s.hpp"
#include "Type/EventError_s.hpp"
#include "Type/EventSnapshot_s.hpp"

#include <nlohmann/json.hpp>

NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_ONLY_SERIALIZE(EventAck_s, version, type, id, action, instance, sequence)
NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_ONLY_SERIALIZE(EventSnapshot_s, version, type, id, instance, sequence, events)

inline void to_json(nlohmann::json& value, const EventEnvelope_s& event)
{
    value = {{"version", event.version}, {"type", event.type}, {"event", event.event}, {"account", event.account ? nlohmann::json(*event.account) : nlohmann::json(nullptr)}, {"instance", event.instance}, {"sequence", event.sequence}, {"timestamp", event.timestamp}, {"payload", event.payload}};
}

inline void to_json(nlohmann::json& value, const EventError_s& error)
{
    value = {{"version", error.version}, {"type", error.type}, {"id", error.id ? nlohmann::json(*error.id) : nlohmann::json(nullptr)}, {"code", error.code}};
}
