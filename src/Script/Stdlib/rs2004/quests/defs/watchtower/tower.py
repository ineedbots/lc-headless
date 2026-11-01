"""Ported from rs2b0t's src/bot/api/ai/quests/defs/watchtower/tower.ts (MIT, see thirdparty/rs2b0t)."""

import _core

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.dialogue import chat_dialog
from rs2004.entities import locs, npcs
from rs2004.game import game, reader
from rs2004.items import inventory
from rs2004.quests.defs.watchtower.areas import WT_ITEM, WT_LOC, WT_NPC, WT_TILE, watchtower_area
from rs2004.quests.defs.watchtower.journal import WATCHTOWER_QUEST, WATCHTOWER_STAGE
from rs2004.quests.defs.watchtower.scene import settle_scene
from rs2004.quests.exec.primitives import drive_dialog, talk_through
from rs2004.reach import reach
from rs2004.tabs import quests
from rs2004.traversal import traversal

__all__ = ['climb_to_wizard', 'leave_wizard_floor', 'start_quest', 'search_evidence_bush', 'hand_in_fingernails', 'relic_state', 'give_relic_part', 'ask_wizard_for_relic', 'ask_wizard_about_shamans', 'show_crystals_to_wizard', 'pull_lever', 'read_spell_scroll']

def level():
    _v1 = (game.tile().level if game.tile() is not None else None)
    return (_v1 if _v1 is not None else -1)


def loc_near(id, op, within=8):
    return locs.query().where(lambda loc: loc.id == id).action(op).within(within).nearest()


def climb_wall(log):
    _w2 = yield from traversal.walk_resilient(WT_TILE.WALL_CLIMB_STAND, radius=1, attempts=3, timeout_ms=300000, log=log)
    if not (_w2):
        return False
    wall = loc_near(WT_LOC.WALL_CLIMB, 'Climb-up', 6)
    if not wall or not (wall.interact('Climb-up')):
        log('no climbable Watchtower wall in range')
        return False
    _result3 = yield from execution.delay_until(lambda: level() == 1, 10000)
    return _result3


def climb_tower_ladder(log):
    _w4 = yield from traversal.walk_resilient(WT_TILE.TOWER_LADDER_STAND, radius=1, attempts=3, timeout_ms=300000, log=log)
    if not (_w4):
        return False
    ladder = loc_near(WT_LOC.TOWER_LADDER, 'Climb-up', 6)
    if not ladder or not (ladder.interact('Climb-up')):
        log('no Watchtower ladder in range')
        return False
    _result5 = yield from execution.delay_until(lambda: level() == 1, 10000)
    return _result5


def climb_to_wizard(stage, log):
    if watchtower_area(game.tile()) == 'towerFloor':
        return True
    if level() == 0:
        # The tower guard refuses the ladder until the quest is started, so the baked ground-to-first-floor edge is a lie at stage 0.
        if stage <= WATCHTOWER_STAGE.NOT_STARTED:
            up = yield from climb_wall(log)
        else:
            up = yield from climb_tower_ladder(log)
        if not up:
            return False
    if level() != 1:
        return False
    yield from settle_scene()
    _w9 = yield from traversal.walk_resilient(WT_TILE.LADDER_UP_STAND, radius=1, attempts=3, timeout_ms=60000, log=log)
    if not (_w9):
        return False
    ladder = loc_near(WT_LOC.WATCH_LADDER_UP, 'Climb-up', 6)
    if not ladder or not (ladder.interact('Climb-up')):
        log('no ladder to the wizard floor in range')
        return False
    _result10 = yield from execution.delay_until(lambda: watchtower_area(game.tile()) == 'towerFloor', 10000)
    return _result10


def leave_wizard_floor(log):
    area = watchtower_area(game.tile())
    if area != 'towerFloor' and area != 'mirrorTower':
        return True
    down = loc_near(WT_LOC.WATCH_LADDER_DOWN, 'Climb-down', 10)
    if not down or not (down.interact('Climb-down')):
        log('no Watchtower ladder down in range')
        return False
    _w11 = yield from execution.delay_until(lambda: level() == 1, 10000)
    if not (_w11):
        return False
    yield from settle_scene()
    out = loc_near(WT_LOC.LADDER_TOP, 'Climb-down', 10)
    if not out or not (out.interact('Climb-down')):
        log('no first-floor ladder down in range')
        return False
    _result12 = yield from execution.delay_until(lambda: level() == 0, 10000)
    return _result12


def talk_to_wizard(prefer, log):
    _w13 = yield from reach.npc_dialog(WT_NPC.WIZARD, WT_TILE.WIZARD_FLOOR, log=log)
    if (_w13) != 'done':
        return False
    _result14 = yield from talk_through(WT_NPC.WIZARD, prefer, log)
    return _result14


def start_quest(log):
    _w15 = yield from climb_to_wizard(WATCHTOWER_STAGE.NOT_STARTED, log)
    if not (_w15):
        return False
    _result16 = yield from talk_to_wizard(["What's the matter?", "So how come the spell doesn't work?", 'Can I be of help?'], log)
    return _result16


def search_evidence_bush(log):
    if inventory.count(WT_ITEM.FINGERNAILS.name) > 0:
        return True
    _w17 = yield from traversal.walk_resilient(WT_TILE.BUSH_NAIL, radius=1, attempts=3, timeout_ms=300000, log=log)
    if not (_w17):
        return False
    if inventory.free() == 0:
        log('pack is full — the bush cannot hand over the fingernails')
        return False
    # 40-odd decoy bushes share the name, and only this one holds evidence.
    bush = locs.query().where(lambda loc: loc.id == WT_LOC.BUSH_NAIL).action('Search').within(6).nearest()
    if not bush or not (bush.interact('Search')):
        log('the fingernail bush is not in range')
        return False
    _result18 = yield from execution.delay_until(lambda: inventory.count(WT_ITEM.FINGERNAILS.name) > 0, 8000)
    return _result18


def hand_in_fingernails(log):
    if inventory.count(WT_ITEM.FINGERNAILS.name) == 0:
        log('no fingernails to hand in')
        return False
    _w19 = yield from climb_to_wizard(WATCHTOWER_STAGE.STARTED, log)
    if not (_w19):
        return False
    _result20 = yield from talk_to_wizard(['What do you suggest I do?', 'So what do I do?'], log)
    return _result20


# Why: the wizard's part bits are a server-only varp and the journal never lists them, so after a death has taken
# the parts the bot learns which he lacks by offering a replacement; "I already have that part" leaves it in the pack.
relic_state = Record({'refused': set(), 'asked': set()})


def wizard_has_part():
    """The wizard's refusal is on screen: a use-on that never landed must not read as one."""
    return chat_dialog.is_open() and any([('already have that part' in text.lower()) for text in chat_dialog.texts()])


def give_relic_part(id, log):
    _w21 = yield from climb_to_wizard(WATCHTOWER_STAGE.GIVEN_FINGERNAILS, log)
    if not (_w21):
        return False
    part = ([item for item in inventory.items() if item.id == id] or [None])[0]
    if not part:
        log(f'relic part {id} is not in the pack')
        return False
    wizard = npcs.query().name(WT_NPC.WIZARD).nearest()
    if not wizard or not (part.use_on(wizard)):
        return False
    # Why: the player's "I had this given to me..." comes first, so the boxes are clicked on while watching for his reply.
    for i in range(20):
        if all([item.id != id for item in inventory.items()]):
            _result23 = yield from drive_dialog([], log)
            return _result23
        if wizard_has_part():
            relic_state.refused.add(id)
            log(f'the wizard already holds relic part {id}')
            yield from drive_dialog([], log)
            return True
        if chat_dialog.can_continue():
            yield from chat_dialog.continue_()
        yield from execution.delay_ticks(1)
    return False


def ask_wizard_for_relic(log):
    _w24 = yield from climb_to_wizard(WATCHTOWER_STAGE.MADE_RELIC, log)
    if not (_w24):
        return False
    _result25 = yield from talk_to_wizard(['I have lost the relic you gave me.'], log)
    return _result25


def ask_wizard_about_shamans(log):
    _w26 = yield from climb_to_wizard(WATCHTOWER_STAGE.FED_NIGHTSHADE, log)
    if not (_w26):
        return False
    _result27 = yield from talk_to_wizard([], log)
    return _result27


def show_crystals_to_wizard(log):
    _w28 = yield from climb_to_wizard(WATCHTOWER_STAGE.MADE_POTION, log)
    if not (_w28):
        return False
    crystal = ([item for item in inventory.items() if item.id == WT_ITEM.CRYSTAL1.id] or [None])[0]
    wizard = npcs.query().name(WT_NPC.WIZARD).nearest()
    if not crystal or not wizard or not (crystal.use_on(wizard)):
        return False
    _result29 = yield from drive_dialog(['This is the last one.', 'I have found another crystal!'], log)
    return _result29


def pull_lever(log):
    _w30 = yield from climb_to_wizard(WATCHTOWER_STAGE.FOUND_ALL_CRYSTALS, log)
    if not (_w30):
        return False
    _w31 = yield from traversal.walk_resilient(WT_TILE.LEVER_STAND, radius=1, attempts=3, timeout_ms=60000, log=log)
    if not (_w31):
        return False
    lever = loc_near(WT_LOC.LEVER, 'Pull', 6)
    if not lever or not (lever.interact('Pull')):
        log('no Watchtower lever in range')
        return False
    _result32 = yield from execution.delay_until(lambda: quests.status(WATCHTOWER_QUEST) == 'complete', 40000)
    return _result32


def read_spell_scroll(log):
    scroll = ([item for item in inventory.items() if item.id == WT_ITEM.WATCHTOWER_SPELL.id] or [None])[0]
    if not scroll:
        return True
    if not (scroll.interact('Read')):
        return False
    yield from execution.delay_ticks(2)
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    log('memorised the Watchtower Teleport scroll')
    return True
