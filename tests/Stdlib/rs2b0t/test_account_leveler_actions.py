"""Ported from rs2b0t's src/bot/../../test/scripts/accountLevelerActions.test.ts (MIT, see thirdparty/rs2b0t)."""
from bots.account_leveler.record import Record
from bots.account_leveler.planner import empty_memory, enabled_skills, plan_next, resolve_activity
from bots.account_leveler.actions import ActionQueue, activity_actions, describe_activity

def snapshot():
    return Record({'levels': {_k: _v for _k, _v in [[skill, (10 if skill == 'hitpoints' else 1)] for skill in enabled_skills]}, 'stock': Record({'coins': 100000}), 'quests': Record({}), 'bank_ready': True, 'target': 40, 'wilderness': True, 'now': 1000})

def _fn1(*_args):
    s = snapshot()
    for _k, _v in Record({'attack': 20, 'strength': 20, 'defence': 20, 'hitpoints': 25}).items():
        s.levels[_k] = _v
    s.levels
    _merged2 = {}
    for _k, _v in ((empty_memory()._fields if isinstance(empty_memory(), Record) else empty_memory())).items():
        _merged2[_k] = _v
    for _k, _v in {'objective': 'attack'}.items():
        _merged2[_k] = _v
    decision = plan_next(s, Record(_merged2), lambda: 0)
    expect(decision.kind).to_be('activity')
    if decision.kind != 'activity':
        return
    expect([plan.script for plan in decision.queue]).to_equal(['Fisher', 'CookBot', 'AutoFighter'])
    s.stock['raw shrimps'] = 28
    next_ = resolve_activity(s, decision.queue[1], empty_memory(), lambda: 0.99)
    expect(next_.kind == 'activity' and next_.plan.script).to_be('CookBot')
    s.stock['shrimps'] = 24
    ready = resolve_activity(s, decision.queue[2], empty_memory(), lambda: 0.99)
    expect(ready.kind == 'activity' and ready.plan.id).to_be(decision.queue[2].id)
    expect(ready.kind == 'activity' and ready.plan.death_walk).to_be(False)
test('a food dependency preserves the chosen fish, cook, combat sequence through bank refreshes', _fn1)

def _fn3(*_args):
    s = snapshot()
    for _k, _v in Record({'attack': 20, 'strength': 20, 'defence': 20, 'hitpoints': 25}).items():
        s.levels[_k] = _v
    s.levels
    _merged4 = {}
    for _k, _v in ((empty_memory()._fields if isinstance(empty_memory(), Record) else empty_memory())).items():
        _merged4[_k] = _v
    for _k, _v in {'objective': 'attack'}.items():
        _merged4[_k] = _v
    decision = plan_next(s, Record(_merged4), lambda: 0)
    if decision.kind != 'activity':
        raise RuntimeError('expected activity')
    actions = activity_actions(decision.plan, s, decision.queue[1:])
    expect((([a for a in actions if a.id == 'shop:Gerrant'] or [None])[0].detail if ([a for a in actions if a.id == 'shop:Gerrant'] or [None])[0] is not None else None)).to_contain('Small fishing net')
    expect((([a for a in actions if a.id == 'shop:Gerrant'] or [None])[0].destination if ([a for a in actions if a.id == 'shop:Gerrant'] or [None])[0] is not None else None)).to_match_object(Record({'x': 3013, 'z': 3224}))
    expect(describe_activity(decision.plan)).to_contain('28 Raw shrimps')
    expect(any(['cook' in a.label for a in actions])).to_be(True)
    expect((([a for a in actions if a.id == f'later:{decision.queue[2].id}'] or [None])[0].detail if ([a for a in actions if a.id == f'later:{decision.queue[2].id}'] or [None])[0] is not None else None)).to_contain('attack')
test('action preview explains the shopping destination and why fishing is queued', _fn3)

def _fn5(*_args):
    queue = ActionQueue()
    queue.reset([Record({'id': 'shop:Bob', 'label': 'Shop at Bob', 'detail': 'Bronze axe'}), Record({'id': 'loadout', 'label': 'Withdraw kit', 'detail': 'Bronze axe'})])
    queue.update(Record({'id': 'shop:Bob', 'message': 'Walking to Bob', 'state': 'running'}), 1000)
    queue.update(Record({'id': 'shop:Bob', 'message': 'Bought Bronze axe', 'state': 'done'}), 2000)
    queue.update(Record({'id': 'loadout', 'message': 'Withdrawing Bronze axe', 'state': 'running', 'destination': Record({'x': 3200, 'z': 3200, 'level': 0})}), 3000)
    expect([a.state for a in queue.items]).to_equal(['done', 'running'])
    queue.fail('Bank did not open', 4000)
    expect(queue.items[1].state).to_be('failed')
    expect(queue.destination).to_be_undefined()
    expect((((queue.history[-1] if len(queue.history) > 0 else None)).message if ((queue.history[-1] if len(queue.history) > 0 else None)) is not None else None)).to_contain('Bank did not open')
    for i in range(100):
        queue.note(f'walk {i}', 5000 + i)
    expect(len(queue.history)).to_be_less_than_or_equal(40)
test('queue advances from real events, retains failures and caps action history', _fn5)

def _fn6(*_args):
    from bots.account_leveler.priority import can_resume_objective
    s = snapshot()
    for _k, _v in Record({'attack': 25, 'strength': 20, 'defence': 5}).items():
        s.levels[_k] = _v
    s.levels
    expect(can_resume_objective(s.levels, s.target, 'agility')).to_be(False)
    expect(can_resume_objective(s.levels, s.target, 'attack')).to_be(False)
    expect(can_resume_objective(s.levels, s.target, 'defence')).to_be(True)
    for skill in ['attack', 'strength', 'defence', 'hitpoints', 'ranged', 'magic', 'prayer']:
        s.levels[skill] = 40
    expect(can_resume_objective(s.levels, s.target, 'agility')).to_be(True)
test('queued goals are revalidated while combat supply dependencies remain eligible', _fn6)

def resolved_wait(value):
    if False:
        yield
    return value
