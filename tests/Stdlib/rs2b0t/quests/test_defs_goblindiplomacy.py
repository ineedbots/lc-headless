"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/goblindiplomacy.test.ts (MIT, see thirdparty/rs2b0t)."""
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot

def _snapshot(**fields):
    for name in ['inv', 'inv_ids', 'bank', 'bank_ids']:
        if isinstance(fields.get(name), (Record, Fake)):
            fields[name] = fields[name]._fields
    return QuestSnapshot(**fields)
from rs2004.quests.defs.goblindiplomacy import decide, GOBLIN_DIPLOMACY_COIN_TARGET, GOBLIN_DIPLOMACY_QUEST_COIN_RESERVE, goblindiplomacy, goblin_mail_gather_step
from rs2004.quests.food import quest_food

def snap(journal, inv=None):
    if inv is None:
        inv = []
    return _snapshot(**{'journal': journal, 'inv': {_k: _v for _k, _v in inv}, 'worn': set(), 'no_progress': 0, 'bank_coins': 0})

def npc_of(s):
    return s.stop.npc if s.kind == 'talk' else f'<{s.kind}>'

def use_product(s):
    return (s.product if s.product is not None else '') if s.kind == 'use_on' else f'<{s.kind}>'

def custom_name(s):
    return s.name if s.kind == 'custom' else f'<{s.kind}>'

def _fn1():
    quest_food.name = 'Lobster'
after_each(_fn1)

def _fn2():

    def _fn3():
        expect(decide(snap('complete')).kind).to_be('done')
        expect(decide(snap('unknown')).kind).to_be('wait')
        expect(npc_of(decide(snap('not_started')))).to_be('Bartender')
    test('journal branches', _fn3)

    def _fn4():
        s = decide(snap('in_progress', [['goblin mail', 3], ['orange dye', 1], ['blue dye', 1]]))
        expect(use_product(s)).to_be('Orange goblin mail')
    test('provisioned start (3 mail + both dyes) dyes orange first', _fn4)

    def _fn5():
        s = decide(snap('in_progress', [['goblin mail', 2], ['orange goblin mail', 1], ['blue dye', 1]]))
        expect(use_product(s)).to_be('Blue goblin mail')
    test('after orange made, blue is dyed while 2 plain remain (keeps 1 for brown)', _fn5)

    def _fn6():
        s = decide(snap('in_progress', [['goblin mail', 1], ['blue dye', 1]]))
        expect(npc_of(s)).to_be('General Wartface')
    test('blue dye is NOT applied with only 1 plain mail left (reserved for brown)', _fn6)

    def _fn7():
        s = decide(snap('in_progress', [['goblin mail', 1], ['orange goblin mail', 1], ['blue goblin mail', 1]]))
        expect(npc_of(s)).to_be('General Wartface')
    test('both armours made -> hand in at the generals', _fn7)

    def _fn8():
        s = decide(snap('in_progress', [['goblin mail', 3], ['blue dye', 1]]))
        expect(use_product(s)).to_be('Blue goblin mail')
    test('order-independent: blue-first start still keeps a plain for brown', _fn8)

    def _fn9():
        expect(npc_of(decide(snap('in_progress')))).to_be('General Wartface')
    test('bare in-progress re-entry falls back to the generals (total)', _fn9)
describe('goblindiplomacy decide', _fn2)

def _fn10():

    def _fn11():
        expect(goblindiplomacy.food).to_be_undefined()
        expect(goblindiplomacy.sustain).to_equal(Fake(**{'foods': ['Kebab'], 'eat_below_hp': 0.6}))
        expect(goblindiplomacy.tools()).to_contain('kebab')
    test('owns a batch food policy and eats fallback Kebabs before low-level combat becomes lethal', _fn11)

    def _fn12():
        quest_food.name = 'Trout'
        expect(goblindiplomacy.tools()).to_contain('trout')
        _merged13 = {}
        for _k, _v in (snap('in_progress', [['trout', 20], ['bronze dagger', 1]])._fields if isinstance(snap('in_progress', [['trout', 20], ['bronze dagger', 1]]), (Record, Fake)) else {name: getattr(snap('in_progress', [['trout', 20], ['bronze dagger', 1]]), name) for name in QuestSnapshot.FIELDS}).items():
            _merged13[_k] = _v
        for _k, _v in {'bank_known': True, 'free_slots': 0}.items():
            _merged13[_k] = _v
        step = goblin_mail_gather_step(Fake(**_merged13))
        expect(step.kind == 'deposit' and step.keep).to_contain('trout')
    test('preserves the configured quest food during spillover banking', _fn12)

    def _fn14():
        step = goblin_mail_gather_step(snap('in_progress'))
        expect(step.kind).to_be('scan_bank')
    test('checks the bank before assuming a fresh account has no food or cash', _fn14)

    def _fn15():
        quest_food.name = 'Trout'
        _merged16 = {}
        for _k, _v in (snap('in_progress')._fields if isinstance(snap('in_progress'), (Record, Fake)) else {name: getattr(snap('in_progress'), name) for name in QuestSnapshot.FIELDS}).items():
            _merged16[_k] = _v
        for _k, _v in {'bank_known': True, 'bank': {_k: _v for _k, _v in [['trout', 20]]}}.items():
            _merged16[_k] = _v
        with_selected = goblin_mail_gather_step(Fake(**_merged16))
        expect(with_selected.kind).not_.to_be('withdraw')
        _merged17 = {}
        for _k, _v in (snap('in_progress')._fields if isinstance(snap('in_progress'), (Record, Fake)) else {name: getattr(snap('in_progress'), name) for name in QuestSnapshot.FIELDS}).items():
            _merged17[_k] = _v
        for _k, _v in {'bank_known': True, 'bank': {_k: _v for _k, _v in [['kebab', 20]]}}.items():
            _merged17[_k] = _v
        with_fallback = goblin_mail_gather_step(Fake(**_merged17))
        expect(with_fallback.kind).not_.to_be('withdraw')
    test('never withdraws food, whatever the bank holds', _fn15)

    def _fn18():
        _merged19 = {}
        for _k, _v in (snap('in_progress', [['coins', 500]])._fields if isinstance(snap('in_progress', [['coins', 500]]), (Record, Fake)) else {name: getattr(snap('in_progress', [['coins', 500]]), name) for name in QuestSnapshot.FIELDS}).items():
            _merged19[_k] = _v
        for _k, _v in {'bank_known': True, 'free_slots': 10}.items():
            _merged19[_k] = _v
        step = goblin_mail_gather_step(Fake(**_merged19))
        expect(step.kind == 'custom' and step.name).to_be('farm goblin mail')
    test('goes for the mail on coins alone, with no food in the pack', _fn18)

    def _fn20():
        _merged21 = {}
        for _k, _v in (snap('in_progress')._fields if isinstance(snap('in_progress'), (Record, Fake)) else {name: getattr(snap('in_progress'), name) for name in QuestSnapshot.FIELDS}).items():
            _merged21[_k] = _v
        for _k, _v in {'bank_known': True, 'bank_coins': 125, 'bank': {_k: _v for _k, _v in [['coins', 125]]}}.items():
            _merged21[_k] = _v
        step = goblin_mail_gather_step(Fake(**_merged21))
        expect(step.kind == 'withdraw' and step.items).to_equal([Fake(**{'name': 'Coins', 'qty': 125})])
    test('uses banked cash before asking a level-three account to self-fund', _fn20)

    def _fn22():
        _merged23 = {}
        for _k, _v in (snap('in_progress')._fields if isinstance(snap('in_progress'), (Record, Fake)) else {name: getattr(snap('in_progress'), name) for name in QuestSnapshot.FIELDS}).items():
            _merged23[_k] = _v
        for _k, _v in {'bank_known': True, 'bank': {}}.items():
            _merged23[_k] = _v
        step = goblin_mail_gather_step(Fake(**_merged23))
        expect(custom_name(step)).to_be(f'earn {GOBLIN_DIPLOMACY_COIN_TARGET} gp')
    test('earns the quest purse when the account is completely empty', _fn22)

    def _fn24():
        _merged25 = {}
        for _k, _v in (snap('in_progress', [['coins', GOBLIN_DIPLOMACY_QUEST_COIN_RESERVE]])._fields if isinstance(snap('in_progress', [['coins', GOBLIN_DIPLOMACY_QUEST_COIN_RESERVE]]), (Record, Fake)) else {name: getattr(snap('in_progress', [['coins', GOBLIN_DIPLOMACY_QUEST_COIN_RESERVE]]), name) for name in QuestSnapshot.FIELDS}).items():
            _merged25[_k] = _v
        for _k, _v in {'bank_known': True}.items():
            _merged25[_k] = _v
        step = goblin_mail_gather_step(Fake(**_merged25))
        expect(custom_name(step)).to_be('farm goblin mail')
    test('travels to Goblin Village on the purse alone, with no batch of food to gather first', _fn24)

    def _fn26():
        _merged27 = {}
        for _k, _v in (snap('in_progress', [['coins', 1]])._fields if isinstance(snap('in_progress', [['coins', 1]]), (Record, Fake)) else {name: getattr(snap('in_progress', [['coins', 1]]), name) for name in QuestSnapshot.FIELDS}).items():
            _merged27[_k] = _v
        for _k, _v in {'bank_known': True, 'bank': {}}.items():
            _merged27[_k] = _v
        step = goblin_mail_gather_step(Fake(**_merged27))
        expect(custom_name(step)).to_be(f'earn {GOBLIN_DIPLOMACY_COIN_TARGET} gp')
    test('self-funds the quest reserve when the purse is short', _fn26)
describe('goblindiplomacy goblin-mail survival', _fn10)
