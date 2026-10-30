"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/murder.test.ts (MIT, see thirdparty/rs2b0t)."""


from rs2004.quests.defs.murder.areas import MURDER_OBJ, SUSPECTS, suspect_order
from rs2004.quests.defs.murder import decide, murder, source_pot
from rs2004.quests.defs.murder.journal import MURDER_STAGE, POISON_PROVED, THREAD_FOUND, parse_murder_journal
from rs2004.quests.defs.murder.state import accused, held_thread
NOT_STARTED = '@dbl@I can start this quest by speaking to one of the @dre@Guards@dbl@ at|' + "@dbl@the @dre@Sinclair Mansion@dbl@, North of the @dre@Seer's Village@dbl@"
PREAMBLE = '@str@Lord Sinclair, a prominent nobleman, had been horribly|' + '@str@murdered at his mansion. The guards had been sent to|' + '@str@investigate his murder, but have been completely stuck.|' + '@dbl@One of the @dre@guards@dbl@ has asked me for my help in solving the|' + '@dbl@murder. I should @dre@examine the crime scene@dbl@ very closely for|' + '@dbl@evidence, and @dre@investigate everybody@dbl@ in the area carefully||'
THREAD_LINE = '@dbl@I have found some @dre@coloured thread@dbl@. It might be useful.|'
WEAPON_LINE = '@dbl@I have taken the @dre@murder weapon@dbl@. I think it might help me.|'
POISON_PAGE = '@str@Lord Sinclair, a prominent nobleman, had been horribly|' + '@str@murdered at his mansion. The guards had been sent to|' + '@str@investigate his murder, but have been completely stuck.|' + '@str@One of the guards asked me for my help in solving the|' + '@str@murder. After careful examination of the crime scene and|' + '@str@interrogating all suspects, I worked out who was guilty.|' + '@dbl@I have @dre@indisputable evidence@dbl@ of who the murderer must be.|' + '@dbl@I should take it to one of the @dre@Guards@dbl@ immediately.'
COMPLETE = '@str@One of the guards asked me for my help in solving the|' + '@str@murder. After careful examination of the crime scene and|' + '@str@interrogating all suspects, I worked out who was guilty. I|' + '@str@took the evidence I had collected to the Guards and|' + '@str@explained how it could identify the killer. Impressed with|' + '@str@my deductions, the killer was arrested and I was given a|' + '@str@fair reward for my help in solving the crime.||' + '@red@QUEST COMPLETE!'


def id_counts(ids):
    result = {}
    for id in ids:
        _v1 = result.get(id)
        result[id] = ((_v1 if _v1 is not None else 0)) + 1
    return result


def snap(options=None):
    if options is None:
        options = Obj({})
    progress = (options.progress if 'progress' in options else Obj({
        'stage': (options.stage if options.stage is not None else MURDER_STAGE.STARTED),
        'flags': set((options.flags if options.flags is not None else [])),
    }))
    return Obj({
        'journal': (options.journal if options.journal is not None else 'in_progress'),
        'inv': {},
        'inv_ids': id_counts((options.inv_ids if options.inv_ids is not None else [])),
        'worn': set(),
        'no_progress': 0,
        'bank_coins': 2000000,
        'stage': (progress.stage if progress is not None else None),
        'progress': progress,
        'bank': {},
        'bank_ids': id_counts((options.bank_ids if options.bank_ids is not None else [])),
        'bank_known': (options.bank_known if options.bank_known is not None else True),
        'free_slots': 28,
    })


ANNA = SUSPECTS[0]
BOB = SUSPECTS[1]
CAROL = SUSPECTS[2]
DAVID = SUSPECTS[3]
ELIZABETH = SUSPECTS[4]
FRANK = SUSPECTS[5]
POT = MURDER_OBJ.POT


def custom_name(step):
    return (step.name if step.kind == 'custom' else None)


def _fn2():
    def _fn3():
        progress = parse_murder_journal(NOT_STARTED)
        expect((progress.stage if progress is not None else None)).to_be(MURDER_STAGE.NOT_STARTED)
        _v4 = (progress.flags if progress is not None else None)
        expect(list(((_v4 if _v4 is not None else [])))).to_equal([])
    test('reads the not-started page as stage 0', _fn3)

    def _fn5():
        progress = parse_murder_journal(PREAMBLE + '||')
        expect((progress.stage if progress is not None else None)).to_be(MURDER_STAGE.STARTED)
        _v6 = (progress.flags if progress is not None else None)
        expect(list(((_v6 if _v6 is not None else [])))).to_equal([])
    test('reads a started page with no evidence as stage 1 and no flags', _fn5)

    def _fn7():
        progress = parse_murder_journal(PREAMBLE + THREAD_LINE + '|')
        expect(('thread' in (progress.flags if progress is not None else None))).to_be(True)
        expect(('weapon' in (progress.flags if progress is not None else None))).to_be(False)
        expect(('weapon' in (parse_murder_journal(PREAMBLE + THREAD_LINE + WEAPON_LINE).flags if parse_murder_journal(PREAMBLE + THREAD_LINE + WEAPON_LINE) is not None else None))).to_be(True)
    test('flags the thread and the weapon only when their lines are on the page', _fn7)

    def _fn8():
        progress = parse_murder_journal(POISON_PAGE)
        expect((progress.stage if progress is not None else None)).to_be(MURDER_STAGE.STARTED)
        expect((POISON_PROVED in (progress.flags if progress is not None else None))).to_be(True)
    test('reads the indisputable-evidence page as the poison proved', _fn8)

    def _fn9():
        expect((parse_murder_journal(COMPLETE).stage if parse_murder_journal(COMPLETE) is not None else None)).to_be(MURDER_STAGE.COMPLETE)
    test('reads the finished page as complete', _fn9)

    def _fn10():
        expect(parse_murder_journal('')).to_be_undefined()
    test('reports nothing for a page it does not recognise', _fn10)


describe('Murder Mystery journal parsing', _fn2)


def _fn11():
    def _fn12():
        expect(suspect_order(MURDER_OBJ.THREAD_GREEN)[0:2]).to_equal([ANNA, DAVID])
        expect(suspect_order(MURDER_OBJ.THREAD_RED)[0:2]).to_equal([BOB, CAROL])
        expect(suspect_order(MURDER_OBJ.THREAD_BLUE)[0:2]).to_equal([ELIZABETH, FRANK])
    test('puts the two whose clothes match the thread first', _fn12)

    def _fn13():
        expect(suspect_order(MURDER_OBJ.THREAD_BLUE)).to_have_length(len(SUSPECTS))
        expect(set(suspect_order(MURDER_OBJ.THREAD_BLUE))).to_equal(set(SUSPECTS))
    test('still lists every suspect, so a colour that convicts nobody is not a dead end', _fn13)


describe('Murder Mystery suspect order', _fn11)


def _fn14():
    def _fn15():
        expect(accused(snap(Obj({'inv_ids': [ANNA.silver]})), MURDER_OBJ.THREAD_GREEN)).to_be_null()
    test('names nobody while the killers print is missing', _fn15)

    def _fn16():
        pack = [MURDER_OBJ.KILLERS_PRINT, ANNA.silver, DAVID.silver]
        expect(accused(snap(Obj({'inv_ids': pack})), MURDER_OBJ.THREAD_GREEN)).to_be(DAVID)
        expect(accused(snap(Obj({'inv_ids': [MURDER_OBJ.KILLERS_PRINT, ANNA.silver]})), MURDER_OBJ.THREAD_GREEN)).to_be(ANNA)
    test('names the last keepsake in test order, which is the suspect the print matched', _fn16)

    def _fn17():
        expect(accused(snap(Obj({'inv_ids': [MURDER_OBJ.KILLERS_PRINT]})), MURDER_OBJ.THREAD_RED)).to_be_null()
    test('names nobody when the keepsakes are gone', _fn17)

    def _fn18():
        expect(held_thread(snap(Obj({'inv_ids': [MURDER_OBJ.THREAD_BLUE]})))).to_be(MURDER_OBJ.THREAD_BLUE)
        expect(held_thread(snap())).to_be_null()
    test('reads the thread colour off the pack', _fn18)


describe('Murder Mystery deduction from the pack', _fn14)


def _fn19():
    def _fn20():
        expect(source_pot(snap(Obj({'bank_known': False})))).to_equal(Obj({'kind': 'scan_bank', 'bank': murder.bank}))
    test('scans the bank before deciding the pot has to be bought', _fn20)

    def _fn21():
        step = source_pot(snap(Obj({'bank_ids': [POT]})))
        expect((step.kind if step is not None else None)).to_be('withdraw')
    test('withdraws a banked pot rather than walking to Catherby', _fn21)

    def _fn22():
        step = source_pot(snap())
        expect((step.kind if step is not None else None)).to_be('buy')
        expect((step.kind if step is not None else None) == 'buy' and step.shop.npc).to_be('Arhein')
    test('buys from Arhein when neither the pack nor the bank holds one', _fn22)

    def _fn23():
        expect(source_pot(snap(Obj({'inv_ids': [POT]})))).to_be_null()
        expect(source_pot(snap(Obj({'inv_ids': [MURDER_OBJ.POT_FLOUR]})))).to_be_null()
    test('asks for nothing once a pot or a pot of flour is carried', _fn23)


describe('Murder Mystery pot sourcing', _fn19)


def _fn24():
    def _fn25():
        expect(decide(snap(Obj({'journal': 'unknown'})))).to_equal(Obj({'kind': 'wait', 'reason': 'quest journal not loaded'}))
    test('waits while the journal has not loaded', _fn25)

    def _fn26():
        expect(decide(snap(Obj({'journal': 'complete'})))).to_equal(Obj({'kind': 'done'}))
    test('is done once the journal is green', _fn26)

    def _fn27():
        expect(decide(snap(Obj({'progress': None}))).kind).to_be('wait')
    test('waits when a started journal cannot be read', _fn27)

    def _fn28():
        step = decide(snap(Obj({'journal': 'not_started', 'stage': MURDER_STAGE.NOT_STARTED})))
        expect(step.kind).to_be('buy')
    test('buys the pot before the quest is even started, so the trip is not made twice', _fn28)

    def _fn29():
        step = decide(snap(Obj({
        'journal': 'not_started',
        'progress': Obj({'stage': MURDER_STAGE.NOT_STARTED, 'flags': set()}),
        'inv_ids': [POT],
    })))
        expect(step.kind == 'talk' and step.stop.prefer).to_equal(["Sure, I'll help"])
    test('starts the quest with the guard once a pot is carried', _fn29)

    def _fn30():
        step = decide(snap(Obj({'inv_ids': [POT], 'bank_ids': [MURDER_OBJ.DAGGER]})))
        expect(step.kind).to_be('withdraw')
        expect(step.kind == 'withdraw' and [i['id'] for i in step.items]).to_equal([MURDER_OBJ.DAGGER])
    test('withdraws evidence the bank is holding before any leg that a banked copy would block', _fn30)

    def _fn31():
        step = decide(snap(Obj({'inv_ids': [POT], 'flags': [THREAD_FOUND]})))
        expect(custom_name(step)).to_be('take the thread from the smashed window')
    test('takes the thread first, because its colour is what halves the suspect list', _fn31)

    def _fn32():
        step = decide(snap(Obj({'inv_ids': [POT, MURDER_OBJ.THREAD_RED], 'flags': [THREAD_FOUND]})))
        expect(custom_name(step)).to_be("match the murderer's fingerprints")
    test('hunts the prints once the thread is in the pack', _fn32)

    def _fn33():
        step = decide(snap(Obj({'inv_ids': [MURDER_OBJ.THREAD_RED, MURDER_OBJ.KILLERS_PRINT, BOB.silver], 'flags': [THREAD_FOUND]})))
        expect(custom_name(step)).to_be('prove the family lied about the poison')
    test('proves the poison once the killers print is in the pack', _fn33)

    def _fn34():
        step = decide(snap(Obj({'inv_ids': [MURDER_OBJ.THREAD_RED, MURDER_OBJ.KILLERS_PRINT, BOB.silver], 'flags': [THREAD_FOUND]})))
        expect(step.kind).to_be('custom')
    test('stops asking for a pot once the prints are matched', _fn34)

    def _fn35():
        step = decide(snap(Obj({
        'inv_ids': [MURDER_OBJ.THREAD_RED, MURDER_OBJ.KILLERS_PRINT, BOB.silver],
        'flags': [THREAD_FOUND, POISON_PROVED],
    })))
        expect(step.kind == 'talk' and step.stop.prefer).to_equal(['I know who did it'])
    test('hands in to the guard once the poison is proved as well', _fn35)


describe('Murder Mystery decide', _fn24)
