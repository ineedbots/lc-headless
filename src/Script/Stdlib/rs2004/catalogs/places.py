"""Places on the map: the altars that restore prayer, the standard teleports, and the essence mine. Ported from
rs2b0t's api/altar/Altars.ts, api/map/Teleport.ts and api/map/regions.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.execution import event_signal
from rs2004.game import skills
from rs2004.geometry import Tile
from rs2004.navigation import navigator
from rs2004.tabs import clean_text

# The Pray-at altars near a bank; no chaos altars.
ALTARS = [
    Record({'name': 'Varrock church', 'tile': Tile(3253, 3486, 0), 'loc': 'Altar'}),
    Record({'name': 'Edgeville Monastery', 'tile': Tile(3051, 3498, 1), 'loc': 'Altar', 'requires': {'skill': {'name': 'prayer', 'level': 31}}}),
    Record({'name': 'Lumbridge church', 'tile': Tile(3243, 3205, 0), 'loc': 'Altar'}),
    Record({'name': 'Port Sarim church', 'tile': Tile(2991, 3177, 0), 'loc': 'Altar'}),
    Record({'name': 'Ardougne church', 'tile': Tile(2617, 3309, 0), 'loc': 'Altar'}),
    Record({'name': 'West Ardougne church', 'tile': Tile(2529, 3286, 0), 'loc': 'Altar'}),
    Record({'name': 'Seers church', 'tile': Tile(2694, 3462, 0), 'loc': 'Altar'}),
    Record({'name': 'Yanille church', 'tile': Tile(2604, 3208, 0), 'loc': 'Altar'}),
    Record({'name': 'Falador church', 'tile': Tile(2925, 3483, 0), 'loc': 'Altar of Guthix'}),
    Record({'name': 'Duel Arena chapel', 'tile': Tile(3376, 3285, 0), 'loc': 'Altar'}),
    Record({'name': 'Canifis temple', 'tile': Tile(3416, 3488, 0), 'loc': 'Altar'}),
]
ALTAR_SEARCH_EXPANSIONS = 500000


def _altar_usable(altar):
    need = altar.requires.skill if altar.requires is not None else None
    return need is None or skills.level(need.name) >= need.level


def nearest_altar(start):
    """The usable altar the shortest route reaches from start, or None, as rs2b0t ranks them by route cost.
    None too when a random event is pending. Not a wait: each route is planned at once."""
    start = Tile.from_tile(start)
    altars = [a for a in ALTARS if _altar_usable(a)]
    altars.sort(key=lambda a: a.tile.distance_to(start))
    best = None
    best_cost = None
    for altar in altars:
        if event_signal.pending():
            return None
        route = navigator.find_path(start, altar.tile, max_expansions=ALTAR_SEARCH_EXPANSIONS, policy={'use_teleports': False})
        if route.ok and (best_cost is None or route.cost < best_cost):
            best = altar
            best_cost = route.cost
    return best


# The standard spellbook's teleports, with the 2004 magic interface's component for each, used only when the
# magic tab has no button whose text names it.
TELEPORTS = {
    'varrock': Record({'name': 'Varrock', 'fallback_com_id': 1164}),
    'lumbridge': Record({'name': 'Lumbridge', 'fallback_com_id': 1167}),
    'falador': Record({'name': 'Falador', 'fallback_com_id': 1170}),
    'camelot': Record({'name': 'Camelot', 'fallback_com_id': 1174}),
    'ardougne': Record({'name': 'Ardougne', 'fallback_com_id': 1540}),
    'watchtower': Record({'name': 'Watchtower', 'fallback_com_id': 1541}),
    'trollheim': Record({'name': 'Trollheim', 'fallback_com_id': 7455}),
}


def _teleport_key(value):
    key = clean_text(value).strip().lower()
    if key.startswith('cast '):
        key = key[5:]
    if key.endswith(' teleport'):
        key = key[:-9]
    return key.strip()


def resolve_teleport(name):
    """The teleport a name means ('Varrock', 'Cast @gre@Varrock teleport'), or None."""
    return TELEPORTS.get(_teleport_key(name))


def teleport_button_text(teleport):
    return f'Cast @gre@{teleport.name} teleport'


def resolve_teleport_component(teleport, find_button):
    """find_button(text) gives a component or -1; the 2004 component when it doesn't find the teleport's."""
    found = find_button(teleport_button_text(teleport))
    return teleport.fallback_com_id if found == -1 else found


def in_ess_mine(x, z):
    """The rune essence mine, where Aubury and the Varrock portal teleport you."""
    return x // 64 == 45 and z // 64 == 75
