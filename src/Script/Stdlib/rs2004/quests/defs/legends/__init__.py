"""Ported from rs2b0t's src/bot/api/ai/quests/defs/legends/index.ts (MIT, see thirdparty/rs2b0t)."""

import math
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.entities import npcs
from rs2004.game import skills
from rs2004.items import inventory
from rs2004.messages import game_messages
from rs2004.quests.data import quest_record
from rs2004.quests.defs.legends.areas import LQ_ID, LQ_ITEM, LQ_NPC, LQ_SHOP, LQ_STAGE, legends_area
from rs2004.quests.defs.legends.fight import fight
from rs2004.quests.defs.legends.gather import BRAVERY_HERBS, identify_herb, pick_herb
from rs2004.quests.defs.legends.guild import enter_guild, hand_in_totem, replace_map, start_quest, take_machete, take_training
from rs2004.quests.defs.legends.journal import read_legends_progress
from rs2004.quests.defs.legends.jungle import enter_jungle, get_bullroarer, leave_jungle, map_jungle, talk_gujuo
from rs2004.quests.defs.legends.pockets import legends_pocket
from rs2004.quests.defs.legends.scene import drive_until
from rs2004.quests.defs.legends.shaman import ask_for_seeds, ask_gujuo_for_water, bless_bowl, cut_reed, enter_octagram, enter_shaman_cave, fill_bowl_from_pool, find_pool_dried, germinate_seeds, make_golden_bowl, speak_to_ungadulu, summon_demon
from rs2004.quests.defs.legends.supplies import BANK_ONLY_KIT, DESCENT_KIT, FOOD_FOR_SLOT, LEG_BANK, LQ_FOODS, ORB_RUNE_KIT, PRAYER_POTIONS, RUNE_KIT, SHOP_GP, coin_top_up, deposit, ditch_ids, dress_for_combat, food_top_up, from_bank, held, held_food, junk_held, owned, potion_top_up, pots_banked, pots_held, provision, source_bank_only, source_from, source_gems, source_gold_bars, source_pickaxe, warn_legends_readiness
from rs2004.quests.defs.legends.totem import ask_for_more_seeds, grow_totem_pole, replace_evil_totem, take_gilded_totem
from rs2004.quests.defs.legends.trials import climb_down_winch, climb_out_of_trials, descend_to_gem_room, descend_to_winch, take_book_of_binding
from rs2004.quests.defs.legends.viyeldi import banish_source_demon, charge_heart_crystal, climb_ledges, collect_sacred_water, cross_barrier, fill_recess, forge_heart_crystal, leave_caves, take_black_dagger, trade_dagger_for_spell
from rs2004.quests.engine.trace import format_tile
from rs2004.quests.engine.types import QuestModule, QuestSustain

__all__ = ['decide', 'legends', 'spent_now']

def step(name, run):
    return Record({'kind': 'custom', 'name': name, 'run': run})


# Why: Each sealed Karamja pocket requires its scripted exit before normal pathfinding can resume.
def escape_pocket(snap):
    """A step out of whatever pocket we are standing in, or null on open ground."""
    # Why: The underground shaman cave has no pocket id, so include it explicitly before treating the tile as open ground.
    area = legends_area(snap.tile)
    if legends_pocket(snap.tile) is not None or area == 'viyeldi_caves' or area == 'shaman_caves':
        return step('climb back out of the caves', leave_caves)
    if area == 'jungle':
        return step('cut back out of the Kharazi Jungle', leave_jungle)
    return None


def in_the_open(snap, when_open):
    """Take `whenOpen` only once we are somewhere a bank walk can start from."""
    _v1 = escape_pocket(snap)
    return (_v1 if _v1 is not None else when_open)


# Why: Each leg has different fixed-slot costs, so food limits are set per leg from the remaining inventory space.
FOOD = Record({'jungle': 4, 'trials': 3, 'fight': 9})
CHOP_KIT = [
    Record({'item': Record({'id': LQ_ID.RUNE_AXE, 'name': LQ_ITEM.RUNE_AXE}), 'qty': 1}),
    Record({'item': Record({'id': LQ_ID.MACHETE, 'name': LQ_ITEM.MACHETE}), 'qty': 1}),
]
MAP_KIT = [
    Record({'item': Record({'id': LQ_ID.PAPYRUS, 'name': LQ_ITEM.PAPYRUS}), 'qty': 6}),
    Record({'item': Record({'id': LQ_ID.CHARCOAL, 'name': LQ_ITEM.CHARCOAL}), 'qty': 6}),
]
BOWL_KIT = [
    Record({'item': Record({'id': LQ_ID.GOLD_BAR, 'name': LQ_ITEM.GOLD_BAR}), 'qty': 2}),
    Record({'item': Record({'id': LQ_ID.HAMMER, 'name': LQ_ITEM.HAMMER}), 'qty': 1}),
    Record({'item': Record({'id': LQ_ID.KNIFE, 'name': LQ_ITEM.KNIFE}), 'qty': 1}),
]
BRAVERY_KIT = [Record({'item': Record({'id': LQ_ID.VIAL_WATER, 'name': LQ_ITEM.VIAL_WATER}), 'qty': 1})]
TRIALS_KIT = [Record({'item': Record({'id': LQ_ID.ROPE, 'name': LQ_ITEM.ROPE}), 'qty': 1})]


def from_shop(snap, kit):
    """Bank first, then Jiminua's counter in Tai Bwo Wannai."""
    return source_from(snap, kit, LQ_SHOP.JIMINUA, SHOP_GP.JIMINUA, LEG_BANK.karamja)


# Why: `jungle_tree` empties every filled bowl state, so leave the island before filling it.
def carrying_water(snap):
    """Holding a golden bowl with anything in it."""
    return any([held(snap, id) > 0 for id in [LQ_ID.GOLD_BOWL_WATER, LQ_ID.GOLD_BOWL_PURE, LQ_ID.GOLD_BOWL_BLESSED_WATER, LQ_ID.GOLD_BOWL_BLESSED_PURE]])


# Why: Several quest rewards fail silently with a full pack, so clear spent mapping, forging, and boulder items first.
BOWLS = [
    LQ_ID.GOLD_BOWL,
    LQ_ID.GOLD_BOWL_BLESSED,
    LQ_ID.GOLD_BOWL_WATER,
    LQ_ID.GOLD_BOWL_PURE,
    LQ_ID.GOLD_BOWL_BLESSED_WATER,
    LQ_ID.GOLD_BOWL_BLESSED_PURE,
]


def spent_now(snap):
    """What the quest is done with, given where it has got to."""
    spent = [LQ_ID.SWAMP_ROCK, LQ_ID.VIAL]
    if held(snap, LQ_ID.MAP_COMPLETE) > 0 or ((snap.stage if snap.stage is not None else 0)) >= LQ_STAGE.MAPPED_JUNGLE:
        spent.extend([LQ_ID.PAPYRUS, LQ_ID.CHARCOAL])
    # Why: The hammer is done after forging, and the machete can cut the reed without the knife.
    if held(snap, LQ_ID.GOLD_BOWL_BLESSED) > 0 or held(snap, LQ_ID.GOLD_BOWL_BLESSED_PURE) > 0:
        spent.extend([LQ_ID.HAMMER, LQ_ID.KNIFE])
    # Why: Any bowl state proves the sketch has served its only purpose.
    if any([held(snap, id) > 0 for id in BOWLS]):
        spent.append(LQ_ID.GOLD_BOWL_SKETCH)
    # Why: Keep Prayer potions until the final demon dies; stage 8 still has three demon fights, guardians, and the trials ahead.
    if ((snap.stage if snap.stage is not None else 0)) >= LQ_STAGE.DEFEATED_NEZI_FINAL:
        spent.extend(list([pot.id for pot in PRAYER_POTIONS]))
    return [id for id in spent if held(snap, id) > 0]


def ditch(ids):
    """Drop the named items, wherever we are standing."""

    def run(log):
        spent = [item for item in inventory.items() if (item.id in ids)]
        for item in spent:
            item.interact('Drop')
            yield from execution.delay_ticks(1)
        log(f'dropped {len(spent)} spent item(s)')
        return len(spent) > 0
    return run


# Why: Bank and shop errands leave the island, and re-entry empties the bowl, so complete them before filling it.
def off_island(snap, kit):
    """A kit errand, routed back out to open ground when it was decided from inside."""
    if not kit:
        return None
    return (kit if legends_area(snap.tile) == 'mainland' else in_the_open(snap, kit))


def gate_kit(snap):
    """Everything a descent to the winch spends, whether or not it is the first."""
    _v3 = source_bank_only(snap, DESCENT_KIT)
    _v4 = (_v3 if _v3 is not None else source_from(snap, ORB_RUNE_KIT, LQ_SHOP.MAGIC_GUILD, SHOP_GP.MAGIC_GUILD, LEG_BANK.runes))
    _v5 = (_v4 if _v4 is not None else source_pickaxe(snap, LEG_BANK.karamja))
    return (_v5 if _v5 is not None else from_shop(snap, TRIALS_KIT))


# Why: The gate consumes the orb, so skip the kit check after crossing it.
PAST_GATE = ['winch_room', 'viyeldi_ledge']


def descent_kit(snap):
    """The descent kit, asked for anywhere the gate is still ahead of us."""
    at = legends_pocket(snap.tile)
    if legends_area(snap.tile) == 'viyeldi_caves' or (at is not None and (at in PAST_GATE)):
        return None
    return off_island(snap, gate_kit(snap))


def trials_kit(snap):
    """Everything the trials swallow in one go, none of which can be fetched from inside."""
    _v6 = source_bank_only(snap, BANK_ONLY_KIT)
    _v7 = (_v6 if _v6 is not None else source_from(snap, RUNE_KIT, LQ_SHOP.MAGIC_GUILD, SHOP_GP.MAGIC_GUILD, LEG_BANK.runes))
    _v8 = (_v7 if _v7 is not None else source_gems(snap, LEG_BANK.karamja))
    _v9 = (_v8 if _v8 is not None else from_shop(snap, TRIALS_KIT))
    return (_v9 if _v9 is not None else gate_kit(snap))


# Why: At level 70, three flasks keep Protect from Melee active through the three aggressive guardians.
FIGHT_POTS = 3


# Why: Summoning drains 90% Prayer, so reserve a potion slot before filling remaining space with food.
def upkeep(snap, food, pots=0):
    """Coin, prayer potions, food and a melee kit, taken only where a booth is reachable."""
    bank = LEG_BANK.karamja
    _v10 = coin_top_up(snap, None, bank)
    _v11 = (_v10 if _v10 is not None else potion_top_up(snap, pots, bank))
    _v12 = (_v11 if _v11 is not None else ((food_top_up(snap, food, bank) if held_food(snap) < math.ceil(food / 2) else None)))
    return (_v12 if _v12 is not None else dress_for_combat(snap, bank))


# Why: Trials, chopping, and random events add items to an already tight pack, so reserve space before withdrawals.
JUNK_RESERVE = 4


def make_room(snap, chosen):
    """Make room: at the booth the step was going to anyway, or on the ground."""
    # Why: Deposit before bank or shop errands when useful junk is present; otherwise the planner could repeat a no-op deposit.
    if (chosen.kind == 'withdraw' or chosen.kind == 'buy') and ((snap.free_slots if snap.free_slots is not None else 28)) <= JUNK_RESERVE and junk_held(snap):
        return deposit((chosen.bank if chosen.bank is not None else LEG_BANK.karamja))
    # Why: Dropping is irreversible, so wait until the pack is full.
    if ((snap.free_slots if snap.free_slots is not None else 1)) > 0:
        return chosen
    # Why: a pack with spent kit in it is already being dropped by the step above, and 2 drops racing each other shed one item a pass.
    junk = ([] if len(spent_now(snap)) > 0 else ditch_ids(snap))
    if len(junk) > 0:
        return step('drop what the quest has no use for', ditch(junk))
    # Why: 28 wanted things still leave no slot for the reed, the herb or the lump about to be handed over, and the lobster count is the only float in the pack.
    # Why: eating below the float's top-up threshold buys a slot the next withdraw spends on another lobster, a loop after a death, so only the surplus is edible.
    spare = held_food(snap) - math.ceil(food_for(snap, (snap.stage if snap.stage is not None else 0)) / 2)
    worst = ([f for f in FOOD_FOR_SLOT if held(snap, f.id) > 0] or [None])[0]
    return (step(f'eat a {worst.name.lower()} to make room', eat_one) if spare > 0 and worst else chosen)


def eat_one(log):
    """Eat the worst food held, for the slot."""
    pack = inventory.items()
    worst = ([f for f in FOOD_FOR_SLOT if any([item.id == f.id for item in pack])] or [None])[0]
    food = (([item for item in pack if item.id == worst.id] or [None])[0] if worst else None)
    if not food:
        log('no food left to eat for the slot')
        return False
    food.interact('Eat')
    yield from execution.delay_ticks(2)
    return inventory.free() > 0


# Why: the pack is tightest through the trials and the fights want the most food, so the float is chosen by where the quest is.
# Why: the Book of Binding in the pack says the trials are behind us and the octagram demon is next; both are stage 10.
def food_for(snap, stage):
    # Why: nothing after the last demon is a fight. The gilded totem is a walk to Radimus and 4 training sessions, so a fight float there (and `potsFor` reads this) is a bank trip for flasks the quest never drinks.
    if stage >= LQ_STAGE.DEFEATED_NEZI_FINAL:
        return FOOD.jungle
    # Why: everything from the winch down is a fight, 3 aggressive guardians then the demon at the source, so the trials float ends where the trials do.
    if held(snap, LQ_ID.BOOK_OF_BINDING) > 0 or stage >= LQ_STAGE.ENTER_LOWER_DUNGEON:
        return FOOD.fight
    return (FOOD.trials if stage >= LQ_STAGE.ASKED_GUJUO_WATER else FOOD.jungle)


# Why: the blessing is a prayer roll that takes 5 points a miss and refuses below 42, so the leg needs a flask as much as the demon does; a plain bowl in the pack says it hasn't happened yet.
def pots_for(snap, stage):
    """How many prayer flasks this stage's next step wants."""
    if food_for(snap, stage) == FOOD.fight:
        return FIGHT_POTS
    return (BLESS_POTS if held(snap, LQ_ID.GOLD_BOWL) > 0 else 0)


# Why: the trance takes 5 points a miss and misses about 3 times in 5, and a 42 bar is one dose back to full, so the doses are the throws and one potion buys 4.
BLESS_POTS = 2


# Why: the shopping happens before Radimus is asked for the quest, because both counters are a sea crossing from everything the quest then does.
def stage_start(snap):
    _v13 = provision(snap)
    return in_the_open(snap, (_v13 if _v13 is not None else step('ask Radimus Erkle for the quest', start_quest)))


# Why: Radimus keeps a free machete in the cupboard beside his desk and refuses a second one, so the counter in Shilo is the fallback.
# Why: The cupboard counts banked machetes but gives none, so withdraw an existing one instead of retrying the cupboard.
def stage_mapping(snap):
    # Why: the completed notes are the mapping's receipt, so holding them means the leg is done whatever the varp says: `radimus_notes.rs2` only advances the stage when it swaps the notes and clears the 3 section bits as it goes.
    # Why: Without this guard, `mapJungle` returns immediate success on every stage-1 iteration.
    if held(snap, LQ_ID.MAP_COMPLETE) > 0:
        return stage_bullroarer(snap)
    if held(snap, LQ_ID.MACHETE) == 0:
        machete = Record({'id': LQ_ID.MACHETE, 'name': LQ_ITEM.MACHETE})
        _v14 = from_bank(snap, machete, 1)
        return in_the_open(snap, (_v14 if _v14 is not None else step("take the machete from Radimus' cupboard", take_machete)))
    if legends_area(snap.tile) == 'mainland':
        chop = from_shop(snap, CHOP_KIT)
        kit = chop if chop is not None else from_shop(snap, MAP_KIT)
        if kit:
            return kit
    return step('map all three thirds of the Kharazi Jungle', map_jungle)


GUJUO_RESCUE_PREFER = [
    'I will release Ungadulu...',
    'How do we make the totem pole?',
    'What can we do instead then?',
    'Can you get your people together?',
    'I want to develop friendly relations with your people.',
    'I was hoping to attract the attention of a native.',
]
accept_rescue = talk_gujuo(GUJUO_RESCUE_PREFER, None, 150000, 'I will release Ungadulu...')


def needs_gujuo(stage):
    """Gujuo is still wanted, so the roarer is still kit."""
    return stage >= LQ_STAGE.MAPPED_JUNGLE and stage < LQ_STAGE.RETURNED_TO_RADIMUS


# Why: the forester wants a map to copy and the map goes the same way the roarer does; Radimus sells a replacement for 30 coins, but only while neither is held.
def regain_roarer(snap):
    """Get a roarer back: buy a map if that went too, redraw it, then trade it."""
    if held(snap, LQ_ID.MAP_COMPLETE) > 0:
        return step('trade a copy of the map for the bull roarer', get_bullroarer)
    if held(snap, LQ_ID.MAP) == 0:
        return step('buy a replacement map from Radimus', replace_map)
    _v15 = from_shop(snap, MAP_KIT)
    return (_v15 if _v15 is not None else step('redraw the map of the Kharazi Jungle', map_jungle))


def stage_bullroarer(snap):
    if held(snap, LQ_ID.BULLROARER) == 0:
        return step('trade a copy of the map for the bull roarer', get_bullroarer)
    return step('swing the bull roarer and befriend Gujuo', accept_rescue)


def stage_cave():
    return step('find Ungadulu and talk through the flames', speak_to_ungadulu)


# Why: the sketch is Gujuo's answer to the pure-water question and the only client-visible proof that the stage moved with it.
def stage_water(snap):
    if held(snap, LQ_ID.GOLD_BOWL_SKETCH) == 0 and owned(snap, LQ_ID.GOLD_BOWL) == 0:
        return step('ask Gujuo where the sacred water is', ask_gujuo_for_water)
    return stage_bowl(snap)


def stage_bowl(snap):
    if held(snap, LQ_ID.GOLD_BOWL_BLESSED_PURE) > 0:
        return step('douse the flames and use the Book of Binding', book_leg)
    if held(snap, LQ_ID.GOLD_BOWL_BLESSED) == 0 and held(snap, LQ_ID.GOLD_BOWL) == 0:
        bars = (source_gold_bars(snap, LEG_BANK.karamja) if legends_area(snap.tile) == 'mainland' else None)
        if bars:
            return bars
        kit = (from_shop(snap, BOWL_KIT) if legends_area(snap.tile) == 'mainland' else None)
        return (kit if kit is not None else in_the_open(snap, step('hammer two gold bars into a golden bowl', make_golden_bowl)))
    if held(snap, LQ_ID.GOLD_BOWL) > 0:
        return step('have Gujuo bless the golden bowl', bless_bowl)
    # Why: `jungle_tree` evaporates a filled bowl on every chop, so the last errand off the island runs before the pool.
    # Why: the gems and the wall runes are spent by the time the book is in the pack and gone from it once the book is read, so asking for them again sends the run back for things nothing sells.
    # Why: with the book in hand the next thing after the fill is a level-187 demon, and the bowl is still empty here, so this is the last free bank trip.
    errands = (upkeep(snap, FOOD.fight, FIGHT_POTS) if held(snap, LQ_ID.BOOK_OF_BINDING) > 0 else (None if ((snap.stage if snap.stage is not None else 0)) >= LQ_STAGE.DEFEATED_NEZI_FIRE else trials_kit(snap)))
    off = off_island(snap, errands)
    if off:
        return off
    # Why: `stat_sub(prayer, 0, 90)` runs as the book opens, so the fight starts with 90% of the prayer bar gone and Protect from Melee lapses within the minute. `potionTopUp` answers null when the bank holds no flask, which walks into a level-187 demon and says nothing.
    # Why: this is the last branch that still has a bank behind it. The fill is next and `jungle_tree` boils the bowl off on any chop back across the band.
    flask = held(snap, LQ_ID.BOOK_OF_BINDING) > 0 and pots_held(snap) == 0 and pots_banked(snap) == 0
    if flask:
        return Record({
            'kind': 'wait',
            'reason': 'no prayer potion in the pack or the bank, and opening the book drains nine tenths of the prayer bar before the demon lands a blow',
        })
    if held(snap, LQ_ID.HOLLOW_REED) == 0:
        return step('cut a hollow reed at the sacred pool', cut_reed)
    return step('syphon the sacred pool into the blessed bowl', fill_bowl_from_pool)


# Why: the book is conjured in the gem room and the magic gate past it is one-way, so this leg stops one crossing short of the winch.
def book_leg(log):
    _w17 = yield from enter_shaman_cave(log)
    _c16 = not (_w17)
    if not _c16:
        _w18 = yield from descend_to_gem_room(log)
        _c16 = not (_w18)
    if _c16:
        return False
    _result19 = yield from take_book_of_binding(log)
    return _result19


# Why: the demon is `npc_del`ed on death, so his leaving the scene ends the fight; without it the loop sits out its budget and reports a win as a failure.
def summon_and_fight(log):
    _w20 = yield from summon_demon(log)
    if not (_w20):
        return False

    def gone():
        return not npcs.query().name(LQ_NPC.NEZIKCHENED).within(14).exists()

    _result21 = yield from fight(Record({'npc': LQ_NPC.NEZIKCHENED, 'done': gone, 'ms': 420000}), log)
    return _result21


def stage_book(snap):
    if held(snap, LQ_ID.BOOK_OF_BINDING) == 0:
        _v22 = off_island(snap, trials_kit(snap))
        return (_v22 if _v22 is not None else step('fetch the Book of Binding from the gem room', book_leg))
    if held(snap, LQ_ID.GOLD_BOWL_BLESSED_PURE) == 0:
        return stage_bowl(snap)
    # Why: `stageBowl` fetches the fight kit while the bowl is empty, but a run arriving here with it filled never went through that, and `choose` only reaches its upkeep on the mainland while this is decided in the caves. Opening the book runs `stat_sub(prayer, 0, 90)`, a level-187 demon on a tenth of a prayer bar.
    # Why: the trip boils the bowl, and `stageBowl` refills it on the way back; a flask is worth a refill against this fight.
    fight_kit = off_island(snap, upkeep(snap, FOOD.fight, FIGHT_POTS))
    if fight_kit:
        return fight_kit
    if pots_held(snap) == 0 and pots_banked(snap) == 0:
        return Record({
            'kind': 'wait',
            'reason': 'no prayer potion in the pack or the bank, and opening the book drains nine tenths of the prayer bar before the demon lands a blow',
        })
    return step('open the Book of Binding on Ungadulu', summon_and_fight)


def stage_seeds(snap):
    if held(snap, LQ_ID.YOMMI_SEEDS) == 0 and held(snap, LQ_ID.YOMMI_SEEDS_GERM) == 0:
        return step('ask Ungadulu for the Yommi tree seeds', ask_for_seeds)
    if held(snap, LQ_ID.YOMMI_SEEDS_GERM) > 0:
        return step('find the sacred pool fouled', find_pool_dried)
    if held(snap, LQ_ID.GOLD_BOWL_BLESSED_PURE) == 0:
        return stage_bowl(snap)
    return step('germinate the seeds in the bowl of sacred water', germinate_seeds)


# Why: only `gujuo_helpme` moves the varp, and it's 3 menus deep: pool-dried, then the source, then the offer of help.
# Why: the goodbye outranks the source question because the menu after the recipe offers both, and picking the source again walks the chain a second time.
GUJUO_POTION_PREFER = [
    'If I went, could you help me?',
    'If I went in search of the source, could you help me?',
    'The water pool has dried up and I need more water.',
    'Where can I get more water for the Yommi tree?',
    'Ok thanks for your help.',
    'Where is the source of the spring of pure water?',
]
ask_for_recipe = talk_gujuo(GUJUO_POTION_PREFER, None, 150000)


def stage_potion(snap):
    if held(snap, LQ_ID.BRAVERY_POTION) > 0:
        _v23 = descent_kit(snap)
        return (_v23 if _v23 is not None else step('climb down the winch into the Viyeldi caves', descend_leg))
    if held(snap, LQ_ID.SNAKEWEED_MIXTURE) > 0 and held(snap, LQ_ID.ARDRIGAL) > 0:
        return Record({
            'kind': 'use_on',
            'item': LQ_ITEM.ARDRIGAL,
            'target_kind': 'item',
            'target': LQ_ITEM.SNAKEWEED_MIXTURE,
            'anchor': LEG_BANK.karamja,
            'product': LQ_ITEM.BRAVERY_POTION,
        })
    pocket = escape_pocket(snap)
    if pocket:
        return pocket
    if legends_area(snap.tile) == 'jungle':
        return step('cut back out of the Kharazi Jungle', leave_jungle)
    for herb in BRAVERY_HERBS:
        if held(snap, herb.id) > 0:
            continue
        if held(snap, herb.unid_id) > 0:
            return step(f'identify the {herb.name}', identify_herb(herb))
        return step(f'pick the {herb.name}', pick_herb(herb))
    vial = from_shop(snap, BRAVERY_KIT)
    if vial:
        return vial
    return Record({
        'kind': 'use_on',
        'item': LQ_ITEM.SNAKE_WEED,
        'target_kind': 'item',
        'target': LQ_ITEM.VIAL_WATER,
        'anchor': LEG_BANK.karamja,
        'product': LQ_ITEM.SNAKEWEED_MIXTURE,
    })


# Why: the rope refuses anyone who hasn't drunk the potion, and the refusal is a chat line with no prompt, so drink before the climb.
def drink_bravery(log):
    dose = ([item for item in inventory.items() if item.id == LQ_ID.BRAVERY_POTION] or [None])[0]
    if not dose:
        return True
    if not (dose.interact('Drink')):
        return False
    # Why: Drink only asks whether you're sure; the swig and the bit the winch checks are behind the yes.
    _result24 = yield from drive_until(lambda: not any([item.id == LQ_ID.BRAVERY_POTION for item in inventory.items()]), ["Yes, I'll bravely drink the bravery potion."], log, 20000)
    return _result24


def descend_leg(log):
    _w25 = yield from drink_bravery(log)
    if not (_w25):
        return False
    _w27 = yield from enter_shaman_cave(log)
    _c26 = not (_w27)
    if not _c26:
        _w28 = yield from descend_to_winch(log)
        _c26 = not (_w28)
    if _c26:
        return False
    _result29 = yield from climb_down_winch(log)
    return _result29


# Why: every leg below the winch stands on a tile the walker can't path to from anywhere else, so a run resumed on the surface climbs back down before it acts.
def viyeldi_step(snap, name, run):
    if legends_area(snap.tile) != 'viyeldi_caves':
        _v30 = descent_kit(snap)
        return (_v30 if _v30 is not None else step('climb back down to the Viyeldi caves', descend_leg))
    return step(name, run)


def stage_crystal(snap):
    if held(snap, LQ_ID.HEART_CRYSTAL_GLOW) > 0 or held(snap, LQ_ID.HEART_CRYSTAL) > 0:
        return stage_recess(snap)
    return viyeldi_step(snap, 'take the dragon heart off the three guardians', forge_heart_crystal)


def stage_recess(snap):
    if held(snap, LQ_ID.HEART_CRYSTAL) > 0:
        return viyeldi_step(snap, "charge the heart on the dragon's eye", charge_heart_crystal)
    return viyeldi_step(snap, 'slot the glowing heart into the recess', fill_recess)


def stage_spirit(snap):
    if held(snap, LQ_ID.HOLY_FORCE) > 0:
        return viyeldi_step(snap, 'read the Holy Force at the spirit and kill it', banish_source_demon)
    if held(snap, LQ_ID.DEATH_DAGGER) > 0:
        return step('take the black dagger to Ungadulu', dagger_to_ungadulu)
    return viyeldi_step(snap, 'push the boulder and hear Echned Zekin out', take_black_dagger)


def dagger_to_ungadulu(log):
    _w31 = yield from climb_ledges(log)
    if not (_w31):
        return False
    _w32 = yield from climb_out_of_trials(log)
    if not (_w32):
        return False
    _w33 = yield from enter_shaman_cave(log)
    if not (_w33):
        return False
    # Why: the flames block a use-on as surely as a step, so the dagger is handed over from inside the octagram.
    _w34 = yield from enter_octagram(log)
    if not (_w34):
        return False
    _result35 = yield from trade_dagger_for_spell(log)
    return _result35


def stage_sacred_water(snap):
    if held(snap, LQ_ID.GOLD_BOWL_BLESSED_PURE) > 0:
        return stage_grow(snap)
    if held(snap, LQ_ID.GOLD_BOWL_BLESSED) == 0:
        return Record({'kind': 'wait', 'reason': 'no empty blessed bowl to fill at the source'})
    return viyeldi_step(snap, 'shift the boulder and fill the bowl at the source', collect_sacred_water)


# Why: the sapling is watered from the bowl and the walk back into the jungle boils it dry, so a bowl that arrives empty is a trip back to the source.
def stage_grow(snap):
    # Why: the carve moves the varp only when the pole is lifted, so for one tick the tree is done and the stage still says it is not.
    if held(snap, LQ_ID.TOTEM_POLE) > 0:
        return stage_replace(snap)
    if held(snap, LQ_ID.YOMMI_SEEDS_GERM) == 0:
        if held(snap, LQ_ID.YOMMI_SEEDS) > 0 and held(snap, LQ_ID.GOLD_BOWL_BLESSED_PURE) > 0:
            return step('germinate the seeds in the bowl of sacred water', germinate_seeds)
        if held(snap, LQ_ID.YOMMI_SEEDS) == 0:
            return step('ask Ungadulu for another set of seeds', ask_for_more_seeds)
    if held(snap, LQ_ID.GOLD_BOWL_BLESSED_PURE) == 0:
        return viyeldi_step(snap, 'fill the bowl again at the source', collect_sacred_water)
    return step('grow a Yommi tree and carve a totem pole', grow_totem_pole)


def stage_replace(snap):
    if held(snap, LQ_ID.GILDED_TOTEM) > 0:
        return in_the_open(snap, step('take the gilded totem to Radimus', hand_in_totem))
    if held(snap, LQ_ID.TOTEM_POLE) > 0:
        # Why: replacing the totem spawns Nezikchened for the last time, and the totems stand in the Kharazi jungle where `choose` never reaches its upkeep, so the fight kit is asked for here.
        kit = off_island(snap, upkeep(snap, FOOD.fight, FIGHT_POTS))
        if kit:
            return kit
        # Why: same silence as the octagram: `potionTopUp` answers null when the bank has no flask, and Protect from Melee can't be raised on an empty prayer bar.
        if pots_held(snap) == 0 and pots_banked(snap) == 0:
            return Record({
                'kind': 'wait',
                'reason': 'no prayer potion in the pack or the bank, and replacing the totem spawns Nezikchened on the spot',
            })
        return step('replace the evil totem and kill what comes out', replace_evil_totem)
    return step('collect the gilded totem from Gujuo', take_gilded_totem)


def decide(snap):
    return make_room(snap, choose(snap))


def choose(snap):
    area = legends_area(snap.tile)
    stage = (snap.stage if snap.stage is not None else -1)
    if snap.journal == 'complete' or stage >= LQ_STAGE.COMPLETE:
        _v36 = escape_pocket(snap)
        return (_v36 if _v36 is not None else Record({'kind': 'done'}))
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    if snap.stage is None:
        return Record({'kind': 'wait', 'reason': 'Legends Quest journal stage unavailable'})
    if area == 'unknown':
        return Record({'kind': 'wait', 'reason': 'player location unavailable'})
    spent = (spent_now(snap) if ((snap.free_slots if snap.free_slots is not None else 9)) <= 1 else [])
    if len(spent) > 0:
        return step('drop what the quest has finished with', ditch(spent))
    # Why: the Karamja ships and Hajedy's cart each want coin, and the walk to the jungle is "unreachable" without it, so the float comes before any leg.
    # Why: only on open ground, as a top-up decided inside a sealed pocket sends the walker at a booth it can't reach.
    # Why: never with water in the bowl, since the only way back into the jungle is a chop and every chop boils it off.
    if area == 'mainland' and not carrying_water(snap):
        kit = upkeep(snap, food_for(snap, stage), pots_for(snap, stage))
        if kit:
            # Why: what the quest is finished with goes out before the bank hands anything over, or the top-up is capped by whatever room the junk left.
            finished = spent_now(snap)
            return (step('drop what the quest has finished with', ditch(finished)) if len(finished) > 0 else kit)
        # Why: the machete and the axe open the jungle band and every leg from the map onwards crosses it, so a death that drops them is a dead run unless they're replaced like food.
        # Why: stage 1 is left alone, since Radimus hands the first machete over for nothing.
        chop = (from_shop(snap, CHOP_KIT) if stage >= LQ_STAGE.MAPPED_JUNGLE and stage < LQ_STAGE.RETURNED_TO_RADIMUS else None)
        if chop:
            return chop
        # Why: the roarer is the only way to summon Gujuo, wanted at the bowl, the recipe and the gilded totem, but the branch that trades for one only runs at stage 3.
        # Why: a Jungle Savage takes a dislike to the noise, and the death that follows drops the roarer and the map together at stage 14.
        roarer = (regain_roarer(snap) if needs_gujuo(stage) and held(snap, LQ_ID.BULLROARER) == 0 else None)
        if roarer:
            return roarer
    if stage == LQ_STAGE.NOT_STARTED:
        return stage_start(snap)
    elif stage == LQ_STAGE.STARTED:
        return stage_mapping(snap)
    elif stage in [LQ_STAGE.MAPPED_JUNGLE, LQ_STAGE.GOT_BULLROARER, LQ_STAGE.SWUNG_BULLROARER]:
        return stage_bullroarer(snap)
    elif stage in [LQ_STAGE.ACCEPTED_RESCUE, LQ_STAGE.FOUND_ENTRANCE]:
        return stage_cave()
    elif stage == LQ_STAGE.SPOKE_UNGADULU:
        return stage_water(snap)
    elif stage == LQ_STAGE.ASKED_GUJUO_WATER:
        return stage_bowl(snap)
    elif stage in [LQ_STAGE.FILLED_BOWL, LQ_STAGE.SUMMONED_NEZI_FIRE]:
        return stage_book(snap)
    elif stage == LQ_STAGE.DEFEATED_NEZI_FIRE:
        return stage_seeds(snap)
    elif stage == LQ_STAGE.GERMINATED_SEEDS:
        # Why: the pool is a jungle loc and `cutReed` walks in on its own, so wrapping this in an escape sends the run out through the band and back for nothing.
        return step('find the sacred pool fouled', find_pool_dried)
    elif stage == LQ_STAGE.POOL_DRIED:
        return step('ask Gujuo for the bravery potion recipe', ask_for_recipe)
    elif stage == LQ_STAGE.TALK_GUJUO_POOL:
        return stage_potion(snap)
    elif stage == LQ_STAGE.ENTER_LOWER_DUNGEON:
        return stage_crystal(snap)
    elif stage == LQ_STAGE.CRYSTAL_SMELTED:
        return stage_recess(snap)
    elif stage == LQ_STAGE.HEART_IN_RECESS:
        return viyeldi_step(snap, 'cross the barrier and rouse the spirit', cross_and_rouse)
    elif stage in [LQ_STAGE.PUSHED_BOULDER, LQ_STAGE.RECEIVED_DAGGER]:
        return stage_spirit(snap)
    elif stage == LQ_STAGE.DEFEATED_NEZI_WATER:
        return stage_sacred_water(snap)
    elif stage == LQ_STAGE.SACRED_WATER:
        return stage_grow(snap)
    elif stage in [LQ_STAGE.COLLECTED_TOTEM, LQ_STAGE.SPAWNED_NEZI_FINAL, LQ_STAGE.DEFEATED_NEZI_FINAL, LQ_STAGE.REPLACED_TOTEM, LQ_STAGE.GOT_GILDED_TOTEM]:
        return stage_replace(snap)
    elif stage in [LQ_STAGE.RETURNED_TO_RADIMUS, LQ_STAGE.TRAINING_1, LQ_STAGE.TRAINING_2, LQ_STAGE.TRAINING_3, LQ_STAGE.TRAINING_4]:
        return in_the_open(snap, step("take Radimus' four training sessions", take_training))
    else:
        return Record({'kind': 'wait', 'reason': f'Legends Quest stage {stage} is not implemented'})


def cross_and_rouse(log):
    _w37 = yield from cross_barrier(log)
    if not (_w37):
        return False
    _result38 = yield from take_black_dagger(log)
    return _result38


def inside_legends(t):
    """Where a restart has no route to a booth until the quest walks it out: the jungle, the caves and the trials."""
    return t is not None and legends_area(t) in ('jungle', 'shaman_caves', 'viyeldi_caves')


def observe(snap, step):
    at = snap.tile
    pocket = legends_pocket(at) if at else None
    where = f'/{pocket}' if pocket else ''
    doing = step.name if step.kind == 'custom' else step.kind
    said = ' / '.join([m.text for m in game_messages.recent(3)])
    hp = round(skills.hp_fraction() * 100)
    stage = snap.stage if snap.stage is not None else '?'
    return [
        f'legends: stage={stage} {format_tile(at)} area={legends_area(at)}{where} step={doing} free={snap.free_slots} food={held_food(snap)} pots={pots_held(snap)} hp={hp}%',
        ('legends: the server has said nothing recently' if said == '' else f'legends: last said — {said}'),
    ]


legends = QuestModule(**{
    'record': quest_record('legends'),
    'bank': LEG_BANK.karamja,
    'owns_inventory': True,
    'coin_float': 0,
    'read_progress': read_legends_progress,
    'resume_at': inside_legends,
    'sustain': QuestSustain(list(LQ_FOODS), 0.6),
    'warn_readiness': warn_legends_readiness,
    'observe': observe,
    'decide': decide,
})
