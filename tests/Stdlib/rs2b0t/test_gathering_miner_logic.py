"""rs2b0t's test/scripts/GatheringBot/MinerLogic.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs import FOOD_OPTIONS, Record
from bots.miner import BOT as MINER
from bots.gathering.miner_logic import MINER_FOOD_SETTINGS, desert_camp_food_reserve_depleted, desert_camp_food_reserved_slots, miner_food_config, miner_food_restock_needed, plan_miner_food_withdrawal, should_eat_miner_food, unsupported_camp_ores


def _fn1():
    def _fn2():
        expect(MINER_FOOD_SETTINGS['food'].options).to_equal(FOOD_OPTIONS)
        expect(MINER_FOOD_SETTINGS['food_withdraw']).to_match_object(Record({'default': 0, 'min': 0, 'max': 27}))
        expect(miner_food_config('Lobster', 0)).to_be_null()
        expect(miner_food_config('  Swordfish  ', 12.9)).to_equal(Record({'name': 'Swordfish', 'target': 12}))
        expect(miner_food_config('Lobster', 99)).to_equal(Record({'name': 'Lobster', 'target': 27}))
        expect(miner_food_config('', 12)).to_be_null()
    test('food is opt-in, named, and bounded to the usable pack size', _fn2)

    def _fn3():
        settings = MINER.settings_schema
        expect(settings.get('food')).to_be(MINER_FOOD_SETTINGS['food'])
        expect(settings.get('food_withdraw')).to_be(MINER_FOOD_SETTINGS['food_withdraw'])
    test('the bundled Miner exposes both food controls', _fn3)


describe('Miner food settings', _fn1)


def _fn5():
    def _fn6():
        expect(should_eat_miner_food(28, 40, 12, 1, False)).to_be(True)
        expect(should_eat_miner_food(29, 40, 12, 1, False)).to_be(False)
    test('eats at the exact no-overheal boundary', _fn6)

    def _fn7():
        expect(should_eat_miner_food(10, 40, 12, 0, True)).to_be(False)
        expect(should_eat_miner_food(0, 40, 12, 1, False)).to_be(False)
        expect(should_eat_miner_food(10, 40, 0, 1, False)).to_be(False)
    test('does not eat without usable food or a living HP state', _fn7)

    def _fn8():
        expect(should_eat_miner_food(40, 40, 12, 3, True)).to_be(True)
        expect(should_eat_miner_food(40, 40, 12, 3, False)).to_be(False)
    test('eats from a full pack even at full HP to make one more ore slot', _fn8)

    def _fn9():
        expect(should_eat_miner_food(40, 40, 4, 7, True, True)).to_be(False)
        expect(should_eat_miner_food(36, 40, 4, 7, True, True)).to_be(True)
    test('retains full-pack food needed for a hazardous travel leg', _fn9)

    def _fn10():
        expect(should_eat_miner_food(5, 10, 12, 3, False, True)).to_be(True)
        expect(should_eat_miner_food(6, 10, 12, 3, False, True)).to_be(False)
    test('eats at the safety floor even when the full heal cannot fit', _fn10)

    def _fn11():
        expect(should_eat_miner_food(9, 10, 12, 2, False, True, 9)).to_be(True)
        expect(should_eat_miner_food(10, 10, 12, 2, False, True, 9)).to_be(False)
    test('eats before Desert Camp heat can kill a low-HP player', _fn11)


describe('Miner eating policy', _fn5)


def _fn12():
    def _fn13():
        expect(desert_camp_food_reserve_depleted(2)).to_be(False)
        expect(desert_camp_food_reserve_depleted(1)).to_be(True)
        expect(desert_camp_food_reserve_depleted(0)).to_be(True)
    test('keeps one food item in reserve for the Desert Camp exit', _fn13)

    def _fn14():
        expect(plan_miner_food_withdrawal(12, 4, 50, 20, 0)).to_equal(Record({'ok': True, 'withdraw': 8}))
        expect(plan_miner_food_withdrawal(12, 12, 0, 16, 0)).to_equal(Record({'ok': True, 'withdraw': 0}))
    test('tops up the named food to the exact configured target', _fn14)

    def _fn15():
        expect(plan_miner_food_withdrawal(12, 4, 7, 20, 0)).to_equal(Record({'ok': False, 'withdraw': 0, 'reason': 'bank-stock', 'missing': 1}))
    test('rejects a partial trip when the bank is short', _fn15)

    def _fn16():
        expect(plan_miner_food_withdrawal(27, 2, 50, 24, 0)).to_equal(Record({'ok': False, 'withdraw': 0, 'reason': 'pack-space', 'missing': 1}))
    test('rejects a target that cannot fit beside the carried gear', _fn16)

    def _fn17():
        expect(desert_camp_food_reserved_slots(8)).to_be(9)
        expect(plan_miner_food_withdrawal(20, 0, 50, 28, 9)).to_equal(Record({'ok': False, 'withdraw': 0, 'reason': 'pack-space', 'missing': 1}))
        expect(plan_miner_food_withdrawal(19, 19, 0, 9, 10)).to_equal(Record({'ok': False, 'withdraw': 0, 'reason': 'pack-space', 'missing': 1}))
    test('keeps route supplies and one ore slot out of the food allowance', _fn17)

    def _fn18():
        expect(plan_miner_food_withdrawal(19, 0, 50, 28, 9)).to_equal(Record({'ok': True, 'withdraw': 19}))
    test('allows the exact food maximum beside supplies and the ore slot', _fn18)

    def _fn19():
        expect(miner_food_restock_needed(True, 4, True)).to_be(True)
        expect(miner_food_restock_needed(True, 4, False)).to_be(False)
        expect(miner_food_restock_needed(True, 0, False)).to_be(True)
        expect(miner_food_restock_needed(False, 0, True)).to_be(False)
    test('restocks once at startup and again only after the trip food is gone', _fn19)


describe('Miner food restocking', _fn12)


def _fn20():
    def _fn21():
        supported = ['copper', 'tin', 'mithril', 'adamantite']
        expect(unsupported_camp_ores(['Copper', 'Tin', 'Mithril', 'Adamantite'], supported)).to_equal([])
        expect(unsupported_camp_ores(['Coal'], supported)).to_equal(['Coal'])
    test('accepts the four live Desert Mining Camp ores and rejects absent Coal', _fn21)

    def _fn22():
        supported = ['copper', 'tin', 'iron', 'coal']
        expect(unsupported_camp_ores(['Copper', 'Tin', 'Iron', 'Coal'], supported)).to_equal([])
        expect(unsupported_camp_ores(['Mithril'], supported)).to_equal(['Mithril'])
    test('accepts the four live Desert Mining Camp Surface ores and rejects underground-only Mithril', _fn22)

    def _fn23():
        expect(unsupported_camp_ores(['Mithril', 'ADAMANTITE'], ['mithril', 'adamantite'])).to_equal([])
        expect(unsupported_camp_ores(['Coal'], None)).to_equal([])
    test('matches ore names case-insensitively and leaves freeform camps alone', _fn23)


describe('named-camp ore validation', _fn20)
