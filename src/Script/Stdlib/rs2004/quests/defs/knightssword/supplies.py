"""Ported from rs2b0t's src/bot/api/ai/quests/defs/knightssword/supplies.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.dialogue import chat_dialog
from rs2004.entities import locs
from rs2004.game import skills
from rs2004.items import inventory
from rs2004.quests.defs.doric import DORIC_PICKAXES
from rs2004.quests.defs.knightssword.areas import GENERAL_STORE, KS_ID, KS_NAME, KS_TILE, WYDIN
from rs2004.quests.exec.primitives import is_underground
from rs2004.quests.exec.prompts import drive_until, use_on_loc
from rs2004.traversal import traversal


__all__ = ['COIN_FLOAT', 'COIN_LOW', 'held_id', 'banked_id', 'kit', 'pie_dish', 'pie', 'ORE_PER_TRIP', 'pickaxe_at', 'iron_bars_at', 'pickaxe']

COINS_ID = 995
# Why: `buy` withdraws `estGp` per shortfall, so fixed-balance top-ups would add a bank trip after every item.
COIN_FLOAT = 1000
COIN_LOW = 200
SHOP_GP = 30


def held_id(snap, id):
    _v1 = (snap.inv_ids or {}).get(id)
    return (_v1 if _v1 is not None else 0)


def banked_id(snap, id):
    _v2 = (snap.bank_ids or {}).get(id)
    return (_v2 if _v2 is not None else 0)


def withdraw(items):
    return Record({'kind': 'withdraw', 'items': items})


# Why: no bank is pinned, as the quest runs across Falador, Varrock, Port Sarim and Rimmington.
# Why: bank contents are global, so naming one booth costs a kingdom-crossing on every leg that touches it.
scan_bank = Record({'kind': 'scan_bank'})


# Why: `ownsInventory` opts this quest out of the engine's coin and food withdrawal, so the module draws both itself.
# Why: food is only asked for above ground; a top-up mid-dungeon walks the bot back out.
def kit(snap, food=None):
    """The module's own coin and food withdrawal, or null when the pack is ready."""
    underground = (is_underground(snap.tile) if snap.tile else False)
    items = []
    if held_id(snap, COINS_ID) < COIN_LOW:
        items.append({'name': 'Coins', 'qty': COIN_FLOAT, 'id': COINS_ID})
    if food and not underground and food.held < food.low:
        items.append({'name': food.name, 'qty': food.target - food.held})
    if len(items) == 0:
        return None
    return (withdraw(items) if snap.bank_known else scan_bank)


def fill_bucket(log):
    """The palace-kitchen sink, 2 tiles from the pie-dish spawn."""
    _result3 = yield from use_on_loc(KS_ID.BUCKET, Record({'name': 'Sink', 'near': KS_TILE.KITCHEN_SINK}), [], lambda: inventory.count_by_id(KS_ID.BUCKET_OF_WATER) > 0, log)
    return _result3


def mix_dough(log):
    flour = inventory.first(KS_NAME.POT_OF_FLOUR)
    water = inventory.first(KS_NAME.BUCKET_OF_WATER)
    if not flour or not water:
        log('no flour or water in the pack to mix')
        return False
    if not (flour.use_on(water)):
        return False
    # dough_interface offers bread / pastry / pizza / pitta; only pastry makes a shell.
    _result4 = yield from drive_until(lambda: inventory.count_by_id(KS_ID.PASTRY_DOUGH) > 0, ['Pastry dough'], log)
    return _result4


# Why: the Range carries no ops; cooking is `[oplocu,_cooking_oven]`, a use-on like filling the bucket.
# Why: Redberry pie requires an oven; a fire is rejected.
def cook_pie(log):
    """Bake the redberry pie on a range."""
    _result5 = yield from use_on_loc(KS_ID.UNCOOKED_PIE, Record({'name': 'Range', 'near': KS_TILE.RANGE}), [], lambda: inventory.count_by_id(KS_ID.REDBERRY_PIE) > 0 or inventory.count_by_id(KS_ID.BURNT_PIE) > 0, log)
    return _result5


def empty_burnt_pie(log):
    burnt = inventory.first(KS_NAME.BURNT_PIE)
    if not burnt:
        return True
    log('the pie burnt — recovering the dish')
    if not (burnt.interact('Empty Dish')):
        return False
    _result6 = yield from execution.delay_until(lambda: inventory.count_by_id(KS_ID.PIE_DISH) > 0, 8000)
    return _result6


def buy(item, shop):
    return (Record({'kind': 'buy', 'item': item, 'qty': 1, 'shop': shop, 'est_gp': SHOP_GP}))


def pie_dish(snap):
    return (withdraw([{'name': KS_NAME.PIE_DISH, 'qty': 1, 'id': KS_ID.PIE_DISH}]) if banked_id(snap, KS_ID.PIE_DISH) > 0 else Record({
        'kind': 'grab_ground',
        'item': KS_NAME.PIE_DISH,
        'anchor': KS_TILE.PIE_DISH_SPAWN,
        'wait_if_missing': True,
    }))


def combine(item, target, product):
    return (Record({
        'kind': 'use_on',
        'item': item,
        'target_kind': 'item',
        'target': target,
        'anchor': KS_TILE.WYDIN,
        'product': product,
    }))


# Why: the chain is read backwards from the pie, so a part-built chain resumes at the right rung.
# Why: nothing in the game sells a redberry pie and there is no ground spawn, so it has to be baked.
def pie(snap):
    """The next rung of the redberry-pie chain."""
    if held_id(snap, KS_ID.REDBERRY_PIE) > 0:
        return Record({'kind': 'wait', 'reason': 'redberry pie already held'})
    if not snap.bank_known:
        return scan_bank
    if banked_id(snap, KS_ID.REDBERRY_PIE) > 0:
        return withdraw([{'name': KS_NAME.REDBERRY_PIE, 'qty': 1, 'id': KS_ID.REDBERRY_PIE}])
    # Why: the burnt pie still holds the dish and Empty Dish is a free op; re-deriving would walk back to Varrock.
    if held_id(snap, KS_ID.BURNT_PIE) > 0:
        return Record({'kind': 'custom', 'name': 'empty the burnt dish', 'run': empty_burnt_pie})
    if held_id(snap, KS_ID.UNCOOKED_PIE) > 0:
        return Record({'kind': 'custom', 'name': 'cook the redberry pie', 'run': cook_pie})
    if held_id(snap, KS_ID.PIE_SHELL) > 0:
        return (combine(KS_NAME.REDBERRIES, KS_NAME.PIE_SHELL, KS_NAME.UNCOOKED_PIE) if held_id(snap, KS_ID.REDBERRIES) > 0 else buy(KS_NAME.REDBERRIES, WYDIN))
    if held_id(snap, KS_ID.PASTRY_DOUGH) > 0:
        return (combine(KS_NAME.PASTRY_DOUGH, KS_NAME.PIE_DISH, KS_NAME.PIE_SHELL) if held_id(snap, KS_ID.PIE_DISH) > 0 else pie_dish(snap))
    # Why: the water side is a Varrock errand and the rest is Port Sarim, so the bucket and sink come first and each town is left once.
    # Why: buying the bucket from Port Sarim's reach costs a 360-tile round trip back to Falador between the berries and the range.
    if held_id(snap, KS_ID.BUCKET_OF_WATER) == 0:
        return (Record({'kind': 'custom', 'name': 'fill the bucket', 'run': fill_bucket}) if held_id(snap, KS_ID.BUCKET) > 0 else buy(KS_NAME.BUCKET, GENERAL_STORE))
    if held_id(snap, KS_ID.PIE_DISH) == 0:
        return pie_dish(snap)
    if held_id(snap, KS_ID.POT_OF_FLOUR) == 0:
        return buy(KS_NAME.POT_OF_FLOUR, WYDIN)
    if held_id(snap, KS_ID.REDBERRIES) == 0:
        return buy(KS_NAME.REDBERRIES, WYDIN)
    return Record({'kind': 'custom', 'name': 'mix pastry dough', 'run': mix_dough})


# Why: smelting.rs2 loses half of every batch, "The ore is too impure and you fail to refine it."
# Why: 8 ore leaves a 9-in-256 chance of not clearing 2 bars, and a short batch is a no-op as the loop re-derives from the bar count.
ORE_PER_TRIP = 8


def pick_held(snap, p):
    return held_id(snap, p.id) > 0 or (((p.id in (snap.worn_ids or set())) if (p.id in (snap.worn_ids or set())) is not None else False))


def best_pick(level, has):
    """Best-first, so the strongest pickaxe the level allows wins."""
    _v7 = ([p for p in DORIC_PICKAXES if level >= p.level and has(p)] or [None])[0]
    return (_v7 if _v7 is not None else None)


def pickaxe_at(snap, mining_level):
    if best_pick(mining_level, lambda p: pick_held(snap, p)):
        return None
    if not snap.bank_known:
        return scan_bank
    banked = best_pick(mining_level, lambda p: banked_id(snap, p.id) > 0)
    if banked:
        return withdraw([{'name': banked.name, 'qty': 1, 'id': banked.id}])
    return Record({'kind': 'grab_ground', 'item': 'Bronze pickaxe', 'anchor': KS_TILE.PICKAXE_SPAWN, 'wait_if_missing': True})


def smelt_iron(log):
    _w8 = yield from traversal.walk_resilient(KS_TILE.FURNACE, radius=2, attempts=4, timeout_ms=300000, log=log)
    if not (_w8):
        return False
    before = inventory.count_by_id(KS_ID.IRON_BAR)
    furnace = locs.query().name('Furnace').action('Smelt').within(8).nearest()
    if not furnace or not (furnace.interact('Smelt')):
        log('the Falador furnace did not answer')
        return False
    _w9 = yield from execution.delay_until(lambda: chat_dialog.is_make_menu(), 8000)
    if not (_w9):
        log('the smelting menu never opened')
        return False
    _w10 = yield from chat_dialog.make_x('Iron', ORE_PER_TRIP)
    if not (_w10):
        log(f"no 'Iron' in the smelt menu: [{', '.join(chat_dialog.make_products())}]")
        return False
    yield from execution.delay_until(lambda: inventory.count_by_id(KS_ID.IRON_ORE) == 0, 120000)
    return inventory.count_by_id(KS_ID.IRON_BAR) > before


def iron_bars_at(snap, mining_level, smithing_level):
    """Nothing sells iron bars, Drogo's Mining Emporium stocks zero and the only ground spawn is deep in the Wilderness, so smelt them."""
    held = held_id(snap, KS_ID.IRON_BAR)
    if held >= 2:
        return Record({'kind': 'wait', 'reason': 'two iron bars already held'})
    if not snap.bank_known:
        return scan_bank
    banked = banked_id(snap, KS_ID.IRON_BAR)
    if banked > 0:
        return withdraw([{'name': KS_NAME.IRON_BAR, 'qty': min(2 - held, banked), 'id': KS_ID.IRON_BAR}])
    if smithing_level < 15:
        return Record({
            'kind': 'wait',
            'reason': 'Smithing 15 is required to smelt iron bars; train Smithing or obtain and bank two Iron bars',
        })
    # Why: `mineRock` ignores its qty and mines one ore per invocation, so the batch is counted here.
    # Why: smelting on the first ore would walk the 130 tiles between Rimmington and the furnace 8 times.
    if held_id(snap, KS_ID.IRON_ORE) >= ORE_PER_TRIP:
        return Record({'kind': 'custom', 'name': 'smelt iron bars', 'run': smelt_iron})
    if mining_level < 15:
        return Record({
            'kind': 'wait',
            'reason': 'Mining 15 is required to mine iron ore; train Mining or obtain and bank two Iron bars',
        })
    _v11 = pickaxe_at(snap, mining_level)
    return (_v11 if _v11 is not None else Record({
        'kind': 'mine_rock',
        'rock': 'Iron',
        'item': KS_NAME.IRON_ORE,
        'qty': ORE_PER_TRIP,
        'anchor': KS_TILE.IRON_ROCKS,
    }))


def pickaxe(snap):
    return pickaxe_at(snap, skills.level('mining'))
