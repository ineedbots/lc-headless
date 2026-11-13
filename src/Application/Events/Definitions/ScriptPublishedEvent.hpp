#pragma once

#include "../../../Script/Type/PublishedScriptEvent_s.hpp"
#include "../EventLimits.hpp"
#include "../Type/EventScope_e.hpp"

#include <nlohmann/json.hpp>

class ScriptPublishedEvent
{
public:
    ScriptPublishedEvent() = delete;
    using Payload = PublishedScriptEvent_s;
    static constexpr std::string_view NAME = "script.event";
    static constexpr EventScope_e SCOPE = EventScope_e::Account;
    static constexpr bool RETAINS_LATEST = false;
    static constexpr std::size_t MAX_SERIALIZED_BYTES = EventLimits::MAX_EVENT_BYTES;
    static constexpr std::size_t MAX_NAME_BYTES = 64;
    static constexpr std::size_t MAX_DATA_BYTES = 4096;
    static constexpr int MAX_DATA_DEPTH = 16;

    static std::optional<std::size_t> Measure(const Payload& payload);
    static nlohmann::json Serialize(const Payload& payload);
};
