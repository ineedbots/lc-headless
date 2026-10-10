"""Waiting. Mirrors rs2b0t's api/execution/Execution.ts (MIT, see third_party/rs2b0t), with generators where
rs2b0t awaits: each wait is used with yield from, from loop() or anything it calls, and returns its result.

    found = yield from execution.delay_until(lambda: inventory.is_full(), 3000)
"""

import _core

__all__ = ['delay', 'delay_ticks', 'delay_until', 'delay_until_ticks', 'note_progress', 'Update', 'Ticks']


class Update:
    """Yielded to resume after the next pump that decoded a packet, when the state may have changed, or
    after timeout_ms when one is given, whichever comes first."""

    def __init__(self, timeout_ms=None):
        self.timeout_ms = timeout_ms

    def __repr__(self):
        return f'Update({self.timeout_ms})'


class Ticks:
    """Yielded to resume after count more server ticks."""

    def __init__(self, count):
        if not isinstance(count, int) or isinstance(count, bool) or count < 1:
            raise ValueError('Ticks needs a count of 1 or more')
        self.count = count

    def __repr__(self):
        return f'Ticks({self.count})'


def delay(ms):
    """Waits at least ms milliseconds of wall-clock time."""
    yield int(ms)


def delay_ticks(n):
    """Waits n server ticks, about 600 ms each."""
    if n > 0:
        yield Ticks(n)


def delay_until(cond, timeout_ms=6000):
    """True as soon as cond() holds, checked now and after every update; False once timeout_ms has passed."""
    deadline = _core.step_time() + timeout_ms
    while True:
        if cond():
            return True
        remaining = deadline - _core.step_time()
        if remaining <= 0:
            return False
        yield Update(remaining)


def delay_until_ticks(cond, max_ticks):
    """The same, checked once a server tick, for at most max_ticks ticks."""
    start = _core.tick()
    while True:
        if cond():
            return True
        # A fresh login starts the tick count over, which ends the wait too.
        if _core.tick() >= start + max_ticks or _core.tick() < start:
            return False
        yield Ticks(1)


def note_progress():
    """Tells the stall guard about progress it can't see, such as a completed trade. Calling it every loop
    turns stall detection off."""
    _core.note_progress()
