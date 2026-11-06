"""Ported from rs2b0t's src/bot/api/ai/quests/defs/goblindiplomacy/redberries.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.catalogs.tasks import sustain
from rs2004.execution import event_signal
from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.quests.exec.steps import execute_step

__all__ = ['acquire_redberries']

SHOP = Record({'npc': 'Wydin', 'anchor': Tile(3014, 3204, 0)})
RESTOCK_TICKS = 100
SPAWNS = [Tile(3267, 3371, 0), Tile(3271, 3366, 0), Tile(3278, 3374, 0)]


def acquire_redberries(log):
    before = inventory.count('Redberries')
    if before >= 3:
        return True
    if event_signal.pending() or inventory.is_full():
        return False
    here = game.tile()
    if not here or here.level != 0 or SPAWNS[0].distance_to(here) > 24:
        yield from execute_step(Record({'kind': 'buy', 'item': 'Redberries', 'qty': 3 - before, 'shop': SHOP, 'est_gp': 60}), [], log)
        if inventory.count('Redberries') >= 3:
            return True
        log(f"Wydin supplied {inventory.count('Redberries') - before} redberries; gathering the remaining berries southeast of Varrock")
    for attempt in range(4):
        if event_signal.pending():
            return False
        if inventory.is_full():
            break
        round_before = inventory.count('Redberries')
        for anchor in SPAWNS:
            if event_signal.pending():
                return False
            if inventory.is_full():
                break
            yield from sustain.run()
            if event_signal.pending():
                return False
            yield from execute_step(Record({'kind': 'grab_ground', 'item': 'Redberries', 'anchor': anchor, 'wait_if_missing': True}), [], log)
            if inventory.count('Redberries') >= 3:
                return True
        if attempt == 3 or inventory.is_full():
            break
        if inventory.count('Redberries') > round_before:
            continue
        log(f"waiting for ground redberries to respawn ({inventory.count('Redberries')}/3, wait {attempt + 1}/3)")
        for tick in range(RESTOCK_TICKS):
            if event_signal.pending():
                return False
            yield from sustain.run()
            if event_signal.pending():
                return False
            yield from execution.delay_ticks(1)
    log(f"redberry acquisition stopped at {inventory.count('Redberries')}/3")
    return inventory.count('Redberries') > before
