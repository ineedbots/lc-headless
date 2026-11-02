"""Ported from rs2b0t's src/bot/api/ai/quests/defs/legends/trials.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.catalogs.tasks import sustain
from rs2004.entities import ground_items, locs
from rs2004.game import direct_navigator, game
from rs2004.messages import game_messages
from rs2004.quests.defs.legends.areas import GEM_ROCKS, LQ_ID, LQ_LOC, LQ_LOC_ID, LQ_TILE, WALL_RUNES, in_octagram, legends_area
from rs2004.quests.defs.legends.pockets import legends_pocket
from rs2004.quests.defs.legends.scene import clear_boxes, drive_boxes, drive_until, held_id, loc_near, modal_text, prompt_loc, said_any, settle_scene, use_on_loc
from rs2004.traversal import traversal

__all__ = ['pocket', 'crawl_bookcase', 'crawl_back_from_crevice', 'open_outer_gate', 'leave_outer_gate', 'open_inner_gate', 'jump_jagged_wall', 'cross_marked_wall', 'place_gems', 'take_book_of_binding', 'cast_magic_gate', 'fall_through_magic_gate', 'climb_down_winch', 'climb_up_rope', 'descend_to_gem_room', 'descend_to_winch', 'climb_out_of_trials', 'leave_shaman_cave', 'leave_octagram']

def pocket():
    """Which sealed pocket of the cave complex we are standing in."""
    return legends_pocket(game.tile())


# Why: every rung of the descent is a one-way crossing, so a leg resumed below one must not walk back at the stand above it.
DESCENT = [
    'shaman_cave',
    'crevice',
    'outer_gate',
    'boulder_one',
    'boulder_two',
    'inner_gate',
    'trials',
    'wall_room',
    'gem_room',
    'winch_room',
    'viyeldi_ledge',
]


def past(want):
    """Standing at or below the named rung of the descent."""
    at = pocket()
    return at is not None and (DESCENT.index(at) if at in DESCENT else -1) >= (DESCENT.index(want) if want in DESCENT else -1)


def loc_by_id(id, within=10, op=None):
    query = locs.query().where(lambda l: l.id == id).within(within)
    return ((query.action(op) if op else query)).nearest()


def either_leaf(left, right, op=None):
    """Whichever leaf of a double gate is in the scene, offering op when one is named."""
    leaf = loc_by_id(left, 6, op)
    return leaf if leaf is not None else loc_by_id(right, 6, op)


# Why: Neither gate is in `doors.json`; one refuses Open and the other uses a Strength prompt, so handle the crossing explicitly.
def step_through(to, want, log, quiet=False):
    """Walk the last tile through a gate the module has opened."""
    # Why: these gates teleport, and the teleport lands a tick or 2 after the box is clicked away: `~mesbox` suspends the script, so `if_close`, the anim and `open_and_close_double_door2` all come after the dismissal.
    # Why: The script places the player on the crossing tile; walking again moves away before the crossing completes.
    yield from settle_scene()
    if pocket() == want:
        return True
    yield from direct_navigator.walk_to(to, 0, 8000)
    yield from settle_scene()
    if pocket() == want:
        return True
    if not quiet:
        log(f'the gate did not let us through to {want}')
    return False


# Why: `stat_random(agility, 60, 254)` decides the crawl and a failure only costs a few ticks, so this retries.
def crawl_bookcase(log):
    """Squeeze through the crevice behind the shaman's bookcase."""
    if past('crevice'):
        return True
    _w1 = yield from traversal.walk_resilient(LQ_TILE.SHAMAN_BOOKCASE, radius=2, attempts=3, timeout_ms=120000, log=log)
    if not (_w1):
        return False
    yield from settle_scene()
    for i in range(6):
        if pocket() == 'crevice':
            yield from settle_scene()
            return True
        ok = yield from prompt_loc(Record({
            'name': LQ_LOC.BOOKCASE,
            'op': 'Search',
            'near': LQ_TILE.SHAMAN_BOOKCASE,
            'prefer': ['Yes please!'],
            'expect': lambda: pocket() == 'crevice',
            'expect_ms': 25000,
        }), log)
        if ok:
            yield from settle_scene()
            return True
    log('six squeezes and the crevice still would not take us')
    return False


def crawl_back_from_crevice(log):
    """Crawl back west through the crevice into the shaman cave."""
    if pocket() != 'crevice':
        return True
    ok = yield from prompt_loc(Record({
        'name': LQ_LOC.CREVICE,
        'op': 'Search',
        'near': LQ_TILE.SHAMAN_CREVICE,
        'prefer': ['Yes please!'],
        'expect': lambda: pocket() == 'shaman_cave',
        'expect_ms': 20000,
    }), log)
    if ok:
        yield from settle_scene()
    return ok


PICK_ATTEMPTS = 10
# Why: `stat_random(thieving, 0, 255)` decides the lock and `stat_random(strength, 0, 255)` the doors, and both leave you on the stand with the gate shut, so a miss is a re-click.
PICK_MISSED = 'fail to pick the lock'
FORCE_MISSED = 'run out of steam'


# Why: Only Search with a lockpick opens the outer gate; plain Open repeats the same refusal from the entrance side.
def open_outer_gate(log):
    """Pick the outer ancient gate and step through it."""
    if past('outer_gate'):
        return True
    _w2 = yield from crawl_bookcase(log)
    if not (_w2):
        return False
    if held_id(LQ_ID.LOCKPICK) == 0:
        log('no lockpick in the pack for the outer ancient gate')
        return False
    _w3 = yield from traversal.walk_resilient(LQ_TILE.LOCKPICK_GATE_NORTH, radius=0, attempts=4, timeout_ms=120000, log=log)
    if not (_w3):
        return False

    # Why: `search_outer_ancient_gate` is a 7-box chain and each box is gone the tick after the driver clicks it, so the open is read off the gate losing its Search op.
    # Why: `next_loc_stage` swaps the leaf to `inac_lglockpickgatebottom*`, a model with no name and no ops, so absence here means open.
    def shut():
        return either_leaf(LQ_LOC_ID.LOCKPICK_GATE_L, LQ_LOC_ID.LOCKPICK_GATE_R, 'Search') is not None

    for i in range(PICK_ATTEMPTS):
        yield from sustain.run()
        gate = either_leaf(LQ_LOC_ID.LOCKPICK_GATE_L, LQ_LOC_ID.LOCKPICK_GATE_R, 'Search')
        if gate and (gate.interact('Search')):
            yield from drive_boxes(lambda: not shut() or said_any(modal_text(), ['tumble the lock mechanism', PICK_MISSED]), 30000)
            # Why: read before the boxes go, since clearing them is what takes the text away.
            missed = PICK_MISSED in modal_text()
            yield from clear_boxes()
            # Why: a missed roll leaves the door shut and you where you were, so the next Search goes straight in; the crossing below can't land and the walk back is to a tile already underfoot.
            if missed:
                continue
        _w5 = yield from step_through(LQ_TILE.LOCKPICK_GATE_SOUTH, 'outer_gate', log, True)
        if _w5:
            return True
        yield from traversal.walk_resilient(LQ_TILE.LOCKPICK_GATE_NORTH, radius=0, attempts=2, timeout_ms=30000, log=log)
    log('ten lockpick attempts and the outer gate is still shut')
    return False


def outer_shut():
    return either_leaf(LQ_LOC_ID.LOCKPICK_GATE_L, LQ_LOC_ID.LOCKPICK_GATE_R, 'Open')


def outer_open():
    return either_leaf(LQ_LOC_ID.LOCKPICK_GATE_L_OPEN, LQ_LOC_ID.LOCKPICK_GATE_R_OPEN)


def leave_outer_gate(log):
    """Open the outer gate from the inside, where it needs no lockpick at all."""
    if pocket() != 'outer_gate':
        return True
    _w6 = yield from traversal.walk_resilient(LQ_TILE.LOCKPICK_GATE_SOUTH, radius=0, attempts=4, timeout_ms=60000, log=log)
    if not (_w6):
        return False
    # Why: the lever swings the doors shut again behind whoever pulled it, so one open and one step is a coin toss. The crossing is retried until it lands.
    last_click = 'never dispatched'
    last_box = ''
    for i in range(6):
        yield from sustain.run()
        gate = outer_shut()
        if gate:
            dispatched = gate.interact('Open')
            last_click = ('dispatched' if dispatched else 'refused')
            if dispatched:
                # Why: `open_outer_ancient_gate` raises a box and suspends on it, so the teleport only comes after it has been clicked away.
                yield from drive_boxes(lambda: modal_text() != '', 6000)
                # Why: read before clearing, since the box is the only thing that says which branch `check_axis` took; the push-on-the-doors message is the gate deciding we're outside trying to get in.
                last_box = modal_text()[0:120]
                yield from clear_boxes()
        elif not outer_open():
            # Why: neither stage in the scene means the walk landed somewhere the gate isn't, which retrying can't fix.
            log(f'no ancient gate in either stage within six tiles of ({LQ_TILE.LOCKPICK_GATE_SOUTH.x},{LQ_TILE.LOCKPICK_GATE_SOUTH.z})')
            return False
        _w7 = yield from step_through(LQ_TILE.LOCKPICK_GATE_NORTH, 'crevice', log, True)
        if _w7:
            return True
        yield from traversal.walk_resilient(LQ_TILE.LOCKPICK_GATE_SOUTH, radius=0, attempts=2, timeout_ms=30000, log=log)
    me = game.tile()
    log(f"six pulls and the outer gate would not let us back out — shut leaf {('present' if outer_shut() else 'absent')}, open leaf {('present' if outer_open() else 'absent')}, click {last_click}, stood at ({(me.x if me is not None else None)},{(me.z if me is not None else None)}), box \"{last_box}\"")
    return False


MINE_ATTEMPTS = 20
WINCH_ATTEMPTS = 6
BOULDERS = [
    Record({
    'id': LQ_LOC_ID.BOULDER_1,
    'from_': 'outer_gate',
    'north': LQ_TILE.BOULDER_1_NORTH,
    'to': 'boulder_one',
    'south': LQ_TILE.BOULDER_1_SOUTH,
}),
    Record({
    'id': LQ_LOC_ID.BOULDER_2,
    'from_': 'boulder_one',
    'north': LQ_TILE.BOULDER_1_SOUTH,
    'to': 'boulder_two',
    'south': LQ_TILE.BOULDER_2_SOUTH,
}),
    Record({
    'id': LQ_LOC_ID.BOULDER_3,
    'from_': 'boulder_two',
    'north': LQ_TILE.BOULDER_2_SOUTH,
    'to': 'inner_gate',
    'south': LQ_TILE.BOULDER_3_SOUTH,
}),
]
# Why: mining a boulder teleports you past it and drops another behind, so each of the 3 is a one-shot crossing re-mined from the other side to come back.
# Why: `stat_random(mining, 90, 255)` decides each swing and a failure costs a mining level, so the loop is generous.
# Why: a missed swing answers with the scratch line and changes nothing else, so waiting on the crossing alone spends the per-swing budget on every miss: 20 of those is 5 minutes per boulder.
SCRATCHED = 'only succeed in scratching the rock'


def mine_boulder(boulder, reverse, log):
    """Smash one trial boulder and land on the far side of it."""
    want = (boulder.from_ if reverse else boulder.to)
    stand = (boulder.south if reverse else boulder.north)
    if pocket() == want or (not reverse and past(want)):
        return True
    _w8 = yield from traversal.walk_resilient(stand, radius=0, attempts=4, timeout_ms=60000, log=log)
    if not (_w8):
        return False
    yield from settle_scene()
    for i in range(MINE_ATTEMPTS):
        if pocket() == want:
            yield from settle_scene()
            return True
        rock = loc_by_id(boulder.id, 6, 'Smash-to-bits')
        if not rock:
            log(f'boulder {boulder.id} is not in the scene from ({stand.x},{stand.z})')
            return False
        yield from sustain.run()
        mark = game_messages.mark()
        if not (rock.interact('Smash-to-bits')):
            continue
        yield from execution.delay_until(lambda: pocket() == want or game_messages.saw_since(mark, SCRATCHED), 15000)
    log(f'twenty swings and boulder {boulder.id} is still in the way')
    return False


STRENGTH_ATTEMPTS = 10


# Why: the inner gate rolls against strength on every push and drains a level on a miss, so the loop retries.
def open_inner_gate(reverse, log):
    """Force the inner ancient gate open and step through it."""
    want = ('inner_gate' if reverse else 'trials')
    stand = (LQ_TILE.STRENGTH_GATE_SOUTH if reverse else LQ_TILE.STRENGTH_GATE_NORTH)
    landing = (LQ_TILE.STRENGTH_GATE_NORTH if reverse else LQ_TILE.STRENGTH_GATE_SOUTH)
    if pocket() == want or (not reverse and past(want)):
        return True
    _w9 = yield from traversal.walk_resilient(stand, radius=0, attempts=4, timeout_ms=60000, log=log)
    if not (_w9):
        return False
    # Why: a forced gate keeps its Open op (that's how it shuts again) and the success box is gone the tick after the driver clicks it, so the crossing itself is the only oracle.
    for i in range(STRENGTH_ATTEMPTS):
        yield from sustain.run()
        gate = either_leaf(LQ_LOC_ID.STRENGTH_GATE_L, LQ_LOC_ID.STRENGTH_GATE_R, 'Open')
        if gate and (gate.interact('Open')):
            yield from drive_boxes(lambda: said_any(modal_text(), ['manage to force the doors open', FORCE_MISSED]), 25000, ["Yes, I'm very strong"])
            missed = FORCE_MISSED in modal_text()
            yield from clear_boxes()
            if missed:
                continue
        _w11 = yield from step_through(landing, want, log, True)
        if _w11:
            return True
        yield from traversal.walk_resilient(stand, radius=0, attempts=2, timeout_ms=30000, log=log)
    log('ten pushes and the inner gate has not budged')
    return False


JUMP_ATTEMPTS = 8


# Why: the jump is `stat_random(agility, 50, 200)`, which misses often at the quest's own requirement, so one attempt isn't a leg.
def jump_jagged_wall(reverse, log):
    """Jump the jagged wall between the trials corridor and the rune wall room."""
    want = ('trials' if reverse else 'wall_room')
    stand = (LQ_TILE.JAGGED_WALL_NORTH if reverse else LQ_TILE.JAGGED_WALL_SOUTH)
    if pocket() == want or (not reverse and past(want)):
        return True
    _w12 = yield from traversal.walk_resilient(stand, radius=0, attempts=4, timeout_ms=90000, log=log)
    if not (_w12):
        return False
    yield from settle_scene()
    for i in range(JUMP_ATTEMPTS):
        if pocket() == want:
            yield from settle_scene()
            return True
        wall = locs.query().name(LQ_LOC.JAGGED_WALL).action('Jump-over').within(6).nearest()
        if not wall:
            log('no jagged wall offering Jump-over from the stand')
            return False
        if not (wall.interact('Jump-over')):
            continue
        yield from execution.delay_until(lambda: pocket() == want, 15000)
        if pocket() != want:
            yield from traversal.walk_resilient(stand, radius=0, attempts=2, timeout_ms=30000, log=log)
    log('eight jumps and the jagged wall is still between us and the rune wall')
    return False


BURNED = 'burns red hot in your hand'


def slid(text):
    """A rune going in: "slide the ... into the ... depression"."""
    return 'slide the ' in text and ' depression' in text


# Why: the 5 depressions take soul, mind, earth, law and law in that order, and a rune offered out of turn burns and drops to the floor without saying which is next.
# Why: the message box is the only oracle for which depression was filled, so each rune is offered once and a burn moves on to the next.
def place_wall_runes(wall, want, log):
    """Feed the marked wall its 5 runes and walk into the gem room."""
    for rune in WALL_RUNES:
        if pocket() == want:
            return True
        if held_id(rune.id) == 0:
            log(f'no {rune.name} left for the marked wall')
            continue
        mark = game_messages.mark()
        yield from use_on_loc(rune.id, Record({'name': LQ_LOC.MARKED_WALL, 'near': wall, 'within': 6, 'id': LQ_LOC_ID.MARKED_WALL}), ["Yes, I'll go through!"], lambda: slid(modal_text()) or pocket() == want or game_messages.saw_since(mark, BURNED), log)
        yield from drive_until(lambda: pocket() == want, ["Yes, I'll go through!"], log, 8000)
        yield from clear_boxes()
    return pocket() == want


def cross_marked_wall(reverse, log):
    """Cross the marked wall in the named direction."""
    want = ('wall_room' if reverse else 'gem_room')
    stand = (LQ_TILE.MARKED_WALL_OUT if reverse else LQ_TILE.MARKED_WALL_IN)
    if pocket() == want or (not reverse and past(want)):
        return True
    _w13 = yield from traversal.walk_resilient(stand, radius=1, attempts=4, timeout_ms=90000, log=log)
    if not (_w13):
        return False
    yield from settle_scene()
    # Why: `[oploc1,lgancientwalldoor]` answers "You see no way to use that.... Perhaps you should search it?" until `^legends_law_rune_2_used` is set, which is invisible from here, so a Use tried first wastes its `expectMs`. A rune still in the pack is the proof the wall hasn't been fed, and feeding it opens the door.
    # Why: offering a spare rune to an already-fed wall is safe, `legends_wall_wrong_rune` jumps straight to `enter_marked_wall` once the fifth is in, so the rune is neither burned nor lost.
    if not reverse and any([held_id(rune.id) > 0 for rune in WALL_RUNES]):
        placed = yield from place_wall_runes(stand, want, log)
        if placed:
            yield from settle_scene()
        return placed
    # Why: once the fifth rune is in, both walls answer a plain Use, which is also the only way back.
    opened = yield from prompt_loc(Record({
        'name': LQ_LOC.MARKED_WALL,
        'op': 'Use',
        'near': stand,
        'within': 6,
        'id': LQ_LOC_ID.MARKED_WALL,
        'prefer': ["Yes, I'll go through!"],
        'expect': lambda: pocket() == want,
        'expect_ms': 15000,
    }), log)
    if opened:
        yield from settle_scene()
        return True
    if reverse:
        log('the marked wall will not open from the gem room')
        return False
    placed = yield from place_wall_runes(stand, want, log)
    if placed:
        yield from settle_scene()
    return placed


# Why: each gem answers only its own carved rock, and a gem already hovering there is refused without being consumed, so a resume re-offers every gem and lets the wall sort them out.
def place_gems(log):
    """Hover all 7 gems over their rocks, which conjures the Book of Binding."""
    for gem in GEM_ROCKS:
        if held_id(gem.id) == 0:
            continue
        # Why: both the placement and the refusal are `mes` game messages, so a gem already hovering is invisible to the modal text and the leg would wait out its budget on it.
        mark = game_messages.mark()
        placed = yield from use_on_loc(gem.id, Record({'name': LQ_LOC.CARVED_ROCK, 'near': gem.rock, 'within': 4, 'id': LQ_LOC_ID.GEM_ROCK}), [], lambda: held_id(gem.id) == 0 or game_messages.saw_since(mark, GEM_SETTLED), log)
        if not placed:
            log(f'the {gem.name} would not settle over its rock at ({gem.rock.x},{gem.rock.z})')
            return False
        yield from clear_boxes()
    return True


def GEM_SETTLED(text):
    return said_any(text.lower(), ['glows and starts spinning', 'already placed'])


BOOK_MS = 90000


def find_book():
    return ground_items.query().where(lambda item: item.id == LQ_ID.BOOK_OF_BINDING).within(20).nearest()


def take_book_of_binding(log):
    """Take the Book of Binding once the seventh gem has conjured it."""
    if held_id(LQ_ID.BOOK_OF_BINDING) > 0:
        return True
    _c14 = not find_book()
    if _c14:
        _w15 = yield from place_gems(log)
        _c14 = not (_w15)
    if _c14:
        return False
    # The conjuring is a 13-tick cutscene that blows you to the middle of the room.
    _w16 = yield from execution.delay_until(lambda: find_book() is not None, BOOK_MS)
    if not (_w16):
        log('the seven gems are placed but no book appeared')
        return False
    _w17 = yield from traversal.walk_resilient(LQ_TILE.BOOK_SPAWN, radius=2, attempts=3, timeout_ms=60000, log=log)
    if not (_w17):
        return False
    book = find_book()
    if not book or not (book.interact('Take')):
        return False
    _result18 = yield from execution.delay_until(lambda: held_id(LQ_ID.BOOK_OF_BINDING) > 0, 8000)
    return _result18


# Why: the magic gate takes any charge-orb spell with an unpowered orb in the pack, and the 4 differ only in level and element; water is the one this quest's magic requirement buys.
ORB_SPELLS = ['Charge water orb', 'Charge earth orb', 'Charge fire orb', 'Charge air orb']


def cast_magic_gate(log):
    """Cast a charge-orb spell at the magic gate and be blown into the winch room."""
    if past('winch_room'):
        return True
    if held_id(LQ_ID.UNPOWERED_ORB) == 0:
        log('no unpowered orb in the pack for the magic gate')
        return False
    _w19 = yield from traversal.walk_resilient(LQ_TILE.MAGIC_GATE_SOUTH, radius=1, attempts=4, timeout_ms=90000, log=log)
    if not (_w19):
        return False
    yield from settle_scene()
    for spell in ORB_SPELLS:
        gate = loc_by_id(LQ_LOC_ID.MAGIC_GATE, 8, 'Open')
        if not gate:
            log('no ancient gate in range of the magic trial stand')
            return False
        if not (game.cast_on_loc(spell, gate)):
            continue
        _w20 = yield from execution.delay_until(lambda: pocket() == 'winch_room', 20000)
        if _w20:
            yield from settle_scene()
            return True
    log('no charge-orb spell moved the magic gate — level, runes or orb short')
    return False


# Why: from the north the gate pulls anyone who touches it straight through for free, which is the return trip.
def fall_through_magic_gate(log):
    """Let the magic gate pull us back south into the gem room."""
    if pocket() == 'gem_room':
        return True
    ok = yield from prompt_loc(Record({
        'name': LQ_LOC.ANCIENT_GATE,
        'op': 'Open',
        'near': LQ_TILE.MAGIC_GATE_NORTH,
        'within': 8,
        'id': LQ_LOC_ID.MAGIC_GATE,
        'expect': lambda: pocket() == 'gem_room',
        'expect_ms': 20000,
    }), log)
    if ok:
        yield from settle_scene()
    return ok


def climb_down_winch(log):
    """Tie the rope to the winch and climb down into the Viyeldi caves."""
    if legends_pocket(game.tile()) == 'viyeldi_ledge':
        return True
    _w21 = yield from traversal.walk_resilient(LQ_TILE.WINCH, radius=3, attempts=4, timeout_ms=90000, log=log)
    if not (_w21):
        return False
    yield from settle_scene()

    def roped():
        return loc_by_id(LQ_LOC_ID.WINCH_ROPE, 8, 'Climb-down')

    # Why: the rope is thrown over for 30 ticks and then falls off again, so tying it and climbing it are one pass.
    # Why: the tie sets `legends_tied_rope_winch`, and from then on the beams hand the rope back to a Search.
    for i in range(WINCH_ATTEMPTS):
        if legends_pocket(game.tile()) == 'viyeldi_ledge':
            return True
        if not roped():
            beams = loc_by_id(LQ_LOC_ID.WINCH_NO_ROPE, 8, 'Search')
            if beams and (beams.interact('Search')):
                yield from execution.delay_until(lambda: roped() is not None, 6000)
        if not roped() and held_id(LQ_ID.ROPE) > 0:
            yield from use_on_loc(LQ_ID.ROPE, Record({'name': LQ_LOC.WINCH, 'near': LQ_TILE.WINCH, 'within': 8, 'id': LQ_LOC_ID.WINCH_NO_ROPE}), [], lambda: roped() is not None, log)
        if not roped():
            log('the winch will not hold a rope')
            yield from execution.delay_ticks(2)
            continue
        ok = yield from prompt_loc(Record({
            'name': LQ_LOC.WINCH,
            'op': 'Climb-down',
            'near': LQ_TILE.WINCH,
            'within': 8,
            'id': LQ_LOC_ID.WINCH_ROPE,
            'prefer': ["Yes, I'll shimmy down the rope"],
            'expect': lambda: legends_pocket(game.tile()) == 'viyeldi_ledge',
            'expect_ms': 25000,
        }), log)
        if ok:
            yield from settle_scene()
            return True
    log('six goes at the winch and the rope never took us down')
    return False


def climb_up_rope(log):
    """Climb the rope back out of the Viyeldi caves into the winch room."""
    if pocket() == 'winch_room':
        return True
    ok = yield from prompt_loc(Record({
        'name': LQ_LOC.CLIMB_ROPE,
        'op': 'Climb',
        'near': LQ_TILE.VIYELDI_LEDGE,
        'within': 6,
        'expect': lambda: pocket() == 'winch_room',
        'expect_ms': 20000,
    }), log)
    if ok:
        yield from settle_scene()
    return ok


# Why: the descent is 9 one-way scripted teleports, so the leg is an ordered chain and each rung is a no-op once behind us.
def descend_to_gem_room(log):
    """The trials descent as far as the gem room, where the Book of Binding is conjured."""
    if past('gem_room'):
        return True
    # Why: the flames are as solid to the pathfinder as they are to the player, so a descent that starts beside Ungadulu steps out of his octagram first.
    _w22 = yield from leave_octagram(log)
    if not (_w22):
        return False
    _w23 = yield from open_outer_gate(log)
    if not (_w23):
        return False
    for boulder in BOULDERS:
        _w24 = yield from mine_boulder(boulder, False, log)
        if not (_w24):
            return False
    _w25 = yield from open_inner_gate(False, log)
    if not (_w25):
        return False
    _w26 = yield from jump_jagged_wall(False, log)
    if not (_w26):
        return False
    _result27 = yield from cross_marked_wall(False, log)
    return _result27


# Why: the magic gate is the one-way crossing out of the gem room, so anything that still needs the gems has to stop short of it.
def descend_to_winch(log):
    """The trials descent, from the shaman cave to the winch."""
    if past('winch_room'):
        return True
    _w28 = yield from descend_to_gem_room(log)
    if not (_w28):
        return False
    _result29 = yield from cast_magic_gate(log)
    return _result29


def climb_out_of_trials(log):
    """The trials ascent, from the winch back to the shaman cave."""
    at = pocket()
    if at is None or at == 'shaman_cave' or at == 'octagram':
        return True
    _c30 = at == 'viyeldi_ledge'
    if _c30:
        _w31 = yield from climb_up_rope(log)
        _c30 = not (_w31)
    if _c30:
        return False
    _c32 = pocket() == 'winch_room'
    if _c32:
        _w33 = yield from fall_through_magic_gate(log)
        _c32 = not (_w33)
    if _c32:
        return False
    _c34 = pocket() == 'gem_room'
    if _c34:
        _w35 = yield from cross_marked_wall(True, log)
        _c34 = not (_w35)
    if _c34:
        return False
    _c36 = pocket() == 'wall_room'
    if _c36:
        _w37 = yield from jump_jagged_wall(True, log)
        _c36 = not (_w37)
    if _c36:
        return False
    _c38 = pocket() == 'trials'
    if _c38:
        _w39 = yield from open_inner_gate(True, log)
        _c38 = not (_w39)
    if _c38:
        return False
    for boulder in list(reversed(BOULDERS)):
        _c40 = pocket() == boulder.to
        if _c40:
            _w41 = yield from mine_boulder(boulder, True, log)
            _c40 = not (_w41)
        if _c40:
            return False
    _c42 = pocket() == 'outer_gate'
    if _c42:
        _w43 = yield from leave_outer_gate(log)
        _c42 = not (_w43)
    if _c42:
        return False
    _result44 = yield from crawl_back_from_crevice(log)
    return _result44


def leave_shaman_cave(log):
    """Walk back out of the cave mouth into the jungle."""
    if legends_area(game.tile()) != 'shaman_caves':
        return True
    # Why: the 2 mouth locs sit at (2772,9342) and (2773,9342) with cave wall around them and the op only lands from the tile below. `Reach` counts a couple of tiles short as arrived, and from (2774,9339) the server answers it can't be reached, which spends the retry budget in silence.
    yield from traversal.walk_resilient(LQ_TILE.CAVE_EXIT, radius=0, attempts=3, timeout_ms=60000, log=log)
    ok = yield from prompt_loc(Record({
        'name': LQ_LOC.CAVE_ENTRANCE,
        'op': 'Walk through',
        'near': LQ_TILE.CAVE_EXIT,
        'expect': lambda: legends_area(game.tile()) == 'jungle',
    }), log)
    if ok:
        yield from settle_scene()
    else:
        # Why: this is the last thing between the shaman cave and every errand above ground, so a failure says what it could see from where it stood.
        at = game.tile()
        door = loc_near(LQ_LOC.CAVE_ENTRANCE, 'Walk through', 8)
        log(f"the cave entrance would not let us out — stood at ({(at.x if at is not None else None)},{(at.z if at is not None else None)}), '{LQ_LOC.CAVE_ENTRANCE}' {('in range' if door else 'not in range')}")
    return ok


# Why: Touch only crosses once the demon is dead, before that `legends_touch_fire_wall` burns you for 4, and the bowl crosses either way, so a dose is spent when one is carried.
# Why: the bowl holds 10 doses, so spending one on the way out costs nothing the quest needs back.
def leave_octagram(log):
    """Step back out of the octagram."""
    if not in_octagram(game.tile()):
        return True
    if held_id(LQ_ID.GOLD_BOWL_BLESSED_PURE) > 0:
        splashed = yield from use_on_loc(LQ_ID.GOLD_BOWL_BLESSED_PURE, Record({'name': LQ_LOC.FIRE_WALL, 'near': LQ_TILE.OCTAGRAM_INSIDE, 'within': 6}), [], lambda: not in_octagram(game.tile()), log)
        if splashed:
            yield from settle_scene()
            return True
    ok = yield from prompt_loc(Record({
        'name': LQ_LOC.FIRE_WALL,
        'op': 'Touch',
        'near': LQ_TILE.OCTAGRAM_INSIDE,
        'within': 6,
        'expect': lambda: not in_octagram(game.tile()),
    }), log)
    if ok:
        yield from settle_scene()
    return ok
