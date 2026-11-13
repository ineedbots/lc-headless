#pragma once

#include "../../Type/ApplicationStarted_s.hpp"
#include "../Type/EventScope_e.hpp"

#include <nlohmann/json.hpp>

class ApplicationStartedEvent
{
public:
    ApplicationStartedEvent() = delete;
    using Payload = ApplicationStarted_s;
    static constexpr std::string_view NAME = "application.started";
    static constexpr EventScope_e SCOPE = EventScope_e::Global;
    static constexpr bool RETAINS_LATEST = true;
    static constexpr std::size_t MAX_SERIALIZED_BYTES = 512;

    static std::optional<std::size_t> Measure(const Payload& payload);
    static nlohmann::json Serialize(const Payload& payload);
};
