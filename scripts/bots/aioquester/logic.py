"""AIOQuester's food choice and queue summary: rs2b0t's AIOQuesterLogic.ts, and queueEntry, blockedEntries, focusRow,
queueSummary and questClockRestarts from AIOQuesterPaint.ts (MIT, see thirdparty/rs2b0t). Includes Shield of Arrav's
gang and partner settings; Hero's Quest's partner and Legends' reward settings come with those quests."""

import math
from rs2004.quests.defs.shieldofarrav.config import arrav_config
from rs2004.catalogs import Record, food_forms, food_heal_amount, should_eat_to_use_food

# Tourist Trap can leave Baker's-stall Cakes in the pack even when the general food is Lobster. Implicit eligibility
# stays narrow so edible quest items stay safe.
OPPORTUNISTIC_FOODS = set(food_forms('Cake'))


def resolve_consume_action(actions):
    """The item's option that eats or drinks it, 'Eat' first, or None."""
    for wanted in ['eat', 'drink']:
        for action in actions:
            if action is not None and action.lower() == wanted:
                return action
    return None


class SustainSelection:
    """An item to consume and the option that does it."""

    def __init__(self, item, action):
        self.item = item
        self.action = action


# Why: a fitting heal wins across the pack before the low-HP safety floor is considered, so a large food in an earlier
# slot can't veto a later Cake bite that fits.
def select_sustain_consumable(items, foods, hp, max_hp):
    """The item to eat now, as a SustainSelection, or None. items have name and actions()."""
    allowed = set([f.strip().lower() for f in foods if f.strip()])
    candidates = []
    for item in items:
        name = (item.name or '').strip().lower()
        policy_food = name in allowed
        if not policy_food and name not in OPPORTUNISTIC_FOODS:
            continue
        action = resolve_consume_action(item.actions())
        if action is None:
            continue
        candidates.append((item, action, food_heal_amount(name), policy_food))
    if hp > 0 and max_hp > 0:
        for item, action, heal, policy_food in candidates:
            if hp + heal <= max_hp:
                return SustainSelection(item, action)
    # The emergency floor belongs only to configured or quest food; opportunistic Cakes are eligible only when their
    # whole bite fits.
    for item, action, heal, policy_food in candidates:
        if policy_food and should_eat_to_use_food(hp, max_hp, heal, 1):
            return SustainSelection(item, action)
    return None


# Why: each food expands to every form it's eaten down through, so a bitten cake is still recognised as food.
# Why: the eat threshold is food-heal based (see catalogs' food_heal_amount).
def resolve_sustain_policy(configured_food, quest=None):
    """The foods to eat, as a Record of foods: the running quest's sustain foods, then the configured food, each with
    its forms."""
    foods = []
    seen = set()
    candidates = list(quest.foods if quest is not None else []) + [configured_food]
    for candidate in candidates:
        food = (candidate or '').strip()
        if not food:
            continue
        for form in food_forms(food):
            if form in seen:
                continue
            seen.add(form)
            foods.append(form)
    return Record({'foods': foods})


# The queue, for the progress report.

QUEUE_ICON = {'DONE': '✓', 'RUNNING': '▶', 'READY': '·', 'PARKED': '⏸', 'BLOCKED': '✗', 'UNKNOWN': '?'}


def queue_entry(row):
    """A queue row as its icon, name and first reason (with how many more): {'icon', 'name', 'note'}."""
    note = ''
    if len(row.reasons) > 0:
        rest = len(row.reasons) - 1
        note = f'{row.reasons[0]} (+{rest} more)' if rest > 0 else row.reasons[0]
    return {'icon': QUEUE_ICON[row.status], 'name': row.name, 'note': note}


def blocked_entries(rows):
    """The quests going nowhere, with every reason they gave: [{'name', 'reasons'}]."""
    out = []
    for r in rows:
        if r.status == 'BLOCKED' or r.status == 'PARKED' or r.status == 'UNKNOWN':
            out.append({'name': r.name, 'reasons': list(r.reasons) if len(r.reasons) > 0 else ['no reason given']})
    return out


def focus_row(rows, running_id):
    """The row to show: what's running, else the next unfinished quest, else -1."""
    for i in range(len(rows)):
        if rows[i].id == running_id:
            return i
    for i in range(len(rows)):
        if rows[i].status != 'DONE':
            return i
    return -1


def queue_summary(rows):
    """{'done', 'stuck', 'total'}."""
    done = len([r for r in rows if r.status == 'DONE'])
    stuck = len([r for r in rows if r.status == 'BLOCKED' or r.status == 'PARKED'])
    return {'done': done, 'stuck': stuck, 'total': len(rows)}


# Why: the engine passes a None running id for a drained queue, a parked plan and a banking spillover, all inside one
# quest, so a plain inequality restarts the quest clock several times without the quest having changed.
def quest_clock_restarts(prev_id, next_id):
    """Whether the per-quest clock restarts for this state update."""
    return next_id is not None and next_id != prev_id

ARRAV_GANG_OPTIONS = ['random', 'phoenix', 'blackarm']


def apply_arrav_settings(raw):
    arrav_config.gang = raw.gang if raw.gang in ARRAV_GANG_OPTIONS else 'random'
    arrav_config.partner = raw.partner.strip()
    count = raw.certs
    arrav_config.cert_target = max(1, math.floor(count if math.isfinite(count) else 2))
