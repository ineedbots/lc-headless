"""Ported from rs2b0t's src/bot/../../test/scripts/accountLevelerLostCity.test.ts (MIT, see thirdparty/rs2b0t)."""

class Idle(LoopingBot):

    def loop(self):
        pass

class Idle(LoopingBot):

    def loop(self):
        pass
import _core
from bots.account_leveler.record import Record
from bots.account_leveler.bot import AccountLeveler
from bots.account_leveler.manifests import manifest_for
from bots.account_leveler.planner import empty_memory, enabled_skills, plan_next
from bots.account_leveler.equipment import melee_equipment
from bots.account_leveler.dragons import dragon_prayer
from bots.account_leveler.supplies import provision

def snapshot():
    return Record({'levels': {_k: _v for _k, _v in [[skill, 50] for skill in enabled_skills]}, 'target': 60, 'now': 1000, 'bank_ready': True, 'wilderness': False, 'quests': Record({'Dragon Slayer': True}), 'stock': Record({'coins': 1000000, 'lobster': 100, 'diamond': 1, 'dragonfire shield': 1, 'mithril scimitar': 1})})

def _fn1(*_args):
    decision = plan_next(snapshot(), empty_memory(), lambda: 0)
    expect(decision.kind).to_be('activity')
    if decision.kind != 'activity':
        return
    expect(decision.plan.script).to_be('AIOQuester')
    expect(decision.plan.settings.get('quests')).to_equal(['zanaris'])
    expect(decision.plan.quest).to_be('Lost City')
    expect(any([need.equip for need in decision.plan.needs])).to_be(False)
test('an eligible account schedules Lost City before ordinary training', _fn1)

def _fn2(skill, level, *_args):
    s = snapshot()
    s.levels[skill] = level
    decision = plan_next(s, empty_memory(), lambda: 0)
    expect(decision.kind == 'activity' and decision.plan.quest).not_.to_be('Lost City')
test_each([['crafting', 30], ['woodcutting', 35]])('Lost City waits for %s readiness', _fn2)

def _fn3(*_args):
    s = snapshot()
    for _k, _v in Record({'attack': 20, 'strength': 20, 'defence': 20, 'hitpoints': 25, 'magic': 13}).items():
        s.levels[_k] = _v
    s.levels
    expect(plan_next(s, empty_memory(), lambda: 0)).to_match_object(Record({'kind': 'activity', 'plan': Record({'quest': 'Lost City'})}))
test('Lost City does not impose Dragon Slayer melee requirements on its spell-based fights', _fn3)

def _fn4(*_args):
    s = snapshot()
    s.stock.pop('diamond', None)
    expect(plan_next(s, empty_memory(), lambda: 0)).not_.to_match_object(Record({'kind': 'activity', 'plan': Record({'quest': 'Lost City'})}))
    s.stock['law rune'] = 1
    decision = plan_next(s, empty_memory(), lambda: 0)
    expect(decision).to_match_object(Record({'kind': 'activity', 'plan': Record({'quest': 'Lost City'})}))
    if decision.kind == 'activity':
        expect(decision.plan.needs).to_contain_equal(Record({'item': 'Law rune', 'count': 1}))
    if decision.kind == 'activity':
        expect(decision.plan.needs).to_contain_equal(Record({'item': 'Air rune', 'count': 303}))
        expect(decision.plan.needs).to_contain_equal(Record({'item': 'Fire rune', 'count': 451}))
        expect(decision.plan.needs).to_contain_equal(Record({'item': 'Mind rune', 'count': 150}))
test('Lost City reserves a way home, accepting teleport runes without a Diamond', _fn4)

def _fn5(*_args):
    s = snapshot()
    memory = empty_memory()
    memory.cooldowns['quest-zanaris'] = s.now + 1000
    expect(plan_next(s, memory, lambda: 0)).to_match_object(Record({'kind': 'activity', 'plan': Record({'script': 'AutoFighter'})}))
    s.quests['Lost City'] = True
    expect(plan_next(s, empty_memory(), lambda: 0)).to_match_object(Record({'kind': 'activity', 'plan': Record({'script': 'AutoFighter'})}))
test('completed and cooling-down Lost City attempts leave training available', _fn5)

def _fn6(*_args):
    s = snapshot()
    s.levels['attack'] = 60
    s.quests['Lost City'] = True
    s.stock['dragon dagger'] = 1
    expect((melee_equipment(s) or [None])[0].item).to_be('Dragon dagger')
    s.stock['dragon longsword'] = 1
    expect((melee_equipment(s) or [None])[0].item).to_be('Dragon longsword')
    expect(((dragon_prayer(s, empty_memory(), lambda: 0).settings if dragon_prayer(s, empty_memory(), lambda: 0) is not None else None)).get('weapon')).to_be('Dragon longsword')
    s.levels['attack'] = 59
    expect((melee_equipment(s) or [None])[0].item).not_.to_start_with('Dragon')
    s.levels['attack'] = 60
    s.quests['Lost City'] = False
    expect((melee_equipment(s) or [None])[0].item).not_.to_start_with('Dragon')
test('owned dragon weapons replace scimitars only at Attack 60 with Lost City complete', _fn6)

def fixture():
    bank = Record({'Coins': 1000000, 'Dramen staff': 1, 'Diamond': 1})
    held = Record({})
    worn = Record({})
    purchases = []
    trips = []
    unlocked = [True]

    def _fn7():
        return True
        if False:
            yield

    def _fn8():
        for name, count in held.items():
            _v9 = bank.get(name)
            bank[name] = ((_v9 if _v9 is not None else 0)) + count
            held.pop(name)
        if False:
            yield

    def _fn11(name):
        held[name] = worn.get(name)
        worn.pop(name)
        return True
        if False:
            yield

    def _fn12(name, count):
        _v13 = bank.get(name)
        if ((_v13 if _v13 is not None else 0)) < count:
            return False
        bank[name] -= count
        _v14 = held.get(name)
        held[name] = ((_v14 if _v14 is not None else 0)) + count
        return True
        if False:
            yield

    def _fn15():
        return True
        if False:
            yield

    def _fn16(*_args):
        trips.append('walk')
        return True
        if False:
            yield

    def _fn17(keeper):
        trips.append(keeper)
        return True
        if False:
            yield

    def _fn18(name, count):
        purchases.append(name)
        held['Coins'] -= (100000 if name == 'Dragon longsword' else 30000)
        _v19 = held.get(name)
        held[name] = ((_v19 if _v19 is not None else 0)) + count
        return count
        if False:
            yield

    def _fn20(name):
        worn[name] = held.get(name)
        held.pop(name)
        return True
        if False:
            yield

    def _fn21():
        expect(worn.get('Dramen staff')).to_be(1)
        expect(held.get('Diamond')).to_be(1)
        held['Diamond'] -= 1
        trips.append('enter')
        return True
        if False:
            yield

    def _fn22():
        trips.append('leave')
        return True
        if False:
            yield
    port = Record({'bank': _fn7, 'deposit': _fn8, 'stock': lambda: {_k: _v for _k, _v in [[name.lower(), count] for name, count in list(bank.items())]}, 'held': lambda name: (held.get(name) if held.get(name) is not None else 0), 'worn': lambda name: (worn.get(name) if worn.get(name) is not None else 0), 'equipment': lambda: list(worn.keys()), 'unequip': _fn11, 'withdraw': _fn12, 'close_bank': _fn15, 'walk': _fn16, 'shop': _fn17, 'shop_stock': lambda *_args: 2, 'buy': _fn18, 'close_shop': lambda *_args: resolved_wait(None), 'equip': _fn20, 'log': lambda *_args: None, 'dragon_shop': Record({'ready': lambda: unlocked[0], 'enter': _fn21, 'leave': _fn22})})
    return Record({'bank': bank, 'held': held, 'worn': worn, 'port': port, 'purchases': purchases, 'trips': trips, 'lock': lambda: unlocked.__setitem__(0, False)})
upgrade = Record({'id': 'quest-zanaris-weapons', 'label': 'Dragon weapons', 'objective': 'attack', 'script': '', 'settings': Record({}), 'needs': [Record({'item': 'Dragon longsword', 'count': 1}), Record({'item': 'Dragon dagger', 'count': 1})]})

def _fn23(*_args):
    f = fixture()
    yield from provision(upgrade, f.port)
    expect(f.purchases).to_equal(['Dragon longsword', 'Dragon dagger'])
    expect(f.trips).to_equal(['enter', 'Jakut', 'leave'])
    expect(f.bank.get('Dragon longsword')).to_be(1)
    expect(f.bank.get('Dragon dagger')).to_be(1)
    expect(f.bank.get('Coins')).to_be(870000)
    if False:
        yield
test('one shop trip banks both dragon weapons, consumes one diamond and preserves travel funds', _fn23)

def _fn24(*_args):
    f = fixture()
    f.lock()
    reject(lambda: provision(upgrade, f.port), 'Lost City')
    expect(f.purchases).to_equal([])
    expect(f.trips).to_equal([])
    if False:
        yield
test('locked dragon shop never starts a purchase trip', _fn24)

def _fn25(*_args):
    f = fixture()
    f.port.shop_stock = lambda name: (0 if name == 'Dragon dagger' else 2)

    def _fn26():
        return not 'enter' in f.trips or 'leave' in f.trips
        if False:
            yield
    f.port.bank = _fn26
    reject(lambda: provision(upgrade, f.port), 'stock')
    expect(f.bank.get('Dragon longsword')).to_be(1)
    expect(f.bank.get('Coins')).to_be(900000)
    _v27 = f.held.get('Coins')
    expect((_v27 if _v27 is not None else 0)).to_be(0)
    expect(f.trips).to_contain('leave')
test('a partial dragon purchase leaves the market and banks the weapon and change before rejecting', _fn25)

def _fn28(*_args):
    f = fixture()
    f.held['Dragon dagger'] = 1
    f.worn['Dragon longsword'] = 1
    yield from provision(upgrade, f.port)
    expect(f.purchases).to_equal([])
    expect(f.trips).to_equal([])
    expect(f.bank.get('Dragon longsword')).to_be(1)
    expect(f.bank.get('Dragon dagger')).to_be(1)
    if False:
        yield
test('owned bank, inventory and worn dragon weapons avoid duplicate purchases', _fn28)

def _fn29(*_args):
    from rs2004.settings import SettingsBag
    f = fixture()
    f.port.shop_stock = lambda name: 0
    s = snapshot()
    s.levels['attack'] = 60
    s.quests['Lost City'] = True
    s.stock = Record(f.port.stock())
    bot = AccountLeveler()
    bot.bind_log(lambda message: None)
    bot._supplies = f.port
    bot.settings = SettingsBag({})
    yield from bot._try_dragon_weapons(s)
    assert f.trips.count('enter') == 1
    assert 'leave' in f.trips
    assert bot._session.memory.cooldowns['quest-zanaris-weapons'] > s.now
    yield from bot._try_dragon_weapons(s)
    assert f.trips.count('enter') == 1
test('an already-running leveler audits newly unlocked dragon weapons and cools down failed purchases', _fn29)

def _fn37(*_args):
    import bots.account_leveler.bot as controller
    f = fixture()
    f.bank['Logs'] = 28
    f.bank['Tinderbox'] = 1
    s = snapshot()
    s.quests['Lost City'] = True
    for skill in enabled_skills:
        s.levels[skill] = 60
    s.levels['woodcutting'] = 1
    s.levels['firemaking'] = 1
    s.stock = Record(f.port.stock())
    state = Record({'tile': Tile(3153, 9576), 'events': []})
    bot = AccountLeveler()
    bot.bind_log(lambda message: None)
    bot._shopping_checked = True
    bot._session.memory.cooldowns['quest-zanaris-weapons'] = _core.step_time() + 60000
    bot._session.memory.objective = 'firemaking'
    bot._supplies = f.port

    def leave(port):
        state.events.append('exit')
        state.tile = Tile(3260, 3171)
        return True
        yield

    def prepare(plan, port, report=None):
        state.events.append('provision')
        assert state.tile.z < 9000
        return None
        yield
    spy_on(AccountLeveler, '_snapshot').mock_return_value(s)
    spy_on(AccountLeveler, '_observe').mock_return_value(None)
    spy_on(game, 'tile').mock_implementation(lambda: state.tile)
    spy_on(controller, 'leave_zanaris').mock_implementation(leave)
    spy_on(controller, 'provision').mock_implementation(prepare)
    spy_on(ScriptActivity, 'start').mock_implementation(lambda *args: resolved_wait(None))
    yield from bot._select_and_start()
    assert state.events == ['exit', 'provision']
    assert bot._session.plan.script == 'Firemaker'
test('the leveler leaves Zanaris before provisioning a full inventory training activity', _fn37)

def resolved_wait(value):
    if False:
        yield
    return value

def reject(call, text):
    try:
        run_wait(call())
    except Exception as error:
        assert text in str(error), str(error)
        return
    raise AssertionError('expected an error')
