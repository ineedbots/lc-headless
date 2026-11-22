"""Regicide's lost-spade recovery across a death restart and failed sources."""

from rs2004.execution import event_signal
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


def reports_missing_spawn():
    spade.reset_recovery()
    scene = Scene(RG_TILE.ARDOUGNE_BANK)
    spy_on(event_signal, 'pending', returns=False)

    expect(run_wait(spade.recover_spade(scene.log))).to_be(False)
    expect(scene.logged('no spade is available at the Ardougne spawn')).to_be(True)
    expect(scene.walks).to_equal([spade.SPADE_SPAWN])
    expect(run_wait(spade.recover_spade(scene.log))).to_be(False)
    expect(scene.walks).to_equal([spade.SPADE_SPAWN])
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
    expect(stopped.reason).to_be('no spade in pack or bank; the Ardougne spawn recovery attempt failed')


test('an empty spawn fails with a clear reason after one visit', reports_missing_spawn)


def reports_unreachable_spawn():
    spade.reset_recovery()
    scene = Scene(RG_TILE.ARDOUGNE_BANK)
    scene.walk_ok = False
    spy_on(event_signal, 'pending', returns=False)

    expect(run_wait(spade.recover_spade(scene.log))).to_be(False)
    expect(scene.logged('could not reach the Ardougne spade spawn')).to_be(True)
    expect(scene.walks).to_equal([spade.SPADE_SPAWN])


test('an unreachable spawn fails after the bounded walk attempts', reports_unreachable_spawn)


def reports_failed_pickup():
    spade.reset_recovery()
    scene = Scene(RG_TILE.ARDOUGNE_BANK)
    scene.on_ground(RG_ITEM.SPADE.id, RG_ITEM.SPADE.name, tile=spade.SPADE_SPAWN, dist=1, effect=lambda op: False)
    spy_on(event_signal, 'pending', returns=False)

    expect(run_wait(spade.recover_spade(scene.log))).to_be(False)
    expect(scene.logged('the Ardougne spade was not acquired')).to_be(True)
    expect(scene.walks).to_equal([spade.SPADE_SPAWN])


test('a refused ground pickup fails with a clear reason', reports_failed_pickup)
