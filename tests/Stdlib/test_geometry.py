from helpers import raises


def test_tile_distance_is_chebyshev_on_one_level():
    tile = Tile(3200, 3200)
    assert tile.distance_to(Tile(3203, 3201)) == 3
    assert tile.distance_to((3190, 3200)) == 10
    assert tile.distance_to(Tile(3200, 3200, 1)) == 1000000


def test_tile_translate_and_equality():
    tile = Tile(3200, 3200, 1)
    assert tile.translate(2, -1) == Tile(3202, 3199, 1)
    assert tile != Tile(3200, 3200, 0)
    assert tile.equals((3200, 3200, 1))
    assert Tile.from_tile((3200, 3201)) == Tile(3200, 3201, 0)
    assert len({Tile(1, 2), Tile(1, 2), Tile(1, 3)}) == 2
    assert list(tile) == [3200, 3200, 1]


def test_rectangular_area_includes_its_corners_on_its_level():
    area = Area.rectangular(Tile(3210, 3220), (3200, 3215))
    assert area.contains((3200, 3215))
    assert area.contains(Tile(3210, 3220))
    assert area.contains((3205, 3218))
    assert not area.contains((3211, 3218))
    assert not area.contains((3205, 3218, 1))
    for _ in range(20):
        assert area.contains(area.get_random_tile())


def test_circular_area():
    area = Area.circular(Tile(3200, 3200), 3)
    assert area.contains((3203, 3200))
    assert not area.contains((3203, 3203))
    for _ in range(20):
        assert area.contains(area.get_random_tile())


def test_polygon_area_includes_its_edges():
    triangle = Area.polygon([(0, 0), (10, 0), (0, 10)])
    assert triangle.contains((2, 2))
    assert triangle.contains((5, 5))
    assert triangle.contains((0, 7))
    assert not triangle.contains((6, 6))
    assert not triangle.contains((2, 2, 1))
    assert 'at least 3' in raises(ValueError, lambda: Area.polygon([(0, 0), (1, 1)]))
