#pragma once

// Counts the attempts at a login or a reconnect, and holds when the next one may start. The wait after
// the first failed attempt is firstDelay, doubling after each one up to maxDelay.
class RetrySchedule
{
public:
    using Clock = std::chrono::steady_clock;

    RetrySchedule(u32 maxAttempts, std::chrono::milliseconds firstDelay, std::chrono::milliseconds maxDelay);

    // No attempts made, and none scheduled.
    void Reset();
    // Counts an attempt, which is the one that was scheduled.
    void BeginAttempt();
    void ScheduleAt(Clock::time_point time);

    [[nodiscard]] u32 GetAttempt() const;
    [[nodiscard]] u32 GetMaxAttempts() const;
    [[nodiscard]] bool HasAttemptsLeft() const;
    // The wait before the next attempt, after the ones made so far failed.
    [[nodiscard]] std::chrono::milliseconds GetDelay() const;
    [[nodiscard]] std::optional<Clock::time_point> GetScheduled() const;

private:
    u32 m_maxAttempts;
    std::chrono::milliseconds m_firstDelay;
    std::chrono::milliseconds m_maxDelay;
    u32 m_attempt = 0;
    std::optional<Clock::time_point> m_scheduled;
};
