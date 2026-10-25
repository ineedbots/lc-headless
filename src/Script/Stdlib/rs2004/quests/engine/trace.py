"""Step tracing for the quest engine: rs2b0t's api/ai/quests/engine/trace.ts (MIT, see thirdparty/rs2b0t).

Why: a leg keeps one description for its run: 'smith 8 nails' covers mining 4 iron, mining 8 coal, 2 furnace trips and
an anvil. Why: a log that prints a step once and suppresses repeats goes silent for minutes, which looks like a hang."""

import math

__all__ = ['HEARTBEAT_ATTEMPTS', 'HEARTBEAT_MS', 'FAIL_WARN', 'format_duration', 'format_tile', 'inv_delta', 'StepTracker']

# Re-announce a repeating step after this many attempts,
HEARTBEAT_ATTEMPTS = 5
# or after this long.
HEARTBEAT_MS = 15000

# A failing step never reaches the no-progress watchdog, so it warns on its own.
FAIL_WARN = 5


def format_duration(ms):
    if ms < 1000:
        return f'{round(ms)}ms'
    if ms < 60000:
        return f'{ms / 1000:.1f}s'
    seconds = str(round((ms % 60000) / 1000))
    if len(seconds) < 2:
        seconds = '0' + seconds
    return f'{math.floor(ms / 60000)}m{seconds}s'


def format_tile(tile):
    if tile is None:
        return '(no tile)'
    level = f',L{tile.level}' if tile.level > 0 else ''
    return f'({tile.x},{tile.z}{level})'


def inv_delta(before, after):
    """What one step changed in the pack, by name."""
    names = set(list(before.keys()) + list(after.keys()))
    parts = []
    for name in sorted(list(names)):
        a = before.get(name, 0)
        b = after.get(name, 0)
        if a != b:
            parts.append(f'{name} {a}→{b}')
    return ', '.join(parts) if len(parts) > 0 else 'no inventory change'


# Why: keyed on quest plus step description, since the engine re-decides from scratch every tick and "the same step"
# is only recognisable by its description.
class StepTracker:
    """Attempt counting and elapsed time for the step being retried."""

    def __init__(self):
        self.key = ''
        self.attempt = 0
        self.since = 0
        self.last_beat = 0

    def open(self, key, now):
        """Called once a pass, before the step runs. The 1-based attempt number."""
        if key != self.key:
            self.key = key
            self.attempt = 0
            self.since = now
            self.last_beat = now
        self.attempt += 1
        return self.attempt

    def attempts(self):
        return self.attempt

    def elapsed(self, now):
        return now - self.since

    def beat(self, now):
        """True when a repeated step has been quiet long enough to say so again."""
        if self.attempt <= 1:
            return False
        if self.attempt % HEARTBEAT_ATTEMPTS == 0 or now - self.last_beat >= HEARTBEAT_MS:
            self.last_beat = now
            return True
        return False

    def reset(self):
        self.key = ''
        self.attempt = 0
        self.since = 0
        self.last_beat = 0
