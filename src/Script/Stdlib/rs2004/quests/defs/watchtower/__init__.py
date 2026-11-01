"""Ported from rs2b0t's src/bot/api/ai/quests/defs/watchtower/index.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.data import quest_record
from rs2004.quests.defs.watchtower.areas import CRYSTALS, RELIC_PARTS, WT_ITEM, WT_TILE, watchtower_area
from rs2004.quests.defs.watchtower.caves import answer_mad_skavid, learn_from_scared_skavid, learn_word, leave_cave, next_skavid_cave, take_nightshade
from rs2004.quests.defs.watchtower.enclave import dissolve_shamans, enter_enclave, leave_enclave, mine_dalgroth, search_shaman_robe
from rs2004.quests.defs.watchtower.gutanoth import CHASM_TOLL, answer_riddle, ask_riddle, cross_battlement, jump_back, leave_lower_city, show_relic_to_guard, steal_rock_cake
from rs2004.quests.defs.watchtower.journal import WATCHTOWER_STAGE, read_watchtower_progress
from rs2004.quests.defs.watchtower.potion import brew_ogre_potion, grind_bat_bones, infuse_potion
from rs2004.quests.defs.watchtower.supplies import bank_only, banked, held, make_room, owned, quest_kit, scan_bank, source_coins, source_death_rune, source_food, source_light_source, source_pestle, source_pickaxe, source_rope, source_vial, withdraw_from
from rs2004.quests.defs.watchtower.tower import ask_wizard_about_shamans, ask_wizard_for_relic, give_relic_part, hand_in_fingernails, leave_wizard_floor, pull_lever, read_spell_scroll, relic_state, search_evidence_bush, show_crystals_to_wizard, start_quest
from rs2004.quests.defs.watchtower.tribes import JANGERBERRY_TARGET, kill_gorad, leave_grew_island, leave_toban_camp, open_toban_chest, pick_jangerberries, talk_to_grew, talk_to_og, talk_to_toban
from rs2004.quests.engine.types import QuestModule, flag_value, has_flag

__all__ = ['decide', 'watchtower']

# Enough for both chasm tolls, a death rune and the odd shop trip.
CITY_PURSE = 2000
# Enough to survive a respawned shaman on the way to the rock.
ENCLAVE_FOOD = 8


def escape_pocket(area, wanted):
    if area == wanted:
        return None
    if area in ['towerFloor', 'mirrorTower']:
        return Record({'kind': 'custom', 'name': 'climb down from the wizard floor', 'run': leave_wizard_floor})
    elif area == 'grewIsland':
        return Record({'kind': 'custom', 'name': 'swing back off Grew island', 'run': leave_grew_island})
    elif area == 'tobanCamp':
        return Record({'kind': 'custom', 'name': "leave Toban's camp", 'run': leave_toban_camp})
    elif area == 'cityGuard':
        return Record({'kind': 'custom', 'name': 'jump back out of the city-guard pocket', 'run': jump_back})
    elif area == 'skavidCaves':
        return Record({'kind': 'custom', 'name': 'leave the skavid cave', 'run': leave_cave})
    elif area == 'enclave':
        return Record({'kind': 'custom', 'name': 'leave the shaman enclave', 'run': leave_enclave})
    elif area == 'lowerCity':
        # The battlement is a two-way climb once the market gift is paid.
        return Record({'kind': 'custom', 'name': 'climb back over the battlement', 'run': leave_lower_city})
    else:
        return None


# Why: `wanted` is where the step's own leg expects to begin, and the open mainland always qualifies, as every leg can walk from there.
def at(area, wanted, step):
    """Take `step` only once somewhere it can start from, escaping any other sealed pocket first."""
    _v1 = escape_pocket(area, wanted)
    return (_v1 if _v1 is not None else step)


def need_rope(snap, area):
    """Each trip onto Grew's island consumes one rope; the swing back out is free."""
    return (None if area == 'grewIsland' else source_rope(snap))


def stage_tribes(snap, area):
    progress = snap.progress
    if not has_flag(progress, 'helped-og'):
        if held(snap, WT_ITEM.STOLEN_GOLD.id) > 0 or not has_flag(progress, 'spoken-og'):
            return at(area, 'yanille', Record({'kind': 'custom', 'name': 'talk to Og', 'run': talk_to_og}))
        if held(snap, WT_ITEM.TOBAN_KEY.id) > 0:
            return at(area, 'tobanCamp', Record({'kind': 'custom', 'name': "take the stolen gold from Toban's chest", 'run': open_toban_chest}))
        return at(area, 'yanille', Record({'kind': 'custom', 'name': 'ask Og for another chest key', 'run': talk_to_og}))
    if not has_flag(progress, 'helped-toban'):
        if held(snap, WT_ITEM.DRAGON_BONES.id) > 0 or not has_flag(progress, 'spoken-toban'):
            return at(area, 'tobanCamp', Record({'kind': 'custom', 'name': 'talk to Toban', 'run': talk_to_toban}))
        bones = bank_only(snap, WT_ITEM.DRAGON_BONES)
        return (at(area, 'yanille', bones) if bones else at(area, 'tobanCamp', Record({'kind': 'custom', 'name': 'talk to Toban', 'run': talk_to_toban})))
    if not has_flag(progress, 'helped-grew'):
        if held(snap, WT_ITEM.OGRE_TOOTH.id) > 0 or not has_flag(progress, 'spoken-grew'):
            rope = need_rope(snap, area)
            return (at(area, 'yanille', rope) if rope else at(area, 'grewIsland', Record({'kind': 'custom', 'name': 'talk to Grew', 'run': talk_to_grew})))
        return at(area, 'tobanCamp', Record({'kind': 'custom', 'name': "knock out one of Gorad's teeth", 'run': kill_gorad}))
    short_of_berries = owned(snap, WT_ITEM.JANGERBERRIES.id) < JANGERBERRY_TARGET
    pick_berries = Record({'kind': 'custom', 'name': 'pick jangerberries on Grew island', 'run': pick_jangerberries})
    # Already on the island: take the berries now, as coming back costs another rope.
    if short_of_berries and area == 'grewIsland':
        return pick_berries
    for part in RELIC_PARTS:
        if held(snap, part.id) > 0 and not (part.id in relic_state.refused):
            return at(area, 'towerFloor', Record({
                'kind': 'custom',
                'name': f'give {part.name} to the wizard',
                'run': lambda log: give_relic_part(part.id, log),
            }))
    if short_of_berries:
        rope = need_rope(snap, area)
        return (at(area, 'yanille', rope) if rope else at(area, 'grewIsland', pick_berries))
    replacement = ask_for_lost_part(snap, area)
    if replacement is not None:
        return replacement
    _v2 = escape_pocket(area, 'yanille')
    return (_v2 if _v2 is not None else Record({'kind': 'wait', 'reason': 'every tribe is helped but no relic part is in the pack'}))


# Each tribe hands over another part when theirs is lost; Grew, who costs a rope, goes last.
RELIC_SOURCES = [
    [WT_ITEM.RELIC_PART1, 'Og', 'yanille', talk_to_og],
    [WT_ITEM.RELIC_PART3, 'Toban', 'tobanCamp', talk_to_toban],
    [WT_ITEM.RELIC_PART2, 'Grew', 'grewIsland', talk_to_grew],
]


def asking(part_id, talk):
    def run(log):
        result = yield from talk(log)
        if result:
            relic_state.asked.add(part_id)
        return result
    return run


# Why: a death drops the tribes' parts, and with every tribe helped nothing else in the stage gets them back.
def ask_for_lost_part(snap, area):
    """Ask the next tribe not yet asked for a replacement part, or None once all have been."""
    for part, tribe, where, talk in RELIC_SOURCES:
        if held(snap, part.id) > 0 or part.id in relic_state.asked:
            continue
        if where == 'grewIsland':
            rope = need_rope(snap, area)
            if rope:
                return at(area, 'yanille', rope)
        return at(area, where, Record({'kind': 'custom', 'name': f'ask {tribe} for the lost relic part', 'run': asking(part.id, talk)}))
    return None


def stage_relic_gate(snap, area):
    if held(snap, WT_ITEM.OGRE_RELIC.id) > 0:
        _v3 = escape_pocket(area, 'yanille')
        return (_v3 if _v3 is not None else Record({'kind': 'custom', 'name': 'show the relic to the north-west ogre guard', 'run': show_relic_to_guard}))
    if not snap.bank_known:
        return at(area, 'yanille', scan_bank())
    if banked(snap, WT_ITEM.OGRE_RELIC.id) > 0:
        return at(area, 'yanille', withdraw_from([{'name': WT_ITEM.OGRE_RELIC.name, 'id': WT_ITEM.OGRE_RELIC.id, 'qty': 1}]))
    return at(area, 'towerFloor', Record({'kind': 'custom', 'name': 'ask the wizard for another relic', 'run': ask_wizard_for_relic}))


def stage_city_entry(snap, area):
    if area == 'cityGuard':
        return Record({'kind': 'custom', 'name': 'ask the city guard for passage', 'run': ask_riddle})
    if not has_flag(snap.progress, 'market-paid'):
        if held(snap, WT_ITEM.ROCK_CAKE.id) == 0:
            return Record({'kind': 'custom', 'name': 'steal a rock cake from the ogre stall', 'run': steal_rock_cake})
        return Record({'kind': 'custom', 'name': 'give the rock cake to the battlement guard', 'run': cross_battlement})
    purse = (source_coins(snap, CITY_PURSE) if held(snap, WT_ITEM.COINS.id) < CHASM_TOLL * 2 else None)
    return (at(area, 'yanille', purse) if purse else Record({'kind': 'custom', 'name': 'pay the ogre guard, jump the chasm, ask the riddle', 'run': ask_riddle}))


def stage_riddle(snap, area):
    # Banking and shopping happen on the mainland, so leave the pocket first.
    rune = source_death_rune(snap)
    if rune:
        return at(area, 'yanille', rune)
    purse = (source_coins(snap, CITY_PURSE) if held(snap, WT_ITEM.COINS.id) < CHASM_TOLL * 2 else None)
    return (at(area, 'yanille', purse) if purse else Record({'kind': 'custom', 'name': 'answer the riddle with a death rune', 'run': answer_riddle}))


# Why: a cave mouth refuses entry without the map and a lit light source, and bounces you to a fixed tile, which loops forever if the kit was banked or lost.
def need_cave_kit(snap, area):
    """The cave kit shortfall, or null when both are held."""
    if held(snap, WT_ITEM.SKAVID_MAP.id) == 0:
        in_bank = bank_only(snap, WT_ITEM.SKAVID_MAP)
        if in_bank and in_bank.kind == 'withdraw':
            return at(area, 'yanille', in_bank)
        return Record({'kind': 'custom', 'name': 'ask the city guard for another skavid map', 'run': ask_riddle})
    light = source_light_source(snap)
    return (at(area, 'yanille', light) if light else None)


def stage_caves(snap, area):
    kit = need_cave_kit(snap, area)
    if kit:
        return kit
    cave = next_skavid_cave(snap.progress)
    if cave == 5:
        return Record({
            'kind': 'custom',
            'name': 'learn skavid words from the scared skavid',
            'run': learn_from_scared_skavid,
        })
    if cave <= 4:
        return Record({
            'kind': 'custom',
            'name': f'answer the skavid in cave {cave}',
            'run': lambda log: learn_word(cave, log),
        })
    # Cave 6 is behind the gold-bar gate, so the bar has to be in the pack first.
    bar = bank_only(snap, WT_ITEM.GOLD_BAR)
    return (at(area, 'yanille', bar) if bar else Record({'kind': 'custom', 'name': 'answer the mad skavid for a crystal', 'run': answer_mad_skavid}))


def stage_enclave_entry(snap, area):
    if area == 'enclave':
        return Record({'kind': 'custom', 'name': 'leave the shaman enclave', 'run': leave_enclave})
    if held(snap, WT_ITEM.NIGHTSHADE.id) == 0:
        _v4 = need_cave_kit(snap, area)
        return (_v4 if _v4 is not None else Record({'kind': 'custom', 'name': 'take Nightshade from the skavid cave', 'run': take_nightshade}))
    food = source_food(snap, ENCLAVE_FOOD)
    return (at(area, 'yanille', food) if food else Record({'kind': 'custom', 'name': 'feed the enclave guard Nightshade', 'run': enter_enclave}))


def stage_potion(snap, area):
    if held(snap, WT_ITEM.OGRE_POTION.id) > 0:
        return at(area, 'towerFloor', Record({'kind': 'custom', 'name': 'have the wizard infuse the ogre potion', 'run': infuse_potion}))
    escape = escape_pocket(area, 'yanille')
    if escape:
        return escape
    mid_brew = held(snap, WT_ITEM.GUAM_VIAL.id) > 0 or held(snap, WT_ITEM.GUAM_JANGER_VIAL.id) > 0
    if not mid_brew:
        guam = bank_only(snap, WT_ITEM.GUAM_LEAF)
        if guam:
            return guam
        vial = source_vial(snap)
        if vial:
            return vial
    if held(snap, WT_ITEM.GUAM_JANGER_VIAL.id) == 0 and held(snap, WT_ITEM.JANGERBERRIES.id) == 0:
        _v5 = need_rope(snap, area)
        return (_v5 if _v5 is not None else Record({'kind': 'custom', 'name': 'pick jangerberries on Grew island', 'run': pick_jangerberries}))
    if held(snap, WT_ITEM.GROUND_BAT_BONES.id) == 0:
        bones = bank_only(snap, WT_ITEM.BAT_BONES)
        if bones:
            return bones
        pestle = source_pestle(snap)
        if pestle:
            return pestle
        return Record({'kind': 'custom', 'name': 'grind the bat bones', 'run': grind_bat_bones})
    return Record({'kind': 'custom', 'name': 'brew the ogre potion', 'run': brew_ogre_potion})


def stage_shamans(snap, area):
    _v6 = flag_value(snap.progress, 'shamans-left')
    left = (_v6 if _v6 is not None else 6)
    # Why: dissolved shamans respawn, so any trip back in needs food, but only the steps that go back in.
    # Why: demanding it while carrying the crystals to the wizard parks the quest for no reason.
    enclave_food = (None if area == 'enclave' else source_food(snap, ENCLAVE_FOOD))

    def provisioned(step):
        return ((at(area, 'yanille', enclave_food) if enclave_food else step))

    if left > 0:
        if held(snap, WT_ITEM.MAGIC_OGRE_POTION.id) == 0:
            if area == 'enclave':
                return Record({'kind': 'custom', 'name': 'leave the enclave to brew another potion', 'run': leave_enclave})
            return stage_potion(snap, area)
        if area != 'enclave' and held(snap, WT_ITEM.NIGHTSHADE.id) == 0:
            _v7 = need_cave_kit(snap, area)
            return (_v7 if _v7 is not None else provisioned(Record({'kind': 'custom', 'name': 'take Nightshade for the enclave', 'run': take_nightshade})))
        # The mining follows in the same visit, so the pickaxe rides along and saves a second trip through the guard.
        pick = (None if area == 'enclave' else source_pickaxe(snap))
        if pick:
            return provisioned(at(area, 'yanille', pick))
        return provisioned(Record({'kind': 'custom', 'name': 'dissolve the ogre shamans', 'run': dissolve_shamans}))
    if held(snap, WT_ITEM.CRYSTAL4.id) == 0 and banked(snap, WT_ITEM.CRYSTAL4.id) == 0:
        # Why: no area guard here; standing in the enclave without a pickaxe is the case that has to walk back out for one, and at() does the leaving.
        pick = source_pickaxe(snap)
        if pick:
            return at(area, 'yanille', pick)
        if area != 'enclave' and held(snap, WT_ITEM.NIGHTSHADE.id) == 0:
            _v8 = need_cave_kit(snap, area)
            return (_v8 if _v8 is not None else provisioned(Record({'kind': 'custom', 'name': 'take Nightshade for the enclave', 'run': take_nightshade})))
        return provisioned(Record({'kind': 'custom', 'name': 'mine the Rock of Dalgroth', 'run': mine_dalgroth}))
    if held(snap, WT_ITEM.CRYSTAL3.id) == 0 and banked(snap, WT_ITEM.CRYSTAL3.id) == 0:
        if area != 'enclave' and held(snap, WT_ITEM.NIGHTSHADE.id) == 0:
            _v9 = need_cave_kit(snap, area)
            return (_v9 if _v9 is not None else provisioned(Record({'kind': 'custom', 'name': 'take Nightshade for the enclave', 'run': take_nightshade})))
        return provisioned(Record({'kind': 'custom', 'name': 'search a shaman robe for the third crystal', 'run': search_shaman_robe}))
    if area == 'enclave':
        return Record({'kind': 'custom', 'name': 'leave the shaman enclave', 'run': leave_enclave})
    recovery = recover_crystals(snap)
    if recovery:
        return recovery
    return at(area, 'towerFloor', Record({'kind': 'custom', 'name': 'take all four crystals to the wizard', 'run': show_crystals_to_wizard}))


CRYSTAL_RECOVERY = {
    WT_ITEM.CRYSTAL1.id: Record({'name': 'ask Grew for another crystal', 'run': talk_to_grew}),
    WT_ITEM.CRYSTAL2.id: Record({'name': 'ask the mad skavid for another crystal', 'run': answer_mad_skavid}),
    WT_ITEM.CRYSTAL3.id: Record({'name': 'search a shaman robe for the third crystal', 'run': search_shaman_robe}),
    WT_ITEM.CRYSTAL4.id: Record({'name': 'mine the Rock of Dalgroth again', 'run': mine_dalgroth}),
}


def recover_crystals(snap):
    # Nothing to recover once all four are carried; don't walk to the bank only to learn what's in it.
    lost = ([crystal for crystal in CRYSTALS if held(snap, crystal.id) == 0] or [None])[0]
    if not lost:
        return None
    # Every re-issue check reads the bank as well as the pack, so a banked crystal blocks its own replacement. Withdraw before asking for another.
    in_bank = [crystal for crystal in CRYSTALS if held(snap, crystal.id) == 0 and banked(snap, crystal.id) > 0]
    if len(in_bank) > 0:
        return withdraw_from([{'name': crystal.name, 'id': crystal.id, 'qty': 1} for crystal in in_bank])
    if not snap.bank_known:
        return scan_bank()
    recovery = CRYSTAL_RECOVERY[lost.id]
    return Record({'kind': 'custom', 'name': recovery.name, 'run': recovery.run})


def decide(snap):
    if snap.journal == 'complete' or ((snap.stage if snap.stage is not None else -1)) >= WATCHTOWER_STAGE.COMPLETE:
        if held(snap, WT_ITEM.WATCHTOWER_SPELL.id) > 0:
            return Record({'kind': 'custom', 'name': 'read the Watchtower spell scroll', 'run': read_spell_scroll})
        # Completing teleports into the mirror tower in region 45_73.
        stranded = escape_pocket(watchtower_area(snap.tile), 'yanille')
        return (stranded if stranded is not None else Record({'kind': 'done'}))
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    if snap.stage is None:
        return Record({'kind': 'wait', 'reason': 'Watch Tower journal stage unavailable'})
    area = watchtower_area(snap.tile)
    if area == 'unknown':
        return Record({'kind': 'wait', 'reason': 'player location unavailable'})
    # Why: pulling the lever teleports into the shielded copy of the tower in region 45_73, and nothing else goes there.
    # Why: standing in it means the quest is done, whatever the journal colour has caught up to.
    if area == 'mirrorTower':
        if held(snap, WT_ITEM.WATCHTOWER_SPELL.id) > 0:
            return Record({'kind': 'custom', 'name': 'read the Watchtower spell scroll', 'run': read_spell_scroll})
        return Record({'kind': 'custom', 'name': 'climb down from the activated Watchtower', 'run': leave_wizard_floor})
    # Why: one bank trip for everything the bank can supply; what the bank lacks still falls to the shop, the ground candle and the guard's riddle.
    # Why: bounded to the collecting stages, as past the potion the kit is spent and a trip proves nothing.
    if snap.stage > WATCHTOWER_STAGE.NOT_STARTED and snap.stage <= WATCHTOWER_STAGE.MADE_POTION:
        room = make_room(snap)
        if room:
            return at(area, 'yanille', room)
        kit = quest_kit(snap, ENCLAVE_FOOD)
        if kit:
            return at(area, 'yanille', kit)
    if snap.stage == WATCHTOWER_STAGE.NOT_STARTED:
        return Record({'kind': 'custom', 'name': 'climb the Watchtower and ask the wizard for work', 'run': start_quest})
    elif snap.stage == WATCHTOWER_STAGE.STARTED:
        if held(snap, WT_ITEM.FINGERNAILS.id) > 0:
            return at(area, 'towerFloor', Record({'kind': 'custom', 'name': 'give the fingernails to the wizard', 'run': hand_in_fingernails}))
        _v10 = escape_pocket(area, 'yanille')
        return (_v10 if _v10 is not None else Record({
            'kind': 'custom',
            'name': 'search the bush by the Watchtower for evidence',
            'run': search_evidence_bush,
        }))
    elif snap.stage == WATCHTOWER_STAGE.GIVEN_FINGERNAILS:
        return (stage_relic_gate(snap, area) if owned(snap, WT_ITEM.OGRE_RELIC.id) > 0 else stage_tribes(snap, area))
    elif snap.stage == WATCHTOWER_STAGE.MADE_RELIC:
        return stage_relic_gate(snap, area)
    elif snap.stage == WATCHTOWER_STAGE.GIVEN_RELIC:
        return stage_city_entry(snap, area)
    elif snap.stage == WATCHTOWER_STAGE.GIVEN_RIDDLE:
        return stage_riddle(snap, area)
    elif snap.stage == WATCHTOWER_STAGE.SOLVED_RIDDLE:
        return stage_caves(snap, area)
    elif snap.stage == WATCHTOWER_STAGE.SKAVID_CRYSTAL:
        return stage_enclave_entry(snap, area)
    elif snap.stage == WATCHTOWER_STAGE.FED_NIGHTSHADE:
        return at(area, 'towerFloor', Record({'kind': 'custom', 'name': 'ask the wizard how to beat the shamans', 'run': ask_wizard_about_shamans}))
    elif snap.stage == WATCHTOWER_STAGE.LEARNED_POTION:
        return stage_potion(snap, area)
    elif snap.stage == WATCHTOWER_STAGE.MADE_POTION:
        return stage_shamans(snap, area)
    elif snap.stage == WATCHTOWER_STAGE.FOUND_ALL_CRYSTALS:
        return at(area, 'towerFloor', Record({'kind': 'custom', 'name': 'pull the lever to activate the shield', 'run': pull_lever}))
    else:
        return Record({'kind': 'wait', 'reason': 'Watch Tower stage ' + str(snap.stage) + ' is not implemented yet'})


watchtower = QuestModule(**{
    'record': quest_record('itwatchtower'),
    'bank': WT_TILE.YANILLE_BANK,
    'owns_inventory': True,
    'read_progress': read_watchtower_progress,
    'sustain': Record({'foods': ['Lobster', 'Swordfish', 'Tuna'], 'eat_below_hp': 0.6}),
    'decide': decide,
})
