"""Ported from rs2b0t's src/bot/api/ai/quests/defs/shilo/index.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.data import quest_record
from rs2004.quests.engine.types import QuestModule
from rs2004.quests.defs.shilo.ahzarhoon import bury_zadimus, cross_cave_in, dig_mound, enter_fissure, leave_ah_za_rhoon, light_fissure, read_scroll, rope_fissure, take_crumpled_scroll, take_tattered_scroll, take_zadimus_corpse
from rs2004.quests.defs.shilo.areas import SV_ITEM, SV_TILE, shilo_area
from rs2004.quests.defs.shilo.cairn import craft_bone_beads, craft_bone_key, craft_dead_beads, deliver_corpse, leave_bervirius_tomb, search_bervirius_dolmen
from rs2004.quests.defs.shilo.gear import combat_gear, reset_combat_gear
from rs2004.quests.defs.shilo.journal import SV_STAGE, read_shilo_progress
from rs2004.quests.defs.shilo.rashtomb import climb_rash_rocks, enter_rash_tomb, leave_rash_tomb, leave_tomb_chamber, pass_gate, place_bone, search_carved_doors, unlock_carved_doors, work_the_dolmen
from rs2004.quests.defs.shilo.start import start_quest, take_wampum_belt
from rs2004.quests.defs.shilo.supplies import FOOD_FALLBACKS, KARAMJA_PURSE, banked, food_held, held, owned, source_bones, source_bronze_wire, source_coins, source_food, source_lit_candle, source_tools, withdraw_from, worn
from rs2004.quests.engine.types import flag_value, has_flag
from rs2004.quests.food import FOOD_FLOAT

__all__ = ['decide', 'shilo']

TOMB_BONES = 3
TOMB_FOOD = FOOD_FLOAT
# Why: a top-up is a return crossing to Ardougne, so a pack a few short still goes in; below this the tomb isn't worth entering.
TOMB_FOOD_MIN = 4


# Why: only coins, bones and food come from off the island, and there's no bank here until the quest opens Shilo's, so provisioning only runs on the mainland.
def on_karamja(tile):
    """True while on Karamja, loosely bounded."""
    if not tile:
        return False
    return tile.x >= 2735 and tile.x <= 3010 and tile.z >= 2870 and tile.z <= 3245


def step(name, run):
    return Record({'kind': 'custom', 'name': name, 'run': run})


# Why: a step that assumes open ground from inside a pocket sends the walker at a tile on the wrong side of a one-way crossing and spends 3 passes proving it unreachable.
def escape_pocket(area):
    """A step out of the current sealed pocket, or null when on open ground."""
    if area in ['ahZaRhoonNorth', 'ahZaRhoonSouth']:
        return step('climb out of Ah Za Rhoon', leave_ah_za_rhoon)
    elif area == 'berviriusTomb':
        return step("climb out of Bervirius' tomb", leave_bervirius_tomb)
    elif area == 'rashInner':
        return step('leave the tomb chamber', leave_tomb_chamber)
    elif area == 'rashLedge':
        return step('open the ancient gate back out', lambda log: pass_gate('out', log))
    elif area == 'rashEntry':
        return step("unlock Rashiliyia's tomb exit", leave_rash_tomb)
    else:
        return None


def in_the_open(area, step_if_open):
    """Take `stepIfOpen` only once we are somewhere it can start from."""
    _v1 = escape_pocket(area)
    return (_v1 if _v1 is not None else step_if_open)


def in_the_open_or_in(area, own_pocket, step_if_ok):
    """For steps that enter their own pocket; escaping unconditionally would climb straight back out of the tomb the step walked into."""
    return (step_if_ok if area == own_pocket else in_the_open(area, step_if_ok))


# Why: coins, bones and food can't be had on Karamja and the nearest bank is an ocean away, so all 3 are settled before the crossing.
def provision(snap, area):
    """Provision coins, bones and food before the crossing, or null."""
    if area != 'karamja' or on_karamja(snap.tile):
        return None
    food = source_food(snap, TOMB_FOOD)
    # Why: an empty larder is only fatal at the tomb door, so it waits there.
    _v2 = source_coins(snap, KARAMJA_PURSE)
    _v3 = (_v2 if _v2 is not None else source_bones(snap, TOMB_BONES))
    return (_v3 if _v3 is not None else ((None if (food.kind if food is not None else None) == 'wait' else food)))


def recover_from_bank(snap, item):
    """Bank-first for anything the quest may have left behind on a previous run."""
    if held(snap, item.id) > 0 or banked(snap, item.id) == 0:
        return None
    return withdraw_from([{'name': item.name, 'id': item.id, 'qty': 1}])


def stage_start(snap, area):
    if held(snap, SV_ITEM.WAMPUM_BELT.id) > 0:
        return in_the_open(area, step('show the Wampum belt to Trufitus', start_quest))
    _v4 = recover_from_bank(snap, SV_ITEM.WAMPUM_BELT)
    return (_v4 if _v4 is not None else in_the_open(area, step('ask Mosol Rei for the Wampum belt', take_wampum_belt)))


def tools_from(stage):
    """Everything Jiminua stocks that the rest of the quest still wants, so one shop trip covers the fissure sequence and both crafts."""
    need = []
    if stage <= SV_STAGE.SEARCHED_MOUND:
        need.append(SV_ITEM.SPADE)
    if stage <= SV_STAGE.DUG_MOUND:
        need.extend([SV_ITEM.CANDLE, SV_ITEM.TINDERBOX])
    if stage <= SV_STAGE.LIT_MOUND:
        need.append(SV_ITEM.ROPE)
    need.extend([SV_ITEM.CHISEL, SV_ITEM.BRONZE_BAR, SV_ITEM.HAMMER])
    return need


def stage_mound(snap, area):
    kit = source_tools(snap, tools_from(SV_STAGE.STARTED))
    return (in_the_open(area, kit) if kit else in_the_open(area, step('dig the mound of earth open', dig_mound)))


def stage_light(snap, area):
    candle = source_lit_candle(snap, tools_from(SV_STAGE.DUG_MOUND))
    return (in_the_open(area, candle) if candle else in_the_open(area, step('drop a lit candle into the fissure', light_fissure)))


def stage_rope(snap, area):
    kit = source_tools(snap, tools_from(SV_STAGE.LIT_MOUND))
    return (in_the_open(area, kit) if kit else in_the_open(area, step('tie the rope to the fissure', rope_fissure)))


# Why: stages 7 to 9 render the same journal block until the Bervirius dolmen is searched, so this branch runs on flags and what is carried.
def stage_middle(snap, area):
    """The next step for the stage 7-9 block."""
    in_caves = area == 'ahZaRhoonNorth' or area == 'ahZaRhoonSouth'
    if not has_flag(snap.progress, 'pommel-taken'):
        # Why: Scroll progress disappears from the journal after the dolmen, so read each scroll before that point.
        if not has_flag(snap.progress, 'read-tattered'):
            if held(snap, SV_ITEM.TATTERED_SCROLL.id) > 0:
                return step('read the tattered scroll', read_scroll(SV_ITEM.TATTERED_SCROLL.id))
            return step('find the tattered scroll behind the loose rocks', take_tattered_scroll)
        if not has_flag(snap.progress, 'read-crumpled'):
            if held(snap, SV_ITEM.CRUMPLED_SCROLL.id) > 0:
                return step('read the crumpled scroll', read_scroll(SV_ITEM.CRUMPLED_SCROLL.id))
            return step('search the old sacks for the crumpled scroll', take_crumpled_scroll)
        if held(snap, SV_ITEM.BONE_SHARD.id) == 0 and held(snap, SV_ITEM.BONE_KEY.id) == 0:
            if held(snap, SV_ITEM.ZADIMUS_CORPSE.id) > 0:
                return in_the_open(area, step("bury Zadimus on Tai Bwo Wannai's sacred ground", bury_zadimus))
            return step('take the corpse from the ancient gallows', take_zadimus_corpse)
        return in_the_open_or_in(area, 'berviriusTomb', step("search the dolmen in Bervirius' tomb", search_bervirius_dolmen))
    if in_caves:
        return step('climb out of Ah Za Rhoon', leave_ah_za_rhoon)
    if not has_flag(snap.progress, 'found-door'):
        return in_the_open(area, step('search the carved doors for their lock', search_carved_doors))
    craft = craft_chain(snap, area, True)
    if craft:
        return craft
    return in_the_open(area, step('unlock the carved doors with the bone key', unlock_carved_doors))


def craft_chain(snap, area, want_key):
    """The necklace and the key share a chisel; the beads are refused until the crumpled scroll is read, the key until the door is searched."""
    # Why: past the carved doors the key is optional, since they stay unlocked and the tomb exit refuses anyone still carrying it.
    need_key = want_key and held(snap, SV_ITEM.BONE_KEY.id) == 0
    need_beads = owned(snap, SV_ITEM.DEAD_BEADS.id) == 0 and not worn(snap, SV_ITEM.DEAD_BEADS.id)
    if not need_key and not need_beads:
        return None
    # One trip: the chisel cuts both the key and the beads, and the bar and hammer are the necklace's wire.
    need = [SV_ITEM.CHISEL]
    if need_beads and held(snap, SV_ITEM.BRONZE_WIRE.id) == 0:
        need.extend([SV_ITEM.BRONZE_BAR, SV_ITEM.HAMMER])
    kit = source_tools(snap, need)
    if kit:
        return in_the_open(area, kit)
    if need_key:
        if held(snap, SV_ITEM.BONE_SHARD.id) == 0:
            _v5 = recover_from_bank(snap, SV_ITEM.BONE_SHARD)
            return (_v5 if _v5 is not None else step('take the corpse from the ancient gallows', take_zadimus_corpse))
        return step('cut the bone shard into a key', craft_bone_key)
    if held(snap, SV_ITEM.BONE_BEADS.id) == 0:
        if held(snap, SV_ITEM.SWORD_POMMEL.id) == 0:
            _v6 = recover_from_bank(snap, SV_ITEM.SWORD_POMMEL)
            return (_v6 if _v6 is not None else in_the_open_or_in(area, 'berviriusTomb', step("search the dolmen in Bervirius' tomb", search_bervirius_dolmen)))
        return step('carve the ivory pommel into beads', craft_bone_beads)
    wire = source_bronze_wire(snap)
    return (in_the_open(area, wire) if wire else step('thread the beads into the Beads of the Dead', craft_dead_beads))


def bones_wanted(snap):
    """How many recesses are still empty, per the journal."""
    _v7 = flag_value(snap.progress, 'bones-placed')
    return max(0, TOMB_BONES - ((_v7 if _v7 is not None else 0)))


def tomb_supplies(snap, bones):
    """Nothing can be fetched from inside, so the bones and the food go in with us."""
    food = (source_food(snap, TOMB_FOOD) if food_held(snap) < TOMB_FOOD_MIN else None)
    _v8 = ((source_bones(snap, bones) if bones > 0 else None))
    return (_v8 if _v8 is not None else food)


def need_beads(snap, area):
    """Beads on before anything else: the gate summons Rashiliyia for anyone without them."""
    if worn(snap, SV_ITEM.DEAD_BEADS.id):
        return None
    if held(snap, SV_ITEM.DEAD_BEADS.id) > 0:
        return Record({'kind': 'equip', 'item': SV_ITEM.DEAD_BEADS.name})
    _v9 = recover_from_bank(snap, SV_ITEM.DEAD_BEADS)
    _v10 = (_v9 if _v9 is not None else craft_chain(snap, area, False))
    return (_v10 if _v10 is not None else Record({'kind': 'wait', 'reason': 'no Beads of the Dead to wear'}))


def stage_tomb(snap, area):
    """Engine stages 10 and 11: through the hillside doors, past the gate, down the rocks."""
    craft = craft_chain(snap, area, False)
    if craft:
        return craft
    beads = need_beads(snap, area)
    if beads:
        return beads
    wanted = bones_wanted(snap)
    # Bones come from Ardougne, so being short inside the tomb means walking back out.
    if held(snap, SV_ITEM.BONES.id) < wanted and area != 'karamja':
        _v11 = escape_pocket(area)
        return (_v11 if _v11 is not None else Record({'kind': 'wait', 'reason': 'short of bones and nowhere to go'}))
    if area == 'rashInner':
        # The third bone opens the doors and pushes us through, so nothing is left once the journal catches up.
        return (step('place a bone in the tomb door', place_bone) if wanted > 0 else Record({'kind': 'wait', 'reason': 'all three bones are placed — waiting for the journal'}))
    if area == 'rashLedge':
        return step('climb down to the tomb chamber', lambda log: climb_rash_rocks('down', log))
    if area == 'rashEntry':
        return step('open the ancient gate', lambda log: pass_gate('in', log))
    supplies = tomb_supplies(snap, wanted)
    if supplies:
        return in_the_open(area, supplies)
    return in_the_open(area, step("enter Rashiliyia's tomb", enter_rash_tomb))


def stage_boss(snap, area):
    """Engine stages 12 and 14: the three Nazastarool forms, then the remains."""
    if owned(snap, SV_ITEM.RASH_CORPSE.id) > 0:
        if held(snap, SV_ITEM.RASH_CORPSE.id) == 0:
            _v12 = recover_from_bank(snap, SV_ITEM.RASH_CORPSE)
            return (_v12 if _v12 is not None else Record({'kind': 'wait', 'reason': 'the remains are unreachable'}))
        return in_the_open_or_in(area, 'berviriusTomb', step("lay the remains on Bervirius' dolmen", deliver_corpse))
    if area == 'rashInner':
        return step('search the tomb dolmen', work_the_dolmen)
    if area == 'rashLedge':
        return step('climb down to the tomb chamber', lambda log: climb_rash_rocks('down', log))
    if area == 'rashEntry':
        return step('open the ancient gate', lambda log: pass_gate('in', log))
    beads = need_beads(snap, area)
    if beads:
        return beads
    supplies = tomb_supplies(snap, 0)
    if supplies:
        return in_the_open(area, supplies)
    return in_the_open(area, step("enter Rashiliyia's tomb", enter_rash_tomb))


def decide(snap):
    area = shilo_area(snap.tile)
    if snap.journal == 'complete' or ((snap.stage if snap.stage is not None else -1)) >= SV_STAGE.COMPLETE:
        _v13 = escape_pocket(area)
        return (_v13 if _v13 is not None else Record({'kind': 'done'}))
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    if snap.stage is None:
        return Record({'kind': 'wait', 'reason': 'Shilo Village journal stage unavailable'})
    if area == 'unknown':
        return Record({'kind': 'wait', 'reason': 'player location unavailable'})
    gear = combat_gear(snap)
    if gear:
        return (gear if gear.kind == 'custom' else in_the_open(area, gear))
    supplies = provision(snap, area)
    if supplies:
        return supplies
    if snap.stage == SV_STAGE.NOT_STARTED:
        return stage_start(snap, area)
    elif snap.stage in [SV_STAGE.STARTED, SV_STAGE.SEARCHED_MOUND]:
        return stage_mound(snap, area)
    elif snap.stage == SV_STAGE.DUG_MOUND:
        return stage_light(snap, area)
    elif snap.stage == SV_STAGE.LIT_MOUND:
        return stage_rope(snap, area)
    elif snap.stage == SV_STAGE.ROPED_MOUND:
        return in_the_open(area, step('climb down the fissure into Ah Za Rhoon', enter_fissure))
    elif snap.stage == SV_STAGE.ENTERED_AH_ZA_RHOON:
        return stage_middle(snap, area)
    elif snap.stage == SV_STAGE.UNLOCKED_RASH_TOMB:
        return stage_tomb(snap, area)
    elif snap.stage == SV_STAGE.UNLOCKED_TOMBDOOR:
        return stage_boss(snap, area)
    else:
        return Record({'kind': 'wait', 'reason': f'Shilo Village stage {snap.stage} is not implemented'})


shilo = QuestModule(**{
    'record': quest_record('zombiequeen'),
    'on_start': reset_combat_gear,
    'bank': SV_TILE.ARDOUGNE_BANK,
    'owns_inventory': True,
    'read_progress': read_shilo_progress,
    'sustain': Record({'foods': list(FOOD_FALLBACKS), 'eat_below_hp': 0.6}),
    'decide': decide,
})
