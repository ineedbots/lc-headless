"""Ported from rs2b0t's src/bot/scripts/AccountLeveler/actions.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from bots.account_leveler.record import Record

__all__ = ['describe_activity', 'activity_actions', 'ActionQueue']

from bots.account_leveler.offers import supply_offer
from bots.account_leveler.types import requirement_key, stock_of
def describe_activity(plan):
    if plan.output:
        return f'Collect {plan.output.count} {plan.output.item} for {plan.objective}'
    if plan.quest:
        return f'Complete {plan.quest} to unlock {plan.objective}'
    if plan.prerequisite_levels:
        return f"Reach {', '.join([f'{skill} {level}' for skill, level in list(plan.prerequisite_levels.items())])} for {plan.objective}"
    return 'Train ' + str(plan.objective) + str((f" against {plan.settings.get('target')}" if plan.settings.get('target') else ''))


def activity_actions(plan, s, later=None, shopping_only=False):
    if later is None:
        later = []
    actions = [Record({'id': 'bank:start', 'label': 'Prepare at bank', 'detail': 'Deposit inventory and check equipment'})]
    shops = {}
    for need in plan.needs:
        missing = need.count - stock_of(s, requirement_key(need))
        offer = supply_offer(need.item)
        if missing <= 0 or not offer:
            continue
        _v2 = shops.get(offer.keeper)
        shop = (_v2 if _v2 is not None else Record({
            'id': f'shop:{offer.keeper}',
            'label': f'Shop at {offer.keeper}',
            'detail': '',
            'destination': offer.tile,
        }))
        shop.detail += f"{(', ' if shop.detail else '')}{missing} {need.item}"
        shops[offer.keeper] = shop
    actions.extend(list(list(shops.values())))
    if shopping_only:
        return actions
    actions.append(Record({
        'id': 'loadout',
        'label': 'Withdraw activity supplies',
        'detail': ', '.join([f"{(n.carry if n.carry is not None else n.count)} {n.item}{str(('' if n.carry else ' in bank'))}" for n in plan.needs]),
    }))
    if any([n.equip for n in plan.needs]):
        actions.append(Record({
            'id': 'equip',
            'label': 'Equip training gear',
            'detail': ', '.join([n.item for n in [n for n in plan.needs if n.equip]]),
        }))
    if plan.travel:
        _v3 = plan.settings.get('location')
        _v4 = plan.settings.get('location')
        actions.append(Record({
            'id': 'travel',
            'label': f'Travel to {(_v3 if _v3 is not None else plan.label)}',
            'detail': f'Destination {plan.travel.x}, {plan.travel.z}, {plan.travel.level}',
            'destination': plan.travel,
        }))
    actions.append(Record({'id': 'train', 'label': plan.label, 'detail': describe_activity(plan), 'destination': plan.travel}))
    actions.extend(list([(Record({
        'id': f'later:{p.id}',
        'label': p.label,
        'detail': f'{describe_activity(p)}; recheck supplies at bank',
        'destination': p.travel,
    })) for p in later]))
    return actions


class ActionQueue:
    current = ''
    destination = None
    changed_at = 0

    def __init__(self):
        self.items = []
        self.history = []

    def reset(self, items):
        self.items = [Record({key: value for key, value in item.items()}) for item in items]
        for item in self.items:
            item.state = 'pending'
        self.current = ''
        self.destination = None

    def update(self, event, now=None):
        if now is None:
            now = _core.step_time()
        item = ([item for item in self.items if item.id == event.id] or [None])[0]
        if item:
            item.state = event.state
        if event.message != self.current:
            self.changed_at = now
        self.current = event.message
        self.destination = event.destination
        self.note(event.message, now)

    def fail(self, reason, now=None):
        if now is None:
            now = _core.step_time()
        for item in self.items:
            if item.state == 'running':
                item.state = 'failed'
        self.current = reason
        self.destination = None
        self.changed_at = now
        self.note(reason, now)

    def note(self, message, now=None):
        if now is None:
            now = _core.step_time()
        if ((self.history[-1] if len(self.history) > 0 else None).message if (self.history[-1] if len(self.history) > 0 else None) is not None else None) == message:
            return
        self.history = (list(self.history) + [Record({'at': now, 'message': message})])[-40:]
