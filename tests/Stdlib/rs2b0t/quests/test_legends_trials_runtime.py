"""Legends Quest's trials descent and ascent against spied facades: the crevice, both ancient gates, the boulders, the
jagged wall, the marked wall's runes, the gems and the book, the magic gate, the winch, and the ways back out, each
through its success and its failures."""

from rs2004.game import direct_navigator, game
from rs2004.geometry import Tile
from rs2004.quests.defs.legends import trials
from rs2004.quests.defs.legends.areas import GEM_ROCKS, LQ_ID, LQ_LOC, LQ_LOC_ID, LQ_TILE, WALL_RUNES


def world(pocket='shaman_cave', at=None):
    """A Scene whose pocket of the cave complex is named outright: the pockets' tiles have their own tests."""
    scene = Scene(at if at is not None else LQ_TILE.SHAMAN_BOOKCASE)
    scene.pocket = pocket
    scene.steps_to = None
    patch(trials, 'pocket', lambda: scene.pocket)
    patch(trials, 'legends_pocket', lambda tile: scene.pocket)
    spy_on(direct_navigator, 'walk_to', impl=lambda *args, **kwargs: stepped(scene))
    return scene


def stepped(scene):
    if scene.steps_to is not None:
        scene.pocket = scene.steps_to
    return True
    yield


def enters(scene, pocket):
    def effect(*args):
        scene.pocket = pocket
    return effect


def run(gen):
    return run_wait(gen)


# Where the player stands.

def descent_order():
    scene = world('boulder_two')
    expect(trials.past('crevice')).to_be(True)
    expect(trials.past('boulder_two')).to_be(True)
    expect(trials.past('trials')).to_be(False)
    scene.pocket = None
    expect(trials.past('crevice')).to_be(False)
    # A pocket off the descent counts as before all of it.
    scene.pocket = 'octagram'
    expect(trials.past('shaman_cave')).to_be(False)


test('the descent is an ordered ladder, and being below a rung is being past it', descent_order)


def real_pocket_reader():
    Scene(LQ_TILE.SHAMAN_BOOKCASE)
    expect(trials.pocket()).to_be_defined()


test('the pocket reads the tile', real_pocket_reader)


def finding_gate_leaves():
    scene = world()
    expect(trials.either_leaf(1, 2)).to_be_null()
    right = scene.loc('Gate', ['Open'], id=2)
    expect(trials.either_leaf(1, 2).id).to_be(right.id)
    left = scene.loc('Gate', ['Search'], id=1)
    expect(trials.either_leaf(1, 2).id).to_be(left.id)
    expect(trials.either_leaf(1, 2, 'Open').id).to_be(right.id)


test('either leaf of a double gate will do, offering the op when one is named', finding_gate_leaves)


def stepping_through():
    # The gate's own teleport lands during the settle.
    scene = world('outer_gate')
    expect(run(trials.step_through(LQ_TILE.LOCKPICK_GATE_SOUTH, 'outer_gate', scene.log))).to_be(True)
    expect(direct_navigator.walk_to.calls).to_have_length(0)

    scene = world('crevice')
    scene.steps_to = 'outer_gate'
    expect(run(trials.step_through(LQ_TILE.LOCKPICK_GATE_SOUTH, 'outer_gate', scene.log))).to_be(True)

    scene = world('crevice')
    expect(run(trials.step_through(LQ_TILE.LOCKPICK_GATE_SOUTH, 'outer_gate', scene.log))).to_be(False)
    expect(scene.logged('the gate did not let us through to outer_gate')).to_be(True)

    scene = world('crevice')
    expect(run(trials.step_through(LQ_TILE.LOCKPICK_GATE_SOUTH, 'outer_gate', scene.log, True))).to_be(False)
    expect(scene.lines).to_have_length(0)


test("a gate's crossing is taken as landed, or walked the last tile", stepping_through)


# The crevice.

def bookcase():
    scene = world('crevice')
    expect(run(trials.crawl_bookcase(scene.log))).to_be(True)
    expect(scene.walks).to_have_length(0)

    scene = world()
    scene.loc_op_effect = enters(scene, 'crevice')
    expect(run(trials.crawl_bookcase(scene.log))).to_be(True)
    expect(scene.loc_ops).to_equal([(LQ_LOC.BOOKCASE, 'Search')])

    scene = world()
    scene.walk_ok = False
    expect(run(trials.crawl_bookcase(scene.log))).to_be(False)


test('the crevice is reached through the bookcase', bookcase)


def bookcase_retries():
    # The crawl lands during the settle of a later pass, not the goal's own wait.
    scene = world()
    tries = []

    def third(name, op):
        tries.append(op)

    scene.loc_op_effect = third
    expect(run(trials.crawl_bookcase(scene.log))).to_be(False)
    expect(tries).to_have_length(6)
    expect(scene.logged('six squeezes')).to_be(True)

    scene = world()
    scene.later(enters(scene, 'crevice'))
    expect(run(trials.crawl_bookcase(scene.log))).to_be(True)
    expect(scene.loc_ops).to_have_length(0)


test('the Agility roll on the crawl gets six goes', bookcase_retries)


def crevice_back():
    scene = world('shaman_cave')
    expect(run(trials.crawl_back_from_crevice(scene.log))).to_be(True)
    expect(scene.loc_ops).to_have_length(0)

    scene = world('crevice')
    scene.loc_op_effect = enters(scene, 'shaman_cave')
    expect(run(trials.crawl_back_from_crevice(scene.log))).to_be(True)

    scene = world('crevice')
    expect(run(trials.crawl_back_from_crevice(scene.log))).to_be(False)


test('the crevice crawls back west', crevice_back)


# The outer gate.

def lockpick_scene():
    scene = world('crevice')
    scene.item(LQ_ID.LOCKPICK, 'Lockpick')
    return scene


def picks_the_gate():
    scene = lockpick_scene()

    def picked(op):
        scene.locs = []
        scene.steps_to = 'outer_gate'

    scene.loc('Gate', ['Search'], id=LQ_LOC_ID.LOCKPICK_GATE_L, effect=picked)
    expect(run(trials.open_outer_gate(scene.log))).to_be(True)


test('picking the lock opens the outer gate', picks_the_gate)


def missed_lock():
    scene = lockpick_scene()
    tries = []

    def pick(op):
        tries.append(op)
        if len(tries) == 1:
            scene.chat.shown = ['You ' + trials.PICK_MISSED + '.']
        else:
            scene.chat.shown = []
            scene.locs = []
            scene.steps_to = 'outer_gate'

    scene.loc('Gate', ['Search'], id=LQ_LOC_ID.LOCKPICK_GATE_R, effect=pick)
    expect(run(trials.open_outer_gate(scene.log))).to_be(True)
    expect(tries).to_have_length(2)


test('a missed lock is clicked again at once', missed_lock)


def outer_gate_failures():
    scene = world('outer_gate')
    expect(run(trials.open_outer_gate(scene.log))).to_be(True)

    scene = world()
    scene.walk_ok = False
    expect(run(trials.open_outer_gate(scene.log))).to_be(False)

    scene = world('crevice')
    expect(run(trials.open_outer_gate(scene.log))).to_be(False)
    expect(scene.logged('no lockpick')).to_be(True)

    scene = lockpick_scene()
    scene.walk_ok = False
    expect(run(trials.open_outer_gate(scene.log))).to_be(False)

    # The gate never opens.
    scene = lockpick_scene()
    scene.loc('Gate', ['Search'], id=LQ_LOC_ID.LOCKPICK_GATE_L)
    expect(run(trials.open_outer_gate(scene.log))).to_be(False)
    expect(scene.logged('ten lockpick attempts')).to_be(True)


test('the outer gate fails with no lockpick, no way there, or no opening', outer_gate_failures)


def leaving_outer_gate():
    scene = world('crevice')
    expect(run(trials.leave_outer_gate(scene.log))).to_be(True)
    expect(scene.walks).to_have_length(0)

    scene = world('outer_gate')
    scene.walk_ok = False
    expect(run(trials.leave_outer_gate(scene.log))).to_be(False)

    # It opens, and the box is read before it is cleared.
    scene = world('outer_gate', LQ_TILE.LOCKPICK_GATE_SOUTH)

    def opens(op):
        scene.chat.shown = ['The doors open.']
        scene.steps_to = 'crevice'

    scene.loc('Gate', ['Open'], id=LQ_LOC_ID.LOCKPICK_GATE_L, effect=opens)
    expect(run(trials.leave_outer_gate(scene.log))).to_be(True)

    # Standing open from an earlier pull: no click is needed.
    scene = world('outer_gate', LQ_TILE.LOCKPICK_GATE_SOUTH)
    scene.loc('Gate', [], id=LQ_LOC_ID.LOCKPICK_GATE_L_OPEN)
    scene.steps_to = 'crevice'
    expect(run(trials.leave_outer_gate(scene.log))).to_be(True)

    # Nothing there at all.
    scene = world('outer_gate', LQ_TILE.LOCKPICK_GATE_SOUTH)
    expect(run(trials.leave_outer_gate(scene.log))).to_be(False)
    expect(scene.logged('no ancient gate in either stage')).to_be(True)


test('the outer gate opens from the inside with no lockpick', leaving_outer_gate)


def outer_gate_refuses_to_let_out():
    scene = world('outer_gate', LQ_TILE.LOCKPICK_GATE_SOUTH)
    scene.loc('Gate', ['Open'], id=LQ_LOC_ID.LOCKPICK_GATE_L, effect=lambda op: False)
    expect(run(trials.leave_outer_gate(scene.log))).to_be(False)
    expect(scene.logged('six pulls and the outer gate would not let us back out')).to_be(True)
    expect(scene.logged('shut leaf present, open leaf absent, click refused')).to_be(True)

    scene = world('outer_gate', LQ_TILE.LOCKPICK_GATE_SOUTH)

    def says(op):
        scene.chat.shown = ['You push on the doors.']

    scene.loc('Gate', ['Open'], id=LQ_LOC_ID.LOCKPICK_GATE_L, effect=says)
    expect(run(trials.leave_outer_gate(scene.log))).to_be(False)
    expect(scene.logged('click dispatched')).to_be(True)
    expect(scene.logged('box "you push on the doors.')).to_be(True)


test('a gate that will not let the player out says what it saw', outer_gate_refuses_to_let_out)


# The boulders.

def boulder_scene(start, rock_effect=None, boulder=None):
    chosen = boulder if boulder is not None else trials.BOULDERS[0]
    scene = world(start, chosen.north)
    scene.loc('Boulder', ['Smash-to-bits'], id=chosen.id, effect=rock_effect)
    return scene


def boulder_crossings():
    b = trials.BOULDERS[0]
    scene = world('outer_gate', b.north)
    scene.loc('Boulder', ['Smash-to-bits'], id=b.id, effect=enters(scene, b.to))
    expect(run(trials.mine_boulder(b, False, scene.log))).to_be(True)

    # Back the other way.
    scene = world(b.to, b.south)
    scene.loc('Boulder', ['Smash-to-bits'], id=b.id, effect=enters(scene, b.from_))
    expect(run(trials.mine_boulder(b, True, scene.log))).to_be(True)

    # Already past it going down; not skipped when going back.
    scene = world('wall_room')
    expect(run(trials.mine_boulder(b, False, scene.log))).to_be(True)
    expect(scene.walks).to_have_length(0)
    scene = world(b.from_)
    expect(run(trials.mine_boulder(b, True, scene.log))).to_be(True)


test('each boulder is one crossing, mined again from the far side to return', boulder_crossings)


def boulder_scratches():
    b = trials.BOULDERS[0]
    scene = world('outer_gate', b.north)
    swings = []

    def swing(op):
        swings.append(op)
        if len(swings) < 3:
            scene.say('You ' + trials.SCRATCHED + '.')
        else:
            scene.pocket = b.to

    scene.loc('Boulder', ['Smash-to-bits'], id=b.id, effect=swing)
    expect(run(trials.mine_boulder(b, False, scene.log))).to_be(True)
    expect(swings).to_have_length(3)
    # A scratch ends the wait early, rather than spending the swing's whole budget.
    expect(scene.clock).to_be_less_than(15000)


test('a scratch moves straight on to the next swing', boulder_scratches)


def boulder_failures():
    b = trials.BOULDERS[0]
    scene = world('outer_gate', Tile(b.north.x + 9, b.north.z, 0))
    scene.walk_ok = False
    expect(run(trials.mine_boulder(b, False, scene.log))).to_be(False)

    scene = world('outer_gate', b.north)
    expect(run(trials.mine_boulder(b, False, scene.log))).to_be(False)
    expect(scene.logged(f'boulder {b.id} is not in the scene')).to_be(True)

    scene = boulder_scene('outer_gate', lambda op: False)
    expect(run(trials.mine_boulder(b, False, scene.log))).to_be(False)
    expect(scene.logged('twenty swings')).to_be(True)


test('a boulder fails with no way there, no boulder, or twenty swings', boulder_failures)


# The inner gate.

def inner_gate():
    scene = world('inner_gate', LQ_TILE.STRENGTH_GATE_NORTH)

    def forced(op):
        scene.chat.shown = ['You manage to force the doors open.']
        scene.steps_to = 'trials'

    scene.loc('Gate', ['Open'], id=LQ_LOC_ID.STRENGTH_GATE_L, effect=forced)
    expect(run(trials.open_inner_gate(False, scene.log))).to_be(True)

    # Past it; and back the other way.
    scene = world('wall_room')
    expect(run(trials.open_inner_gate(False, scene.log))).to_be(True)
    scene = world('inner_gate')
    expect(run(trials.open_inner_gate(True, scene.log))).to_be(True)

    scene = world('trials', LQ_TILE.STRENGTH_GATE_SOUTH)
    scene.steps_to = 'inner_gate'
    scene.loc('Gate', ['Open'], id=LQ_LOC_ID.STRENGTH_GATE_R)
    expect(run(trials.open_inner_gate(True, scene.log))).to_be(True)


test('the inner gate is forced open, either way', inner_gate)


def inner_gate_misses():
    scene = world('inner_gate', LQ_TILE.STRENGTH_GATE_NORTH)
    pushes = []

    def push(op):
        pushes.append(op)
        if len(pushes) == 1:
            scene.chat.shown = ['You ' + trials.FORCE_MISSED + '.']
        else:
            scene.chat.shown = ['You manage to force the doors open.']
            scene.steps_to = 'trials'

    scene.loc('Gate', ['Open'], id=LQ_LOC_ID.STRENGTH_GATE_L, effect=push)
    expect(run(trials.open_inner_gate(False, scene.log))).to_be(True)
    expect(pushes).to_have_length(2)


test('a missed push is pushed again', inner_gate_misses)


def inner_gate_failures():
    scene = world('inner_gate', Tile(LQ_TILE.STRENGTH_GATE_NORTH.x + 9, LQ_TILE.STRENGTH_GATE_NORTH.z, 0))
    scene.walk_ok = False
    expect(run(trials.open_inner_gate(False, scene.log))).to_be(False)

    scene = world('inner_gate', LQ_TILE.STRENGTH_GATE_NORTH)
    expect(run(trials.open_inner_gate(False, scene.log))).to_be(False)
    expect(scene.logged('ten pushes')).to_be(True)


test('the inner gate fails with no way there, or ten pushes', inner_gate_failures)


# The jagged wall.

def jagged_wall():
    scene = world('trials', LQ_TILE.JAGGED_WALL_SOUTH)
    scene.loc(LQ_LOC.JAGGED_WALL, ['Jump-over'], effect=enters(scene, 'wall_room'))
    expect(run(trials.jump_jagged_wall(False, scene.log))).to_be(True)

    scene = world('gem_room')
    expect(run(trials.jump_jagged_wall(False, scene.log))).to_be(True)
    expect(scene.walks).to_have_length(0)

    scene = world('wall_room', LQ_TILE.JAGGED_WALL_NORTH)
    scene.loc(LQ_LOC.JAGGED_WALL, ['Jump-over'], effect=enters(scene, 'trials'))
    expect(run(trials.jump_jagged_wall(True, scene.log))).to_be(True)


test('the jagged wall jumps either way', jagged_wall)


def jagged_wall_failures():
    scene = world('trials', Tile(LQ_TILE.JAGGED_WALL_SOUTH.x + 9, LQ_TILE.JAGGED_WALL_SOUTH.z, 0))
    scene.walk_ok = False
    expect(run(trials.jump_jagged_wall(False, scene.log))).to_be(False)

    scene = world('trials', LQ_TILE.JAGGED_WALL_SOUTH)
    expect(run(trials.jump_jagged_wall(False, scene.log))).to_be(False)
    expect(scene.logged('no jagged wall')).to_be(True)

    scene = world('trials', LQ_TILE.JAGGED_WALL_SOUTH)
    scene.loc(LQ_LOC.JAGGED_WALL, ['Jump-over'])
    expect(run(trials.jump_jagged_wall(False, scene.log))).to_be(False)
    expect(scene.logged('eight jumps')).to_be(True)

    scene = world('trials', LQ_TILE.JAGGED_WALL_SOUTH)
    scene.loc(LQ_LOC.JAGGED_WALL, ['Jump-over'], effect=lambda op: False)
    expect(run(trials.jump_jagged_wall(False, scene.log))).to_be(False)
    expect(scene.logged('eight jumps')).to_be(True)


test('the jagged wall fails with no way there, no wall, or eight failed jumps', jagged_wall_failures)


# The marked wall.

def wall_scene(pocket='wall_room', stand=None):
    scene = world(pocket, stand if stand is not None else LQ_TILE.MARKED_WALL_IN)
    scene.loc(LQ_LOC.MARKED_WALL, ['Use'], id=LQ_LOC_ID.MARKED_WALL)
    return scene


def hold_runes(scene, on_use=None):
    for rune in WALL_RUNES:
        if not scene.has(rune.id):
            scene.item(rune.id, rune.name, on_use=on_use)


def slide_phrase():
    expect(trials.slid('you slide the rune into the depression.')).to_be(True)
    expect(trials.slid('it burns red hot in your hand')).to_be(False)


test('a rune going in is told by its wording', slide_phrase)


def feeds_the_wall():
    scene = wall_scene()
    fed = []

    def feed(target):
        fed.append(target.id)
        if len(fed) == 4:
            scene.pocket = 'gem_room'

    hold_runes(scene, feed)
    expect(run(trials.cross_marked_wall(False, scene.log))).to_be(True)
    expect(fed).to_have_length(4)
    expect(scene.loc_ops).to_have_length(0)


test('held runes are fed to the wall, and that opens it', feeds_the_wall)


def rune_supply_runs_out():
    scene = wall_scene()
    scene.item(WALL_RUNES[0].id, WALL_RUNES[0].name)
    expect(run(trials.cross_marked_wall(False, scene.log))).to_be(False)
    expect(scene.logged(f'no {WALL_RUNES[1].name} left')).to_be(True)


test('a wall still short of runes fails and names what is missing', rune_supply_runs_out)


def rune_fed_and_wall_opens_at_last():
    scene = wall_scene()
    scene.item(WALL_RUNES[3].id, WALL_RUNES[3].name, on_use=enters(scene, 'gem_room'))
    expect(run(trials.cross_marked_wall(False, scene.log))).to_be(True)


test('the last rune alone is enough on an already fed wall', rune_fed_and_wall_opens_at_last)


def marked_wall_by_use():
    scene = wall_scene()
    scene.loc_op_effect = enters(scene, 'gem_room')
    expect(run(trials.cross_marked_wall(False, scene.log))).to_be(True)
    expect(scene.loc_ops).to_equal([(LQ_LOC.MARKED_WALL, 'Use')])

    # Past it.
    scene = world('winch_room')
    expect(run(trials.cross_marked_wall(False, scene.log))).to_be(True)

    # Back through.
    scene = wall_scene('gem_room', LQ_TILE.MARKED_WALL_OUT)
    scene.loc_op_effect = enters(scene, 'wall_room')
    expect(run(trials.cross_marked_wall(True, scene.log))).to_be(True)

    scene = wall_scene('gem_room', LQ_TILE.MARKED_WALL_OUT)
    expect(run(trials.cross_marked_wall(True, scene.log))).to_be(False)
    expect(scene.logged('will not open from the gem room')).to_be(True)

    scene = world('wall_room', Tile(LQ_TILE.MARKED_WALL_IN.x + 9, LQ_TILE.MARKED_WALL_IN.z, 0))
    scene.walk_ok = False
    expect(run(trials.cross_marked_wall(False, scene.log))).to_be(False)

    # No runes and no opening: all five are reported missing.
    scene = wall_scene()
    expect(run(trials.cross_marked_wall(False, scene.log))).to_be(False)
    expect(scene.logged(f'no {WALL_RUNES[0].name} left')).to_be(True)


test('a fed wall answers a plain Use, either way', marked_wall_by_use)


def wall_opens_after_the_use_fails():
    scene = wall_scene()
    tries = []

    def later_rune(name, op):
        tries.append(op)

    scene.loc_op_effect = later_rune
    state = {'fed': False}

    def feeding(wall, want, log):
        state['fed'] = True
        scene.pocket = want
        return True
        yield

    patch(trials, 'place_wall_runes', feeding)
    expect(run(trials.cross_marked_wall(False, scene.log))).to_be(True)
    expect(state['fed']).to_be(True)
    expect(tries).to_have_length(1)


test('a wall that will not answer a Use is fed its runes after all', wall_opens_after_the_use_fails)


# The gems and the book.

def hold_gems(scene, on_use=None):
    for gem in GEM_ROCKS:
        scene.item(gem.id, gem.name, on_use=on_use)
        scene.loc(LQ_LOC.CARVED_ROCK, ['Use'], tile=gem.rock, id=LQ_LOC_ID.GEM_ROCK)


def gems_placed():
    scene = world('gem_room')
    placed = []

    def place(target):
        placed.append(target.id)
        scene.say('It glows and starts spinning.')

    hold_gems(scene, place)
    expect(run(trials.place_gems(scene.log))).to_be(True)
    expect(placed).to_have_length(len(GEM_ROCKS))


test('every gem settles over its rock', gems_placed)


def gem_failures():
    # None held: a resume with the wall already done.
    scene = world('gem_room')
    expect(run(trials.place_gems(scene.log))).to_be(True)
    expect(scene.lines).to_have_length(0)

    # A gem already hovering answers with its own line.
    scene = world('gem_room')
    gem = GEM_ROCKS[0]
    scene.item(gem.id, gem.name, on_use=lambda target: scene.say('That gem is already placed.'))
    scene.loc(LQ_LOC.CARVED_ROCK, ['Use'], tile=gem.rock, id=LQ_LOC_ID.GEM_ROCK)
    expect(run(trials.place_gems(scene.log))).to_be(True)

    scene = world('gem_room')
    gem = GEM_ROCKS[0]
    scene.item(gem.id, gem.name)
    expect(run(trials.place_gems(scene.log))).to_be(False)
    expect(scene.logged(f'the {gem.name} would not settle')).to_be(True)


test('a gem that says nothing stops the leg, and one already placed does not', gem_failures)


def book_on_ground(scene, effect=None):
    return scene.on_ground(LQ_ID.BOOK_OF_BINDING, 'Book of Binding', effect=effect)


def the_book():
    scene = world('gem_room', LQ_TILE.BOOK_SPAWN)
    book_on_ground(scene)
    expect(run(trials.take_book_of_binding(scene.log))).to_be(True)
    expect(scene.has(LQ_ID.BOOK_OF_BINDING)).to_be(True)

    scene = world('gem_room')
    scene.item(LQ_ID.BOOK_OF_BINDING, 'Book of Binding')
    expect(run(trials.take_book_of_binding(scene.log))).to_be(True)
    expect(scene.walks).to_have_length(0)


test('the Book of Binding is taken once conjured', the_book)


def book_conjured_by_the_gems():
    scene = world('gem_room')
    gem = GEM_ROCKS[0]

    def place(target):
        scene.say('It glows and starts spinning.')
        book_on_ground(scene)

    scene.item(gem.id, gem.name, on_use=place)
    scene.loc(LQ_LOC.CARVED_ROCK, ['Use'], tile=gem.rock, id=LQ_LOC_ID.GEM_ROCK)
    expect(run(trials.take_book_of_binding(scene.log))).to_be(True)


test('the seventh gem conjures the book', book_conjured_by_the_gems)


def book_failures():
    scene = world('gem_room')
    gem = GEM_ROCKS[0]
    scene.item(gem.id, gem.name)
    expect(run(trials.take_book_of_binding(scene.log))).to_be(False)

    # All placed and no book.
    scene = world('gem_room')
    expect(run(trials.take_book_of_binding(scene.log))).to_be(False)
    expect(scene.logged('the seven gems are placed but no book appeared')).to_be(True)

    scene = world('gem_room')
    book_on_ground(scene)
    scene.walk_ok = False
    expect(run(trials.take_book_of_binding(scene.log))).to_be(False)

    scene = world('gem_room')
    book_on_ground(scene, lambda op: False)
    expect(run(trials.take_book_of_binding(scene.log))).to_be(False)

    scene = world('gem_room')
    book_on_ground(scene, lambda op: True)
    expect(run(trials.take_book_of_binding(scene.log))).to_be(False)


test('the book fails at each of its steps', book_failures)


# The magic gate.

def magic_gate_scene(cast=None):
    scene = world('gem_room', LQ_TILE.MAGIC_GATE_SOUTH)
    scene.item(LQ_ID.UNPOWERED_ORB, 'Unpowered orb')
    scene.loc(LQ_LOC.ANCIENT_GATE, ['Open'], id=LQ_LOC_ID.MAGIC_GATE)
    spy_on(game, 'cast_on_loc', impl=cast if cast is not None else (lambda spell, gate: True))
    return scene


def magic_gate():
    scene = magic_gate_scene()
    casts = []

    def cast(spell, gate):
        casts.append(spell)
        scene.pocket = 'winch_room'
        return True

    spy_on(game, 'cast_on_loc', impl=cast)
    expect(run(trials.cast_magic_gate(scene.log))).to_be(True)
    expect(casts).to_equal([trials.ORB_SPELLS[0]])

    scene = world('winch_room')
    expect(run(trials.cast_magic_gate(scene.log))).to_be(True)


test('a charge-orb spell at the gate blows the player through', magic_gate)


def magic_gate_tries_each_spell():
    scene = magic_gate_scene()
    casts = []

    def cast(spell, gate):
        casts.append(spell)
        if spell == trials.ORB_SPELLS[0]:
            return False
        if spell == trials.ORB_SPELLS[-1]:
            scene.pocket = 'winch_room'
        return True

    spy_on(game, 'cast_on_loc', impl=cast)
    expect(run(trials.cast_magic_gate(scene.log))).to_be(True)
    expect(casts).to_equal(trials.ORB_SPELLS)


test('a spell not known, or one that moves nothing, moves on to the next', magic_gate_tries_each_spell)


def magic_gate_failures():
    scene = world('gem_room')
    expect(run(trials.cast_magic_gate(scene.log))).to_be(False)
    expect(scene.logged('no unpowered orb')).to_be(True)

    scene = magic_gate_scene()
    scene.at = Tile(LQ_TILE.MAGIC_GATE_SOUTH.x + 9, LQ_TILE.MAGIC_GATE_SOUTH.z, 0)
    scene.walk_ok = False
    expect(run(trials.cast_magic_gate(scene.log))).to_be(False)

    scene = magic_gate_scene()
    scene.locs = []
    expect(run(trials.cast_magic_gate(scene.log))).to_be(False)
    expect(scene.logged('no ancient gate in range')).to_be(True)

    scene = magic_gate_scene()
    expect(run(trials.cast_magic_gate(scene.log))).to_be(False)
    expect(scene.logged('no charge-orb spell moved the magic gate')).to_be(True)


test('the magic gate fails with no orb, no way there, no gate, or no spell that works', magic_gate_failures)


def falling_back():
    scene = world('gem_room')
    expect(run(trials.fall_through_magic_gate(scene.log))).to_be(True)
    expect(scene.loc_ops).to_have_length(0)

    scene = world('winch_room')
    scene.loc_op_effect = enters(scene, 'gem_room')
    expect(run(trials.fall_through_magic_gate(scene.log))).to_be(True)

    scene = world('winch_room')
    expect(run(trials.fall_through_magic_gate(scene.log))).to_be(False)


test('from the north the gate pulls the player back', falling_back)


# The winch.

def winch_scene():
    return world('winch_room', LQ_TILE.WINCH)


def rope_loc(scene):
    scene.loc(LQ_LOC.WINCH, ['Climb-down'], id=LQ_LOC_ID.WINCH_ROPE)


def winch_rope_held():
    scene = winch_scene()
    scene.loc_op_effect = enters(scene, 'viyeldi_ledge')
    scene.loc(LQ_LOC.WINCH, ['Use'], id=LQ_LOC_ID.WINCH_NO_ROPE)
    scene.item(LQ_ID.ROPE, 'Rope', on_use=lambda target: rope_loc(scene))
    expect(run(trials.climb_down_winch(scene.log))).to_be(True)
    expect(scene.loc_ops).to_equal([(LQ_LOC.WINCH, 'Climb-down')])


test('the rope is tied on and climbed in one pass', winch_rope_held)


def winch_beams():
    scene = winch_scene()
    scene.loc_op_effect = enters(scene, 'viyeldi_ledge')
    scene.loc('Beams', ['Search'], id=LQ_LOC_ID.WINCH_NO_ROPE, effect=lambda op: rope_loc(scene))
    expect(run(trials.climb_down_winch(scene.log))).to_be(True)


test('a rope tied before is handed back by the beams', winch_beams)


def winch_already_down():
    scene = world('viyeldi_ledge')
    expect(run(trials.climb_down_winch(scene.log))).to_be(True)
    expect(scene.walks).to_have_length(0)

    # Down during the settle: the loop's first look sees it.
    scene = winch_scene()
    scene.later(enters(scene, 'viyeldi_ledge'))
    expect(run(trials.climb_down_winch(scene.log))).to_be(True)


test('already below the winch, there is nothing to do', winch_already_down)


def winch_failures():
    scene = world('winch_room', Tile(LQ_TILE.WINCH.x + 9, LQ_TILE.WINCH.z, 0))
    scene.walk_ok = False
    expect(run(trials.climb_down_winch(scene.log))).to_be(False)

    # Neither rope nor beams.
    scene = winch_scene()
    expect(run(trials.climb_down_winch(scene.log))).to_be(False)
    expect(scene.logged('the winch will not hold a rope')).to_be(True)
    expect(scene.logged('six goes at the winch')).to_be(True)

    # Roped, and the climb never lands.
    scene = winch_scene()
    rope_loc(scene)
    expect(run(trials.climb_down_winch(scene.log))).to_be(False)
    expect(scene.logged('six goes at the winch')).to_be(True)


test('the winch fails with no way there, no rope, or no climb', winch_failures)


def climbing_up():
    scene = world('winch_room')
    expect(run(trials.climb_up_rope(scene.log))).to_be(True)
    expect(scene.loc_ops).to_have_length(0)

    scene = world('viyeldi_ledge')
    scene.loc_op_effect = enters(scene, 'winch_room')
    expect(run(trials.climb_up_rope(scene.log))).to_be(True)

    scene = world('viyeldi_ledge')
    expect(run(trials.climb_up_rope(scene.log))).to_be(False)


test('the rope climbs back up', climbing_up)


# The whole descent and ascent.

def fine(*args, **kwargs):
    return True
    yield


def broken(*args, **kwargs):
    return False
    yield


DESCENT_LEGS = ['leave_octagram', 'open_outer_gate', 'mine_boulder', 'open_inner_gate', 'jump_jagged_wall', 'cross_marked_wall']


def patch_all(names, value):
    for name in names:
        patch(trials, name, value)


def descent_chain():
    scene = world('winch_room')
    expect(run(trials.descend_to_gem_room(scene.log))).to_be(True)
    expect(run(trials.descend_to_winch(scene.log))).to_be(True)

    scene = world()
    patch_all(DESCENT_LEGS, fine)
    expect(run(trials.descend_to_gem_room(scene.log))).to_be(True)

    for broken_leg in DESCENT_LEGS:
        scene = world()
        patch_all(DESCENT_LEGS, fine)
        patch(trials, broken_leg, broken)
        expect(run(trials.descend_to_gem_room(scene.log))).to_be(False)

    scene = world()
    patch_all(DESCENT_LEGS, fine)
    patch(trials, 'cast_magic_gate', fine)
    expect(run(trials.descend_to_winch(scene.log))).to_be(True)

    scene = world()
    patch_all(DESCENT_LEGS, broken)
    patch(trials, 'cast_magic_gate', fine)
    expect(run(trials.descend_to_winch(scene.log))).to_be(False)


test('the descent is an ordered chain that stops at its first failure', descent_chain)


ASCENT_LEGS = ['climb_up_rope', 'fall_through_magic_gate', 'cross_marked_wall', 'jump_jagged_wall', 'open_inner_gate', 'mine_boulder', 'leave_outer_gate', 'crawl_back_from_crevice']


def ascent():
    for pocket in [None, 'shaman_cave', 'octagram']:
        scene = world(pocket)
        expect(run(trials.climb_out_of_trials(scene.log))).to_be(True)

    # A real walk from the bottom: each leg lands in the next pocket up.
    scene = world('viyeldi_ledge')
    path = {'climb_up_rope': 'winch_room', 'fall_through_magic_gate': 'gem_room', 'cross_marked_wall': 'wall_room', 'jump_jagged_wall': 'trials', 'open_inner_gate': 'inner_gate', 'leave_outer_gate': 'crevice'}
    for name, pocket in path.items():
        patch(trials, name, up_to(scene, pocket))
    patch(trials, 'mine_boulder', mine_up(scene))
    patch(trials, 'crawl_back_from_crevice', up_to(scene, 'shaman_cave'))
    expect(run(trials.climb_out_of_trials(scene.log))).to_be(True)
    expect(scene.pocket).to_be('shaman_cave')


def up_to(scene, pocket):
    def leg(*args):
        scene.pocket = pocket
        return True
        yield
    return leg


def mine_up(scene):
    def leg(boulder, reverse, log):
        scene.pocket = boulder.from_
        return True
        yield
    return leg


test('the ascent climbs out from wherever the player is', ascent)


def ascent_failures():
    starts = [('viyeldi_ledge', 'climb_up_rope'), ('winch_room', 'fall_through_magic_gate'), ('gem_room', 'cross_marked_wall'), ('wall_room', 'jump_jagged_wall'), ('trials', 'open_inner_gate'), ('inner_gate', 'mine_boulder'), ('outer_gate', 'leave_outer_gate'), ('crevice', 'crawl_back_from_crevice')]
    for pocket, leg in starts:
        scene = world(pocket)
        patch(trials, leg, broken)
        expect(run(trials.climb_out_of_trials(scene.log))).to_be(False)


test('the ascent stops at the first leg that fails', ascent_failures)


def cave_mouth():
    jungle = LQ_TILE.CAVE_EXIT_LANDING
    scene = Scene(jungle)
    expect(run(trials.leave_shaman_cave(scene.log))).to_be(True)
    expect(scene.walks).to_have_length(0)

    scene = Scene(LQ_TILE.CAVE_EXIT)

    def out(name, op):
        scene.at = jungle

    scene.loc_op_effect = out
    expect(run(trials.leave_shaman_cave(scene.log))).to_be(True)

    scene = Scene(LQ_TILE.CAVE_EXIT)
    scene.loc(LQ_LOC.CAVE_ENTRANCE, ['Walk through'])
    expect(run(trials.leave_shaman_cave(scene.log))).to_be(False)
    expect(scene.logged("in range")).to_be(True)

    scene = Scene(LQ_TILE.CAVE_EXIT)
    expect(run(trials.leave_shaman_cave(scene.log))).to_be(False)
    expect(scene.logged("not in range")).to_be(True)


test('the cave mouth lets the player out, or says what it could see', cave_mouth)


def steps_out(scene, outside):
    def effect(name, op):
        scene.at = outside
    return effect


def octagram():
    inside = LQ_TILE.OCTAGRAM_INSIDE
    outside = LQ_TILE.SHAMAN_BOOKCASE
    scene = Scene(outside)
    expect(run(trials.leave_octagram(scene.log))).to_be(True)
    expect(scene.loc_ops).to_have_length(0)

    # A blessed bowl crosses the flames.
    scene = Scene(inside)
    scene.loc(LQ_LOC.FIRE_WALL, ['Touch'])

    def splash(target):
        scene.at = outside

    scene.item(LQ_ID.GOLD_BOWL_BLESSED_PURE, 'Golden bowl', on_use=splash)
    # The stand is inside the octagram, so the walk does not move the player out.
    expect(run(trials.leave_octagram(scene.log))).to_be(True)
    expect(scene.loc_ops).to_have_length(0)

    # With no bowl, Touch; and that burns unless the demon is dead.
    scene = Scene(inside)
    scene.loc_op_effect = steps_out(scene, outside)
    expect(run(trials.leave_octagram(scene.log))).to_be(True)

    scene = Scene(inside)
    expect(run(trials.leave_octagram(scene.log))).to_be(False)

    # A bowl that doesn't work falls back to Touch.
    scene = Scene(inside)
    scene.loc_op_effect = steps_out(scene, outside)
    scene.item(LQ_ID.GOLD_BOWL_BLESSED_PURE, 'Golden bowl')
    scene.loc(LQ_LOC.FIRE_WALL, ['Touch'])
    expect(run(trials.leave_octagram(scene.log))).to_be(True)
    expect(scene.loc_ops).to_have_length(1)


test('the octagram is left by the bowl, or by Touch', octagram)
