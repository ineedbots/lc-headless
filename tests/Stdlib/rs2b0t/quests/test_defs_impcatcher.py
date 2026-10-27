"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/impcatcher.test.ts (MIT, see thirdparty/rs2b0t)."""
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot

def _snapshot(**fields):
    for name in ['inv', 'inv_ids', 'bank', 'bank_ids']:
        if isinstance(fields.get(name), (Record, Fake)):
            fields[name] = fields[name]._fields
    return QuestSnapshot(**fields)
from rs2004.quests.exec.primitives import pick_preferred
from rs2004.quests.defs import def_by_id
from rs2004.quests.defs.impcatcher import IMP_BEADS, IMP_FIELD, IMP_SPAWNS, IMP_STAND, MIZGOG, decide, gather_bead, idle_progress, imp_census, search_target, tally_names, impcatcher, nearest_reachable, pick_imp
MAINLAND = Fake(**{'x': 3093, 'z': 3243, 'level': 0})
KARAMJA = Fake(**{'x': 2845, 'z': 3175, 'level': 0})

def with_coins(inv):
    return (inv if inv is not None else [['coins', 1000]]) if inv is None or any([name == 'coins' for name, count in inv]) else list(inv) + [['coins', 1000]]

def snap(journal, inv=None, inv_ids=None, bank=None, bank_ids=None, bank_known=None, bank_coins=None, free_slots=None, tile=None):
    return _snapshot(**{'journal': journal, 'inv': {_k: _v for _k, _v in with_coins(inv)}, 'inv_ids': {_k: _v for _k, _v in (inv_ids if inv_ids is not None else [])}, 'worn': set(), 'no_progress': 0, 'bank_coins': bank_coins if bank_coins is not None else 1000000, 'bank': {_k: _v for _k, _v in (bank if bank is not None else [])}, 'bank_ids': {_k: _v for _k, _v in (bank_ids if bank_ids is not None else [])}, 'bank_known': bank_known if bank_known is not None else True, 'free_slots': free_slots if free_slots is not None else 20, 'tile': tile if tile is not None else MAINLAND})

def all_beads():
    return [[bead.name.lower(), 1] for bead in IMP_BEADS]

def _fn2():

    def _fn3():
        expect(decide(snap('complete')).kind).to_be('done')
    test('complete -> done', _fn3)

    def _fn4():
        step = decide(snap('unknown'))
        expect(step.kind).to_be('wait')
    test('unknown -> wait, never a restart of a finished quest', _fn4)

    def _fn5():
        expect(decide(snap('not_started')).kind).to_be('custom')
    test('notStarted with no beads -> farm first, so the tower is one trip', _fn5)

    def _fn6():
        step = decide(snap('not_started', inv=all_beads()))
        expect(step.kind == 'talk' and step.stop.npc).to_be('Wizard Mizgog')
    test('notStarted holding every bead -> talk to Wizard Mizgog', _fn6)

    def _fn7():
        step = decide(snap('in_progress', inv=all_beads()))
        expect(step.kind == 'talk' and step.stop.npc).to_be('Wizard Mizgog')
    test('all four beads held -> hand them to Mizgog', _fn7)

    def _fn8():
        step = decide(snap('in_progress', inv=all_beads()[1:]))
        expect(step.kind).to_be('custom')
    test('one bead short -> farm imps rather than walk to Mizgog', _fn8)

    def _fn9():
        by_id = [[bead.id, 1] for bead in IMP_BEADS]
        step = decide(snap('in_progress', inv_ids=by_id))
        expect(step.kind == 'talk' and step.stop.npc).to_be('Wizard Mizgog')
    test('beads counted by object id when the name map is empty', _fn9)
describe('impcatcher decide', _fn2)

def _fn10():

    def _fn11():
        step = gather_bead(snap('in_progress', bank_known=False))
        expect(step.kind).to_be('scan_bank')
    test('an unread bank is scanned before a walk to the imps', _fn11)

    def _fn12():
        step = gather_bead(snap('in_progress', bank_known=True, bank=[['red bead', 1], ['white bead', 2]], bank_ids=[[1470, 1], [1476, 2]]))
        expect(step.kind).to_be('withdraw')
        expect(step.kind == 'withdraw' and sorted([item['id'] for item in step.items])).to_equal([1470, 1476])
        expect(step.kind == 'withdraw' and all([item['qty'] == 1 for item in step.items])).to_be(True)
    test('banked beads are withdrawn by id before any imp is killed', _fn12)

    def _fn13():
        step = gather_bead(snap('in_progress', bank_known=True, inv=[['red bead', 1]], inv_ids=[[1470, 1]], bank=[['red bead', 3]], bank_ids=[[1470, 3]]))
        expect(step.kind).to_be('custom')
    test('a bead already held is not withdrawn again', _fn13)

    def _fn14():
        step = gather_bead(snap('in_progress', inv=[['coins', 0]], tile=MAINLAND))
        expect(step.kind).to_be('withdraw')
        expect(step.kind == 'withdraw' and step.items[0]['name']).to_be('Coins')
    test('a coin top-up happens on the mainland, before the crossing', _fn14)

    def _fn15():
        step = gather_bead(snap('in_progress', inv=[['coins', 0]], tile=KARAMJA))
        expect(step.kind).to_be('custom')
    test('short of coins on Karamja, keep farming rather than sail back for the fare', _fn15)

    def _fn16():
        expect(gather_bead(snap('in_progress', inv=[['coins', 1000]], tile=MAINLAND)).kind).to_be('custom')
    test('coins in hand on the mainland go straight to the farm', _fn16)

    def _fn17():
        step = gather_bead(snap('in_progress', inv=[['coins', 0]], bank_coins=0, tile=MAINLAND))
        expect(step.kind).to_be('custom')
    test('an empty bank account farms rather than parking on a withdrawal it cannot make', _fn17)

    def _fn18():
        step = gather_bead(snap('in_progress', free_slots=0, tile=MAINLAND))
        expect(step.kind).to_be('deposit')
        expect(step.kind == 'deposit' and step.keep).to_contain('coins')
        expect(sorted(step.keep_ids)).to_equal([1470, 1472, 1474, 1476])
    test('a full pack is banked, keeping the beads and the fare', _fn18)

    def _fn19():
        step = gather_bead(snap('in_progress', inv=[['black bead', 1], ['red bead', 1]], inv_ids=[[1474, 1], [1470, 1]]))
        expect(step.kind == 'custom' and step.name).to_contain('White bead')
        expect(step.kind == 'custom' and step.name).to_contain('Yellow bead')
        expect(step.kind == 'custom' and step.name).not_.to_contain('Red bead')
    test('the farm step names the beads still outstanding', _fn19)
describe('impcatcher gatherBead', _fn10)

def _fn20():

    def imp(index, x, z, distance, contested=False):
        return Fake(**{'index': index, 'tile': Fake(**{'x': x, 'z': z, 'level': 0}), 'distance': distance, 'contested': contested})

    def anywhere(*args):
        return True

    def _fn21():
        field = [imp(1, 2625, 3203, 20), imp(2, 2633, 3222, 4), imp(3, 2639, 3230, 12)]
        chosen = set()
        for roll in range(60):
            pick = pick_imp(field, anywhere, lambda: roll * 37 % 101 / 101)
            if pick:
                chosen.add(pick.index)
        expect(sorted(list(chosen))).to_equal([1, 2, 3])
    test('every valid imp gets picked over many rolls, not only the nearest', _fn21)

    def _fn22():
        only = imp(7, 2633, 3222, 4)
        expect(pick_imp([only], anywhere, lambda: 0.9).index if pick_imp([only], anywhere, lambda: 0.9) is not None else None).to_be(7)
        expect(pick_imp([only], anywhere, lambda: 0.1).index if pick_imp([only], anywhere, lambda: 0.1) is not None else None).to_be(7)
    test('a single valid imp is picked whatever the roll', _fn22)

    def _fn23():
        expect(pick_imp([imp(1, 2845, 3175, 2)], anywhere)).to_be_null()
    test('an imp outside the field belongs to another spawn cluster', _fn23)

    def _fn24():
        expect(pick_imp([Fake(**{'index': 1, 'tile': Fake(**{'x': 2633, 'z': 3222, 'level': 1}), 'distance': 2, 'contested': False})], anywhere)).to_be_null()
    test('an imp on another level is never in the field', _fn24)

    def _fn25():
        expect(pick_imp([imp(1, 2633, 3222, 2, True)], anywhere)).to_be_null()
    test('an imp another player is fighting is left alone', _fn25)

    def _fn26():
        walled = imp(1, 2629, 3233, 3)
        open = imp(2, 2633, 3222, 18)

        def reachable(tile):
            return tile.z != 3233
        expect(pick_imp([walled, open], reachable).index if pick_imp([walled, open], reachable) is not None else None).to_be(2)
    test('a nearer imp on an unreachable tile loses to a reachable one', _fn26)

    def _fn27():
        expect(pick_imp([imp(1, 2633, 3222, 3)], lambda *_args: False)).to_be_null()
    test('no reachable imp gives no target rather than a doomed walk', _fn27)
describe('impcatcher pickImp', _fn20)

def _fn28():

    def imp(x, z, contested=False):
        return Fake(**{'index': x, 'tile': Fake(**{'x': x, 'z': z, 'level': 0}), 'distance': 5, 'contested': contested})

    def _fn29():
        census = imp_census([imp(2625, 3203), imp(2633, 3222, True), imp(3011, 3314), imp(2639, 3230)], lambda tile: tile.x != 2639)
        expect(census).to_equal(Fake(**{'scene': 4, 'in_field': 3, 'free': 2, 'reachable': 1, 'nearest_refused': 5}))
    test('each filter is counted separately', _fn29)

    def _fn30():
        expect(imp_census([], lambda *_args: True)).to_equal(Fake(**{'scene': 0, 'in_field': 0, 'free': 0, 'reachable': 0, 'nearest_refused': None}))
    test('an empty scene reads as zero everywhere', _fn30)

    def _fn31():
        far = Fake(**{'index': 1, 'tile': Fake(**{'x': 2625, 'z': 3203, 'level': 0}), 'distance': 45, 'contested': False})
        near = Fake(**{'index': 2, 'tile': Fake(**{'x': 2633, 'z': 3222, 'level': 0}), 'distance': 6, 'contested': False})
        expect(imp_census([far, near], lambda *_args: False).nearest_refused).to_be(6)
    test('the closest refused candidate reports its distance', _fn31)

    def _fn32():
        ok = Fake(**{'index': 1, 'tile': Fake(**{'x': 2633, 'z': 3222, 'level': 0}), 'distance': 6, 'contested': False})
        expect(imp_census([ok], lambda *_args: True).nearest_refused).to_be_null()
    test('nothing refused reports no distance', _fn32)
describe('impcatcher impCensus', _fn28)

def _fn33():

    def _fn34():
        expect(tally_names(['Scorpion', 'Monkey', 'Scorpion', 'Snake', 'Scorpion', 'Monkey'])).to_be('Scorpion x3, Monkey x2, Snake')
    test('names are counted and ordered by how many there are', _fn34)

    def _fn35():
        expect(tally_names([])).to_be('nothing')
    test('an empty scene says so rather than printing nothing', _fn35)

    def _fn36():
        expect(tally_names([None, 'Imp'])).to_be('?, Imp')
    test('unnamed entries are not silently dropped', _fn36)
describe('impcatcher tallyNames', _fn33)

def _fn37():

    def drop(id, x, distance):
        return Fake(**{'id': id, 'tile': Fake(**{'x': x, 'z': 3222, 'level': 0}), 'distance': distance})

    def _fn38():
        expect(nearest_reachable([drop(1470, 2625, 9), drop(1472, 2633, 2)], lambda *_args: True).id if nearest_reachable([drop(1470, 2625, 9), drop(1472, 2633, 2)], lambda *_args: True) is not None else None).to_be(1472)
    test('the nearest drop wins', _fn38)

    def _fn39():

        def reachable(tile):
            return tile.x != 2650
        expect(nearest_reachable([drop(1470, 2650, 1), drop(1472, 2633, 20)], reachable).id if nearest_reachable([drop(1470, 2650, 1), drop(1472, 2633, 20)], reachable) is not None else None).to_be(1472)
    test('a nearer drop on an unreachable tile loses to a reachable one', _fn39)

    def _fn40():
        expect(nearest_reachable([drop(1470, 2650, 1)], lambda *_args: False)).to_be_null()
    test('nothing reachable gives nothing', _fn40)
describe('impcatcher nearestReachable', _fn37)

def _fn41():
    target = Fake(**{'index': 1, 'tile': Fake(**{'x': 2633, 'z': 3222, 'level': 0}), 'distance': 4, 'contested': False})

    def _fn42():
        expect(idle_progress(target, False)).to_be(True)
    test('a fightable imp is progress', _fn42)

    def _fn43():
        expect(idle_progress(None, False)).to_be(False)
    test('no imp is not progress, whatever else is happening', _fn43)

    def _fn44():
        expect(idle_progress(target, True)).to_be(False)
    test('a pending random event hands the tick back rather than claiming progress', _fn44)
describe('impcatcher idleProgress', _fn41)

def _fn45():
    middle = Fake(**{'x': IMP_STAND.x, 'z': IMP_STAND.z, 'level': 0})

    def rolls(*values):
        state = [0]

        def roll():
            i = state[0]
            state[0] += 1
            return values[i % len(values)]
        return roll

    def _fn46():
        corners = [Fake(**{'x': IMP_FIELD.min_x, 'z': IMP_FIELD.min_z, 'level': 0}), Fake(**{'x': IMP_FIELD.max_x, 'z': IMP_FIELD.min_z, 'level': 0}), Fake(**{'x': IMP_FIELD.min_x, 'z': IMP_FIELD.max_z, 'level': 0}), Fake(**{'x': IMP_FIELD.max_x, 'z': IMP_FIELD.max_z, 'level': 0})]
        for corner in corners:
            for roll in range(16):
                target = search_target(corner, rolls(roll / 16, roll * 7 % 16 / 16))
                expect(target.x >= IMP_FIELD.min_x and target.x <= IMP_FIELD.max_x, f'{target.x}').to_be(True)
                expect(target.z >= IMP_FIELD.min_z and target.z <= IMP_FIELD.max_z, f'{target.z}').to_be(True)
                expect(target.level).to_be(0)
    test('the sweep stays inside the field from every corner of it', _fn46)

    def _fn47():
        for roll in range(16):
            target = search_target(middle, rolls(roll / 16, 0.5))
            expect(target.distance_to(middle), f'roll {roll}').to_be_greater_than(4)
    test('a sweep from the middle is a move worth walking', _fn47)

    def _fn48():
        north = search_target(middle, rolls(0.25, 0.5))
        south = search_target(middle, rolls(0.75, 0.5))
        expect(f'{north.x},{north.z}').not_.to_be(f'{south.x},{south.z}')
    test('different directions go to different places', _fn48)

    def _fn49():
        target = search_target(middle, rolls(0.1, 0.5, 0.6, 0.5), lambda tile: tile.z != 3230)
        expect(target.z).not_.to_be(3230)
    test('an unreachable heading is re-rolled rather than walked at', _fn49)

    def _fn50():
        expect(search_target(middle, rolls(0.1, 0.5), lambda *_args: False)).to_be(IMP_STAND)
    test('when nothing nearby is reachable the sweep falls back to the stand', _fn50)

    def _fn51():
        target = search_target(middle, rolls(0.25, 0.5))
        expect(target.distance_to(middle)).to_be_greater_than(4)
    test('with no reachability probe every heading is taken as given', _fn51)

    def _fn52():
        expect(search_target(Fake(**{'x': 3093, 'z': 3243, 'level': 0}), rolls(0.5, 0.5))).to_be(IMP_STAND)
    test('from off the strip the sweep heads back to the stand', _fn52)

    def _fn53():
        expect(search_target(None, rolls(0.5, 0.5))).to_be(IMP_STAND)
    test('no known position heads to the stand', _fn53)
describe('impcatcher searchTarget', _fn45)

def _fn54():

    def _fn55():
        for spawn in IMP_SPAWNS:
            expect(IMP_STAND.distance_to(Fake(**{'x': spawn.x, 'z': spawn.z, 'level': spawn.level})), f'{spawn.x},{spawn.z}').to_be_less_than_or_equal(25)
    test('one stand covers every spawn inside the search radius', _fn55)

    def _fn56():
        expect(IMP_STAND.x >= IMP_FIELD.min_x and IMP_STAND.x <= IMP_FIELD.max_x).to_be(True)
        expect(IMP_STAND.z >= IMP_FIELD.min_z and IMP_STAND.z <= IMP_FIELD.max_z).to_be(True)
    test('the stand is inside the field it searches', _fn56)
describe('impcatcher IMP_STAND', _fn54)

def _fn57():

    def _fn58():
        expect(sorted([bead.id for bead in IMP_BEADS])).to_equal([1470, 1472, 1474, 1476])
        expect(sorted([item.name for item in impcatcher.record.items])).to_equal(sorted([bead.name for bead in IMP_BEADS]))
    test('the four beads are the record items, by unique object id', _fn58)

    def _fn59():
        keys = sorted(list((impcatcher.gather if impcatcher.gather is not None else Fake(**{})).keys()))
        expect(keys).to_equal(sorted([item.name.lower() for item in impcatcher.record.items]))
    test('every gather key is a record item name, so the engine can dispatch each', _fn59)

    def _fn60():
        opener = ['Give me a quest!', "Most of your friends are pretty quiet aren't they?"]
        polite = ['Give me a quest please.', 'Give me a quest or else!', 'Just stop messing around and give me a quest!']
        expect(pick_preferred(opener, list(MIZGOG.prefer))).to_be('Give me a quest!')
        expect(pick_preferred(polite, list(MIZGOG.prefer))).to_be('Give me a quest please.')
    test('the prefer list survives both of Mizgog quest-start option pages', _fn60)

    def _fn61():
        expect(def_by_id('imp')).to_be(impcatcher)
    test('the engine can resolve the module from the record id', _fn61)

    def _fn62():
        expect(impcatcher.owns_inventory).to_be(True)
    test('the module owns its inventory, so nothing else tops the fare up mid-farm', _fn62)

    def _fn63():
        expect(MIZGOG.anchor.level).to_be(2)
        expect([MIZGOG.anchor.x, MIZGOG.anchor.z]).to_equal([3103, 3163])
    test('Mizgog stands on the top floor of the Wizards Tower', _fn63)

    def _fn64():
        expect(sorted([[tile.x, tile.z] for tile in list(IMP_SPAWNS)], key=lambda row: row[0] * 10000 + row[1])).to_equal(sorted([[2625, 3203], [2625, 3217], [2629, 3233], [2630, 3210], [2632, 3202], [2633, 3222], [2633, 3243], [2639, 3206], [2639, 3230]], key=lambda row: row[0] * 10000 + row[1]))
        for tile in IMP_SPAWNS:
            expect(tile.x >= IMP_FIELD.min_x and tile.x <= IMP_FIELD.max_x, f'{tile.x}').to_be(True)
            expect(tile.z >= IMP_FIELD.min_z and tile.z <= IMP_FIELD.max_z, f'{tile.z}').to_be(True)
    test('every south-Ardougne imp spawn lies inside the searched field', _fn64)
describe('impcatcher module wiring', _fn57)
