"""Underground Pass quest actions: traps, orbs, crests, Kardia and the doll of Iban."""

from rs2004.game import direct_navigator, game
from rs2004.geometry import Tile
from rs2004.items import equipment
from rs2004.navigation import reachability
from rs2004.quests.defs.upass import area1, area2, bridge, cavern, doll
from rs2004.quests.defs.upass.areas import UP_BADGES, UP_ITEM, UP_LOC, UP_NPC, UP_ORBS, UP_TILE
from rs2004.quests.engine.types import QuestSnapshot


def answer(value):
    def wait(*args, **kwargs):
        return value
        yield
    return wait


def give(scene, item):
    def effect(*args):
        scene.item(item.id, item.name)
    return effect


def consume(scene, id):
    return lambda *args: scene.take(id)


def world():
    scene = Scene(UP_TILE.KOFTIK_BRIDGE)
    spy_on(bridge, 'travel_to', impl=scene._walk)
    spy_on(direct_navigator, 'walk_to', impl=scene._walk)
    spy_on(bridge, 'prayer_upkeep', impl=answer(True))
    for module in [area2, cavern, doll]:
        spy_on(module, 'walk_to', impl=scene._walk)
    return scene


def wall_gates():
    scene = world()
    scene.at = UP_TILE.WALL_GATE_EAST
    spy_on(bridge, 'walk_to', impl=scene._walk)
    scene.walk_ok = False
    expect(run_wait(bridge.cross_to_west(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(bridge.cross_to_west(scene.log))).to_be(False)
    scene.loc('Gate', ['Open'], id=UP_LOC.WALL_DOOR_L, tile=UP_TILE.WALL_GATE_EAST, effect=lambda op: False)
    expect(run_wait(bridge.cross_to_west(scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Gate', ['Open'], id=UP_LOC.WALL_DOOR_L, tile=UP_TILE.WALL_GATE_EAST)
    expect(run_wait(bridge.cross_to_west(scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Gate', ['Open'], id=UP_LOC.WALL_DOOR_L, tile=UP_TILE.WALL_GATE_EAST,
              effect=lambda op: setattr(scene, 'at', UP_TILE.WALL_GATE_WEST))
    expect(run_wait(bridge.cross_to_west(scene.log))).to_be(True)
    expect(run_wait(bridge.cross_to_west(scene.log))).to_be(True)
    scene.locs = []
    scene.loc('Gate', ['Open'], id=UP_LOC.WALL_DOOR_R, tile=UP_TILE.WALL_GATE_WEST,
              effect=lambda op: setattr(scene, 'at', UP_TILE.WALL_GATE_EAST))
    expect(run_wait(bridge.cross_to_east(scene.log))).to_be(True)
    expect(run_wait(bridge.cross_to_east(scene.log))).to_be(True)


test('Ardougne wall gates require the far landing and support both directions without recrossing', wall_gates)


def cavern_recovery():
    scene = world()
    drop = spy_on(area2, 'drop_boulder', impl=answer(False))
    spy_on(area2, 'take_unicorn_horn', impl=answer(True))
    expect(run_wait(area2.crush_unicorn(scene.log))).to_be(False)
    drop.mock_implementation(answer(True))
    expect(run_wait(area2.crush_unicorn(scene.log))).to_be(True)
    scene.item(UP_ITEM.GAUNTLETS.id, UP_ITEM.GAUNTLETS.name)
    spy_on(equipment, 'equip', impl=answer(False))
    expect(run_wait(cavern.wear_gauntlets(scene.log))).to_be(False)
    inside = spy_on(cavern, 'inside_witch_house', returns=True)
    scene.at = UP_TILE.WITCH_DOOR
    scene.loc('Door', ['Open'], id=UP_LOC.WITCH_DOOR, effect=lambda op: False)
    expect(run_wait(cavern.leave_witch_house(scene.log))).to_be(False)
    expect(scene.logged('still shut')).to_be(True)
    inside.mock_return_value(False)
    expect(run_wait(cavern.leave_witch_house(scene.log))).to_be(True)
    expect(area1.orbs_held(QuestSnapshot(inv_ids={UP_ITEM.ORB1.id: 1}))).to_be(1)

    def corridor(dest, what, visible, send, arrived, log):
        expect(visible()).to_be(True)
        result = yield from send()
        return result

    spy_on(area1, 'corridor_hop', impl=corridor)
    scene.at = UP_TILE.LOGTRAP
    scene.loc('Trigger', ['Disarm'], id=UP_LOC.LOGTRAP_TRIGGER)
    spy_on(area1, 'drive_dialog', impl=answer(True))
    spy_on(area1, 'drive_until', impl=answer(False))
    expect(run_wait(area1.take_trapped_orb(scene.log))).to_be(False)
    scene.item(UP_ITEM.ORB1.id, UP_ITEM.ORB1.name)
    scene.loc('Furnace', id=UP_LOC.FURNACE)
    expect(run_wait(area1.burn_orbs(scene.log))).to_be(False)


test('cavern recovery handles failed unicorn drops, gauntlet refusals and the sealed witch door', cavern_recovery)


GATHERING = [
    [area2.take_railing, UP_LOC.RAILINGS_LOOSE, 'Search', UP_ITEM.RAILING],
    [area2.take_unicorn_horn, UP_LOC.UNICORN_CAGE, 'Search', UP_ITEM.UNICORN_HORN],
    [doll.open_sealed_chest, UP_LOC.SEALED_CHEST, 'Open', UP_ITEM.SHADOW],
    [doll.search_cages, UP_LOC.CAGE_DOVE, 'Search', UP_ITEM.DOVE],
]


def gathering(fn, id, op, item):
    scene = world()
    scene.walk_ok = False
    expect(run_wait(fn(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(fn(scene.log))).to_be(False)
    scene.loc('Quest object', [op], id=id, effect=lambda op: False)
    expect(run_wait(fn(scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Quest object', [op], id=id)
    expect(run_wait(fn(scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Quest object', [op], id=id, effect=give(scene, item))
    expect(run_wait(fn(scene.log))).to_be(True)
    expect(run_wait(fn(scene.log))).to_be(True)


test_each(GATHERING)('Underground Pass gathering requires an actual item: %s', gathering)


def drop_and_fight():
    scene = world()
    expect(run_wait(bridge.take_drop(123, scene.log))).to_be(False)
    scene.on_ground(123, 'Drop', effect=lambda op: False)
    expect(run_wait(bridge.take_drop(123, scene.log))).to_be(False)
    scene.ground = []
    scene.on_ground(123, 'Drop')
    expect(run_wait(bridge.take_drop(123, scene.log))).to_be(True)
    expect(run_wait(bridge.take_drop(123, scene.log))).to_be(True)
    expect(run_wait(bridge.fight_until_gone(lambda: None, scene.log))).to_be(True)
    npc = scene.npc('Enemy', ['Attack'], effect=lambda op: False)
    expect(run_wait(bridge.fight_until_gone(lambda: npc, scene.log))).to_be(False)
    scene.npcs = []
    npc = scene.npc('Enemy', ['Attack'])
    scene.chat.pages = ['continue']
    expect(run_wait(bridge.fight_until_gone(lambda: npc, scene.log))).to_be(False)
    scene.npcs = []
    scene.npc('Enemy', ['Attack'], effect=lambda op: scene.npcs.clear())
    expect(run_wait(bridge.fight_until_gone(lambda: scene.npcs[0] if scene.npcs else None, scene.log))).to_be(True)


test('pass combat renews attacks and waits for delayed drops before retrying Take', drop_and_fight)


def fire_arrow():
    scene = world()
    expect(run_wait(bridge.make_fire_arrow(scene.log))).to_be(False)
    scene.item(UP_ITEM.DAMP_CLOTH.id, UP_ITEM.DAMP_CLOTH.name, on_use=lambda target: False)
    scene.item(UP_ITEM.BRONZE_ARROW.id, UP_ITEM.BRONZE_ARROW.name)
    expect(run_wait(bridge.make_fire_arrow(scene.log))).to_be(False)
    scene.take(UP_ITEM.DAMP_CLOTH.id)
    scene.item(UP_ITEM.DAMP_CLOTH.id, UP_ITEM.DAMP_CLOTH.name)
    expect(run_wait(bridge.make_fire_arrow(scene.log))).to_be(False)
    scene.take(UP_ITEM.DAMP_CLOTH.id)
    scene.item(UP_ITEM.DAMP_CLOTH.id, UP_ITEM.DAMP_CLOTH.name, on_use=give(scene, UP_ITEM.UNLIT_ARROW))
    expect(run_wait(bridge.make_fire_arrow(scene.log))).to_be(False)
    scene.item(UP_ITEM.TINDERBOX.id, UP_ITEM.TINDERBOX.name)
    scene.take(UP_ITEM.UNLIT_ARROW.id)
    scene.item(UP_ITEM.UNLIT_ARROW.id, UP_ITEM.UNLIT_ARROW.name, on_use=lambda target: False)
    expect(run_wait(bridge.make_fire_arrow(scene.log))).to_be(False)
    scene.take(UP_ITEM.UNLIT_ARROW.id)
    scene.item(UP_ITEM.UNLIT_ARROW.id, UP_ITEM.UNLIT_ARROW.name, on_use=give(scene, UP_ITEM.LIT_ARROW))
    expect(run_wait(bridge.make_fire_arrow(scene.log))).to_be(True)
    expect(run_wait(bridge.make_fire_arrow(scene.log))).to_be(True)
    scene.item(UP_ITEM.SHORTBOW.id, UP_ITEM.SHORTBOW.name, effect=lambda op: False)
    expect(run_wait(bridge.arm_fire_arrow(scene.log))).to_be(False)
    scene.take(UP_ITEM.SHORTBOW.id)
    expect(run_wait(bridge.arm_fire_arrow(scene.log))).to_be(True)
    scene.take(UP_ITEM.LIT_ARROW.id)
    scene.item(UP_ITEM.LIT_ARROW.id, UP_ITEM.LIT_ARROW.name, effect=lambda op: False)
    expect(run_wait(bridge.arm_fire_arrow(scene.log))).to_be(False)


test('the fire arrow wraps cloth then uses the unlit arrow on the tinderbox', fire_arrow)


def rope_shot():
    scene = world()
    scene.walk_ok = False
    expect(run_wait(bridge.shoot_guiderope(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(bridge.shoot_guiderope(scene.log))).to_be(False)
    scene.loc('Rope', ['Fire-at'], id=UP_LOC.GUIDEROPE, effect=lambda op: False)
    expect(run_wait(bridge.shoot_guiderope(scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Rope', ['Fire-at'], id=UP_LOC.GUIDEROPE)
    expect(run_wait(bridge.shoot_guiderope(scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Rope', ['Fire-at'], id=UP_LOC.GUIDEROPE, effect=lambda op: scene.say('Your arrow misses'))
    expect(run_wait(bridge.shoot_guiderope(scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Rope', ['Fire-at'], id=UP_LOC.GUIDEROPE,
              effect=lambda op: setattr(scene, 'at', Tile(2440, scene.at.z, 0)))
    expect(run_wait(bridge.shoot_guiderope(scene.log))).to_be(True)
    expect(scene.logged('impaled the rope')).to_be(True)


test('a rope shot probes silent stands but stops after a real miss spends the arrow', rope_shot)


def unicorn_and_well():
    scene = world()
    scene.walk_ok = False
    expect(run_wait(area2.drop_boulder(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(area2.drop_boulder(scene.log))).to_be(False)
    scene.loc('Cage', id=UP_LOC.UNICORN_CAGE)
    expect(run_wait(area2.drop_boulder(scene.log))).to_be(True)
    scene.npc('Boulder', id=UP_NPC.BOULDER)
    expect(run_wait(area2.drop_boulder(scene.log))).to_be(False)
    scene.item(UP_ITEM.RAILING.id, UP_ITEM.RAILING.name, on_use=lambda target: False)
    expect(run_wait(area2.drop_boulder(scene.log))).to_be(False)
    scene.take(UP_ITEM.RAILING.id)
    scene.item(UP_ITEM.RAILING.id, UP_ITEM.RAILING.name,
               on_use=lambda target: setattr(scene, 'at', Tile(scene.at.x - 25, scene.at.z, 0)))
    expect(run_wait(area2.drop_boulder(scene.log))).to_be(True)
    scene.walk_ok = False
    expect(run_wait(area2.feed_blood_well(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(area2.feed_blood_well(scene.log))).to_be(False)
    for item in list(UP_BADGES) + [UP_ITEM.UNICORN_HORN]:
        scene.item(item.id, item.name, on_use=consume(scene, item.id))
    expect(run_wait(area2.feed_blood_well(scene.log))).to_be(False)
    scene.loc('Well', id=UP_LOC.BLOODWELL)
    expect(run_wait(area2.feed_blood_well(scene.log))).to_be(True)
    expect(scene.logged('fed 4 item(s)')).to_be(True)


test('the unicorn boulder confirms its forced jump and the well consumes crests and horn', unicorn_and_well)


def paladins():
    scene = world()
    scene.walk_ok = False
    expect(run_wait(area2.kill_paladin(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(area2.kill_paladin(scene.log))).to_be(False)
    paladin = area2.PALADINS[0]
    scene.npc('Paladin', ['Attack'], id=paladin.npc)
    fight = spy_on(area2, 'fight_until_gone', impl=answer(False))
    expect(run_wait(area2.kill_paladin(scene.log))).to_be(False)
    fight.mock_implementation(answer(True))
    killed = set()
    expect(run_wait(area2.kill_paladin(scene.log, killed))).to_be(False)
    expect(len(killed)).to_be(0)
    scene.on_ground(paladin.badge.id, paladin.badge.name)
    expect(run_wait(area2.kill_paladin(scene.log, killed))).to_be(True)
    expect(paladin.npc in killed).to_be(True)
    kill = spy_on(area2, 'kill_paladin', impl=answer(False))
    enter = spy_on(area2, 'enter_main_cavern', impl=answer(False))
    expect(run_wait(area2.cross_the_temple(scene.log))).to_be(False)
    enter.mock_implementation(answer(True))
    expect(run_wait(area2.cross_the_temple(scene.log))).to_be(True)
    scene.at = Tile(scene.at.x, scene.at.z, 1)
    expect(run_wait(area2.cross_the_temple(scene.log))).to_be(True)


test('paladins whose crest never arrives remain eligible for the next crossing', paladins)


def cat_and_dwarves():
    scene = world()
    scene.walk_ok = False
    expect(run_wait(cavern.catch_cat(scene.log))).to_be(False)
    expect(run_wait(cavern.ask_nilhoof(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(cavern.catch_cat(scene.log))).to_be(False)
    expect(run_wait(cavern.ask_nilhoof(scene.log))).to_be(False)
    scene.npc('Cat', ['Take'], id=UP_NPC.WITCH_CAT, effect=lambda op: False)
    expect(run_wait(cavern.catch_cat(scene.log))).to_be(False)
    scene.npcs = []
    scene.npc('Cat', ['Take'], id=UP_NPC.WITCH_CAT, effect=give(scene, UP_ITEM.WITCH_CAT))
    expect(run_wait(cavern.catch_cat(scene.log))).to_be(True)
    expect(run_wait(cavern.catch_cat(scene.log))).to_be(True)
    scene.npc('Nilhoof', id=UP_NPC.NILHOOF)
    scene.talk_status = 'unreachable'
    expect(run_wait(cavern.ask_nilhoof(scene.log))).to_be(False)
    scene.talk_status = 'done'
    spy_on(cavern, 'talk_strict', impl=answer(True))
    expect(run_wait(cavern.ask_nilhoof(scene.log))).to_be(True)
    scene.npc('Klank', id=UP_NPC.KLANK)
    expect(run_wait(cavern.ask_klank(scene.log))).to_be(True)
    expect(run_wait(cavern.wear_gauntlets(scene.log))).to_be(True)
    scene.item(UP_ITEM.GAUNTLETS.id, UP_ITEM.GAUNTLETS.name)
    expect(run_wait(cavern.wear_gauntlets(scene.log))).to_be(True)


test('the witch cat is caught and dwarves are addressed by id before wearing Klank gauntlets', cat_and_dwarves)


def witch_distraction():
    scene = world()
    scene.item(UP_ITEM.WITCH_CAT.id, UP_ITEM.WITCH_CAT.name)
    scene.walk_ok = False
    expect(run_wait(cavern.distract_witch(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(cavern.distract_witch(scene.log))).to_be(False)
    scene.loc('Door', ['Knock'], id=UP_LOC.WITCH_DOOR)
    expect(run_wait(cavern.distract_witch(scene.log))).to_be(False)
    scene.take(UP_ITEM.WITCH_CAT.id)
    scene.item(UP_ITEM.WITCH_CAT.id, UP_ITEM.WITCH_CAT.name, on_use=consume(scene, UP_ITEM.WITCH_CAT.id))
    expect(run_wait(cavern.distract_witch(scene.log))).to_be(True)
    scene.item(UP_ITEM.WITCH_CAT.id, UP_ITEM.WITCH_CAT.name)
    scene.locs = []
    scene.loc('Door', ['Knock'], id=UP_LOC.WITCH_DOOR, effect=consume(scene, UP_ITEM.WITCH_CAT.id))
    expect(run_wait(cavern.distract_witch(scene.log))).to_be(True)
    scene.item(UP_ITEM.WITCH_CAT.id, UP_ITEM.WITCH_CAT.name)
    scene.locs = []
    scene.loc('Door', ['Knock'], id=UP_LOC.WITCH_DOOR, effect=lambda op: scene.say('Kardia is talking to her cat'))
    expect(run_wait(cavern.distract_witch(scene.log))).to_be(True)


test('Kardia distraction probes door sides and accepts the already-talking-to-cat reply', witch_distraction)


def witch_chest():
    scene = world()
    scene.loc_op_status = 'unreachable'
    expect(run_wait(cavern.loot_witch_chest(scene.log))).to_be(False)
    scene.loc_op_status = 'done'
    expect(run_wait(cavern.loot_witch_chest(scene.log))).to_be(False)
    scene.chat.shown = ["The doll's gone"]
    expect(run_wait(cavern.loot_witch_chest(scene.log))).to_be(False)
    expect(scene.logged('already been taken')).to_be(True)
    scene.chat.shown = []
    scene.later(give(scene, UP_ITEM.DOLL))
    expect(run_wait(cavern.loot_witch_chest(scene.log))).to_be(True)
    expect(run_wait(cavern.loot_witch_chest(scene.log))).to_be(True)
    scene.pack = []
    spy_on(cavern, 'catch_cat', impl=answer(False))
    loot = spy_on(cavern, 'loot_witch_chest', impl=answer(False))
    expect(run_wait(cavern.steal_the_doll(scene.log))).to_be(False)
    scene.item(UP_ITEM.WITCH_CAT.id, UP_ITEM.WITCH_CAT.name)
    spy_on(cavern, 'distract_witch', impl=answer(False))
    loot.mock_implementation(answer(True))
    expect(run_wait(cavern.steal_the_doll(scene.log))).to_be(True)
    expect(scene.logged('would not come')).to_be(True)


test('Kardia chest handles an empty chest and retries the complete cat-and-doll chain', witch_chest)


def doll_elements():
    for fn, item in [[doll.rub_ashes, UP_ITEM.ASHES], [doll.rub_shadow, UP_ITEM.SHADOW], [doll.rub_dove, UP_ITEM.DOVE]]:
        scene = world()
        expect(run_wait(fn(scene.log))).to_be(False)
        scene.item(UP_ITEM.DOLL.id, UP_ITEM.DOLL.name)
        scene.item(item.id, item.name, on_use=lambda target: False)
        expect(run_wait(fn(scene.log))).to_be(False)
        scene.take(item.id)
        scene.item(item.id, item.name, on_use=consume(scene, item.id))
        expect(run_wait(fn(scene.log))).to_be(True)
        expect(scene.has(item.id)).to_be(False)
        restore_all()


test('ashes, shadow and dove are each consumed into the doll', doll_elements)


def brew_and_tomb():
    scene = world()
    scene.walk_ok = False
    expect(run_wait(doll.fill_brew(scene.log))).to_be(False)
    expect(run_wait(doll.burn_tomb(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(doll.fill_brew(scene.log))).to_be(False)
    scene.loc('Barrel', id=UP_LOC.BREW_BARREL)
    scene.item(UP_ITEM.BUCKET.id, UP_ITEM.BUCKET.name, on_use=lambda target: False)
    expect(run_wait(doll.fill_brew(scene.log))).to_be(False)
    scene.pack = []
    scene.item(UP_ITEM.BUCKET.id, UP_ITEM.BUCKET.name, on_use=give(scene, UP_ITEM.DWARF_BREW))
    expect(run_wait(doll.fill_brew(scene.log))).to_be(True)
    expect(run_wait(doll.fill_brew(scene.log))).to_be(True)
    expect(run_wait(doll.burn_tomb(scene.log))).to_be(False)
    scene.loc('Tomb', id=UP_LOC.IBAN_TOMB_L)
    expect(run_wait(doll.burn_tomb(scene.log))).to_be(False)
    scene.take(UP_ITEM.DWARF_BREW.id)
    scene.item(UP_ITEM.DWARF_BREW.id, UP_ITEM.DWARF_BREW.name, on_use=lambda target: False)
    expect(run_wait(doll.burn_tomb(scene.log))).to_be(False)
    scene.take(UP_ITEM.DWARF_BREW.id)
    scene.item(UP_ITEM.DWARF_BREW.id, UP_ITEM.DWARF_BREW.name, on_use=consume(scene, UP_ITEM.DWARF_BREW.id))
    expect(run_wait(doll.burn_tomb(scene.log))).to_be(False)
    scene.item(UP_ITEM.TINDERBOX.id, UP_ITEM.TINDERBOX.name, on_use=lambda target: False)
    expect(run_wait(doll.burn_tomb(scene.log))).to_be(False)
    scene.take(UP_ITEM.TINDERBOX.id)
    scene.item(UP_ITEM.TINDERBOX.id, UP_ITEM.TINDERBOX.name, on_use=give(scene, UP_ITEM.ASHES))
    expect(run_wait(doll.burn_tomb(scene.log))).to_be(True)
    expect(run_wait(doll.burn_tomb(scene.log))).to_be(True)


test('Iban tomb is soaked with dwarven brew before the tinderbox produces ashes', brew_and_tomb)


def demon_amulets():
    scene = world()
    expect(run_wait(doll.kill_kalrag(scene.log))).to_be(False)
    scene.item(UP_ITEM.DOLL.id, UP_ITEM.DOLL.name)
    scene.walk_ok = False
    expect(run_wait(doll.kill_kalrag(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(doll.kill_kalrag(scene.log))).to_be(True)
    scene.npc('Kalrag', ['Attack'], id=UP_NPC.KALRAG)
    fight = spy_on(doll, 'fight_until_gone', impl=answer(False))
    expect(run_wait(doll.kill_kalrag(scene.log))).to_be(False)
    fight.mock_implementation(answer(True))
    expect(run_wait(doll.kill_kalrag(scene.log))).to_be(False)
    scene.npcs = []
    expect(run_wait(doll.kill_kalrag(scene.log))).to_be(True)
    kill = spy_on(doll, 'kill_npc', impl=answer(False))
    expect(run_wait(doll.kill_demon(scene.log))).to_be(False)
    kill.mock_implementation(answer(True))
    expect(run_wait(doll.kill_demon(scene.log))).to_be(False)
    for demon in doll.DEMONS:
        scene.on_ground(demon.amulet.id, demon.amulet.name)
        expect(run_wait(doll.kill_demon(scene.log))).to_be(True)
    expect(run_wait(doll.kill_demon(scene.log))).to_be(True)


test('Kalrag requires the doll and each demon pays its own amulet before the sealed chest', demon_amulets)


def iban_throw():
    scene = world()
    inside = spy_on(doll, 'inside_iban_temple', returns=False)
    expect(run_wait(doll.throw_doll(scene.log))).to_be(False)
    inside.mock_return_value(True)
    expect(run_wait(doll.open_iban_door(scene.log))).to_be(True)
    expect(run_wait(doll.throw_doll(scene.log))).to_be(False)
    scene.loc('Altar', id=UP_LOC.IBAN_ALTAR)
    scene.item(UP_ITEM.DOLL.id, UP_ITEM.DOLL.name, on_use=lambda target: False)
    expect(run_wait(doll.throw_doll(scene.log))).to_be(False)
    scene.take(UP_ITEM.DOLL.id)
    scene.item(UP_ITEM.DOLL.id, UP_ITEM.DOLL.name)
    expect(run_wait(doll.throw_doll(scene.log))).to_be(False)
    scene.take(UP_ITEM.DOLL.id)
    scene.item(UP_ITEM.DOLL.id, UP_ITEM.DOLL.name, on_use=consume(scene, UP_ITEM.DOLL.id))
    expect(run_wait(doll.throw_doll(scene.log))).to_be(True)
    expect(scene.has(UP_ITEM.DOLL.id)).to_be(False)


test('the Iban throw refuses outside the temple and succeeds only when the well consumes the doll', iban_throw)


def orbs():
    scene = world()
    hop = spy_on(area1, 'corridor_hop', impl=answer(False))
    for site in area1.ORB_SITES[1:]:
        scene.at = site.tile
        expect(run_wait(area1.take_ground_orb(site.orb, site.tile, scene.log))).to_be(True)
        scene.at = UP_TILE.KOFTIK_BRIDGE
        expect(run_wait(area1.take_ground_orb(site.orb, site.tile, scene.log))).to_be(False)
        hop.mock_implementation(answer(True))
        expect(run_wait(area1.take_ground_orb(site.orb, site.tile, scene.log))).to_be(True)
        scene.item(site.orb.id, site.orb.name)
        expect(run_wait(area1.take_ground_orb(site.orb, site.tile, scene.log))).to_be(True)
        hop.mock_implementation(answer(False))
    scene.at = UP_TILE.LOGTRAP
    expect(run_wait(area1.take_trapped_orb(scene.log))).to_be(True)
    scene.at = UP_TILE.KOFTIK_BRIDGE
    expect(run_wait(area1.take_trapped_orb(scene.log))).to_be(False)
    hop.mock_implementation(answer(True))
    expect(run_wait(area1.take_trapped_orb(scene.log))).to_be(False)
    scene.loc('Trigger', ['Search'], id=UP_LOC.LOGTRAP_TRIGGER)
    expect(run_wait(area1.take_trapped_orb(scene.log))).to_be(False)
    scene.later(give(scene, UP_ITEM.ORB1))
    expect(run_wait(area1.take_trapped_orb(scene.log))).to_be(True)
    expect(run_wait(area1.take_trapped_orb(scene.log))).to_be(True)
    hop.mock_implementation(answer(False))
    expect(run_wait(area1.burn_orbs(scene.log))).to_be(False)
    scene.pack = []
    expect(run_wait(area1.burn_orbs(scene.log))).to_be(True)


test('orb gathering distinguishes a burned spawn from one outside the loaded scene', orbs)


def orb_corridor():
    scene = world()
    expect(run_wait(area1.corridor_hop(scene.at, 'goal', lambda: True, answer(True), lambda: True, scene.log))).to_be(True)

    def journey(opts):
        expect(opts.goal.in_range()).to_be(True)
        expect(run_wait(opts.goal.send())).to_be(True)
        return opts.goal.arrived()
        yield

    spy_on(area1, 'stalled_journey', impl=journey)
    orb = UP_ITEM.ORB2
    scene.on_ground(orb.id, orb.name)
    expect(run_wait(area1.take_ground_orb(orb, UP_TILE.ORB2, scene.log))).to_be(True)
    scene.loc('Furnace', id=UP_LOC.FURNACE)
    scene.take(orb.id)
    scene.item(orb.id, orb.name, on_use=consume(scene, orb.id))
    expect(run_wait(area1.burn_orbs(scene.log))).to_be(True)
    scene.at = UP_TILE.LOGTRAP
    scene.loc('Trigger', ['Search'], id=UP_LOC.LOGTRAP_TRIGGER, effect=give(scene, UP_ITEM.ORB1))
    expect(run_wait(area1.take_trapped_orb(scene.log))).to_be(True)
    scene.at = UP_TILE.WELL
    scene.loc('Well', ['Climb-down'], id=UP_LOC.WELL,
              effect=lambda op: setattr(scene, 'at', Tile(scene.at.x, 9600, 0)))
    expect(run_wait(area1.enter_well(scene.log))).to_be(True)
    scene.at = UP_TILE.WELL
    scene.locs = []
    hop = spy_on(area1, 'corridor_hop', impl=answer(False))
    expect(run_wait(area1.enter_well(scene.log))).to_be(False)
    scene.loc('Well', ['Climb-down'], id=UP_LOC.WELL)
    expect(run_wait(area1.enter_well(scene.log))).to_be(False)
    scene.at = None
    expect(area1.stone_toward(UP_TILE.FURNACE, set(), scene.log)).to_be_null()
    scene.at = Tile(UP_TILE.FURNACE.x + 20, UP_TILE.FURNACE.z, 0)
    expect(area1.stone_toward(UP_TILE.FURNACE, set(), scene.log)).to_be_null()
    scene.loc('Tablet', ['Read'], id=UP_LOC.TABLET_EAST, tile=UP_TILE.FURNACE)
    spent = set()
    stone = area1.stone_toward(UP_TILE.FURNACE, spent, scene.log)
    expect(stone).to_be_defined()
    expect(run_wait(stone.send())).to_be(True)
    scene.at = UP_TILE.FURNACE
    expect(stone.arrived()).to_be(True)
    expect(area1.stone_toward(UP_TILE.FURNACE, spent, scene.log)).to_be_null()


test('the orb corridor sends stalled op-clicks, burns each orb and descends the well', orb_corridor)


def orb_sweep():
    scene = world()
    trap = spy_on(area1, 'take_trapped_orb', impl=answer(False))
    ground = spy_on(area1, 'take_ground_orb', impl=answer(True))
    burn = spy_on(area1, 'burn_orbs', impl=answer(False))
    well = spy_on(area1, 'enter_well', impl=answer(True))
    expect(run_wait(area1.sweep_orbs(scene.log))).to_be(False)
    trap.mock_implementation(answer(True))
    expect(run_wait(area1.sweep_orbs(scene.log))).to_be(False)
    for i in range(28):
        scene.item(i, 'Filler')
    expect(run_wait(area1.sweep_orbs(scene.log))).to_be(False)
    burn.mock_implementation(answer(True))
    expect(run_wait(area1.sweep_orbs(scene.log))).to_be(True)
    expect(len(well.calls)).to_be(1)
    expect(len(ground.calls) > 0).to_be(True)


test('a full pack burns its orbs early and only a completed sweep tries the well', orb_sweep)


CROSSINGS = [
    [bridge.enter_cave, UP_LOC.CAVE_ENTRANCE, 'Enter', Tile(2400, 9700, 0)],
    [bridge.leave_pass, UP_LOC.CAVE_EXIT, 'Leave', UP_TILE.CAVE_MOUTH],
    [cavern.descend_to_dwarves, UP_LOC.TUNNEL_DOWN, 'Climb-down', Tile(2400, 9750, 0)],
    [cavern.ascend_from_dwarves, UP_LOC.TUNNEL_UP, 'Climb-up', Tile(2400, 9600, 1)],
    [area2.enter_main_cavern, UP_LOC.TEMPLE_DOOR_L, 'Open', Tile(2400, 9600, 1)],
]


def crossing(fn, id, op, destination):
    scene = world()
    scene.at = UP_TILE.CAVE_MOUTH
    scene.walk_ok = False
    expect(run_wait(fn(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(fn(scene.log))).to_be(False)
    scene.loc('Crossing', [op], id=id, effect=lambda op: False)
    expect(run_wait(fn(scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Crossing', [op], id=id, effect=lambda op: setattr(scene, 'at', destination))
    expect(run_wait(fn(scene.log))).to_be(True)


test_each(CROSSINGS)('pass crossing confirms its landing: %s', crossing)


def koftik_and_lathas():
    scene = world()
    for fn in [bridge.start_quest, bridge.report_to_lathas, bridge.meet_koftik, bridge.leave_with_koftik, bridge.get_damp_cloth]:
        scene.at = None
        scene.walk_ok = False
        expect(run_wait(fn(scene.log))).to_be(False)
        scene.walk_ok = True
        spy_on(bridge, 'talk_strict', impl=answer(True))
        if fn in [bridge.meet_koftik, bridge.leave_with_koftik, bridge.get_damp_cloth]:
            expect(run_wait(fn(scene.log))).to_be(False)
            for id in [UP_NPC.KOFTIK_SURFACE, UP_NPC.KOFTIK_LAST, UP_NPC.KOFTIK_BRIDGE]:
                scene.npc('Koftik', id=id)
            scene.talk_status = 'unreachable'
            expect(run_wait(fn(scene.log))).to_be(False)
            scene.talk_status = 'done'
        expect(run_wait(fn(scene.log))).to_be(True)
        scene.npcs = []


test('Koftik dialogue uses the guide id and Lathas is approached before reporting', koftik_and_lathas)


def robe_effect(scene, item):
    def equip(op):
        scene.take(item.id)
        scene.wear(item.name, id=item.id)
    return equip


def disciple_robes():
    scene = world()
    scene.walk_ok = False
    expect(run_wait(doll.robe_from_disciple(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(doll.robe_from_disciple(scene.log))).to_be(False)
    spy_on(reachability, 'can_reach', returns=True)
    scene.npc('Disciple', ['Attack'], id=UP_NPC.DISCIPLE, effect=lambda op: False)
    expect(run_wait(doll.robe_from_disciple(scene.log))).to_be(False)
    scene.npcs = []

    def defeated(op):
        scene.npcs = []
        for robe in [UP_ITEM.ZAM_TOP, UP_ITEM.ZAM_BOTTOM]:
            scene.on_ground(robe.id, robe.name)

    scene.npc('Disciple', ['Attack'], id=UP_NPC.DISCIPLE, effect=defeated)
    expect(run_wait(doll.robe_from_disciple(scene.log))).to_be(True)
    expect(run_wait(doll.robe_from_disciple(scene.log))).to_be(True)
    expect(run_wait(doll.wear_only_robes(scene.log))).to_be(False)
    scene.pack = []

    for robe in [UP_ITEM.ZAM_TOP, UP_ITEM.ZAM_BOTTOM]:
        scene.item(robe.id, robe.name, actions=['Wear'], effect=robe_effect(scene, robe))
    scene.wear('Helmet')
    expect(run_wait(doll.wear_only_robes(scene.log))).to_be(True)
    inside = spy_on(doll, 'inside_iban_temple', returns=False)
    scene.walk_ok = False
    expect(run_wait(doll.open_iban_door(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(doll.open_iban_door(scene.log))).to_be(False)
    scene.loc('Door', ['Open'], id=UP_LOC.IBAN_DOOR_L, effect=lambda op: False)
    expect(run_wait(doll.open_iban_door(scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Door', ['Open'], id=UP_LOC.IBAN_DOOR_L, effect=lambda op: inside.mock_return_value(True))
    expect(run_wait(doll.open_iban_door(scene.log))).to_be(True)


test('disciples drop both robes and the temple opens only after stripping to those two slots', disciple_robes)
