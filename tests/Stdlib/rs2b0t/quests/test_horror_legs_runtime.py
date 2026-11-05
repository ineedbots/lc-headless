"""Lighthouse repairs, the six wall slots, both dagannoths and the post-quest exit."""

from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.quests.defs.horror import dungeon, fight, lighthouse
from rs2004.quests.defs.horror.areas import HD_ID, HD_ITEM, HD_LOC, HD_TILE
from rs2004.reach import reach
from rs2004.tabs import prayer


def answer(value):
    def wait(*args, **kwargs):
        return value
        yield
    return wait


def give(scene, id):
    def effect(*args):
        scene.item(id, 'Quest item')
    return effect


def bridge():
    scene = Scene(HD_TILE.BRIDGE_WEST)
    scene.walk_ok = False
    expect(run_wait(lighthouse.repair_bridge(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(lighthouse.repair_bridge(scene.log))).to_be(False)
    for at in [HD_TILE.BRIDGE_WEST, HD_TILE.BRIDGE_EAST]:
        scene.loc(HD_LOC.BRIDGE, tile=at)
    expect(run_wait(lighthouse.repair_bridge(scene.log))).to_be(False)
    scene.item(HD_ID.PLANK, HD_ITEM.PLANK, count=2, on_use=lambda target: False)
    expect(run_wait(lighthouse.repair_bridge(scene.log))).to_be(False)
    scene.pack = []
    scene.item(HD_ID.PLANK, HD_ITEM.PLANK, count=2)
    expect(run_wait(lighthouse.repair_bridge(scene.log))).to_be(True)
    expect(scene.logged('took no plank')).to_be(True)
    scene.pack = []

    def used(target):
        scene.pack[0].count -= 1

    scene.item(HD_ID.PLANK, HD_ITEM.PLANK, count=2, on_use=used)
    scene.chat.pages = ['continue']
    expect(run_wait(lighthouse.repair_bridge(scene.log))).to_be(True)
    expect(scene.logged('bridge built')).to_be(True)


test('both bridge halves use their exact tile and confirm consumed planks', bridge)


def lighthouse_climbs():
    scene = Scene(HD_TILE.LIGHTHOUSE_DOOR)
    expect(run_wait(lighthouse.enter_lighthouse(scene.log))).to_be(False)
    scene.loc_op_effect = lambda *args: setattr(scene, 'at', HD_TILE.QUEST_STAIRS_BASE)
    expect(run_wait(lighthouse.enter_lighthouse(scene.log))).to_be(True)
    expect(run_wait(lighthouse.enter_lighthouse(scene.log))).to_be(True)
    scene.loc_op_status = 'unreachable'
    expect(run_wait(lighthouse.climb_to_light(scene.log))).to_be(False)
    scene.loc_op_status = 'done'

    def up(*args):
        scene.at = Tile(scene.at.x, scene.at.z, scene.at.level + 1)

    scene.loc_op_effect = up
    expect(run_wait(lighthouse.climb_to_light(scene.log))).to_be(True)
    scene.at = HD_TILE.REAL_STAIRS_L2
    scene.loc_op_status = 'unreachable'
    expect(run_wait(lighthouse.descend_to_basement(scene.log))).to_be(False)
    scene.loc_op_status = 'done'

    def down(name, op):
        if name == HD_LOC.LADDER:
            scene.at = HD_TILE.BASEMENT_DOWN
        elif scene.at.level == 2:
            scene.at = HD_TILE.QUEST_STAIRS_L1
        else:
            scene.at = HD_TILE.QUEST_STAIRS_BASE

    scene.loc_op_effect = down
    expect(run_wait(lighthouse.descend_to_basement(scene.log))).to_be(True)
    expect(run_wait(lighthouse.descend_to_basement(scene.log))).to_be(True)
    scene.at = None
    expect(lighthouse._level(-1)).to_be(-1)


test('lighthouse climbing crosses the broken and repaired copies then reaches the basement', lighthouse_climbs)


def light_repair():
    scene = Scene(HD_TILE.QUEST_LIGHT)
    scene.walk_ok = False
    expect(run_wait(lighthouse.repair_light(set(), scene.log))).to_be(False)
    scene.walk_ok = True
    scene.item(HD_ID.SWAMP_TAR, HD_ITEM.SWAMP_TAR)
    expect(run_wait(lighthouse.repair_light(set(), scene.log))).to_be(False)
    scene.loc(HD_LOC.LIGHT)
    expect(run_wait(lighthouse.repair_light(set(), scene.log))).to_be(False)
    scene.pack = []
    scene.item(HD_ID.SWAMP_TAR, HD_ITEM.SWAMP_TAR, on_use=lambda target: False)
    expect(run_wait(lighthouse.repair_light(set(), scene.log))).to_be(False)
    scene.pack = []
    scene.item(HD_ID.SWAMP_TAR, HD_ITEM.SWAMP_TAR, on_use=lambda target: scene.take(HD_ID.SWAMP_TAR))
    scene.item(HD_ID.MOLTEN_GLASS, HD_ITEM.MOLTEN_GLASS, on_use=lambda target: scene.take(HD_ID.MOLTEN_GLASS))
    scene.item(HD_ID.TINDERBOX, HD_ITEM.TINDERBOX,
               on_use=lambda target: setattr(scene, 'at', HD_TILE.REAL_STAIRS_L2))
    expect(run_wait(lighthouse.repair_light(set(), scene.log))).to_be(True)
    expect(lighthouse.in_quest_lighthouse(scene.at)).to_be(False)
    scene.at = HD_TILE.QUEST_LIGHT
    scene.pack = []
    expect(run_wait(lighthouse.repair_light(set(), scene.log))).to_be(False)


test('tar and glass are consumed before lighting teleports into the repaired lighthouse', light_repair)


def wall_slots():
    scene = Scene(HD_TILE.WALL_SOUTH)
    scene.walk_ok = False
    expect(run_wait(dungeon.load_wall(scene.log))).to_be_null()
    scene.walk_ok = True
    expect(run_wait(dungeon.load_wall(scene.log))).to_be_null()
    scene.loc(HD_LOC.WALL, ['Study'])
    expect(len(run_wait(dungeon.load_wall(scene.log)))).to_be(6)
    for slot in dungeon.SLOTS:
        scene.item(slot.id, slot.item)
    expect(run_wait(dungeon.load_wall(scene.log))).to_equal([])
    scene.pack = []
    for slot in dungeon.SLOTS:
        scene.item(slot.id, slot.item, on_use=lambda target: False)
    expect(run_wait(dungeon.load_wall(scene.log))).to_equal([])
    scene.pack = []
    for slot in dungeon.SLOTS:
        scene.item(slot.id, slot.item, on_use=lambda target: scene.say('You place a rune into the slot in the wall'))
    expect(run_wait(dungeon.load_wall(scene.log))).to_equal([])
    expect(scene.logged('placed the')).to_be(True)


test('all six wall slots are attempted and missing ingredients are reported to the door oracle', wall_slots)


def wall_and_ladder():
    scene = Scene(HD_TILE.LIGHTHOUSE_DOOR)
    expect(run_wait(dungeon.open_wall_and_descend(scene.log))).to_be(False)
    scene.at = HD_TILE.WALL_SOUTH
    loaded = spy_on(dungeon, 'load_wall', impl=answer(None))
    expect(run_wait(dungeon.open_wall_and_descend(scene.log))).to_be(False)
    loaded.mock_implementation(answer(['Air rune']))
    expect(run_wait(dungeon.open_wall_and_descend(scene.log))).to_be(False)
    scene.loc(HD_LOC.WALL, ['Open'], tile=Tile(2517, 4627, 1), effect=lambda op: False)
    expect(run_wait(dungeon.open_wall_and_descend(scene.log))).to_be(False)
    scene.locs = []
    scene.loc(HD_LOC.WALL, ['Open'], tile=Tile(2517, 4627, 1))
    expect(run_wait(dungeon.open_wall_and_descend(scene.log))).to_be(False)
    scene.locs = []
    scene.loc(HD_LOC.WALL, ['Open'], tile=Tile(2517, 4627, 1),
              effect=lambda op: scene.say('You cannot see any way to move it'))
    expect(run_wait(dungeon.open_wall_and_descend(scene.log))).to_be(False)
    loaded.mock_implementation(answer([]))
    expect(run_wait(dungeon.open_wall_and_descend(scene.log))).to_be(False)
    scene.at = HD_TILE.BASEMENT_DOWN
    scene.walk_ok = False
    expect(run_wait(dungeon.open_wall_and_descend(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(dungeon.open_wall_and_descend(scene.log))).to_be(False)
    scene.loc(HD_LOC.LADDER, ['Climb'], tile=HD_TILE.BASEMENT_DOWN, effect=lambda op: False)
    expect(run_wait(dungeon.open_wall_and_descend(scene.log))).to_be(False)
    scene.locs = []
    scene.loc(HD_LOC.LADDER, ['Climb'], tile=HD_TILE.BASEMENT_DOWN)
    expect(run_wait(dungeon.open_wall_and_descend(scene.log))).to_be(False)
    scene.locs = []
    scene.loc(HD_LOC.LADDER, ['Climb'], tile=HD_TILE.BASEMENT_DOWN,
              effect=lambda op: setattr(scene, 'at', Tile(HD_TILE.BASEMENT_DOWN.x, HD_TILE.BASEMENT_DOWN.z, 0)))
    expect(run_wait(dungeon.open_wall_and_descend(scene.log))).to_be(True)
    expect(run_wait(dungeon.open_wall_and_descend(scene.log))).to_be(True)


test('the strange wall reports empty slots and its far-side ladder must land in the cavern', wall_and_ladder)


def postquest_exit():
    scene = Scene()
    auto = spy_on(game, 'set_auto_retaliate', returns=None)
    expect(run_wait(dungeon.exit_after_quest(scene.log))).to_be(False)
    scene.at = HD_TILE.LIGHTHOUSE_DOOR
    expect(run_wait(dungeon.exit_after_quest(scene.log))).to_be(True)
    scene.at = HD_TILE.POSTQUEST_LADDER
    scene.walk_ok = False
    expect(run_wait(dungeon.exit_after_quest(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(dungeon.exit_after_quest(scene.log))).to_be(False)
    scene.loc(HD_LOC.LADDER, ['Climb'], tile=HD_TILE.POSTQUEST_LADDER,
              effect=lambda op: setattr(scene, 'at', HD_TILE.REAL_LIGHTHOUSE_L0))
    scene.loc(HD_LOC.DOORWAY, ['Walk-through'], tile=HD_TILE.REAL_LIGHTHOUSE_L0.translate(0, -1), effect=lambda op: setattr(scene, 'at', HD_TILE.LIGHTHOUSE_DOOR))
    expect(run_wait(dungeon.exit_after_quest(scene.log))).to_be(True)
    expect(auto.calls[-1]).to_equal((True,))

    def broken(log):
        raise ValueError('ladder failed')
        yield

    spy_on(dungeon, '_climb_out', impl=broken)
    scene.at = HD_TILE.POSTQUEST_LADDER
    try:
        run_wait(dungeon.exit_after_quest(scene.log))
        raise AssertionError('expected the climb exception')
    except ValueError:
        expect(auto.calls[-1]).to_equal((True,))


test('the post-quest ladder restores auto-retaliate after success, failure and exceptions', postquest_exit)


def fight_world():
    scene = Scene(HD_TILE.JOSSIK)
    spy_on(game, 'open_side_tab', impl=answer(True))
    spy_on(game, 'set_auto_retaliate', returns=None)
    spy_on(game, 'facing', returns=None)
    spy_on(prayer, 'points', returns=50)
    spy_on(prayer, 'active', returns=True)
    spy_on(prayer, 'set', impl=answer(True))
    return scene


def jossik():
    scene = fight_world()
    scene.walk_ok = False
    expect(run_wait(fight.poke_jossik(scene.log))).to_be(False)
    scene.walk_ok = True
    op = spy_on(reach, 'entity_op', impl=answer('unreachable'))
    expect(run_wait(fight.poke_jossik(scene.log))).to_be(False)
    op.mock_implementation(answer('done'))
    expect(run_wait(fight.poke_jossik(scene.log))).to_be(True)
    scene.stats['magic'] = 1
    expect(run_wait(fight.fight_junior(scene.log))).to_be(False)
    expect(run_wait(fight.fight_mother(scene.log))).to_be(False)
    scene.stats['magic'] = 60
    spy_on(fight, 'melee_ready', returns=True)
    spy_on(fight, 'melee_weapon_name', returns='Sword')

    def inspect(plan, log):
        expect(plan.protect).to_be('melee' if plan.handover else 'missiles')
        if plan.handover:
            expect(plan.element(None)).to_be('Wind blast')
            expect(plan.melee(None)).to_be(True)
        else:
            for id, element in fight.FORM_ELEMENT.items():
                expect(plan.element(Fake(id=id))).to_be(element + ' blast')
            expect(plan.element(Fake(id=fight.RANGED_FORM))).to_be_null()
            expect(plan.element(Fake(id=999))).to_be_null()
            expect(plan.melee(Fake(id=fight.MELEE_FORM))).to_be(True)
        return True
        yield

    spy_on(fight, 'fight_loop', impl=inspect)
    expect(run_wait(fight.fight_junior(scene.log))).to_be(True)
    expect(run_wait(fight.fight_mother(scene.log))).to_be(True)


test('Jossik summons the fights and each mother form selects the correct elemental spell', jossik)


def combat_rounds():
    scene = fight_world()
    scene.won = False
    scene.target = None
    plan = Fake(what='test dagannoth', protect='melee', guard=10, target=lambda: scene.target,
                won=lambda: scene.won, melee=None, element=lambda target: 'Wind blast', summon_delay=6)
    poke = spy_on(fight, 'poke_jossik', impl=answer(False))
    expect(run_wait(fight.fight_loop(plan, scene.log))).to_be(False)
    poke.mock_implementation(answer(True))
    expect(run_wait(fight.fight_loop(plan, scene.log))).to_be(False)
    scene.target = scene.npc('Dagannoth', ['Attack'], id=1347)
    cast = spy_on(game, 'cast_on_npc', returns=False)
    expect(run_wait(fight.fight_loop(plan, scene.log))).to_be(False)
    expect(scene.logged('could not select')).to_be(True)
    cast.mock_return_value(True)
    expect(run_wait(fight.fight_loop(plan, scene.log))).to_be(False)
    plan.melee = lambda target: True
    expect(run_wait(fight.fight_loop(plan, scene.log))).to_be(False)
    scene.target = scene.npc('Dagannoth', ['Attack'], effect=lambda op: False)
    expect(run_wait(fight.fight_loop(plan, scene.log))).to_be(False)
    expect(scene.logged('could not attack')).to_be(True)
    scene.won = True
    plan.handover = 'missiles'
    expect(run_wait(fight.fight_loop(plan, scene.log))).to_be(True)
    plan.handover = None
    scene.stats['prayer'] = 1
    expect(run_wait(fight.fight_loop(plan, scene.log))).to_be(True)
    expect(scene.logged('prayer below')).to_be(True)
    scene.stats['prayer'] = 99
    active = spy_on(prayer, 'active', returns=False)
    protection = fight.Protection('melee')
    run_wait(protection.hold())
    expect(protection.arms).to_be(1)
    expect(protection.active()).to_be('none')


test('dagannoth combat handles absent targets, refused spells, melee forms and prayer handover', combat_rounds)


def lighthouse_escape_recovery():
    scene = Scene(Tile(2509, 3640, 2))
    spy_on(dungeon, 'settle_scene', impl=instant_ticks)
    for level in [2, 1]:
        current_level = level
        scene.loc(HD_LOC.STAIRS, actions=['Climb-down'], tile=Tile(2509, 3640, level), effect=lambda op: setattr(scene, 'at', Tile(2509, 3640, scene.at.level - 1)))
    doorway = HD_TILE.REAL_LIGHTHOUSE_L0.translate(0, -1)
    scene.loc(HD_LOC.DOORWAY, actions=['Walk-through'], tile=doorway, effect=lambda op: setattr(scene, 'at', HD_TILE.LIGHTHOUSE_DOOR))
    expect(run_wait(dungeon.exit_after_quest(scene.log))).to_be(True)
    expect(scene.at).to_be(HD_TILE.CAUSEWAY_SOUTH)
    expect(dungeon.in_lighthouse(Tile(2509, 3636, 0))).to_be(True)
    expect(dungeon.in_lighthouse(Tile(2508, 3636, 0))).to_be(False)
    scene.at = None
    expect(run_wait(dungeon.leave_lighthouse(scene.log))).to_be(False)
    scene.at = Tile(2509, 3640, 2)
    scene.locs.clear()
    expect(run_wait(dungeon.leave_lighthouse(scene.log))).to_be(False)
    scene.at = Tile(2509, 3640, 0)
    scene.walk_ok = False
    expect(run_wait(dungeon.leave_lighthouse(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(dungeon.leave_lighthouse(scene.log))).to_be(False)


test('a restart upstairs in the lighthouse descends, leaves the doorway and reaches the causeway', lighthouse_escape_recovery)
