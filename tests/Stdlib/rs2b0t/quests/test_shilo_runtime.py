"""Shilo Village's legs against spied facades: Mosol Rei and Trufitus, the mound and the fissure, Ah Za Rhoon's two
rooms and their scrolls, Zadimus, Bervirius' tomb and the crafts, Rashiliyia's tomb from its doors to the dolmen,
Jiminua's kit, the bones, and the journal reader, each through its success and its failures."""

import _core
import rs2004.quests.defs.shilo as shilo
import rs2004.quests.defs.shilo.ahzarhoon as ahzarhoon
import rs2004.quests.defs.shilo.cairn as cairn
import rs2004.quests.defs.shilo.gear as gear
import rs2004.quests.defs.shilo.journal as journal
import rs2004.quests.defs.shilo.rashtomb as rashtomb
import rs2004.quests.defs.shilo.start as start
import rs2004.quests.defs.shilo.supplies as supplies
from rs2004 import execution
from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import chat_dialog
from rs2004.entities import ground_items, locs, npcs
from rs2004.game import game, reader
from rs2004.geometry import Tile
from rs2004.items import equipment, inventory
from rs2004.quests.defs.shilo.areas import BONE_SPAWNS, SV_ITEM, SV_LOC, SV_NPC, SV_TILE, shilo_area
from rs2004.quests.defs.shilo.journal import SV_STAGE
from rs2004.quests.engine.types import QuestProgress, QuestSnapshot
from rs2004.tabs import quests
from rs2004.trade import shop
from rs2004.traversal import traversal

ARDOUGNE = Tile(2616, 3332, 0)


def result(value):
    return value
    yield


class Island:
    """The player about Karamja and its pockets: the pack, the scene, the area, and what each prompted loc does."""

    def __init__(self, area='karamja'):
        self.area = area
        self.at = SV_TILE.TRUFITUS
        self.pack = []
        self.locs = []
        self.ground = []
        self.npcs = []
        self.walk_ok = True
        self.walks = []
        self.lines = []
        self.prompted = []
        self.effects = {}
        self.dolmen_room = False
        self.fighting = False
        self.clock = 0
        self.status = 'in_progress'
        spy_on(game, 'tile', impl=lambda: self.at)
        spy_on(game, 'in_combat', impl=lambda: self.fighting)
        spy_on(locs, 'query', impl=querying(lambda: self.locs))
        spy_on(ground_items, 'query', impl=querying(lambda: self.ground))
        spy_on(npcs, 'query', impl=querying(lambda: self.npcs))
        spy_on(inventory, 'items', impl=lambda: self.pack)
        spy_on(sustain, 'run', impl=lambda: result(True))
        spy_on(quests, 'status', impl=lambda name: self.status)
        spy_on(_core, 'step_time', impl=self.now)
        spy_on(traversal, 'walk_resilient', impl=self.walk)
        for module in [ahzarhoon, cairn, rashtomb, start]:
            spy_on(module, 'here', impl=lambda: self.area)
        for module in [ahzarhoon, cairn, rashtomb]:
            spy_on(module, 'settle_scene', impl=instant_ticks)
            spy_on(module, 'prompt_loc', impl=self.prompt)
        for module in [ahzarhoon, cairn, rashtomb]:
            spy_on(module, 'use_on_loc', impl=self.use_on_loc)
        for module in [ahzarhoon, cairn]:
            spy_on(module, 'drive_until', impl=lambda expect, prefer, log, ms=30000: result(expect()))
        for module in [ahzarhoon, rashtomb, start]:
            spy_on(module, 'drive_choice', impl=lambda prefer, log: result(True))
        spy_on(rashtomb, 'in_dolmen_room', impl=lambda tile: self.dolmen_room)
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

    def prompt(self, step, log):
        """prompt_loc: the loc's effect runs, and the step's own expect judges it."""
        self.prompted.append(step.name)
        effect = self.effects.get(step.name)
        if effect is not None:
            effect()
        return step.expect()
        yield

    def use_on_loc(self, item_id, loc, prefer, expect, log):
        self.prompted.append(loc.name)
        effect = self.effects.get(item_id)
        if effect is not None:
            effect()
        return expect()
        yield

    def walk(self, tile, radius=2, attempts=None, timeout_ms=None, log=None):
        self.walks.append(tile)
        if self.walk_ok:
            self.at = tile
        return self.walk_ok
        yield

    def count(self, id):
        return sum([i.count for i in self.pack if i.id == id])

    def hold(self, item, count=1, use_on=None, interact=None):
        held = Fake(id=item.id, name=item.name, count=count, use_on=use_on if use_on is not None else (lambda other: True),
                    interact=interact if interact is not None else (lambda op: True))
        self.pack.append(held)
        return held

    def drop(self, item):
        self.pack = [held for held in self.pack if held.id != item.id]

    def gives(self, item, gone=None):
        def give(*args):
            if gone is not None:
                self.drop(gone)
            self.hold(item)
            return True
        return give

    def moves(self, area):
        def move(*args):
            self.area = area
            return True
        return move

    def loc(self, name, actions, interact=None):
        made = Fake(name=name, actions=lambda: actions, distance=lambda: 1, interact=interact if interact is not None else (lambda op: True))
        self.locs.append(made)
        return made

    def npc(self, name, actions=None, interact=None):
        made = Fake(name=name, actions=lambda: actions if actions is not None else ['Talk-to'], distance=lambda: 1,
                    interact=interact if interact is not None else (lambda op: True))
        self.npcs.append(made)
        return made

    def opens_chat(self):
        def use(other):
            self.chat.pages = ['continue']
            return True
        return use


def starts_the_quest():
    island = Island()
    island.hold(SV_ITEM.WAMPUM_BELT)
    expect(run_wait(start.take_wampum_belt(island.log))).to_be(True)
    island.pack = []
    island.walk_ok = False
    expect(run_wait(start.take_wampum_belt(island.log))).to_be(False)
    island.walk_ok = True
    spy_on(start, 'talk_strict', impl=lambda npc, prefer, log: result(False))
    expect(run_wait(start.take_wampum_belt(island.log))).to_be(False)

    def hands_belt(npc, prefer, log):
        island.hold(SV_ITEM.WAMPUM_BELT)
        return True
        yield
    spy_on(start, 'talk_strict', impl=hands_belt)
    expect(run_wait(start.take_wampum_belt(island.log))).to_be(True)

    island.pack = []
    expect(run_wait(start.start_quest(island.log))).to_be(False)
    expect(island.logged('no Wampum belt to show Trufitus')).to_be(True)
    belt = island.hold(SV_ITEM.WAMPUM_BELT, use_on=lambda other: False)
    island.walk_ok = False
    expect(run_wait(start.start_quest(island.log))).to_be(False)
    island.walk_ok = True
    expect(run_wait(start.start_quest(island.log))).to_be(False)
    expect(island.logged('Trufitus is not in range')).to_be(True)
    island.npc(SV_NPC.TRUFITUS)
    expect(run_wait(start.start_quest(island.log))).to_be(False)
    belt._fields['use_on'] = lambda other: True
    expect(run_wait(start.start_quest(island.log))).to_be(False)
    expect(island.logged('showing the belt opened no dialogue')).to_be(True)
    belt._fields['use_on'] = island.opens_chat()
    spy_on(start, 'drive_choice', impl=lambda prefer, log: result(False))
    expect(run_wait(start.start_quest(island.log))).to_be(False)

    def keeps_belt(prefer, log):
        island.drop(SV_ITEM.WAMPUM_BELT)
        return True
        yield
    spy_on(start, 'drive_choice', impl=keeps_belt)
    expect(run_wait(start.start_quest(island.log))).to_be(True)


test("Mosol Rei's belt is fetched and shown to Trufitus, the use-on that starts the quest", starts_the_quest)


def opens_the_fissure():
    island = Island()
    fissure = []

    def opened():
        if len(fissure) == 0:
            fissure.append(island.loc(SV_LOC.FISSURE, ['Search']))
    island.effects[SV_ITEM.SPADE.id] = opened
    expect(run_wait(ahzarhoon.dig_mound(island.log))).to_be(True)
    expect(run_wait(ahzarhoon.dig_mound(island.log))).to_be(True)
    expect(island.prompted).to_equal([SV_LOC.MOUND])

    island.locs = []
    expect(run_wait(ahzarhoon.light_fissure(island.log))).to_be(False)
    expect(island.logged('no lit candle to drop into the fissure')).to_be(True)
    expect(run_wait(ahzarhoon.rope_fissure(island.log))).to_be(False)
    expect(island.logged('no rope to tie to the fissure')).to_be(True)
    island.hold(SV_ITEM.LIT_CANDLE)
    island.hold(SV_ITEM.ROPE)
    expect(run_wait(ahzarhoon.light_fissure(island.log))).to_be(False)
    expect(run_wait(ahzarhoon.rope_fissure(island.log))).to_be(False)
    island.effects[SV_LOC.MOUND] = lambda: island.loc(SV_LOC.FISSURE, ['Search'])
    island.effects[SV_ITEM.LIT_CANDLE.id] = lambda: island.drop(SV_ITEM.LIT_CANDLE)
    island.effects[SV_ITEM.ROPE.id] = lambda: island.drop(SV_ITEM.ROPE)
    expect(run_wait(ahzarhoon.light_fissure(island.log))).to_be(True)
    expect(run_wait(ahzarhoon.rope_fissure(island.log))).to_be(True)

    island.locs = []
    island.effects = {}
    expect(run_wait(ahzarhoon.enter_fissure(island.log))).to_be(False)
    island.effects[SV_LOC.MOUND] = lambda: island.loc(SV_LOC.FISSURE, ['Search'])
    expect(run_wait(ahzarhoon.enter_fissure(island.log))).to_be(False)
    island.effects[SV_LOC.FISSURE] = island.moves('ahZaRhoonNorth')
    expect(run_wait(ahzarhoon.enter_fissure(island.log))).to_be(True)
    expect(run_wait(ahzarhoon.enter_fissure(island.log))).to_be(True)


test('the mound is dug, lit and roped, each fissure re-created by looking at the mound, then climbed down', opens_the_fissure)


def searches_ah_za_rhoon():
    island = Island()
    spy_on(ahzarhoon, 'enter_fissure', impl=lambda log: result(False))
    for leg in [ahzarhoon.take_tattered_scroll, ahzarhoon.take_crumpled_scroll, ahzarhoon.take_zadimus_corpse]:
        expect(run_wait(leg(island.log))).to_be(False)
    island.area = 'ahZaRhoonNorth'
    expect(run_wait(ahzarhoon.in_south_room(island.log))).to_be(False)
    island.effects[SV_LOC.CAVE_IN] = island.moves('ahZaRhoonSouth')
    island.effects[SV_LOC.LOOSE_ROCKS] = island.gives(SV_ITEM.TATTERED_SCROLL)
    island.effects[SV_LOC.OLD_SACKS] = island.gives(SV_ITEM.CRUMPLED_SCROLL)
    island.effects[SV_LOC.GALLOWS] = island.gives(SV_ITEM.ZADIMUS_CORPSE)
    for leg in [ahzarhoon.take_tattered_scroll, ahzarhoon.take_crumpled_scroll, ahzarhoon.take_zadimus_corpse]:
        expect(run_wait(leg(island.log))).to_be(True)
        expect(run_wait(leg(island.log))).to_be(True)
    expect(island.prompted).to_equal([SV_LOC.CAVE_IN, SV_LOC.CAVE_IN, SV_LOC.LOOSE_ROCKS, SV_LOC.OLD_SACKS, SV_LOC.GALLOWS])

    expect(run_wait(ahzarhoon.leave_ah_za_rhoon(island.log))).to_be(False)
    island.effects[SV_LOC.CAVE_IN] = island.moves('ahZaRhoonNorth')
    expect(run_wait(ahzarhoon.leave_ah_za_rhoon(island.log))).to_be(False)
    island.effects[SV_LOC.WATERFALL_ROCKS] = island.moves('karamja')
    expect(run_wait(ahzarhoon.leave_ah_za_rhoon(island.log))).to_be(True)
    expect(run_wait(ahzarhoon.leave_ah_za_rhoon(island.log))).to_be(True)


test("Ah Za Rhoon's south room gives up both scrolls and Zadimus, and the waterfall path leads back out", searches_ah_za_rhoon)


def reads_the_scrolls():
    island = Island()
    read = ahzarhoon.read_scroll(SV_ITEM.TATTERED_SCROLL.id)
    expect(run_wait(read(island.log))).to_be(False)
    expect(island.logged(f'no scroll {SV_ITEM.TATTERED_SCROLL.id} in the pack to read')).to_be(True)
    scroll = island.hold(SV_ITEM.TATTERED_SCROLL, interact=lambda op: False)
    expect(run_wait(read(island.log))).to_be(False)
    scroll._fields['interact'] = lambda op: True
    spy_on(ahzarhoon, 'drive_choice', impl=lambda prefer, log: result(False))
    expect(run_wait(read(island.log))).to_be(False)
    spy_on(ahzarhoon, 'drive_choice', impl=lambda prefer, log: result(True))
    modal = [355]
    spy_on(reader, 'modals', impl=lambda: Fake(main=modal[0]))
    closed = []

    def close():
        modal[0] = -1
        closed.append(1)
        return True
    spy_on(_core, 'close_interfaces', impl=close)
    expect(run_wait(read(island.log))).to_be(True)
    expect(closed).to_equal([1])
    expect(run_wait(read(island.log))).to_be(True)
    expect(closed).to_equal([1])


test("a scroll is read and its body, a main modal the dialogue can't see, is closed after", reads_the_scrolls)


def buries_zadimus():
    island = Island()
    island.hold(SV_ITEM.BONE_SHARD)
    expect(run_wait(ahzarhoon.bury_zadimus(island.log))).to_be(True)
    island.pack = []
    island.walk_ok = False
    expect(run_wait(ahzarhoon.bury_zadimus(island.log))).to_be(False)
    island.walk_ok = True
    spy_on(traversal, 'walk_resilient', impl=lambda tile, radius=2, attempts=None, timeout_ms=None, log=None: result(True))
    expect(run_wait(ahzarhoon.bury_zadimus(island.log))).to_be(False)
    expect(island.logged('not standing on the sacred ground yet')).to_be(True)
    island.at = SV_TILE.SACRED_GROUND
    expect(run_wait(ahzarhoon.bury_zadimus(island.log))).to_be(False)
    expect(island.logged('no Zadimus corpse to bury')).to_be(True)
    corpse = island.hold(SV_ITEM.ZADIMUS_CORPSE, interact=lambda op: False)
    expect(run_wait(ahzarhoon.bury_zadimus(island.log))).to_be(False)
    corpse._fields['interact'] = island.gives(SV_ITEM.BONE_SHARD, SV_ITEM.ZADIMUS_CORPSE)
    expect(run_wait(ahzarhoon.bury_zadimus(island.log))).to_be(True)


test("Zadimus is buried on the sacred ground behind Trufitus's hut, and the bone shard ends the step", buries_zadimus)


def works_bervirius_tomb():
    island = Island()
    expect(run_wait(cairn.leave_bervirius_tomb(island.log))).to_be(True)
    expect(run_wait(cairn.search_bervirius_dolmen(island.log))).to_be(False)
    expect(run_wait(cairn.deliver_corpse(island.log))).to_be(False)
    island.effects[SV_LOC.WELL_STACKED_ROCKS] = island.moves('berviriusTomb')
    island.effects[SV_LOC.BERVIRIUS_DOLMEN] = island.gives(SV_ITEM.SWORD_POMMEL)
    expect(run_wait(cairn.search_bervirius_dolmen(island.log))).to_be(True)
    expect(run_wait(cairn.search_bervirius_dolmen(island.log))).to_be(True)
    island.status = 'in_progress'
    expect(run_wait(cairn.deliver_corpse(island.log))).to_be(False)
    island.status = 'complete'
    expect(run_wait(cairn.deliver_corpse(island.log))).to_be(True)
    expect(run_wait(cairn.leave_bervirius_tomb(island.log))).to_be(False)
    island.effects[SV_LOC.HANDHOLDS] = island.moves('karamja')
    expect(run_wait(cairn.leave_bervirius_tomb(island.log))).to_be(True)

    island.pack = []
    expect(run_wait(cairn.craft_bone_beads(island.log))).to_be(False)
    expect(island.logged(f'missing {SV_ITEM.CHISEL.id} or {SV_ITEM.SWORD_POMMEL.id} for the craft')).to_be(True)
    chisel = island.hold(SV_ITEM.CHISEL, use_on=lambda other: False)
    island.hold(SV_ITEM.SWORD_POMMEL)
    expect(run_wait(cairn.craft_bone_beads(island.log))).to_be(False)
    chisel._fields['use_on'] = island.gives(SV_ITEM.BONE_BEADS, SV_ITEM.SWORD_POMMEL)
    expect(run_wait(cairn.craft_bone_beads(island.log))).to_be(True)
    expect(run_wait(cairn.craft_bone_beads(island.log))).to_be(True)
    island.hold(SV_ITEM.BRONZE_WIRE, use_on=island.gives(SV_ITEM.DEAD_BEADS, SV_ITEM.BONE_BEADS))
    expect(run_wait(cairn.craft_dead_beads(island.log))).to_be(True)
    expect(run_wait(cairn.craft_bone_key(island.log))).to_be(False)


test("Bervirius' tomb is crawled into for the pommel and the remains, and the chisel cuts the beads and the key", works_bervirius_tomb)


def opens_rashiliyias_tomb():
    island = Island()
    expect(run_wait(rashtomb.search_carved_doors(island.log))).to_be(False)
    expect(island.prompted).to_equal([SV_LOC.PALM_TREE])
    doors = island.loc(SV_LOC.CARVED_DOORS, ['Search'], interact=lambda op: False)
    island.walk_ok = False
    expect(run_wait(rashtomb.search_carved_doors(island.log))).to_be(False)
    island.walk_ok = True
    expect(run_wait(rashtomb.search_carved_doors(island.log))).to_be(False)
    doors._fields['interact'] = lambda op: True
    expect(run_wait(rashtomb.search_carved_doors(island.log))).to_be(False)
    doors._fields['interact'] = island.opens_chat()
    expect(run_wait(rashtomb.search_carved_doors(island.log))).to_be(True)
    doors._fields['actions'] = lambda: ['Open']
    expect(run_wait(rashtomb.search_carved_doors(island.log))).to_be(False)
    expect(island.logged('the carved doors closed again before they could be searched')).to_be(True)

    island.locs = []
    expect(run_wait(rashtomb.unlock_carved_doors(island.log))).to_be(False)
    island.loc(SV_LOC.CARVED_DOORS, ['Search'])
    island.effects[SV_ITEM.BONE_KEY.id] = lambda: island.loc(SV_LOC.HILLSIDE_ENTRANCE, ['Enter'])
    expect(run_wait(rashtomb.unlock_carved_doors(island.log))).to_be(True)
    expect(run_wait(rashtomb.unlock_carved_doors(island.log))).to_be(True)

    # After a restart the unlocked doors are shut again, with plain Open.
    island.locs = []
    island.loc(SV_LOC.CARVED_DOORS, ['Open'], interact=lambda op: island.loc(SV_LOC.HILLSIDE_ENTRANCE, ['Enter']) is not None)
    expect(run_wait(rashtomb.enter_rash_tomb(island.log))).to_be(False)
    island.effects[SV_LOC.HILLSIDE_ENTRANCE] = island.moves('rashEntry')
    expect(run_wait(rashtomb.enter_rash_tomb(island.log))).to_be(True)
    expect(run_wait(rashtomb.enter_rash_tomb(island.log))).to_be(True)
    island.area = 'karamja'
    island.locs = []
    expect(run_wait(rashtomb.enter_rash_tomb(island.log))).to_be(False)


test("the carved doors are revealed from the palm trees, searched for their lock and opened with the bone key", opens_rashiliyias_tomb)


def leaves_by_the_tomb_exit():
    island = Island('karamja')
    expect(run_wait(rashtomb.leave_rash_tomb(island.log))).to_be(True)
    island.area = 'rashEntry'
    expect(run_wait(rashtomb.leave_rash_tomb(island.log))).to_be(False)
    island.hold(SV_ITEM.BONE_KEY)
    expect(run_wait(rashtomb.leave_rash_tomb(island.log))).to_be(False)
    expect(island.prompted).to_equal([SV_LOC.TOMB_EXIT, SV_LOC.TOMB_EXIT])
    island.effects[SV_ITEM.BONE_KEY.id] = island.moves('karamja')
    expect(run_wait(rashtomb.leave_rash_tomb(island.log))).to_be(True)
    island.pack = []
    island.area = 'rashEntry'
    island.effects[SV_LOC.TOMB_EXIT] = island.moves('karamja')
    expect(run_wait(rashtomb.leave_rash_tomb(island.log))).to_be(True)


test("the tomb exit refuses the bone key's holder, so the key is used on it instead", leaves_by_the_tomb_exit)


def crosses_the_gate_and_rocks():
    island = Island('rashEntry')
    worn = [False]
    spy_on(equipment, 'contains', impl=lambda name: worn[0])
    expect(run_wait(rashtomb.pass_gate('out', island.log))).to_be(True)
    expect(run_wait(rashtomb.pass_gate('in', island.log))).to_be(False)
    expect(island.logged('the Beads of the Dead are not worn')).to_be(True)
    worn[0] = True
    expect(run_wait(rashtomb.pass_gate('in', island.log))).to_be(False)
    island.effects[SV_LOC.ANCIENT_GATE] = island.moves('rashLedge')
    expect(run_wait(rashtomb.pass_gate('in', island.log))).to_be(True)
    gate = island.loc(SV_LOC.ANCIENT_GATE, ['Open'], interact=lambda op: False)
    expect(run_wait(rashtomb.pass_gate('out', island.log))).to_be(False)
    gate._fields['interact'] = lambda op: True
    expect(run_wait(rashtomb.pass_gate('out', island.log))).to_be(False)
    gate._fields['interact'] = island.moves('rashEntry')
    expect(run_wait(rashtomb.pass_gate('out', island.log))).to_be(True)

    island.area = 'rashLedge'
    expect(run_wait(rashtomb.climb_rash_rocks('up', island.log))).to_be(True)
    expect(run_wait(rashtomb.climb_rash_rocks('down', island.log))).to_be(False)
    expect(island.logged('no climbable rocks in range going down')).to_be(True)
    rocks = island.loc(SV_LOC.RASH_ROCKS, ['Climb'], interact=lambda op: False)
    expect(run_wait(rashtomb.climb_rash_rocks('down', island.log))).to_be(False)
    rocks._fields['interact'] = lambda op: True
    expect(run_wait(rashtomb.climb_rash_rocks('down', island.log))).to_be(False)
    rocks._fields['interact'] = island.moves('rashInner')
    expect(run_wait(rashtomb.climb_rash_rocks('down', island.log))).to_be(True)


test("the ancient gate is crossed only with the beads worn, and the rocks climbed from wherever it dropped us", crosses_the_gate_and_rocks)


def places_the_bones():
    island = Island('rashInner')
    expect(run_wait(rashtomb.place_bone(island.log))).to_be(False)
    expect(island.logged('no bones left for the door recesses')).to_be(True)
    island.hold(SV_ITEM.BONES, 3)
    expect(run_wait(rashtomb.place_bone(island.log))).to_be(False)

    def recess():
        island.pack[0]._fields['count'] -= 1
    island.effects[SV_ITEM.BONES.id] = recess
    expect(run_wait(rashtomb.place_bone(island.log))).to_be(True)
    expect(island.count(SV_ITEM.BONES.id)).to_be(2)


test('each bone goes into one recess of the skeletal doors', places_the_bones)


def crosses_the_skeletal_doors():
    island = Island('rashInner')
    island.dolmen_room = True
    expect(run_wait(rashtomb.cross_tomb_doors('north', island.log))).to_be(True)
    island.walk_ok = False
    expect(run_wait(rashtomb.cross_tomb_doors('south', island.log))).to_be(False)
    island.walk_ok = True
    expect(run_wait(rashtomb.cross_tomb_doors('south', island.log))).to_be(False)
    expect(island.logged('no skeletal doors in range to cross south')).to_be(True)
    doors = island.loc(SV_LOC.TOMB_DOORS, ['Open'], interact=lambda op: False)
    expect(run_wait(rashtomb.cross_tomb_doors('south', island.log))).to_be(False)
    doors._fields['interact'] = lambda op: True
    expect(run_wait(rashtomb.cross_tomb_doors('south', island.log))).to_be(False)

    def through(op):
        island.dolmen_room = not island.dolmen_room
        return True
    doors._fields['interact'] = through
    expect(run_wait(rashtomb.cross_tomb_doors('south', island.log))).to_be(True)

    island.dolmen_room = True
    island.area = 'karamja'
    expect(run_wait(rashtomb.leave_tomb_chamber(island.log))).to_be(True)
    island.area = 'rashInner'
    spy_on(rashtomb, 'cross_tomb_doors', impl=lambda dir, log: result(False))
    expect(run_wait(rashtomb.leave_tomb_chamber(island.log))).to_be(False)
    spy_on(rashtomb, 'cross_tomb_doors', impl=lambda dir, log: result(True))
    island.walk_ok = False
    expect(run_wait(rashtomb.leave_tomb_chamber(island.log))).to_be(False)
    island.walk_ok = True
    spy_on(rashtomb, 'climb_rash_rocks', impl=lambda dir, log: result(dir == 'up'))
    expect(run_wait(rashtomb.leave_tomb_chamber(island.log))).to_be(True)


test('the skeletal doors are opened for every crossing, and the chamber is left by the doors and the rocks', crosses_the_skeletal_doors)


def works_the_tomb_dolmen():
    island = Island('rashInner')
    island.hold(SV_ITEM.RASH_CORPSE)
    expect(run_wait(rashtomb.work_the_dolmen(island.log))).to_be(True)
    island.pack = []
    spy_on(rashtomb, 'cross_tomb_doors', impl=lambda dir, log: result(False))
    expect(run_wait(rashtomb.work_the_dolmen(island.log))).to_be(False)
    spy_on(rashtomb, 'cross_tomb_doors', impl=lambda dir, log: result(True))
    expect(run_wait(rashtomb.work_the_dolmen(island.log))).to_be(False)
    expect(island.prompted).to_equal([SV_LOC.RASH_DOLMEN])
    island.effects[SV_LOC.RASH_DOLMEN] = island.gives(SV_ITEM.RASH_CORPSE)
    expect(run_wait(rashtomb.work_the_dolmen(island.log))).to_be(True)

    island.pack = []
    hits = []

    def attack(op):
        hits.append(op)
        island.fighting = True
        if len(hits) == 2:
            island.npcs = []
        return True

    def summon():
        island.npc(SV_NPC.NAZASTAROOL, ['Attack'], interact=attack)
    island.effects[SV_LOC.RASH_DOLMEN] = summon
    original = island.now

    def now():
        island.fighting = False
        return original()
    spy_on(_core, 'step_time', impl=now)
    expect(run_wait(rashtomb.work_the_dolmen(island.log))).to_be(True)
    expect(len(hits)).to_be(2)
    summon()
    spy_on(game, 'in_combat', returns=True)
    expect(run_wait(rashtomb.work_the_dolmen(island.log))).to_be(False)
    expect(island.logged('Nazastarool outlasted the fight budget')).to_be(True)


test('the tomb dolmen is searched, each Nazastarool it summons fought down, until the remains come up', works_the_tomb_dolmen)


def buys_and_makes_the_kit():
    island = Island()
    wanted = supplies.kit_shortfall(QuestSnapshot(inv_ids={}), [SV_ITEM.ROPE, SV_ITEM.SPADE])
    step = supplies.stock_up(wanted)
    expect(step.name).to_be('buy 1× Rope, 1× Spade from Jiminua')
    island.walk_ok = False
    expect(run_wait(step.run(island.log))).to_be(False)
    island.walk_ok = True
    spy_on(shop, 'open', impl=lambda npc: result(False))
    expect(run_wait(step.run(island.log))).to_be(False)
    expect(island.logged("could not open Jiminua's shop")).to_be(True)
    spy_on(shop, 'open', impl=lambda npc: result(True))
    spy_on(shop, 'close', impl=lambda: result(True))
    spy_on(shop, 'buy', impl=lambda name, qty: result(1 if name == 'Rope' else 0))
    island.hold(SV_ITEM.SPADE)
    expect(run_wait(step.run(island.log))).to_be(True)
    island.pack = []
    expect(run_wait(step.run(island.log))).to_be(True)
    expect(island.logged('Jiminua is out of Spade, or the purse is empty')).to_be(True)

    expect(run_wait(supplies.light_candle(island.log))).to_be(False)
    expect(island.logged('no candle or tinderbox to light with')).to_be(True)
    candle = island.hold(SV_ITEM.CANDLE, use_on=lambda other: False)
    island.hold(SV_ITEM.TINDERBOX)
    expect(run_wait(supplies.light_candle(island.log))).to_be(False)
    candle._fields['use_on'] = island.gives(SV_ITEM.LIT_CANDLE, SV_ITEM.CANDLE)
    expect(run_wait(supplies.light_candle(island.log))).to_be(True)

    island.pack = []
    island.walk_ok = False
    expect(run_wait(supplies.smith_bronze_wire(island.log))).to_be(False)
    island.walk_ok = True
    expect(run_wait(supplies.smith_bronze_wire(island.log))).to_be(False)
    expect(island.logged('no bronze bar in the pack, or no anvil in range')).to_be(True)
    bar = island.hold(SV_ITEM.BRONZE_BAR, use_on=lambda other: False)
    island.loc('Anvil', [])
    expect(run_wait(supplies.smith_bronze_wire(island.log))).to_be(False)
    bar._fields['use_on'] = lambda other: True
    panel = [False]
    spy_on(chat_dialog, 'is_main_make_panel', impl=lambda: panel[0])
    spy_on(chat_dialog, 'main_make_products', returns=['Bronze nails'])
    expect(run_wait(supplies.smith_bronze_wire(island.log))).to_be(False)
    expect(island.logged('the anvil panel never opened')).to_be(True)
    panel[0] = True
    spy_on(chat_dialog, 'make_from_panel', impl=lambda name: result(False))
    expect(run_wait(supplies.smith_bronze_wire(island.log))).to_be(False)
    expect(island.logged("no 'Bronze wire' on the anvil panel: Bronze nails")).to_be(True)
    spy_on(chat_dialog, 'make_from_panel', impl=lambda name: result(island.gives(SV_ITEM.BRONZE_WIRE, SV_ITEM.BRONZE_BAR)()))
    expect(run_wait(supplies.smith_bronze_wire(island.log))).to_be(True)
    expect(run_wait(supplies.smith_bronze_wire(island.log))).to_be(True)


test("Jiminua's kit is bought in one visit, the candle lit and the bronze bar smithed into wire", buys_and_makes_the_kit)


def gathers_the_bones():
    island = Island()
    island.hold(SV_ITEM.BONES, 3)
    expect(run_wait(supplies.gather_bones(3, island.log))).to_be(True)
    island.pack = []
    island.walk_ok = False
    expect(run_wait(supplies.gather_bones(3, island.log))).to_be(False)
    expect(len(island.walks)).to_be(len(BONE_SPAWNS))
    island.walk_ok = True
    pile = Fake(name=SV_ITEM.BONES.name, distance=lambda: 1, interact=island.gives(SV_ITEM.BONES))
    island.ground = [pile]
    expect(run_wait(supplies.gather_bones(2, island.log))).to_be(True)
    pile._fields['interact'] = lambda op: True
    expect(run_wait(supplies.gather_bones(5, island.log))).to_be(False)

    snap = QuestSnapshot(inv={}, inv_ids={}, bank={}, bank_ids={SV_ITEM.BONES.id: 9}, bank_known=False)
    expect(supplies.source_bones(snap, 3).kind).to_be('scan_bank')
    expect(supplies.source_bones(snap.with_fields({'bank_known': True}), 3).items[0]['qty']).to_be(3)
    step = supplies.source_bones(snap.with_fields({'bank_known': True, 'bank_ids': {}}), 3)
    spy_on(supplies, 'gather_bones', impl=lambda want, log: result(want == 3))
    expect(run_wait(step.run(island.log))).to_be(True)
    expect(supplies.source_food(snap, 4).kind).to_be('scan_bank')
    expect(supplies.source_coins(snap, 2000).kind).to_be('scan_bank')
    expect(supplies.source_lit_candle(QuestSnapshot(inv_ids={SV_ITEM.CANDLE.id: 1, SV_ITEM.TINDERBOX.id: 1})).name).to_be('light the candle')
    expect(supplies.source_bronze_wire(QuestSnapshot(inv_ids={SV_ITEM.BRONZE_BAR.id: 1, SV_ITEM.HAMMER.id: 1})).name).to_be('smith the bronze bar into wire')


test('the tomb bones come from the bank, or are picked up across the battlefield spawns', gathers_the_bones)


def snap_at(area_tile, stage, inv_ids=None, bank_ids=None, worn_ids=None, flags=None):
    return QuestSnapshot(**{
        'journal': 'in_progress',
        'inv': {},
        'inv_ids': inv_ids if inv_ids is not None else {},
        'worn': set(),
        'worn_ids': worn_ids if worn_ids is not None else set(),
        'bank': {},
        'bank_ids': bank_ids if bank_ids is not None else {},
        'bank_known': True,
        'stage': stage,
        'progress': QuestProgress(stage, set(flags if flags is not None else [])),
        'tile': area_tile,
        'free_slots': 10,
    })


def decides_the_corners():
    pockets = [['berviriusTomb', "climb out of Bervirius' tomb"], ['rashLedge', 'open the ancient gate back out'],
               ['rashInner', 'leave the tomb chamber'], ['rashEntry', "unlock Rashiliyia's tomb exit"]]
    for area, name in pockets:
        expect(shilo.escape_pocket(area).name).to_be(name)
    expect(shilo.escape_pocket('karamja')).to_be(None)
    expect(shilo.on_karamja(None)).to_be(False)
    expect(shilo_area(Tile(3200, 5000, 0))).to_be('unknown')
    island = Island('rashLedge')
    gates = []
    spy_on(shilo, 'pass_gate', impl=lambda dir, log: result(gates.append(dir) is None))
    expect(run_wait(shilo.escape_pocket('rashLedge').run(island.log))).to_be(True)
    expect(gates).to_equal(['out'])

    beads = SV_ITEM.DEAD_BEADS.id
    karamja = SV_TILE.TRUFITUS
    expect(shilo.need_beads(snap_at(karamja, SV_STAGE.UNLOCKED_TOMBDOOR, bank_ids={beads: 1}), 'karamja').kind).to_be('withdraw')
    kit = {SV_ITEM.CHISEL.id: 1, SV_ITEM.BRONZE_WIRE.id: 1}
    expect(shilo.need_beads(snap_at(karamja, SV_STAGE.UNLOCKED_TOMBDOOR, kit, {SV_ITEM.SWORD_POMMEL.id: 1}), 'karamja').kind).to_be('withdraw')
    step = shilo.need_beads(snap_at(karamja, SV_STAGE.UNLOCKED_TOMBDOOR, kit), 'karamja')
    expect(step.name).to_be("search the dolmen in Bervirius' tomb")
    step = shilo.stage_tomb(snap_at(karamja, SV_STAGE.UNLOCKED_RASH_TOMB, kit), 'karamja')
    expect(step.name).to_be("search the dolmen in Bervirius' tomb")

    worn = set([beads])
    corpse = SV_ITEM.RASH_CORPSE.id
    expect(shilo.stage_boss(snap_at(karamja, SV_STAGE.UNLOCKED_TOMBDOOR, bank_ids={corpse: 1}, worn_ids=worn), 'karamja').kind).to_be('withdraw')
    step = shilo.stage_boss(snap_at(karamja, SV_STAGE.UNLOCKED_TOMBDOOR, {corpse: 1}, worn_ids=worn), 'karamja')
    expect(step.name).to_be("lay the remains on Bervirius' dolmen")
    for area, name in [['rashInner', 'search the tomb dolmen'], ['rashLedge', 'climb down to the tomb chamber'], ['rashEntry', 'open the ancient gate']]:
        expect(shilo.stage_boss(snap_at(karamja, SV_STAGE.UNLOCKED_TOMBDOOR, worn_ids=worn), area).name).to_be(name)
    step = shilo.stage_boss(snap_at(karamja, SV_STAGE.UNLOCKED_TOMBDOOR, worn_ids=worn), 'karamja')
    expect(step.reason).to_contain('bank has no food')
    fed = snap_at(karamja, SV_STAGE.UNLOCKED_TOMBDOOR, worn_ids=worn).with_fields({'inv': {'lobster': 8}})
    expect(shilo.stage_boss(fed, 'karamja').name).to_be("enter Rashiliyia's tomb")

    spy_on(shilo, 'combat_gear', returns=None)
    expect(shilo.decide(snap_at(karamja, SV_STAGE.COMPLETE)).kind).to_be('done')
    expect(shilo.decide(snap_at(karamja, 2)).reason).to_be('Shilo Village stage 2 is not implemented')


test("Shilo's decide climbs out of each pocket, recovers banked quest items, and fights only with the beads on", decides_the_corners)


def wears_carried_gear():
    island = Island()
    spy_on(equipment, 'contains', returns=True)
    spy_on(equipment, 'equip', impl=lambda name: result(False))
    expect(run_wait(gear.wear_carried(['Rune scimitar'])(island.log))).to_be(True)
    expect(island.lines).to_equal([])
    gear.reset_combat_gear()
    snap = QuestSnapshot(inv={'rope': 1}, inv_ids={SV_ITEM.ROPE.id: 1}, worn=set(), worn_ids=set(), bank={'rune scimitar': 1},
                         bank_ids={}, bank_known=True, free_slots=0)
    expect(gear.combat_gear(snap).reason).to_be('need a free inventory slot for combat gear')


test('worn gear is left on, and a full pack of quest items waits rather than banking them for a sword', wears_carried_gear)


def reads_the_journal():
    island = Island()
    state = {'text': 'I climbed down the rope into Ah Za Rhoon', 'modal': 229, 'closed': 0}
    spy_on(quests, 'journal', impl=lambda name: result([state['text']]))
    spy_on(reader, 'modals', impl=lambda: Fake(main=state['modal']))

    def close():
        state['modal'] = -1
        state['closed'] += 1
        return True
    spy_on(_core, 'close_interfaces', impl=close)
    expect(run_wait(journal.read_shilo_progress()).stage).to_be(SV_STAGE.ENTERED_AH_ZA_RHOON)
    expect(state['closed']).to_be(1)
    island.status = 'complete'
    expect(run_wait(journal.read_shilo_progress()).stage).to_be(SV_STAGE.COMPLETE)
    island.status = 'not_started'
    expect(run_wait(journal.read_shilo_progress()).stage).to_be(SV_STAGE.NOT_STARTED)
    island.status = 'unknown'
    expect(run_wait(journal.read_shilo_progress())).to_be(None)


test("the journal reader closes a box left on main before it hands the page's stage over", reads_the_journal)
