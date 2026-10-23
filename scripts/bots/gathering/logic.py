"""GatheringBot's pure decisions on combat, yielding a gather and the bait shop: rs2b0t's
scripts/GatheringBot/GatheringBotLogic.ts (MIT, see thirdparty/rs2b0t). The feather buyout's cost (feather_coins_to_draw,
FEATHER_BUYOUT_GP) comes with the shop pricing of phase 13."""

import math

from rs2004.catalogs import Record

from bots.gathering.tick_manip import combat_breaks_gather

# Why: Roachey restocks a feather a tick toward 1500, so a full buyout is back in fifteen minutes.
FEATHER_RESTOCK_MINUTES = 15
FEATHER_STOCK = 1500
ROACHEY_SELL_MULTIPLIER = 1000
ROACHEY_DELTA = 10
# Why: at a camp whose bait only a shop sells, Shilo's feathers among them, the bank finds none, so running out is
# a reason to go on its own as well as the clock; an empty shelf or purse would then go every loop, so it's paced
# off the same stamp.
BAIT_RETRY_MINUTES = 1


def wilderness_miner_at(is_miner, tile):
    return is_miner and tile is not None and wilderness_level_at(tile) > 0


# Why: FleeCombat also needs the player's own in_combat, which cuts out idle or following players facing it.
def incoming_player_attacker(loaded_players):
    """Whether a loaded player targets the player; clears as soon as none does."""
    return len([p for p in loaded_players if p.targets_me()]) > 0


def wilderness_miner_stance_needed(is_miner, tile, tick_manip_allow_combat, auto_retaliate_on, desert_camp_miner=False):
    """Whether to set a hostile camp's miner back to not retaliating, after going in or a login."""
    return (wilderness_miner_at(is_miner, tile) or desert_camp_miner) and not tick_manip_allow_combat and auto_retaliate_on


# Why: wilderness and desert camp miners hold their ground through the residents' attacks, and a player's attack
# still sends them running.
def gathering_combat_policy(is_miner, tile, incoming_player_attacker, auto_location, tick_manip_allow_combat, desert_camp_miner=False):
    """The live combat policy: a Record of mode, allow_gather and flee."""
    if desert_camp_miner:
        if incoming_player_attacker:
            return Record({'mode': 'desert-camp-miner-player', 'allow_gather': False, 'flee': True})
        return Record({'mode': 'desert-camp-miner-npc', 'allow_gather': True, 'flee': False})
    if wilderness_miner_at(is_miner, tile):
        if incoming_player_attacker:
            return Record({'mode': 'wilderness-miner-player', 'allow_gather': False, 'flee': True})
        return Record({'mode': 'wilderness-miner-npc', 'allow_gather': True, 'flee': False})
    return Record({'mode': 'standard', 'allow_gather': tick_manip_allow_combat, 'flee': not auto_location and not tick_manip_allow_combat})


def attacker_near(n, r):
    if n.distance() > r or 'Attack' not in n.actions():
        return False
    # On us, or fighting in our face, in a multi-combat pack.
    return n.targets_me() or (n.in_combat and not n.targets_another_player() and n.distance() <= 2)


def hostile_attacker_nearby(loaded_npcs, radius=8):
    """A hostile NPC that should keep it from going back into camp after a kite."""
    r = max(1, math.floor(radius))
    return len([n for n in loaded_npcs if attacker_near(n, r)]) > 0


# Why: a live attacker is required, so stale combat state can't set off a blind kite.
def should_flee_combat(in_combat, event_pending, has_attacker):
    return in_combat and not event_pending and has_attacker


def should_yield_gathering(event_pending, inventory_full, dialog_pending, target_gone, in_combat=False, allow_combat=False):
    return event_pending or inventory_full or dialog_pending or target_gone or combat_breaks_gather(in_combat, allow_combat)


def loc_gather_should_yield(event_pending, inventory_full, dialog_pending, in_combat, allow_combat_gather, should_eat_miner_food, clicked_tile_hazard,
                            no_resource_in_camp):
    if event_pending or inventory_full or dialog_pending or should_eat_miner_food:
        return True
    if combat_breaks_gather(in_combat, allow_combat_gather) or clicked_tile_hazard:
        return True
    return no_resource_in_camp


def ent_abort_action(neighbour_in_reach, neighbour_exists):
    if neighbour_in_reach:
        return 'chop-neighbour'
    if neighbour_exists:
        return 'walk-to-neighbour'
    return 'step-off'


def fishing_session_broken(event_pending, inventory_full, dialog_pending, in_combat, spot_gone, spot_moved, became_whirlpool, allow_combat=False):
    return (event_pending or inventory_full or dialog_pending or combat_breaks_gather(in_combat, allow_combat) or spot_gone or spot_moved
            or became_whirlpool)


def feather_buyout_due(last_at_ms, interval_minutes, now_ms):
    """Whether the feather buyout is owed; the first is owed as soon as the run starts."""
    if interval_minutes <= 0:
        return False
    return last_at_ms is None or now_ms - last_at_ms >= interval_minutes * 60000


def bait_trip_due(has_vendor, out_of_bait, last_at_ms, interval_minutes, now_ms):
    """Whether a trip to the camp's bait shop is owed, on the clock or on an empty pack."""
    if not has_vendor:
        return False
    if feather_buyout_due(last_at_ms, interval_minutes, now_ms):
        return True
    return out_of_bait and feather_buyout_due(last_at_ms, BAIT_RETRY_MINUTES, now_ms)
