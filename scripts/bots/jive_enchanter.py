# Enchants jewellery at the nearest bank: wields an elemental staff when the bank has one, withdraws the jewels by
# id and the runes their casts need, casts once every three ticks, and banks the products. rs2b0t's
# JiveEnchanter (MIT, see thirdparty/rs2b0t).

from rs2004.catalogs import ContinueDialog

COSMIC = 'Cosmic rune'
PACK = 28
BOOTH = {'name': 'Bank booth', 'op': 'Use-quickly'}
MAGIC_TAB = 6
# Why: the cast's p_delay(1) keeps you delayed through the next tick's decode, and the engine bins an op it
# decodes then, so one cast lands every three ticks and a click sent sooner is lost.
CAST_TICKS = 3
LAND_TICKS = 2
# Further than this from the bank, a random event's evasion has carried you off and you walk back.
BANK_LEASH = 8
WALK_MS = 180000


class Spell:
    def __init__(self, level, magic, xp, elements):
        self.level = level
        # The spellbook button's text, which game.cast_on_item matches.
        self.name = f'Enchant Lvl-{level} Jewelry'
        self.magic = magic
        self.xp = xp
        self.elements = elements


# The five enchants of magic_spells.dbrow, each taking a cosmic rune besides.
SPELLS = [
    Spell(1, 7, 17.5, [('Water rune', 1)]),
    Spell(2, 27, 37, [('Air rune', 3)]),
    Spell(3, 49, 59, [('Fire rune', 5)]),
    Spell(4, 57, 67, [('Earth rune', 10)]),
    Spell(5, 68, 78, [('Earth rune', 15), ('Water rune', 15)]),
]


class Jewel:
    """id is the obj id, since a strung amulet shares its display name with the unstrung one."""

    def __init__(self, label, id, product, level, name=None):
        self.label = label
        self.id = id
        self.name = name if name is not None else label
        self.product = product
        self.spell = SPELLS[level - 1]


# Every convertobj row of the enchants; the other necklaces have no enchant in this content.
JEWELS = [
    Jewel('Sapphire ring', 1637, 'Ring of recoil', 1),
    Jewel('Sapphire necklace', 1656, 'Games necklace(8)', 1),
    Jewel('Sapphire amulet', 1694, 'Amulet of magic', 1),
    Jewel('Emerald ring', 1639, 'Ring of dueling(8)', 2),
    Jewel('Emerald amulet', 1696, 'Amulet of defence', 2),
    Jewel('Ruby ring', 1641, 'Ring of forging', 3),
    Jewel('Ruby amulet', 1698, 'Amulet of strength', 3),
    Jewel('Diamond ring', 1643, 'Ring of life', 4),
    Jewel('Diamond amulet', 1700, 'Amulet of power', 4),
    Jewel('Dragonstone ring', 1645, 'Ring of wealth', 5),
    Jewel('Dragonstone amulet', 1702, 'Amulet of glory', 5, 'Dragonstoneamulet'),
]
JEWEL_OPTIONS = [j.label for j in JEWELS]

# The staves the spellbook takes in place of each element rune.
STAFFS = {
    'Water rune': ['Staff of water', 'Water battlestaff', 'Mystic water staff'],
    'Air rune': ['Staff of air', 'Air battlestaff', 'Mystic air staff'],
    'Fire rune': ['Staff of fire', 'Fire battlestaff', 'Mystic fire staff'],
    'Earth rune': ['Staff of earth', 'Earth battlestaff', 'Mystic earth staff'],
}

SETTINGS = {
    'jewel': SettingDef('string', 'Sapphire ring', 'Jewel', options=JEWEL_OPTIONS, help='which jewel to enchant this session; an amulet has to be strung first'),
}


def jewel_by_name(name):
    wanted = name.strip().lower()
    for j in JEWELS:
        if j.label.lower() == wanted or j.name.lower() == wanted:
            return j
    return None


def _covered(rune, wielded):
    return len([s for s in STAFFS.get(rune, []) if s in wielded]) > 0


def runes_per_cast(j, wielded):
    """What one cast takes from the pack, as (rune, count) pairs, with these items worn."""
    return [(COSMIC, 1)] + [(rune, count) for rune, count in j.spell.elements if not _covered(rune, wielded)]


def casts_affordable(j, wielded, held):
    return min([held(rune) // count for rune, count in runes_per_cast(j, wielded)])


def jewel_slots(j, wielded):
    """Pack slots left for jewels once every rune the cast needs has a stack."""
    return PACK - len(runes_per_cast(j, wielded))


def decide(jewels, casts):
    """'cast' or 'bank', read off the pack alone, so a restart lands on the same choice."""
    return 'cast' if jewels > 0 and casts > 0 else 'bank'


class TripPlan:
    def __init__(self, ok, reason=None, jewels=0, runes=None):
        self.ok = ok
        self.reason = reason
        self.jewels = jewels
        self.runes = runes or []


def trip_plan(j, wielded, pack_jewels, pack_rune, bank_jewels, bank_rune):
    """What a bank visit withdraws, sized by the free slots and the scarcest of jewels and runes, or why the run
    has to stop."""
    per_cast = runes_per_cast(j, wielded)
    room = max(0, jewel_slots(j, wielded) - pack_jewels)
    fundable = min([(pack_rune(rune) + bank_rune(rune)) // count for rune, count in per_cast])
    total = min(pack_jewels + min(room, bank_jewels), fundable)
    if total < 1:
        if pack_jewels + bank_jewels < 1:
            return TripPlan(False, f'the bank has no {j.label}')
        short = [rune for rune, count in per_cast if pack_rune(rune) + bank_rune(rune) < count][0]
        return TripPlan(False, f'the bank has no {short}')
    runes = [(rune, total * count - pack_rune(rune)) for rune, count in per_cast]
    return TripPlan(True, jewels=max(0, total - pack_jewels), runes=[(rune, n) for rune, n in runes if n > 0])


def staff_for(j, stock):
    """A banked staff that covers one of the spell's elements, or None."""
    for rune, _ in j.spell.elements:
        for staff in STAFFS.get(rune, []):
            if stock(staff) > 0:
                return staff
    return None


# Why: a staff that covers the element saves a rune stack and a slot every trip, so the first bank visit wields
# one when the bank has it, and otherwise settles for runes, once.
class WieldStaff(Task):
    def __init__(self, bot):
        Task.__init__(self, label='wield staff')
        self.bot = bot

    def validate(self):
        return not self.bot.staff_checked

    def execute(self):
        bot = self.bot
        jewel = bot.jewel
        if len(runes_per_cast(jewel, bot.wielded())) < 1 + len(jewel.spell.elements):
            bot.staff_checked = True
            return
        opened = yield from bot.open_bank()
        if not opened:
            return
        loaded = yield from execution.delay_until(lambda: bank.is_open() and bank.loaded(), 5000)
        if not loaded:
            bot.log('[enchanter] the bank list has not filled in, retrying')
            return
        staff = staff_for(jewel, bank.count)
        if staff is None:
            bot.staff_checked = True
            bot.log('[enchanter] no elemental staff in the bank, casting on runes')
            return
        if inventory.used() > 0:
            yield from bank.deposit_all_matching(lambda name, id: True)
            yield from execution.delay_ticks(1)
        taken = yield from bank.withdraw_x(staff, 1)
        if not taken:
            bot.log(f'[enchanter] could not withdraw the {staff}, retrying')
            return
        closed = yield from bank.close()
        if not closed:
            bot.log('[enchanter] the bank would not close, retrying')
            return
        bot.status = f'wielding the {staff}'
        wielded = yield from equipment.equip(staff)
        if wielded:
            bot.log(f'[enchanter] wielding the {staff}, so its rune stays in the bank')
        else:
            bot.log(f'[enchanter] could not wield the {staff}, casting on runes')
        bot.staff_checked = True


class Restock(Task):
    def __init__(self, bot):
        Task.__init__(self, label='restock')
        self.bot = bot

    def validate(self):
        return self.bot.staff_checked and self.bot.step() == 'bank'

    def execute(self):
        bot = self.bot
        jewel = bot.jewel
        opened = yield from bot.open_bank()
        if not opened:
            return
        bot.status = 'banking the load'
        products = inventory.count(jewel.product)
        wielded = bot.wielded()
        keep = [rune.lower() for rune, _ in runes_per_cast(jewel, wielded)]
        keep_jewels = bot.jewels_held() <= jewel_slots(jewel, wielded)
        yield from bank.deposit_all_matching(lambda name, id: (not keep_jewels or id != jewel.id) and name.lower() not in keep)
        loaded = yield from execution.delay_until(lambda: bank.is_open() and bank.loaded(), 5000)
        if not loaded:
            bot.log('[enchanter] the bank list has not filled in, retrying this trip' if bank.is_open() else '[enchanter] the bank window closed, retrying this trip')
            return

        plan = trip_plan(jewel, wielded, bot.jewels_held(), inventory.count, bank.count_by_id(jewel.id), bank.count)
        if not plan.ok:
            yield from bank.close()
            bot.status = 'stopped'
            bot.request_finish(f'[enchanter] {plan.reason}')
            return
        if plan.jewels > 0:
            bot.status = f'withdrawing {plan.jewels} {jewel.label}'
            taken = yield from bank.withdraw_x_by_id(jewel.id, plan.jewels)
            if not taken:
                bot.log(f'[enchanter] could not withdraw {plan.jewels} {jewel.label}, retrying this trip')
                return
        for rune, count in plan.runes:
            if not bank.is_open() or not bank.loaded():
                bot.log('[enchanter] the bank window closed mid-withdrawal, retrying this trip')
                return
            bot.status = f'withdrawing {count} {rune}'
            taken = yield from bank.withdraw_x(rune, count)
            if not taken:
                bot.log(f'[enchanter] could not withdraw {count} {rune}, retrying this trip')
                return
        closed = yield from bank.close()
        if not closed:
            bot.log('[enchanter] the bank would not close, retrying')
            return
        bot.trips += 1
        bot.banked += products
        took = ' + '.join([f'{plan.jewels} {jewel.label}'] + [f'{count} {rune}' for rune, count in plan.runes])
        bot.log(f'[enchanter] banked {products} {jewel.product}, took {took}')


# Why: one cast a call, so the loop comes back between casts and a random event can break in.
class Enchant(Task):
    def __init__(self, bot):
        Task.__init__(self, label='enchant')
        self.bot = bot

    def validate(self):
        return self.bot.staff_checked and self.bot.step() == 'cast'

    def execute(self):
        bot = self.bot
        jewel = bot.jewel
        yield from bot.settle_cast()
        if bank.is_open():
            closed = yield from bank.close()
            if not closed:
                return
        opened = yield from game.open_side_tab(MAGIC_TAB)
        if not opened:
            bot.log('[enchanter] could not open the magic tab, retrying')
            return
        item = None
        for i in inventory.items():
            if i.id == jewel.id:
                item = i
                break
        if item is None:
            return
        before = bot.jewels_held()
        bot.status = f'enchanting {jewel.label}'
        if not game.cast_on_item(jewel.spell.name, item):
            bot.log('[enchanter] the cast was rejected, retrying')
            yield from execution.delay_ticks(1)
            return
        bot.cast_tick = game.tick()
        landed = yield from execution.delay_until_ticks(lambda: bot.jewels_held() < before, LAND_TICKS)
        if not landed:
            bot.log(f'[enchanter] the cast on {jewel.label} landed nothing, retrying')
            return
        bot.enchanted += before - bot.jewels_held()


class JiveEnchanter(TaskBot):
    loop_delay = 400

    def on_start(self):
        self.status = 'starting'
        self.enchanted = 0
        self.trips = 0
        self.banked = 0
        # The tick the last cast was clicked on; every later op is paced off it.
        self.cast_tick = -CAST_TICKS
        self.known_bank = None
        self.bank_tile = None
        self.bank_name = 'the bank'
        self.staff_checked = False
        self.xp_start = skills.xp('magic')
        pick = self.settings.str('jewel', 'Sapphire ring')
        jewel = jewel_by_name(pick)
        self.jewel = jewel if jewel is not None else JEWELS[0]
        if jewel is None:
            self.request_finish(f"[enchanter] unknown jewel '{pick}'")
            return
        level = skills.level('magic')
        if level < jewel.spell.magic:
            self.request_finish(f'[enchanter] {jewel.spell.name} needs Magic {jewel.spell.magic}, this account has {level}')
            return
        resolved = yield from self.resolve_bank()
        if not resolved:
            return
        self.log(f'[enchanter] {jewel.spell.name} on {jewel.label} into {jewel.product}, banking at {self.bank_name}')
        self.add(ContinueDialog(), WieldStaff(self), Restock(self), Enchant(self))

    # Why: the script stands at whichever bank it starts beside, so the nearest is found once and each trip
    # reopens it.
    def resolve_bank(self):
        here = game.tile()
        if here is None:
            return False
        known = nearest_bank(here)
        if known is None:
            self.request_finish('[enchanter] no reachable bank')
            return False
        self.known_bank = known
        self.bank_tile = Tile(known['tile']['x'], known['tile']['z'], known['tile']['level'])
        self.bank_name = known['name']
        if self.bank_tile.level == here.level and self.bank_tile.distance_to(here) <= 4:
            return True
        self.status = f'walking to {self.bank_name}'
        walked = yield from traversal.walk_resilient(self.bank_tile, radius=3, attempts=4, timeout_ms=WALK_MS, log=lambda m: self.log(f'  {m}'))
        if not walked:
            self.request_finish(f'[enchanter] the walk to {self.bank_name} failed')
            return False
        return True

    def recovery_anchor(self):
        return self.bank_tile

    def open_bank(self):
        if bank.is_open():
            return True
        yield from self.settle_cast()
        self.status = 'opening the bank'
        opened = yield from open_bank_access(self.known_bank, BOOTH, lambda m: self.log(f'  {m}'))
        if opened:
            return True
        here = game.tile()
        strayed = self.bank_tile is not None and here is not None and (here.level != self.bank_tile.level or self.bank_tile.distance_to(here) > BANK_LEASH)
        if not strayed:
            self.log('[enchanter] could not open the bank, will retry')
            return False
        self.status = f'walking back to {self.bank_name}'
        yield from traversal.walk_resilient(self.bank_tile, radius=3, attempts=3, timeout_ms=WALK_MS, log=lambda m: self.log(f'  {m}'))
        return False

    # Why: a booth click sent inside the cast's own delay is binned, and the open waits out its window before
    # retrying, so every op after a cast waits the cast out first.
    def settle_cast(self):
        since = game.tick() - self.cast_tick
        if since < CAST_TICKS:
            yield from execution.delay_ticks(CAST_TICKS - since)

    def wielded(self):
        return [i.name or '' for i in equipment.items()]

    def jewels_held(self):
        return inventory.count_by_id(self.jewel.id)

    def casts_held(self):
        return casts_affordable(self.jewel, self.wielded(), inventory.count)

    def step(self):
        return decide(self.jewels_held(), self.casts_held())

    def on_progress_report(self):
        return {'Status': self.status, 'Enchanted': self.enchanted, 'Trips': self.trips, 'Casts left': self.casts_held(),
                'Banked': self.banked, self.jewel.label: self.jewels_held(), 'Magic xp': skills.xp('magic') - self.xp_start}


BOT = define_bot(
    name='JiveEnchanter',
    create=JiveEnchanter,
    description='Stands at the nearest bank and enchants one jewel picked from the dropdown: wields a matching elemental staff when the bank has one, withdraws the jewels by id and the runes their casts need, casts one enchant every three ticks and banks the products. Stops honestly when the bank runs out of the jewel or a rune.',
    category='Magic',
    tags=['magic', 'enchanting', 'jewellery', 'banking', 'afk'],
    settings_schema=SETTINGS,
)
