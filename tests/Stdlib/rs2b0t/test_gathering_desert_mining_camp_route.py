"""rs2b0t's test/scripts/GatheringBot/DesertMiningCampRoute.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs import Record
from bots.gathering.desert_camp import COINS, DESERT_CAMP_KEEP_NAMES, DESERT_OUTFIT, METAL_KEY, PASS, SLAVE_OUTFIT, WROUGHT_KEY, desert_camp_bank_catch_needed, desert_camp_bank_trip_direction, desert_camp_destination_for, desert_camp_keep_names, desert_camp_route_area, desert_camp_route_phase, is_desert_camp_location, metal_key_captain_available, metal_key_captain_claim_acknowledged, metal_key_duel_needs_retreat, metal_key_retreat_after_sustain, plan_desert_camp_supplies


# rs2b0t's DESERT_CAMP_ITEMS; here the names are constants of their own.
DESERT_CAMP_ITEMS = Record({'coins': COINS, 'pass_': PASS, 'metal_key': METAL_KEY, 'wrought_key': WROUGHT_KEY, 'desert': DESERT_OUTFIT, 'slave': SLAVE_OUTFIT})
full_gear = {name: 1 for name in [METAL_KEY, WROUGHT_KEY] + DESERT_OUTFIT + SLAVE_OUTFIT}


def supply(overrides=None):
    if overrides is None:
        overrides = Record({})
    _merged1 = {}
    for _k, _v in {'inventory': Record({}), 'equipment': Record({}), 'bank': Record({}), 'free_slots': 28}.items():
        _merged1[_k] = _v
    for _k, _v in (overrides._fields if isinstance(overrides, Record) else overrides).items():
        _merged1[_k] = _v
    return Record(_merged1)


def _fn2():
    def _fn3():
        expect(metal_key_captain_available(None)).to_be(False)
        expect(metal_key_captain_available(Record({'in_combat': True, 'targets_another_player': lambda: False}))).to_be(False)
        expect(metal_key_captain_available(Record({'in_combat': False, 'targets_another_player': lambda: True}))).to_be(False)
        expect(metal_key_captain_available(Record({'in_combat': False, 'targets_another_player': lambda: False}))).to_be(True)
    test('waits for an unoccupied Mercenary Captain', _fn3)

    def _fn4():
        expect(metal_key_captain_claim_acknowledged(False, False, False)).to_be(False)
        expect(metal_key_captain_claim_acknowledged(True, False, False)).to_be(True)
        expect(metal_key_captain_claim_acknowledged(False, True, False)).to_be(True)
        expect(metal_key_captain_claim_acknowledged(False, False, True)).to_be(True)
    test('does not treat an unacknowledged Talk-to packet as captain ownership', _fn4)

    def _fn5():
        expect(metal_key_duel_needs_retreat(2, True)).to_be(False)
        expect(metal_key_duel_needs_retreat(1, True)).to_be(True)
        expect(metal_key_duel_needs_retreat(0, True)).to_be(True)
    test('retreats before fighting on the final food item', _fn5)

    def _fn6():
        expect(metal_key_duel_needs_retreat(0, False)).to_be(False)
    test('does not retreat after the captain has died and the key reward is pending', _fn6)

    def _fn7():
        expect(metal_key_retreat_after_sustain(True, 1, True)).to_be(False)
        expect(metal_key_retreat_after_sustain(False, 1, False)).to_be(False)
        expect(metal_key_retreat_after_sustain(False, 1, True)).to_be(True)
    test('rechecks both the key and captain after sustain before retreating', _fn7)


describe('Metal key duel safety', _fn2)


def route_area_is(tile, area):
    def run():
        expect(desert_camp_route_area(tile)).to_be(area)
    return run


def _fn8():
    cases = [
        [Record({'x': 3309, 'z': 3120, 'level': 0}), 'shantayNorth'],
        [Record({'x': 3302, 'z': 3114, 'level': 0}), 'desert'],
        [Record({'x': 3288, 'z': 3029, 'level': 0}), 'campSurface'],
        [Record({'x': 3290, 'z': 3033, 'level': 1}), 'campSurface'],
        [Record({'x': 3285, 'z': 3034, 'level': 0}), 'unsupported'],
        [Record({'x': 3278, 'z': 9415, 'level': 0}), 'mineEntrance'],
        [Record({'x': 3286, 'z': 9415, 'level': 0}), 'mineLower'],
        [Record({'x': 3288, 'z': 9435, 'level': 0}), 'unsupported'],
        [Record({'x': 3322, 'z': 9448, 'level': 0}), 'mineLower'],
        [Record({'x': 3322, 'z': 9449, 'level': 0}), 'mineDeep'],
        [Record({'x': 3323, 'z': 9458, 'level': 0}), 'mineDeep'],
        [Record({'x': 2606, 'z': 3102, 'level': 0}), 'mainland'],
        [Record({'x': 3218, 'z': 9618, 'level': 0}), 'unsupported'],
    ]
    for tile, area in cases:
        test(f'{tile.x},{tile.z},{tile.level} is {area}', route_area_is(tile, area))


describe('Desert Mining Camp route areas', _fn8)


def _fn10():
    def _fn11():
        expect(desert_camp_bank_catch_needed(True, False, False, False)).to_be(True)
        expect(desert_camp_bank_catch_needed(False, False, False, False)).to_be(False)
        expect(desert_camp_bank_catch_needed(False, True, False, False)).to_be(True)
        expect(desert_camp_bank_catch_needed(False, False, True, False)).to_be(True)
        expect(desert_camp_bank_catch_needed(False, False, False, True)).to_be(True)
    test('hands a latched trip to banking after the route reaches Shantay', _fn11)

    def _fn12():
        idle = desert_camp_bank_trip_direction(False, False)
        expect(idle).to_equal(Record({'bank_trip': False, 'direction': 'enter'}))
        full_pack = desert_camp_bank_trip_direction(idle.bank_trip, True)
        expect(full_pack).to_equal(Record({'bank_trip': True, 'direction': 'exit'}))
        after_eating = desert_camp_bank_trip_direction(full_pack.bank_trip, False)
        expect(after_eating).to_equal(Record({'bank_trip': True, 'direction': 'exit'}))
        expect(desert_camp_bank_trip_direction(after_eating.bank_trip, False)).to_equal(after_eating)
        expect(desert_camp_bank_trip_direction(False, False)).to_equal(Record({'bank_trip': False, 'direction': 'enter'}))
    test('keeps an outbound bank trip latched after eating frees a pack slot', _fn12)

    def _fn13():
        expect(desert_camp_route_phase('enter', 'shantayNorth')).to_be('prepareAndCrossShantay')
        expect(desert_camp_route_phase('enter', 'desert')).to_be('enterCamp')
        expect(desert_camp_route_phase('enter', 'campSurface')).to_be('enterMine')
        expect(desert_camp_route_phase('enter', 'mineEntrance')).to_be('enterMine')
        expect(desert_camp_route_phase('enter', 'mineLower')).to_be('enterMine')
        expect(desert_camp_route_phase('enter', 'mineDeep')).to_be('done')
    test('entry hands every physical crossing to one shared mine walk', _fn13)

    def _fn14():
        expect(desert_camp_route_phase('enter', 'shantayNorth', 'campSurface')).to_be('prepareAndCrossShantay')
        expect(desert_camp_route_phase('enter', 'desert', 'campSurface')).to_be('enterCamp')
        expect(desert_camp_route_phase('enter', 'campSurface', 'campSurface')).to_be('done')
        expect(desert_camp_route_phase('enter', 'mineDeep', 'campSurface')).to_be('exitMine')
        expect(desert_camp_route_phase('exit', 'campSurface', 'campSurface')).to_be('exitCamp')
        expect(is_desert_camp_location('Desert Mining Camp')).to_be(True)
        expect(is_desert_camp_location('Desert Mining Camp Surface')).to_be(True)
        expect(desert_camp_destination_for('Desert Mining Camp Surface')).to_be('campSurface')
        expect(desert_camp_destination_for('Desert Mining Camp')).to_be('mineDeep')
    test('surface destination stops at the camp and walks out of a leftover underground tile', _fn14)

    def _fn15():
        expect(desert_camp_route_phase('exit', 'mineDeep')).to_be('exitMine')
        expect(desert_camp_route_phase('exit', 'mineLower')).to_be('exitMine')
        expect(desert_camp_route_phase('exit', 'mineEntrance')).to_be('exitMine')
        expect(desert_camp_route_phase('exit', 'campSurface')).to_be('exitCamp')
        expect(desert_camp_route_phase('exit', 'desert')).to_be('crossShantayNorth')
        expect(desert_camp_route_phase('exit', 'shantayNorth')).to_be('done')
    test('exit hands every underground crossing to one shared surface walk', _fn15)

    def _fn16():
        expect(desert_camp_route_phase('enter', 'unsupported')).to_be('unsupported')
        expect(desert_camp_route_phase('exit', 'unsupported')).to_be('unsupported')
    test('unsupported starts remain explicit failures', _fn16)


describe('Desert Mining Camp restart phases', _fn10)


def _fn17():
    def _fn18():
        _merged19 = {}
        for _k, _v in (full_gear._fields if isinstance(full_gear, Record) else full_gear).items():
            _merged19[_k] = _v
        for _k, _v in {DESERT_CAMP_ITEMS.pass_: 30}.items():
            _merged19[_k] = _v
        plan = plan_desert_camp_supplies(supply(Record({
        'equipment': {_k: _v for _k, _v in [[name, 1] for name in DESERT_CAMP_ITEMS.desert]},
        'bank': Record(_merged19),
    })))
        expect(plan).to_match_object(Record({'ok': True, 'buy_pass': False, 'recover_metal_key': False, 'recover_wrought_key': False}))
        expect(plan.withdraw).to_equal(list([(Record({'name': name, 'qty': 1})) for name in DESERT_CAMP_ITEMS.slave]) + [Record({'name': DESERT_CAMP_ITEMS.metal_key, 'qty': 1}), Record({'name': DESERT_CAMP_ITEMS.wrought_key, 'qty': 1}), Record({'name': DESERT_CAMP_ITEMS.pass_, 'qty': 1})])
    test('withdraws banked keys, slave gear and pass exactly once', _fn18)

    def _fn20():
        bank = {_k: _v for _k, _v in [[name, 1] for name in list(DESERT_CAMP_ITEMS.desert) + list(DESERT_CAMP_ITEMS.slave)]}
        _merged21 = {}
        for _k, _v in (bank._fields if isinstance(bank, Record) else bank).items():
            _merged21[_k] = _v
        for _k, _v in {DESERT_CAMP_ITEMS.pass_: 1}.items():
            _merged21[_k] = _v
        plan = plan_desert_camp_supplies(supply(Record({'bank': Record(_merged21)})))
        expect(plan).to_match_object(Record({'ok': True, 'recover_metal_key': True, 'recover_wrought_key': True, 'required_slots': 7}))
        expect(plan.missing).to_equal([])
    test('missing camp keys are recoverable and reserve the three desk-award slots', _fn20)

    def _fn22():
        plan = plan_desert_camp_supplies(supply(Record({
        'equipment': full_gear,
        'inventory': Record({DESERT_CAMP_ITEMS.metal_key: 1}),
        'bank': Record({DESERT_CAMP_ITEMS.pass_: 1}),
    })))
        expect(plan).to_match_object(Record({'ok': True, 'recover_metal_key': False, 'recover_wrought_key': False}))
        without_wrought = plan_desert_camp_supplies(supply(Record({
        'equipment': {_k: _v for _k, _v in [[name, 1] for name in list(DESERT_CAMP_ITEMS.desert) + list(DESERT_CAMP_ITEMS.slave)]},
        'inventory': Record({DESERT_CAMP_ITEMS.metal_key: 1}),
        'bank': Record({DESERT_CAMP_ITEMS.pass_: 1}),
    })))
        expect(without_wrought).to_match_object(Record({'ok': True, 'recover_metal_key': False, 'recover_wrought_key': True, 'required_slots': 3}))
    test('a missing Wrought key reserves Cell plus Wrought without inventing a fallback', _fn22)

    def _fn23():
        plan = plan_desert_camp_supplies(supply(Record({
        'inventory': Record({DESERT_CAMP_ITEMS.coins: 2}),
        'equipment': full_gear,
        'bank': Record({DESERT_CAMP_ITEMS.coins: 3}),
    })))
        expect(plan).to_match_object(Record({
        'ok': True,
        'buy_pass': True,
        'coin_target': 5,
        'withdraw': [Record({'name': DESERT_CAMP_ITEMS.coins, 'qty': 3})],
    }))
    test('uses exactly five coins only when no pass is carried or banked', _fn23)

    def _fn24():
        bank_gear = {_k: _v for _k, _v in [[name, 1] for name in [DESERT_CAMP_ITEMS.metal_key, DESERT_CAMP_ITEMS.wrought_key] + list(DESERT_CAMP_ITEMS.slave)]}
        _merged25 = {}
        for _k, _v in (bank_gear._fields if isinstance(bank_gear, Record) else bank_gear).items():
            _merged25[_k] = _v
        for _k, _v in {DESERT_CAMP_ITEMS.coins: 112}.items():
            _merged25[_k] = _v
        plan = plan_desert_camp_supplies(supply(Record({'bank': Record(_merged25)})))
        expect(plan).to_match_object(Record({'ok': True, 'recover_slave_outfit': False, 'buy_outfit': [], 'buy_pass': True, 'coin_target': 5}))
        expect(plan.withdraw).to_contain_equal(Record({'name': DESERT_CAMP_ITEMS.coins, 'qty': 5}))
    test('does not provision desert clothes when the slave disguise is available', _fn24)

    def _fn26():
        plan = plan_desert_camp_supplies(supply(Record({'bank': Record({DESERT_CAMP_ITEMS.coins: 219})})))
        expect(plan).to_match_object(Record({'ok': True, 'recover_slave_outfit': True, 'coin_target': 112, 'required_slots': 8}))
        expect(plan.buy_outfit).to_equal(list(DESERT_CAMP_ITEMS.desert))
        expect(plan.missing).to_equal([])
        expect(plan.missing).not_.to_contain(DESERT_CAMP_ITEMS.metal_key)
        expect(plan.missing).not_.to_contain(DESERT_CAMP_ITEMS.wrought_key)
    test('provisions one desert outfit to replace a completely lost slave disguise', _fn26)

    def _fn27():
        _merged28 = {}
        for _k, _v in {DESERT_CAMP_ITEMS.slave[0]: 1}.items():
            _merged28[_k] = _v
        for _k, _v in ({_k: _v for _k, _v in [[name, 1] for name in DESERT_CAMP_ITEMS.desert]}._fields if isinstance({_k: _v for _k, _v in [[name, 1] for name in DESERT_CAMP_ITEMS.desert]}, Record) else {_k: _v for _k, _v in [[name, 1] for name in DESERT_CAMP_ITEMS.desert]}).items():
            _merged28[_k] = _v
        _merged29 = {}
        for _k, _v in ({_k: _v for _k, _v in [[name, 1] for name in DESERT_CAMP_ITEMS.desert]}._fields if isinstance({_k: _v for _k, _v in [[name, 1] for name in DESERT_CAMP_ITEMS.desert]}, Record) else {_k: _v for _k, _v in [[name, 1] for name in DESERT_CAMP_ITEMS.desert]}).items():
            _merged29[_k] = _v
        for _k, _v in {DESERT_CAMP_ITEMS.metal_key: 1, DESERT_CAMP_ITEMS.wrought_key: 1, DESERT_CAMP_ITEMS.pass_: 1}.items():
            _merged29[_k] = _v
        plan = plan_desert_camp_supplies(supply(Record({'inventory': Record(_merged28), 'bank': Record(_merged29)})))
        expect(plan).to_match_object(Record({'ok': True, 'recover_slave_outfit': True, 'buy_outfit': [], 'required_slots': 3}))
        expect(plan.withdraw).to_equal([
        Record({'name': DESERT_CAMP_ITEMS.metal_key, 'qty': 1}),
        Record({'name': DESERT_CAMP_ITEMS.wrought_key, 'qty': 1}),
        Record({'name': DESERT_CAMP_ITEMS.pass_, 'qty': 1}),
    ])
    test('uses an existing desert outfit to recover partial slave gear', _fn27)

    def _fn30():
        _merged31 = {}
        for _k, _v in ({_k: _v for _k, _v in [[name, 1] for name in list(DESERT_CAMP_ITEMS.desert) + list(DESERT_CAMP_ITEMS.slave)]}._fields if isinstance({_k: _v for _k, _v in [[name, 1] for name in list(DESERT_CAMP_ITEMS.desert) + list(DESERT_CAMP_ITEMS.slave)]}, Record) else {_k: _v for _k, _v in [[name, 1] for name in list(DESERT_CAMP_ITEMS.desert) + list(DESERT_CAMP_ITEMS.slave)]}).items():
            _merged31[_k] = _v
        for _k, _v in {DESERT_CAMP_ITEMS.pass_: 1}.items():
            _merged31[_k] = _v
        plan = plan_desert_camp_supplies(supply(Record({'bank': Record(_merged31), 'free_slots': 2})))
        expect(plan.ok).to_be(False)
        expect(plan.required_slots).to_be(7)
        expect(plan.missing).to_contain('5 free inventory slot(s)')
    test('rejects a loadout that cannot fit recovery and route supplies', _fn30)

    def _fn32():
        for name in DESERT_CAMP_ITEMS.slave:
            expect(DESERT_CAMP_KEEP_NAMES).to_contain(name)
        for name in DESERT_CAMP_ITEMS.desert:
            expect(DESERT_CAMP_KEEP_NAMES).not_.to_contain(name)
    test('banks desert clothes but keeps the slave disguise between trips', _fn32)

    def _fn33():
        keep = desert_camp_keep_names('campSurface')
        for name in [DESERT_CAMP_ITEMS.metal_key] + list(DESERT_CAMP_ITEMS.desert):
            expect(keep).to_contain(name)
        expect(keep).not_.to_contain(DESERT_CAMP_ITEMS.wrought_key)
        for name in DESERT_CAMP_ITEMS.slave:
            expect(keep).not_.to_contain(name)
    test('surface trips keep desert clothes and Metal key, not slave gear or Wrought', _fn33)

    def _fn34():
        _merged35 = {}
        for _k, _v in ({_k: _v for _k, _v in [[name, 1] for name in DESERT_CAMP_ITEMS.desert]}._fields if isinstance({_k: _v for _k, _v in [[name, 1] for name in DESERT_CAMP_ITEMS.desert]}, Record) else {_k: _v for _k, _v in [[name, 1] for name in DESERT_CAMP_ITEMS.desert]}).items():
            _merged35[_k] = _v
        for _k, _v in {DESERT_CAMP_ITEMS.metal_key: 1, DESERT_CAMP_ITEMS.pass_: 1, DESERT_CAMP_ITEMS.wrought_key: 1}.items():
            _merged35[_k] = _v
        for _k, _v in ({_k: _v for _k, _v in [[name, 1] for name in DESERT_CAMP_ITEMS.slave]}._fields if isinstance({_k: _v for _k, _v in [[name, 1] for name in DESERT_CAMP_ITEMS.slave]}, Record) else {_k: _v for _k, _v in [[name, 1] for name in DESERT_CAMP_ITEMS.slave]}).items():
            _merged35[_k] = _v
        plan = plan_desert_camp_supplies(supply(Record({'bank': Record(_merged35)})), 'campSurface')
        expect(plan).to_match_object(Record({
        'ok': True,
        'recover_slave_outfit': False,
        'recover_wrought_key': False,
        'recover_metal_key': False,
        'buy_pass': False,
    }))
        expect(plan.withdraw).to_equal(list([(Record({'name': name, 'qty': 1})) for name in DESERT_CAMP_ITEMS.desert]) + [Record({'name': DESERT_CAMP_ITEMS.metal_key, 'qty': 1}), Record({'name': DESERT_CAMP_ITEMS.pass_, 'qty': 1})])
    test('surface supply plan withdraws desert clothes and Metal key without slave gear', _fn34)

    def _fn36():
        base = Record({
        'inventory': Record({DESERT_CAMP_ITEMS.pass_: 1}),
        'equipment': full_gear,
        'bank': Record({}),
        'free_slots': 1,
    })
        expect(plan_desert_camp_supplies(supply(base))).to_match_object(Record({'ok': True, 'required_slots': 0}))
        _merged37 = {}
        for _k, _v in (full_gear._fields if isinstance(full_gear, Record) else full_gear).items():
            _merged37[_k] = _v
        for _k, _v in {'Rune pickaxe': 1}.items():
            _merged37[_k] = _v
        _merged38 = {}
        for _k, _v in (base._fields if isinstance(base, Record) else base).items():
            _merged38[_k] = _v
        for _k, _v in {'equipment': Record(_merged37)}.items():
            _merged38[_k] = _v
        expect(plan_desert_camp_supplies(supply(Record(_merged38)))).to_match_object(Record({'ok': True, 'required_slots': 0}))
    test('keeps a worn pickaxe equipped without reserving a pack slot', _fn36)


describe('Desert Mining Camp supply plan', _fn17)
