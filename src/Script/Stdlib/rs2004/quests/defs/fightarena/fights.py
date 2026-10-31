"""Ported from rs2b0t's src/bot/api/ai/quests/defs/fightarena/fights.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import chat_dialog
from rs2004.entities import npcs
from rs2004.execution import event_signal
from rs2004.game import game, skills
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.quests.defs.fightarena.areas import FA_NPC, pocket_of
from rs2004.quests.strike_combat import ARENA_COVER, at_cover, cast_from_cover, cast_strike, ready_strikes, take_strike_cover
from rs2004.tabs import prayer
from rs2004.traversal import traversal

__all__ = ['FA_FIGHT', 'PROTECT_MELEE', 'PROTECT_LEVEL', 'fight_won', 'run_fight']

# Why: running out mid-fight hands the tick back to the engine, which reads the journal, and that opens a main modal on top of a boss.
# Why: the budgets are generous for that reason; a stalled fight is the watchdog's problem.
FA_FIGHT = Record({
    'ogre': Record({'what': 'Khazard Ogre', 'npc_id': FA_NPC.OGRE, 'guard': 600}),
    'scorpion': Record({'what': 'Khazard Scorpion', 'npc_id': FA_NPC.SCORPION, 'guard': 600}),
    'bouncer': Record({'what': 'Bouncer', 'npc_id': FA_NPC.BOUNCER, 'guard': 1500}),
})
PROTECT_MELEE = 'protect from melee'
PROTECT_LEVEL = 43
SEARCH_RADIUS = 20
MISSING_TO_WIN = 3
# Why: the arena scorpion hunts within 2 tiles and its straight chase stops at the cover rock, so live it sat 8 tiles
# off the lane for every lure; Protect from Melee holds each beast's hits at nothing, which makes the open field safe.
LURES_BEFORE_OPEN_FIELD = 2
OPEN_FIELD_RANGE = 6


# Why: an empty scene before the first swing means the server hasn't released the beast yet.
def fight_won(swings, missing_ticks):
    """True once the target has been gone long enough to be dead."""
    return swings > 0 and missing_ticks >= MISSING_TO_WIN


def target(npc_id):
    return npcs.query().where(lambda n: n.id == npc_id).action('Attack').where(lambda n: not n.targets_another_player()).within(SEARCH_RADIUS).nearest()


# Why: Victory dialogue releases the next target or advances the stage, so drain it before returning.
def drain_win_dialogue():
    """Drain whatever the win opened, without answering an option."""
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


# Why: the server decodes 1 player op per tick and drops the rest, so a pass that eats, prays and swings loses 2 of the 3, and the one it loses is the food.
def run_fight(fight, log):
    """Run one arena fight to its win."""
    try:
        outcome = yield from fight_rounds(fight, log)
    except Exception as e:
        if not game.in_combat():
            yield from drop_prayer()
        raise e
    if not game.in_combat():
        yield from drop_prayer()
    return outcome


def fight_rounds(fight, log):
    can_pray = skills.level('prayer') >= PROTECT_LEVEL
    cover = (fight.cover if fight.cover is not None else ARENA_COVER)
    initial = target(fight.npc_id)
    if not fight.cover and initial and pocket_of(initial.network_tile()) != 'arena':
        return 'unengaged'
    _w2 = yield from ready_strikes(log)
    _c1 = not (_w2)
    if not _c1:
        _w3 = yield from take_strike_cover(cover, log, ((lambda: target(fight.npc_id)) if not fight.cover and not at_cover(cover) else None))
        _c1 = not (_w3)
    if _c1:
        return 'stuck'
    last_tick = -1
    reported = -1
    swings = 0
    missing = 0
    lures = 0
    open_field = False
    for i in range(fight.guard):
        if event_signal.pending():
            log(f'{fight.what}: yielding to a random event')
            return 'stuck'
        now = game.tick()
        if now == last_tick:
            yield from execution.delay_ticks(1)
            continue
        last_tick = now
        if chat_dialog.is_open() or chat_dialog.can_continue():
            yield from drain_win_dialogue()
            continue
        if can_pray and prayer.points() > 0 and not prayer.active(PROTECT_MELEE):
            yield from prayer.set(PROTECT_MELEE, True)
            continue
        food_before = len(inventory.items())
        yield from sustain.run()
        if len(inventory.items()) < food_before:
            yield from execution.delay_ticks(1)
            continue
        npc = target(fight.npc_id)
        if not npc:
            missing += 1
            if fight_won(swings, missing):
                log(f'{fight.what}: down after {swings} attacks')
                yield from drain_win_dialogue()
                yield from drop_prayer()
                return 'won'
            yield from execution.delay_ticks(1)
            continue
        missing = 0
        if now - reported >= 40:
            reported = now
            log(f"{fight.what}: hp={skills.effective('hitpoints')}/{skills.level('hitpoints')}" + f' prayer={prayer.points()} attacks={swings} at ({npc.tile().x},{npc.tile().z})')
        if open_field:
            here = game.tile()
            # Why: off the lane on purpose; Bouncer is two tiles wide, and beside the cover his origin falls outside it.
            if here is None or not cast_from_cover(here, npc, False):
                yield from traversal.walk_resilient(npc.tile(), radius=OPEN_FIELD_RANGE, attempts=1, timeout_ms=10000, log=log)
                continue
            _w6 = yield from cast_strike(here, npc, log, False)
            if _w6:
                swings += 1
            yield from execution.delay_ticks(1)
            continue
        if not at_cover(cover):
            yield from take_strike_cover(cover, log)
            return 'stuck'
        if not fight.cover and not cast_from_cover(cover, npc):
            def _fn4():
                current = target(fight.npc_id)
                return current is not None and cast_from_cover(cover, current)
            arrived = yield from execution.delay_until_ticks(_fn4, 12)
            if not arrived:
                lures += 1
                if lures > LURES_BEFORE_OPEN_FIELD:
                    log(f'{fight.what}: never came round the rock — casting in the open under Protect from Melee')
                    open_field = True
                    continue
                log(f'{fight.what}: luring back around the rock')
                yield from take_strike_cover(cover, log, lambda: target(fight.npc_id))
            continue
        _w5 = yield from cast_strike(cover, npc, log)
        if _w5:
            swings += 1
        else:
            log(f'{fight.what}: no cast landed from cover')
            return 'stuck'
        yield from execution.delay_ticks(1)
    log(f'{fight.what}: gave up after {fight.guard} ticks ({swings} attacks)')
    return 'stuck'
