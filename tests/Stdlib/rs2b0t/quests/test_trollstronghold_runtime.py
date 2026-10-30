"""Troll Stronghold's shared combat, which Observatory Quest's guard fight uses too: the protection prayer, the walk that
holds it while something shoots, prayer potions, the one-action-a-tick fight loop and its mid-fight dialogue."""

import rs2004.quests.defs.trollstronghold.combat as combat
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.catalogs.tasks import sustain


def result(value):
    return value
    yield


class Fighter:
    """The player's prayer, health, pack and target, with a tick clock that moves on each wait."""

    def __init__(self, prayer_level=70):
        self.prayer_level = prayer_level
        self.points = 70
        self.max = 70
        self.praying = []
        self.set_ok = True
        self.hp = 70
        self.ate = 0
        self.pack = []
        self.npcs = []
        self.now = 0
        self.fighting = False
        self.pending = False
        self.foe = None
        self.hook = None
        self.lines = []
        self.chat = FakeChat().install(combat.chat_dialog)
        spy_on(combat.skills, 'level', impl=lambda name: self.prayer_level if name == 'prayer' else 70)
        spy_on(combat.skills, 'effective', impl=lambda name: self.hp)
        spy_on(combat.prayer, 'active', impl=lambda name: name in self.praying)
        spy_on(combat.prayer, 'points', impl=lambda: self.points)
        spy_on(combat.prayer, 'max', impl=lambda: self.max)
        spy_on(combat.prayer, 'set', impl=self.pray)
        spy_on(combat.inventory, 'items', impl=lambda: self.pack)
        spy_on(combat.npcs, 'query', impl=querying(lambda: self.npcs))
        spy_on(combat.game, 'tick', impl=lambda: self.now)
        spy_on(combat.game, 'in_combat', impl=lambda: self.fighting)
        spy_on(combat.game, 'set_auto_retaliate', returns=None)
        spy_on(combat.event_signal, 'pending', impl=lambda: self.pending)
        spy_on(sustain, 'run', impl=self.eat)
        spy_on(sustain, 'set', impl=self.set_hook)
        stub(sustain, hook=None)
        patch(execution, 'delay_until', instant_until)
        patch(execution, 'delay_ticks', self.ticks)

    def log(self, text):
        self.lines.append(text)

    def logged(self, part):
        return any([part in line for line in self.lines])

    def set_hook(self, fn):
        self.hook = fn

    def pray(self, name, on):
        if not self.set_ok:
            return False
        if on:
            self.praying.append(name)
        elif name in self.praying:
            self.praying.remove(name)
        return True
        yield

    def eat(self):
        self.ate += 1
        self.hp = 70
        return True
        yield

    def ticks(self, n=1):
        self.now += n
        if self.foe is not None and self.fighting:
            self.foe.life -= n
            self.points -= 1
            if self.foe.life <= 0:
                self.npcs.remove(self.foe)
                self.foe = None
                self.fighting = False
        return None
        yield

    def potion(self, name='Prayer potion(3)', drinks=True):
        def drink(op):
            if drinks:
                self.points = self.max
            return True
        item = Fake(name=name, actions=lambda: ['Drink', 'Drop'], interact=drink)
        self.pack.append(item)
        return item


class Troll:
    def __init__(self, fighter, life, index=1, name='Mountain troll'):
        self.fighter = fighter
        self.life = life
        self.index = index
        self.name = name
        self.attacks = 0

    def actions(self):
        return ['Attack']

    def targets_another_player(self):
        return False

    def distance(self):
        return 3

    def interact(self, op):
        self.attacks += 1
        self.fighter.fighting = True
        self.fighter.foe = self
        return True


def plan(fighter, protect='melee', guard=300, dialogue=None, on_dialogue=None, on_missing=None):
    return Record({
        'what': 'Mountain troll',
        'target': lambda: combat.attackable('Mountain troll', 10),
        'won': lambda: len(fighter.npcs) == 0,
        'protect': protect,
        'guard': guard,
        'dialogue': dialogue,
        'on_dialogue': on_dialogue,
        'on_missing': on_missing,
    })


def fights():
    fighter = Fighter()
    troll = Troll(fighter, 6)
    fighter.npcs = [troll]
    fighter.hp = 50
    fighter.potion()
    expect(run_wait(combat.fight(plan(fighter), fighter.log))).to_be(True)
    expect(troll.attacks).to_be(1)
    expect(fighter.ate).to_be(1)
    expect(fighter.praying).to_equal([])
    expect(fighter.logged('Mountain troll: done (1 attacks, 1 prayer re-arms)')).to_be(True)


test('a fight prays, eats when low, attacks once and drops the prayer when won', fights)


def sips():
    fighter = Fighter()
    fighter.points = 20
    fighter.npcs = [Troll(fighter, 3)]
    fighter.potion()
    expect(run_wait(combat.fight(plan(fighter), fighter.log))).to_be(True)
    expect(fighter.logged('sipped Prayer potion(3) — prayer 20 → 70')).to_be(True)
    expect(run_wait(combat.sip_prayer(fighter.log))).to_be(True)
    fighter.pack = [Fake(name='Prayer potion(4)', actions=lambda: ['Drink'], interact=lambda op: False)]
    expect(run_wait(combat.sip_prayer(fighter.log))).to_be(False)
    fighter.pack = [Fake(name=None, actions=lambda: ['Drink'], interact=lambda op: True)]
    expect(run_wait(combat.sip_prayer(fighter.log))).to_be(False)


test('prayer potions are sipped below half a bar, before the prayer is re-armed', sips)


def low_prayer():
    fighter = Fighter(1)
    fighter.npcs = [Troll(fighter, 3)]
    expect(run_wait(combat.fight(plan(fighter, 'magic'), fighter.log))).to_be(True)
    expect(fighter.logged('prayer below 37')).to_be(True)
    fighter = Fighter()
    fighter.set_ok = False
    protection = combat.Protection('missiles')
    expect(run_wait(protection.hold())).to_be(False)
    fighter.set_ok = True
    fighter.points = 0
    expect(run_wait(protection.hold())).to_be(False)


test('without the prayer level or points the fight goes on unprotected', low_prayer)


def gives_up():
    fighter = Fighter()
    troll = Troll(fighter, 9999)
    fighter.npcs = [troll]
    fighter.points = 999999
    fighter.max = 0
    expect(run_wait(combat.fight(plan(fighter, guard=50), fighter.log))).to_be(False)
    expect(troll.attacks).to_be(1)
    expect(fighter.logged('Mountain troll: gave up after 50 ticks')).to_be(True)
    expect(fighter.praying).to_equal(['protect from melee'])
    fighter.pending = True
    expect(run_wait(combat.fight(plan(fighter), fighter.log))).to_be(False)
    expect(fighter.logged('yielding to a random event')).to_be(True)


test('a fight that is not won keeps the prayer up and gives up at its guard, or yields to an event', gives_up)


def missing():
    fighter = Fighter()
    fighter.npcs = [Fake(name='Rock', actions=lambda: [], distance=lambda: 3)]
    looked = []

    def look():
        looked.append(1)
        return len(looked) < 3
        yield
    expect(run_wait(combat.fight(plan(fighter, on_missing=look), fighter.log))).to_be(False)
    expect(len(looked)).to_be(3)


test("a missing target is looked for by the plan's own leg until that gives up", missing)


def dialogue():
    fighter = Fighter()
    troll = Troll(fighter, 4)
    fighter.npcs = [troll]
    fighter.chat.pages = ['continue', ['Run away', 'I will fight you'], 'continue']
    chosen = []
    expect(run_wait(combat.fight(plan(fighter, dialogue=['fight you'], on_dialogue=chosen.append), fighter.log))).to_be(True)
    expect(chosen).to_equal(['I will fight you'])
    fighter.chat.pages = [['Dance']]
    run_wait(combat.drain_dialogue(['fight'], None, fighter.log))
    expect(fighter.logged('mid-fight dialogue had no preferred option in [Dance]')).to_be(True)


test("mid-fight dialogue is answered from the plan's preferences", dialogue)


def broken_fight():
    fighter = Fighter()
    fighter.npcs = []

    def boom(p, prayers, log):
        raise ValueError('lost the client')
        yield
    spy_on(combat, 'fight_rounds', impl=boom)
    expect(lambda: run_wait(combat.fight(plan(fighter), fighter.log))).to_throw('lost the client')
    expect(fighter.praying).to_equal([])
    fighter.npcs = [Troll(fighter, 1)]
    expect(lambda: run_wait(combat.fight(plan(fighter), fighter.log))).to_throw('lost the client')
    expect(fighter.praying).to_equal(['protect from melee'])


test('a broken fight drops the prayer only once the fight is won', broken_fight)


def guarded_walk():
    fighter = Fighter()
    host_calls = []

    def host():
        host_calls.append(1)
        return result(True)
    stub(sustain, hook=host)
    shooting = [True]

    def walk():
        yield from fighter.hook()
        shooting[0] = False
        yield from fighter.hook()
        fighter.points = 10
        fighter.potion()
        yield from fighter.hook()
        return 'arrived'
    expect(run_wait(combat.protected_walk('missiles', lambda: shooting[0], walk, fighter.log))).to_be('arrived')
    expect(fighter.logged('holding Protect from Missiles')).to_be(True)
    expect(fighter.logged('dropping Protect from Missiles — nothing in range')).to_be(True)
    expect(fighter.logged('sipped Prayer potion(3)')).to_be(True)
    expect(len(host_calls)).to_be(2)
    expect(fighter.hook).to_be(host)
    expect(fighter.praying).to_equal([])


test('a protected walk holds the prayer only while something shoots, sips on the way and restores the hook', guarded_walk)


def broken_walk():
    fighter = Fighter()
    stub(sustain, hook=lambda: None)

    def walk():
        yield from fighter.hook()
        raise ValueError('lost the client')
    expect(lambda: run_wait(combat.protected_walk('magic', lambda: True, walk, fighter.log))).to_throw('lost the client')
    expect(fighter.praying).to_equal([])
    expect(fighter.hook is not None).to_be(True)


test('a broken protected walk still drops the prayer and puts the host hook back', broken_walk)
