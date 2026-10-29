"""Solve held boxes through actual board reads, planning, and delayed move acknowledgements."""

import rs2004.clues.puzzle_box as puzzle
from rs2004.clues.puzzle import apply_puzzle_move, is_puzzle_solved
from rs2004 import execution
from helpers import FakeModule


class Piece:
    def __init__(self, world, slot, id):
        self.world = world
        self.slot = slot
        self.id = id

    def actions(self):
        return ['Move'] if self.world.labels_loaded else []

    def interact(self, op):
        self.world.clicks.append((self.slot, op))
        if self.world.refuse_moves > 0:
            self.world.refuse_moves -= 1
            return False
        if self.world.ignore_moves > 0:
            self.world.ignore_moves -= 1
            return True
        self.world.pending_move = self.slot
        return True


class PuzzleWorld:
    def __init__(self):
        self.board = list(range(24)) + [None]
        self.ids = {}
        for id, slot in puzzle.PUZZLE_PIECE_SLOT.items():
            if slot not in self.ids:
                self.ids[slot] = id
        self.now = 0
        self.open = False
        self.held = True
        self.opens = True
        self.labels_loaded = True
        self.refuse_moves = 0
        self.ignore_moves = 0
        self.lose_board = False
        self.pending_move = None
        self.pending_open = False
        self.pending_close = False
        self.clicks = []
        self.logs = []
        self.box_clicks = []
        self.closed = 0

    def __enter__(self):
        self.saved = (puzzle._core, puzzle.reader, puzzle.inventory, puzzle.modals, execution._core)
        puzzle._core = self
        puzzle.reader = FakeModule(main_modal=lambda: 100 if self.open else -1)
        puzzle.inventory = FakeModule(items=lambda: [FakeModule(id=9000, interact=self.open_box)] if self.held else [])
        puzzle.modals = FakeModule(close=self.close)
        execution._core = self
        return self

    def __exit__(self, *args):
        puzzle._core, puzzle.reader, puzzle.inventory, puzzle.modals, execution._core = self.saved

    def step_time(self):
        return self.now

    def get_inventories(self, main):
        assert main == 100
        return [(101, 'invtext', 0, []), (102, 'inv', 0, []), (103, 'inv', 0, [])]

    def get_inventory(self, com):
        if com != 103 or self.board is None:
            return [FakeModule(id=-1)]
        return [Piece(self, slot, self.ids[value]) for slot, value in enumerate(self.board) if value is not None]

    def open_box(self, op):
        self.box_clicks.append(op)
        self.pending_open = self.opens
        return self.opens

    def close(self):
        self.closed += 1
        self.pending_close = True
        yield execution.Ticks(1)

    def advance(self):
        if self.pending_open:
            self.open = True
            self.pending_open = False
        if self.pending_close:
            self.open = False
            self.pending_close = False
        if self.pending_move is not None:
            assert apply_puzzle_move(self.board, self.pending_move)
            self.pending_move = None
            if self.lose_board:
                self.board = None

    def run(self, task):
        for guard in range(160):
            try:
                wait = next(task)
            except StopIteration as stopped:
                return stopped.value
            assert isinstance(wait, execution.Update) or isinstance(wait, execution.Ticks)
            self.now += 500
            self.advance()
        assert False, 'puzzle exceeded its simulated update budget'

    def solve(self):
        return self.run(puzzle.solve_held(9000, self.logs.append))

    def scramble(self):
        for slot in [23, 18, 17]:
            assert apply_puzzle_move(self.board, slot)


def test_solved_box_opens_reads_board_and_closes_without_moving_pieces():
    with PuzzleWorld() as world:
        assert world.solve()
        assert world.box_clicks == ['Open']
        assert world.clicks == []
        assert world.logs == ['puzzle already solved']
        assert world.closed == 1 and not world.open


def test_puzzle_solves_scrambled_board_and_waits_for_each_move_to_land():
    with PuzzleWorld() as world:
        world.scramble()
        assert world.solve()
        assert is_puzzle_solved(world.board)
        assert len(world.clicks) >= 3
        assert all([op == 'Move' for slot, op in world.clicks])
        assert 'puzzle solved in' in world.logs[-1]
        assert world.closed == 1 and not world.open


def test_puzzle_uses_numeric_move_op_before_labels_load():
    with PuzzleWorld() as world:
        assert apply_puzzle_move(world.board, 23)
        world.labels_loaded = False
        assert world.solve()
        assert world.clicks == [(24, 5)]
        assert is_puzzle_solved(world.board)


def test_refused_move_is_replanned_and_retried():
    with PuzzleWorld() as world:
        assert apply_puzzle_move(world.board, 23)
        world.refuse_moves = 1
        assert world.solve()
        assert world.clicks == [(24, 'Move'), (24, 'Move')]
        assert is_puzzle_solved(world.board)
        assert not world.open


def test_unacknowledged_move_times_out_then_replans_from_live_board():
    with PuzzleWorld() as world:
        assert apply_puzzle_move(world.board, 23)
        world.ignore_moves = 1
        assert world.solve()
        assert world.clicks == [(24, 'Move'), (24, 'Move')]
        assert world.now >= puzzle.MOVE_SETTLE_MS
        assert is_puzzle_solved(world.board)


def test_repeated_refusals_stop_at_stall_limit_and_close_box():
    with PuzzleWorld() as world:
        assert apply_puzzle_move(world.board, 23)
        world.refuse_moves = 100
        assert world.solve() is False
        assert len(world.clicks) == puzzle.STALL_LIMIT
        assert '8 refused in a row' in world.logs[-1]
        assert not world.open and world.closed == 1


def test_unsolvable_board_retries_fresh_reads_then_closes():
    with PuzzleWorld() as world:
        world.board[0], world.board[1] = world.board[1], world.board[0]
        assert world.solve() is False
        assert world.clicks == []
        assert sum(['not solvable' in line for line in world.logs]) == puzzle.STALL_LIMIT
        assert not world.open and world.closed == 1


def test_missing_box_does_not_click_or_open_modal():
    with PuzzleWorld() as world:
        world.held = False
        assert world.solve() is False
        assert world.logs == ['no puzzle box held']
        assert world.box_clicks == [] and world.closed == 0


def test_failed_open_times_out_without_attempting_moves():
    with PuzzleWorld() as world:
        world.opens = False
        assert world.solve() is False
        assert world.now >= puzzle.OPEN_WAIT_MS
        assert world.logs == ['puzzle box did not open']
        assert world.clicks == []


def test_already_open_box_is_not_reopened_and_is_closed_after_solving():
    with PuzzleWorld() as world:
        world.open = True
        assert apply_puzzle_move(world.board, 23)
        assert world.solve()
        assert world.box_clicks == [] and world.closed == 1
        assert not world.open


def test_incomplete_board_is_not_reported_as_open():
    with PuzzleWorld() as world:
        world.open = True
        world.board[0] = None
        assert puzzle.board_now() is None
        assert not puzzle.is_open()
        assert world.run(puzzle.close()) is None
        assert world.closed == 0


def test_board_disappearing_mid_solve_is_reported_as_failure():
    with PuzzleWorld() as world:
        world.scramble()
        world.lose_board = True
        assert world.solve() is False
        assert world.logs[-1] == 'puzzle board went unreadable mid-solve'
        assert len(world.clicks) == 1


def test_click_missing_slot_does_not_send_an_inventory_operation():
    with PuzzleWorld() as world:
        world.open = True
        assert puzzle._click(24) is False
        assert world.clicks == []
