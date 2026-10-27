"""Ported from rs2b0t's src/bot/api/ai/quests/defs/ernest/supplies.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.defs.ernest.areas import EC_ID, EC_NAME, EC_TILE


__all__ = ['held_id', 'banked_id', 'kit']

def held_id(snap, id):
    _v1 = (snap.inv_ids or {}).get(id)
    return (_v1 if _v1 is not None else 0)


def banked_id(snap, id):
    _v2 = (snap.bank_ids or {}).get(id)
    return (_v2 if _v2 is not None else 0)


# Why: `ownsInventory` opts the module out of the engine's food withdrawal, and nothing in the manor is aggressive, so the trip carries the spade and nothing else.
def kit(snap):
    """The module's own spade withdrawal, or null when the pack is ready."""
    if held_id(snap, EC_ID.SPADE) > 0:
        return None
    if not snap.bank_known:
        return Record({'kind': 'scan_bank'})
    if banked_id(snap, EC_ID.SPADE) > 0:
        return Record({'kind': 'withdraw', 'items': [{'name': EC_NAME.SPADE, 'qty': 1, 'id': EC_ID.SPADE}]})
    # No banked spade. The only free source is the manor ground spawn.
    return Record({'kind': 'grab_ground', 'item': EC_NAME.SPADE, 'anchor': EC_TILE.SPADE_SPAWN, 'wait_if_missing': True})
