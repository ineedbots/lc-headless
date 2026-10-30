"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/clocktower.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record

from rs2004.quests.defs.clocktower import COG_OBJ, COG_STAGE, clocktower, decide, parse_clock_tower_journal
from rs2004.quests.engine.types import QuestSnapshot
NOT_STARTED = '@dbl@I can start this quest by talking to @dre@Brother Kojo@dbl@ at the|@dre@Clock Tower@dbl@ which is located @dre@South@dbl@ of @dre@Ardougne|'
PREAMBLE = '@str@I spoke to Brother Kojo at the Clock Tower South of|@str@Argougne and agreed to help him repair the clock.|' + '@dbl@To repair the clock I need to find the four coloured cogs|and place them on the four correctly coloured spindles.|'
UNPLACED = Record({
    'blue': "@dbl@I haven't placed the @dre@Blue Cog@dbl@ on its @dre@spindle@dbl@ yet|",
    'black': "@dbl@I haven't placed the @dre@Black Cog@dbl@ on its @dre@spindle@dbl@ yet|",
    'white': "@dbl@I haven't placed the @dre@White Cog@dbl@ on its @dre@spindle@dbl@ yet|",
    'red': "@dbl@I haven't placed the @dre@Red Cog@dbl@ on its @dre@spindle@dbl@ yet",
})
PLACED = Record({
    'blue': '@str@I have successfully placed the Blue Cog on its spindle|',
    'black': '@str@I have successfully placed the Black Cog on its spindle|',
    'white': '@str@I have successfully placed the White Cog on its spindle|',
    'red': '@str@I have successfully placed the Red Cog on its spindle',
})


def in_progress(placed):
    order = ['blue', 'black', 'white', 'red']
    return PREAMBLE + ''.join([((PLACED.get(c) if (c in placed) else UNPLACED.get(c))) for c in order])


ALL_PLACED = '@str@I spoke to Brother Kojo at the Clock Tower South of|@str@Argougne and agreed to help him repair the clock.|' + '@str@I have placed all four cogs successfully on the spindles.|' + '@dbl@I should speak to @dre@Brother Kojo@dbl@ and claim my @dre@reward'
COMPLETE = '@str@I spoke to Brother Kojo at the Clock Tower South of|@str@Argougne and agreed to help him repair the clock.|' + '@str@I have placed all four cogs successfully on the spindles.|' + '@str@Brother Kojo was grateful for all my help and rewarded me.||@red@QUEST COMPLETE!'


def counts(names):
    result = {}
    for name in names:
        key = name.lower()
        _v1 = result.get(key)
        result[key] = ((_v1 if _v1 is not None else 0)) + 1
    return result


def id_counts(ids):
    result = {}
    for id in ids:
        _v2 = result.get(id)
        result[id] = ((_v2 if _v2 is not None else 0)) + 1
    return result


def snap(options=None):
    if options is None:
        options = Record({})
    placed = (options.placed if options.placed is not None else [])
    progress = (options.progress if 'progress' in options._fields else Record({
        'stage': (options.stage if options.stage is not None else COG_STAGE.STARTED),
        'flags': set([f'placed-{c}' for c in placed]),
    }))
    return QuestSnapshot(**{
        'journal': (options.journal if options.journal is not None else 'in_progress'),
        'inv': counts((options.inv if options.inv is not None else [])),
        'inv_ids': id_counts((options.inv_ids if options.inv_ids is not None else [])),
        'worn': set(),
        'no_progress': 0,
        'bank_coins': 2000000,
        'stage': (progress.stage if progress is not None else None),
        'progress': progress,
        'bank': counts((options.bank if options.bank is not None else [])),
        'bank_known': (options.bank_known if options.bank_known is not None else True),
        'free_slots': 28,
    })


def custom_name(step):
    return (step.name if step.kind == 'custom' else None)


def _fn3():
    def _fn4():
        progress = parse_clock_tower_journal(NOT_STARTED)
        expect((progress.stage if progress is not None else None)).to_be(COG_STAGE.NOT_STARTED)
        _v5 = (progress.flags if progress is not None else None)
        expect(list(((_v5 if _v5 is not None else [])))).to_equal([])
    test('reads the not-started page as stage 0 with no cogs placed', _fn4)

    def _fn6():
        progress = parse_clock_tower_journal(in_progress([]))
        expect((progress.stage if progress is not None else None)).to_be(COG_STAGE.STARTED)
        _v7 = (progress.flags if progress is not None else None)
        expect(list(((_v7 if _v7 is not None else [])))).to_equal([])
    test('reads a started page with nothing placed as stage 1 and no flags', _fn6)

    def _fn8():
        progress = parse_clock_tower_journal(in_progress(['blue', 'red']))
        expect((progress.stage if progress is not None else None)).to_be(COG_STAGE.STARTED)
        expect(('placed-blue' in (progress.flags if progress is not None else None))).to_be(True)
        expect(('placed-red' in (progress.flags if progress is not None else None))).to_be(True)
        expect(('placed-black' in (progress.flags if progress is not None else None))).to_be(False)
        expect(('placed-white' in (progress.flags if progress is not None else None))).to_be(False)
    test('flags only the cogs the page reports as placed', _fn8)

    def _fn9():
        progress = parse_clock_tower_journal(ALL_PLACED)
        expect((progress.stage if progress is not None else None)).to_be(COG_STAGE.ALL_PLACED)
        _v10 = (progress.flags if progress is not None else None)
        expect(sorted(list(((_v10 if _v10 is not None else []))))).to_equal(['placed-black', 'placed-blue', 'placed-red', 'placed-white'])
    test('treats the reward page as all four placed, since it drops the per-cog lines', _fn9)

    def _fn11():
        expect((parse_clock_tower_journal(COMPLETE).stage if parse_clock_tower_journal(COMPLETE) is not None else None)).to_be(COG_STAGE.COMPLETE)
    test('reads the finished page as complete', _fn11)

    def _fn12():
        expect(parse_clock_tower_journal('some other quest entirely')).to_be_undefined()
    test('returns undefined for a page it cannot place', _fn12)


describe('Clock Tower journal parsing', _fn3)


def _fn13():
    def _fn14():
        expect(decide(snap(Record({'journal': 'unknown'})))).to_equal(Record({'kind': 'wait', 'reason': 'quest journal not loaded'}))
    test('waits while the quest list is still loading', _fn14)

    def _fn15():
        expect(decide(snap(Record({'journal': 'complete'}))).kind).to_be('done')
    test('is done once the quest list turns green', _fn15)

    def _fn16():
        step = decide(snap(Record({'journal': 'not_started'})))
        expect(step.kind).to_be('talk')
        expect(step.kind == 'talk' and step.stop.npc).to_be('Brother Kojo')
    test('opens with Brother Kojo when the quest has not started', _fn16)

    def _fn17():
        expect(decide(snap(Record({'progress': None}))).kind).to_be('wait')
    test('waits rather than guessing when the journal stage is unavailable', _fn17)

    def _fn18():
        step = decide(snap(Record({'placed': ['blue', 'black', 'white', 'red']})))
        expect(step.kind).to_be('talk')
        expect(step.kind == 'talk' and step.stop.npc).to_be('Brother Kojo')
    test('returns to Kojo for the reward once all four are placed', _fn18)

    def _fn19():
        step = decide(snap(Record({'inv_ids': [COG_OBJ.red], 'inv': ['Cog', 'Bucket of water']})))
        expect(custom_name(step)).to_be('place the red cog')
    test('places the cog it is carrying before fetching another', _fn19)

    def _fn20():
        step = decide(snap(Record({'inv_ids': [COG_OBJ.white], 'inv': ['Cog', 'Bucket of water']})))
        expect(custom_name(step)).to_be('place the white cog')
    test('tells the four cogs apart by object id rather than by their shared name', _fn20)

    def _fn21():
        step = decide(snap(Record({'inv': ['Bucket']})))
        expect(step).to_match_object(Record({
        'kind': 'use_on',
        'item': 'Bucket',
        'target_kind': 'loc',
        'target': 'Well',
        'product': 'Bucket of water',
    }))
        expect([step.anchor.x, step.anchor.z]).to_equal([2611, 3254])
    test('fills a bucket before the black cog leg, since the cog is too hot to lift', _fn21)

    def _fn22():
        step = decide(snap(Record({})))
        expect(step.kind).to_be('grab_ground')
        expect(step.kind == 'grab_ground' and step.item).to_be('Bucket')
    test('fetches a bucket from the ground when the bank has been read and holds none', _fn22)

    def _fn23():
        step = decide(snap(Record({'bank': ['Bucket']})))
        expect(step.kind).to_be('withdraw')
        expect(step.kind == 'withdraw' and step.items[0]['name']).to_be('Bucket')
    test('takes the banked bucket rather than the single ground spawn', _fn23)

    def _fn24():
        expect(decide(snap(Record({'bank_known': False}))).kind).to_be('scan_bank')
    test('reads the bank before believing it has no bucket', _fn24)

    def _fn25():
        expect(custom_name(decide(snap(Record({'inv': ['Bucket of water']}))))).to_be('fetch the black cog')
    test('fetches the black cog once the water is carried', _fn25)

    def _fn26():
        expect(custom_name(decide(snap(Record({'placed': ['black']}))))).to_be('fetch the red cog')
    test('needs no bucket once the black cog is placed', _fn26)

    def _fn27():
        expect(custom_name(decide(snap(Record({'placed': ['black', 'red', 'blue']}))))).to_be('fetch the white cog')
    test('leaves the white cog last, since its leg has to poison the rats first', _fn27)

    def _fn28():
        step = decide(snap(Record({'placed': ['red'], 'inv_ids': [COG_OBJ.red], 'inv': ['Cog']})))
        expect(step.kind).to_be('wait')
    test('stops rather than looping when it holds a cog whose spindle is already filled', _fn28)


describe('Clock Tower decide', _fn13)


def _fn29():
    def _fn30():
        expect(clocktower.record.items).to_equal([])
    test('leaves the bucket off the record, so a resume past the black cog fetches no water', _fn30)

    def _fn31():
        for tool in ['cog', 'rat poison', 'bucket', 'bucket of water']:
            expect(clocktower.tools).to_contain(tool)
    test('keeps every cog and the poison off the deposit list', _fn31)

    def _fn32():
        stands = [f'{h.stand.x},{h.stand.z}' for h in ((clocktower.hops if clocktower.hops is not None else []))]
        expect(sorted(stands)).to_equal(['2566,3243', '2566,9643'])
    test('hops name the cellar ladder alone, since a sealed room is nearer than it from most of the dungeon', _fn32)


describe('Clock Tower module', _fn29)
