"""Solving a held puzzle box: rs2b0t's api/ai/clues/PuzzleBox.ts (MIT, see thirdparty/rs2b0t). The Waits are used
with yield from.

The board is the open modal's inventory whose items are puzzle pieces, read as the duel's stakes are; a piece is
clicked by its Move op. rs2b0t solves the board afresh before every move; here the plan is made once and made again
only when a move doesn't land as planned, since a solve takes pocketpy tens of milliseconds and a box takes hundreds
of moves."""

import _core
from rs2004 import execution
from rs2004.dialogue import modals
from rs2004.game import reader
from rs2004.items import inventory
from rs2004.clues.data import PUZZLE_PIECE_SLOT
from rs2004.clues.puzzle import PUZZLE_SIZE, apply_puzzle_move, is_puzzle_solved, read_puzzle_board, solve_puzzle

MOVE_OP = 'Move'
# Why: every puzzle piece defines iop5=Move, so the board stays usable before labels load.
MOVE_OP_INDEX = 5
OPEN_OP = 'Open'
OPEN_WAIT_MS = 5000
CLOSE_WAIT_MS = 3000
# Why: the engine drops stale-slot OPHELD packets, so the board is read again after each move.
MOVE_SETTLE_MS = 2000
MAX_MOVES = 600
STALL_LIMIT = 8


def _board_com():
    """The open modal's inventory component holding puzzle pieces, or -1."""
    main = reader.main_modal()
    if main < 0:
        return -1
    for com, type, x, options in _core.get_inventories(main):
        if type != 'inv':
            continue
        pieces = [i for i in _core.get_inventory(com) if i.id in PUZZLE_PIECE_SLOT]
        if len(pieces) > 0:
            return com
    return -1


def board_pieces():
    """The board's pieces as InvItems, with their slots."""
    com = _board_com()
    return [] if com == -1 else [i for i in _core.get_inventory(com) if i.id in PUZZLE_PIECE_SLOT]


def board_now():
    """The board as solve_puzzle reads it, or None while the box is shut or half sent."""
    pieces = board_pieces()
    if len(pieces) != PUZZLE_SIZE - 1:
        return None
    return read_puzzle_board([(i.slot, i.id) for i in pieces], PUZZLE_PIECE_SLOT)


def is_open():
    return board_now() is not None


def _click(slot):
    for piece in board_pieces():
        if piece.slot == slot:
            labelled = [op for op in piece.actions() if op.lower() == MOVE_OP.lower()]
            return piece.interact(labelled[0] if labelled else MOVE_OP_INDEX)
    return False


def close():
    if not is_open():
        return
    yield from modals.close()
    yield from execution.delay_until(lambda: not is_open(), CLOSE_WAIT_MS)


def _same(live, want):
    return live is not None and all([live[slot] == want[slot] for slot in range(len(want))])


def solve_held(puzzle_id, log):
    """Opens the held box and slides it into the solved arrangement. False when it couldn't be opened or the board
    never converged; either way the caller talks to the NPC again, and the box is shut."""
    box = None
    for i in inventory.items():
        if i.id == puzzle_id:
            box = i
            break
    if box is None:
        log('no puzzle box held')
        return False
    if not is_open():
        box.interact(OPEN_OP)
        opened = yield from execution.delay_until(is_open, OPEN_WAIT_MS)
        if not opened:
            log('puzzle box did not open')
            return False
    solved = yield from _slide(log)
    # Why: every way out must leave the modal shut, or an open main interface blocks the hand-back talk and every
    # walk after it.
    yield from close()
    return solved


def _slide(log):
    moved = 0
    stalled = 0
    plan = []
    while moved < MAX_MOVES and stalled < STALL_LIMIT:
        board = board_now()
        if board is None:
            log('puzzle board went unreadable mid-solve')
            return False
        if is_puzzle_solved(board):
            log('puzzle already solved' if moved == 0 else f'puzzle solved in {moved} moves')
            return True
        if len(plan) == 0:
            # Why: a solve can take a Debug build most of a script call's time budget, so it gets a step of its own.
            yield from execution.delay_ticks(1)
            plan = solve_puzzle(board) or []
            if len(plan) == 0:
                log('puzzle board is not solvable as read: retrying from a fresh read')
                stalled += 1
                yield from execution.delay_ticks(1)
                continue
            if moved == 0:
                log(f'puzzle: {len(plan)} moves to solve')
        slot = plan[0]
        want = list(board)
        if not apply_puzzle_move(want, slot) or not _click(slot):
            plan = []
            stalled += 1
            yield from execution.delay_ticks(1)
            continue
        landed = yield from execution.delay_until(lambda: _same(board_now(), want), MOVE_SETTLE_MS)
        if landed:
            plan.pop(0)
            moved += 1
            stalled = 0
        else:
            plan = []
            stalled += 1
    log(f'puzzle stalled after {moved} moves ({stalled} refused in a row)')
    return False
