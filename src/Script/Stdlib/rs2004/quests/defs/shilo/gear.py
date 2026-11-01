"""Ported from rs2b0t's src/bot/api/ai/quests/defs/shilo/gear.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.catalogs.tables import item_db
from rs2004.items import equipment
from rs2004.quests.defs.shilo.areas import SV_ITEM, SV_TILE
from rs2004.quests.defs.shilo.supplies import food_names, scan_bank, withdraw_from
from rs2004.quests.gear import quest_loadout

__all__ = ['reset_combat_gear', 'combat_gear']

TIERS = ['Rune', 'Adamant', 'Mithril', 'Black', 'Steel', 'Iron', 'Bronze']
SLOTS = [
    Record({'slot': 'righthand', 'kinds': ['scimitar', 'longsword', 'sword', 'mace', 'battleaxe', 'warhammer']}),
    Record({'slot': 'torso', 'kinds': ['chainbody', 'platebody']}),
    Record({'slot': 'legs', 'kinds': ['platelegs', 'plateskirt']}),
    Record({'slot': 'hat', 'kinds': ['full helm', 'med helm']}),
    Record({'slot': 'lefthand', 'kinds': ['kiteshield', 'sq shield']}),
]
rejected = set()


def reset_combat_gear():
    rejected.clear()


def count_of(counts, name):
    count = None if counts is None else counts.get(name.lower())
    return count if count is not None else 0


def slot_names(entry, declared):
    """The names that may fill one slot: the loadout's choice, else every tier of every kind."""
    chosen = declared.get(entry.slot)
    if chosen:
        return [chosen]
    names = []
    for tier in TIERS:
        names.extend([f'{tier} {kind}' for kind in entry.kinds])
    return names


def candidates(snap):
    worn = [item for item in item_db() if item.name.lower() in snap.worn]
    worn_slots = set([item.slot for item in worn])
    declared = quest_loadout.current.worn if quest_loadout.current is not None else {}
    righthand = declared.get('righthand')
    wanted = None if righthand is None else righthand.lower()
    two_handed = any([item.two_handed for item in worn]) or any([item.two_handed and item.name.lower() == wanted for item in item_db()])
    out = []
    for entry in SLOTS:
        if entry.slot in worn_slots or (entry.slot == 'lefthand' and two_handed):
            continue
        usable = [name for name in slot_names(entry, declared) if name.lower() not in rejected]
        if len(usable) > 0:
            out.append(usable)
    return out


def wear_carried(carried):
    def run(log):
        for name in carried:
            if equipment.contains(name):
                continue
            worn = yield from equipment.equip(name)
            if not worn:
                rejected.add(name.lower())
                log(f'could not wear {name}; trying other combat gear')
        return True
    return run


def combat_gear(snap):
    missing = candidates(snap)
    if len(missing) == 0:
        return None
    names = []
    for usable in missing:
        pick = ([name for name in usable if count_of(snap.inv, name) > 0] or [None])[0]
        if pick is None:
            pick = ([name for name in usable if count_of(snap.bank, name) > 0] or [None])[0]
        if pick:
            names.append(pick)
    carried = [name for name in names if count_of(snap.inv, name) > 0]
    if len(carried) > 0:
        return Record({'kind': 'custom', 'name': f"wear {', '.join(carried)}", 'run': wear_carried(carried)})
    if not snap.bank_known:
        return scan_bank()
    if len(names) == 0:
        return None
    if snap.free_slots == 0:
        carry = quest_loadout.current.carry if quest_loadout.current is not None else []
        protected_names = set([SV_ITEM.get(key).name.lower() for key in SV_ITEM.keys()] + [item.item.lower() for item in carry])
        food = set([name.lower() for name in food_names()])
        stored = ([name for name in snap.inv.keys() if name in rejected or name in food or name not in protected_names] or [None])[0]
        if not stored:
            return Record({'kind': 'wait', 'reason': 'need a free inventory slot for combat gear'})
        return Record({
            'kind': 'deposit',
            'exact_keep': True,
            'keep': [name for name in snap.inv.keys() if name != stored],
            'bank': SV_TILE.ARDOUGNE_BANK,
        })
    room = snap.free_slots if snap.free_slots is not None else len(names)
    return withdraw_from([{'name': name, 'qty': 1} for name in names[0:room]])
