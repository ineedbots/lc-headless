"""rs2b0t's test/scripts/MuleCrafter/MuleCrafterLogic.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs import Record
from bots.mule_crafter import RUNES, RUNE_OPTIONS, bank_tile, classify_mule_state, is_configured_partner


def _fn1():
    def _fn2():
        def _fn3():
            # Why: asserting the full list re-breaks whenever an altar is added, so pin the shape rather than the census.
            expect(len(list(RUNES.keys()))).to_be_greater_than_or_equal(2)
            for key in RUNES.keys():
                # rs2b0t's /^[A-Z][a-z]+ rune$/.
                word = key[:len(key) - len(' rune')]
                expect(key.endswith(' rune') and len(word) > 1 and word[0] != word[0].lower() and word[1:] == word[1:].lower() and ' ' not in word, key).to_be(True)
        test('keys are singular rune names', _fn3)

        def _fn4():
            air = RUNES.get('Air rune')
            expect(air.rune).to_be('Air rune')
            expect(air.talisman).to_be('Air talisman')
            expect(air.level).to_be(1)
            expect(air.bank).to_be('Falador East')
            expect(air.ruins.x).to_be(2983)
            expect(air.ruins.z).to_be(3288)
        test('Air rune route has correct data', _fn4)

        def _fn5():
            mind = RUNES.get('Mind rune')
            expect(mind.rune).to_be('Mind rune')
            expect(mind.talisman).to_be('Mind talisman')
            expect(mind.level).to_be(2)
            expect(mind.bank).to_be('Edgeville')
            expect(mind.ruins.x).to_be(2980)
            expect(mind.ruins.z).to_be(3511)
        test('Mind rune route has correct data', _fn5)

        def _fn6():
            # `bank` became a BANK_LOCATIONS name rather than a Tile; this is what that
            # indirection has to guarantee, and it catches a typo in any new row.
            for route in list(RUNES.values()):
                expect(lambda: bank_tile(route.bank)).not_.to_throw()
        test('every route names a bank that resolves to a real tile', _fn6)
    describe('RUNES', _fn2)

    def _fn7():
        def _fn8():
            expect(RUNE_OPTIONS).to_equal(list(RUNES.keys()))
        test('matches RUNES keys', _fn8)
    describe('RUNE_OPTIONS', _fn7)

    def _fn9():
        def _fn10():
            expect(is_configured_partner(None, ['Player1'])).to_be(False)
        test('returns false for null name', _fn10)

        def _fn11():
            expect(is_configured_partner('Player1', [])).to_be(False)
        test('returns false for empty configured partners', _fn11)

        def _fn12():
            expect(is_configured_partner('Player1', ['Player1'])).to_be(True)
        test('exact match returns true', _fn12)

        def _fn13():
            expect(is_configured_partner('player1', ['Player1'])).to_be(True)
            expect(is_configured_partner('PLAYER1', ['Player1'])).to_be(True)
        test('case insensitive match', _fn13)

        def _fn14():
            expect(is_configured_partner('Player_One', ['Player One'])).to_be(True)
            expect(is_configured_partner('Player One', ['Player_One'])).to_be(True)
        test('underscore normalization', _fn14)

        def _fn15():
            expect(is_configured_partner('Player' + chr(0xA0) + 'One',['Player One'])).to_be(True)
        test('non-breaking space normalization', _fn15)

        def _fn16():
            expect(is_configured_partner('Player2', ['Player1', 'Player2', 'Player3'])).to_be(True)
        test('multiple partners - matches any', _fn16)

        def _fn17():
            expect(is_configured_partner('PlayerX', ['Player1', 'Player2'])).to_be(False)
        test('no match returns false', _fn17)
    describe('DEFAULT_RUNE', _fn9)

    def _fn18():
        def _fn19():
            offer = [Record({'id': 1436, 'name': 'Rune essence', 'count': 10})]
            expect(classify_mule_state(offer)).to_be('has-essence')
        test('has essence returns has-essence', _fn19)

        def _fn20():
            offer = [
        Record({'id': 1436, 'name': 'Rune essence', 'count': 5}),
        Record({'id': 1436, 'name': 'Rune essence', 'count': 5}),
    ]
            expect(classify_mule_state(offer)).to_be('has-essence')
        test('multiple essence items sums correctly', _fn20)

        def _fn21():
            offer = [Record({'id': 556, 'name': 'Air rune', 'count': 27})]
            expect(classify_mule_state(offer)).to_be('empty')
        test('no essence returns empty', _fn21)

        def _fn22():
            expect(classify_mule_state([])).to_be('empty')
        test('empty offer returns empty', _fn22)

        def _fn23():
            offer = [Record({'id': 1436, 'name': 'rune essence', 'count': 10})]
            expect(classify_mule_state(offer)).to_be('has-essence')
        test('case insensitive essence name', _fn23)

        def _fn24():
            offer = [Record({'id': 1436, 'name': 'Rune Essence', 'count': 10})]
            expect(classify_mule_state(offer)).to_be('has-essence')
        test('mixed case essence name', _fn24)

        def _fn25():
            offer = [Record({'id': 1436, 'name': 'Rune essence', 'count': 0})]
            expect(classify_mule_state(offer)).to_be('empty')
        test('zero count essence returns empty', _fn25)
    describe('classifyMuleState', _fn18)


describe('MuleCrafterLogic', _fn1)

