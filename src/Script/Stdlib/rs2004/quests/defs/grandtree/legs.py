"""Ported from rs2b0t's src/bot/api/ai/quests/defs/grandtree/legs.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.dialogue import chat_dialog
from rs2004.entities import locs, npcs
from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.quests.defs.grandtree.areas import ANITA, CHARLIE, FEMI, FOREMAN, GLOUGH, GT_HOPS, GT_LOC, GT_OBJ, GT_PILLARS, GT_ROOTS, GT_TILE, NARNODE, NARNODE_UNDER, PILOT, in_caves, in_stronghold
from rs2004.quests.exec.primitives import goto_npc, open_dialogue
from rs2004.quests.exec.prompts import drive_until, held_id, settle_scene, use_on_loc
from rs2004.traversal import traversal

__all__ = ['start_quest', 'jailed_by_glough', 'search_cupboard', 'foreman_order', 'fly_to_karamja', 'femi_cart', 'anita_key', 'descend_anita', 'open_chest', 'climb_to_pillars', 'descend_glough_tree', 'place_twig', 'reset_root_cursor', 'search_next_root', 'give_rock', 'leave_caves']

TALK_MS = 120000


def here():
    t = game.tile()
    return (Tile(t.x, t.z, t.level) if t else None)


# Why: several legs are one scripted chain that closes the dialogue, walks you, teleports you and only then speaks again; `driveDialog` gives up in the 1.5s gaps, so the goal ends these.
def talk_until(stop, expect, log, ms=None):
    """Talk, then keep answering whatever the chain raises until `expect` lands."""
    if ms is None:
        ms = TALK_MS
    if expect():
        return True
    _w1 = yield from goto_npc(stop, GT_HOPS, log)
    if not (_w1):
        return False
    _w2 = yield from open_dialogue(stop.npc, log)
    if not (_w2):
        return False
    _result3 = yield from drive_until(expect, stop.prefer, log, ms)
    return _result3


def loc_at(id, tile, within=4):
    return locs.query().where(lambda l: l.id == id and l.tile().level == tile.level and l.tile().distance_to(tile) <= 1).within(within).nearest()


# Why: the King walks you to his trapdoor, drops you into the foundations and climbs you back out inside one `opnpc`, so the bark sample landing is the end of the talk.
# Why: The underground King repeats the initial offer, so interrupted dialogue can resume there.
def start_quest(log):
    """Start the quest and come away with the bark sample and translation book."""
    under = Record({'npc': NARNODE_UNDER.npc, 'anchor': NARNODE_UNDER.anchor, 'leash': NARNODE_UNDER.leash, 'prefer': NARNODE.prefer})
    stop = (under if in_caves(here()) else NARNODE)
    _result5 = yield from talk_until(stop, lambda: held_id(GT_OBJ.BARK) > 0, log)
    return _result5


# Why: Glough calls the guards, marches you to a ladder and jails you at the top of the tree, then the King lets you out, one chain ending with a teleport 1 tile east of the cell.
# Why: an interrupted run resumes from inside the cell, where Charlie's own `apnpc1` runs the same chain from the middle.
# Why: a chain that broke after the teleport also leaves you 1 tile east of the cell, so this leg never short-circuits on the goal state.
# Why: a stage-70 pass that starts there walks back to Glough, who jails you again and runs the chain from the top.
def jailed_by_glough(log):
    """Confront Glough with his journal and get out of the cage."""

    def released():
        t = here()
        return t is not None and t.level == 3 and t.z == GT_TILE.jail.z and t.x > GT_TILE.jail.x and not chat_dialog.is_open() and not chat_dialog.can_continue()

    def in_cell():
        t = here()
        return t is not None and t.level == 3 and GT_TILE.jail.distance_to(t) == 0

    stop = (CHARLIE if in_cell() else GLOUGH)
    _w6 = yield from goto_npc(stop, GT_HOPS, log)
    if not (_w6):
        return False
    _w7 = yield from open_dialogue(stop.npc, log)
    if not (_w7):
        return False
    _result8 = yield from drive_until(released, stop.prefer, log, TALK_MS)
    return _result8


def search_cupboard(log):
    """Open Glough's cupboard and search it for his journal."""
    if held_id(GT_OBJ.JOURNAL) > 0:
        return True
    _w9 = yield from traversal.walk_resilient(GT_TILE.cupboard_stand, radius=1, attempts=3, timeout_ms=120000, log=log)
    if not (_w9):
        return False
    yield from settle_scene()
    cupboard = Tile(2476, 3465, 1)
    shut = loc_at(GT_LOC.CUPBOARD_SHUT, cupboard)
    if shut:
        log("opening the cupboard in Glough's house")
        if not (shut.interact('Open')):
            return False
        # Why: a loc that transforms keeps its shut id for a tick, so poll for the open half.
        yield from execution.delay_until(lambda: loc_at(GT_LOC.CUPBOARD_OPEN, cupboard) is not None, 6000)
    open = loc_at(GT_LOC.CUPBOARD_OPEN, cupboard)
    if not open:
        log(f'no open cupboard at ({cupboard.x},{cupboard.z}) — the Open never landed')
        return False
    if not (open.interact('Search')):
        return False
    _result10 = yield from drive_until(lambda: held_id(GT_OBJ.JOURNAL) > 0, [], log, 10000)
    return _result10


# Why: the foreman closes the dialogue, walks you 35 tiles across the yard and teleports you into his office before the first question, so the generic talk step abandons him mid-walk and the next pass drags you back to his spawn.
# Why: once moved, `[opnpc1,grandtree_foreman]` sees him inside the office zone and skips to the interrogation, so a Foreman already in the scene is talked to where he stands.
def foreman_order(log):
    """Answer the foreman's 3 questions about Glough and take the lumber order."""
    if held_id(GT_OBJ.LUMBER_ORDER) > 0:
        return True
    # Why: the gate swaps itself for an inviswall for 3 ticks after teleporting you through, so the client repaths off the landing tile and a 2-pass walk budget goes on the recovery.
    near = npcs.query().name(FOREMAN.npc).within(8).nearest()
    _c11 = not near
    if _c11:
        _w12 = yield from traversal.walk_resilient(FOREMAN.anchor, radius=4, attempts=5, timeout_ms=120000, log=log)
        _c11 = not (_w12)
    if _c11:
        return False
    _w13 = yield from open_dialogue(FOREMAN.npc, log)
    if not (_w13):
        return False
    _result14 = yield from drive_until(lambda: held_id(GT_OBJ.LUMBER_ORDER) > 0, FOREMAN.prefer, log, 180000)
    return _result14


def fly_to_karamja(log):
    """Take the King's glider out of the stronghold; it crash-lands in the Karamja jungle."""

    def landed():
        t = here()
        return t is not None and t.level == 0 and GT_TILE.karamja_crash.distance_to(t) <= 12

    _result15 = yield from talk_until(PILOT, landed, log, 60000)
    return _result15


# Why: at stage 90 the gate guards turn you away and Femi's food cart is the only way back in; she charges only on the 1000gp branch, which the pay option answers.
def femi_cart(log):
    """Ride Femi's cart back into the stronghold."""
    if in_stronghold(here()):
        return True
    # Why: this leg runs from the Karamja jungle to the gnome gate, 600 tiles, a log balance and a ship, which is more than `gotoNpc`'s 2 45s passes.
    _w16 = yield from traversal.walk_resilient(GT_TILE.femi, radius=3, attempts=6, timeout_ms=300000, log=log)
    if not (_w16):
        return False
    _result17 = yield from talk_until(FEMI, lambda: in_stronghold(here()), log, 60000)
    return _result17


def anita_key(log):
    """Climb to Anita's first floor and take Glough's chest key from her."""
    if held_id(GT_OBJ.KEY) > 0:
        return True

    def upstairs():
        t = here()
        return t is not None and t.level == 1 and GT_TILE.anita_floor.distance_to(t) <= 6

    if not upstairs():
        # Why: this staircase has no baked edge, so the leg owns both directions of it.
        _w18 = yield from traversal.walk_resilient(GT_TILE.anita_stairs, radius=1, attempts=3, timeout_ms=120000, log=log)
        if not (_w18):
            return False
        yield from settle_scene()
        stairs = locs.query().name('Staircase').action('Climb-up').within(4).nearest()
        if not stairs or not (stairs.interact('Climb-up')):
            log(f'no staircase up to Anita at ({GT_TILE.anita_stairs.x},{GT_TILE.anita_stairs.z})')
            return False
        _w19 = yield from execution.delay_until(upstairs, 8000)
        if not (_w19):
            return False
        yield from settle_scene()
    _w20 = yield from talk_until(ANITA, lambda: held_id(GT_OBJ.KEY) > 0, log, 60000)
    if not (_w20):
        return False
    _result21 = yield from descend_anita(log)
    return _result21


def on_ground_floor():
    t = here()
    return t is not None and t.level == 0


def descend_anita(log):
    """Anita's floor is a 13-tile pocket, so the key leg owns the way down too."""
    t = here()
    if not t or t.level != 1 or GT_TILE.anita_floor.distance_to(t) > 6:
        return True
    _w22 = yield from traversal.walk_resilient(GT_TILE.anita_floor, radius=1, attempts=3, timeout_ms=60000, log=log)
    if not (_w22):
        return False
    stairs = locs.query().name('Staircase').action('Climb-down').within(4).nearest()
    if not stairs or not (stairs.interact('Climb-down')):
        log("no staircase down from Anita's floor")
        return False
    _result23 = yield from execution.delay_until(on_ground_floor, 8000)
    return _result23


def open_chest(log):
    """Unlock Glough's chest with Anita's key and take the invasion plans."""
    _result24 = yield from use_on_loc(GT_OBJ.KEY, Record({'name': 'Closed chest', 'near': GT_TILE.chest_stand, 'id': GT_LOC.CHEST_SHUT, 'within': 4}), [], lambda: held_id(GT_OBJ.INVASION_PLANS) > 0, log)
    return _result24


# Why: `grandtree_climbtree` is an Agility 25 climb with no baked edge, so both it and the tree back down belong to the legs that use the pillar floor.
def climb_to_pillars(log):
    """Climb from Glough's first floor to the pillar floor."""

    def upstairs():
        t = here()
        return t is not None and t.level == 2 and GT_TILE.pillar_floor.distance_to(t) <= 6

    if upstairs():
        return True
    _w25 = yield from traversal.walk_resilient(GT_TILE.climb_tree_stand, radius=1, attempts=3, timeout_ms=120000, log=log)
    if not (_w25):
        return False
    yield from settle_scene()
    tree = locs.query().where(lambda l: l.id == GT_LOC.CLIMB_TREE).action('Climb-up').within(4).nearest()
    if not tree or not (tree.interact('Climb-up')):
        log(f'no climbable tree at ({GT_TILE.climb_tree_stand.x},{GT_TILE.climb_tree_stand.z})')
        return False
    _w26 = yield from execution.delay_until(upstairs, 10000)
    if not (_w26):
        return False
    yield from settle_scene()
    return True


def below_pillar_floor():
    t = here()
    return t is not None and t.level < 2


# Why: the pillar floor is a 7-tile pocket whose only ways off are the tree down and the trapdoor, neither baked, so a bank step decided up here has no route and burns its budget proving it.
def descend_glough_tree(log):
    """Climb out of Glough's tree to the ground floor."""
    t = here()
    if not t or t.level == 0:
        return True
    if t.level >= 2:
        _w27 = yield from traversal.walk_resilient(GT_TILE.down_tree_stand, radius=1, attempts=3, timeout_ms=60000, log=log)
        if not (_w27):
            return False
        yield from settle_scene()
        tree = locs.query().where(lambda l: l.id == GT_LOC.DOWN_TREE).action('Climb-down').within(4).nearest()
        if not tree or not (tree.interact('Climb-down')):
            log(f'no tree down from the pillar floor at ({GT_TILE.down_tree_stand.x},{GT_TILE.down_tree_stand.z})')
            return False
        _w28 = yield from execution.delay_until(below_pillar_floor, 10000)
        if not (_w28):
            return False
        yield from settle_scene()
    # Glough's own ladder is baked, so the last leg down is an ordinary walk.
    _result29 = yield from traversal.walk_resilient(GT_TILE.glough_house_foot, radius=2, attempts=3, timeout_ms=90000, log=log)
    return _result29


def place_twig(index):
    """Lay each twig on the pillar the trapdoor's own `obj_find` checks for it."""
    pillar = GT_PILLARS[index]

    def lay(log):
        twig = pillar.obj
        climbed = yield from climb_to_pillars(log)
        if not climbed:
            return False
        laid = yield from use_on_loc(twig, Record({'name': 'Pillar', 'near': pillar.stand, 'id': pillar.loc, 'within': 4}), [], lambda: held_id(twig) == 0, log)
        return laid
    return lay


# Why: the roots are searched in a fixed order, so a resumed run walks the shortest remaining leg with no re-roll.
root_cursor = 0


def reset_root_cursor():
    """Test hook; the search order is module state so the sweep survives a re-decide."""
    global root_cursor
    root_cursor = 0


# Why: 14 of the 15 roots answer "You search the root but don't find anything", which is a search that worked, so it isn't reported as a failed step.
def search_next_root(log):
    """Search one root for the Daconia rock."""
    global root_cursor
    if held_id(GT_OBJ.DACONIA) > 0:
        return True
    index = root_cursor % len(GT_ROOTS)
    root = GT_ROOTS[index]
    root_cursor += 1
    _w33 = yield from traversal.walk_resilient(root.stand, radius=1, attempts=3, timeout_ms=120000, log=log)
    if not (_w33):
        return False
    yield from settle_scene()
    # Why: both root models render "Root" and the closest pair stands 3 tiles apart, so match on placement.
    loc = locs.query().name('Root').action('Search').where(lambda l: l.tile().distance_to(root.sw) <= 1).within(6).nearest()
    if not loc:
        log(f'no Root at ({root.sw.x},{root.sw.z})')
        return False
    if not (loc.interact('Search')):
        return False
    found = yield from drive_until(lambda: held_id(GT_OBJ.DACONIA) > 0, [], log, 6000)
    log(f"root {index + 1}/{len(GT_ROOTS)} at ({root.sw.x},{root.sw.z}): {('the Daconia rock' if found else 'nothing')}")
    return True


def give_rock(log):
    """Hand the rock over; the King's reward queue ends the quest."""
    given = yield from talk_until(NARNODE_UNDER, lambda: held_id(GT_OBJ.DACONIA) == 0, log, 60000)
    return given


def leave_caves(log):
    """Climb out of the root caves so the finished quest can walk to a bank."""
    if not in_caves(here()):
        return True
    _w34 = yield from traversal.walk_resilient(GT_TILE.cave_ladder, radius=1, attempts=3, timeout_ms=120000, log=log)
    if not (_w34):
        return False
    ladder = locs.query().name('Ladder').action('Climb-up').within(4).nearest()
    if not ladder or not (ladder.interact('Climb-up')):
        log(f'no ladder out of the caves at ({GT_TILE.cave_ladder.x},{GT_TILE.cave_ladder.z})')
        return False
    _result35 = yield from execution.delay_until(lambda: not in_caves(here()), 10000)
    return _result35
