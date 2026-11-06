"""Death Plateau recovers missing supplies and stops mountain errands at failed transitions."""

import rs2004.quests.defs.deathplateau as dp
from rs2004.quests.engine.types import QuestProgress, QuestSnapshot


def answer(value):
    def wait(*args, **kwargs):
        return value
        yield
    return wait


def sourcing():
    snap = QuestSnapshot(bank_known=False, inv={}, inv_ids={}, bank={}, bank_ids={}, free_slots=28)
    expect(dp.source_coins(snap, 100).kind).to_be('scan_bank')
    expect(dp.source_named(snap, 'Bread', dp.DEATH_ITEM.BREAD.id, 10).kind).to_be('scan_bank')
    expect(dp.source_cocktail(snap).kind).to_be('scan_bank')
    snap.bank_known = True
    expect(dp.source_named(snap, 'Bread', dp.DEATH_ITEM.BREAD.id, 10).kind).to_be('wait')
    snap.bank = {'coins': 1000}
    expect(dp.source_coins(snap, 100).kind).to_be('withdraw')
    snap.free_slots = 0
    expect(dp.make_space(snap, 1).keep).to_equal(['coins'])
    expect(dp.source_cocktail(snap).kind).to_be('deposit')
    scene = Scene(dp.BALL_PICKUP[0].at)
    spy_on(dp, 'walk_to', impl=scene._walk)
    id = dp.BALL_PICKUP[0].id
    scene.on_ground(id, 'Stone ball', effect=lambda op: False)
    expect(run_wait(dp.take_ground_ball(id, scene.at, scene.log))).to_be(False)
    scene.ground = []
    scene.on_ground(id, 'Stone ball')
    expect(run_wait(dp.take_ground_ball(id, scene.at, scene.log))).to_be(True)


test('Death Plateau scans before sourcing, makes room and verifies coloured-ball ground takes', sourcing)


def mountain_errands():
    scene = Scene(dp.TILE.TENZING)
    snap = QuestSnapshot(journal='in_progress', progress=None, inv={}, inv_ids={}, bank={}, bank_ids={}, bank_known=True, free_slots=28)
    expect(dp.decide(snap).kind).to_be('wait')
    snap.journal = 'unknown'
    expect(dp.decide(snap).kind).to_be('wait')
    snap.journal = 'in_progress'
    snap.progress = QuestProgress(dp.DP_STAGE.UNLOCKED_DOOR, set())
    map = Fake(saba=False, tenzing=False, smithy=False, entrancecert=False, given_cert=False,
               supplies=False, got_map=False, scouted=False)
    spy_on(dp, 'effective_map', returns=map)
    spy_on(dp, 'equip_floor', returns=dp.DP_STAGE.UNLOCKED_DOOR)
    snap.inv_ids[dp.DEATH_ITEM.COMBINATION.id] = 1
    enter = spy_on(dp, 'enter_saba_cave', impl=answer(False))
    talk = spy_on(dp, 'talk_at', impl=answer(False))
    leave = spy_on(dp, 'leave_saba_cave', impl=answer(False))
    door = spy_on(dp, 'open_tenzing_door', impl=answer(False))
    expect(run_wait(dp.decide(snap).run(scene.log))).to_be(False)
    enter.mock_implementation(answer(True))
    expect(run_wait(dp.decide(snap).run(scene.log))).to_be(False)
    map.saba = True
    spy_on(dp, 'in_saba_cave', returns=True)
    expect(run_wait(dp.decide(snap).run(scene.log))).to_be(False)
    leave.mock_implementation(answer(True))
    expect(run_wait(dp.decide(snap).run(scene.log))).to_be(False)
    door.mock_implementation(answer(True))
    expect(run_wait(dp.decide(snap).run(scene.log))).to_be(False)
    map.tenzing = True
    leave.mock_implementation(answer(False))
    expect(run_wait(dp.decide(snap).run(scene.log))).to_be(False)
    leave.mock_implementation(answer(True))
    expect(run_wait(dp.decide(snap).run(scene.log))).to_be(False)
    map.smithy = True
    map.entrancecert = True
    expect(dp.decide(snap).kind).to_be('custom')
    snap.inv_ids[dp.DEATH_ITEM.ENTRANCE_CERT.id] = 1
    expect(dp.decide(snap).run).to_be(dp.give_cert_to_dunstan)
    map.given_cert = True
    snap.inv_ids[dp.DEATH_ITEM.IRON_BAR.id] = 1
    door.mock_implementation(answer(False))
    expect(run_wait(dp.decide(snap).run(scene.log))).to_be(False)
    snap.inv_ids[dp.DEATH_ITEM.SPIKED_BOOTS.id] = 1
    expect(dp.decide(snap).kind).to_be('wait')
    snap.inv_ids[dp.DEATH_ITEM.BREAD.id] = 10
    expect(dp.decide(snap).kind).to_be('wait')
    snap.inv_ids[dp.DEATH_ITEM.TROUT.id] = 10
    expect(run_wait(dp.decide(snap).run(scene.log))).to_be(False)
    map.supplies = True
    expect(run_wait(dp.decide(snap).run(scene.log))).to_be(False)
    map.got_map = True
    expect(run_wait(dp.decide(snap).run(scene.log))).to_be(False)


test('mountain errands stop at failed cave, house and dialogue transitions instead of advancing the map track', mountain_errands)


def certificate_timeout():
    scene = Scene(dp.TILE.DENULTH)
    spy_on(dp, 'walk_to', impl=answer(True))
    spy_on(dp, 'open_dialogue', impl=answer(True))
    spy_on(dp, 'drain_until', impl=answer(False))
    expect(run_wait(dp.get_entrance_cert_from_denulth(scene.log))).to_be(False)
    expect(scene.logged('entrance cert, held=0')).to_be(True)
    snap = QuestSnapshot(journal='in_progress', progress=QuestProgress(dp.DP_STAGE.COMPLETE, set()), inv_ids={})
    expect(dp.decide(snap).kind).to_be('done')
    snap.progress = QuestProgress(dp.DP_STAGE.GIVEN_IOU, set())
    snap.bank_known = True
    snap.inv = {}
    snap.bank = {}
    snap.bank_ids = {}
    expect(dp.decide(snap).run).to_be(dp.reclaim_iou_from_harold)


test('certificate retries report no delivered paper and a missing IOU is reclaimed before solving', certificate_timeout)
