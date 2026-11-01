"""Ported from rs2b0t's src/bot/api/ai/quests/defs/regicide/bomb.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.dialogue import modals
from rs2004.entities import ground_items, locs, npcs
from rs2004.game import game, reader
from rs2004.items import inventory
from rs2004.messages import game_messages
from rs2004.quests.defs.regicide.areas import RG_ITEM, RG_LOC, RG_NPC, RG_SULPHUR_LOCS, RG_TILE
from rs2004.quests.defs.regicide.isafdar import walk_to
from rs2004.quests.defs.regicide.journal import RG_STAGE
from rs2004.quests.exec.prompts import drive_until, held_id, settle_scene
from rs2004.traversal import traversal

__all__ = ['take_barrel', 'take_pot', 'weave_cloth', 'fill_tar', 'take_sulphur', 'grind_sulphur', 'grind_quicklime', 'heat_quicklime', 'catch_rabbit', 'cook_rabbit', 'still_button', 'distil_naphtha', 'mix_bomb', 'fuse_bomb']

GRIND_MS = 12000


# Why: `reachRectangle` requires a cardinal side; nearest otherwise ties the usable seep with an unreachable diagonal one.
# @see docs/decisions/quest-pitfalls-30.md
def reachable_loc(loc_ids):
    here = game.tile()
    found = locs.query().where(lambda loc: (loc.id in loc_ids)).within(10).results()
    if here is None:
        return found[0] if len(found) > 0 else None

    def manhattan(loc):
        return abs(loc.tile().x - here.x) + abs(loc.tile().z - here.z)

    _v1 = (sorted(found[:], key=lambda a: manhattan(a)) or [None])[0]
    return (_v1 if _v1 is not None else None)


def use_held_on_loc(item_id, loc_ids, expect, log):
    yield from settle_scene()
    target = reachable_loc(loc_ids)
    item = ([entry for entry in inventory.items() if entry.id == item_id] or [None])[0]
    if not target or not item:
        log(f'nothing to use {item_id} on within reach')
        return False
    mark = game_messages.mark()
    if not (item.use_on(target)):
        return False
    _w2 = yield from drive_until(expect, [], log, GRIND_MS)
    if _w2:
        return True
    # Why: "I can't reach that!" is the server saying the pair is wrong, so swallowing it makes a reach failure read as a recipe that did nothing.
    said = ' / '.join([m.text for m in game_messages.since(mark)][-2:])
    at = target.tile()
    me = game.tile()
    log(f"using {item_id} on {target.id}@({at.x},{at.z}) from ({(me.x if me is not None else None)},{(me.z if me is not None else None)}) changed nothing{(f' — it said: {said}' if said else '')}")
    return False


def take_barrel(log):
    """An empty barrel off the floor of the elf camp."""
    _w3 = yield from walk_to(RG_TILE.BARREL_SPAWN, 6, RG_STAGE.SPOKEN_IORWERTH2, log)
    if not (_w3):
        return False
    yield from settle_scene()
    before = held_id(RG_ITEM.BARREL.id)
    barrel = ground_items.query().where(lambda item: item.id == RG_ITEM.BARREL.id).within(14).nearest()
    if not barrel:
        log('no barrel on the floor of the elf camp')
        return False
    if not (barrel.interact('Take')):
        return False
    _result4 = yield from execution.delay_until(lambda: held_id(RG_ITEM.BARREL.id) > before, 10000)
    return _result4


def take_pot(log):
    """A pot off the floor of the elf camp; the quicklime dust needs somewhere to go."""
    _w5 = yield from walk_to(RG_TILE.POT_SPAWN, 4, RG_STAGE.SPOKEN_IORWERTH2, log)
    if not (_w5):
        return False
    yield from settle_scene()
    before = held_id(RG_ITEM.POT.id)
    pot = ground_items.query().where(lambda item: item.id == RG_ITEM.POT.id).within(12).nearest()
    if not pot or not (pot.interact('Take')):
        log('no pot on the floor of the elf camp')
        return False
    _result6 = yield from execution.delay_until(lambda: held_id(RG_ITEM.POT.id) > before, 10000)
    return _result6


# Why: `[oplocu,regicide_loom]` consumes four wool at once and rejects smaller amounts.
def weave_cloth(log):
    """4 balls of wool woven into the strip of cloth that becomes the fuse."""
    _w7 = yield from walk_to(RG_TILE.LOOM, 2, RG_STAGE.SPOKEN_IORWERTH2, log)
    if not (_w7):
        return False
    _result8 = yield from use_held_on_loc(RG_ITEM.BALL_OF_WOOL.id, [RG_LOC.LOOM], lambda: held_id(RG_ITEM.CLOTH.id) > 0, log)
    return _result8


def fill_tar(log):
    """The barrel filled from the coal-tar seep in the southern swamp."""
    _w9 = yield from walk_to(RG_TILE.TAR, 3, RG_STAGE.SPOKEN_IORWERTH2, log)
    if not (_w9):
        return False
    before = held_id(RG_ITEM.BARREL_TAR.id)
    _result10 = yield from use_held_on_loc(RG_ITEM.BARREL.id, [RG_LOC.TAR], lambda: held_id(RG_ITEM.BARREL_TAR.id) > before, log)
    return _result10


def take_sulphur(log):
    """A lump broken off one of the sulphur formations beside the swamp."""
    _w11 = yield from walk_to(RG_TILE.SULPHUR, 4, RG_STAGE.SPOKEN_IORWERTH2, log)
    if not (_w11):
        return False
    yield from settle_scene()
    before = held_id(RG_ITEM.SULPHUR.id)
    rock = locs.query().where(lambda loc: (loc.id in RG_SULPHUR_LOCS)).action('Take').within(12).nearest()
    if not rock or not (rock.interact('Take')):
        log('no sulphur formation within reach of the swamp')
        return False
    _result12 = yield from execution.delay_until(lambda: held_id(RG_ITEM.SULPHUR.id) > before, 10000)
    return _result12


# Why: `[opheldu,regicide_sulphar]` and `[opheldu,regicide_quicklime]` are declared on the lump, so the pestle is the item used and the lump the target. The client can't tell which way round a pair was declared, so a refusal sends the other direction.
def grind(from_id, to_id, log):
    pestle = ([item for item in inventory.items() if item.id == RG_ITEM.PESTLE.id] or [None])[0]
    lump = ([item for item in inventory.items() if item.id == from_id] or [None])[0]
    if not pestle or not lump:
        log(f"missing {('the lump' if pestle else 'the pestle and mortar')} to grind {from_id}")
        return False
    before = held_id(to_id)
    for used, target in [[pestle, lump], [lump, pestle]]:
        if not (used.use_on(target)):
            continue
        _w13 = yield from drive_until(lambda: held_id(to_id) > before, [], log, GRIND_MS)
        if _w13:
            return True
    return False


def grind_sulphur(log):
    return grind(RG_ITEM.SULPHUR.id, RG_ITEM.SULPHUR_DUST.id, log)


def grind_quicklime(log):
    return grind(RG_ITEM.QUICKLIME.id, RG_ITEM.QUICKLIME_DUST.id, log)


# Why: `regicide_heat_quicklime` goes through the generic `use_furnace` switch, so any furnace does. The camp's is 6 crossings deeper into the forest and 6 back, and East Ardougne's is 60 tiles from the bank the run passes anyway.
# Why: it costs 8 damage without gloves (`inv_totalcat(worn, armour_hands)`), which the food float covers.
def heat_quicklime(log):
    """Limestone burned to quicklime at the East Ardougne furnace."""
    _w14 = yield from traversal.walk_resilient(RG_TILE.ARDOUGNE_FURNACE, radius=2, attempts=3, timeout_ms=300000, log=log)
    if not (_w14):
        return False
    before = held_id(RG_ITEM.QUICKLIME.id)
    _result15 = yield from use_held_on_loc(RG_ITEM.LIMESTONE.id, [RG_LOC.FURNACE, RG_LOC.FURNACE_MAIN, RG_LOC.FURNACE_SIDE], lambda: held_id(RG_ITEM.QUICKLIME.id) > before, log)
    return _result15


def rabbit_near():
    return npcs.query().where(lambda npc: npc.id == RG_NPC.RABBIT or npc.id == 1193 or npc.id == 1194).action('Attack').within(14).nearest()


RABBIT_MS = 45000
RABBIT_RENEW_MS = 4000


def rabbit_meat():
    return ground_items.query().where(lambda item: item.id == RG_ITEM.RAW_RABBIT.id).within(12).nearest()


# Why: the meat never enters the pack. `[ai_queue3,_rabbit]` is `obj_add(npc_coord, raw_rabbit, 1, ...)`, which drops it on the floor under the rabbit, gated on `npc_findhero`, so waiting on the pack waits for something that can't happen.
# Why: one `Attack` click isn't enough either: the rabbit has `wanderrange=5` and 5 hitpoints, so it walks out of the interaction as often as it dies in it, and the attack is renewed until the meat is on the ground.
def catch_rabbit(log):
    """A rabbit out of the forest, for the guard who cannot catch one himself."""
    if held_id(RG_ITEM.RAW_RABBIT.id) > 0:
        return True
    if rabbit_meat() is not None:
        _result16 = yield from take_rabbit_corpse(log)
        return _result16
    _c17 = not rabbit_near()
    if _c17:
        _w18 = yield from walk_to(RG_TILE.RABBITS, 5, RG_STAGE.SPOKEN_IORWERTH2, log)
        _c17 = not (_w18)
    if _c17:
        return False
    yield from settle_scene()
    deadline = _core.step_time() + RABBIT_MS
    renew_at = 0
    sent = 0
    while _core.step_time() < deadline:
        if rabbit_meat() is not None:
            _result19 = yield from take_rabbit_corpse(log)
            return _result19
        rabbit = rabbit_near()
        if not rabbit:
            log(f'no rabbit within 14 of ({(game.tile().x if game.tile() is not None else None)},{(game.tile().z if game.tile() is not None else None)}) after {sent} attack(s) — they wander five tiles and respawn on a fifty-tick timer')
            return False
        if _core.step_time() >= renew_at:
            if not (rabbit.interact('Attack')):
                return False
            sent += 1
            renew_at = _core.step_time() + RABBIT_RENEW_MS
        yield from execution.delay_ticks(1)
    log(f'the rabbit outlasted {round(RABBIT_MS / 1000)}s and {sent} attack(s) with no meat on the ground')
    return False


def take_rabbit_corpse(log):
    meat = rabbit_meat()
    if not meat:
        log('no raw rabbit on the forest floor to pick up')
        return False
    if not (meat.interact('Take')):
        return False
    log('picked the rabbit up off the forest floor')
    _result20 = yield from execution.delay_until(lambda: held_id(RG_ITEM.RAW_RABBIT.id) > 0, 8000)
    return _result20


def cook_rabbit(log):
    """Cooked on the range beside the Ardougne bank, on the way through to the still."""
    _w21 = yield from traversal.walk_resilient(RG_TILE.ARDOUGNE_BANK, radius=12, attempts=3, timeout_ms=300000, log=log)
    if not (_w21):
        return False
    _w22 = yield from traversal.walk_resilient(RG_TILE.ARDOUGNE_RANGE, radius=1, attempts=3, timeout_ms=60000, log=log)
    if not (_w22):
        return False
    before = held_id(RG_ITEM.COOKED_RABBIT.id)
    _result23 = yield from use_held_on_loc(RG_ITEM.RAW_RABBIT.id, [RANGE_LOC], lambda: held_id(RG_ITEM.COOKED_RABBIT.id) > before, log)
    return _result23


RANGE_LOC = 2728
# The fractionalising still
# Why: `%regicide_still_total` and `%regicide_still_settings` are the 2 varps in this quest with `transmit=yes`, so the still is the one part the bot reads directly. `%temp` isn't among them, so the control law reads the heat needle.
# Why: resolved by the label the client puts in its own menu. The packed ids in `interface.pack` are the server's, and pressing one the client disagrees with is silent: `com_130` sent 600 times and the pressure valve never moved off bit 26.
STILL_LABELS = {
    'valve_shut': 'Turn pressure valve down',
    'valve_open': 'Turn pressure valve up',
    'regulator_down': 'Turn tar flow valve down',
    'regulator_up': 'Turn tar valve up',
    'coal': 'Click this to add coal.',
    'close': 'Close',
}
STILL_ROOT = 4919


def still_button_id(which):
    return reader.button_by_text(STILL_ROOT, STILL_LABELS[which])


VARP_STILL_TOTAL = 330
VARP_STILL_SETTINGS = 331
STILL_TARGET = 26
# Why: the tar regulator at full flow is +2 pressure a tick and the valve one step open is -2, the only pairing that holds the gauge still: shut is +2 a tick and blows in 6, wide open falls to 0 and the regulator has to come back down.
VALVE_HOLD = 1
REGULATOR_FULL = 2
# Why: the needle climbs 1 step a tick while `%temp` is 51-79 and 3 while it's over 80, and passing bit 25 resets the tally to 0. Coal at 6 or below peaks at 9, 2 clear of the ceiling, and the 4-tick gap stops 2 lumps landing inside one softtimer period.
COAL_BELOW = 6
COAL_GAP_TICKS = 4
HEAT_MIN = 6
HEAT_MAX = 11


def needle(settings, base, max_):
    for bit in range(base, max_ + 1):
        if ((settings >> bit) & 1) == 1:
            return bit - base
    return -1


def read_still():
    settings = reader.varp(VARP_STILL_SETTINGS)
    return Record({
        'total': reader.varp(VARP_STILL_TOTAL),
        'heat': needle(settings, 13, 25),
        'valve': needle(settings, 26, 28),
        'regulator': needle(settings, 29, 31),
    })


def still_button(view, since_coal, coal):
    """The next button the control law wants, or null when this tick is a wait."""
    if view.valve < VALVE_HOLD:
        return 'valve_open'
    if view.valve > VALVE_HOLD:
        return 'valve_shut'
    if view.regulator < REGULATOR_FULL:
        return 'regulator_up'
    if coal > 0 and view.heat <= COAL_BELOW and since_coal >= COAL_GAP_TICKS:
        return 'coal'
    return None


STILL_TIMEOUT_TICKS = 600
STILL_TRACE_TICKS = 20


def distil_naphtha(log):
    """Pour a barrel of tar into the still and work the valves until it yields naphtha."""
    if held_id(RG_ITEM.BARREL_NAPHTHA.id) > 0:
        return True
    if reader.modals().main != STILL_ROOT:
        _w24 = yield from traversal.walk_resilient(RG_TILE.STILL, radius=2, attempts=3, timeout_ms=300000, log=log)
        if not (_w24):
            return False
        _w25 = yield from use_held_on_loc(RG_ITEM.BARREL_TAR.id, [RG_LOC.STILL], lambda: reader.modals().main == STILL_ROOT, log)
        if not (_w25):
            log('the still would not take the barrel of coal tar')
            return False
    since_coal = COAL_GAP_TICKS
    best = 0
    for tick in range(STILL_TIMEOUT_TICKS):
        if reader.modals().main != STILL_ROOT:
            log('the still interface closed early')
            break
        view = read_still()
        if view.total >= STILL_TARGET:
            break
        if view.total > best:
            best = view.total
        elif view.total == 0 and best > 0:
            log(f'the still blew its gauge at {best}/{STILL_TARGET} and reset — starting the run again')
            best = 0
        button = still_button(view, since_coal, inventory.count(RG_ITEM.COAL.name))
        if button == 'coal':
            since_coal = 0
        else:
            since_coal += 1
        if button is not None:
            com_id = still_button_id(button)
            if com_id == -1:
                log(f"the still has no '{STILL_LABELS[button]}' button — the interface is not the one this expects")
                break
            _core.click_component(com_id)
        # Why: the gauges are the only feedback here, and without them a run that makes no progress looks like one that never opened.
        if tick % STILL_TRACE_TICKS == 0:
            log(f'still: total {view.total}/{STILL_TARGET} heat {view.heat} valve {view.valve} reg {view.regulator} → button {button}')
        yield from execution.delay_ticks(1)
    finished = read_still().total >= STILL_TARGET
    # Why: `[if_close,regicide_still]` swaps the empty barrel for the naphtha and the tally alone hands over nothing, so the run finishes once the interface is shut.
    _w26 = yield from close_still()
    if not (_w26):
        log('the still interface would not close')
        return False
    if not finished:
        log(f'the still stopped at {read_still().total}/{STILL_TARGET}')
        return False
    _result27 = yield from execution.delay_until(lambda: held_id(RG_ITEM.BARREL_NAPHTHA.id) > 0, 10000)
    return _result27


def close_still():
    _w28 = yield from modals.close()
    if _w28:
        return True
    # Why: the generic close is a CLOSE_BUTTON menu action and this root's own shut is `com_89`, `[if_button,regicide_still:com_89] if_close`.
    close = still_button_id('close')
    if close != -1:
        _core.click_component(close)
    _result29 = yield from execution.delay_until(lambda: reader.modals().main != STILL_ROOT, 5000)
    return _result29


# Why: the 2 powders go into the naphtha in either order and the barrel seals itself on the second, so one step pours whatever it still has and nothing needs sequencing.
def mix_bomb(log):
    """Both powders into the naphtha, which seals the barrel into a bomb."""
    for dust in [RG_ITEM.QUICKLIME_DUST, RG_ITEM.SULPHUR_DUST]:
        if held_id(RG_ITEM.BARREL_LID.id) > 0:
            return True
        powder = ([item for item in inventory.items() if item.id == dust.id] or [None])[0]
        barrel = ([item for item in inventory.items() if item.id == RG_ITEM.BARREL_NAPHTHA.id or item.id == RG_ITEM.MIX_QUICKLIME.id or item.id == RG_ITEM.MIX_SULPHUR.id] or [None])[0]
        if not barrel:
            log('nothing left to mix the powders into')
            return False
        if not powder:
            # Why: the barrel seals on the second powder, so a pack with one of them retries this step forever without saying which one the forest still owes.
            log(f'no {dust.name} to mix in — the bomb needs both powders')
            return False
        before = held_id(dust.id)
        if not (powder.use_on(barrel)):
            return False
        _w30 = yield from drive_until(lambda: held_id(dust.id) < before, [], log, GRIND_MS)
        if not (_w30):
            log(f'the naphtha would not take the {dust.name}')
            return False
    return held_id(RG_ITEM.BARREL_LID.id) > 0


def fuse_bomb(log):
    """The woven cloth stuffed through the barrel's hole as a fuse."""
    cloth = ([item for item in inventory.items() if item.id == RG_ITEM.CLOTH.id] or [None])[0]
    barrel = ([item for item in inventory.items() if item.id == RG_ITEM.BARREL_LID.id] or [None])[0]
    if not cloth or not barrel:
        log(f"missing {('the sealed barrel' if cloth else 'the cloth')} for the fuse")
        return False
    if not (cloth.use_on(barrel)):
        return False
    _result31 = yield from drive_until(lambda: held_id(RG_ITEM.BARREL_FUSED.id) > 0, [], log, GRIND_MS)
    return _result31

