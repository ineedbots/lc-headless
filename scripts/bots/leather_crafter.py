# Crafts the best leather item your Crafting level allows at the nearest bank, buying thread from Dommik, Rommik
# or the Fancy dress shop owner when the bank has none: rs2b0t's LeatherCrafter (MIT, see thirdparty/rs2b0t).

NEEDLE = 1733
THREAD = 1734
COINS = 995
THREAD_MAX_PRICE = 3
THREAD_SHOPS = [
    ('Dommik', Tile(3322, 3194, 0)),
    ('Rommik', Tile(2946, 3205, 0)),
    ('Fancy dress shop owner', Tile(3281, 3398, 0)),
]
BANK_STAND = Tile(3269, 3167, 0)
BOOTH = {'name': 'Bank booth', 'op': 'Use-quickly'}
# The 289 cache's leather_crafting interface (a main modal) and skill_multi3 (a chat one), as rs2b0t has them,
# for when the panels can't be read by their products' names.
LEATHER_IF = 2311
MULTI3_IF = 8880
# skill_multi3's make X per slot: a the body, b the vambraces, c the chaps.
MULTI3_MAKEX = {'a': 8886, 'b': 8890, 'c': 8894}
# Why: hard leather bodies are made by the server at once, so needle uses are queued without waiting, up to this.
HARD_LEATHER_BURST = 60


class Recipe:
    """Soft leather picks a button on the leather_crafting interface; dragonhide answers skill_multi3."""

    def __init__(self, level, qty, label, make1=None, make10=None, slot=None):
        self.level = level
        self.qty = qty
        self.label = label
        self.make1 = make1
        self.make10 = make10
        self.slot = slot


class LeatherKind:
    def __init__(self, leather_id, flow, recipes):
        self.leather_id = leather_id
        self.flow = flow
        self.recipes = recipes


# Why: the levels and quantities are the engine's craft_leather_table. Chaps has no make10, since all three of
# its buttons make one engine-side.
LEATHERS = {
    'Leather': LeatherKind(1741, 'interface', [
        Recipe(1, 1, 'Leather gloves', 8638, 8636),
        Recipe(7, 1, 'Leather boots', 8641, 8639),
        Recipe(9, 1, 'Leather cowl', 8653, 8651),
        Recipe(11, 1, 'Leather vambraces', 8644, 8642),
        Recipe(14, 1, 'Leather body', 8635, 8633),
        Recipe(18, 1, 'Leather chaps', 8647, 8645),
        Recipe(38, 1, 'Coif', 8650, 8648),
    ]),
    'Hard leather': LeatherKind(1743, 'single', [Recipe(28, 1, 'Hardleather body')]),
    'Green dragon leather': LeatherKind(1745, 'multi3', [
        Recipe(57, 1, 'Green vambraces', slot='b'), Recipe(60, 2, 'Green chaps', slot='c'), Recipe(63, 3, 'Green body', slot='a'),
    ]),
    'Blue dragon leather': LeatherKind(2505, 'multi3', [
        Recipe(66, 1, 'Blue vambraces', slot='b'), Recipe(68, 2, 'Blue chaps', slot='c'), Recipe(71, 3, 'Blue body', slot='a'),
    ]),
    'Red dragon leather': LeatherKind(2507, 'multi3', [
        Recipe(73, 1, 'Red vambraces', slot='b'), Recipe(75, 2, 'Red chaps', slot='c'), Recipe(77, 3, 'Red body', slot='a'),
    ]),
    'Black dragon leather': LeatherKind(2509, 'multi3', [
        Recipe(79, 1, 'Black vambraces', slot='b'), Recipe(82, 2, 'Black chaps', slot='c'), Recipe(84, 3, 'Black body', slot='a'),
    ]),
}

SETTINGS = {
    'leather_type': SettingDef('string', 'Leather', 'Leather to use', options=list(LEATHERS.keys()),
                               help='makes the best item your Crafting level allows for this leather; keeps a needle + thread and banks the rest'),
    'thread_per_trip': SettingDef('number', 100, 'Thread to keep stocked', 1, 1000),
}


def withdraw_by_id(id, count):
    """'withdrawn', 'missing' or 'retry'. By id, since the hides and leathers share names."""
    if count <= 0:
        return 'withdrawn'
    if not bank.loaded():
        return 'retry'
    if bank.count_by_id(id) == 0:
        return 'missing'
    taken = yield from bank.withdraw_x_by_id(id, count)
    return 'withdrawn' if taken else 'retry'


def deposit_all_except_ids(keep):
    """Deposits by id: the leathers and their products share names in places."""
    if len(bank.side_items()) == 0 and inventory.used() > 0:
        yield from execution.delay_until(lambda: len(bank.side_items()) > 0 or not bank.is_open(), 1200)
    if len(bank.side_items()) == 0:
        return inventory.used() == 0
    yield from bank.deposit_all_matching(lambda name, id: id not in keep)
    return len([i for i in inventory.items() if i.id not in keep]) == 0


class LeatherCrafter(LoopingBot):
    loop_delay = 100

    def on_start(self):
        self.kind_label = self.settings.str('leather_type', 'Leather')
        self.kind = LEATHERS.get(self.kind_label, LEATHERS['Leather'])
        self.thread_stock = self.settings.num('thread_per_trip', 100)
        self.recipe = None
        self.thread_vendor = None
        self.restock_bank = None
        self.crafted = 0
        self.status = 'starting'
        self.xp_at_start = skills.xp('crafting')
        self.pick_recipe()
        if self.recipe is None:
            need = min([r.level for r in self.kind.recipes])
            self.request_finish(f"Crafting {skills.level('crafting')} is too low for {self.kind_label} (needs {need})")
            return
        self.log(f'LeatherCrafter; {self.kind_label} -> {self.recipe.label} (level {self.recipe.level}, {self.recipe.qty} per item)')

    def pick_recipe(self):
        """The highest-level item the Crafting level unlocks for the leather."""
        level = skills.level('crafting')
        usable = [r for r in self.kind.recipes if r.level <= level]
        usable.sort(key=lambda r: r.level, reverse=True)
        best = usable[0] if len(usable) > 0 else None
        if best is not None and (self.recipe is None or best.label != self.recipe.label):
            if self.recipe is not None:
                self.log(f'levelled up; switching to {best.label}')
            self.recipe = best

    def loop(self):
        self.pick_recipe()
        if self.recipe is None:
            return
        if self.thread_vendor is not None:
            yield from self.buy_thread()
            return
        if self.restock_bank is not None:
            yield from self.bank_leg()
            return
        if inventory.count_by_id(self.kind.leather_id) >= self.recipe.qty and inventory.count_by_id(THREAD) > 0:
            yield from self.craft_leg()
            return
        yield from self.bank_leg()

    def bank_leg(self):
        here = game.tile()
        # Why: the bank cheapest to reach, rather than the nearest by the straight line, so it banks from wherever
        # you are; the bank's contents are the account's anywhere.
        picked = nearest_bank_reachable(here, navigator) if here is not None else None
        stand = self.restock_bank
        if stand is None:
            stand = Tile(picked['tile']['x'], picked['tile']['z'], picked['tile']['level']) if picked is not None else BANK_STAND
        if here is None or here.level != stand.level or max(abs(here.x - stand.x), abs(here.z - stand.z)) > 4:
            self.status = 'walking to the bank'
            walked = yield from traversal.walk_resilient(stand, radius=3, attempts=2, timeout_ms=45000, log=lambda m: self.log(f'  {m}'))
            if not walked:
                self.log('bank leg: walk failed; retrying')
                return

        self.status = 'banking'
        known = nearest_bank(stand) if self.restock_bank is not None else picked
        opened = yield from open_bank_access(known, BOOTH, lambda m: self.log(f'  {m}'))
        if not opened:
            self.log('bank leg: could not open the bank; retrying')
            return
        loaded = yield from execution.delay_until(lambda: bank.loaded(), 3000)
        if not loaded:
            self.log('bank leg: bank contents not ready; retrying')
            return
        deposited = yield from deposit_all_except_ids([NEEDLE, THREAD, self.kind.leather_id])
        if not deposited:
            self.log('bank leg: bank inventory view not ready; retrying')
            return

        if inventory.count_by_id(NEEDLE) == 0:
            taken = yield from self.withdraw_required(NEEDLE, 1, 'needle', 'no needle in the bank')
            if not taken:
                return
        if inventory.count_by_id(THREAD) < 5:
            result = yield from withdraw_by_id(THREAD, self.thread_stock)
            if result == 'retry':
                self.log('bank leg: could not withdraw thread; retrying')
                return
            if result == 'missing' and inventory.count_by_id(THREAD) == 0:
                yield from self.fund_thread(stand)
                return

        free = backpack_capacity() - inventory.used()
        taken = yield from self.withdraw_required(self.kind.leather_id, free, self.kind_label, f'no {self.kind_label} left in the bank')
        if not taken:
            return
        closed = yield from bank.close()
        if closed:
            self.restock_bank = None

    def fund_thread(self, stand):
        deposited = yield from deposit_all_except_ids([NEEDLE, THREAD, COINS])
        if not deposited:
            return
        available = bank.count_by_id(COINS)
        needed = max(0, self.thread_stock * THREAD_MAX_PRICE - inventory.count_by_id(COINS))
        if needed > 0 and available > 0:
            result = yield from withdraw_by_id(COINS, min(available, needed))
            if result != 'withdrawn':
                return
        if inventory.count_by_id(COINS) == 0:
            self.request_finish('no thread or coins in the bank')
            return
        self.restock_bank = stand
        vendors = list(THREAD_SHOPS)
        vendors.sort(key=lambda shop: stand.distance_to(shop[1]))
        self.thread_vendor = vendors[0]
        yield from bank.close()

    def buy_thread(self):
        npc, tile = self.thread_vendor
        if bank.is_open():
            closed = yield from bank.close()
            if not closed:
                return
        self.status = f'buying thread from {npc}'
        here = game.tile()
        if here is None or tile.distance_to(here) > 4:
            walked = yield from traversal.walk_resilient(tile, radius=2, attempts=2, timeout_ms=45000, log=self.log)
            if not walked:
                return
        opened = yield from shop.open(npc)
        if not opened:
            return
        yield from shop.buy('Thread', max(0, self.thread_stock - inventory.count_by_id(THREAD)))
        yield from shop.close()
        if inventory.count_by_id(THREAD) > 0:
            self.thread_vendor = None
        elif inventory.count_by_id(COINS) == 0:
            self.request_finish('not enough coins to buy thread')
        else:
            self.status = 'waiting for thread stock'
            yield from execution.delay_ticks(5)

    def withdraw_required(self, id, count, label, stop_reason):
        result = yield from withdraw_by_id(id, count)
        if result == 'withdrawn':
            return True
        if result == 'retry':
            self.log(f'could not withdraw {label}; retrying')
            return False
        self.request_finish(stop_reason)
        return False

    def craft_leg(self):
        recipe = self.recipe
        leather_id = self.kind.leather_id
        needle = None
        for item in inventory.items():
            if item.id == NEEDLE:
                needle = item
                break
        leathers = [i for i in inventory.items() if i.id == leather_id]
        if needle is None or len(leathers) == 0:
            return
        before = inventory.count_by_id(leather_id)
        self.status = f'making {recipe.label}'

        if self.kind.flow == 'single':
            # Why: hard leather has no make-X interface; the server crafts at once and takes the first leather in
            # the pack, so the last slot is used as many times as there is leather.
            last = leathers[-1]
            sent = 0
            for _ in range(min(before, HARD_LEATHER_BURST)):
                if not needle.use_on(last):
                    break
                sent += 1
            if sent == 0:
                return
            moved = yield from execution.delay_until(lambda: inventory.count_by_id(leather_id) < before, 5000)
            if moved:
                yield from execution.delay_ticks(1)
            else:
                self.log('craft leg: hard leather never moved; retrying')
        elif not needle.use_on(leathers[0]):
            return
        elif self.kind.flow == 'interface':
            opened = yield from execution.delay_until(lambda: chat_dialog.is_main_make_panel() or reader.main_modal() == LEATHER_IF, 5000)
            if not opened:
                return
            op = 'Make 10' if recipe.make10 is not None else 'Make'
            made = yield from chat_dialog.make_from_panel(recipe.label, op)
            if not made:
                interfaces.click(recipe.make10 if recipe.make10 is not None else recipe.make1)
            yield from self.await_crafting(before)
        else:
            opened = yield from execution.delay_until(lambda: chat_dialog.is_make_menu() or reader.chat_modal() == MULTI3_IF, 5000)
            if not opened:
                return
            count = before // recipe.qty
            made = yield from chat_dialog.make_x(recipe.label, count)
            if not made:
                interfaces.click(MULTI3_MAKEX[recipe.slot])
                asked = yield from execution.delay_until(lambda: reader.count_dialog_open(), 3000)
                if not asked:
                    return
                chat_dialog.answer_count(count)
            yield from self.await_crafting(before)

        used = before - inventory.count_by_id(leather_id)
        if used > 0:
            self.crafted += used // recipe.qty
        else:
            self.log(f'craft leg: no leather consumed (leather {before} unchanged)')

    def await_crafting(self, before):
        """Waits while the batch makes item after item, until the leather stops going."""
        leather_id = self.kind.leather_id
        last = before
        for _ in range(8):
            seen = last
            settled = yield from execution.delay_until(lambda: inventory.count_by_id(leather_id) < seen, 4000)
            now = inventory.count_by_id(leather_id)
            if now < self.recipe.qty or inventory.count_by_id(THREAD) == 0:
                return
            if not settled and now == last:
                return
            last = now

    def on_progress_report(self):
        return {'Status': self.status, 'Made': self.crafted, 'Crafting xp': skills.xp('crafting') - self.xp_at_start,
                'Item': self.recipe.label if self.recipe is not None else '-', 'Thread': inventory.count_by_id(THREAD)}


BOT = define_bot(
    name='LeatherCrafter',
    create=LeatherCrafter,
    description='Crafts the best leather item your Crafting level allows at the nearest bank. Buys missing thread from Dommik, Rommik, or the Fancy dress shop owner and returns to the same bank.',
    category='Crafting',
    tags=['crafting', 'leather', 'dragonhide', 'banking', 'afk'],
    settings_schema=SETTINGS,
)
