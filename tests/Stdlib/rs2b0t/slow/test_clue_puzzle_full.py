"""The full size of rs2b0t's puzzleLogic.test.ts runs: 10,000 engine-style shuffles and 500 deep scrambles, each
solved and replayed. About seven minutes in Release, so it runs only under the hidden [Slow] case."""

from rs2004.clues.puzzle import PUZZLE_BLANK_SLOT, PUZZLE_SIZE, apply_puzzle_move, is_puzzle_solved, puzzle_neighbours, solve_puzzle


class Mulberry32:
    def __init__(self, seed):
        self.a = seed & 0xFFFFFFFF

    def __call__(self):
        self.a = (self.a + 0x6D2B79F5) & 0xFFFFFFFF
        t = self.a
        t = ((t ^ (t >> 15)) * (t | 1)) & 0xFFFFFFFF
        t ^= (t + ((t ^ (t >> 7)) * (t | 61)) & 0xFFFFFFFF) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296


def shuffle(rand, moves):
    board = [None if i == PUZZLE_BLANK_SLOT else i for i in range(PUZZLE_SIZE)]
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


test('solves 10,000 engine-style shuffles', lambda: solves(20260802, 10000, 101, 400))
test('solves 500 deeply scrambled boards', lambda: solves(7, 500, 5000))
