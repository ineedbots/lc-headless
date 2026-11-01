"""Ported from rs2b0t's src/bot/api/ai/quests/defs/ikov/dungeon.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import chat_dialog
from rs2004.entities import ground_items, locs
from rs2004.game import direct_navigator, game
from rs2004.items import equipment, inventory
from rs2004.messages import game_messages
from rs2004.quests.defs.ikov.areas import ARROWS_WANTED, ICE_CHESTS, IKOV_LOC, IKOV_NAME, IKOV_OBJ, IKOV_TILE, LAVA_BRIDGE_ZONE, in_dark_room, in_trap_pit, past_south_gate, west_of_bridge
from rs2004.quests.defs.ikov.gear import RANGED_ARMOUR_NAMES
from rs2004.quests.defs.ikov.supplies import light_candle
from rs2004.quests.exec.prompts import drive_until, held_id, settle_scene
from rs2004.traversal import traversal

__all__ = ['south_gate_open', 'temple_walk', 'wearing_boots', 'wear_fear_pendant', 'escape_pocket', 'pull_trap_lever', 'arrows_secured', 'boots_step', 'unlock_south_gate', 'stock_ice_arrows']

WALK_MS = 300000
CHEST_ROUNDS = 3
CHEST_EMPTY = 'search the chest, but find nothing'
# Why: `%ikov_dungeon` is untransmitted and no journal line moves for the lever, so having stood in the ice cavern is the only evidence the south gate is unlocked.
south_gate_seen_open = False


def south_gate_open():
    """Whether this session has seen the south gate open; false sends the next descent across the lava."""
    return south_gate_seen_open


# Why: the bridge isn't a baked edge but its tiles are walkable, so a route across them ferries the bot to the wrong side.
def temple_walk(dest, radius, log):
    return traversal.walk_resilient(dest, radius=radius, attempts=3, timeout_ms=WALK_MS, avoid_zones=[LAVA_BRIDGE_ZONE], log=log)


def loc_by_id(id, within=8):
    return locs.query().where(lambda l: l.id == id).within(within).nearest()


# Why: `~mesbox` blocks on `p_pausebutton`, so the script that raised it has not run its `inv_del` or its `setbit` yet, and the next op is swallowed while the box is up.
def clear_box():
    """Click through whatever message box the last op raised."""
    for i in range(12):
        if chat_dialog.can_continue():
            yield from chat_dialog.continue_()
            yield from execution.delay_ticks(1)
            continue
        if not chat_dialog.is_open():
            return
        yield from execution.delay_ticks(1)


def wearing_boots():
    return equipment.contains(IKOV_NAME.BOOTS)


def wear_fear_pendant(log):
    """The Door of Fear only opens northward for a character wearing Lucien's pendant."""
    if equipment.contains(IKOV_NAME.PENDANT_LUCIEN):
        return True
    if held_id(IKOV_OBJ.PENDANT_LUCIEN) == 0:
        log('ikov: no pendant of lucien to wear — the Door of Fear stays shut')
        return False
    _result1 = yield from equipment.equip(IKOV_NAME.PENDANT_LUCIEN)
    return _result1


def climb_dark_stairs_up(log):
    _w2 = yield from temple_walk(IKOV_TILE.DARK_STAIRS_UP, 1, log)
    if not (_w2):
        return False
    stairs = loc_by_id(IKOV_LOC.DARK_STAIRS_UP, 4)
    if not stairs or not (stairs.interact('Climb-up')):
        log('ikov: no dark stairs out of the boots room')
        return False

    def _fn3():
        t = game.tile()
        return t is not None and not in_dark_room(t)
    out = yield from execution.delay_until(_fn3, 10000)
    if out:
        yield from settle_scene()
    return out


def climb_trap_ladder(log):
    _w4 = yield from temple_walk(IKOV_TILE.TRAP_PIT_LADDER, 1, log)
    if not (_w4):
        return False
    ladder = loc_by_id(IKOV_LOC.TRAP_LADDER, 4)
    if not ladder or not (ladder.interact('Climb-up')):
        log('ikov: no ladder out of the trap pit')
        return False

    def _fn5():
        t = game.tile()
        return t is not None and not in_trap_pit(t)
    out = yield from execution.delay_until(_fn5, 10000)
    if out:
        yield from settle_scene()
    return out


# Why: the crossing is a zone timer with no loc, so stepping onto the bridge is the action and the far side is the only oracle.
def cross_bridge(go_west, log):
    start = (IKOV_TILE.BRIDGE_EAST if go_west else IKOV_TILE.BRIDGE_WEST)
    step = (IKOV_TILE.BRIDGE_ZONE_EAST if go_west else IKOV_TILE.BRIDGE_ZONE_WEST)

    def landed():
        t = game.tile()
        return t is not None and west_of_bridge(t) == go_west

    if landed():
        return True
    if not wearing_boots():
        log('ikov: refusing the lava bridge without the boots of lightness')
        return False
    # Why: the server tests `weight >= 0` in grams and the client gets truncated kilograms, so 0 could still be 100 grams over.
    if game.weight() >= 0:
        log(f'ikov: the pack reads {game.weight()}kg — the bridge gives way at anything but negative weight')
        return False
    _w6 = yield from temple_walk(start, 1, log)
    if not (_w6):
        return False
    log(f"ikov: stepping onto the lava bridge, heading {('west' if go_west else 'east')}")
    # Why: the bridge moves you a tick after you step on, and a walk that polls every 2 ticks misses the tile, re-clicks it from the far side and is carried back, so this is one click.
    _core.walk_to(step.x, step.z, False)
    crossed = yield from execution.delay_until(landed, 12000)
    if not crossed:
        log('ikov: the bridge did not carry us across — retrying')
        return False
    yield from settle_scene()
    return True


def escape_pocket(log):
    """Climb, cross or clamber out of whichever sealed part of the temple the bot woke up in."""
    here = game.tile()
    if not here:
        return False
    if in_dark_room(here):
        log('ikov: climbing out of the boots room')
        _result7 = yield from climb_dark_stairs_up(log)
        return _result7
    if in_trap_pit(here):
        log('ikov: climbing out of the trap pit')
        _result8 = yield from climb_trap_ladder(log)
        return _result8
    if west_of_bridge(here):
        log('ikov: crossing back over the lava')
        _result9 = yield from cross_bridge(False, log)
        return _result9
    return True


def slash_web(log):
    if loc_by_id(IKOV_LOC.WEB, 6) is None:
        return True
    knife = ([i for i in inventory.items() if i.id == IKOV_OBJ.KNIFE] or [None])[0]
    if not knife:
        log('ikov: the web needs a knife and the pack has none')
        return False
    # Why: `slash_checker` only reads the equipped weapon, so `Slash` refuses a packed knife; the `oplocu` branch names the knife explicitly.
    for attempt in range(8):
        web = loc_by_id(IKOV_LOC.WEB, 6)
        if not web:
            return True
        held = ([i for i in inventory.items() if i.id == IKOV_OBJ.KNIFE] or [None])[0]
        if not held or not (held.use_on(web)):
            return False
        _w10 = yield from execution.delay_until(lambda: loc_by_id(IKOV_LOC.WEB, 6) is None, 5000)
        if _w10:
            log(f'ikov: slashed the web after {attempt + 1} cut(s)')
            return True
    log('ikov: eight cuts and the web still holds')
    return False


def take_boots(log):
    if held_id(IKOV_OBJ.BOOTS) > 0:
        return True
    _w11 = yield from temple_walk(IKOV_TILE.BOOTS_WEB, 0, log)
    if not (_w11):
        return False
    _w12 = yield from slash_web(log)
    if not (_w12):
        return False
    yield from direct_navigator.walk_to(IKOV_TILE.BOOTS_SPAWN, 1, 8000)
    boots = ground_items.query().where(lambda g: g.id == IKOV_OBJ.BOOTS).within(6).nearest()
    if not boots:
        log(f'ikov: no boots of lightness at ({IKOV_TILE.BOOTS_SPAWN.x},{IKOV_TILE.BOOTS_SPAWN.z})')
        return False
    if not (boots.interact('Take')):
        return False
    _result13 = yield from execution.delay_until(lambda: held_id(IKOV_OBJ.BOOTS) > 0, 8000)
    return _result13


def fetch_boots(log):
    """Fetch and wear the boots; everything past the lava bridge depends on the negative weight."""
    if wearing_boots():
        return True
    if held_id(IKOV_OBJ.BOOTS) > 0:
        _result14 = yield from equipment.equip(IKOV_NAME.BOOTS)
        return _result14
    here = game.tile()
    if here and in_dark_room(here):
        _w15 = yield from take_boots(log)
        if not (_w15):
            return False
        _w16 = yield from equipment.equip(IKOV_NAME.BOOTS)
        if not (_w16):
            log('ikov: took the boots but could not wear them')
        _result17 = yield from climb_dark_stairs_up(log)
        return _result17
    _w18 = yield from escape_pocket(log)
    if not (_w18):
        return False
    _w19 = yield from light_candle(log)
    if not (_w19):
        return False
    _w20 = yield from temple_walk(IKOV_TILE.DARK_STAIRS_DOWN, 1, log)
    if not (_w20):
        return False
    stairs = loc_by_id(IKOV_LOC.DARK_STAIRS_DOWN, 6)
    if not stairs or not (stairs.interact('Climb-down')):
        log('ikov: no dark stairs down at the temple corridor')
        return False

    def _fn21():
        t = game.tile()
        return t is not None and in_dark_room(t)
    arrived = yield from execution.delay_until(_fn21, 10000)
    if not arrived:
        # Why: without a lit source the stairs drop you into a walled dead end and raise a box, which reads as "did not arrive".
        yield from clear_box()
        log('ikov: the dark stairs left us short — the candle was not lit')
        return False
    yield from settle_scene()
    return True


def pull_trap_lever(log):
    """Disarm and pull the trap lever. Both ops are no-ops once their stage has passed."""
    _w22 = yield from escape_pocket(log)
    if not (_w22):
        return False
    _w23 = yield from wear_fear_pendant(log)
    if not (_w23):
        return False
    _w24 = yield from temple_walk(IKOV_TILE.TRAP_LEVER, 1, log)
    if not (_w24):
        return False
    lever = loc_by_id(IKOV_LOC.TRAP_LEVER, 6)
    if not lever:
        log(f'ikov: no trap lever at ({IKOV_TILE.TRAP_LEVER.x},{IKOV_TILE.TRAP_LEVER.z})')
        return False
    log('ikov: searching the trap lever for traps')
    if not (lever.interact('Search for traps')):
        return False
    yield from execution.delay_ticks(3)
    yield from clear_box()
    again = loc_by_id(IKOV_LOC.TRAP_LEVER, 6)
    if not again or not (again.interact('Pull')):
        return False
    yield from execution.delay_ticks(4)
    yield from clear_box()
    # Why: an undisarmed pull drops the player down a shaft, and the ladder out is the only way back.
    here = game.tile()
    if here and in_trap_pit(here):
        log('ikov: the trap fired — climbing back out')
        _result25 = yield from climb_trap_ladder(log)
        return _result25
    return True


def take_ikov_lever(log):
    _w26 = yield from temple_walk(IKOV_TILE.IKOV_LEVER_SPAWN, 1, log)
    if not (_w26):
        return False
    lever = ground_items.query().where(lambda g: g.id == IKOV_OBJ.LEVER).within(8).nearest()
    if not lever:
        log(f'ikov: no Lever at ({IKOV_TILE.IKOV_LEVER_SPAWN.x},{IKOV_TILE.IKOV_LEVER_SPAWN.z})')
        return False
    if not (lever.interact('Take')):
        return False
    _result27 = yield from execution.delay_until(lambda: held_id(IKOV_OBJ.LEVER) > 0, 8000)
    return _result27


def fetch_ikov_lever(log):
    """Cross the lava, take the Lever, cross back."""
    if held_id(IKOV_OBJ.LEVER) > 0:
        held = game.tile()
        if held is None or not west_of_bridge(held):
            return True
        _result_back = yield from cross_bridge(False, log)
        return _result_back
    here = game.tile()
    if not here:
        return False
    if not west_of_bridge(here):
        _w28 = yield from escape_pocket(log)
        if not (_w28):
            return False
        _w29 = yield from wear_fear_pendant(log)
        if not (_w29):
            return False
        _w30 = yield from cross_bridge(True, log)
        if not (_w30):
            return False
    _w31 = yield from take_ikov_lever(log)
    if not (_w31):
        return False
    _result32 = yield from cross_bridge(False, log)
    return _result32


def mend_and_pull_lever(log):
    """Fit the Lever into its bracket and pull it; the south gate opens off the bit it sets."""
    _w33 = yield from escape_pocket(log)
    if not (_w33):
        return False
    _w34 = yield from temple_walk(IKOV_TILE.LEVER_BRACKET, 1, log)
    if not (_w34):
        return False
    yield from settle_scene()
    if held_id(IKOV_OBJ.LEVER) > 0:
        bracket = loc_by_id(IKOV_LOC.LEVER_BRACKET, 6)
        lever = ([i for i in inventory.items() if i.id == IKOV_OBJ.LEVER] or [None])[0]
        if not bracket or not lever:
            log('ikov: no lever bracket in reach')
            return False
        log('ikov: fitting the lever into the bracket')
        if not (lever.use_on(bracket)):
            return False
        # Why: the fit runs `~mesbox` before its `inv_del`, so the lever is still in the pack until the box is answered.
        _w35 = yield from drive_until(lambda: held_id(IKOV_OBJ.LEVER) == 0, [], log, 15000)
        if not (_w35):
            log('ikov: the bracket never took the lever')
            return False
        yield from settle_scene()
    mended = loc_by_id(IKOV_LOC.MENDED_LEVER, 6)
    if not mended:
        log('ikov: the bracket carries no lever to pull')
        return False
    log('ikov: pulling the mended lever')
    if not (mended.interact('Pull')):
        return False
    yield from execution.delay_ticks(6)
    yield from clear_box()
    return True


def search_chest(chest, log):
    _w36 = yield from temple_walk(chest.stand, 0, log)
    if not (_w36):
        return False
    yield from settle_scene()

    def open_loc():
        return locs.query().where(lambda l: l.id == IKOV_LOC.CHEST_OPEN).within(4).nearest()

    shut = locs.query().where(lambda l: l.id == IKOV_LOC.CHEST_SHUT).within(4).nearest()
    if shut:
        if not (shut.interact('Open')):
            return False
        # Why: a loc that transforms keeps its old id for a tick, so poll for the open chest.
        yield from execution.delay_until(lambda: open_loc() is not None, 5000)
    open = open_loc()
    if not open:
        log(f'ikov: the chest at ({chest.loc.x},{chest.loc.z}) never opened')
        return False
    before = inventory.count(IKOV_NAME.ICE_ARROWS)
    mark = game_messages.mark()
    if not (open.interact('Search')):
        return False
    # Why: a find raises an `~objbox` that must be answered; 5 of the 6 chests answer with one `mes` line and no modal, so without that as an oracle every circuit pays the full timeout 5 times.
    yield from drive_until(lambda: inventory.count(IKOV_NAME.ICE_ARROWS) > before or game_messages.saw_since(mark, CHEST_EMPTY), [], log, 6000)
    found = inventory.count(IKOV_NAME.ICE_ARROWS) > before
    yield from clear_box()
    if found:
        log(f'ikov: {inventory.count(IKOV_NAME.ICE_ARROWS)} ice arrows')
    return found


# Why: the arrow chest is re-rolled after every find, so the search is a circuit and returning on the first find would restart it from the west.
# Why: `~randomize_ice_arrow_chest` is a bare `random(6)`, so the re-roll can land on the chest underfoot, and re-opening it costs a click where the next costs the same odds plus 10 tiles.
def search_ice_chests(log):
    before = inventory.count(IKOV_NAME.ICE_ARROWS)

    def enough():
        return inventory.count(IKOV_NAME.ICE_ARROWS) >= ARROWS_WANTED

    for round in range(CHEST_ROUNDS):
        for chest in ICE_CHESTS:
            yield from sustain.run()
            if enough():
                return True
            while True:
                _w37 = yield from search_chest(chest, log)
                if not ((_w37) and not enough()):
                    break
                yield from sustain.run()
    return inventory.count(IKOV_NAME.ICE_ARROWS) > before


# Why: `%ikov_dungeon` is untransmitted, so whether the south gate opens is the only client-visible answer to "has the lever been pulled".
def enter_ice_cavern(log):
    here = game.tile()
    if here and past_south_gate(here):
        return gate_is_open()
    _w38 = yield from temple_walk(IKOV_TILE.SOUTH_GATE_NORTH, 0, log)
    if not (_w38):
        return False
    yield from direct_navigator.walk_to(IKOV_TILE.SOUTH_GATE_SOUTH, 0, 8000)
    if crossed_into_cavern():
        yield from settle_scene()
        return gate_is_open()
    _v39 = loc_by_id(IKOV_LOC.SOUTH_GATE_LEFT, 4)
    gate = (_v39 if _v39 is not None else loc_by_id(IKOV_LOC.SOUTH_GATE_RIGHT, 4))
    if gate and (gate.interact('Open')):
        yield from execution.delay_ticks(2)
        # Why: the refusal is a `~mesbox`, and a box left up swallows every op the next leg sends.
        yield from clear_box()
        yield from direct_navigator.walk_to(IKOV_TILE.SOUTH_GATE_SOUTH, 0, 8000)
    if not crossed_into_cavern():
        yield from clear_box()
        return False
    yield from settle_scene()
    return gate_is_open()


def gate_is_open():
    global south_gate_seen_open
    south_gate_seen_open = True
    return True


def crossed_into_cavern():
    t = game.tile()
    return t is not None and past_south_gate(t)


# Why: a stack of 2 to 5 arrows carries its own object id and all 5 share one display name, so arrows are counted by name.
def arrows_secured(snap):
    key = IKOV_NAME.ICE_ARROWS.lower()
    if (key in snap.worn):
        return True
    _v40 = snap.inv.get(key)
    _v41 = (snap.bank.get(key) if snap.bank is not None else None)
    return ((_v40 if _v40 is not None else 0)) + ((_v41 if _v41 is not None else 0)) >= ARROWS_WANTED


# Why: reading a banked pair as done left them in the booth and sent the gate check down the dark stairs for a second pair, see docs/decisions/quest-pitfalls-25.md.
def boots_step(snap):
    """The boots errand on its own; it takes a leg of the descent per call and holds nothing until the last."""
    # A pair in the pack is one `unlockSouthGate` puts on itself.
    if wearing_boots() or (snap.inv_ids is not None and snap.inv_ids.get(IKOV_OBJ.BOOTS, 0) > 0):
        return None
    _v42 = (snap.bank_ids.get(IKOV_OBJ.BOOTS) if snap.bank_ids is not None else None)
    if ((_v42 if _v42 is not None else 0)) > 0:
        return Record({'kind': 'withdraw', 'items': [{'name': IKOV_NAME.BOOTS, 'id': IKOV_OBJ.BOOTS, 'qty': 1}]})
    return Record({'kind': 'custom', 'name': 'fetch the boots of lightness', 'run': fetch_boots})


def unlock_south_gate(log):
    """Cross the lava for the Lever and pull it, which is what the south gate reads."""
    _w43 = yield from escape_pocket(log)
    if not (_w43):
        return False
    # Why: the boots are the crossing's weight budget, and their own leg runs to completion before this one starts.
    if not wearing_boots():
        yield from fetch_boots(log)
    # Why: `fetchBoots` answers true per leg of progress, and one leg ends in the dark room, which the ice-cavern half-plane covers, so a gate check from there reads unlocked without a walk.
    if not wearing_boots():
        log('ikov: the boots are not on yet — the gate check waits for them')
        return False
    _w44 = yield from enter_ice_cavern(log)
    if _w44:
        return True
    log('ikov: the south gate is still locked — fetching the lever across the lava')
    # Why: armour put on for a gate that turned out shut is too heavy for the bridge, and the trim only sees the pack, so it comes off for the next pass to bank.
    if game.weight() >= 0:
        worn = [item.name for item in equipment.items() if (item.name or '').lower() in RANGED_ARMOUR_NAMES]
        if len(worn) > 0:
            log(f"ikov: taking off {', '.join(worn)} for the bridge")
            for name in worn:
                yield from equipment.unequip(name)
            return False
    _w45 = yield from fetch_ikov_lever(log)
    if not (_w45):
        return False
    _w46 = yield from mend_and_pull_lever(log)
    if not (_w46):
        return False
    _w47 = yield from enter_ice_cavern(log)
    if _w47:
        return True
    log('ikov: the south gate refused even after the lever was pulled')
    return False


# Why: the lava is behind the bot by now, so this is the first leg that can carry weight, and the armour is for the ice spiders on the circuit.
def stock_ice_arrows(log):
    """The chest circuit, which crosses nothing and so runs in whatever armour the bank dressed."""
    global south_gate_seen_open
    _w48 = yield from escape_pocket(log)
    if not (_w48):
        return False
    _w49 = yield from enter_ice_cavern(log)
    if not (_w49):
        log('ikov: the south gate is shut again — the lever has to be pulled before the chests')
        south_gate_seen_open = False
        return False
    _result50 = yield from search_ice_chests(log)
    return _result50
