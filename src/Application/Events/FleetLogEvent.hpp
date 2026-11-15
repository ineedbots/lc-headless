#pragma once

#include <nlohmann/json.hpp>

class FleetLogEvent
{
public:
    FleetLogEvent() = delete;
    static std::optional<std::size_t> Measure(const nlohmann::ordered_json& record);
    static nlohmann::json Serialize(const nlohmann::ordered_json& record);
};
