"""Ported from rs2b0t's src/bot/api/ai/quests/defs/tbwt/index.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.game import skills
from rs2004.quests.data import quest_record
from rs2004.quests.engine.types import QuestModule
from rs2004.quests.defs.tbwt.areas import FOOD_TARGET, KARAMBWANJI_WANTED, KARAMBWAN_BAIT, SPEAR_HUNT_KILLS, TBWT_QUEST, TB_ID, TB_LUBUFU, TB_MAIN, TB_NPC, TB_POTIONS, TB_SPEAR_DROPS, TB_TAMAYU, TB_TIADECHE, TB_TILE, TB_TINSAY, in_cutscene
from rs2004.quests.defs.tbwt.brothers import become_apprentice, claim_reward, give_karambwanji, give_manual, give_tamayu, give_tinsay, hunt_shaikahan, meet_lubufu, meet_tamayu, meet_tiadeche, meet_tinsay, spare_vessel, start_quest, tiadeche_catch
from rs2004.quests.defs.tbwt.crafting import burn_jogre_bones, buy_rum, combine, cook_on_fire, fish_karambwan, fish_karambwanji, grind, kill_for, load_vessel, make_sandwich, paste_bones, pick_banana, poison_spear
from rs2004.quests.defs.tbwt.journal import TB_FLAG, parse_tbwt_journal, read_tbwt_progress
from rs2004.quests.defs.tbwt.supplies import TB_PROVEN, bare_spear_held, doses_held, held_id, kp_spear_held, lubufu_stage, outstanding_supplies, prepare, readiness, tamayu_stage, tiadeche_stage, tinsay_stage
from rs2004.quests.defs.tbwt.talk import use_on_npc
from rs2004.quests.engine.types import has_flag

__all__ = ['TBWT_QUEST', 'TB_ID', 'TB_LUBUFU', 'TB_MAIN', 'TB_TAMAYU', 'TB_TIADECHE', 'TB_TINSAY', 'parse_tbwt_journal', 'read_tbwt_progress', 'TB_FLAG', 'outstanding_supplies', 'prepare', 'TB_PROVEN', 'decide', 'tbwt']


def custom(name, run):
    return (Record({'kind': 'custom', 'name': name, 'run': run}))


def wait(reason):
    return (Record({'kind': 'wait', 'reason': reason}))


def vessel_held(snap):
    """The vessel in whichever state the pack holds it."""
    return (TB_ID.VESSEL if held_id(snap, TB_ID.VESSEL) > 0 else ((TB_ID.VESSEL_LOADED if held_id(snap, TB_ID.VESSEL_LOADED) > 0 else 0)))


def baited_vessel(snap):
    """A baited vessel, sourcing the vessel and the bait if either is gone."""
    if held_id(snap, TB_ID.VESSEL_LOADED) > 0:
        return None
    if held_id(snap, TB_ID.VESSEL) == 0:
        return custom('ask Lubufu for another Karambwan vessel', spare_vessel)
    if held_id(snap, TB_ID.RAW_KARAMBWANJI) == 0:
        return custom('net a Karambwanji for bait', fish_karambwanji(1))
    return custom('bait the Karambwan vessel', load_vessel)


# Why: Lubufu counts the 20 in himself, so a part-load is progress and the pack never has to hold all of them at once.
def lubufu_leg(snap, stage):
    if stage < TB_LUBUFU.FETCH_KARAMBWANJI:
        return custom('introduce yourself to Lubufu', meet_lubufu)
    if stage < TB_LUBUFU.GIVEN_KARAMBWANJI:
        owed = KARAMBWANJI_WANTED - (stage - TB_LUBUFU.FETCH_KARAMBWANJI)
        carrying = held_id(snap, TB_ID.RAW_KARAMBWANJI)
        free = (snap.free_slots if snap.free_slots is not None else 0)
        if carrying >= owed or (carrying > 0 and free <= 1):
            return custom(f'hand Lubufu {carrying} of the {owed} Karambwanji he still wants', give_karambwanji)
        return custom(f'net Karambwanji ({carrying}/{owed})', fish_karambwanji(min(owed, carrying + free)))
    return custom("take up Lubufu's apprenticeship", become_apprentice)


def tiadeche_catch_leg(snap, stage):
    if stage < TB_TIADECHE.RETURN_WHEN_CAUGHT:
        return custom('bring Tiadeche the news', meet_tiadeche)
    if stage == TB_TIADECHE.CAUGHT:
        return custom('ask Tiadeche what he needs next', meet_tiadeche)
    _v1 = baited_vessel(snap)
    return (_v1 if _v1 is not None else custom('hand Tiadeche the baited vessel', tiadeche_catch))


# Why: Tamayu wants a spear above bronze and Karambwan-poisoned; the poison is a poorly cooked Karambwan ground with a pestle, and his own gift is the first one.
# Why: the paste is ground first and the shaft found second, so the hunt is a last resort.
def karambwan_spear(snap):
    if kp_spear_held(snap) > 0:
        return None
    if held_id(snap, TB_ID.KARAMBWAN_POISON_PASTE) > 0:
        spear = bare_spear_held(snap)
        if not spear:
            return custom('hunt Jogres for a spear', kill_for(TB_NPC.JOGRE, TB_TILE.JOGRES, TB_SPEAR_DROPS, 'a spear', SPEAR_HUNT_KILLS))
        return custom(f'smear the Karambwan paste over the {spear.name.lower()}', poison_spear(spear))
    if held_id(snap, TB_ID.POORLY_COOKED_KARAMBWAN) > 0:
        return custom('grind the cooked Karambwan into poison', grind(TB_ID.POORLY_COOKED_KARAMBWAN, TB_ID.KARAMBWAN_POISON_PASTE))
    if held_id(snap, TB_ID.RAW_KARAMBWAN) > 0:
        return custom('cook the Karambwan on the jungle fire', cook_on_fire(TB_ID.RAW_KARAMBWAN, TB_ID.POORLY_COOKED_KARAMBWAN, 'raw Karambwan'))
    for id, name in [
        [TB_ID.KARAMBWAN_POISON_PASTE, 'Karambwan paste'],
        [TB_ID.POORLY_COOKED_KARAMBWAN, 'Cooked karambwan'],
        [TB_ID.RAW_KARAMBWAN, 'Raw karambwan'],
    ]:
        _v2 = (snap.bank_ids.get(id) if snap.bank_ids is not None else None)
        if ((_v2 if _v2 is not None else 0)) > 0:
            return Record({
                'kind': 'withdraw',
                'items': [Record({'id': id, 'name': name, 'qty': 1})],
                'bank': TB_TILE.ARDOUGNE_BANK,
            })
    if skills.level('fishing') < 65:
        return wait('replacement Karambwan needs 65 Fishing or a banked raw Karambwan; the one-time gift is missing')
    # Why: 2 spare Karambwanji ride along, so a burn is re-cooked from this trip.
    if held_id(snap, TB_ID.RAW_KARAMBWANJI) < KARAMBWAN_BAIT:
        return custom('net bait for the Karambwan shoal', fish_karambwanji(KARAMBWAN_BAIT))
    if vessel_held(snap) == 0:
        return custom('ask Lubufu for another Karambwan vessel', spare_vessel)
    return custom('lower the vessel for a Karambwan', fish_karambwan())


def tamayu_leg(snap, stage):
    if stage < TB_TAMAYU.SLAY_SHAIKAHAN:
        return custom('bring Tamayu the news', meet_tamayu)
    if stage < TB_TAMAYU.WATCHED_CUTSCENE:
        return custom("watch Tamayu's hunt", hunt_shaikahan)
    # Why: he counts doses and only the 4th writes a journal line, so this pours one per pass.
    if not has_flag(snap.progress, TB_FLAG.AGILITY):
        bottle = ([potion for potion in TB_POTIONS if held_id(snap, potion.id) > 0] or [None])[0]
        if not bottle:
            return wait(f'Tamayu is short of his four doses and the pack holds {doses_held(snap)}')
        return custom(f'give Tamayu the {bottle.name}', give_tamayu(bottle.id))
    if not has_flag(snap.progress, TB_FLAG.SPEAR):
        _v3 = karambwan_spear(snap)
        return (_v3 if _v3 is not None else custom('give Tamayu the Karambwan-poisoned spear', give_tamayu(kp_spear_held(snap))))
    return custom('follow Tamayu on the killing hunt', hunt_shaikahan)


def rum_leg(snap):
    if held_id(snap, TB_ID.RUM_SLICED) > 0:
        return custom('give Tinsay the sliced banana in Karamjan rum', give_tinsay(TB_ID.RUM_SLICED))
    if held_id(snap, TB_ID.SLICED_BANANA) == 0:
        if held_id(snap, TB_ID.BANANA) == 0:
            return custom('pick a banana in the plantation', pick_banana)
        return custom('slice the banana', lambda log: combine(TB_ID.KNIFE, TB_ID.BANANA, TB_ID.SLICED_BANANA, log))
    if held_id(snap, TB_ID.RUM) == 0:
        return custom('buy Karamjan rum from Zambo', buy_rum)
    return custom('drop the banana slices into the rum', lambda log: combine(TB_ID.SLICED_BANANA, TB_ID.RUM, TB_ID.RUM_SLICED, log))


# Why: nobody else on the island will skin a monkey, and Tamayu only does it once his own hunt is over.
def sandwich_leg(snap):
    if held_id(snap, TB_ID.SANDWICH) > 0:
        return custom('give Tinsay the seaweed sandwich', give_tinsay(TB_ID.SANDWICH))
    if held_id(snap, TB_ID.MONKEY_SKIN) == 0:
        if held_id(snap, TB_ID.MONKEY_CORPSE) == 0:
            return custom('shoot a monkey for its corpse', kill_for(TB_NPC.MONKEY, TB_TILE.MONKEYS, [TB_ID.MONKEY_CORPSE], 'Monkey corpse'))
        return custom('ask Tamayu to skin the monkey', give_tamayu(TB_ID.MONKEY_CORPSE))
    return custom('sandwich the seaweed into the monkey skin', make_sandwich)


def bones_leg(snap):
    if held_id(snap, TB_ID.MARINATED_JOGRE_BONES) > 0:
        return custom('give Tinsay the marinated Jogre bones', give_tinsay(TB_ID.MARINATED_JOGRE_BONES))
    if held_id(snap, TB_ID.PASTY_JOGRE_BONES) > 0:
        return custom('marinate the bones on the jungle fire', cook_on_fire(TB_ID.PASTY_JOGRE_BONES, TB_ID.MARINATED_JOGRE_BONES, 'pasty Jogre bones'))
    if held_id(snap, TB_ID.BURNT_JOGRE_BONES) > 0:
        if held_id(snap, TB_ID.KARAMBWANJI_PASTE) > 0:
            return custom('smother the bones in Karambwanji paste', paste_bones)
        if held_id(snap, TB_ID.RAW_KARAMBWANJI) == 0:
            return custom('net a Karambwanji for the marinade', fish_karambwanji(1))
        return custom('grind the Karambwanji into paste', grind(TB_ID.RAW_KARAMBWANJI, TB_ID.KARAMBWANJI_PASTE))
    if held_id(snap, TB_ID.JOGRE_BONES) == 0:
        return custom('kill a Jogre for its bones', kill_for(TB_NPC.JOGRE, TB_TILE.JOGRES, [TB_ID.JOGRE_BONES], 'Jogre bones'))
    return custom('burn the Jogre bones', burn_jogre_bones)


def tinsay_leg(snap, stage):
    if stage < TB_TINSAY.FETCH_RUM:
        return custom('bring Tinsay the news', meet_tinsay)
    # Handing an item over sets the "given" stage; only the next talk asks for the one after it.
    if stage == TB_TINSAY.GIVEN_RUM or stage == TB_TINSAY.GIVEN_SANDWICH:
        return custom('ask Tinsay what he needs next', meet_tinsay)
    if stage == TB_TINSAY.FETCH_RUM:
        return rum_leg(snap)
    if stage == TB_TINSAY.FETCH_SANDWICH:
        return sandwich_leg(snap)
    return bones_leg(snap)


def tiadeche_manual_leg(snap):
    if held_id(snap, TB_ID.CRAFTING_MANUAL) > 0:
        return custom('give Tiadeche the crafting manual', give_manual)
    vessel = vessel_held(snap)
    if vessel == 0:
        return custom('ask Lubufu for another Karambwan vessel', spare_vessel)
    return custom('take a vessel to Tinsay for the crafting instructions', lambda log: use_on_npc(vessel, TB_NPC.TINSAY, TB_TILE.TINSAY, [], log))


def decide(snap):
    if snap.journal == 'unknown':
        return wait('quest journal not loaded')
    if snap.journal == 'complete':
        return Record({'kind': 'done'})
    main = snap.stage
    if main is None:
        return wait('Tai Bwo Wannai Trio stage not readable')
    # The hunt teleports the player into a sealed instance; nothing out there can be acted on from it.
    if in_cutscene(snap.tile):
        return wait('watching Tamayu hunt the Shaikahan')
    if main >= TB_MAIN.ALL_BROTHERS:
        return custom("claim Timfraku's reward", claim_reward)
    # Why: Timfraku is across a 30gp ferry each way, so the pack is filled before the first crossing, ferry coin included.
    kit = prepare(snap)
    if kit:
        return kit
    if main <= TB_MAIN.ASKED_FOR_HELP:
        return custom('ask Timfraku for the job', start_quest)
    lubufu = lubufu_stage(snap)
    tiadeche = tiadeche_stage(snap)
    tamayu = tamayu_stage(snap)
    tinsay = tinsay_stage(snap)
    # The vessel is the spine: Tiadeche cannot catch without it and Tinsay will not write without one.
    if lubufu < TB_LUBUFU.COMPLETE:
        return lubufu_leg(snap, lubufu)
    # His first catch is the raw Karambwan the poisoned spear is ground from.
    if tiadeche < TB_TIADECHE.REQUEST_MANUAL:
        return tiadeche_catch_leg(snap, tiadeche)
    if tamayu < TB_TAMAYU.COMPLETE:
        return tamayu_leg(snap, tamayu)
    if tinsay < TB_TINSAY.COMPLETE:
        return tinsay_leg(snap, tinsay)
    if tiadeche < TB_TIADECHE.COMPLETE:
        return tiadeche_manual_leg(snap)
    return wait('all four brothers are done — waiting for the quest varp to catch up')


def observe(snap, step=None):
    return [f'lubufu={lubufu_stage(snap)} tiadeche={tiadeche_stage(snap)} tamayu={tamayu_stage(snap)}' + f' tinsay={tinsay_stage(snap)} agility={has_flag(snap.progress, TB_FLAG.AGILITY)} spear={has_flag(snap.progress, TB_FLAG.SPEAR)}']


from rs2004.quests.defs.tbwt.loadout import TB_FOODS

tbwt = QuestModule(**{
    'food': FOOD_TARGET,
    'sustain': Record({'foods': TB_FOODS, 'eat_below_hp': 0.5}),
    'record': quest_record('tbwt'),
    # Why: Karamja has no bank until Shilo Village is complete, and Ardougne West is the nearest booth to the Brimhaven ferry.
    'bank': TB_TILE.ARDOUGNE_BANK,
    'owns_inventory': True,
    'read_progress': read_tbwt_progress,
    'warn_readiness': lambda: readiness(lambda skill: skills.level(skill)),
    'observe': observe,
    'decide': decide,
})
