"""Regicide's lost-spade recovery across a death restart and failed sources."""

from rs2004.execution import event_signal
from rs2004.clues.tools import SPADE_SPAWNS
from rs2004.game import game
from rs2004.traversal import traversal
from rs2004.quests.defs.regicide import decide, spade
from rs2004.quests.defs.regicide.areas import RG_ITEM, RG_TILE
from rs2004.quests.defs.regicide.journal import RG_STAGE
from rs2004.quests.defs.regicide.supplies import KIT
from rs2004.quests.engine.types import QuestProgress, QuestSnapshot


def recovers_the_spade_after_death():
    spade.reset_recovery()
    scene = Scene(RG_TILE.ARDOUGNE_BANK)
    spy_on(event_signal, 'pending', returns=False)
    ground = scene.on_ground(RG_ITEM.SPADE.id, RG_ITEM.SPADE.name, tile=spade.SPADE_SPAWN, dist=1)

    expect(run_wait(spade.recover_spade(scene.log))).to_be(True)
    expect(scene.has(RG_ITEM.SPADE.id)).to_be(True)
    expect(ground in scene.ground).to_be(False)
    expect(scene.walks).to_equal([spade.SPADE_SPAWN])
    expect(scene.logged('recovered a spade at Ardougne')).to_be(True)


test('a death restart with no banked spade picks up the Ardougne ground spawn', recovers_the_spade_after_death)


def recovers_from_the_nearest_falador_spawn():
    spade.reset_recovery()
    scene = Scene(SPADE_SPAWNS[1])
    spy_on(event_signal, 'pending', returns=False)
    ground = scene.on_ground(RG_ITEM.SPADE.id, RG_ITEM.SPADE.name, tile=SPADE_SPAWNS[1], dist=1)

    expect(run_wait(spade.recover_spade(scene.log))).to_be(True)
    expect(scene.walks).to_equal([SPADE_SPAWNS[1]])
    expect(ground in scene.ground).to_be(False)
    expect(scene.logged('recovered a spade at Falador')).to_be(True)


test('a missing spade is recovered from the nearest Falador spawn', recovers_from_the_nearest_falador_spawn)


def recovers_by_spade_name_when_id_differs():
    spade.reset_recovery()
    scene = Scene(RG_TILE.ARDOUGNE_BANK)
    spy_on(event_signal, 'pending', returns=False)
    scene.on_ground(999, RG_ITEM.SPADE.name, tile=SPADE_SPAWNS[0], dist=1)

    expect(run_wait(spade.recover_spade(scene.log))).to_be(True)
    expect(scene.has(999)).to_be(True)


test('spade recovery recognizes a ground item by name when its id differs', recovers_by_spade_name_when_id_differs)


def returns_early_when_the_spade_is_already_carried():
    spade.reset_recovery()
    scene = Scene(RG_TILE.ARDOUGNE_BANK)
    scene.item(RG_ITEM.SPADE.id, RG_ITEM.SPADE.name)

    expect(run_wait(spade.recover_spade(scene.log))).to_be(True)
    expect(scene.walks).to_equal([])
    expect(spade.recovery_failed()).to_be(False)


test('spade recovery returns immediately when the spade is already in inventory', returns_early_when_the_spade_is_already_carried)


def keeps_the_default_spawn_order_without_a_tile():
    spade.reset_recovery()
    scene = Scene(None)
    spy_on(game, 'tile', returns=None)
    spy_on(event_signal, 'pending', returns=False)

    expect(run_wait(spade.recover_spade(scene.log))).to_be(False)
    expect(scene.walks).to_equal(SPADE_SPAWNS)


test('spade recovery uses the known spawn order when the player tile is unavailable', keeps_the_default_spawn_order_without_a_tile)


def defers_recovery_when_an_event_is_pending():
    spade.reset_recovery()
    scene = Scene(RG_TILE.ARDOUGNE_BANK)
    spy_on(event_signal, 'pending', returns=True)

    expect(run_wait(spade.recover_spade(scene.log))).to_be(False)
    expect(scene.walks).to_equal([spade.SPADE_SPAWN])
    expect(spade.recovery_failed()).to_be(False)


test('spade recovery yields to a pending event and can be retried', defers_recovery_when_an_event_is_pending)


def walks_to_a_spade_beyond_the_spawn_radius():
    spade.reset_recovery()
    scene = Scene(RG_TILE.ARDOUGNE_BANK)
    scene.on_ground(RG_ITEM.SPADE.id, RG_ITEM.SPADE.name, tile=SPADE_SPAWNS[0], dist=2)
    spy_on(event_signal, 'pending', returns=False)

    expect(run_wait(spade.recover_spade(scene.log))).to_be(True)
    expect(scene.walks).to_equal([SPADE_SPAWNS[0], SPADE_SPAWNS[0]])
    expect(scene.has(RG_ITEM.SPADE.id)).to_be(True)


test('walks to a ground spade outside the spawn radius', walks_to_a_spade_beyond_the_spawn_radius)


def yields_to_an_event_while_walking_to_the_ground_item():
    spade.reset_recovery()
    scene = Scene(RG_TILE.ARDOUGNE_BANK)
    scene.on_ground(RG_ITEM.SPADE.id, RG_ITEM.SPADE.name, tile=SPADE_SPAWNS[0], dist=2)
    pending = [False, True]
    spy_on(event_signal, 'pending', impl=lambda: pending.pop(0))

    expect(run_wait(spade.recover_spade(scene.log))).to_be(False)
    expect(scene.walks).to_equal([SPADE_SPAWNS[0], SPADE_SPAWNS[0]])
    expect(spade.recovery_failed()).to_be(False)


test('spade recovery yields to an event while approaching the ground item', yields_to_an_event_while_walking_to_the_ground_item)


def skips_a_ground_spade_that_cannot_be_reached():
    spade.reset_recovery()
    scene = Scene(RG_TILE.ARDOUGNE_BANK)
    scene.on_ground(RG_ITEM.SPADE.id, RG_ITEM.SPADE.name, tile=SPADE_SPAWNS[0], dist=2)
    outcomes = [True, False, False]

    def walk(dest, **kwargs):
        scene.walks.append(dest)
        return outcomes.pop(0)
        yield

    spy_on(traversal, 'walk_resilient', impl=walk)
    spy_on(event_signal, 'pending', returns=False)

    expect(run_wait(spade.recover_spade(scene.log))).to_be(False)
    expect(scene.logged('could not reach the spade at the Ardougne spawn')).to_be(True)
    expect(scene.walks).to_equal([SPADE_SPAWNS[0], SPADE_SPAWNS[0], SPADE_SPAWNS[1]])


test('spade recovery skips a ground item when its follow-up walk fails', skips_a_ground_spade_that_cannot_be_reached)


def reports_missing_spawn():
    spade.reset_recovery()
    scene = Scene(RG_TILE.ARDOUGNE_BANK)
    spy_on(event_signal, 'pending', returns=False)

    expect(run_wait(spade.recover_spade(scene.log))).to_be(False)
    expect(scene.logged('no spade is available at the Ardougne spawn')).to_be(True)
    expect(scene.logged('no spade is available at the Falador spawn')).to_be(True)
    expect(scene.walks).to_equal([spade.SPADE_SPAWN, SPADE_SPAWNS[1]])
    expect(run_wait(spade.recover_spade(scene.log))).to_be(False)
    expect(scene.walks).to_equal([spade.SPADE_SPAWN, SPADE_SPAWNS[1]])
    expect(scene.logged('already attempted and failed')).to_be(True)

    carried = {supply.item.id: supply.qty for supply in KIT if supply.item.id != RG_ITEM.SPADE.id}
    stopped = decide(QuestSnapshot(
        journal='in_progress',
        inv_ids=carried,
        worn={'rune scimitar'},
        worn_ids=set(),
        bank_known=True,
        bank_ids={},
        stage=RG_STAGE.SPOKEN_LATHAS,
        progress=QuestProgress(RG_STAGE.SPOKEN_LATHAS, set()),
        tile=RG_TILE.ARDOUGNE_BANK,
    ))
    expect(stopped.kind).to_be('wait')
    expect(stopped.reason).to_be('no spade in pack or bank; the bounded spawn recovery failed')


test('an empty spawn fails with a clear reason after one visit', reports_missing_spawn)


def reports_unreachable_spawn():
    spade.reset_recovery()
    scene = Scene(RG_TILE.ARDOUGNE_BANK)
    scene.walk_ok = False
    spy_on(event_signal, 'pending', returns=False)

    expect(run_wait(spade.recover_spade(scene.log))).to_be(False)
    expect(scene.logged('could not reach the Ardougne spade spawn')).to_be(True)
    expect(scene.logged('could not reach the Falador spade spawn')).to_be(True)
    expect(scene.walks).to_equal([spade.SPADE_SPAWN, SPADE_SPAWNS[1]])


test('an unreachable spawn fails after the bounded walk attempts', reports_unreachable_spawn)


def reports_failed_pickup():
    spade.reset_recovery()
    scene = Scene(RG_TILE.ARDOUGNE_BANK)
    scene.on_ground(RG_ITEM.SPADE.id, RG_ITEM.SPADE.name, tile=spade.SPADE_SPAWN, dist=1, effect=lambda op: False)
    spy_on(event_signal, 'pending', returns=False)

    expect(run_wait(spade.recover_spade(scene.log))).to_be(False)
    expect(scene.logged('the spade at the Ardougne spawn was not acquired')).to_be(True)
    expect(scene.walks).to_equal([spade.SPADE_SPAWN, SPADE_SPAWNS[1]])


test('a refused ground pickup fails with a clear reason', reports_failed_pickup)
