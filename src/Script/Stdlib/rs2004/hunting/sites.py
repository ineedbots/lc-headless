"""The dragon sites: their gates, fees, stands and exits. Ported from rs2b0t's api/combat/hunting/sites.ts (MIT, see
thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.geometry import Tile

__all__ = [
    'DragonSite', 'DragonStand', 'in_box', 'TAVERLEY_BLUE', 'TAVERLEY_BLACK', 'HEROES_BLUE', 'GUTANOTH_BLUE', 'BRIMHAVEN_IRON',
    'BRIMHAVEN_STEEL', 'DRAGON_SITES', 'STAND_SITE_KEYS', 'MAX_STANDS', 'needs_shield', 'SITE_OPTIONS', 'ENCLAVE_TARGET_OPTIONS',
    'enclave_targets', 'hunt_names', 'stand_for', 'site_for',
]


class DragonStand:
    """One numbered place to fight from: the tiles the ladder rotates between, and the tile melee uses.
    label says which dragon it looks at, for the log."""

    def __init__(self, label, tiles, anchor):
        self.label = label
        self.tiles = tiles
        self.anchor = anchor

    def __repr__(self):
        return f'DragonStand({repr(self.label)})'


class DragonSite:
    """A place to hunt. Each field is rs2b0t's, in snake_case; those it marks optional default to None:

    - gate: a door the key opens, a Record of loc_id, op, outside and inside.
    - talk_gate: a way in that's a conversation, a Record of npc, op, choose (the option that gets you past)
      and stand.
    - fee_gate: a way in that costs coins at an npc before a loc op teleports inside: npc, op, coins, stand,
      entrance (loc_id and op), and paid_line and prepaid_line, the text the payment prints and the text a
      second Pay gets when it's already paid.
    - exit: a way out that's a loc op, not the walk back: loc_id, op and stand.
    - stands: numbered DragonStands to choose between; safespots and melee_anchor are the first of them.
    - escape_teleport_id: a teleport id from the walker's catalog, never a copied rune list; walk_out is where
      to walk when it won't fire.
    - ranged_threat: the target hits the safespot from range, so hp lost there isn't the tile being wrong.
    - loot_setting: the setting holding this site's loot choices, 'loot' when None.
    - food: the food when the loadout names none. antipoison: the route in is worth a Superantipoison.
    - also_hunt: other npcs worth killing from the same stand, taken only when the target isn't up.
    - fire_at_range: the target breathes at range, so every style wears the shield and range is refused.
    - antifire: the trip carries Antifire potions. coins: carried per trip, for fees and fares. axe: the walk
      in chops vines. food_per_trip: the food a trip carries while the setting sits on its default.
    - in_area(tile): whether a tile is inside the site."""

    def __init__(self, key=None, label=None, target=None, bones=None, key_item=None, gate=None, approach=None, safespots=None,
                 melee_anchor=None, bank=None, escape_teleport_id=None, walk_out=None, ranged_threat=None, loot_setting=None, food=None,
                 antipoison=None, talk_gate=None, exit=None, stands=None, also_hunt=None, fee_gate=None, fire_at_range=None, antifire=None,
                 coins=None, axe=None, food_per_trip=None, in_area=None):
        self.key = key
        self.label = label
        self.target = target
        self.bones = bones
        self.key_item = key_item
        self.gate = gate
        self.approach = approach if approach is not None else []
        self.safespots = safespots if safespots is not None else []
        self.melee_anchor = melee_anchor
        self.bank = bank
        self.escape_teleport_id = escape_teleport_id
        self.walk_out = walk_out
        self.ranged_threat = ranged_threat
        self.loot_setting = loot_setting
        self.food = food
        self.antipoison = antipoison
        self.talk_gate = talk_gate
        self.exit = exit
        self.stands = stands
        self.also_hunt = also_hunt
        self.fee_gate = fee_gate
        self.fire_at_range = fire_at_range
        self.antifire = antifire
        self.coins = coins
        self.axe = axe
        self.food_per_trip = food_per_trip
        self._in_area = in_area

    def in_area(self, tile):
        return self._in_area is not None and self._in_area(tile)

    def with_changes(self, **changes):
        """A copy with the given fields changed, as rs2b0t's { ...site, field } does."""
        fields = {}
        for name in _SITE_FIELDS:
            fields[name] = getattr(self, name)
        fields['in_area'] = self._in_area
        for key, value in changes.items():
            fields[key] = value
        return DragonSite(**fields)

    def __repr__(self):
        return f'DragonSite({repr(self.key)})'


_SITE_FIELDS = [
    'key', 'label', 'target', 'bones', 'key_item', 'gate', 'approach', 'safespots', 'melee_anchor', 'bank', 'escape_teleport_id', 'walk_out',
    'ranged_threat', 'loot_setting', 'food', 'antipoison', 'talk_gate', 'exit', 'stands', 'also_hunt', 'fee_gate', 'fire_at_range', 'antifire',
    'coins', 'axe', 'food_per_trip',
]


def in_box(min_x, max_x, min_z, max_z, level):
    """A tile test for a box on one level."""
    return lambda t: t is not None and t.level == level and t.x >= min_x and t.x <= max_x and t.z >= min_z and t.z <= max_z


TAVERLEY_BLUE = DragonSite(
    key='taverley-blue',
    label='Taverley Dungeon blue dragons',
    target='Blue dragon',
    bones='Dragon bones',
    key_item=Record({'name': 'Dusty key', 'id': 1590}),
    gate=Record({'loc_id': 2623, 'op': 'Open', 'outside': Tile(2924, 9803, 0), 'inside': Tile(2923, 9803, 0)}),
    approach=[Tile(2911, 9809, 0)],
    safespots=[Tile(2901, 9809, 0), Tile(2904, 9808, 0), Tile(2901, 9810, 0)],
    melee_anchor=Tile(2900, 9808, 0),
    bank=Tile(2946, 3369, 0),
    escape_teleport_id='falador',
    walk_out=Tile(2884, 3398, 0),
    # Why: the entrance corridor runs up the same z band as the lair with a strip of rock between, so a radius
    # reads the way in as the way through.
    in_area=in_box(2888, 2923, 9769, 9816, 0),
)

# Why: a second site is an entry here plus four code changes, none of which this table can carry. supply hard-codes
# Velrak's jail, and DragonSite has no field saying where a key comes from. JiveDragons builds the loot options
# from the drop table at load, because a setting's options are a fixed list. The safespot1..3 settings only reach
# the first three tiles of safespots, and they're shared by every site rather than kept per site.

# Why: the black dragons sit deeper on the same side of the dusty-key gate as the blue lair, so the gate, the key,
# the bank, the escape and the walk-out are the blue site's, and only the room and the walk to it are its own.
# Why: the way there runs south out of the blue lair, west through the demon square and north into the room, so
# the area is the blue box plus that passage plus the room; a single box would swallow half the dungeon.
_BLACK_ROOM = in_box(2818, 2850, 9815, 9832, 0)
_BLACK_PASSAGE = in_box(2835, 2896, 9762, 9820, 0)

TAVERLEY_BLACK = TAVERLEY_BLUE.with_changes(
    key='taverley-black',
    label='Taverley Dungeon black dragons',
    target='Black dragon',
    loot_setting='loot_black',
    food='Shark',
    antipoison=True,
    # Why: the walk in passes the poison spiders at (2871,9792) and (2870,9799), which is what the
    # Superantipoison is for.
    approach=[Tile(2893, 9790, 0), Tile(2882, 9768, 0), Tile(2860, 9803, 0), Tile(2845, 9815, 0)],
    # Why: derived by rs2b0t's tools/nav/jive-safespots.ts --target black. The corridor south of the room is the
    # only cluster the walk in reaches without crossing tiles a dragon stands on.
    safespots=[Tile(2836, 9817, 0), Tile(2835, 9817, 0), Tile(2834, 9817, 0)],
    melee_anchor=Tile(2835, 9818, 0),
    in_area=lambda t: TAVERLEY_BLUE.in_area(t) or _BLACK_ROOM(t) or _BLACK_PASSAGE(t),
)

# Why: the lone adult is penned behind railing and spearwall, both `blockrange=no`, so a spell crosses the fence and
# the dragon never crosses back. Its own gate at (2909, 9910) is what the loot walk opens, and npcs don't open gates,
# so leaving it open doesn't widen the wander.
# Why: derived by jive-safespots.ts --target heroes, which rebuilds collision off the engine's loc configs. rs2b0t's
# pack bakes only the walking wall layer, reads the railing as opaque and derives no safespot here at all.
HEROES_BLUE = DragonSite(
    key='heroes-blue',
    label="Heroes' Guild blue dragon",
    target='Blue dragon',
    bones='Dragon bones',
    # Why: the cellar ladder is a transport the graph already carries, so the walk in only needs its landing named;
    # the fight loop takes the rest.
    approach=[Tile(2892, 9908, 0)],
    safespots=[Tile(2905, 9909, 0), Tile(2906, 9911, 0), Tile(2907, 9911, 0)],
    melee_anchor=Tile(2909, 9910, 0),
    bank=TAVERLEY_BLUE.bank,
    escape_teleport_id=TAVERLEY_BLUE.escape_teleport_id,
    # Why: outside the guild doors, one east of Achietties, so the walk out proves the doors opened before the bank
    # leg starts.
    walk_out=Tile(2904, 3510, 0),
    # Why: the cellar is its own region behind one ladder, so a single box bounds it.
    in_area=in_box(2886, 2942, 9883, 9917, 0),
)

# Why: the six spawns share the cave with ten spiders, six shamans, six chieftains and five greater demons, none of
# which the safespot deriver models, so every stand comes off jive-safespots.ts --target gutanoth, cross-referenced
# against those spawn tiles: each is a derived safespot, at least five tiles off the nearest of them, with
# neighbours to rotate onto, seeing as much of one dragon's wander as the cave allows.
# Why: a stand is chosen for how much of a dragon's wander it sees, not for seeing one dragon and no other.
# Requiring that first left the south dragon a stand that saw 11% of it, and a live run there took no kills in
# twenty minutes.
# Why: stand 1 is the proven one and stays first, at 79% of its dragon and ten tiles clear.
_GUTANOTH_STANDS = [
    DragonStand('the north dragon at 2590,9461', [Tile(2585, 9468, 0), Tile(2586, 9468, 0), Tile(2584, 9468, 0)], Tile(2588, 9468, 0)),
    DragonStand('the west dragon at 2568,9437', [Tile(2573, 9429, 0), Tile(2572, 9429, 0), Tile(2574, 9429, 0)], Tile(2574, 9430, 0)),
    DragonStand('the north-west dragon at 2579,9445', [Tile(2587, 9449, 0), Tile(2586, 9447, 0), Tile(2587, 9447, 0)], Tile(2586, 9449, 0)),
    DragonStand('the south dragon at 2592,9431', [Tile(2591, 9423, 0), Tile(2590, 9423, 0), Tile(2591, 9422, 0)], Tile(2597, 9426, 0)),
    DragonStand('the east dragon at 2604,9443', [Tile(2611, 9441, 0), Tile(2611, 9442, 0), Tile(2610, 9442, 0)], Tile(2610, 9441, 0)),
    DragonStand('the far east dragon at 2609,9459', [Tile(2604, 9466, 0), Tile(2603, 9464, 0), Tile(2603, 9465, 0)], Tile(2606, 9466, 0)),
]

GUTANOTH_BLUE = DragonSite(
    key='gutanoth-blue',
    label="Gu'Tanoth Enclave blue dragons",
    target='Blue dragon',
    bones='Dragon bones',
    # Why: `[opnpc1,enclave_guard]` runs `@enter_skavid_cave` on the first option once Watch Tower is complete,
    # the guard being distracted; without the quest it wants a Nightshade, and this site needs the quest anyway.
    talk_gate=Record({'npc': 'Enclave guard', 'op': 'Talk-to', 'choose': 'I want to go in there', 'stand': Tile(2508, 3038, 0)}),
    # Why: `p_teleport(0_40_147_28_2)` drops you at the south end, so the approach is the walk up the middle of the
    # cave and the fight loop takes it from wherever the chosen stand is.
    approach=[Tile(2588, 9432, 0)],
    stands=_GUTANOTH_STANDS,
    safespots=_GUTANOTH_STANDS[0].tiles,
    melee_anchor=_GUTANOTH_STANDS[0].anchor,
    # Why: `[oploc1,enclavecave]` teleports to (2540,3054) on the Gu'Tanoth hillside, thirteen tiles east of the
    # stand.
    exit=Record({'loc_id': 2813, 'op': 'Enter', 'stand': Tile(2597, 9468, 0)}),
    bank=Tile(2612, 3092, 0),
    # Why: the Watchtower spell needs the quest this site already needs, and lands two ladders and 111 tiles from
    # the Yanille bank; every other spell lands further.
    escape_teleport_id='watchtower',
    walk_out=Tile(2540, 3054, 0),
    food='Shark',
    # Why: the cave's greater demons can't be camped, since the four in the east chamber wander into one shared body
    # with no tile that sees one out of another's reach; the fifth stands within a cast of stand 1, so it's filler.
    also_hunt=['Greater demon'],
    loot_setting='loot_enclave',
    # Why: the stand is melee-proof but nothing in the cave is range-proof, and a live soak took 8 and 13 off it
    # with one adult up, so a hit here is the room, not the tile being wrong, and the ladder mustn't rotate off.
    ranged_threat=True,
    in_area=in_box(2560, 2623, 9408, 9471, 0),
)

# Why: the dungeon is nine pockets joined by vines, stepping stones, a log and a pipe, all edges in transports.json,
# and the landing is sealed from everything else; the box covers it all, so the walk in from the landing is a walk
# to the stand and never a second payment.
_BRIMHAVEN_DUNGEON = in_box(2624, 2751, 9408, 9599, 0)

# Why: derived by jive-safespots.ts --target iron --anywhere. A metal dragon parks at ten tiles and breathes, and
# the shield with an Antifire dose makes that 0, so the stand isn't a melee-proof pocket but the open tile that sees
# the most dragons. A camp still keeps out of every idle wander footprint and the tile beside it, since a dragon
# that wanders adjacent headbutts for fifteen a hit. Camp 1 sees the dragon at (2739,9450) over two thirds of its
# wander and camp 2 the south-west one, both on the room's edge and clear of the wild dogs, black demons and bronze
# dragons on the north side.
_BRIMHAVEN_IRON_STANDS = [
    DragonStand('the north-east corner from 2744,9457', [Tile(2744, 9457, 0), Tile(2743, 9457, 0), Tile(2744, 9458, 0)], Tile(2744, 9457, 0)),
    DragonStand('the south-west from 2704,9417', [Tile(2704, 9417, 0), Tile(2703, 9417, 0), Tile(2705, 9417, 0)], Tile(2704, 9417, 0)),
]

# Why: every steel spawn sits among iron wander boxes, so the one camp outside all of them sees the west steel
# dragon at half its wander and an iron beside it, which the filler rule finishes when it bites.
_BRIMHAVEN_STEEL_STANDS = [
    DragonStand('the west dragon from 2698,9440', [Tile(2698, 9440, 0), Tile(2698, 9439, 0), Tile(2697, 9441, 0)], Tile(2698, 9440, 0)),
]

# Why: the walk in is the landing pocket to the pipe, one obstacle a stop, so a leg that fails retries its own
# crossing rather than every crossing.
_BRIMHAVEN_APPROACH = [Tile(2691, 9564, 0), Tile(2649, 9562, 0), Tile(2672, 9499, 0), Tile(2682, 9506, 0), Tile(2698, 9500, 0), Tile(2698, 9492, 0)]

# Why: the Ardougne teleport lands twenty tiles from the east bank and the ferry to Brimhaven leaves from beside it,
# so the trip is spell, booth, fare, Saniboch, fare again; Falador is two boats further.
BRIMHAVEN_IRON = DragonSite(
    key='brimhaven-iron',
    label='Brimhaven Dungeon iron dragons',
    target='Iron dragon',
    bones='Dragon bones',
    fee_gate=Record({
        'npc': 'Saniboch',
        'op': 'Pay',
        'coins': 875,
        'stand': Tile(2747, 3152, 0),
        'entrance': {'loc_id': 5083, 'op': 'Enter'},
        'paid_line': 'you pay saniboch 875 coins',
        'prepaid_line': 'already given me lots of nice coins',
    }),
    approach=_BRIMHAVEN_APPROACH,
    stands=_BRIMHAVEN_IRON_STANDS,
    safespots=_BRIMHAVEN_IRON_STANDS[0].tiles,
    melee_anchor=_BRIMHAVEN_IRON_STANDS[0].anchor,
    # Why: `[oploc1,karam_dungeon_exit]` teleports to the tile beside Saniboch, and the loc is a wall piece on the
    # landing's east side.
    exit=Record({'loc_id': 5084, 'op': 'leave', 'stand': Tile(2713, 9564, 0)}),
    bank=Tile(2655, 3283, 0),
    escape_teleport_id='ardougne',
    walk_out=Tile(2745, 3152, 0),
    food='Shark',
    food_per_trip=8,
    loot_setting='loot_iron',
    # Why: losing a metal dragon's aggro is hard, so whichever of the two kinds is biting gets finished, and auto
    # retaliate stays on for it.
    also_hunt=['Steel dragon'],
    fire_at_range=True,
    ranged_threat=True,
    antifire=True,
    # Why: 875 for Saniboch and 30 each way on the ferry, with a margin for a pile the run leaves behind.
    coins=1000,
    axe=True,
    in_area=_BRIMHAVEN_DUNGEON,
)

BRIMHAVEN_STEEL = BRIMHAVEN_IRON.with_changes(
    key='brimhaven-steel',
    label='Brimhaven Dungeon steel dragons',
    target='Steel dragon',
    stands=_BRIMHAVEN_STEEL_STANDS,
    safespots=_BRIMHAVEN_STEEL_STANDS[0].tiles,
    melee_anchor=_BRIMHAVEN_STEEL_STANDS[0].anchor,
    also_hunt=['Iron dragon'],
    loot_setting='loot_steel',
)

DRAGON_SITES = {}
for _site in [TAVERLEY_BLUE, TAVERLEY_BLACK, HEROES_BLUE, GUTANOTH_BLUE, BRIMHAVEN_IRON, BRIMHAVEN_STEEL]:
    DRAGON_SITES[_site.key] = _site


def _stand_count(site):
    return len(site.stands) if site.stands is not None else 0


# Every site whose stands are numbered, for the stand setting.
STAND_SITE_KEYS = [s.key for s in DRAGON_SITES.values() if _stand_count(s) > 1]

# The most stands any site carries.
MAX_STANDS = max([_stand_count(s) if s.stands is not None else 1 for s in DRAGON_SITES.values()])


def needs_shield(site, style):
    """Whether the run wears the Dragonfire shield: always for melee, and on a site that breathes at range for
    every style."""
    return style == 'melee' or site.fire_at_range == True


SITE_OPTIONS = list(DRAGON_SITES.keys())

ENCLAVE_TARGET_OPTIONS = ['both', 'dragons', 'demons']


def enclave_targets(site, mode='both'):
    """The Enclave's targets for its target setting; any other site as it is."""
    if site.key != GUTANOTH_BLUE.key:
        return site
    if mode == 'demons':
        return site.with_changes(target='Greater demon', bones='Ashes', also_hunt=None)
    return site.with_changes(target='Blue dragon', bones='Dragon bones', also_hunt=None if mode == 'dragons' else ['Greater demon'])


# Why: the target comes first, so a caller that wants one thing to hunt takes the head and a caller that wants
# everything takes the lot.
def hunt_names(site):
    """Every npc name this site kills: its target, then anything it fills downtime with."""
    return [site.target] + list(site.also_hunt if site.also_hunt is not None else [])


# Why: a site with no stands keeps behaving as it always did, and a number past the end clamps rather than throwing
# on a settings typo.
def stand_for(site, n):
    """The numbered stand to fight from, 1-based; the site's own tiles when it names none."""
    stands = site.stands
    if not stands:
        return DragonStand(site.label, list(site.safespots), site.melee_anchor)
    whole = int(n) if n else 1
    i = min(max(1, whole if whole else 1), len(stands)) - 1
    return stands[i]


def site_for(key):
    site = DRAGON_SITES.get(key)
    return site if site is not None else TAVERLEY_BLUE
