"""rs2b0t's test/event/webwalk/pathFollowPolicy.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.routeplan import DEFAULT_DOOR_STEP_TICKS, DEFAULT_PATH_DEVIATION_CHEBYSHEV, DEFAULT_PATH_STALL_TICKS, DEFAULT_TRANSPORT_APPROACH_CHEBYSHEV, resolve_path_follow_config



def _fn1():
    def _fn2():
        c = resolve_path_follow_config()
        expect(c.stall_ticks).to_be(DEFAULT_PATH_STALL_TICKS)
        expect(c.deviation_chebyshev).to_be(DEFAULT_PATH_DEVIATION_CHEBYSHEV)
        expect(c.transport_approach_chebyshev).to_be(DEFAULT_TRANSPORT_APPROACH_CHEBYSHEV)
        expect(c.stall_ticks).to_be(5)
        expect(c.deviation_chebyshev).to_be(10)
    test('defaults match observed client/baked path slop', _fn2)

    def _fn3():
        c = resolve_path_follow_config(Obj({'stall_ticks': 15, 'deviation_chebyshev': 12}))
        expect(c.stall_ticks).to_be(15)
        expect(c.deviation_chebyshev).to_be(12)
    test('walk opts override defaults', _fn3)


describe('resolvePathFollowConfig', _fn1)


def _fn4():
    def _fn5():
        expect(DEFAULT_DOOR_STEP_TICKS).to_be(1)
        expect(resolve_path_follow_config().door_step_ticks).to_be(1)
    test('defaults to one tick after the open leaf shows', _fn5)

    def _fn6():
        expect(resolve_path_follow_config(Obj({'door_step_ticks': 0})).door_step_ticks).to_be(0)
    test('a walk can step on the open frame', _fn6)

    def _fn7():
        expect(resolve_path_follow_config(Obj({'door_step_ticks': -3})).door_step_ticks).to_be(0)
        expect(resolve_path_follow_config(Obj({'door_step_ticks': 1.9})).door_step_ticks).to_be(1)
    test('never waits a negative or fractional tick', _fn7)


describe('doorStepTicks', _fn4)
