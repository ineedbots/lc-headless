from rs2004.reach import _can_reach


def test_doors_and_gates_are_told_shut_or_open_by_their_options():
    assert is_openable_barrier('Door', ['Open', 'Knock-at'])
    assert is_openable_barrier('Large gate', [None, 'Open'])
    assert not is_openable_barrier('Door', ['Close'])
    assert not is_openable_barrier('Crate', ['Open'])
    assert not is_openable_barrier(None, ['Open'])
    assert is_open_barrier_leaf('Gate', ['Close'])
    assert not is_open_barrier_leaf('Gate', ['Open'])


def test_options_are_found_by_how_they_start():
    assert open_op(['Knock-at', 'Open']) == 'Open'
    assert close_op(['Open']) is None
    assert talk_op(['Attack', 'Talk-to']) == 'Talk-to'
    assert talk_op([]) is None


def test_a_door_toward_the_target_is_no_further_from_it_than_you_are_give_or_take():
    here = Tile(3200, 3200)
    target = Tile(3210, 3200)
    assert toward_dest(Tile(3205, 3200), here, target)
    assert toward_dest(Tile(3197, 3200), here, target)
    assert not toward_dest(Tile(3190, 3200), here, target)


def test_game_messages_match_text_by_part_or_a_callable():
    assert game_messages.mark() == 0
    assert game_messages.since(0) == []
    assert not game_messages.saw_since(0, CANT_REACH)
    assert WRONG_SIDE('You cannot do that from here.') and WRONG_SIDE("You can't do that from here.")
    assert not WRONG_SIDE('Nothing interesting happens.')
