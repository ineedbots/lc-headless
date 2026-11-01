"""Ported from rs2b0t's test/api/ai/quests/regicideJournal.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.quests.defs.regicide.journal import RG_FLAG, RG_STAGE, parse_regicide_journal

# Why: the journal is additive, so later stages must win over earlier struck lines.
COURIER = '@str@A courier has given me a message. I have been sent for|@str@ by King Lathas. I must go to his castle in Ardougne.||'
LATHAS = "@str@King Lathas has asked me to re-enter the underground @str@pass. Now that the Well of Voyage is repaired I'm to go @str@to the realm beyond.||"
SCOUTS = '@str@I have met a elvish scout party, who said I should go see @str@Lord Iorwerth@str@.||'
IORWERTH = "@str@Lord Iorwerth has offered the help of one of his @str@trackers@str@, who I'm to meet with at a camp Tyras recently @str@abandoned.||"
PENDANT = '@dbl@Lord Iorwerth has given me his pendant as proof that I am not the intruder that the @dre@tracker@dbl@ believes me to be.||'
NO_PROOF = "@dbl@The tracker didn't trust me and asked for some @dre@proof@dbl@ that I had been sent by @dre@Lord Iorwerth@dbl@.||"
SHOWN = '@str@After proving that I was not a bandit the tracker has @str@offered his help.||'
TRACKS = '@str@I have found some tracks leading off into the @str@undergrowth @str@but I am unable to follow them.||'
TRACKER2 = '@str@I asked the tracker about the tracks, he told me of signs to @str@look for and how to @str@pass@str@ the @str@dense woodland@str@.||'
SOLDIER = "@str@Pushing my way through the undergrowth I encountered @str@a soldier, one of King Tyras's men I guess.||"
CAMP = '@str@I have found the camp of King Tyras hidden in the woods @str@The king is in his tent and is well guarded.||'
BOOK = '@str@Lord Iorwerth@str@ has given me a @str@book@str@. It may be of help.||'
CHEMIST = '@dbl@The chemist read the book and told me I need to make Naphta, Quicklime and Brimstone.||'
CATAPULT = '@dbl@The catapult provided a great way to deliver my gift to King Tyras and no one is any the wiser it was me.||'
LETTER = '@dbl@Lord Iorwerth has given me a @dre@message@dbl@ to carry to @dre@King Lathas@dbl@.|'
ARIANWYN = "@dbl@When returning home I met an elf who showed me the truth of who's side I really was on.||"
DONE = "@str@I have told King Lathas about Tyras's death.||@red@QUEST COMPLETE!"


def up_to(*lines):
    return lines


def _fn1():
    # Why: Underground Pass opens its own scroll with the same sentence, one street away.
    def _fn2():
        upass = '@dbl@I can start this quest by speaking to @dre@King Lathas@dbl@ who is in @dre@East Ardougne@dbl@.'
        expect(parse_regicide_journal([upass])).to_be_undefined()
    test("Underground Pass's own not-started scroll is not a Regicide stage", _fn2)

    def _fn3():
        text = '@dbl@I can start this quest by speaking to @dre@King Lathas@dbl@ in @dre@Ardougne Castle@dbl@.||'
        expect((parse_regicide_journal([text]).stage if parse_regicide_journal([text]) is not None else None)).to_be(RG_STAGE.NOT_STARTED)
    test('the not-started scroll reads stage 0, before the messenger has been sent', _fn3)

    def _fn4():
        text = '@dre@King Lathas@dbl@ will send word when I can start this quest.|'
        expect((parse_regicide_journal([text]).stage if parse_regicide_journal([text]) is not None else None)).to_be(RG_STAGE.NOT_STARTED)
    test('the waiting-for-word scroll reads stage 0 too', _fn4)
    CASES = [
        ['the courier', up_to(COURIER), RG_STAGE.RECEIVED_MESSAGE],
        ['King Lathas', up_to(COURIER, LATHAS), RG_STAGE.SPOKEN_LATHAS],
        ['the scouts', up_to(COURIER, LATHAS, SCOUTS), RG_STAGE.SPOKEN_SCOUTS],
        ['Lord Iorwerth', up_to(COURIER, LATHAS, SCOUTS, IORWERTH), RG_STAGE.SPOKEN_IORWERTH],
        ['the tracker refusing', up_to(COURIER, LATHAS, SCOUTS, IORWERTH, NO_PROOF), RG_STAGE.SPOKEN_TRACKER],
        ['the pendant', up_to(COURIER, LATHAS, SCOUTS, IORWERTH, PENDANT), RG_STAGE.SPOKEN_TRACKER],
        ['the pendant shown', up_to(COURIER, LATHAS, SCOUTS, IORWERTH, SHOWN), RG_STAGE.SHOWN_PENDANT],
        ['the tracks', up_to(COURIER, LATHAS, SCOUTS, IORWERTH, SHOWN, TRACKS), RG_STAGE.FOUND_FOOTPRINTS],
        [
        'the tracker again',
        up_to(COURIER, LATHAS, SCOUTS, IORWERTH, SHOWN, TRACKS, TRACKER2),
        RG_STAGE.SPOKEN_TRACKER2,
    ],
        ['the soldier', up_to(COURIER, LATHAS, SHOWN, TRACKS, TRACKER2, SOLDIER), RG_STAGE.DEFEATED_GUARD],
        ['the camp', up_to(COURIER, LATHAS, SHOWN, TRACKS, TRACKER2, SOLDIER, CAMP), RG_STAGE.ENTERED_CAMP],
        [
        'the book',
        up_to(COURIER, LATHAS, SHOWN, TRACKS, TRACKER2, SOLDIER, CAMP, BOOK),
        RG_STAGE.SPOKEN_IORWERTH2,
    ],
        ['the catapult', up_to(COURIER, LATHAS, CAMP, BOOK, CATAPULT), RG_STAGE.KILLED_TYRAS],
        ['the letter', up_to(COURIER, LATHAS, CAMP, BOOK, CATAPULT, LETTER), RG_STAGE.REPORTED_IORWERTH],
        ['Arianwyn', up_to(COURIER, LATHAS, CAMP, BOOK, CATAPULT, LETTER, ARIANWYN), RG_STAGE.SPOKEN_ARIANWYN],
        ['the reward', up_to(DONE), RG_STAGE.COMPLETE],
    ]

    def _fn5(_what, lines, stage):
        expect((parse_regicide_journal(lines).stage if parse_regicide_journal(lines) is not None else None)).to_be(stage)
    test_each(CASES)('%s reads its own stage', _fn5)

    def _fn6():
        progress = parse_regicide_journal(up_to(COURIER, LATHAS, SCOUTS, IORWERTH, PENDANT))
        expect((RG_FLAG.PENDANT in (progress.flags if progress is not None else None))).to_be(True)
    test('the pendant line is carried as a flag, so a handed-over pendant is still remembered', _fn6)

    def _fn7():
        progress = parse_regicide_journal(up_to(COURIER, LATHAS, SCOUTS, IORWERTH, NO_PROOF))
        expect((RG_FLAG.PENDANT in (progress.flags if progress is not None else None))).to_be(False)
    test('a tracker who refused leaves no pendant flag', _fn7)

    def _fn8():
        progress = parse_regicide_journal(up_to(COURIER, LATHAS, CAMP, BOOK, CHEMIST))
        expect((progress.stage if progress is not None else None)).to_be(RG_STAGE.SPOKEN_IORWERTH2)
        expect((RG_FLAG.CHEMIST in (progress.flags if progress is not None else None))).to_be(True)
    test('the chemist line is carried as a flag', _fn8)


describe('parseRegicideJournal', _fn1)

