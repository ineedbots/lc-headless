"""Troll Stronghold's own legs against spied facades (its combat is test_trollstronghold_runtime.py's): the walks, the
boots, Dad, the General, the cell keys and the prisoners; and the five phase-17c journal readers."""

import _core
import rs2004.quests.defs.trollstronghold as troll
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.entities import ground_items, locs, npcs
from rs2004.game import game, reader, skills
from rs2004.geometry import Tile
from rs2004.items import equipment, inventory
from rs2004.quests.defs.biohazard.journal import BIO_STAGE, read_biohazard_progress
from rs2004.quests.defs.deathplateau.journal import DP_STAGE, read_death_plateau_progress
from rs2004.quests.defs.eadgar import journal as eadgar_journal
from rs2004.quests.defs.eadgar.journal import EADGAR_FLAG, EADGAR_STAGE, read_eadgar_progress
from rs2004.quests.defs.plaguecity.journal import PC_STAGE, read_plague_progress
from rs2004.quests.defs.trollstronghold.areas import ITEM, TILE
from rs2004.quests.defs.trollstronghold.journal import TROLL_STAGE, read_troll_stronghold_progress
from rs2004.quests.engine.types import QuestProgress, QuestSnapshot
from rs2004.tabs import quests
from rs2004.traversal import traversal

BURTHORPE = Tile(2896, 3528, 0)
MOUNTAIN = Tile(2840, 3690, 0)
STRONGHOLD = Tile(2837, 10090, 2)


def result(value):
    return value
    yield


class Trolls:
    """The player between Burthorpe and the stronghold, with the pack, the worn kit and the scene."""

    def __init__(self, at):
        self.at = at
        self.pack = []
        self.worn = []
        self.locs = []
        self.ground = []
        self.npcs = []
        self.walk_ok = True
        self.walks = []
        self.plans = []
        self.fight_ok = True
        self.lines = []
        spy_on(game, 'tile', impl=lambda: self.at)
        spy_on(locs, 'query', impl=querying(lambda: self.locs))
        spy_on(ground_items, 'query', impl=querying(lambda: self.ground))
        spy_on(npcs, 'query', impl=querying(lambda: self.npcs))
        spy_on(inventory, 'contains', impl=lambda name: self.count(name) > 0)
        spy_on(inventory, 'count', impl=self.count)
        spy_on(equipment, 'contains', impl=lambda name: name in self.worn)
        spy_on(traversal, 'walk_resilient', impl=self.walk)
        spy_on(troll, 'fight', impl=self.fight)
        spy_on(troll, 'attackable', impl=lambda name, within: None)
        patch(execution, 'delay_until', instant_until)
        patch(execution, 'delay_ticks', instant_ticks)

    def log(self, text):
        self.lines.append(text)

    def logged(self, part):
        return any([part in line for line in self.lines])

    def count(self, name):
        return len([held for held in self.pack if held == name])

    def walk(self, tile, radius=2, attempts=None, timeout_ms=None, log=None):
        self.walks.append(tile)
        if self.walk_ok:
            self.at = tile
        return self.walk_ok
        yield

    def fight(self, plan, log):
        self.plans.append(plan)
        return self.fight_ok
        yield


def walks_up():
    hills = Trolls(TILE.DENULTH)
    expect(run_wait(troll.walk_to(TILE.DENULTH, 2, hills.log))).to_be(True)
    expect(len(hills.walks)).to_be(0)
    hills.at = STRONGHOLD
    expect(run_wait(troll.walk_to_stronghold(TILE.GENERAL, 5, hills.log))).to_be(True)
    hills.at = BURTHORPE
    hills.walk_ok = False
    expect(run_wait(troll.walk_to_stronghold(TILE.GENERAL, 5, hills.log))).to_be(False)
    hills.walk_ok = True
    guarded = []

    def guard(kind, threat, walk, log):
        guarded.append([kind, threat()])
        moved = yield from walk()
        return moved
    spy_on(troll, 'protected_walk', impl=guard)
    hills.npcs = [Fake(name='Thrower Troll', distance=lambda: 4)]
    hills.at = MOUNTAIN
    expect(run_wait(troll.walk_to_stronghold(TILE.GENERAL, 5, hills.log))).to_be(True)
    expect(guarded).to_equal([['missiles', True]])
    spy_on(troll, 'walk_to_stronghold', impl=lambda tile, radius, log: result(True))
    expect(run_wait(troll.enter_prison(hills.log))).to_be(True)


test('the walk up crosses the troll pass under a missile guard, and needs the cave mouth first', walks_up)


def buys_and_wears_boots():
    hills = Trolls(BURTHORPE)
    hills.pack = [ITEM.CLIMBING_BOOTS]
    expect(run_wait(troll.buy_boots(hills.log))).to_be(True)
    hills.pack = []
    expect(run_wait(troll.buy_boots(hills.log))).to_be(False)
    expect(hills.logged('need 12 coins')).to_be(True)
    hills.pack = [ITEM.COINS] * 20
    hills.walk_ok = False
    expect(run_wait(troll.buy_boots(hills.log))).to_be(False)
    hills.walk_ok = True

    def sells(npc, rules, prefer, log):
        hills.pack.append(ITEM.CLIMBING_BOOTS)
        return False
        yield
    spy_on(troll, 'talk_choosing_by', impl=sells)
    expect(run_wait(troll.buy_boots(hills.log))).to_be(True)

    put_on = []

    def equips(name):
        put_on.append(name)
        return name != 'Rune platebody'
        yield
    spy_on(equipment, 'equip', impl=equips)
    hills.worn = ['Rune full helm']
    step = troll.wear_all(['Rune full helm', 'Rune scimitar', 'Rune platebody'])
    expect(run_wait(step.run(hills.log))).to_be(True)
    expect(put_on).to_equal(['Rune scimitar', 'Rune platebody'])
    expect(hills.logged('cannot wear Rune platebody')).to_be(True)
    troll.unwearable.add(ITEM.CLIMBING_BOOTS.lower())
    expect(troll.wear_boots().kind).to_be('wait')
    troll.unwearable.clear()
    expect(troll.wear_boots().kind).to_be('custom')


test("Tenzing's boots are bought for 12gp, and a piece the server won't let on is shed", buys_and_wears_boots)


def fights_dad():
    hills = Trolls(BURTHORPE)
    hills.walk_ok = False
    expect(run_wait(troll.fight_dad(hills.log))).to_be(False)
    hills.walk_ok = True
    dad = Fake(name='Dad')
    spy_on(troll, 'attackable', impl=lambda name, within: dad)
    spy_on(game, 'in_combat', returns=False)
    expect(run_wait(troll.fight_dad(hills.log))).to_be(True)
    plan = hills.plans[-1]
    expect(plan.target()).to_be(dad)
    expect(plan.won()).to_be(False)
    spy_on(troll, 'attackable', impl=lambda name, within: None)
    expect(plan.won()).to_be(True)
    plan.on_dialogue("I'll be going now.")
    expect(plan.won()).to_be(True)
    hills.locs = [Fake(name='Arena Exit', actions=lambda: ['Open'], distance=lambda: 1, interact=lambda op: True)]
    expect(run_wait(plan.on_missing())).to_be(True)
    expect(hills.logged('Dad is not in the arena')).to_be(True)
    hills.walk_ok = False
    hills.at = TILE.DAD
    expect(run_wait(plan.on_missing())).to_be(False)


test('Dad is fought until he forfeits, and poked back into the arena when he leaves it', fights_dad)


def hunts_the_general():
    hills = Trolls(STRONGHOLD)
    hills.pack = [ITEM.PRISON_KEY]
    expect(run_wait(troll.take_ground(ITEM.PRISON_KEY, hills.log))).to_be(True)
    expect(run_wait(troll.hunt_general(hills.log))).to_be(True)
    hills.pack = []
    expect(run_wait(troll.take_ground(ITEM.PRISON_KEY, hills.log))).to_be(False)
    hills.ground = [Fake(name=ITEM.PRISON_KEY, distance=lambda: 1, interact=lambda op: False)]
    expect(run_wait(troll.take_ground(ITEM.PRISON_KEY, hills.log))).to_be(False)

    def takes(op):
        hills.ground = []
        hills.pack.append(ITEM.PRISON_KEY)
        return True
    hills.ground = [Fake(name=ITEM.PRISON_KEY, distance=lambda: 1, interact=takes)]
    expect(run_wait(troll.hunt_general(hills.log))).to_be(True)

    hills.pack = []
    spy_on(troll, 'walk_to_stronghold', impl=lambda tile, radius, log: result(False))
    expect(run_wait(troll.hunt_general(hills.log))).to_be(False)
    spy_on(troll, 'walk_to_stronghold', impl=lambda tile, radius, log: result(True))
    hills.fight_ok = False
    expect(run_wait(troll.hunt_general(hills.log))).to_be(False)
    plan = hills.plans[-1]
    expect(plan.won()).to_be(False)
    expect(plan.target()).to_be(None)
    expect(run_wait(plan.on_missing())).to_be(True)
    hills.fight_ok = True

    def drops(plan, log):
        hills.plans.append(plan)
        hills.ground = [Fake(name=ITEM.PRISON_KEY, distance=lambda: 1, interact=takes)]
        return True
        yield
    spy_on(troll, 'fight', impl=drops)
    expect(run_wait(troll.hunt_general(hills.log))).to_be(True)


test("a Troll General is killed for the prison key, which is taken off the floor", hunts_the_general)


def steals_cell_keys():
    hills = Trolls(TILE.EADGAR_CELL)
    hills.pack = [ITEM.CELL_KEY_2]
    expect(run_wait(troll.steal_cell_key('Berry', ITEM.CELL_KEY_2, TILE.EADGAR_CELL, hills.log))).to_be(True)
    hills.pack = []
    hills.walk_ok = False
    expect(run_wait(troll.steal_cell_key('Berry', ITEM.CELL_KEY_2, TILE.EADGAR_CELL, hills.log))).to_be(False)
    hills.walk_ok = True
    spy_on(skills, 'effective', returns=30)

    def lifts(op):
        hills.pack.append(ITEM.CELL_KEY_2)
        return True
    hills.npcs = [Fake(name='Berry', actions=lambda: ['Pickpocket'], distance=lambda: 1, interact=lifts)]
    expect(run_wait(troll.steal_cell_key('Berry', ITEM.CELL_KEY_2, TILE.EADGAR_CELL, hills.log))).to_be(True)
    expect(hills.logged('pickpocketed Berry')).to_be(True)

    hills.pack = []
    spy_on(skills, 'effective', returns=10)
    woken = Fake(name='Berry', actions=lambda: ['Attack'], distance=lambda: 1, interact=lambda op: True)
    hills.npcs = [woken]
    state = {'fights': 0}

    def attackable(name, within):
        return woken if state['fights'] < 2 else None

    def kills(plan, log):
        expect(plan.target()).to_be(woken)
        expect(plan.won()).to_be(False)
        state['fights'] += 1
        if state['fights'] == 2:
            hills.pack.append(ITEM.CELL_KEY_2)
        return True
        yield
    spy_on(troll, 'attackable', impl=attackable)
    spy_on(troll, 'fight', impl=kills)
    expect(run_wait(troll.steal_cell_key('Berry', ITEM.CELL_KEY_2, TILE.EADGAR_CELL, hills.log))).to_be(True)

    hills.pack = []
    hills.npcs = [Fake(name='Berry', actions=lambda: ['Pickpocket'], distance=lambda: 1, interact=lambda op: False)]
    spy_on(skills, 'effective', returns=30)
    expect(run_wait(troll.steal_cell_key('Berry', ITEM.CELL_KEY_2, TILE.EADGAR_CELL, hills.log))).to_be(False)
    expect(hills.logged('could not get Cell key 2 from Berry')).to_be(True)


test('a cell key is pickpocketed off its sleeping guard, or taken off him once woken and killed', steals_cell_keys)


def frees_the_prisoners():
    hills = Trolls(TILE.GODRIC_CELL)
    hills.walk_ok = False
    expect(run_wait(troll.unlock_cell(ITEM.CELL_KEY_1, troll.GODRIC_DOOR, TILE.GODRIC_CELL, hills.log))).to_be(False)
    hills.walk_ok = True
    expect(run_wait(troll.unlock_cell(ITEM.CELL_KEY_1, troll.GODRIC_DOOR, TILE.GODRIC_CELL, hills.log))).to_be(False)
    expect(hills.logged('no Cell Door to Unlock')).to_be(True)
    door = troll.GODRIC_DOOR
    hills.locs = [Fake(name='Cell Door', actions=lambda: ['Unlock'], distance=lambda: 1, tile=lambda: door, interact=lambda op: False)]
    expect(run_wait(troll.unlock_cell(ITEM.CELL_KEY_1, troll.GODRIC_DOOR, TILE.GODRIC_CELL, hills.log))).to_be(False)
    hills.pack = [ITEM.CELL_KEY_1]

    def unlocks(op):
        hills.pack = []
        return True
    hills.locs = [Fake(name='Cell Door', actions=lambda: ['Unlock'], distance=lambda: 1, tile=lambda: door, interact=unlocks)]
    expect(run_wait(troll.unlock_cell(ITEM.CELL_KEY_1, troll.GODRIC_DOOR, TILE.GODRIC_CELL, hills.log))).to_be(True)

    spy_on(troll, 'walk_to_stronghold', impl=lambda tile, radius, log: result(False))
    expect(run_wait(troll.free_prisoners(False, hills.log))).to_be(False)
    spy_on(troll, 'walk_to_stronghold', impl=lambda tile, radius, log: result(True))
    spy_on(troll, 'steal_cell_key', impl=lambda guard, key, stand, log: result(guard == 'Twig'))
    spy_on(troll, 'unlock_cell', impl=lambda key, door, stand, log: result(True))
    expect(run_wait(troll.free_prisoners(False, hills.log))).to_be(True)
    expect(hills.logged('could not free Mad Eadgar')).to_be(True)
    spy_on(troll, 'steal_cell_key', impl=lambda guard, key, stand, log: result(True))
    spy_on(troll, 'unlock_cell', impl=lambda key, door, stand, log: result(key == ITEM.CELL_KEY_1))
    expect(run_wait(troll.free_prisoners(False, hills.log))).to_be(True)
    expect(hills.logged("could not open Mad Eadgar's cell")).to_be(True)
    spy_on(troll, 'steal_cell_key', impl=lambda guard, key, stand, log: result(False))
    expect(run_wait(troll.free_prisoners(True, hills.log))).to_be(False)


test('Mad Eadgar is freed before Godric where the key allows, and Godric whatever happens to him', frees_the_prisoners)


def decides_and_warns():
    hills = Trolls(BURTHORPE)
    spy_on(quests, 'status', returns='in_progress')
    snap = QuestSnapshot(journal='not_started', stage=TROLL_STAGE.NOT_STARTED, progress=QuestProgress(TROLL_STAGE.NOT_STARTED, set()),
                         bank_known=True, bank={}, tile=BURTHORPE)
    expect(troll.decide(snap).reason).to_contain('Death Plateau must be complete')
    snap = QuestSnapshot(journal='in_progress', stage=TROLL_STAGE.ENTERED_PRISON, progress=QuestProgress(TROLL_STAGE.ENTERED_PRISON, set()),
                         inv={'climbing boots': 1, 'lobster': 8}, worn=set(['climbing boots', 'rune scimitar']), bank_known=True, bank={},
                         tile=STRONGHOLD)
    step = troll.decide(snap)
    expect(step.kind).to_be('custom')
    spy_on(troll, 'free_prisoners', impl=lambda freed, log: result(freed))
    expect(run_wait(step.run(hills.log))).to_be(False)
    expect(troll.decide(snap.with_fields({'stage': None, 'progress': None})).kind).to_be('wait')
    expect(troll.decide(snap.with_fields({'stage': 99, 'progress': QuestProgress(99, set())})).kind).to_be('done')
    expect(troll.decide(snap.with_fields({'stage': 35, 'progress': QuestProgress(35, set())})).kind).to_be('wait')

    spy_on(skills, 'level', returns=1)
    expect(troll.warn_troll_stronghold_readiness()).to_contain('Agility 15')
    spy_on(skills, 'level', returns=99)
    expect(troll.warn_troll_stronghold_readiness()).to_be(None)


test("decide waits on Death Plateau and an unreadable stage, and the readiness warning names what's short", decides_and_warns)


class Journal:
    """The quest list and journal as a reader sees them: one quest's status, its journal lines, and the modal."""

    def __init__(self, status, lines):
        self.status = status
        self.lines = lines
        self.main = -1
        self.closed = 0
        spy_on(quests, 'status', impl=lambda name: self.status)
        spy_on(quests, 'journal', impl=self.journal)
        spy_on(reader, 'modals', impl=lambda: Record({'main': self.main, 'chat': -1, 'side': -1}))
        spy_on(_core, 'close_interfaces', impl=self.close)
        patch(execution, 'delay_ticks', instant_ticks)

    def journal(self, name):
        self.main = 275
        return self.lines
        yield

    def close(self):
        self.closed += 1
        self.main = -1


def reads_each_journal():
    for reader_, complete, not_started, line, stage in [
        [read_plague_progress, PC_STAGE.COMPLETE, PC_STAGE.NOT_STARTED, "I've spoken to Jethick", PC_STAGE.SHOWN_PICTURE],
        [read_biohazard_progress, BIO_STAGE.COMPLETE, BIO_STAGE.NOT_STARTED, "I've crossed the wall into West Ardougne", BIO_STAGE.CLIMBED_LADDER],
        [read_death_plateau_progress, DP_STAGE.COMPLETE, DP_STAGE.NOT_STARTED, 'I bought the guard a drink', DP_STAGE.GIVEN_ALE],
        [read_troll_stronghold_progress, TROLL_STAGE.COMPLETE, TROLL_STAGE.NOT_STARTED, 'I defeated the troll champion', TROLL_STAGE.DEFEATED_DAD],
    ]:
        page = Journal('complete', [])
        expect(run_wait(reader_()).stage).to_be(complete)
        page.status = 'not_started'
        expect(run_wait(reader_()).stage).to_be(not_started)
        page.status = 'unknown'
        expect(run_wait(reader_())).to_be(None)
        if line is not None:
            page.status = 'in_progress'
            page.lines = [line]
            expect(run_wait(reader_()).stage).to_be(stage)
            expect(page.closed).to_be(1)


test("each quest's journal reader takes the tab's status first and reads the journal only when it's in progress", reads_each_journal)


def reads_eadgars_journal_and_the_freed_flag():
    eadgar_journal.freed_cache = None
    page = Journal('complete', [])
    expect(run_wait(read_eadgar_progress()).stage).to_be(EADGAR_STAGE.COMPLETE)
    page.status = 'unknown'
    expect(run_wait(read_eadgar_progress())).to_be(None)
    page.status = 'not_started'
    expect(run_wait(eadgar_journal.troll_freed_eadgar())).to_be(False)
    statuses = {"Eadgar's Ruse": 'not_started', 'Troll Stronghold': 'complete'}
    spy_on(quests, 'status', impl=lambda name: statuses[name])
    page.lines = ["I've rescued Godric and Mad Eadgar."]
    progress = run_wait(read_eadgar_progress())
    expect(progress.stage).to_be(EADGAR_STAGE.NOT_STARTED)
    expect(EADGAR_FLAG.EADGAR_FREED in progress.flags).to_be(True)
    expect(eadgar_journal.freed_cache).to_be(True)

    statuses["Eadgar's Ruse"] = 'in_progress'
    page.lines = ['Mad Eadgar has a plan']
    progress = run_wait(read_eadgar_progress())
    expect(progress.stage).to_be(EADGAR_STAGE.NEEDS_PARROT)
    expect(EADGAR_FLAG.EADGAR_FREED in progress.flags).to_be(True)
    page.lines = ['nothing the journal says']
    expect(run_wait(read_eadgar_progress())).to_be(None)

    eadgar_journal.freed_cache = None
    eadgar_journal.mark_eadgar_freed()
    expect(run_wait(eadgar_journal.troll_freed_eadgar())).to_be(True)
    eadgar_journal.freed_cache = None


test("Eadgar's journal carries Troll Stronghold's freed-Eadgar line, read once and cached", reads_eadgars_journal_and_the_freed_flag)
