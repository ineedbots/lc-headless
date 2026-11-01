"""Ported from rs2b0t's src/bot/api/ai/quests/defs/heroquest/feather.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.catalogs.tasks import sustain
from rs2004.entities import ground_items, locs, npcs
from rs2004.game import game, skills
from rs2004.geometry import Tile
from rs2004.items import equipment, inventory
from rs2004.quests.defs.heroquest.areas import HERO_ID, HERO_NAMED, HERO_NPC, HERO_SHOP, HERO_TILE, on_entrana
from rs2004.quests.defs.heroquest.shops import kit_step, priced
from rs2004.quests.defs.heroquest.state import anywhere, banked_id, food_name, held_food, held_id, worn_id
from rs2004.quests.defs.knightssword.supplies import pickaxe_at
from rs2004.quests.defs.trollstronghold.combat import fight
from rs2004.quests.exec.primitives import talk_through
from rs2004.quests.exec.prompts import settle_scene
from rs2004.quests.food import FOOD_FLOAT
from rs2004.traversal import traversal

__all__ = ['combat_kit_step', 'kill_ice_queen', 'sail_to_entrana', 'sail_from_entrana', 'take_feather', 'feather_step', 'ENTRANA_LANDING']

# Why: the Ice Queen is level 111 with 104 hitpoints and the kit is Scavvo's on the Champions' Guild upper floor. Each float clears the asking price of a shop below base stock, which buys at more.
COMBAT_KIT = [
    Record({'id': 1113, 'name': 'Rune chainbody', 'qty': 1, 'sources': [priced(HERO_SHOP.SCAVVO, 80000)]}),
    Record({'id': 1079, 'name': 'Rune platelegs', 'qty': 1, 'sources': [priced(HERO_SHOP.SCAVVO, 100000)]}),
    Record({'id': 1303, 'name': 'Rune longsword', 'qty': 1, 'sources': [priced(HERO_SHOP.SCAVVO, 55000)]}),
]
FOOD_TARGET = FOOD_FLOAT
FIREBIRD_MS = 90000
ICE_QUEEN_TICKS = 600
ICE_QUEEN_RESPAWN_MS = 300000
PLANK_TRIES = 6


def entrana_keep():
    """Everything Entrana's monks allow: the gloves carry no `armour_*` category, coins and food never did."""
    return [HERO_NAMED.ICE_GLOVES.lower(), 'coins', food_name().lower()]


def has_entrana_spillover(snap):
    keep = entrana_keep()
    return any([not (name in keep) for name in list(list(snap.inv.keys()))])


# Why: The engine lowercases `inv` and `worn`, so compare normalized names or stripped equipment appears present.
def wearing_anything_else(snap):
    gloves = HERO_NAMED.ICE_GLOVES.lower()
    return any([name != gloves for name in list(snap.worn)])


def unequip_all(_log):
    for item in equipment.items():
        if item.name == HERO_NAMED.ICE_GLOVES:
            continue
        _c4 = item.name
        if _c4:
            _w5 = yield from equipment.unequip(item.name)
            _c4 = not (_w5)
        if _c4:
            return False
    return all([item.name == HERO_NAMED.ICE_GLOVES for item in equipment.items()])


def combat_kit_step(snap):
    return kit_step(snap, COMBAT_KIT)


def ice_queen():
    return npcs.query().where(lambda n: n.id == HERO_NPC.ICE_QUEEN).nearest()


def gloves_on_floor():
    return ground_items.query().where(lambda g: g.id == HERO_ID.ICE_GLOVES).within(12).nearest()


def kill_ice_queen(log):
    """Kill the Ice Queen and take the gloves she drops."""
    if inventory.count_by_id(HERO_ID.ICE_GLOVES) > 0:
        return True
    _w6 = yield from traversal.walk_resilient(HERO_TILE.ICE_QUEEN, radius=3, attempts=2, timeout_ms=180000, log=log)
    if not (_w6):
        log('could not reach the Ice Queen; the rockslide needs 50 Mining and a usable pickaxe')
        return False
    # Why: the partner needs gloves too and there's one Queen, so she may be dead when this bot arrives, and with nothing to fight the win below reads true at once with no drop, until the quest parks.
    if ice_queen() is None and gloves_on_floor() is None:
        log('the Ice Queen is not here; waiting for her to respawn')
        came = yield from execution.delay_until(lambda: ice_queen() is not None or gloves_on_floor() is not None, ICE_QUEEN_RESPAWN_MS)
        if not came:
            log('the Ice Queen never respawned')
            return False
    won = yield from fight(Record({
        'what': 'Ice Queen',
        'target': lambda: ice_queen(),
        'won': lambda: ice_queen() is None or gloves_on_floor() is not None,
        'protect': 'melee',
        'guard': ICE_QUEEN_TICKS,
    }), log)
    if not won:
        return False
    drop = gloves_on_floor()
    if not drop:
        log('the Ice Queen is down but no ice gloves are on the floor')
        return False
    if not drop.interact('Take'):
        return False
    _result8 = yield from execution.delay_until(lambda: inventory.count_by_id(HERO_ID.ICE_GLOVES) > 0, 8000)
    return _result8


# Why: every ferry lands on the deck at level 1 and the Gangplank loc is absent from the scene for a tick or 2 after the region change, so an early click leaves the bot aboard with `onEntrana` false.
def step_off_ship(log):
    """Cross the gangplank off whatever deck the character is standing on."""
    if (game.tile().level if game.tile() is not None else None) == 0:
        return True
    for attempt in range(PLANK_TRIES):
        yield from settle_scene()
        plank = locs.query().name('Gangplank').action('Cross').within(12).nearest()
        _c9 = plank and (plank.interact('Cross'))
        if _c9:
            _w10 = yield from execution.delay_until(lambda: (game.tile().level if game.tile() is not None else None) == 0, 10000)
            _c9 = (_w10)
        if _c9:
            return True
    log('still on the ship deck: no Gangplank offered Cross')
    return False


def sail_to_entrana(log):
    _w11 = yield from step_off_ship(log)
    if not (_w11):
        return False
    if on_entrana(game.tile()):
        return True
    _w12 = yield from traversal.walk_resilient(HERO_TILE.PORT_SARIM_MONK, radius=3, attempts=3, timeout_ms=180000, log=log)
    if not (_w12):
        return False
    _w13 = yield from talk_through('Monk of Entrana', ["Yes, okay, I'm ready to go."], log)
    if not (_w13):
        return False

    def _fn14():
        tile = game.tile()
        return tile is not None and tile.x >= 2790 and tile.x <= 2880 and tile.z >= 3290 and tile.z <= 3440
    landed = yield from execution.delay_until(_fn14, 30000)
    _c15 = not landed
    if not _c15:
        _w16 = yield from step_off_ship(log)
        _c15 = not (_w16)
    if _c15:
        return False
    return on_entrana(game.tile())


def sail_from_entrana(log):
    _w17 = yield from step_off_ship(log)
    if not (_w17):
        return False
    if not on_entrana(game.tile()):
        return True
    _w18 = yield from traversal.walk_resilient(HERO_TILE.ENTRANA_DOCK, radius=3, attempts=3, timeout_ms=120000, log=log)
    if not (_w18):
        return False
    _w19 = yield from talk_through('Monk of Entrana', ["Yes, I'm ready to go."], log)
    if not (_w19):
        return False
    yield from execution.delay_until(lambda: not on_entrana(game.tile()), 30000)
    _w20 = yield from step_off_ship(log)
    if not (_w20):
        return False
    return not on_entrana(game.tile())


# Why: the feather burns for hitpoints/8 + 1 and stays on the floor unless the gloves are worn, so the equip is part of the pickup.
def take_feather(log):
    """Kill the level-2 firebird barehanded and take the feather with the gloves on."""
    if inventory.count_by_id(HERO_ID.FEATHER) > 0:
        return True
    _w21 = yield from traversal.walk_resilient(HERO_TILE.FIREBIRD, radius=4, attempts=3, timeout_ms=120000, log=log)
    if not (_w21):
        return False
    _c22 = not equipment.contains(HERO_NAMED.ICE_GLOVES)
    if _c22:
        _w23 = yield from equipment.equip(HERO_NAMED.ICE_GLOVES)
        _c22 = not (_w23)
    if _c22:
        log('could not wear the ice gloves — the feather cannot be picked up without them')
        return False

    def feather():
        return ground_items.query().where(lambda g: g.id == HERO_ID.FEATHER).within(12).nearest()

    def bird():
        return npcs.query().where(lambda n: n.id == HERO_NPC.FIREBIRD).nearest()

    deadline = _core.step_time() + FIREBIRD_MS
    while _core.step_time() < deadline and feather() is None:
        target = bird()
        if target and not game.in_combat():
            target.interact('Attack')
        yield from sustain.run()
        yield from execution.delay_ticks(2)
    drop = feather()
    if not drop:
        log('no fire feather on the floor after the firebird fight')
        return False
    if not drop.interact('Take'):
        return False
    _result25 = yield from execution.delay_until(lambda: inventory.count_by_id(HERO_ID.FEATHER) > 0, 8000)
    return _result25


def feather_step(snap):
    """The feather chain: gloves from the Ice Queen, then a stripped trip to Entrana."""
    # Why: the island has one way off it and no walkable route home, so a bot standing on it owes the ferry before anything else, a finished feather included.
    if on_entrana(snap.tile):
        if anywhere(snap, HERO_ID.FEATHER) > 0:
            return Record({'kind': 'custom', 'name': 'sail back from Entrana', 'run': sail_from_entrana})
        return Record({'kind': 'custom', 'name': 'take the firebird feather', 'run': take_feather})
    if anywhere(snap, HERO_ID.FEATHER) > 0:
        return None
    if held_id(snap, HERO_ID.ICE_GLOVES) == 0 and not worn_id(snap, HERO_ID.ICE_GLOVES):
        if banked_id(snap, HERO_ID.ICE_GLOVES) > 0:
            return Record({
                'kind': 'withdraw',
                'items': [{'name': HERO_NAMED.ICE_GLOVES, 'qty': 1, 'id': HERO_ID.ICE_GLOVES}],
            })
        mining = skills.level('mining')
        if mining < 50:
            return Record({'kind': 'wait', 'reason': '50 Mining is required to clear the Ice Queen rockslide'})
        kit = combat_kit_step(snap)
        if kit:
            return kit
        pickaxe = pickaxe_at(snap, mining)
        if pickaxe:
            return pickaxe
        if held_food(snap) < FOOD_TARGET:
            return Record({'kind': 'withdraw', 'items': [{'name': food_name(), 'qty': FOOD_TARGET}]})
        return Record({'kind': 'custom', 'name': 'kill the Ice Queen for her gloves', 'run': kill_ice_queen})
    if has_entrana_spillover(snap):
        return Record({'kind': 'deposit', 'keep': entrana_keep(), 'bank': HERO_TILE.DRAYNOR_BANK, 'exact_keep': True})
    if wearing_anything_else(snap):
        return Record({'kind': 'custom', 'name': 'strip the Entrana-restricted equipment', 'run': unequip_all})
    return Record({'kind': 'custom', 'name': 'sail from Port Sarim to Entrana', 'run': sail_to_entrana})


ENTRANA_LANDING = Tile(2834, 3331, 1)
