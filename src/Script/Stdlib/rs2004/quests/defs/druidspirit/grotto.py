"""Ported from rs2b0t's src/bot/api/ai/quests/defs/druidspirit/grotto.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.dialogue import chat_dialog
from rs2004.entities import locs, npcs
from rs2004.game import game, skills
from rs2004.items import inventory
from rs2004.quests.defs.druidspirit.areas import FILLIMAN, NATURE_SPIRIT, NS_ID, NS_LOC, NS_TILE, in_grotto
from rs2004.quests.exec.primitives import drive_dialog, talk_through
from rs2004.quests.exec.prompts import drive_until, held_id, settle_scene
from rs2004.traversal import traversal

__all__ = ['enter_grotto', 'leave_grotto', 'talk_in_grotto', 'bless_sickle', 'recharge_prayer', 'exit_after_quest']


def inside():
    return in_grotto(game.tile())


def grotto_spirit():
    """Whichever form of Filliman is in the grotto."""
    if npcs.query().name(NATURE_SPIRIT.npc).within(12).nearest():
        return Record({'name': NATURE_SPIRIT.npc})
    if npcs.query().name(FILLIMAN.npc).within(12).nearest():
        return Record({'name': FILLIMAN.npc})
    return None


# Why: the walker has no route into the grotto; `Enter` teleports you, and past the ritual stage that's all the op does.
def enter_grotto(log):
    if inside():
        return True
    _w1 = yield from traversal.walk_resilient(NS_TILE.GROTTO_DOOR, radius=2, attempts=4, timeout_ms=300000, log=log)
    if not (_w1):
        return False
    yield from settle_scene()
    door = locs.query().name(NS_LOC.GROTTO_DOOR).action('Enter').within(8).nearest()
    if not door:
        log('no grotto door in the scene')
        return False
    if not (door.interact('Enter')):
        return False
    _result2 = yield from execution.delay_until(inside, 15000)
    return _result2


def leave_grotto(log):
    if not inside():
        return True
    yield from settle_scene()
    door = locs.query().name(NS_LOC.GROTTO_DOOR).action('Exit').within(16).nearest()
    if not door:
        log('no grotto exit in the scene')
        return False
    if not (door.interact('Exit')):
        return False
    _result3 = yield from execution.delay_until(lambda: not inside(), 15000)
    return _result3


# Why: searching the grotto pool npc_adds the spirit and he despawns on a timer, so an empty grotto means search.
def talk_in_grotto(prefer, log):
    """Talk to the spirit inside the grotto, summoning it if it has gone."""
    _w4 = yield from enter_grotto(log)
    if not (_w4):
        return False
    yield from settle_scene()
    present = grotto_spirit()
    if present:
        _result5 = yield from talk_through(present.name, prefer, log)
        return _result5
    pool = locs.query().name(NS_LOC.GROTTO_POOL).action('Search').within(16).nearest()
    if not pool:
        log('no grotto pool to search for the spirit')
        return False
    if not (pool.interact('Search')):
        return False
    yield from execution.delay_until(lambda: grotto_spirit() is not None or chat_dialog.is_open() or chat_dialog.can_continue(), 8000)
    _result6 = yield from drive_dialog(prefer, log)
    return _result6


# Why: a lost blessed sickle is replaced by dipping a plain one in the grotto water, which is an `oplocu` with no op of its own.
def bless_sickle(log):
    """Dip a plain silver sickle in the grotto pool."""
    if held_id(NS_ID.SICKLE_BLESSED) > 0:
        return True
    _w7 = yield from enter_grotto(log)
    if not (_w7):
        return False
    yield from settle_scene()
    _v8 = locs.query().name(NS_LOC.ALTAR).within(16).nearest()
    pool = (_v8 if _v8 is not None else locs.query().name(NS_LOC.GROTTO_POOL).action('Search').within(16).nearest())
    sickle = ([i for i in inventory.items() if i.id == NS_ID.SICKLE] or [None])[0]
    if not pool or not sickle:
        log('no grotto pool in reach, or no plain sickle to dip')
        return False
    if not (sickle.use_on(pool)):
        return False
    _result9 = yield from drive_until(lambda: held_id(NS_ID.SICKLE_BLESSED) > 0, [], log)
    return _result9


# Why: the grotto's Altar of nature is on level 1 at (3441,9740) and the door only teleports there after the quest, so mid-quest there is no altar below the camp (quest-pitfalls-6).
def recharge_prayer(log):
    """Top the prayer bar up at Paterdomus, the temple this quest already walks through."""
    full = skills.level('prayer')
    if skills.effective('prayer') >= full:
        return True
    # The grotto is a scripted pocket, so the walker needs the door before it has a route anywhere.
    _c10 = inside()
    if _c10:
        _w11 = yield from leave_grotto(log)
        _c10 = not (_w11)
    if _c10:
        return False
    _w12 = yield from traversal.walk_resilient(NS_TILE.TEMPLE_ALTAR, radius=2, attempts=4, timeout_ms=300000, log=log)
    if not (_w12):
        return False
    yield from settle_scene()
    altar = locs.query().name(NS_LOC.TEMPLE_ALTAR).action('Pray-at').within(8).nearest()
    if not altar:
        log(f'no altar within 8 tiles of ({NS_TILE.TEMPLE_ALTAR.x},{NS_TILE.TEMPLE_ALTAR.z}) to pray at')
        return False
    before = skills.effective('prayer')
    if not (altar.interact('Pray-at')):
        return False
    _result13 = yield from execution.delay_until(lambda: skills.effective('prayer') > before, 6000)
    return _result13


def exit_after_quest(log):
    """The quest ends inside the pocket; the retreat to a bank has to start outside it."""
    _result14 = yield from leave_grotto(log)
    return _result14
