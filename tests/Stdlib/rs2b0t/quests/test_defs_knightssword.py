"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/knightssword.test.ts (MIT, see thirdparty/rs2b0t)."""
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot

def _snapshot(**fields):
    for name in ['inv', 'inv_ids', 'bank', 'bank_ids']:
        if isinstance(fields.get(name), (Record, Fake)):
            fields[name] = fields[name]._fields
    return QuestSnapshot(**fields)
from rs2004.quests.defs.knightssword.areas import KS_ID, KS_STAGE
from rs2004.quests.defs.knightssword import decide_at, knightssword
from rs2004.quests.defs import QUEST_DEFS
from rs2004.quests.food import quest_food
COINS = 995
BRONZE_PICKAXE = 1265
MAX_MINING = 70
original_food = quest_food.name

def _fn1():
    quest_food.name = 'Lobster'
before_each(_fn1)

def _fn2():
    quest_food.name = original_food
after_each(_fn2)

def snap(options=None):
    """Kitted out by default, so every case exercises the branch it names."""
    if options is None:
        options = Fake(**{})
    stage = options.stage if options.stage is not None else KS_STAGE.NOT_STARTED
    inv = {_k: _v for _k, _v in [['lobster', options.food if options.food is not None else 14]]}
    return _snapshot(**{'journal': options.journal if options.journal is not None else ('not_started' if stage == KS_STAGE.NOT_STARTED else 'in_progress'), 'inv': inv, 'inv_ids': {_k: _v for _k, _v in [[COINS, 1000]] + list(options.inv_ids if options.inv_ids is not None else [])}, 'worn': set(), 'worn_ids': set(options.worn_ids if options.worn_ids is not None else []), 'no_progress': 0, 'bank_coins': 2000000, 'stage': stage, 'progress': Fake(**{'stage': stage, 'flags': set()}), 'bank': {}, 'bank_ids': {_k: _v for _k, _v in (options.bank_ids if options.bank_ids is not None else [])}, 'bank_known': options.bank_known if options.bank_known is not None else True, 'tile': options.tile if options.tile is not None else Fake(**{'x': 2946, 'z': 3369, 'level': 0}), 'free_slots': 20})

def decide(options=None):
    if options is None:
        options = Fake(**{})
    return decide_at(snap(options), MAX_MINING, 15)

def talk_to(step):
    return step.stop.npc if step.kind == 'talk' else None

def _fn3():

    def _fn4():
        expect(decide(Fake(**{'journal': 'unknown'})).kind).to_be('wait')
    test('waits while the journal is unknown', _fn4)

    def _fn5():
        expect(decide(Fake(**{'journal': 'complete', 'stage': KS_STAGE.COMPLETE})).kind).to_be('done')
    test('is done when complete', _fn5)

    def _fn6():
        _merged7 = {}
        for _k, _v in (snap(Fake(**{'journal': 'in_progress'}))._fields if isinstance(snap(Fake(**{'journal': 'in_progress'})), (Record, Fake)) else {name: getattr(snap(Fake(**{'journal': 'in_progress'})), name) for name in QuestSnapshot.FIELDS}).items():
            _merged7[_k] = _v
        for _k, _v in {'stage': None, 'progress': None}.items():
            _merged7[_k] = _v
        blind = Fake(**_merged7)
        expect(decide_at(blind, MAX_MINING, 15).kind).to_be('wait')
    test('waits when the stage is unreadable', _fn6)

    def _fn8():
        expect(talk_to(decide())).to_be('Squire')
    test('starts with the Squire', _fn8)

    def _fn9():
        expect(decide(Fake(**{'stage': KS_STAGE.STARTED}))).to_match_object(Fake(**{'kind': 'grab_ground', 'item': 'Pie dish'}))
    test('grabs the pie dish on the way to Reldo', _fn9)

    def _fn10():
        expect(talk_to(decide(Fake(**{'stage': KS_STAGE.STARTED, 'inv_ids': [[KS_ID.PIE_DISH, 1]]})))).to_be('Reldo')
    test('talks to Reldo once the dish is held', _fn10)

    def _fn11():
        step = decide(Fake(**{'stage': KS_STAGE.STARTED, 'bank_ids': [[KS_ID.PIE_DISH, 1]]}))
        expect(talk_to(step)).to_be('Reldo')
    test('a banked dish is enough to move on to Reldo', _fn11)

    def _fn12():
        step = decide(Fake(**{'stage': KS_STAGE.SPOKEN_RELDO, 'inv_ids': [[KS_ID.PIE_DISH, 1]]}))
        expect(step.kind).not_.to_be('talk')
    test('builds a pie after Reldo', _fn12)

    def _fn13():
        step = decide(Fake(**{'stage': KS_STAGE.SPOKEN_RELDO, 'inv_ids': [[KS_ID.REDBERRY_PIE, 1]]}))
        expect(talk_to(step)).to_be('Thurgo')
    test('takes a held pie to Thurgo', _fn13)

    def _fn14():
        expect(talk_to(decide(Fake(**{'stage': KS_STAGE.GIVEN_PIE})))).to_be('Thurgo')
    test('returns to Thurgo after the pie is eaten', _fn14)

    def _fn15():
        expect(talk_to(decide(Fake(**{'stage': KS_STAGE.SPOKEN_THURGO})))).to_be('Squire')
    test('reports back to the Squire for the portrait lead', _fn15)

    def _fn16():
        expect(decide(Fake(**{'stage': KS_STAGE.LOOKING_PORTRAIT}))).to_match_object(Fake(**{'kind': 'custom', 'name': 'take the portrait'}))
    test('fetches the portrait at stage 5', _fn16)

    def _fn17():
        step = decide(Fake(**{'stage': KS_STAGE.LOOKING_PORTRAIT, 'inv_ids': [[KS_ID.PORTRAIT, 1]]}))
        expect(talk_to(step)).to_be('Thurgo')
    test('takes a held portrait to Thurgo', _fn17)

    def _fn18():
        for stage in KS_STAGE._fields.values():
            step = decide(Fake(**{'stage': stage, 'inv_ids': [[KS_ID.PORTRAIT, 1]]}))
            banking = step.kind == 'deposit'
            expect(banking).to_be(False)
    test('never banks the portrait', _fn18)
describe("The Knight's Sword decide()", _fn3)

def _fn19():

    def at6(options=None):
        if options is None:
            options = Fake(**{})
        _merged20 = {}
        for _k, _v in (options._fields if isinstance(options, (Record, Fake)) else options).items():
            _merged20[_k] = _v
        for _k, _v in {'stage': KS_STAGE.LOOKING_BLURITE}.items():
            _merged20[_k] = _v
        return decide(Fake(**_merged20))

    def _fn21():
        expect(at6(Fake(**{'worn_ids': [KS_ID.BLURITE_SWORD]}))).to_match_object(Fake(**{'kind': 'equip'}))
    test('unequips a worn sword before handing it over', _fn21)

    def _fn22():
        expect(at6(Fake(**{'bank_ids': [[KS_ID.BLURITE_SWORD, 1]]})).kind).to_be('withdraw')
    test('withdraws a banked sword', _fn22)

    def _fn23():
        expect(talk_to(at6(Fake(**{'inv_ids': [[KS_ID.BLURITE_SWORD, 1]]})))).to_be('Squire')
    test('hands a held sword to the Squire', _fn23)

    def _fn24():
        expect(at6(Fake(**{'inv_ids': [[BRONZE_PICKAXE, 1]]}))).to_match_object(Fake(**{'kind': 'mine_rock', 'rock': 'Iron'}))
    test('gets iron bars before blurite', _fn24)

    def _fn25():
        step = at6(Fake(**{'inv_ids': [[KS_ID.IRON_BAR, 2], [BRONZE_PICKAXE, 1]]}))
        expect(step).to_match_object(Fake(**{'kind': 'custom', 'name': 'mine blurite'}))
    test('mines blurite once the bars are in the pack', _fn25)

    def _fn26():
        step = at6(Fake(**{'inv_ids': [[KS_ID.IRON_BAR, 2], [KS_ID.BLURITE_ORE, 1], [BRONZE_PICKAXE, 1]]}))
        expect(talk_to(step)).to_be('Thurgo')
    test('takes the full set to Thurgo', _fn26)

    def _fn27():
        step = at6(Fake(**{'inv_ids': [[KS_ID.IRON_BAR, 2], [BRONZE_PICKAXE, 1]], 'food': 0}))
        expect(step).to_match_object(Fake(**{'kind': 'custom', 'name': 'mine blurite'}))
    test('goes for the blurite with no food, since it stocks none', _fn27)

    def _fn28():
        step = at6(Fake(**{'inv_ids': [[KS_ID.IRON_BAR, 2], [BRONZE_PICKAXE, 1]], 'food': 0, 'tile': Fake(**{'x': 3049, 'z': 9566, 'level': 0})}))
        expect(step).to_match_object(Fake(**{'kind': 'custom', 'name': 'mine blurite'}))
    test('does not walk back out of the dungeon to re-bank', _fn28)

    def _fn29():
        bare = snap(Fake(**{'stage': KS_STAGE.SPOKEN_RELDO}))
        bare.inv_ids = {_k: _v for _k, _v in [[COINS, 1]]}
        step = decide_at(bare, MAX_MINING, 15)
        expect(step.kind == 'withdraw' and any([i['id'] == COINS for i in step.items])).to_be(True)
    test('tops the coin float up before anything else', _fn29)
describe('stage 6, the materials and the sword', _fn19)

def _fn30():

    def _fn31():
        expect([d.module() for d in QUEST_DEFS]).to_contain(knightssword)
        expect(knightssword.record.id).to_be('squire')
    test('is registered in the queue', _fn31)

    def _fn32():
        expect(knightssword.owns_inventory).to_be(True)
    test('owns its inventory, because acquisition is just-in-time', _fn32)

    def _fn33():
        expect(knightssword.tools).to_contain('coins')
    test('keeps coins in tools, or every purchase parks on "need gp"', _fn33)

    def _fn34():
        expect(knightssword.bank).to_be('nearest')
    test('pins no bank, because the quest crosses four towns', _fn34)
describe('the module', _fn30)

def _fn35():
    expect(talk_to(decide_at(snap(), 10, 1))).to_be('Squire')
    expect(talk_to(decide_at(snap(Fake(**{'stage': KS_STAGE.LOOKING_BLURITE, 'inv_ids': [[KS_ID.IRON_BAR, 2], [KS_ID.BLURITE_ORE, 1]]})), 10, 1))).to_be('Thurgo')
test('Smithing 1 does not block starting the quest or delivering acquired materials', _fn35)

def banked_bars_still_need_pickaxe():
    step = decide_at(snap(Fake(stage=KS_STAGE.LOOKING_BLURITE, inv_ids=[[KS_ID.IRON_BAR,2]], bank_ids=[[BRONZE_PICKAXE,1]])),10,1)
    expect(step.kind).to_be('withdraw')
    expect(step.items).to_equal([{'name':'Bronze pickaxe','qty':1,'id':BRONZE_PICKAXE}])
test('draws a banked pickaxe for blurite even when iron bars came from the bank', banked_bars_still_need_pickaxe)

def source_missing_pickaxe_for_blurite():
    step = decide_at(snap(Fake(stage=KS_STAGE.LOOKING_BLURITE, inv_ids=[[KS_ID.IRON_BAR,2]])),10,1)
    expect(step.kind).to_be('grab_ground')
    expect(step.item).to_be('Bronze pickaxe')
test('sources a free pickaxe for blurite when neither pack nor bank has one', source_missing_pickaxe_for_blurite)

def worn_pickaxe_for_blurite():
    step = decide_at(snap(Fake(stage=KS_STAGE.LOOKING_BLURITE, inv_ids=[[KS_ID.IRON_BAR,2]], worn_ids=[BRONZE_PICKAXE])),10,1)
    expect(step.kind).to_be('custom')
    expect(step.name).to_be('mine blurite')
test('a worn pickaxe is sufficient for blurite', worn_pickaxe_for_blurite)

def banked_food_for_blurite():
    state = snap(Fake(stage=KS_STAGE.LOOKING_BLURITE, inv_ids=[[KS_ID.IRON_BAR,2],[BRONZE_PICKAXE,1]], food=0))
    state.bank = {'lobster':10}
    step = decide_at(state,10,1)
    expect(step.kind).to_be('withdraw')
    expect(step.items).to_equal([{'name':'Lobster','qty':5}])
test('takes optional banked food before the ice dungeon', banked_food_for_blurite)

def no_food_restock_inside_blurite():
    state = snap(Fake(stage=KS_STAGE.LOOKING_BLURITE, inv_ids=[[KS_ID.IRON_BAR,2],[BRONZE_PICKAXE,1]], tile=Fake(x=3049,z=9566,level=0), food=0))
    state.bank = {'lobster':10}
    step = decide_at(state,10,1)
    expect(step.kind).to_be('custom')
    expect(step.name).to_be('mine blurite')
test('never leaves the ice dungeon to replenish food while mining', no_food_restock_inside_blurite)
