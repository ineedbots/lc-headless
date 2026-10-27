"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/princeali.test.ts (MIT, see thirdparty/rs2b0t)."""
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot

def _snapshot(**fields):
    for name in ['inv', 'inv_ids', 'bank', 'bank_ids']:
        if isinstance(fields.get(name), (Record, Fake)):
            fields[name] = fields[name]._fields
    return QuestSnapshot(**fields)
from rs2004.quests.defs.princeali.areas import PA_ITEM
from rs2004.quests.defs.princeali.journal import PRINCE_STAGE
from rs2004.quests.defs.princeali import decide, princeali
I = PA_ITEM
S = PRINCE_STAGE
RICH = [[I.COINS.id, 2000000]]
PURSE = [[I.COINS.id, 1000]]
DISGUISE = [[I.BLOND_WIG.id, 1], [I.PINK_SKIRT.id, 1], [I.PASTE.id, 1]]

def snap(stage, inv_ids=None, bank_ids=None, extra=None):
    if inv_ids is None:
        inv_ids = []
    if bank_ids is None:
        bank_ids = RICH
    if extra is None:
        extra = Fake(**{})
    _merged1 = {}
    for _k, _v in {'journal': 'complete' if stage == S.COMPLETE else 'in_progress', 'inv': {}, 'inv_ids': {_k: _v for _k, _v in inv_ids}, 'worn': set(), 'worn_ids': set(), 'no_progress': 0, 'bank_coins': 0, 'bank': {}, 'bank_ids': {_k: _v for _k, _v in bank_ids}, 'bank_known': True, 'stage': stage, 'progress': None if stage is None else Fake(**{'stage': stage, 'flags': set()})}.items():
        _merged1[_k] = _v
    for _k, _v in (extra._fields if isinstance(extra, (Record, Fake)) else extra).items():
        _merged1[_k] = _v
    return _snapshot(**_merged1)

def kitted(stage, extra=None):
    if extra is None:
        extra = []
    return snap(stage, list(PURSE) + list(DISGUISE) + [[I.PRINCE_KEY.id, 1], [I.ROPE.id, 2], [I.BEER.id, 3], [I.JUG_OF_WATER.id, 1]] + list(extra))

def _fn2():

    def _fn3():
        expect(princeali.bank).to_match_object(Fake(**{'x': 3093, 'z': 3243, 'level': 0}))
    test('declares the Draynor bank at level 0', _fn3)

    def _fn4():
        expect(princeali.owns_inventory).to_be(True)
        expect(princeali.read_progress).to_be_defined()
        expect(princeali.gather).to_be_undefined()
    test('owns its own inventory and reads progress, with no gather map', _fn4)

    def _fn5():
        expect(len(princeali.record.items)).to_be_greater_than(0)
        for item in princeali.record.items:
            expect(item.kind).to_be('acquirable')
    test('every record item is acquirable, so eligibility never blocks the quest', _fn5)

    def _fn6():
        expect([item.name.lower() for item in princeali.record.items]).to_contain('coins')
    test('the record keeps coins, or every dialogue purchase parks', _fn6)

    def _fn7():
        expect(princeali.record.quest_points).to_be(3)
    test('three quest points', _fn7)
describe('module shape', _fn2)

def _fn8():

    def _fn9():
        expect(decide(snap(None, [], RICH, Fake(**{'journal': 'unknown'}))).kind).to_be('wait')
    test('an unloaded journal waits — it is not notStarted', _fn9)

    def _fn10():
        expect(decide(snap(None)).kind).to_be('wait')
    test('a loaded journal with no readable stage waits', _fn10)

    def _fn11():
        step = decide(snap(S.NOT_STARTED, PURSE))
        expect(step.kind == 'talk' and step.stop.npc).to_be('Hassan')
    test('stage 0 -> Hassan', _fn11)

    def _fn12():
        step = decide(snap(S.STARTED, PURSE))
        expect(step.kind == 'talk' and step.stop.npc).to_be('Osman')
    test('stage 10 -> Osman', _fn12)

    def _fn13():
        step = decide(snap(S.SAVED))
        expect(step.kind == 'talk' and step.stop.npc).to_be('Hassan')
    test('stage 100 -> Hassan for the reward', _fn13)

    def _fn14():
        expect(decide(snap(S.COMPLETE)).kind).to_be('done')
        expect(decide(snap(S.SAVED, [], RICH, Fake(**{'journal': 'complete'}))).kind).to_be('done')
    test('stage 110 and a complete journal are both done', _fn14)
describe('lifecycle', _fn8)

def _fn15():

    def _fn16():
        s = snap(S.NOT_STARTED, [], RICH, Fake(**{'bank_known': False}))
        expect(decide(s).kind).to_be('scan_bank')
    test('an unseen bank is scanned first, even at stage 0', _fn16)

    def _fn17():
        step = decide(snap(S.NOT_STARTED))
        expect(step.kind == 'withdraw' and step.items[0]['name']).to_be('Coins')
    test('stage 0 with an empty purse withdraws coins before walking to Hassan', _fn17)

    def _fn18():
        step = decide(snap(S.STARTED))
        expect(step.kind == 'withdraw' and step.items[0]['name']).to_be('Coins')
    test('stage 10 with an empty purse withdraws coins before walking to Osman', _fn18)

    def _fn19():
        step = decide(snap(S.SAVED, [], []))
        expect(step.kind == 'talk' and step.stop.npc).to_be('Hassan')
    test('stage 100 does not need coins — the gate is free once the prince is out', _fn19)

    def _fn20():
        expect(decide(snap(S.SPOKEN_OSMAN, [], [])).kind).to_be('wait')
    test('no coins anywhere at stage 20 is an honest wait, never a loop', _fn20)
describe('the purse comes before anything that walks', _fn15)

def _fn21():

    def _fn22():
        step = decide(snap(S.SPOKEN_OSMAN, PURSE))
        expect(step.kind == 'buy' and step.item).to_be('Bronze bar')
        expect(step.kind == 'buy' and step.shop.npc).to_be('Shantay')
    test('with coins, the first leg is the Al-Kharid bar', _fn22)

    def _fn23():
        step = decide(snap(S.SPOKEN_OSMAN, list(PURSE) + [[I.BRONZE_BAR.id, 1]]))
        expect(step.kind == 'buy' and step.item).to_be('Jug of water')
        expect(step.kind == 'buy' and step.shop.npc).to_be('Shantay')
    test('then the water, on the same Shantay trip', _fn23)

    def _fn24():
        step = decide(snap(S.SPOKEN_OSMAN, list(PURSE) + [[I.BRONZE_BAR.id, 1], [I.JUG_OF_WATER.id, 2]]))
        expect(step.kind == 'buy' and step.shop.npc).to_be('Shop keeper')
    test('then Lumbridge, before Varrock and before the west', _fn24)

    def _fn25():
        step = decide(kitted(S.SPOKEN_OSMAN))
        expect(step.kind == 'custom' and step.name).to_contain('Leela')
    test('everything held -> Leela hands the key over and promotes the stage', _fn25)
describe('stage 20 route order', _fn21)

def _fn26():

    def _fn27():
        step = decide(snap(S.SPOKEN_OSMAN, list(PURSE) + list(DISGUISE) + [[I.SOFT_CLAY.id, 1], [I.BRONZE_BAR.id, 1], [I.ROPE.id, 2], [I.BEER.id, 3], [I.JUG_OF_WATER.id, 1]]))
        expect(step.kind == 'talk' and step.stop.npc).to_be('Lady Keli')
    test('a soft clay in the pack routes to Lady Keli, not back to the mine', _fn27)

    def _fn28():
        step = decide(snap(S.SPOKEN_OSMAN, list(PURSE) + list(DISGUISE) + [[I.KEY_PRINT.id, 1], [I.BRONZE_BAR.id, 1], [I.ROPE.id, 2], [I.BEER.id, 3], [I.JUG_OF_WATER.id, 1]]))
        expect(step.kind == 'custom' and step.name).to_contain('Osman')
    test('a print plus a bar routes to the forge-and-collect', _fn28)

    def _fn29():
        step = decide(snap(S.SPOKEN_OSMAN, list(PURSE) + list(DISGUISE) + [[I.ROPE.id, 2], [I.BEER.id, 3], [I.JUG_OF_WATER.id, 1]], list(RICH) + [[I.PRINCE_KEY.id, 1]]))
        expect(step.kind == 'withdraw' and any([item['id'] == I.PRINCE_KEY.id for item in step.items])).to_be(True)
    test('a banked key is withdrawn rather than re-forged', _fn29)

    def _fn30():
        step = decide(snap(S.SPOKEN_OSMAN, list(PURSE) + [[I.BRONZE_BAR.id, 1], [I.JUG_OF_WATER.id, 2], [I.TINDERBOX.id, 1], [I.PINK_SKIRT.id, 1], [I.CLAY.id, 1], [I.REDBERRIES.id, 1], [I.POT_OF_FLOUR.id, 1], [I.BEER.id, 3], [I.ASHES.id, 1], [I.PLAIN_WIG.id, 1], [I.YELLOW_DYE.id, 1]]))
        expect(step.kind).to_be('custom')
        expect(step.kind == 'custom' and step.name).to_contain('dye')
    test('a plain wig plus dye routes to dyeing it, not to Ned for another wig', _fn30)

    def _fn31():
        step = decide(snap(S.SPOKEN_OSMAN, list(PURSE) + [[I.BRONZE_BAR.id, 1], [I.JUG_OF_WATER.id, 2], [I.TINDERBOX.id, 1], [I.PLAIN_WIG.id, 1], [I.YELLOW_DYE.id, 1], [I.PINK_SKIRT.id, 1]]))
        expect(step.kind == 'grab_ground' and step.item).to_be('Bronze pickaxe')
    test('the route reaches the pickaxe before the Draynor crafting', _fn31)
describe('stage 20 resumability', _fn26)

def _fn32():

    def _fn33():
        step = decide(kitted(S.PREP_FINISHED))
        expect(step.kind == 'talk' and step.stop.npc).to_be('Joe')
    test('30 -> Joe', _fn33)

    def _fn34():
        step = decide(kitted(S.GUARD_DRUNK))
        expect(step.kind == 'custom' and step.name).to_contain('Keli')
    test('40 -> the break-in', _fn34)

    def _fn35():
        step = decide(kitted(S.TIED_KELI))
        expect(step.kind == 'custom' and step.name).to_contain('Keli')
    test('50 -> the break-in', _fn35)

    def _fn36():
        step = decide(snap(S.PREP_FINISHED, list(PURSE) + list(DISGUISE) + [[I.PRINCE_KEY.id, 1], [I.ROPE.id, 1]]))
        expect(step.kind == 'talk' and step.stop.npc).to_be('Bartender')
    test('30 short of beer buys more rather than talking to Joe empty-handed', _fn36)
describe('stages 30 through 50', _fn32)

def _fn37():

    def _fn38():
        step = decide(snap(S.GUARD_DRUNK, list(PURSE) + [[I.BLOND_WIG.id, 1], [I.PINK_SKIRT.id, 1], [I.PRINCE_KEY.id, 1], [I.ROPE.id, 1]]))
        expect(step.kind).not_.to_be('wait')
        expect(step.kind).not_.to_be('done')
    test('a lost paste at stage 40 goes shopping, it does not wait', _fn38)

    def _fn39():
        step = decide(snap(S.TIED_KELI, list(PURSE) + [[I.PINK_SKIRT.id, 1], [I.PASTE.id, 1], [I.PRINCE_KEY.id, 1], [I.ROPE.id, 1]]))
        expect(step.kind).not_.to_be('wait')
    test('a lost wig at stage 50 rebuilds it from wool', _fn39)

    def _fn40():
        step = decide(snap(S.GUARD_DRUNK, list(PURSE) + list(DISGUISE) + [[I.ROPE.id, 1]]))
        expect(step.kind == 'custom' and step.name).to_contain('Leela')
        expect(step.kind == 'custom' and step.name).not_.to_contain('Osman')
    test('a lost key at stage 40 asks Leela to replace it, never Osman', _fn40)

    def _fn41():
        step = decide(snap(S.TIED_KELI, list(PURSE) + list(DISGUISE) + [[I.PRINCE_KEY.id, 1]]))
        expect(step.kind == 'talk' and step.stop.npc).to_be('Ned')
    test('a lost rope at stage 50 buys another from Ned', _fn41)

    def _fn42():
        step = decide(snap(S.GUARD_DRUNK, list(PURSE) + list(DISGUISE) + [[I.PRINCE_KEY.id, 1], [I.ROPE.id, 1], [I.PICKAXE.id, 1]]))
        expect(step.kind).not_.to_be('mine_rock')
    test('no clay is mined at stage 40 — Osman would refuse the print', _fn42)
describe('stages 30 through 50 recover a lost disguise instead of parking', _fn37)

def _fn43():
    for stage in S._fields.values():

        def _make__fn44(stage):
            def _fn44():
                step = decide(kitted(stage))
                expect(step.kind).to_be_defined()
            return _fn44
        test(f'stage {stage} never returns undefined', _make__fn44(stage))
describe('every stage produces a step', _fn43)
