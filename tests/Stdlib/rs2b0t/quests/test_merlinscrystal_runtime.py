"""Merlin's Crystal's legs: the knights, the keep's crate and Mordred, the bat, the wax, Excalibur and Thrantax."""

import rs2004.quests.defs.merlinscrystal as mc
from rs2004 import execution
from rs2004.geometry import Tile

KEEP_L0 = Tile(2770, 3400, 0)
CAMELOT = Tile(2758, 3508, 0)


def result(value):
    return value
    yield


after_each(mc.live_reset_mordred_brief)


class Merlin:
    """The player, their pack and the scene around them, with a chat dialog of pages."""

    def __init__(self, at=None):
        mc.live_reset_mordred_brief()
        self.at = at if at is not None else CAMELOT
        self.pack = []
        self.worn = []
        self.locs = []
        self.npcs = []
        self.ground = []
        self.walks = []
        self.walk_ok = True
        self.on_walk = None
        self.fighting = False
        self.pending = False
        self.lines = []
        self.chat = FakeChat().install(mc.chat_dialog)
        spy_on(mc.game, 'tile', impl=lambda: self.at)
        spy_on(mc.game, 'set_combat_style', returns=True)
        spy_on(mc.game, 'in_combat', impl=lambda: self.fighting)
        spy_on(mc.locs, 'query', impl=querying(lambda: self.locs))
        spy_on(mc.npcs, 'query', impl=querying(lambda: self.npcs))
        spy_on(mc.ground_items, 'query', impl=querying(lambda: self.ground))
        spy_on(mc.traversal, 'walk_resilient', impl=self.walk)
        spy_on(mc.inventory, 'contains', impl=lambda name: self.item(name) is not None)
        spy_on(mc.inventory, 'first', impl=self.item)
        spy_on(mc.equipment, 'contains', impl=lambda name: name in self.worn)
        spy_on(mc.equipment, 'equip', impl=self.equip)
        spy_on(mc.event_signal, 'pending', impl=lambda: self.pending)
        spy_on(mc.sustain, 'run', impl=instant_ticks)
        patch(execution, 'delay_until', instant_until)
        patch(execution, 'delay_ticks', instant_ticks)

    def log(self, text):
        self.lines.append(text)

    def logged(self, part):
        return any([part in line for line in self.lines])

    def walk(self, tile, radius=None, attempts=None, timeout_ms=None, log=None):
        self.walks.append(tile)
        if self.walk_ok:
            self.at = tile
            if self.on_walk is not None:
                self.on_walk(tile)
        return self.walk_ok
        yield

    def hold(self, name, use_on=None, interact=None):
        item = Fake(name=name, use_on=use_on if use_on is not None else (lambda other: True),
                    interact=interact if interact is not None else (lambda op: True))
        self.pack.append(item)
        return item

    def item(self, name):
        for item in self.pack:
            if item.name == name:
                return item
        return None

    def drop(self, name):
        self.pack = [item for item in self.pack if item.name != name]

    def equip(self, name):
        self.drop(name)
        self.worn.append(name)
        return True
        yield

    def thing(self, name, ops, at=None, interact=None, distance=1):
        tile = at if at is not None else self.at
        return Fake(name=name, actions=lambda: ops, distance=lambda: distance, tile=lambda: tile,
                    interact=interact if interact is not None else (lambda op: True))

    def stair(self, name, op, step):
        """A stair or ladder that moves the player step levels; it stays beside them."""
        def climb(chosen):
            self.at = Tile(self.at.x, self.at.z, self.at.level + step)
            return True
        return self.thing(name, [op], interact=climb)


def drives_pages():
    world = Merlin()
    world.chat.pages = ['continue', ['Leave', 'Tell me how to untrap Merlin'], ['Nothing', 'Bye']]
    run_wait(mc.drive_dialogue(['untrap Merlin'], world.log))
    expect(world.chat.chosen).to_equal(['Tell me how to untrap Merlin', 'Bye'])
    expect(world.logged('taking the last')).to_be(True)
    world.chat.pages = ['continue']
    world.pending = True
    run_wait(mc.drive_dialogue([], world.log))
    expect(len(world.chat.pages)).to_be(1)


test('dialogue continues, prefers its fragments and otherwise takes the last option', drives_pages)


def climbs():
    world = Merlin()
    world.walk_ok = False
    expect(run_wait(mc.climb_at(mc.CAM_STAIR_L0, 'Climb-up', world.log))).to_be(False)
    world.walk_ok = True
    expect(run_wait(mc.climb_at(mc.CAM_STAIR_L0, 'Climb-up', world.log))).to_be(False)
    expect(world.logged('LIVE-VERIFY')).to_be(True)
    world.locs = [world.thing('Staircase', ['Climb-up'], interact=lambda op: False)]
    expect(run_wait(mc.climb_at(mc.CAM_STAIR_L0, 'Climb-up', world.log))).to_be(False)
    world.locs = [world.thing('Staircase', ['Climb-up'])]
    expect(run_wait(mc.climb_at(mc.CAM_STAIR_L0, 'Climb-up', world.log))).to_be(False)
    world.locs = [world.stair('Staircase', 'Climb-up', 1)]
    expect(run_wait(mc.climb_at(mc.CAM_STAIR_L0, 'Climb-up', world.log))).to_be(True)
    expect(world.at.level).to_be(1)
    expect(run_wait(mc.ensure_camelot_l1(world.log))).to_be(True)


test('a climb needs the walk, the stair, the click and a changed level', climbs)


def descends():
    world = Merlin(Tile(2767, 3494, 2))
    world.locs = [world.stair('Ladder', 'Climb-down', -1)]
    expect(run_wait(mc.descend_tower(world.log))).to_be(True)
    expect(world.at.level).to_be(0)
    world.at = Tile(2767, 3494, 2)
    world.locs = []
    expect(run_wait(mc.descend_tower(world.log))).to_be(False)
    world.locs = [world.thing('Ladder', ['Climb-down'], interact=lambda op: False)]
    expect(run_wait(mc.descend_tower(world.log))).to_be(False)
    world.locs = [world.thing('Ladder', ['Climb-down'])]
    expect(run_wait(mc.descend_tower(world.log))).to_be(False)


test('the tower is climbed down ladder by ladder to the ground', descends)


class Knights(Merlin):
    def __init__(self, talks=True):
        Merlin.__init__(self)
        self.talks = talks
        self.talked = []
        self.gotos = []
        self.npcs = [self.thing('Sir Gawain', ['Talk-to'], at=Tile(2761, 3508, 0), distance=3)]
        self.locs = [self.stair('Staircase', 'Climb-up', 1)]
        spy_on(mc, 'goto_npc', impl=self.goto)
        spy_on(mc, 'talk_through', impl=self.talk)
        self.on_walk = self.arrive

    def goto(self, stop, hops, log):
        self.gotos.append(stop.npc)
        return False
        yield

    def arrive(self, tile):
        if tile == mc.LANCELOT.anchor:
            self.npcs = [self.thing('Sir Lancelot', ['Talk-to'], at=tile)]

    def talk(self, name, prefer, log):
        self.talked.append(name)
        return self.talks
        yield


def talks_to_both():
    world = Knights()
    run_wait(mc.talk_knights(world.log))
    expect(world.talked).to_equal(['Sir Gawain', 'Sir Lancelot'])
    expect(world.walks[0]).to_equal(Tile(2761, 3508, 0))
    expect(world.gotos).to_equal(['Sir Lancelot'])
    expect(world.at.level).to_be(1)


test("Gawain is spoken to on the ground floor, then Lancelot on the first once he's found", talks_to_both)


def gives_up():
    world = Knights(False)
    world.locs = []
    run_wait(mc.talk_knights(world.log))
    expect(world.talked).to_equal(['Sir Gawain'] * 5)
    expect(world.logged('could not climb')).to_be(True)
    expect(world.logged("giving up on 'Sir Lancelot'")).to_be(True)
    world = Knights()
    world.pending = True
    run_wait(mc.talk_knights(world.log))
    expect(world.talked).to_equal([])


test('the knights are given up for the pass after five failed talks, and an event stops them', gives_up)


def candle_maker(offers):
    def run():
        world = Merlin()
        options = ['Have you got any black candles?', 'No thank you'] if offers else ['Buy candles', 'No thank you']
        world.chat.pages = ['continue', options]
        spy_on(mc, 'goto_npc', impl=lambda stop, hops, log: result(True))
        world.npcs = [world.thing('Candle maker', ['Talk-to'])]
        expect(run_wait(mc.candle_maker_stage_four(world.log))).to_be(offers)
        expect(world.chat.chosen).to_equal(['black candles' if offers else 'No thank you'])
    return run


test("the candle maker's black-candle option shows Morgan's brief is done", candle_maker(True))
test('the candle maker without that option is declined and not taken for success', candle_maker(False))


def candle_maker_missing():
    world = Merlin()
    spy_on(mc, 'goto_npc', impl=lambda stop, hops, log: result(False))
    expect(run_wait(mc.candle_maker_stage_four(world.log))).to_be(False)
    spy_on(mc, 'goto_npc', impl=lambda stop, hops, log: result(True))
    expect(run_wait(mc.candle_maker_stage_four(world.log))).to_be(False)
    world.npcs = [world.thing('Candle maker', ['Talk-to'])]
    expect(run_wait(mc.candle_maker_stage_four(world.log))).to_be(False)


test('the candle maker needs reaching, finding and a dialogue', candle_maker_missing)


def boards_crate():
    world = Merlin(mc.CATHERBY_CRATE_STAND)

    def hide(op):
        world.at = KEEP_L0
        world.chat.pages = [['Yes.', 'No.']]
        return True
    world.locs = [world.thing('Crate', ['Hide-in'], interact=hide)]
    expect(run_wait(mc.fortress(world.log))).to_be(False)
    expect(world.chat.chosen).to_equal(['Yes.'])
    expect(world.logged('insideKeep=True')).to_be(True)
    world.at = mc.CATHERBY_CRATE_STAND
    world.locs = []
    expect(run_wait(mc.fortress(world.log))).to_be(False)
    expect(world.logged('no Catherby Crate')).to_be(True)
    world.walk_ok = False
    expect(run_wait(mc.fortress(world.log))).to_be(False)


test("the fortress is reached by hiding in Catherby's crate", boards_crate)


class Keep(Merlin):
    def __init__(self, at=None):
        Merlin.__init__(self, at if at is not None else KEEP_L0)
        self.crate = self.thing('Crate', ['Hide-in'], at=mc.RETURN_CRATE_STAND, interact=self.ride)
        self.rides = True
        self.stairs = self.stair('Staircase', 'Climb-down', -1)
        self.locs = [self.stairs, self.crate]

    def ride(self, op):
        self.chat.pages = ['continue', ['Yes.', 'No.']]
        if self.rides:
            self.at = mc.CATHERBY_CRATE_STAND
        return True


def leaves_by_crate():
    world = Keep(Tile(2769, 3399, 2))
    expect(run_wait(mc.leave_keep(world.log))).to_be(True)
    expect(world.at).to_equal(mc.CATHERBY_CRATE_STAND)
    expect(world.chat.chosen).to_equal(['Yes.'])
    expect(world.logged('crate ride out')).to_be(True)
    expect(run_wait(mc.leave_keep(world.log))).to_be(True)


test('the keep is left down its stairs and home by the crate ride', leaves_by_crate)


def leaves_by_door():
    world = Keep()
    world.rides = False
    world.locs.append(world.thing('Large door', ['Open']))
    expect(run_wait(mc.leave_keep(world.log))).to_be(True)
    expect(world.logged('did not leave the keep')).to_be(True)
    expect(world.at).to_equal(Tile(2758, 3401, 0))
    world = Keep()
    world.locs = []
    world.walk_ok = False
    expect(run_wait(mc.leave_keep(world.log))).to_be(False)


test('a crate that does not ride is followed by the west door', leaves_by_door)


def stuck_upstairs():
    world = Keep(Tile(2769, 3399, 2))
    world.locs = []
    expect(run_wait(mc.leave_keep(world.log))).to_be(False)
    expect(world.walks).to_equal([mc.KEEP_STAIR_L2_DOWN])
    world.locs = [world.thing('Staircase', ['Climb-down'], interact=lambda op: False)]
    expect(run_wait(mc.leave_keep(world.log))).to_be(False)
    world.locs = [world.thing('Staircase', ['Climb-down'])]
    expect(run_wait(mc.leave_keep(world.log))).to_be(False)


test('the keep is not left while its stairs do not take the player down', stuck_upstairs)


def keep_dialogue(pages, briefed):
    def run():
        world = Keep()
        world.chat.pages = list(pages)
        expect(run_wait(mc.fortress(world.log))).to_be(False)
        expect(mc.live_mordred_briefed()).to_be(briefed)
        expect(world.at).to_equal(mc.CATHERBY_CRATE_STAND)
    return run


test("a crate's Yes/No inside the keep is confirmed without counting as Morgan's brief",
     keep_dialogue([['Yes.', 'No.']], False))
test("Morgan's brief inside the keep is latched before leaving",
     keep_dialogue(['continue', ['Tell me how to untrap Merlin and I might.', 'Leave']], True))


def briefed_inside():
    world = Keep()
    run_wait(mc.live_fortress_step(world.log))
    mc.mordred_briefed = True
    expect(run_wait(mc.fortress(world.log))).to_be(False)
    expect(world.logged('already briefed')).to_be(True)
    expect(run_wait(mc.fortress(world.log))).to_be(True)


test('a briefed player leaves the keep, and outside it the fortress is done', briefed_inside)


def climbs_to_mordred():
    for level in [0, 1]:
        world = Keep(Tile(2769, 3404, level))
        world.locs = [world.stair('Staircase', 'Climb-up', 1)]
        expect(run_wait(mc.fortress(world.log))).to_be(False)
        expect(world.at.level).to_be(level + 1)


test("the keep's floors are climbed one per pass toward Mordred", climbs_to_mordred)


class Mordred(Keep):
    def __init__(self, talks=True):
        Keep.__init__(self, Tile(2769, 3399, 2))
        self.talks = talks
        self.hits = []
        self.hold(mc.WEAPON)
        self.on_walk = None
        self.locs = [self.stairs, self.crate]
        self.npcs = [self.thing('Sir Mordred', ['Attack'], at=Tile(2772, 3403, 2), interact=self.attack)]

    def walk(self, tile, radius=None, attempts=None, timeout_ms=None, log=None):
        self.walks.append(tile)
        if tile != mc.MORDRED_TILE and self.walk_ok:
            self.at = tile
        return self.walk_ok
        yield

    def attack(self, op):
        self.hits.append(op)
        if self.talks:
            self.chat.pages = ['continue', ['OK I will go do all that.']]
        return True


def fights_mordred():
    world = Mordred()
    expect(run_wait(mc.fortress(world.log))).to_be(False)
    expect(world.worn).to_equal([mc.WEAPON])
    expect(world.hits).to_equal(['Attack'])
    expect(mc.live_mordred_briefed()).to_be(True)
    expect(world.logged('after Mordred fight')).to_be(True)
    expect(world.at).to_equal(mc.CATHERBY_CRATE_STAND)


test("Mordred is fought until Morgan's brief opens, then the keep is left", fights_mordred)


def silent_mordred():
    world = Mordred(False)
    expect(run_wait(mc.fortress(world.log))).to_be(False)
    expect(mc.live_mordred_briefed()).to_be(False)
    expect(world.at.level).to_be(2)
    world = Mordred()
    world.chat.pages = [['Tell me how to untrap Merlin', 'Leave']]
    expect(run_wait(mc.fortress(world.log))).to_be(False)
    expect(world.hits).to_equal([])
    expect(mc.live_mordred_briefed()).to_be(True)
    world = Mordred()
    world.walk_ok = False
    expect(run_wait(mc.fortress(world.log))).to_be(False)


test('a fight that ends without the brief stays for another pass, and a brief opened on arrival skips it', silent_mordred)


def opening():
    world = Merlin()
    order = []
    spy_on(mc, 'fortress', impl=lambda log: result(order.append('fortress')))
    spy_on(mc, 'kill_giant_bat', impl=lambda log: result(order.append('bat')))
    spy_on(mc, 'talk_knights', impl=lambda log: result(order.append('knights')))
    candles = spy_on(mc, 'candle_maker_stage_four', impl=lambda log: result(False))
    run_wait(mc.opening_leg(world.log))
    candles.mock_implementation(lambda log: result(True))
    run_wait(mc.opening_leg(world.log))
    world.at = mc.BAT_ANCHOR
    run_wait(mc.opening_leg(world.log))
    world.at = KEEP_L0
    run_wait(mc.opening_leg(world.log))
    world.at = CAMELOT
    mc.mordred_briefed = True
    run_wait(mc.opening_leg(world.log))
    expect(order).to_equal(['knights', 'fortress', 'knights', 'bat', 'bat', 'fortress', 'bat'])


test('the opening goes knights, candle maker, then the fortress or the bat', opening)


def bat():
    world = Merlin(mc.BAT_ANCHOR)
    world.hold(mc.BAT_BONES)
    expect(run_wait(mc.kill_giant_bat(world.log))).to_be(True)
    world.pack = []
    world.ground = [world.thing(mc.BAT_BONES, ['Take'], interact=lambda op: world.hold(mc.BAT_BONES) is not None)]
    expect(run_wait(mc.kill_giant_bat(world.log))).to_be(True)
    world.pack = []
    world.ground = [world.thing(mc.BAT_BONES, ['Take'], interact=lambda op: False)]
    expect(run_wait(mc.kill_giant_bat(world.log))).to_be(False)
    world.ground = []
    expect(run_wait(mc.kill_giant_bat(world.log))).to_be(False)
    expect(world.logged('no Giant bat')).to_be(True)
    attacks = []
    world.npcs = [world.thing('Giant bat', ['Attack'], distance=4, interact=lambda op: attacks.append(op))]
    expect(run_wait(mc.kill_giant_bat(world.log))).to_be(False)
    expect(attacks).to_equal(['Attack'])
    world.walk_ok = False
    expect(run_wait(mc.kill_giant_bat(world.log))).to_be(False)


test("the bat's bones are taken when dropped, otherwise a bat is attacked for them", bat)


def wax():
    world = Merlin()
    world.hold(mc.WAX)
    expect(run_wait(mc.get_wax(world.log))).to_be(True)
    world.pack = []
    world.ground = [world.thing(mc.REPELLENT, ['Take'], interact=lambda op: world.hold(mc.REPELLENT) is not None)]
    expect(run_wait(mc.get_wax(world.log))).to_be(True)
    world.pack = []
    world.ground = [world.thing(mc.REPELLENT, ['Take'], interact=lambda op: False)]
    expect(run_wait(mc.get_wax(world.log))).to_be(False)
    world.ground = []
    expect(run_wait(mc.get_wax(world.log))).to_be(False)
    expect(world.walks[-1]).to_equal(mc.REPELLENT_SPAWN)
    world.hold(mc.REPELLENT)
    expect(run_wait(mc.get_wax(world.log))).to_be(False)
    expect(world.logged('no empty Bucket')).to_be(True)
    world.hold(mc.BUCKET, use_on=lambda hive: world.hold(mc.WAX) is not None)
    expect(run_wait(mc.get_wax(world.log))).to_be(False)
    expect(world.logged('no Beehive')).to_be(True)
    world.locs = [world.thing('Beehive', ['Take-from'])]
    expect(run_wait(mc.get_wax(world.log))).to_be(True)
    world.drop(mc.WAX)
    world.walk_ok = False
    expect(run_wait(mc.get_wax(world.log))).to_be(False)


test('wax comes from the beehive after the repellent, with a bucket', wax)


def candle():
    world = Merlin()
    world.hold(mc.LIT_CANDLE)
    expect(run_wait(mc.light_candle(world.log))).to_be(True)
    world.pack = []
    expect(run_wait(mc.light_candle(world.log))).to_be(False)
    world.hold(mc.UNLIT_CANDLE)
    world.hold(mc.TINDERBOX, use_on=lambda other: False)
    expect(run_wait(mc.light_candle(world.log))).to_be(False)
    world.drop(mc.TINDERBOX)
    world.hold(mc.TINDERBOX, use_on=lambda other: world.hold(mc.LIT_CANDLE) is not None)
    expect(run_wait(mc.light_candle(world.log))).to_be(True)


test('the black candle is lit with the tinderbox', candle)


def excalibur():
    world = Merlin()
    world.hold(mc.EXCALIBUR)
    expect(run_wait(mc.get_excalibur(world.log))).to_be(True)
    world.pack = []
    talked = []
    spy_on(mc, 'goto_npc', impl=lambda stop, hops, log: result(True))

    def talk(name, prefer, log):
        talked.append(name)
        if name == 'Beggar':
            world.hold(mc.EXCALIBUR)
        return True
        yield
    spy_on(mc, 'talk_through', impl=talk)
    expect(run_wait(mc.get_excalibur(world.log))).to_be(False)
    expect(world.logged('no Bread')).to_be(True)
    world.hold(mc.BREAD)
    world.npcs = [world.thing('Beggar', ['Talk-to'])]
    expect(run_wait(mc.get_excalibur(world.log))).to_be(True)
    expect(talked).to_equal(['The Lady of the Lake', 'The Lady of the Lake', 'Beggar'])


test('Excalibur comes from the Beggar after the Lady of the Lake', excalibur)


def jeweller_door():
    world = Merlin()
    world.hold(mc.BREAD)
    spy_on(mc, 'goto_npc', impl=lambda stop, hops, log: result(False))
    expect(run_wait(mc.get_excalibur(world.log))).to_be(False)
    expect(world.logged('no jeweller Door')).to_be(True)
    world.locs = [world.thing('Door', ['Open'], interact=lambda op: False)]
    expect(run_wait(mc.get_excalibur(world.log))).to_be(False)
    world.locs = [world.thing('Door', ['Open'])]
    expect(run_wait(mc.get_excalibur(world.log))).to_be(False)
    expect(world.logged('never appeared')).to_be(True)

    def opened(op):
        world.chat.pages = ['continue', ['Yes certainly.', 'No']]
        return True
    world.chat.on_choose = lambda text: world.hold(mc.EXCALIBUR)
    world.locs = [world.thing('Door', ['Open'], interact=opened)]
    expect(run_wait(mc.get_excalibur(world.log))).to_be(True)
    world.pack = [world.item(mc.BREAD)]
    world.walk_ok = False
    expect(run_wait(mc.get_excalibur(world.log))).to_be(False)


test("the Beggar is brought out by the jeweller's door when he isn't in the street", jeweller_door)


class Tower(Merlin):
    def __init__(self, breaks=True):
        Merlin.__init__(self, mc.TOWER_LADDER_0)
        self.breaks = breaks
        self.crystal = self.thing('Giant crystal', [], distance=2)
        self.locs = [self.stair('Ladder', 'Climb-up', 1), self.crystal]
        self.hold(mc.EXCALIBUR, use_on=self.strike)

    def strike(self, crystal):
        if self.breaks:
            self.locs = [loc for loc in self.locs if loc.name != 'Giant crystal']
        return True


def crystal():
    world = Tower()
    expect(run_wait(mc.try_break_crystal(world.log))).to_be('broke')
    expect(world.at).to_equal(mc.CRYSTAL_STAND)
    world = Tower(False)
    expect(run_wait(mc.try_break_crystal(world.log))).to_be('need-summon')
    world.drop(mc.EXCALIBUR)
    expect(run_wait(mc.try_break_crystal(world.log))).to_be('fail')
    world.locs = []
    expect(run_wait(mc.try_break_crystal(world.log))).to_be('fail')
    expect(world.logged('scene not synced')).to_be(True)
    world.locs = [world.thing('Ladder', ['Climb-down'])]
    expect(run_wait(mc.try_break_crystal(world.log))).to_be('broke')
    world.walk_ok = False
    expect(run_wait(mc.try_break_crystal(world.log))).to_be('fail')
    world.at = mc.TOWER_LADDER_0
    expect(run_wait(mc.try_break_crystal(world.log))).to_be('fail')
    world.walk_ok = True
    world.at = mc.TOWER_LADDER_1
    world.locs = []
    expect(run_wait(mc.try_break_crystal(world.log))).to_be('fail')


test('Excalibur breaks the crystal once Thrantax is summoned, and a missing crystal means it already broke', crystal)


def summon_and_break():
    world = Merlin()
    outcome = {'value': 'fail'}
    spy_on(mc, 'try_break_crystal', impl=lambda log: result(outcome['value']))
    spy_on(mc, 'descend_tower', impl=lambda log: result(True))
    summoned = spy_on(mc, 'summon_thrantax', impl=lambda log: result(True))
    reached = spy_on(mc, 'goto_npc', impl=lambda stop, hops, log: result(False))
    told = spy_on(mc, 'talk_through', impl=lambda name, prefer, log: result(True))
    expect(run_wait(mc.summon_and_break(world.log))).to_be(False)
    outcome['value'] = 'need-summon'
    expect(run_wait(mc.summon_and_break(world.log))).to_be(False)
    expect(len(summoned.calls)).to_be(1)
    outcome['value'] = 'broke'
    expect(run_wait(mc.summon_and_break(world.log))).to_be(False)
    reached.mock_implementation(lambda stop, hops, log: result(True))
    expect(run_wait(mc.summon_and_break(world.log))).to_be(True)
    expect(told.calls[0][0]).to_be('King Arthur')


test('a broken crystal is reported to King Arthur, and an unbroken one summons Thrantax', summon_and_break)


def thrantax():
    world = Merlin()
    checks = []
    world.locs = [world.thing('Chaos altar', ['Check'], interact=lambda op: checks.append(op))]
    world.hold(mc.LIT_CANDLE)
    expect(run_wait(mc.summon_thrantax(world.log))).to_be(False)
    expect(world.logged('no Bat bones')).to_be(True)
    expect(checks).to_equal(['Check'])
    world.hold(mc.BAT_BONES, interact=lambda op: False)
    expect(run_wait(mc.summon_thrantax(world.log))).to_be(False)
    world.drop(mc.BAT_BONES)
    world.hold(mc.BAT_BONES)
    expect(run_wait(mc.summon_thrantax(world.log))).to_be(False)
    expect(world.logged('did not appear')).to_be(True)
    world.npcs = [world.thing(mc.THRANTAX, ['Talk-to'])]
    world.chat.pages = ['continue', ['Snarthon Candtrick Termanto', 'Run']]
    expect(run_wait(mc.summon_thrantax(world.log))).to_be(True)
    expect(world.chat.chosen).to_equal(['Snarthon Candtrick Termanto'])
    world.drop(mc.LIT_CANDLE)
    expect(run_wait(mc.summon_thrantax(world.log))).to_be(False)
    world.walk_ok = False
    expect(run_wait(mc.summon_thrantax(world.log))).to_be(False)


test('Thrantax is summoned by dropping bat bones on the symbol with the candle lit', thrantax)


def weapon():
    world = Merlin()
    run_wait(mc.wield_weapon(world.log))
    expect(world.worn).to_equal([])
    world.hold(mc.WEAPON)
    run_wait(mc.wield_weapon(world.log))
    expect(world.worn).to_equal([mc.WEAPON])
    expect(world.logged('wielded')).to_be(True)


test('the rune mace is wielded when held', weapon)


def snap(journal, held=None):
    inv = {}
    for name in held if held is not None else []:
        inv[name.lower()] = 1
    return Fake(journal=journal, inv=inv)


def decides():
    expect(mc.decide(snap('complete')).kind).to_be('done')
    expect(mc.decide(snap('unknown')).kind).to_be('wait')
    expect(mc.decide(snap('not_started')).stop.npc).to_be('King Arthur')
    rows = [
        ([], mc.opening_leg),
        ([mc.WAX], mc.kill_giant_bat),
        ([mc.BAT_BONES], mc.get_wax),
        ([mc.BAT_BONES, mc.UNLIT_CANDLE], mc.light_candle),
        ([mc.BAT_BONES, mc.LIT_CANDLE], mc.get_excalibur),
        ([mc.BAT_BONES, mc.LIT_CANDLE, mc.EXCALIBUR], mc.summon_and_break),
    ]
    for held, leg in rows:
        expect(mc.decide(snap('in_progress', held)).run, str(held)).to_be(leg)
    expect(mc.decide(snap('in_progress', [mc.BAT_BONES, mc.WAX])).stop.npc).to_be('Candle maker')


test('decide walks the products from the opening to the crystal', decides)
