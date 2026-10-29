"""Shop transfers count actual arrivals and stop on depleted stock or rejected updates."""

import rs2004.trade as market
from rs2004.entities import EntityQuery
from helpers import FakeModule
from coverage_world import PatchWorld
from test_trade_workflows import Item


class ShopWorld(PatchWorld):
    def __init__(self):
        PatchWorld.__init__(self)
        self.open = True
        self.stock = [Item(1, 'Logs', 100, ['Value', 'Buy 1', 'Buy 5', 'Buy 10'])]
        self.pack = [Item(1, 'Logs', 20, ['Value', 'Sell 1', 'Sell 5', 'Sell 10'])]
        self.keepers = [FakeModule(name='Bob', distance=lambda: 1, actions=lambda: ['Trade'], interact=self.interact)]
        self.transfers = []
        self.clicks = []
        self.respond = True
        self.pending_open = False

    def __enter__(self):
        PatchWorld.__enter__(self)
        self.patch(market, '_core', self)
        self.patch(market, 'inventory', FakeModule(count=self.count, count_by_id=self.count_id))
        self.patch(market, 'npcs', FakeModule(query=lambda: EntityQuery(self.scene, lambda obj: True)))
        return self

    def count(self, name):
        return sum([item.count for item in self.pack if item.name == name])

    def count_id(self, id):
        return sum([item.count for item in self.pack if item.id == id])

    def scene(self, ids, names, radius, layer):
        return self.keepers

    def interact(self, op):
        assert op == 'Trade'
        self.pending_open = True
        return True

    def get_main_modal(self):
        return 100 if self.open else -1

    def get_side_modal(self):
        return 200 if self.open else -1

    def get_inventories(self, root):
        return [(root + 1, 'inv', 0, ['Buy 1'] if root == 100 else ['Sell 1'])]

    def get_inventory(self, com):
        return self.stock if com == 101 else self.pack

    def inv_button(self, item, op):
        label = item._ops[op - 1]
        self.clicks.append((item.id, label))
        self.transfers.append((item, label))
        return True

    def close_interfaces(self):
        self.open = False

    def advance(self):
        PatchWorld.advance(self)
        if self.respond:
            if self.pending_open:
                self.open, self.pending_open = True, False
            for item, label in self.transfers:
                amount = min(item.count, int(label.split()[-1]))
                item.count -= amount
                target = self.pack if label.startswith('Buy') else self.stock
                found = [entry for entry in target if entry.id == item.id]
                if found:
                    found[0].count += amount
                else:
                    target.append(Item(item.id, item.name, amount, ['Sell 1', 'Sell 5', 'Sell 10']))
            self.pack = [item for item in self.pack if item.count > 0]
        self.transfers = []


def test_shop_opens_from_keeper_and_handles_missing_or_silent_keeper():
    with ShopWorld() as world:
        assert world.run(market.shop.open('Bob'))
        world.open = False
        assert world.run(market.shop.open('Bob')) and world.now == 500
        world.open, world.keepers = False, []
        assert world.run(market.shop.open('Bob')) is False
    with ShopWorld() as world:
        world.open, world.respond = False, False
        assert world.run(market.shop.open('Bob')) is False
        assert world.now == market.OPEN_TIMEOUT_MS * 3


def test_shop_buy_by_id_counts_arrivals_and_missing_id_is_noop():
    with ShopWorld() as world:
        assert world.run(market.shop.buy_by_id(1, 16)) == 16
        assert world.count_id(1) == 36 and world.stock[0].count == 84
        assert world.run(market.shop.buy_by_id(2, 1)) == 0


def test_shop_depleted_stock_missing_actions_and_silent_server_stop():
    for failure in ['empty', 'actions', 'silent']:
        with ShopWorld() as world:
            if failure == 'empty':
                world.stock[0].count = 0
            elif failure == 'actions':
                world.stock[0]._ops = ['Value']
            else:
                world.respond = False
            assert world.run(market.shop.buy('Logs', 10)) == 0
            assert world.count('Logs') == 20


def test_shop_sell_uses_selected_stack_and_sell_all_drains_remaining_pack():
    with ShopWorld() as world:
        world.pack.append(Item(2, 'Logs', 5, ['Sell 1', 'Sell 5', 'Sell 10']))
        assert world.run(market.shop.sell('Logs', 5, lambda item: item.id == 2)) == 5
        assert world.count_id(2) == 0 and world.count_id(1) == 20
        assert world.run(market.shop.sell_all('Logs')) == 20
        assert world.pack == []
        assert world.run(market.shop.sell_all('Missing')) == 0


def test_shop_sell_all_missing_actions_silent_server_and_closed_shop():
    for failure in ['actions', 'silent', 'closed']:
        with ShopWorld() as world:
            if failure == 'actions':
                world.pack[0]._ops = ['Value']
            elif failure == 'silent':
                world.respond = False
            else:
                world.open = False
            assert world.run(market.shop.sell_all('Logs')) == 0 and world.count('Logs') == 20


def test_shop_close_confirms_closed_state_and_is_idempotent():
    with ShopWorld() as world:
        assert world.run(market.shop.close()) and not world.open
        assert world.run(market.shop.close())
