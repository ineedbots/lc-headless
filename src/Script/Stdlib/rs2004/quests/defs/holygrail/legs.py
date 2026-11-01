"""Ported from rs2b0t's src/bot/api/ai/quests/defs/holygrail/legs.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import chat_dialog, modals
from rs2004.entities import ground_items, locs, npcs
from rs2004.execution import event_signal
from rs2004.game import game, skills
from rs2004.items import equipment, inventory
from rs2004.quests.defs.holygrail.areas import FISHERMAN, FISHER_KING, GRAIL_TILE, ITEM, MERLIN, MERLIN_ID, SIR_PERCIVAL, TITAN_ID, WHISTLE_DOOR_ID, east_of_titan, in_blighted_realm, in_castle_upstairs, in_fisher_realm
from rs2004.quests.defs.holygrail.armour import unwearable
from rs2004.quests.exec.primitives import drive_dialog, talk_through
from rs2004.tabs import prayer
from rs2004.traversal import traversal

__all__ = ['merlin_leg', 'unequip_all', 'wear_armour', 'draynor_whistles', 'whistle_in', 'whistle_out', 'PROTECT_LEVEL', 'should_protect', 'realm_leg', 'free_percival', 'take_grail']

# Why: the castle floor plan interleaves with the ground outside, so remembering the bell landing is the cheap way to know which side of the wall we're on.
inside_castle = False


def walk_to(dest, radius, log):
    here = game.tile()
    if here and here.level == dest.level and dest.distance_to(here) <= radius:
        return True
    result = yield from traversal.walk_resilient(dest, radius=radius, attempts=4, timeout_ms=180000, log=log)
    return result


def chebyshev(a, b):
    return (max(abs(a.x - b.x), abs(a.z - b.z)) if a.level == b.level else float('inf'))


def drain():
    """Drain a mesbox or a one-sided chat without answering an option."""
    for i in range(20):
        if not ((chat_dialog.is_open() or chat_dialog.can_continue())):
            break
        if chat_dialog.can_continue():
            yield from chat_dialog.continue_()
            yield from execution.delay_ticks(1)
            continue
        if len(chat_dialog.options()) > 0:
            return
        yield from execution.delay_ticks(1)
    yield from modals.close_if_open()


def climb_at(stand, op, log):
    _w3 = yield from walk_to(stand, 1, log)
    if not (_w3):
        return False
    stair = locs.query().name('Staircase').action(op).within(5).nearest()
    if not stair:
        log(f'no Staircase offering \'{op}\' near ({stand.x},{stand.z})')
        return False
    here = game.tile()
    before = here.level if here is not None else stand.level
    if not (stair.interact(op)):
        return False

    def level_changed():
        now = game.tile()
        return now is not None and now.level != before

    result = yield from execution.delay_until(level_changed, 8000)
    return result


# Why: `merlin2` and the `merlin` that Merlin's Crystal frees both render as "Merlin", and only the workshop one carries the Grail dialogue.
def merlin_leg(log):
    """Open the workshop door, which spawns Merlin, and take his advice."""
    _w6 = yield from walk_to(GRAIL_TILE.MERLIN_WORKSHOP, 2, log)
    if not (_w6):
        return False
    merlin = npcs.query().where(lambda n: n.id == MERLIN_ID).action('Talk-to').within(8).nearest()
    if not merlin:
        log('no Merlin in the workshop — the door spawns him, so open it again')
        door = locs.query().name('Door').action('Open').within(6).nearest()
        if door:
            door.interact('Open')
            yield from execution.delay_ticks(3)
        return False
    if not (merlin.interact('Talk-to')):
        return False
    _w7 = yield from execution.delay_until(lambda: chat_dialog.is_open() or chat_dialog.can_continue(), 8000)
    if not (_w7):
        return False
    _result8 = yield from drive_dialog(MERLIN.prefer, log)
    return _result8


def unequip_all(log):
    """Strip every worn piece so the Entrana monk's search passes."""
    for item in equipment.items():
        _c9 = item.name
        if _c9:
            _w10 = yield from equipment.unequip(item.name)
            _c9 = not (_w10)
        if _c9:
            log(f'could not remove {item.name}')
            return False
    return len(equipment.items()) == 0


def wear_armour(names, log):
    """Wear what the armour planner picked, remembering anything the account may not hold."""
    for name in names:
        if equipment.contains(name):
            continue
        _w11 = yield from equipment.equip(name)
        if not (_w11):
            log(f'cannot wear {name} — level or quest requirement; leaving it behind')
            unwearable.add(name.lower())
        yield from execution.delay_ticks(1)
    return True


# Why: the door checks the napkin and the whistle count itself, so opening it while carrying the cloth is all there is to it.
# Why: the pair despawns after 100 ticks, so both are taken inside one step.
def draynor_whistles(want, log):
    """Open Draynor Manor's top-floor door and pick up the whistles it drops."""
    if inventory.count(ITEM.WHISTLE) >= want:
        return True
    if not inventory.contains(ITEM.NAPKIN):
        log('no Holy table napkin in the pack — the whistles will not appear')
        return False
    _w12 = yield from walk_to(GRAIL_TILE.WHISTLE_STAND, 0, log)
    if not (_w12):
        return False
    for _attempt in range(3):
        if not (inventory.count(ITEM.WHISTLE) < want):
            break
        door = locs.query().where(lambda l: l.id == WHISTLE_DOOR_ID).action('Open').within(6).nearest()
        if door:
            door.interact('Open')
            yield from execution.delay_ticks(2)
        for _take in range(4):
            if not (inventory.count(ITEM.WHISTLE) < want):
                break
            drop = ground_items.query().name(ITEM.WHISTLE).within(8).nearest()
            if not drop:
                break
            before = inventory.count(ITEM.WHISTLE)
            if not (drop.interact('Take')):
                break
            yield from execution.delay_until(lambda: inventory.count(ITEM.WHISTLE) > before, 6000)
    got = inventory.count(ITEM.WHISTLE)
    if got < want:
        log(f'Draynor Manor gave {got} of {want} Magic whistles')
    return got >= want


def blow(log):
    whistle = inventory.first(ITEM.WHISTLE)
    if not whistle:
        log('no Magic whistle in the pack')
        return False
    before = game.tile()
    if not (whistle.interact('Blow')):
        return False

    def _fn13():
        now = game.tile()
        return now is not None and before is not None and (now.x != before.x or now.z != before.z)
    moved = yield from execution.delay_until(_fn13, 10000)
    yield from drain()
    return moved


def whistle_in(log):
    """Blow the whistle on Karamja's six heads to cross into the Realm of the Fisher King."""
    _w14 = yield from walk_to(GRAIL_TILE.SIX_HEADS, 1, log)
    if not (_w14):
        return False
    _w15 = yield from blow(log)
    if not (_w15):
        return False
    return in_fisher_realm(game.tile())


def whistle_out(log):
    """Blow the whistle anywhere in the realm to land back on Karamja."""
    global inside_castle
    _w16 = yield from blow(log)
    if not (_w16):
        return False
    if in_fisher_realm(game.tile()):
        return False
    inside_castle = False
    return True


TITAN_GUARD_TICKS = 900
EAT_AT_MISSING = 15
PROTECT_MELEE = 'protect from melee'
PROTECT_LEVEL = 43


def hungry():
    max_ = skills.level('hitpoints')
    return max_ > 0 and skills.effective('hitpoints') <= max_ - EAT_AT_MISSING


# Why: the titan attacks in melee and nothing else, so Protect from Melee zeroes the fight for as long as the points last.
def should_protect(prayer_level, points, up):
    """True when melee protection is worth the tick's one action."""
    return prayer_level >= PROTECT_LEVEL and points > 0 and not up


# Why: the titan full-heals and drops the stage to 7 for anyone who kills him without Excalibur worn, so the check refuses.
# Why: the win is a p_teleport past him, so leaving the pocket is the only proof the fight was the winning one.
def fight_titan(log):
    """Kill the Black Knight Titan wearing Excalibur; the win teleports us across his crossing."""
    if not equipment.contains(ITEM.EXCALIBUR):
        log('refusing to fight the titan without Excalibur wielded — an unarmed kill heals him and sets the quest back')
        return False
    _w17 = yield from walk_to(GRAIL_TILE.TITAN_STAND, 0, log)
    if not (_w17):
        return False
    if skills.level('prayer') < PROTECT_LEVEL:
        log(f'prayer below {PROTECT_LEVEL} — the titan will land hits this fight')
    game.set_auto_retaliate(True)
    game.set_combat_style('strength')
    try:
        won = yield from _titan_rounds(log)
    except Exception as e:
        yield from _drop_titan_prayer()
        raise e
    yield from _drop_titan_prayer()
    return won


def _drop_titan_prayer():
    # Why: the win teleports out of his reach but a yield leaves him swinging, so dropping the prayer there hands back the hits it was bought to stop.
    if not game.in_combat() and prayer.active(PROTECT_MELEE):
        yield from prayer.set(PROTECT_MELEE, False)


def _titan_rounds(log):
    last_tick = -1
    reported = -1
    swings = 0
    attacking = -1
    for i in range(TITAN_GUARD_TICKS):
        if event_signal.pending():
            log('titan: yielding to a runtime event')
            return False
        if not east_of_titan(game.tile()):
            log(f'titan: down after {swings} attacks — teleported past his crossing')
            yield from drain()
            return True
        now = game.tick()
        if now == last_tick:
            yield from execution.delay_ticks(1)
            continue
        last_tick = now
        if chat_dialog.is_open() or chat_dialog.can_continue():
            yield from drain()
            continue
        # Why: the server takes 1 op a tick and drops the rest, so the order is pray, eat, swing; a re-arm skipped for food never comes back while the hits land.
        if should_protect(skills.level('prayer'), prayer.points(), prayer.active(PROTECT_MELEE)):
            yield from prayer.set(PROTECT_MELEE, True)
            continue
        if hungry():
            yield from sustain.run()
            continue
        titan = npcs.query().where(lambda n: n.id == TITAN_ID).action('Attack').nearest()
        if not titan:
            yield from execution.delay_ticks(1)
            continue
        if now - reported >= 40:
            reported = now
            log(f"titan: hp={skills.effective('hitpoints')}/{skills.level('hitpoints')}" + f' prayer={prayer.points()} attacks={swings}')
        # Melee keeps swinging on its own; re-clicking spends the tick's one action on re-targeting.
        if titan.index == attacking and game.facing() == ('npc', titan.index):
            yield from execution.delay_ticks(1)
            continue
        if titan.interact('Attack'):
            attacking = titan.index
            swings += 1
        yield from execution.delay_ticks(1)
    log(f'titan: gave up after {TITAN_GUARD_TICKS} ticks ({swings} attacks)')
    return False


RING_ATTEMPTS = 12


def ring_bell(log):
    """Ring the Grail bell beside a maiden; the answer is a teleport into the castle."""
    global inside_castle
    _w18 = yield from walk_to(GRAIL_TILE.RING_STAND, 1, log)
    if not (_w18):
        # Why: the ring stand is outside the castle wall, so unreachable means we're already in.
        if traversal.last_outcome == 'unreachable':
            log('bell: the ring stand is unreachable — already inside the castle')
            inside_castle = True
            return True
        return False
    for i in range(RING_ATTEMPTS):
        here = game.tile()
        maiden = npcs.query().name('Grail Maiden').nearest()
        if not here or not maiden or chebyshev(here, maiden.tile()) > 4:
            # The maidens wander inside the castle; one drifts back into earshot.
            yield from execution.delay_ticks(2)
            continue
        bell = inventory.first(ITEM.BELL)
        if not bell:
            log('no Grail bell in the pack')
            return False
        if not (bell.interact('Ring')):
            return False

        def _fn19():
            now = game.tile()
            return now is not None and GRAIL_TILE.CASTLE_LANDING.distance_to(now) <= 2 and now.level == 0
        landed = yield from execution.delay_until(_fn19, 8000)
        yield from drain()
        if landed:
            log('bell: inside the Grail castle')
            inside_castle = True
            return True
    log('bell: no Grail Maiden came within four tiles of the ring stand')
    return False


def take_bell(log):
    if inventory.contains(ITEM.BELL):
        return True
    if ground_items.query().name(ITEM.BELL).within(12).nearest() is None:
        _w20 = yield from walk_to(GRAIL_TILE.BELL_SPAWN, 1, log)
        if not (_w20):
            return False
        yield from execution.delay_ticks(2)
    drop = ground_items.query().name(ITEM.BELL).within(12).nearest()
    if not drop:
        log('no Grail bell on the ground — the Fisherman spawns it for 500 ticks, so ask him again')
        return False
    if not (drop.interact('Take')):
        return False
    _result21 = yield from execution.delay_until(lambda: inventory.contains(ITEM.BELL), 8000)
    return _result21


# Why: one step; every stage inside the realm is read off the tile and the scene, so an interrupted run re-enters where it stopped.
def realm_leg(log):
    """Everything inside the blighted realm: the titan, the bell, and the Fisher King."""
    global inside_castle
    here = game.tile()
    if not in_blighted_realm(here):
        inside_castle = False
        log('realm_leg: not in the Realm of the Fisher King')
        return False
    if east_of_titan(here):
        _result22 = yield from fight_titan(log)
        return _result22
    if in_castle_upstairs(here):
        inside_castle = True
        _w23 = yield from walk_to(GRAIL_TILE.FISHER_KING_DOOR, 1, log)
        if not (_w23):
            return False
        # Reach opens the diagonal door in front of the hall when the server refuses.
        _result24 = yield from talk_through(FISHER_KING.npc, FISHER_KING.prefer, log)
        return _result24
    if inside_castle:
        _result25 = yield from climb_at(GRAIL_TILE.CASTLE_STAIR, 'Climb-up', log)
        return _result25
    if not inventory.contains(ITEM.BELL) and ground_items.query().name(ITEM.BELL).within(16).nearest() is None:
        _w26 = yield from walk_to(FISHERMAN.anchor, 1, log)
        if not (_w26):
            return False
        _w27 = yield from talk_through(FISHERMAN.npc, FISHERMAN.prefer, log)
        if not (_w27):
            return False
    _w28 = yield from take_bell(log)
    if not (_w28):
        return False
    _result29 = yield from ring_bell(log)
    return _result29


# Why: `oploc2,percy_sacks` gates on the stage alone, so King Arthur's golden feather is a hint the bot does not need.
def free_percival(log):
    """Open the Goblin Village sacks and hand the freed Sir Percival a whistle."""
    if not inventory.contains(ITEM.WHISTLE):
        log('no Magic whistle to give Sir Percival')
        return False
    _w30 = yield from walk_to(GRAIL_TILE.SACKS_STAND, 2, log)
    if not (_w30):
        return False
    if npcs.query().name('Sir Percival').action('Talk-to').within(8).nearest():
        _result31 = yield from talk_through(SIR_PERCIVAL.npc, SIR_PERCIVAL.prefer, log)
        return _result31
    sacks = locs.query().name('Sacks').action('Open').within(6).nearest()
    if not sacks:
        log('no Sacks to Open at the Goblin Village')
        return False
    if not (sacks.interact('Open')):
        return False
    _w32 = yield from execution.delay_until(lambda: chat_dialog.is_open() or chat_dialog.can_continue(), 8000)
    if not (_w32):
        return False
    _result33 = yield from drive_dialog(SIR_PERCIVAL.prefer, log)
    return _result33


def take_grail(log):
    """Climb the renewed castle's tower and lift the Grail off the round table."""
    if inventory.contains(ITEM.GRAIL):
        return True
    # Why: radius 0, since only the cardinal neighbour south of the round table counts as adjacent.
    _w34 = yield from walk_to(GRAIL_TILE.GRAIL_STAND, 0, log)
    if not (_w34):
        return False
    grail = ground_items.query().name(ITEM.GRAIL).within(4).nearest()
    if not grail:
        log('no Holy grail on the table — LIVE-VERIFY the tower route')
        return False
    if not (grail.interact('Take')):
        return False
    took = yield from execution.delay_until(lambda: inventory.contains(ITEM.GRAIL), 8000)
    yield from drain()
    return took
