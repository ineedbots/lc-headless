"""The sliding puzzle box: rs2b0t's api/ai/clues/puzzleLogic.ts (MIT, see thirdparty/rs2b0t). A board is a list of
25 slots, each the slot its piece belongs in when solved, or None for the gap."""

PUZZLE_WIDTH = 5
PUZZLE_SIZE = PUZZLE_WIDTH * PUZZLE_WIDTH
PUZZLE_BLANK_SLOT = PUZZLE_SIZE - 1

# Why: cells are placed in these batches, each frozen once solved, and batching the awkward ones (a row's last
# two, the final 3x3) lets the search find the rotation that frees them instead of hard-coding escape sequences.
_GROUPS = [
    [0], [1], [2], [3, 4],
    [5], [10], [15, 20],
    [6], [7], [8, 9],
    [11], [16, 21],
    [12, 13, 14],
    [17, 18, 19, 22, 23],
]


def _neighbours_of(slot):
    col = slot % PUZZLE_WIDTH
    out = []
    if col > 0:
        out.append(slot - 1)
    if col < PUZZLE_WIDTH - 1:
        out.append(slot + 1)
    if slot >= PUZZLE_WIDTH:
        out.append(slot - PUZZLE_WIDTH)
    if slot < PUZZLE_SIZE - PUZZLE_WIDTH:
        out.append(slot + PUZZLE_WIDTH)
    return out


_NEIGHBOURS = [_neighbours_of(slot) for slot in range(PUZZLE_SIZE)]


def puzzle_neighbours(slot):
    return list(_NEIGHBOURS[slot]) if 0 <= slot < PUZZLE_SIZE else []


def is_puzzle_solved(board):
    if len(board) != PUZZLE_SIZE:
        return False
    for slot in range(PUZZLE_SIZE):
        want = None if slot == PUZZLE_BLANK_SLOT else slot
        if board[slot] != want:
            return False
    return True


def _is_valid_board(board):
    if len(board) != PUZZLE_SIZE:
        return False
    seen = set()
    gaps = 0
    for value in board:
        if value is None:
            gaps += 1
            continue
        if type(value) is not int or value < 0 or value >= PUZZLE_BLANK_SLOT or value in seen:
            return False
        seen.add(value)
    return gaps == 1 and len(seen) == PUZZLE_BLANK_SLOT


def apply_puzzle_move(board, slot):
    """Slides the piece at slot into the gap beside it, in place. False when there's no gap beside it."""
    if type(slot) is not int or slot < 0 or slot >= PUZZLE_SIZE or board[slot] is None:
        return False
    for n in _NEIGHBOURS[slot]:
        if board[n] is None:
            board[n] = board[slot]
            board[slot] = None
            return True
    return False


def read_puzzle_board(slots, slot_of_piece, size=25):
    """A board from (slot, piece id) pairs, or None until every piece and all but one slot are there."""
    board = [None] * size
    filled = 0
    for slot, id in slots:
        target = slot_of_piece.get(id)
        if target is None or slot < 0 or slot >= size or board[slot] is not None:
            return None
        board[slot] = target
        filled += 1
    return board if filled == size - 1 else None


def _encode(pieces, gap):
    key = gap
    for p in pieces:
        key = key * PUZZLE_SIZE + p
    return key


def _search(start, start_gap, group, frozen):
    """The gap's moves that bring each of group's pieces home without touching a frozen slot."""
    in_group = set(group)
    count = len(group)

    def done(pieces, gap):
        if gap in in_group:
            return False
        for i in range(count):
            if pieces[i] != group[i]:
                return False
        return True

    if done(start, start_gap):
        return []
    start_key = _encode(start, start_gap)
    came_from = {start_key: (-1, -1)}
    frontier = [(start, start_gap, start_key)]
    while frontier:
        nxt = []
        for pieces, gap, key in frontier:
            for move in _NEIGHBOURS[gap]:
                if frozen[move]:
                    continue
                moved = list(pieces)
                for i in range(count):
                    if moved[i] == move:
                        moved[i] = gap
                        break
                new_key = _encode(moved, move)
                if new_key in came_from:
                    continue
                came_from[new_key] = (key, move)
                if done(moved, move):
                    path = []
                    cur = new_key
                    while cur != start_key:
                        prev, step = came_from[cur]
                        path.append(step)
                        cur = prev
                    path.reverse()
                    return path
                nxt.append((moved, move, new_key))
        frontier = nxt
    return None


def solve_puzzle(board):
    """The slots to click, in order, to solve the board, each sliding its piece into the gap beside it; None for
    a board that isn't one."""
    if not _is_valid_board(board):
        return None
    work = list(board)
    frozen = [False] * PUZZLE_SIZE
    moves = []
    for group in _GROUPS:
        pieces = [work.index(target) if target in work else -1 for target in group]
        if any([p < 0 for p in pieces]):
            return None
        leg = _search(pieces, work.index(None), group, frozen)
        if leg is None:
            return None
        for move in leg:
            apply_puzzle_move(work, move)
        moves.extend(leg)
        for target in group:
            frozen[target] = True
    return moves if is_puzzle_solved(work) else None
