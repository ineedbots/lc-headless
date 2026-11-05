"""Ported from rs2b0t's src/bot/api/ai/quests/defs/ikov/supplies.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import chat_dialog, modals
from rs2004.entities import ground_items, locs, npcs
from rs2004.execution import event_signal
from rs2004.game import game, skills
from rs2004.items import equipment, inventory
from rs2004.navigation import reachability
from rs2004.quests.defs.ikov.areas import IKOV_FOODS, IKOV_LOC, IKOV_NAME, IKOV_NPC, IKOV_OBJ, IKOV_TILE, ROOTS_WANTED
from rs2004.quests.defs.ikov.gear import melee_weapon_step, ranged_armour_step
from rs2004.quests.exec.prompts import held_id
from rs2004.traversal import traversal

__all__ = ['held_or_banked', 'restock_step', 'supplies_step', 'sourcing_shortfall']

IKOV_SOURCING_SKILLS = [
    Record({'skill': 'woodcutting', 'level': 60}),
    Record({'skill': 'fletching', 'level': 65}),
    Record({'skill': 'crafting', 'level': 10}),
]
WEAPON_SLOT = 3
AMMO_SLOT = 13
FARM_FOOD = 10
FARM_FOOD_FLOOR = 5
FARM_ARROWS = 20
AXE_GP = 300
CHOP_MS = 120000
PICK_MS = 20000
KILL_MS = 60000
HOB_RADIUS = 20
FLEE_HP = 0.45
ROOT_RADIUS = 12
REACH_STEPS = 20000
# Why: the make menu's caption is 'Yew Short Bow', where the item is 'Yew shortbow', so the item's name finds no product.
FLETCH_PRODUCT = 'Yew Short Bow'


# Why: a worn bow doesn't need fletching again, and the pack view can't see it.
def held_or_banked(snap, id):
    _v1 = (snap.inv_ids.get(id) if snap.inv_ids is not None else None)
    _v2 = (snap.bank_ids.get(id) if snap.bank_ids is not None else None)
    return ((_v1 if _v1 is not None else 0)) + ((_v2 if _v2 is not None else 0)) + ((1 if ((id in snap.worn_ids) if snap.worn_ids is not None else None) == True else 0))


def kit_candle_ready(snap):
    """True once the bank or the pack can produce a lit candle for the dark stairs."""
    if held_or_banked(snap, IKOV_OBJ.LIT_CANDLE) > 0:
        return True
    return held_or_banked(snap, IKOV_OBJ.UNLIT_CANDLE) > 0 and held_or_banked(snap, IKOV_OBJ.TINDERBOX) > 0


def chop_yew(log):
    if not inventory.contains(IKOV_NAME.IRON_AXE) and not any([((i.name if i.name is not None else '').lower().endswith('axe')) for i in inventory.items()]):
        log('ikov: no axe in the pack for the yew')
        return False
    before = inventory.count(IKOV_NAME.YEW_LOGS)
    tree = locs.query().where(lambda l: l.id == IKOV_LOC.YEW_TREE).action('Chop down').within(10).nearest()
    if not tree:
        _result3 = yield from traversal.walk_resilient(IKOV_TILE.YEW_TREES, radius=3, attempts=3, timeout_ms=300000, log=log)
        return _result3
    if not (tree.interact('Chop down')):
        return False
    log('ikov: chopping a yew for the bow stave')
    deadline = _core.step_time() + CHOP_MS
    while _core.step_time() < deadline:
        if inventory.count(IKOV_NAME.YEW_LOGS) > before:
            return True
        if event_signal.pending():
            return False
        yield from sustain.run()
        yield from execution.delay_ticks(2)
    log('ikov: the yew gave nothing in two minutes')
    return False


def pick_flax(log):
    before = inventory.count(IKOV_NAME.FLAX)
    plant = locs.query().where(lambda l: l.id == IKOV_LOC.FLAX).action('Pick').within(10).nearest()
    if not plant:
        _result4 = yield from traversal.walk_resilient(IKOV_TILE.FLAX_FIELD, radius=3, attempts=3, timeout_ms=300000, log=log)
        return _result4
    if not (plant.interact('Pick')):
        return False
    _result5 = yield from execution.delay_until(lambda: inventory.count(IKOV_NAME.FLAX) > before, PICK_MS)
    return _result5


# Why: strung and unstrung yew shortbows share the display name, so the product is chosen off the make menu and counted by id.
def fletch_bow(log):
    # Why: the first use-on after a bank trip lands while the booth is still closing, and the menu never opens.
    for attempt in range(3):
        if not (not chat_dialog.is_make_menu()):
            break
        yield from modals.close_if_open()
        yield from execution.delay_ticks(2)
        knife = ([i for i in inventory.items() if i.id == IKOV_OBJ.KNIFE] or [None])[0]
        logs = ([i for i in inventory.items() if i.id == IKOV_OBJ.YEW_LOGS] or [None])[0]
        if not knife or not logs:
            log('ikov: the pack is short a knife or yew logs')
            return False
        if not (knife.use_on(logs)):
            continue
        yield from execution.delay_until(lambda: chat_dialog.is_make_menu(), 6000)
    if not chat_dialog.is_make_menu():
        log('ikov: the fletch menu never opened')
        return False
    before = held_id(IKOV_OBJ.UNSTRUNG_YEW_SHORTBOW)
    _w6 = yield from chat_dialog.make_one(FLETCH_PRODUCT)
    if not (_w6):
        log(f"ikov: no shortbow on the fletch menu — products: [{', '.join(chat_dialog.make_products())}]")
        return False
    _result7 = yield from execution.delay_until(lambda: held_id(IKOV_OBJ.UNSTRUNG_YEW_SHORTBOW) > before, 10000)
    return _result7


def string_bow(log):
    string = ([i for i in inventory.items() if i.id == IKOV_OBJ.BOW_STRING] or [None])[0]
    stave = ([i for i in inventory.items() if i.id == IKOV_OBJ.UNSTRUNG_YEW_SHORTBOW] or [None])[0]
    if not string or not stave:
        log('ikov: the pack is short a bow string or a yew stave')
        return False
    if not (string.use_on(stave)):
        return False
    _result8 = yield from execution.delay_until(lambda: held_id(IKOV_OBJ.YEW_SHORTBOW) > 0, 10000)
    return _result8


def light_candle(log):
    if held_id(IKOV_OBJ.LIT_CANDLE) > 0:
        return True
    tinderbox = ([i for i in inventory.items() if i.id == IKOV_OBJ.TINDERBOX] or [None])[0]
    candle = ([i for i in inventory.items() if i.id == IKOV_OBJ.UNLIT_CANDLE] or [None])[0]
    if not tinderbox or not candle:
        log(f"ikov: the pack is short {('a tinderbox' if not tinderbox else 'a candle')} for the dark stairs")
        return False
    log('ikov: lighting the candle for the dark stairs')
    if not (tinderbox.use_on(candle)):
        return False
    _result9 = yield from execution.delay_until(lambda: held_id(IKOV_OBJ.LIT_CANDLE) > 0, 8000)
    return _result9


def scene_reachable(tile):
    return reachability.can_reach(tile, adjacent_ok=True, max_steps=REACH_STEPS)


def starving():
    """Low enough that the next 2 hits could land the bot in Lumbridge, with no food to stop them."""
    max_ = skills.level('hitpoints')
    return max_ > 0 and skills.effective('hitpoints') <= max_ * FLEE_HP and not any([inventory.contains(food) for food in IKOV_FOODS])


def hobgoblin():
    return npcs.query().where(lambda n: n.id == IKOV_NPC.HOBGOBLIN_ARMED or n.id == IKOV_NPC.HOBGOBLIN_UNARMED).action('Attack').where(lambda n: not n.targets_another_player()).where(lambda n: scene_reachable(n.tile())).within(HOB_RADIUS).nearest()


def take_root(log):
    drop = ground_items.query().where(lambda g: g.id == IKOV_OBJ.LIMPWURT_ROOT).action('Take').within(ROOT_RADIUS).nearest()
    if not drop:
        return False
    before = inventory.count_by_id(IKOV_OBJ.LIMPWURT_ROOT)
    _c10 = drop.distance() > 1
    if _c10:
        _w11 = yield from traversal.walk_resilient(drop.tile(), radius=1, attempts=2, timeout_ms=60000, log=log)
        _c10 = not (_w11)
    if _c10:
        return False
    still = ground_items.query().where(lambda g: g.id == IKOV_OBJ.LIMPWURT_ROOT).action('Take').within(ROOT_RADIUS).nearest()
    if not still or not (still.interact('Take')):
        return False
    took = yield from execution.delay_until(lambda: inventory.count_by_id(IKOV_OBJ.LIMPWURT_ROOT) > before, 6000)
    if took:
        log(f'ikov: {inventory.count_by_id(IKOV_OBJ.LIMPWURT_ROOT)}/{ROOTS_WANTED} limpwurt roots')
    return took


def kill_hobgoblin(target, log):
    index = target.index

    def live():
        return ([n for n in npcs.all() if n.index == index] or [None])[0]

    game.set_auto_retaliate(True)
    _c12 = target.distance() > 8
    if _c12:
        _w13 = yield from traversal.walk_resilient(target.tile(), radius=2, attempts=2, timeout_ms=90000, log=log)
        _c12 = not (_w13)
    if _c12:
        return False
    if not (target.interact('Attack')):
        return False
    deadline = _core.step_time() + KILL_MS
    while _core.step_time() < deadline:
        if event_signal.pending():
            return False
        yield from sustain.run()
        if not live():
            return True
        # Why: the camp is a crowd and the bot fights it in boots, so an empty pack at low hp is a death; handing the tick back sends the ladder to a booth, which is also the way out.
        if starving():
            log(f"ikov: {skills.effective('hitpoints')} hitpoints and nothing to eat — leaving the camp")
            return False
        yield from execution.delay_ticks(1)
    log(f'ikov: hobgoblin {index} outlived {KILL_MS / 1000}s')
    return False


def farm_roots(log):
    """One unit of root farming: take a drop, kill a hobgoblin, or close on the camp."""
    _w14 = yield from take_root(log)
    if _w14:
        return True
    if inventory.free() == 0:
        log('ikov: the pack is full mid-farm')
        return False
    hob = hobgoblin()
    if hob:
        _result15 = yield from kill_hobgoblin(hob, log)
        return _result15
    here = game.tile()
    if here and IKOV_TILE.HOBGOBLINS.distance_to(here) <= HOB_RADIUS:
        yield from execution.delay_until(lambda: hobgoblin() is not None or event_signal.pending(), 6000)
        return hobgoblin() is not None
    log(f'ikov: walking to the hobgoblins at ({IKOV_TILE.HOBGOBLINS.x},{IKOV_TILE.HOBGOBLINS.z})')
    _result16 = yield from traversal.walk_resilient(IKOV_TILE.HOBGOBLINS, radius=4, attempts=3, timeout_ms=420000, log=log)
    return _result16


# Why: the warrior fight leaves the yew shortbow worn over an empty quiver, and it answers every Attack click with "There is no ammo left in your quiver".
def armed_for_melee():
    worn = equipment.items()
    weapon = ([item for item in worn if item.slot == WEAPON_SLOT] or [None])[0]
    if not weapon:
        return False
    if not ((weapon.name if weapon.name is not None else '').lower().endswith('bow')):
        return True
    return any([item.slot == AMMO_SLOT and item.count >= FARM_ARROWS for item in worn])


def stow_empty_bow(log):
    """Take the spent bow off; fists beat a bow with no arrows."""
    log('ikov: stowing the empty yew shortbow — it cannot swing at a hobgoblin')
    _result17 = yield from equipment.unequip(IKOV_NAME.YEW_SHORTBOW)
    return _result17


# Why: the crossing kit leaves the bot bare-handed against level-42 hobgoblins, and the axe the yew was cut with is banked and is a weapon.
def arm_for_the_farm(snap):
    # Why: a spent bow still fills the weapon slot, so it comes off before anything is picked to replace it.
    if not armed_for_melee() and equipment.contains(IKOV_NAME.YEW_SHORTBOW):
        return Record({'kind': 'custom', 'name': 'stow the empty bow', 'run': stow_empty_bow})
    # Why: the best weapon in the bank beats the axe the yew was cut with.
    better = melee_weapon_step(snap)
    if better:
        return better
    # Why: an armed bot keeps whatever it's already holding.
    if armed_for_melee():
        return None
    _v18 = (snap.inv_ids.get(IKOV_OBJ.IRON_AXE) if snap.inv_ids is not None else None)
    if ((_v18 if _v18 is not None else 0)) > 0:
        return Record({'kind': 'equip', 'item': IKOV_NAME.IRON_AXE})
    _v19 = (snap.bank_ids.get(IKOV_OBJ.IRON_AXE) if snap.bank_ids is not None else None)
    if ((_v19 if _v19 is not None else 0)) > 0:
        return Record({
            'kind': 'withdraw',
            'items': [{'name': IKOV_NAME.IRON_AXE, 'id': IKOV_OBJ.IRON_AXE, 'qty': 1}],
        })
    # Why: a run resumed at this stage never walked the sourcing leg, so the axe it would have banked was never bought.
    _v20 = snap.inv.get('coins')
    if snap.bank_coins + ((_v20 if _v20 is not None else 0)) >= AXE_GP:
        return Record({
            'kind': 'buy',
            'item': IKOV_NAME.IRON_AXE,
            'qty': 1,
            'shop': Record({'npc': 'Aemad', 'anchor': IKOV_TILE.AEMAD}),
            'est_gp': AXE_GP,
        })
    return None


# Why: the engine's food float is a one-shot at provisioning and both fights outlast it.
def restock_step(snap, want, floor):
    """Walk to a booth for more lobsters once the pack is down to `floor`, or null when it is stocked."""
    food = IKOV_NAME.LOBSTER.lower()
    _v21 = snap.inv.get(food)
    held = (_v21 if _v21 is not None else 0)
    if held >= floor:
        return None
    _v22 = (snap.bank.get(food) if snap.bank is not None else None)
    qty = min(want - held, (_v22 if _v22 is not None else 0))
    if qty <= 0:
        return None
    return Record({'kind': 'withdraw', 'items': [{'name': IKOV_NAME.LOBSTER, 'qty': qty}]})


# Why: hobgoblins are aggressive, so the retreat has to clear their radius; standing still in the camp with no food dies before the watchdog fires.
def leave_the_camp(log):
    """Walk out of the camp when there is no food left anywhere to farm it with."""
    log('ikov: no food in the pack or the bank — leaving the hobgoblin camp')
    yield from traversal.walk_resilient(IKOV_TILE.HOBGOBLIN_RETREAT, radius=3, attempts=2, timeout_ms=180000, log=log)
    return False


def foodless(snap):
    food = IKOV_NAME.LOBSTER.lower()
    banked = snap.bank.get(food, 0) if snap.bank is not None else 0
    return snap.inv.get(food, 0) == 0 and banked == 0


# Why: 20 unstackable roots plus food fill the pack, so the farm banks in batches.
# Why: the camp is 3 level-42 attackers at once and a resumed run never walked the leg that put armour on, so it's checked here too.
def root_step(snap):
    _v24 = ranged_armour_step(snap)
    _v25 = (_v24 if _v24 is not None else arm_for_the_farm(snap))
    arm = (_v25 if _v25 is not None else restock_step(snap, FARM_FOOD, FARM_FOOD_FLOOR))
    if arm:
        return arm
    _v26 = (snap.inv_ids.get(IKOV_OBJ.LIMPWURT_ROOT) if snap.inv_ids is not None else None)
    held = (_v26 if _v26 is not None else 0)
    _v27 = (snap.bank_ids.get(IKOV_OBJ.LIMPWURT_ROOT) if snap.bank_ids is not None else None)
    banked = (_v27 if _v27 is not None else 0)
    if held > 0 and (banked + held >= ROOTS_WANTED or ((snap.free_slots if snap.free_slots is not None else 28)) <= 2):
        return Record({'kind': 'deposit', 'keep': [IKOV_NAME.LOBSTER, 'coins'], 'exact_keep': True})
    if foodless(snap):
        return Record({'kind': 'custom', 'name': 'leave the hobgoblin camp', 'run': leave_the_camp})
    return Record({'kind': 'custom', 'name': f'farm limpwurt roots ({banked + held}/{ROOTS_WANTED})', 'run': farm_roots})


def supplies_step(snap, candle, bow, roots, fletching_level=None):
    """The next surface acquisition for the wanted parts of the kit, or null when they are all in hand."""
    need_bow = bow and held_or_banked(snap, IKOV_OBJ.YEW_SHORTBOW) == 0
    if need_bow and fletching_level is not None and fletching_level < 65:
        return Record({'kind': 'wait', 'reason': 'need Fletching 65 to make a Yew shortbow, or a banked Yew shortbow'})
    # Why: Aemad's is in East Ardougne and the rest of the kit is a Catherby-Seers loop, so the axe is bought on the way out.
    if need_bow and axe_outstanding(snap):
        return Record({
            'kind': 'buy',
            'item': IKOV_NAME.IRON_AXE,
            'qty': 1,
            'shop': Record({'npc': 'Aemad', 'anchor': IKOV_TILE.AEMAD}),
            'est_gp': AXE_GP,
        })
    if candle and not kit_candle_ready(snap):
        if held_or_banked(snap, IKOV_OBJ.TINDERBOX) == 0:
            return Record({
                'kind': 'buy',
                'item': IKOV_NAME.TINDERBOX,
                'qty': 1,
                'shop': Record({'npc': 'Arhein', 'anchor': IKOV_TILE.ARHEIN}),
                'est_gp': 100,
            })
        return Record({
            'kind': 'buy',
            'item': IKOV_NAME.CANDLE,
            'qty': 1,
            'shop': Record({'npc': 'Candle maker', 'anchor': IKOV_TILE.CANDLE_MAKER}),
            'est_gp': 100,
        })
    if need_bow:
        bow_step = bow_chain_step(snap)
        if bow_step:
            return bow_step
    # Why: the web over the boots needs the knife, and only the bow chain fetched one, so a death after the bow is made left the errand cutting with nothing.
    if candle and held_or_banked(snap, IKOV_OBJ.KNIFE) == 0:
        return Record({
            'kind': 'grab_ground',
            'item': IKOV_NAME.KNIFE,
            'anchor': IKOV_TILE.KNIFE_SPAWN,
            'wait_if_missing': True,
        })
    if roots and held_or_banked(snap, IKOV_OBJ.LIMPWURT_ROOT) < ROOTS_WANTED:
        return root_step(snap)
    return None


# Why: a withdraw step fails when any line comes up short, so don't ask for something already in the pack.
def _id_count(counts, id):
    return counts.get(id, 0) if counts is not None else 0


def withdraw_missing(snap, wanted):
    """Withdraw only the listed items the pack is short of and the bank can cover."""
    short = [item for item in wanted if _id_count(snap.inv_ids, item.id) == 0 and _id_count(snap.bank_ids, item.id) > 0]
    if len(short) == 0:
        return None
    return Record({'kind': 'withdraw', 'items': [{'name': item.name, 'id': item.id, 'qty': 1} for item in short]})


def axe_outstanding(snap):
    """True while an axe still has to be bought: no bow stave in sight, no logs, and nothing to cut one with."""
    return held_or_banked(snap, IKOV_OBJ.UNSTRUNG_YEW_SHORTBOW) == 0 and held_or_banked(snap, IKOV_OBJ.YEW_LOGS) == 0 and held_or_banked(snap, IKOV_OBJ.IRON_AXE) == 0


# Why: the order is a west-to-east sweep: Aemad's, then Catherby for the candle and yews, then Seers for the knife, flax and wheel.
def bow_chain_step(snap):
    stave = held_or_banked(snap, IKOV_OBJ.UNSTRUNG_YEW_SHORTBOW)
    string = held_or_banked(snap, IKOV_OBJ.BOW_STRING)
    if stave > 0 and string > 0:
        carry = withdraw_missing(snap, [
            Record({'name': IKOV_NAME.UNSTRUNG_YEW_SHORTBOW, 'id': IKOV_OBJ.UNSTRUNG_YEW_SHORTBOW}),
            Record({'name': IKOV_NAME.BOW_STRING, 'id': IKOV_OBJ.BOW_STRING}),
        ])
        return (carry if carry is not None else Record({'kind': 'custom', 'name': 'string the yew shortbow', 'run': string_bow}))
    if stave == 0 and held_or_banked(snap, IKOV_OBJ.YEW_LOGS) == 0:
        axe = withdraw_missing(snap, [Record({'name': IKOV_NAME.IRON_AXE, 'id': IKOV_OBJ.IRON_AXE})])
        return (axe if axe is not None else Record({'kind': 'custom', 'name': 'chop a yew log', 'run': chop_yew}))
    if held_or_banked(snap, IKOV_OBJ.KNIFE) == 0:
        return Record({
            'kind': 'grab_ground',
            'item': IKOV_NAME.KNIFE,
            'anchor': IKOV_TILE.KNIFE_SPAWN,
            'wait_if_missing': True,
        })
    if string == 0:
        if held_or_banked(snap, IKOV_OBJ.FLAX) == 0:
            return Record({'kind': 'custom', 'name': 'pick flax', 'run': pick_flax})
        flax = withdraw_missing(snap, [Record({'name': IKOV_NAME.FLAX, 'id': IKOV_OBJ.FLAX})])
        if flax:
            return flax
        return Record({
            'kind': 'use_on',
            'item': IKOV_NAME.FLAX,
            'target_kind': 'loc',
            'target': 'Spinning wheel',
            'anchor': IKOV_TILE.SPINNING_WHEEL,
            'product': IKOV_NAME.BOW_STRING,
        })
    if stave == 0:
        kit = withdraw_missing(snap, [
            Record({'name': IKOV_NAME.YEW_LOGS, 'id': IKOV_OBJ.YEW_LOGS}),
            Record({'name': IKOV_NAME.KNIFE, 'id': IKOV_OBJ.KNIFE}),
        ])
        return (kit if kit is not None else Record({'kind': 'custom', 'name': 'fletch a yew shortbow', 'run': fletch_bow}))
    return None


def sourcing_shortfall():
    short = [req for req in IKOV_SOURCING_SKILLS if skills.level(req.skill) < req.level]
    if len(short) == 0:
        return None
    return f"Temple of Ikov sources its own yew shortbow — needs {', '.join([f'{s.skill} {s.level}' for s in short])}"
