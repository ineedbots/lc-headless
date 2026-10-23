"""The miner's food and camp decisions: rs2b0t's scripts/GatheringBot/MinerLogic.ts (MIT, see thirdparty/rs2b0t)."""

import math

from rs2004.catalogs import FOOD_OPTIONS, MIN_EAT_HP, Record

from bots.gathering.camp import is_number

MINER_FOOD_SETTINGS = {
    'food': SettingDef('string', 'Lobster', 'Food', options=FOOD_OPTIONS, group='Food & healing',
                       help='Eaten at the bank or mine when its full heal fits. Bank mode also eats for ore slots; power mode keeps food for healing.'),
    'food_withdraw': SettingDef('number', 0, 'Food to withdraw', 0, 27, group='Food & healing',
                                help='Exact food target for each trip, replenished after bank healing. 0 carries no food; the selected food is still used to heal at the bank.'),
}


def desert_camp_food_reserved_slots(route_supply_slots):
    return max(0, math.floor(route_supply_slots)) + 1


def desert_camp_food_reserve_depleted(food_count):
    return food_count <= 1


def unsupported_camp_ores(selected, supported):
    if not supported:
        return []
    available = [name.strip().lower() for name in supported]
    return [name for name in selected if name.strip().lower() not in available]


def miner_food_config(name, target):
    """The miner's food settings as a trip's Record of name and target, or None for no food."""
    normalized = name.strip()
    if len(normalized) == 0 or not is_number(target):
        return None
    count = max(0, min(27, math.floor(target)))
    return Record({'name': normalized, 'target': count}) if count > 0 else None


def should_eat_miner_food(hp, max_hp, heal, food_count, inventory_full, retain_for_travel=False, hazard_max_hit=None):
    if food_count <= 0:
        return False
    if inventory_full and not retain_for_travel:
        return True
    if hp <= 0 or max_hp <= 0 or heal <= 0:
        return False
    hazard_floor = min(max_hp - 1, max(0, math.floor(hazard_max_hit or 0)))
    if hp <= max(MIN_EAT_HP, hazard_floor):
        return True
    return hp + heal <= max_hp


def plan_miner_food_withdrawal(target, held, banked, free_slots, reserved_slots=0):
    """An exact top-up, refusing a short bank or a cramped pack: a Record of ok and withdraw, with reason
    ('pack-space' or 'bank-stock') and missing when it isn't ok."""
    target = max(0, math.floor(target))
    held = max(0, math.floor(held))
    banked = max(0, math.floor(banked))
    raw_free = max(0, math.floor(free_slots))
    reserved = max(0, math.floor(reserved_slots or 0))
    if reserved > raw_free:
        return Record({'ok': False, 'withdraw': 0, 'reason': 'pack-space', 'missing': reserved - raw_free})
    free = raw_free - reserved
    shortfall = max(0, target - held)
    if shortfall == 0:
        return Record({'ok': True, 'withdraw': 0})
    if held + free < target:
        return Record({'ok': False, 'withdraw': 0, 'reason': 'pack-space', 'missing': target - held - free})
    if held + banked < target:
        return Record({'ok': False, 'withdraw': 0, 'reason': 'bank-stock', 'missing': target - held - banked})
    return Record({'ok': True, 'withdraw': shortfall})


def miner_food_restock_needed(configured, food_count, startup_pending):
    """Restocks once at the start, then only once the food carried is eaten."""
    return configured and (startup_pending or food_count <= 0)
