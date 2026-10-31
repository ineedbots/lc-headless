"""Ported from rs2b0t's src/bot/api/ai/quests/defs/biohazard/ardougne.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.entities import ground_items
from rs2004.game import game
from rs2004.items import inventory
from rs2004.quests.defs.biohazard.areas import BIO_ITEM, BIO_LOC, BIO_NPC, BIO_TILE, in_pigeon_zone
from rs2004.quests.defs.biohazard.gear import held_id
from rs2004.quests.defs.biohazard.travel import loc_by_id, talk_at, walk_to
from rs2004.quests.exec.prompts import drive_until, settle_scene

__all__ = ['start_quest', 'ask_jerico', 'hand_over_distillator', 'report_to_elena', 'ask_elena_for_replacements', 'confront_lathas', 'take_birdfeed', 'take_pigeons', 'feed_the_tower', 'release_pigeons']

START_PREFER = ["I'll try to retrieve it for you."]
REISSUE_PREFER = ["I'm afraid I've lost some of the stuff that you gave me"]
LATHAS_PREFER = ["I don't understand"]


def start_quest(log):
    return talk_at(BIO_NPC.ELENA, BIO_TILE.ELENA, START_PREFER, log)


def ask_jerico(log):
    return talk_at(BIO_NPC.JERICO, BIO_TILE.JERICO, [], log)


def hand_over_distillator(log):
    return talk_at(BIO_NPC.ELENA, BIO_TILE.ELENA, [], log)


def report_to_elena(log):
    return talk_at(BIO_NPC.ELENA, BIO_TILE.ELENA, [], log)


# Why: Elena reissues every vial and the sample she still owes, gated on the pack, so this is the only recovery for a vial an errand boy drank, sold or painted with.
def ask_elena_for_replacements(log):
    return talk_at(BIO_NPC.ELENA, BIO_TILE.ELENA, REISSUE_PREFER, log)


# Why: the second branch closes the dialogue without queueing quest_biohazard_complete.
def confront_lathas(log):
    return talk_at(BIO_NPC.LATHAS, BIO_TILE.LATHAS, LATHAS_PREFER, log)


def take_birdfeed(log):
    """Open Jerico's cupboard, then search it. It refuses a second bag while one is banked."""
    _w1 = yield from walk_to(BIO_TILE.JERICO_CUPBOARD, 1, log)
    if not (_w1):
        return False
    yield from settle_scene()
    open = loc_by_id(BIO_LOC.JERICO_CUPBOARD_OPEN, 'Search', 6)
    if open:
        if not (open.interact('Search')):
            return False
        _result2 = yield from drive_until(lambda: held_id(BIO_ITEM.BIRDFEED.id) > 0, [], log, 10000)
        return _result2
    shut = loc_by_id(BIO_LOC.JERICO_CUPBOARD_SHUT, 'Open', 6)
    if not shut or not (shut.interact('Open')):
        log("no cupboard in Jerico's house")
        return False
    _result3 = yield from execution.delay_until(lambda: loc_by_id(BIO_LOC.JERICO_CUPBOARD_OPEN, 'Search', 6) is not None, 6000)
    return _result3


# Why: The spent `pigeoncage` shares the display name, so match the filled cage by id.
def take_pigeons(log):
    _w4 = yield from walk_to(BIO_TILE.PIGEON_SPAWN, 1, log)
    if not (_w4):
        return False
    yield from settle_scene()
    cage = ground_items.query().where(lambda item: item.id == BIO_ITEM.PIGEONS.id).within(8).nearest()
    if not cage:
        log(f'no full Pigeon cage at ({BIO_TILE.PIGEON_SPAWN.x},{BIO_TILE.PIGEON_SPAWN.z}) — waiting for the respawn')
        yield from execution.delay_ticks(4)
        return False
    if not (cage.interact('Take')):
        return False
    _result5 = yield from execution.delay_until(lambda: held_id(BIO_ITEM.PIGEONS.id) > 0, 8000)
    return _result5


def feed_the_tower(log):
    """Throw the seed onto the tower. The mourners do not react until the birds follow it."""
    _w6 = yield from walk_to(BIO_TILE.WATCHTOWER, 1, log)
    if not (_w6):
        return False
    yield from settle_scene()
    tower = loc_by_id(BIO_LOC.WATCHTOWER, None, 8)
    feed = ([item for item in inventory.items() if item.id == BIO_ITEM.BIRDFEED.id] or [None])[0]
    if not tower or not feed:
        log(f"no {('Bird feed' if tower else 'Watchtower')} for the distraction")
        return False
    if not (feed.use_on(tower)):
        return False
    _w7 = yield from drive_until(lambda: held_id(BIO_ITEM.BIRDFEED.id) == 0, [], log, 15000)
    if not (_w7):
        return False
    # Why: the script deletes the seed, waits 2 ticks and only then moves the stage, so returning on the empty slot hands the next decide a journal that still says "fetch bird feed".
    yield from execution.delay_ticks(4)
    return True


# Why: `opheld1,pigeons` only fires inside 2559..2565 x 3299..3307; outside it the cage answers "The pigeons don't want to leave" and the stage never moves.
def release_pigeons(log):
    _c8 = not in_pigeon_zone(game.tile())
    if _c8:
        _w9 = yield from walk_to(BIO_TILE.WATCHTOWER, 1, log)
        _c8 = not (_w9)
    if _c8:
        return False
    if not in_pigeon_zone(game.tile()):
        here = game.tile()
        log(f'({(here.x if here is not None else None)},{(here.z if here is not None else None)}) is outside the pigeon-release box — the cage would not open')
        return False
    cage = ([item for item in inventory.items() if item.id == BIO_ITEM.PIGEONS.id] or [None])[0]
    if not cage or not (cage.interact('Open')):
        log('no full Pigeon cage in the pack to open')
        return False
    _result10 = yield from drive_until(lambda: held_id(BIO_ITEM.PIGEONS.id) == 0, [], log, 20000)
    return _result10
