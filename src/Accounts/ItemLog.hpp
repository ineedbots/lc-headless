#pragma once

#include "../Cache/GameCache_s.hpp"
#include "../Console/Logger.hpp"
#include "../Game/State/GameState_s.hpp"

#include <chrono>
#include <filesystem>
#include <memory>
#include <string>

// Writes one of an account's item containers to <directory>/<account>.jsonl whenever its contents change,
// grouped by item id. The last line is what it holds now, and the earlier lines are its history.
//
// Backpack samples follow the bank: while one is open the game swaps in the bank's own backpack, so the
// sample is of that, and bankOpen says so. Changes closer together than the interval are held until it
// passes, so a busy account writes a line every few seconds rather than one per step.
class ItemLog
{
public:
    using Clock = std::chrono::steady_clock;

    enum class Kind_e
    {
        Backpack,
        Equipment,
    };

    // A zero interval records every change.
    ItemLog(const GameCache_s& cache, std::shared_ptr<Logger> logger, std::string accountName, std::filesystem::path directory, Kind_e kind, std::chrono::seconds interval);

    // Called every step while in game.
    void Step(Clock::time_point now, const GameState_s& state);

    [[nodiscard]] const std::filesystem::path& GetPath() const { return m_path; }

private:
    // One item's worth of entries: the id, and how many are held across the slots.
    struct Entry_s
    {
        s32 id = 0;
        s32 qty = 0;

        [[nodiscard]] bool operator==(const Entry_s&) const = default;
    };

    struct Contents_s
    {
        u16 com = 0;
        bool bankOpen = false;
        // Occupied and total slots, counted before grouping, so free stays right.
        std::size_t used = 0;
        std::size_t slots = 0;
        // Grouped by id, in id order, so two samples of the same contents compare equal.
        std::vector<Entry_s> items;

        [[nodiscard]] bool operator==(const Contents_s&) const = default;
    };

    [[nodiscard]] Contents_s Read(const GameState_s& state) const;
    void WriteSample(Clock::time_point now, const Contents_s& contents);

    const GameCache_s& m_cache;
    std::shared_ptr<Logger> m_logger;
    std::string m_accountName;
    std::filesystem::path m_path;
    Kind_e m_kind;
    std::chrono::seconds m_interval;
    std::optional<Contents_s> m_lastSample;
    // Set by a change the interval held back, so it is written once the interval passes.
    std::optional<Contents_s> m_pending;
    std::optional<Clock::time_point> m_nextSample;
    bool m_writeFailed = false;
};
