"""Trade decisions over delayed interface updates, with no real player or server."""

import rs2004.trade as market
from rs2004 import execution


class Item:
    def __init__(self, id, name, count, ops):
        self.id = id
        self.name = name
        self.count = count
        self._ops = ops


class Component:
    def __init__(self, x=0, width=512):
        self.x = x
        self.width = width


class TradeWorld:
    def __init__(self):
        self.mode = 'offer'
        self.pack = [Item(1511, 'Logs', 20, ['Offer 1', 'Offer 5', 'Offer 10', 'Offer All', 'Offer X'])]
        self.mine = []
        self.theirs = []
        self.labels = []
        self.texts = ['Trading With: Alice']
        self.clicks = []
        self.answers = []
        self.waits = []
        self.now = 0
        self.count_open = False
        self.accept_count = True
        self.accept_click = True
        self.respond = True
        self.pending = None
        self.selected = None
        self.closed = 0

    def __enter__(self):
        self.saved = (market._core, execution._core)
        market._core = self
        execution._core = self
        return self

    def __exit__(self, *args):
        market._core, execution._core = self.saved

    def step_time(self):
        return self.now

    def get_main_modal(self):
        return -1 if self.mode == 'closed' else 100

    def get_side_modal(self):
        return 200 if self.mode == 'offer' else -1

    def get_inventories(self, root):
        if root == 200:
            return [(201, 'inv', 0, ['Offer 1'])]
        if root == 100 and self.mode == 'offer':
            return [(101, 'inv', 20, ['Remove All']), (102, 'inv', 300, [None])]
        if root == 100 and self.mode == 'confirm':
            return [(301, 'invtext', 20, []), (302, 'invtext', 300, [])]
        return []

    def get_inventory(self, com):
        if com == 201:
            return self.pack
        if com == 101 or com == 301:
            return self.mine
        if com == 102 or com == 302:
            return self.theirs
        return []

    def get_component(self, com):
        return Component()

    def find_components(self, text, unused, root):
        assert text == 'Absolutely nothing!'
        return self.labels

    def get_texts(self, root):
        return self.texts

    def inv_button(self, item, op):
        label = item._ops[op - 1]
        self.clicks.append((item.id, label))
        if not self.accept_click:
            return False
        self.selected = item
        if label == 'Offer X':
            self.pending = ('count', 0)
        elif label == 'Offer All':
            self.pending = ('offer', item.count)
        elif label.startswith('Offer '):
            self.pending = ('offer', int(label.split()[1]))
        elif label == 'Remove All':
            self.pending = ('remove', 0)
        return True

    def is_count_dialog_open(self):
        return self.count_open

    def answer_count(self, amount):
        self.answers.append(amount)
        if not self.accept_count:
            return False
        self.count_open = False
        self.pending = ('offer', amount)
        return True

    def click_text(self, text, root):
        self.clicks.append(text)
        return False

    def close_interfaces(self):
        self.closed += 1
        self.pending = ('close', 0)

    def advance(self):
        if not self.respond or self.pending is None:
            return
        kind, amount = self.pending
        self.pending = None
        if kind == 'count':
            self.count_open = True
        elif kind == 'offer':
            amount = min(amount, self.selected.count)
            self.selected.count -= amount
            self.mine.append(Item(self.selected.id, self.selected.name, amount, ['Remove All']))
        elif kind == 'remove':
            self.mine = [item for item in self.mine if item is not self.selected]
        elif kind == 'close':
            self.mode = 'closed'

    def run(self, task):
        for guard in range(40):
            try:
                self.waits.append(next(task))
            except StopIteration as stopped:
                return stopped.value
            self.now += 500
            self.advance()
        assert False, 'the trade did not finish within the simulated update budget'


def test_offering_a_fixed_amount_waits_for_the_server_to_acknowledge_it():
    with TradeWorld() as world:
        assert world.run(market.trade.offer(' logs ', 5))
        assert world.clicks == [(1511, 'Offer 5')]
        assert world.answers == []
        assert [item.count for item in market.trade.my_offer()] == [5]
        assert world.pack[0].count == 15
        assert len(world.waits) == 1


def test_offering_a_custom_amount_waits_for_the_count_dialog_and_then_the_offer():
    with TradeWorld() as world:
        assert world.run(market.trade.offer('Logs', 7))
        assert world.clicks == [(1511, 'Offer X')]
        assert world.answers == [7]
        assert sum([item.count for item in market.trade.my_offer()]) == 7
        assert world.pack[0].count == 13
        assert len(world.waits) == 2


def test_a_missing_count_dialog_times_out_without_sending_an_amount():
    with TradeWorld() as world:
        world.respond = False
        assert not world.run(market.trade.offer('Logs', 7))
        assert world.answers == []
        assert world.mine == []
        assert world.now >= market.COUNT_DIALOG_TIMEOUT_MS


def test_a_rejected_count_answer_does_not_report_a_successful_offer():
    with TradeWorld() as world:
        world.accept_count = False
        assert not world.run(market.trade.offer('Logs', 7))
        assert world.answers == [7]
        assert world.mine == []
        assert world.pack[0].count == 20


def test_a_rejected_fixed_amount_click_does_not_wait_or_change_the_offer():
    with TradeWorld() as world:
        world.accept_click = False
        assert not world.run(market.trade.offer('Logs', 5))
        assert world.waits == []
        assert world.mine == []


def test_an_unacknowledged_offer_times_out_without_claiming_items_were_offered():
    with TradeWorld() as world:
        world.respond = False
        assert not world.run(market.trade.offer('Logs', 5))
        assert world.mine == []
        assert world.pack[0].count == 20
        assert world.now >= market.OFFER_TIMEOUT_MS


def test_existing_coins_do_not_acknowledge_a_new_offer_of_logs():
    with TradeWorld() as world:
        world.mine = [Item(995, 'Coins', 100, ['Remove All'])]
        world.respond = False
        assert not world.run(market.trade.offer('Logs', 5))
        assert [(item.id, item.count) for item in market.trade.my_offer()] == [(995, 100)]
        assert world.now >= market.OFFER_TIMEOUT_MS


def test_an_existing_stack_must_increase_before_an_additional_offer_succeeds():
    with TradeWorld() as world:
        world.mine = [Item(1511, 'Logs', 5, ['Remove All'])]
        assert world.run(market.trade.offer('Logs', 5))
        assert sum([item.count for item in market.trade.my_offer()]) == 10
        assert len(world.waits) == 1


def test_an_item_without_offer_x_cannot_silently_offer_a_different_quantity():
    with TradeWorld() as world:
        world.pack[0]._ops = ['Offer 1', 'Offer 5', 'Offer All']
        assert not world.run(market.trade.offer('Logs', 7))
        assert world.clicks == [] and world.waits == []


def test_invalid_quantities_and_missing_items_never_send_trade_clicks():
    with TradeWorld() as world:
        assert not world.run(market.trade.offer('Logs', 0))
        assert not world.run(market.trade.offer('Logs', -1))
        assert not world.run(market.trade.offer('missing', 5))
        assert world.clicks == [] and world.waits == []


def test_offer_all_can_choose_one_of_two_same_named_stacks():
    with TradeWorld() as world:
        world.pack.append(Item(1512, 'Logs', 3, ['Offer All']))
        assert market.trade.offer_all('Logs', lambda item: item.id == 1512)
        world.advance()
        assert world.clicks == [(1512, 'Offer All')]
        assert world.pack[0].count == 20
        assert [(item.id, item.count) for item in market.trade.my_offer()] == [(1512, 3)]


def test_an_empty_confirmation_is_ready_only_after_both_empty_labels_arrive():
    with TradeWorld() as world:
        world.mode = 'confirm'
        assert market.trade.on_confirm_screen()
        assert not market.trade.confirm_ready()
        world.labels = [Component(x=20)]
        assert not market.trade.confirm_ready()
        world.labels.append(Component(x=300))
        assert market.trade.confirm_ready()


def test_confirmation_can_mix_items_on_one_side_and_an_empty_label_on_the_other():
    with TradeWorld() as world:
        world.mode = 'confirm'
        world.mine = [Item(1511, 'Logs', 5, [])]
        assert not market.trade.confirm_ready()
        world.labels = [Component(x=300)]
        assert market.trade.confirm_ready()
        assert [item.count for item in market.trade.my_offer()] == [5]
        assert market.trade.their_offer() == []


def test_removing_the_offer_waits_for_each_stack_and_stops_when_it_is_empty():
    with TradeWorld() as world:
        world.mine = [Item(1511, 'Logs', 5, ['Remove All']), Item(995, 'Coins', 30, ['Remove All'])]
        assert world.run(market.trade.remove_all())
        assert world.mine == []
        assert world.clicks == [(1511, 'Remove All'), (995, 'Remove All')]
        assert len(world.waits) == 2


def test_removing_an_offer_stops_after_the_retry_limit_when_the_server_never_changes_it():
    with TradeWorld() as world:
        world.respond = False
        world.mine = [Item(1511, 'Logs', 5, ['Remove All'])]
        assert not world.run(market.trade.remove_all())
        assert len(world.clicks) == market.REMOVE_ROUNDS
        assert len(world.waits) == market.REMOVE_ROUNDS


def test_decline_falls_back_to_closing_interfaces_and_waits_for_the_close():
    with TradeWorld() as world:
        assert world.run(market.trade.decline())
        assert world.clicks == ['Decline']
        assert world.closed == 1
        assert world.mode == 'closed'
        assert market.trade.partner() is None


def test_trade_status_distinguishes_waiting_from_the_other_players_acceptance():
    with TradeWorld() as world:
        world.texts += ['Other player has accepted.', 'Welcome to RuneScape.']
        assert market.trade.partner() == 'Alice'
        assert market.trade.their_accepted()
        assert not market.trade.waiting()
        assert market.trade.status() == ['Other player has accepted.']
        world.texts = ['Waiting for other player...']
        assert market.trade.waiting()
        assert not market.trade.their_accepted()
