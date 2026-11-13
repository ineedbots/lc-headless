#include "pch.hpp"
#include "FleetLogEvent.hpp"

#include "EventLimits.hpp"

#include <nlohmann/json.hpp>

std::optional<std::size_t> FleetLogEvent::Measure(std::string_view recordJson)
{
    // Leave room for the envelope, including a maximally escaped account name.
    if (recordJson.size() > EventLimits::MAX_EVENT_BYTES - 1024)
    {
        return {};
    }

    const auto record = nlohmann::json::parse(recordJson, nullptr, false);
    if (!record.is_object() || record.dump().size() > EventLimits::MAX_EVENT_BYTES - 1024)
    {
        return {};
    }

    return recordJson.size();
}

nlohmann::json FleetLogEvent::Serialize(std::string_view recordJson)
{
    return nlohmann::json::parse(recordJson);
}
