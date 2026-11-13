#pragma once

#include "Type/ApplicationEvent_s.hpp"
#include "Type/EventSubscription_s.hpp"
#include "Type/ApplicationEvents_s.hpp"

class EventProtocol
{
public:
    EventProtocol() = delete;
    static std::variant<EventCommand_s, EventProtocolError_s> Decode(std::string_view text);
    static std::string_view Name(const ApplicationEventPayload& payload);
    static bool IsKnown(std::string_view name);
    static bool RetainsLatest(const ApplicationEventPayload& payload);
    static std::optional<std::size_t> Measure(const ApplicationEventPayload& payload);
    template <typename T>
    static std::optional<std::size_t> Measure(const T& payload)
    {
        using Event = ApplicationEvents_s::Definition<T>;
        const auto bytes = Event::Measure(payload);
        if (!bytes || *bytes > std::numeric_limits<std::size_t>::max() - sizeof(ApplicationEvent_s))
        {
            return {};
        }
        return *bytes + sizeof(ApplicationEvent_s);
    }
    static std::size_t MaxSerializedBytes(const ApplicationEventPayload& payload);
    static std::string Encode(const ApplicationEvent_s& event, std::string_view instance, u64 sequence);
    static std::string Ack(std::string_view id, std::string_view action, std::string_view instance, u64 sequence);
    static std::string Error(std::string_view id, std::string_view code);
    static std::string Snapshot(std::string_view id, std::string_view instance, u64 sequence, const std::vector<std::shared_ptr<const std::string>>& events);
};
