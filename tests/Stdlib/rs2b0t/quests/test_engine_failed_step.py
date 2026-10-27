"""rs2b0t's test/api/ai/quests/engine/failed-step.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect.

This fixture explicitly picks Rune Mysteries then Sheep Shearer; the goblin combat case uses 16b's real gather policy.
"""

from rs2004 import execution
from rs2004.bank import bank, banking
from rs2004.catalogs.record import Record
from rs2004.dialogue import modals
from rs2004.execution import event_signal
from rs2004.game import game, skills
from rs2004.geometry import Tile
from rs2004.items import equipment, inventory
from rs2004.messages import game_messages
from rs2004.quests.defs import def_by_id
from rs2004.quests.engine import quest_engine
from rs2004.quests.engine.quest_engine import QuestEngine
from rs2004.quests.engine.types import QuestPrayer, QuestProgress, quest_step
from rs2004.quests.types import QuestItem
from rs2004.tabs import quests

runemysteries = def_by_id('runemysteries')
sheepshearer = def_by_id('sheep')

# The fixture's world, which every fake reads.
S = {}


class Host:
    def __init__(self):
        self.food = None

    def log(self, m):
        pass

    def verbose(self):
        return False

    def food_item(self):
        return self.food

    def picked_ids(self):
        return S['picked']

    def skip_pending(self):
        return S['skip']

    def consume_skip(self):
        skip = S['skip']
        S['skip'] = False
        return skip

    def consume_death(self):
        death = S['death']
        S['death'] = False
        return death

    def note_state(self, rows, running, step_desc, no_progress, parked):
        S['rows'] = rows
        S['running'] = running

    def finish(self, reason):
        pass


def gather_ore(log):
    S['attempts'] += 1
    if S['gain']:
        S['ore'] += 1
    S['bank_open'] = S['bank_gain']
    return S['ok']
    yield


def fixture_decide(snap):
    if S['wait']:
        return quest_step('wait', reason='fixture wait')
    return quest_step('custom', name='gather ore', run=gather_ore)


def next_quest_run(log):
    return False
    yield


def banking_open(*args, **kwargs):
    S['bank_actions'].append('open')
    S['bank_open'] = True
    return True
    yield


def withdraw_x(name, qty):
    S['bank_actions'].append(f'withdraw:{name}:{qty}')
    S['bank_coins'] -= qty
    S['coins'] += qty
    return True
    yield


def close_modals():
    S['bank_open'] = False
    if S['bank_gain']:
        S['ore'] += 1
    return True
    yield


def bank_items():
    if S['bank_coins']:
        return [Record({'id': 995, 'name': 'Coins', 'count': S['bank_coins']})]
    return []


def inventory_items():
    out = []
    if S['ore']:
        out.append(Record({'id': 436, 'name': 'Copper ore', 'count': S['ore']}))
    if S['coins']:
        out.append(Record({'id': 995, 'name': 'Coins', 'count': S['coins']}))
    return out


def answer_true(cond, ms=0):
    return True
    yield


def fixture():
    S['ore'] = 0
    S['ok'] = False
    S['gain'] = False
    S['skip'] = False
    S['death'] = False
    S['bank_open'] = False
    S['bank_gain'] = False
    S['wait'] = False
    S['rows'] = []
    S['running'] = None
    S['attempts'] = 0
    S['coins'] = 0
    S['bank_coins'] = 0
    S['bank_actions'] = []
    S['picked'] = set(['runemysteries', 'sheep'])
    S['combat'] = False
    S['xp'] = 0
    S['now'] = 100000
    host = Host()
    spy_on(quest_engine, '_now_ms', impl=lambda: S['now'])
    spy_on(game, 'in_combat', impl=lambda: S['combat'])
    spy_on(skills, 'xp', impl=lambda name: S['xp'])
    spy_on(event_signal, 'pending', returns=False)
    spy_on(modals, 'main', returns=-1)
    spy_on(bank, 'is_open', impl=lambda: S['bank_open'])
    spy_on(bank, 'loaded', returns=True)
    spy_on(bank, 'ready', returns=True)
    spy_on(bank, 'items', impl=bank_items)
    spy_on(banking, 'open', impl=banking_open)
    spy_on(bank, 'withdraw_x', impl=withdraw_x)
    spy_on(modals, 'close', impl=close_modals)
    spy_on(game_messages, 'recent', returns=[])
    spy_on(equipment, 'items', returns=[])
    spy_on(game, 'tile', returns=Tile(3093, 3243, 0))
    spy_on(inventory, 'used', returns=0)
    spy_on(inventory, 'free', returns=28)
    spy_on(inventory, 'items', impl=inventory_items)
    spy_on(skills, 'level', returns=99)
    spy_on(skills, 'effective', returns=99)
    spy_on(quests, 'status', returns='in_progress')
    spy_on(quests, 'points', returns=100)
    spy_on(execution, 'delay_ticks', impl=instant_ticks)
    spy_on(execution, 'delay_until', impl=answer_true)
    stub(sheepshearer, read_stage=lambda: 0, decide=lambda snap: quest_step('custom', name='next quest', run=next_quest_run))
    stub(runemysteries, decide=fixture_decide)
    engine = QuestEngine(host)
    for id in ['runemysteries', 'sheep']:
        engine._provisioned.add(id)
        engine._deposited.add(id)
        engine._freshened.add(id)
    return engine, host


def execute(engine, count):
    for i in range(count):
        yield from engine.execute()


def row_status(id):
    for row in S['rows']:
        if row.id == id:
            return row.status
    return None


# The oracle tests: does not park when the eighth false step advances only flags, or only the stage.

def read_flags():
    S['reads'] += 1
    return QuestProgress(1, set(['scroll-read'] if S['attempts'] >= 8 else []))
    yield


def read_stage_advancing():
    S['reads'] += 1
    return 2 if S['attempts'] >= 8 else 1
    yield


def oracle_test(oracle):
    def body():
        engine, host = fixture()
        S['reads'] = 0
        if oracle == 'flags':
            stub(runemysteries, read_progress=read_flags)
        else:
            stub(runemysteries, read_stage=read_stage_advancing)
        yield from execute(engine, 8)
        expect(engine.running_id).to_be('runemysteries')
        expect(S['reads']).to_be(8)
        yield from engine.execute()
        expect(S['attempts']).to_be(9)
        expect(engine.running_id).to_be('runemysteries')
        expect(engine._no_progress_count).to_be(1)
        expect(S['reads']).to_be(9)
    return body


for _oracle in ['flags', 'stage']:
    test(f'does not park when the eighth false step advances only {_oracle}', oracle_test(_oracle))


def _parks():
    engine, host = fixture()
    yield from execute(engine, 9)
    expect(S['attempts']).to_be(8)
    expect(S['running']).to_be('sheep')
    expect(row_status('runemysteries')).to_be('PARKED')


test('parks eight unchanged failures and runs the next quest', _parks)


def read_stage_one():
    return 1
    yield


def _confirms():
    engine, host = fixture()
    stub(runemysteries, read_stage=read_stage_one)
    yield from execute(engine, 9)
    expect(S['attempts']).to_be(8)
    expect(engine.running_id).to_be_null()
    yield from engine.execute()
    expect(S['running']).to_be('sheep')
    expect(row_status('runemysteries')).to_be('PARKED')


test('confirms an unchanged oracle without executing a ninth failed step', _confirms)


def interruption_test(interruption):
    def body():
        engine, host = fixture()
        stub(runemysteries, read_stage=read_stage_one)
        yield from execute(engine, 8)
        S[interruption] = True
        yield from execute(engine, 7)
        expect(engine.running_id).to_be('sheep' if interruption == 'skip' else 'runemysteries')
    return body


for _interruption in ['skip', 'death']:
    test(f'{_interruption} clears a pending threshold confirmation', interruption_test(_interruption))


def _gains():
    engine, host = fixture()
    S['gain'] = True
    yield from execute(engine, 20)
    expect(S['ore']).to_be(20)
    expect(S['running']).to_be('runemysteries')
    expect(engine._no_progress_count).to_be(0)


test('preserves false-returning retries that gain ore', _gains)


def _fight():
    engine, host = fixture()
    S['combat'] = True
    for i in range(80):
        S['now'] += 1200
        if i % 10 == 0:
            S['xp'] += 1
        yield from engine.execute()
    expect(S['attempts']).to_be(80)
    expect(engine.running_id).to_be('runemysteries')


test('keeps a cooperative fight active through misses while combat XP advances', _fight)


def _stalled_fight():
    engine, host = fixture()
    S['combat'] = True
    for i in range(45):
        S['now'] += 1200
        yield from engine.execute()
    expect(engine.running_id).to_be('runemysteries')
    for i in range(20):
        S['now'] += 1200
        yield from engine.execute()
    expect(row_status('runemysteries')).to_be('PARKED')


test('still parks a fight that makes no combat progress for over a minute', _stalled_fight)


def _success_resets():
    engine, host = fixture()
    yield from execute(engine, 7)
    S['ok'] = True
    yield from engine.execute()
    S['ok'] = False
    yield from execute(engine, 7)
    expect(engine.running_id).to_be('runemysteries')
    yield from execute(engine, 2)
    expect(S['running']).to_be('sheep')


test('success resets the failed-attempt budget', _success_resets)


def _switching():
    engine, host = fixture()
    yield from execute(engine, 7)
    S['skip'] = True
    yield from execute(engine, 7)
    expect(engine.running_id).to_be('sheep')
    yield from execute(engine, 2)
    expect(engine.running_id).to_be_null()


test('switching quests clears the failed-attempt budget', _switching)


def _bank_settles():
    engine, host = fixture()
    S['bank_gain'] = True
    yield from execute(engine, 20)
    expect(S['ore']).to_be(20)
    expect(engine._no_progress_count).to_be(0)
    expect(S['running']).to_be('runemysteries')


test('observes partial progress after the bank settles and closes', _bank_settles)


def _death():
    engine, host = fixture()
    yield from execute(engine, 7)
    S['death'] = True
    yield from engine.execute()
    yield from engine.execute()
    expect(S['bank_actions']).to_equal(['open'])
    yield from execute(engine, 7)
    expect(engine.running_id).to_be('runemysteries')
    yield from execute(engine, 2)
    expect(S['running']).to_be('sheep')


test('death recovery clears the failed-attempt budget', _death)


def _successful_unchanged():
    engine, host = fixture()
    S['ok'] = True
    yield from execute(engine, 8)
    expect(engine.running_id).to_be('runemysteries')
    yield from execute(engine, 2)
    expect(S['attempts']).to_be(9)
    expect(S['running']).to_be('sheep')


test('successful unchanged steps retain their original watchdog budget', _successful_unchanged)


def _waits():
    engine, host = fixture()
    S['wait'] = True
    yield from execute(engine, 14)
    expect(engine.running_id).to_be('runemysteries')
    yield from execute(engine, 2)
    expect(S['running']).to_be('sheep')


test('wait steps retain their separate fifteen-step budget', _waits)


def _coin_float():
    engine, host = fixture()
    stub(runemysteries.record, items=[])
    stub(runemysteries, coin_float=1000)
    S['picked'] = set(['runemysteries'])
    S['bank_coins'] = 6204130
    engine._provisioned.discard('runemysteries')
    engine._freshened.discard('runemysteries')
    spy_on(inventory, 'used', impl=lambda: 1 if S['coins'] > 0 else 0)
    spy_on(quests, 'status', returns='not_started')
    yield from execute(engine, 3)
    expect(S['bank_actions']).to_equal(['open', 'open', 'withdraw:Coins:1000'])
    expect(S['coins']).to_be(1000)
    expect(S['attempts']).to_be(1)


test('an empty pack checks an unknown bank for the coin float before starting a quest', _coin_float)


def supply_test(supply):
    def body():
        engine, host = fixture()
        stub(runemysteries.record, items=[])
        stub(runemysteries, coin_float=0, food=8 if supply == 'food' else 0,
             pray=QuestPrayer('melee', 2) if supply == 'prayer' else None)
        host.food = 'Lobster'
        S['picked'] = set(['runemysteries'])
        engine._provisioned.discard('runemysteries')
        yield from engine.execute()
        expect(S['bank_actions']).to_equal(['open'])
        expect(S['attempts']).to_be(0)
    return body


for _supply in ['food', 'prayer']:
    test(f'checks an unknown bank for {_supply} even when the quest needs no coins', supply_test(_supply))


SCENARIOS = [
    {'name': 'unknown bank scans then withdraws banked mustHave supplies', 'bank_known': False, 'bank_coins': 20000, 'coins': 0,
     'owns_inventory': False, 'ticks': 3, 'actions': ['open', 'open', 'withdraw:Coins:1'], 'attempts': 1, 'blocked': False, 'held': 1},
    {'name': 'known empty bank gives up after three parks', 'bank_known': True, 'bank_coins': 0, 'coins': 0, 'owns_inventory': False,
     'ticks': 3, 'actions': [], 'attempts': 0, 'blocked': True, 'held': 0},
    {'name': 'carried supplies need no bank scan', 'bank_known': False, 'bank_coins': 20000, 'coins': 1, 'owns_inventory': False,
     'ticks': 1, 'actions': [], 'attempts': 1, 'blocked': False, 'held': 1},
    {'name': 'ownsInventory keeps control without an unknown-bank scan', 'bank_known': False, 'bank_coins': 20000, 'coins': 0,
     'owns_inventory': True, 'ticks': 1, 'actions': [], 'attempts': 1, 'blocked': False, 'held': 0},
]


def scenario_test(scenario):
    def body():
        engine, host = fixture()
        stub(runemysteries.record, items=[QuestItem('Coins', 1, 'mustHave')])
        stub(runemysteries, coin_float=0, owns_inventory=scenario['owns_inventory'])
        S['picked'] = set(['runemysteries'])
        S['bank_coins'] = scenario['bank_coins']
        S['coins'] = scenario['coins']
        engine._bank_known = scenario['bank_known']
        engine._provisioned.discard('runemysteries')
        yield from execute(engine, scenario['ticks'])
        expect(S['bank_actions']).to_equal(scenario['actions'])
        expect(S['coins']).to_be(scenario['held'])
        expect(S['attempts']).to_be(scenario['attempts'])
        expect('runemysteries' in engine._blocked).to_be(scenario['blocked'])
    return body


for _scenario in SCENARIOS:
    test(_scenario['name'], scenario_test(_scenario))


# Not rs2b0t's: it counts the pack alone, so a quest restarted while wearing its must-have items, as Black Knights'
# Fortress is in its disguise, parked on them as missing and was given up.
def _worn_supplies():
    engine, host = fixture()
    stub(runemysteries.record, items=[QuestItem('Iron chainbody', 1, 'mustHave')])
    stub(runemysteries, coin_float=0)
    spy_on(equipment, 'items', returns=[Record({'id': 1101, 'name': 'Iron chainbody', 'count': 1})])
    S['picked'] = set(['runemysteries'])
    engine._bank_known = True
    engine._provisioned.discard('runemysteries')
    yield from engine.execute()
    expect(S['attempts']).to_be(1)
    expect('runemysteries' in engine._blocked).to_be(False)
    expect(len(engine._parked)).to_be(0)


test('a worn mustHave item counts as held', _worn_supplies)


def _goblin_progress():
    from rs2004.entities import npcs, ground_items
    from rs2004.catalogs.tasks import sustain
    from rs2004.quests.defs.goblindiplomacy import goblin_mail_gather_step
    engine, host = fixture()
    S['coins'] = 500
    S['combat'] = True
    S['goblin_hp'] = 30
    tile = Tile(2958, 3507, 0)
    spy_on(game, 'tile', returns=tile)
    spy_on(game, 'my_name', returns='quest-combat-fixture')
    spy_on(ground_items, 'query', impl=querying(lambda: []))
    def goblins():
        return [Fake(id=100, index=1, name='Goblin', level=2, size=1, tile=lambda: Tile(2958,3508,0),
                     distance=lambda: 1, actions=lambda: ['Attack'], in_combat=True, health=S['goblin_hp'],
                     max_health=30, targets_me=lambda: True, targets_another_player=lambda: False, valid=lambda: True)]
    spy_on(npcs, 'query', impl=querying(goblins))
    spy_on(npcs, 'all', impl=goblins)
    def fight_tick():
        S['goblin_hp'] -= 1
        S['xp'] += 4
        yield
    spy_on(sustain, 'run', impl=fight_tick)
    stub(runemysteries, decide=lambda snap: goblin_mail_gather_step(snap))
    run_wait(execute(engine,12))
    expect(S['goblin_hp']).to_be_less_than(22)
    expect(engine.running_id).to_be('runemysteries')
    expect(engine._no_progress_count).to_be(0)
test('goblin mail gathering keeps fighting when its step yields before the drop', _goblin_progress)
