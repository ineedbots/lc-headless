"""Chronozon's fight: phase 17f's live run died to him on casts the server refused, because something else was hitting
the account in a single-way area."""

import rs2004.quests.defs.familycrest.chronozon as cz
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.geometry import Tile

CHRONOZON_ID = cz.FC_NPC.CHRONOZON_NPC_ID


def nothing():
    return None
    yield


class FakeNpc:
    def __init__(self, id, name, index, targets):
        self.id = id
        self.name = name
        self.index = index
        self.targets = targets
        self.attacks = 0
        self.on_attack = None

    def targets_me(self):
        return self.targets

    def tile(self):
        return Tile(3089, 9940)

    def distance(self):
        return 8

    def interact(self, op):
        self.attacks += 1
        if self.on_attack is not None:
            self.on_attack()
        return True


class Lair:
    def __init__(self):
        self.npcs = [FakeNpc(CHRONOZON_ID, 'Chronozon', 1, True)]
        self.lines = []
        self.casts = []
        self.logs = []
        self.now = 0
        self.on_cast = None
        spy_on(cz.npcs, 'query', impl=querying(lambda: self.npcs))
        spy_on(cz.game, 'tile', impl=lambda: cz.SAFESPOT)
        spy_on(cz.game, 'facing', impl=lambda: None)
        spy_on(cz.game, 'cast_on_npc', impl=self.cast)
        spy_on(cz.game_messages, 'mark', impl=lambda: len(self.lines))
        spy_on(cz.game_messages, 'saw_since', impl=lambda mark, needle: any([needle in line.lower() for line in self.lines[mark:]]))
        spy_on(cz.sustain, 'run', impl=nothing)
        spy_on(execution, 'delay_until', impl=instant_until)
        spy_on(execution, 'delay_ticks', impl=self.tick)
        spy_on(cz._core, 'step_time', impl=lambda: self.now)

    def tick(self, n=1):
        self.now += 600
        return None
        yield

    def cast(self, spell, target):
        self.casts.append(spell)
        if self.on_cast is not None:
            self.on_cast()
        return True

    def state(self):
        return Record({'safespot': False})


def blocked_by_spider():
    lair = Lair()
    spider = FakeNpc(134, 'Poison spider', 2, True)
    spider.on_attack = lambda: lair.npcs.remove(spider)
    lair.npcs.append(spider)
    result = run_wait(cz._cast_blast('Wind blast', lair.state(), lair.logs.append))
    expect(result).to_be('blocked')
    expect(spider.attacks).to_be(1)
    expect(lair.casts).to_equal([])


test('a follower is killed before a cast is wasted on the demon', blocked_by_spider)


def demon_alone():
    lair = Lair()
    lair.on_cast = lambda: lair.lines.append('Chronozon weakens...')
    result = run_wait(cz._cast_blast('Wind blast', lair.state(), lair.logs.append))
    expect(result).to_be('landed')
    expect(lair.casts).to_equal(['Wind blast'])
    expect(lair.npcs[0].attacks).to_be(0)


test('the demon itself attacking us is no reason to stop casting', demon_alone)


def refused_cast():
    lair = Lair()
    lair.on_cast = lambda: lair.lines.append("I'm already under attack!")
    result = run_wait(cz._cast_blast('Wind blast', lair.state(), lair.logs.append))
    expect(result).to_be('blocked')


test("a refused cast reads as blocked, not as a miss that shows the safespot is bad", refused_cast)


def gives_up_in_time():
    lair = Lair()
    spider = FakeNpc(134, 'Poison spider', 2, True)
    lair.npcs.append(spider)
    expect(run_wait(cz.clear_attacker(lair.logs.append))).to_be(True)
    expect(lair.now >= cz.CLEAR_ATTACKER_MS).to_be(True)


test('a follower that will not die does not hold the fight for ever', gives_up_in_time)
