"""rs2b0t's test/api/ai/quests/defs/mortton.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestProgress, QuestSnapshot
from rs2004.quests.defs import QUEST_DEFS
from rs2004.quests.defs.mortton import decide, mortton
from rs2004.quests.defs.mortton.areas import SM_ID, SM_STAGE
from rs2004.quests.defs.mortton.journal import SM_FLAG
from rs2004.quests.defs.mortton.supplies import FOOD_TARGET
from rs2004.quests.defs.mortton.town import BUILD_SETS, PASTE_PER_SET, builders_order, general_order, sets_that_fit
from rs2004.quests.food import quest_food

MORTTON = Record({'x': 3490, 'z': 3290, 'level': 0})
FOOD = (quest_food.name if quest_food.name is not None else 'Trout')


def snap(options=None):
    """Coins, food, a tinderbox, the ashes and the pyre log, everything the approach kit asks for."""
    if options is None:
        options = Record({})
    stage = (options.stage if options.stage is not None else SM_STAGE.NOT_STARTED)
    inv = {_k: _v for _k, _v in [[FOOD.lower(), (options.food if options.food is not None else 6)]]}
    return QuestSnapshot(**{
        'journal': (options.journal if options.journal is not None else (('not_started' if stage == SM_STAGE.NOT_STARTED else 'in_progress'))),
        'inv': inv,
        'inv_ids': {_k: _v for _k, _v in [[SM_ID.COINS, 30000], [SM_ID.TINDERBOX, 1], [SM_ID.ASHES, 2], [SM_ID.LOGS, 1]] + list(((options.inv_ids if options.inv_ids is not None else [])))},
        'worn': set(),
        'worn_ids': set(),
        'no_progress': 0,
        'bank_coins': 2000000,
        'stage': stage,
        'progress': QuestProgress(stage, set((options.flags if options.flags is not None else []))),
        'bank': {_k: _v for _k, _v in [['coins', 2000000], [FOOD.lower(), 100]]},
        'bank_ids': {_k: _v for _k, _v in (options.bank_ids if options.bank_ids is not None else [])},
        'bank_known': True,
        'tile': MORTTON,
        'free_slots': 14,
    })


def step(options=None):
    if options is None:
        options = Record({})
    return decide(snap(options))


def named(s):
    return ((s.name if s.kind == 'custom' else s.kind))


SERUMS = [[SM_ID.SERUM3, 2]]


def _fn1():
    def _fn2():
        expect(step(Record({'journal': 'unknown'}))).to_equal(Record({'kind': 'wait', 'reason': 'quest journal not loaded'}))
    test('an unloaded journal waits rather than restarting the quest', _fn2)

    def _fn3():
        expect(step(Record({'journal': 'complete', 'stage': SM_STAGE.COMPLETE}))).to_equal(Record({'kind': 'done'}))
    test('a complete journal is done', _fn3)

    def _fn4():
        s = decide(snap(Record({'journal': 'in_progress'})).with_fields({'stage': None, 'progress': None}))
        expect(s).to_equal(Record({'kind': 'wait', 'reason': 'quest stage not readable'}))
    test('an unreadable stage waits', _fn4)

    def _fn6():
        expect(named(step())).to_be("take Herbi Flax's diary")
        expect(named(step(Record({'inv_ids': [[SM_ID.DIARY, 1]]})))).to_be("read Herbi Flax's diary")
    test('the diary is taken before it is read', _fn6)


describe('shades of mortton decide', _fn1)


def _fn7():
    def _fn8():
        expect(step(Record({
        'stage': SM_STAGE.KILL_SHADES,
        'inv_ids': [[SM_ID.ASHES, 0], [SM_ID.LOGS, 0]],
        'bank_ids': [[SM_ID.SERUM2, 1], [SM_ID.SERUM3, 1], [SM_ID.UNID_TARROMIN, 37]],
    }))).to_equal(Record({'kind': 'withdraw', 'items': [Record({'name': 'Serum 207 (3)', 'id': SM_ID.SERUM3, 'qty': 1})]}))
    test('a resumed shade hunt recovers banked serum before burning or searching for herbs', _fn8)

    def _fn9():
        expect(decide(snap(Record({'stage': SM_STAGE.KILL_SHADES})).with_fields({'bank_known': False})).kind).to_be('scan_bank')
    test('a missing serum checks an unread bank before reusing the one-shot herb table', _fn9)

    def _fn11():
        expect(step(Record({'stage': SM_STAGE.KILL_SHADES, 'bank_ids': [[SM_ID.UNID_TARROMIN, 37]]}))).to_equal(Record({'kind': 'withdraw', 'items': [Record({'name': 'Herb', 'id': SM_ID.UNID_TARROMIN, 'qty': 1})]}))
    test('banked tarromin replaces the herbs from an exhausted table', _fn11)

    def _fn12():
        expect(named(step(Record({
        'stage': SM_STAGE.KILL_SHADES,
        'inv_ids': [[SM_ID.TARROMIN_UNF, 1]],
        'bank_ids': [[SM_ID.UNID_TARROMIN, 37]],
    })))).to_be('mix serum 207')
    test('a carried unfinished potion is brewed before fetching another banked herb', _fn12)

    def _fn13():
        expect(step(Record({'stage': SM_STAGE.LIT_PYRE, 'bank_ids': [[SM_ID.SERUM_PERM1, 1]]}))).to_equal(Record({'kind': 'withdraw', 'items': [Record({'name': 'Serum 207(p) (1)', 'id': SM_ID.SERUM_PERM1, 'qty': 1})]}))
    test('banked permanent serum also covers the remaining conversations', _fn13)

    def _fn14():
        expect(step(Record({'stage': SM_STAGE.READ_DIARY, 'bank_ids': [[SM_ID.SERUM4, 1], [SM_ID.UNID_TARROMIN, 37]]}))).to_equal(Record({'kind': 'withdraw', 'items': [Record({'name': 'Herb', 'id': SM_ID.UNID_TARROMIN, 'qty': 1})]}))
    test('a character that has never brewed serum still has to make its own', _fn14)

    def _fn15():
        full = snap(Record({'stage': SM_STAGE.KILL_SHADES, 'bank_ids': [[SM_ID.SERUM3, 1]]}))
        full.free_slots = 0
        full.inv = {_k: _v for _k, _v in [['logs', 28]]}
        full.inv_ids = {_k: _v for _k, _v in [[SM_ID.LOGS, 28]]}
        action = decide(full)
        expect(action.kind).to_be('deposit')
        if action.kind == 'deposit':
            expect(any([(name in 'logs') for name in action.keep])).to_be(False)
            expect((action.keep_ids if action.keep_ids is not None else [])).not_.to_contain(SM_ID.LOGS)
    test('a pack full of surplus logs makes room for the banked serum', _fn15)

    def _fn16():
        full = snap(Record({
        'stage': SM_STAGE.CREATED_PYRE_LOGS,
        'inv_ids': [[SM_ID.PYRE_LOGS, 1], [SM_ID.REMAINS, 2]],
        'bank_ids': [[SM_ID.SERUM1, 1]],
    }))
        full.free_slots = 0
        action = decide(full)
        expect(action.kind).to_be('deposit')
        if action.kind == 'deposit':
            for name in ['pyre logs', 'loar remains', 'sacred oil(2)', 'olive oil(3)']:
                expect(any([(keep in name) for keep in action.keep])).to_be(True)
    test('making room late in the quest preserves the prepared pyre and remains', _fn16)

    def _fn17():
        full = snap(Record({'stage': SM_STAGE.KILL_SHADES, 'bank_ids': [[SM_ID.SERUM3, 1]]}))
        full.free_slots = 0
        full.inv = {_k: _v for _k, _v in [['loar remains', 28]]}
        full.inv_ids = {_k: _v for _k, _v in [[SM_ID.REMAINS, 28]]}
        expect(decide(full)).to_equal(Record({'kind': 'wait', 'reason': 'no pack room for serum recovery'}))
    test('a full pack containing only protected items does not repeat an ineffective deposit', _fn17)

    def _fn18():
        expect(named(step(Record({'stage': SM_STAGE.READ_DIARY})))).to_be('search the smashed table for herbs')
    test('a started quest with no herb searches the smashed table', _fn18)

    def _fn19():
        s = step(Record({'stage': SM_STAGE.READ_DIARY, 'inv_ids': [[SM_ID.UNID_TARROMIN, 2]]}))
        expect(named(s)).to_be('identify the tarromin')
    test('an unidentified herb is identified', _fn19)

    def _fn20():
        s = step(Record({'stage': SM_STAGE.READ_DIARY, 'inv_ids': [[SM_ID.TARROMIN, 1]]}))
        expect(named(s)).to_be('take an empty vial')
    test('a clean tarromin with no glass fetches an empty vial', _fn20)

    def _fn21():
        s = step(Record({'stage': SM_STAGE.READ_DIARY, 'inv_ids': [[SM_ID.TARROMIN, 1], [SM_ID.VIAL_EMPTY, 1]]}))
        expect(named(s)).to_be('fill a vial at the sink')
    test('an empty vial is filled at the sink', _fn21)

    def _fn22():
        s = step(Record({'stage': SM_STAGE.READ_DIARY, 'inv_ids': [[SM_ID.TARROMIN, 1], [SM_ID.VIAL_WATER, 1]]}))
        expect(named(s)).to_be('mix the unfinished potion')
    test('a herb and water make the unfinished potion', _fn22)

    def _fn23():
        s = step(Record({'stage': SM_STAGE.READ_DIARY, 'inv_ids': [[SM_ID.TARROMIN_UNF, 1]]}))
        expect(named(s)).to_be('mix serum 207')
    test('the unfinished potion takes the ashes', _fn23)

    def _fn24():
        expect(named(step(Record({'stage': SM_STAGE.MADE_SERUM, 'inv_ids': SERUMS})))).to_be('talk to Razmire')
    test('two vials of serum are enough for the whole quest, so the chain stops', _fn24)

    def _fn25():
        s = step(Record({'stage': SM_STAGE.SHADES_TO_ULSQUIRE, 'inv_ids': [[SM_ID.SERUM2, 1]]}))
        expect(named(s)).to_be('talk to Ulsquire')
    test('one vial past the shade hunt still covers what is left', _fn25)


describe('the serum chain', _fn7)


def _fn26():
    def _fn27():
        bare = snap()
        bare.inv_ids = {}
        bare.bank_known = False
        expect(decide(bare).kind).to_be('scan_bank')
    test('an empty pack scans the bank before anything else', _fn27)

    def _fn28():
        bare = snap()
        bare.inv_ids = {_k: _v for _k, _v in [[SM_ID.COINS, 30000], [SM_ID.ASHES, 2], [SM_ID.LOGS, 1]]}
        s = decide(bare)
        expect(s.kind).to_be('buy')
        expect(s.kind == 'buy' and s.item).to_be('Tinderbox')
    test('a missing tinderbox with an empty bank is bought in Varrock', _fn28)

    def _fn29():
        bare = snap(Record({'bank_ids': [[SM_ID.TINDERBOX, 1]]}))
        bare.inv_ids = {_k: _v for _k, _v in [[SM_ID.COINS, 30000], [SM_ID.ASHES, 2], [SM_ID.LOGS, 1]]}
        s = decide(bare)
        expect(s.kind).to_be('withdraw')
    test('a banked tinderbox is withdrawn rather than bought', _fn29)

    def _fn30():
        bare = snap()
        bare.bank = {_k: _v for _k, _v in [['coins', 2000000], ['rune scimitar', 1], ['rune chainbody', 1]]}
        s = decide(bare)
        expect(s.kind).to_be('withdraw')
        expect(s.kind == 'withdraw' and [i['name'] for i in s.items]).to_equal(['Rune scimitar', 'Rune chainbody'])
    test('a banked melee kit is drawn before the swamp crossing', _fn30)

    def _fn31():
        bare = snap()
        bare.inv = {_k: _v for _k, _v in [[FOOD.lower(), 6], ['rune scimitar', 1]]}
        bare.bank = {_k: _v for _k, _v in [['coins', 2000000], ['rune scimitar', 1]]}
        expect(named(decide(bare))).to_be('wear Rune scimitar')
    test('a carried kit is worn rather than withdrawn again', _fn31)

    def _fn32():
        bare = snap()
        bare.inv_ids = {_k: _v for _k, _v in [[SM_ID.COINS, 30000], [SM_ID.TINDERBOX, 1], [SM_ID.LOGS, 1]]}
        expect(named(decide(bare))).to_be('burn logs for ashes')
    test('no ashes means a trip to the Varrock logs', _fn32)

    def _fn33():
        bare = snap(Record({'inv_ids': [[SM_ID.PYRE_LOGS, 1]], 'stage': SM_STAGE.CREATED_PYRE_LOGS}))
        bare.inv_ids = {_k: _v for _k, _v in [[SM_ID.COINS, 30000], [SM_ID.TINDERBOX, 1], [SM_ID.PYRE_LOGS, 1], [SM_ID.SERUM3, 1]]}
        expect(named(decide(bare))).to_be('stack the pyre logs')
    test('pyre logs in the pack retire the spare log', _fn33)


describe('sourcing', _fn26)


def hunts_at(stage):
    def body():
        expect(named(step(Record({'stage': stage, 'inv_ids': SERUMS})))).to_be('hunt a Loar Shade')
    return body


def _fn34():
    for stage in [SM_STAGE.KILL_SHADES, SM_STAGE.KILLED_1, SM_STAGE.KILLED_4]:
        test(f'stage {stage} hunts', hunts_at(stage))

    def _fn36():
        s = step(Record({'stage': SM_STAGE.KILLED_5, 'inv_ids': list(SERUMS) + [[SM_ID.REMAINS, 4]]}))
        expect(named(s)).to_be('hunt a Loar Shade')
    test('the fifth kill still hunts while the pack is short of remains', _fn36)

    def _fn37():
        s = step(Record({'stage': SM_STAGE.KILLED_5, 'inv_ids': list(SERUMS) + [[SM_ID.REMAINS, 5]]}))
        expect(named(s)).to_be('hand Razmire the remains and stock up')
    test('five sets of remains go to Razmire with the shopping list', _fn37)


describe('the shade hunt', _fn34)


def _fn38():
    stocked = [
        [SM_ID.HAMMER, 1],
        [SM_ID.OLIVE_OIL3, 1],
        [SM_ID.PLANK, 5],
        [SM_ID.LIMESTONE_BRICK, 5],
        [SM_ID.SWAMP_PASTE, 30],
    ]

    # Why: the oil has nowhere to land beside eleven slots of plank, brick and paste, so it waits for the rebuild to spend them.
    def _fn39():
        s = step(Record({'stage': SM_STAGE.SHADES_TO_RAZMIRE, 'inv_ids': list(SERUMS) + [[SM_ID.HAMMER, 1], [SM_ID.REMAINS, 3]]}))
        expect(named(s)).to_be('buy temple materials from Razmire')
    test('the handover trip buys building material and leaves the oil for later', _fn39)

    def _fn40():
        s = step(Record({'stage': SM_STAGE.SHADES_TO_RAZMIRE, 'inv_ids': list(SERUMS) + list(stocked) + [[SM_ID.REMAINS, 3]]}))
        expect(named(s)).to_be('talk to Ulsquire')
    test('a stocked pack past the handover shows the remains to Ulsquire', _fn40)

    def _fn41():
        s = step(Record({'stage': SM_STAGE.ULSQUIRE_TEMPLE, 'inv_ids': list(SERUMS) + [[SM_ID.OLIVE_OIL3, 1]]}))
        expect(named(s)).to_be("buy from Razmire's general store")
    test('a missing hammer sends the bot to the general counter', _fn41)

    def _fn42():
        s = step(Record({'stage': SM_STAGE.ULSQUIRE_TEMPLE, 'inv_ids': list(SERUMS) + [[SM_ID.HAMMER, 1], [SM_ID.OLIVE_OIL3, 1]]}))
        expect(named(s)).to_be('buy temple materials from Razmire')
    test('an empty material pool sends the bot to the builders counter', _fn42)

    def _fn43():
        s = step(Record({
        'stage': SM_STAGE.REBUILD_TEMPLE,
        'inv_ids': list(SERUMS) + [[SM_ID.HAMMER, 1], [SM_ID.OLIVE_OIL3, 1]],
        'flags': [f'{SM_FLAG.RESOURCES}:40'],
    }))
        expect(named(s)).to_be('rebuild the Flamtaer temple')
    test('a pool that still has resources builds without shopping', _fn43)

    def _fn44():
        s = step(Record({'stage': SM_STAGE.ULSQUIRE_TEMPLE, 'inv_ids': list(SERUMS) + list(stocked)}))
        expect(named(s)).to_be('rebuild the Flamtaer temple')
    test('carried materials build without shopping', _fn44)

    def _fn45():
        s = step(Record({'stage': SM_STAGE.CAN_LIGHT_ALTAR, 'inv_ids': list(SERUMS) + list(stocked)}))
        expect(named(s)).to_be('light the altar and sanctify the oil')
    test('the rebuilt temple lights the altar', _fn45)

    def _fn46():
        s = step(Record({'stage': SM_STAGE.CAN_LIGHT_ALTAR, 'inv_ids': SERUMS}))
        expect(named(s)).to_be("buy from Razmire's general store")
    test('an altar with nothing to sanctify buys oil first, and the hammer is no longer wanted', _fn46)

    def _fn47():
        s = step(Record({
        'stage': SM_STAGE.CAN_LIGHT_ALTAR,
        'inv_ids': list(SERUMS) + [[SM_ID.PYRE_LOGS, 1]],
        'flags': [f'{SM_FLAG.SANCTITY}:40', f'{SM_FLAG.REPAIRED}:100'],
    }))
        expect(named(s)).to_be('light the altar and sanctify the oil')
    test('pyre logs already made count as oil, so the altar leg runs', _fn47)

    # Why: sanctity is a player varp, so a temple another run left finished still owes this character a load of material before the flame answers.
    def _fn48():
        s = step(Record({'stage': SM_STAGE.CAN_LIGHT_ALTAR, 'inv_ids': list(SERUMS) + [[SM_ID.HAMMER, 1], [SM_ID.OLIVE_OIL3, 1]]}))
        expect(named(s)).to_be('buy temple materials from Razmire')
    test('a rebuilt temple with no sanctity of its own buys material first', _fn48)


describe('the temple', _fn38)


def _fn49():
    late = [[SM_ID.SERUM3, 1], [SM_ID.REMAINS, 2], [SM_ID.HAMMER, 1]]
    sanctified = [f'{SM_FLAG.SANCTITY}:40', f'{SM_FLAG.REPAIRED}:100']

    def _fn50():
        s = step(Record({
        'stage': SM_STAGE.CREATED_SACRED_OIL,
        'inv_ids': list(late) + [[SM_ID.SACRED_OIL3, 1]],
        'flags': sanctified,
    }))
        expect(named(s)).to_be('soak the logs in sacred oil')
    test('sacred oil goes onto the logs', _fn50)

    def _fn51():
        s = step(Record({
        'stage': SM_STAGE.CREATED_SACRED_OIL,
        'inv_ids': list(late) + [[SM_ID.OLIVE_OIL3, 1]],
        'flags': sanctified,
    }))
        expect(named(s)).to_be('sanctify more oil in the flame')
    test('a sacred-oil stage with no oil left goes back to the flame', _fn51)

    def _fn52():
        s = step(Record({'stage': SM_STAGE.CREATED_PYRE_LOGS, 'inv_ids': list(late) + [[SM_ID.PYRE_LOGS, 1]]}))
        expect(named(s)).to_be('stack the pyre logs')
    test('pyre logs are stacked', _fn52)

    def _fn53():
        s = step(Record({'stage': SM_STAGE.LOGS_ON_PYRE, 'inv_ids': late}))
        expect(named(s)).to_be('cremate the shade')
    test('a stacked pyre takes the remains and the flame', _fn53)

    def _fn54():
        s = step(Record({'stage': SM_STAGE.LIT_PYRE, 'inv_ids': late}))
        expect(named(s)).to_be('talk to Ulsquire')
    test('a lit pyre is reported to Ulsquire', _fn54)


describe('the cremation', _fn49)


def _fn55():
    def _fn56():
        expect([[i.name, i.qty] for i in builders_order().items]).to_equal([['Swamp paste', BUILD_SETS * PASTE_PER_SET], ['Plank', BUILD_SETS], ['Limestone brick', BUILD_SETS]])
        # Paste is one stack whatever the count, so the order carries more than the five-per-set the build spends.
        expect(PASTE_PER_SET).to_be_greater_than_or_equal(5)
    test('the builders order is five sets of material', _fn56)

    # Why: eleven slots is what five sets need, and a pack with less room buys fewer sets rather than parking on a refusal.
    def _fn57():
        expect(sets_that_fit(14)).to_be(BUILD_SETS)
        expect(sets_that_fit(11)).to_be(5)
        expect(sets_that_fit(9)).to_be(4)
        expect(sets_that_fit(3)).to_be(1)
        expect(sets_that_fit(2)).to_be(0)
        expect([i.qty for i in builders_order(2).items]).to_equal([2 * PASTE_PER_SET, 2, 2])
    test('the order shrinks to the room the pack has', _fn57)

    def _fn58():
        expect(builders_order().asks).to_contain('I keep running out of building materials')
        expect(builders_order().asks).to_contain('Can I see the building store')
        expect(general_order(True, True).asks).to_contain('Can you open a store for me')
        expect(general_order(True, True).asks).to_contain('Can I see the general store')
    test('each counter is named by a line from both shapes of Razmire menu', _fn58)

    # Why: Morytania has no bank to trim against, so the stage-45 pack has to hold every purchase at once.
    def _fn59():
        carried = 1 + 1 + 2 + 3 + 1 + FOOD_TARGET
        shopped = 1 + 1 + 2 * BUILD_SETS
        expect(carried + shopped).to_be_less_than_or_equal(28)
    test('the stage-45 loadout and both counters fit one pack', _fn59)


describe('the shopping list', _fn55)


def _fn60():
    def _fn61():
        ids = [d.record.id for d in QUEST_DEFS]
        expect(ids).to_contain('mortton')
        expect((ids.index('mortton') if 'mortton' in ids else -1)).to_be_greater_than((ids.index('druidspirit') if 'druidspirit' in ids else -1))
    test('the module is registered after Nature Spirit', _fn61)

    def _fn62():
        expect(mortton.record.quest_points).to_be(3)
        expect(mortton.record.requirements.quests).to_equal(['priestperil'])
        expect(mortton.record.requirements.skills).to_equal([
        Record({'skill': 'crafting', 'level': 20}),
        Record({'skill': 'herblore', 'level': 15}),
        Record({'skill': 'firemaking', 'level': 5}),
    ])
    test('the record carries the official gates', _fn62)

    def _fn63():
        expect(mortton.owns_inventory).to_be(True)
        expect(type(mortton.read_progress).__name__).to_be('function')
        expect((mortton.sustain.foods if mortton.sustain is not None else None)).to_contain('Lobster')
    test('the module owns its own loadout and reads its own progress', _fn63)


describe('module wiring', _fn60)
