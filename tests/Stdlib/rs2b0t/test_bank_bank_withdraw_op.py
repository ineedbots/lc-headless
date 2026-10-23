"""rs2b0t's test/api/bank/bank-withdraw-op.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""




def _fn1():
    space_ops = ['Withdraw 1', 'Withdraw 5', 'Withdraw 10', 'Withdraw All', None]
    hyphen_ops = ['Withdraw-1', 'Withdraw-5', 'Withdraw-10', 'Withdraw-All']

    def _fn2():
        expect(withdraw_op(space_ops, 'all')).to_be('Withdraw All')
        expect(withdraw_op(hyphen_ops, 'all')).to_be('Withdraw-All')
    test('resolves the all op in both label forms', _fn2)

    def _fn3():
        expect(withdraw_op(space_ops, '10')).to_be('Withdraw 10')
        expect(withdraw_op(hyphen_ops, '10')).to_be('Withdraw-10')
    test('resolves the 10 op in both label forms', _fn3)

    def _fn4():
        expect(withdraw_op(space_ops, '5')).to_be('Withdraw 5')
        expect(withdraw_op(hyphen_ops, '5')).to_be('Withdraw-5')
        expect(withdraw_op(['Withdraw 10', 'Withdraw-X'], '5')).to_be_null()
    test("'5' is bounded — never catches Withdraw 10", _fn4)

    def _fn5():
        expect(withdraw_op(['Withdraw-X', 'Withdraw-1'], 'x')).to_be('Withdraw-X')
        expect(withdraw_op(['Withdraw X'], 'x')).to_be('Withdraw X')
    test('resolves the x op in both label forms', _fn5)

    def _fn6():
        expect(withdraw_op(space_ops, '1')).to_be('Withdraw 1')
        expect(withdraw_op(['Withdraw 10', 'Withdraw All'], '1')).to_be_null()
    test("'1' is anchored — never catches Withdraw 10", _fn6)

    def _fn7():
        expect(withdraw_op(['Examine', 'Withdraw 5'], 'any')).to_be('Withdraw 5')
        expect(withdraw_op(['Examine', None], 'any')).to_be_null()
        expect(withdraw_op(['Examine', None], 'all')).to_be_null()
    test("'any' takes the first withdraw op; non-withdraw ops never match", _fn7)


describe('withdrawOp', _fn1)
