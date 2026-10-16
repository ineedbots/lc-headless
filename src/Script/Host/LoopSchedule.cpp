#include "pch.hpp"
#include "LoopSchedule.hpp"

#include "../../Game/State/GameState_s.hpp"

void LoopSchedule::RunAt(Clock::time_point time)
{
    m_wait = LoopWait_e::Time;
    m_nextLoop = time;
}

void LoopSchedule::Schedule(Clock::time_point now, std::string_view kind, s64 value, const GameState_s& state)
{
    if (kind == WAIT_MS)
    {
        RunAt(now + std::chrono::milliseconds{value});
        return;
    }

    if (kind == WAIT_UPDATE)
    {
        m_wait = LoopWait_e::Update;
        m_waitUpdateCount = state.updateCount;
        m_waitHasTimeout = value >= 0;
        m_nextLoop = now + std::chrono::milliseconds{std::max<s64>(value, 0)};
        return;
    }

    m_wait = LoopWait_e::Ticks;
    m_waitTick = state.tick + static_cast<u64>(value);
}

bool LoopSchedule::IsDue(Clock::time_point now, const GameState_s& state) const
{
    switch (m_wait)
    {
    case LoopWait_e::Time:
        return now >= m_nextLoop;
    case LoopWait_e::Update:
        return state.updateCount != m_waitUpdateCount || (m_waitHasTimeout && now >= m_nextLoop);
    case LoopWait_e::Ticks:
        return state.tick >= m_waitTick;
    }

    return true;
}

std::optional<LoopSchedule::Clock::time_point> LoopSchedule::GetNextTime() const
{
    if (m_wait == LoopWait_e::Ticks || (m_wait == LoopWait_e::Update && !m_waitHasTimeout))
    {
        return std::nullopt;
    }

    return m_nextLoop;
}
