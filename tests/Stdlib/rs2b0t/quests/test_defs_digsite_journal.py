"""Ported from rs2b0t's test/api/ai/quests/defs/digsite-journal.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.quests.defs.digsite.journal import DIG_STAGE, parse_digsite_journal

OPENING = '@str@I should speak to the Examiner about taking Earth|@str@Science Exams.|'
STAMP_DONE = [
    '|@str@I should take the letter the Examiner has given me|@str@to the Curator of the Varrock Museum for his approval.|',
    '|@str@I need to return the letter of recommendation from the|@str@Curator of Varrock Museum, to the Examiner at the|@str@Exam Centre for inspection.|',
]
NOT_STARTED = [
    '@dbl@I can start this quest by speaking to the @dre@Examiner @dbl@at the @dre@Digsite Exam Centre.|',
    '|@dbl@To complete this quest I need:|',
    '@dre@Level 10 Agility|',
    '@dre@Level 10 Herblore|',
    '@dre@Level 25 Thieving|',
]
STAMPING_NO_LETTER = [
    OPENING,
    '|@dbl@I should take the @dre@letter @dbl@the @dre@Examiner @dbl@has given me to the @dre@Curator of the Varrock Museum @dbl@for his approval.',
]
STAMPING_LETTER_HELD = [
    OPENING,
    '|@str@I should take the letter the Examiner has given me|@str@to the Curator of the Varrock Museum for his approval.|',
    '|@dbl@I need to return the @dre@letter of recommendation @dbl@from the @dre@Curator of Varrock Museum@dbl@, to the @dre@Examiner @dbl@at the|@dbl@Exam Centre for inspection.|',
]
GREEN_TODO = '|@dbl@I need to speak to the student in the green top about the exams.'
PURPLE_TODO = '|@dbl@I need to speak to the student in the purple shirt about the exams.'
ORANGE_TODO = '|@dbl@I need to speak to the student in the orange top about the exams.'
GREEN_DONE = [
    '|@str@I need to speak to the student in the green top about the|@str@exams.',
    '|@str@He gave me an answer to one of the questions on the first|@str@exam.',
]
PURPLE_DONE = [
    '|@str@I need to speak to the student in the purple shirt about|@str@the exams.',
    '|@str@She gave me an answer to one of the questions on the|@str@first exam.',
]
ORANGE_DONE = [
    '|@str@I need to speak to the student in the orange top about the|@str@exams.',
    '|@str@He gave me an answer to one of the questions on the first|@str@exam.',
]
GREEN_STARTED = [
    '|@str@I need to speak to the student in the green top about the|@str@exams.',
    '|@dbl@I have agreed to help the student in the green top.|',
    'He has lost his rock sample and thinks he may have dropped it around the digsite.|I need to find it and return it to him.',
]
READY = '|@dbl@I should talk to the Examiner to take my first exam. If I have forgotten anything I can always ask the students again.'
FIRST_EXAM_HEAD = [OPENING] + list(STAMP_DONE) + ['|@dbl@I need to study for my first exam. Perhaps the @dre@students @dbl@on the digsite can help?|']
PASSED_1 = '|@str@I have passed my first Earth Science exam.|'
PASSED_2 = '|@str@I have passed my second Earth Science exam.|'
PASSED_3 = '|@str@I have passed my third Earth Science exam.|'
SECOND_EXAM = [OPENING] + list(STAMP_DONE) + [PASSED_1, '|@dbl@I need to study for my second exam. Perhaps the three students on the digsite can help me again?|', GREEN_TODO, PURPLE_TODO, ORANGE_TODO]
THIRD_EXAM_OPAL = [OPENING] + list(STAMP_DONE) + [PASSED_1, PASSED_2, '|@dbl@I need to study for my third exam. Perhaps the three students on the digsite can help me again?|', '|@str@I need to speak to the student in the green top about the|@str@exams.', '|@str@I need to speak to the student in the purple shirt about|@str@the exams.', '|@dbl@I need to bring her an opal.', ORANGE_TODO]
IMPRESS_EXPERT = [OPENING] + list(STAMP_DONE) + [PASSED_1, PASSED_2, PASSED_3, '|@dbl@I need a find from the site to impress the @dre@archeological expert at the Exam Centre.', '|@dbl@I need to take the @dre@letter @dbl@to a workman near a @dre@winch.']
PERMIT = [OPENING] + list(STAMP_DONE) + [PASSED_1, PASSED_2, PASSED_3, '|@str@I need a find from the site to impress the archeological|@str@expert at the Exam Centre.', '|@str@I need to take the letter to a workman near a winch.|', '|@dbl@I need to @dre@investigate the dig shafts.', '|@dbl@I need to find a way to move the rocks blocking the way in the shaft. Perhaps someone else in these dig shafts can help me.']
POURED = list(PERMIT[0:-2]) + ['|@str@I need to investigate the dig shafts.', '|@str@I need to find a way to move the rocks blocking the way|@str@in the shaft. Perhaps someone else in these dig shafts|@str@can help me.|', '|@str@I covered the rocks in the cave with an explosive compound.|', '|@dbl@I need to ignite the explosive compound and blow up the rocks blocking the way.']
BLOWN = list(POURED[0:-1]) + ['|@str@I need to ignite the explosive compound and blow up the|@str@rocks blocking the way.|', '|@dbl@I should look for an interesting find in the secret room I found, and show it to @dre@the archeological expert@dbl@ at the Exam Centre.']
COMPLETE = list(BLOWN[0:-1]) + ['|@str@I should look for an interesting find in the secret room I|@str@found, and show it to the archeological expert|@str@at the Exam Centre.|', '|@str@The expert was impressed with the Zarosian tablet that I|@str@found, and I also discovered an ancient altar!', '|@red@QUEST COMPLETE!']
PAGES = [
    ['not started', NOT_STARTED, DIG_STAGE.NOT_STARTED],
    ['stamping without the letter', STAMPING_NO_LETTER, DIG_STAGE.STAMPING],
    ['stamping with the letter', STAMPING_LETTER_HELD, DIG_STAGE.STAMPING],
    ['first exam', list(FIRST_EXAM_HEAD) + [GREEN_TODO, PURPLE_TODO, ORANGE_TODO], DIG_STAGE.FIRST_EXAM],
    ['second exam', SECOND_EXAM, DIG_STAGE.SECOND_EXAM],
    ['third exam', THIRD_EXAM_OPAL, DIG_STAGE.THIRD_EXAM],
    ['impress the expert', IMPRESS_EXPERT, DIG_STAGE.IMPRESS_EXPERT],
    ['mineshaft permit', PERMIT, DIG_STAGE.MINESHAFT_PERMIT],
    ['compound poured', POURED, DIG_STAGE.POURED_COMPOUND],
    ['blockage removed', BLOWN, DIG_STAGE.REMOVED_BLOCKAGE],
    ['complete', COMPLETE, DIG_STAGE.COMPLETE],
]


def reads_page(page, stage):
    def body():
        expect((parse_digsite_journal(page).stage if parse_digsite_journal(page) is not None else None)).to_be(stage)
    return body


def _fn1():
    for name, page, stage in PAGES:
        test(f'reads {name}', reads_page(page, stage))

    def _fn3():
        expect(parse_digsite_journal([])).to_be_undefined()
        expect(parse_digsite_journal(['   '])).to_be_undefined()
    test('an empty page is unreadable rather than not started', _fn3)


describe('Digsite journal stages', _fn1)


def _fn4():
    def _fn5():
        flags = (parse_digsite_journal(list(FIRST_EXAM_HEAD) + [GREEN_TODO, PURPLE_TODO, ORANGE_TODO]).flags if parse_digsite_journal(list(FIRST_EXAM_HEAD) + [GREEN_TODO, PURPLE_TODO, ORANGE_TODO]) is not None else None)
        expect((('green-answered' in flags) if flags is not None else None)).to_be(False)
        expect((('purple-answered' in flags) if flags is not None else None)).to_be(False)
        expect((('orange-answered' in flags) if flags is not None else None)).to_be(False)
        expect((('exam-ready' in flags) if flags is not None else None)).to_be(False)
    test('no errand answered leaves every student flag clear', _fn5)

    def _fn6():
        flags = (parse_digsite_journal(list(FIRST_EXAM_HEAD) + list(GREEN_DONE) + [PURPLE_TODO, ORANGE_TODO]).flags if parse_digsite_journal(list(FIRST_EXAM_HEAD) + list(GREEN_DONE) + [PURPLE_TODO, ORANGE_TODO]) is not None else None)
        expect((('green-answered' in flags) if flags is not None else None)).to_be(True)
        expect((('orange-answered' in flags) if flags is not None else None)).to_be(False)
    test('the green student alone reads as green, not orange', _fn6)

    def _fn7():
        flags = (parse_digsite_journal(list(FIRST_EXAM_HEAD) + [GREEN_TODO, PURPLE_TODO] + list(ORANGE_DONE)).flags if parse_digsite_journal(list(FIRST_EXAM_HEAD) + [GREEN_TODO, PURPLE_TODO] + list(ORANGE_DONE)) is not None else None)
        expect((('orange-answered' in flags) if flags is not None else None)).to_be(True)
        expect((('green-answered' in flags) if flags is not None else None)).to_be(False)
    test('the orange student alone reads as orange, not green', _fn7)

    def _fn8():
        flags = (parse_digsite_journal(list(FIRST_EXAM_HEAD) + list(GREEN_STARTED) + [PURPLE_TODO, ORANGE_TODO]).flags if parse_digsite_journal(list(FIRST_EXAM_HEAD) + list(GREEN_STARTED) + [PURPLE_TODO, ORANGE_TODO]) is not None else None)
        expect((('green-answered' in flags) if flags is not None else None)).to_be(False)
    test('a started errand is not an answered one', _fn8)

    def _fn9():
        flags = (parse_digsite_journal(list(FIRST_EXAM_HEAD) + list(GREEN_DONE) + list(PURPLE_DONE) + list(ORANGE_DONE) + [READY]).flags if parse_digsite_journal(list(FIRST_EXAM_HEAD) + list(GREEN_DONE) + list(PURPLE_DONE) + list(ORANGE_DONE) + [READY]) is not None else None)
        expect((('green-answered' in flags) if flags is not None else None)).to_be(True)
        expect((('purple-answered' in flags) if flags is not None else None)).to_be(True)
        expect((('orange-answered' in flags) if flags is not None else None)).to_be(True)
        expect((('exam-ready' in flags) if flags is not None else None)).to_be(True)
    test('all three answered sets every flag and exam-ready', _fn9)

    def _fn10():
        flags = (parse_digsite_journal(list(FIRST_EXAM_HEAD) + list(GREEN_DONE) + list(PURPLE_DONE) + [ORANGE_TODO]).flags if parse_digsite_journal(list(FIRST_EXAM_HEAD) + list(GREEN_DONE) + list(PURPLE_DONE) + [ORANGE_TODO]) is not None else None)
        expect((('green-answered' in flags) if flags is not None else None)).to_be(True)
        expect((('purple-answered' in flags) if flags is not None else None)).to_be(True)
        expect((('orange-answered' in flags) if flags is not None else None)).to_be(False)
    test('the purple student\'s "She gave me an answer" is not the other two\'s line', _fn10)

    def _fn11():
        flags = (parse_digsite_journal(list(FIRST_EXAM_HEAD) + [GREEN_TODO] + list(PURPLE_DONE) + [ORANGE_TODO]).flags if parse_digsite_journal(list(FIRST_EXAM_HEAD) + [GREEN_TODO] + list(PURPLE_DONE) + [ORANGE_TODO]) is not None else None)
        expect((('purple-answered' in flags) if flags is not None else None)).to_be(True)
        expect((('green-answered' in flags) if flags is not None else None)).to_be(False)
        expect((('orange-answered' in flags) if flags is not None else None)).to_be(False)
    test('the purple student alone answers nobody else', _fn11)

    def _fn12():
        expect(('opal-wanted' in (parse_digsite_journal(THIRD_EXAM_OPAL).flags if parse_digsite_journal(THIRD_EXAM_OPAL) is not None else None))).to_be(True)
    test('the purple student wanting an opal is its own flag', _fn12)

    def _fn13():
        expect((parse_digsite_journal(BLOWN).stage if parse_digsite_journal(BLOWN) is not None else None)).to_be(DIG_STAGE.REMOVED_BLOCKAGE)
        expect((parse_digsite_journal(COMPLETE).stage if parse_digsite_journal(COMPLETE) is not None else None)).to_be(DIG_STAGE.COMPLETE)
    test('a struck-through earlier stage never wins over the live one', _fn13)


describe('Digsite journal flags', _fn4)
