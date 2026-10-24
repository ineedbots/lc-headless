"""GreenDragon's pure decisions: rs2b0t's scripts/GreenDragon/GreenDragonLogic.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.hunting.logic import is_clue_obj

# The first wilderness row north of the Edgeville ditch.
WILDY_MIN_Z = 3520

# The hold before walking back after an escape from a threat.
RETURN_HOLD_MS = 60000


def in_wilderness(z):
    return z > WILDY_MIN_Z


# Why: a player killer only registers once auto retaliate points us back at them.
# Why: our face target doesn't decay when they leave, so the wilderness gate is what ends the threat.
def under_player_attack(z, retaliating_at_player):
    """True while a player is attacking us in the wilderness."""
    return z is not None and retaliating_at_player and in_wilderness(z)


def is_clue_like(id):
    """Matched by id, not name: every hard trail is a distinct obj, all showing as "Clue scroll"."""
    return is_clue_obj(id)


class LootFilter:
    """What a ground item must be to be picked up: in loot_set (lower-case names), shared bank junk when
    bank_common, a clue when solve_clues, or the bones to bury."""

    def __init__(self, loot_set, bank_common, solve_clues, bury_bones=False, bone_name=None):
        self.loot_set = loot_set
        self.bank_common = bank_common
        self.solve_clues = solve_clues
        self.bury_bones = bury_bones
        self.bone_name = bone_name


# Why: clues and the bones to bury ignore loot_set, so unticking a loot box can't silently stop clue solving or leave
# the bones you asked to bury.
def wants_ground_item(item, f):
    if f.solve_clues and is_clue_like(item.id):
        return True
    name = item.name or ''
    if len(name) == 0:
        return False
    n = name.lower()
    if f.bury_bones == True and f.bone_name is not None and n == f.bone_name.lower():
        return True
    return n in f.loot_set or (f.bank_common and matches_common_bank_loot(name, item.id))


# Why: only the weapon and shield are set, so armour worn at the start would be banked on the first trip, or taken
# off for an Entrana clue, and never put back on.
def gear_candidates(weapon, shield, tracked):
    """The gear the bot must keep and put back on."""
    out = []
    for name in [weapon, shield] + list(tracked):
        if name != '' and len([seen for seen in out if seen.lower() == name.lower()]) == 0:
            out.append(name)
    return out


# Why: keeping a worn item by name also keeps a looted duplicate from the deposit, and our own armour is on the drop
# table, so the pack fills with helms that never bank.
def gear_to_keep(gear, worn):
    """The gear that earns a keep slot: the pieces currently off."""
    return [n for n in gear if not worn(n)]


# The Chebyshev radius around the bank stand that counts as the flee finished.
AT_BANK_RADIUS = 8


# Why: low hp and no food stay true after arriving, so checking again at the bank walks a zero-tile path and wedges
# the bot on the spot; restocking is the bank run's job, below this task.
def escape_needed(threat, hp_fraction, panic_hp, has_food, at_bank):
    """Whether an escape is still needed; a flee ends at the bank."""
    if threat:
        return True
    return not at_bank and hp_fraction < panic_hp and not has_food


# Why: food is a resource the bot spends, and freeing slots turns it into room, so a pack full of food is no reason
# to bank.
def pack_forces_bank(pack_full, food_count, food_reserve):
    """Whether the pack alone forces the bank trip."""
    return pack_full and food_count <= food_reserve


# Why: carrying a trail's spade, sextant, watch, chart, god page or stray runes back to the dragons wastes slots, so
# holding any forces a bank and restock.
def is_grind_foreign(item, keep, loot):
    """An item that's neither grind kit nor wanted loot. keep holds the lower-case names kept."""
    name = item.name or ''
    if len(name) == 0 or is_clue_like(item.id):
        return False
    if name.lower() in keep:
        return False
    return not wants_ground_item(item, loot)


# Why: eating wins whenever the heal isn't wasted, and at full hp the food is dropped instead.
# Why: the reserve is never dug into; below it the caller falls through to its bank run.
def slot_freeing_action(pack_full, loot_present, food_count, food_reserve, hp_fraction, loot_stacks_into_pack):
    """Trades a food slot for a loot slot rather than walking to the bank: 'eat', 'drop' or 'none'.
    loot_stacks_into_pack: the loot merges into a stack already held, so it needs no slot."""
    if not pack_full or not loot_present or loot_stacks_into_pack:
        return 'none'
    if food_count <= food_reserve:
        return 'none'
    return 'eat' if hp_fraction < 1 else 'drop'
