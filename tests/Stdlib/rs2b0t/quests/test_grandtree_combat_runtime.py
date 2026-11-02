"""Grand Tree's trapdoor, demon spawn and Strike fight against Scene facades."""

from rs2004.game import direct_navigator, game
from rs2004.entities import npcs
from rs2004.geometry import Tile
from rs2004.navigation import reachability
from rs2004.quests.defs.grandtree import fight
from rs2004.quests.defs.grandtree.areas import GT_LOC, GT_NPC, GT_TILE
from rs2004.quests.strike_combat import DEMON_COVER
from rs2004.tabs import autocast, prayer


def move(scene, tile):
    def effect(op):
        scene.at = tile
        return True
    return effect


def trapdoor():
    scene = Scene(GT_TILE.cave_landing)
    expect(run_wait(fight.descend_trapdoor(scene.log))).to_be(True)
    expect(scene.walks).to_equal([])
    scene.at = None
    scene.walk_ok = False
    expect(run_wait(fight.descend_trapdoor(scene.log))).to_be(False)
    scene.at = GT_TILE.pillar_floor
    scene.no_walk = [GT_TILE.trapdoor_stand]
    scene.walk_ok = True
    expect(run_wait(fight.descend_trapdoor(scene.log))).to_be(False)
    scene.no_walk = []
    expect(run_wait(fight.descend_trapdoor(scene.log))).to_be(False)
    expect(scene.logged('no trapdoor')).to_be(True)
    scene.loc('Trapdoor', ['Open'], id=999, dist=0)
    expect(run_wait(fight.descend_trapdoor(scene.log))).to_be(False)
    door = scene.loc('Trapdoor', ['Open'], id=GT_LOC.TRAPDOOR_SHUT, effect=lambda op: False)
    expect(run_wait(fight.descend_trapdoor(scene.log))).to_be(False)
    door._fields['interact'] = lambda op: True
    before = scene.clock
    expect(run_wait(fight.descend_trapdoor(scene.log))).to_be(False)
    expect(scene.clock - before >= 12000).to_be(True)
    expect(scene.logged('did not drop us')).to_be(True)
    door._fields['interact'] = move(scene, GT_TILE.cave_landing)
    expect(run_wait(fight.descend_trapdoor(scene.log))).to_be(True)
    expect(scene.at).to_equal(GT_TILE.cave_landing)
    expect(scene.walks[-1]).to_equal(GT_TILE.trapdoor_stand)


test('Grand Tree opens its trapdoor and confirms arrival in the caves', trapdoor)


def combat_world(at):
    scene = Scene(at)
    scene.stats['magic'] = 1
    scene.stats['prayer'] = 1
    scene.item(558, 'Mind rune')
    scene.item(556, 'Air rune', count=20)
    scene.casts = []
    scene.cast_ok = True
    spy_on(game, 'set_auto_retaliate', returns=True)
    spy_on(game, 'auto_retaliate_on', returns=False)
    spy_on(autocast, 'armed', returns=False)
    spy_on(prayer, 'active', returns=False)
    spy_on(prayer, 'points', returns=0)
    spy_on(reachability, 'line_of_sight', returns=True)
    spy_on(direct_navigator, 'walk', returns=True)
    spy_on(npcs, 'all', impl=lambda: list(scene.npcs))

    def cast(spell, target):
        scene.casts.append((spell, target.id, scene.at))
        if not scene.cast_ok:
            return False
        scene.take(558)
        scene.npcs = []
        return True

    spy_on(game, 'cast_on_npc', impl=cast)
    return scene


def spawn_demon(scene):
    npc = scene.npc('Black Demon', ['Attack'], id=GT_NPC.BLACK_DEMON, tile=Tile(DEMON_COVER.x + 4, DEMON_COVER.z, 0))
    npc._fields['size'] = 1
    npc._fields['network_tile'] = npc.tile
    return npc


def missing_demon():
    for start, timeout in [(GT_TILE.cave_landing, 15000), (GT_TILE.pillar_floor, 90000)]:
        scene = combat_world(start)
        scene.loc('Trapdoor', ['Open'], id=GT_LOC.TRAPDOOR_SHUT, effect=move(scene, GT_TILE.cave_landing))
        scene.loc('Ladder', ['Climb-up'], effect=move(scene, GT_TILE.narnode))
        scene.npc('Black Demon', ['Attack'], id=999)
        scene.npc('Black Demon', ['Attack'], id=GT_NPC.BLACK_DEMON, dist=21)
        expect(run_wait(fight.fight_black_demon(scene.log))).to_be(False)
        expect(scene.clock >= timeout).to_be(True)
        expect(scene.logged('climbing back out')).to_be(True)
        expect(scene.logged("waiting out Glough's speech")).to_be(start == GT_TILE.pillar_floor)
        expect(scene.at).to_equal(GT_TILE.narnode)
        expect(scene.casts).to_equal([])


test('Grand Tree waits for the demon then exits to retry when the spawn is missing', missing_demon)


def demon_fight():
    scene = combat_world(GT_TILE.pillar_floor)

    def spawn():
        spawn_demon(scene)

    def drop(op):
        expect(op).to_be('Open')
        scene.at = GT_TILE.cave_landing
        scene.later(lambda: None)
        scene.later(lambda: None)
        scene.later(spawn)
        return True

    scene.loc('Trapdoor', ['Open'], id=GT_LOC.TRAPDOOR_SHUT, effect=drop)
    expect(run_wait(fight.fight_black_demon(scene.log))).to_be(True)
    expect(scene.logged("waiting out Glough's speech")).to_be(True)
    expect(scene.casts).to_equal([('Wind Strike', GT_NPC.BLACK_DEMON, DEMON_COVER)])
    expect(scene.at).to_equal(DEMON_COVER)
    expect(scene.has(558)).to_be(False)
    expect(scene.npcs).to_equal([])
    expect(scene.logged('down after 1 attacks')).to_be(True)


test('Grand Tree waits through the cutscene and wins by casting from demon cover', demon_fight)


def combat_failures():
    scene = combat_world(GT_TILE.cave_landing)
    scene.take(558)
    expect(run_wait(fight.fight_black_demon(scene.log))).to_be(False)
    expect(scene.walks).to_equal([])
    expect(scene.casts).to_equal([])
    scene.item(558, 'Mind rune', count=10)
    scene.at = GT_TILE.pillar_floor
    scene.no_walk = [GT_TILE.trapdoor_stand]
    expect(run_wait(fight.fight_black_demon(scene.log))).to_be(False)
    expect(scene.casts).to_equal([])
    scene.at = GT_TILE.cave_landing
    scene.no_walk = []
    target = spawn_demon(scene)
    scene.cast_ok = False
    expect(run_wait(fight.fight_black_demon(scene.log))).to_be(False)
    expect(scene.npcs).to_equal([target])
    expect(scene.casts).to_equal([('Wind Strike', GT_NPC.BLACK_DEMON, DEMON_COVER)])
    expect(scene.logged('no cast landed from cover')).to_be(True)


test('Grand Tree stops on missing runes, failed entry or a refused combat cast', combat_failures)
