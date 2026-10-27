"""Ported from rs2b0t's src/bot/api/ai/quests/defs/shieldofarrav/hideout.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.defs.shieldofarrav.areas import SOA_LOC, SOA_TILE, in_black_arm_inner, in_black_arm_upper, in_phoenix_hq, in_phoenix_inner, in_store_ground, in_weapon_store
from rs2004.quests.exec.prompts import cross_teleport_door, settle_scene
from rs2004.quests.exec.legs import climb, open_container, walk_and_talk
from rs2004.game import game
from rs2004.messages import game_messages
from rs2004.reach import reach

__all__ = ['enter_hideout', 'talk_in_hideout', 'leave_hideout', 'enter_phoenix_inner', 'enter_black_arm_upper', 'leave_black_arm_upper', 'leave_weapon_store']

# Why: the generic legs live in exec/ so a second partner quest can use them; the hideout keeps only the Shield of Arrav pockets they point at.
# Why: `isFar` is a component test; the two sides of a 1-tile wall are 2 tiles apart.
def cross_door(id, stand, is_far, log):
    """A hideout door teleports you through, so landing on the far side is the only proof."""
    mark = game_messages.mark()
    crossed = yield from cross_teleport_door(Record({'id': id, 'stand': stand, 'is_far': lambda: is_far(game.tile()), 'log': log}))
    if not crossed:
        for line in game_messages.since(mark):
            log(f'door {id}: {line.text}')
    return crossed


def enter_hideout(log):
    if in_phoenix_hq(game.tile()):
        return True
    # Why: Reach owns the approach: it walks, opens the building's door and retries on one budget, where a pre-walk plus its own walk spends 2 and wedges for minutes.
    # Why: 2 attempts, because the first from outside the building often lands on the wrong side of that door and a retry here is cheaper than a quest-engine round trip.
    status = 'retry'
    attempt = 0
    while attempt < 2 and not in_phoenix_hq(game.tile()):
        status = yield from reach.loc_op('Ladder', 'Climb-down', SOA_TILE.CELLAR_LADDER, lambda: in_phoenix_hq(game.tile()), id=SOA_LOC.CELLAR_LADDER, expect_ms=15000, log=log)
        yield from settle_scene()
        attempt += 1
    # Why: Reach reports 'retry' on a climb that landed, so where you're standing settles it.
    if in_phoenix_hq(game.tile()):
        return True
    log(f'descent into the hideout returned \'{status}\' and left the character on the surface')
    return False


def talk_in_hideout(stop, prefer, log):
    """Reach an NPC that lives inside the hideout, entering it first."""
    _w1 = yield from enter_hideout(log)
    if not (_w1):
        return False
    _result2 = yield from walk_and_talk(stop, prefer, log)
    return _result2


def leave_hideout(log):
    if not in_phoenix_hq(game.tile()):
        return True
    # Why: the chest sits behind the gang door, which is the pocket's only crossing in either direction.
    _c3 = in_phoenix_inner(game.tile())
    if _c3:
        _w4 = yield from cross_door(SOA_LOC.PHOENIX_DOOR, SOA_TILE.PHOENIX_DOOR_INNER, lambda t: in_phoenix_hq(t) and not in_phoenix_inner(t), log)
        _c3 = not (_w4)
    if _c3:
        return False
    status = yield from reach.loc_op('Ladder', 'Climb-up', SOA_TILE.HQ_LADDER, lambda: not in_phoenix_hq(game.tile()), id=SOA_LOC.HQ_LADDER, expect_ms=15000, log=log)
    yield from settle_scene()
    if not in_phoenix_hq(game.tile()):
        return True
    log(f'climb out of the hideout returned \'{status}\' and left the character underground')
    return False


def enter_phoenix_inner(log):
    """Through the gang door into the half of the hideout the chest is in."""
    _w5 = yield from enter_hideout(log)
    if not (_w5):
        return False
    _result6 = yield from cross_door(SOA_LOC.PHOENIX_DOOR, SOA_TILE.PHOENIX_DOOR, in_phoenix_inner, log)
    return _result6


def enter_black_arm_inner(log):
    """Through the gang door only. The stairs are a leg further on."""
    if in_black_arm_inner(game.tile()) or in_black_arm_upper(game.tile()):
        return True
    _result7 = yield from cross_door(SOA_LOC.BLACKARM_DOOR, SOA_TILE.BLACKARM_DOOR, in_black_arm_inner, log)
    return _result7


def enter_black_arm_upper(log):
    if in_black_arm_upper(game.tile()):
        return True
    _w8 = yield from enter_black_arm_inner(log)
    if not (_w8):
        return False
    _result9 = yield from climb(SOA_LOC.BLACKARM_STAIRS, 'Climb-up', SOA_TILE.BLACKARM_STAIRS, SOA_TILE.BLACKARM_STAIRS_TOP, log)
    return _result9


def leave_black_arm_upper(log):
    _c10 = in_black_arm_upper(game.tile())
    if _c10:
        _w11 = yield from climb(SOA_LOC.BLACKARM_STAIRS_TOP, 'Climb-down', SOA_TILE.BLACKARM_STAIRS_TOP, SOA_TILE.BLACKARM_STAIRS, log)
        _c10 = not (_w11)
    if _c10:
        return False
    # Why: the gang door seals the stairs pocket and is out of the nav graph, so climbing down alone strands you with the half and every route out reads unreachable.
    if not in_black_arm_inner(game.tile()):
        return True
    _result12 = yield from cross_door(SOA_LOC.BLACKARM_DOOR, SOA_TILE.BLACKARM_DOOR_INNER, lambda t: t is not None and t.level == 0 and not in_black_arm_inner(t), log)
    return _result12


def leave_weapon_store(log):
    _c13 = in_weapon_store(game.tile())
    if _c13:
        _w14 = yield from climb(SOA_LOC.STORE_LADDER_TOP, 'Climb-down', SOA_TILE.STORE_LADDER_TOP, SOA_TILE.STORE_LADDER, log)
        _c13 = not (_w14)
    if _c13:
        return False
    # Why: the store door seals the 10-tile ground floor and is out of the nav graph, so climbing down alone strands you with the crossbows.
    # Why: `unlock_weaponstore_door` lets a leaver through on op1, so no key is needed on the way out.
    if not in_store_ground(game.tile()):
        return True
    _result15 = yield from cross_door(SOA_LOC.STORE_DOOR, SOA_TILE.STORE_DOOR_INNER, lambda t: t is not None and t.level == 0 and not in_store_ground(t), log)
    return _result15
