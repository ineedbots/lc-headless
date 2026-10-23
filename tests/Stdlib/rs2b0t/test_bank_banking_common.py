"""rs2b0t's test/api/bank/banking-common.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""




def _fn1():
    def _fn2():
        for n in ['Uncut sapphire', 'Sapphire', 'Emerald', 'Ruby', 'Diamond', 'Strange fruit', 'Beer', 'Kebab']:
            expect(matches_common_bank_loot(n, -1)).to_be(True)
    test('matches each junk category (case-insensitive contains)', _fn2)

    def _fn3():
        expect(matches_common_bank_loot('Casket', RANDOM_EVENT_CASKET_ID)).to_be(True)
        expect(matches_common_bank_loot('casket', RANDOM_EVENT_CASKET_ID)).to_be(True)
        expect(matches_common_bank_loot('Casket', 2714)).to_be(False)
        expect(matches_common_bank_loot('Casket', 406)).to_be(False)
        expect(matches_common_bank_loot('Rusty casket', 3849)).to_be(False)
    test('matches only the random-event Casket object ID', _fn3)

    def _fn4():
        expect(matches_common_bank_loot('Coins', 995)).to_be(False)
        expect(matches_common_bank_loot('Bones', 526)).to_be(False)
        expect(matches_common_bank_loot('', -1)).to_be(False)
    test('rejects unrelated names and empty', _fn4)

    def _fn5():
        expect(matches_common_bank_loot('Ruby')).to_be(True)
        expect(matches_common_bank_loot('Casket')).to_be(False)
    test('keeps name-only callers compatible without guessing which Casket they mean', _fn5)

    def _fn6():
        expect(len(COMMON_BANK_LOOT)).to_be_greater_than(0)
        expect(all([p == p.lower() for p in COMMON_BANK_LOOT])).to_be(True)
    test('COMMON_BANK_LOOT is non-empty and lowercased', _fn6)


describe('matchesCommonBankLoot', _fn1)


def _fn7():
    def own(n):
        return ('coins' in n.lower())

    def _fn8():
        m = deposit_matcher(own, True)
        expect(m('Coins', 995)).to_be(True)
        expect(m('Ruby', -1)).to_be(True)
        expect(m('Bones', 526)).to_be(False)
    test('own OR common when enabled', _fn8)

    def _fn9():
        m = deposit_matcher(own, False)
        expect(m('Coins', 995)).to_be(True)
        expect(m('Ruby', -1)).to_be(False)
    test('common suppressed when disabled', _fn9)

    def _fn10():
        expect(deposit_matcher(own, True)('Ruby')).to_be(True)
    test('keeps name-only matcher calls compatible', _fn10)

    def _fn11():
        expect(deposit_matcher(lambda *_args: False, True)('Casket', RANDOM_EVENT_CASKET_ID)).to_be(True)
    test('banks a Casket when common rewards are enabled', _fn11)

    def _fn12():
        expect(deposit_matcher(lambda *_args: False, False)('Casket', RANDOM_EVENT_CASKET_ID)).to_be(False)
    test('keeps a Casket when common rewards are disabled', _fn12)

    def _fn13():
        def own_casket(name):
            return name.lower() == 'casket'
        expect(deposit_matcher(own_casket, False)('Casket', RANDOM_EVENT_CASKET_ID)).to_be(True)
    test('the caller predicate still banks its own Casket when common rewards are disabled', _fn13)


describe('depositMatcher', _fn7)


def _fn14():
    def _fn15():
        expect(is_disposable_gather_junk('Uncut sapphire', -1)).to_be(True)
        expect(is_disposable_gather_junk('Strange fruit', -1)).to_be(True)
        expect(is_disposable_gather_junk('Casket', RANDOM_EVENT_CASKET_ID)).to_be(True)
    test('includes common bank loot and random-event casket id', _fn15)

    def _fn16():
        expect(is_disposable_gather_junk('Flier', -1)).to_be(True)
        expect(is_disposable_gather_junk('Half a meat pie', -1)).to_be(True)
        expect(is_disposable_gather_junk('Half a redberry pie', -1)).to_be(True)
        expect(is_disposable_gather_junk('Half an apple pie', -1)).to_be(True)
    test('includes other event leftovers that this content actually has', _fn16)

    def _fn17():
        expect(is_disposable_gather_junk('Rune axe', -1)).to_be(False)
        expect(is_disposable_gather_junk('Coins', 995)).to_be(False)
        expect(is_disposable_gather_junk('Willow logs', -1)).to_be(False)
        expect(is_disposable_gather_junk('Tinderbox', -1)).to_be(False)
    test('rejects tools, coins, logs', _fn17)


describe('isDisposableGatherJunk', _fn14)


def _fn18():
    def _fn19():
        expect(PERIODIC_BANK_SETTINGS.get('bank_common_junk')).to_be_defined()
        expect(PERIODIC_BANK_SETTINGS.get('bank_common_junk').type).to_be('boolean')
        expect(PERIODIC_BANK_SETTINGS.get('bank_common_junk').default).to_be(True)
    test('exposes the bankCommonJunk opt-out, default true', _fn19)


describe('PERIODIC_BANK_SETTINGS', _fn18)


def _fn20():
    def _fn21():
        d = deposit_all_except(['Bones'])
        for junk in ['Casket', 'Strange fruit', 'Beer', 'Kebab', 'Uncut sapphire', 'Cow hide']:
            expect(d(junk), junk).to_be(True)
    test('deposits loot and random-event junk alike', _fn21)

    def _fn22():
        d = deposit_all_except(['Bones', 'Lobster'])
        expect(d('Bones')).to_be(False)
        expect(d('bones')).to_be(False)
        expect(d('LOBSTER')).to_be(False)
        expect(d('')).to_be(False)
    test('keeps the keep-list (case-insensitive), never the empty name', _fn22)

    def _fn23():
        d = deposit_all_except([])
        expect(d('Bones')).to_be(True)
        expect(d('Casket')).to_be(True)
    test('empty keep-list (cow killer, not burying) deposits the whole pack', _fn23)


describe('depositAllExcept', _fn20)
