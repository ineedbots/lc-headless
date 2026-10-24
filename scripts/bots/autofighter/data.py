"""AutoFighter's options and pure decisions: rs2b0t's scripts/AutoFighter/AutoFighterData.ts (MIT, see
thirdparty/rs2b0t)."""

START_POSITION = 'Start position'
CUSTOM_COORDINATES = 'Custom coordinates'
SPOT_OPTIONS = [START_POSITION, CUSTOM_COORDINATES]
BANKING_OPTIONS = ['Auto', 'None']
# The nearest unlocked bank, or a named one.
BANK_LOCATION_OPTIONS = ['Nearest'] + [b['name'] for b in BANK_LOCATIONS]
DEFAULT_CUSTOM_SPOT = Tile(3273, 3427, 0)
BURIAL_BONE_NAME = 'Bones'


def resolve_killing_spot(mode, start, custom):
    chosen = custom if mode.strip().lower() == CUSTOM_COORDINATES.lower() else start
    return Tile(chosen.x, chosen.z, chosen.level)


def auto_bank_enabled(mode):
    return mode.strip().lower() == 'auto'


def should_bank_after_minutes(auto_bank, every_minutes, minutes_since_last_bank, loot_count):
    """CowKiller's timed bank: auto banking, a positive interval, loot in the pack, and the time up."""
    if not auto_bank or every_minutes <= 0 or loot_count <= 0:
        return False
    return minutes_since_last_bank >= every_minutes


def is_burial_bone(name, bury_bones=True, bury_big_bones=False):
    normalized = name.strip().lower() if name is not None else None
    return (bury_bones and normalized == BURIAL_BONE_NAME.lower()) or (bury_big_bones and normalized == 'big bones')


def wants_auto_fighter_loot(name, configured, bury_bones, bury_big_bones=False):
    normalized = name.strip().lower() if name is not None else None
    listed = normalized is not None and len([entry for entry in configured if entry.strip().lower() == normalized]) > 0
    return listed or is_burial_bone(name, bury_bones, bury_big_bones)


# Why: Fight's validate is false while in combat, so with retaliate off an attacking random event (strange fruit)
# never gets a new target.
def auto_retaliate_should_enable(on):
    return not on


def assert_auto_retaliate_on(on):
    if not on:
        raise RuntimeError('[AutoFighter] could not enable Auto Retaliate')


def special_available(enabled, style, cost):
    """A weapon with a special is in hand and specials are on. Spells never spec."""
    return enabled and style != 'mage' and cost is not None


def should_arm_special(enabled, style, cost, energy, armed):
    """Arm when the wielded weapon's special is affordable and the last one is already spent."""
    return special_available(enabled, style, cost) and not armed and energy >= (cost if cost is not None else 0)


def should_bury_regular_bones(enabled, in_combat, bank_open, bone_count, inventory_full):
    # A full backpack deliberately doesn't block it: burying makes the slot the next drop needs.
    return enabled and not in_combat and not bank_open and bone_count > 0


DEFAULT_LOOT = [
    'clue scroll',
    'uncut sapphire', 'uncut emerald', 'uncut ruby', 'uncut diamond',
    'half of a key',
    'chaos talisman', 'nature talisman',
]
