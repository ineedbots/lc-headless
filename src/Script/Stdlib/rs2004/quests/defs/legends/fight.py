"""Ported from rs2b0t's src/bot/api/ai/quests/defs/legends/fight.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.tasks import sustain
from rs2004.entities import npcs
from rs2004.game import game, skills
from rs2004.items import inventory
from rs2004.quests.defs.legends.supplies import PRAYER_POTIONS
from rs2004.tabs import prayer

__all__ = ['drink_prayer', 'fight']

PROTECT_MELEE = 'Protect from Melee'
PRAYER_OFF_ATTEMPTS = 3
SWING_GAP = 5
# Why: prayer points equal the prayer level, so 70 is 3.5 minutes of Protect from Melee and the 3 guardians outlast it; the dose goes in well before the prayer lapses.
PRAYER_FLOOR = 25
# Why: the 3 Viyeldi guardians are all aggressive at once and each hits for double figures, so a pass that starts eating at 55% can lose the rest in the same tick.
EAT_BELOW = 0.7


def target(name):
    return npcs.query().name(name).action('Attack').within(14).nearest()


def hurt():
    max_ = skills.level('hitpoints')
    return max_ > 0 and skills.effective('hitpoints') / max_ < EAT_BELOW


def drink_prayer(log):
    """Drink one dose of prayer restore, if the pack has any."""
    dose = ([item for item in inventory.items() if any([p.id == item.id for p in PRAYER_POTIONS])] or [None])[0]
    if not dose:
        return False
    if not (dose.interact('Drink')):
        return False
    log('drank a prayer potion')
    yield from execution.delay_ticks(1)
    return True


# Why: the server runs one op per tick and drops the rest, so a pass that eats, prays and swings loses 2 of the 3, and the one it loses is the food.
# Why: the order is eat, then top the prayer up, then swing, which keeps hitpoints off the floor against a level-187 demon at 70s.
def fight(plan, log):
    """Fight one named NPC to a goal, holding Protect from Melee and eating as needed."""
    want_pray = plan.pray != False and prayer.known(PROTECT_MELEE) and skills.level('prayer') >= 43
    won = yield from fight_loop(plan, want_pray, log)
    # Why: the server runs one op per tick and drops the rest, and this toggle is sent on the tick the fight ended, which the loop may have spent on a swing, so it's the send most likely to be dropped.
    # Why: left on it drains through the walk out and empties the flask the next fight needs. `Prayer.set` returns false when the toggle doesn't land, so retry it.
    if want_pray:
        for i in range(PRAYER_OFF_ATTEMPTS):
            if not prayer.active(PROTECT_MELEE):
                break
            yield from prayer.set(PROTECT_MELEE, False)
        if prayer.active(PROTECT_MELEE):
            log('Protect from Melee would not switch off')
    return won


def fight_loop(plan, want_pray, log):
    deadline = _core.step_time() + (plan.ms if plan.ms is not None else 300000)
    last_tick = -1
    last_swing = -99
    # Why: the loop spends its first ticks eating and swinging, and 3 aggressive guardians take a third of the bar in that time, so the prayer goes up before the first blow.
    if want_pray and not prayer.active(PROTECT_MELEE) and prayer.available(PROTECT_MELEE):
        yield from prayer.set(PROTECT_MELEE, True)
    while _core.step_time() < deadline:
        if plan.done():
            return True
        tick = game.tick()
        if tick == last_tick:
            yield from execution.delay_ticks(1)
            continue
        last_tick = tick
        if hurt():
            yield from sustain.run()
            continue
        if want_pray and prayer.points() <= PRAYER_FLOOR:
            drank = yield from drink_prayer(log)
            if drank:
                continue
        if want_pray and not prayer.active(PROTECT_MELEE) and prayer.available(PROTECT_MELEE):
            yield from prayer.set(PROTECT_MELEE, True)
            continue
        enemy = target(plan.npc)
        if not enemy:
            yield from execution.delay_ticks(2)
            continue
        # Why: With three attackers, the named NPC may not be the active opponent; repeated Attack ops can consume eating ticks.
        if (not game.in_combat() or not enemy.targets_me()) and tick - last_swing >= SWING_GAP:
            last_swing = tick
            enemy.interact('Attack')
            yield from execution.delay_until(lambda: game.in_combat() or plan.done(), 5000)
            continue
        yield from execution.delay_ticks(1)
    log(f'{plan.npc} outlasted the fight budget')
    return plan.done()
