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


# rs2b0t's test/api/bank/banking-route.test.ts.
DRAYNOR = Tile(3093, 3243, 0)
EDGEVILLE = Tile(3094, 3493, 0)
CATHERBY = Tile(2809, 3441, 0)
VARROCK_WEST = Tile(3185, 3440, 0)
NEAREST_DRAYNOR = {'name': 'Draynor', 'tile': {'x': 3093, 'z': 3243, 'level': 0}}
NEAREST_CATHERBY = {'name': 'Catherby', 'tile': {'x': 2809, 'z': 3441, 'level': 0}}


def test_the_nearby_bank_radius_is_wide_enough_for_a_booth_underfoot():
    assert NEARBY_BANK_RADIUS == 14


def test_an_open_bank_wins_over_everything():
    assert resolve_bank_open_route(bank_open=True, here=DRAYNOR, stand=EDGEVILLE, nearby_booth_dist=2, nearest=NEAREST_DRAYNOR) == 'already-open'


def test_a_booth_within_the_radius_beats_a_distant_preset():
    assert resolve_bank_open_route(here=DRAYNOR, stand=EDGEVILLE, nearby_booth_dist=3, nearest=NEAREST_DRAYNOR) == 'scene-booth'
    assert resolve_bank_open_route(here=DRAYNOR, stand=EDGEVILLE, nearby_booth_dist=NEARBY_BANK_RADIUS, nearest=NEAREST_DRAYNOR) == 'scene-booth'
    assert resolve_bank_open_route(here=DRAYNOR, stand=EDGEVILLE, nearby_booth_dist=NEARBY_BANK_RADIUS + 1, nearest=NEAREST_DRAYNOR) != 'scene-booth'


def test_without_prefer_nearby_the_preset_stand_is_used():
    assert resolve_bank_open_route(here=DRAYNOR, stand=EDGEVILLE, nearby_booth_dist=2, nearest=NEAREST_DRAYNOR, prefer_nearby=False) == 'preset-stand'


def test_a_known_bank_here_beats_a_distant_preset():
    varrock = {'name': 'Varrock West', 'tile': {'x': 3185, 'z': 3440, 'level': 0}}
    assert resolve_bank_open_route(here=VARROCK_WEST, stand=DRAYNOR, nearest=varrock) == 'local-bank'


def test_the_preset_stand_when_it_is_the_bank_here_too():
    assert resolve_bank_open_route(here=CATHERBY, stand=CATHERBY, nearest=NEAREST_CATHERBY) == 'preset-stand'


def test_the_preset_stand_when_nothing_is_near():
    assert resolve_bank_open_route(here=Tile(3000, 3300, 0), stand=EDGEVILLE) == 'preset-stand'


def test_the_nearest_bank_when_there_is_no_stand_and_no_bank_here():
    assert resolve_bank_open_route(here=Tile(2500, 3200, 0), nearest=NEAREST_DRAYNOR) == 'nearest-fallback'
    assert resolve_bank_open_route(here=DRAYNOR, nearest=NEAREST_DRAYNOR) == 'local-bank'


def test_a_tighter_radius_tightens_the_booth_snap():
    assert resolve_bank_open_route(here=DRAYNOR, stand=EDGEVILLE, nearby_booth_dist=10, nearest=NEAREST_DRAYNOR, nearby_radius=8) != 'scene-booth'
    assert resolve_bank_open_route(here=DRAYNOR, stand=EDGEVILLE, nearby_booth_dist=10, nearest=NEAREST_DRAYNOR, nearby_radius=12) == 'scene-booth'
