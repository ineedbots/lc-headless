# fixture: jive_dragons
"""rs2b0t JiveDragons facade scenarios through the Python hunting scheduler (MIT, see thirdparty/rs2b0t)."""

import _core
import bots.jive_dragons as dragons
from rs2004.game import reader
from rs2004.navigation import reachability
from rs2004.hunting import combat
from rs2004.geometry import Tile
from rs2004.settings import SettingsBag


ITEM_NAMES = {379: 'Lobster', 385: 'Shark', 892: 'Rune arrow', 890: 'Mithril arrow', 536: 'Dragon bones',
              1747: 'Dragonhide', 995: 'Coins', 1617: 'Uncut diamond', 1540: 'Dragonfire shield'}


class DragonItem(Held):
    def __init__(self, world, id, count=1, slot=0):
        Held.__init__(self, id, ITEM_NAMES.get(id, 'Other'), count, slot)
        self.world = world
        self.noted = False

    def actions(self):
        return ['Wield', 'Eat', 'Drop', 'Bury']

    def interact(self, op):
        world = self.world
        world.events.append((op, self.id, world.tile))
        if op == 'Wield':
            if not world.confirm_equip:
                return True
            quiver = [i for i in world.worn if i.id == self.id]
            if quiver:
                quiver[0].count += self.count
            else:
                world.worn.append(self)
        elif op == 'Bury' and world.reject_bury:
            return False
        elif op == 'Drop':
            world.drop(self.id, world.tile, self.count)
        elif op == 'Eat':
            world.hp = 99
        world.pack = [item for item in world.pack if item is not self]
        return True


class DragonDrop:
    def __init__(self, world, id, tile, count):
        self.world = world
        self.id = id
        self.name = ITEM_NAMES.get(id, 'Other')
        self.position = tile
        self.count = count

    def actions(self):
        return ['Take']

    def tile(self):
        return self.position

    def distance(self):
        return self.world.tile.distance_to(self.position)

    def valid(self):
        return self in self.world.ground

    def interact(self, op):
        world = self.world
        world.events.append((op, self.id, self.position))
        if world.reject_take:
            return False
        stack = [item for item in world.pack if item.id == self.id]
        if stack and self.id in [892, 995]:
            stack[0].count += self.count
        else:
            world.pack.append(DragonItem(world, self.id, self.count))
        world.ground.remove(self)
        return True


class DragonNpc:
    def __init__(self, world, index=17):
        self.world = world
        self.index = index
        self.id = 1
        self.name = world.site.target
        self.size = 3
        self.position = Tile(world.tile.x + 3, world.tile.z, world.tile.level)
        self.visual = None
        self.health = 100
        self.max_health = 200
        self.in_combat = True
        self.ours = False
        self.foreign = False

    def tile(self):
        return self.visual or self.position

    def network_tile(self):
        return self.position

    def distance(self):
        return self.world.tile.distance_to(self.tile())

    def actions(self):
        return ['Attack']

    def targets_me(self):
        return self.ours

    def targets_another_player(self):
        return self.foreign

    def interact(self, op):
        self.world.attacks += 1
        self.world.events.append((op, self.index, self.world.tile))
        return True


class DragonWorld(Lair):
    def __init__(self, site='taverley-black', style='range', settings=None):
        Lair.__init__(self, site, style)
        self.install()
        self.clock = 10000
        self.hp = 99
        self.pending = False
        self.stop_at = 1000000000
        self.ground = []
        self.npcs = []
        self.events = []
        self.attacks = 0
        self.confirm_equip = True
        self.reject_bury = False
        self.reject_take = False
        self.worn.append(Held(892, 'Rune arrow', 100, 13))
        self.pack = [DragonItem(self, 385) for n in range(10)]
        spy_on(_core, 'step_time', impl=lambda: self.clock)
        spy_on(dragons, 'now_ms', impl=lambda: self.clock)
        spy_on(game, 'tick', impl=lambda: self.clock // 600)
        spy_on(game, 'facing', returns=None)
        spy_on(skills, 'effective', impl=lambda name: self.hp)
        spy_on(skills, 'hp_fraction', impl=lambda: self.hp / 99)
        spy_on(npcs, 'query', impl=querying(lambda: self.npcs))
        spy_on(npcs, 'all', impl=lambda: self.npcs)
        spy_on(ground_items, 'query', impl=querying(lambda: self.ground))
        spy_on(event_signal, 'pending', impl=lambda: self.pending or self.clock >= self.stop_at)
        spy_on(reachability, 'line_of_sight', returns=True)
        spy_on(reachability, 'can_reach', returns=True)
        spy_on(reachability, 'walkable', returns=True)
        spy_on(execution, 'delay_ticks', impl=self.ticks)
        spy_on(traversal, 'walk_resilient', impl=lambda tile, **opts: self.walk(tile, opts))
        spy_on(direct_navigator, 'walk', impl=self.direct_walk)
        values = {'site': site, 'combat_style': style, 'ammo': 'Rune arrow', 'food': 'Shark', 'solve_clues': False,
                  'use_special': False, 'bury_bones': True, 'loot': ['Dragon bones', 'Dragonhide', 'Coins', 'Uncut diamond'],
                  'loot_black': ['Dragon bones', 'Dragonhide', 'Coins', 'Uncut diamond']}
        values.update(settings or {})
        self.bot = JiveDragons()
        self.bot.settings = SettingsBag(values)
        self.bot.bind_log(lambda line: None)
        run_wait(self.bot.on_start())
        sustain.set(None)
        self.dragon = DragonNpc(self)
        self.npcs = [self.dragon]
        self.gear_validate = dragons.GearEquip.validate
        spy_on(reader, 'item_type', impl=lambda id: Fake(stackable=id in [892, 995]))
        for task in self.bot._tasks:
            if type(task).__name__ not in ['FreeSlot', 'LootCorpse', 'BankRun', 'Fight', 'BuryBones']:
                spy_on(task, 'validate', returns=False)
        spy_on(self.task('BankRun'), 'execute', impl=self.bank_run)

    def task(self, name):
        return [task for task in self.bot._tasks if type(task).__name__ == name][0]

    def ticks(self, count=1):
        self.clock += count * 600
        return
        yield

    def direct_walk(self, tile, *args, **opts):
        self.events.append(('Walk', -1, tile))
        self.tile = tile
        return True

    def walk(self, tile, opts):
        self.events.append(('Walk', -1, tile))
        if self.walk_ok:
            self.tile = tile
        return self.walk_ok
        yield

    def bank_run(self):
        self.events.append(('Bank', -1, self.tile))
        return
        yield

    def drop(self, id, tile=None, count=1):
        drop = DragonDrop(self, id, tile or Tile(self.tile.x + 1, self.tile.z, self.tile.level), count)
        self.ground.append(drop)
        return drop

    def run(self, count=1):
        for n in range(count):
            self.stop_at = self.clock + 1200
            run_wait(self.bot.loop())


def ownership_blocks_loot(full):
    world = DragonWorld()
    if full:
        world.pack = [DragonItem(world, 385) for n in range(28)]
    world.drop(892, count=4)
    world.bot.fight._set_target(17)
    world.run()
    expect(any([event[0] in ['Take', 'Drop'] for event in world.events])).to_be(False)
    expect(world.bot.kills).to_be(0)


test_each([False, True])('an owned live dragon blocks food-slot changes and loot, full=%s', ownership_blocks_loot)


def pending_kill_before_loot(other_dragon):
    world = DragonWorld()
    world.drop(892, count=4)
    world.bot.fight._set_target(17)
    world.npcs = []
    if other_dragon:
        other = DragonNpc(world, 18)
        other.in_combat = False
        world.npcs = [other]
    world.run()
    expect(world.bot.kills).to_be(1)
    expect(any([event[0] == 'Take' for event in world.events])).to_be(False)
    world.run()
    expect(any([event[0] == 'Take' for event in world.events])).to_be(True)
    expect(world.bot.kills).to_be(1)
    expect(world.attacks).to_be(0)


test_each([False, True])('a completed engagement yields loot priority before another dragon, other=%s', pending_kill_before_loot)


def recheck_after_validation(name):
    world = DragonWorld()
    if name == 'FreeSlot':
        world.pack = [DragonItem(world, 385) for n in range(28)]
    world.drop(536)
    task = world.task(name)
    expect(task.validate()).to_be(True)
    world.bot.fight._set_target(17)
    run_wait(task.execute())
    expect(world.events).to_equal([])


test_each(['FreeSlot', 'LootCorpse'])('%s rechecks combat ownership after validation', recheck_after_validation)


def stale_or_abandoned(stale):
    world = DragonWorld()
    world.drop(892, count=4)
    world.bot.fight._set_target(17)
    if stale:
        world.clock += 10000
    else:
        world.bot.fight._clear_target()
    world.npcs = []
    world.run(2)
    expect(world.bot.kills).to_be(0)
    expect(any([event[0] == 'Take' for event in world.events])).to_be(True)


test_each([False, True])('abandonment or stale disappearance releases loot without inventing a kill: %s', stale_or_abandoned)


def outline_not_ownership():
    world = DragonWorld()
    world.bot.target_idx = 17
    world.drop(892, count=4)
    world.run()
    expect(any([event[0] == 'Take' for event in world.events])).to_be(True)
    expect(world.bot.kills).to_be(0)


test('a leash outline is not ownership and does not prevent old loot', outline_not_ownership)



def loot_world(food=28):
    world = DragonWorld()
    world.npcs = []
    world.pack = [DragonItem(world, 385) for n in range(food)] + [DragonItem(world, 1617) for n in range(28 - food)]
    return world


def loot_capacity(food):
    world = loot_world(food)
    anchor = world.tile
    world.drop(536)
    world.drop(1747)
    world.run(4)
    actions = [event[0] for event in world.events if event[0] != 'Walk']
    expect(actions[:4]).to_equal(['Drop', 'Take', 'Bury', 'Take'])
    expect(world.bot.loot_counts.get('Dragonhide')).to_be(1)
    expect(world.tile.equals(anchor)).to_be(True)


test_each([28, 4, 2, 1])('safe corpse loot can spend food at capacity: %s', loot_capacity)


def stack_fits(count):
    world = loot_world(27)
    world.pack[-1] = DragonItem(world, 892, count)
    world.drop(892, count=3)
    world.run(4)
    expect([event[0] for event in world.events if event[0] != 'Walk']).to_equal(['Take'])
    expect(inventory.count('Rune arrow')).to_be(count + 3)


test_each([1, 100])('stack-fitting arrows never consume food: %s', stack_fits)


def burial_reclaims_food(uppercase):
    world = loot_world()
    anchor = world.tile
    if uppercase:
        for item in world.pack:
            item.name = 'SHARK'
    foreign = world.drop(385)
    world.drop(536)
    world.run(5)
    expect([(event[0], event[1]) for event in world.events if event[0] != 'Walk']).to_equal([
        ('Drop', 385), ('Take', 536), ('Bury', 536), ('Take', 385)])
    expect(foreign in world.ground).to_be(True)
    expect(len(world.pack)).to_be(28)
    expect(world.tile.equals(anchor)).to_be(True)


test_each([False, True])('burial reclaims only our dropped food, case insensitive=%s', burial_reclaims_food)


def existing_anchor_food():
    world = loot_world()
    world.drop(385, world.tile)
    world.drop(536)
    world.run(5)
    expect(any([event[0] == 'Take' and event[1] == 385 for event in world.events])).to_be(False)


test('food already on the anchor never becomes ours', existing_anchor_food)


def finished_return_forgets_food():
    world = loot_world()
    world.drop(536)
    world.drop(1747)
    world.run(6)
    world.pack.pop()
    world.run(3)
    expect(len([event for event in world.events if event[0] == 'Drop'])).to_be(1)
    expect(any([event[0] == 'Take' and event[1] == 385 for event in world.events])).to_be(False)


test('a finished full return forgets food even if space later becomes free', finished_return_forgets_food)


def wounded_capacity():
    world = loot_world()
    world.hp = 95
    world.drop(536)
    world.run(5)
    expect([event[0] for event in world.events if event[0] != 'Walk']).to_equal(['Eat', 'Take', 'Bury'])


test('wounded capacity preparation eats rather than drops', wounded_capacity)


def bounded_pickup_failure():
    world = loot_world()
    world.reject_take = True
    world.drop(536)
    world.run(20)
    expect(len([event for event in world.events if event[0] == 'Drop'])).to_be(1)


test('failed pickups do not repeat food drop and reclaim indefinitely', bounded_pickup_failure)


def unreachable_anchor():
    world = loot_world()
    anchor = world.tile
    world.tile = Tile(anchor.x + 2, anchor.z, anchor.level)
    world.walk_ok = False
    world.drop(536)
    world.run(2)
    expect(all([event[0] == 'Walk' for event in world.events])).to_be(True)
    expect(len(world.pack)).to_be(28)


test('an unreachable anchor forbids food dropping at the corpse', unreachable_anchor)


def low_health_loot():
    world = loot_world()
    world.hp = 30
    world.drop(536)
    world.run(2)
    expect(world.events).to_equal([])


test('low health prevents optional slot preparation and loot movement', low_health_loot)


def mixed_ammo(confirmed):
    world = DragonWorld()
    world.npcs = []
    world.pack = [DragonItem(world, 385), DragonItem(world, 892, 3), DragonItem(world, 890, 5)]
    world.confirm_equip = confirmed
    gear = world.bot.gear_equip
    for n in range(6):
        if world.gear_validate(gear):
            run_wait(gear.execute())
    expect(inventory.count('Mithril arrow')).to_be(5)
    if confirmed:
        expect([(event[0], event[1]) for event in world.events]).to_equal([('Wield', 892)])
        expect(inventory.count('Rune arrow')).to_be(0)
        expect(world.bot.quiver_count()).to_be(103)
    else:
        expect(len(world.events)).to_be(5)
        expect(world.gear_validate(gear)).to_be(False)
        expect(inventory.count('Rune arrow')).to_be(3)
        expect(world.bot.quiver_count()).to_be(100)


test_each([True, False])('ammo merges only the configured stack after acknowledgement: %s', mixed_ammo)



def scene_rebuild(abandoned):
    world = DragonWorld()
    world.drop(892, count=4)
    world.bot.fight._set_target(17)
    if abandoned:
        world.bot.fight._clear_target()
    world.npcs = []
    spy_on(game, 'scene_ready', returns=False)
    run_wait(world.bot.fight.execute())
    run_wait(world.task('LootCorpse').execute())
    expect(world.bot.kills).to_be(0)
    expect(world.events).to_equal([])
    expect(world.bot.fight.loot_target).to_be(17)


test_each([False, True])('scene rebuild cannot invent a kill or release living loot ownership: %s', scene_rebuild)


def ownership_across_sites(site, style):
    world = DragonWorld(site, style)
    world.drop(892, count=4)
    world.bot.fight._set_target(17)
    run_wait(world.task('LootCorpse').execute())
    expect(world.events).to_equal([])
    expect(world.bot.kills).to_be(0)


test_each([['taverley-blue', 'range'], ['heroes-blue', 'mage'], ['brimhaven-iron', 'melee']])(
    'combat ownership blocks loot across site and style: %s', ownership_across_sites)


def no_ammo_banks_owned_fight():
    world = DragonWorld()
    world.bot.fight._set_target(17)
    world.worn = []
    world.drop(892, count=4)
    world.run()
    expect([event[0] for event in world.events]).to_equal(['Bank'])
    expect(world.bot.kills).to_be(0)


test('missing ammo banks before an owned fight or its arrows', no_ammo_banks_owned_fight)


def loot_rechecks_movement():
    world = DragonWorld()
    world.drop(892, count=4)
    spy_on(reachability, 'can_reach', returns=False)

    def walk(tile, **opts):
        world.bot.fight._set_target(17)
        return True
        yield

    spy_on(traversal, 'walk_resilient', impl=walk)
    run_wait(world.task('LootCorpse').execute())
    expect(world.events).to_equal([])


test('loot rechecks combat ownership after asynchronous movement', loot_rechecks_movement)


def engagement_after_preparation(change):
    world = DragonWorld('heroes-blue', 'melee')
    world.dragon.in_combat = False

    def prepare():
        if change == 'claimed':
            world.dragon.in_combat = True
        elif change == 'event':
            world.pending = True
        else:
            world.npcs = []
        return
        yield

    spy_on(world.bot, 'arm_special', impl=prepare)
    expect(run_wait(world.bot.fight._engage(world.dragon, 'blue dragon'))).to_be(False)
    expect(world.attacks).to_be(0)


test_each(['claimed', 'event', 'despawn'])('melee revalidates its target after special preparation: %s', engagement_after_preparation)


def heroes_gate(reached):
    world = DragonWorld('heroes-blue', 'melee')
    world.dragon.in_combat = False
    accessible = [False]
    spy_on(reachability, 'can_reach', impl=lambda *args: accessible[0])

    def walk(tile, **opts):
        accessible[0] = reached
        return reached
        yield

    walked = spy_on(traversal, 'walk_resilient', impl=walk)
    expect(run_wait(world.bot.fight._engage(world.dragon, 'blue dragon'))).to_be(reached)
    expect(len(walked.calls)).to_be(1)
    expect(world.attacks).to_be(1 if reached else 0)


test_each([True, False])('Heroes melee crosses the pen gate before attacking: %s', heroes_gate)


def shield_blocks_attack():
    world = DragonWorld('brimhaven-iron', 'melee')
    world.worn = []
    world.dragon.in_combat = False
    expect(world.bot.fight.validate()).to_be(False)
    expect(run_wait(world.bot.fight._engage(world.dragon, world.dragon.name))).to_be(False)
    expect(world.attacks).to_be(0)


test('a required missing shield prevents attacks even after target selection', shield_blocks_attack)
