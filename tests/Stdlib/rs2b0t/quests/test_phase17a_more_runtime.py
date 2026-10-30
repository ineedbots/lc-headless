"""Drive the custom legs that depend on generators, pockets and delayed results."""
import _core
import rs2004.quests.defs.gertrudescat as cat
import rs2004.quests.defs.junglepotion as jungle
import rs2004.quests.defs.clocktower as clock
import rs2004.quests.defs.hazeelcult as cult
from rs2004 import execution
from rs2004.quests.engine.types import QuestSnapshot
from rs2004.quests.defs import def_by_id
from rs2004.game import reader
from rs2004.tabs import quests


def result(value):
    return value
    yield


def journal_case(id, line, expected):
    def run():
        text = line
        spy_on(quests, 'status', returns='in_progress')
        spy_on(quests, 'journal', impl=lambda name: result([text]))
        spy_on(reader, 'modals', returns=Fake(main=123))
        closed = spy_on(_core, 'close_interfaces')
        module = def_by_id(id)
        progress = run_wait(module.read_progress())
        expect(progress.stage).to_be(expected)
        expect(len(closed.calls)).to_be(1)
    return run


test('cat progress reads the rescued journal and closes it', journal_case('fluffs',
     'I gave Fluffs her kitten back', 5))
test('jungle progress reads the latest requested herb and closes it', journal_case('junglepotion',
     'I need to pick some fresh Volencia Moss', 7))
test('clock progress reads the all-placed page and closes it', journal_case('cog',
     'I have placed all four cogs successfully', 5))
test('cult progress reads the armour return and closes it', journal_case('hazeelcult',
     "I returned the armour, but Ceril didn't believe Jones", 7))


def cat_offering():
    state = {'held': True, 'driven': False}
    calls = []
    def held(id):
        expect(id).to_be(1554)
        return 1 if state['held'] else 0
    def use(target):
        calls.append(target.id)
        return True
    def drive(expect, prefer, log, timeout):
        expect_before = expect()
        state['held'] = False
        state['driven'] = expect()
        assert not expect_before
        yield from execution.delay_ticks(1)
        return True
    spy_on(cat, 'held_id', impl=held)
    spy_on(cat, 'climb_to_cat', impl=lambda log: result(True))
    spy_on(cat.npcs, 'query', impl=querying(lambda: [Fake(id=759)]))
    spy_on(cat.inventory, 'items', returns=[Fake(id=1554, use_on=use)])
    spy_on(cat, 'drive_until', impl=drive)
    settled = spy_on(cat, 'settle_cutscene', impl=instant_ticks)
    run = cat.offer_to_cat(1554, 'kitten')
    expect(run_wait(run(lambda message: None))).to_be(True)
    expect(calls).to_equal([759])
    expect(state['driven']).to_be(True)
    expect(len(settled.calls)).to_be(1)


test('a returned cat-offering generator retains the exact item id and settles the cutscene', cat_offering)


def banked_kitten():
    snap = QuestSnapshot(journal='in_progress', progress=cat.parse_gertrudes_cat_journal(
        'I gave the cat milk and sardines'), bank_known=True, bank_ids={1554: 1})
    step = cat.decide(snap)
    expect(step.name).to_be('retrieve the banked kitten')
    calls = []
    def leave(log):
        calls.append('leave')
        return True
        yield
    def withdraw(step, hops, log):
        calls.append(step.items[0]['id'])
        return True
        yield
    spy_on(cat.game, 'tile', returns=Tile(3307, 3507))
    spy_on(cat, 'leave_yard', impl=leave)
    spy_on(cat, 'execute_step', impl=withdraw)
    expect(run_wait(step.run(lambda message: None))).to_be(True)
    expect(calls).to_equal(['leave', 1554])


test('a banked kitten is retrieved after leaving the yard instead of searching empty crates', banked_kitten)


def wrong_crate():
    state = {'refused': False}
    crate = Fake(interact=lambda op: True)
    query = Fake(where=lambda predicate: state['query'], within_of=lambda spot, radius: state['query'], nearest=lambda: crate)
    state['query'] = query
    spy_on(cat.npcs, 'query', returns=query)
    spy_on(cat.game_messages, 'mark', returns=1)
    def saw(mark, pattern):
        expect(pattern).to_be('you find nothing')
        return pattern in 'you find nothing.'
    spy_on(cat.game_messages, 'saw_since', impl=saw)
    def drive(expect, prefer, log, timeout):
        state['refused'] = expect()
        return None
        yield
    spy_on(cat, 'drive_until', impl=drive)
    run_wait(cat.search_crate(Tile(3307, 3507), lambda: False, lambda message: None))
    expect(state['refused']).to_be(True)


test('a wrong kitten crate is rejected by its game message instead of a regex literal', wrong_crate)


def identify_herb():
    state = {'clean': False}
    def interact(op):
        expect(op).to_be('Identify')
        state['clean'] = True
        return True
    spy_on(jungle.inventory, 'items', returns=[Fake(id=1527, interact=interact)])
    spy_on(jungle, 'held_id', impl=lambda id: 1 if id == 1528 and state['clean'] else 0)
    spy_on(execution, 'delay_until', impl=instant_until)
    run = jungle.identify_herb(jungle.JUNGLE_HERBS[1])
    expect(run_wait(run(lambda message: None))).to_be(True)
    expect(state['clean']).to_be(True)


test('a returned herb-identification generator waits for the correct cleaned id', identify_herb)


def pick_herb():
    spy_on(jungle, 'held_id', returns=0)
    spy_on(jungle.game, 'tile', returns=Tile(2830, 9521))
    escaped = spy_on(jungle, 'leave_pothole', impl=lambda log: result(True))
    def prompt(spec, log):
        expect(spec.name).to_be('Palm tree')
        expect(spec.expect()).to_be(False)
        return True
        yield
    spy_on(jungle, 'prompt_loc', impl=prompt)
    run = jungle.pick_herb(jungle.JUNGLE_HERBS[1])
    expect(run_wait(run(lambda message: None))).to_be(True)
    expect(len(escaped.calls)).to_be(1)


test('a surface herb pick leaves the cave before searching its loc', pick_herb)


def cog_fetch():
    spy_on(clock, 'leave_pocket', impl=lambda log, colour: result(True))
    spy_on(clock, 'walk_with_hops', impl=lambda tile, radius, hops, log: result(True))
    taken = spy_on(clock, 'take_black_cog', impl=lambda log: result(True))
    expect(run_wait(clock.fetch_leg('black')(lambda message: None))).to_be(True)
    expect(len(taken.calls)).to_be(1)


test('fetching a cog drives the inner generator and returns its actual outcome', cog_fetch)


def cog_place():
    spy_on(clock, 'leave_pocket', impl=lambda log: result(True))
    spy_on(clock, 'walk_with_hops', impl=lambda tile, radius, hops, log: result(True))
    spy_on(clock, 'held_id', impl=lambda id: 0 if id == 22 else 1)
    def use(item, loc, prefer, expect, log):
        assert item == 22 and loc.id == 32 and expect()
        return True
        yield
    spy_on(clock, 'use_on_loc', impl=use)
    expect(run_wait(clock.place_leg('blue')(lambda message: None))).to_be(True)


test('placing a cog keeps its colour available inside the result predicate', cog_place)


def rat_gate_message():
    state = {'tile': Tile(2579, 9656), 'clicked': False}
    spy_on(clock.traversal, 'walk_resilient', impl=lambda *args, **kwargs: result(True))
    spy_on(clock.game, 'tile', impl=lambda: state['tile'])
    def click(op):
        assert op == 'Go-through'
        state['clicked'] = True
        return True
    spy_on(clock, 'loc_by_id', returns=Fake(interact=click))
    def drive(expect, prefer, log, timeout):
        assert state['clicked'] and not expect()
        state['tile'] = Tile(2578, 9656)
        assert expect()
        return True
        yield
    driven = spy_on(clock, 'drive_until', impl=drive)
    spy_on(clock, 'settle_scene', impl=instant_ticks)
    expect(run_wait(clock.cross_rat_gate(lambda message: None))).to_be(True)
    expect(len(driven.calls)).to_be(1)
    expect(clock.clocktower.resume_at(state['tile'])).to_be(True)
    expect(clock.clocktower.resume_at(Tile(2655, 3283))).to_be(False)


test('the rat gate drives its message before waiting for the crossing', rat_gate_message)


def bankless_armour():
    snap = QuestSnapshot(journal='in_progress', progress=cult.parse_hazeel_journal(
        'I managed to enter the hideout, kill the cult leader'), tile=Tile(2609, 9669), bank_known=False)
    step = cult.decide(snap)
    expect(step.kind).to_be('custom')
    expect(step.name).to_contain('armour')


test('a bankless hideout resume seeks the armour drop before asking for a bank', bankless_armour)


def valves():
    stub(cult, valves_turned=False)
    spy_on(cult.game, 'tile', returns=Tile(2587, 3237))
    turned = spy_on(cult, 'turn_valves', impl=lambda log: result(True))
    spy_on(cult, 'walk_with_hops', impl=lambda dest, radius, hops, log: result(False))
    expect(run_wait(cult.to_hideout(lambda message: None))).to_be(False)
    expect(cult.valves_turned).to_be(True)
    expect(run_wait(cult.to_hideout(lambda message: None))).to_be(False)
    expect(len(turned.calls)).to_be(1)


test('the valve tour persists across custom-step retries', valves)


def raft_landing():
    state = {'tile': Tile(2567, 9680)}
    def board(op):
        assert op == 'Board'
        state['tile'] = Tile(2606, 9692)
        return True
    spy_on(cult.game, 'tile', impl=lambda: state['tile'])
    spy_on(cult, 'loc_by_id', returns=Fake(interact=board))
    spy_on(cult, 'clear_boxes', impl=instant_ticks)
    spy_on(cult, 'settle_scene', impl=instant_ticks)
    spy_on(execution, 'delay_until', impl=instant_until)
    expect(run_wait(cult.board_raft(4, lambda message: None))).to_be(True)


test('the raft confirms movement from a copied departure tile', raft_landing)
