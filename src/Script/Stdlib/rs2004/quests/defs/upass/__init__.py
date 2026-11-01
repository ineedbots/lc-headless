"""Ported from rs2b0t's src/bot/api/ai/quests/defs/upass/index.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.data import quest_record
from rs2004.quests.defs.upass.area1 import sweep_orbs
from rs2004.quests.defs.upass.area2 import badges_held, cross_the_temple, crush_unicorn, take_railing
from rs2004.quests.defs.upass.areas import UP_ITEM, UP_TILE, carried, held, inside_iban_temple, inside_witch_house, past_grid_tile, upass_area, worn
from rs2004.quests.defs.upass.bridge import arm_fire_arrow, cross_to_east, cross_to_west, enter_cave, get_damp_cloth, leave_pass, leave_with_koftik, make_fire_arrow, meet_koftik, report_to_lathas, shoot_guiderope, start_quest
from rs2004.quests.defs.upass.cavern import ascend_from_dwarves, ask_klank, ask_nilhoof, catch_cat, descend_to_dwarves, distract_witch, leave_witch_house, loot_witch_chest, wear_gauntlets
from rs2004.quests.defs.upass.doll import amulets_held, burn_tomb, fill_brew, kill_demon, kill_kalrag, open_iban_door, open_sealed_chest, rub_ashes, rub_dove, rub_shadow, search_cages, throw_doll
from rs2004.quests.defs.upass.grid import cross_grid
from rs2004.quests.defs.upass.journal import UP_FLAG, UP_STAGE, read_upass_progress
from rs2004.quests.defs.upass.railings import outstanding_crossing, take_next_crossing
from rs2004.quests.defs.upass.supplies import bow_worn, draw_gear, kit_shortfall, melee_carried, source_kit, wear_gear
from rs2004.quests.engine.types import QuestModule, has_flag

__all__ = ['decide', 'upass']

def custom(name, run):
    return (Record({'kind': 'custom', 'name': name, 'run': run}))


def flag(snap, name):
    return has_flag(snap.progress, name)


def outfit(snap, area):
    """Everything the pass needs, drawn and worn while a bank is still reachable."""
    if area != 'mainland':
        return None
    kit = source_kit(snap)
    return kit if kit is not None else wear_gear(snap)


# Why: Koftik and the cave mouth are inside West Ardougne, which the navigator has no edge into; the wall is only crossed through the Plague City sewer with the kit already packed.
def in_west(snap, area, step):
    if area == 'westardougne':
        return step
    _v2 = ready_to_descend(snap)
    return (_v2 if _v2 is not None else custom('cross the wall into West Ardougne', cross_to_west))


# Why: the cave mouth is the last point with a bank behind it, so a pack short of the kit stops here and says what's missing.
def ready_to_descend(snap):
    missing = kit_shortfall(snap)
    # Why: 3 paladins at level 62, 3 demons and Kalrag stand between the bridge and the end, with no bank past the cave mouth, so the fire arrow's bow alone can't win it.
    if not melee_carried(snap):
        missing.append('a melee weapon (the paladins, the demons and Kalrag), have none')
    return (None if len(missing) == 0 else Record({'kind': 'wait', 'reason': f"not equipped for the pass: {'; '.join(missing)}"}))


def bridge_leg(snap, area):
    if area == 'mainland' or area == 'westardougne':
        # Why: the kit is checked here too, since a pack that lost something inside West Ardougne would walk into a one-way dungeon without it.
        _v3 = ready_to_descend(snap)
        return (_v3 if _v3 is not None else in_west(snap, area, custom('enter the underground pass', enter_cave)))
    if area != 'area1':
        return Record({'kind': 'wait', 'reason': f'bridge leg reached from {area}'})
    if carried(snap, UP_ITEM.LIT_ARROW) == 0:
        if held(snap, UP_ITEM.DAMP_CLOTH) == 0 and held(snap, UP_ITEM.UNLIT_ARROW) == 0:
            return custom('take the damp cloth from Koftik', get_damp_cloth)
        return custom('wrap and light a fire arrow', make_fire_arrow)
    if not worn(snap, UP_ITEM.LIT_ARROW) or not bow_worn(snap):
        return custom('wield the bow and the lit arrow', arm_fire_arrow)
    return custom('fire the lit arrow at the bridge stay rope', shoot_guiderope)


# Why: all 4 orbs are gathered before any is burned, because the furnace sits between the grid and the well and a per-orb round trip crosses the spear-trap corridor 4 times.
def orb_leg(snap):
    if not past_grid_tile(snap.tile):
        # Why: the crossing walks itself to the grid lip first, and the rope swing onto that shelf is in travelTo's vocabulary, so the caller doesn't pick seams.
        return custom('cross the spiked grid with the journal held open', cross_grid)
    # Why: one step for the sweep. A burned orb has left the pack and reads as never collected, and no site hands over a second, so a per-site decide cycle picks the same site forever. The step keeps its own tally.
    return custom('take and burn the four orbs, then climb the well', sweep_orbs)


# Why: stages 3 and 4 are one leg because the journal can't tell them apart, both print "I must work my way deeper into these caverns" and differ only in which line is struck through. The horn is what the snapshot can see, so it ends the step.
def unicorn_leg(snap, area):
    if held(snap, UP_ITEM.UNICORN_HORN) > 0 or badges_held(snap) > 0 or area != 'area2':
        return paladin_leg()
    if held(snap, UP_ITEM.RAILING) == 0:
        # Why: 6 crossings stand between the well's corridor and that cage, and the engine recognises "the same step" by description alone, so one step for all of them never resets the attempt counter and the watchdog parks it. Each crossing is its own step.
        next_ = outstanding_crossing()
        if next_ is not None:
            return custom(f'cross {next_.what}', take_next_crossing)
        return custom('search the cage bars for a loose railing', take_railing)
    return custom('crush the unicorn and take its horn', crush_unicorn)


# Why: the way back up to the paladins' shelf is the unicorn tunnel at the south end of the second cavern; the mud pile climbs into the orb corridor behind every trap already crossed. The tunnel is one of travelTo's seams, so walking is enough.
# Why: the crests, the well and the doors are one step, because the well eats the crests and the journal never says so, so a snapshot can't tell "not killed yet" from "already fed".
def paladin_leg():
    return custom('take the crests, feed the well and pass the temple doors', cross_the_temple)


def dwarf_leg(area):
    if area != 'dwarves':
        return custom('climb down the wall tunnel to the dwarves', descend_to_dwarves)
    return custom('ask Nilhoof about the way through', ask_nilhoof)


def witch_leg(snap, area):
    if area == 'dwarves':
        return (custom('take a tinderbox from Klank', ask_klank) if held(snap, UP_ITEM.TINDERBOX) == 0 else custom('climb back up out of the dwarves cave', ascend_from_dwarves))
    # Why: the knock takes the cat and the journal never records it, so "no cat, no doll" reads the same before and after the knock. Only the knock leaves you at her door, so the tile tells them apart.
    # Why: 3 steps because the engine recognises "the same step" by description alone, and the walk to the cat is 56 tiles across 4 bridges. Each part names itself so finishing one resets the count.
    at = snap.tile
    at_her_door = at is not None and at.level == UP_TILE.WITCH_DOOR.level and max(abs(at.x - UP_TILE.WITCH_DOOR.x), abs(at.z - UP_TILE.WITCH_DOOR.z)) <= 6
    if not at_her_door and held(snap, UP_ITEM.WITCH_CAT) == 0:
        return custom('catch the witches cat', catch_cat)
    if held(snap, UP_ITEM.WITCH_CAT) > 0:
        return custom("knock on Kardia's door with the cat", distract_witch)
    return custom("open Kardia's chest and take the doll", loot_witch_chest)


# Why: the 4 elements are ordered by where they are: ashes and blood hang off the 2 wall tunnels, shadow and conscience off the level-1 platforms, so each tunnel is used once.
def doll_leg(snap, area):
    if held(snap, UP_ITEM.ASHES) > 0:
        return custom("rub Iban's ashes into the doll", rub_ashes)
    if held(snap, UP_ITEM.SHADOW) > 0:
        return custom("pour Iban's shadow over the doll", rub_shadow)
    if held(snap, UP_ITEM.DOVE) > 0:
        return custom("crumble Iban's dove into the doll", rub_dove)
    # Why: the 4 elements sit in 4 pockets joined by one-way tunnels, so each names the pocket it needs and the step that gets there.
    if not flag(snap, UP_FLAG.ASHES_ON_DOLL):
        # Why: the camp and Kalrag's cave are one pocket, so a resume on her side is already down here; naming only the camp sends it back down a tunnel it's standing below.
        if area != 'dwarves' and area != 'kalrag':
            return custom('climb down the wall tunnel to the dwarves', descend_to_dwarves)
        if held(snap, UP_ITEM.GAUNTLETS) == 0:
            return custom("take Klank's gauntlets", ask_klank)
        return (custom('fill the bucket with dwarf brew', fill_brew) if held(snap, UP_ITEM.DWARF_BREW) == 0 else custom("soak and burn Iban's tomb", burn_tomb))
    # Why: the collision pack floods the dwarf camp, Iban's tomb, Kalrag and both wall-tunnel exits into one pocket, so take the blood while already down here. Kalrag only gives it with the doll in the pack and the stage still `found`.
    if not flag(snap, UP_FLAG.BLOOD_ON_DOLL) and (area == 'dwarves' or area == 'kalrag'):
        return custom('kill Kalrag with the doll in hand', kill_kalrag)
    if not flag(snap, UP_FLAG.DOVE_ON_DOLL):
        # Why: taking the blood leaves you on Kalrag's tile, which classifies as `kalrag`, and a guard naming only `dwarves` walks off to a level-1 cage from level 0. Both names are one pocket and both climb out.
        if area == 'dwarves' or area == 'kalrag':
            return custom('climb back up out of the dwarves cave', ascend_from_dwarves)
        return (custom("wear Klank's gauntlets", wear_gauntlets) if held(snap, UP_ITEM.GAUNTLETS) > 0 and not worn(snap, UP_ITEM.GAUNTLETS) else custom('search the soulless cages for the dove', search_cages))
    if not flag(snap, UP_FLAG.SHADOW_ON_DOLL):
        return (custom('kill a demon for its amulet', kill_demon) if amulets_held(snap) < 3 else custom('open the sealed chest for the shadow', open_sealed_chest))
    if not flag(snap, UP_FLAG.BLOOD_ON_DOLL):
        return (custom('kill Kalrag with the doll in hand', kill_kalrag) if area == 'kalrag' or area == 'dwarves' else custom('climb down the wall tunnel to the dwarves', descend_to_dwarves))
    return custom("open Iban's temple doors", open_iban_door)


# Why: the temple throws you into the second cavern, which has no walkable way up; Koftik's dialogue is the transport, so the walk out is 4 steps keyed on where the last one landed.
def finish_leg(area):
    if area == 'area2':
        return custom('find Koftik and let him lead the way out', leave_with_koftik)
    elif area == 'area1':
        return custom('leave the underground pass', leave_pass)
    elif area == 'westardougne':
        return custom('cross the wall back into East Ardougne', cross_to_east)
    elif area == 'mainland':
        return custom('report to King Lathas', report_to_lathas)
    else:
        return Record({'kind': 'wait', 'reason': f'thrown out of Iban\'s temple into {area}'})


def stage_step(snap, area, stage):
    # Why: The doll chest pocket's only exit is absent from the nav pack, so leave it explicitly.
    if inside_witch_house(snap.tile):
        return custom("let yourself out of Kardia's house", leave_witch_house)
    # Why: Keep the bow equipped through the rope shot and reserve inventory space for the orb sweep; equip melee gear only after the robe-only door.
    bare = flag(snap, UP_FLAG.DOLL_COMPLETE) and stage < UP_STAGE.DEFEATED_IBAN
    gear = (draw_gear(snap) if stage >= UP_STAGE.PASSED_BRIDGE and not bare else None)
    if gear:
        return gear
    if stage == UP_STAGE.NOT_STARTED:
        _v4 = outfit(snap, area)
        return (_v4 if _v4 is not None else ((in_west(snap, area, custom('meet Koftik at the cave mouth', meet_koftik)) if flag(snap, UP_FLAG.STARTED) else custom('ask King Lathas about the mountains', start_quest))))
    elif stage == UP_STAGE.SPOKEN_KOFTIK:
        _v5 = outfit(snap, area)
        return (_v5 if _v5 is not None else bridge_leg(snap, area))
    elif stage == UP_STAGE.PASSED_BRIDGE:
        return orb_leg(snap)
    elif stage in [UP_STAGE.ENTERED_SECOND_AREA, UP_STAGE.KILLED_UNICORN]:
        return unicorn_leg(snap, area)
    elif stage == UP_STAGE.ENTERED_MAIN_AREA:
        return dwarf_leg(area)
    elif stage == UP_STAGE.SPOKEN_NILHOOF:
        return witch_leg(snap, area)
    elif stage in [UP_STAGE.FOUND_DOLL, UP_STAGE.CONFRONTED_IBAN]:
        if flag(snap, UP_FLAG.DOLL_COMPLETE):
            return (custom('throw the doll into the pit of the damned', throw_doll) if inside_iban_temple(snap.tile) else custom("open Iban's temple doors", open_iban_door))
        return doll_leg(snap, area)
    elif stage == UP_STAGE.DEFEATED_IBAN:
        return finish_leg(area)
    else:
        return Record({'kind': 'wait', 'reason': f'Underground Pass stage {stage} is not implemented'})


def decide(snap):
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    area = upass_area(snap.tile)
    if area == 'unknown':
        return Record({'kind': 'wait', 'reason': 'player location unavailable'})
    if snap.journal == 'complete' or ((snap.stage if snap.stage is not None else -1)) >= UP_STAGE.COMPLETE:
        return Record({'kind': 'done'})
    if snap.stage is None:
        return Record({'kind': 'wait', 'reason': 'Underground Pass journal stage unavailable'})
    return stage_step(snap, area, snap.stage)


# Why: every pocket under the wall, where a restart has no route to a booth until the quest walks it out.
BANKLESS = ['area1', 'area2', 'gridpit', 'main', 'temple', 'witch', 'voyage', 'kalrag', 'dwarves']


def inside_pass(t):
    return t is not None and upass_area(t) in BANKLESS


upass = QuestModule(**{
    'record': quest_record('upass'),
    'pray': Record({'protect': 'melee', 'potions': 2}),
    'bank': UP_TILE.ARDOUGNE_BANK,
    'owns_inventory': True,
    'read_progress': read_upass_progress,
    'resume_at': inside_pass,
    # Why: the corridor traps are timer damage on chokepoint tiles, and avoiding those tiles deletes 4 of the 6 routes through the orb corridor because the traps sit in the only walkable squares, so the eat threshold is high.
    'sustain': Record({'foods': [UP_ITEM.LOBSTER.name], 'eat_below_hp': 0.8}),
    'decide': decide,
})

