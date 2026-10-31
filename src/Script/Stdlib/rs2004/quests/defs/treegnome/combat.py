"""Ported from rs2b0t's src/bot/api/ai/quests/defs/treegnome/combat.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import chat_dialog
from rs2004.entities import npcs
from rs2004.execution import event_signal
from rs2004.game import game, skills
from rs2004.quests.defs.treegnome.areas import TG_ITEM, TG_TILE
from rs2004.quests.exec.prompts import held_id, settle_scene
from rs2004.tabs import prayer
from rs2004.traversal import traversal

__all__ = ['kill_the_warlord', 'clear_commander']

WARLORD_ID = 477
COMMANDER_ID = 478
PROTECT_MELEE = 'protect from melee'
PROTECT_LEVEL = 43
EAT_AT_MISSING = 15
SEARCH_RADIUS = 16
REPORT_TICKS = 40


def hungry():
    max_ = skills.level('hitpoints')
    return max_ > 0 and skills.effective('hitpoints') <= max_ - EAT_AT_MISSING


def target(npc_id, radius):
    return npcs.query().where(lambda n: n.id == npc_id).action('Attack').where(lambda n: not n.targets_another_player()).within(radius).nearest()


def drain_dialogue():
    for i in range(30):
        if chat_dialog.can_continue():
            yield from chat_dialog.continue_()
            yield from execution.delay_ticks(1)
            continue
        if not chat_dialog.is_open():
            return
        yield from execution.delay_ticks(1)


def drop_prayer():
    if prayer.active(PROTECT_MELEE):
        yield from prayer.set(PROTECT_MELEE, False)


# Why: the server decodes 1 player op per tick and drops the rest, so a pass that prays, eats and swings loses 2 of the 3.
def fight_until_won(fight, log):
    can_pray = skills.level('prayer') >= PROTECT_LEVEL
    if not can_pray:
        log(f'prayer below {PROTECT_LEVEL} — {fight.what} will land every hit this fight')
    game.set_auto_retaliate(True)
    last_tick = -1
    reported = -1
    swings = 0
    attacking = -1
    for i in range(fight.guard):
        if fight.won():
            log(f'{fight.what}: down after {swings} attacks')
            yield from drain_dialogue()
            return True
        if event_signal.pending():
            log(f'{fight.what}: yielding to a random event')
            return False
        now = game.tick()
        if now == last_tick:
            yield from execution.delay_ticks(1)
            continue
        last_tick = now
        if chat_dialog.is_open() or chat_dialog.can_continue():
            yield from drain_dialogue()
            continue
        if can_pray and prayer.points() > 0 and not prayer.active(PROTECT_MELEE):
            yield from prayer.set(PROTECT_MELEE, True)
            continue
        if hungry():
            yield from sustain.run()
            continue
        npc = target(fight.npc_id, fight.radius)
        if not npc:
            attacking = -1
            yield from execution.delay_ticks(2)
            continue
        if now - reported >= REPORT_TICKS:
            reported = now
            log(f"{fight.what}: hp={skills.effective('hitpoints')}/{skills.level('hitpoints')}" + f' prayer={prayer.points()} attacks={swings}')
        # Why: melee keeps swinging on its own, so re-clicking the same target spends the tick's one action on re-targeting.
        if npc.index == attacking and game.in_combat():
            yield from execution.delay_ticks(1)
            continue
        if npc.interact('Attack'):
            attacking = npc.index
            swings += 1
        yield from execution.delay_ticks(1)
    log(f'{fight.what}: gave up after {fight.guard} ticks ({swings} attacks)')
    return False


# Why: left on, Protect from Melee burns the bar flat over the walk to the next fight; the loop re-arms in a tick if this one isn't over.
def melee_fight(fight, log):
    try:
        won = yield from fight_until_won(fight, log)
    except Exception as e:
        yield from drop_prayer()
        raise e
    yield from drop_prayer()
    return won


WARLORD_GUARD = 1500
COMMANDER_GUARD = 200


def kill_the_warlord(log):
    """`defeat_warlord` hands the orbs over on his death, so the pack is the oracle."""
    if held_id(TG_ITEM.ORBS.id) > 0:
        return True
    _w1 = yield from traversal.walk_resilient(TG_TILE.WARLORD, radius=4, attempts=3, timeout_ms=240000, log=log)
    if not (_w1):
        return False
    yield from settle_scene()
    _result2 = yield from melee_fight(Record({
        'what': 'Khazard warlord',
        'npc_id': WARLORD_ID,
        'radius': SEARCH_RADIUS,
        'guard': WARLORD_GUARD,
        'won': lambda: held_id(TG_ITEM.ORBS.id) > 0,
    }), log)
    return _result2


# Why: opening the chest and climbing the wall both run `~npc_retaliate`, and a commander swinging at the bot walks it off every stand the leg depends on.
def clear_commander(log):
    if target(COMMANDER_ID, 6) is None:
        return True
    log('a Khazard commander is in the way — clearing it')
    _result3 = yield from melee_fight(Record({
        'what': 'Khazard commander',
        'npc_id': COMMANDER_ID,
        'radius': 6,
        'guard': COMMANDER_GUARD,
        'won': lambda: target(COMMANDER_ID, 6) is None,
    }), log)
    return _result3
