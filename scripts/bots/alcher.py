# Casts High or Low Level Alchemy on the ticked items, richest first: each withdrawn as notes, alched until the
# bank is out, then the next, with a fire staff worn and nature runes topped up: rs2b0t's Alcher (MIT, see
# thirdparty/rs2b0t).

import math
import time

from rs2004.catalogs import STAFF_RUNES, Record, item_db
from rs2004.market import format_gp, live_catalog

# AlcherLogic.ts

# High Level Alchemy pays 60% of an item's shop cost; Low pays 40%.
HIGH_ALCH_RATE = 0.6
LOW_ALCH_RATE = 0.4
HIGH_ALCH_LEVEL = 55
LOW_ALCH_LEVEL = 21
HIGH_ALCH_SPELL = 'High Level Alchemy'
LOW_ALCH_SPELL = 'Low Level Alchemy'

SPELL_HIGH = 'High'
SPELL_LOW = 'Low'
SPELL_OPTIONS = [SPELL_HIGH, SPELL_LOW]
SPELL_OPTION_LABELS = {SPELL_HIGH: HIGH_ALCH_SPELL, SPELL_LOW: LOW_ALCH_SPELL}

HIGH = Record({'key': SPELL_HIGH, 'name': HIGH_ALCH_SPELL, 'level': HIGH_ALCH_LEVEL, 'rate': HIGH_ALCH_RATE})
LOW = Record({'key': SPELL_LOW, 'name': LOW_ALCH_SPELL, 'level': LOW_ALCH_LEVEL, 'rate': LOW_ALCH_RATE})


def resolve_alch_spell(raw):
    """High is the default, so a missing or unknown setting keeps saved High runs working."""
    wanted = raw.strip().lower()
    if wanted == 'low' or wanted == 'low level alchemy' or wanted == 'lowalch':
        return LOW
    return HIGH


def alch_value_of(cost, rate=0.6):
    return int(math.floor(cost * rate))


# The fire-rune staff preferred when the bank has several.
FIRE_STAFF = 'Staff of fire'
FIRE_RUNE = 'fire rune'

# Why: Staff of fire stays first, so a bank that still has one withdraws it ahead of a battlestaff.
FIRE_STAVES = [FIRE_STAFF] + [staff for staff in STAFF_RUNES if staff.lower() != FIRE_STAFF.lower() and len([r for r in STAFF_RUNES[staff] if r.lower() == FIRE_RUNE]) > 0]


def pick_fire_staff(has):
    """The first fire-rune staff has(name) reports as present, or None."""
    for name in FIRE_STAVES:
        if has(name):
            return name
    return None


# Why: dragonhide colours share a display name, so they're picked by id and shown by a label of their own.
FODDER = [
    ('maple_longbow', None), ('yew_longbow', None), ('magic_longbow', None),
    ('steel_platebody', None), ('steel_platelegs', None), ('steel_2h_sword', None), ('black_platebody', None),
    ('mithril_platebody', None), ('mithril_platelegs', None), ('mithril_kiteshield', None), ('mithril_2h_sword', None),
    ('adamant_platebody', None), ('adamant_platelegs', None), ('adamant_kiteshield', None), ('adamant_2h_sword', None),
    ('rune_platebody', None), ('rune_platelegs', None), ('rune_kiteshield', None), ('rune_chainbody', None),
    ('rune_full_helm', None), ('rune_sq_shield', None), ('rune_scimitar', None), ('rune_2h_sword', None),
    ('dragonhide_body', "Green d'hide body"), ('blue_dragonhide_body', "Blue d'hide body"),
    ('red_dragonhide_body', "Red d'hide body"), ('black_dragonhide_body', "Black d'hide body"),
    ('dragonhide_chaps', "Green d'hide chaps"), ('blue_dragonhide_chaps', "Blue d'hide chaps"),
    ('red_dragonhide_chaps', "Red d'hide chaps"), ('black_dragonhide_chaps', "Black d'hide chaps"),
    ('battlestaff', None), ('air_battlestaff', None), ('water_battlestaff', None), ('earth_battlestaff', None), ('fire_battlestaff', None),
]

ALCH_FODDER_OBJS = [obj for obj, label in FODDER]

# The chip that pulls in whatever the custom field names.
CUSTOM_ALCH_KEY = 'custom'


def _richest_first(item):
    return (-item.alch_value, item.label.lower())


def _db_by(field, value):
    for r in item_db():
        if r.get(field) == value:
            return r
    return None


def _alch_item(key, id, name, label, alch_value):
    return Record({'key': key, 'id': id, 'name': name, 'label': label, 'alch_value': alch_value})


def _alch_items():
    out = []
    for obj, label in FODDER:
        rec = _db_by('obj', obj)
        if rec is not None:
            out.append(_alch_item(obj, rec.id, rec.name, label if label is not None else rec.name, alch_value_of(rec.cost)))
    out.sort(key=_richest_first)
    return out


ALCH_ITEMS = _alch_items()

# Why: the chips are for finding an item by name, so they read alphabetically by label; ALCH_ITEMS keeps its
# richest-first order, which is what the drain runs on.
ALCH_OPTIONS = [CUSTOM_ALCH_KEY] + [i.key for i in sorted(ALCH_ITEMS, key=lambda i: i.label.lower())]

ALCH_OPTION_LABELS = {CUSTOM_ALCH_KEY: 'Custom item (named below)'}
for _item in ALCH_ITEMS:
    ALCH_OPTION_LABELS[_item.key] = _item.label + ' (' + format_gp(_item.alch_value) + ')'


def _fold(s):
    return ' '.join(s.strip().lower().replace('_', ' ').split())


def _revalue(item, rate):
    if rate == HIGH_ALCH_RATE:
        return item
    rec = _db_by('id', item.id)
    if rec is None:
        return item
    return _alch_item(item.key, item.id, item.name, item.label, alch_value_of(rec.cost, rate))


def custom_alch_item(text, rate=0.6):
    """The item the custom field names, by obj name or client name, or None when the database has no such item.

    Why: several items share a client name, so the obj name is the precise form and the first match settles the
    rest."""
    wanted = _fold(text)
    if wanted == '':
        return None
    for i in ALCH_ITEMS:
        if _fold(i.key) == wanted or _fold(i.label) == wanted:
            return _revalue(i, rate)
    rec = None
    for r in item_db():
        if _fold(r.obj) == wanted:
            rec = r
            break
    if rec is None:
        for r in item_db():
            if _fold(r.name) == wanted:
                rec = r
                break
    if rec is None:
        return None
    for i in ALCH_ITEMS:
        if i.id == rec.id:
            return _revalue(i, rate)
    return _alch_item(rec.obj, rec.id, rec.name, rec.name, alch_value_of(rec.cost, rate))


def _apply_rate(items, rate):
    return items if rate == HIGH_ALCH_RATE else [_revalue(i, rate) for i in items]


# Yew and magic longbows, steel platebodies and the dragonhide armour.
DEFAULT_ALCH_ITEMS = [
    'black_dragonhide_body', 'red_dragonhide_body', 'blue_dragonhide_body', 'dragonhide_body',
    'black_dragonhide_chaps', 'red_dragonhide_chaps', 'blue_dragonhide_chaps', 'dragonhide_chaps',
    'magic_longbow', 'steel_platebody', 'yew_longbow',
]


def alch_item(key):
    wanted = key.strip().lower()
    for i in ALCH_ITEMS:
        if i.key == wanted:
            return i
    return None


def selected_alch_items(keys, custom_text='', rate=0.6):
    """The ticked items plus the custom one, richest first.

    Why: the chips give option order, not click order, so the table's order is the drain's; with the custom chip
    ticked an unresolved name selects nothing, so a typo stops the run instead of alching the defaults."""
    wanted = set([k.strip().lower() for k in keys])
    picked = [i for i in ALCH_ITEMS if i.key in wanted]
    if CUSTOM_ALCH_KEY not in wanted:
        rows = picked if len(picked) > 0 else [i for i in ALCH_ITEMS if i.key in DEFAULT_ALCH_ITEMS]
        return _apply_rate(rows, rate)
    custom = custom_alch_item(custom_text)
    if custom is not None and len([i for i in picked if i is custom]) == 0:
        picked.append(custom)
        picked.sort(key=_richest_first)
    return _apply_rate(picked, rate)


def next_alch_target(selected, empty):
    """The richest selected item the bank hasn't run out of."""
    for i in selected:
        if i.key not in empty:
            return i
    return None


def fmt_gp(n):
    v = round(n)
    mag = abs(v)
    if mag >= 1000000:
        return f'{v / 1000000:.1f}m'
    if mag >= 10000:
        return f'{round(v / 1000)}k'
    if mag >= 1000:
        return f'{v / 1000:.1f}k'
    return str(v)


# Alcher.ts

BOOTH = {'name': 'Bank booth', 'op': 'Use-quickly'}
MAGIC_TAB = 6
NATURE_RUNE = 'Nature rune'
# Why: the cast's p_delay(3) leaves the player delayed through tick+4's packet decode, and the engine bins an op
# it decodes while delayed, so the server takes one cast per 5 ticks and no faster.
ALCH_TICKS = 5
# Ticks to give the note before a cast counts as binned.
ALCH_LAND_TICKS = 2
# Past this from the resolved bank, an evade has carried us out of booth range and we walk back.
BANK_LEASH = 8
EQUIP_WORDS = ['wield', 'wear', 'equip']

SETTINGS = {
    'spell': SettingDef('string', SPELL_HIGH, 'Spell', options=SPELL_OPTIONS, option_labels=SPELL_OPTION_LABELS,
                        help='High needs 55 Magic and pays 60% of shop cost. Low needs 21 Magic and pays 40%. Saved item lists and alchs-per-trip keep working.'),
    'items': SettingDef('string[]', DEFAULT_ALCH_ITEMS, 'Items to alch', options=ALCH_OPTIONS, option_labels=ALCH_OPTION_LABELS,
                        help='ticked items are drained richest first: the bot withdraws one as notes, alchs it until the bank is out, then moves to the next. '
                        + 'Chips show the alch value each. Tick Custom to add the item named below. Leave every chip clear to run the defaults.'),
    'custom_item': SettingDef('string', '', 'Custom item', show_if={'key': 'items', 'any_of': [CUSTOM_ALCH_KEY]},
                              help='shown when Custom is ticked. Any item the database knows, by client name or obj name, e.g. "Iron platebody" or "iron_platebody". '
                              + 'It drains in value order with the ticked chips.'),
    'alchs': SettingDef('number', 27, 'Alchs per trip', min=1, max=1000,
                        help='how many notes + nature runes to withdraw each trip; both stack in a single slot each, so even 1000 fits in 2 pack slots'),
}


class Alcher(TaskBot):
    loop_delay = 400

    def on_start(self):
        yield from execution.delay_until(lambda: game.ingame() and game.tile() is not None, 0)
        self.selected = []
        # Keys a loaded bank has confirmed it holds none of.
        self.empty = set()
        self.bank = None
        self.bank_tile = None
        self.bank_name = 'the bank'
        self.trips = 0
        self.alched = 0
        self.gp = 0
        self.status = 'starting'
        # Bank stock and noted id by item key.
        self.stock = {}
        self.noted = {}
        # The tick the last cast was clicked on; every later op is paced off it.
        self.cast_tick = -ALCH_TICKS
        self.started_at = time.time()
        self.xp_at_start = skills.xp('magic')
        self.spell = resolve_alch_spell(self.settings.str('spell', SPELL_HIGH))
        keys = self.settings.list('items', DEFAULT_ALCH_ITEMS)
        custom_text = self.settings.str('custom_item', '')
        if CUSTOM_ALCH_KEY in keys:
            custom = custom_alch_item(custom_text, self.spell.rate)
            if custom is None:
                self.log(f'custom item "{custom_text}" is not in the item database — stopping')
                self.request_finish(f'custom item "{custom_text}" is not in the item database')
                return
            self.log(f'custom item: {custom.label} ({custom.key}, {custom.alch_value}gp each)')
        self.selected = selected_alch_items(keys, custom_text, self.spell.rate)
        self.alchs = self.settings.num('alchs', 27)

        if skills.level('magic') < self.spell.level:
            self.log(f"{self.spell.name} needs {self.spell.level} Magic (have {skills.level('magic')}) — stopping")
            self.request_finish(f'{self.spell.name} needs {self.spell.level} Magic')
            return
        self.log(f"Alcher — {self.spell.name} on {len(self.selected)} item(s), richest first: {', '.join([i.label for i in self.selected])}")
        resolved = yield from self.resolve_bank()
        if not resolved:
            return
        self.add(EnsureGear(self), Restock(self), Alch(self))

    def loop(self):
        if len(self.targets()) == 0 and self.pack_alchable() is None:
            self.log('the bank is out of every selected item — stopping')
            self.request_finish('the bank is out of every selected item')
            return
        result = yield from TaskBot.loop(self)
        return result

    def resolve_bank(self):
        """The nearest bank a route reaches, once, and the walk to it; later trips reuse it. Use with yield from.

        Why: inside a dungeon the bank nearest in a straight line can be one far from the exit, so the routes are
        priced first."""
        here = game.tile()
        if here is None:
            return False
        found = nearest_bank_reachable(here, navigator)
        if found is None:
            self.log('no reachable bank — stopping')
            self.request_finish('no reachable bank')
            return False
        self.bank = found
        access = found.get('npcAccess') or found.get('access') or BOOTH
        tile = found['tile']
        self.bank_tile = Tile(tile['x'], tile['z'], tile['level'])
        self.bank_name = found['name']
        self.log(f"banking at {self.bank_name} ({access['name']} / {access['op']})")
        if self.bank_tile.level == here.level and self.bank_tile.distance_to(here) <= 4:
            return True
        self.status = f'walking to {self.bank_name}'
        arrived = yield from traversal.walk_resilient(self.bank_tile, radius=3, attempts=4, timeout_ms=180000, log=lambda m: self.log(f'  {m}'))
        if not arrived:
            self.log('walk to the bank failed — stopping')
            self.request_finish('walk to the bank failed')
            return False
        return True

    def recovery_anchor(self):
        return self.bank_tile

    def open_bank(self):
        """Opens the resolved bank's booth or banker, and walks back to it when an evade has carried us off. Use
        with yield from."""
        if bank.is_open():
            return True
        yield from self.settle_cast()
        self.status = 'opening bank'
        opened = yield from open_bank_access(self.bank, BOOTH, lambda m: self.log(f'  {m}'))
        if opened:
            return True
        here = game.tile()
        strayed = self.bank_tile is not None and here is not None and (here.level != self.bank_tile.level or self.bank_tile.distance_to(here) > BANK_LEASH)
        if not strayed:
            self.log('could not open the bank — retrying')
            return False
        self.status = f'walking back to {self.bank_name}'
        self.log(f'drifted off the bank stand — walking back to {self.bank_name}')
        yield from traversal.walk_resilient(self.bank_tile, radius=3, attempts=3, timeout_ms=120000, log=lambda m: self.log(f'  {m}'))
        return False

    def note_cast(self):
        self.cast_tick = game.tick()

    def settle_cast(self):
        """Waits out the last cast's delay. Use with yield from.

        Why: the engine drops an op it decodes while the player is delayed, so a booth click inside the cast's own
        delay is binned, and the open sits out its timeout before retrying."""
        since = game.tick() - self.cast_tick
        if since < ALCH_TICKS:
            yield from execution.delay_ticks(ALCH_TICKS - since)

    def bank_truly_out_of(self, names):
        """Whether the loaded bank holds none of the names. Use with yield from.

        Why: a count of 0 can be a list that hasn't loaded rather than an empty bank."""
        settled = yield from execution.delay_until(lambda: bank.ready(), 3500)
        if not settled:
            return False
        return len([name for name in names if bank.count(name) != 0]) == 0

    def targets(self):
        """The selected items the bank hasn't been confirmed out of, richest first."""
        return [i for i in self.selected if i.key not in self.empty]

    def target(self):
        return next_alch_target(self.selected, self.empty)

    def mark_empty(self, item):
        self.empty.add(item.key)
        self.stock[item.key] = 0
        self.log(f'the bank is out of {item.label} — moving on')

    def noted_id(self, item):
        """The noted id an item lands as in note mode; the unnoted id, not kept, while the catalog has none."""
        hit = self.noted.get(item.key)
        if hit is not None:
            return hit
        id = live_catalog().noted_of.get(item.id)
        if id is None:
            return item.id
        self.noted[item.key] = id
        return id

    def notes_held(self, item):
        return inventory.count_by_id(self.noted_id(item))

    def notes_in_pack(self):
        """Every selected item's notes in the pack, so the rune top-up covers all of them."""
        return sum([self.notes_held(item) for item in self.selected])

    def pack_alchable(self):
        """The richest selected item with notes in the pack, whether or not the bank still has it."""
        for item in self.selected:
            if self.notes_held(item) > 0:
                return item
        return None

    def note_in_pack(self, item):
        id = self.noted_id(item)
        for i in inventory.items():
            if i.id == id:
                return i
        return None

    def can_alch_one(self):
        """The pack funds one cast: a note to alch and a nature rune."""
        return self.pack_alchable() is not None and inventory.count(NATURE_RUNE) > 0

    def bank_stock(self, item):
        return self.stock.get(item.key, 0)

    def fuel(self):
        """The alchs the bank still holds over every item in play."""
        return sum([self.bank_stock(item) for item in self.targets()])

    def count_alch(self, item, n):
        self.alched += n
        self.gp += n * item.alch_value

    def on_progress_report(self):
        minutes = (time.time() - self.started_at) / 60
        per_hour = (self.alched / minutes) * 60 if minutes >= 0.5 else 0
        target = self.target()
        return {
            'Status': self.status,
            'Target': target.label if target is not None else 'out of stock',
            'Alchs': self.alched,
            'Alch/hr': round(per_hour) if per_hour > 0 else '—',
            'Profit': fmt_gp(self.gp),
            'Trips': self.trips,
            'Notes': self.notes_in_pack(),
            'Runes': inventory.count(NATURE_RUNE),
            'Banked': self.fuel(),
            'Magic xp': skills.xp('magic') - self.xp_at_start,
        }


def _has_equip_option(name):
    item = inventory.first(name)
    if item is None:
        return False
    for option in item.actions():
        if option is not None and len([w for w in EQUIP_WORDS if w in option.lower()]) > 0:
            return True
    return False


class EnsureGear(Task):
    """A fire-rune staff, once: everything deposited, one withdrawn, the bank closed so Wield is a backpack
    option, worn, and the bank opened again."""

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    def validate(self):
        return pick_fire_staff(equipment.contains) is None

    def execute(self):
        bot = self.bot
        opened = yield from bot.open_bank()
        if not opened:
            return
        if inventory.used() > 0:
            yield from bank.deposit_all_matching(lambda name, id: True)
            yield from execution.delay_ticks(1)
        staff = pick_fire_staff(lambda name: inventory.count(name) > 0)
        if staff is None:
            staff = pick_fire_staff(lambda name: bank.count(name) > 0)
            took = False
            if staff is not None:
                bot.log(f'withdrawing {staff}')
                took = yield from bank.withdraw_x(staff, 1)
            if not took:
                out = yield from bot.bank_truly_out_of(FIRE_STAVES)
                if not out:
                    bot.log('withdraw of a fire staff stalled but the bank list is still settling — retrying')
                    return
                bot.log('no fire staff in the bank — stopping')
                bot.request_finish('no fire staff in the bank')
                return
        closed = yield from bank.close()
        if not closed:
            bot.log('bank would not close — retrying')
            return
        # Why: closing leaves the Deposit options on the backpack for a beat, so the equip waits for Wield.
        yield from execution.delay_until(lambda: not bank.is_open() and _has_equip_option(staff), 3000)
        bot.status = f'wielding {staff}'
        worn = yield from equipment.equip(staff)
        if not worn:
            bot.log(f'could not wield {staff} — stopping')
            bot.request_finish(f'could not wield {staff}')
            return
        bot.log(f'wore {staff} — casts need only {NATURE_RUNE}s now')
        yield from bot.open_bank()


class Restock(Task):
    """Keeps the runes and the notes still worth alching, and tops the pack up from the richest item the bank
    still holds. Items the bank is out of are marked, so the next trip drops to the one below."""

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    def validate(self):
        # Why: whenever the pack can't cover one cast. A bank short of the trip amount still gives a partial load
        # that gets alched, so a shortfall never turns into a loop.
        return not self.bot.can_alch_one()

    def execute(self):
        bot = self.bot
        opened = yield from bot.open_bank()
        if not opened:
            return

        # Why: coins and whatever random events left go in; the nature runes and the notes to alch stay, so a
        # short bank stock never starts from scratch.
        bot.status = 'restocking'
        keep = set([bot.noted_id(item) for item in bot.selected])
        if inventory.used() > 0:
            before = inventory.used()
            runes = NATURE_RUNE.lower()
            yield from bank.deposit_all_matching(lambda name, id: name.lower() != runes and id not in keep)
            yield from execution.delay_ticks(1)
            cleared = before - inventory.used()
            if cleared > 0:
                bot.log(f'cleared {cleared} items from the pack')

        # Why: note mode withdraws the item as notes, which one cast at a time alchs in full. The bank opens in
        # item mode, so it's set after opening.
        yield from bank.set_note_mode(True)
        if not bank.ready():
            # Why: a count of 0 proves the bank out only once it has said what it holds.
            bot.log('bank item list not loaded yet — retrying restock')
            yield from execution.delay_until(lambda: bank.ready(), 5000)
            return

        # Why: the loaded bank reading 0 is what proves an item gone, so a withdrawal that fails for a passing
        # reason is retried instead of retiring an item the bank still holds.
        for item in bot.targets():
            stock = bank.count_by_id(item.id)
            bot.stock[item.key] = stock
            if stock == 0:
                bot.mark_empty(item)

        target = bot.target()
        if target is None:
            bot.log('the bank is out of every selected item — stopping')
            bot.request_finish('the bank is out of every selected item')
            return

        want = bot.alchs
        held = bot.notes_held(target)
        if held < want:
            yield from bank.withdraw_x_by_id(target.id, want - held, bot.noted_id(target))
            got = bot.notes_held(target) - held
            if got == 0:
                bot.log(f'withdraw of {target.label} landed nothing against {bot.bank_stock(target)} banked — retrying')
                return
            bot.log(f'withdrew {got} {target.label} (noted, {target.alch_value}gp each)')

        need_runes = bot.notes_in_pack() - inventory.count(NATURE_RUNE)
        if need_runes > 0:
            before = inventory.count(NATURE_RUNE)
            ok = yield from bank.withdraw_x(NATURE_RUNE, need_runes)
            got = inventory.count(NATURE_RUNE) - before
            if got > 0:
                bot.log(f'withdrew {got} {NATURE_RUNE}s')
            if not ok or got == 0:
                bot.log(f'no {NATURE_RUNE}s in the bank — stopping')
                bot.request_finish(f'no {NATURE_RUNE}s in the bank')
                return

        closed = yield from bank.close()
        if not closed:
            bot.log('bank would not close — retrying')
            return
        bot.trips += 1
        bot.log(f'restocked: {bot.notes_held(target)} {target.label} notes + {inventory.count(NATURE_RUNE)} {NATURE_RUNE}s')


class Alch(Task):
    """One cast a call.

    Why: random events break in only between loop passes, so a loop of all 27 casts gave them no point to, and the
    bot alched on through swarms and dwarves until it died."""

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    def validate(self):
        if bank.is_open():
            return False
        return self.bot.can_alch_one()

    def execute(self):
        bot = self.bot
        target = bot.pack_alchable()
        if target is None:
            return
        bot.status = f'alching {target.label}'
        # Why: waiting the cast out at the end of the call put the loop's own gap after it, which sent the next click
        # most of a tick late; waiting the remainder here sends every click on the tick.
        yield from bot.settle_cast()
        yield from game.open_side_tab(MAGIC_TAB)
        note = bot.note_in_pack(target)
        if note is None:
            return
        before = bot.notes_held(target)
        if not game.cast_on_item(bot.spell.name, note):
            bot.log('cast-on-item was rejected — retrying')
            yield from execution.delay_ticks(1)
            return
        bot.note_cast()
        landed = yield from execution.delay_until_ticks(lambda: bot.notes_held(target) < before, ALCH_LAND_TICKS)
        if not landed:
            bot.log(f'the cast on {target.label} landed nothing — retrying')
            return
        bot.count_alch(target, before - bot.notes_held(target))


BOT = define_bot(
    name='Alcher',
    create=Alcher,
    description='Alchemy loop — tick the items to alch and the bot drains them richest first, withdrawing each as notes and casting High or Low Level Alchemy (fire staff + nature runes) until the bank is out, then moving to the next',
    category='Magic',
    tags=['magic', 'high alchemy', 'low alchemy', 'alchemy', 'banking', 'noted'],
    settings_schema=SETTINGS,
)
