"""Fight Arena's open-field fallback, from a live run where the Khazard Scorpion sat behind the cover rock for every
lure and no Strike was cast in 20 minutes, and the legs between its fights."""

from rs2004 import execution
from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import chat_dialog
from rs2004.entities import npcs
from rs2004.execution import event_signal
from rs2004.game import game, skills
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.navigation import reachability
from rs2004.quests.defs.fightarena import fights, legs
from rs2004.quests.defs.fightarena.areas import FA_LOC, FA_NPC, FA_OBJ, FA_TILE
from rs2004.quests.defs.fightarena.fights import FA_FIGHT, fight_rounds
from rs2004.quests.strike_combat import ARENA_COVER
from rs2004.tabs import prayer
from rs2004.traversal import traversal

SCORPION_AT = Tile(2594, 3159, 0)


class Arena:
    def __init__(self):
        self.here = ARENA_COVER
        self.tick = 0
        self.casts = []
        self.walks = []
        self.alive = True
        self.scorpion = Fake(id=FA_FIGHT.scorpion.npc_id, size=2, tile=lambda: SCORPION_AT, network_tile=lambda: SCORPION_AT,
                             targets_another_player=lambda: False, targets_me=lambda: True, actions=lambda: ['Attack'], distance=lambda: 8)

    def game_tick(self):
        self.tick += 1
        return self.tick

    def tile(self):
        return self.here

    def scorpions(self):
        return [self.scorpion] if self.alive else []

    def walk(self, dest, radius=None, attempts=None, timeout_ms=None, log=None):
        self.walks.append(dest)
        self.here = Tile(2596, 3162, 0)
        return True
        yield

    def cover(self, spot, log, lure_target=None):
        self.here = ARENA_COVER
        return True
        yield

    def cast(self, spot, target, log, lane=True):
        self.casts.append(spot)
        if len(self.casts) >= 2:
            self.alive = False
        return True
        yield

    def in_sight(self, a, b, size=1):
        # The rock stands between the cover and the scorpion; anywhere else sees it.
        return a != ARENA_COVER


def ready(log):
    return True
    yield


def casts_in_the_open():
    arena = Arena()
    spy_on(game, 'tick', arena.game_tick)
    spy_on(game, 'tile', arena.tile)
    spy_on(game, 'auto_retaliate_on', returns=False)
    spy_on(npcs, 'query', querying(arena.scorpions))
    spy_on(skills, 'level', returns=70)
    spy_on(prayer, 'active', returns=True)
    spy_on(prayer, 'points', returns=40)
    spy_on(chat_dialog, 'is_open', returns=False)
    spy_on(chat_dialog, 'can_continue', returns=False)
    spy_on(event_signal, 'pending', returns=False)
    spy_on(sustain, 'run', instant_ticks)
    spy_on(inventory, 'items', returns=[])
    spy_on(traversal, 'walk_resilient', arena.walk)
    spy_on(reachability, 'line_of_sight', arena.in_sight)
    patch(execution, 'delay_ticks', instant_ticks)
    patch(execution, 'delay_until_ticks', instant_until_ticks)
    patch(fights, 'ready_strikes', ready)
    patch(fights, 'take_strike_cover', arena.cover)
    patch(fights, 'cast_strike', arena.cast)
    outcome = yield from fight_rounds(FA_FIGHT.scorpion, lambda message: None)
    expect(outcome).to_be('won')
    expect(len(arena.walks)).to_be_greater_than(0)
    expect([spot == ARENA_COVER for spot in arena.casts]).to_equal([False, False])


test('a beast that never comes round the rock is fought in the open under the prayer', casts_in_the_open)


class BesideCover(Arena):
    """Bouncer, three tiles wide, beside the cover: in sight, but his origin is off the lane."""

    def __init__(self):
        Arena.__init__(self)
        at = Tile(2596, 3167, 0)
        self.lanes = []
        self.scorpion = Fake(id=FA_FIGHT.bouncer.npc_id, size=3, tile=lambda: at, network_tile=lambda: at,
                             targets_another_player=lambda: False, targets_me=lambda: True, actions=lambda: ['Attack'], distance=lambda: 2)

    def cast(self, spot, target, log, lane=True):
        self.lanes.append(lane)
        return Arena.cast(self, spot, target, log)

    def in_sight(self, a, b, size=1):
        return True


def hits_beside_the_cover():
    arena = BesideCover()
    spy_on(game, 'tick', arena.game_tick)
    spy_on(game, 'tile', arena.tile)
    spy_on(game, 'auto_retaliate_on', returns=False)
    spy_on(npcs, 'query', querying(arena.scorpions))
    spy_on(skills, 'level', returns=70)
    spy_on(prayer, 'active', returns=True)
    spy_on(prayer, 'points', returns=40)
    spy_on(chat_dialog, 'is_open', returns=False)
    spy_on(chat_dialog, 'can_continue', returns=False)
    spy_on(event_signal, 'pending', returns=False)
    spy_on(sustain, 'run', instant_ticks)
    spy_on(inventory, 'items', returns=[])
    spy_on(traversal, 'walk_resilient', arena.walk)
    spy_on(reachability, 'line_of_sight', arena.in_sight)
    patch(execution, 'delay_ticks', instant_ticks)
    patch(execution, 'delay_until_ticks', instant_until_ticks)
    patch(fights, 'ready_strikes', ready)
    patch(fights, 'take_strike_cover', arena.cover)
    patch(fights, 'cast_strike', arena.cast)
    outcome = yield from fight_rounds(FA_FIGHT.bouncer, lambda message: None)
    expect(outcome).to_be('won')
    expect(arena.walks).to_equal([])
    expect(arena.casts).to_equal([ARENA_COVER, ARENA_COVER])
    expect(arena.lanes).to_equal([False, False])


test('a wide beast beside the cover is hit without the lane once the lures fail', hits_beside_the_cover)


def pockets():
    from rs2004.quests.defs.fightarena import fightarena
    from rs2004.quests.defs.fightarena.areas import FA_TILE, walled_in
    expect(fightarena.resume_at).to_be(walled_in)
    for tile in [FA_TILE.ARENA_CENTRE, FA_TILE.DOOR1_INSIDE, Tile(2599, 3143, 0)]:
        expect(walled_in(tile), str(tile)).to_be(True)
    for tile in [FA_TILE.DOOR1_OUTSIDE, FA_TILE.YANILLE_BANK, FA_TILE.LADY_SERVIL]:
        expect(walled_in(tile), str(tile)).to_be(False)


test('a restart in the arena, its cells or its building resumes there before any banking', pockets)


# The legs between fights: the disguise, the doors, Jeremy's gate, the Servils and the flight from Khazard.

ARENA = FA_TILE.ARENA_CENTRE
BUILDING = Tile(2610, 3145, 0)
OUTSIDE = FA_TILE.DOOR1_OUTSIDE
RUNE_FULL_HELM = 1163
RUNE_CHAINBODY = 1113


def result(value):
    return value
    yield


class Compound:
    """The player around the arena: their pack and worn items by id, the locs and npcs, and waits that run on_tick."""

    def __init__(self, at=None):
        self.at = at if at is not None else OUTSIDE
        self.pack = []
        self.worn = []
        self.locs = []
        self.npcs = []
        self.walks = []
        self.walk_ok = True
        self.equip_ok = True
        self.retaliate = True
        self.praying = []
        self.points = 40
        self.hp = 70
        self.ate = 0
        self.on_tick = None
        self.lines = []
        spy_on(legs.game, 'tile', impl=lambda: self.at)
        spy_on(legs.game, 'auto_retaliate_on', impl=lambda: self.retaliate)
        spy_on(legs.game, 'set_auto_retaliate', impl=self.set_retaliate)
        spy_on(legs.inventory, 'items', impl=lambda: self.pack)
        spy_on(legs.inventory, 'count_by_id', impl=lambda id: len([item for item in self.pack if item.id == id]))
        spy_on(legs.equipment, 'items', impl=lambda: self.worn)
        spy_on(legs.equipment, 'contains', impl=lambda name: any([item.name == name for item in self.worn]))
        spy_on(legs.equipment, 'equip', impl=self.equip)
        spy_on(legs.locs, 'query', impl=querying(lambda: self.locs))
        spy_on(legs.npcs, 'query', impl=querying(lambda: self.npcs))
        spy_on(legs.traversal, 'walk_resilient', impl=self.walk)
        spy_on(legs, 'settle_scene', impl=instant_ticks)
        spy_on(legs.skills, 'level', impl=lambda name: 70 if name == 'hitpoints' else 43)
        spy_on(legs.skills, 'effective', impl=lambda name: self.hp)
        spy_on(legs.prayer, 'points', impl=lambda: self.points)
        spy_on(legs.prayer, 'active', impl=lambda name: name in self.praying)
        spy_on(legs.prayer, 'set', impl=self.pray)
        spy_on(legs.sustain, 'run', impl=self.eat)
        patch(execution, 'delay_until', self.until)
        patch(execution, 'delay_ticks', instant_ticks)

    def log(self, text):
        self.lines.append(text)

    def logged(self, part):
        return any([part in line for line in self.lines])

    def until(self, cond, timeout_ms=6000):
        if self.on_tick is not None:
            self.on_tick()
        return cond()
        yield

    def set_retaliate(self, on):
        self.retaliate = on

    def pray(self, name, on):
        if on:
            self.praying.append(name)
        else:
            self.praying.remove(name)
        return True
        yield

    def eat(self):
        self.ate += 1
        return True
        yield

    def walk(self, tile, radius=None, attempts=None, timeout_ms=None, log=None):
        self.walks.append(tile)
        if self.walk_ok:
            self.at = tile
        return self.walk_ok
        yield

    def hold(self, id, name=None, use_on=None):
        item = Fake(id=id, name=name, use_on=use_on if use_on is not None else (lambda other: True))
        self.pack.append(item)
        return item

    def equip(self, name):
        item = ([item for item in self.pack if (item.name if item.name is not None else str(item.id)) == name] or [None])[0]
        if not self.equip_ok or item is None:
            return False
        self.pack.remove(item)
        self.worn.append(item)
        return True
        yield

    def loc(self, id, ops, name='Door', interact=None):
        return Fake(id=id, name=name, actions=lambda: ops, distance=lambda: 1,
                    interact=interact if interact is not None else (lambda op: True))

    def moves(self, tile):
        def go(*args):
            self.at = tile
            return True
        return go


def chest():
    world = Compound()
    world.walk_ok = False
    expect(run_wait(legs.search_chest(world.log))).to_be(False)
    expect(world.logged('could not stand north')).to_be(True)
    world.walk_ok = True
    expect(run_wait(legs.search_chest(world.log))).to_be(False)
    expect(world.logged('no Chest to Search')).to_be(True)
    opened = []
    world.locs = [world.loc(1, ['Open'], FA_LOC.CHEST, lambda op: opened.append(op))]
    expect(run_wait(legs.search_chest(world.log))).to_be(False)
    expect(opened).to_equal(['Open'])
    world.locs = [world.loc(1, ['Search'], FA_LOC.CHEST, lambda op: False)]
    expect(run_wait(legs.search_chest(world.log))).to_be(False)

    def search(op):
        world.hold(FA_OBJ.HELMET)
        world.hold(FA_OBJ.ARMOUR)
        return True
    world.locs = [world.loc(1, ['Search'], FA_LOC.CHEST, search)]
    expect(run_wait(legs.search_chest(world.log))).to_be(True)
    expect(world.walks).to_equal([FA_TILE.CHEST_STAND] * 2)
    expect(run_wait(legs.search_chest(world.log))).to_be(True)
    expect(len(world.walks)).to_be(2)


test("the disguise is searched for from the chest's north side, opening it first", chest)


def disguise():
    world = Compound()
    world.hold(FA_OBJ.HELMET, 'Khazard helmet')
    world.hold(FA_OBJ.ARMOUR)
    expect(run_wait(legs.wear_khazard(world.log))).to_be(True)
    expect(legs.disguised()).to_be(True)
    expect(run_wait(legs.wear_khazard(world.log))).to_be(True)
    world = Compound()
    world.hold(FA_OBJ.HELMET, 'Khazard helmet')
    world.equip_ok = False
    expect(run_wait(legs.wear_khazard(world.log))).to_be(False)
    expect(world.logged('could not wear Khazard helmet')).to_be(True)


test('the disguise is worn piece by piece, and a missing or refused piece fails it', disguise)


def kit():
    world = Compound()
    world.hold(1, 'Rune scimitar')
    world.worn = [Fake(id=2, name='Rune full helm')]
    expect(run_wait(legs.wear_kit(['Rune full helm', 'Rune scimitar', 'Dragon longsword'], world.log))).to_be(True)
    expect([item.name for item in world.worn]).to_equal(['Rune full helm', 'Rune scimitar'])
    expect(world.logged('cannot wear Dragon longsword')).to_be(True)
    expect('dragon longsword' in legs.unwearable).to_be(True)
    legs.unwearable.clear()


test('a kit piece the account cannot wear is left behind', kit)


def combat():
    world = Compound()
    expect(run_wait(legs.wear_combat(world.log))).to_be(True)
    world.hold(RUNE_CHAINBODY)
    world.hold(RUNE_FULL_HELM)
    world.hold(FA_OBJ.HELMET)
    expect(run_wait(legs.wear_combat(world.log))).to_be(True)
    expect([item.id for item in world.worn]).to_equal([RUNE_FULL_HELM, RUNE_CHAINBODY])


test("the account's own head and body go back on before a fight", combat)


def doors():
    world = Compound()
    expect(run_wait(legs.enter_building(world.log))).to_be(False)
    expect(world.logged('refusing to knock')).to_be(True)
    world.worn = [Fake(id=FA_OBJ.HELMET, name='Khazard helmet')]
    expect(run_wait(legs.enter_building(world.log))).to_be(False)
    expect(world.logged('no loc 81 offering Open')).to_be(True)
    talks = spy_on(legs, 'drive_dialog', impl=lambda prefer, log: result(True))
    world.locs = [world.loc(FA_LOC.DOOR1, ['Open'], interact=world.moves(BUILDING))]
    expect(run_wait(legs.enter_building(world.log))).to_be(True)
    world.locs = [world.loc(FA_LOC.DOOR1, ['Open'], interact=world.moves(OUTSIDE))]
    expect(run_wait(legs.leave_building(world.log))).to_be(True)
    world.locs = [world.loc(FA_LOC.DOOR2, ['Open'], interact=world.moves(ARENA))]
    expect(run_wait(legs.enter_arena_by_door2(world.log))).to_be(True)
    world.locs = [world.loc(FA_LOC.DOOR1, ['Open'], interact=world.moves(ARENA))]
    expect(run_wait(legs.enter_arena_by_guard(world.log))).to_be(True)
    expect(len(talks.calls)).to_be(3)
    world.at = ARENA
    world.walk_ok = False
    for leg in [legs.leave_building, legs.enter_arena_by_door2, legs.enter_arena_by_guard]:
        expect(run_wait(leg(world.log))).to_be(False)
    world.walk_ok = True
    world.locs = [world.loc(FA_LOC.DOOR1, ['Open'])]
    world.at = BUILDING
    expect(run_wait(legs.enter_arena_by_guard(world.log))).to_be(False)


test('each scripted door is opened from its exact stand and crossed only when the pocket changes', doors)


def jeremy():
    world = Compound(BUILDING)
    spy_on(legs, 'drive_dialog', impl=lambda prefer, log: result(True))
    world.walk_ok = False
    expect(run_wait(legs.unlock_jeremy(world.log))).to_be(False)
    world.walk_ok = True
    expect(run_wait(legs.unlock_jeremy(world.log))).to_be(False)
    expect(world.logged('no Jeremy gate in reach')).to_be(True)
    world.locs = [world.loc(FA_LOC.JEREMY_DOOR, [])]
    world.hold(FA_OBJ.KEYS, use_on=lambda door: False)
    expect(run_wait(legs.unlock_jeremy(world.log))).to_be(False)
    world.pack = []
    world.hold(FA_OBJ.KEYS, use_on=world.moves(ARENA))
    expect(run_wait(legs.unlock_jeremy(world.log))).to_be(True)


test("Jeremy's gate opens to the cell keys and the server puts us in the arena", jeremy)


def servil():
    return Fake(id=FA_NPC.LADY_SERVIL, name='Lady Servil', actions=lambda: ['Talk-to'], distance=lambda: 3)


class Reach:
    def __init__(self):
        self.status = 'unreachable'
        self.found = []

    def entity_op(self, find, op, ready, expect_ms=5000, open_when_unreachable=False, what=None, log=None):
        self.found.append(find())
        return self.status
        yield


def talks():
    world = Compound()
    world.walk_ok = False
    expect(run_wait(legs.talk_by_id(FA_NPC.LADY_SERVIL, [], world.log, FA_TILE.LADY_SERVIL))).to_be(False)
    expect(world.logged('could not walk to (2566,3199) for npc 264')).to_be(True)
    world.walk_ok = True
    reach = Reach()
    spy_on(legs.reach, 'entity_op', impl=reach.entity_op)
    expect(run_wait(legs.talk_by_id(FA_NPC.LADY_SERVIL, [], world.log, FA_TILE.LADY_SERVIL))).to_be(False)
    expect(world.logged('npc 264 never opened a dialogue')).to_be(True)
    reach.status = 'done'
    world.npcs = [servil()]
    spy_on(legs, 'drive_dialog', impl=lambda prefer, log: result(True))
    expect(run_wait(legs.talk_by_id(FA_NPC.LADY_SERVIL, [], world.log, FA_TILE.LADY_SERVIL))).to_be(True)
    expect(reach.found[-1].id).to_be(FA_NPC.LADY_SERVIL)
    expect(world.walks).to_equal([FA_TILE.LADY_SERVIL, FA_TILE.LADY_SERVIL])
    expect(run_wait(legs.talk_and_land(FA_NPC.LADY_SERVIL, 'outside', 1000, world.log))).to_be(True)
    expect(run_wait(legs.talk_and_land(FA_NPC.LADY_SERVIL, 'arena', 1000, world.log))).to_be(False)
    expect(world.logged('did not put us in the arena')).to_be(True)
    reach.status = 'failed'
    expect(run_wait(legs.talk_and_land(FA_NPC.LADY_SERVIL, 'arena', 1000, world.log))).to_be(False)


test('a talk by id walks near first, needs the dialogue to open and may end in a ride', talks)


def ogre():
    return Fake(id=FA_NPC.OGRE, name='Khazard Ogre', actions=lambda: ['Attack'], distance=lambda: 5)


def releases():
    world = Compound(ARENA)
    fight = Fake(npc_id=FA_NPC.OGRE, what='the ogre')
    outcomes = []

    def fights(f, log):
        return outcomes.pop(0)
        yield
    spy_on(legs, 'run_fight', impl=fights)
    talked = spy_on(legs, 'talk_by_id', impl=lambda npc_id, prefer, log: result(False))
    world.npcs = [ogre()]
    outcomes.append('won')
    expect(run_wait(legs.fight_with_release(fight, FA_NPC.LADY_SERVIL, world.log))).to_be(True)
    outcomes.append('lost')
    expect(run_wait(legs.fight_with_release(fight, FA_NPC.LADY_SERVIL, world.log))).to_be(False)
    outcomes.append('unengaged')
    expect(run_wait(legs.fight_with_release(fight, FA_NPC.LADY_SERVIL, world.log))).to_be(False)
    expect(world.logged('the ogre is still caged')).to_be(True)
    world.npcs = []
    talked.mock_implementation(lambda npc_id, prefer, log: result(True))
    expect(run_wait(legs.fight_with_release(fight, FA_NPC.LADY_SERVIL, world.log))).to_be(False)
    expect(world.logged('did not come out after the dialogue')).to_be(True)
    world.on_tick = lambda: world.npcs.append(ogre())
    outcomes.append('won')
    expect(run_wait(legs.fight_with_release(fight, FA_NPC.LADY_SERVIL, world.log))).to_be(True)
    expect(len(talked.calls)).to_be(3)


test('a caged beast is let out by a Servil before it is fought', releases)


def flees():
    world = Compound(ARENA)
    world.hp = 40
    world.locs = [world.loc(FA_LOC.DOOR2, ['Open'], interact=world.moves(BUILDING)),
                  world.loc(FA_LOC.DOOR1, ['Open'], interact=world.moves(OUTSIDE))]
    expect(run_wait(legs.flee_arena(world.log))).to_be(True)
    expect(world.at).to_equal(OUTSIDE)
    expect(world.ate).to_be(1)
    expect(world.retaliate).to_be(True)
    expect(world.praying).to_equal([])
    expect(world.logged('out of the arena')).to_be(True)
    expect(run_wait(legs.flee_arena(world.log))).to_be(True)


test('fleeing Khazard prays, eats, leaves by door2 and door1, then restores retaliation and prayer', flees)


def flee_fails():
    world = Compound(ARENA)
    world.points = 0
    expect(run_wait(legs.flee_arena(world.log))).to_be(False)
    world.locs = [world.loc(FA_LOC.DOOR2, ['Open'])]
    expect(run_wait(legs.flee_arena(world.log))).to_be(False)
    world.retaliate = False
    world.praying = [legs.PROTECT_MELEE]

    def boom(log):
        raise ValueError('lost the client')
        yield
    spy_on(legs, 'run_from_khazard', impl=boom)
    expect(lambda: run_wait(legs.flee_arena(world.log))).to_throw('lost the client')
    expect(world.praying).to_equal([])
    expect(world.retaliate).to_be(False)


test('a failed or broken flight still puts retaliation and prayer back', flee_fails)
