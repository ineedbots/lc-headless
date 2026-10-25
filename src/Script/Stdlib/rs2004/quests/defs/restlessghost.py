"""The Restless Ghost: rs2b0t's api/ai/quests/defs/restlessghost.ts (MIT, see thirdparty/rs2b0t). Father Urhney's
amulet, the ghost in Lumbridge's graveyard, and its skull from under the Wizards' Tower."""

from rs2004 import execution
from rs2004.entities import ground_items, locs, npcs
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.quests.data import quest_record
from rs2004.quests.defs.runemysteries import WIZARD_HOPS
from rs2004.quests.engine.types import QuestModule, quest_step
from rs2004.quests.exec.primitives import NpcStop, talk_through, walk_with_hops

__all__ = ['AMULET', 'SKULL', 'AERECK', 'URHNEY', 'decide', 'restlessghost']

AMULET = 'Ghostspeak amulet'
SKULL = 'Skull'

AERECK = NpcStop('Father Aereck', Tile(3244, 3206, 0), 6, ["I'm looking for a quest!"])
URHNEY = NpcStop('Father Urhney', Tile(3235, 3154, 0), 6,
                 ['Father Aereck sent me to talk to you.', "He's got a ghost haunting his graveyard.", "I've lost the amulet."])
GHOST_PREFER = ['Yep, now tell me what the problem is.']
COFFIN_STAND = Tile(3250, 3193, 0)
SKULL_TILE = Tile(3120, 9565, 0)


def _ensure_coffin_open(log):
    shut = locs.query().name('Coffin').action('Open').within(6).nearest()
    if shut is not None:
        shut.interact('Open')
        yield from execution.delay_ticks(2)


def _skull_near():
    return ground_items.query().name(SKULL).within(10).nearest()


def _grab_skull(log):
    for cycle in range(10):
        skull = _skull_near()
        if skull is not None:
            skull.interact('Take')
            taken = yield from execution.delay_until(lambda: inventory.contains(SKULL), 8000)
            if taken:
                return True
            log('lost the skull to another quester — waiting for it to respawn')
        else:
            log('altar skull already taken — waiting for the shared spawn to respawn')
        yield from execution.delay_until(lambda: _skull_near() is not None, 70000)
    log('altar skull never returned — re-entering to re-check the ghost trip')
    return False


def ghost_and_skull(log):
    """The ghost at its coffin, then the skull from the altar. Use with yield from."""
    walked = yield from walk_with_hops(COFFIN_STAND, 2, WIZARD_HOPS, log)
    if not walked:
        return False
    yield from _ensure_coffin_open(log)
    if npcs.query().name('Restless ghost').within(8).nearest() is None:
        log('no ghost after opening the coffin — re-check next loop')
        return False
    talked = yield from talk_through('Restless ghost', GHOST_PREFER, log)
    if not talked:
        return False
    walked = yield from walk_with_hops(SKULL_TILE, 2, WIZARD_HOPS, log)
    if not walked:
        return False
    grabbed = yield from _grab_skull(log)
    return grabbed


def return_skull(log):
    """The skull back into the coffin. Use with yield from."""
    walked = yield from walk_with_hops(COFFIN_STAND, 2, WIZARD_HOPS, log)
    if not walked:
        return False
    yield from _ensure_coffin_open(log)
    coffin = locs.query().name('Coffin').within(6).nearest()
    skull = inventory.first(SKULL)
    if coffin is None or skull is None:
        return False
    if not skull.use_on(coffin):
        return False
    gone = yield from execution.delay_until(lambda: not inventory.contains(SKULL), 8000)
    return gone


def decide(snap):
    if snap.journal == 'complete':
        return quest_step('done')
    if snap.journal == 'unknown':
        return quest_step('wait', reason='quest journal not loaded')
    if snap.journal == 'not_started':
        return quest_step('talk', stop=AERECK)
    if 'skull' in snap.inv:
        return quest_step('custom', name='return skull', run=return_skull)
    amulet = AMULET.lower()
    if amulet not in snap.inv and amulet not in snap.worn:
        return quest_step('talk', stop=URHNEY)
    if amulet not in snap.worn:
        return quest_step('equip', item=AMULET)
    return quest_step('custom', name='ghost + skull', run=ghost_and_skull)


restlessghost = QuestModule(
    record=quest_record('priest'),
    bank=Tile(3093, 3243, 0),
    tools=['ghostspeak amulet', 'skull'],
    hops=WIZARD_HOPS,
    decide=decide,
)
