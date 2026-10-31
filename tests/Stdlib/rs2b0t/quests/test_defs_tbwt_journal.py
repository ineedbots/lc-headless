"""rs2b0t's test/api/ai/quests/defs/tbwt-journal.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.quests.defs.tbwt.areas import TB_LUBUFU, TB_TAMAYU, TB_TINSAY
from rs2004.quests.defs.tbwt.journal import TB_FLAG, parse_tbwt_journal

HEADER = [
    '@str@I have found the three sons of Timfraku:|',
    '@str@Tamayu|@str@Tinsay|@str@Tiadeche|',
    '@dbl@I need to convince them to return to the village.||',
]
TIADECHE_WAITING = ['@dre@Tiadeche:|', '@dbl@He will only return to the village once he has caught a|@dre@Karambwan@dbl@.||']
TIADECHE_MANUAL = [
    '@dre@Tiadeche:|',
    '@str@He has successfully caught a Karambwan.|',
    '@dbl@I must take a @dre@Karambwan vessel@dbl@ to @dre@Tinsay@dbl@ and retrieve @dre@crafting instructions@dbl@ for @dre@Tiadeche@dbl@.||',
]
LUBUFU_BASE = [
    '@dre@Lubufu:|',
    '@str@Lubufu is a crochety old fisherman just south of|@str@Brimhaven.|',
    '@str@He appears to have a local monopoly over the sale of|@str@Karambwan.||',
]


def value(flags, name):
    flag = ([f for f in list(flags) if f.startswith(f'{name}:')] or [None])[0]
    return int(flag.split(':')[1])


def _fn1():
    def _fn2():
        expect(parse_tbwt_journal([])).to_be_undefined()
        expect(parse_tbwt_journal(['@dbl@I can start this quest by speaking to @dre@Timfraku@dbl@.'])).to_be_undefined()
    test('a page that never rendered is not a quest at zero', _fn2)

    def _fn3():
        flags = parse_tbwt_journal(list(HEADER) + list(TIADECHE_WAITING) + ['@dre@Tinsay:|', '@dbl@He requires @dre@banana in Karamja rum@dbl@ to repair the tribal statue||', '@dre@Tamayu:|', '@dbl@He will only return to the village once he has slain @dre@Shaikahan@dbl@.||'] + list(LUBUFU_BASE) + ['@str@Lubufu has difficulty collecting bait, due to his age. I have|@str@offered to help collect bait. Lubufu has accepted.|', '@dbl@I need to give Lubufu 20 Karambwanji.||'])
        expect(value(flags, TB_FLAG.TINSAY)).to_be(TB_TINSAY.FETCH_RUM)
        expect(value(flags, TB_FLAG.TAMAYU)).to_be(TB_TAMAYU.SLAY_SHAIKAHAN)
        expect(value(flags, TB_FLAG.LUBUFU)).to_be(TB_LUBUFU.FETCH_KARAMBWANJI)
    test('the opening brothers page reads every sub-stage at once', _fn3)

    # Why: "Nothing of interest." is the intro line for three different brothers, so a marker only counts inside its own heading.
    def _fn4():
        flags = parse_tbwt_journal(list(HEADER) + list(TIADECHE_WAITING) + ['@dre@Tinsay:|', 'Nothing of interest.||', '@dre@Tamayu:|', '@dbl@He will only return to the village once he has slain @dre@Shaikahan@dbl@.||'])
        expect(value(flags, TB_FLAG.TINSAY)).to_be(TB_TINSAY.INTRO)
        expect(value(flags, TB_FLAG.TAMAYU)).to_be(TB_TAMAYU.SLAY_SHAIKAHAN)
        expect(value(flags, TB_FLAG.LUBUFU)).to_be(TB_LUBUFU.UNKNOWN)
    test('an intro line is scoped to the brother whose heading it sits under', _fn4)

    def _fn5():
        def page(extra):
            return parse_tbwt_journal(list(HEADER) + list(TIADECHE_WAITING) + ['@dre@Tinsay:|'] + list(extra))
        given = '@str@I have given him sliced banana in Karamja rum.|'
        sandwich = '@str@I have given him a seaweed in monkey skin sandwich.|'
        expect(value(page([given]), TB_FLAG.TINSAY)).to_be(TB_TINSAY.GIVEN_RUM)
        expect(value(page([
        given,
        '@dbl@He requires a @dre@seaweed in monkey skin sandwich to repair @dre@the tribal statue with.||',
    ]), TB_FLAG.TINSAY)).to_be(TB_TINSAY.FETCH_SANDWICH)
        expect(value(page([given, sandwich]), TB_FLAG.TINSAY)).to_be(TB_TINSAY.GIVEN_SANDWICH)
        expect(value(page([
        given,
        sandwich,
        '@dbl@He requires @dre@burnt Jogre bones marinated in Karambwanji to ... repair the tribal statue with?||',
    ]), TB_FLAG.TINSAY)).to_be(TB_TINSAY.FETCH_BONES)
        expect(value(page([given, sandwich, '@str@I have given him a burnt Jogre bones marinated in|@str@Karambwanji paste.||']), TB_FLAG.TINSAY)).to_be(TB_TINSAY.COMPLETE)
    test('later Tinsay stages re-print the earlier lines and still read as the latest', _fn5)

    def _fn6():
        flags = parse_tbwt_journal(list(HEADER) + list(TIADECHE_MANUAL) + ['@dre@Tamayu:|', '@dbl@He will only return to the village once he has slain @dre@Shaikahan@dbl@.|', '@dbl@He appears to be having difficulty in the hunt.||', "@str@I have increased his agility to match the Shaikahan's.|", '@str@I have give him a stronger and Karambwan poisoned spear.||'])
        expect(value(flags, TB_FLAG.TAMAYU)).to_be(TB_TAMAYU.WATCHED_CUTSCENE)
        expect((TB_FLAG.AGILITY in flags)).to_be(True)
        expect((TB_FLAG.SPEAR in flags)).to_be(True)
    test("Tamayu's two hunt preconditions are journal-visible", _fn6)

    def _fn7():
        flags = parse_tbwt_journal(list(HEADER) + list(TIADECHE_WAITING) + ['@dre@Tamayu:|', '@dbl@He will only return to the village once he has slain @dre@Shaikahan@dbl@.|', '@dbl@He appears to be having difficulty in the hunt.||'])
        expect(value(flags, TB_FLAG.TAMAYU)).to_be(TB_TAMAYU.WATCHED_CUTSCENE)
        expect((TB_FLAG.AGILITY in flags)).to_be(False)
        expect((TB_FLAG.SPEAR in flags)).to_be(False)
    test('a watched hunt with neither gift given carries neither flag', _fn7)

    def _fn8():
        flags = parse_tbwt_journal(list(HEADER) + list(TIADECHE_MANUAL) + ['@str@Tamayu:|', '@str@Tamayu has slain the Shaikahan!||'])
        expect(value(flags, TB_FLAG.TAMAYU)).to_be(TB_TAMAYU.COMPLETE)
        expect((TB_FLAG.AGILITY in flags)).to_be(True)
        expect((TB_FLAG.SPEAR in flags)).to_be(True)
    test('a slain Shaikahan implies both gifts, whatever the page states', _fn8)

    def _fn9():
        def page(extra):
            return parse_tbwt_journal(list(HEADER) + list(LUBUFU_BASE) + list(extra))
        expect(value(page([]), TB_FLAG.LUBUFU)).to_be(TB_LUBUFU.INITIAL_OPS)
        expect(value(page(['@dbl@Lubufu has difficulty collecting bait, due to his age. I have offered to help collect bait.||']), TB_FLAG.LUBUFU)).to_be(TB_LUBUFU.OFFERED_TO_HELP)
        expect(value(page(['@str@I have given Lubufu 20 Karambwanji.||']), TB_FLAG.LUBUFU)).to_be(TB_LUBUFU.GIVEN_KARAMBWANJI)
        expect(value(page(['@str@I have given Lubufu 20 Karambwanji.||', '@dbl@Lubufu has offered to train me as his apprentice.||']), TB_FLAG.LUBUFU)).to_be(TB_LUBUFU.OFFERED_APPRENTICE)
        expect(value(page([
        '@str@I have given Lubufu 20 Karambwanji.||',
        '@str@Lubufu has offered to train me as his apprentice.|',
        "@str@I have accepted Lubufu's offer.||",
    ]), TB_FLAG.LUBUFU)).to_be(TB_LUBUFU.COMPLETE)
    test('the Lubufu ladder reads from first offer to apprenticeship', _fn9)


describe('tbwt journal', _fn1)
