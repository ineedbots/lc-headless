"""rs2b0t's test/api/ai/clues/kharaziJungle.test.ts, its band case (MIT, see thirdparty/rs2b0t), on spec.py's test
and expect. It plans over the real map, so it runs with the real cache."""

from rs2004.clues.data import CLUE_DB
from rs2004.clues.travel import KHARAZI_CLUES

KHARAZI_IDS = sorted(list(KHARAZI_CLUES))
JUNGLE_LANDING = Tile(2816, 2936, 0)
KARAMJA_MAINLAND = Tile(2946, 3050, 0)


def routes_from(start):
    return [id for id in KHARAZI_IDS if navigator.find_path(start, CLUE_DB[id]['coord'], max_expansions=4000000, policy={'use_teleports': False}).ok]


# Why: the feature rests on the band being the only thing in the way, so both halves are pinned: the map can't route
# in, and once the chop has landed the ordinary walker reaches every dig.
def band_seals():
    expect(routes_from(KARAMJA_MAINLAND)).to_equal([])
    expect(routes_from(JUNGLE_LANDING)).to_equal(KHARAZI_IDS)


test('no dig routes from Karamja, and every one routes from the far side of the band', band_seals)
