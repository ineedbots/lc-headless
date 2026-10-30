"""Ported from rs2b0t's src/bot/api/ai/quests/defs/fishingcontest/supplies.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.entities import locs
from rs2004.execution import event_signal
from rs2004.messages import CANT_REACH, game_messages
from rs2004.traversal import traversal
from rs2004.quests.engine.types import banked_id, held_id
from rs2004.quests.exec.garlic import GARLIC, take_garlic
from rs2004.quests.exec.prompts import held_id as live_held_id, settle_scene
from rs2004.quests.defs.fishingcontest.areas import FC_ID, FC_TILE, HARRY_SHOP, nearest_spade, RED_VINE_LOCS
from rs2004.quests.defs.fishingcontest.contest import claim_pass
from rs2004.quests.engine.types import QuestModule, QuestProgress
from rs2004.quests.data import quest_record

__all__ = ['ITEM', 'ENTRY_FEE', 'WORM_TARGET', 'source_pass', 'source_garlic', 'source_rod', 'source_spade', 'source_fee', 'source_worms']

ITEM = Record({
    'PASS': 'Fishing pass',
    'ROD': 'Fishing rod',
    'SPADE': 'Spade',
    'WORM': 'Red vine worm',
    'TROPHY': 'Fishing trophy',
    'COINS': 'Coins',
})
ENTRY_FEE = 5
# Why: 3 casts win the contest, and the spare 2 cover a cast the server refused and a death on the way in.
WORM_TARGET = 5
ROD_GP = 60
COIN_TRIP = 200
DIG_MS = 10000


def from_bank(snap, id, name, qty):
    if not snap.bank_known:
        return Record({'kind': 'scan_bank'})
    banked = banked_id(snap, id)
    return (Record({'kind': 'withdraw', 'items': [{'name': name, 'qty': min(qty, banked), 'id': id}]}) if banked > 0 else None)


def source_pass(snap):
    if held_id(snap, FC_ID.PASS) > 0:
        return None
    _v1 = from_bank(snap, FC_ID.PASS, ITEM.PASS, 1)
    return (_v1 if _v1 is not None else Record({'kind': 'custom', 'name': 'ask the dwarf for another competition pass', 'run': claim_pass}))


def source_garlic(snap):
    if held_id(snap, FC_ID.GARLIC) > 0:
        return None
    _v2 = from_bank(snap, FC_ID.GARLIC, GARLIC, 1)
    return (_v2 if _v2 is not None else Record({'kind': 'custom', 'name': "take garlic from Morgan's cupboard", 'run': take_garlic}))


def source_rod(snap):
    if held_id(snap, FC_ID.FISHING_ROD) > 0:
        return None
    _v3 = from_bank(snap, FC_ID.FISHING_ROD, ITEM.ROD, 1)
    return (_v3 if _v3 is not None else Record({'kind': 'buy', 'item': ITEM.ROD, 'qty': 1, 'shop': HARRY_SHOP, 'est_gp': ROD_GP}))


def source_spade(snap):
    if held_id(snap, FC_ID.SPADE) > 0:
        return None
    _v4 = from_bank(snap, FC_ID.SPADE, ITEM.SPADE, 1)
    return (_v4 if _v4 is not None else Record({'kind': 'grab_ground', 'item': ITEM.SPADE, 'anchor': nearest_spade(snap.tile), 'wait_if_missing': True}))


def source_fee(snap):
    if held_id(snap, FC_ID.COINS) >= ENTRY_FEE:
        return None
    _v5 = from_bank(snap, FC_ID.COINS, ITEM.COINS, COIN_TRIP)
    return (_v5 if _v5 is not None else Record({'kind': 'wait', 'reason': f'no coins for the {ENTRY_FEE}gp contest entry fee'}))


# Why: `need` is 1 once the contest is under way; topping a half-spent pack back to 5 would walk out of Hemenster mid-round and lose the entry at the gate.
def source_worms(snap, need):
    """Top the pack back to {@link WORM_TARGET} whenever it holds fewer than `need`."""
    held = held_id(snap, FC_ID.RED_VINE_WORM)
    if held >= need:
        return None
    banked = from_bank(snap, FC_ID.RED_VINE_WORM, ITEM.WORM, WORM_TARGET - held)
    if banked:
        return banked
    _v6 = source_spade(snap)
    return (_v6 if _v6 is not None else Record({
        'kind': 'custom',
        'name': f'dig {WORM_TARGET - held} red vine worm(s)',
        'run': lambda log: dig_worms(WORM_TARGET, log),
    }))


# Why: the wood is a sealed pocket whose one entrance, the loose railing, is already a baked transport, so the walk needs no leg of its own.
# Why: the server can only path to some of the 20-odd vines from a given tile (the nearest answered "I can't reach that!" from 1 step away while its neighbour dug fine), so walk the ring.
def dig_worms(target, log):
    """Dig the red-worm patch in McGrubor's Wood up to `target` worms."""

    def held():
        return live_held_id(FC_ID.RED_VINE_WORM)

    if held() >= target:
        return True
    _w7 = yield from traversal.walk_resilient(FC_TILE.VINES, radius=2, attempts=3, timeout_ms=180000, log=log)
    if not (_w7):
        return False
    yield from settle_scene()
    # Why: reachability is a property of the pair, so a refusal is only evidence until the next dig moves the character.
    refused = set()
    while held() < target:
        if event_signal.pending():
            return False
        vine = (sorted([l for l in locs.query().where(lambda l: (l.id in RED_VINE_LOCS)).action('Check').within(8).results() if not (f'{l.tile().x},{l.tile().z}' in refused)], key=lambda a: a.distance()) or [None])[0]
        if not vine:
            log(f'no reachable red-worm Vine at ({FC_TILE.VINES.x},{FC_TILE.VINES.z}) — {len(refused)} refused')
            return False
        before = held()
        mark = game_messages.mark()
        if not (vine.interact('Check')):
            return False
        yield from execution.delay_until(lambda: held() > before or game_messages.saw_since(mark, CANT_REACH), DIG_MS)
        if held() > before:
            refused.clear()
            continue
        refused.add(f'{vine.tile().x},{vine.tile().z}')
    return True
