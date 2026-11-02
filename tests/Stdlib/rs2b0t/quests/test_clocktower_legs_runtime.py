"""Clock Tower's cog rooms, cage crossings and spindle placement against Scene facades."""

import rs2004.quests.defs.clocktower as cog
from rs2004.game import direct_navigator


def move(scene, tile):
    def effect(*args):
        scene.at = tile
        return True
    return effect


def world(at=None):
    scene = Scene(at if at is not None else cog.CELLAR_FOOT)
    scene.step_ok = True

    def step(dest, radius, timeout_ms):
        if scene.step_ok:
            scene.at = dest
        return scene.step_ok
        yield

    spy_on(direct_navigator, 'walk_to', impl=step)
    return scene


def pocket_exits():
    scene = world()
    scene.at = None
    expect(run_wait(cog.leave_pocket(scene.log))).to_be(False)
    scene.at = cog.CELLAR_FOOT
    expect(run_wait(cog.leave_pocket(scene.log))).to_be(True)
    expect(scene.walks).to_equal([])
    for colour, stand in [('white', cog.WHITE_ROOM_LADDER), ('blue', cog.BLUE_ROOM_LADDER)]:
        scene = world(stand)
        expect(run_wait(cog.leave_pocket(scene.log, colour))).to_be(True)
        expect(scene.walks).to_equal([])
        scene.no_walk = [stand]
        expect(run_wait(cog.leave_pocket(scene.log))).to_be(False)
        scene.no_walk = []
        expect(run_wait(cog.leave_pocket(scene.log))).to_be(False)
        expect(scene.logged('no ladder out')).to_be(True)
        ladder = scene.loc('Ladder', ['Climb-up'], effect=lambda op: False)
        expect(run_wait(cog.leave_pocket(scene.log))).to_be(False)
        ladder._fields['interact'] = lambda op: True
        before = scene.clock
        expect(run_wait(cog.leave_pocket(scene.log))).to_be(False)
        expect(scene.clock - before).to_be(10000)
        ladder._fields['interact'] = move(scene, cog.CELLAR_TOP)
        expect(run_wait(cog.leave_pocket(scene.log))).to_be(True)
        expect(scene.at).to_equal(cog.CELLAR_TOP)


test('Clock Tower leaves each cog pocket only after its ladder reaches the surface', pocket_exits)


def loose_cogs():
    for colour in cog.COLOURS:
        scene = world(cog.COG_SPAWN[colour])
        id = getattr(cog.COG_OBJ, colour)
        expect(run_wait(cog.take_cog(colour, scene.log))).to_be(False)
        expect(scene.logged('no ' + colour + ' cog')).to_be(True)
        floor = scene.on_ground(id, colour + ' cog', effect=lambda op: False)
        expect(run_wait(cog.take_cog(colour, scene.log))).to_be(False)
        floor._fields['interact'] = lambda op: True
        before = scene.clock
        expect(run_wait(cog.take_cog(colour, scene.log))).to_be(False)
        expect(scene.clock - before >= 8000).to_be(True)
        scene.ground = []
        scene.on_ground(id, colour + ' cog')
        expect(run_wait(cog.take_cog(colour, scene.log))).to_be(True)
        expect(scene.has(id)).to_be(True)
        expect(scene.ground).to_equal([])
        expect(run_wait(cog.take_cog(colour, scene.log))).to_be(True)


test('Clock Tower takes each colour by id and waits for inventory confirmation', loose_cogs)


def black_cooling():
    scene = world(cog.COG_SPAWN['black'])
    expect(run_wait(cog.take_black_cog(scene.log))).to_be(False)
    scene.on_ground(cog.COG_OBJ.black, 'Black cog', effect=lambda op: False)
    expect(run_wait(cog.take_black_cog(scene.log))).to_be(False)
    expect(scene.logged('still hot')).to_be(True)
    water = scene.item(1929, cog.WATER, on_use=lambda target: False)
    expect(run_wait(cog.take_black_cog(scene.log))).to_be(False)
    water._fields['use_on'] = lambda target: True
    expect(run_wait(cog.take_black_cog(scene.log))).to_be(False)
    expect(scene.logged('water never poured')).to_be(True)

    scene = world(cog.COG_SPAWN['black'])
    state = {'cool': False, 'takes': 0}

    def take(op):
        expect(op).to_be('Take')
        state['takes'] += 1
        if state['cool']:
            scene.item(cog.COG_OBJ.black, 'Black cog')
        return True

    floor = scene.on_ground(cog.COG_OBJ.black, 'Black cog', effect=take)

    def pour(target):
        expect(target).to_be(floor)
        state['cool'] = True
        scene.take(1929)
        scene.item(1925, cog.BUCKET)
        return True

    scene.item(1929, cog.WATER, on_use=pour)
    expect(run_wait(cog.take_black_cog(scene.log))).to_be(True)
    expect(state['takes']).to_be(2)
    expect(scene.has(cog.COG_OBJ.black)).to_be(True)
    expect(scene.has(1929)).to_be(False)
    expect(scene.has(1925)).to_be(True)
    expect(run_wait(cog.take_black_cog(scene.log))).to_be(True)
    expect(state['takes']).to_be(2)


test('Clock Tower cools a refused black cog, spends the water and retries Take', black_cooling)


def pen_lever():
    scene = world(cog.LEVER_STAND)
    scene.loc('Lever', id=cog.LEVER_OPEN)
    expect(run_wait(cog.open_pen_gate(scene.log))).to_be(True)
    expect(scene.walks).to_equal([])
    scene = world()
    scene.no_walk = [cog.LEVER_STAND]
    expect(run_wait(cog.open_pen_gate(scene.log))).to_be(False)
    scene.no_walk = []
    expect(run_wait(cog.open_pen_gate(scene.log))).to_be(False)
    expect(scene.logged('no rat-cage lever')).to_be(True)
    lever = scene.loc('Lever', ['Pull'], id=cog.LEVER_SHUT, effect=lambda op: False)
    expect(run_wait(cog.open_pen_gate(scene.log))).to_be(False)
    lever._fields['interact'] = lambda op: True
    before = scene.clock
    expect(run_wait(cog.open_pen_gate(scene.log))).to_be(False)
    expect(scene.clock - before).to_be(6000)

    def pull(op):
        expect(op).to_be('Pull')
        scene.loc('Lever', id=cog.LEVER_OPEN)
        return True

    lever._fields['interact'] = pull
    expect(run_wait(cog.open_pen_gate(scene.log))).to_be(True)
    expect(cog.loc_by_id(cog.LEVER_OPEN)).to_be_defined()


test('Clock Tower verifies that pulling the cage lever changes its id', pen_lever)


def pen_crossings():
    scene = world(cog.PEN_GATE_INSIDE)
    expect(run_wait(cog.enter_pen(scene.log))).to_be(True)
    expect(scene.walks).to_equal([])
    scene = world()
    expect(run_wait(cog.enter_pen(scene.log))).to_be(False)
    scene.loc('Lever', id=cog.LEVER_OPEN)
    scene.no_walk = [cog.PEN_GATE_OUTSIDE]
    expect(run_wait(cog.enter_pen(scene.log))).to_be(False)
    scene.no_walk = []
    scene.step_ok = False
    expect(run_wait(cog.enter_pen(scene.log))).to_be(False)
    expect(scene.logged('did not let us through')).to_be(True)
    scene.step_ok = True
    expect(run_wait(cog.enter_pen(scene.log))).to_be(True)
    expect(cog.in_pen(scene.at)).to_be(True)
    scene.no_walk = [cog.PEN_GATE_INSIDE]
    expect(run_wait(cog.leave_pen(scene.log))).to_be(False)
    scene.no_walk = []
    expect(run_wait(cog.leave_pen(scene.log))).to_be(True)
    expect(scene.at).to_equal(cog.PEN_GATE_OUTSIDE)
    scene.at = cog.PEN_GATE_INSIDE
    scene.step_ok = False
    expect(run_wait(cog.leave_pen(scene.log))).to_be(False)
    expect(scene.logged('neither open nor openable')).to_be(True)
    gate = scene.loc('Gate', ['Open'], id=cog.PEN_GATE, effect=lambda op: False)
    expect(run_wait(cog.leave_pen(scene.log))).to_be(False)
    gate._fields['interact'] = lambda op: True
    before = scene.clock
    expect(run_wait(cog.leave_pen(scene.log))).to_be(False)
    expect(scene.clock - before).to_be(6000)
    gate._fields['interact'] = move(scene, cog.PEN_GATE_OUTSIDE)
    expect(run_wait(cog.leave_pen(scene.log))).to_be(True)
    expect(scene.at).to_equal(cog.PEN_GATE_OUTSIDE)


test('Clock Tower enters and leaves the cage through open and reclosed gates', pen_crossings)


def poison_pickup():
    scene = world()
    scene.no_walk = [cog.POISON_SPAWN]
    expect(run_wait(cog.take_poison(scene.log))).to_be(False)
    scene.no_walk = []
    expect(run_wait(cog.take_poison(scene.log))).to_be(False)
    expect(scene.logged('no Rat poison')).to_be(True)
    poison = scene.on_ground(cog.RAT_POISON_OBJ, 'Rat poison', effect=lambda op: False)
    expect(run_wait(cog.take_poison(scene.log))).to_be(False)
    poison._fields['interact'] = lambda op: True
    before = scene.clock
    expect(run_wait(cog.take_poison(scene.log))).to_be(False)
    expect(scene.clock - before).to_be(8000)
    scene.ground = []
    scene.on_ground(cog.RAT_POISON_OBJ, 'Rat poison')
    expect(run_wait(cog.take_poison(scene.log))).to_be(True)
    expect(scene.has(cog.RAT_POISON_OBJ)).to_be(True)
    scene.walk_ok = False
    expect(run_wait(cog.take_poison(scene.log))).to_be(True)


test('Clock Tower takes poison before entering the cage and confirms the pickup', poison_pickup)


def rat_crossing():
    scene = world(cog.PEN_GATE_INSIDE)
    scene.no_walk = [cog.RAT_GATE_STAND]
    expect(run_wait(cog.cross_rat_gate(scene.log))).to_be(False)
    scene.no_walk = []
    expect(run_wait(cog.cross_rat_gate(scene.log))).to_be(False)
    expect(scene.logged('no rat-room gate')).to_be(True)
    gate = scene.loc('Gate', ['Go-through'], id=cog.RAT_GATE, effect=lambda op: False)
    expect(run_wait(cog.cross_rat_gate(scene.log))).to_be(False)
    gate._fields['interact'] = lambda op: True
    before = scene.clock
    expect(run_wait(cog.cross_rat_gate(scene.log))).to_be(False)
    expect(scene.clock - before >= 6000).to_be(True)
    gate._fields['interact'] = move(scene, cog.COG_SPAWN['white'])
    ticks = scene.ticks
    expect(run_wait(cog.cross_rat_gate(scene.log))).to_be(True)
    expect(cog.in_white_room(scene.at)).to_be(True)
    expect(scene.ticks - ticks).to_be(2)


test('Clock Tower waits for the rat gate teleport and then settles the new scene', rat_crossing)


def white_room():
    scene = world(cog.COG_SPAWN['white'])
    expect(run_wait(cog.enter_white_room(scene.log))).to_be(True)
    expect(scene.walks).to_equal([])
    scene = world()
    expect(run_wait(cog.enter_white_room(scene.log))).to_be(False)
    scene.on_ground(cog.RAT_POISON_OBJ, 'Rat poison')
    expect(run_wait(cog.enter_white_room(scene.log))).to_be(False)
    expect(scene.has(cog.RAT_POISON_OBJ)).to_be(True)

    scene = world(cog.PEN_GATE_INSIDE)
    expect(run_wait(cog.enter_white_room(scene.log))).to_be(False)
    expect(scene.logged('leaving to fetch some')).to_be(True)
    expect(scene.at).to_equal(cog.PEN_GATE_OUTSIDE)

    scene = world(cog.PEN_GATE_INSIDE)
    gate = scene.loc('Gate', ['Go-through'], id=cog.RAT_GATE, effect=move(scene, cog.COG_SPAWN['white']))
    expect(run_wait(cog.enter_white_room(scene.log))).to_be(True)
    expect(scene.has(cog.RAT_POISON_OBJ)).to_be(False)

    scene = world(cog.PEN_GATE_INSIDE)
    state = {'poisoned': False, 'crossings': 0}

    def cross(op):
        expect(op).to_be('Go-through')
        state['crossings'] += 1
        if state['poisoned']:
            scene.at = cog.COG_SPAWN['white']
        return True

    scene.loc('Gate', ['Go-through'], id=cog.RAT_GATE, effect=cross)
    poison = scene.item(cog.RAT_POISON_OBJ, 'Rat poison', on_use=lambda target: False)
    expect(run_wait(cog.enter_white_room(scene.log))).to_be(False)
    trough = scene.loc('Food trough', id=cog.FOOD_TROUGH)
    expect(run_wait(cog.enter_white_room(scene.log))).to_be(False)
    expect(scene.has(cog.RAT_POISON_OBJ)).to_be(True)

    def pour(target):
        expect(target).to_be(trough)
        state['poisoned'] = True
        scene.take(cog.RAT_POISON_OBJ)
        return True

    poison._fields['use_on'] = pour
    before = state['crossings']
    expect(run_wait(cog.enter_white_room(scene.log))).to_be(True)
    expect(state['crossings'] - before).to_be(2)
    expect(scene.has(cog.RAT_POISON_OBJ)).to_be(False)
    expect(cog.in_white_room(scene.at)).to_be(True)


test('Clock Tower probes the rat gate, poisons the trough if refused and retries', white_room)


def blue_room():
    scene = world(cog.COG_SPAWN['blue'])
    expect(run_wait(cog.enter_blue_room(scene.log))).to_be(True)
    expect(scene.walks).to_equal([])
    scene = world()
    scene.no_walk = [cog.SECRET_WALL_STAND]
    expect(run_wait(cog.enter_blue_room(scene.log))).to_be(False)
    scene.no_walk = []
    expect(run_wait(cog.enter_blue_room(scene.log))).to_be(False)
    expect(scene.logged('no secret wall')).to_be(True)
    wall = scene.loc('Wall', ['Push'], id=cog.SECRET_WALL, effect=lambda op: False)
    expect(run_wait(cog.enter_blue_room(scene.log))).to_be(False)
    wall._fields['interact'] = lambda op: True
    before = scene.clock
    expect(run_wait(cog.enter_blue_room(scene.log))).to_be(False)
    expect(scene.clock - before).to_be(8000)
    wall._fields['interact'] = move(scene, cog.COG_SPAWN['blue'])
    ticks = scene.ticks
    expect(run_wait(cog.enter_blue_room(scene.log))).to_be(True)
    expect(cog.in_blue_room(scene.at)).to_be(True)
    expect(scene.ticks - ticks).to_be(2)


test('Clock Tower pushes the secret wall and verifies arrival in the blue room', blue_room)


def fetch_cogs():
    for colour in cog.COLOURS:
        scene = world(cog.COG_SPAWN[colour])
        id = getattr(cog.COG_OBJ, colour)
        scene.on_ground(id, colour + ' cog')
        expect(run_wait(cog.fetch_leg(colour)(scene.log))).to_be(True)
        expect(scene.has(id)).to_be(True)
        scene = world()
        scene.walk_ok = False
        expect(run_wait(cog.fetch_leg(colour)(scene.log))).to_be(False)
        scene = world(cog.WHITE_ROOM_LADDER if colour != 'white' else cog.BLUE_ROOM_LADDER)
        expect(run_wait(cog.fetch_leg(colour)(scene.log))).to_be(False)
        if colour in ['blue', 'white']:
            scene = world(cog.COG_SPAWN[colour])
            scene.walk_ok = False
            expect(run_wait(cog.fetch_leg(colour)(scene.log))).to_be(False)


test('Clock Tower fetch legs route to the right room and propagate access failures', fetch_cogs)


def place_cogs():
    for colour in cog.COLOURS:
        stand = cog.SPINDLE_STAND[colour]
        id = getattr(cog.COG_OBJ, colour)
        scene = world(cog.WHITE_ROOM_LADDER)
        expect(run_wait(cog.place_leg(colour)(scene.log))).to_be(False)
        scene = world(stand)
        scene.item(id, colour + ' cog')
        scene.no_walk = [stand]
        # Start far enough away that the approach must walk.
        scene.at = cog.CELLAR_FOOT if colour == 'black' else cog.KOJO.anchor
        expect(run_wait(cog.place_leg(colour)(scene.log))).to_be(False)
        scene = world(stand)
        used = []

        def fit(target):
            used.append(target.id)
            scene.take(id)
            return True

        scene.item(id, colour + ' cog', on_use=fit)
        scene.loc('Clock spindle', id=999, dist=0)
        expect(run_wait(cog.place_leg(colour)(scene.log))).to_be(False)
        expect(used).to_equal([])
        expect(scene.has(id)).to_be(True)
        scene.loc('Clock spindle', id=cog.SPINDLE_LOC[colour])
        expect(run_wait(cog.place_leg(colour)(scene.log))).to_be(True)
        expect(used).to_equal([cog.SPINDLE_LOC[colour]])
        expect(scene.has(id)).to_be(False)


test('Clock Tower fits every cog to its spindle id, ignoring nearer decoys', place_cogs)
