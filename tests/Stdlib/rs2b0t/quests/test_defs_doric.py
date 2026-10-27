"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/doric.test.ts (MIT, see thirdparty/rs2b0t)."""
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot

def _each_run(fn, row):
    def run():
        return fn(*row) if isinstance(row, list) else fn(row)
    return run

def _each(rows, label, fn):
    for row in rows:
        test(label + ' ' + str(row), _each_run(fn, row))


def _snapshot(**fields):
    for name in ['inv', 'inv_ids', 'bank', 'bank_ids']:
        if isinstance(fields.get(name), (Record, Fake)):
            fields[name] = fields[name]._fields
    return QuestSnapshot(**fields)
from rs2004.quests.defs.doric import decide, decide_for_mining_level, doric, DORIC_ITEM, DORIC_PICKAXES, DORIC_STAGE, parse_doric_journal

def stack(item, qty=1):
    _merged1 = {}
    for _k, _v in (item._fields if isinstance(item, (Record, Fake)) else item).items():
        _merged1[_k] = _v
    for _k, _v in {'qty': qty}.items():
        _merged1[_k] = _v
    return Fake(**_merged1)

def fake(name, id, qty):
    return Fake(**{'name': name, 'id': id, 'qty': qty})

def name_counts(items):
    counts = {}
    for item in items:
        name = item.name.lower()
        _v2 = counts.get(name)
        counts[name] = (_v2 if _v2 is not None else 0) + item.qty
    return counts

def id_counts(items):
    counts = {}
    for item in items:
        _v3 = counts.get(item.id)
        counts[item.id] = (_v3 if _v3 is not None else 0) + item.qty
    return counts

def snap(options=None):
    if options is None:
        options = Fake(**{})
    inv = options.inv if options.inv is not None else []
    worn = options.worn if options.worn is not None else []
    bank = options.bank if options.bank is not None else []
    return _snapshot(**{'journal': options.journal if options.journal is not None else 'in_progress', 'inv': name_counts(inv), 'inv_ids': id_counts(inv), 'worn': set([item.name for item in worn]), 'worn_ids': set([item.id for item in worn]), 'no_progress': 0, 'bank_coins': 2000000, 'stage': options.stage if options.stage is not None else DORIC_STAGE.STARTED, 'bank': name_counts(bank), 'bank_ids': id_counts(bank), 'bank_known': options.bank_known if options.bank_known is not None else True, 'free_slots': options.free_slots if options.free_slots is not None else max(0, 28 - sum([item.qty for item in inv]))})

def custom_name(step):
    return step.name if step.kind == 'custom' else None

def expect_custom(step, purpose):
    expect(step.kind).to_be('custom')
    name = custom_name(step).lower()
    if 'pickaxe' in purpose:
        expect('pickaxe' in name and any([word in name for word in ['acquire', 'collect', 'source', 'ground']])).to_be(True)
    elif 'train|mine' in purpose:
        expect(('train' in name or 'mine' in name) and 'copper' in name).to_be(True)
    elif 'drop' in purpose:
        expect('drop' in name and 'copper' in name).to_be(True)
    else:
        for word in purpose.strip('/i').split('.*'):
            expect(name).to_contain(word.lower())

def expect_doric_talk(step):
    expect(['talk', 'custom']).to_contain(step.kind)
    if step.kind == 'talk':
        expect(step.stop.npc).to_be('Doric')
    elif step.kind == 'custom':
        expect(step.name).to_contain('Doric')

def expect_withdrawal(step, items):
    expect(step.kind).to_be('withdraw')
    if step.kind == 'withdraw':
        expect(step.items).to_equal(items)
        expect(step.bank).to_be_defined()
BRONZE_PICK = stack(DORIC_ITEM.BRONZE_PICKAXE)
IRON_PICK = Fake(**{'name': 'Iron pickaxe', 'id': 1267})
STEEL_PICK = Fake(**{'name': 'Steel pickaxe', 'id': 1269})
MITHRIL_PICK = Fake(**{'name': 'Mithril pickaxe', 'id': 1273})
ADAMANT_PICK = Fake(**{'name': 'Adamant pickaxe', 'id': 1271})
RUNE_PICK = Fake(**{'name': 'Rune pickaxe', 'id': 1275})

def unloaded_journal():
    expect(parse_doric_journal(["Doric's Quest", 'Loading...'])).to_be_undefined()
    expect(parse_doric_journal('I should collect some ore for a smith.')).to_be_undefined()

def _fn4():
    cases = [['@dbl@I can start this quest by talking to @dre@Doric@dbl@ at his home|north of @dre@Falador@dbl@.', DORIC_STAGE.NOT_STARTED], ['@str@I have spoken to @dre@Doric||@dbl@I need to collect some items and bring them to @dre@Doric|@dre@6 Clay|@dre@4 Copper Ore|@dre@2 Iron Ore|', DORIC_STAGE.STARTED], ["@str@I have spoken to @dre@Doric||@str@I have collected some Clay, Copper Ore, and Iron Ore.||@str@Doric rewarded me for all my hard work.|@str@I can now use Doric's Anvils whenever I want.|@red@QUEST COMPLETE!", DORIC_STAGE.COMPLETE]]
    for text, stage in cases:

        def _make__fn5(text, stage):
            def _fn5():
                expect(parse_doric_journal(text)).to_be(stage)
            return _fn5
        test(f'maps the rendered journal to exact stage {stage}', _make__fn5(text, stage))

    def _fn6():
        text = '@str@I have spoken to @dre@Doric||@dbl@I need to collect some items and bring them to @dre@Doric|@str@6 Clay|@str@4 Copper Ore|@dre@2 Iron Ore|'
        expect(parse_doric_journal(text)).to_be(DORIC_STAGE.STARTED)
    test('keeps the active stage when journal material lines are crossed out dynamically', _fn6)

    test('does not infer a stage from loading or unrelated text', unloaded_journal)

describe("Doric's Quest journal stage parsing", _fn4)

def _fn8():

    def _fn9():
        expect_doric_talk(decide(snap(Fake(**{'stage': DORIC_STAGE.NOT_STARTED}))))
    test('stage 0 starts the quest with Doric', _fn9)

    def _fn10():
        expect(decide_for_mining_level(snap(Fake(**{'stage': DORIC_STAGE.COMPLETE})), 1)).to_equal(Fake(**{'kind': 'done'}))
        expect(decide(snap(Fake(**{'stage': DORIC_STAGE.NOT_STARTED, 'journal': 'complete'})))).to_equal(Fake(**{'kind': 'done'}))
    test('stage 100 and an authoritative complete journal are no-ops', _fn10)

    def _fn11():
        expect(decide(snap(Fake(**{'journal': 'unknown'})))).to_equal(Fake(**{'kind': 'wait', 'reason': 'quest journal not loaded'}))
        unavailable = snap()
        unavailable.stage = None
        unavailable_step = decide(unavailable)
        expect(unavailable_step.kind).to_be('wait')
        expect(unavailable_step.kind == 'wait' and unavailable_step.reason).to_contain('stage unavailable')
        unknown_step = decide_for_mining_level(snap(Fake(**{'stage': 70})), 15)
        expect(unknown_step.kind).to_be('wait')
        expect(unknown_step.kind == 'wait' and unknown_step.reason).to_contain("unrecognized Doric's Quest stage 70")
    test('waits safely for an unknown journal, unavailable stage, or unknown stage', _fn11)
describe("Doric's Quest authoritative stage routing", _fn8)

def _fn12():

    def _fn13():
        step = decide_for_mining_level(snap(Fake(**{'bank_known': False})), 1)
        expect(step.kind).to_be('scan_bank')
        expect(step.kind == 'scan_bank' and step.bank).to_be_defined()
    test('scans an unknown bank before mining, buying, or collecting a tool', _fn13)

    def _fn14():
        step = decide_for_mining_level(snap(Fake(**{'bank': [stack(DORIC_ITEM.CLAY, 20), stack(DORIC_ITEM.COPPER, 20), stack(DORIC_ITEM.IRON, 20)]})), 1)
        _merged15 = {}
        for _k, _v in (DORIC_ITEM.CLAY._fields if isinstance(DORIC_ITEM.CLAY, (Record, Fake)) else DORIC_ITEM.CLAY).items():
            _merged15[_k] = _v
        for _k, _v in {'qty': DORIC_ITEM.CLAY.qty}.items():
            _merged15[_k] = _v
        _merged16 = {}
        for _k, _v in (DORIC_ITEM.COPPER._fields if isinstance(DORIC_ITEM.COPPER, (Record, Fake)) else DORIC_ITEM.COPPER).items():
            _merged16[_k] = _v
        for _k, _v in {'qty': DORIC_ITEM.COPPER.qty}.items():
            _merged16[_k] = _v
        _merged17 = {}
        for _k, _v in (DORIC_ITEM.IRON._fields if isinstance(DORIC_ITEM.IRON, (Record, Fake)) else DORIC_ITEM.IRON).items():
            _merged17[_k] = _v
        for _k, _v in {'qty': DORIC_ITEM.IRON.qty}.items():
            _merged17[_k] = _v
        expect_withdrawal(step, [Fake(**_merged15), Fake(**_merged16), Fake(**_merged17)])
    test('withdraws all three exact material requirements in one bank visit', _fn14)

    def _fn18():
        step = decide_for_mining_level(snap(Fake(**{'inv': [stack(DORIC_ITEM.CLAY, 2), stack(DORIC_ITEM.COPPER, 1)], 'bank': [stack(DORIC_ITEM.CLAY, 4), stack(DORIC_ITEM.COPPER, 3), stack(DORIC_ITEM.IRON, 2), fake('Clay', 9434, 50)]})), 1)
        _merged19 = {}
        for _k, _v in (DORIC_ITEM.CLAY._fields if isinstance(DORIC_ITEM.CLAY, (Record, Fake)) else DORIC_ITEM.CLAY).items():
            _merged19[_k] = _v
        for _k, _v in {'qty': 4}.items():
            _merged19[_k] = _v
        _merged20 = {}
        for _k, _v in (DORIC_ITEM.COPPER._fields if isinstance(DORIC_ITEM.COPPER, (Record, Fake)) else DORIC_ITEM.COPPER).items():
            _merged20[_k] = _v
        for _k, _v in {'qty': 3}.items():
            _merged20[_k] = _v
        _merged21 = {}
        for _k, _v in (DORIC_ITEM.IRON._fields if isinstance(DORIC_ITEM.IRON, (Record, Fake)) else DORIC_ITEM.IRON).items():
            _merged21[_k] = _v
        for _k, _v in {'qty': 2}.items():
            _merged21[_k] = _v
        expect_withdrawal(step, [Fake(**_merged19), Fake(**_merged20), Fake(**_merged21)])
    test('withdraws only deficits from a partial inventory and mixed bank', _fn18)

    def _fn22():
        step = decide_for_mining_level(snap(Fake(**{'inv': [stack(DORIC_ITEM.CLAY, 6), stack(DORIC_ITEM.COPPER, 4), BRONZE_PICK], 'bank': [stack(DORIC_ITEM.IRON, 2)]})), 1)
        _merged23 = {}
        for _k, _v in (DORIC_ITEM.IRON._fields if isinstance(DORIC_ITEM.IRON, (Record, Fake)) else DORIC_ITEM.IRON).items():
            _merged23[_k] = _v
        for _k, _v in {'qty': 2}.items():
            _merged23[_k] = _v
        expect_withdrawal(step, [Fake(**_merged23)])
    test('withdraws banked iron at Mining 1 instead of needlessly training to Mining 15', _fn22)

    def _fn24():
        step = decide_for_mining_level(snap(Fake(**{'inv': [fake('Clay', 9434, 6), fake('Copper ore', 9436, 4), fake('Iron ore', 9440, 2), fake('Bronze pickaxe', 9265, 1)]})), 15)
        expect_custom(step, '/(?:acquire|collect|source|ground).*(?:bronze )?pickaxe/i')
    test('same-name inventory collisions do not satisfy exact quest items or tools', _fn24)

    def _fn25():
        step = decide_for_mining_level(snap(Fake(**{'inv': [stack(DORIC_ITEM.CLAY, 6), stack(DORIC_ITEM.COPPER, 4), BRONZE_PICK], 'bank': [fake('Iron ore', 9440, 2)]})), 15)
        expect_custom(step, '/mine.*iron/i')
    test('same-name bank collisions are neither withdrawn nor counted as quest progress', _fn25)
describe("Doric's Quest exact item and bank recovery decisions", _fn12)

def _fn26():

    def _fn27():
        _merged28 = {}
        for _k, _v in (RUNE_PICK._fields if isinstance(RUNE_PICK, (Record, Fake)) else RUNE_PICK).items():
            _merged28[_k] = _v
        for _k, _v in {'level': 41}.items():
            _merged28[_k] = _v
        _merged29 = {}
        for _k, _v in (ADAMANT_PICK._fields if isinstance(ADAMANT_PICK, (Record, Fake)) else ADAMANT_PICK).items():
            _merged29[_k] = _v
        for _k, _v in {'level': 31}.items():
            _merged29[_k] = _v
        _merged30 = {}
        for _k, _v in (MITHRIL_PICK._fields if isinstance(MITHRIL_PICK, (Record, Fake)) else MITHRIL_PICK).items():
            _merged30[_k] = _v
        for _k, _v in {'level': 21}.items():
            _merged30[_k] = _v
        _merged31 = {}
        for _k, _v in (STEEL_PICK._fields if isinstance(STEEL_PICK, (Record, Fake)) else STEEL_PICK).items():
            _merged31[_k] = _v
        for _k, _v in {'level': 6}.items():
            _merged31[_k] = _v
        _merged32 = {}
        for _k, _v in (IRON_PICK._fields if isinstance(IRON_PICK, (Record, Fake)) else IRON_PICK).items():
            _merged32[_k] = _v
        for _k, _v in {'level': 1}.items():
            _merged32[_k] = _v
        _merged33 = {}
        for _k, _v in (DORIC_ITEM.BRONZE_PICKAXE._fields if isinstance(DORIC_ITEM.BRONZE_PICKAXE, (Record, Fake)) else DORIC_ITEM.BRONZE_PICKAXE).items():
            _merged33[_k] = _v
        for _k, _v in {'level': 1}.items():
            _merged33[_k] = _v
        expect(DORIC_PICKAXES).to_equal([Fake(**_merged28), Fake(**_merged29), Fake(**_merged30), Fake(**_merged31), Fake(**_merged32), Fake(**_merged33)])
    test('exports every exact pickaxe ID in best-first usable-tier order', _fn27)
    usable_tier_cases = [Fake(**{'level': 1, 'available': [RUNE_PICK, STEEL_PICK, IRON_PICK, DORIC_ITEM.BRONZE_PICKAXE], 'expected': IRON_PICK}), Fake(**{'level': 14, 'available': [RUNE_PICK, MITHRIL_PICK, STEEL_PICK, IRON_PICK], 'expected': STEEL_PICK}), Fake(**{'level': 31, 'available': [RUNE_PICK, ADAMANT_PICK, STEEL_PICK], 'expected': ADAMANT_PICK}), Fake(**{'level': 41, 'available': [RUNE_PICK, ADAMANT_PICK, DORIC_ITEM.BRONZE_PICKAXE], 'expected': RUNE_PICK})]
    for _item34 in usable_tier_cases:
        level = _item34.level
        available = _item34.available
        expected = _item34.expected

        def _fn35():
            step = decide_for_mining_level(snap(Fake(**{'bank': [stack(item) for item in available]})), level)
            expect_withdrawal(step, [Fake(**{'name': expected.name, 'id': expected.id, 'qty': 1})])
        test(f'Mining {level} withdraws the best usable banked tier', _fn35)

    def _fn36():
        step = decide_for_mining_level(snap(Fake(**{'inv': [stack(RUNE_PICK)], 'bank': [stack(DORIC_ITEM.BRONZE_PICKAXE)]})), 1)
        _merged37 = {}
        for _k, _v in (DORIC_ITEM.BRONZE_PICKAXE._fields if isinstance(DORIC_ITEM.BRONZE_PICKAXE, (Record, Fake)) else DORIC_ITEM.BRONZE_PICKAXE).items():
            _merged37[_k] = _v
        for _k, _v in {'qty': 1}.items():
            _merged37[_k] = _v
        expect_withdrawal(step, [Fake(**_merged37)])
    test('ignores an unusable held tier and withdraws a usable one', _fn36)

    def _fn38():
        step = decide_for_mining_level(snap(Fake(**{'worn': [IRON_PICK]})), 1)
        expect_custom(step, '/mine.*clay/i')
    test('uses a usable exact worn pickaxe without trying to reacquire it', _fn38)

    def _fn39():
        step = decide_for_mining_level(snap(), 1)
        expect_custom(step, '/(?:acquire|collect|source|ground).*(?:bronze )?pickaxe/i')
    test('collects the free bronze pickaxe spawn when no usable pick exists anywhere', _fn39)
describe("Doric's Quest pickaxe sourcing", _fn26)

def _fn40():

    def _fn41():
        step = decide_for_mining_level(snap(Fake(**{'inv': [BRONZE_PICK]})), 1)
        expect_custom(step, '/mine.*clay/i')
    test('mines the six required clay before moving to copper', _fn41)

    def _fn42():
        step = decide_for_mining_level(snap(Fake(**{'inv': [BRONZE_PICK, stack(DORIC_ITEM.CLAY, 6)]})), 1)
        expect_custom(step, '/mine.*copper/i')
    test('mines the four required copper after clay is complete', _fn42)

    def _fn43(level):
        step = decide_for_mining_level(snap(Fake(**{'inv': [BRONZE_PICK, stack(DORIC_ITEM.CLAY, 6), stack(DORIC_ITEM.COPPER, 4)]})), level)
        expect_custom(step, '/(?:train|mine).*copper/i')
    _each([1, 14], 'Mining %i trains on copper after the clay and copper requirements are secured', _fn43)

    def _fn44():
        step = decide_for_mining_level(snap(Fake(**{'inv': [BRONZE_PICK, stack(DORIC_ITEM.CLAY, 6), stack(DORIC_ITEM.COPPER, 4)]})), 15)
        expect_custom(step, '/mine.*iron/i')
    test('Mining 15 stops training and mines the two required iron', _fn44)

    def _fn45():
        complete = decide_for_mining_level(snap(Fake(**{'inv': [stack(DORIC_ITEM.CLAY, 6), stack(DORIC_ITEM.COPPER, 4), stack(DORIC_ITEM.IRON, 2)]})), 1)
        expect_doric_talk(complete)
        split = decide_for_mining_level(snap(Fake(**{'inv': [stack(DORIC_ITEM.CLAY, 6), stack(DORIC_ITEM.COPPER, 4)], 'bank': [stack(DORIC_ITEM.IRON, 2)]})), 1)
        expect(split.kind).to_be('withdraw')
    test('hands in only when all three exact requirements are simultaneously held', _fn45)

    def _fn46():
        step = decide_for_mining_level(snap(Fake(**{'inv': [stack(DORIC_ITEM.CLAY, 6), stack(DORIC_ITEM.COPPER, 4), stack(DORIC_ITEM.IRON, 2)]})), 1)
        expect_custom(step, '/hand Doric.*collect the full reward/i')
    test('the hand-in owns the full post-completion reward queue', _fn46)

    def _fn47():
        step = decide_for_mining_level(snap(Fake(**{'inv': [BRONZE_PICK, stack(DORIC_ITEM.CLAY, 7), stack(DORIC_ITEM.COPPER, 3), stack(DORIC_ITEM.IRON, 3)]})), 15)
        expect_custom(step, '/mine.*copper/i')
        expect(custom_name(step)).not_.to_contain('drop')
    test('preserves extra clay and iron rather than treating them as disposable training ore', _fn47)

    def _fn48(clay, copper, iron):
        step = decide_for_mining_level(snap(Fake(**{'inv': [stack(DORIC_ITEM.CLAY, clay), stack(DORIC_ITEM.COPPER, copper), stack(DORIC_ITEM.IRON, iron)]})), 15)
        expect_doric_talk(step)
    _each([[7, 4, 2], [6, 4, 3], [8, 12, 5]], 'hands in immediately with surplus counts (%i clay, %i copper, %i iron)', _fn48)

    def _fn49():
        step = decide_for_mining_level(snap(Fake(**{'inv': [stack(DORIC_ITEM.CLAY, 6), stack(DORIC_ITEM.COPPER, 22)], 'worn': [DORIC_ITEM.BRONZE_PICKAXE], 'free_slots': 0})), 14)
        expect_custom(step, '/drop.*(?:surplus|training)?.*copper/i')
    test('drops disposable training copper when it fills the pack', _fn49)

    def _fn50():
        step = decide_for_mining_level(snap(Fake(**{'inv': [stack(DORIC_ITEM.CLAY, 6), stack(DORIC_ITEM.COPPER, 4), BRONZE_PICK, fake('Bones', 526, 17)], 'free_slots': 0})), 15)
        expect(step.kind).to_be('deposit')
        if step.kind == 'deposit':
            expect(step.exact_keep).to_be(True)
            expect(step.keep).to_equal([])
            expect(set(step.keep_ids)).to_equal(set([DORIC_ITEM.CLAY.id, DORIC_ITEM.COPPER.id, DORIC_ITEM.IRON.id] + list([item.id for item in DORIC_PICKAXES])))
            expect(step.keep_ids).not_.to_contain(526)
    test('cleans a full junk pack while preserving exact quest and pickaxe IDs', _fn50)

    def _fn51():
        step = decide_for_mining_level(snap(Fake(**{'inv': [stack(DORIC_ITEM.CLAY, 7), stack(DORIC_ITEM.COPPER, 4), stack(DORIC_ITEM.IRON, 1), stack(DORIC_ITEM.BRONZE_PICKAXE, 1), stack(RUNE_PICK, 15)], 'free_slots': 0})), 1)
        expect(step.kind).to_be('deposit')
        if step.kind == 'deposit':
            expect(step.exact_keep).to_be(True)
            expect(step.keep).to_equal([])
            expect(step.keep_ids).to_equal([])
    test('rebalances a full exact-item pack instead of parking forever', _fn51)

    def _fn52():
        step = decide_for_mining_level(snap(Fake(**{'inv': [stack(DORIC_ITEM.CLAY, 20), stack(DORIC_ITEM.BRONZE_PICKAXE, 5)], 'bank': [stack(DORIC_ITEM.COPPER, 4), stack(DORIC_ITEM.IRON, 2)], 'free_slots': 3})), 1)
        expect(step.kind).to_be('deposit')
        if step.kind == 'deposit':
            expect(step.keep_ids).to_equal([])
    test('rebalances exact items when a bank withdrawal needs more slots than remain', _fn52)
describe("Doric's Quest mining progression", _fn40)

def _fn53():

    def _fn54():
        expect(doric.record.id).to_be('doric')
        expect(doric.owns_inventory).to_be(True)
        expect(doric.read_stage).to_be_defined()
        expect(doric.decide).to_be(decide)
        expect(doric.bank).to_be_defined()
        expect(doric.gather).to_be_undefined()
    test('owns its inventory and exposes its exact journal-stage oracle', _fn54)
describe("Doric's Quest module wiring", _fn53)

