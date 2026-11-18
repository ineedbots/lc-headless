#pragma once

#include <nlohmann/json.hpp>

class FleetLogEvent
{
public:
    FleetLogEvent() = delete;

    static constexpr std::size_t ENVELOPE_RESERVE_BYTES = 1024;
    static std::optional<std::size_t> ValidateAndMeasureJsonBytes(const nlohmann::ordered_json& record);
    static nlohmann::json Serialize(const nlohmann::ordered_json& record);
};
