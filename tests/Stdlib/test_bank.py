from rs2004.bank import FAILURE_BACKOFF_MS


def test_deposit_all_except_keeps_named_items_and_nameless_ones():
    deposit = deposit_all_except(['Bronze pickaxe', 'TINDERBOX'])
    assert deposit('Copper ore')
    assert not deposit('bronze pickaxe')
    assert not deposit('Tinderbox')
    assert not deposit('')


def test_common_bank_loot_matches_by_part_and_the_casket_by_id():
    assert matches_common_bank_loot('Uncut sapphire')
    assert matches_common_bank_loot('Strange fruit')
    assert not matches_common_bank_loot('Logs')
    assert not matches_common_bank_loot('')
    assert matches_common_bank_loot('', RANDOM_EVENT_CASKET_ID)
    assert is_disposable_gather_junk('Flier')
    assert is_disposable_gather_junk(None, RANDOM_EVENT_CASKET_ID)
    assert not is_disposable_gather_junk('Oak logs')


def test_deposit_matcher_adds_common_loot_when_asked():
    own = lambda name: name == 'Logs'
    assert deposit_matcher(own, True)('Logs')
    assert deposit_matcher(own, True)('Uncut ruby', -1)
    assert not deposit_matcher(own, False)('Uncut ruby', -1)


def test_withdraw_op_reads_the_amount_from_the_options():
    ops = ['Withdraw 1', 'Withdraw 5', 'Withdraw 10', 'Withdraw All', 'Withdraw X']
    assert withdraw_op(ops, '1') == 'Withdraw 1'
    assert withdraw_op(ops, '10') == 'Withdraw 10'
    assert withdraw_op(ops, 'all') == 'Withdraw All'
    assert withdraw_op(ops, 'x') == 'Withdraw X'
    assert withdraw_op(ops, 'any') == 'Withdraw 1'
    assert withdraw_op(['Withdraw-5', None], '5') == 'Withdraw-5'
    assert withdraw_op(['Deposit 1'], 'any') is None


def test_bank_strategies_decide_by_items_time_or_either():
    assert parse_bank_strategy('Loot count') == 'items'
    assert parse_bank_strategy(' Either ') == 'either'
    assert parse_bank_strategy('Time') == 'time'
    assert parse_bank_strategy('nonsense') == 'off'

    state = {'loot_count': 5, 'minutes_since_last_bank': 12, 'items_threshold': 10, 'minutes_threshold': 10}
    assert not should_bank_now('items', state)
    assert should_bank_now('time', state)
    assert should_bank_now('either', state)
    assert not should_bank_now('off', state)
    state['loot_count'] = 0
    assert not should_bank_now('either', state)


def test_the_bank_is_closed_without_a_game():
    assert not bank.is_open()
    assert bank.items() == []
    assert bank.count('Coins') == 0
    assert not bank.withdraw('Coins')
    assert PERIODIC_BANK_SETTINGS['bank_every_items'].default == 15
    assert FAILURE_BACKOFF_MS == 180000
