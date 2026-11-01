"""Ported from rs2b0t's src/bot/api/ai/quests/defs/ikov/index.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.game import game
from rs2004.quests.data import quest_record
from rs2004.quests.defs.ikov.areas import ARROWS_WANTED, IKOV_FOODS, IKOV_NAME, IKOV_OBJ, IKOV_TILE, LUCIEN_START, ROOTS_WANTED, WINELDA_STOP, in_dark_room, in_guardian_temple, in_temple, in_trap_pit, on_winelda_ledge, west_of_bridge
from rs2004.quests.defs.ikov.dungeon import arrows_secured, boots_step, escape_pocket, pull_trap_lever, south_gate_open, stock_ice_arrows, temple_walk, unlock_south_gate, wear_fear_pendant, wearing_boots
from rs2004.quests.defs.ikov.fight import fight_fire_warrior, kill_lucien
from rs2004.quests.defs.ikov.gear import IKOV_GEAR_NAMES, RANGED_ARMOUR_NAMES, ranged_armour_step
from rs2004.quests.defs.ikov.journal import IKOV_STAGE, read_ikov_stage
from rs2004.quests.defs.ikov.supplies import held_or_banked, restock_step, sourcing_shortfall, supplies_step
from rs2004.quests.defs.ikov.temple import join_the_guardians, leave_the_far_side
from rs2004.quests.engine.types import QuestModule
from rs2004.quests.exec.primitives import talk_strict

__all__ = ['decide', 'ikov']

IKOV_ID = 'ikov'
IKOV_TOOLS = ['coins', 'candle', 'tinderbox', 'knife', 'iron axe', 'yew logs', 'flax', 'bow string', 'yew shortbow', 'ice arrows', 'boots of lightness', 'pendant', 'limpwurt root', 'lever', 'shiny key'] + list(IKOV_GEAR_NAMES)
WARRIOR_FOOD = 8
WARRIOR_FOOD_FLOOR = 2
# Why: the lava bridge weighs the pack, and stackables are free, so the trim is about the non-stackables the surface legs leave behind, the yew shortbow (3lb) and the iron axe most of all.
BRIDGE_KEEP = ['coins', 'candle', 'tinderbox', 'knife', 'pendant', 'boots of lightness', 'ice arrows', 'lever'] + list(IKOV_FOODS)


def held(snap, id):
    _v1 = (snap.inv_ids.get(id) if snap.inv_ids is not None else None)
    return (_v1 if _v1 is not None else 0)


def bridge_trim_step(snap):
    """Bank whatever the crossing cannot afford to carry, before the bot is underground with no booth."""
    return trim_step(snap, BRIDGE_KEEP)


ROOTS_KEEP = ['coins', 'pendant', 'limpwurt root'] + list(IKOV_FOODS)
# Why: keeping the farm's food leaves 19 slots for a 20-root withdraw, which retries until the watchdog fires.
FERRY_KEEP = ['coins', 'pendant', 'limpwurt root']


def roots_trim_step(snap, keep=None):
    if keep is None:
        keep = ROOTS_KEEP
    return trim_step(snap, keep)


def trim_step(snap, keep):
    spare = [name for name in list(list(snap.inv.keys())) if not any([(k in name) for k in keep])]
    if len(spare) == 0:
        return None
    return Record({'kind': 'deposit', 'keep': list(keep)})


def withdraw_for(snap, wanted):
    """Withdraw anything the next leg needs that the pack does not already hold."""
    missing = [item for item in wanted if held(snap, item.id) < item.qty]
    if len(missing) == 0:
        return None
    if not snap.bank_known:
        return Record({'kind': 'scan_bank'})
    available = [item for item in missing if snap.bank_ids is not None and snap.bank_ids.get(item.id, 0) > 0]
    if len(available) == 0:
        return None
    return Record({
        'kind': 'withdraw',
        'items': [{'name': item.name, 'id': item.id, 'qty': item.qty} for item in available],
    })


# Why: the lava bridge fails at any non-negative weight, so the bow and the arrows stay in the bank until the ice-arrow leg is done.
def dungeon_kit_step(snap):
    wanted = [Record({'name': IKOV_NAME.KNIFE, 'id': IKOV_OBJ.KNIFE, 'qty': 1})]
    if held(snap, IKOV_OBJ.LIT_CANDLE) == 0:
        wanted.extend([Record({'name': IKOV_NAME.CANDLE, 'id': IKOV_OBJ.UNLIT_CANDLE, 'qty': 1}), Record({'name': IKOV_NAME.TINDERBOX, 'id': IKOV_OBJ.TINDERBOX, 'qty': 1})])
    return withdraw_for(snap, wanted)


def war_kit_step(snap):
    bow = withdraw_for(snap, [Record({'name': IKOV_NAME.YEW_SHORTBOW, 'id': IKOV_OBJ.YEW_SHORTBOW, 'qty': 1})])
    if bow:
        return bow
    # Why: the ice-chest circuit is 4 minutes of damage that eats the engine's one-shot float, so the bot reaches the Fire Warrior's door on an empty pack unless this leg refills it.
    food = restock_step(snap, WARRIOR_FOOD, WARRIOR_FOOD_FLOOR)
    if food:
        return food
    key = IKOV_NAME.ICE_ARROWS.lower()
    if (key in snap.worn) or snap.inv.get(key, 0) > 0:
        return None
    _v2 = (snap.bank.get(key) if snap.bank is not None else None)
    banked = (_v2 if _v2 is not None else 0)
    if banked == 0:
        return None
    return Record({'kind': 'withdraw', 'items': [{'name': IKOV_NAME.ICE_ARROWS, 'qty': min(banked, ARROWS_WANTED)}]})


# Why: Lucien re-issues only when `obj_gettotal` reads zero, and that counts the bank, so a banked pendant is one he refuses to replace.
def have_fear_pendant(snap):
    return held_or_banked(snap, IKOV_OBJ.PENDANT_LUCIEN) > 0 or ((IKOV_OBJ.PENDANT_LUCIEN in snap.worn_ids) if snap.worn_ids is not None else None) == True


# Why: `gotoNpc` walks without the bridge exclusion, and the ledge is 4 stage-gated doors deep, so the approach is the module's own walk.
def talk_to_winelda(log):
    _w3 = yield from escape_pocket(log)
    if not (_w3):
        return False
    _w4 = yield from wear_fear_pendant(log)
    if not (_w4):
        return False
    _w5 = yield from temple_walk(IKOV_TILE.WINELDA, 2, log)
    if not (_w5):
        return False
    _result6 = yield from talk_strict(WINELDA_STOP.npc, WINELDA_STOP.prefer, log)
    return _result6


def finish_for_armadyl(log):
    _w7 = yield from leave_the_far_side(log)
    if not (_w7):
        return False
    _result8 = yield from kill_lucien(log)
    return _result8


def in_sealed_temple(t):
    """The temple's pockets the walker has no edge out of: the boots room, the trap pit, past the lava, Winelda's ledge and the guardians."""
    return t is not None and in_temple(t) and (in_dark_room(t) or in_trap_pit(t) or west_of_bridge(t) or on_winelda_ledge(t) or in_guardian_temple(t))


def decide(snap):
    if snap.journal == 'complete':
        return Record({'kind': 'done'})
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    stage = snap.stage
    if stage is None:
        return Record({'kind': 'wait', 'reason': 'Temple of Ikov journal stage unavailable'})
    if stage == IKOV_STAGE.NOT_STARTED:
        return Record({'kind': 'talk', 'stop': LUCIEN_START})
    # Why: past Winelda's ferry the way off is the shiny key, so neither leg can start with a bank scan, and neither needs one.
    if stage >= IKOV_STAGE.HELPING_ARMADYL:
        return Record({'kind': 'custom', 'name': 'leave the temple and banish Lucien', 'run': finish_for_armadyl})
    if stage >= IKOV_STAGE.PAID_WINELDA:
        return Record({'kind': 'custom', 'name': 'join the Guardians of Armadyl', 'run': join_the_guardians})
    # Why: a restart in a pocket has no route to a booth until it climbs or crosses out.
    if not snap.bank_known:
        if in_sealed_temple(snap.tile):
            return Record({'kind': 'custom', 'name': 'climb out of the temple pocket', 'run': escape_pocket})
        return Record({'kind': 'scan_bank'})
    # Why: Lucien re-issues the pendant and the Door of Fear is shut without it; this sits below the stage-60 return so it can't fire on the far side of the lava, which has no walk back.
    if not have_fear_pendant(snap):
        return Record({'kind': 'talk', 'stop': LUCIEN_START})
    pendant = withdraw_for(snap, [Record({'name': IKOV_NAME.PENDANT_LUCIEN, 'id': IKOV_OBJ.PENDANT_LUCIEN, 'qty': 1})])
    if pendant and ((IKOV_OBJ.PENDANT_LUCIEN in snap.worn_ids) if snap.worn_ids is not None else None) != True:
        return pendant
    if stage >= IKOV_STAGE.SPOKEN_WINELDA:
        if held_or_banked(snap, IKOV_OBJ.LIMPWURT_ROOT) < ROOTS_WANTED:
            roots = supplies_step(snap, False, False, True)
            if roots:
                return roots
        # Why: 20 unstackable roots plus coins and food fill the pack, so anything else has to go before the withdraw can land.
        gathered = held_or_banked(snap, IKOV_OBJ.LIMPWURT_ROOT) >= ROOTS_WANTED
        room = roots_trim_step(snap, (FERRY_KEEP if gathered else ROOTS_KEEP))
        if room:
            return room
        carry = withdraw_for(snap, [Record({'name': IKOV_NAME.LIMPWURT_ROOT, 'id': IKOV_OBJ.LIMPWURT_ROOT, 'qty': ROOTS_WANTED})])
        if carry:
            return carry
        return Record({'kind': 'custom', 'name': 'pay Winelda her twenty limpwurt roots', 'run': talk_to_winelda})
    if stage >= IKOV_STAGE.KILLED_WARRIOR:
        return Record({'kind': 'custom', 'name': 'ask Winelda for the ferry across the lava', 'run': talk_to_winelda})
    # Why: the candle only lights the stairs down to the boots, so it leaves the kit once the boots are had.
    need_boots = not wearing_boots() and held_or_banked(snap, IKOV_OBJ.BOOTS) == 0
    supplies = supplies_step(snap, need_boots, True, False)
    if supplies:
        return supplies
    if not arrows_secured(snap) or need_boots:
        # Why: the boots and the lever are both on the far side of a bridge that fails at any non-negative weight, so that descent carries the crossing kit and no armour.
        if need_boots or not south_gate_open():
            trim = bridge_trim_step(snap)
            if trim:
                return trim
            kit = dungeon_kit_step(snap)
            if kit:
                return kit
            # Why: `fetchBoots` completes one descent leg at a time, so keep it as a separate step before checking the gate.
            boots = boots_step(snap)
            if boots:
                return boots
            return Record({'kind': 'custom', 'name': 'unlock the south gate', 'run': unlock_south_gate})
        # Why: past the lever the ice cavern needs no crossing, so this is the first leg that can wear anything, and 9 level-61 ice spiders stand on the circuit.
        armour = ranged_armour_step(snap)
        if armour:
            return armour
        return Record({'kind': 'custom', 'name': 'stock ice arrows from the temple chests', 'run': stock_ice_arrows})
    if stage < IKOV_STAGE.PULLED_LEVER:
        return Record({'kind': 'custom', 'name': 'disarm and pull the trap lever', 'run': pull_trap_lever})
    war = war_kit_step(snap)
    if war:
        return war
    return Record({'kind': 'custom', 'name': 'shoot the Fire Warrior of Lesarkus', 'run': fight_fire_warrior})


def _fn9(snap, step):
    t = snap.tile
    where = (f'({t.x},{t.z},{t.level})' if t else '(?)')
    stage = snap.stage if snap.stage is not None else '?'
    boots = 'worn' if wearing_boots() else 'no'
    arrows = snap.inv.get(IKOV_NAME.ICE_ARROWS.lower(), 0)
    pendant = 'yes' if have_fear_pendant(snap) else 'no'
    armour = len([name for name in RANGED_ARMOUR_NAMES if (name in snap.worn)])
    gate = 'open' if south_gate_open() else 'shut'
    return [
        f"ikov: stage={stage} at {where} step={step.kind}",
        f"ikov: boots={boots} arrows={arrows} roots={held(snap, IKOV_OBJ.LIMPWURT_ROOT)} pendant={pendant} armour={armour}/4 gate={gate} weight={game.weight()}kg",
    ]


ikov = QuestModule(**{
    'record': quest_record(IKOV_ID),
    'bank': 'nearest',
    'food': 6,
    'grind': ['Hobgoblin', 'Fire Warrior of Lesarkus', 'Lucien'],
    'tools': IKOV_TOOLS,
    'sustain': Record({'foods': ['Lobster', 'Swordfish', 'Tuna'], 'eat_below_hp': 0.75}),
    'read_stage': read_ikov_stage,
    'resume_at': in_sealed_temple,
    'warn_readiness': sourcing_shortfall,
    'observe': _fn9,
    'decide': decide,
})
