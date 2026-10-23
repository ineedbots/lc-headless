# Makes potions at the nearest bank: withdraws vials of water and a herb, makes 14 unfinished potions, then
# withdraws a secondary to finish them and banks them. rs2b0t's PotionMaker (MIT, see thirdparty/rs2b0t).

# Why: every herb's unfinished potion has the same display name, so each step goes by ids.
VIAL_OF_WATER_ID = 227
# Of each half, withdrawn and combined a batch.
BATCH = 14
# The dropdown choice that reveals the matching text setting.
CUSTOM = 'Custom'
BOOTH = {'name': 'Bank booth', 'op': 'Use-quickly'}


class HerbDef:
    """name is the clean herb, id what's withdrawn, unf_id the unfinished potion it makes with a vial of water."""

    def __init__(self, key, name, id, unf_id):
        self.key = key
        self.name = name
        self.id = id
        self.unf_id = unf_id


class SecondaryDef:
    def __init__(self, key, name, id):
        self.key = key
        self.name = name
        self.id = id


HERBS = [
    HerbDef('guam', 'Guam leaf', 249, 91),
    HerbDef('marrentill', 'Marrentill', 251, 93),
    HerbDef('tarromin', 'Tarromin', 253, 95),
    HerbDef('harralander', 'Harralander', 255, 97),
    HerbDef('ranarr', 'Ranarr weed', 257, 99),
    HerbDef('toadflax', 'Toadflax', 2998, 3002),
    HerbDef('irit', 'Irit leaf', 259, 101),
    HerbDef('avantoe', 'Avantoe', 261, 103),
    HerbDef('kwuarm', 'Kwuarm', 263, 105),
    HerbDef('snapdragon', 'Snapdragon', 3000, 3004),
    HerbDef('cadantine', 'Cadantine', 265, 107),
    HerbDef('lantadyme', 'Lantadyme', 2481, 2483),
    HerbDef('dwarf weed', 'Dwarf weed', 267, 109),
    HerbDef('torstol', 'Torstol', 269, 111),
]
SECONDARIES = [
    SecondaryDef('eye of newt', 'Eye of newt', 221),
    SecondaryDef('red spiders eggs', "Red spiders' eggs", 223),
    SecondaryDef('limpwurt root', 'Limpwurt root', 225),
    SecondaryDef('snape grass', 'Snape grass', 231),
    SecondaryDef('unicorn horn dust', 'Unicorn horn dust', 235),
    SecondaryDef('white berries', 'White berries', 239),
    SecondaryDef('dragon scale dust', 'Dragon scale dust', 241),
    SecondaryDef('wine of zamorak', 'Wine of zamorak', 245),
    SecondaryDef('jangerberries', 'Jangerberries', 247),
]
HERB_OPTIONS = [h.name for h in HERBS]
SECONDARY_OPTIONS = [s.name for s in SECONDARIES]

SETTINGS = {
    'herb': SettingDef('string', CUSTOM, 'Herb', options=HERB_OPTIONS + [CUSTOM], help='Which herb to turn into unfinished potions. Choose Custom to reveal a free-text field.'),
    'herb_custom': SettingDef('string', 'Guam leaf', 'Custom herb', show_if={'key': 'herb', 'any_of': [CUSTOM]}, help='Shown when Herb is Custom — a clean herb name like "guam leaf" or "ranarr".'),
    'secondary': SettingDef('string', CUSTOM, 'Secondary', options=SECONDARY_OPTIONS + [CUSTOM], help='Which secondary to finish the potions with. Choose Custom to reveal a free-text field.'),
    'secondary_custom': SettingDef('string', 'Eye of newt', 'Custom secondary', show_if={'key': 'secondary', 'any_of': [CUSTOM]}, help='Shown when Secondary is Custom — a secondary name like "eye of newt" or "snape".'),
}


def _find(items, test):
    for item in items:
        if test(item):
            return item
    return None


def herb_by_name(name):
    """A herb by clean name, whole then by part then by key, without regard to case."""
    wanted = name.strip().lower()
    if not wanted:
        return None
    return (_find(HERBS, lambda h: h.name.lower() == wanted) or _find(HERBS, lambda h: wanted in h.name.lower())
            or _find(HERBS, lambda h: h.key.lower() == wanted))


def secondary_by_name(name):
    wanted = name.strip().lower()
    if not wanted:
        return None
    return _find(SECONDARIES, lambda s: s.name.lower() == wanted) or _find(SECONDARIES, lambda s: wanted in s.name.lower())


def last_item(id):
    items = [i for i in inventory.items() if i.id == id]
    return items[-1] if len(items) > 0 else None


def open_nearest_bank(bot):
    """Walks to the nearest bank when it isn't within 4 tiles, and opens it: the bank, or None."""
    here = game.tile()
    known = nearest_bank(here) if here is not None else None
    if known is None:
        bot.log('no reachable bank')
        return None
    stand = Tile(known['tile']['x'], known['tile']['z'], known['tile']['level'])
    if here is None or stand.level != here.level or stand.distance_to(here) > 4:
        walked = yield from traversal.walk_resilient(stand, radius=3, attempts=4, timeout_ms=180000, log=lambda m: bot.log(f'  {m}'))
        if not walked:
            bot.log('walk to the bank failed; retrying')
            return None
    opened = yield from open_bank_access(known, known.get('access') or BOOTH, lambda m: bot.log(f'  {m}'))
    if not opened:
        bot.log('could not open the bank; retrying')
        return None
    return known


# Why: it runs only when the pack holds neither herbs nor unfinished potions, so it never breaks into a make.
class RestockIngredients(Task):
    """Withdraws a batch's water and herbs into an empty pack, then closes the bank."""

    def __init__(self, bot):
        Task.__init__(self, label='restock ingredients')
        self.bot = bot
        self.failed_withdraws = 0

    def validate(self):
        herb = self.bot.herb
        return inventory.count_by_id(herb.id) == 0 and inventory.count_by_id(herb.unf_id) == 0

    def failed(self, what):
        self.failed_withdraws += 1
        self.bot.log(f'ingredient withdrawal failed ({self.failed_withdraws}/3)')
        if self.failed_withdraws >= 3:
            self.bot.log(f'withdrawing {what} failed three times; stopping')
            self.bot.request_finish(f'could not withdraw {what}')

    def execute(self):
        bot = self.bot
        herb = bot.herb
        if not bank.is_open():
            bot.status = 'banking'
            known = yield from open_nearest_bank(bot)
            if known is None:
                return
        deposited = yield from bot.deposit_inventory()
        if not deposited:
            bot.log('bank stock did not reload after the deposit, retrying')
            return
        if not bank.ready():
            return
        vials = bank.count_by_id(VIAL_OF_WATER_ID)
        herbs = bank.count_by_id(herb.id)
        if vials == 0 or herbs == 0:
            missing = 'vials of water' if vials == 0 else herb.name
            bot.log(f'no {missing} in the bank; stopping')
            bot.request_finish(f'no {missing} in the bank')
            return
        taken = yield from bank.withdraw_x_by_id(VIAL_OF_WATER_ID, BATCH)
        if not taken:
            self.failed('vials of water')
            return
        taken = yield from bank.withdraw_x_by_id(herb.id, BATCH)
        if not taken:
            self.failed(herb.name)
            return
        self.failed_withdraws = 0
        closed = yield from bank.close()
        if not closed:
            bot.log('bank would not close; retrying the trip')
            return
        bot.batches += 1
        bot.log(f'withdrew {inventory.count_by_id(VIAL_OF_WATER_ID)} vials of water + {inventory.count_by_id(herb.id)} {herb.name}')


# Why: using the last slots lets the game drain the stacks from the end, as GemCutter's cutting does.
class MakeUnfinished(Task):
    """Uses the last herb on the last vial, again and again, to make the batch's unfinished potions."""

    def __init__(self, bot):
        Task.__init__(self, label='make unfinished')
        self.bot = bot

    def validate(self):
        return inventory.count_by_id(self.bot.herb.id) > 0 and inventory.count_by_id(VIAL_OF_WATER_ID) > 0

    def execute(self):
        bot = self.bot
        herb = bot.herb
        if bank.is_open():
            closed = yield from bank.close()
            if not closed:
                bot.log('bank would not close, retrying')
                return
        bot.status = f'making {herb.name} unfinished potions'
        herb_item = last_item(herb.id)
        vial_item = last_item(VIAL_OF_WATER_ID)
        if herb_item is None or vial_item is None:
            return
        start_xp = skills.xp('herblore')
        for _ in range(BATCH * 4):
            if inventory.count_by_id(herb.id) == 0 or inventory.count_by_id(VIAL_OF_WATER_ID) == 0:
                break
            herb_item.use_on(vial_item)
        yield from execution.delay_until(lambda: inventory.count_by_id(herb.id) == 0 or skills.xp('herblore') > start_xp, 8000)
        yield from execution.delay_ticks(1)


class FinishPotions(Task):
    """Withdraws the secondary, uses it on the unfinished potions, and banks the finished batch."""

    def __init__(self, bot):
        Task.__init__(self, label='finish potions')
        self.bot = bot
        self.failed_withdraws = 0

    def validate(self):
        herb = self.bot.herb
        return inventory.count_by_id(herb.id) == 0 and inventory.count_by_id(herb.unf_id) > 0

    def execute(self):
        bot = self.bot
        herb = bot.herb
        secondary = bot.secondary
        bot.status = f'withdrawing {secondary.name}'
        known = yield from open_nearest_bank(bot)
        if known is None:
            return
        deposited = yield from bot.wait_for_deposit()
        if not deposited:
            return
        if not bank.ready():
            yield from bank.close()
            return
        needed = max(0, min(BATCH, inventory.count_by_id(herb.unf_id)) - inventory.count_by_id(secondary.id))
        if needed > 0 and bank.count_by_id(secondary.id) == 0:
            bot.log(f'no {secondary.name} in the bank; stopping at the booth holding the batch')
            yield from bank.close()
            bot.request_finish(f'no {secondary.name} in the bank')
            return
        if needed > 0:
            taken = yield from bank.withdraw_x_by_id(secondary.id, needed)
            if not taken:
                yield from bank.close()
                self.failed_withdraws += 1
                bot.log(f'could not withdraw {secondary.name} ({self.failed_withdraws}/3)')
                if self.failed_withdraws >= 3:
                    bot.log(f'withdrawing {secondary.name} failed three times; stopping')
                    bot.request_finish(f'could not withdraw {secondary.name}')
                return
        self.failed_withdraws = 0
        closed = yield from bank.close()
        if not closed:
            bot.log('bank would not close; retrying the trip')
            return

        bot.status = f'finishing {herb.name} potions'
        sec_item = last_item(secondary.id)
        unf_item = last_item(herb.unf_id)
        if sec_item is not None and unf_item is not None:
            start_xp = skills.xp('herblore')
            for _ in range(BATCH * 4):
                if inventory.count_by_id(herb.unf_id) == 0 or inventory.count_by_id(secondary.id) == 0:
                    break
                sec_item.use_on(unf_item)
            yield from execution.delay_until(lambda: inventory.count_by_id(herb.unf_id) == 0 or skills.xp('herblore') > start_xp, 8000)

        # Why: the bank is left open, since the next cycle's restock reuses it.
        bot.status = 'banking finished potions'
        opened = yield from open_bank_access(known, known.get('access') or BOOTH, lambda m: bot.log(f'  {m}'))
        if not opened:
            bot.log('could not open the bank; retrying')
            return
        yield from bot.deposit_inventory()


class PotionMaker(TaskBot):
    loop_delay = 100

    def on_start(self):
        s = self.settings
        self.batches = 0
        self.status = 'starting'
        self.pending_bank_generation = None
        self.xp_at_start = skills.xp('herblore')
        herb_choice = s.str('herb', CUSTOM)
        herb_raw = s.str('herb_custom', '') if herb_choice == CUSTOM else herb_choice
        self.herb = herb_by_name(herb_raw)
        if self.herb is None:
            self.log(f'Unknown herb "{herb_raw}"; stopping')
            self.request_finish('unknown herb')
            return
        secondary_choice = s.str('secondary', CUSTOM)
        secondary_raw = s.str('secondary_custom', '') if secondary_choice == CUSTOM else secondary_choice
        self.secondary = secondary_by_name(secondary_raw)
        if self.secondary is None:
            self.log(f'Unknown secondary "{secondary_raw}"; stopping')
            self.request_finish('unknown secondary')
            return
        self.log(f'PotionMaker; {self.herb.name} + {self.secondary.name} at the nearest bank')
        self.add(RestockIngredients(self), MakeUnfinished(self), FinishPotions(self))

    def wait_for_deposit(self):
        if self.pending_bank_generation is None:
            return True
        reloaded = yield from bank.wait_snapshot_after(self.pending_bank_generation)
        if not reloaded:
            yield from bank.close()
            return False
        self.pending_bank_generation = None
        return True

    def deposit_inventory(self):
        waited = yield from self.wait_for_deposit()
        if not waited:
            return False
        if inventory.used() > 0:
            self.pending_bank_generation = bank.snapshot_generation()
            yield from bank.deposit_all_matching(lambda name, id: True)
            yield from execution.delay_ticks(1)
        waited = yield from self.wait_for_deposit()
        return waited

    def on_progress_report(self):
        return {'Status': self.status, 'Herblore xp': skills.xp('herblore') - self.xp_at_start, 'Batches': self.batches,
                'Herblore': skills.level('herblore'), 'Pack': inventory.used()}


BOT = define_bot(
    name='PotionMaker',
    create=PotionMaker,
    description='Banks at the nearest bank, withdraws vials of water and a chosen herb, spam-makes 14 unfinished potions, then withdraws a chosen secondary to finish them and deposits the potions, repeating the cycle. Each leg picks an herb and a secondary from the dropdowns, or types one via Custom',
    category='Herblore',
    tags=['herblore', 'potion', 'banking', 'members', 'afk'],
    settings_schema=SETTINGS,
)
