"""Loadouts: the gear to wear and the supplies to carry. Ported from rs2b0t's api/loadout (MIT, see
thirdparty/rs2b0t). A loadout is {name, worn: {slot: item}, carry: [{item, qty}]}. rs2b0t keeps them in its
panel's storage; here they're the account file's script.settings["Loadouts"].sets, through the loadouts store,
which every bot shares. A bot's own 'loadouts' setting, a list of them, is used instead when it has one, and its
'loadout' setting (LOADOUT_SETTING) names the one to use.
"""

import json

from rs2004.settings import SettingDef, settings_store

LOADOUTS_NAMESPACE = 'Loadouts'
LOADOUTS_KEY = 'sets'
LOADOUT_SETTING = SettingDef(
    'string', '', 'Loadout', options=[], options_from='loadouts',
    help="the gear and supplies to wear and carry; blank uses the first loadout. What it doesn't name falls back to the bot's own default",
)

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


def _as_dict(loadout):
    return {'name': loadout.name, 'worn': {k: v for k, v in loadout.worn.items()}, 'carry': [{'item': c.item, 'qty': c.qty} for c in loadout.carry]}


def serialize_loadouts(loadouts):
    """The loadouts as JSON text, as parse_loadouts reads it back."""
    return json.dumps([_as_dict(l) for l in loadouts])


class _LoadoutStore:
    """rs2b0t's Loadouts: the loadouts every bot on the account shares."""

    def all(self):
        return parse_loadouts(settings_store.saved(LOADOUTS_NAMESPACE, LOADOUTS_KEY) or [])

    def names(self):
        return [l.name for l in self.all()]

    def by_name(self, name):
        wanted = name.strip().lower()
        for loadout in self.all():
            if loadout.name.lower() == wanted:
                return loadout
        return None

    def save(self, loadouts):
        """Saves the list into the account file, replacing what was there."""
        settings_store.save(LOADOUTS_NAMESPACE, LOADOUTS_KEY, [_as_dict(l) for l in loadouts])


loadouts = _LoadoutStore()


def _store_all():
    return loadouts.all()


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
    """The loadout settings.loadout names, else the first: of the bot's own loadouts setting when it has one,
    else of the shared store. None when there are none."""
    own = settings.get('loadouts')
    loadouts = parse_loadouts(own) if own else _store_all()
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
