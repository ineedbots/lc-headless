"""Ported from rs2b0t's src/bot/api/ai/quests/defs/regicide/index.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.game import skills
from rs2004.messages import game_messages
from rs2004.quests.data import quest_record
from rs2004.quests.defs.regicide.areas import RG_ITEM, RG_MIXES, RG_TILE, carried, count_held, held, regicide_area
from rs2004.quests.defs.regicide.bomb import catch_rabbit, cook_rabbit, distil_naphtha, fill_tar, fuse_bomb, grind_quicklime, grind_sulphur, heat_quicklime, mix_bomb, take_barrel, take_pot, take_sulphur, weave_cloth
from rs2004.quests.defs.regicide.finish import feed_lazy_guard, fire_catapult, meet_arianwyn, report_to_iorwerth, report_to_lathas
from rs2004.quests.defs.regicide.isafdar import ask_iorwerth, ask_tracker, brief_from_lathas, enter_camp, follow_tracks, kill_soldier, meet_scouts, take_summons
from rs2004.quests.defs.regicide.journal import RG_FLAG, RG_STAGE, read_regicide_progress
from rs2004.quests.defs.regicide.pack import manage_pack
from rs2004.quests.defs.regicide.pass_ import enter_tirannwn, leave_tirannwn
from rs2004.quests.defs.regicide.pockets import pocket_at
from rs2004.quests.defs.regicide.supplies import COAL_TARGET, KEEP_IDS, KIT, RETURN_KIT, STILL_FOOD, bow_carried, kit_shortfall, source_coal, source_kit
from rs2004.quests.defs.upass import inside_pass
from rs2004.quests.defs.upass.supplies import BOW_IDS, draw_gear, melee_carried, wear_gear
from rs2004.quests.engine.types import QuestModule, has_flag
from rs2004.quests.engine.trace import format_tile

__all__ = ['decide', 'regicide']

def custom(name, run):
    return (Record({'kind': 'custom', 'name': name, 'run': run}))


def flag(snap, name):
    return has_flag(snap.progress, name)


# Why: Distillation and forest pickups need free slots; deposit only when removable items exist or the planner repeats a no-op bank step.
SLOTS_NEEDED = 6


def outfit(snap, area):
    """Everything Tirannwn consumes, drawn and worn while a bank is still reachable."""
    if area != 'mainland':
        return None
    junk = any([not (id in KEEP_IDS) for id in (snap.inv_ids if snap.inv_ids is not None else {}).keys()])
    if junk and ((snap.free_slots if snap.free_slots is not None else SLOTS_NEEDED)) < SLOTS_NEEDED:
        return Record({'kind': 'deposit', 'keep': [RG_ITEM.SHARK.name], 'keep_ids': KEEP_IDS, 'bank': RG_TILE.ARDOUGNE_BANK})
    _v3 = wear_gear(snap, 'weapon')
    return (_v3 if _v3 is not None else source_kit(snap))


# Why: past the Arandar palisade there's one shop and no bank, and the way back in is the Underground Pass walked end to end, so a pack short of the kit stops on the mainland and says what's missing.
def ready_for_tirannwn(snap, kit):
    missing = kit_shortfall(snap, kit)
    # Why: The route crosses aggressive soldiers, elf warriors, and a grizzly bear with no equipment source beyond the gate.
    if not melee_carried(snap):
        missing.append('a melee weapon (the soldiers and the elf warriors), have none')
    return (None if len(missing) == 0 else Record({'kind': 'wait', 'reason': f"not equipped for Tirannwn: {'; '.join(missing)}"}))


# Why: the fire arrow is built inside the pass with Koftik's damp cloth in hand, and `make_clotharrow` tests `inv_itemspace` before it deletes the cloth. 2 spare slots is the cloth and the arrow it becomes; a pack that crosses full reads "You don't have space to do that." at the bridge with no bank within an hour's walk.
FIRE_ARROW_SLOTS = 3


# Why: the walk back is planned. `sourceKit` only adds, so a pack that finished the still crosses carrying leftover coal and food with no room for the fire arrow. The leftovers have to be banked on the way past, which a kit list can't say and a plan can.
def return_run():
    return (Record({
        'what': 'the walk back through the pass',
        'allow': list(BOW_IDS),
        'caps': [(Record({'item': supply.item, 'qty': supply.qty})) for supply in [supply for supply in RETURN_KIT if supply.item.id != RG_ITEM.SHORTBOW.id]],
        'free_needed': FIRE_ARROW_SLOTS,
    }))


def cross_in(snap):
    """Into Tirannwn the only way it opens before the deed is done: the pass, and the Well of Voyage."""
    carrying_bomb = held(snap, RG_ITEM.BARREL_FUSED) > 0 or held(snap, RG_ITEM.BARREL_LID) > 0
    kit = (RETURN_KIT if carrying_bomb else KIT)
    # Why: shaped only on the mainland: from inside the pass a bank step aims the walk at Ardougne, the wrong side of every crossing already made.
    if regicide_area(snap.tile) == 'mainland':
        _v4 = ((manage_pack(snap, return_run()) if carrying_bomb else None))
        shaped = (_v4 if _v4 is not None else source_kit(snap, kit))
        if shaped:
            return shaped
    _v5 = ready_for_tirannwn(snap, kit)
    return (_v5 if _v5 is not None else custom('walk the Underground Pass to the Well of Voyage', enter_tirannwn))


def in_tirannwn(snap, area, step):
    return (step if area == 'tirannwn' else cross_in(snap))


# The bomb
def barrel_in_play(snap):
    """True once the barrel is somewhere along the naphtha chain, so a second one is not fetched."""
    return held(snap, RG_ITEM.BARREL_TAR) > 0 or held(snap, RG_ITEM.BARREL_NAPHTHA) > 0 or count_held(snap, RG_MIXES) > 0 or held(snap, RG_ITEM.BARREL_LID) > 0 or held(snap, RG_ITEM.BARREL_FUSED) > 0


def quicklime_done(snap):
    return held(snap, RG_ITEM.QUICKLIME_DUST) > 0 or held(snap, RG_ITEM.MIX_QUICKLIME) > 0 or held(snap, RG_ITEM.BARREL_LID) > 0 or held(snap, RG_ITEM.BARREL_FUSED) > 0


def sulphur_done(snap):
    return held(snap, RG_ITEM.SULPHUR_DUST) > 0 or held(snap, RG_ITEM.MIX_SULPHUR) > 0 or held(snap, RG_ITEM.BARREL_LID) > 0 or held(snap, RG_ITEM.BARREL_FUSED) > 0


def cloth_done(snap):
    return held(snap, RG_ITEM.CLOTH) > 0 or held(snap, RG_ITEM.BARREL_FUSED) > 0


def rabbit_done(snap):
    return held(snap, RG_ITEM.RAW_RABBIT) > 0 or held(snap, RG_ITEM.COOKED_RABBIT) > 0


# Why: every raw ingredient is inside Tirannwn and the still that turns tar into naphtha is in Rimmington, so the gathering finishes in one pass through the forest; the way back in is the Underground Pass, and nobody wants to walk it twice for a forgotten ball of wool.
# Why: ordered by where each thing is: the loom, the barrel and the pot are in the elf camp, the tar and the sulphur in the old camp's swamp, and the quarry on the way out to the palisade. What the forest can't finish is left for the mainland leg.
def near_quarry(tile):
    """True once the quarry is close enough that the generic mining step can walk the rest itself."""
    return tile is not None and max(abs(tile.x - RG_TILE.QUARRY.x), abs(tile.z - RG_TILE.QUARRY.z)) <= 12


def gather_leg(snap):
    """The next thing the forest still owes the bomb, or null once the pack can leave."""
    if not cloth_done(snap):
        return custom('weave the balls of wool into cloth', weave_cloth)
    if not quicklime_done(snap) and held(snap, RG_ITEM.POT) == 0:
        return custom('take a pot from the elf camp', take_pot)
    if not barrel_in_play(snap):
        return (custom('take an empty barrel from the elf camp', take_barrel) if held(snap, RG_ITEM.BARREL) == 0 else custom('fill the barrel from the coal-tar seep', fill_tar))
    if not rabbit_done(snap):
        return custom('catch a rabbit for the catapult guard', catch_rabbit)
    if not sulphur_done(snap):
        return (custom('break a lump off a sulphur formation', take_sulphur) if held(snap, RG_ITEM.SULPHUR) == 0 else custom('grind the sulphur to dust', grind_sulphur))
    if not quicklime_done(snap) and held(snap, RG_ITEM.QUICKLIME) == 0 and held(snap, RG_ITEM.LIMESTONE) == 0:
        # Why: the quarry is on the Arandar side of the palisade and `regicideArea` still calls that Tirannwn, so the gathering leg owns it, but the walk crosses a seam. A bare `mineRock` anchors a plain `walkResilient`, which from any forest pocket answers "no path to (2323,3269): unreachable" and mines nothing.
        return (Record({
            'kind': 'mine_rock',
            'rock': 'Limestone',
            'item': RG_ITEM.LIMESTONE.name,
            'qty': 1,
            'anchor': RG_TILE.QUARRY,
        }) if near_quarry(snap.tile) else custom('cross out to the Arandar quarry', lambda log: leave_tirannwn(RG_TILE.QUARRY, (snap.stage if snap.stage is not None else RG_STAGE.SPOKEN_IORWERTH2), log)))
    return None


# Why: the coal run carries the chain, the 2 tools that build it and a short food float. Coal doesn't stack, so the 12 the still burns want 12 slots free before the first swing, and the kit is 24 slots and leaves 4.
# Why: the room asked for is what's left to mine. Coal accumulates in the pack, so a plan still asking for 12 free once 6 are held parks a leg one swing from finishing: "needs 12 free slot(s) and the pack has 11".
def coal_run(snap):
    return (Record({
        'what': 'the coal run',
        'allow': [
        RG_ITEM.BARREL_TAR.id,
        RG_ITEM.BARREL_NAPHTHA.id,
        RG_ITEM.CLOTH.id,
        RG_ITEM.SULPHUR_DUST.id,
        RG_ITEM.QUICKLIME_DUST.id,
        RG_ITEM.POT.id,
        RG_ITEM.COOKED_RABBIT.id,
        RG_ITEM.PICKAXE.id,
        RG_ITEM.PESTLE.id,
        RG_ITEM.COAL.id,
    ],
        'caps': [Record({'item': RG_ITEM.SHARK, 'qty': STILL_FOOD})],
        'free_needed': max(0, COAL_TARGET - carried(snap, RG_ITEM.COAL)),
    }))


def mainland_leg(snap):
    """The chemistry the forest can't do: a furnace, a range, coal, and Rimmington's still."""
    if held(snap, RG_ITEM.RAW_RABBIT) > 0:
        return custom('cook the rabbit on the Ardougne range', cook_rabbit)
    if not quicklime_done(snap):
        return (custom('burn the limestone to quicklime', heat_quicklime) if held(snap, RG_ITEM.QUICKLIME) == 0 else custom('grind the quicklime into a pot', grind_quicklime))
    if held(snap, RG_ITEM.BARREL_LID) > 0 or held(snap, RG_ITEM.BARREL_FUSED) > 0:
        return (cross_in(snap) if held(snap, RG_ITEM.BARREL_FUSED) > 0 else custom('stuff the cloth through the barrel as a fuse', fuse_bomb))
    if held(snap, RG_ITEM.BARREL_NAPHTHA) > 0 or count_held(snap, RG_MIXES) > 0:
        return custom('mix the powders into the naphtha', mix_bomb)
    if carried(snap, RG_ITEM.COAL) < COAL_TARGET:
        shaped = manage_pack(snap, coal_run(snap))
        if shaped:
            return shaped
    _v6 = source_coal(snap)
    return (_v6 if _v6 is not None else custom('distil the coal tar into naphtha', distil_naphtha))


def bomb_leg(snap, area):
    if held(snap, RG_ITEM.BARREL_FUSED) > 0:
        if area != 'tirannwn':
            return cross_in(snap)
        # Why: `regicide_cross_over3` clears `^regicide_given_rabbit` whenever it's taken inside mapsquare 34_49 and the walk from the Isafdar entry to the catapult takes that crossing, so the rabbit is handed over beside the catapult, never before setting out.
        return (custom('give the cooked rabbit to the catapult guard', feed_lazy_guard) if held(snap, RG_ITEM.COOKED_RABBIT) > 0 else custom('fire the barrel bomb over the trees', fire_catapult))
    if area == 'tirannwn':
        gather = gather_leg(snap)
        if gather:
            return gather
        return custom('leave Tirannwn through the Arandar palisade', lambda log: leave_tirannwn(RG_TILE.ARDOUGNE_BANK, RG_STAGE.SPOKEN_IORWERTH2, log))
    if area == 'mainland':
        return mainland_leg(snap)
    return cross_in(snap)


def stage_step(snap, area, stage):
    gear = draw_gear(snap, 'weapon')
    if gear:
        return gear
    if stage == RG_STAGE.NOT_STARTED:
        _v7 = outfit(snap, area)
        return (_v7 if _v7 is not None else custom("wait for the King's messenger", take_summons))
    elif stage == RG_STAGE.RECEIVED_MESSAGE:
        _v8 = outfit(snap, area)
        return (_v8 if _v8 is not None else custom('take the commission from King Lathas', brief_from_lathas))
    elif stage == RG_STAGE.SPOKEN_LATHAS:
        _v9 = outfit(snap, area)
        return (_v9 if _v9 is not None else in_tirannwn(snap, area, custom('stand still for the elf scouts', meet_scouts)))
    elif stage == RG_STAGE.SPOKEN_SCOUTS:
        return in_tirannwn(snap, area, custom('report to Lord Iorwerth', lambda log: ask_iorwerth(stage, log)))
    elif stage == RG_STAGE.SPOKEN_IORWERTH:
        return in_tirannwn(snap, area, custom('find the tracker at the old camp', lambda log: ask_tracker(stage, log)))
    elif stage == RG_STAGE.SPOKEN_TRACKER:
        # Why: the tracker wants proof, and Iorwerth only hands the pendant over once he's been asked.
        return in_tirannwn(snap, area, (custom('show the tracker the crystal pendant', lambda log: ask_tracker(stage, log)) if carried(snap, RG_ITEM.PENDANT) > 0 or flag(snap, RG_FLAG.PENDANT) else custom('ask Lord Iorwerth for a token of his trust', lambda log: ask_iorwerth(stage, log))))
    elif stage == RG_STAGE.SHOWN_PENDANT:
        return in_tirannwn(snap, area, custom('search the west end of the old camp', follow_tracks))
    elif stage == RG_STAGE.FOUND_FOOTPRINTS:
        return in_tirannwn(snap, area, custom('ask the tracker how to follow the tracks', lambda log: ask_tracker(stage, log)))
    elif stage == RG_STAGE.SPOKEN_TRACKER2:
        return in_tirannwn(snap, area, custom('kill the soldier in the dense wood', kill_soldier))
    elif stage == RG_STAGE.DEFEATED_GUARD:
        return in_tirannwn(snap, area, custom("squeeze into King Tyras's camp", enter_camp))
    elif stage == RG_STAGE.ENTERED_CAMP:
        return in_tirannwn(snap, area, custom('tell Lord Iorwerth where the camp is', lambda log: ask_iorwerth(stage, log)))
    elif stage == RG_STAGE.SPOKEN_IORWERTH2:
        return bomb_leg(snap, area)
    elif stage == RG_STAGE.KILLED_TYRAS:
        return in_tirannwn(snap, area, custom('tell Lord Iorwerth the deed is done', report_to_iorwerth))
    elif stage == RG_STAGE.REPORTED_IORWERTH:
        return (custom('leave Tirannwn through the Arandar palisade', lambda log: leave_tirannwn(RG_TILE.ARDOUGNE_BANK, stage, log)) if area == 'tirannwn' else custom('take the Ardougne road past Arianwyn', meet_arianwyn))
    elif stage == RG_STAGE.SPOKEN_ARIANWYN:
        return (custom('leave Tirannwn through the Arandar palisade', lambda log: leave_tirannwn(RG_TILE.ARDOUGNE_BANK, stage, log)) if area == 'tirannwn' else custom('hand King Lathas the letter', report_to_lathas))
    else:
        return Record({'kind': 'wait', 'reason': f'Regicide stage {stage} is not implemented'})


def decide(snap):
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    area = regicide_area(snap.tile)
    if area == 'unknown':
        return Record({'kind': 'wait', 'reason': 'player location unavailable'})
    if snap.journal == 'complete' or ((snap.stage if snap.stage is not None else -1)) >= RG_STAGE.COMPLETE:
        return Record({'kind': 'done'})
    if snap.stage is None:
        return Record({'kind': 'wait', 'reason': 'Regicide journal stage unavailable'})
    return stage_step(snap, area, snap.stage)


def observe(snap, step):
    at = snap.tile
    pocket = (pocket_at(at) if at and at.level == 0 else None)

    # Why: hand-labelled, because the 5 barrel states all begin with "Barrel" and a name-derived key prints `barrel=0 barrel=0 barrel=0`, saying nothing about where along the chain the bomb is.
    def kit(label, item):
        return f'{label}={held(snap, item)}'

    said = ' / '.join([m.text for m in game_messages.recent(3)])
    where = f'/{pocket}' if pocket else ''
    stage = snap.stage if snap.stage is not None else '?'
    free = snap.free_slots if snap.free_slots is not None else '?'
    doing = step.name if step.kind == 'custom' else step.kind
    bow = 1 if bow_carried(snap) else 0
    pack = ' '.join([
        kit('summons', RG_ITEM.SUMMONS),
        kit('letter', RG_ITEM.MESSAGE),
        kit('pendant', RG_ITEM.PENDANT),
        kit('spade', RG_ITEM.SPADE),
        kit('rope', RG_ITEM.ROPE),
        kit('arrows', RG_ITEM.BRONZE_ARROW),
        f'bow={bow}',
        kit('tinderbox', RG_ITEM.TINDERBOX),
        kit('coal', RG_ITEM.COAL),
        kit('rabbit', RG_ITEM.COOKED_RABBIT),
        kit('food', RG_ITEM.SHARK),
    ])
    bomb = ' '.join([
        kit('empty', RG_ITEM.BARREL),
        kit('tar', RG_ITEM.BARREL_TAR),
        kit('naphtha', RG_ITEM.BARREL_NAPHTHA),
        kit('lidded', RG_ITEM.BARREL_LID),
        kit('fused', RG_ITEM.BARREL_FUSED),
        kit('cloth', RG_ITEM.CLOTH),
        kit('sulphur', RG_ITEM.SULPHUR_DUST),
        kit('quicklime', RG_ITEM.QUICKLIME_DUST),
    ])
    hp = round(skills.hp_fraction() * 100)
    return [
        f'regicide: stage={stage} {format_tile(at)} area={regicide_area(at)}{where} step={doing} free={free} hp={hp}%',
        f'regicide: {pack} | bomb: {bomb}',
        ('regicide: the server has said nothing recently' if said == '' else f'regicide: last said — {said}'),
    ]


def inside_regicide(t):
    """Where a restart has no route to a booth until the quest walks it out: the forest, its pits and the pass."""
    return t is not None and (regicide_area(t) in ('tirannwn', 'voyage', 'pit') or inside_pass(t))


regicide = QuestModule(**{
    'record': quest_record('regicide'),
    'bank': RG_TILE.ARDOUGNE_BANK,
    'owns_inventory': True,
    'read_progress': read_regicide_progress,
    'resume_at': inside_regicide,
    'sustain': Record({'foods': [RG_ITEM.SHARK.name], 'eat_below_hp': 0.7}),
    'warn_readiness': lambda: f'Regicide needs Underground Pass complete, Agility 56 and Crafting 10, and burns about {COAL_TARGET} coal at the still.',
    'observe': observe,
    'decide': decide,
})

