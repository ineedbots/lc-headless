"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/sheepherder-journal.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.quests.defs.sheepherder.journal import SH_STAGE, parse_sheep_herder_journal

NOT_STARTED = '@dbl@I can start this quest by speaking to @dre@Councillor Halgrive @dbl@near to the @dre@Zoo @dbl@in @dre@East Ardougne@dbl@.'
PREAMBLE = '@str@Councillor Halgrive asked me to dispose of four|@str@plague-bearing sheep just north of Ardougne|@str@and I accepted.|' + '@str@He gave me some poisoned sheep feed to do this.|'
NEED_SUIT = PREAMBLE + '|@dbl@I need to get some protective clothing from @dre@Dr Orbon @dbl@who is in the church just north of @dre@Ardougne Zoo'
BOUGHT_SUIT = PREAMBLE + '|@str@I bought some protective clothing from Dr Orbon in the|@str@chapel north of Ardougne Zoo. I could now kill the sheep.|'
ORDINAL = ['first', 'second', 'third', 'fourth']


def line(ordinal, state):
    if state == 'burnt':
        return f'|@str@I have killed the {ordinal} sheep and incinerated its bones.|'
    elif state == 'killed':
        return f'|@dbl@I have killed the {ordinal} sheep. Now I must incinerate its @dre@bones@dbl@.|'
    elif state == 'herded':
        return f'|@dbl@I have herded the {ordinal} sheep to the pen. Now I must kill it safely.|'
    else:
        return f'|@dbl@I must find the {ordinal} sheep and herd it to the pen.|'


def disposing(states):
    return BOUGHT_SUIT + ''.join([line(ordinal, states[i]) for i, ordinal in enumerate(ORDINAL)])


ALL_BURNT = BOUGHT_SUIT + '|@str@I equipped a prod and then I used it to herd the diseased|@str@sheep to a pen where I could safely kill them and|@str@incinerate their bones.|' + '|@dbl@I should return to @dre@Councillor Halgrive @dbl@to collect the reward he has promised me for my hard work.'
COMPLETE = BOUGHT_SUIT + '|@str@I returned to let Councillor Halgrive know that the plagued|@str@sheep were no more and claimed my reward.|' + '@red@QUEST COMPLETE!'


def _fn1():
    def _fn2():
        progress = parse_sheep_herder_journal(NOT_STARTED)
        expect((progress.stage if progress is not None else None)).to_be(SH_STAGE.NOT_STARTED)
        _v3 = (progress.flags if progress is not None else None)
        expect(list(((_v3 if _v3 is not None else [])))).to_equal([])
    test('reads the not-started page as stage 0', _fn2)

    def _fn4():
        expect((parse_sheep_herder_journal(NEED_SUIT).stage if parse_sheep_herder_journal(NEED_SUIT) is not None else None)).to_be(SH_STAGE.NEED_SUIT)
    test('reads the pre-suit page as the stage that still owes Doctor Orbon a visit', _fn4)

    def _fn5():
        progress = parse_sheep_herder_journal(disposing(['none', 'none', 'none', 'none']))
        expect((progress.stage if progress is not None else None)).to_be(SH_STAGE.DISPOSING)
        _v6 = (progress.flags if progress is not None else None)
        expect(list(((_v6 if _v6 is not None else [])))).to_equal([])
    test('reads a page with no sheep dealt with as disposing and no flags', _fn5)

    def _fn7():
        progress = parse_sheep_herder_journal(disposing(['burnt', 'killed', 'herded', 'none']))
        _v8 = (progress.flags if progress is not None else None)
        expect(sorted(list(((_v8 if _v8 is not None else []))))).to_equal(['burnt-1', 'herded-1', 'herded-2', 'herded-3', 'killed-1', 'killed-2'])
    test('separates herded, killed and incinerated per sheep', _fn7)

    def _fn9():
        progress = parse_sheep_herder_journal(disposing(['none', 'none', 'none', 'killed']))
        expect(('killed-4' in (progress.flags if progress is not None else None))).to_be(True)
        expect(('burnt-4' in (progress.flags if progress is not None else None))).to_be(False)
    test('reads the killed line, whose colour tag sits between "its" and "bones"', _fn9)

    def _fn10():
        progress = parse_sheep_herder_journal(ALL_BURNT)
        expect((progress.stage if progress is not None else None)).to_be(SH_STAGE.DISPOSING)
        _v11 = (progress.flags if progress is not None else None)
        expect(sorted(list(((_v11 if _v11 is not None else []))))).to_equal(['burnt-1', 'burnt-2', 'burnt-3', 'burnt-4'])
    test('treats the reward page as all four burnt, since it drops the per-sheep lines', _fn10)

    def _fn12():
        expect((parse_sheep_herder_journal(COMPLETE).stage if parse_sheep_herder_journal(COMPLETE) is not None else None)).to_be(SH_STAGE.COMPLETE)
    test('reads the finished page as complete', _fn12)

    def _fn13():
        expect(parse_sheep_herder_journal('some other quest entirely')).to_be_undefined()
    test('returns undefined for a page it cannot place', _fn13)


describe('Sheep Herder journal parsing', _fn1)
