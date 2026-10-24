#pragma once

// Hands out the times that clients sharing it may start a login attempt, at least an interval apart and in the
// order they asked, so accounts that all lose their connection at once take turns reconnecting rather than
// tripping the server's limit on login attempts. A turn a client gives up is left unused.
class LoginQueue
{
public:
    using Clock = std::chrono::steady_clock;

    explicit LoginQueue(std::chrono::milliseconds interval);

    // The first turn at or after earliest that is an interval after the last one handed out.
    [[nodiscard]] Clock::time_point Reserve(Clock::time_point earliest);

private:
    std::chrono::milliseconds m_interval;
    std::optional<Clock::time_point> m_lastTurn;
};
