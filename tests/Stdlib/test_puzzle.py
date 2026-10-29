"""Reject impossible puzzle reads before search and preserve legal-move solutions."""

import rs2004.clues.puzzle as puzzle


class NoSearch:
    def __enter__(self):
        self.search = puzzle._search
        puzzle._search = self.unexpected_search
        return self

    def __exit__(self, *args):
        puzzle._search = self.search

    def unexpected_search(self, *args):
        assert False, 'an impossible board must not reach the search'


def test_odd_parity_boards_are_rejected_without_search_or_mutation():
    with NoSearch():
        board = list(range(24)) + [None]
        board[0], board[1] = board[1], board[0]
        # Moving the gap across rows must not change the parity decision.
        for slot in [24, 23, 18, 13, 8, 3, 2, 1, 0]:
            if slot != 24:
                assert puzzle.apply_puzzle_move(board, slot)
            before = list(board)
            assert puzzle.solve_puzzle(board) is None
            assert board == before


def test_even_parity_board_with_displaced_gap_solves_without_mutating_input():
    board = list(range(24)) + [None]
    for slot in [23, 18, 17]:
        assert puzzle.apply_puzzle_move(board, slot)
    before = list(board)
    plan = puzzle.solve_puzzle(board)
    assert plan is not None and len(plan) > 0
    assert board == before
    for slot in plan:
        assert puzzle.apply_puzzle_move(board, slot)
    assert puzzle.is_puzzle_solved(board)
