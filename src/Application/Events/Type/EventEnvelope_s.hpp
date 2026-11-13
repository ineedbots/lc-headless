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
