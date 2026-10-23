# Cuts uncut gems with a chisel at the nearest bank, lowest level first, banking the cut ones: rs2b0t's
# GemCutter (MIT, see thirdparty/rs2b0t). Each trip deposits the whole pack but the chisel, so start with nothing
# valuable carried.

import time

CHISEL_ID = 1755
CRUSHED_GEMSTONE_ID = 1633
BOOTH = {'name': 'Bank booth', 'op': 'Use-quickly'}
# Chisel uses queued in one go.
MAX_SPAM = 60
MAX_BANK_MS = 15000


class GemDef:
    def __init__(self, key, name, uncut_id, cut_id, level, xp, can_crush):
        self.key = key
        self.name = name
        self.uncut_id = uncut_id
        self.cut_id = cut_id
        self.level = level
        self.xp = xp
        self.can_crush = can_crush


GEMS = [
    GemDef('sapphire', 'Sapphire', 1623, 1607, 20, 500, False),
    GemDef('emerald', 'Emerald', 1621, 1605, 27, 675, False),
    GemDef('ruby', 'Ruby', 1619, 1603, 34, 850, False),
    GemDef('diamond', 'Diamond', 1617, 1601, 43, 1075, False),
    GemDef('dragonstone', 'Dragonstone', 1631, 1615, 55, 1375, False),
    GemDef('opal', 'Opal', 1625, 1609, 1, 150, True),
    GemDef('jade', 'Jade', 1627, 1611, 13, 200, True),
    GemDef('red_topaz', 'Red topaz', 1629, 1613, 16, 250, True),
]
GEM_OPTIONS = [g.name for g in GEMS]

SETTINGS = {
    'gems': SettingDef('string[]', [], 'Gems to cut', options=GEM_OPTIONS,
                       help='check specific gems to restrict the run; leave all unchecked to cut every gem your Crafting level allows — the bot deposits everything from your pack into the bank each cycle, including non-gems, so start with nothing valuable carried'),
}


def gem_by_uncut_id(id):
    for gem in GEMS:
        if gem.uncut_id == id:
            return gem
    return None


def eligible_gems(crafting_level, selected):
    """The gems Crafting allows, restricted to selected when it names some, lowest level first so cheap xp comes
    first."""
    wanted = [s.lower() for s in selected]
    gems = [g for g in GEMS if g.level <= crafting_level and (len(wanted) == 0 or g.name.lower() in wanted)]
    gems.sort(key=lambda g: g.level)
    return gems


def chisel():
    for item in inventory.items():
        if item.id == CHISEL_ID:
            return item
    return None


class Cut(Task):
    def __init__(self, bot):
        Task.__init__(self, label='cut')
        self.bot = bot

    def validate(self):
        # Cutting needs a chisel and an eligible gem.
        return not bank.is_open() and chisel() is not None and self.bot.peek_cuttable() is not None

    def execute(self):
        bot = self.bot
        tool = chisel()
        if tool is None:
            return
        # The highest slot, so the game works back through the stack.
        target_item = None
        target_gem = None
        for gem in bot.targets():
            items = [i for i in inventory.items() if i.id == gem.uncut_id]
            if len(items) > 0:
                target_item = items[-1]
                target_gem = gem
                break
        if target_item is None:
            return

        bot.status = f'cutting {target_gem.name}s'
        start_xp = skills.xp('crafting')
        for _ in range(MAX_SPAM):
            if inventory.count_by_id(target_gem.uncut_id) == 0 or inventory.count_by_id(CHISEL_ID) == 0:
                break
            tool.use_on(target_item)
        yield from execution.delay_until(lambda: skills.xp('crafting') > start_xp, 3000)
        if bot.take_refusal():
            bot.deny(target_gem)
        yield from execution.delay_ticks(1)


class BankTrip(Task):
    def __init__(self, bot):
        Task.__init__(self, label='bank trip')
        self.bot = bot

    def validate(self):
        return self.bot.count_eligible_uncuts() == 0

    def execute(self):
        bot = self.bot
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

        bot.log('depositing inventory (keeping chisel)')
        yield from bank.deposit_all_matching(lambda name, id: id != CHISEL_ID)
        yield from execution.delay_ticks(1)

        if inventory.count_by_id(CHISEL_ID) == 0:
            bot.log('withdrawing chisel')
            taken = yield from bank.withdraw_x_by_id(CHISEL_ID, 1)
            if not taken:
                bot.log('no chisel in bank; stopping')
                bot.request_finish('no chisel in bank')
                return

        withdrew = 0
        deposited = 0
        started = time.time() * 1000
        while time.time() * 1000 - started < MAX_BANK_MS:
            got_any = False
            for gem in bot.targets():
                if inventory.is_full():
                    break
                want = inventory.free()
                if want <= 0:
                    break
                before = inventory.count_by_id(gem.uncut_id)
                taken = yield from bank.withdraw_x_by_id(gem.uncut_id, want)
                if taken:
                    withdrew += inventory.count_by_id(gem.uncut_id) - before
                    got_any = True
                else:
                    bot.log(f'withdraw {gem.name} failed; marking empty in bank')
                    bot.mark_empty(gem)
            if got_any:
                break
            if inventory.is_full():
                before_deposit = inventory.used()
                yield from bank.deposit_all_matching(lambda name, id: id != CHISEL_ID)
                deposited = max(deposited, before_deposit - inventory.used())
                continue
            if len(bot.targets()) == 0:
                break
            yield from execution.delay_ticks(1)

        closed = yield from bank.close()
        if not closed:
            bot.log('bank would not close; retrying the trip')
            return
        if withdrew > 0 or deposited > 0:
            bot.trips += 1
            bot.log(f"banked @ {known['name']}: gave {deposited} items, took {withdrew} uncut gems")
        else:
            bot.log('nothing to deposit and the bank has no eligible gems; stopping')
            bot.request_finish('bank has no eligible gems')


class GemCutter(TaskBot):
    loop_delay = 100

    def on_start(self):
        self.denied = []
        self.confirmed_empty = []
        self.planned_level = -1
        self.trips = 0
        self.status = 'starting'
        self.refused = False
        self.xp_at_start = skills.xp('crafting')
        self.refresh_eligible()
        if len(self.eligible) == 0:
            self.log(f"No gems to cut; Crafting {skills.level('crafting')} with no selectable gem at or above level. Stopping.")
            self.request_finish("no selectable gems at the player's Crafting level")
            return
        self.on('chat_message', self.heard)
        self.log(f"GemCutter; cut {', '.join([g.name for g in self.eligible])} (Crafting {skills.level('crafting')})")
        self.add(Cut(self), BankTrip(self))

    def heard(self, e):
        text = e.text or ''
        if 'You need a Crafting level of' in text and 'to cut' in text:
            self.refused = True

    def loop(self):
        level = skills.level('crafting')
        if level != self.planned_level:
            self.planned_level = level
            self.refresh_eligible()
        # Stops once the bank has shown every eligible gem empty.
        if len(self.targets()) == 0:
            self.log('All selected gems confirmed empty in bank; stopping')
            self.request_finish('all gems confirmed empty in bank')
            return
        yield from TaskBot.loop(self)

    def refresh_eligible(self):
        self.eligible = [g for g in eligible_gems(skills.level('crafting'), self.settings.list('gems', [])) if g.key not in self.denied]

    def targets(self):
        return [g for g in self.eligible if g.key not in self.confirmed_empty]

    def deny(self, gem):
        self.denied.append(gem.key)
        self.eligible = [g for g in self.eligible if g.key != gem.key]
        self.log(f'Crafting {gem.level} required for {gem.name}; skipping it')
        if len(self.eligible) == 0:
            self.log('no cuttable gems remain; stopping')
            self.request_finish('no cuttable gems remain')

    def take_refusal(self):
        refused = self.refused
        self.refused = False
        return refused

    def mark_empty(self, gem):
        self.confirmed_empty.append(gem.key)
        self.log(f'{gem.name} confirmed empty in bank; skipping on future trips')

    def peek_cuttable(self):
        """The first eligible uncut gem in the pack, lowest level first."""
        for gem in self.eligible:
            for item in inventory.items():
                if item.id == gem.uncut_id:
                    return item
        return None

    def count_eligible_uncuts(self):
        ids = [g.uncut_id for g in self.eligible]
        return len([i for i in inventory.items() if i.id in ids])

    def on_progress_report(self):
        return {'Status': self.status, 'Crafting xp': skills.xp('crafting') - self.xp_at_start, 'Trips': self.trips,
                'Crafting': skills.level('crafting'), 'Pack': inventory.used()}


BOT = define_bot(
    name='GemCutter',
    create=GemCutter,
    description='Banks at the nearest bank, withdraws uncut gems and a chisel, cuts every gem your Crafting level allows — lowest-level first — deposits the cut gems (and crushed gems), and repeats. Leave all gems unchecked to cut everything you can; check specific gems to restrict the run to a subset. Each bank cycle deposits everything from your pack, so start with nothing valuable carried',
    category='Crafting',
    tags=['crafting', 'gems', 'banking', 'members'],
    settings_schema=SETTINGS,
)
