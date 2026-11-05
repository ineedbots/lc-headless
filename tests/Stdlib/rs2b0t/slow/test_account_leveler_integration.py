"""Ported from rs2b0t's src/bot/../../test/scripts/accountLevelerIntegration.test.ts (MIT, see thirdparty/rs2b0t)."""
from bots.account_leveler.record import Record
from bots.account_leveler.manifests import manifest_for
from bots.account_leveler.planner import empty_memory, enabled_skills, plan_next
from bots.account_leveler.methods import method_for, producer
from bots.account_leveler.offers import supply_offer
from bots.account_leveler.combat import COMBAT_CAMPS, combat_plan
from bots.account_leveler.session import LevelerSession

def snapshot(level=1):
    return Record({'levels': {_k: _v for _k, _v in [[s, (max(10, level) if s == 'hitpoints' else level)] for s in enabled_skills]}, 'stock': Record({'coins': 100000}), 'bank_ready': True, 'quests': Record({}), 'target': 40, 'wilderness': True, 'now': 1000})

def validate(plan, s):
    meta = manifest_for(plan.script)
    expect(meta, plan.script).to_be_defined()
    for key, value in plan.settings.items():
        _v1 = (meta.settings_schema if meta is not None else None)
        def_ = (_v1[key] if _v1 is not None else None)
        expect(def_, f'{plan.script}.{key}').to_be_defined()
        if ((len((def_.options if def_ is not None else None)) if ((def_.options if def_ is not None else None)) is not None else None)) and (not def_.options_from):
            for chosen in (value if isinstance(value, list) else [value]):
                expect(def_.options, f'{plan.script}.{key}={chosen}').to_contain(chosen)
    for need in plan.needs:
        if need.item == 'Coins':
            continue
        expect(supply_offer(need.item) or producer(s, plan.objective, need, empty_memory(), lambda: 0), need.item).to_be_truthy()

def _fn2(*_args):
    for level in [1, 5, 10, 14, 15, 20, 25, 30, 39, 40, 41, 50, 59]:
        s = snapshot(level)
        s.target = 60
        for stocked in [False, True]:
            s.stock['shrimps'] = (24 if stocked else 0)
            for quests in [False, True]:
                s.quests = Record({'Druidic Ritual': quests, 'Rune Mysteries Quest': quests})
                for skill in enabled_skills:
                    for roll in [0, 0.25, 0.5, 0.75, 0.999]:
                        plan = method_for(s, skill, empty_memory(), lambda: roll)
                        expect(plan, skill).not_.to_be_null()
                        if plan:
                            validate(plan, s)
test('every training adapter uses an installed script and supported settings', _fn2)
