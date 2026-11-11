"""rs2b0t's test/api/ai/quests/defs/tbwt-supplies.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestProgress, QuestSnapshot
from rs2004.game import skills
from rs2004.quests.defs.tbwt.areas import TB_ARMOUR, TB_ID, TB_LUBUFU, TB_MAIN, TB_NAME, TB_POTIONS, TB_SPEARS, TB_TAMAYU, TB_TIADECHE, TB_TINSAY
from rs2004.quests.defs.tbwt.journal import TB_FLAG
from rs2004.quests.defs.tbwt.supplies import TB_KEEP_IDS, arrow_choice, bow_choice, doses_wanted, outstanding_supplies, potions_in_bank, prepare, spear_in_bank, spear_wanted

KARAMJA = Record({'x': 2780, 'z': 3087, 'level': 0})
IRON = TB_SPEARS[0]
STEEL = TB_SPEARS[1]
RUNE = TB_SPEARS[4]
DOSE4 = TB_POTIONS[0]
DOSE2 = TB_POTIONS[2]
DOSE1 = TB_POTIONS[3]
KIT = ['Maple shortbow', 'Adamant arrow'] + list(TB_ARMOUR)


def snap(options=None):
    if options is None:
        options = Record({})
    flags = set([
        f'{TB_FLAG.TIADECHE}:{(options.tiadeche if options.tiadeche is not None else TB_TIADECHE.UNKNOWN)}',
        f'{TB_FLAG.LUBUFU}:{(options.lubufu if options.lubufu is not None else TB_LUBUFU.UNKNOWN)}',
        f'{TB_FLAG.TAMAYU}:{(options.tamayu if options.tamayu is not None else TB_TAMAYU.UNKNOWN)}',
        f'{TB_FLAG.TINSAY}:{(options.tinsay if options.tinsay is not None else TB_TINSAY.UNKNOWN)}',
    ])
    if options.agility:
        flags.add(TB_FLAG.AGILITY)
    if options.spear:
        flags.add(TB_FLAG.SPEAR)
    return QuestSnapshot(**{
        'journal': 'in_progress',
        'inv': {_k: _v for _k, _v in (options.inv if options.inv is not None else [])},
        'inv_ids': {_k: _v for _k, _v in (options.inv_ids if options.inv_ids is not None else [])},
        'worn': set([n.lower() for n in ((options.worn if options.worn is not None else []))]),
        'worn_ids': set(),
        'no_progress': 0,
        'bank_coins': 2000000,
        'stage': TB_MAIN.STARTED,
        'progress': QuestProgress(TB_MAIN.STARTED, flags),
        'bank': {_k: _v for _k, _v in [[n.lower(), q] for n, q in ((options.bank if options.bank is not None else []))]},
        'bank_ids': {_k: _v for _k, _v in (options.bank_ids if options.bank_ids is not None else [])},
        'bank_known': (options.bank_known if options.bank_known is not None else True),
        'tile': KARAMJA,
        'free_slots': (options.free_slots if options.free_slots is not None else 14),
        'ranged': (options.ranged if options.ranged is not None else 70),
    })


def names(options=None):
    if options is None:
        options = Record({})
    return [s.name for s in outstanding_supplies(snap(options))]


DRESSED = Record({'worn': KIT, 'inv': [['coins', 500], ['lobster', 6]]})


def _upstream_fn2():
    _upstream_merged3 = {}
    for _k, _v in (DRESSED._fields if isinstance(DRESSED, Record) else DRESSED).items():
        _upstream_merged3[_k] = _v
    for _k, _v in {
        'lubufu': TB_LUBUFU.COMPLETE,
        'tamayu': TB_TAMAYU.COMPLETE,
        'tinsay': TB_TINSAY.COMPLETE,
        'tiadeche': TB_TIADECHE.REQUEST_MANUAL,
    }.items():
        _upstream_merged3[_k] = _v
    ready = Record(_upstream_merged3)
    lower = ['Adamant chainbody', 'Adamant platelegs', 'Adamant full helm']
    leather = ['Leather body', 'Leather chaps', 'Leather cowl']

    def _upstream_fn4():
        spy_on(skills, 'level').mock_return_value(1)
        _upstream_merged5 = {}
        for _k, _v in (ready._fields if isinstance(ready, Record) else ready).items():
            _upstream_merged5[_k] = _v
        for _k, _v in {'worn': ['Maple shortbow', 'Adamant arrow'], 'bank': [[name, 1] for name in leather]}.items():
            _upstream_merged5[_k] = _v
        step = prepare(snap(Record(_upstream_merged5)))
        expect(([item.get('name') for item in step.items] if (step.kind if step is not None else None) == 'withdraw' else step)).to_equal(leather)
    test('withdraws a complete banked leather kit', _upstream_fn4)

    def _upstream_fn6():
        spy_on(skills, 'level').mock_return_value(1)
        _upstream_merged7 = {}
        for _k, _v in (ready._fields if isinstance(ready, Record) else ready).items():
            _upstream_merged7[_k] = _v
        for _k, _v in {
        'bank_known': False,
        'worn': ['Maple shortbow', 'Adamant arrow'],
        'inv': list(((ready.inv if ready.inv is not None else []))) + list([[name.lower(), 1] for name in leather]),
    }.items():
            _upstream_merged7[_k] = _v
        step = prepare(snap(Record(_upstream_merged7)))
        expect((step.kind if step is not None else None)).to_be('custom')
    test('equips carried leather without a bank trip', _upstream_fn6)

    def _upstream_fn8():
        _upstream_merged9 = {}
        for _k, _v in (ready._fields if isinstance(ready, Record) else ready).items():
            _upstream_merged9[_k] = _v
        for _k, _v in {'worn': ['Maple shortbow', 'Adamant arrow'] + list(leather), 'bank': [[name, 1] for name in lower]}.items():
            _upstream_merged9[_k] = _v
        step = prepare(snap(Record(_upstream_merged9)))
        expect(step).to_be_null()
    test('retains worn leather even with metal armor banked', _upstream_fn8)

    def _upstream_fn10():
        spy_on(skills, 'level').mock_return_value(70)
        _upstream_merged11 = {}
        for _k, _v in (ready._fields if isinstance(ready, Record) else ready).items():
            _upstream_merged11[_k] = _v
        for _k, _v in {'worn': ['Maple shortbow', 'Adamant arrow'], 'bank': [[name, 1] for name in lower]}.items():
            _upstream_merged11[_k] = _v
        step = prepare(snap(Record(_upstream_merged11)))
        expect(([item.get('name') for item in step.items] if (step.kind if step is not None else None) == 'withdraw' else step)).to_equal(lower)
    test('withdraws lower armor when Rune is not owned', _upstream_fn10)

    def _upstream_fn12():
        spy_on(skills, 'level').mock_return_value(30)
        _upstream_merged13 = {}
        for _k, _v in (ready._fields if isinstance(ready, Record) else ready).items():
            _upstream_merged13[_k] = _v
        for _k, _v in {
        'worn': ['Maple shortbow', 'Adamant arrow'],
        'bank': [[name, 1] for name in list(TB_ARMOUR) + list(lower)],
    }.items():
            _upstream_merged13[_k] = _v
        step = prepare(snap(Record(_upstream_merged13)))
        expect(([item.get('name') for item in step.items] if (step.kind if step is not None else None) == 'withdraw' else step)).to_equal(lower)
    test('skips banked Rune when Defence is insufficient', _upstream_fn12)

    def _upstream_fn14():
        spy_on(skills, 'level').mock_return_value(70)
        _upstream_merged15 = {}
        for _k, _v in (ready._fields if isinstance(ready, Record) else ready).items():
            _upstream_merged15[_k] = _v
        for _k, _v in {'worn': ['Maple shortbow', 'Adamant arrow'] + list(lower), 'bank': [[name, 1] for name in TB_ARMOUR]}.items():
            _upstream_merged15[_k] = _v
        step = prepare(snap(Record(_upstream_merged15)))
        expect(step).to_be_null()
    test('keeps worn alternatives even when Rune is banked', _upstream_fn14)

    def _upstream_fn16():
        spy_on(skills, 'level').mock_return_value(30)
        _upstream_merged17 = {}
        for _k, _v in (ready._fields if isinstance(ready, Record) else ready).items():
            _upstream_merged17[_k] = _v
        for _k, _v in {'worn': ['Maple shortbow', 'Adamant arrow']}.items():
            _upstream_merged17[_k] = _v
        step = prepare(snap(Record(_upstream_merged17)))
        expect((step.kind if step is not None else None)).to_be('wait')
    test('waits rather than departing with empty armor slots', _upstream_fn16)


describe('tbwt flexible armour', _upstream_fn2)


def _upstream_fn18():
    def _upstream_fn19():
        expect(names()).to_equal([TB_NAME.NET])
    test('a fresh quest only requires the fishing net', _upstream_fn19)

    # Why: each of these is consumed by one leg, and a supply left on the list after its leg drags the bot back across the ferry for it.
    def _upstream_fn20():
        expect(names(Record({'tinsay': TB_TINSAY.GIVEN_RUM}))).not_.to_contain(TB_NAME.KNIFE)
        expect(names(Record({'tinsay': TB_TINSAY.GIVEN_SANDWICH}))).not_.to_contain(TB_NAME.SEAWEED)
        expect(names(Record({
        'tamayu': TB_TAMAYU.COMPLETE,
        'tinsay': TB_TINSAY.COMPLETE,
        'lubufu': TB_LUBUFU.COMPLETE,
        'tiadeche': TB_TIADECHE.REQUEST_MANUAL,
    }))).to_equal([])
    test('a supply drops off the list the moment its leg is behind us', _upstream_fn20)

    def _upstream_fn21():
        expect(names(Record({'tinsay': TB_TINSAY.FETCH_SANDWICH, 'inv_ids': [[TB_ID.SANDWICH, 1]]}))).not_.to_contain(TB_NAME.SEAWEED)
    test('a made sandwich retires the seaweed before Tinsay has eaten it', _upstream_fn21)


describe('tbwt supplies', _upstream_fn18)


def _fn22():
    def _fn23():
        expect(spear_wanted(snap(Record({'inv_ids': [[RUNE.id, 1]]})))).to_be(False)
        expect(spear_wanted(snap(Record({'inv_ids': [[STEEL.kp_id, 1]]})))).to_be(False)
        expect(spear_wanted(snap(Record({'spear': True})))).to_be(False)
        expect(spear_wanted(snap(Record({'tamayu': TB_TAMAYU.COMPLETE})))).to_be(False)
    test('any tier in the pack satisfies the leg, poisoned or bare', _fn23)

    # Why: the paste is the poison, not the shaft, a pack that lost the spear still has to replace it.
    def _fn24():
        expect(spear_wanted(snap(Record({'inv_ids': [[TB_ID.KARAMBWAN_POISON_PASTE, 1]]})))).to_be(True)
    test('paste alone does not count as a spear', _fn24)

    # Why: `inv_del(inv, $spear, 1)` means Tamayu keeps it, so the bank gives up its cheapest one.
    def _fn25():
        expect((spear_in_bank(snap(Record({'bank_ids': [[RUNE.id, 1], [IRON.id, 1]]}))).name if spear_in_bank(snap(Record({'bank_ids': [[RUNE.id, 1], [IRON.id, 1]]}))) is not None else None)).to_be(IRON.name)
        expect((spear_in_bank(snap(Record({'bank_ids': [[RUNE.id, 1]]}))).name if spear_in_bank(snap(Record({'bank_ids': [[RUNE.id, 1]]}))) is not None else None)).to_be(RUNE.name)
    test('the cheapest spear in the bank is the one drawn', _fn25)

    def _fn26():
        expect((spear_in_bank(snap(Record({'bank_ids': [[STEEL.kp_id, 1]]}))).name if spear_in_bank(snap(Record({'bank_ids': [[STEEL.kp_id, 1]]}))) is not None else None)).to_be(STEEL.kp_name)
    test('a ready-poisoned spear is taken when the bank holds no bare one', _fn26)

    # Why: bronze sets neither flag Tamayu checks, and a dragon spear is worth more than the quest.
    def _fn27():
        expect(spear_in_bank(snap(Record({'bank_ids': [[1237, 1], [1249, 1], [3170, 1], [3176, 1]]})))).to_be_null()
    test('bronze and dragon are never drawn', _fn27)

    # Why: an empty bank is not a dead end, the Jogres on this quest's own route drop spears.
    def _fn28():
        _merged29 = {}
        for _k, _v in (DRESSED._fields if isinstance(DRESSED, Record) else DRESSED).items():
            _merged29[_k] = _v
        for _k, _v in {'inv_ids': [
        [TB_ID.NET, 1],
        [TB_ID.KNIFE, 1],
        [TB_ID.PESTLE, 1],
        [TB_ID.TINDERBOX, 1],
        [TB_ID.SEAWEED, 1],
        [DOSE4.id, 1],
    ]}.items():
            _merged29[_k] = _v
        step = prepare(snap(Record(_merged29)))
        expect(step).to_be_null()
    test('a bank with no spear parks nothing, so the hunt can run', _fn28)


describe('tbwt spear choice', _fn22)


def _upstream_fn30():
    def _upstream_fn31():
        expect(doses_wanted(snap(Record({'inv_ids': [[DOSE1.id, 1]]})))).to_be(False)
        expect(doses_wanted(snap(Record({'agility': True})))).to_be(False)
        expect(doses_wanted(snap(Record({'tamayu': TB_TAMAYU.COMPLETE})))).to_be(False)
        expect(doses_wanted(snap())).to_be(True)
    test('four doses in any mix satisfy him', _upstream_fn31)

    def _upstream_fn32():
        expect(potions_in_bank(snap(Record({'bank_ids': [[DOSE4.id, 3]]})))).to_equal([Record({'name': DOSE4.name, 'qty': 1, 'id': DOSE4.id})])
        expect(potions_in_bank(snap(Record({'bank_ids': [[DOSE2.id, 5]]})))).to_equal([Record({'name': DOSE2.name, 'qty': 2, 'id': DOSE2.id})])
        expect(potions_in_bank(snap(Record({'bank_ids': [[DOSE2.id, 1], [DOSE1.id, 4]]})))).to_equal([
        Record({'name': DOSE2.name, 'qty': 1, 'id': DOSE2.id}),
        Record({'name': DOSE1.name, 'qty': 2, 'id': DOSE1.id}),
    ])
        expect(potions_in_bank(snap())).to_equal([])
    test('bottles are drawn fullest first, up to four doses', _upstream_fn32)

    # Why: no shop on the island sells one and no leg of this quest brews one.
    def _upstream_fn33():
        _upstream_merged34 = {}
        for _k, _v in (DRESSED._fields if isinstance(DRESSED, Record) else DRESSED).items():
            _upstream_merged34[_k] = _v
        for _k, _v in {
        'lubufu': TB_LUBUFU.COMPLETE,
        'tiadeche': TB_TIADECHE.REQUEST_MANUAL,
        'inv_ids': [
        [TB_ID.NET, 1],
        [TB_ID.KNIFE, 1],
        [TB_ID.PESTLE, 1],
        [TB_ID.TINDERBOX, 1],
        [TB_ID.SEAWEED, 1],
        [IRON.id, 1],
    ],
    }.items():
            _upstream_merged34[_k] = _v
        step = prepare(snap(Record(_upstream_merged34)))
        expect((step.kind if step is not None else None)).to_be('wait')
        expect((step.kind if step is not None else None) == 'wait' and step.reason).to_contain('agility potion')
    test('a bank with no agility potion parks with a reason', _upstream_fn33)


describe('tbwt agility doses', _upstream_fn30)


def _fn35():
    bows = [['Magic shortbow', 1], ['Yew shortbow', 1], ['Maple shortbow', 1]]

    def _fn36():
        expect(bow_choice(snap(Record({'bank': bows, 'ranged': 70})))).to_be('Magic shortbow')
        expect(bow_choice(snap(Record({'bank': bows, 'ranged': 45})))).to_be('Yew shortbow')
        expect(bow_choice(snap(Record({'bank': bows, 'ranged': 31})))).to_be('Maple shortbow')
    test('the best bow the account can draw wins', _fn36)

    def _fn37():
        expect(bow_choice(snap(Record({'bank': bows, 'worn': ['Willow longbow']})))).to_be('Willow longbow')
    test('a bow already worn is the one used, whatever the bank holds', _fn37)

    def _fn38():
        expect(bow_choice(snap(Record({'bank': [['Magic shortbow', 1]], 'ranged': 20})))).to_be_null()
        expect(bow_choice(snap())).to_be_null()
    test('nothing wieldable reads as no bow at all', _fn38)

    def _fn39():
        expect(arrow_choice(snap(Record({'bank': [['Rune arrow', 500], ['Adamant arrow', 500]]})))).to_be('Adamant arrow')
        expect(arrow_choice(snap(Record({'bank': [['Rune arrow', 500]]})))).to_be('Rune arrow')
        expect(arrow_choice(snap(Record({'bank': [['Bronze arrow', 500]]})))).to_be('Bronze arrow')
        expect(arrow_choice(snap())).to_be_null()
    test('arrows fall back down the tiers', _fn39)

    def _fn40():
        step = prepare(snap(Record({'ranged': 20, 'bank': [['Magic shortbow', 1]], 'inv': [['lobster', 6], ['coins', 500]]})))
        expect((step.kind if step is not None else None)).to_be('wait')
        expect((step.kind if step is not None else None) == 'wait' and step.reason).to_contain('Ranged 20')
    test('an empty quiver rack parks with a reason naming the level', _fn40)


describe('tbwt ranged kit', _fn35)


def _upstream_fn41():
    stocked = [[TB_NAME.COINS, 2000000], ['Lobster', 60]] + list([[n, 200] for n in KIT])
    stocked_ids = [
        [TB_ID.NET, 1],
        [TB_ID.KNIFE, 1],
        [TB_ID.PESTLE, 1],
        [TB_ID.TINDERBOX, 1],
        [TB_ID.SEAWEED, 2],
        [IRON.id, 1],
        [DOSE4.id, 1],
    ]

    def _upstream_fn42():
        _upstream_merged43 = {}
        for _k, _v in (DRESSED._fields if isinstance(DRESSED, Record) else DRESSED).items():
            _upstream_merged43[_k] = _v
        for _k, _v in {'inv_ids': stocked_ids, 'inv': [['coins', 500], ['lobster', 16]], 'free_slots': 0}.items():
            _upstream_merged43[_k] = _v
        step = prepare(snap(Record(_upstream_merged43)))
        expect((step.kind if step is not None else None)).to_be('deposit')
        if (step.kind if step is not None else None) != 'deposit':
            return
        expect(step.keep).not_.to_contain('lobster')
        expect(step.keep_ids).to_contain(TB_ID.NET)
        expect(step.keep_ids).not_.to_contain(TB_ID.KNIFE)
        expect(step.caps).to_contain_equal(Record({'id': 379, 'qty': 6}))
    test('banks excess food while retaining quest items and the ranged kit', _upstream_fn42)

    def _upstream_fn44():
        _upstream_merged46 = {}
        for _k, _v in (DRESSED._fields if isinstance(DRESSED, Record) else DRESSED).items():
            _upstream_merged46[_k] = _v
        for _k, _v in {
        'inv': [['coins', 500]],
        'inv_ids': [(id, _2) for id, _2 in stocked_ids if id != TB_ID.NET],
        'bank': stocked,
        'bank_ids': stocked_ids,
        'free_slots': 8,
    }.items():
            _upstream_merged46[_k] = _v
        step = prepare(snap(Record(_upstream_merged46)))
        expect((step.kind if step is not None else None)).to_be('withdraw')
        if (step.kind if step is not None else None) != 'withdraw':
            return
        expect(step.items).to_contain_equal(Record({'name': TB_NAME.NET, 'id': TB_ID.NET, 'qty': 1}))
        expect(step.items).to_contain_equal(Record({'name': 'Lobster', 'qty': 6}))
        expect(8 - sum([item.get('qty') for item in step.items])).to_be(1)
    test('reserves catch space after withdrawing quest supplies and food together', _upstream_fn44)

    def _upstream_fn47():
        _upstream_merged48 = {}
        for _k, _v in (DRESSED._fields if isinstance(DRESSED, Record) else DRESSED).items():
            _upstream_merged48[_k] = _v
        for _k, _v in {'inv_ids': stocked_ids, 'lubufu': TB_LUBUFU.COMPLETE, 'free_slots': 0}.items():
            _upstream_merged48[_k] = _v
        step = prepare(snap(Record(_upstream_merged48)))
        expect((step.kind if step is not None else None)).to_be('deposit')
        if (step.kind if step is not None else None) == 'deposit':
            expect(step.keep).not_.to_contain('lobster')
    test("removes food from a full resumed pack before accepting Tiadeche's catch", _upstream_fn47)

    def _upstream_fn49():
        _upstream_merged50 = {}
        for _k, _v in (DRESSED._fields if isinstance(DRESSED, Record) else DRESSED).items():
            _upstream_merged50[_k] = _v
        for _k, _v in {'inv_ids': stocked_ids, 'lubufu': TB_LUBUFU.COMPLETE, 'free_slots': 0}.items():
            _upstream_merged50[_k] = _v
        initial = prepare(snap(Record(_upstream_merged50)))
        expect((initial.kind if initial is not None else None)).to_be('deposit')
        _upstream_merged51 = {}
        for _k, _v in (DRESSED._fields if isinstance(DRESSED, Record) else DRESSED).items():
            _upstream_merged51[_k] = _v
        for _k, _v in {
        'inv_ids': stocked_ids,
        'inv': [['coins', 500]],
        'bank': [['Lobster', 6]],
        'lubufu': TB_LUBUFU.COMPLETE,
        'free_slots': 6,
    }.items():
            _upstream_merged51[_k] = _v
        refill = prepare(snap(Record(_upstream_merged51)))
        expect(refill).to_match_object(Record({'kind': 'withdraw', 'items': [Record({'name': 'Lobster', 'qty': 5})]}))
        _upstream_merged52 = {}
        for _k, _v in (DRESSED._fields if isinstance(DRESSED, Record) else DRESSED).items():
            _upstream_merged52[_k] = _v
        for _k, _v in {
        'inv_ids': stocked_ids,
        'inv': [['coins', 500], ['lobster', 2]],
        'bank': [['Lobster', 4]],
        'lubufu': TB_LUBUFU.COMPLETE,
        'free_slots': 4,
    }.items():
            _upstream_merged52[_k] = _v
        expect(prepare(snap(Record(_upstream_merged52)))).to_be_null()
    test('a trimmed full pack refills only the food that fits and resumes the quest', _upstream_fn49)

    def _upstream_fn53():
        _upstream_merged54 = {}
        for _k, _v in (DRESSED._fields if isinstance(DRESSED, Record) else DRESSED).items():
            _upstream_merged54[_k] = _v
        for _k, _v in {'inv_ids': stocked_ids, 'lubufu': TB_LUBUFU.FETCH_KARAMBWANJI, 'free_slots': 0}.items():
            _upstream_merged54[_k] = _v
        step = prepare(snap(Record(_upstream_merged54)))
        expect((step.kind if step is not None else None)).to_be('deposit')
        if (step.kind if step is not None else None) == 'deposit':
            expect(step.keep).not_.to_contain('lobster')
    test('makes room before the first Karambwanji catch from a full pack', _upstream_fn53)

    def _upstream_fn55():
        _upstream_merged56 = {}
        for _k, _v in (DRESSED._fields if isinstance(DRESSED, Record) else DRESSED).items():
            _upstream_merged56[_k] = _v
        for _k, _v in {
        'inv': [['coins', 500], ['lobster', 8]],
        'inv_ids': list(stocked_ids) + [[TB_ID.RAW_KARAMBWANJI, 10]],
        'lubufu': TB_LUBUFU.FETCH_KARAMBWANJI,
        'free_slots': 0,
    }.items():
            _upstream_merged56[_k] = _v
        expect(prepare(snap(Record(_upstream_merged56)))).to_be_null()
    test('lets Lubufu take a full catch before trimming excess food', _upstream_fn55)

    def _upstream_fn57():
        _upstream_merged58 = {}
        for _k, _v in (DRESSED._fields if isinstance(DRESSED, Record) else DRESSED).items():
            _upstream_merged58[_k] = _v
        for _k, _v in {'inv': [['coins', 500]], 'inv_ids': [[TB_ID.NET, 1]], 'bank': [['Lobster', 100]], 'free_slots': 2}.items():
            _upstream_merged58[_k] = _v
        step = prepare(snap(Record(_upstream_merged58)))
        expect(step).to_match_object(Record({'kind': 'withdraw', 'items': [Record({'name': 'Lobster', 'qty': 1})]}))
    test('a tight pack can still take food when the next catch fits', _upstream_fn57)

    def _upstream_fn59():
        previous = quest_food.name
        quest_food.name = 'Cake'
        try:
            _upstream_merged60 = {}
            for _k, _v in (DRESSED._fields if isinstance(DRESSED, Record) else DRESSED).items():
                _upstream_merged60[_k] = _v
            for _k, _v in {'inv_ids': stocked_ids, 'inv': [['coins', 500], ['cake', 4], ['2/3 cake', 3], ['slice of cake', 2]]}.items():
                _upstream_merged60[_k] = _v
            step = prepare(snap(Record(_upstream_merged60)))
            expect((step.kind if step is not None else None)).to_be('deposit')
            if (step.kind if step is not None else None) == 'deposit':
                for name in ['cake', '2/3 cake', 'slice of cake']:
                    expect(step.keep).not_.to_contain(name)
        except Exception as e:
            quest_food.name = previous
            raise e

        quest_food.name = previous
    test('counts partially eaten cakes when trimming the food loadout', _upstream_fn59)

    def _upstream_fn61():
        previous = quest_food.name
        quest_food.name = 'Cake'
        try:
            _upstream_merged62 = {}
            for _k, _v in (DRESSED._fields if isinstance(DRESSED, Record) else DRESSED).items():
                _upstream_merged62[_k] = _v
            for _k, _v in {
            'inv_ids': stocked_ids,
            'inv': [['coins', 500]],
            'bank': [['2/3 cake', 4], ['Slice of cake', 2]],
            'free_slots': 8,
        }.items():
                _upstream_merged62[_k] = _v
            step = prepare(snap(Record(_upstream_merged62)))
            expect(step).to_match_object(Record({'kind': 'withdraw', 'items': [Record({'name': '2/3 cake', 'qty': 4})]}))
            _upstream_merged63 = {}
            for _k, _v in (DRESSED._fields if isinstance(DRESSED, Record) else DRESSED).items():
                _upstream_merged63[_k] = _v
            for _k, _v in {'inv_ids': stocked_ids, 'inv': [['coins', 500], ['2/3 cake', 4]], 'free_slots': 4}.items():
                _upstream_merged63[_k] = _v
            expect(prepare(snap(Record(_upstream_merged63)))).to_be_null()
        except Exception as e:
            quest_food.name = previous
            raise e

        quest_food.name = previous
    test('can refill with the partial cakes it just banked', _upstream_fn61)

    def _upstream_fn64():
        expect((prepare(snap(Record({'bank_known': False, 'worn': KIT}))).kind if prepare(snap(Record({'bank_known': False, 'worn': KIT}))) is not None else None)).to_be('scan_bank')
    test('an unread bank is scanned before anything is judged missing', _upstream_fn64)

    def _upstream_fn65():
        step = prepare(snap(Record({'bank': stocked, 'bank_ids': stocked_ids, 'worn': KIT, 'inv': [['lobster', 6], ['coins', 500]]})))
        expect((step.kind if step is not None else None)).to_be('withdraw')
    test('a stocked bank is withdrawn from', _upstream_fn65)

    def _upstream_fn66():
        _upstream_merged67 = {}
        for _k, _v in (DRESSED._fields if isinstance(DRESSED, Record) else DRESSED).items():
            _upstream_merged67[_k] = _v
        for _k, _v in {
        'lubufu': TB_LUBUFU.COMPLETE,
        'tiadeche': TB_TIADECHE.REQUEST_MANUAL,
        'bank': stocked,
        'bank_ids': stocked_ids,
    }.items():
            _upstream_merged67[_k] = _v
        step = prepare(snap(Record(_upstream_merged67)))
        expect((step.kind if step is not None else None)).to_be('withdraw')
        drawn = ([i.get('name') for i in step.items] if (step.kind if step is not None else None) == 'withdraw' else [])
        expect(drawn).to_contain(IRON.name)
        expect(drawn).to_contain(DOSE4.name)
    test('the spear and the potion ride out on the same withdrawal', _upstream_fn66)

    def _upstream_fn68():
        carried = [[n.lower(), 1] for n in KIT]
        _upstream_merged69 = {}
        for _k, _v in (DRESSED._fields if isinstance(DRESSED, Record) else DRESSED).items():
            _upstream_merged69[_k] = _v
        for _k, _v in {'worn': [], 'inv': list(((DRESSED.inv if DRESSED.inv is not None else []))) + list(carried)}.items():
            _upstream_merged69[_k] = _v
        step = prepare(snap(Record(_upstream_merged69)))
        expect((step.kind if step is not None else None)).to_be('custom')
        expect((step.kind if step is not None else None) == 'custom' and step.name).to_contain('wear')
    test('gear already in the pack is worn without a bank trip', _upstream_fn68)

    # Why: Jiminua's counter is inside the quest area and the bank is a 30gp ferry away.
    def _upstream_fn70():
        _upstream_merged73 = {}
        for _k, _v in (DRESSED._fields if isinstance(DRESSED, Record) else DRESSED).items():
            _upstream_merged73[_k] = _v
        for _k, _v in {
        'lubufu': TB_LUBUFU.COMPLETE,
        'tiadeche': TB_TIADECHE.REQUEST_MANUAL,
        'tamayu': TB_TAMAYU.COMPLETE,
        'bank': stocked,
        'bank_ids': [(id, _2) for id, _2 in stocked_ids if id != TB_ID.KNIFE],
        'inv_ids': [(id, _2) for id, _2 in stocked_ids if id != TB_ID.KNIFE],
    }.items():
            _upstream_merged73[_k] = _v
        step = prepare(snap(Record(_upstream_merged73)))
        expect((step.kind if step is not None else None)).to_be('buy')
        expect((step.kind if step is not None else None) == 'buy' and step.item).to_be(TB_NAME.KNIFE)
    test('a knife the bank does not stock is bought in the village', _upstream_fn70)

    # Why: nothing else stocks a small fishing net on Karamja, so a bank without one is a dead end that has to say so.
    def _upstream_fn74():
        shop_bought = [[TB_ID.KNIFE, 1], [TB_ID.PESTLE, 1], [TB_ID.TINDERBOX, 1], [IRON.id, 1], [DOSE4.id, 1]]
        _upstream_merged75 = {}
        for _k, _v in (DRESSED._fields if isinstance(DRESSED, Record) else DRESSED).items():
            _upstream_merged75[_k] = _v
        for _k, _v in {'inv_ids': shop_bought}.items():
            _upstream_merged75[_k] = _v
        step = prepare(snap(Record(_upstream_merged75)))
        expect((step.kind if step is not None else None)).to_be('wait')
        expect((step.kind if step is not None else None) == 'wait' and step.reason).to_contain(TB_NAME.NET)
    test('a bank with none of it parks with a reason rather than looping', _upstream_fn74)

    def _upstream_fn76():
        _upstream_merged77 = {}
        for _k, _v in (DRESSED._fields if isinstance(DRESSED, Record) else DRESSED).items():
            _upstream_merged77[_k] = _v
        for _k, _v in {'inv_ids': stocked_ids}.items():
            _upstream_merged77[_k] = _v
        expect(prepare(snap(Record(_upstream_merged77)))).to_be_null()
    test('nothing is outstanding once the pack is right', _upstream_fn76)


describe('tbwt prepare', _upstream_fn41)

from rs2004.quests.food import quest_food
