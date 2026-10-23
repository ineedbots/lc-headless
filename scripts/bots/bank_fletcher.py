# Fletches at a bank until the bank runs out: logs into arrow shafts or bows with a knife through the make
# menu's Make X, bow string onto unstrung bows, arrowtips onto headless arrows, or logs cut and then strung in one
# trip. rs2b0t's BankFletcher (MIT, see thirdparty/rs2b0t).

import math

from rs2004.catalogs import ContinueDialog

LOG_OPTIONS = ['Logs', 'Oak logs', 'Willow logs', 'Maple logs', 'Yew logs', 'Magic logs']
PRODUCT_OPTIONS = [
    'Arrow shafts', 'Short bow', 'Long bow', 'String short bow', 'String long bow',
    'Headless arrows', 'Bronze arrows', 'Iron arrows', 'Steel arrows', 'Mithril arrows', 'Adamant arrows', 'Rune arrows',
]
FLETCH_MODES = ['auto', 'cut', 'string', 'cut+string']
DEFAULT_BANK_STAND = Tile(3185, 3440, 0)

SETTINGS = {
    'mode': SettingDef('string', 'auto', 'Fletch mode', options=FLETCH_MODES,
                       option_labels={'auto': 'auto (from product)', 'cut': 'cut logs', 'string': 'string bows', 'cut+string': 'cut+string'},
                       help='auto takes the job from the product, as it always has. cut fletches logs with the knife, string attaches bow string to unstrung bows, and cut+string does both in one trip: logs, then unstrung, then strung. In cut+string and string the log type picks the wood and Long bow means String long bow'),
    'material': SettingDef('string', 'Logs', 'Log type', options=LOG_OPTIONS,
                           help='the exact log to withdraw and fletch — only regular Logs make Arrow shafts; every log makes a bow. Selects the unstrung wood for String short/long bow. Ignored for the arrow attach products'),
    'product': SettingDef('string', 'Arrow shafts', 'Fletch product', options=PRODUCT_OPTIONS,
                          help='knife products open the make-menu; string products attach Bow string onto the unstrung bow for this log type; arrow products attach item-on-item (material/knife ignored)'),
    'bank_stand': SettingDef('tile', [3185, 3440, 0], 'Bank stand tile (x,z)', help='preset bank to walk when no booth is nearby — a booth underfoot wins over it'),
    'bank_booth': SettingDef('string', 'Bank booth', 'Bank booth loc name'),
}

KNIFE = 'Knife'
BOOTH_OP = 'Use-quickly'
BOW_STRING = 'Bow string'
BOW_STRING_ID = 1777
# The count dialog's cap: one Make X uses a whole backpack of logs.
MAKE_X_CAP = 30
# The engine runs five item actions a tick from one player, and drops the rest.
INSTANT_ACTIONS_PER_TICK = 5
ARROW_PER_ACTION = 15
# A bank list that's missing the item this many times running means the bank is out of it.
EMPTY_READ_LIMIT = 3
NO_PROGRESS_LIMIT = 3
LIST_WAIT_TICKS = 7
WITHDRAW_CONFIRM_TICKS = 4
BATCH_IDLE_TICKS = 12
PACK_SLOTS = 28
UNSTACKED_STRING_SLOTS = 14


class AttachPlan:
    def __init__(self, inputs, product, level):
        self.inputs = inputs
        self.product = product
        self.level = level
        self.per_action = ARROW_PER_ACTION


class StringPlan:
    def __init__(self, display_name, unstrung_id, strung_id, level):
        self.display_name = display_name
        self.unstrung_id = unstrung_id
        self.strung_id = strung_id
        self.level = level
        self.string_id = BOW_STRING_ID
        self.per_action = 1


ATTACH_PRODUCTS = {
    'headless arrows': AttachPlan(['Feather', 'Arrow shaft'], 'Headless arrow', 1),
    'bronze arrows': AttachPlan(['Bronze arrowtips', 'Headless arrow'], 'Bronze arrow', 1),
    'iron arrows': AttachPlan(['Iron arrowtips', 'Headless arrow'], 'Iron arrow', 15),
    'steel arrows': AttachPlan(['Steel arrowtips', 'Headless arrow'], 'Steel arrow', 30),
    'mithril arrows': AttachPlan(['Mithril arrowtips', 'Headless arrow'], 'Mithril arrow', 45),
    'adamant arrows': AttachPlan(['Adamant arrowtips', 'Headless arrow'], 'Adamant arrow', 60),
    'rune arrows': AttachPlan(['Rune arrowtips', 'Headless arrow'], 'Rune arrow', 75),
}
# Bows by log and shape: (name, unstrung id, strung id, level). Unstrung and strung bows share a name, so they're
# counted and withdrawn by id.
WOOD_BOWS = {
    'logs': {'short': ('Shortbow', 50, 841, 5), 'long': ('Longbow', 48, 839, 10)},
    'oak logs': {'short': ('Oak shortbow', 54, 843, 20), 'long': ('Oak longbow', 56, 845, 25)},
    'willow logs': {'short': ('Willow shortbow', 60, 849, 35), 'long': ('Willow longbow', 58, 847, 40)},
    'maple logs': {'short': ('Maple shortbow', 64, 853, 50), 'long': ('Maple longbow', 62, 851, 55)},
    'yew logs': {'short': ('Yew shortbow', 68, 857, 65), 'long': ('Yew longbow', 66, 855, 70)},
    'magic logs': {'short': ('Magic shortbow', 72, 861, 80), 'long': ('Magic longbow', 70, 859, 85)},
}
PRODUCT_KEYWORDS = {'arrow shafts': ['shaft', 'arrow'], 'short bow': ['short'], 'long bow': ['long']}


# The pure decisions, kept apart from the game so they can be tested without a client.

def make_batch_count(log_count):
    """What to type into Make X: the pack's logs, capped at the dialog's most."""
    return max(1, min(log_count, MAKE_X_CAP))


def batch_ride_floor(start, count, used_make_x):
    """The batch is ridden until this many logs are left: Make X uses count, a fixed make rides to idle."""
    return max(0, start - count) if used_make_x else 0


def name_matches(item_name, wanted):
    return item_name is not None and item_name.strip().lower() == wanted.strip().lower()


def exact_name(items, query):
    """The item whose name is query, ignoring case."""
    for item in items:
        if name_matches(item.name, query):
            return item
    return None


def match_product(options, product):
    """The make menu's option for the product, by its keywords."""
    key = product.strip().lower()
    keys = PRODUCT_KEYWORDS.get(key, [key] if key else [])
    for option in options:
        lower = (option or '').lower()
        if len([k for k in keys if k in lower]) > 0:
            return option
    return None


def attach_plan_for(product):
    return ATTACH_PRODUCTS.get(product.strip().lower())


def string_shape(product):
    p = product.strip().lower()
    if p == 'string short bow':
        return 'short'
    if p == 'string long bow':
        return 'long'
    return None


def string_plan_for(product, material):
    shape = string_shape(product)
    bows = WOOD_BOWS.get(material.strip().lower())
    if shape is None or bows is None:
        return None
    name, unstrung, strung, level = bows[shape]
    return StringPlan(name, unstrung, strung, level)


def knife_product_level(product, material):
    p = product.strip().lower()
    if p == 'arrow shafts':
        return 1
    bows = WOOD_BOWS.get(material.strip().lower())
    if bows is None:
        return None
    if p == 'short bow':
        return bows['short'][3]
    if p == 'long bow':
        return bows['long'][3]
    return None


def work_kind(product):
    if attach_plan_for(product) is not None:
        return 'attach'
    if string_shape(product) is not None:
        return 'string'
    return 'knife'


def count_by_id(items, id):
    return sum([max(1, i.count) for i in items if i.id == id])


# Why: the server checks the slot clicked still holds the item, and a removal takes the lowest slot while an
# addition refills it, so the highest slot stays good through a burst of five clicks.
def last_item_by_id(items, id):
    for i in range(len(items) - 1, -1, -1):
        if items[i].id == id:
            return items[i]
    return None


def can_withdraw_by_name(items, id):
    """Whether every stack with this id's name is that id."""
    hits = [i for i in items if i.id == id]
    if len(hits) == 0 or not hits[0].name:
        return False
    same = [i for i in items if name_matches(i.name, hits[0].name)]
    return len(same) > 0 and len([i for i in same if i.id != id]) == 0


def instant_actions_for(input0, input1, per_action=1):
    available = max(0, min(math.floor(input0), math.floor(input1)))
    if available == 0 or per_action <= 0:
        return 0
    return min(INSTANT_ACTIONS_PER_TICK, math.ceil(available / per_action))


def string_is_stacked(string_count, string_slots):
    return string_slots > 0 and string_count > string_slots


def extra_string_slots_wanted(string_slots, stacked):
    """The bow-string slots to withdraw after a deposit that kept the strings held."""
    if stacked:
        return 0 if string_slots > 0 else 1
    return max(0, UNSTACKED_STRING_SLOTS - string_slots)


def fixed_withdraw_clicks(n):
    """Bank clicks of 10 and 1 that add up to n, without the Withdraw-X count dialog."""
    left = max(0, math.floor(n))
    return [10] * (left // 10) + [1] * (left % 10)


def keep_names(kind):
    if kind == 'string':
        return [BOW_STRING]
    if kind == 'knife':
        return [KNIFE]
    if kind == 'cut+string':
        return [BOW_STRING, KNIFE]
    return []


def needs_restock(kind, log_count, knife_count, input0, input1):
    if kind == 'cut+string':
        return not (log_count > 0 and knife_count > 0) and not (input0 > 0 and input1 > 0)
    if kind != 'knife':
        return input0 == 0 or input1 == 0
    return log_count == 0 or knife_count == 0


def bank_list_state(open, loaded):
    if not open:
        return 'closed'
    return 'ready' if loaded else 'unready'


def stock_action(state, has_item, wait_timed_out):
    if has_item:
        return 'ok'
    if state == 'closed':
        return 'retry-closed'
    if state == 'ready':
        return 'empty-confirmed'
    return 'empty-unready' if wait_timed_out else 'retry-unready'


def next_empty_reads(current, action):
    if action == 'ok':
        return 0
    # A ready list can still be the snapshot from before the deposit, so one miss isn't enough.
    if action == 'empty-confirmed' or action == 'empty-unready':
        return current + 1
    return current


def should_stop_no_progress(no_progress, sent):
    return sent == 0 or no_progress >= NO_PROGRESS_LIMIT


def stack_op(item):
    ops = item.actions()
    return withdraw_op(ops, 'all') or withdraw_op(ops, 'any') or 'Withdraw-All'


def withdraw_stack(item, log):
    op = stack_op(item)
    log(f"withdrawing all id {item.id} ('{op}')")
    return bank.withdraw_by_id(item.id, op)


def withdraw_exact(item, n, got, log):
    """Withdraws n of the item, by clicks of 10 and 1 where it can, else through Withdraw X. Use with yield from."""
    if n <= 0:
        return True
    before = got()
    ops = item.actions()
    ten_op = withdraw_op(ops, '10')
    one_op = withdraw_op(ops, '1') or withdraw_op(ops, 'any')
    plan = fixed_withdraw_clicks(n)
    if len(plan) > 0 and len([a for a in plan if not (ten_op if a == 10 else one_op)]) == 0:
        log(f"withdrawing {n} of id {item.id} ({'+'.join([str(a) for a in plan])})")
        remaining = n
        while remaining > 0 and not inventory.is_full():
            click_before = got()
            burst = fixed_withdraw_clicks(remaining)[0:INSTANT_ACTIONS_PER_TICK]
            if len(burst) == 0:
                break
            expected = sum(burst)
            for amount in burst:
                if not bank.withdraw_by_id(item.id, ten_op if amount == 10 else one_op):
                    return got() > before
            yield from execution.delay_until_ticks(lambda: got() - click_before >= expected or inventory.is_full(), WITHDRAW_CONFIRM_TICKS)
            gained = got() - click_before
            if gained <= 0 or len([i for i in bank.items() if i.id == item.id]) == 0:
                break
            remaining -= gained
        return got() > before
    if item.name and can_withdraw_by_name(bank.items(), item.id):
        log(f'withdrawing {n} {item.name}')
        took = yield from bank.withdraw_x(item.name, n)
        return took and (got() > before or inventory.is_full())
    log(f'withdrawing {n} of id {item.id}')
    took = yield from bank.withdraw_x_by_id(item.id, n)
    return took and (got() > before or inventory.is_full())


class FletchDialog(Task):
    def __init__(self, bot):
        Task.__init__(self, label='fletch dialog')
        self.bot = bot

    def validate(self):
        k = self.bot.work_kind()
        return (k == 'knife' or k == 'cut+string') and chat_dialog.is_make_menu()

    def execute(self):
        bot = self.bot
        bot.status = 'choosing product'
        products = chat_dialog.make_products()
        choice = match_product(products, bot.product)
        if choice is None:
            bot.request_finish(f"BankFletcher: '{bot.product}' isn't offered for '{bot.material}' (menu: [{', '.join(products)}]) — refusing to make the wrong item")
            return
        start = bot.log_count()
        count = make_batch_count(start)
        used_make_x = False
        picked = yield from chat_dialog.make_x(choice, count)
        if not picked and chat_dialog.is_make_menu():
            bot.log(f'Make-X missed for *{bot.product}* — retrying')
            picked = yield from chat_dialog.make_x(choice, count)
        if picked:
            used_make_x = True
        elif chat_dialog.is_make_menu():
            # No Make X, or its count dialog failed: the largest fixed amount, once.
            bot.log(f'Make-X failed for *{bot.product}* — falling back to fixed qty')
            picked = yield from chat_dialog.make(choice)
        if not picked:
            bot.log(f"make menu open but couldn't pick *{bot.product}* — products: [{', '.join(products)}]")
            yield from execution.delay_ticks(1)
            return
        # An open make menu means making hasn't started; it waits before trying Make X again.
        started = yield from execution.delay_until(lambda: not chat_dialog.is_make_menu() and (game.animating() or bot.log_count() < start or chat_dialog.can_continue()), 5000)
        if not started:
            return
        # Why: Make X uses count logs without opening the menu again, so the batch is ridden to the end, through
        # the short gaps in the animation, or logs are left behind.
        floor = batch_ride_floor(start, count, used_make_x)
        mark = bot.log_count()
        idle = 0
        for _ in range(400):
            if bot.log_count() <= floor:
                break
            # A menu open again means the batch finished or was interrupted.
            if chat_dialog.can_continue() or chat_dialog.is_make_menu():
                return
            yield from execution.delay_ticks(1)
            now = bot.log_count()
            if now < mark:
                bot.made += mark - now
                mark = now
                idle = 0
            else:
                idle += 1
                if idle >= BATCH_IDLE_TICKS:
                    return


class BankTrip(Task):
    def __init__(self, bot):
        Task.__init__(self, label='bank trip')
        self.bot = bot

    def validate(self):
        return self.bot.must_restock()

    def execute(self):
        bot = self.bot
        bot.status = 'banking'
        opened = yield from banking.open(stand=bot.bank_stand, booth_name=bot.booth_name, booth_op=BOOTH_OP, log=lambda m: bot.log(f'  {m}'))
        if not opened:
            bot.log('could not open the bank — will retry')
            return
        yield from self.restock()
        # Why: the bank is left so the knife and logs can be used, and the close is sent even unseen.
        if bank.is_open():
            closed = yield from bank.close()
            if not closed:
                bot.log('could not close the bank after withdraw — will retry')

    def list_state(self):
        return bank_list_state(bank.is_open(), bank.loaded())

    def missed(self, key, action, finished):
        """After a stock check that found nothing: retries, or stops once the bank's read empty enough times."""
        bot = self.bot
        if action.startswith('retry'):
            bot.log(f"no '{key}' in the bank list yet ({action}) — will retry")
        elif bot.empty_reads.get(key, 0) >= EMPTY_READ_LIMIT:
            bot.request_finish(finished)
        else:
            bot.log(f"bank snapshot missed '{key}' ({bot.empty_reads.get(key, 0)}/{EMPTY_READ_LIMIT}) — will retry")

    def restock(self):
        """Use with yield from."""
        bot = self.bot
        stringing = bot.string_plan()
        string_locked = (stringing is not None and bot.pack_count_by_id(stringing.unstrung_id) == 0 and bot.pack_count_by_id(stringing.string_id) > 0
                         and inventory.used() >= 27)
        keep = [] if string_locked else keep_names(bot.work_kind())
        if string_locked:
            bot.log('pack is only bow string — depositing to make room for unstrung')
        yield from bank.deposit_all_matching(deposit_all_except(keep))
        bot.trips += 1
        arrived = yield from execution.delay_until_ticks(lambda: bank.loaded() or not bank.is_open(), LIST_WAIT_TICKS)
        if self.list_state() == 'closed':
            bot.log('bank window closed — will retry')
            return
        if bot.mode == 'cut+string' and stringing is not None:
            yield from self.withdraw_cut_string(stringing, not arrived)
            return
        if stringing is not None:
            yield from self.withdraw_stringing(stringing, not arrived)
            return
        plan = bot.attach_plan()
        if plan is not None:
            yield from self.withdraw_attaching(plan, not arrived)
            return
        log_item = exact_name(bank.items(), bot.material)
        action = stock_action(self.list_state(), log_item is not None, not arrived)
        bot.note_empty(bot.material, action)
        if action != 'ok':
            self.missed(bot.material, action, f"BankFletcher: bank is out of '{bot.material}' — fletching complete")
            return
        if not bot.has_knife():
            got = yield from self.withdraw_knife(not arrived)
            if not got:
                return
        bot.log(f'withdrawing {log_item.name}')
        took = yield from bank.withdraw_load(log_item.name)
        if not took:
            bot.log(f'could not withdraw {log_item.name} — will retry')

    def withdraw_knife(self, wait_timed_out):
        """Use with yield from."""
        bot = self.bot
        knife = exact_name(bank.items(), KNIFE)
        action = stock_action(self.list_state(), knife is not None, wait_timed_out)
        bot.note_empty(KNIFE, action)
        if action != 'ok':
            if action.startswith('retry'):
                bot.log('knife unread in the bank list — will retry')
                return False
            bot.status = 'error: no Knife'
            bot.log('No Knife in bank or inventory.')
            bot.request_finish('BankFletcher: no Knife in bank or inventory')
            return False
        ops = knife.actions()
        op = withdraw_op(ops, '1') or withdraw_op(ops, 'any') or 'Withdraw-1'
        bot.log(f"withdrawing {knife.name} ('{op}')")
        bank.withdraw(knife.name, op)
        yield from execution.delay_until_ticks(bot.has_knife, WITHDRAW_CONFIRM_TICKS)
        return bot.has_knife()

    def withdraw_attaching(self, plan, wait_timed_out):
        """Use with yield from."""
        bot = self.bot
        for name in plan.inputs:
            pat = name.lower()
            found = [i for i in bank.items() if i.name is not None and pat in i.name.lower()]
            action = stock_action(self.list_state(), len(found) > 0, wait_timed_out)
            bot.note_empty(name, action)
            if action != 'ok':
                self.missed(name, action, f"BankFletcher: bank is out of '{name}'")
                return
            bank_name = found[0].name
            op = stack_op(found[0])
            bot.log(f"withdrawing all {bank_name} ('{op}')")
            bank.withdraw(bank_name, op)
            yield from execution.delay_until_ticks(lambda: bot.pack_count(name) > 0 or bank.count(bank_name) == 0, WITHDRAW_CONFIRM_TICKS)

    def withdraw_strings_and_unstrung(self, plan, wait_timed_out, done_reason):
        """Bow string to 14 slots, then all the unstrung bows that fit. Use with yield from."""
        bot = self.bot
        string_slots = len([i for i in inventory.items() if i.id == plan.string_id])
        stacked = string_is_stacked(bot.pack_count_by_id(plan.string_id), string_slots)
        string_exact = extra_string_slots_wanted(string_slots, stacked)
        if string_exact > 0:
            strings = [i for i in bank.items() if i.id == plan.string_id]
            string_item = strings[0] if len(strings) > 0 else exact_name(bank.items(), BOW_STRING)
            action = stock_action(self.list_state(), string_item is not None, wait_timed_out)
            bot.note_empty(BOW_STRING, action)
            if action != 'ok':
                self.missed(BOW_STRING, action, f"BankFletcher: bank is out of '{BOW_STRING}'")
                return
            took = yield from withdraw_exact(string_item, string_exact, lambda: bot.pack_count_by_id(plan.string_id), bot.log)
            if not took:
                return
        unstrungs = [i for i in bank.items() if i.id == plan.unstrung_id]
        action = stock_action(self.list_state(), len(unstrungs) > 0, wait_timed_out)
        key = f'unstrung:{plan.unstrung_id}'
        bot.note_empty(key, action)
        if action == 'ok':
            if inventory.is_full():
                return
            before = bot.pack_count_by_id(plan.unstrung_id)
            if not withdraw_stack(unstrungs[0], bot.log):
                return
            yield from execution.delay_until_ticks(lambda: bot.pack_count_by_id(plan.unstrung_id) > before or inventory.is_full()
                                                   or len([i for i in bank.items() if i.id == plan.unstrung_id]) == 0, WITHDRAW_CONFIRM_TICKS)
            return
        if action.startswith('retry'):
            bot.log(f'no {plan.display_name} (u id {plan.unstrung_id}) in the bank list yet ({action}) — will retry')
        elif bot.empty_reads.get(key, 0) >= EMPTY_READ_LIMIT:
            bot.request_finish(done_reason)
        else:
            bot.log(f'bank snapshot missed unstrung {plan.display_name} ({bot.empty_reads.get(key, 0)}/{EMPTY_READ_LIMIT}) — will retry')

    def withdraw_stringing(self, plan, wait_timed_out):
        """Use with yield from."""
        yield from self.withdraw_strings_and_unstrung(plan, wait_timed_out, f'BankFletcher: bank is out of unstrung {plan.display_name}')

    def withdraw_cut_string(self, plan, wait_timed_out):
        """Use with yield from."""
        bot = self.bot
        # Why: it cuts first, as FlaxAIO picks before it spins, so the logs run out before a single bow is strung.
        log_item = exact_name(bank.items(), bot.material)
        action = stock_action(self.list_state(), log_item is not None, wait_timed_out)
        bot.note_empty(bot.material, action)
        if action == 'ok':
            if not bot.has_knife():
                got = yield from self.withdraw_knife(wait_timed_out)
                if not got:
                    return
            bot.log(f'withdrawing {log_item.name} (cut phase)')
            took = yield from bank.withdraw_load(log_item.name)
            if not took:
                bot.log(f'could not withdraw {log_item.name} — will retry')
            return
        if action.startswith('retry'):
            bot.log(f"'{bot.material}' unread ({action}) — will retry")
            return
        # Why: running out of logs ends the cut phase, not the run; the string phase owns the stop.
        bot.log(f"no '{bot.material}' left for cutting — switching to stringing phase")
        # Why: stringing is item on item, so the knife would hold a slot for the rest of the run.
        if bot.has_knife():
            bot.log(f'cut+string string phase — depositing {KNIFE} to free a slot')
            yield from bank.deposit_all_matching(lambda name, *_args: name_matches(name, KNIFE))
            yield from execution.delay_ticks(1)
        yield from self.withdraw_strings_and_unstrung(plan, wait_timed_out, f'BankFletcher: bank is out of unstrung {plan.display_name} — cut+string complete')


class Fletch(Task):
    def __init__(self, bot):
        Task.__init__(self, label='fletch')
        self.bot = bot

    def validate(self):
        bot = self.bot
        k = bot.work_kind()
        return (k == 'knife' or k == 'cut+string') and bot.log_count() > 0 and bot.has_knife() and not chat_dialog.is_open() and not bank.is_open()

    def execute(self):
        bot = self.bot
        for _ in range(30):
            if bot.log_count() == 0 or chat_dialog.is_make_menu() or chat_dialog.can_continue():
                return
            knife = exact_name(inventory.items(), KNIFE)
            last = bot.last_log()
            if knife is None or last is None:
                yield from execution.delay_ticks(2)
                return
            bot.status = f'fletching {bot.product}'
            before = bot.log_count()
            if not knife.use_on(last):
                yield from execution.delay_ticks(1)
                continue
            yield from execution.delay_until(lambda: chat_dialog.is_make_menu() or bot.log_count() < before or chat_dialog.can_continue(), 8000)
            if chat_dialog.is_make_menu():
                return


class InstantAttach(Task):
    def __init__(self, bot):
        Task.__init__(self, label='instant attach')
        self.bot = bot

    # Why: it cuts first, so a cut+string pack is strung only once its logs are gone.
    def validate(self):
        bot = self.bot
        kind = bot.work_kind()
        ready = bot.log_count() == 0 if kind == 'cut+string' else (kind == 'attach' or kind == 'string')
        return ready and bot.input_count(0) > 0 and bot.input_count(1) > 0 and not chat_dialog.is_open() and not bank.is_open()

    def execute(self):
        bot = self.bot
        stringing = bot.string_plan()
        attach = bot.attach_plan()
        per_action = stringing.per_action if stringing is not None else (attach.per_action if attach is not None else 1)
        bot.status = f'stringing {stringing.display_name}' if stringing is not None else f"attaching {attach.product if attach is not None else 'product'}s"
        no_progress = 0
        for _ in range(80):
            if chat_dialog.is_open():
                return
            want = instant_actions_for(bot.input_count(0), bot.input_count(1), per_action)
            if want == 0:
                return
            before = bot.product_count()
            before0 = bot.input_count(0)
            before1 = bot.input_count(1)
            sent = 0
            for _ in range(want):
                a = bot.input_item(0)
                b = bot.input_item(1)
                if a is None or b is None:
                    break
                if a.use_on(b):
                    sent += 1
            yield from execution.delay_ticks(1)
            now = bot.product_count()
            if now > before:
                bot.made += now - before
                no_progress = 0
            elif bot.input_count(0) < before0 or bot.input_count(1) < before1:
                no_progress = 0
            else:
                no_progress += 1
                if should_stop_no_progress(no_progress, sent):
                    return


class BankFletcher(TaskBot):
    def on_start(self):
        self.loop_delay = 600
        self.made = 0
        self.trips = 0
        self.status = 'starting'
        self.empty_reads = {}
        yield from execution.delay_until(lambda: game.ingame() and game.tile() is not None, 0)
        s = self.settings
        self.material = s.str('material', 'Logs')
        self.product = s.str('product', 'Arrow shafts')
        mode = s.str('mode', 'auto')
        self.mode = mode if mode in FLETCH_MODES else 'auto'
        self.bank_stand = s.tile('bank_stand', DEFAULT_BANK_STAND)
        self.booth_name = s.str('bank_booth', 'Bank booth')
        kind = self.work_kind()
        attach = self.attach_plan()
        stringing = self.string_plan()
        if attach is not None:
            need = attach.level
        elif stringing is not None:
            need = stringing.level
        else:
            need = knife_product_level(self.product, self.material)
        if need is not None and skills.level('fletching') < need:
            self.log(f"BankFletcher: Fletching {need} required for {self.product} (have {skills.level('fletching')}) — stopping.")
            raise ValueError('BankFletcher: fletching level too low for the chosen product')
        natural = work_kind(self.product)
        if self.mode == 'cut' and natural != 'knife':
            self.log(f"BankFletcher: mode 'cut' needs a knife product (Short/Long bow, Arrow shafts), not '{self.product}' — stopping.")
            raise ValueError('BankFletcher: cut mode needs a knife product')
        if self.mode == 'string' and natural == 'knife' and stringing is None:
            self.log(f"BankFletcher: mode 'string' needs a string/attach product, not '{self.product}' — stopping.")
            raise ValueError('BankFletcher: string mode needs a string/attach product')
        if (kind == 'string' or kind == 'cut+string') and stringing is None:
            self.log(f"BankFletcher: {'Stringing' if kind == 'string' else 'cut+string'} '{self.product}' needs a known log type, not '{self.material}' — stopping.")
            raise ValueError(f"BankFletcher: {'stringing' if kind == 'string' else 'cut+string'} needs a known log type")
        if kind == 'knife' and self.product.strip().lower() == 'arrow shafts' and self.material.strip().lower() != 'logs':
            self.log(f"BankFletcher: Arrow shafts fletch only from regular Logs, not '{self.material}' — pick Logs or a bow product. Stopping.")
            raise ValueError('BankFletcher: arrow shafts require regular Logs')
        self.xp_at_start = skills.xp('fletching')
        if kind == 'cut+string':
            self.log(f"BankFletcher cut+string '{stringing.display_name}' — {self.material} → unstrung (u id {stringing.unstrung_id}) → strung")
        elif stringing is not None:
            self.log(f"BankFletcher stringing '{stringing.display_name}' (u id {stringing.unstrung_id})")
        elif attach is not None:
            self.log(f"BankFletcher attaching '{attach.inputs[0]}' onto '{attach.inputs[1]}' → {attach.product}")
        else:
            self.log(f"BankFletcher fletching '{self.material}' → {self.product}")
        self.add(ContinueDialog(), FletchDialog(self), BankTrip(self), InstantAttach(self), Fletch(self))

    def work_kind(self):
        if self.mode == 'cut+string':
            return 'cut+string'
        if self.mode == 'cut':
            return 'knife'
        k = work_kind(self.product)
        if self.mode == 'string' and k == 'knife':
            return 'string'
        return k

    def attach_plan(self):
        return attach_plan_for(self.product)

    def string_plan(self):
        plan = string_plan_for(self.product, self.material)
        if plan is not None:
            return plan
        # Why: in the stringing modes 'Short bow' names the bow to finish, so it's 'String short bow'.
        if self.mode == 'cut+string' or self.mode == 'string':
            return string_plan_for(f'String {self.product}', self.material)
        return None

    def note_empty(self, key, action):
        self.empty_reads[key] = next_empty_reads(self.empty_reads.get(key, 0), action)

    # What's in the backpack.

    def pack_count(self, name):
        pat = name.lower()
        return sum([max(1, i.count) for i in inventory.items() if pat in (i.name or '').lower()])

    def pack_item(self, name):
        pat = name.lower()
        for i in inventory.items():
            if pat in (i.name or '').lower():
                return i
        return None

    def pack_count_by_id(self, id):
        return count_by_id(inventory.items(), id)

    def log_count(self):
        return sum([max(1, i.count) for i in inventory.items() if name_matches(i.name, self.material)])

    def last_log(self):
        logs = [i for i in inventory.items() if name_matches(i.name, self.material)]
        return logs[-1] if len(logs) > 0 else None

    def has_knife(self):
        return exact_name(inventory.items(), KNIFE) is not None

    def input_item(self, which):
        stringing = self.string_plan()
        if stringing is not None:
            return last_item_by_id(inventory.items(), stringing.string_id if which == 0 else stringing.unstrung_id)
        attach = self.attach_plan()
        return self.pack_item(attach.inputs[which]) if attach is not None else None

    def input_count(self, which):
        stringing = self.string_plan()
        if stringing is not None:
            return self.pack_count_by_id(stringing.string_id if which == 0 else stringing.unstrung_id)
        attach = self.attach_plan()
        return self.pack_count(attach.inputs[which]) if attach is not None else 0

    def product_count(self):
        stringing = self.string_plan()
        if stringing is not None:
            return self.pack_count_by_id(stringing.strung_id)
        attach = self.attach_plan()
        return inventory.count(attach.product) if attach is not None else 0

    def must_restock(self):
        if bank.is_open():
            return True
        return needs_restock(self.work_kind(), self.log_count(), 1 if self.has_knife() else 0, self.input_count(0), self.input_count(1))

    def on_progress_report(self):
        return {'Status': self.status, self.product: self.made, 'Bank trips': self.trips, 'Fletching xp': skills.xp('fletching') - self.xp_at_start}


BOT = define_bot(
    name='BankFletcher',
    create=BankFletcher,
    description='Bank-standing fletcher — keeps the knife (or bow string), Make-X logs into shafts/unstrung bows, or spam-string unstrung bows and attach arrows',
    category='Fletching',
    tags=['fletching', 'banking', 'afk', 'bows', 'arrows', 'stringing'],
    settings_schema=SETTINGS,
)
