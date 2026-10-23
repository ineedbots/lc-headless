# Cleans (identifies) grimy herbs at the nearest bank, lowest level first, banking the clean ones: rs2b0t's
# HerbCleaner (MIT, see thirdparty/rs2b0t). Each trip deposits the whole pack, so start with nothing valuable
# carried. Members only.

from rs2004.catalogs import HERBS, HERB_OPTIONS

BOOTH = {'name': 'Bank booth', 'op': 'Use-quickly'}
# How a grimy herb is cleaned.
IDENTIFY_OP = 'Identify'
# The engine's refusals: Herblore below the herb's level, or a free world.
CANNOT_IDENTIFY = ['you cannot identify this herb', 'need to be on a members world', "need to be on a members' world"]

SETTINGS = {
    'herbs': SettingDef('string[]', [], 'Herbs to clean', options=HERB_OPTIONS,
                        help='check specific herbs to restrict the run; leave all unchecked to clean every herb your Herblore level allows — the bot deposits everything from your pack into the bank each cycle, including non-herbs, so start with nothing valuable carried'),
}


def herb_by_unid_id(id):
    """2004's grimy herbs all read 'Unidentified herb', so herbs go by id: unid_id grimy, id clean."""
    for herb in HERBS:
        if herb.unid_id == id:
            return herb
    return None


def eligible_herbs(herblore_level, selected):
    """The herbs Herblore allows, restricted to selected when it names some, lowest level first so cheap
    identifies come before dear ones."""
    wanted = [s.lower() for s in selected]
    herbs = [h for h in HERBS if h.level <= herblore_level and (len(wanted) == 0 or h.name.lower() in wanted)]
    herbs.sort(key=lambda h: h.level)
    return herbs


def cannot_identify(text):
    lower = text.lower().replace('’', "'")
    return len([r for r in CANNOT_IDENTIFY if r in lower]) > 0


class Clean(Task):
    def __init__(self, bot):
        Task.__init__(self, label='clean')
        self.bot = bot

    def validate(self):
        return not bank.is_open() and self.bot.peek_cleanable() is not None

    def execute(self):
        bot = self.bot
        # Why: interact sends the option without waiting, so every grimy herb is clicked in one pass, and one
        # wait on the clean count and the xp covers them all.
        before_clean = bot.clean_count()
        before_xp = skills.xp('herblore')
        clicked = []
        for herb in bot.targets():
            for item in inventory.items():
                if item.id == herb.unid_id:
                    item.interact(IDENTIFY_OP)
                    clicked.append(herb)
        if len(clicked) == 0:
            return

        bot.status = f"identifying {len(clicked)} grimy herb{'' if len(clicked) == 1 else 's'}"
        ok = yield from execution.delay_until(lambda: bot.clean_count() > before_clean or skills.xp('herblore') > before_xp, 3000)
        if ok:
            bot.cleaned += bot.clean_count() - before_clean
        elif bot.take_refusal():
            # Why: the engine refused every click, from drift in the level table or a free world, so the herbs
            # clicked are denied rather than a guessed level.
            for herb in clicked:
                bot.deny(herb)
        yield from execution.delay_ticks(1)


class BankTrip(Task):
    def __init__(self, bot):
        Task.__init__(self, label='bank trip')
        self.bot = bot

    def validate(self):
        return bank.is_open() or self.bot.count_eligible_unids() == 0

    def execute(self):
        bot = self.bot
        if bot.count_eligible_unids() > 0:
            yield from bank.close()
            return

        here = game.tile()
        known = nearest_bank(here) if here is not None else None
        if known is None:
            bot.log('no reachable bank')
            return
        bot.status = f"banking at {known['name']}"
        stand = Tile(known['tile']['x'], known['tile']['z'], known['tile']['level'])
        near = here is not None and stand.level == here.level and stand.distance_to(here) <= 4
        if not near:
            walked = yield from traversal.walk_resilient(stand, radius=3, attempts=4, timeout_ms=180000, log=lambda m: bot.log(f'  {m}'))
            if not walked:
                bot.log('walk to the bank failed; retrying')
                return

        opened = yield from open_bank_access(known, known.get('access') or BOOTH, lambda m: bot.log(f'  {m}'))
        if not opened:
            bot.log('could not open the bank; retrying')
            return
        ready = yield from bank.wait_ready()
        if ready:
            ready = yield from bank.backpack_ready()
        if not ready:
            bot.log('bank contents are still loading, retrying')
            return

        before_deposit = inventory.used()
        yield from bank.deposit_all_matching(lambda name, id: True)
        deposited = before_deposit - inventory.used()
        if inventory.used() > 0:
            bot.log('items remain after depositing, retrying')
            return

        withdrew = 0
        for herb in bot.targets():
            if inventory.is_full():
                break
            if bank.snapshot_ready() and len([i for i in bank.items() if i.id == herb.unid_id and i.count > 0]) == 0:
                bot.mark_empty(herb)
                continue
            before = inventory.count_by_id(herb.unid_id)
            withdrawn = yield from bank.withdraw_load(herb.unid_id)
            if not withdrawn:
                bot.log(f'withdraw {herb.name} did not complete, retrying')
                return
            withdrew += inventory.count_by_id(herb.unid_id) - before

        closed = yield from bank.close()
        if not closed:
            bot.log('bank would not close; retrying the trip')
            return
        if withdrew > 0 or deposited > 0:
            bot.trips += 1
            bot.log(f"banked @ {known['name']}: gave {deposited} items, took {withdrew} grimy herbs")
        elif len(bot.targets()) == 0:
            bot.log('nothing to deposit and the bank has no eligible herbs; stopping')
            bot.request_finish('bank has no eligible herbs')


class HerbCleaner(TaskBot):
    loop_delay = 100

    def on_start(self):
        self.denied = []
        self.confirmed_empty = []
        self.planned_level = -1
        self.cleaned = 0
        self.trips = 0
        self.status = 'starting'
        self.refused = False
        self.xp_at_start = skills.xp('herblore')
        self.refresh_eligible()
        if len(self.eligible) == 0:
            self.log(f"No herbs to clean; Herblore {skills.level('herblore')} with no selectable herb at or above level. Stopping.")
            self.request_finish("no selectable herbs at the player's Herblore level")
            return
        self.on('chat_message', self.heard)
        self.log(f"HerbCleaner; clean {', '.join([h.name for h in self.eligible])} (Herblore {skills.level('herblore')})")
        self.add(Clean(self), BankTrip(self))

    def heard(self, e):
        if cannot_identify(e.text or ''):
            self.refused = True

    def loop(self):
        # The eligible herbs follow a level gained mid-run.
        level = skills.level('herblore')
        if level != self.planned_level:
            self.planned_level = level
            self.refresh_eligible()
        # Why: a withdraw that fails against a loaded bank means the herb is gone, so once every eligible herb is
        # marked, the trips have nothing left to fetch.
        if len(self.targets()) == 0 and not bank.is_open():
            self.log('every selected herb is empty in the bank, stopping')
            self.request_finish('every selected herb is empty in the bank')
            return
        yield from TaskBot.loop(self)

    def refresh_eligible(self):
        self.eligible = [h for h in eligible_herbs(skills.level('herblore'), self.settings.list('herbs', [])) if h.key not in self.denied]

    def targets(self):
        return [h for h in self.eligible if h.key not in self.confirmed_empty]

    def mark_empty(self, herb):
        self.confirmed_empty.append(herb.key)
        self.log(f'{herb.name} is empty in the bank, skipping it on later trips')

    def clean_count(self):
        """The eligible clean herbs held."""
        ids = [h.id for h in self.eligible]
        return len([i for i in inventory.items() if i.id in ids])

    def deny(self, herb):
        self.denied.append(herb.key)
        self.eligible = [h for h in self.eligible if h.key != herb.key]
        self.log(f'Herb {herb.level} required for {herb.name}; skipping it')
        if len(self.eligible) == 0:
            self.log('no cleanable herbs remain; stopping')
            self.request_finish('no cleanable herbs remain')

    def take_refusal(self):
        refused = self.refused
        self.refused = False
        return refused

    def peek_cleanable(self):
        """The first eligible grimy herb in the pack, lowest level first."""
        for herb in self.eligible:
            for item in inventory.items():
                if item.id == herb.unid_id:
                    return item
        return None

    def count_eligible_unids(self):
        ids = [h.unid_id for h in self.eligible]
        return len([i for i in inventory.items() if i.id in ids])

    def on_progress_report(self):
        return {'Status': self.status, 'Cleaned': self.cleaned, 'Trips': self.trips, 'Herblore': skills.level('herblore'),
                'Herblore xp': skills.xp('herblore') - self.xp_at_start, 'Pack': inventory.used()}


BOT = define_bot(
    name='HerbCleaner',
    create=HerbCleaner,
    description='Banks at the nearest bank, withdraws unidentified herbs, cleans (identifies) every one your Herblore level allows — lowest-level first — deposits the cleaned herbs, and repeats. Leave all herbs unchecked to clean everything you can; check specific herbs to restrict the run to a subset. Each bank cycle deposits everything from your pack, so start with nothing valuable carried',
    category='Herblore',
    tags=['herblore', 'identify', 'clean', 'banking', 'members'],
    settings_schema=SETTINGS,
)
