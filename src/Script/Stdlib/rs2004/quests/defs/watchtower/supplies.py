"""Ported from rs2b0t's src/bot/api/ai/quests/defs/watchtower/supplies.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.geometry import Tile
from rs2004.quests.defs.watchtower.areas import WT_ITEM, WT_TILE
from rs2004.quests.food import quest_food

__all__ = ['ARDOUGNE_ADVENTURER', 'MAGIC_GUILD', 'VARROCK_RUNES', 'OGRE_HERBLORE', 'held', 'banked', 'owned', 'withdraw_from', 'scan_bank', 'source', 'bank_only', 'source_coins', 'source_rope', 'source_death_rune', 'source_vial', 'source_pestle', 'source_pickaxe', 'source_light_source', 'carried_food', 'source_food', 'make_room', 'quest_kit']

# Why: every shop here was read out of the engine's own configs.
# Why: nobody in this game is called 'Shop keeper'; the shop belongs to a named NPC through param=owned_shop, and Shop.open() matches on the display name.
ARDOUGNE_ADVENTURER = Record({'npc': 'Aemad', 'anchor': Tile(2613, 3294, 0)})
MAGIC_GUILD = Record({'npc': 'Magic Store owner', 'anchor': Tile(2595, 3087, 1)})
# Why: the Magic Guild's door turns away anyone under Magic 66 ("The magical energy in here is unsafe"), and the
# record asks only 14, so a lower account buys its rune from Aubury, the nearest other death-rune stock.
VARROCK_RUNES = Record({'npc': 'Aubury', 'anchor': Tile(3253, 3402, 0)})
MAGIC_GUILD_LEVEL = 66
OGRE_HERBLORE = Record({'npc': 'Ogre merchant', 'anchor': Tile(2528, 3048, 0)})
# Shop asking prices run above the obj cost, so each of these leaves headroom.
ROPE_PRICE = 60
DEATH_RUNE_PRICE = 120
VIAL_PRICE = 20
PESTLE_PRICE = 40
PICKAXE_PRICE = 60


def held(snap, id):
    _v1 = (snap.inv_ids.get(id) if snap.inv_ids is not None else None)
    return (_v1 if _v1 is not None else 0)


def banked(snap, id):
    _v2 = (snap.bank_ids.get(id) if snap.bank_ids is not None else None)
    return (_v2 if _v2 is not None else 0)


def owned(snap, id):
    return held(snap, id) + banked(snap, id)


KIT_ITEMS = [
    WT_ITEM.ROPE,
    WT_ITEM.LIT_CANDLE,
    WT_ITEM.VIAL_WATER,
    WT_ITEM.GUAM_LEAF,
    WT_ITEM.PESTLE,
    WT_ITEM.PICKAXE,
    WT_ITEM.BAT_BONES,
    WT_ITEM.DRAGON_BONES,
    WT_ITEM.DEATH_RUNE,
    WT_ITEM.GOLD_BAR,
    WT_ITEM.SKAVID_MAP,
]
KIT_COINS = 2000


def withdraw_from(items):
    return Record({'kind': 'withdraw', 'items': items, 'bank': WT_TILE.YANILLE_BANK})


def scan_bank():
    return Record({'kind': 'scan_bank', 'bank': WT_TILE.YANILLE_BANK})


def source(snap, item, qty, shop, unit_gp):
    """Bank first, then shop. Null once the pack already holds enough."""
    if held(snap, item.id) >= qty:
        return None
    if not snap.bank_known:
        return scan_bank()
    missing = qty - held(snap, item.id)
    in_bank = banked(snap, item.id)
    if in_bank > 0:
        return withdraw_from([{'name': item.name, 'id': item.id, 'qty': min(missing, in_bank)}])
    return Record({'kind': 'buy', 'item': item.name, 'qty': missing, 'shop': shop, 'est_gp': missing * unit_gp})


def bank_only(snap, item, qty=1):
    """Bank-only item; wait for the user when the bank has none."""
    if held(snap, item.id) >= qty:
        return None
    if not snap.bank_known:
        return scan_bank()
    in_bank = banked(snap, item.id)
    if in_bank > 0:
        return withdraw_from([{'name': item.name, 'id': item.id, 'qty': min(qty - held(snap, item.id), in_bank)}])
    return Record({'kind': 'wait', 'reason': f'no {item.name} in the bank — it is a drop-only item'})


def source_coins(snap, want):
    if held(snap, WT_ITEM.COINS.id) >= want:
        return None
    if not snap.bank_known:
        return scan_bank()
    available = banked(snap, WT_ITEM.COINS.id)
    if available <= 0:
        return Record({'kind': 'wait', 'reason': f'need {want} gp for Gu\'Tanoth tolls and shops'})
    return withdraw_from([{'name': WT_ITEM.COINS.name, 'id': WT_ITEM.COINS.id, 'qty': min(want, available)}])


def source_rope(snap):
    return source(snap, WT_ITEM.ROPE, 1, ARDOUGNE_ADVENTURER, ROPE_PRICE)


def source_death_rune(snap):
    shop = (VARROCK_RUNES if snap.magic is not None and snap.magic < MAGIC_GUILD_LEVEL else MAGIC_GUILD)
    return source(snap, WT_ITEM.DEATH_RUNE, 1, shop, DEATH_RUNE_PRICE)


def source_vial(snap):
    return source(snap, WT_ITEM.VIAL_WATER, 1, ARDOUGNE_ADVENTURER, VIAL_PRICE)


def source_pestle(snap):
    return source(snap, WT_ITEM.PESTLE, 1, OGRE_HERBLORE, PESTLE_PRICE)


# Why: the Rock of Dalgroth is the quest's only mining, and without a pickaxe the rock gives no response at all, so the step retries forever.
# Why: Aemad stocks bronze, which is all a max-stats miner needs here.
def source_pickaxe(snap):
    """Source a pickaxe, or null when one is held."""
    return source(snap, WT_ITEM.PICKAXE, 1, ARDOUGNE_ADVENTURER, PICKAXE_PRICE)


def source_light_source(snap):
    """The candle by the tower respawns already lit, so no tinderbox is needed."""
    if held(snap, WT_ITEM.LIT_CANDLE.id) > 0:
        return None
    if banked(snap, WT_ITEM.LIT_CANDLE.id) > 0:
        return withdraw_from([{'name': WT_ITEM.LIT_CANDLE.name, 'id': WT_ITEM.LIT_CANDLE.id, 'qty': 1}])
    return Record({'kind': 'grab_ground', 'item': WT_ITEM.LIT_CANDLE.name, 'anchor': WT_TILE.CANDLE, 'wait_if_missing': True})


# Why: Check the selected food first, then fallbacks, so other banked food can still provision the enclave trip.
FALLBACK_FOODS = ['Tuna', 'Swordfish', 'Lobster']


def quest_foods():
    """The configured food, then the fish the module falls back on."""
    chosen = (quest_food.name.strip() if quest_food.name is not None else None)
    out = ([chosen] if chosen else [])
    for food in FALLBACK_FOODS:
        if not any([name.lower() == food.lower() for name in out]):
            out.append(food)
    return out


def carried_food(snap):
    return sum([((snap.inv.get(food.lower()) if snap.inv.get(food.lower()) is not None else 0)) for food in quest_foods()])


# Why: the shamans are 99 in every combat stat and respawn about every 100 ticks, so an enclave trip without food is a death.
# Why: ownsInventory means the engine's own food provisioning never runs for this quest.
def source_food(snap, want):
    """Source `want` food, or null when the pack has it."""
    carried = carried_food(snap)
    if carried >= want:
        return None
    if not snap.bank_known:
        return scan_bank()
    for food in quest_foods():
        _v3 = (snap.bank.get(food.lower()) if snap.bank is not None else None)
        in_bank = (_v3 if _v3 is not None else 0)
        if in_bank > 0:
            # Why: a withdrawal past the free slots draws what fits and asks again for the rest into a full pack forever.
            room = (snap.free_slots if snap.free_slots is not None else want)
            if room <= 0:
                return (None if carried > 0 else Record({'kind': 'wait', 'reason': 'no room in the pack for the shaman enclave food'}))
            return Record({
                'kind': 'withdraw',
                'items': [{'name': food, 'qty': min(want - carried, in_bank, room)}],
                'bank': WT_TILE.YANILLE_BANK,
            })
    return Record({'kind': 'wait', 'reason': 'no food in the bank for the shaman enclave'})


# Why: ownsInventory skips the engine's bank-to-nothing, so a quest resumed after another one starts on that quest's
# leftovers, and a full pack refuses every shop buy and withdrawal (live: Aemad's rope, 0 free after The Grand Tree).
QUEST_ITEMS = [getattr(WT_ITEM, key) for key in WT_ITEM.keys()]
KEEP_NAMES = ['prayer']


def make_room(snap):
    """Bank everything but quest items, food and prayer potions when the pack is full; None while it has room or
    holds nothing else to bank."""
    if snap.free_slots is None or snap.free_slots > 0 or snap.inv is None:
        return None
    keep = [name.lower() for name in quest_foods() + KEEP_NAMES]
    quest_names = [item.name.lower() for item in QUEST_ITEMS]
    spare = [name for name in list(snap.inv.keys()) if not (name in quest_names) and not any([k in name for k in keep])]
    if len(spare) == 0:
        return None
    return Record({
        'kind': 'deposit',
        'keep': quest_foods() + KEEP_NAMES,
        'keep_ids': [item.id for item in QUEST_ITEMS],
        'bank': WT_TILE.YANILLE_BANK,
    })


# Why: the bank supplies the kit in one go; sourcing item by item costs a trip each from wherever the quest has got to.
# Why: only what the bank holds is asked for, so the shop, the ground candle and the guard's riddle stay as fallbacks and an empty bank changes nothing.
def quest_kit(snap, food_want):
    """Everything the kit still needs that the bank can supply, in one withdrawal."""
    # Why: an unread bank is left to the first stage that needs a scan, so a quest wanting nothing more from the bank never takes a trip to prove it.
    if not snap.bank_known:
        return None
    items = []
    for item in KIT_ITEMS:
        missing = 1 - held(snap, item.id)
        if missing > 0 and banked(snap, item.id) > 0:
            items.append({'name': item.name, 'id': item.id, 'qty': missing})
    # Why: gear is what the trip is for; a purse 23 coins down or a lobster eaten is no reason to walk back to Yanille, and the stage sourcers refill those.
    # Why: topping a delta up each tick ran 16 bank trips and fed the no-progress watchdog until it parked the quest.
    if len(items) == 0:
        return None
    coins_short = KIT_COINS - held(snap, WT_ITEM.COINS.id)
    banked_coins = banked(snap, WT_ITEM.COINS.id)
    if coins_short > 0 and banked_coins > 0:
        items.append({'name': WT_ITEM.COINS.name, 'id': WT_ITEM.COINS.id, 'qty': min(coins_short, banked_coins)})
    food_short = food_want - carried_food(snap)
    if food_short > 0:
        for food in quest_foods():
            _v4 = (snap.bank.get(food.lower()) if snap.bank is not None else None)
            in_bank = (_v4 if _v4 is not None else 0)
            if in_bank > 0:
                items.append({'name': food, 'qty': min(food_short, in_bank)})
                break
    return (withdraw_from(items) if len(items) > 0 else None)
