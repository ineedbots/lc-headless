"""Hunt restocking over delayed bank updates, plus healing and escape failures."""

import rs2004.hunting.supply as supply
from rs2004.geometry import Tile
from helpers import FakeModule
from test_bank_workflows import BankWorld, Item


class Food(Item):
    def __init__(self, world):
        Item.__init__(self, 379, 'Lobster', 1)
        self.world = world

    def interact(self, op):
        return self.world.eat(self, op)


class SupplyWorld(BankWorld):
    def __init__(self):
        BankWorld.__init__(self)
        self.stock = []
        self.logs = []
        self.statuses = []
        self.hp = 40
        self.magic = 99
        self.position = Tile(3000, 3000)
        self.teleports = []
        self.teleport_lands = True
        self.worn = []
        self.food_target = 12
        self.eat_pending = None
        self.refuse_food = False
        self.eat_clicks = 0
        self.host = FakeModule(log=self.logs.append, set_status=self.statuses.append,
                               food_name=lambda: 'Lobster', food_withdraw=lambda: self.food_target,
                               style=lambda: 'range', ammo_name=lambda: 'Bronze arrow',
                               weapon_name=lambda: 'Shortbow', spell_name=lambda: 'Wind strike',
                               leave_by_walk=lambda: False, park_for=self.logs.append)
        self.site = FakeModule(escape_teleport_id='varrock',
                               in_area=lambda tile: tile.x == 3000, fire_at_range=False,
                               key_item=None, coins=None, fee_gate=None)

    def __enter__(self):
        BankWorld.__enter__(self)
        self.supply_saved = (supply.bank, supply.inventory, supply.equipment, supply.skills,
                             supply.game, supply._core, supply.teleport_by_id)
        supply.bank = self.bank
        supply.inventory = self
        supply.equipment = FakeModule(items=lambda: self.worn,
                                       contains=lambda name: any([i.name == name for i in self.worn]))
        supply.skills = FakeModule(level=lambda name: self.magic,
                                   effective=lambda name: self.hp, hp_fraction=lambda: self.hp / 100)
        supply.game = FakeModule(tile=lambda: self.position, teleport=self.teleport)
        supply._core = self
        # The fixture has no navigation cache; provide one catalog entry, with real rune requirements.
        supply.teleport_by_id = lambda id: {'label': 'Varrock', 'requires': {
            'skills': [{'name': 'magic', 'level': 25}],
            'items': [{'name': 'Law rune', 'count': 1}, {'name': 'Air rune', 'count': 3},
                      {'name': 'Fire rune', 'count': 1}]}} if id == 'varrock' else None
        return self

    def __exit__(self, *args):
        (supply.bank, supply.inventory, supply.equipment, supply.skills,
         supply.game, supply._core, supply.teleport_by_id) = self.supply_saved
        BankWorld.__exit__(self, *args)

    def tick(self):
        return self.now // 500

    def first(self, name):
        return ([i for i in self.pack if i.name == name] or [None])[0]

    def advance(self):
        BankWorld.advance(self)
        if self.eat_pending is not None:
            self.pack.remove(self.eat_pending)
            self.eat_pending = None
            self.hp = min(100, self.hp + 12)

    def teleport(self, id):
        self.teleports.append(id)
        if self.teleport_lands:
            self.position = Tile(3210, 3424)
        return self.teleport_lands

    def food(self, count):
        for _ in range(count):
            self.pack.append(Food(self))

    def eat(self, item, op):
        assert op == 'Eat'
        self.eat_clicks += 1
        if self.refuse_food:
            return False
        self.eat_pending = item
        return True


def test_withdraw_to_tops_up_instead_of_withdrawing_the_target_again():
    for target in [4, 8, 10, 14, 50]:
        with SupplyWorld() as world:
            world.pack = [Item(882, 'Bronze arrow', 3)]
            world.stock = [Item(882, 'Bronze arrow', 100)]
            assert world.run(supply.withdraw_to('Bronze arrow', target)) == target - 3
            assert world.count('Bronze arrow') == target
            assert world.run(supply.withdraw_to('Bronze arrow', target)) == 0


def test_withdraw_to_returns_only_arrivals_when_bank_stock_runs_out():
    with SupplyWorld() as world:
        world.stock = [Item(882, 'Bronze arrow', 5)]
        assert world.run(supply.withdraw_to('Bronze arrow', 30)) == 5
        assert world.count('Bronze arrow') == 5
        assert len(world.clicks) < 10


def test_withdraw_to_stops_when_full_or_server_does_not_respond():
    for full in [True, False]:
        with SupplyWorld() as world:
            world.stock = [Item(882, 'Bronze arrow', 100)]
            world.free_slots = 0 if full else 28
            world.respond = False
            assert world.run(supply.withdraw_to('Bronze arrow', 5)) == 0
            assert len(world.clicks) == (0 if full else 1)


def test_food_restock_uses_batches_and_warns_only_when_no_food_remains():
    with SupplyWorld() as world:
        world.stock = [Item(379, 'Lobster', 30)]
        # Food is unstackable: each server arrival is a single inventory item.
        world.food_target = 3
        world.run(supply.withdraw_food_to(world.host))
        assert supply.food_count(world.host) == 3
        assert world.clicks == [(379, 'Withdraw 1')] * 3
        assert world.logs == []
    with SupplyWorld() as world:
        world.run(supply.withdraw_food_to(world.host))
        assert len(world.logs) == 1
        assert 'no \'Lobster\' in the bank' in world.logs[0]


def test_flasks_count_partial_doses_and_only_top_up_missing_flasks():
    with SupplyWorld() as world:
        plan = supply.antipoison_plan(3)
        world.pack = [Item(179, plan.doses[-1], 1)]
        world.stock = [Item(2448, plan.flask, 10)]
        world.run(supply.withdraw_flasks(world.host, [plan]))
        assert supply.flasks_held(plan) == 3
        assert world.clicks == [(2448, 'Withdraw 1')] * 2
        assert world.logs == ['withdrew 2 Superantipoison(4)']
        assert supply.dose_to_drink(world.count) == plan.doses[-1]


def test_flasks_do_not_loop_on_missing_stock_or_a_full_pack():
    for full in [False, True]:
        with SupplyWorld() as world:
            world.free_slots = 0 if full else 28
            world.run(supply.withdraw_flasks(world.host, [supply.prayer_plan(2)]))
            assert len(world.logs) == 1
            assert 'trip goes without' in world.logs[0]
            assert world.clicks == []


def test_escape_shortfall_checks_magic_then_all_missing_runes():
    with SupplyWorld() as world:
        spell = supply.EscapeSpell([('Law rune', 1), ('Air rune', 3)], 25, 'Varrock')
        world.magic = 24
        assert supply.escape_shortfall(spell) == 'magic 24 is below the 25 it needs'
        world.magic = 25
        assert supply.escape_shortfall(spell) == 'no Law rune and Air rune'
        world.pack = [Item(563, 'Law rune', 1), Item(556, 'Air rune', 3)]
        assert supply.escape_shortfall(spell) is None


def test_escape_restock_reserves_the_exit_cast_on_top_of_spares():
    with SupplyWorld() as world:
        spell = supply.escape_runes_for(world.site.escape_teleport_id)
        world.stock = [Item(index + 1, row[0], 100) for index, row in enumerate(spell.runes)]
        world.run(supply.withdraw_escape_runes(world.host, world.site, supply.BankOpts(escape_stock=2)))
        for name, count in spell.runes:
            assert world.count(name) == count * 3
        assert world.logs == []
    with SupplyWorld() as world:
        world.run(supply.withdraw_escape_runes(world.host, world.site, supply.BankOpts()))
        assert len(world.logs) == 1
        assert 'cannot be cast' in world.logs[0]


def test_teleport_out_confirms_arrival_and_bounds_retries():
    for lands in [True, False]:
        with SupplyWorld() as world:
            spell = supply.escape_runes_for(world.site.escape_teleport_id)
            world.pack = [Item(index + 1, row[0], row[1]) for index, row in enumerate(spell.runes)]
            world.teleport_lands = lands
            why = world.run(supply.teleport_out(world.host, world.site))
            assert why == (None if lands else 'the cast never landed')
            assert len(world.teleports) == (1 if lands else 3)
            assert world.site.in_area(world.position) == (not lands)


def test_teleport_out_does_not_attempt_a_cast_without_runes():
    with SupplyWorld() as world:
        why = world.run(supply.teleport_out(world.host, world.site))
        assert why.startswith('no ')
        assert world.teleports == []


def test_ammo_counts_equipment_and_pack_case_insensitively():
    with SupplyWorld() as world:
        world.worn = [Item(882, 'BRONZE ARROW', 40), Item(841, 'Shortbow', 1)]
        world.pack = [Item(882, 'Bronze arrow', 7)]
        assert supply.ammo_left(world.host) == 47
        world.worn = []
        assert supply.ammo_left(world.host) == 7


def test_eat_once_waits_for_food_consumption_and_ignores_noted_food():
    with SupplyWorld() as world:
        note = Item(380, 'Lobster', 100)
        note.noted = True
        world.pack = [note]
        assert world.run(supply.eat_once(world.host)) is False
        world.food(1)
        assert world.run(supply.eat_once(world.host)) is True
        assert world.hp == 52
        assert world.pack == [note]


def test_heal_closes_bank_eats_to_threshold_and_leaves_remaining_food():
    with SupplyWorld() as world:
        world.food(8)
        assert world.run(supply.heal_up(world.host, 0.9)) is True
        assert not world.open
        assert world.hp == 100
        assert supply.food_count(world.host) == 3
        assert world.eat_clicks == 5
        assert 'healed 40% to 100%' in world.logs[-1]


def test_heal_stops_after_three_refused_bites():
    with SupplyWorld() as world:
        world.food(4)
        world.refuse_food = True
        assert world.run(supply.heal_up(world.host, 0.9)) is True
        assert world.eat_clicks == 3
        assert world.hp == 40
        assert supply.food_count(world.host) == 4


def test_heal_skips_when_healthy_or_without_food_and_stops_if_bank_wont_close():
    with SupplyWorld() as world:
        assert world.run(supply.heal_up(world.host, 0.9)) is False
        world.food(2)
        world.hp = 90
        assert world.run(supply.heal_up(world.host, 0.9)) is False
        assert world.clicks == []
        world.hp = 40
        world.close_responds = False
        assert world.run(supply.heal_up(world.host, 0.9)) is False
        assert world.eat_clicks == 0


def test_cell_bounds_include_edges_but_exclude_other_floors():
    with SupplyWorld() as world:
        for x, z in [(2928, 9683), (2934, 9689), (2931, 9686)]:
            world.position = Tile(x, z)
            assert supply.in_cell()
        for tile in [None, Tile(2927, 9683), Tile(2935, 9689),
                     Tile(2931, 9682), Tile(2931, 9690), Tile(2931, 9686, 1)]:
            world.position = tile
            assert not supply.in_cell()


def test_key_is_withdrawn_by_id_and_existing_key_is_not_duplicated():
    with SupplyWorld() as world:
        world.site.key_item = FakeModule(id=1590, name='Dusty key')
        world.stock = [Item(1590, 'Dusty key', 1)]
        assert world.run(supply.withdraw_key(world.host, world.site)) is True
        assert world.count_by_id(1590) == 1
        assert world.run(supply.withdraw_key(world.host, world.site)) is True
        assert world.clicks == [(1590, 'Withdraw 1')]
    with SupplyWorld() as world:
        world.site.key_item = FakeModule(id=1590, name='Dusty key')
        assert world.run(supply.withdraw_key(world.host, world.site)) is False
        assert 'Velrak' in world.logs[0]
        world.site.key_item = None
        assert world.run(supply.withdraw_key(world.host, world.site)) is True


def test_gear_restock_preserves_worn_items_and_withdraws_carry_items():
    with SupplyWorld() as world:
        world.worn = [Item(841, 'Shortbow', 1)]
        world.stock = [Item(1712, 'Amulet of glory', 1), Item(946, 'Knife', 1)]
        assert world.run(supply.withdraw_gear(world.host, world.site,
                                              wear=['Amulet of glory'], carry=['Knife'])) is True
        assert world.count('Amulet of glory') == 1
        assert world.count('Knife') == 1
        assert world.clicks == [(1712, 'Withdraw 1'), (946, 'Withdraw 1')]
        assert world.run(supply.withdraw_gear(world.host, world.site,
                                              wear=['Amulet of glory'], carry=['Knife'])) is True
        assert len(world.clicks) == 2


def test_gear_requires_a_shield_at_sites_with_ranged_dragonfire():
    with SupplyWorld() as world:
        world.site.fire_at_range = True
        world.worn = [Item(841, 'Shortbow', 1)]
        world.stock = [Item(995, 'Coins', 1)]
        assert world.run(supply.withdraw_gear(world.host, world.site)) is False
        assert any(['Dragonfire shield' in line for line in world.logs])
        world.stock = [Item(1540, supply.SHIELD, 1)]
        assert world.run(supply.withdraw_gear(world.host, world.site)) is True
        assert world.count(supply.SHIELD) == 1


def test_gear_does_not_withdraw_from_a_closed_or_unloaded_bank():
    for closed in [True, False]:
        with SupplyWorld() as world:
            world.open = not closed
            world.stock = [Item(841, 'Shortbow', 1)] if closed else []
            assert world.run(supply.withdraw_gear(world.host, world.site)) is False
            assert world.clicks == []


def test_fee_coins_are_topped_up_and_missing_entry_fees_are_reported():
    with SupplyWorld() as world:
        world.site.coins = 1000
        world.site.fee_gate = FakeModule(coins=875)
        world.pack = [Item(995, 'Coins', 100)]
        world.stock = [Item(995, 'Coins', 2000)]
        world.run(supply.withdraw_coins(world.host, world.site))
        assert world.count('Coins') == 1000
        assert world.logs == ['withdrew 900 coins (1000/1000)']
        world.run(supply.withdraw_coins(world.host, world.site))
        assert len(world.logs) == 1
    with SupplyWorld() as world:
        world.site.coins = 1000
        world.site.fee_gate = FakeModule(coins=875)
        world.run(supply.withdraw_coins(world.host, world.site))
        assert 'cannot cover the 875 coins' in world.logs[-1]


def test_ranged_restock_uses_requested_ammo_and_accepts_worn_ammo():
    with SupplyWorld() as world:
        world.stock = [Item(882, 'Bronze arrow', 100)]
        world.run(supply.withdraw_style_supplies(world.host, supply.BankOpts(ammo=20)))
        assert world.count('Bronze arrow') == 20
        assert world.logs == ['withdrew 20 Bronze arrow']
    with SupplyWorld() as world:
        world.worn = [Item(882, 'Bronze arrow', 7)]
        world.run(supply.withdraw_style_supplies(world.host, supply.BankOpts()))
        assert world.logs == []
        world.worn = []
        world.run(supply.withdraw_style_supplies(world.host, supply.BankOpts()))
        assert 'Deposit ammo to resume' in world.logs[-1]


def test_mage_restock_does_not_withdraw_elemental_runes_supplied_by_staff():
    with SupplyWorld() as world:
        world.host.style = lambda: 'mage'
        world.worn = [Item(1381, 'Staff of air', 1)]
        world.stock = [Item(558, 'Mind rune', 100), Item(556, 'Air rune', 100)]
        world.run(supply.withdraw_style_supplies(world.host, supply.BankOpts(rune_casts=10, rune_buffer=2)))
        assert world.count('Mind rune') == 12
        assert world.count('Air rune') == 0
        assert supply.casts_left(world.host) == 12
    with SupplyWorld() as world:
        world.host.style = lambda: 'mage'
        world.run(supply.withdraw_style_supplies(world.host, supply.BankOpts(rune_casts=1, rune_buffer=0)))
        assert 'cannot supply a single' in world.logs[-1]
