"""rs2b0t's test/api/ai/clues/puzzleLogic.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and
expect. A solve takes pocketpy about 40 ms in Release, so the suite runs 100 of rs2b0t's 10,000 shuffles and 10 of
its 500 deep scrambles; slow/test_clue_puzzle_full.py runs them all, under the hidden [Slow] case."""

from rs2004.clues.puzzle import PUZZLE_BLANK_SLOT, PUZZLE_SIZE, PUZZLE_WIDTH, apply_puzzle_move, is_puzzle_solved, puzzle_neighbours
from rs2004.clues.puzzle import read_puzzle_board, solve_puzzle


def solved():
    return [None if i == PUZZLE_BLANK_SLOT else i for i in range(PUZZLE_SIZE)]


class Mulberry32:
    """rs2b0t's seeded generator, so the shuffles are the same boards."""

    def __init__(self, seed):
        self.a = seed & 0xFFFFFFFF

    def __call__(self):
        self.a = (self.a + 0x6D2B79F5) & 0xFFFFFFFF
        t = self.a
        t = ((t ^ (t >> 15)) * (t | 1)) & 0xFFFFFFFF
        t ^= (t + ((t ^ (t >> 7)) * (t | 61)) & 0xFFFFFFFF) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296


def shuffle(rand, moves=101):
    """Mirrors shuffle_trail_puzzle: 101 legal moves from the solved state."""
    board = solved()
    for _ in range(moves):
        options = puzzle_neighbours(board.index(None))
        apply_puzzle_move(board, options[int(rand() * len(options))])
    return board


def solves(seed, count, moves, worst_limit=None):
    rand = Mulberry32(seed)
    worst = 0
    for _ in range(count):
        board = shuffle(rand, moves)
        path = solve_puzzle(board)
        expect(path).not_.to_be_null()
        replay = list(board)
        for slot in path:
            expect(apply_puzzle_move(replay, slot)).to_be(True)
        expect(is_puzzle_solved(replay)).to_be(True)
        worst = max(worst, len(path))
    if worst_limit is not None:
        expect(worst).to_be_less_than(worst_limit)


def one_move():
    board = solved()
    expect(apply_puzzle_move(board, PUZZLE_BLANK_SLOT - 1)).to_be(True)
    expect(is_puzzle_solved(board)).to_be(False)


def duplicated():
    board = solved()
    board[0] = 1
    expect(solve_puzzle(board)).to_be_null()


describe('board helpers', lambda: [
    test('the solved board is piece i in slot i with the blank last', lambda: expect(is_puzzle_solved(solved())).to_be(True)),
    test('any single move leaves the board unsolved', one_move),
    test('a move is refused when the blank is not adjacent', lambda: expect(apply_puzzle_move(solved(), 0)).to_be(False)),
    test('neighbours never wrap across a row edge', lambda: [
        expect(sorted(puzzle_neighbours(0))).to_equal([1, PUZZLE_WIDTH]),
        expect(puzzle_neighbours(PUZZLE_WIDTH - 1)).not_.to_contain(PUZZLE_WIDTH),
    ]),
])

describe('read_puzzle_board', lambda: [
    test('maps piece obj ids to their target slots and leaves the gap None',
         lambda: expect(read_puzzle_board([(2, 700), (0, 702), (1, 701)], {700: 0, 701: 1, 702: 2}, 4)).to_equal([2, 1, 0, None])),
    test('rejects a board holding a piece it cannot identify', lambda: expect(read_puzzle_board([(0, 999)], {700: 0}, 2)).to_be_null()),
    test('rejects a partially transmitted board', lambda: expect(read_puzzle_board([(0, 700)], {700: 0, 701: 1}, 3)).to_be_null()),
])

describe('solve_puzzle', lambda: [
    test('an already solved board needs no moves', lambda: expect(solve_puzzle(solved())).to_equal([])),
    test('rejects a malformed board', lambda: expect(solve_puzzle([1, 2, 3])).to_be_null()),
    test('rejects a board with a duplicated piece', duplicated),
    # The engine shuffles by 101 legal moves from solved, so every board the bot can be handed is solvable.
    test('solves engine-style shuffles (100 of the 10,000)', lambda: solves(20260802, 100, 101, 400)),
    test('solves deeply scrambled boards (10 of the 500)', lambda: solves(7, 10, 5000)),
])
