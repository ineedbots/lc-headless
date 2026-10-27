"""Ported from rs2b0t's src/bot/api/ai/quests/defs/shieldofarrav/state.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.quests.defs.shieldofarrav.areas import SOA_ID
from rs2004.game import reader
from rs2004.items import inventory

__all__ = ['own_half', 'other_half', 'live_item', 'modal_said']

def own_half(gang):
    """The half this gang can take for itself."""
    return (SOA_ID.SHIELD_PHOENIX if gang == 'phoenix' else SOA_ID.SHIELD_BLACKARM)


def other_half(gang):
    """The half only the other gang can reach."""
    return (SOA_ID.SHIELD_BLACKARM if gang == 'phoenix' else SOA_ID.SHIELD_PHOENIX)


def live_item(id):
    _v1 = ([item for item in inventory.items() if item.id == id] or [None])[0]
    return (_v1 if _v1 is not None else None)


# Why: `~objbox` and `~mesbox` build a main modal, so their text never reaches `GameMessages`.
def modal_said(pattern):
    """Whether the open main modal says something."""
    return any([pattern.lower() in line.lower() for line in reader.main_modal_texts()])
