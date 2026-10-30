"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/hazeelcult.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record

from rs2004.quests.defs.hazeelcult import ARMOUR_OBJ, HC_STAGE, at_cave_mouth, decide, hazeelcult, in_hideout, parse_hazeel_journal
from rs2004.quests.engine.types import QuestSnapshot
from rs2004.quests.defs import QUEST_DEFS
NOT_STARTED = '@dbl@I can start this quest by talking to @dre@Sir Ceril Carnillean@dbl@ at the house due @dre@West@dbl@ of @dre@Ardougne Zoo'
PREAMBLE = '@str@I spoke to Sir Ceril Carnillean at his house, and|@str@agreed to help him investigate the theft of a|@str@family heirloom.'
STARTED = PREAMBLE + '|@dbl@The @dre@Cult@dbl@ who were responsible live in a cave @dre@South@dbl@ of the|' + '@dre@Carnillean Mansion near the start of the forest|'
FOUND_CLIVET = PREAMBLE + "|@str@I found a member of the cult called Clivet at the entrance|@str@to the cult's hideout, south of Ardougne.|"
SPOKEN_CLIVET = FOUND_CLIVET + '@dbl@He told me a pack of lies about the Carnilleans, then asked me to join the cult. Obviously, I refused.|' + 'I was still no closer to recovering the @dre@missing armour'
REFUSED_LINES = '@str@He told me a pack of lies about the Carnilleans, then asked|' + '@str@me to join the cult. Obviously, I refused.|' + '@str@I was still no closer to recovering the missing armour|'
REFUSED_CULT = FOUND_CLIVET + REFUSED_LINES + '@dbl@After speaking to him, he jumped onto a @dre@raft@dbl@ and headed into the @dre@sewer system@dbl@. I need to find a way to follow.'
KILLED_LINES = '@str@I managed to enter the hideout, kill the cult leader and|' + '@str@retrieve the armour. I discovered that Jones the Butler|' + '@str@was secretly a member of the cult and a traitor.|'
KILLED_ALOMONE = FOUND_CLIVET + REFUSED_LINES + KILLED_LINES + "@dbl@I should return @dre@Ceril's armour@dbl@ and tell him about @dre@Jones"
RETURNED_LINES = "@str@I returned the armour, but Ceril didn't believe Jones was|" + '@str@involved with the cult and was responsible for the theft.|'
RETURNED_ARMOUR = FOUND_CLIVET + REFUSED_LINES + KILLED_LINES + RETURNED_LINES + '@dbl@I have to find some @dre@evidence@dbl@ linking @dre@Butler Jones@dbl@ to the @dre@Cult@dbl@ so that I can @dre@clear my name@dbl@ and claim my @dre@reward'
COMPLETE = FOUND_CLIVET + REFUSED_LINES + KILLED_LINES + RETURNED_LINES + '@str@I found undeniable evidence that the Butler was involved|' + '@str@with the cult and gave it to Ceril. My name was cleared|' + '@str@and I graciously accepted the reward for all of my help.|||@red@QUEST COMPLETE!'
EVIL_JOINED = FOUND_CLIVET + "@dre@Clivet@dbl@ told me the truth about the @dre@Carnilleans@dbl@, and I decided I would help them in their revenge. He gave me some @dre@poison@dbl@ to put into the @dre@family's food"
EVIL_POISONED = FOUND_CLIVET + '@str@Having decided to assist the cult in their mission|@str@to revive Hazeel, I have poisoned some food to|@str@try and poison the Carnilleans.|' + '@str@I spoke to Clivet and he told me that I had failed, but he|@str@gave me an amulet anyway.|' + '@dbl@By turning the @dre@sewer valves@dbl@ in the directions shown by the @dre@amulet@dbl@, I can take the @dre@sewer raft@dbl@ to the hideout'
EVIL_BRIEFED = FOUND_CLIVET + '@str@Having decided to assist the cult in their mission|@str@to revive Hazeel, I have poisoned some food to|@str@try and poison the Carnilleans.|' + '@str@I spoke to Clivet and he told me that I had failed, but he|@str@gave me an amulet anyway.|' + '@str@Then I managed to take the sewer rafts to the cult hideout.|' + '@dre@Alomone@dbl@ told me to find a @dre@spell scroll@dbl@ that is hidden somewhere within the @dre@Carnillean household|'


def id_counts(ids):
    result = {}
    for id in ids:
        _v1 = result.get(id)
        result[id] = ((_v1 if _v1 is not None else 0)) + 1
    return result


def snap(options=None):
    if options is None:
        options = Record({})
    progress = (options.progress if 'progress' in options._fields else Record({
        'stage': (options.stage if options.stage is not None else HC_STAGE.STARTED),
        'flags': set((['evil'] if options.evil else [])),
    }))
    return QuestSnapshot(**{
        'journal': (options.journal if options.journal is not None else 'in_progress'),
        'inv': {},
        'inv_ids': id_counts((options.inv_ids if options.inv_ids is not None else [])),
        'worn': set(),
        'worn_ids': set((options.worn_ids if options.worn_ids is not None else [])),
        'no_progress': 0,
        'bank_coins': 2000000,
        'stage': (progress.stage if progress is not None else None),
        'progress': progress,
        'bank': {},
        'bank_ids': id_counts((options.bank_ids if options.bank_ids is not None else [])),
        'bank_known': (options.bank_known if options.bank_known is not None else True),
        'free_slots': 28,
    })


def custom_name(step):
    return (step.name if step.kind == 'custom' else None)


def _fn2():
    def _fn3():
        expect((parse_hazeel_journal(NOT_STARTED).stage if parse_hazeel_journal(NOT_STARTED) is not None else None)).to_be(HC_STAGE.NOT_STARTED)
    test('reads the not-started page', _fn3)

    def _fn4():
        expect((parse_hazeel_journal(STARTED).stage if parse_hazeel_journal(STARTED) is not None else None)).to_be(HC_STAGE.STARTED)
    test('reads the page that only points at the forest cave', _fn4)

    def _fn5():
        expect((parse_hazeel_journal(SPOKEN_CLIVET).stage if parse_hazeel_journal(SPOKEN_CLIVET) is not None else None)).to_be(HC_STAGE.SPOKEN_CLIVET)
        expect((parse_hazeel_journal(REFUSED_CULT).stage if parse_hazeel_journal(REFUSED_CULT) is not None else None)).to_be(HC_STAGE.REFUSED_CULT)
    test('separates a first word with Clivet from the refusal that follows it', _fn5)

    def _fn6():
        expect((parse_hazeel_journal(KILLED_ALOMONE).stage if parse_hazeel_journal(KILLED_ALOMONE) is not None else None)).to_be(HC_STAGE.KILLED_ALOMONE)
        expect((parse_hazeel_journal(RETURNED_ARMOUR).stage if parse_hazeel_journal(RETURNED_ARMOUR) is not None else None)).to_be(HC_STAGE.RETURNED_ARMOUR)
    test('reads the kill and the hand-over apart, though the page keeps both', _fn6)

    def _fn7():
        expect((parse_hazeel_journal(COMPLETE).stage if parse_hazeel_journal(COMPLETE) is not None else None)).to_be(HC_STAGE.COMPLETE)
    test('reads the finished page as complete', _fn7)

    def _fn8():
        for page in [EVIL_JOINED, EVIL_POISONED, EVIL_BRIEFED]:
            expect(('evil' in (parse_hazeel_journal(page).flags if parse_hazeel_journal(page) is not None else None))).to_be(True)
    test('flags every cult-side page, so no leg mistakes one for the Carnillean side', _fn8)

    def _fn9():
        for page in [STARTED, SPOKEN_CLIVET, REFUSED_CULT, KILLED_ALOMONE, RETURNED_ARMOUR]:
            expect(('evil' in (parse_hazeel_journal(page).flags if parse_hazeel_journal(page) is not None else None))).to_be(False)
    test('leaves no Carnillean-side page flagged as the cult side', _fn9)

    def _fn10():
        expect(parse_hazeel_journal('some other quest entirely')).to_be_undefined()
    test('returns undefined for a page it cannot place', _fn10)


describe('Hazeel Cult journal parsing', _fn2)


def _fn11():
    def _fn12():
        expect(decide(snap(Record({'journal': 'unknown'})))).to_equal(Record({'kind': 'wait', 'reason': 'quest journal not loaded'}))
    test('waits while the quest list is still loading', _fn12)

    def _fn13():
        expect(decide(snap(Record({'journal': 'complete'}))).kind).to_be('done')
    test('is done once the quest list turns green', _fn13)

    def _fn14():
        expect(decide(snap(Record({'progress': None}))).kind).to_be('wait')
    test('waits rather than guessing when the journal stage is unavailable', _fn14)

    def _fn15():
        expect(custom_name(decide(snap(Record({'stage': HC_STAGE.NOT_STARTED}))))).to_be('ask Ceril Carnillean about the stolen armour')
    test('opens with Ceril when the quest has not started', _fn15)

    def _fn16():
        for stage in [HC_STAGE.STARTED, HC_STAGE.SPOKEN_CLIVET]:
            expect(custom_name(decide(snap(Record({'stage': stage}))))).to_be('refuse Clivet at the cult cave')
    test('refuses Clivet from either of the two stages that offer the choice', _fn16)

    def _fn17():
        expect(custom_name(decide(snap(Record({'stage': HC_STAGE.REFUSED_CULT}))))).to_be('take the Carnillean armour from the cult hideout')
    test('goes for the armour once the side is locked in', _fn17)

    def _fn18():
        expect(custom_name(decide(snap(Record({'stage': HC_STAGE.KILLED_ALOMONE, 'inv_ids': [ARMOUR_OBJ]}))))).to_be('return the armour to Ceril upstairs')
    test('returns the armour it is carrying rather than riding back in', _fn18)

    def _fn19():
        expect(custom_name(decide(snap(Record({'stage': HC_STAGE.KILLED_ALOMONE, 'worn_ids': [ARMOUR_OBJ]}))))).to_be('return the armour to Ceril upstairs')
    test('counts a worn suit as carried', _fn19)

    def _fn20():
        expect(decide(snap(Record({'stage': HC_STAGE.KILLED_ALOMONE, 'bank_known': False}))).kind).to_be('scan_bank')
    test('reads the bank before believing the armour is gone', _fn20)

    def _fn21():
        step = decide(snap(Record({'stage': HC_STAGE.KILLED_ALOMONE, 'bank_ids': [ARMOUR_OBJ]})))
        expect(step.kind).to_be('withdraw')
        expect(step.kind == 'withdraw' and step.items[0]['id']).to_be(ARMOUR_OBJ)
    test('withdraws a banked suit, since a banked copy stops Alomone dropping another', _fn21)

    def _fn22():
        expect(custom_name(decide(snap(Record({'stage': HC_STAGE.KILLED_ALOMONE}))))).to_be('take the Carnillean armour from the cult hideout')
    test('rides back in when the armour is nowhere', _fn22)

    def _fn23():
        expect(custom_name(decide(snap(Record({'stage': HC_STAGE.RETURNED_ARMOUR}))))).to_be("search Jones' cupboard for the evidence")
    test('searches the cupboard once the armour is handed over', _fn23)

    def _fn24():
        step = decide(snap(Record({'stage': HC_STAGE.POURED_POISON, 'evil': True})))
        expect(step.kind).to_be('wait')
        expect(step.kind == 'wait' and step.reason).to_contain('joined the cult')
    test('stops rather than guessing on a save that joined the cult', _fn24)


describe('Hazeel Cult decide', _fn11)


def _fn25():
    def _fn26():
        expect(in_hideout(Record({'x': 2606, 'z': 9692}))).to_be(True)
        expect(in_hideout(Record({'x': 2609, 'z': 9669}))).to_be(True)
        for island in [
        Record({'x': 2578, 'z': 9687}),
        Record({'x': 2593, 'z': 9694}),
        Record({'x': 2599, 'z': 9712}),
        Record({'x': 2616, 'z': 9725}),
    ]:
            expect(in_hideout(island)).to_be(False)
    test('the hideout box holds the raft landing and Alomone but no sewer island', _fn26)

    def _fn27():
        expect(at_cave_mouth(Record({'x': 2570, 'z': 9682}))).to_be(True)
        expect(at_cave_mouth(Record({'x': 2567, 'z': 9680}))).to_be(True)
        expect(at_cave_mouth(Record({'x': 2570, 'z': 9668}))).to_be(False)
        expect(at_cave_mouth(Record({'x': 2578, 'z': 9687}))).to_be(False)
    test('the cave mouth box excludes the mansion cellar, which shares the mapsquare', _fn27)

    def _fn28():
        expect(in_hideout(Record({'x': 2606, 'z': 3292}))).to_be(False)
        expect(at_cave_mouth(Record({'x': 2570, 'z': 3282}))).to_be(False)
    test('neither box claims a tile above ground', _fn28)


describe('Hazeel Cult areas', _fn25)


def _fn29():
    def _fn30():
        stands = [f'{h.stand.x},{h.stand.z}' for h in ((hazeelcult.hops if hazeelcult.hops is not None else []))]
        expect(sorted(stands)).to_equal(['2570,9682', '2585,3233'])
    test('names only the two crossings the walker may pick for itself', _fn30)

    def _fn31():
        expect(hazeelcult.tools).to_contain('carnillean armour')
    test('keeps the armour off the deposit list', _fn31)

    def _fn32():
        expect(hazeelcult.record.items).to_equal([])
    test('declares no items, so a resume mid-quest fetches nothing it cannot buy', _fn32)

    def _fn33():
        order = [d.record.id for d in QUEST_DEFS]
        expect((order.index('hazeelcult') if 'hazeelcult' in order else -1)).to_be_greater_than((order.index('elena') if 'elena' in order else -1))
    test('runs after Plague City, whose teleport pays for the Ardougne legs', _fn33)


describe('Hazeel Cult module', _fn29)
