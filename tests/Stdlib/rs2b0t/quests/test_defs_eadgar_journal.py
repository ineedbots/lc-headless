"""Ported from rs2b0t's test/api/ai/quests/defs/eadgar-journal.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.defs.eadgar.areas import ER_ITEM, committed, eadgar_zone
from rs2004.quests.defs.eadgar.journal import EADGAR_FLAG, EADGAR_STAGE, parse_eadgar_journal
from rs2004.quests.engine.types import flag_value

def at(x, z, level=0):
    return (Record({'x': x, 'z': z, 'level': level}))


# Lines lifted from content `eadgar_journal.rs2`; the journal keeps every earlier one struck through.
OPENED = '@str@Sanfew asked me to find him some Goutweed.'
COOK = '|@str@The Troll Cook will tell me how to find goutweed if I bring him|@str@a tasty human.'
PLAN = '|@str@Mad Eadgar has a plan.'
PARROT = '||@str@I got the parrot Eadgar wanted.'
HIDDEN = '|@str@I hid the parrot under the rack in the Troll prison.'
GAVE = '|@str@Eadgar wants to make a fake human to give the troll cook. I|@str@gave Eadgar everything he needed.'
POTION = '|@str@I made the Troll potion and gave it to Mad Eadgar.'
FETCHED = '|@str@I fetched the parrot back from the Troll prison rack'
FAKE_MAN = " and|@str@gave it to Eadgar.||@str@I got Eadgar's fake man"
BURNT = ' and gave it to the Troll Cook.|@str@The Troll Cook told me the key to the storeroom is in a|@str@fake bottom in the kitchen drawers.'
UNLOCKED = "||@str@I've unlocked the storeroom!"
NOT_STARTED = '@dbl@I can start this quest by speaking to @dre@Sanfew@dbl@ after|completing the @dre@Druidic Ritual@dbl@ quest in @dre@Taverley@dbl@. To complete|' + 'this quest I need @dre@Level 31 Herblore@dbl@. I also need to have|rescued @dre@Mad Eadgar@dbl@ from the @dre@Troll Stronghold'
NEEDS_LIST = OPENED + COOK + PLAN + PARROT + HIDDEN + '||@dbl@Eadgar wants to make a @dre@fake human @dbl@to give the Troll Cook.|I still need to bring him:' + '@dre@|Logs|5 raw chickens|10 sheaves of grains|Some Dirty Clothes'


def _fn1():
    def _fn2(text, stage):
        expect((parse_eadgar_journal(text).stage if parse_eadgar_journal(text) is not None else None)).to_be(stage)
    test_each([
        [NOT_STARTED, EADGAR_STAGE.NOT_STARTED],
        [
        OPENED + '||@dbl@I need to find out where to get @dre@Goutweed - Mad Eadgar@dbl@ may|be able to help.',
        EADGAR_STAGE.STARTED,
    ],
        [
        OPENED + '||@dbl@I need to find out where to get @dre@Goutweed - @dbl@I should ask the|@dre@Troll Cook.',
        EADGAR_STAGE.SPOKE_EADGAR,
    ],
        [
        OPENED + COOK + '||@dbl@I need to get @dre@a tasty human@dbl@ for the @dre@Troll Cook. Mad Eadgar|@dbl@may be able to help.',
        EADGAR_STAGE.SPOKE_BURNTMEAT,
    ],
        [
        OPENED + COOK + PLAN + '||@dbl@I need to bring Eadgar a @dre@parrot @dbl@from the @dre@Zoo',
        EADGAR_STAGE.NEEDS_PARROT,
    ],
        [
        OPENED + COOK + PLAN + PARROT + '||@dbl@I need to @dre@hide the parrot@dbl@ somewhere it can hear what Trolls|expect humans to sound like.',
        EADGAR_STAGE.EXPLAINED_PLAN,
    ],
        [
        OPENED + COOK + PLAN + PARROT + HIDDEN + "||@dbl@I should go and find out the rest of Mad Eadgar's plan.",
        EADGAR_STAGE.HID_PARROT,
    ],
        [NEEDS_LIST, EADGAR_STAGE.NEEDS_ITEMS],
        [
        OPENED + COOK + PLAN + PARROT + HIDDEN + GAVE + '|@dbl@I need to make a troll truth potion by putting @dre@dried, @dre@ground|troll thistle @dbl@in a @dre@potion of ranarr weed',
        EADGAR_STAGE.NEEDS_POTION,
    ],
        [
        OPENED + COOK + PLAN + PARROT + HIDDEN + GAVE + POTION + '||@dbl@I need to fetch the parrot back from the @dre@prison rack',
        EADGAR_STAGE.NEEDS_PARROT_BACK,
    ],
        [
        OPENED + COOK + PLAN + PARROT + HIDDEN + GAVE + POTION + FETCHED + '.|@dbl@I should go tell Eadgar.',
        EADGAR_STAGE.GOT_PARROT_BACK,
    ],
        [
        OPENED + COOK + PLAN + PARROT + HIDDEN + GAVE + POTION + FETCHED + FAKE_MAN + '.|@dbl@I should give the fake man to the @dre@Troll cook',
        EADGAR_STAGE.GOT_FAKE_MAN,
    ],
        [
        OPENED + COOK + PLAN + PARROT + HIDDEN + GAVE + POTION + FETCHED + FAKE_MAN + BURNT + '||@dbl@I should get the @dre@key to the storeroom @dbl@and unlock it.',
        EADGAR_STAGE.GOT_BURNT_MEAT,
    ],
        [
        OPENED + COOK + PLAN + PARROT + HIDDEN + GAVE + POTION + FETCHED + FAKE_MAN + BURNT + UNLOCKED + '|@dbl@I should sneak in and get some @dre@goutweed',
        EADGAR_STAGE.UNLOCKED_STOREROOM,
    ],
        [
        OPENED + COOK + PLAN + PARROT + HIDDEN + GAVE + POTION + FETCHED + FAKE_MAN + BURNT + UNLOCKED + '|@str@I snuck into the storeroom and got some goutweed. I gave|@str@ it to Sanfew and he taught me the Trollheim Teleport spell.' + '||@dre@QUEST COMPLETE!',
        EADGAR_STAGE.COMPLETE,
    ],
    ])('maps journal text to stage %#', _fn2)

    def _fn3():
        expect(parse_eadgar_journal(["Eadgar's Ruse", 'Loading…'])).to_be_undefined()
    test('fails closed on journal text it does not recognise', _fn3)

    # Why: every later entry keeps every struck-through line, so a phrase that first appears
    # at stage 60 is still in the text at stage 100, the newest phrase has to win.
    def _fn4():
        late = OPENED + COOK + PLAN + PARROT + HIDDEN + GAVE + POTION + FETCHED + FAKE_MAN + BURNT + UNLOCKED
        expect(late).to_contain('I hid the parrot under the rack')
        expect(late).to_contain("I got Eadgar's fake man")
        expect((parse_eadgar_journal(late).stage if parse_eadgar_journal(late) is not None else None)).to_be(EADGAR_STAGE.UNLOCKED_STOREROOM)
    test('the newest phrase wins over every earlier one it still carries', _fn4)


describe('parseEadgarJournal', _fn1)


def _fn5():
    def _fn6():
        progress = parse_eadgar_journal(NEEDS_LIST)
        expect((progress.stage if progress is not None else None)).to_be(EADGAR_STAGE.NEEDS_ITEMS)
        expect((EADGAR_FLAG.NEED_LOGS in (progress.flags if progress is not None else None))).to_be(True)
        expect((EADGAR_FLAG.NEED_CLOTHES in (progress.flags if progress is not None else None))).to_be(True)
        expect(flag_value(progress, EADGAR_FLAG.NEED_CHICKENS)).to_be(5)
        expect(flag_value(progress, EADGAR_FLAG.NEED_GRAIN)).to_be(10)
    test('reads the whole list at stage 70', _fn6)

    def _fn7():
        progress = parse_eadgar_journal(OPENED + COOK + PLAN + PARROT + HIDDEN + '||@dbl@Eadgar wants to make a @dre@fake human @dbl@to give the Troll Cook.|I still need to bring him:' + '@dre@|1 raw chicken|1 sheaf of grain')
        expect((EADGAR_FLAG.NEED_LOGS in (progress.flags if progress is not None else None))).to_be(False)
        expect((EADGAR_FLAG.NEED_CLOTHES in (progress.flags if progress is not None else None))).to_be(False)
        expect(flag_value(progress, EADGAR_FLAG.NEED_CHICKENS)).to_be(1)
        expect(flag_value(progress, EADGAR_FLAG.NEED_GRAIN)).to_be(1)
    test('reads a part-delivered list, singulars included', _fn7)

    # Why: "a tasty human" and "the rack in the Troll prison" both sit above the list in the same
    # journal, and neither is anything the scarecrow still wants.
    def _fn8():
        progress = parse_eadgar_journal(OPENED + COOK + PLAN + PARROT + HIDDEN + '||@dbl@Eadgar wants to make a @dre@fake human @dbl@to give the Troll Cook.|I still need to bring him:@dre@|Logs')
        expect((EADGAR_FLAG.NEED_LOGS in (progress.flags if progress is not None else None))).to_be(True)
        expect(flag_value(progress, EADGAR_FLAG.NEED_CHICKENS)).to_be_undefined()
        expect(flag_value(progress, EADGAR_FLAG.NEED_GRAIN)).to_be_undefined()
        expect((EADGAR_FLAG.NEED_CLOTHES in (progress.flags if progress is not None else None))).to_be(False)
    test('reads the tail after the list header, never the struck-through history', _fn8)

    def _fn9():
        with_potion = parse_eadgar_journal(OPENED + COOK + PLAN + PARROT + HIDDEN + GAVE + '|@dbl@I made the Troll potion. I should go give it to @dre@Mad @dre@Eadgar')
        expect((with_potion.stage if with_potion is not None else None)).to_be(EADGAR_STAGE.NEEDS_POTION)
        expect((EADGAR_FLAG.POTION_MADE in (with_potion.flags if with_potion is not None else None))).to_be(True)
        with_goutweed = parse_eadgar_journal(OPENED + COOK + PLAN + PARROT + HIDDEN + GAVE + POTION + FETCHED + FAKE_MAN + BURNT + UNLOCKED + '|@str@I snuck into the storeroom and got some goutweed.|@dbl@I should bring this to @dre@Sanfew and collect my reward.')
        expect((with_goutweed.stage if with_goutweed is not None else None)).to_be(EADGAR_STAGE.UNLOCKED_STOREROOM)
        expect((EADGAR_FLAG.HAVE_GOUTWEED in (with_goutweed.flags if with_goutweed is not None else None))).to_be(True)
    test('the made-potion and carried-goutweed lines are flags, not stages', _fn9)


describe("Eadgar's Ruse scarecrow needs", _fn5)


def _fn10():
    def _fn11():
        expect(eadgar_zone(at(2893, 10074, 2))).to_be('cave')
        expect(eadgar_zone(at(2890, 10086, 2))).to_be('cave')
        expect(eadgar_zone(at(2844, 10057, 1))).to_be('stronghold')
        expect(eadgar_zone(at(2856, 10075))).to_be('stronghold')
        expect(eadgar_zone(at(2891, 3676))).to_be('trollside')
        expect(eadgar_zone(at(2907, 10019))).to_be('trollside')
        expect(eadgar_zone(at(2946, 3369))).to_be('mainland')
        expect(eadgar_zone(at(2611, 3287))).to_be('mainland')
        expect(eadgar_zone(None)).to_be('unknown')
    test('classifies each leg of the route', _fn11)

    def _fn12():
        expect(committed(eadgar_zone(at(2946, 3369)))).to_be(False)
        expect(committed(eadgar_zone(None))).to_be(False)
        for tile in [at(2893, 10074, 2), at(2844, 10057, 1), at(2891, 3676)]:
            expect(committed(eadgar_zone(tile))).to_be(True)
    test('only the mainland is cheap enough to bank from', _fn12)


describe('eadgarZone', _fn10)


def _fn13():
    # Why: every unfinished potion in 2004 displays as "Unfinished potion", so the ranarr vial is
    # only ever safe to address by id.
    def _fn14():
        expect(ER_ITEM.RANARR_VIAL.id).to_be(99)
        expect(ER_ITEM.RANARR_VIAL.name).to_be('Unfinished potion')
    test('the ranarr vial is addressed by id, not by its shared display name', _fn14)

    def _fn15():
        expect(ER_ITEM.GOUTWEED.name).to_be('Goutweed')
        expect(ER_ITEM.DRIED_THISTLE.name).to_be('Dried thistle')
        expect(ER_ITEM.GROUND_THISTLE.name).to_be('Ground thistle')
        expect(ER_ITEM.TROLL_POTION.name).to_be('Troll potion')
        expect(ER_ITEM.ALCO_CHUNKS.name).to_be('Alco-chunks')
        expect(ER_ITEM.DIRTY_ROBE.name).to_be('Dirty robe')
        expect(ER_ITEM.STOREROOM_KEY.name).to_be('Storeroom key')
    test('the quest-issued names match the content obj configs', _fn15)


describe("Eadgar's Ruse item identity", _fn13)
