from bots.account_leveler.record import Record
"""Ported from rs2b0t's src/bot/scripts/AccountLeveler/session.ts (MIT, see thirdparty/rs2b0t)."""


__all__ = ['uses_activity_cooldown', 'LevelerSession']

def uses_activity_cooldown(plan):
    return plan.combat == True or not not plan.quest or plan.script == 'RangingGuild'


class LevelerSession:
    plan = None
    remaining_ms = 0
    _progress = ''
    _progress_at = 0
    _sampled_at = None

    def __init__(self, memory):
        self.memory = memory
        self._failures = Record({})

    def start(self, plan, now, random):
        self.plan = plan
        self.memory.objective = plan.objective
        self.memory.attempted[plan.objective] = now
        self.remaining_ms = (10 + min(1, max(0, random())) * 10) * 60000
        self._progress_at = now
        self._progress = ''
        self._sampled_at = None

    def observe(self, signature, now):
        if signature == self._progress:
            return
        self._progress = signature
        self._progress_at = now

    def stalled(self, now):
        return now - self._progress_at > 180000

    def work(self, elapsed_ms):
        self.remaining_ms -= max(0, elapsed_ms)

    def sample_work(self, now, training):
        if self.plan and training and self._sampled_at is not None:
            self.work(min(2000, now - self._sampled_at))
        self._sampled_at = now

    def resupply(self, now):
        plan = self.plan
        if not plan:
            return
        self.memory.objective = plan.objective
        self.memory.attempted[plan.objective] = now
        self._failures.pop(plan.id, None)
        self.plan = None

    def failure(self, now):
        plan = self.plan
        if not plan:
            return 'reset'
        _v1 = self._failures.get(plan.id)
        count = ((_v1 if _v1 is not None else 0)) + 1
        self._failures[plan.id] = count
        if not uses_activity_cooldown(plan):
            if count < 3:
                return 'reset'
            self._failures.pop(plan.id, None)
            self.plan = None
            return 'rotate'
        if count == 1:
            return 'reset'
        self.memory.cooldowns[plan.id] = now + 15 * 60000
        self.memory.objective = None
        self.plan = None
        return 'rotate'

    def death(self, now):
        self.memory.deaths += 1
        if (self.plan.death_walk if self.plan is not None else None):
            self.resupply(now)
            return 'reset'
        return self.failure(now)

    def complete(self, now, objective_met):
        plan = self.plan
        if not plan:
            return
        self.memory.recent = (list(self.memory.recent) + [plan.id])[-6:]
        self.memory.attempted[plan.objective] = now
        self.memory.objective = (plan.objective if objective_met and (plan.output or plan.quest or plan.prerequisite_levels) else None)
        self._failures.pop(plan.id, None)
        self.plan = None
