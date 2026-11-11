"""Ported from rs2b0t's src/bot/scripts/AccountLeveler/loot.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs import HERBS
from rs2004.catalogs._drops import DROP_DB

__all__ = ['SECONDARY_LOOT']

from bots.account_leveler.catalog import POTIONS

SECONDARY_LOOT = ['Herb', 'Unicorn horn'] + [herb.name for herb in HERBS] + [potion.secondary for potion in POTIONS]
for drops in DROP_DB.values():
    SECONDARY_LOOT.extend([item for item in drops if item.endswith(' rune')])
SECONDARY_LOOT = list(set(SECONDARY_LOOT))
