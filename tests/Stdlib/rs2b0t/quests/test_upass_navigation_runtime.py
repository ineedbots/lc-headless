"""Pass navigation proves pocket crossings rather than mistaking an approach for progress."""

from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.navigation import navigator, reachability
from rs2004.quests.defs.upass import cross, grid, pass_ as travel, railings, stall
from rs2004.quests.defs.upass.areas import UP_ITEM, UP_LOC, UP_TILE


def answer(value):
    def wait(*args, **kwargs):
        return value
        yield
    return wait


def world():
    scene = Scene(Tile(2400, 9600, 0))
    scene.reachable = True
    scene.path = True
    spy_on(reachability, 'can_reach', impl=lambda *args, **kwargs: scene.reachable)
    spy_on(reachability, 'probeable', returns=True)
    spy_on(reachability, 'walkable', returns=True)
    spy_on(navigator, 'find_path', impl=lambda *args, **kwargs: Fake(ok=scene.path))
    stub(travel, spent_by_dest={})
    return scene


def standing():
    scene = world()
    at = Tile(2410, 9600, 0)
    dest = Tile(2420, 9600, 0)
    scene.at = at
    expect(run_wait(travel.stand_beside(at, dest, scene.log))).to_be('stood')
    expect(run_wait(travel.stand_beside(at, dest, scene.log, named=[at]))).to_be('stood')
    scene.at = Tile(2407, 9600, 0)
    expect(run_wait(travel.stand_beside(at, dest, scene.log))).to_be('stood')
    scene.at = Tile(2400, 9600, 0)
    scene.reachable = False
    expect(run_wait(travel.stand_beside(at, dest, scene.log))).to_be('no')
    expect(run_wait(travel.stand_beside(at, dest, scene.log, named=[at]))).to_be('no')
    scene.at = Tile(2405, 9600, 0)
    expect(run_wait(travel.stand_beside(at, dest, scene.log))).to_be('from-range')
    scene.at = Tile(2400, 9600, 0)
    scene.reachable = True
    scene.walk_ok = False
    expect(run_wait(travel.stand_beside(at, dest, scene.log))).to_be('no')
    scene.walk_ok = True
    expect(run_wait(travel.stand_beside(at, dest, scene.log))).to_be('stood')
    expect(scene.logged('stood@')).to_be(True)


test('seam approaches distinguish named stands, reachable sides and safe server-path range', standing)


def seam_inventory():
    scene = world()
    dest = Tile(2420, 9600, 0)
    rock = scene.loc('Rockslide', ['Climb-over'], id=UP_LOC.ROCKSLIDE, tile=Tile(2410, 9600, 0))
    scene.loc('Ledge', ['Cross'], id=UP_LOC.LEDGE, tile=Tile(2411, 9600, 0))
    scene.loc('Mud', id=UP_LOC.MUD_DIG, tile=Tile(2412, 9600, 0))
    expect(travel.seam_reachable(rock.tile())).to_be(True)
    expect(travel.seam_open(rock)).to_be(True)
    expect(len(travel.seams_in_scene())).to_be(3)
    options = travel.hops_toward(dest, scene.at)
    expect(len(options.leading)).to_be(2)
    scene.reachable = False
    options = travel.hops_toward(dest, scene.at)
    expect(len(options.trailing)).to_be(2)
    travel.report_stuck(dest, scene.at, scene.log)
    expect(scene.logged('walled')).to_be(True)
    expect(travel.shortlist('lead', [], dest, 20, lambda loc: 'fresh')).to_be('lead none')
    expect(travel.shortlist('lead', [rock] * 7, dest, 20, lambda loc: 'elsewhere')).to_contain('+1')
    expect(travel.kind_of(Fake(id=999))).to_be_null()
    expect(travel.seam_key(rock)).to_contain(str(UP_LOC.ROCKSLIDE))
    expect(travel.pack_route(scene.at, dest)).to_be(True)
    expect(travel.pack_route_beside(scene.at, dest)).to_be(True)
    expect(travel.cage_worth_taking(dest, scene.at, travel.MUD_CAGE)).to_be(True)
    expect(travel.in_cage_corridor()).to_be(False)
    expect(len(travel.tunnel_landing(scene.at))).to_be(3)


test('seam discovery ranks reachable progress first and reports why other seams are blocked', seam_inventory)


def obstacle_attempts():
    scene = world()
    start = scene.at
    dest = Tile(2420, 9600, 0)
    rock = scene.loc('Rockslide', ['Climb-over'], id=UP_LOC.ROCKSLIDE, tile=Tile(2401, 9600, 0), effect=lambda op: False)
    expect(run_wait(travel.try_hops([rock], dest, start, scene.log, {}))).to_be(False)
    spent = {travel.seam_key(rock): [start]}
    expect(run_wait(travel.try_hops([rock], dest, start, scene.log, spent))).to_be(False)
    expect(run_wait(travel.try_hops([Fake(id=999, tile=lambda: start)], dest, start, scene.log, {}))).to_be(False)
    stood = spy_on(travel, 'stand_beside', impl=answer('no'))
    expect(run_wait(travel.try_hops([rock], dest, start, scene.log, {}))).to_be(False)
    stood.mock_implementation(answer('stood'))
    scene.locs = []
    rock = scene.loc('Rockslide', ['Climb-over'], id=UP_LOC.ROCKSLIDE, tile=start)
    expect(run_wait(travel.try_hops([rock], dest, start, scene.log, {}))).to_be(False)
    scene.locs = []
    rock = scene.loc('Rockslide', ['Climb-over'], id=UP_LOC.ROCKSLIDE, tile=start,
                     effect=lambda op: scene.say('You fail to cross'))
    spy_on(travel, 'verdict_since', returns='failed')
    expect(run_wait(travel.try_hops([rock], dest, start, scene.log, {}))).to_be(False)
    verdict = spy_on(travel, 'verdict_since', returns='refused')
    expect(run_wait(travel.try_hops([rock], dest, start, scene.log, {}))).to_be(False)
    stood.mock_implementation(answer('from-range'))
    expect(run_wait(travel.try_hops([rock], dest, start, scene.log, {}))).to_be(False)
    stood.mock_implementation(answer('stood'))
    verdict.mock_return_value('crossing')
    scene.reachable = False
    scene.locs = []
    rock = scene.loc('Rockslide', ['Climb-over'], id=UP_LOC.ROCKSLIDE, tile=start,
                     effect=lambda op: setattr(scene, 'at', Tile(2405, 9600, 0)))
    spent = {}
    expect(run_wait(travel.try_hops([rock], dest, start, scene.log, spent))).to_be(True)
    expect(travel.seam_key(rock) in spent).to_be(True)
    expect(scene.logged('behind us now')).to_be(True)


test('a hop requires a script crossing, enough movement and the near-side stand becoming unreachable', obstacle_attempts)


def item_seams():
    scene = world()
    seam = travel.USE_SEAMS[0]
    dest = seam.landing
    scene.at = None
    expect(run_wait(travel.use_seam_toward(dest, scene.log))).to_be(False)
    scene.at = Tile(dest.x - 10, dest.z, 0)
    expect(run_wait(travel.use_seam_toward(dest, scene.log))).to_be(False)
    scene.item(seam.item.id, seam.item.name)
    expect(run_wait(travel.use_seam_toward(dest, scene.log))).to_be(False)
    scene.loc('Swing', id=seam.locs[0])
    scene.reachable = False
    expect(run_wait(travel.use_seam_toward(dest, scene.log))).to_be(False)
    scene.reachable = True
    scene.walk_ok = False
    expect(run_wait(travel.use_seam_toward(dest, scene.log))).to_be(False)
    scene.walk_ok = True
    scene.take(seam.item.id)
    scene.item(seam.item.id, seam.item.name, on_use=lambda target: False)
    expect(run_wait(travel.use_seam_toward(dest, scene.log))).to_be(False)
    scene.take(seam.item.id)
    scene.item(seam.item.id, seam.item.name)
    expect(run_wait(travel.use_seam_toward(dest, scene.log))).to_be(False)
    scene.take(seam.item.id)

    def cross(target):
        scene.take(seam.item.id)
        scene.at = dest

    scene.item(seam.item.id, seam.item.name, on_use=cross)
    expect(run_wait(travel.use_seam_toward(dest, scene.log))).to_be(True)
    expect(scene.has(seam.item.id)).to_be(False)


test('rope seams require a useful landing and confirm the consumed rope and forced movement', item_seams)


def baked_routes():
    scene = world()
    from_ = scene.at
    dest = Tile(2420, 9600, 1)
    scene.path = False
    expect(travel.platform_pocket(from_)).to_be_null()
    expect(travel.pocket_of_target(dest)).to_be_null()
    expect(travel.platform_step(from_, dest, scene.log)).to_be_null()
    links = travel.links_for(1)
    first = links[0]
    here = spy_on(travel, 'platform_pocket', returns=first.a.pocket)
    goal = spy_on(travel, 'pocket_of_target', returns=first.b.pocket)
    expect(travel.platform_step(from_, dest, scene.log)).to_equal(first.a.tile)
    goal.mock_return_value('not-connected')
    expect(travel.platform_step(from_, dest, scene.log)).to_be_null()
    goal.mock_return_value(first.a.pocket)
    expect(travel.platform_step(from_, dest, scene.log)).to_be_null()
    step = spy_on(travel, 'platform_step', returns=first.a.tile)
    expect(run_wait(travel.cross_by_route(from_, dest, scene.log))).to_be(False)
    scene.path = True
    scene.walk_ok = False
    expect(run_wait(travel.cross_by_route(from_, dest, scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(travel.cross_by_route(from_, dest, scene.log))).to_be(False)
    scene.loc('Bridge', ['Cross'], id=UP_LOC.COLLAPSED_A, effect=lambda op: False)
    expect(run_wait(travel.cross_by_route(from_, dest, scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Bridge', ['Cross'], id=UP_LOC.COLLAPSED_A)
    expect(run_wait(travel.cross_by_route(from_, dest, scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Bridge', ['Cross'], id=UP_LOC.COLLAPSED_A,
              effect=lambda op: setattr(scene, 'at', Tile(scene.at.x + 5, scene.at.z, 1)))
    expect(run_wait(travel.cross_by_route(from_, dest, scene.log))).to_be(True)


test('baked platform routes use a shortest bridge chain and require the routed crossing to move', baked_routes)


def sweep_and_travel():
    scene = world()
    dest = Tile(2420, 9600, 0)
    expect(len(travel.sweep_probes(scene.at))).to_be(8)
    scene.reachable = False
    expect(travel.sweep_probes(scene.at)).to_equal([])
    expect(run_wait(travel.sweep_pocket(dest, scene.log, {}))).to_be(False)
    scene.at = None
    expect(run_wait(travel.hop_toward(dest, scene.log, {}))).to_be(False)
    expect(run_wait(travel.sweep_pocket(dest, scene.log, {}))).to_be(False)
    scene.at = Tile(2400, 9600, 0)
    hop = spy_on(travel, 'hop_toward', impl=answer(False))
    scene.reachable = True
    expect(run_wait(travel.sweep_pocket(dest, scene.log, {}))).to_be(False)
    hop.mock_implementation(answer(True))
    expect(run_wait(travel.sweep_pocket(dest, scene.log, {}))).to_be(True)
    expect(run_wait(travel.travel_to(dest, 1, scene.log))).to_be(True)
    expect(run_wait(travel.travel_to(dest, 1, scene.log))).to_be(True)
    scene.at = Tile(2400, 9600, 0)
    scene.walk_ok = False
    scene.path = False
    spy_on(travel, 'cross_once', impl=answer('nowhere'))
    spy_on(travel, 'cross_by_route', impl=answer(False))
    hop.mock_implementation(answer(False))
    sweep = spy_on(travel, 'sweep_pocket', impl=answer(False))
    expect(run_wait(travel.travel_to(dest, 1, scene.log))).to_be(False)
    expect(scene.logged('STUCK on hop')).to_be(True)
    hop.mock_implementation(answer(True))
    expect(run_wait(travel.travel_to(dest, 1, scene.log))).to_be(False)
    expect(scene.logged('24 crossings')).to_be(True)


test('pocket sweeps probe all directions and travel stops with diagnostics when no crossing progresses', sweep_and_travel)


def table_crossings():
    scene = world()
    edge = cross.UPASS_CROSSINGS[0]
    expect(cross.operate(edge, scene.log)).to_be(False)
    scene.loc('Obstacle', [edge.op], id=edge.loc, tile=edge.stand)
    expect(cross.operate(edge, scene.log)).to_be(True)
    used = Fake(loc=2275, op='Swing-on', stand=scene.at)
    scene.loc('Swing', id=2275)
    expect(cross.operate(used, scene.log)).to_be(False)
    scene.item(954, 'Rope')
    expect(cross.operate(used, scene.log)).to_be(True)
    scene.at = None
    expect(run_wait(cross.cross_once(edge.lands, scene.log))).to_be('nowhere')
    scene.at = Tile(2400, 9600, 1)
    expect(run_wait(cross.cross_once(edge.lands, scene.log))).to_be('nowhere')
    scene.at = edge.stand
    area = spy_on(cross, 'area_at', returns=None)
    scene.walk_ok = False
    expect(run_wait(cross.cross_once(edge.lands, scene.log))).to_be('nowhere')
    scene.walk_ok = True
    expect(run_wait(cross.cross_once(edge.lands, scene.log))).to_be('crossed')
    scene.at = edge.stand

    def area_of(tile):
        return edge.to if tile == edge.lands else edge.from_

    area.mock_implementation(area_of)
    scene.walk_ok = False
    expect(run_wait(cross.cross_once(edge.lands, scene.log))).to_be('same')
    scene.walk_ok = True
    op = spy_on(cross, 'operate', returns=False)
    expect(run_wait(cross.cross_once(edge.lands, scene.log))).to_be('same')
    op.mock_return_value(True)
    verdict = spy_on(cross, 'verdict_since', returns='failed')
    expect(run_wait(cross.cross_once(edge.lands, scene.log))).to_be('same')
    verdict.mock_return_value(None)
    expect(run_wait(cross.cross_once(edge.lands, scene.log))).to_be('same')

    def landed(edge, log):
        scene.at = edge.lands
        return True

    op.mock_implementation(landed)
    expect(run_wait(cross.cross_once(edge.lands, scene.log))).to_be('crossed')


test('the crossing table handles item uses, blocked animation tiles and failed rolls', table_crossings)


def fresh_and_backtracking():
    scene = world()
    dest = Tile(2420, 9600, 0)
    rock = scene.loc('Rockslide', ['Climb-over'], id=UP_LOC.ROCKSLIDE, tile=Tile(2410, 9600, 0))
    ledge = scene.loc('Ledge', ['Cross'], id=UP_LOC.LEDGE, tile=Tile(2409, 9600, 0))
    from rs2004.catalogs.record import Record
    spy_on(travel, 'hops_toward', returns=Record({'leading': [rock], 'trailing': [ledge], 'filtered': 1}))
    state = spy_on(travel, 'spent_state_here', returns='fresh')
    hops = spy_on(travel, 'try_hops', impl=answer(False))
    use = spy_on(travel, 'use_seam_toward', impl=answer(False))
    expect(run_wait(travel.hop_toward(dest, scene.log, {}))).to_be(False)
    hops.mock_implementation(answer(True))
    expect(run_wait(travel.hop_toward(dest, scene.log, {}))).to_be(True)
    hops.mock_implementation(answer(False))
    use.mock_implementation(answer(True))
    expect(run_wait(travel.hop_toward(dest, scene.log, {}))).to_be(True)
    use.mock_implementation(answer(False))
    state.mock_return_value('elsewhere')
    expect(run_wait(travel.hop_toward(dest, scene.log, {}))).to_be(False)
    expect(scene.logged('backing out')).to_be(True)
    spy_on(travel, 'hop_toward', impl=answer(True))
    scene.path = False
    expect(run_wait(travel.sweep_pocket(dest, scene.log, {}))).to_be(True)
    scene.at = Tile(2400, 9600, 0)
    scene.walk_ok = False
    expect(run_wait(travel.sweep_pocket(dest, scene.log, {}))).to_be(False)
    expect(scene.logged('not walked at')).to_be(True)


test('pass search tries fresh seams and item crossings before backing out over an earlier seam', fresh_and_backtracking)
