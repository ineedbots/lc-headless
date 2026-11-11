"""Ported from rs2b0t's src/bot/api/ai/quests/defs/grandtree/index.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.data import quest_record
from rs2004.quests.defs.grandtree.areas import CHARLIE, GLOUGH, GT_HOPS, GT_ITEMS, GT_OBJ, GT_PILLARS, GT_STAGE, HAZELMERE, NARNODE, NARNODE_UNDER, in_caves, in_karamja, in_stronghold
from rs2004.quests.defs.grandtree.fight import descend_trapdoor, fight_black_demon
from rs2004.quests.defs.grandtree.journal import read_grand_tree_stage
from rs2004.quests.engine.types import QuestModule
from rs2004.quests.defs.grandtree.legs import anita_key, descend_glough_tree, femi_cart, fly_to_karamja, foreman_order, give_rock, jailed_by_glough, leave_caves, open_chest, place_twig, search_cupboard, search_next_root, start_quest
from rs2004.quests.food import FOOD_FLOAT, quest_food
from rs2004.quests.strike import STRIKE_RUNES, prepare_strikes

__all__ = ['decide', 'grandtree']

DEMON_FOOD = 8


def custom(name, run):
    return Record({'kind': 'custom', 'name': name, 'run': run})


def held(snap, id):
    _v1 = (snap.inv_ids.get(id) if snap.inv_ids is not None else None)
    return (_v1 if _v1 is not None else 0)


def food_name():
    return quest_food.name


def keep_list():
    food = (food_name().lower() if food_name() is not None else None)
    return list(GT_ITEMS) + list(STRIKE_RUNES) + ['coins'] + list((([food] if food else [])))


# Why: The King requires two free slots at the start and four at stage 110.
def room_for(snap, slots):
    """Bank junk when the next dialogue needs more free slots."""
    if ((snap.free_slots if snap.free_slots is not None else 28)) >= slots:
        return None
    return Record({'kind': 'deposit', 'keep': keep_list()})


def demon_kit(snap):
    food = food_name()
    if not food:
        return None
    _v2 = snap.inv.get(food.lower())
    missing = DEMON_FOOD - ((_v2 if _v2 is not None else 0))
    if missing <= 0:
        return None
    if not snap.bank_known:
        return Record({'kind': 'scan_bank'})
    _v3 = (snap.bank.get(food.lower()) if snap.bank is not None else None)
    qty = min(missing, (_v3 if _v3 is not None else 0))
    return (Record({'kind': 'withdraw', 'items': [{'name': food, 'qty': qty}]}) if qty > 0 else None)


# Why: the King re-issues twigs whenever none is held, and one already on its pillar counts as neither held nor lost, so only ask with an empty pack at stage 120.
def next_twig(snap):
    """The next twig to lay, or null when the pack holds none."""
    for index in range(len(GT_PILLARS)):
        if held(snap, GT_PILLARS[index].obj) > 0:
            return index
    return None


# Why: Anita re-issues the key and the chest re-issues the plans whenever neither the pack nor the bank holds one, so a death between the two only costs a walk.
def invasion_plans(snap):
    """Fetch the key, unlock the chest, take Glough's invasion plans."""
    return (custom("unlock Glough's chest", open_chest) if held(snap, GT_OBJ.KEY) > 0 else custom('ask Anita for the chest key', anita_key))


def observe(snap, step):
    return [
        f"stage={(snap.stage if snap.stage is not None else '?')} step={step.kind} caves={in_caves(snap.tile)}" + f' stronghold={in_stronghold(snap.tile)} karamja={in_karamja(snap.tile)}',
        f'held: bark={held(snap, GT_OBJ.BARK)} scroll={held(snap, GT_OBJ.SCROLL)}' + f' journal={held(snap, GT_OBJ.JOURNAL)} order={held(snap, GT_OBJ.LUMBER_ORDER)}' + f' key={held(snap, GT_OBJ.KEY)} plans={held(snap, GT_OBJ.INVASION_PLANS)}' + f' twigs={len([p for p in GT_PILLARS if held(snap, p.obj) > 0])}/4 rock={held(snap, GT_OBJ.DACONIA)}',
    ]


def decide(snap):
    if snap.journal == 'complete':
        return Record({'kind': 'done'})
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    stage = snap.stage
    if stage is None:
        return Record({'kind': 'wait', 'reason': 'The Grand Tree journal stage unavailable'})
    # Why: the twig legs live on Glough's pillar floor, a 7-tile pocket with no baked way off it, so the kit is bought on the ground before the first climb.
    # Why: a bank step decided in the pocket has no route and burns its budget proving so, so anyone up there still owing gear climbs back down for it.
    if (stage == GT_STAGE.GIVEN_TWIGS or stage == GT_STAGE.UNLOCKED_TRAPDOOR) and not in_caves(snap.tile):
        _v4 = prepare_strikes(snap, keep_list())
        kit = (_v4 if _v4 is not None else demon_kit(snap))
        if kit:
            _v5 = (snap.tile.level if snap.tile is not None else None)
            return (custom("climb down out of Glough's tree for the kit", descend_glough_tree) if ((_v5 if _v5 is not None else 0)) > 0 else kit)
    # Why: everything past the demon happens in the root caves, whose only mouth before the quest ends is Glough's trapdoor, so a death or a surface resume climbs back down first.
    if stage >= GT_STAGE.DEFEATED_BLACK_DEMON and stage < GT_STAGE.COMPLETE and not in_caves(snap.tile):
        return custom('drop back into the root caves', descend_trapdoor)
    if stage == GT_STAGE.NOT_STARTED:
        _v6 = room_for(snap, 2)
        return (_v6 if _v6 is not None else custom('start the quest with King Narnode', start_quest))
    elif stage == GT_STAGE.STARTED:
        # Why: Hazelmere hands nothing over without the sample, and `~check_narnode_items` replaces a lost one.
        if held(snap, GT_OBJ.BARK) > 0:
            return Record({'kind': 'talk', 'stop': HAZELMERE})
        room = room_for(snap, 2)
        return (room if room is not None else Record({'kind': 'talk', 'stop': NARNODE}))
    elif stage == GT_STAGE.SPOKEN_HAZELMERE:
        return Record({'kind': 'talk', 'stop': NARNODE})
    elif stage == GT_STAGE.RELAYED_MESSAGE:
        return Record({'kind': 'talk', 'stop': GLOUGH})
    elif stage == GT_STAGE.SPOKEN_GLOUGH:
        return Record({'kind': 'talk', 'stop': NARNODE})
    elif stage == GT_STAGE.FOUND_PRISONER:
        return Record({'kind': 'talk', 'stop': CHARLIE})
    elif stage == GT_STAGE.SPOKEN_PRISONER:
        return custom("search Glough's cupboard", search_cupboard)
    elif stage == GT_STAGE.FOUND_JOURNAL:
        return custom('confront Glough and get out of his cage', jailed_by_glough)
    elif stage == GT_STAGE.RELEASED_PRISON:
        return (custom('get the lumber order from the foreman', foreman_order) if in_karamja(snap.tile) else custom('take the glider to Karamja', fly_to_karamja))
    elif stage == GT_STAGE.OBTAINED_LUMBER_ORDER:
        return (Record({'kind': 'talk', 'stop': CHARLIE}) if in_stronghold(snap.tile) else custom("ride Femi's cart into the stronghold", femi_cart))
    elif stage == GT_STAGE.CLUE_CHARLIE:
        return invasion_plans(snap)
    elif stage == GT_STAGE.FOUND_INVASION_PLANS:
        if held(snap, GT_OBJ.INVASION_PLANS) == 0:
            return invasion_plans(snap)
        _v7 = room_for(snap, 4)
        return (_v7 if _v7 is not None else Record({'kind': 'talk', 'stop': NARNODE}))
    elif stage == GT_STAGE.GIVEN_TWIGS:
        twig = next_twig(snap)
        return (Record({'kind': 'talk', 'stop': NARNODE}) if twig is None else custom(f'lay twig {twig + 1} of 4 on its pillar', place_twig(twig)))
    elif stage == GT_STAGE.UNLOCKED_TRAPDOOR:
        return custom('take the trapdoor and kill the Black Demon', fight_black_demon)
    elif stage == GT_STAGE.DEFEATED_BLACK_DEMON:
        return Record({'kind': 'talk', 'stop': NARNODE_UNDER})
    elif stage == GT_STAGE.SEARCHING_DACONIA:
        return (custom('give the King the Daconia rock', give_rock) if held(snap, GT_OBJ.DACONIA) > 0 else custom('search the roots for the Daconia rock', search_next_root))
    else:
        return Record({'kind': 'wait', 'reason': f'unhandled Grand Tree stage {stage}'})


grandtree = QuestModule(**{
    'auto_retaliate': lambda snap: not in_caves(snap.tile),
    'record': quest_record('grandtree'),
    'bank': 'nearest',
    'hops': GT_HOPS,
    'food': FOOD_FLOAT,
    'coin_float': 2000,
    'tools': list(GT_ITEMS) + ['coins'] + list(STRIKE_RUNES),
    'read_stage': read_grand_tree_stage,
    'sustain': Record({'foods': ['Lobster'], 'eat_below_hp': 0.6}),
    'exit': leave_caves,
    'observe': observe,
    'decide': decide,
})
