"""Ore rocks by type, from the 289 content's rocks.loc. Ported from rs2b0t's data/miningRocks.ts (MIT, see
thirdparty/rs2b0t). Every rock is named "Rocks", so ore and depleted rocks differ only by id."""

# Ore names in tier order, best last.
ROCK_OPTIONS = ['Clay', 'Copper', 'Tin', 'Iron', 'Silver', 'Coal', 'Gold', 'Mithril', 'Adamantite', 'Runite']
ROCK_TYPES = {
    'Clay': [2108, 2109],
    'Copper': [2090, 2091],
    'Tin': [2094, 2095],
    'Iron': [2092, 2093],
    'Silver': [2100, 2101],
    'Coal': [2096, 2097],
    'Gold': [2098, 2099],
    'Mithril': [2102, 2103],
    'Adamantite': [2104, 2105],
    'Runite': [2106, 2107],
}
# Quest-only rocks, kept out of ROCK_OPTIONS so an empty ore choice never falls back to them.
QUEST_ROCK_TYPES = {
    'Blurite': [2110],
    'Limestone': [4027, 4028, 4029],
}
ROCK_TIER_ORDER = ROCK_OPTIONS

# Rocks that explode when mined: the mining random event's gas.
GAS_ROCK_IDS = list(range(2119, 2140))
GAS_ROCK_TICKS = 60
BROKEN_PICKAXE = 'Broken pickaxe'

_TIER_BY_ID = {}
for _tier in range(len(ROCK_TIER_ORDER)):
    for _id in ROCK_TYPES[ROCK_TIER_ORDER[_tier]]:
        _TIER_BY_ID[_id] = _tier


def rock_tier_by_id(id):
    """The rock's tier, higher being better; -1 for an id that isn't an ore rock."""
    return _TIER_BY_ID.get(id, -1)


def resolve_rock_ids(names):
    """The loc ids of the named ores, matched without regard to case; unknown names are skipped."""
    ids = []
    for name in names:
        wanted = name.strip().lower()
        for key in ROCK_OPTIONS:
            if key.lower() == wanted:
                for id in ROCK_TYPES[key]:
                    if id not in ids:
                        ids.append(id)
    return ids
