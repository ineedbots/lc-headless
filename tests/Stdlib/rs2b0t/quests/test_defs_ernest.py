"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/ernest.test.ts (MIT, see thirdparty/rs2b0t)."""
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot

def _snapshot(**fields):
    for name in ['inv', 'inv_ids', 'bank', 'bank_ids']:
        if isinstance(fields.get(name), (Record, Fake)):
            fields[name] = fields[name]._fields
    return QuestSnapshot(**fields)
from rs2004.quests.defs.ernest.areas import EC_ID, EC_STAGE
from rs2004.quests.defs.ernest import decide, ernest
from rs2004.quests.defs import QUEST_DEFS
from rs2004.quests.food import quest_food
original_food = quest_food.name

def _fn1():
    quest_food.name = 'Lobster'
before_each(_fn1)

def _fn2():
    quest_food.name = original_food
after_each(_fn2)

def snap(options=None):
    """Kitted out by default, so every case exercises the branch it names."""
    if options is None:
        options = Fake(**{})
    stage = options.stage if options.stage is not None else EC_STAGE.NOT_STARTED
    return _snapshot(**{'journal': options.journal if options.journal is not None else ('not_started' if stage == EC_STAGE.NOT_STARTED else 'in_progress'), 'inv': {_k: _v for _k, _v in [['lobster', 8]]}, 'inv_ids': {_k: _v for _k, _v in [[EC_ID.SPADE, 1]] + list(options.inv_ids if options.inv_ids is not None else [])}, 'worn': set(), 'worn_ids': set(), 'no_progress': 0, 'bank_coins': 2000000, 'stage': stage, 'progress': Fake(**{'stage': stage, 'flags': set()}), 'bank': {}, 'bank_ids': {}, 'bank_known': True, 'tile': options.tile if options.tile is not None else Fake(**{'x': 3093, 'z': 3243, 'level': 0}), 'free_slots': 20})

def step(options=None):
    if options is None:
        options = Fake(**{})
    return decide(snap(options))

def talk_to(s):
    return s.stop.npc if s.kind == 'talk' else None

def custom_name(s):
    return s.name if s.kind == 'custom' else None
ALL_PARTS = [[EC_ID.RUBBER_TUBE, 1], [EC_ID.PRESSURE_GAUGE, 1], [EC_ID.OIL_CAN, 1]]

def _fn3():

    def _fn4():
        expect(step(Fake(**{'journal': 'unknown'})).kind).to_be('wait')
    test('waits while the journal is unknown', _fn4)

    def _fn5():
        expect(step(Fake(**{'journal': 'complete', 'stage': EC_STAGE.COMPLETE})).kind).to_be('done')
    test('is done once the journal reads complete', _fn5)

    def _fn6():
        expect(talk_to(step(Fake(**{'stage': EC_STAGE.NOT_STARTED})))).to_be('Veronica')
    test('starts with Veronica', _fn6)

    def _fn7():
        expect(talk_to(step(Fake(**{'stage': EC_STAGE.STARTED})))).to_be('Professor Oddenstein')
    test('goes to Oddenstein once the quest has started', _fn7)

    def _fn8():
        expect(custom_name(step(Fake(**{'stage': EC_STAGE.SPOKEN_ODDENSTEIN})))).to_be('fetch the rubber tube')
    test('collects the rubber tube first — it is the only leg inside the manor', _fn8)

    def _fn9():
        s = step(Fake(**{'stage': EC_STAGE.SPOKEN_ODDENSTEIN, 'inv_ids': [[EC_ID.RUBBER_TUBE, 1]]}))
        expect(custom_name(s)).to_be('fetch the oil can')
    test('then the oil can, because the basement is entered from the same floor', _fn9)

    def _fn10():
        s = step(Fake(**{'stage': EC_STAGE.SPOKEN_ODDENSTEIN, 'inv_ids': [[EC_ID.RUBBER_TUBE, 1], [EC_ID.OIL_CAN, 1]]}))
        expect(custom_name(s)).to_be('fetch the pressure gauge')
    test('then the pressure gauge, which is the one leg that leaves the manor', _fn10)

    def _fn11():
        expect(talk_to(step(Fake(**{'stage': EC_STAGE.SPOKEN_ODDENSTEIN, 'inv_ids': ALL_PARTS})))).to_be('Professor Oddenstein')
    test('hands everything to Oddenstein once all three parts are held', _fn11)

    def _fn12():
        stuck = step(Fake(**{'stage': EC_STAGE.SPOKEN_ODDENSTEIN, 'tile': Fake(**{'x': 3111, 'z': 3367, 'level': 0})}))
        expect(custom_name(stuck)).to_be('leave the closet')
    test('keys its way out of the closet before doing anything else', _fn12)

    def _fn13():
        _merged14 = {}
        for _k, _v in (snap(Fake(**{'stage': EC_STAGE.SPOKEN_ODDENSTEIN, 'tile': Fake(**{'x': 3111, 'z': 3367, 'level': 0})}))._fields if isinstance(snap(Fake(**{'stage': EC_STAGE.SPOKEN_ODDENSTEIN, 'tile': Fake(**{'x': 3111, 'z': 3367, 'level': 0})})), (Record, Fake)) else {name: getattr(snap(Fake(**{'stage': EC_STAGE.SPOKEN_ODDENSTEIN, 'tile': Fake(**{'x': 3111, 'z': 3367, 'level': 0})})), name) for name in QuestSnapshot.FIELDS}).items():
            _merged14[_k] = _v
        for _k, _v in {'inv_ids': {}}.items():
            _merged14[_k] = _v
        bare = decide(Fake(**_merged14))
        expect(custom_name(bare)).to_be('leave the closet')
    test('the closet escape outranks even the supply trip', _fn13)

    def _fn15():
        in_basement = step(Fake(**{'stage': EC_STAGE.SPOKEN_ODDENSTEIN, 'inv_ids': [[EC_ID.RUBBER_TUBE, 1], [EC_ID.OIL_CAN, 1]], 'tile': Fake(**{'x': 3117, 'z': 9755, 'level': 0})}))
        expect(custom_name(in_basement)).to_be('leave the manor basement')
    test('escapes the basement once the can is held, ahead of the gauge leg', _fn15)

    def _fn16():
        in_alcove_tile = step(Fake(**{'stage': EC_STAGE.SPOKEN_ODDENSTEIN, 'inv_ids': [[EC_ID.RUBBER_TUBE, 1], [EC_ID.OIL_CAN, 1]], 'tile': Fake(**{'x': 3094, 'z': 3362, 'level': 0})}))
        expect(custom_name(in_alcove_tile)).to_be('leave the manor basement')
    test('escapes the ladder alcove once the can is held', _fn16)

    def _fn17():
        going_in = step(Fake(**{'stage': EC_STAGE.SPOKEN_ODDENSTEIN, 'inv_ids': [[EC_ID.RUBBER_TUBE, 1]], 'tile': Fake(**{'x': 3117, 'z': 9755, 'level': 0})}))
        expect(custom_name(going_in)).to_be('fetch the oil can')
    test('does not fight fetchOilCan for the pocket before the can is held', _fn17)

    def _fn18():
        outside = step(Fake(**{'stage': EC_STAGE.SPOKEN_ODDENSTEIN, 'tile': Fake(**{'x': 3107, 'z': 3367, 'level': 0})}))
        expect(custom_name(outside)).to_be('fetch the rubber tube')
    test('a tile just outside the closet is not treated as inside it', _fn18)

    def _fn19():
        _merged20 = {}
        for _k, _v in (snap(Fake(**{'stage': EC_STAGE.SPOKEN_ODDENSTEIN}))._fields if isinstance(snap(Fake(**{'stage': EC_STAGE.SPOKEN_ODDENSTEIN})), (Record, Fake)) else {name: getattr(snap(Fake(**{'stage': EC_STAGE.SPOKEN_ODDENSTEIN})), name) for name in QuestSnapshot.FIELDS}).items():
            _merged20[_k] = _v
        for _k, _v in {'inv_ids': {}}.items():
            _merged20[_k] = _v
        bare = decide(Fake(**_merged20))
        expect(['grab_ground', 'withdraw', 'scan_bank']).to_contain(bare.kind)
    test('fetches a spade before anything that needs one', _fn19)

    def _fn21():
        expect(any([d.record.id == 'haunted' for d in QUEST_DEFS])).to_be(True)
        expect(ernest.owns_inventory).to_be(True)
        expect(ernest.bank).not_.to_be('nearest')
    test('is registered in the queue and pins the Draynor bank', _fn21)
describe('Ernest the Chicken decide()', _fn3)
