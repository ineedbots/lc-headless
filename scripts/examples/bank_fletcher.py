# Fletches at a bank until the bank runs out: logs into arrow shafts or bows with a knife through the make
# menu's Make X, bow string onto unstrung bows, or arrowtips onto headless arrows. rs2b0t's BankFletcher (MIT,
# see third_party/rs2b0t), less its cut+string mode.

from rs2004.catalogs import ContinueDialog

LOG_OPTIONS = ['Logs', 'Oak logs', 'Willow logs', 'Maple logs', 'Yew logs', 'Magic logs']
PRODUCT_OPTIONS = [
    'Arrow shafts', 'Short bow', 'Long bow', 'String short bow', 'String long bow',
    'Headless arrows', 'Bronze arrows', 'Iron arrows', 'Steel arrows', 'Mithril arrows', 'Adamant arrows', 'Rune arrows',
]

SETTINGS = {
    'material': SettingDef('string', 'Logs', 'Log type', options=LOG_OPTIONS, help='the log to fletch; only plain Logs make arrow shafts. For stringing, the wood of the unstrung bow'),
    'product': SettingDef('string', 'Arrow shafts', 'Fletch product', options=PRODUCT_OPTIONS),
    'bank_stand': SettingDef('tile', [3185, 3440, 0], 'Bank stand', help='walked to when no booth is near; Varrock West by default'),
    'bank_booth': SettingDef('string', 'Bank booth', 'Bank booth name'),
}

KNIFE = 'Knife'
BOW_STRING = 'Bow string'
BOW_STRING_ID = 1777
# The count dialog's cap: one Make X uses a whole backpack of logs.
MAKE_X_CAP = 30
# The engine runs five item actions a tick from one player, and drops the rest.
INSTANT_ACTIONS_PER_TICK = 5
ARROW_PER_ACTION = 15
# A bank list that's missing the item this many times running means the bank is out of it.
EMPTY_READ_LIMIT = 3
BATCH_IDLE_TICKS = 12

# Arrows: (inputs, product, level).
ATTACH_PRODUCTS = {
    'headless arrows': (['Feather', 'Arrow shaft'], 'Headless arrow', 1),
    'bronze arrows': (['Bronze arrowtips', 'Headless arrow'], 'Bronze arrow', 1),
    'iron arrows': (['Iron arrowtips', 'Headless arrow'], 'Iron arrow', 15),
    'steel arrows': (['Steel arrowtips', 'Headless arrow'], 'Steel arrow', 30),
    'mithril arrows': (['Mithril arrowtips', 'Headless arrow'], 'Mithril arrow', 45),
    'adamant arrows': (['Adamant arrowtips', 'Headless arrow'], 'Adamant arrow', 60),
    'rune arrows': (['Rune arrowtips', 'Headless arrow'], 'Rune arrow', 75),
}
# Bows by wood and shape: (name, unstrung id, strung id, level). Unstrung and strung bows share a name, so
# they're counted by id.
WOOD_BOWS = {
    'logs': {'short': ('Shortbow', 50, 841, 5), 'long': ('Longbow', 48, 839, 10)},
    'oak logs': {'short': ('Oak shortbow', 54, 843, 20), 'long': ('Oak longbow', 56, 845, 25)},
    'willow logs': {'short': ('Willow shortbow', 60, 849, 35), 'long': ('Willow longbow', 58, 847, 40)},
    'maple logs': {'short': ('Maple shortbow', 64, 853, 50), 'long': ('Maple longbow', 62, 851, 55)},
    'yew logs': {'short': ('Yew shortbow', 68, 857, 65), 'long': ('Yew longbow', 66, 855, 70)},
    'magic logs': {'short': ('Magic shortbow', 72, 861, 80), 'long': ('Magic longbow', 70, 859, 85)},
}
PRODUCT_KEYWORDS = {'arrow shafts': ['shaft', 'arrow'], 'short bow': ['short'], 'long bow': ['long']}


def make_batch_count(log_count):
    return max(1, min(log_count, MAKE_X_CAP))


def match_product(options, product):
    """The make menu's option for the product, by its keywords."""
    keys = PRODUCT_KEYWORDS.get(product.strip().lower(), [product.strip().lower()])
    for option in options:
        lower = (option or '').lower()
        if len([k for k in keys if k in lower]) > 0:
            return option
    return None


def string_shape(product):
    p = product.strip().lower()
    if p == 'string short bow':
        return 'short'
    if p == 'string long bow':
        return 'long'
    return None


def work_kind(product):
    if product.strip().lower() in ATTACH_PRODUCTS:
        return 'attach'
    if string_shape(product) is not None:
        return 'string'
    return 'knife'


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


def instant_actions_for(input0, input1, per_action):
    available = max(0, min(input0, input1))
    if available == 0 or per_action <= 0:
        return 0
    return min(INSTANT_ACTIONS_PER_TICK, (available + per_action - 1) // per_action)


def count_by_id(items, id):
    return sum([max(1, i.count) for i in items if i.id == id])


def count_by_name(items, name):
    wanted = name.strip().lower()
    return sum([max(1, i.count) for i in items if (i.name or '').strip().lower() == wanted])


class BankFletcher(TaskBot):
    def on_start(self):
        s = self.settings
        self.material = s.material
        self.product = s.product
        self.kind = work_kind(self.product)
        self.made = 0
        self.trips = 0
        self.empty_reads = {}
        self.xp_start = skills.xp('fletching')
        self.attach = ATTACH_PRODUCTS.get(self.product.strip().lower())
        self.bow = None
        if self.kind == 'string':
            bows = WOOD_BOWS.get(self.material.strip().lower())
            if bows is None:
                raise ValueError(f"stringing needs a known log type, not '{self.material}'")
            self.bow = bows[string_shape(self.product)]
        if self.kind == 'knife' and self.product.strip().lower() == 'arrow shafts' and self.material.strip().lower() != 'logs':
            raise ValueError('only plain Logs make arrow shafts')
        if self.attach is not None:
            need = self.attach[2]
        elif self.bow is not None:
            need = self.bow[3]
        else:
            need = knife_product_level(self.product, self.material)
        if need is not None and skills.level('fletching') < need:
            raise ValueError(f'{self.product} needs Fletching {need}; this account has {skills.level("fletching")}')
        log('fletching', self.product, 'from', self.material if self.attach is None else ' and '.join(self.attach[0]))
        self.add(
            ContinueDialog(),
            Task(lambda: self.kind == 'knife' and chat_dialog.is_make_menu(), self.choose_product, 'make menu'),
            Task(self.must_restock, self.bank_trip, 'bank'),
            Task(lambda: self.kind != 'knife' and self.input_count(0) > 0 and self.input_count(1) > 0 and not chat_dialog.is_open() and not bank.is_open(), self.combine, 'combine'),
            Task(lambda: self.kind == 'knife' and self.log_count() > 0 and self.has_knife() and not chat_dialog.is_open() and not bank.is_open(), self.cut, 'cut'),
        )

    # What's in the backpack.

    def log_count(self):
        return count_by_name(inventory.items(), self.material)

    def has_knife(self):
        return inventory.contains(KNIFE)

    def input_item(self, which):
        """The last stack of an input, which stays valid through a burst of clicks."""
        items = inventory.items()
        if self.bow is not None:
            wanted = BOW_STRING_ID if which == 0 else self.bow[1]
            matching = [i for i in items if i.id == wanted]
        else:
            name = self.attach[0][which].lower()
            matching = [i for i in items if name in (i.name or '').lower()]
        return matching[-1] if matching else None

    def input_count(self, which):
        items = inventory.items()
        if self.bow is not None:
            return count_by_id(items, BOW_STRING_ID if which == 0 else self.bow[1])
        if self.attach is None:
            return 0
        name = self.attach[0][which].lower()
        return sum([max(1, i.count) for i in items if name in (i.name or '').lower()])

    def product_count(self):
        if self.bow is not None:
            return count_by_id(inventory.items(), self.bow[2])
        return inventory.count(self.attach[1]) if self.attach is not None else 0

    def must_restock(self):
        if bank.is_open():
            return True
        if self.kind == 'knife':
            return self.log_count() == 0 or not self.has_knife()
        return self.input_count(0) == 0 or self.input_count(1) == 0

    def keep_list(self):
        if self.kind == 'knife':
            return [KNIFE]
        if self.kind == 'string':
            return [BOW_STRING]
        return []

    # Banking.

    def note_empty(self, key, empty):
        self.empty_reads[key] = self.empty_reads.get(key, 0) + 1 if empty else 0
        if self.empty_reads[key] >= EMPTY_READ_LIMIT:
            self.request_finish(f'the bank is out of {key}')
            return True
        if empty:
            log('no', key, 'in the bank list yet; trying again')
        return empty

    def bank_trip(self):
        opened = yield from banking.open(self.settings.bank_stand, self.settings.bank_booth)
        if not opened:
            log('could not open the bank; trying again')
            return
        yield from bank.deposit_all_matching(deposit_all_except(self.keep_list()))
        self.trips += 1
        yield from bank.wait_ready()
        if self.kind == 'knife':
            yield from self.withdraw_for_cutting()
        elif self.kind == 'string':
            yield from self.withdraw_for_stringing()
        else:
            yield from self.withdraw_for_attaching()
        yield from bank.close()

    def withdraw_for_cutting(self):
        if not self.has_knife():
            if self.note_empty(KNIFE, bank.count(KNIFE) == 0):
                return
            bank.withdraw(KNIFE)
            yield from execution.delay_until_ticks(lambda: self.has_knife(), 4)
        if self.note_empty(self.material, bank.count(self.material) == 0):
            return
        yield from bank.withdraw_load(self.material)

    def withdraw_for_stringing(self):
        strings = len([i for i in inventory.items() if i.id == BOW_STRING_ID])
        want = max(0, 14 - strings)
        if want > 0:
            if self.note_empty(BOW_STRING, bank.count_by_id(BOW_STRING_ID) == 0):
                return
            yield from bank.withdraw_x_by_id(BOW_STRING_ID, want)
        unstrung = self.bow[1]
        if self.note_empty(self.bow[0] + ' (u)', bank.count_by_id(unstrung) == 0):
            return
        yield from bank.withdraw_x_by_id(unstrung, inventory.free())

    def withdraw_for_attaching(self):
        for name in self.attach[0]:
            if self.note_empty(name, bank.count(name) == 0):
                return
            item = [i for i in bank.items() if (i.name or '').lower() == name.lower()][0]
            op = withdraw_op(item.actions(), 'all') or withdraw_op(item.actions(), 'any')
            bank.withdraw(item.name, op)
            yield from execution.delay_until_ticks(lambda: self.input_count(self.attach[0].index(name)) > 0, 4)

    # Fletching.

    def cut(self):
        knife = inventory.first(KNIFE)
        logs = [i for i in inventory.items() if (i.name or '').lower() == self.material.lower()]
        if knife is None or not logs:
            return
        before = self.log_count()
        knife.use_on(logs[-1])
        yield from execution.delay_until(lambda: chat_dialog.is_make_menu() or self.log_count() < before or chat_dialog.can_continue(), 8000)

    def choose_product(self):
        products = chat_dialog.make_products()
        choice = match_product(products, self.product)
        if choice is None:
            self.request_finish(f"{self.product} isn't on the make menu for {self.material}: {products}")
            return
        start = self.log_count()
        count = make_batch_count(start)
        made = yield from chat_dialog.make_x(choice, count)
        if not made and chat_dialog.is_make_menu():
            made = yield from chat_dialog.make(choice)
        if not made:
            yield from execution.delay_ticks(1)
            return
        started = yield from execution.delay_until(lambda: not chat_dialog.is_make_menu() and (game.animating() or self.log_count() < start), 5000)
        if not started:
            return
        # Make X goes on without the menu, so the batch is waited out, through the pauses in the animation.
        floor = max(0, start - count)
        mark = self.log_count()
        idle = 0
        while self.log_count() > floor:
            if chat_dialog.can_continue() or chat_dialog.is_make_menu():
                return
            yield from execution.delay_ticks(1)
            now = self.log_count()
            if now < mark:
                self.made += mark - now
                mark = now
                idle = 0
            else:
                idle += 1
                if idle >= BATCH_IDLE_TICKS:
                    return

    def combine(self):
        per_action = ARROW_PER_ACTION if self.attach is not None else 1
        idle = 0
        while idle < 3:
            if chat_dialog.is_open():
                return
            want = instant_actions_for(self.input_count(0), self.input_count(1), per_action)
            if want == 0:
                return
            before = self.product_count()
            before_inputs = (self.input_count(0), self.input_count(1))
            for i in range(want):
                first = self.input_item(0)
                second = self.input_item(1)
                if first is None or second is None:
                    break
                first.use_on(second)
            yield from execution.delay_ticks(1)
            now = self.product_count()
            if now > before:
                self.made += now - before
                idle = 0
            elif (self.input_count(0), self.input_count(1)) != before_inputs:
                idle = 0
            else:
                idle += 1

    def on_progress_report(self):
        return {'Made': self.made, 'Bank trips': self.trips, 'Fletching xp': skills.xp('fletching') - self.xp_start}


BOT = define_bot(
    name='Bank fletcher',
    create=BankFletcher,
    description="Fletches logs, strings bows or tips arrows from the bank until it runs out; rs2b0t's BankFletcher",
    category='Fletching',
    settings_schema=SETTINGS,
)
