"""JiveDemons' site: rs2b0t's scripts/JiveDemons/sites.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.hunting.sites import TAVERLEY_BLUE, in_box

# Why: the pocket sits behind the dusty-key gate on the far side of the blue lair, so the gate, the key, the bank,
# the escape and the walk out are the blue site's, and only the tiles past the passage are its own.
# Why: the entrance corridor at x 2881..2887 runs between the blue lair and the pocket on the ladder side of the
# gate, so the area is three boxes that meet around it rather than one that would swallow it.
_POCKET = in_box(2850, 2880, 9762, 9797, 0)
_CORRIDOR = in_box(2874, 2899, 9762, 9775, 0)

TAVERLEY_BLACK_DEMON = TAVERLEY_BLUE.with_changes(
    key='taverley-black-demon',
    label='Taverley Dungeon black demons',
    target='Black Demon',
    bones='',
    approach=[Tile(2893, 9790, 0), Tile(2893, 9771, 0), Tile(2875, 9774, 0)],
    safespots=[Tile(2856, 9786, 0), Tile(2857, 9786, 0), Tile(2855, 9786, 0)],
    melee_anchor=Tile(2859, 9786, 0),
    in_area=lambda t: TAVERLEY_BLUE.in_area(t) or _POCKET(t) or _CORRIDOR(t),
)

DEMON_SITES = {TAVERLEY_BLACK_DEMON.key: TAVERLEY_BLACK_DEMON}

SITE_OPTIONS = list(DEMON_SITES.keys())


def site_for(key):
    site = DEMON_SITES.get(key)
    return site if site is not None else TAVERLEY_BLACK_DEMON
