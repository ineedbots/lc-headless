"""Regicide resumes the physical pass crossing from the current pocket."""

from rs2004.geometry import Tile
from rs2004.quests.defs.regicide import pass_ as travel, pockets
from rs2004.quests.defs.regicide.areas import RG_LOC, RG_TILE
from rs2004.quests.defs.upass.areas import UP_ITEM, UP_LOC, UP_TILE


def answer(value):
    def wait(*args, **kwargs):
        return value
        yield
    return wait


def move(scene, at):
    def effect(*args):
        scene.at = at
        return True
    return effect


def world():
    scene = Scene(Tile(2400, 9600, 0))
    stub(travel, bridge_gear=[])
    spy_on(travel, 'travel_to', impl=scene._walk)
    return scene


def wells_and_doors():
    scene = world()
    scene.walk_ok = False
    for fn in [travel.climb_well, travel.open_voyage_door, travel.climb_unicorn_tunnel,
               travel.climb_voyage_well, travel.leave_voyage_temple]:
        expect(run_wait(fn(scene.log))).to_be(False)
    scene.walk_ok = True
    for fn in [travel.climb_well, travel.open_voyage_door, travel.climb_unicorn_tunnel,
               travel.climb_voyage_well, travel.leave_voyage_temple]:
        expect(run_wait(fn(scene.log))).to_be(False)
    cases = [
        [travel.climb_well, UP_LOC.WELL, UP_TILE.WELL, 'Climb-down', Tile(2393, 9655, 0), 'upass_area', 'area2'],
        [travel.open_voyage_door, UP_LOC.IBAN_DOOR_R, RG_TILE.IBAN_DOOR, 'Open', Tile(2000, 9600, 0), 'upass_area', 'voyage'],
        [travel.climb_unicorn_tunnel, UP_LOC.UNICORN_DOOR_L, travel.UNICORN_TUNNEL_DOORS[0], 'Open', Tile(2370, 9666, 0), 'upass_area', 'area1'],
        [travel.climb_voyage_well, RG_LOC.WELL_OF_VOYAGE, RG_TILE.WELL_OF_VOYAGE, 'Climb-down', RG_TILE.VOYAGE_EXIT, 'regicide_area', 'voyage'],
        [travel.leave_voyage_temple, RG_LOC.TEMPLE_EXIT, RG_TILE.VOYAGE_EXIT, 'Exit', Tile(2200, 3200, 0), 'regicide_area', 'tirannwn'],
    ]
    for fn, id, at, op, landing, classifier, area in cases:
        scene.locs = []
        scene.loc('Crossing', [op], id=id, tile=at, effect=lambda op: False)
        expect(run_wait(fn(scene.log))).to_be(False)
        scene.locs = []
        scene.loc('Crossing', [op], id=id, tile=at, effect=move(scene, landing))
        spy_on(travel, classifier, returns=area)
        expect(run_wait(fn(scene.log))).to_be(True)
        expect(scene.at).to_equal(landing)
    scene.locs = []
    scene.walk_ok = False
    scene.loc('Door', ['Open'])
    expect(run_wait(travel.climb_voyage_well(scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Door', ['Open'], effect=lambda op: setattr(scene, 'walk_ok', True))
    scene.loc('Well', ['Climb-down'], id=RG_LOC.WELL_OF_VOYAGE, tile=RG_TILE.WELL_OF_VOYAGE)
    spy_on(travel, 'regicide_area', returns='voyage')
    expect(run_wait(travel.climb_voyage_well(scene.log))).to_be(True)


test('pass wells and doors require an op and verify their landing, including a closed inner door', wells_and_doors)


def bridge():
    scene = world()
    cloth = spy_on(travel, 'get_damp_cloth', impl=answer(False))
    fire = spy_on(travel, 'make_fire_arrow', impl=answer(False))
    expect(run_wait(travel.cross_bridge(scene.log))).to_be(False)
    cloth.mock_implementation(answer(True))
    expect(run_wait(travel.cross_bridge(scene.log))).to_be(False)
    scene.item(UP_ITEM.DAMP_CLOTH.id, UP_ITEM.DAMP_CLOTH.name)
    fire.mock_implementation(answer(True))
    arm = spy_on(travel, 'arm_fire_arrow', impl=answer(False))
    spy_on(travel, 'shoot_guiderope', impl=answer(True))
    expect(run_wait(travel.cross_bridge(scene.log))).to_be(False)
    arm.mock_implementation(answer(True))
    expect(run_wait(travel.cross_bridge(scene.log))).to_be(True)
    stub(travel, bridge_gear=['Sword'])
    scene.item(123, 'Sword')
    from rs2004.items import equipment
    equip = spy_on(equipment, 'equip', impl=answer(False))
    expect(run_wait(travel.restore_bridge_gear(scene.log))).to_be(False)
    expect(travel.bridge_gear).to_equal(['Sword'])
    scene.take(123)
    expect(run_wait(travel.restore_bridge_gear(scene.log))).to_be(True)
    expect(scene.logged('could not restore')).to_be(True)
    restore = spy_on(travel, 'restore_bridge_gear', impl=answer(False))
    expect(run_wait(travel.cross_bridge(scene.log))).to_be(False)

    def broken(*args):
        raise RuntimeError('interrupted shot')
        yield

    arm.mock_implementation(broken)
    try:
        run_wait(travel.cross_bridge(scene.log))
        expect(False).to_be(True)
    except RuntimeError as error:
        expect(str(error)).to_be('interrupted shot')
    expect(len(restore.calls) >= 2).to_be(True)


test('bridge restores displaced gear after successful, refused and interrupted shots', bridge)


def routing():
    scene = world()
    reg_area = spy_on(travel, 'regicide_area', returns=None)
    up_area = spy_on(travel, 'upass_area', returns=None)
    names = ['restore_bridge_gear', 'climb_out_of_pit', 'leave_voyage_temple', 'cross_to_west',
             'enter_cave', 'cross_bridge', 'cross_grid', 'enter_main_cavern', 'climb_well',
             'climb_unicorn_tunnel', 'take_next_crossing', 'travel_to', 'climb_voyage_well', 'open_voyage_door']
    calls = {}
    for name in names:
        calls[name] = spy_on(travel, name, impl=answer(True))
    stub(travel, bridge_gear=['Shield'])
    expect(run_wait(travel.enter_tirannwn(scene.log))).to_be(True)
    expect(len(calls['restore_bridge_gear'].calls)).to_be(1)
    stub(travel, bridge_gear=[])
    for area in ['tirannwn', 'pit', 'voyage']:
        reg_area.mock_return_value(area)
        expect(run_wait(travel.enter_tirannwn(scene.log))).to_be(True)
    reg_area.mock_return_value(None)
    crossing = spy_on(travel, 'outstanding_crossing', returns=None)
    for area in ['mainland', 'westardougne', 'area2', 'gridpit', 'voyage', 'main', 'witch', 'temple', 'dwarves', 'kalrag']:
        up_area.mock_return_value(area)
        expect(run_wait(travel.enter_tirannwn(scene.log))).to_be(True)
    crossing.mock_return_value(Fake())
    up_area.mock_return_value('area2')
    expect(run_wait(travel.enter_tirannwn(scene.log))).to_be(True)
    up_area.mock_return_value('area1')
    grid = spy_on(travel, 'past_grid_tile', returns=False)
    for at in [Tile(2450, 9715, 0), Tile(2400, 9600, 0)]:
        scene.at = at
        expect(run_wait(travel.enter_tirannwn(scene.log))).to_be(True)
    grid.mock_return_value(True)
    for at in [Tile(2370, 9666, 0), Tile(2400, 9600, 0)]:
        scene.at = at
        expect(run_wait(travel.enter_tirannwn(scene.log))).to_be(True)
    up_area.mock_return_value(None)
    expect(run_wait(travel.enter_tirannwn(scene.log))).to_be(False)
    for name in names:
        expect(len(calls[name].calls) > 0).to_be(True)
    spy_on(travel, 'travel_tirannwn', impl=answer(True))
    expect(run_wait(travel.leave_tirannwn(RG_TILE.ARDOUGNE_BANK, 13, scene.log))).to_be(True)


test('Regicide resumes every mainland, cavern, grid and voyage leg from current position', routing)


def forest_retries():
    scene = world()
    leg = pockets.plan_route(pockets.REGICIDE_SEAMS[0].sides[0].pocket,
                             pockets.REGICIDE_SEAMS[0].sides[1].pocket, 13)[0]
    stub(pockets, CROSS_TRIES=2, STAND_TRIES=2, MAX_LEGS=2, CROSS_FAILS=2)
    where = spy_on(pockets, 'standing_in', returns=leg.from_.pocket)
    walk = spy_on(pockets, 'walk_with', impl=answer(False))
    expect(run_wait(pockets.cross_seam(leg, scene.log, {}))).to_be(False)
    walk.mock_implementation(answer(True))
    expect(run_wait(pockets.cross_seam(leg, scene.log, {}))).to_be(False)
    scene.at = Tile(leg.seam.x, leg.seam.z, 0)
    scene.loc('Seam', [leg.seam.op], id=leg.seam.loc_id, effect=lambda op: False)
    expect(run_wait(pockets.cross_seam(leg, scene.log, {}))).to_be(False)
    scene.locs = []
    scene.loc('Seam', [leg.seam.op], id=leg.seam.loc_id)
    expect(run_wait(pockets.cross_seam(leg, scene.log, {}))).to_be(False)
    scene.locs = []
    scene.loc('Seam', [leg.seam.op], id=leg.seam.loc_id,
              effect=lambda op: where.mock_return_value(leg.to.pocket))
    expect(run_wait(pockets.cross_seam(leg, scene.log, {}))).to_be(True)
    expect(run_wait(pockets.cross_seam(leg, scene.log, {}))).to_be(True)
    where.mock_return_value(leg.from_.pocket)
    scene.at = Tile(2400, 9500, 0)
    spy_on(pockets, 'climb_out_of_pit', impl=answer(False))
    expect(run_wait(pockets.cross_seam(leg, scene.log, {}))).to_be(False)
    expect(run_wait(pockets.travel_tirannwn(RG_TILE.ARDOUGNE_BANK, 1, 13, scene.log))).to_be(False)
    scene.at = Tile(2400, 3200, 0)
    spy_on(pockets, 'pocket_at', impl=lambda tile: 'source' if tile == scene.at else 'target')
    route = spy_on(pockets, 'plan_route', returns=[leg])
    cross = spy_on(pockets, 'cross_seam', impl=answer(False))
    expect(run_wait(pockets.travel_tirannwn(RG_TILE.ARDOUGNE_BANK, 1, 13, scene.log))).to_be(False)
    expect(scene.logged('replanning')).to_be(True)
    cross.mock_implementation(answer(True))
    expect(run_wait(pockets.travel_tirannwn(RG_TILE.ARDOUGNE_BANK, 1, 13, scene.log))).to_be(False)
    expect(scene.logged('without reaching')).to_be(True)
    route.mock_return_value([])
    expect(run_wait(pockets.travel_tirannwn(RG_TILE.ARDOUGNE_BANK, 1, 13, scene.log))).to_be(True)


test('forest crossings bound approach failures, distinguish movement from arrival and replan refused traps', forest_retries)
