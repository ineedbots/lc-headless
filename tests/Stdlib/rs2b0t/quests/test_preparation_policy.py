"""Preparation must train only requirements not already satisfied by stock."""

from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress
from rs2004.quests.engine.preparation_policy import quest_preparation_request, quest_food_request
from rs2004.quests.types import QuestRecord, QuestItem, QuestRequirements, SkillReq


def request(id, stock=None, ids=None, progress=None, items=None):
    module = QuestModule(record=QuestRecord(id=id, items=items or []))
    return quest_preparation_request(module, 'Trout', 'not_started', stock, ids, progress)


def targets(value):
    return {s.skill: s.level for s in value.skills or []}


def preparation_targets():
    expect(targets(request('upass'))['ranged']).to_be(25)
    expect(targets(request('elemental_workshop'))['mining']).to_be(30)
    expect(targets(request('druidspirit'))).to_equal({'smithing': 20, 'mining': 20})
    expect(targets(request('druidspirit', {'silver ore': 1}))).to_equal({'smithing': 20})
    expect(targets(request('druidspirit', {'silver sickle(b)': 1}))).to_equal({})
    expect(targets(request('chompybird'))['crafting']).to_be(5)
    expect(targets(request('regicide'))['mining']).to_be(30)
    expect(targets(request('dragon'))).to_equal({'crafting': 8, 'smithing': 34, 'mining': 30})
    expect(targets(request('dragon', {'unfired bowl': 1, 'nails': 12}))).to_equal({})
    expect(targets(request('crest'))['fishing']).to_be(50)
    expect(targets(request('crest', {'swordfish': 1, 'bass': 1, 'tuna': 1, 'salmon': 1, 'shrimps': 1}))).to_equal({})
    expect(targets(request('ikov', {}, {}))).to_equal({'fletching': 65, 'woodcutting': 60, 'crafting': 10})
    expect(targets(request('ikov', {}, {857: 1}))).to_equal({})
    expect(targets(request('ikov', {'bow string': 1}, {68: 1}))).to_equal({'fletching': 65})
    expect(targets(request('hero'))).to_equal({'mining': 50, 'cooking': 53, 'fishing': 53, 'herblore': 25})
    expect(targets(request('hero', {'ice gloves': 1, 'lava eel': 1}))).to_equal({})
    module = QuestModule(record=QuestRecord(id='test', requirements=QuestRequirements(skills=[SkillReq('attack', 10)])), pray=Record({'protect': 'melee'}))
    expect(targets(quest_preparation_request(module, '', 'in_progress'))).to_equal({'attack': 10, 'prayer': 43})


test('preparation derives stock-sensitive skill targets for quest materials', preparation_targets)


def supplies_and_food():
    value = request('legends', {'prayer potion(2)': 6}, items=[QuestItem('Lockpick', 2, 'mustHave')])
    expect([i.count for i in value.items if i.item == 'Lockpick']).to_equal([2])
    expect([i for i in value.items if i.item == 'Prayer potion(4)']).to_equal([])
    expect([i for i in request('priestperil', {'rune pickaxe': 1}).items or [] if i.item == 'Bronze pickaxe']).to_equal([])
    expect([i.item for i in request('tbwt').items]).to_contain('Agility potion(3)')
    expect('Agility potion(3)' in [i.item for i in request('tbwt', {'agility potion(2)': 2}).items]).to_be(False)
    expect('Agility potion(3)' in [i.item for i in request('tbwt', progress=QuestProgress(stage=0, flags={'agility': True})).items]).to_be(False)
    module = QuestModule(record=QuestRecord(id='desertrescue'))
    expect(quest_food_request(module, None)).to_be(None)
    expect(quest_food_request(module, ' Cake ').count).to_be(8)
    module.record.id = 'upass'
    expect(quest_food_request(module, 'Trout').item).to_be('Lobster')
    module.record.id = 'death'
    module.food = 8
    expect(quest_food_request(module, 'Bread').item).to_be('Trout')
    module.sustain = Record({'foods': ['Bread', 'Cake']})
    expect(quest_food_request(module, None).item).to_be('Cake')


test('preparation merges supplies, counts potion doses and protects material food', supplies_and_food)
