"""Ported from rs2b0t's src/bot/api/ai/quests/defs/trollstronghold/combat.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.bot import is_generator
from rs2004.catalogs.record import Record
from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import chat_dialog
from rs2004.entities import npcs
from rs2004.execution import event_signal
from rs2004.game import game, skills
from rs2004.items import inventory
from rs2004.quests.defs.trollstronghold.areas import PRAYER_SIP_AT
from rs2004.quests.exec.primitives import pick_preferred
from rs2004.tabs import prayer

__all__ = ['PROTECT', 'protected_walk', 'needs_sip', 'fight', 'attackable']

PROTECT = {
    'melee': Record({'name': 'protect from melee', 'level': 43}),
    'missiles': Record({'name': 'protect from missiles', 'level': 40}),
    'magic': Record({'name': 'protect from magic', 'level': 37}),
}


class Protection:
    usable = None
    arms = 0

    def __init__(self, kind):
        self._kind = kind
        self.usable = skills.level('prayer') >= PROTECT[kind].level

    def up(self):
        return prayer.active(PROTECT[self._kind].name)

    def hold(self):
        if not self.usable or prayer.points() <= 0 or self.up():
            return False
        _w1 = yield from prayer.set(PROTECT[self._kind].name, True)
        if _w1:
            self.arms += 1
            return True
        return False

    def clear(self):
        if self.up():
            yield from prayer.set(PROTECT[self._kind].name, False)


# Why: a fixed on-at-A-off-at-B window is wrong at one end; the throwers are behind you before the stronghold door and prayer burnt after that is prayer the fight inside doesn't get.
# Why: the walker pumps `Sustain` every pass, so borrowing the hook for the walk gives a per-tick check: up while something is shooting, down when nothing is.
# Why: the host's own hook (eating) still runs first; a prayer already holding costs nothing, food does.
class _WalkGuard:
    """What protected_walk's hook keeps between ticks: the prayer, whether it holds, and the host's own hook."""

    def __init__(self, kind, threat, host, log):
        self.kind = kind
        self.threat = threat
        self.host = host
        self.log = log
        self.prayer = Protection(kind)
        self.armed = False

    def label(self):
        return 'Missiles' if self.kind == 'missiles' else self.kind

    def tick(self):
        # The crossing drains too, so the same rule applies out here.
        if self.prayer.usable and needs_sip(prayer.points(), prayer.max()):
            sipped = yield from sip_prayer(self.log)
            if sipped:
                return
        if self.threat():
            if not self.armed:
                held = yield from self.prayer.hold()
                if held:
                    self.armed = True
                    self.log(f'holding Protect from {self.label()}')
        elif self.armed:
            self.armed = False
            yield from self.prayer.clear()
            self.log(f'dropping Protect from {self.label()} — nothing in range')
        if self.host is not None:
            result = self.host()
            if is_generator(result):
                yield from result


def protected_walk(kind, threat, walk, log):
    """Run `walk` with a protection prayer that tracks the threat."""
    guard = _WalkGuard(kind, threat, sustain.hook, log)
    sustain.set(guard.tick)
    try:
        result = yield from walk()
    except Exception as e:
        sustain.set(guard.host)
        yield from guard.prayer.clear()
        raise e
    sustain.set(guard.host)
    yield from guard.prayer.clear()
    return result


def needs_sip(points, max_):
    return max_ > 0 and points < max_ * PRAYER_SIP_AT


def sip_prayer(log):
    """False when there is nothing to drink, so the caller can spend the tick elsewhere."""

    def drinkable(i):
        name = (i.name if i.name is not None else '').lower()
        return name.startswith('prayer potion') and any([a.lower() == 'drink' for a in i.actions()])

    pot = ([i for i in inventory.items() if drinkable(i)] or [None])[0]
    if not pot:
        return False
    before = prayer.points()
    if not (pot.interact('Drink')):
        return False
    drank = yield from execution.delay_until(lambda: prayer.points() > before, 3000)
    if drank:
        log(f'sipped {pot.name} — prayer {before} → {prayer.points()}')
    return drank


EAT_AT_MISSING = 12


def hungry():
    max_ = skills.level('hitpoints')
    return max_ > 0 and skills.effective('hitpoints') <= max_ - EAT_AT_MISSING


# Why: the server runs one op per tick and silently drops the rest, so this loop does one action per tick, in the order dialogue, pray, eat, attack.
# Why: prayer goes before food because it is free once the varp says it is up, and a loop that eats first spends every damaged tick on food and never re-arms.
def fight_rounds(plan, prayers, log):
    game.set_auto_retaliate(True)
    last_tick = -1
    reported = -1
    swings = 0
    attacking = -1
    for i in range(plan.guard):
        if plan.won():
            log(f'{plan.what}: done ({swings} attacks, {prayers.arms} prayer re-arms)')
            return True
        # Why: the host answers random events, and this loop owns the tick budget until it returns.
        if event_signal.pending():
            log(f'{plan.what}: yielding to a random event')
            return False
        now = game.tick()
        if now == last_tick:
            yield from execution.delay_ticks(1)
            continue
        last_tick = now
        if plan.dialogue and (chat_dialog.is_open() or chat_dialog.can_continue()):
            yield from drain_dialogue(plan.dialogue, plan.on_dialogue, log)
            continue
        # Sip first: prayer cannot be re-armed on an empty bar.
        _c10 = prayers.usable and needs_sip(prayer.points(), prayer.max())
        if _c10:
            _w11 = yield from sip_prayer(log)
            _c10 = (_w11)
        if _c10:
            continue
        if prayers.usable and not prayers.up() and prayer.points() > 0:
            yield from prayers.hold()
            continue
        if hungry():
            yield from sustain.run()
            continue
        target = plan.target()
        if not target:
            attacking = -1
            _c12 = plan.on_missing
            if _c12:
                _w13 = yield from plan.on_missing()
                _c12 = not (_w13)
            if _c12:
                return False
            yield from execution.delay_ticks(2)
            continue
        if now - reported >= 40:
            reported = now
            log(f"{plan.what}: hp={skills.effective('hitpoints')}/{skills.level('hitpoints')}" + f' prayer={prayer.points()} attacks={swings}')
        # Why: melee keeps swinging on its own, so re-clicking the same target spends the tick's one action re-targeting.
        # Why: Dad's slam knocks us 7 tiles clear and drops combat, which is when to re-issue.
        if target.index == attacking and game.in_combat():
            yield from execution.delay_ticks(1)
            continue
        if target.interact('Attack'):
            attacking = target.index
            swings += 1
        yield from execution.delay_ticks(1)
    log(f'{plan.what}: gave up after {plan.guard} ticks')
    return False


def fight(plan, log):
    """Run one fight to its win condition."""
    prayers = Protection(plan.protect)
    if not prayers.usable:
        log(f'prayer below {PROTECT[plan.protect].level} — the {plan.what} will land hits this fight')
    yield from prayers.hold()
    try:
        won = yield from fight_rounds(plan, prayers, log)
    except Exception as e:
        if plan.won():
            yield from prayers.clear()
        raise e
    if plan.won():
        yield from prayers.clear()
    return won


def drain_dialogue(prefer, on_chosen, log):
    for i in range(20):
        if chat_dialog.can_continue():
            yield from chat_dialog.continue_()
            yield from execution.delay_ticks(1)
            continue
        opts = chat_dialog.options()
        if len(opts) == 0:
            return
        pick = pick_preferred(opts, list(prefer))
        if not pick:
            log(f"WARN: mid-fight dialogue had no preferred option in [{' | '.join(opts)}]")
            return
        yield from chat_dialog.choose_option(pick)
        if on_chosen is not None:
            on_chosen(pick)
        yield from execution.delay_ticks(2)


def attackable(name, within):
    """Nearest NPC of `name` offering Attack and not already someone else's fight."""
    return npcs.query().name(name).action('Attack').where(lambda n: not n.targets_another_player()).within(within).nearest()
