"""Ported from rs2b0t's src/bot/api/ai/quests/defs/fremenniktrials/warrior.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.execution import event_signal
from rs2004.game import game, skills
from rs2004.quests.defs.fremenniktrials.areas import FT_LOC, FT_TILE, PEER, THORVALD, in_battleground
from rs2004.quests.defs.fremenniktrials.seer import PEER_BANK
from rs2004.quests.defs.fremenniktrials.supplies import walk_to
from rs2004.quests.defs.trollstronghold.combat import attackable
from rs2004.quests.engine.types import has_flag
from rs2004.quests.exec.prompts import settle_scene
from rs2004.quests.prayer import prayer_upkeep
from rs2004.reach import reach
from rs2004.tabs import prayer

__all__ = ['warrior_step', 'leave_loft_step', 'on_loft', 'PROTECT_MELEE_LEVEL', 'PROVEN_PRAYER']

KOSCHEI = 'Koschei the deathless'


# Why: `viking_honour_death` passes the trial on the blow that would have killed you.
# Why: Koschei's 4th form has 255 hitpoints and 255 defence against a strength of 5, so the fight ends in your death.
def warrior_step(snap):
    """Thorvald's trial: fight Koschei bare-handed until he wins."""
    if has_flag(snap.progress, 'warrior-done'):
        return None
    if not has_flag(snap.progress, 'warrior-started'):
        return Record({'kind': 'talk', 'stop': THORVALD(['Yes'])})
    if in_battleground(snap.tile):
        return Record({'kind': 'custom', 'name': 'fight Koschei to the death', 'run': fight_koschei})
    # Why: the ladder refuses anyone carrying armour, a weapon, runes, logs, arrows or a clue, and Peer's spell is the nearest bank.
    if len(snap.inv) > 0 or len(snap.worn) > 0:
        return Record({'kind': 'talk', 'stop': PEER(PEER_BANK)})
    return Record({'kind': 'custom', 'name': "climb down to Thorvald's battleground", 'run': enter_battleground})


# Why: the honourable death drops you on Thorvald's loft, which the walker has no baked edge off, so every route out reads unreachable until this ladder is climbed.
def on_loft(here):
    """Where `viking_honour_death` teleports the character, and the only exit that means the trial passed."""
    return not not here and here.level == 1 and FT_TILE.WARRIOR_LOFT.distance_to(here) <= 6


def leave_loft_step(snap):
    """The climb down from the loft, whatever the quest is doing next."""
    if not on_loft(snap.tile):
        return None
    return Record({'kind': 'custom', 'name': 'climb down from the loft', 'run': leave_loft})


def enter_battleground(log):
    status = yield from reach.loc_op('Ladder', 'Climb-down', FT_TILE.WARRIOR_LADDER, lambda: in_battleground(game.tile()), id=FT_LOC.WARRIOR_LADDER, expect_ms=15000, log=log)
    return status == 'done'


FIGHT_GUARD = 3000
PROTECT_MELEE = 'protect from melee'
PROTECT_MELEE_LEVEL = 43
# Why: the prayer burns a point every 5 ticks, the three forms have 150 hitpoints to punch through and no potion may come in, so Prayer 43 runs dry in the second form, and the overshoot is an ordinary death. rs2b0t's recipe proved it at 70.
PROVEN_PRAYER = 70


# Why: only the 4th form is wired to `viking_honour_death`; the first 3 kill an unarmed character outright, even at 70 stats.
# Why: Protect from Melee carries those 3 without costing the trial; `playerhit_n_melee_viking` zeroes damage while it holds, and the lethal blow lands once prayer drains on the 4th form.
# Why: the shared `fight` helper spends every damaged tick calling `Sustain` for food this trial forbids carrying, and stops swinging while it does.
def fight_koschei(log):
    """Beat Koschei's first 3 forms under prayer, then let the 4th win."""
    log('unarmed against Koschei — three forms to beat, then the fourth passes the trial by killing you')
    can_pray = skills.level('prayer') >= PROTECT_MELEE_LEVEL
    if not can_pray:
        log(f'prayer below {PROTECT_MELEE_LEVEL} — the first three forms will land every hit')
    game.set_auto_retaliate(True)
    attacking = -1
    reported = -1
    for i in range(FIGHT_GUARD):
        if not in_battleground(game.tile()):
            if on_loft(game.tile()):
                log('Koschei landed the last blow — the trial is passed')
                return True
            # Why: `combat_viking_damage_player` only calls `viking_honour_death` when the roll lands on the last remaining hitpoint, and an overkill is an ordinary death in Lumbridge.
            log('Koschei overshot the killing blow — that was a real death, walking back for another round')
            return False
        if event_signal.pending():
            log('yielding to a random event')
            return False
        if can_pray and prayer.points() > 0 and not prayer.active(PROTECT_MELEE):
            yield from prayer.set(PROTECT_MELEE, True)
            continue
        target = attackable(KOSCHEI, 14)
        if not target:
            yield from execution.delay_ticks(2)
            continue
        now = game.tick()
        if now - reported >= 40:
            reported = now
            log(f"{KOSCHEI}: hp={skills.effective('hitpoints')}/{skills.level('hitpoints')} prayer={prayer.points()}")
        if target.index != attacking or not game.in_combat():
            if target.interact('Attack'):
                attacking = target.index
        else:
            yield from prayer_upkeep()
        yield from execution.delay_ticks(1)
    log(f'gave up on Koschei after {FIGHT_GUARD} ticks')
    return False


def leave_loft(log):
    _w1 = yield from walk_to(FT_TILE.WARRIOR_LOFT_LADDER, 1, log)
    if not (_w1):
        return False
    yield from settle_scene()
    status = yield from reach.loc_op('Ladder', 'Climb-down', FT_TILE.WARRIOR_LOFT_LADDER, lambda: (game.tile().level if game.tile() is not None else None) == 0, id=FT_LOC.WARRIOR_LADDER_DOWN, expect_ms=15000, log=log)
    return status == 'done'
