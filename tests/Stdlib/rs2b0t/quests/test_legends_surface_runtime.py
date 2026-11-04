"""Legends Guild errands, jungle mapping, Gujuo, gathering and the final Yommi totem."""

import rs2004.quests.defs.legends.fight as combat
from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.quests.defs.legends import gather, guild, jungle, scene as dialog, totem
from rs2004.quests.defs.legends.areas import GEM_CUTS, LQ_ID, LQ_LOC, LQ_LOC_ID, LQ_NPC, LQ_TILE
from rs2004.tabs import prayer


def answer(value):
    def wait(*args, **kwargs):
        return value
        yield
    return wait


def totem_axe_and_healing():
    scene = Scene(LQ_TILE.GOLD_ROCKS)
    tree = spy_on(totem, 'tree_at', returns=None)
    spy_on(totem, 'use_on_loc', impl=answer(False))
    expect(run_wait(totem.axe_on(1, 'Tree', scene.at, 2, scene.log))).to_be(False)
    tree.mock_return_value(Fake())
    expect(run_wait(totem.axe_on(1, 'Tree', scene.at, 2, scene.log))).to_be(True)
    spy_on(combat, 'hurt', returns=True)
    plan = Fake(done=lambda: False, ms=1000)
    expect(run_wait(combat.fight_loop(plan, False, scene.log))).to_be(False)


test('totem axe work waits for its next tree form and combat prioritizes healing', totem_axe_and_healing)


def give(scene, id):
    def effect(*args):
        scene.item(id, 'Quest item')
    return effect


def guild_entry():
    scene = Scene(LQ_TILE.GUARD)
    scene.walk_ok = False
    expect(run_wait(guild.enter_guild(scene.log))).to_be(False)
    scene.walk_ok = True
    prompt = spy_on(guild, 'prompt_loc', impl=answer(False))
    expect(run_wait(guild.enter_guild(scene.log))).to_be(False)
    expect(len(prompt.calls)).to_be(2)
    prompt.mock_implementation(answer(True))
    expect(run_wait(guild.enter_guild(scene.log))).to_be(True)
    scene.status = 'not_started'
    scene.talk_status = 'unreachable'
    expect(run_wait(guild.enter_guild(scene.log))).to_be(False)
    scene.talk_status = 'done'
    expect(run_wait(guild.enter_guild(scene.log))).to_be(False)
    scene.main_texts = ['You must complete more quests']
    expect(run_wait(guild.enter_guild(scene.log))).to_be(False)
    expect(scene.logged('refused entry')).to_be(True)
    scene.main_texts = []
    scene.later(lambda: setattr(scene, 'at', Tile(2725, 3352, 0)))
    expect(run_wait(guild.enter_guild(scene.log))).to_be(True)
    expect(run_wait(guild.enter_guild(scene.log))).to_be(True)


test('the guild gate uses guard dialogue before the quest and either gate leaf afterwards', guild_entry)


def guild_errands():
    for fn, product in [[guild.start_quest, LQ_ID.MAP], [guild.replace_map, LQ_ID.MAP],
                        [guild.hand_in_totem, None]]:
        scene = Scene(LQ_TILE.GUARD)
        enter = spy_on(guild, 'enter_guild', impl=answer(False))
        expect(run_wait(fn(scene.log))).to_be(False)
        enter.mock_implementation(answer(True))
        scene.walk_ok = False
        expect(run_wait(fn(scene.log))).to_be(False)
        scene.walk_ok = True
        scene.talk_status = 'unreachable'
        expect(run_wait(fn(scene.log))).to_be(False)
        scene.talk_status = 'done'
        if product is not None:
            scene.later(give(scene, product))
        expect(run_wait(fn(scene.log))).to_be(True)
        if product is not None:
            expect(run_wait(fn(scene.log))).to_be(True)
        restore_all()
    scene = Scene(LQ_TILE.CUPBOARD)
    enter = spy_on(guild, 'enter_guild', impl=answer(False))
    expect(run_wait(guild.take_machete(scene.log))).to_be(False)
    enter.mock_implementation(answer(True))
    scene.walk_ok = False
    expect(run_wait(guild.take_machete(scene.log))).to_be(False)
    scene.walk_ok = True
    scene.loc(LQ_LOC.CUPBOARD, ['Open'])
    prompt = spy_on(guild, 'prompt_loc', impl=answer(True))
    expect(run_wait(guild.take_machete(scene.log))).to_be(True)
    scene.item(LQ_ID.MACHETE, 'Machete')
    expect(run_wait(guild.take_machete(scene.log))).to_be(True)
    expect(prompt.calls[-1][0].id).to_be(LQ_LOC_ID.CUPBOARD_OPEN)


test('Radimus errands stop at failed approaches and obtain the map or cupboard machete', guild_errands)


def hall_and_training():
    scene = Scene(LQ_TILE.GUARD)
    enter = spy_on(guild, 'enter_guild', impl=answer(False))
    expect(run_wait(guild.enter_main_hall(scene.log))).to_be(False)
    enter.mock_implementation(answer(True))
    spy_on(guild, 'prompt_loc', impl=answer(True))
    expect(run_wait(guild.enter_main_hall(scene.log))).to_be(True)
    scene.at = Tile(2725, 3380, 0)
    expect(run_wait(guild.enter_main_hall(scene.log))).to_be(True)
    hall = spy_on(guild, 'enter_main_hall', impl=answer(False))
    expect(run_wait(guild.take_training(scene.log))).to_be(False)
    hall.mock_implementation(answer(True))
    scene.walk_ok = False
    expect(run_wait(guild.take_training(scene.log))).to_be(False)
    scene.walk_ok = True
    scene.talk_status = 'unreachable'
    expect(run_wait(guild.take_training(scene.log))).to_be(False)
    scene.talk_status = 'done'
    spy_on(guild, 'drive_to_end', impl=answer(True))
    scene.status = 'complete'
    expect(run_wait(guild.take_training(scene.log))).to_be(True)
    expect(len(guild.training_prefer())).to_be(6)


test('guild training requires the hall and waits for quest completion after the conversation', hall_and_training)


def dialogue_boundary():
    scene = Scene(LQ_TILE.GUARD)
    npc = scene.npc('Recipient')
    expect(run_wait(dialog.offer_to(123, npc, scene.log))).to_be(False)
    scene.item(123, 'Gift')
    scene.walk_ok = False
    expect(run_wait(dialog.offer_to(123, npc, scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(dialog.offer_to(123, npc, scene.log))).to_be(True)
    expect(run_wait(dialog.drive_to_end([], scene.log))).to_be(False)
    scene.chat.pages = [['Unknown']]
    expect(run_wait(dialog.drive_to_end([], scene.log))).to_be(False)
    scene.chat.pages = ['continue']
    expect(run_wait(dialog.drive_to_end([], scene.log, required='Required'))).to_be(False)
    scene.chat.pages = ['continue', ['Required']]
    scene.main_modal = 123
    expect(run_wait(dialog.drive_to_end(['Required'], scene.log, required='Required'))).to_be(True)
    expect(scene.main_modal).to_be(-1)
    scene.chat.pages = ['continue']
    expect(run_wait(dialog.drive_to_end([], scene.log, ms=100))).to_be(True)


test('Legends dialogue requires a real conversation and its required topic', dialogue_boundary)


def jungle_world():
    scene = Scene(LQ_TILE.JUNGLE_MOUTH)
    scene.area = 'surface'
    patch(jungle, 'here', lambda: scene.area)
    return scene


def cutting_band():
    scene = jungle_world()
    scene.at = None
    expect(jungle.pick_plant(-1)).to_be_null()
    scene.at = LQ_TILE.JUNGLE_MOUTH
    expect(run_wait(jungle.chop_through_band(-1, lambda: False, scene.log))).to_be(False)
    scene.loc(LQ_LOC.JUNGLE_BUSH, ['Chop-down'], tile=Tile(scene.at.x, scene.at.z - 1, 0), effect=lambda op: False)
    expect(run_wait(jungle.chop_through_band(-1, lambda: False, scene.log))).to_be(False)
    scene.locs = []

    def cut(op):
        scene.at = LQ_TILE.JUNGLE_INSIDE

    scene.loc(LQ_LOC.JUNGLE_TREE, ['Chop-down'], tile=Tile(scene.at.x, scene.at.z - 1, 0), effect=cut)
    expect(run_wait(jungle.chop_through_band(-1, jungle.through_south, scene.log))).to_be(True)
    expect(jungle.moved_off(LQ_TILE.JUNGLE_MOUTH)).to_be(True)
    scene.item(123, 'Teak logs')
    run_wait(jungle.drop_logs())
    expect(scene.ticks > 0).to_be(True)


test('the jungle band picks cardinal plants, retries cuts and sheds logs after crossing', cutting_band)


def jungle_crossings():
    scene = jungle_world()
    cave = spy_on(jungle, 'leave_caves', impl=answer(False))
    expect(run_wait(jungle.enter_jungle(scene.log))).to_be(False)
    cave.mock_implementation(answer(True))
    scene.walk_ok = False
    expect(run_wait(jungle.enter_jungle(scene.log))).to_be(False)
    scene.walk_ok = True
    cut = spy_on(jungle, 'chop_through_band', impl=answer(False))
    expect(run_wait(jungle.enter_jungle(scene.log))).to_be(False)
    cut.mock_implementation(answer(True))
    expect(run_wait(jungle.enter_jungle(scene.log))).to_be(True)
    expect(run_wait(jungle.leave_jungle(scene.log))).to_be(True)
    scene.area = 'jungle'
    scene.at = LQ_TILE.MAP_WEST
    expect(run_wait(jungle.enter_jungle(scene.log))).to_be(True)
    scene.walk_ok = False
    expect(run_wait(jungle.leave_jungle(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(jungle.leave_jungle(scene.log))).to_be(True)
    expect(cut.calls[-1][0]).to_be(1)


test('jungle entry first escapes caves and departure chops north', jungle_crossings)


def mapping():
    scene = jungle_world()
    expect(run_wait(jungle.draw_section(scene.log))).to_be('short')
    scene.item(LQ_ID.MAP, 'Notes', effect=lambda op: False)
    expect(run_wait(jungle.draw_section(scene.log))).to_be('retry')
    scene.pack = []
    scene.item(LQ_ID.MAP, 'Notes')
    expect(run_wait(jungle.draw_section(scene.log))).to_be('retry')
    scene.main_texts = ['need some papyrus and charcoal']
    expect(run_wait(jungle.draw_section(scene.log))).to_be('short')
    scene.main_texts = ['neatly add a new section']
    expect(run_wait(jungle.draw_section(scene.log))).to_be('done')
    scene.item(LQ_ID.MAP_COMPLETE, 'Completed map')
    expect(run_wait(jungle.map_jungle(scene.log))).to_be(True)
    scene.pack = []
    enter = spy_on(jungle, 'enter_jungle', impl=answer(False))
    expect(run_wait(jungle.map_jungle(scene.log))).to_be(False)
    enter.mock_implementation(answer(True))
    scene.walk_ok = False
    expect(run_wait(jungle.map_jungle(scene.log))).to_be(False)
    scene.walk_ok = True
    draw = spy_on(jungle, 'draw_section', impl=answer('short'))
    expect(run_wait(jungle.map_jungle(scene.log))).to_be(False)
    draw.mock_implementation(answer('retry'))
    expect(run_wait(jungle.map_jungle(scene.log))).to_be(False)
    draw.mock_implementation(answer('done'))
    expect(run_wait(jungle.map_jungle(scene.log))).to_be(False)
    sections = []

    def drawn(log):
        sections.append(True)
        if len(sections) == 3:
            scene.item(LQ_ID.MAP_COMPLETE, 'Map')
        return 'done'
        yield

    draw.mock_implementation(drawn)
    expect(run_wait(jungle.map_jungle(scene.log))).to_be(True)
    expect(len(sections)).to_be(3)


test('mapping retries crafting rolls but stops on missing papyrus or charcoal', mapping)


def bullroarer_trade():
    scene = jungle_world()
    leave = spy_on(jungle, 'leave_jungle', impl=answer(False))
    expect(run_wait(jungle.get_bullroarer(scene.log))).to_be(False)
    leave.mock_implementation(answer(True))
    scene.walk_ok = False
    expect(run_wait(jungle.get_bullroarer(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(jungle.get_bullroarer(scene.log))).to_be(False)
    scene.npc(LQ_NPC.FORESTER)
    offer = spy_on(jungle, 'offer_to', impl=answer(False))
    expect(run_wait(jungle.get_bullroarer(scene.log))).to_be(False)
    offer.mock_implementation(answer(True))
    scene.later(give(scene, LQ_ID.BULLROARER))
    expect(run_wait(jungle.get_bullroarer(scene.log))).to_be(True)
    expect(run_wait(jungle.get_bullroarer(scene.log))).to_be(True)


test('the forester trades the completed map for a bullroarer', bullroarer_trade)


def gujuo():
    scene = jungle_world()
    enter = spy_on(jungle, 'enter_jungle', impl=answer(False))
    expect(run_wait(jungle.summon_gujuo(scene.log))).to_be(False)
    enter.mock_implementation(answer(True))
    expect(run_wait(jungle.summon_gujuo(scene.log))).to_be(False)
    scene.item(LQ_ID.BULLROARER, 'Roarer', effect=lambda op: False)
    expect(run_wait(jungle.summon_gujuo(scene.log))).to_be(False)
    scene.pack = []
    scene.item(LQ_ID.BULLROARER, 'Roarer')
    expect(run_wait(jungle.summon_gujuo(scene.log))).to_be(False)
    scene.pack = []
    scene.item(LQ_ID.BULLROARER, 'Roarer', effect=lambda op: scene.npc(LQ_NPC.GUJUO))
    expect(run_wait(jungle.summon_gujuo(scene.log))).to_be(True)
    expect(run_wait(jungle.summon_gujuo(scene.log))).to_be(True)
    scene.npcs = []
    scene.npc('Jungle Wolf', ['Attack'], targets_me=True)
    fight = spy_on(jungle, 'fight', impl=answer(True))
    run_wait(jungle.see_off_enemy(scene.log))
    expect(fight.calls[0][0].pray).to_be(False)
    summon = spy_on(jungle, 'summon_gujuo', impl=answer(False))
    expect(run_wait(jungle.talk_gujuo_status([])(scene.log))).to_be('nodialog')
    summon.mock_implementation(answer(True))
    scene.talk_status = 'unreachable'
    expect(run_wait(jungle.talk_gujuo_status([])(scene.log))).to_be('nodialog')
    scene.talk_status = 'done'
    spy_on(jungle, 'drive_to_end', impl=answer(False))
    expect(run_wait(jungle.talk_gujuo_status([])(scene.log))).to_be('nogoal')
    expect(run_wait(jungle.talk_gujuo_status([], lambda: True)(scene.log))).to_be('goal')
    scene.chat.pages = ['continue']
    scene.goal = False
    scene.later(lambda: setattr(scene, 'goal', True))
    expect(run_wait(jungle.talk_gujuo([], lambda: scene.goal)(scene.log))).to_be(True)


test('the bullroarer summons Gujuo, sees off attackers and distinguishes missing dialogue from missing topics', gujuo)


def gathering():
    scene = Scene(LQ_TILE.GEM_ROCKS)
    scene.walk_ok = False
    expect(run_wait(gather.mine_gem(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(gather.mine_gem(scene.log))).to_be(False)
    scene.loc('Rock', ['Mine'], id=gather.GEM_ROCK_ID, effect=give(scene, GEM_CUTS[0].uncut))
    expect(run_wait(gather.mine_gem(scene.log))).to_be(True)
    expect(run_wait(gather.smelt_gold_bar(scene.log))).to_be(False)
    scene.item(LQ_ID.GOLD_ORE, 'Ore')
    scene.walk_ok = False
    expect(run_wait(gather.smelt_gold_bar(scene.log))).to_be(False)
    scene.walk_ok = True
    spy_on(gather, 'use_on_loc', impl=answer(True))
    expect(run_wait(gather.smelt_gold_bar(scene.log))).to_be(True)
    for herb in gather.BRAVERY_HERBS:
        expect(run_wait(gather.identify_herb(herb)(scene.log))).to_be(False)
        scene.item(herb.unid_id, 'Unidentified', effect=lambda op: False)
        expect(run_wait(gather.pick_herb(herb)(scene.log))).to_be(True)
        expect(run_wait(gather.identify_herb(herb)(scene.log))).to_be(False)
        scene.take(herb.unid_id)
        scene.item(herb.unid_id, 'Unidentified', effect=give(scene, herb.id))
        expect(run_wait(gather.identify_herb(herb)(scene.log))).to_be(True)
        expect(run_wait(gather.identify_herb(herb)(scene.log))).to_be(True)
        scene.take(herb.id)
        scene.take(herb.unid_id)
        prompt = spy_on(gather, 'prompt_loc', impl=answer(True))
        expect(run_wait(gather.pick_herb(herb)(scene.log))).to_be(True)
        expect(prompt.calls[-1][0].expect()).to_be(False)


test('Legends gathering confirms any uncut gem and identifies both bravery herbs', gathering)


def prayer_combat():
    scene = Scene(LQ_TILE.SOURCE_STAND)
    expect(run_wait(combat.drink_prayer(scene.log))).to_be(False)
    dose = combat.PRAYER_POTIONS[0]
    scene.item(dose.id, dose.name, effect=lambda op: False)
    expect(run_wait(combat.drink_prayer(scene.log))).to_be(False)
    scene.pack = []
    scene.item(dose.id, dose.name)
    expect(run_wait(combat.drink_prayer(scene.log))).to_be(True)
    spy_on(prayer, 'known', returns=True)
    spy_on(prayer, 'available', returns=True)
    active = spy_on(prayer, 'active', returns=True)
    spy_on(prayer, 'points', returns=50)
    off = spy_on(prayer, 'set', impl=answer(False))
    plan = Fake(npc='Demon', done=lambda: False, ms=5000, pray=True)
    expect(run_wait(combat.fight(plan, scene.log))).to_be(False)
    expect(scene.logged('would not switch off')).to_be(True)
    expect(len(off.calls)).to_be(3)
    active.mock_return_value(False)
    expect(run_wait(combat.fight(plan, scene.log))).to_be(False)
    active.mock_return_value(True)
    scene.npc('Demon', ['Attack'], targets_me=True)
    expect(run_wait(combat.fight_loop(plan, False, scene.log))).to_be(False)
    scene.fighting = True
    expect(run_wait(combat.fight_loop(plan, False, scene.log))).to_be(False)
    expect(run_wait(combat.fight_loop(Fake(done=lambda: True), False, scene.log))).to_be(True)


test('Legends combat restores prayer, observes swing gaps and retries switching protection off', prayer_combat)


def totem_growth():
    scene = Scene(LQ_TILE.MAP_WEST)
    enter = spy_on(totem, 'enter_jungle', impl=answer(False))
    expect(run_wait(totem.grow_totem_pole(scene.log))).to_be(False)
    enter.mock_implementation(answer(True))
    expect(run_wait(totem.grow_totem_pole(scene.log))).to_be(False)
    scene.item(LQ_ID.RUNE_AXE, 'Axe')
    scene.walk_ok = False
    expect(run_wait(totem.grow_totem_pole(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(totem.grow_totem_pole(scene.log))).to_be(False)
    scene.item(LQ_ID.YOMMI_SEEDS_GERM, 'Seeds')
    expect(run_wait(totem.grow_totem_pole(scene.log))).to_be(False)
    scene.item(LQ_ID.GOLD_BOWL_BLESSED_PURE, 'Water')
    soil = totem.nearest_of(totem.FERTILE_SOILS)
    use = spy_on(totem, 'use_on_loc', impl=answer(False))
    expect(run_wait(totem.grow_totem_pole(scene.log))).to_be(False)
    scene.loc('Sapling', id=LQ_LOC_ID.YOMMI_SAPLING, tile=soil)
    expect(run_wait(totem.grow_totem_pole(scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Adult', id=LQ_LOC_ID.YOMMI_ADULT, tile=soil)
    axe = spy_on(totem, 'axe_on', impl=answer(False))
    expect(run_wait(totem.grow_totem_pole(scene.log))).to_be(False)
    cuts = []

    def cut(id, name, near, next_, log):
        cuts.append(id)
        if next_ == LQ_LOC_ID.YOMMI_TOTEM:
            scene.loc('Totem', id=next_, tile=soil, effect=give(scene, LQ_ID.TOTEM_POLE))
        return True
        yield

    axe.mock_implementation(cut)
    expect(run_wait(totem.grow_totem_pole(scene.log))).to_be(True)
    expect(len(cuts)).to_be(3)
    expect(run_wait(totem.grow_totem_pole(scene.log))).to_be(True)
    scene.at = None
    expect(totem.nearest_of(totem.FERTILE_SOILS)).to_equal(totem.FERTILE_SOILS[0])


test('Yommi growth requires water and a rune axe then fells, trims, carves and lifts the pole', totem_growth)


def evil_totem_and_seeds():
    scene = Scene(LQ_TILE.MAP_WEST)
    expect(run_wait(totem.replace_evil_totem(scene.log))).to_be(True)
    scene.item(LQ_ID.TOTEM_POLE, 'Pole')
    enter = spy_on(totem, 'enter_jungle', impl=answer(False))
    expect(run_wait(totem.replace_evil_totem(scene.log))).to_be(False)
    enter.mock_implementation(answer(True))
    scene.walk_ok = False
    expect(run_wait(totem.replace_evil_totem(scene.log))).to_be(False)
    scene.walk_ok = True
    use = spy_on(totem, 'use_on_loc', impl=answer(False))
    expect(run_wait(totem.replace_evil_totem(scene.log))).to_be(False)
    scene.npc(LQ_NPC.NEZIKCHENED, ['Attack'])

    def won(plan, log):
        expect(plan.done()).to_be(False)
        scene.npcs = []
        return plan.done()
        yield

    spy_on(totem, 'fight', impl=won)

    def replace(id, opts, prefer, goal, log):
        scene.take(id)
        return goal()
        yield

    use.mock_implementation(replace)
    expect(run_wait(totem.replace_evil_totem(scene.log))).to_be(True)
    expect(run_wait(totem.ask_for_more_seeds(scene.log))).to_be(False)
    scene.npc(LQ_NPC.UNGADULU, effect=lambda op: False)
    expect(run_wait(totem.ask_for_more_seeds(scene.log))).to_be(False)
    scene.npcs = []
    scene.npc(LQ_NPC.UNGADULU, effect=give(scene, LQ_ID.YOMMI_SEEDS))
    expect(run_wait(totem.ask_for_more_seeds(scene.log))).to_be(True)
    expect(run_wait(totem.ask_for_more_seeds(scene.log))).to_be(True)


test('the evil totem is replaced after fighting its demon and lost seeds can be requested again', evil_totem_and_seeds)
