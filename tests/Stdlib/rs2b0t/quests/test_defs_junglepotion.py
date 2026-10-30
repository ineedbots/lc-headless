"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/junglepotion.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record

from rs2004.quests.defs.junglepotion import JP_STAGE, JUNGLE_HERBS, decide, herb_for_stage, junglepotion, parse_jungle_journal
from rs2004.quests.engine.types import QuestSnapshot
from rs2004.quests.food import quest_food
original_food = None


def _fn1():
    global original_food
    original_food = quest_food.name
    quest_food.name = 'Lobster'


before_each(_fn1)


def _fn2():
    quest_food.name = original_food


after_each(_fn2)


def snapshot(o=None):
    if o is None:
        o = Record({})
    return QuestSnapshot(**{
        'journal': (o.journal if o.journal is not None else 'in_progress'),
        'inv': (o.inv._fields if isinstance(o.inv, Record) else (o.inv or {})),
        'inv_ids': (o.inv_ids._fields if isinstance(o.inv_ids, Record) else (o.inv_ids or {})),
        'worn': (o.worn if o.worn is not None else set()),
        'worn_ids': (o.worn_ids if o.worn_ids is not None else set()),
        'no_progress': 0,
        'bank_coins': (o.bank_coins if o.bank_coins is not None else 0),
        'stage': (o.stage if o.stage is not None else (o.progress.stage if o.progress is not None else None)),
        'progress': o.progress,
        'bank': (o.bank._fields if isinstance(o.bank, Record) else (o.bank or {})),
        'bank_ids': (o.bank_ids._fields if isinstance(o.bank_ids, Record) else (o.bank_ids or {})),
        'bank_known': (o.bank_known if o.bank_known is not None else True),
        'tile': (Record({'x': 2809, 'z': 3086, 'level': 0}) if o.tile is None else o.tile),
        'free_slots': (o.free_slots if o.free_slots is not None else 28),
    })


def _fn3():
    def _fn4():
        expect(len(set([h.unid_id for h in JUNGLE_HERBS]))).to_be(5)
        expect(len(set([h.id for h in JUNGLE_HERBS]))).to_be(5)
    test('every unidentified herb shares one display name, so ids are the only key', _fn4)

    def _fn5():
        expect((herb_for_stage(JP_STAGE.GET_SNAKE_WEED).key if herb_for_stage(JP_STAGE.GET_SNAKE_WEED) is not None else None)).to_be('snake weed')
        expect((herb_for_stage(JP_STAGE.FOUND_SNAKE_WEED).key if herb_for_stage(JP_STAGE.FOUND_SNAKE_WEED) is not None else None)).to_be('snake weed')
        expect((herb_for_stage(JP_STAGE.GET_ARDRIGAL).key if herb_for_stage(JP_STAGE.GET_ARDRIGAL) is not None else None)).to_be('ardrigal')
        expect((herb_for_stage(JP_STAGE.FOUND_SITO_FOIL).key if herb_for_stage(JP_STAGE.FOUND_SITO_FOIL) is not None else None)).to_be('sito foil')
        expect((herb_for_stage(JP_STAGE.GET_VOLENCIA_MOSS).key if herb_for_stage(JP_STAGE.GET_VOLENCIA_MOSS) is not None else None)).to_be('volencia moss')
        expect((herb_for_stage(JP_STAGE.FOUND_ROGUES_PURSE).key if herb_for_stage(JP_STAGE.FOUND_ROGUES_PURSE) is not None else None)).to_be('rogues purse')
    test('both stages of a herb map to the same herb', _fn5)

    def _fn6():
        expect(herb_for_stage(JP_STAGE.NOT_STARTED)).to_be_null()
        expect(herb_for_stage(JP_STAGE.FOUND_ALL_HERBS)).to_be_null()
        expect(herb_for_stage(JP_STAGE.COMPLETE)).to_be_null()
    test('stages outside the herb run have no herb', _fn6)

    def _fn7():
        expect([h.key for h in [h for h in JUNGLE_HERBS if h.underground]]).to_equal(['rogues purse'])
    test('only the rogues purse is underground', _fn7)


describe('jungle potion herbs', _fn3)


def _fn8():
    def _fn9():
        p = parse_jungle_journal('@dbl@I can start this quest by speaking to @dre@Trufitus Shakaya|')
        expect((p.stage if p is not None else None)).to_be(JP_STAGE.NOT_STARTED)
    test('not started', _fn9)

    def _fn10():
        expect((parse_jungle_journal('@str@As a reward he showed me some herblore techniques.||@red@QUEST COMPLETE!').stage if parse_jungle_journal('@str@As a reward he showed me some herblore techniques.||@red@QUEST COMPLETE!') is not None else None)).to_be(JP_STAGE.COMPLETE)
    test('complete', _fn10)

    def _fn11():
        p = parse_jungle_journal([
        '@str@I spoke to Trufitus, he needs to commune with the|',
        "@str@gods, he's asked me to help him by collecting herbs.||",
        '@dbl@I need to pick some fresh @dre@Snakeweed@dbl@ for @dre@Trufitus@dbl@.',
    ])
        expect((p.stage if p is not None else None)).to_be(JP_STAGE.GET_SNAKE_WEED)
    test('asked for a herb but not yet holding it', _fn11)

    def _fn12():
        p = parse_jungle_journal([
        '@str@I picked some fresh Snakeweed for Trufitus.||',
        '@dbl@I need to give the @dre@Snake Weed@dbl@ to @dre@Trufitus@dbl@.',
    ])
        expect((p.stage if p is not None else None)).to_be(JP_STAGE.FOUND_SNAKE_WEED)
    test('picked it: the "give" line outranks the "pick" line', _fn12)

    def _fn13():
        p = parse_jungle_journal([
        "@str@I've given Snakeweed, Ardrigal and Sito Foil|",
        '@str@to Trufitus.||',
        '@dbl@I need to pick some fresh @dre@Volencia Moss@dbl@ for @dre@Trufitus@dbl@.',
    ])
        expect((p.stage if p is not None else None)).to_be(JP_STAGE.GET_VOLENCIA_MOSS)
    test('a later herb outranks the history of an earlier one', _fn13)

    def _fn14():
        p = parse_jungle_journal([
        "@str@I've given Snakeweed, Ardrigal, Sito Foil|",
        '@str@and Volencia Moss to Trufitus.||',
        '@dbl@I need to give the @dre@Rogue Purse@dbl@ to @dre@Trufitus@dbl@.',
    ])
        expect((p.stage if p is not None else None)).to_be(JP_STAGE.FOUND_ROGUES_PURSE)
    test('the rogues purse "give" line is singular in the engine text', _fn14)

    def _fn15():
        p = parse_jungle_journal([
        '@str@I have given Trufitus Snakeweed, Ardrigal,|',
        '@str@Sito Foil,Volencia moss and Rogues purse.||',
        '@str@Trufitus needs to commune with the gods.||',
        '@dbl@I should speak to @dre@Trufitus@dbl@.',
    ])
        expect((p.stage if p is not None else None)).to_be(JP_STAGE.FOUND_ALL_HERBS)
    test('all five delivered', _fn15)

    def _fn16():
        expect(parse_jungle_journal('some other quest entirely')).to_be_undefined()
    test('unrecognised text yields nothing rather than a guess', _fn16)


describe('parseJungleJournal', _fn8)


def _fn17():
    def _fn18():
        expect(decide(snapshot(Fake(**{
        'journal': 'not_started',
        'stage': 0,
        'bank_known': False,
        'tile': Record({'x': 2615, 'z': 3332, 'level': 0}),
    }))).kind).to_be('scan_bank')
    test('reads the bank before departing the mainland with an empty pack', _fn18)

    def _fn19():
        step = decide(snapshot(Fake(**{
        'journal': 'not_started',
        'stage': 0,
        'tile': Record({'x': 2615, 'z': 3332, 'level': 0}),
        'bank': {_k: _v for _k, _v in [['coins', 6204130], ['lobster', 7671]]},
    })))
        expect(step).to_match_object(Record({
        'kind': 'withdraw',
        'items': [Record({'name': 'Coins', 'qty': 1000}), Record({'name': 'Lobster', 'qty': 8})],
    }))
    test('draws food and money for both crossings before entering the jungle', _fn19)

    def _fn20():
        step = decide(snapshot(Fake(**{'stage': JP_STAGE.GET_SNAKE_WEED, 'bank_known': False})))
        expect(step.kind == 'custom' and step.name).to_be('pick Snake weed')
    test('continues a bankless resume without trying to top up food on the mainland', _fn20)

    def _fn21():
        expect(decide(snapshot(Fake(**{'stage': 1, 'bank_known': False, 'tile': Record({'x': 2955, 'z': 3204, 'level': 0})}))).kind).to_be('scan_bank')
    test('Rimmington is mainland and still needs provisions', _fn21)

    def _fn22():
        step = decide(snapshot(Fake(**{
        'stage': 2,
        'tile': Record({'x': 2615, 'z': 3332, 'level': 0}),
        'free_slots': 0,
        'inv': {_k: _v for _k, _v in [['snake weed', 1], ['logs', 27]]},
        'inv_ids': {_k: _v for _k, _v in [[1526, 1], [1511, 27]]},
        'bank': {_k: _v for _k, _v in [['coins', 1000], ['lobster', 8]]},
    })))
        expect(step.kind).to_be('deposit')
        expect(step.kind == 'deposit' and step.keep_ids).to_contain(1526)
        expect(step.kind == 'deposit' and step.keep).not_.to_contain('logs')
    test('makes room for provisions without banking the current quest herb', _fn22)

    def _fn23():
        expect(decide(snapshot(Fake(**{'journal': 'complete'}))).kind).to_be('done')
    test('a complete journal is done', _fn23)

    def _fn24():
        expect(decide(snapshot(Fake(**{'journal': 'unknown'}))).kind).to_be('wait')
    test('an unloaded journal waits — it is not notStarted', _fn24)

    def _fn25():
        expect(decide(snapshot(Fake(**{'stage': None}))).kind).to_be('wait')
    test('a missing stage waits rather than guessing', _fn25)

    def _fn26():
        step = decide(snapshot(Fake(**{'journal': 'not_started', 'stage': JP_STAGE.NOT_STARTED})))
        expect(step.kind).to_be('custom')
        expect(step.kind == 'custom' and step.name).to_contain('Trufitus')
    test('not started asks Trufitus for the job', _fn26)

    def _fn27():
        # Only picking advances get_ to found_, and only found_ accepts a hand-in.
        step = decide(snapshot(Fake(**{'stage': JP_STAGE.GET_ARDRIGAL, 'inv_ids': {_k: _v for _k, _v in [[1528, 1]]}})))
        expect(step.kind == 'custom' and step.name).to_be('pick Ardrigal')
    test('a get_ stage picks even while an identified herb is already held', _fn27)

    def _fn28():
        # At found_snake_weed with the unid held the journal writes no line at all,
        # and every other found_ stage writes the previous "go and pick it" line.
        found = decide(snapshot(Fake(**{'stage': JP_STAGE.FOUND_ARDRIGAL, 'inv_ids': {_k: _v for _k, _v in [[1527, 1]]}})))
        expect(found.kind == 'custom' and found.name).to_be('identify the Ardrigal')
        no_stage = decide(snapshot(Fake(**{'stage': None, 'inv_ids': {_k: _v for _k, _v in [[1525, 1]]}})))
        expect(no_stage.kind == 'custom' and no_stage.name).to_be('identify the Snake weed')
        wrong_stage = decide(snapshot(Fake(**{'stage': JP_STAGE.GET_SITO_FOIL, 'inv_ids': {_k: _v for _k, _v in [[1529, 1]]}})))
        expect(wrong_stage.kind == 'custom' and wrong_stage.name).to_be('identify the Sito foil')
    test('a carried unid is identified whatever the journal says', _fn28)

    def _fn29():
        step = decide(snapshot(Fake(**{'stage': JP_STAGE.FOUND_ARDRIGAL, 'inv_ids': {_k: _v for _k, _v in [[1528, 1]]}})))
        expect(step.kind == 'custom' and step.name).to_contain('give the Ardrigal')
    test('a found_ stage with a clean herb hands it over', _fn29)

    def _fn30():
        step = decide(snapshot(Fake(**{'stage': JP_STAGE.FOUND_SITO_FOIL})))
        expect(step.kind == 'custom' and step.name).to_be('pick Sito foil')
    test('a found_ stage with nothing held re-picks', _fn30)

    def _fn31():
        step = decide(snapshot(Fake(**{'stage': JP_STAGE.FOUND_ALL_HERBS})))
        expect(step.kind == 'custom' and step.name).to_contain('commune')
    test('all five delivered goes back to Trufitus', _fn31)


describe('junglepotion decide', _fn17)


def _fn32():
    def _fn33():
        expect(junglepotion.owns_inventory).to_be(True)
    test('it owns its inventory — Karamja has no bank', _fn33)

    def _fn34():
        expect(junglepotion.record.requirements.quests).to_equal(['druid'])
    test('the record carries the Druidic Ritual prerequisite the engine enforces', _fn34)


describe('junglepotion module', _fn32)
