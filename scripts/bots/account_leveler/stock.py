"""Ported from rs2b0t's src/bot/scripts/AccountLeveler/stock.ts (MIT, see thirdparty/rs2b0t)."""

from bots.account_leveler.record import Record

__all__ = ['LevelerStock']

from bots.account_leveler.supplies import stock_counts
class LevelerStock:
    ready = False

    def __init__(self):
        self._bank = Record({})

    def observe(self, items, ready):
        if not ready:
            return
        self._bank = stock_counts(items)
        self.ready = True

    def total(self, carried):
        _merged1 = {}
        for _k, _v in (self._bank._fields if isinstance(self._bank, Record) else self._bank).items():
            _merged1[_k] = _v
        result = _merged1
        for key, count in stock_counts(carried).items():
            _v2 = result.get(key)
            result[key] = ((_v2 if _v2 is not None else 0)) + count
        return result

    def invalidate(self):
        self.ready = False
        self._bank = Record({})
