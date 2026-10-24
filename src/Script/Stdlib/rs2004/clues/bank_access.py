"""Opening the bank a trail stops at: rs2b0t's api/ai/clues/bankAccess.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.bank import bank
from rs2004.game import game
from rs2004.traversal import nearest_bank


def open_clue_bank(log=None):
    """Opens the nearest bank its own way: an NPC banker, a chest or other access, or a booth. A Wait."""
    here = game.tile()
    near = nearest_bank(here) if here is not None else None
    if near is not None and near.get('npcAccess'):
        opened = yield from bank.open_npc_access(near['npcAccess'])
        return opened
    if near is not None and near.get('access'):
        opened = yield from bank.open_nearest_access(near['access'])
        return opened
    opened = yield from bank.open_nearest('Bank booth', 'Use-quickly')
    return opened


def reopen_clue_bank():
    """Opens the trail's bank again and waits for it to be ready. A Wait."""
    opened = yield from open_clue_bank()
    if not opened:
        return False
    ready = yield from bank.wait_ready()
    return ready
