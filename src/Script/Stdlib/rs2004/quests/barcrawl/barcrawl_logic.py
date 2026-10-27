"""Ported from rs2b0t's src/bot/api/ai/quests/barcrawl/BarcrawlLogic.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record

from rs2004.geometry import Tile
from rs2004.quests.journal_text import normalize_journal

__all__ = ['COINS_ID', 'BARCRAWL_CARD', 'COINS', 'BARS', 'BARCRAWL_GP', 'BARBARIAN_GUARD_ID', 'GUARD_TILE', 'GUARD_PREFER', 'BAR_PREFER', 'TOO_DRUNK', 'GATE_IS_OPEN', 'parse_card', 'next_bar']

# Why: Alfred Grimhand's Barcrawl is a miniquest of its own and the only way past the Barbarian Outpost gate, so its data and card parsing live here, outside the one quest that needs it.
# Why: {@link RunBarcrawl} drives it, and scripts and quest modules both call that.
# Why: `%barcrawl` is `scope=perm` with no transmit, so which bars are signed isn't on the wire.
# Why: the card's Read op is the oracle: it renders one green/red line per bar into a scroll modal, same shape as a quest journal.
COINS_ID = 995
BARCRAWL_CARD = 'Barcrawl card'
COINS = 'Coins'
BARS = [
    Record({'id': 734, 'npc': 'Bartender', 'tile': Tile(3045, 3258, 0), 'line': 'rusty anchor', 'gp': 8}),
    Record({'id': 736, 'npc': 'Barmaid', 'tile': Tile(2957, 3371, 0), 'line': 'rising sun', 'gp': 70}),
    Record({'id': 733, 'npc': 'Bartender', 'tile': Tile(3226, 3400, 0), 'line': 'bluemoon', 'gp': 50}),
    Record({'id': 731, 'npc': 'Bartender', 'tile': Tile(3276, 3488, 0), 'line': 'jolly boar', 'gp': 10}),
    Record({'id': 737, 'npc': 'Bartender', 'tile': Tile(2690, 3494, 0), 'line': 'foresters arms', 'gp': 18}),
    Record({'id': 738, 'npc': 'Bartender', 'tile': Tile(2575, 3321, 0), 'line': 'flying horse', 'gp': 8}),
    Record({'id': 739, 'npc': 'Bartender', 'tile': Tile(2556, 3079, 0), 'line': 'dragon inn', 'gp': 12}),
    Record({'id': 848, 'npc': 'Blurberry', 'tile': Tile(2480, 3490, 1), 'line': "blurberry's bar", 'gp': 10}),
    Record({'id': 568, 'npc': 'Zambo', 'tile': Tile(2924, 3143, 0), 'line': 'karamja spirits', 'gp': 7}),
    Record({'id': 735, 'npc': 'Bartender', 'tile': Tile(2796, 3155, 0), 'line': "dead man's chest", 'gp': 15}),
]
BARCRAWL_GP = sum([bar.gp for bar in BARS]) + 200
BARBARIAN_GUARD_ID = 384
GUARD_TILE = Tile(2544, 3572, 0)
GUARD_PREFER = ['I want to come through this gate.', 'Looks can be deceiving, I am in fact a barbarian.']
BAR_PREFER = ['Alfred Grimhand', 'Barcrawl', 'Yes']

TOO_DRUNK = 'too drunk to be able to read'

GATE_IS_OPEN = 'ello friend'


def normalise(lines):
    return normalize_journal(lines)


def parse_card(lines):
    """Which bars are still red. "Completed!" and "Not Completed..." both contain the happy word, so each line is matched on its negation."""
    text = normalise(lines)
    if not ('barcrawl' in text):
        return None

    remaining = []
    for bar in BARS:
        at = text.find(bar.line)
        if at == -1 or 'not completed' in text[at:at + len(bar.line) + 24]:
            remaining.append(bar)
    return Record({'remaining': remaining, 'done': len(remaining) == 0})


def next_bar(remaining, here):
    """Nearest-first, so the tour is a rough loop."""
    if not here:
        return (remaining or [None])[0]
    return (sorted(list(remaining), key=lambda a: a.tile.distance_to(here)) or [None])[0]
