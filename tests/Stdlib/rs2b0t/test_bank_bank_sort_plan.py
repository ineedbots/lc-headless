"""rs2b0t's test/api/bank/bankSortPlan.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs import Record
from rs2004.banksort import apply_move, longest_increasing_subsequence, plan_bank_sort


COINS = 995
AIR_RUNE = 556
LAW_RUNE = 563
SHARK = 385
LOBSTER = 379
MITHRIL_ORE = 447
JUNK_A = 31337
JUNK_B = 31338


def bank(ids):
    names = {
        COINS: 'Coins',
        AIR_RUNE: 'Air rune',
        LAW_RUNE: 'Law rune',
        SHARK: 'Shark',
        LOBSTER: 'Lobster',
        MITHRIL_ORE: 'Mithril ore',
        JUNK_A: 'Nameless thing a',
        JUNK_B: 'Nameless thing b',
    }
    costs = {COINS: 1, AIR_RUNE: 4, LAW_RUNE: 240, SHARK: 200, LOBSTER: 100, MITHRIL_ORE: 81, JUNK_A: 1, JUNK_B: 1}
    return [(Record({
        'slot': slot,
        'id': id,
        'name': names.get(id),
        'cost': costs.get(id, 0),
    })) for slot, id in enumerate(ids)]


def replay(ids, plan):
    order = list(ids)
    for move in plan.moves:
        order = apply_move(order, move, plan.mode)
    return order


def _fn1():
    def _fn2():
        expect(longest_increasing_subsequence([3, 0, 1, 2])).to_equal([0, 1, 2])
        expect(longest_increasing_subsequence([0, 1, 2, 3])).to_equal([0, 1, 2, 3])
        expect(len(longest_increasing_subsequence([3, 2, 1, 0]))).to_be(1)
        expect(longest_increasing_subsequence([])).to_equal([])
    test('returns the values of a longest run', _fn2)


describe('longestIncreasingSubsequence', _fn1)


def _fn3():
    def _fn4():
        expect(apply_move([10, 20, 30, 40], Record({'from_': 0, 'to': 2}), 'swap')).to_equal([30, 20, 10, 40])
    test('swap exchanges two slots', _fn4)

    def _fn5():
        expect(apply_move([10, 20, 30, 40], Record({'from_': 3, 'to': 0}), 'insert')).to_equal([40, 10, 20, 30])
    test('insert shifts right to left, matching insert_bank', _fn5)

    def _fn6():
        expect(apply_move([10, 20, 30, 40], Record({'from_': 0, 'to': 2}), 'insert')).to_equal([20, 30, 10, 40])
    test('insert shifts left to right, matching insert_bank', _fn6)


describe('applyMove', _fn3)


def _fn7():
    def _fn8():
        plan = plan_bank_sort(bank([COINS, LAW_RUNE, AIR_RUNE, SHARK, LOBSTER, MITHRIL_ORE, JUNK_A]))
        expect(plan.moves).to_equal([])
    test('an already sorted bank yields no moves', _fn8)

    def _fn9():
        ids = [JUNK_A, SHARK, COINS, AIR_RUNE]
        plan = plan_bank_sort(bank(ids))
        expect(plan.layout[0]).to_be(COINS)
        expect((replay(ids, plan) or [None])[0]).to_be(COINS)
    test('coins always land in slot 0', _fn9)

    def _fn10():
        ids = [JUNK_A, SHARK, COINS, JUNK_B, AIR_RUNE]
        plan = plan_bank_sort(bank(ids))
        expect(sorted(plan.layout[-2:])).to_equal(sorted([JUNK_A, JUNK_B]))
    test('junk always lands last', _fn10)

    def _fn11():
        plan = plan_bank_sort(bank([LOBSTER, SHARK]))
        expect(plan.layout).to_equal([SHARK, LOBSTER])
    test('within a category the dearer item comes first', _fn11)

    def _fn12():
        ids = [JUNK_B, MITHRIL_ORE, COINS, LOBSTER, AIR_RUNE, JUNK_A, SHARK, LAW_RUNE]
        plan = plan_bank_sort(bank(ids))
        expect(replay(ids, plan)).to_equal(plan.layout)
    test('replaying the plan reaches the planned layout', _fn12)

    def _fn13():
        ids = [JUNK_B, MITHRIL_ORE, COINS, LOBSTER, AIR_RUNE, JUNK_A, SHARK, LAW_RUNE]
        plan = plan_bank_sort(bank(ids))
        expect(sorted(list(plan.layout))).to_equal(sorted(list(ids)))
    test('the layout is a permutation of the input', _fn13)

    def _fn14():
        plan = plan_bank_sort(bank([COINS, JUNK_A, SHARK]))
        expect(plan.unmatched).to_equal([JUNK_A])
    test('unmatched items are reported', _fn14)

    def _fn15():
        expect(plan_bank_sort(bank([COINS, LAW_RUNE, AIR_RUNE, SHARK, LOBSTER, MITHRIL_ORE, JUNK_A])).moves).to_equal([])
        # A law rune deposited after that sort lands at the end and belongs at index 1.
        ids = [COINS, AIR_RUNE, SHARK, LOBSTER, MITHRIL_ORE, JUNK_A, LAW_RUNE]
        plan = plan_bank_sort(bank(ids))
        expect(plan.mode).to_be('insert')
        expect(len(plan.moves)).to_be(1)
        expect(replay(ids, plan)).to_equal(plan.layout)
    test('a bank sorted then topped up picks insert, and one move per new item', _fn15)

    def _fn16():
        ids = [JUNK_A, MITHRIL_ORE, LOBSTER, SHARK, AIR_RUNE, LAW_RUNE, COINS]
        plan = plan_bank_sort(bank(ids))
        expect(plan.mode).to_be('swap')
        expect(replay(ids, plan)).to_equal(plan.layout)
    test('a reversed bank picks swap, because inserts cost more there', _fn16)

    def _fn17():
        items = [
        Record({'slot': 0, 'id': SHARK, 'name': 'Shark', 'cost': 200}),
        Record({'slot': 4, 'id': COINS, 'name': 'Coins', 'cost': 1}),
    ]
        expect(plan_bank_sort(items).moves).to_equal([])
    test('sparse slots produce an empty plan rather than a wrong one', _fn17)

    def _fn18():
        expect(plan_bank_sort([]).moves).to_equal([])
    test('an empty bank plans nothing', _fn18)

    def _fn19():
        ids = [COINS, SHARK, LAW_RUNE]
        overrides = {_k: _v for _k, _v in [[SHARK, 'questObsolete']]}
        plan = plan_bank_sort(bank(ids), overrides)
        expect(plan.layout).to_equal([COINS, LAW_RUNE, SHARK])
    test('an override outranks the rule table', _fn19)

    def _fn20():
        # Why: a seeded LCG so a failure is reproducible.
        seed = [12345]

        def next_():
            seed[0] = (seed[0] * 1103515245 + 12345) & 0x7fffffff
            return seed[0]
        pool = [COINS, AIR_RUNE, LAW_RUNE, SHARK, LOBSTER, MITHRIL_ORE, JUNK_A, JUNK_B]
        for round_ in range(200):
            ids = pool[0:2 + (next_() % (len(pool) - 1))]
            for i in range(len(ids) - 1, 0, -1):
                j = next_() % (i + 1)
                ids[i], ids[j] = [ids[j], ids[i]]
            for force in [None, 'swap', 'insert']:
                plan = plan_bank_sort(bank(ids), None, force)
                expect(Record({'round': round_, 'force': force, 'got': replay(ids, plan)})).to_equal(Record({'round': round_, 'force': force, 'got': plan.layout}))
    test('both plans reach the layout on 200 shuffled banks', _fn20)

    def _fn21():
        ids = [JUNK_B, MITHRIL_ORE, COINS, LOBSTER, AIR_RUNE, JUNK_A, SHARK, LAW_RUNE]
        plan = plan_bank_sort(bank(ids), None, 'swap')
        stationary = len([id for i, id in enumerate(plan.layout) if id == ids[i]])
        expect(len(plan.moves)).to_be_less_than_or_equal(len(ids) - max(1, stationary))
    test('the swap plan never beats the cycle bound', _fn21)

    def _fn22():
        ids = [COINS, AIR_RUNE, SHARK, LOBSTER, MITHRIL_ORE, JUNK_A, LAW_RUNE]
        expect(plan_bank_sort(bank(ids)).mode).to_be('insert')
        forced = plan_bank_sort(bank(ids), None, 'swap')
        expect(forced.mode).to_be('swap')
        expect(replay(ids, forced)).to_equal(forced.layout)
    test('force pins the mode even when the other is cheaper', _fn22)


describe('planBankSort', _fn7)


def _fn23():
    def tiered(rows):
        """Costs run opposite to the wanted order everywhere, so any layout below is rank winning over price."""
        return [Record({'slot': slot, 'id': rows[slot][0], 'name': rows[slot][1], 'cost': rows[slot][2]}) for slot in range(len(rows))]

    def layout_of(rows):
        items = tiered(rows)
        by_id = {_k: _v for _k, _v in [[i.id, i.name] for i in items]}
        return [by_id.get(id) for id in plan_bank_sort(items).layout]

    def _fn25():
        expect(layout_of([
        [451, 'Runite ore', 20000],
        [2349, 'Bronze bar', 8],
        [436, 'Copper ore', 3],
        [453, 'Coal', 45],
        [2363, 'Runite bar', 40000],
        [440, 'Iron ore', 17],
    ])).to_equal(['Copper ore', 'Iron ore', 'Coal', 'Runite ore', 'Bronze bar', 'Runite bar'])
    test('ores and bars run copper to rune, cheapest first, against the price tiebreak', _fn25)

    def _fn26():
        expect(layout_of([
        [1277, 'Bronze sword', 26],
        [436, 'Copper ore', 3],
        [1215, 'Dragon dagger', 30000],
        [451, 'Runite ore', 20000],
        [1333, 'Rune scimitar', 15000],
    ])).to_equal(['Dragon dagger', 'Rune scimitar', 'Bronze sword', 'Copper ore', 'Runite ore'])
    test('weapons run dragon to bronze while ores run copper to rune in the same bank', _fn26)

    def _fn27():
        expect(layout_of([
        [1631, 'Uncut dragonstone', 20000],
        [1607, 'Sapphire', 250],
        [1615, 'Dragonstone', 22000],
        [989, 'Crystal key', 1],
        [1623, 'Uncut sapphire', 200],
    ])).to_equal(['Crystal key', 'Dragonstone', 'Sapphire', 'Uncut dragonstone', 'Uncut sapphire'])
    test('keys sit with the cut dragonstone, and cut gems come before uncut', _fn27)

    def _fn28():
        expect(layout_of([
        [556, 'Air rune', 4],
        [563, 'Law rune', 240],
        [565, 'Blood rune', 400],
        [554, 'Fire rune', 4],
        [558, 'Mind rune', 3],
    ])).to_equal(['Blood rune', 'Mind rune', 'Law rune', 'Air rune', 'Fire rune'])
    test('runes run combat, utility, then elemental, cheap fire rune last', _fn28)

    def _fn29():
        expect(layout_of([[1513, 'Magic logs', 1000], [1511, 'Logs', 4], [1515, 'Yew logs', 400]])).to_equal(['Logs', 'Yew logs', 'Magic logs'])
        expect(layout_of([[882, 'Bronze arrow', 1], [892, 'Rune arrow', 260], [886, 'Steel arrow', 12]])).to_equal(['Rune arrow', 'Steel arrow', 'Bronze arrow'])
    test('logs run in woodcutting order and arrows run rune to bronze', _fn29)

    def _fn30():
        # Why: asserted on ids, because every unidentified herb reads back as the same "Herb".
        expect(plan_bank_sort(tiered([
        [219, 'Herb', 1],
        [269, 'Torstol', 6000],
        [249, 'Guam leaf', 10],
        [199, 'Herb', 1],
        [257, 'Ranarr weed', 4000],
    ])).layout).to_equal([249, 257, 269, 199, 219])
    test('herbs run in identify order, unidentified ones behind the clean ones', _fn30)

    def _fn31():
        expect(layout_of([
        [1305, 'Dragon longsword', 100000],
        [4151, 'Abyssal whip', 2000000],
        [1307, 'Granite maul', 1500],
        [1333, 'Rune scimitar', 15000],
    ])).to_equal(['Dragon longsword', 'Rune scimitar', 'Abyssal whip', 'Granite maul'])
    test('an item the rank table does not name falls behind the ones it does, then sorts on price', _fn31)


describe('planBankSort ranks within a category', _fn23)

