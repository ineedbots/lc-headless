"""Ported from rs2b0t's src/bot/api/ai/quests/defs/fremenniktrials/warrior.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.catalogs.tasks import sustain
from rs2004.execution import event_signal
from rs2004.game import game, skills
from rs2004.quests.defs.fremenniktrials.areas import FT_LOC, FT_TILE, PEER, THORVALD, in_battleground
from rs2004.quests.defs.fremenniktrials.seer import PEER_BANK
from rs2004.quests.defs.fremenniktrials.supplies import FOOD_TARGET, banked, food_held, food_in_bank, food_names, scan_bank, walk_to, withdraw_step
from rs2004.quests.defs.trollstronghold.combat import attackable
from rs2004.quests.engine.types import has_flag
from rs2004.quests.exec.prompts import settle_scene
from rs2004.reach import reach
from rs2004.tabs import prayer

__all__ = ['warrior_step', 'leave_loft_step', 'on_loft', 'koschei_food_allowed', 'PROTECT_MELEE_LEVEL', 'PROVEN_PRAYER']

KOSCHEI = 'Koschei the deathless'
# The forms change type while retaining the same NPC index.
KOSCHEI_FORMS = [1290, 1291, 1292, 1293]


def koschei_food_allowed():
    """Food is useful only while a known first, second or third form is present."""
    target = attackable(KOSCHEI, 14)
    return target is not None and target.id in KOSCHEI_FORMS[:3]


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
    # Peer banks the entire pack, so clear equipment before withdrawing the food the ladder permits.
    foods = set([name.lower() for name in food_names()])
    if any([name not in foods for name in snap.inv]) or len(snap.worn) > 0:
        return Record({'kind': 'talk', 'stop': PEER(PEER_BANK)})
    if not snap.bank_known:
        return scan_bank()
    food = food_in_bank(snap)
    if food_held(snap) < FOOD_TARGET and food is not None:
        return withdraw_step([{'name': food, 'qty': min(banked(snap, food), FOOD_TARGET - food_held(snap))}])
    if food_held(snap) == 0:
        return Record({'kind': 'wait', 'reason': 'bank food for Koschei\'s first three forms'})
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
# Prayer 70 provides a larger buffer while punching through the first three forms.
PROVEN_PRAYER = 70


# Why: only the 4th form is wired to `viking_honour_death`; the first 3 kill an unarmed character outright, even at 70 stats.
# Protect from Melee blocks damage while it lasts; food covers the remainder, then protection drops for form 4.
def fight_koschei(log):
    """Beat the first 3 forms with food and prayer, then let the 4th win."""
    log('unarmed against Koschei — three forms to beat, then the fourth passes the trial by killing you')
    can_pray = skills.level('prayer') >= PROTECT_MELEE_LEVEL
    if not can_pray:
        log(f'prayer below {PROTECT_MELEE_LEVEL} — the first three forms will land every hit')
    game.set_auto_retaliate(True)
    attacking = -1
    reported = -1
    form = None
    for i in range(FIGHT_GUARD):
        if not in_battleground(game.tile()):
            if on_loft(game.tile()):
                log('Koschei landed the last blow — the trial is passed')
                return True
            log('left Koschei\'s battleground without the safe loft landing — trial not passed')
            return False
        if event_signal.pending():
            log('yielding to a random event')
            return False
        target = attackable(KOSCHEI, 14)
        if not target:
            yield from execution.delay_ticks(2)
            continue
        if target.id != form:
            form = target.id
            if form in KOSCHEI_FORMS:
                log(f'Koschei form {KOSCHEI_FORMS.index(form) + 1}/4')
        if form in KOSCHEI_FORMS[:3]:
            # Outside combat, shared upkeep drops protection; raising it again here would prevent reengaging.
            if game.in_combat():
                before = game.tick()
                yield from sustain.run()
                if game.tick() != before:
                    continue
            if can_pray and prayer.points() > 0 and not prayer.active(PROTECT_MELEE):
                yield from prayer.set(PROTECT_MELEE, True)
                continue
        elif form == KOSCHEI_FORMS[3] and prayer.active(PROTECT_MELEE):
            yield from prayer.set(PROTECT_MELEE, False)
            continue
        now = game.tick()
        if now - reported >= 40:
            reported = now
            log(f"{KOSCHEI}: hp={skills.effective('hitpoints')}/{skills.level('hitpoints')} prayer={prayer.points()}")
        if target.index != attacking or not game.in_combat():
            if target.interact('Attack'):
                attacking = target.index
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
