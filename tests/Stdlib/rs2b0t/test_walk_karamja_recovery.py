"""rs2b0t's walking/karamjaRecovery.test.ts: earn the fare and retry, preserving failures."""
from rs2004 import execution
import rs2004.traversal as walking
from rs2004.execution import event_signal
from rs2004.game import game
from rs2004.items import inventory
from rs2004.geometry import Tile
from rs2004.traversal import traversal
from rs2004.routeplan import MissingItem
from rs2004 import karamja_recovery as recovery
from rs2004.quests.defs.piratestreasure import karamja
from rs2004.quests.exec import primitives

DOCK = Tile(2772, 3235, 0)
MAINLAND = Tile(3093, 3243, 0)
S = {}

def prepare():
    S.update({'here': DOCK, 'coins': 0, 'full': False, 'pending': False, 'filled': False, 'fill_ok': True,
              'paid': False, 'talks': 0, 'fills': 0, 'teleport': False, 'recursive': False, 'missing': 'Coins'})
    recovery.recovering = False
    from rs2004.catalogs.tasks import sustain
    spy_on(sustain, 'run').mock_implementation(instant_ticks)
    spy_on(game, 'tile').mock_implementation(lambda: S['here'])
    spy_on(walking, 'local_tile').mock_implementation(lambda: S['here'])
    spy_on(inventory, 'count_by_id').mock_implementation(lambda id: S['coins'] if id == 995 else 0)
    spy_on(inventory, 'is_full').mock_implementation(lambda: S['full'])
    spy_on(event_signal, 'pending').mock_implementation(lambda: S['pending'])
    def walk(dest, *args, **kwargs):
        if dest == MAINLAND and S['coins'] < 30 and not S['teleport']:
            traversal.last_outcome = 'failed'
            traversal.last_missing_gate_items = [MissingItem(S['missing'], 30 - S['coins'])]
            return False
        S['here'] = dest
        traversal.last_outcome = 'arrived'
        traversal.last_missing_gate_items = []
        return True
        yield
    def talk(*args):
        S['talks'] += 1
        expect(args[0]).to_be('Luthas')
        if S['recursive']:
            result = yield from traversal.walk_to(MAINLAND)
            return result
        if S['paid'] or S['filled']:
            S['coins'] += 30
        return True
    def fill(*args):
        S['fills'] += 1
        S['filled'] = S['fill_ok']
        return S['fill_ok']
        yield
    spy_on(traversal, '_walk_to').mock_implementation(walk)
    spy_on(primitives, 'talk_strict').mock_implementation(talk)
    spy_on(karamja, 'fill_crate').mock_implementation(fill)
before_each(prepare)

def ready_payment():
    S['paid'] = True
    expect(run_wait(traversal.walk_to(MAINLAND))).to_be(True)
    expect(S['talks']).to_be(1)
    expect(S['here']).to_equal(MAINLAND)
test('collects an existing payment and retries the destination', ready_payment)

def affordable():
    S['coins'] = 30
    expect(run_wait(traversal.walk_to(MAINLAND))).to_be(True)
    expect(S['talks']).to_be(0)
test('keeps an already affordable route', affordable)

def empty_pack():
    expect(run_wait(traversal.walk_resilient(MAINLAND, attempts=2))).to_be(True)
    expect(S['talks']).to_be(2)
    expect(S['fills']).to_be(1)
    expect(S['here']).to_equal(MAINLAND)
test('earns a fare from an empty pack before a resilient walk', empty_pack)

def no_bananas():
    S['fill_ok'] = False
    expect(run_wait(traversal.walk_to(MAINLAND))).to_be(False)
    expect(traversal.last_outcome).to_be('failed')
    expect(traversal.last_missing_gate_items).to_equal([MissingItem('Coins', 30)])
    expect(recovery.recovering).to_be(False)
test('preserves the missing fare after a failed plantation job', no_bananas)

def recursive():
    S['recursive'] = True
    expect(run_wait(traversal.walk_to(MAINLAND))).to_be(False)
    expect(S['talks']).to_be(1)
test('does not recursively recover a walk inside the job', recursive)

def teleport():
    S['teleport'] = True
    expect(run_wait(traversal.walk_to(MAINLAND))).to_be(True)
    expect(S['talks']).to_be(0)
test('uses an available teleport first', teleport)

def full():
    S['full'] = True
    expect(run_wait(traversal.walk_to(MAINLAND))).to_be(False)
    expect(S['talks']).to_be(0)
test('keeps a full inventory', full)

def mainland():
    S['here'] = Tile(3008, 3200, 0)
    expect(run_wait(traversal.walk_to(MAINLAND))).to_be(False)
    expect(S['talks']).to_be(0)
test('does not earn coins on the mainland', mainland)

def pending():
    S['pending'] = True
    expect(run_wait(traversal.walk_to(MAINLAND))).to_be(False)
    expect(S['talks']).to_be(0)
test('yields to random events', pending)

def rope():
    S['missing'] = 'Rope'
    expect(run_wait(traversal.walk_to(MAINLAND))).to_be(False)
    expect(S['talks']).to_be(0)
test('does not replace a missing rope with a banana job', rope)

def exception_cleanup():
    def fail(*args):
        raise ValueError('job failed')
        yield
    spy_on(karamja, 'fill_crate').mock_implementation(fail)
    try:
        run_wait(traversal.walk_to(MAINLAND))
        raise AssertionError('expected the job error')
    except ValueError:
        pass
    expect(recovery.recovering).to_be(False)
test('clears the recursion guard after an exception', exception_cleanup)
