"""rs2b0t's test/api/ai/clues/hard-tier.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs.record import Record
from rs2004.quests.data import QUESTS

from rs2004.clues.data import CLUE_DB, CLUE_GATES, PUZZLE_PIECE_SLOT
from rs2004.clues.puzzle import PUZZLE_BLANK_SLOT

rows = as_records(list(CLUE_DB.values()))
hard = [row for row in rows if '_hard_' in row.obj]
GUARDIANS = ['Saradomin Wizard', 'Zamorak Wizard']


def _fn1():
    def _fn2():
        expect(len(hard)).to_be(64)
        expect(len(rows)).to_be(186)
    test('all 64 hard clues from trail_hard.enum are present', _fn2)

    def _fn3():
        expect(len(set([r.id for r in rows]))).to_be(len(rows))
    test('the tiers share one table without colliding on an obj id', _fn3)

    # A trail_casket param alone does not make a dig: riddle004 carries one but
    # has no coord and is answered by talking to Gerrant.
    def _fn4():
        expect([r for r in rows if r.type == 'dig' and not r.coord]).to_equal([])
        expect([r for r in rows if r.type == 'talk' and not r.npc]).to_equal([])
        expect(CLUE_DB[2778]).to_match_object({'type': 'talk', 'npc': 'Gerrant'})
    test('every dig has a coord and every talk has an npc', _fn4)


describe('hard tier in CLUE_DB', _fn1)


def _fn5():
    guarded = [row for row in hard if row.guardian is not None]

    def _fn6():
        expect(len(guarded)).to_be(30)
        expect(sorted(list(set([r.guardian for r in guarded])))).to_equal(GUARDIANS)
    test('30 coordinate digs are guarded, by one of the two wizards', _fn6)

    def _fn7():
        expect([r for r in guarded if r.type != 'dig']).to_equal([])
        expect([r for r in guarded if r.needs_sextant != True]).to_equal([])
    test('a guardian only ever sits on a sextant dig', _fn7)

    def _fn8():
        expect([r for r in rows if r.guardian is not None and not ('_hard_' in r.obj)]).to_equal([])
    test('no easy or medium clue picked up a guardian', _fn8)


describe('dig guardians', _fn5)


def _fn9():
    puzzles = [row for row in hard if row.puzzle is not None]

    def _fn10():
        expect(len(puzzles)).to_be(9)
        expect([r for r in puzzles if r.type != 'talk']).to_equal([])
        expect([r for r in puzzles if not isinstance(r.puzzle.id, int) or r.puzzle.id <= 0]).to_equal([])
    test('9 talk clues hand over a puzzle box, each with a resolved obj id', _fn10)

    def _fn11():
        slots = list(PUZZLE_PIECE_SLOT.values())
        expect(len(slots)).to_be(72)
        for piece_set in range(3):
            of_set = sorted(slots[piece_set * 24:piece_set * 24 + 24])
            expect(of_set).to_equal(list(range(PUZZLE_BLANK_SLOT)))
    test('the three piece sets cover every board slot exactly once', _fn11)


describe('puzzle boxes', _fn9)


def _fn12():
    def _fn13():
        for id, gate in CLUE_GATES.items():
            expect(CLUE_DB.get(id), f'gate {id} is not a clue').to_be_defined()
            expect(len(gate['reason'])).to_be_greater_than(10)
    test('every gate names a real clue and gives a reason', _fn13)

    def _fn14():
        known = set([q.name for q in QUESTS])
        for id, gate in CLUE_GATES.items():
            expect(gate['quest'] in known, f"gate {id} names '{gate['quest']}'").to_be(True)
    test('every gate names a quest the bot can drive', _fn14)


describe('gated clues', _fn12)
