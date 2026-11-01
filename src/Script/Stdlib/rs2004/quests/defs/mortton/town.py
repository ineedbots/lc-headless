"""Ported from rs2b0t's src/bot/api/ai/quests/defs/mortton/town.ts (MIT, see thirdparty/rs2b0t)."""

import _core

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.dialogue import chat_dialog, modals
from rs2004.entities import ground_items, npcs
from rs2004.execution import event_signal
from rs2004.game import reader
from rs2004.items import inventory
from rs2004.quests.defs.mortton.areas import SM_ID, SM_LOC, SM_LOC_ID, SM_NAME, SM_NPC, SM_TILE
from rs2004.quests.defs.mortton.supplies import perm_serum_vial_id, serum_vial_id
from rs2004.quests.exec.prompts import prompt_loc, settle_scene
from rs2004.reach import reach
from rs2004.trade import shop
from rs2004.traversal import traversal

__all__ = ['JUNK_IDS', 'drive_once', 'villager', 'talk_villager', 'visit', 'take_diary', 'read_diary', 'search_table', 'identify_tarromin', 'take_vial', 'mix_unfinished', 'mix_serum', 'shop_at_razmire', 'handover_and_stock', 'drop_junk', 'drop_down', 'RAZMIRE_START_SCRIPT', 'ULSQUIRE_TEMPLE_SCRIPT', 'BUILD_SETS', 'PASTE_PER_SET', 'sets_that_fit', 'builders_order', 'general_order']

# Why: `book` is opened by `if_openmain`, and its forward-page arrow is a graphic with no label, so the component id is the only handle on it.
BOOK_MODAL = 837
BOOK_NEXT = 841
BOOK_LAST_PAGE = 'index of solution'
BOOK_PAGES = 16
JUNK_IDS = [SM_ID.DIARY, SM_ID.ROTTEN_FOOD, SM_ID.UNID_ROGUES_PURSE]


WORD_CHARS = 'abcdefghijklmnopqrstuvwxyz0123456789_'


def is_ok_option(text):
    """rs2b0t's /^ok\b/i: the option starts with the word "ok"."""
    lower = text.strip().lower()
    if not lower.startswith('ok'):
        return False
    return len(lower) == 2 or lower[2] not in WORD_CHARS


# Why: several of these menus loop back to themselves after the option that moves the quest, so a plain preference list picks the same line forever.
def drive_once(script, log):
    """Drive a dialogue taking each scripted option once, then leaving by its exit line."""
    pending = list(script)
    for i in range(80):
        if event_signal.pending():
            return False
        if chat_dialog.can_continue():
            yield from chat_dialog.continue_()
            yield from execution.delay_ticks(1)
            continue
        opts = chat_dialog.options()
        if len(opts) > 0:
            want_index = ([_i for _i, want in enumerate(pending) if any([(want.lower() in o.lower()) for o in opts])] or [-1])[0]
            if want_index >= 0:
                want = pending.pop(want_index)
                yield from chat_dialog.choose_option(([o for o in opts if (want.lower() in o.lower())] or [None])[0])
                yield from execution.delay_ticks(2)
                continue
            exit = ([o for o in opts if is_ok_option(o)] or [None])[0]
            if not exit:
                log(f"no scripted or exit option in [{' | '.join(opts)}]")
                return False
            yield from chat_dialog.choose_option(exit)
            yield from execution.delay_ticks(2)
            continue
        if not chat_dialog.is_open():
            return True
        yield from execution.delay_ticks(1)
    return not chat_dialog.is_open()


def villager(cured, afflicted):
    """Either face of a villager: afflicted, or cured for a couple of minutes by a dose of serum."""
    return npcs.query().where(lambda n: n.name == cured or n.name == afflicted).within(12).nearest()


# Why: `opnpc1` on an afflicted villager only ever answers in gibberish, and the serum's `opnpcu` both sets the visible bit and opens the conversation in the same action.
# Why: `npc_changetype` and the visible bit run the same 200-tick clock, so the villager's own name is the oracle for whether a dose is still needed.
def talk_villager(cured, afflicted, anchor, script, log):
    """Talk to a villager, spending a dose of serum first only if he has gone back to gibberish."""
    yield from modals.close_if_open()
    _w1 = yield from traversal.walk_resilient(anchor, radius=2, attempts=3, timeout_ms=180000, log=log)
    if not (_w1):
        return False
    yield from settle_scene()
    if npcs.query().name(cured).within(12).nearest():
        status = yield from reach.npc_dialog(cured, anchor, log=log)
        if status == 'done':
            _result2 = yield from drive_once(script, log)
            return _result2
        log(f'{cured} did not answer — falling back to a dose of serum')
    # Why: the sanctified vial is spent first, its dose sets the villager's permanent bit, so it buys every later visit as well as this one.
    _v3 = perm_serum_vial_id()
    vial_id = (_v3 if _v3 is not None else serum_vial_id())
    if vial_id is None:
        log(f'no serum 207 in the pack to use on {cured}')
        return False
    npc = villager(cured, afflicted)
    serum = ([i for i in inventory.items() if i.id == vial_id] or [None])[0]
    if not npc or not serum:
        log(f'no {cured} beside ({anchor.x},{anchor.z}) or no serum to use')
        return False
    if not (serum.use_on(npc)):
        return False
    _w4 = yield from execution.delay_until(lambda: chat_dialog.is_open() or chat_dialog.can_continue(), 8000)
    if not (_w4):
        log(f'the serum on {cured} opened no dialogue')
        return False
    _result5 = yield from drive_once(script, log)
    return _result5


def visit(cured, afflicted, anchor, script):
    return lambda log: talk_villager(cured, afflicted, anchor, script, log)


def take_diary(log):
    """Take Herbi Flax's diary off the shelf."""
    # The shelf answers with an objbox, which sits on main until something closes it.
    took = yield from prompt_loc(Record({
        'name': SM_LOC.SHELF,
        'op': 'Search',
        'near': SM_TILE.SHELF,
        'id': SM_LOC_ID.SHELF,
        'within': 8,
        'expect': lambda: inventory.count_by_id(SM_ID.DIARY) > 0,
        'expect_ms': 15000,
    }), log)
    yield from modals.close_if_open()
    return took or inventory.count_by_id(SM_ID.DIARY) > 0


# Why: the quest only starts once the reader reaches page 25, so the book has to be paged all the way through.
# Why: `[opheld1,serum_book]` puts an `~objbox` in front of the book, which ends in `p_pausebutton`, so the book opens after the continue.
def read_diary(log):
    """Read the diary to its last page."""
    diary = ([i for i in inventory.items() if i.id == SM_ID.DIARY] or [None])[0]
    if not diary:
        log('no diary in the pack to read')
        return False
    yield from modals.close_if_open()
    if not (diary.interact('Read')):
        return False

    def book_open():
        return reader.modals().main == BOOK_MODAL

    for i in range(20):
        if not (not book_open()):
            break
        if chat_dialog.can_continue():
            yield from chat_dialog.continue_()
        yield from execution.delay_ticks(1)
    if not book_open():
        log(f'the diary never opened the book interface (main modal {reader.modals().main})')
        return False

    def on_last_page():
        return (BOOK_LAST_PAGE in ' '.join(reader.main_modal_texts()).lower())

    for page in range(BOOK_PAGES):
        if not (not on_last_page()):
            break
        _core.click_component(BOOK_NEXT)
        yield from execution.delay_ticks(1)
    read = on_last_page()
    if not read:
        shown = ' / '.join(reader.main_modal_texts()[1:3])
        log(f'the diary stopped at "{shown}"')
    yield from modals.close()
    return read


# Why: the table hands out its 3 herbs once per player, so a search that finds nothing is a dead end.
def search_table(log):
    """Search the smashed table for the 2 tarromin the serums need."""
    before = inventory.count_by_id(SM_ID.UNID_TARROMIN)
    found = yield from prompt_loc(Record({
        'name': SM_LOC.TABLE,
        'op': 'Search',
        'near': SM_TILE.TABLE,
        'id': SM_LOC_ID.TABLE,
        'within': 8,
        'expect': lambda: inventory.count_by_id(SM_ID.UNID_TARROMIN) > before,
        'expect_ms': 15000,
    }), log)
    yield from modals.close_if_open()
    return found


# Why: every unid renders as "Herb", so the tarromin is picked out of the pack by id.
def identify_tarromin(log):
    """Identify one held unidentified tarromin."""
    unid = ([i for i in inventory.items() if i.id == SM_ID.UNID_TARROMIN] or [None])[0]
    if not unid:
        log('no unidentified tarromin in the pack')
        return False
    before = inventory.count_by_id(SM_ID.TARROMIN)
    if not (unid.interact('Identify')):
        return False
    _result6 = yield from execution.delay_until(lambda: inventory.count_by_id(SM_ID.TARROMIN) > before, 8000)
    return _result6


def vial_spawn():
    return ground_items.query().where(lambda g: g.id == SM_ID.VIAL_EMPTY).within(8).nearest()


# Why: the 2 empty-vial spawns in the experiment house are the only glass inside Morytania, and they come back on their own timer.
def take_vial(log):
    """Take an empty vial from the spawns beside the shelf."""
    before = inventory.count_by_id(SM_ID.VIAL_EMPTY)
    if not vial_spawn():
        _w7 = yield from traversal.walk_resilient(SM_TILE.VIALS, radius=2, attempts=3, timeout_ms=180000, log=log)
        if not (_w7):
            return False
        yield from settle_scene()
    vial = vial_spawn()
    if not vial:
        log('no empty vial on the experiment-house floor yet — waiting for the spawn')
        yield from execution.delay_ticks(4)
        return False
    if not (vial.interact('Take')):
        return False
    _result8 = yield from execution.delay_until(lambda: inventory.count_by_id(SM_ID.VIAL_EMPTY) > before, 8000)
    return _result8


def combine(a, b, product, what, log):
    """Combine two held items and wait for the product."""
    first = ([i for i in inventory.items() if i.id == a] or [None])[0]
    second = ([i for i in inventory.items() if i.id == b] or [None])[0]
    if not first or not second:
        log(f'{what}: the pack is missing an ingredient')
        return False
    before = inventory.count_by_id(product)
    if not (first.use_on(second)):
        return False
    _result9 = yield from execution.delay_until(lambda: inventory.count_by_id(product) > before, 10000)
    return _result9


def mix_unfinished(log):
    return combine(SM_ID.TARROMIN, SM_ID.VIAL_WATER, SM_ID.TARROMIN_UNF, 'unfinished potion', log)


def mix_serum(log):
    return combine(SM_ID.ASHES, SM_ID.TARROMIN_UNF, SM_ID.SERUM3, 'serum 207', log)


def bought(order):
    return all([inventory.count_by_id(w.id) >= w.qty for w in order.items])


def slots_wanted(order):
    """Pack slots the outstanding half of an order still needs."""
    total = 0
    for w in order.items:
        held = inventory.count_by_id(w.id)
        if held >= w.qty:
            continue
        total += ((0 if held > 0 else 1) if w.stack else w.qty - held)
    return total


def fill_order(order, log):
    _w14 = yield from execution.delay_until(lambda: shop.is_open(), 8000)
    if not (_w14):
        log(f'\'{order.op}\' never opened a shop')
        return False
    for want in order.items:
        short = want.qty - inventory.count_by_id(want.id)
        if short > 0:
            yield from shop.buy(want.name, short)
    yield from shop.close()
    if not bought(order):
        short = ', '.join([m.name + ' ' + str(inventory.count_by_id(m.id)) + '/' + str(m.qty) for m in order.items])
        log(f'short after the shop: {short}')
        return False
    return True


# Why: Razmire's counters are `opnpc3` and `opnpc4`, and neither op exists while he is afflicted, so a fresh dose buys the dialogue's store menu as the way in.
def shop_at_razmire(order):
    """Open one of Razmire's counters, curing him first if his ops have gone, and buy the order out."""

    def _fn15(log):
        if bought(order):
            return True
        # Why: a shop trip on a full pack buys nothing and, on the retry, spends a dose of serum re-curing Razmire for it.
        if inventory.free() < slots_wanted(order):
            log(f'no room for the order — {inventory.free()} free, {slots_wanted(order)} wanted')
            return False
        yield from modals.close_if_open()
        _w16 = yield from traversal.walk_resilient(SM_TILE.RAZMIRE, radius=2, attempts=3, timeout_ms=180000, log=log)
        if not (_w16):
            return False
        yield from settle_scene()
        counter = npcs.query().name(SM_NPC.RAZMIRE).action(order.op).within(12).nearest()
        if counter and (counter.interact(order.op)):
            _result17 = yield from fill_order(order, log)
            return _result17
        _w18 = yield from talk_villager(SM_NPC.RAZMIRE, SM_NPC.RAZMIRE_AFFLICTED, SM_TILE.RAZMIRE, order.asks, log)
        if not (_w18):
            return False
        _result19 = yield from fill_order(order, log)
        return _result19
    return _fn15


# Why: the stage-40 conversation ends in the store menu, so the handover, the builders counter and the general counter all fit inside the one dose it costs.
def handover_and_stock(orders):
    """Hand Razmire the 5 sets of remains, then stock both counters on the same visit."""

    def _fn20(log):
        first = orders[0] if len(orders) > 0 else None
        rest = orders[1:]
        script = (first.asks if first else [])
        _w21 = yield from talk_villager(SM_NPC.RAZMIRE, SM_NPC.RAZMIRE_AFFLICTED, SM_TILE.RAZMIRE, script, log)
        if not (_w21):
            return False
        if not first:
            return True
        _w22 = yield from fill_order(first, log)
        if not (_w22):
            return False
        for order in rest:
            _w23 = yield from shop_at_razmire(order)(log)
            if not (_w23):
                return False
        return True
    return _fn20


# Why: the temple loadout fills 27 slots, and the swamp crossing arrives holding a spent diary and whatever the ghasts turned the food into.
def drop_junk(log):
    return drop_down([(Record({'id': id, 'keep': 0})) for id in JUNK_IDS], log)


# Why: only the pyre consumes a set of remains, so anything past a spare is a slot the temple load wants back.
def drop_down(wants, log):
    """Drop each id down to the count it is worth keeping."""
    for want in wants:
        while inventory.count_by_id(want.id) > want.keep:
            before = inventory.count_by_id(want.id)
            item = ([i for i in inventory.items() if i.id == want.id] or [None])[0]
            if not item or not (item.interact('Drop')):
                log(f'item {want.id} would not drop')
                return False
            _w24 = yield from execution.delay_until(lambda: inventory.count_by_id(want.id) < before, 5000)
            if not (_w24):
                return False
    return True


RAZMIRE_START_SCRIPT = ['What are all these shadow creatures', "Yes, I'll dispatch those dark and evil creatures"]
ULSQUIRE_TEMPLE_SCRIPT = ['What can you tell me about that temple']
SHOP_GENERAL = 'Trade-General-Store'
SHOP_BUILDERS = 'Trade-Builders-Store'
# Why: a set is a plank, a brick and 5 paste, worth 800 points of a rebuild that spends about 2600; 5 is what the stage-45 loadout can carry, and a smaller pack buys fewer and comes back.
BUILD_SETS = 5
PASTE_PER_SET = 6


def sets_that_fit(free_slots):
    """Sets that fit, given the pack's free slots: a plank and a brick each, plus one for the paste stack."""
    return max(0, min(BUILD_SETS, ((free_slots - 1) // 2)))


def builders_order(sets=None):
    if sets is None:
        sets = BUILD_SETS
    return (Record({
        'op': SHOP_BUILDERS,
        'asks': [
        'I keep running out of building materials',
        'Can you open a store for me',
        'Can I see the building store',
    ],
        'items': [
        Record({'name': SM_NAME.SWAMP_PASTE, 'qty': sets * PASTE_PER_SET, 'id': SM_ID.SWAMP_PASTE, 'stack': True}),
        Record({'name': SM_NAME.PLANK, 'qty': sets, 'id': SM_ID.PLANK}),
        Record({'name': SM_NAME.LIMESTONE_BRICK, 'qty': sets, 'id': SM_ID.LIMESTONE_BRICK}),
    ],
    }))


def general_order(hammer, oil):
    return (Record({
        'op': SHOP_GENERAL,
        'asks': ['Can you open a store for me', 'Can I see the general store'],
        'items': ([Record({'name': SM_NAME.HAMMER, 'qty': 1, 'id': SM_ID.HAMMER})] if hammer else []) + ([Record({'name': SM_NAME.OLIVE_OIL3, 'qty': 1, 'id': SM_ID.OLIVE_OIL3})] if oil else []),
    }))
