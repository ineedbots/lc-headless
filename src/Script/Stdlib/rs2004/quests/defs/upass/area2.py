"""Ported from rs2b0t's src/bot/api/ai/quests/defs/upass/area2.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.entities import npcs
from rs2004.game import game
from rs2004.items import inventory
from rs2004.quests.defs.upass.areas import UP_BADGES, UP_ITEM, UP_LOC, UP_NPC, UP_TILE, count_held
from rs2004.quests.defs.upass.bridge import fight_until_gone, loc_by_id, take_drop, walk_to
from rs2004.quests.exec.prompts import drive_until, held_id, settle_scene

__all__ = ['take_railing', 'crush_unicorn', 'drop_boulder', 'take_unicorn_horn', 'badges_held', 'cross_the_temple', 'kill_paladin', 'feed_blood_well', 'enter_main_cavern']

def take_railing(log):
    """Search the middle cage for the loose railing that levers the boulder."""
    if held_id(UP_ITEM.RAILING.id) > 0:
        return True
    _w1 = yield from walk_to(UP_TILE.RAILINGS_LOOSE, 1, log)
    if not (_w1):
        return False
    yield from settle_scene()
    cage = loc_by_id(UP_LOC.RAILINGS_LOOSE, 'Search', 8)
    if not cage or not (cage.interact('Search')):
        log('no searchable cage bars at the loose railing')
        return False
    _result2 = yield from drive_until(lambda: held_id(UP_ITEM.RAILING.id) > 0, [], log, 12000)
    return _result2


# Why: the journal can't tell this stage from the last: both print "Something is watching me" and "I must work my way deeper into these caverns" and differ only in strike-through colour. The horn is the signal, so taking it is part of the same step.
def crush_unicorn(log):
    """Lever the boulder onto the unicorn, then take the horn from what is left of the cage."""
    _c3 = held_id(UP_ITEM.UNICORN_HORN.id) == 0
    if _c3:
        _w4 = yield from drop_boulder(log)
        _c3 = not (_w4)
    if _c3:
        return False
    _result5 = yield from take_unicorn_horn(log)
    return _result5


def drop_boulder(log):
    """Lever the boulder onto the unicorn; the script telejumps the player west afterwards."""
    _w6 = yield from walk_to(UP_TILE.BOULDER, 2, log)
    if not (_w6):
        return False
    yield from settle_scene()
    boulder = npcs.query().where(lambda npc: npc.id == UP_NPC.BOULDER).within(10).nearest()
    railing = ([item for item in inventory.items() if item.id == UP_ITEM.RAILING.id] or [None])[0]
    # Why: no boulder and a smashed cage means the job is done; the stage moved and the journal didn't.
    if not boulder and loc_by_id(UP_LOC.UNICORN_CAGE, None, 16) is not None:
        log('the boulder is already down and the cage is smashed')
        return True
    if not boulder or not railing:
        log(f"missing {('the piece of railing' if boulder else 'the boulder')} for the unicorn")
        return False
    from_ = game.tile()
    if not (railing.use_on(boulder)):
        return False

    # Why: the script keeps the railing, so the oracle is its `p_telejump(coord - 25x)`, with the threshold past anything the op-click's walk could cover.
    def _fn8():
        now = game.tile()
        return now is not None and from_ is not None and abs(now.x - from_.x) >= 20
    _result7 = yield from drive_until(_fn8, [], log, 15000)
    return _result7


def take_unicorn_horn(log):
    """All that is left of the unicorn is the horn the blood well wants."""
    if held_id(UP_ITEM.UNICORN_HORN.id) > 0:
        return True
    _w9 = yield from walk_to(UP_TILE.UNICORN_CAGE, 3, log)
    if not (_w9):
        return False
    yield from settle_scene()
    cage = loc_by_id(UP_LOC.UNICORN_CAGE, None, 8)
    op = ((cage.actions() if cage is not None else None) or [None])[0]
    if not cage or not op or not (cage.interact(op)):
        log('no crushed unicorn cage to search')
        return False
    _result10 = yield from drive_until(lambda: held_id(UP_ITEM.UNICORN_HORN.id) > 0, [], log, 12000)
    return _result10


PALADINS = [
    Record({'npc': UP_NPC.PALADIN_JERRO, 'badge': UP_ITEM.BADGE_JERRO}),
    Record({'npc': UP_NPC.PALADIN_CARL, 'badge': UP_ITEM.BADGE_CARL}),
    Record({'npc': UP_NPC.PALADIN_HARRY, 'badge': UP_ITEM.BADGE_HARRY}),
]


def badges_held(snap):
    return count_held(snap, UP_BADGES)


# Why: the 3 paladins only turn hostile once the main cavern has been entered, so before that they're killed one at a time from a standing start.
# Why: the well eats the crests and the journal never says so, so a snapshot can't tell "not killed yet" from "already fed". Every irreversible part is one step, ending on the one thing the journal can see: standing on the level-1 platform past the temple doors.
def cross_the_temple(log):
    """Kill paladins, feed the well and pass the doors, whatever of that is still outstanding."""

    def crests():
        return len([badge for badge in UP_BADGES if held_id(badge.id) > 0])

    # Why: a paladin respawns and "whichever is alive" always picks the nearest, so the same one would die every time and its crest feed a bit already set. Each is killed once per crossing, by id.
    killed = set()
    for round in range(4):
        _v11 = (game.tile().level if game.tile() is not None else None)
        if ((_v11 if _v11 is not None else 0)) == 1:
            return True
        # Why: all 3 crests before one trip to the well; feeding each as it drops costs a 50-odd tile walk each way per crest.
        while True:
            _c12 = crests() < 3
            if _c12:
                _w13 = yield from kill_paladin(log, killed)
                _c12 = (_w13)
            if not (_c12):
                break
            log(f'crests in hand: {crests()}')
        if crests() > 0 or held_id(UP_ITEM.UNICORN_HORN.id) > 0:
            yield from feed_blood_well(log)
        _w14 = yield from enter_main_cavern(log)
        if _w14:
            return True
    log('the temple doors will not open and there is nothing left to feed the well')
    _v15 = (game.tile().level if game.tile() is not None else None)
    return ((_v15 if _v15 is not None else 0)) == 1


def _npc_is(id):
    return lambda npc: npc.id == id


def kill_paladin(log, killed=None):
    """Kill a paladin this crossing has not killed yet and take the crest it drops."""
    if killed is None:
        killed = set()
    _w16 = yield from walk_to(UP_TILE.PALADINS, 4, log)
    if not (_w16):
        return False
    yield from settle_scene()
    # Why: which crest is owed can't be read once the well has eaten them, so the target is picked by who hasn't been killed yet.
    target = npcs.query().where(lambda npc: any([p.npc == npc.id for p in PALADINS]) and not (npc.id in killed)).action('Attack').within(14).nearest()
    if not target:
        log('no paladin left on the shelf that this crossing has not already killed')
        return False
    killed.add(target.id)
    _v17 = ([p for p in PALADINS if p.npc == target.id] or [None])[0]
    owed = (_v17 if _v17 is not None else PALADINS[0])
    npc_id = owed.npc
    # Why: `ai_queue3` drops the crest on the paladin's tile, so waiting for it in the pack waits forever; the kill and the pickup are separate.
    _w18 = yield from fight_until_gone(lambda: npcs.query().where(_npc_is(npc_id)).within(14).nearest(), log)
    if not (_w18):
        log(f'paladin {owed.npc} outlasted the fight')
        return False
    taken = yield from take_drop(owed.badge.id, log)
    if not taken:
        log(f'paladin {owed.npc} died but no coat of arms came to the pack')
        # Why: he owes one still, and marking him killed would spend the crossing's rounds on the 2 who've paid.
        killed.remove(owed.npc)
    return taken


def feed_blood_well(log):
    """The blood well opens the temple doors once it has all 3 crests and the horn."""
    _w20 = yield from walk_to(UP_TILE.BLOODWELL, 3, log)
    if not (_w20):
        return False
    yield from settle_scene()
    fed = 0
    for item in list(UP_BADGES) + [UP_ITEM.UNICORN_HORN]:
        if held_id(item.id) == 0:
            continue
        well = loc_by_id(UP_LOC.BLOODWELL, None, 8)
        held = ([inv for inv in inventory.items() if inv.id == item.id] or [None])[0]
        if not well or not held:
            break
        if not (held.use_on(well)):
            break
        _w21 = yield from drive_until(lambda: held_id(item.id) == 0, [], log, 15000)
        if not (_w21):
            log(f'the blood well would not take {item.name}')
            break
        fed += 1
    log(f'fed {fed} item(s) to the blood well')
    return fed > 0


def enter_main_cavern(log):
    """Through the double doors into the main cavern."""
    _w22 = yield from walk_to(UP_TILE.TEMPLE_DOOR, 3, log)
    if not (_w22):
        return False
    yield from settle_scene()
    _v23 = loc_by_id(UP_LOC.TEMPLE_DOOR_L, None, 8)
    door = (_v23 if _v23 is not None else loc_by_id(UP_LOC.TEMPLE_DOOR_R, None, 8))
    op = ((door.actions() if door is not None else None) or [None])[0]
    if not door or not op or not (door.interact(op)):
        log('no temple double door at the west end of the shelf')
        return False
    _result24 = yield from drive_until(lambda: (((game.tile().level if game.tile() is not None else None) if (game.tile().level if game.tile() is not None else None) is not None else 0)) == 1, [], log, 15000)
    return _result24

