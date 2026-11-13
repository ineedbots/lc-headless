#pragma once

#include <nlohmann/json.hpp>

class FleetLogEvent
{
public:
    FleetLogEvent() = delete;
    static std::optional<std::size_t> Measure(std::string_view recordJson);
    static nlohmann::json Serialize(std::string_view recordJson);
};
