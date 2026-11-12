#pragma once

#include "../Cache/Type/GameCache_s.hpp"
#include "../Config/Type/AccountConfig_s.hpp"
#include "../Config/Type/Config_s.hpp"
#include "../Console/Logger.hpp"
#include "../Game/GameClient.hpp"
#include "../Game/State/Type/GameState_s.hpp"
#include "../Script/Host/ScriptHost.hpp"
#include "BankLogger.hpp"
#include "ExperienceLog.hpp"
#include "ItemLog.hpp"
#include "ProgressReporter.hpp"
#include "Type/ProgressReport_s.hpp"

// Owned after GameClient, whose shared cache outlives the item and bank log references.
// Separate sampling points preserve ordering around relog, script control requests and shutdown.
class AccountReporting
{
public:
    using Clock = std::chrono::steady_clock;

    AccountReporting(const Config_s& config, const AccountConfig_s& account, const GameCache_s& cache, std::shared_ptr<Logger> logger, std::function<void(const ProgressReport_s&)> onReport);

    void ObserveSession(Clock::time_point now, const GameState_s& state, ClientStatus_e status);
    void AfterScript(Clock::time_point now, ScriptHost& script);
    void SampleItems(Clock::time_point now, const GameState_s& state);

private:
    ProgressReporter m_progress;
    std::optional<ExperienceLog> m_experience;
    std::optional<BankLogger> m_bankLog;
    std::optional<ItemLog> m_inventory;
    std::optional<ItemLog> m_equipment;
};
