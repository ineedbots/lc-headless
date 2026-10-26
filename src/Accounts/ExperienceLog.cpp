#include "pch.hpp"
#include "ExperienceLog.hpp"

#include "../Utils/StringUtils.hpp"

#include <fstream>

namespace
{
    constexpr auto EXTENSION = ".jsonl"sv;

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

ExperienceLog::ExperienceLog(std::filesystem::path directory, std::string accountName, std::chrono::minutes interval, std::shared_ptr<Logger> logger)
    : m_path{std::move(directory) / (accountName + std::string{EXTENSION})}
    , m_accountName{std::move(accountName)}
    , m_interval{interval}
    , m_logger{std::move(logger)}
{
}

void ExperienceLog::Step(Clock::time_point now, const GameState_s& state, bool inGame)
{
    if (m_interval <= std::chrono::minutes::zero() || !inGame)
    {
        return;
    }

    const auto due = !m_nextSample || now >= *m_nextSample;
    if (!due)
    {
        return;
    }

    // The first sample is the baseline, and says so; later ones cover the time since.
    const auto baseline = !m_nextSample;
    const auto hours = baseline ? 0.0 : std::chrono::duration<double, std::ratio<3600>>{std::chrono::duration_cast<Clock::duration>(m_interval)}.count();
    m_nextSample = now + m_interval;

    WriteSample(std::chrono::system_clock::now(), state);

    // A baseline has nothing to compare with; a sample with no gain has nothing to say.
    if (!baseline && m_hasLastXp)
    {
        LogGains(state, hours);
    }

    for (std::size_t i = 0; i < SKILL_NAMES.size(); ++i)
    {
        m_lastXp[i] = state.stats[i].xp;
    }

    m_hasLastXp = true;
}

void ExperienceLog::WriteSample(std::chrono::system_clock::time_point time, const GameState_s& state)
{
    auto line = std::string{};
    line.reserve(2048);
    std::format_to(std::back_inserter(line), "{{\"time\":\"{:%Y-%m-%dT%H:%M:%SZ}\",\"account\":\"{}\",\"skills\":{{",
                   std::chrono::floor<std::chrono::seconds>(time), m_accountName);

    for (std::size_t i = 0; i < SKILL_NAMES.size() && i < GameState_s::STAT_COUNT; ++i)
    {
        const auto& stat = state.stats[i];
        std::format_to(std::back_inserter(line), "{}\"{}\":{{\"level\":{},\"base\":{},\"xp\":{}}}",
                       i == 0 ? "" : ",", SKILL_NAMES[i], stat.level, stat.baseLevel, stat.xp);
    }

    line += "}}\n";

    try
    {
        const auto folder = m_path.parent_path();
        if (!folder.empty())
        {
            auto error = std::error_code{};
            std::filesystem::create_directories(folder, error);
        }

        auto file = std::ofstream{m_path, std::ios::binary | std::ios::app};
        file << line;
        file.flush();
        if (!file)
        {
            throw std::runtime_error{std::format("can't write {}", m_path.string())};
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
