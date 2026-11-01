"""rs2b0t's test/api/ai/quests/engine/shilo-gear-lifecycle.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect.

rs2b0t stubs the client's singletons with stubProps; here the facades are spied on, as test_engine_failed_step.py does.
"""

from rs2004 import execution
from rs2004.bank import bank
from rs2004.dialogue import modals
from rs2004.execution import event_signal
from rs2004.game import game, reader, skills
from rs2004.geometry import Tile
from rs2004.items import equipment, inventory
from rs2004.messages import game_messages
from rs2004.quests.defs import def_by_id
from rs2004.quests.defs.shilo.gear import reset_combat_gear
from rs2004.quests.defs.shilo.journal import SV_STAGE
from rs2004.quests.engine.quest_engine import QuestEngine
from rs2004.quests.engine.types import QuestSnapshot
from rs2004.quests.gear import quest_loadout
from rs2004.tabs import quests

shilo = def_by_id('zombiequeen')


class Host:
    def log(self, m):
        pass

    def verbose(self):
        return False

    def food_item(self):
        return None

    def picked_ids(self):
        return set(['zombiequeen'])

    def skip_pending(self):
        return False

    def consume_skip(self):
        return False

    def consume_death(self):
        return False

    def note_state(self, rows, running, step_desc, no_progress, parked):
        pass

    def finish(self, reason):
        pass


def refuse_equip(name):
    return False
    yield


def no_progress():
    return None
    yield


def status_of(name):
    return 'in_progress' if name == 'Shilo Village' else 'complete'


def snap():
    return QuestSnapshot(**{
        'journal': 'in_progress',
        'stage': SV_STAGE.STARTED,
        'no_progress': 0,
        'inv': {'steel scimitar': 1},
        'worn': set(),
        'bank_known': True,
        'bank_coins': 0,
        'bank': {},
        'tile': Tile(2809, 3086, 0),
    })


def wear_name(step):
    return step.name if step.kind == 'custom' else None


def reject(s):
    """Wear the scimitar, have the server refuse it, and see the next pass leave it alone."""
    step = shilo.decide(s)
    expect(wear_name(step)).to_be('wear Steel scimitar')
    if step.kind == 'custom':
        yield from step.run(lambda *_args: None)
    after = shilo.decide(s)
    expect(wear_name(after)).not_.to_be('wear Steel scimitar')


def _fn1():
    stub(quest_loadout, current=None)
    stub(shilo, read_progress=no_progress)
    spy_on(equipment, 'equip', impl=refuse_equip)
    spy_on(equipment, 'contains', returns=False)
    spy_on(equipment, 'items', returns=[])
    spy_on(game, 'tile', returns=Tile(2809, 3086, 0))
    spy_on(game, 'in_combat', returns=False)
    spy_on(bank, 'is_open', returns=False)
    spy_on(modals, 'main', returns=-1)
    spy_on(reader, 'modals', returns=None)
    spy_on(skills, 'level', returns=99)
    spy_on(skills, 'effective', returns=99)
    spy_on(skills, 'xp', returns=0)
    spy_on(quests, 'status', impl=status_of)
    spy_on(quests, 'points', returns=100)
    spy_on(event_signal, 'pending', returns=False)
    spy_on(execution, 'delay_ticks', impl=instant_ticks)
    spy_on(execution, 'delay_until', impl=instant_until)
    spy_on(game_messages, 'recent', returns=[])
    spy_on(inventory, 'items', returns=[])
    spy_on(inventory, 'used', returns=0)
    spy_on(inventory, 'free', returns=28)
    s = snap()
    first = QuestEngine(Host())
    yield from first.execute()
    yield from reject(s)
    yield from first.execute()
    expect(wear_name(shilo.decide(s))).not_.to_be('wear Steel scimitar')
    yield from QuestEngine(Host()).execute()
    expect(wear_name(shilo.decide(s))).to_be('wear Steel scimitar')
    reset_combat_gear()


test('a new quest run retries gear rejected in the previous run', _fn1)
