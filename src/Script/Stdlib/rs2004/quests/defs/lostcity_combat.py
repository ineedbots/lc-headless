"""Ported from rs2b0t's src/bot/api/ai/quests/defs/lostcityCombat.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.combat import SPELL_DB, casts_available
from rs2004.catalogs.tasks import sustain
from rs2004.entities import locs, npcs
from rs2004.execution import event_signal
from rs2004.game import direct_navigator, game, skills
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.traversal import traversal

__all__ = ['TREE_SPIRIT_SAFESPOT', 'TREE_SPIRIT_TRAP', 'TREE_STAND', 'LURE', 'highest_lost_city_strike', 'defeat_tree_spirit']

STRIKES = ['Fire Strike', 'Earth Strike', 'Water Strike', 'Wind Strike']
TREE_SPIRIT_SAFESPOT = Tile(2859, 9731, 0)
TREE_SPIRIT_TRAP = Tile(2859, 9733, 0)
TREE_STAND = Tile(2860, 9733, 0)
LURE = [Tile(2860, 9732, 0), Tile(2860, 9731, 0), TREE_SPIRIT_SAFESPOT]


def here():
    return game.tile()


def at(tile):
    position = here()
    return position is not None and tile.equals(position)


def spirit():
    return ([npc for npc in npcs.all() if npc.id == 655 and not npc.targets_another_player() and not (npc.health == 0 and npc.max_health > 0)] or [None])[0]


def trapped():
    target = spirit()
    return target is not None and TREE_SPIRIT_TRAP.equals(target.network_tile())


def strike():
    return highest_lost_city_strike(skills.effective('magic'), lambda name: inventory.count(name))


def highest_lost_city_strike(magic, count):
    return ([name for name in STRIKES if SPELL_DB[name]['level'] <= magic and casts_available(name, [], count) > 0] or [None])[0]


def take_cover(log):
    if at(TREE_SPIRIT_SAFESPOT) and trapped():
        return True
    _w2 = yield from traversal.walk_resilient(TREE_STAND, radius=0, attempts=2, timeout_ms=30000, log=log)
    if not (_w2):
        return False
    for tile in LURE:
        if event_signal.pending() or not (direct_navigator.walk(tile)):
            return False
        arrived = False
        for tick in range(8):
            if event_signal.pending():
                return False
            yield from sustain.run()
            if at(tile):
                arrived = True
                break
            yield from execution.delay_ticks(1)
        if not arrived:
            return False
    for tick in range(15):
        if event_signal.pending() or not at(TREE_SPIRIT_SAFESPOT):
            return False
        if trapped():
            log('Tree Spirit trapped behind the fungus; casting from 2859,9731')
            return True
        yield from sustain.run()
        yield from execution.delay_ticks(1)
    log('Tree Spirit did not reach the trapped tile; withholding casts')
    return False


class PendingCast:
    """Whether a cast's walk is still queued, so the safespot has to be stood on again."""

    def __init__(self):
        self.pending = True


def step_back(cast):
    if cast.pending:
        position = here()
        if position:
            direct_navigator.walk(position)


def settle_cast(spell, target, cast, log):
    """Cast once from the safespot and wait for the runes to go. True once they have."""
    before = inventory.count('Mind rune')
    consumed = False
    if not (game.cast_on_npc(spell, target)):
        log(f'could not cast {spell}; holding the Tree Spirit safespot')
        return False
    for tick in range(10):
        if event_signal.pending():
            return False
        yield from sustain.run()
        if not at(TREE_SPIRIT_SAFESPOT):
            cast.pending = not (direct_navigator.walk(TREE_SPIRIT_SAFESPOT))
            log('cast moved away from the Tree Spirit safespot')
            return False
        if game.auto_retaliate_on() or (spirit() and not trapped()):
            game.set_auto_retaliate(False)
            log('Tree Spirit moved before the cast settled; cancelling')
            return False
        consumed = consumed or inventory.count('Mind rune') < before
        if tick >= 5 and consumed:
            break
        yield from execution.delay_ticks(1)
    if not consumed:
        log(f'{spell} did not consume runes; holding cover')
        return False
    cast.pending = False
    return True


def defeat_tree_spirit(log, complete):
    if event_signal.pending():
        return False
    retaliate = game.auto_retaliate_on()
    game.set_auto_retaliate(False)
    _w3 = yield from execution.delay_until_ticks(lambda: not game.auto_retaliate_on(), 5)
    if not (_w3):
        return False
    if not spirit():
        _w4 = yield from complete()
        if _w4:
            game.set_auto_retaliate(retaliate)
            return True
        if not strike():
            log('no castable Strike spell; supply runes before summoning the Tree Spirit')
            return False
        if any([npc.id == 655 for npc in npcs.all()]):
            log('waiting for the other player to finish their Tree Spirit')
            return False
        _w5 = yield from traversal.walk_resilient(TREE_STAND, radius=0, attempts=2, timeout_ms=90000, log=log)
        if not (_w5):
            return False
        tree = locs.query().where(lambda loc: loc.id == 1292).action('Chop down').within(8).nearest()
        if not tree or not (tree.interact('Chop down')):
            return False
        _w6 = yield from execution.delay_until_ticks(lambda: spirit() is not None, 20)
        if not (_w6):
            return False
    _w7 = yield from take_cover(log)
    if not (_w7):
        return False
    deadline = _core.step_time() + 540000
    casts = 0
    missing = 0
    while _core.step_time() < deadline and casts < 300:
        if event_signal.pending():
            return False
        yield from sustain.run()
        target = spirit()
        if not target:
            missing += 1
            if missing < 5:
                yield from execution.delay_ticks(1)
                continue
            _w8 = yield from complete()
            if not (_w8):
                log('Tree Spirit disappeared without quest credit')
                return False
            log(f'Tree Spirit defeated with {casts} Strike casts')
            game.set_auto_retaliate(retaliate)
            return True
        missing = 0
        if game.auto_retaliate_on():
            game.set_auto_retaliate(False)
            return False
        if not at(TREE_SPIRIT_SAFESPOT) or not trapped():
            log('Tree Spirit safespot changed; withholding casts')
            yield from take_cover(log)
            return False
        spell = strike()
        if not spell:
            log('no castable Strike spell; holding the Tree Spirit safespot')
            return False
        cast = PendingCast()
        try:
            landed = yield from settle_cast(spell, target, cast, log)
        except Exception as e:
            step_back(cast)
            raise e
        step_back(cast)
        if not landed:
            return False
        casts += 1
        log(f'Tree Spirit: {spell} cast {casts}')
    log('Tree Spirit cast budget reached; holding cover')
    return False
