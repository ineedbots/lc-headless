"""Ported from rs2b0t's src/bot/api/ai/quests/defs/digsite/caves.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.dialogue import chat_dialog, modals
from rs2004.entities import ground_items
from rs2004.game import game
from rs2004.items import inventory
from rs2004.messages import game_messages
from rs2004.quests.defs.digsite.areas import DIG_ID, DIG_LOC, DIG_NPC, DIG_TILE, in_altar_cave, in_shaft_east, in_shaft_west
from rs2004.quests.defs.digsite.common import climb_out_of_cave, drive_until_held, loc_by_id_action, loc_by_ids, talk_to_npc_id, use_on_loc_ids, walk_to
from rs2004.quests.exec.prompts import drive_choice, settle_scene

__all__ = ['descend_winch', 'west_shaft_leg', 'grab_arcenia', 'chest_leg', 'barrel_leg', 'mix_items', 'mix_step', 'blast_leg', 'tablet_leg', 'leave_cave_step']

DESCEND_MS = 15000
KEY_PREFER = [
    'I have been invited to research here.',
    'Do you know where to find a chest key?',
    "I don't suppose I could use it?",
    'Aww... go on.',
    'Pretty please with sugar on top!',
    'Pretty please!',
    'Please?',
]


# Why: Winch-rope state is not transmitted; Operate either descends or emits the unroped message.
def descend_winch(winch_loc_id, stand, arrived, log):
    """Operate a winch, adding a rope if the shaft reports that it is unroped."""
    if arrived():
        return True
    _w1 = yield from walk_to(stand, 1, log)
    if not (_w1):
        return False
    for attempt in range(3):
        if not (not arrived()):
            break
        yield from modals.close_if_open()
        yield from settle_scene()
        winch = loc_by_id_action([winch_loc_id], 'Operate', 8)
        if not winch:
            log(f'no winch {winch_loc_id} within eight tiles of ({stand.x},{stand.z})')
            return False
        if not (winch.interact('Operate')):
            yield from execution.delay_ticks(1)
            continue
        yield from execution.delay_until(lambda: arrived() or chat_dialog.is_open() or chat_dialog.can_continue(), DESCEND_MS)
        if arrived():
            yield from settle_scene()
            return True
        # The bucket stopped short: the shaft has no rope on it yet.
        yield from drive_choice([], log)
        yield from modals.close_if_open()
        rope = ([i for i in inventory.items() if i.id == DIG_ID.ROPE] or [None])[0]
        if not rope:
            log('the winch needs a rope tied to its bucket and the pack has none')
            return False
        ropes_before = inventory.count_by_id(DIG_ID.ROPE)
        mark = game_messages.mark()
        target = loc_by_ids([winch_loc_id], 8)
        if not target or not (rope.use_on(target)):
            yield from execution.delay_ticks(1)
            continue
        tied = yield from execution.delay_until(lambda: inventory.count_by_id(DIG_ID.ROPE) < ropes_before or game_messages.saw_since(mark, 'tie the rope to the bucket'), 10000)
        if not tied:
            log('the rope would not tie to the winch bucket')
        yield from execution.delay_ticks(2)
        yield from modals.close_if_open()
    if arrived():
        return True
    log(f'the winch at ({stand.x},{stand.z}) never dropped us down the shaft')
    return False


def west_shaft_leg(need_key, need_root):
    """The western shaft holds the cave workman with the chest key, and 2 arcenia roots."""

    def _fn2(log):
        if not in_shaft_west(game.tile()):
            _w3 = yield from descend_winch(DIG_LOC.WINCH_PRIVATE, DIG_TILE.WINCH_PRIVATE_STAND, lambda: in_shaft_west(game.tile()), log)
            if not (_w3):
                return False
        progressed = False
        if need_key and inventory.count_by_id(DIG_ID.CHEST_KEY) == 0:
            yield from talk_to_npc_id(DIG_NPC.CAVE_WORKMAN, DIG_TILE.CAVE_WORKMAN, KEY_PREFER, log)
            yield from drive_until_held(lambda: inventory.count_by_id(DIG_ID.CHEST_KEY) > 0, KEY_PREFER, log, 30000)
            progressed = inventory.count_by_id(DIG_ID.CHEST_KEY) > 0
            if not progressed:
                log('the cave workman kept his key this pass')
        if need_root and inventory.count_by_id(DIG_ID.ARCENIA_ROOT) == 0:
            _w4 = yield from grab_arcenia(log)
            progressed = (_w4) or progressed
        still_needs = (need_key and inventory.count_by_id(DIG_ID.CHEST_KEY) == 0) or (need_root and inventory.count_by_id(DIG_ID.ARCENIA_ROOT) == 0)
        _c5 = not still_needs
        if _c5:
            _w6 = yield from climb_out_of_cave(log)
            _c5 = not (_w6)
        if _c5:
            log('the shaft work is done but the climb out did not land — retrying next pass')
        return progressed
    return Record({
        'kind': 'custom',
        'name': ('beg the cave workman for the chest key' if need_key else 'pick an arcenia root in the dig shaft'),
        'run': _fn2,
    })


def grab_arcenia(log):
    """Arcenia root lies on the shaft floor in both halves of the cave."""
    if inventory.count_by_id(DIG_ID.ARCENIA_ROOT) > 0:
        return True
    for anchor in [DIG_TILE.ARCENIA_WEST, DIG_TILE.ARCENIA_WEST_ALT]:
        root = ground_items.query().where(lambda g: g.id == DIG_ID.ARCENIA_ROOT).within(24).nearest()
        if not root:
            _w7 = yield from walk_to(anchor, 1, log)
            if not (_w7):
                continue
            yield from settle_scene()
        found = ground_items.query().where(lambda g: g.id == DIG_ID.ARCENIA_ROOT).within(24).nearest()
        if not found:
            continue
        _c8 = found.distance() > 1
        if _c8:
            _w9 = yield from walk_to(found.tile(), 1, log)
            _c8 = not (_w9)
        if _c8:
            continue
        if not (found.interact('Take')):
            continue
        _w10 = yield from execution.delay_until(lambda: inventory.count_by_id(DIG_ID.ARCENIA_ROOT) > 0, 8000)
        if _w10:
            return True
    log('no arcenia root within reach in this shaft')
    return False


def chest_leg():
    """The chest on the river bank: unlocked with the workman's key, then searched for the powder."""

    def _fn11(log):
        if inventory.count_by_id(DIG_ID.POWDER) > 0:
            return True
        _w12 = yield from walk_to(DIG_TILE.CHEST_STAND, 0, log)
        if not (_w12):
            return False
        yield from settle_scene()
        if not loc_by_id_action([DIG_LOC.CHEST_OPEN], 'Search', 4):
            key = ([i for i in inventory.items() if i.id == DIG_ID.CHEST_KEY] or [None])[0]
            shut = loc_by_ids([DIG_LOC.CHEST_SHUT], 4)
            if not key or not shut:
                log('the chest is shut and the pack has no chest key')
                return False
            if not (key.use_on(shut)):
                return False
            yield from execution.delay_until(lambda: loc_by_id_action([DIG_LOC.CHEST_OPEN], 'Search', 4) is not None, 10000)
            yield from settle_scene()
        opened = loc_by_id_action([DIG_LOC.CHEST_OPEN], 'Search', 4)
        if not opened:
            log('the chest never opened')
            return False
        if not (opened.interact('Search')):
            return False
        _result13 = yield from drive_until_held(lambda: inventory.count_by_id(DIG_ID.POWDER) > 0, [], log, 15000)
        return _result13
    return Record({'kind': 'custom', 'name': 'unlock and search the digsite chest', 'run': _fn11})


def barrel_leg():
    """The sealed barrel: levered open with the trowel, then decanted into a vial."""

    def _fn14(log):
        if inventory.count_by_id(DIG_ID.LIQUID) > 0:
            return True
        if inventory.count_by_id(DIG_ID.VIAL) == 0:
            log('no empty vial in the pack to fill')
            return False
        _w15 = yield from walk_to(DIG_TILE.BARREL_STAND, 1, log)
        if not (_w15):
            return False
        yield from settle_scene()
        # Why: the lid flag is a `%itexam_bits` bit, so the trowel goes on first every pass; a second lever is a no-op and a missing one leaves "It's not open!".
        trowel = ([i for i in inventory.items() if i.id == DIG_ID.TROWEL] or [None])[0]
        barrel = loc_by_ids([DIG_LOC.BARREL], 6)
        if not trowel or not barrel:
            log('no trowel or no barrel at (3364,3377)')
            return False
        if trowel.use_on(barrel):
            yield from execution.delay_ticks(3)
            yield from drive_choice([], log)
        yield from modals.close_if_open()
        _result16 = yield from use_on_loc_ids(DIG_ID.VIAL, [DIG_LOC.BARREL], DIG_TILE.BARREL_STAND, lambda: inventory.count_by_id(DIG_ID.LIQUID) > 0, log)
        return _result16
    return Record({'kind': 'custom', 'name': 'lever the barrel open and fill a vial', 'run': _fn14})


def mix_items(a_id, b_id, product_id, log):
    """Try a use both ways round: `opheldu` is declared on one of the pair and the client cannot tell which."""
    if inventory.count_by_id(product_id) > 0:
        return True
    for from_id, to_id in [[a_id, b_id], [b_id, a_id]]:
        from_ = ([i for i in inventory.items() if i.id == from_id] or [None])[0]
        to = ([i for i in inventory.items() if i.id == to_id] or [None])[0]
        if not from_ or not to:
            log(f'mix: the pack is missing {from_id} or {to_id}')
            return False
        if not (from_.use_on(to)):
            continue
        # Why: the last mix ends in a `~chatplayer` line and only adds the compound after it, so a wait that doesn't drive the dialogue times out on a mix that worked.
        _w17 = yield from drive_until_held(lambda: inventory.count_by_id(product_id) > 0, [], log, 12000)
        if _w17:
            return True
    yield from modals.close_if_open()
    log(f'mixing {a_id} with {b_id} produced no {product_id}')
    return False


def mix_step(name, a_id, b_id, product_id):
    return Record({'kind': 'custom', 'name': name, 'run': lambda log: mix_items(a_id, b_id, product_id, log)})


def on_brick_stand():
    here = game.tile()
    return here is not None and here.level == 0 and here.x == DIG_TILE.BRICK_STAND.x and here.z == DIG_TILE.BRICK_STAND.z


def blast_leg(pour):
    """Pour the compound over the bricks and light it; the run-away sequence needs one specific tile."""

    def _fn18(log):
        if not in_shaft_east(game.tile()):
            if in_altar_cave(game.tile()):
                return True
            _w19 = yield from descend_winch(DIG_LOC.WINCH_MAIN, DIG_TILE.WINCH_MAIN_STAND, lambda: in_shaft_east(game.tile()), log)
            if not (_w19):
                return False
        # Why: `digsite_blockage_run_sequence` refuses any coord but (3379,9826) with "Eep! Eep! Unexpected player coord!", and a radius-0 walk reports the closest reachable tile as an arrival.
        for attempt in range(3):
            if not (not on_brick_stand()):
                break
            yield from walk_to(DIG_TILE.BRICK_STAND, 0, log)
        if not on_brick_stand():
            here = game.tile()
            log(f'the blast wants ({DIG_TILE.BRICK_STAND.x},{DIG_TILE.BRICK_STAND.z}) and we are at ({(here.x if here is not None else None)},{(here.z if here is not None else None)})')
            return False
        yield from settle_scene()
        brick = loc_by_ids([DIG_LOC.BRICK], 4)
        if not brick:
            log('no blocked brick within four tiles of (3379,9826)')
            return False
        if pour:
            compound = ([i for i in inventory.items() if i.id == DIG_ID.COMPOUND] or [None])[0]
            if not compound:
                log('no chemical compound in the pack to pour')
                return False
            if not (compound.use_on(brick)):
                return False
            poured = yield from drive_until_held(lambda: inventory.count_by_id(DIG_ID.COMPOUND) == 0, [], log, 15000)
            yield from modals.close_if_open()
            return poured
        tinderbox = ([i for i in inventory.items() if i.id == DIG_ID.TINDERBOX] or [None])[0]
        if not tinderbox:
            log('no tinderbox in the pack to strike')
            return False
        again = loc_by_ids([DIG_LOC.BRICK], 4)
        if not again or not (tinderbox.use_on(again)):
            return False
        # Why: the run-away sequence teleports across a mapsquare and ends in a `~chatplayer` line, and the client's own tile reads stale until that scene rebuild settles.
        yield from execution.delay_until(lambda: in_altar_cave(game.tile()) or chat_dialog.is_open() or chat_dialog.can_continue(), 30000)
        yield from drive_choice([], log)
        yield from modals.close_if_open()
        yield from settle_scene()
        if in_altar_cave(game.tile()):
            return True
        log('the tinderbox did not set the compound off')
        return False
    return Record({
        'kind': 'custom',
        'name': ('pour the compound over the blocked bricks' if pour else 'light the explosive compound'),
        'run': _fn18,
    })


def tablet_leg():
    """The Zarosian tablet lies on the altar floor once the blast has opened the way."""

    def _fn20(log):
        if inventory.count_by_id(DIG_ID.STONE_TABLET) > 0:
            return True
        if not in_altar_cave(game.tile()):
            _w21 = yield from descend_winch(DIG_LOC.WINCH_MAIN, DIG_TILE.WINCH_MAIN_STAND, lambda: in_altar_cave(game.tile()), log)
            if not (_w21):
                return False
        _w22 = yield from walk_to(DIG_TILE.TABLET, 1, log)
        if not (_w22):
            return False
        yield from settle_scene()
        tablet = ground_items.query().where(lambda g: g.id == DIG_ID.STONE_TABLET).within(8).nearest()
        if not tablet:
            log('no stone tablet within eight tiles of (3374,9747)')
            return False
        if not (tablet.interact('Take')):
            return False
        _result23 = yield from execution.delay_until(lambda: inventory.count_by_id(DIG_ID.STONE_TABLET) > 0, 8000)
        return _result23
    return Record({'kind': 'custom', 'name': 'take the Zarosian stone tablet', 'run': _fn20})


def leave_cave_step():
    return Record({'kind': 'custom', 'name': 'climb out of the dig shaft', 'run': climb_out_of_cave})
