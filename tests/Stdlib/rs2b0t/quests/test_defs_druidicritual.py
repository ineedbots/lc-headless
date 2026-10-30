"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/druidicritual.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot

from rs2004.quests.defs.druidicritual import decide, druidicritual, druidic_ritual_area, DRUIDIC_RITUAL_STAGE, parse_druidic_ritual_journal
MAINLAND = Record({'x': 3220, 'z': 3220, 'level': 0})
DUNGEON = Record({'x': 2888, 'z': 9831, 'level': 0})
ENTRANA_DUNGEON = Record({'x': 2822, 'z': 9774, 'level': 0})
RAW = ['Raw bear meat', 'Raw rat meat', 'Raw chicken', 'Raw beef']
ENCHANTED = ['Enchanted bear', 'Enchanted rat', 'Enchanted chicken', 'Enchanted beef']


def counts(names):
    result = {}
    for name in names:
        key = name.lower()
        _v1 = result.get(key)
        result[key] = ((_v1 if _v1 is not None else 0)) + 1
    return result


def snap(options=None):
    if options is None:
        options = Record({})
    return QuestSnapshot(**{
        'journal': (options.journal if options.journal is not None else 'in_progress'),
        'inv': counts((options.inv if options.inv is not None else [])),
        'worn': set(),
        'no_progress': 0,
        'bank_coins': 2000000,
        'stage': (options.stage if options.stage is not None else DRUIDIC_RITUAL_STAGE.SPOKEN_TO_SANFEW),
        'bank': counts((options.bank if options.bank is not None else [])),
        'bank_known': (options.bank_known if options.bank_known is not None else True),
        'tile': (MAINLAND if options.tile is None else options.tile),
        'free_slots': (options.free_slots if options.free_slots is not None else 28 - (((len(options.inv) if options.inv is not None else None) if (len(options.inv) if options.inv is not None else None) is not None else 0))),
    })


def custom_name(step):
    return (step.name if step.kind == 'custom' else None)


def each_case(body, row):
    def run():
        body(*row)
    return run


def _fn2():
    def _fn3(text, stage):
        expect(parse_druidic_ritual_journal(text)).to_be(stage)
    for row in [
        ['@dbl@I can start this quest by speaking to @dre@Kaqemeex', 0],
        ['I told Kaqemeex I would help them prepare their ceremony.|@dbl@I should speak to @dre@Sanfew', 1],
        [
        '@dre@Sanfew@dbl@ told me for the ritual they would need me to place raw meats in the Cauldron of Thunder',
        2,
    ],
        [
        'The ceremony required various meats being placed in the Cauldron of Thunder. I did this and gave them to Sanfew.|I should speak to Kaqemeex again and claim my reward',
        3,
    ],
        ['@red@QUEST COMPLETE!', 4],
    ]:
        test('maps rendered journal text to exact stage %i' + repr(row), each_case(_fn3, row))

    def _fn4():
        history = 'I told Kaqemeex I would help. Sanfew told me for the ritual what was needed. I did this and gave them to Sanfew.'
        expect(parse_druidic_ritual_journal(history)).to_be(DRUIDIC_RITUAL_STAGE.GIVEN_INGREDIENTS)
    test('matches the newest entry when the journal retains earlier history', _fn4)

    def _fn5():
        expect(parse_druidic_ritual_journal(['Druidic Ritual', 'Loading…'])).to_be_undefined()
    test('does not guess from an unrecognized or loading journal', _fn5)


describe('Druidic Ritual journal stage parsing', _fn2)


def _fn6():
    def _fn7():
        expect(druidic_ritual_area(MAINLAND)).to_be('mainland')
        expect(druidic_ritual_area(DUNGEON)).to_be('dungeon')
        expect(druidic_ritual_area(ENTRANA_DUNGEON)).to_be('mainland')
        expect(druidic_ritual_area(None)).to_be('unknown')
    test('recognizes mainland, dungeon, and a missing player tile', _fn7)

    def _fn8():
        step = decide(snap(Record({'stage': 0})))
        expect(step.kind).to_be('talk')
        if step.kind == 'talk':
            expect(step.stop.npc).to_be('Kaqemeex')
            expect(step.stop.prefer).to_equal(["I'm in search of a quest.", 'Ok, I will try and help.'])
    test('starts with Kaqemeex using both exact choices', _fn8)

    def _fn9():
        step = decide(snap(Record({'stage': 1})))
        expect(step.kind).to_be('talk')
        if step.kind == 'talk':
            expect(step.stop.npc).to_be('Sanfew')
            expect(step.stop.anchor.level).to_be(1)
            expect(step.stop.prefer).to_equal(["I've been sent to help purify the Varrock stone circle.", "Ok, I'll do that then."])
    test('continues stage 1 with upstairs Sanfew using both exact choices', _fn9)

    def _fn10():
        reward = decide(snap(Record({'stage': 3, 'inv': []})))
        expect(reward.kind == 'talk' and reward.stop.npc).to_be('Kaqemeex')
        expect(decide(snap(Record({'stage': 4}))).kind).to_be('done')
        expect(decide(snap(Record({'stage': 0, 'journal': 'complete'}))).kind).to_be('done')
    test('returns to Kaqemeex at stage 3 and finishes at stage 4', _fn10)

    def _fn11():
        expect(decide(snap(Record({'journal': 'unknown'}))).kind).to_be('wait')
        unavailable = snap()
        unavailable.stage = None
        expect(decide(unavailable)).to_equal(Record({'kind': 'wait', 'reason': 'Druidic Ritual stage unavailable'}))
    test('waits safely for unknown journal or unavailable stage state', _fn11)


describe('Druidic Ritual stage routing', _fn6)


def _fn12():
    def _fn13():
        step = decide(snap(Record({'bank_known': False})))
        expect(step.kind).to_be('scan_bank')
        expect(step.kind == 'scan_bank' and step.bank).to_be_defined()
    test('checks an unknown bank before sourcing any absent meat', _fn13)

    def _fn14():
        step = decide(snap(Record({'inv': ['Raw bear meat'], 'bank': ['Enchanted rat', 'Raw chicken', 'Enchanted beef']})))
        expect(step.kind).to_be('withdraw')
        expect(step.kind == 'withdraw' and step.items).to_equal([
        {'name': 'Enchanted rat', 'qty': 1},
        {'name': 'Raw chicken', 'qty': 1},
        {'name': 'Enchanted beef', 'qty': 1},
    ])
    test('prefers banked enchanted forms and otherwise withdraws raw forms', _fn14)

    def _fn15(enchanted, raw):
        others = [name for name in ENCHANTED if name != enchanted]
        step = decide(snap(Record({'inv': [enchanted] + list(others)})))
        expect(step.kind).to_be('talk')
        expect(step.kind == 'talk' and step.stop.npc).to_be('Sanfew')
        expect(repr(step)).not_.to_contain(raw)
    for row in [
        ['Enchanted bear', 'Raw bear meat'],
        ['Enchanted rat', 'Raw rat meat'],
        ['Enchanted chicken', 'Raw chicken'],
        ['Enchanted beef', 'Raw beef'],
    ]:
        test('%s satisfies its species without reacquiring %s' + repr(row), each_case(_fn15, row))

    def _fn16(npc, raw):
        index = (RAW.index(raw) if raw in RAW else -1)
        held = [name for i, name in enumerate(ENCHANTED) if i != index]
        step = decide(snap(Record({'inv': held})))
        expect(custom_name(step)).to_be(f'hunt {npc} for {raw}')
    for row in [
        ['Bear', 'Raw bear meat'],
        ['Giant rat', 'Raw rat meat'],
        ['Chicken', 'Raw chicken'],
        ['Cow', 'Raw beef'],
    ]:
        test('hunts %s when %s is absent from both inventory and bank' + repr(row), each_case(_fn16, row))

    def _fn17():
        dirty = list(RAW[0:3]) + list(['Bones'] * 25)
        step = decide(snap(Record({'inv': dirty, 'bank': ['Enchanted beef'], 'free_slots': 0})))
        expect(step.kind).to_be('deposit')
        if step.kind == 'deposit':
            expect(step.exact_keep).to_be(True)
            expect(step.keep).to_contain('raw beef')
            expect(step.keep).to_contain('enchanted beef')
    test('cleans a full dirty pack before a withdrawal or hunt', _fn17)

    def _fn18():
        full = ['Raw bear meat'] * 28
        step = decide(snap(Record({'inv': full, 'free_slots': 0})))
        expect(step.kind).to_be('deposit')
        expect(step.kind == 'deposit' and step.keep).to_equal([])
        expect(step.kind == 'deposit' and step.exact_keep).to_be(True)
    test('banks duplicate quest forms instead of parking when only they fill the pack', _fn18)


describe('Druidic Ritual item recovery', _fn12)


def _fn19():
    def _fn20():
        step = decide(snap(Record({'inv': RAW})))
        expect(custom_name(step)).to_be('dip Raw bear meat in the Cauldron of Thunder')
    test('enters the dungeon and dips one exact raw form at a time', _fn20)

    def _fn21():
        step = decide(snap(Record({'inv': ['Enchanted bear', 'Raw rat meat', 'Enchanted chicken', 'Raw beef'], 'tile': DUNGEON})))
        expect(custom_name(step)).to_be('dip Raw rat meat in the Cauldron of Thunder')
    test('continues from a partial enchanted/raw state inside the dungeon', _fn21)

    def _fn22():
        step = decide(snap(Record({'inv': ['Enchanted bear', 'Raw rat meat', 'Raw chicken'], 'bank': ['Raw beef'], 'tile': DUNGEON})))
        expect(custom_name(step)).to_be('leave the dungeon to recover missing ritual meat')
    test('leaves the dungeon before consulting the bank for a missing species', _fn22)

    def _fn23():
        complete_set = decide(snap(Record({'inv': ENCHANTED, 'tile': DUNGEON})))
        expect(complete_set.kind == 'talk' and complete_set.stop.npc).to_be('Sanfew')
        split = decide(snap(Record({'inv': ENCHANTED[0:3], 'bank': [ENCHANTED[3]]})))
        expect(split.kind == 'withdraw' and split.items).to_equal([{'name': 'Enchanted beef', 'qty': 1}])
    test('hands in only when all four enchanted meats are simultaneously held', _fn23)

    def _fn24():
        step = decide(snap(Record({'inv': ENCHANTED[0:3]})))
        expect(custom_name(step)).to_be('hunt Cow for Raw beef')
    test('a lost enchanted item is naturally reacquired as its raw counterpart', _fn24)


describe('Druidic Ritual cauldron and restart states', _fn19)


def _fn25():
    def _fn26():
        expect(druidicritual.record.id).to_be('druid')
        expect([item.name for item in druidicritual.record.items]).to_equal(['Raw bear meat', 'Raw beef', 'Raw chicken', 'Raw rat meat'])
        expect(druidicritual.owns_inventory).to_be(True)
        expect(druidicritual.read_stage).to_be_defined()
        expect(druidicritual.hops).to_have_length(2)
        expect(druidicritual.grind).to_equal(['Bear', 'Giant rat', 'Chicken', 'Cow', 'Suit of armour'])
    test('owns inventory and supplies exact dungeon transport and combat metadata', _fn26)


describe('Druidic Ritual module wiring', _fn25)
