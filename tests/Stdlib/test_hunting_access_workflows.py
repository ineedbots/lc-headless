"""Dungeon entry, paid access, prison keys and exits acknowledge delayed movement."""

import rs2004.hunting.supply as supply
from rs2004 import execution
from rs2004.entities import EntityQuery
from rs2004.geometry import Tile
from helpers import FakeModule
from test_hunting_supply import SupplyWorld
from test_bank_workflows import Item


class AccessObject(Item):
    def __init__(self, world, id, name, op, destination=None):
        Item.__init__(self, id, name, 1)
        self.world, self.op, self.destination = world, op, destination
        self.index, self.dist = id, 1
        self.accept = True

    def actions(self):
        return [self.op]

    def distance(self):
        return self.dist

    def tile(self):
        return self.world.position.translate(2, 0)

    def interact(self, op):
        self.world.actions.append((self.name, op))
        if not self.accept:
            return False
        if op == 'Pay':
            self.world.pending_payment = True
        elif op == 'Attack':
            self.world.pending_kill = self
        elif op == 'Take':
            self.world.pending_key = supply.JAIL_KEY_ID
        elif op == 'Talk-to':
            self.world.pending_talk = self
        else:
            self.world.pending_position = (supply.JAIL_DOOR if self.id == supply.JAIL_DOOR_LOC and supply.in_cell()
                                           else self.destination)
        return True

    def use_on(self, target):
        self.world.actions.append((self.name, 'Use', target.name))
        if self.accept:
            self.world.pending_position = target.destination
        return self.accept


class AccessWorld(SupplyWorld):
    def __init__(self):
        SupplyWorld.__init__(self)
        self.position = Tile(100, 100)
        self.site.in_area = lambda tile: tile is not None and tile.x >= 200
        self.site.key, self.site.approach = 'test lair', [Tile(201, 100), Tile(210, 100)]
        self.site.gate, self.site.talk_gate, self.site.exit = None, None, None
        self.site.walk_out, self.site.bank, self.site.target = Tile(100, 100), Tile(90, 100), 'Dragon'
        self.host.keep_extra = lambda: ['Keepsake']
        self.walks, self.actions, self.messages, self.scene, self.locations, self.drops = [], [], [], [], [], []
        self.walk_results = []
        self.pending_position, self.pending_kill, self.pending_key, self.pending_talk = None, None, None, None
        self.pending_payment = False
        self.movement_lands, self.payment_lands, self.kill_lands, self.key_lands = True, True, True, True
        self.dialogue_open, self.talk_lands, self.interrupted = False, True, False
        self.can_reach, self.bank_opens, self.trips = False, True, 0
        self.host.count_bank_trip = self.count_trip
        self.host.food_withdraw = lambda: 0
        self.hp = 100
        self.patches = []

    def patch(self, name, value):
        self.patches.append((name, getattr(supply, name)))
        setattr(supply, name, value)

    def __enter__(self):
        SupplyWorld.__enter__(self)
        self.patch('fee_paid_for', None)
        self.patch('traversal', FakeModule(walk_resilient=self.walk))
        self.patch('direct_navigator', FakeModule(walk_to=self.direct_walk))
        self.patch('reachability', FakeModule(can_reach=lambda *args, **kwargs: self.can_reach))
        self.patch('locs', FakeModule(query=lambda: self.query(self.locations)))
        self.patch('npcs', FakeModule(query=lambda: self.query(self.scene), all=lambda: self.scene))
        self.patch('ground_items', FakeModule(query=lambda: self.query(self.drops)))
        self.patch('event_signal', FakeModule(pending=lambda: self.interrupted))
        self.patch('sustain', FakeModule(run=self.sustain))
        self.patch('chat_dialog', FakeModule(can_continue=lambda: False, is_open=lambda: self.dialogue_open))
        self.patch('reader', FakeModule(modals=lambda: FakeModule(main=-1)))
        self.patch('game_messages', FakeModule(mark=lambda: len(self.messages), saw_since=self.saw))
        self.patch('drive_dialog', self.dialog)
        return self

    def __exit__(self, *args):
        for name, value in reversed(self.patches):
            setattr(supply, name, value)
        SupplyWorld.__exit__(self, *args)

    def query(self, objects):
        def scene(ids, names, radius, layer):
            return [obj for obj in objects if (names is None or obj.name in names)
                    and (radius is None or obj.distance() <= radius)]
        return EntityQuery(scene, lambda obj: True)

    def saw(self, mark, needle):
        return any([needle.lower() in line.lower() for line in self.messages[mark:]])

    def count_trip(self):
        self.trips += 1

    def walk(self, tile, **kwargs):
        self.walks.append(tile)
        accepted = self.walk_results.pop(0) if self.walk_results else True
        if accepted:
            self.pending_position = tile
        yield execution.Ticks(1)
        return accepted

    def direct_walk(self, tile, radius, timeout):
        result = yield from self.walk(tile)
        return result

    def sustain(self):
        yield from execution.delay_ticks(0)

    def dialog(self, prefer, log):
        yield execution.Ticks(1)
        self.dialogue_open = False
        return self.talk_lands

    def advance(self):
        SupplyWorld.advance(self)
        if self.pending_position is not None:
            if self.movement_lands:
                self.position = self.pending_position
            self.pending_position = None
        if self.pending_payment:
            if self.payment_lands:
                self.messages.append('fee paid')
            self.pending_payment = False
        if self.pending_kill is not None:
            if self.kill_lands:
                self.scene.remove(self.pending_kill)
                self.drops.append(AccessObject(self, supply.JAIL_KEY_ID, supply.JAIL_KEY, 'Take'))
            self.pending_kill = None
        if self.pending_key is not None:
            if self.key_lands:
                self.pack.append(AccessObject(self, self.pending_key, 'Key', 'Use'))
                self.drops = []
            self.pending_key = None
        if self.pending_talk is not None:
            if self.talk_lands:
                self.dialogue_open = True
                if self.pending_talk.name == supply.VELRAK:
                    self.pack.append(AccessObject(self, 999, 'Dusty key', 'Use'))
                else:
                    self.position = Tile(200, 100)
            self.pending_talk = None

    def gate(self, keyed=False):
        gate = FakeModule(outside=Tile(100, 100), inside=Tile(200, 100), loc_id=10, op='Open')
        self.site.gate = gate
        self.locations = [AccessObject(self, 10, 'Gate', 'Open', gate.inside)]
        if keyed:
            self.site.key_item = FakeModule(id=999, name='Dusty key')
            self.pack.append(AccessObject(self, 999, 'Dusty key', 'Use'))
        return self.locations[0]

    def fee(self):
        self.site.fee_gate = FakeModule(npc='Doorman', coins=10, stand=Tile(100, 100), op='Pay',
            paid_line='fee paid', prepaid_line='already paid', entrance=FakeModule(loc_id=10, op='Open'))
        self.pack = [Item(995, 'Coins', 20)]
        self.scene = [AccessObject(self, 20, 'Doorman', 'Pay')]
        self.locations = [AccessObject(self, 10, 'Entrance', 'Open', Tile(200, 100))]

    def prison(self):
        self.site.key_item = FakeModule(id=999, name='Dusty key')
        self.position = supply.JAIL_DOOR
        self.locations = [AccessObject(self, supply.JAIL_DOOR_LOC, 'Cell door', 'Open', supply.JAIL_DOOR_INSIDE)]
        self.scene = [AccessObject(self, 1, supply.JAILER, 'Attack'),
                      AccessObject(self, 2, supply.VELRAK, 'Talk-to')]

    def banking(self):
        if not self.stock:
            self.stock = [Item(1, 'Bank placeholder', 1)]
        actual = self.bank
        proxy = FakeModule(open_nearest=self.open_bank)
        for name in ['items', 'count', 'count_by_id', 'is_open', 'loaded', 'withdraw', 'withdraw_by_id',
                     'deposit', 'deposit_all_matching', 'close', 'withdraw_x']:
            setattr(proxy, name, getattr(actual, name))
        self.patch('bank', proxy)
        supply.equipment.equip = self.equip
        for item in self.pack:
            item.noted = False

    def open_bank(self, name, op):
        yield execution.Ticks(1)
        self.open = self.bank_opens
        return self.bank_opens

    def equip(self, name):
        item = self.first(name)
        self.pack.remove(item)
        self.worn.append(item)
        yield execution.Ticks(1)
        return True


def test_hunt_approach_skips_reachable_stand_and_walks_remaining_stops():
    with AccessWorld() as world:
        world.can_reach = True
        world.run(supply.walk_approach(world.host, world.site, Tile(210, 100)))
        assert world.walks == []
        world.can_reach = False
        world.position = Tile(201, 100)
        world.run(supply.walk_approach(world.host, world.site))
        assert world.walks == [Tile(210, 100)]


def test_hunt_ungated_entry_confirms_final_area():
    for lands in [True, False]:
        with AccessWorld() as world:
            world.movement_lands = lands
            assert world.run(supply.enter_lair(world.host, world.site)) == lands
            assert len(world.walks) == 2


def test_hunt_gate_accepts_plain_open_or_key_and_checks_arrival():
    for keyed in [True, False]:
        with AccessWorld() as world:
            world.gate(keyed)
            assert world.run(supply.enter_lair(world.host, world.site))
            assert world.site.in_area(world.position) and len(world.actions) == 1
            assert world.run(supply.enter_lair(world.host, world.site))
            assert len(world.actions) == 1


def test_hunt_gate_missing_key_rejected_click_and_failed_arrival():
    for failure in ['walk', 'missing', 'key', 'click', 'arrival']:
        with AccessWorld() as world:
            door = world.gate(True)
            if failure == 'walk':
                world.walk_results = [False]
            elif failure == 'missing':
                world.locations = []
            elif failure == 'key':
                world.pack = []
            elif failure == 'click':
                world.pack[0].accept = False
            else:
                world.movement_lands = False
            assert world.run(supply.enter_lair(world.host, world.site)) is False
            assert not world.site.in_area(world.position)


def test_hunt_fee_paid_once_when_entrance_requires_retry():
    with AccessWorld() as world:
        world.fee()
        entrance = world.locations.pop()
        assert world.run(supply.enter_lair(world.host, world.site)) is False
        assert supply.fee_prepaid(world.site)
        world.locations = [entrance]
        assert world.run(supply.enter_lair(world.host, world.site))
        assert world.actions.count(('Doorman', 'Pay')) == 1
        assert not supply.fee_prepaid(world.site)


def test_hunt_fee_failure_paths_stop_before_entrance():
    for failure in ['coins', 'walk', 'missing', 'click', 'payment', 'arrival']:
        with AccessWorld() as world:
            world.fee()
            if failure == 'coins':
                world.pack = []
            elif failure == 'walk':
                world.walk_results = [False]
            elif failure == 'missing':
                world.scene = []
            elif failure == 'click':
                world.scene[0].accept = False
            elif failure == 'payment':
                world.payment_lands = False
            else:
                world.movement_lands = False
            assert world.run(supply.enter_lair(world.host, world.site)) is False


def test_hunt_talk_gate_success_missing_refused_and_unanswered():
    for outcome in ['success', 'missing', 'refused', 'silent', 'walk']:
        with AccessWorld() as world:
            world.site.talk_gate = FakeModule(npc='Guard', stand=Tile(100, 100), op='Talk-to', choose='Yes')
            world.scene = [AccessObject(world, 1, 'Guard', 'Talk-to')]
            if outcome == 'missing':
                world.scene = []
            elif outcome == 'refused':
                world.scene[0].accept = False
            elif outcome == 'silent':
                world.talk_lands = False
            elif outcome == 'walk':
                world.walk_results = [False]
            assert world.run(supply.enter_lair(world.host, world.site)) == (outcome == 'success')


def test_hunt_walk_exit_checks_that_area_was_left():
    for lands in [True, False]:
        with AccessWorld() as world:
            world.position = Tile(210, 100)
            world.movement_lands = lands
            assert world.run(supply.walk_out_of_lair(world.host, world.site)) == lands


def test_hunt_cave_exit_success_missing_refused_and_silent():
    for outcome in ['success', 'missing', 'refused', 'silent']:
        with AccessWorld() as world:
            world.position = Tile(210, 100)
            world.site.exit = FakeModule(stand=world.position, loc_id=10, op='Exit')
            cave = AccessObject(world, 10, 'Cave', 'Exit', Tile(100, 100))
            world.locations = [] if outcome == 'missing' else [cave]
            cave.accept = outcome != 'refused'
            world.movement_lands = outcome != 'silent'
            assert world.run(supply.walk_out_of_lair(world.host, world.site)) == (outcome == 'success')


def test_hunt_gate_exit_opens_from_inside_and_walks_out():
    with AccessWorld() as world:
        door = world.gate()
        world.position = Tile(210, 100)
        door.destination = Tile(100, 100)
        world.host.leave_by_walk = lambda: True
        assert world.run(supply.leave_lair(world.host, world.site))
        assert world.actions == [('Gate', 'Open')] and not world.site.in_area(world.position)
        assert world.run(supply.leave_lair(world.host, world.site))


def test_hunt_jailer_death_leads_to_confirmed_key_pickup():
    with AccessWorld() as world:
        world.prison()
        assert world.run(supply.kill_jailer(world.host))
        assert world.count_by_id(supply.JAIL_KEY_ID) == 1
        assert world.actions == [('Jailer', 'Attack'), (supply.JAIL_KEY, 'Take')]


def test_hunt_jailer_rejected_attack_does_not_claim_key():
    with AccessWorld() as world:
        world.prison()
        world.scene[0].accept = False
        assert world.run(supply.kill_jailer(world.host)) is False
        assert world.count_by_id(supply.JAIL_KEY_ID) == 0


def test_hunt_key_pickup_missing_and_unacknowledged_are_bounded():
    for missing in [True, False]:
        with AccessWorld() as world:
            world.key_lands = False
            if not missing:
                drop = AccessObject(world, supply.JAIL_KEY_ID, supply.JAIL_KEY, 'Take')
                drop.dist = 2
                world.drops = [drop]
            assert world.run(supply.take_jail_key(world.host)) is False
            assert world.count_by_id(supply.JAIL_KEY_ID) == 0


def test_hunt_cell_unlock_and_leave_confirm_each_side():
    with AccessWorld() as world:
        world.prison()
        world.pack = [AccessObject(world, supply.JAIL_KEY_ID, supply.JAIL_KEY, 'Use')]
        assert world.run(supply.unlock_cell(world.host)) and supply.in_cell()
        world.locations[0].destination = supply.JAIL_DOOR
        assert world.run(supply.leave_cell(world.host)) and not supply.in_cell()
        assert world.run(supply.leave_cell(world.host))


def test_hunt_cell_missing_key_door_or_arrival_is_failure():
    for failure in ['key', 'door', 'click', 'arrival']:
        with AccessWorld() as world:
            world.prison()
            world.pack = [AccessObject(world, supply.JAIL_KEY_ID, supply.JAIL_KEY, 'Use')]
            if failure == 'key':
                world.pack = []
            elif failure == 'door':
                world.locations = []
            elif failure == 'click':
                world.pack[0].accept = False
            else:
                world.movement_lands = False
            assert world.run(supply.unlock_cell(world.host)) is False


def test_hunt_velrak_talk_waits_for_dialogue_and_key():
    with AccessWorld() as world:
        world.prison()
        world.scene[1].dist = 3
        assert world.run(supply.talk_in_cell(world.host))
        assert world.count_by_id(999) == 1 and world.walks


def test_hunt_velrak_missing_refused_and_silent_dialogue():
    for failure in ['missing', 'refused', 'silent']:
        with AccessWorld() as world:
            world.prison()
            if failure == 'missing':
                world.scene = []
            elif failure == 'refused':
                world.scene[1].accept = False
            else:
                world.talk_lands = False
            assert world.run(supply.talk_in_cell(world.host)) is False


def test_hunt_ensure_key_without_requirement_or_with_held_key_is_noop():
    with AccessWorld() as world:
        assert world.run(supply.acquire_key(world.host, world.site)) == 'held'
        world.site.key_item = FakeModule(id=999, name='Dusty key')
        world.pack = [AccessObject(world, 999, 'Dusty key', 'Use')]
        assert world.run(supply.acquire_key(world.host, world.site)) == 'held'


def test_hunt_bank_open_checks_travel_open_and_loaded_state():
    for failure in ['none', 'walk', 'open', 'loaded']:
        with AccessWorld() as world:
            world.banking()
            world.walk_results = [failure != 'walk']
            world.bank_opens = failure != 'open'
            if failure == 'loaded':
                world.stock = []
            assert world.run(supply.open_site_bank(world.host, world.site)) == (failure == 'none')


def test_hunt_full_bank_routine_restock_then_equip_and_count_trip():
    for deposit_all in [False, True]:
        with AccessWorld() as world:
            world.banking()
            world.stock = [Item(841, 'Shortbow', 1), Item(882, 'Bronze arrow', 100)]
            opts = supply.BankOpts(deposit_inventory=deposit_all, withdraw_food=True, escape_stock=0)
            world.run(supply.bank_routine(world.host, world.site, opts))
            assert world.trips == 1 and not world.open
            assert any([i.name == 'Shortbow' for i in world.worn])
            assert world.statuses[-1] == 'restocked, heading back to the dragons'


def test_hunt_bank_routine_failed_open_does_not_count_trip():
    with AccessWorld() as world:
        world.banking()
        world.bank_opens = False
        world.run(supply.bank_routine(world.host, world.site, supply.BankOpts()))
        assert world.trips == 0


def test_hunt_gate_exit_unacknowledged_movement_is_failure():
    with AccessWorld() as world:
        world.gate()
        world.position = Tile(200, 100)
        world.movement_lands = False
        assert world.run(supply.walk_out_of_lair(world.host, world.site)) is False
        assert world.site.in_area(world.position)


def test_hunt_acquire_key_failed_bank_open_returns_fetch_state():
    with AccessWorld() as world:
        world.site.key_item = FakeModule(id=999, name='Dusty key')
        world.banking()
        world.bank_opens = False
        assert world.run(supply.acquire_key(world.host, world.site)) == 'fetch'


def test_hunt_bank_keeps_key_coins_and_supplies_but_deposits_notes():
    with AccessWorld() as world:
        world.site.key_item, world.site.coins = FakeModule(id=999, name='Dusty key'), 100
        world.pack = [Item(1, 'Keepsake', 1), Item(2, 'Loot', 1)]
        world.pack[1]._ops = ['Deposit All']
        world.banking()
        assert 'Dusty key' in supply.keep_names(world.host, world.site)
        world.run(supply.deposit_loot(world.host, world.site))
        assert [i.name for i in world.pack] == ['Keepsake']


def test_hunt_acquire_key_from_bank_or_velrak():
    for banked in [True, False]:
        with AccessWorld() as world:
            world.prison()
            world.banking()
            world.site.in_area = lambda tile: False
            world.site.approach = []
            if banked:
                world.stock = [Item(999, 'Dusty key', 1)]
            assert world.run(supply.acquire_key(world.host, world.site)) == 'held'
            assert world.count_by_id(999) == 1 and not world.open
            if not banked:
                assert not supply.in_cell()


def test_hunt_fetch_key_failed_talk_still_leaves_cell():
    with AccessWorld() as world:
        world.prison()
        world.position = supply.JAIL_DOOR_INSIDE
        world.talk_lands = False
        assert world.run(supply.fetch_from_velrak(world.host, 999)) is False
        assert not supply.in_cell()


def test_hunt_fetch_key_failed_walk_or_jailer_stops_early():
    for failure in ['walk', 'jailer']:
        with AccessWorld() as world:
            world.prison()
            if failure == 'walk':
                world.position = Tile(2900, 9690)
                world.walk_results = [False]
            else:
                world.scene[0].accept = False
            assert world.run(supply.fetch_from_velrak(world.host, 999)) is False


def test_hunt_jailer_absence_and_interrupted_fight_are_failure():
    for missing in [True, False]:
        with AccessWorld() as world:
            world.prison()
            if missing:
                world.scene = []
            else:
                world.interrupted = True
            assert world.run(supply.kill_jailer(world.host)) is False


def test_hunt_cell_exit_missing_door_and_unacknowledged_open():
    for missing in [True, False]:
        with AccessWorld() as world:
            world.prison()
            world.position = supply.JAIL_DOOR_INSIDE
            if missing:
                world.locations = []
            else:
                world.movement_lands = False
            assert world.run(supply.leave_cell(world.host)) is False


def test_hunt_flask_conversion_preserves_potion_dose_forms():
    from rs2004.catalogs.combat import PotionPlan, BoostPotion
    potion = BoostPotion('attack', 'atk', 'Attack potion')
    plan = supply.as_flask(PotionPlan(potion, potion.flask, 2))
    assert plan.want == 2 and plan.doses == potion.doses
    assert 'Antifire' in repr(supply.antifire_plan(1))
