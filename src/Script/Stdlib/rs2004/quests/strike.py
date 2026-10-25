"""Strike spells for the quests that fight with them: rs2b0t's api/ai/quests/strike.ts (MIT, see thirdparty/rs2b0t).
The best Strike the account can cast, and the runes for STRIKE_CASTS of it, from the bank or Betty's shop."""

from rs2004.catalogs.combat import SPELL_DB, casts_available
from rs2004.geometry import Tile
from rs2004.quests.engine.types import quest_step

__all__ = ['STRIKE_CASTS', 'STRIKE_RUNES', 'STRIKES', 'BETTY', 'strike_spell', 'prepare_strikes']

STRIKE_CASTS = 150
STRIKE_RUNES = ['mind rune', 'air rune', 'water rune', 'earth rune', 'fire rune']
STRIKES = ['Fire Strike', 'Earth Strike', 'Water Strike', 'Wind Strike']
BETTY = {'npc': 'Betty', 'anchor': Tile(3012, 3259, 0)}


# Why: a large count, not infinity: casts_available floor-divides it, and inf // n is nan in Python.
def _unlimited(rune):
    return 1000000000


def strike_spell(magic, count=None):
    """The best Strike magic casts that count(rune) pays for at least once, or None. Without count, runes are
    taken as plenty."""
    held = count if count is not None else _unlimited
    for name in STRIKES:
        if SPELL_DB[name]['level'] <= magic and casts_available(name, [], held) > 0:
            return name
    return None


def prepare_strikes(snap, keep=None):
    """The step towards STRIKE_CASTS of the best Strike in the pack, or None once they're there."""
    spell = strike_spell(snap.magic if snap.magic is not None else 1)
    if spell is None:
        return quest_step('wait', reason='need Magic 1 for Strike spells')
    missing = []
    for r in SPELL_DB[spell]['runes']:
        qty = r['count'] * STRIKE_CASTS - snap.inv.get(r['rune'].lower(), 0)
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
