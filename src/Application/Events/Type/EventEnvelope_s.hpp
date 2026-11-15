#pragma once

#include <nlohmann/json.hpp>

struct EventEnvelope_s
{
    s32 version = 1;
    std::string type = "event";
    std::string event;
    std::optional<std::string> account;
    std::string instance;
    u64 sequence = 0;
    std::string timestamp;
    nlohmann::json payload;
};

inline void to_json(nlohmann::json& value, const EventEnvelope_s& event)
{
    value = {{"version", event.version}, {"type", event.type}, {"event", event.event}, {"account", event.account ? nlohmann::json(*event.account) : nlohmann::json(nullptr)}, {"instance", event.instance}, {"sequence", event.sequence}, {"timestamp", event.timestamp}, {"payload", event.payload}};
}
