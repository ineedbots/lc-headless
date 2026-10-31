"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/lostcity-combat.test.ts (MIT, see thirdparty/rs2b0t).

rs2b0t's fixture keeps the fight in closure variables its stubs reassign; here a TreeSpiritWorld holds them, and the
facades are patched to its methods for the test."""

from rs2004 import execution
from rs2004.catalogs.tasks import sustain
from rs2004.entities import npcs
from rs2004.execution import event_signal
from rs2004.game import direct_navigator, game, skills
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.quests.defs.lostcity_combat import defeat_tree_spirit, highest_lost_city_strike
from rs2004.traversal import traversal


def stocked(name):
    return 1000


def selects(magic, spell):
    def run():
        expect(highest_lost_city_strike(magic, stocked)).to_be(spell)
    return run


for magic, spell in [[0, None], [1, 'Wind Strike'], [4, 'Wind Strike'], [5, 'Water Strike'], [8, 'Water Strike'], [9, 'Earth Strike'], [12, 'Earth Strike'], [13, 'Fire Strike'], [99, 'Fire Strike']]:
    test(f'Magic {magic} selects {spell} from stocked Strike runes', selects(magic, spell))


def falls_back():
    runes = {'Mind rune': 10, 'Air rune': 10, 'Fire rune': 3, 'Earth rune': 2, 'Water rune': 1}

    def count(name):
        return runes.get(name, 0)

    for name, element in [['Fire Strike', 'Fire rune'], ['Earth Strike', 'Earth rune'], ['Water Strike', 'Water rune'], ['Wind Strike', 'Air rune']]:
        expect(highest_lost_city_strike(99, count)).to_be(name)
        runes[element] = 0
    expect(highest_lost_city_strike(99, count)).to_be_null()


test('falls back through available Strike runes without selecting stronger spell families', falls_back)

SAFE = Tile(2859, 9731, 0)


class FakeSpirit:
    def __init__(self):
        self.id = 655
        self.index = 7
        self.name = 'Tree spirit'
        self.health = 85
        self.max_health = 85
        self.network_x = 2859

    def tile(self):
        return Tile(self.network_x, 9733, 0)

    def network_tile(self):
        return Tile(self.network_x, 9733, 0)

    def targets_another_player(self):
        return False


class TreeSpiritWorld:
    """The fight's state, which the patched facades read and change."""

    def __init__(self, options):
        self.o = options
        self.here = None if options.get('missing_tile') else (Tile(2860, 9733, 0) if options.get('displaced') else SAFE)
        self.runes = {k: v for k, v in options.get('runes', {'Mind rune': 2, 'Air rune': 3, 'Fire rune': 3}).items()}
        self.cast = []
        self.walks = []
        self.logs = []
        self.alive = True
        self.retaliate = True
        self.ticks = 0
        self.melee = 0
        self.npc = FakeSpirit()

    def tile(self):
        return self.here

    def auto_retaliate_on(self):
        return self.retaliate

    def set_auto_retaliate(self, on):
        self.retaliate = on
        return True

    def cast_on_npc(self, spell, target):
        expect(self.here).to_equal(SAFE)
        expect(self.retaliate).to_be(False)
        self.cast.append(spell)
        if self.o.get('refuses'):
            return False
        if self.o.get('no_consumption'):
            return True
        self.runes['Mind rune'] = self.runes.get('Mind rune', 0) - 1
        self.runes['Air rune'] = self.runes.get('Air rune', 0) - (2 if spell == 'Fire Strike' else 1)
        if spell == 'Fire Strike':
            self.runes['Fire rune'] = self.runes.get('Fire rune', 0) - 3
        if len(self.cast) >= self.o.get('win_after', 2):
            self.alive = False
            self.npc.health = 0
        return True

    def all_npcs(self):
        return [self.npc] if self.alive or self.o.get('corpse') else []

    def count(self, name):
        return self.runes.get(name, 0)

    def pending(self):
        return bool(self.o.get('event')) or (bool(self.o.get('event_after_cast')) and len(self.cast) > 0)

    def delay_ticks(self, n=1):
        self.ticks += 1
        if self.ticks > 100:
            raise RuntimeError('fight did not settle')
        if self.o.get('drift_after_cast') and len(self.cast) > 0:
            self.npc.network_x = 2860
        return None
        yield

    def delay_until_ticks(self, check, ticks=1):
        return check()
        yield

    def walk_resilient(self, tile, radius=None, attempts=None, timeout_ms=None, log=None):
        self.walks.append(tile)
        return False
        yield

    def walk(self, tile, run=False):
        self.walks.append(tile)
        self.here = tile
        return True

    def complete(self):
        return not self.alive and self.o.get('credit') != False
        yield


def fight_fixture(**options):
    world = TreeSpiritWorld(options)
    spy_on(game, 'tile', world.tile)
    spy_on(game, 'auto_retaliate_on', world.auto_retaliate_on)
    spy_on(game, 'set_auto_retaliate', world.set_auto_retaliate)
    spy_on(game, 'cast_on_npc', world.cast_on_npc)
    spy_on(npcs, 'all', world.all_npcs)
    spy_on(inventory, 'count', world.count)
    spy_on(skills, 'effective', lambda name: 13)
    spy_on(sustain, 'run', instant_ticks)
    spy_on(event_signal, 'pending', world.pending)
    patch(execution, 'delay_ticks', world.delay_ticks)
    patch(execution, 'delay_until_ticks', world.delay_until_ticks)
    spy_on(traversal, 'walk_resilient', world.walk_resilient)
    spy_on(direct_navigator, 'walk', world.walk)
    world.won = yield from defeat_tree_spirit(lambda message: world.logs.append(message), world.complete)
    return world


def _fights():
    def _casts():
        result = yield from fight_fixture()
        expect(result.won).to_be(True)
        expect(result.cast).to_equal(['Fire Strike', 'Wind Strike'])
        expect(result.melee).to_be(0)
        expect(result.walks).to_equal([])
    test('casts strongest remaining Strike from cover and confirms quest credit', _casts)

    def _exhaustion():
        result = yield from fight_fixture(runes={'Mind rune': 1, 'Air rune': 2, 'Fire rune': 3}, win_after=2)
        expect(result.won).to_be(False)
        expect(result.cast).to_equal(['Fire Strike'])
        expect(result.melee).to_be(0)
        expect(result.walks).to_equal([])
        expect(result.retaliate).to_be(False)
        expect(' '.join(result.logs)).to_contain('no castable Strike')
    test('exhaustion holds cover with retaliation disabled instead of meleeing', _exhaustion)

    def _failed_lure():
        result = yield from fight_fixture(displaced=True)
        expect(result.won).to_be(False)
        expect(result.cast).to_equal([])
        expect(result.melee).to_be(0)
        expect(len(result.walks)).to_be_greater_than(0)
    test('a failed lure never casts or falls back to melee', _failed_lure)

    def _rejected():
        result = yield from fight_fixture(refuses=True)
        expect(result.won).to_be(False)
        expect(result.cast).to_equal(['Fire Strike'])
        expect(result.melee).to_be(0)
    test('a rejected cast ends the attempt without attacking', _rejected)

    def _no_credit():
        result = yield from fight_fixture(win_after=1, credit=False)
        expect(result.won).to_be(False)
        expect(result.cast).to_equal(['Fire Strike'])
        expect(' '.join(result.logs)).to_contain('credit')
    test('a disappearing spirit without quest credit is not a victory', _no_credit)

    def _event():
        result = yield from fight_fixture(event=True)
        expect(result.won).to_be(False)
        expect(result.cast).to_equal([])
        expect(result.walks).to_equal([])
    test('a pending random event yields before movement or casting', _event)

    def _corpse():
        result = yield from fight_fixture(win_after=1, corpse=True)
        expect(result.won).to_be(True)
        expect(result.cast).to_equal(['Fire Strike'])
        expect(result.melee).to_be(0)
    test('waits out a known death animation without casting at the corpse', _corpse)

    for option in ['event_after_cast', 'drift_after_cast', 'no_consumption']:
        test(f'cancels the queued cast when {option} interrupts its acknowledgement', cancels_queued_cast(option))

    def _missing_tile():
        result = yield from fight_fixture(missing_tile=True)
        expect(result.won).to_be(False)
        expect(result.cast).to_equal([])
    test('missing player tiles stop the attempt without throwing or casting', _missing_tile)


def cancels_queued_cast(option):
    def run():
        options = {'no_consumption': True}
        options[option] = True
        result = yield from fight_fixture(**options)
        expect(result.won).to_be(False)
        expect(result.cast).to_equal(['Fire Strike'])
        expect(result.walks).to_contain_equal(SAFE)
        expect(result.melee).to_be(0)
        expect(result.retaliate).to_be(False)
    return run


describe('Lost City Tree Spirit fight', _fights)


def full_cost():
    runes = {'Mind rune': 1, 'Air rune': 1, 'Fire rune': 3}

    def count(name):
        return runes.get(name, 0)

    expect(highest_lost_city_strike(13, count)).to_be('Wind Strike')
    runes['Air rune'] = 2
    expect(highest_lost_city_strike(13, count)).to_be('Fire Strike')
    runes['Fire rune'] = 2
    expect(highest_lost_city_strike(13, count)).to_be('Wind Strike')
    runes['Mind rune'] = 0
    expect(highest_lost_city_strike(99, count)).to_be_null()


test('requires the full rune cost and a mind rune for each cast', full_cost)
