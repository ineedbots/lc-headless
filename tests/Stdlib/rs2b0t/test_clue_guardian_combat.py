"""rs2b0t's test/api/ai/clues/guardianCombat.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and
expect, with the facades patched as rs2b0t spies on them. A face target of 32768 is us, 32769 another player."""

from rs2004 import execution
from rs2004.catalogs.tasks import sustain
from rs2004.clues.executor import ClueExecutor
from rs2004.clues.guardian import GuardianEncounter, GuardianProtection, fight_guardian
from rs2004.clues.plan import SUPERANTI, GuardianRangedLoadout

MINE = 32768
FOREIGN = 32769
DEAD = 'Oh dear, you are dead!'


class Held:
    def __init__(self, id, name, count=1, slot=0):
        self.id = id
        self.name = name
        self.count = count
        self.slot = slot
        self.noted = False


def wizard(name='Saradomin Wizard', distance=1, tile=None, face=32768):
    return {'index': 4, 'id': 1, 'name': name, 'size': 1, 'tile': tile or Tile(3000, 3000, 0), 'distance': distance,
            'health': 40, 'max_health': 40, 'face': face}


def bow_loadout():
    return GuardianRangedLoadout('Magic shortbow', 'Rune arrow', 500, 1)


class Fight:
    def __init__(self):
        self.tick = 0
        self.energy = 1000
        self.armed = False
        self.events = []
        self.advance = None
        self.pack = [Held(185, 'Superantipoison(1)'), Held(385, 'Shark', 15), Held(1231, 'Dragon dagger(p)')]
        self.worn = []
        self.npcs = [wizard()]
        self.messages = []
        self.pending = False
        self.in_combat = False
        self.here = None
        self.special_ready = None
        self.mode = 0
        self.on_interact = None
        self.on_attack = None
        self.on_equip = None
        self.on_walk_to = None
        self.interacts = 0
        self.attacks = 0
        self.walk_tos = 0
        self.walks = 0

    def install(self):
        w = self
        stub(sustain, hook=None)
        spy_on(inventory, 'items', lambda: [w.held(i) for i in w.pack])
        spy_on(inventory, 'first', lambda name: w.first(name))
        spy_on(inventory, 'count', lambda name: sum([i.count for i in w.pack if i.name == name]))
        spy_on(inventory, 'count_by_id', lambda id: sum([i.count for i in w.pack if i.id == id]))
        spy_on(inventory, 'is_full', lambda: False)
        spy_on(equipment, 'items', lambda: list(w.worn))
        spy_on(equipment, 'equip', lambda name: w.equip(name))
        spy_on(npcs, 'query', querying(lambda: [w.npc(n) for n in w.npcs]))
        spy_on(skills, 'level', lambda name: 60)
        spy_on(skills, 'effective', lambda name: 60)
        spy_on(quests, 'status', lambda name: 'complete')
        spy_on(game, 'tick', lambda: w.tick)
        spy_on(game, 'in_combat', lambda: w.in_combat)
        spy_on(game, 'tile', lambda: w.here)
        spy_on(game, 'combat_mode', lambda: w.mode)
        spy_on(game, 'set_combat_mode', lambda mode: w.set_mode(mode))
        spy_on(event_signal, 'pending', lambda: w.pending)
        patch(execution, 'delay_until', instant_until)
        patch(execution, 'delay_until_ticks', instant_until_ticks)
        patch(execution, 'delay_ticks', lambda n=1: w.ticks(n))
        spy_on(prayer, 'set', lambda name, on: instant_until(lambda: True))
        spy_on(special, 'wielded', lambda: w.worn[0].name if w.worn else '')
        spy_on(special, 'ready', lambda name: w.energy >= 250 if w.special_ready is None else w.special_ready)
        spy_on(special, 'armed', lambda: w.armed)
        spy_on(special, 'arm', lambda: w.arm())
        spy_on(game_messages, 'mark', lambda: len(w.messages))
        spy_on(game_messages, 'saw_since', lambda mark, pattern: any([pattern.lower() in m.lower() for m in w.messages[mark:]]))
        spy_on(game_messages, 'since', lambda mark: [Fake(text=m) for m in w.messages[mark:]])
        spy_on(reachability, 'probeable', lambda tile: False)
        spy_on(traversal, 'walk_to', lambda tile, **opts: w.walk_to(tile, opts))
        spy_on(chat_dialog, 'can_continue', lambda: False)
        spy_on(chat_dialog, 'is_open', lambda: False)
        spy_on(reader, 'count_dialog_open', lambda: False)
        spy_on(modals, 'close', lambda: instant_until(lambda: True))
        spy_on(settings_store, 'save', lambda *a: None)
        return self

    def first(self, name):
        for i in self.pack:
            if i.name == name:
                return self.held(i)
        return None

    def ticks(self, n):
        self.tick += n
        if self.advance is not None:
            self.advance()
        return None
        yield

    def walk(self):
        self.walks += 1
        self.events.append(f'walk:{self.tick}')
        return True
        yield

    def set_mode(self, mode):
        self.mode = mode
        return True

    def equip(self, name):
        if self.on_equip is not None:
            on = yield from self.on_equip(name)
            return on
        found = [i for i in self.pack if i.name == name]
        if not found:
            return False
        self.worn = [Held(found[0].id, found[0].name, found[0].count, 3)]
        self.pack = [i for i in self.pack if i is not found[0]]
        self.events.append(f'equip:{self.tick}')
        return True
        yield

    def arm(self):
        self.events.append(f'special:{self.tick}')
        self.armed = True
        return True
        yield

    def walk_to(self, tile, opts):
        self.walk_tos += 1
        if self.on_walk_to is not None:
            reached = yield from self.on_walk_to(tile, opts)
            return reached
        return False
        yield

    def held(self, i):
        w = self
        item = i

        def interact(op):
            w.interacts += 1
            if w.on_interact is not None:
                return w.on_interact(item, op)
            w.events.append(f'drink:{w.tick}')
            w.pack = [p for p in w.pack if p.id != item.id]
            return True

        return Fake(id=i.id, name=i.name, count=i.count, slot=i.slot, noted=False, actions=lambda: ['Drink', 'Eat', 'Wield', 'Dig'], interact=interact)

    def npc(self, n):
        w = self

        def interact(op):
            w.attacks += 1
            if w.on_attack is not None:
                return w.on_attack()
            w.events.append(f'attack:{w.tick}')
            if w.armed:
                w.energy -= 250
                w.armed = False
            for other in w.npcs:
                other['health'] = 0
            return True

        return Fake(index=n['index'], id=n['id'], name=n['name'], size=n['size'], health=n['health'], max_health=n['max_health'],
                    distance=lambda: n['distance'], tile=lambda: n['tile'], actions=lambda: ['Attack'], interact=interact,
                    targets_me=lambda: n['face'] == MINE, targets_another_player=lambda: n['face'] >= MINE and n['face'] != MINE)

    def sharks(self, count):
        for i in self.pack:
            if i.id == 385:
                i.count = count

    def shark_count(self):
        return sum([i.count for i in self.pack if i.id == 385])

    def despawn_dead(self):
        if self.npcs and self.npcs[0]['health'] == 0:
            self.npcs = []

    def attacked(self):
        return any([e.startswith('attack:') for e in self.events])


def prepared(w, protection=None):
    p = protection or GuardianProtection()
    run_wait(p.prepare())
    return p


def fight(name='Saradomin Wizard', protection=None):
    return run_wait(fight_guardian(name, lambda m: None, protection))


def dds_and_dose():
    w = Fight().install()
    protection = GuardianProtection()
    expect(run_wait(protection.prepare())).to_be(True)
    expect(w.worn[0].id).to_be(1231)
    expect(any([i.id == 185 for i in w.pack])).to_be(False)
    expect(run_wait(protection.maintain())).to_be('ready')


def bow_kit(w):
    w.pack = [i for i in w.pack if i.id != 1231]
    w.worn = [Held(861, 'Magic shortbow', 1, 3), Held(892, 'Rune arrow', 50, 13)]


def ranged_fight():
    w = Fight().install()
    bow_kit(w)
    spy_on(skills, 'level', lambda name: 1)
    spy_on(quests, 'status', lambda name: 'not_started')
    w.here = Tile(2995, 3000, 0)
    spy_on(reachability, 'probeable', lambda tile: True)
    spy_on(reachability, 'line_of_sight', lambda a, b, size=1: True)
    w.npcs[0]['distance'] = 5
    protection = GuardianProtection('Saradomin Wizard', bow_loadout())
    expect(run_wait(protection.prepare())).to_be(True)
    w.advance = w.despawn_dead
    expect(fight('Saradomin Wizard', protection)).to_be('killed')
    expect(w.walk_tos).to_be(0)
    expect(w.worn[0].id).to_be(861)
    expect(w.mode).to_be(1)
    expect(w.attacked()).to_be(True)
    w.npcs = [wizard('Saradomin Wizard', 5)]
    w.worn = [i for i in w.worn if i.slot != 13]
    attacks = w.attacks
    expect(fight('Saradomin Wizard', protection)).to_be('supplies-needed')
    expect(w.attacks).to_be(attacks)


def ranged_stand():
    w = Fight().install()
    bow_kit(w)
    w.here = Tile(2990, 3000, 0)
    stand = Tile(2993, 3000, 0)
    w.mode = 1
    spy_on(reachability, 'probeable', lambda tile: True)
    spy_on(reachability, 'line_of_sight', lambda a, b, size=1: stand.equals(a))
    spy_on(reachability, 'can_reach', lambda tile, **opts: stand.equals(tile))
    spy_on(reachability, 'can_step', lambda a, b: True)
    seen = []

    def walk(tile, opts):
        seen.append(tile.equals(stand))
        w.here = stand
        w.npcs[0]['distance'] = 7
        return True
        yield

    w.on_walk_to = walk
    w.npcs[0]['distance'] = 10
    protection = GuardianProtection('Saradomin Wizard', bow_loadout())
    expect(run_wait(protection.prepare())).to_be(True)
    w.advance = w.despawn_dead
    expect(fight('Saradomin Wizard', protection)).to_be('killed')
    expect(seen).to_equal([True])


def longsword(already_worn):
    w = Fight().install()
    w.pack = [i for i in w.pack if i.id != 1231]
    if already_worn:
        w.worn = [Held(1305, 'Dragon longsword', 1, 3)]
    else:
        w.pack.append(Held(1305, 'Dragon longsword'))
    protection = GuardianProtection()
    expect(run_wait(protection.prepare())).to_be(True)
    expect(w.worn[0].id).to_be(1305)
    expect(any([i.id == 185 for i in w.pack])).to_be(False)
    w.advance = w.despawn_dead
    expect(fight('Saradomin Wizard', protection)).to_be('killed')
    expect(w.attacked()).to_be(True)


def escape_reserve(count):
    w = Fight().install()
    w.sharks(count)
    expect(run_wait(GuardianProtection().prepare())).to_be(count > 3)
    expect(w.interacts).to_be(1 if count > 3 else 0)


def three_escape(count):
    w = Fight().install()
    protection = prepared(w)
    w.sharks(count)
    stub(sustain, hook=lambda: w.sharks(3))
    w.advance = w.despawn_dead
    expect(fight('Saradomin Wizard', protection)).to_be('supplies-needed')
    expect(w.attacks).to_be(0)
    expect(w.shark_count()).to_be(3)


def untrusted_dose():
    w = Fight().install()
    w.on_interact = lambda item, op: True
    expect(run_wait(GuardianProtection().prepare())).to_be(False)
    expect(w.interacts).to_be(3)


def transient(sent):
    w = Fight().install()
    attempts = []

    def drink(item, op):
        attempts.append(w.tick)
        if len(attempts) == 1:
            return sent
        w.pack = [p for p in w.pack if p.id != item.id]
        return True

    w.on_interact = drink
    protection = GuardianProtection()
    expect(run_wait(protection.prepare())).to_be(True)
    expect(len(attempts)).to_be(2)
    expect(attempts[1] - attempts[0] >= 2).to_be(True)
    expect(run_wait(protection.maintain())).to_be('ready')


def late_confirmation():
    w = Fight().install()
    w.on_interact = lambda item, op: True

    def landed():
        w.pack = [p for p in w.pack if p.id != 185]

    w.advance = landed
    protection = GuardianProtection()
    expect(run_wait(protection.prepare())).to_be(True)
    expect(w.interacts).to_be(1)
    expect(run_wait(protection.maintain())).to_be('ready')


def reserve_stops_retries():
    w = Fight().install()
    w.on_interact = lambda item, op: False
    stub(sustain, hook=lambda: w.sharks(3))
    expect(run_wait(GuardianProtection().prepare())).to_be(False)
    expect(w.interacts).to_be(1)
    expect(w.shark_count()).to_be(3)


def refreshes():
    w = Fight().install()
    protection = prepared(w)
    w.pack.append(Held(185, 'Superantipoison(1)'))
    w.tick += 540
    expect(run_wait(protection.maintain())).to_be('drank')
    w.pack.append(Held(185, 'Superantipoison(1)'))
    w.messages.append('You have been poisoned!')
    expect(run_wait(protection.maintain())).to_be('drank')


def first_bite():
    w = Fight().install()
    protection = prepared(w)
    state = {'eaten': False}

    def eat():
        if not state['eaten']:
            state['eaten'] = True
            w.sharks(14)
            w.events.append(f'eat:{w.tick}')

    stub(sustain, hook=eat)
    w.advance = w.despawn_dead
    expect(fight('Saradomin Wizard', protection)).to_be('killed')
    expect(w.energy).to_be(750)
    bite = [e.split(':')[1] for e in w.events if e.startswith('eat:')][0]
    expect(w.events).not_.to_contain(f'attack:{bite}')


def death_not_victory():
    w = Fight().install()
    protection = prepared(w)

    def die():
        w.messages.append(DEAD)
        w.npcs = []

    stub(sustain, hook=die)
    expect(fight('Saradomin Wizard', protection)).to_be('dead')


def incoming_only():
    w = Fight().install()
    protection = prepared(w)
    w.in_combat = True

    def advance():
        if (w.npcs and w.npcs[0]['health'] == 0) or w.tick > 8:
            w.npcs = []

    w.advance = advance
    expect(fight('Saradomin Wizard', protection)).to_be('killed')
    expect(len([e for e in w.events if e.startswith('attack:')])).to_be(1)
    expect(w.energy).to_be(750)


def resumes_after_eating():
    w = Fight().install()
    protection = prepared(w)
    w.in_combat = True
    w.special_ready = False
    state = {'attacking': False, 'eaten': False}
    attacks = []

    def attack():
        attacks.append(w.tick)
        state['attacking'] = True
        return True

    def eat():
        if state['attacking'] and not state['eaten']:
            state['eaten'] = True
            state['attacking'] = False
            w.sharks(14)

    def advance():
        if (w.npcs and w.npcs[0]['health'] == 0) or w.tick > 40:
            w.npcs = []
        elif state['attacking'] and state['eaten']:
            for n in w.npcs:
                n['health'] = 0

    w.on_attack = attack
    stub(sustain, hook=eat)
    w.advance = advance
    expect(fight('Saradomin Wizard', protection)).to_be('killed')
    expect(state['eaten']).to_be(True)
    expect(len(attacks)).to_be(2)
    expect(4 <= attacks[1] - attacks[0] <= 10).to_be(True)


def bounded_retries():
    w = Fight().install()
    protection = prepared(w)
    w.in_combat = True
    w.special_ready = False
    attacks = []

    def attack():
        attacks.append(w.tick)
        return True

    end = w.tick + 25

    def advance():
        if w.tick >= end:
            w.npcs = []

    w.on_attack = attack
    w.advance = advance
    expect(fight('Saradomin Wizard', protection)).to_be('guardian-lost')
    expect(len(attacks) >= 3).to_be(True)
    expect(all([4 <= attacks[i] - attacks[i - 1] <= 10 for i in range(1, len(attacks))])).to_be(True)


def unwitnessed_despawn():
    w = Fight().install()
    protection = prepared(w)
    stub(sustain, hook=lambda: w.npcs.clear())
    expect(fight('Saradomin Wizard', protection)).to_be('guardian-lost')


def foreign_never_attacked():
    w = Fight().install()
    protection = prepared(w)
    w.npcs[0]['face'] = FOREIGN
    expect(fight('Saradomin Wizard', protection)).to_be('guardian-lost')
    expect(w.attacks).to_be(0)


describe('guardian protection and combat', lambda: [
    test('equips DDS and confirms the final potion dose before the dig', dds_and_dose),
    test('ranged guardians keep the bow, shoot from range, and stop when equipped arrows run out', ranged_fight),
    test('ranged guardian approach stops at a reachable firing tile instead of walking into melee', ranged_stand),
    test('prepares and defeats a guardian with a dragon longsword: already worn False', lambda: longsword(False)),
    test('prepares and defeats a guardian with a dragon longsword: already worn True', lambda: longsword(True)),
    test('guardian preparation needs food above the escape reserve: 3 Sharks', lambda: escape_reserve(3)),
    test('guardian preparation needs food above the escape reserve: 4 Sharks', lambda: escape_reserve(4)),
    test('guardian stops before attacking with three escape Sharks: starts with 3', lambda: three_escape(3)),
    test('guardian stops before attacking with three escape Sharks: starts with 4', lambda: three_escape(4)),
    test('does not trust a potion interaction without a dose change', untrusted_dose),
    test('retries a transient potion preparation failure: click returned False', lambda: transient(False)),
    test('retries a transient potion preparation failure: click returned True', lambda: transient(True)),
    test('accepts a late final-dose confirmation without sending another drink', late_confirmation),
    test('stops preparation retries when upkeep reaches the escape food reserve', reserve_stops_retries),
    test('refreshes before protection expires and cures a poison message', refreshes),
    test('the first eaten Shark does not abort combat and DDS energy is spent', first_bite),
    test('death is not victory even when the guardian disappears', death_not_victory),
    test('sends the initial DDS attack when only incoming combat is active', incoming_only),
    test('resumes attacking after eating cancels outgoing combat with retaliation off', resumes_after_eating),
    test('bounds attack retries while incoming combat hides a stalled attack', bounded_retries),
    test('despawn without a witnessed death is not a kill', unwitnessed_despawn),
    test('a foreign guardian is never attacked', foreign_never_attacked),
])


# The guarded trail, through the executor

def guarded_trail(w, guardian='Saradomin Wizard', clue=3526):
    w.pack.extend([Held(clue, 'Clue scroll (hard)'), Held(952, 'Spade'), Held(2574, 'Sextant'), Held(2575, 'Watch'), Held(2576, 'Chart')])
    for n in w.npcs:
        n['name'] = guardian
    spy_on(traversal, 'walk_resilient', lambda dest, **opts: w.walk())


def solve(ranged=None):
    return run_wait(ClueExecutor().solve_held_clue(lambda m: None, None, ranged))


def refuses_without(id):
    w = Fight().install()
    w.pack = [Held(3526, 'Clue scroll (hard)')] + [i for i in w.pack if i.id != id]
    spy_on(traversal, 'walk_resilient', lambda dest, **opts: w.walk())
    expect(solve()).to_be('supplies-needed')
    expect(w.interacts).to_be(0)
    expect(w.walks).to_be(0)
    expect(any([i.id == 3526 for i in w.pack])).to_be(True)


def swap_clue(w, old, new):
    for i in w.pack:
        if i.id == old:
            i.id = new


def ranged_trail():
    w = Fight().install()
    guarded_trail(w, 'Zamorak Wizard', 2723)
    bow_kit(w)
    spy_on(skills, 'level', lambda name: 1)
    spy_on(quests, 'status', lambda name: 'not_started')
    w.here = Tile(2995, 3000, 0)
    w.mode = 1
    spy_on(reachability, 'probeable', lambda tile: True)
    spy_on(reachability, 'line_of_sight', lambda a, b, size=1: True)
    w.npcs[0]['distance'] = 5
    state = {'digs': 0}

    def dig(item, op):
        if op == 'Dig':
            state['digs'] += 1
            if state['digs'] == 2:
                swap_clue(w, 2723, 2724)
                w.pending = True
        return True

    w.on_interact = dig
    w.advance = w.despawn_dead
    expect(solve(bow_loadout())).to_be('yield')
    expect(state['digs']).to_be(2)
    expect([i.id for i in w.worn if i.slot == 3]).to_equal([861])
    expect(any([i.id == 2724 for i in w.pack])).to_be(True)
    expect(w.attacked()).to_be(True)


def sextant012():
    w = Fight().install()
    guarded_trail(w)
    swap_clue(w, 3526, 2745)
    w.here = Tile(3053, 3696, 0)
    digs = []
    spy_on(GuardianProtection, 'prepare', lambda *a: instant_until(lambda: True))

    def chase(*a):
        w.here = Tile(3056, 3697, 0)
        return 'killed'
        yield

    spy_on(GuardianEncounter, 'fight', chase)

    def walk(dest, opts):
        w.here = Tile(dest.x + opts.get('radius', 0), dest.z, dest.level)
        return True
        yield

    spy_on(traversal, 'walk_resilient', lambda dest, **opts: walk(dest, opts))

    def dig(item, op):
        if item.id != 952 or op != 'Dig':
            return False
        digs.append(w.here)
        if len(digs) == 2:
            swap_clue(w, 2745, 2746)
            w.pending = True
        return True

    w.on_interact = dig
    expect(solve()).to_be('yield')
    expect([(t.x, t.z) for t in digs]).to_equal([(3054, 3696), (3054, 3696)])
    expect(any([i.id == 2746 for i in w.pack])).to_be(True)


def event_during_potion(phase):
    w = Fight().install()
    guarded_trail(w)
    state = {'drinks': 0, 'digs': 0}

    def act(item, op):
        if op == 'Dig':
            state['digs'] += 1
        if op == 'Drink':
            state['drinks'] += 1
            if phase == 'retry':
                return False
            w.pack = [p for p in w.pack if p.id != item.id]
        return True

    def fire():
        w.pending = True

    w.on_interact = act
    w.advance = fire
    expect(solve()).to_be('yield')
    expect(state['drinks']).to_be(1)
    expect(state['digs']).to_be(0)
    expect(w.attacks).to_be(0)


def travel_bite(count):
    w = Fight().install()
    guarded_trail(w)
    w.sharks(count)

    def walk():
        w.sharks(14)
        return True
        yield

    spy_on(traversal, 'walk_resilient', lambda dest, **opts: walk())
    state = {'digs': 0}

    def act(item, op):
        if op == 'Drink':
            w.pack = [p for p in w.pack if p.id != item.id]
        if op == 'Dig':
            state['digs'] += 1
            if state['digs'] == 2:
                swap_clue(w, 3526, 3528)
        return True

    w.on_interact = act
    w.advance = w.despawn_dead
    expect(solve()).to_be('supplies-needed')
    expect(state['digs']).to_be(2)
    expect(w.attacks).to_be(1)
    expect(w.shark_count()).to_be(14)


def three_sharks_kept():
    w = Fight().install()
    guarded_trail(w)
    w.sharks(3)
    expect(solve()).to_be('supplies-needed')
    expect(w.walks).to_be(0)
    expect(w.interacts).to_be(0)
    expect(w.shark_count()).to_be(3)


def drinks_near_dig():
    w = Fight().install()
    guarded_trail(w)
    state = {'digs': 0}

    def act(item, op):
        if op == 'Drink':
            w.events.append(f'drink:{w.tick}')
            w.pack = [p for p in w.pack if p.id != item.id]
        if op == 'Dig':
            state['digs'] += 1
            w.events.append(f'dig:{w.tick}')
            if state['digs'] == 2:
                swap_clue(w, 3526, 3528)
        return True

    def upkeep():
        if state['digs'] == 1:
            w.sharks(14)

    w.on_interact = act
    stub(sustain, hook=upkeep)
    w.advance = w.despawn_dead
    expect(solve()).to_be('supplies-needed')
    expect(state['digs']).to_be(2)
    order = [e.split(':')[0] for e in w.events]
    expect(order.index('walk') < order.index('drink')).to_be(True)
    expect(order.index('drink') < order.index('dig')).to_be(True)
    expect(any([i.id == 3528 for i in w.pack])).to_be(True)


def death_halts():
    w = Fight().install()
    guarded_trail(w)
    state = {'digs': 0}

    def act(item, op):
        if op == 'Drink':
            w.pack = [p for p in w.pack if p.id != item.id]
        if op == 'Dig':
            state['digs'] += 1
            w.messages.append(DEAD)
            w.npcs = []
        return True

    w.on_interact = act
    executor = ClueExecutor()
    expect(run_wait(executor.solve_held_clue(lambda m: None))).to_be('dead')
    expect(run_wait(executor.solve_held_clue(lambda m: None))).to_be('dead')
    expect(state['digs']).to_be(1)
    expect(any([i.id == 3526 for i in w.pack])).to_be(True)


def dose_name(id, fallback=''):
    for d in SUPERANTI:
        if d['id'] == id:
            return d['name']
    return fallback


def dose_transition(id, next_id):
    w = Fight().install()
    for i in w.pack:
        if i.id == 185:
            i.id = id
            i.name = dose_name(id)

    def drink(item, op):
        for p in w.pack:
            if p.id == item.id:
                p.id = next_id
                p.name = dose_name(next_id, 'Vial')
        return True

    w.on_interact = drink
    protection = GuardianProtection()
    expect(run_wait(protection.prepare())).to_be(True)
    expect(run_wait(protection.maintain())).to_be('ready')


def immunity_bound():
    w = Fight().install()
    protection = prepared(w)
    w.tick = 540
    expect(run_wait(protection.maintain())).to_be('ready')
    w.tick = 570
    expect(run_wait(protection.maintain())).to_be('supplies-needed')


def untrusted_equip():
    w = Fight().install()

    def equip(name):
        return True
        yield

    w.on_equip = equip
    expect(run_wait(GuardianProtection().prepare())).to_be(False)
    expect(w.interacts).to_be(0)


def last_spawn_tick():
    w = Fight().install()
    protection = prepared(w)
    guardian = w.npcs[0]
    w.npcs = []
    spawn_at = w.tick + 10

    def advance():
        if w.tick == spawn_at:
            w.npcs = [guardian]
        else:
            w.despawn_dead()

    w.advance = advance
    expect(fight('Saradomin Wizard', protection)).to_be('killed')


def potion_delay():
    w = Fight().install()
    prepared(w)
    expect(w.tick).to_be(3)


def displaced(distance):
    w = Fight().install()
    protection = prepared(w)
    w.npcs[0]['distance'] = distance
    w.npcs[0]['tile'] = Tile(3000 + distance, 3000, 0)
    seen = []

    def walk(tile, opts):
        seen.append((opts.get('use_teleport_catalog'), opts.get('policy', {}).get('use_teleports')))
        w.npcs[0]['distance'] = 1
        return True
        yield

    w.on_walk_to = walk
    w.advance = w.despawn_dead
    expect(fight('Saradomin Wizard', protection)).to_be('killed')
    expect(seen).to_equal([(False, False)])
    expect(w.attacked()).to_be(True)


def no_foreign_chase():
    w = Fight().install()
    protection = prepared(w)
    w.npcs[0]['distance'] = 20
    w.npcs[0]['face'] = FOREIGN

    def walk(tile, opts):
        return True
        yield

    w.on_walk_to = walk
    expect(fight('Saradomin Wizard', protection)).to_be('guardian-lost')
    expect(w.walk_tos).to_be(0)
    expect(w.attacked()).to_be(False)


def approach_fails(outcome):
    w = Fight().install()
    protection = prepared(w)
    w.npcs[0]['distance'] = 3

    def walk(tile, opts):
        if outcome == 'event':
            w.pending = True
        if outcome == 'death':
            w.messages.append(DEAD)
        return False
        yield

    w.on_walk_to = walk
    expected = 'yield' if outcome == 'event' else ('dead' if outcome == 'death' else 'guardian-lost')
    expect(fight('Saradomin Wizard', protection)).to_be(expected)
    expect(w.attacked()).to_be(False)


def around_fence():
    w = Fight().install()
    protection = prepared(w)
    w.here = Tile(3055, 3696, 0)
    mage = Tile(3056, 3696, 0)
    stand = Tile(3056, 3697, 0)
    w.npcs[0]['distance'] = 1
    w.npcs[0]['tile'] = mage
    spy_on(reachability, 'probeable', lambda tile: True)
    spy_on(reachability, 'can_step', lambda a, b: a.x == stand.x and a.z == stand.z)
    spy_on(reachability, 'can_reach', lambda tile, **opts: tile.x == stand.x and tile.z == stand.z)
    seen = []

    def walk(tile, opts):
        seen.append((tile.equals(stand), opts.get('radius'), opts.get('policy', {}).get('use_teleports')))
        w.here = stand
        return True
        yield

    attacks = []

    def attack():
        attacks.append(w.here.equals(stand))
        for n in w.npcs:
            n['health'] = 0
        return True

    w.on_walk_to = walk
    w.on_attack = attack
    w.advance = w.despawn_dead
    expect(fight('Saradomin Wizard', protection)).to_be('killed')
    expect(seen).to_equal([(True, 0, False)])
    expect(attacks).to_equal([True])


def enclosed():
    w = Fight().install()
    protection = prepared(w)
    w.here = Tile(2999, 3000, 0)
    spy_on(reachability, 'probeable', lambda tile: True)
    spy_on(reachability, 'can_step', lambda a, b: False)
    expect(fight('Saradomin Wizard', protection)).to_be('guardian-lost')
    expect(w.walk_tos).to_be(0)
    expect(w.attacked()).to_be(False)


def zamorak_prepares(has_potion):
    w = Fight().install()
    if not has_potion:
        w.pack = [i for i in w.pack if i.id != 185]
    protection = GuardianProtection('Zamorak Wizard')
    expect(run_wait(protection.prepare())).to_be(True)
    expect(run_wait(protection.maintain())).to_be('ready')
    w.tick += 600
    expect(run_wait(protection.maintain())).to_be('ready')
    expect([e for e in w.events if e.startswith('drink:')]).to_equal([])
    expect(w.worn[0].id).to_be(1231)


def zamorak_trail(has_potion):
    w = Fight().install()
    guarded_trail(w, 'Zamorak Wizard', 2723)
    if not has_potion:
        w.pack = [i for i in w.pack if i.id != 185]
    state = {'digs': 0}

    def act(item, op):
        if op == 'Drink':
            w.events.append(f'drink:{w.tick}')
            w.pack = [p for p in w.pack if p.id != item.id]
        if op == 'Dig':
            state['digs'] += 1
            if state['digs'] == 2:
                swap_clue(w, 2723, 2724)
                w.pending = True
        return True

    w.on_interact = act
    w.advance = w.despawn_dead
    expect(solve()).to_be('yield')
    expect(state['digs']).to_be(2)
    expect([e for e in w.events if e.startswith('drink:')]).to_equal([])
    expect(any([i.id == 185 for i in w.pack])).to_be(has_potion)
    expect(any([i.id == 2724 for i in w.pack])).to_be(True)


def zamorak_default(entry):
    w = Fight().install()
    w.worn = [Held(1305, 'Dragon longsword', 1, 3)]
    w.npcs[0]['name'] = 'Zamorak Wizard'
    w.advance = w.despawn_dead
    if entry == 'function':
        result = fight('Zamorak Wizard')
    else:
        result = run_wait(GuardianEncounter('Zamorak Wizard').fight(lambda m: None))
    expect(result).to_be('killed')
    expect([e for e in w.events if e.startswith('drink:')]).to_equal([])
    expect(any([i.id == 185 for i in w.pack])).to_be(True)


describe('the guarded trail', lambda: [
    test('executor refuses guarded spawning without 1231', lambda: refuses_without(1231)),
    test('executor refuses guarded spawning without 185', lambda: refuses_without(185)),
    test('executor refuses guarded spawning without 385', lambda: refuses_without(385)),
    test('the executor carries ranged equipment through the spawn, guardian fight, and reward dig', ranged_trail),
    test('hard sextant012 digs at 3054,3696 before and after chasing its wizard', sextant012),
    test('yields before spawning a guardian when an event arrives during potion retry', lambda: event_during_potion('retry')),
    test('yields before spawning a guardian when an event arrives during potion prepared', lambda: event_during_potion('prepared')),
    test('guarded trail permits a travel bite with 14 Sharks before the leg', lambda: travel_bite(14)),
    test('guarded trail permits a travel bite with 15 Sharks before the leg', lambda: travel_bite(15)),
    test('guarded trail preserves three Sharks without spawning a guardian', three_sharks_kept),
    test('drinks near the dig, finishes the post-kill dig below fifteen, then requests restock', drinks_near_dig),
    test('death after spawning prevents every later dig until explicit retry', death_halts),
])

describe('the protection in detail', lambda: [
    test('confirms dose transition 2448 to 181', lambda: dose_transition(2448, 181)),
    test('confirms dose transition 181 to 183', lambda: dose_transition(181, 183)),
    test('confirms dose transition 183 to 185', lambda: dose_transition(183, 185)),
    test('confirms dose transition 185 to 229', lambda: dose_transition(185, 229)),
    test('a final dose remains valid until the conservative immunity bound', immunity_bound),
    test('does not trust an equip success without the DDS actually worn', untrusted_equip),
    test('accepts a guardian appearing on the final spawn-wait tick', last_spawn_tick),
    test('holds the dig back until the potion delay has cleared on the server', potion_delay),
    test('walks to an owned guardian displaced by 3 tiles before attacking', lambda: displaced(3)),
    test('walks to an owned guardian displaced by 20 tiles before attacking', lambda: displaced(20)),
    test('does not chase a displaced guardian belonging to another player', no_foreign_chase),
    test('guardian approach handles blocked without attacking', lambda: approach_fails('blocked')),
    test('guardian approach handles event without attacking', lambda: approach_fails('event')),
    test('guardian approach handles death without attacking', lambda: approach_fails('death')),
    test('walks around a fence to a reachable melee tile instead of attacking through it', around_fence),
    test('an enclosed guardian with no reachable melee tile requests recovery without attacking', enclosed),
    test('Zamorak preparation and prolonged combat never drink or require antipoison: carried False', lambda: zamorak_prepares(False)),
    test('Zamorak preparation and prolonged combat never drink or require antipoison: carried True', lambda: zamorak_prepares(True)),
    test('Zamorak clue completes both digs without consuming a dose: carried False', lambda: zamorak_trail(False)),
    test('Zamorak clue completes both digs without consuming a dose: carried True', lambda: zamorak_trail(True)),
    test('default function guardian entry does not drink against Zamorak', lambda: zamorak_default('function')),
    test('default encounter guardian entry does not drink against Zamorak', lambda: zamorak_default('encounter')),
])
