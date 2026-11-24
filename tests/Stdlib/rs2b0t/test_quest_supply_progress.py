"""Supply activity progress must track output without querying a fictional skill."""

import json
from bots.aioquester import preparation_runtime as runtime
from bots.account_leveler.record import Record
from rs2004.game import skills


class SupplyEnvironment(runtime.GameEnvironment):
    def __init__(self):
        self.count = 0

    def snapshot(self):
        return Record({'stock': Record({'seaweed': self.count})})


def supply_progress():
    environment = SupplyEnvironment()
    plan = Record({'objective': 'supplies', 'output': Record({'item': 'Seaweed', 'count': 1})})
    before = json.loads(environment.progress(plan))
    environment.count = 1
    after = json.loads(environment.progress(plan))
    assert before == [{}, 0]
    assert after == [{}, 1]


test('ground supply progress follows the collected item without a supplies skill', supply_progress)


def skill_progress():
    environment = SupplyEnvironment()
    plan = Record({'objective': 'fishing'})
    result = json.loads(environment.progress(plan))
    assert result == [{'fishing': skills.xp('fishing')}, None]


test('training progress still tracks the objective skill XP', skill_progress)


def prerequisite_progress():
    environment = SupplyEnvironment()
    plan = Record({'objective': 'supplies', 'prerequisite_levels': {'fishing': 65}})
    result = json.loads(environment.progress(plan))
    assert result == [{'fishing': skills.xp('fishing')}, None]


test('explicit prerequisite skill progress remains tracked for supply plans', prerequisite_progress)
