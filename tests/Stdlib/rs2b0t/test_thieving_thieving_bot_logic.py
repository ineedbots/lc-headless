"""rs2b0t's test/scripts/ArdyFighter/ThievingBotLogic.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs import Record, STUN_COMBAT_TICKS, THIEVER_BANKING_OPTIONS, auto_food_banking, can_steal_now, count_food, food_matches, next_withdraw_chunk, safe_to_steal, should_restock_food


def _fn1():
    def _fn2():
        expect(THIEVER_BANKING_OPTIONS).to_equal(['None', 'Auto'])
        expect(auto_food_banking('Auto')).to_be(True)
        expect(auto_food_banking(' none ')).to_be(False)
    test('banking is opt-in', _fn2)

    def _fn3():
        expect(food_matches('2/3 cake', 'cake')).to_be(True)
        expect(food_matches('Lobster', 'CAKE')).to_be(False)
        expect(food_matches('Cake', '')).to_be(False)
        expect(count_food([
        Record({'name': 'Cake', 'count': 1}),
        Record({'name': 'Slice of cake', 'count': 2}),
        Record({'name': 'Coins', 'count': 50}),
    ], 'cake')).to_be(3)
    test('food matching retains the existing case-insensitive contains behavior', _fn3)

    def _fn4():
        expect(should_restock_food(True, 1, 1, False)).to_be(True)
        expect(should_restock_food(True, 2, 1, False)).to_be(False)
        expect(should_restock_food(True, 10, 1, True)).to_be(True)
        expect(should_restock_food(False, 0, 1, True)).to_be(False)
    test('auto banking triggers at the food floor or a full pack with bankable items', _fn4)

    def _fn5():
        expect(safe_to_steal(0.49, 0.5, 0)).to_be(False)
        expect(safe_to_steal(0.49, 0.5, 1)).to_be(True)
        expect(safe_to_steal(0.5, 0.5, 0)).to_be(True)
        expect(can_steal_now(0, 4, 5, False)).to_be(False)
        expect(can_steal_now(1, 4, 5, False)).to_be(True)
        expect(can_steal_now(0, 6, 5, False)).to_be(True)
    test('low health without food blocks another pickpocket attempt', _fn5)

    def _fn6():
        expect(can_steal_now(0, 4, 5, True)).to_be(True)
        expect(can_steal_now(0, 1, 5, True)).to_be(True)
    test('suicide thieving keeps stealing at low HP with no food', _fn6)


describe('Thiever food banking', _fn1)


def _fn7():
    def _fn8():
        # Here a chunk is a (kind, op or count) tuple.
        expect(next_withdraw_chunk(0)).to_be_null()
        expect(next_withdraw_chunk(-1)).to_be_null()
        expect(next_withdraw_chunk(1)).to_equal(('op', 'Withdraw-1'))
        expect(next_withdraw_chunk(4)).to_equal(('op', 'Withdraw-1'))
        expect(next_withdraw_chunk(5)).to_equal(('op', 'Withdraw-5'))
        expect(next_withdraw_chunk(9)).to_equal(('op', 'Withdraw-5'))
        expect(next_withdraw_chunk(10)).to_equal(('op', 'Withdraw-10'))
        expect(next_withdraw_chunk(11)).to_equal(('x', 11))
        expect(next_withdraw_chunk(22)).to_equal(('x', 22))
    test('need ladder: 1 / 5 / 10 / X', _fn8)


describe('bulk withdraw chunk selection', _fn7)


def _fn9():
    def _fn10():
        expect(STUN_COMBAT_TICKS).to_be(9)
    test('wait the full 9-tick movement lock (retrying at 8 only turns the character)', _fn10)


describe('pickpocket stun', _fn9)
