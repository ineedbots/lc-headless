"""Ported from rs2b0t's src/bot/api/ai/quests/exec/fundCoins.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import chat_dialog
from rs2004.entities import npcs
from rs2004.execution import event_signal
from rs2004.game import game, skills
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.traversal import traversal

__all__ = ['VARROCK_FUNDING_MAN', 'AL_KHARID_FUNDING_MAN', 'KEBAB_SELLER', 'AL_KHARID_TOLL', 'AL_KHARID_ENTRY_CASH', 'SAFE_PICKPOCKET_HP', 'in_al_kharid_funding_area', 'east_of_al_kharid_gate', 'fund_quest_coins', 'earn_quest_coins_step']

VARROCK_FUNDING_MAN = Tile(3240, 3405, 0)
AL_KHARID_FUNDING_MAN = Tile(3279, 3188, 0)
KEBAB_SELLER = Tile(3272, 3182, 0)
AL_KHARID_TOLL = 10
AL_KHARID_ENTRY_CASH = AL_KHARID_TOLL + 3
SAFE_PICKPOCKET_HP = 3
FUNDING_MAN_LEASH = 24
FUNDING_STALL_MS = 120000
FUNDING_REGEN_WAIT_MS = 60000
KEBAB = 'Kebab'


def in_al_kharid_funding_area(tile):
    # Town proper around the Man + kebab shop; Shantay Pass (z 3116 to 3124) is excluded.
    return tile is not None and tile.level == 0 and tile.x >= 3260 and tile.x <= 3305 and tile.z >= 3155 and tile.z <= 3210


def funding_man(anchor):
    return npcs.query().name('Man').action('Pickpocket').where(lambda npc: npc.tile().distance_to(anchor) <= FUNDING_MAN_LEASH).nearest()


def reach_funding_man(anchor, log):
    if event_signal.pending():
        return False
    _w1 = yield from traversal.walk_resilient(anchor, radius=6, attempts=4, timeout_ms=180000, log=log)
    if not (_w1):
        return False
    if event_signal.pending():
        return False
    _c2 = funding_man(anchor)
    if not _c2:
        _w3 = yield from execution.delay_until(lambda: funding_man(anchor) is not None, 15000)
        _c2 = (_w3)
    if _c2:
        return True
    log(f'no pickpocketable Man within {FUNDING_MAN_LEASH} tiles of ({anchor.x},{anchor.z})')
    return False


def clear_funding_dialog():
    for pages in range(12):
        if not (chat_dialog.can_continue()):
            break
        if event_signal.pending():
            return False
        yield from chat_dialog.continue_()
        yield from execution.delay_ticks(1)
    return not event_signal.pending()


def pickpocket_funding_man(anchor, log):
    if event_signal.pending():
        return False
    man = funding_man(anchor)
    if not man:
        _w4 = yield from reach_funding_man(anchor, log)
        if not (_w4):
            return False
        man = funding_man(anchor)
    if not man or event_signal.pending():
        return False
    coins_before = inventory.count('Coins')
    xp_before = skills.xp('thieving')
    hp_before = skills.effective('hitpoints')
    if not (man.interact('Pickpocket')):
        yield from execution.delay_ticks(2)
        return True
    resolved = yield from execution.delay_until(lambda: inventory.count('Coins') > coins_before or skills.xp('thieving') > xp_before or skills.effective('hitpoints') < hp_before or chat_dialog.can_continue() or event_signal.pending(), 8000)
    if event_signal.pending():
        return False
    if not resolved:
        log(f'pickpocketing Man at {man.tile()} produced no coin, XP, health, or dialogue change')
        yield from execution.delay_ticks(2)
        return True
    _w5 = yield from clear_funding_dialog()
    if not (_w5):
        return False
    if skills.effective('hitpoints') < hp_before:
        # Failed level-1 Man pickpocket stuns for 8 server ticks.
        yield from execution.delay_ticks(8)
    return True


def buy_kebab(log):
    """Buy one Kebab from the Al Kharid seller (exact "Yes please." dialogue)."""
    if event_signal.pending():
        return False
    _w6 = yield from traversal.walk_resilient(KEBAB_SELLER, radius=2, attempts=3, timeout_ms=60000, log=log)
    if not (_w6):
        return False
    seller = npcs.query().name('Kebab seller').action('Talk-to').within(8).nearest()
    if not seller:
        log(f'no talkable Kebab seller near ({KEBAB_SELLER.x},{KEBAB_SELLER.z})')
        return False
    before = inventory.count(KEBAB)
    if not (seller.interact('Talk-to')):
        return False
    for step in range(40):
        if event_signal.pending():
            return False
        if inventory.count(KEBAB) > before:
            return True
        if chat_dialog.can_continue():
            yield from chat_dialog.continue_()
            yield from execution.delay_ticks(1)
            continue
        options = chat_dialog.options()
        if len(options) > 0:
            yes = ([option for option in options if option.strip().lower() == 'yes please.'] or [None])[0]
            if not yes:
                log(f"Kebab seller offered unexpected options: [{' | '.join(options)}]")
                return False
            _w7 = yield from chat_dialog.choose_option(yes)
            if not (_w7):
                return False
            yield from execution.delay_ticks(1)
            continue
        yield from execution.delay_ticks(1)
    log('Kebab seller did not complete a purchase within 40 dialogue steps')
    return False


def eat_funding_kebab():
    kebab = ([i for i in inventory.items() if (i.name.lower() if i.name is not None else None) == KEBAB.lower()] or [None])[0]
    if not kebab:
        return False
    before = inventory.count(KEBAB)
    if not (kebab.interact('Eat')):
        return False
    _result8 = yield from execution.delay_until(lambda: inventory.count(KEBAB) < before, 5000)
    return _result8


def restore_funding_health(can_buy_kebabs, log):
    while skills.effective('hitpoints') < SAFE_PICKPOCKET_HP:
        if event_signal.pending():
            return False
        yield from sustain.run()
        if event_signal.pending():
            return False
        if skills.effective('hitpoints') >= SAFE_PICKPOCKET_HP:
            continue
        if can_buy_kebabs and inventory.count('Coins') > 0:
            _w10 = yield from buy_kebab(log)
            _c9 = not (_w10)
            if not _c9:
                _w11 = yield from eat_funding_kebab()
                _c9 = not (_w11)
            if _c9:
                return False
            continue
        log(f'waiting up to {FUNDING_REGEN_WAIT_MS / 1000}s for {SAFE_PICKPOCKET_HP} HP before another Man pickpocket')
        _w12 = yield from execution.delay_until(lambda: skills.effective('hitpoints') >= SAFE_PICKPOCKET_HP or event_signal.pending(), FUNDING_REGEN_WAIT_MS)
        if not (_w12):
            log(f'still below {SAFE_PICKPOCKET_HP} HP with no food or Kebab funds — funding paused')
            return False
        if event_signal.pending():
            return False
    return True


def farm_funding_coins(anchor, target, can_buy_kebabs, log, label):
    _w13 = yield from reach_funding_man(anchor, log)
    if not (_w13):
        return False
    reported_hundreds = (inventory.count('Coins') // 100)
    last_evidence_at = _core.step_time()
    while inventory.count('Coins') < target:
        if event_signal.pending():
            return False
        coins_before = inventory.count('Coins')
        xp_before = skills.xp('thieving')
        hp_before = skills.effective('hitpoints')
        _w14 = yield from restore_funding_health(can_buy_kebabs, log)
        if not (_w14):
            return False
        _w15 = yield from pickpocket_funding_man(anchor, log)
        if not (_w15):
            return False
        if event_signal.pending():
            return False
        if inventory.count('Coins') != coins_before or skills.xp('thieving') != xp_before or skills.effective('hitpoints') != hp_before:
            last_evidence_at = _core.step_time()
        elif _core.step_time() - last_evidence_at >= FUNDING_STALL_MS:
            log(f'no cash, Thieving XP, or Hitpoints change for {FUNDING_STALL_MS / 1000}s at the verified Man')
            return False
        hundreds = (inventory.count('Coins') // 100)
        if hundreds > reported_hundreds:
            reported_hundreds = hundreds
            log(f"{label} funding: {inventory.count('Coins')}/{target} gp")
    return True


def east_of_al_kharid_gate(tile):
    """East of the Al Kharid toll gate (incl. Shantay north), no 10gp fee to reach the Man."""
    return tile is not None and tile.level == 0 and tile.x >= 3265 and tile.z >= 3110 and tile.z <= 3350


def fund_quest_coins(target, log, label=None):
    """Earn pack coins up to `target` via Men pickpockets. Uses Al Kharid Man + Kebab seller once inside the gate; Varrock Man only for the toll."""
    if event_signal.pending():
        return False
    if target <= 0:
        return True
    if inventory.count('Coins') >= target:
        return True
    label = (label if label is not None else 'quest')
    here = game.tile()
    if not in_al_kharid_funding_area(here):
        # Only farm the Varrock Man when we still need the toll to get east.
        if not east_of_al_kharid_gate(here) and inventory.count('Coins') < AL_KHARID_ENTRY_CASH:
            log(f'earning {AL_KHARID_ENTRY_CASH} gp (Al Kharid toll + food reserve) from a Varrock Man')
            _w16 = yield from farm_funding_coins(VARROCK_FUNDING_MAN, AL_KHARID_ENTRY_CASH, False, log, label)
            if not (_w16):
                return False
        if inventory.count('Coins') >= target:
            return True
        _w17 = yield from traversal.walk_resilient(AL_KHARID_FUNDING_MAN, radius=6, attempts=4, timeout_ms=240000, log=log)
        if not (_w17):
            return False
        if event_signal.pending():
            return False
        if not in_al_kharid_funding_area(game.tile()):
            log('did not reach the Al Kharid Man/Kebab funding area')
            return False
    log(f'pickpocketing the Al Kharid Man to {target} gp, buying Kebabs below {SAFE_PICKPOCKET_HP} HP')
    _result18 = yield from farm_funding_coins(AL_KHARID_FUNDING_MAN, target, True, log, label)
    return _result18


def earn_quest_coins_step(target, label='quest'):
    """Decide-time step: earn coins when bank has none and the pack is short."""
    return Record({
        'kind': 'custom',
        'name': f'earn {target} gp (Al Kharid Man + Kebabs)',
        'run': lambda log: fund_quest_coins(target, log, label=label),
    })
