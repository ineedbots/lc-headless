"""JiveKBD's poison clock: rs2b0t's scripts/JiveKBD/logic.ts (MIT, see thirdparty/rs2b0t). The poison kit is the
hunting framework's, and is passed through for this module's importers."""

from rs2004.hunting.supply import ANTIPOISON_DOSES, ANTIPOISON_LABEL, POISONED, antipoison_plan, dose_to_drink

# Ticks a super antipoison holds the poison counter below zero.
IMMUNE_TICKS = 600
# Ticks kept back, so the lever is pulled inside the window rather than on its edge.
DOSE_MARGIN_TICKS = 100


# Why: the poison varp isn't sent to the client, so the only clock on the immunity is the bot's own record of the
# last drink.
def dose_due(last_dose_tick, now):
    """Whether a dose is owed before the walk past the lever spiders."""
    return last_dose_tick is None or now - last_dose_tick >= IMMUNE_TICKS - DOSE_MARGIN_TICKS
