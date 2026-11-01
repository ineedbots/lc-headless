"""Ported from rs2b0t's src/bot/api/ai/quests/defs/fremenniktrials/merchant.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.defs.fremenniktrials.areas import ASKELADDEN, BRUNDT, FISHERMAN, FT_ID, MANNI, MERCHANT_FIRST, OLAF, PEER, SAILOR, SIGLI, SIGMUND, SKULGRIMEN, SWENSEN, THORA, THORVALD, YRSA
from rs2004.quests.defs.fremenniktrials.supplies import gather_coins, held_id, walk_to
from rs2004.quests.engine.types import has_flag
from rs2004.quests.exec.primitives import talk_through

__all__ = ['merchant_step']

ASKELADDEN_FEE = 5000
# Why: every trade is one item in, one item out, so what is carried names the next councillor without any journal read.
HANDOVER = [
    Record({'id': FT_ID.FLOWER, 'label': 'Exotic flower', 'to': SIGMUND}),
    Record({'id': FT_ID.BALLAD, 'label': 'Fremennik ballad', 'to': SAILOR}),
    Record({'id': FT_ID.STURDY_BOOTS, 'label': 'Sturdy boots', 'to': OLAF}),
    Record({'id': FT_ID.FISCAL_STATEMENT, 'label': 'Fiscal statement', 'to': YRSA}),
    Record({'id': FT_ID.HUNTERS_MAP, 'label': 'Hunters map', 'to': BRUNDT}),
    Record({'id': FT_ID.BOWSTRING, 'label': 'Custom bow string', 'to': SIGLI}),
    Record({'id': FT_ID.UNUSUAL_FISH, 'label': 'Unusual fish', 'to': SKULGRIMEN}),
    Record({'id': FT_ID.SEA_MAP, 'label': 'Sea fishing map', 'to': FISHERMAN}),
    Record({'id': FT_ID.FORECAST, 'label': 'Weather forecast', 'to': SWENSEN}),
    Record({'id': FT_ID.WARRIORS_CONTRACT, 'label': "Warriors' contract", 'to': PEER}),
    Record({'id': FT_ID.CHAMPIONS_TOKEN, 'label': 'Champions token', 'to': THORVALD}),
    Record({'id': FT_ID.COCKTAIL, 'label': 'Legendary cocktail', 'to': MANNI}),
    Record({'id': FT_ID.PROMISSORY_NOTE, 'label': 'Promissory note', 'to': THORA}),
]
ASK = Record({
    'olaf': YRSA,
    'yrsa': BRUNDT,
    'chief': SIGLI,
    'sigli': SKULGRIMEN,
    'skul': FISHERMAN,
    'fisherman': SWENSEN,
    'swensen': PEER,
    'seer': THORVALD,
    'thorvald': MANNI,
    'manni': THORA,
})


def merchant_at(progress):
    for flag in (progress.flags if progress is not None else []):
        if flag.startswith('merchant-at:'):
            return flag[len('merchant-at:'):]
    return None


def merchant_step(snap):
    """Sigmund's trial: trade a promissory note up 11 hands into the exotic flower."""
    if has_flag(snap.progress, 'merchant-done'):
        return None
    if not has_flag(snap.progress, 'merchant-started'):
        return Record({'kind': 'talk', 'stop': SIGMUND(['Yes'])})
    carrying = ([entry for entry in HANDOVER if held_id(snap, entry.id) > 0] or [None])[0]
    if carrying:
        return Record({'kind': 'talk', 'stop': carrying.to(MERCHANT_FIRST)})
    at = merchant_at(snap.progress)
    if at is None:
        return Record({'kind': 'custom', 'name': 'ask the Sailor and then Olaf about the flower', 'run': open_chain})
    if at == 'thora':
        _v1 = gather_coins(snap, ASKELADDEN_FEE)
        return (_v1 if _v1 is not None else Record({'kind': 'talk', 'stop': ASKELADDEN(list(MERCHANT_FIRST) + ['Yes'])}))
    next_ = ASK.get(at)
    if not next_:
        return Record({'kind': 'wait', 'reason': f'the merchant trial is at an unmapped step \'{at}\''})
    return Record({'kind': 'talk', 'stop': next_(MERCHANT_FIRST)})


# Why: `sigmund_started` and `sigmund_spoke_sailor` render the same journal page, so the 2 openings are one step.
def open_chain(log):
    _w2 = yield from walk_to(SAILOR([]).anchor, 2, log)
    if not (_w2):
        return False
    _w3 = yield from talk_through('Sailor', MERCHANT_FIRST, log)
    if not (_w3):
        return False
    _w4 = yield from walk_to(OLAF([]).anchor, 2, log)
    if not (_w4):
        return False
    _result5 = yield from talk_through('Olaf the Bard', MERCHANT_FIRST, log)
    return _result5
