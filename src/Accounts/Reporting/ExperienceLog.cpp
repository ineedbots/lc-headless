#include "pch.hpp"
#include "ExperienceLog.hpp"

#include "ReportWriteCompletion.hpp"
#include "ReportingStatus.hpp"

#include "Websockets/Events/ApplicationEventPublisher.hpp"

#include "Utils/StringUtils.hpp"
#include "Game/State/Type/Stat_s.hpp"
#include "Accounts/Reporting/Type/FleetExperienceLog_s.hpp"
#include "Accounts/Reporting/Type/FleetSkill_s.hpp"

namespace
{
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

ExperienceLog::ExperienceLog(std::string accountName, std::chrono::minutes interval, std::shared_ptr<Logger> logger, std::shared_ptr<FleetDatabase> database, std::shared_ptr<ApplicationEventPublisher> events)
    : m_accountName{std::move(accountName)}
    , m_interval{interval}
    , m_logger{std::move(logger)}
    , m_database{std::move(database)}
    , m_events{std::move(events)}
{
    assert(interval > 0min);
}

void ExperienceLog::Step(Clock::time_point now, const GameState_s& state, ClientStatus_e status, bool settled)
{
    Poll(now);

    const auto statusName = ReportingStatus::Name(status);
    const auto inGame = status == ClientStatus_e::InGame && settled;
    if (m_lastObservedStatus != statusName)
    {
        m_lastObservedStatus = std::string{statusName};
        if (m_deferredStatuses.size() >= FleetDatabase::MAX_PENDING_WRITES)
        {
            if (!m_writeFailed)
            {
                m_writeFailed = true;
                m_logger->Warning("The experience log's pending status-transition queue is full; the transition wasn't saved");
            }
        }
        else
        {
            m_deferredStatuses.push_back(MakeSample(now, std::chrono::system_clock::now(), state, statusName, {.settled = inGame, .statusTransition = true}));
        }
    }

    if (m_write)
    {
        return;
    }

    if (m_retryAt && now < *m_retryAt)
    {
        return;
    }

    if (!m_deferredStatuses.empty())
    {
        auto sample = std::move(m_deferredStatuses.front());
        m_deferredStatuses.pop_front();
        sample.startsBaseline = sample.inGame && !m_hasBaseline;
        if (!WriteSample(sample))
        {
            m_deferredStatuses.push_front(std::move(sample));
            m_retryAt = now + std::min(m_interval, std::chrono::minutes{1});
        }

        return;
    }

    const auto firstBaseline = inGame && !m_hasBaseline;
    const auto due = inGame && m_hasBaseline && (!m_nextSample || now >= *m_nextSample);

    if (!firstBaseline && !due)
    {
        return;
    }

    auto sample = MakeSample(now, std::chrono::system_clock::now(), state, statusName, {.settled = inGame, .startsBaseline = firstBaseline || due, .periodic = due});
    if (!WriteSample(std::move(sample)))
    {
        m_retryAt = now + std::min(m_interval, std::chrono::minutes{1});
    }
}

ExperienceLog::Sample_s ExperienceLog::MakeSample(Clock::time_point now, std::chrono::system_clock::time_point time, const GameState_s& state, std::string_view statusName, SampleOptions_s options) const
{
    auto sample = Sample_s{
        .record = FleetExperienceLog_s{
            .time = std::format("{:%Y-%m-%dT%H:%M:%SZ}", std::chrono::floor<std::chrono::seconds>(time)),
            .account = m_accountName,
            .state = std::string{statusName},
            .settled = options.settled},
        .sampledAt = now,
        .inGame = options.settled && statusName == "ingame",
        .startsBaseline = options.startsBaseline,
        .periodic = options.periodic,
        .statusTransition = options.statusTransition};

    for (std::size_t i = 0; i < SKILL_NAMES.size() && i < GameState_s::STAT_COUNT; ++i)
    {
        const auto& stat = state.stats[i];
        sample.record.skills.emplace_back(std::string{SKILL_NAMES[i]}, FleetSkill_s{.level = stat.level, .base = stat.baseLevel, .xp = stat.xp});
    }

    for (std::size_t i = 0; i < sample.xp.size(); ++i)
    {
        sample.xp[i] = state.stats[i].xp;
    }

    return sample;
}

bool ExperienceLog::WriteSample(Sample_s sample)
{
    try
    {
        auto completion = m_database->Enqueue(sample.record);
        if (!completion)
        {
            throw std::runtime_error{"fleet database write queue is full"};
        }

        m_write.emplace(PendingWrite_s{std::move(sample), std::move(*completion)});
        Poll(Clock::now());

        return true;
    }
    catch (const std::exception& e)
    {
        // A convenience, like the progress report: never take the account down over it.
        if (!m_writeFailed)
        {
            m_writeFailed = true;
            m_logger->Warning("The experience log wasn't saved to {}; it will retry: {}", m_database->GetPath().string(), e.what());
        }

        return false;
    }
}

void ExperienceLog::Poll(Clock::time_point now)
{
    ReportWriteCompletion::Poll(m_write, [this](auto& write)
    {
        ReportWriteCompletion::Publish(m_events, *m_logger, m_accountName, write.sample.record);

        if (m_writeFailed)
        {
            m_writeFailed = false;
            m_logger->Info("Writing experience to {} again", m_database->GetPath().string());
        }

        m_retryAt.reset();

        if (write.sample.inGame)
        {
            if (write.sample.startsBaseline)
            {
                m_hasBaseline = true;
                m_nextSample = write.sample.sampledAt + m_interval;
            }

            if (write.sample.periodic && m_hasLastXp)
            {
                const auto hours = std::chrono::duration<double, std::ratio<3600>>{std::chrono::duration_cast<Clock::duration>(m_interval)}.count();
                LogGains(write.sample.xp, hours);
            }

            m_lastXp = write.sample.xp;
            m_hasLastXp = true;
        }
        else
        {
            // The next login is a new run, with its own baseline; no rate crosses a logout.
            m_hasBaseline = false;
            m_nextSample.reset();
        }
    }, [this, now](auto& write, const std::exception& e)
    {
        if (write.sample.statusTransition)
        {
            m_deferredStatuses.push_front(std::move(write.sample));
        }

        if (!m_writeFailed)
        {
            m_writeFailed = true;
            m_logger->Warning("The experience log wasn't saved to {}; it will retry: {}", m_database->GetPath().string(), e.what());
        }

        m_retryAt = now + std::min(m_interval, std::chrono::minutes{1});
    });
}

void ExperienceLog::Flush()
{
    if (m_write)
    {
        m_write->completion.wait();
        Poll(Clock::now());
    }

    const auto attempts = m_deferredStatuses.size();
    for (auto i = std::size_t{}; i < attempts && !m_deferredStatuses.empty(); ++i)
    {
        auto sample = std::move(m_deferredStatuses.front());
        m_deferredStatuses.pop_front();
        sample.startsBaseline = sample.inGame && !m_hasBaseline;
        if (!WriteSample(sample))
        {
            m_database->Flush();
            if (!WriteSample(sample))
            {
                m_deferredStatuses.push_front(std::move(sample));
                return;
            }
        }

        if (m_write)
        {
            m_write->completion.wait();
            Poll(Clock::now());
        }

        if (m_writeFailed)
        {
            return;
        }
    }
}

void ExperienceLog::LogGains(const std::array<s32, GameState_s::STAT_COUNT>& xp, double hours)
{
    auto parts = std::vector<std::string>{};
    for (std::size_t i = 0; i < SKILL_NAMES.size() && i < GameState_s::STAT_COUNT; ++i)
    {
        const auto gained = xp[i] - m_lastXp[i];
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
