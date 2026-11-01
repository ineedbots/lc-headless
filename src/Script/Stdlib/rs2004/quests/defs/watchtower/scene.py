"""Ported from rs2b0t's src/bot/api/ai/quests/defs/watchtower/scene.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.entities import locs

__all__ = ['settle_scene']

# Why: a blank Locs query is no evidence the loc is absent, so every scripted crossing in this quest settles before it decides anything is missing.
def settle_scene(within=16):
    """Wait for scenery to exist again after a level change or teleport."""
    yield from execution.delay_ticks(2)
    yield from execution.delay_until(lambda: locs.query().within(within).count() > 0, 5000)
