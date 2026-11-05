"""Ported from rs2b0t's src/bot/api/ai/quests/defs/ikov/gear.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.items import equipment

__all__ = ['RANGED_ARMOUR_NAMES', 'IKOV_GEAR_NAMES', 'ranged_armour_step', 'melee_weapon_step']

# Why: 9 level-61 ice spiders on the chest circuit and 3 level-42 hobgoblins at once, both `crush_style`, and the bank is the only wardrobe; feet hold the boots of lightness and the right hand the bow, so neither slot is filled here.
RANGED_SLOTS = [
    ['Coif', 'Leather cowl'],
    ['Dragonhide body', 'Studded body', 'Hardleather body', 'Leather body'],
    ['Dragonhide chaps', 'Studded chaps', 'Leather chaps'],
    ['Dragon vambraces', 'Leather vambraces', 'Leather gloves'],
]
MELEE_TIERS = ['Rune', 'Adamant', 'Mithril', 'Black', 'Steel', 'Iron', 'Bronze']
# Why: a hobgoblin carries 1 stab defence and 1 slash defence, so tier beats shape and the fastest weapon of the best tier wins, a scimitar ahead of the longsword of the same metal.
MELEE_KINDS = ['scimitar', 'longsword', 'sword', 'battleaxe', 'mace', 'warhammer']
_flat1 = []
for tier in MELEE_TIERS:
    _flat1.extend([f'{tier} {kind}' for kind in MELEE_KINDS])


MELEE_WEAPONS = _flat1
RANGED_ARMOUR_NAMES = []
for slot in RANGED_SLOTS:
    RANGED_ARMOUR_NAMES.extend([name.lower() for name in slot])


IKOV_GEAR_NAMES = list(RANGED_ARMOUR_NAMES) + list([name.lower() for name in MELEE_WEAPONS])
# Why: `equip` answers a level or quest refusal with false and no message, so a piece re-picked every pass is a run spent withdrawing the same body.
refused = set()


def stocked(snap, name):
    key = name.lower()
    _v2 = snap.inv.get(key)
    _v3 = (snap.bank.get(key) if snap.bank is not None else None)
    return ((_v2 if _v2 is not None else 0)) + ((_v3 if _v3 is not None else 0)) + int(key in snap.worn)


def dressed(snap, slot):
    return any([(name.lower() in snap.worn) for name in slot])


def best_in_bank(snap, slot):
    _v4 = ([name for name in slot if not (name.lower() in refused) and stocked(snap, name) > 0] or [None])[0]
    return (_v4 if _v4 is not None else None)


# Why: a slot already carrying something is left alone, because a mid-run swap costs a bank trip to save a point of defence.
def ranged_gear_wanted(snap):
    """The best ranged piece the bank can dress each bare slot with."""
    out = []
    for slot in RANGED_SLOTS:
        if dressed(snap, slot):
            continue
        pick = best_in_bank(snap, slot)
        if pick:
            out.append(pick)
    return out


def ranged_armour_step(snap):
    """Withdraw and wear the best ranged armour the bank holds, or null once it can do no better."""
    if not snap.bank_known:
        return None
    wanted = ranged_gear_wanted(snap)
    if len(wanted) == 0:
        return None
    missing = [name for name in wanted if ((snap.inv.get(name.lower()) if snap.inv.get(name.lower()) is not None else 0)) == 0]
    if len(missing) > 0:
        return Record({'kind': 'withdraw', 'items': [{'name': name, 'qty': 1} for name in missing]})

    def _fn5(log):
        for name in wanted:
            _c6 = equipment.contains(name)
            if not _c6:
                _w7 = yield from equipment.equip(name)
                _c6 = (_w7)
            if _c6:
                continue
            log(f'ikov: the server refused {name} — a level or quest gate; dropping it from the kit')
            refused.add(name.lower())
        return True
    return Record({'kind': 'custom', 'name': f"wear {', '.join(wanted)}", 'run': _fn5})


# Why: the crossing kit leaves the bot bare-handed for the roots farm, so the weapon is picked like the armour, best in the bank, with the yew axe as the floor.
def best_melee_weapon(snap):
    """The best melee weapon the bank holds, or null when it holds none the server has not refused."""
    if not snap.bank_known:
        return None
    return best_in_bank(snap, MELEE_WEAPONS)


def melee_weapon_step(snap):
    """Withdraw and wield that weapon, or null when the pack is already carrying the best there is."""
    want = best_melee_weapon(snap)
    if not want:
        return None
    # Why: wielding swaps the old weapon into the pack, so ranking only what's stocked made a worn scimitar and a spare bronze sword trade places forever.
    if any([name.lower() in snap.worn for name in MELEE_WEAPONS[:MELEE_WEAPONS.index(want) + 1]]):
        return None
    _v8 = snap.inv.get(want.lower())
    if ((_v8 if _v8 is not None else 0)) == 0:
        return Record({'kind': 'withdraw', 'items': [{'name': want, 'qty': 1}]})

    def _fn9(log):
        _c10 = equipment.contains(want)
        if not _c10:
            _w11 = yield from equipment.equip(want)
            _c10 = (_w11)
        if _c10:
            return True
        log(f'ikov: the server refused {want} — an attack-level gate; dropping it from the kit')
        refused.add(want.lower())
        return True
    return Record({'kind': 'custom', 'name': f'wield {want}', 'run': _fn9})
