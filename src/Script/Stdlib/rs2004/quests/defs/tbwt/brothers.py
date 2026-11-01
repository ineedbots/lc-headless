"""Ported from rs2b0t's src/bot/api/ai/quests/defs/tbwt/brothers.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.game import reader
from rs2004.items import inventory
from rs2004.quests.defs.tbwt.areas import TB_ID, TB_NPC, TB_TIADECHE, TB_TILE, TB_VARP, TIMFRAKU_REWARD, TIMFRAKU_START
from rs2004.quests.defs.tbwt.talk import CUTSCENE_GAP, LONG_GAP, talk_fully, use_on_npc

__all__ = ['start_quest', 'claim_reward', 'meet_lubufu', 'give_karambwanji', 'become_apprentice', 'spare_vessel', 'meet_tiadeche', 'tiadeche_catch', 'give_manual', 'meet_tinsay', 'give_tinsay', 'meet_tamayu', 'hunt_shaikahan', 'give_tamayu']


def held_id(id):
    return sum([i.count for i in [i for i in inventory.items() if i.id == id]])


# Why: every list is matched by preference, ordered so the first entry that appears in a menu is the one this leg wants.
LUBUFU_MEET = [
    "What's a whippersnapper?",
    'Talk about him',
    'How old are you?',
    'I could help collect the bait.',
    'You sound like you could do with the help.',
]
LUBUFU_APPRENTICE = ['What is a Karambwan?', 'Yes!']
LUBUFU_SPARE_VESSEL = ["Actually, I've lost my Karambwan vessel.", 'a shark ate it!']
TIADECHE_INTRO = ['When will you be finished?']
TIADECHE_ACCEPT = ['Yes']
TAMAYU_HUNT = ['When will you succeed?', 'Take me on your next hunt', 'Yes']
# Why: the queue is 10 ticks, but a talk the reach layer re-clicked has already armed it once, so the wait carries margin.
LUBUFU_QUEUE_TICKS = 16


def start_quest(log):
    return talk_fully(TIMFRAKU_START.npc, TIMFRAKU_START.anchor, TIMFRAKU_START.prefer, log, LONG_GAP)


def claim_reward(log):
    return talk_fully(TIMFRAKU_REWARD.npc, TIMFRAKU_REWARD.anchor, TIMFRAKU_REWARD.prefer, log, LONG_GAP)


def meet_lubufu(log):
    """Talk, sit out the brush-off queue, talk again, idempotent from either state."""
    _w1 = yield from talk_fully(TB_NPC.LUBUFU, TB_TILE.LUBUFU, LUBUFU_MEET, log)
    if not (_w1):
        return False
    yield from execution.delay_ticks(LUBUFU_QUEUE_TICKS)
    _result2 = yield from talk_fully(TB_NPC.LUBUFU, TB_TILE.LUBUFU, LUBUFU_MEET, log)
    return _result2


def give_karambwanji(log):
    """Give over all held Karambwanji; the NPC counts them."""
    before = held_id(TB_ID.RAW_KARAMBWANJI)
    if before == 0:
        log('no Raw karambwanji in the pack to hand over')
        return False
    _w3 = yield from talk_fully(TB_NPC.LUBUFU, TB_TILE.LUBUFU, [], log, LONG_GAP)
    if not (_w3):
        return False
    return held_id(TB_ID.RAW_KARAMBWANJI) < before


def become_apprentice(log):
    """Ask until he offers the apprenticeship and hands the vessel over."""
    ask = 0
    while ask < 6 and held_id(TB_ID.VESSEL) == 0 and held_id(TB_ID.VESSEL_LOADED) == 0:
        _w4 = yield from talk_fully(TB_NPC.LUBUFU, TB_TILE.LUBUFU, LUBUFU_APPRENTICE, log, LONG_GAP)
        if not (_w4):
            return False
        ask += 1
    return held_id(TB_ID.VESSEL) > 0 or held_id(TB_ID.VESSEL_LOADED) > 0


# Why: Tiadeche keeps the first vessel and Tinsay consumes the second, and Lubufu re-issues one to anyone carrying none.
def spare_vessel(log):
    """A replacement vessel from Lubufu."""
    if held_id(TB_ID.VESSEL) > 0 or held_id(TB_ID.VESSEL_LOADED) > 0:
        return True
    _w5 = yield from talk_fully(TB_NPC.LUBUFU, TB_TILE.LUBUFU, LUBUFU_SPARE_VESSEL, log, LONG_GAP)
    if not (_w5):
        return False
    _result6 = yield from execution.delay_until(lambda: held_id(TB_ID.VESSEL) > 0, 8000)
    return _result6


def meet_tiadeche(log):
    return talk_fully(TB_NPC.TIADECHE, TB_TILE.TIADECHE, TIADECHE_INTRO, log)


def tiadeche_catch(log):
    """Hand him the baited vessel; the "Yes" to his first catch puts the raw Karambwan the poisoned spear needs into the pack."""
    _w7 = yield from use_on_npc(TB_ID.VESSEL_LOADED, TB_NPC.TIADECHE, TB_TILE.TIADECHE, TIADECHE_ACCEPT, log, LONG_GAP)
    if not (_w7):
        return False
    return reader.varp(TB_VARP.TIADECHE) >= TB_TIADECHE.REQUEST_MANUAL


def give_manual(log):
    return use_on_npc(TB_ID.CRAFTING_MANUAL, TB_NPC.TIADECHE, TB_TILE.TIADECHE, [], log, LONG_GAP)


def meet_tinsay(log):
    return talk_fully(TB_NPC.TINSAY, TB_TILE.TINSAY, ['Yes.'], log, LONG_GAP)


def give_tinsay(item_id):
    return lambda log: use_on_npc(item_id, TB_NPC.TINSAY, TB_TILE.TINSAY, [], log, LONG_GAP)


def meet_tamayu(log):
    return talk_fully(TB_NPC.TAMAYU, TB_TILE.TAMAYU, [], log, LONG_GAP)


# Why: the hunt is a cutscene, 6 camera moves in an instance with nothing on the chat interface, then a teleport back beside Tamayu for his verdict.
def hunt_shaikahan(log):
    """Follow Tamayu on a hunt. With 4 doses and a poisoned spear given, this is the kill."""
    return talk_fully(TB_NPC.TAMAYU, TB_TILE.TAMAYU, TAMAYU_HUNT, log, CUTSCENE_GAP)


def give_tamayu(item_id):
    return lambda log: use_on_npc(item_id, TB_NPC.TAMAYU, TB_TILE.TAMAYU, [], log, LONG_GAP)
