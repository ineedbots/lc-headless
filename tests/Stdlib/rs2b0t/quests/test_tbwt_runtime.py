"""Tai Bwo Wannai Trio's legs against spied facades: the long talks and the use-ons, the four brothers' errands, the
bait and the Karambwan, the banana and the rum, the jungle fire, the hunts, the Jogre bones, the kit, and the journal
reader, each through its success and its failures."""

import _core
import rs2004.quests.defs.tbwt as tbwt
import rs2004.quests.defs.tbwt.brothers as brothers
import rs2004.quests.defs.tbwt.crafting as crafting
import rs2004.quests.defs.tbwt.journal as journal
import rs2004.quests.defs.tbwt.supplies as supplies
import rs2004.quests.defs.tbwt.talk as talk
from rs2004 import execution
from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import chat_dialog
from rs2004.entities import ground_items, locs, npcs
from rs2004.game import game, reader
from rs2004.geometry import Tile
from rs2004.items import equipment, inventory
from rs2004.messages import game_messages
from rs2004.quests.defs.tbwt.areas import TB_ID, TB_LOC, TB_LUBUFU, TB_MAIN, TB_NAME, TB_NPC, TB_POTIONS, TB_SPEARS, TB_TAMAYU, TB_TIADECHE, TB_TILE, TB_TINSAY, TB_VARP
from rs2004.quests.defs.tbwt.journal import TB_FLAG
from rs2004.quests.engine.types import QuestProgress, QuestSnapshot
from rs2004.quests.food import quest_food
from rs2004.tabs import quests
from rs2004.trade import shop
from rs2004.traversal import traversal

VILLAGE = Tile(2780, 3087, 0)


def result(value):
    return value
    yield


class Legs:
    """Stand-in legs that record their calls, each answering from ok, True unless told otherwise."""

    def __init__(self):
        self.calls = []
        self.ok = {}

    def talk(self, npc, anchor, prefer, log, quiet_ticks=6):
        self.calls.append([npc, list(prefer), quiet_ticks])
        return self.ok.get(npc, True)
        yield

    def use(self, item_id, npc, anchor, prefer, log, quiet_ticks=None):
        self.calls.append([item_id, npc, quiet_ticks])
        return self.ok.get(npc, True)
        yield


class Jungle:
    """The player about Karamja, with the pack, the scene, the clock and the chat."""

    def __init__(self, at):
        self.at = at
        self.pack = []
        self.locs = []
        self.ground = []
        self.npcs = []
        self.walk_ok = True
        self.walks = []
        self.lines = []
        self.clock = 0
        self.varps = {}
        self.refused = False
        spy_on(game, 'tile', impl=lambda: self.at)
        spy_on(reader, 'varp', impl=lambda id: self.varps.get(id, 0))
        spy_on(locs, 'query', impl=querying(lambda: self.locs))
        spy_on(ground_items, 'query', impl=querying(lambda: self.ground))
        spy_on(npcs, 'query', impl=querying(lambda: self.npcs))
        spy_on(npcs, 'all', impl=lambda: self.npcs)
        spy_on(inventory, 'items', impl=lambda: self.pack)
        spy_on(inventory, 'free', impl=lambda: 28 - len(self.pack))
        spy_on(inventory, 'count', impl=lambda name: sum([i.count for i in self.pack if i.name == name]))
        spy_on(inventory, 'first', impl=lambda name: ([i for i in self.pack if i.name == name] or [None])[0])
        spy_on(sustain, 'run', impl=lambda: result(True))
        spy_on(game_messages, 'mark', returns=7)
        spy_on(game_messages, 'saw_since', impl=lambda mark, text: self.refused)
        spy_on(_core, 'step_time', impl=self.now)
        spy_on(traversal, 'walk_resilient', impl=self.walk)
        for module in [crafting, talk]:
            spy_on(module, 'settle_scene', impl=instant_ticks)
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

    def walk(self, tile, radius=2, attempts=None, timeout_ms=None, log=None):
        self.walks.append(tile)
        if self.walk_ok:
            self.at = tile
        return self.walk_ok
        yield

    def count(self, id):
        return sum([i.count for i in self.pack if i.id == id])

    def hold(self, id, count=1, name=None, use_on=None, interact=None):
        held = Fake(id=id, name=name, count=count, use_on=use_on if use_on is not None else (lambda other: True),
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

    def drops(self, id):
        return lambda op: self.drop(id) or True

    def item(self, id, interact=None):
        made = Fake(id=id, distance=lambda: 1, interact=interact if interact is not None else self.gives(id))
        self.ground.append(made)
        return made

    def npc(self, name, actions=None, index=1, interact=None):
        made = Fake(name=name, index=index, actions=lambda: actions if actions is not None else ['Talk-to'], distance=lambda: 1,
                    targets_another_player=lambda: False, interact=interact if interact is not None else (lambda op: True))
        self.npcs.append(made)
        return made

    def opens_chat(self, pages):
        def use(other):
            self.chat.pages = list(pages)
            return True
        return use


def drives_past_the_gaps():
    jungle = Jungle(VILLAGE)
    jungle.chat.pages = ['continue', ['How old are you?', 'Bye'], 'continue']
    expect(run_wait(talk.drive_fully(['How old are you?'], jungle.log))).to_be(True)
    expect(jungle.chat.chosen).to_equal(['How old are you?'])
    jungle.chat.pages = [['Bye']]
    expect(run_wait(talk.drive_fully(['Yes'], jungle.log))).to_be(False)
    expect(jungle.logged('no preferred option in [Bye]')).to_be(True)
    spy_on(chat_dialog, 'is_open', returns=True)
    spy_on(chat_dialog, 'can_continue', returns=False)
    spy_on(chat_dialog, 'options', returns=[])
    expect(run_wait(talk.drive_fully([], jungle.log, 2))).to_be(False)


test("a brother's talk is driven past the scripted gaps where the chat closes and re-opens", drives_past_the_gaps)


def talks_and_uses_fully():
    jungle = Jungle(VILLAGE)
    jungle.walk_ok = False
    expect(run_wait(talk.talk_fully(TB_NPC.LUBUFU, TB_TILE.LUBUFU, [], jungle.log))).to_be(False)
    expect(run_wait(talk.use_on_npc(TB_ID.VESSEL, TB_NPC.TINSAY, TB_TILE.TINSAY, [], jungle.log))).to_be(False)
    jungle.walk_ok = True
    opens = [False, False]
    spy_on(talk, 'open_dialogue', impl=lambda name, log: result(opens.pop(0) if len(opens) > 0 else True))
    expect(run_wait(talk.talk_fully(TB_NPC.LUBUFU, TB_TILE.LUBUFU, [], jungle.log))).to_be(False)
    opens.extend([False, True])
    spy_on(talk, 'drive_fully', impl=lambda prefer, log, quiet_ticks=6: result(quiet_ticks))
    expect(run_wait(talk.talk_fully(TB_NPC.LUBUFU, TB_TILE.LUBUFU, [], jungle.log, 9))).to_be(9)

    expect(run_wait(talk.use_on_npc(TB_ID.VESSEL, TB_NPC.TINSAY, TB_TILE.TINSAY, [], jungle.log))).to_be(False)
    expect(jungle.logged(f"no 'Tinsay' in reach, or no item {TB_ID.VESSEL} in the pack")).to_be(True)
    jungle.npc(TB_NPC.TINSAY)
    vessel = jungle.hold(TB_ID.VESSEL, use_on=lambda other: False)
    expect(run_wait(talk.use_on_npc(TB_ID.VESSEL, TB_NPC.TINSAY, TB_TILE.TINSAY, [], jungle.log))).to_be(False)
    vessel._fields['use_on'] = lambda other: True
    expect(run_wait(talk.use_on_npc(TB_ID.VESSEL, TB_NPC.TINSAY, TB_TILE.TINSAY, [], jungle.log))).to_be(False)
    expect(jungle.logged(f"'Tinsay' did not answer item {TB_ID.VESSEL}")).to_be(True)
    vessel._fields['use_on'] = jungle.opens_chat(['continue'])
    expect(run_wait(talk.use_on_npc(TB_ID.VESSEL, TB_NPC.TINSAY, TB_TILE.TINSAY, [], jungle.log))).to_be(talk.LONG_GAP)


test('a talk or a use-on is aimed twice at a wandering brother, then driven to its end', talks_and_uses_fully)


def runs_the_brothers_errands():
    jungle = Jungle(VILLAGE)
    legs = Legs()
    spy_on(brothers, 'talk_fully', impl=legs.talk)
    spy_on(brothers, 'use_on_npc', impl=legs.use)
    for leg in [brothers.start_quest, brothers.claim_reward, brothers.meet_tiadeche, brothers.give_manual, brothers.meet_tinsay,
                brothers.meet_tamayu, brothers.hunt_shaikahan, brothers.give_tinsay(TB_ID.SANDWICH), brothers.give_tamayu(TB_ID.MONKEY_CORPSE)]:
        expect(run_wait(leg(jungle.log))).to_be(True)
    expect(legs.calls[6]).to_equal([TB_NPC.TAMAYU, ['When will you succeed?', 'Take me on your next hunt', 'Yes'], talk.CUTSCENE_GAP])

    legs.ok[TB_NPC.LUBUFU] = False
    expect(run_wait(brothers.meet_lubufu(jungle.log))).to_be(False)
    legs.ok[TB_NPC.LUBUFU] = True
    expect(run_wait(brothers.meet_lubufu(jungle.log))).to_be(True)

    expect(run_wait(brothers.give_karambwanji(jungle.log))).to_be(False)
    expect(jungle.logged('no Raw karambwanji in the pack to hand over')).to_be(True)
    jungle.hold(TB_ID.RAW_KARAMBWANJI, 20)
    legs.ok[TB_NPC.LUBUFU] = False
    expect(run_wait(brothers.give_karambwanji(jungle.log))).to_be(False)
    legs.ok[TB_NPC.LUBUFU] = True
    expect(run_wait(brothers.give_karambwanji(jungle.log))).to_be(False)

    def counts(npc, anchor, prefer, log, quiet_ticks=6):
        jungle.drop(TB_ID.RAW_KARAMBWANJI)
        return True
        yield
    spy_on(brothers, 'talk_fully', impl=counts)
    expect(run_wait(brothers.give_karambwanji(jungle.log))).to_be(True)

    spy_on(brothers, 'talk_fully', impl=legs.talk)
    legs.ok[TB_NPC.LUBUFU] = False
    expect(run_wait(brothers.become_apprentice(jungle.log))).to_be(False)
    expect(run_wait(brothers.spare_vessel(jungle.log))).to_be(False)
    legs.ok[TB_NPC.LUBUFU] = True
    expect(run_wait(brothers.become_apprentice(jungle.log))).to_be(False)
    expect(run_wait(brothers.spare_vessel(jungle.log))).to_be(False)
    jungle.hold(TB_ID.VESSEL)
    expect(run_wait(brothers.become_apprentice(jungle.log))).to_be(True)
    expect(run_wait(brothers.spare_vessel(jungle.log))).to_be(True)

    legs.ok[TB_NPC.TIADECHE] = False
    expect(run_wait(brothers.tiadeche_catch(jungle.log))).to_be(False)
    legs.ok[TB_NPC.TIADECHE] = True
    expect(run_wait(brothers.tiadeche_catch(jungle.log))).to_be(False)
    jungle.varps[TB_VARP.TIADECHE] = TB_TIADECHE.REQUEST_MANUAL
    expect(run_wait(brothers.tiadeche_catch(jungle.log))).to_be(True)


test("each brother's errand is one long talk or a use-on, and Lubufu's need the pack to change", runs_the_brothers_errands)


def nets_the_bait():
    jungle = Jungle(TB_TILE.KARAMBWANJI_SHOAL)
    jungle.hold(TB_ID.RAW_KARAMBWANJI, 5)
    expect(run_wait(crafting.fish_karambwanji(5)(jungle.log))).to_be(True)
    jungle.pack = []
    jungle.walk_ok = False
    expect(run_wait(crafting.fish_karambwanji(5)(jungle.log))).to_be(False)
    jungle.walk_ok = True
    expect(run_wait(crafting.fish_karambwanji(5)(jungle.log))).to_be(False)
    expect(jungle.logged('no Karambwanji shoal in reach')).to_be(True)
    spot = jungle.npc(TB_NPC.FISHING_SPOT, ['Net'], interact=lambda op: False)
    expect(run_wait(crafting.fish_karambwanji(5)(jungle.log))).to_be(False)
    catches = []

    def net(op):
        catches.append(op)
        if len(catches) == 1:
            jungle.hold(0, name=TB_NAME.RAW_SHRIMP, interact=jungle.drops(0))
        else:
            jungle.hold(TB_ID.RAW_KARAMBWANJI)
        return True
    spot._fields['interact'] = net
    expect(run_wait(crafting.fish_karambwanji(2)(jungle.log))).to_be(True)
    expect(jungle.count(TB_ID.RAW_KARAMBWANJI)).to_be(2)
    for i in range(26):
        jungle.hold(1000 + i)
    expect(run_wait(crafting.fish_karambwanji(3)(jungle.log))).to_be(True)


test('Karambwanji are netted at the Holy Lake, dropping the shrimp the shoal yields too', nets_the_bait)


def lowers_the_vessel():
    jungle = Jungle(TB_TILE.KARAMBWAN_SHOAL)
    jungle.hold(TB_ID.RAW_KARAMBWAN, 2)
    expect(run_wait(crafting.fish_karambwan()(jungle.log))).to_be(True)
    jungle.pack = []
    jungle.walk_ok = False
    expect(run_wait(crafting.fish_karambwan()(jungle.log))).to_be(False)
    jungle.walk_ok = True
    expect(run_wait(crafting.fish_karambwan()(jungle.log))).to_be(False)
    expect(jungle.logged('pack is missing item')).to_be(True)
    jungle.hold(TB_ID.VESSEL_LOADED)
    expect(run_wait(crafting.fish_karambwan()(jungle.log))).to_be(False)
    expect(jungle.logged("no Karambwan shoal in reach of Lubufu's stand")).to_be(True)
    spot = jungle.npc(TB_NPC.FISHING_SPOT, ['Fish'], interact=lambda op: False)
    expect(run_wait(crafting.fish_karambwan()(jungle.log))).to_be(False)
    spot._fields['interact'] = jungle.gives(TB_ID.RAW_KARAMBWAN)
    expect(run_wait(crafting.fish_karambwan(1)(jungle.log))).to_be(True)

    jungle.pack = []
    expect(run_wait(crafting.load_vessel(jungle.log))).to_be(False)
    jungle.hold(TB_ID.RAW_KARAMBWANJI, use_on=jungle.gives(TB_ID.VESSEL_LOADED, TB_ID.VESSEL))
    jungle.hold(TB_ID.VESSEL)
    expect(run_wait(crafting.load_vessel(jungle.log))).to_be(True)
    expect(run_wait(crafting.load_vessel(jungle.log))).to_be(True)


test("the baited vessel is lowered at Lubufu's spot, re-baited from the pack between casts", lowers_the_vessel)


def fetches_the_banana_and_rum():
    jungle = Jungle(VILLAGE)
    jungle.hold(TB_ID.SLICED_BANANA)
    expect(run_wait(crafting.pick_banana(jungle.log))).to_be(True)
    jungle.pack = []
    jungle.walk_ok = False
    expect(run_wait(crafting.pick_banana(jungle.log))).to_be(False)
    expect(run_wait(crafting.buy_rum(jungle.log))).to_be(False)
    jungle.walk_ok = True
    expect(run_wait(crafting.pick_banana(jungle.log))).to_be(False)
    expect(jungle.logged('no Banana Tree with a Search op')).to_be(True)
    tree = Fake(name=TB_LOC.BANANA_TREE, actions=lambda: ['Search'], distance=lambda: 1, interact=lambda op: False)
    jungle.locs = [tree]
    expect(run_wait(crafting.pick_banana(jungle.log))).to_be(False)
    tree._fields['interact'] = jungle.gives(TB_ID.BANANA)
    expect(run_wait(crafting.pick_banana(jungle.log))).to_be(True)

    spy_on(shop, 'open', impl=lambda npc: result(False))
    expect(run_wait(crafting.buy_rum(jungle.log))).to_be(False)
    expect(jungle.logged("could not open Zambo's shop")).to_be(True)
    spy_on(shop, 'open', impl=lambda npc: result(True))
    spy_on(shop, 'buy', impl=lambda name, qty: result(jungle.hold(TB_ID.RUM) is not None))
    spy_on(shop, 'close', impl=lambda: result(True))
    expect(run_wait(crafting.buy_rum(jungle.log))).to_be(True)
    expect(run_wait(crafting.buy_rum(jungle.log))).to_be(True)


test("the banana is searched out of the plantation and the rum bought at Zambo's bar", fetches_the_banana_and_rum)


def cooks_on_the_fire():
    jungle = Jungle(TB_TILE.FIRE)
    outcome = ['cooked']

    def use_on_loc(item_id, loc, prefer, expect_fn, log):
        if outcome[0] == 'cooked':
            jungle.drop(item_id)
            jungle.hold(TB_ID.MARINATED_JOGRE_BONES)
        elif outcome[0] == 'burnt':
            jungle.drop(item_id)
            jungle.hold(TB_ID.BURNT_KARAMBWAN, interact=jungle.drops(TB_ID.BURNT_KARAMBWAN))
        return expect_fn()
        yield
    spy_on(crafting, 'use_on_loc', impl=use_on_loc)
    leg = crafting.cook_on_fire(TB_ID.PASTY_JOGRE_BONES, TB_ID.MARINATED_JOGRE_BONES, 'pasty Jogre bones')
    expect(run_wait(leg(jungle.log))).to_be(False)
    expect(jungle.logged('no pasty Jogre bones in the pack to cook')).to_be(True)
    jungle.hold(TB_ID.PASTY_JOGRE_BONES)
    expect(run_wait(leg(jungle.log))).to_be(True)
    expect(run_wait(leg(jungle.log))).to_be(True)
    jungle.pack = []
    jungle.hold(TB_ID.PASTY_JOGRE_BONES)
    outcome[0] = 'ignored'
    expect(run_wait(leg(jungle.log))).to_be(False)
    expect(jungle.logged('the fire did not answer the pasty Jogre bones')).to_be(True)
    outcome[0] = 'burnt'
    expect(run_wait(leg(jungle.log))).to_be(False)
    expect(jungle.logged('the pasty Jogre bones burned — sourcing another')).to_be(True)
    expect(jungle.pack).to_equal([])

    jungle.hold(TB_ID.PESTLE)
    jungle.hold(TB_ID.RAW_KARAMBWANJI, use_on=lambda other: False)
    expect(run_wait(crafting.grind(TB_ID.RAW_KARAMBWANJI, TB_ID.KARAMBWANJI_PASTE)(jungle.log))).to_be(False)
    jungle.pack[0]._fields['use_on'] = jungle.gives(TB_ID.KARAMBWANJI_PASTE)
    expect(run_wait(crafting.grind(TB_ID.RAW_KARAMBWANJI, TB_ID.KARAMBWANJI_PASTE)(jungle.log))).to_be(True)
    spear = TB_SPEARS[0]
    jungle.hold(spear.id)
    expect(run_wait(crafting.poison_spear(spear)(jungle.log))).to_be(False)
    expect(jungle.logged(f'pack is missing item {TB_ID.KARAMBWAN_POISON_PASTE}')).to_be(True)
    for leg in [crafting.make_sandwich, crafting.paste_bones]:
        expect(run_wait(leg(jungle.log))).to_be(False)


test('the marinade is cooked on the jungle fire, and a burnt one is dropped to be sourced again', cooks_on_the_fire)


def hunts_for_a_drop():
    jungle = Jungle(TB_TILE.MONKEYS)
    hunt = crafting.kill_for(TB_NPC.MONKEY, TB_TILE.MONKEYS, [TB_ID.MONKEY_CORPSE], 'Monkey corpse')
    jungle.hold(TB_ID.MONKEY_CORPSE)
    expect(run_wait(hunt(jungle.log))).to_be(True)
    jungle.pack = []
    jungle.item(TB_ID.MONKEY_CORPSE, interact=lambda op: False)
    expect(run_wait(crafting.take_ground([TB_ID.MONKEY_CORPSE], 'Monkey corpse', jungle.log))).to_be(False)
    jungle.ground = []
    jungle.item(TB_ID.MONKEY_CORPSE)
    expect(run_wait(hunt(jungle.log))).to_be(True)
    jungle.pack = []
    jungle.ground = []
    jungle.walk_ok = False
    expect(run_wait(hunt(jungle.log))).to_be(False)
    jungle.walk_ok = True
    expect(run_wait(hunt(jungle.log))).to_be(False)
    expect(jungle.logged('no Monkey within 12 tiles of the stand')).to_be(True)
    monkey = jungle.npc(TB_NPC.MONKEY, ['Attack'], 4, interact=lambda op: False)
    expect(run_wait(hunt(jungle.log))).to_be(False)

    def dies(op):
        jungle.npcs = []
        jungle.item(TB_ID.MONKEY_CORPSE)
        return True
    monkey._fields['interact'] = dies
    expect(run_wait(hunt(jungle.log))).to_be(True)

    # A spear hunt outlasts one kill, but not the food.
    jungle.pack = []
    jungle.ground = []
    jungle.npcs = [monkey]
    monkey._fields['interact'] = lambda op: True
    spears = crafting.kill_for(TB_NPC.MONKEY, TB_TILE.MONKEYS, [TB_SPEARS[0].id], 'Iron spear', 2)
    expect(run_wait(spears(jungle.log))).to_be(False)
    expect(jungle.logged('out of food 1 kills into the Monkey hunt')).to_be(True)
    jungle.hold(0, 5, name=quest_food.name)
    expect(run_wait(spears(jungle.log))).to_be(False)
    expect(jungle.logged("2 Monkeys died without dropping 'Iron spear'")).to_be(True)
    expect(run_wait(hunt(jungle.log))).to_be(False)
    expect(jungle.logged("the Monkey left no 'Monkey corpse' within 14 tiles")).to_be(True)


test('a hunt kills until the drop it wants is in the pack, and banks when the food has gone', hunts_for_a_drop)


def burns_the_jogre_bones():
    jungle = Jungle(TB_TILE.JOGRES)
    jungle.hold(TB_ID.BURNT_JOGRE_BONES)
    expect(run_wait(crafting.burn_jogre_bones(jungle.log))).to_be(True)
    jungle.pack = []
    jungle.item(TB_ID.BURNT_JOGRE_BONES)
    expect(run_wait(crafting.burn_jogre_bones(jungle.log))).to_be(True)
    jungle.pack = []
    jungle.ground = []
    jungle.item(TB_ID.JOGRE_BONES)
    expect(run_wait(crafting.burn_jogre_bones(jungle.log))).to_be(False)
    expect(jungle.logged('need both Jogre bones and a Tinderbox')).to_be(True)
    expect(jungle.count(TB_ID.JOGRE_BONES)).to_be(1)
    jungle.ground = []
    jungle.pack[0]._fields['use_on'] = lambda other: False
    jungle.hold(TB_ID.TINDERBOX)
    expect(run_wait(crafting.burn_jogre_bones(jungle.log))).to_be(False)
    jungle.pack[0]._fields['use_on'] = lambda other: True
    jungle.refused = True
    expect(run_wait(crafting.burn_jogre_bones(jungle.log))).to_be(False)
    expect(jungle.logged('cannot light a fire at (2916,3053) — stepping aside')).to_be(True)
    expect(jungle.walks[-1]).to_equal(Tile(2918, 3054, 0))
    jungle.refused = False
    expect(run_wait(crafting.burn_jogre_bones(jungle.log))).to_be(False)
    expect(jungle.logged('the bones never caught at (2918,3054)')).to_be(True)

    def lights(other):
        jungle.drop(TB_ID.JOGRE_BONES)
        jungle.item(TB_ID.BURNT_JOGRE_BONES)
        return True
    jungle.pack[0]._fields['use_on'] = lights
    expect(run_wait(crafting.burn_jogre_bones(jungle.log))).to_be(True)


test('the Jogre bones are burnt with the tinderbox, stepping off a tile that already has a fire', burns_the_jogre_bones)


def wears_and_deposits_the_kit():
    jungle = Jungle(VILLAGE)
    worn = []

    def equip(name):
        worn.append(name)
        return name != 'Rune full helm'
        yield
    spy_on(equipment, 'equip', impl=equip)
    step = supplies.wear_all(['Maple shortbow', 'Adamant arrow'])
    expect(step.name).to_be('wear Maple shortbow, Adamant arrow')
    expect(run_wait(step.run(jungle.log))).to_be(True)
    expect(run_wait(supplies.wear_all(['Rune full helm']).run(jungle.log))).to_be(False)
    expect(jungle.logged('cannot wear Rune full helm')).to_be(True)

    bank = {'maple shortbow': 1, 'adamant arrow': 400, 'rune chainbody': 1, 'rune platelegs': 1, 'rune full helm': 1, 'coins': 9000,
            quest_food.name.lower(): 20}
    snap = QuestSnapshot(**{
        'journal': 'in_progress',
        'inv': {'coins': 3},
        'inv_ids': {TB_ID.COINS: 3},
        'worn': set(),
        'worn_ids': set(),
        'bank': bank,
        'bank_ids': {},
        'bank_known': True,
        'stage': TB_MAIN.STARTED,
        'progress': QuestProgress(TB_MAIN.STARTED, set()),
        'tile': TB_TILE.ARDOUGNE_BANK,
        'free_slots': 3,
        'ranged': 70,
    })
    step = supplies.prepare(snap)
    expect(step.kind).to_be('deposit')
    expect(step.keep).to_contain('maple shortbow')
    step = supplies.prepare(snap.with_fields({'free_slots': 20}))
    expect(step.kind).to_be('withdraw')
    expect([w for w in step.items if w['name'] == 'Coins'][0]['qty']).to_be(500)

    expect(supplies.readiness(lambda skill: 70)).to_be(None)
    gaps = supplies.readiness(lambda skill: 10)
    expect(gaps).to_contain('Firemaking 10 < 30')
    expect(gaps).to_contain('Cooking 10 < 30')


test('the kit is worn from the pack, a cramped pack is deposited down first, and the skill gaps are reported', wears_and_deposits_the_kit)


def stage_snap(main, flags, tile=None, inv_ids=None):
    return QuestSnapshot(**{
        'journal': 'in_progress',
        'inv': {},
        'inv_ids': inv_ids if inv_ids is not None else {},
        'worn': set(),
        'worn_ids': set(),
        'bank': {},
        'bank_ids': {},
        'bank_known': True,
        'stage': main,
        'progress': QuestProgress(main, set(flags)),
        'tile': tile if tile is not None else VILLAGE,
        'free_slots': 12,
    })


def decides_the_corners():
    expect(tbwt.decide(stage_snap(None, [])).reason).to_be('Tai Bwo Wannai Trio stage not readable')
    spy_on(tbwt, 'prepare', returns=None)
    done = [f'{TB_FLAG.LUBUFU}:{TB_LUBUFU.COMPLETE}', f'{TB_FLAG.TIADECHE}:{TB_TIADECHE.COMPLETE}', f'{TB_FLAG.TAMAYU}:{TB_TAMAYU.COMPLETE}',
            f'{TB_FLAG.TINSAY}:{TB_TINSAY.COMPLETE}']
    expect(tbwt.decide(stage_snap(TB_MAIN.STARTED, done)).reason).to_contain('all four brothers are done')
    expect(tbwt.tamayu_leg(stage_snap(TB_MAIN.STARTED, []), TB_TAMAYU.INTRO).name).to_be('bring Tamayu the news')
    expect(tbwt.tamayu_leg(stage_snap(TB_MAIN.STARTED, []), TB_TAMAYU.WATCHED_CUTSCENE).reason).to_contain('short of his four doses')
    potion = TB_POTIONS[1]
    step = tbwt.tamayu_leg(stage_snap(TB_MAIN.STARTED, [], inv_ids={potion.id: 1}), TB_TAMAYU.WATCHED_CUTSCENE)
    expect(step.name).to_be(f'give Tamayu the {potion.name}')
    expect(tbwt.tinsay_leg(stage_snap(TB_MAIN.STARTED, []), TB_TINSAY.INTRO).name).to_be('bring Tinsay the news')
    expect(tbwt.observe(stage_snap(TB_MAIN.STARTED, done + [TB_FLAG.SPEAR]))[0]).to_contain('agility=False spear=True')


test("TBWT's decide waits on an unreadable stage and on the quest varp once every brother is done", decides_the_corners)


def reads_the_journal():
    jungle = Jungle(VILLAGE)
    journal.reset_tbwt_progress_cache()
    state = {'status': 'in_progress', 'modal': -1, 'closed': 0,
             'text': ['I have found the three sons of Timfraku:|', '@dre@Tinsay:|', 'Nothing of interest.||']}
    jungle.varps = {TB_VARP.MAIN: TB_MAIN.STARTED, TB_VARP.TIADECHE: 2}
    spy_on(quests, 'status', impl=lambda name: state['status'])
    spy_on(quests, 'journal', impl=lambda name: result(state['text']))
    spy_on(reader, 'modals', impl=lambda: Fake(main=state['modal']))

    def close():
        state['modal'] = -1
        state['closed'] += 1
        return True
    spy_on(_core, 'close_interfaces', impl=close)
    progress = run_wait(journal.read_tbwt_progress())
    expect(f'{TB_FLAG.TINSAY}:{TB_TINSAY.INTRO}' in progress.flags).to_be(True)
    expect(f'{TB_FLAG.TIADECHE}:2' in progress.flags).to_be(True)
    state['text'] = []
    state['modal'] = 229
    expect(run_wait(journal.read_tbwt_progress())).to_be(progress)
    expect(state['closed']).to_be(1)
    jungle.varps[TB_VARP.MAIN] = TB_MAIN.ALL_BROTHERS
    expect(run_wait(journal.read_tbwt_progress()).stage).to_be(TB_MAIN.ALL_BROTHERS)
    state['status'] = 'complete'
    expect(run_wait(journal.read_tbwt_progress()).stage).to_be(TB_MAIN.COMPLETE)
    state['status'] = 'unknown'
    expect(run_wait(journal.read_tbwt_progress())).to_be(None)
    journal.reset_tbwt_progress_cache()


test('the journal is read only in the brothers phase, keeping the last good page through a blank one', reads_the_journal)
