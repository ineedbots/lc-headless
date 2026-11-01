"""Ported from rs2b0t's src/bot/api/ai/quests/defs/grandtree/areas.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.geometry import Tile
from rs2004.quests.exec.primitives import LadderHop

__all__ = ['GT_STAGE', 'GT_OBJ', 'GT_LOC', 'GT_NPC', 'GT_ITEMS', 'GT_TILE', 'GT_PILLARS', 'GT_ROOTS', 'NARNODE_TRANSLATION', 'NARNODE', 'NARNODE_UNDER', 'HAZELMERE', 'GLOUGH', 'CHARLIE', 'ANITA', 'FOREMAN', 'FEMI', 'PILOT', 'GT_HOPS', 'in_caves', 'in_karamja', 'in_stronghold']

GT_STAGE = Record({
    'NOT_STARTED': 0,
    'STARTED': 10,
    'SPOKEN_HAZELMERE': 20,
    'RELAYED_MESSAGE': 30,
    'SPOKEN_GLOUGH': 40,
    'FOUND_PRISONER': 50,
    'SPOKEN_PRISONER': 60,
    'FOUND_JOURNAL': 70,
    'RELEASED_PRISON': 80,
    'OBTAINED_LUMBER_ORDER': 90,
    'CLUE_CHARLIE': 100,
    'FOUND_INVASION_PLANS': 110,
    'GIVEN_TWIGS': 120,
    'UNLOCKED_TRAPDOOR': 130,
    'DEFEATED_BLACK_DEMON': 140,
    'SEARCHING_DACONIA': 150,
    'COMPLETE': 160,
})
# Why: all 4 twigs render "Twigs" and only the id says which pillar each belongs on, so every pack read here is by id.
GT_OBJ = Record({
    'BARK': 783,
    'TRANSLATION_BOOK': 784,
    'JOURNAL': 785,
    'SCROLL': 786,
    'LUMBER_ORDER': 787,
    'KEY': 788,
    'TWIG_T': 789,
    'TWIG_U': 790,
    'TWIG_Z': 791,
    'TWIG_O': 792,
    'DACONIA': 793,
    'INVASION_PLANS': 794,
})
GT_LOC = Record({
    'CUPBOARD_SHUT': 2434,
    'CUPBOARD_OPEN': 2435,
    'CHEST_SHUT': 2436,
    'PILLAR_T': 2440,
    'PILLAR_U': 2441,
    'PILLAR_Z': 2442,
    'PILLAR_O': 2443,
    'TRAPDOOR_SHUT': 2444,
    'CLIMB_TREE': 2447,
    'DOWN_TREE': 2448,
    'ROOT_A': 1985,
    'ROOT_B': 1986,
})
GT_NPC = Record({'BLACK_DEMON': 677})
GT_ITEMS = [
    'bark sample',
    'translation book',
    "hazelmere's scroll",
    'lumber order',
    "glough's journal",
    "glough's key",
    'twigs',
    'invasion plans',
    'daconia rock',
]
GT_TILE = Record({
    'narnode': Tile(2466, 3497, 0),
    'narnode_under': Tile(2464, 9896, 0),
    'hazelmere': Tile(2678, 3086, 1),
    'glough': Tile(2478, 3463, 1),
    'glough_house_foot': Tile(2476, 3464, 0),
    'cupboard_stand': Tile(2477, 3464, 1),
    'chest_stand': Tile(2482, 3463, 1),
    'climb_tree_stand': Tile(2484, 3463, 1),
    'down_tree_stand': Tile(2485, 3465, 2),
    'pillar_floor': Tile(2486, 3465, 2),
    'trapdoor_stand': Tile(2487, 3465, 2),
    'cave_landing': Tile(2491, 9864, 0),
    'cave_ladder': Tile(2463, 9896, 0),
    'charlie': Tile(2465, 3495, 3),
    'jail': Tile(2464, 3496, 3),
    'glider_pad': Tile(2465, 3501, 3),
    'karamja_crash': Tile(2917, 3058, 0),
    'foreman': Tile(2999, 3043, 0),
    'femi': Tile(2460, 3382, 0),
    'femi_landing': Tile(2459, 3409, 0),
    'anita_stairs': Tile(2388, 3512, 0),
    'anita_floor': Tile(2388, 3513, 1),
    'anita': Tile(2390, 3514, 1),
})
GT_PILLARS = [
    Record({'obj': GT_OBJ.TWIG_T, 'loc': GT_LOC.PILLAR_T, 'stand': Tile(2485, 3466, 2)}),
    Record({'obj': GT_OBJ.TWIG_U, 'loc': GT_LOC.PILLAR_U, 'stand': Tile(2486, 3466, 2)}),
    Record({'obj': GT_OBJ.TWIG_Z, 'loc': GT_LOC.PILLAR_Z, 'stand': Tile(2487, 3466, 2)}),
    Record({'obj': GT_OBJ.TWIG_O, 'loc': GT_LOC.PILLAR_O, 'stand': Tile(2488, 3466, 2)}),
]
# Why: `%daconia_rock_root` is `random_range(1,15)` and the client cannot read it, so the rock is found by searching every root.
# Why: each root is a 3x3 that blocks its own footprint, and the stands below are the nearest walkable tile in the caves' own component.
GT_ROOTS = [
    Record({'sw': Tile(2456, 9886, 0), 'stand': Tile(2455, 9885, 0)}),
    Record({'sw': Tile(2457, 9881, 0), 'stand': Tile(2456, 9882, 0)}),
    Record({'sw': Tile(2455, 9874, 0), 'stand': Tile(2454, 9875, 0)}),
    Record({'sw': Tile(2443, 9878, 0), 'stand': Tile(2442, 9877, 0)}),
    Record({'sw': Tile(2439, 9881, 0), 'stand': Tile(2438, 9881, 0)}),
    Record({'sw': Tile(2444, 9893, 0), 'stand': Tile(2443, 9892, 0)}),
    Record({'sw': Tile(2452, 9893, 0), 'stand': Tile(2451, 9892, 0)}),
    Record({'sw': Tile(2465, 9891, 0), 'stand': Tile(2464, 9890, 0)}),
    Record({'sw': Tile(2468, 9890, 0), 'stand': Tile(2467, 9889, 0)}),
    Record({'sw': Tile(2467, 9896, 0), 'stand': Tile(2466, 9895, 0)}),
    Record({'sw': Tile(2473, 9897, 0), 'stand': Tile(2472, 9896, 0)}),
    Record({'sw': Tile(2481, 9904, 0), 'stand': Tile(2480, 9903, 0)}),
    Record({'sw': Tile(2485, 9885, 0), 'stand': Tile(2484, 9884, 0)}),
    Record({'sw': Tile(2490, 9889, 0), 'stand': Tile(2489, 9888, 0)}),
    Record({'sw': Tile(2467, 9872, 0), 'stand': Tile(2466, 9871, 0)}),
]
# Why: the King only accepts the 2nd and 3rd answers in one order, so listing them ahead of "None of the above." picks right on every page.
# Why: the first 2 pages offer none of them and fall through to "None of the above.", which is what `narnode_correct_b2` and `_b3` want.
NARNODE_TRANSLATION = [
    'I think so!',
    "A man came to me with the King's seal.",
    'I gave the man Daconia rocks.',
    'And Daconia rocks will kill the tree!',
    'None of the above.',
]
NARNODE = Record({
    'npc': 'King Narnode Shareen',
    'anchor': GT_TILE.narnode,
    'leash': 6,
    'prefer': ["You seem worried, what's up?", "I'd be happy to help!"] + list(NARNODE_TRANSLATION),
})
NARNODE_UNDER = Record({'npc': 'King Narnode Shareen', 'anchor': GT_TILE.narnode_under, 'leash': 8, 'prefer': []})
HAZELMERE = Record({'npc': 'Hazelmere', 'anchor': GT_TILE.hazelmere, 'leash': 8, 'prefer': []})
GLOUGH = Record({'npc': 'Glough', 'anchor': GT_TILE.glough, 'leash': 8, 'prefer': []})
CHARLIE = Record({'npc': 'Charlie', 'anchor': GT_TILE.charlie, 'leash': 4, 'prefer': []})
ANITA = Record({'npc': 'Anita', 'anchor': GT_TILE.anita, 'leash': 5, 'prefer': []})
# Why: a wrong answer makes the foreman attack, so the list names the 3 `grandtree_foreman_rightans*` lines and nothing else.
FOREMAN = Record({
    'npc': 'Foreman',
    'anchor': GT_TILE.foreman,
    'leash': 10,
    'prefer': ['Sadly his wife is no longer with us!', 'He loves worm holes.', 'Anita.'],
})
# Why: `%femi_help` is 0 until the gate's box-lifting conversation sets it; 0 and 2 ride free, only the 1 branch charges, and the pay option answers that.
FEMI = Record({'npc': 'Femi', 'anchor': GT_TILE.femi, 'leash': 6, 'prefer': ["OK then, I'll pay.", "I'd better get going!"]})
PILOT = Record({'npc': 'Gnome pilot', 'anchor': GT_TILE.glider_pad, 'leash': 6, 'prefer': ['Take me to Karamja please!']})
# Why: `grandtree_trapdoorunder` only opens once the quest is complete, so the only way in is Glough's one-way trapdoor, which the module drives itself.
GT_HOPS = [LadderHop(GT_TILE.cave_ladder, 'Ladder', 'Climb-up', Tile(2463, 3497, 0))]


def in_caves(t):
    return t is not None and t.z >= 9856 and t.z <= 9919


def in_karamja(t):
    """True in the Karamja jungle and the shipyard, on the far side of the glider ride."""
    return t is not None and t.x >= 2850 and t.z <= 3200


def in_stronghold(t):
    """True inside the stronghold walls, which the gate shuts against a spy at stage 90."""
    return t is not None and t.x >= 2370 and t.x <= 2540 and t.z >= 3384 and t.z <= 3540
