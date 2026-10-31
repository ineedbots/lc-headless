"""Shades of Mort'ton's legs against spied facades: the villagers and their serum, the diary, the herbs and the
vials, Razmire's counters, the Varrock burn, the temple rebuild and the sacred flame, the pyre, the shades, and the
journal reader, each through its success and its failures."""

import _core
import rs2004.quests.defs.mortton as mortton
import rs2004.quests.defs.mortton.journal as journal
import rs2004.quests.defs.mortton.pyre as pyre
import rs2004.quests.defs.mortton.shades as shades
import rs2004.quests.defs.mortton.supplies as supplies
import rs2004.quests.defs.mortton.temple as temple
import rs2004.quests.defs.mortton.town as town
from rs2004 import execution
from rs2004.bank import bank
from rs2004.catalogs.record import Record
from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import chat_dialog, modals
from rs2004.entities import ground_items, locs, npcs
from rs2004.execution import event_signal
from rs2004.game import game, reader, skills
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.quests.defs.mortton.areas import SM_ID, SM_LOC_ID, SM_NPC, SM_NPC_ID, SM_STAGE, SM_TILE, SM_VARP, in_mortton, in_temple_zone, is_temple_wall
from rs2004.quests.defs.mortton.journal import SM_FLAG
from rs2004.quests.engine.types import QuestProgress, QuestSnapshot
from rs2004.quests.food import quest_food
from rs2004.reach import reach
from rs2004.tabs import quests
from rs2004.trade import shop
from rs2004.traversal import traversal

VARROCK = Tile(3212, 3424, 0)
WALL = Tile(3504, 3318, 0)


def result(value):
    return value
    yield


class Legs:
    """Stand-in legs that record their calls, each succeeding unless ok says otherwise."""

    def __init__(self):
        self.calls = []
        self.ok = {}

    def leg(self, name):
        def run(log):
            self.calls.append(name)
            return self.ok.get(name, True)
            yield
        return run

    def shop_at(self, order):
        def go(log):
            self.calls.append(order.op)
            return len(self.calls) < 2
            yield
        return go


class Town:
    """The player about Mort'ton, with the pack, the scene, the temple's meters and whatever box is up."""

    def __init__(self, at):
        self.at = at
        self.pack = []
        self.locs = []
        self.ground = []
        self.npcs = []
        self.walk_ok = True
        self.walks = []
        self.lines = []
        self.hp = [40, 40]
        self.ticks = 0
        self.varps = {SM_VARP.TEMPLE_REPAIRED: 0, SM_VARP.TEMPLE_RESOURCES: 0, SM_VARP.TEMPLE_SANCTITY: 0}
        self.modal = Fake(chat=-1, main=-1)
        self.texts = []
        self.pending = False
        self.fighting = False
        self.animating = False
        spy_on(game, 'tile', impl=lambda: self.at)
        spy_on(game, 'tick', impl=self.tick)
        spy_on(game, 'in_combat', impl=lambda: self.fighting)
        spy_on(game, 'animating', impl=lambda: self.animating)
        spy_on(game, 'set_auto_retaliate', returns=True)
        spy_on(skills, 'level', impl=lambda name: self.hp[0])
        spy_on(skills, 'effective', impl=lambda name: self.hp[1])
        spy_on(reader, 'varp', impl=lambda id: self.varps.get(id, 0))
        spy_on(reader, 'modals', impl=lambda: self.modal)
        spy_on(reader, 'chat_modal_texts', impl=lambda: list(self.texts))
        spy_on(reader, 'main_modal_texts', impl=lambda: list(self.texts))
        spy_on(event_signal, 'pending', impl=lambda: self.pending)
        spy_on(locs, 'query', impl=querying(lambda: self.locs))
        spy_on(ground_items, 'query', impl=querying(lambda: self.ground))
        spy_on(npcs, 'query', impl=querying(lambda: self.npcs))
        spy_on(npcs, 'all', impl=lambda: self.npcs)
        spy_on(inventory, 'items', impl=lambda: self.pack)
        spy_on(inventory, 'free', impl=lambda: 28 - len(self.pack))
        spy_on(inventory, 'count_by_id', impl=self.count)
        spy_on(modals, 'close_if_open', impl=lambda: result(True))
        spy_on(modals, 'close', impl=lambda: result(True))
        spy_on(sustain, 'run', impl=self.eat)
        spy_on(traversal, 'walk_resilient', impl=self.walk)
        for module in [pyre, shades, supplies, temple, town]:
            spy_on(module, 'settle_scene', impl=instant_ticks)
        patch(execution, 'delay_until', instant_until)
        patch(execution, 'delay_ticks', instant_ticks)
        self.chat = FakeChat().install(chat_dialog)

    def tick(self):
        self.ticks += 1
        return self.ticks

    def eat(self):
        self.hp[1] = self.hp[0]
        return True
        yield

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

    def count(self, id):
        return sum([i.count for i in self.pack if i.id == id])

    def hold(self, id, count=1, use_on=None, interact=None):
        held = Fake(id=id, count=count, use_on=use_on if use_on is not None else (lambda other: True),
                    interact=interact if interact is not None else (lambda op: True))
        self.pack.append(held)
        return held

    def drop(self, id):
        self.pack = [held for held in self.pack if held.id != id]

    def gives(self, id, gone=None):
        def give(*args):
            if gone is not None:
                self.drop(gone)
            self.hold(id)
            return True
        return give

    def dose(self, used, label):
        """A serum's use-on that opens the villager's talk."""
        def use(other):
            used.append(label)
            self.chat.pages = ['continue']
            return True
        return use

    def loc(self, id, actions, tile=None, interact=None, name=None):
        made = Fake(id=id, name=name, actions=lambda: actions, distance=lambda: 1, tile=lambda: tile if tile is not None else self.at,
                    interact=interact if interact is not None else (lambda op: True))
        self.locs.append(made)
        return made

    def item(self, id, interact=None):
        made = Fake(id=id, distance=lambda: 1, interact=interact if interact is not None else self.gives(id))
        self.ground.append(made)
        return made

    def npc(self, name, actions=None, id=None, index=1):
        made = Fake(name=name, id=id, index=index, actions=lambda: actions if actions is not None else ['Talk-to'],
                    distance=lambda: 1, targets_another_player=lambda: False, interact=lambda op: True)
        self.npcs.append(made)
        return made


def drives_each_line_once():
    place = Town(SM_TILE.RAZMIRE)
    expect([town.is_ok_option(o) for o in ['Ok, thanks.', 'Ok', 'Okay then.', 'Nothing']]).to_equal([True, True, False, False])
    shadows = 'What are all these shadow creatures?'
    place.chat.pages = ['continue', [shadows, 'Ok, thanks.'], [shadows, 'Ok, thanks.']]
    expect(run_wait(town.drive_once(town.RAZMIRE_START_SCRIPT, place.log))).to_be(True)
    expect(place.chat.chosen).to_equal([shadows, 'Ok, thanks.'])
    place.chat.pages = [['Who are you?']]
    expect(run_wait(town.drive_once([], place.log))).to_be(False)
    expect(place.logged('no scripted or exit option in [Who are you?]')).to_be(True)
    place.pending = True
    expect(run_wait(town.drive_once([], place.log))).to_be(False)
    place.pending = False
    spy_on(chat_dialog, 'is_open', returns=True)
    spy_on(chat_dialog, 'options', returns=[])
    expect(run_wait(town.drive_once([], place.log))).to_be(False)


test('a villager menu that loops back takes each scripted line once and then leaves by its "ok" line', drives_each_line_once)


def talks_to_a_villager():
    place = Town(SM_TILE.TOWN)
    place.walk_ok = False
    expect(run_wait(town.talk_villager(SM_NPC.RAZMIRE, SM_NPC.RAZMIRE_AFFLICTED, SM_TILE.RAZMIRE, [], place.log))).to_be(False)
    place.walk_ok = True
    place.npc(SM_NPC.RAZMIRE)
    statuses = ['done']
    spy_on(reach, 'npc_dialog', impl=lambda name, anchor, log=None: result(statuses[0]))
    spy_on(town, 'drive_once', impl=lambda script, log: result(True))
    expect(run_wait(town.visit(SM_NPC.RAZMIRE, SM_NPC.RAZMIRE_AFFLICTED, SM_TILE.RAZMIRE, [])(place.log))).to_be(True)
    statuses[0] = 'unreachable'
    expect(run_wait(town.talk_villager(SM_NPC.RAZMIRE, SM_NPC.RAZMIRE_AFFLICTED, SM_TILE.RAZMIRE, [], place.log))).to_be(False)
    expect(place.logged('did not answer — falling back to a dose of serum')).to_be(True)
    expect(place.logged('no serum 207 in the pack')).to_be(True)

    place.npcs = []
    place.hold(SM_ID.SERUM3)
    expect(run_wait(town.talk_villager(SM_NPC.RAZMIRE, SM_NPC.RAZMIRE_AFFLICTED, SM_TILE.RAZMIRE, [], place.log))).to_be(False)
    expect(place.logged('no Razmire Keelgan beside (3489,3296)')).to_be(True)
    place.npc(SM_NPC.RAZMIRE_AFFLICTED)
    used = []
    place.pack[0]._fields['use_on'] = lambda other: False
    expect(run_wait(town.talk_villager(SM_NPC.RAZMIRE, SM_NPC.RAZMIRE_AFFLICTED, SM_TILE.RAZMIRE, [], place.log))).to_be(False)
    place.pack[0]._fields['use_on'] = lambda other: True
    expect(run_wait(town.talk_villager(SM_NPC.RAZMIRE, SM_NPC.RAZMIRE_AFFLICTED, SM_TILE.RAZMIRE, [], place.log))).to_be(False)
    expect(place.logged('the serum on Razmire Keelgan opened no dialogue')).to_be(True)
    place.pack[0]._fields['use_on'] = place.dose(used, 'serum')
    place.hold(SM_ID.SERUM_PERM2, use_on=place.dose(used, 'sanctified'))
    expect(run_wait(town.talk_villager(SM_NPC.RAZMIRE, SM_NPC.RAZMIRE_AFFLICTED, SM_TILE.RAZMIRE, [], place.log))).to_be(True)
    expect(used).to_equal(['sanctified'])


test('a villager is talked to cured while his face lasts, and dosed with serum, sanctified first, once it has gone', talks_to_a_villager)


def finds_the_diary_and_herbs():
    place = Town(SM_TILE.SHELF)
    searched = []

    def search(step, log):
        searched.append(step.name)
        if step.name == 'Shelf':
            place.hold(SM_ID.DIARY)
        else:
            place.hold(SM_ID.UNID_TARROMIN, 3)
        return step.expect()
        yield
    spy_on(town, 'prompt_loc', impl=search)
    expect(run_wait(town.take_diary(place.log))).to_be(True)
    spy_on(town, 'prompt_loc', impl=lambda step, log: result(False))
    expect(run_wait(town.take_diary(place.log))).to_be(True)
    place.pack = []
    expect(run_wait(town.take_diary(place.log))).to_be(False)
    spy_on(town, 'prompt_loc', impl=search)
    expect(run_wait(town.search_table(place.log))).to_be(True)
    expect(searched).to_equal(['Shelf', 'Smashed table'])

    place.pack = []
    expect(run_wait(town.identify_tarromin(place.log))).to_be(False)
    expect(place.logged('no unidentified tarromin')).to_be(True)
    herb = place.hold(SM_ID.UNID_TARROMIN, interact=lambda op: False)
    expect(run_wait(town.identify_tarromin(place.log))).to_be(False)
    herb._fields['interact'] = place.gives(SM_ID.TARROMIN, SM_ID.UNID_TARROMIN)
    expect(run_wait(town.identify_tarromin(place.log))).to_be(True)


test("Herbi Flax's diary comes off the shelf and the tarromin out of the smashed table, identified by id", finds_the_diary_and_herbs)


def reads_the_diary():
    place = Town(SM_TILE.SHELF)
    clicks = []
    expect(run_wait(town.read_diary(place.log))).to_be(False)
    expect(place.logged('no diary in the pack to read')).to_be(True)
    diary = place.hold(SM_ID.DIARY, interact=lambda op: False)
    expect(run_wait(town.read_diary(place.log))).to_be(False)
    diary._fields['interact'] = lambda op: True
    place.chat.pages = ['continue']
    expect(run_wait(town.read_diary(place.log))).to_be(False)
    expect(place.logged('the diary never opened the book interface (main modal -1)')).to_be(True)

    def opens(op):
        place.modal = Fake(chat=-1, main=town.BOOK_MODAL)
        place.texts = ['Diary', 'Page 1', 'Of my travels']
        return True
    diary._fields['interact'] = opens

    def turn(id):
        clicks.append(id)
        if len(clicks) == 3:
            place.texts = ['Diary', 'Index of solution', 'The serum']
        return True
    spy_on(_core, 'click_component', impl=turn)
    expect(run_wait(town.read_diary(place.log))).to_be(True)
    expect(clicks).to_equal([town.BOOK_NEXT, town.BOOK_NEXT, town.BOOK_NEXT])
    spy_on(_core, 'click_component', returns=True)
    expect(run_wait(town.read_diary(place.log))).to_be(False)
    expect(place.logged('the diary stopped at "Page 1 / Of my travels"')).to_be(True)


test("the diary is paged to its index of solution through the book's unlabelled arrow", reads_the_diary)


def brews_the_serum():
    place = Town(SM_TILE.SHELF)
    place.walk_ok = False
    expect(run_wait(town.take_vial(place.log))).to_be(False)
    place.walk_ok = True
    expect(run_wait(town.take_vial(place.log))).to_be(False)
    expect(place.logged('no empty vial on the experiment-house floor yet')).to_be(True)
    vial = place.item(SM_ID.VIAL_EMPTY, interact=lambda op: False)
    expect(run_wait(town.take_vial(place.log))).to_be(False)
    vial._fields['interact'] = place.gives(SM_ID.VIAL_EMPTY)
    expect(run_wait(town.take_vial(place.log))).to_be(True)

    expect(run_wait(town.mix_unfinished(place.log))).to_be(False)
    expect(place.logged('unfinished potion: the pack is missing an ingredient')).to_be(True)
    herb = place.hold(SM_ID.TARROMIN, use_on=lambda other: False)
    place.hold(SM_ID.VIAL_WATER)
    expect(run_wait(town.mix_unfinished(place.log))).to_be(False)
    herb._fields['use_on'] = place.gives(SM_ID.TARROMIN_UNF, SM_ID.TARROMIN)
    expect(run_wait(town.mix_unfinished(place.log))).to_be(True)
    place.hold(SM_ID.ASHES, use_on=place.gives(SM_ID.SERUM3, SM_ID.ASHES))
    expect(run_wait(town.mix_serum(place.log))).to_be(True)
    expect(place.count(SM_ID.SERUM3)).to_be(1)

    filled = []

    def use_on_loc(item_id, loc, prefer, expect_fn, log):
        filled.append([item_id, loc.name])
        place.hold(SM_ID.VIAL_WATER)
        return expect_fn()
        yield
    spy_on(supplies, 'use_on_loc', impl=use_on_loc)
    expect(run_wait(supplies.fill_vial(place.log))).to_be(True)
    expect(filled).to_equal([[SM_ID.VIAL_EMPTY, 'Sink']])


test('serum 207 is brewed from the house vials, the sink water, the tarromin and the ashes', brews_the_serum)


def shops_at_razmire():
    place = Town(SM_TILE.RAZMIRE)
    order = town.builders_order(2)
    expect(town.slots_wanted(order)).to_be(5)
    place.hold(SM_ID.SWAMP_PASTE, 4)
    expect(town.slots_wanted(order)).to_be(4)
    place.pack = []
    opened = [False]
    spy_on(shop, 'is_open', impl=lambda: opened[0])
    spy_on(shop, 'close', impl=lambda: result(True))
    stocked = [True]

    def buy(name, qty):
        items = order.items
        if stocked[0]:
            id = [w.id for w in items if w.name == name][0]
            place.hold(id, qty)
        return stocked[0]
        yield
    spy_on(shop, 'buy', impl=buy)
    expect(run_wait(town.fill_order(order, place.log))).to_be(False)
    expect(place.logged("'Trade-Builders-Store' never opened a shop")).to_be(True)
    opened[0] = True
    stocked[0] = False
    expect(run_wait(town.fill_order(order, place.log))).to_be(False)
    expect(place.logged('short after the shop: Swamp paste 0/12, Plank 0/2, Limestone brick 0/2')).to_be(True)
    stocked[0] = True

    leg = town.shop_at_razmire(order)
    for i in range(24):
        place.hold(SM_ID.LOGS)
    expect(run_wait(leg(place.log))).to_be(False)
    expect(place.logged('no room for the order — 4 free, 5 wanted')).to_be(True)
    place.pack = []
    place.walk_ok = False
    expect(run_wait(leg(place.log))).to_be(False)
    place.walk_ok = True
    spy_on(town, 'talk_villager', impl=lambda cured, afflicted, anchor, script, log: result(False))
    expect(run_wait(leg(place.log))).to_be(False)
    spy_on(town, 'talk_villager', impl=lambda cured, afflicted, anchor, script, log: result(True))
    expect(run_wait(leg(place.log))).to_be(True)
    expect(run_wait(leg(place.log))).to_be(True)
    place.pack = []
    place.npc(SM_NPC.RAZMIRE, ['Talk-to', 'Trade-General-Store', 'Trade-Builders-Store'])
    expect(run_wait(leg(place.log))).to_be(True)


test("Razmire's counters are opened by their op or through a cured talk, and the order is bought out", shops_at_razmire)


def hands_over_and_stocks():
    place = Town(SM_TILE.RAZMIRE)
    talks = [True]
    spy_on(town, 'talk_villager', impl=lambda cured, afflicted, anchor, script, log: result(talks[0]))
    fills = [True]
    spy_on(town, 'fill_order', impl=lambda order, log: result(fills[0]))
    visits = Legs()
    spy_on(town, 'shop_at_razmire', impl=visits.shop_at)
    expect(run_wait(town.handover_and_stock([])(place.log))).to_be(True)
    orders = [town.general_order(True, False), town.builders_order(5), town.general_order(False, True)]
    talks[0] = False
    expect(run_wait(town.handover_and_stock(orders)(place.log))).to_be(False)
    talks[0] = True
    fills[0] = False
    expect(run_wait(town.handover_and_stock(orders)(place.log))).to_be(False)
    fills[0] = True
    expect(run_wait(town.handover_and_stock(orders[:2])(place.log))).to_be(True)
    expect(run_wait(town.handover_and_stock(orders)(place.log))).to_be(False)
    expect(visits.calls).to_equal(['Trade-Builders-Store', 'Trade-Builders-Store'])


test("the stage-40 handover stocks every counter inside the one cured talk", hands_over_and_stocks)


def drops_down():
    place = Town(SM_TILE.TOWN)
    place.hold(SM_ID.DIARY, interact=lambda op: place.drop(SM_ID.DIARY) or True)
    place.hold(SM_ID.ROTTEN_FOOD, interact=lambda op: place.drop(SM_ID.ROTTEN_FOOD) or True)
    expect(run_wait(town.drop_junk(place.log))).to_be(True)
    expect(place.pack).to_equal([])
    place.hold(SM_ID.REMAINS, interact=lambda op: False)
    expect(run_wait(town.drop_down([Record({'id': SM_ID.REMAINS, 'keep': 0})], place.log))).to_be(False)
    expect(place.logged(f'item {SM_ID.REMAINS} would not drop')).to_be(True)
    place.pack[0]._fields['interact'] = lambda op: True
    expect(run_wait(town.drop_down([Record({'id': SM_ID.REMAINS, 'keep': 0})], place.log))).to_be(False)


test('the spent diary and the rotten food are dropped, and a drop that never lands gives up', drops_down)


def burns_for_ashes():
    place = Town(SM_TILE.VARROCK_LOGS)
    expect(run_wait(supplies.burn_one(place.log))).to_be(False)
    expect(place.logged('burnOne: no tinderbox or no logs')).to_be(True)
    tinder = place.hold(SM_ID.TINDERBOX, use_on=lambda other: False)
    place.hold(SM_ID.LOGS)
    expect(run_wait(supplies.burn_one(place.log))).to_be(False)
    tinder._fields['use_on'] = lambda other: True
    expect(run_wait(supplies.burn_one(place.log))).to_be(False)
    expect(place.logged('burnOne: the fire never left any ashes')).to_be(True)
    ash = place.item(SM_ID.ASHES, interact=lambda op: False)
    expect(run_wait(supplies.burn_one(place.log))).to_be(False)
    ash._fields['interact'] = place.gives(SM_ID.ASHES)
    expect(run_wait(supplies.burn_one(place.log))).to_be(True)

    place = Town(VARROCK)
    clock = [0]

    def now():
        clock[0] += 1000
        return clock[0]
    spy_on(_core, 'step_time', impl=now)
    spy_on(bank, 'is_open', returns=True)
    closed = []
    spy_on(bank, 'close', impl=lambda: result(closed.append(1) is None))
    place.walk_ok = False
    expect(run_wait(supplies.make_ashes(1, 1)(place.log))).to_be(False)
    expect(closed).to_equal([1])
    place.walk_ok = True
    spawn = place.item(SM_ID.LOGS)

    def burn(log):
        logs = [held for held in place.pack if held.id == SM_ID.LOGS]
        place.pack = [held for held in place.pack if held.id != SM_ID.LOGS] + logs[1:]
        place.hold(SM_ID.ASHES)
        return True
        yield
    spy_on(supplies, 'burn_one', impl=burn)
    expect(run_wait(supplies.make_ashes(1, 1)(place.log))).to_be(True)
    expect([place.count(SM_ID.ASHES), place.count(SM_ID.LOGS)]).to_equal([1, 1])
    spy_on(supplies, 'burn_one', impl=lambda log: result(False))
    expect(run_wait(supplies.make_ashes(2, 0)(place.log))).to_be(False)
    place.ground = []
    expect(run_wait(supplies.make_ashes(3, 1)(place.log))).to_be(False)
    expect(place.logged('makeAshes: gave up holding 1 ashes')).to_be(True)
    spawn._fields['interact'] = lambda op: False
    place.ground = [spawn]
    expect(run_wait(supplies.make_ashes(3, 1)(place.log))).to_be(False)


test("the Varrock log spawns feed the burns until the pack holds the ashes and the pyre's log", burns_for_ashes)


def kit_snap(inv_ids, inv=None, bank=None, bank_ids=None, stage=None):
    if stage is None:
        stage = SM_STAGE.READ_DIARY
    return QuestSnapshot(**{
        'journal': 'in_progress',
        'inv': inv if inv is not None else {},
        'inv_ids': inv_ids,
        'worn': set(),
        'worn_ids': set(),
        'bank': bank if bank is not None else {},
        'bank_ids': bank_ids if bank_ids is not None else {},
        'bank_known': True,
        'stage': stage,
        'progress': QuestProgress(stage, set()),
        'tile': SM_TILE.TOWN,
        'free_slots': 14,
    })


def draws_the_kit():
    food = quest_food.name.lower()
    step = supplies.kit(kit_snap({}, {}, {'coins': 90000, food: 3}, {SM_ID.LOGS: 9}), SM_STAGE.READ_DIARY)
    expect(step.kind).to_be('withdraw')
    expect([[w['name'], w['qty']] for w in step.items]).to_equal([['Coins', 30000], [quest_food.name, 3], ['Logs', 3]])
    step = supplies.kit(kit_snap({SM_ID.COINS: 30000, SM_ID.TINDERBOX: 1}, {food: 0}, {}, {}), SM_STAGE.LIT_PYRE)
    expect(step).to_be(None)
    expect(supplies.serum_vials(kit_snap({SM_ID.SERUM3: 1, SM_ID.SERUM1: 2}))).to_be(3)


test('the approach kit draws coins, food and logs from the bank, and gives up quietly when none is banked', draws_the_kit)


def rebuilds_the_temple():
    place = Town(SM_TILE.TEMPLE_INSIDE)
    expect([is_temple_wall(4070), is_temple_wall(4085), is_temple_wall(4090)]).to_equal([True, True, False])
    expect([in_mortton(SM_TILE.TOWN), in_mortton(VARROCK), in_temple_zone(SM_TILE.ALTAR), in_temple_zone(None)]).to_equal([True, False, True, False])
    expect(run_wait(temple.repair_temple(place.log))).to_be(False)
    expect(place.logged('no hammer in the pack')).to_be(True)
    place.hold(SM_ID.HAMMER)
    place.at = VARROCK
    place.walk_ok = False
    expect(run_wait(temple.repair_temple(place.log))).to_be(False)
    place.walk_ok = True
    place.pending = True
    expect(run_wait(temple.repair_temple(place.log))).to_be(False)
    expect(place.logged('yielding to a random event mid-build')).to_be(True)
    place.pending = False

    # One click, the server's own loop builds; the re-click waits out a fight and three quiet ticks.
    clicks = []
    wall = place.loc(SM_LOC_ID.WALL_BASE, ['Repair'], tile=WALL)

    def build(op):
        clicks.append(op)
        if len(clicks) == 2:
            place.varps[SM_VARP.TEMPLE_SANCTITY] = 5
            place.varps[SM_VARP.TEMPLE_RESOURCES] = 40
            place.varps[SM_VARP.TEMPLE_REPAIRED] = 100
            wall._fields['actions'] = lambda: ['Reinforce']
            place.loc(SM_LOC_ID.ALTAR_UNLIT, ['Light'])
        return True
    wall._fields['interact'] = build
    place.varps[SM_VARP.TEMPLE_RESOURCES] = 50
    place.texts = ['You need a hammer']
    place.modal = Fake(chat=1, main=-1)
    place.chat.pages = ['continue']
    shown = [True]

    def box():
        if shown[0]:
            shown[0] = False
            return Fake(chat=1, main=-1)
        return Fake(chat=-1, main=-1)
    spy_on(reader, 'modals', impl=box)
    place.hp = [40, 20]
    place.fighting = True
    original_tick = place.tick

    def tick():
        now = original_tick()
        if now == 6:
            place.fighting = False
        return now
    spy_on(game, 'tick', impl=tick)
    expect(run_wait(temple.repair_temple(place.log))).to_be(True)
    expect(clicks).to_equal(['Repair', 'Repair'])
    expect(place.logged('temple rebuilt — sanctity 5%, pool 40%')).to_be(True)
    expect(place.hp[1]).to_be(40)

    # Finished pieces are reinforced only while nothing else wants a repair.
    place.locs = [wall]
    clicks.clear()
    patch(temple, 'BUILD_GUARD', 12)
    expect(run_wait(temple.repair_temple(place.log))).to_be(True)
    expect(clicks[0]).to_be('Reinforce')
    expect(place.logged('build guard hit at 100% repaired')).to_be(True)

    place.locs = []
    place.at = VARROCK
    walks = [True]

    def walk(tile, radius=2, attempts=None, timeout_ms=None, log=None):
        return walks.pop(0) if len(walks) > 0 else False
        yield
    spy_on(traversal, 'walk_resilient', impl=walk)
    expect(run_wait(temple.repair_temple(place.log))).to_be(False)


test('the temple shell is built by one click per server loop until the fire altar appears', rebuilds_the_temple)


def runs_out_of_material():
    place = Town(SM_TILE.TEMPLE_INSIDE)
    place.hold(SM_ID.HAMMER)
    place.modal = Fake(chat=1, main=-1)
    place.texts = ['The temple', 'has run out of its material resource pool.']
    place.chat.pages = ['continue']
    expect(run_wait(temple.repair_temple(place.log))).to_be(False)
    expect(place.logged('out of building materials at 0% repaired')).to_be(True)
    expect(temple.box_text()).to_contain('material resource pool')
    place.modal = Fake(chat=-1, main=-1)
    expect(temple.box_text()).to_be(None)


test("the temple's out-of-material box ends the rebuild with both of its boxes answered", runs_out_of_material)


def lights_the_altar():
    place = Town(SM_TILE.TEMPLE_INSIDE)
    lit = place.loc(SM_LOC_ID.ALTAR_LIT, [])
    expect(run_wait(temple.light_altar(place.log))).to_be(True)
    place.locs = []
    expect(run_wait(temple.light_altar(place.log))).to_be(False)
    expect(place.logged('no tinderbox in the pack')).to_be(True)
    place.hold(SM_ID.TINDERBOX)
    place.at = VARROCK
    place.walk_ok = False
    expect(run_wait(temple.light_altar(place.log))).to_be(False)
    place.walk_ok = True

    def strike(op):
        place.locs = [lit]
        return True
    place.varps[SM_VARP.TEMPLE_SANCTITY] = 25
    place.loc(SM_LOC_ID.ALTAR_UNLIT, ['Light'], interact=strike)
    expect(run_wait(temple.light_altar(place.log))).to_be(True)

    # Cold sanctity is built on the walls first; a box on the way is answered.
    place.locs = []
    place.varps[SM_VARP.TEMPLE_SANCTITY] = 15
    place.varps[SM_VARP.TEMPLE_RESOURCES] = 50
    shown = [True]

    def box():
        if shown[0]:
            shown[0] = False
            return Fake(chat=1, main=-1)
        return Fake(chat=-1, main=-1)
    spy_on(reader, 'modals', impl=box)

    def build(op):
        place.varps[SM_VARP.TEMPLE_SANCTITY] = 25
        return True
    place.loc(SM_LOC_ID.WALL_BASE + 3, ['Reinforce'], interact=build)
    place.loc(SM_LOC_ID.ALTAR_UNLIT, ['Light'], interact=strike)
    place.animating = True
    original_tick = place.tick

    def tick():
        now = original_tick()
        place.animating = now < 5
        return now
    spy_on(game, 'tick', impl=tick)
    expect(run_wait(temple.light_altar(place.log))).to_be(True)

    place.locs = []
    place.varps[SM_VARP.TEMPLE_SANCTITY] = 15
    expect(run_wait(temple.light_altar(place.log))).to_be(False)
    expect(place.logged('the altar is broken and no wall is in reach')).to_be(True)
    place.varps[SM_VARP.TEMPLE_SANCTITY] = 5
    place.varps[SM_VARP.TEMPLE_RESOURCES] = 0
    expect(run_wait(temple.light_altar(place.log))).to_be(False)
    expect(place.logged('sanctity is 5% with an empty pool')).to_be(True)
    place.varps[SM_VARP.TEMPLE_SANCTITY] = 15
    place.varps[SM_VARP.TEMPLE_RESOURCES] = 50
    spy_on(game, 'tick', impl=place.tick)
    place.animating = True
    expect(run_wait(temple.light_altar(place.log))).to_be(False)
    expect(place.logged('the sacred flame never caught')).to_be(True)


test('the altar is struck once sanctity is built, re-armed on the walls when cold, and abandoned without material', lights_the_altar)


def sanctifies_in_the_flame():
    place = Town(SM_TILE.TEMPLE_INSIDE)
    used = []

    def use_on_loc(item_id, loc, prefer, expect_fn, log):
        used.append(item_id)
        place.drop(item_id)
        place.hold(SM_ID.SACRED_OIL3 if item_id == SM_ID.OLIVE_OIL3 else SM_ID.SERUM_PERM3)
        return expect_fn()
        yield
    spy_on(temple, 'use_on_loc', impl=use_on_loc)
    expect(run_wait(temple.sanctify_oil(place.log))).to_be(False)
    expect(place.logged('no olive oil of two doses or more')).to_be(True)
    place.hold(SM_ID.OLIVE_OIL3)
    expect(run_wait(temple.sanctify_oil(place.log))).to_be(True)
    expect(temple.sacred_oil_doses()).to_be(3)

    expect(run_wait(temple.sanctify_serum(place.log))).to_be(False)
    expect(place.logged('no serum 207 left to sanctify')).to_be(True)
    place.hold(SM_ID.SERUM2)
    expect(run_wait(temple.sanctify_serum(place.log))).to_be(False)
    expect(place.logged('the flame wants 20% for the serum')).to_be(True)
    place.varps[SM_VARP.TEMPLE_SANCTITY] = 20
    expect(run_wait(temple.sanctify_serum(place.log))).to_be(True)
    expect(run_wait(temple.sanctify_serum(place.log))).to_be(True)
    expect(used).to_equal([SM_ID.OLIVE_OIL3, SM_ID.SERUM2])


test('the olive oil and a vial of serum are sanctified in the lit flame', sanctifies_in_the_flame)


def builds_the_pyre():
    place = Town(SM_TILE.TOWN)
    expect(run_wait(pyre.make_pyre_logs(place.log))).to_be(False)
    expect(place.logged('only 0 dose(s) of sacred oil')).to_be(True)
    oil = place.hold(SM_ID.SACRED_OIL2, use_on=lambda other: False)
    expect(run_wait(pyre.make_pyre_logs(place.log))).to_be(False)
    expect(place.logged('no sacred oil vial or no logs')).to_be(True)
    place.hold(SM_ID.LOGS)
    expect(run_wait(pyre.make_pyre_logs(place.log))).to_be(False)
    oil._fields['use_on'] = place.gives(SM_ID.PYRE_LOGS, SM_ID.LOGS)
    expect(run_wait(pyre.make_pyre_logs(place.log))).to_be(True)

    stage = [SM_LOC_ID.PYRE_EMPTY]

    def use_on_loc(item_id, loc, prefer, expect_fn, log):
        stage[0] = SM_LOC_ID.PYRE_LOGS if loc.id == SM_LOC_ID.PYRE_EMPTY else SM_LOC_ID.PYRE_BONES
        place.locs = [Fake(id=stage[0], distance=lambda: 1, interact=lambda op: True)]
        return expect_fn()
        yield
    spy_on(pyre, 'use_on_loc', impl=use_on_loc)
    place.walk_ok = False
    expect(run_wait(pyre.stack_pyre(place.log))).to_be(False)
    expect(run_wait(pyre.lay_remains(place.log))).to_be(False)
    place.walk_ok = True
    expect(run_wait(pyre.stack_pyre(place.log))).to_be(True)
    expect(run_wait(pyre.stack_pyre(place.log))).to_be(True)
    expect(run_wait(pyre.lay_remains(place.log))).to_be(True)
    expect(run_wait(pyre.lay_remains(place.log))).to_be(True)
    expect(run_wait(pyre.at_pyres(place.log))).to_be(True)


test('sacred oil soaks the pyre logs, which are stacked on our own pyre before the remains are laid on them', builds_the_pyre)


def lights_the_pyre():
    place = Town(SM_TILE.PYRE)
    expect(run_wait(pyre.light_pyre(place.log))).to_be(False)
    expect(place.logged('no tinderbox in the pack')).to_be(True)
    place.hold(SM_ID.TINDERBOX)
    place.at = VARROCK
    place.walk_ok = False
    expect(run_wait(pyre.light_pyre(place.log))).to_be(False)
    place.walk_ok = True
    expect(run_wait(pyre.light_pyre(place.log))).to_be(False)
    expect(place.logged('no loaded funeral pyre in reach')).to_be(True)
    bodied = Fake(id=SM_LOC_ID.PYRE_BONES, distance=lambda: 1, interact=lambda op: False)
    place.locs = [bodied]
    expect(run_wait(pyre.light_pyre(place.log))).to_be(False)
    bodied._fields['interact'] = lambda op: True
    expect(run_wait(pyre.light_pyre(place.log))).to_be(False)
    expect(place.logged('the funeral pyre never caught')).to_be(True)

    def burn(op):
        place.locs = []
        return True
    bodied._fields['interact'] = burn
    expect(run_wait(pyre.light_pyre(place.log))).to_be(True)


test('the funeral pyre is lit and the leg waits for it to revert once the reward has run', lights_the_pyre)


def hunts_a_shade():
    place = Town(SM_TILE.TOWN)
    remains = place.item(SM_ID.REMAINS, interact=lambda op: False)
    place.walk_ok = False
    expect(run_wait(shades.hunt_shade(place.log))).to_be(False)
    remains._fields['interact'] = place.gives(SM_ID.REMAINS)
    expect(run_wait(shades.hunt_shade(place.log))).to_be(True)
    place.ground = []
    place.walk_ok = True
    expect(run_wait(shades.hunt_shade(place.log))).to_be(False)
    expect(place.logged('no Loar Shadow in the streets yet')).to_be(True)

    shadow = place.npc(SM_NPC.SHADOW, ['Attack'], SM_NPC_ID.SHADOW, 9)
    place.pending = True
    expect(run_wait(shades.hunt_shade(place.log))).to_be(False)
    expect(place.logged('yielding to a random event mid-shade')).to_be(True)
    place.pending = False
    swings = []

    def attack(op):
        swings.append(op)
        if len(swings) == 2:
            place.npcs = []
            place.item(SM_ID.REMAINS)
        return True
    shadow._fields['interact'] = attack
    place.hp = [40, 20]
    original_tick = place.tick

    def tick():
        now = original_tick()
        place.fighting = now == 3
        return now
    spy_on(game, 'tick', impl=tick)
    expect(run_wait(shades.hunt_shade(place.log))).to_be(True)
    expect(len(swings)).to_be(2)
    expect(place.count(SM_ID.REMAINS)).to_be(2)

    place.npcs = [shadow]
    place.ground = []
    shadow._fields['interact'] = lambda op: False
    expect(run_wait(shades.hunt_shade(place.log))).to_be(False)
    expect(place.logged('gave up on Loar Shadow 9 after 0 attacks')).to_be(True)


test('a Loar Shadow is fought until it sinks and its remains are pocketed in the same step', hunts_a_shade)


def runs_the_altar_and_pyre_legs():
    place = Town(SM_TILE.TEMPLE_INSIDE)
    state = {'repaired': 50, 'sanctity': 30, 'perm': None, 'lit': None}
    stand_in = Legs()
    legs = stand_in.ok
    calls = stand_in.calls
    legs['repair'] = False
    for name, short in [['repair_temple', 'repair'], ['light_altar', 'light'], ['sanctify_oil', 'oil'], ['sanctify_serum', 'sanctify'],
                        ['lay_remains', 'lay'], ['light_pyre', 'light']]:
        spy_on(mortton, name, impl=stand_in.leg(short))
    spy_on(mortton, 'temple_repaired', impl=lambda: state['repaired'])
    spy_on(mortton, 'temple_sanctity', impl=lambda: state['sanctity'])
    spy_on(mortton, 'perm_serum_vial_id', impl=lambda: state['perm'])
    spy_on(mortton, 'altar_lit', impl=lambda: state['lit'])
    expect(run_wait(mortton.altar_leg(place.log))).to_be(False)
    state['repaired'] = 100
    legs['light'] = False
    expect(run_wait(mortton.altar_leg(place.log))).to_be(False)
    legs['light'] = True
    legs['oil'] = False
    expect(run_wait(mortton.altar_leg(place.log))).to_be(False)
    legs['oil'] = True
    calls.clear()
    expect(run_wait(mortton.altar_leg(place.log))).to_be(True)
    expect(calls).to_equal(['light', 'oil', 'light', 'sanctify'])

    legs['lay'] = False
    expect(run_wait(mortton.cremate(place.log))).to_be(False)
    legs['lay'] = True
    calls.clear()
    expect(run_wait(mortton.cremate(place.log))).to_be(True)
    expect(calls).to_equal(['lay', 'light'])


test('the altar leg rebuilds, lights and sanctifies in order, and the cremation lays the remains before the light', runs_the_altar_and_pyre_legs)


def ready_snap(stage, inv_ids=None, free_slots=14, flags=None, inv=None):
    """Everything the approach kit and the serum chain ask for, at the stage."""
    food = quest_food.name.lower()
    ids = {SM_ID.COINS: 30000, SM_ID.TINDERBOX: 1, SM_ID.ASHES: 2, SM_ID.LOGS: 1, SM_ID.SERUM3: 2, SM_ID.PYRE_LOGS: 1}
    for id, count in (inv_ids if inv_ids is not None else {}).items():
        ids[id] = count
    pack = {food: 6}
    for name, count in (inv if inv is not None else {}).items():
        pack[name] = count
    return QuestSnapshot(**{
        'journal': 'in_progress',
        'inv': pack,
        'inv_ids': ids,
        'worn': set(['rune scimitar', 'rune chainbody', 'rune platelegs', 'rune full helm', 'rune kiteshield']),
        'worn_ids': set(),
        'bank': {'coins': 2000000, food: 100},
        'bank_ids': {},
        'bank_known': True,
        'stage': stage,
        'progress': QuestProgress(stage, set(flags if flags is not None else [])),
        'tile': SM_TILE.TOWN,
        'free_slots': free_slots,
    })


def decides_the_corners():
    expect(mortton.decide(ready_snap(SM_STAGE.COMPLETE)).kind).to_be('done')
    expect(mortton.decide(ready_snap(SM_STAGE.MADE_SERUM, {SM_ID.DIARY: 1})).name).to_be('drop the diary and the rotten food')
    step = mortton.decide(ready_snap(SM_STAGE.SHADES_TO_ULSQUIRE, {SM_ID.REMAINS: 4}))
    expect(step.name).to_be('drop the spare remains')
    place = Town(SM_TILE.TOWN)
    dropped = []
    spy_on(mortton, 'drop_down', impl=lambda wants, log: result(dropped.extend([[w.id, w.keep] for w in wants]) is None))
    expect(run_wait(step.run(place.log))).to_be(True)
    expect(dropped).to_equal([[SM_ID.REMAINS, 2]])
    flags = [f'{SM_FLAG.SANCTITY}:30', f'{SM_FLAG.REPAIRED}:100']
    step = mortton.decide(ready_snap(SM_STAGE.CREATED_SACRED_OIL, {SM_ID.PYRE_LOGS: 0}, flags=flags))
    expect(step.name).to_be("buy from Razmire's general store")
    step = mortton.decide(ready_snap(SM_STAGE.REBUILD_TEMPLE, {SM_ID.HAMMER: 1}, free_slots=0))
    expect(step.reason).to_be('no pack room for building material')
    expect(mortton.decide(ready_snap(46)).reason).to_be('unmapped stage 46')
    expect(mortton.warn_readiness()).to_contain('5 sets of plank, brick and 6 paste')

    unread = ready_snap(SM_STAGE.KILL_SHADES).with_fields({'worn': set(), 'bank': {'rune scimitar': 1}, 'bank_known': False})
    expect(mortton.gear_leg(unread).kind).to_be('scan_bank')


test("Mort'ton's decide drops what the temple load wants back and waits on a full pack", decides_the_corners)


def reads_the_journal():
    place = Town(SM_TILE.TOWN)
    state = {'status': 'in_progress', 'text': "I've killed two shades", 'closed': 0}
    place.varps[SM_VARP.TEMPLE_REPAIRED] = 40
    spy_on(quests, 'status', impl=lambda name: state['status'])
    spy_on(quests, 'journal', impl=lambda name: result([state['text']]))

    def close():
        place.modal = Fake(chat=-1, main=-1)
        state['closed'] += 1
        return True
    spy_on(_core, 'close_interfaces', impl=close)
    progress = run_wait(journal.read_mortton_progress())
    expect(progress.stage).to_be(SM_STAGE.KILLED_2)
    expect('repaired:40' in progress.flags).to_be(True)
    state['text'] = ''
    place.modal = Fake(chat=-1, main=229)
    expect(run_wait(journal.read_mortton_progress()).stage).to_be(SM_STAGE.KILLED_2)
    expect(state['closed']).to_be(1)
    state['status'] = 'complete'
    expect(run_wait(journal.read_mortton_progress()).stage).to_be(SM_STAGE.COMPLETE)
    state['status'] = 'not_started'
    expect(run_wait(journal.read_mortton_progress()).stage).to_be(SM_STAGE.NOT_STARTED)
    state['status'] = 'unknown'
    expect(run_wait(journal.read_mortton_progress())).to_be(None)


test("the journal reader carries the temple's meters as flags and keeps the last stage through a blanked read", reads_the_journal)
