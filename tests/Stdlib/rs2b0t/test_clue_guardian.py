"""rs2b0t's test/api/ai/clues: guardianWeapon.test.ts and guardianEvents.test.ts (MIT, see thirdparty/rs2b0t), on
spec.py's describe, test and expect, with the facades patched as rs2b0t spies on them. rs2b0t reaches into a
SolveClue's private fields to set up the host test; here they're plain attributes."""

from rs2004 import execution
from rs2004.clues import bank_access
from rs2004.clues.executor import ClueExecutor
from rs2004.clues.guardian import hard_kit_fingerprint, stock_hard_weapon
from rs2004.clues.solve import SolveClue


def item(id, name, count=1, slot=0):
    return Fake(id=id, name=name, count=count, slot=slot, noted=False)


SWORD = item(1305, 'Dragon longsword')
DAGGER = item(1231, 'Dragon dagger(p)')


class Armoury:
    """The bank stop's world: a pack, a bank and worn gear."""

    def __init__(self):
        self.pack = []
        self.bank = [item(2448, 'Superantipoison(4)'), item(385, 'Shark', 30)]
        self.worn = [item(861, 'Magic shortbow', 1, 3)]
        self.remembered = []

    def install(self):
        w = self
        spy_on(inventory, 'items', lambda: list(w.pack))
        spy_on(inventory, 'first', lambda name: w.find(w.pack, name))
        spy_on(equipment, 'items', lambda: list(w.worn))
        spy_on(equipment, 'contains', lambda name: w.find(w.worn, name) is not None)
        spy_on(equipment, 'equip', lambda name: w.equip(name))
        spy_on(equipment, 'unequip', lambda name: w.unequip(name))
        spy_on(bank, 'ready', lambda: True)
        spy_on(bank, 'is_open', lambda: True)
        spy_on(bank, 'items', lambda: list(w.bank))
        spy_on(bank, 'count', lambda name: sum([i.count for i in w.bank if i.name == name]))
        spy_on(bank, 'withdraw', lambda name, op='Withdraw 1': w.withdraw(name))
        spy_on(bank, 'deposit_all_matching', lambda matches: w.deposit(matches))
        spy_on(bank, 'wait_ready', lambda timeout_ms=4000: instant_until(lambda: True))
        spy_on(bank_access, 'open_clue_bank', lambda log=None: instant_until(lambda: True))
        spy_on(skills, 'level', lambda name: 60)
        spy_on(quests, 'status', lambda name: 'complete')
        spy_on(game, 'tile', lambda: None)
        patch(execution, 'delay_until', instant_until)
        return self

    def find(self, items, name):
        for i in items:
            if i.name == name:
                return i
        return None

    def withdraw(self, name):
        source = None
        for i in self.bank:
            if i.name == name and i.count > 0:
                source = i
                break
        if source is None:
            return False
        self.pack.append(item(source.id, source.name))
        self.bank = [i for i in self.bank if i is not source]
        return True

    def equip(self, name):
        nxt = self.find(self.pack, name)
        if nxt is None:
            return self.find(self.worn, name) is not None
        self.pack = [i for i in self.pack if i is not nxt] + [item(i.id, i.name, i.count) for i in self.worn]
        self.worn = [item(nxt.id, nxt.name, nxt.count, 3)]
        return True
        yield

    def unequip(self, name):
        self.pack.extend([item(i.id, i.name, i.count) for i in self.worn if i.name == name])
        self.worn = [i for i in self.worn if i.name != name]
        return True
        yield

    def deposit(self, matches):
        self.bank.extend([i for i in self.pack if matches(i.name or '', i.id)])
        self.pack = [i for i in self.pack if not matches(i.name or '', i.id)]
        return None
        yield


def stock(w, entrana=False, preferred=None):
    return run_wait(stock_hard_weapon(entrana, lambda name: w.remembered.append(name), preferred))


def keeps_longsword():
    w = Armoury().install()
    w.worn = [item(1305, 'Dragon longsword', 1, 3)]
    w.bank.append(DAGGER)
    expect(stock(w)).to_be(True)
    expect(w.worn[0].id).to_be(1305)
    expect(any([i.id == 1231 for i in w.bank])).to_be(True)
    expect(w.remembered).to_equal([])


def longsword_from(source):
    w = Armoury().install()
    (w.pack if source == 'inventory' else w.bank).append(SWORD)
    expect(stock(w)).to_be(True)
    expect(w.worn[0].id).to_be(1305)
    expect(w.remembered).to_equal(['Magic shortbow'])


def prefers_configured():
    w = Armoury().install()
    w.worn = []
    w.bank.extend([DAGGER, SWORD])
    expect(stock(w, False, 'Dragon longsword')).to_be(True)
    expect(w.worn[0].id).to_be(1305)


def dagger_fallback():
    w = Armoury().install()
    w.bank.append(DAGGER)
    expect(stock(w, False, 'Dragon longsword')).to_be(True)
    expect(w.worn[0].id).to_be(1231)


def never_unsupported():
    w = Armoury().install()
    w.bank.extend([DAGGER, item(1333, 'Rune scimitar')])
    expect(stock(w, False, 'Rune scimitar')).to_be(True)
    expect(w.worn[0].id).to_be(1231)


def banks_for_entrana():
    w = Armoury().install()
    w.worn = [item(1305, 'Dragon longsword', 1, 3)]
    expect(stock(w, True)).to_be(True)
    expect(w.worn).to_equal([])
    expect(any([i.id == 1305 for i in w.pack])).to_be(False)
    expect(any([i.id == 1305 for i in w.bank])).to_be(True)


def fingerprint_moves():
    w = Armoury().install()
    before = hard_kit_fingerprint(True)
    w.bank.append(SWORD)
    expect(hard_kit_fingerprint(True)).not_.to_be(before)


describe('stock_hard_weapon', lambda: [
    test('keeps the equipped longsword when a dagger is banked', keeps_longsword),
    test('equips a longsword from the inventory without requiring a dagger', lambda: longsword_from('inventory')),
    test('equips a longsword from the bank without requiring a dagger', lambda: longsword_from('bank')),
    test('prefers the configured supported weapon after Entrana strips equipment', prefers_configured),
    test('falls back to a dagger when the configured weapon is unavailable', dagger_fallback),
    test('never selects an unsupported configured weapon', never_unsupported),
    test('banks the accepted longsword before visiting Entrana', banks_for_entrana),
    test('adding a longsword changes the blocked-kit fingerprint', fingerprint_moves),
])


# The guardian across an interruption (guardianEvents.test.ts)

class Dig:
    """A guarded hard dig with a Saradomin wizard beside it."""

    def __init__(self):
        self.tick = 0
        self.pending = False
        self.interrupted = False
        self.digs = 0
        self.drinks = 0
        self.attacks = []
        self.messages = []
        self.pack = [item(3526, 'Clue scroll (hard)'), item(185, 'Superantipoison(1)'), item(385, 'Shark', 15), item(952, 'Spade'),
                     item(2574, 'Sextant'), item(2575, 'Watch'), item(2576, 'Chart')]
        self.wizards = [{'index': 4, 'id': 1, 'distance': 1, 'health': 40, 'mine': True, 'foreign': False}]
        self.on_tick = None
        self.on_dig = None
        self.on_attack = None
        self.equips = 0

    def install(self):
        w = self
        spy_on(inventory, 'items', lambda: [w.pack_item(i) for i in w.pack])
        spy_on(inventory, 'first', lambda name: w.first(name))
        spy_on(inventory, 'count', lambda name: sum([i.count for i in w.pack if i.name == name]))
        spy_on(inventory, 'count_by_id', lambda id: sum([i.count for i in w.pack if i.id == id]))
        spy_on(inventory, 'is_full', lambda: False)
        spy_on(equipment, 'items', lambda: [item(1231, 'Dragon dagger(p)', 1, 3)])
        spy_on(npcs, 'query', querying(lambda: [w.wizard(n) for n in w.wizards]))
        spy_on(skills, 'level', lambda name: 60)
        spy_on(skills, 'effective', lambda name: 60)
        spy_on(quests, 'status', lambda name: 'complete')
        spy_on(game, 'tick', lambda: w.tick)
        spy_on(game, 'in_combat', lambda: True)
        spy_on(game, 'tile', lambda: Tile(3000, 3000, 0))
        spy_on(event_signal, 'pending', lambda: w.pending)
        spy_on(chat_dialog, 'can_continue', lambda: False)
        spy_on(chat_dialog, 'is_open', lambda: False)
        spy_on(reader, 'count_dialog_open', lambda: False)
        spy_on(traversal, 'walk_resilient', lambda dest, **opts: instant_until(lambda: True))
        patch(execution, 'delay_until', instant_until)
        patch(execution, 'delay_until_ticks', instant_until_ticks)
        patch(execution, 'delay_ticks', lambda n=1: w.ticked())
        spy_on(prayer, 'set', lambda name, on: instant_until(lambda: True))
        spy_on(special, 'ready', lambda name: False)
        spy_on(game_messages, 'mark', lambda: len(w.messages))
        spy_on(game_messages, 'saw_since', lambda mark, pattern: any([pattern.lower() in m.lower() for m in w.messages[mark:]]))
        spy_on(game_messages, 'since', lambda mark: [Fake(text=m) for m in w.messages[mark:]])
        spy_on(modals, 'close', lambda: instant_until(lambda: True))
        spy_on(equipment, 'equip', lambda name: w.equip(name))
        return self

    def equip(self, name):
        self.equips += 1
        return False
        yield

    def first(self, name):
        for i in self.pack:
            if i.name == name:
                return self.pack_item(i)
        return None

    def ticked(self):
        self.tick += 1
        if self.on_tick is not None:
            self.on_tick()
        else:
            if len(self.wizards) > 0 and self.wizards[0]['health'] == 0:
                self.wizards = []
            if self.digs == 1 and not self.interrupted:
                self.interrupted = True
                self.pending = True
                self.pack = [item(i.id, i.name, 14) if i.id == 385 else i for i in self.pack]
        return None
        yield

    def pack_item(self, i):
        w = self
        held = i

        def interact(op):
            if op == 'Drink':
                w.drinks += 1
                w.pack = [p for p in w.pack if p.id != held.id]
            if op == 'Dig':
                w.digs += 1
                if w.on_dig is not None:
                    w.on_dig()
                elif w.digs == 2:
                    w.pack = [item(3528, p.name, p.count) if p.id == 3526 else p for p in w.pack]
            return True

        return Fake(id=i.id, name=i.name, count=i.count, slot=i.slot, noted=False, actions=lambda: ['Drink', 'Eat', 'Dig'], interact=interact)

    def wizard(self, n):
        w = self

        def interact(op):
            w.attacks.append(n['index'])
            if w.on_attack is not None:
                w.on_attack()
            else:
                n['health'] = 0
            return True

        return Fake(index=n['index'], id=n['id'], name='Saradomin Wizard', size=1, health=n['health'], max_health=40, distance=lambda: n['distance'],
                    tile=lambda: Tile(3000, 3000, 0), actions=lambda: ['Attack'], targets_me=lambda: n['mine'] and not n['foreign'],
                    targets_another_player=lambda: n['foreign'], interact=interact)


def solve(executor):
    return run_wait(executor.solve_held_clue(lambda m: None))


def event_mid_wait():
    w = Dig().install()
    expect(solve(ClueExecutor())).to_be('yield')
    expect(w.attacks).to_equal([])
    expect(w.digs).to_be(1)


def resumes_guardian():
    w = Dig().install()
    executor = ClueExecutor()
    solve(executor)
    w.pending = False
    expect(solve(executor)).to_be('supplies-needed')
    expect(w.attacks).to_equal([4])
    expect(w.drinks).to_be(1)
    expect(w.digs).to_be(2)
    expect(any([i.id == 3528 for i in w.pack])).to_be(True)


def revalidates(change):
    w = Dig().install()
    executor = ClueExecutor()
    solve(executor)
    w.pending = False
    if change == 'missing':
        w.wizards = []
    elif change == 'index':
        w.wizards[0]['index'] = 5
    elif change == 'id':
        w.wizards[0]['id'] = 2
    elif change == 'foreign':
        w.wizards[0]['foreign'] = True
    elif change == 'distant':
        w.wizards[0]['distance'] = 40
    elif change == 'dead':
        w.messages.append('Oh dear, you are dead!')
    expect(solve(executor)).to_be('dead' if change == 'dead' else 'reset-needed')
    expect(w.attacks).to_equal([])
    expect(w.digs).to_be(1)


class Host:
    def log(self, m):
        pass

    def set_status(self, text):
        pass

    def is_food(self, name):
        return name == 'Shark'

    def food_name(self):
        return 'Shark'

    def food_withdraw(self):
        return 20

    def use_teleports(self):
        return False

    def restore_prayer(self):
        return False


def host_ledger():
    w = Dig().install()
    task = SolveClue(Host())
    task.banked_this_solve = True
    task.hard_trail = True
    task.stripped_gear = ['Magic shortbow']
    task.trail_weapon = 'Magic shortbow'

    def attacked():
        w.pending = True

    w.on_attack = attacked
    run_wait(task.execute())
    w.pending = False
    run_wait(task.execute())
    expect(task.clue_status()).to_be('event: yielding')
    expect(w.attacks).to_equal([4])
    expect(task.death_blocked).to_be(False)
    expect(task.banked_this_solve).to_be(True)
    expect(task.stripped_gear).to_equal(['Magic shortbow'])
    expect(w.equips).to_be(0)


def witnessed_death():
    w = Dig().install()
    w.interrupted = True

    def on_tick():
        if len(w.wizards) > 0 and w.wizards[0]['health'] == 0:
            w.wizards = []
            w.pending = True

    w.on_tick = on_tick
    executor = ClueExecutor()
    expect(solve(executor)).to_be('yield')
    w.pending = False
    expect(solve(executor)).to_be('supplies-needed')
    expect(w.digs).to_be(2)
    expect(w.attacks).to_equal([4])


def expired_protection():
    w = Dig().install()
    executor = ClueExecutor()
    solve(executor)
    w.pending = False
    w.tick += 570
    expect(solve(executor)).to_be('supplies-needed')
    expect(w.attacks).to_equal([])
    expect(w.digs).to_be(1)


def kill_credit():
    w = Dig().install()
    w.interrupted = True

    def on_dig():
        if w.digs == 6:
            w.pack = [item(3527, p.name, p.count) if p.id == 3526 else p for p in w.pack]
            w.pending = True

    w.on_dig = on_dig
    executor = ClueExecutor()
    expect(solve(executor)).to_be('reset-needed')
    expect(w.attacks).to_equal([4])
    expect(w.digs).to_be(5)
    expect(solve(executor)).to_be('yield')
    expect(w.digs).to_be(6)
    expect(w.attacks).to_equal([4])


def still_missing():
    w = Dig().install()
    executor = ClueExecutor()
    solve(executor)
    w.pending = False
    w.wizards = []
    expect(solve(executor)).to_be('reset-needed')
    w.pack.append(item(2448, 'Superantipoison(4)'))
    spy_on(settings_store, 'save', lambda *a: None)
    expect(solve(executor)).to_be('abandon')
    expect(w.attacks).to_equal([])


describe('the guardian across an interruption', lambda: [
    test('yields without another attack when an event fires during a combat wait', event_mid_wait),
    test('resumes the same guardian below fifteen Sharks with the final dose still active', resumes_guardian),
    test('revalidates a missing guardian on resume instead of spawning another', lambda: revalidates('missing')),
    test('revalidates a guardian whose index changed on resume', lambda: revalidates('index')),
    test('revalidates a guardian whose id changed on resume', lambda: revalidates('id')),
    test('revalidates a guardian another player took on resume', lambda: revalidates('foreign')),
    test('revalidates a distant guardian on resume', lambda: revalidates('distant')),
    test('a death on resume stops the trail', lambda: revalidates('dead')),
    test('host preserves its original weapon ledger and bank state across a guardian event', host_ledger),
    test('preserves witnessed guardian death across an event before despawn', witnessed_death),
    test('rechecks expired protection on resume without another spawn dig', expired_protection),
    test('bank reset after a failed post-kill dig preserves guardian kill credit', kill_credit),
    test('a guardian still missing after the bank reset abandons without another reset', still_missing),
])
