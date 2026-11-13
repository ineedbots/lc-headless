#pragma once

#include <nlohmann/json.hpp>

struct EventSnapshot_s
{
    s32 version = 1;
    std::string type = "snapshot";
    std::string id;
    std::string instance;
    u64 sequence = 0;
    std::vector<nlohmann::json> events;
};
