"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/waterfall.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.geometry import Tile
from rs2004.quests.defs.waterfall import WATERFALL_STAGE, decide, parse_waterfall_journal, read_waterfall_stage, source_food, waterfall, waterfall_area, waterfall_dungeon_entry_readiness, waterfall_funding_target
from rs2004.quests.food import quest_food
from rs2004.quests.engine.types import QuestSnapshot

def _fn1():
    quest_food.name = 'Trout'


before_each(_fn1)
ITEM = Record({
    'BOOK': Record({'id': 292, 'name': 'Book on baxtorian'}),
    'GOLRIE_KEY': Record({'id': 293, 'name': 'A key'}),
    'PEBBLE': Record({'id': 294, 'name': "Glarial's pebble"}),
    'AMULET': Record({'id': 295, 'name': "Glarial's amulet"}),
    'FULL_URN': Record({'id': 296, 'name': "Glarial's urn"}),
    'EMPTY_URN': Record({'id': 297, 'name': "Glarial's urn"}),
    'BAXTORIAN_KEY': Record({'id': 298, 'name': 'A key'}),
    'WATER_RUNE': Record({'id': 555, 'name': 'Water rune', 'stackable': True}),
    'AIR_RUNE': Record({'id': 556, 'name': 'Air rune', 'stackable': True}),
    'EARTH_RUNE': Record({'id': 557, 'name': 'Earth rune', 'stackable': True}),
    'COINS': Record({'id': 995, 'name': 'Coins', 'stackable': True}),
    'ROPE': Record({'id': 954, 'name': 'Rope'}),
    'SWORD': Record({'id': 1277, 'name': 'Bronze sword'}),
    'EMPTY_CUP': Record({'id': 1980, 'name': 'Empty cup'}),
    'FOOD': Record({'id': 333, 'name': 'Trout'}),
})


def count_by_name(entries):
    counts = {}
    for item, qty in entries:
        key = item.name.lower()
        _v2 = counts.get(key)
        counts[key] = ((_v2 if _v2 is not None else 0)) + qty
    return counts


def count_by_id(entries):
    counts = {}
    for item, qty in entries:
        _v3 = counts.get(item.id)
        counts[item.id] = ((_v3 if _v3 is not None else 0)) + qty
    return counts


def used_slots(entries):
    return sum([((1 if qty > 0 else 0) if item.stackable else qty) for item, qty in entries])


# Why: rs2b0t tells an omitted tile, the Ardougne bank, from a null one; pocketpy's defaults are literals, so 'bank'.
def snapshot(journal=None, stage=None, inv=None, worn=None, bank=None, bank_known=None, tile='bank', free_slots=None):
    inv = (inv if inv is not None else [])
    bank = (bank if bank is not None else [])
    worn = (worn if worn is not None else [])
    given = [] if tile == 'bank' or tile is None else tile
    tile = (None if tile is None else Tile(
        given[0] if len(given) > 0 else 2616,
        given[1] if len(given) > 1 else 3332,
        given[2] if len(given) > 2 else 0,
    ))
    _v5 = count_by_id(bank).get(ITEM.COINS.id)
    return QuestSnapshot(**{
        'journal': (journal if journal is not None else 'in_progress'),
        'inv': count_by_name(inv),
        'inv_ids': count_by_id(inv),
        'worn': set([item.name.lower() for item in worn]),
        'worn_ids': set([item.id for item in worn]),
        'no_progress': 0,
        'bank_coins': (_v5 if _v5 is not None else 0),
        'stage': stage,
        'bank': count_by_name(bank),
        'bank_ids': count_by_id(bank),
        'bank_known': (bank_known if bank_known is not None else True),
        'tile': tile,
        'free_slots': (free_slots if free_slots is not None else max(0, 28 - used_slots(inv))),
    })


START_PACK = [[ITEM.ROPE, 1], [ITEM.FOOD, 8], [ITEM.COINS, 992]]
DUNGEON_PACK = [
    [ITEM.ROPE, 1],
    [ITEM.FOOD, 8],
    [ITEM.AMULET, 1],
    [ITEM.FULL_URN, 1],
    [ITEM.AIR_RUNE, 6],
    [ITEM.EARTH_RUNE, 6],
    [ITEM.WATER_RUNE, 6],
    [ITEM.COINS, 500],
]
FINAL_PACK = [[ITEM.ROPE, 1], [ITEM.FOOD, 8], [ITEM.AMULET, 1], [ITEM.FULL_URN, 1], [ITEM.COINS, 500]]


def custom_name(step):
    return (step.name if step.kind == 'custom' else None)


def withdrawal(step):
    expect(step.kind).to_be('withdraw')
    if step.kind != 'withdraw':
        raise RuntimeError('expected withdraw step')
    return step


def _fn6():
    cases = [
        [WATERFALL_STAGE.NOT_STARTED, ['@red@I can start this quest by speaking to Almera.']],
        [WATERFALL_STAGE.STARTED, ['I spoke to Almera in a house close to the Baxtorian waterfall.']],
        [WATERFALL_STAGE.SPOKEN_TO_HUDON, ['I found Hudon a short raft ride down the river.']],
        [WATERFALL_STAGE.READ_BOOK, ["The book also mentions Glarial's tomb. I should investigate it."]],
        [WATERFALL_STAGE.ENTERED_TOMB, ['I managed to enter the Tomb of Glarial.']],
        [WATERFALL_STAGE.ENTERED_WATERFALL, ['I used it to enter Baxtorian Falls.']],
        [
        WATERFALL_STAGE.ENTERED_PUZZLE,
        ["I found a Chalice within Baxtorian Falls. However, it is floating out of reach. I'll need to work out how to get to it."],
    ],
        [WATERFALL_STAGE.RAISED_FLOOR, ['I worked out how to raise the floor.']],
        [WATERFALL_STAGE.COMPLETE, ['@gre@Quest complete!']],
    ]
    def _each_121(stage, lines):
        def _fn7():
            expect(parse_waterfall_journal(lines)).to_be(stage)
        test(f'recognizes exact stage {stage}', _fn7)

    for stage, lines in cases:
        _each_121(stage, lines)

    def _fn8():
        expect(parse_waterfall_journal([
        'I can start this quest by speaking to Almera.',
        'I spoke to Almera in a house close to the Baxtorian waterfall.',
        'I found Hudon a short raft ride down the river.',
        "The book also mentions Glarial's tomb.",
        'I managed to enter the Tomb of Glarial.',
        'I used it to enter Baxtorian Falls.',
        "I'll need to work out how to get to it.",
        'Now I just need to retrieve the treasure.',
    ])).to_be(WATERFALL_STAGE.RAISED_FLOOR)
    test('matches the newest retained journal entry before older history', _fn8)

    def _fn9():
        expect(parse_waterfall_journal('@yel@I used it | to enter   Baxtorian Falls.')).to_be(WATERFALL_STAGE.ENTERED_WATERFALL)
    test('normalizes color tags, pipes, whitespace, and a single rendered string', _fn9)

    def _fn10():
        expect(parse_waterfall_journal([])).to_be_undefined()
        expect(parse_waterfall_journal(['Please wait...'])).to_be_undefined()
        expect(parse_waterfall_journal(['A future server journal phrase.'])).to_be_undefined()
    test('fails closed on loading or unrecognized text', _fn10)


describe('Waterfall journal stage parser', _fn6)


def _fn11():
    cases = [
        ['unknown', None],
        ['mainland', [3222, 3218, 0]],
        ['hudonMound', [2512, 3481, 0]],
        ['fallsTreeBank', [2512, 3470, 0]],
        ['fallsLedge', [2512, 3463, 0]],
        ['tgvDungeon', [2533, 9556, 0]],
        ['glarialTomb', [2554, 9844, 0]],
        ['waterfallDungeon', [2575, 9861, 0]],
        ['puzzleRoom', [2565, 9912, 0]],
        ['raisedRoom', [2603, 9910, 0]],
    ]
    def _each_166(area, tile):
        def _fn12():
            world_tile = (Record({'x': tile[0], 'z': tile[1], 'level': tile[2]}) if tile else None)
            expect(waterfall_area(world_tile)).to_be(area)
        test(f'classifies {area}', _fn12)

    for area, tile in cases:
        _each_166(area, tile)

    def _fn13():
        expect(waterfall_area(Tile(2598, 9905, 0))).to_be('raisedRoom')
        expect(waterfall_area(Tile(2558, 9907, 0))).to_be('puzzleRoom')
    test('specific raised and puzzle rooms win over the encompassing dungeon bounds', _fn13)


describe('Waterfall area classifier', _fn11)


def _fn14():
    def _fn15():
        expect(waterfall_dungeon_entry_readiness(39, 1, 10, False)).to_be('waitForEnergy')
        expect(waterfall_dungeon_entry_readiness(40, 1, 10, False)).to_be('heal')
    test('waits for the full hostile-route energy budget before healing or toggling run', _fn15)

    def _fn16():
        expect(waterfall_dungeon_entry_readiness(40, 10, 10, False)).to_be('enableRun')
        expect(waterfall_dungeon_entry_readiness(40, 10, 10, True)).to_be('ready')
    test('enters only at full health with run enabled', _fn16)


describe('Waterfall dungeon survival gate', _fn14)


def _fn17():
    def _fn18():
        expect(decide(snapshot(journal='complete', bank_known=False)).kind).to_be('done')
    test('coarse complete status is terminal without a stage', _fn18)

    def _fn19():
        expect(decide(snapshot(stage=WATERFALL_STAGE.COMPLETE)).kind).to_be('done')
    test('exact stage 10 is terminal while the coarse journal is still in progress', _fn19)

    def _fn20():
        step = decide(snapshot(journal='unknown', stage=WATERFALL_STAGE.ENTERED_PUZZLE, inv=DUNGEON_PACK))
        expect(step).to_equal(Record({'kind': 'wait', 'reason': 'quest journal not loaded'}))
    test('unknown journal waits instead of guessing from inventory', _fn20)

    def _fn21():
        expect(decide(snapshot())).to_equal(Record({'kind': 'wait', 'reason': 'Waterfall Quest journal stage unavailable'}))
        expect(decide(snapshot(stage=7))).to_equal(Record({'kind': 'wait', 'reason': 'unrecognized Waterfall Quest stage 7'}))
    test('missing and unrecognized exact stages fail closed', _fn21)

    def _fn22():
        cases = [
        [WATERFALL_STAGE.NOT_STARTED, Record({'inv': START_PACK}), 'talk', 'Almera'],
        [WATERFALL_STAGE.STARTED, Record({'inv': START_PACK}), 'custom', 'board Almera raft and find Hudon'],
        [
        WATERFALL_STAGE.SPOKEN_TO_HUDON,
        Record({'inv': START_PACK}),
        'custom',
        'find and read the Book on Baxtorian',
    ],
        [
        WATERFALL_STAGE.READ_BOOK,
        Record({'inv': [[ITEM.PEBBLE, 1], [ITEM.FOOD, 8]]}),
        'custom',
        'loot Glarial amulet and urn',
    ],
        [WATERFALL_STAGE.ENTERED_TOMB, Record({'inv': DUNGEON_PACK}), 'custom', 'enter Baxtorian Falls'],
        [WATERFALL_STAGE.ENTERED_WATERFALL, Record({'inv': DUNGEON_PACK}), 'custom', 'cross into Baxtorian Falls'],
        [WATERFALL_STAGE.ENTERED_PUZZLE, Record({'inv': DUNGEON_PACK}), 'custom', 'cross into Baxtorian Falls'],
        [WATERFALL_STAGE.RAISED_FLOOR, Record({'inv': FINAL_PACK}), 'custom', 'return to the Waterfall dungeon'],
    ]
        for stage, options, kind, detail in cases:
            step = decide(snapshot(stage=stage, **options._fields))
            expect(step.kind).to_be(kind)
            if kind == 'talk' and step.kind == 'talk':
                expect(step.stop.npc).to_be(detail)
            if kind == 'custom':
                expect(custom_name(step)).to_be(detail)
    test('dispatches every implemented exact stage independently of held-item phase guesses', _fn22)


describe('journal and exact-stage gates', _fn17)


def _fn24():
    def _each_255(stage):
        def _fn25():
            expect(decide(snapshot(stage=stage, bank_known=False)).kind).to_be('scan_bank')
        test(f'stage {stage} scans the bank before mainland recovery', _fn25)

    for stage in [
        WATERFALL_STAGE.NOT_STARTED,
        WATERFALL_STAGE.READ_BOOK,
        WATERFALL_STAGE.ENTERED_TOMB,
        WATERFALL_STAGE.ENTERED_WATERFALL,
        WATERFALL_STAGE.ENTERED_PUZZLE,
        WATERFALL_STAGE.RAISED_FLOOR,
    ]:
        _each_255(stage)

    def _fn26():
        step = decide(snapshot(stage=WATERFALL_STAGE.ENTERED_PUZZLE, bank_known=False, tile=[2565, 9912]))
        expect(custom_name(step)).to_be('solve the six rune pillars')
    test('puzzle dispatch never tries to bank from inside the dungeon', _fn26)

    def _fn27():
        step = decide(snapshot(stage=WATERFALL_STAGE.RAISED_FLOOR, bank_known=False, inv=[[ITEM.FULL_URN, 1]], tile=[2603, 9910], free_slots=5))
        expect(custom_name(step)).to_be("pour Glarial's ashes into the Chalice")
    test('raised-room completion never tries to bank from inside the dungeon', _fn27)


describe('bank knowledge and one-way areas', _fn24)


def _fn28():
    # Why: refilling on any shortfall walked the run back to Ardougne for a single fish, and the walker
    # was still following the route to the falls when the next decision turned it round.
    def pack(held):
        return snapshot(stage=WATERFALL_STAGE.ENTERED_WATERFALL, inv=[[ITEM.FOOD, held]], bank=[[ITEM.FOOD, 100]])

    def _fn29():
        for held in [8, 7, 6, 5, 4]:
            expect(source_food(pack(held))).to_be_null()
    test('a pack above the low mark asks for nothing', _fn29)

    def _fn30():
        expect(withdrawal(source_food(pack(3))).items).to_equal([Record({'name': 'Trout', 'id': 333, 'qty': 5})])
        expect(withdrawal(source_food(pack(0))).items).to_equal([Record({'name': 'Trout', 'id': 333, 'qty': 8})])
    test('at or under the low mark it refills to the float in one trip', _fn30)

    def _fn31():
        dry = snapshot(stage=WATERFALL_STAGE.ENTERED_WATERFALL, inv=[[ITEM.FOOD, 1]], bank=[])
        expect((source_food(dry).kind if source_food(dry) is not None else None)).to_be('wait')
    test('an empty bank parks rather than walking there for nothing', _fn31)


describe('food is refilled at a low mark, not on every bite', _fn28)


def _fn32():
    def _fn33():
        expect(waterfall_funding_target(1472, Tile(3253, 3420, 0))).to_be(1482)
        expect(waterfall_funding_target(500, Tile(2616, 3332, 0))).to_be(570)
    test('reserves the exact observed route home from each funding area', _fn33)

    def _fn34():
        step = decide(snapshot(stage=WATERFALL_STAGE.NOT_STARTED, inv=[[ITEM.COINS, 992], [ITEM.FOOD, 8], [ITEM.ROPE, 1]], tile=[2654, 3311]))
        expect(step.kind).to_be('talk')
        if step.kind == 'talk':
            expect(step.stop.npc).to_be('Almera')
    test('does not refarm after the aggregate cash is spent on the stocked western loadout', _fn34)

    def _fn35():
        expect(custom_name(decide(snapshot(stage=WATERFALL_STAGE.NOT_STARTED, inv=[[ITEM.COINS, 500], [ITEM.EMPTY_CUP, 6], [ITEM.FOOD, 8], [ITEM.ROPE, 1]], tile=[2654, 3311])))).to_be('bank everything except Waterfall supplies')
    test('banks spent cups but retains unconsumed tea during startup', _fn35)

    def _fn36():
        expect(custom_name(decide(snapshot(stage=WATERFALL_STAGE.STARTED, inv=[[ITEM.SWORD, 28]], tile=[3222, 3218])))).to_be('prepare the Almera raft trip')
        expect(custom_name(decide(snapshot(stage=WATERFALL_STAGE.SPOKEN_TO_HUDON, inv=[[ITEM.SWORD, 28]], tile=[3222, 3218])))).to_be('prepare the Book on Baxtorian trip')
    test('clears a full arbitrary restart pack before stage 1 food or stage 2 book acquisition', _fn36)


describe('coin funding', _fn32)


def _fn37():
    def _fn38():
        bax = withdrawal(decide(snapshot(stage=WATERFALL_STAGE.ENTERED_WATERFALL, inv=DUNGEON_PACK, bank=[[ITEM.BAXTORIAN_KEY, 1]])))
        expect(bax.items).to_equal([Record({'name': 'A key', 'id': 298, 'qty': 1})])
        golrie = decide(snapshot(stage=WATERFALL_STAGE.ENTERED_WATERFALL, inv=DUNGEON_PACK, bank=[[ITEM.GOLRIE_KEY, 1]]))
        expect(custom_name(golrie)).to_be('cross into Baxtorian Falls')
    test('withdraws Baxtorian key 298, not same-name Golrie key 293', _fn38)

    def _fn39():
        expect(custom_name(decide(snapshot(stage=WATERFALL_STAGE.ENTERED_WATERFALL, inv=list(DUNGEON_PACK) + [[ITEM.BAXTORIAN_KEY, 1]])))).to_be('cross into Baxtorian Falls')
        expect(custom_name(decide(snapshot(stage=WATERFALL_STAGE.ENTERED_WATERFALL, inv=list(DUNGEON_PACK) + [[ITEM.GOLRIE_KEY, 1]])))).to_be('prepare a safe Waterfall dungeon trip')
    test('keeps Baxtorian key 298 but strips same-name Golrie key 293 from the dungeon loadout', _fn39)

    def _fn40():
        without_urn = [entry for entry in DUNGEON_PACK if entry[0].id != ITEM.FULL_URN.id]
        full = withdrawal(decide(snapshot(stage=WATERFALL_STAGE.ENTERED_WATERFALL, inv=without_urn, bank=[[ITEM.FULL_URN, 1]])))
        expect(full.items).to_equal([Record({'name': "Glarial's urn", 'id': 296, 'qty': 1})])
        empty = decide(snapshot(stage=WATERFALL_STAGE.ENTERED_WATERFALL, inv=[[ITEM.PEBBLE, 1], [ITEM.FOOD, 8]], bank=[[ITEM.EMPTY_URN, 1]]))
        expect(custom_name(empty)).to_be('loot Glarial amulet and urn')
    test('withdraws full urn 296 and does not accept same-name empty urn 297', _fn40)

    def _fn42():
        step = decide(snapshot(stage=WATERFALL_STAGE.ENTERED_WATERFALL, inv=[[ITEM.PEBBLE, 1], [ITEM.AMULET, 1], [ITEM.EMPTY_URN, 1], [ITEM.FOOD, 8]]))
        expect(custom_name(step)).to_be('strip prohibited items before Glarial tomb')
    test('an empty urn in inventory is prohibited tomb baggage, not a recovered full urn', _fn42)


describe('exact object-ID collisions', _fn37)


def _fn43():
    def _fn44():
        step = withdrawal(decide(snapshot(stage=WATERFALL_STAGE.READ_BOOK, inv=[[ITEM.FOOD, 8]], bank=[[ITEM.PEBBLE, 1]])))
        expect(step.items).to_equal([Record({'name': "Glarial's pebble", 'id': 294, 'qty': 1})])
    test('withdraws the exact pebble ID when it is banked', _fn44)

    def _fn45():
        expect(custom_name(decide(snapshot(stage=WATERFALL_STAGE.READ_BOOK, inv=[[ITEM.FOOD, 8]])))).to_be('recover Glarial pebble from Golrie')
    test('returns to Golrie when the pebble is absent from a known bank', _fn45)

    def _fn46():
        forbidden = decide(snapshot(stage=WATERFALL_STAGE.READ_BOOK, inv=[[ITEM.PEBBLE, 1], [ITEM.FOOD, 8], [ITEM.AIR_RUNE, 6]]))
        expect(custom_name(forbidden)).to_be('strip prohibited items before Glarial tomb')
        equipped = decide(snapshot(stage=WATERFALL_STAGE.READ_BOOK, inv=[[ITEM.PEBBLE, 1], [ITEM.FOOD, 8]], worn=[ITEM.SWORD]))
        expect(custom_name(equipped)).to_be('strip prohibited items before Glarial tomb')
    test('strips forbidden inventory and all equipment before tomb entry', _fn46)

    def _fn47():
        expect(custom_name(decide(snapshot(stage=WATERFALL_STAGE.RAISED_FLOOR, inv=[[ITEM.PEBBLE, 1], [ITEM.FOOD, 1], [ITEM.SWORD, 26]], bank=[[ITEM.FULL_URN, 1], [ITEM.BAXTORIAN_KEY, 1]])))).to_be('strip prohibited items before Glarial tomb')
    test('banks a full prohibited pack before trying to replenish tomb food', _fn47)

    def _fn48():
        step = decide(snapshot(stage=WATERFALL_STAGE.READ_BOOK, inv=[[ITEM.PEBBLE, 1], [ITEM.FOOD, 8], [ITEM.COINS, 500]]))
        expect(custom_name(step)).to_be('loot Glarial amulet and urn')
    test('retains only exact tomb-safe IDs and begins looting', _fn48)

    def _fn49():
        for stage in [WATERFALL_STAGE.READ_BOOK, WATERFALL_STAGE.ENTERED_TOMB]:
            expect(custom_name(decide(snapshot(stage=stage, bank_known=False, tile=[2554, 9844])))).to_be('loot Glarial amulet and urn')
    test('finishes tomb recovery in place without trying to reach a bank', _fn49)

    def _fn50():
        step = withdrawal(decide(snapshot(stage=WATERFALL_STAGE.ENTERED_TOMB, inv=[[ITEM.COINS, 500], [ITEM.FOOD, 8], [ITEM.ROPE, 1]], bank=[[ITEM.AMULET, 1], [ITEM.FULL_URN, 1]])))
        expect(step.items).to_equal([
        Record({'name': "Glarial's amulet", 'id': 295, 'qty': 1}),
        Record({'name': "Glarial's urn", 'id': 296, 'qty': 1}),
    ])
    test('withdraws both exact relics after a mainland death when they are banked', _fn50)

    def _fn51():
        withdraw_survivors = withdrawal(decide(snapshot(stage=WATERFALL_STAGE.RAISED_FLOOR, inv=[[ITEM.PEBBLE, 1], [ITEM.FOOD, 8]], bank=[[ITEM.FULL_URN, 1], [ITEM.BAXTORIAN_KEY, 1]])))
        expect(withdraw_survivors.items).to_equal([Record({'name': "Glarial's urn", 'id': 296, 'qty': 1}), Record({'name': 'A key', 'id': 298, 'qty': 1})])
        expect(custom_name(decide(snapshot(stage=WATERFALL_STAGE.RAISED_FLOOR, inv=[[ITEM.PEBBLE, 1], [ITEM.FOOD, 8], [ITEM.FULL_URN, 1], [ITEM.BAXTORIAN_KEY, 1]])))).to_be('loot Glarial amulet and urn')
    test('protects surviving relics during Golrie recovery, then carries them into the tomb', _fn51)


describe('Glarial tomb stripping and recovery', _fn43)


def _fn52():
    def _fn53():
        expect(custom_name(decide(snapshot(stage=WATERFALL_STAGE.ENTERED_WATERFALL, inv=DUNGEON_PACK)))).to_be('cross into Baxtorian Falls')
        expect(custom_name(decide(snapshot(stage=WATERFALL_STAGE.ENTERED_PUZZLE, inv=DUNGEON_PACK)))).to_be('cross into Baxtorian Falls')
    test('a complete mainland loadout enters the falls at stages 5 and 6', _fn53)

    def _fn54():
        relics = [ITEM.AMULET, ITEM.FULL_URN, ITEM.BAXTORIAN_KEY]
        expect(custom_name(decide(snapshot(stage=WATERFALL_STAGE.ENTERED_WATERFALL, inv=[[ITEM.COINS, 500]] + list([[item, 1] for item in relics]), tile=[3222, 3218])))).to_be('prepare a safe Waterfall dungeon trip')
        expect(custom_name(decide(snapshot(stage=WATERFALL_STAGE.ENTERED_WATERFALL, inv=[[ITEM.COINS, 500], [ITEM.ROPE, 1]] + list([[item, 1] for item in relics]) + [[ITEM.AIR_RUNE, 6], [ITEM.EARTH_RUNE, 6], [ITEM.WATER_RUNE, 6]], tile=[2616, 3332])))).to_be('prepare a safe Waterfall dungeon trip')
        refill = decide(snapshot(stage=WATERFALL_STAGE.ENTERED_WATERFALL, inv=[[ITEM.COINS, 500]], bank=list([[item, 1] for item in relics]) + [[ITEM.FOOD, 20]], tile=[3222, 3218]))
        expect(withdrawal(refill).items).to_equal([Record({'name': 'Trout', 'id': 333, 'qty': 8})])
        # Why: the supply bank no longer moves with the player, so east and west both restore from Ardougne.
        for tile in [[3222, 3218], [2616, 3332]]:
            restored = withdrawal(decide(snapshot(stage=WATERFALL_STAGE.ENTERED_WATERFALL, inv=[[ITEM.COINS, 500], [ITEM.FOOD, 8], [ITEM.ROPE, 1]], bank=[[item, 1] for item in relics], tile=tile)))
            expect([item['id'] for item in restored.items]).to_equal([295, 296, 298])
            expect(Record({
            'x': (restored.bank.x if restored.bank is not None else None),
            'z': (restored.bank.z if restored.bank is not None else None),
        })).to_equal(Record({'x': 2616, 'z': 3332}))
    test('banks relics before any capacity-bound food refill, then restores them after', _fn54)

    def _fn55():
        without_rope = [entry for entry in DUNGEON_PACK if entry[0].id != ITEM.ROPE.id]
        expect(withdrawal(decide(snapshot(stage=WATERFALL_STAGE.ENTERED_WATERFALL, inv=without_rope, bank=[[ITEM.ROPE, 1]]))).items).to_equal([Record({'name': 'Rope', 'id': 954, 'qty': 1})])
        expect(withdrawal(decide(snapshot(stage=WATERFALL_STAGE.ENTERED_WATERFALL, inv=[[ITEM.COINS, 500], [ITEM.ROPE, 1], [ITEM.FOOD, 2]], bank=[[ITEM.FOOD, 10], [ITEM.AMULET, 1], [ITEM.FULL_URN, 1]], tile=[2616, 3332]))).items).to_equal([Record({'name': 'Trout', 'id': 333, 'qty': 6})])
        short_air = [[item, (2 if item.id == ITEM.AIR_RUNE.id else qty)] for item, qty in DUNGEON_PACK]
        expect(withdrawal(decide(snapshot(stage=WATERFALL_STAGE.ENTERED_PUZZLE, inv=short_air, bank=[[ITEM.AIR_RUNE, 3]]))).items).to_equal([Record({'name': 'Air rune', 'id': 556, 'qty': 3})])
    test('withdraws missing rope, food, and partial runes by exact ID', _fn55)

    def _fn58():
        short_air = [[item, (5 if item.id == ITEM.AIR_RUNE.id else (600 if item.id == ITEM.COINS.id else qty))] for item, qty in DUNGEON_PACK]
        step = decide(snapshot(stage=WATERFALL_STAGE.ENTERED_PUZZLE, inv=short_air, tile=[3012, 3259]))
        expect(step.kind).to_be('buy')
        if step.kind == 'buy':
            expect(Record({'item': step.item, 'qty': step.qty, 'npc': step.shop.npc})).to_equal(Record({'item': 'Air rune', 'qty': 1, 'npc': 'Betty'}))
    test('buys only the residual rune shortage after an interrupted trip', _fn58)

    def _fn60():
        partial_pack = [[item, (900 if item.id == ITEM.COINS.id else qty)] for item, qty in [entry for entry in DUNGEON_PACK if entry[0].id != ITEM.EARTH_RUNE.id and entry[0].id != ITEM.WATER_RUNE.id]]
        step = decide(snapshot(stage=WATERFALL_STAGE.ENTERED_TOMB, inv=partial_pack, tile=[3012, 3259]))
        expect(step.kind).to_be('buy')
        if step.kind == 'buy':
            expect(Record({'item': step.item, 'qty': step.qty, 'npc': step.shop.npc, 'est_gp': step.est_gp})).to_equal(Record({'item': 'Earth rune', 'qty': 6, 'npc': 'Betty', 'est_gp': 144}))
        after_earth = [[item, (756 if item.id == ITEM.COINS.id else qty)] for item, qty in partial_pack]
        final_stack = decide(snapshot(stage=WATERFALL_STAGE.ENTERED_TOMB, inv=list(after_earth) + [[ITEM.EARTH_RUNE, 6]], tile=[3012, 3259]))
        expect(final_stack.kind).to_be('buy')
        if final_stack.kind == 'buy':
            expect(final_stack.item).to_be('Water rune')
    test('budgets all remaining Betty runes without returning to bank between stacks', _fn60)

    def _fn64():
        rune_ids = set([ITEM.AIR_RUNE.id, ITEM.EARTH_RUNE.id, ITEM.WATER_RUNE.id])
        without_runes = [entry for entry in DUNGEON_PACK if not (entry[0].id in rune_ids)]
        expect(withdrawal(decide(snapshot(stage=WATERFALL_STAGE.ENTERED_TOMB, inv=without_runes, bank=[[ITEM.EARTH_RUNE, 6], [ITEM.WATER_RUNE, 6]]))).items).to_equal([Record({'name': 'Earth rune', 'id': 557, 'qty': 6}), Record({'name': 'Water rune', 'id': 555, 'qty': 6})])
        expect(withdrawal(decide(snapshot(stage=WATERFALL_STAGE.ENTERED_TOMB, inv=list(without_runes) + [[ITEM.EARTH_RUNE, 6]], bank=[[ITEM.WATER_RUNE, 6]]))).items).to_equal([Record({'name': 'Water rune', 'id': 555, 'qty': 6})])
    test('withdraws every useful banked rune before starting Betty purchases', _fn64)

    def _fn66():
        one_air_short = [[item, (5 if item.id == ITEM.AIR_RUNE.id else (100 if item.id == ITEM.COINS.id else qty))] for item, qty in DUNGEON_PACK]
        top_up = withdrawal(decide(snapshot(stage=WATERFALL_STAGE.ENTERED_TOMB, inv=one_air_short, bank=[[ITEM.COINS, 2000000]])))
        expect(top_up.items).to_equal([Record({'name': 'Coins', 'id': 995, 'qty': 484})])
        partial_air = [[item, (500 if item.id == ITEM.COINS.id else qty)] for item, qty in [entry for entry in DUNGEON_PACK if entry[0].id != ITEM.AIR_RUNE.id]]
        expect(withdrawal(decide(snapshot(stage=WATERFALL_STAGE.ENTERED_TOMB, inv=list(partial_air) + [[ITEM.AIR_RUNE, 2]], bank=[[ITEM.AIR_RUNE, 3], [ITEM.COINS, 2000000]]))).items).to_equal([Record({'name': 'Air rune', 'id': 556, 'qty': 3})])
    test('budgets only the unbanked residual and preserves the cash float before departure', _fn66)

    def _fn70():
        excluded_ids = set([ITEM.COINS.id, ITEM.AIR_RUNE.id, ITEM.EARTH_RUNE.id, ITEM.WATER_RUNE.id])
        without_coins_or_runes = [entry for entry in DUNGEON_PACK if not (entry[0].id in excluded_ids)]
        step = decide(snapshot(stage=WATERFALL_STAGE.ENTERED_TOMB, inv=without_coins_or_runes, tile=[2616, 3332]))
        expect(step.kind).to_be('custom')
        expect(custom_name(step)).to_be('earn 992 gp for Waterfall supplies')
    test('self-funds the exact full rune-shop budget when the known bank has no cash or runes', _fn70)

    def _fn72():
        expect(custom_name(decide(snapshot(stage=WATERFALL_STAGE.ENTERED_WATERFALL, tile=[2575, 9861], bank_known=False)))).to_be('cross the Waterfall dungeon')
        expect(custom_name(decide(snapshot(stage=WATERFALL_STAGE.ENTERED_PUZZLE, tile=[2565, 9912], bank_known=False)))).to_be('solve the six rune pillars')
    test('dispatches stage 5 through the dungeon and stage 6 to the pillars', _fn72)

    def _fn73():
        expect(custom_name(decide(snapshot(stage=WATERFALL_STAGE.ENTERED_WATERFALL, tile=[2512, 3481], inv=[[ITEM.AMULET, 1]])))).to_be('swim back from Hudon mound')
        expect(decide(snapshot(stage=WATERFALL_STAGE.ENTERED_WATERFALL, tile=[2512, 3470], inv=[[ITEM.AMULET, 1]]))).to_equal(Record({'kind': 'wait', 'reason': 'Rope missing on the one-way Waterfall crossing'}))
        expect(custom_name(decide(snapshot(stage=WATERFALL_STAGE.ENTERED_WATERFALL, tile=[2512, 3463], inv=[[ITEM.ROPE, 1]])))).to_be('leave the ledge without risking the amulet door')
    test('handles one-way crossing recovery without impossible banking', _fn73)


describe('stage 5/6 dungeon loadout and dispatch', _fn52)


def _fn74():
    def _fn75():
        for tile in [[2512, 3481], [2512, 3470], [2512, 3463]]:
            expect(custom_name(decide(snapshot(stage=WATERFALL_STAGE.ENTERED_TOMB, tile=tile, inv=DUNGEON_PACK)))).to_be('enter Baxtorian Falls')
    test('continues the intended raft, tree, and ledge transit instead of escaping it', _fn75)

    def _fn76():
        expect(custom_name(decide(snapshot(stage=WATERFALL_STAGE.ENTERED_TOMB, tile=[2512, 3481], inv=[[ITEM.AMULET, 1]])))).to_be('swim back from Hudon mound')
        expect(decide(snapshot(stage=WATERFALL_STAGE.ENTERED_TOMB, tile=[2512, 3470], inv=[[ITEM.AMULET, 1]]))).to_equal(Record({'kind': 'wait', 'reason': 'Rope missing on the one-way Waterfall crossing'}))
        expect(custom_name(decide(snapshot(stage=WATERFALL_STAGE.ENTERED_TOMB, tile=[2512, 3463], inv=[[ITEM.ROPE, 1]])))).to_be('leave the ledge without risking the amulet door')
    test('does not strand a missing-Rope trip or open the ledge door without the amulet', _fn76)


describe('stage 4 Waterfall crossing', _fn74)


def _fn77():
    def _fn78():
        expect(custom_name(decide(snapshot(stage=WATERFALL_STAGE.RAISED_FLOOR, tile=[2603, 9910], inv=[[ITEM.FULL_URN, 1]], free_slots=5)))).to_be("pour Glarial's ashes into the Chalice")
    test('uses the full urn at exactly five free slots', _fn78)

    def _fn79():
        expect(custom_name(decide(snapshot(stage=WATERFALL_STAGE.RAISED_FLOOR, tile=[2603, 9910], inv=[[ITEM.FULL_URN, 1]], free_slots=4)))).to_be('wash out to recover the final loadout')
        expect(custom_name(decide(snapshot(stage=WATERFALL_STAGE.RAISED_FLOOR, tile=[2603, 9910], inv=[[ITEM.EMPTY_URN, 1]], free_slots=5)))).to_be('wash out to recover the final loadout')
    test('washes out with four free slots or only the empty urn', _fn79)

    def _fn80():
        for tile in [[2575, 9861], [2565, 9912]]:
            expect(custom_name(decide(snapshot(stage=WATERFALL_STAGE.RAISED_FLOOR, tile=tile, bank_known=False)))).to_be('return directly to the raised Chalice room')
    test('uses the keyed direct route from either dungeon side', _fn80)

    def _fn81():
        expect(custom_name(decide(snapshot(stage=WATERFALL_STAGE.RAISED_FLOOR, inv=FINAL_PACK)))).to_be('return to the Waterfall dungeon')
    test('final mainland loadout does not source puzzle runes again', _fn81)

    def _fn82():
        expect(custom_name(decide(snapshot(stage=WATERFALL_STAGE.RAISED_FLOOR, inv=list(FINAL_PACK) + [[ITEM.AIR_RUNE, 1]])))).to_be('prepare a safe final Waterfall trip')
    test('banks puzzle leftovers before the final trip', _fn82)

    def _fn83():
        expect(custom_name(decide(snapshot(stage=WATERFALL_STAGE.RAISED_FLOOR, inv=[[item, (20 if item.id == ITEM.FOOD.id else qty)] for item, qty in FINAL_PACK])))).to_be('prepare a safe final Waterfall trip')
        expect(custom_name(decide(snapshot(stage=WATERFALL_STAGE.ENTERED_WATERFALL, inv=list(DUNGEON_PACK) + [[ITEM.ROPE, 1]])))).to_be('prepare a safe Waterfall dungeon trip')
    test('rebuilds overfilled allowed-item packs instead of looping below five reward slots', _fn83)

    def _fn85():
        step = withdrawal(decide(snapshot(stage=WATERFALL_STAGE.RAISED_FLOOR, inv=[[ITEM.COINS, 500], [ITEM.FOOD, 8], [ITEM.ROPE, 1]], bank=[[ITEM.AMULET, 1], [ITEM.FULL_URN, 1], [ITEM.BAXTORIAN_KEY, 1]])))
        expect(step.items).to_equal([
        Record({'name': "Glarial's amulet", 'id': 295, 'qty': 1}),
        Record({'name': "Glarial's urn", 'id': 296, 'qty': 1}),
        Record({'name': 'A key', 'id': 298, 'qty': 1}),
    ])
    test('withdraws exact banked final relics and key after a death', _fn85)


describe('stage 8 final recovery and completion', _fn77)


def _fn86():
    def _fn87():
        food = withdrawal(decide(snapshot(stage=WATERFALL_STAGE.ENTERED_PUZZLE, inv=[[ITEM.COINS, 600]], bank=[[ITEM.COINS, 1999400], [ITEM.FOOD, 20]], tile=[2616, 3332])))
        expect(food.items).to_equal([Record({'name': 'Trout', 'id': 333, 'qty': 8})])
        expect(custom_name(decide(snapshot(stage=WATERFALL_STAGE.ENTERED_PUZZLE, inv=[[ITEM.FOOD, 8]], tile=[2654, 3311])))).to_be('recover Glarial pebble from Golrie')
    test('draws food from the bank before sending an empty 10-HP recovery account to Golrie', _fn87)
    def _each_563(stage):
        def _fn88():
            expect(decide(snapshot(stage=stage, bank_known=False)).kind).to_be('scan_bank')
        test(f'stage {stage} scans an unknown post-death bank', _fn88)

        def _fn89():
            expect(custom_name(decide(snapshot(stage=stage, inv=[[ITEM.FOOD, 8]])))).to_be('recover Glarial pebble from Golrie')
        test(f'stage {stage} reacquires the pebble when all dropped relics are absent', _fn89)

        def _fn90():
            expect(custom_name(decide(snapshot(stage=stage, inv=[[ITEM.FOOD, 8], [ITEM.GOLRIE_KEY, 1]], bank_known=False, tile=[2515, 9570])))).to_be('recover Glarial pebble from Golrie')
        test(f'stage {stage} resumes the Golrie leg after acquiring its key', _fn90)

        def _fn91():
            step = withdrawal(decide(snapshot(stage=stage, inv=[[ITEM.COINS, 500], [ITEM.FOOD, 8], [ITEM.ROPE, 1]], bank=[[ITEM.AMULET, 1], [ITEM.FULL_URN, 1]])))
            expect(step.items).to_equal([
        Record({'name': "Glarial's amulet", 'id': 295, 'qty': 1}),
        Record({'name': "Glarial's urn", 'id': 296, 'qty': 1}),
    ])
        test(f'stage {stage} withdraws exact relics from a known post-death bank', _fn91)

    for stage in [
        WATERFALL_STAGE.ENTERED_TOMB,
        WATERFALL_STAGE.ENTERED_WATERFALL,
        WATERFALL_STAGE.ENTERED_PUZZLE,
        WATERFALL_STAGE.RAISED_FLOOR,
    ]:
        _each_563(stage)


describe('mainland death and restart states', _fn86)


def _fn92():
    def _fn93():
        expect(waterfall.owns_inventory).to_be(True)
        expect(waterfall.read_stage).to_be(read_waterfall_stage)
        expect(waterfall.decide).to_be(decide)
        expect(waterfall.food).to_be_undefined()
    test('owns its exact loadout and stage oracle', _fn93)

    def _fn94():
        expect(waterfall.sustain).to_equal(Record({'foods': [], 'eat_below_hp': 1}))
    test('names no food of its own, so the configured one is what gets eaten', _fn94)


describe('Waterfall module wiring', _fn92)
