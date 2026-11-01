"""Ported from rs2b0t's src/bot/api/ai/quests/defs/horror/barcrawl.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.barcrawl.barcrawl_logic import BARCRAWL_GP
from rs2004.quests.defs.horror.areas import HD_ID, HD_ITEM

__all__ = ['barcrawl_funds']

# Why: the tour itself lives in `src/bot/api/ai/quests/barcrawl/`; this only adds the coin provisioning as a `QuestStep` so the engine banks for it.
def barcrawl_funds(snap):
    """Coin cover for the tour, drawn before the walk."""
    held = snap.inv_ids.get(HD_ID.COINS, 0) if snap.inv_ids is not None else 0
    if held >= BARCRAWL_GP:
        return None
    if not snap.bank_known:
        return Record({'kind': 'scan_bank'})
    return Record({
        'kind': 'withdraw',
        'items': [{'name': HD_ITEM.COINS, 'qty': BARCRAWL_GP * 4, 'id': HD_ID.COINS}],
    })
