"""AccountLevelerController.test.ts, adapted to the host's tick hooks and generator waits (rs2b0t, MIT)."""

import _core
import bots.account_leveler.bot as controller
from bots.account_leveler.bot import AccountLeveler
from bots.account_leveler.record import Record
from bots.account_leveler.planner import empty_memory, enabled_skills
from bots.account_leveler.supplies import SupplyStockError, SupplyUnavailableError
from rs2004.settings import SettingsBag, settings_store


def snapshot():
    return Record({'levels': {skill: 10 if skill == 'hitpoints' else 1 for skill in enabled_skills},
                   'stock': {'coins': 100000}, 'quests': {}, 'bank_ready': True,
                   'target': 40, 'wilderness': False, 'now': _core.step_time()})


def activity(combat=True, needs=None):
    return Record({'id': 'lumbridge-chickens' if combat else 'fish-shrimps', 'label': 'training',
                   'objective': 'attack', 'script': 'AutoFighter' if combat else 'Fisher',
                   'combat': combat, 'settings': {}, 'needs': needs or []})


def resolved(value=None):
    if False:
        yield
    return value


class Child:
    def __init__(self):
        self.child = None
        self.outcome = None
        self.calls = 0
        self.stops = 0
        self.starts = []

    def start(self, manifest, overrides):
        self.starts.append([manifest, overrides])
        return None
        yield

    def loop(self):
        self.calls += 1
        return None
        yield

    def stop(self):
        self.stops += 1

    def interrupt(self, reason):
        self.outcome = Record({'kind': 'interrupted', 'reason': reason})


class Controller(AccountLeveler):
    def __init__(self):
        AccountLeveler.__init__(self)
        self.snap = snapshot()
        self.settings = SettingsBag({'market_axes': False})
        self._activity = Child()
        self._shopping_checked = True
        self.logs = []
        self.bind_log(self.logs.append)
        self.saved = 0
        self._supplies = Record({'bank': lambda: resolved(True), 'walk': lambda tile: resolved(True)})

    def _snapshot(self):
        return self.snap

    def _save(self):
        self.saved += 1

    def _observe(self):
        pass

    def _eat(self):
        if False:
            yield

    def train(self, plan):
        self._session.start(plan, _core.step_time(), lambda: 0)
        self._phase = 'train'


def setup():
    spy_on(game, 'scene_ready', returns=True)
    spy_on(game, 'tile', returns=Tile(3222, 3222))
    spy_on(game, 'in_combat', returns=False)
    spy_on(bank, 'is_open', returns=False)
    spy_on(bank, 'ready', returns=False)
    spy_on(bank, 'items', returns=[])
    spy_on(bank, 'close', impl=lambda: resolved(True))
    spy_on(inventory, 'count', returns=0)
    spy_on(controller, 'provision', impl=lambda *args: resolved())


def combat_boundary():
    setup()
    bot = Controller()
    plan = activity()
    plan.death_walk = True
    bot.train(plan)
    bot._pending_plans = [plan]
    bot.snap.levels['attack'] = 12
    bot.snap.levels['strength'] = 12
    bot.snap.levels['defence'] = 12
    bot.snap.levels['hitpoints'] = 17
    spy_on(game, 'in_combat', returns=True)
    run_wait(bot.loop())
    assert bot._session.plan is plan
    spy_on(game, 'in_combat', returns=False)
    run_wait(bot.loop())
    assert bot._phase == 'bank'
    assert bot._session.plan is None
    assert bot._retry is None
    assert bot._pending_plans == []
    assert bot._session.memory.cooldowns._fields == {}


test('reaching combat 15 finishes the current fight then banks for food without resuming the death walk', combat_boundary)


def stale_death_walk(source):
    setup()
    bot = Controller()
    plan = activity()
    plan.death_walk = True
    bot.snap.levels = Record({skill: 20 for skill in enabled_skills})
    if source == 'retry':
        bot._retry = plan
    else:
        bot._pending_plans = [plan]
    run_wait(bot._select_and_start())
    assert not bot._session.plan.death_walk
    assert bot._session.plan.script in ['Fisher', 'CookBot']


test_each(['retry', 'pending'])('combat 15 replaces a stale death walk from %s with food preparation', stale_death_walk)


def pending_bank():
    setup()
    bot = Controller()
    def wait_bank():
        while True:
            yield ('update', 20)
    bot._supplies.bank = wait_bank
    step = bot.loop()
    next(step)
    initial_progress = bot._session._progress_at
    bot._last_logged_at = _core.step_time() - 30001
    bot.on_tick(1)
    assert 'nearest bank' in bot.logs[-1]
    assert '3222' in bot.logs[-1]
    assert bot._session._progress_at == initial_progress


test('a pending bank operation reports its action and position without claiming progress', pending_bank)


def sample_pending_child():
    setup()
    bot = Controller()
    bot.train(activity())
    bot._session.sample_work(_core.step_time() - 600, False)
    spy_on(game, 'animating', returns=True)
    spy_on(bank, 'items', returns=[Record({'id': 995, 'name': 'Coins', 'count': 9000})])
    spy_on(bank, 'ready', returns=True)
    before = bot._session.remaining_ms
    bot.on_tick(1)
    assert bot._stock.ready
    assert bot._stock.total([])['coins'] == 9000
    assert bot._session.remaining_ms == before - 600


test('controller observes bank changes and training while a delegated loop is pending', sample_pending_child)


def failed_optional_stock():
    setup()
    bot = Controller()
    bot._shopping_checked = False
    def broken(*args):
        raise RuntimeError('shop failed')
        yield
    spy_on(controller, 'provision', impl=broken)
    run_wait(bot.loop())
    assert bot._shopping_checked
    assert bot._last_failure.reason == 'shop failed'
    assert bot._phase == 'bank'


test('a failed optional stock-up is recorded and yields to normal planning on retry', failed_optional_stock)


def out_of_stock():
    setup()
    bot = Controller()
    def empty_shop(*args):
        raise SupplyStockError('sold out', ['Steel axe'])
        yield
    spy_on(controller, 'provision', impl=empty_shop)
    run_wait(bot.loop())
    assert bot._phase == 'bank'
    assert bot._temporarily_unavailable['steel axe'] > _core.step_time()
    assert 'steel axe' not in bot._unavailable_items
    assert bot._session.memory.cooldowns._fields == {}
    assert bot._session.plan is None


test('empty shop stock retries without blacklisting the item or the activity', out_of_stock)


def exhausted_ammo():
    setup()
    bot = Controller()
    plan = activity(needs=[Record({'item': 'Bronze arrow', 'count': 300, 'minimum': 1, 'equip': True})])
    bot.train(plan)
    run_wait(bot.loop())
    assert bot._phase == 'bank'
    assert bot._retry is plan
    assert bot._session.memory.cooldowns._fields == {}


test('consuming the last equipped arrow triggers resupply rather than a failed combat attempt', exhausted_ammo)


def bounded_preparation():
    setup()
    bot = Controller()
    plan = activity(False)
    bot._session.plan = plan
    for attempt in range(20):
        bot._fail('bank unavailable')
        assert bot._phase == 'bank'
        assert bot._waiting_until <= _core.step_time() + 60000
    assert bot._session.memory.cooldowns._fields == {}
    assert bot._session.plan is None


test('bank preparation errors do not count as failed fishing attempts', bounded_preparation)


def rotate_failed_combat():
    setup()
    bot = Controller()
    plan = activity()
    bot._session.plan = plan
    for attempt in range(3):
        bot._fail('bank unavailable')
    assert bot._session.plan is None
    assert bot._retry is None
    assert bot._session.memory.cooldowns[plan.id] > _core.step_time()


test('repeated combat preparation failure abandons the plan, not the account leveler', rotate_failed_combat)


def route_failure(combat):
    setup()
    bot = Controller()
    plan = activity(combat)
    plan.travel = Tile(3220, 3210)
    bot._retry = plan
    bot._supplies.walk = lambda tile: resolved(False)
    run_wait(bot.loop())
    assert bot._phase == 'bank'
    if combat:
        assert bot._session.memory.cooldowns[plan.id] > _core.step_time()
    else:
        assert bot._session.memory.cooldowns._fields == {}


test_each([True, False])('exhausted route replans without stopping and cools down only combat camps: %s', route_failure)


def completion():
    setup()
    bot = Controller()
    bot.snap.levels = Record({skill: 40 for skill in enabled_skills})
    bot.snap.quests['Lost City'] = True
    finishes = []
    bot.bind_finish(finishes.append)
    run_wait(bot.loop())
    assert len(finishes) == 1
    assert '19 enabled skills' in finishes[0]


test('reaching every target still finishes the leveler', completion)


def saved_progress():
    bot = Controller()
    spy_on(settings_store, 'saved', returns={
        'objective': 'attack', 'recent': ['one', 3, 'two'], 'deaths': 2,
        'cooldowns': {'fish-shrimps': 1000, 'quest-dragon': 1000, 'prayer-blue-dragons': 1000, 'ranging-guild': 1000},
        'attempted': {'attack': 3, 'strength': 'bad'},
        'diagnostics': {'failure': {'reason': 'original failure'}, 'history': [{'at': 0, 'message': 'saved'}]},
    })
    bot._load()
    assert bot._session.memory.objective == 'attack'
    assert bot._session.memory.recent == ['one', 'two']
    assert bot._session.memory.deaths == 2
    assert 'fish-shrimps' not in bot._session.memory.cooldowns
    assert bot._session.memory.cooldowns['quest-dragon'] == _core.step_time() + 1000
    assert bot._session.memory.cooldowns['ranging-guild'] == _core.step_time() + 1000
    for i in range(100):
        bot._actions.note(str(i))
    assert bot._last_failure['reason'] == 'original failure'


test('saved gathering cooldowns are removed while the original failure survives diagnostic history rotation', saved_progress)


def guild_failure():
    setup()
    bot = Controller()
    plan = Record({'id': 'ranging-guild', 'objective': 'ranged', 'label': 'Ranging Guild',
                   'script': 'RangingGuild', 'needs': [{'item': 'Coins', 'count': 1000, 'carry': 1000}], 'settings': {}})
    bot.snap.stock['coins'] = 600
    for attempt in range(2):
        bot.train(plan)
        bot._waiting_until = 0
        bot._activity.outcome = Record({'kind': 'failed', 'reason': 'RangingGuild: gave up after 3 recoveries'})
        run_wait(bot.loop())
    assert bot._session.memory.cooldowns['ranging-guild'] > _core.step_time()
    assert bot._retry is None


test('failed guild rounds enter cooldown even after some entry coins were spent', guild_failure)
