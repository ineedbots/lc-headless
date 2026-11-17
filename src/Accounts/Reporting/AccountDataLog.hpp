#pragma once

#include "Websockets/Events/ApplicationEventPublisher.hpp"
#include "Cache/Type/GameCache_s.hpp"
#include "Console/Logger.hpp"
#include "Game/GameClient.hpp"
#include "Game/State/Type/GameState_s.hpp"
#include "Database/FleetDatabase.hpp"

class AccountDataLog
{
public:
    using Clock = std::chrono::steady_clock;

    AccountDataLog(const GameCache_s& cache, std::shared_ptr<Logger> logger, std::string accountName, std::shared_ptr<FleetDatabase> database, std::chrono::seconds interval, std::shared_ptr<ApplicationEventPublisher> events = {});
    void Step(Clock::time_point now, const GameState_s& state, ClientStatus_e status);
    void Poll(Clock::time_point now);
    void Flush();

    [[nodiscard]] const std::filesystem::path& GetDatabasePath() const
    {
        return m_database->GetPath();
    }

private:
    struct PendingWrite_s
    {
        FleetAccountDataLog_s record;
        std::future<void> completion;
        bool sessionTransition = false;
    };

    [[nodiscard]] FleetAccountDataLog_s Read(const GameState_s& state, ClientStatus_e status) const;

    const GameCache_s& m_cache;
    std::shared_ptr<Logger> m_logger;
    std::string m_accountName;
    std::shared_ptr<FleetDatabase> m_database;
    std::chrono::seconds m_interval;
    std::shared_ptr<ApplicationEventPublisher> m_events;
    std::optional<PendingWrite_s> m_write;
    std::deque<FleetAccountDataLog_s> m_deferredSessions;
    std::optional<std::pair<std::string, bool>> m_lastObservedSession;
    std::optional<FleetAccountDataLog_s> m_lastSample;
    std::optional<Clock::time_point> m_nextSample;
    bool m_writeFailed = false;
};
