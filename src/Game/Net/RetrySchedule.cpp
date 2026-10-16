#include "pch.hpp"
#include "RetrySchedule.hpp"

RetrySchedule::RetrySchedule(u32 maxAttempts, std::chrono::milliseconds firstDelay, std::chrono::milliseconds maxDelay)
    : m_maxAttempts{maxAttempts}
    , m_firstDelay{firstDelay}
    , m_maxDelay{maxDelay}
{
}

void RetrySchedule::Reset()
{
    m_attempt = 0;
    m_scheduled.reset();
}

void RetrySchedule::BeginAttempt()
{
    ++m_attempt;
    m_scheduled.reset();
}

void RetrySchedule::ScheduleAt(Clock::time_point time)
{
    m_scheduled = time;
}

u32 RetrySchedule::GetAttempt() const
{
    return m_attempt;
}

u32 RetrySchedule::GetMaxAttempts() const
{
    return m_maxAttempts;
}

bool RetrySchedule::HasAttemptsLeft() const
{
    return m_attempt < m_maxAttempts;
}

std::chrono::milliseconds RetrySchedule::GetDelay() const
{
    auto delay = m_firstDelay;
    for (auto i = u32{1}; i < m_attempt && delay < m_maxDelay; ++i)
    {
        delay *= 2;
    }

    return std::min(delay, m_maxDelay);
}

std::optional<RetrySchedule::Clock::time_point> RetrySchedule::GetScheduled() const
{
    return m_scheduled;
}
