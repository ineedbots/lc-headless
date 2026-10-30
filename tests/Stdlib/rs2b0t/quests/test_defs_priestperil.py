"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/priestperil.test.ts (MIT, see thirdparty/rs2b0t)."""


from rs2004.quests.defs.priestperil import decide
def snap(journal, items=None):
    if items is None:
        items = []
    return (Obj({
        'journal': journal,
        'inv': {_k: _v for _k, _v in [[n, 1] for n in items]},
        'worn': set(),
        'no_progress': 0,
        'bank_coins': 0,
    }))


def routed(s):
    return (f'talk:{s.stop.npc}' if s.kind == 'talk' else (f'custom:{s.name}' if s.kind == 'custom' else s.kind))


def _fn1():
    def _fn2():
        expect(decide(snap('complete')).kind).to_be('done')
        expect(decide(snap('unknown')).kind).to_be('wait')
        expect(routed(decide(snap('not_started')))).to_be('talk:King Roald')
    test('journal drives the ends', _fn2)

    def _fn3():
        expect(routed(decide(snap('in_progress', ['golden key'])))).to_be('custom:monument key swap')
        expect(routed(decide(snap('in_progress', ['iron key'])))).to_be('custom:unlock the cell')
        expect(routed(decide(snap('in_progress', ['bucket of water'])))).to_be('custom:water chain')
        expect(routed(decide(snap('in_progress', ['rune essence'])))).to_be('custom:essence delivery')
    test('held items route the mid-quest legs (exact full-name keys)', _fn3)

    def _fn4():
        expect(routed(decide(snap('in_progress', ['rune essence', 'golden key'])))).to_be('custom:monument key swap')
    test('key priority: a golden key outranks essence in the pack', _fn4)

    def _fn5():
        expect(routed(decide(snap('in_progress', ['bucket'])))).to_be('custom:locate phase')
    test('a plain empty Bucket does NOT trigger the water chain (exact-key get)', _fn5)

    def _fn6():
        expect(routed(decide(snap('in_progress')))).to_be('custom:locate phase')
    test('empty-handed inProgress runs the stage-oracle spine', _fn6)


describe('priestperil decide', _fn1)
