"""Ported from rs2b0t's src/bot/api/ai/quests/defs/murder/areas.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.geometry import Tile
from rs2004.quests.engine.types import QuestModule, QuestProgress
from rs2004.quests.data import quest_record

__all__ = ['MURDER_NAME', 'MURDER_OBJ', 'MURDER_LOC', 'MURDER_TILE', 'ARHEIN', 'GUARD_START', 'GUARD_HANDIN', 'SALESMAN', 'SUSPECTS', 'suspect_order', 'MURDER_EVIDENCE']

MURDER_NAME = 'Murder Mystery'
# Why: every floured item renders the same name as its clean form, all 3 threads render "Criminals' thread", and "Pot" has twins, so nothing here is matched by name.
MURDER_OBJ = Record({
    'POT': 1931,
    'POT_FLOUR': 1933,
    'FLYPAPER': 1811,
    'DAGGER': 1813,
    'DAGGER_DUST': 1814,
    'UNKNOWN_PRINT': 1822,
    'KILLERS_PRINT': 1815,
    'THREAD_RED': 1808,
    'THREAD_GREEN': 1809,
    'THREAD_BLUE': 1810,
})
MURDER_LOC = Record({'WINDOW': 2666, 'FLOUR_BARREL': 2662, 'SACKS': 2663})
MURDER_TILE = Record({
    'BANK': Tile(2725, 3491, 0),
    'GUARD': Tile(2741, 3562, 0),
    'STUDY': Tile(2747, 3578, 0),
    'FLOUR_BARREL': Tile(2735, 3581, 0),
    'SACKS': Tile(2732, 3581, 0),
    'SALESMAN': Tile(2737, 3491, 0),
    'ARHEIN': Tile(2803, 3430, 0),
})
ARHEIN = Record({'npc': 'Arhein', 'anchor': MURDER_TILE.ARHEIN})
GUARD_START = Record({'npc': 'Guard', 'anchor': MURDER_TILE.GUARD, 'leash': 8, 'prefer': ["Sure, I'll help"]})
GUARD_HANDIN = Record({'npc': 'Guard', 'anchor': MURDER_TILE.GUARD, 'leash': 8, 'prefer': ['I know who did it']})
SALESMAN = Record({
    'npc': 'Poison Salesman',
    'anchor': MURDER_TILE.SALESMAN,
    'leash': 10,
    'prefer': ['Talk about the Murder Mystery Quest', 'Who did you sell Poison to at the house'],
})
POISON_ASK = ['buy poison the other day']
SUSPECTS = [
    Record({
    'stop': Record({'npc': 'Anna', 'anchor': Tile(2734, 3575, 0), 'leash': 8, 'prefer': POISON_ASK}),
    'barrel': Record({'id': 2656, 'name': "Annas' barrel", 'near': Tile(2734, 3575, 0)}),
    'silver': 1796,
    'dust': 1797,
    'print': 1816,
    'thread': MURDER_OBJ.THREAD_GREEN,
    'poison': Record({'id': 2650, 'name': 'Sinclair family compost heap', 'near': Tile(2732, 3572, 0)}),
}),
    Record({
    'stop': Record({'npc': 'Bob', 'anchor': Tile(2748, 3559, 0), 'leash': 8, 'prefer': POISON_ASK}),
    'barrel': Record({'id': 2657, 'name': "Bobs' barrel", 'near': Tile(2734, 3578, 0)}),
    'silver': 1798,
    'dust': 1799,
    'print': 1817,
    'thread': MURDER_OBJ.THREAD_RED,
    'poison': Record({'id': 2651, 'name': 'Sinclair family beehive', 'near': Tile(2731, 3559, 0)}),
}),
    Record({
    'stop': Record({'npc': 'Carol', 'anchor': Tile(2734, 3581, 1), 'leash': 8, 'prefer': POISON_ASK}),
    'barrel': Record({'id': 2658, 'name': "Carols' barrel", 'near': Tile(2734, 3581, 1)}),
    'silver': 1800,
    'dust': 1801,
    'print': 1818,
    'thread': MURDER_OBJ.THREAD_RED,
    'poison': Record({'id': 2652, 'name': 'Sinclair mansion drain', 'near': Tile(2736, 3572, 0)}),
}),
    Record({
    'stop': Record({'npc': 'David', 'anchor': Tile(2739, 3581, 0), 'leash': 8, 'prefer': POISON_ASK}),
    'barrel': Record({'id': 2659, 'name': "Davids' barrel", 'near': Tile(2734, 3578, 1)}),
    'silver': 1802,
    'dust': 1803,
    'print': 1819,
    'thread': MURDER_OBJ.THREAD_GREEN,
    'poison': Record({'id': 2653, 'name': "Spiders' nest", 'near': Tile(2740, 3575, 1)}),
}),
    Record({
    'stop': Record({'npc': 'Elizabeth', 'anchor': Tile(2746, 3581, 1), 'leash': 8, 'prefer': POISON_ASK}),
    'barrel': Record({'id': 2660, 'name': "Elizabeths' barrel", 'near': Tile(2746, 3581, 1)}),
    'silver': 1804,
    'dust': 1805,
    'print': 1820,
    'thread': MURDER_OBJ.THREAD_BLUE,
    'poison': Record({'id': 2654, 'name': 'Sinclair family fountain', 'near': Tile(2746, 3563, 0)}),
}),
    Record({
    'stop': Record({'npc': 'Frank', 'anchor': Tile(2742, 3577, 0), 'leash': 8, 'prefer': POISON_ASK}),
    'barrel': Record({'id': 2661, 'name': "Franks' barrel", 'near': Tile(2746, 3577, 1)}),
    'silver': 1806,
    'dust': 1807,
    'print': 1821,
    'thread': MURDER_OBJ.THREAD_BLUE,
    'poison': Record({'id': 2655, 'name': 'Sinclair family crest', 'near': Tile(2745, 3573, 0)}),
}),
]


# Why: the window thread is cut from the murderer's own clothes, so its colour halves the field before any print is lifted.
def suspect_order(thread):
    """The 2 whose clothes match the thread, then the rest as a fallback."""
    matched = [s for s in SUSPECTS if s.thread == thread]
    return list(matched) + list([s for s in SUSPECTS if not (s in matched)])


_flat1 = []
for s in SUSPECTS:
    _flat1.extend([
    Record({'id': s.silver, 'name': 'silver keepsake'}),
    Record({'id': s.dust, 'name': 'floured keepsake'}),
    Record({'id': s.print, 'name': 'suspect print'}),
])


MURDER_EVIDENCE = [Record({'id': MURDER_OBJ.DAGGER, 'name': "Criminals' dagger"}), Record({'id': MURDER_OBJ.DAGGER_DUST, 'name': "Criminals' dagger"}), Record({'id': MURDER_OBJ.UNKNOWN_PRINT, 'name': 'Unknown print'}), Record({'id': MURDER_OBJ.KILLERS_PRINT, 'name': "Killers' print"}), Record({'id': MURDER_OBJ.THREAD_RED, 'name': "Criminals' thread"}), Record({'id': MURDER_OBJ.THREAD_GREEN, 'name': "Criminals' thread"}), Record({'id': MURDER_OBJ.THREAD_BLUE, 'name': "Criminals' thread"})] + list(_flat1)
