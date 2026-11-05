"""AccountLevelerTravel.test.ts (rs2b0t, MIT), on the headless walk options and map."""
from bots.account_leveler.bot import AccountLeveler
from bots.account_leveler.travel import leveler_travel_zones
from rs2004.walkgeom import resolve_danger_zones, tile_in_danger_zones


def resolved(value):
    if False:
        yield
    return value


def travel_options(destination, wilderness=True):
    options = []
    def walk(tile, radius=2, attempts=None, timeout_ms=None, avoid_zones=None, log=None):
        options.append(avoid_zones)
        return True
        yield
    spy_on(game, 'tile', returns=Tile(2725, 3492))
    spy_on(traversal, 'walk_resilient', impl=walk)
    bot = AccountLeveler()
    bot._wilderness = wilderness
    assert run_wait(bot._supplies.walk(destination))
    return resolve_danger_zones(options[0], known=[])


def routine():
    zones = travel_options(Tile(3231, 3421))
    assert tile_in_danger_zones(3154, 3924, 0, zones)
    assert tile_in_danger_zones(3100, 10000, 0, zones)


test('routine Leveler travel excludes surface and underground Wilderness even when training there is enabled', routine)


def explicit():
    destination = Tile(3154, 3924)
    allowed = travel_options(destination)
    denied = travel_options(destination, False)
    assert not tile_in_danger_zones(destination.x, destination.z, 0, allowed)
    assert tile_in_danger_zones(destination.x, destination.z, 0, denied)


test('only explicitly enabled Wilderness destinations permit entry', explicit)


def bank_exclusions():
    zones = leveler_travel_zones()
    options = []
    def walk(tile, *args, **kwargs):
        options.append(kwargs.get('avoid_zones'))
        return True
        yield
    spy_on(game, 'tile', returns=Tile(2725, 3492))
    spy_on(locs, 'query', returns=EmptyLocQuery())
    spy_on(bank, 'is_open', returns=False)
    spy_on(bank, 'open_booth', impl=lambda *args: resolved(True))
    spy_on(traversal, 'walk_resilient', impl=walk)
    assert run_wait(banking.open(stand=Tile(3094, 3492), prefer_nearby=False, avoid_zones=zones))
    assert options[0] == zones


class EmptyLocQuery:
    def name(self, value):
        return self
    def where(self, value):
        return self
    def nearest(self):
        return None


test('Banking forwards caller travel exclusions to the bank walk', bank_exclusions)
