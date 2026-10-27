"""Ported from rs2b0t's src/bot/api/ai/quests/barcrawl/RunBarcrawl.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.quests.barcrawl.barcrawl_logic import BARS, COINS
from rs2004.catalogs.record import Record
from rs2004.quests.exec.prompts import drive_until
from rs2004.quests.barcrawl.barcrawl_logic import BARBARIAN_GUARD_ID, BARCRAWL_CARD, BAR_PREFER, BARS, COINS, GATE_IS_OPEN, GUARD_PREFER, GUARD_TILE, TOO_DRUNK, next_bar, parse_card
from rs2004.dialogue import chat_dialog, modals
from rs2004.entities import npcs
from rs2004.game import game, reader
from rs2004.items import inventory
from rs2004.messages import game_messages
from rs2004.quests.exec.prompts import drive_until
from rs2004.reach import reach
from rs2004.traversal import traversal

__all__ = ['read_card', 'ensure_barcrawl']

# Why: the scroll is a main modal built with `if_settext`, so no dialogue driver can see it.
# Why: every other modal read comes back empty while it's up, so it has to be closed again, like a quest journal.
READ_TRIES = 3


def read_card(log=None):
    if not inventory.first(BARCRAWL_CARD):
        return None
    # Why: the previous read's close takes a tick to land, and a `before` sampled while that scroll is still up can't differ from the id the next Read opens, so every read after a successful one times out.
    yield from modals.close_if_open()
    yield from execution.delay_until(lambda: reader.modals().main == -1, 3000)
    before = reader.modals().main
    mark = game_messages.mark()
    # Why: the client clears the modal on close but the server clears it a tick or more later and drops an `opheld` that arrives in between, so the first Read after a read opens nothing.
    # Why: `drinkAt` survived that by reading 3 times; every other caller read once and called the card unreadable.
    id_changed = False
    parsed = None
    attempt = 0
    while attempt < READ_TRIES and not id_changed:
        if attempt > 0:
            yield from execution.delay_ticks(3)
        card = inventory.first(BARCRAWL_CARD)
        if not card:
            return None
        if not (card.interact('Read')):
            if log is not None:
                log('the card refused its Read op')
            return None

        # Why: the modal id arrives in `if_openmain`, each line of the scroll arrives in its own `if_settext`, and component text persists in the interface list between modals.
        # Why: sampling on the tick the id changes therefore reads an empty scroll, or the previous read's.
        # Why: settle a tick and wait for text that parses as the card; the id alone proves nothing.
        def _fn1():
            main = reader.modals().main
            return main != -1 and main != before
        id_changed = yield from execution.delay_until(_fn1, 5000)
        attempt += 1
    if id_changed:
        yield from execution.delay_ticks(1)
        yield from execution.delay_until(lambda: parse_card(reader.main_modal_texts()) is not None, 5000)
        parsed = parse_card(reader.main_modal_texts())
        yield from modals.close_if_open()
    if parsed:
        return parsed
    # Why: `opheld1,barcrawl_card` stops opening the scroll once every bar is signed, and "You are too drunk to be able to read the barcrawl card" is the finished state.
    # Why: taking that line for a failed read leaves the tour looping at the 10th bar forever.
    if game_messages.saw_since(mark, TOO_DRUNK):
        return Record({'remaining': [], 'done': True})
    if log is not None:
        log(('the card scroll opened but never rendered a parseable line' if id_changed else 'the card scroll never opened, and no "too drunk" message came back'))
    return None


def by_id(id):
    return npcs.query().where(lambda n: n.id == id).nearest()


# Why: `[opnpcu,<bartender>]` takes the card straight to the barcrawl branch, skipping the 4-option menu the talk op puts up.
# Why: that branch behaves the same at all 10 bars.
def drink_at(bar, log):
    _w2 = yield from traversal.walk_resilient(bar.tile, radius=3, attempts=3, timeout_ms=300000, log=log)
    if not (_w2):
        log(f'could not reach the {bar.line} bartender')
        return False
    yield from execution.delay_ticks(2)
    npc = by_id(bar.id)
    card = inventory.first(BARCRAWL_CARD)
    if not npc or not card:
        log(f'no bartender {bar.id} or no card at the {bar.line}')
        return False
    before_coins = inventory.count(COINS)
    if not (card.use_on(npc)):
        return False
    # Why: 9 of the 10 go straight into the drink, but the Rising Sun's barmaid offers her ale list first.
    # Why: so the barcrawl line has to be in the preference list, or her menu sits unanswered and the card never signs.
    # Why: the coin deduction says the drink was bought; the card only turns green several `p_delay`s later, so the read is retried.
    yield from drive_until(lambda: inventory.count(COINS) < before_coins, BAR_PREFER, log, 20000)
    for attempt in range(3):
        yield from execution.delay_ticks(5)
        after = yield from read_card(lambda m: log(f'  read {attempt + 1}/3: {m}'))
        if after is not None and not any([b.line == bar.line for b in after.remaining]):
            log(f'signed at the {bar.line}')
            return True
    log(f'the {bar.line} did not sign the card')
    return False


GIVE_UP = 3


def run_barcrawl(log, on_progress=None):
    """Drive the crawl. Returns once the card is fully signed; the guard still has to be told, which {@link handInBarcrawl} does."""
    missed = 0
    for pass_ in range(len(BARS) * 2):
        progress = yield from read_card(lambda m: log(f'  {m}'))
        if not progress:
            log(('no barcrawl card in the pack to read' if inventory.count(BARCRAWL_CARD) == 0 else 'holding a barcrawl card but could not read it — stopping rather than re-walking the tour'))
            return False
        if on_progress is not None:
            on_progress(len(BARS) - len(progress.remaining), len(BARS))
        if progress.done:
            log('barcrawl card fully signed')
            return True
        next_ = next_bar(progress.remaining, game.tile())
        if not next_:
            return True
        log(f'barcrawl: {len(progress.remaining)} bars left, heading for the {next_.line}')
        # Why: the next pass re-reads the card and re-sorts, so the loop moves on past one bar that won't answer and comes back to it.
        _w3 = yield from drink_at(next_, log)
        missed = (0 if (_w3) else missed + 1)
        if missed >= GIVE_UP:
            log(f'{missed} bars in a row refused the card — stopping')
            return False
    _w4 = yield from read_card()
    _v5 = ((_w4).done if (_w4) is not None else None)
    return (_v5 if _v5 is not None else False)


def talk_to_guard(log):
    _w6 = yield from traversal.walk_resilient(GUARD_TILE, radius=4, attempts=3, timeout_ms=300000, log=log)
    if not (_w6):
        log('could not reach the outpost gate guard')
        return False
    yield from execution.delay_ticks(2)
    # Why: the outpost's other "Barbarian guard" is the attackable one and the gate loc runs the same conversation, so a talk aimed by display name can land on either, hence the id.
    if not by_id(BARBARIAN_GUARD_ID):
        log('no barbarian guard at the outpost gate')
        return False
    status = yield from reach.entity_op(lambda: by_id(BARBARIAN_GUARD_ID), 'Talk-to', lambda: chat_dialog.is_open() or chat_dialog.can_continue(), what='Barbarian guard', log=log)
    return status == 'done'


# Why: `outpost_guard_progress` consumes the card and sets `%barcrawl` to complete, which is what opens the gate.
def hand_in_barcrawl(log):
    """Give the signed card to the gate guard."""
    _w7 = yield from talk_to_guard(log)
    if not (_w7):
        return False
    yield from drive_until(lambda: inventory.count(BARCRAWL_CARD) == 0, [], log, 20000)
    return inventory.count(BARCRAWL_CARD) == 0


# Why: the guard is the only oracle (`%barcrawl` isn't on the wire), and an empty pack looks the same before the card is issued as after it's handed in.
# Why: `outpost_guard_talk` branches on the varp, "Oi, whaddya want?" for not started, "'Ello friend." for complete, "So, how's the Barcrawl coming along?" for anything between, and that last branch re-issues a lost card.
# Why: the greeting is the verdict, since a random event landing mid-conversation abandons the option chain and leaves the pack empty.
# Why: reading "no card came out" as "already done" sends the bot at a gate that won't open, so only "'Ello friend." means finished.
def ask_guard(log):
    """Ask the gate guard where the crawl stands."""
    _w8 = yield from talk_to_guard(log)
    if not (_w8):
        log('the outpost guard never opened a dialogue')
        return 'retry'
    greeting = ' / '.join(chat_dialog.texts())
    log(f"guard opens with: {greeting or '(nothing)'}")
    if GATE_IS_OPEN in greeting.lower():
        return 'complete'
    # Why: the branch that issues a card is 3 menus deep, so stopping at the first lull leaves the choice on screen with the tour un-started.
    yield from drive_until(lambda: inventory.count(BARCRAWL_CARD) > 0, GUARD_PREFER, log, 25000)
    held = inventory.count(BARCRAWL_CARD)
    log(f'guard done — card in pack: {held}')
    return ('issued' if held > 0 else 'retry')


def ensure_barcrawl(log, on_progress=None):
    """Everything between "no barcrawl" and a gate that opens; true once the guard will let the character through."""
    if inventory.count(BARCRAWL_CARD) == 0:
        verdict = yield from ask_guard(log)
        if verdict == 'complete':
            log('the guard waves us through — the barcrawl is already done')
            return True
        if verdict == 'retry':
            # The conversation was cut short, usually by a random event; fail so the caller walks back and asks again.
            log('the guard handed over no card and did not wave us through — retrying')
            return False
    _w9 = yield from run_barcrawl(log, on_progress)
    if not (_w9):
        return False
    _result10 = yield from hand_in_barcrawl(log)
    return _result10
