"""Damage dealt, read off the xp: rs2b0t's scripts/JiveKQ/stats.ts (MIT, see thirdparty/rs2b0t)."""


class CombatStats:
    """Damage and fighting time while a fight is live; dps() is their ratio."""

    def __init__(self):
        self.damage = 0
        self.fighting_ms = 0
        self._at = None
        self._xp = None
        self._active = False

    def observe(self, now, xp, active):
        if self._at is not None and self._active:
            self.fighting_ms += max(0, now - self._at)
            self.damage += max(0, xp - (self._xp if self._xp is not None else xp)) / 4
        self._at = now
        self._xp = xp
        self._active = active

    def dps(self):
        return self.damage / (self.fighting_ms / 1000) if self.fighting_ms > 0 else 0
