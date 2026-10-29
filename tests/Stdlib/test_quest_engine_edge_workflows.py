"""Quest orchestration handles modal cleanup, provisioning, death and safe completion."""

import rs2004.quests.engine.quest_engine as engine
from rs2004.quests.engine.types import QuestModule, QuestSnapshot, QuestPrayer, quest_step
from rs2004.quests.types import QuestRecord, QuestItem
from helpers import FakeModule
from quest_world import QuestWorld


class EngineWorld(QuestWorld):
    def __init__(self):
        QuestWorld.__init__(self)
        self.status = 'in_progress'
        self.open_bank = False
        self.step_ok = True
        self.death = False
        self.verbose = True
        self.picked = {'test'}
        self.steps = []
        self.states = []
        self.finishes = []
        self.record = QuestRecord('test', 'Test Quest')
        self.module = QuestModule(record=self.record, decide=lambda snap: quest_step('custom', name='work', run=None),
                                  owns_inventory=True, coin_float=0)
        self.host = FakeModule(log=self.logs.append, verbose=lambda: self.verbose, food_item=lambda: 'Lobster',
            skip_pending=lambda: False, consume_skip=lambda: False, consume_death=self.consume_death,
            picked_ids=lambda: self.picked, note_state=lambda *a: self.states.append(a), finish=self.finishes.append)

    def __enter__(self):
        QuestWorld.__enter__(self)
        self.install(engine)
        self.patch(engine, 'QUESTS', [self.record])
        self.patch(engine, 'QUEST_DEFS', [FakeModule(record=self.record, module=lambda: self.module)])
        self.patch(engine, 'def_by_id', lambda id: self.module)
        self.patch(engine, 'quests', FakeModule(status=lambda n: self.status, points=lambda: 99))
        self.patch(engine, 'bank', FakeModule(is_open=lambda: self.open_bank, loaded=lambda: True,
                                             ready=lambda: True, items=lambda: []))
        self.patch(engine, 'prayer_upkeep', lambda: self.reply(False))
        self.patch(engine, 'execute_step', self.execute_step)
        self.bot = engine.QuestEngine(self.host)
        return self

    def execute_step(self, step, hops, log):
        self.steps.append(step)
        log('action sent')
        yield from self.reply()
        return self.step_ok

    def consume_death(self):
        death = self.death
        self.death = False
        return death


def test_engine_cleans_leftover_modal_and_yields_to_events_and_open_bank():
    with EngineWorld() as w:
        assert w.bot.validate()
        w.interrupted = True
        w.run(w.bot.execute())
        assert not w.steps
        w.interrupted = False
        w.open_bank = True
        w.run(w.bot.execute())
        assert w.bot._bank_known
        w.open_bank = False
        w.pages = [('main', ['Quest complete!'])]
        w.run(w.bot.execute())
        assert not w.pages and 'closed a leftover' in w.logs[-1]


def test_engine_drained_queue_and_missing_definition_report_a_concrete_reason():
    with EngineWorld() as w:
        w.picked = set()
        w.run(w.bot.execute())
        assert 'queue drained' in w.finishes[-1]
        w.picked = {'test'}
        w.bot.running_id = 'test'
        w.patch(engine, 'def_by_id', lambda id: None)
        w.run(w.bot.execute())
        assert w.bot._blocked['test'] == ['internal: no module']


def test_engine_announces_readiness_observes_failed_step_and_reuses_verbose_sublog():
    with EngineWorld() as w:
        starts = []
        w.module.on_start = lambda: starts.append(True)
        w.module.warn_readiness = lambda: 'bring food'
        w.module.observe = lambda snap, step: ['observed ' + step.kind]
        w.step_ok = False
        w.run(w.bot.execute())
        assert starts == [True]
        assert 'observed custom' in ' '.join(w.logs)
        assert any(['[t1]' in line for line in w.logs])
        assert any(['action sent' in line for line in w.logs])
        assert w.bot._fail_streak == 1


def test_engine_finished_quest_retreats_before_clearing_its_latches():
    with EngineWorld() as w:
        w.status = 'complete'
        w.bot.running_id = 'test'
        w.bot._park_counts['test'] = 1
        w.module.exit = lambda log: w.reply(True)
        w.run(w.bot.execute())
        assert w.steps[-1].kind == 'scan_bank'
        assert w.bot.running_id is None and 'test' not in w.bot._park_counts
        assert any(['COMPLETE' in line for line in w.logs])
        w.step_ok = False
        w.bot._retreated.clear()
        for i in range(engine.RETREAT_GIVE_UP):
            w.run(w.bot._retreat_to_bank(w.module, 'test', []))
        assert w.run(w.bot._retreat_to_bank(w.module, 'test', []))


def test_engine_freshens_new_quest_pack_and_bounded_failed_bank_trips():
    for success in [True, False]:
        with EngineWorld() as w:
            w.status = 'not_started'
            w.hold('Junk')
            w.step_ok = success
            snap = QuestSnapshot(journal='not_started')
            for i in range(1 if success else engine.FRESH_GIVE_UP):
                assert w.run(w.bot._freshen_pack(w.module, 'test', snap, []))
            assert 'test' in w.bot._freshened
            assert w.steps[-1].keep == [] and w.steps[-1].leave_open


def test_engine_provision_draws_food_and_prayer_once_and_blocks_missing_gatherer():
    with EngineWorld() as w:
        w.bot._bank_known = True
        w.bot._last_bank_counts = {'lobster': 20, engine.PRAYER_POTION.lower(): 4}
        w.module.food = 5
        w.module.pray = QuestPrayer(potions=2)
        snap = QuestSnapshot(journal='in_progress', inv={})
        step = w.bot._provision_step(w.module, 'test', snap, {'test'}, {})
        assert step.kind == 'withdraw' and len(step.items) == 2
        snap.inv = {'lobster': 5, engine.PRAYER_POTION.lower(): 2}
        assert w.bot._provision_step(w.module, 'test', snap, {'test'}, {}).kind == 'custom'
        assert 'test' in w.bot._food_drawn and 'test' in w.bot._potions_drawn
        w.record.items = [QuestItem('Egg', 1, 'acquirable')]
        assert w.bot._provision_step(w.module, 'test', snap, {'test'}, {}) is None
        assert 'no gather' in w.bot._blocked['test'][0]
        w.module.gather = {'egg': lambda snap, need: quest_step('grab_ground', item='Egg')}
        assert w.bot._provision_step(w.module, 'test', snap, {'test'}, {}).item == 'Egg'


def test_engine_death_without_active_step_and_with_observer_clears_provisioning():
    with EngineWorld() as w:
        w.death = True
        assert w.run(w.bot._recover_death_if_pending())
        w.bot.running_id = 'test'
        w.bot._provisioned.add('test')
        w.module.observe = lambda snap, step: ['death observed']
        w.patch(engine, 'game_messages', FakeModule(recent=lambda n: [FakeModule(text='Oh dear, you are dead!')]))
        w.death = True
        assert w.run(w.bot._recover_death_if_pending())
        assert 'test' not in w.bot._provisioned and 'death observed' in ' '.join(w.logs)


def test_engine_step_descriptions_include_targets_and_quantities():
    cases = [(quest_step('talk', stop=FakeModule(npc='Doric')), 'Doric'),
        (quest_step('grab_ground', item='Egg'), 'Egg'), (quest_step('pick_loc', op='Pick', loc='Onion'), 'Onion'),
        (quest_step('use_on', item='Key', target='Door'), 'Door'), (quest_step('equip', item='Sword'), 'Sword'),
        (quest_step('deposit', keep=['coins']), '1 kept'), (quest_step('mine_rock', item='Clay'), 'Clay'),
        (quest_step('buy', item='Bucket', qty=2, shop=FakeModule(npc='Shop keeper')), '2'),
        (quest_step('done'), 'done')]
    for step, text in cases:
        assert text in engine.describe_step(step)
    assert engine.bank_for(QuestModule(bank='nearest')) is None
    assert engine._now_ms() > 0
