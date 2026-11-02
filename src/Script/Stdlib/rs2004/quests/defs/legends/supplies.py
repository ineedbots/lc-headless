"""Ported from rs2b0t's src/bot/api/ai/quests/defs/legends/supplies.ts (MIT, see thirdparty/rs2b0t)."""

import math
from rs2004.catalogs.record import Record
from rs2004.game import skills
from rs2004.quests.armour import QUEST_ARMOUR, armour_choice, armour_held, armour_worn
from rs2004.quests.defs.legends.areas import GEM_CUTS, GEM_ROCKS, LQ_BANK, LQ_ID, LQ_ITEM, LQ_SHOP, LQ_SKILLS, LQ_TILE
from rs2004.quests.defs.legends.gather import mine_gem, smelt_gold_bar
from rs2004.quests.weapons import MELEE_WEAPONS, best_banked, pack_weapon, wielded_weapon

__all__ = ['LQ_FOODS', 'FOOD_CARRY', 'COIN_CARRY', 'COIN_FLOOR', 'SHOP_GP', 'PRAYER_POTIONS', 'ARMOUR', 'PICKAXES', 'held', 'banked', 'worn', 'owned', 'held_name', 'banked_name', 'scan_bank', 'withdraw', 'KEEP_IDS', 'FOOD_FOR_SLOT', 'junk_ids', 'junk_held', 'ditch_ids', 'deposit', 'from_bank', 'source', 'bank_only', 'coin_top_up', 'held_food', 'food_top_up', 'pots_held', 'pots_banked', 'potion_top_up', 'dress_for_combat', 'has_pickaxe', 'source_pickaxe', 'JIMINUA_KIT', 'RUNE_KIT', 'ORB_RUNE_KIT', 'BANK_ONLY_KIT', 'DESCENT_KIT', 'source_from', 'source_bank_only', 'source_gems', 'source_gold_bars', 'provision', 'warn_legends_readiness', 'LQ_PROVEN_COMBAT_FLOOR', 'LEG_BANK']

# Why: best first, since `foodTopUp` takes the first of these the bank holds and the float has to outlast Nezikchened 3 times and 3 aggressive guardians. The rest are fallbacks in descending heal.
LQ_FOODS = ['Shark', 'Swordfish', 'Lobster', 'Tuna']
FOOD_CARRY = 14
# Why: Buy steps fund themselves; this smaller balance covers route fares while limiting coins lost during the demon fights.
COIN_CARRY = 5000
# Why: Fares cost 30 or 100 coins, so refill only near empty rather than at half the target balance.
COIN_FLOOR = 1000
# Why: `calc_shop_value` returns `oc_cost` unchanged while a shop sits at base stock (the Magic Guild's multipliers are sell 1000 / delta 10, which cancel) and climbs only as the shelf empties.
# Why: so the guild list is 2 soul runes at 1250, 4 law at 40, 2 mind at 3, 2 earth at 4 and 150 water at 4, about 3.8k with the water's depletion in it, and nearer 5k than 60k even bought down to the last soul rune. `estGp` is what the buy step tops the pack up to.
SHOP_GP = Record({'JIMINUA': 3000, 'MAGIC_GUILD': 12000})
PRAYER_POTIONS = [
    Record({'id': 2434, 'name': 'Prayer potion(4)'}),
    Record({'id': 139, 'name': 'Prayer potion(3)'}),
    Record({'id': 141, 'name': 'Prayer potion(2)'}),
    Record({'id': 143, 'name': 'Prayer potion(1)'}),
]
# Why: rune chainbody, since the platebody wants Dragon Slayer as well as Defence 40 and the refusal is a bare false with no message.
ARMOUR = [
    Record({'id': 1113, 'name': 'Rune chainbody'}),
    Record({'id': 1079, 'name': 'Rune platelegs'}),
    Record({'id': 1163, 'name': 'Rune full helm'}),
    Record({'id': 1201, 'name': 'Rune kiteshield'}),
    Record({'id': 1704, 'name': 'Amulet of glory'}),
]
PICKAXES = [
    Record({'id': LQ_ID.RUNE_PICKAXE, 'name': 'Rune pickaxe'}),
    Record({'id': LQ_ID.ADAMANT_PICKAXE, 'name': 'Adamant pickaxe'}),
    Record({'id': LQ_ID.MITHRIL_PICKAXE, 'name': 'Mithril pickaxe'}),
    Record({'id': LQ_ID.STEEL_PICKAXE, 'name': 'Steel pickaxe'}),
    Record({'id': LQ_ID.IRON_PICKAXE, 'name': 'Iron pickaxe'}),
    Record({'id': LQ_ID.BRONZE_PICKAXE, 'name': 'Bronze pickaxe'}),
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


def owned(snap, id):
    return held(snap, id) + ((1 if worn(snap, id) else 0))


def held_name(snap, name):
    _v4 = snap.inv.get(name.lower())
    return (_v4 if _v4 is not None else 0)


def banked_name(snap, name):
    _v5 = (snap.bank.get(name.lower()) if snap.bank is not None else None)
    return (_v5 if _v5 is not None else 0)


def scan_bank(bank=None):
    return Record({'kind': 'scan_bank', 'bank': bank})


def withdraw(items, bank=None):
    return Record({'kind': 'withdraw', 'items': items, 'bank': bank})


# Why: every quest item this list forgets is deposited on the next bank trip and has to be re-earned, so it's a deny list.
KEEP_IDS = [LQ_ID.MAP, LQ_ID.MAP_COMPLETE, LQ_ID.BULLROARER, LQ_ID.GOLD_BOWL_SKETCH, LQ_ID.GOLD_BOWL, LQ_ID.GOLD_BOWL_BLESSED, LQ_ID.GOLD_BOWL_WATER, LQ_ID.GOLD_BOWL_PURE, LQ_ID.GOLD_BOWL_BLESSED_WATER, LQ_ID.GOLD_BOWL_BLESSED_PURE, LQ_ID.HOLLOW_REED, LQ_ID.BOOK_OF_BINDING, LQ_ID.YOMMI_SEEDS, LQ_ID.YOMMI_SEEDS_GERM, LQ_ID.SNAKEWEED_MIXTURE, LQ_ID.ARDRIGAL_MIXTURE, LQ_ID.BRAVERY_POTION, LQ_ID.SNAKE_WEED, LQ_ID.ARDRIGAL, LQ_ID.UNID_SNAKE_WEED, LQ_ID.UNID_ARDRIGAL, LQ_ID.CRYSTAL_CHUNK, LQ_ID.CRYSTAL_HUNK, LQ_ID.CRYSTAL_LUMP, LQ_ID.HEART_CRYSTAL, LQ_ID.HEART_CRYSTAL_GLOW, LQ_ID.DEATH_DAGGER, LQ_ID.DEATH_DAGGER_DONE, LQ_ID.HOLY_FORCE, LQ_ID.TOTEM_POLE, LQ_ID.GILDED_TOTEM, LQ_ID.MACHETE, LQ_ID.RUNE_AXE, LQ_ID.LOCKPICK, LQ_ID.UNPOWERED_ORB, LQ_ID.PAPYRUS, LQ_ID.CHARCOAL, LQ_ID.GOLD_BAR, LQ_ID.HAMMER, LQ_ID.KNIFE, LQ_ID.ROPE, LQ_ID.CHISEL, LQ_ID.VIAL_WATER, LQ_ID.SOUL_RUNE, LQ_ID.MIND_RUNE, LQ_ID.EARTH_RUNE, LQ_ID.LAW_RUNE, LQ_ID.WATER_RUNE, LQ_ID.COSMIC_RUNE, LQ_ID.AIR_RUNE, LQ_ID.FIRE_RUNE, LQ_ID.DEATH_RUNE] + list([g.id for g in GEM_ROCKS]) + list([g.uncut for g in GEM_CUTS]) + list([p.id for p in PICKAXES]) + list([w.id for w in MELEE_WEAPONS]) + list([a.id for a in ARMOUR]) + list([a.id for a in QUEST_ARMOUR]) + list([p.id for p in PRAYER_POTIONS]) + [LQ_ID.COINS]
# Why: Trials return three rock items, so calculate withdrawals from available slots.
FOOD_IDS = [LQ_ID.SHARK, LQ_ID.SWORDFISH, LQ_ID.LOBSTER, LQ_ID.TUNA]
# Why: a slot is bought with the worst food held, the opposite order to the float, to keep the heal that has to outlast the demon.
FOOD_FOR_SLOT = [
    Record({'id': LQ_ID.TUNA, 'name': LQ_ITEM.TUNA}),
    Record({'id': LQ_ID.LOBSTER, 'name': LQ_ITEM.LOBSTER}),
    Record({'id': LQ_ID.SWORDFISH, 'name': LQ_ITEM.SWORDFISH}),
    Record({'id': LQ_ID.SHARK, 'name': LQ_ITEM.SHARK}),
]


def junk_ids(snap):
    """Everything in the pack this quest has no use for, random-event gifts included."""
    return [id for id in list(list(((snap.inv_ids if snap.inv_ids is not None else {})).keys())) if not (id in KEEP_IDS) and not (id in FOOD_IDS)]


def junk_held(snap):
    """Something in the pack a deposit would take."""
    return len(junk_ids(snap)) > 0


# Why: Gem rocks produce many spare opals before a diamond; drop surplus uncut gems once their cut form is held.
def ditch_ids(snap):
    """Everything the drop may shed where you stand, spare uncut gems included."""
    spare = [gem.uncut for gem in [gem for gem in GEM_CUTS if held(snap, gem.uncut) > 0 and owned(snap, gem.cut) > 0]]
    return list(junk_ids(snap)) + list(spare)


def deposit(bank=None):
    return Record({'kind': 'deposit', 'keep': list(LQ_FOODS), 'keep_ids': KEEP_IDS, 'bank': bank})


# `null` means either the item is already owned or the bank cannot provide it; callers choose the next source.
# Why: Bank contents are global, so withdrawals use the nearest booth; the supplied bank remains only for shop funding.
def from_bank(snap, item, qty=1):
    """Withdraw a shortfall when the bank has it."""
    short = qty - owned(snap, item.id)
    if short <= 0:
        return None
    if not snap.bank_known:
        return scan_bank()
    in_bank = banked(snap, item.id)
    return (withdraw([{'name': item.name, 'id': item.id, 'qty': min(short, in_bank)}]) if in_bank > 0 else None)


# Why: `stock` is what the counter is asked for and `qty` what the leg needs: the magic gate eats a cast every descent and the Magic Guild is in Yanille, and runes stack, so a run's worth costs the same slot as one.
def source(snap, item, qty, shop, est_gp, bank=None, stock=None):
    """Bank first, then the counter that stocks it."""
    if stock is None:
        stock = qty
    have = owned(snap, item.id)
    if have >= qty:
        return None
    _v6 = from_bank(snap, item, qty)
    return (_v6 if _v6 is not None else Record({
        'kind': 'buy',
        'item': item.name,
        'qty': max(stock, qty) - have,
        'shop': shop,
        'est_gp': est_gp,
        'bank': bank,
    }))


def bank_only(snap, item, qty):
    """Bank only, nothing in the game sells this."""
    if owned(snap, item.id) >= qty:
        return None
    _v7 = from_bank(snap, item, qty)
    return (_v7 if _v7 is not None else Record({'kind': 'wait', 'reason': f'no {item.name} in the pack or the bank, and no shop stocks one'}))


def coin_top_up(snap, want=None, bank=None):
    if want is None:
        want = COIN_CARRY
    have = held_name(snap, LQ_ITEM.COINS)
    if have >= min(COIN_FLOOR, want):
        return None
    if not snap.bank_known:
        return scan_bank(bank)
    in_bank = banked_name(snap, LQ_ITEM.COINS)
    return (withdraw([{'name': LQ_ITEM.COINS, 'id': LQ_ID.COINS, 'qty': min(want - have, in_bank)}], bank) if in_bank > 0 else None)


def held_food(snap):
    return sum([held_name(snap, f) for f in LQ_FOODS])


def food_top_up(snap, want=None, bank=None):
    if want is None:
        want = FOOD_CARRY
    if held_food(snap) >= math.ceil(want / 2):
        return None
    if not snap.bank_known:
        return scan_bank(bank)
    food = ([f for f in LQ_FOODS if banked_name(snap, f) > 0] or [None])[0]
    if not food:
        return None
    # Why: Cap the withdrawal to free slots so the planner does not request the same overflow again.
    room = max(0, (snap.free_slots if snap.free_slots is not None else 28))
    take = min(want - held_food(snap), banked_name(snap, food), room)
    return (withdraw([{'name': food, 'qty': take}], bank) if take > 0 else None)


# Why: Prayer doses must last through the level-187 Nezikchened fight.
def pots_held(snap):
    """Prayer doses in the pack."""
    return sum([held(snap, pot.id) for pot in PRAYER_POTIONS])


def pots_banked(snap):
    """Prayer doses the bank could still hand over."""
    return sum([banked(snap, pot.id) for pot in PRAYER_POTIONS])


def potion_top_up(snap, want, bank=None):
    if want <= 0:
        return None
    have = sum([held(snap, pot.id) for pot in PRAYER_POTIONS])
    if have >= want:
        return None
    if not snap.bank_known:
        return scan_bank(bank)
    pot = ([p for p in PRAYER_POTIONS if banked(snap, p.id) > 0] or [None])[0]
    if not pot:
        return None
    return withdraw([{'name': pot.name, 'id': pot.id, 'qty': min(want - have, banked(snap, pot.id))}], bank)


def dress_for_combat(snap, bank=None):
    """Equip the best melee weapon and armour the bank can dress us in, or null."""
    # Why: the weapon is whatever tier the Attack level reaches and the account owns, so it's resolved at runtime.
    if not wielded_weapon(snap):
        in_pack = pack_weapon(snap)
        if in_pack:
            return Record({'kind': 'equip', 'item': in_pack.name})
        if not snap.bank_known:
            return scan_bank(bank)
        from_the_bank = best_banked(snap)
        if from_the_bank:
            return withdraw([{'name': from_the_bank.name, 'id': from_the_bank.id, 'qty': 1}], bank)
    for slot in ['torso', 'legs', 'hat', 'lefthand']:
        piece = armour_choice(snap, slot)
        if piece and armour_worn(snap, piece):
            continue
        if piece and armour_held(snap, piece):
            return Record({'kind': 'equip', 'item': piece.name})
        if not snap.bank_known:
            return scan_bank(bank)
        if piece:
            return withdraw([{'name': piece.name, 'id': piece.id, 'qty': 1}], bank)
        # Why: a death keeps the 3 dearest things and the bank was seeded with one kit, so a lost helm or shield parked a run nothing on its route sells one to. Only the body is worth stopping for.
        if slot == 'torso':
            return Record({'kind': 'wait', 'reason': f'no usable {slot} armour in the pack or bank'})
    if armour_choice(snap, 'front'):
        return None
    glory = Record({'id': 1704, 'name': 'Amulet of glory'})
    if held(snap, glory.id) > 0:
        return Record({'kind': 'equip', 'item': glory.name})
    if snap.bank_known and banked(snap, glory.id) > 0:
        return withdraw([{'name': glory.name, 'id': glory.id, 'qty': 1}], bank)
    return None


def has_pickaxe(snap):
    return any([owned(snap, p.id) > 0 for p in PICKAXES])


def source_pickaxe(snap, bank=None):
    """Bank first, then Obli's bronze pickaxe, mining 52 is met by anything."""
    if has_pickaxe(snap):
        return None
    if not snap.bank_known:
        return scan_bank(bank)
    in_bank = ([p for p in PICKAXES if banked(snap, p.id) > 0] or [None])[0]
    if in_bank:
        return withdraw([{'name': in_bank.name, 'id': in_bank.id, 'qty': 1}], bank)
    return Record({
        'kind': 'buy',
        'item': 'Bronze pickaxe',
        'qty': 1,
        'shop': LQ_SHOP.JIMINUA,
        'est_gp': SHOP_GP.JIMINUA,
        'bank': bank,
    })


# Why: no machete on this list. Radimus keeps a free one in the cupboard and counts the bank when deciding whether to hand it over, so provisioning one breaks the step that would get it for nothing.
JIMINUA_KIT = [
    Record({'item': Record({'id': LQ_ID.PAPYRUS, 'name': LQ_ITEM.PAPYRUS}), 'qty': 8}),
    Record({'item': Record({'id': LQ_ID.CHARCOAL, 'name': LQ_ITEM.CHARCOAL}), 'qty': 8}),
    Record({'item': Record({'id': LQ_ID.KNIFE, 'name': LQ_ITEM.KNIFE}), 'qty': 1}),
    Record({'item': Record({'id': LQ_ID.ROPE, 'name': LQ_ITEM.ROPE}), 'qty': 1}),
    Record({'item': Record({'id': LQ_ID.HAMMER, 'name': LQ_ITEM.HAMMER}), 'qty': 1}),
    Record({'item': Record({'id': LQ_ID.CHISEL, 'name': LQ_ITEM.CHISEL}), 'qty': 1}),
    Record({'item': Record({'id': LQ_ID.VIAL_WATER, 'name': LQ_ITEM.VIAL_WATER}), 'qty': 1}),
]
# Why: the wall keeps its 5 in `%legends_bits`, so they're spent once, but a death on the way down drops them and the replacement is another trip to Yanille for the only soul rune in the game. A spare set stacks into the same slots.
RUNE_KIT = [
    Record({'item': Record({'id': LQ_ID.SOUL_RUNE, 'name': LQ_ITEM.SOUL_RUNE}), 'qty': 1, 'stock': 2}),
    Record({'item': Record({'id': LQ_ID.MIND_RUNE, 'name': LQ_ITEM.MIND_RUNE}), 'qty': 1, 'stock': 2}),
    Record({'item': Record({'id': LQ_ID.EARTH_RUNE, 'name': LQ_ITEM.EARTH_RUNE}), 'qty': 1, 'stock': 2}),
    Record({'item': Record({'id': LQ_ID.LAW_RUNE, 'name': LQ_ITEM.LAW_RUNE}), 'qty': 2, 'stock': 4}),
]
# Why: the magic gate eats an orb and a cast every downward crossing, while everything else in the trials is spent once, so the 2 kits are asked for separately.
# Why: the Magic Guild counter is in Yanille, the ship, the walk and the bank from Karamja, so the descent's cast is bought a run's worth at a time; a rune stack is one slot whatever the count.
DESCENTS_STOCKED = 5
ORB_RUNE_KIT = [Record({
    'item': Record({'id': LQ_ID.WATER_RUNE, 'name': LQ_ITEM.WATER_RUNE}),
    'qty': 30,
    'stock': 30 * DESCENTS_STOCKED,
})]
BANK_ONLY_KIT = [Record({'item': Record({'id': LQ_ID.RUNE_AXE, 'name': LQ_ITEM.RUNE_AXE}), 'qty': 1})]
# Why: the outer gate shuts behind whoever picked it and the 3 boulders drop back behind whoever mined them, so every descent is paid for in full.
# Why: the Magic Guild counter stocks fire, water, air, earth, mind, body, soul, nature, chaos, blood, law and death and no cosmic, and the only shop that sells one is the Mage Arena's, deep Wilderness and behind a setting, so the cosmic runes are bank-only. Asked for at a counter that can't sell it, the leg buys nothing and says nothing.
DESCENT_KIT = [
    Record({'item': Record({'id': LQ_ID.LOCKPICK, 'name': LQ_ITEM.LOCKPICK}), 'qty': 1}),
    Record({'item': Record({'id': LQ_ID.UNPOWERED_ORB, 'name': LQ_ITEM.UNPOWERED_ORB}), 'qty': 1}),
    Record({'item': Record({'id': LQ_ID.COSMIC_RUNE, 'name': LQ_ITEM.COSMIC_RUNE}), 'qty': 3}),
]


def source_from(snap, kit, shop, est_gp, bank=None):
    for want in kit:
        step = source(snap, want.item, want.qty, shop, est_gp, bank, want.stock)
        if step:
            return step
    return None


def source_bank_only(snap, kit):
    for want in kit:
        step = bank_only(snap, want.item, want.qty)
        if step:
            return step
    return None


# Why: only the Falador and Al Kharid gem counters sell a cut gem at all, they hold one apiece, and neither ever stocks opal, jade or red topaz.
# Why: the only rocks that drop all 7 are north of Shilo Village, reached by Hajedy's cart out of Brimhaven, so the chain is mine-then-cut with the bank in front.
def source_gems(snap, bank=None):
    """The next rung of the 7-gem chain, or null once all 7 are carried."""
    missing = [gem for gem in GEM_ROCKS if owned(snap, gem.id) == 0]
    if len(missing) == 0:
        return None
    if not snap.bank_known:
        return scan_bank(bank)
    from_the_bank = ([gem for gem in missing if banked(snap, gem.id) > 0] or [None])[0]
    if from_the_bank:
        return withdraw([{'name': from_the_bank.name, 'id': from_the_bank.id, 'qty': 1}], bank)
    cut = ([gem for gem in GEM_CUTS if owned(snap, gem.cut) == 0 and (held(snap, gem.uncut) > 0 or banked(snap, gem.uncut) > 0)] or [None])[0]
    if cut:
        rough = from_bank(snap, Record({'id': cut.uncut, 'name': cut.uncut_name}), 1)
        if rough:
            return rough
        chisel = source(snap, Record({'id': LQ_ID.CHISEL, 'name': LQ_ITEM.CHISEL}), 1, LQ_SHOP.JIMINUA, SHOP_GP.JIMINUA, bank)
        if chisel:
            return chisel
        return Record({
            'kind': 'use_on',
            'item': LQ_ITEM.CHISEL,
            'target_kind': 'item',
            'target': cut.uncut_name,
            'anchor': (bank if bank is not None else LQ_BANK.ARDOUGNE),
            'product': cut.name,
        })
    pickaxe = source_pickaxe(snap, bank)
    if pickaxe:
        return pickaxe
    return Record({'kind': 'custom', 'name': f'mine a gem ({len(missing)} of seven still missing)', 'run': mine_gem})


# Why: Drogo's is the only gold-bar counter and its baseline stock is 0, so the chain is mine at Brimhaven and smelt at the Shilo furnace next to the booth.
def source_gold_bars(snap, bank=None):
    """The next rung of the 2-gold-bar chain, or null once both are carried."""
    bars = Record({'id': LQ_ID.GOLD_BAR, 'name': LQ_ITEM.GOLD_BAR})
    if owned(snap, bars.id) >= 2:
        return None
    from_the_bank = from_bank(snap, bars, 2)
    if from_the_bank:
        return from_the_bank
    if held_name(snap, 'Gold ore') > 0:
        return Record({'kind': 'custom', 'name': 'smelt a gold bar at the Ardougne furnace', 'run': smelt_gold_bar})
    pickaxe = source_pickaxe(snap, bank)
    if pickaxe:
        return pickaxe
    return Record({'kind': 'mine_rock', 'rock': 'Gold', 'item': 'Gold ore', 'qty': 1, 'anchor': LQ_TILE.GOLD_ROCKS})


# Why: every counter this quest uses is a sea crossing from the next thing it needs, Jiminua's on Karamja and the Magic Guild upstairs in Yanille, so buy once, bank once, and every later leg is a withdraw.
# Why: the check is against `qty` and the purchase against `stock`, the same split `source` makes, so a pack holding a descent's worth isn't sent shopping for 4 more.
COUNTERS = [
    Record({
    'shop': LQ_SHOP.MAGIC_GUILD,
    'est_gp': SHOP_GP.MAGIC_GUILD,
    'bank': LQ_BANK.YANILLE,
    'kit': list(RUNE_KIT) + list(ORB_RUNE_KIT),
}),
    Record({'shop': LQ_SHOP.JIMINUA, 'est_gp': SHOP_GP.JIMINUA, 'bank': LQ_BANK.SHILO, 'kit': JIMINUA_KIT}),
]
# Why: a shared counter with `allstock=no` can be bought out, and a shopping list that parks on one empty shelf blocks a run the per-leg sourcing could still finish. The give-up is the engine's own no-progress count.
PROVISION_GIVE_UP = 3


def provision_deposit(bank):
    """Coins and food ride along; everything a counter sold goes into the bank."""
    return Record({'kind': 'deposit', 'keep': list(LQ_FOODS), 'keep_ids': [LQ_ID.COINS], 'bank': bank})


def provision(snap):
    """Stock the bank from every counter before the quest touches the field, or null once it is stocked."""
    if snap.no_progress >= PROVISION_GIVE_UP:
        return None
    for counter in COUNTERS:
        short = ([want for want in counter.kit if owned(snap, want.item.id) + banked(snap, want.item.id) < want.qty] or [None])[0]
        if short:
            if not snap.bank_known:
                return scan_bank(counter.bank)
            have = owned(snap, short.item.id) + banked(snap, short.item.id)
            target = max((short.stock if short.stock is not None else short.qty), short.qty)
            return Record({
                'kind': 'buy',
                'item': short.item.name,
                'qty': target - have,
                'shop': counter.shop,
                'est_gp': counter.est_gp,
                'bank': counter.bank,
            })
        # Why: banked at this counter's own booth, as the 2 lists together are more slots than the pack has.
        if any([held(snap, want.item.id) > 0 for want in counter.kit]):
            return provision_deposit(counter.bank)
    return None


def warn_legends_readiness():
    missing = [f'{skill} {skills.level(skill)}/{getattr(LQ_SKILLS, skill)}' for skill in LQ_SKILLS.keys() if skills.level(skill) < getattr(LQ_SKILLS, skill)]
    if len(missing) > 0:
        return f"official skill reqs not met ({', '.join(missing)}), the trials and the Yommi tree both refuse below them"
    combat = [f'{skill} {skills.level(skill)}/{LQ_PROVEN_COMBAT_FLOOR}' for skill in ['attack', 'strength', 'defence', 'hitpoints', 'prayer'] if skills.level(skill) < LQ_PROVEN_COMBAT_FLOOR]
    if len(combat) == 0:
        return None
    return f"combat below the only proven profile ({', '.join(combat)}; rs2b0t's run was at 70s). " + 'Nezikchened is a level-187 demon fought three times and the three Viyeldi guardians follow him, expect death risk.'


LQ_PROVEN_COMBAT_FLOOR = 70
# Why: Shilo Village banks Karamja; Ardougne West is the Brimhaven ship and a walk each way, and the gold, the gems, Jiminua's counter and the jungle are all on this side of that crossing.
LEG_BANK = Record({'guild': LQ_BANK.ARDOUGNE, 'karamja': LQ_BANK.SHILO, 'runes': LQ_BANK.YANILLE})
