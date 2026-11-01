"""Ported from rs2b0t's src/bot/api/ai/quests/defs/holygrail/armour.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record

__all__ = ['ARMOUR_KEEP', 'unwearable', 'reset_unwearable', 'armour_wanted']

TIERS = ['rune', 'adamant', 'mithril', 'black', 'steel', 'iron', 'bronze']
# Why: no weapon slot; Excalibur is the only sword that kills the titan and anything else loses the fight in silence.
# Why: chainbody outranks platebody, as rune plate wants Dragon Slayer complete and refuses without a message.
SLOTS = [
    Record({'kinds': ['chainbody', 'platebody']}),
    Record({'kinds': ['platelegs', 'plateskirt']}),
    Record({'kinds': ['full helm', 'med helm']}),
    Record({'kinds': ['kiteshield', 'sq shield']}),
]
ARMOUR_KEEP = []
for _slot in SLOTS:
    ARMOUR_KEEP.extend(_slot.kinds)
unwearable = set()


def reset_unwearable():
    unwearable.clear()


def wearing_kind(snap, kinds):
    for name in snap.worn:
        if any([name.endswith(kind) for kind in kinds]):
            return True
    return False


def best_for_slot(snap, kinds):
    for tier in TIERS:
        for kind in kinds:
            name = f'{tier} {kind}'
            if (name in unwearable):
                continue
            in_bank = snap.bank.get(name, 0) if snap.bank is not None else 0
            if in_bank > 0 or snap.inv.get(name, 0) > 0:
                return name[0].upper() + name[1:]
    return None


def armour_wanted(snap):
    """The best banked armour for the slots the account has not filled."""
    out = []
    for slot in SLOTS:
        kinds = slot.kinds
        if wearing_kind(snap, kinds):
            continue
        pick = best_for_slot(snap, kinds)
        if pick:
            out.append(pick)
    return out
