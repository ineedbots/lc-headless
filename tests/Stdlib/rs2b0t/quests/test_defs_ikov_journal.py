"""Ported from rs2b0t's test/api/ai/quests/defs/ikov-journal.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.quests.defs.ikov.journal import IKOV_STAGE, parse_ikov_journal

NOT_STARTED = [
    '@dbl@I can start this quest at the @dre@Flying Horse Inn@dbl@ in @dre@Ardougne@dbl@ by speaking to @dbl@Lucien||',
    '@dbl@I must have:|',
    '@dre@Level 42 thieving|',
    '@dre@Level 40 ranged|',
]
STARTED = ['@dre@Lucien@dbl@ has asked me to retrieve the @dre@Staff of Armadyl@dbl@ from the @dre@Temple of Ikov@dbl@.' + ' The entrance is near @dre@Hemenster@dbl@. He has given me a @dre@pendant@dbl@ so I can enter the @dre@chamber of fear.']
PREFIX = [
    '@str@Lucien has asked me to retrieve the Staff of Armadyl from|',
    '@str@the Temple of Ikov. The entrance is near Hemenster. He has|',
    '@str@given me a pendant so I can enter the chamber of fear.|',
]
TRAP = list(PREFIX) + ['@str@I have entered the chamber of fear. I found a trap on a|', '@str@lever and have disabled it. I pulled the lever.|', '@str@I have found some boots of lightness. I have entered the|', '@str@Ice Cavern and found some arrows made of ice.']
WARRIOR = list(PREFIX) + ['@str@I have entered the chamber of fear. I found a trap on a|', '@str@lever and have disabled it. I pulled the lever; I went into|', '@str@another chamber and was attacked by a Fire Warrior! I|', '@str@killed it using arrows made of ice and my trusty bow.|']
SPOKEN_WINELDA = list(WARRIOR) + ['|@dbl@My path is blocked by lava. @dre@Winelda@dbl@ will teleport me across if I first get her @dre@twenty limpwurt roots']
PAID_WINELDA = list(WARRIOR) + ['|@str@My path was blocked by lava. Winelda teleported me across|', '@str@after I got her twenty limpwurt roots.|']
HELPING_ARMADYL = list(PAID_WINELDA) + ['|@dbl@I agreed to help the @dre@Guardians of Armadyl@dbl@, I will kill @dre@Lucien@dbl@.' + ' The guardians gave me a @dre@pendant@dbl@ that I will need to enable me to attack him']
COMPLETE = list(PAID_WINELDA) + ['|@str@I agreed to help the Guardians of Armadyl. I killed|', '@str@Lucien and banished him from this plane!|', '|@dre@QUEST COMPLETE!']


def _reads(lines, stage):
    def check():
        expect(parse_ikov_journal(lines)).to_be(stage)
    return check


def _fn1():
    cases = [
        ['not started', NOT_STARTED, IKOV_STAGE.NOT_STARTED],
        ['started', STARTED, IKOV_STAGE.STARTED],
        ['trap disarmed and lever pulled', TRAP, IKOV_STAGE.PULLED_LEVER],
        ['Fire Warrior down', WARRIOR, IKOV_STAGE.KILLED_WARRIOR],
        ['Winelda wants roots', SPOKEN_WINELDA, IKOV_STAGE.SPOKEN_WINELDA],
        ['Winelda paid', PAID_WINELDA, IKOV_STAGE.PAID_WINELDA],
        ['helping the guardians', HELPING_ARMADYL, IKOV_STAGE.HELPING_ARMADYL],
        ['complete', COMPLETE, IKOV_STAGE.COMPLETE],
    ]
    for label, lines, stage in cases:
        test(f'reads {label}', _reads(lines, stage))

    # Why: every earlier line stays on the page struck through, so a later page still contains the earlier needles.
    def _fn3():
        expect(parse_ikov_journal(WARRIOR)).to_be_greater_than(parse_ikov_journal(TRAP))
        expect(parse_ikov_journal(PAID_WINELDA)).to_be_greater_than(parse_ikov_journal(SPOKEN_WINELDA))
        expect(parse_ikov_journal(HELPING_ARMADYL)).to_be_greater_than(parse_ikov_journal(PAID_WINELDA))
    test('a later page outranks the struck-through lines it still carries', _fn3)

    def _fn4():
        expect(parse_ikov_journal(TRAP)).to_be(IKOV_STAGE.PULLED_LEVER)
    test('stage 20 and stage 30 render one page, so both read as PULLED_LEVER', _fn4)

    def _fn5():
        expect(parse_ikov_journal([])).to_be_undefined()
        expect(parse_ikov_journal('')).to_be_undefined()
    test('an empty read is not a stage', _fn5)

    def _fn6():
        expect(parse_ikov_journal(['@dbl@I can start this quest by speaking to @dre@Reldo@dbl@.'])).to_be_undefined()
    test('a page of unrelated text is not a stage', _fn6)

    # Why: colour tags and line breaks both normalise to one space, so a needle reads the same wherever they fall.
    def _fn7():
        expect(parse_ikov_journal(['@str@I killed it using @dre@arrows made of ice@dbl@ and my bow.'])).to_be(IKOV_STAGE.KILLED_WARRIOR)
        expect(parse_ikov_journal(['@str@I killed it using arrows|@str@made of ice and my bow.'])).to_be(IKOV_STAGE.KILLED_WARRIOR)
    test('needles survive the colour tags and breaks inside them', _fn7)


describe('parseIkovJournal', _fn1)
