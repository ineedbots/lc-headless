"""Ported from rs2b0t's src/bot/api/ai/quests/defs/upass/area1.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.dialogue import modals
from rs2004.entities import ground_items, locs
from rs2004.game import game, skills
from rs2004.items import inventory
from rs2004.messages import game_messages
from rs2004.quests.defs.upass.areas import UP_ITEM, UP_LOC, UP_ORBS, UP_TILE, count_held
from rs2004.quests.defs.upass.bridge import loc_by_id
from rs2004.quests.defs.upass.stall import stalled_journey
from rs2004.quests.exec.primitives import drive_dialog
from rs2004.quests.exec.prompts import drive_until, held_id, settle_scene

__all__ = ['ORB_SITES', 'orbs_held', 'take_trapped_orb', 'take_ground_orb', 'burn_orbs', 'sweep_orbs', 'enter_well']

ORB_SITES = [
    Record({'orb': UP_ITEM.ORB1, 'tile': UP_TILE.LOGTRAP, 'from_trap': True}),
    Record({'orb': UP_ITEM.ORB2, 'tile': UP_TILE.ORB2, 'from_trap': False}),
    Record({'orb': UP_ITEM.ORB3, 'tile': UP_TILE.ORB3, 'from_trap': False}),
    Record({'orb': UP_ITEM.ORB4, 'tile': UP_TILE.ORB4, 'from_trap': False}),
]


def orbs_held(snap):
    """How many orbs the snapshot's pack holds."""
    return count_held(snap, UP_ORBS)


# Why: `[timer,upass_trap]` is set to 1 tick across map squares 0_37_151 and 0_38_151 and hits for `hp/10 + 1` on a spear and `base_hp*8/100 + 1` on a spring whenever you end a tick on one, and the corridor is a single tile wide at every one of the 20 trap tiles.
# Why: so the corridor is crossed like the spiked grid, on an op-click with the journal held open, which suspends the timer. No plain walks: `MoveClickHandler` clears the modal on any move that isn't an op-click, and the walker re-clicks every few tiles.
# Why: Op-clicks require a loc in the build area, so traverse the long corridor through its stepping stones, traps, and tablets.
STONES = [
    Record({'id': UP_LOC.SPEARTRAP, 'op': 'Search'}),
    Record({'id': UP_LOC.SPRINGTRAP, 'op': 'Search'}),
    Record({'id': UP_LOC.LOGTRAP_TRIGGER, 'op': 'Search'}),
    Record({'id': UP_LOC.TABLET_EAST, 'op': 'Read'}),
    Record({'id': UP_LOC.TABLET_WEST, 'op': 'Read'}),
]
STONE_GAIN = 3
STONE_SEARCH = 40


def cheb(a, b):
    return max(abs(a.x - b.x), abs(a.z - b.z))


def near(tile, radius):
    now = game.tile()
    return now is not None and cheb(now, tile) <= radius


def stone_toward(dest, spent, log):
    from_ = game.tile()
    if not from_:
        return None
    mine = cheb(from_, dest)
    reachable = []
    for stone in STONES:
        for loc in locs.query().where(lambda loc: loc.id == stone.id).action(stone.op).within(STONE_SEARCH).results():
            if cheb(loc.tile(), dest) + STONE_GAIN <= mine and not (f'{loc.tile().x},{loc.tile().z}' in spent):
                reachable.append(Record({'loc': loc, 'op': stone.op}))
    if len(reachable) == 0:
        return None
    pick = sorted(reachable, key=lambda a: cheb(a.loc.tile(), dest))[0]
    at = pick.loc.tile()
    spent.add(f'{at.x},{at.z}')
    log(f'stall: stepping to {(pick.loc.name if pick.loc.name is not None else pick.loc.id)} at ({at.x},{at.z})')

    def _fn4():
        return pick.loc.interact(pick.op)
        if False:
            yield
    return Record({
        'send': _fn4,
        'arrived': lambda: near(at, 1),
        'what': f'{(pick.loc.name if pick.loc.name is not None else pick.loc.id)} at ({at.x},{at.z})',
    })


def corridor_hop(dest, what, in_range, send, arrived, log):
    """Reach `dest` and do its op-click, stepping over the traps with the journal held open throughout."""
    if arrived():
        return True
    yield from settle_scene()
    spent = set()
    _result5 = yield from stalled_journey(Record({
        'goal': Record({'send': send, 'arrived': arrived, 'what': what, 'in_range': in_range}),
        'next_stone': lambda: stone_toward(dest, spent, log),
        'log': log,
    }))
    return _result5


# Why: the disarm is a `stat_random(thieving, 160, 300)` roll and a fail springs the log (stun, forced move, damage), so retry inside the step; once per decide cycle would walk the corridor between every roll.
DISARM_ATTEMPTS = 5


def take_trapped_orb(log):
    """The hanging-log trap yields the first orb once disarmed."""
    if held_id(UP_ITEM.ORB1.id) > 0:
        return True

    def find_trigger():
        return loc_by_id(UP_LOC.LOGTRAP_TRIGGER, None, STONE_SEARCH)

    def _fn6():
        trigger = find_trigger()
        op = ((trigger.actions() if trigger is not None else None) or [None])[0]
        return trigger is not None and op is not None and trigger.interact(op)
        if False:
            yield
    arrived = yield from corridor_hop(UP_TILE.LOGTRAP, 'the hanging-log trigger', lambda: find_trigger() is not None, _fn6, lambda: near(UP_TILE.LOGTRAP, 1), log)
    if not arrived:
        # Why: the trigger is deleted for 50 ticks once its orb is taken, so absent while standing on it means burned; absent from across the corridor only means out of the build area.
        if near(UP_TILE.LOGTRAP, 8) and find_trigger() is None:
            log('no hanging-log trigger rock at the orb — already burned')
            return True
        return False
    # Why: springing the log blows you 5 tiles west, clear of every trap tile, so the retries stay local.
    for attempt in range(DISARM_ATTEMPTS):
        if attempt > 0:
            trigger = find_trigger()
            op = ((trigger.actions() if trigger is not None else None) or [None])[0]
            if not trigger or not op or not (trigger.interact(op)):
                log('the log trap trigger stopped answering')
                return False
        # Why: the trap opens with `~mesbox`, a main modal `driveDialog` can't dismiss, so the "do you want to disarm it?" choice underneath is never answered. Close the modal first, then drive the choice.
        mark = game_messages.mark()
        yield from modals.close_if_open()
        yield from drive_dialog(["Yes, I'll give it a go"], log)
        _w7 = yield from drive_until(lambda: held_id(UP_ITEM.ORB1.id) > 0, [], log, 12000)
        if _w7:
            return True
        # Why: once the orb's bit is set the trap answers "you hear it resetting" instead, which is the only way to tell "already burned" from "the roll failed": the bit isn't on the wire and the trap respawns 50 ticks after it's taken.
        if game_messages.saw_since(mark, 'resetting'):
            log('the log trap has already given up its orb')
            return True
        log(f'the log trap sprang on attempt {attempt + 1}')
        yield from execution.delay_ticks(3)
    return False


def _has_id(id):
    return lambda item: item.id == id


# Why: nothing records which orbs are dark: the varp is untransmitted and the journal only says "after destroying four orbs" once the well has been used. An orb neither in the pack nor on its floor tile has gone into the furnace.
def take_ground_orb(orb, tile, log):
    if held_id(orb.id) > 0:
        return True

    # Why: all 4 orbs display as "Orb of light", so the ground pile is matched on id.
    def find_drop():
        return ground_items.query().where(_has_id(orb.id)).within(STONE_SEARCH).nearest()

    def _fn8():
        drop = find_drop()
        return drop is not None and drop.interact('Take')
        if False:
            yield
    took = yield from corridor_hop(tile, f'the Orb of light at ({tile.x},{tile.z})', lambda: find_drop() is not None, _fn8, lambda: held_id(orb.id) > 0, log)
    if took:
        return True
    # Why: an orb absent from its floor tile has gone into the furnace; absent from across the corridor only means the client hasn't loaded that far.
    if near(tile, 8) and find_drop() is None:
        log(f'no Orb of light on the floor at ({tile.x},{tile.z}) — already burned')
        return True
    return False


# Why: `destroy_orboflight` is 4 ticks of messages before the orb leaves the pack, so a 1-tick gap fires the next use into a running script and the loop drops out after one orb.
# Why: the first orb doubles as the trip: using it on the furnace from across the corridor is an op-click, so the walk stalls, and the rest go in from there.
def burn_orbs(log):
    """Every orb in the pack, thrown into the furnace one at a time."""

    def held():
        return [orb for orb in UP_ORBS if held_id(orb.id) > 0]

    before = len(held())
    if before == 0:
        return True
    for pass_ in range(3):
        if not (len(held()) > 0):
            break
        for orb in held():
            def find_furnace():
                return locs.query().where(lambda loc: loc.id == UP_LOC.FURNACE).within(STONE_SEARCH).nearest()

            def _fn9():
                furnace = find_furnace()
                item = ([inv for inv in inventory.items() if inv.id == orb.id] or [None])[0]
                return furnace is not None and item is not None and item.use_on(furnace)
                if False:
                    yield
            gone = yield from corridor_hop(UP_TILE.FURNACE, f'the {orb.name} on the furnace', lambda: find_furnace() is not None, _fn9, lambda: held_id(orb.id) == 0, log)
            if not gone:
                log(f'the furnace would not take orb {orb.id} on pass {pass_ + 1}')
            yield from execution.delay_ticks(4)
    left = len(held())
    log(f'burned {before - left} orb(s) in the furnace, {left} still lit')
    return left == 0


# Why: a snapshot can't say which orbs are dark: the bit isn't on the wire, a burned orb has left the pack, and the trap and ground spawns refuse a second one silently. So the sweep is one step with its own tally, and the well is the oracle: it only descends once all 4 are dark.
def sweep_orbs(log):
    """Take every orb the pack can hold, then burn the lot in one trip, then climb the well."""
    for site in ORB_SITES:
        if site.from_trap:
            _w11 = yield from take_trapped_orb(log)
            _c10 = _w11
        else:
            _w12 = yield from take_ground_orb(site.orb, site.tile, log)
            _c10 = _w12
        took = _c10
        if not took:
            log(f'could not settle the orb at ({site.tile.x},{site.tile.z})')
            return False
        # Why: the corridor traps are the only damage source down here and a death mid-sweep leaves no sign in the log, so say what's left after each site.
        log(f"orb sweep: {skills.effective('hitpoints')}/{skills.level('hitpoints')} hp, {inventory.free()} free")
        # Why: a full pack can't take the next orb, so the furnace trip happens early.
        _c13 = inventory.free() == 0
        if _c13:
            _w14 = yield from burn_orbs(log)
            _c13 = not (_w14)
        if _c13:
            return False
    _w15 = yield from burn_orbs(log)
    if not (_w15):
        return False
    _result16 = yield from enter_well(log)
    return _result16


def enter_well(log):
    """The well only takes you down once all 4 orbs are dark."""

    def down():
        return (((game.tile().z if game.tile() is not None else None) if (game.tile().z if game.tile() is not None else None) is not None else 9999)) < 9664

    def find_well():
        return loc_by_id(UP_LOC.WELL, None, STONE_SEARCH)

    def _fn17():
        well = find_well()
        op = ((well.actions() if well is not None else None) or [None])[0]
        return well is not None and op is not None and well.interact(op)
        if False:
            yield
    climbed = yield from corridor_hop(UP_TILE.WELL, 'the well', lambda: find_well() is not None, _fn17, down, log)
    # Why: `cave_well` runs 3 zero-tick delays before the teleport, so the descent can land a tick after the journey has given up.
    _c18 = climbed
    if not _c18:
        _w19 = yield from execution.delay_until_ticks(down, 6)
        _c18 = (_w19)
    if _c18:
        return True
    log(('never got within sight of the well at the west end of the first cavern' if find_well() is None else 'the well blasted the player back out — an orb is still lit'))
    return False

