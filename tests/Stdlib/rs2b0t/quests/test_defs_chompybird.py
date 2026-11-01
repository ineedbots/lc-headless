"""rs2b0t's test/api/ai/quests/defs/chompybird.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs.record import Record
from rs2004.game import skills
from rs2004.quests.defs.chompybird import chompybird, decide
from rs2004.quests.defs.chompybird.areas import CB_ID, CB_STAGE
from rs2004.quests.defs.chompybird.cook import cook_state
from rs2004.quests.defs.chompybird.hunt import chest_state
from rs2004.quests.defs.chompybird.supplies import ARROW_TARGET
from rs2004.quests.defs import QUEST_DEFS
from rs2004.quests.engine.types import QuestProgress, QuestSnapshot

RANTZ = Record({'x': 2630, 'z': 2981, 'level': 0})
SEASONINGS = [
    [CB_ID.POTATO, 1],
    [CB_ID.ONION, 1],
    [CB_ID.CABBAGE, 1],
    [CB_ID.TOMATO, 1],
    [CB_ID.EQUA, 1],
    [CB_ID.DOOGLE, 1],
]


def snap(options=None):
    """A pack that has already been through the bank: coins, food and an axe."""
    if options is None:
        options = Record({})
    stage = (options.stage if options.stage is not None else CB_STAGE.NOT_STARTED)
    inv = {_k: _v for _k, _v in [['coins', 2000], ['trout', 6], ['bronze axe', 1]] + list(((options.inv if options.inv is not None else [])))}
    return QuestSnapshot(**{
        'journal': (options.journal if options.journal is not None else (('not_started' if stage == CB_STAGE.NOT_STARTED else 'in_progress'))),
        'inv': inv,
        'inv_ids': {_k: _v for _k, _v in [[CB_ID.FEATHER, ARROW_TARGET * 4]] + list(((options.inv_ids if options.inv_ids is not None else [])))},
        'worn': set(),
        'worn_ids': set((options.worn_ids if options.worn_ids is not None else [])),
        'no_progress': 0,
        'bank_coins': 2000000,
        'stage': stage,
        'progress': QuestProgress(stage, set()),
        'bank': {_k: _v for _k, _v in (options.bank if options.bank is not None else [['coins', 2000000]])},
        'bank_ids': {_k: _v for _k, _v in (options.bank_ids if options.bank_ids is not None else [])},
        'bank_known': (options.bank_known if options.bank_known is not None else True),
        'tile': RANTZ,
        'free_slots': 20,
    })


def step(options=None):
    if options is None:
        options = Record({})
    return decide(snap(options))


def named(s):
    return ((s.name if s.kind == 'custom' else s.kind))


TOOLED = [[CB_ID.KNIFE, 1], [CB_ID.CHISEL, 1]]


def _fn1():
    def _fn2():
        cook_state.kids_asked = False
        chest_state.refused = False
        spy_on(skills, 'level', impl=lambda skill: 70)
    before_each(_fn2)

    def _fn3():
        expect(step(Record({'journal': 'unknown'}))).to_equal(Record({'kind': 'wait', 'reason': 'quest journal not loaded'}))
    test('an unloaded journal waits rather than restarting the quest', _fn3)

    def _fn4():
        expect(step(Record({'journal': 'complete', 'stage': CB_STAGE.COMPLETE}))).to_equal(Record({'kind': 'done'}))
    test('a complete journal is done', _fn4)

    def _fn5():
        bare = snap(Record({'journal': 'in_progress'}))
        bare.stage = None
        bare.progress = None
        expect(decide(bare)).to_equal(Record({'kind': 'wait', 'reason': 'quest stage not readable'}))
    test('an unreadable stage waits', _fn5)

    def _fn7():
        expect(named(step())).to_be("agree to make Rantz his 'stabbers'")
    test('a dressed pack starts the quest with Rantz', _fn7)

    def _fn8():
        s = step(Record({'inv': [['bronze axe', 0]], 'bank': [['coins', 2000000], ['iron axe', 1]]}))
        expect(s.kind).to_be('withdraw')
        expect(s.kind == 'withdraw' and any([i['name'] == 'Iron axe' for i in s.items])).to_be(True)
    test('an axe is withdrawn before the walk south when the bank has one', _fn8)

    def _fn9():
        s = step(Record({'inv': [['bronze axe', 0]]}))
        expect(s.kind).to_be('buy')
        expect(s.kind == 'buy' and s.item).to_be('Bronze axe')
        expect(s.kind == 'buy' and s.shop.npc).to_be('Bob')
    test('an axeless bank buys one from Bob rather than parking', _fn9)

    def _fn10():
        s = step(Record({'inv_ids': [[CB_ID.FEATHER, 0]]}))
        expect(s.kind).to_be('buy')
        expect(s.kind == 'buy' and s.item).to_be('Feather')
        expect(s.kind == 'buy' and s.qty).to_be(ARROW_TARGET * 4)
    test('feathers are bought from Gerrant before the quest starts', _fn10)

    def _fn11():
        s = step(Record({'inv_ids': [[CB_ID.FEATHER, 0]], 'bank_ids': [[CB_ID.FEATHER, 500]]}))
        expect(s.kind).to_be('withdraw')
        expect(s.kind == 'withdraw' and s.items[0].get('id')).to_be(CB_ID.FEATHER)
    test('banked feathers are withdrawn instead of bought', _fn11)

    def _fn12():
        expect(named(step(Record({'stage': CB_STAGE.STARTED})))).to_be('buy the knife and chisel from Bugs')
    test('the started quest buys the knife and chisel from Bugs', _fn12)

    def _fn13():
        s = step(Record({'stage': CB_STAGE.STARTED, 'bank_ids': [[CB_ID.KNIFE, 1], [CB_ID.CHISEL, 1]]}))
        expect(s.kind).to_be('withdraw')
        expect(s.kind == 'withdraw' and [i['id'] for i in s.items]).to_equal([CB_ID.KNIFE, CB_ID.CHISEL])
    test('a banked knife and chisel are withdrawn rather than bought', _fn13)

    def _fn14():
        expect(named(step(Record({'stage': CB_STAGE.STARTED, 'inv_ids': TOOLED})))).to_be('chop an achey tree')
    test('with tools and no logs it chops an achey tree', _fn14)

    def _fn15():
        s = step(Record({'stage': CB_STAGE.STARTED, 'inv_ids': list(TOOLED) + [[CB_ID.ACHEY_LOGS, 1]]}))
        expect(s.kind).to_be('use_on')
        expect(s.kind == 'use_on' and s.target).to_be('Achey tree logs')
        expect(s.kind == 'use_on' and s.product).to_be('Ogre arrow shaft')
    test('logs in the pack are cut into shafts', _fn15)

    def _fn16():
        s = step(Record({'stage': CB_STAGE.STARTED, 'inv_ids': list(TOOLED) + [[CB_ID.SHAFT, 6]]}))
        expect(s.kind).to_be('use_on')
        expect(s.kind == 'use_on' and s.product).to_be('Flighted ogre arrow')
    test('a batch of six shafts is feathered rather than fed in threes', _fn16)

    def _fn17():
        s = step(Record({
        'stage': CB_STAGE.STARTED,
        'inv_ids': list(TOOLED) + [[CB_ID.FLIGHTED, 6]],
        'bank': [['coins', 2000000], ['rune scimitar', 1]],
    }))
        expect(s.kind).to_be('withdraw')
        expect(s.kind == 'withdraw' and any([i['name'] == 'Rune scimitar' for i in s.items])).to_be(True)
    test('flighted arrows with no tips arm the account before the wolf', _fn17)

    def _fn18():
        s = step(Record({
        'stage': CB_STAGE.STARTED,
        'inv_ids': list(TOOLED) + [[CB_ID.FLIGHTED, 6]],
        'inv': [['rune scimitar', 0]],
        'worn_ids': [1333],
    }))
        expect(named(s)).to_be('kill a wolf for bones')
    test('an armed account fights the wolf itself', _fn18)

    def below_tips_crafting():
        spy_on(skills, 'level', impl=lambda skill: 4)
        s = step(Record({'stage': CB_STAGE.STARTED, 'inv_ids': list(TOOLED) + [[CB_ID.FLIGHTED, 6]], 'inv': [['rune scimitar', 0]], 'worn_ids': [1333]}))
        expect(s.kind).to_be('wait')
        expect(s.reason).to_contain('Crafting 5')
    test('below Crafting 5 it waits with the reason rather than killing a wolf for tips it cannot chisel', below_tips_crafting)

    def _fn19():
        s = step(Record({'stage': CB_STAGE.STARTED, 'inv_ids': list(TOOLED) + [[CB_ID.FLIGHTED, 6], [CB_ID.ARROWTIPS, 6]]}))
        expect(s.kind).to_be('use_on')
        expect(s.kind == 'use_on' and s.product).to_be('Ogre arrow')
    test('flighted arrows and tips make ogre arrows', _fn19)

    def _fn20():
        s = step(Record({'stage': CB_STAGE.STARTED, 'inv_ids': list(TOOLED) + [[CB_ID.ARROW, ARROW_TARGET]]}))
        expect(named(s)).to_be('hand Rantz the six ogre arrows')
    test('a full quiver hands six over to Rantz', _fn20)

    def _fn21():
        expect(named(step(Record({'stage': CB_STAGE.GIVEN_ARROWS})))).to_be('ask Rantz how to make the chompys come')
    test('the given-arrows stage asks how to make the chompys come', _fn21)

    def _fn22():
        expect(named(step(Record({'stage': CB_STAGE.KIDS_PLAY_WITH_TOAD})))).to_be('take the ogre bellows from the chest')
    test('the chest is searched for the bellows once the kids have been mentioned', _fn22)

    def _fn23():
        chest_state.refused = True
        s = step(Record({'stage': CB_STAGE.KIDS_PLAY_WITH_TOAD, 'bank_ids': [[CB_ID.BELLOWS_EMPTY, 1]]}))
        expect(s.kind).to_be('withdraw')
        expect(s.kind == 'withdraw' and s.items[0].get('id')).to_be(CB_ID.BELLOWS_EMPTY)
    test('a refused chest sends it to the bank for the pair the account already owns', _fn23)

    def _fn24():
        chest_state.refused = True
        expect(step(Record({'stage': CB_STAGE.KIDS_PLAY_WITH_TOAD}))).to_equal(Record({'kind': 'wait', 'reason': 'no ogre bellows in the chest or the bank'}))
    test('a refused chest and an empty bank park with a reason', _fn24)

    def _fn25():
        s = step(Record({'stage': CB_STAGE.REMOVED_ROCK, 'inv_ids': [[CB_ID.BELLOWS3, 1]]}))
        expect(named(s)).to_be('inflate a swamp toad')
    test('bellows in the pack inflate a toad', _fn25)

    def _fn26():
        s = step(Record({'stage': CB_STAGE.REMOVED_ROCK, 'inv_ids': [[CB_ID.BELLOWS1, 1], [CB_ID.TOAD, 1]]}))
        expect(named(s)).to_be('show Rantz the bloated toad')
    test('a bloated toad is shown to Rantz before it is placed', _fn26)

    def _fn27():
        s = step(Record({'stage': CB_STAGE.SHOWN_TOAD, 'inv_ids': [[CB_ID.BELLOWS3, 1], [CB_ID.TOAD, 1]]}))
        expect(named(s)).to_be('bait the clearing and watch Rantz shoot')
    test('the shown-toad stage baits the clearing and waits for Rantz', _fn27)

    def _fn28():
        expect(named(step(Record({'stage': CB_STAGE.RANTZ_MISSED})))).to_be('borrow the ogre bow from Rantz')
    test('a missed shot sends it back to Rantz for the bow', _fn28)

    # Why: past the loan Rantz sells the replacement for 500-550 coins and answers an empty purse with "come back when you have".
    def _fn29():
        s = step(Record({'stage': CB_STAGE.GOT_BOW, 'inv': [['coins', 0]]}))
        expect(s.kind).to_be('withdraw')
        expect(s.kind == 'withdraw' and any([i['name'] == 'Coins' for i in s.items])).to_be(True)
    test('coins come out of the bank before the bow is asked for', _fn29)

    def _fn30():
        s = step(Record({'stage': CB_STAGE.GOT_BOW, 'inv': [['coins', 0], ['bronze axe', 0]]}))
        expect(s.kind).to_be('withdraw')
        expect(s.kind == 'withdraw' and all([not i['name'].endswith('axe') for i in s.items])).to_be(True)
    test('the empty-purse withdrawal leaves the axe alone', _fn30)

    def _fn31():
        s = step(Record({'stage': CB_STAGE.GOT_BOW, 'inv_ids': [[CB_ID.BOW, 1], [CB_ID.ARROW, 6], [CB_ID.BELLOWS3, 1]]}))
        expect(named(s)).to_be('shoot and pluck a chompy bird')
    test('bow, arrows and bellows in hand hunt the chompy', _fn31)

    def _fn32():
        s = step(Record({'stage': CB_STAGE.GOT_BOW, 'inv_ids': [[CB_ID.BELLOWS3, 1]], 'worn_ids': [CB_ID.BOW, CB_ID.ARROW]}))
        expect(named(s)).to_be('shoot and pluck a chompy bird')
    test('a quivered arrow counts, since the worn count is not on the wire', _fn32)

    def _fn33():
        s = step(Record({'stage': CB_STAGE.GOT_BOW, 'inv_ids': list(TOOLED) + [[CB_ID.BOW, 1], [CB_ID.BELLOWS3, 1]]}))
        expect(named(s)).to_be('chop an achey tree')
    test('an empty quiver goes back to the fletching chain', _fn33)

    def _fn34():
        s = step(Record({'stage': CB_STAGE.KILLED_CHOMPY, 'inv_ids': [[CB_ID.RAW_CHOMPY, 1]]}))
        expect(named(s)).to_be('show Rantz the raw chompy')
    test('a plucked chompy is shown to Rantz', _fn34)

    def _fn35():
        s = step(Record({'stage': CB_STAGE.KILLED_CHOMPY, 'inv_ids': [[CB_ID.BOW, 1], [CB_ID.ARROW, 6], [CB_ID.BELLOWS3, 1]]}))
        expect(named(s)).to_be('shoot and pluck a chompy bird')
    test('the killed stage hunts again when the carcass was lost', _fn35)

    # Why: the chompy takes several shots, so a handful of arrows is a fight that runs dry with the bird alive.
    def _fn36():
        s = step(Record({
        'stage': CB_STAGE.GOT_BOW,
        'inv_ids': list(TOOLED) + [[CB_ID.BOW, 1], [CB_ID.ARROW, 3], [CB_ID.BELLOWS3, 1]],
    }))
        expect(named(s)).to_be('chop an achey tree')
    test('a short quiver goes back to the fletching chain rather than hunting', _fn36)

    def _fn37():
        s = step(Record({'stage': CB_STAGE.TOLD_TO_COOK, 'inv_ids': [[CB_ID.RAW_CHOMPY, 1]]}))
        expect(named(s)).to_be('ask Bugs and Fycie what they want')
    test('the cook stage asks the children first', _fn37)

    def _fn38():
        cook_state.kids_asked = True
        s = step(Record({'stage': CB_STAGE.TOLD_TO_COOK, 'inv_ids': [[CB_ID.RAW_CHOMPY, 1]]}))
        expect(named(s)).to_be('pick a potato')
    test('every seasoning is carried, since none of the three choices is on the wire', _fn38)

    def _fn39():
        cook_state.kids_asked = True
        s = step(Record({'stage': CB_STAGE.TOLD_TO_COOK, 'inv_ids': [[CB_ID.RAW_CHOMPY, 1]] + list(SEASONINGS)}))
        expect(named(s)).to_be('roast the chompy on the ogre spit')
    test('a stocked pack roasts the chompy', _fn39)

    def _fn40():
        s = step(Record({'stage': CB_STAGE.CHOMPY_COOKED, 'inv_ids': [[CB_ID.SEASONED_CHOMPY, 1]]}))
        expect(named(s)).to_be('hand Rantz the seasoned chompy')
    test('the cooked stage hands the seasoned chompy over', _fn40)


describe('big chompy bird hunting decide', _fn1)


def _fn41():
    def _fn42():
        expect(any([d.record.id == 'chompybird' for d in QUEST_DEFS])).to_be(True)
    test('is registered in the quest queue', _fn42)

    def _fn43():
        expect(chompybird.owns_inventory).to_be(True)
        expect(chompybird.bank).to_match_object(Record({'x': 2612, 'z': 3092, 'level': 0}))
    test('owns its own inventory and banks at Yanille', _fn43)

    def _fn44():
        skills = (chompybird.record.requirements.skills if chompybird.record.requirements.skills is not None else [])
        expect(skills).to_equal([
        Record({'skill': 'fletching', 'level': 5}),
        Record({'skill': 'cooking', 'level': 30}),
        Record({'skill': 'ranged', 'level': 30}),
    ])
    test('declares the official requirements', _fn44)


describe('big chompy bird hunting module', _fn41)
