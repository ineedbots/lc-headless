# Mines ore at a camp and banks it: the mining side of rs2b0t's GatheringBot (MIT, see thirdparty/rs2b0t).
# It finds the camp from the catalogs, gets the best pickaxe from the bank (or buys one, when allowed), mines
# the best ore it can, and banks a full backpack at the camp's bank. With bank off it drops the ore instead.

from rs2004.catalogs import ROCK_OPTIONS, MINING_LOCATION_OPTIONS, TOOL_ACQUIRE_OPTIONS, ContinueDialog
from rs2004.catalogs import pickaxe_req, has_all_tools, tool_restock_plan, tools_needing_equip, best_held_tool_names
from rs2004.catalogs import MINING_LOCATIONS, resolve_gathering_location, resolve_rock_ids, rock_tier_by_id, pick_bucket_nearest
from rs2004.catalogs import plan_gather_tool_acquire, parse_tool_acquire_mode, AcquireWorld, walk_to_tool_vendor
from rs2004.catalogs import acquire_keep_names, booth_fields, create_return_to_anchor_task, AnchorHost, COINS

SETTINGS = {
    'rocks': SettingDef('string[]', ['Copper', 'Tin'], 'Rock types', options=ROCK_OPTIONS, help='the ores to mine; empty mines any'),
    'location': SettingDef('string', 'Use Closest', 'Location', options=MINING_LOCATION_OPTIONS, help='a camp, the nearest camp, or around where you start'),
    'leash_radius': SettingDef('number', 16, 'Leash radius (tiles)', 4, 64),
    'bank': SettingDef('boolean', True, 'Bank the ore', help='off drops it instead'),
    'tool_acquire': SettingDef('string', 'Off', 'Acquire tools', options=TOOL_ACQUIRE_OPTIONS, help='Buy / repair gets a pickaxe from Nurmof when the bank has none'),
}

MINE_TIMEOUT_MS = 12000
# A rock that gave nothing is left this many ticks while others are free.
ROCK_COOLDOWN_TICKS = 8
ORE_NAMES = ['Clay', 'Copper ore', 'Tin ore', 'Iron ore', 'Silver ore', 'Coal', 'Gold ore', 'Mithril ore', 'Adamantite ore', 'Runite ore', 'Uncut sapphire', 'Uncut emerald', 'Uncut ruby', 'Uncut diamond']


class Miner(TaskBot):
    def on_start(self):
        s = self.settings
        self.reqs = [pickaxe_req()]
        self.rock_ids = resolve_rock_ids(s.rocks) if s.rocks else resolve_rock_ids(ROCK_OPTIONS)
        here = game.tile()
        # Only camps with one of the chosen ores, so the nearest camp is one worth mining at.
        wanted = [r.lower() for r in s.rocks]
        camps = [c for c in MINING_LOCATIONS if not wanted or len([o for o in (c.resources or []) if o in wanted]) > 0]
        self.camp = resolve_gathering_location(s.location, here, camps)
        if s.location == 'Use Closest':
            # The nearest camp in a straight line can be one the walker can't reach, such as the desert's.
            camps.sort(key=lambda c: (c.spot.x - here.x) ** 2 + (c.spot.z - here.z) ** 2)
            self.camp = None
            for camp in camps[:6]:
                if traversal.route_cost(here, camp.spot) is not None:
                    self.camp = camp
                    break
                # Each plan gets a call of its own, under scripting.callTimeoutMs.
                yield 0
        self.anchor = self.camp.spot if self.camp is not None else here
        self.bank_stand = self.camp.bank_stand if self.camp is not None else None
        self.booth_name, self.booth_op = booth_fields(self.camp)
        self.host = AnchorHost(self.anchor, int(s.leash_radius), lambda m: log(' ', m))
        self.mined = 0
        self.trips = 0
        self.cooldown = {}
        self.xp_start = skills.xp('mining')
        log('mining', ', '.join(s.rocks) if s.rocks else 'any ore', 'at', self.camp.name if self.camp is not None else 'the start tile', self.anchor)
        self.add(
            ContinueDialog(),
            Task(lambda: not has_all_tools(self.reqs, skills.level, self.held), self.get_tools, 'tools'),
            Task(lambda: len(tools_needing_equip(self.reqs, skills.level, self.held, equipment.contains)) > 0, self.wield, 'wield'),
            Task(lambda: inventory.is_full() and self.settings.bank, self.bank_ore, 'bank'),
            Task(lambda: inventory.is_full() and not self.settings.bank, self.drop_ore, 'drop'),
            create_return_to_anchor_task(self.host, 4, 6, 120000, 30),
            Task(lambda: self.find_rock() is not None, self.mine, 'mine'),
        )

    def recovery_anchor(self):
        return self.anchor

    def held(self, name):
        return inventory.count(name) + (1 if equipment.contains(name) else 0)

    # Tools.

    def get_tools(self):
        log('no usable pickaxe; banking for one')
        opened = yield from self.open_bank()
        if not opened:
            yield from execution.delay_ticks(5)
            return
        plan = tool_restock_plan(self.reqs, skills.level, inventory.count, bank.count)
        for step in plan:
            yield from bank.withdraw_x(step.name, step.qty)
        if not has_all_tools(self.reqs, skills.level, self.held) and parse_tool_acquire_mode(self.settings.tool_acquire) == 'on':
            yield from self.buy_pickaxe()
            return
        yield from bank.close()
        if not has_all_tools(self.reqs, skills.level, self.held):
            self.request_finish('no pickaxe this account can use in the bank or the backpack')

    def buy_pickaxe(self):
        world = AcquireWorld(skills.level, self.held, inventory.count, bank.count, equipment.contains)
        plan = plan_gather_tool_acquire(self.reqs, world)
        if plan is None or plan.kind != 'buy':
            self.request_finish('no pickaxe, and none that can be bought')
            return
        log('acquire:', plan.reason, 'from', plan.vendor.keeper)
        yield from bank.deposit_all_matching(deposit_all_except(acquire_keep_names(plan)))
        need = plan.cost - inventory.count(COINS)
        if need > 0:
            yield from bank.withdraw_x(COINS, need)
        yield from bank.close()
        arrived = yield from walk_to_tool_vendor(plan.vendor, lambda m: log(' ', m))
        if not arrived:
            return
        opened = yield from shop.open(plan.vendor.keeper)
        if opened:
            yield from shop.buy(plan.name, 1)
            shop.close()

    def wield(self):
        for name in tools_needing_equip(self.reqs, skills.level, self.held, equipment.contains):
            yield from equipment.equip(name)

    # Banking.

    def open_bank(self):
        opened = yield from banking.open(self.bank_stand, self.booth_name, self.booth_op)
        return opened

    def bank_ore(self):
        opened = yield from self.open_bank()
        if not opened:
            log('could not open the bank; trying again')
            yield from execution.delay_ticks(5)
            return
        keep = best_held_tool_names(self.reqs, skills.level, self.held)
        yield from bank.deposit_all_matching(deposit_all_except(keep))
        self.trips += 1
        yield from bank.close()
        yield from traversal.walk_resilient(self.anchor, radius=6, timeout_ms=120000, log=lambda m: log(' ', m))

    def drop_ore(self):
        for item in inventory.items():
            if item.name in ORE_NAMES:
                item.interact('Drop')
                yield from execution.delay_ticks(1)

    # Mining.

    def find_rock(self):
        now = game.tick()
        anchor = self.anchor
        leash = self.host.leash_radius
        cooldown = self.cooldown
        rocks = locs.query().id(self.rock_ids).where(lambda r: r.tile().distance_to(anchor) <= leash).results()
        rocks = [r for r in rocks if cooldown.get((r.tile().x, r.tile().z), -1) < now]
        return pick_bucket_nearest(rocks, lambda r: rock_tier_by_id(r.id), lambda r: r.distance())

    def mine(self):
        rock = self.find_rock()
        if rock is None:
            return
        tile = rock.tile()
        id = rock.id
        before = inventory.used()
        if not rock.interact('Mine'):
            yield from execution.delay_ticks(1)
            return
        got = yield from execution.delay_until(lambda: inventory.used() > before or self.rock_gone(tile, id), MINE_TIMEOUT_MS)
        if inventory.used() > before:
            self.mined += 1
        elif not got:
            self.cooldown[(tile.x, tile.z)] = game.tick() + ROCK_COOLDOWN_TICKS

    def rock_gone(self, tile, id):
        now = locs.at(tile, LAYER_GROUND)
        return now is None or now.id != id

    def on_progress_report(self):
        return {'Ore mined': self.mined, 'Bank trips': self.trips, 'Mining xp': skills.xp('mining') - self.xp_start}


BOT = define_bot(
    name='Miner',
    create=Miner,
    description="Mines ore at a camp and banks it; the mining side of rs2b0t's GatheringBot",
    category='Mining',
    settings_schema=SETTINGS,
)
