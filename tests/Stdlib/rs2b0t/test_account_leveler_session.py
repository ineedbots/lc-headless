"""Ported from rs2b0t's src/bot/../../test/scripts/accountLevelerSession.test.ts (MIT, see thirdparty/rs2b0t)."""
from bots.account_leveler.record import Record
from bots.account_leveler.session import LevelerSession
from bots.account_leveler.planner import empty_memory
plan = Record({'id': 'goblins', 'label': 'goblins', 'script': 'AutoFighter', 'objective': 'attack', 'needs': [], 'settings': Record({}), 'combat': True})

def _fn1(*_args):
    session = LevelerSession(empty_memory())
    session.start(plan, 1000, lambda: 0)
    expect(session.failure(2000)).to_be('reset')
    session.start(plan, 3000, lambda: 0)
    expect(session.failure(4000)).to_be('rotate')
    expect(session.memory.cooldowns.get('goblins')).to_be_greater_than(4000)
    expect(session.memory.objective).to_be_null()
test('first stall requests a bank reset; repeated failure cools down the camp', _fn1)

def _fn2(*_args):
    session = LevelerSession(empty_memory())
    session.start(plan, 0, lambda: 0)
    session.observe('xp:1', 1000)
    expect(session.stalled(180000)).to_be(False)
    expect(session.stalled(182000)).to_be(True)
    session.failure(182000)
    session.start(plan, 183000, lambda: 0)
    session.observe('xp:2', 184000)
    expect(session.failure(185000)).to_be('rotate')
test('observed progress advances the stall deadline but does not erase the retry budget', _fn2)

def _fn3(*_args):
    session = LevelerSession(empty_memory())
    _merged4 = {}
    for _k, _v in ((plan._fields if isinstance(plan, Record) else plan)).items():
        _merged4[_k] = _v
    for _k, _v in {'id': 'logs', 'output': Record({'item': 'Logs', 'count': 28})}.items():
        _merged4[_k] = _v
    session.start(Record(_merged4), 0, lambda: 0)
    session.complete(1000, True)
    expect(session.memory.objective).to_be('attack')
    session.start(plan, 2000, lambda: 0)
    session.complete(3000, True)
    expect(session.memory.objective).to_be_null()
    expect(session.memory.recent).to_contain('goblins')
test('finishing a resource dependency retains the objective; finishing training rotates it', _fn3)

def _fn5(*_args):
    session = LevelerSession(empty_memory())
    session.start(plan, 0, lambda: 0)
    expect(session.death(1000)).to_be('reset')
    session.start(plan, 2000, lambda: 0)
    expect(session.death(3000)).to_be('rotate')
    expect(session.memory.deaths).to_be(2)
test('death records recovery and repeated deaths exclude the same location', _fn5)

def _fn6(*_args):
    session = LevelerSession(empty_memory())
    for i in range(3):
        session.start(plan, i * 1000, lambda: 0)
        session.resupply(i * 1000 + 500)
    expect(session.memory.cooldowns).to_equal(Record({}))
    expect(session.memory.objective).to_be('attack')
    session.start(plan, 5000, lambda: 0)
    expect(session.failure(6000)).to_be('reset')
test('normal resupply keeps its objective without consuming the failure budget', _fn6)

def _fn7(*_args):
    session = LevelerSession(empty_memory())
    session.start(plan, 0, lambda: 0)
    session.observe('walked to bank', 300000)
    session.observe('walked to camp', 1200000)
    expect(session.remaining_ms).to_be(600000)
    session.work(10000)
    expect(session.remaining_ms).to_be(590000)
test('travel and bank observation do not consume the training budget', _fn7)

def _fn8(*_args):
    session = LevelerSession(empty_memory())
    session.start(plan, 0, lambda: 0)
    session.sample_work(1000, False)
    t = 1600
    while t <= 61000:
        session.sample_work(t, True)
        t += 600
    expect(session.remaining_ms).to_be(540000)
    session.sample_work(61600, False)
    expect(session.remaining_ms).to_be(540000)
test('a child starting idle is charged for a full fight while its loop remains pending', _fn8)

def _fn10(*_args):
    session = LevelerSession(empty_memory())
    _merged11 = {}
    for _k, _v in ((plan._fields if isinstance(plan, Record) else plan)).items():
        _merged11[_k] = _v
    for _k, _v in {'id': 'fish-shrimps', 'label': 'fish shrimps', 'script': 'Fisher', 'combat': False, 'output': Record({'item': 'Raw shrimps', 'count': 28})}.items():
        _merged11[_k] = _v
    fish = Record(_merged11)
    for attempt in range(1, 12 + 1):
        session.start(fish, attempt * 1000, lambda: 0)
        expect(session.failure(attempt * 1000 + 500)).to_be(('reset' if attempt % 3 else 'rotate'))
        expect(session.memory.cooldowns).to_equal(Record({}))
    expect(session.memory.objective).to_be('attack')
test('routine gathering keeps recovering without stopping or cooling down food production', _fn10)

def _fn12(*_args):
    session = LevelerSession(empty_memory())
    _merged13 = {}
    for _k, _v in ((plan._fields if isinstance(plan, Record) else plan)).items():
        _merged13[_k] = _v
    for _k, _v in {'death_walk': True}.items():
        _merged13[_k] = _v
    early = Record(_merged13)
    for attempt in range(5):
        session.start(early, attempt * 10000, lambda: 0)
        expect(session.death(attempt * 10000 + 1000)).to_be('reset')
        expect(session.memory.objective).to_be('attack')
        expect(session.memory.cooldowns).to_equal(Record({}))
    expect(session.memory.deaths).to_be(5)
    session.start(early, 60000, lambda: 0)
    expect(session.failure(61000)).to_be('reset')
    session.start(early, 62000, lambda: 0)
    expect(session.failure(63000)).to_be('rotate')
test('early death walking recovers repeatedly without cooling down the camp', _fn12)

def resolved_wait(value):
    if False:
        yield
    return value
