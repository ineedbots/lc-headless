"""Test item confirmation, mouse fallback and recovery after a witch catch."""
import rs2004.quests.defs.witchshouse.house as house
import rs2004.quests.defs.witchshouse.garden as garden
from rs2004.quests.defs.witchshouse.areas import WH_OBJ as OBJ, WH_TILE as SPOT
from rs2004 import execution


def result(value):
    return value
    yield


def key_confirmation(received):
    def run():
        state = {'key': 0}
        given = received
        spy_on(house.inventory, 'count_by_id', impl=lambda id: state['key'])
        def prompt(step, log):
            assert step.id == house.WH_LOC.POT and step.op == 'Look-under'
            assert not step.expect()
            state['key'] = 1 if given else 0
            return True
            yield
        spy_on(house, 'prompt_loc', impl=prompt)
        closed = spy_on(house.modals, 'close', impl=instant_ticks)
        expect(run_wait(house.take_door_key(lambda message: None))).to_be(received)
        expect(len(closed.calls)).to_be(1)
    return run


test('Witch door key is confirmed by inventory after the modal', key_confirmation(True))
test('Witch door key does not trust a prompt without the item', key_confirmation(False))


def magnet_search(found):
    def run():
        state = {'held': 0}
        available = found
        spy_on(house.inventory, 'count_by_id', impl=lambda id: state['held'])
        spy_on(house.traversal, 'walk_resilient', impl=lambda *args, **kwargs: result(True))
        spy_on(house, 'settle_scene', impl=instant_ticks)
        spy_on(house, 'open_container', impl=lambda *args: result(True))
        spy_on(house.game_messages, 'mark', returns=1)
        spy_on(house.game_messages, 'saw_since', returns=True)
        def prompt(step, log):
            assert step.id == house.WH_LOC.CUPBOARD_OPEN
            state['held'] = 1 if available else 0
            return available
            yield
        spy_on(house, 'prompt_loc', impl=prompt)
        closed = spy_on(house.modals, 'close', impl=instant_ticks)
        messages = []
        expect(run_wait(house.fetch_magnet(lambda text: messages.append(text)))).to_be(found)
        expect(len(closed.calls)).to_be(1)
        expect(len(messages)).to_be(0 if found else 1)
    return run


test('Witch cupboard search confirms the magnet and closes its modal', magnet_search(True))
test('Witch empty cupboard reports an existing magnet in bank or pack', magnet_search(False))


def mouse_lure(use_succeeds, mouse_arrives):
    def run():
        state = {'mouse': False, 'drops': 0}
        use_ok = use_succeeds
        arrives = mouse_arrives
        def use(target):
            state['mouse'] = arrives and use_ok
            return use_ok
        def drop(op):
            assert op == 'Drop'
            state['drops'] += 1
            state['mouse'] = arrives
            return True
        cheese = Fake(id=OBJ.CHEESE, use_on=use, interact=drop)
        hole = Fake(id=house.WH_LOC.MOUSE_HOLE, distance=lambda: 1)
        spy_on(house.inventory, 'items', returns=[cheese])
        spy_on(house.locs, 'query', impl=querying(lambda: [hole]))
        spy_on(house, 'mouse', impl=lambda: Fake(id=901) if state['mouse'] else None)
        spy_on(house, 'drive_boxes', impl=lambda predicate, *args: result(predicate()))
        cleared = spy_on(house, 'clear_boxes', impl=instant_ticks)
        expect(run_wait(house.lure_mouse(lambda message: None))).to_be(mouse_arrives)
        expect(state['drops']).to_be(0 if use_succeeds and mouse_arrives else 1)
        expect(len(cleared.calls)).to_be(1)
    return run


test('Witch mouse comes out when cheese is used on its hole', mouse_lure(True, True))
test('Witch mouse lure falls back to dropping cheese when use is refused', mouse_lure(False, True))
test('Witch mouse lure fails when neither use nor drop brings a mouse', mouse_lure(True, False))


def back_door(already_unlocked):
    def run():
        state = {'magnet': 1}
        already = already_unlocked
        spy_on(house.game, 'tile', returns=SPOT.PORCH)
        spy_on(house, 'settle_scene', impl=instant_ticks)
        spy_on(house, 'mouse', returns=Fake(id=901))
        def fit(target):
            assert target.id == 901
            state['magnet'] = 1 if already else 0
            return True
        spy_on(house.inventory, 'items', returns=[Fake(id=OBJ.MAGNET, use_on=fit)])
        spy_on(house.inventory, 'count_by_id', impl=lambda id: state['magnet'])
        spy_on(house.game_messages, 'mark', returns=1)
        spy_on(house.game_messages, 'saw_since', returns=already_unlocked)
        spy_on(house, 'drive_boxes', impl=lambda predicate, *args: result(predicate()))
        spy_on(house, 'clear_boxes', impl=instant_ticks)
        expect(run_wait(house.unlock_back_door(lambda message: None))).to_be(True)
    return run


test('Witch back door unlock waits for the magnet to be consumed', back_door(False))
test('Witch back door accepts the already-unlocked reply on a restart', back_door(True))


def diary_recovery():
    house.reset_diary_state()
    spy_on(house.inventory, 'count_by_id', returns=0)
    spy_on(house.traversal, 'walk_resilient', impl=lambda *args, **kwargs: result(True))
    spy_on(house, 'settle_scene', impl=instant_ticks)
    spy_on(house.ground_items, 'query', impl=querying(lambda: []))
    log = lambda message: None
    for attempt in range(3):
        expect(house.diary_wanted()).to_be(True)
        expect(run_wait(house.fetch_diary(log))).to_be(False)
    expect(house.diary_wanted()).to_be(False)
    house.reset_diary_state()
    state = {'held': 0, 'open': False}
    def interact(op):
        if op == 'Take':
            state['held'] = 1
        else:
            assert op == 'Read'
            state['open'] = True
        return True
    diary = Fake(id=OBJ.DIARY, distance=lambda: 1, interact=interact)
    spy_on(house.ground_items, 'query', impl=querying(lambda: [diary]))
    spy_on(house.inventory, 'items', returns=[diary])
    spy_on(house.inventory, 'count_by_id', impl=lambda id: state['held'])
    spy_on(execution, 'delay_until', impl=instant_until)
    spy_on(house.modals, 'is_open', impl=lambda: state['open'])
    spy_on(house.modals, 'close', impl=instant_ticks)
    expect(run_wait(house.fetch_diary(log))).to_be(True)
    expect(run_wait(house.read_diary(log))).to_be(True)
    expect(house.diary_wanted()).to_be(False)
    expect(house.diary_state.read).to_be(True)
    house.reset_diary_state()


test('Witch diary retries are bounded and reset before a successful pickup and read', diary_recovery)


def ball_after_catch():
    state = {'tile': SPOT.THROWN_OUT, 'ball': 0}
    spy_on(garden.game, 'tile', impl=lambda: state['tile'])
    spy_on(garden, 'held', impl=lambda id: state['ball'] if id == OBJ.BALL else 0)
    spy_on(garden, 'walk_garden', impl=lambda *args: result(True))
    def cross(step):
        assert step.use_item is None, 'a completed fight must not require another shed key'
        state['tile'] = SPOT.BALL
        assert step.is_far()
        return True
        yield
    spy_on(garden, 'cross_teleport_door', impl=cross)
    spy_on(garden.traversal, 'walk_resilient', impl=lambda *args, **kwargs: result(True))
    spy_on(garden, 'settle_scene', impl=instant_ticks)
    def take(op):
        assert op == 'Take'
        state['ball'] = 1
        return True
    spy_on(garden.ground_items, 'query', impl=querying(lambda: [Fake(id=OBJ.BALL, distance=lambda: 1, interact=take)]))
    spy_on(execution, 'delay_until', impl=instant_until)
    expect(run_wait(garden.take_ball(lambda message: None))).to_be(True)
    expect(state['ball']).to_be(1)


test('Witch retrieves the ball after a catch without requiring the deleted shed key', ball_after_catch)


def shed_key_and_fountain():
    state = {'key': 0, 'tile': SPOT.PORCH}
    spy_on(garden.game, 'tile', impl=lambda: state['tile'])
    spy_on(garden, 'held', impl=lambda id: state['key'] if id == OBJ.SHED_KEY else 0)
    log = lambda message: None
    expect(run_wait(garden.enter_shed(log))).to_be(False)
    spy_on(garden, 'walk_garden', impl=lambda *args: result(True))
    spy_on(garden, 'settle_scene', impl=instant_ticks)
    spy_on(garden.modals, 'close', impl=instant_ticks)
    def fountain(step, log):
        assert step.id == garden.WH_LOC.FOUNTAIN
        state['key'] = 1
        return step.expect()
        yield
    spy_on(garden, 'prompt_loc', impl=fountain)
    expect(run_wait(garden.fountain_key(log))).to_be(True)
    def cross(step):
        assert step.use_item == OBJ.SHED_KEY
        state['tile'] = SPOT.BALL
        return step.is_far()
        yield
    spy_on(garden, 'cross_teleport_door', impl=cross)
    expect(run_wait(garden.enter_shed(log))).to_be(True)


test('Witch replaces a missing shed key at the fountain before using it on the shed', shed_key_and_fountain)


def shapeshifter_fight():
    state = {'form': -1, 'won': False, 'casts': []}
    spy_on(garden.game, 'tile', returns=SPOT.BALL)
    spy_on(garden, 'ready_strikes', impl=lambda log: result(True))
    spy_on(garden, 'enter_shed', impl=lambda log: result(True))
    spy_on(garden, 'settle_scene', impl=instant_ticks)
    spy_on(garden, 'clear_boxes', impl=instant_ticks)
    def summon(op):
        assert op == 'Take'
        state['form'] = 0
        return True
    spy_on(garden, 'ball_drop', returns=Fake(interact=summon))
    def target():
        index = state['form']
        return Fake(id=garden.EXPERIMENT_IDS[index], size=2) if index >= 0 and index < 4 else None
    spy_on(garden, 'experiment', impl=target)
    spy_on(execution, 'delay_until', impl=instant_until)
    spy_on(garden.event_signal, 'pending', returns=False)
    spy_on(garden.sustain, 'run', impl=instant_ticks)
    spy_on(garden._core, 'step_time', returns=0)
    spy_on(garden.game_messages, 'mark', returns=1)
    spy_on(garden.game_messages, 'saw_since', impl=lambda mark, message: state['won'])
    spy_on(garden, 'at_cover', returns=True)
    covers = spy_on(garden, 'take_strike_cover', impl=lambda *args: result(True))
    def cast(cover, npc, log):
        state['casts'].append(npc.id)
        state['form'] += 1
        state['won'] = state['form'] == 4
        return True
        yield
    spy_on(garden, 'cast_strike', impl=cast)
    expect(run_wait(garden.kill_experiment(lambda message: None))).to_be(True)
    expect(state['casts']).to_equal(list(garden.EXPERIMENT_IDS))
    expect(len(covers.calls)).to_be(2)
    expect(covers.calls[0][0]).to_be(garden.BEAR_COVER)


test('Witch summons a missing shapeshifter and repositions through all four forms until the kill message', shapeshifter_fight)


def fight_stops(interrupted):
    def run():
        spy_on(garden, 'ready_strikes', impl=lambda log: result(True))
        spy_on(garden._core, 'step_time', returns=0)
        spy_on(garden.game_messages, 'mark', returns=1)
        spy_on(garden.game_messages, 'saw_since', returns=False)
        spy_on(garden.event_signal, 'pending', returns=interrupted)
        spy_on(garden.sustain, 'run', impl=instant_ticks)
        spy_on(garden, 'experiment', returns=None)
        ticks = spy_on(execution, 'delay_ticks', impl=instant_ticks)
        expect(run_wait(garden.fight_experiment(lambda message: None))).to_be(False)
        expect(len(ticks.calls)).to_be(0 if interrupted else garden.SPAWN_TICKS)
    return run


test('Witch fight yields immediately to an interrupt without claiming a kill', fight_stops(True))
test('Witch fight bounds a missing-form wait without treating disappearance as victory', fight_stops(False))
