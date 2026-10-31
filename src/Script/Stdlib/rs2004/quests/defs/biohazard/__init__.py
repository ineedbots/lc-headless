"""Ported from rs2b0t's src/bot/api/ai/quests/defs/biohazard/index.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.data import quest_record
from rs2004.quests.engine.types import QuestModule
from rs2004.quests.defs.biohazard.ardougne import ask_elena_for_replacements, ask_jerico, confront_lathas, feed_the_tower, hand_over_distillator, release_pigeons, report_to_elena, start_quest, take_birdfeed, take_pigeons
from rs2004.quests.defs.biohazard.areas import BIO_ITEM, VIALS, bio_area, held, in_guidor_quarter, owned, worn
from rs2004.quests.defs.biohazard.journal import BIO_STAGE, read_biohazard_progress
from rs2004.quests.defs.biohazard.supplies import HANDBACK_SLOTS, owns_all, reclaim, scan_bank, source_coins, source_food, tidy
from rs2004.quests.defs.biohazard.travel import go_mainland, go_west
from rs2004.quests.defs.biohazard.varrock import PRIEST_SUIT_GP, buy_priest_suit, collect_from_errand_boys, cross_east_gate, get_touch_paper, hand_to_errand_boys, leave_quarter, visit_guidor
from rs2004.quests.defs.biohazard.west import poison_the_stew, search_the_crate, take_doctor_gown, take_mourner_key, take_rotten_apples

__all__ = ['decide', 'biohazard']


def custom(name, run):
    return (Record({'kind': 'custom', 'name': name, 'run': run}))


TO_MAINLAND = custom('leave for the East Ardougne side', go_mainland)
TO_WEST = custom("cross the wall on Omart's rope ladder", go_west)
TIDY_FLOOR = 8
COLLECT_GIVE_UP = 2
PRIEST_SUIT = [BIO_ITEM.PRIEST_GOWN, BIO_ITEM.PRIEST_ROBE]


def on_mainland(area, step):
    return (step if area == 'mainland' else TO_MAINLAND)


def in_west(area, step):
    return (step if area == 'west' or area == 'hq' or area == 'hqUpstairs' else TO_WEST)


# Why: the meal and the priest suit's float come out here; Jerico's house is 9 tiles from the Ardougne booth and the watchtower where the next stage ends is 60.
def distraction_step(snap, area):
    """The distraction leg: seed from Jerico's cupboard, birds from behind his house, then the tower."""
    _v1 = source_food(snap)
    kit = (_v1 if _v1 is not None else source_coins(snap, PRIEST_SUIT_GP, False))
    if kit:
        return on_mainland(area, kit)
    _v2 = reclaim(snap, BIO_ITEM.BIRDFEED)
    feed = (_v2 if _v2 is not None else ((None if held(snap, BIO_ITEM.BIRDFEED) > 0 else custom("take bird feed from Jerico's cupboard", take_birdfeed))))
    if feed:
        return on_mainland(area, feed)
    birds = pigeon_step(snap)
    return on_mainland(area, (birds if birds is not None else custom('throw the bird feed onto the watchtower', feed_the_tower)))


def pigeon_step(snap):
    if held(snap, BIO_ITEM.PIGEONS) > 0:
        return None
    _v3 = reclaim(snap, BIO_ITEM.PIGEONS)
    return (_v3 if _v3 is not None else custom("take a pigeon cage from behind Jerico's house", take_pigeons))


def distillator_step(snap, area):
    """Everything the mourner headquarters leg needs, in the order the building demands it."""
    if owned(snap, BIO_ITEM.DOCTOR_GOWN) == 0:
        return in_west(area, custom("search the nurse's cupboard for a doctors' gown", take_doctor_gown))
    # Why: the cupboard hands nothing over while one is banked, so the banked copy is the only one this stage gets, and West Ardougne has no booth to draw it from.
    if held(snap, BIO_ITEM.DOCTOR_GOWN) == 0 and not worn(snap, BIO_ITEM.DOCTOR_GOWN):
        gown = reclaim(snap, BIO_ITEM.DOCTOR_GOWN)
        return (on_mainland(area, gown) if gown else Record({'kind': 'wait', 'reason': "the doctors' gown is nowhere the bot can reach"}))
    if held(snap, BIO_ITEM.MOURNER_KEY) == 0:
        key = reclaim(snap, BIO_ITEM.MOURNER_KEY)
        return (on_mainland(area, key) if key else in_west(area, custom('take the key off the sick mourner', take_mourner_key)))
    return in_west(area, custom("search the crate for Elena's distillator", search_the_crate))


# Why: Elena returns four items individually under `inv_freespace > 1`, requiring five free slots for all of them.
def return_distillator_step(snap, area):
    if held(snap, BIO_ITEM.DISTILLATOR) == 0:
        banked = reclaim(snap, BIO_ITEM.DISTILLATOR)
        return (banked if banked is not None else in_west(area, custom("search the crate for Elena's distillator", search_the_crate)))
    _v4 = tidy(snap, HANDBACK_SLOTS)
    return on_mainland(area, (_v4 if _v4 is not None else custom('hand Elena her distillator', hand_over_distillator)))


# Why: an errand boy taking a vial and Elena's own vials being lost look identical from the pack, so only the sample is reissued here; no errand boy is ever given it.
def reagent_step(snap, area):
    """Draw whatever Elena already handed over out of the bank, and replace a lost sample."""
    for item in list(VIALS) + [BIO_ITEM.PLAGUE_SAMPLE]:
        banked = reclaim(snap, item)
        if banked:
            return banked
    if held(snap, BIO_ITEM.PLAGUE_SAMPLE) > 0:
        return None
    return on_mainland(area, custom('ask Elena to replace the sample she gave me', ask_elena_for_replacements))


def outside_quarter_step(snap, area):
    """Rimmington and Varrock proper: hand the vials over, dress as a priest, then cross the gate."""
    reagents = reagent_step(snap, area)
    if reagents:
        return reagents
    if any([held(snap, vial) > 0 for vial in VIALS]):
        return custom('give the errand boys their vials', hand_to_errand_boys)
    if not owns_all(snap, PRIEST_SUIT):
        _v5 = source_coins(snap, PRIEST_SUIT_GP)
        return (_v5 if _v5 is not None else custom('buy a priest gown from Thessalia', buy_priest_suit))
    _v6 = reclaim(snap, BIO_ITEM.PRIEST_GOWN)
    suit = (_v6 if _v6 is not None else reclaim(snap, BIO_ITEM.PRIEST_ROBE))
    return (suit if suit is not None else custom("walk through the gate to Varrock's east quarter", cross_east_gate))


def outside(name, errand):
    """Leave the quarter through the guarded gate, then run the errand that sent us out."""

    def _fn7(log):
        _w9 = yield from leave_quarter(log)
        _c8 = (_w9)
        if not (_c8):
            return _c8
        _result10 = yield from errand(log)
        return _result10
    return custom(name, _fn7)


# Why: The quarter has no bank, and the gate confiscates any vial carried back out.
def in_quarter_step(snap):
    if owned(snap, BIO_ITEM.TOUCH_PAPER) == 0:
        return outside('ask the chemist for touch paper', get_touch_paper)
    if held(snap, BIO_ITEM.PLAGUE_SAMPLE) == 0:
        return outside('ask Elena to replace the sample she gave me', ask_elena_for_replacements)
    if any([held(snap, vial) == 0 for vial in VIALS]):
        # Why: Elena alone replaces lost vials, while the gate confiscates any remaining vial on exit.
        return (outside('ask Elena to replace the vials the errand boys ruined', ask_elena_for_replacements) if snap.no_progress >= COLLECT_GIVE_UP else custom('collect the vials at the Dancing Donkey', collect_from_errand_boys))
    return custom('take the kit to Guidor', visit_guidor)


def smuggle_step(snap, area):
    if in_guidor_quarter(snap.tile):
        return in_quarter_step(snap)
    if owned(snap, BIO_ITEM.TOUCH_PAPER) == 0:
        return on_mainland(area, custom('ask the chemist for touch paper', get_touch_paper))
    _v11 = reclaim(snap, BIO_ITEM.TOUCH_PAPER)
    return (_v11 if _v11 is not None else outside_quarter_step(snap, area))


def stage_step(snap, area, stage):
    if stage == BIO_STAGE.NOT_STARTED:
        return on_mainland(area, custom('ask Elena about her distillator', start_quest))
    elif stage == BIO_STAGE.STARTED:
        return on_mainland(area, custom('ask Jerico how to cross the wall', ask_jerico))
    elif stage == BIO_STAGE.SPOKEN_JERICO:
        return distraction_step(snap, area)
    elif stage == BIO_STAGE.USED_BIRDFEED:
        _v12 = pigeon_step(snap)
        return on_mainland(area, (_v12 if _v12 is not None else custom('open the pigeon cage by the wall', release_pigeons)))
    elif stage == BIO_STAGE.RELEASED_PIGEONS:
        return TO_WEST
    elif stage == BIO_STAGE.CLIMBED_LADDER:
        if held(snap, BIO_ITEM.ROTTEN_APPLES) == 0:
            return in_west(area, custom('take the rotten apples in West Ardougne', take_rotten_apples))
        return in_west(area, custom("poison the mourners' stew", poison_the_stew))
    elif stage == BIO_STAGE.POISONED_STEW:
        return distillator_step(snap, area)
    elif stage == BIO_STAGE.FOUND_DISTILLATOR:
        return return_distillator_step(snap, area)
    elif stage == BIO_STAGE.GIVEN_DISTILLATOR:
        _v13 = reagent_step(snap, area)
        return (_v13 if _v13 is not None else on_mainland(area, custom('ask the chemist for touch paper', get_touch_paper)))
    elif stage == BIO_STAGE.SPOKEN_CHEMIST:
        return smuggle_step(snap, area)
    elif stage == BIO_STAGE.FOUND_SECRET:
        return on_mainland(area, custom('tell Elena what Guidor found', report_to_elena))
    elif stage == BIO_STAGE.REPORTED_ELENA:
        return on_mainland(area, custom('confront King Lathas about the plague', confront_lathas))
    else:
        return Record({'kind': 'wait', 'reason': f'Biohazard stage {stage} is not implemented'})


def decide(snap):
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    area = bio_area(snap.tile)
    if area == 'unknown':
        return Record({'kind': 'wait', 'reason': 'player location unavailable'})
    _v14 = (snap.progress.stage if snap.progress is not None else None)
    stage = (_v14 if _v14 is not None else snap.stage)
    if snap.journal == 'complete' or ((stage if stage is not None else -1)) >= BIO_STAGE.COMPLETE:
        return Record({'kind': 'done'})
    if stage is None:
        return Record({'kind': 'wait', 'reason': 'Biohazard journal stage unavailable'})
    # Why: `ownsInventory` skips the engine's provisioning, so a banked gown, vial or key stays invisible until this module reads the bank; past the wall the navigator answers "unreachable" for every booth, so the read waits for the mainland.
    if not snap.bank_known:
        if area == 'mainland':
            return scan_bank()
        if stage >= BIO_STAGE.POISONED_STEW:
            return TO_MAINLAND
    spillover = (tidy(snap, TIDY_FLOOR) if area == 'mainland' else None)
    step = (spillover if spillover is not None else stage_step(snap, area, stage))
    # Why: West Ardougne has no booth and the headquarters is sealed behind a door the navigator has no edge for, so a bank leg decided over there walks at a booth it can prove no route to.
    return (TO_MAINLAND if bankless(area) and banking(step) else step)


def bankless(area):
    return area == 'hq' or area == 'hqUpstairs' or area == 'west' or area == 'sewer'


def banking(step):
    return step.kind == 'withdraw' or step.kind == 'deposit' or step.kind == 'scan_bank'


biohazard = QuestModule(**{
    'record': quest_record('biohazard'),
    'bank': 'nearest',
    'owns_inventory': True,
    'read_progress': read_biohazard_progress,
    'sustain': Record({'foods': ['Lobster', 'Swordfish', 'Tuna'], 'eat_below_hp': 0.5}),
    'decide': decide,
})
