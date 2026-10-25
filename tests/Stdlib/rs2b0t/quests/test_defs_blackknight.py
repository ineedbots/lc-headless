"""rs2b0t's test/api/ai/quests/defs/blackknight.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot

from rs2004.quests.defs.blackknight import decide
def snap(over=None):
    if over is None:
        over = Record({})
    _merged1 = {}
    for _k, _v in {'journal': 'in_progress', 'inv': {}, 'worn': set(), 'no_progress': 0, 'bank_coins': 0}.items():
        _merged1[_k] = _v
    for _k, _v in (over._fields if isinstance(over, Record) else over).items():
        _merged1[_k] = _v
    return QuestSnapshot().with_fields(_merged1)


def held(*names):
    return {_k: _v for _k, _v in [[n.lower(), 1] for n in names]}


def wearing(*names):
    return set([n.lower() for n in names])


def _fn2():
    def _fn3():
        expect(decide(snap(Record({'journal': 'complete'}))).kind).to_be('done')
    test('complete → done', _fn3)

    def _fn4():
        s = decide(snap(Record({'journal': 'not_started'})))
        expect(s.kind).to_be('talk')
        expect(s.kind == 'talk' and s.stop.npc).to_be('Sir Amik Varze')
    test('not started → talk Sir Amik', _fn4)

    def _fn5():
        s = decide(snap(Record({'worn': wearing('iron chainbody'), 'inv': held('Bronze med helm', 'Cabbage')})))
        expect(s.kind).to_be('equip')
        expect(s.kind == 'equip' and s.item).to_be('Bronze med helm')
    test('in progress, disguise not worn → equip the missing piece', _fn5)

    def _fn6():
        s = decide(snap(Record({'worn': wearing('iron chainbody', 'bronze med helm'), 'inv': held('Cabbage')})))
        expect(s.kind).to_be('custom')
        expect(s.kind == 'custom' and s.name).to_be('infiltrate')
    test('in progress, disguise worn, cabbage held → infiltrate', _fn6)

    def _fn7():
        s = decide(snap(Record({'worn': wearing('iron chainbody', 'bronze med helm'), 'inv': {}})))
        expect(s.kind).to_be('talk')
        expect(s.kind == 'talk' and s.stop.npc).to_be('Sir Amik Varze')
    test('in progress, disguise worn, cabbage GONE (sabotaged) → talk Sir Amik', _fn7)

    def _fn8():
        expect(decide(snap(Record({'journal': 'unknown'}))).kind).to_be('wait')
    test('unknown journal → wait', _fn8)


describe('Black Knight decide', _fn2)
