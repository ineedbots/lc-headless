"""Ported from rs2b0t's src/bot/api/ai/quests/defs/scorpcatcher/antipoison.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.items import inventory
from rs2004.messages import game_messages
from rs2004.quests.defs.scorpcatcher.areas import ANTIPOISON_DOSES, ANTIPOISON_GP, ANTIPOISON_SHOP, SC_ITEM
from rs2004.trade import shop
from rs2004.traversal import traversal

__all__ = ['poison_mark', 'stock_antipoison', 'cure_poison']

WALK_MS = 300000
DRINK_MS = 5000
POISONED = 'you have been poisoned'


def held_dose():
    return ([name for name in ANTIPOISON_DOSES if inventory.count(name) > 0] or [None])[0]


def poison_mark():
    """Chat position to measure a later poison against."""
    return game_messages.mark()


# Why: best-effort; the quest has always finished without a cure, so an empty shop or short purse runs the corridor uncured.
def stock_antipoison(log):
    """Cross to Musa Point for a dose before the dungeon."""
    if held_dose() is not None:
        return
    coins = inventory.count('Coins')
    if coins < ANTIPOISON_GP:
        log(f'scorpcatcher: {coins} gp will not cover the {ANTIPOISON_GP} the antipoison trip costs — running the spiders uncured')
        return
    log('scorpcatcher: crossing to Musa Point for an antipoison')
    _w1 = yield from traversal.walk_resilient(ANTIPOISON_SHOP.anchor, radius=3, attempts=3, timeout_ms=WALK_MS, log=log)
    if not (_w1):
        log('scorpcatcher: could not reach the Karamja general store — running the spiders uncured')
        return
    _w2 = yield from shop.open(ANTIPOISON_SHOP.npc)
    if not (_w2):
        log('scorpcatcher: the Karamja general store would not open — running the spiders uncured')
        return
    yield from shop.buy(SC_ITEM.ANTIPOISON, 1)
    yield from shop.close()
    log((f'scorpcatcher: bought an {SC_ITEM.ANTIPOISON}' if held_dose() is not None else 'scorpcatcher: the Karamja general store is out of antipoison — running the spiders uncured'))


# Why: a dose cures and holds `%poison` negative for 5 poison ticks (90s); drunk where the spiders can still reach, that window expires and they poison you again.
def cure_poison(mark, log):
    """Drink the dose once the deep dungeon gate is shut, and only if something inside poisoned us."""
    if not game_messages.saw_since(mark, POISONED):
        return
    name = held_dose()
    if name is None:
        log('scorpcatcher: poisoned in the dungeon with no antipoison to drink')
        return
    before = inventory.count(name)
    dose = ([item for item in inventory.items() if item.name == name] or [None])[0]
    if not dose or not (dose.interact('Drink')):
        log(f'scorpcatcher: the {name} refused the drink')
        return
    _w3 = yield from execution.delay_until(lambda: inventory.count(name) < before, DRINK_MS)
    if _w3:
        log(f'scorpcatcher: drank the {name} clear of the spiders')
