"""Ported from rs2b0t's src/bot/api/ai/quests/defs/horror/index.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.tabs import quests
from rs2004.catalogs.record import Record
from rs2004.items import inventory
from rs2004.quests.barcrawl.run_barcrawl import ensure_barcrawl
from rs2004.quests.data import quest_record
from rs2004.quests.defs.horror.areas import GUNNJORN, HD_ID, HD_ITEM, HD_STAGE, HD_TILE, LARRISSA
from rs2004.quests.defs.horror.barcrawl import barcrawl_funds
from rs2004.quests.defs.horror.dungeon import exit_after_quest, in_cavern, in_lighthouse, in_postquest_cavern, open_wall_and_descend
from rs2004.quests.defs.horror.fight import fight_junior, fight_mother
from rs2004.quests.defs.horror.journal import HD_FLAG, read_horror_progress
from rs2004.quests.defs.horror.lighthouse import climb_to_light, descend_to_basement, enter_lighthouse, in_basement, in_quest_lighthouse, repair_bridge, repair_light
from rs2004.quests.defs.horror.supplies import HORROR_TOOLS, NAILS_NEEDED, PLANKS_NEEDED, banked_id, dungeon_kit, food_want, hammer, held_id, kit, make_room, nails, planks, rune_kit, sealed_area, warn_horror_readiness
from rs2004.quests.engine.types import QuestModule, has_flag
from rs2004.quests.exec.primitives import talk_through
from rs2004.traversal import traversal

__all__ = ['decide', 'horror']

def custom(name, run):
    return (Record({'kind': 'custom', 'name': name, 'run': run}))


# Why: Gunnjorn is inside the Barbarian Outpost course behind the gate and the pipe, and the gate's guard intercepts anyone without the 10-bar barcrawl.
def fetch_key(log):
    """Fetch Larrissa's spare key from her cousin Gunnjorn."""
    if inventory.count_by_id(HD_ID.KEY) > 0:
        return True
    _w1 = yield from ensure_barcrawl(log)
    if not (_w1):
        return False
    _w2 = yield from traversal.walk_resilient(HD_TILE.GUNNJORN, radius=4, attempts=4, timeout_ms=300000, log=log)
    if not (_w2):
        log('could not get through the outpost to Gunnjorn')
        return False
    yield from execution.delay_ticks(2)
    _w3 = yield from talk_through(GUNNJORN.npc, GUNNJORN.prefer, log)
    if not (_w3):
        return False
    _result4 = yield from execution.delay_until(lambda: inventory.count_by_id(HD_ID.KEY) > 0, 8000)
    return _result4


# Why: `smithNails` banks everything outside its KEEP list for 4 iron and 8 coal, and runes aren't on it, so this runs after the nails.
def teleport_runes(snap):
    """Runes, when hops are on and the pack is short."""
    return (rune_kit(snap) if traversal.teleports_enabled() else None)


# Why: every step banks before it shops since most accounts own a hammer and nails; hammer, nails and runes are Varrock errands and the planks are outpost spawns on the way to the lighthouse.
def bridge_kit(snap):
    """Everything the bridge repair consumes, in the order the map wants it."""
    if held_id(snap, HD_ID.HAMMER) == 0:
        return hammer(snap)
    # Nails before planks: the smithing leg banks the pack for ore, and a plank banked mid-leg is fetched twice.
    if held_id(snap, HD_ID.NAILS) < NAILS_NEEDED:
        return nails(snap)
    runes = teleport_runes(snap)
    if runes:
        return runes
    if held_id(snap, HD_ID.PLANK) < PLANKS_NEEDED:
        return planks(snap)
    return None


# Why: assembling the lighthouse load here crosses the causeway once; at stage 2 it's 3 times.
def before_the_door(snap):
    """Everything Larrissa wants before she opens the lighthouse, plus the load inside it."""
    if not has_flag(snap.progress, HD_FLAG.BRIDGE):
        _v5 = bridge_kit(snap)
        return (_v5 if _v5 is not None else custom('repair the bridge', repair_bridge))
    # Why: a resume past the bridge never enters `bridgeKit` and would walk the 10-bar tour, the leg hops pay for, with an empty pouch.
    runes = teleport_runes(snap)
    if runes:
        return runes
    if held_id(snap, HD_ID.KEY) == 0:
        if not snap.bank_known:
            return Record({'kind': 'scan_bank'})
        if banked_id(snap, HD_ID.KEY) > 0:
            return Record({'kind': 'withdraw', 'items': [{'name': HD_ITEM.KEY, 'qty': 1, 'id': HD_ID.KEY}]})
        # Why: The guard refuses a banked card, leaving the tour complete but the gate closed.
        if held_id(snap, HD_ID.BARCRAWL_CARD) == 0 and banked_id(snap, HD_ID.BARCRAWL_CARD) > 0:
            return Record({
                'kind': 'withdraw',
                'items': [{'name': HD_ITEM.BARCRAWL_CARD, 'qty': 1, 'id': HD_ID.BARCRAWL_CARD}],
            })
        _v6 = barcrawl_funds(snap)
        return (_v6 if _v6 is not None else custom("the barcrawl and Larrissa's key", fetch_key))
    short = dungeon_kit(snap, True)
    if short:
        return short
    return Record({'kind': 'talk', 'stop': LARRISSA})


# Why: the lighthouse, basement and cavern are sealed pockets linked by scripted teleports, and a death drops you on the mainland mid-stage, so every branch starts by locating the pocket.
def inside(snap, need_light, at_depth):
    """Route a branch by which sealed pocket the character is in."""
    if not sealed_area(snap.tile):
        short = dungeon_kit(snap, need_light)
        if short:
            return short
        return custom('enter the lighthouse', enter_lighthouse)
    return at_depth()


def _climb_and_repair(flags, log):
    climbed = yield from climb_to_light(log)
    if not climbed:
        return False
    result = yield from repair_light(flags, log)
    return result


def repair_the_light(snap):
    flags = snap.progress.flags if snap.progress is not None else set()
    step = custom('repair the lighthouse light', lambda log: _climb_and_repair(flags, log))
    return inside(snap, True, lambda: step)


def reach_the_cavern(snap, at_cavern):
    """Down the ladder, through the strange wall, and on to the juniors."""

    def _fn15():
        if in_cavern(snap.tile):
            return at_cavern
        if in_basement(snap.tile):
            return custom('open the strange wall', open_wall_and_descend)
        if in_quest_lighthouse(snap.tile) or (snap.tile is not None and snap.tile.level > 0):
            return custom('descend to the basement', descend_to_basement)
        return custom('enter the lighthouse', enter_lighthouse)
    return inside(snap, False, _fn15)


def decide(snap):
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    if snap.journal == 'complete':
        return Record({'kind': 'done'})
    _v16 = (snap.progress.stage if snap.progress is not None else None)
    stage = (_v16 if _v16 is not None else snap.stage)
    if stage is None:
        return Record({'kind': 'wait', 'reason': 'quest stage not readable'})
    # Why: upkeep never runs inside a sealed pocket, or a mid-fight top-up walks you back out of the cavern.
    if not sealed_area(snap.tile):
        room = make_room(snap, stage)
        if room:
            return room
        float_ = kit(snap, food_want(snap, stage))
        if float_:
            return float_
    if stage == HD_STAGE.NOT_STARTED:
        # Why: the bridge kit comes before Larrissa since the kit is Varrock and the outpost, on the way to the lighthouse, and nothing in it is quest-gated.
        # Why: `bridgeKit` checks the bank first and skips sourcing nails already owned.
        _v17 = bridge_kit(snap)
        return (_v17 if _v17 is not None else Record({'kind': 'talk', 'stop': LARRISSA}))
    elif stage == HD_STAGE.STARTED:
        return before_the_door(snap)
    elif stage in [HD_STAGE.ENTERED_LIGHTHOUSE, HD_STAGE.FIXING_LIGHTHOUSE]:
        return repair_the_light(snap)
    elif stage == HD_STAGE.REPAIRED_LIGHTHOUSE:
        return reach_the_cavern(snap, custom('kill the dagannoth junior', fight_junior))
    elif stage == HD_STAGE.DEFEATED_DAGJR:
        return reach_the_cavern(snap, custom('kill the Dagannoth mother', fight_mother))
    else:
        return Record({'kind': 'done'})


horror = QuestModule(**{
    'record': quest_record('horror'),
    'pray': Record({'protect': 'melee', 'potions': 2}),
    'bank': 'nearest',
    'tools': list(HORROR_TOOLS),
    'owns_inventory': True,
    'sustain': Record({'foods': ['Shark', 'Swordfish', 'Lobster', 'Tuna'], 'eat_below_hp': 0.6}),
    'warn_readiness': warn_horror_readiness,
    'read_progress': read_horror_progress,
    'recover': lambda tile: custom('leave the lighthouse for the mainland', exit_after_quest) if in_postquest_cavern(tile) or (in_lighthouse(tile) and quests.status('Horror from the Deep') == 'complete') else None,
    'exit': exit_after_quest,
    'decide': decide,
})
