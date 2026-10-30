"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/sheepherder.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.defs.sheepherder import decide, sheepherder
from rs2004.quests.defs.sheepherder.areas import BONES_OBJ, FEED_OBJ, JACKET, JACKET_OBJ, PROD_OBJ, TROUSERS, TROUSERS_OBJ
from rs2004.quests.defs.sheepherder.journal import SH_STAGE
from rs2004.geometry import Tile
from rs2004.quests.engine.types import QuestSnapshot

DRESSED = [JACKET_OBJ, TROUSERS_OBJ, PROD_OBJ]


def snap(options=None):
    if options is None:
        options = Record({})
    progress = (options.progress if 'progress' in options._fields else Record({
        'stage': (options.stage if options.stage is not None else SH_STAGE.DISPOSING),
        'flags': set((options.flags if options.flags is not None else [])),
    }))
    inv_ids = {}
    for id in (options.inv_ids if options.inv_ids is not None else [FEED_OBJ]):
        _v1 = inv_ids.get(id)
        inv_ids[id] = ((_v1 if _v1 is not None else 0)) + 1
    return QuestSnapshot(**{
        'journal': (options.journal if options.journal is not None else 'in_progress'),
        'inv': {_k: _v for _k, _v in (options.inv if options.inv is not None else [['coins', 1000]])},
        'inv_ids': inv_ids,
        'worn': set(),
        'worn_ids': set((options.worn_ids if options.worn_ids is not None else DRESSED)),
        'no_progress': 0,
        'bank_coins': 2000000,
        'stage': (progress.stage if progress is not None else None),
        'progress': progress,
        'bank': {},
        'bank_known': True,
        'free_slots': 24,
    })


def custom_name(step):
    return ((step.name if step.kind == 'custom' else None))


def talk_to(step):
    return ((step.stop.npc if step.kind == 'talk' else None))


def _fn2():
    def _fn3():
        expect(decide(snap(Record({'journal': 'unknown'}))).kind).to_be('wait')
    test('waits while the quest list is still loading', _fn3)

    def _fn4():
        expect(decide(snap(Record({'journal': 'complete'}))).kind).to_be('done')
    test('is done once the quest list turns green', _fn4)

    def _fn5():
        expect(talk_to(decide(snap(Record({'journal': 'not_started'}))))).to_be('Councillor Halgrive')
    test('opens with Councillor Halgrive', _fn5)

    def _fn6():
        expect(decide(snap(Record({'progress': None}))).kind).to_be('wait')
    test('waits rather than guessing when the journal stage is unavailable', _fn6)

    def _fn7():
        expect(talk_to(decide(snap(Record({'stage': SH_STAGE.NEED_SUIT}))))).to_be('Doctor Orbon')
    test('buys the suit from Doctor Orbon once the quest is started', _fn7)

    def _fn8():
        step = decide(snap(Record({'stage': SH_STAGE.NEED_SUIT, 'inv': []})))
        expect(step.kind).to_be('withdraw')
    test('fetches coins before walking to Orbon with an empty purse', _fn8)

    def _fn9():
        step = decide(snap(Record({'worn_ids': [PROD_OBJ], 'inv_ids': [FEED_OBJ, JACKET_OBJ, TROUSERS_OBJ]})))
        expect(step).to_equal(Record({'kind': 'equip', 'item': JACKET}))
    test('wears a suit it is carrying rather than buying another', _fn9)

    def _fn10():
        expect(talk_to(decide(snap(Record({'worn_ids': [JACKET_OBJ, PROD_OBJ]}))))).to_be('Doctor Orbon')
    test('goes back to Orbon when a half of the suit is gone entirely', _fn10)

    def _fn11():
        step = decide(snap(Record({'worn_ids': [JACKET_OBJ, PROD_OBJ], 'inv_ids': [FEED_OBJ, TROUSERS_OBJ]})))
        expect(step).to_equal(Record({'kind': 'equip', 'item': TROUSERS}))
    test('equips the trousers when only they are missing', _fn11)

    def _fn12():
        expect(custom_name(decide(snap(Record({'worn_ids': [JACKET_OBJ, TROUSERS_OBJ]}))))).to_be('fetch the Prod from the barn')
    test('fetches the prod from the barn before herding', _fn12)

    def _fn13():
        expect(talk_to(decide(snap(Record({'inv_ids': []}))))).to_be('Councillor Halgrive')
    test('asks Halgrive for more feed when the pack has none', _fn13)

    def _fn14():
        expect(custom_name(decide(snap(Record({'flags': ['burnt-1']}))))).to_be('herd and kill sheep 2')
    test('herds the first sheep that has not been burnt', _fn14)

    def _fn15():
        step = decide(snap(Record({'flags': ['burnt-1'], 'inv_ids': [FEED_OBJ, BONES_OBJ[2]]})))
        expect(custom_name(step)).to_be('incinerate the remains of sheep 2')
    test('burns the remains it is carrying before herding anything else', _fn15)

    def _fn16():
        step = decide(snap(Record({'flags': ['burnt-1', 'burnt-2'], 'inv_ids': [FEED_OBJ, BONES_OBJ[3]]})))
        expect(custom_name(step)).to_be('incinerate the remains of sheep 3')
    test('tells the four sets of remains apart by id, since all four render "Bones"', _fn16)

    def _fn17():
        step = decide(snap(Record({'worn_ids': [JACKET_OBJ, TROUSERS_OBJ], 'inv_ids': [BONES_OBJ[1]]})))
        expect(custom_name(step)).to_be('incinerate the remains of sheep 1')
    test('burns held remains with no prod worn, since only the suit gates the enclosure', _fn17)

    def _fn18():
        step = decide(snap(Record({'worn_ids': [PROD_OBJ], 'inv_ids': [BONES_OBJ[1], JACKET_OBJ, TROUSERS_OBJ]})))
        expect(step).to_equal(Record({'kind': 'equip', 'item': JACKET}))
    test('dresses before burning, since the incinerator stands inside the enclosure', _fn18)

    def _fn19():
        step = decide(snap(Record({'flags': ['burnt-1', 'burnt-2', 'burnt-3', 'burnt-4']})))
        expect(talk_to(step)).to_be('Councillor Halgrive')
    test('returns to Halgrive once all four are incinerated', _fn19)

    def _fn20():
        expect(custom_name(decide(snap(Record({'flags': ['herded-1', 'killed-1']}))))).to_be('herd and kill sheep 1')
    test('re-herds a sheep the journal calls penned but whose remains are gone', _fn20)


describe('Sheep Herder decide', _fn2)


def _fn21():
    def _fn22():
        expect(sheepherder.record.items).to_equal([])
    test('requires nothing up front — the suit, prod and feed all come from the quest', _fn22)

    def _fn23():
        for tool in ['coins', 'prod', 'feed', 'plague jacket', 'plague trousers', 'bones']:
            expect(sheepherder.tools).to_contain(tool)
    test('keeps the coin float and every quest item off the deposit list', _fn23)

    def _fn24():
        expect([sheepherder.bank.x, sheepherder.bank.z, sheepherder.bank.level]).to_equal([2616, 3332, 0])
    test('banks at Ardougne West, the booth nearest both the chapel and the enclosure', _fn24)


describe('Sheep Herder module', _fn21)
