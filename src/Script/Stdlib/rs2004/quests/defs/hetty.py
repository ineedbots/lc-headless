"""Witch's Potion: rs2b0t's api/ai/quests/defs/hetty.ts (MIT, see thirdparty/rs2b0t). An onion, a rat's tail, an
eye of newt and burnt meat for Hetty in Rimmington, then a drink from her cauldron."""

from rs2004 import execution
from rs2004.dialogue import chat_dialog
from rs2004.entities import ground_items, locs, npcs
from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.quests.data import quest_record
from rs2004.quests.engine.types import QuestModule, quest_step
from rs2004.quests.exec.primitives import NpcStop, goto_npc, talk_through
from rs2004.traversal import traversal

__all__ = [
    'HETTY', 'RATS_TAIL', 'INGREDIENTS', 'gather_onion', 'gather_eye_of_newt', 'gather_rats_tail', 'gather_burnt_meat',
    'decide', 'hetty',
]

HETTY = NpcStop('Hetty', Tile(2970, 3207, 0), 6, ['I am in search of a quest.', 'Yes help me become one with my darker side.'])
CAULDRON = Tile(2967, 3205, 0)
RANGE = Tile(2970, 3209, 0)
RATS = Tile(2955, 3204, 0)
ONION_FIELD = Tile(2950, 3251, 0)
BETTY_SHOP = {'npc': 'Betty', 'anchor': Tile(3011, 3260, 0)}
WYDIN_SHOP = {'npc': 'Wydin', 'anchor': Tile(3014, 3204, 0)}
DRAYNOR_BANK = Tile(3093, 3243, 0)
# Why: content 289 renamed the obj from "Rats tail" (274) to "Rat's tail"; name match is apostrophe-exact.
RATS_TAIL = "Rat's tail"

INGREDIENTS = [RATS_TAIL.lower(), 'onion', 'eye of newt', 'burnt meat']


def _gp_short(snap, est_gp):
    return max(0, est_gp - snap.inv.get('coins', 0) - snap.bank_coins)


def _started_or(snap, step):
    if snap.journal == 'unknown':
        return quest_step('wait', reason='quest journal not loaded')
    if snap.journal == 'not_started':
        return quest_step('talk', stop=HETTY)
    return step


def gather_onion(snap, need=1):
    return _started_or(snap, quest_step('pick_loc', loc='Onion', op='Pick', item='Onion', anchor=ONION_FIELD))


def gather_eye_of_newt(snap, need=1):
    if _gp_short(snap, 20) > 0:
        step = quest_step('wait', reason='need ~20 gp for Eye of newt')
    else:
        step = quest_step('buy', item='Eye of newt', qty=1, shop=BETTY_SHOP, est_gp=20)
    return _started_or(snap, step)


def gather_rats_tail(snap, need=1):
    return _started_or(snap, quest_step('custom', name='kill a rat for its tail', run=kill_rat_grab_tail))


def gather_burnt_meat(snap, need=1):
    if 'cooked meat' in snap.inv or 'raw beef' in snap.inv:
        step = quest_step('custom', name='burn the meat on the range', run=burn_meat)
    elif _gp_short(snap, 20) > 0:
        step = quest_step('wait', reason='need ~20 gp for Raw beef')
    else:
        step = quest_step('buy', item='Raw beef', qty=2, shop=WYDIN_SHOP, est_gp=20)
    return _started_or(snap, step)


def _free_rat(n):
    return not n.in_combat


def _tail_or_no_rat():
    return ground_items.query().name(RATS_TAIL).within(8).nearest() is not None or npcs.query().name('Rat').within(1).nearest() is None


def kill_rat_grab_tail(log):
    """Takes a dropped tail, or kills a Rimmington rat for one. Use with yield from."""
    if inventory.contains(RATS_TAIL):
        return True
    drop = ground_items.query().name(RATS_TAIL).within(8).nearest()
    if drop is not None:
        log(f'picking up the dropped {RATS_TAIL}')
        if not drop.interact('Take'):
            return False
        taken = yield from execution.delay_until(lambda: inventory.contains(RATS_TAIL), 6000)
        return taken
    log('walking to the Rimmington rats to get a tail')
    walked = yield from traversal.walk_resilient(RATS, radius=5, attempts=3, timeout_ms=120000, log=log)
    if not walked:
        return False
    rat = npcs.query().name('Rat').action('Attack').where(_free_rat).within(10).nearest()
    if rat is None:
        log('kill_rat_grab_tail: no free Rat near the anchor — LIVE-VERIFY the Rimmington spawn')
        return False
    game.set_combat_style('strength')
    log('attacking a Rat for its tail')
    if not rat.interact('Attack'):
        return False
    yield from execution.delay_until(_tail_or_no_rat, 6000)
    return False


def _oven():
    return locs.query().name('Range').where(lambda l: l.tile().distance_to(RANGE) <= 6).nearest()


def burn_meat(log):
    """Cooks the beef on Hetty's range until it burns. Use with yield from."""
    if inventory.contains('Burnt meat'):
        return True
    walked = yield from traversal.walk_resilient(RANGE, radius=2, attempts=3, timeout_ms=90000, log=log)
    if not walked:
        return False
    for n in range(12):
        if inventory.contains('Burnt meat'):
            break
        if chat_dialog.is_make_menu():
            made = yield from chat_dialog.make('meat')
            if not made:
                yield from chat_dialog.make()
            yield from execution.delay_ticks(2)
            continue
        meat = inventory.first('Cooked meat')
        if meat is None:
            meat = inventory.first('Raw beef')
        if meat is None:
            return False
        range_loc = _oven()
        if range_loc is None:
            return False
        cooked_before = inventory.count('Cooked meat')
        burnt_before = inventory.count('Burnt meat')
        log('burning the cooked meat on the range' if meat.name == 'Cooked meat' else 'cooking the raw beef on the range')
        if not meat.use_on(range_loc):
            yield from execution.delay_ticks(2)
            continue

        def changed():
            return chat_dialog.is_make_menu() or inventory.count('Burnt meat') > burnt_before or inventory.count('Cooked meat') != cooked_before

        yield from execution.delay_until(changed, 6000)
    return inventory.contains('Burnt meat')


def hand_in_and_drink(log):
    """The four ingredients to Hetty, then a drink from the cauldron. Use with yield from."""
    reached = yield from goto_npc(HETTY, [], log)
    if not reached:
        return False
    log('handing the four ingredients to Hetty')
    yield from talk_through('Hetty', [], log)
    walked = yield from traversal.walk_resilient(CAULDRON, radius=2, attempts=3, timeout_ms=60000, log=log)
    if not walked:
        return False
    cauldron = locs.query().name('Cauldron').action('Drink From').within(8).nearest()
    if cauldron is None:
        log('hand_in_and_drink: no Cauldron[Drink From] near Hetty — LIVE-VERIFY')
        return False
    log('drinking from the cauldron to finish the quest')
    if not cauldron.interact('Drink From'):
        return False
    yield from execution.delay_ticks(3)
    return True


def _gather_for(name, snap):
    if name == 'onion':
        return gather_onion(snap)
    if name == RATS_TAIL.lower():
        return gather_rats_tail(snap)
    if name == 'eye of newt':
        return gather_eye_of_newt(snap)
    if name == 'burnt meat':
        return gather_burnt_meat(snap)
    return quest_step('wait', reason=f'no gatherer for {name}')


def decide(snap):
    if snap.journal == 'complete':
        return quest_step('done')
    if snap.journal == 'unknown':
        return quest_step('wait', reason='quest journal not loaded')
    if snap.journal == 'not_started':
        return quest_step('talk', stop=HETTY)
    need = [i for i in INGREDIENTS if i not in snap.inv]
    if len(need) == 0:
        return quest_step('custom', name='hand in the ingredients and drink the potion', run=hand_in_and_drink)
    return _gather_for(need[0], snap)


hetty = QuestModule(
    record=quest_record('hetty'),
    bank=DRAYNOR_BANK,
    grind=['Rat'],
    tools=['coins', 'raw beef', 'cooked meat'],
    gather={
        'onion': gather_onion,
        RATS_TAIL.lower(): gather_rats_tail,
        'eye of newt': gather_eye_of_newt,
        'burnt meat': gather_burnt_meat,
    },
    decide=decide,
)
