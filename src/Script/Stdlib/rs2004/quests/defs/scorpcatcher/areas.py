"""Ported from rs2b0t's src/bot/api/ai/quests/defs/scorpcatcher/areas.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.geometry import Tile
from rs2004.quests.exec.primitives import NpcStop

__all__ = ['SC_STAGE', 'CAGE_ID', 'CAGE_NAME', 'SCORPION_NPC', 'SC_ID', 'SC_ITEM', 'ANTIPOISON_DOSES', 'ANTIPOISON_SHOP', 'ANTIPOISON_GP', 'EVERY_CAGE', 'EVERY_SCORPION', 'SCORPION_LABEL', 'caught_in', 'cage_with', 'SC_TILE', 'THORMAC', 'SEER', 'ABBOT', 'VELRAK', 'JAILER_NPC']

SC_STAGE = Record({'NOT_STARTED': 0, 'STARTED': 1, 'FIRST_HINT': 2, 'SECOND_HINT': 3, 'COMPLETE': 6})
# Why: all 8 cages render "Scorpion cage", so only the obj id says what's inside.
CAGE_ID = Record({'EMPTY': 456, 'A': 457, 'AB': 458, 'AC': 459, 'B': 460, 'BC': 461, 'C': 462, 'FULL': 463})
CAGE_NAME = 'Scorpion cage'
SCORPION_NPC = {'a': 385, 'b': 386, 'c': 387}
SC_ID = Record({
    'DUSTY_KEY': 1590,
    'JAIL_KEY': 1591,
    'SECRET_WALL': 2117,
    'DEEP_GATE': 2623,
    'JAIL_DOOR': 2631,
    'MONASTERY_LADDER': 2641,
})
SC_ITEM = Record({'DUSTY_KEY': 'Dusty key', 'JAIL_KEY': 'Jail key', 'ANTIPOISON': 'Antipoison(3)'})
# Why: 8 `poisonspider` spawns between (2850,9799) and (2876,9806) with `wanderrange=10` cover the coffin corridor and the secret-room wall.
# Why: `poison_severity=27` is 6 damage every 18s for 8 minutes, and `%poison` is `scope=perm` with no transmit, so its opening chat line is the only reading.
# Why: the Karamja general store is the one shop in the content that stocks the cure, so the leg pays a 30gp ferry each way for it.
ANTIPOISON_DOSES = ['Antipoison(3)', 'Antipoison(2)', 'Antipoison(1)']
ANTIPOISON_SHOP = Record({'npc': 'Shop keeper', 'anchor': Tile(2902, 3146, 0)})
ANTIPOISON_GP = 600
CAGE_CONTENTS = {_k: _v for _k, _v in [
    [CAGE_ID.EMPTY, []],
    [CAGE_ID.A, ['a']],
    [CAGE_ID.B, ['b']],
    [CAGE_ID.C, ['c']],
    [CAGE_ID.AB, ['a', 'b']],
    [CAGE_ID.AC, ['a', 'c']],
    [CAGE_ID.BC, ['b', 'c']],
    [CAGE_ID.FULL, ['a', 'b', 'c']],
]}
EVERY_CAGE = list(list(CAGE_CONTENTS.keys()))
# Why: the catch order is the walk: the outpost is next to the Seers, Taverley is on the way back east, and the monastery is the last stop before the tower.
EVERY_SCORPION = ['b', 'a', 'c']
SCORPION_LABEL = {'a': 'Taverley', 'b': 'Barbarian Outpost', 'c': 'monastery'}


def caught_in(cage_id):
    """What a cage of this id is holding."""
    _v1 = CAGE_CONTENTS.get(cage_id)
    return set((_v1 if _v1 is not None else []))


def cage_with(caught):
    """The cage obj holding this set of scorpions and no others."""
    for id, keys in CAGE_CONTENTS.items():
        if len(keys) == len(caught) and all([(key in caught) for key in keys]):
            return id
    return None


SC_TILE = Record({
    'THORMAC': Tile(2702, 3405, 3),
    'SEER': Tile(2702, 3475, 0),
    'OUTPOST_HUT': Tile(2552, 3571, 0),
    'JAIL_DOOR': Tile(2931, 9690, 0),
    'JAIL_CELL': Tile(2931, 9689, 0),
    'VELRAK': Tile(2931, 9685, 0),
    'DEEP_GATE': Tile(2924, 9803, 0),
    'DEEP_DUNGEON': Tile(2923, 9803, 0),
    'SECRET_WALL': Tile(2875, 9799, 0),
    'SECRET_ROOM': Tile(2875, 9798, 0),
    'SCORPION_A': Tile(2877, 9796, 0),
    'ABBOT': Tile(3058, 3482, 0),
    'MONASTERY_LADDER': Tile(3057, 3484, 0),
    'MONASTERY_ROOM': Tile(3058, 3487, 1),
    'BANK': Tile(2946, 3369, 0),
})
# Why: Thormac's first line is the quest offer, his second is the cage, and only the third starts it, so every rung of that chain is in the list.
# Why: "I've lost my cage." comes before the other `thormac_how_goes` option, as that branch is the only way back to a cage the run has dropped.
THORMAC = NpcStop('Thormac', SC_TILE.THORMAC, 6, [
    'What do you need assistance with?',
    'So how would I go about catching them then?',
    'Ok, I will do it then',
    "I've lost my cage.",
    "I've not caught all the scorpions yet.",
])
# Why: The seer has three stage-specific openers; retrying the wrong one only adds another walk to Seers' Village.
SEER = NpcStop('Seer', SC_TILE.SEER, 8, [
    'I need to locate some scorpions.',
    'Where did you say that scorpion was again?',
    'Your friend Thormac sent me to speak to you.',
    'Many greetings.',
])
ABBOT = NpcStop('Abbot Langley', SC_TILE.ABBOT, 8, ['How do I get further into the monastery?', 'Well can I join your order?'])
VELRAK = NpcStop('Velrak the explorer', SC_TILE.VELRAK, 6, ['So... do you know anywhere good to explore?', 'Yes please!'])
JAILER_NPC = 'Jailer'
