"""rs2b0t's test/scripts/GatheringBot/FishCookLogic.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs import Record
from bots.gathering.fish_cook import bank_pace_ticks, cook_batch_after_load, cook_filter_label, cook_pace_ticks, cooked_name_from_raw, count_matching, count_raw_in_bank, is_burnt_fish_name, is_cooked_fish_name, is_raw_fish_name, last_matching_index, parse_after_cook_cycle, parse_burnt_policy, parse_cook_mode, parse_positive_int, raw_matches_cook_filter, resolve_cook_fish_filter, should_cook_then_bank, should_finish_cook_load, should_keep_draining_cook_batch, should_start_bank_raw_cook_batch


def _fn1():
    def _fn2():
        expect(parse_cook_mode('Off')).to_be('off')
        expect(parse_cook_mode('Cook then bank')).to_be('cook-then-bank')
        expect(parse_cook_mode('bank raw then cook')).to_be('bank-raw-then-cook')
        expect(parse_cook_mode('nope')).to_be('off')
    test('parses cook mode labels', _fn2)

    def _fn3():
        expect(parse_burnt_policy('Drop')).to_be('drop')
        expect(parse_burnt_policy('Bank')).to_be('bank')
        expect(parse_burnt_policy('')).to_be('drop')
    test('burnt defaults to drop', _fn3)

    def _fn4():
        expect(parse_after_cook_cycle('Stop')).to_be('stop')
        expect(parse_after_cook_cycle('Continue')).to_be('continue')
        expect(parse_after_cook_cycle('')).to_be('stop')
        expect(parse_after_cook_cycle('continue')).to_be('continue')
    test('after cook cycle defaults to stop', _fn4)


describe('parseCookMode / parseBurntPolicy / parseAfterCookCycle', _fn1)


def _fn5():
    def _fn6():
        expect(parse_positive_int(56, 56)).to_be(56)
        expect(parse_positive_int(9999, 56)).to_be(9999)
        expect(parse_positive_int(0, 56)).to_be(1)
        expect(parse_positive_int(-3, 56)).to_be(1)
        expect(parse_positive_int('1,200', 56)).to_be(1200)
        expect(parse_positive_int('  84 ', 56)).to_be(84)
        expect(parse_positive_int('nope', 56)).to_be(56)
        expect(parse_positive_int(None, 56)).to_be(56)
    test('parsePositiveInt has no artificial max', _fn6)

    def _fn7():
        expect(resolve_cook_fish_filter('All raw', '')).to_be('')
        expect(resolve_cook_fish_filter('Swordfish', '')).to_be('Swordfish')
        expect(resolve_cook_fish_filter('Tuna', '')).to_be('Tuna')
        expect(resolve_cook_fish_filter('Custom', 'raw shark')).to_be('raw shark')
        expect(resolve_cook_fish_filter('Custom', '  ')).to_be('')
    test('resolveCookFishFilter', _fn7)

    def _fn8():
        expect(raw_matches_cook_filter('Raw swordfish', 'Swordfish')).to_be(True)
        expect(raw_matches_cook_filter('Raw tuna', 'Swordfish')).to_be(False)
        expect(raw_matches_cook_filter('Raw tuna', 'Tuna')).to_be(True)
        expect(raw_matches_cook_filter('Raw swordfish', 'Tuna')).to_be(False)
        expect(raw_matches_cook_filter('Raw lobster', '')).to_be(True)
        expect(raw_matches_cook_filter('Lobster', 'Lobster')).to_be(False)
        expect(raw_matches_cook_filter('Raw shark', 'raw shark')).to_be(True)
        expect(raw_matches_cook_filter(None, 'Tuna')).to_be(False)
    test('rawMatchesCookFilter tuna vs swordfish split', _fn8)

    def _fn9():
        expect(cook_filter_label('')).to_be('all raw')
        expect(cook_filter_label('Swordfish')).to_be('Swordfish')
    test('cookFilterLabel', _fn9)


describe('parsePositiveInt / cook fish filter', _fn5)


def _fn10():
    def _fn11():
        expect(is_raw_fish_name('Raw lobster')).to_be(True)
        expect(is_raw_fish_name('raw shark')).to_be(True)
        expect(is_raw_fish_name('Lobster')).to_be(False)
        expect(is_raw_fish_name('Burnt fish')).to_be(False)
        expect(is_raw_fish_name(None)).to_be(False)
    test('raw fish', _fn11)

    def _fn12():
        expect(is_burnt_fish_name('Burnt fish')).to_be(True)
        expect(is_burnt_fish_name('Burnt lobster')).to_be(True)
        expect(is_burnt_fish_name('Lobster')).to_be(False)
        expect(is_burnt_fish_name('Raw lobster')).to_be(False)
    test('burnt fish', _fn12)

    def _fn13():
        expect(is_cooked_fish_name('Lobster')).to_be(True)
        expect(is_cooked_fish_name('Swordfish')).to_be(True)
        expect(is_cooked_fish_name('Shrimps')).to_be(True)
        expect(is_cooked_fish_name('Cooked swordfish')).to_be(True)
        expect(is_cooked_fish_name('Raw lobster')).to_be(False)
        expect(is_cooked_fish_name('Burnt fish')).to_be(False)
        expect(is_cooked_fish_name('Coins')).to_be(False)
        expect(is_cooked_fish_name('Cooked meat')).to_be(False)
        expect(is_cooked_fish_name('Meat')).to_be(False)
    test('cooked fish', _fn13)

    def _fn14():
        expect(cooked_name_from_raw('Raw lobster')).to_be('lobster')
        expect(cooked_name_from_raw('Raw Shark')).to_be('Shark')
    test('cookedNameFromRaw strips Raw prefix', _fn14)


describe('fish name classifiers', _fn10)


def _fn15():
    pack = [
        Record({'name': 'Raw lobster'}),
        Record({'name': 'Lobster'}),
        Record({'name': 'Burnt fish'}),
        Record({'name': 'Raw lobster'}),
        Record({'name': 'Harpoon'}),
    ]

    def _fn16():
        expect(count_matching(pack, is_raw_fish_name)).to_be(2)
        expect(count_matching(pack, is_cooked_fish_name)).to_be(1)
        expect(count_matching(pack, is_burnt_fish_name)).to_be(1)
    test('countMatching', _fn16)

    def _fn17():
        expect(last_matching_index(pack, is_raw_fish_name)).to_be(3)
        expect(last_matching_index(pack, lambda n: n == 'Coins')).to_be(-1)
    test('lastMatchingIndex prefers last raw', _fn17)

    def _fn18():
        bank = [
        Record({'name': 'Raw tuna', 'count': 40}),
        Record({'name': 'Raw swordfish', 'count': 28}),
        Record({'name': 'Lobster', 'count': 10}),
        Record({'name': 'Coins', 'count': 500}),
        Record({'name': 'Raw lobster', 'count': 5}),
    ]
        expect(count_raw_in_bank(bank, '')).to_be(40 + 28 + 5)
        expect(count_raw_in_bank(bank, 'Swordfish')).to_be(28)
        expect(count_raw_in_bank(bank, 'Tuna')).to_be(40)
        expect(count_raw_in_bank(bank, 'lobster')).to_be(5)
        expect(count_raw_in_bank(bank, 'shark')).to_be(0)
    test('countRawInBank sums stacks for cook filter', _fn18)


describe('count / last index / bank raw sum', _fn15)


def _fn19():
    def _fn20():
        expect(should_cook_then_bank('cook-then-bank', True, 20)).to_be(True)
        expect(should_cook_then_bank('cook-then-bank', False, 20)).to_be(False)
        expect(should_cook_then_bank('cook-then-bank', True, 0)).to_be(False)
        expect(should_cook_then_bank('off', True, 20)).to_be(False)
        expect(should_cook_then_bank('bank-raw-then-cook', True, 20)).to_be(False)
    test('shouldCookThenBank only when full with cookable raw', _fn20)

    def _fn21():
        expect(should_finish_cook_load('cook-then-bank', True, 5)).to_be(True)
        expect(should_finish_cook_load('cook-then-bank', True, 0)).to_be(False)
        expect(should_finish_cook_load('off', True, 5)).to_be(False)
    test('shouldFinishCookLoad while cooking with raw left', _fn21)

    def _fn22():
        expect(should_start_bank_raw_cook_batch('bank-raw-then-cook', 56, 56)).to_be(True)
        expect(should_start_bank_raw_cook_batch('bank-raw-then-cook', 55, 56)).to_be(False)
        expect(should_start_bank_raw_cook_batch('cook-then-bank', 100, 56)).to_be(False)
        expect(should_start_bank_raw_cook_batch('bank-raw-then-cook', 10, 0)).to_be(False)
        expect(should_start_bank_raw_cook_batch('bank-raw-then-cook', 9999, 500)).to_be(True)
    test('shouldStartBankRawCookBatch uses live bank total vs target', _fn22)

    def _fn23():
        # fish-bank-raw-cook: cert_raw_lobster 973 → bank, inv 26 raw + catch 1.
        N = 1000
        banked = 973
        deposited = 27
        expect(should_start_bank_raw_cook_batch('bank-raw-then-cook', banked, N)).to_be(False)
        expect(should_start_bank_raw_cook_batch('bank-raw-then-cook', banked + deposited, N)).to_be(True)
        expect(count_raw_in_bank([Record({'name': 'Raw lobster', 'count': banked + deposited})], 'Lobster')).to_be(1000)
    test('harness shape: 973 banked + 27 deposited hits explicit N=1000', _fn23)

    def _fn24():
        N = 5000
        expect(should_start_bank_raw_cook_batch('bank-raw-then-cook', 5000, N)).to_be(True)
        # The threshold stays latched after the first withdrawal.
        expect(should_start_bank_raw_cook_batch('bank-raw-then-cook', 4972, N)).to_be(False)
        expect(should_keep_draining_cook_batch(True, 4972)).to_be(True)
        expect(should_keep_draining_cook_batch(True, 1)).to_be(True)
        expect(should_keep_draining_cook_batch(True, 0)).to_be(False)
        expect(should_keep_draining_cook_batch(False, 4972)).to_be(False)
    test('sticky batch: N is entry only — keep draining after withdraw drops below N', _fn24)

    def _fn25():
        expect(cook_batch_after_load(4972, 'stop')).to_be('drain-more')
        expect(cook_batch_after_load(4972, 'continue')).to_be('drain-more')
        expect(cook_batch_after_load(1, 'stop')).to_be('drain-more')
        expect(cook_batch_after_load(0, 'stop')).to_be('stop')
        expect(cook_batch_after_load(0, 'continue')).to_be('fish-again')
    test('cookBatchAfterLoad: drain-more until empty, then stop or fish-again', _fn25)


describe('cook flow predicates', _fn19)


def _fn26():
    def _fn27():
        def low():
            return 0.1

        def high():
            return 0.9
        expect(cook_pace_ticks(low)).to_be(1)
        expect(cook_pace_ticks(high)).to_be(1)
        expect(bank_pace_ticks(low)).to_be(2)
        expect(bank_pace_ticks(high)).to_be(1)
    test('cook is 1 tick; bank is 1–2 ticks', _fn27)


describe('pace ticks', _fn26)
