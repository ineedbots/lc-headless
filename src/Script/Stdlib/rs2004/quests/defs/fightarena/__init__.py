"""Ported from rs2b0t's src/bot/api/ai/quests/defs/fightarena/index.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.defs.fightarena.areas import FA_NPC, FA_OBJ, FA_TILE, pocket_of
from rs2004.quests.defs.fightarena.fights import FA_FIGHT
from rs2004.quests.defs.fightarena.journal import FA_STAGE, read_fight_arena_stage
from rs2004.quests.defs.fightarena.legs import enter_arena_by_door2, enter_arena_by_guard, enter_building, fight_with_release, flee_arena, leave_building, search_chest, talk_and_land, talk_by_id, unlock_jeremy, unwearable, wear_khazard
from rs2004.quests.exec.primitives import NpcStop, talk_strict
from rs2004.quests.strike import STRIKE_RUNES, prepare_strikes
from rs2004.traversal import traversal
from rs2004.quests.engine.types import QuestModule
from rs2004.quests.data import quest_record

__all__ = ['KIT_KEEP', 'kit_wanted', 'decide', 'fightarena']

LADY_SERVIL = NpcStop('Lady Servil', FA_TILE.LADY_SERVIL, 8, ['Can I help you?', 'Yes'])


def held(snap, id):
    return ((snap.inv_ids.get(id) if snap.inv_ids.get(id) is not None else 0)) > 0


def worn(snap, id):
    return ((id in snap.worn_ids) if (id in snap.worn_ids) is not None else False)


def disguised(snap):
    return worn(snap, FA_OBJ.HELMET) or worn(snap, FA_OBJ.ARMOUR)


# Why: door1 lets one piece through, but the drunk guard's `~wearing_khazard_armour` wants both, so half a disguise loops at him forever.
def has_both(snap):
    return (held(snap, FA_OBJ.HELMET) or worn(snap, FA_OBJ.HELMET)) and (held(snap, FA_OBJ.ARMOUR) or worn(snap, FA_OBJ.ARMOUR))


def custom(name, run):
    return (Record({'kind': 'custom', 'name': name, 'run': run}))


CHEST = custom("search the guards' chest", search_chest)
WEAR_DISGUISE = custom('wear the Khazard disguise', wear_khazard)
ENTER_BUILDING = custom('enter the arena building', enter_building)
LEAVE_BUILDING = custom('leave the arena building', leave_building)
ENTER_ARENA = custom('enter the arena', enter_arena_by_door2)
KNOCK_FOR_GUARD = custom('knock for the arena guard', enter_arena_by_guard)
UNLOCK_JEREMY = custom("unlock Jeremy's cell", unlock_jeremy)
FLEE = custom('run from General Khazard', flee_arena)
DRUNK_GUARD = custom('talk to the drunk guard', lambda log: talk_by_id(FA_NPC.DRUNK_GUARD, ['Do you still fancy a drink?', 'Yes'], log, FA_TILE.DRUNK_GUARD))
CUTSCENE_MS = 60000
HENGRAD = custom('talk to Hengrad', lambda log: talk_and_land(FA_NPC.HENGRAD, 'arena', CUTSCENE_MS, log))
ASK_SERVILS = custom('ask the Servils about Khazard', lambda log: talk_by_id(FA_NPC.JEREMY_ARENA, [], log))
RELEASE_BEAST = custom('ask Justin what comes next', lambda log: talk_and_land(FA_NPC.JUSTIN, 'prisonCell', CUTSCENE_MS, log))


# Why: the barman runs no shop, and an unmatched option buys a beer by mistake.
def _fn1(log):
    _w2 = yield from traversal.walk_resilient(FA_TILE.BARMAN, radius=3, attempts=4, timeout_ms=180000, log=log)
    if not (_w2):
        return False
    _result3 = yield from talk_strict('Khazard barman', ["I'd like a Khali brew please."], log)
    return _result3


BUY_BREW = custom('buy a Khali brew', _fn1)
# Why: `jeremy_servil_arena` is the one who queues the ogre, and Justin is the one who opens the scorpion's and Bouncer's gates.
FIGHT_OGRE = custom(f'fight {FA_FIGHT.ogre.what}', lambda log: fight_with_release(FA_FIGHT.ogre, FA_NPC.JEREMY_ARENA, log))
FIGHT_SCORPION = custom(f'fight {FA_FIGHT.scorpion.what}', lambda log: fight_with_release(FA_FIGHT.scorpion, FA_NPC.JUSTIN, log))
FIGHT_BOUNCER = custom(f'fight {FA_FIGHT.bouncer.what}', lambda log: fight_with_release(FA_FIGHT.bouncer, FA_NPC.JUSTIN, log))
# Why: the queue keeps its gear banked between quests, so a bot that walks in wearing nothing punches a level-137 dog for 116 hitpoints.
# Why: Bouncer's damagetype is stab and its defences are flat, so a scimitar is as good as anything and faster than a two-hander.
TIERS = ['rune', 'adamant', 'mithril', 'black', 'steel', 'iron', 'bronze']
# Why: chainbody outranks platebody because rune plate wants Dragon Slayer complete and refuses in silence.
KIT_SLOTS = [
    Record({'kinds': ['scimitar', 'longsword', 'battleaxe', 'mace', 'sword']}),
    Record({'kinds': ['chainbody', 'platebody']}),
    Record({'kinds': ['platelegs', 'plateskirt']}),
    Record({'kinds': ['full helm', 'med helm']}),
    Record({'kinds': ['kiteshield', 'sq shield']}),
]
_flat4 = []
for _slot in KIT_SLOTS:
    _flat4.extend(_slot.kinds)


KIT_KEEP = _flat4


def wearing_kind(snap, kinds):
    for name in snap.worn:
        if any([name.endswith(kind) for kind in kinds]):
            return True
    return False


def best_for_slot(snap, kinds):
    for tier in TIERS:
        for kind in kinds:
            name = f'{tier} {kind}'
            if (name in unwearable):
                continue
            _v5 = snap.bank.get(name)
            if ((_v5 if _v5 is not None else 0)) > 0 or ((snap.inv.get(name) if snap.inv.get(name) is not None else 0)) > 0:
                return name[0].upper() + name[1:]
    return None


def kit_wanted(snap):
    """The best melee kit the account owns for the slots it has not filled."""
    out = []
    for _item6 in KIT_SLOTS:
        kinds = _item6.kinds
        if wearing_kind(snap, kinds):
            continue
        # Why: a two-hander would take the shield slot with it, and none of the weapon kinds here is one.
        pick = best_for_slot(snap, kinds)
        if pick:
            out.append(pick)
    return out


def outside_step(snap, stage):
    if stage <= FA_STAGE.NOT_STARTED or stage >= FA_STAGE.FREED_SERVILS:
        return Record({'kind': 'talk', 'stop': LADY_SERVIL})
    if stage < FA_STAGE.DEFEATED_BOUNCER:
        runes = prepare_strikes(snap, ['khazard helmet', 'khazard armour', 'khazard cell keys', 'khali brew'])
        if runes:
            return runes
    if stage >= FA_STAGE.SENT_JAIL:
        return KNOCK_FOR_GUARD
    if not has_both(snap):
        return CHEST
    if stage == FA_STAGE.SPOKEN_DRUNKGUARD and not held(snap, FA_OBJ.BREW):
        return BUY_BREW
    if not disguised(snap):
        return WEAR_DISGUISE
    return ENTER_BUILDING


def building_step(snap, stage):
    # Why: from stage 9 the arena is entered through the guard at door1, and door2 refuses anyone coming from inside the building.
    if stage >= FA_STAGE.SENT_JAIL:
        return LEAVE_BUILDING
    if stage >= FA_STAGE.ENTERED_OGRE_FIGHT:
        return ENTER_ARENA
    if stage == FA_STAGE.GIVEN_KHALI_BREW:
        # Why: a death drops the keys, and the drunk guard hands out a spare set below stage 6.
        if not held(snap, FA_OBJ.KEYS):
            return (DRUNK_GUARD if disguised(snap) else WEAR_DISGUISE)
        return UNLOCK_JEREMY
    if (stage == FA_STAGE.SPOKEN_DRUNKGUARD and not held(snap, FA_OBJ.BREW)) or not has_both(snap):
        return LEAVE_BUILDING
    if not disguised(snap):
        return WEAR_DISGUISE
    return DRUNK_GUARD


def arena_step(_snap, stage):
    if stage >= FA_STAGE.FREED_SERVILS:
        return FLEE
    if stage == FA_STAGE.DEFEATED_BOUNCER:
        return ASK_SERVILS
    if stage == FA_STAGE.DEFEATED_SCORPION:
        return FIGHT_BOUNCER
    if stage == FA_STAGE.SENT_JAIL:
        return FIGHT_SCORPION
    if stage == FA_STAGE.DEFEATED_OGRE:
        return RELEASE_BEAST
    return FIGHT_OGRE


def decide(snap):
    if snap.journal == 'complete':
        return Record({'kind': 'done'})
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    stage = snap.stage
    if stage is None:
        return Record({'kind': 'wait', 'reason': 'Fight Arena stage unavailable'})
    if stage >= FA_STAGE.COMPLETE:
        return Record({'kind': 'done'})
    where = pocket_of(snap.tile)
    if where == 'jeremyCell':
        return Record({'kind': 'wait', 'reason': "standing inside Jeremy's cell — nothing routes out"})
    if where == 'prisonCell':
        return HENGRAD
    if where == 'arena':
        return arena_step(snap, stage)
    if where == 'building':
        return building_step(snap, stage)
    return outside_step(snap, stage)


# Why: the fights are back to back with no bank between the jail and the escape, so the pack carries every meal the quest gets.
FOOD = 8
fightarena = QuestModule(**{
    'record': quest_record('arena'),
    'pray': Record({'protect': 'melee', 'potions': 2}),
    'bank': FA_TILE.YANILLE_BANK,
    'food': FOOD,
    'grind': ['Khazard Ogre', 'Khazard Scorpion', 'Bouncer'],
    'tools': ['khazard helmet', 'khazard armour', 'khazard cell keys', 'khali brew', 'coins'] + list(STRIKE_RUNES) + list(KIT_KEEP),
    'food_ready': lambda snap: ((snap.stage if snap.stage is not None else 0)) >= FA_STAGE.DEFEATED_BOUNCER or prepare_strikes(snap) is None,
    'read_stage': read_fight_arena_stage,
    'sustain': Record({'foods': ['Lobster', 'Swordfish', 'Shark', 'Tuna'], 'eat_below_hp': 0.6}),
    'warn_readiness': lambda: 'Fight Arena ends on Bouncer — level 137, 116 hitpoints, 120 attack and defence',
    'decide': decide,
})
