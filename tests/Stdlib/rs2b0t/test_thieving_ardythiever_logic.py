"""rs2b0t's test/scripts/ArdyFighter/ardythiever-logic.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs import ARDOUGNE_PICKPOCKET_TARGETS, HOSTILE_NAMES, Record, choose_target, is_hostile_attacker, required_thieving, target_spot


# Tables keyed by NPC name, so plain dicts.
SPAWNS = {
    'Guard': [[2651, 3307], [2659, 3309], [2660, 3309], [2661, 3309], [2663, 3301], [2665, 3300], [2664, 3318]],
    'Knight of Ardougne': [[2652, 3318], [2653, 3300], [2669, 3298], [2671, 3313]],
    'Paladin': [[2653, 3315], [2657, 3307]],
    'Hero': [[2647, 3306], [2667, 3316]],
}
MAXRANGE = {'Guard': 7, 'Knight of Ardougne': 17, 'Paladin': 4, 'Hero': 7}


def _fn1():
    def _fn2():
        for name in ARDOUGNE_PICKPOCKET_TARGETS:
            spot = target_spot(name)
            expect(spot.anchor.level).to_be(0)
            expect(spot.leash).to_be_greater_than_or_equal(12)
    test('resolves a spot for every Ardougne dropdown target', _fn2)

    def _fn3():
        for name, spawns in SPAWNS.items():
            spot = target_spot(name)
            for x, z in spawns:
                expect(spot.anchor.distance_to(Record({'x': x, 'z': z, 'level': 0})) + MAXRANGE.get(name)).to_be_less_than_or_equal(spot.leash)
    test('every spawn PLUS its engine roam cap sits within the target leash (Chebyshev)', _fn3)

    def _fn4():
        expect(target_spot('Nonexistent')).to_equal(target_spot('Guard'))
    test('unknown target falls back to the Guard spot', _fn4)


describe('targetSpot', _fn1)


def _fn5():
    def _fn6():
        expect(required_thieving('Guard')).to_be(40)
        expect(required_thieving('Knight of Ardougne')).to_be(55)
        expect(required_thieving('Paladin')).to_be(70)
        expect(required_thieving('Hero')).to_be(80)
    test('per-target pickpocket requirements from the content table', _fn6)

    def _fn7():
        expect(required_thieving('Nonexistent')).to_be(1)
    test('unknown target does not gate (level 1)', _fn7)


describe('requiredThieving', _fn5)


def _fn8():
    guard = Record({
        'name': 'Guard',
        'in_combat': True,
        'distance': 1,
        'actions': ['Pickpocket', 'Attack'],
        'targets_another_player': False,
    })

    def _fn9():
        expect(is_hostile_attacker(guard, 5)).to_be(True)
    test('accepts an in-combat adjacent market hostile with an Attack op', _fn9)

    def _fn10():
        _merged11 = {}
        for _k, _v in (guard._fields if isinstance(guard, Record) else guard).items():
            _merged11[_k] = _v
        for _k, _v in {'targets_another_player': True}.items():
            _merged11[_k] = _v
        expect(is_hostile_attacker(Record(_merged11), 5)).to_be(False)
    test('rejects a guard already fighting ANOTHER player (not us)', _fn10)

    def _fn12():
        expect(sorted(list(HOSTILE_NAMES))).to_equal(sorted(list(ARDOUGNE_PICKPOCKET_TARGETS)))
    test('every fight-mode hostile is an Ardougne dropdown target and vice versa', _fn12)

    def _fn13():
        _merged14 = {}
        for _k, _v in (guard._fields if isinstance(guard, Record) else guard).items():
            _merged14[_k] = _v
        for _k, _v in {'in_combat': False}.items():
            _merged14[_k] = _v
        expect(is_hostile_attacker(Record(_merged14), 5)).to_be(False)
    test('rejects a bystander not in combat', _fn13)

    def _fn15():
        _merged16 = {}
        for _k, _v in (guard._fields if isinstance(guard, Record) else guard).items():
            _merged16[_k] = _v
        for _k, _v in {'distance': 6}.items():
            _merged16[_k] = _v
        expect(is_hostile_attacker(Record(_merged16), 5)).to_be(False)
    test('rejects a hostile beyond the engage radius', _fn15)

    def _fn17():
        _merged18 = {}
        for _k, _v in (guard._fields if isinstance(guard, Record) else guard).items():
            _merged18[_k] = _v
        for _k, _v in {'distance': 5}.items():
            _merged18[_k] = _v
        expect(is_hostile_attacker(Record(_merged18), 5)).to_be(True)
    test('accepts a hostile at the exact engage radius (inclusive boundary)', _fn17)

    def _fn19():
        _merged20 = {}
        for _k, _v in (guard._fields if isinstance(guard, Record) else guard).items():
            _merged20[_k] = _v
        for _k, _v in {'name': 'Baker'}.items():
            _merged20[_k] = _v
        expect(is_hostile_attacker(Record(_merged20), 5)).to_be(False)
        _merged21 = {}
        for _k, _v in (guard._fields if isinstance(guard, Record) else guard).items():
            _merged21[_k] = _v
        for _k, _v in {'name': None}.items():
            _merged21[_k] = _v
        expect(is_hostile_attacker(Record(_merged21), 5)).to_be(False)
    test('rejects non-hostile NPCs (the Baker) and null names', _fn19)

    def _fn22():
        _merged23 = {}
        for _k, _v in (guard._fields if isinstance(guard, Record) else guard).items():
            _merged23[_k] = _v
        for _k, _v in {'actions': ['Pickpocket']}.items():
            _merged23[_k] = _v
        expect(is_hostile_attacker(Record(_merged23), 5)).to_be(False)
    test('rejects a hostile with no Attack op (mid-death / op-less variant)', _fn22)


describe('isHostileAttacker', _fn8)


def _fn24():
    def reach(set_):
        return lambda t: (t in set_)

    def _fn25():
        r = choose_target(['A', 'B', 'C'], reach(set(['B', 'C'])))
        expect(r).to_equal(Record({'target': 'B', 'blocked': None}))
    test('picks the nearest REACHABLE target, skipping closer unreachable ones', _fn25)

    def _fn26():
        expect(choose_target(['A', 'B'], reach(set(['A', 'B'])))).to_equal(Record({'target': 'A', 'blocked': None}))
    test('nearest reachable wins when the closest IS reachable', _fn26)

    def _fn27():
        expect(choose_target(['A', 'B'], reach(set()))).to_equal(Record({'target': None, 'blocked': 'A'}))
    test('none reachable → no target, surfaces the nearest as blocked for a bounded clear', _fn27)

    def _fn28():
        expect(choose_target([], reach(set()))).to_equal(Record({'target': None, 'blocked': None}))
    test('empty candidate list → nothing to do', _fn28)


describe('chooseTarget (reachability-aware pickpocket selection)', _fn24)
