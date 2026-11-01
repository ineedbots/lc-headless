"""Test Priest in Peril's key, water and essence handoffs across reruns, and its legs against a spied temple."""
import _core
import rs2004.quests.defs.priestperil as priest
from rs2004 import execution
from rs2004.bank import bank
from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import chat_dialog
from rs2004.entities import ground_items, locs, npcs
from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.items import inventory


def result(value):
    return value
    yield


def key_swap():
    state = {'iron': False, 'tile': priest.MONUMENTS[0], 'uses': 0}
    spy_on(priest, 'try_open', impl=lambda *args: result(True))
    spy_on(priest, 'held_id', impl=lambda id: state['iron'] if id == priest.IRON_KEY_ID else False)
    def walk(tile, radius, log):
        state['tile'] = tile
        return True
        yield
    spy_on(priest, 'walk_to', impl=walk)
    def use(target):
        state['uses'] += 1
        state['iron'] = state['uses'] == 2
        return True
    spy_on(priest.inventory, 'items', returns=[Fake(id=priest.GOLDEN_KEY_ID, use_on=use)])
    def monuments():
        position = state['tile']
        return [Fake(name='Monument', tile=lambda: position)]
    spy_on(priest.locs, 'query', impl=querying(monuments))
    spy_on(execution, 'delay_ticks', impl=instant_ticks)
    expect(run_wait(priest.monument_leg(lambda message: None))).to_be(False)
    expect(state['iron']).to_be(True)
    expect(state['uses']).to_be(2)


test('Priest swaps the golden key at successive monuments and stops once the iron key arrives', key_swap)


def water_chain():
    state = {'water': priest.MURKY_ID, 'reported': False}
    spy_on(priest.game, 'tile', returns=priest.CELL_DOOR_STAND)
    spy_on(priest, 'enter_temple', impl=lambda *args: result(True))
    spy_on(priest, 'try_open', impl=lambda *args: result(True))
    spy_on(priest, 'walk_to', impl=lambda *args: result(True))
    spy_on(priest, 'held_id', impl=lambda id: state['water'] == id)
    drezel = Fake(name='Drezel', distance=lambda: 1)
    coffin = Fake(name='Coffin', tile=lambda: priest.COFFIN, distance=lambda: 1)
    spy_on(priest.npcs, 'query', impl=querying(lambda: [drezel]))
    spy_on(priest.locs, 'query', impl=querying(lambda: [coffin]))
    def use(target):
        if state['water'] == priest.MURKY_ID:
            assert target is drezel
            state['water'] = priest.BLESSED_ID
        else:
            assert target is coffin
            state['water'] = 0
        return True
    def items():
        return [Fake(id=state['water'], use_on=use)]
    spy_on(priest.inventory, 'items', impl=items)
    spy_on(execution, 'delay_until', impl=instant_until)
    def report(stop, log):
        assert stop is priest.DREZEL_CELL and state['water'] == 0
        state['reported'] = True
        return True
        yield
    spy_on(priest, 'reach_and_talk', impl=report)
    log = lambda message: None
    expect(run_wait(priest.water_leg(log))).to_be(False)
    expect(state['water']).to_be(priest.BLESSED_ID)
    expect(state['reported']).to_be(False)
    expect(run_wait(priest.water_leg(log))).to_be(False)
    expect(state['water']).to_be(0)
    expect(state['reported']).to_be(True)


test('Priest blesses murky water then pours it on the coffin before reporting to Drezel', water_chain)


def essence_delivery(finishes):
    def run():
        state = {'essence': 27, 'done': False, 'post_talks': 0}
        final_load = finishes
        spy_on(priest, 'journal_complete', impl=lambda: state['done'])
        spy_on(priest.inventory, 'count', impl=lambda name: state['essence'])
        spy_on(priest.inventory, 'contains', impl=lambda name: name == 'Wolfbane' and state['done'])
        spy_on(priest, 'try_open', impl=lambda *args: result(True))
        spy_on(priest, 'walk_to', impl=lambda *args: result(True))
        def hand_in(name, prefer, log):
            assert name == 'Drezel'
            state['essence'] = 0
            state['done'] = final_load
            return True
            yield
        spy_on(priest, 'talk_through', impl=hand_in)
        def post_talk(stop, log):
            assert stop is priest.DREZEL_MAUS
            state['post_talks'] += 1
            return True
            yield
        spy_on(priest, 'reach_and_talk', impl=post_talk)
        spy_on(execution, 'delay_until', impl=instant_until)
        spy_on(execution, 'delay_ticks', impl=instant_ticks)
        expect(run_wait(priest.essence_leg(lambda message: None))).to_be(finishes)
        expect(state['essence']).to_be(0)
        expect(state['post_talks']).to_be(1 if finishes else 0)
    return run


test('Priest returns to collect another load after a partial essence hand-in', essence_delivery(False))
test('Priest follows the final essence hand-in with the barrier-access conversation', essence_delivery(True))


def completed_barrier():
    spy_on(priest, 'journal_complete', returns=True)
    state = {'talks': 0}
    spy_on(priest.inventory, 'contains', impl=lambda name: state['talks'] == 2)
    def talk(stop, log):
        state['talks'] += 1
        return True
        yield
    spy_on(priest, 'reach_and_talk', impl=talk)
    expect(run_wait(priest.essence_leg(lambda message: None))).to_be(True)
    expect(state['talks']).to_be(2)


test('Priest performs both post-quest talks when Wolfbane was banked', completed_barrier)


def essence_restock(bank_has_essence):
    def run():
        state = {'essence': 0}
        available = bank_has_essence
        spy_on(priest, 'journal_complete', returns=False)
        spy_on(priest.inventory, 'count', impl=lambda name: state['essence'])
        spy_on(priest, 'free_slots', returns=19)
        spy_on(priest, 'walk_to', impl=lambda *args: result(True))
        def withdraw(step, hops, log):
            expect(step.items).to_equal([{'name': 'Rune essence', 'qty': 18}])
            assert step.bank is priest.VARROCK_EAST_BANK
            state['essence'] = 18 if available else 0
            return available
            yield
        spy_on(priest, 'execute_step', impl=withdraw)
        mined = spy_on(priest, 'mine_essence', impl=lambda log: result(False))
        expect(run_wait(priest.essence_leg(lambda message: None))).to_be(False)
        expect(len(mined.calls)).to_be(0 if bank_has_essence else 1)
    return run


test('Priest reserves a pack slot when withdrawing the next banked essence load', essence_restock(True))
test('Priest falls back to mining when the bank cannot supply essence', essence_restock(False))


def mining_trip():
    state = {'tile': priest.AUBURY_TILE, 'pick': False, 'full': False, 'operations': []}
    spy_on(priest.game, 'tile', impl=lambda: state['tile'])
    spy_on(priest, 'in_ess_mine', impl=lambda x, z: z == 10000)
    spy_on(priest.inventory, 'items', impl=lambda: [Fake(name='Bronze pickaxe')] if state['pick'] else [])
    def withdraw(step, hops, log):
        assert step.items[0]['name'] == 'Bronze pickaxe'
        state['pick'] = True
        return True
        yield
    spy_on(priest, 'execute_step', impl=withdraw)
    spy_on(priest, 'walk_to', impl=lambda *args: result(True))
    def teleport(op):
        assert op == 'Teleport'
        state['operations'].append(op)
        state['tile'] = Tile(2900, 10000)
        return True
    aubury = Fake(name='Aubury', actions=lambda: ['Teleport'], distance=lambda: 1, interact=teleport)
    spy_on(priest.npcs, 'query', impl=querying(lambda: [aubury]))
    def mine(op):
        assert op == 'Mine'
        state['operations'].append(op)
        state['full'] = True
        return True
    def leave(op):
        assert op == 'Use'
        state['operations'].append(op)
        state['tile'] = priest.AUBURY_TILE
        return True
    rock = Fake(name='Rune Essence', actions=lambda: ['Mine'], interact=mine)
    portal = Fake(name='Portal', actions=lambda: ['Use'], interact=leave)
    spy_on(priest.locs, 'query', impl=querying(lambda: [rock, portal]))
    spy_on(priest, 'free_slots', impl=lambda: 0 if state['full'] else 1)
    spy_on(execution, 'delay_until', impl=instant_until)
    expect(run_wait(priest.mine_essence(lambda message: None))).to_be(False)
    expect(state['operations']).to_equal(['Teleport', 'Mine', 'Use'])
    expect(state['tile']).to_be(priest.AUBURY_TILE)


test('Priest equips its mining trip with a banked pickaxe, teleports, fills the pack and leaves through the portal', mining_trip)


def missing_mining_tools():
    spy_on(priest.game, 'tile', returns=priest.AUBURY_TILE)
    spy_on(priest.inventory, 'items', returns=[])
    attempts = spy_on(priest, 'execute_step', impl=lambda *args: result(False))
    expect(run_wait(priest.mine_essence(lambda message: None))).to_be(False)
    expect(len(attempts.calls)).to_be(3)


test('Priest parks after all three banked pickaxe choices fail', missing_mining_tools)


def gathers_bucket():
    gather = priest.priestperil.gather.get('bucket')
    step = gather(None, 1)
    expect(step.kind).to_be('buy')
    expect(step.item).to_be('Bucket')


test('the bucket gather takes the snapshot and need the engine passes', gathers_bucket)


OUTSIDE = Tile(3300, 3400, 0)


class Temple:
    """The player about Paterdomus and the mausoleum, with the pack, the scene and the primitives each leg calls."""

    def __init__(self, at):
        self.at = at
        self.pack = []
        self.locs = []
        self.ground = []
        self.npcs = []
        self.walk_ok = True
        self.lines = []
        self.fighting = False
        self.facing = None
        self.clock = 0
        self.talks = []
        spy_on(game, 'tile', impl=lambda: self.at)
        spy_on(game, 'in_combat', impl=lambda: self.fighting)
        spy_on(game, 'facing', impl=lambda: self.facing)
        spy_on(locs, 'query', impl=querying(lambda: self.locs))
        spy_on(ground_items, 'query', impl=querying(lambda: self.ground))
        spy_on(npcs, 'query', impl=querying(lambda: self.npcs))
        spy_on(npcs, 'all', impl=lambda: self.npcs)
        spy_on(inventory, 'items', impl=lambda: self.pack)
        spy_on(inventory, 'contains', impl=lambda name: any([i.name == name for i in self.pack]))
        spy_on(inventory, 'count', impl=lambda name: sum([i.count for i in self.pack if i.name == name]))
        spy_on(inventory, 'first', impl=lambda name: ([i for i in self.pack if i.name == name] or [None])[0])
        spy_on(sustain, 'run', impl=lambda: result(True))
        spy_on(_core, 'step_time', impl=self.now)
        spy_on(priest, 'walk_with_hops', impl=self.walk)
        spy_on(priest, 'talk_through', impl=self.talk)
        spy_on(priest, 'settle_scene', impl=instant_ticks)
        patch(execution, 'delay_until', instant_until)
        patch(execution, 'delay_ticks', instant_ticks)
        self.chat = FakeChat().install(chat_dialog)

    def now(self):
        self.clock += 1000
        return self.clock

    def log(self, text):
        self.lines.append(text)

    def logged(self, part):
        return any([part in line for line in self.lines])

    def walk(self, dest, radius, hops, log):
        if self.walk_ok:
            self.at = dest
        return self.walk_ok
        yield

    def talk(self, npc, prefer, log):
        self.talks.append(npc)
        return True
        yield

    def hold(self, id, name=None, count=1, use_on=None):
        held = Fake(id=id, name=name, count=count, use_on=use_on if use_on is not None else (lambda other: True))
        self.pack.append(held)
        return held

    def drop(self, id):
        self.pack = [held for held in self.pack if held.id != id]

    def swaps(self, gone, got):
        def swap(*args):
            self.drop(gone)
            if got is not None:
                self.hold(got)
            return True
        return swap

    def loc(self, name, actions, tile=None, interact=None):
        made = Fake(name=name, actions=lambda: actions, distance=lambda: 1, tile=lambda: tile if tile is not None else self.at,
                    interact=interact if interact is not None else (lambda op: True))
        self.locs.append(made)
        return made

    def npc(self, name, actions=None, id=None, index=1, interact=None):
        made = Fake(name=name, id=id, index=index, actions=lambda: actions if actions is not None else ['Talk-to'], distance=lambda: 1,
                    interact=interact if interact is not None else (lambda op: True))
        self.npcs.append(made)
        return made

    def opens_chat(self):
        def open_chat(op):
            self.chat.pages.append('continue')
            return True
        return open_chat

    def removes_locs(self):
        def remove(op):
            self.locs = []
            return True
        return remove

    def moves(self, tile):
        def move(op):
            self.at = tile
            return True
        return move


class Calls:
    """Stand-in legs that record their names and give what answer holds."""

    def __init__(self, answer=True):
        self.names = []
        self.answer = answer

    def leg(self, name):
        def run(*args):
            self.names.append(name)
            return self.answer
            yield
        return run

    def queued(self, answers):
        def run(*args):
            return answers.pop(0) if len(answers) > 0 else True
            yield
        return run


def walks_talks_and_opens():
    temple = Temple(OUTSIDE)
    temple.walk_ok = False
    expect(run_wait(priest.reach_and_talk(priest.ROALD, temple.log))).to_be(False)
    expect(run_wait(priest.try_open('Gate', priest.GATE1, temple.log))).to_be(False)
    temple.walk_ok = True
    expect(run_wait(priest.reach_and_talk(priest.ROALD, temple.log))).to_be(True)
    expect(temple.talks).to_equal(['King Roald'])
    expect(run_wait(priest.try_open('Gate', priest.GATE1, temple.log))).to_be(True)
    temple.at = OUTSIDE
    gate = temple.loc('Gate', ['Open'], tile=priest.GATE1, interact=lambda op: False)
    expect(run_wait(priest.try_open('Gate', priest.GATE1, temple.log))).to_be(False)
    gate._fields['interact'] = temple.removes_locs()
    expect(run_wait(priest.try_open('Gate', priest.GATE1, temple.log))).to_be(True)
    expect(temple.at).to_equal(priest.GATE1)


test('Priest walks to a stop before talking, and opens a shut leaf near a tile only when one is there', walks_talks_and_opens)


def enters_the_temple():
    temple = Temple(priest.CELL_DOOR)
    expect(priest.inside_temple(priest.CELL_DOOR)).to_be(True)
    expect(priest.inside_temple(priest.TEMPLE_LOBBY)).to_be(True)
    expect(priest.inside_temple(OUTSIDE)).to_be(False)
    expect(run_wait(priest.enter_temple(temple.log))).to_be(True)
    temple.at = OUTSIDE
    temple.walk_ok = False
    expect(run_wait(priest.enter_temple(temple.log))).to_be(False)
    temple.walk_ok = True
    expect(run_wait(priest.enter_temple(temple.log))).to_be(False)
    door = temple.loc('Large door', ['Open'], interact=lambda op: False)
    expect(run_wait(priest.enter_temple(temple.log))).to_be(False)
    door._fields['interact'] = temple.moves(priest.TEMPLE_LOBBY)
    expect(run_wait(priest.enter_temple(temple.log))).to_be(True)


test('Priest enters the temple through the large door unless it is already inside', enters_the_temple)


def kills_a_target():
    temple = Temple(priest.DOG_TILE)
    dog = temple.npc('Temple guardian', ['Attack'], index=5, interact=lambda op: False)
    expect(run_wait(priest.kill_target(dog, 'temple guardian'))).to_be(False)
    dog._fields['interact'] = lambda op: True
    expect(run_wait(priest.kill_target(dog, 'temple guardian'))).to_be(False)
    temple.fighting = True
    attacks = Calls()
    dog._fields['interact'] = attacks.queued([True, True, False])
    expect(run_wait(priest.kill_target(dog, 'temple guardian'))).to_be(False)
    temple.facing = ('npc', 5)
    dog._fields['interact'] = lambda op: True
    expect(run_wait(priest.kill_target(dog, 'temple guardian'))).to_be(False)

    def dies(op):
        temple.npcs = []
        return True
    dog._fields['interact'] = dies
    temple.npcs = [dog]
    expect(run_wait(priest.kill_target(dog, 'temple guardian'))).to_be(True)


test('Priest holds an attack until the target leaves the scene, re-attacking after it eats', kills_a_target)


def knocks_and_kills_the_dog():
    temple = Temple(OUTSIDE)
    temple.walk_ok = False
    expect(run_wait(priest.early_leg(temple.log))).to_be(False)
    temple.walk_ok = True
    temple.loc('Large door', ['Knock-at'], interact=temple.opens_chat())
    drives = []
    spy_on(priest, 'drive_dialog', impl=lambda prefer, log: result(drives.append(prefer) is None))
    walks = Calls()
    spy_on(priest, 'walk_with_hops', impl=walks.queued([True, False]))
    expect(run_wait(priest.early_leg(temple.log))).to_be(False)
    expect(drives).to_equal([priest.KNOCK_PREFER])
    temple.npc('Temple guardian', ['Attack'])
    kills = Calls()
    spy_on(priest, 'kill_target', impl=kills.leg('temple guardian'))
    spy_on(priest, 'goto_npc', impl=lambda stop, hops, log: result(False))
    expect(run_wait(priest.early_leg(temple.log))).to_be(False)
    spy_on(priest, 'goto_npc', impl=lambda stop, hops, log: result(True))
    expect(run_wait(priest.early_leg(temple.log))).to_be(False)
    expect(kills.names).to_equal(['temple guardian', 'temple guardian'])
    expect(temple.talks).to_equal(['King Roald'])


test('Priest knocks at the temple, kills the guardian dog below, and reports to King Roald', knocks_and_kills_the_dog)


def hears_the_cell_story_and_hunts_monks():
    temple = Temple(priest.CELL_DOOR_STAND)
    temple.walk_ok = False
    expect(run_wait(priest.cell_story_leg(temple.log))).to_be(False)
    expect(run_wait(priest.monk_hunt_leg(temple.log))).to_be(False)
    temple.walk_ok = True
    expect(run_wait(priest.cell_story_leg(temple.log))).to_be(False)
    expect(temple.logged('no Cell door offering Talk-through')).to_be(True)
    door = temple.loc('Cell door', ['Talk-through'], interact=lambda op: False)
    expect(run_wait(priest.cell_story_leg(temple.log))).to_be(False)
    door._fields['interact'] = lambda op: True
    expect(run_wait(priest.cell_story_leg(temple.log))).to_be(False)
    door._fields['interact'] = temple.opens_chat()
    spy_on(priest, 'drive_dialog', impl=lambda prefer, log: result(prefer == priest.CELL_STORY_PREFER))
    expect(run_wait(priest.cell_story_leg(temple.log))).to_be(True)

    temple.locs = []
    expect(run_wait(priest.monk_hunt_leg(temple.log))).to_be(False)
    expect(temple.logged('no key-dropping Monk of Zamorak (id 1046)')).to_be(True)
    kills = Calls()
    spy_on(priest, 'kill_target', impl=kills.leg('monk of zamorak'))
    temple.npc('Monk of Zamorak', ['Attack'], priest.MONK3_NPC_ID)
    expect(run_wait(priest.monk_hunt_leg(temple.log))).to_be(False)
    expect(kills.names).to_equal(['monk of zamorak'])
    key = Fake(name='Golden key', distance=lambda: 1, interact=lambda op: False)
    temple.ground = [key]
    expect(run_wait(priest.monk_hunt_leg(temple.log))).to_be(False)
    key._fields['interact'] = temple.swaps(0, priest.GOLDEN_KEY_ID)
    expect(run_wait(priest.monk_hunt_leg(temple.log))).to_be(False)
    expect(priest.held_id(priest.GOLDEN_KEY_ID)).to_be(True)


test("Priest hears Drezel's story through the cell door and kills the key-dropping monk for the golden key", hears_the_cell_story_and_hunts_monks)


def locates_the_phase():
    temple = Temple(None)
    expect(run_wait(priest.spine_leg(temple.log))).to_be(False)
    expect(run_wait(priest.water_leg(temple.log))).to_be(False)
    legs = Calls()
    for name in ['essence_leg', 'early_leg', 'water_leg', 'monk_hunt_leg', 'kill_target']:
        spy_on(priest, name, impl=legs.leg(name))
    opens = [True]
    spy_on(priest, 'try_open', impl=lambda name, near, log: result(opens[0]))
    temple.at = priest.GATE1
    expect(run_wait(priest.spine_leg(temple.log))).to_be(True)
    opens[0] = False
    expect(run_wait(priest.spine_leg(temple.log))).to_be(False)
    temple.npc('Temple guardian', ['Attack'])
    temple.at = priest.GATE1
    spy_on(priest, 'goto_npc', impl=lambda stop, hops, log: result(False))
    expect(run_wait(priest.spine_leg(temple.log))).to_be(False)
    spy_on(priest, 'goto_npc', impl=lambda stop, hops, log: result(True))
    temple.at = priest.GATE1
    expect(run_wait(priest.spine_leg(temple.log))).to_be(False)
    expect(temple.talks).to_equal(['King Roald'])
    temple.at = priest.GATE1
    temple.walk_ok = False
    expect(run_wait(priest.spine_leg(temple.log))).to_be(False)
    temple.walk_ok = True

    temple.npcs = []
    temple.at = OUTSIDE
    spy_on(priest, 'enter_temple', impl=lambda log: result(False))
    expect(run_wait(priest.spine_leg(temple.log))).to_be(True)
    spy_on(priest, 'enter_temple', impl=lambda log: result(True))
    expect(run_wait(priest.spine_leg(temple.log))).to_be(True)
    opens[0] = True
    expect(run_wait(priest.spine_leg(temple.log))).to_be(True)
    expect(legs.names).to_equal(['essence_leg', 'kill_target', 'kill_target', 'early_leg', 'monk_hunt_leg', 'water_leg'])


test('Priest reads its phase off where it stands: the mausoleum gates, the temple door, the cell door', locates_the_phase)


def swaps_and_unlocks():
    temple = Temple(priest.GATE1)
    opens = [False]
    spy_on(priest, 'try_open', impl=lambda name, near, log: result(opens[0]))
    spy_on(priest, 'enter_temple', impl=lambda log: result(False))
    expect(run_wait(priest.monument_leg(temple.log))).to_be(False)
    spy_on(priest, 'enter_temple', impl=lambda log: result(True))
    stories = spy_on(priest, 'cell_story_leg', impl=lambda log: result(True))
    expect(run_wait(priest.monument_leg(temple.log))).to_be(False)
    expect(len(stories.calls)).to_be(1)
    opens[0] = True
    expect(run_wait(priest.monument_leg(temple.log))).to_be(False)
    temple.hold(priest.GOLDEN_KEY_ID, use_on=lambda other: False)
    temple.walk_ok = False
    expect(run_wait(priest.monument_leg(temple.log))).to_be(False)
    temple.walk_ok = True
    expect(run_wait(priest.monument_leg(temple.log))).to_be(False)
    expect(temple.logged(f'no Monument at ({priest.MONUMENTS[0].x},{priest.MONUMENTS[0].z})')).to_be(True)
    expect(temple.logged('golden key fit NO monument')).to_be(True)
    for tile in priest.MONUMENTS:
        temple.loc('Monument', [], tile=tile)
    expect(run_wait(priest.monument_leg(temple.log))).to_be(False)

    temple = Temple(priest.CELL_DOOR_STAND)
    spy_on(priest, 'enter_temple', impl=lambda log: result(False))
    expect(run_wait(priest.unlock_leg(temple.log))).to_be(False)
    spy_on(priest, 'enter_temple', impl=lambda log: result(True))
    temple.walk_ok = False
    expect(run_wait(priest.unlock_leg(temple.log))).to_be(False)
    temple.walk_ok = True
    expect(run_wait(priest.unlock_leg(temple.log))).to_be(False)
    temple.loc('Cell door', ['Open'], tile=priest.CELL_DOOR)
    key = temple.hold(priest.IRON_KEY_ID, use_on=lambda other: False)
    expect(run_wait(priest.unlock_leg(temple.log))).to_be(False)
    key._fields['use_on'] = temple.swaps(priest.IRON_KEY_ID, None)
    expect(run_wait(priest.unlock_leg(temple.log))).to_be(False)
    expect(priest.held_id(priest.IRON_KEY_ID)).to_be(False)


test('Priest hears the story when the gate is shut, then swaps the golden key and unlocks the cell with the iron one', swaps_and_unlocks)


def water_leg_failures():
    temple = Temple(priest.CELL_DOOR_STAND)
    entered = [False]
    opens = [False]
    spy_on(priest, 'enter_temple', impl=lambda log: result(entered[0]))
    spy_on(priest, 'try_open', impl=lambda name, near, log: result(opens[0]))
    reports = spy_on(priest, 'reach_and_talk', impl=lambda stop, log: result(True))
    for water in [priest.BLESSED_ID, priest.MURKY_ID, None]:
        temple.pack = []
        if water is not None:
            temple.hold(water, use_on=lambda other: False)
        expect(run_wait(priest.water_leg(temple.log))).to_be(False)
    entered[0] = True
    for water in [priest.BLESSED_ID, priest.MURKY_ID]:
        temple.pack = []
        temple.hold(water, use_on=lambda other: False)
        temple.walk_ok = False
        opens[0] = True
        expect(run_wait(priest.water_leg(temple.log))).to_be(False)
        temple.walk_ok = True
        opens[0] = False
        expect(run_wait(priest.water_leg(temple.log))).to_be(False)
    opens[0] = True
    for water in [priest.BLESSED_ID, priest.MURKY_ID]:
        temple.pack = []
        temple.hold(water, use_on=lambda other: False)
        expect(run_wait(priest.water_leg(temple.log))).to_be(False)
        temple.loc('Coffin', [], tile=priest.COFFIN)
        temple.npc('Drezel')
        expect(run_wait(priest.water_leg(temple.log))).to_be(False)
        temple.locs = []
        temple.npcs = []
    temple.pack = []
    temple.hold(priest.BLESSED_ID, use_on=temple.swaps(priest.BLESSED_ID, None))
    temple.loc('Coffin', [], tile=priest.COFFIN)
    opens[0] = False
    expect(run_wait(priest.water_leg(temple.log))).to_be(False)
    expect(len(reports.calls)).to_be(0)


test('Priest abandons a water step whose temple, cell door, coffin or Drezel is out of reach', water_leg_failures)


def fills_the_bucket():
    temple = Temple(priest.CELL_DOOR_STAND)
    spy_on(priest, 'enter_temple', impl=lambda log: result(True))
    gates = []
    spy_on(priest, 'try_open', impl=Calls().queued(gates))
    spy_on(priest, 'reach_and_talk', impl=lambda stop, log: result(True))
    spy_on(priest, 'essence_leg', impl=lambda log: result('essence'))
    expect(run_wait(priest.water_leg(temple.log))).to_be('essence')
    gates.extend([False])
    expect(run_wait(priest.water_leg(temple.log))).to_be(False)

    steps = []

    def execute(step, hops, log):
        steps.append(step.kind)
        return False
        yield
    spy_on(priest, 'execute_step', impl=execute)
    gates.extend([True, True, False])
    expect(run_wait(priest.water_leg(temple.log))).to_be(False)
    expect(steps).to_equal(['withdraw', 'buy'])

    bucket = temple.hold(1925, 'Bucket', use_on=lambda other: False)
    gates.extend([True, True, False, False])
    expect(run_wait(priest.water_leg(temple.log))).to_be(False)
    gates.extend([True, True, False, True])
    temple.walk_ok = False
    expect(run_wait(priest.water_leg(temple.log))).to_be(False)
    temple.walk_ok = True
    gates.extend([True, True, False, True])
    expect(run_wait(priest.water_leg(temple.log))).to_be(False)
    expect(temple.logged('no Well/Bucket in reach at the stand')).to_be(True)
    temple.loc('Well', [])
    gates.extend([True, True, False, True])
    expect(run_wait(priest.water_leg(temple.log))).to_be(False)
    bucket._fields['use_on'] = temple.swaps(1925, priest.MURKY_ID)
    gates.extend([True, True, False, True])
    expect(run_wait(priest.water_leg(temple.log))).to_be(False)
    expect(priest.held_id(priest.MURKY_ID)).to_be(True)


test('Priest fills a bucket at the mausoleum well, buying one first when the bank has none', fills_the_bucket)


def banks_early_essence():
    temple = Temple(priest.GATE1)
    temple.hold(1436, 'Rune essence', 9)
    spy_on(priest, 'journal_complete', returns=False)
    gates = []
    spy_on(priest, 'try_open', impl=Calls().queued(gates))
    opened = [False]
    spy_on(priest, 'open_bank_leg', impl=lambda reason, tile, log: result(opened[0]))

    def deposit(matches):
        temple.pack = [i for i in temple.pack if not matches(i.name, i.id)]
        return True
        yield
    spy_on(bank, 'deposit_all_matching', impl=deposit)
    temple.walk_ok = False
    gates.extend([False])
    expect(run_wait(priest.essence_leg(temple.log))).to_be(False)
    temple.walk_ok = True
    gates.extend([True, False])
    expect(run_wait(priest.essence_leg(temple.log))).to_be(False)
    expect(temple.logged('Gate 2 refused during essence phase')).to_be(True)
    opened[0] = True
    gates.extend([False])
    expect(run_wait(priest.essence_leg(temple.log))).to_be(False)
    expect(inventory.count('Rune essence')).to_be(0)

    temple.hold(1436, 'Rune essence', 9)
    gates.extend([True, True])
    temple.walk_ok = False
    expect(run_wait(priest.essence_leg(temple.log))).to_be(False)
    temple.pack = []
    expect(run_wait(priest.essence_leg(temple.log))).to_be(False)


test('Priest banks essence a stage-locked gate refuses, rather than carrying it through the early phase', banks_early_essence)


def mining_failures():
    temple = Temple(None)
    expect(run_wait(priest.mine_essence(temple.log))).to_be(False)
    temple.at = priest.AUBURY_TILE
    temple.hold(1265, 'Bronze pickaxe')
    temple.walk_ok = False
    expect(run_wait(priest.mine_essence(temple.log))).to_be(False)
    temple.walk_ok = True
    expect(run_wait(priest.mine_essence(temple.log))).to_be(False)
    expect(temple.logged('no Aubury offering Teleport')).to_be(True)
    aubury = temple.npc('Aubury', ['Teleport'], interact=lambda op: False)
    expect(run_wait(priest.mine_essence(temple.log))).to_be(False)
    aubury._fields['interact'] = lambda op: True
    expect(run_wait(priest.mine_essence(temple.log))).to_be(False)

    in_mine = [True]
    spy_on(priest, 'in_ess_mine', impl=lambda x, z: z == 10000 and in_mine[0])
    temple.at = Tile(2900, 10000, 0)
    spy_on(priest, 'free_slots', returns=5)
    rock = temple.loc('Rune Essence', ['Mine'], interact=lambda op: False)
    expect(run_wait(priest.mine_essence(temple.log))).to_be(False)
    expect(temple.logged('no Portal to leave the mine')).to_be(True)
    temple.locs = []
    expect(run_wait(priest.mine_essence(temple.log))).to_be(False)

    def dig(op):
        in_mine[0] = False
        return True
    rock._fields['interact'] = dig
    temple.locs = [rock]
    expect(run_wait(priest.mine_essence(temple.log))).to_be(False)
    expect(temple.logged('left the mine mid-dig')).to_be(True)


test('Priest gives up a mining trip Aubury will not teleport, and leaves a mine it was pulled out of', mining_failures)
