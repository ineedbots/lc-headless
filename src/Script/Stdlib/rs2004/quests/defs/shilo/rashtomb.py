"""Ported from rs2b0t's src/bot/api/ai/quests/defs/shilo/rashtomb.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import chat_dialog
from rs2004.entities import npcs
from rs2004.game import game
from rs2004.items import equipment
from rs2004.quests.defs.shilo.areas import SV_ITEM, SV_LOC, SV_NPC, SV_TILE, in_dolmen_room
from rs2004.quests.defs.shilo.scene import drive_choice, held_id, here, loc_near, prompt_loc, settle_scene, use_on_loc
from rs2004.traversal import traversal

__all__ = ['search_carved_doors', 'unlock_carved_doors', 'enter_rash_tomb', 'leave_rash_tomb', 'pass_gate', 'climb_rash_rocks', 'place_bone', 'leave_tomb_chamber', 'work_the_dolmen']


def carved_doors():
    """The doors hide themselves again about 50 ticks after the trees are searched."""
    _v1 = loc_near(SV_LOC.CARVED_DOORS, 'Search', 10)
    return (_v1 if _v1 is not None else loc_near(SV_LOC.CARVED_DOORS, 'Open', 10))


def hillside_entrance():
    return loc_near(SV_LOC.HILLSIDE_ENTRANCE, 'Enter', 10)


def reveal_doors(log):
    if carved_doors() or hillside_entrance():
        return True
    _result2 = yield from prompt_loc(Record({
        'name': SV_LOC.PALM_TREE,
        'op': 'Search',
        'near': SV_TILE.PALM_TREES,
        'expect': lambda: carved_doors() is not None or hillside_entrance() is not None,
        'expect_ms': 10000,
    }), log)
    return _result2


# Why: searching the doors teaches the bone lock, and the engine only records it at stage `entered_tomb_bervirius`, so this runs after the Bervirius dolmen and before the key is cut.
def search_carved_doors(log):
    """Search the carved doors to learn the bone lock."""
    _w3 = yield from reveal_doors(log)
    if not (_w3):
        return False
    _w4 = yield from traversal.walk_resilient(SV_TILE.CARVED_DOORS, radius=2, attempts=3, timeout_ms=180000, log=log)
    if not (_w4):
        return False
    yield from settle_scene()
    doors = loc_near(SV_LOC.CARVED_DOORS, 'Search', 10)
    if not doors:
        log('the carved doors closed again before they could be searched')
        return False
    if not (doors.interact('Search')):
        return False
    # The bit lands with the message box and nothing else changes, so the next journal read confirms it.
    _w5 = yield from execution.delay_until(lambda: chat_dialog.is_open() or chat_dialog.can_continue(), 8000)
    if not (_w5):
        return False
    _result6 = yield from drive_choice([], log)
    return _result6


def unlock_carved_doors(log):
    if hillside_entrance():
        return True
    _w7 = yield from reveal_doors(log)
    if not (_w7):
        return False
    _result8 = yield from use_on_loc(SV_ITEM.BONE_KEY.id, Record({'name': SV_LOC.CARVED_DOORS, 'near': SV_TILE.CARVED_DOORS}), [], lambda: hillside_entrance() is not None, log)
    return _result8


def enter_rash_tomb(log):
    if here() != 'karamja':
        return True
    _w9 = yield from reveal_doors(log)
    if not (_w9):
        return False
    # Why: After using the bone key, the doors switch to plain Open but may be shut again after restart.
    if not hillside_entrance():
        shut = loc_near(SV_LOC.CARVED_DOORS, 'Open', 10)
        if shut and (shut.interact('Open')):
            yield from execution.delay_until(lambda: hillside_entrance() is not None, 10000)
    ok = yield from prompt_loc(Record({
        'name': SV_LOC.HILLSIDE_ENTRANCE,
        'op': 'Enter',
        'near': SV_TILE.CARVED_DOORS,
        'expect': lambda: here() == 'rashEntry',
    }), log)
    if ok:
        yield from settle_scene()
    return ok


def leave_rash_tomb(log):
    """`zq_open_tombexit` refuses anyone carrying the bone key; the key has to be used on the door instead."""
    if here() != 'rashEntry':
        return True
    if held_id(SV_ITEM.BONE_KEY.id) == 0:
        ok = yield from prompt_loc(Record({
            'name': SV_LOC.TOMB_EXIT,
            'op': 'Open',
            'near': SV_TILE.TOMB_EXIT,
            'expect': lambda: here() != 'rashEntry',
        }), log)
        if ok:
            yield from settle_scene()
        return ok
    ok = yield from use_on_loc(SV_ITEM.BONE_KEY.id, Record({'name': SV_LOC.TOMB_EXIT, 'near': SV_TILE.TOMB_EXIT}), [], lambda: here() != 'rashEntry', log)
    if ok:
        yield from settle_scene()
    return ok


# Why: the gate teleports across itself in either direction, so both crossings are the same click; southbound it summons Rashiliyia for anyone without the Beads of the Dead worn.
def pass_gate(dir, log):
    """Cross the tomb gate in the named direction."""
    want = ('rashLedge' if dir == 'in' else 'rashEntry')
    if here() == want:
        return True
    if dir == 'in' and not equipment.contains(SV_ITEM.DEAD_BEADS.name):
        log('the Beads of the Dead are not worn — the gate would summon Rashiliyia')
        return False
    gate = loc_near(SV_LOC.ANCIENT_GATE, 'Open', 12)
    if not gate:
        # Out of range: walk up to the gate and let the next pass click it.
        ok = yield from prompt_loc(Record({
            'name': SV_LOC.ANCIENT_GATE,
            'op': 'Open',
            'near': SV_TILE.ANCIENT_GATE,
            'expect': lambda: here() == want,
        }), log)
        if ok:
            yield from settle_scene()
        return ok
    if not (gate.interact('Open')):
        return False
    ok = yield from execution.delay_until(lambda: here() == want, 15000)
    if ok:
        yield from settle_scene()
    return ok


def climb_rash_rocks(dir, log):
    """The rocks are clicked from wherever the gate dropped us; the ledge is unwalkable in the baked pack."""
    want = ('rashInner' if dir == 'down' else 'rashLedge')
    if here() == want:
        return True
    rocks = loc_near(SV_LOC.RASH_ROCKS, 'Climb', 8)
    if not rocks:
        log(f'no climbable rocks in range going {dir}')
        return False
    if not (rocks.interact('Climb')):
        return False
    ok = yield from execution.delay_until(lambda: here() == want, 20000)
    if ok:
        yield from settle_scene()
    return ok


def place_bone(log):
    """3 plain bones, one recess at a time; the third opens the doors and pushes you through."""
    if held_id(SV_ITEM.BONES.id) == 0:
        log('no bones left for the door recesses')
        return False
    before = held_id(SV_ITEM.BONES.id)
    _result10 = yield from use_on_loc(SV_ITEM.BONES.id, Record({'name': SV_LOC.TOMB_DOORS, 'near': SV_TILE.TOMB_DOORS}), [], lambda: held_id(SV_ITEM.BONES.id) < before, log)
    return _result10


# Why: the skeletal doors revert to closed 3 ticks after a crossing and are excluded from the door bake, so every trip through is another `Open`, which teleports.
def cross_tomb_doors(dir, log):
    """Cross the skeletal doors in the named direction."""
    want = dir == 'north'

    def there():
        return in_dolmen_room(game.tile()) == want

    if there():
        return True
    stand = (SV_TILE.TOMB_DOORS if want else SV_TILE.TOMB_DOORS_INSIDE)
    _w11 = yield from traversal.walk_resilient(stand, radius=2, attempts=3, timeout_ms=120000, log=log)
    if not (_w11):
        return False
    yield from settle_scene()
    doors = loc_near(SV_LOC.TOMB_DOORS, 'Open', 8)
    if not doors:
        log(f'no skeletal doors in range to cross {dir}')
        return False
    if not (doors.interact('Open')):
        return False
    ok = yield from execution.delay_until(there, 15000)
    if ok:
        yield from settle_scene()
    return ok


# Why: nothing but the skeletal doors connects the dolmen room to the rest of the tomb, so leaving is doors, east to the climbing rocks, then up.
def leave_tomb_chamber(log):
    """Walk out of the dolmen chamber."""
    if here() != 'rashInner':
        return True
    _w12 = yield from cross_tomb_doors('south', log)
    if not (_w12):
        return False
    _w13 = yield from traversal.walk_resilient(SV_TILE.RASH_ROCKS_BOTTOM, radius=2, attempts=3, timeout_ms=120000, log=log)
    if not (_w13):
        return False
    _result14 = yield from climb_rash_rocks('up', log)
    return _result14


FIGHT_MS = 240000


# Why: searching the dolmen summons the next Nazastarool or, once all 3 are down, yields the remains; one step covers both since the journal can claim kills the engine has reset.
def work_the_dolmen(log):
    """Search the dolmen, fighting whatever it summons."""
    if held_id(SV_ITEM.RASH_CORPSE.id) > 0:
        return True

    def boss():
        return npcs.query().name(SV_NPC.NAZASTAROOL).action('Attack').within(14).nearest()

    if boss():
        _result15 = yield from fight_nazastarool(log)
        return _result15
    _w16 = yield from cross_tomb_doors('north', log)
    if not (_w16):
        return False
    searched = yield from prompt_loc(Record({
        'name': SV_LOC.RASH_DOLMEN,
        'op': 'Search',
        'near': SV_TILE.RASH_DOLMEN,
        'expect': lambda: held_id(SV_ITEM.RASH_CORPSE.id) > 0 or boss() is not None,
        'expect_ms': 20000,
    }), log)
    if not searched:
        return False
    if held_id(SV_ITEM.RASH_CORPSE.id) > 0:
        return True
    _result17 = yield from fight_nazastarool(log)
    return _result17


def fight_nazastarool(log):
    deadline = _core.step_time() + FIGHT_MS
    while _core.step_time() < deadline:
        target = npcs.query().name(SV_NPC.NAZASTAROOL).action('Attack').within(14).nearest()
        if not target:
            return True
        yield from sustain.run()
        if not game.in_combat():
            target.interact('Attack')
            yield from execution.delay_until(lambda: game.in_combat(), 5000)
        yield from execution.delay_ticks(2)
    log('Nazastarool outlasted the fight budget')
    return False
