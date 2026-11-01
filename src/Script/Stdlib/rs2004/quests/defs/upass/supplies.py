"""Ported from rs2b0t's src/bot/api/ai/quests/defs/upass/supplies.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs._items import ITEM_DB
from rs2004.catalogs.loadout import gear_of, weapon_of
from rs2004.catalogs.record import Record
from rs2004.geometry import Tile
from rs2004.items import equipment
from rs2004.quests.defs.upass.areas import UP_ITEM, UP_TILE, banked, carried, held
from rs2004.quests.food import FOOD_FLOAT
from rs2004.quests.gear import quest_loadout

__all__ = ['ARROW_TARGET', 'FOOD_TARGET', 'BOW_IDS', 'bow_worn', 'bow_carried', 'scan_bank', 'withdraw', 'from_bank', 'KIT', 'KEEP_IDS', 'source_kit', 'kit_shortfall', 'needs_equip', 'planned_gear', 'wear_gear', 'melee_armed', 'melee_carried', 'draw_gear']

ARROW_TARGET = 50
# Why: the grid crossing and the orb corridor alone cost 8 lobsters, and the traps below are timer damage you walk into. Koftik, the paladins and Nilhoof give a dozen food between them, but as separate stacks that each take a slot, so the float covers the trapped stretches.
FOOD_TARGET = FOOD_FLOAT
# Why: upass_bridge.rs2 gates the rope shot on oc_category = weapon_bow, which is 13 items. A crossbow is weapon_crossbow, fires bolts and must not qualify.
def _is_bow(obj):
    """rs2b0t's /^(?:[a-z]+_)?(?:short|long)bow$|^ogre_bow$/."""
    if obj == 'ogre_bow':
        return True
    parts = obj.split('_')
    return len(parts) <= 2 and parts[-1] in ('shortbow', 'longbow')


BOW_IDS = set([row['id'] for row in ITEM_DB if _is_bow(row['obj'])])
NAME_BY_ID = {row['id']: row['name'] for row in ITEM_DB}


def first_bow(ids):
    if ids is None:
        return None
    for id, n in ids.items():
        if n > 0 and (id in BOW_IDS):
            return id
    return None


def bow_worn(snap):
    """True once a bow is in the right hand, which is what `upass_bridge` reads."""
    for id in (snap.worn_ids if snap.worn_ids is not None else []):
        if (id in BOW_IDS):
            return True
    return False


def bow_carried(snap):
    """True once a bow is worn or carried, which is what the cave mouth waits for."""
    return bow_worn(snap) or first_bow(snap.inv_ids) is not None


# Why: Aemad's counter is 40 tiles from the booth this quest banks at, and Lowe is the only bow counter with a walked stand. Nothing else in the kit has a shop worth the trip.
AEMAD = Record({'npc': 'Aemad', 'anchor': UP_TILE.AEMAD})
LOWE = Record({'npc': 'Lowe', 'anchor': UP_TILE.LOWE})
ROPE_GP = 40
BOW_GP = 100
BOW_TO_BUY = UP_ITEM.SHORTBOW


def scan_bank():
    return Record({'kind': 'scan_bank', 'bank': UP_TILE.ARDOUGNE_BANK})


def withdraw(items):
    return Record({'kind': 'withdraw', 'items': items, 'bank': UP_TILE.ARDOUGNE_BANK})


def from_bank(snap, item, qty):
    """Draw `qty` of `item` from the bank, or null when the pack already holds enough."""
    have = carried(snap, item)
    if have >= qty:
        return None
    if not snap.bank_known:
        return scan_bank()
    stock = banked(snap, item)
    if stock <= 0:
        return None
    return withdraw([{'name': item.name, 'id': item.id, 'qty': min(qty - have, stock)}])


# Why: the pass has no bank or shop and every trip back out is the dungeon over again, so the kit is drawn in one go before the cave mouth.
KIT = [
    Record({
    'item': UP_ITEM.ROPE,
    'qty': 3,
    'reason': 'the rock swing east, which eats one per attempt',
    'shop': AEMAD,
    'unit_gp': ROPE_GP,
}),
    Record({'item': UP_ITEM.BRONZE_ARROW, 'qty': ARROW_TARGET, 'reason': 'the fire arrow'}),
    Record({'item': UP_ITEM.TINDERBOX, 'qty': 1, 'reason': 'lighting the cloth arrow and burning the tomb'}),
    Record({'item': UP_ITEM.SPADE, 'qty': 1, 'reason': 'the filled-in tunnel out of the slave cages'}),
    Record({'item': UP_ITEM.BUCKET, 'qty': 1, 'reason': "the dwarf brew for Iban's tomb"}),
    Record({'item': UP_ITEM.LOBSTER, 'qty': FOOD_TARGET, 'reason': 'the demons, Kalrag and the trap falls'}),
]
KEEP_IDS = [UP_ITEM.get(key).id for key in UP_ITEM.keys()] + list(BOW_IDS)


# Why: the buy step tops the purse up itself, so a buy emitted with no coins walks to a counter it can't pay and retries there; falling through reaches the shortfall stop.
def can_afford(snap, gp):
    """True when pack and bank between them cover the asking price."""
    return held(snap, UP_ITEM.COINS) + banked(snap, UP_ITEM.COINS) >= gp


def buy_at(snap, item, qty, shop, unit_gp):
    """Buy the shortfall. Null when nothing is missing, or when there are no coins to pay with."""
    missing = qty - carried(snap, item)
    gp = missing * unit_gp
    if missing <= 0 or not can_afford(snap, gp):
        return None
    return Record({
        'kind': 'buy',
        'item': item.name,
        'qty': missing,
        'shop': shop,
        'est_gp': gp,
        'bank': UP_TILE.ARDOUGNE_BANK,
    })


def source_bow(snap):
    """Withdraw whichever bow the bank holds, else buy one. Null once a bow is worn or carried."""
    if bow_carried(snap):
        return None
    if not snap.bank_known:
        return scan_bank()
    stocked = first_bow(snap.bank_ids)
    if stocked is not None:
        _v1 = NAME_BY_ID.get(stocked)
        return withdraw([{'name': (_v1 if _v1 is not None else BOW_TO_BUY.name), 'id': stocked, 'qty': 1}])
    return buy_at(snap, BOW_TO_BUY, 1, LOWE, BOW_GP)


def source_kit(snap):
    """The next missing piece of kit, or null once the pack is ready to go underground."""
    for _item2 in KIT:
        item = _item2.item
        qty = _item2.qty
        shop = _item2.shop
        unit_gp = _item2.unit_gp
        step = from_bank(snap, item, qty)
        if step:
            return step
        if shop and unit_gp is not None:
            bought = buy_at(snap, item, qty, shop, unit_gp)
            if bought:
                return bought
    return source_bow(snap)


def kit_shortfall(snap):
    """What the kit is still short of, for the stop message."""
    short = [f'{row.qty}x {row.item.name} ({row.reason}), have {carried(snap, row.item)}' for row in KIT if carried(snap, row.item) < row.qty]
    if not bow_carried(snap):
        short.append('a bow (firing the bridge stay rope), have none')
    return short


def needs_equip(snap, item):
    return held(snap, item) > 0


# Why: the pass is fought through: 3 paladins at level 62 for their crests, 3 demons for their amulets and Kalrag for the blood. The bow is for one arrow at a rope, so descending in what the fire arrow left on is descending unarmed.
TIERS = ['dragon', 'rune', 'adamant', 'mithril', 'black', 'steel', 'iron', 'bronze']
# Why: "Dragon dagger(p)" ends in the poison suffix, so an endsWith test on the kind misses it. Poisoned dagger(p) has no tier word at all.
POISONS = ['', '(p)', '(p+)', '(p++)']


def base_name(name):
    """The name less its poison suffix: rs2b0t's poison suffix pattern."""
    for suffix in POISONS[1:]:
        if name.endswith(suffix):
            return name[:-len(suffix)].rstrip()
    return name.rstrip()


GEAR_SLOTS = [
    Record({'slot': 'weapon', 'kinds': ['scimitar', 'longsword', 'battleaxe', 'sword', 'mace', 'dagger']}),
    Record({'slot': 'body', 'kinds': ['platebody', 'chainbody']}),
    Record({'slot': 'legs', 'kinds': ['platelegs', 'plateskirt']}),
    Record({'slot': 'helm', 'kinds': ['full helm', 'med helm']}),
    Record({'slot': 'shield', 'kinds': ['kiteshield', 'sq shield']}),
]
unwearable = set()
refusals = {}
# Why: a wield sent while a cutscene holds you gets no answer, and `equip` reads that as it reads a real refusal. The doll's throw wrote a rune scimitar off that way, and Regicide then fought a level 110 soldier with a bronze sword. A level or quest refusal fails every time, so it takes a few. This departs from rs2b0t.
REFUSALS_TO_WRITE_OFF = 3


def note_refused(name, log):
    """Counts a failed equip, and writes the piece off once it has failed enough times."""
    key = name.lower()
    refusals[key] = refusals.get(key, 0) + 1
    if refusals[key] < REFUSALS_TO_WRITE_OFF:
        log(f'{name} did not go on, try {refusals[key]} of {REFUSALS_TO_WRITE_OFF}')
        return
    log(f'cannot wear {name}, level or quest requirement; carrying it and moving on')
    unwearable.add(key)


def banked_named(snap, name):
    return snap.bank.get(name.lower(), 0) if snap.bank is not None else 0


def held_named(snap, name):
    return snap.inv.get(name.lower(), 0)


def wearing_slot(snap, kinds):
    for name in snap.worn:
        if any([base_name(name).endswith(kind) for kind in kinds]):
            return True
    return False


def best_in_bank(snap, kinds):
    for tier in TIERS:
        for kind in kinds:
            for poison in POISONS:
                name = f'{tier} {kind}{poison}'
                if (name in unwearable):
                    continue
                if banked_named(snap, name) > 0 or held_named(snap, name) > 0:
                    return name[0].upper() + name[1:]
    return None


def planned_gear(snap, slots='all'):
    """A declared loadout is taken literally; declaring nothing takes the best tier the bank holds."""
    if slots == 'weapon' and melee_armed(snap):
        return []
    weapon = weapon_of(quest_loadout.current)
    declared = ((([weapon] if weapon else [])) if slots == 'weapon' else gear_of(quest_loadout.current))
    if len(declared) > 0:
        return [name for name in declared if not (name.lower() in unwearable) and not (name.lower() in snap.worn)]
    out = []
    for _item5 in GEAR_SLOTS:
        slot = _item5.slot
        kinds = _item5.kinds
        if slots == 'weapon' and slot != 'weapon':
            continue
        if wearing_slot(snap, kinds):
            continue
        pick = best_in_bank(snap, kinds)
        if pick:
            out.append(pick)
    return out


def wear_gear(snap, slots='all'):
    """Draw and wear the melee kit; refusals are shed."""
    names = planned_gear(snap, slots)
    if len(names) == 0:
        return None
    if not snap.bank_known:
        return scan_bank()
    to_draw = [name for name in names if held_named(snap, name) == 0 and banked_named(snap, name) > 0]
    if len(to_draw) > 0:
        return Record({
            'kind': 'withdraw',
            'bank': UP_TILE.ARDOUGNE_BANK,
            'items': [{'name': name, 'qty': 1} for name in to_draw],
        })

    def _fn6(log):
        for name in names:
            _c7 = equipment.contains(name)
            if not _c7:
                _w8 = yield from equipment.equip(name)
                _c7 = (_w8)
            if _c7:
                continue
            note_refused(name, log)
        return True
    return Record({'kind': 'custom', 'name': f"wear {', '.join(names)}", 'run': _fn6})


WEAPON_KINDS = GEAR_SLOTS[0].kinds


def melee_armed(snap):
    """True once a melee weapon is on; the bow doesn't count."""
    return wearing_slot(snap, WEAPON_KINDS)


def melee_carried(snap):
    """True once a melee weapon is on or in the pack, which is what the cave mouth waits for."""
    return melee_armed(snap) or pack_weapon(snap) is not None


def pack_weapon(snap):
    return pack_gear(snap, [Record({'kinds': WEAPON_KINDS})])


def pack_gear(snap, slots):
    for _item9 in slots:
        kinds = _item9.kinds
        if wearing_slot(snap, kinds):
            continue
        for name in list(snap.inv.keys()):
            if any([base_name(name).endswith(kind) for kind in kinds]) and not (name in unwearable):
                return name
    return None


# Why: `armFireArrow` puts the shortbow in the right hand and the melee weapon in the pack, and nothing after the bridge takes it back out. Armour in the pack is the same plus 5 slots the orb sweep needs, so the full set goes on.
# Why: a rune platebody wants Dragon Slayer, and `equip` answers a refusal and a miss the same way, false, so a plain equip step would retry forever. The piece is written off and the step still succeeds.
def draw_gear(snap, slots='all'):
    """Wear the next piece of melee kit the pack is still carrying, once the bow has had its turn."""
    name = (pack_weapon(snap) if slots == 'weapon' else pack_gear(snap, GEAR_SLOTS))
    if name is None:
        return None

    def _fn10(log):
        _c11 = equipment.contains(name)
        if not _c11:
            _w12 = yield from equipment.equip(name)
            _c11 = (_w12)
        if _c11:
            return True
        note_refused(name, log)
        return True
    return Record({'kind': 'custom', 'name': f'wear {name}', 'run': _fn10})

