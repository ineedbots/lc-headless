#pragma once

#include "../../Game/State/GameState_s.hpp"

// When the bot's loop() runs next: at a time, after the next update from the server (with or without a
// timeout), or once the server's tick reaches a number.
class LoopSchedule
{
public:
    using Clock = std::chrono::steady_clock;

    static constexpr auto WAIT_MS = "ms"sv;
    static constexpr auto WAIT_UPDATE = "update"sv;

    void RunAt(Clock::time_point time);
    // How the stdlib's runtime said to wait: "ms" for a number of milliseconds; "update" for the next update,
    // with a timeout in milliseconds unless it's negative; anything else for a number of ticks.
    void Schedule(Clock::time_point now, std::string_view kind, s64 value, const GameState_s& state);
    [[nodiscard]] bool IsDue(Clock::time_point now, const GameState_s& state) const;
    // Nullopt for a wait on the server with no timeout.
    [[nodiscard]] std::optional<Clock::time_point> GetNextTime() const;

private:
    enum class LoopWait_e : u8
    {
        Time,
        Update,
        Ticks,
    };

    // Until m_nextLoop; for an update after m_waitUpdateCount, or until m_nextLoop when m_waitHasTimeout; or for
    // the tick to reach m_waitTick.
    LoopWait_e m_wait = LoopWait_e::Time;
    Clock::time_point m_nextLoop;
    u64 m_waitUpdateCount = 0;
    bool m_waitHasTimeout = false;
    u64 m_waitTick = 0;
};
