"""Chop then burn: with a full pack of logs, the woodcutter lights them in a lane of the fire plot rather than
banking them. rs2b0t's scripts/GatheringBot/ChopBurnTasks.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs import burn_lane_want, find_burn_lane, fire_reaction_ticks, in_fire_plot, is_burn_west, light_fire, run_in_dir
from rs2004.catalogs import should_burn_full_load, tile_key

# Why: a kite that takes it this far from the plot's centre ends the load, so it can start again by the plot.
KITE_LEFT_PLOT = 16


def _walkable(tile):
    return reachability.walkable(tile)


def _can_step(a, b):
    return reachability.can_step(a, b)


def hostile_face_target():
    """FleeCombat's filter for a face target, ignoring the sticky combat state."""
    if npcs.query().where(lambda n: n.in_combat and n.targets_me() and 'Attack' in n.actions()).nearest() is not None:
        return True
    return npcs.query().where(lambda n: n.in_combat and not n.targets_another_player() and 'Attack' in n.actions() and n.distance() <= 2).nearest() is not None


def occupied():
    return set([tile_key(l.tile()) for l in locs.query().results()])


def create_chop_burn_tasks(bot):
    return [ChopBurnLoad(bot)]


class ChopBurnLoad(Task):
    def __init__(self, bot):
        Task.__init__(self, label='chop burn load')
        self.bot = bot
        self.lane_dir = (-1, 0)

    def validate(self):
        bot = self.bot
        if not bot.burn_enabled() or bot.is_power_mode() or event_signal.pending():
            return False
        # The attackers are FleeCombat's; sticky combat state alone mustn't freeze chop-then-burn for minutes.
        if game.in_combat() and hostile_face_target():
            return False
        if bot.burning_load:
            return bot.log_count() > 0 and bot.has_tinderbox()
        return should_burn_full_load('chop-then-burn', inventory.is_full(), bot.log_count(), bot.has_tinderbox())

    def execute(self):
        bot = self.bot
        plot = bot.burn_plot_or_none()
        if plot is None:
            bot.log('burn: no fire plot — skipping')
            bot.end_burning_load()
            return
        if not bot.has_tinderbox():
            bot.set_status('burn: need tinderbox')
            bot.log('burn: need tinderbox — restock will fetch')
            bot.end_burning_load()
            return
        bot.begin_burning_load()
        stalls = 0
        lane_fails = 0
        local = bot.is_local_burn()
        while bot.log_count() > 0:
            if event_signal.pending() or (game.in_combat() and hostile_face_target()):
                # Why: walking off the plot, as a guard's kite does, ends the load, so it can start again by the
                # plot after the fight rather than soft-lock burning with nothing lit.
                here = game.tile()
                p = bot.burn_plot_or_none()
                if here is not None and p is not None and not in_fire_plot(here, p) and max(abs(here.x - (p.x0 + p.x1) // 2), abs(here.z - (p.z0 + p.z1) // 2)) > KITE_LEFT_PLOT:
                    bot.log('burn: combat kite left the plot — ending load to re-camp')
                    bot.end_burning_load()
                return
            plot = bot.burn_plot_or_none() or plot
            if bot.burn_lane_left <= 0:
                found = yield from self.goto_lane(plot)
                if not found:
                    if local and bot.try_expand_burn_plot():
                        lane_fails = 0
                        continue
                    if local and lane_fails < 4:
                        lane_fails += 1
                        bot.set_status('burn: waiting for clear tiles')
                        bot.log(f'burn: no clear lane — repath wait ({lane_fails}/4)')
                        yield from execution.delay_ticks(20)
                        continue
                    # A named bank strip, or a local one used up: this load's leftover logs are banked.
                    bot.log('burn: no space left near start — banking leftover logs' if local else 'burn: no clear lane — banking logs')
                    bot.end_burning_load()
                    return
            bot.set_status(f'burn: {bot.log_count()} {bot.burn_log_name()} (lane {bot.burn_lane_left})')
            outcome = yield from light_fire(bot.burn_log_name())
            if outcome == 'lit':
                bot.fires += 1
                bot.burn_lane_left -= 1
                stalls = 0
                lane_fails = 0
                yield from execution.delay_ticks(fire_reaction_ticks())
                continue
            bot.burn_lane_left = 0
            if outcome == 'blocked':
                continue
            stalls += 1
            if stalls >= 3:
                bot.log('burn: three stalls — ending load')
                bot.end_burning_load()
                return
        bot.end_burning_load()
        bot.log('burn: load finished')

    def goto_lane(self, plot):
        """Use with yield from."""
        bot = self.bot
        if game.tile() is None:
            return False
        for _ in range(3):
            want = burn_lane_want(bot.log_count())
            live = bot.burn_plot_or_none() or plot
            found = find_burn_lane(live, game.tile(), occupied(), want, _walkable, _can_step)
            if found is None:
                bot.set_status('burn: waiting for clear lane')
                yield from execution.delay_ticks(15)
                continue
            self.lane_dir = found.dir
            start = found.start
            full = found.run >= want and is_burn_west(found.dir)
            bot.set_status(f'burn: walk to full lane {start.x},{start.z} x{found.run}' if full else f'burn: walk to tile {start.x},{start.z} (lane x{found.run})')
            yield from traversal.walk_resilient(start, radius=0, attempts=2, timeout_ms=60000, log=lambda m: bot.log(f'  {m}'))
            at = game.tile()
            ok = at is not None and in_fire_plot(at, live)
            # Measured again from where it stopped; a lane that isn't west is one tile, since the client shoves west.
            cap = want if is_burn_west(self.lane_dir) else 1
            bot.burn_lane_left = run_in_dir(at, live, self.lane_dir, occupied(), _walkable, _can_step, cap) if ok else 0
            if bot.burn_lane_left > 0:
                note = ' (full load)' if full else (' (tight — light wherever)' if bot.burn_lane_left < want else '')
                bot.log(f'burn: lane {at.x},{at.z} dir {self.lane_dir[0]},{self.lane_dir[1]} x{bot.burn_lane_left}{note}')
                return True
        return False
