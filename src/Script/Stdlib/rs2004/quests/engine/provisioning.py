"""What a quest withdraws, gathers or banks before it starts: rs2b0t's api/ai/quests/engine/provisioning.ts (MIT, see
thirdparty/rs2b0t). Pure, over pack and bank counts by lower-case name."""

import math

__all__ = [
    'ProvisionPlan', 'plan_provisioning', 'COIN_FLOAT', 'buy_purse_top_up', 'should_freshen_pack', 'float_draw_plan',
    'deposit_plan', 'gp_short', 'float_withdraw', 'coin_float_withdraw', 'coin_float_plan',
]


class ProvisionPlan:
    """withdraw: dicts of name and qty; gather: dicts of name and need; blocked: what a mustHave item is short."""

    def __init__(self):
        self.withdraw = []
        self.gather = []
        self.blocked = []
        self.satisfied = True


def plan_provisioning(items, inv, bank):
    plan = ProvisionPlan()
    for item in items:
        key = item.name.lower()
        have = inv.get(key, 0)
        if have >= item.qty:
            continue
        plan.satisfied = False
        short = item.qty - have
        banked = bank.get(key, 0)
        if banked > 0:
            take = min(short, banked)
            plan.withdraw.append({'name': item.name, 'qty': take})
            short -= take
        if short > 0:
            if item.kind == 'mustHave':
                plan.blocked.append(f'{item.name} x{item.qty}')
            else:
                plan.gather.append({'name': item.name, 'need': short})
    return plan


# Spending money a quest keeps in the pack unless its module names another figure.
COIN_FLOAT = 1000

# Purse below which a counter trip is worth making, well under anything a quest asks for.
BUY_TOPUP_DIVISOR = 4


def buy_purse_top_up(held, est_gp):
    """Whether a buy needs a bank trip first, and how much it draws: {'need': ..., 'draw': ...}.

    Why: topping up to the item's own estimate left 20 gp after a loaf and the next boat fare emptied it, so Merlin's
    Crystal ran dry and walked back for another 20. Why: the trip refills a float, and only once the purse is a quarter
    of it, so nothing returns to the bank between 2 cheap buys."""
    target = max(est_gp, COIN_FLOAT)
    if held >= math.ceil(target / BUY_TOPUP_DIVISOR):
        return {'need': False, 'draw': 0}
    return {'need': True, 'draw': target - held}


def should_freshen_pack(journal, used_slots, already_fresh):
    """Whether to bank the pack to nothing before the quest starts.

    Why: the bot starts carrying anything and the quest before this one leaves anything behind, so every quest
    provisions from empty. Why: the journal is the only gate, since a quest underway may carry the only copy of
    something (Shield of Arrav's chest and Straven both re-check the bank, so a swept store key and shield half never
    come back)."""
    if used_slots == 0 or already_fresh:
        return False
    return journal == 'not_started'


def float_draw_plan(held, banked, target, already_drawn):
    """{'qty': to withdraw, 'drawn': whether the float is closed}.

    Why: the provisioning block re-runs every tick while a quest is still gathering, so topping a float up sent the bot
    back to the bank each time it ate a lobster or drank a dose. Why: 'drawn' closes the float for the quest once the
    pack has held it, and an empty bank leaves it open so a restock is still honoured."""
    if already_drawn or held >= target:
        return {'qty': 0, 'drawn': True}
    return {'qty': max(0, min(target - held, banked)), 'drawn': False}


def deposit_plan(inv, keep):
    """The names in the pack that no kept name is part of."""
    out = []
    for name in inv.keys():
        kept = False
        for k in keep:
            if k in name:
                kept = True
                break
        if not kept:
            out.append(name)
    return out


def gp_short(snap, est_gp):
    have = snap.inv.get('coins', 0) + snap.bank_coins
    return max(0, est_gp - have)


def float_withdraw(inv, bank, name, target):
    """The withdrawal that tops name up to target from the bank, or None."""
    key = name.lower()
    want = min(target - inv.get(key, 0), bank.get(key, 0))
    return {'name': name, 'qty': want} if want > 0 else None


def coin_float_withdraw(inv, bank, float_):
    return float_withdraw(inv, bank, 'Coins', float_)


def coin_float_plan(held, banked, target, already_drawn):
    """float_draw_plan for the purse.

    Why: the provisioning block re-runs every tick while a quest is still gathering, so topping the purse after a 10gp
    gate sent Cook's Assistant back to Al Kharid. Why: 'drawn' closes the float once the pack has held it, the same latch
    food already uses, and a target of 0 never withdraws."""
    if target <= 0:
        return {'qty': 0, 'drawn': True}
    return float_draw_plan(held, banked, target, already_drawn)
