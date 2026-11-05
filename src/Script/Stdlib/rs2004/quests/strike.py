"""Strike spells for the quests that fight with them: rs2b0t's api/ai/quests/strike.ts (MIT, see thirdparty/rs2b0t).
The best Strike the account can cast, and the runes for STRIKE_CASTS of it, from the bank or Betty's shop."""

from rs2004.catalogs.combat import SPELL_DB, STAFF_RUNES, casts_available, runes_per_cast
from rs2004.geometry import Tile
from rs2004.trade import shop
from rs2004.traversal import traversal
from rs2004.quests.engine.types import quest_step

__all__ = ['STRIKE_CASTS', 'STRIKE_RUNES', 'STRIKES', 'BETTY', 'strike_spell', 'prepare_strikes', 'prepare_strike_staff', 'STRIKE_STAVES']

STRIKE_CASTS = 150
STRIKE_RUNES = ['mind rune', 'air rune', 'water rune', 'earth rune', 'fire rune']
STRIKES = ['Fire Strike', 'Earth Strike', 'Water Strike', 'Wind Strike']
BETTY = {'npc': 'Betty', 'anchor': Tile(3012, 3259, 0)}


STRIKE_MAX_HITS = {'Fire Strike': 8, 'Earth Strike': 6, 'Water Strike': 4, 'Wind Strike': 2}
STRIKE_STAVES = [name.lower() for name in STAFF_RUNES]
ZAFF = Tile(3203, 3433, 0)
STAFF_GP = 2000


def strike_spell(magic, count=None, wielded=None):
    if count is None:
        return ([name for name in STRIKES if SPELL_DB[name]['level'] <= magic] or [None])[0]
    held = count
    best = None
    budget = 0
    for name in STRIKES:
        if SPELL_DB[name]['level'] > magic:
            continue
        damage = casts_available(name, wielded or [], held) * STRIKE_MAX_HITS[name]
        if damage > budget:
            best = name
            budget = damage
    return best


def supplied_strike(magic, wielded):
    for name in STRIKES:
        if SPELL_DB[name]['level'] <= magic:
            element = SPELL_DB[name]['runes'][1]['rune']
            if not any([cost['rune'] == element for cost in runes_per_cast(name, wielded)]):
                return name
    return None


def buy_strike_staff(staves, log):
    arrived = yield from traversal.walk_resilient(ZAFF, radius=3, attempts=3, timeout_ms=120000, log=log)
    if not arrived:
        return False
    opened = yield from shop.open('Zaff')
    if not opened:
        return False
    bought = False
    try:
        for staff in staves:
            if not any([item.name == staff and item.count > 0 for item in shop.stock()]):
                continue
            count = yield from shop.buy(staff, 1)
            if count > 0:
                bought = True
                break
        if not bought:
            log('Zaff has no usable elemental staff in stock')
    except Exception:
        yield from shop.close()
        raise
    yield from shop.close()
    return bought


def prepare_strike_staff(snap, keep=None):
    magic = snap.magic if snap.magic is not None else 1
    if not strike_spell(magic) or supplied_strike(magic, list(snap.worn)):
        return None
    elements = [SPELL_DB[name]['runes'][1] for name in STRIKES if SPELL_DB[name]['level'] <= magic]
    usable = []
    for name, runes in STAFF_RUNES.items():
        level = 40 if name.startswith('Mystic') else (30 if name.endswith('battlestaff') else 1)
        ranks = [i for i, element in enumerate(elements) if element['rune'] in runes]
        if ranks and level <= magic and level <= (snap.attack if snap.attack is not None else 1):
            usable.append((min(ranks), name))
    usable = [pair[1] for pair in sorted(usable, key=lambda pair: pair[0])]
    for name in usable:
        if snap.inv.get(name.lower(), 0) > 0:
            return quest_step('equip', item=name)
    element = elements[0]
    bank = snap.bank or {}
    if snap.inv.get(element['rune'].lower(), 0) + (bank.get(element['rune'].lower(), 0) if snap.bank_known else 0) >= element['count'] * STRIKE_CASTS:
        return None
    if not snap.bank_known:
        return quest_step('scan_bank')
    banked = ([name for name in usable if bank.get(name.lower(), 0) > 0] or [None])[0]
    short = STAFF_GP - snap.inv.get('coins', 0)
    if not banked and short > snap.bank_coins:
        return None
    if (snap.free_slots if snap.free_slots is not None else 28) < 1:
        preserve = list(keep or []) + STRIKE_RUNES + STRIKE_STAVES + ['coins']
        if any([name not in preserve for name in snap.inv]):
            return quest_step('deposit', keep=preserve, exact_keep=True)
        return quest_step('wait', reason='need a free inventory slot for a Strike staff')
    if banked:
        return quest_step('withdraw', items=[{'name': banked, 'qty': 1}])
    if short > 0:
        return quest_step('withdraw', items=[{'name': 'Coins', 'qty': short}])
    staves = ['Staff of ' + element['rune'].split(' ')[0].lower() for element in elements]
    return quest_step('custom', name='buy a Strike staff from Zaff', run=lambda log: buy_strike_staff(staves, log))


def prepare_strikes(snap, keep=None, wielded=None):
    """The step towards STRIKE_CASTS of the best Strike in the pack, or None once they're there."""
    magic = snap.magic if snap.magic is not None else 1
    wielded = list(snap.worn) if wielded is None else wielded
    strongest = strike_spell(magic)
    if strongest is None:
        return quest_step('wait', reason='need Magic 1 for Strike spells')
    banked = snap.bank or {}
    supplied = casts_available(strongest, wielded, lambda rune: snap.inv.get(rune.lower(), 0) + (banked.get(rune.lower(), 0) if snap.bank_known else 0)) >= STRIKE_CASTS
    spell = strongest if supplied else (supplied_strike(magic, wielded) or strongest)
    casts = (STRIKE_CASTS * STRIKE_MAX_HITS[strongest] + STRIKE_MAX_HITS[spell] - 1) // STRIKE_MAX_HITS[spell]
    missing = []
    for r in runes_per_cast(spell, wielded):
        qty = r['count'] * casts - snap.inv.get(r['rune'].lower(), 0)
        if qty > 0:
            missing.append({'name': r['rune'], 'qty': qty})
    if len(missing) == 0:
        return None
    if not snap.bank_known:
        return quest_step('scan_bank')
    slots = len([item for item in missing if item['name'].lower() not in snap.inv])
    free = snap.free_slots if snap.free_slots is not None else 28
    if free < slots:
        preserve = list(keep or []) + STRIKE_RUNES + ['coins']
        if len([name for name in snap.inv.keys() if name not in preserve]) > 0:
            return quest_step('deposit', keep=preserve, exact_keep=True)
        return quest_step('wait', reason=f'need {slots} free inventory slots for Strike runes')
    bank = snap.bank if snap.bank is not None else {}
    draw = []
    for item in missing:
        qty = min(item['qty'], bank.get(item['name'].lower(), 0))
        if qty > 0:
            draw.append({'name': item['name'], 'qty': qty})
    if len(draw) > 0:
        return quest_step('withdraw', items=draw)
    item = missing[0]
    return quest_step('buy', item=item['name'], qty=item['qty'], shop=BETTY, est_gp=min(1000, item['qty'] * 24))
