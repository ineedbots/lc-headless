#pragma once

#include "Type/ApplicationEvent_s.hpp"
#include "ApplicationEventPublisher.hpp"
#include "EventLimits.hpp"
#include "Type/EventSubscription_s.hpp"

class ApplicationEventBridge : public ApplicationEventPublisher
{
public:
    static constexpr std::size_t MAX_MESSAGE_BYTES = EventLimits::MAX_MESSAGE_BYTES;
    static constexpr std::size_t MAX_EVENT_BYTES = EventLimits::MAX_EVENT_BYTES;
    static constexpr std::size_t MAX_OUTBOX_BYTES = EventLimits::MAX_OUTBOX_BYTES;
    static constexpr std::size_t MAX_OUTBOX_ITEMS = EventLimits::MAX_OUTBOX_ITEMS;
    static constexpr std::size_t MAX_JOURNAL_ITEMS = EventLimits::MAX_JOURNAL_ITEMS;
    static constexpr std::size_t MAX_JOURNAL_BYTES = EventLimits::MAX_JOURNAL_BYTES;

    struct Diagnostics_s
    {
        std::size_t connections = 0;
        std::size_t subscriptions = 0;
        std::size_t journalItems = 0;
        std::size_t journalBytes = 0;
        u64 rejectedSubscriptions = 0;
        u64 publisherResets = 0;
        u64 overflowDisconnects = 0;
        std::size_t outgoingItems = 0;
        std::size_t outgoingBytes = 0;
        std::size_t journalHighWaterItems = 0;
        std::size_t journalHighWaterBytes = 0;
        std::size_t clientHighWaterItems = 0;
        std::size_t clientHighWaterBytes = 0;
        s64 maxDeliveryLagMs = 0;
    };

    explicit ApplicationEventBridge(std::vector<std::string> accounts = {});
    u64 Connect();
    void Disconnect(u64 client);
    void Enqueue(u64 client, std::string message);
    // Only producers and runner safe points call Publish/Service.
    using ApplicationEventPublisher::Publish;
    bool Publish(ApplicationEvent_s event) override;
    void Service();
    void Stop();
    bool HasIncoming() const;
    bool IsClosing(u64 client) const;
    bool IsStopping() const override;
    std::shared_ptr<const std::string> Front(u64 client) const;
    void Pop(u64 client);
    Diagnostics_s GetDiagnostics() const;

private:
    struct Client_s
    {
        std::vector<EventSubscription_s> subscriptions;
        std::deque<std::shared_ptr<const std::string>> outbox;
        std::size_t bytes = 0;
        bool closing = false;
    };

    struct Incoming_s
    {
        u64 client;
        std::string message;
    };

    struct JournalEntry_s
    {
        std::variant<Incoming_s, ApplicationEvent_s> value;
        std::size_t bytes;
        std::chrono::steady_clock::time_point created = std::chrono::steady_clock::now();
    };

    struct CachedEvent_s
    {
        std::string name;
        std::shared_ptr<const std::string> text;
    };

    struct Fanout_s
    {
        std::optional<std::string> account;
        CachedEvent_s event;
        u64 cursor = 0;
        std::chrono::steady_clock::time_point created;
    };

    static bool Matches(const EventSubscription_s& subscription, std::string_view event, const std::optional<std::string>& account);
    void Apply(Incoming_s incoming);
    void Send(u64 client, std::shared_ptr<const std::string> text);
    void Overflow(u64 client);
    void ResetPublisher();
    void RejectPublication() override;
    bool Append(JournalEntry_s entry);

    std::vector<std::string> m_accounts;
    std::string m_instance;
    u64 m_sequence = 0;
    u64 m_nextClient = 0;
    bool m_stopping = false;
    std::map<u64, Client_s> m_clients;
    std::deque<JournalEntry_s> m_journal;
    std::size_t m_journalBytes = 0;
    std::map<std::pair<std::optional<std::string>, std::string>, CachedEvent_s> m_latest;
    std::optional<Fanout_s> m_fanout;
    Diagnostics_s m_diagnostics;
};
