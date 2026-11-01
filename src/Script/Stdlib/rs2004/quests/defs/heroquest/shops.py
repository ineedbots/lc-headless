"""Ported from rs2b0t's src/bot/api/ai/quests/defs/heroquest/shops.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.items import inventory
from rs2004.quests.defs.heroquest.areas import HERO_ID, HERO_NAMED
from rs2004.quests.defs.heroquest.doors import return_to_street
from rs2004.quests.defs.heroquest.state import banked_id, held_id, worn_id
from rs2004.quests.exec.steps import execute_step

__all__ = ['priced', 'buy_from_any', 'purchase_step', 'kit_owned', 'kit_step']

def priced(shop, gp):
    """A stockist and what to carry there."""
    return Record({'npc': shop.npc, 'anchor': shop.anchor, 'gp': gp})


# Why: `World.restock` skips a null slot, so a shared shop that sells its last unit never gets it back; 2 stockists is what makes an `allstock=no` item dependable.
def buy_from_any(item, log):
    """Buy from the first stockist that still has one."""
    # Why: 5 of the 6 rooms this quest works in are pockets the navigator has no edge out of, so a shop walk planned from inside one reads `unreachable` before it takes a step.
    _w1 = yield from return_to_street(log)
    if not (_w1):
        return False
    for source in item.sources:
        # Why: the engine's purse only banks below a quarter of the estimate, so 30000 gp left after the chainbody never
        # went back for the 100000 gp platelegs, and Scavvo refused "You don't have enough coins" until the quest parked.
        short = source.gp - inventory.count(HERO_NAMED.COINS)
        if short > 0:
            drawn = yield from execute_step(Record({'kind': 'withdraw', 'items': [{'name': HERO_NAMED.COINS, 'qty': short, 'id': HERO_ID.COINS}]}), [], log)
            if not drawn:
                log(f'could not draw {short} gp for {item.name}')
                return False
        bought = yield from execute_step(Record({
            'kind': 'buy',
            'item': item.name,
            'qty': item.qty,
            'shop': Record({'npc': source.npc, 'anchor': source.anchor}),
            'est_gp': source.gp,
        }), [], log)
        if bought:
            return True
        log(f'{source.npc} had no {item.name}')
    return False


def purchase_step(snap, item):
    """Wear it, withdraw it, or buy it, in that order."""
    if worn_id(snap, item.id):
        return None
    if held_id(snap, item.id) >= item.qty:
        return Record({'kind': 'equip', 'item': item.name})
    if banked_id(snap, item.id) >= item.qty:
        return Record({'kind': 'withdraw', 'items': [{'name': item.name, 'qty': item.qty, 'id': item.id}]})
    return Record({'kind': 'custom', 'name': f'buy {item.qty}× {item.name}', 'run': lambda log: buy_from_any(item, log)})


def kit_owned(snap, kit):
    """True once every piece is worn, carried or banked."""
    return all([worn_id(snap, item.id) or held_id(snap, item.id) >= item.qty or banked_id(snap, item.id) >= item.qty for item in kit])


def kit_step(snap, kit):
    """The first piece that still needs work, or null once the kit is worn."""
    for item in kit:
        step = purchase_step(snap, item)
        if step:
            return step
    return None
