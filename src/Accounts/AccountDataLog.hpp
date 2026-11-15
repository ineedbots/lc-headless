#pragma once

#include "../Application/Events/ApplicationEventPublisher.hpp"
#include "../Cache/Type/GameCache_s.hpp"
#include "../Console/Logger.hpp"
#include "../Game/GameClient.hpp"
#include "../Game/State/Type/GameState_s.hpp"
#include "FleetDatabase.hpp"

#include <nlohmann/json.hpp>

class AccountDataLog
{
public:
    using Clock = std::chrono::steady_clock;

    AccountDataLog(const GameCache_s& cache, std::shared_ptr<Logger> logger, std::string accountName, std::shared_ptr<FleetDatabase> database, std::chrono::seconds interval, std::shared_ptr<ApplicationEventPublisher> events = {});
    void Step(Clock::time_point now, const GameState_s& state, ClientStatus_e status);

    [[nodiscard]] const std::filesystem::path& GetDatabasePath() const
    {
        return m_database->GetPath();
    }

private:
    [[nodiscard]] nlohmann::ordered_json Read(const GameState_s& state, ClientStatus_e status) const;

    const GameCache_s& m_cache;
    std::shared_ptr<Logger> m_logger;
    std::string m_accountName;
    std::shared_ptr<FleetDatabase> m_database;
    std::chrono::seconds m_interval;
    std::shared_ptr<ApplicationEventPublisher> m_events;
    std::optional<nlohmann::ordered_json> m_lastSample;
    std::optional<Clock::time_point> m_nextSample;
    bool m_writeFailed = false;
};
