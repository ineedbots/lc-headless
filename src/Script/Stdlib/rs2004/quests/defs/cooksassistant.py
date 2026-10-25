"""Cook's Assistant: rs2b0t's api/ai/quests/defs/cooksassistant.ts (MIT, see thirdparty/rs2b0t). An egg from the
farm's pen, milk from a cow, and flour milled from wheat at the windmill, for the Lumbridge cook."""

from rs2004 import execution
from rs2004.entities import locs
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.messages import game_messages
from rs2004.quests.data import quest_record
from rs2004.quests.engine.types import QuestModule, quest_step
from rs2004.quests.exec.primitives import NpcStop
from rs2004.traversal import traversal

__all__ = ['COOK', 'gather_flour', 'gather_milk', 'gather_egg', 'decide', 'cooksassistant']

COOK = NpcStop('Cook', Tile(3209, 3215, 0), 6, ["What's wrong?", "Yes, I'll help you."])
EGG_PEN = Tile(3227, 3300, 0)
FARMHOUSE_BUCKET = Tile(3225, 3294, 0)
COW_FIELD = Tile(3255, 3288, 0)
WHEAT_FIELD = Tile(3158, 3300, 0)
POT_SPAWN = Tile(3208, 3213, 0)
MILL_TOP = Tile(3166, 3306, 2)
MILL_BASE = Tile(3166, 3306, 0)


def _says(*needles):
    def matches(text):
        lower = text.lower()
        for needle in needles:
            if needle in lower:
                return True
        return False
    return matches


GRAIN_LOADED = _says('you put the grain in the hopper', 'there is already grain in the hopper')
GRAIN_GROUND = _says('the grain slides down the chute')
HOPPER_EMPTY = _says('you operate the empty hopper')
BIN_ALREADY_FULL = _says('flour bin downstairs is full, i should empty')


def _scene_has(name):
    """Locs read blank for about a tick after a level change. Use with yield from."""
    found = yield from execution.delay_until(lambda: locs.query().name(name).within(8).exists(), 6000)
    return found


def _fill_hopper(log):
    grain = inventory.first('Grain')
    if grain is None:
        return True
    hopper = locs.query().name('Hopper').within(8).nearest()
    if hopper is None:
        log('no Hopper on the mill top floor')
        return False
    mark = game_messages.mark()
    log('putting the grain in the hopper')
    if not grain.use_on(hopper):
        return False
    # Why: the grain leaves the pack before the server walks us to the hopper, so only the closing message means the
    # fill is done; acting on the pack sends the next op mid-walk, where it's dropped.
    loaded = yield from execution.delay_until(lambda: game_messages.saw_since(mark, GRAIN_LOADED), 20000)
    return loaded


def _grind_hopper(log):
    """'ground', 'bin_full' or 'failed'. Use with yield from."""
    controls = locs.query().name('Hopper controls').action('Operate').within(8).nearest()
    if controls is None:
        log('no Hopper controls on the top floor')
        return 'failed'
    mark = game_messages.mark()
    log('operating the hopper controls to grind the flour')
    if not controls.interact('Operate'):
        return 'failed'

    def settled():
        return game_messages.saw_since(mark, GRAIN_GROUND) or game_messages.saw_since(mark, BIN_ALREADY_FULL) or game_messages.saw_since(mark, HOPPER_EMPTY)

    answered = yield from execution.delay_until(settled, 20000)
    if not answered:
        log('the hopper controls never answered')
        return 'failed'
    if game_messages.saw_since(mark, GRAIN_GROUND):
        return 'ground'
    if game_messages.saw_since(mark, BIN_ALREADY_FULL):
        log('the flour bin is already full downstairs')
        return 'bin_full'
    log('the hopper was still empty when the controls were pulled')
    return 'failed'


def mill_flour(log):
    """Grain into the hopper, the controls, then the flour bin into the pot. Use with yield from."""
    walked = yield from traversal.walk_resilient(MILL_TOP, radius=2, attempts=3, timeout_ms=120000, log=log)
    if not walked:
        return False
    loaded = yield from _scene_has('Hopper controls')
    if not loaded:
        log('the mill top floor has not loaded')
        return False
    filled = yield from _fill_hopper(log)
    if not filled:
        return False
    ground = yield from _grind_hopper(log)
    if ground == 'failed':
        return False
    log('heading down to the flour bin')
    walked = yield from traversal.walk_resilient(MILL_BASE, radius=2, attempts=3, timeout_ms=120000, log=log)
    if not walked:
        return False
    loaded = yield from _scene_has('Flour bin')
    if not loaded:
        log('the mill ground floor has not loaded')
        return False
    flour_bin = locs.query().name('Flour bin').action('Empty').within(8).nearest()
    if flour_bin is None or not flour_bin.interact('Empty'):
        return False
    log('emptying the flour bin into the pot')
    filled = yield from execution.delay_until(lambda: inventory.contains('Pot of flour'), 15000)
    return filled


def gather_flour(snap, need=1):
    if 'pot' not in snap.inv:
        return quest_step('grab_ground', item='Pot', anchor=POT_SPAWN)
    if 'grain' not in snap.inv:
        return quest_step('pick_loc', loc='Wheat', op='Pick', item='Grain', anchor=WHEAT_FIELD)
    return quest_step('custom', name='mill flour', run=mill_flour)


def gather_milk(snap, need=1):
    if 'bucket' not in snap.inv:
        return quest_step('grab_ground', item='Bucket', anchor=FARMHOUSE_BUCKET)
    return quest_step('use_on', item='Bucket', target_kind='npc', target='Cow', anchor=COW_FIELD, product='Bucket of milk')


def gather_egg(snap=None, need=1):
    return quest_step('grab_ground', item='Egg', anchor=EGG_PEN, wait_if_missing=True)


def decide(snap):
    if snap.journal == 'complete':
        return quest_step('done')
    if snap.journal == 'unknown':
        return quest_step('wait', reason='quest journal not loaded')
    if snap.journal == 'not_started':
        return quest_step('talk', stop=COOK)
    if 'egg' not in snap.inv:
        return gather_egg()
    if 'bucket of milk' not in snap.inv:
        return gather_milk(snap)
    if 'pot of flour' not in snap.inv:
        return gather_flour(snap)
    return quest_step('talk', stop=COOK)


cooksassistant = QuestModule(
    record=quest_record('cook'),
    bank=Tile(3093, 3243, 0),
    coin_float=0,
    tools=['pot', 'grain', 'bucket', 'egg'],
    gather={'egg': gather_egg, 'bucket of milk': gather_milk, 'pot of flour': gather_flour},
    decide=decide,
)
