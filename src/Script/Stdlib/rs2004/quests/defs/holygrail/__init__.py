"""Ported from rs2b0t's src/bot/api/ai/quests/defs/holygrail/index.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.data import quest_record
from rs2004.quests.engine.types import QuestModule
from rs2004.quests.defs.holygrail.areas import GALAHAD, GRAIL_TILE, HIGH_PRIEST, ITEM, KING_ARTHUR_FINISH, KING_ARTHUR_START, LADY_OF_THE_LAKE, east_of_titan, in_blighted_realm, in_fisher_realm, in_renewed_realm
from rs2004.quests.defs.holygrail.armour import ARMOUR_KEEP, armour_wanted
from rs2004.quests.defs.holygrail.journal import GRAIL_STAGE, read_holy_grail_progress
from rs2004.quests.defs.holygrail.legs import draynor_whistles, free_percival, merlin_leg, realm_leg, take_grail, unequip_all, wear_armour, whistle_in, whistle_out
from rs2004.quests.engine.provisioning import gp_short
from rs2004.quests.food import FOOD_FLOAT, quest_food

__all__ = ['excalibur_plan', 'decide', 'holygrail']

EXCALIBUR_PRICE = 500


def held(snap, name):
    _v1 = snap.inv.get(name.lower())
    return (_v1 if _v1 is not None else 0)


def banked(snap, name):
    _v2 = (snap.bank.get(name.lower()) if snap.bank is not None else None)
    return (_v2 if _v2 is not None else 0)


def worn(snap, name):
    return (name.lower() in snap.worn)


def custom(name, run):
    return Record({'kind': 'custom', 'name': name, 'run': run})


def excalibur_plan(snap, _need=None):
    """Merlin's Crystal doesn't consume Excalibur, so the bank almost always has it."""
    if held(snap, ITEM.EXCALIBUR) > 0 or worn(snap, ITEM.EXCALIBUR):
        return Record({'kind': 'equip', 'item': ITEM.EXCALIBUR})
    if not snap.bank_known:
        return Record({'kind': 'scan_bank'})
    if banked(snap, ITEM.EXCALIBUR) > 0:
        return Record({'kind': 'withdraw', 'items': [{'name': ITEM.EXCALIBUR, 'qty': 1}]})
    if held(snap, ITEM.COINS) >= EXCALIBUR_PRICE:
        return Record({'kind': 'talk', 'stop': LADY_OF_THE_LAKE})
    if gp_short(snap, EXCALIBUR_PRICE) > 0:
        return Record({
            'kind': 'wait',
            'reason': f'need {EXCALIBUR_PRICE} gp to buy Excalibur back from the Lady of the Lake',
        })
    return Record({'kind': 'withdraw', 'items': [{'name': ITEM.COINS, 'qty': EXCALIBUR_PRICE}]})


# Why: the monk's search covers held and worn alike, so the pack has to be down to coin and food before walking to the boat.
ENTRANA_KEEP = [ITEM.COINS.lower()]


def entrana_spillover(snap, food):
    keep = (list(ENTRANA_KEEP) + [food.lower()] if food else ENTRANA_KEEP)
    return [name for name in list(snap.inv.keys()) if not (name in keep)]


# Why: the gear comes off before the deposit; stripping after puts it straight back in the pack and buys a second bank trip.
def entrana_leg(snap, food):
    if len(snap.worn) > 0:
        return custom('remove weapons and armour for Entrana', unequip_all)
    if len(entrana_spillover(snap, food)) > 0:
        return Record({
            'kind': 'deposit',
            'keep': ([ITEM.COINS, food] if food else [ITEM.COINS]),
            'bank': GRAIL_TILE.DRAYNOR_BANK,
            'exact_keep': True,
        })
    return Record({'kind': 'talk', 'stop': HIGH_PRIEST})


def arm_step(snap):
    """Re-arm after the Entrana strip: Excalibur first, then whatever armour the bank holds."""
    if not worn(snap, ITEM.EXCALIBUR):
        if held(snap, ITEM.EXCALIBUR) == 0:
            return excalibur_plan(snap)
        return Record({'kind': 'equip', 'item': ITEM.EXCALIBUR})
    wanted = armour_wanted(snap)
    if len(wanted) == 0:
        return None
    carried = [name for name in wanted if held(snap, name) > 0]
    if len(carried) > 0:
        return custom(f"wear {', '.join(carried)}", lambda log: wear_armour(carried, log))
    return Record({'kind': 'withdraw', 'items': [{'name': name, 'qty': 1} for name in wanted]})


def napkin_step(snap):
    if held(snap, ITEM.NAPKIN) > 0:
        return None
    if banked(snap, ITEM.NAPKIN) > 0:
        return Record({'kind': 'withdraw', 'items': [{'name': ITEM.NAPKIN, 'qty': 1}]})
    return Record({'kind': 'talk', 'stop': GALAHAD})


# Why: the whistles are the way in and the way home, and the door only drops them for a character carrying the napkin, so every leg that needs one has to check the cloth first.
# Why: Galahad only replaces a lost napkin at stages 4 and 7, so past that a missing one parks with a reason.
def whistle_step(snap, want):
    """Withdraw the napkin if needed, then fetch whistles; null once `want` are in the pack."""
    if held(snap, ITEM.WHISTLE) >= want:
        return None
    if held(snap, ITEM.NAPKIN) == 0:
        if banked(snap, ITEM.NAPKIN) > 0:
            return Record({'kind': 'withdraw', 'items': [{'name': ITEM.NAPKIN, 'qty': 1}]})
        return Record({
            'kind': 'wait',
            'reason': 'no Holy table napkin, and Galahad replaces one only before Sir Percival is the errand',
        })
    return custom('collect Magic whistles from Draynor Manor', lambda log: draynor_whistles(2, log))


def crossing_leg(snap):
    """Stages 4 and 7 are the same errand: arm, fetch 2 whistles, cross, and see the Fisher King."""
    if in_blighted_realm(snap.tile):
        # Excalibur is needed on the far side of the titan and cannot be fetched from in here.
        if east_of_titan(snap.tile) and not worn(snap, ITEM.EXCALIBUR):
            if held(snap, ITEM.EXCALIBUR) > 0:
                return Record({'kind': 'equip', 'item': ITEM.EXCALIBUR})
            return custom('leave the realm to fetch Excalibur', whistle_out)
        return custom('cross the realm to the Fisher King', realm_leg)
    if in_renewed_realm(snap.tile):
        return custom('leave the renewed realm', whistle_out)
    napkin = napkin_step(snap)
    if napkin:
        return napkin
    arm = arm_step(snap)
    if arm:
        return arm
    # Why: 2, one for Sir Percival's ride home and one for the only way out of the realm.
    _v3 = whistle_step(snap, 2)
    return (_v3 if _v3 is not None else custom("blow the whistle at Karamja's six heads", whistle_in))


def percival_leg(snap):
    if in_fisher_realm(snap.tile):
        return custom('leave the realm to find Sir Percival', whistle_out)
    _v4 = whistle_step(snap, 1)
    return (_v4 if _v4 is not None else custom('free Sir Percival from the Goblin Village sacks', free_percival))


def grail_leg(snap):
    if held(snap, ITEM.GRAIL) > 0:
        return (custom('carry the Grail out of the realm', whistle_out) if in_fisher_realm(snap.tile) else Record({'kind': 'talk', 'stop': KING_ARTHUR_FINISH}))
    if in_renewed_realm(snap.tile):
        return custom('take the Holy Grail from the round table', take_grail)
    if in_blighted_realm(snap.tile):
        return custom('leave the blighted realm', whistle_out)
    _v5 = whistle_step(snap, 1)
    return (_v5 if _v5 is not None else custom("blow the whistle at Karamja's six heads", whistle_in))


def selected_food():
    food = (quest_food.name.strip() if quest_food.name is not None else None)
    return (food if food else None)


def decide(snap, food=None):
    if food is None:
        food = selected_food()
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    if snap.journal == 'complete':
        return Record({'kind': 'done'})
    _v6 = (snap.progress.stage if snap.progress is not None else None)
    stage = (_v6 if _v6 is not None else snap.stage)
    if stage is None:
        return Record({'kind': 'wait', 'reason': 'quest stage not readable'})
    # Why: `ownsInventory` is off, but the armour planner reads the bank, and an unread bank looks empty.
    if not snap.bank_known and not in_fisher_realm(snap.tile):
        return Record({'kind': 'scan_bank'})
    if stage == GRAIL_STAGE.NOT_STARTED:
        return Record({'kind': 'talk', 'stop': KING_ARTHUR_START})
    elif stage == GRAIL_STAGE.STARTED:
        return custom("talk to Merlin in Camelot's workshop", merlin_leg)
    elif stage == GRAIL_STAGE.SPOKEN_MERLIN:
        return entrana_leg(snap, food)
    elif stage in [GRAIL_STAGE.SPOKEN_CRONE, GRAIL_STAGE.FAILED_TITAN]:
        return crossing_leg(snap)
    elif stage == GRAIL_STAGE.FINDING_PERCIVAL:
        return percival_leg(snap)
    elif stage == GRAIL_STAGE.GIVEN_WHISTLE:
        return grail_leg(snap)
    else:
        return Record({'kind': 'wait', 'reason': f'unmapped Holy Grail stage {stage}'})


holygrail = QuestModule(**{
    'record': quest_record('grail'),
    'bank': 'nearest',
    'food': FOOD_FLOAT,
    'grind': ['Black Knight Titan'],
    'tools': [ITEM.EXCALIBUR.lower(), ITEM.NAPKIN.lower(), ITEM.WHISTLE.lower(), ITEM.BELL.lower(), ITEM.GRAIL.lower(), 'coins'] + list(ARMOUR_KEEP),
    'sustain': Record({'foods': ['Lobster', 'Swordfish', 'Tuna'], 'eat_below_hp': 0.5}),
    'gather': Record({'excalibur': excalibur_plan}),
    'read_progress': read_holy_grail_progress,
    # A restart inside the realm has no way to a bank but the whistle, which decide() blows when it's needed.
    'resume_at': in_fisher_realm,
    'warn_readiness': lambda: 'Holy Grail fights a level-120 Black Knight Titan (142 hp, 91 defence); the proven floor is 70 combat in rune with Lobsters',
    'decide': decide,
})
