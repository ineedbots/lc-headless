"""Ported from rs2b0t's test/api/ai/quests/defs/familycrest.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestProgress, QuestSnapshot
from rs2004.quests.defs.familycrest import BLASTS, FC_ID, FC_STAGE, SAFESPOT, decide, familycrest, in_perfect_gold_zone, mine_region, parse_family_crest_journal, teleport_kit_plan, teleport_kit_top_up

VARROCK = Record({'x': 3253, 'z': 3420, 'level': 0})
MINE_MAIN = Record({'x': 2700, 'z': 9683, 'level': 0})
MINE_GOLD = Record({'x': 2737, 'z': 9689, 'level': 0})
RUNE_SCIM = 1333
STEEL_PICK = 1269


def snap(options=None):
    if options is None:
        options = Record({})
    stage = (options.stage if options.stage is not None else FC_STAGE.NOT_STARTED)
    # Fragments already granted at this stage are carried unless a test is
    # deliberately exercising the lost-fragment recovery.
    granted = ([] if options.drop_fragments == True else list((([[FC_ID.CREST_FROM_CALEB, 1]] if stage >= FC_STAGE.CALEB_WHERE else []))) + list((([[FC_ID.CREST_FROM_AVAN, 1]] if stage >= FC_STAGE.AVAN_PIECE else []))))
    inv_ids = {_k: _v for _k, _v in granted}
    for id, qty in (options.inv_ids if options.inv_ids is not None else []):
        inv_ids[id] = qty
    return QuestSnapshot(**{
        'journal': (options.journal if options.journal is not None else (('not_started' if stage == FC_STAGE.NOT_STARTED else 'in_progress'))),
        'inv': {_k: _v for _k, _v in [[n.lower(), q] for n, q in ((options.inv if options.inv is not None else []))]},
        'inv_ids': inv_ids,
        'worn': set(),
        'worn_ids': set((options.worn_ids if options.worn_ids is not None else [])),
        'no_progress': 0,
        'bank_coins': 2000000,
        'stage': stage,
        'progress': QuestProgress(stage, set()),
        'bank': {_k: _v for _k, _v in [[n.lower(), q] for n, q in ((options.bank if options.bank is not None else []))]},
        'bank_ids': {_k: _v for _k, _v in (options.bank_ids if options.bank_ids is not None else [])},
        'bank_known': (options.bank_known if options.bank_known is not None else True),
        'tile': (VARROCK if options.tile is None else options.tile),
        'attack': (options.attack if options.attack is not None else 60),
        'free_slots': (options.free_slots if options.free_slots is not None else 20),
    })


ALL_FISH = [[FC_ID.SWORDFISH, 1], [FC_ID.BASS, 1], [FC_ID.TUNA, 1], [FC_ID.SALMON, 1], [FC_ID.SHRIMP, 1]]


def talk_target(step):
    return (step.stop.npc if step.kind == 'talk' else None)


def custom_name(step):
    return (step.name if step.kind == 'custom' else None)


HEADER = "@str@I have agreed to restore Dimintheis' family crest to him.|"
FOUND_CALEB = '@str@I found Caleb working as a Chef in Catherby and told him of|' + '@str@my Quest for his father to restore his Family Crest.|' + '@str@I discovered the Crest had been split into three with each|' + "@str@of Dimintheis' three sons taking a piece each.|"
GAVE_FISH = '@str@I gave Caleb the Swordfish, Bass, Tuna, Salmon and Shrimp|' + '@str@he needed for his salad in return for his crest piece.|'
FOUND_AVAN = '@str@I found Avan by some gold rocks North of Al-Kharid.|'
AVAN_GAVE = '@str@Avan gave me his crest piece in return for a ruby ring and|' + "@str@ruby necklace made of high quality 'perfect gold'.|"
CURED = '@str@I found Johnathan looking very ill at the Jolly Boar Inn.|' + '@str@He soon recovered when I used an antipoison potion on|@str@him.|'


def _fn3():
    def _fn4():
        expect((parse_family_crest_journal('@dbl@I can start this quest by speaking to @dre@Dimintheis@dbl@ in @dre@East|@dre@Varrock|').stage if parse_family_crest_journal('@dbl@I can start this quest by speaking to @dre@Dimintheis@dbl@ in @dre@East|@dre@Varrock|') is not None else None)).to_be(FC_STAGE.NOT_STARTED)
    test('not started', _fn4)

    def _fn5():
        expect((parse_family_crest_journal(HEADER + '@dbl@I need to find his son @dre@Caleb@dbl@. The last Dimintheis heard of|' + '@dbl@him he was a great @dre@chef@dbl@ beyond @dre@White Wolf Mountain').stage if parse_family_crest_journal(HEADER + '@dbl@I need to find his son @dre@Caleb@dbl@. The last Dimintheis heard of|' + '@dbl@him he was a great @dre@chef@dbl@ beyond @dre@White Wolf Mountain') is not None else None)).to_be(FC_STAGE.SPOKEN_DIMINTHEIS)
    test('spoken to Dimintheis', _fn5)

    def _fn6():
        expect((parse_family_crest_journal(HEADER + FOUND_CALEB + '@dre@Caleb@dbl@ will let me have @dre@his piece@dbl@ in return for:|' + '@dre@one cooked Tuna|@dre@one cooked Bass|@dre@one cooked Salmon|' + '@dre@one cooked Shrimp|@dre@one cooked Swordfish').stage if parse_family_crest_journal(HEADER + FOUND_CALEB + '@dre@Caleb@dbl@ will let me have @dre@his piece@dbl@ in return for:|' + '@dre@one cooked Tuna|@dre@one cooked Bass|@dre@one cooked Salmon|' + '@dre@one cooked Shrimp|@dre@one cooked Swordfish') is not None else None)).to_be(FC_STAGE.SPOKEN_CALEB)
    test('Caleb wants the fish', _fn6)

    def _fn7():
        expect((parse_family_crest_journal(HEADER + FOUND_CALEB + GAVE_FISH + '@dbl@I have @dre@one@dbl@ crest piece, I need to find the other @dre@two').stage if parse_family_crest_journal(HEADER + FOUND_CALEB + GAVE_FISH + '@dbl@I have @dre@one@dbl@ crest piece, I need to find the other @dre@two') is not None else None)).to_be(FC_STAGE.CALEB_PIECE)
    test('one crest piece', _fn7)

    def _fn8():
        expect((parse_family_crest_journal(HEADER + FOUND_CALEB + GAVE_FISH + '@dre@Caleb@dbl@ told me his brother @dre@Avan@dbl@ is on a treasure hunt in the|' + '@dre@desert@dbl@ somewhere - I should search for him there').stage if parse_family_crest_journal(HEADER + FOUND_CALEB + GAVE_FISH + '@dre@Caleb@dbl@ told me his brother @dre@Avan@dbl@ is on a treasure hunt in the|' + '@dre@desert@dbl@ somewhere - I should search for him there') is not None else None)).to_be(FC_STAGE.CALEB_WHERE)
    test('Caleb pointed at the desert', _fn8)

    def _fn9():
        expect((parse_family_crest_journal(HEADER + FOUND_CALEB + GAVE_FISH + '@dbl@The @dre@Al-Kharid Gem Trader@dbl@ told me that @dre@Avan@dbl@ is wearing a|' + '@dre@yellow cape@dbl@, and headed into the @dre@desert@dbl@ by the @dre@scorpions').stage if parse_family_crest_journal(HEADER + FOUND_CALEB + GAVE_FISH + '@dbl@The @dre@Al-Kharid Gem Trader@dbl@ told me that @dre@Avan@dbl@ is wearing a|' + '@dre@yellow cape@dbl@, and headed into the @dre@desert@dbl@ by the @dre@scorpions') is not None else None)).to_be(FC_STAGE.SPOKEN_GEM_TRADER)
    test('gem trader described the yellow cape', _fn9)

    def _fn10():
        expect((parse_family_crest_journal(HEADER + FOUND_CALEB + GAVE_FISH + '@dbl@I should find a dwarf named @dre@Boot@dbl@ who lives somewhere in|' + "@dre@the mountains@dbl@ and knows where to find @dre@'Perfect Gold'").stage if parse_family_crest_journal(HEADER + FOUND_CALEB + GAVE_FISH + '@dbl@I should find a dwarf named @dre@Boot@dbl@ who lives somewhere in|' + "@dre@the mountains@dbl@ and knows where to find @dre@'Perfect Gold'") is not None else None)).to_be(FC_STAGE.SPOKEN_AVAN)
    test('Avan sent us to Boot', _fn10)

    def _fn11():
        expect((parse_family_crest_journal(HEADER + FOUND_CALEB + GAVE_FISH + FOUND_AVAN + '@dre@Avan@dbl@ will give me his @dre@crest piece@dbl@ if I can bring him a @dre@ruby|' + "@dre@ring@dbl@ and @dre@ruby necklace@dbl@ made from @dre@'perfect gold'|" + "@dbl@I need to make a @dre@ruby ring@dbl@ made of @dre@'perfect gold'|").stage if parse_family_crest_journal(HEADER + FOUND_CALEB + GAVE_FISH + FOUND_AVAN + '@dre@Avan@dbl@ will give me his @dre@crest piece@dbl@ if I can bring him a @dre@ruby|' + "@dre@ring@dbl@ and @dre@ruby necklace@dbl@ made from @dre@'perfect gold'|" + "@dbl@I need to make a @dre@ruby ring@dbl@ made of @dre@'perfect gold'|") is not None else None)).to_be(FC_STAGE.SPOKEN_BOOT)
    test('Boot named the mine', _fn11)

    def _fn12():
        expect((parse_family_crest_journal(HEADER + FOUND_CALEB + GAVE_FISH + FOUND_AVAN + AVAN_GAVE + '@dbl@The @dre@final crest@dbl@ piece is with their brother @dre@Johnathon@dbl@ who is|' + '@dbl@a magical demon hunter at a @dre@tavern@dbl@ near the @dre@wilderness').stage if parse_family_crest_journal(HEADER + FOUND_CALEB + GAVE_FISH + FOUND_AVAN + AVAN_GAVE + '@dbl@The @dre@final crest@dbl@ piece is with their brother @dre@Johnathon@dbl@ who is|' + '@dbl@a magical demon hunter at a @dre@tavern@dbl@ near the @dre@wilderness') is not None else None)).to_be(FC_STAGE.AVAN_PIECE)
    test('two pieces, Johnathon next', _fn12)

    def _fn13():
        expect((parse_family_crest_journal(HEADER + FOUND_CALEB + GAVE_FISH + FOUND_AVAN + AVAN_GAVE + '@dbl@I found @dre@Johnathon@dbl@ looking very ill at the @dre@Jolly Boar Inn').stage if parse_family_crest_journal(HEADER + FOUND_CALEB + GAVE_FISH + FOUND_AVAN + AVAN_GAVE + '@dbl@I found @dre@Johnathon@dbl@ looking very ill at the @dre@Jolly Boar Inn') is not None else None)).to_be(FC_STAGE.SPOKEN_JOHNATHON)
    test('Johnathon is poisoned', _fn13)

    def _fn14():
        expect((parse_family_crest_journal(HEADER + FOUND_CALEB + GAVE_FISH + FOUND_AVAN + AVAN_GAVE + CURED + '@dre@Johnathon@dbl@ lost his piece of the family crest to a demon|' + '@dbl@named @dre@Chronozon@dbl@ under the @dre@Air Obelisk@dbl@ in the @dre@Wilderness').stage if parse_family_crest_journal(HEADER + FOUND_CALEB + GAVE_FISH + FOUND_AVAN + AVAN_GAVE + CURED + '@dre@Johnathon@dbl@ lost his piece of the family crest to a demon|' + '@dbl@named @dre@Chronozon@dbl@ under the @dre@Air Obelisk@dbl@ in the @dre@Wilderness') is not None else None)).to_be(FC_STAGE.CURED_JOHNATHON)
    test('cured — Chronozon is the last step', _fn14)

    def _fn15():
        expect((parse_family_crest_journal(HEADER + FOUND_CALEB + GAVE_FISH + FOUND_AVAN + AVAN_GAVE + CURED).stage if parse_family_crest_journal(HEADER + FOUND_CALEB + GAVE_FISH + FOUND_AVAN + AVAN_GAVE + CURED) is not None else None)).to_be(FC_STAGE.CURED_JOHNATHON)
    test('the cured line alone still reads as stage 10, not 9', _fn15)

    def _fn16():
        expect((parse_family_crest_journal(HEADER + FOUND_CALEB + GAVE_FISH + FOUND_AVAN + AVAN_GAVE + CURED + '@str@I took all three pieces of the crest back to Dimintheis in|@red@QUEST COMPLETE!').stage if parse_family_crest_journal(HEADER + FOUND_CALEB + GAVE_FISH + FOUND_AVAN + AVAN_GAVE + CURED + '@str@I took all three pieces of the crest back to Dimintheis in|@red@QUEST COMPLETE!') is not None else None)).to_be(FC_STAGE.COMPLETE)
    test('quest complete', _fn16)

    def _fn17():
        expect(parse_family_crest_journal('')).to_be_undefined()
    test('an unparseable scroll yields nothing rather than stage 0', _fn17)


describe('Family Crest journal parsing', _fn3)


def _fn18():
    def _fn19():
        expect(mine_region(Record({'x': 2700, 'z': 9683, 'level': 0}))).to_be('main')
        expect(mine_region(Record({'x': 2723, 'z': 9670, 'level': 0}))).to_be('south')
        expect(mine_region(Record({'x': 2723, 'z': 9717, 'level': 0}))).to_be('north_room')
        expect(mine_region(Record({'x': 2737, 'z': 9689, 'level': 0}))).to_be('gold')
        expect(mine_region(Record({'x': 2696, 'z': 3282, 'level': 0}))).to_be('outside')
        expect(mine_region(None)).to_be('outside')
    test('the four lever-door regions are told apart by tile alone', _fn19)

    def _fn20():
        expect(in_perfect_gold_zone(Record({'x': 2737, 'z': 9689, 'level': 0}))).to_be(True)
        expect(in_perfect_gold_zone(Record({'x': 2740, 'z': 9684, 'level': 0}))).to_be(True)
        # One tile south of the boundary rock: mining from here yields plain gold.
        expect(in_perfect_gold_zone(Record({'x': 2737, 'z': 9683, 'level': 0}))).to_be(False)
        expect(in_perfect_gold_zone(Record({'x': 2735, 'z': 9689, 'level': 0}))).to_be(False)
    test('the perfect-gold zone is the players tile, not the rocks', _fn20)


describe('Family Crest mine geography', _fn18)


def _fn21():
    def _fn22():
        expect(decide(snap(Record({'journal': 'unknown'}))).kind).to_be('wait')
    test('an unloaded journal waits rather than restarting the quest', _fn22)

    def _fn23():
        expect(decide(snap(Record({'journal': 'complete'}))).kind).to_be('done')
    test('a complete journal is done', _fn23)

    def _fn24():
        expect(talk_target(decide(snap()))).to_be('Dimintheis')
    test('not started → Dimintheis', _fn24)

    def _fn25():
        expect(talk_target(decide(snap(Record({'stage': FC_STAGE.SPOKEN_DIMINTHEIS}))))).to_be('Caleb')
    test('started → Caleb', _fn25)

    def _fn26():
        step = decide(snap(Record({'stage': FC_STAGE.SPOKEN_CALEB, 'inv_ids': [[FC_ID.SWORDFISH, 1], [FC_ID.BASS, 1]]})))
        expect(step.kind).to_be('wait')
        expect(step.kind == 'wait' and step.reason).to_contain('Tuna')
        expect(step.kind == 'wait' and step.reason).to_contain('Salmon')
        expect(step.kind == 'wait' and step.reason).to_contain('Shrimps')
        expect(step.kind == 'wait' and step.reason).not_.to_contain('Swordfish')
    test('Caleb waits on the fish and names exactly what is short', _fn26)

    def _fn27():
        step = decide(snap(Record({'stage': FC_STAGE.SPOKEN_CALEB, 'bank_ids': [[FC_ID.TUNA, 3]], 'bank': [['tuna', 3]]})))
        expect(step.kind).to_be('withdraw')
        expect(step.kind == 'withdraw' and step.items[0].get('id')).to_be(FC_ID.TUNA)
    test('Caleb withdraws the fish the bank does hold', _fn27)

    def _fn28():
        expect(talk_target(decide(snap(Record({'stage': FC_STAGE.SPOKEN_CALEB, 'inv_ids': ALL_FISH}))))).to_be('Caleb')
    test('with all five fish held, Caleb is talked to', _fn28)

    def _fn29():
        expect(talk_target(decide(snap(Record({'stage': FC_STAGE.CALEB_PIECE}))))).to_be('Caleb')
    test('one piece → back to Caleb for his brother', _fn29)

    def _fn30():
        expect(talk_target(decide(snap(Record({'stage': FC_STAGE.CALEB_WHERE}))))).to_be('Gem trader')
    test('desert lead → the Al Kharid gem trader', _fn30)

    def _fn31():
        expect(custom_name(decide(snap(Record({'stage': FC_STAGE.SPOKEN_GEM_TRADER}))))).to_contain('Avan')
    test('after the gem trader, Avan is addressed by id rather than by name', _fn31)

    def _fn32():
        expect(talk_target(decide(snap(Record({'stage': FC_STAGE.SPOKEN_AVAN}))))).to_be('Boot')
    test('after Avan → Boot', _fn32)


describe('Family Crest decide', _fn21)


def _fn33():
    kitted = Record({'inv_ids': [[STEEL_PICK, 1]], 'inv': [['shark', 10]], 'worn_ids': [RUNE_SCIM]})

    def _fn34():
        step = decide(snap(Record({'stage': FC_STAGE.SPOKEN_BOOT, 'inv_ids': [[STEEL_PICK, 1], [RUNE_SCIM, 1]], 'inv': [['shark', 10]]})))
        expect(step.kind).to_be('equip')
        expect(step.kind == 'equip' and step.item).to_be('Rune scimitar')
    test('a scimitar in the pack is wielded before the ladder, not carried down', _fn34)

    def _fn35():
        step = decide(snap(Record({'stage': FC_STAGE.SPOKEN_BOOT, 'bank_ids': [[STEEL_PICK, 1]], 'bank': [['steel pickaxe', 1]]})))
        expect(step.kind).to_be('withdraw')
        expect(step.kind == 'withdraw' and step.items[0].get('id')).to_be(STEEL_PICK)
    test('a pickaxe is sourced before the ladder, never after it', _fn35)

    def _fn36():
        _merged37 = {}
        for _k, _v in {'stage': FC_STAGE.SPOKEN_BOOT}.items():
            _merged37[_k] = _v
        for _k, _v in (kitted._fields if isinstance(kitted, Record) else kitted).items():
            _merged37[_k] = _v
        expect(custom_name(decide(snap(Record(_merged37))))).to_contain('climb down')
    test('kitted out and outside, the bot climbs down', _fn36)

    def _fn38():
        _merged39 = {}
        for _k, _v in {'stage': FC_STAGE.SPOKEN_BOOT}.items():
            _merged39[_k] = _v
        for _k, _v in (kitted._fields if isinstance(kitted, Record) else kitted).items():
            _merged39[_k] = _v
        for _k, _v in {'tile': MINE_MAIN}.items():
            _merged39[_k] = _v
        expect(custom_name(decide(snap(Record(_merged39))))).to_contain('mine perfect gold')
    test('inside the mine with no ore, it mines', _fn38)

    def _fn40():
        expect(custom_name(decide(snap(Record({
        'stage': FC_STAGE.SPOKEN_BOOT,
        'inv_ids': list(kitted.inv_ids) + [[FC_ID.PERFECT_GOLD_ORE, 2]],
        'worn_ids': kitted.worn_ids,
        'tile': MINE_GOLD,
    }))))).to_contain('climb out')
    test('inside the mine holding both ores, it climbs back out', _fn40)

    def _fn41():
        step = decide(snap(Record({
        'stage': FC_STAGE.SPOKEN_BOOT,
        'inv_ids': list(kitted.inv_ids) + [[FC_ID.PERFECT_GOLD_ORE, 2]],
        'worn_ids': kitted.worn_ids,
        'bank': [['coins', 2000000]],
    })))
        expect(step.kind).to_be('withdraw')
        expect(step.kind == 'withdraw' and step.items[0].get('name')).to_be('Coins')
    test('a coin float is taken once so each purchase does not re-bank', _fn41)

    def _fn42():
        step = decide(snap(Record({
        'stage': FC_STAGE.SPOKEN_BOOT,
        'inv_ids': list(kitted.inv_ids) + [[FC_ID.PERFECT_GOLD_ORE, 2]],
        'worn_ids': kitted.worn_ids,
    })))
        expect(step.kind).to_be('buy')
        expect(step.kind == 'buy' and step.item).to_be('Ring mould')
    test('with ore but no moulds, the moulds come before the furnace trip', _fn42)

    def _fn43():
        step = decide(snap(Record({
        'stage': FC_STAGE.SPOKEN_BOOT,
        'inv_ids': list(kitted.inv_ids) + [[FC_ID.PERFECT_GOLD_ORE, 2], [FC_ID.RING_MOULD, 1], [FC_ID.NECKLACE_MOULD, 1]],
        'worn_ids': kitted.worn_ids,
    })))
        expect(step.kind).to_be('buy')
        expect(step.kind == 'buy' and step.item).to_be('Ruby')
        expect(step.kind == 'buy' and step.shop.npc).to_be('Gem merchant')
    test('with ore and moulds but no rubies, it tries the gem merchant', _fn43)

    def _fn44():
        expect(custom_name(decide(snap(Record({
        'stage': FC_STAGE.SPOKEN_BOOT,
        'inv_ids': list(kitted.inv_ids) + [[FC_ID.PERFECT_GOLD_ORE, 2], [FC_ID.RING_MOULD, 1], [FC_ID.NECKLACE_MOULD, 1], [FC_ID.RUBY, 2]],
        'worn_ids': kitted.worn_ids,
    }))))).to_contain('smelt')
    test('fully supplied but still holding ore, it smelts first', _fn44)

    def _fn45():
        expect(custom_name(decide(snap(Record({
        'stage': FC_STAGE.SPOKEN_BOOT,
        'inv_ids': list(kitted.inv_ids) + [[FC_ID.PERFECT_GOLD_BAR, 2], [FC_ID.RING_MOULD, 1], [FC_ID.NECKLACE_MOULD, 1], [FC_ID.RUBY, 2]],
        'worn_ids': kitted.worn_ids,
    }))))).to_contain('craft')
    test('fully supplied, it crafts', _fn45)

    def _fn46():
        expect(custom_name(decide(snap(Record({
        'stage': FC_STAGE.SPOKEN_BOOT,
        'inv_ids': [[FC_ID.PERFECT_RUBY_RING, 1], [FC_ID.PERFECT_RUBY_NECKLACE, 1]],
    }))))).to_contain('Avan')
    test('with both pieces made, Avan gets them', _fn46)


describe('Family Crest perfect-gold leg', _fn33)


def _fn47():
    endgame_kit = [
        [FC_ID.AIR_RUNE, 600],
        [FC_ID.WATER_RUNE, 200],
        [FC_ID.EARTH_RUNE, 200],
        [FC_ID.FIRE_RUNE, 250],
        [FC_ID.DEATH_RUNE, 60],
        [FC_ID.ANTIPOISON_3, 1],
        [FC_ID.ANTIPOISON_2, 1],
    ]

    def _fn48():
        # Varrock East and Aubury both sit on that walk; sourcing each piece
        # where it is first needed cost three separate trips back to Varrock.
        step = decide(snap(Record({'stage': FC_STAGE.AVAN_PIECE, 'inv': [['coins', 200000]]})))
        expect(step.kind).to_be('buy')
        expect(step.kind == 'buy' and step.shop.npc).to_be('Aubury')
    test('the endgame kit is loaded before the walk to Johnathon', _fn48)

    def _fn49():
        step = decide(snap(Record({
        'stage': FC_STAGE.AVAN_PIECE,
        'inv': [['coins', 200000], ['shark', 16]],
        'inv_ids': [
        [FC_ID.AIR_RUNE, 600],
        [FC_ID.WATER_RUNE, 200],
        [FC_ID.EARTH_RUNE, 200],
        [FC_ID.FIRE_RUNE, 250],
        [FC_ID.DEATH_RUNE, 60],
    ],
        'bank_ids': [[FC_ID.ANTIPOISON_3, 2]],
        'worn_ids': [RUNE_SCIM],
    })))
        expect(step.kind).to_be('withdraw')
        expect(step.kind == 'withdraw' and step.items[0].get('qty')).to_be(2)
    test('two antipoison are carried — one cures him, one is for the spiders', _fn49)

    def _fn50():
        expect(talk_target(decide(snap(Record({
        'stage': FC_STAGE.AVAN_PIECE,
        'inv': [['coins', 200000], ['shark', 16]],
        'inv_ids': endgame_kit,
        'worn_ids': [RUNE_SCIM],
    }))))).to_be('Johnathon')
    test('two pieces and a full pack → Johnathon', _fn50)

    def _fn51():
        step = decide(snap(Record({'stage': FC_STAGE.SPOKEN_JOHNATHON})))
        expect(step.kind).to_be('buy')
        expect(step.kind == 'buy' and step.shop.npc).to_be('Jiminua')
    test('poisoned Johnathon with no antipoison anywhere → Jiminua', _fn51)

    def _fn52():
        expect(custom_name(decide(snap(Record({'stage': FC_STAGE.SPOKEN_JOHNATHON, 'inv_ids': [[FC_ID.ANTIPOISON_1, 1]]}))))).to_contain('cure Johnathon')
    test('any dose of antipoison is enough to cure him', _fn52)

    def _fn53():
        step = decide(snap(Record({'stage': FC_STAGE.CURED_JOHNATHON, 'inv': [['coins', 100000]]})))
        expect(step.kind).to_be('buy')
        expect(step.kind == 'buy' and step.shop.npc).to_be('Aubury')
    test('cured, with no runes, it buys them from Aubury', _fn53)
    stocked = [
        [FC_ID.AIR_RUNE, 600],
        [FC_ID.WATER_RUNE, 200],
        [FC_ID.EARTH_RUNE, 200],
        [FC_ID.FIRE_RUNE, 250],
        [FC_ID.DEATH_RUNE, 60],
        [FC_ID.ANTIPOISON_3, 1],
    ]

    def _fn54():
        # The kit carries 30 fire, one cast of Fire Blast is 5, so the old
        # one-cast floor was satisfied and the fight went in unable to finish.
        step = decide(snap(Record({
        'stage': FC_STAGE.CURED_JOHNATHON,
        'inv': [['coins', 200000], ['shark', 12]],
        'inv_ids': [[FC_ID.AIR_RUNE, 150], [FC_ID.FIRE_RUNE, 30], [FC_ID.WATER_RUNE, 30]],
        'worn_ids': [RUNE_SCIM],
    })))
        expect(step.kind).to_be('buy')
        expect(step.kind == 'buy' and step.item).to_be('Air rune')
    test('the teleport kit does not count as a fighting rune stock', _fn54)

    def _fn55():
        step = decide(snap(Record({
        'stage': FC_STAGE.CURED_JOHNATHON,
        'inv': [['shark', 12]],
        'inv_ids': [
        [FC_ID.AIR_RUNE, 600],
        [FC_ID.WATER_RUNE, 200],
        [FC_ID.EARTH_RUNE, 200],
        [FC_ID.FIRE_RUNE, 250],
        [FC_ID.DEATH_RUNE, 60],
    ],
        'bank_ids': [[FC_ID.ANTIPOISON_3, 1]],
        'worn_ids': [RUNE_SCIM],
    })))
        expect(step.kind).to_be('withdraw')
        expect(step.kind == 'withdraw' and step.items[0].get('id')).to_be(FC_ID.ANTIPOISON_3)
    test('a spare antipoison is taken for the spiders on the gate tiles', _fn55)

    def _fn56():
        # The wilderness deposit banks it on purpose; re-fetching walked the law
        # runes and the ring back into the fight they were banked to avoid.
        step = decide(snap(Record({
        'stage': FC_STAGE.CURED_JOHNATHON,
        'inv': [['shark', 12]],
        'inv_ids': stocked,
        'bank_ids': [[FC_ID.LAW_RUNE, 200], [2552, 1]],
        'worn_ids': [RUNE_SCIM],
    })))
        expect(step.kind).not_.to_be('withdraw')
    test('the teleport kit is not re-fetched while the demon is still standing', _fn56)

    def _fn57():
        step = decide(snap(Record({
        'stage': FC_STAGE.CURED_JOHNATHON,
        'inv': [['coins', 100000], ['shark', 12]],
        'inv_ids': stocked,
        'worn_ids': [RUNE_SCIM],
    })))
        expect(step.kind).to_be('deposit')
        expect(step.kind == 'deposit' and step.keep).not_.to_contain('coins')
        # Law runes stay: the lair is wilderness 3, so the walk home after the
        # last fragment becomes a Varrock teleport instead of a death march.
        expect(step.kind == 'deposit' and step.keep).to_contain('law rune')
        # the fragments must survive that deposit
        expect(step.kind == 'deposit' and step.keep_ids).to_contain(FC_ID.CREST_FROM_CALEB)
    test('the coin float is banked before stepping into the wilderness', _fn57)

    def _fn58():
        # Eating or drinking would otherwise drop the pack under a threshold and
        # walk the bot back to Varrock in the middle of the fight.
        expect(custom_name(decide(snap(Record({
        'stage': FC_STAGE.CURED_JOHNATHON,
        'tile': Record({'x': 3089, 'z': 9932, 'level': 0}),
        'inv': [['coins', 100000]],
    }))))).to_contain('Chronozon')
    test('inside the lair it fights rather than topping up mid-fight', _fn58)

    def _fn59():
        expect(custom_name(decide(snap(Record({'stage': FC_STAGE.CURED_JOHNATHON, 'inv': [['shark', 12]], 'inv_ids': stocked, 'worn_ids': [RUNE_SCIM]}))))).to_contain('Chronozon')
    test('runes, food, a weapon and no coin → the fight', _fn59)

    def _fn60():
        expect(custom_name(decide(snap(Record({
        'stage': FC_STAGE.CURED_JOHNATHON,
        'inv_ids': [[FC_ID.CREST_FROM_CALEB, 1], [FC_ID.CREST_FROM_AVAN, 1], [FC_ID.CREST_FROM_CHRONOZON, 1]],
    }))))).to_contain('combine')
    test('three fragments outrank the stage and are combined', _fn60)

    def _fn61():
        expect(talk_target(decide(snap(Record({'stage': FC_STAGE.SPOKEN_BOOT, 'drop_fragments': True}))))).to_be('Caleb')
    test('a fragment lost after Caleb sends the bot back for a replacement', _fn61)

    def _fn62():
        expect(custom_name(decide(snap(Record({'stage': FC_STAGE.CURED_JOHNATHON, 'drop_fragments': True, 'inv_ids': [[FC_ID.CREST_FROM_CALEB, 1]]}))))).to_contain('Avan')
    test('a fragment lost after Avan sends the bot back to him', _fn62)

    def _fn63():
        # `crest_avan_piece` routes to `avan_where`, pure chat, no lost-fragment
        # branch. That only exists from stage 9, so asking here parks forever.
        expect(talk_target(decide(snap(Record({
        'stage': FC_STAGE.AVAN_PIECE,
        'drop_fragments': True,
        'inv': [['coins', 200000], ['shark', 16]],
        'inv_ids': [
        [FC_ID.CREST_FROM_CALEB, 1],
        [FC_ID.AIR_RUNE, 600],
        [FC_ID.WATER_RUNE, 200],
        [FC_ID.EARTH_RUNE, 200],
        [FC_ID.FIRE_RUNE, 250],
        [FC_ID.DEATH_RUNE, 60],
        [FC_ID.ANTIPOISON_3, 1],
        [FC_ID.ANTIPOISON_2, 1],
    ],
        'worn_ids': [RUNE_SCIM],
    }))))).to_be('Johnathon')
    test('at stage 8 exactly it goes to Johnathon rather than asking Avan', _fn63)

    def _fn64():
        expect(talk_target(decide(snap(Record({'stage': FC_STAGE.CURED_JOHNATHON, 'drop_fragments': True, 'inv_ids': [[FC_ID.CREST_FROM_CHRONOZON, 1]]}))))).to_be('Caleb')
    test('holding only Chronozons piece, the brothers are asked again', _fn64)

    def _fn65():
        expect(talk_target(decide(snap(Record({'stage': FC_STAGE.CURED_JOHNATHON, 'inv_ids': [[FC_ID.FAMILY_CREST, 1]]}))))).to_be('Dimintheis')
    test('the restored crest goes back to Dimintheis', _fn65)


describe('Family Crest endgame', _fn47)


def _fn66():
    banked = [[FC_ID.LAW_RUNE, 500], [FC_ID.AIR_RUNE, 500], [FC_ID.FIRE_RUNE, 500], [FC_ID.WATER_RUNE, 500]]

    def _fn67():
        # The Global defaults off, and the nav layer reads the same setting,
        # fetching a kit it will never plan a hop with is a wasted bank trip.
        expect(teleport_kit_top_up(snap(Record({'stage': FC_STAGE.SPOKEN_DIMINTHEIS, 'bank_ids': banked})))).to_be_null()
    test('nothing is fetched while nav teleports are off', _fn67)

    def _fn68():
        # Every spell hop needs air as well as law; a guard keyed on law alone
        # stopped after one withdraw and left the spells uncastable.
        with_laws = snap(Record({'stage': FC_STAGE.SPOKEN_DIMINTHEIS, 'inv_ids': [[FC_ID.LAW_RUNE, 30]], 'bank_ids': banked}))
        step = teleport_kit_plan(with_laws)
        expect((step.kind if step is not None else None)).to_be('withdraw')
        expect((step.kind if step is not None else None) == 'withdraw' and step.items[0].get('id')).to_be(FC_ID.AIR_RUNE)
    test('the whole kit is fetched, not just the law runes', _fn68)

    def _fn69():
        # Why: only law has to be banked, Aubury stocks the rest, twenty tiles from the booth this trip already visits.
        step = teleport_kit_plan(snap(Record({
        'stage': FC_STAGE.SPOKEN_DIMINTHEIS,
        'inv_ids': [[FC_ID.LAW_RUNE, 30]],
        'bank_ids': [[FC_ID.LAW_RUNE, 200]],
    })))
        expect((step.kind if step is not None else None)).to_be('buy')
        expect((step.kind if step is not None else None) == 'buy' and step.shop.npc).to_be('Aubury')
        expect((step.kind if step is not None else None) == 'buy' and step.item).to_be('Air rune')
    test('spell runes are bought from Aubury when the bank has none', _fn69)

    def _fn70():
        # Twice now a satisfied-runes check returned before reaching the ring.
        step = teleport_kit_plan(snap(Record({
        'stage': FC_STAGE.SPOKEN_DIMINTHEIS,
        'inv_ids': [[FC_ID.LAW_RUNE, 30], [FC_ID.AIR_RUNE, 150], [FC_ID.FIRE_RUNE, 30], [FC_ID.WATER_RUNE, 30]],
        'bank_ids': [[2552, 1]],
    })))
        expect((step.kind if step is not None else None)).to_be('withdraw')
        expect((step.kind if step is not None else None) == 'withdraw' and step.items[0].get('id')).to_be(2552)
    test('the ring is fetched even once every rune is already carried', _fn70)

    def _fn71():
        # The ring reaches Al Kharid, which no spell on this book can.
        step = teleport_kit_plan(snap(Record({'stage': FC_STAGE.SPOKEN_DIMINTHEIS, 'bank_ids': [[2560, 1]]})))
        expect((step.kind if step is not None else None)).to_be('withdraw')
        expect((step.kind if step is not None else None) == 'withdraw' and step.items[0].get('id')).to_be(2560)
    test('a banked ring is fetched even with no law runes anywhere', _fn71)

    def _fn72():
        # Law runes are Magic Guild / Mage Arena stock only, so this is normal.
        expect(teleport_kit_plan(snap(Record({'stage': FC_STAGE.SPOKEN_DIMINTHEIS, 'bank_known': True})))).to_be_null()
    test('an empty bank walks rather than blocking', _fn72)


describe('Family Crest teleport kit', _fn66)


def _fn73():
    def _fn74():
        expect(familycrest.record.id).to_be('crest')
        expect(familycrest.record.name).to_be('Family Crest')
    test('the record is the one registered in data/quests', _fn74)

    def _fn75():
        expect(familycrest.owns_inventory).to_be(True)
    test('it owns its own inventory — the legs need different loadouts', _fn75)

    def _fn76():
        caleb = ['swordfish', 'bass', 'tuna', 'salmon', 'shrimps']
        for food in ((familycrest.sustain.foods if familycrest.sustain is not None else None) if (familycrest.sustain.foods if familycrest.sustain is not None else None) is not None else []):
            expect(caleb).not_.to_contain(food.lower())
    test('sustain never eats one of Calebs five fish', _fn76)

    def _fn77():
        expect(list(BLASTS)).to_equal(['Wind blast', 'Water blast', 'Earth blast', 'Fire blast'])
    test('all four elemental blasts are cast, in the order the demon needs', _fn77)

    def _fn78():
        # Two tiles clear of the demon's body, and eleven-plus from spider
        # spawns that wander ten, the east alcove sits three inside it.
        expect(Record({'x': SAFESPOT.x, 'z': SAFESPOT.z, 'level': SAFESPOT.level})).to_equal(Record({'x': 3089, 'z': 9932, 'level': 0}))
    test('the safespot is the south end, out of the poison spiders roam', _fn78)


describe('Family Crest module wiring', _fn73)
