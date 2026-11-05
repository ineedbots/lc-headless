"""Ported from rs2b0t's src/bot/api/ai/quests/defs/familycrest/fish.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.fishing import spot_matches_method
from rs2004.catalogs.record import Record
from rs2004.dialogue import chat_dialog
from rs2004.entities import locs, npcs
from rs2004.game import skills
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.quests.defs.familycrest.areas import FC_BANK
from rs2004.quests.defs.familycrest.supplies import deposit, from_bank, held
from rs2004.traversal import traversal

__all__ = ['CALEB_KEEP', 'source_caleb_fish']

SHORE = Tile(2845, 3431, 0)
RIVER = Tile(3104, 3424, 0)
RANGE = Tile(2817, 3443, 0)
HARRY = Record({'npc': 'Harry', 'anchor': Tile(2831, 3446, 0)})
GERRANT = Record({'npc': 'Gerrant', 'anchor': Tile(3013, 3225, 0)})
FISH = [
    Record({
    'id': 373,
    'name': 'Swordfish',
    'raw': 371,
    'fishing': 50,
    'cooking': 45,
    'tool': 'Harpoon',
    'op': 'Harpoon',
    'pair': 'Cage',
    'spot': SHORE,
}),
    Record({
    'id': 365,
    'name': 'Bass',
    'raw': 363,
    'fishing': 46,
    'cooking': 43,
    'tool': 'Big fishing net',
    'op': 'Net',
    'pair': 'Harpoon',
    'spot': SHORE,
}),
    Record({
    'id': 361,
    'name': 'Tuna',
    'raw': 359,
    'fishing': 35,
    'cooking': 30,
    'tool': 'Harpoon',
    'op': 'Harpoon',
    'pair': 'Cage',
    'spot': SHORE,
}),
    Record({
    'id': 329,
    'name': 'Salmon',
    'raw': 331,
    'fishing': 30,
    'cooking': 25,
    'tool': 'Fly fishing rod',
    'op': 'Lure',
    'pair': 'Bait',
    'spot': RIVER,
}),
    Record({
    'id': 315,
    'name': 'Shrimps',
    'raw': 317,
    'fishing': 1,
    'cooking': 1,
    'tool': 'Small fishing net',
    'op': 'Net',
    'pair': 'Bait',
    'spot': SHORE,
}),
]
CALEB_KEEP = ['Coins'] + list([f.tool for f in FISH]) + ['Feather', 'rune', 'Ring of dueling']


def catch_fish(fish, log):
    _w1 = yield from traversal.walk_resilient(fish.spot, radius=3, attempts=3, timeout_ms=300000, log=log)
    if not (_w1):
        return False
    spot = npcs.query().name('Fishing spot').where(lambda n: spot_matches_method(n.actions(), fish)).within(20).nearest()
    if not spot:
        return False
    before = len(inventory.items())
    if not (spot.interact(fish.op)):
        return False
    _result2 = yield from execution.delay_until(lambda: len(inventory.items()) > before, 30000)
    return _result2


def cook_fish(fish, log):
    _w3 = yield from traversal.walk_resilient(RANGE, radius=1, attempts=3, timeout_ms=300000, log=log)
    if not (_w3):
        return False
    raw = ([i for i in inventory.items() if i.id == fish.raw] or [None])[0]
    range_ = locs.query().name('Range').within(6).nearest()
    if not raw or not range_:
        return False
    before = inventory.count_by_id(fish.raw)
    if not (raw.use_on(range_)):
        return False
    yield from execution.delay_until(lambda: inventory.count_by_id(fish.raw) < before or chat_dialog.is_make_menu(), 6000)
    if chat_dialog.is_make_menu():
        yield from chat_dialog.make(f'Raw {fish.name.lower()}')
    _result4 = yield from execution.delay_until(lambda: inventory.count_by_id(fish.raw) < before, 8000)
    return _result4


def source_caleb_fish(snap, missing, fishing=None, cooking=None):
    if fishing is None:
        fishing = skills.level('fishing')
    if cooking is None:
        cooking = skills.level('cooking')
    fish = ([f for f in FISH if any([m.id == f.id for m in missing])] or [None])[0]
    raw = Record({'id': fish.raw, 'name': f'Raw {fish.name.lower()}'})
    banked = from_bank(snap, raw, 1, FC_BANK.CATHERBY)
    if held(snap, fish.raw) == 0 and banked:
        return banked
    if cooking < fish.cooking or (held(snap, fish.raw) == 0 and fishing < fish.fishing):
        return Record({
            'kind': 'wait',
            'reason': f"Caleb needs cooked {', '.join([f.name for f in missing])}; gathering {fish.name} needs Fishing {fish.fishing} and Cooking {fish.cooking} (have {fishing}/{cooking})",
        })
    if held(snap, fish.raw) > 0:
        return Record({'kind': 'custom', 'name': f'cook {fish.name} for Caleb', 'run': lambda log: cook_fish(fish, log)})
    if ((snap.free_slots if snap.free_slots is not None else 28)) < 4:
        return deposit(CALEB_KEEP, FC_BANK.CATHERBY)
    for tool in [fish.tool] + list(((['Feather'] if fish.op == 'Lure' else []))):
        _v5 = snap.inv.get(tool.lower())
        if ((_v5 if _v5 is not None else 0)) > 0:
            continue
        _v6 = (snap.bank.get(tool.lower()) if snap.bank is not None else None)
        available = (_v6 if _v6 is not None else 0)
        qty = (min(20, available or 20) if tool == 'Feather' else 1)
        if available > 0:
            return Record({'kind': 'withdraw', 'items': [{'name': tool, 'qty': qty}], 'bank': FC_BANK.CATHERBY})
        return Record({
            'kind': 'buy',
            'item': tool,
            'qty': qty,
            'shop': (GERRANT if fish.op == 'Lure' else HARRY),
            'est_gp': 1000,
        })
    return Record({'kind': 'custom', 'name': f'catch {fish.name} for Caleb', 'run': lambda log: catch_fish(fish, log)})
