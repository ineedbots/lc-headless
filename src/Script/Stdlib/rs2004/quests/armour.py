"""The armour a quest wears: rs2b0t's api/ai/quests/armour.ts (MIT, see thirdparty/rs2b0t). Metal by Defence tier,
and the ranged hides by Defence and Ranged."""

from rs2004.catalogs.record import Record
from rs2004.catalogs.tables import item_db
from rs2004.game import skills
from rs2004.quests.weapons import quest_done

__all__ = ['TIERS', 'SHAPES', 'QUEST_ARMOUR', 'armour_worn', 'armour_held', 'armour_choice']

TIERS = [('Rune', 40), ('Adamant', 30), ('Mithril', 20), ('Black', 10), ('Steel', 5), ('Iron', 1), ('Bronze', 1)]

SHAPES = {
    'torso': ['chainbody', 'platebody'],
    'legs': ['platelegs', 'plateskirt'],
    'hat': ['full helm', 'med helm'],
    'lefthand': ['kiteshield', 'sq shield'],
}

# obj, the Defence it needs, the Ranged it needs.
RANGED_ARMOUR = [
    ('studded_body', 20, 20), ('hardleather_body', 10, 0), ('leather_armour', 0, 1), ('studded_chaps', 0, 20),
    ('leather_chaps', 0, 1), ('coif', 0, 20), ('leather_cowl', 0, 1),
]


def _piece(row, defence, ranged):
    return Record({'id': row.id, 'name': row.name, 'slot': row.slot, 'defence': defence, 'ranged': ranged})


def _build():
    by_name = {}
    by_obj = {}
    for row in item_db():
        if row.name not in by_name:
            by_name[row.name] = row
        if row.obj not in by_obj:
            by_obj[row.obj] = row
    out = []
    for tier, defence in TIERS:
        for slot in SHAPES.keys():
            for shape in SHAPES[slot]:
                row = by_name.get(f'{tier} {shape}')
                if row is not None:
                    out.append(_piece(row, defence, 0))
    for obj, defence, ranged in RANGED_ARMOUR:
        row = by_obj.get(obj)
        if row is not None:
            out.append(_piece(row, defence, ranged))
    return out


# Each piece a quest may wear: a Record of id, name, slot, and the defence and ranged levels it needs.
QUEST_ARMOUR = _build()


def armour_worn(snap, item):
    return (snap.worn_ids is not None and item.id in snap.worn_ids) or item.name.lower() in snap.worn


def armour_held(snap, item):
    if snap.inv_ids is not None and item.id in snap.inv_ids:
        return snap.inv_ids[item.id] > 0
    return snap.inv.get(item.name.lower(), 0) > 0


def _banked(snap, item):
    if snap.bank_ids is not None and item.id in snap.bank_ids:
        return snap.bank_ids[item.id]
    return snap.bank.get(item.name.lower(), 0) if snap.bank is not None else 0


def armour_choice(snap, slot):
    """What to wear in a slot ('torso', 'legs', 'hat', 'lefthand' or 'front'), as a Record with id and name: what's
    worn there already, else the best the account may wear that the pack holds, else that the bank holds, else None."""
    for row in item_db():
        if row.slot == slot and armour_worn(snap, row):
            return row
    defence = skills.level('defence')
    ranged = snap.ranged if snap.ranged is not None else skills.level('ranged')
    usable = [item for item in QUEST_ARMOUR if item.slot == slot and item.defence <= defence and item.ranged <= ranged
              and (item.name != 'Rune platebody' or quest_done('Dragon Slayer'))]
    for item in usable:
        if armour_held(snap, item):
            return item
    if snap.bank_known:
        for item in usable:
            if _banked(snap, item) > 0:
                return item
    return None
