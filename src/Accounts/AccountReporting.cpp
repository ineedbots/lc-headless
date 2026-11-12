#include "pch.hpp"
#include "AccountReporting.hpp"

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

AccountReporting::AccountReporting(const Config_s& config, const AccountConfig_s& account, const GameCache_s& cache, std::shared_ptr<Logger> logger, std::function<void(const ProgressReport_s&)> onReport)
    : m_progress{account.script ? account.script->progressReportMinutes : std::chrono::minutes{0}, std::filesystem::path{config.scripting.progressDirectory} / (account.name + ".txt"), logger, std::move(onReport)}
{
    const auto& experience = config.scripting;
    if (!experience.experienceDirectory.empty() && experience.experienceIntervalMinutes > std::chrono::minutes::zero())
    {
        m_experience.emplace(std::filesystem::path{experience.experienceDirectory}, account.name, experience.experienceIntervalMinutes, logger);
    }

    if (!config.scripting.bankLogDirectory.empty())
    {
        // The bank is the cache's, so this needs no script and works for every bot.
        m_bankLog.emplace(cache, logger, account.name, std::filesystem::path{config.scripting.bankLogDirectory});
    }

    if (!config.scripting.inventoryDirectory.empty())
    {
        m_inventory.emplace(cache, logger, account.name, std::filesystem::path{config.scripting.inventoryDirectory},
                            ItemLog::Kind_e::Backpack, config.scripting.inventoryIntervalSeconds);
    }

    if (!config.scripting.equipmentDirectory.empty())
    {
        // Worn equipment changes rarely, so every change is worth a line.
        m_equipment.emplace(cache, logger, account.name, std::filesystem::path{config.scripting.equipmentDirectory},
                            ItemLog::Kind_e::Equipment, 0s);
    }
}

void AccountReporting::ObserveSession(Clock::time_point now, const GameState_s& state, ClientStatus_e status)
{
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
        m_bankLog->Step(state);
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
