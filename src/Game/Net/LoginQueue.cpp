#include "pch.hpp"
#include "LoginQueue.hpp"

LoginQueue::LoginQueue(std::chrono::milliseconds interval)
    : m_interval{interval}
{
}

LoginQueue::Clock::time_point LoginQueue::Reserve(Clock::time_point earliest)
{
    auto turn = earliest;
    if (m_lastTurn)
    {
        turn = std::max(turn, *m_lastTurn + m_interval);
    }

    m_lastTurn = turn;
    return turn;
}
