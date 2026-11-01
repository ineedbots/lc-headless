"""Ported from rs2b0t's src/bot/api/ai/quests/defs/horror/supplies.ts (MIT, see thirdparty/rs2b0t)."""

import math
from rs2004 import execution
from rs2004.catalogs.loadout import weapon_of
from rs2004.catalogs.record import Record
from rs2004.entities import locs
from rs2004.game import skills
from rs2004.geometry import Tile
from rs2004.items import equipment, inventory
from rs2004.quests.defs.dragonslayer.supplies import smith_nails
from rs2004.quests.defs.elementalworkshop.areas import PICKAXES
from rs2004.quests.defs.horror.areas import ARCHERY_SHOP, GENERAL_SHOP, HD_ID, HD_ITEM, HD_LOC, HD_TILE, RUNE_SHOP, SWORD_SHOP
from rs2004.quests.exec.prompts import use_on_loc
from rs2004.quests.food import FOOD_FLOAT, quest_food
from rs2004.quests.gear import quest_loadout
from rs2004.quests.prayer import PRAYER_POTION_IDS
from rs2004.quests.weapons import banked_pickaxe, live_best_weapon
from rs2004.traversal import traversal

__all__ = ['PLANKS_NEEDED', 'NAILS_NEEDED', 'held_id', 'banked_id', 'food_want', 'kit', 'hammer', 'planks', 'nails', 'rune_kit', 'dungeon_kit', 'make_room', 'prayer_potions', 'melee_weapon_name', 'melee_ready', 'warn_horror_readiness', 'HORROR_TOOLS', 'sealed_area']

COIN_FLOAT = 20000
COIN_LOW = 2000
SHOP_GP = 1500
# Why: the dungeon load is 15 slots before food (coins, hammer, pickaxe, key, tinderbox, dagger, arrows, 6 rune stacks, tar, glass) and the quest ends by pushing a casket into the pack, so leave the last slot free.
FOOD_TARGET = FOOD_FLOAT
FOOD_LOW = 4
TRAVEL_FOOD = 4
PLANKS_NEEDED = 2
NAILS_NEEDED = 8
# Why: Carry about 60 casts plus one of each elemental rune for the strange wall; Aubury restocks depleted runes one at a time.
# Why: with nav teleports on the air stack also pays hops, 3 per standard and 5 for Camelot over about 30 hops, so the headroom keeps routing out of the fight's supply.
RUNES = [
    Record({'id': HD_ID.AIR_RUNE, 'name': HD_ITEM.AIR_RUNE, 'qty': 350}),
    Record({'id': HD_ID.WATER_RUNE, 'name': HD_ITEM.WATER_RUNE, 'qty': 120}),
    Record({'id': HD_ID.EARTH_RUNE, 'name': HD_ITEM.EARTH_RUNE, 'qty': 120}),
    Record({'id': HD_ID.FIRE_RUNE, 'name': HD_ITEM.FIRE_RUNE, 'qty': 130}),
    Record({'id': HD_ID.DEATH_RUNE, 'name': HD_ITEM.DEATH_RUNE, 'qty': 80}),
    Record({'id': HD_ID.CHAOS_RUNE, 'name': HD_ITEM.CHAOS_RUNE, 'qty': 80}),
]
# Why: law is the limiting rune at 1 or 2 a teleport, the elemental halves come out of {@link RUNES}, and 60 is about double a full run's hop count.
# Why: bank-only, since the Magic Guild (66 magic) and the Mage Arena are the only shops that stock it; a bank without law falls back to walking.
LAW_RUNES = 60
LAW_LOW = math.ceil(LAW_RUNES / 3)
PRAYER_DOSES = 3
PRAYER_POTION_NAMES = {2434: 'Prayer potion(4)', 139: 'Prayer potion(3)', 141: 'Prayer potion(2)', 143: 'Prayer potion(1)'}


def held_id(snap, id):
    _v1 = (snap.inv_ids.get(id) if snap.inv_ids is not None else None)
    return (_v1 if _v1 is not None else 0)


def banked_id(snap, id):
    _v2 = (snap.bank_ids.get(id) if snap.bank_ids is not None else None)
    return (_v2 if _v2 is not None else 0)


def withdraw(items):
    return (Record({'kind': 'withdraw', 'items': items}))


scan_bank = Record({'kind': 'scan_bank'})


def buy(item, qty, shop, est_gp=None):
    if est_gp is None:
        est_gp = SHOP_GP
    return (Record({'kind': 'buy', 'item': item, 'qty': qty, 'shop': shop, 'est_gp': est_gp}))


# Why: `snap.bankIds` is empty before the first bank scan, so preserve unknown state before shopping.
def from_bank(snap, id, name, qty):
    """Withdraw from the bank when it can help, before any shop trip."""
    if not snap.bank_known:
        return scan_bank
    banked = banked_id(snap, id)
    if banked <= 0:
        return None
    return withdraw([{'name': name, 'qty': min(qty, banked), 'id': id}])


def source(snap, id, name, qty, shop, est_gp=None):
    if est_gp is None:
        est_gp = SHOP_GP
    _v3 = from_bank(snap, id, name, qty)
    return (_v3 if _v3 is not None else buy(name, qty, shop, est_gp))


# Why: nothing before the lighthouse is a fight, and the nails leg needs 12 slots of ore on top of coins, hammer and pickaxe; 15 sharks leaves 10 free and `smithNails` stops on "pack is full, no room for Coal".
def food_want(snap, stage):
    """How much food this stage wants, or null."""
    name = (quest_food.name.strip() if quest_food.name is not None else None)
    if not name:
        return None
    full = stage >= 2
    _v4 = snap.inv.get(name.lower())
    return Record({
        'name': name,
        'held': (_v4 if _v4 is not None else 0),
        'target': (FOOD_TARGET if full else TRAVEL_FOOD),
        'low': (FOOD_LOW if full else 1),
    })


def _kept(name, keep):
    return any([k in name for k in keep])


# Why: the nails leg leaves ore and gems behind, and a queue resumed after another quest carries that quest's pack; rs2b0t asks the bank for what a full pack can't take, until the quest parks.
def make_room(snap, stage):
    """With a full pack, bank what this stage has no use for; null with room, or when everything carried is wanted."""
    if (snap.free_slots if snap.free_slots is not None else 28) > 0 or not snap.bank_known:
        return None
    keep = list(HORROR_TOOLS) if stage < 2 else [name for name in HORROR_TOOLS if name not in PAST_THE_BRIDGE]
    keep += ['prayer potion', 'law rune']
    food = quest_food.name.strip().lower() if quest_food.name is not None else ''
    if food:
        keep.append(food)
    weapon = melee_weapon_name()
    if weapon:
        keep.append(weapon.lower())
    if not any([not _kept(name, keep) for name in snap.inv.keys()]):
        return None
    return Record({'kind': 'deposit', 'keep': keep})


# Why: `ownsInventory` opts out of the engine's coin and food withdrawal; the float is a threshold since a `buy` step withdraws `estGp` when short, and topping up to an exact balance means a booth trip per purchase.
def kit(snap, food=None):
    """The module's own coin and food withdrawal, or null when the pack is ready."""
    items = []
    if held_id(snap, HD_ID.COINS) < COIN_LOW:
        items.append({'name': HD_ITEM.COINS, 'qty': COIN_FLOAT, 'id': HD_ID.COINS})
    if food and food.held < food.low:
        room = snap.free_slots if snap.free_slots is not None else 28
        if room > 0:
            items.append({'name': food.name, 'qty': min(food.target - food.held, room)})
    if len(items) == 0:
        return None
    return (withdraw(items) if snap.bank_known else scan_bank)


# Why: most accounts already own a hammer, and a bare `buy` walks past a bankful to pay for another.
def hammer(snap):
    """Source the bridge hammer, bank before shop."""
    return source(snap, HD_ID.HAMMER, HD_ITEM.HAMMER, 1, GENERAL_SHOP, 100)


def planks(snap):
    """Four `woodplank` spawns sit north-east of the Barbarian Outpost gate."""
    held = held_id(snap, HD_ID.PLANK)
    need = PLANKS_NEEDED - held
    _v5 = from_bank(snap, HD_ID.PLANK, HD_ITEM.PLANK, need)
    return (_v5 if _v5 is not None else Record({'kind': 'grab_ground', 'item': HD_ITEM.PLANK, 'anchor': HD_TILE.PLANK_SPAWNS[0], 'wait_if_missing': True}))


# Why: nothing sells nails or steel bars, so they're mined, smelted and hammered by Dragon Slayer's ship-repair chain.
def nails(snap):
    """Source the 8 steel nails: the bank's nails, then its steel, then the ore chain."""
    held = held_id(snap, HD_ID.NAILS)
    need = NAILS_NEEDED - held
    if need <= 0:
        return Record({'kind': 'wait', 'reason': 'nails already held'})
    from_nails = from_bank(snap, HD_ID.NAILS, HD_ITEM.NAILS, need)
    if from_nails:
        return from_nails
    # Why: `smithNails` only reads steel in the pack, so banked bars (2 nails each) get withdrawn to skip the ore chain.
    bars = math.ceil(need / 2)
    if held_id(snap, HD_ID.STEEL_BAR) < bars:
        from_steel = from_bank(snap, HD_ID.STEEL_BAR, 'Steel bar', bars - held_id(snap, HD_ID.STEEL_BAR))
        if from_steel:
            return from_steel
        # Prefer the best owned pickaxe; the ground-spawn fallback is bronze.
        pick = banked_pickaxe(snap.bank_ids, (snap.attack if snap.attack is not None else 0))
        if pick and not any([held_id(snap, p.id) > 0 or (snap.worn_ids is not None and p.id in snap.worn_ids) for p in PICKAXES]):
            return withdraw([{'name': pick.name, 'qty': 1, 'id': pick.id}])
    return Record({'kind': 'custom', 'name': f'smith {need} nails', 'run': lambda log: smith_nails(need, log)})


# Why: both the Range and the Furnace are `forceapproach=east`, which rotates with placement: the Yanille range is angle 0 so east is east, the Ardougne furnace angle 2 so its "east" is west.
# Why: from any other side the use-on is silently dropped, so this lands on the exact tile.
def use_on_loc_from(stand, item_id, loc_name, done, log):
    """Use a held item on a loc from an exact tile."""
    if done():
        return True
    _w6 = yield from traversal.walk_resilient(stand, radius=0, attempts=4, timeout_ms=300000, log=log)
    if not (_w6):
        log(f'could not stand on ({stand.x},{stand.z}) to use the {loc_name}')
        return False
    yield from execution.delay_ticks(2)
    loc = locs.query().name(loc_name).within(6).nearest()
    item = ([entry for entry in inventory.items() if entry.id == item_id] or [None])[0]
    if not loc or not item:
        log(f'no {loc_name} in reach, or nothing to use on it')
        return False
    if not (item.use_on(loc)):
        return False
    _result7 = yield from execution.delay_until(done, 12000)
    return _result7


def cook_seaweed(log):
    return use_on_loc_from(HD_TILE.YANILLE_RANGE, HD_ID.SEAWEED, HD_LOC.RANGE, lambda: inventory.count_by_id(HD_ID.SODA_ASH) > 0, log)


def fill_sand(log):
    return use_on_loc(HD_ID.BUCKET, Record({'name': HD_LOC.SAND_PIT, 'near': HD_TILE.SAND_PIT}), [], lambda: inventory.count_by_id(HD_ID.BUCKET_OF_SAND) > 0, log)


# Why: sand and soda ash on a furnace run `smelt_glass`; Rellekka's furnace is nearer but refuses anyone without The Fremennik Trials, so this is East Ardougne's.
def smelt_glass(log):
    return use_on_loc_from(HD_TILE.FURNACE, HD_ID.BUCKET_OF_SAND, HD_LOC.FURNACE, lambda: inventory.count_by_id(HD_ID.MOLTEN_GLASS) > 0, log)


# Why: the chain is read backwards from the glass so a part-built one resumes at the right rung; nothing sells glass, soda ash, sand or seaweed.
# Why: seaweed is the Rellekka shore (Catherby's spawns are on an unwalkable islet) and cooks to soda ash on the Yanille range, 7 tiles from the sand pit.
def molten_glass(snap):
    """The next rung of the molten-glass chain."""
    if held_id(snap, HD_ID.MOLTEN_GLASS) > 0:
        return Record({'kind': 'wait', 'reason': 'molten glass already held'})
    banked = from_bank(snap, HD_ID.MOLTEN_GLASS, HD_ITEM.MOLTEN_GLASS, 1)
    if banked:
        return banked
    ash = held_id(snap, HD_ID.SODA_ASH)
    sand = held_id(snap, HD_ID.BUCKET_OF_SAND)
    if ash > 0 and sand > 0:
        return Record({'kind': 'custom', 'name': 'smelt molten glass', 'run': smelt_glass})
    if ash == 0:
        if held_id(snap, HD_ID.SEAWEED) > 0:
            return Record({'kind': 'custom', 'name': 'cook seaweed into soda ash', 'run': cook_seaweed})
        return Record({'kind': 'grab_ground', 'item': HD_ITEM.SEAWEED, 'anchor': HD_TILE.SEAWEED, 'wait_if_missing': True})
    if held_id(snap, HD_ID.BUCKET) == 0:
        return source(snap, HD_ID.BUCKET, HD_ITEM.BUCKET, 1, GENERAL_SHOP, 100)
    return Record({'kind': 'custom', 'name': 'fill a bucket with sand', 'run': fill_sand})


def glass_wanted(snap):
    """True while the glass still has to be made."""
    return held_id(snap, HD_ID.MOLTEN_GLASS) == 0 and banked_id(snap, HD_ID.MOLTEN_GLASS) == 0


def swamp_tar(snap):
    """Lumbridge swamp: 17 spawns, the only ones outside Morytania."""
    _v8 = from_bank(snap, HD_ID.SWAMP_TAR, HD_ITEM.SWAMP_TAR, 1)
    return (_v8 if _v8 is not None else Record({'kind': 'grab_ground', 'item': HD_ITEM.SWAMP_TAR, 'anchor': HD_TILE.SWAMP_TAR, 'wait_if_missing': True}))


# Why: split out of {@link dungeonKit} because with nav teleports on it's worth a Varrock counter before the 10-bar barcrawl, and a hop is only planned when the live pack can pay for it.
# Why: law isn't in {@link kit}, which runs every decide tick: `smithNails` banks the pack for ore and law isn't on its keep-list, so a per-tick top-up and the nails leg would deposit each other's work forever.
def rune_kit(snap, teleports=None):
    """The rune kit, law from the bank, the elements from Aubury."""
    if teleports is None:
        teleports = traversal.teleports_enabled()
    if teleports and held_id(snap, HD_ID.LAW_RUNE) < LAW_LOW:
        # Why: `bankIds` is blank until a booth has been opened, so an unread bank can't be called empty or the toggle does nothing.
        if not snap.bank_known:
            return scan_bank
        banked = banked_id(snap, HD_ID.LAW_RUNE)
        if banked > 0:
            return withdraw([{'name': HD_ITEM.LAW_RUNE, 'qty': min(LAW_RUNES, banked), 'id': HD_ID.LAW_RUNE}])
    for rune in RUNES:
        # Half is the top-up mark: buying the last 100 after every splash would walk the bot back to Varrock mid-quest.
        if held_id(snap, rune.id) < rune.qty / 2:
            _v9 = from_bank(snap, rune.id, rune.name, rune.qty)
            return (_v9 if _v9 is not None else buy(rune.name, rune.qty - held_id(snap, rune.id), RUNE_SHOP, 20000))
    return None


# Why: owning its inventory opts the quest out of the engine's potion draw, and rs2b0t's max Prayer never felt it; at Prayer 43 the walk in spent the bar and the mother hit an unprotected account from 96 to dead in 7 seconds.
def prayer_potions(snap):
    """The doses the two back-to-back fights lean on, when the bank has any."""
    held = sum([held_id(snap, id) for id in PRAYER_POTION_IDS])
    if held >= PRAYER_DOSES or not snap.bank_known:
        return None
    for id in PRAYER_POTION_IDS:
        banked = banked_id(snap, id)
        if banked > 0:
            return withdraw([{'name': PRAYER_POTION_NAMES[id], 'qty': min(PRAYER_DOSES - held, banked), 'id': id}])
    return None


# Why: the order makes the 2 Varrock shops and 2 ground-spawn errands happen once each; `needLight` goes false once the lamp is lit, past which tinderbox, tar and glass are spent and re-sourcing them is a wasted trip.
def dungeon_kit(snap, need_light):
    """The one shortfall worth acting on, or null when the load is complete."""
    if need_light and held_id(snap, HD_ID.TINDERBOX) == 0:
        return source(snap, HD_ID.TINDERBOX, HD_ITEM.TINDERBOX, 1, GENERAL_SHOP, 100)
    # Why: the bucket rides the tinderbox's counter; left to the glass chain it's asked for at the Yanille range, 900 tiles and 2 boat fares from the nearest general store in Varrock.
    if need_light and glass_wanted(snap) and held_id(snap, HD_ID.BUCKET) == 0 and held_id(snap, HD_ID.BUCKET_OF_SAND) == 0:
        return source(snap, HD_ID.BUCKET, HD_ITEM.BUCKET, 1, GENERAL_SHOP, 100)
    if held_id(snap, HD_ID.DAGGER) == 0:
        return source(snap, HD_ID.DAGGER, HD_ITEM.DAGGER, 1, SWORD_SHOP, 200)
    if held_id(snap, HD_ID.ARROW) == 0:
        return source(snap, HD_ID.ARROW, HD_ITEM.ARROW, 5, ARCHERY_SHOP, 100)
    runes = rune_kit(snap)
    if runes:
        return runes
    melee = melee_weapon(snap)
    if melee:
        return melee
    potions = prayer_potions(snap)
    if potions:
        return potions
    if need_light and held_id(snap, HD_ID.SWAMP_TAR) == 0:
        return swamp_tar(snap)
    if need_light and held_id(snap, HD_ID.MOLTEN_GLASS) == 0:
        return molten_glass(snap)
    return None


# Why: Zeke's Superior Scimitars stops at mithril, so the weapon is whatever the loadout holds; absent or unwieldable, the fights fall back to magic and pray through the melee form.
melee_gave_up = False
WIELD_TRIES = 3
wield_tries = 0


def melee_weapon_name():
    # Why: no shop sells a rune scimitar, so the fallback is the best tier the account's Attack level reaches and already owns.
    name = weapon_of(quest_loadout.current)
    if name is None:
        best = live_best_weapon()
        name = best.name if best is not None else None
    name = name.strip() if name is not None else None
    return name if name else None


def melee_ready():
    """True once the weapon is wielded."""
    name = melee_weapon_name()
    return name is not None and equipment.contains(name)


def wield_melee(name, log):
    global wield_tries, melee_gave_up
    if equipment.contains(name):
        return True
    _w12 = yield from equipment.equip(name)
    if _w12:
        log(f'wielded the {name}')
        wield_tries = 0
        return True
    # An attack level short of the weapon's requirement refuses silently.
    wield_tries += 1
    if wield_tries >= WIELD_TRIES:
        melee_gave_up = True
        log(f'could not wield the {name} after {WIELD_TRIES} tries ' + f"(attack {skills.level('attack')}), falling back to the magic-only fight")
    return False


def melee_weapon(snap):
    global melee_gave_up
    name = melee_weapon_name()
    if not name or melee_gave_up:
        return None
    key = name.lower()
    if (key in snap.worn):
        return None
    if snap.inv.get(key, 0) > 0:
        return Record({'kind': 'custom', 'name': f'wield the {name}', 'run': lambda log: wield_melee(name, log)})
    if not snap.bank_known:
        return scan_bank
    if (snap.bank.get(key, 0) if snap.bank is not None else 0) <= 0:
        # The magic loadout wins the quest on its own.
        melee_gave_up = True
        return None
    return withdraw([{'name': name, 'qty': 1}])


# Why: the server doesn't gate these but the quest needs them: `smithing` is the nails (2 to a steel bar at 34), `crafting` the glass, `magic` the mother fight's spell tier.
# Why: `prayer` 43 covers both protections, melee for the junior and missiles for the mother, whose ranged attack hits 24.
HD_PROVEN_SKILLS = Record({'smithing': 34, 'crafting': 1, 'magic': 59, 'prayer': 43})
MAGIC_FLOOR = 13


def warn_horror_readiness():
    have = {
        'smithing': skills.level('smithing'),
        'crafting': skills.level('crafting'),
        'magic': skills.level('magic'),
        'prayer': skills.level('prayer'),
    }
    if have['magic'] < MAGIC_FLOOR:
        magic = have['magic']
        return f'magic {magic} cannot cast Fire Strike, and four of the Dagannoth mother\'s six forms take damage from nothing else'
    short = [f'{s} {have[s]}/{HD_PROVEN_SKILLS.get(s)}' for s in HD_PROVEN_SKILLS.keys() if have[s] < HD_PROVEN_SKILLS.get(s)]
    if len(short) == 0:
        return None
    return f"below the proven profile ({', '.join(short)}); headed PASS at max stats. " + 'Low magic makes the mother a long fight, and without the protection prayers she ranges for up to 24 a hit.'


HORROR_TOOLS = [
    'coins',
    'hammer',
    'plank',
    'nails',
    'tinderbox',
    'swamp tar',
    'molten glass',
    'soda ash',
    'bucket',
    'bucket of sand',
    'seaweed',
    'lighthouse key',
    'air rune',
    'water rune',
    'earth rune',
    'fire rune',
    'death rune',
    'chaos rune',
    'bronze dagger',
    'bronze arrow',
    'barcrawl card',
    'rusty casket',
    'pickaxe',
    'iron ore',
    'coal',
    'steel bar',
]


# What the bridge and its nails were for, spare past it.
PAST_THE_BRIDGE = ['hammer', 'plank', 'nails', 'pickaxe', 'iron ore', 'coal', 'steel bar']


def sealed_area(tile):
    """True while standing anywhere a bank trip cannot start from."""
    if not tile:
        return False
    # The broken lighthouse copy (38_71) and the cavern beneath it (39_72).
    if tile.z >= 4544 and tile.z <= 4671 and tile.x >= 2432 and tile.x <= 2559:
        return True
    # The post-quest cavern the completion teleport lands in.
    if tile.z >= 9984 and tile.z <= 10047 and tile.x >= 2496 and tile.x <= 2559:
        return True
    # The lighthouse above the ground floor.
    return tile.level > 0 and tile.x >= 2503 and tile.x <= 2514 and tile.z >= 3635 and tile.z <= 3646
