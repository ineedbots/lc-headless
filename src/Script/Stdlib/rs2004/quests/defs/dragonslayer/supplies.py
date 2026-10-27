"""Ported from rs2b0t's src/bot/api/ai/quests/defs/dragonslayer/supplies.ts (MIT, see thirdparty/rs2b0t)."""

import _core
import math
from rs2004 import execution
from rs2004.bank import bank
from rs2004.catalogs.record import Record
from rs2004.quests.exec.primitives import talk_through
from rs2004.quests.exec.steps import open_bank_leg
from rs2004.quests.food import quest_food
from rs2004.dialogue import chat_dialog, modals
from rs2004.entities import ground_items, locs
from rs2004.game import game, skills
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.trade import shop
from rs2004.traversal import traversal

__all__ = ['SUPPLY', 'SUPPLY_TOOLS', 'ensure_coins', 'smith_nails', 'in_plank_graveyard', 'SUPPLY_GATHERS']

# Why: 4 of the 7 shopping items are bought; planks only lie on the ground (nearest pile outside Crandor is the Graveyard of Shadows), nails are 2 to a steel bar, and an unfired bowl is clay, water and a potter's wheel.
SUPPLY = Record({
    'GENERAL_STORE': Record({'npc': 'Shop keeper', 'anchor': Tile(2955, 3389, 0)}),
    'THESSALIA': Record({'npc': 'Thessalia', 'anchor': Tile(3204, 3417, 0)}),
    'GERRANT': Record({'npc': 'Gerrant', 'anchor': Tile(3013, 3225, 0)}),
    'BARMAID': Record({'npc': 'Barmaid', 'anchor': Tile(2957, 3371, 0)}),
    'NURMOF': Record({'npc': 'Nurmof', 'anchor': Tile(2998, 9844, 0)}),
})
SUPPLY_LOC = Record({
    'FOUNTAIN': Tile(2949, 3381, 0),
    'CLAY_ROCKS': Tile(3181, 3373, 0),
    'IRON_ROCKS': Tile(3040, 9773, 0),
    'COAL_ROCKS': Tile(3042, 9760, 0),
    'ANVIL': Tile(3012, 9812, 0),
    'FURNACE': Tile(2974, 3369, 0),
    'POTTERS_WHEEL': Tile(3087, 3410, 0),
    'PLANK_SPAWNS': [Tile(3154, 3659, 0), Tile(3154, 3670, 0), Tile(3148, 3671, 0), Tile(3182, 3669, 0), Tile(3171, 3680, 0)],
})
SUPPLY_ITEM = Record({
    'JUG': 'Jug',
    'JUG_WATER': 'Jug of water',
    'CLAY': 'Clay',
    'SOFT_CLAY': 'Soft clay',
    'STEEL_BAR': 'Steel bar',
    'IRON_ORE': 'Iron ore',
    'COAL': 'Coal',
    'PICKAXE': 'Bronze pickaxe',
})
SUPPLY_TOOLS = ['jug', 'clay', 'steel bar', 'iron ore', 'coal', 'pickaxe', 'bucket']


def walk(to, log, radius=2):
    return traversal.walk_resilient(to, radius=radius, attempts=3, timeout_ms=180000, log=log)


def scene_loaded():
    return execution.delay_until(lambda: locs.query().within(10).exists(), 6000)


def buy(item, qty, shop, est_gp):
    return (Record({
        'kind': 'buy',
        'item': item,
        'qty': qty,
        'shop': Record({'npc': shop.npc, 'anchor': shop.anchor}),
        'est_gp': est_gp,
    }))


# Why: no standing coin float; it's topped up every provisioning loop and would put a bank trip between purchases.
def ensure_coins(need, log):
    """Fetch spending money only when a leg is about to spend it."""
    if inventory.count('Coins') >= need:
        return True
    _w1 = yield from open_bank_leg('no bank to draw spending money from', None, log)
    if not (_w1):
        return False
    yield from bank.withdraw_x('Coins', max(need, 2000))
    yield from modals.close()
    return inventory.count('Coins') >= need


def buy_mind_bomb(log):
    """The barmaid sells through dialogue, so the generic buy step cannot see her."""
    _w2 = yield from ensure_coins(10, log)
    if not (_w2):
        log('no coins for a mind bomb')
        return False
    # Why: she takes the money regardless, and a bomb bought into a full pack lands on the floor, so check here too.
    if inventory.is_full():
        log('pack is full — she would pour the mind bomb onto the floor')
        return False
    _w3 = yield from walk(SUPPLY.BARMAID.anchor, log, 2)
    if not (_w3):
        return False
    before = inventory.count("Wizard's mind bomb")
    log("ordering a Wizard's Mind Bomb at the Rising Sun")
    _w4 = yield from talk_through(SUPPLY.BARMAID.npc, ["I'll try the Mind Bomb."], log)
    if not (_w4):
        return False
    _result5 = yield from execution.delay_until(lambda: inventory.count("Wizard's mind bomb") > before, 5000)
    return _result5


# Why: a timeout throws away the current swing and the caller re-clicks, so one shorter than the ore takes loops forever and looks like a slow rock. Hence the loud log.
MINE_TIMEOUT_MS = 20000


def _material_count(name):
    # Random-event rewards can include notes sharing the raw material's display name.
    return sum([item.count for item in inventory.items() if item.name == name and not getattr(item, 'noted', False)])


def mine_for(rock_ids, item, want, at, log):
    """Mines until the pack holds `want` of the named ore."""
    if _material_count(item) >= want:
        return True
    if not any([('pickaxe' in i.name.lower()) for i in inventory.items()]):
        log('no pickaxe in the pack')
        return False
    # Why: a full pack doesn't refuse the Mine op, the rock never yields, which looks like an empty rock.
    if inventory.is_full():
        log(f'pack is full — no room for {item}')
        return False
    ids = set(rock_ids)

    # Wide enough to cross a seam: a mined rock is a different loc until it respawns, so a tight radius parks the leg on its own leftovers.
    def rock():
        target_ids = ids
        return locs.query().where(lambda l: (l.id in target_ids)).action('Mine').within(14).nearest()

    def seam():
        target_ids = ids
        return locs.query().where(lambda l: (l.id in target_ids)).action('Mine').within(14).count()

    if not rock():
        log(f'no live {item} rock within 14 — walking to the seam at ({at.x},{at.z})')
        _w7 = yield from walk(at, log, 2)
        _c6 = not (_w7)
        if not _c6:
            _w8 = yield from scene_loaded()
            _c6 = not (_w8)
        if _c6:
            log(f'could not reach the {item} seam at ({at.x},{at.z})')
            return False
    target = rock()
    if not target:
        log(f"no {item} rocks in reach — waiting on a respawn (mining {skills.level('mining')}, " + f'{_material_count(item)}/{want} {item} held)')
        yield from execution.delay_ticks(5)
        return False
    before = _material_count(item)
    spot = target.tile()
    log(f'mining {item} {before}/{want} — rock {target.id} at ({spot.x},{spot.z}) ' + f'{target.distance()} tile(s) away, {seam()} live rock(s) in the seam, {inventory.free()} free slot(s)')
    if not (target.interact('Mine')):
        log(f'the Mine click on rock {target.id} was not accepted')
        return False
    swung_at = _core.step_time()
    landed = yield from execution.delay_until(lambda: _material_count(item) > before, MINE_TIMEOUT_MS)
    took = f'{((_core.step_time() - swung_at) / 1000):.1f}'
    if not landed:
        log(f"gave up on rock {target.id} after {took}s with no {item} — mining {skills.level('mining')}; " + 'the next pass re-clicks and restarts the swing, so a rock slower than ' + f'{MINE_TIMEOUT_MS / 1000}s never finishes')
        return False
    now = _material_count(item)
    log(f'got {item} {now}/{want} in {took}s')
    return now >= want


ROCKS = Record({'clay': [2108, 2109], 'iron': [2092, 2093], 'coal': [2096, 2097]})
# Why: bronze pickaxes lie on the ground free, one 13 tiles from the Falador bank; Nurmof is at the bottom of the Dwarven Mine, so he's last.
PICKAXE_SPAWNS = [Tile(3009, 3342, 0), Tile(3081, 3429, 0), Tile(2963, 3216, 0)]
pickaxe_tried = set()


def ensure_pickaxe(log):
    if any([('pickaxe' in i.name.lower()) for i in inventory.items()]):
        pickaxe_tried.clear()
        return True
    loose = ground_items.query().name(SUPPLY_ITEM.PICKAXE).within(12).nearest()
    if loose:
        log('taking the pickaxe off the ground')
        if loose.interact('Take'):
            _result9 = yield from execution.delay_until(lambda: inventory.contains(SUPPLY_ITEM.PICKAXE), 8000)
            return _result9
    here = game.tile()

    spawn = (sorted([t for t in PICKAXE_SPAWNS if not (f'{t.x},{t.z}' in pickaxe_tried)], key=lambda t: t.distance_to(here) if here else 0) or [None])[0]
    if spawn:
        pickaxe_tried.add(f'{spawn.x},{spawn.z}')
        log(f'checking the pickaxe spawn at ({spawn.x},{spawn.z})')
        yield from walk(spawn, log, 1)
        yield from scene_loaded()
        return False
    # Every spawn was bare; Nurmof always has one.
    log('no pickaxe on the ground anywhere — buying one from Nurmof')
    _w11 = yield from ensure_coins(200, log)
    _c10 = not (_w11)
    if not _c10:
        _w12 = yield from walk(SUPPLY.NURMOF.anchor, log, 2)
        _c10 = not (_w12)
    if _c10:
        return False
    _w13 = yield from shop.open(SUPPLY.NURMOF.npc)
    if not (_w13):
        log("could not open Nurmof's shop")
        return False
    yield from shop.buy(SUPPLY_ITEM.PICKAXE, 1)
    yield from shop.close()
    return inventory.contains(SUPPLY_ITEM.PICKAXE)


def make_unfired_bowl(log):
    """Clay, water and a potter's wheel; the bowl is fired later or not at all."""
    if inventory.contains('Unfired bowl'):
        return True
    if inventory.contains(SUPPLY_ITEM.SOFT_CLAY):
        _w15 = yield from walk(SUPPLY_LOC.POTTERS_WHEEL, log, 1)
        _c14 = not (_w15)
        if not _c14:
            _w16 = yield from scene_loaded()
            _c14 = not (_w16)
        if _c14:
            return False
        wheel = locs.query().name("Potter's Wheel").within(5).nearest()
        clay = inventory.first(SUPPLY_ITEM.SOFT_CLAY)
        if not wheel or not clay:
            log("no potter's wheel in reach")
            return False
        log('throwing a bowl on the wheel')
        if not (clay.use_on(wheel)):
            return False
        # skill_multi3 is if_openchat, a chat make menu; the anvil uses the main skill panel.
        _w17 = yield from execution.delay_until(lambda: chat_dialog.is_make_menu(), 6000)
        if not (_w17):
            log('the wheel did not offer anything to make')
            return False
        _w18 = yield from chat_dialog.make('Bowl')
        if not (_w18):
            return False
        _result19 = yield from execution.delay_until(lambda: inventory.contains('Unfired bowl'), 10000)
        return _result19
    if inventory.contains(SUPPLY_ITEM.CLAY) and inventory.contains(SUPPLY_ITEM.JUG_WATER):
        clay = inventory.first(SUPPLY_ITEM.CLAY)
        water = inventory.first(SUPPLY_ITEM.JUG_WATER)
        if not clay or not water:
            return False
        log('mixing the clay with water')
        if not (clay.use_on(water)):
            return False
        _result20 = yield from execution.delay_until(lambda: inventory.contains(SUPPLY_ITEM.SOFT_CLAY), 8000)
        return _result20
    if not inventory.contains(SUPPLY_ITEM.JUG_WATER):
        if not inventory.contains(SUPPLY_ITEM.JUG):
            log('buying a jug')
            _w21 = yield from ensure_coins(200, log)
            if not (_w21):
                return False
            _w23 = yield from walk(SUPPLY.GENERAL_STORE.anchor, log, 2)
            _c22 = not (_w23)
            if not _c22:
                _w24 = yield from shop.open(SUPPLY.GENERAL_STORE.npc)
                _c22 = not (_w24)
            if _c22:
                return False
            yield from shop.buy(SUPPLY_ITEM.JUG, 1)
            yield from shop.close()
            return inventory.contains(SUPPLY_ITEM.JUG)
        _w26 = yield from walk(SUPPLY_LOC.FOUNTAIN, log, 1)
        _c25 = not (_w26)
        if not _c25:
            _w27 = yield from scene_loaded()
            _c25 = not (_w27)
        if _c25:
            return False
        fountain = locs.query().name('Fountain').within(5).nearest()
        jug = inventory.first(SUPPLY_ITEM.JUG)
        if not fountain or not jug:
            log('no fountain in reach')
            return False
        log('filling the jug')
        if not (jug.use_on(fountain)):
            return False
        _result28 = yield from execution.delay_until(lambda: inventory.contains(SUPPLY_ITEM.JUG_WATER), 8000)
        return _result28
    _w29 = yield from ensure_pickaxe(log)
    if not (_w29):
        return False
    _result30 = yield from mine_for(ROCKS.clay, SUPPLY_ITEM.CLAY, 1, SUPPLY_LOC.CLAY_ROCKS, log)
    return _result30


def smith_nails(need, log):
    """Nails are 2 to a steel bar and nothing sells bars: 1 iron and 2 coal per bar at the Falador furnace, then the Dwarven Mine anvil."""
    # `need` is the shortfall. 2 nails to a bar.
    if need <= 0:
        return True
    bars = math.ceil(need / 2)

    def ore():
        return _material_count(SUPPLY_ITEM.IRON_ORE)

    # Why: a banked maze key reads to decide() as "the briefing never happened", Ned waits on the map, and the shield can't be fetched once the ship has sailed.
    KEEP = [
        'coins',
        'pickaxe',
        'hammer',
        'maze key',
        'crandor map',
        'map part',
        'dragonfire shield',
        'iron ore',
        'coal',
        'steel bar',
        'nails',
        'shark',
        'lobster',
        'swordfish',
        'tuna',
        'salmon',
        'trout',
    ]

    def coal():
        return _material_count(SUPPLY_ITEM.COAL)

    def steel():
        return _material_count(SUPPLY_ITEM.STEEL_BAR)

    # Why: mine the load, smelt the load, hammer the load; per-bar it's 6 round trips between furnace and anvil.
    if steel() == 0 and (ore() < bars or coal() < bars * 2):
        # The maze carries a combat load; the eighteen-slot ore batch needs the original three-fish float.
        food = quest_food.name
        if food and inventory.count(food) > 3:
            opened = yield from open_bank_leg('no bank to reduce the maze food at', None, log)
            if not opened:
                return False
            while inventory.count(food) > 3:
                before = inventory.count(food)
                if not bank.deposit(food):
                    return False
                deposited = yield from execution.delay_until(lambda: inventory.count(food) < before, 3000)
                if not deposited:
                    return False
            log('banked surplus maze food for the ore load')
            return False
        # Why: 6 bars is 18 slots of ore, so the shopping goes in the bank until the ship needs it.
        note_ids = set([i.id for i in inventory.items() if getattr(i, 'noted', False)])
        if note_ids or any([i.name is not None and not any([(k in i.name.lower()) for k in KEEP]) for i in inventory.items()]):
            log('banking the shopping to make room for ore')
            _w31 = yield from open_bank_leg('no bank to clear the pack at', None, log)
            if not (_w31):
                return False
            spare = [i.name for i in inventory.items() if i.id in note_ids or (i.name is not None and not any([k in i.name.lower() for k in KEEP]))]
            yield from bank.deposit_all_matching(lambda name, id: id in note_ids or not any([(k in name.lower()) for k in KEEP]))
            log(f"banked {len(spare)} items for ore room: {', '.join(spare)}")
            # Why: the bank stays open since QuestEngine only re-reads it while the interface is up; a stale snapshot makes the deposit look lost and sends the bot back to Oziach for the maze key.
            return False
        _w32 = yield from ensure_pickaxe(log)
        if not (_w32):
            return False
        if ore() < bars:
            _result33 = yield from mine_for(ROCKS.iron, SUPPLY_ITEM.IRON_ORE, bars, SUPPLY_LOC.IRON_ROCKS, log)
            return _result33
        _result34 = yield from mine_for(ROCKS.coal, SUPPLY_ITEM.COAL, bars * 2, SUPPLY_LOC.COAL_ROCKS, log)
        return _result34
    if ore() > 0 and coal() >= 2:
        _w36 = yield from walk(SUPPLY_LOC.FURNACE, log, 1)
        _c35 = not (_w36)
        if not _c35:
            _w37 = yield from scene_loaded()
            _c35 = not (_w37)
        if _c35:
            return False
        # The Smelt op opens the quantity panel; use-on instead makes one bar without a menu.
        smelter = locs.query().name('Furnace').action('Smelt').within(5).nearest()
        furnace = smelter if smelter is not None else locs.query().name('Furnace').within(5).nearest()
        if not furnace:
            log('no furnace in reach')
            return False
        log(f'smelting {min(ore(), coal() // 2)} steel bars')
        if smelter:
            if not smelter.interact('Smelt'):
                return False
        else:
            held = inventory.first(SUPPLY_ITEM.IRON_ORE)
            if not held or not held.use_on(furnace):
                return False
        menu = yield from execution.delay_until(lambda: chat_dialog.is_make_menu(), 6000)
        if not menu:
            return steel() > 0
        made = yield from chat_dialog.make('Steel')
        if not made:
            return False
        yield from execution.delay_until(lambda: ore() == 0 or coal() < 2, 180000)
        return steel() > 0
    if steel() == 0:
        log('no steel and nothing to smelt it from')
        return False
    # An anvil without a hammer does nothing and says nothing.
    if not inventory.contains('Hammer'):
        log('no hammer — an anvil will not answer without one')
        return False
    _w41 = yield from walk(SUPPLY_LOC.ANVIL, log, 1)
    _c40 = not (_w41)
    if not _c40:
        _w42 = yield from scene_loaded()
        _c40 = not (_w42)
    if _c40:
        return False
    anvil = locs.query().name('Anvil').within(5).nearest()
    bar = inventory.first(SUPPLY_ITEM.STEEL_BAR)
    if not anvil or not bar:
        log('no anvil in reach')
        return False
    log(f'hammering {steel()} bars into nails')
    if not (bar.use_on(anvil)):
        return False
    _w43 = yield from execution.delay_until(lambda: chat_dialog.is_main_make_panel(), 6000)
    if not (_w43):
        return False
    _w44 = yield from chat_dialog.make_from_panel_max('Nails')
    if not (_w44):
        return False
    yield from execution.delay_until(lambda: steel() == 0, 180000)
    return inventory.count('Nails') >= need


def in_plank_graveyard(t):
    return not not t and t.level == 0 and any([abs(s.x - t.x) <= 8 and abs(s.z - t.z) <= 8 for s in SUPPLY_LOC.PLANK_SPAWNS])


plank_tried = set()


# Why: `need` is the shortfall the engine still wants; compared against the pack, "2 held, 1 short" reads as satisfied and the third plank never gets fetched.
def grab_planks(need, log):
    """Walk the Graveyard of Shadows picking up the plank spawns."""
    if need <= 0:
        plank_tried.clear()
        return True
    loose = ground_items.query().name('Plank').within(14).nearest()
    if loose:
        before = inventory.count('Plank')
        log('taking a plank')
        if not (loose.interact('Take')):
            return False
        yield from execution.delay_until(lambda: inventory.count('Plank') > before, 8000)
        return inventory.count('Plank') >= need
    here = game.tile()
    if here:
        for t in SUPPLY_LOC.PLANK_SPAWNS:
            if t.distance_to(here) <= 6 and t.level == here.level:
                plank_tried.add(f'{t.x},{t.z}')

    next_ = (sorted([t for t in SUPPLY_LOC.PLANK_SPAWNS if not (f'{t.x},{t.z}' in plank_tried)], key=lambda t: t.distance_to(here) if here else 0) or [None])[0]
    if not next_:
        log('every plank spawn was empty — they respawn, so waiting')
        plank_tried.clear()
        yield from execution.delay_ticks(10)
        return False
    log(f'walking to the plank spawn at ({next_.x},{next_.z})')
    yield from walk(next_, log, 2)
    yield from scene_loaded()
    return False


def custom(name, run):
    return (Record({'kind': 'custom', 'name': name, 'run': run}))


# Why: the mining load is left out since 18 slots of ore is what fills the pack, and smithNails re-mines whatever gets banked.
SHOPPING_KEEP = [
    'coins',
    'maze key',
    'pickaxe',
    'hammer',
    'lobster pot',
    "wizard's mind bomb",
    'unfired bowl',
    'silk',
    'plank',
    'jug',
    'clay',
]


# Why: a purchase into a full pack isn't refused, `inv_add` drops the overflow at your feet and the coins are gone, so the "did it arrive" check loops and pays every lap.
def make_room(snap, slots=1):
    """Free `slots` inventory slots before an acquisition, or null when there is room."""
    if snap.free_slots is None or snap.free_slots >= slots:
        return None
    food = quest_food.name.lower()
    keep = (list(SHOPPING_KEEP) + [food] if food else list(SHOPPING_KEEP))
    spare = any([not any([(k in name) for k in keep]) for name in list(list(snap.inv.keys()))])
    return (Record({'kind': 'deposit', 'keep': keep}) if spare else Record({
        'kind': 'wait',
        'reason': f"no room for {slots} more item{('' if slots == 1 else 's')} and nothing spare to bank",
    }))


SUPPLY_GATHERS = Record({
    'hammer': lambda snap, need: (make_room(snap) if make_room(snap) is not None else buy('Hammer', 1, SUPPLY.GENERAL_STORE, 100)),
    'silk': lambda snap, need: (make_room(snap) if make_room(snap) is not None else buy('Silk', 1, SUPPLY.THESSALIA, 200)),
    'lobster pot': lambda snap, need: (make_room(snap) if make_room(snap) is not None else buy('Lobster pot', 1, SUPPLY.GERRANT, 200)),
    "wizard's mind bomb": lambda snap, need: (make_room(snap) if make_room(snap) is not None else custom('buy a mind bomb at the Rising Sun', buy_mind_bomb)),
    'unfired bowl': lambda snap, need: (Record({
    'kind': 'wait',
    'reason': 'Crafting 8 is required to make an unfired bowl; train Crafting or obtain and bank an Unfired bowl',
}) if skills.effective('crafting') < 8 else (make_room(snap) if make_room(snap) is not None else custom('make an unfired bowl', make_unfired_bowl))),
    'plank': lambda snap, need: (make_room(snap, need) if make_room(snap, need) is not None else custom(f"fetch {need} plank{('' if need == 1 else 's')}", lambda log: grab_planks(need, log))),
})
