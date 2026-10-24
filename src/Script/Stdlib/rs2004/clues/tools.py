"""Where a trail gets its spade, its coordinate trio and the odd extra item: rs2b0t's api/ai/clues/data/toolAcquire.ts
(MIT, see thirdparty/rs2b0t)."""

from rs2004.geometry import Tile
from rs2004.quests.exec.primitives import NpcStop
from rs2004.clues.data import CLUE_DB

SPADE_NAME = 'Spade'
TRIO = ['Sextant', 'Watch', 'Chart']


def trail_kit(scroll_id):
    """The tools a trail with this scroll may want: the spade, the trio, and the row's own items."""
    if scroll_id is None:
        return []
    row = CLUE_DB.get(scroll_id) or {}
    return [SPADE_NAME] + TRIO + list(row.get('items') or [])


SPADE_SPAWNS = [Tile(2574, 3331, 0), Tile(2981, 3369, 0)]


def next_coord_tool(sextant, watch, chart):
    """The first of the trio not yet held: 'sextant', 'watch', 'chart', or None."""
    if not sextant:
        return 'sextant'
    if not watch:
        return 'watch'
    if not chart:
        return 'chart'
    return None


PROFESSOR = NpcStop('Observatory professor', Tile(2438, 3186, 0), 10, ['Treasure Trails', 'lost', 'navigation', 'sextant', 'watch'])
MURPHY = NpcStop('Murphy', Tile(2668, 3162, 0), 10, ['sextant', 'lost'])
KOJO = NpcStop('Brother Kojo', Tile(2569, 3249, 0), 10, ['watch', 'lost'])
KOJO_EXIT = Tile(2576, 3250, 0)


class ShopSource:
    """A counter that sells something a trail needs, with rough coins a unit, so a caller can say why it
    couldn't buy."""

    def __init__(self, npc, stand, cost):
        self.npc = npc
        self.stand = stand
        self.cost = cost


# Why: a trail that rolls an items row mustn't be abandoned for want of an 18gp purchase; only rows carrying
# items reach this, today Rope (2811, Baxtorian Falls), from Aemad's counter in East Ardougne.
_EXTRA_ITEM_SHOPS = {'rope': ShopSource('Aemad', Tile(2613, 3294, 0), 18)}

# Why: the Kharidian desert has one baked entrance and it eats a Shantay pass, so without one the desert leaves the
# graph; Shantay stocks the pass himself, north of his own gate, so the trip is payable from the side the bot is on.
_GATE_ITEM_SHOPS = {'shantay pass': ShopSource('Shantay', Tile(3304, 3122, 0), 5)}


def extra_item_shop(name):
    return _EXTRA_ITEM_SHOPS.get(name.strip().lower())


def gate_item_shop(name):
    return _GATE_ITEM_SHOPS.get(name.strip().lower())
