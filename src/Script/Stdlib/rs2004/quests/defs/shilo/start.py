"""Ported from rs2b0t's src/bot/api/ai/quests/defs/shilo/start.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.dialogue import chat_dialog
from rs2004.entities import npcs
from rs2004.items import inventory
from rs2004.quests.defs.shilo.areas import SV_ITEM, SV_NPC, SV_TILE
from rs2004.quests.defs.shilo.scene import drive_choice, held_id
from rs2004.quests.exec.primitives import talk_strict
from rs2004.traversal import traversal

__all__ = ['take_wampum_belt', 'start_quest']

# Why: `pickPreferred` takes the earliest preference that appears and Mosol's menus re-offer earlier ones, so the deepest option comes first or his 4th menu loops.
# Why: "What danger is there around here?" spawns 1 to 3 aggressive Undead Ones, hence `talkStrict`.
MOSOL_DIALOGUE = [
    "Yes, I'm sure and I'll take the Wampum belt to Trufitus.",
    "I'll go to see the Shaman.",
    'What can we do?',
    'Rashiliyia? Who is she?',
    'Why do I need to run?',
]
TRUFITUS_DIALOGUE = [
    'Yes, I will seriously look for Ah Za Rhoon',
    'I am going to search for Ah Za Rhoon!',
    'Why was it called Ah Za Rhoon?',
    'Mosol Rei said something about a legend?',
]


def take_wampum_belt(log):
    if held_id(SV_ITEM.WAMPUM_BELT.id) > 0:
        return True
    _w1 = yield from traversal.walk_resilient(SV_TILE.MOSOL_REI, radius=3, attempts=3, timeout_ms=300000, log=log)
    if not (_w1):
        return False
    _w2 = yield from talk_strict(SV_NPC.MOSOL_REI, MOSOL_DIALOGUE, log)
    if not (_w2):
        return False
    _result3 = yield from execution.delay_until(lambda: held_id(SV_ITEM.WAMPUM_BELT.id) > 0, 10000)
    return _result3


def start_quest(log):
    """The quest starts from `opnpcu`: the belt is used on Trufitus, and only then does the Ah Za Rhoon thread appear."""
    if held_id(SV_ITEM.WAMPUM_BELT.id) == 0:
        log('no Wampum belt to show Trufitus')
        return False
    _w4 = yield from traversal.walk_resilient(SV_TILE.TRUFITUS, radius=2, attempts=3, timeout_ms=300000, log=log)
    if not (_w4):
        return False
    trufitus = npcs.query().name(SV_NPC.TRUFITUS).nearest()
    belt = ([item for item in inventory.items() if item.id == SV_ITEM.WAMPUM_BELT.id] or [None])[0]
    if not trufitus or not belt:
        log('Trufitus is not in range')
        return False
    if not (belt.use_on(trufitus)):
        return False
    _w5 = yield from execution.delay_until(lambda: chat_dialog.is_open() or chat_dialog.can_continue(), 8000)
    if not (_w5):
        log('showing the belt opened no dialogue')
        return False
    _w6 = yield from drive_choice(TRUFITUS_DIALOGUE, log)
    if not (_w6):
        return False
    _result7 = yield from execution.delay_until(lambda: held_id(SV_ITEM.WAMPUM_BELT.id) == 0, 10000)
    return _result7
