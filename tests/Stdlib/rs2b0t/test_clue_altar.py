"""rs2b0t's test/api/ai/clues/nearestAltar.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and
expect, with the route planner patched as rs2b0t spies on it. The baked-map case runs with the real cache in
nav/test_clue_altar_map.py; the queued-worker case isn't ported, as find_path here plans at once rather than queueing
behind a path worker."""

from rs2004.catalogs.places import nearest_altar

LUMBRIDGE = Tile(3243, 3205, 0)
SARIM = Tile(2991, 3177, 0)


def routes(cost, prayer=60):
    asked = []

    def find_path(start, to, **opts):
        asked.append(to)
        value = cost(to)
        return Fake(ok=False, cost=0, reason='unreachable') if value is None else Fake(ok=True, cost=value)

    spy_on(skills, 'level', lambda name: prayer)
    spy_on(event_signal, 'pending', lambda: False)
    spy_on(navigator, 'find_path', find_path)
    return asked


def lumbridge_church():
    routes(lambda to: 25 if to.x == LUMBRIDGE.x else 250)
    altar = nearest_altar(Tile(3222, 3218, 0))
    expect(altar.name).to_be('Lumbridge church')
    expect(altar.tile.equals(LUMBRIDGE)).to_be(True)


def shorter_route():
    routes(lambda to: 80 if to.x == LUMBRIDGE.x else (150 if to.x == SARIM.x else None))
    expect(nearest_altar(Tile(3080, 3180, 0)).tile.equals(LUMBRIDGE)).to_be(True)


def unreachable():
    routes(lambda to: 300 if to.x == SARIM.x else None)
    expect(nearest_altar(LUMBRIDGE).tile.equals(SARIM)).to_be(True)


def none_reachable():
    routes(lambda to: None)
    expect(nearest_altar(LUMBRIDGE)).to_be(None)


def monastery_gated():
    asked = routes(lambda to: 1 if to.level == 1 else (150 if to.x == 3253 else None), 30)
    expect(nearest_altar(Tile(3051, 3498, 0)).name).to_be('Varrock church')
    expect(any([t.level == 1 for t in asked])).to_be(False)


describe('nearest_altar', lambda: [
    test('Lumbridge prayer uses the Lumbridge church', lumbridge_church),
    test('a shorter reachable route wins over straight-line proximity to Port Sarim', shorter_route),
    test('an unreachable altar cannot win on distance', unreachable),
    test('no reachable altar skips the detour', none_reachable),
    test('the upstairs monastery is excluded below 31 prayer', monastery_gated),
])
