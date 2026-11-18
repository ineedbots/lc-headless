#include "pch.hpp"
#include "AccountReporting.hpp"

#include "Websockets/Events/ApplicationEventPublisher.hpp"

#include "Cache/Type/GameCache_s.hpp"
#include "Config/Type/AccountConfig_s.hpp"
#include "Config/Type/Config_s.hpp"
#include "Console/Logger.hpp"
#include "Game/GameClient.hpp"
#include "Game/State/Type/GameState_s.hpp"
#include "Script/Host/ScriptHost.hpp"
#include "AccountDataLog.hpp"
#include "BankLogger.hpp"
#include "ExperienceLog.hpp"
#include "ItemLog.hpp"
#include "ProgressReporter.hpp"
#include "Accounts/Reporting/Type/ProgressReport_s.hpp"

AccountReporting::AccountReporting(const Config_s& config, const AccountConfig_s& account, const GameCache_s& cache, std::shared_ptr<Logger> logger, std::function<void(const ProgressReport_s&)> onReport, std::shared_ptr<ApplicationEventPublisher> events, FleetDatabaseProvider_t databaseProvider)
    : m_progress{account.script ? account.script->progressReportMinutes : std::chrono::minutes{0}, std::filesystem::path{config.scripting.progressDirectory} / (account.name + ".txt"), logger, std::move(onReport)}
{
    const auto& scripting = config.scripting;
    if (!scripting.fleetDatabasePath.empty() && (scripting.accountDataLogEnabled || scripting.experienceLogEnabled || scripting.bankLogEnabled || scripting.inventoryLogEnabled || scripting.equipmentLogEnabled))
    {
        m_fleetDatabase = databaseProvider ? databaseProvider(scripting.fleetDatabasePath) : std::make_shared<FleetDatabase>(scripting.fleetDatabasePath, FleetDatabase::Mode_e::Inline, scripting.fleetRetention);
    }

    if (m_fleetDatabase && scripting.accountDataLogEnabled)
    {
        m_accountData.emplace(cache, logger, account.name, m_fleetDatabase, scripting.accountDataIntervalSeconds, events);
    }

    if (m_fleetDatabase && scripting.experienceLogEnabled)
    {
        m_experience.emplace(account.name, scripting.experienceIntervalMinutes, logger, m_fleetDatabase, events);
    }

    if (m_fleetDatabase && scripting.bankLogEnabled)
    {
        // The bank is the cache's, so this needs no script and works for every bot.
        m_bankLog.emplace(cache, logger, account.name, m_fleetDatabase, events);
    }

    if (m_fleetDatabase && scripting.inventoryLogEnabled)
    {
        m_inventory.emplace(cache, logger, account.name, m_fleetDatabase, ItemLog::Kind_e::Backpack, scripting.inventoryIntervalSeconds, events);
    }

    if (m_fleetDatabase && scripting.equipmentLogEnabled)
    {
        // Worn equipment changes rarely, so every change is worth a record.
        m_equipment.emplace(cache, logger, account.name, m_fleetDatabase, ItemLog::Kind_e::Equipment, 0s, events);
    }
}

void AccountReporting::Poll(Clock::time_point now)
{
    if (m_accountData)
    {
        m_accountData->Poll(now);
    }

    if (m_experience)
    {
        m_experience->Poll(now);
    }

    if (m_bankLog)
    {
        m_bankLog->Poll(now);
    }

    if (m_inventory)
    {
        m_inventory->Poll(now);
    }

    if (m_equipment)
    {
        m_equipment->Poll(now);
    }
}

void AccountReporting::Flush()
{
    if (m_accountData)
    {
        m_accountData->Flush();
    }

    if (m_experience)
    {
        m_experience->Flush();
    }

    if (m_bankLog)
    {
        m_bankLog->Flush();
    }

    if (m_inventory)
    {
        m_inventory->Flush();
    }

    if (m_equipment)
    {
        m_equipment->Flush();
    }
}

void AccountReporting::ObserveSession(Clock::time_point now, const GameState_s& state, ClientStatus_e status)
{
    if (m_accountData)
    {
        m_accountData->Step(now, state, status);
    }

    if (m_experience)
    {
        m_experience->Step(now, state, status, state.IsSettled());
    }
}

void AccountReporting::AfterScript(Clock::time_point now, ScriptHost& script)
{
    m_progress.Step(now, script);
}

void AccountReporting::SampleItems(Clock::time_point now, const GameState_s& state)
{
    if (m_bankLog)
    {
        m_bankLog->Step(now, state);
    }

    if (m_inventory)
    {
        m_inventory->Step(now, state);
    }

    if (m_equipment)
    {
        m_equipment->Step(now, state);
    }
}
