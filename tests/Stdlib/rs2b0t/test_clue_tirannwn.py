"""rs2b0t's test/api/ai/clues/tirannwnTravel.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's test and expect. Its
teleport cases plan on a fake route here, since the route search and its spell, rune and policy checks are the C++
core's and have tests of their own."""

from rs2004 import execution
from rs2004 import traversal as traversal_module
from rs2004.catalogs.tasks import sustain
from rs2004.clues import guardian
from rs2004.clues.executor import ClueExecutor
from rs2004.clues.solve import walk_to_bank
from rs2004.clues.travel import crosses_tirannwn, in_kharazi, set_trail_teleports, tirannwn_stage, trail_walk_opts, walk_across_tirannwn
from rs2004.execution import event_signal
from rs2004.navigation import navigator
from rs2004.quests.defs.legends import jungle
from rs2004.quests.defs.legends.areas import LQ_TILE
from rs2004.quests.defs.regicide.areas import RG_TILE
from rs2004.quests.defs.regicide.journal import RG_STAGE
from rs2004.quests.defs.regicide.pockets import ARDOUGNE, pocket_at
from rs2004.quests.defs.regicide.seams import REGICIDE_SEAMS

JUNGLE_DIG = Tile(2950, 2902, 0)
ISAFDAR_DIG = Tile(2181, 3206, 0)
SPELL_HOP = {'kind': 'teleport', 'family': 'spell', 'loc_name': 'Ardougne', 'teleport_id': 'ardougne', 'to_tile': [2661, 3301], 'to_level': 0}

W = {'here': None, 'walks': [], 'crossings': 0, 'plans': 0, 'pending': False, 'casts': 0, 'lands': True, 'accepts': True, 'route': None, 'exits': 0, 'entries': 0}


def log(line):
    pass


def where():
    return W['here']


def at(tile):
    return [tile.x, tile.z, tile.level]


def plain_walk(dest, **opts):
    if event_signal.pending():
        return False
    W['here'] = Tile(dest.x, dest.z, dest.level)
    W['walks'].append([W['here'], opts])
    return True
    yield


def no_upkeep():
    return None
    yield


def cross(seam):
    W['crossings'] += 1
    here = pocket_at(W['here'])
    from_ = here if here is not None else ARDOUGNE
    to = [side for side in seam.sides if side.pocket != from_][0]
    W['here'] = Tile(to.stand.x, to.stand.z, 0)
    return True


def seam_loc(seam):
    tile = Tile(seam.x, seam.z, 0)
    return Fake(id=seam.loc_id, name=seam.loc, tile=lambda: tile, distance=lambda: tile.distance_to(W['here']), actions=lambda: [seam.op], interact=lambda op: cross(seam))


def plan(start, dest, **opts):
    W['plans'] += 1
    return W['route']


def cast(name):
    W['casts'] += 1
    if not W['accepts']:
        return False
    if W['lands']:
        W['here'] = Tile(2661, 3301, 0)
    return True


def world(here):
    set_trail_teleports(True)
    W['here'] = here
    W['walks'] = []
    W['crossings'] = 0
    W['plans'] = 0
    W['pending'] = False
    W['casts'] = 0
    W['lands'] = True
    W['accepts'] = True
    W['exits'] = 0
    W['entries'] = 0
    W['route'] = Fake(ok=False, raw={'ok': False})
    spy_on(event_signal, 'pending', impl=lambda: W['pending'])
    spy_on(navigator, 'find_path', impl=plan)
    spy_on(game, 'tile', impl=where)
    spy_on(quests, 'status', returns='complete')
    spy_on(sustain, 'run', impl=no_upkeep)
    spy_on(execution, 'delay_ticks', impl=instant_ticks)
    spy_on(execution, 'delay_until', impl=instant_until)
    spy_on(traversal, 'walk_resilient', impl=plain_walk)
    spy_on(game, 'teleport', impl=cast)
    patch(traversal_module, 'local_tile', where)
    rows = [seam_loc(seam) for seam in REGICIDE_SEAMS]
    spy_on(locs, 'query', impl=querying(lambda: rows))


def teleport_planned():
    W['route'] = Fake(ok=True, raw={'ok': True, 'waypoints': [{'x': 2205, 'z': 3252, 'level': 0}, {'x': 2661, 'z': 3301, 'level': 0, 'transport': SPELL_HOP}]})


def on_foot_after_mainland(enabled):
    world(Tile(3168, 3041, 0))
    set_trail_teleports(enabled)
    expect(run_wait(walk_across_tirannwn(RG_TILE.IORWERTH, 3, log, trail_walk_opts(log)))).to_be(True)
    first = W['walks'][0]
    expect(at(first[0])).to_equal([2384, 3335, 0])
    expect(first[1]['use_teleport_catalog']).to_be(enabled)
    expect(first[1]['policy']['use_teleports']).to_be(enabled)
    expect(len(W['walks'])).to_be_greater_than(2)
    for walk in W['walks'][1:]:
        expect(walk[1]['policy']['use_teleports']).to_be(False)
    expect(at(W['here'])).to_equal(at(RG_TILE.IORWERTH))
    set_trail_teleports(True)


test('desert to Iorwerth with teleports on uses them on the mainland only', lambda: on_foot_after_mainland(True))
test('desert to Iorwerth with teleports off walks all the way', lambda: on_foot_after_mainland(False))


def crossings_to_bank():
    world(RG_TILE.IORWERTH)
    expect(run_wait(walk_to_bank(RG_TILE.ARDOUGNE_BANK, log))).to_be(True)
    expect(W['walks'][-1][1]['policy']['use_teleports']).to_be(True)
    for walk in W['walks'][:-1]:
        expect(walk[1]['policy']['use_teleports']).to_be(False)
    expect(at(W['here'])).to_equal(at(RG_TILE.ARDOUGNE_BANK))


test('without an available teleport, leaving Iorwerth walks the crossings before the mainland bank', crossings_to_bank)


def teleports_out():
    world(RG_TILE.IORWERTH)
    teleport_planned()
    expect(run_wait(walk_to_bank(RG_TILE.ARDOUGNE_BANK, log))).to_be(True)
    expect(W['casts']).to_be(1)
    expect(W['crossings']).to_be(0)
    expect(at(W['here'])).to_equal(at(RG_TILE.ARDOUGNE_BANK))


test('leaving Iorwerth teleports before approaching any exit crossing', teleports_out)


def falls_back(accepted):
    world(RG_TILE.IORWERTH)
    teleport_planned()
    W['accepts'] = accepted
    W['lands'] = False
    expect(run_wait(walk_to_bank(RG_TILE.ARDOUGNE_BANK, log))).to_be(True)
    expect(W['casts']).to_be(1)
    expect(W['crossings']).to_be_greater_than(0)
    expect(at(W['here'])).to_equal(at(RG_TILE.ARDOUGNE_BANK))


test('a rejected teleport falls back to crossings', lambda: falls_back(False))
test('an unlanded teleport falls back to crossings', lambda: falls_back(True))


def disabled_never_plans():
    world(RG_TILE.IORWERTH)
    set_trail_teleports(False)
    expect(run_wait(walk_across_tirannwn(RG_TILE.ARDOUGNE_BANK, 1, log, trail_walk_opts(log)))).to_be(True)
    expect(W['plans']).to_be(0)
    expect(W['crossings']).to_be_greater_than(0)
    set_trail_teleports(True)


test('disabled teleports leave Iorwerth using crossings without planning a teleport', disabled_never_plans)


def between_pockets():
    world(RG_TILE.IORWERTH)
    expect(run_wait(walk_across_tirannwn(ISAFDAR_DIG, 0, log, trail_walk_opts(log)))).to_be(True)
    expect(W['plans']).to_be(0)
    expect(W['crossings']).to_be_greater_than(0)


test('travel between Isafdar pockets stays on foot', between_pockets)


def event_while_planning():
    world(RG_TILE.IORWERTH)

    def interrupted(start, dest, **opts):
        W['pending'] = True
        return W['route']

    spy_on(navigator, 'find_path', impl=interrupted)
    expect(run_wait(walk_across_tirannwn(RG_TILE.ARDOUGNE_BANK, 1, log, trail_walk_opts(log)))).to_be(False)
    expect(W['casts']).to_be(0)
    expect(W['crossings']).to_be(0)
    expect(at(W['here'])).to_equal(at(RG_TILE.IORWERTH))


test('an event while planning the exit prevents both casting and crossing', event_while_planning)


def stops_at_approach(dest, **opts):
    W['walks'].append([Tile(dest.x, dest.z, dest.level), opts])
    return False
    yield


def dispatch(enabled):
    world(Tile(3168, 3041, 0))
    set_trail_teleports(enabled)
    spy_on(traversal, 'walk_resilient', impl=stops_at_approach)
    run_wait(ClueExecutor().walk_leg(RG_TILE.IORWERTH, log))
    expect(at(W['walks'][0][0])).to_equal([2384, 3335, 0])
    expect(W['walks'][0][1]['policy']['use_teleports']).to_be(enabled)
    set_trail_teleports(True)


test('the Iorwerth clue dispatch preserves teleports on', lambda: dispatch(True))
test('the Iorwerth clue dispatch preserves teleports off', lambda: dispatch(False))


def leave_ok(line_log):
    W['exits'] += 1
    W['here'] = LQ_TILE.JUNGLE_MOUTH
    return True
    yield


def leave_refused(line_log):
    return False
    yield


def jungle_tile_walk(dest, **opts):
    if in_kharazi(W['here']):
        return False
    W['here'] = Tile(dest.x, dest.z, dest.level)
    W['walks'].append([W['here'], opts])
    return True
    yield


def cross_from_jungle(dest, enabled):
    world(JUNGLE_DIG)
    set_trail_teleports(enabled)
    patch(jungle, 'leave_jungle', leave_ok)
    spy_on(traversal, 'walk_resilient', impl=jungle_tile_walk)
    expect(run_wait(walk_across_tirannwn(dest, 0, log, trail_walk_opts(log, 0)))).to_be(True)
    expect(W['exits']).to_be(1)
    expect(at(W['here'])).to_equal(at(dest))
    expect(W['walks'][0][1]['policy']['use_teleports']).to_be(enabled)
    set_trail_teleports(True)


def jungle_case(dest, enabled):
    return lambda: cross_from_jungle(dest, enabled)


for _dest in [Tile(2181, 3206, 0), Tile(2209, 3161, 0), RG_TILE.IORWERTH]:
    test(f'leaves Kharazi before routing to Isafdar {_dest.x},{_dest.z}, teleports on', jungle_case(_dest, True))
    test(f'leaves Kharazi before routing to Isafdar {_dest.x},{_dest.z}, teleports off', jungle_case(_dest, False))


def failed_exit():
    world(JUNGLE_DIG)
    patch(jungle, 'leave_jungle', leave_refused)
    expect(run_wait(walk_across_tirannwn(ISAFDAR_DIG, 0, log, trail_walk_opts(log)))).to_be(False)
    expect(W['walks']).to_equal([])
    expect(at(W['here'])).to_equal(at(JUNGLE_DIG))


test('a failed jungle exit stops before attempting the Arandar approach', failed_exit)


def enter_ok(line_log):
    expect(at(W['here'])).to_equal(at(LQ_TILE.JUNGLE_MOUTH))
    W['entries'] += 1
    W['here'] = LQ_TILE.JUNGLE_INSIDE
    return True
    yield


def enter_refused(line_log):
    return False
    yield


def uncut_refused_walk(dest, **opts):
    if in_kharazi(dest) and W['entries'] == 0:
        return False
    W['here'] = Tile(dest.x, dest.z, dest.level)
    W['walks'].append([W['here'], opts])
    return True
    yield


def both_boundaries(enabled):
    world(ISAFDAR_DIG)
    set_trail_teleports(enabled)
    patch(jungle, 'enter_jungle', enter_ok)
    spy_on(traversal, 'walk_resilient', impl=uncut_refused_walk)
    expect(run_wait(walk_across_tirannwn(JUNGLE_DIG, 0, log, trail_walk_opts(log, 0)))).to_be(True)
    expect(W['entries']).to_be(1)
    expect(at(W['here'])).to_equal(at(JUNGLE_DIG))
    mouth = [walk for walk in W['walks'] if walk[0].x == 2816 and walk[0].z == 2940]
    expect(mouth[0][1]['policy']['use_teleports']).to_be(enabled)
    set_trail_teleports(True)


test('Isafdar to Kharazi crosses both boundaries in order, teleports on', lambda: both_boundaries(True))
test('Isafdar to Kharazi crosses both boundaries in order, teleports off', lambda: both_boundaries(False))


def failed_entry():
    world(RG_TILE.IORWERTH)
    patch(jungle, 'enter_jungle', enter_refused)
    expect(run_wait(walk_across_tirannwn(JUNGLE_DIG, 0, log, trail_walk_opts(log)))).to_be(False)
    expect(at(W['here'])).to_equal(at(LQ_TILE.JUNGLE_MOUTH))


test('a failed jungle entry prevents a direct walk through the uncut band', failed_entry)


def stage_gates():
    spy_on(quests, 'status', returns='complete')
    expect(tirannwn_stage()).to_be(RG_STAGE.COMPLETE)
    spy_on(quests, 'status', returns='in_progress')
    expect(tirannwn_stage()).to_be(RG_STAGE.NOT_STARTED)


test("the seam graph is handed Regicide's last stage only once the journal reads complete", stage_gates)


def crossing_either_end():
    world(Tile(3168, 3041, 0))
    expect(crosses_tirannwn(RG_TILE.IORWERTH)).to_be(True)
    expect(crosses_tirannwn(RG_TILE.ARDOUGNE_BANK)).to_be(False)
    world(RG_TILE.IORWERTH)
    expect(crosses_tirannwn(RG_TILE.ARDOUGNE_BANK)).to_be(True)


test('a walk crosses Tirannwn when either end is in a pocket', crossing_either_end)


class TwoDigs:
    """A pack holding a Kharazi dig that reports an Isafdar one: rs2b0t's case for one running executor finishing both."""

    def __init__(self):
        self.pack = [self.item(3536, 'Clue scroll'), self.item(952, 'Spade'), self.item(2574, 'Sextant'), self.item(2575, 'Watch'), self.item(2576, 'Chart'),
                     self.item(2448, 'Superantipoison(4)'), self.item(385, 'Shark', 12), self.item(975, 'Machete'), self.item(1351, 'Bronze axe')]
        self.digs = 0
        self.fights = 0
        self.lines = []

    def item(self, id, name, count=1):
        return Fake(id=id, name=name, count=count, slot=0, noted=False, actions=lambda: ['Dig'], interact=lambda op: self.dig(id, op))

    def swap(self, old, new):
        self.pack = [self.item(new, 'Clue scroll') if i.id == old else i for i in self.pack]

    def dig(self, id, op):
        if id != 952 or op != 'Dig':
            return False
        isafdar = self.digs >= 2
        expect(at(W['here'])).to_equal(at(ISAFDAR_DIG if isafdar else JUNGLE_DIG))
        self.digs += 1
        if self.digs == 2:
            self.swap(3536, 3562)
        if self.digs == 4:
            self.swap(3562, 2677)
            W['pending'] = True
        return True

    def fight(self, *args):
        self.fights += 1
        W['here'] = Tile(W['here'].x + 3, W['here'].z, 0)
        return 'killed'
        yield

    def first(self, name):
        rows = [i for i in self.pack if i.name == name]
        return rows[0] if len(rows) > 0 else None


def both_digs():
    world(JUNGLE_DIG)
    w = TwoDigs()
    sword = Fake(id=1305, name='Dragon longsword', count=1, slot=3, noted=False, actions=lambda: [])
    patch(jungle, 'leave_jungle', leave_ok)
    spy_on(traversal, 'walk_resilient', impl=lambda dest, **opts: boundary_walk(dest))
    spy_on(inventory, 'items', impl=lambda: w.pack)
    spy_on(inventory, 'first', impl=w.first)
    spy_on(inventory, 'count_by_id', impl=lambda id: sum([i.count for i in w.pack if i.id == id]))
    spy_on(equipment, 'items', returns=[sword])
    spy_on(equipment, 'contains', impl=lambda name: name == sword.name)
    spy_on(skills, 'level', returns=70)
    spy_on(chat_dialog, 'is_open', returns=False)
    spy_on(chat_dialog, 'can_continue', returns=False)
    spy_on(bank, 'is_open', returns=False)
    spy_on(reader, 'main_modal', returns=-1)
    spy_on(ground_items, 'query', impl=querying(lambda: []))
    spy_on(guardian.GuardianProtection, 'prepare', impl=lambda *a: instant_until(lambda: True))
    spy_on(guardian.GuardianEncounter, 'fight', impl=w.fight)
    outcome = run_wait(ClueExecutor().solve_held_clue(lambda line: w.lines.append(line)))
    expect([outcome, w.digs, w.fights, W['exits']]).to_equal(['yield', 4, 2, 1])
    expect(any([i.id == 2677 for i in w.pack])).to_be(True)
    expect([line for line in w.lines if 'abandon' in line or 'resetting' in line]).to_equal([])


def boundary_walk(dest):
    if in_kharazi(W['here']) != in_kharazi(dest):
        return False
    W['here'] = Tile(dest.x, dest.z, dest.level)
    return True
    yield


test('the same running executor finishes Kharazi then the reported Isafdar dig without abandoning', both_digs)
