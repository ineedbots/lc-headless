"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/gertrudescat.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record

from rs2004.quests.defs.gertrudescat import FLUFFS_OBJ, FLUFFS_STAGE, decide, gertrudescat, parse_gertrudes_cat_journal
from rs2004.quests.engine.types import QuestSnapshot
ACCEPTED = "@str@I accepted the challenge of finding Gertrude's lost cat."
SPOKE = "@str@I spoke to Shilop, Gertrude's Son."
FOUND = "@str@I found the lost cat but it won't come back."
FED = '@str@I gave the cat milk and sardines.'
JOURNAL = {
    FLUFFS_STAGE.NOT_STARTED: '@dbl@I can start this quest by talking to @dre@Gertrude@dbl@. She can be found in a house south of the road leading|@dre@west out of Varrock@dbl@.',
    FLUFFS_STAGE.STARTED: f'{ACCEPTED}||@dbl@I need to @dre@speak to Shilop and Wilough@dbl@ at the @dre@marketplace@dbl@.',
    FLUFFS_STAGE.PAID_BOY: f'{ACCEPTED}|{SPOKE}||@dbl@I need to @dre@go to their play area@dbl@ and @dre@find the lost cat and return it to Gertrude@dbl@.',
    FLUFFS_STAGE.GAVE_MILK: f'{ACCEPTED}|{SPOKE}|{FOUND}||@dbl@I still need to @dre@get her to follow me home@dbl@.',
    FLUFFS_STAGE.GAVE_SARDINE: f'{ACCEPTED}|{SPOKE}|{FOUND}|{FED}||@dbl@I still need to @dre@get her to follow me home@dbl@.',
    FLUFFS_STAGE.RESCUED: f'{ACCEPTED}|{SPOKE}|@str@The cat didn\'t follow me back.|{FED}|@str@I gave Fluffs her kitten back.||@dbl@She ran off home.',
    FLUFFS_STAGE.COMPLETE: '@str@I helped Gertrude to find her lost cat,|@str@I fed it and returned her missing kitten,|@str@Gertrude gave me my very own pet for a reward.||@red@QUEST COMPLETE!',
}


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
    progress = (options.progress if 'progress' in options._fields else Record({'stage': (options.stage if options.stage is not None else FLUFFS_STAGE.STARTED), 'flags': set()}))
    inv = counts((options.inv if options.inv is not None else []))
    inv['coins'] = (options.coins if options.coins is not None else 1000)
    return QuestSnapshot(**{
        'journal': (options.journal if options.journal is not None else 'in_progress'),
        'inv': inv,
        'inv_ids': id_counts((options.inv_ids if options.inv_ids is not None else [])),
        'worn': set(),
        'no_progress': 0,
        'bank_coins': 2000000,
        'stage': (progress.stage if progress is not None else None),
        'progress': progress,
        'bank': {},
        'bank_known': True,
        'free_slots': 28,
    })


def custom_name(step):
    return (step.name if step.kind == 'custom' else None)


def journal_case(stage, text):
    def run():
        expect(parse_gertrudes_cat_journal(text).stage).to_be(stage)
    return run


def _fn3():
    for stage, text in JOURNAL.items():
        test(f"reads the stage {stage} page", journal_case(stage, text))

    def _fn5():
        expect((parse_gertrudes_cat_journal(JOURNAL[FLUFFS_STAGE.GAVE_SARDINE]).stage if parse_gertrudes_cat_journal(JOURNAL[FLUFFS_STAGE.GAVE_SARDINE]) is not None else None)).not_.to_be(FLUFFS_STAGE.GAVE_MILK)
        expect((parse_gertrudes_cat_journal(JOURNAL[FLUFFS_STAGE.RESCUED]).stage if parse_gertrudes_cat_journal(JOURNAL[FLUFFS_STAGE.RESCUED]) is not None else None)).not_.to_be(FLUFFS_STAGE.GAVE_SARDINE)
    test('keeps the cumulative pages apart, newest sentence first', _fn5)

    def _fn6():
        expect(parse_gertrudes_cat_journal('some other quest entirely')).to_be_undefined()
    test('returns undefined for a page it cannot place', _fn6)


describe("Gertrude's Cat journal parsing", _fn3)


def _fn7():
    def _fn8():
        expect(decide(snap(Record({'journal': 'unknown'})))).to_equal(Record({'kind': 'wait', 'reason': 'quest journal not loaded'}))
    test('waits while the quest list is still loading', _fn8)

    def _fn9():
        expect(decide(snap(Record({'journal': 'complete'}))).kind).to_be('done')
    test('is done once the quest list turns green', _fn9)

    def _fn10():
        step = decide(snap(Record({'journal': 'not_started'})))
        expect(step.kind).to_be('talk')
        expect(step.kind == 'talk' and step.stop.npc).to_be('Gertrude')
    test('opens with Gertrude when the quest has not started', _fn10)

    def _fn11():
        expect(decide(snap(Record({'progress': None}))).kind).to_be('wait')
    test('waits rather than guessing when the journal stage is unavailable', _fn11)

    def _fn12():
        step = decide(snap(Record({'stage': FLUFFS_STAGE.STARTED, 'coins': 20})))
        expect(step.kind).to_be('withdraw')
        expect(step.kind == 'withdraw' and step.items[0]['name']).to_be('Coins')
    test('tops up coins before walking to the market, since the boy wants 100', _fn12)

    def _fn13():
        expect(custom_name(decide(snap(Record({'stage': FLUFFS_STAGE.STARTED}))))).to_be('buy the play area out of Shilop')
    test('pays the brothers once the coins are in the pack', _fn13)

    def _fn14():
        step = decide(snap(Record({'stage': FLUFFS_STAGE.PAID_BOY})))
        expect(step.kind).to_be('grab_ground')
        expect(step.kind == 'grab_ground' and step.item).to_be('Doogle leaves')
    test('picks the doogle leaves before the walk to Port Sarim', _fn14)

    def _fn15():
        step = decide(snap(Record({'stage': FLUFFS_STAGE.PAID_BOY, 'inv_ids': [FLUFFS_OBJ.doogle_leaves]})))
        expect(step.kind).to_be('buy')
        expect(step.kind == 'buy' and step.shop.npc).to_be('Gerrant')
    test('buys the raw sardine once the leaves are held', _fn15)

    def _fn16():
        step = decide(snap(Record({
        'stage': FLUFFS_STAGE.PAID_BOY,
        'inv_ids': [FLUFFS_OBJ.doogle_leaves, FLUFFS_OBJ.raw_sardine],
        'inv': ['Doogle leaves', 'Raw sardine'],
    })))
        expect(custom_name(step)).to_be('season the sardine with doogle leaves')
    test('seasons the sardine as soon as both halves are in the pack', _fn16)

    # Why: the milk is used first, but its cow is a detour off the Port Sarim road, so the sardine is bought on the way past rather than fetched on a second lap.
    def _fn17():
        step = decide(snap(Record({'stage': FLUFFS_STAGE.PAID_BOY, 'inv_ids': [FLUFFS_OBJ.seasoned_sardine]})))
        expect(step.kind).to_be('grab_ground')
        expect(step.kind == 'grab_ground' and step.item).to_be('Bucket')
    test('fetches the milk only after the sardine is seasoned', _fn17)

    def _fn18():
        step = decide(snap(Record({'stage': FLUFFS_STAGE.PAID_BOY, 'inv_ids': [FLUFFS_OBJ.seasoned_sardine], 'inv': ['Bucket']})))
        expect(step.kind).to_be('use_on')
        expect(step.kind == 'use_on' and step.target).to_be('Cow')
    test('milks a cow once it carries a bucket', _fn18)

    def _fn19():
        step = decide(snap(Record({
        'stage': FLUFFS_STAGE.PAID_BOY,
        'inv_ids': [FLUFFS_OBJ.seasoned_sardine, FLUFFS_OBJ.bucket_of_milk],
        'inv': ['Bucket of milk'],
    })))
        expect(custom_name(step)).to_be('give Fluffs the milk')
    test('climbs to Fluffs with the milk once both are ready', _fn19)

    def _fn20():
        step = decide(snap(Record({'stage': FLUFFS_STAGE.GAVE_MILK})))
        expect(step.kind).to_be('grab_ground')
        expect(step.kind == 'grab_ground' and step.item).to_be('Doogle leaves')
    test('re-sources the sardine after a death that ate it', _fn20)

    def _fn21():
        expect(custom_name(decide(snap(Record({'stage': FLUFFS_STAGE.GAVE_MILK, 'inv_ids': [FLUFFS_OBJ.seasoned_sardine]}))))).to_be('give Fluffs the doogle sardine')
    test('feeds the doogle sardine once the milk is drunk', _fn21)

    def _fn22():
        expect(custom_name(decide(snap(Record({'stage': FLUFFS_STAGE.GAVE_SARDINE}))))).to_be('search the crates for the kitten')
    test('searches the crates once Fluffs has eaten', _fn22)

    def _fn23():
        expect(custom_name(decide(snap(Record({'stage': FLUFFS_STAGE.GAVE_SARDINE, 'inv_ids': [FLUFFS_OBJ.kitten]}))))).to_be('give Fluffs her kitten')
    test('returns the kitten rather than searching on once it is found', _fn23)

    def _fn24():
        expect(custom_name(decide(snap(Record({'stage': FLUFFS_STAGE.RESCUED}))))).to_be('take the news back to Gertrude')
    test('claims the reward from Gertrude once Fluffs has run home', _fn24)


describe("Gertrude's Cat decide", _fn7)


def _fn25():
    def _fn26():
        expect(gertrudescat.record.items).to_equal([])
    test('leaves every consumable off the record, so a resume past a stage refetches nothing', _fn26)

    def _fn27():
        for tool in ['coins', 'bucket', 'doogle leaves', 'sardine', "fluffs' kitten"]:
            expect(gertrudescat.tools).to_contain(tool)
    test('keeps the coins and all four quest items off the deposit list', _fn27)

    def _fn28():
        expect([gertrudescat.bank.x, gertrudescat.bank.z, gertrudescat.bank.level]).to_equal([3185, 3440, 0])
    test('banks in Varrock West, the closest booth to Gertrude and the market', _fn28)


describe("Gertrude's Cat module", _fn25)
