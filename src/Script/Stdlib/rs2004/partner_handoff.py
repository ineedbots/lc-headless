"""Ported from rs2b0t's src/bot/api/trade/PartnerHandoff.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.partner import DEFAULT_TRADE_RANGE, names_match
from rs2004.catalogs.record import Record
from rs2004.dialogue import modals
from rs2004.entities import players
from rs2004.game import reader
from rs2004.items import inventory
from rs2004.trade import trade
from rs2004.traversal import traversal

__all__ = ['OPEN_REQUEST_EVERY_MS', 'decide_open_trade', 'run_handoff']

# Why: partner accepts aren't tied to this client's tick rate, so these are wall-clock (7 ticks at 300ms is 2.1s, too short for a mutual Trade).
MEET_MS = 90000
SCREEN_MS = 8000
HANDOFF_MS = 120000
OPEN_REQUEST_EVERY_MS = 3000


# Why: `[opplayer4,_]` opens the window on the second of the two clicks and keeps its varps with no expiry, so re-sending completes a handshake whose first click was dropped.
def decide_open_trade(state):
    trade_active = state.trade_active
    partner_near = state.partner_near
    now_ms = state.now_ms
    deadline_ms = state.deadline_ms
    next_request_at_ms = state.next_request_at_ms
    if trade_active:
        return 'done'
    if now_ms >= deadline_ms:
        return 'give-up'
    if not partner_near:
        return 'wait'
    return ('request' if now_ms >= next_request_at_ms else 'wait')


def partner_near(partner):
    name = partner.strip()
    if len(name) == 0:
        return False
    return players.query().where(lambda p: names_match((p.name if p.name is not None else ''), name)).within(DEFAULT_TRADE_RANGE).nearest() is not None


def open_trade(partner, log):
    """Drive the mutual Trade-with until the window opens, the partner never returns, or the budget runs out."""
    deadline = _core.step_time() + MEET_MS
    next_request_at = 0
    waited_for = False
    while True:
        action = decide_open_trade(Record({'trade_active': trade.active(), 'partner_near': partner_near(partner), 'now_ms': _core.step_time(), 'deadline_ms': deadline, 'next_request_at_ms': next_request_at}))
        if action == 'done':
            return True
        if action == 'give-up':
            log(f'trade with \'{partner}\' never opened within {round(MEET_MS / 1000)}s')
            return False
        if action == 'request':
            if not (trade.request(partner)):
                log(f'could not open a trade with \'{partner}\'')
                return False
            next_request_at = _core.step_time() + OPEN_REQUEST_EVERY_MS
        elif not waited_for and not partner_near(partner):
            # Why: the giver leaves as soon as its own item lands, so the taker's partner is en route.
            log(f'waiting for \'{partner}\' to come back into trade range')
            waited_for = True
        yield from execution.delay_ticks(2)


def run_handoff(spec):
    """Move one object between two bots and prove it landed."""
    partner = spec.partner
    id = spec.id
    name = spec.name
    giving = spec.giving
    label = spec.label
    log = spec.log
    confirmed = False
    # Why: an item moved into the offer is gone from the pack view, so a give is believed only once the window is shut and the pack reads back.
    # Why: the baseline is taken with no window open, because declining an open trade to grab one kills the partner's handshake.
    before = (None if trade.active() else inventory.count_by_id(id))

    def pack_readable():
        return inventory.used() > 0

    def landed():
        now = inventory.count_by_id(id)
        if not giving:
            return (now > 0 if before is None else now > before)
        if trade.active() or not pack_readable():
            return False
        # Why: a giver that keeps one of two is still a giver, so "gone from the pack" is the wrong test.
        return (confirmed if before is None else now < before)

    if landed():
        return True
    if giving and before == 0:
        log(f'nothing to give: no {name} ({id}) in the pack')
        return False
    # Why: a main modal left over from the last conversation swallows the Trade-with click, and the window then never opens for either side.
    if reader.modals().main != -1:
        yield from modals.close()
    _w1 = yield from traversal.walk_resilient(spec.rendezvous, radius=2, attempts=3, timeout_ms=MEET_MS, log=log)
    if not (_w1):
        return False
    # Why: a wait step would park the quest after 15 identical passes, so openTrade owns both the wait for a partner and the clicking.
    _c2 = not trade.active()
    if _c2:
        _w3 = yield from open_trade(partner, log)
        _c2 = not (_w3)
    if _c2:
        return False
    deadline = _core.step_time() + HANDOFF_MS
    offered = False
    last = ''
    while _core.step_time() < deadline:
        # Why: the engine shuts the offer screen a tick before it opens the confirm, so one frame with neither up is the handover.
        if not trade.active():
            yield from execution.delay_ticks(3)
            if not trade.active():
                break
        who = trade.partner()
        if who is not None and not names_match(who, partner):
            log(f'declining a trade from \'{who}\' — not the configured partner')
            trade.decline()
            return False
        screen = ('confirm' if trade.on_confirm_screen() else 'offer')

        def ids(slots):
            return ','.join([f'{s.id}x{s.count}' for s in slots]) or '-'

        state = f'{screen} modal={reader.modals().main} want={id}' + f' mine=[{ids(trade.my_offer())}] theirs=[{ids(trade.their_offer())}]'
        if state != last:
            log(f'{label}: {state}')
            last = state
        if trade.on_confirm_screen():
            trade.accept()
            confirmed = True
            yield from execution.delay_until(lambda: not trade.active(), SCREEN_MS)
            continue
        if giving and not offered:
            # Why: the slot is chosen by id, because more than one object can share the display name.
            _w4 = yield from trade.offer(name, 1, lambda slot: slot.id == id)
            if not (_w4):
                log(f'could not offer {name} ({id})')
                trade.decline()
                return False
            offered = True
            continue
        # Why: the taker must not accept an empty offer. The giver may still be walking to the window.
        if not giving and not any([o.id == id for o in trade.their_offer()]):
            yield from execution.delay_ticks(1)
            continue
        # Why: one accept per screen; the engine sets pending on each click and opens the confirm on the second player's, so re-clicks only race the handover.
        clicked = trade.accept()
        log(f'{label}: accept on {screen} -> {clicked}')
        yield from execution.delay_until(lambda: trade.on_confirm_screen() or not trade.active(), SCREEN_MS)
    # Why: the pack view only comes back once the window is gone, so nothing is measured before then.
    yield from execution.delay_until(lambda: not trade.active(), SCREEN_MS)
    yield from execution.delay_ticks(2)
    if not landed():
        log(f'{label} did not move a {name} (offered={offered} confirmed={confirmed})')
        return False
    log(f'{label} moved a {name}')
    return True
