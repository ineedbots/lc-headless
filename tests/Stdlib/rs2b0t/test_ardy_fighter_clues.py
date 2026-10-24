"""rs2b0t's test/scripts/ArdyFighter/clueWeapon.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test
and expect, with the facades patched as rs2b0t spies on them. The walker's bank list is patched to the south bank,
where rs2b0t's fixture stands."""

from bots.ardy_fighter import ArdyFighter
from rs2004 import execution
from rs2004.catalogs import loadout as loadout_module
from rs2004.catalogs.tasks import sustain
from rs2004.clues import bank_access
from rs2004.clues import solve as solve_module
from rs2004.clues.executor import ClueExecutor
from rs2004.clues.solve import SolveClue

SOUTH_BANK = Tile(2655, 3286, 0)


def held(id, name, slot=0):
    return Fake(id=id, name=name, count=1, slot=slot, noted=False)


WEAPON = held(1333, 'Rune scimitar')


class Market:
    def __init__(self):
        self.pack = [held(3490, 'Clue scroll'), held(561, 'Nature rune')]
        self.worn = []
        self.bank = []
        self.open = False

    def install(self):
        w = self
        stub(sustain, hook=None)
        spy_on(inventory, 'items', lambda: list(w.pack))
        spy_on(inventory, 'first', lambda name: ([i for i in w.pack if i.name == name] + [None])[0])
        spy_on(inventory, 'count', lambda name: len([i for i in w.pack if i.name == name]))
        spy_on(inventory, 'count_by_id', lambda id: len([i for i in w.pack if i.id == id]))
        spy_on(inventory, 'free', lambda: 28 - len(w.pack))
        spy_on(inventory, 'is_full', lambda: len(w.pack) >= 28)
        spy_on(equipment, 'items', lambda: list(w.worn))
        spy_on(equipment, 'contains', lambda name: any([i.name == name for i in w.worn]))
        spy_on(bank, 'is_open', lambda: w.open)
        spy_on(bank, 'ready', lambda: w.open)
        spy_on(bank, 'wait_ready', lambda timeout_ms=4000: instant_until(lambda: True))
        spy_on(bank, 'items', lambda: list(w.bank))
        spy_on(bank, 'count', lambda name: 0)
        spy_on(bank, 'count_by_id', lambda id: 0)
        spy_on(bank, 'withdraw', lambda name, op='Withdraw 1': False)
        spy_on(bank, 'withdraw_x', lambda name, count: instant_until(lambda: False))
        spy_on(bank, 'deposit_all_matching', lambda matches: w.deposit(matches))
        spy_on(bank, 'close', lambda: w.close())
        spy_on(bank, 'open_nearest', lambda *a: w.open_bank())
        spy_on(bank, 'open_nearest_access', lambda *a: w.open_bank())
        spy_on(bank, 'open_npc_access', lambda *a: w.open_bank())
        patch(solve_module, 'nearest_bank', lambda tile, settings=None: {'name': 'Ardougne south', 'tile': {'x': 2655, 'z': 3286, 'level': 0}})
        patch(bank_access, 'nearest_bank', lambda tile, settings=None: None)
        patch(loadout_module, '_store_all', lambda: [])
        spy_on(game, 'ingame', lambda: True)
        spy_on(game, 'tile', lambda: SOUTH_BANK)
        spy_on(game, 'in_combat', lambda: False)
        spy_on(event_signal, 'pending', lambda: False)
        spy_on(skills, 'level', lambda name: 60)
        spy_on(skills, 'effective', lambda name: 60)
        spy_on(skills, 'xp', lambda name: 0)
        spy_on(traversal, 'walk_resilient', lambda tile, **opts: instant_until(lambda: True))
        patch(execution, 'delay_until', instant_until)
        patch(execution, 'delay_until_ticks', instant_until_ticks)
        patch(execution, 'delay_ticks', instant_ticks)
        spy_on(ClueExecutor, 'solve_held_clue', lambda *a: instant_until(lambda: 'yield'))
        return self

    def open_bank(self):
        self.open = True
        return True
        yield

    def close(self):
        self.open = False
        return True
        yield

    def deposit(self, matches):
        self.bank.extend([i for i in self.pack if matches(i.name or '', i.id)])
        self.pack = [i for i in self.pack if not matches(i.name or '', i.id)]
        return None
        yield


def keeps_weapon(source):
    w = Market().install()
    loadouts = [{'name': 'Melee', 'worn': {'righthand': 'Rune scimitar'}, 'carry': []}] if source == 'loadout' else []
    if source == 'equipped':
        w.worn = [held(1333, 'Rune scimitar', 3)]
    bot = ArdyFighter()
    bot.settings = SettingsBag({'loadout': 'Melee', 'loadouts': loadouts})
    run_wait(bot.on_start())
    w.worn = []
    w.pack.append(WEAPON)
    clue = [t for t in bot._tasks if isinstance(t, SolveClue)]
    expect(len(clue)).to_be(1)
    run_wait(clue[0].execute())
    run_wait(clue[0].execute())
    expect(any([i.id == 1333 for i in w.pack])).to_be(True)
    expect(any([i.id == 1333 for i in w.bank])).to_be(False)
    expect(any([i.id == 561 for i in w.bank])).to_be(True)


describe('ArdyFighter clue banking', lambda: [
    test('clue banking keeps the loadout weapon when it is in the backpack', lambda: keeps_weapon('loadout')),
    test('clue banking keeps the equipped weapon when it is in the backpack', lambda: keeps_weapon('equipped')),
])
