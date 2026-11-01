# ---- api/ai/quests/defs/upass/chest.ts
"""Ported from rs2b0t's src/bot/api/ai/quests/defs/upass/chest.ts (MIT, see thirdparty/rs2b0t). A ts2py draft: fix what's
marked "ts2py:", then this line."""

from rs2004.catalogs.record import Record
from rs2004.quests.defs.upass.areas import UP_LOC

__all__ = ['CHEST_FORMS', 'chest_form']

# Why: Kardia's chest changes from id 3272/Open to id 3273/Search for 20 ticks, so accept either form.
CHEST_FORMS = [Record({'id': UP_LOC.WITCH_CHEST, 'op': 'Open'}), Record({'id': UP_LOC.WITCH_CHEST_OPEN, 'op': 'Search'})]


def chest_form(present):
    """The form of the chest that is standing there now. Why: the closed form when neither is in sight, so the reach still walks to it; the chest can be out of the build area from the street."""
    _v1 = ([form for form in CHEST_FORMS if present(form.id, form.op)] or [None])[0]
    return (_v1 if _v1 is not None else CHEST_FORMS[0])

