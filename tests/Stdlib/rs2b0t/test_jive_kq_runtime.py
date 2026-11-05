"""rs2b0t's KQ facade scenarios over the real Python controller (MIT, see thirdparty/rs2b0t)."""

import bots.jive_kq as kq
import _core
from bots.jivekq import supply, route, loot
from bots.jivekq.party import Party
from bots.jivekq.loadout import MACE, BOW, RECOIL, FOOD
from bots.jivekq.policy import Supplies
from bots.jivekq.policy import SURFACE, UPPER
from bots.jivekq.recovery import DeathReport, RecoveryItem
from rs2004.random_events import _RandomEvents
from rs2004.bank import bank, banking
from rs2004.catalogs import sustain
from rs2004.execution import event_signal
from rs2004.game import game, skills, reader
from rs2004.geometry import Tile
from rs2004.items import inventory, equipment
from rs2004.navigation import reachability
from rs2004.tabs import prayer, special, PROTECT_FROM_MAGIC
from rs2004.settings import SettingsBag


def result(value):
    return value
    yield


class QueenWorld(Scene):
    def __init__(self):
        Scene.__init__(self, Tile(3477, 9493))
        self.ticks = 100
        self.hp = 45
        self.food = 10
        self.prayer_points = 60
        self.prayer_doses = 6
        self.escape_ok = True
        self.arrows = 200
        self.accept = True
        self.active_prayers = set([PROTECT_FROM_MAGIC])
        self.events = []
        self.worn_ids = set([MACE, BOW, RECOIL])
        self.carried = {}
        self.pack_counts = False
        self.peer_overrides = {}
        self.bot = kq.JiveKQ()
        self.bot.settings = SettingsBag({'team': 'one,two,three,four'})
        self.bot.bind_log(self.log)
        stub(sustain, hook=None)
        stub(event_signal, _interrupt=None)
        spy_on(kq, 'now_ms', impl=self.now)
        spy_on(loot, 'now_ms', impl=self.now)
        spy_on(game, 'ingame', returns=True)
        spy_on(game, 'scene_ready', returns=True)
        spy_on(game, 'my_name', returns='one')
        spy_on(game, 'set_auto_retaliate', returns=True)
        spy_on(game, 'combat_mode', returns=1)
        spy_on(game, 'combat_styles', returns=[(1, 'Aggressive')])
        spy_on(game, 'facing', returns=('npc', 1))
        spy_on(skills, 'level', returns=70)
        spy_on(skills, 'effective', impl=lambda name: self.hp if name == 'hitpoints' else 80)
        spy_on(inventory, 'count_by_id', impl=self.count_id)
        spy_on(prayer, 'points', impl=lambda: self.prayer_points)
        spy_on(prayer, 'max', returns=70)
        spy_on(prayer, 'active', impl=lambda name: name in self.active_prayers)
        spy_on(prayer, 'toggle', impl=self.toggle)
        spy_on(special, 'ready', returns=False)
        spy_on(reachability, 'walkable', returns=True)
        spy_on(reachability, 'line_of_sight', returns=True)
        spy_on(self.bot, 'on', returns=None)
        spy_on(self.bot, 'post', returns=None)
        spy_on(kq, 'supplies', impl=lambda: Supplies(self.hp, self.count_id(FOOD), self.prayer_points, self.prayer_doses, self.escape_ok, self.arrows))
        spy_on(kq, 'worn', impl=lambda id: id in self.worn_ids)
        spy_on(kq, 'doses', impl=lambda name: self.prayer_doses if name == 'Prayer potion' else 0)
        spy_on(kq, 'boost', impl=lambda melee: result(False))
        spy_on(kq, 'send_eat', impl=self.send_eat)
        spy_on(kq, 'send_equip', impl=self.send_equip)
        spy_on(kq, 'step_to', impl=self.walk_click)
        spy_on(loot, 'step_to', impl=self.walk_click)
        spy_on(kq, 'camelot', impl=self.escape)
        run_wait(self.bot.on_start())
        self.bot.stage = 'fight'
        self.bot.trip = 1
        self.bot.prepared = True
        self.bot.last_dose = self.now()
        self.bot.last_attack = self.ticks
        self.bot.party = Party(['one', 'two', 'three', 'four'], 'one', 'one')
        self.queen = self.npc('Kalphite Queen', ['Attack'], Tile(3480, 9493), effect=self.attack, id=1158)
        self.queen._fields.update({'index': 1, 'size': 5, 'health': 255, 'max_health': 255, 'face_entity': -1})
        self.heartbeat()

    def now(self):
        return 1000000 + self.clock

    def heartbeat(self):
        tile = {'x': self.at.x, 'z': self.at.z, 'level': self.at.level}
        for name in self.bot.party.roster:
            if name == self.bot.party.self_name:
                continue
            message = {'name': name, 'session': name, 'trip': 1, 'stage': 'fight', 'ready': True, 'tile': tile}
            message.update(self.peer_overrides.get(name, {}))
            self.bot.party.receive(message, self.now())
        self.bot.heartbeat()

    def count_id(self, id):
        if self.pack_counts:
            return sum([item.count for item in self.pack if item.id == id])
        return self.food if id == FOOD else self.carried.get(id, 0)

    def drop(self, id=1113, name='Rune chainbody', tile=None):
        def take(op):
            self.events.append(('take', id, self.ticks))
            return self.accept

        return self.on_ground(id, name, tile=tile or Tile(3495, 9493), effect=take)

    def send_eat(self):
        self.events.append(('eat', self.ticks))
        return self.accept

    def send_equip(self, id):
        self.events.append(('equip', id))
        return self.accept

    def attack(self, op):
        self.events.append(('attack', self.ticks))
        return True

    def walk_click(self, tile):
        self.events.append(('walk', tile))
        return True

    def toggle(self, name, on):
        self.events.append(('prayer', name, on))
        if on:
            self.active_prayers.add(name)
        else:
            self.active_prayers.discard(name)
        return True

    def escape(self):
        self.events.append(('escape', self.ticks))
        self.at = Tile(2757, 3478)
        return True
        yield

    def run(self, ticks=0):
        self.ticks += ticks
        self.clock += ticks * 600
        self.heartbeat()
        run_wait(self.bot.loop())


def eat_and_attack(hp):
    world = QueenWorld()
    world.hp = hp
    world.run()
    assert world.bot.stage == 'fight', str(world.lines)
    expect(world.bot.retreats).to_be(0)
    expect(('eat', 100) in world.events).to_be(True)
    expect(('attack', 100) in world.events).to_be(True)


test_each([45, 15])('food and a renewed attack share a tick without retreating at hp=%s', eat_and_attack)


def food_cooldown(confirmed):
    world = QueenWorld()
    world.run()
    if confirmed:
        world.food -= 1
    for n in range(1, 4 if confirmed else 5):
        world.run(1)
    eats = [event for event in world.events if event[0] == 'eat']
    expect(eats).to_equal([('eat', 100), ('eat', 103 if confirmed else 104)])
    expect(world.bot.stage).to_be('fight')


test_each([True, False])('confirmed food cools down three ticks and unconfirmed food retries after four: %s', food_cooldown)


def rejected_food():
    world = QueenWorld()
    world.accept = False
    world.run()
    world.run(1)
    expect([event for event in world.events if event[0] == 'eat']).to_equal([('eat', 100), ('eat', 101)])
    expect(world.bot.pending_food).to_be_null()


test('a rejected food send can retry next tick without stopping combat', rejected_food)


def late_food():
    world = QueenWorld()
    world.run()
    world.run(2)
    world.food -= 1
    world.run(1)
    world.run(1)
    expect([event for event in world.events if event[0] == 'eat']).to_equal([('eat', 100)])
    world.run(1)
    expect([event for event in world.events if event[0] == 'eat']).to_equal([('eat', 100), ('eat', 105)])


test('late food confirmation extends the cooldown without repeating the pending action', late_food)


def missing_weapon():
    world = QueenWorld()
    world.worn_ids.discard(MACE)
    world.run()
    expect(world.bot.stage).to_be('retreat')
    expect(world.bot.restocking).to_be(True)


test('a missing phase weapon restocks only its owner', missing_weapon)


def delayed_weapon(accepted):
    world = QueenWorld()
    world.worn_ids.discard(MACE)
    world.carried[MACE] = 1
    world.accept = accepted
    world.run()
    world.run(1)
    equips = [event for event in world.events if event[0] == 'equip']
    expect(len(equips)).to_be(1 if accepted else 2)
    world.accept = True
    world.worn_ids.add(MACE)
    world.run(1)
    expect(world.bot.weapon_request).to_be_null()
    expect(world.bot.stage).to_be('fight')
    expect(any([event[0] == 'attack' for event in world.events])).to_be(True)


test_each([True, False])('a delayed/rejected phase equip leaves food available and waits before retrying: %s', delayed_weapon)


def pending_protection():
    world = QueenWorld()
    world.active_prayers.clear()
    spy_on(prayer, 'toggle', impl=lambda name, on: world.events.append(('prayer', name, on)) or True)
    world.run()
    world.run(1)
    expect(len([event for event in world.events if event == ('prayer', PROTECT_FROM_MAGIC, True)])).to_be(1)
    expect(any([event[0] == 'eat' for event in world.events])).to_be(True)
    expect(any([event[0] == 'attack' for event in world.events])).to_be(False)
    world.active_prayers.add(PROTECT_FROM_MAGIC)
    world.run(1)
    expect(any([event[0] == 'attack' for event in world.events])).to_be(True)
    expect(world.bot.protection_failures).to_be(0)


test('pending protection permits food but suppresses unprotected attacks and duplicate toggles', pending_protection)


def healthy_food_threshold():
    world = QueenWorld()
    world.hp = 51
    world.run()
    expect(any([event[0] == 'eat' for event in world.events])).to_be(False)
    world.hp = 50
    world.run(1)
    expect(('eat', 101) in world.events).to_be(True)


test('a level-70 fighter saves a shark until it can heal twenty hitpoints', healthy_food_threshold)


def phase_changes_while_equipping():
    world = QueenWorld()
    world.worn_ids.discard(BOW)
    world.carried[MACE] = 1
    world.carried[BOW] = 1
    expect(world.bot.equip_weapon(BOW)).to_be(False)
    world.ticks += 4
    expect(world.bot.equip_weapon(MACE)).to_be(False)
    expect([event for event in world.events if event[0] == 'equip']).to_equal([('equip', BOW)])
    world.worn_ids.add(BOW)
    world.worn_ids.discard(MACE)
    world.ticks += 4
    expect(world.bot.equip_weapon(MACE)).to_be(False)
    expect([event for event in world.events if event[0] == 'equip']).to_equal([('equip', BOW), ('equip', MACE)])
    world.worn_ids.add(MACE)
    world.ticks += 1
    expect(world.bot.equip_weapon(MACE)).to_be(True)


test('a phase change waits for an earlier pending weapon acknowledgement', phase_changes_while_equipping)


def offensive_prayers_do_not_block():
    world = QueenWorld()
    spy_on(prayer, 'toggle', impl=lambda name, on: world.events.append(('prayer', name, on)) or False)
    world.run()
    expect(('eat', 100) in world.events).to_be(True)
    expect(('attack', 100) in world.events).to_be(True)
    expect(world.bot.stage).to_be('fight')


test('pending or failed offensive prayers do not block food or attacks', offensive_prayers_do_not_block)


def special_does_not_wait():
    world = QueenWorld()
    spy_on(prayer, 'toggle', returns=True)
    spy_on(special, 'ready', returns=True)
    spy_on(special, 'armed', returns=False)
    spy_on(special, 'bar_component', returns=123)
    clicked = spy_on(_core, 'click_component', returns=True)
    world.run()
    expect(('eat', 100) in world.events).to_be(True)
    expect(('attack', 100) in world.events).to_be(True)
    expect(world.ticks).to_be(100)
    world.run(1)
    expect(clicked.calls).to_equal([(123,)])


test('special and offensive prayer acknowledgements do not delay same-tick food and attack or repeat pending toggles', special_does_not_wait)


def protection_retries(accepted):
    world = QueenWorld()
    world.active_prayers.clear()
    spy_on(prayer, 'toggle', impl=lambda name, on: world.events.append(('prayer', name, on)) or accepted)
    expect(world.bot.protect()).to_be(False)
    for n in range(3):
        world.ticks += 10 if accepted else 1
        world.bot.protect()
    expect(world.bot.stage).to_be('retreat')
    expect(world.bot.restocking).to_be(True)


test_each([True, False])('repeated unconfirmed/rejected protection eventually restocks only its owner: %s', protection_retries)


def late_second_protection():
    world = QueenWorld()
    world.active_prayers.clear()
    spy_on(prayer, 'toggle', returns=True)
    world.bot.protect()
    world.ticks += 10
    world.bot.protect()
    world.ticks += 1
    world.active_prayers.add(PROTECT_FROM_MAGIC)
    expect(world.bot.protect()).to_be(True)
    expect(world.bot.stage).to_be('fight')
    expect(world.bot.protection_failures).to_be(0)


test('late second protection acknowledgement is observed before another request or retreat', late_second_protection)


def delayed_prayer_off():
    world = QueenWorld()
    toggles = spy_on(prayer, 'toggle', returns=True)
    expect(world.bot.clear_prayers()).to_be(False)
    world.ticks += 1
    expect(world.bot.clear_prayers()).to_be(False)
    expect(len(toggles.calls)).to_be(1)
    expect(world.bot.queue_combat_food()).to_be(True)
    world.active_prayers.clear()
    expect(world.bot.clear_prayers()).to_be(True)


test('a delayed prayer-off toggle is not repeated and does not block food', delayed_prayer_off)


def zero_prayer(hp):
    world = QueenWorld()
    world.hp = hp
    world.prayer_points = 0
    world.active_prayers.clear()

    def drink(name):
        world.events.append(('restore', world.ticks))
        world.prayer_points = 60
        return True
        yield

    spy_on(kq, 'drink', impl=drink)
    world.run()
    if hp > 31:
        expect(world.events).to_equal([('restore', 100)])
    else:
        expect(world.events).to_equal([('eat', 100)])
        world.food -= 1
        world.hp += 20
        world.run(1)
        world.run(1)
        world.run(1)
        expect(('restore', 103) in world.events).to_be(True)
    expect(world.bot.stage).to_be('fight')


test_each([45, 20])('zero prayer restores before routine food but after critical food, hp=%s', zero_prayer)


def bank_interrupt(failure):
    world = QueenWorld()
    world.hp = 99
    world.prayer_points = 99
    spy_on(skills, 'level', returns=99)
    spy_on(prayer, 'max', returns=99)
    spy_on(prayer, 'clear', impl=lambda: result(True))
    spy_on(equipment, 'items', returns=[Fake(id=id, count=250 if id == supply.ARROWS else 1, name=str(id)) for id in supply.GEAR])
    state = [False, 0]

    def open_bank(**options):
        state[0] = True
        return True
        yield

    def close_bank():
        state[0] = False
        return True
        yield

    def deposit(matches):
        state[1] += 1
        if failure == 'deposit' and state[1] == 3:
            state[0] = False
        return
        yield

    def withdraw(id, count, lands_as_id=None):
        state[0] = False
        return False
        yield

    spy_on(banking, 'open', impl=open_bank)
    spy_on(bank, 'wait_ready', impl=lambda timeout_ms=4000: result(state[0]))
    spy_on(bank, 'is_open', impl=lambda: state[0])
    spy_on(bank, 'close', impl=close_bank)
    spy_on(bank, 'set_note_mode', impl=lambda on: result(True))
    spy_on(bank, 'deposit_all_matching', impl=deposit)
    spy_on(bank, 'count_by_id', impl=lambda id: (0 if failure == 'shortage' and id == BOW else 1000) if state[0] else 0)
    spy_on(bank, 'withdraw_x_by_id', impl=withdraw)
    if failure == 'shortage':
        try:
            run_wait(supply.provision(1, world.log))
            raise AssertionError('an open-bank bow shortage must be reported')
        except supply.BankShortage as error:
            expect(str(error)).to_contain('item 861')
    else:
        expect(run_wait(supply.provision(1, world.log))).to_be(False)
        expect(world.logged('interrupted, retrying KQ supplies')).to_be(True)


test_each(['deposit', 'withdrawal', 'shortage'])('KQ provision distinguishes bank interruption from real shortage: %s', bank_interrupt)


def valuable_loot():
    world = QueenWorld()
    world.hp = 70
    world.drop()
    world.run()
    expect(any([event[0] == 'take' for event in world.events])).to_be(False)
    world.run(1)
    expect(('take', 1113, 101) in world.events).to_be(True)
    expect(world.bot.looted).to_be(0)
    world.carried[1113] = 1
    world.ground = []
    world.run(1)
    expect(world.bot.looted).to_be(1)
    expect(world.bot.stage).to_be('fight')
    expect(PROTECT_FROM_MAGIC in world.active_prayers).to_be(True)


test('late public valuable loot is elected and counted only after an inventory acknowledgement', valuable_loot)


def loot_priority():
    world = QueenWorld()
    world.hp = 70
    for id, name in [[892, 'Rune arrow'], [884, 'Iron arrow'], [888, 'Mithril arrow'], [565, 'Blood rune'], [1731, 'Amulet of power']]:
        world.drop(id, name)
    world.run()
    world.run(1)
    expect([event[1] for event in world.events if event[0] == 'take']).to_equal([1731])


test('valuable equipment outranks consumables and arrows never interrupt live queen combat', loot_priority)


def missing_loot(late_inventory):
    world = QueenWorld()
    world.hp = 70
    world.drop()
    world.run()
    world.run(1)
    world.ground = []
    world.run(1)
    if late_inventory:
        world.carried[1113] = 1
    world.run(4)
    expect(world.bot.looted).to_be(1 if late_inventory else 0)
    expect(len([event for event in world.events if event[0] == 'take'])).to_be(1)
    expect(world.bot.collector.claim()).to_be_null()
    expect(world.bot.retreats).to_be(0)


test_each([False, True])('vanished loot releases after grace, while a late inventory update still confirms: %s', missing_loot)


def moving_pickup():
    world = QueenWorld()
    world.hp = 70
    world.drop()
    world.run()
    world.run(1)
    for n in range(6):
        world.at = Tile(world.at.x + 1, world.at.z)
        world.run(1)
    world.hp = 20
    world.run(1)
    expect(('eat', 108) in world.events).to_be(True)
    expect(world.bot.collector.claim()).not_.to_be_null()
    world.carried[1113] = 1
    world.ground = []
    world.run(1)
    expect(world.bot.looted).to_be(1)


test('a distant accepted pickup survives movement while emergency food remains available', moving_pickup)


def full_loot_pack(kind):
    world = QueenWorld()
    world.hp = 70
    world.pack_counts = True
    for n in range(28):
        world.item(FOOD if kind != 'reserve' or n < 2 else 557, 'Shark' if kind != 'reserve' or n < 2 else 'Earth rune')
    if kind == 'vial':
        world.pack.pop()

        def drop_vial(op):
            world.events.append(('drop', 229, world.ticks))
            return True

        world.item(229, 'Vial', effect=drop_vial)
    world.drop(565 if kind == 'consumable' else 1113, 'Blood rune' if kind == 'consumable' else 'Rune chainbody')
    world.run()
    world.run(1)
    if kind == 'vial':
        expect([event for event in world.events if event[0] == 'drop']).to_equal([('drop', 229, 101)])
        world.run(1)
        expect(len([event for event in world.events if event[0] == 'drop'])).to_be(1)
        world.take(229)
    elif kind == 'food':
        expect([event for event in world.events if event[0] == 'eat']).to_equal([('eat', 101)])
        world.pack.pop()
    else:
        expect(any([event[0] in ['take', 'drop', 'eat'] for event in world.events])).to_be(False)
        return
    world.run(1)
    expect(any([event[0] == 'take' for event in world.events])).to_be(True)


test_each(['vial', 'food', 'reserve', 'consumable'])('full-pack loot makes only safe confirmed room: %s', full_loot_pack)


def stacked_loot(noted):
    world = QueenWorld()
    world.hp = 70
    world.pack_counts = True
    id = 1620 if noted else 565
    name = 'Uncut ruby' if noted else 'Blood rune'
    for n in range(27):
        world.item(FOOD, 'Shark')
    world.item(id, name, 5)
    spy_on(reader, 'item_type', returns=Fake(stackable=True))
    world.drop(id, name)
    world.run()
    world.run(1)
    expect(('take', id, 101) in world.events).to_be(True)
    expect(any([event[0] in ['drop', 'eat'] for event in world.events])).to_be(False)


test_each([False, True])('an existing stack uses actual metadata and fits a full pack, noted=%s', stacked_loot)


def arrow_sweep(confirmed_kill):
    world = QueenWorld()
    world.hp = 70
    world.npcs = []
    if confirmed_kill:
        world.bot.queen_tracker.killed_at = world.now()
        world.bot.last_kill_tick = world.ticks
    world.drop(892, 'Rune arrow')
    world.run()
    world.run(1)
    world.run(1)
    expect(any([event[0] == 'take' for event in world.events])).to_be(confirmed_kill)
    if confirmed_kill:
        expect(len(world.active_prayers)).to_be(0)


test_each([False, True])('Rune-arrow sweeps require a confirmed kill and keep prayers off: %s', arrow_sweep)


def arrow_sweep_interrupted(reason):
    world = QueenWorld()
    world.hp = 70
    world.npcs = []
    world.bot.queen_tracker.killed_at = world.now()
    world.bot.last_kill_tick = world.ticks
    world.drop(892, 'Rune arrow')
    world.run()
    world.run(1)
    if reason == 'valuable':
        world.drop()
    elif reason == 'queen':
        world.npcs = [world.queen]
    elif reason == 'expiry':
        world.ticks += 121
    else:
        world.bot.retreat('test retreat')
        expect(world.bot.collector.claim()).to_be_null()
        return
    world.run(1)
    expect(world.bot.collector.claim()).to_be_null()


test_each(['valuable', 'queen', 'expiry', 'retreat'])('an existing arrow sweep yields to %s', arrow_sweep_interrupted)


def failed_pickup_backs_off():
    world = QueenWorld()
    world.hp = 70
    world.accept = False
    world.drop()
    world.run()
    for n in range(18):
        world.run(1)
    expect(world.bot.collector.claim()).to_be_null()
    expect(world.bot.looted).to_be(0)
    expect(len([event for event in world.events if event[0] == 'take']) <= 4).to_be(True)


test('unacknowledged pickups back off after bounded attempts and ordinary combat resumes', failed_pickup_backs_off)


def pending_food_cooldown():
    world = QueenWorld()
    world.hp = 70
    world.pack_counts = True
    for n in range(28):
        world.item(FOOD, 'Shark')
    world.bot.next_eat_tick = 103
    world.drop()
    world.run()
    world.run(1)
    world.run(1)
    expect(any([event[0] in ['eat', 'drop'] for event in world.events])).to_be(False)
    world.run(1)
    expect(('eat', 103) in world.events).to_be(True)
    world.pack.pop()
    world.run(1)
    expect(('take', 1113, 104) in world.events).to_be(True)


test('room-making food respects the existing combat cooldown without abandoning valuable gear', pending_food_cooldown)


def pending_combat_food(stackable):
    world = QueenWorld()
    world.pack_counts = True
    for n in range(27):
        world.item(FOOD, 'Shark')
    if stackable:
        world.item(565, 'Blood rune', 5)
        spy_on(reader, 'item_type', returns=Fake(stackable=True))
    else:
        world.item(229, 'Vial', effect=lambda op: world.events.append(('drop', 229, world.ticks)) or True)
    world.drop(565 if stackable else 1113, 'Blood rune' if stackable else 'Rune chainbody')
    world.run()
    world.run(1)
    expect(any([event[0] == 'drop' for event in world.events])).to_be(False)
    expect(any([event[0] == 'take' for event in world.events])).to_be(stackable)


test_each([False, True])('pending combat food reserves its future free slot but permits existing stacks: %s', pending_combat_food)


def loot_waits_for_entry():
    world = QueenWorld()
    world.hp = 70
    world.bot.entry_at = world.now()
    world.peer_overrides['two'] = {'stage': 'upper', 'tile': {'x': UPPER.x, 'z': UPPER.z, 'level': 2}}
    world.drop()
    world.run()
    world.run(1)
    expect(any([event[0] == 'take' for event in world.events])).to_be(False)
    expect(world.bot.retreats).to_be(0)


test('loot waits until every active fighter has finished chamber entry', loot_waits_for_entry)


def private_collector(other_collecting):
    world = QueenWorld()
    world.hp = 70
    world.bot.party = Party(['one', 'two', 'three', 'four'], 'two', 'two')
    world.drop()
    if other_collecting:
        world.peer_overrides['one'] = {'loot': {'id': 1113, 'name': 'Rune chainbody',
            'tile': {'x': 3495, 'z': 9493, 'level': 0}, 'collecting': True}}
    world.heartbeat()
    world.bot.loot()
    world.ticks += 1
    world.heartbeat()
    world.bot.loot()
    expect(any([event[0] == 'take' for event in world.events])).to_be(not other_collecting)


test_each([False, True])('a private drop elects its visible later member unless another collector owns it: %s', private_collector)


def unknown_respawn_keeps_protection():
    world = QueenWorld()
    world.hp = 70
    world.queen._fields['health'] = 0
    world.queen._fields['max_health'] = 0
    world.bot.queen_tracker.killed_at = world.now()
    world.bot.last_kill_tick = world.ticks
    world.drop()
    world.run()
    world.run(1)
    expect(PROTECT_FROM_MAGIC in world.active_prayers).to_be(True)
    expect(('take', 1113, 101) in world.events).to_be(True)


test('an unknown respawn health bar preserves protection during collection', unknown_respawn_keeps_protection)


def ignored_events(name):
    world = QueenWorld()
    guardian = _RandomEvents()
    event = Fake(name=name, key=lambda: name)
    spy_on(guardian, '_detect_raw', returns=event)
    guardian.configure(world.bot)
    expect(guardian.detect()).to_be_null()
    world.at = route.CAMELOT
    world.bot.stage = 'retreat'
    guardian.configure(world.bot)
    expect(guardian.detect()).to_be_null()
    world.bot.stage = 'bank'
    guardian.configure(world.bot)
    expect(guardian.detect()).to_be(event)


test_each(['genie', 'strange plant'])('%s cannot block fighting/escape and becomes available again at safety', ignored_events)


def poison_and_boosts(where):
    world = QueenWorld()
    world.hp = 99
    world.bot.stage = 'travel'
    world.at = Tile(3483, 9510, 2) if where != 'surface' else Tile(3270, 3110)
    drinks = spy_on(kq, 'drink', impl=lambda name: result(True))
    boost = spy_on(kq, 'boost', impl=lambda melee: result(True))
    spy_on(kq, 'doses', returns=4)
    world.bot.last_dose = world.now()
    if where == 'poisoned':
        world.bot.poisoned = True
    if where == 'moving':
        world.bot.walk_tile = Tile(world.at.x - 1, world.at.z, world.at.level)
    run_wait(world.bot.upkeep(where in ['surface', 'moving']))
    if where == 'poisoned':
        expect(drinks.calls).to_equal([('Superantipoison',)])
        expect(boost.calls).to_equal([])
    else:
        expect(boost.calls).to_equal([(True,)] if where == 'moving' else [])
    expect(world.bot.stage).to_be('travel')


test_each(['surface', 'stationary', 'moving', 'poisoned'])('cavern upkeep respects movement and observed poison: %s', poison_and_boosts)


def visible_respawn_before_food():
    world = QueenWorld()
    world.active_prayers.clear()
    world.run()
    protected = world.events.index(('prayer', PROTECT_FROM_MAGIC, True))
    eaten = world.events.index(('eat', 100))
    expect(protected < eaten).to_be(True)


test('a visible respawn restores protection before routine food upkeep', visible_respawn_before_food)


def transformation_protection(confirmed_kill):
    world = QueenWorld()
    world.hp = 70
    world.npcs = []
    if confirmed_kill:
        world.bot.queen_tracker.killed_at = world.now()
        world.bot.last_kill_tick = world.ticks
    run_wait(world.bot.upkeep())
    expect(PROTECT_FROM_MAGIC in world.active_prayers).to_be(not confirmed_kill)


test_each([False, True])('transformation gaps preserve protection; confirmed kills clear it: %s', transformation_protection)


def own_visitor(stage):
    world = QueenWorld()
    world.bot.stage = stage
    world.at = UPPER if stage == 'upper' else world.at
    world.npc('Genie', ['Talk-to'], targets_me=True)
    expect(world.bot.check_safety()).to_be(True)
    expect(world.bot.stage).to_be('retreat')
    expect(world.bot.restocking).to_be(stage == 'fight')


test_each(['fight', 'upper'])('an owned visitor retires the affected fighter before continuing %s', own_visitor)


def food_exhaustion():
    world = QueenWorld()
    world.food = 1
    expect(world.bot.check_safety()).to_be(True)
    expect(world.bot.restocking).to_be(True)
    expect(world.bot.party.unsafe(1, world.now())).to_be(False)
    expect(world.bot.collector.claim()).to_be_null()


test('food exhaustion restocks only its owner and immediately releases any loot claim', food_exhaustion)


def dead_respawn_returns_to_bank():
    world = QueenWorld()
    world.at = Tile(3221, 3218)
    world.bot.death = DeathReport(world.now(), Tile(3477, 9493), [RecoveryItem(BOW, 1)], [])
    world.bot.stage = 'retreat'
    spy_on(prayer, 'clear', impl=lambda: result(True))
    run_wait(world.bot.escape())
    expect(world.bot.stage).to_be('bank')
    expect(world.bot.prepared).to_be(False)


test('a respawned dead fighter banks without requiring lost teleport supplies', dead_respawn_returns_to_bank)


def server_position_death():
    world = QueenWorld()
    world.bot.observe_death()
    world.at = route.CAMELOT
    world.hp = 0
    world.bot.observe_death()
    expect(world.bot.death.tile).to_equal(route.CAMELOT)
    expect(world.bot.restocking).to_be(True)


test('a queued hit after teleport records the new death tile rather than the old chamber', server_position_death)


def recovery_provision_waits(short_arrows):
    world = QueenWorld()
    world.hp = 70
    world.prayer_points = 70
    spy_on(prayer, 'clear', impl=lambda: result(True))
    spy_on(banking, 'open', impl=lambda **opts: result(True))
    spy_on(bank, 'wait_ready', impl=lambda timeout_ms=4000: result(True))
    deposited = spy_on(bank, 'deposit_all_matching', impl=lambda predicate: result(True))
    spy_on(bank, 'count_by_id', returns=1 if short_arrows else 0)
    withdrawn = spy_on(bank, 'withdraw_x_by_id', impl=lambda id, count: result(True))
    if short_arrows:
        spy_on(equipment, 'items', returns=[Fake(id=id, count=1, name='') for id in supply.GEAR])
        spy_on(bank, 'close', impl=lambda: result(True))
        spy_on(bank, 'set_note_mode', impl=lambda on: result(True))
    expect(run_wait(supply.provision(3, world.log, True))).to_be(False)
    expect(len(deposited.calls) >= 1).to_be(True)
    expect(withdrawn.calls).to_equal([])


test_each([False, True])('death provisioning deposits survivors before waiting for missing gear/arrows: %s', recovery_provision_waits)


def gate_world(gate='upper'):
    world = QueenWorld()
    world.hp = 70
    world.at = UPPER if gate == 'upper' else SURFACE
    world.bot.stage = gate
    for name in ['two', 'three', 'four']:
        world.peer_overrides[name] = {'stage': gate}
    world.heartbeat()
    spy_on(world.bot, 'together', returns=True)
    spy_on(kq, 'boosts_ready', returns=True)
    spy_on(kq, 'rope_ready', returns=True)
    return world


def accepted_gate(low_hp):
    world = gate_world()
    world.hp = 20 if low_hp else 70
    world.bot.party.accept(world.bot.party.release('upper', 1, world.now()), world.now())
    spy_on(kq, 'boosts_ready', returns=False)
    boosted = spy_on(kq, 'boost', impl=lambda melee: result(True))

    def descend(gate):
        world.at = Tile(3508, 9493)
        return True
        yield

    descending = spy_on(kq, 'descend', impl=descend)
    world.run()
    expect(descending.calls).to_equal([('upper',)])
    expect(boosted.calls).to_equal([])
    expect(world.bot.stage).to_be('fight')
    expect(world.bot.entries).to_be(1)
    world.bot.observe_descent()
    expect(world.bot.entries).to_be(1)


test_each([False, True])('accepted rope release precedes decayed boosts and low-HP upkeep: %s', accepted_gate)


def timed_descent_arrival():
    world = gate_world()
    world.bot.party.accept(world.bot.party.release('upper', 1, world.now()), world.now())
    descending = spy_on(kq, 'descend', impl=lambda gate: result(False))
    run_wait(world.bot.step())
    run_wait(world.bot.step())
    expect(len(descending.calls)).to_be(2)
    expect(world.bot.descent).to_be('upper')
    world.at = Tile(3508, 9493)
    world.bot.observe_descent()
    world.bot.observe_descent()
    expect(world.bot.stage).to_be('fight')
    expect(world.bot.entries).to_be(1)


test('a timed-out released descent retries before upkeep and counts a late landing only once', timed_descent_arrival)


def aborted_release():
    world = gate_world()
    world.bot.party.accept(world.bot.party.release('upper', 1, world.now()), world.now())
    world.peer_overrides['two'] = {'stage': 'retreat', 'ready': False}
    world.heartbeat()
    descending = spy_on(kq, 'descend', impl=lambda gate: result(True))
    expect(run_wait(world.bot.enter_released_gate())).to_be(False)
    world.peer_overrides['two'] = {'stage': 'upper', 'ready': True}
    world.heartbeat()
    expect(run_wait(world.bot.enter_released_gate())).to_be(False)
    expect(descending.calls).to_equal([])


test('an aborted release cannot enter after a peer advertises ready again', aborted_release)


def late_team_member():
    world = gate_world('surface')
    world.peer_overrides['four'] = {'stage': 'travel'}
    placed = spy_on(kq, 'place_rope', impl=lambda gate, log: result(True))
    descending = spy_on(kq, 'descend', impl=lambda gate: result(False))
    for n in range(3):
        world.heartbeat()
        run_wait(world.bot.gate('surface'))
        world.clock += 41000
    expect(placed.calls).to_equal([])
    expect(descending.calls).to_equal([])
    world.peer_overrides['four'] = {'stage': 'surface'}
    world.heartbeat()
    run_wait(world.bot.gate('surface'))
    expect(len(placed.calls)).to_be(1)
    expect(descending.calls).to_equal([('surface',)])


test('a delayed teammate cannot consume ropes until all four rendezvous at the gate', late_team_member)


def peer_upkeep_during_rope():
    world = gate_world('surface')

    def place(gate, log):
        world.peer_overrides['two'] = {'stage': 'travel'}
        world.heartbeat()
        return True
        yield

    spy_on(kq, 'place_rope', impl=place)
    descending = spy_on(kq, 'descend', impl=lambda gate: result(True))
    run_wait(world.bot.gate('surface'))
    expect(world.bot.party.released('surface', 1, world.now())).to_be(False)
    expect(descending.calls).to_equal([])


test('a peer starting upkeep during rope placement cancels the pending entrance release', peer_upkeep_during_rope)


def gate_upkeep(kind):
    world = gate_world()
    observed = []

    def sip(name):
        observed.append(world.bot.stage)
        return True
        yield

    if kind == 'food':
        world.hp = 45
        spy_on(kq, 'eat', impl=lambda: sip('food'))
        run_wait(world.bot.upkeep())
    else:
        world.bot.last_dose = 0
        spy_on(kq, 'drink', impl=sip)
        run_wait(world.bot.gate('upper'))
    expect(observed).to_equal(['travel'])
    expect(world.bot.stage).to_be('travel')


test_each(['food', 'antipoison'])('%s at the upper rope withdraws rendezvous readiness before waiting', gate_upkeep)


def release_during_sip():
    world = gate_world()
    world.bot.last_dose = 0

    def drink(name):
        world.bot.stage = 'upper'
        world.heartbeat()
        world.bot.party.accept(world.bot.party.release('upper', 1, world.now()), world.now())
        return True
        yield

    drinks = spy_on(kq, 'drink', impl=drink)
    run_wait(world.bot.gate('upper'))

    def descend(gate):
        world.at = Tile(3508, 9493)
        return True
        yield

    descending = spy_on(kq, 'descend', impl=descend)
    run_wait(world.bot.step())
    expect(len(drinks.calls)).to_be(1)
    expect(descending.calls).to_equal([('upper',)])
    expect(world.bot.stage).to_be('fight')


test('a release received during a sip enters next loop before another boost or sip', release_during_sip)


def approaching_rope():
    world = gate_world('surface')
    world.at = Tile(SURFACE.x + 2, SURFACE.z - 2)
    walking = spy_on(kq, 'walk', impl=lambda tile, radius, log: result(True))
    run_wait(world.bot.gate('surface'))
    expect(world.bot.stage).to_be('travel')
    expect(walking.calls[0][0]).to_equal(SURFACE)
    expect(walking.calls[0][1]).to_be(0)


test('a member approaching a rope remains travelling rather than releasing the team', approaching_rope)


def banking_member_not_barrier():
    world = QueenWorld()
    world.hp = 70
    world.bot.last_attack = 0
    world.peer_overrides['two'] = {'stage': 'bank', 'restocking': True, 'ready': False}
    world.run()
    expect(world.bot.stage).to_be('fight')
    expect(('attack', 100) in world.events).to_be(True)


test('a member banking independently does not hold remaining fighters at the entry barrier', banking_member_not_barrier)


def formation_before_optional_prayers():
    world = QueenWorld()
    world.hp = 70
    world.at = Tile(3470, 9495)
    world.run()
    expect(any([event[0] == 'walk' for event in world.events])).to_be(True)
    expect(any([event[0] == 'prayer' for event in world.events])).to_be(False)


test('approaching a visible queen spreads into formation before optional offensive prayers', formation_before_optional_prayers)



def blocked_queen(engaged=False):
    world = QueenWorld()
    world.hp = 70
    world.at = Tile(3480, 9498)
    centre = Tile(3477, 9509)
    world.queen._fields.update({'id': 1160, 'network_tile': lambda: centre, 'tile': lambda: centre,
                                'targets_me': lambda: engaged, 'target': ('player', 1) if engaged else None})
    spy_on(reachability, 'walkable', impl=lambda p: not (p.x > 3477 and p.z == 9509))
    spy_on(reachability, 'can_reach', returns=True)
    spy_on(reachability, 'can_step', returns=True)
    world.heartbeat()
    world.bot.observe_queen()
    return world


def blocked_approach():
    world = blocked_queen()
    run_wait(world.bot.fight())
    expect(world.bot.stage).to_be('fight')
    expect(world.bot.blocked).to_be(True)
    target = [event[1] for event in world.events if event[0] == 'walk'][-1]
    expect(max(abs(target.x - 3477), abs(target.z - 9509))).to_be(6)


test('a blocked cross approaches the unengaged queen before searching elsewhere', blocked_approach)


def body_wide_pull():
    world = blocked_queen(True)
    stepped = spy_on(reachability, 'can_step', returns=True)
    run_wait(world.bot.fight())
    expect(world.bot.sighting.engaged).to_be(True)
    target = [event[1] for event in world.events if event[0] == 'walk'][-1]
    expect(target.equals(Tile(3477, 9495))).to_be(True)
    expect(any([call[0].equals(Tile(3479, 9511)) and call[1].equals(Tile(3479, 9510)) for call in stepped.calls])).to_be(True)


test('an engaged queen pull checks steps for the whole five-wide body', body_wide_pull)


def stationary_reacquisition():
    world = blocked_queen(True)
    run_wait(world.bot.fight())
    queen = world.queen
    world.npcs = []
    world.clock += 9000
    world.heartbeat()
    world.bot.observe_queen()
    run_wait(world.bot.fight())
    world.heartbeat()
    run_wait(world.bot.fight())
    expect(world.bot.lure_at).to_be(0)
    world.npcs = [queen]
    world.heartbeat()
    world.bot.observe_queen()
    run_wait(world.bot.fight())
    expect(world.bot.lure_at).to_be(world.now())
    world.clock += 16000
    world.heartbeat()
    world.bot.observe_queen()
    run_wait(world.bot.fight())
    expect(world.bot.lure_attempt).to_be(1)
    expect(world.bot.stage).to_be('fight')


test('reacquiring a stationary queen restarts the pull retry timer', stationary_reacquisition)


def sighting_persists():
    world = blocked_queen()
    world.npcs = []
    world.bot.observe_queen()
    expect(world.bot.blocked).to_be(True)
    expect(world.bot.sighting.tile.equals(Tile(3477, 9509))).to_be(True)


test('a blocked queen leaving view retains her last observed position', sighting_persists)


def peer_sighting():
    world = QueenWorld()
    world.hp = 70
    world.npcs = []
    world.at = Tile(3508, 9493)
    world.peer_overrides['two'] = {'blocked': True, 'queen': {'id': 1160, 'tile': {'x': 3478, 'z': 9510, 'level': 0},
        'at': world.now(), 'engaged': False}}
    spy_on(reachability, 'can_reach', returns=True)
    world.heartbeat()
    run_wait(world.bot.fight())
    expect(world.bot.status).to_be('searching the last reported queen position')
    target = [event[1] for event in world.events if event[0] == 'walk'][-1]
    expect(max(abs(target.x - 3478), abs(target.z - 9510))).to_be(6)
    expect(world.bot.party.unsafe(1, world.now())).to_be(False)


test('an unseen queen can be approached from a peer sighting without group abort', peer_sighting)


def remote_aggression():
    world = blocked_queen()
    world.queen._fields['target'] = ('player', 2)
    world.peer_overrides['two'] = {'player_slot': 2}
    spy_on(reader, 'players', returns=[])
    world.heartbeat()
    world.bot.observe_queen()
    expect(world.bot.sighting.engaged).to_be(True)


test('queen aggression recognizes party slots beyond local player visibility', remote_aggression)


def empty_search():
    world = QueenWorld()
    world.hp = 70
    world.npcs = []
    world.at = Tile(3488, 9496)
    spy_on(reachability, 'can_reach', returns=True)
    world.heartbeat()
    run_wait(world.bot.fight())
    target = [event[1] for event in world.events if event[0] == 'walk'][-1]
    expect(target.equals(world.at)).to_be(False)
    expect(world.bot.status).to_be('searching the queen chamber')
    expect(world.bot.stage).to_be('fight')


test('an empty central waypoint advances the chamber search', empty_search)



def recovery_world():
    world = QueenWorld()
    world.hp = 70
    death = DeathReport(world.now(), world.at, [RecoveryItem(BOW, 1)], [])
    world.peer_overrides['two'] = {'stage': 'retreat', 'ready': False, 'restocking': True, 'death': death.to_message()}
    world.peer_overrides['three'] = {'recovery_space': 4}
    world.peer_overrides['four'] = {'recovery_space': 4}
    world.heartbeat()
    return world


def recovery_election():
    world = recovery_world()
    original = world.bot.party
    world.bot.party = Party(original.roster, 'three', 'three')
    spot = {'x': world.at.x, 'z': world.at.z, 'level': 0}
    for name in original.roster:
        message = {'name': name, 'session': name, 'trip': 1, 'stage': 'fight', 'ready': True, 'tile': spot, 'recovery_space': 4}
        message.update(world.peer_overrides.get(name, {}))
        world.bot.party.receive(message, world.now())
    expect(run_wait(world.bot.recover_loot())).to_be(False)
    expect(world.events).to_equal([])
    world.bot.party.receive({'name': 'one', 'session': 'one', 'trip': 1, 'stage': 'retreat', 'ready': False,
                             'restocking': True, 'tile': spot, 'recovery_space': 0}, world.now())
    expect(run_wait(world.bot.recover_loot())).to_be(True)
    expect(world.bot.status).to_contain('recovering two')


test('only the first survivor with recovery space leaves formation for teammate gear', recovery_election)


def confirmed_gear_recovery(acknowledged):
    world = recovery_world()
    world.active_prayers.clear()
    drop = world.drop(BOW, 'Magic shortbow', world.at)

    def take(op):
        world.events.append(('take', BOW))
        if acknowledged:
            world.carried[BOW] = 1
            world.ground = []
        return True

    drop._fields['interact'] = take
    drop._fields['count'] = 1
    expect(run_wait(world.bot.recover_loot())).to_be(True)
    expect(any([event[0] == 'take' for event in world.events])).to_be(False)
    expect(run_wait(world.bot.recover_loot())).to_be(True)
    expect(len(world.bot.recovered_items)).to_be(1 if acknowledged else 0)
    if acknowledged:
        expect(world.bot.loot_counts.get('Recovered for two: Magic shortbow')).to_be(1)
        expect(world.bot.recovered_items[0].owner).to_be('two')
        world.ticks += 13
        run_wait(world.bot.recover_loot())
        run_wait(world.bot.recover_loot())
        expect(world.bot.stage).to_be('retreat')
        expect(world.bot.restocking).to_be(True)
    else:
        expect(world.bot.loot_counts.get('Recovered for two: Magic shortbow')).to_be_null()


test_each([True, False])('teammate gear recovery waits for protection and inventory acknowledgement: %s', confirmed_gear_recovery)


def recovery_preserves_supplies():
    world = recovery_world()
    world.drop(BOW, 'Magic shortbow', world.at)
    world.pack = [Fake(id=FOOD, name='Shark', count=1) for n in range(28)]
    run_wait(world.bot.recover_loot())
    run_wait(world.bot.recover_loot())
    expect(all([event[0] == 'walk' for event in world.events])).to_be(True)
    expect(world.bot.stage).to_be('retreat')
    expect(len(world.pack)).to_be(28)


test('full recovery inventories preserve food and escape supplies', recovery_preserves_supplies)
