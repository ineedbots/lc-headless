#include "pch.hpp"
#include "ApplicationStartedEvent.hpp"

#include "../../Type/ApplicationStarted_s.hpp"

#include <nlohmann/json.hpp>

std::optional<std::size_t> ApplicationStartedEvent::Measure(const ApplicationStarted_s&)
{
    return sizeof(ApplicationStarted_s);
}

nlohmann::json ApplicationStartedEvent::Serialize(const ApplicationStarted_s&)
{
    return nlohmann::json::object();
}
