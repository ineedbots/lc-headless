#include "pch.hpp"
#include "ScriptPublishedEvent.hpp"

#include "../../../Script/Type/PublishedScriptEvent_s.hpp"
#include "../EventPayloadJson.hpp"

#include <nlohmann/json.hpp>

namespace
{
    std::optional<nlohmann::json> ReadData(std::string_view text)
    {
        if (text.size() > ScriptPublishedEvent::MAX_DATA_BYTES)
        {
            return {};
        }

        auto tooDeep = false;
        auto value = nlohmann::json::parse(text, [&](int depth, nlohmann::json::parse_event_t event, nlohmann::json&)
        {
            if ((event == nlohmann::json::parse_event_t::object_start || event == nlohmann::json::parse_event_t::array_start) && depth >= ScriptPublishedEvent::MAX_DATA_DEPTH)
            {
                tooDeep = true;
                return false;
            }

            return true;
        }, false);

        if (tooDeep || value.is_discarded())
        {
            return {};
        }

        return value;
    }
}

std::optional<std::size_t> ScriptPublishedEvent::Measure(const PublishedScriptEvent_s& payload)
{
    if (payload.name.empty() || payload.name.size() > MAX_NAME_BYTES || !std::ranges::all_of(payload.name, [](unsigned char c)
    {
        return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '.' || c == '_' || c == '-';
    }) ||
        !ReadData(payload.dataJson))
    {
        return {};
    }

    return sizeof(PublishedScriptEvent_s) + payload.name.size() + payload.dataJson.size();
}

void to_json(nlohmann::json& value, const PublishedScriptEvent_s& payload)
{
    auto data = ReadData(payload.dataJson);
    if (!data)
    {
        throw std::invalid_argument{"Invalid script event JSON"};
    }

    value = {{"name", payload.name}, {"data", std::move(*data)}};
}

nlohmann::json ScriptPublishedEvent::Serialize(const PublishedScriptEvent_s& payload)
{
    return payload;
}
