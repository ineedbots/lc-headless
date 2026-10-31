"""Eadgar's Ruse's legs against spied facades: the gathering trips, the parrot, the thistle and the potion, Mad
Eadgar's cell, the storeroom and the guarded talks, each through its success and its failures."""

import rs2004.quests.defs.eadgar as eadgar
import rs2004.quests.defs.eadgar.parrot as parrot
import rs2004.quests.defs.eadgar.storeroom as storeroom
import rs2004.quests.defs.eadgar.supplies as supplies
import rs2004.quests.defs.eadgar.travel as travel
import rs2004.quests.defs.eadgar.trollheim as trollheim
from rs2004 import execution
from rs2004.dialogue import modals
from rs2004.entities import ground_items, locs, npcs
from rs2004.game import game, skills
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.quests.defs.eadgar.areas import CHICKEN_NPC_ID, ER_ITEM, ER_LOC, ER_TILE, THISTLE_SPOTS
from rs2004.quests.defs.eadgar.journal import EADGAR_FLAG, EADGAR_STAGE
from rs2004.quests.defs.eadgar.supplies import take_ground
from rs2004.quests.engine.types import QuestProgress, QuestSnapshot
from rs2004.traversal import traversal

FALADOR = Tile(2946, 3369, 0)
TROLLHEIM = Tile(2891, 3676, 0)
STRONGHOLD = Tile(2844, 10057, 1)


def result(value):
    return value
    yield


class Ruse:
    """The player about Trollheim and the farms, with the pack, the scene, and what each leg's prompt does."""

    def __init__(self, at):
        self.at = at
        self.pack = []
        self.locs = []
        self.ground = []
        self.npcs = []
        self.walk_ok = True
        self.walks = []
        self.lines = []
        spy_on(game, 'tile', impl=lambda: self.at)
        spy_on(locs, 'query', impl=querying(lambda: self.locs))
        spy_on(ground_items, 'query', impl=querying(lambda: self.ground))
        spy_on(npcs, 'query', impl=querying(lambda: self.npcs))
        spy_on(inventory, 'items', impl=lambda: self.pack)
        spy_on(inventory, 'count', impl=lambda name: sum([i.count for i in self.pack if i.name == name]))
        spy_on(inventory, 'count_by_id', impl=lambda id: sum([i.count for i in self.pack if i.id == id]))
        spy_on(inventory, 'contains', impl=lambda name: any([i.name == name for i in self.pack]))
        spy_on(traversal, 'walk_resilient', impl=self.walk)
        for module in [storeroom, trollheim]:
            spy_on(module, 'settle_scene', impl=instant_ticks)
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

    def hold(self, item, use_on=None, interact=None):
        held = Fake(id=item.id, name=item.name, count=1, use_on=use_on if use_on is not None else (lambda other: True),
                    interact=interact if interact is not None else (lambda op: True))
        self.pack.append(held)
        return held

    def drop(self, item):
        self.pack = [held for held in self.pack if held.id != item.id]

    def gives(self, item, drops=None):
        def give(*args):
            if drops is not None:
                self.drop(drops)
            self.hold(item)
            return True
        return give


def takes_from_the_ground():
    ruse = Ruse(FALADOR)
    held = {'count': 1}
    drop = Fake(name='Raw chicken', interact=lambda op: True, distance=lambda: 1)
    spy_on(ground_items, 'query', impl=querying(lambda: [drop]))
    spy_on(inventory, 'count', impl=lambda name: held['count'])
    spy_on(inventory, 'contains', impl=lambda name: held['count'] > 0)
    # The Take hasn't landed: one chicken in the pack already must not read as success.
    expect(run_wait(take_ground('Raw chicken', ruse.log))).to_be(False)
    spy_on(ground_items, 'query', impl=querying(lambda: []))
    expect(run_wait(take_ground('Raw chicken', ruse.log))).to_be(False)
    spy_on(ground_items, 'query', impl=querying(lambda: [Fake(name='Raw chicken', interact=lambda op: False, distance=lambda: 1)]))
    expect(run_wait(take_ground('Raw chicken', ruse.log))).to_be(False)


test('a ground take waits for the count to rise, not for the pack to hold one already', takes_from_the_ground)


def gathers_the_scarecrow():
    ruse = Ruse(ER_TILE.TREES)
    expect(supplies.nearest_trees()).to_equal(ER_TILE.TREES)
    ruse.at = FALADOR
    expect(supplies.nearest_trees()).to_equal(ER_TILE.TREES_FALADOR)
    spy_on(game, 'tile', returns=None)
    expect(supplies.nearest_trees()).to_equal(ER_TILE.TREES)
    spy_on(game, 'tile', impl=lambda: ruse.at)

    ruse.at = Tile(3200, 3200, 0)
    ruse.walk_ok = False
    expect(run_wait(supplies.chop_logs(1, ruse.log))).to_be(False)
    ruse.walk_ok = True
    ruse.at = ER_TILE.TREES
    ruse.locs = [Fake(name='Tree', actions=lambda: ['Chop down'], distance=lambda: 1, interact=ruse.gives(ER_ITEM.LOGS))]
    expect(run_wait(supplies.chop_logs(2, ruse.log))).to_be(True)
    ruse.pack = []
    ruse.locs = []
    expect(run_wait(supplies.chop_logs(1, ruse.log))).to_be(False)
    expect(ruse.logged('could not cut 1 logs')).to_be(True)

    ruse = Ruse(ER_TILE.CHICKENS)
    spy_on(game, 'in_combat', returns=False)
    spy_on(game, 'set_combat_style', returns=True)
    chicken = Fake(id=CHICKEN_NPC_ID, name='Chicken', in_combat=False, actions=lambda: ['Attack'], distance=lambda: 1,
                   targets_another_player=lambda: False, valid=lambda: False, interact=lambda op: True)
    ruse.npcs = [chicken]

    def drops_meat():
        ruse.ground = [Fake(name='Raw chicken', distance=lambda: 1, interact=ruse.gives(ER_ITEM.RAW_CHICKEN))]
    chicken._fields['interact'] = lambda op: drops_meat() or True
    expect(run_wait(supplies.hunt_chickens(2, ruse.log))).to_be(True)
    ruse.pack = []
    ruse.ground = []
    ruse.npcs = []
    expect(run_wait(supplies.hunt_chickens(1, ruse.log))).to_be(False)
    expect(ruse.logged('could not gather 1 raw chicken')).to_be(True)
    ruse.at = FALADOR
    ruse.walk_ok = False
    expect(run_wait(supplies.hunt_chickens(1, ruse.log))).to_be(False)
    ruse.walk_ok = True
    spy_on(game, 'in_combat', returns=True)
    ruse.at = ER_TILE.CHICKENS
    expect(run_wait(supplies.hunt_chickens(1, ruse.log))).to_be(False)

    snap = QuestSnapshot(inv_ids={}, bank_ids={}, bank_known=True, inv={}, bank={}, tile=FALADOR)
    step = supplies.source_logs(snap.with_fields({'inv_ids': {ER_ITEM.AXE.id: 1}}), 1)
    expect(step.kind).to_be('custom')
    spy_on(supplies, 'chop_logs', impl=lambda qty, log: result(qty == 1))
    expect(run_wait(step.run(ruse.log))).to_be(True)
    step = supplies.source_chickens(snap, 5)
    spy_on(supplies, 'hunt_chickens', impl=lambda qty, log: result(qty == 5))
    expect(run_wait(step.run(ruse.log))).to_be(True)


test("the scarecrow's logs are chopped at the nearer trees and its chickens hunted at the Ardougne farm", gathers_the_scarecrow)


def buys_boots_and_prepares():
    ruse = Ruse(FALADOR)
    ruse.hold(ER_ITEM.CLIMBING_BOOTS)
    expect(run_wait(supplies.buy_boots(ruse.log))).to_be(True)
    ruse.pack = []
    expect(run_wait(supplies.buy_boots(ruse.log))).to_be(False)
    expect(ruse.logged('need 12 coins')).to_be(True)
    coins = Fake(id=995, name='Coins', count=100)
    ruse.pack = [coins]
    ruse.walk_ok = False
    expect(run_wait(supplies.buy_boots(ruse.log))).to_be(False)
    ruse.walk_ok = True

    def sells(npc, rules, prefer, log):
        ruse.hold(ER_ITEM.CLIMBING_BOOTS)
        return False
        yield
    spy_on(supplies, 'talk_choosing_by', impl=sells)
    expect(run_wait(supplies.buy_boots(ruse.log))).to_be(True)

    snap = QuestSnapshot(inv={'climbing boots': 1, 'lobster': 2}, inv_ids={ER_ITEM.CLIMBING_BOOTS.id: 1}, worn=set(), worn_ids=set(),
                         bank={}, bank_ids={}, bank_known=True, tile=TROLLHEIM)
    expect(supplies.prepare(snap, 'trollside').kind).to_be('custom')
    snap = snap.with_fields({'worn': set(['climbing boots']), 'worn_ids': set([ER_ITEM.CLIMBING_BOOTS.id]), 'inv_ids': {}, 'inv': {'lobster': 2}})
    expect(supplies.prepare(snap, 'trollside')).to_be(None)
    potions = snap.with_fields({'bank': {'prayer potion(4)': 1, 'prayer potion(3)': 5, 'coins': 0}, 'tile': FALADOR,
                                'inv': {'lobster': 9}, 'inv_ids': {}})
    step = supplies.prepare(potions, 'mainland', 4)
    expect(step.kind).to_be('withdraw')
    expect(step.items).to_equal([{'name': 'Prayer potion(4)', 'qty': 1}, {'name': 'Prayer potion(3)', 'qty': 1}])


test("Tenzing's boots are bought on the way, and the loadout draws two prayer doses for the crossings", buys_boots_and_prepares)


def catches_the_parrot():
    ruse = Ruse(ER_TILE.HECKEL)
    spy_on(modals, 'close_if_open', impl=lambda: result(True))
    spy_on(parrot, 'drive_until', impl=lambda expect_, prefer, log, ms=30000: result(expect_()))
    ruse.hold(ER_ITEM.PINEAPPLE_CHUNKS)
    expect(run_wait(parrot.dice_pineapple(ruse.log))).to_be(True)
    ruse.pack = []
    expect(run_wait(parrot.dice_pineapple(ruse.log))).to_be(False)
    expect(ruse.logged('no Knife or no Pineapple')).to_be(True)
    ruse.hold(ER_ITEM.KNIFE, use_on=lambda other: False)
    ruse.hold(ER_ITEM.PINEAPPLE)
    expect(run_wait(parrot.dice_pineapple(ruse.log))).to_be(False)
    ruse.pack = []
    ruse.hold(ER_ITEM.KNIFE, use_on=ruse.gives(ER_ITEM.PINEAPPLE_CHUNKS, ER_ITEM.PINEAPPLE))
    ruse.hold(ER_ITEM.PINEAPPLE)
    expect(run_wait(parrot.dice_pineapple(ruse.log))).to_be(True)

    ruse = Ruse(ER_TILE.PETE)
    ruse.hold(ER_ITEM.DRUNK_PARROT)
    expect(run_wait(parrot.catch_parrot(ruse.log))).to_be(True)
    ruse.pack = []
    ruse.walk_ok = False
    expect(run_wait(parrot.catch_parrot(ruse.log))).to_be(False)
    ruse.walk_ok = True
    spy_on(parrot, 'talk_strict', impl=lambda npc, prefer, log: result(False))
    expect(run_wait(parrot.catch_parrot(ruse.log))).to_be(False)
    expect(ruse.logged('Parroty Pete would not answer')).to_be(True)
    spy_on(parrot, 'talk_strict', impl=lambda npc, prefer, log: result(True))
    expect(run_wait(parrot.catch_parrot(ruse.log))).to_be(False)
    expect(ruse.logged('no Pineapple chunks or no liquor')).to_be(True)
    ruse.hold(ER_ITEM.PINEAPPLE_CHUNKS, use_on=lambda other: False)
    ruse.hold(ER_ITEM.VODKA)
    expect(run_wait(parrot.catch_parrot(ruse.log))).to_be(False)
    ruse.pack = []
    ruse.hold(ER_ITEM.PINEAPPLE_CHUNKS, use_on=lambda other: True)
    ruse.hold(ER_ITEM.VODKA)
    expect(run_wait(parrot.catch_parrot(ruse.log))).to_be(False)
    expect(ruse.logged('did not soak')).to_be(True)
    ruse.pack = []
    ruse.hold(ER_ITEM.PINEAPPLE_CHUNKS, use_on=ruse.gives(ER_ITEM.ALCO_CHUNKS, ER_ITEM.PINEAPPLE_CHUNKS))
    ruse.hold(ER_ITEM.VODKA)

    def baits(item_id, loc, prefer, expect_, log):
        ruse.hold(ER_ITEM.DRUNK_PARROT)
        return expect_()
        yield
    spy_on(parrot, 'use_on_loc', impl=baits)
    expect(run_wait(parrot.catch_parrot(ruse.log))).to_be(True)


test("the pineapple is diced, not sliced, Pete is asked both lines, and the soaked chunks bait the aviary", catches_the_parrot)


def brews_the_troll_potion():
    ruse = Ruse(TROLLHEIM)
    ruse.hold(ER_ITEM.TROLL_POTION)
    expect(run_wait(trollheim.mix_ids(ER_ITEM.GROUND_THISTLE.id, ER_ITEM.RANARR_VIAL.id, ER_ITEM.TROLL_POTION.id, ruse.log))).to_be(True)
    ruse.pack = []
    expect(run_wait(trollheim.mix_ids(ER_ITEM.GROUND_THISTLE.id, ER_ITEM.RANARR_VIAL.id, ER_ITEM.TROLL_POTION.id, ruse.log))).to_be(False)
    expect(ruse.logged('mix: missing item')).to_be(True)
    ruse.hold(ER_ITEM.GROUND_THISTLE, use_on=lambda other: False)
    ruse.hold(ER_ITEM.RANARR_VIAL)
    expect(run_wait(trollheim.mix_ids(ER_ITEM.GROUND_THISTLE.id, ER_ITEM.RANARR_VIAL.id, ER_ITEM.TROLL_POTION.id, ruse.log))).to_be(False)
    ruse.pack = []
    ruse.hold(ER_ITEM.GROUND_THISTLE, use_on=ruse.gives(ER_ITEM.TROLL_POTION))
    ruse.hold(ER_ITEM.RANARR_VIAL)
    expect(run_wait(trollheim.mix_ids(ER_ITEM.GROUND_THISTLE.id, ER_ITEM.RANARR_VIAL.id, ER_ITEM.TROLL_POTION.id, ruse.log))).to_be(True)

    snap = QuestSnapshot(inv_ids={}, bank_ids={}, bank_known=True, inv={}, bank={}, tile=FALADOR)
    for held, name in [[ER_ITEM.GROUND_THISTLE, 'mix the troll truth potion'], [ER_ITEM.DRIED_THISTLE, 'grind the dried thistle']]:
        step = trollheim.source_troll_potion(snap.with_fields({'inv_ids': {held.id: 1, ER_ITEM.RANARR_VIAL.id: 1, ER_ITEM.PESTLE.id: 1}}))
        expect(step.name).to_be(name)
        spy_on(trollheim, 'mix_ids', impl=lambda a, b, c, log: result(True))
        expect(run_wait(step.run(ruse.log))).to_be(True)
    step = trollheim.source_ranarr_vial(snap.with_fields({'inv_ids': {ER_ITEM.RANARR.id: 1, ER_ITEM.VIAL_WATER.id: 1}}))
    expect(run_wait(step.run(ruse.log))).to_be(True)
    expect(trollheim.source_vial(snap.with_fields({'bank_known': False})).kind).to_be('scan_bank')
    expect(trollheim.source_ranarr_vial(snap.with_fields({'bank_known': False})).kind).to_be('scan_bank')


test('the thistle is ground and mixed into the troll potion by object id', brews_the_troll_potion)


def picks_and_dries_the_thistle():
    ruse = Ruse(THISTLE_SPOTS[2])
    ruse.hold(ER_ITEM.THISTLE)
    expect(run_wait(trollheim.pick_thistle(ruse.log))).to_be(True)
    ruse.pack = []
    ruse.at = FALADOR
    ruse.walk_ok = False
    expect(run_wait(trollheim.pick_thistle(ruse.log))).to_be(False)
    ruse.walk_ok = True
    ruse.at = THISTLE_SPOTS[2]
    expect(run_wait(trollheim.pick_thistle(ruse.log))).to_be(False)
    expect(ruse.logged('no Troll Thistle in the scene')).to_be(True)
    expect(ruse.logged('could not pick a Troll Thistle')).to_be(True)
    ruse.npcs = [Fake(name='Thistle', actions=lambda: ['Pick'], distance=lambda: 1, interact=ruse.gives(ER_ITEM.THISTLE))]
    ruse.at = THISTLE_SPOTS[2]
    expect(run_wait(trollheim.pick_thistle(ruse.log))).to_be(True)

    ruse.pack = []
    ruse.hold(ER_ITEM.DRIED_THISTLE)
    expect(run_wait(trollheim.dry_thistle(ruse.log))).to_be(True)
    ruse.pack = []
    expect(run_wait(trollheim.dry_thistle(ruse.log))).to_be(False)
    expect(ruse.logged('no Troll thistle to dry')).to_be(True)
    ruse.hold(ER_ITEM.THISTLE)
    expect(run_wait(trollheim.dry_thistle(ruse.log))).to_be(False)
    expect(ruse.logged('no Tinderbox or no Logs')).to_be(True)

    fire = Fake(id=trollheim.FIRE_LOC, name='Fire', actions=lambda: [], distance=lambda: 1)

    def lights(other):
        ruse.locs = [fire]
        return True
    ruse.hold(ER_ITEM.TINDERBOX, use_on=lambda other: False)
    ruse.hold(ER_ITEM.LOGS)
    expect(run_wait(trollheim.dry_thistle(ruse.log))).to_be(False)
    expect(ruse.logged('the logs never caught')).to_be(True)
    ruse.pack = []
    ruse.hold(ER_ITEM.THISTLE, use_on=ruse.gives(ER_ITEM.DRIED_THISTLE, ER_ITEM.THISTLE))
    ruse.hold(ER_ITEM.TINDERBOX, use_on=lights)
    ruse.hold(ER_ITEM.LOGS)
    expect(run_wait(trollheim.dry_thistle(ruse.log))).to_be(True)
    ruse.pack = []
    ruse.hold(ER_ITEM.THISTLE, use_on=lambda other: False)
    expect(run_wait(trollheim.dry_thistle(ruse.log))).to_be(False)


test("the thistle is picked as it hops between its tiles, and dried on a fire lit where nothing stands", picks_and_dries_the_thistle)


def frees_eadgar_and_hides_the_parrot():
    ruse = Ruse(STRONGHOLD)
    ruse.walk_ok = False
    expect(run_wait(trollheim.free_eadgar(ruse.log))).to_be(False)
    ruse.walk_ok = True
    spy_on(trollheim, 'steal_cell_key', impl=lambda guard, key, stand, log: result(False))
    expect(run_wait(trollheim.free_eadgar(ruse.log))).to_be(False)
    spy_on(trollheim, 'steal_cell_key', impl=lambda guard, key, stand, log: result(True))
    spy_on(trollheim, 'unlock_cell', impl=lambda key, door, stand, log: result(False))
    expect(run_wait(trollheim.free_eadgar(ruse.log))).to_be(False)
    spy_on(trollheim, 'unlock_cell', impl=lambda key, door, stand, log: result(True))
    marked = []
    spy_on(trollheim, 'mark_eadgar_freed', impl=lambda: marked.append(True))
    expect(run_wait(trollheim.free_eadgar(ruse.log))).to_be(True)
    expect(marked).to_equal([True])

    spy_on(trollheim, 'use_on_loc', impl=lambda item_id, loc, prefer, expect_, log: result(loc.id == ER_LOC.RACK))
    expect(run_wait(trollheim.hide_parrot(ruse.log))).to_be(True)


test("Mad Eadgar's cell is opened with Berry's key, and the parrot goes under the rack", frees_eadgar_and_hides_the_parrot)


def works_the_storeroom():
    ruse = Ruse(STRONGHOLD)
    prompts = []

    def prompt(step, log):
        prompts.append(step.id)
        return step.expect()
        yield
    spy_on(storeroom, 'prompt_loc', impl=prompt)
    ruse.hold(ER_ITEM.STOREROOM_KEY)
    expect(run_wait(storeroom.take_storeroom_key(ruse.log))).to_be(True)
    expect(run_wait(storeroom.unlock_storeroom(ruse.log))).to_be(False)
    ruse.pack = []
    expect(run_wait(storeroom.unlock_storeroom(ruse.log))).to_be(False)
    expect(ruse.logged('no Storeroom key')).to_be(True)
    ruse.walk_ok = False
    expect(run_wait(storeroom.take_storeroom_key(ruse.log))).to_be(False)
    ruse.hold(ER_ITEM.STOREROOM_KEY)
    expect(run_wait(storeroom.unlock_storeroom(ruse.log))).to_be(False)
    ruse.pack = []
    ruse.walk_ok = True
    ruse.locs = [Fake(id=ER_LOC.KITCHEN_DRAWERS, name='Kitchen Drawers', actions=lambda: ['Open'], distance=lambda: 1, interact=lambda op: False)]
    expect(run_wait(storeroom.take_storeroom_key(ruse.log))).to_be(False)

    def opens(op):
        ruse.locs = [Fake(id=ER_LOC.KITCHEN_DRAWERS_OPEN, name='Kitchen Drawers', actions=lambda: ['Search'], distance=lambda: 1)]
        return True
    ruse.locs = [Fake(id=ER_LOC.KITCHEN_DRAWERS, name='Kitchen Drawers', actions=lambda: ['Open'], distance=lambda: 1, interact=opens)]
    expect(run_wait(storeroom.take_storeroom_key(ruse.log))).to_be(False)
    expect(prompts[-1]).to_be(ER_LOC.KITCHEN_DRAWERS_OPEN)

    ruse.hold(ER_ITEM.STOREROOM_KEY)

    def turns_key(step, log):
        ruse.pack = []
        return step.expect()
        yield
    spy_on(storeroom, 'prompt_loc', impl=turns_key)
    expect(run_wait(storeroom.unlock_storeroom(ruse.log))).to_be(True)

    ruse.hold(ER_ITEM.GOUTWEED)
    expect(run_wait(storeroom.take_goutweed(ruse.log))).to_be(True)
    ruse.pack = []
    spy_on(storeroom, 'prompt_loc', impl=lambda step, log: result(False))
    expect(run_wait(storeroom.take_goutweed(ruse.log))).to_be(False)
    expect(ruse.logged('knocked back from the goutweed crate (attempt 12/12)')).to_be(True)
    spy_on(storeroom, 'prompt_loc', impl=lambda step, log: result(True))
    expect(run_wait(storeroom.take_goutweed(ruse.log))).to_be(True)
    spy_on(storeroom, 'prompt_loc', impl=lambda step, log: result(step.id == ER_LOC.RACK))
    expect(run_wait(storeroom.retrieve_parrot(ruse.log))).to_be(True)


test('the drawers give the storeroom key, the key opens the door, and the crate is searched through the patrol', works_the_storeroom)


def talks_under_guard():
    ruse = Ruse(TROLLHEIM)
    guarded = []

    def guard(kind, threat, walk, log):
        guarded.append([kind, threat()])
        moved = yield from walk()
        return moved
    spy_on(travel, 'protected_walk', impl=guard)
    spy_on(travel, 'goto_npc', impl=lambda stop, hops, log: result(False))
    step = travel.guarded_talk(eadgar.EADGAR_TALK)
    expect(step.name).to_be('talk to Eadgar')
    expect(run_wait(step.run(ruse.log))).to_be(False)
    spy_on(travel, 'goto_npc', impl=lambda stop, hops, log: result(True))
    spy_on(travel, 'talk_through', impl=lambda npc, prefer, log: result(True))
    expect(run_wait(step.run(ruse.log))).to_be(True)
    expect(guarded).to_equal([['missiles', False], ['missiles', False]])


test('a talk on Trollheim walks to its NPC under the missile guard', talks_under_guard)


def decides_hands_and_warns():
    def snap(stage, inv_ids=None, bank_ids=None, bank_known=True, flags=None):
        return QuestSnapshot(journal='in_progress', stage=stage, progress=QuestProgress(stage, set(flags if flags is not None else [EADGAR_FLAG.EADGAR_FREED])),
                             inv={}, inv_ids=inv_ids or {}, bank={}, bank_ids=bank_ids or {}, bank_known=bank_known, tile=FALADOR)
    expect(eadgar.parrot_in_hand(snap(60, inv_ids={ER_ITEM.DRUNK_PARROT.id: 1}))).to_be(None)
    expect(eadgar.parrot_in_hand(snap(60, bank_known=False)).kind).to_be('scan_bank')
    expect(eadgar.parrot_in_hand(snap(60, bank_ids={ER_ITEM.DRUNK_PARROT.id: 1})).kind).to_be('withdraw')
    expect(eadgar.parrot_in_hand(snap(60)).kind).to_be('talk')
    expect(eadgar.fake_man_in_hand(snap(87, inv_ids={ER_ITEM.FAKE_MAN.id: 1}))).to_be(None)
    expect(eadgar.fake_man_in_hand(snap(87, bank_known=False)).kind).to_be('scan_bank')
    expect(eadgar.fake_man_in_hand(snap(87, bank_ids={ER_ITEM.FAKE_MAN.id: 1})).kind).to_be('withdraw')
    expect(eadgar.fake_man_in_hand(snap(87)).kind).to_be('talk')
    expect(eadgar.source_storeroom_key(snap(90, bank_ids={ER_ITEM.STOREROOM_KEY.id: 1})).kind).to_be('withdraw')
    lines = eadgar.observe(snap(70, flags=['need-grain:3']), eadgar.decide(snap(70, flags=['need-grain:3', EADGAR_FLAG.EADGAR_FREED])))
    expect(lines[1]).to_contain('grain=3')

    spy_on(skills, 'level', returns=1)
    expect(eadgar.warn_eadgar_readiness()).to_contain('Herblore 31')
    spy_on(skills, 'level', returns=99)
    expect(eadgar.warn_eadgar_readiness()).to_be(None)


test("the parrot and the fake man come from the pack, the bank or Eadgar, and the readiness warning names what's short", decides_hands_and_warns)
