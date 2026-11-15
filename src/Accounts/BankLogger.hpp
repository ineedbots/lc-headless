#pragma once

#include "../Application/Events/ApplicationEventPublisher.hpp"

#include "../Cache/Type/GameCache_s.hpp"
#include "../Console/Logger.hpp"
#include "../Game/State/Type/GameState_s.hpp"
#include "FleetDatabase.hpp"

// Writes a bank's contents whenever one opens. Deliberately
// open-only: deposits and withdrawals made while the bank stays open aren't re-read, so each entry is the
// bank as it was when it opened. The last line is the bank's current contents.
class BankLogger
{
public:
    using Clock = std::chrono::steady_clock;

    BankLogger(const GameCache_s& cache, std::shared_ptr<Logger> logger, std::string accountName, std::shared_ptr<FleetDatabase> database, std::shared_ptr<ApplicationEventPublisher> events = {});

    // Called every step while in game. Records on the closed -> open edge only.
    void Step(Clock::time_point now, const GameState_s& state);
    void Poll(Clock::time_point now);
    void Flush();
    void Step(const GameState_s& state)
    {
        Step(Clock::now(), state);
    }

    [[nodiscard]] const std::filesystem::path& GetDatabasePath() const
    {
        return m_database->GetPath();
    }

private:
    struct Snapshot_s
    {
        FleetBankLog_s record;
        std::string summary;
    };

    struct PendingWrite_s
    {
        Snapshot_s snapshot;
        std::future<void> completion;
    };

    [[nodiscard]] std::optional<Snapshot_s> Read(const GameState_s& state) const;
    bool WriteSample(Clock::time_point now, Snapshot_s snapshot);

    const GameCache_s& m_cache;
    std::shared_ptr<Logger> m_logger;
    std::string m_accountName;
    std::shared_ptr<FleetDatabase> m_database;
    bool m_wasOpen = false;
    // So a folder that can't be written is reported once, not on every open.
    bool m_writeFailed = false;
    std::optional<Clock::time_point> m_retryAt;
    std::shared_ptr<ApplicationEventPublisher> m_events;
    std::optional<PendingWrite_s> m_write;
    std::deque<Snapshot_s> m_pendingSnapshots;
};
