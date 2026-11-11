"""Ported from rs2b0t's src/bot/api/ai/quests/defs/heroquest/partner.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.partner_handoff import run_handoff as run_partner_handoff
from rs2004.quests.defs.heroquest.areas import HERO_ID, HERO_NAMED, HERO_TILE
from rs2004.quests.defs.heroquest.config import hero_config
from rs2004.quests.defs.heroquest.doors import return_to_street
from rs2004.quests.defs.heroquest.journal import HERO_STAGE

__all__ = ['hero_handoff_state', 'LURE_RETRIES_BEFORE_REFETCH', 'reset_hero_handoff_state', 'should_fetch_key', 'decide_hero_handoff', 'run_hero_handoff', 'hero_handoff_step']

# Why: Grip re-issues the spare whenever `~obj_gettotal(misc_key)` reads 0, so the flag stops a bot trading keys forever and the lure counter re-opens it for a rival that died holding one.
# Why: session scope is enough; a restart fetches one more key, which is correct work.
hero_handoff_state = Record({'gave_key': False, 'lure_failures': 0})
LURE_RETRIES_BEFORE_REFETCH = 3


def reset_hero_handoff_state():
    hero_handoff_state.gave_key = False
    hero_handoff_state.lure_failures = 0


def should_fetch_key(state=None):
    """True while the Black Arm bot should go back to Grip for a spare key before luring him."""
    if state is None:
        state = hero_handoff_state
    return not state.gave_key or state.lure_failures >= LURE_RETRIES_BEFORE_REFETCH


# Why: `open_and_close_door` teleports the actor and re-shuts in 3 ticks, so the door opens for nobody else: the tradeable spare key goes over and the untradeable keyring comes off the floor.
def decide_hero_handoff(gang, stage, has_key, candlesticks, partner_configured, ready, partner_stage=None, partner_has_key=None):
    """Who owes whom, from the snapshot alone."""
    if not partner_configured:
        return None
    if gang == 'blackarm':
        # Why: Grip re-issues the spare whenever `~obj_gettotal` reads 0, so giving it away costs nothing.
        if stage >= HERO_STAGE.BLACKARM_PAPERS_GIVEN and stage < HERO_STAGE.BLACKARM_ARMBAND and has_key and partner_has_key != True and (partner_stage is None or partner_stage < HERO_STAGE.PHOENIX_KILLED_GRIP):
            return 'give-key'
        # Why: The chest gives two candlesticks and refuses while one is held or banked; one is reserved for the partner.
        if stage >= HERO_STAGE.BLACKARM_LOOTED and stage < HERO_STAGE.BLACKARM_ARMBAND and candlesticks >= 2:
            return 'give-candlestick'
        return None
    # Why: the key is only useful with a bow already worn, and the walk to fetch one afterwards starts in Brimhaven, whose nearest bank is Ardougne, a fare each way.
    if stage == HERO_STAGE.PHOENIX_CHARLIE and not has_key and ready:
        return 'take-key'
    if stage == HERO_STAGE.PHOENIX_KILLED_GRIP and candlesticks == 0:
        return 'take-candlestick'
    return None


def item_for(handoff):
    if handoff == 'give-key':
        return Record({'id': HERO_ID.MISC_KEY, 'name': HERO_NAMED.MISC_KEY, 'giving': True})
    elif handoff == 'take-key':
        return Record({'id': HERO_ID.MISC_KEY, 'name': HERO_NAMED.MISC_KEY, 'giving': False})
    elif handoff == 'give-candlestick':
        return Record({'id': HERO_ID.CANDLESTICK, 'name': HERO_NAMED.CANDLESTICK, 'giving': True})
    elif handoff == 'take-candlestick':
        return Record({'id': HERO_ID.CANDLESTICK, 'name': HERO_NAMED.CANDLESTICK, 'giving': False})


def run_hero_handoff(handoff, log):
    # Why: every trade meets on the street, and 5 of the 6 rooms this quest works in are pockets the navigator has no edge out of.
    _w1 = yield from return_to_street(log)
    if not (_w1):
        return False
    want = item_for(handoff)
    moved = yield from run_partner_handoff(Record({
        'partner': hero_config.partner,
        'rendezvous': HERO_TILE.RENDEZVOUS,
        'id': want.id,
        'name': want.name,
        'giving': want.giving,
        'label': handoff,
        'log': log,
    }))
    if moved and handoff == 'give-key':
        hero_handoff_state.gave_key = True
        hero_handoff_state.lure_failures = 0
    return moved


def hero_handoff_step(handoff):
    return Record({
        'kind': 'custom',
        'cooperative': True,
        'name': f'{handoff} with {hero_config.partner}',
        'run': lambda log: run_hero_handoff(handoff, log),
    })
