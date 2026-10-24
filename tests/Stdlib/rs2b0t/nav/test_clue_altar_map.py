"""rs2b0t's test/api/ai/clues/nearestAltar.test.ts, its baked-map case (MIT, see thirdparty/rs2b0t), on spec.py's
test and expect. It plans over the real map, so it runs with the real cache."""

from rs2004.catalogs.places import nearest_altar


def lumbridge_castle():
    spy_on(skills, 'level', lambda name: 60)
    spy_on(event_signal, 'pending', lambda: False)
    expect(nearest_altar(Tile(3222, 3218, 0)).tile.equals(Tile(3243, 3205, 0))).to_be(True)


test('the baked map routes Lumbridge Castle prayer to Lumbridge church', lumbridge_castle)
