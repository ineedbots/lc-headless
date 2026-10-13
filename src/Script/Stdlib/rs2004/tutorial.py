"""Leaving Tutorial Island. A new account starts there, where the walker finds no route anywhere. The
RuneScape Guide asks a player who has just designed their character whether to skip the tutorial, on a server
that isn't live; "Yes please." sends them to Lumbridge with the starter kit.

The runtime calls skip() before on_start when the player is on the island.
"""

import _core
from rs2004 import execution
from rs2004.dialogue import chat_dialog
from rs2004.entities import npcs
from rs2004.game import game

__all__ = ['on_tutorial_island']

GUIDE = 'RuneScape Guide'
SKIP_OPTION = 'Yes please'
# A design the server allows: a male with the first of each body kit, in the first colours.
DESIGN_KITS = [0, 10, 18, 26, 33, 36, 42]
DESIGN_COLOURS = [0, 0, 0, 0, 0]
# The design screen opens as the player is placed, sometimes a tick or two after.
DESIGN_WAIT_MS = 1800
DESIGN_CLOSE_MS = 5000
TALK_ATTEMPTS = 3
# Walking to the guide comes first.
TALK_OPEN_MS = 10000
DIALOGUE_STEPS = 25
LEAVE_MS = 10000


def in_tutorial_area(x, z):
    """Whether the tile is on the island or in its mine and dungeon below, as the server's in_tutorial_island
    has them, on any level."""
    if 3053 <= x and x <= 3156 and 3056 <= z and z <= 3136:
        return True
    return 3072 <= x and x <= 3118 and 9492 <= z and z <= 9535


def on_tutorial_island():
    return _core.is_placed() and in_tutorial_area(_core.get_x(), _core.get_z())


def offers_skip(options):
    """Whether the guide's options include skipping, matched by part without regard to case, as
    choose_option matches."""
    wanted = SKIP_OPTION.lower()
    for option in options:
        if wanted in option.lower():
            return True
    return False


def _finish_design(say):
    """Saves a design when the design screen is open; the server lets the guide offer the skip after one."""
    yield from execution.delay_until(lambda: game.appearance_screen_open(), DESIGN_WAIT_MS)
    if not game.appearance_screen_open():
        return
    say('tutorial: saving a character design')
    game.set_appearance(False, DESIGN_KITS, DESIGN_COLOURS)
    yield from execution.delay_until(lambda: not game.appearance_screen_open(), DESIGN_CLOSE_MS)


def _talk(say):
    """Talks to the guide and answers him. 'skipped', 'refused' when he talked without offering the skip,
    or 'failed'."""
    guide = npcs.query().name(GUIDE).nearest()
    if guide is None:
        say(f"tutorial: can't see the {GUIDE}")
        return 'failed'
    if not guide.interact('Talk-to'):
        return 'failed'
    opened = yield from execution.delay_until(lambda: chat_dialog.is_open(), TALK_OPEN_MS)
    if not opened:
        return 'failed'
    for i in range(DIALOGUE_STEPS):
        if not chat_dialog.is_open():
            break
        options = chat_dialog.options()
        if options:
            if not offers_skip(options):
                return 'refused'
            yield from chat_dialog.choose_option(SKIP_OPTION)
            return 'skipped'
        if chat_dialog.can_continue():
            yield from chat_dialog.continue_()
        else:
            yield from execution.delay_ticks(1)
    return 'refused'


def skip(say):
    """Gets off the island by the guide's skip. Use with yield from; True once the player has left."""
    say('tutorial: on Tutorial Island; asking the RuneScape Guide to skip it')
    yield from _finish_design(say)
    for attempt in range(TALK_ATTEMPTS):
        outcome = yield from _talk(say)
        if outcome == 'refused':
            break
        if outcome != 'skipped':
            continue
        left = yield from execution.delay_until(lambda: not on_tutorial_island(), LEAVE_MS)
        if left:
            say('tutorial: skipped')
            return True
    say(f"tutorial: the {GUIDE} didn't offer to skip the tutorial; still on the island")
    return False
