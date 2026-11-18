#pragma once

#include "FleetLogEvent.hpp"

#include <nlohmann/json.hpp>

template <typename TRecord>
class FleetEventPayload
{
public:
    FleetEventPayload() = delete;

    static std::optional<std::size_t> ValidateAndMeasureOwnedBytes(const TRecord& payload)
    {
        const auto bytes = FleetLogEvent::ValidateAndMeasureJsonBytes(nlohmann::ordered_json(payload));
        return bytes ? std::optional{*bytes + sizeof(TRecord)} : std::nullopt;
    }

    static nlohmann::json Serialize(const TRecord& payload)
    {
        return FleetLogEvent::Serialize(nlohmann::ordered_json(payload));
    }
};
