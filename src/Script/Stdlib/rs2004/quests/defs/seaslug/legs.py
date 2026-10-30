"""Ported from rs2b0t's src/bot/api/ai/quests/defs/seaslug/legs.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.dialogue import chat_dialog
from rs2004.entities import locs
from rs2004.game import game
from rs2004.items import inventory
from rs2004.karamja_recovery import on_island
from rs2004.messages import game_messages
from rs2004.reach import reach
from rs2004.traversal import traversal
from rs2004.quests.exec.primitives import drive_dialog, goto_npc, talk_through
from rs2004.quests.exec.prompts import settle_scene
from rs2004.quests.defs.seaslug.areas import HOLGART_ISLAND, HOLGART_LAND, HOLGART_PLATFORM, KENT, SS_LOC, SS_OBJ, SS_TILE, on_island, on_platform
from rs2004.quests.engine.types import QuestModule, QuestProgress
from rs2004.quests.data import quest_record

__all__ = ['region_of', 'climb_to', 'sail_to', 'call_kennith', 'open_panel_and_call', 'rotate_crane', 'find_kent', 'rub_sticks']

WALK = Record({'radius': 1, 'attempts': 3, 'timeout_ms': 120000})
RUB_ATTEMPTS = 12


def panel_reply(text):
    lower = text.lower()
    return 'crumbles away' in lower or 'nothing interesting happens' in lower


def crane_reply(text):
    lower = text.lower()
    return 'rotate the crane around' in lower or 'get closer to use that' in lower


def sticks_reply(text):
    lower = text.lower()
    return 'catch alight' in lower or 'smoke momentarily' in lower or 'firemaking level of 30' in lower


def region_of(tile):
    if on_platform(tile):
        return 'platform'
    return ('island' if on_island(tile) else 'mainland')


def held_id(id):
    return sum([item.count for item in [item for item in inventory.items() if item.id == id]])


def climb_to(level, log):
    here = game.tile()
    if not here:
        return False
    if here.level == level:
        return True
    stand = (SS_TILE.LADDER_FOOT if level == 1 else SS_TILE.LADDER_TOP)
    op = ('Climb-up' if level == 1 else 'Climb-down')
    _merged1 = {}
    for _k, _v in (WALK._fields if isinstance(WALK, Record) else WALK).items():
        _merged1[_k] = _v
    for _k, _v in {'log': log}.items():
        _merged1[_k] = _v
    _w2 = yield from traversal.walk_resilient(stand, **_merged1)
    if not (_w2):
        return False
    ladder = locs.query().name('Ladder').action(op).within(4).nearest()
    if not ladder:
        log(f'seaslug: no Ladder offering \'{op}\' at ({stand.x},{stand.z},{stand.level})')
        return False
    mark = game_messages.mark()
    if not (ladder.interact(op)):
        return False
    climbed = yield from execution.delay_until(lambda: (game.tile().level if game.tile() is not None else None) == level, 12000)
    if not climbed and game_messages.saw_since(mark, 'fishing rod'):
        log('seaslug: the fishermen turned us back — the climb wants a lit torch from stage 6 on')
        return False
    if climbed:
        yield from settle_scene()
    return climbed


def board_from(region, log):
    _c3 = region == 'platform'
    if _c3:
        _w4 = yield from climb_to(0, log)
        _c3 = not (_w4)
    if _c3:
        return False
    stop = (HOLGART_ISLAND if region == 'island' else (HOLGART_PLATFORM if region == 'platform' else HOLGART_LAND))
    _w5 = yield from goto_npc(stop, [], log)
    if not (_w5):
        return False
    _w6 = yield from talk_through(stop.npc, stop.prefer, log)
    if not (_w6):
        return False
    _result7 = yield from execution.delay_until(lambda: region_of(game.tile()) != region, 20000)
    return _result7


def sail_to(target, log):
    for hop in range(3):
        here = region_of(game.tile())
        if here == target:
            return True
        log(f'seaslug: boarding at the {here} bound for the {target}')
        _w8 = yield from board_from(here, log)
        if not (_w8):
            return False
    return region_of(game.tile()) == target


def pick_loc(id, op, stand, what, expect, log):
    _w9 = yield from climb_to(1, log)
    if not (_w9):
        return False
    status = yield from reach.loc_op(what, op, stand, expect, within=6, id=id, log=log)
    if status == 'done':
        return True
    note = ('still closing in' if status == 'retry' else 'no route')
    log(f'seaslug: \'{op}\' on {what} (loc {id}) from ({stand.x},{stand.z},{stand.level}) — {note}')
    return False


def shout_across(log):
    spoke = yield from pick_loc(SS_LOC.CRATES, 'Shout-across', SS_TILE.CRATES_STAND, 'Crates', lambda: chat_dialog.is_open() or chat_dialog.can_continue(), log)
    if not spoke:
        return False
    _result10 = yield from drive_dialog([], log)
    return _result10


def call_kennith(log):
    _w11 = yield from sail_to('platform', log)
    if not (_w11):
        return False
    _result12 = yield from shout_across(log)
    return _result12


def open_panel_and_call(log):
    _w13 = yield from sail_to('platform', log)
    if not (_w13):
        return False
    mark = game_messages.mark()
    kicked = yield from pick_loc(SS_LOC.LOOSE_PANEL, 'Kick', SS_TILE.PANEL_STAND, 'Loose panel', lambda: game_messages.saw_since(mark, 'you kick the loose panel'), log)
    if not kicked:
        return False
    yield from execution.delay_until(lambda: game_messages.saw_since(mark, panel_reply), 12000)
    _result14 = yield from shout_across(log)
    return _result14


def rotate_crane(log):
    _w15 = yield from sail_to('platform', log)
    if not (_w15):
        return False
    mark = game_messages.mark()
    turned = yield from pick_loc(SS_LOC.CRANE, 'Rotate', SS_TILE.CRANE_STAND, 'Crane', lambda: game_messages.saw_since(mark, crane_reply), log)
    if not turned:
        return False
    lowered = yield from execution.delay_until(lambda: game_messages.saw_since(mark, 'lower kennith to the row boat'), 25000)
    if not lowered and game_messages.saw_since(mark, 'get closer to use that'):
        log(f'seaslug: the crane refused from ({(game.tile().x if game.tile() is not None else None)},{(game.tile().z if game.tile() is not None else None)}) — its stand has to be north of the 4x4 footprint')
    return lowered


def find_kent(log):
    _w16 = yield from sail_to('island', log)
    if not (_w16):
        return False
    _w17 = yield from goto_npc(KENT, [], log)
    if not (_w17):
        return False
    _result18 = yield from talk_through(KENT.npc, KENT.prefer, log)
    return _result18


def rub_sticks(log):
    for attempt in range(RUB_ATTEMPTS):
        sticks = ([item for item in inventory.items() if item.id == SS_OBJ.DRY_STICKS] or [None])[0]
        if not sticks:
            log('seaslug: no Dry sticks in the pack to rub')
            return False
        mark = game_messages.mark()
        if not (sticks.interact('Rub-together')):
            return False
        answered = yield from execution.delay_until(lambda: game_messages.saw_since(mark, sticks_reply), 8000)
        if game_messages.saw_since(mark, 'catch alight'):
            return True
        if game_messages.saw_since(mark, 'firemaking level of 30'):
            log('seaslug: Firemaking is under 30 — the sticks will never catch')
            return False
        if not answered:
            log('seaslug: the rub produced no message at all')
            return False
    log(f'seaslug: {RUB_ATTEMPTS} rubs and the sticks never caught')
    return held_id(SS_OBJ.TORCH_LIT) > 0
