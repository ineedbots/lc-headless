#pragma once

#include "Type/AccountPhase_e.hpp"

// Account policy only. Wire login/reconnect/logout state and its deadlines belong to GameClient.
class AccountLifecycle
{
public:
    using Clock = std::chrono::steady_clock;

    void Start();
    void Interrupt();
    void BeginKillGrace(Clock::time_point deadline);
    void BeginStopping();
    void BeginRelog(std::chrono::seconds delay);
    void WaitAfterLogout(Clock::time_point now);
    void WaitToRecover(Clock::time_point deadline);
    void ResumeLogin();
    void MarkFailed();
    void Finish(bool confirmedLogout);
    [[nodiscard]] bool Succeeded() const;
    [[nodiscard]] std::string_view DescribeOutcome() const;
    [[nodiscard]] bool IdleExpired(Clock::time_point now, std::chrono::seconds duration);

    [[nodiscard]] AccountPhase_e GetPhase() const
    {
        return m_phase;
    }
    [[nodiscard]] bool IsStarted() const
    {
        return m_started;
    }
    [[nodiscard]] bool IsFinished() const
    {
        return m_phase == AccountPhase_e::Finished;
    }
    [[nodiscard]] bool HasFailed() const
    {
        return m_failed;
    }
    [[nodiscard]] bool IsStopping() const;
    [[nodiscard]] bool IsRelogging() const;
    [[nodiscard]] bool IsEscalated() const
    {
        return m_interrupts > 1;
    }
    [[nodiscard]] bool KillGraceExpired(Clock::time_point now) const;
    [[nodiscard]] bool LoginDue(Clock::time_point now) const;

private:
    void ClearDeadlines();
    void CheckInvariants() const;

    AccountPhase_e m_phase = AccountPhase_e::Pending;
    // Admission history is independent of phase: runner teardown can finish a pending account.
    bool m_started = false;
    bool m_failed = false;
    bool m_confirmedLogout = false;
    u32 m_interrupts = 0;
    std::optional<Clock::time_point> m_killDeadline;
    std::optional<Clock::time_point> m_idleUntil;
    std::optional<std::chrono::seconds> m_relogDelay;
    std::optional<Clock::time_point> m_reloginAt;
};
