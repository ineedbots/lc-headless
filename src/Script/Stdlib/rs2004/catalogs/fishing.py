"""Fishing methods and the gear each needs. Ported from rs2b0t's data/fishingMethods.ts (MIT, see
thirdparty/rs2b0t)."""


class FishingGearPiece:
    """name, min (to fish at all) and restock (how many a bank trip tops up to)."""

    def __init__(self, name, min=1, restock=1):
        self.name = name
        self.min = min
        self.restock = restock

    def __repr__(self):
        return f'FishingGearPiece({repr(self.name)}, {self.min}, {self.restock})'


class FishingMethod:
    """name, op (the spot's option), pair (the other option such a spot has) and gear."""

    def __init__(self, name, op, pair, gear):
        self.name = name
        self.op = op
        self.pair = pair
        self.gear = gear

    def __repr__(self):
        return f'FishingMethod({repr(self.name)})'


WHIRLPOOL_IDS = [403, 404, 405, 406]


def _tool(name):
    return FishingGearPiece(name, 1, 1)


def _bait(name, restock=100):
    return FishingGearPiece(name, 1, restock)


FISHING_METHODS = [
    FishingMethod('Small net — shrimp/anchovy', 'Net', 'Bait', [_tool('Small fishing net')]),
    FishingMethod('Bait rod — sardine/herring', 'Bait', 'Net', [_tool('Fishing rod'), _bait('Fishing bait')]),
    FishingMethod('Fly fishing — trout/salmon', 'Lure', 'Bait', [_tool('Fly fishing rod'), _bait('Feather')]),
    FishingMethod('Bait rod — pike', 'Bait', 'Lure', [_tool('Fishing rod'), _bait('Fishing bait')]),
    FishingMethod('Big net — mackerel/cod/bass', 'Net', 'Harpoon', [_tool('Big fishing net')]),
    FishingMethod('Lobster cage — lobster', 'Cage', 'Harpoon', [_tool('Lobster pot')]),
    FishingMethod('Harpoon — tuna/swordfish', 'Harpoon', 'Cage', [_tool('Harpoon')]),
    FishingMethod('Harpoon — sharks', 'Harpoon', 'Net', [_tool('Harpoon')]),
    FishingMethod('Oily rod — lava eel', 'Bait', '', [_tool('Oily fishing rod'), _bait('Fishing bait')]),
]

FISHING_METHOD_OPTIONS = [m.name for m in FISHING_METHODS]

ALL_FISHING_GEAR_NAMES = []
for _method in FISHING_METHODS:
    for _piece in _method.gear:
        if _piece.name not in ALL_FISHING_GEAR_NAMES:
            ALL_FISHING_GEAR_NAMES.append(_piece.name)


def resolve_fish_method(name):
    """The method of that name, or the first, small net."""
    for method in FISHING_METHODS:
        if method.name == name:
            return method
    return FISHING_METHODS[0]


def gear_keep_names(method):
    return [g.name for g in method.gear]


def has_fishing_gear(method, count):
    return len([g for g in method.gear if count(g.name) < g.min]) == 0


def missing_fishing_gear(method, count):
    return [g for g in method.gear if count(g.name) < g.min]


def gear_label(method):
    return ' + '.join([g.name for g in method.gear])


def fishing_restock_plan(method, inv_count, bank_count):
    """[(name, qty)] to withdraw, up to each piece's restock count."""
    plan = []
    for piece in method.gear:
        need = piece.restock - inv_count(piece.name)
        if need <= 0:
            continue
        available = bank_count(piece.name)
        if available <= 0:
            continue
        plan.append((piece.name, min(need, available)))
    return plan


def spot_matches_method(actions, method):
    """Whether a fishing spot with these options is one this method fishes: it has the op, and the pair too
    when the method names one."""
    ops = [a.lower() for a in actions if a is not None]
    primary = method.op.lower()
    if primary not in ops:
        return False
    pair = method.pair.strip().lower()
    if not pair or pair == primary:
        return True
    return pair in ops
