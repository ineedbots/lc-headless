"""Axe and pickaxe tiers, and the tool kit a gathering bot needs. Ported from rs2b0t's
api/acquisition/Tools.ts (MIT, see third_party/rs2b0t).

A requirement is a ToolReq: a tiered one picks the best axe or pickaxe the skill can use, and an exact one
names one item. Counting and skill levels come in as functions, so the planners stay pure:
    has_all_tools([axe_req(), tinderbox_req()], skills.level, inventory.count)
"""


class ToolTier:
    """name, level (the skill level to use it) and attack_level (to wield it)."""

    def __init__(self, name, level, attack_level=1):
        self.name = name
        self.level = level
        self.attack_level = attack_level

    def __repr__(self):
        return f'ToolTier({repr(self.name)}, {self.level}, {self.attack_level})'


class ToolReq:
    """kind 'tiered' (skill, tiers best-first, label, equip) or 'exact' (name, min, restock, equip)."""

    def __init__(self, kind, skill=None, tiers=None, label=None, name=None, min=1, restock=1, equip=False):
        self.kind = kind
        self.skill = skill
        self.tiers = tiers
        self.label = label
        self.name = name
        self.min = min
        self.restock = restock
        self.equip = equip

    def __repr__(self):
        if self.kind == 'tiered':
            return f'ToolReq(tiered {self.label})'
        return f'ToolReq(exact {self.name})'


PICKAXES = [
    ToolTier('Rune pickaxe', 41, 40),
    ToolTier('Adamant pickaxe', 31, 30),
    ToolTier('Mithril pickaxe', 21, 20),
    ToolTier('Steel pickaxe', 6, 5),
    ToolTier('Iron pickaxe', 1, 1),
    ToolTier('Bronze pickaxe', 1, 1),
]

# This revision gates axe wielding on Attack, with no Woodcutting requirement.
AXES = [
    ToolTier('Rune axe', 1, 40),
    ToolTier('Adamant axe', 1, 30),
    ToolTier('Mithril axe', 1, 20),
    ToolTier('Steel axe', 1, 5),
    ToolTier('Iron axe', 1, 1),
    ToolTier('Bronze axe', 1, 1),
]

TINDERBOX = 'Tinderbox'
HAMMER = 'Hammer'
KNIFE = 'Knife'
CHISEL = 'Chisel'
NEEDLE = 'Needle'


def tool_attack_level(name):
    """The Attack level to wield an axe or pickaxe; 1 for any other tool."""
    want = name.lower()
    for tier in PICKAXES + AXES:
        if tier.name.lower() == want:
            return tier.attack_level
    return 1


def can_wield_tool(name, attack_level):
    return attack_level >= tool_attack_level(name)


def pickaxe_req(equip=True):
    return ToolReq('tiered', skill='mining', tiers=PICKAXES, label='pickaxe', equip=equip)


def axe_req(equip=True):
    return ToolReq('tiered', skill='woodcutting', tiers=AXES, label='axe', equip=equip)


def exact_tool(name, min=1, restock=None, equip=False):
    return ToolReq('exact', name=name, min=min, restock=restock if restock is not None else min, equip=equip)


def tinderbox_req():
    return exact_tool(TINDERBOX)


def best_from_tiers(level, tiers, available):
    """The best tier, of tiers best-first, that level can use and available(name) allows; None for none."""
    for tier in tiers:
        if level >= tier.level and available(tier.name):
            return tier.name
    return None


def best_pickaxe(mining_level, available):
    return best_from_tiers(mining_level, PICKAXES, available)


def best_axe(woodcutting_level, available):
    return best_from_tiers(woodcutting_level, AXES, available)


def _unique(names):
    out = []
    for name in names:
        if name not in out:
            out.append(name)
    return out


def tool_keep_names(reqs):
    """Every name the requirements could be met by, for a deposit's keep list."""
    names = []
    for req in reqs:
        if req.kind == 'tiered':
            names.extend([tier.name for tier in req.tiers])
        else:
            names.append(req.name)
    return _unique(names)


def _best_held(req, skill_level, count):
    return best_from_tiers(skill_level(req.skill), req.tiers, lambda n: count(n) > 0)


def has_tool_req(req, skill_level, count):
    if req.kind == 'tiered':
        return _best_held(req, skill_level, count) is not None
    return count(req.name) >= req.min


def has_all_tools(reqs, skill_level, count):
    return len([r for r in reqs if not has_tool_req(r, skill_level, count)]) == 0


def missing_tool_labels(reqs, skill_level, count):
    return [r.label if r.kind == 'tiered' else r.name for r in reqs if not has_tool_req(r, skill_level, count)]


def tool_kit_label(reqs, skill_level, count):
    """'Rune axe + Tinderbox', with 'axe (bronze to rune)' for a tier not held."""
    if not reqs:
        return 'gear'
    parts = []
    for req in reqs:
        if req.kind == 'tiered':
            held = _best_held(req, skill_level, count)
            parts.append(held if held is not None else f'{req.label} (bronze to rune)')
        else:
            parts.append(req.name)
    return ' + '.join(parts)


class ToolRestockStep:
    def __init__(self, name, qty, equip):
        self.name = name
        self.qty = qty
        self.equip = equip

    def __eq__(self, other):
        return isinstance(other, ToolRestockStep) and self.name == other.name and self.qty == other.qty and self.equip == other.equip

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return f'ToolRestockStep({repr(self.name)}, {self.qty}, {self.equip})'


def tool_restock_plan(reqs, skill_level, inv_count, bank_count):
    """What to withdraw: the best tier owned across backpack and bank, when it's only in the bank, and the
    exact tools short of their restock count."""
    plan = []
    for req in reqs:
        if req.kind == 'tiered':
            best_owned = best_from_tiers(skill_level(req.skill), req.tiers, lambda n: inv_count(n) > 0 or bank_count(n) > 0)
            if best_owned is None or inv_count(best_owned) > 0 or bank_count(best_owned) <= 0:
                continue
            plan.append(ToolRestockStep(best_owned, 1, req.equip))
            continue
        need = req.restock - inv_count(req.name)
        if need <= 0:
            continue
        available = bank_count(req.name)
        if available <= 0:
            continue
        plan.append(ToolRestockStep(req.name, min(need, available), req.equip))
    return plan


def bank_has_better_gather_tool(reqs, skill_level, inv_count, bank_count):
    """Whether the bank holds a better usable axe or pickaxe than the one carried."""
    tiered_names = []
    for req in reqs:
        if req.kind == 'tiered':
            tiered_names.extend([tier.name.lower() for tier in req.tiers])
    steps = tool_restock_plan(reqs, skill_level, inv_count, bank_count)
    return len([s for s in steps if s.name.lower() in tiered_names]) > 0


def tools_needing_equip(reqs, skill_level, count, worn):
    """Tools to wield now: held, marked equip, not worn, and Attack high enough. A tool too good to wield is
    still used from the backpack."""
    attack = skill_level('attack')
    out = []
    for req in reqs:
        if not req.equip:
            continue
        if req.kind == 'tiered':
            best = _best_held(req, skill_level, count)
            if best is not None and not worn(best) and can_wield_tool(best, attack):
                out.append(best)
            continue
        if count(req.name) > 0 and not worn(req.name) and can_wield_tool(req.name, attack):
            out.append(req.name)
    return out


def best_held_tool_names(reqs, skill_level, count):
    """The best tier held of each tiered requirement, and the exact tools held: what a deposit keeps."""
    out = []
    for req in reqs:
        if req.kind == 'tiered':
            best = _best_held(req, skill_level, count)
            if best is not None:
                out.append(best)
        elif count(req.name) > 0:
            out.append(req.name)
    return out


def surplus_held_tool_names(reqs, skill_level, count):
    """Tiers held that are worse than the best one held, such as a bronze axe beside a steel one."""
    surplus = []
    for req in reqs:
        if req.kind != 'tiered':
            continue
        best = _best_held(req, skill_level, count)
        if best is None:
            continue
        for tier in req.tiers:
            if tier.name.lower() != best.lower() and count(tier.name) > 0:
                surplus.append(tier.name)
    return _unique(surplus)
