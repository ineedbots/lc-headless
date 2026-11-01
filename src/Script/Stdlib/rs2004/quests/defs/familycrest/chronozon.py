"""Ported from rs2b0t's src/bot/api/ai/quests/defs/familycrest/chronozon.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.catalogs.tasks import sustain
from rs2004.entities import ground_items, npcs
from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.messages import game_messages
from rs2004.quests.defs.familycrest.areas import ANTIPOISON_IDS, FC_ID, FC_ITEM, FC_NPC, in_chronozon_lair
from rs2004.quests.exec.prompts import held_id, settle_scene
from rs2004.traversal import traversal

__all__ = ['SAFESPOT', 'BLASTS', 'fight_chronozon', 'combine_crest']

WEAKENS = 'chronozon weakens'
UNDER_ATTACK = 'already under attack'
CLEAR_ATTACKER_MS = 30000
POISONED = 'you have been poisoned'
# Why: the south end of the chamber, 2 tiles clear of the demon's furthest-south 3x3 placement, on an open x=3089 column with line of sight north.
# Why: the east alcove at (3092,9940) is inside the poison spiders' roam (spawn z 9943-9945, `wanderrange=10`, `maxrange=12`); here the nearest spawn is 11 to 13 away.
# Why: derived by `tools/nav/chronozon-safespot.ts`; the west passage is a sealed island and the corridor north of the gates is behind a gate that blocks the cast (3 live casts never landed).
SAFESPOT = Tile(3089, 9932, 0)
SAFESPOT_PROBE_CASTS = 3
# Why: `~chronozon_spell` runs inside `pvm_spell_success`, so a splash sets nothing; "Chronozon weakens..." is emitted when the bit is set, so each spell is retried until that line appears.
# The 4 spells that unlock the kill, in casting order.
BLASTS = ['Wind blast', 'Water blast', 'Earth blast', 'Fire blast']
# Why: a dose sets `%poison = min(%poison, -5)`, a cure plus a short immunity, so it's drunk on the way out; the poison comes from the gate tiles and threatens the walk home, and the safespot is 11 tiles clear of the spiders.
# Why: `%poison` is `scope=perm` with no transmit, so the tell is the server's "You have been poisoned!" line; the drink is rate-limited so a retried step doesn't drink the potion dry.
IMMUNITY_MS = 80000
last_drink = -IMMUNITY_MS


def drink_antipoison(log):
    global last_drink
    if _core.step_time() - last_drink < IMMUNITY_MS:
        return True
    dose = ([i for i in inventory.items() if (i.id in (ANTIPOISON_IDS))] or [None])[0]
    if not dose:
        return False
    if not (dose.interact('Drink')):
        return False
    last_drink = _core.step_time()
    yield from execution.delay_ticks(2)
    log('drank antipoison — the spiders on the gate tiles poison on contact')
    return True


# Why: hp loss can't tell the demon from poison or the size-1 spiders that follow into the alcove; the reported tile is the middle of a 3x3, so within 2 is melee reach.
def demon_in_reach():
    """Whether the demon's body is touching us."""
    target = chronozon()
    me = game.tile()
    if not target or not me:
        return False
    t = target.tile()
    return t.level == me.level and max(abs(t.x - me.x), abs(t.z - me.z)) <= 2


def on_safespot():
    here = game.tile()
    return here is not None and here.level == 0 and here.x == SAFESPOT.x and here.z == SAFESPOT.z


# Why: a false here means the fight happens in the open, which is the proven path.
def take_safespot(log):
    """Try to stand on the safespot; returns whether we are on it."""
    if on_safespot():
        return True
    ok = yield from traversal.walk_resilient(SAFESPOT, radius=0, attempts=3, timeout_ms=90000, log=log)
    if ok and on_safespot():
        log(f'on the safespot at ({SAFESPOT.x},{SAFESPOT.z}) — no 3x3 placement reaches here, and the spiders do not roam this far south')
        return True
    log('could not take the safespot — fighting in the open')
    return False


def chronozon():
    return npcs.query().where(lambda n: n.id == FC_NPC.CHRONOZON_NPC_ID).within(16).nearest()


# Why: Chronozon respawns 60 ticks after a kill and this fight kills it repeatedly while arming the 4 bits, so "not in the scene" usually means "not back yet".
def walk_to_chronozon(log):
    """Walk to Chronozon's chamber, waiting out a respawn."""
    if in_chronozon_lair(game.tile()) and chronozon():
        return True
    _c1 = not in_chronozon_lair(game.tile())
    if _c1:
        _w2 = yield from traversal.walk_resilient(FC_NPC.CHRONOZON, radius=4, attempts=5, timeout_ms=300000, log=log)
        _c1 = not (_w2)
    if _c1:
        return False
    yield from settle_scene()
    if chronozon():
        return True
    log('Chronozon is not in the scene — waiting for the respawn')
    _result3 = yield from execution.delay_until(lambda: chronozon() is not None, 60000)
    return _result3


# Why: killing it before all 4 blasts land is harmless, `ai_queue3` heals it to full and sets it back on you, so the loop never guards its damage output.
def fight_chronozon(log):
    """Land one of each elemental blast, then finish the demon."""
    try:
        result = yield from run_fight(log)
    except Exception as e:
        game.set_auto_retaliate(True)
        raise e
    game.set_auto_retaliate(True)
    return result


def attacker():
    """Whatever else is hitting us: a follower from the gates, say."""
    return npcs.query().where(lambda n: n.id != FC_NPC.CHRONOZON_NPC_ID and n.targets_me()).within(16).nearest()


# Why: the lair is single-way, so while anything else is hitting us the server refuses every cast at the demon with "I'm already under attack!".
# Why: rs2b0t casts on regardless, and with auto-retaliate off the follower never dies: Chronozon killed a 99-combat account through 8 lobsters on 11 refused casts.
def clear_attacker(log):
    """Kill what stands between us and the demon. True when there was something to kill."""
    pest = attacker()
    if not pest:
        return False
    log(f'killing the {pest.name} that is blocking the casts')
    deadline = _core.step_time() + CLEAR_ATTACKER_MS
    while _core.step_time() < deadline:
        yield from sustain.run()
        pest = attacker()
        if not pest:
            return True
        if game.facing() != ('npc', pest.index):
            pest.interact('Attack')
        yield from execution.delay_ticks(1)
    return True


def _cast_blast(spell, state, log):
    yield from sustain.run()
    cleared = yield from clear_attacker(log)
    if cleared:
        return 'blocked'
    if state.safespot and not on_safespot():
        state.safespot = yield from take_safespot(log)
    target = chronozon()
    if not target:
        return 'gone'
    mark = game_messages.mark()
    if not (game.cast_on_npc(spell, target)):
        return 'nospell'
    yield from execution.delay_until(lambda: game_messages.saw_since(mark, WEAKENS) or game_messages.saw_since(mark, UNDER_ATTACK), 8000)
    if game_messages.saw_since(mark, WEAKENS):
        return 'landed'
    return 'blocked' if game_messages.saw_since(mark, UNDER_ATTACK) else 'missed'


def run_fight(log):
    # Why: auto-retaliate breaks the safespot, swinging back at a gate spider walks the bot into the demon's reach.
    game.set_auto_retaliate(False)
    # Why: `walkToChronozon` closes to within 4 tiles, inside its reach, so the walk targets the safespot; the walker handles the trapdoor and gates.
    state = Record({'safespot': False})
    state.safespot = yield from take_safespot(log)
    _c5 = not state.safespot
    if _c5:
        _w6 = yield from walk_to_chronozon(log)
        _c5 = not (_w6)
    if _c5:
        log('could not reach Chronozon')
        return False
    poison_mark = game_messages.mark()
    for spell in BLASTS:
        landed = False
        for attempt in range(12):
            if not (not landed):
                break
            result = yield from _cast_blast(spell, state, log)
            if result == 'nospell':
                log(f'could not select {spell} — magic level or runes short')
                return False
            if result == 'gone':
                _w8 = yield from walk_to_chronozon(log)
                if not (_w8):
                    return False
                continue
            if result == 'blocked':
                continue
            landed = result == 'landed'
            # Why: casts not landing, or the demon in reach on the safespot, means the gate is in the way or the spot is wrong; the open fight is the proven fallback.
            if state.safespot and attempt + 1 >= SAFESPOT_PROBE_CASTS and not landed:
                log('safespot casts are not landing — fighting in the open instead')
                state.safespot = False
            elif state.safespot and on_safespot() and demon_in_reach():
                log('the demon reaches the safespot after all — fighting in the open instead')
                state.safespot = False
            if not state.safespot and not on_safespot() and not landed:
                # Why: abandoning the spot has to move, since whatever blocked the casts still blocks them from here.
                yield from walk_to_chronozon(log)
        if not landed:
            log(f'{spell} never landed on Chronozon — out of runes?')
            return False
        log(f'{spell} landed')
    log('all four blasts landed — killing Chronozon')
    for attempt in range(60):
        yield from sustain.run()
        yield from clear_attacker(log)
        if held_id(FC_ID.CREST_FROM_CHRONOZON) > 0:
            # Cure on the way out: the walk home is the part poison decides.
            if game_messages.saw_since(poison_mark, POISONED):
                yield from drink_antipoison(log)
            return True
        drop = ground_items.query().name(FC_ITEM.CREST_PART).within(16).nearest()
        if drop:
            # Taking it means leaving the safespot; the demon is dead by now.
            state.safespot = False
            before = held_id(FC_ID.CREST_FROM_CHRONOZON)
            if drop.interact('Take'):
                _w9 = yield from execution.delay_until(lambda: held_id(FC_ID.CREST_FROM_CHRONOZON) > before, 6000)
                if _w9:
                    log("took Johnathon's crest part")
                    if game_messages.saw_since(poison_mark, POISONED):
                        yield from drink_antipoison(log)
                    return True
            continue
        target = chronozon()
        if not target:
            # Dead, or wandered: give the drop a tick to land before re-walking.
            yield from execution.delay_ticks(2)
            if ground_items.query().name(FC_ITEM.CREST_PART).within(12).nearest():
                continue
            _w10 = yield from walk_to_chronozon(log)
            if not (_w10):
                return False
            continue
        # Why: a rune scimitar against defence 173 outlasts the loop, and from the safespot casting is the only option that keeps the distance.
        if state.safespot and not on_safespot():
            state.safespot = yield from take_safespot(log)
        if not (game.cast_on_npc('Fire blast', target)) and not state.safespot:
            if not target.targets_me() and not game.in_combat():
                target.interact('Attack')
        yield from execution.delay_ticks(3)
    return held_id(FC_ID.CREST_FROM_CHRONOZON) > 0


def combine_crest(log):
    """Combine the three fragments. Any pairing runs the same `combine_crest_parts`."""
    if inventory.count_by_id(FC_ID.FAMILY_CREST) > 0:
        return True
    first = ([i for i in inventory.items() if i.id == FC_ID.CREST_FROM_CALEB] or [None])[0]
    second = ([i for i in inventory.items() if i.id == FC_ID.CREST_FROM_AVAN] or [None])[0]
    if not first or not second:
        log('need all three fragments in the pack before they combine')
        return False
    if not (first.use_on(second)):
        return False
    made = yield from execution.delay_until(lambda: inventory.count_by_id(FC_ID.FAMILY_CREST) > 0, 8000)
    if made:
        log('restored the Family Crest')
    return made
