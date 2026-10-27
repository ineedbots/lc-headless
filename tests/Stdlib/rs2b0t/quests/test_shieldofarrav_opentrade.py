"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/shieldofarrav-opentrade.test.ts (MIT, see thirdparty/rs2b0t)."""
from rs2004.partner_handoff import OPEN_REQUEST_EVERY_MS, decide_open_trade
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot
base = Fake(**{'trade_active': False, 'partner_near': True, 'now_ms': 0, 'deadline_ms': 90000, 'next_request_at_ms': 0})

def _fn1():

    def _fn2():
        _merged3 = {}
        for _k, _v in (base._fields if isinstance(base, (Record, Fake)) else base).items():
            _merged3[_k] = _v
        for _k, _v in {'trade_active': True}.items():
            _merged3[_k] = _v
        expect(decide_open_trade(Fake(**_merged3))).to_be('done')
    test('an open window is done', _fn2)

    def _fn4():
        _merged5 = {}
        for _k, _v in (base._fields if isinstance(base, (Record, Fake)) else base).items():
            _merged5[_k] = _v
        for _k, _v in {'trade_active': True, 'now_ms': 99000}.items():
            _merged5[_k] = _v
        expect(decide_open_trade(Fake(**_merged5))).to_be('done')
    test('an open window wins over an expired budget', _fn4)

    def _fn6():
        _merged7 = {}
        for _k, _v in (base._fields if isinstance(base, (Record, Fake)) else base).items():
            _merged7[_k] = _v
        for _k, _v in {'partner_near': False}.items():
            _merged7[_k] = _v
        expect(decide_open_trade(Fake(**_merged7))).to_be('wait')
    test('a partner out of trade range is waited for, never given up on', _fn6)

    def _fn8():
        now = 0
        while now < 60000:
            _merged9 = {}
            for _k, _v in (base._fields if isinstance(base, (Record, Fake)) else base).items():
                _merged9[_k] = _v
            for _k, _v in {'partner_near': False, 'now_ms': now, 'next_request_at_ms': 0}.items():
                _merged9[_k] = _v
            expect(decide_open_trade(Fake(**_merged9))).to_be('wait')
            now += 2000
    test('a partner out of trade range is never clicked at', _fn8)

    def _fn10():
        _merged11 = {}
        for _k, _v in (base._fields if isinstance(base, (Record, Fake)) else base).items():
            _merged11[_k] = _v
        for _k, _v in {'now_ms': 5000, 'next_request_at_ms': 5000}.items():
            _merged11[_k] = _v
        expect(decide_open_trade(Fake(**_merged11))).to_be('request')
    test('a partner in range is requested when the throttle has elapsed', _fn10)

    def _fn12():
        _merged13 = {}
        for _k, _v in (base._fields if isinstance(base, (Record, Fake)) else base).items():
            _merged13[_k] = _v
        for _k, _v in {'now_ms': 1000, 'next_request_at_ms': OPEN_REQUEST_EVERY_MS}.items():
            _merged13[_k] = _v
        expect(decide_open_trade(Fake(**_merged13))).to_be('wait')
    test('a partner in range is not re-requested inside the throttle', _fn12)

    def _fn14():
        next_ = 0
        sent = 0
        now = 0
        while now < 20000:
            _merged15 = {}
            for _k, _v in (base._fields if isinstance(base, (Record, Fake)) else base).items():
                _merged15[_k] = _v
            for _k, _v in {'now_ms': now, 'next_request_at_ms': next_}.items():
                _merged15[_k] = _v
            if decide_open_trade(Fake(**_merged15)) == 'request':
                sent += 1
                next_ = now + OPEN_REQUEST_EVERY_MS
            now += 500
        expect(sent).to_be_greater_than(1)
    test('the request repeats while the partner stays in range', _fn14)

    def _fn16():
        _merged17 = {}
        for _k, _v in (base._fields if isinstance(base, (Record, Fake)) else base).items():
            _merged17[_k] = _v
        for _k, _v in {'now_ms': 90000}.items():
            _merged17[_k] = _v
        expect(decide_open_trade(Fake(**_merged17))).to_be('give-up')
        _merged18 = {}
        for _k, _v in (base._fields if isinstance(base, (Record, Fake)) else base).items():
            _merged18[_k] = _v
        for _k, _v in {'now_ms': 90001, 'partner_near': False}.items():
            _merged18[_k] = _v
        expect(decide_open_trade(Fake(**_merged18))).to_be('give-up')
    test('the budget running out gives up', _fn16)
describe('decideOpenTrade', _fn1)

def snapshot_fields(**fields):
    for name in ['inv', 'inv_ids', 'bank', 'bank_ids']:
        if isinstance(fields.get(name), (Record, Fake)):
            fields[name] = fields[name]._fields
    return QuestSnapshot(**fields)
