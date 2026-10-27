"""Ported from rs2b0t's src/bot/api/ai/quests/defs/piratestreasure/crate.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.entities import locs
from rs2004.messages import game_messages
from rs2004.quests.defs.piratestreasure.areas import PT_LOC, PT_TILE
from rs2004.quests.exec.prompts import settle_scene
from rs2004.traversal import traversal


__all__ = ['CRATE_FULL', 'read_crate_messages', 'search_banana_crate']

CRATE_FULL = 10


def read_crate_messages(lines):
    """`[oploc1,bananacrate]` prints both varps the client cannot read."""
    text = ' '.join(lines).lower()
    rum = ('there is some rum in here' in text) or ('there is also some rum stashed in here' in text)
    if ('the crate is completely empty' in text):
        return Record({'rum': False, 'bananas': 0})
    if ('the crate is full of bananas' in text):
        return Record({'rum': rum, 'bananas': CRATE_FULL})

    prefix = 'the crate has '
    if prefix in text:
        tail = text.split(prefix)[1]
        number = tail.split(' ')[0]
        if number and all([ch in '0123456789' for ch in number]) and (' banana inside' in tail or ' bananas inside' in tail):
            return Record({'rum': rum, 'bananas': int(number)})
    if rum:
        return Record({'rum': True, 'bananas': 0})
    return None


def search_banana_crate(log):
    """Walk to the plantation crate, Search it, and read what it says back."""
    _w1 = yield from traversal.walk_resilient(PT_TILE.BANANA_CRATE, radius=2, attempts=3, timeout_ms=180000, log=log)
    if not (_w1):
        log('could not reach the plantation crate')
        return None
    yield from settle_scene()
    crate = locs.query().where(lambda l: l.id == PT_LOC.BANANA_CRATE).action('Search').within(6).nearest()
    if not crate:
        log('no searchable Crate at the plantation')
        return None
    mark = game_messages.mark()
    if not (crate.interact('Search')):
        return None

    def said():
        return [m.text for m in game_messages.since(mark)]

    yield from execution.delay_until(lambda: read_crate_messages(said()) is not None, 8000)
    state = read_crate_messages(said())
    if state:
        log(f'plantation crate: rum={state.rum} bananas={state.bananas}')
    else:
        log(f"plantation crate said nothing readable: [{' | '.join(said())}]")
    return state
