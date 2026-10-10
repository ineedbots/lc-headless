"""Food, eating, boost potions and what a fight keeps in the backpack. Ported from rs2b0t's api/combat/food.ts,
eatTiming.ts, boostPotions.ts, keepList.ts and fightUpkeep.ts (MIT, see third_party/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs import _data

FOOD_OPTIONS = [
    'Shark', 'Lobster', 'Swordfish', 'Tuna', 'Salmon', 'Trout', 'Pike', 'Bass', 'Herring', 'Sardine', 'Anchovies', 'Shrimps',
    'Cooked meat', 'Cooked chicken', 'Bread', 'Stew',
    'Cake', 'Chocolate cake', 'Plain pizza', 'Meat pizza', 'Anchovy pizza', 'Pineapple pizza', 'Redberry pie', 'Meat pie', 'Apple pie',
]

# A food's partly eaten forms.
FOOD_FORMS = {
    'cake': ['cake', '2/3 cake', 'slice of cake'],
    'chocolate cake': ['chocolate cake', '2/3 chocolate cake', 'chocolate slice'],
    'plain pizza': ['plain pizza', '1/2 plain pizza'],
    'meat pizza': ['meat pizza', '1/2 meat pizza'],
    'anchovy pizza': ['anchovy pizza', '1/2 anchovy pizza'],
    'pineapple pizza': ['pineapple pizza', '1/2 pineapple pizza'],
    'redberry pie': ['redberry pie', 'half a redberry pie'],
    'meat pie': ['meat pie', 'half a meat pie'],
    'apple pie': ['apple pie', 'half an apple pie'],
}

# Hitpoints one bite heals.
FOOD_HEAL = {
    'shrimps': 3, 'shrimp': 3, 'anchovies': 1, 'sardine': 4, 'herring': 5, 'trout': 7, 'pike': 8, 'salmon': 9,
    'tuna': 10, 'lobster': 12, 'bass': 13, 'swordfish': 14, 'shark': 20,
    'cooked meat': 3, 'cooked chicken': 3, 'bread': 5, 'stew': 11,
    'cake': 4, '2/3 cake': 4, 'slice of cake': 4,
    'chocolate cake': 5, '2/3 chocolate cake': 5, 'chocolate slice': 5,
    'plain pizza': 7, '1/2 plain pizza': 7, 'meat pizza': 8, '1/2 meat pizza': 8,
    'anchovy pizza': 9, '1/2 anchovy pizza': 9, 'pineapple pizza': 11, '1/2 pineapple pizza': 11,
    'redberry pie': 5, 'half a redberry pie': 5, 'meat pie': 6, 'half a meat pie': 6,
    'apple pie': 7, 'half an apple pie': 7,
}

# Always eat at or below this, while food remains.
MIN_EAT_HP = 5
DEFAULT_FOOD_HEAL = 8
URGENT_HP_FRACTION = 0.35


def food_forms(food_name):
    key = food_name.lower()
    return FOOD_FORMS.get(key, [key])


def is_food_item(name, food_name):
    return (name or '').lower() in food_forms(food_name)


def is_edible_food(item, food_name):
    """An unnoted item of the food, in any of its forms."""
    return not getattr(item, 'noted', False) and is_food_item(item.name, food_name)


def food_count(items, food_name):
    return len([i for i in items if is_edible_food(i, food_name)])


def food_heal_amount(food_name):
    """Hitpoints one bite of the food heals; 8 for a food it doesn't know."""
    key = food_name.strip().lower()
    if not key:
        return DEFAULT_FOOD_HEAL
    if key in FOOD_HEAL:
        return FOOD_HEAL[key]
    for parent, forms in FOOD_FORMS.items():
        if parent == key or key in forms:
            return FOOD_HEAL.get(parent, FOOD_HEAL.get(forms[0], DEFAULT_FOOD_HEAL))
    for name, heal in FOOD_HEAL.items():
        if name in key or key in name:
            return heal
    return DEFAULT_FOOD_HEAL


def eat_at_hp_threshold(max_hp, heal, min_hp=5):
    """The hitpoints at or below which a bite heals in full, never above max_hp - 1 nor below min_hp."""
    if max_hp <= 0:
        return min_hp
    return max(min_hp, min(max_hp - 1, max_hp - max(0, heal)))


def should_eat_to_use_food(hp, max_hp, heal, count, min_hp=5):
    """Eat when a bite heals in full, or at the floor so you don't die with food left."""
    if count <= 0 or hp <= 0 or max_hp <= 0:
        return False
    if hp <= min_hp:
        return True
    heal = max(0, heal)
    return heal > 0 and max_hp - hp >= heal


def should_eat_food(food_name, hp, max_hp, count, min_hp=5):
    return should_eat_to_use_food(hp, max_hp, food_heal_amount(food_name), count, min_hp)


def should_hold_eat(attacked_this_tick, hp_fraction, urgent_at=0.35):
    """Whether to put eating off a tick: on the tick an attack started, unless health is urgent. Eating takes
    the tick, so on the swing's tick it costs the attack, and anywhere in the cooldown it costs nothing."""
    if hp_fraction <= urgent_at:
        return False
    return attacked_this_tick


class AttackClock:
    """The tick your attack animation started on, from the animation each tick."""

    def __init__(self):
        self.reset()

    def observe(self, animation, tick):
        if animation != self.last_animation:
            self.last_animation = animation
            if animation != -1:
                self.started_tick = tick

    def attacked_this_tick(self, tick):
        return self.started_tick == tick

    def reset(self):
        self.last_animation = -1
        self.started_tick = -1


_clock = AttackClock()


def swing_started_this_tick():
    """Whether your swing began this tick, when anything that takes a tick should wait."""
    tick = _core.tick()
    _clock.observe(_core.get_local_player().animation, tick)
    return _clock.attacked_this_tick(tick)


def bury_one_in_fight(bone_name):
    """Buries one bone in a fight's cooldown, not on a swing's tick. Use with yield from; True once it's gone."""
    from rs2004.items import inventory
    if swing_started_this_tick():
        return False
    bones = inventory.first(bone_name)
    if bones is None:
        return False
    before = inventory.used()
    if not bones.interact('Bury'):
        return False
    buried = yield from execution.delay_until_ticks(lambda: inventory.used() < before, 3)
    return buried


class BoostPotion:
    """skill, short (a label), flask (the dose drawn when the loadout names none) and doses (every form)."""

    def __init__(self, skill, short, label):
        self.skill = skill
        self.short = short
        self.flask = f'{label}(3)'
        self.doses = [f'{label}({d})' for d in [4, 3, 2, 1]]

    def __repr__(self):
        return f'BoostPotion({repr(self.flask)})'


SUPER_ATTACK = BoostPotion('attack', 'Att', 'Super attack')
SUPER_STRENGTH = BoostPotion('strength', 'Str', 'Super strength')
SUPER_DEFENCE = BoostPotion('defence', 'Def', 'Super defence')
SUPER_SET = [SUPER_ATTACK, SUPER_STRENGTH, SUPER_DEFENCE]
RANGING_POTION = BoostPotion('ranged', 'Rng', 'Ranging potion')
# Checked in this order, one sip a tick: attack wins a tick both could use.
BOOST_POTIONS = [SUPER_ATTACK, SUPER_STRENGTH]
EMPTY_VIAL = 'Vial'
BOOST_FLOOR = 0.1


def boost_faded(base, effective, floor=0.1):
    """Whether a boost has worn down to within the floor of the base level. A drained level isn't one: a super
    potion restores none of it."""
    boost = effective - base
    return base > 0 and boost >= 0 and boost <= floor * base


class PotionPlan:
    def __init__(self, potion, flask, want):
        self.potion = potion
        self.flask = flask
        self.want = want

    def __repr__(self):
        return f'PotionPlan({repr(self.flask)}, {self.want})'


def _plan_for(potion, carry):
    for entry in carry:
        wanted = entry.item.strip().lower()
        for dose in potion.doses:
            if dose.lower() == wanted:
                return PotionPlan(potion, dose, entry.qty)
    return PotionPlan(potion, potion.flask, 1)


def ranging_plan(carry):
    return _plan_for(RANGING_POTION, carry)


def planned_potions(carry, potions=None):
    """The dose form and count of each potion the loadout's carry list names, else one three-dose flask."""
    return [_plan_for(p, carry) for p in (potions if potions is not None else BOOST_POTIONS)]


def potion_to_sip(plans, held, levels):
    """The one potion to drink this tick, or None: held(plan) counts flasks, levels(skill) gives (base,
    effective)."""
    for plan in plans:
        base, effective = levels(plan.potion.skill)
        if held(plan) > 0 and boost_faded(base, effective):
            return plan
    return None


SPELL_DB = _data.SPELL_DB


def combat_keep_names(food, style, spell=None, ammo=None, weapon=None, extra=None):
    """What a fight's deposit keeps: the food in every form, the spell's runes, the ammo and the weapon."""
    keep = food_forms(food) + list(extra or [])
    if style == 'mage' and spell is not None and spell in SPELL_DB:
        keep.extend([r['rune'] for r in SPELL_DB[spell]['runes']])
    if style == 'range' and ammo:
        keep.append(ammo)
    if weapon:
        keep.append(weapon)
    return keep
