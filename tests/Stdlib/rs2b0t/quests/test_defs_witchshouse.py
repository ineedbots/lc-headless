"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/witchshouse.test.ts (MIT, see thirdparty/rs2b0t)."""


from rs2004.quests.defs.witchshouse.areas import WH_OBJ, in_garden, in_shed
from rs2004.quests.defs.witchshouse import diary_state, decide, reset_diary_state, witchshouse
from rs2004.quests.defs.witchshouse.journal import WH_STAGE
from rs2004.quests.defs import def_by_id
def snap(options=None):
    if options is None:
        options = Obj({})
    stage = (options.stage if options.stage is not None else WH_STAGE.NOT_STARTED)
    inv_ids = {}
    for id in (options.ids if options.ids is not None else []):
        _v1 = inv_ids.get(id)
        inv_ids[id] = ((_v1 if _v1 is not None else 0)) + 1
    return Obj({
        'journal': (options.journal if options.journal is not None else (('not_started' if stage == WH_STAGE.NOT_STARTED else 'in_progress'))),
        'inv': {_k: _v for _k, _v in [['mind rune', 150], ['air rune', 150]]},
        'inv_ids': inv_ids,
        'worn': set(),
        'worn_ids': set((options.worn if options.worn is not None else [])),
        'no_progress': 0,
        'bank_coins': 5000,
        'stage': stage,
        'progress': Obj({'stage': stage, 'flags': set()}),
        'bank': {},
        'bank_ids': {},
        'bank_known': True,
        'tile': (Obj({'x': 2928, 'z': 3456, 'level': 0}) if options.tile is None else options.tile),
        'free_slots': 20,
    })


def named(step):
    return ((step.name if step.kind == 'custom' else step.kind))


DRESSED = Obj({'worn': [WH_OBJ.GLOVES], 'ids': [WH_OBJ.DOOR_KEY]})
before_each(lambda: reset_diary_state())


def _fn2():
    def _fn3():
        expect(decide(snap(Obj({'journal': 'unknown'}))).kind).to_be('wait')
    test('an unloaded journal waits rather than restarting the quest', _fn3)

    def _fn4():
        expect(decide(snap(Obj({'journal': 'complete', 'stage': WH_STAGE.COMPLETE}))).kind).to_be('done')
    test('a complete journal is done', _fn4)

    def _fn5():
        _merged6 = {}
        for _k, _v in (snap(Obj({'journal': 'in_progress'}))._fields if isinstance(snap(Obj({'journal': 'in_progress'})), Obj) else snap(Obj({'journal': 'in_progress'}))).items():
            _merged6[_k] = _v
        for _k, _v in {'stage': None, 'progress': None}.items():
            _merged6[_k] = _v
        blank = Obj(_merged6)
        expect(decide(blank).kind).to_be('wait')
    test('an in-progress journal nothing parses waits rather than guessing a stage', _fn5)

    def _fn7():
        step = decide(snap())
        expect(step.kind).to_be('talk')
        expect(step.kind == 'talk' and step.stop.npc).to_be('Boy')
    test('not started talks to the boy', _fn7)


describe('witchshouse decide', _fn2)


def _fn8():
    def _fn9():
        expect(named(decide(snap(Obj({'stage': WH_STAGE.STARTED}))))).to_contain('flower pot')
    test('started with no door key looks under the flower pot', _fn9)

    def _fn10():
        step = decide(snap(Obj({'stage': WH_STAGE.UNLOCKED_DOOR, 'ids': []})))
        expect(named(step)).to_contain('flower pot')
    test('a door key lost at the shed stage is replaced before the garden', _fn10)

    def _fn11():
        step = decide(snap(Obj({'stage': WH_STAGE.STARTED, 'ids': [WH_OBJ.DOOR_KEY]})))
        expect(step.kind).to_be('withdraw')
        expect(step).to_match_object(Obj({'items': [Obj({'name': 'Leather gloves', 'qty': 1, 'id': WH_OBJ.GLOVES})]}))
    test('the gloves are withdrawn when neither worn nor held', _fn11)

    def _fn12():
        step = decide(snap(Obj({'stage': WH_STAGE.STARTED, 'ids': [WH_OBJ.DOOR_KEY, WH_OBJ.GLOVES]})))
        expect(step).to_match_object(Obj({'kind': 'equip', 'item': 'Leather gloves'}))
    test('held gloves are equipped, because the iron gate reads the worn slot', _fn12)

    def _fn13():
        _merged14 = {}
        for _k, _v in {'stage': WH_STAGE.STARTED}.items():
            _merged14[_k] = _v
        for _k, _v in (DRESSED._fields if isinstance(DRESSED, Obj) else DRESSED).items():
            _merged14[_k] = _v
        expect(named(decide(snap(Obj(_merged14))))).to_contain('cellar cupboard')
    test('dressed and started, the cellar cupboard is the step', _fn13)


describe('witchshouse gets into the house before anything else', _fn8)


def _fn15():
    def _fn16():
        step = decide(snap(Obj({'stage': WH_STAGE.STARTED, 'worn': [WH_OBJ.GLOVES], 'ids': [WH_OBJ.DOOR_KEY, WH_OBJ.MAGNET]})))
        expect(named(step)).to_contain('drop the magnet')
    test('a magnet carried into stage 1 is dropped so the cupboard will hand one out', _fn16)

    def _fn17():
        _merged18 = {}
        for _k, _v in {'stage': WH_STAGE.FOUND_MAGNET}.items():
            _merged18[_k] = _v
        for _k, _v in (DRESSED._fields if isinstance(DRESSED, Obj) else DRESSED).items():
            _merged18[_k] = _v
        expect(named(decide(snap(Obj(_merged18))))).to_contain('cellar cupboard')
    test('stage 2 with no magnet goes back to the cupboard', _fn17)

    def _fn19():
        step = decide(snap(Obj({'stage': WH_STAGE.FOUND_MAGNET, 'worn': [WH_OBJ.GLOVES], 'ids': [WH_OBJ.DOOR_KEY, WH_OBJ.MAGNET]})))
        expect(step.kind).to_be('buy')
        expect(step).to_match_object(Obj({'item': 'Cheese', 'shop': Obj({'npc': 'Wydin'})}))
    test('holding the magnet with no cheese buys another before the mouse hole', _fn19)

    def _fn20():
        step = decide(snap(Obj({
        'stage': WH_STAGE.FOUND_MAGNET,
        'worn': [WH_OBJ.GLOVES],
        'ids': [WH_OBJ.DOOR_KEY, WH_OBJ.MAGNET, WH_OBJ.CHEESE],
    })))
        expect(named(step)).to_contain('lure the mouse')
    test('holding both goes to the mouse, not the shop', _fn20)


describe('witchshouse unlocks the back door', _fn15)


def _fn21():
    def _fn22():
        expect(named(decide(snap(Obj({'stage': WH_STAGE.UNLOCKED_DOOR, 'ids': [WH_OBJ.DOOR_KEY]}))))).to_contain('take the witch')
    test('stage 3 with no diary fetches one', _fn22)

    def _fn23():
        step = decide(snap(Obj({'stage': WH_STAGE.UNLOCKED_DOOR, 'ids': [WH_OBJ.DOOR_KEY, WH_OBJ.DIARY]})))
        expect(named(step)).to_contain('read the witch')
    test('holding the diary reads it', _fn23)

    def _fn24():
        diary_state.read = True
        step = decide(snap(Obj({'stage': WH_STAGE.UNLOCKED_DOOR, 'ids': [WH_OBJ.DOOR_KEY, WH_OBJ.DIARY]})))
        expect(named(step)).to_contain('fountain')
    test('once read, the fountain is the step', _fn24)

    def _fn25():
        diary_state.tries = 3
        expect(named(decide(snap(Obj({'stage': WH_STAGE.UNLOCKED_DOOR, 'ids': [WH_OBJ.DOOR_KEY]}))))).to_contain('fountain')
    test('a diary that cannot be fetched stops blocking the quest', _fn25)

    # Why: the walk out of the garden is where `witch.rs2` deletes the key, so a diary detour with one
    # in the pack throws away the leg that earned it.
    def _fn26():
        step = decide(snap(Obj({'stage': WH_STAGE.UNLOCKED_DOOR, 'ids': [WH_OBJ.DOOR_KEY, WH_OBJ.SHED_KEY]})))
        expect(named(step)).to_contain('kill the experiment')
    test('a shed key already held outranks the diary', _fn26)


describe('witchshouse reads the diary before it enters the garden', _fn21)


def _fn27():
    def _fn28():
        expect(named(decide(snap(Obj({'stage': WH_STAGE.DEFEATED, 'ids': [WH_OBJ.DOOR_KEY]}))))).to_contain('take the ball')
    test('the experiment dead and no ball goes back for it', _fn28)

    def _fn29():
        step = decide(snap(Obj({'stage': WH_STAGE.DEFEATED, 'ids': [WH_OBJ.BALL]})))
        expect(step.kind).to_be('talk')
    test('the ball in the pack goes to the boy', _fn29)

    # Why: `witch.rs2` deletes the ball as well as the key, and the boy is where she drops you.
    def _fn30():
        step = decide(snap(Obj({'stage': WH_STAGE.DEFEATED, 'ids': [WH_OBJ.DOOR_KEY], 'tile': Obj({'x': 2929, 'z': 3456, 'level': 0})})))
        expect(named(step)).to_contain('take the ball')
    test('a ball taken back by the witch is fetched again rather than handed in', _fn30)


describe('witchshouse finishes at the shed', _fn27)


def _fn31():
    def _fn32():
        expect(in_garden(Obj({'x': 2901, 'z': 3466, 'level': 0}))).to_be(False)
        expect(in_garden(Obj({'x': 2901, 'z': 3465, 'level': 0}))).to_be(True)
    test('the porch is not the garden, though they share a row', _fn32)

    def _fn33():
        expect(in_garden(Obj({'x': 2911, 'z': 3470, 'level': 0}))).to_be(True)
        expect(in_garden(Obj({'x': 2933, 'z': 3463, 'level': 0}))).to_be(True)
    test('the fountain yard and the ring corridor are both the garden', _fn33)

    def _fn34():
        expect(in_shed(Obj({'x': 2935, 'z': 3461, 'level': 0}))).to_be(True)
        expect(in_garden(Obj({'x': 2935, 'z': 3461, 'level': 0}))).to_be(False)
    test('the shed is its own room, not the garden', _fn34)

    def _fn35():
        expect(in_garden(Obj({'x': 2911, 'z': 3470, 'level': 1}))).to_be(False)
    test('nothing upstairs counts as the garden', _fn35)


describe('witchshouse areas', _fn31)


def _fn36():
    def _fn37():
        expect(def_by_id('ball')).to_be(witchshouse)
    test("the def is registered under the record's id", _fn37)

    def _fn38():
        expect(witchshouse.read_progress).to_be_defined()
    test('a journal reader is declared, so decide runs off a stage and not the pack', _fn38)

    def _fn39():
        expect(witchshouse.pray).to_match_object(Obj({'protect': 'melee'}))
    test('the fight declares the melee protection it needs', _fn39)


describe('witchshouse module wiring', _fn36)
