"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/princeali-disguise.test.ts (MIT, see thirdparty/rs2b0t)."""
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot

def _snapshot(**fields):
    for name in ['inv', 'inv_ids', 'bank', 'bank_ids']:
        if isinstance(fields.get(name), (Record, Fake)):
            fields[name] = fields[name]._fields
    return QuestSnapshot(**fields)
from rs2004.quests.defs.princeali.areas import PA_ITEM
from rs2004.quests.defs.princeali.disguise import disguise_complete, make_ashes, make_blond_wig, make_paste, source_onions, source_paste_goods, source_pink_skirt, source_shears, source_tinderbox, source_wool

def snap(inv_ids=None, bank_ids=None):
    if inv_ids is None:
        inv_ids = []
    if bank_ids is None:
        bank_ids = []
    return _snapshot(**{'journal': 'in_progress', 'inv': {}, 'inv_ids': {_k: _v for _k, _v in inv_ids}, 'worn': set(), 'worn_ids': set(), 'no_progress': 0, 'bank_coins': 0, 'bank': {}, 'bank_ids': {_k: _v for _k, _v in bank_ids}, 'bank_known': True})
I = PA_ITEM

def _fn1():

    def _fn2():
        expect(source_wool(snap())).not_.to_be_null()
    test('nothing held -> wool is wanted', _fn2)

    def _fn3():
        expect(source_wool(snap([[I.PLAIN_WIG.id, 1]]))).to_be_null()
    test('a plain wig held -> no more wool', _fn3)

    def _fn4():
        s = snap([[I.BLOND_WIG.id, 1]])
        expect(source_wool(s)).to_be_null()
        expect(source_onions(s)).to_be_null()
        expect(make_blond_wig(s)).to_be_null()
    test('a blond wig held -> no wool, no onions, nothing left to make', _fn4)

    def _fn5():
        expect(source_wool(snap([[I.BALL_OF_WOOL.id, 3]]))).to_be_null()
    test('three balls already held -> no more wool', _fn5)

    def _fn6():
        expect(source_onions(snap()).kind if source_onions(snap()) is not None else None).to_be('pick_loc')
        expect(source_onions(snap([[I.YELLOW_DYE.id, 1]]))).to_be_null()
        expect(source_onions(snap([[I.ONION.id, 2]]))).to_be_null()
    test('onions are only wanted while the dye is missing', _fn6)

    def _fn7():
        step = source_onions(snap())
        expect((step.kind if step is not None else None) == 'pick_loc' and step.op).to_be('Pick')
        expect((step.kind if step is not None else None) == 'pick_loc' and step.anchor.x).to_be(3189)
    test('onions come from the Lumbridge patch by Pick', _fn7)

    def _fn8():
        step = make_blond_wig(snap([[I.ONION.id, 2]]))
        expect((step.kind if step is not None else None) == 'custom' and step.name).to_contain('yellow dye')
    test('two onions and no dye -> make the dye at Aggie', _fn8)

    def _fn9():
        step = make_blond_wig(snap([[I.YELLOW_DYE.id, 1], [I.BALL_OF_WOOL.id, 3]]))
        expect((step.kind if step is not None else None) == 'talk' and step.stop.npc).to_be('Ned')
    test('dye and three balls of wool but no wig -> Ned makes the wig', _fn9)

    def _fn10():
        step = make_blond_wig(snap([[I.PLAIN_WIG.id, 1], [I.YELLOW_DYE.id, 1]]))
        expect((step.kind if step is not None else None) == 'custom' and step.name).to_contain('dye')
    test('dye plus plain wig -> dye the wig', _fn10)

    def _fn11():
        step = make_blond_wig(snap([], [[I.BLOND_WIG.id, 1]]))
        expect(step.kind if step is not None else None).to_be('withdraw')
    test('a banked blond wig is withdrawn rather than remade', _fn11)
describe('the wig chain never re-buys a consumed input', _fn1)

def _fn12():

    def _fn13():
        s = snap([[I.PASTE.id, 1]])
        expect(source_paste_goods(s)).to_be_null()
        expect(source_tinderbox(s)).to_be_null()
        expect(make_ashes(s)).to_be_null()
        expect(make_paste(s)).to_be_null()
    test('paste held -> nothing in the chain is wanted', _fn13)

    def _fn14():
        step = source_paste_goods(snap())
        expect((step.kind if step is not None else None) == 'buy' and step.item).to_be('Redberries')
        expect((step.kind if step is not None else None) == 'buy' and step.shop.npc).to_be('Wydin')
    test('no redberries -> buy at Wydin', _fn14)

    def _fn15():
        step = source_paste_goods(snap([[I.REDBERRIES.id, 1]]))
        expect((step.kind if step is not None else None) == 'buy' and step.item).to_be('Pot of flour')
    test('redberries but no flour -> buy the flour at Wydin', _fn15)

    def _fn16():
        s = snap([[I.ASHES.id, 1]])
        expect(source_tinderbox(s)).to_be_null()
        expect(make_ashes(s)).to_be_null()
    test('ashes held -> no tinderbox and no logs', _fn16)

    def _fn17():
        expect(make_ashes(snap())).to_be_null()
    test('no tinderbox yet -> the ashes leg holds off; the tinderbox leg runs earlier', _fn17)

    def _fn18():
        step = make_ashes(snap([[I.TINDERBOX.id, 1]]))
        expect((step.kind if step is not None else None) == 'grab_ground' and step.item).to_be('Logs')
        expect((step.kind if step is not None else None) == 'grab_ground' and step.anchor.x).to_be(3089)
    test('tinderbox but no logs -> grab the Draynor spawn', _fn18)

    def _fn19():
        step = make_ashes(snap([[I.TINDERBOX.id, 1], [I.LOGS.id, 1]]))
        expect((step.kind if step is not None else None) == 'custom' and step.name).to_contain('ash')
    test('tinderbox and logs -> burn them', _fn19)

    def _fn20():
        s = snap([[I.REDBERRIES.id, 1], [I.POT_OF_FLOUR.id, 1], [I.ASHES.id, 1], [I.JUG_OF_WATER.id, 1]])
        step = make_paste(s)
        expect(step.kind if step is not None else None).to_be('talk')
        expect((step.kind if step is not None else None) == 'talk' and step.stop.npc).to_be('Aggie')
    test('all four ingredients -> Aggie mixes the paste', _fn20)

    def _fn21():
        s = snap([[I.REDBERRIES.id, 1], [I.POT_OF_FLOUR.id, 1], [I.ASHES.id, 1]])
        step = make_paste(s)
        expect(step.kind if step is not None else None).to_be('wait')
        expect((step.kind if step is not None else None) == 'wait' and step.reason).to_contain('Jug of water')
    test('no water -> the paste leg waits and names what is missing', _fn21)
describe('paste chain', _fn12)

def _fn22():

    def _fn23():
        step = source_pink_skirt(snap())
        expect((step.kind if step is not None else None) == 'buy' and step.shop.npc).to_be('Thessalia')
    test('no skirt -> buy at Thessalia', _fn23)

    def _fn24():
        expect(source_pink_skirt(snap([[I.PINK_SKIRT.id, 1]]))).to_be_null()
    test('skirt held -> null', _fn24)

    def _fn25():
        expect(source_shears(snap()).kind if source_shears(snap()) is not None else None).to_be('buy')
        expect(source_shears(snap([[I.PLAIN_WIG.id, 1]]))).to_be_null()
        expect(source_shears(snap([[I.BALL_OF_WOOL.id, 3]]))).to_be_null()
        expect(source_shears(snap([[I.SHEARS.id, 1]]))).to_be_null()
    test('shears are only wanted while wool is still needed', _fn25)

    def _fn26():
        shears = source_shears(snap())
        tinderbox = source_tinderbox(snap())
        expect((shears.kind if shears is not None else None) == 'buy' and shears.shop.npc).to_be('Shop keeper')
        expect((tinderbox.kind if tinderbox is not None else None) == 'buy' and tinderbox.shop.npc).to_be('Shop keeper')
    test('shears come from the Lumbridge general store, on the same trip as the tinderbox', _fn26)
describe('skirt and shears', _fn22)

def _fn27():

    def _fn28():
        expect(disguise_complete(snap([[I.PLAIN_WIG.id, 1], [I.PINK_SKIRT.id, 1], [I.PASTE.id, 1]]))).to_be(False)
        expect(disguise_complete(snap([[I.BLOND_WIG.id, 1], [I.PINK_SKIRT.id, 1], [I.PASTE.id, 1]]))).to_be(True)
    test('needs the blond wig, not the plain one', _fn28)

    def _fn29():
        expect(disguise_complete(snap([[I.BLOND_WIG.id, 1], [I.PINK_SKIRT.id, 1]], [[I.PASTE.id, 1]]))).to_be(False)
    test('banked pieces do not count — the prince needs them in the pack', _fn29)
describe('disguiseComplete', _fn27)
