"""Ported from rs2b0t's src/bot/api/ai/quests/defs/tbwt/crafting.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.catalogs.tables import CANT_LIGHT
from rs2004.catalogs.tasks import sustain
from rs2004.entities import ground_items, locs, npcs
from rs2004.game import game, skills
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.messages import game_messages
from rs2004.quests.defs.tbwt.areas import TB_ID, TB_LOC, TB_NAME, TB_NPC, TB_TILE
from rs2004.quests.defs.tbwt.loadout import food_forms_for_quest
from rs2004.quests.defs.tbwt.talk import walk_to
from rs2004.quests.exec.prompts import settle_scene, use_on_loc
from rs2004.trade import shop
from rs2004.traversal import traversal

__all__ = ['combine', 'take_ground', 'fish_karambwanji', 'fish_karambwan', 'load_vessel', 'pick_banana', 'buy_rum', 'cook_on_fire', 'grind', 'poison_spear', 'make_sandwich', 'paste_bones', 'kill_for', 'burn_jogre_bones']


def held_id(id):
    return sum([i.count for i in [i for i in inventory.items() if i.id == id]])


def combine(use_id, target_id, product_id, log):
    """Use one carried item on another and wait for the product to land."""
    if held_id(product_id) > 0:
        return True
    use = ([i for i in inventory.items() if i.id == use_id] or [None])[0]
    target = ([i for i in inventory.items() if i.id == target_id] or [None])[0]
    if not use or not target:
        log(f'pack is missing item {(target_id if use else use_id)}')
        return False
    if not (use.use_on(target)):
        return False
    _result1 = yield from execution.delay_until(lambda: held_id(product_id) > 0, 10000)
    return _result1


def held_any(ids):
    return sum([held_id(id) for id in ids])


def food_held():
    return sum([inventory.count(name) for name in food_forms_for_quest()])


def quiet(message):
    pass


def take_ground(ids, name, log):
    """Take the nearest drop matching any of `ids`; false when there is nothing to take yet."""
    drop = ground_items.query().where(lambda g: (g.id in ids)).within(14).nearest()
    if not drop:
        log(f'no \'{name}\' on the ground within 14 tiles')
        return False
    before = held_any(ids)
    if not (drop.interact('Take')):
        return False
    _result2 = yield from execution.delay_until(lambda: held_any(ids) > before, 8000)
    return _result2


# Why: the shoal is an NPC with `op1=Net`, and each cast is a fresh interaction.
def fish_karambwanji(want):
    """Net Karambwanji until the pack holds `want` of them, or has no room left."""

    def _fn3(log):
        if want <= 0:
            return False
        if held_id(TB_ID.RAW_KARAMBWANJI) >= want:
            return True
        if inventory.free() < 1:
            log('Karambwanji catch needs a free inventory slot')
            return False
        _w4 = yield from walk_to(TB_TILE.KARAMBWANJI_SHOAL, 5, log)
        if not (_w4):
            return False
        yield from settle_scene()
        for cast in range(60):
            yield from sustain.run()
            # The shoal yields shrimp as well, and a pack of them is a pack with no room for bait.
            shrimp = inventory.first(TB_NAME.RAW_SHRIMP)
            if shrimp:
                shrimp.interact('Drop')
                yield from execution.delay_ticks(1)
                continue
            if held_id(TB_ID.RAW_KARAMBWANJI) >= want or inventory.free() < 1:
                break
            spot = npcs.query().name(TB_NPC.FISHING_SPOT).action('Net').within(8).nearest()
            if not spot:
                log('no Karambwanji shoal in reach of the Holy Lake stand')
                return False
            before = held_id(TB_ID.RAW_KARAMBWANJI)
            if not (spot.interact('Net')):
                return False
            yield from execution.delay_until(lambda: held_id(TB_ID.RAW_KARAMBWANJI) > before, 20000)
        return held_id(TB_ID.RAW_KARAMBWANJI) >= want
    return _fn3


# Why: a raw Karambwan burns 3 times in 10 and the shoal is 160 tiles from the Holy Lake bait, so a spare caught now is cheaper than a second round trip.
def fish_karambwan(want=2):
    """Lower the loaded vessel at Lubufu's spot until `want` Karambwan come up, or the bait runs out."""

    def _fn5(log):
        target = want
        if held_id(TB_ID.RAW_KARAMBWAN) >= target:
            return True
        if skills.level('fishing') < 65:
            log('replacement Karambwan requires 65 Fishing')
            return False
        if inventory.free() < 1:
            log('Karambwan catch needs a free inventory slot')
            return False
        _w6 = yield from walk_to(TB_TILE.KARAMBWAN_SHOAL, 5, log)
        if not (_w6):
            return False
        yield from settle_scene()
        for attempt in range(24):
            if not (held_id(TB_ID.RAW_KARAMBWAN) < target):
                break
            yield from sustain.run()
            _c7 = held_id(TB_ID.VESSEL_LOADED) == 0
            if _c7:
                _w8 = yield from load_vessel(log)
                _c7 = not (_w8)
            if _c7:
                break
            if inventory.free() < 1:
                log('Karambwan catch needs a free inventory slot')
                return False
            spot = npcs.query().name(TB_NPC.FISHING_SPOT).action('Fish').within(8).nearest()
            if not spot:
                log("no Karambwan shoal in reach of Lubufu's stand")
                return False
            if not (spot.interact('Fish')):
                return False
            yield from execution.delay_until(lambda: held_id(TB_ID.RAW_KARAMBWAN) >= target or held_id(TB_ID.VESSEL_LOADED) == 0, 20000)
        return held_id(TB_ID.RAW_KARAMBWAN) > 0
    return _fn5


def load_vessel(log):
    """Bait the vessel; needs one raw Karambwanji in the pack."""
    if held_id(TB_ID.VESSEL_LOADED) > 0:
        return True
    _result9 = yield from combine(TB_ID.RAW_KARAMBWANJI, TB_ID.VESSEL, TB_ID.VESSEL_LOADED, log)
    return _result9


def pick_banana(log):
    if held_id(TB_ID.BANANA) > 0 or held_id(TB_ID.SLICED_BANANA) > 0:
        return True
    _w10 = yield from walk_to(TB_TILE.BANANA_PLANTATION, 4, log)
    if not (_w10):
        return False
    yield from settle_scene()
    for tries in range(8):
        if not (held_id(TB_ID.BANANA) == 0):
            break
        tree = locs.query().name(TB_LOC.BANANA_TREE).action('Search').within(10).nearest()
        if not tree:
            log('no Banana Tree with a Search op in the plantation')
            return False
        if not (tree.interact('Search')):
            return False
        yield from execution.delay_until(lambda: held_id(TB_ID.BANANA) > 0, 6000)
    return held_id(TB_ID.BANANA) > 0


# Why: 3 different objects render as "Karamjan rum", so the purchase is counted by id.
def buy_rum(log):
    """Zambo's bar in Musa Point is the only Karamjan rum on the island."""
    if held_id(TB_ID.RUM) > 0 or held_id(TB_ID.RUM_SLICED) > 0:
        return True
    _w11 = yield from walk_to(TB_TILE.ZAMBO, 3, log)
    if not (_w11):
        return False
    yield from settle_scene()
    _w12 = yield from shop.open(TB_NPC.ZAMBO)
    if not (_w12):
        log("could not open Zambo's shop")
        return False
    yield from shop.buy(TB_NAME.RUM, 1)
    yield from shop.close()
    _result13 = yield from execution.delay_until(lambda: held_id(TB_ID.RUM) > 0, 6000)
    return _result13


def cook_on_fire(item_id, product_id, what):
    """Cook one item on the permanent jungle fire south of the village."""

    def _fn14(log):
        raw = item_id
        cooked = product_id
        if held_id(cooked) > 0:
            return True
        if held_id(raw) == 0:
            log(f'no {what} in the pack to cook')
            return False
        # Why: a raw Karambwan burns 3 times in 10, so the wait also ends when the input is gone.
        yield from use_on_loc(raw, Record({'name': TB_LOC.FIRE, 'near': TB_TILE.FIRE, 'within': 8}), [], lambda: held_id(cooked) > 0 or held_id(raw) == 0, log)
        if held_id(cooked) > 0:
            return True
        if held_id(raw) > 0:
            log(f'the fire did not answer the {what}')
            return False
        log(f'the {what} burned — sourcing another')
        ruined = ([i for i in inventory.items() if i.id == TB_ID.BURNT_KARAMBWAN] or [None])[0]
        if ruined:
            ruined.interact('Drop')
        return False
    return _fn14


def grind(item_id, product_id):
    """Grind one carried item with the pestle and mortar."""
    return lambda log: combine(TB_ID.PESTLE, item_id, product_id, log)


# Why: only `[opheldu,tbwt_poisonous_karambwan_paste]` answers, so the spear is used on the paste; the other way round hits `_weapon_spear`'s silent default.
def poison_spear(spear):
    """Smear the poisonous paste over whichever spear the pack is carrying."""
    return lambda log: combine(spear.id, TB_ID.KARAMBWAN_POISON_PASTE, spear.kp_id, log)


def make_sandwich(log):
    return combine(TB_ID.SEAWEED, TB_ID.MONKEY_SKIN, TB_ID.SANDWICH, log)


def paste_bones(log):
    return combine(TB_ID.BURNT_JOGRE_BONES, TB_ID.KARAMBWANJI_PASTE, TB_ID.PASTY_JOGRE_BONES, log)


# Why: the monkey deflects every melee swing while the quest is live (`opnpc2,monkey`), so the bow is worn from the start.
# Why: Jogre bones fall from every corpse but a spear falls 4 times in 129, so `kills` lets a hunt outlast one kill.
def kill_for(npc_name, anchor, drop_ids, drop_name, kills=1):
    """Kill up to `kills` of one NPC, stopping as soon as one of `dropIds` is in the pack."""

    def _fn15(log):
        for kill in range(kills):
            if held_any(drop_ids) > 0:
                return True
            _w16 = yield from take_ground(drop_ids, drop_name, quiet)
            if _w16:
                return True
            # A hunt that outlives the food dies in the jungle.
            if kill > 0 and food_held() == 0:
                log(f'out of food {kill} kills into the {npc_name} hunt — banking before the next one')
                return False
            _w17 = yield from walk_to(anchor, 5, log)
            if not (_w17):
                return False
            yield from settle_scene()
            victim = npcs.query().name(npc_name).action('Attack').where(lambda n: not n.targets_another_player()).within(12).nearest()
            if not victim:
                log(f'no {npc_name} within 12 tiles of the stand')
                return False
            index = victim.index
            if not (victim.interact('Attack')):
                return False
            # Hold this one until it dies: `Game.inCombat()` reads our own bar, so a decoy landing a hit would end the wait.
            deadline = _core.step_time() + 120000
            while _core.step_time() < deadline:
                yield from sustain.run()
                if not any([n.index == index for n in npcs.all()]):
                    break
                yield from execution.delay_ticks(1)
            yield from execution.delay_ticks(2)
            yield from take_ground(drop_ids, drop_name, quiet)
        if held_any(drop_ids) > 0:
            return True
        log((f'the {npc_name} left no \'{drop_name}\' within 14 tiles' if kills == 1 else f'{kills} {npc_name}s died without dropping \'{drop_name}\''))
        return False
    return _fn15


# Why: `light_jogre_bones_inv` drops the bones at the player's tile, lights them 3 ticks later, then burns for 25-50 ticks before `obj_addall` puts the burnt bones back on the ground.
# Why: a walktrigger clears the timer, so nothing may move until the fire catches.
def burn_jogre_bones(log):
    """Burn Jogre bones with the tinderbox and pick the burnt ones back up."""
    if held_id(TB_ID.BURNT_JOGRE_BONES) > 0:
        return True
    _w18 = yield from take_ground([TB_ID.BURNT_JOGRE_BONES], TB_NAME.BURNT_JOGRE_BONES, quiet)
    if _w18:
        return True
    # Why: lighting drops the bones on the floor first, so a lost roll leaves them there.
    if held_id(TB_ID.JOGRE_BONES) == 0:
        yield from take_ground([TB_ID.JOGRE_BONES], TB_NAME.JOGRE_BONES, quiet)
    bones = ([i for i in inventory.items() if i.id == TB_ID.JOGRE_BONES] or [None])[0]
    tinderbox = ([i for i in inventory.items() if i.id == TB_ID.TINDERBOX] or [None])[0]
    if not bones or not tinderbox:
        log('need both Jogre bones and a Tinderbox to burn them')
        return False
    mark = game_messages.mark()
    if not (bones.use_on(tinderbox)):
        return False
    # Why: a tile that already carries a loc refuses with a chat line and nothing else, so read the refusal; waiting it out costs 90 seconds per attempt.
    _w19 = yield from execution.delay_until(lambda: game_messages.saw_since(mark, CANT_LIGHT), 3000)
    if _w19:
        here = game.tile()
        log(f'cannot light a fire at ({(here.x if here is not None else None)},{(here.z if here is not None else None)}) — stepping aside')
        if here:
            yield from traversal.walk_resilient(Tile(here.x + 2, here.z + 1, here.level), radius=0, attempts=1, log=log)
        return False
    at = game.tile()
    lit = yield from execution.delay_until(lambda: ground_items.query().where(lambda g: g.id == TB_ID.BURNT_JOGRE_BONES).within(6).exists(), 90000)
    if not lit:
        log(f'the bones never caught at ({(at.x if at is not None else None)},{(at.z if at is not None else None)}) — the roll never landed')
        return False
    _result20 = yield from take_ground([TB_ID.BURNT_JOGRE_BONES], TB_NAME.BURNT_JOGRE_BONES, log)
    return _result20

from rs2004.quests.defs.tbwt.loadout import food_forms_for_quest
