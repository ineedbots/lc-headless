"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/knightssword-supplies.test.ts (MIT, see thirdparty/rs2b0t)."""
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot

def _snapshot(**fields):
    for name in ['inv', 'inv_ids', 'bank', 'bank_ids']:
        if isinstance(fields.get(name), (Record, Fake)):
            fields[name] = fields[name]._fields
    return QuestSnapshot(**fields)
__all__ = ['snap']
from rs2004.quests.defs.knightssword.areas import KS_ID
from rs2004.quests.defs.knightssword.supplies import COIN_LOW, ORE_PER_TRIP, iron_bars_at, kit, pickaxe_at, pie
COINS = 995
BRONZE_PICKAXE = 1265
RUNE_PICKAXE = 1275
MAX_MINING = 70

def snap(inv_ids=None, bank_ids=None, bank_known=None, tile=None):
    if inv_ids is None:
        inv_ids = []
    return _snapshot(**{'journal': 'in_progress', 'inv': {}, 'inv_ids': {_k: _v for _k, _v in [[COINS, COIN_LOW * 2]] + list(inv_ids)}, 'worn': set(), 'worn_ids': set(), 'no_progress': 0, 'bank_coins': 2000000, 'bank': {}, 'bank_ids': {_k: _v for _k, _v in (bank_ids if bank_ids is not None else [])}, 'bank_known': bank_known if bank_known is not None else True, 'tile': tile if tile is not None else Fake(**{'x': 2946, 'z': 3369, 'level': 0}), 'free_slots': 20})

def withdrawn(step):
    return [i.get('id', -1) for i in step.items] if step.kind == 'withdraw' else []

def lobsters(held):
    return Fake(**{'name': 'Lobster', 'held': held, 'target': 14, 'low': 4})

def _fn1():

    def _fn2():
        expect(kit(snap([[COINS, 3]], bank_known=False)).kind if kit(snap([[COINS, 3]], bank_known=False)) is not None else None).to_be('scan_bank')
    test('scans the bank before withdrawing anything it has not seen', _fn2)

    def _fn3():
        expect(withdrawn(kit(snap([[COINS, 3]])))).to_contain(COINS)
    test('withdraws a coin float when the pack is nearly empty', _fn3)

    def _fn4():
        expect(kit(snap([[COINS, COIN_LOW + 1]]))).to_be_null()
    test('does not re-withdraw after a small purchase', _fn4)

    def _fn5():
        step = kit(snap(), lobsters(0))
        expect(step).to_match_object(Fake(**{'kind': 'withdraw'}))
        expect(step.kind == 'withdraw' and step.items).to_contain_equal(Fake(**{'name': 'Lobster', 'qty': 14}))
    test('withdraws food up to target when the pack is short', _fn5)

    def _fn6():
        expect(kit(snap(), lobsters(14))).to_be_null()
    test('leaves a stocked pack alone', _fn6)

    def _fn7():
        expect(kit(snap(), lobsters(5))).to_be_null()
    test('does not top up on every bite eaten', _fn7)

    def _fn8():
        below = snap([], tile=Fake(**{'x': 3049, 'z': 9566, 'level': 0}))
        expect(kit(below, lobsters(0))).to_be_null()
    test('never re-banks for food from underground', _fn8)
describe('kit', _fn1)

def _fn9():

    def _fn10():
        expect(pie(snap([], bank_known=False)).kind).to_be('scan_bank')
    test('scans the bank before buying anything', _fn10)

    def _fn11():
        step = pie(snap([], bank_ids=[[KS_ID.REDBERRY_PIE, 1]]))
        expect(withdrawn(step)).to_contain(KS_ID.REDBERRY_PIE)
    test('withdraws a banked pie rather than baking one', _fn11)

    def _fn12():
        step = pie(snap([[KS_ID.POT_OF_FLOUR, 1], [KS_ID.REDBERRIES, 1], [KS_ID.BUCKET_OF_WATER, 1]]))
        expect(step).to_match_object(Fake(**{'kind': 'grab_ground', 'item': 'Pie dish'}))
    test('grabs the pie dish from the Varrock kitchen when none is held', _fn12)

    def _fn13():
        step = pie(snap([[KS_ID.BUCKET_OF_WATER, 1]], bank_ids=[[KS_ID.PIE_DISH, 1]]))
        expect(withdrawn(step)).to_contain(KS_ID.PIE_DISH)
    test('withdraws a banked pie dish instead of walking to Varrock', _fn13)

    def _fn14():
        empty = pie(snap())
        expect(empty).to_match_object(Fake(**{'kind': 'buy', 'item': 'Bucket'}))
        with_bucket = pie(snap([[KS_ID.BUCKET, 1]]))
        expect(with_bucket).to_match_object(Fake(**{'kind': 'custom', 'name': 'fill the bucket'}))
    test('does the whole water leg before leaving for Port Sarim', _fn14)

    def _fn15():
        step = pie(snap([[KS_ID.PIE_DISH, 1], [KS_ID.BUCKET_OF_WATER, 1], [KS_ID.REDBERRIES, 1]]))
        expect(step).to_match_object(Fake(**{'kind': 'buy', 'item': 'Pot of flour'}))
    test('buys flour at Wydin when the dish and water are in hand', _fn15)

    def _fn16():
        step = pie(snap([[KS_ID.PIE_DISH, 1], [KS_ID.BUCKET_OF_WATER, 1], [KS_ID.POT_OF_FLOUR, 1]]))
        expect(step).to_match_object(Fake(**{'kind': 'buy', 'item': 'Redberries'}))
    test('buys redberries when everything else is in hand', _fn16)

    def _fn17():
        step = pie(snap([[KS_ID.PIE_DISH, 1], [KS_ID.POT_OF_FLOUR, 1], [KS_ID.REDBERRIES, 1]]))
        expect(step).to_match_object(Fake(**{'kind': 'buy', 'item': 'Bucket'}))
    test('buys a bucket before trying to fill one', _fn17)

    def _fn18():
        step = pie(snap([[KS_ID.PIE_DISH, 1], [KS_ID.POT_OF_FLOUR, 1], [KS_ID.REDBERRIES, 1], [KS_ID.BUCKET, 1]]))
        expect(step).to_match_object(Fake(**{'kind': 'custom', 'name': 'fill the bucket'}))
    test('fills a held bucket at the fountain', _fn18)

    def _fn19():
        step = pie(snap([[KS_ID.PIE_DISH, 1], [KS_ID.POT_OF_FLOUR, 1], [KS_ID.REDBERRIES, 1], [KS_ID.BUCKET_OF_WATER, 1]]))
        expect(step).to_match_object(Fake(**{'kind': 'custom', 'name': 'mix pastry dough'}))
    test('mixes dough once flour and water are both held', _fn19)

    def _fn20():
        step = pie(snap([[KS_ID.PASTRY_DOUGH, 1], [KS_ID.PIE_DISH, 1], [KS_ID.REDBERRIES, 1]]))
        expect(step).to_match_object(Fake(**{'kind': 'use_on', 'product': 'Pie shell'}))
    test('makes the shell from dough and dish', _fn20)

    def _fn21():
        step = pie(snap([[KS_ID.PIE_SHELL, 1], [KS_ID.REDBERRIES, 1]]))
        expect(step).to_match_object(Fake(**{'kind': 'use_on', 'product': 'Uncooked berry pie'}))
    test('fills the shell with redberries', _fn21)

    def _fn22():
        step = pie(snap([[KS_ID.PIE_SHELL, 1]]))
        expect(step).to_match_object(Fake(**{'kind': 'buy', 'item': 'Redberries'}))
    test('buys more redberries when the shell is made but the berries are gone', _fn22)

    def _fn23():
        step = pie(snap([[KS_ID.UNCOOKED_PIE, 1]]))
        expect(step).to_match_object(Fake(**{'kind': 'custom', 'name': 'cook the redberry pie'}))
    test('cooks the uncooked pie on a range', _fn23)

    def _fn24():
        step = pie(snap([[KS_ID.BURNT_PIE, 1]]))
        expect(step).to_match_object(Fake(**{'kind': 'custom', 'name': 'empty the burnt dish'}))
    test('empties a burnt pie instead of fetching another dish', _fn24)

    def _fn25():
        expect(pie(snap([[KS_ID.REDBERRY_PIE, 1]])).kind).to_be('wait')
    test('a held pie ends the chain', _fn25)
describe('redberry pie chain', _fn9)

def _fn26():

    def _fn27():
        expect(pickaxe_at(snap([[BRONZE_PICKAXE, 1]]), MAX_MINING)).to_be_null()
    test('nothing to do when a usable one is already held', _fn27)

    def _fn28():
        _merged29 = {}
        for _k, _v in (snap()._fields if isinstance(snap(), (Record, Fake)) else {name: getattr(snap(), name) for name in QuestSnapshot.FIELDS}).items():
            _merged29[_k] = _v
        for _k, _v in {'worn_ids': set([BRONZE_PICKAXE])}.items():
            _merged29[_k] = _v
        worn = Fake(**_merged29)
        expect(pickaxe_at(worn, MAX_MINING)).to_be_null()
    test('a worn pickaxe counts as held', _fn28)

    def _fn30():
        expect(pickaxe_at(snap([], bank_known=False), MAX_MINING).kind if pickaxe_at(snap([], bank_known=False), MAX_MINING) is not None else None).to_be('scan_bank')
    test('scans an unknown bank before walking to a spawn', _fn30)

    def _fn31():
        step = pickaxe_at(snap([], bank_ids=[[BRONZE_PICKAXE, 1], [RUNE_PICKAXE, 1]]), MAX_MINING)
        expect(withdrawn(step)).to_contain(RUNE_PICKAXE)
    test('withdraws the best banked pickaxe the level allows', _fn31)

    def _fn32():
        step = pickaxe_at(snap([], bank_ids=[[RUNE_PICKAXE, 1]]), 10)
        expect(step).to_match_object(Fake(**{'kind': 'grab_ground', 'item': 'Bronze pickaxe'}))
    test('ignores a banked pickaxe the level cannot swing', _fn32)

    def _fn33():
        expect(pickaxe_at(snap(), MAX_MINING)).to_match_object(Fake(**{'kind': 'grab_ground', 'item': 'Bronze pickaxe'}))
    test('falls back to the Rimmington spawn with an empty bank', _fn33)
describe('pickaxe sourcing', _fn26)

def _fn34():

    def with_pick(extra=None):
        if extra is None:
            extra = []
        return snap([[BRONZE_PICKAXE, 1]] + list(extra))

    def _fn35():
        expect(iron_bars_at(snap([], bank_known=False), MAX_MINING, 15).kind).to_be('scan_bank')
    test('scans an unknown bank first', _fn35)

    def _fn36():
        step = iron_bars_at(snap([], bank_ids=[[KS_ID.IRON_BAR, 2]]), MAX_MINING, 15)
        expect(withdrawn(step)).to_contain(KS_ID.IRON_BAR)
    test('withdraws banked bars rather than smelting', _fn36)

    def _fn37():
        step = iron_bars_at(snap([[KS_ID.IRON_BAR, 1]], bank_ids=[[KS_ID.IRON_BAR, 5]]), MAX_MINING, 15)
        expect(step.kind == 'withdraw' and step.items[0]['qty']).to_be(1)
    test('withdraws only the shortfall', _fn37)

    def _fn38():
        expect(iron_bars_at(snap(), MAX_MINING, 15)).to_match_object(Fake(**{'kind': 'grab_ground', 'item': 'Bronze pickaxe'}))
    test('sources a pickaxe before heading for the rocks', _fn38)

    def _fn39():
        expect(iron_bars_at(with_pick(), MAX_MINING, 15)).to_match_object(Fake(**{'kind': 'mine_rock', 'rock': 'Iron', 'qty': ORE_PER_TRIP}))
    test('mines a batch of ore once a pickaxe is held', _fn39)

    def _fn40():
        step = iron_bars_at(with_pick([[KS_ID.IRON_ORE, ORE_PER_TRIP]]), MAX_MINING, 15)
        expect(step).to_match_object(Fake(**{'kind': 'custom', 'name': 'smelt iron bars'}))
    test('smelts once the whole batch is mined', _fn40)

    def _fn41():
        for ore in [1, ORE_PER_TRIP - 1]:
            expect(iron_bars_at(with_pick([[KS_ID.IRON_ORE, ore]]), MAX_MINING, 15)).to_match_object(Fake(**{'kind': 'mine_rock', 'rock': 'Iron'}))
    test('keeps mining on a part-built batch', _fn41)

    def _fn42():
        expect(iron_bars_at(with_pick([[KS_ID.IRON_BAR, 1]]), MAX_MINING, 15)).to_match_object(Fake(**{'kind': 'mine_rock'}))
    test('one bar and no ore goes back to the rocks', _fn42)

    def _fn43():
        expect(iron_bars_at(with_pick([[KS_ID.IRON_BAR, 2]]), MAX_MINING, 15).kind).to_be('wait')
    test('two bars ends the chain', _fn43)

    def _fn44():
        expect(ORE_PER_TRIP).to_be_greater_than_or_equal(8)
    test('the batch covers two bars with room to spare', _fn44)
describe('iron bar chain', _fn34)

def _fn45():

    def _fn46():
        expect(iron_bars_at(snap([[KS_ID.IRON_ORE, ORE_PER_TRIP]]), 86, 1)).to_match_object(Fake(**{'kind': 'wait', 'reason': 'Smithing 15 is required to smelt iron bars; train Smithing or obtain and bank two Iron bars'}))
    test('does not try smelting an iron batch at Smithing 1', _fn46)

    def _fn47():
        expect(iron_bars_at(snap([], bank_ids=[[KS_ID.IRON_BAR, 2]]), 10, 1)).to_match_object(Fake(**{'kind': 'withdraw', 'items': [Fake(**{'name': 'Iron bar', 'id': KS_ID.IRON_BAR, 'qty': 2})]}))
    test('withdraws banked bars at the quest Mining floor and Smithing 1', _fn47)

    def _fn48():
        expect(iron_bars_at(snap([[BRONZE_PICKAXE, 1]]), 10, 15)).to_match_object(Fake(**{'kind': 'wait', 'reason': 'Mining 15 is required to mine iron ore; train Mining or obtain and bank two Iron bars'}))
    test('does not mine iron below Mining 15', _fn48)

    def _fn49():
        expect(iron_bars_at(snap([[KS_ID.IRON_ORE, ORE_PER_TRIP]]), 10, 15)).to_match_object(Fake(**{'kind': 'custom', 'name': 'smelt iron bars'}))
    test('smelts carried ore below Mining 15 when Smithing permits it', _fn49)
describe('iron bar skill requirements', _fn45)
