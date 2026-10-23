"""Rules on what the backpack holds: what matches a list of names, and when to bank, restock, eat or flee.
Ported from rs2b0t's api/inventory/packRules.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.combat import should_eat_to_use_food


def matches_any(name, patterns):
    """Whether the name holds any of the patterns, by part, without regard to case. Blank patterns match nothing."""
    if name is None:
        return False
    lower = name.lower()
    return len([p for p in patterns if p.strip() and p.strip().lower() in lower]) > 0


def count_matching(items, patterns):
    """How many of the matching items there are, stacks counted in full."""
    return sum([i.count for i in items if matches_any(i.name, patterns)])


def slots_matching(items, patterns):
    """How many slots hold a matching item."""
    return len([i for i in items if matches_any(i.name, patterns)])


def should_bank(loot_slots, bank_at, inv_full):
    """Bank at bank_at slots of loot, or as soon as the backpack is full with any."""
    return loot_slots >= bank_at or (inv_full and loot_slots > 0)


def should_restock(food_count, threshold):
    return food_count < threshold


def should_eat(hp, max_hp, heal, food_count):
    """Eat when a bite of heal fits in full, or hitpoints are at the floor; should_eat_food takes the food's name."""
    return should_eat_to_use_food(hp, max_hp, heal, food_count)


def should_panic(hp_fraction, gate, food_count):
    """Run when hitpoints are below the gate with no food left."""
    return hp_fraction < gate and food_count == 0
