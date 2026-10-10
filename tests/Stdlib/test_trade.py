def test_shop_batches_take_tens_then_fives_then_ones_five_clicks_a_tick():
    ops = ['Value', 'Buy 1', 'Buy 5', 'Buy 10', None]
    assert shop_op_batch(ops, 'buy', 16) == [4, 3, 2]
    assert shop_op_batch(ops, 'buy', 3) == [2, 2, 2]
    assert shop_op_batch(ops, 'buy', 100) == [4, 4, 4, 4, 4]
    assert shop_op_batch(ops, 'sell', 5) == []
    assert shop_op_batch(['Value', 'Sell 1', 'Sell 5', 'Sell 10'], 'sell', 7) == [3, 2, 2]


def test_the_trade_partner_comes_from_the_header():
    assert parse_trade_partner_header('Trading With: Zezima') == 'Zezima'
    assert parse_trade_partner_header('Trading with Bob') == 'Bob'
    assert parse_trade_partner_header('Trading With:') is None
    assert parse_trade_partner_header('') is None
    assert parse_trade_partner_header(None) is None


def test_nothing_is_open_without_a_game():
    assert not shop.is_open()
    assert shop.stock() == []
    assert not trade.active()
    assert trade.partner() is None
    assert trade.my_offer() == []
    assert not trade.accept()
