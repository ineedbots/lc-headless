#pragma once

class EventLimits
{
public:
    EventLimits() = delete;
    static constexpr std::size_t MAX_ACCOUNTS = 16;
    static constexpr std::size_t MAX_FILTER_NAME_BYTES = 128;
    static constexpr std::size_t MAX_ACCOUNT_BYTES = MAX_FILTER_NAME_BYTES;
    static constexpr std::size_t MAX_CONNECTIONS = 128;
    static constexpr std::size_t MAX_FILTER_ENTRIES = 16;
    static constexpr std::size_t MAX_SUBSCRIPTIONS = 16;
    static constexpr std::size_t MAX_MESSAGE_BYTES = 4096;
    static constexpr std::size_t MAX_EVENT_BYTES = 8192;
    static constexpr std::size_t MAX_OUTBOX_BYTES = 262144;
    static constexpr std::size_t MAX_OUTBOX_ITEMS = 64;
    static constexpr std::size_t MAX_JOURNAL_ITEMS = 256;
    static constexpr std::size_t MAX_JOURNAL_BYTES = 1048576;
    // Reserve the subscription framing and ack alongside a full snapshot.
    static constexpr std::size_t SNAPSHOT_OVERHEAD_BYTES = 1024;
};
