"""Ported from rs2b0t's src/bot/api/ai/quests/defs/regicide/supplies.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs._items import ITEM_DB
from rs2004.catalogs.record import Record
from rs2004.geometry import Tile
from rs2004.quests.defs.regicide.areas import RG_ITEM, RG_TILE, banked, carried
from rs2004.quests.defs.upass.supplies import BOW_IDS, bow_worn
from rs2004.quests.engine.provisioning import gp_short
from rs2004.quests.food import FOOD_FLOAT

__all__ = ['usable_bows', 'bow_carried', 'ARDOUGNE_STORE', 'TAVERLEY_HERBLORE', 'CATHERBY_ARCHERY', 'COAL_ROCKS', 'ARDOUGNE_RANGE', 'FOOD_TARGET', 'WOOL_TARGET', 'ROPE_TARGET', 'ARROW_TARGET', 'STILL_FOOD', 'COAL_TARGET', 'BARREL_TARGET', 'scan_bank', 'withdraw', 'from_bank', 'KIT', 'KEEP_IDS', 'RETURN_KIT', 'source_kit', 'kit_shortfall', 'source_coal']

BOW_LEVELS = {'oak': 5, 'willow': 20, 'maple': 30, 'yew': 40, 'magic': 50, 'ogre': 30}


def usable_bows(ranged):
    return set([row['id'] for row in ITEM_DB if row['id'] in BOW_IDS and ranged >= BOW_LEVELS.get(row['obj'].split('_')[0], 1)])


def bow_carried(snap):
    usable = usable_bows((snap.ranged if snap.ranged is not None else 99))
    return bow_worn(snap) or any([count > 0 and (id in usable) for id, count in (snap.inv_ids if snap.inv_ids is not None else {}).items()])


# Why: Tirannwn has one shop and no bank, and the way out is the Arandar palisade or the Underground Pass walked end to end, so everything the forest consumes is bought and drawn in Ardougne before the quest leaves the mainland.
ARDOUGNE_STORE = Record({'npc': 'Aemad', 'anchor': Tile(2613, 3293, 0)})
TAVERLEY_HERBLORE = Record({'npc': 'Jatix', 'anchor': Tile(2899, 3428, 0)})
CATHERBY_ARCHERY = Record({'npc': 'Hickton', 'anchor': Tile(2825, 3442, 0)})
COAL_ROCKS = Tile(2581, 3480, 0)
ARDOUGNE_RANGE = Tile(2648, 3298, 0)
# Why: Making and lighting the cloth arrow each requires a free slot; 12 food left too little room once the bomb was added.
FOOD_TARGET = FOOD_FLOAT
WOOL_TARGET = 4
ROPE_TARGET = 3
ARROW_TARGET = 50
STILL_FOOD = 4
# Why: 12 is 2 clean distillations at 6 apiece. 18 was 3, and coal doesn't stack, so with the bomb chain and the food alongside it the pack ran out of room and the mining step kept swinging at a full inventory.
COAL_TARGET = 12
BARREL_TARGET = 2


def scan_bank():
    return Record({'kind': 'scan_bank', 'bank': RG_TILE.ARDOUGNE_BANK})


def withdraw(items):
    return Record({'kind': 'withdraw', 'items': items, 'bank': RG_TILE.ARDOUGNE_BANK})


def from_bank(snap, item, qty):
    """Draw `qty` from the bank, or null when the pack already holds enough or the bank has none."""
    have = carried(snap, item)
    if have >= qty:
        return None
    if not snap.bank_known:
        return scan_bank()
    stock = banked(snap, item)
    return (None if stock <= 0 else withdraw([{'name': item.name, 'id': item.id, 'qty': min(qty - have, stock)}]))


def buy_or_wait(snap, step):
    if gp_short(snap, step.est_gp) > 0:
        return Record({'kind': 'wait', 'reason': f'need ~{step.est_gp} gp for {step.item}'})
    return step


# Why: grouped by where each thing is sold. Aemad stocks 5 of the 9, and by quest order they take 4 separate visits with Taverley and Catherby in between: Ardougne, Taverley, Ardougne, Catherby, Ardougne, about 3 minutes of walking.
# Why: the bank items last, because the bank is in Ardougne and the pass is entered from West Ardougne, so finishing there is the one ordering that walks the loop once.
KIT = [
    Record({
    'item': RG_ITEM.BALL_OF_WOOL,
    'qty': WOOL_TARGET,
    'reason': "the loom, which weaves four into the bomb's fuse cloth",
    'shop': ARDOUGNE_STORE,
    'est_gp': 60,
}),
    Record({
    'item': RG_ITEM.PICKAXE,
    'qty': 1,
    'reason': 'the limestone quarry on the Arandar pass',
    'shop': ARDOUGNE_STORE,
    'est_gp': 40,
}),
    Record({
    'item': RG_ITEM.ROPE,
    'qty': ROPE_TARGET,
    'reason': "the pass's rope swing, which eats one per attempt",
    'min': 1,
    'shop': ARDOUGNE_STORE,
    'est_gp': 120,
}),
    Record({
    'item': RG_ITEM.BRONZE_ARROW,
    'qty': ARROW_TARGET,
    'reason': 'the fire arrow, one spent per shot whether it lands or not',
    'min': 1,
    'shop': ARDOUGNE_STORE,
    'est_gp': 600,
}),
    Record({
    'item': RG_ITEM.TINDERBOX,
    'qty': 1,
    'reason': 'lighting the cloth-wrapped arrow',
    'shop': ARDOUGNE_STORE,
    'est_gp': 150,
}),
    Record({
    'item': RG_ITEM.PESTLE,
    'qty': 1,
    'reason': 'grinding the sulphur and the quicklime',
    'shop': TAVERLEY_HERBLORE,
    'est_gp': 60,
}),
    Record({
    'item': RG_ITEM.SHORTBOW,
    'qty': 1,
    'reason': "firing the bridge stay rope; Aemad's stocks no bow",
    'shop': CATHERBY_ARCHERY,
    'est_gp': 150,
}),
    Record({'item': RG_ITEM.SPADE, 'qty': 1, 'reason': 'the filled-in tunnel out of the slave cages'}),
    Record({
    'item': RG_ITEM.SHARK,
    'qty': FOOD_TARGET,
    'reason': 'the traps, the soldiers and the elf warriors',
    'min': 1,
}),
]
KEEP_IDS = [RG_ITEM.get(key).id for key in RG_ITEM.keys()] + list(BOW_IDS)
# Why: the walk back in carries the crossings and the food and nothing that built the bomb: the wool is already cloth, the limestone already dust, and the pickaxe and pestle have no rock or lump left to work. The full kit would be 9 slots of dead weight beside a barrel bomb that has to fit too.
RETURN_IDS = set([
    RG_ITEM.SPADE.id,
    RG_ITEM.ROPE.id,
    RG_ITEM.SHORTBOW.id,
    RG_ITEM.BRONZE_ARROW.id,
    RG_ITEM.TINDERBOX.id,
    RG_ITEM.SHARK.id,
])
RETURN_KIT = [supply for supply in KIT if (supply.item.id in RETURN_IDS)]


def source_kit(snap, kit=None):
    """The next missing piece of kit, or null once the pack is ready for Tirannwn."""
    if kit is None:
        kit = KIT
    for supply in kit:
        if supply.item.id == RG_ITEM.SHORTBOW.id:
            if bow_carried(snap):
                continue
            if not snap.bank_known:
                return scan_bank()
            usable = usable_bows((snap.ranged if snap.ranged is not None else 99))
            stock = snap.bank_ids if snap.bank_ids is not None else {}
            bow = ([row for row in ITEM_DB if row['id'] in usable and stock.get(row['id'], 0) > 0] or [None])[0]
            if bow:
                return withdraw([{'name': bow['name'], 'id': bow['id'], 'qty': 1}])
        if carried(snap, supply.item) >= supply.qty:
            continue
        drawn = from_bank(snap, supply.item, supply.qty)
        if drawn:
            return drawn
        if supply.shop and supply.est_gp is not None:
            return buy_or_wait(snap, Record({
                'kind': 'buy',
                'item': supply.item.name,
                'qty': supply.qty - carried(snap, supply.item),
                'shop': supply.shop,
                'est_gp': supply.est_gp,
            }))
    return None


def kit_shortfall(snap, kit=None):
    """What the kit is still short of, for the stop message."""
    if kit is None:
        kit = KIT
    short = []
    for supply in kit:
        needed = supply.min if supply.min is not None else supply.qty
        if supply.item.id == RG_ITEM.SHORTBOW.id:
            if not bow_carried(snap):
                short.append('a bow (firing the bridge stay rope), have none')
        elif carried(snap, supply.item) < needed:
            short.append(f'{needed}x {supply.item.name} ({supply.reason}), have {carried(snap, supply.item)}')
    return short


def source_coal(snap):
    """Coal for the still, mined at the trucks; no 2004 shop keeps a stock of it."""
    if carried(snap, RG_ITEM.COAL) >= COAL_TARGET:
        return None
    drawn = from_bank(snap, RG_ITEM.COAL, COAL_TARGET)
    if drawn:
        return drawn
    return Record({'kind': 'mine_rock', 'rock': 'Coal', 'item': RG_ITEM.COAL.name, 'qty': COAL_TARGET, 'anchor': COAL_ROCKS})

