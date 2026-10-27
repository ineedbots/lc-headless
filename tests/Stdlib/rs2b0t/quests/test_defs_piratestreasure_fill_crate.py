"""rs2b0t's piratestreasure-fill-crate.test.ts: fill ten bananas through one free slot."""
from rs2004 import execution
from rs2004.catalogs.tasks import sustain
from rs2004.entities import locs
from rs2004.items import inventory
from rs2004.traversal import traversal
from rs2004.quests.defs.piratestreasure import karamja
from rs2004.catalogs.record import Record

def fill_one_slot():
    state = {'held': 0, 'packed': 0, 'picks': 0}
    def search(log):
        return Record({'rum': False, 'bananas': state['packed']})
        yield
    def pick(op):
        expect(state['held']).to_be(0)
        state['held'] += 1
        state['picks'] += 1
        return True
    def pack(*args):
        state['held'] -= 1
        state['packed'] += 1
        return True
        yield
    spy_on(karamja, 'search_banana_crate').mock_implementation(search)
    spy_on(inventory, 'count_by_id').mock_implementation(lambda id: state['held'] if id == 1963 else 0)
    spy_on(inventory, 'is_full').mock_implementation(lambda: state['held'] == 1)
    spy_on(execution, 'delay_until').mock_implementation(instant_until)
    spy_on(sustain, 'run').mock_implementation(instant_ticks)
    spy_on(traversal, 'walk_resilient').mock_implementation(lambda *args, **kwargs: success())
    spy_on(karamja, 'settle_scene').mock_implementation(instant_ticks)
    spy_on(karamja, 'use_on_loc').mock_implementation(pack)
    tree = Fake(id=2073, name='Banana Tree', distance=lambda: 1, actions=lambda: ['Search'], interact=pick)
    spy_on(locs, 'query').mock_implementation(querying(lambda: [tree]))
    expect(run_wait(karamja.fill_crate(lambda m: None))).to_be(True)
    expect(state['packed']).to_be(10)
    expect(state['picks']).to_be(10)
test('fills ten bananas with only one free inventory slot', fill_one_slot)

def success():
    return True
    yield
