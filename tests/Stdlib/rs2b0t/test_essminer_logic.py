"""rs2b0t's test/scripts/EssMiner/essminer-logic.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect.
Here resolve_pick gives (kind, item) or ('stop', reason), and withdraw_op(ops, '1') is withdrawOneOp. EssMinerChat's
tests stub the chat facade, which pocketpy can't (see BotApiParityDesign.md §5, "As built")."""

from rs2004.catalogs import in_ess_mine

from bots.ess_miner import BEST_AVAILABLE, ESS_ITEM, PICK_OPTIONS, PICK_TIERS, desired_pickaxe, held_pickaxe_to_keep, needs_pickaxe_check, required_mining_level, resolve_pick


def _fn1():
    def _fn2():
        expect([[t.item, t.level] for t in PICK_TIERS]).to_equal([
            ['Rune pickaxe', 41], ['Adamant pickaxe', 31], ['Mithril pickaxe', 21], ['Steel pickaxe', 6], ['Iron pickaxe', 1], ['Bronze pickaxe', 1]])
    test('best-first with the content levelrequire values (pickaxes.obj)', _fn2)

    def _fn3():
        expect(PICK_OPTIONS).to_equal([BEST_AVAILABLE, 'Rune', 'Adamant', 'Mithril', 'Steel', 'Iron', 'Bronze'])
    test('dropdown options are Best available + every tier', _fn3)


describe('PICK_TIERS', _fn1)


def _fn4():
    def _fn5():
        expect(required_mining_level('Rune')).to_be(41)
        expect(required_mining_level('steel')).to_be(6)
        expect(required_mining_level(BEST_AVAILABLE)).to_be_null()
        expect(required_mining_level('Dragon')).to_be_null()
    test('specific tiers report their gate; Best available and unknowns do not', _fn5)


describe('requiredMiningLevel', _fn4)


def _fn6():
    def _fn7():
        expect(desired_pickaxe(BEST_AVAILABLE, 50).item).to_be('Rune pickaxe')
        expect(desired_pickaxe(BEST_AVAILABLE, 40).item).to_be('Adamant pickaxe')
        expect(desired_pickaxe(BEST_AVAILABLE, 20).item).to_be('Steel pickaxe')
    test('Best available resolves the exact highest tier the level can use', _fn7)

    def _fn8():
        expect(desired_pickaxe('Mithril', 50).item).to_be('Mithril pickaxe')
        expect(desired_pickaxe('Mithril', 20)).to_be_null()
    test('specific selections remain exact and level-gated', _fn8)


describe('desiredPickaxe', _fn6)


def _fn9():
    def _fn10():
        expect(needs_pickaxe_check('Adamant pickaxe', BEST_AVAILABLE, 40)).to_be(False)
        expect(needs_pickaxe_check('Adamant pickaxe', BEST_AVAILABLE, 41)).to_be(True)
        expect(needs_pickaxe_check('Rune pickaxe', BEST_AVAILABLE, 42)).to_be(False)
    test('re-arms only when a Mining threshold unlocks another tier', _fn10)


describe('needsPickaxeCheck', _fn9)


def _fn11():
    def _fn12():
        expect(resolve_pick(BEST_AVAILABLE, 50, ['Bronze pickaxe', 'Rune pickaxe'], [])).to_equal(('held', 'Rune pickaxe'))
    test('best available prefers the best usable tier that is held', _fn12)

    def _fn13():
        expect(resolve_pick(BEST_AVAILABLE, 40, ['Rune pickaxe', 'Steel pickaxe'], [])).to_equal(('held', 'Steel pickaxe'))
    test('best available skips tiers above the mining level', _fn13)

    def _fn14():
        expect(resolve_pick(BEST_AVAILABLE, 50, ['Bronze pickaxe'], ['Rune pickaxe'])).to_equal(('held', 'Bronze pickaxe'))
    test('any held usable tier beats a better one that is only banked', _fn14)

    def _fn15():
        expect(resolve_pick(BEST_AVAILABLE, 50, [], ['Bronze pickaxe', 'Adamant pickaxe'])).to_equal(('withdraw', 'Adamant pickaxe'))
    test('nothing held: withdraw the best usable tier from the bank', _fn15)

    def _fn16():
        kind, reason = resolve_pick(BEST_AVAILABLE, 5, [], [])
        expect(kind).to_be('stop')
        expect(reason).to_contain('Bronze pickaxe')
        expect(reason).not_.to_contain('Steel pickaxe')
    test('nothing anywhere: stop with the usable tier list', _fn16)

    def _fn17():
        expect(resolve_pick('Rune', 40, ['Rune pickaxe'], [])).to_equal(('stop', 'Mining 41 required for the Rune pickaxe (have 40)'))
    test('specific tier below the mining level stops with the gate', _fn17)

    def _fn18():
        expect(resolve_pick('Steel', 30, ['Steel pickaxe', 'Rune pickaxe'], [])).to_equal(('held', 'Steel pickaxe'))
        expect(resolve_pick('Steel', 30, ['Bronze pickaxe'], ['Steel pickaxe'])).to_equal(('withdraw', 'Steel pickaxe'))
        expect(resolve_pick('Steel', 30, ['Bronze pickaxe'], ['Rune pickaxe'])[0]).to_be('stop')
    test('specific tier: held wins, then bank, then stop — never a fallback tier', _fn18)

    def _fn19():
        expect(resolve_pick(BEST_AVAILABLE, 50, ['rune PICKAXE'], [])).to_equal(('held', 'Rune pickaxe'))
    test('name matching is case-insensitive', _fn19)


describe('resolvePick', _fn11)


def _fn20():
    def _fn21():
        expect(held_pickaxe_to_keep(BEST_AVAILABLE, 50, ['Bronze pickaxe', 'Rune pickaxe', 'Logs'])).to_be('Rune pickaxe')
    test('keeps only the best usable held tier for Best available', _fn21)

    def _fn22():
        expect(held_pickaxe_to_keep(BEST_AVAILABLE, 40, ['Rune pickaxe', 'Steel pickaxe'])).to_be('Steel pickaxe')
    test('does not preserve a higher tier the miner cannot use', _fn22)

    def _fn23():
        expect(held_pickaxe_to_keep('Bronze', 50, ['Rune pickaxe', 'Bronze pickaxe'])).to_be('Bronze pickaxe')
    test('specific tier settings remain authoritative', _fn23)

    def _fn24():
        expect(held_pickaxe_to_keep(BEST_AVAILABLE, 50, ['Logs', 'Coins'])).to_be_null()
    test('returns null when no selected usable pickaxe is held', _fn24)


describe('heldPickaxeToKeep', _fn20)


def _fn25():
    def _fn26():
        expect(in_ess_mine(2880, 4800)).to_be(True)
        expect(in_ess_mine(2943, 4863)).to_be(True)
        expect(in_ess_mine(2879, 4800)).to_be(False)
        expect(in_ess_mine(2880, 4799)).to_be(False)
        expect(in_ess_mine(2944, 4800)).to_be(False)
        expect(in_ess_mine(3253, 3418)).to_be(False)
    test('mapsquare 45_75 boundaries', _fn26)


describe('inEssMine', _fn25)


def _fn27():
    def _fn28():
        expect(ESS_ITEM).to_be('Rune essence')
    test('matches the blankrune obj display name', _fn28)


describe('ESS_ITEM', _fn27)


def _fn29():
    def _fn30():
        expect(withdraw_op(['Withdraw 1'], '1')).to_be('Withdraw 1')
    test('matches the real "Withdraw 1" label (a space)', _fn30)

    def _fn31():
        expect(withdraw_op(['Withdraw-1'], '1')).to_be('Withdraw-1')
    test('also matches the hyphenated "Withdraw-1" default', _fn31)

    def _fn32():
        expect(withdraw_op(['Withdraw 10', 'Withdraw All', 'Withdraw X'], '1')).to_be_null()
    test('anchored — never matches "Withdraw 10"/All/X', _fn32)

    def _fn33():
        expect(withdraw_op([None, 'Withdraw 5', 'Withdraw 1', 'Withdraw 10', 'Withdraw All', 'Withdraw X'], '1')).to_be('Withdraw 1')
    test('picks "Withdraw 1" out of a realistic op list', _fn33)

    def _fn34():
        expect(withdraw_op([], '1')).to_be_null()
    test('empty op list returns null', _fn34)

    def _fn35():
        expect(withdraw_op(['WITHDRAW 1'], '1')).to_be('WITHDRAW 1')
    test('case-insensitive', _fn35)


describe('withdrawOneOp', _fn29)
