"""Ported from rs2b0t's src/bot/api/ai/quests/defs/upass/stall.ts (MIT, see thirdparty/rs2b0t)."""

import _core
import math
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.entities import locs
from rs2004.game import game, reader
from rs2004.quests.defs.upass.journal import UPASS
from rs2004.tabs import quests

__all__ = ['release_journal', 'stalled_approach', 'stalled_journey', 'stalled_walk', 'stalled_walk_to_loc', 'stalled_crossing']

# Why: An open journal blocks normal timer traps through `canAccess()`; soft timers still run.
# Why: the walk has to be an op-click. `MoveClickHandler` calls `clearPendingAction()`, which closes the modal, for every move except `opClick`.
POLL_TICKS = 2
# Why: The journal blocks op scripts through `canAccess()`; three stable polls confirm the player has stopped beneath it.
IDLE_POLLS = 3


def tile_now():
    return game.tile()


def modal_open():
    return reader.modals().main != -1


def press_journal():
    """Send the journal button without waiting; the caller manages timing."""
    return quests.press_journal(UPASS)


def release_journal():
    if modal_open():
        _core.close_interfaces()
        yield from execution.delay_ticks(1)


def stalled_approach(opts):
    """Cross timer-trapped ground on an op-click, holding the quest journal open for every step of the walk. Leaves the modal closed; whether the op itself then ran is the caller's `arrived` to decide."""
    send = opts.send
    what = opts.what
    arrived = opts.arrived
    log = opts.log
    timeout_ms = (opts.timeout_ms if opts.timeout_ms is not None else 30000)
    if arrived():
        return True
    from_ = tile_now()
    _w2 = yield from send()
    if not (_w2):
        log(f'stall: {what} would not send')
        return False

    # Why: the journal must land in its own tick: a modal opened in the tick `moveClickRequest` settles latches it true and `updateMovement` freezes at the first 8x8 zone boundary because the engine queue can't drain while busy. The press waits on the first step, so the caller stages far enough back to still be on safe ground then.
    def _fn3():
        now = tile_now()
        return now is not None and from_ is not None and (now.x != from_.x or now.z != from_.z)
    moved = yield from execution.delay_until_ticks(_fn3, 8)
    if not moved:
        # Why: already on the target means no walk and no trap tiles, so wait the op out; a journal here would only hide the script.
        _result4 = yield from execution.delay_until_ticks(arrived, math.ceil(timeout_ms / 600))
        return _result4
    if not press_journal():
        log('stall: the quest journal button never sent — traps are live')
        return False
    try:
        result = yield from hold_journal_walk(opts, arrived, timeout_ms, log)
    except Exception as e:
        if opts.hold != True:
            yield from release_journal()
        raise e
    if opts.hold != True:
        yield from release_journal()
    return result


def hold_journal_walk(opts, arrived, timeout_ms, log):
    deadline = _core.step_time() + timeout_ms
    opened = False
    last = tile_now()
    idle = 0
    while _core.step_time() < deadline:
        if arrived():
            return True
        abort = opts.abort
        if abort is not None and abort() == True:
            at = tile_now()
            log(f'stall: attempt lost at ({(at.x if at is not None else None)},{(at.z if at is not None else None)})')
            return False
        at = tile_now()
        idle = (idle + 1 if at is not None and last is not None and at.x == last.x and at.z == last.z else 0)
        last = at
        if idle >= IDLE_POLLS and modal_open():
            log(f'stall: the walk stopped at ({(at.x if at is not None else None)},{(at.z if at is not None else None)}) and the journal is up — whatever was clicked cannot run until it comes down')
            return False
        if modal_open():
            opened = True
        elif opened and not arrived():
            # Why: anything the server pushes closes the modal and re-arms the traps, so it goes straight back up.
            press_journal()
        yield from execution.delay_ticks(POLL_TICKS)
    here = tile_now()
    log(f'stall: timed out at ({(here.x if here is not None else None)},{(here.z if here is not None else None)}) — never reached the far side')
    return False


def finish_goal(goal, log):
    """Finish the last click with the journal down. Why: a goal keyed on what its script did can't come true while the journal is up, because `tryInteract` is gated on `canAccess()`. The stones have already carried you onto the goal, and a goal tile is never a trap tile, so the modal comes down and the op gets its own ticks."""
    yield from release_journal()
    _w6 = yield from execution.delay_until_ticks(goal.arrived, 8)
    if _w6:
        return True
    _w7 = yield from goal.send()
    if not (_w7):
        log(f'stall: {goal.what} would not send with the journal down')
        return False
    ran = yield from execution.delay_until_ticks(goal.arrived, 15)
    # Why: the journey walks on over trap tiles and only re-presses the journal after its next op-click has moved you, so put the modal back up before the walk.
    if not ran:
        press_journal()
    return ran


def with_fields(stone, log):
    fields = {}
    for key, value in stone._fields.items():
        fields[key] = value
    fields['hold'] = True
    fields['log'] = log
    return Record(fields)


def stalled_journey(opts):
    """Reach `goal` over a chain of stalled op-clicks, holding the journal across every leg of the journey. Why: an op-click can only name a loc in the client's build area, which lags you, so the reach is far shorter than the corridor."""
    try:
        result = yield from journey_legs(opts)
    except Exception as e:
        yield from release_journal()
        raise e
    yield from release_journal()
    return result


def journey_legs(opts):
    goal = opts.goal
    next_stone = opts.next_stone
    log = opts.log
    legs = (opts.legs if opts.legs is not None else 14)
    for leg in range(legs):
        if goal.arrived():
            return True
        if goal.in_range():
            _w9 = yield from stalled_approach(with_fields(goal, log))
            if _w9:
                return True
            _w10 = yield from finish_goal(goal, log)
            if _w10:
                return True
        stone = next_stone()
        if not stone:
            at = tile_now()
            log(f'stall: nothing at ({(at.x if at is not None else None)},{(at.z if at is not None else None)}) steps toward {goal.what}')
            return False
        yield from stalled_approach(with_fields(stone, log))
    log(f'stall: {legs} legs without reaching {goal.what}')
    return goal.arrived()


def stalled_walk(opts):
    """`stalledApproach` where the op-click is an op on a loc found on the far side."""
    find = opts.find
    op = opts.op

    def send():
        target = find()
        return target is not None and target.interact(op)
        if False:
            yield
    fields = {}
    for key, value in opts._fields.items():
        fields[key] = value
    fields['what'] = f"'{op}' on the far side"
    fields['send'] = send
    return stalled_approach(Record(fields))


def _loc_is(loc_id):
    return lambda loc: loc.id == loc_id


def stalled_walk_to_loc(loc_id, op, arrived, log, within=24):
    """`stalledWalk` against a loc looked up by id."""
    return stalled_walk(Record({
        'find': lambda: locs.query().where(_loc_is(loc_id)).action(op).within(within).nearest(),
        'op': op,
        'arrived': arrived,
        'log': log,
    }))


# Why: whether the modal beats you onto the trapped ground is a 1-tick race, since the press can't go out until the op-click has moved you or the walk freezes at the first zone boundary. A short approach can't win every time, so a lost attempt recovers to the lip and goes again.
def stalled_crossing(opts):
    attempts = (opts.attempts if opts.attempts is not None else 4)
    for attempt in range(1, attempts + 1):
        # Why: the crossing can land after `stalledWalk` has given up on its oracle, so ask again before recovering or you walk back east to re-approach a grid you're already west of.
        if opts.arrived():
            return True
        _w14 = yield from stalled_walk(opts)
        if _w14:
            return True
        if opts.arrived():
            return True
        if attempt == attempts:
            break
        opts.log(f'stall: attempt {attempt} did not carry the crossing — recovering')
        _w15 = yield from opts.recover()
        if not (_w15):
            opts.log('stall: could not get back to the approach tile')
            return False
    return opts.arrived()

