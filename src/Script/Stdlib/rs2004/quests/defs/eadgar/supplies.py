"""Ported from rs2b0t's src/bot/api/ai/quests/defs/eadgar/supplies.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.entities import ground_items, locs, npcs
from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.quests.defs.eadgar.areas import CHICKEN_NPC_ID, ER_ITEM, ER_TILE, LIQUORS, banked, committed, held, quest_bank, worn
from rs2004.quests.defs.trollstronghold import planned_gear, wear_all
from rs2004.quests.defs.trollstronghold.areas import COMBAT_FOODS, PRAYER_POTIONS, PRAYER_POTION_TARGET, TENZING_BOOTS, TENZING_DONE_RULES
from rs2004.quests.exec.primitives import talk_choosing_by
from rs2004.quests.food import FOOD_FLOAT, quest_food
from rs2004.traversal import traversal

__all__ = ['BOOT_COST', 'COIN_FLOAT', 'COIN_FLOOR', 'FOOD_TARGET', 'SCARECROW_FOOD_TARGET', 'FOOD_FLOOR', 'HECKEL', 'GULLUCK', 'AEMAD', 'JATIX', 'WISTAN', 'food_names', 'food_held', 'scan_bank', 'withdraw', 'source_pestle', 'source_tinderbox', 'source_knife', 'source_axe', 'source_liquor', 'held_liquor', 'prepare', 'source_logs', 'source_chickens', 'source_grain']

BOOT_COST = 12
COIN_FLOAT = 1000
# Why: the float is drawn once and spent down; topping up after every 5gp price walks you to a bank between the pineapple, the vodka and the knife.
COIN_FLOOR = 200
FOOD_TARGET = FOOD_FLOAT
# Why: the scarecrow is 16 slots of grain and chicken, so the float shrinks to make room while that load is still being gathered.
# Why: holding it down across stages 60 and 70 means crossing the thrower gauntlet on 4 lobsters, which killed 3 runs.
SCARECROW_FOOD_TARGET = 6
FOOD_FLOOR = 2
PRICE = Record({'PINEAPPLE': 5, 'LIQUOR': 20, 'KNIFE': 20, 'PESTLE': 20, 'TINDERBOX': 10, 'AXE': 100, 'VIAL': 10})
# Why: `Shop.open` requires the stock owner's display name; no NPC is named "Shop keeper".
HECKEL = Record({'npc': 'Heckel Funch', 'anchor': ER_TILE.HECKEL})
GULLUCK = Record({'npc': 'Gulluck', 'anchor': ER_TILE.GULLUCK})
AEMAD = Record({'npc': 'Aemad', 'anchor': ER_TILE.AEMAD})
JATIX = Record({'npc': 'Jatix', 'anchor': ER_TILE.JATIX})
WISTAN = Record({'npc': 'Wistan', 'anchor': ER_TILE.WISTAN})


def food_names():
    configured = (quest_food.name.strip() if quest_food.name is not None else None)
    names = [n for n in [configured] + list(COMBAT_FOODS) if bool(n)]
    by_lower = {}
    for n in names:
        by_lower[n.lower()] = n
    return list(by_lower.values())


def food_held(snap):
    return sum([pack_count(snap, name) for name in food_names()])


def pack_count(snap, name):
    count = snap.inv.get(name.lower())
    return count if count is not None else 0


def bank_count(snap, name):
    count = snap.bank.get(name.lower()) if snap.bank is not None else None
    return count if count is not None else 0


def scan_bank(snap):
    return (Record({'kind': 'scan_bank', 'bank': quest_bank(snap)}))


def withdraw(snap, items):
    return (Record({'kind': 'withdraw', 'items': items, 'bank': quest_bank(snap)}))


def take(snap, item, qty=1):
    return withdraw(snap, [{'name': item.name, 'id': item.id, 'qty': qty}])


def from_bank(snap, item, qty):
    """Bank first; null when the bank cannot help either."""
    if not snap.bank_known:
        return scan_bank(snap)
    stock = banked(snap, item)
    return (take(snap, item, min(qty - held(snap, item), stock)) if stock > 0 else None)


def buy(item, qty, shop, unit_gp):
    return Record({'kind': 'buy', 'item': item.name, 'qty': qty, 'shop': shop, 'est_gp': qty * unit_gp})


def source(snap, item, qty, shop, unit_gp):
    """Bank, then the shop counter. Null once the pack holds enough."""
    if held(snap, item) >= qty:
        return None
    _v1 = from_bank(snap, item, qty)
    return (_v1 if _v1 is not None else buy(item, qty - held(snap, item), shop, unit_gp))


def source_pestle(snap):
    return source(snap, ER_ITEM.PESTLE, 1, JATIX, PRICE.PESTLE)


# Why: the tinderbox is only wanted on the mountain and Burthorpe Supplies is on the route; Aemad's is 400 tiles the wrong way.
def source_tinderbox(snap):
    return source(snap, ER_ITEM.TINDERBOX, 1, WISTAN, PRICE.TINDERBOX)


def source_knife(snap):
    return source(snap, ER_ITEM.KNIFE, 1, HECKEL, PRICE.KNIFE)


# Why: Gulluck is one ladder above Heckel Funch, so the axe rides the trip the fruit and the vodka already pay for.
def source_axe(snap):
    return source(snap, ER_ITEM.AXE, 1, GULLUCK, PRICE.AXE)


def source_liquor(snap):
    """Any of the 4 liquors the aviary accepts, bank first."""
    if any([held(snap, liquor) > 0 for liquor in LIQUORS]):
        return None
    if not snap.bank_known:
        return scan_bank(snap)
    stocked = ([liquor for liquor in LIQUORS if banked(snap, liquor) > 0] or [None])[0]
    return (take(snap, stocked) if stocked else buy(ER_ITEM.VODKA, 1, HECKEL, PRICE.LIQUOR))


def held_liquor(snap):
    """The liquor this pass will dip the chunks in."""
    _v2 = ([liquor for liquor in LIQUORS if held(snap, liquor) > 0] or [None])[0]
    return (_v2 if _v2 is not None else None)


# Loadout
def keep_ids():
    return [ER_ITEM.get(key).id for key in ER_ITEM.keys()]


def keep_names(snap):
    return [name.lower() for name in [ER_ITEM.get(key).name for key in ER_ITEM.keys()] + [liquor.name for liquor in LIQUORS] + list(food_names()) + list(PRAYER_POTIONS) + list(planned_gear(snap))]


def buy_boots(log):
    if inventory.contains(ER_ITEM.CLIMBING_BOOTS.name):
        return True
    if inventory.count(ER_ITEM.COINS.name) < BOOT_COST:
        log(f'need {BOOT_COST} coins for Climbing boots')
        return False
    # Radius 1: Tenzing is inside his hut and a wider radius is satisfied on the doorstep.
    _w3 = yield from traversal.walk_resilient(ER_TILE.TENZING, radius=1, attempts=3, timeout_ms=180000, log=log)
    if not (_w3):
        return False
    before = inventory.count(ER_ITEM.CLIMBING_BOOTS.name)
    yield from talk_choosing_by(TENZING_BOOTS.npc, TENZING_DONE_RULES, TENZING_BOOTS.prefer, log)
    _result4 = yield from execution.delay_until(lambda: inventory.count(ER_ITEM.CLIMBING_BOOTS.name) > before, 8000)
    return _result4


# Why: this runs on every decide() tick while you're still off the mountain, so each branch has to be idempotent; a step that leaves the snapshot unchanged spins here forever.
def prepare(snap, zone, food_want=None):
    """The loadout in one pure pass; null once the pack is ready to travel."""
    if food_want is None:
        food_want = FOOD_TARGET
    boots_ready = held(snap, ER_ITEM.CLIMBING_BOOTS) > 0 or worn(snap, ER_ITEM.CLIMBING_BOOTS)
    # Past the stile a bank trip means climbing back down the secret way, so only a spent pack or missing boots is worth it.
    if committed(zone) and boots_ready and food_held(snap) >= FOOD_FLOOR:
        if not worn(snap, ER_ITEM.CLIMBING_BOOTS):
            return wear_all([ER_ITEM.CLIMBING_BOOTS.name])
        carried = [name for name in planned_gear(snap) if pack_count(snap, name) > 0]
        return (wear_all(carried) if len(carried) > 0 else None)
    if not snap.bank_known:
        return scan_bank(snap)
    keep = keep_names(snap)
    if any([not (name in keep) for name in list(list(snap.inv.keys()))]):
        return Record({
            'kind': 'deposit',
            'keep': keep,
            'keep_ids': keep_ids(),
            'exact_keep': True,
            'bank': quest_bank(snap),
        })
    from_vault = []
    if held(snap, ER_ITEM.COINS) < COIN_FLOOR and banked(snap, ER_ITEM.COINS) > 0:
        from_vault.append({
            'name': ER_ITEM.COINS.name,
            'id': ER_ITEM.COINS.id,
            'qty': min(COIN_FLOAT - held(snap, ER_ITEM.COINS), banked(snap, ER_ITEM.COINS)),
        })
    if not boots_ready and banked(snap, ER_ITEM.CLIMBING_BOOTS) > 0:
        from_vault.append({'name': ER_ITEM.CLIMBING_BOOTS.name, 'id': ER_ITEM.CLIMBING_BOOTS.id, 'qty': 1})
    # A loadout names what you want; anything the bank lacks is skipped, as this quest fights nothing it can't walk away from.
    for name in planned_gear(snap):
        if pack_count(snap, name) == 0 and bank_count(snap, name) > 0:
            from_vault.append({'name': name, 'qty': 1, 'id': -1})
    have = food_held(snap)
    if have < food_want:
        for name in food_names():
            stock = bank_count(snap, name)
            if stock > 0:
                from_vault.append({'name': name, 'qty': min(food_want - have, stock), 'id': -1})
                break
    # Why: rs2b0t brings no prayer, and an account arriving from Troll Stronghold's fights has none left, so the
    # missile guard had nothing to raise and the throwers killed the run on the scarecrow's thin food float.
    # Troll Stronghold's own optional draw, kept through deposits; the guard sips them below half.
    want_potions = PRAYER_POTION_TARGET - sum([pack_count(snap, name) for name in PRAYER_POTIONS])
    for name in PRAYER_POTIONS:
        if want_potions <= 0:
            break
        stock = bank_count(snap, name)
        if stock > 0:
            take = min(want_potions, stock)
            from_vault.append({'name': name, 'qty': take, 'id': -1})
            want_potions -= take
    if len(from_vault) > 0:
        # Why: only the ranarr vial needs an exact id; food is matched by display name.
        return Record({
            'kind': 'withdraw',
            'bank': quest_bank(snap),
            'items': [({'name': item['name'], 'qty': item['qty']} if item['id'] < 0 else item) for item in from_vault],
        })
    to_wear = [name for name in planned_gear(snap) if pack_count(snap, name) > 0]
    if len(to_wear) > 0:
        return wear_all(to_wear)
    if not boots_ready:
        if held(snap, ER_ITEM.COINS) < BOOT_COST:
            return Record({'kind': 'wait', 'reason': f'need {BOOT_COST} gp for Climbing boots, the bank has none'})
        return Record({'kind': 'custom', 'name': 'buy Climbing boots from Tenzing (12gp)', 'run': buy_boots})
    if not worn(snap, ER_ITEM.CLIMBING_BOOTS):
        return wear_all([ER_ITEM.CLIMBING_BOOTS.name])
    if food_held(snap) == 0:
        return Record({'kind': 'wait', 'reason': f"no food in the bank (tried {', '.join(food_names())})"})
    return None


# Gathering
def take_ground(name, log):
    drop = ground_items.query().name(name).within(12).nearest()
    if not drop:
        return False
    log(f'taking {name}')
    before = inventory.count(name)
    _c7 = (drop.interact('Take'))
    if not (_c7):
        return _c7
    # Why: rs2b0t waited for the pack to contain the item, which the second chicken already does, so every Take read as landed at once and the hunt spent its 60 passes in under a second.
    _result8 = yield from execution.delay_until(lambda: inventory.count(name) > before, 8000)
    return _result8


# Why: logs are wanted twice, with the chickens and grain in Ardougne and again beside the Falador bank for the drying fire; one anchor makes the other trip 500 tiles longer.
def nearest_trees():
    here = game.tile()
    if not here:
        return ER_TILE.TREES
    return (ER_TILE.TREES if ER_TILE.TREES.distance_to(here) <= ER_TILE.TREES_FALADOR.distance_to(here) else ER_TILE.TREES_FALADOR)


def chop_logs(qty, log):
    """Chop until the pack holds `qty` logs."""
    trees = nearest_trees()
    for attempt in range(40):
        if inventory.count(ER_ITEM.LOGS.name) >= qty:
            return True
        here = game.tile()
        if not here or trees.distance_to(here) > 12:
            _w9 = yield from traversal.walk_resilient(trees, radius=6, attempts=3, timeout_ms=180000, log=log)
            if not (_w9):
                return False
        tree = locs.query().name('Tree').action('Chop down').within(10).nearest()
        if not tree:
            yield from execution.delay_ticks(2)
            continue
        before = inventory.count(ER_ITEM.LOGS.name)
        if tree.interact('Chop down'):
            yield from execution.delay_until(lambda: inventory.count(ER_ITEM.LOGS.name) > before, 30000)
    log(f'could not cut {qty} logs')
    return False


# Why: arming a protection prayer for a level-1 chicken burns a bar the stronghold walk still needs, so this is a plain attack-and-loot loop.
def hunt_chickens(qty, log):
    """Kill chickens at the Ardougne farm until the pack holds `qty` raw chicken."""
    for attempt in range(60):
        if inventory.count(ER_ITEM.RAW_CHICKEN.name) >= qty:
            return True
        _w10 = yield from take_ground(ER_ITEM.RAW_CHICKEN.name, log)
        if _w10:
            continue
        here = game.tile()
        if not here or ER_TILE.CHICKENS.distance_to(here) > 10:
            _w11 = yield from traversal.walk_resilient(ER_TILE.CHICKENS, radius=5, attempts=3, timeout_ms=180000, log=log)
            if not (_w11):
                return False
            continue
        if game.in_combat():
            yield from execution.delay_until(lambda: not game.in_combat(), 60000)
            continue
        target = npcs.query().where(lambda n: n.id == CHICKEN_NPC_ID and not n.in_combat and not n.targets_another_player()).action('Attack').within(12).nearest()
        if not target:
            yield from execution.delay_ticks(3)
            continue
        game.set_combat_style('strength')
        if not (target.interact('Attack')):
            continue
        yield from execution.delay_until(lambda: ground_items.query().name(ER_ITEM.RAW_CHICKEN.name).within(12).nearest() is not None or not target.valid(), 60000)
    log(f'could not gather {qty} raw chicken')
    return False


def source_logs(snap, qty):
    """Bank, then the trees north of the Ardougne bank. Null once the pack holds enough."""
    if held(snap, ER_ITEM.LOGS) >= qty:
        return None
    _v12 = from_bank(snap, ER_ITEM.LOGS, qty)
    _v13 = (_v12 if _v12 is not None else source_axe(snap))
    return (_v13 if _v13 is not None else Record({'kind': 'custom', 'name': f'chop {qty} logs', 'run': lambda log: chop_logs(qty, log)}))


def source_chickens(snap, qty):
    """Bank, then the Ardougne farm. Null once the pack holds enough."""
    if held(snap, ER_ITEM.RAW_CHICKEN) >= qty:
        return None
    _v14 = from_bank(snap, ER_ITEM.RAW_CHICKEN, qty)
    return (_v14 if _v14 is not None else Record({
        'kind': 'custom',
        'name': f'kill chickens for {qty} raw chicken',
        'run': lambda log: hunt_chickens(qty, log),
    }))


# Why: the field behind the stile is the closest wheat to the zoo, the trees and the chicken farm, where the rest of the scarecrow comes from.
def source_grain(snap, qty):
    """Bank, then the Ardougne wheat field, one sheaf per pass."""
    if held(snap, ER_ITEM.GRAIN) >= qty:
        return None
    _v15 = from_bank(snap, ER_ITEM.GRAIN, qty)
    return (_v15 if _v15 is not None else Record({'kind': 'pick_loc', 'loc': 'Wheat', 'op': 'Pick', 'item': ER_ITEM.GRAIN.name, 'anchor': ER_TILE.WHEAT}))
