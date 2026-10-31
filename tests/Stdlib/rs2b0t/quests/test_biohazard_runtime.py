"""Biohazard's legs against spied facades: the wall and the headquarters door, the distraction, the stew and the
key, and the smuggle through Varrock, each through its success and its failures."""

import rs2004.quests.defs.biohazard.ardougne as ardougne
import rs2004.quests.defs.biohazard.gear as gear
import rs2004.quests.defs.biohazard.travel as travel
import rs2004.quests.defs.biohazard.varrock as varrock
import rs2004.quests.defs.biohazard.west as west
from rs2004 import execution
from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import chat_dialog
from rs2004.entities import ground_items, locs, npcs
from rs2004.execution import event_signal
from rs2004.game import game, skills
from rs2004.geometry import Tile
from rs2004.items import equipment, inventory
from rs2004.quests.defs.biohazard.areas import BIO_ITEM, BIO_LOC, BIO_NPC, BIO_TILE, SICK_MOURNER_ID
from rs2004.reach import reach
from rs2004.trade import shop
from rs2004.traversal import traversal

MAINLAND = Tile(2616, 3332, 0)
WEST = Tile(2529, 3304, 0)
HQ = Tile(2551, 3321, 0)
HQ_TOP = Tile(2550, 3326, 1)
CASTLE_TOP = Tile(2578, 3293, 1)
SEWER = Tile(2530, 9703, 0)
QUARTER = Tile(3270, 3390, 0)
PIGEON_SPOT = Tile(2562, 3303, 0)


def result(value):
    return value
    yield


def leg(calls, name, ok=True):
    def run(*args):
        calls.append(name)
        return ok
        yield
    return run


class Ardougne:
    """The player either side of the wall, with the pack, what's worn, the scene and the dialogue."""

    def __init__(self, at):
        self.at = at
        self.pack = []
        self.worn = []
        self.locs = []
        self.ground = []
        self.npcs = []
        self.walk_ok = True
        self.walks = []
        self.dialog = 'done'
        self.talk_ok = True
        self.talks = []
        self.prompts = []
        self.prompt_lands = None
        self.chat_open = False
        self.lines = []
        spy_on(game, 'tile', impl=lambda: self.at)
        spy_on(locs, 'query', impl=querying(lambda: self.locs))
        spy_on(ground_items, 'query', impl=querying(lambda: self.ground))
        spy_on(npcs, 'query', impl=querying(lambda: self.npcs))
        spy_on(inventory, 'items', impl=lambda: self.pack)
        spy_on(equipment, 'items', impl=lambda: self.worn)
        spy_on(traversal, 'walk_resilient', impl=self.walk)
        spy_on(reach, 'npc_dialog', impl=lambda npc, near, log=None: result(self.dialog))
        spy_on(chat_dialog, 'is_open', impl=lambda: self.chat_open)
        spy_on(chat_dialog, 'can_continue', returns=False)
        spy_on(travel, 'talk_strict', impl=self.talk)
        spy_on(travel, 'prompt_loc', impl=self.prompt)
        for module in [travel, ardougne, varrock, west]:
            spy_on(module, 'settle_scene', impl=instant_ticks)
            spy_on(module, 'drive_until', impl=lambda expect, prefer, log, ms=30000: result(expect()))
        patch(execution, 'delay_until', instant_until)
        patch(execution, 'delay_ticks', instant_ticks)

    def log(self, text):
        self.lines.append(text)

    def logged(self, part):
        return any([part in line for line in self.lines])

    def walk(self, tile, radius=2, attempts=None, timeout_ms=None, log=None):
        self.walks.append(tile)
        if self.walk_ok:
            self.at = tile
        return self.walk_ok
        yield

    def talk(self, npc, prefer, log):
        self.talks.append(npc)
        return self.talk_ok
        yield

    def prompt(self, step, log):
        self.prompts.append(step.id)
        if self.prompt_lands is not None:
            self.at = self.prompt_lands
        return step.expect()
        yield

    def hold(self, item, use_on=None, interact=None, actions=None):
        held = Fake(id=item.id, name=item.name, count=1, use_on=use_on if use_on is not None else (lambda other: True),
                    interact=interact if interact is not None else (lambda op: True),
                    actions=lambda: actions if actions is not None else ['Wear'])
        self.pack.append(held)
        return held

    def drop(self, item):
        self.pack = [held for held in self.pack if held.id != item.id]

    def wears(self, item):
        self.worn.append(Fake(id=item.id, name=item.name, count=1))

    def loc(self, id, interact=None):
        made = Fake(id=id, name='Loc', actions=lambda: ['Open', 'Search'], distance=lambda: 1,
                    interact=interact if interact is not None else (lambda op: True))
        self.locs.append(made)
        return made

    def moves(self, tile):
        def go(*args):
            self.at = tile
            return True
        return go

    def gives(self, item):
        def give(*args):
            self.hold(item)
            return True
        return give

    def takes(self, item):
        def take(*args):
            self.drop(item)
            return True
        return take


def wears_by_id():
    town = Ardougne(MAINLAND)
    town.wears(BIO_ITEM.DOCTOR_GOWN)
    expect(gear.worn_id(BIO_ITEM.DOCTOR_GOWN.id)).to_be(True)
    expect(run_wait(gear.wear(BIO_ITEM.DOCTOR_GOWN, town.log))).to_be(True)
    expect(run_wait(gear.wear(BIO_ITEM.PRIEST_GOWN, town.log))).to_be(False)
    expect(town.logged('in the pack to wear')).to_be(True)
    town.hold(BIO_ITEM.PRIEST_GOWN, actions=['Drop'])
    expect(run_wait(gear.wear(BIO_ITEM.PRIEST_GOWN, town.log))).to_be(False)
    expect(town.logged('offered no Wear')).to_be(True)
    town.pack = []

    def puts_on(op):
        town.drop(BIO_ITEM.PRIEST_GOWN)
        town.wears(BIO_ITEM.PRIEST_GOWN)
        return True
    town.hold(BIO_ITEM.PRIEST_GOWN, interact=puts_on)
    expect(gear.held_id(BIO_ITEM.PRIEST_GOWN.id)).to_be(1)
    expect(run_wait(gear.wear(BIO_ITEM.PRIEST_GOWN, town.log))).to_be(True)


test('the priest suit and the gown are worn by object id', wears_by_id)


def crosses_the_wall():
    town = Ardougne(MAINLAND)
    expect(travel.area()).to_be('mainland')
    town.loc(BIO_LOC.HQ_DOOR)
    expect(travel.loc_by_id(BIO_LOC.HQ_DOOR, 'Open', 8)).to_be_truthy()
    expect(travel.loc_by_id(BIO_LOC.VARROCK_GATE, None, 8)).to_be_falsy()
    town.at = BIO_TILE.ELENA
    expect(run_wait(travel.walk_to(BIO_TILE.ELENA, 2, town.log))).to_be(True)
    expect(len(town.walks)).to_be(0)
    town.walk_ok = False
    expect(run_wait(travel.talk_at(BIO_NPC.ELENA, BIO_TILE.JERICO, [], town.log))).to_be(False)
    town.walk_ok = True
    town.dialog = 'failed'
    expect(run_wait(travel.talk_at(BIO_NPC.ELENA, BIO_TILE.JERICO, [], town.log))).to_be(False)
    expect(town.logged('no dialogue with Elena')).to_be(True)
    town.dialog = 'done'

    town.at = MAINLAND
    expect(run_wait(travel.climb_with_omart(town.log))).to_be(False)

    def over(npc, prefer, log):
        town.at = WEST
        return True
        yield
    spy_on(travel, 'talk_strict', impl=over)
    expect(run_wait(travel.climb_with_omart(town.log))).to_be(True)

    def back(npc, prefer, log):
        town.at = MAINLAND
        return True
        yield
    spy_on(travel, 'talk_strict', impl=back)
    expect(run_wait(travel.climb_with_kilron(town.log))).to_be(True)


test("Omart's ladder crosses west and Kilron's crosses back, each landing on its side", crosses_the_wall)


def works_the_headquarters_door():
    town = Ardougne(HQ)
    expect(run_wait(travel.enter_hq(town.log))).to_be(True)
    town.at = WEST
    expect(run_wait(travel.enter_hq(town.log))).to_be(False)
    expect(town.logged("Doctors' gown has to be worn")).to_be(True)
    town.wears(BIO_ITEM.DOCTOR_GOWN)
    expect(run_wait(travel.enter_hq(town.log))).to_be(False)
    town.prompt_lands = HQ
    expect(run_wait(travel.enter_hq(town.log))).to_be(True)
    expect(town.prompts[-1]).to_be(BIO_LOC.HQ_DOOR)

    town.prompt_lands = None
    town.at = HQ_TOP
    town.walk_ok = False
    expect(run_wait(travel.leave_hq(town.log))).to_be(False)
    town.walk_ok = True
    town.at = WEST
    expect(run_wait(travel.leave_hq(town.log))).to_be(True)
    town.at = HQ
    expect(run_wait(travel.leave_hq(town.log))).to_be(False)
    town.prompt_lands = WEST
    town.at = HQ
    expect(run_wait(travel.leave_hq(town.log))).to_be(True)


test('the headquarters door is crossed by its own prompt, in the gown going in and from inside going out', works_the_headquarters_door)


def routes_between_sides():
    town = Ardougne(WEST)
    calls = []
    for name in ['climb_with_omart', 'climb_with_kilron', 'leave_hq']:
        spy_on(travel, name, impl=leg(calls, name))
    for at in [WEST, HQ, HQ_TOP]:
        town.at = at
        expect(run_wait(travel.go_west(town.log))).to_be(True)
    town.at = MAINLAND
    expect(run_wait(travel.go_west(town.log))).to_be(True)
    for at in [CASTLE_TOP, SEWER]:
        town.at = at
        expect(run_wait(travel.go_west(town.log))).to_be(True)
        town.walk_ok = False
        town.at = at
        expect(run_wait(travel.go_west(town.log))).to_be(False)
        town.walk_ok = True
    town.at = Tile(2616, 3332, 2)
    expect(run_wait(travel.go_west(town.log))).to_be(False)
    expect(run_wait(travel.go_mainland(town.log))).to_be(False)

    town.at = MAINLAND
    expect(run_wait(travel.go_mainland(town.log))).to_be(True)
    town.at = WEST
    expect(run_wait(travel.go_mainland(town.log))).to_be(True)
    spy_on(travel, 'climb_with_kilron', impl=leg(calls, 'kilron', False))
    town.at = WEST
    expect(run_wait(travel.go_mainland(town.log))).to_be(True)
    expect(town.logged('Kilron would not cross')).to_be(True)
    town.at = SEWER
    expect(run_wait(travel.go_mainland(town.log))).to_be(True)
    spy_on(travel, 'leave_hq', impl=leg(calls, 'leave_hq', False))
    town.at = HQ
    expect(run_wait(travel.go_mainland(town.log))).to_be(False)

    def out(log):
        town.at = MAINLAND
        return True
        yield
    spy_on(travel, 'leave_hq', impl=out)
    town.at = HQ_TOP
    expect(run_wait(travel.go_mainland(town.log))).to_be(True)


test('each side has its way west and back, Kilron or the manhole, and the headquarters out first', routes_between_sides)


def distracts_the_mourners():
    town = Ardougne(MAINLAND)
    for talk in [ardougne.start_quest, ardougne.ask_jerico, ardougne.hand_over_distillator, ardougne.report_to_elena,
                 ardougne.ask_elena_for_replacements, ardougne.confront_lathas]:
        expect(run_wait(talk(town.log))).to_be(True)
    town.walk_ok = False
    for take in [ardougne.take_birdfeed, ardougne.take_pigeons, ardougne.feed_the_tower]:
        expect(run_wait(take(town.log))).to_be(False)
    town.walk_ok = True
    expect(run_wait(ardougne.take_birdfeed(town.log))).to_be(False)
    expect(town.logged("no cupboard in Jerico's house")).to_be(True)

    def opens(op):
        town.locs = []
        town.loc(BIO_LOC.JERICO_CUPBOARD_OPEN, interact=town.gives(BIO_ITEM.BIRDFEED))
        return True
    town.loc(BIO_LOC.JERICO_CUPBOARD_SHUT, interact=opens)
    expect(run_wait(ardougne.take_birdfeed(town.log))).to_be(True)
    expect(run_wait(ardougne.take_birdfeed(town.log))).to_be(True)
    town.locs = []
    town.loc(BIO_LOC.JERICO_CUPBOARD_OPEN, interact=lambda op: False)
    expect(run_wait(ardougne.take_birdfeed(town.log))).to_be(False)

    expect(run_wait(ardougne.take_pigeons(town.log))).to_be(False)
    expect(town.logged('waiting for the respawn')).to_be(True)
    town.ground = [Fake(id=BIO_ITEM.PIGEONS.id, name='Pigeon cage', distance=lambda: 1, interact=lambda op: False)]
    expect(run_wait(ardougne.take_pigeons(town.log))).to_be(False)
    town.ground = [Fake(id=BIO_ITEM.PIGEONS.id, name='Pigeon cage', distance=lambda: 1, interact=town.gives(BIO_ITEM.PIGEONS))]
    expect(run_wait(ardougne.take_pigeons(town.log))).to_be(True)

    town.pack = []
    expect(run_wait(ardougne.feed_the_tower(town.log))).to_be(False)
    expect(town.logged('no Watchtower')).to_be(True)
    town.loc(BIO_LOC.WATCHTOWER)
    expect(run_wait(ardougne.feed_the_tower(town.log))).to_be(False)
    town.hold(BIO_ITEM.BIRDFEED, use_on=lambda other: False)
    expect(run_wait(ardougne.feed_the_tower(town.log))).to_be(False)
    town.pack = []
    town.hold(BIO_ITEM.BIRDFEED, use_on=lambda other: True)
    expect(run_wait(ardougne.feed_the_tower(town.log))).to_be(False)
    town.pack = []
    town.hold(BIO_ITEM.BIRDFEED, use_on=town.takes(BIO_ITEM.BIRDFEED))
    expect(run_wait(ardougne.feed_the_tower(town.log))).to_be(True)

    town.at = MAINLAND
    town.walk_ok = False
    expect(run_wait(ardougne.release_pigeons(town.log))).to_be(False)
    town.walk_ok = True
    spy_on(ardougne, 'walk_to', impl=lambda to, radius, log: result(True))
    expect(run_wait(ardougne.release_pigeons(town.log))).to_be(False)
    expect(town.logged('outside the pigeon-release box')).to_be(True)
    town.at = PIGEON_SPOT
    expect(run_wait(ardougne.release_pigeons(town.log))).to_be(False)
    expect(town.logged('no full Pigeon cage')).to_be(True)
    town.hold(BIO_ITEM.PIGEONS, interact=town.takes(BIO_ITEM.PIGEONS))
    expect(run_wait(ardougne.release_pigeons(town.log))).to_be(True)


test("the seed comes from Jerico's cupboard, the birds from behind his house, and both go to the tower", distracts_the_mourners)


def poisons_and_takes_the_key():
    town = Ardougne(WEST)
    town.walk_ok = False
    for take in [west.take_rotten_apples, west.poison_the_stew, west.take_doctor_gown, west.search_the_crate]:
        expect(run_wait(take(town.log))).to_be(False)
    town.walk_ok = True
    expect(run_wait(west.take_rotten_apples(town.log))).to_be(False)
    town.ground = [Fake(id=BIO_ITEM.ROTTEN_APPLES.id, name='Rotten apples', distance=lambda: 1, interact=lambda op: False)]
    expect(run_wait(west.take_rotten_apples(town.log))).to_be(False)
    town.ground = [Fake(id=BIO_ITEM.ROTTEN_APPLES.id, name='Rotten apples', distance=lambda: 1, interact=town.gives(BIO_ITEM.ROTTEN_APPLES))]
    expect(run_wait(west.take_rotten_apples(town.log))).to_be(True)

    town.pack = []
    expect(run_wait(west.poison_the_stew(town.log))).to_be(False)
    expect(town.logged('no Cauldron')).to_be(True)
    town.loc(BIO_LOC.CAULDRON)
    town.hold(BIO_ITEM.ROTTEN_APPLES, use_on=lambda other: False)
    expect(run_wait(west.poison_the_stew(town.log))).to_be(False)
    town.pack = []
    town.hold(BIO_ITEM.ROTTEN_APPLES, use_on=lambda other: True)
    expect(run_wait(west.poison_the_stew(town.log))).to_be(False)
    town.pack = []
    town.hold(BIO_ITEM.ROTTEN_APPLES, use_on=town.takes(BIO_ITEM.ROTTEN_APPLES))
    expect(run_wait(west.poison_the_stew(town.log))).to_be(True)

    town.locs = []
    expect(run_wait(west.take_doctor_gown(town.log))).to_be(False)

    def opens(op):
        town.locs = []
        town.loc(BIO_LOC.NURSE_CUPBOARD_OPEN, interact=town.gives(BIO_ITEM.DOCTOR_GOWN))
        return True
    town.loc(BIO_LOC.NURSE_CUPBOARD_SHUT, interact=opens)
    expect(run_wait(west.take_doctor_gown(town.log))).to_be(True)
    expect(run_wait(west.take_doctor_gown(town.log))).to_be(True)
    town.locs = []
    town.loc(BIO_LOC.NURSE_CUPBOARD_OPEN, interact=lambda op: False)
    expect(run_wait(west.take_doctor_gown(town.log))).to_be(False)

    town.at = HQ_TOP
    town.pack = []
    spy_on(west, 'wear', impl=lambda item, log: result(True))
    spy_on(west, 'enter_hq', impl=lambda log: result(True))
    expect(run_wait(west.search_the_crate(town.log))).to_be(False)
    expect(town.logged('no Key in the pack')).to_be(True)
    town.hold(BIO_ITEM.MOURNER_KEY)
    expect(run_wait(west.search_the_crate(town.log))).to_be(False)
    expect(town.logged('no Crate')).to_be(True)
    town.loc(BIO_LOC.HQ_CRATE, interact=lambda op: False)
    expect(run_wait(west.search_the_crate(town.log))).to_be(False)
    town.locs = []
    town.loc(BIO_LOC.HQ_CRATE, interact=town.gives(BIO_ITEM.DISTILLATOR))
    expect(run_wait(west.search_the_crate(town.log))).to_be(True)
    spy_on(west, 'enter_hq', impl=lambda log: result(False))
    expect(run_wait(west.search_the_crate(town.log))).to_be(False)


test('the apples go in the stew over the fence, the gown comes from the nurse, and the key opens the crate', poisons_and_takes_the_key)


class Mourner:
    """The sick mourner upstairs: Attack lands, and after hits he dies and leaves the key."""

    def __init__(self, town, hits_to_die, drops=True):
        self.town = town
        self.left = hits_to_die
        self.drops = drops
        self.npc = Fake(id=SICK_MOURNER_ID, name=BIO_NPC.MOURNER, index=7, distance=lambda: 2, tile=lambda: HQ_TOP,
                        targets_another_player=lambda: False, interact=self.attack)

    def attack(self, op):
        if op == 'Talk-to':
            return True
        self.left -= 1
        if self.left <= 0:
            self.town.npcs = []
            if self.drops:
                self.town.hold(BIO_ITEM.MOURNER_KEY)
        return True


def fights_for_the_key():
    town = Ardougne(HQ_TOP)
    hp = {'now': 70}
    spy_on(skills, 'level', returns=70)
    spy_on(skills, 'effective', impl=lambda name: hp['now'])
    spy_on(game, 'set_auto_retaliate', returns=True)
    spy_on(game, 'in_combat', returns=False)
    spy_on(event_signal, 'pending', returns=False)
    spy_on(sustain, 'run', impl=lambda: result(None))
    expect(west.hungry()).to_be(False)
    hp['now'] = 50
    expect(west.hungry()).to_be(True)
    hp['now'] = 70

    mourner = Mourner(town, 3)
    town.npcs = [mourner.npc]
    expect(west.sick_mourner()).to_be(mourner.npc)
    expect(run_wait(west.fight_for_key(town.log))).to_be(True)
    expect(town.logged('took the key off the mourner')).to_be(True)

    town.pack = []
    mourner = Mourner(town, 1, False)
    town.npcs = [mourner.npc]
    expect(run_wait(west.fight_for_key(town.log))).to_be(False)
    expect(town.logged('dropped no key')).to_be(True)

    spy_on(event_signal, 'pending', returns=True)
    expect(run_wait(west.fight_for_key(town.log))).to_be(False)
    expect(town.logged('yielding to a random event')).to_be(True)

    spy_on(event_signal, 'pending', returns=False)
    state = {'boxes': 1}

    def continue_():
        state['boxes'] -= 1
        return True
        yield
    spy_on(chat_dialog, 'can_continue', impl=lambda: state['boxes'] > 0)
    spy_on(chat_dialog, 'continue_', impl=continue_)
    hp['now'] = 40

    def eats():
        hp['now'] = 70
        return None
        yield
    spy_on(sustain, 'run', impl=eats)
    town.pack = []
    mourner = Mourner(town, 2)
    town.npcs = [mourner.npc]
    expect(run_wait(west.fight_for_key(town.log))).to_be(True)

    town.pack = []
    stubborn = Fake(id=SICK_MOURNER_ID, name=BIO_NPC.MOURNER, index=8, distance=lambda: 2, tile=lambda: HQ_TOP,
                    targets_another_player=lambda: False, interact=lambda op: True)
    town.npcs = [stubborn]
    spy_on(game, 'in_combat', returns=True)
    expect(run_wait(west.fight_for_key(town.log))).to_be(False)
    expect(town.logged('gave up after')).to_be(True)


test('the sick mourner is fought to his key, through boxes, food and events, and given up when he never falls', fights_for_the_key)


def provokes_the_mourner():
    town = Ardougne(HQ_TOP)
    town.hold(BIO_ITEM.MOURNER_KEY)
    expect(run_wait(west.take_mourner_key(town.log))).to_be(True)
    town.pack = []
    spy_on(west, 'wear', impl=lambda item, log: result(False))
    expect(run_wait(west.take_mourner_key(town.log))).to_be(False)
    spy_on(west, 'wear', impl=lambda item, log: result(True))
    spy_on(west, 'enter_hq', impl=lambda log: result(False))
    expect(run_wait(west.take_mourner_key(town.log))).to_be(False)
    spy_on(west, 'enter_hq', impl=lambda log: result(True))
    town.walk_ok = False
    expect(run_wait(west.take_mourner_key(town.log))).to_be(False)
    town.walk_ok = True
    expect(run_wait(west.take_mourner_key(town.log))).to_be(False)
    expect(town.logged('no sick Mourner')).to_be(True)
    refuses = Fake(id=SICK_MOURNER_ID, name=BIO_NPC.MOURNER, index=1, distance=lambda: 2, tile=lambda: HQ_TOP,
                   targets_another_player=lambda: False, interact=lambda op: False)
    town.npcs = [refuses]
    expect(run_wait(west.take_mourner_key(town.log))).to_be(False)
    town.npcs = [Mourner(town, 1).npc]
    town.chat_open = True
    spy_on(west, 'drive_choice', impl=lambda prefer, log: result(True))
    spy_on(west, 'fight_for_key', impl=lambda log: result(True))
    expect(run_wait(west.take_mourner_key(town.log))).to_be(True)


test('the mourner is talked to in the gown, his prompt answered, then fought', provokes_the_mourner)


def smuggles_through_varrock():
    town = Ardougne(BIO_TILE.CHEMIST)
    expect(run_wait(varrock.get_touch_paper(town.log))).to_be(True)
    expect(run_wait(varrock.hand_to_errand_boys(town.log))).to_be(False)
    for errand in varrock.ERRANDS:
        town.hold(errand.vial)
    town.talk_ok = False
    expect(run_wait(varrock.hand_to_errand_boys(town.log))).to_be(False)
    expect(town.logged('would not take')).to_be(True)
    town.talk_ok = True

    def hands(npc, prefer, log):
        vial = [e.vial for e in varrock.ERRANDS if e.npc == npc][0]
        town.drop(vial)
        return True
        yield
    spy_on(travel, 'talk_strict', impl=hands)
    expect(run_wait(varrock.hand_to_errand_boys(town.log))).to_be(True)
    expect(town.logged('carrying the')).to_be(True)

    spy_on(travel, 'talk_strict', impl=lambda npc, prefer, log: result(False))
    expect(run_wait(varrock.collect_from_errand_boys(town.log))).to_be(False)
    spy_on(travel, 'talk_strict', impl=lambda npc, prefer, log: result(True))
    expect(run_wait(varrock.collect_from_errand_boys(town.log))).to_be(False)
    expect(town.logged('did not hand back')).to_be(True)

    def returns(npc, prefer, log):
        town.hold([e.vial for e in varrock.ERRANDS if e.npc == npc][0])
        return True
        yield
    spy_on(travel, 'talk_strict', impl=returns)
    expect(run_wait(varrock.collect_from_errand_boys(town.log))).to_be(True)
    expect(run_wait(varrock.collect_from_errand_boys(town.log))).to_be(False)


test('the vials go to the errand boys who will not ruin them, and come back at the Dancing Donkey', smuggles_through_varrock)


def dresses_as_a_priest():
    town = Ardougne(BIO_TILE.THESSALIA)
    town.walk_ok = False
    expect(run_wait(varrock.buy_priest_suit(town.log))).to_be(False)
    town.walk_ok = True
    spy_on(shop, 'open', impl=lambda npc: result(False))
    expect(run_wait(varrock.buy_priest_suit(town.log))).to_be(False)
    expect(town.logged("could not open Thessalia's shop")).to_be(True)
    spy_on(shop, 'open', impl=lambda npc: result(True))
    spy_on(shop, 'close', impl=lambda: result(True))
    spy_on(shop, 'buy_by_id', impl=lambda id, n: result(0))
    expect(run_wait(varrock.buy_priest_suit(town.log))).to_be(False)
    expect(town.logged('sold no priest gown')).to_be(True)
    bought = []

    def buys(id, n):
        bought.append(id)
        return 1
        yield
    spy_on(shop, 'buy_by_id', impl=buys)
    town.hold(BIO_ITEM.PRIEST_GOWN)
    expect(run_wait(varrock.buy_priest_suit(town.log))).to_be(True)
    expect(bought).to_equal([BIO_ITEM.PRIEST_ROBE.id])

    spy_on(varrock, 'wear', impl=lambda item, log: result(False))
    expect(run_wait(varrock.visit_guidor(town.log))).to_be(False)
    spy_on(varrock, 'wear', impl=lambda item, log: result(True))
    town.walk_ok = False
    expect(run_wait(varrock.visit_guidor(town.log))).to_be(False)
    town.walk_ok = True
    town.loc(BIO_LOC.GUIDOR_DOOR, interact=lambda op: False)
    expect(run_wait(varrock.visit_guidor(town.log))).to_be(False)
    town.locs = []
    town.loc(BIO_LOC.GUIDOR_DOOR)
    town.talk_ok = False
    expect(run_wait(varrock.visit_guidor(town.log))).to_be(False)
    town.talk_ok = True
    town.hold(BIO_ITEM.PLAGUE_SAMPLE)
    expect(run_wait(varrock.visit_guidor(town.log))).to_be(False)
    town.drop(BIO_ITEM.PLAGUE_SAMPLE)
    expect(run_wait(varrock.visit_guidor(town.log))).to_be(True)


test("Thessalia's suit is bought by id, worn, and gets the kit past Guidor's wife", dresses_as_a_priest)


def passes_the_east_gate():
    town = Ardougne(BIO_TILE.GATE_OUTSIDE)
    town.hold(BIO_ITEM.ETHENEA)
    expect(run_wait(varrock.cross_east_gate(town.log))).to_be(False)
    expect(town.logged('the gate guard would take these vials')).to_be(True)
    town.pack = []
    town.walk_ok = False
    expect(run_wait(varrock.pass_varrock_gate(town.log))).to_be(False)
    expect(run_wait(varrock.cross_east_gate(town.log))).to_be(False)
    town.walk_ok = True
    town.at = BIO_TILE.GATE_OUTSIDE
    expect(run_wait(varrock.pass_varrock_gate(town.log))).to_be(False)
    expect(town.logged('no Varrock east gate')).to_be(True)
    town.loc(BIO_LOC.VARROCK_GATE[0], interact=lambda op: False)
    expect(run_wait(varrock.pass_varrock_gate(town.log))).to_be(False)
    town.locs = []
    town.loc(BIO_LOC.VARROCK_GATE[1])
    expect(run_wait(varrock.cross_east_gate(town.log))).to_be(True)
    town.at = QUARTER
    expect(run_wait(varrock.cross_east_gate(town.log))).to_be(True)
    expect(run_wait(varrock.leave_quarter(town.log))).to_be(True)
    town.at = MAINLAND
    expect(run_wait(varrock.leave_quarter(town.log))).to_be(True)


test("the Varrock east gate's search is sat out both ways, and refuses anyone carrying a vial", passes_the_east_gate)
