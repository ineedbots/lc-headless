"""rs2b0t's test/api/ai/quests/defs/druidspirit-supplies.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestProgress, QuestSnapshot
from rs2004.quests.defs.druidspirit.areas import NS_ID, NS_STAGE
from rs2004.quests.defs.druidspirit.supplies import amulet, sickle_step

MAX_MINING = 99
MAX_SMITHING = 99
BRONZE_PICKAXE = 1265


def snap(options=None):
    if options is None:
        options = Record({})
    return QuestSnapshot(**{
        'journal': 'in_progress',
        'inv': {},
        'inv_ids': {_k: _v for _k, _v in (options.inv_ids if options.inv_ids is not None else [])},
        'worn': set(),
        'worn_ids': set((options.worn_ids if options.worn_ids is not None else [])),
        'no_progress': 0,
        'bank_coins': 2000000,
        'stage': NS_STAGE.STARTED,
        'progress': QuestProgress(NS_STAGE.STARTED, set()),
        'bank': {},
        'bank_ids': {_k: _v for _k, _v in (options.bank_ids if options.bank_ids is not None else [])},
        'bank_known': (options.bank_known if options.bank_known is not None else True),
        'tile': Record({'x': 3253, 'z': 3420, 'level': 0}),
        'free_slots': 20,
    })


def _fn1():
    def _fn2():
        expect(amulet(snap(Record({'worn_ids': [NS_ID.GHOSTSPEAK]})))).to_be_null()
    test('a worn amulet needs nothing', _fn2)

    def _fn3():
        expect(amulet(snap(Record({'inv_ids': [[NS_ID.GHOSTSPEAK, 1]]})))).to_equal(Record({'kind': 'equip', 'item': 'Ghostspeak amulet'}))
    test('a held amulet is equipped rather than fetched', _fn3)

    def _fn4():
        expect(amulet(snap(Record({'bank_ids': [[NS_ID.GHOSTSPEAK, 1]]})))).to_equal(Record({'kind': 'withdraw', 'items': [Record({'name': 'Ghostspeak amulet', 'qty': 1, 'id': NS_ID.GHOSTSPEAK})]}))
    test('a banked amulet is withdrawn before Urhney is walked to', _fn4)

    def _fn5():
        expect(amulet(snap(Record({'bank_known': False})))).to_equal(Record({'kind': 'scan_bank'}))
    test('an unread bank is scanned before concluding the amulet is gone', _fn5)

    def _fn6():
        step = amulet(snap())
        expect((step.kind if step is not None else None)).to_be('talk')
        expect((step.kind if step is not None else None) == 'talk' and step.stop.npc).to_be('Father Urhney')
    test('with no amulet anywhere, Urhney re-issues one', _fn6)


describe('nature spirit amulet', _fn1)


def _fn7():
    def _fn8():
        expect(sickle_step(snap(Record({'inv_ids': [[NS_ID.SICKLE_BLESSED, 1]]})), MAX_MINING, MAX_SMITHING)).to_be_null()
    test('a blessed sickle ends the chain', _fn8)

    def _fn9():
        expect(sickle_step(snap(Record({'inv_ids': [[NS_ID.SICKLE, 1]]})), MAX_MINING, MAX_SMITHING)).to_be_null()
    test('a plain sickle ends the chain too — the grotto blesses it', _fn9)

    def _fn10():
        expect(sickle_step(snap(Record({'bank_known': False})), MAX_MINING, MAX_SMITHING)).to_equal(Record({'kind': 'scan_bank'}))
    test('an unread bank is scanned first', _fn10)

    def _fn11():
        expect(sickle_step(snap(Record({'bank_ids': [[NS_ID.SICKLE, 1]]})), MAX_MINING, MAX_SMITHING)).to_equal(Record({'kind': 'withdraw', 'items': [Record({'name': 'Silver sickle', 'qty': 1, 'id': NS_ID.SICKLE})]}))
    test('a banked sickle beats buying a mould', _fn11)

    def _fn12():
        step = sickle_step(snap(), MAX_MINING, MAX_SMITHING)
        expect((step.kind if step is not None else None)).to_be('buy')
        expect((step.kind if step is not None else None) == 'buy' and step.shop.npc).to_be('Dommik')
    test('no mould held sends the bot to Dommik', _fn12)

    def _fn13():
        expect(sickle_step(snap(Record({'bank_ids': [[NS_ID.MOULD, 1]]})), MAX_MINING, MAX_SMITHING)).to_equal(Record({'kind': 'withdraw', 'items': [Record({'name': 'Sickle mould', 'qty': 1, 'id': NS_ID.MOULD})]}))
    test('a banked mould is withdrawn rather than bought again', _fn13)

    def _fn14():
        step = sickle_step(snap(Record({'inv_ids': [[NS_ID.MOULD, 1]]})), MAX_MINING, MAX_SMITHING)
        expect((step.kind if step is not None else None)).to_be('buy')
        expect((step.kind if step is not None else None) == 'buy' and step.shop.npc).to_be('Bob')
        expect((step.kind if step is not None else None) == 'buy' and step.item).to_be('Bronze pickaxe')
    test('a mould and no silver buys a pickaxe from Bob rather than walking to Rimmington', _fn14)

    def _fn15():
        step = sickle_step(snap(Record({'inv_ids': [[NS_ID.MOULD, 1]], 'bank_ids': [[BRONZE_PICKAXE, 1]]})), MAX_MINING, MAX_SMITHING)
        expect((step.kind if step is not None else None)).to_be('withdraw')
    test('a banked pickaxe beats buying one', _fn15)

    def _fn16():
        step = sickle_step(snap(Record({'inv_ids': [[NS_ID.MOULD, 1], [BRONZE_PICKAXE, 1]]})), MAX_MINING, MAX_SMITHING)
        expect((step.kind if step is not None else None)).to_be('mine_rock')
        expect((step.kind if step is not None else None) == 'mine_rock' and step.rock).to_be('Silver')
    test('a mould and a pickaxe mine silver', _fn16)

    def _fn17():
        step = sickle_step(snap(Record({'inv_ids': [[NS_ID.MOULD, 1], [NS_ID.SILVER_ORE, 1]]})), MAX_MINING, MAX_SMITHING)
        expect((step.kind if step is not None else None)).to_be('custom')
        expect((step.kind if step is not None else None) == 'custom' and step.name).to_be('smelt a silver bar')
    test('mould and ore smelt a bar', _fn17)

    def _fn18():
        step = sickle_step(snap(Record({'inv_ids': [[NS_ID.MOULD, 1], [NS_ID.SILVER_BAR, 1]]})), MAX_MINING, MAX_SMITHING)
        expect((step.kind if step is not None else None)).to_be('custom')
        expect((step.kind if step is not None else None) == 'custom' and step.name).to_be('cast the silver sickle')
    test('mould and bar cast the sickle', _fn18)

    def _fn19():
        expect(sickle_step(snap(Record({'inv_ids': [[NS_ID.MOULD, 1]], 'bank_ids': [[NS_ID.SILVER_BAR, 1]]})), MAX_MINING, MAX_SMITHING)).to_equal(Record({'kind': 'withdraw', 'items': [Record({'name': 'Silver bar', 'qty': 1, 'id': NS_ID.SILVER_BAR})]}))
    test('a banked bar is withdrawn rather than mined for', _fn19)


describe('nature spirit sickle chain', _fn7)
