#pragma once

#include <nlohmann/json.hpp>

struct EventAck_s
{
    s32 version = 1;
    std::string type = "ack";
    std::string id;
    std::string action;
    std::string instance;
    u64 sequence = 0;
};

NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_ONLY_SERIALIZE(EventAck_s, version, type, id, action, instance, sequence)
