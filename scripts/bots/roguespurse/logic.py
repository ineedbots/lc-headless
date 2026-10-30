"""Ported from rs2b0t's src/bot/scripts/RoguesPurse/RoguesPurseLogic.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.defs.junglepotion import JP_STAGE, JUNGLE_POTION_QUEST

__all__ = ['IDENTIFY_LEVEL', 'IDENTIFY_XP', 'WALL_STAGE', 'IDENTIFY_OP', 'DROP_OP', 'COINS', 'FARE', 'FARE_FLOAT', 'is_stage_refusal', 'is_level_refusal', 'check_gates', 'detour_cost', 'rank_banks_by_detour', 'plan_cycle']

IDENTIFY_LEVEL = 3
IDENTIFY_XP = 2.5
WALL_STAGE = JP_STAGE.GET_ROGUES_PURSE
IDENTIFY_OP = 'Identify'
DROP_OP = 'Drop'
COINS = 'Coins'
# Why: the Karamja ship is a `Pay-fare` SpecialCrossing, and the navigator prunes crossings it cannot pay for.
# Why: an empty pack therefore makes the island read as `unreachable` rather than as "you are broke".
# Why: this must stay in step with `nav/data/specialCrossings.ts`.
FARE = 30
FARE_FLOAT = 100


def is_stage_refusal(text):
    """The wall refused the search: `%junglepotion` is below {@link WALL_STAGE}."""
    return ' '.join(text.lower().replace(',', '').split()).startswith('unfortunately you find nothing of interest')


def is_level_refusal(text):
    """The identify refused: Herblore is below {@link IDENTIFY_LEVEL}."""
    return 'you cannot identify this herb' in text.lower()


RUN_THE_QUEST = f'run AIOQuester with {JUNGLE_POTION_QUEST} first'


def check_gates(state):
    herblore_level = state.herblore_level
    stage = state.stage
    """Both engine gates, checked before the walk to Karamja rather than after it."""
    if herblore_level < IDENTIFY_LEVEL:
        return Record({
            'ok': False,
            'reason': f'Herblore {IDENTIFY_LEVEL} required to identify a Rogues purse (have {herblore_level})' + ' — identify guams elsewhere first',
        })
    if stage is None:
        return Record({'ok': False, 'reason': f'could not read the {JUNGLE_POTION_QUEST} journal'})
    if stage >= WALL_STAGE:
        return Record({'ok': True})
    if stage <= JP_STAGE.NOT_STARTED:
        return Record({'ok': False, 'reason': f'{JUNGLE_POTION_QUEST} not started — {RUN_THE_QUEST}'})
    return Record({
        'ok': False,
        'reason': f'Trufitus hasn\'t asked for the Rogues purse yet ({JUNGLE_POTION_QUEST} stage {stage}, ' + f'need {WALL_STAGE}) — {RUN_THE_QUEST}',
    })


def dist(a, b):
    return ((b.x - a.x) ** 2 + (b.z - a.z) ** 2) ** 0.5


# Why: a bank behind us is a there-and-back detour even when it is the closest one.
# Why: from the Lumbridge death spawn Al Kharid is nearest, but it is 50 tiles the wrong way and the walk afterwards comes straight back past Draynor.
def detour_cost(here, bank, dest):
    """Cost of banking at `bank` on the way from `here` to `dest`."""
    return dist(here, bank) + dist(bank, dest)


def rank_banks_by_detour(here, dest, banks):
    """Candidate banks for the fare trip, cheapest detour first."""
    return sorted(list(banks), key=lambda a: detour_cost(here, bank_tile(a), dest))


# Why: `opheld` runs inline during decode while `oploc` resolves in the movement phase, so identify and drop act on what the pack already holds and the search lands after them.
# Why: four user events, inside the engine's five.
def plan_cycle(state):
    continue_pending = state.continue_pending
    unids = state.unids
    identified = state.identified
    free_slots = state.free_slots
    """One tick's packets."""
    plan = []
    if continue_pending:
        plan.append('continue')
    if unids > 0:
        plan.append('identify')
    if identified > 0:
        plan.append('drop')
    if free_slots > 0:
        plan.append('search')
    return plan


def bank_tile(row):
    tile = row.get('tile') if isinstance(row, dict) else row.tile
    return Record(tile) if isinstance(tile, dict) else tile
