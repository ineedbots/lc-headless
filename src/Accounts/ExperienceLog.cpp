#include "pch.hpp"
#include "ExperienceLog.hpp"

#include "../Application/Events/ApplicationEventPublisher.hpp"

#include "../Utils/FileUtils.hpp"
#include "../Utils/StringUtils.hpp"
#include "../Game/State/Type/Stat_s.hpp"
#include "FleetLogJson.hpp"
#include "Type/ExperienceLogRecord_s.hpp"
#include "Type/FleetSkill_s.hpp"

#include "Type/FleetExperienceLog_s.hpp"

#include <nlohmann/json.hpp>

namespace
{
    constexpr auto EXTENSION = ".jsonl"sv;

    std::string_view StatusName(ClientStatus_e status)
    {
        switch (status)
        {
        case ClientStatus_e::Disconnected:
            return "disconnected";
        case ClientStatus_e::Connecting:
            return "connecting";
        case ClientStatus_e::InGame:
            return "ingame";
        case ClientStatus_e::LoggingOut:
            return "logging out";
        case ClientStatus_e::LoggedOut:
            return "logged out";
        }

        return "unknown";
    }

    // A skill's name, in the log line, as a sentence would start it.
    std::string Title(std::string_view name)
    {
        auto title = std::string{name};
        if (!title.empty())
        {
            title.front() = static_cast<char>(std::toupper(static_cast<unsigned char>(title.front())));
        }

        return title;
    }
}

ExperienceLog::ExperienceLog(std::filesystem::path directory, std::string accountName, std::chrono::minutes interval, std::shared_ptr<Logger> logger, std::shared_ptr<ApplicationEventPublisher> events)
    : m_path{std::move(directory) / (accountName + std::string{EXTENSION})}
    , m_accountName{std::move(accountName)}
    , m_interval{interval}
    , m_logger{std::move(logger)}
    , m_events{std::move(events)}
{
}

void ExperienceLog::Step(Clock::time_point now, const GameState_s& state, ClientStatus_e status, bool settled)
{
    if (m_interval <= std::chrono::minutes::zero())
    {
        return;
    }

    const auto statusName = StatusName(status);
    const auto inGame = status == ClientStatus_e::InGame && settled;
    const auto statusChanged = m_lastStatus != statusName;
    const auto firstBaseline = inGame && !m_hasBaseline;
    const auto due = inGame && m_hasBaseline && (!m_nextSample || now >= *m_nextSample);

    if (!statusChanged && !firstBaseline && !due)
    {
        return;
    }

    auto periodic = false;
    if (firstBaseline)
    {
        m_hasBaseline = true;
        m_nextSample = now + m_interval;
    }
    else if (due)
    {
        periodic = true;
        m_nextSample = now + m_interval;
    }

    WriteSample(std::chrono::system_clock::now(), state, statusName, inGame && settled);
    m_lastStatus = std::string{statusName};

    // A sample with no gain has nothing to say; a status line and a baseline have no window to compare.
    if (periodic && m_hasLastXp)
    {
        const auto hours = std::chrono::duration<double, std::ratio<3600>>{std::chrono::duration_cast<Clock::duration>(m_interval)}.count();
        LogGains(state, hours);
    }

    if (inGame)
    {
        for (std::size_t i = 0; i < SKILL_NAMES.size(); ++i)
        {
            m_lastXp[i] = state.stats[i].xp;
        }

        m_hasLastXp = true;
    }
    else
    {
        // The next login is a new run, with its own baseline; no rate crosses a logout.
        m_hasBaseline = false;
        m_nextSample.reset();
    }
}

void ExperienceLog::WriteSample(std::chrono::system_clock::time_point time, const GameState_s& state, std::string_view statusName, bool settled)
{
    auto record = ExperienceLogRecord_s{
        .time = std::format("{:%Y-%m-%dT%H:%M:%SZ}", std::chrono::floor<std::chrono::seconds>(time)),
        .account = m_accountName,
        .state = std::string{statusName},
        .settled = settled};

    for (std::size_t i = 0; i < SKILL_NAMES.size() && i < GameState_s::STAT_COUNT; ++i)
    {
        const auto& stat = state.stats[i];
        record.skills.emplace_back(std::string{SKILL_NAMES[i]}, FleetSkill_s{.level = stat.level, .base = stat.baseLevel, .xp = stat.xp});
    }

    try
    {
        const auto line = nlohmann::ordered_json(record).dump(-1, ' ', false, nlohmann::json::error_handler_t::replace) + '\n';
        FileUtils::AppendText(m_path, line);

        if (m_events)
        {
            m_events->Publish(m_accountName, FleetExperienceLog_s{line});
        }

        if (m_writeFailed)
        {
            m_writeFailed = false;
            m_logger->Info("Writing experience to {} again", m_path.string());
        }
    }
    catch (const std::exception& e)
    {
        // A convenience, like the progress report: never take the account down over it.
        if (!m_writeFailed)
        {
            m_writeFailed = true;
            m_logger->Warning("The experience log wasn't saved; it won't be tried again until one works: {}", e.what());
        }
    }
}

void ExperienceLog::LogGains(const GameState_s& state, double hours)
{
    auto parts = std::vector<std::string>{};
    for (std::size_t i = 0; i < SKILL_NAMES.size() && i < GameState_s::STAT_COUNT; ++i)
    {
        const auto gained = state.stats[i].xp - m_lastXp[i];
        if (gained <= 0)
        {
            continue;
        }

        const auto rate = hours > 0.0 ? static_cast<s64>(std::llround(gained / hours)) : 0;
        parts.push_back(std::format("{} +{} xp ({} an hour)", Title(SKILL_NAMES[i]), gained, rate));
    }

    if (!parts.empty())
    {
        m_logger->Info("experience: {}", StringUtils::Join(parts, ", "));
    }
}
