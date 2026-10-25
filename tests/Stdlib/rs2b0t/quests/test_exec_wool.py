"""rs2b0t's test/api/ai/quests/exec/wool.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.geometry import Tile
from rs2004.quests.defs.sheepshearer import gather_balls
from rs2004.quests.engine.types import QuestSnapshot
from rs2004.quests.exec.wool import UNSHEARED_SHEEP_ID, WoolSites, gather_wool

SITES = WoolSites(Tile(3197, 3266, 0), Tile(3209, 3213, 1), Tile(3152, 3306, 0), 'spin wool at Lumbridge')


def snap(items=None):
    return QuestSnapshot(journal='in_progress', inv={k: v for k, v in (items or [])}, inv_ids={}, worn=set(), worn_ids=set(),
                         no_progress=0, bank_coins=0)


def _fn1():
    def _fn2():
        expect(UNSHEARED_SHEEP_ID).to_be(43)
    test('the unsheared sheep npc id is 43', _fn2)

    def _fn3():
        step = gather_wool(snap(), 3, SITES)
        expect(step.kind).to_be('grab_ground')
        expect(step.item).to_be('Shears')
        expect(step.anchor.x).to_be(3152)
    test('no shears -> grab the shears spawn, not the pen', _fn3)

    def _fn4():
        step = gather_wool(snap([['shears', 1]]), 3, SITES)
        expect(step.kind).to_be('custom')
        expect(step.name).to_contain('shear')
    test('shears but not enough wool -> shear', _fn4)

    def _fn5():
        step = gather_wool(snap([['shears', 1], ['wool', 3]]), 3, SITES)
        expect(step.kind).to_be('custom')
        expect(step.name).to_be('spin wool at Lumbridge')
    test('enough wool -> spin, under the caller-supplied label', _fn5)


describe('gatherWool', _fn1)


def _fn6():
    def _fn7():
        expect(gather_balls(snap(), 20).kind).to_be('grab_ground')
        expect(gather_balls(snap([['shears', 1]]), 20).kind).to_be('custom')
        spin = gather_balls(snap([['shears', 1], ['wool', 20]]), 20)
        expect(spin.kind).to_be('custom')
        expect(spin.name).to_be('spin wool at Falador')
    test('gatherBalls still returns the same step kinds and the Falador label', _fn7)

    def _fn8():
        step = gather_balls(snap(), 20)
        expect(step.kind).to_be('grab_ground')
        expect(step.anchor.x).to_be(3152)
        expect(step.anchor.z).to_be(3306)
    test('its shears spawn is still the free one at 3152,3306', _fn8)


describe('sheepshearer keeps its own sites and its own labels', _fn6)
