"""What teleports a trail can carry: rs2b0t's api/ai/clues/teleportKit.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.routeplan import meets_requires, teleports


class TeleportKit:
    """runes: (name, per_cast) of each rune the castable spells take, the hungriest spell's count. jewellery_prefixes:
    the jewellery the account may rub, as lower-case name prefixes, since charges show as "Amulet of glory(4)".
    usable: the spell teleport ids the account can cast."""

    def __init__(self, runes, jewellery_prefixes, usable):
        self.runes = runes
        self.jewellery_prefixes = jewellery_prefixes
        self.usable = usable


# Why: runes and pack space are left out because stocking fills that gap, and checking them here would keep every
# kit empty.
def _castable(dest, state):
    """Whether the account could use the destination if it held the runes: magic level, members, quests."""
    if dest.get('family') == 'lever':
        return False
    requires = {k: v for k, v in (dest.get('requires') or {}).items() if k != 'items' and k != 'freeSlots'}
    ok, _ = meets_requires(requires, state)
    return ok


# Why: derived from the catalog so a new destination can't leave its runes being banked, and gated on what the
# account can cast so a low-magic trail doesn't carry four spellbooks' worth of dead runes.
def teleport_kit_for(state, catalog=None):
    """The teleport kit for an account, from world_state()."""
    runes = {}
    jewellery = set()
    usable = []
    for dest in (catalog if catalog is not None else teleports()):
        if not _castable(dest, state):
            continue
        if dest.get('family') == 'spell':
            usable.append(dest['teleportId'])
        for item in (dest.get('requires') or {}).get('items') or []:
            runes[item['name']] = max(runes.get(item['name'], 0), item['count'])
        for name in dest.get('itemNameMatch') or []:
            jewellery.add(name.lower())
    return TeleportKit([(name, runes[name]) for name in sorted(runes.keys())], sorted(jewellery), usable)


def is_teleport_item(name, kit):
    """Whether an item is part of the kit and mustn't be banked."""
    n = name.lower()
    return any([rune.lower() == n for rune, _ in kit.runes]) or any([n.startswith(p) for p in kit.jewellery_prefixes])
