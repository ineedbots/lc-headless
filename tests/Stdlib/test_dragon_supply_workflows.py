"""Dragon Slayer builds supplies in batches and checks each acquisition's server response."""

import rs2004.quests.defs.dragonslayer.supplies as supply
from helpers import FakeModule
from quest_world import QuestWorld, QuestObject


class SupplyWorld(QuestWorld):
    def __init__(self):
        QuestWorld.__init__(self)
        self.menu = False
        self.panel_open = False
        self.product = None
        self.can_make = True
        self.can_bank = True
        self.can_shop = True
        self.buy_lands = True
        self.food = ''
        self.bank_calls = []

    def __enter__(self):
        QuestWorld.__enter__(self)
        self.install(supply)
        self.patch(supply, '_core', self)
        self.patch(supply, 'pickaxe_tried', set())
        self.patch(supply, 'plank_tried', set())
        self.patch(supply, 'quest_food', FakeModule(name=self.food))
        self.patch(supply, 'open_bank_leg', lambda *a: self.reply(self.can_bank))
        self.patch(supply, 'bank', FakeModule(withdraw_x=self.withdraw, deposit=self.deposit,
                                            deposit_all_matching=self.deposit_matching))
        self.patch(supply, 'shop', FakeModule(open=lambda npc: self.reply(self.can_shop),
                                            buy=self.buy, close=lambda: self.reply()))
        self.patch(supply, 'chat_dialog', FakeModule(is_make_menu=lambda: self.menu,
            is_main_make_panel=lambda: self.panel_open, make=self.make, make_from_panel_max=self.make))
        self.patch(supply, 'talk_through', lambda *a: self.buy("Wizard's mind bomb", 1))
        return self

    def withdraw(self, name, count):
        self.bank_calls.append((name, count))
        yield from self.buy(name, count)
        return True

    def buy(self, name, count):
        yield from self.reply()
        if self.buy_lands:
            self.hold(name, count)
        return count if self.buy_lands else 0

    def deposit(self, name):
        self.effects.append(lambda: self.pack.remove(self.first(name)))
        return True

    def deposit_matching(self, predicate):
        yield from self.reply()
        self.pack = [i for i in self.pack if not predicate(i.name, i.id)]
        return True

    def make(self, name):
        yield from self.reply()
        if self.can_make and self.product is not None:
            self.pack = [i for i in self.pack if i.name not in ['Clay', 'Soft clay', 'Iron ore', 'Coal', 'Steel bar']]
            self.hold(self.product, 12 if self.product == 'Nails' else 1)
        return self.can_make


def test_dragon_spending_money_is_drawn_only_when_needed_and_verified():
    for mode in ['held', 'no_bank', 'no_money', 'drawn']:
        with SupplyWorld() as w:
            w.can_bank = mode != 'no_bank'
            w.buy_lands = mode != 'no_money'
            if mode == 'held':
                w.hold('Coins', 100)
            assert w.run(supply.ensure_coins(100, w.logs.append)) == (mode in ['held', 'drawn'])
            if mode == 'drawn':
                assert w.bank_calls == [('Coins', 2000)]


def test_mind_bomb_purchase_checks_cash_room_arrival_dialogue_and_delivery():
    for mode in ['no_cash', 'full', 'walk_failed', 'silent', 'bought']:
        with SupplyWorld() as w:
            w.can_bank = mode != 'no_cash'
            w.can_walk = mode != 'walk_failed'
            w.buy_lands = mode != 'silent'
            if mode == 'full':
                w.hold('Coins', 20)
                w.pack += [QuestObject(w, 'Junk') for i in range(27)]
            assert w.run(supply.buy_mind_bomb(w.logs.append)) == (mode == 'bought')


def test_dragon_mining_checks_tools_space_seam_and_unnoted_yield():
    for mode in ['held', 'no_pick', 'full', 'walk_failed', 'no_scene', 'depleted', 'refused', 'silent', 'mined']:
        with SupplyWorld() as w:
            w.position = supply.SUPPLY_LOC.CLAY_ROCKS
            if mode != 'no_pick':
                w.hold('Bronze pickaxe')
            if mode == 'held':
                w.hold('Clay')
            if mode == 'full':
                w.pack += [QuestObject(w, 'Junk') for i in range(27)]
            rock = QuestObject(w, 'Rocks', 2108, ['Mine'], effect=lambda: w.hold('Clay'))
            rock.accept = mode != 'refused'
            w.respond = mode != 'silent'
            if mode == 'depleted':
                w.scene = [QuestObject(w, 'Depleted rocks', 999)]
            elif mode in ['refused', 'silent', 'mined']:
                w.scene = [rock]
            w.can_walk = mode != 'walk_failed'
            assert w.run(supply.mine_for([2108], 'Clay', 1, w.position, w.logs.append)) == (mode in ['held', 'mined'])
            if mode == 'mined':
                assert w.count('Clay') == 1


def test_dragon_pickaxe_search_checks_all_spawns_before_buying():
    with SupplyWorld() as w:
        w.scene = [QuestObject(w, 'Scenery')]
        for i in range(len(supply.PICKAXE_SPAWNS)):
            assert not w.run(supply.ensure_pickaxe(w.logs.append))
        assert w.run(supply.ensure_pickaxe(w.logs.append))
        assert w.count('Bronze pickaxe') == 1
        assert w.run(supply.ensure_pickaxe(w.logs.append)) and not supply.pickaxe_tried
    for mode in ['take', 'refused', 'no_cash', 'walk_failed', 'shop_failed']:
        with SupplyWorld() as w:
            if mode in ['take', 'refused']:
                drop = QuestObject(w, 'Bronze pickaxe', effect=lambda: w.hold('Bronze pickaxe'))
                drop.accept = mode != 'refused'
                w.scene = [drop]
            else:
                supply.pickaxe_tried.update([f'{t.x},{t.z}' for t in supply.PICKAXE_SPAWNS])
            w.can_bank = mode != 'no_cash'
            w.can_walk = mode != 'walk_failed'
            w.can_shop = mode != 'shop_failed'
            assert w.run(supply.ensure_pickaxe(w.logs.append)) == (mode == 'take')


def test_dragon_bowl_chain_sources_jug_water_clay_and_shapes_the_bowl():
    for mode in ['held', 'jug', 'fill', 'mix', 'shape']:
        with SupplyWorld() as w:
            w.hold('Coins', 2000)
            if mode == 'held':
                w.hold('Unfired bowl')
            elif mode == 'fill':
                jug = w.hold('Jug', effect=lambda: w.hold('Jug of water'))
                w.scene = [QuestObject(w, 'Fountain', at=supply.SUPPLY_LOC.FOUNTAIN)]
            elif mode == 'mix':
                w.hold('Clay', effect=lambda: w.hold('Soft clay'))
                w.hold('Jug of water')
            elif mode == 'shape':
                w.hold('Soft clay', effect=lambda: setattr(w, 'menu', True))
                w.scene = [QuestObject(w, "Potter's Wheel", at=supply.SUPPLY_LOC.POTTERS_WHEEL)]
                w.product = 'Unfired bowl'
            assert w.run(supply.make_unfired_bowl(w.logs.append)), mode
            expected = {'held': 'Unfired bowl', 'jug': 'Jug', 'fill': 'Jug of water', 'mix': 'Soft clay', 'shape': 'Unfired bowl'}[mode]
            assert w.count(expected) > 0


def test_dragon_bowl_chain_fails_on_rejected_use_missing_fixture_or_make():
    for phase in ['jug', 'fill', 'mix', 'shape']:
        for failure in ['walk', 'missing', 'refused', 'silent', 'make']:
            with SupplyWorld() as w:
                w.hold('Coins', 2000)
                w.can_walk = failure != 'walk'
                w.respond = failure != 'silent'
                if phase == 'jug':
                    w.can_shop = False
                elif phase == 'fill':
                    item = w.hold('Jug')
                    w.scene = [QuestObject(w, 'Fountain', at=supply.SUPPLY_LOC.FOUNTAIN)]
                elif phase == 'mix':
                    item = w.hold('Clay')
                    w.hold('Jug of water')
                else:
                    item = w.hold('Soft clay', effect=lambda: setattr(w, 'menu', True))
                    w.scene = [QuestObject(w, "Potter's Wheel", at=supply.SUPPLY_LOC.POTTERS_WHEEL)]
                if phase != 'jug':
                    item.accept = failure != 'refused'
                if failure == 'missing':
                    w.scene = [QuestObject(w, 'Scenery', at=supply.SUPPLY_LOC.FOUNTAIN if phase == 'fill' else supply.SUPPLY_LOC.POTTERS_WHEEL)]
                w.can_make = failure != 'make'
                assert not w.run(supply.make_unfired_bowl(w.logs.append))


def test_dragon_nails_bank_spare_shopping_then_mine_an_ore_batch():
    with SupplyWorld() as w:
        w.hold('Silk')
        assert not w.run(supply.smith_nails(12, w.logs.append))
        assert not w.pack
        w.hold('Bronze pickaxe')
        w.position = supply.SUPPLY_LOC.IRON_ROCKS
        w.scene = [QuestObject(w, 'Iron rocks', 2092, ['Mine'], effect=lambda: w.hold('Iron ore', 6))]
        assert w.run(supply.smith_nails(12, w.logs.append)) and w.count('Iron ore') == 6
        w.position = supply.SUPPLY_LOC.COAL_ROCKS
        w.scene = [QuestObject(w, 'Coal rocks', 2096, ['Mine'], effect=lambda: w.hold('Coal', 12))]
        assert w.run(supply.smith_nails(12, w.logs.append)) and w.count('Coal') == 12


def test_dragon_nails_smelts_batch_and_hammers_bars_only_after_make_ack():
    for phase in ['smelt', 'hammer']:
        for mode in ['walk_failed', 'missing', 'refused', 'no_menu', 'make_failed', 'made']:
            with SupplyWorld() as w:
                w.can_walk = mode != 'walk_failed'
                w.can_make = mode != 'make_failed'
                if phase == 'smelt':
                    w.hold('Iron ore', 6)
                    w.hold('Coal', 12)
                    w.product = 'Steel bar'
                    fixture = QuestObject(w, 'Furnace', ops=['Smelt'], at=supply.SUPPLY_LOC.FURNACE,
                                          effect=lambda: setattr(w, 'menu', mode != 'no_menu'))
                    fixture.accept = mode != 'refused'
                else:
                    bar = w.hold('Steel bar', 6, effect=lambda: setattr(w, 'panel_open', mode != 'no_menu'))
                    bar.accept = mode != 'refused'
                    w.hold('Hammer')
                    w.product = 'Nails'
                    fixture = QuestObject(w, 'Anvil', at=supply.SUPPLY_LOC.ANVIL)
                w.scene = [QuestObject(w, 'Scenery', at=fixture.at)] if mode == 'missing' else [fixture]
                assert w.run(supply.smith_nails(12, w.logs.append)) == (mode == 'made'), (phase, mode, w.logs)
                if mode == 'made':
                    assert w.count(w.product) > 0
    with SupplyWorld() as w:
        assert w.run(supply.smith_nails(0, w.logs.append))
        w.hold('Steel bar')
        assert not w.run(supply.smith_nails(2, w.logs.append))


def test_dragon_planks_visit_each_empty_spawn_then_wait_for_respawn():
    with SupplyWorld() as w:
        for i in range(len(supply.SUPPLY_LOC.PLANK_SPAWNS) + 1):
            assert not w.run(supply.grab_planks(3, w.logs.append))
        assert any(['every plank spawn was empty' in line for line in w.logs])
        drop = QuestObject(w, 'Plank', effect=lambda: w.hold('Plank', 3))
        w.scene = [drop]
        drop.accept = False
        assert not w.run(supply.grab_planks(3, w.logs.append))
        drop.accept = True
        assert w.run(supply.grab_planks(3, w.logs.append))
        assert w.run(supply.grab_planks(0, w.logs.append)) and not supply.plank_tried
