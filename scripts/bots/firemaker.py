# Banks logs and burns them along the longest clear lane beside the bank, at Varrock east or west, Draynor or
# Seers' Village: rs2b0t's Firemaker (MIT, see thirdparty/rs2b0t).

from rs2004.catalogs import FIRE_SPOTS, LOG_LEVELS, NoLightTiles, TINDERBOX, burn_lane_want, exact_tool, find_burn_lane
from rs2004.catalogs import fire_reaction_ticks, has_all_tools, in_fire_plot, is_burn_west, light_fire, run_in_dir, tile_key
from rs2004.catalogs import tool_keep_names, tool_restock_plan

SETTINGS = {
    'log_type': SettingDef('string', 'Logs', 'What to burn', options=list(LOG_LEVELS.keys())),
    'location': SettingDef('string', 'Varrock East', 'Where to burn', options=list(FIRE_SPOTS.keys()), help='each spot is a bank plus the longest clear west-running ground next to it'),
}

TOOLS = [exact_tool(TINDERBOX)]


def _walkable(tile):
    return reachability.walkable(tile)


def _can_step(a, b):
    return reachability.can_step(a, b)


class Firemaker(LoopingBot):
    loop_delay = 600

    def on_start(self):
        self.spot_name = self.settings.str('location', 'Varrock East')
        self.plot = FIRE_SPOTS.get(self.spot_name)
        self.log_name = self.settings.str('log_type', 'Logs')
        self.no_light = NoLightTiles()
        self.lane = 0
        self.fires = 0
        self.trips = 0
        self.failed_log_withdraws = 0
        self.pending_bank_generation = None
        self.xp_start = skills.xp('firemaking')
        self.status = 'starting'

        need = LOG_LEVELS.get(self.log_name)
        have = skills.level('firemaking')
        if self.plot is None or need is None:
            self.request_finish(f"unknown setting; log_type='{self.log_name}', location='{self.spot_name}'")
            return
        if have < need:
            self.request_finish(f'{self.log_name} need Firemaking {need}, you have {have}')
            return
        p = self.plot
        self.log(f'Firemaker; {self.log_name} at {self.spot_name}, plot x{p.x0}-{p.x1} z{p.z0}-{p.z1}')

    def loop(self):
        banked = yield from self.bank_leg()
        if not banked:
            return
        yield from self.burn_leg()
        self.trips += 1

    def logs_left(self):
        return inventory.count(self.log_name)

    def walk_to(self, dest, what, radius):
        self.status = f'walking to {what}'
        arrived = yield from traversal.walk_resilient(dest, radius=radius, attempts=3, timeout_ms=120000, log=lambda m: self.log(f'  {m}'))
        return arrived

    def wait_for_deposit(self):
        if self.pending_bank_generation is None:
            return True
        reloaded = yield from bank.wait_snapshot_after(self.pending_bank_generation)
        if not reloaded:
            self.log('bank stock did not reload after the deposit, reopening')
            yield from bank.close()
            return False
        self.pending_bank_generation = None
        return True

    def bank_leg(self):
        here = game.tile()
        stand = self.plot.bank
        if here is not None and max(abs(here.x - stand.x), abs(here.z - stand.z)) > 4:
            arrived = yield from self.walk_to(stand, f'the {self.spot_name} bank', 2)
            if not arrived:
                return False
        self.status = 'banking'
        opened = yield from bank.open_nearest('Bank booth', 'Use-quickly')
        if not opened:
            self.log('could not open the bank; retrying')
            return False
        if not bank.ready():
            return False
        deposited = yield from self.wait_for_deposit()
        if not deposited:
            return False
        deposit = deposit_all_except(tool_keep_names(TOOLS))
        if len([item for item in inventory.items() if deposit(item.name or '', item.id)]) > 0:
            self.pending_bank_generation = bank.snapshot_generation()
            yield from bank.deposit_all_matching(deposit)
        deposited = yield from self.wait_for_deposit()
        if not deposited:
            return False

        for step in tool_restock_plan(TOOLS, skills.level, inventory.count, bank.count):
            bank.withdraw(step.name)
            name = step.name
            taken = yield from execution.delay_until_ticks(lambda: inventory.count(name) > 0, 5)
            if not taken:
                self.request_finish(f'no {step.name} in the bank or pack')
                return False
        if not has_all_tools(TOOLS, skills.level, inventory.count):
            self.request_finish('no tinderbox in the bank or pack')
            return False
        if not bank.ready():
            return False
        if bank.count(self.log_name) == 0:
            self.request_finish(f'no {self.log_name} left in the bank')
            return False
        withdrawn = yield from bank.withdraw_x(self.log_name, backpack_capacity() - inventory.used())
        if not withdrawn:
            self.failed_log_withdraws += 1
            self.log(f'could not withdraw {self.log_name} ({self.failed_log_withdraws}/3)')
            if self.failed_log_withdraws >= 3:
                self.request_finish(f'could not withdraw {self.log_name}')
            return False
        self.failed_log_withdraws = 0

        yield from bank.close()
        return self.logs_left() > 0

    def occupied(self):
        return self.no_light.merge([tile_key(l.tile()) for l in locs.query().results()])

    def goto_lane(self):
        for _ in range(3):
            want = burn_lane_want(self.logs_left())
            found = find_burn_lane(self.plot, game.tile(), self.occupied(), want, _walkable, _can_step)
            if found is None:
                refused = f' ({self.no_light.size} tiles refused a light)' if self.no_light.size > 0 else ''
                self.log(f'no clear ground left in the {self.spot_name} plot{refused}; waiting for fires to burn out')
                self.status = 'waiting for a clear lane'
                yield from execution.delay_ticks(25)
                continue
            start = found.start
            full = found.run >= want and is_burn_west(found.dir)
            kind = 'full lane' if full else 'tile'
            self.status = f'walking to {kind} {start.x},{start.z} ({found.run} long)'
            yield from self.walk_to(start, f'lane {start.x},{start.z}', 0)

            at = game.tile()
            ok = at is not None and in_fire_plot(at, self.plot)
            cap = want if is_burn_west(found.dir) else 1
            self.lane = run_in_dir(at, self.plot, found.dir, self.occupied(), _walkable, _can_step, cap) if ok else 0
            if self.lane > 0:
                note = ', full load)' if full else (', tight fallback)' if self.lane < want else ')')
                self.log(f'lane {at.x},{at.z} dir {found.dir[0]},{found.dir[1]} x{self.lane} (wanted {want} at {start.x},{start.z}{note}')
                return True
            where = f'{at.x},{at.z}' if at is not None else 'nowhere'
            self.log(f"stopped at {where}, which is {'not lightable' if ok else 'outside the plot'}; rescanning")
        return False

    def burn_leg(self):
        stalls = 0
        while self.logs_left() > 0:
            if event_signal.pending():
                return
            if self.lane <= 0:
                found = yield from self.goto_lane()
                if not found:
                    return
            self.status = f'burning {self.logs_left()} {self.log_name} (lane {self.lane})'
            outcome = yield from light_fire(self.log_name)
            if outcome == 'lit':
                self.fires += 1
                self.lane -= 1
                stalls = 0
                yield from execution.delay_ticks(fire_reaction_ticks())
                continue
            self.lane = 0
            if outcome == 'blocked':
                at = game.tile()
                if at is not None:
                    self.no_light.add(at)
                continue
            stalls += 1
            if stalls >= 3:
                self.log('three lighting attempts went unanswered; rescanning from the bank')
                return

    def on_progress_report(self):
        return {'Status': self.status, 'Fires': self.fires, 'Trips': self.trips, 'Firemaking xp': skills.xp('firemaking') - self.xp_start, 'Logs': self.logs_left()}


BOT = define_bot(
    name='Firemaker',
    create=Firemaker,
    description='Banks logs and burns them along the longest clear lane next to the bank — Varrock east/west, Draynor or Seers',
    category='Firemaking',
    tags=['firemaking', 'banking', 'varrock', 'draynor', 'seers', 'afk'],
    settings_schema=SETTINGS,
)
