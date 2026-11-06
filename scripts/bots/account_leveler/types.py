"""Ported from rs2b0t's src/bot/scripts/AccountLeveler/types.ts (MIT, see thirdparty/rs2b0t)."""


__all__ = ['stock_of', 'requirement_key']

def stock_of(snapshot, item):
    _v1 = snapshot.stock.get(item.lower())
    return (_v1 if _v1 is not None else 0)


def requirement_key(need):
    return (need.item if need.id is None else f'#{need.id}')
