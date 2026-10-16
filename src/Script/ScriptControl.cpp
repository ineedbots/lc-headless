#include "pch.hpp"
#include "ScriptControl.hpp"

void ScriptControl::RequestStop(StopRequest_e request)
{
    m_stopRequest = std::max(m_stopRequest, request);
}

StopRequest_e ScriptControl::TakeStopRequest()
{
    return std::exchange(m_stopRequest, StopRequest_e::None);
}

void ScriptControl::RequestRelog(std::chrono::seconds delay)
{
    m_relogRequest = delay;
}

std::optional<std::chrono::seconds> ScriptControl::TakeRelogRequest()
{
    return std::exchange(m_relogRequest, std::nullopt);
}

void ScriptControl::SetStepTime(s64 milliseconds)
{
    m_stepTime = milliseconds;
}

s64 ScriptControl::GetStepTime() const
{
    return m_stepTime;
}

void ScriptControl::NoteProgress()
{
    m_lastProgress = m_stepTime;
}

std::optional<s64> ScriptControl::GetLastProgress() const
{
    return m_lastProgress;
}
