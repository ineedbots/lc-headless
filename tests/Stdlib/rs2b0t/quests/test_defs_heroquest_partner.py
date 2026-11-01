"""Ported from rs2b0t's test/api/ai/quests/defs/heroquest-partner.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.defs.heroquest.journal import HERO_STAGE
from rs2004.quests.defs.heroquest.partner import LURE_RETRIES_BEFORE_REFETCH, decide_hero_handoff, should_fetch_key

def input(over=None):
    if over is None:
        over = Record({})
    _merged1 = {}
    for _k, _v in {
        'gang': 'blackarm',
        'stage': HERO_STAGE.STARTED,
        'has_key': False,
        'candlesticks': 0,
        'partner_configured': True,
        'ready': True,
    }.items():
        _merged1[_k] = _v
    for _k, _v in (over._fields if isinstance(over, Record) else over).items():
        _merged1[_k] = _v
    return Record(_merged1)


def handoff(i):
    return decide_hero_handoff(i.gang, i.stage, i.has_key, i.candlesticks, i.partner_configured, i.ready)


def _fn2():
    def _fn3():
        expect(handoff(input(Record({'partner_configured': False, 'stage': HERO_STAGE.BLACKARM_PAPERS_GIVEN, 'has_key': True})))).to_be_null()
    test('nothing is owed while no partner is configured', _fn3)

    # Why: `open_and_close_door` teleports the actor and re-shuts in three ticks, so the Black Arm bot
    # cannot hold the side door open, the tradeable spare key is the only way the rival gets in.
    def _fn4():
        expect(handoff(input(Record({'stage': HERO_STAGE.BLACKARM_PAPERS_GIVEN, 'has_key': True})))).to_be('give-key')
    test('the Black Arm bot gives the spare key the moment Grip issues it', _fn4)

    def _fn5():
        expect(handoff(input(Record({'stage': HERO_STAGE.BLACKARM_PAPERS_GIVEN})))).to_be_null()
    test('it does not give a key it has not been handed', _fn5)

    def _fn6():
        expect(handoff(input(Record({'stage': HERO_STAGE.BLACKARM_MANSION, 'has_key': True})))).to_be_null()
    test('it does not give the key before Grip has taken the papers', _fn6)

    # Why: the chest hands over two, one of which is the rival's payment for the kill.
    def _fn7():
        expect(handoff(input(Record({'stage': HERO_STAGE.BLACKARM_LOOTED, 'candlesticks': 2})))).to_be('give-candlestick')
    test('two candlesticks owes the rival one', _fn7)

    def _fn8():
        expect(handoff(input(Record({'stage': HERO_STAGE.BLACKARM_LOOTED, 'candlesticks': 1})))).to_be_null()
    test('the last candlestick is Katrine’s, not the rival’s', _fn8)

    # Why: the key is only useful with a bow worn, and fetching one afterwards starts in Brimhaven,
    # where the nearest bank is Ardougne across a fare each way.
    def _fn9():
        expect(handoff(input(Record({'gang': 'phoenix', 'stage': HERO_STAGE.PHOENIX_CHARLIE, 'ready': False})))).to_be_null()
    test('a Phoenix bot without its bow fetches that first', _fn9)

    def _fn10():
        expect(handoff(input(Record({'gang': 'phoenix', 'stage': HERO_STAGE.PHOENIX_CHARLIE})))).to_be('take-key')
    test('the Phoenix bot asks for the key once Charlie has shown the door', _fn10)

    def _fn11():
        expect(handoff(input(Record({'gang': 'phoenix', 'stage': HERO_STAGE.PHOENIX_CHARLIE, 'has_key': True})))).to_be_null()
    test('it stops asking once it holds one', _fn11)

    def _fn12():
        expect(handoff(input(Record({'gang': 'phoenix', 'stage': HERO_STAGE.PHOENIX_KILLED_GRIP})))).to_be('take-candlestick')
    test('after the kill the Phoenix bot waits on its candlestick', _fn12)

    def _fn13():
        expect(handoff(input(Record({'gang': 'phoenix', 'stage': HERO_STAGE.PHOENIX_KILLED_GRIP, 'candlesticks': 1})))).to_be_null()
    test('and stops once it has one', _fn13)

    def _fn14():
        expect(handoff(input(Record({'stage': HERO_STAGE.BLACKARM_ARMBAND, 'has_key': True, 'candlesticks': 2})))).to_be_null()
        expect(handoff(input(Record({'gang': 'phoenix', 'stage': HERO_STAGE.PHOENIX_ARMBAND, 'candlesticks': 0})))).to_be_null()
    test('an armbanded bot on either side owes nothing', _fn14)


describe('decideHeroHandoff', _fn2)


# Why: Grip re-issues the spare whenever the bot holds none, so a Black Arm bot that fetches after
# every trade swaps keys with its rival forever instead of luring him onto the arrow slit.
def _fn15():
    def _fn16():
        expect(should_fetch_key(Record({'gave_key': False, 'lure_failures': 0}))).to_be(True)
    test('the first key is always fetched', _fn16)

    def _fn17():
        expect(should_fetch_key(Record({'gave_key': True, 'lure_failures': 0}))).to_be(False)
        expect(should_fetch_key(Record({'gave_key': True, 'lure_failures': LURE_RETRIES_BEFORE_REFETCH - 1}))).to_be(False)
    test('a bot that has already handed one over lures instead', _fn17)

    # Why: a rival that died holding the key needs a second one, and only an empty-handed bot can ask.
    def _fn18():
        expect(should_fetch_key(Record({'gave_key': True, 'lure_failures': LURE_RETRIES_BEFORE_REFETCH}))).to_be(True)
    test('a run of fruitless lures re-opens the fetch', _fn18)


describe('shouldFetchKey', _fn15)
