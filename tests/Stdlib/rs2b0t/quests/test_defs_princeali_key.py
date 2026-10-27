"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/princeali-key.test.ts (MIT, see thirdparty/rs2b0t)."""
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot

def _snapshot(**fields):
    for name in ['inv', 'inv_ids', 'bank', 'bank_ids']:
        if isinstance(fields.get(name), (Record, Fake)):
            fields[name] = fields[name]._fields
    return QuestSnapshot(**fields)
from rs2004.quests.defs.princeali.areas import PA_ITEM
from rs2004.quests.defs.princeali.journal import PRINCE_STAGE
from rs2004.quests.defs.princeali.key import collect_key, have_key, make_soft_clay, source_bronze_bar, source_clay, source_pickaxe, source_water, take_key_print

def snap(inv_ids=None, bank_ids=None, extra=None):
    if inv_ids is None:
        inv_ids = []
    if bank_ids is None:
        bank_ids = []
    if extra is None:
        extra = Fake(**{})
    _merged1 = {}
    for _k, _v in {'journal': 'in_progress', 'inv': {}, 'inv_ids': {_k: _v for _k, _v in inv_ids}, 'worn': set(), 'worn_ids': set(), 'no_progress': 0, 'bank_coins': 0, 'bank': {}, 'bank_ids': {_k: _v for _k, _v in bank_ids}, 'bank_known': True, 'stage': PRINCE_STAGE.SPOKEN_OSMAN}.items():
        _merged1[_k] = _v
    for _k, _v in (extra._fields if isinstance(extra, (Record, Fake)) else extra).items():
        _merged1[_k] = _v
    return _snapshot(**_merged1)

def at(stage, inv_ids=None, bank_ids=None):
    if inv_ids is None:
        inv_ids = []
    if bank_ids is None:
        bank_ids = []
    return snap(inv_ids, bank_ids, Fake(**{'stage': stage}))
I = PA_ITEM

def _fn2():

    def _fn3():
        step = source_bronze_bar(snap())
        expect((step.kind if step is not None else None) == 'buy' and step.item).to_be('Bronze bar')
        expect((step.kind if step is not None else None) == 'buy' and step.shop.npc).to_be('Shantay')
    test('bought at Shantay while the key is still missing', _fn3)

    def _fn4():
        expect(source_bronze_bar(snap([[I.PRINCE_KEY.id, 1]]))).to_be_null()
        expect(source_bronze_bar(snap([], [[I.PRINCE_KEY.id, 1]]))).to_be_null()
    test('not wanted once the key is owned', _fn4)

    def _fn5():
        expect(source_bronze_bar(at(PRINCE_STAGE.PREP_FINISHED))).to_be_null()
        expect(source_bronze_bar(at(PRINCE_STAGE.TIED_KELI))).to_be_null()
    test('never wanted from stage 30 on: the key was already issued, so nothing can forge', _fn5)
describe('bronze bar', _fn2)

def _fn6():

    def _fn7():
        step = source_water(snap())
        expect((step.kind if step is not None else None) == 'buy' and step.qty).to_be(2)
        expect((step.kind if step is not None else None) == 'buy' and step.shop.npc).to_be('Shantay')
    test('two jugs: one for the soft clay, one for the paste', _fn7)

    def _fn8():
        step = source_water(snap([[I.PASTE.id, 1]]))
        expect((step.kind if step is not None else None) == 'buy' and step.qty).to_be(1)
    test('one needed once the paste is made and the clay is still raw', _fn8)

    def _fn9():
        expect(source_water(snap([[I.PASTE.id, 1], [I.SOFT_CLAY.id, 1]]))).to_be_null()
    test('none once the paste is made and the soft clay exists', _fn9)

    def _fn10():
        expect(source_water(snap([[I.SOFT_CLAY.id, 1], [I.JUG_OF_WATER.id, 1]]))).to_be_null()
    test('a spent jug is not re-bought: soft clay made, paste jug still held', _fn10)

    def _fn11():
        expect(source_water(at(PRINCE_STAGE.PREP_FINISHED, [[I.PASTE.id, 1]]))).to_be_null()
        step = source_water(at(PRINCE_STAGE.PREP_FINISHED))
        expect((step.kind if step is not None else None) == 'buy' and step.qty).to_be(1)
    test('at stage 30 only the paste can still want water', _fn11)
describe('water', _fn6)

def _fn12():

    def _fn13():
        step = source_pickaxe(snap())
        expect((step.kind if step is not None else None) == 'grab_ground' and step.item).to_be('Bronze pickaxe')
        expect((step.kind if step is not None else None) == 'grab_ground' and step.anchor.x).to_be(2963)
    test('no pickaxe -> the Rimmington spawn', _fn13)

    def _fn14():
        expect(source_pickaxe(snap([], [], Fake(**{'worn_ids': set([1271])})))).to_be_null()
    test('a worn pickaxe counts', _fn14)

    def _fn15():
        expect(source_pickaxe(snap([[I.SOFT_CLAY.id, 1]]))).to_be_null()
    test('no pickaxe wanted once the soft clay exists', _fn15)

    def _fn16():
        expect(source_pickaxe(at(PRINCE_STAGE.PREP_FINISHED))).to_be_null()
        expect(source_clay(at(PRINCE_STAGE.PREP_FINISHED, [[I.PICKAXE.id, 1]]))).to_be_null()
    test('no pickaxe or clay wanted from stage 30 on', _fn16)

    def _fn17():
        step = source_clay(snap([[I.PICKAXE.id, 1]]))
        expect((step.kind if step is not None else None) == 'mine_rock' and step.rock).to_be('Clay')
        expect((step.kind if step is not None else None) == 'mine_rock' and step.anchor.x).to_be(2986)
    test('pickaxe held -> mine clay', _fn17)

    def _fn18():
        expect(source_clay(snap([[I.PICKAXE.id, 1], [I.KEY_PRINT.id, 1]]))).to_be_null()
    test('clay is not mined again once a print exists', _fn18)
describe('pickaxe and clay', _fn12)

def _fn19():

    def _fn20():
        step = make_soft_clay(snap([[I.CLAY.id, 1], [I.JUG_OF_WATER.id, 1]]))
        expect((step.kind if step is not None else None) == 'use_on' and step.item).to_be('Jug of water')
        expect((step.kind if step is not None else None) == 'use_on' and step.target).to_be('Clay')
        expect((step.kind if step is not None else None) == 'use_on' and step.target_kind).to_be('item')
        expect((step.kind if step is not None else None) == 'use_on' and step.product).to_be('Soft clay')
    test('clay plus water -> the item-on-item craft', _fn20)

    def _fn21():
        expect(make_soft_clay(snap([[I.SOFT_CLAY.id, 1]]))).to_be_null()
        expect(make_soft_clay(snap([[I.KEY_PRINT.id, 1]]))).to_be_null()
        expect(make_soft_clay(snap([[I.PRINCE_KEY.id, 1]]))).to_be_null()
    test('null once the soft clay, print or key exists', _fn21)

    def _fn22():
        expect(make_soft_clay(snap([[I.CLAY.id, 1]]))).to_be_null()
    test('null with clay but no water — the water leg runs earlier', _fn22)
describe('soft clay', _fn19)

def _fn23():

    def _fn24():
        step = take_key_print(snap([[I.SOFT_CLAY.id, 1]]))
        expect((step.kind if step is not None else None) == 'talk' and step.stop.npc).to_be('Lady Keli')
    test('soft clay held -> Lady Keli', _fn24)

    def _fn25():
        expect(take_key_print(snap())).to_be_null()
    test('no soft clay -> nothing; the clay legs run first', _fn25)

    def _fn26():
        expect(take_key_print(snap([[I.SOFT_CLAY.id, 1], [I.KEY_PRINT.id, 1]]))).to_be_null()
        expect(take_key_print(snap([[I.SOFT_CLAY.id, 1], [I.PRINCE_KEY.id, 1]]))).to_be_null()
    test('null once a print or the key exists', _fn26)

    def _fn27():
        expect(take_key_print(at(PRINCE_STAGE.PREP_FINISHED, [[I.SOFT_CLAY.id, 1]]))).to_be_null()
    test('never taken from stage 30 on, even holding soft clay', _fn27)
describe('key print', _fn23)

def _fn28():

    def _fn29():
        expect(collect_key(snap([[I.PRINCE_KEY.id, 1]]))).to_be_null()
    test('key in the pack -> nothing left to do', _fn29)

    def _fn30():
        step = collect_key(snap([], [[I.PRINCE_KEY.id, 1]]))
        expect(step.kind if step is not None else None).to_be('withdraw')
    test('a banked key is withdrawn before anyone is asked for another', _fn30)

    def _fn31():
        step = collect_key(snap([[I.KEY_PRINT.id, 1], [I.BRONZE_BAR.id, 1]]))
        expect((step.kind if step is not None else None) == 'custom' and step.name).to_contain('Osman')
    test('print plus bar -> the self-correcting forge-and-collect', _fn31)

    def _fn32():
        expect(collect_key(snap([[I.KEY_PRINT.id, 1]]))).to_be_null()
    test('print without a bar -> nothing here; the bar leg runs earlier', _fn32)

    def _fn33():
        expect(collect_key(snap())).to_be_null()
    test('no print and no key at stage 20 -> nothing; the clay legs run earlier', _fn33)

    def _fn34():
        for stage in [PRINCE_STAGE.PREP_FINISHED, PRINCE_STAGE.GUARD_DRUNK, PRINCE_STAGE.TIED_KELI]:
            step = collect_key(at(stage))
            expect(step.kind if step is not None else None).to_be('custom')
            expect((step.kind if step is not None else None) == 'custom' and step.name).to_contain('Leela')
            expect((step.kind if step is not None else None) == 'custom' and step.name).not_.to_contain('Osman')
    test('a lost key at stage 30+ is re-issued by Leela, not re-forged', _fn34)

    def _fn35():
        step = collect_key(at(PRINCE_STAGE.GUARD_DRUNK, [], [[I.PRINCE_KEY.id, 1]]))
        expect(step.kind if step is not None else None).to_be('withdraw')
    test('a banked key at stage 30+ is still withdrawn first, not re-issued', _fn35)
describe('collectKey — the wedge', _fn28)

def _fn36():

    def _fn37():
        expect(have_key(snap([[I.PRINCE_KEY.id, 1]]))).to_be(True)
        expect(have_key(snap([], [[I.PRINCE_KEY.id, 1]]))).to_be(False)
        expect(have_key(snap())).to_be(False)
    test('true only when the key is in the pack', _fn37)
describe('haveKey', _fn36)
