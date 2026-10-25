"""rs2b0t's test/api/ai/quests/engine/provisioning.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""


from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot
from rs2004.quests.engine.provisioning import coin_float_withdraw, coin_float_plan, deposit_plan, float_withdraw, gp_short, plan_provisioning, float_draw_plan, should_freshen_pack, buy_purse_top_up, COIN_FLOAT

def it(name, qty, kind):
    return (Record({'name': name, 'qty': qty, 'kind': kind}))


def _fn1():
    def _fn2():
        p = plan_provisioning([it('Egg', 1, 'acquirable')], {_k: _v for _k, _v in [['egg', 1]]}, {})
        expect(p.satisfied).to_be(True)
        expect(p.withdraw).to_equal([])
        expect(p.gather).to_equal([])
        expect(p.blocked).to_equal([])
    test('pack already satisfied -> nothing to do', _fn2)

    def _fn3():
        p = plan_provisioning([it('Clay', 6, 'acquirable')], {}, {_k: _v for _k, _v in [['clay', 10]]})
        expect(p.withdraw).to_equal([Record({'name': 'Clay', 'qty': 6})])
        expect(p.gather).to_equal([])
        expect(p.satisfied).to_be(False)
    test('bank-first: banked items are withdrawn, not gathered', _fn3)

    def _fn4():
        p = plan_provisioning([it('Clay', 6, 'acquirable')], {_k: _v for _k, _v in [['clay', 1]]}, {_k: _v for _k, _v in [['clay', 2]]})
        expect(p.withdraw).to_equal([Record({'name': 'Clay', 'qty': 2})])
        expect(p.gather).to_equal([Record({'name': 'Clay', 'need': 3})])
    test('partial bank tops up from gather', _fn4)

    def _fn5():
        p = plan_provisioning([it('Redberry pie', 1, 'mustHave'), it('Cadava berries', 1, 'acquirable')], {}, {})
        expect(p.blocked).to_equal(['Redberry pie x1'])
        expect(p.gather).to_equal([Record({'name': 'Cadava berries', 'need': 1})])
    test('mustHave that bank cannot cover blocks; acquirable does not', _fn5)

    def _fn6():
        p = plan_provisioning([it('Ball of wool', 20, 'acquirable')], {_k: _v for _k, _v in [['ball of wool', 20]]}, {})
        expect(p.satisfied).to_be(True)
    test('name matching is case-insensitive against the lowercased maps', _fn6)


describe('planProvisioning', _fn1)


def _fn7():
    def inv(names):
        return {_k: _v for _k, _v in [[n, 1] for n in names]}

    def _fn8():
        out = deposit_plan(inv(['bronze pickaxe', 'logs', 'coins', 'clay']), ['pickaxe', 'clay'])
        expect(out).to_equal(['logs', 'coins'])
    test('keeps substring matches, deposits the rest', _fn8)

    def _fn9():
        expect(deposit_plan(inv(['shears', 'wool']), ['shears', 'wool'])).to_equal([])
    test('clean pack -> nothing to deposit', _fn9)

    def _fn10():
        expect(deposit_plan(inv(['cadava berries', 'cadava potion', 'egg']), ['cadava'])).to_equal(['egg'])
    test('substring keep covers derived forms (cadava berries + cadava potion)', _fn10)


describe('depositPlan', _fn7)


def _fn11():
    def snap_with(pack_coins, bank_coins):
        return QuestSnapshot(inv={_k: _v for _k, _v in ([['coins', pack_coins]] if pack_coins > 0 else [])}, bank_coins=bank_coins)

    def _fn12():
        expect(gp_short(snap_with(100, 0), 100)).to_be(0)
        expect(gp_short(snap_with(40, 60), 100)).to_be(0)
    test('pack + bank covers -> 0', _fn12)

    def _fn13():
        expect(gp_short(snap_with(0, 0), 150)).to_be(150)
        expect(gp_short(snap_with(30, 20), 150)).to_be(100)
    test('short -> the exact shortfall', _fn13)


describe('gpShort', _fn11)


def _fn14():
    def pack_bank(pack, bank):
        return [
            {_k: _v for _k, _v in ([['coins', pack]] if pack > 0 else [])},
            {_k: _v for _k, _v in ([['coins', bank]] if bank > 0 else [])},
        ]

    def _fn15():
        inv, bank = pack_bank(0, 5000)
        expect(coin_float_withdraw(inv, bank, 1000)).to_equal(Record({'name': 'Coins', 'qty': 1000}))
    test('empty pack, bank covers -> withdraw the full float', _fn15)

    def _fn16():
        inv, bank = pack_bank(300, 5000)
        expect(coin_float_withdraw(inv, bank, 1000)).to_equal(Record({'name': 'Coins', 'qty': 700}))
    test('partial pack -> tops up to the float', _fn16)

    def _fn17():
        inv, bank = pack_bank(1000, 5000)
        expect(coin_float_withdraw(inv, bank, 1000)).to_be_null()
        inv, bank = pack_bank(1500, 5000)
        expect(coin_float_withdraw(inv, bank, 1000)).to_be_null()
    test('pack already at/over the float -> null', _fn17)

    def _fn18():
        inv, bank = pack_bank(0, 250)
        expect(coin_float_withdraw(inv, bank, 1000)).to_equal(Record({'name': 'Coins', 'qty': 250}))
    test('bank short -> withdraw only what the bank holds (drains in one trip)', _fn18)

    def _fn19():
        inv, bank = pack_bank(300, 0)
        expect(coin_float_withdraw(inv, bank, 1000)).to_be_null()
    test('bank dry -> null (no re-withdraw loop)', _fn19)


describe('coinFloatWithdraw', _fn14)


def _fn20():
    def _fn21():
        expect(coin_float_plan(990, 5000, 0, False)).to_equal(Record({'qty': 0, 'drawn': True}))
        expect(coin_float_plan(0, 5000, 0, False)).to_equal(Record({'qty': 0, 'drawn': True}))
    test('a spend-nothing quest never withdraws', _fn21)

    def _fn22():
        expect(coin_float_plan(0, 5000, 1000, False)).to_equal(Record({'qty': 1000, 'drawn': False}))
    test('empty pack, bank covers -> withdraw the full float', _fn22)

    def _fn23():
        expect(coin_float_plan(1000, 5000, 1000, False)).to_equal(Record({'qty': 0, 'drawn': True}))
    test('a pack holding the float is drawn and never revisited', _fn23)

    def _fn24():
        expect(coin_float_plan(990, 5000, 1000, False)).to_equal(Record({'qty': 10, 'drawn': False}))
        expect(coin_float_plan(990, 5000, 1000, True)).to_equal(Record({'qty': 0, 'drawn': True}))
    test('a 10gp gate after the float is drawn does not emit a withdraw', _fn24)


describe('coinFloatPlan', _fn20)


def _fn25():
    def _fn26():
        inv = {}
        bank = {_k: _v for _k, _v in [['trout', 50]]}
        expect(float_withdraw(inv, bank, 'Trout', 10)).to_equal(Record({'name': 'Trout', 'qty': 10}))
    test('lowercases the lookup, keeps the display name on the withdraw', _fn26)

    def _fn27():
        expect(float_withdraw({_k: _v for _k, _v in [['trout', 4]]}, {_k: _v for _k, _v in [['trout', 50]]}, 'Trout', 10)).to_equal(Record({'name': 'Trout', 'qty': 6}))
        expect(float_withdraw({}, {_k: _v for _k, _v in [['trout', 3]]}, 'Trout', 10)).to_equal(Record({'name': 'Trout', 'qty': 3}))
        expect(float_withdraw({_k: _v for _k, _v in [['trout', 10]]}, {_k: _v for _k, _v in [['trout', 50]]}, 'Trout', 10)).to_be_null()
        expect(float_withdraw({}, {}, 'Trout', 10)).to_be_null()
    test('tops up to target, capped at the bank; null once held or bank dry', _fn27)


describe('floatWithdraw (generalised, e.g. quest food)', _fn25)


def _fn28():
    def _fn29():
        expect(should_freshen_pack('not_started', 28, False)).to_be(True)
        expect(should_freshen_pack('not_started', 1, False)).to_be(True)
    test('a not-started quest with anything in the pack starts by emptying it', _fn29)

    def _fn30():
        expect(should_freshen_pack('not_started', 0, False)).to_be(False)
    test('an empty pack is already fresh', _fn30)

    def _fn31():
        expect(should_freshen_pack('not_started', 28, True)).to_be(False)
    test('runs once per quest', _fn31)

    # Why: Shield of Arrav resumed at PHOENIX_JOINED had its store key and shield half banked by the session's first sweep, and both the chest and Straven re-check the bank, so neither came back.
    def _fn32():
        expect(should_freshen_pack('in_progress', 28, False)).to_be(False)
    test('a quest already underway keeps its pack, first of the session or not', _fn32)

    def _fn33():
        expect(should_freshen_pack('unknown', 28, False)).to_be(False)
        expect(should_freshen_pack('complete', 28, False)).to_be(False)
    test('an unread journal waits rather than banking the pack blind', _fn33)


describe('shouldFreshenPack', _fn28)


def _fn34():
    def _fn35():
        expect(float_draw_plan(0, 500, 8, False)).to_equal(Record({'qty': 8, 'drawn': False}))
    test('draws the whole float into an empty pack', _fn35)

    def _fn36():
        expect(float_draw_plan(3, 500, 8, False)).to_equal(Record({'qty': 5, 'drawn': False}))
    test('tops up a partial pack on the first pass', _fn36)

    def _fn37():
        expect(float_draw_plan(8, 500, 8, False)).to_equal(Record({'qty': 0, 'drawn': True}))
        expect(float_draw_plan(20, 500, 8, False)).to_equal(Record({'qty': 0, 'drawn': True}))
    test('a pack holding the float is drawn and never revisited', _fn37)

    def _fn38():
        expect(float_draw_plan(2, 500, 8, True)).to_equal(Record({'qty': 0, 'drawn': True}))
    test('eating into a drawn float does not send the quest back to the bank', _fn38)

    def _fn39():
        expect(float_draw_plan(0, 0, 8, False)).to_equal(Record({'qty': 0, 'drawn': False}))
    test('an empty bank draws nothing and stays undrawn, so a restock is still honoured', _fn39)

    def _fn40():
        expect(float_draw_plan(0, 3, 8, False)).to_equal(Record({'qty': 3, 'drawn': False}))
    test('a short bank draws what it has', _fn40)


describe('floatDrawPlan', _fn34)


def _fn41():
    def _fn42():
        # Why: bread estimates 20 gp. Topping up to 20 left the next boat fare unpayable.
        expect(buy_purse_top_up(0, 20)).to_equal(Record({'need': True, 'draw': COIN_FLOAT}))
    test('a cheap counter still carries a real purse, not the price of one loaf', _fn42)

    def _fn43():
        expect(buy_purse_top_up(COIN_FLOAT / 4 - 1, 20)['need']).to_be(True)
        expect(buy_purse_top_up(COIN_FLOAT / 4 + 1, 20)['need']).to_be(False)
    test('the trip is made well below what the quest needs, not at the last coin', _fn43)

    def _fn44():
        expect(buy_purse_top_up(COIN_FLOAT, 20)).to_equal(Record({'need': False, 'draw': 0}))
        expect(buy_purse_top_up(50000, 20)).to_equal(Record({'need': False, 'draw': 0}))
    test('a purse that already covers the float is left alone', _fn44)

    def _fn45():
        expect(buy_purse_top_up(0, 12000)).to_equal(Record({'need': True, 'draw': 12000}))
        expect(buy_purse_top_up(2000, 12000)).to_equal(Record({'need': True, 'draw': 10000}))
    test('a counter dearer than the float tops up to the counter', _fn45)

    def _fn46():
        expect(buy_purse_top_up(200, 20)['draw']).to_be(COIN_FLOAT - 200)
    test('the draw is the shortfall, never the whole target on top of the pack', _fn46)


describe('buyPurseTopUp', _fn41)
