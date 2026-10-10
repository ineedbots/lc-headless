"""Keeping a bot going while it runs: the run manager and the stall guard. Mirrors rs2b0t's
runtime/RunManager.ts, and the watchdog in runtime/Supervisor.ts with StallGuard.ts (MIT, see third_party/rs2b0t).

The host calls the runtime's upkeep once a server tick. The run manager turns run back on once there's energy
for it. The stall guard watches for progress: a change of tile, experience, or execution.note_progress().
After scripting.stallMinutes without any, it walks back to the bot's recovery_anchor() when that's more than
8 tiles away, and otherwise restarts the bot.
"""

import _core
from rs2004.events import SKILL_NAMES
from rs2004.geometry import Tile

__all__ = ['run_manager']

RUN_CHECK_MS = 1500
# Under attack, any energy at all is worth spending to get away.
ENERGY_MIN_ATTACKED = 1
ANCHOR_RADIUS = 8
RETRY_MS = 15 * 60000
# A gap this long between ticks means the account was away, as during a relog; the wait isn't a stall.
GAP_MS = 5000
MINUTE_MS = 60000


def resolve_run_policy(override, run_auto, energy_min):
    """(run_auto, energy_min): the script's override, where it sets them, over the config's."""
    if override is not None:
        if override.get('run_auto') is not None:
            run_auto = override['run_auto']
        if override.get('energy_min') is not None:
            energy_min = override['energy_min']
    return run_auto, max(0, min(100, energy_min))


def should_enable_run(run_on, in_combat, energy, energy_min, modal_open):
    """Whether to turn run on now. Clicking run makes the server close the open modal, which can shut a bank
    mid-trip, so not while one is open, unless you're being attacked: getting away matters more."""
    if run_on:
        return False
    if modal_open and not in_combat:
        return False
    return energy >= (ENERGY_MIN_ATTACKED if in_combat else energy_min)


class _RunManager:
    """Turns run back on: scripting.runAuto and scripting.runEnergyMin, or the script's override()."""

    def __init__(self):
        self.run_auto = True
        self.energy_min = 20
        self._override = None
        self._next_check = 0

    def configure(self, run_auto, energy_min):
        self.run_auto = run_auto
        self.energy_min = energy_min
        self._override = None
        self._next_check = 0

    def override(self, run_auto=None, energy_min=None):
        """Replaces the config's choices for this script. The last call wins as a whole, and one with neither
        goes back to the config's."""
        if run_auto is None and energy_min is None:
            self._override = None
        else:
            self._override = {'run_auto': run_auto, 'energy_min': energy_min}

    def policy(self):
        """(run_auto, energy_min) as they stand."""
        return resolve_run_policy(self._override, self.run_auto, self.energy_min)

    def tick(self, now):
        """Turns run on when it should be; True when it did. Checks every 1.5 s, or at once when you're hit."""
        run_on = _core.is_running()
        in_combat = _core.in_combat()
        if now < self._next_check and not (in_combat and not run_on):
            return False
        self._next_check = now + RUN_CHECK_MS
        run_auto, energy_min = self.policy()
        if not run_auto or not _core.can_set_run():
            return False
        if not should_enable_run(run_on, in_combat, _core.get_run_energy(), energy_min, _core.get_main_modal() != -1):
            return False
        _core.set_run(True)
        return True


class StallGuard:
    """Notices a bot that has stopped making progress: no change of tile, no experience and no
    note_progress() for limit_ms. A recovery is due once, then again no sooner than 15 minutes later."""

    def __init__(self):
        self.limit_ms = 0
        self.reset(0)

    def configure(self, minutes):
        self.limit_ms = minutes * MINUTE_MS

    def reset(self, now):
        self.last_progress = now
        self.last_tile = None
        self.last_xp = None
        self.last_seen = None
        self.last_recovery = None

    def busy(self, now):
        """Something else has taken over, such as a random event; that isn't a stall."""
        self.last_progress = now
        self.last_seen = now

    def observe(self, now, tile, xp, noted):
        """Records this tick: tile as (x, z, level), xp as the total, noted as when note_progress() was last
        called or None. True when a recovery is due."""
        if self.last_seen is not None and now - self.last_seen > GAP_MS:
            self.last_progress = now
        self.last_seen = now
        if noted is not None and noted > self.last_progress:
            self.last_progress = noted
        if tile != self.last_tile:
            self.last_tile = tile
            self.last_progress = now
        if xp != self.last_xp:
            self.last_xp = xp
            self.last_progress = now
        if self.limit_ms <= 0 or now - self.last_progress <= self.limit_ms:
            return False
        if self.last_recovery is not None and now - self.last_recovery <= RETRY_MS:
            return False
        self.last_recovery = now
        return True


def total_xp():
    return sum([_core.get_experience(skill) for skill in SKILL_NAMES.keys()])


def here():
    return (_core.get_x(), _core.get_z(), _core.get_level())


def anchor_is_far(anchor, x, z, level):
    """Whether walking back to the anchor would get anywhere: more than 8 tiles off, or on another level."""
    return anchor.level != level or max(abs(anchor.x - x), abs(anchor.z - z)) > ANCHOR_RADIUS


def recover(bot, minutes, say):
    """The stall guard's recovery: walk back to the anchor, or ask for a restart. Use with yield from; gives
    'recovered' or 'restart'."""
    x, z, level = here()
    say(f'stall guard: no progress for {minutes} min at ({x}, {z}, {level})')
    anchor = bot.recovery_anchor()
    if anchor is not None:
        anchor = Tile.from_tile(anchor)
    if anchor is not None and anchor_is_far(anchor, x, z, level):
        say(f'stall guard: walking back to {anchor}')
        from rs2004.traversal import traversal
        arrived = yield from traversal.walk_resilient(anchor, radius=3, attempts=3, log=say)
        if arrived:
            return 'recovered'
        say('stall guard: the walk back failed; restarting the bot')
    else:
        say('stall guard: stuck where it should be, or no recovery_anchor(); restarting the bot')
    return 'restart'


run_manager = _RunManager()
stall_guard = StallGuard()
