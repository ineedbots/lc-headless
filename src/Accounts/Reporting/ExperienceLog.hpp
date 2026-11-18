#pragma once

#include "Websockets/Events/ApplicationEventPublisher.hpp"

#include "Console/Logger.hpp"
#include "Game/GameClient.hpp"
#include "Game/State/Type/GameState_s.hpp"
#include "Database/FleetDatabase.hpp"

// Logs one account's skill experience so a tool can work out what each skill is gaining from two samples.
// Written only once the account is in game and placed, so a login or a logout never records a baseline of zeroes.
class ExperienceLog
{
public:
    using Clock = std::chrono::steady_clock;

    // The 19 skills, in the game's stat order, as the state holds them.
    static constexpr auto SKILL_NAMES = std::to_array<std::string_view>({
        "attack",
        "defence",
        "strength",
        "hitpoints",
        "ranged",
        "prayer",
        "magic",
        "cooking",
        "woodcutting",
        "fletching",
        "fishing",
        "firemaking",
        "crafting",
        "smithing",
        "mining",
        "herblore",
        "agility",
        "thieving",
        "runecraft",
    });

    // A zero interval turns the log off; the account doesn't build one.
    ExperienceLog(std::string accountName, std::chrono::minutes interval, std::shared_ptr<Logger> logger, std::shared_ptr<FleetDatabase> database, std::shared_ptr<ApplicationEventPublisher> events = {});

    // Called every step. The account's status is recorded on every change, and skills are sampled while it
    // is in game and settled; `settled` is the state's own test, since the stats arrive a tick after the
    // player is placed.
    void Step(Clock::time_point now, const GameState_s& state, ClientStatus_e status, bool settled);
    void Poll(Clock::time_point now);
    void Flush();

    [[nodiscard]] const std::filesystem::path& GetDatabasePath() const
    {
        return m_database->GetPath();
    }

private:
    struct SampleOptions_s
    {
        bool settled = false;
        bool startsBaseline = false;
        bool periodic = false;
        bool statusTransition = false;
    };

    struct Sample_s
    {
        FleetExperienceLog_s record;
        std::array<s32, GameState_s::STAT_COUNT> xp{};
        Clock::time_point sampledAt;
        bool inGame = false;
        bool startsBaseline = false;
        bool periodic = false;
        bool statusTransition = false;
    };

    struct PendingWrite_s
    {
        Sample_s sample;
        std::future<void> completion;
    };

    [[nodiscard]] Sample_s MakeSample(Clock::time_point now, std::chrono::system_clock::time_point time, const GameState_s& state, std::string_view statusName, SampleOptions_s options) const;
    bool WriteSample(Sample_s sample);
    void LogGains(const std::array<s32, GameState_s::STAT_COUNT>& xp, double hours);

    std::string m_accountName;
    std::chrono::minutes m_interval;
    std::shared_ptr<Logger> m_logger;
    std::shared_ptr<FleetDatabase> m_database;
    std::optional<Clock::time_point> m_nextSample;
    std::string m_lastObservedStatus;
    std::deque<Sample_s> m_deferredStatuses;
    // Whether a settled baseline has been written for the current run.
    bool m_hasBaseline = false;
    // What the last sample held, for the log line's gains.
    std::array<s32, GameState_s::STAT_COUNT> m_lastXp{};
    bool m_hasLastXp = false;
    // So a file that can't be written is reported once, not every sample.
    bool m_writeFailed = false;
    std::optional<Clock::time_point> m_retryAt;
    std::shared_ptr<ApplicationEventPublisher> m_events;
    std::optional<PendingWrite_s> m_write;
};
