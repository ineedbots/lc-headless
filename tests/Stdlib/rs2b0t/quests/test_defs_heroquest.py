"""Ported from rs2b0t's test/api/ai/quests/defs/heroquest.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestProgress, QuestSnapshot
from rs2004.quests.data import QUESTS
from rs2004.quests.defs.heroquest import decide, heroquest, in_sealed_pocket
from rs2004.quests.defs.heroquest.areas import HERO_ID
from rs2004.quests.defs.heroquest.config import hero_config, reset_hero_gang_cache
from rs2004.quests.defs.heroquest.journal import HERO_STAGE
from rs2004.quests.defs import QUEST_DEFS, def_by_id
from rs2004.quests.defs.shieldofarrav.config import arrav_config

VARROCK = Record({'x': 3210, 'z': 3490, 'level': 0})


# Why: the quest keeps a coin float for the 30gp ferry, so every snapshot carries one, a test that
# leaves the pack empty gets the withdrawal rather than the branch it is asking about.
def snap(over=None):
    if over is None:
        over = Fake()
    stage = (over.stage if over.stage is not None else HERO_STAGE.STARTED)
    _merged1 = {}
    for _k, _v in {
        'journal': 'in_progress',
        'inv': {},
        'worn': set(),
        'worn_ids': set(),
        'no_progress': 0,
        'bank_coins': 2000000,
        'bank': {},
        'bank_ids': {},
        'bank_known': True,
        'tile': VARROCK,
        'free_slots': 20,
        'stage': stage,
        'progress': QuestProgress(stage),
    }.items():
        _merged1[_k] = _v
    for _k, _v in over._fields.items():
        _merged1[_k] = _v
    inv_ids = {HERO_ID.COINS: 5000}
    if over.inv_ids is not None:
        for _k, _v in over.inv_ids.items():
            inv_ids[_k] = _v
    _merged1['inv_ids'] = inv_ids
    return QuestSnapshot(**_merged1)


def with_gang(gang):
    arrav_config.gang = gang
    reset_hero_gang_cache()


def kitted(gang):
    """Every piece the Black Arm disguise and the Phoenix snipe kit need, so a test can skip past them."""
    return ({_k: _v for _k, _v in [[HERO_ID.BLACK_PLATEBODY, 1], [HERO_ID.BLACK_PLATELEGS, 1], [HERO_ID.BLACK_FULL_HELM, 1]]} if gang == 'blackarm' else {_k: _v for _k, _v in [[HERO_ID.OAK_LONGBOW, 1], [HERO_ID.STEEL_ARROW, 150]]})


def _fn2():
    arrav_config.gang = 'random'
    hero_config.partner = ''
    reset_hero_gang_cache()


after_each(_fn2)


# Why: `no path to (2793,3180,0): unreachable without 30x Coins` is the failure in full, the Ardougne
# ferry is 30 coins and the pathfinder refuses the route without them in the pack.
def _fn3():
    def _fn4():
        with_gang('blackarm')
        step = decide(snap(Fake(**{'inv_ids': {_k: _v for _k, _v in [[HERO_ID.COINS, 0]]}, 'stage': HERO_STAGE.BLACKARM_SPOKEN})))
        expect(step).to_match_object(Record({'kind': 'withdraw'}))
    test('an empty pack withdraws before anything else', _fn4)

    def _fn5():
        with_gang('blackarm')
        hero_config.partner = 'rival'
        expect(decide(snap(Fake(**{'stage': HERO_STAGE.BLACKARM_SPOKEN})))).not_.to_match_object(Record({'kind': 'withdraw'}))
    test('a float already carried is left alone', _fn5)

    # Why: a float restored on every pass costs a bank trip after every shop, so the mark is low.
    def _fn6():
        with_gang('blackarm')
        hero_config.partner = 'rival'
        step = decide(snap(Fake(**{'stage': HERO_STAGE.BLACKARM_SPOKEN, 'inv_ids': {_k: _v for _k, _v in [[HERO_ID.COINS, 660]]}})))
        expect(step).not_.to_match_object(Record({'kind': 'withdraw'}))
    test('the change left after a purchase is enough', _fn6)

    def _fn7():
        with_gang('blackarm')
        step = decide(snap(Fake(**{
        'inv_ids': {_k: _v for _k, _v in [[HERO_ID.COINS, 0]]},
        'bank_coins': 0,
        'stage': HERO_STAGE.BLACKARM_SPOKEN,
    })))
        expect(step).not_.to_match_object(Record({'kind': 'withdraw'}))
    test('an empty bank does not send the bot to a booth for nothing', _fn7)


describe("hero's quest coin float", _fn3)


def _fn8():
    def _fn9():
        expect(decide(snap(Fake(**{'journal': 'unknown'})))).to_match_object(Record({'kind': 'wait'}))
    test('an unloaded journal waits rather than restarting a finished quest', _fn9)

    def _fn10():
        expect(decide(snap(Fake(**{'journal': 'complete'})))).to_match_object(Record({'kind': 'done'}))
    test('a green journal is done', _fn10)

    def _fn11():
        expect(decide(snap(Fake(**{'stage': None, 'progress': None})))).to_match_object(Record({'kind': 'wait'}))
    test('an unreadable stage waits', _fn11)

    # Why: ownsInventory skips the engine's provisioning, so nothing else opens a booth and a banked
    # armband, feather or eel stays invisible until the module asks for one read.
    def _fn12():
        expect(decide(snap(Fake(**{'bank_known': False})))).to_match_object(Record({'kind': 'scan_bank'}))
    test('an unread bank is scanned before anything else is decided', _fn12)

    def _fn13():
        step = decide(snap(Fake(**{'stage': HERO_STAGE.NOT_STARTED, 'progress': Record({'stage': 0, 'flags': set()})})))
        expect(step).to_match_object(Record({'kind': 'custom'}))
    test('a not-started quest applies to Achietties', _fn13)

    def _fn14():
        with_gang('blackarm')
        step = decide(snap(Fake(**{'stage': HERO_STAGE.BLACKARM_ARMBAND})))
        expect(step).to_match_object(Record({'kind': 'wait'}))
        expect((step).reason).to_contain('heroPartner')
    test('without a partner the armband stalls with a readable reason', _fn14)


describe("hero's quest decide", _fn8)


def _fn15():
    def ready(over=None):
        if over is None:
            over = Fake()
        _merged16 = {}
        for _k, _v in {
            'stage': HERO_STAGE.BLACKARM_ARMBAND,
            'inv_ids': {_k: _v for _k, _v in [[HERO_ID.ARMBAND, 1], [HERO_ID.FEATHER, 1], [HERO_ID.LAVA_EEL, 1]]},
        }.items():
            _merged16[_k] = _v
        for _k, _v in over._fields.items():
            _merged16[_k] = _v
        return snap(Fake(**_merged16))

    def _fn17():
        with_gang('blackarm')
        expect(decide(ready())).to_match_object(Record({'kind': 'custom'}))
    test('all three carried hands them to Achietties', _fn17)

    # Why: `~send_quest_complete` reads inv_total, so a banked feather is not a carried one.
    def _fn18():
        with_gang('blackarm')
        step = decide(ready(Fake(**{
        'inv_ids': {_k: _v for _k, _v in [[HERO_ID.ARMBAND, 1], [HERO_ID.LAVA_EEL, 1]]},
        'bank_ids': {_k: _v for _k, _v in [[HERO_ID.FEATHER, 1]]},
    })))
        expect(step).to_match_object(Record({'kind': 'withdraw'}))
    test('a banked feather is withdrawn rather than handed in', _fn18)

    def _fn19():
        with_gang('blackarm')
        step = decide(snap(Fake(**{
        'stage': HERO_STAGE.BLACKARM_ARMBAND,
        'inv_ids': {_k: _v for _k, _v in [[HERO_ID.ARMBAND, 1], [HERO_ID.FEATHER, 1]]},
    })))
        expect(step).not_.to_match_object(Record({'kind': 'done'}))
        expect(repr(step._fields)).not_.to_contain('Achietties')
    test('with the armband but no eel the eel chain runs first', _fn19)


describe("hero's quest hand-in", _fn15)


def _fn20():
    def _fn21():
        with_gang('blackarm')
        hero_config.partner = 'rival'
        step = decide(snap(Fake(**{'stage': HERO_STAGE.BLACKARM_SPOKEN})))
        expect((step).name).to_contain('Black platebody')
    test('the Black Arm bot buys its disguise before crossing to Brimhaven', _fn21)

    def _fn22():
        with_gang('phoenix')
        hero_config.partner = 'rival'
        step = decide(snap(Fake(**{'stage': HERO_STAGE.PHOENIX_SPOKEN})))
        expect((step).name).to_contain('Oak longbow')
    test('the Phoenix bot buys a bow before crossing to Brimhaven', _fn22)

    def _fn23():
        with_gang('blackarm')
        hero_config.partner = 'rival'
        step = decide(snap(Fake(**{'stage': HERO_STAGE.BLACKARM_SPOKEN, 'inv_ids': kitted('blackarm')})))
        expect(step).to_match_object(Record({'kind': 'custom'}))
    test('a kitted Black Arm bot goes for the hideout password', _fn23)

    def _fn24():
        with_gang('blackarm')
        hero_config.partner = 'rival'
        step = decide(snap(Fake(**{
        'stage': HERO_STAGE.BLACKARM_PAPERS_GIVEN,
        'inv_ids': {_k: _v for _k, _v in list(kitted('blackarm').items()) + [[HERO_ID.MISC_KEY, 1]]},
    })))
        expect((step).name).to_contain('give-key')
    test('the Black Arm bot hands the spare key over the moment Grip gives it', _fn24)

    # Why: the key is only useful with a bow worn, and fetching one afterwards starts in Brimhaven.
    def _fn25():
        with_gang('phoenix')
        hero_config.partner = 'rival'
        step = decide(snap(Fake(**{'stage': HERO_STAGE.PHOENIX_CHARLIE, 'inv_ids': kitted('phoenix')})))
        expect(step).to_match_object(Record({'kind': 'equip'}))
    test('a carried bow is worn before the key is asked for', _fn25)

    def _fn26():
        with_gang('phoenix')
        hero_config.partner = 'rival'
        step = decide(snap(Fake(**{'stage': HERO_STAGE.PHOENIX_CHARLIE, 'worn_ids': set([HERO_ID.OAK_LONGBOW, HERO_ID.STEEL_ARROW])})))
        expect((step).name).to_contain('take-key')
    test('a kitted Phoenix bot waits for that key before it walks to the slit', _fn26)

    def _fn27():
        with_gang('phoenix')
        hero_config.partner = 'rival'
        step = decide(snap(Fake(**{
        'stage': HERO_STAGE.PHOENIX_CHARLIE,
        'inv_ids': {_k: _v for _k, _v in list(kitted('phoenix').items()) + [[HERO_ID.MISC_KEY, 1]]},
        'worn_ids': set([HERO_ID.OAK_LONGBOW, HERO_ID.STEEL_ARROW]),
    })))
        expect((step).name).to_contain('arrow slit')
    test('holding the key, the Phoenix bot goes to the arrow slit', _fn27)

    # Why: the chest hands over two, one of which is the rival's payment.
    def _fn28():
        with_gang('blackarm')
        hero_config.partner = 'rival'
        step = decide(snap(Fake(**{'stage': HERO_STAGE.BLACKARM_LOOTED, 'inv_ids': {_k: _v for _k, _v in [[HERO_ID.CANDLESTICK, 2]]}})))
        expect((step).name).to_contain('give-candlestick')
    test('two candlesticks means one is owed to the rival', _fn28)

    def _fn29():
        with_gang('blackarm')
        hero_config.partner = 'rival'
        step = decide(snap(Fake(**{'stage': HERO_STAGE.BLACKARM_LOOTED, 'inv_ids': {_k: _v for _k, _v in [[HERO_ID.CANDLESTICK, 1]]}})))
        expect((step).name).to_contain('Katrine')
    test('one candlestick left goes to Katrine', _fn29)


describe("hero's quest gang branches", _fn20)


# Why: every Brimhaven pocket is sealed in the baked graph, so a shop or bank walk planned from inside
# one reads `unreachable` before it takes a step, the module owes the way out first.
def _fn30():
    MANSION = Record({'x': 2774, 'z': 3192, 'level': 0})

    def _fn31():
        with_gang('blackarm')
        step = decide(snap(Fake(**{'bank_known': False, 'tile': MANSION})))
        expect((step).name).to_contain('sealed')
    test('a bank scan from inside the mansion leaves it first', _fn31)

    # Why: a withdraw is a walk the navigator plans, where a buy leg crosses its own doors first.
    def _fn32():
        with_gang('blackarm')
        hero_config.partner = 'rival'
        step = decide(snap(Fake(**{
        'stage': HERO_STAGE.BLACKARM_SPOKEN,
        'tile': MANSION,
        'bank_ids': {_k: _v for _k, _v in [[HERO_ID.BLACK_PLATEBODY, 1]]},
    })))
        expect((step).name).to_contain('sealed')
    test('a bank withdrawal from inside the mansion leaves it first', _fn32)

    def _fn33():
        with_gang('blackarm')
        hero_config.partner = 'rival'
        step = decide(snap(Fake(**{
        'stage': HERO_STAGE.BLACKARM_PAPERS_GIVEN,
        'tile': MANSION,
        'inv_ids': {_k: _v for _k, _v in list(kitted('blackarm').items()) + [[HERO_ID.GRIP_KEYS, 1]]},
    })))
        expect((step).name).to_contain('treasure room')
    test('a custom leg is left alone — it crosses its own doors', _fn33)

    def _fn34():
        expect(in_sealed_pocket(snap(Fake(**{'tile': MANSION})))).to_be(True)
        expect(in_sealed_pocket(snap(Fake(**{'tile': Record({'x': 2793, 'z': 3180, 'level': 0})})))).to_be(False)
    test('the pocket test knows the street from the rooms', _fn34)


describe("hero's quest sealed pockets", _fn30)


def _fn35():
    def _fn36():
        expect(heroquest.record).to_be(([q for q in QUESTS if q.id == 'hero'] or [None])[0])
    test('the record is the one in the quest data', _fn36)

    def _fn37():
        expect(def_by_id('hero')).to_be(heroquest)
        ids = [d.record.id for d in QUEST_DEFS]
        expect(ids.index('hero')).to_be_greater_than(ids.index('dragon'))
    test('it is registered, and after Dragon Slayer', _fn37)

    def _fn38():
        expect(heroquest.owns_inventory).to_be(True)
    test('it owns its inventory, because nothing it needs is provisioned up front', _fn38)

    def _fn39():
        _fn40 = getattr(heroquest, 'warn_readiness', None)
        expect((_fn40() if _fn40 is not None else None)).to_contain('partner')
        hero_config.partner = 'rival'
        _fn41 = getattr(heroquest, 'warn_readiness', None)
        expect((_fn41() if _fn41 is not None else None)).to_be_null()
    test('readiness warns while no partner is set', _fn39)


describe("hero's quest module", _fn35)


def resumes_in_the_pockets():
    expect(heroquest.resume_at(Record({'x': 2770, 'z': 3195, 'level': 0}))).to_be(True)
    expect(heroquest.resume_at(Record({'x': 2847, 'z': 3387, 'level': 0}))).to_be(True)
    expect(heroquest.resume_at(VARROCK)).to_be(False)


test('a restart in a sealed pocket or on Entrana stays with the quest', resumes_in_the_pockets)
