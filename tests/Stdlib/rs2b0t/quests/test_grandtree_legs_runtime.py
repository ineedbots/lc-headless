"""Grand Tree's cupboard, tree climbs and Daconia root sweep against Scene facades."""

from rs2004.geometry import Tile
from rs2004.quests.defs.grandtree import legs
from rs2004.quests.defs.grandtree.areas import GT_LOC, GT_OBJ, GT_ROOTS, GT_TILE


def move(scene, tile):
    def effect(op):
        scene.at = tile
        return True
    return effect


def cupboard():
    scene = Scene(GT_TILE.cupboard_stand)
    scene.walk_ok = False
    expect(run_wait(legs.search_cupboard(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(legs.search_cupboard(scene.log))).to_be(False)
    expect(scene.logged('no open cupboard')).to_be(True)
    shut = scene.loc('Cupboard', ['Open'], tile=Tile(2476, 3465, 1), id=GT_LOC.CUPBOARD_SHUT, effect=lambda op: False)
    expect(run_wait(legs.search_cupboard(scene.log))).to_be(False)
    shut._fields['interact'] = lambda op: True
    before = scene.clock
    expect(run_wait(legs.search_cupboard(scene.log))).to_be(False)
    expect(scene.clock - before >= 6000).to_be(True)
    scene.locs = []
    scene.loc('Cupboard', ['Search'], tile=Tile(2476, 3465, 0), id=GT_LOC.CUPBOARD_OPEN)
    scene.loc('Cupboard', ['Search'], tile=Tile(2480, 3465, 1), id=GT_LOC.CUPBOARD_OPEN)
    expect(run_wait(legs.search_cupboard(scene.log))).to_be(False)
    opened = scene.loc('Cupboard', ['Search'], tile=Tile(2476, 3465, 1), id=GT_LOC.CUPBOARD_OPEN, effect=lambda op: False)
    expect(run_wait(legs.search_cupboard(scene.log))).to_be(False)
    opened._fields['interact'] = lambda op: True
    before = scene.clock
    expect(run_wait(legs.search_cupboard(scene.log))).to_be(False)
    expect(scene.clock - before >= 10000).to_be(True)
    scene.locs = []

    def search(op):
        expect(op).to_be('Search')
        scene.item(GT_OBJ.JOURNAL, "Glough's journal")
        return True

    def open_cupboard(op):
        expect(op).to_be('Open')
        scene.locs = []
        scene.loc('Cupboard', ['Search'], tile=Tile(2476, 3465, 1), id=GT_LOC.CUPBOARD_OPEN, effect=search)
        return True

    scene.loc('Cupboard', ['Open'], tile=Tile(2476, 3465, 1), id=GT_LOC.CUPBOARD_SHUT, effect=open_cupboard)
    expect(run_wait(legs.search_cupboard(scene.log))).to_be(True)
    expect(scene.has(GT_OBJ.JOURNAL)).to_be(True)
    walks = len(scene.walks)
    expect(run_wait(legs.search_cupboard(scene.log))).to_be(True)
    expect(len(scene.walks)).to_be(walks)


test('Grand Tree opens the correct cupboard and confirms the journal after its id changes', cupboard)


def climb_tree():
    scene = Scene(GT_TILE.pillar_floor)
    expect(run_wait(legs.climb_to_pillars(scene.log))).to_be(True)
    expect(scene.walks).to_equal([])
    scene.at = None
    scene.walk_ok = False
    expect(run_wait(legs.climb_to_pillars(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(legs.climb_to_pillars(scene.log))).to_be(False)
    scene.loc('Tree', ['Climb-up'], id=GT_LOC.DOWN_TREE)
    expect(run_wait(legs.climb_to_pillars(scene.log))).to_be(False)
    tree = scene.loc('Tree', ['Climb-up'], id=GT_LOC.CLIMB_TREE, effect=lambda op: False)
    expect(run_wait(legs.climb_to_pillars(scene.log))).to_be(False)
    tree._fields['interact'] = lambda op: True
    before = scene.clock
    expect(run_wait(legs.climb_to_pillars(scene.log))).to_be(False)
    expect(scene.clock - before >= 10000).to_be(True)
    tree._fields['interact'] = move(scene, GT_TILE.pillar_floor)
    expect(run_wait(legs.climb_to_pillars(scene.log))).to_be(True)
    expect(scene.at).to_equal(GT_TILE.pillar_floor)


test('Grand Tree confirms the pillar floor after climbing the matching tree', climb_tree)


def descend_tree():
    scene = Scene()
    expect(run_wait(legs.descend_glough_tree(scene.log))).to_be(True)
    scene.at = GT_TILE.glough_house_foot
    expect(run_wait(legs.descend_glough_tree(scene.log))).to_be(True)
    expect(scene.walks).to_equal([])
    scene.at = GT_TILE.pillar_floor
    scene.walk_ok = False
    expect(run_wait(legs.descend_glough_tree(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(legs.descend_glough_tree(scene.log))).to_be(False)
    tree = scene.loc('Tree', ['Climb-down'], id=GT_LOC.DOWN_TREE, effect=lambda op: False)
    expect(run_wait(legs.descend_glough_tree(scene.log))).to_be(False)
    tree._fields['interact'] = lambda op: True
    before = scene.clock
    expect(run_wait(legs.descend_glough_tree(scene.log))).to_be(False)
    expect(scene.clock - before >= 10000).to_be(True)
    tree._fields['interact'] = move(scene, GT_TILE.climb_tree_stand)
    scene.no_walk = [GT_TILE.glough_house_foot]
    expect(run_wait(legs.descend_glough_tree(scene.log))).to_be(False)
    expect(scene.at).to_equal(GT_TILE.climb_tree_stand)
    scene.at = GT_TILE.pillar_floor
    scene.no_walk = []
    expect(run_wait(legs.descend_glough_tree(scene.log))).to_be(True)
    expect(scene.walks[-2:]).to_equal([GT_TILE.down_tree_stand, GT_TILE.glough_house_foot])
    expect(scene.at).to_equal(GT_TILE.glough_house_foot)


test('Grand Tree descends through the first floor before walking to the ground', descend_tree)


def root_sweep():
    scene = Scene(GT_TILE.cave_landing)
    legs.reset_root_cursor()
    searched = []

    def root_effect(root, searched):
        def search(op):
            expect(op).to_be('Search')
            searched.append(root.sw)
            return True
        return search

    for root in GT_ROOTS:
        scene.loc('Root', ['Search'], tile=root.sw, effect=root_effect(root, searched))
    for root in GT_ROOTS:
        before = scene.clock
        expect(run_wait(legs.search_next_root(scene.log))).to_be(True)
        expect(scene.walks[-1]).to_equal(root.stand)
        expect(scene.clock - before >= 6000).to_be(True)
    expect(searched).to_equal([root.sw for root in GT_ROOTS])
    expect(scene.has(GT_OBJ.DACONIA)).to_be(False)
    expect(scene.logged('nothing')).to_be(True)

    def find_rock(op):
        expect(op).to_be('Search')
        scene.item(GT_OBJ.DACONIA, 'Daconia rock')
        return True

    scene.locs[0]._fields['interact'] = find_rock
    expect(run_wait(legs.search_next_root(scene.log))).to_be(True)
    expect(scene.walks[-1]).to_equal(GT_ROOTS[0].stand)
    expect(scene.has(GT_OBJ.DACONIA)).to_be(True)
    expect(scene.logged('the Daconia rock')).to_be(True)
    walks = len(scene.walks)
    expect(run_wait(legs.search_next_root(scene.log))).to_be(True)
    expect(len(scene.walks)).to_be(walks)
    legs.reset_root_cursor()


test('Grand Tree sweeps every root in order, wraps around and stops after finding Daconia', root_sweep)


def root_failures():
    scene = Scene(GT_TILE.cave_landing)
    legs.reset_root_cursor()
    scene.walk_ok = False
    expect(run_wait(legs.search_next_root(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(legs.search_next_root(scene.log))).to_be(False)
    expect(scene.walks[-1]).to_equal(GT_ROOTS[1].stand)
    expect(scene.logged('no Root')).to_be(True)
    root = GT_ROOTS[2]
    scene.loc('Root', ['Search'], tile=root.sw, effect=lambda op: False)
    expect(run_wait(legs.search_next_root(scene.log))).to_be(False)
    expect(scene.walks[-1]).to_equal(root.stand)
    expect(scene.has(GT_OBJ.DACONIA)).to_be(False)
    legs.reset_root_cursor()


test('Grand Tree reports failed root walks, missing roots and refused searches', root_failures)


def cave_exit():
    scene = Scene(GT_TILE.narnode)
    expect(run_wait(legs.leave_caves(scene.log))).to_be(True)
    expect(scene.walks).to_equal([])
    scene.at = GT_TILE.cave_landing
    scene.walk_ok = False
    expect(run_wait(legs.leave_caves(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(legs.leave_caves(scene.log))).to_be(False)
    expect(scene.logged('no ladder out')).to_be(True)
    ladder = scene.loc('Ladder', ['Climb-up'], effect=lambda op: False)
    expect(run_wait(legs.leave_caves(scene.log))).to_be(False)
    ladder._fields['interact'] = lambda op: True
    before = scene.clock
    expect(run_wait(legs.leave_caves(scene.log))).to_be(False)
    expect(scene.clock - before).to_be(10000)
    ladder._fields['interact'] = move(scene, GT_TILE.narnode)
    expect(run_wait(legs.leave_caves(scene.log))).to_be(True)
    expect(scene.walks[-1]).to_equal(GT_TILE.cave_ladder)
    expect(scene.at).to_equal(GT_TILE.narnode)


test('Grand Tree leaves the caves only after the ladder reaches the surface', cave_exit)
