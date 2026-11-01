"""Ported from rs2b0t's src/bot/api/ai/quests/defs/ikov/fight.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import chat_dialog, modals
from rs2004.entities import ground_items, locs, npcs
from rs2004.execution import event_signal
from rs2004.game import direct_navigator, game, skills
from rs2004.items import equipment, inventory
from rs2004.quests.defs.ikov.areas import IKOV_FOODS, IKOV_LOC, IKOV_NAME, IKOV_NPC, IKOV_TILE, LAVA_BRIDGE_ZONE
from rs2004.quests.defs.ikov.dungeon import escape_pocket, pull_trap_lever, wear_fear_pendant
from rs2004.traversal import traversal

__all__ = ['arrow_action', 'fight_fire_warrior', 'kill_lucien']

WARRIOR_GUARD = 900
RAPID_MODE = 1
NEVER_APPEARED = 30
LUCIEN_GUARD = 400
EAT_AT_MISSING = 18
ARROW_RADIUS = 12
WALK_MS = 300000
REPORT_TICKS = 40


def hungry():
    max_ = skills.level('hitpoints')
    return max_ > 0 and skills.effective('hitpoints') <= max_ - EAT_AT_MISSING


# Why: `Sustain.run()` does not report whether it ate, so an empty pack cannot drive the loop condition.
def can_eat():
    return any([inventory.contains(food) for food in IKOV_FOODS])


def ice_arrows_held():
    """Every ice-arrow stack size renders under one display name, so the pack is counted by name."""
    return inventory.count(IKOV_NAME.ICE_ARROWS) + ((worn_arrows() if equipment.contains(IKOV_NAME.ICE_ARROWS) else 0))


def worn_arrows():
    """The quiver alone, which is all a bow can shoot."""
    return sum([i.count for i in [i for i in equipment.items() if ((i.name if i.name is not None else '')).lower() == IKOV_NAME.ICE_ARROWS.lower()]])


# Why: Recovered arrows land in inventory, but only equipped arrows can fire; track total and equipped counts separately.
def arrow_action(quiver, pack, sweepable):
    """Decide between shooting, nocking, sweeping and giving up. Pure, so the empty-quiver case is testable."""
    if quiver > 0:
        return 'shoot'
    if pack > 0:
        return 'nock'
    return ('sweep' if sweepable else 'spent')


def nock_arrows():
    """Move a pack stack into the quiver; true once there is something nocked to shoot."""
    if worn_arrows() > 0:
        return True
    if inventory.count(IKOV_NAME.ICE_ARROWS) == 0:
        return False
    _result1 = yield from equipment.equip(IKOV_NAME.ICE_ARROWS)
    return _result1


def arm_for_the_warrior(log):
    """The Fire Warrior refuses anything but ranged, and only with ice arrows in the quiver."""
    _c2 = not equipment.contains(IKOV_NAME.YEW_SHORTBOW)
    if _c2:
        _w3 = yield from equipment.equip(IKOV_NAME.YEW_SHORTBOW)
        _c2 = not (_w3)
    if _c2:
        log('ikov: no yew shortbow to wield')
        return False
    _w4 = yield from nock_arrows()
    if not (_w4):
        log('ikov: no ice arrows to nock')
        return False
    # Why: the warrior refuses any `%damagetype` but ranged, and rapid is the fastest of the bow's 3.
    game.set_combat_mode(RAPID_MODE)
    return True


def pick_up_arrows(log):
    for sweep in range(12):
        drop = ground_items.query().where(lambda g: ((g.name if g.name is not None else '')).lower() == IKOV_NAME.ICE_ARROWS.lower()).action('Take').within(ARROW_RADIUS).nearest()
        if not drop:
            return
        where = drop.tile()
        if drop.distance() > 1:
            yield from direct_navigator.walk_to(where, 0, 6000)
        still = ground_items.query().where(lambda g: ((g.name if g.name is not None else '')).lower() == IKOV_NAME.ICE_ARROWS.lower()).action('Take').within(ARROW_RADIUS).nearest()
        if not still or not (still.interact('Take')):
            return
        yield from execution.delay_ticks(2)
    log(f'ikov: recovered arrows, {ice_arrows_held()} held')


# Why: an empty bow answers every later Attack click with "There is no ammo left in your quiver", which the hobgoblin farm 2 legs on pays for.
def stow_spent_bow(log):
    """Take the bow off once the quiver behind it is empty."""
    if not equipment.contains(IKOV_NAME.YEW_SHORTBOW) or ice_arrows_held() > 0:
        return
    log('ikov: the quiver is spent — stowing the yew shortbow')
    yield from equipment.unequip(IKOV_NAME.YEW_SHORTBOW)


def walk_to_fire_door(log):
    return traversal.walk_resilient(IKOV_TILE.FIRE_DOOR_SOUTH, radius=2, attempts=3, timeout_ms=WALK_MS, avoid_zones=[LAVA_BRIDGE_ZONE], log=log)


def warrior():
    return npcs.query().where(lambda n: n.id == IKOV_NPC.FIRE_WARRIOR).action('Attack').within(15).nearest()


# Why: opening the door below the stage summons the warrior on the near side and blasts you back a tile.
def summon_warrior(log):
    if warrior():
        return True
    door = locs.query().where(lambda l: l.id == IKOV_LOC.FIREWARRIOR_DOOR).within(6).nearest()
    if not door:
        log('ikov: no fire warrior door in reach')
        return False
    log('ikov: opening the fire warrior door')
    if not (door.interact('Open')):
        log('ikov: the fire warrior door refused the click')
        return False
    came = yield from execution.delay_until(lambda: warrior() is not None, 20000)
    # Why: "no warrior" reads the same whether the cutscene never fired or the scene is being filtered, and the two have different fixes.
    log(('ikov: the Fire Warrior is up' if came else f'ikov: no Fire Warrior after the door — scene holds {tally_nearby()}'))
    return came


def tally_nearby():
    names = [f"{(n.name if n.name is not None else '?')}#{n.id}" for n in npcs.query().within(15).results()]
    return ('nothing' if len(names) == 0 else ', '.join(list(set(names))))


# Why: a chat modal with no continue button never drains, and a fight loop that keeps yielding to it spins out the guard in silence.
def drain_dialogue(log=None):
    """Click through what the last op raised; close it outright if it will not drain."""
    for i in range(20):
        if chat_dialog.can_continue():
            yield from chat_dialog.continue_()
            yield from execution.delay_ticks(1)
            continue
        if not chat_dialog.is_open():
            return
        yield from execution.delay_ticks(1)
    if chat_dialog.is_open():
        if log is not None:
            log('ikov: a chat modal would not drain — closing it and fighting on')
        _core.close_interfaces()
        yield from execution.delay_ticks(2)


def fight_fire_warrior(log):
    """Shoot the Fire Warrior down with ice arrows and sweep the spent ones up."""
    _w5 = yield from escape_pocket(log)
    if not (_w5):
        return False
    _w6 = yield from wear_fear_pendant(log)
    if not (_w6):
        return False
    _w7 = yield from arm_for_the_warrior(log)
    if not (_w7):
        return False
    # Why: the journal renders stages 20 and 30 alike, so a run interrupted between the search and the pull reads as pulled and finds the door shut.
    _w8 = yield from walk_to_fire_door(log)
    if not (_w8):
        log('ikov: the trap-lever door is shut — pulling the lever again')
        _w10 = yield from pull_trap_lever(log)
        _c9 = not (_w10)
        if not _c9:
            _w11 = yield from walk_to_fire_door(log)
            _c9 = not (_w11)
        if _c9:
            return False
    _w12 = yield from summon_warrior(log)
    if not (_w12):
        return False
    game.set_auto_retaliate(True)
    attacking = -1
    missing = 0
    swings = 0
    refused = 0
    # Why: a sweep that recovers nothing mustn't be retried every tick, so the second empty quiver in a row ends the fight.
    swept = False
    # Why: auto-retaliate fights the warrior whether or not our Attack clicks land, so "did a shot go out" can't tell whether the fight happened.
    engaged = False
    last_tick = -1
    reported = -1
    for i in range(WARRIOR_GUARD):
        if event_signal.pending():
            log('ikov: yielding the Fire Warrior to a random event')
            return False
        now = game.tick()
        if now == last_tick:
            yield from execution.delay_ticks(1)
            continue
        last_tick = now
        engaged = engaged or game.in_combat()
        # Why: every branch below can yield the tick, so a report only on the shooting one leaves a stalled fight silent.
        if now - reported >= REPORT_TICKS:
            reported = now
            target = warrior()
            where = f'{target.tile().x},{target.tile().z}' if target else 'none'
            chat = 'open' if chat_dialog.is_open() else 'closed'
            log(f"ikov: warrior fight hp={skills.effective('hitpoints')}/{skills.level('hitpoints')} arrows={ice_arrows_held()} shots={swings} refused={refused} engaged={engaged} food={can_eat()} target={where} chat={chat}")
        if chat_dialog.is_open() or chat_dialog.can_continue():
            yield from drain_dialogue(log)
            continue
        if hungry() and can_eat():
            yield from sustain.run()
            continue
        npc = warrior()
        if not npc:
            attacking = -1
            missing += 1
            if engaged and missing >= 4:
                log(f'ikov: the Fire Warrior is down after {swings} shots')
                yield from drain_dialogue()
                yield from pick_up_arrows(log)
                # Why: the sweep leaves the recovered arrows in the pack, and the next leg reads the quiver, so what was picked up is nocked before the bow comes off.
                yield from nock_arrows()
                yield from stow_spent_bow(log)
                return True
            # Why: spinning out the full guard on an empty scene costs 3 minutes and says nothing; the tally names what is standing there.
            if not engaged and missing >= NEVER_APPEARED:
                log(f'ikov: the Fire Warrior never joined the fight — scene holds {tally_nearby()}')
                return False
            yield from execution.delay_ticks(1)
            continue
        missing = 0
        # Why: 80% of shots land on the floor, so an empty quiver mid-fight is a sweep; only the quiver counts here, since `iceArrowsHeld` adds the pack and a swept pack reads as armed.
        next_ = arrow_action(worn_arrows(), inventory.count(IKOV_NAME.ICE_ARROWS), not swept)
        if next_ != 'shoot':
            if next_ == 'spent':
                log('ikov: nothing left to shoot the Fire Warrior with')
                return False
            if next_ == 'sweep':
                log('ikov: the quiver is empty — sweeping the spent arrows')
                swept = True
                yield from pick_up_arrows(log)
            _w13 = yield from nock_arrows()
            if not (_w13):
                log('ikov: nothing left to shoot the Fire Warrior with')
                return False
            log(f'ikov: nocked {worn_arrows()} ice arrows')
            swept = False
            attacking = -1
            continue
        if npc.index == attacking and game.in_combat():
            yield from execution.delay_ticks(1)
            continue
        if npc.interact('Attack'):
            attacking = npc.index
            swings += 1
            engaged = True
        else:
            _v15 = refused
            refused += 1
            if _v15 == 0:
                at = npc.tile()
                log(f'ikov: the Fire Warrior refused an Attack click at ({at.x},{at.z}), {npc.distance()} away')
        yield from execution.delay_ticks(1)
    log(f'ikov: the Fire Warrior outlived {WARRIOR_GUARD} ticks')
    return False


def lucien():
    return npcs.query().where(lambda n: n.id == IKOV_NPC.LUCIEN_HOSTILE).action('Attack').nearest()


def kill_lucien(log):
    """Kill Lucien for the Armadyl ending. He is level 14 and the pendant is what makes him attackable."""
    if not equipment.contains(IKOV_NAME.PENDANT_ARMADYL):
        _w16 = yield from equipment.equip(IKOV_NAME.PENDANT_ARMADYL)
        if not (_w16):
            log('ikov: no Armadyl pendant to wear — Lucien cannot be attacked without it')
            return False
    yield from stow_spent_bow(log)
    _w17 = yield from traversal.walk_resilient(IKOV_TILE.LUCIEN_HUT, radius=4, attempts=3, timeout_ms=600000, log=log)
    if not (_w17):
        return False
    game.set_auto_retaliate(True)
    attacking = -1
    missing = 0
    swings = 0
    engaged = False
    last_tick = -1
    for i in range(LUCIEN_GUARD):
        if event_signal.pending():
            return False
        now = game.tick()
        if now == last_tick:
            yield from execution.delay_ticks(1)
            continue
        last_tick = now
        engaged = engaged or game.in_combat()
        if chat_dialog.is_open() or chat_dialog.can_continue():
            yield from drain_dialogue(log)
            continue
        if hungry() and can_eat():
            yield from sustain.run()
            continue
        npc = lucien()
        if not npc:
            attacking = -1
            missing += 1
            if engaged and missing >= 5:
                log(f'ikov: Lucien is banished after {swings} attacks')
                yield from drain_dialogue()
                # Why: the completion scroll is a main modal, and one left up stops the retreat to a bank dead.
                yield from modals.close_if_open()
                return True
            yield from execution.delay_ticks(1)
            continue
        missing = 0
        if npc.index == attacking and game.in_combat():
            yield from execution.delay_ticks(1)
            continue
        if npc.interact('Attack'):
            attacking = npc.index
            swings += 1
            engaged = True
        yield from execution.delay_ticks(1)
    log(f'ikov: Lucien outlived {LUCIEN_GUARD} ticks')
    return False
