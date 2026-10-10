"""Loadouts: the gear to wear and the supplies to carry. Ported from rs2b0t's api/loadout (MIT, see
third_party/rs2b0t). rs2b0t keeps loadouts in its panel; here they're settings: a script's 'loadouts' setting
is a list of {name, worn: {slot: item}, carry: [{item, qty}]}, and 'loadout' names the one to use.
"""

SLOTS = ['hat', 'back', 'front', 'righthand', 'torso', 'lefthand', 'legs', 'hands', 'feet', 'ring', 'quiver']


class CarryEntry:
    def __init__(self, item, qty):
        self.item = item
        self.qty = qty

    def __repr__(self):
        return f'CarryEntry({repr(self.item)}, {self.qty})'


class Loadout:
    """name, worn ({slot: item name}) and carry ([CarryEntry])."""

    def __init__(self, name, worn=None, carry=None):
        self.name = name
        self.worn = worn or {}
        self.carry = carry or []

    def __repr__(self):
        return f'Loadout({repr(self.name)})'


def _read_worn(raw):
    out = {}
    if not isinstance(raw, dict):
        return out
    for slot, value in raw.items():
        if slot in SLOTS and isinstance(value, str) and value.strip():
            out[slot] = value
    return out


def _read_carry(raw):
    out = []
    if not isinstance(raw, list):
        return out
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        item = entry.get('item')
        qty = entry.get('qty')
        if isinstance(item, str) and item.strip() and isinstance(qty, (int, float)) and not isinstance(qty, bool) and qty > 0:
            out.append(CarryEntry(item, int(qty)))
    return out


def parse_loadouts(raw):
    """Loadouts from a list of dicts, or JSON text of one, skipping what isn't one; never raises."""
    if isinstance(raw, str):
        if not raw.strip():
            return []
        import json
        try:
            raw = json.loads(raw)
        except Exception:
            return []
    if not isinstance(raw, list):
        return []
    out = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        name = entry.get('name')
        if not isinstance(name, str) or not name.strip():
            continue
        out.append(Loadout(name, _read_worn(entry.get('worn')), _read_carry(entry.get('carry'))))
    return out


def upsert_loadout(loadouts, loadout):
    out = list(loadouts)
    for i in range(len(out)):
        if out[i].name.lower() == loadout.name.lower():
            out[i] = loadout
            return out
    out.append(loadout)
    return out


def remove_loadout(loadouts, name):
    return [l for l in loadouts if l.name.lower() != name.lower()]


def unique_name(loadouts, base):
    taken = [l.name.lower() for l in loadouts]
    if base.lower() not in taken:
        return base
    n = 2
    while f'{base} {n}'.lower() in taken:
        n += 1
    return f'{base} {n}'


def selected_loadout(settings):
    """The loadout settings.loadout names, else the first; None when settings.loadouts defines none."""
    loadouts = parse_loadouts(settings.get('loadouts', []))
    if not loadouts:
        return None
    wanted = str(settings.get('loadout', '') or '').strip().lower()
    for loadout in loadouts:
        if loadout.name.lower() == wanted:
            return loadout
    return loadouts[0]


def _is_food(name):
    import _core
    for id in _core.find_type_ids('item', name):
        item_type = _core.get_item_type(id)
        if item_type is not None and 'Eat' in [op for op in item_type.inventory_ops if op is not None]:
            return True
    return False


def food_of(loadout, fallback, is_food=None):
    """The first carried item that's eaten, as the cache says, or fallback."""
    edible = is_food if is_food is not None else _is_food
    for entry in (loadout.carry if loadout is not None else []):
        if edible(entry.item):
            return entry.item
    return fallback


def gear_of(loadout):
    return list(loadout.worn.values()) if loadout is not None else []


def supplies_of(loadout):
    return list(loadout.carry) if loadout is not None else []


def weapon_of(loadout, fallback=None):
    if loadout is None:
        return fallback
    return loadout.worn.get('righthand', fallback)


def script_food(settings, fallback):
    return food_of(selected_loadout(settings), fallback)


def script_foods(settings, fallback):
    chosen = food_of(selected_loadout(settings), '')
    return [chosen] if chosen else list(fallback)
