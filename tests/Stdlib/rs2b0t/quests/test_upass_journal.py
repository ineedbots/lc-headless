"""Ported from rs2b0t's test/api/ai/quests/upassJournal.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.quests.defs.upass.journal import UP_FLAG, UP_STAGE, parse_upass_journal

# Why: lines are verbatim from `upass_journal.rs2`, so the parser is tested against what the engine renders.
# Why: the journal is additive, every stage keeps the earlier lines, so each case builds on the last.
KOFTIK_DONE = '@str@King Lathas asked me to meet a tracker named Koftik. He|@str@can be found by a cave entrance in far West Ardougne.|'
MET_KOFTIK = '|@str@I have met Koftik. He fears these caves, but he agreed to|@str@help. He said to meet him at the bridge inside the cave.|'
AT_BRIDGE = "|@str@I have met Koftik at an underground river where there is a|@str@drawbridge. But it's held up by ropes and pulleys. Koftik|@str@found a damp cloth amongst the charred remains of some|@str@arrows.|"
CROSSED = '|@str@I managed to cross the bridge by shooting the stay rope|@str@with a burning arrow. I guess the only way now is onwards.|'
ORBS = '|@str@After destroying four orbs I was able to climb down a well.|'
WATCHED = "@str@Something is watching me, I'm starting to understand|@str@Koftik's fear.|"
SECOND_WELL = "|@str@I have found yet another well. Upon it an inscription says|@str@that I must 'feed' it three crests and a creature's remains.|"
DOUBLE_DOORS = "|@str@After 'feeding' crests and a horn to the well I was able to|@str@pass through the double doors that lead to a huge cavern.|"
KOFTIK_MAD = '|@str@I have seen Koftik again, I fear for his sanity. In his raving|@str@he did mention dwarfs that live in the south of this cavern.|'
DWARVES = '|@str@I have met some dwarfs living here, the group leader said|@str@to seek a witch living on a platform above.|'
STOLE_DOLL = '|@str@After distracting the witch I was able to steal a|@str@doll and a book. The book may give some clues.|'


def stage_of(text):
    return (parse_upass_journal(text).stage if parse_upass_journal(text) is not None else None)


def flags_of(text):
    return ((parse_upass_journal(text).flags if parse_upass_journal(text) is not None else None) if (parse_upass_journal(text).flags if parse_upass_journal(text) is not None else None) is not None else set())


def _fn1():
    def _fn2():
        text = '@dbl@I can start this quest by speaking to @dre@King Lathas@dbl@ who is in @dre@East Ardougne@dbl@.'
        expect(stage_of(text)).to_be(UP_STAGE.NOT_STARTED)
        expect((UP_FLAG.STARTED in flags_of(text))).to_be(False)
    test('not started, and not yet sent to Koftik', _fn2)

    def _fn3():
        text = '@dbl@King Lathas asked me to meet a tracker named @dre@Koftik@dbl@. He can be found by a @dre@cave entrance@dbl@ in far @dre@West Ardougne.'
        expect(stage_of(text)).to_be(UP_STAGE.NOT_STARTED)
        expect((UP_FLAG.STARTED in flags_of(text))).to_be(True)
    test('started is a flag on stage zero, not a stage of its own', _fn3)

    def _fn4():
        text = KOFTIK_DONE + '|@dbl@I have met Koftik. He fears these caves, but he agreed to help. He said to meet him at the @dre@bridge@dbl@ inside the cave.|'
        expect(stage_of(text)).to_be(UP_STAGE.SPOKEN_KOFTIK)
    test('spoken to Koftik', _fn4)

    def _fn5():
        text = KOFTIK_DONE + MET_KOFTIK + "|@dbl@I have met Koftik at an underground river where there is a drawbridge. But it's held up by @dre@ropes@dbl@ and pulleys. Koftik found a damp cloth amongst the charred remains of some arrows."
        expect(stage_of(text)).to_be(UP_STAGE.SPOKEN_KOFTIK)
        expect((UP_FLAG.ARROW_PARTS in flags_of(text))).to_be(True)
    test('the damp cloth shows up as the arrow-parts flag', _fn5)

    def _fn6():
        text = KOFTIK_DONE + MET_KOFTIK + AT_BRIDGE + CROSSED + '|@dbl@I must work my way deeper into these caverns.|'
        expect(stage_of(text)).to_be(UP_STAGE.PASSED_BRIDGE)
    test('crossed the bridge', _fn6)

    def _fn7():
        text = KOFTIK_DONE + MET_KOFTIK + AT_BRIDGE + CROSSED + ORBS + "@dbl@Something is watching me, I'm starting to understand Koftik's fear.|"
        expect(stage_of(text)).to_be(UP_STAGE.ENTERED_SECOND_AREA)
    test('down the well into the second area', _fn7)

    def _fn8():
        text = KOFTIK_DONE + MET_KOFTIK + AT_BRIDGE + CROSSED + ORBS + WATCHED + "|@dbl@I have found yet another @dre@well@dbl@. Upon it an inscription says that I must 'feed' it @dre@three crests@dbl@ and a @dre@creature's remains@dbl@."
        expect(stage_of(text)).to_be(UP_STAGE.KILLED_UNICORN)
        expect((UP_FLAG.WELL_INSCRIPTION in flags_of(text))).to_be(True)
    test('unicorn crushed', _fn8)

    def _fn9():
        text = KOFTIK_DONE + MET_KOFTIK + AT_BRIDGE + CROSSED + ORBS + WATCHED + SECOND_WELL + "|@dbl@After 'feeding' crests and a horn to the well I was able to pass through the double doors that lead to a huge cavern.|"
        expect(stage_of(text)).to_be(UP_STAGE.ENTERED_MAIN_AREA)
    test('through the double doors', _fn9)

    def _fn10():
        text = KOFTIK_DONE + MET_KOFTIK + AT_BRIDGE + CROSSED + ORBS + WATCHED + SECOND_WELL + DOUBLE_DOORS + KOFTIK_MAD + "|@dbl@I have met some dwarfs living here, the group leader said to seek Iban's advisor: a @dre@witch@dbl@ living on a platform above."
        expect(stage_of(text)).to_be(UP_STAGE.SPOKEN_NILHOOF)
        expect((UP_FLAG.KOFTIK_INSANE in flags_of(text))).to_be(True)
    test('spoken to Nilhoof', _fn10)

    def _fn11():
        text = KOFTIK_DONE + MET_KOFTIK + AT_BRIDGE + CROSSED + ORBS + WATCHED + SECOND_WELL + DOUBLE_DOORS + KOFTIK_MAD + DWARVES + '|@dbl@After distracting the witch with her cat I was able to steal a doll and a book. The book may give some clues.|'
        expect(stage_of(text)).to_be(UP_STAGE.FOUND_DOLL)
    test('doll stolen from the chest', _fn11)

    def _fn12():
        text = '@str@I have informed King Lathas that I have destroyed Iban.|@str@He told me that he would send magi to restore the well.||@dre@QUEST COMPLETE!'
        expect(stage_of(text)).to_be(UP_STAGE.COMPLETE)
    test('quest complete', _fn12)

    def _fn13():
        expect(parse_upass_journal('@dbl@Some other quest entirely.')).to_be_undefined()
    test('unrecognised text is undefined, never a guessed stage', _fn13)


describe('parseUpassJournal stages', _fn1)


def _fn14():
    base = KOFTIK_DONE + MET_KOFTIK + AT_BRIDGE + CROSSED + ORBS + WATCHED + SECOND_WELL + DOUBLE_DOORS + KOFTIK_MAD + DWARVES + STOLE_DOLL

    def _fn15():
        text = base + "|@dbl@Having burned Iban's tomb, I was able to collect some of his ashes. I rubbed some of the ash into the doll.|" + '|@dbl@I killed the huge blood-drinking spider, Kalrag. As it died I managed to smear some of its fluids onto the doll.|'
        flags = flags_of(text)
        expect((UP_FLAG.ASHES_ON_DOLL in flags)).to_be(True)
        expect((UP_FLAG.BLOOD_ON_DOLL in flags)).to_be(True)
        expect((UP_FLAG.SHADOW_ON_DOLL in flags)).to_be(False)
        expect((UP_FLAG.DOVE_ON_DOLL in flags)).to_be(False)
    test('each element sets its own flag', _fn15)

    def _fn16():
        text = base + "|@dbl@Having burned Iban's tomb, I was able to collect some of his ashes. I rubbed some of the ash into the doll.|" + '|@dbl@I killed the huge blood-drinking spider, Kalrag. As it died I managed to smear some of its fluids onto the doll.|' + "|@dbl@Collecting Shadow was tough, but after defeating 3 demons I was able to open a chest. The doll now has Iban's shadow.|" + "|@dbl@After searching some cages I found some dove bones. Crushing these over the doll imbued it with Iban's conscience|" + '|@dbl@I have completed the doll, all that remains is to face @dre@Iban@dbl@.|'
        flags = flags_of(text)
        expect((UP_FLAG.DOLL_COMPLETE in flags)).to_be(True)
        expect((UP_FLAG.SHADOW_ON_DOLL in flags)).to_be(True)
        expect((UP_FLAG.DOVE_ON_DOLL in flags)).to_be(True)
    test('a finished doll is its own flag', _fn16)


describe('parseUpassJournal doll elements', _fn14)

