#pragma once

#include "../Application/Events/ApplicationEventPublisher.hpp"

#include "../Cache/Type/GameCache_s.hpp"
#include "../Console/Logger.hpp"
#include "../Game/State/Type/GameState_s.hpp"
#include "FleetDatabase.hpp"

// Writes one of an account's item containers whenever its contents change, grouped by item id.
//
// Backpack samples follow the bank: while one is open the game swaps in the bank's own backpack, so the
// sample is of that, and bankOpen says so. Changes closer together than the interval are held until it
// passes, so a busy account writes a line every few seconds rather than one per step.
class ItemLog
{
public:
    using Clock = std::chrono::steady_clock;

    enum class Kind_e
    {
        Backpack,
        Equipment,
    };

    // A zero interval records every change.
    ItemLog(const GameCache_s& cache, std::shared_ptr<Logger> logger, std::string accountName, std::shared_ptr<FleetDatabase> database, Kind_e kind, std::chrono::seconds interval, std::shared_ptr<ApplicationEventPublisher> events = {});

    // Called every step while in game.
    void Step(Clock::time_point now, const GameState_s& state);
    void Poll(Clock::time_point now);
    void Flush();

    [[nodiscard]] const std::filesystem::path& GetDatabasePath() const
    {
        return m_database->GetPath();
    }

private:
    // One item's worth of entries: the id, and how many are held across the slots.
    struct Entry_s
    {
        s32 id = 0;
        s32 qty = 0;

        [[nodiscard]] bool operator==(const Entry_s&) const = default;
    };

    struct Contents_s
    {
        u16 com = 0;
        bool bankOpen = false;
        // Occupied and total slots, counted before grouping, so free stays right.
        std::size_t used = 0;
        std::size_t slots = 0;
        // Grouped by id, in id order, so two samples of the same contents compare equal.
        std::vector<Entry_s> items;

        [[nodiscard]] bool operator==(const Contents_s&) const = default;
    };

    struct PendingWrite_s
    {
        std::variant<FleetInventoryLog_s, FleetEquipmentLog_s> record;
        std::future<void> completion;
        Contents_s contents;
        Clock::time_point sampledAt;
    };

    [[nodiscard]] Contents_s Read(const GameState_s& state) const;
    bool WriteSample(Clock::time_point now, const Contents_s& contents);

    const GameCache_s& m_cache;
    std::shared_ptr<Logger> m_logger;
    std::string m_accountName;
    std::shared_ptr<FleetDatabase> m_database;
    Kind_e m_kind;
    std::chrono::seconds m_interval;
    std::optional<Contents_s> m_lastSample;
    // Set by a change the interval held back, so it is written once the interval passes.
    std::optional<Contents_s> m_pending;
    std::optional<Clock::time_point> m_nextSample;
    bool m_writeFailed = false;
    std::optional<Clock::time_point> m_retryAt;
    std::shared_ptr<ApplicationEventPublisher> m_events;
    std::optional<PendingWrite_s> m_write;
};
