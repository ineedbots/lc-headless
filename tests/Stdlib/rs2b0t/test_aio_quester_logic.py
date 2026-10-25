"""rs2b0t's test/scripts/AIOQuester/AIOQuesterLogic.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect.
Its applyLegendsSettings cases come with Legends' Quest."""

from rs2004.catalogs.record import Record
from bots.aioquester.logic import resolve_consume_action, resolve_sustain_policy, select_sustain_consumable


def food(name, ops=None):
    if ops is None:
        ops = ['Eat']
    return Record({'name': name, 'actions': lambda: ops})


def _fn1():
    def _fn2():
        expect(resolve_consume_action(['Use', 'Eat', 'Drop'])).to_be('Eat')
        expect(resolve_consume_action(['drink', 'Drop'])).to_be('drink')
    test('uses the exact offered Eat or Drink operation', _fn2)

    def _fn3():
        expect(resolve_consume_action(['Use', 'Drop'])).to_be_null()
    test('fails closed when the item is not consumable', _fn3)


describe('resolveConsumeAction', _fn1)


def _fn4():
    def _fn5():
        policy = resolve_sustain_policy('Lobster')
        for name in ['Cake', '2/3 cake', 'Slice of cake']:
            lobster = food('Lobster')
            cake = food(name)
            expect(select_sustain_consumable([lobster, cake], policy.foods, 6, 10)).to_equal(Record({'item': cake, 'action': 'Eat'}))
    test('a Lobster in the first slot cannot veto any later Cake form that exactly fits', _fn5)

    def _fn6():
        lobster = food('Lobster')
        cake = food('Cake')
        expect(select_sustain_consumable([lobster, cake], ['lobster'], 6, 10)).to_equal(Record({'item': cake, 'action': 'Eat'}))
        expect(select_sustain_consumable([lobster, cake], ['lobster'], 7, 10)).to_be_null()
    test('uses the inclusive no-overheal boundary for the selected Cake form', _fn6)

    def _fn7():
        lobster = food('Lobster')
        cake = food('Slice of cake')
        expect(select_sustain_consumable([lobster, cake], ['lobster', 'slice of cake'], 5, 10)).to_equal(Record({'item': cake, 'action': 'Eat'}))
        expect(select_sustain_consumable([lobster], ['lobster'], 5, 10)).to_equal(Record({'item': lobster, 'action': 'Eat'}))
        cake_first = food('Cake')
        expect(select_sustain_consumable([cake_first, lobster], ['lobster'], 5, 8)).to_equal(Record({'item': lobster, 'action': 'Eat'}))
    test('prefers a fitting Cake over the emergency-floor Lobster fallback', _fn7)

    def _fn8():
        unusable_cake = food('Cake', ['Use', 'Drop'])
        cake_slice = food('Slice of cake', ['eat', 'Drop'])
        expect(select_sustain_consumable([unusable_cake, cake_slice], ['cake', 'slice of cake'], 6, 10)).to_equal(Record({'item': cake_slice, 'action': 'eat'}))
    test('returns the chosen item and its actual operation while ignoring unusable matches', _fn8)

    def _fn9():
        expect((select_sustain_consumable([food('Cake')], ['lobster'], 6, 10).item if select_sustain_consumable([food('Cake')], ['lobster'], 6, 10) is not None else None).name).to_be('Cake')
        expect((select_sustain_consumable([food('2/3 cake')], ['lobster'], 6, 10).item if select_sustain_consumable([food('2/3 cake')], ['lobster'], 6, 10) is not None else None).name).to_be('2/3 cake')
        expect((select_sustain_consumable([food('Slice of cake')], ['lobster'], 6, 10).item if select_sustain_consumable([food('Slice of cake')], ['lobster'], 6, 10) is not None else None).name).to_be('Slice of cake')
        expect(select_sustain_consumable([food('Bread')], ['lobster'], 5, 10)).to_be_null()
        expect(select_sustain_consumable([food('Chocolate cake')], ['lobster'], 5, 10)).to_be_null()
        expect(select_sustain_consumable([food('Rock cake')], ['lobster'], 5, 10)).to_be_null()
    test('implicitly permits only the plain Cake chain outside the active policy', _fn9)

    def _fn10():
        expect(select_sustain_consumable([food('Cake')], ['lobster'], 5, 8)).to_be_null()
        expect((select_sustain_consumable([food('Cake')], ['cake'], 5, 8).item if select_sustain_consumable([food('Cake')], ['cake'], 5, 8) is not None else None).name).to_be('Cake')
    test('does not apply the emergency overfill floor to an implicit Cake', _fn10)


describe('selectSustainConsumable', _fn4)


def _fn11():
    def _fn12():
        expect(resolve_sustain_policy('Trout')).to_equal(Record({'foods': ['trout']}))
    test('uses the configured food when no quest policy is active', _fn12)

    def _fn13():
        expect(resolve_sustain_policy('Trout', Record({'foods': ['Bread'], 'eat_below_hp': 0.95}))).to_equal(Record({'foods': ['bread', 'trout']}))
    test('adds active quest foods ahead of the configured food', _fn13)

    def _fn14():
        expect(resolve_sustain_policy(' BREAD ', Record({'foods': ['Bread', '', ' bread ', 'Tuna'], 'eat_below_hp': 0.75}))).to_equal(Record({'foods': ['bread', 'tuna']}))
    test('trims, ignores empty names, and de-duplicates foods case-insensitively', _fn14)

    def _fn15():
        expect(resolve_sustain_policy(None, Record({'foods': ['Bread'], 'eat_below_hp': 0.95}))).to_equal(Record({'foods': ['bread']}))
    test('allows quest food when the configured food is blank', _fn15)

    def _fn16():
        expect(resolve_sustain_policy('Cake').foods).to_equal(['cake', '2/3 cake', 'slice of cake'])
    test('keeps eating a cake once it has been bitten', _fn16)

    def _fn17():
        expect(resolve_sustain_policy('Meat pie').foods).to_equal(['meat pie', 'half a meat pie'])
        expect(resolve_sustain_policy('Chocolate cake').foods).to_equal(['chocolate cake', '2/3 chocolate cake', 'chocolate slice'])
    test('covers the half-eaten form of every multi-bite food it is given', _fn17)

    def _fn18():
        expect(resolve_sustain_policy('Cake', Record({'foods': ['Cake'], 'eat_below_hp': 0.5})).foods).to_equal(['cake', '2/3 cake', 'slice of cake'])
    test('de-duplicates when a quest food and the configured food share a chain', _fn18)

    def _fn19():
        expect(resolve_sustain_policy(' Shark ').foods).to_equal(['shark'])
    test('leaves single-stage food alone', _fn19)


describe('resolveSustainPolicy', _fn11)
