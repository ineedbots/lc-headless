# Two accounts at Seers' Village: the Runner picks flax and hands it over at the wheel house, and the Spinner
# spins it into bow strings and banks them: rs2b0t's FlaxRunner (MIT, see thirdparty/rs2b0t). Run one account as
# each, each naming the other as its partner.

import time

from rs2004.catalogs import ContinueDialog, drive_active_partner_trade

# FlaxRunnerLogic.ts

FLAX_FIELD = Tile(2741, 3444, 0)
FLAX_GATE = Tile(2736, 3443, 0)
SPINNING_WHEEL_AREA = Tile(2711, 3471, 1)
BANK_ENTRANCE = Tile(2726, 3487, 0)
BANK_STAND = Tile(2725, 3493, 0)
LADDER_TILE = Tile(2714, 3471, 0)
# Why: the tile sits outside the wheel house, a few tiles east of the east-wall door at (2716,3472).
# Why: meeting inside leaves partners "at meet" under LEASH behind a closed door, unable to trade or path through.
MEET_TILE = Tile(2719, 3471, 0)
TRADE_RANGE = 2
TRADE_REQUEST_COOLDOWN_TICKS = 9
TRADE_FAIL_COOLDOWN_TICKS = 14
TRADE_REQUEST_COOLDOWN_MS = TRADE_REQUEST_COOLDOWN_TICKS * 600
TRADE_FAIL_COOLDOWN_MS = TRADE_FAIL_COOLDOWN_TICKS * 600
FLAX = 'Flax'


def partner_name_matches(configured, seen):
    """Configured partner name matches trade-header / player display name (case-insensitive)."""
    if not configured or not seen:
        return False
    return configured.strip().lower() == seen.strip().lower()


def flax_units_in_offer(items):
    """Total flax units on a trade offer side (stacks use count)."""
    n = 0
    for o in items:
        if ((o.name if o.name is not None else '')).lower() == FLAX.lower():
            n += max(1, o.count)
    return n


# Why: a full runner pack cannot land when the spinner has only a few free slots, so the trade fails and both sides re-request.
def spinner_needs_clear_pack(flax_held, slots_used):
    """Whether the spinner must bank non-flax (bow strings, random-event junk) before handoff."""
    return flax_held == 0 and slots_used > 0


def can_receive_flax_offer(free_slots, offered_flax_units):
    """True if free inventory slots can hold `units` of offered flax (1 slot per stack item in trade)."""
    # Why: flax stacks in a trade still need one free slot per offered stack line, and a full runner pack is typically one stack of 28 or fewer.
    # Why: the spinner holds no flax at handoff, so one free slot receives the stack.
    if offered_flax_units <= 0:
        return True
    return free_slots >= 1


BOW_STRING = 'Bow string'
SPINNING_WHEEL = 'Spinning wheel'
SPIN_OP = 'Spin'
PICK_OP = 'Pick'
BOOTH_NAME = 'Bank booth'
LADDER_NAME = 'Ladder'
CLIMB_UP = 'Climb-up'
CLIMB_DOWN = 'Climb-down'
FIELD_SCOPE = 12
FIELD_ARRIVE = 3
LOCAL_PICK_RADIUS = 4
POCKET_CAP = 40
CARVE_DROP = 5

# FlaxRunner.ts

LEASH = 8
BOOTH_OP = 'Use-quickly'
SETTINGS = {
    'mode': SettingDef('string', 'Runner', 'Mode', options=['Runner', 'Spinner'], help='Runner picks flax and delivers to Spinner; Spinner spins flax into bow strings and banks them'),
    'partner': SettingDef('string', '', 'Partner name', help="Runner: spinner's player name. Spinner: runner's player name."),
    'min_flax_capacity': SettingDef('number', 24, 'Min flax capacity', min=1, max=28, help='Runner only: bank non-flax junk (keeps flax) when a full pack still has trash, or mid-trip when junk leaves room for fewer than this many flax'),
}


def flax_count():
    return inventory.count(FLAX)


def bow_string_count():
    return inventory.count(BOW_STRING)


def climb_ladder(name, op, log):
    ladder = locs.query().name(name).action(op).nearest()
    if not ladder:
        log(f"no '{name}' offering '{op}' nearby")
        return False
    before = (game.tile().level if game.tile() is not None else None)
    ladder.interact(op)

    def _fn2():
        t = game.tile()
        return t is not None and t.level != before
    _result1 = yield from execution.delay_until_ticks(_fn2, 14)
    return _result1


def now_ms():
    return time.time() * 1000


class FlaxRunner(TaskBot):
    loop_delay = 600

    def on_start(self):
        yield from execution.delay_until(lambda: game.ingame() and game.tile() is not None, 0)
        self._picked = 0
        self._delivered = 0
        self._spun = 0
        self._trips = 0
        self._status = 'starting'
        # The last flax tile committed to, kept while the plant's still there.
        self._sticky_flax = None
        # The earliest time a Trade with may be sent again, so the two don't thrash requests.
        self._next_trade_request_at_ms = 0
        self._started_at = time.time()
        self._mode = self.settings.str('mode', 'Runner')
        self._partner = self.settings.str('partner', '')
        self._min_flax_capacity = self.settings.num('min_flax_capacity', 24)
        self.log(f"{self._mode} mode — partner: {self._partner or '(none)'}" + ((f', min flax capacity {self._min_flax_capacity}' if self._mode == 'Runner' else '')))

        self.on('inventory_changed', self.on_inventory_changed)
        self.add(ContinueDialog())
        if self._mode == 'Runner':
            self.add(EscapeFlaxTrap(self), OfferTrade(self), BankJunk(self), WaitAndTrade(self), GoToMeet(self), PickFlax(self), WaitForFlax(self), GoToField(self))
        else:
            self.add(HandleTrade(self), SpinFlax(self), ClimbDown(self), BankStrings(self), ClimbUp(self), RequestTrade(self), GoToMeet(self))

    def on_inventory_changed(self, e):
        if e.id != -1 and self.is_flax(e.name):
            self._picked += 1

    def recovery_anchor(self):
        if self._mode == 'Spinner':
            # Random-event junk / leftover strings: clear pack before handoff.
            if self.spinner_needs_bank():
                return BANK_STAND
            return SPINNING_WHEEL_AREA
        # Junk bank mid-trip: prefer the bank so watchdog doesn't yank us to the field first.
        if self.needs_junk_bank():
            return BANK_STAND
        # Waiting on trade must not walk a full pack back to the field.
        return (MEET_TILE if self.ready_to_deliver() else FLAX_FIELD)

    def on_progress_report(self):
        minutes = int((time.time() - self._started_at) / 60)
        report = {'Status': f'{self._mode} — {self._status}', 'Runtime': f'{minutes}m', 'Partner': self._partner or '—', 'Trips': self._trips}
        if self._mode == 'Runner':
            report['Picked'] = self._picked
            report['Delivered'] = self._delivered
            report['Held'] = flax_count()
        else:
            report['Spun'] = self._spun
            report['Strings'] = bow_string_count()
        return report

    def get_mode(self):
        return self._mode

    def get_partner(self):
        return self._partner

    def is_flax(self, name):
        return (FLAX.lower() in ((name if name is not None else '')).lower())

    def is_partner(self, name):
        return partner_name_matches(self._partner, name)

    def can_request_trade(self):
        # Wall-clock: two players' Trade with thrash doesn't follow this client's tick rate.
        return now_ms() >= self._next_trade_request_at_ms

    def note_trade_request(self):
        self._next_trade_request_at_ms = now_ms() + TRADE_REQUEST_COOLDOWN_MS

    def note_trade_failed(self):
        self._next_trade_request_at_ms = now_ms() + TRADE_FAIL_COOLDOWN_MS

    def note_trade_ok(self):
        # Short quiet period after a successful handoff so both sides don't re-open.
        self._next_trade_request_at_ms = now_ms() + TRADE_REQUEST_COOLDOWN_MS

    def spinner_needs_bank(self):
        """Spinner: any non-flax in the pack with no flax held blocks a full runner delivery (random-event garbage, bow strings, etc.)."""
        return spinner_needs_clear_pack(flax_count(), inventory.used())

    def spinner_ready_for_handoff(self):
        """Spinner is ready to receive a full flax pack (empty inventory)."""
        return flax_count() == 0 and inventory.used() == 0

    def ready_to_deliver(self):
        """Pack is full and still holds flax, deliver, do not pick or return to the field."""
        return inventory.is_full() and flax_count() > 0 and not self.needs_junk_bank()

    def needs_flax(self):
        return not inventory.is_full()

    def flax_capacity(self):
        """Slots available for flax (pack size minus non-flax junk)."""
        free = inventory.free()
        used = inventory.used()
        size = free + used
        if size <= 0:
            return 28
        non_flax = max(0, used - flax_count())
        return max(0, size - non_flax)

    def has_non_flax(self):
        return inventory.used() > flax_count()

    # Why: a full pack that still holds junk clears the trash before walking to the meet.
    # Why: mid-trip junk that cuts flax capacity below minFlaxCapacity also forces the bank.
    def needs_junk_bank(self):
        """Whether non-flax should be banked, keeping flax."""
        if not self.has_non_flax():
            return False
        # Handoff-ready pack with trash: bank first, refill if needed, then meet.
        if inventory.is_full() and flax_count() > 0:
            return True
        return self.flax_capacity() < self._min_flax_capacity

    def bank_non_flax(self):
        def log(m):
            return self.log(f'  {m}')

        junk_before = max(0, inventory.used() - flax_count())
        self.set_status('banking non-flax junk')
        self.clear_sticky_flax()
        self.log(f'banking {junk_before} non-flax slot(s) (flax {flax_count()}, capacity {self.flax_capacity()}, min {self._min_flax_capacity})')
        if self.at_field():
            self.set_status('leaving the field via the gate')
            yield from traversal.walk_resilient(FLAX_GATE, radius=0, attempts=4, timeout_ms=120000, log=log)
        self.set_status('walking to the bank')
        arrived = yield from traversal.walk_resilient(BANK_ENTRANCE, radius=1, attempts=6, timeout_ms=240000, log=log)
        if not arrived:
            self.log('could not reach the bank entrance — will retry')
            return False
        yield from traversal.walk_resilient(BANK_STAND, radius=0, attempts=3, timeout_ms=60000, log=log)
        opened = yield from bank.open_booth(BANK_STAND, BOOTH_NAME, BOOTH_OP)
        if not opened:
            opened = yield from bank.open_nearest(BOOTH_NAME, BOOTH_OP)
        if not opened:
            self.log('could not open the bank — will retry')
            return False
        # Keep flax; dump random-event trash and anything else.
        yield from bank.deposit_all_matching(deposit_all_except([FLAX]))
        yield from bank.close()
        yield from execution.delay_ticks(1)
        self.log(f'deposited non-flax junk — holding {flax_count()} flax, capacity {self.flax_capacity()}')
        return True

    def at_field(self):
        here = game.tile()
        return here is not None and FLAX_FIELD.distance_to(here) <= FIELD_SCOPE

    def at_wheel(self):
        here = game.tile()
        return here is not None and SPINNING_WHEEL_AREA.distance_to(here) <= LEASH

    def at_meet(self):
        here = game.tile()
        # Why: a tight radius stops WaitAndTrade and RequestTrade pre-empting GoToMeet several tiles short of the handoff tile.
        # Why: LEASH would let partners "meet" on opposite sides of the house and never trade.
        return here is not None and MEET_TILE.distance_to(here) <= TRADE_RANGE

    def is_on_floor(self, level):
        t = game.tile()
        return t is not None and t.level == level

    def flax_loc_at(self, x, z, level):
        return locs.query().name(FLAX).action(PICK_OP).where(lambda l: l.tile().x == x and l.tile().z == z and l.tile().level == level).nearest()

    def flax_still_at(self, tile):
        return self.flax_loc_at(tile.x, tile.z, tile.level) is not None

    def _field_flax(self):
        return locs.query().name(FLAX).action(PICK_OP).where(lambda l: l.tile().distance_to(FLAX_FIELD) <= FIELD_SCOPE).results()

    def _reachable_sorted(self, flax, me):
        reachable = [f for f in flax if reachability.can_reach(f.tile(), adjacent_ok=True, max_steps=400)]
        reachable.sort(key=lambda a: a.tile().distance_to(me))
        return reachable

    def nearest_flax(self):
        """Prefer sticky target, then local plants, then nearest reachable in the field. Avoids thrashing across the field as plants respawn."""
        me = game.tile()
        all_ = self._field_flax()
        if len(all_) == 0:
            self._sticky_flax = None
            return None
        if not me:
            return all_[0]
        if self._sticky_flax and self.flax_still_at(self._sticky_flax):
            sticky = self.flax_loc_at(self._sticky_flax.x, self._sticky_flax.z, self._sticky_flax.level)
            if sticky and reachability.can_reach(sticky.tile(), adjacent_ok=True, max_steps=400):
                return sticky
        reachable = self._reachable_sorted(all_, me)
        if len(reachable) == 0:
            self._sticky_flax = None
            return None
        local = [f for f in reachable if f.tile().distance_to(me) <= LOCAL_PICK_RADIUS]
        pick = local[0] if len(local) > 0 else reachable[0]
        t = pick.tile()
        self._sticky_flax = Tile(t.x, t.z, t.level)
        return pick

    def clear_sticky_flax(self):
        self._sticky_flax = None

    def _pocket_tiles(self, cap):
        me = game.tile()
        if not me:
            return []
        level = me.level

        def key(x, z):
            return f'{x},{z}'

        seen = set([key(me.x, me.z)])
        out = [Tile(me.x, me.z, level)]
        queue = [Tile(me.x, me.z, level)]
        dirs = [[1, 0], [-1, 0], [0, 1], [0, -1]]
        while len(queue) > 0 and len(out) < cap:
            cur = queue.pop(0)
            from_ = cur
            for dx, dz in dirs:
                nx = cur.x + dx
                nz = cur.z + dz
                k = key(nx, nz)
                if (k in seen) or not reachability.can_step(from_, Tile(nx, nz, level)):
                    continue
                seen.add(k)
                out.append(Tile(nx, nz, level))
                queue.append(Tile(nx, nz, level))
        return out

    def _boundary_flax(self, pocket):
        _v8 = (game.tile().level if game.tile() is not None else None)
        level = (_v8 if _v8 is not None else 0)
        in_pocket = set([f'{t.x},{t.z}' for t in pocket])
        seen = set()
        walls = []
        dirs = [[1, 0], [-1, 0], [0, 1], [0, -1]]
        for p in pocket:
            for dx, dz in dirs:
                nx = p.x + dx
                nz = p.z + dz
                k = f'{nx},{nz}'
                if (k in in_pocket) or (k in seen):
                    continue
                seen.add(k)
                flax = self.flax_loc_at(nx, nz, level)
                if flax:
                    walls.append(flax)
        return walls

    def boxed_by_flax(self):
        """Full pack (or delivering) and reachable ground is a small pocket walled by flax. 2004 flax is solid collision. The runner can be sealed in as plants respawn."""
        if not self.at_field():
            return False
        if not inventory.is_full() and not self.ready_to_deliver():
            return False
        pocket = self._pocket_tiles(POCKET_CAP)
        return len(pocket) < POCKET_CAP and len(self._boundary_flax(pocket)) > 0

    def _drop_flax(self, n):
        for i in range(n):
            flax = ([it for it in inventory.items() if self.is_flax(it.name)] or [None])[0]
            if not flax:
                return
            before = flax_count()
            if not (flax.interact('Drop')):
                return
            yield from execution.delay_until_ticks(lambda: flax_count() < before, 4)

    def carve_out(self):
        self.set_status('boxed in by flax — carving a way out')
        self.log(f'boxed in by flax — dropping {CARVE_DROP} flax to pick a path toward the gate')
        self.clear_sticky_flax()
        yield from self._drop_flax(CARVE_DROP)
        for n in range(20):
            if chat_dialog.can_continue() or event_signal.pending():
                return
            pocket = self._pocket_tiles(POCKET_CAP)
            if len(pocket) >= POCKET_CAP:
                self.log('carved back out to open ground')
                return
            walls = self._boundary_flax(pocket)
            if len(walls) == 0:
                return
            if inventory.is_full():
                yield from self._drop_flax(CARVE_DROP)
            target = (sorted(walls, key=lambda a: a.tile().distance_to(FLAX_GATE)) or [None])[0]
            t = target.tile()
            if not (target.interact(PICK_OP)):
                yield from execution.delay_ticks(2)
                continue
            yield from execution.delay_until_ticks(lambda: not self.flax_still_at(t), 7)

    def nearest_partner(self):
        if not self._partner:
            return None
        return players.query().name(self._partner).nearest()

    def set_status(self, s):
        self._status = s

    def count_trip(self):
        self._trips += 1

    def count_delivered(self, n):
        self._delivered += n

    def count_spun(self, n):
        self._spun += n


# Runner tasks.
class EscapeFlaxTrap(Task):
    def __init__(self, bot):
        super().__init__()
        self._bot = bot

    def validate(self):
        if self._bot.get_mode() != 'Runner':
            return False
        if trade.active():
            return False
        return self._bot.boxed_by_flax()

    def execute(self):
        yield from self._bot.carve_out()


class BankJunk(Task):
    def __init__(self, bot):
        super().__init__()
        self._bot = bot

    def validate(self):
        if self._bot.get_mode() != 'Runner':
            return False
        if trade.active():
            return False
        return self._bot.needs_junk_bank()

    def execute(self):
        yield from self._bot.bank_non_flax()


class OfferTrade(Task):
    def __init__(self, bot):
        super().__init__()
        self._bot = bot
        self._partner_wait = 0

    def validate(self):
        if self._bot.get_mode() != 'Runner':
            return False
        return trade.active()

    def execute(self):
        def _fn9():
            self._partner_wait += 1
            if self._partner_wait > 8:
                self._partner_wait = 0
                return 'decline'
            return 'wait'

        def _fn10():
            self._bot.note_trade_failed()

        def _fn11(delta):
            # Giver: flax leaves pack → delta is negative when metric is flax count.
            gone = -delta
            if gone > 0:
                self._bot.count_delivered(gone)
                self._bot.count_trip()
                self._bot.note_trade_ok()
                self._bot.log(f'delivered {gone} flax to spinner')
            else:
                self._bot.note_trade_failed()
                self._bot.log('trade closed without delivering flax — backing off before re-request')
        yield from drive_active_partner_trade(
            'giver', [self._bot.get_partner()], lambda name: False, lambda: [FLAX] if flax_count() > 0 else [],
            self._bot.set_status, self._bot.log,
            inventory_metric=flax_count,
            verify_giver_partner=True,
            my_offer_ready=lambda: flax_units_in_offer(trade.my_offer()) > 0,
            on_missing_partner=_fn9,
            on_decline=_fn10,
            on_complete=_fn11,
            labels={
                'confirming': 'confirming trade with spinner',
                'wait_header': 'reading trade partner',
                'offering': 'offering flax to spinner',
                'accepting_offer': 'accepting trade offer',
                'declining': 'declining trade',
            })
        # Reset wait counter once a partner header is present.
        if trade.partner() is not None:
            self._partner_wait = 0
        if not trade.active():
            self._partner_wait = 0


class WaitAndTrade(Task):
    def __init__(self, bot):
        super().__init__()
        self._bot = bot

    def validate(self):
        if self._bot.get_mode() != 'Runner':
            return False
        if trade.active():
            return False
        if not self._bot.ready_to_deliver():
            return False
        if not self._bot.can_request_trade():
            return False
        return self._bot.at_meet()

    def execute(self):
        partner = self._bot.nearest_partner()
        if not partner or partner.distance() > TRADE_RANGE:
            self._bot.set_status('waiting for spinner to arrive')
            yield from execution.delay_ticks(2)
            return
        self._bot.set_status('requesting trade with spinner')
        self._bot.note_trade_request()
        trade.request(self._bot.get_partner())
        # Wall-clock: mutual Trade-with needs both players; tick waits shrink under speed 300.
        yield from execution.delay_until(lambda: trade.active() or event_signal.pending(), 5000)


class GoToMeet(Task):
    def __init__(self, bot):
        super().__init__()
        self._bot = bot

    def validate(self):
        if trade.active():
            return False
        here = game.tile()
        if not here:
            return False
        # Match atMeet / TRADE_RANGE, a d<=1 test fights WaitAndTrade at d=2.
        if self._bot.at_meet():
            return False
        # Runner only leaves the field when the pack is ready to hand off.
        if self._bot.get_mode() == 'Runner':
            return self._bot.ready_to_deliver()
        # Spinner: clear pack first (BankStrings), then meet only when empty.
        if self._bot.get_mode() == 'Spinner':
            if self._bot.spinner_needs_bank():
                return False
            return self._bot.spinner_ready_for_handoff()
        return True

    def execute(self):
        self._bot.set_status('travelling to meet point')
        self._bot.clear_sticky_flax()
        # Outside the wheel house (east of the door) so a closed door cannot
        # trap partners mid-handoff. Nav opens doors when the spinner leaves.
        yield from traversal.walk_resilient(MEET_TILE, radius=TRADE_RANGE, attempts=6, timeout_ms=240000, log=lambda m: self._bot.log(f'  {m}'))


class PickFlax(Task):
    def __init__(self, bot):
        super().__init__()
        self._bot = bot

    def validate(self):
        if self._bot.get_mode() != 'Runner':
            return False
        if trade.active():
            return False
        if not self._bot.needs_flax():
            return False
        return self._bot.at_field() and self._bot.nearest_flax() is not None

    def execute(self):
        for n in range(30):
            if not self._bot.needs_flax():
                return
            if chat_dialog.can_continue() or event_signal.pending():
                return
            if self._bot.boxed_by_flax():
                return
            flax = self._bot.nearest_flax()
            if not flax:
                return
            target = flax.tile()
            self._bot.set_status(f'picking flax at {target}')
            before = flax_count()
            if not (flax.interact(PICK_OP)):
                yield from execution.delay_ticks(2)
                continue
            yield from execution.delay_until_ticks(lambda: flax_count() > before or inventory.is_full() or chat_dialog.can_continue() or event_signal.pending() or not self._bot.flax_still_at(target), 10)
            if not self._bot.flax_still_at(target):
                self._bot.clear_sticky_flax()


class WaitForFlax(Task):
    def __init__(self, bot):
        super().__init__()
        self._bot = bot

    def validate(self):
        if self._bot.get_mode() != 'Runner':
            return False
        if trade.active():
            return False
        if not self._bot.needs_flax():
            return False
        return self._bot.at_field() and self._bot.nearest_flax() is None

    def execute(self):
        here = game.tile()
        if here and FLAX_FIELD.distance_to(here) > FIELD_ARRIVE:
            self._bot.set_status('moving to field centre for respawns')
            yield from traversal.walk_resilient(FLAX_FIELD, radius=FIELD_ARRIVE, attempts=3, timeout_ms=60000, log=lambda m: self._bot.log(f'  {m}'))
            return
        self._bot.set_status('waiting for flax to respawn')
        self._bot.clear_sticky_flax()
        yield from execution.delay_ticks(2)


class GoToField(Task):
    def __init__(self, bot):
        super().__init__()
        self._bot = bot

    def validate(self):
        if self._bot.get_mode() != 'Runner':
            return False
        if trade.active():
            return False
        if not self._bot.needs_flax():
            return False
        return not self._bot.at_field()

    def execute(self):
        self._bot.set_status('travelling to the flax field')
        self._bot.clear_sticky_flax()
        yield from traversal.walk_resilient(FLAX_FIELD, radius=FIELD_ARRIVE, attempts=6, timeout_ms=240000, log=lambda m: self._bot.log(f'  {m}'))


# Spinner tasks.
class RequestTrade(Task):
    def __init__(self, bot):
        super().__init__()
        self._bot = bot

    def validate(self):
        if self._bot.get_mode() != 'Spinner':
            return False
        if trade.active():
            return False
        # Empty pack only, junk/strings must bank first or the runner's full
        # offer cannot land and both sides re-trade forever.
        if not self._bot.spinner_ready_for_handoff():
            return False
        if not self._bot.can_request_trade():
            return False
        return self._bot.at_meet()

    def execute(self):
        partner = self._bot.nearest_partner()
        if not partner or partner.distance() > TRADE_RANGE:
            self._bot.set_status('waiting for runner to arrive')
            yield from execution.delay_ticks(2)
            return
        # 2004 needs both players to click Trade; stagger spinner slightly so
        # both bots don't hammer request every loop (opens/closes thrash).
        self._bot.set_status('requesting trade from runner')
        self._bot.note_trade_request()
        trade.request(self._bot.get_partner())
        # Wall-clock: mutual Trade-with needs both players; tick waits shrink under speed 300.
        yield from execution.delay_until(lambda: trade.active() or event_signal.pending(), 5000)


class HandleTrade(Task):
    def __init__(self, bot):
        super().__init__()
        self._bot = bot
        self._pending = 0
        self._partner_wait = 0

    def validate(self):
        if self._bot.get_mode() != 'Spinner':
            return False
        return trade.active()

    def execute(self):
        # Stamp pending only when we are about to accept (product + room).
        if trade.on_offer_screen() and trade.partner() is not None:
            their_flax = flax_units_in_offer(trade.their_offer())
            if their_flax > 0 and can_receive_flax_offer(inventory.free(), their_flax):
                self._pending = their_flax
        def _fn12():
            self._partner_wait += 1
            if self._partner_wait > 8:
                self._partner_wait = 0
                return 'decline'
            return 'wait'

        def _fn13(their_flax):
            if can_receive_flax_offer(inventory.free(), their_flax):
                return True
            return (False, f'cannot take {their_flax} flax — only {inventory.free()} free slot(s) (random-event junk?). Declining and banking.')

        def _fn14():
            self._bot.note_trade_failed()
            self._pending = 0

        def _fn15(delta):
            # Prefer the live metric; pending is only a lag fallback while flax is held.
            live_gain = (delta if delta > 0 else 0)
            held = flax_count()
            gained = (live_gain if live_gain > 0 else (self._pending if held > 0 and self._pending > 0 else 0))
            if gained > 0:
                self._bot.log(f'received {gained} flax from runner')
                self._bot.note_trade_ok()
            else:
                self._bot.note_trade_failed()
                self._bot.log('trade closed without receiving flax — backing off before re-request')
            self._pending = 0
        yield from drive_active_partner_trade(
            'receiver', [self._bot.get_partner()], lambda n: FLAX.lower() in (n or '').lower(), lambda: [],
            self._bot.set_status, self._bot.log,
            inventory_metric=flax_count,
            on_missing_partner=_fn12,
            receiver_can_accept=_fn13,
            on_decline=_fn14,
            on_complete=_fn15,
            labels={
                'confirming': 'confirming trade',
                'wait_header': 'reading trade partner',
                'wait_offer': 'waiting for runner to offer flax',
                'accepting': 'accepting flax from runner',
                'declining': 'declining trade',
            })
        # rs2b0t's finally; a raise ends the bot here, so only the normal exit needs it.
        # Confirm timeout / external cancel never hits onDecline or onComplete.
        if not trade.active():
            self._pending = 0
            self._partner_wait = 0
        elif trade.partner() is not None:
            self._partner_wait = 0


class SpinFlax(Task):
    def __init__(self, bot):
        super().__init__()
        self._bot = bot
        self._spinning_until_tick = 0

    def validate(self):
        if self._bot.get_mode() != 'Spinner':
            return False
        if trade.active():
            return False
        if game.tick() < self._spinning_until_tick:
            return False
        if flax_count() == 0:
            return False
        return self._bot.is_on_floor(1)

    def execute(self):
        if game.animating() and not chat_dialog.is_make_menu():
            yield from self._ride()
            return
        if not chat_dialog.is_make_menu():
            wheel = locs.query().name(SPINNING_WHEEL).action(SPIN_OP).where(lambda l: l.tile().distance_to(SPINNING_WHEEL_AREA) <= LEASH).nearest()
            if not wheel:
                yield from execution.delay_ticks(2)
                return
            self._bot.set_status('opening the spinning wheel')
            if not (wheel.interact(SPIN_OP)):
                yield from execution.delay_ticks(2)
                return
            opened = yield from execution.delay_until_ticks(lambda: chat_dialog.is_make_menu() or chat_dialog.can_continue() or game.animating(), 10)
            if not opened:
                return
        if chat_dialog.is_make_menu():
            made = yield from chat_dialog.make_x(FLAX, flax_count())
            if not made:
                self._bot.log(f"Spin menu open but couldn't Make-X '{FLAX}' — products: [{', '.join(chat_dialog.make_products())}]")
                yield from execution.delay_ticks(2)
                return
        yield from self._ride()

    def _ride(self):
        self._bot.set_status('spinning')
        last = flax_count()
        idle = 0
        while flax_count() > 0:
            if chat_dialog.can_continue() or event_signal.pending() or not self._bot.is_on_floor(1):
                return
            yield from execution.delay_ticks(1)
            now = flax_count()
            if now < last:
                self._bot.count_spun(last - now)
                last = now
                idle = 0
            else:
                idle += 1
                if idle >= 6:
                    return


# Why: random-event garbage alone leaves the spinner at the meet with no free slots, so the runner's full flax offer never lands and both sides re-trade.
class BankStrings(Task):
    """Spinner pack clear before handoff and after spinning."""

    def __init__(self, bot):
        super().__init__()
        self._bot = bot

    def validate(self):
        if self._bot.get_mode() != 'Spinner':
            return False
        if trade.active():
            return False
        return self._bot.spinner_needs_bank()

    def execute(self):
        strings = bow_string_count()
        used = inventory.used()
        self._bot.set_status(('banking bow strings' if strings > 0 else 'banking junk before handoff'))
        self._bot.log(f'spinner banking pack ({used} slot(s) used, {strings} string(s), {flax_count()} flax) so the next trade can take a full flax load')
        walked = yield from traversal.walk_resilient(BANK_ENTRANCE, radius=3, attempts=4, timeout_ms=120000, log=lambda m: self._bot.log(f'  {m}'))
        if not walked:
            self._bot.log('could not reach the bank entrance — will retry')
            return
        opened = yield from bank.open_booth(BANK_STAND, BOOTH_NAME, BOOTH_OP)
        if not opened:
            self._bot.log('could not open the bank — will retry')
            return
        # Deposit everything, strings, leftover fibre, and random-event trash.
        yield from bank.deposit_inventory()
        yield from bank.close()
        if strings > 0:
            self._bot.count_trip()


class ClimbDown(Task):
    def __init__(self, bot):
        super().__init__()
        self._bot = bot

    def validate(self):
        if self._bot.get_mode() != 'Spinner':
            return False
        if trade.active():
            return False
        if not self._bot.is_on_floor(1):
            return False
        return flax_count() == 0

    def execute(self):
        self._bot.set_status('heading back down')
        yield from climb_ladder(LADDER_NAME, CLIMB_DOWN, lambda m: self._bot.log(f'  {m}'))


class ClimbUp(Task):
    def __init__(self, bot):
        super().__init__()
        self._bot = bot

    def validate(self):
        if self._bot.get_mode() != 'Spinner':
            return False
        if trade.active():
            return False
        if self._bot.is_on_floor(1):
            return False
        return flax_count() > 0

    def execute(self):
        self._bot.set_status('heading up to the wheel')
        ladder = locs.query().name(LADDER_NAME).action(CLIMB_UP).nearest()
        if not ladder or ladder.distance() > 1:
            yield from walk_opening(LADDER_TILE, 1, ['door'], lambda m: self._bot.log(m))
        yield from climb_ladder(LADDER_NAME, CLIMB_UP, lambda m: self._bot.log(f'  {m}'))


BOT = define_bot(
    name='FlaxRunner',
    create=FlaxRunner,
    description='Two-player cooperative flax picking and spinning — Runner picks flax and delivers to Spinner; Spinner spins flax into bow strings and banks them',
    category='Crafting',
    tags=['crafting', 'fletching', 'flax', 'bow-strings', 'trade', 'two-player', 'afk'],
    settings_schema=SETTINGS,
)
