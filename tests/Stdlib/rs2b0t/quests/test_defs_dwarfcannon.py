"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/dwarfcannon.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.defs.dwarfcannon import decide, dwarfcannon
from rs2004.quests.defs.dwarfcannon.areas import CANNON_PARTS, MC_OBJ, RAILINGS
from rs2004.quests.defs.dwarfcannon.journal import MC_FLAG, MC_STAGE
from rs2004.quests.defs.dwarfcannon.repair import CANNON_CYCLE, cannon_outcome, in_cave
from rs2004.quests.defs import def_by_id
from rs2004.geometry import Tile
from rs2004.quests.engine.types import QuestSnapshot
from rs2004.quests.engine.types import QuestProgress

def snap(options=None):
    if options is None:
        options = Record({})
    stage = (options.stage if options.stage is not None else MC_STAGE.NOT_STARTED)
    inv_ids = {}
    for id in (options.inv_ids if options.inv_ids is not None else []):
        _v1 = inv_ids.get(id)
        inv_ids[id] = ((_v1 if _v1 is not None else 0)) + 1
    return QuestSnapshot(**{
        'journal': (options.journal if options.journal is not None else (('not_started' if stage == MC_STAGE.NOT_STARTED else 'in_progress'))),
        'inv': {},
        'inv_ids': inv_ids,
        'worn': set(),
        'no_progress': 0,
        'bank_coins': 0,
        'stage': stage,
        'progress': QuestProgress(stage, set((options.flags if options.flags is not None else []))),
        'bank': {},
        'bank_ids': {},
        'bank_known': True,
        'tile': (Tile(2571, 3463, 0) if options.tile is None else options.tile),
        'free_slots': 20,
    })


def _fn2():
    def _fn3():
        expect(decide(snap(Record({'journal': 'unknown'}))).kind).to_be('wait')
    test('an unloaded journal waits rather than restarting the quest', _fn3)

    def _fn4():
        expect(decide(snap(Record({'journal': 'complete', 'stage': MC_STAGE.COMPLETE}))).kind).to_be('done')
    test('a complete journal is done', _fn4)

    def _fn5():
        step = decide(snap())
        expect(step.kind).to_be('talk')
        expect(step.kind == 'talk' and step.stop.npc).to_be('Dwarf Commander')
    test('not started talks to the Commander', _fn5)

    def _fn6():
        step = decide(snap(Record({'stage': MC_STAGE.RAILINGS, 'flags': [MC_FLAG.RAILINGS_DONE]})))
        expect(step.kind).to_be('talk')
    test('railings done reports back to the Commander', _fn6)

    def _fn7():
        step = decide(snap(Record({'stage': MC_STAGE.GUARD_TOWER, 'flags': [MC_FLAG.HAS_REMAINS], 'inv_ids': [MC_OBJ.REMAINS.id]})))
        expect(step.kind).to_be('talk')
    test('holding the remains reports back to the Commander', _fn7)

    def _fn8():
        expect(decide(snap(Record({'stage': MC_STAGE.CHILD_RESCUED}))).kind).to_be('talk')
    test('the child is rescued, so the Commander is next', _fn8)

    def _fn9():
        expect(decide(snap(Record({'stage': MC_STAGE.CANNON_FIXED}))).kind).to_be('talk')
    test('the cannon is fixed, so the Commander is next', _fn9)

    def _fn10():
        step = decide(snap(Record({'stage': MC_STAGE.SEE_NULODION})))
        expect(step.kind).to_be('talk')
        expect(step.kind == 'talk' and step.stop.npc).to_be('Nulodion')
    test('stage 9 talks to Nulodion', _fn10)

    def _fn11():
        step = decide(snap(Record({'stage': MC_STAGE.RETURN_NOTES, 'inv_ids': [MC_OBJ.NOTES.id, MC_OBJ.MOULD.id]})))
        expect(step.kind).to_be('talk')
        expect(step.kind == 'talk' and step.stop.npc).to_be('Dwarf Commander')
    test('stage 10 holding both hands them to the Commander', _fn11)

    def _fn12():
        step = decide(snap(Record({'stage': MC_STAGE.RETURN_NOTES, 'inv_ids': [MC_OBJ.NOTES.id]})))
        expect(step.kind).to_be('talk')
        expect(step.kind == 'talk' and step.stop.npc).to_be('Nulodion')
    test('stage 10 missing the mould goes back to Nulodion for a replacement', _fn12)


describe('dwarfcannon decide', _fn2)


def _fn13():
    def _fn14():
        step = decide(snap(Record({'stage': MC_STAGE.RAILINGS})))
        expect(step.kind).to_be('custom')
        expect(step.kind == 'custom' and step.name).to_contain('railing')
    test('stage 1 without the flag runs the railing loop', _fn14)

    def _fn15():
        expect(RAILINGS).to_have_length(6)
        expect(len(set([r.id for r in RAILINGS]))).to_be(6)
        expect(len(set([f'{r.at.x},{r.at.z}' for r in RAILINGS]))).to_be(6)
    test('six railings, each a distinct loc id and tile', _fn15)

    def _fn16():
        expect([r.id for r in RAILINGS]).to_equal([15, 16, 17, 18, 19, 20])
    test('the loc ids are the contiguous content block 15..20', _fn16)


describe('railings', _fn13)


def _fn17():
    def _fn18():
        step = decide(snap(Record({'stage': MC_STAGE.GUARD_TOWER})))
        expect(step.kind).to_be('custom')
        expect(step.kind == 'custom' and step.name).to_contain('watchtower')
    test('stage 2 without the remains climbs the tower', _fn18)

    def _fn19():
        step = decide(snap(Record({'stage': MC_STAGE.GUARD_TOWER, 'inv_ids': [MC_OBJ.REMAINS.id]})))
        expect(step.kind).to_be('talk')
    test('the remains outrank a journal that has not caught up', _fn19)


describe('watchtower', _fn17)


def _fn20():
    def _fn21():
        step = decide(snap(Record({'stage': MC_STAGE.GOBLIN_CAVE})))
        expect(step.kind).to_be('custom')
    test('stage 3 enters the cave', _fn21)

    def _fn22():
        step = decide(snap(Record({'stage': MC_STAGE.FIND_CHILD, 'tile': Tile(2620, 9797, 0)})))
        expect(step.kind).to_be('custom')
        expect(step.kind == 'custom' and step.name).to_contain('crate')
    test('stage 4 searches the crate', _fn22)

    def _fn23():
        step = decide(snap(Record({'stage': MC_STAGE.CHILD_RESCUED, 'tile': Tile(2571, 9850, 0)})))
        expect(step.kind).to_be('custom')
        expect(step.kind == 'custom' and step.name).to_contain('mud pile')
    test('the rescued child is walked out of the cave before the Commander', _fn23)

    def _fn24():
        expect(in_cave(Record({'z': 9797}))).to_be(True)
        expect(in_cave(Record({'z': 3463}))).to_be(False)
        expect(in_cave(None)).to_be(False)
    test('the cave is recognised by the underground z band', _fn24)


describe('goblin cave', _fn20)


def _fn25():
    def _fn26():
        step = decide(snap(Record({'stage': MC_STAGE.FIX_CANNON, 'inv_ids': [MC_OBJ.TOOLKIT.id]})))
        expect(step.kind).to_be('custom')
        expect(step.kind == 'custom' and step.name).to_contain('cannon')
    test('stage 6 runs the repair loop', _fn26)

    def _fn27():
        step = decide(snap(Record({'stage': MC_STAGE.FIX_CANNON})))
        expect(step.kind).to_be('talk')
        expect(step.kind == 'talk' and step.stop.npc).to_be('Dwarf Commander')
    test('a lost toolkit sends the bot back to the Commander, who re-issues one', _fn27)

    def _fn28():
        expect(CANNON_PARTS).to_equal(['Pipe', 'Barrel', 'Axle', 'Shaft'])
    test('four damaged components, in menu order', _fn28)

    def _fn29():
        expect(cannon_outcome("It's a strange dwarf contraption.")).to_be('done')
    test('the contraption line ends the loop, because the stage has moved past the repair', _fn29)

    def _fn30():
        expect(cannon_outcome('After some tinkering you manage to fix it.')).to_be('fixed')
        expect(cannon_outcome("You've already fixed this part of the cannon.")).to_be('already')
        expect(cannon_outcome("You try, but can't quite find the problem.")).to_be('retry')
        expect(cannon_outcome("It's too hard you fail to fix it.")).to_be('retry')
    test('the repair outcomes still read off their own messages', _fn30)

    def _fn31():
        for line in [
        "It's a strange dwarf contraption.",
        'After some tinkering you manage to fix it.',
        "You've already fixed this part of the cannon.",
        "You try, but can't quite find the problem.",
        "It's too hard you fail to fix it.",
    ]:
            expect(CANNON_CYCLE(line)).to_be(True)
    test('every outcome message also ends the drive, or the step waits out its timeout', _fn31)


describe('cannon repair', _fn25)


def _fn32():
    def _fn33():
        expect(def_by_id('mcannon')).to_be(dwarfcannon)
    test('is registered', _fn33)

    def _fn34():
        expect(dwarfcannon.record.items).to_equal([])
    test('requires no items, so nothing is provisioned up front', _fn34)

    def _fn35():
        for name in ['tool kit', 'dwarf remains', "nulodion's notes", 'ammo mould', 'railing']:
            expect(dwarfcannon.tools).to_contain(name)
    test('keeps every carried quest item off the spillover deposit', _fn35)


describe('dwarfcannon module', _fn32)
