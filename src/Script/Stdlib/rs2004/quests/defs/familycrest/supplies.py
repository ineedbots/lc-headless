"""Ported from rs2b0t's src/bot/api/ai/quests/defs/familycrest/supplies.ts (MIT, see thirdparty/rs2b0t)."""

import math
from rs2004.catalogs.record import Record
from rs2004.game import skills
from rs2004.quests.defs.familycrest.areas import ANTIPOISON_IDS, DUEL_RING_IDS, FC_BANK, FC_ID, FC_ITEM, FC_SHOP, PICKAXES
from rs2004.quests.weapons import best_banked, best_held, pack_weapon, wielded_weapon
from rs2004.traversal import traversal

__all__ = ['FC_OFFICIAL_SKILLS', 'FC_FOODS', 'FOOD_WITHDRAW', 'RUNE_GP', 'MOULD_GP', 'RUBY_GP', 'ANTIPOISON_GP', 'CALEB_FISH', 'BLAST_RUNES', 'BLAST_MINIMUM', 'held', 'banked', 'worn', 'held_name', 'banked_name', 'held_antipoison', 'banked_antipoison', 'has_pickaxe', 'best_bank_pickaxe', 'has_weapon', 'best_bank_weapon', 'wield_weapon', 'TELEPORT_KIT', 'teleport_kit_top_up', 'teleport_kit_plan', 'held_food', 'scan_bank', 'withdraw', 'from_bank', 'buy', 'CREST_KEEP_IDS', 'deposit', 'coin_top_up', 'food_top_up', 'LEG_BANK', 'SHOP', 'warn_family_crest_readiness']

FC_OFFICIAL_SKILLS = Record({'mining': 40, 'crafting': 40, 'smithing': 40, 'magic': 59})
# Why: the hellhounds (lvl 122) at the perfect-gold rocks aggro at any reachable combat level, and Chronozon (lvl 170, att 173 / str 172) is in the wilderness where the not-too-strong check doesn't apply.
# Why: only max stats have cleared a headed run; lower this once a realistic profile does (docs/QUESTS.md polish goal).
FC_PROVEN_COMBAT_FLOOR = Record({'attack': 99, 'strength': 99, 'defence': 99, 'hitpoints': 99})
FC_FOODS = ['Shark', 'Lobster', 'Trout', 'Herring']
FOOD_WITHDRAW = 10
RUNE_BUY = Record({'air': 600, 'water': 200, 'earth': 200, 'fire': 250, 'death': 60})
# Why: a `buy` step withdraws this much when the pack is under it, so each estimate stays under the leg's coin float or every purchase walks back to a bank.
# Per-purchase coin estimates.
RUNE_GP = 25000
MOULD_GP = 1000
RUBY_GP = 12000
ANTIPOISON_GP = 2000
CALEB_FISH = [
    Record({'id': FC_ID.SWORDFISH, 'name': FC_ITEM.SWORDFISH}),
    Record({'id': FC_ID.BASS, 'name': FC_ITEM.BASS}),
    Record({'id': FC_ID.TUNA, 'name': FC_ITEM.TUNA}),
    Record({'id': FC_ID.SALMON, 'name': FC_ITEM.SALMON}),
    Record({'id': FC_ID.SHRIMP, 'name': FC_ITEM.SHRIMP}),
]
BLAST_RUNES = [
    Record({'item': Record({'id': FC_ID.AIR_RUNE, 'name': FC_ITEM.AIR_RUNE}), 'qty': RUNE_BUY.air}),
    Record({'item': Record({'id': FC_ID.WATER_RUNE, 'name': FC_ITEM.WATER_RUNE}), 'qty': RUNE_BUY.water}),
    Record({'item': Record({'id': FC_ID.EARTH_RUNE, 'name': FC_ITEM.EARTH_RUNE}), 'qty': RUNE_BUY.earth}),
    Record({'item': Record({'id': FC_ID.FIRE_RUNE, 'name': FC_ITEM.FIRE_RUNE}), 'qty': RUNE_BUY.fire}),
    Record({'item': Record({'id': FC_ID.DEATH_RUNE, 'name': FC_ITEM.DEATH_RUNE}), 'qty': RUNE_BUY.death}),
]
# Why: reference and test material only; as a provisioning threshold the teleport kit alone clears it and the fight runs dry after 6 Fire Blasts.
# One cast of every blast.
BLAST_MINIMUM = [
    Record({'item': Record({'id': FC_ID.AIR_RUNE, 'name': FC_ITEM.AIR_RUNE}), 'qty': 13}),
    Record({'item': Record({'id': FC_ID.WATER_RUNE, 'name': FC_ITEM.WATER_RUNE}), 'qty': 3}),
    Record({'item': Record({'id': FC_ID.EARTH_RUNE, 'name': FC_ITEM.EARTH_RUNE}), 'qty': 4}),
    Record({'item': Record({'id': FC_ID.FIRE_RUNE, 'name': FC_ITEM.FIRE_RUNE}), 'qty': 5}),
    Record({'item': Record({'id': FC_ID.DEATH_RUNE, 'name': FC_ITEM.DEATH_RUNE}), 'qty': 4}),
]


def held(snap, id):
    _v1 = (snap.inv_ids.get(id) if snap.inv_ids is not None else None)
    return (_v1 if _v1 is not None else 0)


def banked(snap, id):
    _v2 = (snap.bank_ids.get(id) if snap.bank_ids is not None else None)
    return (_v2 if _v2 is not None else 0)


def worn(snap, id):
    _v3 = ((id in snap.worn_ids) if snap.worn_ids is not None else None)
    return (_v3 if _v3 is not None else False)


def held_name(snap, name):
    _v4 = snap.inv.get(name.lower())
    return (_v4 if _v4 is not None else 0)


def banked_name(snap, name):
    _v5 = (snap.bank.get(name.lower()) if snap.bank is not None else None)
    return (_v5 if _v5 is not None else 0)


def held_antipoison(snap):
    return sum([held(snap, id) for id in ANTIPOISON_IDS])


def banked_antipoison(snap):
    for id in ANTIPOISON_IDS:
        if banked(snap, id) > 0:
            return Record({
                'id': id,
                'name': f'Antipoison({(4 if id == FC_ID.ANTIPOISON_4 else (3 if id == FC_ID.ANTIPOISON_3 else (2 if id == FC_ID.ANTIPOISON_2 else 1)))})',
            })
    return None


def has_pickaxe(snap):
    return any([held(snap, p.id) > 0 or worn(snap, p.id) for p in PICKAXES])


def best_bank_pickaxe(snap):
    _v6 = ([p for p in PICKAXES if banked(snap, p.id) > 0] or [None])[0]
    return (_v6 if _v6 is not None else None)


def has_weapon(snap):
    return best_held(snap) is not None


def best_bank_weapon(snap):
    return best_banked(snap)


# Why: `hasWeapon` is satisfied by a scimitar in the pack, hence the separate `worn` check; null covers both wielded and none anywhere, since Chronozon dies to the blasts and an unarmed fight is only slow.
def wield_weapon(snap, bank=None):
    """Equip a melee weapon when one is held or banked, or null."""
    if wielded_weapon(snap):
        return None
    in_pack = pack_weapon(snap)
    if in_pack:
        return Record({'kind': 'equip', 'item': in_pack.name})
    if not snap.bank_known:
        return scan_bank(bank)
    from_the_bank = best_bank_weapon(snap)
    return (from_bank(snap, from_the_bank, 1, bank) if from_the_bank else None)


# Why: air covers Camelot (5) and the strike half of the others, law is the limit at 1 or 2 a hop, and the quest takes about 10 hops; unused runes come home.
# Runes the standard-spellbook hops need, and how many to carry.
TELEPORT_KIT = [
    Record({'item': Record({'id': FC_ID.LAW_RUNE, 'name': FC_ITEM.LAW_RUNE}), 'qty': 30}),
    Record({'item': Record({'id': FC_ID.AIR_RUNE, 'name': FC_ITEM.AIR_RUNE}), 'qty': 150}),
    Record({'item': Record({'id': FC_ID.FIRE_RUNE, 'name': FC_ITEM.FIRE_RUNE}), 'qty': 30}),
    Record({'item': Record({'id': FC_ID.WATER_RUNE, 'name': FC_ITEM.WATER_RUNE}), 'qty': 30}),
]
AUBURY_STOCKS = set([FC_ID.AIR_RUNE, FC_ID.FIRE_RUNE, FC_ID.WATER_RUNE])


def nav_teleports_on():
    return traversal.teleports_enabled()


def held_duel_ring(snap):
    return sum([held(snap, id) for id in DUEL_RING_IDS])


# Why: A* only injects a teleport the live inventory can afford and nothing else here carries law, so this is what lets it plan a hop at all.
# Why: one bank trip: Camelot lands 71 tiles from Caleb against a 379-cost walk, and the duel ring 73 from the Al Kharid furnace against about 600 from Witchaven; no runes banked means walking.
def teleport_kit_top_up(snap, bank=None):
    """Carry the teleport kit when nav teleports are on and the bank can pay for it."""
    return (teleport_kit_plan(snap, bank) if nav_teleports_on() else None)


def teleport_kit_plan(snap, bank=None):
    """{@link teleportKitTopUp} without the settings read, so it is testable."""
    # Why: both halves are tested up front; keyed on law alone it stopped before the air, on runes alone before the ring.
    runes_short = any([held(snap, want.item.id) < math.ceil(want.qty / 3) for want in TELEPORT_KIT])
    ring_short = held_duel_ring(snap) == 0
    if not runes_short and not ring_short:
        return None
    if not snap.bank_known:
        return scan_bank(bank)
    # Why: law is Magic Guild and Mage Arena stock only, so a bank without it is normal and the spell hops stay off.
    if runes_short and banked(snap, TELEPORT_KIT[0].item.id) > 0:
        for want in TELEPORT_KIT:
            step = from_bank(snap, want.item, want.qty, bank)
            if step:
                return step
            # Why: Aubury stocks air, fire and water 20 tiles from the Varrock East booth, so only law has to come from the bank.
            if held(snap, want.item.id) < math.ceil(want.qty / 3) and (want.item.id in AUBURY_STOCKS):
                return Record({
                    'kind': 'buy',
                    'item': want.item.name,
                    'qty': want.qty,
                    'shop': FC_SHOP.AUBURY,
                    'est_gp': RUNE_GP,
                })
    # Independent of the runes: the ring reaches Al Kharid, which no spell on this book can (Ardougne teleport needs Plague City).
    if ring_short:
        ring = ([id for id in DUEL_RING_IDS if banked(snap, id) > 0] or [None])[0]
        if ring is not None:
            return withdraw([{'name': 'Ring of dueling', 'id': ring, 'qty': 1}], bank)
    return None


def best_bank_food(snap):
    _v7 = ([f for f in FC_FOODS if banked_name(snap, f) > 0] or [None])[0]
    return (_v7 if _v7 is not None else None)


def held_food(snap):
    return sum([held_name(snap, f) for f in FC_FOODS])


def scan_bank(bank=None):
    return Record({'kind': 'scan_bank', 'bank': bank})


def withdraw(items, bank=None):
    return Record({'kind': 'withdraw', 'items': items, 'bank': bank})


# Why: `null` covers both "already carried" and "the bank cannot help", and the caller decides whether that is a shop trip or a park.
def from_bank(snap, item, qty=1, bank=None):
    """Withdraw a shortfall when the bank has it."""
    short = qty - held(snap, item.id)
    if short <= 0:
        return None
    if not snap.bank_known:
        return scan_bank(bank)
    in_bank = banked(snap, item.id)
    return (withdraw([{'name': item.name, 'id': item.id, 'qty': min(short, in_bank)}], bank) if in_bank > 0 else None)


def buy(item, qty, shop, est_gp):
    return Record({'kind': 'buy', 'item': item.name, 'qty': qty, 'shop': shop, 'est_gp': est_gp})


CREST_KEEP_IDS = [FC_ID.CREST_FROM_CALEB, FC_ID.CREST_FROM_AVAN, FC_ID.CREST_FROM_CHRONOZON, FC_ID.FAMILY_CREST]


def deposit(keep, bank=None):
    return Record({'kind': 'deposit', 'keep': keep, 'keep_ids': CREST_KEEP_IDS, 'bank': bank})


COIN_CARRY = 100000


def coin_top_up(snap, want=None, bank=None):
    if want is None:
        want = COIN_CARRY
    have = held_name(snap, FC_ITEM.COINS)
    if have >= want / 2:
        return None
    if not snap.bank_known:
        return scan_bank(bank)
    in_bank = banked_name(snap, FC_ITEM.COINS)
    if in_bank <= 0:
        return None
    return withdraw([{'name': FC_ITEM.COINS, 'id': FC_ID.COINS, 'qty': min(want - have, in_bank)}], bank)


def food_top_up(snap, want=None, bank=None):
    if want is None:
        want = FOOD_WITHDRAW
    if held_food(snap) >= math.ceil(want / 2):
        return None
    if not snap.bank_known:
        return scan_bank(bank)
    food = best_bank_food(snap)
    if not food:
        return None
    take = min(want - held_food(snap), banked_name(snap, food))
    return (withdraw([{'name': food, 'qty': take}], bank) if take > 0 else None)


LEG_BANK = Record({
    'start': FC_BANK.VARROCK_EAST,
    'caleb': FC_BANK.CATHERBY,
    'alkharid': FC_BANK.AL_KHARID,
    'gold': FC_BANK.AL_KHARID,
    'mine': FC_BANK.ARDOUGNE_EAST,
    'boot': FC_BANK.FALADOR_EAST,
    'chronozon': FC_BANK.VARROCK_EAST,
})
SHOP = FC_SHOP


def warn_family_crest_readiness():
    have = {
        'mining': skills.level('mining'),
        'crafting': skills.level('crafting'),
        'smithing': skills.level('smithing'),
        'magic': skills.level('magic'),
        'attack': skills.level('attack'),
        'strength': skills.level('strength'),
        'defence': skills.level('defence'),
        'hitpoints': skills.level('hitpoints'),
    }
    missing = []
    for skill in FC_OFFICIAL_SKILLS.keys():
        need = FC_OFFICIAL_SKILLS.get(skill)
        n = have[skill]
        if n < need:
            missing.append(f'{skill} {n}/{need}')
    if len(missing) > 0:
        return f"official skill reqs not met ({', '.join(missing)}) — Fire Blast and the perfect-gold jewellery will both refuse"
    floor = FC_PROVEN_COMBAT_FLOOR
    short = [f'{s} {have[s]}/{floor.get(s)}' for s in ['attack', 'strength', 'defence', 'hitpoints'] if have[s] < floor.get(s)]
    if len(short) == 0:
        return None
    return f"combat below the only proven profile ({', '.join(short)}; headed PASS at max). " + 'Hellhounds guard the gold rocks and Chronozon is a lvl-170 wilderness demon — expect death risk.'
