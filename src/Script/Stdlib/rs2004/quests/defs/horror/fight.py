"""Ported from rs2b0t's src/bot/api/ai/quests/defs/horror/fight.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import chat_dialog
from rs2004.entities import npcs
from rs2004.game import game, skills
from rs2004.items import inventory
from rs2004.quests.defs.horror.areas import HD_ID, HD_TILE
from rs2004.quests.defs.horror.supplies import melee_ready, melee_weapon_name
from rs2004.quests.exec.primitives import drive_dialog
from rs2004.quests.exec.prompts import settle_scene
from rs2004.quests.prayer import PRAYER_FLOOR, PRAYER_POTION_IDS
from rs2004.reach import reach
from rs2004.tabs import prayer
from rs2004.traversal import traversal

__all__ = ['FORM_ELEMENT', 'RANGED_FORM', 'MELEE_FORM', 'IMMUNE_FORMS', 'MOTHER_IDS', 'spell_tier', 'fight_junior', 'fight_mother']

MAGIC_TAB = 6
DAGANNOTH_JR = 1347
# Why: `npc_max_dealt` zeroes every hit the current form isn't weak to, so the form's npc id from `npc_changetype` picks the spell.
# The mother's 6 forms.
FORM_ELEMENT = {
    1348: 'Wind',
    1349: 'Wind',
    1350: 'Wind',
    1351: 'Wind',
    1352: 'Water',
    1353: 'Fire',
    1354: 'Earth',
}
# Why: no spell touches `horror_dagganoth_ranged` (1355) or `horror_dagganoth_melee` (1356), named in `npc.dat` for the style they're weak to; a wielded melee weapon turns 1356's 30 ticks into a fight.
RANGED_FORM = 1355
MELEE_FORM = 1356
IMMUNE_FORMS = set([RANGED_FORM, MELEE_FORM])
MOTHER_IDS = [1348, 1349, 1350, 1351, 1352, 1353, 1354, 1355, 1356]
TIERS = [
    Record({'suffix': 'blast', 'level': 59}),
    Record({'suffix': 'bolt', 'level': 35}),
    Record({'suffix': 'strike', 'level': 13}),
]


def spell_tier(magic):
    for t in TIERS:
        if magic >= t.level:
            return t.suffix
    return None


def by_ids(ids):
    return npcs.query().where(lambda n: (n.id in ids)).nearest()


def mother():
    return by_ids(MOTHER_IDS)


def junior():
    return by_ids([DAGANNOTH_JR])


# Why: at stage 4 this queues the junior and at stage 5 the mother; neither respawns on its own, so it's how a death resumes.
def poke_jossik(log):
    """Talk to Jossik to queue the next dagannoth."""
    _w2 = yield from traversal.walk_resilient(HD_TILE.JOSSIK, radius=3, attempts=4, timeout_ms=120000, log=log)
    if not (_w2):
        return False
    yield from settle_scene()
    status = yield from reach.entity_op(lambda: npcs.query().name('Jossik').nearest(), 'Talk-to', lambda: chat_dialog.is_open() or chat_dialog.can_continue(), what='Jossik', log=log)
    if status != 'done':
        return False
    yield from drive_dialog([], log)
    return True


# Why: `horror_dagannoth_jr4` has no `ai_*player2`, so it runs the default melee AI at `damagetype=stab_style`; Protect from Melee zeroes it and Protect from Missiles does nothing.
# Why: the mother melees in `opplayer2` and ranges in `applayer2`, and `ai_applayer2` puts her back on melee once missiles are protected, so missiles forces her onto the single-figure style.
# Why: alternating prayers only wins if the flip lands every tick, and eating spends the tick's one action, so hold one prayer.
PROTECT = {
    'melee': Record({'name': 'protect from melee', 'level': 43}),
    'missiles': Record({'name': 'protect from missiles', 'level': 40}),
}


class Protection:
    def __init__(self, kind):
        self.arms = 0
        self._kind = kind
        self._prayer = PROTECT[kind].name
        self.usable = skills.level('prayer') >= PROTECT[kind].level

    def up(self):
        return prayer.active(self._prayer)

    def hold(self):
        """Cheap when already up: `Prayer.set` reads the varp and returns."""
        if not self.usable or prayer.points() <= 0 or self.up():
            return
        raised = yield from prayer.set(self._prayer, True)
        if raised:
            self.arms += 1

    def active(self):
        return (self._kind if self.up() else 'none')

    def clear(self):
        yield from prayer.set(self._prayer, False)


def low_on_prayer_dose():
    """A dose to drink, when the bar is nearly out and there is one."""
    if prayer.points() > PRAYER_FLOOR:
        return None
    return ([item for item in inventory.items() if item.id in PRAYER_POTION_IDS] or [None])[0]


CAST_TICKS = 5
# Why: eat at a tuna's worth of damage; waiting for a shark's worth spends the margin a bad 30 ticks eats through.
EAT_AT_MISSING = 12


def hungry():
    max_ = skills.level('hitpoints')
    return max_ > 0 and skills.effective('hitpoints') <= max_ - EAT_AT_MISSING


# Why: the server runs one op per tick and drops the rest, so it's one action per tick in the order pray, eat, cast.
# Why: eating first spends every damaged tick on food and the prayer never re-arms; prayer is a no-op once the varp says it's up, so it goes first.
def fight_loop(plan, log):
    """Run one fight to its win condition."""
    prayers = Protection(plan.protect)
    if not prayers.usable:
        log(f'prayer below {PROTECT[plan.protect].level} — the {plan.what} will land hits this fight')
    # Prayer first, tab second. Whatever is already attacking doesn't wait for an interface.
    yield from prayers.hold()
    # The spellbook root is only walkable once its tab is built, so open it before the first form change.
    yield from game.open_side_tab(MAGIC_TAB)
    game.set_auto_retaliate(False)
    state = Record({'handed_over': False})
    try:
        result = yield from _fight_rounds(plan, prayers, state, log)
    except Exception as e:
        game.set_auto_retaliate(True)
        if not state.handed_over:
            yield from prayers.clear()
        raise e
    game.set_auto_retaliate(True)
    if not state.handed_over:
        yield from prayers.clear()
    return result


def _fight_rounds(plan, prayers, state, log):
    casts = 0
    refused = 0
    last_tick = -1
    last_cast = -CAST_TICKS
    reported = -1
    swings = 0
    meleeing = -1
    for i in range(plan.guard):
        if plan.won():
            log(f'the {plan.what} is dead ({casts} casts, {swings} melee attacks, {prayers.arms} prayer re-arms)')
            if plan.handover:
                yield from Protection(plan.handover).hold()
                state.handed_over = True
            return True
        now = game.tick()
        if now == last_tick:
            yield from execution.delay_ticks(1)
            continue
        last_tick = now
        target = plan.target()
        if not target:
            poked = yield from poke_jossik(log)
            if not poked:
                return False
            yield from execution.delay_ticks(plan.summon_delay)
            continue
        if now - reported >= 40:
            reported = now
            log(f"{plan.what}: form {target.id} hp={skills.effective('hitpoints')}/{skills.level('hitpoints')}" + f' prayer={prayers.active()} ({prayer.points()}) casts={casts} swings={swings}')
        dose = low_on_prayer_dose() if prayers.usable else None
        if dose:
            dose.interact('Drink')
            yield from execution.delay_ticks(1)
            continue
        if prayers.usable and not prayers.up() and prayer.points() > 0:
            yield from prayers.hold()
            continue
        if hungry():
            yield from sustain.run()
            continue
        if plan.melee is not None and plan.melee(target):
            # Already swinging at this form: the op stands, so don't re-target.
            if target.index == meleeing and game.facing() == ('npc', target.index):
                yield from execution.delay_ticks(1)
                continue
            if target.interact('Attack'):
                meleeing = target.index
                swings += 1
            else:
                refused += 1
                if refused >= 5:
                    log(f'could not attack form {target.id} — the weapon is not wielded')
                    return False
            yield from execution.delay_ticks(1)
            continue
        meleeing = -1
        element = plan.element(target)
        if element and now - last_cast >= CAST_TICKS:
            if game.cast_on_npc(element, target):
                last_cast = now
                casts += 1
                refused = 0
            else:
                refused += 1
                if refused >= 5:
                    # A cast that never selects is silent: no message, no animation.
                    log(f'could not select {element} — magic level or runes short')
                    return False
        yield from execution.delay_ticks(1)
    return plan.won()


def fight_junior(log):
    """Kill the junior. It only becomes attackable on the 4th tick of its spawn."""
    magic = skills.level('magic')
    tier = spell_tier(magic)
    if not tier:
        log(f'magic {magic} cannot cast any combat spell')
        return False
    # It takes damage from anything, so a wielded weapon beats a spell: no cast delay, no runes, no 5-tick cap.
    melee = melee_ready()
    log((f'meleeing the junior with the {melee_weapon_name()}' if melee else f'no melee weapon wielded — casting Wind {tier} at the junior'))
    _result6 = yield from fight_loop(Record({
        'what': 'dagannoth junior',
        'target': junior,
        'melee': lambda *_args: melee,
        'element': lambda *_args: f'Wind {tier}',
        'won': lambda: mother() is not None,
        'summon_delay': 6,
        'protect': 'melee',
        'handover': 'missiles',
        'guard': 3000,
    }), log)
    return _result6


def _mother_won():
    here = game.tile()
    return inventory.count_by_id(HD_ID.CASKET) > 0 or (here is not None and here.z >= 9984)


# Why: 2 of her 6 forms take no damage from a magic loadout, so the loop prays through those 30 ticks; the 4 elemental windows clear 120 hp in a cycle and a half.
def fight_mother(log):
    """Kill the Dagannoth mother."""
    magic = skills.level('magic')
    tier = spell_tier(magic)
    if not tier:
        log(f'magic {magic} cannot cast any combat spell')
        return False
    melee = melee_ready()
    log((f'meleeing form {MELEE_FORM} with the {melee_weapon_name()}; form {RANGED_FORM} still has to be prayed through' if melee else f'no melee weapon wielded — forms {MELEE_FORM} and {RANGED_FORM} will be prayed through'))

    def _fn8(npc):
        form = FORM_ELEMENT.get(npc.id)
        if not form and not (npc.id in IMMUNE_FORMS):
            log(f'unexpected dagannoth form {npc.id}')
        return (f'{form} {tier}' if form else None)
    _result7 = yield from fight_loop(Record({
        'what': 'Dagannoth mother',
        'target': mother,
        'melee': lambda npc: melee and npc.id == MELEE_FORM,
        'element': _fn8,
        'won': _mother_won,
        'summon_delay': 8,
        'protect': 'missiles',
        'guard': 6000,
    }), log)
    return _result7
