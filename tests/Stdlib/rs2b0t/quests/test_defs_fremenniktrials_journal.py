"""Ported from rs2b0t's test/api/ai/quests/defs/fremenniktrials-journal.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.defs.fremenniktrials.journal import FT_STAGE, parse_fremennik_journal, reset_fremennik_journal_cache

HEADER = '@str@I spoke to Brundt the Fremennik chieftan, and he told me|@str@that I could join their tribe if I could pass some trials|' + '@str@and get seven of the twelve council members votes.|'
VOTES = {
    '0': "@dbl@I don't have any votes yet|@dbl@I should try and find some of the @dre@council members|",
    '1': '@dbl@I have @dre@one@dbl@ vote so far|',
    '2': '@dbl@I have @dre@two@dbl@ votes so far|',
    '3': '@dbl@I have @dre@three@dbl@ votes so far|',
    '6': '@dbl@I have @dre@six@dbl@ votes so far|',
    '7': '@dbl@I have @dre@seven votes@dbl@! I should go speak to @dre@Brundt@dbl@ again|',
}
STARTED = Record({
    'navigator': '@dbl@The @dre@Navigator@dbl@ will vote for me if I can pass his trial|@dbl@I need to get from one end of his @dre@maze@dbl@ to the other|',
    'merchant': '@dbl@The @dre@Merchant@dbl@ will vote for me if I can pass his trial.|@dbl@Someone in this town has a @dre@rare flower@dbl@ that he wants.|',
    'hunter': '@dbl@The @dre@Hunter@dbl@ will vote for me if I can pass his trial.|@dbl@I need to @dre@track and defeat@dbl@ a creature called the @dre@Draugen|',
    'seer': '@dbl@The @dre@Seer@dbl@ will vote for me if I can pass his trial|@dbl@I need to get from @dre@one side@dbl@ of his house to @dre@the other|',
    'warrior': '@dbl@The @dre@Warrior@dbl@ will vote for me if I can pass his trial|@dbl@I need to fight @dre@Koschei@dbl@ to the @dre@death@dbl@ in @dre@unarmed combat|',
    'reveller': '@dbl@The @dre@Reveller@dbl@ will vote for me if I can pass his trial|@dbl@I need to defeat him in a @dre@drinking contest@dbl@ somehow!|',
    'bard': '@dbl@The @dre@Bard@dbl@ will vote for me if I can pass his trial|@dbl@I must make myself @dre@a lyre@dbl@ and play it in the @dre@longhall|',
})
DONE = Record({
    'navigator': "@str@I now have the Navigator's vote at the council.|",
    'merchant': "@str@I now have the Merchant's vote at the council.|",
    'hunter': "@str@I now have the Hunter's vote at the council.|",
    'seer': "@str@I now have the Seer's vote at the council|",
    'warrior': "@str@I now have the Warrior's vote at the council|",
    'reveller': "@str@I now have the Reveller's vote at the council|",
    'bard': "@str@I now have the Bard's vote at the council.|",
})
MERCHANT_STEP = Record({
    'olaf': '@dbl@The @dre@bard@dbl@ is looking for some @dre@new boots@dbl@...||',
    'yrsa': '@dbl@The @dre@shopkeeper@dbl@ is looking for a @dre@tax reduction@dbl@...||',
    'chief': '|@dbl@The @dre@chieftan@dbl@ wants a @dre@map of new hunting grounds@dbl@...||',
    'sigli': '|@dbl@The @dre@hunter@dbl@ is looking for a @dre@custom bowstring@dbl@...||',
    'skul': '|@dbl@The @dre@armourer@dbl@ is looking for a @dre@rare inedible fish@dbl@...||',
    'fisherman': '|@dbl@The @dre@fisherman@dbl@ is looking for a @dre@map of fishing spots@dbl@...||',
    'swensen': '|@dbl@The @dre@navigator@dbl@ is looking for a @dre@weather forecast@dbl@...||',
    'seer': '|@dbl@The @dre@seer@dbl@ is looking for a @dre@warrior to be his bodyguard@dbl@...||',
    'thorvald': '|@dbl@The @dre@warrior@dbl@ is looking for a @dre@champions token@dbl@...||',
    'manni': '|@dbl@The @dre@reveller@dbl@ is looking for a @dre@legendary cocktail@dbl@...||',
    'thora': '|@dbl@All @dre@Askeladden@dbl@ wants is @dre@some money@dbl@!||',
})
COMPLETE = '@str@I made my way to the far north of Kandarin and found the|@str@Barbarian hometown of Rellekka. The tribe that live there|' + '@str@call themselves the Fremennik, and offered me the chance|@str@to join them if I could pass their trials.|' + '@str@I managed to persuade seven of the twelve council of|@str@elders to vote for me at their next meeting, and became|' + '@str@an honorary member of the Fremennik.||@red@QUEST COMPLETE!|@dbl@They also gave me a new name:|@dre@Sigvald'


def page(votes=None, started=None, done=None, merchant_at=None):
    started = (started if started is not None else [])
    done = (done if done is not None else [])

    def line(trial):
        return (DONE.get(trial) if (trial in done) else (STARTED.get(trial) if (trial in started) else '|'))

    _v1 = VOTES[str(votes if votes is not None else 0)]
    return HEADER + (_v1) + line('navigator') + line('merchant') + ((MERCHANT_STEP.get(merchant_at) if merchant_at else '|')) + line('hunter') + line('seer') + line('warrior') + line('reveller') + line('bard')


def _reads_votes(votes):
    def check():
        expect(parse_fremennik_journal(page(votes=votes)).stage).to_be(votes)
    return check


def _names_step(step):
    def check():
        progress = parse_fremennik_journal(page(started=['merchant'], merchant_at=step))
        expect(f'merchant-at:{step}' in progress.flags).to_be(True)
        expect('merchant-started' in progress.flags).to_be(True)
    return check


def _fn2():
    def _fn3():
        expect((parse_fremennik_journal(COMPLETE).stage if parse_fremennik_journal(COMPLETE) is not None else None)).to_be(FT_STAGE.COMPLETE)
    test('reads the completed page', _fn3)

    def _fn4():
        progress = parse_fremennik_journal(page())
        expect((progress.stage if progress is not None else None)).to_be(0)
        _v5 = (progress.flags if progress is not None else None)
        expect(list(((_v5 if _v5 is not None else [])))).to_equal([])
    test('reads a fresh page as no votes and no flags', _fn4)
    for votes in [1, 2, 3, 6, 7]:
        test(f'reads {votes} vote(s) off the page', _reads_votes(votes))

    def _fn7():
        progress = parse_fremennik_journal(page(votes=1, done=['reveller'], started=['bard', 'hunter']))
        expect(('reveller-done' in (progress.flags if progress is not None else None))).to_be(True)
        expect(('bard-started' in (progress.flags if progress is not None else None))).to_be(True)
        expect(('hunter-started' in (progress.flags if progress is not None else None))).to_be(True)
        expect(('bard-done' in (progress.flags if progress is not None else None))).to_be(False)
        expect(('navigator-started' in (progress.flags if progress is not None else None))).to_be(False)
    test('separates a started trial from a won one', _fn7)
    for step in MERCHANT_STEP.keys():
        test(f'names the flower trade at \'{step}\'', _names_step(step))

    def _fn9():
        _v10 = (parse_fremennik_journal(page(started=['merchant'])).flags if parse_fremennik_journal(page(started=['merchant'])) is not None else None)
        flags = (_v10 if _v10 is not None else set())
        expect(any([f.startswith('merchant-at:') for f in list(flags)])).to_be(False)
    test('a started merchant trial with no step line carries no position', _fn9)

    def _fn11():
        reset_fremennik_journal_cache()
        expect(parse_fremennik_journal('')).to_be_undefined()
        expect(parse_fremennik_journal('@dbl@Some unrelated scroll')).to_be_undefined()
    test('an empty page is unreadable rather than zero votes', _fn11)


describe('The Fremennik Trials journal parsing', _fn2)
