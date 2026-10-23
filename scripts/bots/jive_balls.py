# Shears sheep and banks the raw wool, keeping the shears: rs2b0t's JiveBalls (MIT, see thirdparty/rs2b0t). It
# works one of five flocks, or one picked at random by flock size, and gets shears from the bank or a free spawn.

import random

SHEARS = 1735
WOOL = 1737
SHEEP = 43
SHEARS_SPAWN = Tile(3152, 3306, 0)
SHEAR_FAILED = ['manages to get away', 'already been shorn', "can't reach that"]


class SheepSite:
    def __init__(self, id, label, pen, radius, bank, sheep):
        self.id = id
        self.label = label
        self.pen = pen
        self.radius = radius
        self.bank = bank
        self.sheep = sheep


SHEEP_SITES = [
    SheepSite('lumbridge', 'Lumbridge (16 sheep, Draynor bank)', Tile(3198, 3266, 0), 18, Tile(3093, 3243, 0), 16),
    SheepSite('varrock', 'Varrock south (5 sheep, Varrock East bank)', Tile(3245, 3347, 0), 25, Tile(3253, 3420, 0), 5),
    SheepSite('falador', 'Falador west (3 sheep, Falador West bank)', Tile(2925, 3324, 0), 10, Tile(2946, 3369, 0), 3),
    SheepSite('monastery', 'Monastery (3 sheep, Edgeville bank)', Tile(3052, 3518, 0), 10, Tile(3094, 3493, 0), 3),
    SheepSite('ardougne', 'Ardougne north (10 sheep, north bank)', Tile(2654, 3367, 0), 16, Tile(2616, 3332, 0), 10),
]


def choose_site(choice, rand=None):
    """The site a setting names, or for 'random', one drawn by flock size."""
    if choice != 'random':
        for site in SHEEP_SITES:
            if site.id == choice:
                return site
        return None
    draw = (rand() if rand is not None else random.random()) * sum([site.sheep for site in SHEEP_SITES])
    for site in SHEEP_SITES:
        draw -= site.sheep
        if draw < 0:
            return site
    return SHEEP_SITES[-1]


def shear_failed(text):
    lower = text.lower()
    return len([f for f in SHEAR_FAILED if f in lower]) > 0


LOCATION_LABELS = {'random': 'Random (weighted by flock size)'}
for _site in SHEEP_SITES:
    LOCATION_LABELS[_site.id] = _site.label

SETTINGS = {
    'location': SettingDef('string', 'random', 'Sheep location', options=['random'] + [site.id for site in SHEEP_SITES], option_labels=LOCATION_LABELS,
                           help='random picks once per run, favoring larger flocks. Select locations to spread bots across fields and worlds. Banks raw wool; gets shears from your bank or a free spawn'),
}


class JiveBalls(TaskBot):
    loop_delay = 100

    def on_start(self):
        self.status = 'starting'
        self.collected = 0
        self.banked = 0
        self.fetching_shears = False
        self.done = False
        self.retry_after = {}
        site = choose_site(self.settings.str('location', 'random'))
        if site is None:
            self.site = SHEEP_SITES[0]
            self.done = True
            self.request_finish('unknown sheep location; select a JiveBalls location')
            return
        self.site = site
        self.banking = self.shears() is None or inventory.count_by_id(SHEARS) > 1 or inventory.free() == 0 or len([i for i in inventory.items() if i.id != SHEARS and i.id != WOOL]) > 0
        self.startup = self.banking
        self.log(f'JiveBalls: {site.label}; shearing and banking raw wool')
        self.add(Task(lambda: not self.done and game.ingame(), self.run, 'Gather wool'))

    def recovery_anchor(self):
        return SHEARS_SPAWN if self.fetching_shears else self.site.pen

    def shears(self):
        for item in inventory.items():
            if item.id == SHEARS and not item.noted:
                return item
        return None

    def run(self):
        if not self.banking and bank.is_open():
            yield from bank.close()
            return
        if self.fetching_shears:
            if self.shears() is None:
                yield from self.fetch_shears()
                return
            self.fetching_shears = False
        if self.banking or self.shears() is None or inventory.free() == 0:
            self.banking = True
            yield from self.bank()
            return

        site = self.site
        here = game.tile()
        if here is None or here.level != site.pen.level or site.pen.distance_to(here) > site.radius:
            yield from self.go_to_flock()
            return
        now = game.tick()
        self.retry_after = {index: tick for index, tick in self.retry_after.items() if tick > now}
        retry_after = self.retry_after

        def shearable(n):
            return (n.id == SHEEP and n.tile().level == site.pen.level and not n.targets_another_player() and n.index not in retry_after
                    and reachability.can_reach(n.tile(), adjacent_ok=True, max_steps=2048))

        candidates = npcs.query().name('Sheep').within_of(site.pen, site.radius).where(shearable).results()
        candidates.sort(key=lambda n: n.distance())
        candidates = candidates[0:3]
        if len(candidates) == 0:
            if site.pen.distance_to(here) > 2 or not reachability.can_reach(site.pen):
                yield from self.go_to_flock()
            else:
                self.status = 'waiting for sheep to regrow'
                yield from execution.delay_ticks(2)
            return
        sheep = candidates[random.randint(0, len(candidates) - 1)]

        self.status = 'shearing sheep'
        before = inventory.count_by_id(WOOL)
        mark = game_messages.mark()
        if self.shears().use_on(sheep):
            yield from execution.delay_until(lambda: inventory.count_by_id(WOOL) > before or game_messages.saw_since(mark, shear_failed), 6000)
        gained = inventory.count_by_id(WOOL) - before
        if gained > 0:
            self.collected += gained
            execution.note_progress()
        else:
            self.retry_after[sheep.index] = game.tick() + 5

    def go_to_flock(self):
        self.status = f'walking to {self.site.label}'
        yield from traversal.walk_resilient(self.site.pen, radius=2, attempts=3, timeout_ms=180000, log=self.log)

    def bank(self):
        self.status = 'banking wool'
        opened = yield from banking.open(None if self.startup else self.site.bank, log=self.log)
        if not opened:
            return
        ready = yield from bank.wait_ready()
        if not ready:
            return
        ready = yield from bank.backpack_ready()
        if not ready:
            return
        before = inventory.count_by_id(WOOL)
        yield from bank.deposit_all_matching(lambda name, id: id != SHEARS)
        deposited = max(0, before - inventory.count_by_id(WOOL))
        self.banked += deposited
        if deposited > 0:
            execution.note_progress()
        if len([i for i in inventory.items() if i.id != SHEARS]) > 0:
            return
        while inventory.count_by_id(SHEARS) > 1:
            held = inventory.count_by_id(SHEARS)
            if not bank.deposit('Shears'):
                return
            dropped = yield from execution.delay_until(lambda: inventory.count_by_id(SHEARS) < held, 4000)
            if not dropped:
                return

        if self.shears() is None:
            if bank.count_by_id(SHEARS) > 0:
                yield from bank.set_note_mode(False)
                taken = yield from bank.withdraw_x_by_id(SHEARS, 1)
                if not taken:
                    return
            else:
                self.fetching_shears = True
        self.banking = False
        self.startup = False
        yield from bank.close()

    def fetch_shears(self):
        self.status = 'collecting free shears'
        here = game.tile()
        if here is None or here.level != 0 or SHEARS_SPAWN.distance_to(here) > 3 or not reachability.can_reach(SHEARS_SPAWN, adjacent_ok=True):
            yield from traversal.walk_resilient(SHEARS_SPAWN, radius=1, attempts=3, timeout_ms=180000, log=self.log)
            return
        shears = ground_items.query().within_of(SHEARS_SPAWN, 2).where(lambda i: i.id == SHEARS and i.tile().level == 0).nearest()
        if shears is None:
            self.status = 'waiting for shears to respawn'
            yield from execution.delay_ticks(2)
            return
        if shears.interact('Take'):
            taken = yield from execution.delay_until(lambda: self.shears() is not None, 4000)
            if taken:
                execution.note_progress()

    def on_progress_report(self):
        return {'Status': self.status, 'Site': self.site.label, 'Collected': self.collected, 'Banked': self.banked}


BOT = define_bot(
    name='JiveBalls',
    create=JiveBalls,
    description='Shears sheep and banks raw wool, keeping shears. Select Lumbridge, Varrock south, Falador west, the Monastery or Ardougne north, or randomly choose a flock once per run, weighted by flock size. Retrieves shears from the bank or a free spawn. Waits for wool to regrow and repeats bank trips to the selected flock.',
    category='Money making',
    tags=['sheep', 'wool', 'shearing', 'banking', 'gathering'],
    settings_schema=SETTINGS,
)
