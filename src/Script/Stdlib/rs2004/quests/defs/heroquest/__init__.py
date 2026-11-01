"""Ported from rs2b0t's src/bot/api/ai/quests/defs/heroquest/index.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.items import inventory
from rs2004.quests.data import quest_record
from rs2004.quests.defs.heroquest.areas import ACHIETTIES, HERO_ID, HERO_NAMED, TAVERLEY_HOP_DOWN, TAVERLEY_HOP_UP, in_brimhaven_hq, in_deep_dungeon, in_garden, in_kitchen, in_mansion, in_side_room, in_treasure_room, in_velrak_cell, in_yard, on_entrana
from rs2004.quests.defs.heroquest.blackarm import blackarm_armband_step
from rs2004.quests.defs.heroquest.config import hero_config, hero_gang, partner_configured
from rs2004.quests.defs.heroquest.doors import return_to_street
from rs2004.quests.defs.heroquest.eel import eel_step, free_velrak, leave_deep_dungeon
from rs2004.quests.defs.heroquest.feather import feather_step
from rs2004.quests.defs.heroquest.journal import HERO_STAGE, read_hero_quest_progress
from rs2004.quests.defs.heroquest.partner import decide_hero_handoff, hero_handoff_step
from rs2004.quests.defs.heroquest.phoenix import phoenix_armband_step, snipe_kit_step
from rs2004.quests.defs.heroquest.state import anywhere, banked_id, held_id
from rs2004.quests.engine.types import QuestModule
from rs2004.quests.exec.legs import talk_and_close, talk_until

__all__ = ['in_sealed_pocket', 'decide', 'heroquest']

HAND_IN = [
    Record({'id': HERO_ID.FEATHER, 'name': HERO_NAMED.FEATHER}),
    Record({'id': HERO_ID.LAVA_EEL, 'name': HERO_NAMED.LAVA_EEL}),
    Record({'id': HERO_ID.ARMBAND, 'name': HERO_NAMED.ARMBAND}),
]


def hand_in_step(snap):
    # Why: `~send_quest_complete` reads `inv_total(inv, ...)`, so a banked feather doesn't count.
    for item in HAND_IN:
        if held_id(snap, item.id) == 0:
            if banked_id(snap, item.id) > 0:
                return Record({'kind': 'withdraw', 'items': [{'name': item.name, 'qty': 1, 'id': item.id}]})
            return Record({'kind': 'wait', 'reason': f'no {item.name} to hand in'})
    return Record({
        'kind': 'custom',
        'name': 'give Achietties the three items',
        'run': lambda log: talk_until(ACHIETTIES, ACHIETTIES.prefer, lambda: inventory.count_by_id(HERO_ID.ARMBAND) == 0, log, 60000),
    })


def in_sealed_pocket(snap):
    """The 6 Brimhaven pockets, none of which the navigator has an edge out of."""
    return in_brimhaven_hq(snap.tile) or in_mansion(snap.tile) or in_treasure_room(snap.tile) or in_kitchen(snap.tile) or in_garden(snap.tile) or in_yard(snap.tile) or in_side_room(snap.tile)


# Why: a bank, shop or booth is a walk the navigator plans, and from inside a sealed pocket every such plan reads `unreachable`. The custom legs cross their own doors; these steps can't.
NEEDS_STREET = set(['buy', 'withdraw', 'deposit', 'scan_bank', 'mine_rock'])
# Why: `no path to (2793,3180,0): unreachable without 30x Coins`: the Ardougne ferry is 30 coins and the legs between purchases carry none, so the quest holds a float.
LOW_COINS = 200
COIN_TOP_UP = 10000


def decide(snap):
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    if snap.journal == 'complete':
        return Record({'kind': 'done'})
    _v1 = (snap.progress.stage if snap.progress is not None else None)
    stage = (_v1 if _v1 is not None else snap.stage)
    if stage is None:
        return Record({'kind': 'wait', 'reason': 'quest stage not readable'})
    # Why: `ownsInventory` skips the engine's provisioning, so nothing else opens a booth and an armband or feather banked by an earlier run stays invisible until this read.
    if not snap.bank_known:
        return egress(snap, Record({'kind': 'scan_bank'}))
    if held_id(snap, HERO_ID.COINS) < LOW_COINS and snap.bank_coins > 0:
        return egress(snap, Record({
            'kind': 'withdraw',
            'items': [{'name': HERO_NAMED.COINS, 'qty': min(COIN_TOP_UP, snap.bank_coins), 'id': HERO_ID.COINS}],
        }))
    if stage == HERO_STAGE.NOT_STARTED:
        return Record({
            'kind': 'custom',
            'name': 'apply to the Heroes Guild',
            'run': lambda log: talk_and_close(ACHIETTIES, ACHIETTIES.prefer, log),
        })
    gang = hero_gang()
    # Why: the trades outrank the gang legs: the rival is waiting at the rendezvous and every other leg on this side is blocked until the key or the candlestick has moved.
    handoff = decide_hero_handoff(gang, stage, held_id(snap, HERO_ID.MISC_KEY) > 0, held_id(snap, HERO_ID.CANDLESTICK), partner_configured(), gang != 'phoenix' or snipe_kit_step(snap) is None)
    if handoff:
        return hero_handoff_step(handoff)
    if anywhere(snap, HERO_ID.ARMBAND) == 0:
        armband = (phoenix_armband_step(snap, stage) if gang == 'phoenix' else blackarm_armband_step(snap, stage))
        if armband:
            return egress(snap, armband)
        return Record({
            'kind': 'wait',
            'reason': (f'waiting on {hero_config.partner} at stage {stage}' if partner_configured() else 'Heroes Quest needs a rival-gang partner — set heroPartner'),
        })
    # Why: Entrana is a one-ferry island with no walkable route home, so a bot standing on it settles the feather leg before the chain order gets a say.
    if on_entrana(snap.tile):
        _v2 = feather_step(snap)
        return (_v2 if _v2 is not None else hand_in_step(snap))
    _v3 = eel_step(snap)
    _v4 = (_v3 if _v3 is not None else feather_step(snap))
    return egress(snap, (_v4 if _v4 is not None else hand_in_step(snap)))


# Why: a restart mid-leg can leave a bot in either Taverley pocket, and both doors open from the inside without a key, so the way out is never the way in.
def egress(snap, step):
    if not (step.kind in NEEDS_STREET):
        return step
    if in_deep_dungeon(snap.tile):
        return Record({'kind': 'custom', 'name': 'leave the deep dungeon', 'run': leave_deep_dungeon})
    if in_velrak_cell(snap.tile):
        return Record({'kind': 'custom', 'name': "leave Velrak's cell", 'run': free_velrak})
    if not in_sealed_pocket(snap):
        return step
    return Record({'kind': 'custom', 'name': 'leave the sealed Brimhaven pocket', 'run': return_to_street})


def resumes_at(t):
    """The sealed Brimhaven pockets, Taverley's two and Entrana, whose only ways out are this quest's own."""
    return in_brimhaven_hq(t) or in_mansion(t) or in_treasure_room(t) or in_kitchen(t) or in_garden(t) or in_yard(t) or in_side_room(t) or in_deep_dungeon(t) or in_velrak_cell(t) or on_entrana(t)


heroquest = QuestModule(**{
    'record': quest_record('hero'),
    'pray': Record({'protect': 'melee', 'potions': 2}),
    'bank': 'nearest',
    'owns_inventory': True,
    'hops': [TAVERLEY_HOP_DOWN, TAVERLEY_HOP_UP],
    'grind': ['Chaos druid', 'Grip', 'Ice Queen', 'Jailer'],
    'tools': [
    HERO_NAMED.ICE_GLOVES,
    HERO_NAMED.FEATHER,
    HERO_NAMED.LAVA_EEL,
    HERO_NAMED.ARMBAND,
    HERO_NAMED.OILY_ROD,
    HERO_NAMED.FISHING_BAIT,
    HERO_NAMED.CANDLESTICK,
    HERO_NAMED.MISC_KEY,
    HERO_NAMED.JAIL_KEY,
    HERO_NAMED.DUSTY_KEY,
],
    'sustain': Record({'foods': ['Lobster', 'Swordfish', 'Tuna'], 'eat_below_hp': 0.5}),
    'read_progress': read_hero_quest_progress,
    'resume_at': resumes_at,
    'warn_readiness': lambda: (None if partner_configured() else "Hero's Quest needs a rival-gang partner — the armband cannot be earned alone"),
    'decide': decide,
})
