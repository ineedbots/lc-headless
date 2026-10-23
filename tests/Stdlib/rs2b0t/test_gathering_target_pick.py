"""rs2b0t's test/scripts/GatheringBot/TargetPick.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs import Record, pick_bucket_nearest, pick_nearest_prefer_local, should_cooldown_gather_tile
from bots.gathering.tasks import LOCAL_MINE_PREFER_RADIUS


def _fn1():
    def rock(id, dist):
        return (Record({'id': id, 'dist': dist}))

    def _fn2():
        near = rock('near', 3)
        far = rock('far', 28)
        expect(LOCAL_MINE_PREFER_RADIUS).to_be(12)
        expect((pick_nearest_prefer_local([far, near], lambda r: r.dist).id if pick_nearest_prefer_local([far, near], lambda r: r.dist) is not None else None)).to_be('near')
        expect((pick_nearest_prefer_local([far], lambda r: r.dist).id if pick_nearest_prefer_local([far], lambda r: r.dist) is not None else None)).to_be('far')
    test('prefers local cluster when any rock is within prefer radius', _fn2)

    def _fn3():
        a = rock('a', 5)
        b = rock('b', 2)
        far = rock('far', 40)
        expect((pick_nearest_prefer_local([a, far, b], lambda r: r.dist).id if pick_nearest_prefer_local([a, far, b], lambda r: r.dist) is not None else None)).to_be('b')
    test('among local rocks picks the closest', _fn3)

    def _fn4():
        expect(pick_nearest_prefer_local([], lambda: 0)).to_be(None)
    test('empty candidates → null', _fn4)


describe('pickNearestPreferLocal', _fn1)


def _fn5():
    def rock(id, bucket, dist):
        return (Record({'id': id, 'bucket': bucket, 'dist': dist}))

    def _fn6():
        coal = rock('coal', 6, 40)
        iron = rock('iron', 3, 2)
        expect((pick_bucket_nearest([iron, coal], lambda r: r.bucket, lambda r: r.dist).id if pick_bucket_nearest([iron, coal], lambda r: r.bucket, lambda r: r.dist) is not None else None)).to_be('coal')
    test('the best bucket wins even when farther away', _fn6)

    def _fn7():
        local = rock('local', 6, 3)
        far = rock('far', 6, 30)
        lower = rock('lower', 1, 1)
        expect((pick_bucket_nearest([lower, far, local], lambda r: r.bucket, lambda r: r.dist).id if pick_bucket_nearest([lower, far, local], lambda r: r.bucket, lambda r: r.dist) is not None else None)).to_be('local')
        expect((pick_bucket_nearest([lower, far], lambda r: r.bucket, lambda r: r.dist).id if pick_bucket_nearest([lower, far], lambda r: r.bucket, lambda r: r.dist) is not None else None)).to_be('far')
    test('within the best bucket, the nearest wins and the local radius still applies', _fn7)

    def _fn8():
        expect(pick_bucket_nearest([], lambda: 0, lambda: 0)).to_be(None)
    test('empty candidates → null', _fn8)


describe('pickBucketNearest', _fn5)


def _fn9():
    def _fn10():
        expect(should_cooldown_gather_tile(True, True)).to_be(False)
        expect(should_cooldown_gather_tile(True, False)).to_be(False)
    test('does not cooldown after a successful ore/log', _fn10)

    def _fn11():
        expect(should_cooldown_gather_tile(False, True)).to_be(True)
        expect(should_cooldown_gather_tile(False, False)).to_be(False)
    test('cools only failed clicks when other targets exist', _fn11)


describe('shouldCooldownGatherTile', _fn9)
