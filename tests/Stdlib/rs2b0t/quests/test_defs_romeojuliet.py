"""rs2b0t's test/api/ai/quests/defs/romeojuliet.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs.record import Record
from rs2004.quests.defs.romeojuliet import ROMEO_JULIET_ITEM, ROMEO_JULIET_STAGE, decide, parse_romeo_juliet_journal, romeojuliet
from rs2004.quests.engine.types import QuestSnapshot

VARROCK = Record({'x': 3211, 'z': 3425, 'level': 0})
FAR_AWAY = Record({'x': 3000, 'z': 3200, 'level': 0})
ITEM_IDS = {}
for _item in ROMEO_JULIET_ITEM.values():
    ITEM_IDS[_item['name'].lower()] = _item['id']


def name_counts(names):
    result = {}
    for name in names:
        key = name.lower()
        result[key] = result.get(key, 0) + 1
    return result


def id_counts(names):
    result = {}
    for name in names:
        id = ITEM_IDS.get(name.lower())
        if id is not None:
            result[id] = result.get(id, 0) + 1
    return result


def snap(options=None):
    o = options or {}
    inv = o.get('inv', [])
    bank = o.get('bank', [])
    return QuestSnapshot().with_fields({
        'journal': o.get('journal', 'in_progress'),
        'inv': name_counts(inv),
        'inv_ids': o['inv_ids'] if 'inv_ids' in o else id_counts(inv),
        'worn': set(),
        'no_progress': o.get('no_progress', 0),
        'bank_coins': 0,
        'stage': o.get('stage', ROMEO_JULIET_STAGE.SPOKEN_TO_FATHER),
        'bank': name_counts(bank),
        'bank_ids': o['bank_ids'] if 'bank_ids' in o else id_counts(bank),
        'bank_known': o.get('bank_known', True),
        'tile': o['tile'] if 'tile' in o else VARROCK,
        'free_slots': o.get('free_slots', 28 - len(inv)),
    })


def custom_name(step):
    return (step.name if step.kind == 'custom' else None)


def bank_item(step):
    return step.items[0] if step.kind == 'withdraw' else None


JOURNALS = [
    ['@dbl@I can start this quest by talking to @dre@Romeo@dbl@ in @dre@Varrock|@dre@Square@dbl@.', 0],
    ['I have agreed to find Juliet.|@dbl@I should go and speak to @dre@Juliet@dbl@. I can find her west of Varrock.', 10],
    ['Juliet gave me a message.|@dbl@I should take the @dre@message@dbl@ from @dre@Juliet@dbl@ to @dre@Romeo@dbl@.', 20],
    ['I delivered the message to Romeo.|@dbl@I should find @dre@Father Lawrence@dbl@ and see how we can help', 30],
    ['I found Father Lawrence.|@dbl@I need to find the @dre@Apothecary@dbl@ to make a @dre@cadaver potion@dbl@.', 40],
    ['@str@I went to the Apothecary regarding making this cadava|@str@potion, and he told me to bring him some cadava berries.|@dbl@I will have to find some @dre@cadava berries@dbl@.', 50],
    ["After the Apothecary made me the potion, I delivered it to Juliet.|@dbl@I have to find @dre@Romeo@dbl@ and tell him what's happened.", 60],
    ['I told Romeo what was going to happen.|@red@QUEST COMPLETE!', 100],
]

SUFFIXES = [
    'I should take these cadava berries to the Apothecary.',
    'I should take this cadava potion to Juliet.',
    'I will have to find some cadava berries.',
]

ROUTES = [
    [0, [], 'stage 0: ask Romeo how to help find Juliet'],
    [10, [], "stage 10: ask Juliet for Romeo's message"],
    [20, ['Message'], "stage 20: deliver Juliet's message to Romeo"],
    [30, [], 'stage 30: ask Father Lawrence for help'],
    [40, [], 'stage 40: ask the Apothecary for a Cadava potion'],
    [50, ['Cadava berries'], 'stage 50: exchange Cadava berries with the Apothecary'],
    [50, ['Cadava potion'], 'stage 50: deliver the Cadava potion to Juliet'],
    [60, [], 'stage 60: tell Romeo that Juliet took the potion'],
]


def parses_as(text, stage):
    def body():
        expect(parse_romeo_juliet_journal(text)).to_be(stage)
    return body


def keeps_fifty(suffix):
    def body():
        history = f'I should find Father Lawrence. I need to find the Apothecary. I went to the Apothecary regarding making this cadava potion, and he told me to bring him some cadava berries. {suffix}'
        expect(parse_romeo_juliet_journal(history)).to_be(ROMEO_JULIET_STAGE.SPOKEN_TO_APOTHECARY)
    return body


def routes(stage, inv, expected):
    def body():
        expect(custom_name(decide(snap({'stage': stage, 'inv': inv})))).to_be(expected)
    return body


def _fn3():
    for _text, _stage in JOURNALS:
        test(f'maps the rendered journal to exact stage {_stage}', parses_as(_text, _stage))

    def _fn5():
        legacy = 'I went to the Apothecary regarding making this cadaver potion, and he told me to bring him some cadaver berries.'
        expect(parse_romeo_juliet_journal(legacy)).to_be(ROMEO_JULIET_STAGE.SPOKEN_TO_APOTHECARY)
    test('also parses the legacy journal spelling deployed by older servers', _fn5)

    for _suffix in SUFFIXES:
        test(f'keeps dynamic Apothecary-stage journal suffixes at stage 50: {_suffix}', keeps_fifty(_suffix))

    def _fn7():
        history = "I should go and speak to Juliet. I should take the message to Romeo. I should find Father Lawrence. I need to find the Apothecary. I went to the Apothecary regarding making this cadaver potion. I have to find Romeo and tell him what's happened."
        expect(parse_romeo_juliet_journal(history)).to_be(ROMEO_JULIET_STAGE.JULIET_IN_CRYPT)
    test('matches the newest milestone when the journal retains all earlier history', _fn7)

    def _fn8():
        expect(parse_romeo_juliet_journal(['Romeo & Juliet', 'Loading…'])).to_be_undefined()
        expect(parse_romeo_juliet_journal('I spoke to someone in Varrock.')).to_be_undefined()
    test('does not infer a stage from partial or loading text', _fn8)


describe('Romeo & Juliet journal stage parsing', _fn3)


def _fn9():
    for _stage, _inv, _expected in ROUTES:
        test(f'routes stage {_stage} deterministically to {_expected}', routes(_stage, _inv, _expected))

    def _fn11():
        cases = [
        [30, [], 'stage 30: ask Father Lawrence for help'],
        [40, [], 'stage 40: ask the Apothecary for a Cadava potion'],
        [50, ['Cadava berries'], 'stage 50: exchange Cadava berries with the Apothecary'],
        [60, ['Cadava berries'], 'stage 60: tell Romeo that Juliet took the potion'],
    ]
        for stage, inv, expected in cases:
            for no_progress in [0, 1, 2, 3, 7]:
                for tile in [VARROCK, FAR_AWAY, None]:
                    expect(custom_name(decide(snap({'stage': stage, 'inv': inv, 'no_progress': no_progress, 'tile': tile})))).to_be(expected)
    test('routing no longer depends on no-progress count or player tile', _fn11)

    def _fn12():
        full = ['Cadava berries'] + ['Bones'] * 27
        expect(custom_name(decide(snap({'stage': 60, 'inv': full, 'free_slots': 0, 'bank_known': False})))).to_be('stage 60: tell Romeo that Juliet took the potion')
    test('stage 60 ignores obsolete berries and a full pack and goes straight to Romeo', _fn12)

    def _fn13():
        expect(decide(snap({'stage': 0, 'journal': 'complete'})).kind).to_be('done')
        expect(decide(snap({'stage': 100})).kind).to_be('done')
        expect(decide(snap({'journal': 'unknown'}))).to_equal(Record({'kind': 'wait', 'reason': 'quest journal not loaded'}))
        unavailable = snap().with_fields({'stage': None})
        expect(decide(unavailable)).to_equal(Record({'kind': 'wait', 'reason': 'Romeo & Juliet stage unavailable'}))
        expect(decide(snap({'stage': 70}))).to_equal(Record({'kind': 'wait', 'reason': 'unrecognized Romeo & Juliet stage 70'}))
    test('completes from either status or exact stage and waits on unknown state', _fn13)


describe('Romeo & Juliet authoritative stage routing', _fn9)


def _fn14():
    def _fn15():
        full = ['Message'] + ['Bones'] * 27
        expect(custom_name(decide(snap({'stage': 20, 'inv': full, 'free_slots': 0, 'bank_known': False})))).to_be("stage 20: deliver Juliet's message to Romeo")
    test('uses a held exact message immediately, even before a bank scan', _fn15)

    def _fn16():
        step = decide(snap({'stage': 20, 'bank_known': False}))
        expect(step.kind).to_be('scan_bank')
        expect(step.kind == 'scan_bank' and step.bank).to_be_defined()
    test('scans an unknown bank before asking Juliet to replace a missing message', _fn16)

    def _fn17():
        step = decide(snap({'stage': 20, 'bank': ['Message']}))
        expect(bank_item(step)).to_equal({'name': 'Message', 'id': 755, 'qty': 1})
    test('withdraws the exact banked quest message after a restart', _fn17)

    def _fn18():
        expect(custom_name(decide(snap({'stage': 20})))).to_be('stage 20: ask Juliet to replace the lost message')
    test('asks Juliet for a replacement only after proving the message is absent', _fn18)

    def _fn19():
        step = decide(snap({'stage': 20, 'inv': ['Message'], 'inv_ids': {9999: 1}, 'bank_known': True}))
        expect(custom_name(step)).to_be('stage 20: ask Juliet to replace the lost message')
    test('does not mistake a different item named Message for quest item id 755', _fn19)

    def _fn20():
        for stage in [10, 20]:
            step = decide(snap({'stage': stage, 'inv': ['Bones'] * 28, 'free_slots': 0}))
            expect(step.kind).to_be('deposit')
            if step.kind == 'deposit':
                expect(step.keep).to_equal([])
                expect(step.keep_ids).to_equal([])
                expect(step.exact_keep).to_be(True)
    test('clears a full pack before Juliet creates or replaces a message', _fn20)

    def _fn21():
        step = decide(snap({'stage': 50, 'inv': ['Cadava berries', 'Cadava potion']}))
        expect(custom_name(step)).to_be('stage 50: deliver the Cadava potion to Juliet')
    test('stage 50 prioritizes a held potion over held berries', _fn21)

    def _fn22():
        expect(decide(snap({'stage': 50, 'bank_known': False})).kind).to_be('scan_bank')
        potion = decide(snap({'stage': 50, 'bank': ['Cadava berries', 'Cadava potion']}))
        expect(bank_item(potion)).to_equal({'name': 'Cadava potion', 'id': 756, 'qty': 1})
        berries = decide(snap({'stage': 50, 'bank': ['Cadava berries']}))
        expect(bank_item(berries)).to_equal({'name': 'Cadava berries', 'id': 753, 'qty': 1})
    test('stage 50 scans the bank, then prioritizes banked potion over berries', _fn22)

    def _fn23():
        expect(custom_name(decide(snap({'stage': 50})))).to_be('stage 50: collect Cadava berries from their ground spawns')
    test('collects a ground berry only after inventory and known bank are both empty', _fn23)

    def _fn24():
        step = decide(snap({'stage': 50, 'inv': ['Bones'] * 28, 'free_slots': 0, 'bank': ['Cadava potion']}))
        expect(step.kind).to_be('deposit')
        expect(step.kind == 'deposit' and step.exact_keep).to_be(True)
    test('clears a full pack before withdrawing or collecting a stage-50 item', _fn24)

    def _fn25():
        inventory_collision = decide(snap({'stage': 50, 'inv': ['Cadava potion'], 'inv_ids': {9998: 1}}))
        expect(custom_name(inventory_collision)).to_be('stage 50: collect Cadava berries from their ground spawns')
        bank_collision = decide(snap({'stage': 50, 'bank': ['Cadava berries'], 'bank_ids': {9997: 1}}))
        expect(custom_name(bank_collision)).to_be('stage 50: collect Cadava berries from their ground spawns')
    test('does not mistake same-name inventory or bank entries for exact quest IDs', _fn25)


describe('Romeo & Juliet restart and item recovery', _fn14)


def _fn26():
    def _fn27():
        expect(romeojuliet.record.id).to_be('romeojuliet')
        expect(romeojuliet.owns_inventory).to_be(True)
        expect(romeojuliet.read_stage).to_be_defined()
        expect(romeojuliet.bank).to_be_defined()
        expect(romeojuliet.gather).to_be_undefined()
    test('owns its stage-specific inventory and exposes the journal stage oracle', _fn27)


describe('Romeo & Juliet module wiring', _fn26)
