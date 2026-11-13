#include "pch.hpp"
#include "AccountLifecycle.hpp"

#include "Type/AccountPhase_e.hpp"

void AccountLifecycle::Start()
{
    assert(m_phase == AccountPhase_e::Pending && !m_started);
    m_started = true;
    m_phase = AccountPhase_e::Active;
    CheckInvariants();
}

void AccountLifecycle::Interrupt()
{
    assert(m_started && !IsFinished());
    ++m_interrupts;
}

void AccountLifecycle::BeginKillGrace(Clock::time_point deadline)
{
    assert(m_phase == AccountPhase_e::Active && m_interrupts == 1);
    m_killDeadline = deadline;
    CheckInvariants();
}

void AccountLifecycle::BeginStopping()
{
    assert(m_started && !IsFinished());
    ClearDeadlines();
    m_phase = AccountPhase_e::Stopping;
    CheckInvariants();
}

void AccountLifecycle::BeginRelog(std::chrono::seconds delay)
{
    assert(m_phase == AccountPhase_e::Active);
    m_relogDelay = delay;
    m_phase = AccountPhase_e::RelogLogout;
    CheckInvariants();
}

void AccountLifecycle::WaitAfterLogout(Clock::time_point now)
{
    assert(m_phase == AccountPhase_e::RelogLogout && m_relogDelay);
    m_reloginAt = now + *m_relogDelay;
    m_relogDelay.reset();
    m_phase = AccountPhase_e::RelogWait;
    CheckInvariants();
}

void AccountLifecycle::WaitToRecover(Clock::time_point deadline)
{
    assert(m_started && !IsFinished() && !IsStopping());
    m_relogDelay.reset();
    m_reloginAt = deadline;
    m_phase = AccountPhase_e::RelogWait;
    CheckInvariants();
}

void AccountLifecycle::ResumeLogin()
{
    assert(m_phase == AccountPhase_e::RelogWait);
    m_reloginAt.reset();
    m_phase = AccountPhase_e::Active;
    CheckInvariants();
}

void AccountLifecycle::MarkFailed()
{
    assert(!IsFinished());
    m_failed = true;
}

void AccountLifecycle::Finish(bool confirmedLogout)
{
    ClearDeadlines();
    m_confirmedLogout = confirmedLogout;
    m_phase = AccountPhase_e::Finished;
    CheckInvariants();
}

bool AccountLifecycle::IdleExpired(Clock::time_point now, std::chrono::seconds duration)
{
    assert(m_phase == AccountPhase_e::Active);
    if (duration > 0s && !m_idleUntil)
    {
        m_idleUntil = now + duration;
    }
    return m_idleUntil && now >= *m_idleUntil;
}

bool AccountLifecycle::IsStopping() const
{
    return m_phase == AccountPhase_e::Stopping || m_interrupts > 0;
}

bool AccountLifecycle::IsRelogging() const
{
    return m_phase == AccountPhase_e::RelogLogout || m_phase == AccountPhase_e::RelogWait;
}

bool AccountLifecycle::KillGraceExpired(Clock::time_point now) const
{
    return m_killDeadline && now >= *m_killDeadline;
}

bool AccountLifecycle::LoginDue(Clock::time_point now) const
{
    assert(m_phase == AccountPhase_e::RelogWait && m_reloginAt);
    return now >= *m_reloginAt;
}

void AccountLifecycle::ClearDeadlines()
{
    m_killDeadline.reset();
    m_idleUntil.reset();
    m_relogDelay.reset();
    m_reloginAt.reset();
}

void AccountLifecycle::CheckInvariants() const
{
    assert(m_relogDelay.has_value() == (m_phase == AccountPhase_e::RelogLogout));
    assert(m_reloginAt.has_value() == (m_phase == AccountPhase_e::RelogWait));
    assert(!m_killDeadline || (m_started && m_interrupts > 0 && !IsFinished()));
    assert(m_phase != AccountPhase_e::Stopping || (!m_killDeadline && !m_idleUntil));
    assert(!IsFinished() || (!m_killDeadline && !m_idleUntil));
    assert(m_started || m_phase == AccountPhase_e::Pending || IsFinished());
}

bool AccountLifecycle::Succeeded() const
{
    return IsFinished() && !m_failed && m_confirmedLogout;
}

std::string_view AccountLifecycle::DescribeOutcome() const
{
    if (!m_started)
    {
        return "never started";
    }
    if (!IsFinished())
    {
        return "still running";
    }
    if (m_failed)
    {
        return "failed";
    }
    return m_confirmedLogout ? "logged out" : "disconnected without a confirmed logout";
}
