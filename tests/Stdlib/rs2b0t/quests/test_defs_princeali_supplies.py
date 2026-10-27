"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/princeali-supplies.test.ts (MIT, see thirdparty/rs2b0t)."""
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot

def _snapshot(**fields):
    for name in ['inv', 'inv_ids', 'bank', 'bank_ids']:
        if isinstance(fields.get(name), (Record, Fake)):
            fields[name] = fields[name]._fields
    return QuestSnapshot(**fields)
from rs2004.quests.defs.princeali.areas import PA_ITEM, PA_SHOP, PA_TILE
from rs2004.quests.defs.princeali.supplies import PURSE_FLOOR, PURSE_TOP, banked, buy_item, from_bank, grab_item, has_any_pickaxe, held, owned, scan_bank, source_coins

def snap(inv_ids=None, bank_ids=None, extra=None):
    if inv_ids is None:
        inv_ids = []
    if bank_ids is None:
        bank_ids = []
    if extra is None:
        extra = Fake(**{})
    _merged1 = {}
    for _k, _v in {'journal': 'in_progress', 'inv': {}, 'inv_ids': {_k: _v for _k, _v in inv_ids}, 'worn': set(), 'worn_ids': set(), 'no_progress': 0, 'bank_coins': 0, 'bank': {}, 'bank_ids': {_k: _v for _k, _v in bank_ids}, 'bank_known': True}.items():
        _merged1[_k] = _v
    for _k, _v in (extra._fields if isinstance(extra, (Record, Fake)) else extra).items():
        _merged1[_k] = _v
    return _snapshot(**_merged1)

def _fn2():

    def _fn3():
        s = snap([[PA_ITEM.ROPE.id, 2]], [[PA_ITEM.ROPE.id, 5]])
        expect(held(s, PA_ITEM.ROPE.id)).to_be(2)
        expect(banked(s, PA_ITEM.ROPE.id)).to_be(5)
        expect(owned(s, PA_ITEM.ROPE.id)).to_be(7)
    test('held, banked and owned read the id maps', _fn3)

    def _fn4():
        s = snap([[PA_ITEM.PLAIN_WIG.id, 1]])
        expect(held(s, PA_ITEM.BLOND_WIG.id)).to_be(0)
        expect(held(s, PA_ITEM.PLAIN_WIG.id)).to_be(1)
    test('a plain wig does not count as a blond one', _fn4)

    def _fn5():
        expect(has_any_pickaxe(snap())).to_be(False)
        expect(has_any_pickaxe(snap([[1265, 1]]))).to_be(True)
        expect(has_any_pickaxe(snap([], [], Fake(**{'worn_ids': set([1271])})))).to_be(True)
    test('any pickaxe counts, held or worn', _fn5)

    def _fn6():
        expect(has_any_pickaxe(snap([], [[1265, 1]]))).to_be(False)
    test('a banked pickaxe is not a held one', _fn6)
describe('counting', _fn2)

def _fn7():

    def _fn8():
        expect(from_bank(snap([[PA_ITEM.ROPE.id, 2]]), PA_ITEM.ROPE, 2)).to_be_null()
    test('null once the pack has enough', _fn8)

    def _fn9():
        s = snap([], [], Fake(**{'bank_known': False}))
        expect(from_bank(s, PA_ITEM.ROPE, 1)).to_equal(scan_bank())
    test('scans first when the bank has never been seen', _fn9)

    def _fn10():
        step = from_bank(snap([], [[PA_ITEM.ROPE.id, 1]]), PA_ITEM.ROPE, 2)
        expect(step.kind if step is not None else None).to_be('withdraw')
        expect((step.kind if step is not None else None) == 'withdraw' and step.items).to_equal([Fake(**{'name': 'Rope', 'id': 954, 'qty': 1})])
    test('withdraws by id, capped at what the bank holds', _fn10)

    def _fn11():
        step = from_bank(snap([], [[PA_ITEM.ROPE.id, 1]]), PA_ITEM.ROPE, 1)
        expect((step.kind if step is not None else None) == 'withdraw' and step.bank).to_be_undefined()
    test('withdraw steps use the nearest bank, not a fixed one', _fn11)

    def _fn12():
        expect(from_bank(snap(), PA_ITEM.ROPE, 1)).to_be_null()
    test('null when neither pack nor bank can supply it', _fn12)
describe('fromBank', _fn7)

def _fn13():

    def _fn14():
        step = buy_item(snap([], [[PA_ITEM.TINDERBOX.id, 1]]), PA_ITEM.TINDERBOX, 1, PA_SHOP.LUMBRIDGE, 10)
        expect(step.kind if step is not None else None).to_be('withdraw')
    test('bank before shop', _fn14)

    def _fn15():
        step = buy_item(snap(), PA_ITEM.BEER, 3, PA_SHOP.LUMBRIDGE, 10)
        expect((step.kind if step is not None else None) == 'buy' and step.item).to_be('Beer')
        expect((step.kind if step is not None else None) == 'buy' and step.qty).to_be(3)
        expect((step.kind if step is not None else None) == 'buy' and step.est_gp).to_be(30)
    test('shop when the bank is empty, priced for the shortfall', _fn15)

    def _fn16():
        step = buy_item(snap([[PA_ITEM.BEER.id, 1]]), PA_ITEM.BEER, 3, PA_SHOP.LUMBRIDGE, 10)
        expect((step.kind if step is not None else None) == 'buy' and step.qty).to_be(2)
    test('only buys the shortfall', _fn16)

    def _fn17():
        expect(buy_item(snap([[PA_ITEM.BEER.id, 3]]), PA_ITEM.BEER, 3, PA_SHOP.LUMBRIDGE, 10)).to_be_null()
    test('null once satisfied', _fn17)
describe('buyItem', _fn13)

def _fn18():

    def _fn19():
        step = grab_item(snap([], [[PA_ITEM.PICKAXE.id, 1]]), PA_ITEM.PICKAXE, PA_TILE.PICKAXE_SPAWN)
        expect(step.kind if step is not None else None).to_be('withdraw')
    test('bank before the ground spawn', _fn19)

    def _fn20():
        step = grab_item(snap(), PA_ITEM.LOGS, PA_TILE.LOGS_SPAWN)
        expect((step.kind if step is not None else None) == 'grab_ground' and step.item).to_be('Logs')
        expect((step.kind if step is not None else None) == 'grab_ground' and step.wait_if_missing).to_be(True)
    test('otherwise walks to the spawn and waits for a respawn', _fn20)

    def _fn21():
        expect(grab_item(snap([[PA_ITEM.LOGS.id, 1]]), PA_ITEM.LOGS, PA_TILE.LOGS_SPAWN)).to_be_null()
    test('null once held', _fn21)
describe('grabItem', _fn18)

def _fn22():

    def _fn23():
        expect(source_coins(snap([[PA_ITEM.COINS.id, PURSE_FLOOR]]), PURSE_FLOOR, PURSE_TOP)).to_be_null()
    test('null while the purse is above the floor', _fn23)

    def _fn24():
        step = source_coins(snap([[PA_ITEM.COINS.id, 10]], [[PA_ITEM.COINS.id, 2000000]]), PURSE_FLOOR, PURSE_TOP)
        expect((step.kind if step is not None else None) == 'withdraw' and step.items).to_equal([Fake(**{'name': 'Coins', 'id': 995, 'qty': PURSE_TOP - 10})])
    test('tops up to PURSE_TOP when below the floor', _fn24)

    def _fn25():
        step = source_coins(snap([], [[PA_ITEM.COINS.id, 40]]), PURSE_FLOOR, PURSE_TOP)
        expect((step.kind if step is not None else None) == 'withdraw' and step.items).to_equal([Fake(**{'name': 'Coins', 'id': 995, 'qty': 40})])
    test('takes what the bank has when it cannot cover the top-up', _fn25)

    def _fn26():
        expect(source_coins(snap(), PURSE_FLOOR, PURSE_TOP).kind if source_coins(snap(), PURSE_FLOOR, PURSE_TOP) is not None else None).to_be('wait')
    test('an empty bank and an empty purse is an honest wait, not a loop', _fn26)

    def _fn27():
        s = snap([], [], Fake(**{'bank_known': False}))
        expect(source_coins(s, PURSE_FLOOR, PURSE_TOP)).to_equal(scan_bank())
    test('scans an unseen bank before deciding it is empty', _fn27)

    def _fn28():
        expect(PURSE_TOP - PURSE_FLOOR).to_be_greater_than(500)
    test('the floor is low enough that a shop trip does not trigger a bank trip', _fn28)
describe('sourceCoins', _fn22)
