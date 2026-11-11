"""Regression outcomes for rs2b0t review 8b7db422..95175bcc (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record as Value
from rs2004.quests.engine.types import QuestModule, QuestSnapshot
from rs2004.quests.engine.preparation_policy import quest_preparation_request, quest_food_request
from rs2004.quests.engine.recovery import QuestBankReset
from rs2004.quests.types import QuestRecord, QuestRequirements, QuestItem, SkillReq
from bots.account_leveler.record import Record
from bots.account_leveler.planner import enabled_skills, empty_memory
from bots.aioquester.preparation import plan_preparation
from bots.aioquester.partnerships import PartnerCoordinator
from bots.aioquester.quest_selection import plan_quest_selection
from bots.superheater import wants_goldsmith_gauntlets
from bots.dragonfireshield.logic import decide


def snapshot():
    return Record({'levels': {skill: 40 for skill in enabled_skills}, 'stock': {'coins': 100000}, 'bank_ready': True, 'quests': {'Druidic Ritual': True, 'Rune Mysteries Quest': True}, 'target': 99, 'wilderness': False, 'now': 1000})


def policy_outcomes():
    module = QuestModule(record=QuestRecord(id='squire', items=[QuestItem('Iron bar', 2, 'mustHave')]))
    request = quest_preparation_request(module, 'Trout', 'not_started', {})
    expect([(s.skill, s.level) for s in request.skills]).to_equal([('smithing', 15), ('mining', 15)])
    expect([(r.item, r.count) for r in request.items]).to_equal([('Iron bar', 2)])
    banked = quest_preparation_request(module, 'Trout', 'not_started', {'iron bar': 2})
    expect(banked.skills).to_be(None)
    expect(quest_preparation_request(module, 'Trout', 'unknown')).to_be(None)
    module.record.id = 'crest'
    expect(quest_food_request(module, 'Tuna').item).to_be('Lobster')
    module.record.id = 'waterfall'
    expect(quest_food_request(module, 'Trout')).to_be(None)
    module.record.id = 'desertrescue'
    expect(quest_preparation_request(module, 'Trout', 'in_progress')).to_be(None)


test('preparation uses bank stock and keeps quest materials out of food', policy_outcomes)


def planning_outcomes():
    s = snapshot()
    request = Value({'skills': [Value({'skill': 'runecraft', 'level': 50})]})
    s.quests['Rune Mysteries Quest'] = False
    blocked = plan_preparation(s, request, empty_memory(), lambda: 0)
    expect(blocked.kind).to_be('blocked')
    expect(blocked.reason).to_contain('Rune Mysteries')
    s.bank_ready = False
    expect(plan_preparation(s, request, empty_memory()).kind).to_be('refresh')
    s = snapshot()
    s.stock['cake'] = 8
    ready = plan_preparation(s, Value({'items': [Value({'item': 'Cake', 'count': 8})]}), empty_memory())
    expect(ready.kind).to_be('complete')
    s.stock['cake'] = 0
    cakes = plan_preparation(s, Value({'food': Value({'item': 'Cake', 'count': 8})}), empty_memory(), lambda: 0)
    expect(cakes.kind).to_be('activity')
    expect(cakes.plan.script).to_be('QuestCakeSupply')
    expect(cakes.plan.quest).to_be(None)


test('preparation refuses recursive quests and selects a cake supply activity', planning_outcomes)


def peer(name, gang):
    return {'name': name, 'world': '1', 'gang': gang, 'quests': {'blackarmgang': {'eligible': True, 'stage': 8 if gang == 'phoenix' else 21, 'has_key': False}}, 'active_quest': 'blackarmgang', 'available': True, 'trade_active': False}


def pairing():
    a = PartnerCoordinator('a', started_at=1)
    b = PartnerCoordinator('b', started_at=2)
    first = a.update(peer('Alice', 'phoenix'), 100)
    b.receive(first, 100)
    a.receive(b.update(peer('Bob', 'blackarm'), 100), 100)
    b.receive(a.update(peer('Alice', 'phoenix'), 200), 200)
    a.receive(b.update(peer('Bob', 'blackarm'), 200), 200)
    expect(a.update(peer('Alice', 'phoenix'), 300)['claims']['blackarmgang']).to_be('b')
    expect(a.partner('blackarmgang')).to_be('Bob')
    expect(a.has_live_partner('blackarmgang', 300)).to_be(True)
    expect(a.has_live_partner('blackarmgang', 16000)).to_be(False)
    a.update(peer('Alice', 'phoenix'), 16000)
    expect(a.partner('blackarmgang')).to_be('')
    a.receive({'session': 'broken'}, 16000)
    other_world = peer('Bob', 'blackarm')
    other_world['world'] = '2'
    a.receive(b.update(other_world, 17000), 17000)
    a.update(peer('Alice', 'phoenix'), 17000)
    expect(a.partner('blackarmgang')).to_be('')


test('pairing requires mutual claims, the same world, and fresh heartbeats', pairing)


class ResetPort:
    def __init__(self):
        self.pack = [Value({'id': 42, 'name': 'Quest item', 'count': 1})]
        self.worn = [Value({'id': 43, 'name': 'Weapon', 'count': 1})]
        self.stock = {}
        self.reject = False

    def inventory(self):
        return self.pack

    def equipment(self):
        return self.worn

    def tile(self):
        return Tile(3093, 3243, 0)

    def in_combat(self):
        return False

    def open_bank(self, module, log):
        yield from ()
        return True

    def close_bank(self):
        yield from ()
        return True

    def bank_inventory(self):
        yield from ()
        return self.pack

    def deposit_all(self):
        for item in self.pack:
            self.stock[item.id] = self.stock.get(item.id, 0) + item.count
        self.pack = []
        yield from ()

    def unequip(self, id):
        self.pack += self.worn
        self.worn = []
        yield from ()
        return True

    def withdraw(self, id, qty):
        yield from ()
        if self.reject or self.stock.get(id, 0) < qty:
            return False
        self.stock[id] -= qty
        self.pack.append(Value({'id': id, 'name': 'Restored', 'count': qty}))
        return True

    def equip(self, id):
        self.worn = [item for item in self.pack if item.id == id]
        self.pack = [item for item in self.pack if item.id != id]
        yield from ()
        return True


def restoration():
    port = ResetPort()
    reset = QuestBankReset(port=port)
    module = QuestModule(record=QuestRecord(id='imp', items=[QuestItem('Quest item')]))
    expect(run_wait(reset.prepare(module, QuestSnapshot(), lambda text: None))).to_be(True)
    expect(reset.pending).to_be(True)
    expect(port.pack).to_equal([])
    expect(port.worn).to_equal([])
    port.reject = True
    expect(run_wait(reset.restore(lambda text: None))).to_be(False)
    expect(reset.pending).to_be(True)
    port.reject = False
    expect(run_wait(reset.restore(lambda text: None))).to_be(True)
    expect([item.id for item in port.pack]).to_equal([42])
    expect([item.id for item in port.worn]).to_equal([43])
    expect(reset.pending).to_be(False)
    port.pack = [Value({'id': 431, 'count': 1})]
    expect(run_wait(reset.prepare(module, QuestSnapshot(), lambda text: None))).to_be(False)
    expect(reset.pending).to_be(False)


test('bank reset preserves a retryable snapshot until both inventory and equipment are restored', restoration)


def selection_and_bots():
    prerequisite = QuestRecord(id='first', quest_points=2)
    target = QuestRecord(id='second', requirements=QuestRequirements(quests=['first']))
    expect(plan_quest_selection(set(['second']), set(), [prerequisite, target], set(), 0)).to_equal(set(['first', 'second']))
    expect(plan_quest_selection(set(['second']), set(['first']), [prerequisite, target], set(), 0)).to_equal(set(['second']))
    expect(wants_goldsmith_gauntlets(' Gold ', True)).to_be(True)
    expect(wants_goldsmith_gauntlets('Iron', True)).to_be(False)
    expect(wants_goldsmith_gauntlets('Gold', False)).to_be(False)
    p = Value({'at_stand': True, 'trip_active': False, 'full': True})
    expect(decide(p)).to_be('bank')


test('quest selection respects exclusions and gold gauntlets apply only to gold', selection_and_bots)
