"""Ported from rs2b0t's src/bot/api/ai/quests/defs/shilo/supplies.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.dialogue import chat_dialog
from rs2004.entities import ground_items, locs
from rs2004.items import inventory
from rs2004.quests.defs.shilo.areas import BONE_SPAWNS, SV_ITEM, SV_NPC, SV_TILE
from rs2004.quests.food import quest_food
from rs2004.trade import shop
from rs2004.traversal import traversal

__all__ = ['KARAMJA_PURSE', 'FOOD_FALLBACKS', 'held', 'banked', 'owned', 'worn', 'scan_bank', 'withdraw_from', 'source_coins', 'source_tools', 'food_names', 'food_held', 'source_food', 'source_lit_candle', 'light_candle', 'source_bronze_wire', 'source_bones', 'gather_bones']

# Why: Jiminua stocks rope, spade, chisel, candle, tinderbox, hammer and a bronze bar 35 tiles from Trufitus, and Karamja has no bank until this quest opens Shilo's, so everything but coins, bones and food is bought here.
JIMINUA_SHOP = Record({'npc': SV_NPC.JIMINUA, 'anchor': SV_TILE.JIMINUA})
KARAMJA_PURSE = 2000
FOOD_FALLBACKS = ['Lobster', 'Swordfish', 'Tuna', 'Salmon', 'Trout']


def held(snap, id):
    _v1 = (snap.inv_ids.get(id) if snap.inv_ids is not None else None)
    return (_v1 if _v1 is not None else 0)


def banked(snap, id):
    _v2 = (snap.bank_ids.get(id) if snap.bank_ids is not None else None)
    return (_v2 if _v2 is not None else 0)


def banked_by_name(snap, name):
    _v3 = (snap.bank.get(name.lower()) if snap.bank is not None else None)
    return (_v3 if _v3 is not None else 0)


def owned(snap, id):
    return held(snap, id) + banked(snap, id)


def worn(snap, id):
    return snap.worn_ids is not None and id in snap.worn_ids


def scan_bank():
    return Record({'kind': 'scan_bank', 'bank': SV_TILE.ARDOUGNE_BANK})


def withdraw_from(items):
    return Record({'kind': 'withdraw', 'items': items, 'bank': SV_TILE.ARDOUGNE_BANK})


# Why: Jiminua is 35 tiles from Trufitus but the mound is 200 the other way, so buying one item per trip costs 6 crossings of the island.
def stock_up(wanted):
    """Buy every tool the rest of the quest still needs in one visit."""
    list_ = ', '.join([f'{w.qty}× {w.item.name}' for w in wanted])
    return Record({'kind': 'custom', 'name': f'buy {list_} from Jiminua', 'run': lambda log: buy_kit(wanted, log)})


def buy_kit(wanted, log):
    _w5 = yield from traversal.walk_resilient(SV_TILE.JIMINUA, radius=3, attempts=3, timeout_ms=240000, log=log)
    if not (_w5):
        return False
    _w6 = yield from shop.open(JIMINUA_SHOP.npc)
    if not (_w6):
        log("could not open Jiminua's shop")
        return False
    bought = 0
    for _item7 in wanted:
        item = _item7.item
        qty = _item7.qty
        short = qty - carried_id(item.id)
        if short <= 0:
            continue
        _w8 = yield from shop.buy(item.name, short)
        if (_w8) > 0:
            bought += 1
        else:
            log(f'Jiminua is out of {item.name}, or the purse is empty')
    yield from shop.close()
    return bought > 0


def carried_id(id):
    return sum([entry.count for entry in [entry for entry in inventory.items() if entry.id == id]])


def source_coins(snap, want):
    """The engine's `buy` step falls back to a bank trip when short of coin and Karamja has none, so the purse is filled at Ardougne before crossing."""
    if held(snap, SV_ITEM.COINS.id) >= want:
        return None
    if not snap.bank_known:
        return scan_bank()
    available = banked(snap, SV_ITEM.COINS.id)
    if available <= 0:
        return Record({'kind': 'wait', 'reason': f'need {want} gp for the Karamja crossing and Jiminua\'s shop'})
    return withdraw_from([{'name': SV_ITEM.COINS.name, 'id': SV_ITEM.COINS.id, 'qty': min(want, available)}])


def kit_shortfall(snap, need):
    """The outstanding toolkit; one `stockUp` step buys all of it in a single visit."""
    return [(Record({'item': item, 'qty': 1})) for item in [item for item in need if held(snap, item.id) == 0]]


def source_tools(snap, need):
    short = kit_shortfall(snap, need)
    return (None if len(short) == 0 else stock_up(short))


def food_names():
    """What the pack may eat, the food the script was given first."""
    chosen = (quest_food.name.strip() if quest_food.name is not None else None)
    names = [n for n in [chosen] + list(FOOD_FALLBACKS) if bool(n)]
    unique = []
    seen = set()
    for n in names:
        if n.lower() in seen:
            continue
        seen.add(n.lower())
        unique.append(n)
    return unique


def held_by_name(snap, name):
    count = snap.inv.get(name.lower())
    return count if count is not None else 0


def food_held(snap):
    return sum([held_by_name(snap, name) for name in food_names()])


# Why: `ownsInventory` opts out of the engine's food withdrawal, and nothing on Karamja sells food worth taking to Nazastarool, so the pack is filled at Ardougne.
def source_food(snap, want):
    """Draw `want` food from Ardougne, or null once the pack carries it."""
    carried = food_held(snap)
    if carried >= want:
        return None
    if not snap.bank_known:
        return scan_bank()
    stocked = ([name for name in food_names() if banked_by_name(snap, name) > 0] or [None])[0]
    if not stocked:
        return Record({'kind': 'wait', 'reason': f"bank has no food: none of {', '.join(food_names())}"})
    return withdraw_from([{'name': stocked, 'qty': min(want - carried, banked_by_name(snap, stocked))}])


def source_lit_candle(snap, need=None):
    """Only a lit candle, lit black candle or lit torch satisfies the fissure, and the shop sells the candle unlit, so the tinderbox rides along."""
    if need is None:
        need = []
    if held(snap, SV_ITEM.LIT_CANDLE.id) > 0:
        return None
    short = kit_shortfall(snap, list(need) + [SV_ITEM.CANDLE, SV_ITEM.TINDERBOX])
    if len(short) > 0:
        return stock_up(short)
    return Record({'kind': 'custom', 'name': 'light the candle', 'run': light_candle})


def light_candle(log):
    candle = ([item for item in inventory.items() if item.id == SV_ITEM.CANDLE.id] or [None])[0]
    tinderbox = ([item for item in inventory.items() if item.id == SV_ITEM.TINDERBOX.id] or [None])[0]
    if not candle or not tinderbox:
        log('no candle or tinderbox to light with')
        return False
    if not (candle.use_on(tinderbox)):
        return False
    _result9 = yield from execution.delay_until(lambda: any([item.id == SV_ITEM.LIT_CANDLE.id for item in inventory.items()]), 6000)
    return _result9


def source_bronze_wire(snap, need=None):
    """Nothing sells bronze wire; Smithing 4 turns a Jiminua bar into one at the Tai Bwo Wannai anvil."""
    if need is None:
        need = []
    if held(snap, SV_ITEM.BRONZE_WIRE.id) > 0:
        return None
    short = kit_shortfall(snap, list(need) + [SV_ITEM.BRONZE_BAR, SV_ITEM.HAMMER])
    if len(short) > 0:
        return stock_up(short)
    return Record({'kind': 'custom', 'name': 'smith the bronze bar into wire', 'run': smith_bronze_wire})


def smith_bronze_wire(log):
    if any([item.id == SV_ITEM.BRONZE_WIRE.id for item in inventory.items()]):
        return True
    _w10 = yield from traversal.walk_resilient(SV_TILE.ANVIL, radius=2, attempts=3, timeout_ms=120000, log=log)
    if not (_w10):
        return False
    bar = ([item for item in inventory.items() if item.id == SV_ITEM.BRONZE_BAR.id] or [None])[0]
    anvil = locs.query().name('Anvil').within(8).nearest()
    if not bar or not anvil:
        log('no bronze bar in the pack, or no anvil in range at Tai Bwo Wannai')
        return False
    if not (bar.use_on(anvil)):
        return False
    _w11 = yield from execution.delay_until(lambda: chat_dialog.is_main_make_panel(), 8000)
    if not (_w11):
        log('the anvil panel never opened')
        return False
    _w12 = yield from chat_dialog.make_from_panel('Bronze wire')
    if not (_w12):
        log(f"no 'Bronze wire' on the anvil panel: {', '.join(chat_dialog.main_make_products())}")
        return False
    _result13 = yield from execution.delay_until(lambda: any([item.id == SV_ITEM.BRONZE_WIRE.id for item in inventory.items()]), 12000)
    return _result13


def source_bones(snap, want):
    """No shop sells bones and every NPC this quest kills has `death_drop=null`, so the 3 for the tomb door come from the bank or the Khazard battlefield spawns."""
    carried = held(snap, SV_ITEM.BONES.id)
    if carried >= want:
        return None
    if not snap.bank_known:
        return scan_bank()
    in_bank = banked(snap, SV_ITEM.BONES.id)
    if in_bank > 0:
        return withdraw_from([{'name': SV_ITEM.BONES.name, 'id': SV_ITEM.BONES.id, 'qty': min(want - carried, in_bank)}])
    return Record({
        'kind': 'custom',
        'name': f'pick up {want - carried} bones on the battlefield',
        'run': lambda log: gather_bones(want, log),
    })


def gather_bones(want, log):
    def carried():
        return sum([i.count for i in [item for item in inventory.items() if item.id == SV_ITEM.BONES.id]])

    for spawn in BONE_SPAWNS:
        if carried() >= want:
            return True
        _w14 = yield from traversal.walk_resilient(spawn, radius=3, attempts=2, timeout_ms=120000, log=log)
        if not (_w14):
            continue
        # Each battlefield tile respawns one pile, so take every pile in range before walking to the next.
        while carried() < want:
            before = carried()
            pile = ground_items.query().name(SV_ITEM.BONES.name).within(6).nearest()
            if not pile or not (pile.interact('Take')):
                break
            _w15 = yield from execution.delay_until(lambda: carried() > before, 5000)
            if not (_w15):
                break
    return carried() >= want
