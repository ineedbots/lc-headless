"""rs2b0t's test/api/ai/quests/defs/druidspirit-journal.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs.record import Record
from rs2004.quests.defs.druidspirit.areas import NS_STAGE
from rs2004.quests.defs.druidspirit.journal import NS_FLAG, parse_druid_journal

OPENING = "@str@After talking to Drezel in the temple of Saradomin I've|@str@agreed to look for a Druid called Filliman Tarlock.|"
SPIRIT_FOUND = "@str@I've found a spirit in the swamp which I think might be|@str@Filliman Tarlock.|"
GHOSTSPEAK = "@str@I've communicated with Filliman using the amulet of|@str@ghostspeak.|"
CONVINCED = "@str@I managed to convince Filliman that he's a ghost.|@str@Filliman is looking for his journal to help him plan what his|@str@next step is.|"
GAVE_JOURNAL = "@str@I've given Filliman his journal. I wonder what he plans to do|@str@now?|"
AGREED = "@str@I've agreed to help Filliman become a nature spirit.|@str@I need to find 'something from nature', 'something of|@str@faith' and 'something of the spirit-to-become freely given'.|"
GOT_SPELL = "@str@Filliman gave me a 'bloom' spell to cast in the swamp.|@str@With the bloom spell I can collect 'Something of nature.'|"
BLESSED = "@str@I've been blessed at the temple by Drezel.|"
CAST = "@str@I've cast the bloom spell in the swamp.|"
FUNGI = '@str@I collected a Mort Myre Fungi.|'
RITUAL = '@str@I managed to get all the required items that Filliman|@str@asked for.|' + '@str@He says that he can cast the spell now which will transform|@str@him into a Nature Spirit.|'
BEFORE_RITUAL = OPENING + SPIRIT_FOUND + GHOSTSPEAK + CONVINCED + GAVE_JOURNAL + AGREED + GOT_SPELL + BLESSED + CAST + FUNGI
ENTERED = BEFORE_RITUAL + '@str@I mannaged to get all the required items that Filliman|@str@asked for.|' + '@str@He says that he can cast the spell now which will transform|@str@him into a Nature Spirit.|' + '@str@I entered Fillimans grotto as he asked me to.|'
TRANSFORMED = ENTERED + '@str@Filliman has turned into a nature spirit, it was an impressive|@str@transformation!|' + '@str@Filliman says he can help me to defeat the ghasts.|'
SICKLE_BLESSED = TRANSFORMED + '@str@Filliman has blessed the silver sickle for me.|'
SICKLE_CAST = SICKLE_BLESSED + '@str@I cast the bloom spell in the swamp.|'
HARVESTED = SICKLE_CAST + '@str@I collected some bloomed items from the swamp.|'
POUCH = HARVESTED + '@str@I collected some bloomed items from the swamp and put|@str@them into a druid pouch.|'
GHAST1 = POUCH + '@str@The druid pouch made a ghast appear which I attacked and|@str@killed.|'


def stage_of(text):
    return (parse_druid_journal(text).stage if parse_druid_journal(text) is not None else None)


def _fn1():
    def _fn2():
        expect(stage_of('@dbl@I can start this quest by speaking to @dre@Drezel@dbl@ in the|@dre@Mausoleum@dbl@ beneath @dre@Paterdomus@dbl@.')).to_be(NS_STAGE.NOT_STARTED)
    test('not started', _fn2)

    def _fn3():
        expect(stage_of(OPENING + '@dbl@I need to look for @dre@Filliman Tarlock@dbl@ in the @dre@Swamps@dbl@ of Mort|Myre.')).to_be(NS_STAGE.STARTED)
    test('started', _fn3)

    def _fn4():
        expect(stage_of(OPENING + SPIRIT_FOUND + "@dbl@I can't really communicate with this @dre@spirit@dbl@.")).to_be(NS_STAGE.FAILED_TALK)
    test('failed talk', _fn4)

    def _fn5():
        expect(stage_of(OPENING + SPIRIT_FOUND + GHOSTSPEAK + "@dbl@I think I need to convince this poor fellow @dre@Tarlock@dbl@ that he's|actually @dre@dead@dbl@!")).to_be(NS_STAGE.SPOKEN_FILLIMAN)
    test('spoken to Filliman', _fn5)

    def _fn6():
        expect(stage_of(OPENING + SPIRIT_FOUND + GHOSTSPEAK + CONVINCED + '@dbl@Perhaps I should try to help @dre@Filliman@dbl@ to find his @dre@journal@dbl@?')).to_be(NS_STAGE.SHOWN_MIRROR)
    test('shown the mirror', _fn6)

    def _fn7():
        expect(stage_of(OPENING + SPIRIT_FOUND + GHOSTSPEAK + CONVINCED + GAVE_JOURNAL + '@dre@Filliman@dbl@ might need @dre@my help@dbl@ with his @dre@plan@dbl@.')).to_be(NS_STAGE.GIVEN_JOURNAL)
    test('given the journal', _fn7)

    def _fn8():
        expect(stage_of(OPENING + SPIRIT_FOUND + GHOSTSPEAK + CONVINCED + GAVE_JOURNAL + AGREED + "@dre@Filliman@dbl@ gave me a '@dre@bloom'@dbl@ spell but I need to be @dre@blessed@dbl@ at|the @dre@temple@dbl@ before I can cast it.")).to_be(NS_STAGE.RECEIVED_SPELL)
    test('holds the bloom spell, not yet blessed', _fn8)

    def _fn9():
        expect(stage_of(OPENING + SPIRIT_FOUND + GHOSTSPEAK + CONVINCED + GAVE_JOURNAL + AGREED + GOT_SPELL + BLESSED + "@dbl@I need to collect '@dre@something of nature.@dbl@'")).to_be(NS_STAGE.BLESSED)
    test('blessed', _fn9)

    def _fn10():
        expect(stage_of(OPENING + SPIRIT_FOUND + GHOSTSPEAK + CONVINCED + GAVE_JOURNAL + AGREED + GOT_SPELL + BLESSED + CAST + "@dbl@I need to collect '@dre@something of nature.@dbl@'")).to_be(NS_STAGE.CASTED_SPELL)
    test('cast the scroll', _fn10)

    def _fn11():
        progress = parse_druid_journal(BEFORE_RITUAL + '@dbl@I have a @dre@Mort Myre Fungi@dbl@, I hope this is what @dre@Filliman|@dbl@wanted.|' + "@dbl@I need to find '@dre@Something with faith@dbl@'|" + "@dbl@I need to find :|'@dre@Something of the spirit-to-become freely given.@dbl@'")
        expect((progress.stage if progress is not None else None)).to_be(NS_STAGE.PICKED_FUNGI)
        expect((NS_FLAG.NATURE in (progress.flags if progress is not None else None))).to_be(False)
        expect((NS_FLAG.SPIRIT in (progress.flags if progress is not None else None))).to_be(False)
    test('holds the fungus, no stones fed', _fn11)

    def _fn12():
        progress = parse_druid_journal(BEFORE_RITUAL + "@str@The Mort Myre Fungi was absorbed into the nature stone|@str@I think I have collected 'something of nature.'|" + "@dbl@I need to find '@dre@Something with faith@dbl@'|" + "@str@The spell scroll was absorbed into the spirit stone I think I|@str@have collected 'something of spirit-to-become freely|@str@given.'")
        expect((progress.stage if progress is not None else None)).to_be(NS_STAGE.PICKED_FUNGI)
        expect((NS_FLAG.NATURE in (progress.flags if progress is not None else None))).to_be(True)
        expect((NS_FLAG.SPIRIT in (progress.flags if progress is not None else None))).to_be(True)
    test('both stones fed shows as two flags at the same stage', _fn12)

    def _fn13():
        progress = parse_druid_journal(BEFORE_RITUAL + RITUAL + '@dre@Filliman@dbl@ asked me to meet him in his @dre@grotto@dbl@.')
        expect((progress.stage if progress is not None else None)).to_be(NS_STAGE.PERFORMED_RITUAL)
        expect((NS_FLAG.NATURE in (progress.flags if progress is not None else None))).to_be(True)
        expect((NS_FLAG.SPIRIT in (progress.flags if progress is not None else None))).to_be(True)
    test('ritual performed', _fn13)

    def _fn14():
        expect(stage_of(ENTERED + '@dre@Filliman@dbl@ asked me to meet him in his @dre@grotto@dbl@.')).to_be(NS_STAGE.ENTERED_GROTTO)
    test('entered the grotto', _fn14)

    def _fn15():
        expect(stage_of(TRANSFORMED + '@dre@Filliman@dbl@ asked me to get a @dre@silver sickle@dbl@.')).to_be(NS_STAGE.FULL_TRANSFORM)
    test('transformed', _fn15)

    def _fn16():
        expect(stage_of(SICKLE_BLESSED + '@dbl@I need to use the @dre@sickle@dbl@ to make the swamp bloom.')).to_be(NS_STAGE.BLESSED_SICKLE)
    test('sickle blessed', _fn16)

    def _fn17():
        expect(stage_of(SICKLE_CAST + "@dre@Filliman@dbl@ said something about collecting '@dre@natures bounty@dbl@'.")).to_be(NS_STAGE.CASTED_SICKLE_BLOOM)
    test('bloomed with the sickle', _fn17)

    def _fn18():
        expect(stage_of(HARVESTED + "@dre@Filliman@dbl@ said something about a '@dre@druid pouch@dbl@'.")).to_be(NS_STAGE.PICKED_SICKLE)
    test('harvested', _fn18)

    def _fn19():
        expect(stage_of(POUCH + '@dre@Filliman@dbl@ asked me to kill @dre@three ghasts@dbl@.')).to_be(NS_STAGE.ADDED_POUCH)
    test('pouch filled', _fn19)

    def _fn20():
        expect(stage_of(GHAST1 + "@dbl@I've killed @dre@one@dbl@ ghast, I have another @dre@two@dbl@ to kill.")).to_be(NS_STAGE.KILLED_GHAST1)
    test('one ghast down', _fn20)

    def _fn21():
        expect(stage_of(GHAST1 + "@str@I've killed two ghasts now.|@dbl@I've killed @dre@two@dbl@ ghasts, I have another @dre@one@dbl@ to kill.")).to_be(NS_STAGE.KILLED_GHAST2)
    test('two ghasts down', _fn21)

    def _fn22():
        expect(stage_of(GHAST1 + "@str@I've killed two ghasts now.|@str@I've killed three ghasts now.|" + "@dbl@I should tell @dre@Filliman@dbl@ that I've killed the @dre@three ghasts@dbl@.")).to_be(NS_STAGE.KILLED_GHAST3)
    test('three ghasts down', _fn22)

    def _fn23():
        expect(stage_of('@str@Drezel, a priest of Saradomin, asked me to look for the|@str@druid Filliman Tarlock.|@red@QUEST COMPLETE!')).to_be(NS_STAGE.COMPLETE)
    test('complete', _fn23)

    def _fn24():
        expect(parse_druid_journal('')).to_be_undefined()
    test('an unreadable page yields nothing rather than a wrong stage', _fn24)

    def _fn25():
        expect(parse_druid_journal([OPENING, '@dbl@I need to look for @dre@Filliman Tarlock@dbl@ in the @dre@Swamps@dbl@ of Mort|Myre.'])).to_equal(Record({'stage': NS_STAGE.STARTED, 'flags': set()}))
    test('journal lines arrive as an array too', _fn25)


describe('nature spirit journal', _fn1)
