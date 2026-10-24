"""Who to trade with, and what to do on the trade screen, for mule and runner bots, and the steps that drive a
partner trade through. Ported from rs2b0t's api/trade/PartnerTrade.ts, drivePartnerTrade.ts and
PartnerHandoff.ts (MIT, see thirdparty/rs2b0t). The trade itself is rs2004.trade's."""

import _core
from rs2004 import execution
from rs2004.dialogue import modals
from rs2004.entities import players
from rs2004.items import inventory
from rs2004.trade import trade
from rs2004.traversal import traversal

DEFAULT_TRADE_RANGE = 2
MULE_MODE_OPTIONS = ['Off', 'Gatherer', 'Mule', 'Cooker', 'Supplier']


def parse_partner_list(raw):
    """Partner names from a comma-separated setting."""
    return [name.strip() for name in raw.split(',') if name.strip()]


def names_match(a, b):
    return a.strip().lower() == b.strip().lower()


def is_configured_partner(name, partners):
    if name is None or not name.strip() or not partners:
        return False
    wanted = name.strip().lower()
    return len([p for p in partners if p.strip().lower() == wanted]) > 0


def count_offer_by_name(items, item_name):
    """The count of offered items with that name; an item's count is at least 1."""
    wanted = item_name.strip().lower()
    return sum([max(1, i.count) for i in items if (i.name or '').strip().lower() == wanted])


def count_offer_matching(items, test):
    return sum([max(1, i.count) for i in items if i.name is not None and test(i.name)])


def decide_receiver_offer_screen(partner_header, partners, my_offer_slots, their_product_count):
    """On the first screen, receiving: ('wait-header',), ('decline', reason), ('wait-offer',) or ('accept',)."""
    if partner_header is None:
        return ('wait-header',)
    if not is_configured_partner(partner_header, partners):
        return ('decline', f'not a configured partner ({partner_header})')
    if my_offer_slots > 0:
        return ('decline', 'safety: own offer not empty')
    if their_product_count <= 0:
        return ('wait-offer',)
    return ('accept',)


def decide_giver_offer_screen(my_offer_slots):
    """On the first screen, giving: 'offer' the haul, then 'accept'."""
    return 'offer' if my_offer_slots <= 0 else 'accept'


def parse_mule_mode(raw):
    mode = raw.strip().lower()
    return mode if mode in ['gatherer', 'mule', 'cooker', 'supplier'] else 'off'


def mule_gatherer_handoff_active(mode, partners, power_mode):
    return mode == 'gatherer' and len(partners) > 0 and not power_mode


def mule_receiver_active(mode, partners):
    return mode == 'mule' and len(partners) > 0


def mule_cooker_active(mode, partners):
    return mode == 'cooker' and len(partners) > 0


def mule_supplier_active(mode, partners, power_mode):
    return mode == 'supplier' and len(partners) > 0 and not power_mode


def mule_non_gatherer_active(mode, partners):
    return mule_receiver_active(mode, partners) or mule_cooker_active(mode, partners) or (mode == 'supplier' and len(partners) > 0)


# Driving a partner trade (drivePartnerTrade.ts). Shared by GatheringBot's mule modes and FlaxRunner's hand-off.
# The policy above decides; these only sequence the screen's clicks and the script's hooks.

# Why: partner accepts and offer sync aren't tied to this client's tick rate, so these are wall-clock: 7 ticks
# is too short for a mutual accept.
TRADE_OFFER_WAIT_MS = 5000
TRADE_CONFIRM_WAIT_MS = 8000


def trade_screen_state():
    """Which trade screen is up, 'offer', 'confirm' or 'closed', for scripts that log hand-back diagnostics."""
    if trade.on_offer_screen():
        return 'offer'
    if trade.on_confirm_screen():
        return 'confirm'
    return 'closed'


def stable_closed_poll(min_ms=600, now_fn=None):
    """A condition that holds once the trade has been shut for `min_ms` without a break.

    Why: the offer-to-confirm swap reports neither screen for a stretch, so closure needs a full tick of
    continuous inactivity."""
    inactive_since = [-1]
    now = now_fn if now_fn is not None else _core.step_time

    def closed():
        if trade.active():
            inactive_since[0] = -1
            return False
        t = now()
        if inactive_since[0] < 0:
            inactive_since[0] = t
        return t - inactive_since[0] >= min_ms

    return closed


def _signed(delta):
    return f"{'+' if delta >= 0 else ''}{delta}"


def _label(labels, key, fallback):
    if labels is None:
        return fallback
    value = labels.get(key) if isinstance(labels, dict) else getattr(labels, key, None)
    return value if value is not None else fallback


def _decline(reason, log, set_status, labels, on_decline, why=None):
    set_status(_label(labels, 'declining', 'mule: declining trade'))
    log(why if why is not None else f'trade: declining ({reason})')
    yield from trade.decline()
    log(f'trade: decline clicked — screen now {trade_screen_state()}')
    if on_decline is not None:
        on_decline(reason)


def _gate_reason(gate):
    """None when a receiver_can_accept answer lets the trade go on, else why not. The answer is a bool, or an
    (ok, reason) pair."""
    if gate is True:
        return None
    if isinstance(gate, tuple):
        return None if gate[0] else (gate[1] if len(gate) > 1 else 'receiver cannot accept offer')
    return 'receiver cannot accept offer'


def _after_offer_accept(log, before, metric):
    stable = stable_closed_poll()
    yield from execution.delay_until(lambda: trade.on_confirm_screen() or stable(), TRADE_OFFER_WAIT_MS)
    if trade.on_confirm_screen():
        log('trade: offer accepted — confirm screen is up')
    elif stable() and not trade.active():
        log(f'trade: window closed after OUR offer-accept without reaching confirm — partner declined, walked or cancelled (inv Δ{_signed(metric() - before)})')
    else:
        log(f'trade: offer-accept wait TIMED OUT — screen now {trade_screen_state()}')


def drive_active_partner_trade(role, partners, their_product_match, product_names_to_offer, set_status, log, on_complete=None, on_decline=None, inventory_metric=None, on_missing_partner=None, receiver_can_accept=None, my_offer_ready=None, baseline=None, verify_giver_partner=False, labels=None):
    """Takes one step of an open partner trade, as the 'giver' or the 'receiver'. Use with yield from.

    The receiver accepts once a configured partner offers product (`their_product_match(name)`); the giver
    offers each of `product_names_to_offer()` with Offer All, then accepts. On the confirm screen both accept,
    and `on_complete(delta)` gets `inventory_metric()` (default `inventory.used()`) after less before, the
    before from `baseline()` when given: a giver's stack leaves the pack at offer time, so a confirm-time
    baseline would read every trade as 0. `on_missing_partner()` answers 'wait' or 'decline' while the
    partner's name hasn't shown; `receiver_can_accept(count)` a bool or (ok, reason); `my_offer_ready()` whether
    the giver's offer is in; `verify_giver_partner` makes the giver check the partner too. `labels` (a dict)
    renames the statuses."""
    metric = inventory_metric if inventory_metric is not None else inventory.used

    if trade.on_confirm_screen():
        set_status(_label(labels, 'confirming', 'mule: confirming trade'))
        before = baseline() if baseline is not None else metric()
        log(f'trade: clicking Accept on the confirm screen ({trade_screen_state()})')
        trade.accept()
        # Both players must confirm; wait wall-clock for the modal to close.
        closed = yield from execution.delay_until(stable_closed_poll(), TRADE_CONFIRM_WAIT_MS)
        log(f"trade: confirm wait {'satisfied' if closed else 'TIMED OUT'} after the last click — screen now {trade_screen_state()}")
        if trade.active():
            log('mule: confirm still open after wait — partner may not have accepted')
            return
        # Why: settle a beat after the modal reports closed; a gather click fired during teardown is swallowed and stalls the loop.
        yield from execution.delay_ticks(1)
        delta = metric() - before
        if on_complete is not None:
            on_complete(delta)
        else:
            log(f'mule: trade complete (inv Δ{_signed(delta)})')
        return

    if not trade.on_offer_screen():
        return

    who = None
    if role == 'receiver' or verify_giver_partner:
        who = trade.partner()
        if who is None:
            action = on_missing_partner() if on_missing_partner is not None else 'wait'
            if action == 'decline':
                yield from _decline('partner header timeout', log, set_status, labels, on_decline, 'trade: declining — partner name never appeared on the modal')
                return
            set_status(_label(labels, 'wait_header', 'mule: reading partner'))
            yield from execution.delay_ticks(1)
            return

    if role == 'receiver':
        their_n = count_offer_matching(trade.their_offer(), their_product_match)
        decision = decide_receiver_offer_screen(who, partners, len(trade.my_offer()), their_n)
        if decision[0] == 'wait-header' or decision[0] == 'wait-offer':
            if decision[0] == 'wait-header':
                set_status(_label(labels, 'wait_header', 'mule: reading partner'))
            else:
                set_status(_label(labels, 'wait_offer', 'mule: waiting for product offer'))
            yield from execution.delay_ticks(1)
            return
        if decision[0] == 'decline':
            yield from _decline(decision[1], log, set_status, labels, on_decline)
            return
        if receiver_can_accept is not None:
            reason = _gate_reason(receiver_can_accept(their_n))
            if reason is not None:
                yield from _decline(reason, log, set_status, labels, on_decline)
                return
        set_status(_label(labels, 'accepting', 'mule: accepting product'))
        before = metric()
        log(f'trade: clicking Accept on the offer screen ({trade_screen_state()})')
        trade.accept()
        # Wait for the confirm screen or the modal's close, so the next beat sees the confirm.
        yield from _after_offer_accept(log, before, metric)
        return

    # The giver: offer the haul, then accept.
    if verify_giver_partner:
        gate = decide_receiver_offer_screen(who, partners, 0, 1)
        if gate[0] == 'decline':
            yield from _decline(gate[1], log, set_status, labels, on_decline)
            return
    ready = my_offer_ready() if my_offer_ready is not None else len(trade.my_offer()) > 0
    if decide_giver_offer_screen(1 if ready else 0) == 'offer':
        names = product_names_to_offer()
        if len(names) == 0:
            set_status('mule: nothing to offer — declining')
            log('trade: declining (nothing to offer)')
            yield from trade.decline()
            log(f'trade: decline clicked — screen now {trade_screen_state()}')
            if on_decline is not None:
                on_decline('nothing to offer')
            return
        set_status(_label(labels, 'offering', f"mule: offering {', '.join(names)}"))
        any_offered = False
        for name in names:
            if trade.offer_all(name):
                any_offered = True
            else:
                log(f'mule: offerAll failed for {name}')
        if not any_offered:
            set_status('mule: declining trade')
            log('trade: declining (offerAll failed for every product)')
            yield from trade.decline()
            log(f'trade: decline clicked — screen now {trade_screen_state()}')
            if on_decline is not None:
                on_decline('offerAll failed')
            return
        # Wait until the offer side shows the product, or the modal dies, before the accept beat.
        settled = stable_closed_poll()

        def offer_shown():
            shown = my_offer_ready() if my_offer_ready is not None else len(trade.my_offer()) > 0
            return shown or trade.on_confirm_screen() or settled()

        yield from execution.delay_until(offer_shown, TRADE_OFFER_WAIT_MS)
        if settled() and not trade.active():
            log('trade: window closed while waiting for the offer to register — partner declined, walked or cancelled')
        return
    before = metric()
    set_status(_label(labels, 'accepting_offer', 'mule: accepting handoff'))
    log(f'trade: clicking Accept on the offer screen ({trade_screen_state()})')
    trade.accept()
    yield from _after_offer_accept(log, before, metric)


# One item between two bots (PartnerHandoff.ts), as the quests' key and herb hand-overs use.

# Why: partner accepts aren't tied to this client's tick rate, so these are wall-clock.
MEET_MS = 90000
SCREEN_MS = 8000
HANDOFF_MS = 120000
# How often the mutual Trade with is clicked again while the partner stands in range.
OPEN_REQUEST_EVERY_MS = 3000


def decide_open_trade(trade_active, partner_near, now_ms, deadline_ms, next_request_at_ms):
    """'done', 'give-up', 'wait' or 'request'.

    Why: [opplayer4,_] opens the window on the second of the two clicks and keeps its varps with no expiry, so
    sending it again completes a handshake whose first click was dropped."""
    if trade_active:
        return 'done'
    if now_ms >= deadline_ms:
        return 'give-up'
    if not partner_near:
        return 'wait'
    return 'request' if now_ms >= next_request_at_ms else 'wait'


def _partner_near(partner):
    name = partner.strip()
    if len(name) == 0:
        return False
    return players.query().where(lambda p: names_match(p.name or '', name)).within(DEFAULT_TRADE_RANGE).nearest() is not None


def _open_trade(partner, log):
    """Drives the mutual Trade with until the window opens, the partner never comes back, or the time runs out."""
    deadline = _core.step_time() + MEET_MS
    next_request_at = 0
    waited_for = False
    while True:
        action = decide_open_trade(trade.active(), _partner_near(partner), _core.step_time(), deadline, next_request_at)
        if action == 'done':
            return True
        if action == 'give-up':
            log(f"trade with '{partner}' never opened within {round(MEET_MS / 1000)}s")
            return False
        if action == 'request':
            if not trade.request(partner):
                log(f"could not open a trade with '{partner}'")
                return False
            next_request_at = _core.step_time() + OPEN_REQUEST_EVERY_MS
        elif not waited_for and not _partner_near(partner):
            # Why: the giver leaves as soon as its own item lands, so the taker's partner is on its way.
            log(f"waiting for '{partner}' to come back into trade range")
            waited_for = True
        yield from execution.delay_ticks(2)


def _offer_ids(slots):
    return ','.join([f'{s.id}x{s.count}' for s in slots]) or '-'


class _Handoff:
    """What run_handoff's checks read, kept on an object, since a closure doesn't see a local rebound later."""

    def __init__(self, id, giving):
        self.id = id
        self.giving = giving
        self.confirmed = False
        # Why: the baseline is taken with no window open, because declining an open trade to grab one kills the partner's handshake.
        self.before = None if trade.active() else inventory.count_by_id(id)

    def landed(self):
        now = inventory.count_by_id(self.id)
        if not self.giving:
            return now > 0 if self.before is None else now > self.before
        # Why: an item moved into the offer is gone from the pack view, so a give is believed only once the window is shut and the pack reads back.
        if trade.active() or inventory.used() <= 0:
            return False
        # Why: a giver that keeps one of two is still a giver, so "gone from the pack" is the wrong test.
        return self.confirmed if self.before is None else now < self.before


def run_handoff(partner, rendezvous, id, name, giving, label, log):
    """Moves one object, by `id` (Key, Herb and Certificate each name several), between this bot and `partner`,
    meeting at `rendezvous`, and proves it landed. `name` is its display name, for the offer click; `label`
    prefixes the log. Use with yield from: True once it has moved."""
    handoff = _Handoff(id, giving)
    if handoff.landed():
        return True
    if giving and handoff.before == 0:
        log(f'nothing to give: no {name} ({id}) in the pack')
        return False

    # Why: a main modal left over from the last conversation swallows the Trade with click, and the window then never opens for either side.
    if modals.main() != -1:
        yield from modals.close()
    arrived = yield from traversal.walk_resilient(rendezvous, radius=2, attempts=3, timeout_ms=MEET_MS, log=log)
    if not arrived:
        return False
    if not trade.active():
        opened = yield from _open_trade(partner, log)
        if not opened:
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
            log(f"declining a trade from '{who}' — not the configured partner")
            yield from trade.decline()
            return False

        screen = 'confirm' if trade.on_confirm_screen() else 'offer'
        state = f'{screen} modal={modals.main()} want={id} mine=[{_offer_ids(trade.my_offer())}] theirs=[{_offer_ids(trade.their_offer())}]'
        if state != last:
            log(f'{label}: {state}')
            last = state

        if trade.on_confirm_screen():
            trade.accept()
            handoff.confirmed = True
            yield from execution.delay_until(lambda: not trade.active(), SCREEN_MS)
            continue

        if giving and not offered:
            # Why: the slot is chosen by id, because more than one object can share the display name.
            put = yield from trade.offer(name, 1, lambda slot: slot.id == id)
            if not put:
                log(f'could not offer {name} ({id})')
                yield from trade.decline()
                return False
            offered = True
            continue

        # Why: the taker must not accept an empty offer. The giver may still be walking to the window.
        if not giving and len([o for o in trade.their_offer() if o.id == id]) == 0:
            yield from execution.delay_ticks(1)
            continue

        # Why: one accept per screen; the engine sets pending on each click and opens the confirm on the second player's, so clicking again only races the handover.
        clicked = trade.accept()
        log(f'{label}: accept on {screen} -> {clicked}')
        yield from execution.delay_until(lambda: trade.on_confirm_screen() or not trade.active(), SCREEN_MS)

    # Why: the pack view only comes back once the window is gone, so nothing is measured before then.
    yield from execution.delay_until(lambda: not trade.active(), SCREEN_MS)
    yield from execution.delay_ticks(2)
    if not handoff.landed():
        log(f'{label} did not move a {name} (offered={offered} confirmed={handoff.confirmed})')
        return False
    log(f'{label} moved a {name}')
    return True
