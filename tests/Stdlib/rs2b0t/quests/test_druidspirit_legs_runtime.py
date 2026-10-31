"""Nature Spirit's legs against spied facades: Filliman's camp, the mirror and the journal, the bloom scroll and the
ritual stones, the grotto, the sickle at the furnace, the ghasts, and the journal reader, each through its success
and its failures."""

import _core
import rs2004.quests.defs.druidspirit as druidspirit
import rs2004.quests.defs.druidspirit.camp as camp
import rs2004.quests.defs.druidspirit.ghasts as ghasts
import rs2004.quests.defs.druidspirit.grotto as grotto
import rs2004.quests.defs.druidspirit.journal as journal
import rs2004.quests.defs.druidspirit.supplies as supplies
from rs2004 import execution
from rs2004.dialogue import chat_dialog
from rs2004.entities import ground_items, locs, npcs
from rs2004.game import game, reader, skills
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.quests.defs.druidspirit.areas import FILLIMAN, NATURE_SPIRIT, NS_ID, NS_LOC, NS_NAME, NS_STAGE, NS_TILE
from rs2004.quests.defs.druidspirit.journal import NS_FLAG
from rs2004.quests.engine.types import QuestProgress, QuestSnapshot
from rs2004.tabs import quests
from rs2004.traversal import traversal

GROTTO = Tile(3442, 9734, 0)
SWAMP = Tile(3430, 3340, 0)
LUMBRIDGE = Tile(3222, 3218, 0)


def result(value):
    return value
    yield


class Swamp:
    """The player about Mort Myre, with the pack, the scene, the prayer bar and an open chat."""

    def __init__(self, at):
        self.at = at
        self.pack = []
        self.locs = []
        self.ground = []
        self.npcs = []
        self.walk_ok = True
        self.walks = []
        self.lines = []
        self.prayer = [40, 40]
        self.fighting = False
        spy_on(game, 'tile', impl=lambda: self.at)
        spy_on(game, 'in_combat', impl=lambda: self.fighting)
        spy_on(skills, 'level', impl=lambda name: self.prayer[0])
        spy_on(skills, 'effective', impl=lambda name: self.prayer[1])
        spy_on(locs, 'query', impl=querying(lambda: self.locs))
        spy_on(ground_items, 'query', impl=querying(lambda: self.ground))
        spy_on(npcs, 'query', impl=querying(lambda: self.npcs))
        spy_on(npcs, 'all', impl=lambda: self.npcs)
        spy_on(inventory, 'items', impl=lambda: self.pack)
        spy_on(inventory, 'used', impl=lambda: len(self.pack))
        spy_on(inventory, 'count_by_id', impl=lambda id: sum([i.count for i in self.pack if i.id == id]))
        spy_on(traversal, 'walk_resilient', impl=self.walk)
        for module in [camp, ghasts, grotto, supplies]:
            spy_on(module, 'settle_scene', impl=instant_ticks)
        patch(execution, 'delay_until', instant_until)
        patch(execution, 'delay_ticks', instant_ticks)
        self.chat = FakeChat().install(chat_dialog)

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

    def hold(self, id, count=1, use_on=None, interact=None):
        held = Fake(id=id, count=count, use_on=use_on if use_on is not None else (lambda other: True),
                    interact=interact if interact is not None else (lambda op: True))
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

    def gives(self, id):
        return lambda op: self.hold(id) is not None

    def loc(self, name, actions, tile=None, interact=None):
        made = Fake(name=name, actions=lambda: actions, distance=lambda: 1, tile=lambda: tile if tile is not None else self.at,
                    interact=interact if interact is not None else (lambda op: True))
        self.locs.append(made)
        return made

    def npc(self, name, actions=None, index=1):
        made = Fake(name=name, index=index, actions=lambda: actions if actions is not None else ['Talk-to'], distance=lambda: 1,
                    interact=lambda op: True)
        self.npcs.append(made)
        return made


def drives_one_topic():
    swamp = Swamp(NS_TILE.CAMP)
    swamp.chat.pages = ['continue', ['How can I help?', 'Ok, thanks.'], 'continue', ['How can I help?', 'Ok, thanks.']]
    expect(run_wait(camp.drive_once('How can I help?', swamp.log))).to_be(True)
    expect(swamp.chat.chosen).to_equal(['How can I help?', 'Ok, thanks.'])
    swamp.chat.pages = [['Something else']]
    expect(run_wait(camp.drive_once('How can I help?', swamp.log))).to_be(False)
    expect(swamp.logged("no 'How can I help?' and no goodbye")).to_be(True)
    # A dialogue that never closes runs out its 40 passes.
    spy_on(chat_dialog, 'is_open', returns=True)
    spy_on(chat_dialog, 'can_continue', returns=False)
    spy_on(chat_dialog, 'options', returns=[])
    expect(run_wait(camp.drive_once('How can I help?', swamp.log))).to_be(False)


test("Filliman's topic is taken once and then the goodbye, since every topic re-offers the same list", drives_one_topic)


def summons_filliman():
    swamp = Swamp(LUMBRIDGE)
    swamp.walk_ok = False
    expect(run_wait(camp.talk_filliman(None, swamp.log))).to_be(False)
    swamp.walk_ok = True
    expect(run_wait(camp.talk_filliman(None, swamp.log))).to_be(False)
    expect(swamp.logged('no grotto door at the camp')).to_be(True)
    door = swamp.loc(NS_LOC.GROTTO_DOOR, ['Enter'], interact=lambda op: False)
    expect(run_wait(camp.talk_filliman(None, swamp.log))).to_be(False)

    def knock(op):
        swamp.npc(FILLIMAN.npc)
        return True
    door._fields['interact'] = knock
    spy_on(camp, 'drive_dialog', impl=lambda prefer, log: result(True))
    expect(run_wait(camp.talk_filliman(None, swamp.log))).to_be(True)
    spy_on(camp, 'open_dialogue', impl=lambda name, log: result(False))
    expect(run_wait(camp.talk_filliman('How can I help?', swamp.log))).to_be(False)
    spy_on(camp, 'open_dialogue', impl=lambda name, log: result(True))
    spy_on(camp, 'drive_once', impl=lambda topic, log: result(topic == 'How can I help?'))
    expect(run_wait(camp.talk_filliman('How can I help?', swamp.log))).to_be(True)

    expect(run_wait(camp.ensure_spirit(swamp.log))).to_be(True)
    swamp.npcs = []
    spy_on(camp, 'talk_filliman', impl=lambda topic, log: result(False))
    expect(run_wait(camp.ensure_spirit(swamp.log))).to_be(False)
    spy_on(camp, 'talk_filliman', impl=lambda topic, log: result(True))
    expect(run_wait(camp.ensure_spirit(swamp.log))).to_be(False)


test('an empty camp knocks on the grotto door to summon the spirit, and a present one is talked to', summons_filliman)


def shows_the_mirror():
    swamp = Swamp(NS_TILE.CAMP)
    swamp.walk_ok = False
    expect(run_wait(camp.mirror_leg(swamp.log))).to_be(False)
    swamp.walk_ok = True
    expect(run_wait(camp.mirror_leg(swamp.log))).to_be(False)
    expect(swamp.logged('the mirror is already taken')).to_be(True)
    bowl = Fake(name=NS_NAME.BOWL, distance=lambda: 1, interact=lambda op: False)
    swamp.ground = [bowl]
    expect(run_wait(camp.mirror_leg(swamp.log))).to_be(False)

    def uncover(op):
        swamp.ground = [Fake(name=NS_NAME.MIRROR, distance=lambda: 1, interact=swamp.swaps(0, NS_ID.MIRROR))]
        return True
    bowl._fields['interact'] = uncover
    expect(run_wait(camp.mirror_leg(swamp.log))).to_be(True)
    expect(run_wait(camp.mirror_leg(swamp.log))).to_be(True)
    expect(len([i for i in swamp.pack if i.id == NS_ID.MIRROR])).to_be(1)

    spy_on(camp, 'ensure_spirit', impl=lambda log: result(False))
    expect(run_wait(camp.mirror_leg(swamp.log))).to_be(False)
    spy_on(camp, 'ensure_spirit', impl=lambda log: result(True))
    expect(run_wait(camp.mirror_leg(swamp.log))).to_be(False)
    swamp.npc(FILLIMAN.npc)
    swamp.pack[0]._fields['use_on'] = lambda other: False
    expect(run_wait(camp.mirror_leg(swamp.log))).to_be(False)
    swamp.pack[0]._fields['use_on'] = lambda other: True
    spy_on(camp, 'drive_dialog', impl=lambda prefer, log: result(True))
    expect(run_wait(camp.mirror_leg(swamp.log))).to_be(True)


test('the washing bowl uncovers the mirror, which is taken and then shown to the spirit', shows_the_mirror)


def hands_over_the_journal():
    swamp = Swamp(NS_TILE.CAMP)
    searched = []

    def search(step, log):
        searched.append(step.name)
        swamp.hold(NS_ID.JOURNAL)
        return True
        yield
    spy_on(camp, 'prompt_loc', impl=search)
    expect(run_wait(camp.journal_leg(swamp.log))).to_be(True)
    expect(searched).to_equal([NS_LOC.GROTTO_TREE])
    spy_on(camp, 'ensure_spirit', impl=lambda log: result(False))
    expect(run_wait(camp.journal_leg(swamp.log))).to_be(False)
    spy_on(camp, 'ensure_spirit', impl=lambda log: result(True))
    expect(run_wait(camp.journal_leg(swamp.log))).to_be(False)
    swamp.npc(FILLIMAN.npc)
    swamp.pack[0]._fields['use_on'] = lambda other: False
    expect(run_wait(camp.journal_leg(swamp.log))).to_be(False)
    swamp.pack[0]._fields['use_on'] = lambda other: True

    def given(expect_fn, prefer, log, ms=30000):
        swamp.drop(NS_ID.JOURNAL)
        return expect_fn()
        yield
    spy_on(camp, 'drive_until', impl=given)
    expect(run_wait(camp.journal_leg(swamp.log))).to_be(True)

    spy_on(camp, 'talk_filliman', impl=lambda topic, log: result(False))
    expect(run_wait(camp.ask_to_help(swamp.log))).to_be(False)

    def hands_scroll(topic, log):
        swamp.hold(NS_ID.SPELL)
        return True
        yield
    spy_on(camp, 'talk_filliman', impl=hands_scroll)
    expect(run_wait(camp.ask_to_help(swamp.log))).to_be(True)


test("Tarlock's journal is searched out of the grotto tree and handed over, then the bloom scroll asked for", hands_over_the_journal)


def stands_beside_a_log():
    swamp = Swamp(LUMBRIDGE)
    swamp.walk_ok = False
    expect(run_wait(camp.stand_beside(swamp.log))).to_be(False)
    swamp.walk_ok = True
    swamp.at = SWAMP
    expect(run_wait(camp.stand_beside(swamp.log))).to_be(False)
    expect(swamp.logged('nothing bloomable within 40 tiles')).to_be(True)
    swamp.loc(NS_LOC.LOG, [], tile=SWAMP.translate(1, 0))
    expect(run_wait(camp.stand_beside(swamp.log))).to_be(True)
    swamp.locs = []
    swamp.loc(NS_LOC.LOG, [], tile=SWAMP.translate(5, 5))
    expect(run_wait(camp.stand_beside(swamp.log, [NS_LOC.LOG]))).to_be(True)
    expect(swamp.walks[-1]).to_equal(SWAMP.translate(6, 5))
    swamp.at = SWAMP
    swamp.walk_ok = False
    expect(run_wait(camp.stand_beside(swamp.log))).to_be(False)
    spy_on(game, 'tile', returns=None)
    swamp.walk_ok = True
    expect(run_wait(camp.stand_beside(swamp.log))).to_be(False)


test('the bloom is cast from beside a bloomable, never on it, walking round it until one side is reached', stands_beside_a_log)


def blooms_the_fungus():
    swamp = Swamp(SWAMP)
    expect(camp.pickable()).to_be(None)
    swamp.hold(NS_ID.FUNGI)
    expect(run_wait(camp.bloom_with_scroll(swamp.log))).to_be(True)
    swamp.pack = []
    spy_on(camp, 'stand_beside', impl=lambda log, names=None: result(False))
    expect(run_wait(camp.bloom_with_scroll(swamp.log))).to_be(False)
    spy_on(camp, 'stand_beside', impl=lambda log, names=None: result(True))
    expect(run_wait(camp.bloom_with_scroll(swamp.log))).to_be(False)
    expect(swamp.logged('no Druidic spell held')).to_be(True)
    scroll = swamp.hold(NS_ID.SPELL, interact=lambda op: False)
    expect(run_wait(camp.bloom_with_scroll(swamp.log))).to_be(False)

    def cast(op):
        swamp.loc(NS_LOC.FUNGI_LOG, ['Pick'], interact=swamp.gives(NS_ID.FUNGI))
        return True
    scroll._fields['interact'] = cast
    expect(run_wait(camp.bloom_with_scroll(swamp.log))).to_be(True)
    expect(camp.pickable().op).to_be('Pick')

    swamp.locs = []
    expect(run_wait(camp.pick_harvest(swamp.log))).to_be(False)
    expect(swamp.logged('nothing bloomed within reach')).to_be(True)
    swamp.loc(NS_LOC.PEAR_BUSH, ['Pick'], interact=lambda op: False)
    expect(run_wait(camp.pick_harvest(swamp.log))).to_be(False)


test('the paper scroll blooms a rotting log and the fungus is picked before the log reverts', blooms_the_fungus)


def feeds_the_stones():
    swamp = Swamp(NS_TILE.CAMP)
    expect(run_wait(camp.feed_stones(set(), swamp.log))).to_be(False)
    expect(swamp.logged('no Mort myre fungi held')).to_be(True)
    swamp.hold(NS_ID.FUNGI)
    swamp.walk_ok = False
    expect(run_wait(camp.feed_stones(set(), swamp.log))).to_be(False)
    swamp.walk_ok = True
    expect(run_wait(camp.feed_stones(set(), swamp.log))).to_be(False)
    expect(swamp.logged('no stone at (3439,3336)')).to_be(True)
    swamp.loc(NS_LOC.STONE, [], tile=NS_TILE.NATURE_STONE)
    swamp.loc(NS_LOC.STONE, [], tile=NS_TILE.SPIRIT_STONE)
    swamp.pack[0]._fields['use_on'] = lambda other: False
    expect(run_wait(camp.feed_stones(set(), swamp.log))).to_be(False)
    swamp.pack[0]._fields['use_on'] = lambda other: True

    def absorbed(expect_fn, prefer, log, ms=30000):
        swamp.pack = []
        return expect_fn()
        yield
    spy_on(camp, 'drive_until', impl=absorbed)
    expect(run_wait(camp.feed_stones(set(), swamp.log))).to_be(True)
    expect(run_wait(camp.use_on_stone(NS_ID.FUNGI, NS_TILE.NATURE_STONE, lambda: True, swamp.log))).to_be(True)

    nature = set([NS_FLAG.NATURE])
    expect(run_wait(camp.feed_stones(nature, swamp.log))).to_be(False)
    expect(swamp.logged('no bloom scroll held')).to_be(True)
    swamp.hold(NS_ID.SPELL_USED)
    expect(run_wait(camp.feed_stones(nature, swamp.log))).to_be(True)
    swamp.hold(NS_ID.SPELL)
    expect(run_wait(camp.feed_stones(nature, swamp.log))).to_be(True)


test('the fungus feeds the nature stone and the spent scroll the spirit stone, each addressed by its tile', feeds_the_stones)


def solves_on_the_faith_stone():
    swamp = Swamp(NS_TILE.CAMP)
    spy_on(camp, 'ensure_spirit', impl=lambda log: result(False))
    expect(run_wait(camp.solve_puzzle(swamp.log))).to_be(False)
    spy_on(camp, 'ensure_spirit', impl=lambda log: result(True))
    swamp.walk_ok = False
    expect(run_wait(camp.solve_puzzle(swamp.log))).to_be(False)
    expect(swamp.logged('could not reach the faith stone')).to_be(True)
    spy_on(traversal, 'walk_resilient', impl=lambda tile, radius=2, attempts=None, timeout_ms=None, log=None: result(True))
    expect(run_wait(camp.solve_puzzle(swamp.log))).to_be(False)
    expect(swamp.logged('rather than on the faith stone')).to_be(True)
    swamp.at = NS_TILE.FAITH_STONE
    expect(run_wait(camp.solve_puzzle(swamp.log))).to_be(False)
    expect(swamp.logged('the spirit despawned')).to_be(True)
    swamp.npc(FILLIMAN.npc)
    spy_on(camp, 'open_dialogue', impl=lambda name, log: result(False))
    expect(run_wait(camp.solve_puzzle(swamp.log))).to_be(False)

    def walked_off(name, log):
        swamp.at = NS_TILE.CAMP
        return True
        yield
    spy_on(camp, 'open_dialogue', impl=walked_off)
    expect(run_wait(camp.solve_puzzle(swamp.log))).to_be(False)
    expect(swamp.logged('off the faith stone')).to_be(True)
    swamp.at = NS_TILE.FAITH_STONE
    spy_on(camp, 'open_dialogue', impl=lambda name, log: result(True))
    spy_on(camp, 'drive_once', impl=lambda topic, log: result(topic == "I think I've solved the puzzle!"))
    expect(run_wait(camp.solve_puzzle(swamp.log))).to_be(True)


test('the puzzle is answered standing on the faith stone, and a talk that moved the player off it is abandoned', solves_on_the_faith_stone)


def blooms_with_the_sickle():
    swamp = Swamp(SWAMP)
    swamp.prayer = [40, 0]
    expect(run_wait(ghasts.bloom_with_sickle(swamp.log))).to_be(False)
    expect(swamp.logged('no prayer points left')).to_be(True)
    swamp.prayer = [40, 40]
    spy_on(ghasts, 'stand_beside', impl=lambda log, names=None: result(False))
    expect(run_wait(ghasts.bloom_with_sickle(swamp.log))).to_be(False)
    spy_on(ghasts, 'stand_beside', impl=lambda log, names=None: result(True))
    expect(run_wait(ghasts.bloom_with_sickle(swamp.log))).to_be(False)
    expect(swamp.logged('no Silver sickle(b) held')).to_be(True)
    sickle = swamp.hold(NS_ID.SICKLE_BLESSED, interact=lambda op: False)
    expect(run_wait(ghasts.bloom_with_sickle(swamp.log))).to_be(False)

    def bloom(op):
        swamp.locs = []
        swamp.loc(NS_LOC.BUDDING_BRANCH, ['Take-cutting'], interact=swamp.gives(NS_ID.STEM))
        return True
    sickle._fields['interact'] = bloom
    expect(run_wait(ghasts.bloom_with_sickle(swamp.log))).to_be(True)
    expect(ghasts.harvest_held()).to_be(3)


test("the blessed sickle blooms the swamp until three of nature's bounty are held, refusing on an empty prayer bar", blooms_with_the_sickle)


def fills_the_pouch():
    swamp = Swamp(SWAMP)
    expect(run_wait(ghasts.fill_pouch(swamp.log))).to_be(False)
    expect(swamp.logged('only 0 harvest item(s) held')).to_be(True)
    for id in [NS_ID.PEAR, NS_ID.STEM, NS_ID.FUNGI]:
        swamp.hold(id)
    expect(run_wait(ghasts.fill_pouch(swamp.log))).to_be(False)
    expect(swamp.logged('no druid pouch held')).to_be(True)
    pouch = swamp.hold(NS_ID.POUCH_EMPTY, interact=lambda op: False)
    expect(run_wait(ghasts.fill_pouch(swamp.log))).to_be(False)

    def fill(op):
        swamp.drop(NS_ID.POUCH_EMPTY)
        swamp.hold(NS_ID.POUCH, 3)
        return True
    pouch._fields['interact'] = fill
    expect(run_wait(ghasts.fill_pouch(swamp.log))).to_be(True)


test('three harvest items fill the druid pouch', fills_the_pouch)


def pops_a_ghast():
    swamp = Swamp(SWAMP)
    expect(run_wait(ghasts.kill_ghast(swamp.log))).to_be(False)
    expect(swamp.logged('no charged druid pouch')).to_be(True)
    pouch = swamp.hold(NS_ID.POUCH, 3)
    swamp.walk_ok = False
    expect(run_wait(ghasts.kill_ghast(swamp.log))).to_be(False)
    swamp.walk_ok = True
    expect(run_wait(ghasts.kill_ghast(swamp.log))).to_be(False)
    expect(swamp.logged('no ghast in the scene')).to_be(True)
    expect(swamp.walks[-1]).to_equal(NS_TILE.GHAST_HUNT)
    swamp.npc(ghasts.GHAST, [])
    pouch._fields['use_on'] = lambda other: False
    expect(run_wait(ghasts.kill_ghast(swamp.log))).to_be(False)
    pouch._fields['use_on'] = lambda other: True
    expect(run_wait(ghasts.kill_ghast(swamp.log))).to_be(False)
    expect(swamp.logged('did not make a ghast visible')).to_be(True)

    def appear(other):
        swamp.npcs = []
        swamp.npc(ghasts.GHAST, ['Attack'], 7)
        return True
    pouch._fields['use_on'] = appear
    expect(run_wait(ghasts.kill_ghast(swamp.log))).to_be(False)
    swamp.fighting = True
    swamp.npcs[0]._fields['interact'] = lambda op: False
    expect(run_wait(ghasts.kill_ghast(swamp.log))).to_be(False)

    def attack(op):
        swamp.npcs = []
        return True
    swamp.npcs[0]._fields['interact'] = attack
    expect(run_wait(ghasts.kill_ghast(swamp.log))).to_be(True)


test('a pouch charge makes a hidden ghast visible, which is attacked until it leaves the scene', pops_a_ghast)


def enters_and_leaves_the_grotto():
    swamp = Swamp(GROTTO)
    expect(run_wait(grotto.enter_grotto(swamp.log))).to_be(True)
    expect(run_wait(grotto.leave_grotto(swamp.log))).to_be(False)
    expect(swamp.logged('no grotto exit in the scene')).to_be(True)
    exit_door = swamp.loc(NS_LOC.GROTTO_DOOR, ['Exit'], interact=lambda op: False)
    expect(run_wait(grotto.leave_grotto(swamp.log))).to_be(False)

    def out(op):
        swamp.at = NS_TILE.CAMP
        return True
    exit_door._fields['interact'] = out
    expect(run_wait(grotto.exit_after_quest(swamp.log))).to_be(True)
    expect(run_wait(grotto.leave_grotto(swamp.log))).to_be(True)

    swamp.locs = []
    swamp.walk_ok = False
    expect(run_wait(grotto.enter_grotto(swamp.log))).to_be(False)
    swamp.walk_ok = True
    expect(run_wait(grotto.enter_grotto(swamp.log))).to_be(False)
    expect(swamp.logged('no grotto door in the scene')).to_be(True)
    door = swamp.loc(NS_LOC.GROTTO_DOOR, ['Enter'], interact=lambda op: False)
    expect(run_wait(grotto.enter_grotto(swamp.log))).to_be(False)

    def into(op):
        swamp.at = GROTTO
        return True
    door._fields['interact'] = into
    expect(run_wait(grotto.enter_grotto(swamp.log))).to_be(True)


test('the grotto is entered and left by its door, since the walker has no route into the pocket', enters_and_leaves_the_grotto)


def talks_in_the_grotto():
    swamp = Swamp(GROTTO)
    spy_on(grotto, 'enter_grotto', impl=lambda log: result(False))
    expect(run_wait(grotto.talk_in_grotto(['Ok thanks.'], swamp.log))).to_be(False)
    spy_on(grotto, 'enter_grotto', impl=lambda log: result(True))
    expect(run_wait(grotto.talk_in_grotto(['Ok thanks.'], swamp.log))).to_be(False)
    expect(swamp.logged('no grotto pool to search')).to_be(True)
    pool = swamp.loc(NS_LOC.GROTTO_POOL, ['Search'], interact=lambda op: False)
    expect(run_wait(grotto.talk_in_grotto(['Ok thanks.'], swamp.log))).to_be(False)
    pool._fields['interact'] = lambda op: True
    spy_on(grotto, 'drive_dialog', impl=lambda prefer, log: result(True))
    expect(run_wait(grotto.talk_in_grotto(['Ok thanks.'], swamp.log))).to_be(True)
    talked = []

    def talk(name, prefer, log):
        talked.append(name)
        return True
        yield
    spy_on(grotto, 'talk_through', impl=talk)
    swamp.npc(FILLIMAN.npc)
    expect(run_wait(grotto.talk_in_grotto(['Ok thanks.'], swamp.log))).to_be(True)
    swamp.npc(NATURE_SPIRIT.npc)
    expect(run_wait(grotto.talk_in_grotto(['Ok thanks.'], swamp.log))).to_be(True)
    expect(talked).to_equal([FILLIMAN.npc, NATURE_SPIRIT.npc])


test('the spirit is talked to in the grotto, and an empty grotto searches the pool to summon him', talks_in_the_grotto)


def blesses_the_sickle():
    swamp = Swamp(GROTTO)
    swamp.hold(NS_ID.SICKLE_BLESSED)
    expect(run_wait(grotto.bless_sickle(swamp.log))).to_be(True)
    swamp.pack = []
    spy_on(grotto, 'enter_grotto', impl=lambda log: result(False))
    expect(run_wait(grotto.bless_sickle(swamp.log))).to_be(False)
    spy_on(grotto, 'enter_grotto', impl=lambda log: result(True))
    expect(run_wait(grotto.bless_sickle(swamp.log))).to_be(False)
    expect(swamp.logged('no plain sickle to dip')).to_be(True)
    sickle = swamp.hold(NS_ID.SICKLE, use_on=lambda other: False)
    swamp.loc(NS_LOC.GROTTO_POOL, ['Search'])
    expect(run_wait(grotto.bless_sickle(swamp.log))).to_be(False)
    sickle._fields['use_on'] = swamp.swaps(NS_ID.SICKLE, NS_ID.SICKLE_BLESSED)
    spy_on(grotto, 'drive_until', impl=lambda expect_fn, prefer, log, ms=30000: result(expect_fn()))
    expect(run_wait(grotto.bless_sickle(swamp.log))).to_be(True)


test('a plain silver sickle is dipped in the grotto pool to bless it', blesses_the_sickle)


def recharges_prayer():
    swamp = Swamp(GROTTO)
    expect(run_wait(grotto.recharge_prayer(swamp.log))).to_be(True)
    swamp.prayer = [40, 5]
    spy_on(grotto, 'leave_grotto', impl=lambda log: result(False))
    expect(run_wait(grotto.recharge_prayer(swamp.log))).to_be(False)
    spy_on(grotto, 'leave_grotto', impl=lambda log: result(True))
    swamp.walk_ok = False
    expect(run_wait(grotto.recharge_prayer(swamp.log))).to_be(False)
    swamp.walk_ok = True
    expect(run_wait(grotto.recharge_prayer(swamp.log))).to_be(False)
    expect(swamp.logged('to pray at')).to_be(True)
    altar = swamp.loc(NS_LOC.TEMPLE_ALTAR, ['Pray-at'], interact=lambda op: False)
    expect(run_wait(grotto.recharge_prayer(swamp.log))).to_be(False)

    def pray(op):
        swamp.prayer = [40, 40]
        return True
    altar._fields['interact'] = pray
    expect(run_wait(grotto.recharge_prayer(swamp.log))).to_be(True)


test('prayer is recharged at the Paterdomus altar, leaving the grotto first', recharges_prayer)


def casts_at_the_furnace():
    swamp = Swamp(NS_TILE.FURNACE)
    made = []
    spy_on(chat_dialog, 'is_make_menu', returns=True)
    spy_on(chat_dialog, 'make_products', returns=['Silver bar'])

    def make(product, qty):
        made.append(product)
        if product == 'Silver':
            swamp.hold(NS_ID.SILVER_BAR)
        return product != 'Gold'
        yield
    spy_on(chat_dialog, 'make_x', impl=make)
    swamp.walk_ok = False
    expect(run_wait(supplies.smelt_silver(swamp.log))).to_be(False)
    swamp.walk_ok = True
    expect(run_wait(supplies.smelt_silver(swamp.log))).to_be(False)
    expect(swamp.logged('no Furnace in reach')).to_be(True)
    furnace = swamp.loc(NS_LOC.FURNACE, ['Smelt'], interact=lambda op: False)
    expect(run_wait(supplies.smelt_silver(swamp.log))).to_be(False)
    expect(swamp.logged('the Al Kharid furnace did not answer')).to_be(True)
    furnace._fields['interact'] = lambda op: True
    spy_on(chat_dialog, 'is_make_menu', returns=False)
    expect(run_wait(supplies.smelt_silver(swamp.log))).to_be(False)
    expect(swamp.logged('the make menu never opened')).to_be(True)
    spy_on(chat_dialog, 'is_make_menu', returns=True)
    expect(run_wait(supplies.at_furnace(swamp.log, supplies.open_smelt, 'Gold', lambda: False))).to_be(False)
    expect(swamp.logged("no 'Gold' in the menu: [Silver bar]")).to_be(True)
    expect(run_wait(supplies.smelt_silver(swamp.log))).to_be(True)
    expect(run_wait(supplies.smelt_silver(swamp.log))).to_be(True)
    expect(made).to_equal(['Gold', 'Silver'])

    swamp.drop(NS_ID.SILVER_BAR)
    expect(run_wait(supplies.use_bar_on(furnace))).to_be(False)
    swamp.hold(NS_ID.SILVER_BAR, use_on=lambda other: True)

    def cast(product, qty):
        swamp.hold(NS_ID.SICKLE)
        return True
        yield
    spy_on(chat_dialog, 'make_x', impl=cast)
    expect(run_wait(supplies.cast_sickle(swamp.log))).to_be(True)


test('the silver is smelted and the sickle cast at the Al Kharid furnace through its make menu', casts_at_the_furnace)


def sources_the_sickle():
    snap = QuestSnapshot(inv_ids={}, bank_ids={}, bank_known=True, inv={}, bank={}, worn=set(), worn_ids=set())
    step = supplies.sickle_step(snap.with_fields({'inv_ids': {NS_ID.MOULD: 1}, 'bank_ids': {NS_ID.SILVER_ORE: 1}}), 20, 20)
    expect(step.kind).to_be('withdraw')
    expect(step.items[0]['id']).to_be(NS_ID.SILVER_ORE)
    step = supplies.sickle_step(snap.with_fields({'inv_ids': {NS_ID.MOULD: 1, NS_ID.SILVER_ORE: 1}}), 20, 20)
    expect(step.name).to_be('smelt a silver bar')
    step = supplies.sickle_step(snap.with_fields({'inv_ids': {NS_ID.MOULD: 1, NS_ID.SILVER_BAR: 1}}), 20, 20)
    expect(step.name).to_be('cast the silver sickle')
    step = supplies.sickle_step(snap.with_fields({'inv_ids': {NS_ID.MOULD: 1}}), 20, 20)
    expect(step.kind).to_be('buy')
    expect(step.item).to_be('Bronze pickaxe')
    spy_on(skills, 'level', returns=20)
    step = supplies.sickle_step(snap.with_fields({'inv_ids': {NS_ID.MOULD: 1, 1265: 1}}))
    expect(step.kind).to_be('mine_rock')
    expect(supplies.sickle_step(snap.with_fields({'bank_known': False})).kind).to_be('scan_bank')


test("the sickle chain reads the skill levels it isn't given, and buys Bob's pickaxe over a far ground spawn", sources_the_sickle)


def ghast_snap(inv_ids, bank_ids=None, prayer=40, inv=None, bank_known=True):
    return QuestSnapshot(**{
        'journal': 'in_progress',
        'inv': inv if inv is not None else {},
        'inv_ids': inv_ids,
        'worn': set(['rune scimitar', 'rune chainbody', 'rune platelegs', 'rune full helm', 'rune kiteshield']),
        'worn_ids': set([NS_ID.GHOSTSPEAK]),
        'bank': {},
        'bank_ids': bank_ids if bank_ids is not None else {},
        'bank_known': bank_known,
        'stage': NS_STAGE.ADDED_POUCH,
        'progress': QuestProgress(NS_STAGE.ADDED_POUCH, set()),
        'prayer': prayer,
        'tile': SWAMP,
    })


def loops_the_ghasts():
    blessed = {NS_ID.SICKLE_BLESSED: 1}
    expect(druidspirit.decide(ghast_snap({NS_ID.SICKLE: 1})).name).to_be('bless the sickle')
    expect(druidspirit.decide(ghast_snap({}, {NS_ID.SICKLE_BLESSED: 1})).kind).to_be('withdraw')
    expect(druidspirit.decide(ghast_snap(blessed, bank_known=False)).kind).to_be('scan_bank')
    step = druidspirit.decide(ghast_snap(blessed, {NS_ID.POUCH: 7}))
    expect(step.items[0]['qty']).to_be(3)
    step = druidspirit.decide(ghast_snap(blessed, {NS_ID.POUCH_EMPTY: 2}))
    expect(step.items[0]['qty']).to_be(1)
    expect(druidspirit.decide(ghast_snap(blessed)).reason).to_be('no Druid pouch held or banked')
    with_pouch = {NS_ID.SICKLE_BLESSED: 1, NS_ID.POUCH_EMPTY: 1}
    full = {NS_ID.SICKLE_BLESSED: 1, NS_ID.POUCH_EMPTY: 1, NS_ID.PEAR: 1, NS_ID.STEM: 1, NS_ID.FUNGI: 1}
    expect(druidspirit.decide(ghast_snap(full)).name).to_be('fill the druid pouch')
    expect(druidspirit.decide(ghast_snap(with_pouch, prayer=3)).name).to_be('recharge prayer at the Paterdomus altar')
    expect(druidspirit.decide(ghast_snap(with_pouch)).name).to_be('harvest natures bounty')
    grotto_snap = ghast_snap(with_pouch).with_fields({'tile': GROTTO})
    expect(druidspirit.decide(grotto_snap).name).to_be('leave the grotto')


test('past the transformation the ghast loop blesses, draws the pouch, fills it, recharges and blooms in turn', loops_the_ghasts)


def stage_snap(stage, inv_ids=None, flags=None):
    return QuestSnapshot(**{
        'journal': 'in_progress',
        'inv': {},
        'inv_ids': inv_ids if inv_ids is not None else {},
        'worn': set(),
        'worn_ids': set([NS_ID.GHOSTSPEAK]),
        'bank': {},
        'bank_ids': {},
        'bank_known': True,
        'stage': stage,
        'progress': QuestProgress(stage, flags if flags is not None else set()),
        'tile': NS_TILE.CAMP,
    })


def runs_the_stage_closures():
    swamp = Swamp(NS_TILE.CAMP)
    topics = []

    def talk(topic, log):
        topics.append(topic)
        return True
        yield
    spy_on(druidspirit, 'talk_filliman', impl=talk)
    spy_on(druidspirit, 'feed_stones', impl=lambda flags, log: result(NS_FLAG.NATURE in flags))
    prefers = []

    def grotto_talk(prefer, log):
        prefers.append(prefer)
        return True
        yield
    spy_on(druidspirit, 'talk_in_grotto', impl=grotto_talk)
    expect(run_wait(druidspirit.decide(stage_snap(NS_STAGE.STARTED)).run(swamp.log))).to_be(True)
    expect(run_wait(druidspirit.decide(stage_snap(NS_STAGE.BLESSED)).run(swamp.log))).to_be(True)
    expect(topics).to_equal([druidspirit.GHOST_TOPIC, druidspirit.ANOTHER_SCROLL])
    step = druidspirit.decide(stage_snap(NS_STAGE.BLESSED, {NS_ID.SPELL: 1}))
    expect(step.name).to_be('bloom the swamp for a fungus')
    step = druidspirit.decide(stage_snap(NS_STAGE.PICKED_FUNGI, {NS_ID.FUNGI: 1}, set()))
    expect(run_wait(step.run(swamp.log))).to_be(False)
    step = druidspirit.decide(stage_snap(NS_STAGE.SPOKEN_FILLIMAN2, {}, set([NS_FLAG.NATURE])))
    expect(run_wait(step.run(swamp.log))).to_be(True)
    for stage in [NS_STAGE.ENTERED_GROTTO, NS_STAGE.KILLED_GHAST3]:
        expect(run_wait(druidspirit.decide(stage_snap(stage)).run(swamp.log))).to_be(True)
    step = druidspirit.decide(stage_snap(NS_STAGE.FULL_TRANSFORM, {NS_ID.SICKLE: 1}))
    expect(run_wait(step.run(swamp.log))).to_be(True)
    expect(len(prefers)).to_be(3)
    snap = stage_snap(NS_STAGE.FULL_TRANSFORM).with_fields({'bank_ids': {NS_ID.SICKLE: 1}})
    expect(druidspirit.decide(snap).kind).to_be('withdraw')
    expect(druidspirit.decide(stage_snap(NS_STAGE.COMPLETE)).kind).to_be('done')

    kit = druidspirit.decide(ghast_snap({NS_ID.SICKLE_BLESSED: 1, NS_ID.POUCH: 3}, inv={'rune scimitar': 1}).with_fields({'worn': set()}))
    worn = []

    def wear(names, log):
        worn.extend(names)
        return True
        yield
    spy_on(druidspirit, 'wear_kit', impl=wear)
    expect(run_wait(kit.run(swamp.log))).to_be(True)
    expect(worn).to_equal(['Rune scimitar'])


test("each stage's step runs its leg with the topic or the farewell it was given", runs_the_stage_closures)


def reads_the_journal():
    state = {'status': 'in_progress', 'text': 'I need to look for Filliman Tarlock', 'modal': -1, 'closed': 0}
    spy_on(quests, 'status', impl=lambda name: state['status'])

    def page(name):
        return [state['text']]
        yield
    spy_on(quests, 'journal', impl=page)
    spy_on(reader, 'modals', impl=lambda: Fake(main=state['modal']))

    def close():
        state['modal'] = -1
        state['closed'] += 1
        return True
    spy_on(_core, 'close_interfaces', impl=close)
    patch(execution, 'delay_ticks', instant_ticks)
    expect(run_wait(journal.read_druid_progress()).stage).to_be(NS_STAGE.STARTED)
    state['text'] = 'The swamp gate said nothing'
    state['modal'] = 229
    expect(run_wait(journal.read_druid_progress()).stage).to_be(NS_STAGE.STARTED)
    expect(state['closed']).to_be(1)
    state['status'] = 'complete'
    expect(run_wait(journal.read_druid_progress()).flags).to_equal(set([NS_FLAG.NATURE, NS_FLAG.SPIRIT]))
    state['status'] = 'not_started'
    expect(run_wait(journal.read_druid_progress()).stage).to_be(NS_STAGE.NOT_STARTED)
    state['status'] = 'unknown'
    expect(run_wait(journal.read_druid_progress())).to_be(None)


test("the journal reader closes the swamp gate's message box and keeps the last good page through an empty read", reads_the_journal)
