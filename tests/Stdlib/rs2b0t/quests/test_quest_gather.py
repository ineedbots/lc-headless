"""rs2b0t's test/api/ai/quests/quest-gather.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect.
Its Witch's House cases come with that quest."""

from rs2004.quests.defs import QUEST_DEFS


# Why: the engine reaches gather only when the bank can't cover an acquirable item, so a def missing one runs fine on a
# stocked account and blocks outright on a fresh one.
def _fn1():
    def _fn2():
        missing = []
        for d in QUEST_DEFS:
            module = d.module()
            if module.owns_inventory:
                continue
            for item in module.record.items:
                if item.kind == 'acquirable' and (module.gather is None or module.gather.get(item.name.lower()) is None):
                    missing.append(f'{module.record.name}: {item.name}')
        expect(missing).to_equal([])
    test('every acquirable the records name has a gather fn, or the module owns its inventory', _fn2)


describe('acquirable items have somewhere to come from', _fn1)
