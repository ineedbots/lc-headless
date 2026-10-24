"""rs2b0t's test/scripts/JiveMarketDumper/settings.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test
and expect. Here because the banks are the walker's data. Its runtime.test.ts stubs the bank and game facades,
which pocketpy can't, so it isn't ported."""

from bots.jive_market_dumper import BOT, NEAREST_BANK, SETTINGS, bank_choice


def _fn1():
    def _fn2():
        expect(list(SETTINGS.keys())).to_equal(['maker', 'bank'])
        expect(SETTINGS['maker'].default).to_be('')
    test('the maker and the bank are what there is to set', _fn2)

    def _fn3():
        expect('price_book' in SETTINGS).to_be(False)
        expect('max_per_trade' in SETTINGS).to_be(False)
    test('no price book and no trade cap, since the dump takes whatever the maker pays', _fn3)

    # Why: the maker stands at a bank of its own choosing, and the nearest one to the dumper is not always that bank.
    def _fn4():
        expect(SETTINGS['bank'].default).to_be(NEAREST_BANK)
        expect(SETTINGS['bank'].options).to_contain(NEAREST_BANK)
        for name in ['Seers', 'Varrock West', 'Falador East']:
            expect(SETTINGS['bank'].options).to_contain(name)
        expect(SETTINGS['bank'].options).to_equal([NEAREST_BANK] + [b['name'] for b in BANK_LOCATIONS])
    test('the bank is picked from the known banks, defaulting to the nearest', _fn4)

    def _fn5():
        expect('bank_stand' in SETTINGS).to_be(False)
        expect('spot' in SETTINGS).to_be(False)
    test('no free-typed tile, so a bank is only ever one the walker knows how to open', _fn5)


describe('JiveMarketDumper settings', _fn1)


def _fn6():
    def _fn7():
        expect(bank_choice('Seers')['name']).to_be('Seers')
        expect(bank_choice('  seers  ')['name']).to_be('Seers')
    test('a named bank resolves to that bank, whatever is nearer', _fn7)

    def _fn8():
        expect(bank_choice(NEAREST_BANK)).to_be_null()
        expect(bank_choice('')).to_be_null()
        expect(bank_choice('Lumbridge')).to_be_null()
    test('the nearest option and an unknown name both resolve to nothing, leaving the walker to pick', _fn8)


describe('bankChoice', _fn6)


def _fn9():
    def _fn10():
        expect(BOT.category).to_be('Money making')
        expect(BOT.tags).to_contain('trading')
        expect(BOT.tags).to_contain('bank')
        expect(BOT.settings_schema).to_be(SETTINGS)
    test('is a Money making script with the trading tags', _fn10)


describe('JiveMarketDumper registration', _fn9)
