#pragma once

#include "../Console/Logger.hpp"
#include "../Game/State/GameState_s.hpp"

#include <chrono>
#include <filesystem>
#include <memory>
#include <optional>
#include <string>

// Logs one account's skill experience to <directory>/<account>.jsonl, one sample per line, so a tool can
// work out what each skill is gaining from two samples. Written only once the account is in game and
// placed, so a login or a logout never records a baseline of zeroes.
//
// The first sample is the baseline and is written at once; later ones follow every interval. A sample is
// a whole line of JSON, appended and flushed, so the file is readable while it is being written.
class ExperienceLog
{
public:
    using Clock = std::chrono::steady_clock;

    // The 19 skills, in the game's stat order, as the state holds them.
    static constexpr auto SKILL_NAMES = std::to_array<std::string_view>({
        "attack", "defence", "strength", "hitpoints", "ranged", "prayer", "magic",
        "cooking", "woodcutting", "fletching", "fishing", "firemaking", "crafting",
        "smithing", "mining", "herblore", "agility", "thieving", "runecraft",
    });

    // A zero interval turns the log off; the account doesn't build one.
    ExperienceLog(std::filesystem::path directory, std::string accountName, std::chrono::minutes interval, std::shared_ptr<Logger> logger);

    // Called every step. `inGame` is the account's status, so nothing is logged before it is in game.
    void Step(Clock::time_point now, const GameState_s& state, bool inGame);

    [[nodiscard]] const std::filesystem::path& GetPath() const { return m_path; }

private:
    void WriteSample(std::chrono::system_clock::time_point time, const GameState_s& state);
    void LogGains(const GameState_s& state, double hours);

    std::filesystem::path m_path;
    std::string m_accountName;
    std::chrono::minutes m_interval;
    std::shared_ptr<Logger> m_logger;
    std::optional<Clock::time_point> m_nextSample;
    // What the last sample held, for the log line's gains.
    std::array<s32, GameState_s::STAT_COUNT> m_lastXp{};
    bool m_hasLastXp = false;
    // So a file that can't be written is reported once, not every sample.
    bool m_writeFailed = false;
};
