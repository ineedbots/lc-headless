# The run manager's policy and the stall guard's clock, ported in part from rs2b0t's test/runtime (MIT, see
# thirdparty/rs2b0t). The host-side restart is in tests/Script/ScriptHostTests.cpp.

from rs2004.geometry import Tile
from rs2004.upkeep import resolve_run_policy, should_enable_run, StallGuard, anchor_is_far, run_manager
from rs2004.upkeep import RETRY_MS

MINUTE = 60000


def test_the_override_wins_where_it_sets_a_choice():
    assert resolve_run_policy(None, True, 20) == (True, 20)
    assert resolve_run_policy({'run_auto': False, 'energy_min': None}, True, 20) == (False, 20)
    assert resolve_run_policy({'run_auto': None, 'energy_min': 50}, True, 20) == (True, 50)
    assert resolve_run_policy({'run_auto': None, 'energy_min': 150}, True, 20) == (True, 100)
    assert resolve_run_policy(None, True, -5) == (True, 0)


def test_run_goes_on_at_the_threshold_but_not_over_a_modal():
    assert should_enable_run(False, False, 20, 20, False)
    assert not should_enable_run(False, False, 19, 20, False)
    assert not should_enable_run(True, False, 100, 20, False)
    assert not should_enable_run(False, False, 100, 20, True)


def test_under_attack_any_energy_will_do_even_over_a_modal():
    assert should_enable_run(False, True, 1, 20, True)
    assert not should_enable_run(False, True, 0, 20, False)


def test_override_replaces_the_whole_snapshot_and_none_clears_it():
    run_manager.configure(True, 20)
    run_manager.override(energy_min=60)
    assert run_manager.policy() == (True, 60)
    run_manager.override(run_auto=False)
    assert run_manager.policy() == (False, 20)
    run_manager.override()
    assert run_manager.policy() == (True, 20)


def ticking(guard, start, end, tile=(1, 1, 0), xp=0, noted=None):
    """Observes every 600 ms from start to end; the first time a recovery came due, or None."""
    now = start
    while now <= end:
        if guard.observe(now, tile, xp, noted):
            return now
        now += 600
    return None


def test_a_bot_that_stays_put_is_stalled_after_the_limit():
    guard = StallGuard()
    guard.configure(10)
    due = ticking(guard, 0, 11 * MINUTE)
    assert due is not None and due > 10 * MINUTE and due <= 10 * MINUTE + 600


def test_moving_gaining_experience_or_noting_progress_resets_the_clock():
    guard = StallGuard()
    guard.configure(10)
    assert ticking(guard, 0, 9 * MINUTE) is None
    assert not guard.observe(9 * MINUTE + 600, (2, 1, 0), 0, None)
    assert ticking(guard, 9 * MINUTE + 1200, 18 * MINUTE, tile=(2, 1, 0)) is None
    assert not guard.observe(18 * MINUTE + 600, (2, 1, 0), 25, None)
    assert ticking(guard, 18 * MINUTE + 1200, 27 * MINUTE, tile=(2, 1, 0), xp=25) is None
    assert ticking(guard, 27 * MINUTE + 600, 36 * MINUTE, tile=(2, 1, 0), xp=25, noted=27 * MINUTE) is None


def test_time_away_is_not_a_stall():
    guard = StallGuard()
    guard.configure(10)
    assert ticking(guard, 0, 9 * MINUTE) is None
    # Logged out for 5 minutes, as during a relog.
    assert ticking(guard, 14 * MINUTE, 22 * MINUTE) is None


def test_a_recovery_is_not_tried_again_for_fifteen_minutes():
    guard = StallGuard()
    guard.configure(10)
    first = ticking(guard, 0, 11 * MINUTE)
    assert first is not None
    second = ticking(guard, first + 600, first + RETRY_MS + 1200)
    assert second is not None and second > first + RETRY_MS


def test_off_at_zero_and_while_something_else_has_taken_over():
    guard = StallGuard()
    assert ticking(guard, 0, 30 * MINUTE) is None
    guard.configure(10)
    guard.reset(0)
    now = 0
    while now < 20 * MINUTE:
        guard.busy(now)
        now += 600
    assert not guard.observe(now, (1, 1, 0), 0, None)


def test_the_anchor_is_walked_to_only_when_it_is_far_or_on_another_level():
    assert not anchor_is_far(Tile(100, 100, 0), 108, 92, 0)
    assert anchor_is_far(Tile(100, 100, 0), 109, 100, 0)
    assert anchor_is_far(Tile(100, 100, 1), 100, 100, 0)
