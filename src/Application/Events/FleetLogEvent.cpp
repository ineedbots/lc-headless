#include "pch.hpp"
#include "FleetLogEvent.hpp"

#include "EventLimits.hpp"

#include <nlohmann/json.hpp>

std::optional<std::size_t> FleetLogEvent::Measure(const nlohmann::ordered_json& record)
{
    // Leave room for the envelope, including a maximally escaped account name.
    if (!record.is_object())
    {
        return {};
    }

    const auto serialized = record.dump(-1, ' ', false, nlohmann::json::error_handler_t::replace);
    if (serialized.size() > EventLimits::MAX_EVENT_BYTES - 1024)
    {
        return {};
    }

    return serialized.size();
}

nlohmann::json FleetLogEvent::Serialize(const nlohmann::ordered_json& record)
{
    const auto serialized = record.dump(-1, ' ', false, nlohmann::json::error_handler_t::replace);
    return nlohmann::json::parse(serialized);
}
