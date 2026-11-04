"""Regicide bomb production, forest combat, messenger and catapult finale."""

import _core
from rs2004.game import reader
from rs2004.quests.defs.regicide import bomb, finish, isafdar
from rs2004.quests.defs.regicide.areas import RG_ITEM, RG_LOC, RG_NPC, RG_TILE


def answer(value):
    def wait(*args, **kwargs):
        return value
        yield
    return wait


def give(scene, item):
    def effect(*args):
        scene.item(item.id, item.name)
    return effect


def consume(scene, item):
    return lambda *args: scene.take(item.id)


def world():
    scene = Scene(RG_TILE.ARDOUGNE_BANK)

    def walk(dest, radius, stage, log):
        result = yield from scene._walk(dest, radius, log=log)
        return result

    for module in [bomb, finish, isafdar]:
        spy_on(module, 'walk_to', impl=walk)
    return scene


RECIPES = [
    [bomb.weave_cloth, RG_ITEM.BALL_OF_WOOL, RG_LOC.LOOM, RG_ITEM.CLOTH],
    [bomb.fill_tar, RG_ITEM.BARREL, RG_LOC.TAR, RG_ITEM.BARREL_TAR],
    [bomb.heat_quicklime, RG_ITEM.LIMESTONE, RG_LOC.FURNACE, RG_ITEM.QUICKLIME],
    [bomb.cook_rabbit, RG_ITEM.RAW_RABBIT, bomb.RANGE_LOC, RG_ITEM.COOKED_RABBIT],
]


def recipe(fn, source, loc, product):
    scene = world()
    scene.walk_ok = False
    expect(run_wait(fn(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(fn(scene.log))).to_be(False)
    scene.loc('Recipe target', id=loc)
    scene.item(source.id, source.name, on_use=lambda target: False)
    expect(run_wait(fn(scene.log))).to_be(False)
    scene.pack = []
    scene.item(source.id, source.name)
    expect(run_wait(fn(scene.log))).to_be(False)
    scene.pack = []
    scene.item(source.id, source.name, on_use=give(scene, product))
    expect(run_wait(fn(scene.log))).to_be(True)
    expect(scene.has(product.id)).to_be(True)


test_each(RECIPES)('Regicide recipe requires an actual product: %s', recipe)


def raw_materials():
    for fn, item in [[bomb.take_barrel, RG_ITEM.BARREL], [bomb.take_pot, RG_ITEM.POT]]:
        scene = world()
        scene.walk_ok = False
        expect(run_wait(fn(scene.log))).to_be(False)
        scene.walk_ok = True
        expect(run_wait(fn(scene.log))).to_be(False)
        scene.on_ground(item.id, item.name, effect=lambda op: False)
        expect(run_wait(fn(scene.log))).to_be(False)
        scene.ground = []
        scene.on_ground(item.id, item.name)
        expect(run_wait(fn(scene.log))).to_be(True)
        restore_all()
    scene = world()
    scene.walk_ok = False
    expect(run_wait(bomb.take_sulphur(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(bomb.take_sulphur(scene.log))).to_be(False)
    scene.loc('Sulphur', ['Take'], id=bomb.RG_SULPHUR_LOCS[0], effect=give(scene, RG_ITEM.SULPHUR))
    expect(run_wait(bomb.take_sulphur(scene.log))).to_be(True)
    scene.at = None
    expect(bomb.reachable_loc(bomb.RG_SULPHUR_LOCS)).to_be_defined()
    for fn, lump, dust in [[bomb.grind_sulphur, RG_ITEM.SULPHUR, RG_ITEM.SULPHUR_DUST],
                           [bomb.grind_quicklime, RG_ITEM.QUICKLIME, RG_ITEM.QUICKLIME_DUST]]:
        scene.pack = []
        expect(run_wait(fn(scene.log))).to_be(False)
        scene.item(RG_ITEM.PESTLE.id, RG_ITEM.PESTLE.name, on_use=lambda target: False)
        scene.item(lump.id, lump.name)
        expect(run_wait(fn(scene.log))).to_be(False)
        scene.take(lump.id)
        scene.item(lump.id, lump.name, on_use=give(scene, dust))
        expect(run_wait(fn(scene.log))).to_be(True)


test('camp spawns and sulphur are taken before both powders are ground in either direction', raw_materials)


def rabbit():
    scene = world()
    expect(run_wait(bomb.take_rabbit_corpse(scene.log))).to_be(False)
    scene.walk_ok = False
    expect(run_wait(bomb.catch_rabbit(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(bomb.catch_rabbit(scene.log))).to_be(False)
    scene.npc('Rabbit', ['Attack'], id=RG_NPC.RABBIT, effect=lambda op: False)
    expect(run_wait(bomb.catch_rabbit(scene.log))).to_be(False)
    scene.npcs = []
    scene.npc('Rabbit', ['Attack'], id=RG_NPC.RABBIT)
    expect(run_wait(bomb.catch_rabbit(scene.log))).to_be(False)
    scene.npcs = []
    scene.npc('Rabbit', ['Attack'], id=RG_NPC.RABBIT,
              effect=lambda op: scene.on_ground(RG_ITEM.RAW_RABBIT.id, RG_ITEM.RAW_RABBIT.name))
    expect(run_wait(bomb.catch_rabbit(scene.log))).to_be(True)
    expect(run_wait(bomb.catch_rabbit(scene.log))).to_be(True)
    scene.pack = []
    scene.on_ground(RG_ITEM.RAW_RABBIT.id, RG_ITEM.RAW_RABBIT.name, effect=lambda op: False)
    expect(run_wait(bomb.catch_rabbit(scene.log))).to_be(False)


test('rabbits are attacked until meat is on the floor and then picked up', rabbit)


def powders_and_fuse():
    scene = world()
    expect(run_wait(bomb.mix_bomb(scene.log))).to_be(False)
    scene.item(RG_ITEM.BARREL_NAPHTHA.id, RG_ITEM.BARREL_NAPHTHA.name)
    expect(run_wait(bomb.mix_bomb(scene.log))).to_be(False)
    scene.item(RG_ITEM.QUICKLIME_DUST.id, RG_ITEM.QUICKLIME_DUST.name, on_use=lambda target: False)
    expect(run_wait(bomb.mix_bomb(scene.log))).to_be(False)
    scene.take(RG_ITEM.QUICKLIME_DUST.id)
    scene.item(RG_ITEM.QUICKLIME_DUST.id, RG_ITEM.QUICKLIME_DUST.name)
    expect(run_wait(bomb.mix_bomb(scene.log))).to_be(False)
    scene.take(RG_ITEM.QUICKLIME_DUST.id)
    scene.item(RG_ITEM.QUICKLIME_DUST.id, RG_ITEM.QUICKLIME_DUST.name, on_use=consume(scene, RG_ITEM.QUICKLIME_DUST))

    def seal(target):
        scene.take(RG_ITEM.SULPHUR_DUST.id)
        scene.item(RG_ITEM.BARREL_LID.id, RG_ITEM.BARREL_LID.name)

    scene.item(RG_ITEM.SULPHUR_DUST.id, RG_ITEM.SULPHUR_DUST.name, on_use=seal)
    expect(run_wait(bomb.mix_bomb(scene.log))).to_be(True)
    expect(run_wait(bomb.mix_bomb(scene.log))).to_be(True)
    expect(run_wait(bomb.fuse_bomb(scene.log))).to_be(False)
    scene.item(RG_ITEM.CLOTH.id, RG_ITEM.CLOTH.name, on_use=lambda target: False)
    expect(run_wait(bomb.fuse_bomb(scene.log))).to_be(False)
    scene.take(RG_ITEM.CLOTH.id)
    scene.item(RG_ITEM.CLOTH.id, RG_ITEM.CLOTH.name, on_use=give(scene, RG_ITEM.BARREL_FUSED))
    expect(run_wait(bomb.fuse_bomb(scene.log))).to_be(True)


test('both powders must be consumed before the cloth can fuse the sealed barrel', powders_and_fuse)


def still():
    scene = world()
    scene.walk_ok = False
    expect(run_wait(bomb.distil_naphtha(scene.log))).to_be(False)
    scene.walk_ok = True
    use = spy_on(bomb, 'use_held_on_loc', impl=answer(False))
    expect(run_wait(bomb.distil_naphtha(scene.log))).to_be(False)
    scene.main_modal = bomb.STILL_ROOT
    scene.total = 0
    spy_on(reader, 'varp', impl=lambda id: scene.total if id == bomb.VARP_STILL_TOTAL else (1 << 19) | (1 << 27) | (1 << 31))
    button = spy_on(reader, 'button_by_text', returns=-1)
    scene.item(RG_ITEM.COAL.id, RG_ITEM.COAL.name)
    expect(run_wait(bomb.distil_naphtha(scene.log))).to_be(False)
    scene.main_modal = bomb.STILL_ROOT
    button.mock_return_value(123)

    def clicked(id):
        scene.total += 10

    spy_on(_core, 'click_component', impl=clicked)
    scene.later(lambda: setattr(scene, 'total', bomb.STILL_TARGET))
    scene.later(give(scene, RG_ITEM.BARREL_NAPHTHA))
    expect(run_wait(bomb.distil_naphtha(scene.log))).to_be(True)
    expect(run_wait(bomb.distil_naphtha(scene.log))).to_be(True)
    expect(bomb.read_still().total).to_be(bomb.STILL_TARGET)


test('the still resolves menu captions, works its gauges and hands over naphtha only after closing', still)


def messenger_and_talks():
    scene = world()
    stub(isafdar.messenger, armed=False)
    relog = spy_on(_core, 'relog', returns=None)
    expect(run_wait(isafdar.take_summons(scene.log))).to_be(True)
    expect(len(relog.calls)).to_be(1)
    expect(run_wait(isafdar.take_summons(scene.log))).to_be(False)
    scene.npc('Messenger', id=RG_NPC.MESSENGER)
    talk = spy_on(isafdar, 'talk_strict', impl=answer(True))
    expect(run_wait(isafdar.take_summons(scene.log))).to_be(True)
    scene.later(give(scene, RG_ITEM.SUMMONS))
    expect(run_wait(isafdar.take_summons(scene.log))).to_be(True)
    expect(run_wait(isafdar.take_summons(scene.log))).to_be(True)
    for fn in [isafdar.ask_iorwerth, isafdar.ask_tracker]:
        scene.walk_ok = False
        expect(run_wait(fn(1, scene.log))).to_be(False)
        scene.walk_ok = True
        scene.talk_status = 'unreachable'
        expect(run_wait(fn(1, scene.log))).to_be(False)
        scene.talk_status = 'done'
        expect(run_wait(fn(1, scene.log))).to_be(True)
    scene.walk_ok = False
    expect(run_wait(isafdar.brief_from_lathas(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(isafdar.brief_from_lathas(scene.log))).to_be(True)
    expect(run_wait(isafdar.meet_scouts(scene.log))).to_be(False)
    scene.chat.pages = ['continue']
    expect(run_wait(isafdar.meet_scouts(scene.log))).to_be(True)


test('the summons arms its login timer once and the forest scouts must finish their chain', messenger_and_talks)


def soldier():
    scene = world()
    scene.walk_ok = False
    expect(run_wait(isafdar.follow_tracks(scene.log))).to_be(False)
    expect(run_wait(isafdar.kill_soldier(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(isafdar.follow_tracks(scene.log))).to_be(False)
    scene.loc('Tracks', ['Follow'], id=RG_LOC.FOOTPRINTS)
    expect(run_wait(isafdar.follow_tracks(scene.log))).to_be(True)
    expect(run_wait(isafdar.kill_soldier(scene.log))).to_be(False)
    scene.loc('Crossing', ['Enter'], id=3998)
    expect(run_wait(isafdar.kill_soldier(scene.log))).to_be(False)
    scene.npc('Guard', ['Attack'], id=RG_NPC.CAMP_GUARD, effect=lambda op: False)
    expect(run_wait(isafdar.kill_soldier(scene.log))).to_be(False)
    scene.stats['hp_fraction'] = 0.2
    expect(run_wait(isafdar.kill_soldier(scene.log))).to_be(False)
    expect(scene.logged('breaking off')).to_be(True)
    scene.stats['hp_fraction'] = 1
    scene.npcs = []
    scene.npc('Guard', ['Attack'], id=RG_NPC.CAMP_GUARD, effect=lambda op: scene.npcs.clear())
    expect(run_wait(isafdar.kill_soldier(scene.log))).to_be(True)
    scene.npcs = []
    expect(run_wait(isafdar.fight_soldier(scene.log))).to_be(True)
    expect(run_wait(isafdar.enter_camp(scene.log))).to_be(True)


test('the camp guard is fought with renewed attacks and abandoned when health and food run out', soldier)


def catapult():
    for fn, item, id, npc in [[finish.feed_lazy_guard, RG_ITEM.COOKED_RABBIT, RG_NPC.LAZY_GUARD, True],
                              [finish.fire_catapult, RG_ITEM.BARREL_FUSED, RG_LOC.CATAPULT, False]]:
        scene = world()
        scene.walk_ok = False
        expect(run_wait(fn(scene.log))).to_be(False)
        scene.walk_ok = True
        expect(run_wait(fn(scene.log))).to_be(False)
        if npc:
            scene.npc('Guard', id=id)
        else:
            scene.loc('Catapult', id=id)
        scene.item(item.id, item.name, on_use=lambda target: False)
        expect(run_wait(fn(scene.log))).to_be(False)
        scene.pack = []
        scene.item(item.id, item.name)
        expect(run_wait(fn(scene.log))).to_be(False)
        scene.pack = []
        scene.item(item.id, item.name, on_use=consume(scene, item))
        expect(run_wait(fn(scene.log))).to_be(True)
        restore_all()


test('only the lazy guard takes the rabbit and the catapult must consume the fused bomb', catapult)


def final_letter():
    scene = world()
    expect(run_wait(finish.meet_arianwyn(scene.log))).to_be(False)
    expect(run_wait(finish.report_to_lathas(scene.log))).to_be(False)
    scene.walk_ok = False
    expect(run_wait(finish.report_to_iorwerth(scene.log))).to_be(False)
    scene.walk_ok = True
    talk = spy_on(finish, 'talk_strict', impl=answer(False))
    expect(run_wait(finish.report_to_iorwerth(scene.log))).to_be(False)
    talk.mock_implementation(answer(True))
    expect(run_wait(finish.report_to_iorwerth(scene.log))).to_be(False)
    scene.item(RG_ITEM.MESSAGE.id, RG_ITEM.MESSAGE.name)
    expect(run_wait(finish.report_to_iorwerth(scene.log))).to_be(True)
    scene.walk_ok = False
    expect(run_wait(finish.report_to_lathas(scene.log))).to_be(False)
    expect(run_wait(finish.meet_arianwyn(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(finish.report_to_lathas(scene.log))).to_be(True)
    expect(run_wait(finish.meet_arianwyn(scene.log))).to_be(False)
    scene.later(lambda: scene.chat.pages.append('continue'))
    expect(run_wait(finish.meet_arianwyn(scene.log))).to_be(True)


test('the finale carries Iorwerth letter through Arianwyn ambush to Lathas', final_letter)
