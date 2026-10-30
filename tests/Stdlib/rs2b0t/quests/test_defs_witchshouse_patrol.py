from rs2004 import execution
from rs2004.game import game, direct_navigator
from rs2004.entities import npcs
from rs2004.items import inventory
from rs2004.traversal import traversal

PATROL_TEST_STATE = {}

def stub_props(target, fields):
    for name, value in fields.items():
        spy_on(target, name, impl=value)
    return lambda: None

"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/witchshouse-patrol.test.ts (MIT, see thirdparty/rs2b0t)."""
from rs2004.quests.defs.witchshouse.garden import fountain_key
from rs2004.quests.defs.witchshouse import decide
from rs2004.quests.defs.witchshouse.areas import WH_OBJ, WH_TILE
from rs2004.quests.defs.witchshouse.journal import WH_STAGE

def _fn1():
    PATROL_TEST_STATE['walks'] = 0

    def _fn2():
        PATROL_TEST_STATE['walks'] += 1
        return False
        if False:
            yield
    restores = [stub_props(game, Obj({'tile': lambda: Obj({'x': 2909, 'z': 3460, 'level': 0})})), stub_props(inventory, Obj({'count_by_id': lambda id: 0})), stub_props(npcs, Obj({'all': lambda: []})), stub_props(execution, Obj({'delay_ticks': instant_ticks})), stub_props(traversal, Obj({'walk_resilient': _fn2}))]
    try:
        _w3 = yield from fountain_key(lambda *_args: None)
        expect(_w3).to_be(False)
        expect(PATROL_TEST_STATE['walks']).to_be(0)
    except Exception as e:
        for restore in reversed(restores):
            restore()
        raise e
    for restore in reversed(restores):
        restore()
test('a missing patrol snapshot never starts an unguarded fountain run', _fn1)

def _fn4():
    step = decide(Obj({'journal': 'in_progress', 'stage': WH_STAGE.DEFEATED, 'inv': {_k: _v for _k, _v in [['ball', 1]]}, 'inv_ids': {_k: _v for _k, _v in [[WH_OBJ.BALL, 1]]}, 'worn': set(), 'bank': {}, 'bank_known': True, 'bank_coins': 0, 'no_progress': 0, 'tile': WH_TILE.BALL}))
    expect(step.kind).to_be('custom')
    expect(step.kind == 'custom' and step.name).to_contain('garden')
test('a recovered ball leaves the garden safely before walking to the boy', _fn4)
from rs2004.quests.defs.witchshouse.patrol import garden_legs, GARDEN_ENTRY, FOUNTAIN_STAND, GARDEN_SHED, safe_crossing, sheltered, walk_garden, observe_witch

def patrol(tick):
    return Obj({'x': 2904 + (tick % 52 if tick % 52 <= 26 else 52 - tick % 52), 'z': 3463, 'level': 0})

def route_case(from_, to):

    def _fn5():
        legs = garden_legs(from_, to)
        expect(legs).not_.to_be_null()
        for phase in range(52):
            tick = phase
            for leg in legs:
                waited = 0
                observation = None
                while waited < 120:
                    observation = observe_witch(observation, patrol(tick) if abs(patrol(tick).x - leg[0].x) <= 15 else None, tick)
                    if safe_crossing(leg, observation):
                        break
                    expect(sheltered(leg[0])).to_be(True)
                    tick += 1
                    waited += 1
                expect(waited).to_be_less_than(120)
                for point in leg[1:]:
                    tick += 1
                    witch = patrol(tick)
                    expect(sheltered(point) or max(abs(point.x - witch.x), abs(point.z - witch.z)) > 3).to_be(True)
                expect(sheltered(leg[-1] if len(leg) > 0 else None)).to_be(True)
    return _fn5
for from_, to in [[GARDEN_ENTRY, FOUNTAIN_STAND], [FOUNTAIN_STAND, GARDEN_SHED], [GARDEN_SHED, GARDEN_ENTRY]]:
    test(f'walking {from_.x},{from_.z} to {to.x},{to.z} stays safe at every patrol phase', route_case(from_, to))

def _fn6():
    expect(sheltered(Obj({'x': 2912, 'z': 3460, 'level': 0}))).to_be(False)
    expect(sheltered(Obj({'x': 2916, 'z': 3466, 'level': 0}))).to_be(False)
    expect(sheltered(Obj({'x': 2932, 'z': 3460, 'level': 0}))).to_be(False)
test('hedge gaps and the south-east corner are not waiting places', _fn6)

def _fn7():
    PATROL_TEST_STATE['walks'] = []
    PATROL_TEST_STATE['here'] = Obj({'x': 2909, 'z': 3460, 'level': 0})
    PATROL_TEST_STATE['sample'] = 14

    def _fn8(tile):
        PATROL_TEST_STATE['walks'].append(tile)
        return True

    def _fn9(count=1):
        PATROL_TEST_STATE['sample'] += 1
        if False:
            yield

    def _fn10(*args):
        return False
        if False:
            yield
    restores = [stub_props(game, Obj({'tile': lambda: PATROL_TEST_STATE['here'], 'tick': lambda: PATROL_TEST_STATE['sample']})), stub_props(npcs, Obj({'all': lambda: [Obj({'id': 896, 'network_tile': lambda: patrol(PATROL_TEST_STATE['sample'])})]})), stub_props(direct_navigator, Obj({'walk': _fn8})), stub_props(execution, Obj({'delay_ticks': _fn9, 'delay_until_ticks': _fn10}))]
    try:
        _w11 = yield from walk_garden(FOUNTAIN_STAND, lambda *_args: None)
        expect(_w11).to_be(False)
        expect(PATROL_TEST_STATE['walks']).to_have_length(2)
        expect(PATROL_TEST_STATE['walks'][-1] if len(PATROL_TEST_STATE['walks']) > 0 else None).to_equal(PATROL_TEST_STATE['here'])
    except Exception as e:
        for restore in reversed(restores):
            restore()
        raise e
    for restore in reversed(restores):
        restore()
test('a stalled crossing stops before another leg is issued', _fn7)

def _fn12():
    PATROL_TEST_STATE['here'] = Obj({'x': 2909, 'z': 3460, 'level': 0})
    _merged13 = {}
    for _k, _v in (PATROL_TEST_STATE['here']._fields if isinstance(PATROL_TEST_STATE['here'], Obj) else PATROL_TEST_STATE['here']).items():
        _merged13[_k] = _v
    PATROL_TEST_STATE['destination'] = Obj(_merged13)
    PATROL_TEST_STATE['stopped_ticks'] = 0
    PATROL_TEST_STATE['sample'] = 14
    PATROL_TEST_STATE['walks'] = []

    def advance(count=1):
        PATROL_TEST_STATE['sample'] += 1
        if PATROL_TEST_STATE['here'].x == 2912 and PATROL_TEST_STATE['stopped_ticks'] < 2:
            PATROL_TEST_STATE['stopped_ticks'] += 1
            return
        _merged14 = {}
        for _k, _v in (PATROL_TEST_STATE['here']._fields if isinstance(PATROL_TEST_STATE['here'], Obj) else PATROL_TEST_STATE['here']).items():
            _merged14[_k] = _v
        for _k, _v in {'x': PATROL_TEST_STATE['here'].x + (1 if PATROL_TEST_STATE['destination'].x - PATROL_TEST_STATE['here'].x > 0 else (-1 if PATROL_TEST_STATE['destination'].x - PATROL_TEST_STATE['here'].x < 0 else 0))}.items():
            _merged14[_k] = _v
        PATROL_TEST_STATE['here'] = Obj(_merged14)
        if False:
            yield

    def _fn15(tile):
        PATROL_TEST_STATE['walks'].append(tile)
        _merged16 = {}
        for _k, _v in (tile._fields if isinstance(tile, Obj) else {'x':tile.x, 'z':tile.z, 'level':tile.level}).items():
            _merged16[_k] = _v
        PATROL_TEST_STATE['destination'] = Obj(_merged16)
        return True

    def _fn17(check, ticks):
        i = 0
        while i < ticks and (not check()):
            yield from advance()
            i += 1
        return check()
    restores = [stub_props(game, Obj({'tile': lambda: PATROL_TEST_STATE['here'], 'tick': lambda: PATROL_TEST_STATE['sample']})), stub_props(npcs, Obj({'all': lambda: [Obj({'id': 896, 'network_tile': lambda: patrol(PATROL_TEST_STATE['sample'])})]})), stub_props(direct_navigator, Obj({'walk': _fn15})), stub_props(execution, Obj({'delay_ticks': advance, 'delay_until_ticks': _fn17}))]
    try:
        _w18 = yield from walk_garden(FOUNTAIN_STAND, lambda *_args: None)
        expect(_w18).to_be(False)
        expect(PATROL_TEST_STATE['walks']).to_have_length(2)
        expect(sheltered(PATROL_TEST_STATE['here'])).to_be(True)
        expect(PATROL_TEST_STATE['here'].x).to_be(2909)
    except Exception as e:
        for restore in reversed(restores):
            restore()
        raise e
    for restore in reversed(restores):
        restore()
test('a mid-gap stall retreats to a hedge before another patrol wait', _fn12)

def _fn19():
    first = observe_witch(None, patrol(10), 10)
    moving = observe_witch(first, patrol(11), 11)
    expect(moving.direction).to_be(1)
    expect(observe_witch(moving, moving.tile, 12).direction if observe_witch(moving, moving.tile, 12) is not None else None).to_be(0)
    expect(observe_witch(moving, None, 12)).to_be_null()
    expect(observe_witch(None, patrol(40), 40).direction if observe_witch(None, patrol(40), 40) is not None else None).to_be(0)
    expect(observe_witch(moving, patrol(13), 12).direction if observe_witch(moving, patrol(13), 12) is not None else None).to_be(0)
    expect(observe_witch(moving, patrol(12), 13).direction if observe_witch(moving, patrol(12), 13) is not None else None).to_be(0)
test('stationary, missing, jumped and skipped observations invalidate the heading', _fn19)

def _fn21():
    PATROL_TEST_STATE['sprite'] = Obj({'x': 2909, 'z': 3460, 'level': 0})
    _merged22 = {}
    for _k, _v in (PATROL_TEST_STATE['sprite']._fields if isinstance(PATROL_TEST_STATE['sprite'], Obj) else PATROL_TEST_STATE['sprite']).items():
        _merged22[_k] = _v
    PATROL_TEST_STATE['server'] = Obj(_merged22)
    _merged23 = {}
    for _k, _v in (PATROL_TEST_STATE['server']._fields if isinstance(PATROL_TEST_STATE['server'], Obj) else PATROL_TEST_STATE['server']).items():
        _merged23[_k] = _v
    PATROL_TEST_STATE['destination'] = Obj(_merged23)
    PATROL_TEST_STATE['tick'] = 14
    PATROL_TEST_STATE['walks'] = []

    def _fn24(tile):
        PATROL_TEST_STATE['walks'].append(tile)
        _merged25 = {}
        for _k, _v in (tile._fields if isinstance(tile, Obj) else {'x':tile.x, 'z':tile.z, 'level':tile.level}).items():
            _merged25[_k] = _v
        PATROL_TEST_STATE['destination'] = Obj(_merged25)
        return True

    def _fn26(count=1):
        PATROL_TEST_STATE['tick'] += 1
        _merged27 = {}
        for _k, _v in (PATROL_TEST_STATE['server']._fields if isinstance(PATROL_TEST_STATE['server'], Obj) else PATROL_TEST_STATE['server']).items():
            _merged27[_k] = _v
        for _k, _v in {'x': PATROL_TEST_STATE['server'].x + (1 if PATROL_TEST_STATE['destination'].x - PATROL_TEST_STATE['server'].x > 0 else (-1 if PATROL_TEST_STATE['destination'].x - PATROL_TEST_STATE['server'].x < 0 else 0))}.items():
            _merged27[_k] = _v
        PATROL_TEST_STATE['server'] = Obj(_merged27)
        if False:
            yield
    restores = [stub_props(game, Obj({'tile': lambda: PATROL_TEST_STATE['server'], 'tick': lambda: PATROL_TEST_STATE['tick']})), stub_props(npcs, Obj({'all': lambda: [Obj({'id': 896, 'network_tile': lambda: patrol(PATROL_TEST_STATE['tick'])})]})), stub_props(direct_navigator, Obj({'walk': _fn24})), stub_props(execution, Obj({'delay_ticks': _fn26}))]
    try:
        _w28 = yield from walk_garden(Tile(2915, 3460, 0), lambda *_args: None)
        expect(_w28).to_be(True)
        expect(PATROL_TEST_STATE['walks']).to_have_length(1)
        expect(PATROL_TEST_STATE['server'].x).to_be(2915)
        expect(PATROL_TEST_STATE['sprite'].x).to_be(2909)
    except Exception as e:
        for restore in reversed(restores):
            restore()
        raise e
    for restore in reversed(restores):
        restore()
test('headless server position drives garden movement', _fn21)
