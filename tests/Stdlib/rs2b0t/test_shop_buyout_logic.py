"""rs2b0t's test/api/shop/buyout-logic.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs import Record, buyout_plan


REC = Record({
    'inv': 'magearena_runeshop',
    'title': '',
    'keepers': ['Lundail'],
    'sell': 1000,
    'buy': 550,
    'delta': 30,
    'scope': 'shared',
    'allstock': False,
    'items': [
    Record({
    'obj': 'mindrune',
    'name': 'Mind rune',
    'baseline': 140,
    'restock_ticks': 50,
    'cost': 3,
    'stackable': True,
    'members': False,
}),
    Record({
    'obj': 'lawrune',
    'name': 'Law rune',
    'baseline': 250,
    'restock_ticks': 300,
    'cost': 40,
    'stackable': True,
    'members': False,
}),
    Record({
    'obj': 'deathrune',
    'name': 'Death rune',
    'baseline': 250,
    'restock_ticks': 150,
    'cost': 30,
    'stackable': True,
    'members': False,
}),
    Record({
    'obj': 'firerune',
    'name': 'Fire rune',
    'baseline': 200,
    'restock_ticks': 50,
    'cost': 4,
    'stackable': True,
    'members': False,
}),
],
})
ALL = set([i.name.lower() for i in REC.items])


def _fn1():
    def _fn2():
        plan = buyout_plan(REC, Record({'mindrune': 10, 'lawrune': 10, 'deathrune': 10, 'firerune': 10}), 1000000, ALL)
        expect([p.obj for p in plan]).to_equal(['lawrune', 'deathrune', 'firerune', 'mindrune'])
        expect(all([p.units == 10 for p in plan])).to_be(True)
    test('allocates valuable-first (law > death > fire > mind) regardless of record order', _fn2)

    def _fn3():
        plan = buyout_plan(REC, Record({'lawrune': 10, 'mindrune': 10}), 1000, ALL)
        law = ([p for p in plan if p.obj == 'lawrune'] or [None])[0]
        mind = ([p for p in plan if p.obj == 'mindrune'] or [None])[0]
        expect(law.units).to_be(4)
        expect(law.est_cost).to_be(960)
        expect(mind.units).to_be(2)
    test('coin budget bounds the plan; cheap tail starves before the valuable head', _fn3)

    def _fn4():
        plan = buyout_plan(REC, Record({'lawrune': 5, 'deathrune': 0, 'firerune': 5}), 100000, set(['law rune', 'death rune']))
        expect([p.obj for p in plan]).to_equal(['lawrune'])
        expect(plan[0].units).to_be(5)
    test('honors the chosen filter and skips empty stock', _fn4)

    def _fn5():
        expect(buyout_plan(REC, Record({'not_a_rune': 50}), 100000, ALL)).to_equal([])
        expect(buyout_plan(REC, Record({'lawrune': 5}), 0, ALL)).to_equal([])
    test('unknown stock names are ignored; zero coins buys nothing', _fn5)


describe('buyoutPlan', _fn1)

