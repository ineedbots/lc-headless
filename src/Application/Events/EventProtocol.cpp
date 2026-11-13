#include "pch.hpp"
#include "EventProtocol.hpp"

#include "Type/ApplicationEvent_s.hpp"
#include "Type/EventSubscription_s.hpp"
#include "Type/ApplicationEvents_s.hpp"
#include "EventLimits.hpp"
#include "Type/EventScope_e.hpp"
#include "Type/EventAck_s.hpp"
#include "Type/EventEnvelope_s.hpp"
#include "Type/EventError_s.hpp"
#include "Type/EventSnapshot_s.hpp"
#include "EventMessageJson.hpp"

#include <nlohmann/json.hpp>

namespace
{
    bool IsId(std::string_view id)
    {
        return !id.empty() && id.size() <= 64 && std::ranges::all_of(id, [](unsigned char c)
        {
            return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '_' || c == '-';
        });
    }

    bool ReadList(const nlohmann::json& value, std::vector<std::string>& out)
    {
        if (!value.is_array() || value.size() > EventLimits::MAX_FILTER_ENTRIES)
        {
            return false;
        }

        for (const auto& entry : value)
        {
            if (!entry.is_string())
            {
                return false;
            }

            auto name = entry.get<std::string>();
            if (name.empty() || name.size() > EventLimits::MAX_FILTER_NAME_BYTES || std::ranges::find(out, name) != out.end())
            {
                return false;
            }

            out.push_back(std::move(name));
        }

        return true;
    }
}

std::variant<EventCommand_s, EventProtocolError_s> EventProtocol::Decode(std::string_view text)
{
    auto id = std::string{};
    try
    {
        const auto value = nlohmann::json::parse(text);
        if (!value.is_object())
        {
            return EventProtocolError_s{.code = "invalid_message"};
        }

        if (value.contains("id") && value["id"].is_string() && IsId(value["id"].get_ref<const std::string&>()))
        {
            id = value["id"].get<std::string>();
        }

        if (!value.contains("version") || !value["version"].is_number_integer() || value["version"] != 1)
        {
            return EventProtocolError_s{id, "unsupported_version"};
        }

        if (!value.contains("type") || !value["type"].is_string())
        {
            return EventProtocolError_s{id, "invalid_message"};
        }

        auto command = EventCommand_s{value["type"].get<std::string>(), {.id = id}};
        if (command.action != "subscribe" && command.action != "unsubscribe")
        {
            return EventProtocolError_s{id, "unsupported_type"};
        }

        for (const auto& [key, field] : value.items())
        {
            static_cast<void>(field);
            if (key != "version" && key != "type" && key != "id" && !(command.action == "subscribe" && (key == "events" || key == "accounts")))
            {
                return EventProtocolError_s{id, "unknown_field"};
            }
        }

        if (id.empty())
        {
            return EventProtocolError_s{id, "invalid_id"};
        }

        if (command.action == "subscribe")
        {
            auto& subscription = command.subscription;
            if (!value.contains("events") || !ReadList(value["events"], subscription.events) || subscription.events.empty() ||
                (value.contains("accounts") && !ReadList(value["accounts"], subscription.accounts)) ||
                !std::ranges::all_of(subscription.events, IsKnown))
            {
                return EventProtocolError_s{id, "invalid_subscription"};
            }
        }

        return command;
    }
    catch (const nlohmann::json::exception&)
    {
        return EventProtocolError_s{id, "invalid_message"};
    }
}

std::string_view EventProtocol::Name(const ApplicationEventPayload& payload)
{
    return std::visit([](const auto& value) -> std::string_view
    {
        using Event = ApplicationEvents_s::Definition<std::decay_t<decltype(value)>>;
        return Event::NAME;
    }, payload);
}

bool EventProtocol::IsKnown(std::string_view name)
{
    return ApplicationEvents_s::IsKnown(name);
}

bool EventProtocol::RetainsLatest(const ApplicationEventPayload& payload)
{
    return std::visit([](const auto& value)
    {
        using Event = ApplicationEvents_s::Definition<std::decay_t<decltype(value)>>;
        return Event::RETAINS_LATEST;
    }, payload);
}

std::optional<std::size_t> EventProtocol::Measure(const ApplicationEventPayload& payload)
{
    return std::visit([](const auto& value)
    {
        return Measure(value);
    }, payload);
}

std::string EventProtocol::Encode(const ApplicationEvent_s& event, std::string_view instance, u64 sequence)
{
    auto payload = std::visit([](const auto& value) -> nlohmann::json
    {
        using Event = ApplicationEvents_s::Definition<std::decay_t<decltype(value)>>;
        return Event::Serialize(value);
    }, event.payload);

    return nlohmann::json(EventEnvelope_s{
                              .event = std::string{Name(event.payload)},
                              .account = event.account,
                              .instance = std::string{instance},
                              .sequence = sequence,
                              .timestamp = std::format("{:%FT%T}Z", std::chrono::floor<std::chrono::seconds>(event.timestamp)),
                              .payload = std::move(payload)})
        .dump();
}

std::string EventProtocol::Ack(std::string_view id, std::string_view action, std::string_view instance, u64 sequence)
{
    return nlohmann::json(EventAck_s{.id = std::string{id}, .action = std::string{action}, .instance = std::string{instance}, .sequence = sequence}).dump();
}

std::string EventProtocol::Error(std::string_view id, std::string_view code)
{
    return nlohmann::json(EventError_s{.id = id.empty() ? std::nullopt : std::optional{std::string{id}}, .code = std::string{code}}).dump();
}

std::string EventProtocol::Snapshot(std::string_view id, std::string_view instance, u64 sequence, const std::vector<std::shared_ptr<const std::string>>& events)
{
    auto snapshot = EventSnapshot_s{.id = std::string{id}, .instance = std::string{instance}, .sequence = sequence};
    snapshot.events.reserve(events.size());
    for (const auto& event : events)
    {
        snapshot.events.push_back(nlohmann::json::parse(*event));
    }

    return nlohmann::json(snapshot).dump();
}

std::size_t EventProtocol::MaxSerializedBytes(const ApplicationEventPayload& payload)
{
    return std::visit([](const auto& value)
    {
        using Event = ApplicationEvents_s::Definition<std::decay_t<decltype(value)>>;
        return Event::MAX_SERIALIZED_BYTES;
    }, payload);
}

EventScope_e EventProtocol::Scope(const ApplicationEventPayload& payload)
{
    return std::visit([](const auto& value)
    {
        using Event = ApplicationEvents_s::Definition<std::decay_t<decltype(value)>>;
        return Event::SCOPE;
    }, payload);
}
