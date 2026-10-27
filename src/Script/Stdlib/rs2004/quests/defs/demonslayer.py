"""Ported from rs2b0t's src/bot/api/ai/quests/defs/demonslayer.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.dialogue import chat_dialog
from rs2004.entities import ground_items, locs, npcs
from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.items import equipment, inventory
from rs2004.quests.data import QUESTS
from rs2004.quests.engine.provisioning import gp_short
from rs2004.quests.engine.types import QuestModule
from rs2004.quests.exec.primitives import goto_npc, is_underground, talk_through
from rs2004.quests.exec.steps import execute_step
from rs2004.quests.exec.prompts import drive_boxes, clear_boxes
from rs2004.reach import reach
from rs2004.tabs import quests
from rs2004.traversal import traversal


__all__ = ['decide', 'demonslayer']

TRAIBORN_KEY_ID = 2399
ROVIN_KEY_ID = 2400
DRAIN_KEY_ID = 2401
GYPSY = Record({
    'npc': 'Gypsy',
    'anchor': Tile(3203, 3424, 0),
    'leash': 6,
    'prefer': [
    'Ok, here you go.',
    'Very interesting. What does that Aaargh bit mean?',
    "Who's Delrith?",
    "Okay, where is he? I'll kill him for you!",
    'Where can I find Silverlight?',
    "Okay, thanks. I'll do my best to stop the demon.",
],
})
PRYSIN = Record({
    'npc': 'Sir Prysin',
    'anchor': Tile(3205, 3473, 0),
    'leash': 6,
    'prefer': [
    'Gypsy Aris said I should come and talk to you.',
    'I need to find Silverlight.',
    "He's back and unfortunately I've got to deal with him.",
    'So give me the keys!',
    'Where does the wizard live?',
    "Well I'd better go key hunting.",
    "I'm still looking.",
],
})
ROVIN = Record({
    'npc': 'Captain Rovin',
    'anchor': Tile(3204, 3496, 2),
    'leash': 6,
    'prefer': ['Yes I know, but this is important.', "There's a demon who wants to invade this city."],
})
TRAIBORN = Record({
    'npc': 'Traiborn',
    'anchor': Tile(3112, 3162, 1),
    'leash': 2,
    'prefer': [
    'I need to get a key given to you by Sir Prysin.',
    'have you got any keys knocking around',
    "I'll get the bones for you",
],
})
WIZ_INSIDE_STAND = Tile(3105, 3160, 0)
DRAIN_TILE = Tile(3225, 3495, 0)
SINK_TILE = Tile(3224, 3494, 0)
MANHOLE_TILE = Tile(3237, 3458, 0)
SEWER_LAND = Tile(3237, 9858, 0)
SEWER_KEY = Tile(3225, 9897, 0)
DELRITH_TILE = Tile(3229, 3369, 0)
GOBLIN_ANCHOR = Tile(3144, 3231, 0)
WIZ_L1_STAND = Tile(3105, 3160, 1)
VARROCK_GENERAL = Record({'npc': 'Shop keeper', 'anchor': Tile(3218, 3414, 0)})
INCANTATION = 'Aber Camerinthum Purchai Gabindo'
BONES_NEEDED = 25
BONES_ID = 526
GOBLIN_ID = 100
GOBLIN_RADIUS = 20


def has(snap, name):
    return ((snap.inv.get(name.lower()) if snap.inv.get(name.lower()) is not None else 0)) > 0


def worn(snap, name):
    return (name.lower() in snap.worn)


def held_id(id):
    return any([i.id == id for i in inventory.items()])


def buy_or_wait(snap, step):
    if gp_short(snap, step.est_gp) > 0:
        return Record({'kind': 'wait', 'reason': f'need ~{step.est_gp} gp for {step.item}'})
    return step


def fill_bucket(snap, need=1):
    if has(snap, 'bucket'):
        return Record({
            'kind': 'use_on',
            'item': 'Bucket',
            'target_kind': 'loc',
            'target': 'Sink',
            'anchor': SINK_TILE,
            'product': 'Bucket of water',
        })
    return buy_or_wait(snap, Record({'kind': 'buy', 'item': 'Bucket', 'qty': 1, 'shop': VARROCK_GENERAL, 'est_gp': 15}))


def grind_goblins(log):
    if inventory.count('Bones') >= BONES_NEEDED:
        return True
    if game.in_combat():
        yield from execution.delay_ticks(2)
        return False
    drop = ground_items.query().name('Bones').where(lambda item: item.id == BONES_ID).within(GOBLIN_RADIUS).nearest()
    if drop:
        before = inventory.count('Bones')
        if not (drop.interact('Take')):
            return False
        yield from execution.delay_until(lambda: inventory.count('Bones') > before, 6000)
        return False
    goblin = npcs.query().name('Goblin').action('Attack').where(lambda n: n.id == GOBLIN_ID and not n.in_combat and not n.targets_another_player()).within(GOBLIN_RADIUS).nearest()
    if not goblin:
        yield from traversal.walk_resilient(GOBLIN_ANCHOR, radius=3, attempts=3, timeout_ms=90000, log=log)
        return False
    if not (goblin.interact('Attack')):
        return False
    yield from execution.delay_until(lambda: game.in_combat() or not goblin.valid(), 5000)
    yield from execution.delay_until(lambda: not goblin.valid(), 30000)
    return False


def drain_leg(log):
    here = game.tile()
    if here is None:
        return False
    if is_underground(here):
        if not held_id(DRAIN_KEY_ID):
            _w1 = yield from traversal.walk_resilient(SEWER_KEY, radius=2, attempts=3, timeout_ms=90000, log=log)
            if not (_w1):
                return False
            _v2 = ground_items.query().name('Key').where(lambda g: g.id == DRAIN_KEY_ID).within(10).nearest()
            key = (_v2 if _v2 is not None else ground_items.query().name('Key').within(10).nearest())
            if key:
                key.interact('Take')
                yield from execution.delay_until(lambda: held_id(DRAIN_KEY_ID), 6000)
            else:
                log('drainLeg: no "Key" on the sewer floor — despawned? climbing out to re-pour')
        _w3 = yield from traversal.walk_resilient(SEWER_LAND, radius=2, attempts=3, timeout_ms=90000, log=log)
        if not (_w3):
            return False
        _v4 = locs.query().action('Climb-up').within(8).nearest()
        _v5 = (_v4 if _v4 is not None else locs.query().action('Climb up').within(8).nearest())
        up = (_v5 if _v5 is not None else locs.query().name('Manhole').within(8).nearest())
        if not up:
            log('drainLeg: LIVE-VERIFY — no Climb-up/Manhole at the sewer landing (3237,9858); confirm the Varrock-sewer exit')
            return False


        _v6 = ([a for a in up.actions() if 'climb' in a.lower() and 'up' in a.lower()] or [None])[0]
        op = (_v6 if _v6 is not None else (up.actions() or [None])[0])
        if op:
            up.interact(op)

        def _fn7():
            t = game.tile()
            return t is not None and not is_underground(t)
        yield from execution.delay_until(_fn7, 12000)
        return False
    if held_id(DRAIN_KEY_ID):
        return True
    if inventory.contains('Bucket of water'):
        _w8 = yield from traversal.walk_resilient(DRAIN_TILE, radius=2, attempts=3, timeout_ms=90000, log=log)
        if not (_w8):
            return False
        drain = locs.query().name('Drain').within(8).nearest()
        bucket = inventory.first('Bucket of water')
        if drain and bucket:
            bucket.use_on(drain)
            yield from execution.delay_until(lambda: not inventory.contains('Bucket of water'), 6000)
        _w9 = yield from traversal.walk_resilient(MANHOLE_TILE, radius=2, attempts=3, timeout_ms=90000, log=log)
        if not (_w9):
            return False
        closed = locs.query().name('Manhole').action('Open').within(6).nearest()
        if closed:
            closed.interact('Open')
            yield from execution.delay_ticks(2)
        open = locs.query().name('Manhole').action('Climb down').within(6).nearest()
        if open:
            open.interact('Climb down')

            def _fn10():
                t = game.tile()
                return t is not None and is_underground(t)
            yield from execution.delay_until(_fn10, 12000)
        else:
            log('drainLeg: no open Manhole to Climb down — retrying the Open next pass')
        return False
    if inventory.contains('Bucket'):
        _w11 = yield from traversal.walk_resilient(SINK_TILE, radius=2, attempts=3, timeout_ms=90000, log=log)
        if not (_w11):
            return False
        sink = locs.query().name('Sink').within(8).nearest()
        bucket = inventory.first('Bucket')
        if sink and bucket:
            bucket.use_on(sink)
            yield from execution.delay_until(lambda: inventory.contains('Bucket of water'), 6000)
        return False
    yield from execute_step(Record({'kind': 'buy', 'item': 'Bucket', 'qty': 1, 'shop': VARROCK_GENERAL, 'est_gp': 15}), [], log)
    return False


def key_hunt(log):
    here = game.tile()
    if here is None:
        return False
    if is_underground(here):
        _result12 = yield from drain_leg(log)
        return _result12
    has_rovin = held_id(ROVIN_KEY_ID)
    has_traiborn = held_id(TRAIBORN_KEY_ID)
    has_drain = held_id(DRAIN_KEY_ID)
    if has_rovin and has_traiborn and has_drain:
        _w13 = yield from goto_npc(PRYSIN, [], log)
        if not (_w13):
            return False
        yield from talk_through('Sir Prysin', PRYSIN.prefer, log)
        _result14 = yield from execution.delay_until(lambda: inventory.contains('Silverlight'), 6000)
        return _result14
    if not has_rovin and not has_traiborn and not has_drain:
        _w15 = yield from goto_npc(PRYSIN, [], log)
        if not (_w15):
            return False
        yield from talk_through('Sir Prysin', PRYSIN.prefer, log)
    if not has_rovin:
        _w16 = yield from goto_npc(ROVIN, [], log)
        if not (_w16):
            return False
        yield from talk_through('Captain Rovin', ROVIN.prefer, log)
        _result17 = yield from execution.delay_until(lambda: held_id(ROVIN_KEY_ID), 6000)
        return _result17
    if not has_traiborn:
        _v18 = (game.tile().level if game.tile() is not None else None)
        level = (_v18 if _v18 is not None else 0)
        bones = inventory.count('Bones')
        if bones < BONES_NEEDED and not (bones > 0 and inventory.is_full()):
            if level == 1:
                yield from reach.loc_op('Staircase', 'Climb-down', WIZ_L1_STAND, lambda: (((game.tile().level if game.tile() is not None else None) if (game.tile().level if game.tile() is not None else None) is not None else 0)) == 0, log=log)
                return False
            _result19 = yield from grind_goblins(log)
            return _result19
        if level != 1:
            climbed = yield from reach.loc_op('Staircase', 'Climb-up', WIZ_INSIDE_STAND, lambda: (((game.tile().level if game.tile() is not None else None) if (game.tile().level if game.tile() is not None else None) is not None else 0)) >= 1, log=log)
            if climbed == 'unreachable':
                log('demon: tower staircase unreachable — re-entering to re-plan')
            return False
        _w20 = yield from reach.npc_dialog('Traiborn', TRAIBORN.anchor, log=log)
        if (_w20) != 'done':
            return False
        before_hand = inventory.count('Bones')
        yield from talk_through('Traiborn', TRAIBORN.prefer, log)
        # His ritual switches from chat to main-modal message boxes before handing over the key.
        yield from drive_boxes(lambda: held_id(TRAIBORN_KEY_ID), 15000, TRAIBORN.prefer, log)
        if held_id(TRAIBORN_KEY_ID):
            yield from clear_boxes()
            return True
        yield from execution.delay_ticks(2)
        if inventory.count('Bones') < before_hand or chat_dialog.is_open():
            last_bones = inventory.count('Bones')
            settled = 0
            i = 0
            while i < 60 and not held_id(TRAIBORN_KEY_ID):
                if chat_dialog.can_continue():
                    yield from chat_dialog.continue_()
                yield from execution.delay_ticks(1)
                now = inventory.count('Bones')
                settled = (settled + 1 if (not chat_dialog.is_open() and now == last_bones) else 0)
                last_bones = now
                if settled >= 8:
                    break
                i += 1
        return False
    if not has_drain:
        _result21 = yield from drain_leg(log)
        return _result21
    return False


def fight_delrith(log):
    if not equipment.contains('Silverlight'):
        if inventory.contains('Silverlight'):
            yield from equipment.equip('Silverlight')
        return False
    if not chat_dialog.can_continue() and len(chat_dialog.options()) == 0:
        _w22 = yield from traversal.walk_resilient(DELRITH_TILE, radius=4, attempts=3, timeout_ms=90000, log=log)
        if not (_w22):
            return False
        delrith = npcs.query().name('Delrith').action('Attack').within(12).nearest()
        if delrith:
            delrith.interact('Attack')
        elif npcs.query().name('Weakened Delrith').within(12).nearest() is None:
            log('fightDelrith: no Delrith at the stone circle (3229,3369) — LIVE-VERIFY the spawn')
            return False
    _result23 = yield from drive_incantation(log)
    return _result23


def drive_incantation(_log):
    deadline = _core.step_time() + 60000
    while _core.step_time() < deadline:
        if quests.status('Demon Slayer') == 'complete':
            return True
        opts = chat_dialog.options()
        if len(opts) > 0:
            inc = ([o for o in opts if (INCANTATION.lower() in o.lower())] or [None])[0]
            yield from chat_dialog.choose_option((inc if inc is not None else opts[len(opts) - 1]))
            yield from execution.delay_ticks(1)
            continue
        if chat_dialog.can_continue():
            yield from chat_dialog.continue_()
            yield from execution.delay_ticks(1)
            continue
        if not game.in_combat():
            d = npcs.query().name('Delrith').action('Attack').within(12).nearest()
            if d:
                d.interact('Attack')
                yield from execution.delay_until(lambda: game.in_combat() or chat_dialog.can_continue() or len(chat_dialog.options()) > 0, 5000)
                continue
        yield from execution.delay_ticks(2)
    return quests.status('Demon Slayer') == 'complete'


def decide(snap):
    if snap.journal == 'complete':
        return Record({'kind': 'done'})
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    if snap.journal == 'not_started':
        return Record({'kind': 'talk', 'stop': GYPSY})
    if worn(snap, 'Silverlight'):
        return Record({'kind': 'custom', 'name': 'fight Delrith', 'run': fight_delrith})
    if has(snap, 'Silverlight'):
        return Record({'kind': 'equip', 'item': 'Silverlight'})
    keys = [TRAIBORN_KEY_ID, ROVIN_KEY_ID, DRAIN_KEY_ID]
    banked = snap.bank_ids or {}
    carried = snap.inv_ids or {}
    draw = [{'name': 'Key', 'id': id, 'qty': 1} for id in keys if banked.get(id, 0) > 0 and carried.get(id, 0) == 0]
    if draw:
        return Record({'kind': 'withdraw', 'items': draw})
    return Record({'kind': 'custom', 'name': 'key hunt', 'run': key_hunt})


demonslayer = QuestModule(**{
    'record': ([r for r in QUESTS if r.id == 'demon'] or [None])[0],
    'bank': Tile(3185, 3440, 0),
    'grind': ['delrith', 'weakened delrith', 'dark wizard', 'goblin'],
    'gather': Record({
    'bucket of water': fill_bucket,
    'bones': lambda snap, need: (Record({'kind': 'custom', 'name': 'grind bones', 'run': grind_goblins})),
}),
    'tools': ['key', 'silverlight', 'bucket', 'bones', 'coins'],
    'decide': decide,
})
