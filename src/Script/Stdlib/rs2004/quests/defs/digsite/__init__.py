"""Ported from rs2b0t's src/bot/api/ai/quests/defs/digsite/index.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.items import inventory
from rs2004.quests.data import quest_record
from rs2004.quests.engine.types import QuestModule
from rs2004.quests.defs.digsite.areas import DIG_ID, DIG_ITEM, DIG_NPC, DIG_TILE, DIG_ZONE, in_altar_cave, in_dig_cave, in_shaft_west
from rs2004.quests.defs.digsite.caves import barrel_leg, blast_leg, chest_leg, leave_cave_step, mix_step, tablet_leg, west_shaft_leg
from rs2004.quests.defs.digsite.common import banked_id, held_id, use_on_npc_id
from rs2004.quests.defs.digsite.exams import DELIVER_GREEN, DELIVER_ORANGE, DELIVER_PURPLE, answered, exam_ready, replace_trowel, search_bush, stamp_letter, study_with_students, talk_to_examiner
from rs2004.quests.defs.digsite.journal import DIG_STAGE, read_digsite_progress
from rs2004.quests.defs.digsite.supplies import SHOP, buy, dig_until, digsite_state, herblore_kit, kit, pan_until, pickpocket_workman, take_specimen_jar

__all__ = ['decide', 'digsite']

ROPE_TARGET = 2


def withdraw(name, qty, id):
    return Record({
        'kind': 'withdraw',
        'items': [{'name': name, 'qty': qty, 'id': id}],
        'bank': DIG_TILE.VARROCK_BANK,
    })


def from_bank(snap, id, name, qty=1):
    """Withdraw it when the bank has one, otherwise fall through to the world source."""
    return (withdraw(name, qty, id) if banked_id(snap, id) > 0 else None)


def custom(name, run):
    return Record({'kind': 'custom', 'name': name, 'run': run})


def use_on_expert(item_id, name, expect):
    return custom(name, lambda log: use_on_npc_id(item_id, DIG_NPC.EXPERT, DIG_TILE.EXPERT, expect, log))


def rope_step(snap):
    if held_id(snap, DIG_ID.ROPE) > 0:
        return None
    banked = from_bank(snap, DIG_ID.ROPE, DIG_ITEM.ROPE, ROPE_TARGET)
    if banked:
        return banked
    return custom(f'pickpocket the workmen for {ROPE_TARGET} ropes', lambda log: pickpocket_workman(lambda: inventory.count_by_id(DIG_ID.ROPE) >= ROPE_TARGET, log))


def tinderbox_step(snap):
    if held_id(snap, DIG_ID.TINDERBOX) > 0:
        return None
    _v1 = from_bank(snap, DIG_ID.TINDERBOX, DIG_ITEM.TINDERBOX)
    return (_v1 if _v1 is not None else buy(DIG_ITEM.TINDERBOX, 1, SHOP.GENERAL, 200))


def trowel_step(snap):
    if held_id(snap, DIG_ID.TROWEL) > 0:
        return None
    _v2 = from_bank(snap, DIG_ID.TROWEL, DIG_ITEM.TROWEL)
    return (_v2 if _v2 is not None else replace_trowel())


# Why: the guide only steps in on a pan he objects to, so the refused attempt is what asks for the tea, and that has to be remembered for one purchase.
def panning_gate(snap):
    """The cup of tea a refused pan asked for, or null while the river is open."""
    if not digsite_state.tea_wanted or held_id(snap, DIG_ID.CUP_OF_TEA) > 0:
        return None
    _v3 = from_bank(snap, DIG_ID.CUP_OF_TEA, DIG_ITEM.CUP_OF_TEA)
    return (_v3 if _v3 is not None else buy(DIG_ITEM.CUP_OF_TEA, 1, SHOP.TEA, 200))


def _holds(id):
    return lambda: inventory.count_by_id(id) > 0


def pan_for(id, label):
    holds = _holds(id)
    return custom(label, lambda log: pan_until(holds, log))


def first_exam_plan(snap):
    """Exam 1 is 3 errands: a stolen sample, a sample in a bush and a sample in the river."""
    if not answered(snap, 'green-answered'):
        if held_id(snap, DIG_ID.ROCK_SAMPLE_GREEN) > 0:
            return DELIVER_GREEN()
        return custom("pickpocket the workmen for the green student's sample", lambda log: pickpocket_workman(lambda: inventory.count_by_id(DIG_ID.ROCK_SAMPLE_GREEN) > 0, log))
    if not answered(snap, 'purple-answered'):
        if held_id(snap, DIG_ID.ROCK_SAMPLE_PURPLE) > 0:
            return DELIVER_PURPLE()
        return search_bush()
    if not answered(snap, 'orange-answered'):
        if held_id(snap, DIG_ID.ROCK_SAMPLE_ORANGE) > 0:
            return DELIVER_ORANGE()
        _v4 = panning_gate(snap)
        return (_v4 if _v4 is not None else pan_for(DIG_ID.ROCK_SAMPLE_ORANGE, "pan the river for the orange student's sample"))
    return talk_to_examiner('sit the first Earth Sciences exam')


def third_exam_plan(snap):
    """Exam 3's third errand is an opal, which the river gives up uncut."""
    if held_id(snap, DIG_ID.OPAL) > 0:
        return study_with_students(DIG_STAGE.THIRD_EXAM)
    if held_id(snap, DIG_ID.UNCUT_OPAL) > 0:
        if held_id(snap, DIG_ID.CHISEL) == 0:
            _v5 = from_bank(snap, DIG_ID.CHISEL, DIG_ITEM.CHISEL)
            return (_v5 if _v5 is not None else buy(DIG_ITEM.CHISEL, 1, SHOP.GENERAL, 200))
        return Record({
            'kind': 'use_on',
            'item': DIG_ITEM.CHISEL,
            'target_kind': 'item',
            'target': DIG_ITEM.UNCUT_OPAL,
            'anchor': DIG_TILE.STUDENTS,
            'product': DIG_ITEM.OPAL,
        })
    _v6 = from_bank(snap, DIG_ID.OPAL, DIG_ITEM.OPAL)
    _v7 = (_v6 if _v6 is not None else from_bank(snap, DIG_ID.UNCUT_OPAL, DIG_ITEM.UNCUT_OPAL))
    _v8 = (_v7 if _v7 is not None else panning_gate(snap))
    return (_v8 if _v8 is not None else pan_for(DIG_ID.UNCUT_OPAL, 'pan the river for an opal'))


def impress_plan(snap):
    """Stage 5: find something on the site worth showing the expert, and take his letter to a workman."""
    if held_id(snap, DIG_ID.EXPERT_SCROLL) > 0:
        return custom('show the invitation letter to a workman', lambda log: use_on_npc_id(DIG_ID.EXPERT_SCROLL, DIG_NPC.WORKMAN, DIG_TILE.WORKMEN, lambda: inventory.count_by_id(DIG_ID.EXPERT_SCROLL) == 0, log))
    if held_id(snap, DIG_ID.TALISMAN) > 0:
        return use_on_expert(DIG_ID.TALISMAN, 'show the Zarosian talisman to the expert', lambda: inventory.count_by_id(DIG_ID.EXPERT_SCROLL) > 0)
    trowel = trowel_step(snap)
    if trowel:
        return trowel
    if held_id(snap, DIG_ID.SPECIMEN_JAR) == 0:
        _v9 = from_bank(snap, DIG_ID.SPECIMEN_JAR, DIG_ITEM.SPECIMEN_JAR)
        return (_v9 if _v9 is not None else custom('search the sacks for a specimen jar', take_specimen_jar))
    if held_id(snap, DIG_ID.SPECIMEN_BRUSH) == 0:
        _v10 = from_bank(snap, DIG_ID.SPECIMEN_BRUSH, DIG_ITEM.SPECIMEN_BRUSH)
        return (_v10 if _v10 is not None else custom('pickpocket the workmen for a specimen brush', lambda log: pickpocket_workman(lambda: inventory.count_by_id(DIG_ID.SPECIMEN_BRUSH) > 0, log)))
    return custom('dig the level 3 site for a find', lambda log: dig_until(DIG_ZONE.LEVEL3, lambda: inventory.count_by_id(DIG_ID.TALISMAN) > 0, log))


def compound_plan(snap, underground):
    """Stage 6: 4 chemicals, 2 of them out of the shaft and the river bank."""

    def held(id):
        return held_id(snap, id)

    mixed = held(DIG_ID.PRE_CHARCOAL) > 0 or held(DIG_ID.POST_CHARCOAL) > 0
    have_nitrate = held(DIG_ID.AMMONIUM_NITRATE) > 0 or mixed
    have_nitro = held(DIG_ID.NITROGLYCERIN) > 0 or mixed
    have_ground = held(DIG_ID.GROUND_CHARCOAL) > 0 or held(DIG_ID.POST_CHARCOAL) > 0
    if held(DIG_ID.COMPOUND) > 0:
        tinderbox = (None if underground else tinderbox_step(snap))
        if tinderbox:
            return tinderbox
        rope = (None if underground else rope_step(snap))
        if rope:
            return rope
        return blast_leg(True)
    need_key = held(DIG_ID.CHEST_KEY) == 0 and held(DIG_ID.POWDER) == 0 and not have_nitrate
    need_root = held(DIG_ID.ARCENIA_ROOT) == 0
    if need_key or need_root:
        if underground:
            return (west_shaft_leg(need_key, need_root) if in_shaft_west(snap.tile) else leave_cave_step())
        _v11 = rope_step(snap)
        return (_v11 if _v11 is not None else west_shaft_leg(need_key, need_root))
    if underground:
        return leave_cave_step()
    # Why: the tinderbox counter is in Varrock and the vial counter in Taverley on the same road, so buying each at the step that needs it walks that road 3 times.
    tinderbox = tinderbox_step(snap)
    if tinderbox:
        return tinderbox
    need_vial = held(DIG_ID.VIAL) == 0 and held(DIG_ID.LIQUID) == 0 and not have_nitro
    need_pestle = held(DIG_ID.PESTLE) == 0 and not have_ground
    if need_vial or need_pestle:
        banked_vial = (from_bank(snap, DIG_ID.VIAL, DIG_ITEM.VIAL) if need_vial else None)
        banked_pestle = (from_bank(snap, DIG_ID.PESTLE, DIG_ITEM.PESTLE) if need_pestle else None)
        banked = banked_vial if banked_vial is not None else banked_pestle
        return banked if banked is not None else herblore_kit(need_vial, need_pestle)
    if not have_nitrate:
        if held(DIG_ID.POWDER) > 0:
            return use_on_expert(DIG_ID.POWDER, 'have the expert identify the powder', lambda: inventory.count_by_id(DIG_ID.AMMONIUM_NITRATE) > 0)
        return chest_leg()
    if not have_nitro:
        if held(DIG_ID.LIQUID) > 0:
            return use_on_expert(DIG_ID.LIQUID, 'have the expert identify the liquid', lambda: inventory.count_by_id(DIG_ID.NITROGLYCERIN) > 0)
        trowel = trowel_step(snap)
        if trowel:
            return trowel
        return barrel_leg()
    if not mixed:
        return mix_step('mix the nitrate into the nitroglycerin', DIG_ID.AMMONIUM_NITRATE, DIG_ID.NITROGLYCERIN, DIG_ID.PRE_CHARCOAL)
    if not have_ground:
        if held(DIG_ID.CHARCOAL) == 0:
            trowel = trowel_step(snap)
            if trowel:
                return trowel
            _v12 = from_bank(snap, DIG_ID.CHARCOAL, DIG_ITEM.CHARCOAL)
            return (_v12 if _v12 is not None else custom('dig the training site for charcoal', lambda log: dig_until(DIG_ZONE.TRAINING, lambda: inventory.count_by_id(DIG_ID.CHARCOAL) > 0, log)))
        return mix_step('grind the charcoal to a powder', DIG_ID.CHARCOAL, DIG_ID.PESTLE, DIG_ID.GROUND_CHARCOAL)
    if held(DIG_ID.POST_CHARCOAL) == 0:
        return mix_step('mix the ground charcoal in', DIG_ID.PRE_CHARCOAL, DIG_ID.GROUND_CHARCOAL, DIG_ID.POST_CHARCOAL)
    return mix_step('mix the arcenia root in', DIG_ID.POST_CHARCOAL, DIG_ID.ARCENIA_ROOT, DIG_ID.COMPOUND)


def plan(snap, stage, underground):
    # Why: every leg but the shaft ones starts on the surface, and a bot left down a one-way winch spends 3 passes proving a surface tile unreachable.
    def surface(step):
        return ((leave_cave_step() if underground else step))

    if stage == DIG_STAGE.NOT_STARTED:
        return surface(talk_to_examiner('ask the Examiner about the Earth Sciences exams'))
    elif stage == DIG_STAGE.STAMPING:
        if held_id(snap, DIG_ID.STAMPED_LETTER) > 0:
            return surface(talk_to_examiner('hand the stamped letter to the Examiner'))
        if held_id(snap, DIG_ID.PLAIN_LETTER) > 0:
            return surface(stamp_letter())
        _v13 = from_bank(snap, DIG_ID.STAMPED_LETTER, DIG_ITEM.STAMPED_LETTER)
        _v14 = (_v13 if _v13 is not None else from_bank(snap, DIG_ID.PLAIN_LETTER, DIG_ITEM.PLAIN_LETTER))
        return surface((_v14 if _v14 is not None else talk_to_examiner('ask the Examiner to replace the lost letter')))
    elif stage == DIG_STAGE.FIRST_EXAM:
        return surface((talk_to_examiner('sit the first Earth Sciences exam') if exam_ready(snap) else first_exam_plan(snap)))
    elif stage == DIG_STAGE.SECOND_EXAM:
        return surface((talk_to_examiner('sit the second Earth Sciences exam') if exam_ready(snap) else study_with_students(DIG_STAGE.SECOND_EXAM)))
    elif stage == DIG_STAGE.THIRD_EXAM:
        return surface((talk_to_examiner('sit the third Earth Sciences exam') if exam_ready(snap) else third_exam_plan(snap)))
    elif stage == DIG_STAGE.IMPRESS_EXPERT:
        return surface(impress_plan(snap))
    elif stage == DIG_STAGE.MINESHAFT_PERMIT:
        return compound_plan(snap, underground)
    elif stage == DIG_STAGE.POURED_COMPOUND:
        if in_altar_cave(snap.tile):
            return tablet_leg()
        tinderbox = (None if underground else tinderbox_step(snap))
        if tinderbox:
            return tinderbox
        rope = (None if underground else rope_step(snap))
        if rope:
            return rope
        return blast_leg(False)
    elif stage == DIG_STAGE.REMOVED_BLOCKAGE:
        if held_id(snap, DIG_ID.STONE_TABLET) > 0:
            return surface(use_on_expert(DIG_ID.STONE_TABLET, 'show the stone tablet to the expert', lambda: inventory.count_by_id(DIG_ID.STONE_TABLET) == 0))
        if underground and not in_altar_cave(snap.tile):
            return leave_cave_step()
        rope = (None if in_altar_cave(snap.tile) else rope_step(snap))
        if rope:
            return rope
        return tablet_leg()
    else:
        return Record({'kind': 'wait', 'reason': f'nothing planned for stage {stage}'})


def decide(snap):
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    if snap.journal == 'complete':
        return Record({'kind': 'done'})
    _v15 = (snap.progress.stage if snap.progress is not None else None)
    stage = (_v15 if _v15 is not None else snap.stage)
    if stage is None:
        return Record({'kind': 'wait', 'reason': 'quest stage not readable'})
    # Why: `ownsInventory` skips the engine's provisioning, so nothing else opens a booth and a banked trowel or vial stays invisible until one read happens.
    if not snap.bank_known:
        return Record({'kind': 'scan_bank', 'bank': DIG_TILE.VARROCK_BANK})
    underground = in_dig_cave(snap.tile)
    # Why: coins and food are the module's own business here, and a shaft has no booth to draw them from.
    supplies = (None if underground else kit(snap))
    if supplies:
        return supplies
    return plan(snap, stage, underground)


def region(snap):
    if in_altar_cave(snap.tile):
        return 'altar cave'
    if in_shaft_west(snap.tile):
        return 'west shaft'
    if in_dig_cave(snap.tile):
        return 'east shaft'
    return 'surface'


def observe(snap, step):
    progress = snap.progress
    stage = progress.stage if progress is not None else snap.stage
    flags = list(progress.flags) if progress is not None else []
    shown = stage if stage is not None else '?'
    return [
        f"stage {shown} · {region(snap)} · flags [{', '.join(flags)}]",
        f"step '{step.name if step.kind == 'custom' else step.kind}' · tea_wanted={digsite_state.tea_wanted}",
    ]


digsite = QuestModule(**{
    'record': quest_record('itexam'),
    'bank': DIG_TILE.VARROCK_BANK,
    'owns_inventory': True,
    'tools': ['coins', 'trowel', 'specimen jar', 'specimen brush', 'panning tray', 'rope', 'vial', 'pestle and mortar', 'tinderbox', 'chisel'],
    'sustain': Record({'foods': ['Lobster', 'Swordfish', 'Tuna'], 'eat_below_hp': 0.5}),
    'read_progress': read_digsite_progress,
    'observe': observe,
    'decide': decide,
})
