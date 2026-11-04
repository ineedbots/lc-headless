"""Quest gear refusals, self-sourced bow supplies, root farming and Fremennik provisioning."""

from rs2004.dialogue import chat_dialog
from rs2004.entities import npcs
from rs2004.execution import event_signal
from rs2004.game import game
from rs2004.items import equipment
from rs2004.navigation import reachability
from rs2004.quests.defs.ikov import gear, supplies as ikov
from rs2004.quests.defs.ikov.areas import IKOV_LOC, IKOV_NAME, IKOV_NPC, IKOV_OBJ, IKOV_TILE
from rs2004.quests.defs.fremenniktrials import supplies as fremennik
from rs2004.quests.engine.types import QuestSnapshot
from rs2004.quests.gear import quest_loadout


def answer(value):
    def wait(*args, **kwargs):
        return value
        yield
    return wait


def give(scene, id, name='Quest item'):
    def effect(*args):
        scene.item(id, name)
    return effect


def gear_refusals():
    scene = Scene()
    stub(gear, refused=set())
    snap = QuestSnapshot(bank_known=True, inv={'coif': 1}, bank={})
    step = gear.ranged_armour_step(snap)
    equip = spy_on(equipment, 'equip', impl=answer(False))
    expect(run_wait(step.run(scene.log))).to_be(True)
    expect('coif' in gear.refused).to_be(True)
    expect(gear.ranged_armour_step(snap)).to_be_null()
    snap.inv = {'rune scimitar': 1}
    step = gear.melee_weapon_step(snap)
    expect(run_wait(step.run(scene.log))).to_be(True)
    expect('rune scimitar' in gear.refused).to_be(True)
    gear.refused.clear()
    equip.mock_implementation(scene._equip)
    scene.item(1, 'Coif')
    snap.inv = {'coif': 1}
    expect(run_wait(gear.ranged_armour_step(snap).run(scene.log))).to_be(True)
    scene.item(2, 'Rune scimitar')
    snap.inv = {'rune scimitar': 1}
    expect(run_wait(gear.melee_weapon_step(snap).run(scene.log))).to_be(True)


test('Ikov gear records server refusals and does not select the same refused item forever', gear_refusals)


def bow_materials():
    scene = Scene(IKOV_TILE.YEW_TREES)
    spy_on(event_signal, 'pending', returns=False)
    expect(run_wait(ikov.chop_yew(scene.log))).to_be(False)
    scene.item(IKOV_OBJ.IRON_AXE, IKOV_NAME.IRON_AXE)
    expect(run_wait(ikov.chop_yew(scene.log))).to_be(True)
    scene.loc('Yew', ['Chop down'], id=IKOV_LOC.YEW_TREE, effect=lambda op: False)
    expect(run_wait(ikov.chop_yew(scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Yew', ['Chop down'], id=IKOV_LOC.YEW_TREE)
    expect(run_wait(ikov.chop_yew(scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Yew', ['Chop down'], id=IKOV_LOC.YEW_TREE, effect=give(scene, IKOV_OBJ.YEW_LOGS, IKOV_NAME.YEW_LOGS))
    expect(run_wait(ikov.chop_yew(scene.log))).to_be(True)
    expect(run_wait(ikov.pick_flax(scene.log))).to_be(True)
    scene.loc('Flax', ['Pick'], id=IKOV_LOC.FLAX, effect=lambda op: False)
    expect(run_wait(ikov.pick_flax(scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Flax', ['Pick'], id=IKOV_LOC.FLAX, effect=give(scene, IKOV_OBJ.FLAX, IKOV_NAME.FLAX))
    expect(run_wait(ikov.pick_flax(scene.log))).to_be(True)
    expect(run_wait(ikov.string_bow(scene.log))).to_be(False)
    scene.item(IKOV_OBJ.UNSTRUNG_YEW_SHORTBOW, 'Stave')
    scene.item(IKOV_OBJ.BOW_STRING, 'String', on_use=lambda target: False)
    expect(run_wait(ikov.string_bow(scene.log))).to_be(False)
    scene.take(IKOV_OBJ.BOW_STRING)
    scene.item(IKOV_OBJ.BOW_STRING, 'String', on_use=give(scene, IKOV_OBJ.YEW_SHORTBOW))
    expect(run_wait(ikov.string_bow(scene.log))).to_be(True)
    expect(run_wait(ikov.light_candle(scene.log))).to_be(False)
    scene.item(IKOV_OBJ.UNLIT_CANDLE, 'Candle')
    scene.item(IKOV_OBJ.TINDERBOX, 'Tinderbox', on_use=lambda target: False)
    expect(run_wait(ikov.light_candle(scene.log))).to_be(False)
    scene.take(IKOV_OBJ.TINDERBOX)
    scene.item(IKOV_OBJ.TINDERBOX, 'Tinderbox', on_use=give(scene, IKOV_OBJ.LIT_CANDLE))
    expect(run_wait(ikov.light_candle(scene.log))).to_be(True)
    expect(run_wait(ikov.light_candle(scene.log))).to_be(True)


test('Ikov sources yew and flax, strings the bow and lights its candle', bow_materials)


def fletching():
    scene = Scene()
    menu = spy_on(chat_dialog, 'is_make_menu', returns=False)
    expect(run_wait(ikov.fletch_bow(scene.log))).to_be(False)
    scene.item(IKOV_OBJ.KNIFE, 'Knife', on_use=lambda target: False)
    scene.item(IKOV_OBJ.YEW_LOGS, 'Yew logs')
    expect(run_wait(ikov.fletch_bow(scene.log))).to_be(False)
    scene.take(IKOV_OBJ.KNIFE)
    scene.item(IKOV_OBJ.KNIFE, 'Knife', on_use=lambda target: menu.mock_return_value(True))
    spy_on(chat_dialog, 'make_products', returns=[])
    make = spy_on(chat_dialog, 'make_one', impl=answer(False))
    expect(run_wait(ikov.fletch_bow(scene.log))).to_be(False)

    def made(name):
        expect(name).to_be('Yew Short Bow')
        scene.item(IKOV_OBJ.UNSTRUNG_YEW_SHORTBOW, 'Stave')
        return True
        yield

    make.mock_implementation(made)
    expect(run_wait(ikov.fletch_bow(scene.log))).to_be(True)


test('fletching retries opening the menu and selects its caption instead of the item name', fletching)


def roots():
    scene = Scene(IKOV_TILE.HOBGOBLINS)
    spy_on(game, 'set_auto_retaliate', returns=None)
    spy_on(npcs, 'all', impl=lambda: scene.npcs)
    spy_on(reachability, 'can_reach', returns=True)
    pending = spy_on(event_signal, 'pending', returns=False)
    expect(run_wait(ikov.take_root(scene.log))).to_be(False)
    scene.on_ground(IKOV_OBJ.LIMPWURT_ROOT, 'Root', dist=3, effect=lambda op: False)
    scene.walk_ok = False
    expect(run_wait(ikov.take_root(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(ikov.take_root(scene.log))).to_be(False)
    scene.ground = []
    scene.on_ground(IKOV_OBJ.LIMPWURT_ROOT, 'Root')
    expect(run_wait(ikov.farm_roots(scene.log))).to_be(True)
    scene.pack = []
    for i in range(28):
        scene.item(i, 'Filler')
    expect(run_wait(ikov.farm_roots(scene.log))).to_be(False)
    scene.pack = []
    expect(run_wait(ikov.farm_roots(scene.log))).to_be(False)
    target = scene.npc('Hobgoblin', ['Attack'], id=IKOV_NPC.HOBGOBLIN_ARMED, dist=9, effect=lambda op: False)
    scene.walk_ok = False
    expect(run_wait(ikov.kill_hobgoblin(target, scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(ikov.kill_hobgoblin(target, scene.log))).to_be(False)
    scene.npcs = []
    target = scene.npc('Hobgoblin', ['Attack'], id=IKOV_NPC.HOBGOBLIN_ARMED)
    pending.mock_return_value(True)
    expect(run_wait(ikov.farm_roots(scene.log))).to_be(False)
    pending.mock_return_value(False)
    expect(run_wait(ikov.farm_roots(scene.log))).to_be(False)
    scene.npcs = []
    scene.npc('Hobgoblin', ['Attack'], id=IKOV_NPC.HOBGOBLIN_ARMED, effect=lambda op: scene.npcs.clear())
    expect(run_wait(ikov.farm_roots(scene.log))).to_be(True)
    scene.at = None
    expect(run_wait(ikov.farm_roots(scene.log))).to_be(True)
    expect(run_wait(ikov.leave_the_camp(scene.log))).to_be(False)


test('root farming takes drops, respects pack capacity and handles unreachable or missing hobgoblins', roots)


def fremennik_tools():
    scene = Scene()
    snap = QuestSnapshot(bank_known=False, inv_ids={}, bank_ids={})
    for fn in [fremennik.gather_knife, fremennik.gather_axe, fremennik.gather_tinderbox, fremennik.gather_shark]:
        expect(fn(snap).kind).to_be('scan_bank')
    snap.bank_known = True
    for fn, kind in [[fremennik.gather_knife, 'grab_ground'], [fremennik.gather_axe, 'grab_ground'],
                     [fremennik.gather_tinderbox, 'buy'], [fremennik.gather_shark, 'buy']]:
        expect(fn(snap).kind).to_be(kind)
    expect(fremennik.gather_coins(snap, 100).kind).to_be('wait')
    snap.bank = {'coins': 5000}
    expect(fremennik.gather_coins(snap, 100).items[0]['qty']).to_be(5000)
    snap.inv = {'coins': 100, 'tinderbox': 1}
    expect(fremennik.gather_coins(snap, 100)).to_be_null()
    expect(fremennik.gather_tinderbox(snap)).to_be_null()
    snap.bank = {'rune longsword': 1, 'rune chainbody': 1, 'lobster': 20}
    stub(quest_loadout, current=None)
    expect(fremennik.combat_kit(snap).kind).to_be('withdraw')
    snap.inv['lobster'] = 8
    expect(fremennik.combat_kit(snap).kind).to_be('withdraw')
    snap.inv['rune longsword'] = 1
    snap.inv['rune chainbody'] = 1
    step = fremennik.combat_kit(snap)
    expect(step.kind).to_be('custom')
    expect(run_wait(step.run(scene.log))).to_be(True)
    expect(scene.logged('cannot wear')).to_be(True)
    scene.item(1, 'Rune longsword')
    scene.item(2, 'Rune chainbody')
    expect(run_wait(step.run(scene.log))).to_be(True)
    snap.worn = set(['rune longsword', 'rune chainbody'])
    expect(fremennik.combat_kit(snap)).to_be_null()
    snap.bank = {}
    snap.inv = {}
    snap.worn = set()
    expect(fremennik.combat_kit(snap).kind).to_be('wait')


test('Fremennik provisioning scans before sourcing and dresses and feeds before the Draugen', fremennik_tools)


def fremennik_combine_and_talk():
    scene = Scene()
    scene.walk_ok = False
    expect(run_wait(fremennik.talk_until('NPC', IKOV_TILE.AEMAD, [], lambda: False, scene.log, 1200))).to_be(False)
    scene.walk_ok = True
    opened = spy_on(fremennik, 'open_dialogue', impl=answer(False))
    expect(run_wait(fremennik.talk_until('NPC', IKOV_TILE.AEMAD, [], lambda: False, scene.log, 1200))).to_be(False)
    opened.mock_implementation(answer(True))
    scene.goal = False
    scene.later(lambda: None)
    scene.later(lambda: setattr(scene, 'goal', True))
    expect(run_wait(fremennik.talk_until('NPC', IKOV_TILE.AEMAD, [], lambda: scene.goal, scene.log))).to_be(True)
    step = fremennik.combine(1, 2, 3, 'Recipe')
    expect(run_wait(step.run(scene.log))).to_be(False)
    scene.item(1, 'Source', on_use=lambda target: False)
    scene.item(2, 'Target')
    expect(run_wait(step.run(scene.log))).to_be(False)
    scene.take(1)
    scene.item(1, 'Source', on_use=give(scene, 3))
    expect(run_wait(step.run(scene.log))).to_be(True)
    expect(scene.has(3)).to_be(True)


test('Fremennik conversations reopen until their goal and item combinations verify the product', fremennik_combine_and_talk)


def bow_chain_recovery():
    scene = Scene()
    snap = QuestSnapshot(bank_known=True, inv_ids={IKOV_OBJ.UNSTRUNG_YEW_SHORTBOW: 1, IKOV_OBJ.KNIFE: 1},
                         bank_ids={IKOV_OBJ.FLAX: 1})
    expect(ikov.bow_chain_step(snap).items[0]['id']).to_be(IKOV_OBJ.FLAX)
    snap.inv_ids[IKOV_OBJ.FLAX] = 1
    step = ikov.bow_chain_step(snap)
    expect(step.kind).to_be('use_on')
    expect(step.target).to_be('Spinning wheel')
    expect(ikov.sourcing_shortfall()).to_be_null()
    scene.stats['woodcutting'] = 1
    scene.stats['fletching'] = 1
    expect(ikov.sourcing_shortfall()).to_contain('needs')
    scene.item(IKOV_OBJ.YEW_SHORTBOW, IKOV_NAME.YEW_SHORTBOW)
    run_wait(equipment.equip(IKOV_NAME.YEW_SHORTBOW))
    expect(run_wait(ikov.stow_empty_bow(scene.log))).to_be(True)
    expect(equipment.contains(IKOV_NAME.YEW_SHORTBOW)).to_be(False)


test('bow sourcing withdraws flax before spinning and reports skills missing for self-sourcing', bow_chain_recovery)
