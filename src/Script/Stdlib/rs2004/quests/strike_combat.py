"""Fighting with Strike spells from cover: rs2b0t's api/ai/quests/strikeCombat.ts (MIT, see thirdparty/rs2b0t). The
cover tiles the quests fight from, the sight check from cover, and one cast that waits for its hit."""

from rs2004 import execution
from rs2004.catalogs.tasks import sustain
from rs2004.execution import event_signal
from rs2004.game import direct_navigator, game, skills
from rs2004.geometry import Tile
from rs2004.entities import npcs
from rs2004.hunting.logic import body_origin
from rs2004.items import equipment, inventory
from rs2004.navigation import reachability
from rs2004.quests.strike import strike_spell
from rs2004.tabs import autocast
from rs2004.traversal import traversal

__all__ = [
    'ARENA_COVER', 'ARENA_LURE', 'DEMON_COVER', 'EXPERIMENT_COVER', 'EXPERIMENT_TRAP', 'at_cover', 'cast_from_cover',
    'ready_strikes', 'take_strike_cover', 'cast_strike',
]

ARENA_COVER = Tile(2594, 3167, 0)
ARENA_LURE = [Tile(2598, 3167, 0), Tile(2598, 3169, 0), Tile(2594, 3169, 0), ARENA_COVER]
DEMON_COVER = Tile(2472, 9865, 0)
EXPERIMENT_COVER = Tile(2936, 3465, 0)
EXPERIMENT_TRAP = Tile(2937, 3466, 0)

# What a caster keeps on: staves, amulets, capes, light gloves and boots, robes.
CASTER_WEAR = ['staff', 'amulet', 'cape', 'leather gloves', 'leather boots', 'robe', 'wizard']


def at_cover(tile):
    here = game.tile()
    return here is not None and tile == here


def cast_from_cover(spot, target):
    """Whether a Strike from spot reaches target: in range, on its level, in sight, and inside the lane the cover
    is for."""
    centre = target.network_tile()
    origin = body_origin(centre, target.size)
    tile = Tile(origin.x, origin.z, centre.level)
    distance = max(tile.x - spot.x, spot.x - tile.x - target.size + 1, tile.z - spot.z, spot.z - tile.z - target.size + 1)
    if tile.level != spot.level or distance > 10 or distance < 1:
        return False
    if spot == ARENA_COVER and not ((tile.x >= 2596 and tile.z >= 3166 and tile.z <= 3168) or (tile.x >= 2594 and tile.z == 3169)):
        return False
    if spot == EXPERIMENT_COVER and EXPERIMENT_TRAP != tile:
        return False
    return reachability.line_of_sight(spot, tile, target.size)


def _casterly(name):
    lower = name.lower()
    for part in CASTER_WEAR:
        if part in lower:
            return True
    return False


def ready_strikes(log):
    """Retaliation off, autocast off, and melee gear taken off; True when a Strike can be cast. Use with yield
    from."""
    game.set_auto_retaliate(False)
    off = yield from execution.delay_until_ticks(lambda: not game.auto_retaliate_on(), 5)
    if not off:
        return False
    if autocast.armed():
        opened = yield from game.open_side_tab(0)
        if not opened:
            return False
        disarmed = yield from autocast.disarm()
        if not disarmed:
            return False
    for item in equipment.items():
        if not item.name or _casterly(item.name):
            continue
        removed = yield from equipment.unequip(item.name)
        if not removed:
            log(f'need room to remove {item.name} before casting')
            return False
    return strike_spell(skills.effective('magic'), lambda rune: inventory.count(rune)) is not None


def take_strike_cover(spot, log, lure_target=None):
    """Walks to spot, by the arena's lure path when it's the arena's cover, casting at lure_target() on the way
    when it's in sight. True once at cover. Use with yield from."""
    if at_cover(spot) and lure_target is None:
        return True
    route = ARENA_LURE if spot == ARENA_COVER else [spot]
    for tile in route:
        if event_signal.pending():
            return False
        yield from sustain.run()
        walked = yield from traversal.walk_resilient(tile, radius=0, attempts=2, timeout_ms=30000, log=log)
        if not walked:
            return False
        if tile == ARENA_LURE[0] and lure_target is not None:
            target = lure_target()
            if target is not None and not target.targets_me() and cast_from_cover(tile, target):
                cast = yield from cast_strike(tile, target, log)
                if not cast:
                    return False
    return at_cover(spot)


class _Cast:
    def __init__(self):
        self.settled = False
        self.returning = False


def _same_npc(target):
    for npc in npcs.all():
        if npc.index == target.index and npc.id == target.id:
            return npc
    return None


def _cast_and_watch(spot, target, spell, before, state):
    if not game.cast_on_npc(spell, target):
        return False
    for tick in range(10):
        if event_signal.pending():
            return False
        yield from sustain.run()
        if not at_cover(spot):
            state.returning = direct_navigator.walk(spot)
            return False
        current = _same_npc(target)
        if game.auto_retaliate_on() or autocast.armed() or (current is not None and not cast_from_cover(spot, current)):
            game.set_auto_retaliate(False)
            return False
        if tick >= 5 and inventory.count('Mind rune') < before:
            state.settled = True
            return True
        yield from execution.delay_ticks(1)
    return False


def cast_strike(spot, target, log):
    """Casts the best Strike at target from spot and waits for the runes to go. Off cover or out of sight, it gives
    up and steps back onto its own tile, so the cast isn't walked into. Use with yield from."""
    if event_signal.pending() or game.auto_retaliate_on() or not at_cover(spot) or not cast_from_cover(spot, target):
        return False
    spell = strike_spell(skills.effective('magic'), lambda rune: inventory.count(rune))
    if spell is None:
        log('out of Strike runes; holding cover')
        return False
    before = inventory.count('Mind rune')
    state = _Cast()
    cast = yield from _cast_and_watch(spot, target, spell, before, state)
    # Why: rs2b0t's finally: a cast that didn't land leaves the player walking at the target, so stand still.
    if not state.settled and not state.returning:
        here = game.tile()
        if here is not None:
            direct_navigator.walk(Tile(here.x, here.z, here.level))
    return cast
