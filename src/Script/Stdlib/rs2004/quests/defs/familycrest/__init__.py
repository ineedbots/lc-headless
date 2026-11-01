"""Ported from rs2b0t's src/bot/api/ai/quests/defs/familycrest/index.ts (MIT, see thirdparty/rs2b0t)."""

import math
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.dialogue import chat_dialog
from rs2004.entities import npcs
from rs2004.items import inventory
from rs2004.quests.data import quest_record
from rs2004.quests.engine.types import QuestModule
from rs2004.quests.defs.familycrest.areas import ANTIPOISON_IDS, FC_ID, FC_ITEM, FC_NPC, FC_QUEST, FC_STAGE, in_chronozon_lair, in_perfect_gold_zone
from rs2004.quests.defs.familycrest.chronozon import BLASTS, SAFESPOT, combine_crest, fight_chronozon
from rs2004.quests.defs.familycrest.journal import describe_journal, parse_family_crest_journal, read_family_crest_progress
from rs2004.quests.defs.familycrest.mine import PERFECT_ORE_NEEDED, craft_perfect_jewellery, enter_gold_mine, leave_gold_mine, mine_perfect_gold, mine_region, smelt_perfect_bars
from rs2004.quests.defs.familycrest.supplies import ANTIPOISON_GP, BLAST_RUNES, CALEB_FISH, CREST_KEEP_IDS, FC_FOODS, FC_OFFICIAL_SKILLS, LEG_BANK, MOULD_GP, RUBY_GP, RUNE_GP, SHOP, TELEPORT_KIT, banked_antipoison, best_bank_pickaxe, coin_top_up, deposit, food_top_up, from_bank, has_pickaxe, has_weapon, held, held_antipoison, held_food, held_name, teleport_kit_plan, teleport_kit_top_up, warn_family_crest_readiness, wield_weapon
from rs2004.quests.exec.primitives import NpcStop
from rs2004.quests.exec.prompts import drive_choice, settle_scene
from rs2004.reach import reach
from rs2004.traversal import traversal

__all__ = ['decide', 'familycrest', 'parse_family_crest_journal', 'read_family_crest_progress', 'describe_journal', 'FC_STAGE', 'FC_ID', 'FC_ITEM', 'FC_NPC', 'FC_QUEST', 'in_perfect_gold_zone', 'mine_region', 'BLASTS', 'SAFESPOT', 'CREST_KEEP_IDS', 'warn_family_crest_readiness', 'FC_OFFICIAL_SKILLS', 'teleport_kit_top_up', 'teleport_kit_plan', 'TELEPORT_KIT']

def custom(name, run):
    return Record({'kind': 'custom', 'name': name, 'run': run})


DIMINTHEIS_START = NpcStop('Dimintheis', FC_NPC.DIMINTHEIS, 8, ['Why would a nobleman live in a dump like this?', 'So where is this crest?', 'Ok, I will help you.'])
DIMINTHEIS_FINISH = NpcStop('Dimintheis', FC_NPC.DIMINTHEIS, 8, [])
CALEB_START = NpcStop('Caleb', FC_NPC.CALEB, 8, ['Are you Caleb Fitzharmon?', 'So can I have your bit?', 'Ok, I will get those.'])
# Why: handing the fish over promotes to stage 3 and then offers the question that promotes to stage 4, so one conversation covers both.
CALEB_FISH_STOP = NpcStop('Caleb', FC_NPC.CALEB, 8, ['Uh... what happened to the rest of it?', 'Thank you very much!'])
GEM_TRADER = NpcStop('Gem trader', FC_NPC.GEM_TRADER, 8, ["I'm in search of a man named Avan Fitzharmon."])
BOOT = NpcStop('Boot', FC_NPC.BOOT, 8, ["Hello. I'm in search of very high quality gold."])
# Why: both brothers re-issue their fragment only while neither pack nor bank holds it, so nothing here banks one; Avan calls it a "fragment", Caleb a "piece".
CALEB_LOST = NpcStop('Caleb', FC_NPC.CALEB, 8, ['I have lost the piece you gave me.'])
JOHNATHON = NpcStop('Johnathon', FC_NPC.JOHNATHON, 8, [])


def talk_to_avan(prefer, log):
    """Avan's NPC is called "Man" and Al Kharid is full of them, so he's addressed by id."""

    def find():
        return npcs.query().where(lambda n: n.id == FC_NPC.AVAN_NPC_ID).nearest()

    _c1 = not find()
    if _c1:
        _w2 = yield from traversal.walk_resilient(FC_NPC.AVAN, radius=3, attempts=4, timeout_ms=180000, log=log)
        _c1 = not (_w2)
    if _c1:
        return False
    yield from settle_scene()
    if not find():
        log('Avan (npc 663) is not in the scene by the gold rocks')
        return False
    status = yield from reach.entity_op(find, 'Talk-to', lambda: chat_dialog.is_open() or chat_dialog.can_continue(), open_when_unreachable=True, expect_ms=15000, what='Avan', log=log)
    if status != 'done':
        log('Avan never opened a dialogue')
        return False
    _result3 = yield from drive_choice(prefer, log)
    return _result3


def cure_johnathon(log):
    """Any dose cures Johnathon; `opnpcu` accepts all 4."""
    _w4 = yield from traversal.walk_resilient(FC_NPC.JOHNATHON, radius=2, attempts=4, timeout_ms=180000, log=log)
    if not (_w4):
        return False
    yield from settle_scene()
    potion = ([i for i in inventory.items() if (i.id in (ANTIPOISON_IDS))] or [None])[0]
    npc = npcs.query().name('Johnathon').within(8).nearest()
    if not potion or not npc:
        log('no antipoison in the pack, or Johnathon is not upstairs')
        return False
    if not (potion.use_on(npc)):
        return False
    yield from execution.delay_until(lambda: chat_dialog.is_open() or chat_dialog.can_continue(), 6000)
    # Why: Curing him opens a required three-choice Chronozon dialogue with no initial exit.
    _result5 = yield from drive_choice(['Where can I find Chronozon?', 'I will be on my way now.'], log)
    return _result5


def crest_parts(snap):
    return len([id for id in [FC_ID.CREST_FROM_CALEB, FC_ID.CREST_FROM_AVAN, FC_ID.CREST_FROM_CHRONOZON] if held(snap, id) > 0])


def missing_fish(snap):
    return [fish for fish in CALEB_FISH if held(snap, fish.id) == 0]


def source(snap, item, qty, bank, shop=None, est_gp=None):
    """Source from bank, then shop, or return a wait step with the exact shortfall."""
    short = qty - held(snap, item.id)
    if short <= 0:
        return None
    from_the_bank = from_bank(snap, item, qty, bank)
    if from_the_bank:
        return from_the_bank
    if shop:
        return Record({
            'kind': 'buy',
            'item': item.name,
            'qty': short,
            'shop': shop,
            'est_gp': (est_gp if est_gp is not None else 5000),
        })
    return Record({'kind': 'wait', 'reason': f'need {short}x {item.name} — none in the bank and nothing sells it'})


# Why: the top-up is a third of the buy quantity; against `BLAST_MINIMUM` (one cast each) the teleport kit's 30 fire runes pass and the kill phase runs dry after 6 Fire Blasts.
def source_runes(snap):
    """Withdraw the blast runes when the pack is short, or null."""
    for want in BLAST_RUNES:
        if held(snap, want.item.id) >= math.ceil(want.qty / 3):
            continue
        banked = from_bank(snap, want.item, want.qty, LEG_BANK.chronozon)
        if banked:
            return banked
        return Record({'kind': 'buy', 'item': want.item.name, 'qty': want.qty, 'shop': SHOP.AUBURY, 'est_gp': RUNE_GP})
    return None


ANTIPOISON_CARRY = 2
# Why: 5 rune stacks, law, coins, the ring, 2 doses and the fragments leave about 19 slots after the pre-wilderness deposit, so more is a withdraw that can't complete.
ENDGAME_FOOD = 16


def source_antipoison(snap, want):
    if held_antipoison(snap) >= want:
        return None
    if not snap.bank_known:
        return Record({'kind': 'scan_bank', 'bank': LEG_BANK.chronozon})
    in_bank = banked_antipoison(snap)
    if in_bank:
        step = from_bank(snap, in_bank, want, LEG_BANK.chronozon)
        if step:
            return step
    # Jiminua is a Karamja round trip, only worth it for the dose the quest can't proceed without.
    if held_antipoison(snap) == 0:
        return Record({
            'kind': 'buy',
            'item': 'Antipoison(3)',
            'qty': ANTIPOISON_CARRY,
            'shop': SHOP.JIMINUA,
            'est_gp': ANTIPOISON_GP,
        })
    return None


# Why: fetched at stage 8 since Varrock East and Aubury sit on the walk to the Jolly Boar Inn; sourcing each piece where first needed was 3 trips back to Varrock.
def endgame_loadout(snap):
    """Everything the Johnathon-to-Chronozon run needs, in one visit."""
    runes = source_runes(snap)
    if runes:
        # Coins only while there's still something to buy, or this and the pre-wilderness deposit undo each other.
        _v6 = coin_top_up(snap, 150000, LEG_BANK.chronozon)
        return (_v6 if _v6 is not None else runes)
    potions = source_antipoison(snap, ANTIPOISON_CARRY)
    if potions:
        return potions
    food = food_top_up(snap, ENDGAME_FOOD, LEG_BANK.chronozon)
    if food:
        return food
    return wield_weapon(snap, LEG_BANK.chronozon)


ALWAYS_KEEP = ['coins'] + list([f.lower() for f in FC_FOODS])
# Why: coins and the ring of dueling are what this deposit banks; law stays since the lair is wilderness level 3, under the level-20 spell cutoff, so the walk home past the black demons and giant skeletons becomes a Varrock teleport.
WILDERNESS_KEEP = list([f.lower() for f in FC_FOODS]) + list([r.item.name.lower() for r in BLAST_RUNES]) + [FC_ITEM.LAW_RUNE.lower(), 'antipoison', 'scimitar']


def tidy_for(snap, need, keep, bank):
    return (None if ((snap.free_slots if snap.free_slots is not None else 28)) >= need else deposit(list(ALWAYS_KEEP) + list(keep), bank))


# Why: `%crestquest` isn't transmitted, so the journal is the only state read.
def decide(snap):
    """Pure decide over journal stage plus held items."""
    if snap.journal == 'complete':
        return Record({'kind': 'done'})
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    _v7 = (snap.progress.stage if snap.progress is not None else None)
    stage = (_v7 if _v7 is not None else snap.stage)
    if stage is None:
        return Record({'kind': 'wait', 'reason': 'Family Crest stage unavailable'})
    if stage >= FC_STAGE.COMPLETE:
        return Record({'kind': 'done'})
    # The endgame outranks the stage: Chronozon's drop is the only evidence stage 10 finished, and the restored crest the only evidence of the combine.
    if held(snap, FC_ID.FAMILY_CREST) > 0:
        return Record({'kind': 'talk', 'stop': DIMINTHEIS_FINISH})
    if crest_parts(snap) == 3:
        return custom('combine the three crest parts', combine_crest)
    # Why: a missing fragment was lost to a death or banked; both brothers hand theirs over again and Chronozon drops his again.
    if stage >= FC_STAGE.CALEB_WHERE and held(snap, FC_ID.CREST_FROM_CALEB) == 0:
        return Record({'kind': 'talk', 'stop': CALEB_LOST})
    # Why: at stage 8 `switch_int(%crestquest)` sends `crest_avan_piece` to `avan_where`, which has no "I have lost the fragment" branch; that lives in `avan_pieces` from stage 9 on.
    if stage >= FC_STAGE.SPOKEN_JOHNATHON and held(snap, FC_ID.CREST_FROM_AVAN) == 0:
        return custom('ask Avan to replace the fragment', lambda log: talk_to_avan(['I have lost the fragment you gave me.'], log))
    if stage == FC_STAGE.NOT_STARTED:
        return Record({'kind': 'talk', 'stop': DIMINTHEIS_START})
    # Why: one bank trip before the first long leg when nav teleports are on, since A* won't plan a hop the live inventory can't pay for and nothing else here carries law.
    # Why: skipped while Chronozon stands, since the wilderness deposit banks the kit on purpose and re-fetching walks 30 law and a ring of dueling back into the fight.
    fight_pending = stage == FC_STAGE.CURED_JOHNATHON and held(snap, FC_ID.CREST_FROM_CHRONOZON) == 0
    if not fight_pending:
        tele_kit = teleport_kit_top_up(snap, LEG_BANK.start)
        if tele_kit:
            return tele_kit
    # Caleb: the 5 cooked fish
    if stage <= FC_STAGE.CALEB_PIECE:
        if stage == FC_STAGE.SPOKEN_DIMINTHEIS:
            return Record({'kind': 'talk', 'stop': CALEB_START})
        if stage == FC_STAGE.SPOKEN_CALEB:
            short = missing_fish(snap)
            if len(short) > 0:
                tidy = tidy_for(snap, len(short) + 2, [f.name.lower() for f in CALEB_FISH], LEG_BANK.caleb)
                if tidy:
                    return tidy
                for fish in short:
                    step = from_bank(snap, fish, 1, LEG_BANK.caleb)
                    if step:
                        return step
                if not snap.bank_known:
                    return Record({'kind': 'scan_bank', 'bank': LEG_BANK.caleb})
                return Record({
                    'kind': 'wait',
                    'reason': f"Caleb needs cooked {', '.join([f.name for f in short])} — none in the bank",
                })
        return Record({'kind': 'talk', 'stop': CALEB_FISH_STOP})
    # The desert: an Al Kharid trader, then Avan, then Boot
    if stage == FC_STAGE.CALEB_WHERE:
        return Record({'kind': 'talk', 'stop': GEM_TRADER})
    if stage == FC_STAGE.SPOKEN_GEM_TRADER:
        return custom('ask Avan about the crest', lambda log: talk_to_avan(["I'm looking for a man named Avan Fitzharmon."], log))
    if stage == FC_STAGE.SPOKEN_AVAN:
        return Record({'kind': 'talk', 'stop': BOOT})
    # Perfect gold: mine, smelt, craft, hand over
    if stage == FC_STAGE.SPOKEN_BOOT:
        have_ring = held(snap, FC_ID.PERFECT_RUBY_RING) > 0
        have_necklace = held(snap, FC_ID.PERFECT_RUBY_NECKLACE) > 0
        if have_ring and have_necklace:
            return custom('hand Avan the perfect jewellery', lambda log: talk_to_avan([], log))
        in_mine = mine_region(snap.tile) != 'outside'
        made = ((1 if have_ring else 0)) + ((1 if have_necklace else 0))
        outstanding = 2 - made
        supply = held(snap, FC_ID.PERFECT_GOLD_BAR) + held(snap, FC_ID.PERFECT_GOLD_ORE)
        if in_mine:
            if supply < outstanding and held(snap, FC_ID.PERFECT_GOLD_ORE) < PERFECT_ORE_NEEDED:
                return custom('mine perfect gold', mine_perfect_gold)
            return custom('climb out of the gold mine', leave_gold_mine)
        if supply < outstanding:
            # Why: the walk back out costs the lever chain, so everything is sourced before entering.
            # Why: the bank is pinned to Ardougne because the next stop is Witchaven; from Boot, Falador is closer but the Falador-then-Witchaven walk is about 90 tiles longer.
            # Why: scan before deciding "buy from Nurmof", or the bot crosses the map for a pickaxe that was in the bank.
            if not snap.bank_known and (not has_pickaxe(snap) or not has_weapon(snap) or held_food(snap) == 0):
                return Record({'kind': 'scan_bank', 'bank': LEG_BANK.mine})
            pickaxe = (None if has_pickaxe(snap) else ((from_bank(snap, best_bank_pickaxe(snap), 1, LEG_BANK.mine) if best_bank_pickaxe(snap) else Record({'kind': 'buy', 'item': 'Steel pickaxe', 'qty': 1, 'shop': SHOP.NURMOF, 'est_gp': 2000}))))
            if pickaxe:
                return pickaxe
            food = food_top_up(snap, 10, LEG_BANK.mine)
            if food:
                return food
            arm = wield_weapon(snap, LEG_BANK.mine)
            if arm:
                return arm
            return custom('climb down into the perfect-gold mine', enter_gold_mine)
        # Why: moulds, rubies, furnace and Avan are all in Al Kharid, so moulds and rubies are sourced before the smelt to keep it one trip.
        # Why: coins first, since a `buy` step withdraws its own `estGp` and buying the ring mould leaves the pack under it for the next purchase.
        leg_coins = coin_top_up(snap, 50000, LEG_BANK.gold)
        if leg_coins:
            return leg_coins
        moulds = [
            [Record({'id': FC_ID.RING_MOULD, 'name': FC_ITEM.RING_MOULD}), (0 if have_ring else 1)],
            [Record({'id': FC_ID.NECKLACE_MOULD, 'name': FC_ITEM.NECKLACE_MOULD}), (0 if have_necklace else 1)],
        ]
        for mould, qty in moulds:
            if qty == 0:
                continue
            step = source(snap, mould, qty, LEG_BANK.gold, SHOP.DOMMIK, MOULD_GP)
            if step:
                return step
        # Why: the Ardougne gem merchant restocks one cut ruby every 60k ticks and no other shop stocks one, so the shop is tried once and the shortfall reported.
        ruby_short = outstanding - held(snap, FC_ID.RUBY)
        if ruby_short > 0:
            banked = from_bank(snap, Record({'id': FC_ID.RUBY, 'name': FC_ITEM.RUBY}), outstanding, LEG_BANK.gold)
            if banked:
                return banked
            if snap.no_progress >= 2:
                return Record({
                    'kind': 'wait',
                    'reason': f'need {ruby_short}x Ruby — none in the bank, and the Ardougne gem merchant stocks one',
                })
            return Record({
                'kind': 'buy',
                'item': FC_ITEM.RUBY,
                'qty': ruby_short,
                'shop': SHOP.GEM_MERCHANT,
                'est_gp': RUBY_GP,
            })
        if held(snap, FC_ID.PERFECT_GOLD_ORE) > 0:
            return custom('smelt the perfect gold', smelt_perfect_bars)
        return custom('craft the perfect gold jewellery', craft_perfect_jewellery)
    # Johnathon
    if stage == FC_STAGE.AVAN_PIECE:
        load = endgame_loadout(snap)
        if load:
            return load
        return Record({'kind': 'talk', 'stop': JOHNATHON})
    if stage == FC_STAGE.SPOKEN_JOHNATHON:
        # Normally already carried from stage 8; this only fires after a death.
        if held_antipoison(snap) == 0:
            potions = source_antipoison(snap, ANTIPOISON_CARRY)
            if potions:
                return potions
        return custom('cure Johnathon with antipoison', cure_johnathon)
    # Chronozon
    if stage == FC_STAGE.CURED_JOHNATHON:
        # Why: preparation re-runs every tick, and inside the lair eating 3 sharks or drinking a dose would drop the pack under a threshold and walk the bot out mid-fight.
        if in_chronozon_lair(snap.tile):
            return custom('kill Chronozon with the four blasts', fight_chronozon)
        # Normally all fetched at stage 8; re-running the list re-provisions after a death.
        load = endgame_loadout(snap)
        if load:
            return load
        # Bank the float before the wilderness, where dying drops it. Nothing past here costs coin.
        if held_name(snap, FC_ITEM.COINS) > 0:
            return deposit(WILDERNESS_KEEP, LEG_BANK.chronozon)
        return custom('kill Chronozon with the four blasts', fight_chronozon)
    return Record({'kind': 'wait', 'reason': f'no plan for Family Crest stage {stage}'})


familycrest = QuestModule(**{
    'record': quest_record('crest'),
    'bank': 'nearest',
    'owns_inventory': True,
    'tools': ['coins', 'ruby', 'ring mould', 'necklace mould', 'antipoison'],
    'read_progress': read_family_crest_progress,
    'sustain': Record({'foods': list(FC_FOODS), 'eat_below_hp': 0.55}),
    'warn_readiness': warn_family_crest_readiness,
    'exit': leave_gold_mine,
    'decide': decide,
})
