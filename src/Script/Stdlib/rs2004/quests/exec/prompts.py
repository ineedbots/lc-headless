"""Answering what a loc or a door asks: rs2b0t's api/ai/quests/exec/prompts.ts (MIT, see thirdparty/rs2b0t). Each
takes a log function, which may be a bot's self.log."""

import _core
from rs2004 import execution
from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import chat_dialog, modals
from rs2004.entities import locs
from rs2004.items import inventory
from rs2004.messages import game_messages
from rs2004.quests.exec.primitives import pick_preferred
from rs2004.quests.prayer import prayer_upkeep
from rs2004.reach import reach
from rs2004.traversal import traversal

__all__ = [
    'held_id', 'loc_near', 'settle_scene', 'drive_choice', 'drive_until', 'drive_boxes', 'clear_boxes', 'DoorCrossing',
    'cross_teleport_door', 'LocPrompt', 'prompt_loc', 'use_on_loc',
]


def _quiet(_):
    pass


def held_id(id):
    """How many of the item id you carry, stacks counted."""
    return sum([item.count for item in inventory.items() if item.id == id])


def loc_near(name, op, within=12):
    """The nearest loc of that name offering op, within that many tiles, or None."""
    return locs.query().name(name).action(op).within(within).nearest()


def settle_scene():
    """Waits 2 ticks after a level or region change, as rs2b0t does: its loc queries come back empty for about a
    tick after one, so an empty scene proves nothing. Use with yield from."""
    yield from execution.delay_ticks(2)


def _box_up():
    return chat_dialog.is_open() or chat_dialog.can_continue() or modals.is_open()


# Why: loc prompts often list the refusal first ("I don't think so, it might animate and attack me!"), so an unmatched list stops here instead of falling through.
def drive_choice(prefer, log):
    """Like drive_dialog, but stops on an option list none of prefer matches. True once the dialogue closed. Use
    with yield from."""
    for _ in range(60):
        if chat_dialog.can_continue():
            yield from chat_dialog.continue_()
            yield from execution.delay_ticks(1)
            continue
        opts = chat_dialog.options()
        if len(opts) > 0:
            pick = pick_preferred(opts, prefer)
            if not pick:
                log(f"no preferred option in [{' | '.join(opts)}]")
                return False
            yield from chat_dialog.choose_option(pick)
            yield from execution.delay_ticks(2)
            continue
        if not chat_dialog.is_open():
            return True
        yield from execution.delay_ticks(1)
    return not chat_dialog.is_open()


# Why: a scripted chain has gaps with nothing open yet, and drive_choice returns at the first one.
# Why: drive_choice runs a chain to its end, so the goal is only tested between chains and a goal on one box's text never sees it. Want game_messages.saw_since here; transient box text wants drive_boxes.
def drive_until(expect, prefer, log, ms=30000):
    """Keeps answering prompts until expect() holds, or ms pass. Use with yield from."""
    deadline = _core.step_time() + ms
    while _core.step_time() < deadline:
        if expect():
            return True
        if chat_dialog.is_open() or chat_dialog.can_continue():
            driven = yield from drive_choice(prefer, log)
            if not driven:
                return expect()
        yield from prayer_upkeep()
        yield from execution.delay_ticks(1)
    return expect()


# Why: drive_choice only clicks the chat modal and a loc script's ~mesbox chain lands in the main one, so drive_until would never click it away.
# Why: the goal is tested before each dismissal so the box carrying the answer is still readable, and it eats between boxes since sustain is call-driven.
def drive_boxes(expect, ms, prefer=None, log=None):
    """Drives a message-box chain, in either the chat or the main modal, until expect() holds, clicking each box
    away as it comes. Use with yield from."""
    if prefer is None:
        prefer = []
    if log is None:
        log = _quiet
    deadline = _core.step_time() + ms
    while _core.step_time() < deadline:
        if expect():
            return True
        # Why: one click per pass, since drive_choice runs a chain to the end without re-testing the goal and a goal on the last box's text ("manage to force the doors open") gets clicked away unread.
        opts = chat_dialog.options()
        if len(opts) > 0:
            pick = pick_preferred(opts, prefer)
            # Why: a list nothing matches can't move, so waiting on it only burns the budget (Gujuo's 4 dead-end topics cost 2 minutes each).
            # Why: logged, because the option list is the only record of what the script wanted and the module didn't offer.
            if not pick:
                log(f"no preferred option in [{' | '.join(opts)}]")
                return expect()
            # Why: without this a wrong topic and a right topic that led nowhere look the same in the log.
            log(f"chose \"{pick}\" from [{' | '.join(opts)}]")
            yield from chat_dialog.choose_option(pick)
            yield from execution.delay_ticks(2)
            continue
        if chat_dialog.can_continue():
            yield from chat_dialog.continue_()
            yield from execution.delay_ticks(1)
            continue
        if modals.is_open():
            # Why: a modal root with no close button returns without changing anything, so a bare retry would spin without yielding a tick.
            closed = yield from modals.close()
            if not closed:
                yield from execution.delay_ticks(1)
            continue
        yield from sustain.run()
        yield from execution.delay_ticks(1)
    return expect()


# Why: ~mesbox can land in either widget, and the server script stays suspended until the box is clicked.
def clear_boxes(max_boxes=8):
    """Dismisses every standing message box in either widget. Use with yield from."""
    for _ in range(max_boxes):
        if chat_dialog.can_continue():
            yield from chat_dialog.continue_()
            yield from execution.delay_ticks(1)
            continue
        if modals.is_open():
            closed = yield from modals.close()
            if not closed:
                return
            continue
        return


class DoorCrossing:
    """A quest door whose Open teleports you through: its loc id, the tile to click from on the side you're
    leaving (stand), and is_far(), true once you're past it, testing one coordinate. prefer is the options to take
    when it raises a dialogue instead of opening; name and op the loc's when it isn't a Door offering Open;
    use_item the key's id for a door whose Open says it's locked; stand_radius how far off stand counts as there,
    0 for a door that tests your side by one axis."""

    def __init__(self, id, stand, is_far, log, prefer=None, name=None, op=None, use_item=None, stand_radius=None):
        self.id = id
        self.stand = stand
        self.is_far = is_far
        self.log = log
        self.prefer = prefer
        self.name = name
        self.op = op
        self.use_item = use_item
        # Why: ~check_axis reads your side off one coordinate, so an axis door is clicked from its own tile.
        self.stand_radius = stand_radius


# Why: open_and_close_door teleports in the click's own script run with at most one p_delay(1) between its two teleports, so a crossing lands within a couple of ticks or never.
DOOR_MS = 3000
# Why: the server runs the door's script a tick after the click, so the dialogue check needs a window.
DIALOG_MS = 2000
# Why: the Brimhaven crossings are reached from Varrock by ferry, and a 2-minute budget times out mid-ocean and reports the door as missing.
DOOR_WALK_MS = 300000


def _door_loc(door_id, name, op):
    # Why: ~door_open swings the loc onto a different tile and id once anyone opens it, and a sealed pocket has one door, so the actioned neighbour is it.
    loc = locs.query().action(op).within(4).where(lambda l: l.id == door_id).nearest()
    if loc is None:
        loc = locs.query().action(op).within(2).where(lambda l: l.name == name).nearest()
    return loc


# Why: ~open_and_close_door teleports you through and re-shuts in 3 ticks, so the far side is the only proof of a crossing and no door can be held open for a partner.
def cross_teleport_door(door):
    """Crosses a DoorCrossing. True once you're past it. Use with yield from."""
    is_far = door.is_far
    log = door.log
    if is_far():
        return True
    # Why: a leftover ~mesbox from the door's own challenge ("You hear the door being unbarred from inside.") swallows the next Open click silently.
    if modals.is_open():
        yield from modals.close()
    radius = door.stand_radius if door.stand_radius is not None else 1
    walked = yield from traversal.walk_resilient(door.stand, radius=radius, attempts=3, timeout_ms=DOOR_WALK_MS, log=log)
    if not walked:
        return False
    op = door.op if door.op is not None else 'Open'
    name = door.name if door.name is not None else 'Door'
    loc = _door_loc(door.id, name, op)
    if not loc:
        log(f"no {name.lower()} {door.id} offering '{op}' within four tiles of ({door.stand.x},{door.stand.z})")
        return False
    # Why: a crossing prints nothing (open_and_close_door is two teleports, a loc_change and a synth), so any game message after the click is a refusal. Marked before the click since the refusal can be its immediate answer.
    said = game_messages.mark()
    # Why: a key door's oploc1 answers "This <name> is locked" and only its oplocu opens, so the crossing is a use-item on the loc.
    if door.use_item is not None:
        key = None
        for item in inventory.items():
            if item.id == door.use_item:
                key = item
                break
        if not key:
            log(f'no key {door.use_item} in the pack for {name.lower()} {door.id}')
            return False
        if not key.use_on(loc):
            log(f'{name.lower()} {door.id} refused the key')
            return False
    elif not loc.interact(op):
        log(f'{name.lower()} {door.id} refused the {op} click')
        return False

    def refused():
        return len(game_messages.since(said)) > 0

    # Why: the door's script runs a tick after the click, so a check straight off interact sees nothing, and a door talks in either modal (challenge in chat, flavour in a box).
    # Why: a refusal ends the wait too, so a door that says no doesn't cost the full cap.
    yield from execution.delay_until(lambda: is_far() or _box_up() or refused(), DIALOG_MS)
    if not is_far() and _box_up():
        yield from drive_boxes(is_far, DIALOG_MS, list(door.prefer or []))
    yield from execution.delay_until(lambda: is_far() or refused(), DOOR_MS)
    if not is_far() and refused():
        # Why: a door that narrates its own crossing would otherwise be abandoned a tick early, and that costs a retry.
        yield from execution.delay_ticks(2)
    if not is_far():
        return False
    yield from settle_scene()
    return True


class LocPrompt:
    """A loc to act on and the prompt it raises: op the name loc near the near tile, then answer with prefer until
    expect() holds, within expect_ms. within is how far from near to look, id the loc's id when its name is
    shared with another in range, and refused a game message pattern the loc's script answers with when the op
    can't work yet."""

    def __init__(self, name, op, near, expect, prefer=None, expect_ms=None, within=None, id=None, refused=None):
        self.name = name
        self.op = op
        self.near = near
        self.expect = expect
        self.prefer = prefer
        self.expect_ms = expect_ms
        self.within = within
        self.id = id
        self.refused = refused


def prompt_loc(step, log):
    """Walks to a LocPrompt's loc, acts on it, and answers whatever it raised. Use with yield from."""
    if step.expect():
        return True

    # Why: a box counts as the loc answering, otherwise reach treats a talking loc as one that did nothing and re-sends the op to its cap.
    def answered_or_talking():
        return step.expect() or _box_up()

    within = step.within if step.within is not None else 10
    status = yield from reach.loc_op(step.name, step.op, step.near, answered_or_talking, within=within, id=step.id, refused=step.refused, log=log)
    if status != 'done':
        # Why: a loc that couldn't be clicked and a click that led nowhere want different fixes, so the log says which.
        log(f"prompt: '{step.op}' on '{step.name}' never reached the loc ({status})")
        return False
    expect_ms = step.expect_ms if step.expect_ms is not None else 20000
    answered = yield from drive_boxes(step.expect, expect_ms, step.prefer or [], log)
    # Why: a satisfied goal owns the screen: Tribal Totem's lock waits for its door panel, and clearing after a success shut that panel.
    # Why: a failure is cleared because its next step is a retry, and a retry can't click through a standing box.
    if not answered:
        log(f"prompt: '{step.op}' on '{step.name}' was sent and the goal never came")
        yield from clear_boxes()
    return answered


# Why: quest item chains run through oplocu, which no op-based step can express.
def use_on_loc(item_id, loc, prefer, expect, log):
    """Walks near a loc, uses the carried item_id on it, and answers whatever it raised until expect() holds. loc
    has a name and a near tile, and may have within (12 by default) and an id for when the name is shared: a
    Record({'name': ..., 'near': ...}) say. Use with yield from."""
    if expect():
        return True
    walked = yield from traversal.walk_resilient(loc.near, radius=2, attempts=3, timeout_ms=180000, log=log)
    if not walked:
        return False
    yield from settle_scene()
    # Why: quest areas have same-named locs a tile apart, and nearest picks the decoy.
    loc_id = loc.id
    within = loc.within if loc.within is not None else 12
    target = locs.query().name(loc.name).where(lambda l: loc_id is None or l.id == loc_id).within(within).nearest()
    item = None
    for entry in inventory.items():
        if entry.id == item_id:
            item = entry
            break
    if not target or not item:
        which = '' if loc_id is None else f' id {loc_id}'
        log(f"no '{loc.name}'{which} or no item {item_id} to use on it near ({loc.near.x},{loc.near.z})")
        return False
    if not item.use_on(target):
        return False
    result = yield from drive_until(expect, prefer, log)
    return result
