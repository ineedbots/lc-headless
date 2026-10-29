"""Catalog persistence, fire acknowledgements and recovery failure boundaries."""

import rs2004.catalogs.firemaking as fires
import rs2004.catalogs.loadout as loadout
import rs2004.catalogs.tools as tools
import rs2004.catalogs.pack as pack
import rs2004.market.price_book as prices
import rs2004.upkeep as upkeep
import rs2004.activity as activity
from rs2004 import execution
from rs2004.geometry import Tile
from rs2004.bot import LoopingBot, define_bot
from helpers import FakeModule, raises
from coverage_world import PatchWorld


class FireWorld(PatchWorld):
    def __init__(self):
        PatchWorld.__init__(self)
        self.logs_held = 2
        self.xp = 0
        self.accept = True
        self.outcome = 'lit'
        self.messages = []
        self.pending_fire = False
        self.animation = False
        self.interrupted = False
        self.have_tinder = True

    def __enter__(self):
        PatchWorld.__enter__(self)
        self.patch(fires, 'inventory', self)
        self.patch(fires, 'skills', FakeModule(xp=lambda skill: self.xp))
        self.patch(fires, 'game', FakeModule(animating=lambda: self.animation))
        self.patch(fires, 'event_signal', FakeModule(pending=lambda: self.interrupted))
        self.patch(fires, 'game_messages', FakeModule(mark=lambda: len(self.messages), saw_since=self.saw))
        return self

    def first(self, name):
        return self if (self.have_tinder if name == tools.TINDERBOX else self.logs_held > 0) else None

    def count(self, name):
        return self.logs_held

    def use_on(self, target):
        assert target is self
        self.pending_fire = self.accept
        return self.accept

    def saw(self, mark, predicate):
        return any([predicate.lower() in message.lower() for message in self.messages[mark:]])

    def advance(self):
        PatchWorld.advance(self)
        if self.pending_fire:
            self.pending_fire = False
            if self.outcome == 'lit':
                self.logs_held -= 1
                self.xp += 40
            elif self.outcome == 'blocked':
                self.messages.append("You can't light a fire here.")
            elif self.outcome in ['animation', 'interrupt']:
                self.animation = True
                self.interrupted = self.outcome == 'interrupt'


def test_fire_missing_supplies_or_rejected_use_does_not_wait():
    with FireWorld() as world:
        world.have_tinder = False
        assert world.run(fires.light_fire('Logs')) == 'stalled'
        world.have_tinder, world.accept = True, False
        assert world.run(fires.light_fire('Logs')) == 'stalled'
        assert world.waits == []


def test_fire_acknowledgement_distinguishes_lit_blocked_and_stalled():
    for outcome, expected in [('lit', 'lit'), ('blocked', 'blocked'), ('silent', 'stalled'),
                              ('animation', 'stalled'), ('interrupt', 'stalled')]:
        with FireWorld() as world:
            world.outcome = outcome
            assert world.run(fires.light_fire('Logs')) == expected
            assert (world.xp > 0) == (outcome == 'lit')
            assert len(world.waits) > 0


def test_fire_lane_blocked_step_and_no_usable_tile():
    plot = FakeModule(x0=0, x1=2, z0=0, z1=0, bank=Tile(0, 0))
    assert fires.run_west(Tile(2, 0), plot, set(), lambda t: True, lambda a, b: False, 3) == 1
    assert fires.find_burn_lane(plot, Tile(0, 0), set(), 3, lambda t: False, lambda a, b: True) is None
    refused = fires.NoLightTiles()
    refused.add(Tile(1, 0))
    refused.clear()
    assert refused.size == 0 and fires.fire_reaction_ticks() == 1


def test_loadout_malformed_entries_append_and_unique_name_collisions():
    assert loadout.parse_loadouts(3) == []
    parsed = loadout.parse_loadouts([None, {'name': 'kit', 'carry': [None, {'item': 'Logs', 'qty': 2}]}])
    assert parsed[0].carry[0].qty == 2
    other = loadout.Loadout('kit 2')
    assert loadout.upsert_loadout(parsed, other) == parsed + [other]
    assert loadout.unique_name(parsed + [other], 'kit') == 'kit 3'
    assert 'kit' in repr(parsed[0]) and 'Logs' in repr(parsed[0].carry[0])


def test_tool_exact_equipping_and_restock_value_objects():
    req = tools.exact_tool('Hammer', equip=True)
    assert tools.tools_needing_equip([req], lambda s: 1, lambda n: 1, lambda n: False) == ['Hammer']
    assert tools.tool_kit_label([], lambda s: 1, lambda n: 0) == 'gear'
    step = tools.ToolRestockStep('Hammer', 1, True)
    assert step == tools.ToolRestockStep('Hammer', 1, True)
    assert step != tools.ToolRestockStep('Hammer', 2, True) and step != 3
    assert 'Hammer' in repr(step) and 'exact' in repr(req) and 'tiered' in repr(tools.axe_req())
    assert 'Rune' in repr(tools.AXES[0])
    assert tools.tool_restock_plan([req], lambda s: 1, lambda n: 1, lambda n: 3) == []
    assert tools.surplus_held_tool_names([req], lambda s: 1, lambda n: 1) == []
    assert pack.should_restock(0, 1) and not pack.should_restock(1, 1)
    assert pack.should_eat(1, 30, 5, 1) and not pack.should_eat(30, 30, 5, 1)


def test_price_books_saved_list_json_and_case_insensitive_lookup():
    saved = []
    with PatchWorld() as world:
        store = FakeModule(saved=lambda namespace, key: saved, save=lambda namespace, key, value: saved.extend(value))
        world.patch(prices, 'settings_store', store)
        row = prices.make_row(1, 100, sell=120)
        book = prices.make_book('Runes', rows=[row])
        prices.PriceBooks.save([book])
        assert prices.PriceBooks.names() == ['Runes']
        assert prices.PriceBooks.by_name(' RUNES ').rows[0].sell == 120
        assert prices.PriceBooks.by_name('missing') is None
        store.saved = lambda namespace, key: prices.serialize_books([book])
        assert prices.PriceBooks.all()[0].name == 'Runes'
        store.saved = lambda namespace, key: 3
        assert prices.PriceBooks.all() == []
        assert prices.unique_book_name([book, prices.make_book('Runes 2')], 'Runes') == 'Runes 3'
        assert prices.parse_books('[null, {"name":"bad rows","rows":[null]}]')[0].rows == []


class BadStop(LoopingBot):
    def loop(self):
        return 0

    def on_stop(self, reason):
        raise RuntimeError('stop failure')


def exhaust(task):
    return list(task)


def test_activity_stop_error_still_detaches_child_and_subscriptions():
    host = activity.ScriptActivity(lambda line: None)
    exhaust(host.start(define_bot('bad stop', BadStop)))
    disposed = []
    host.child._subscriptions = [lambda: disposed.append(True)]
    assert raises(RuntimeError, host.stop) == 'stop failure'
    assert host.child is None and disposed == [True]
    host.interrupt('already stopped')
    assert 'finished' in repr(activity.ActivityOutcome('finished', 'done'))


def test_run_manager_enables_run_only_when_energy_and_modal_policy_allow():
    state = {'energy': 10, 'running': False}
    with PatchWorld() as world:
        world.patch(upkeep, '_core', FakeModule(is_running=lambda: state['running'], in_combat=lambda: False,
            can_set_run=lambda: True, get_run_energy=lambda: state['energy'], get_main_modal=lambda: -1,
            set_run=lambda value: state.update({'running': value})))
        manager = upkeep._RunManager()
        assert manager.tick(0) is False
        state['energy'] = 30
        assert manager.tick(1500) is True and state['running']


def test_stall_recovery_walks_to_distant_anchor_or_requests_restart():
    import rs2004.traversal as routes
    walks = [True, False]
    def walk(tile, **kwargs):
        assert tile == Tile(100, 100) and kwargs['attempts'] == 3
        yield execution.Ticks(1)
        return walks.pop(0)
    with PatchWorld() as world:
        world.patch(upkeep, '_core', FakeModule(get_x=lambda: 0, get_z=lambda: 0, get_level=lambda: 0))
        world.patch(routes, 'traversal', FakeModule(walk_resilient=walk))
        bot = FakeModule(recovery_anchor=lambda: (100, 100))
        assert world.run(upkeep.recover(bot, 5, world.logs.append)) == 'recovered'
        assert world.run(upkeep.recover(bot, 5, world.logs.append)) == 'restart'
