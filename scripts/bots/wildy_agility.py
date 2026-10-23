# Runs the Wilderness Agility Course, eating as it goes, and after a death banks for food and comes back:
# rs2b0t's WildyAgility (MIT, see thirdparty/rs2b0t). It needs Agility 52 for the ridge, and carried food.

import random
import time

from rs2004.catalogs import FOOD_OPTIONS, LOADOUT_SETTING, ContinueDialog, DeathRecovery, food_heal_amount, is_food_item, script_food, should_eat_to_use_food

COURSE_OBSTACLES = ['obstacle pipe', 'ropeswing', 'stepping stone', 'log balance', 'rocks']
COURSE_CENTRE = Tile(2998, 3945, 0)
RIDGE_DOOR = Tile(2998, 3917, 0)
RIDGE_APPROACH = Tile(2998, 3916, 0)
# Why: the course is gate-based, the same plane strictly north of the Gate within COURSE_X_RADIUS, not a square
# around its centre: that keeps the wolf pit and the ridge's approach out and the pit ladders' exits in. A tight
# radius of 16 read the ladder exits as away, and pathfound out through the Gate or the Door.
COURSE_X_RADIUS = 24
ENTRY_RADIUS = 10
SEARCH_RADIUS = 20
PIT_Z_GAP = 2000
RIDGE_MIN_AGILITY = 52
EDGEVILLE_BANK = Tile(3094, 3493, 0)
GATE_TILE = Tile(2998, 3931, 0)
RIDGE_NAME = 'Door'
RIDGE_OP = 'Open'
PIT_LADDER_OP = 'Climb-up'
OBSTACLE_START = {
    'obstacle pipe': Tile(3004, 3937, 0),
    'ropeswing': Tile(3005, 3952, 0),
    'stepping stone': Tile(3002, 3960, 0),
    'log balance': Tile(3002, 3945, 0),
    'rocks': Tile(2994, 3937, 0),
}
# Why: the default wait is 24 ticks, and clearing an obstacle can take about 20.
LAP_RETRY_LIMIT = 2
RIDGE_TIMEOUT_MS = 10000
BANK_TILE = EDGEVILLE_BANK

SETTINGS = {
    'loadout': LOADOUT_SETTING,
    'food': SettingDef('string', '', 'Food (overrides loadout)', options=FOOD_OPTIONS,
                       help="exact food to eat and withdraw; blank uses the loadout's food, or 'Lobster' if the loadout names none"),
    'food_withdraw': SettingDef('number', 20, 'Food to withdraw', 1, 28, help='how many to withdraw at startup restock and after death'),
    'min_food': SettingDef('number', 1, 'Bank below food count', 0, 28,
                           help='at script start (and after death), bank if carrying fewer than this many; 0 = skip the startup food check'),
    'acquire_food_at_start': SettingDef('boolean', True, 'Acquire food at start',
                                        help="if the inventory has no 'Food to withdraw' when the script starts (and you're not already on the course), withdraw from the bank before heading out; turn off to skip the startup bank trip even when empty"),
    'obstacle_timeout_ticks': SettingDef('number', 24, 'Obstacle timeout (ticks)', 5, 60,
                                         help='max ticks to wait for XP or a known-delaying event before treating as timeout'),
}


# The game's messages, as type-0 lines.

def course_wrong_side(text):
    t = text.lower()
    return t.startswith('you cannot do that from here') or t.startswith("you can't enter the pipe from this side") or t.startswith("you can' enter the pipe from this side")


def pit_fall(text):
    t = text.lower()
    return 'you slip and fall into the pit below' in t or 'you lose your footing and fall into the lava' in t or 'you slip and fall onto the spikes below' in t


def ridge_success(text):
    return 'you skillfully balance across the ridge' in text.lower()


def ridge_fail(text):
    return 'you lose your footing and fall into the wolf pit' in text.lower()


def is_death(text):
    t = text.lower()
    return 'oh dear' in t and 'you are dead' in t


# The pure decisions, kept apart from the game so they can be tested without a client.

def classify_ridge(xp_gained, success_message, fail_message, in_wolf_pit, interrupted):
    if interrupted:
        return 'interrupted'
    # A fail comes before a success, so a leftover success line can't hide a new fail; xp only comes with a real
    # balance, so it counts as a success.
    if fail_message or in_wolf_pit:
        return 'fail'
    if xp_gained or success_message:
        return 'success'
    return 'timeout'


def classify_obstacle(xp_gained, pit, cant_reach, wrong_side, pit_fall_message, interrupted, low_hp):
    """How a finished obstacle wait ended."""
    if xp_gained:
        return 'xp'
    if pit:
        return 'pit'
    if interrupted:
        return 'interrupted'
    if wrong_side:
        return 'wrong_side'
    if pit_fall_message:
        return 'pit_fall_msg'
    if cant_reach:
        return 'cant_reach'
    if low_hp:
        return 'low_hp'
    return 'timeout'


def get_start_tile(obstacle_name):
    return OBSTACLE_START.get(obstacle_name.lower())


def on_course(here):
    """The lap zone: strictly north of the inner Gate, on its plane, within a band either side. The wolf pit, the
    ridge's approach (z 3917 and below) and the corridor from the ridge to the Gate (to z 3931) are outside it."""
    return here.level == GATE_TILE.level and here.z > GATE_TILE.z and abs(here.x - GATE_TILE.x) <= COURSE_X_RADIUS


def near_course_entry(here):
    """The corridor from the ridge's approach to the Gate, by the path. TravelToCourse mustn't pull the player out
    of it; EnterCourse owns it."""
    if here.level != GATE_TILE.level or here.z > GATE_TILE.z or here.z < RIDGE_APPROACH.z - 2:
        return False
    return abs(here.x - GATE_TILE.x) <= ENTRY_RADIUS


def away_from_course(here):
    """Far from both the lap zone and the ridge's corridor, such as at the bank or the death spawn."""
    return not on_course(here) and not near_course_entry(here)


def in_pit(here):
    """In an obstacle's pit (the ropeswing, log balance or pipe), which the server moves to a scene far north. A
    fall into the ridge's wolf pit stays in the same scene, so this isn't for it."""
    return here.level == COURSE_CENTRE.level and here.z - COURSE_CENTRE.z > PIT_Z_GAP


def south_of_ridge(here):
    """On the ridge Door's south, outer side."""
    return here.level == RIDGE_DOOR.level and here.z <= RIDGE_APPROACH.z


def near_tile(here, dest, radius):
    return here.level == dest.level and max(abs(here.x - dest.x), abs(here.z - dest.z)) <= radius


def at_ridge_approach(here, radius=2):
    """Ready to click the ridge: by its south stand, not already north of the Door."""
    return near_tile(here, RIDGE_APPROACH, radius) and south_of_ridge(here)


def reaction_ms():
    """A human pause after clearing an obstacle; the character settles a tick before the next click, or the first
    try is wasted."""
    if random.random() < 0.1:
        return 1200 + random.random() * 1800
    return 600 + random.random() * 900


def now_ms():
    return time.time() * 1000


def food_count(bot):
    return len([i for i in inventory.items() if is_food_item(i.name, bot.food)])


def need_eat(bot):
    n = food_count(bot)
    if n <= 0:
        return False
    return should_eat_to_use_food(skills.effective('hitpoints'), skills.level('hitpoints'), food_heal_amount(bot.food), n)


def ensure_retaliate_off(log):
    """Auto retaliate off, so the skeletons nearby can't pull it off the course."""
    if game.auto_retaliate_on():
        log(f'Auto Retaliate turned off ({game.set_auto_retaliate(False)})')


def find_ridge():
    return locs.query().name(RIDGE_NAME).action(RIDGE_OP).where(lambda l: l.distance() <= SEARCH_RADIUS).nearest()


# Why: a walk to a tile north of the Door opens the Door on the way as a transport, which takes the ridge attempt
# away from the script.
def walk_to_ridge_approach(bot, label, attempts=4, timeout_ms=60000):
    """Walks to the ridge Door's south stand without pathing through it. Use with yield from."""
    here = game.tile()
    if here is not None and at_ridge_approach(here):
        return
    bot.status = f'{label}walking to ridge approach ({RIDGE_APPROACH.x},{RIDGE_APPROACH.z})'
    yield from traversal.walk_resilient(RIDGE_APPROACH, radius=1, attempts=attempts, timeout_ms=timeout_ms, log=lambda m: bot.log(f'  {m}'))


# Why: the result comes from the game's messages and xp: "You skillfully balance across the ridge..." for a
# success, and "You lose your footing and fall into the wolf pit." for a fail, in the same scene, not the far pit
# PitEscape handles. Only the ridge's interact may cross the Door, so the approach stays south of z 3917.
def attempt_ridge_crossing(bot, label):
    """Crosses the wilderness ridge into the course. Use with yield from."""
    yield from walk_to_ridge_approach(bot, label)
    ridge = find_ridge()
    if ridge is None:
        bot.status = f"{label}waiting: no '{RIDGE_NAME}' (ridge) within {SEARCH_RADIUS} tiles"
        yield from execution.delay_ticks(2)
        return 'timeout'
    # The mark comes before the click, so only this attempt's messages count.
    mark = game_messages.mark()
    before_xp = skills.xp('agility')
    bot.status = f'{label}crossing the ridge ({RIDGE_OP} {ridge.name} @ {ridge.tile().x},{ridge.tile().z})'
    if not ridge.interact(RIDGE_OP):
        yield from execution.delay_ticks(2)
        return 'timeout'
    # The wolf pit is in the same scene, so it settles on chat, xp or an interrupt, never the pit's z.
    yield from execution.delay_until(lambda: event_signal.pending() or skills.xp('agility') > before_xp or game_messages.saw_since(mark, ridge_success)
                                     or game_messages.saw_since(mark, ridge_fail), RIDGE_TIMEOUT_MS)
    saw_fail = game_messages.saw_since(mark, ridge_fail)
    outcome = classify_ridge(skills.xp('agility') > before_xp, game_messages.saw_since(mark, ridge_success), saw_fail, saw_fail, event_signal.pending())
    if outcome == 'success':
        bot.entered = True
        # The ridge's xp can come just after its line, so RunLap doesn't credit it to the first obstacle.
        bot.last_cleared_tick = game.tick()
        bot.log(f'{label}ridge crossed')
        return outcome
    if outcome == 'interrupted':
        bot.status = 'random event — handling'
        return outcome
    # A fail or a timeout goes back to the south stand, and the next loop tries again; never north of the Door,
    # which the pathfinder would open.
    bot.log(f'{label}fell into the wolf pit — walking back to ridge approach' if outcome == 'fail' else f'{label}ridge crossing timed out — walking back to ridge approach')
    yield from walk_to_ridge_approach(bot, label, 3, 30000)
    return outcome


class EatFood(Task):
    def __init__(self, bot):
        Task.__init__(self, label='eat food')
        self.bot = bot

    def validate(self):
        return need_eat(self.bot)

    def execute(self):
        bot = self.bot
        for _ in range(28):
            if bot.died or chat_dialog.can_continue() or event_signal.pending() or not need_eat(bot):
                return
            foods = [i for i in inventory.items() if is_food_item(i.name, bot.food)]
            if len(foods) == 0:
                return
            food = foods[0]
            bot.status = f'eating {food.name} ({round(skills.hp_fraction() * 100)}% hp)'
            before = skills.effective('hitpoints')
            if not food.interact('Eat'):
                return
            yield from execution.delay_until(lambda: skills.effective('hitpoints') > before or food_count(bot) == 0, 3000)
            if skills.effective('hitpoints') > before:
                bot.eats += 1


def climbs_up(a):
    t = a.lower()
    return 'climb-up' in t or 'climb up' in t


def climbs(a):
    t = a.lower()
    return 'climb' in t or 'ladder' in t


class PitEscape(Task):
    """Climbs out of an obstacle's far pit (the ropeswing, log balance or pipe). A fall into the ridge's wolf pit
    stays in the same scene and is attempt_ridge_crossing's."""

    def __init__(self, bot):
        Task.__init__(self, label='pit escape')
        self.bot = bot

    def find_ladder(self):
        # Climb-up first, so it doesn't keep climbing down into the pit.
        ladder = locs.query().where(lambda l: len([a for a in l.actions() if climbs_up(a)]) > 0).nearest()
        if ladder is None:
            ladder = locs.query().where(lambda l: len([a for a in l.actions() if climbs(a)]) > 0).nearest()
        return ladder

    # Death recovery owns the walk after a death; a pit escape from there would set off from Lumbridge toward a
    # ladder it can't reach. Only the pit's z counts, so the wolf pit stays out of this task.
    def validate(self):
        if self.bot.died:
            return False
        here = game.tile()
        return here is not None and in_pit(here)

    def execute(self):
        bot = self.bot
        if bot.died:
            return
        ladder = self.find_ladder()
        if ladder is None:
            near = locs.query().where(lambda l: len(l.actions()) > 0).nearest()
            bot.status = 'in the pit — no ladder found'
            found = f"{near.name} [{', '.join(near.actions())}]" if near is not None else 'none'
            bot.log(f'fell into the pit but found no climb/ladder loc — nearest interactable: {found}')
            yield from execution.delay_ticks(3)
            return
        ups = [a for a in ladder.actions() if climbs_up(a)]
        any_climb = [a for a in ladder.actions() if climbs(a)]
        op = ups[0] if len(ups) > 0 else (any_climb[0] if len(any_climb) > 0 else PIT_LADDER_OP)
        here = game.tile()
        lt = ladder.tile()
        if here is not None and not near_tile(here, lt, 2):
            bot.status = 'in the pit — heading to the ladder'
            # A short walk inside the pit, which needs no retries.
            yield from traversal.walk_to(lt, radius=1)
            if bot.died:
                return
        bot.status = f'climbing out of the pit ({op} {ladder.name})'
        bot.log(f'fell into the pit — {op} {ladder.name} back up to the course')
        if not ladder.interact(op):
            yield from execution.delay_ticks(2)
            return
        yield from execution.delay_until(lambda: game.tile() is not None and not in_pit(game.tile()), 10000)
        bot.mark_escaped_pit()


class TravelToCourse(Task):
    def __init__(self, bot):
        Task.__init__(self, label='travel to course')
        self.bot = bot

    def validate(self):
        here = game.tile()
        return here is not None and away_from_course(here)

    def execute(self):
        bot = self.bot
        bot.entered = False
        bot.status = 'walking to the wilderness agility course'
        # South of the ridge Door, never north of it, which the pathfinder opens.
        yield from traversal.walk_resilient(RIDGE_APPROACH, radius=2, attempts=6, timeout_ms=120000, log=lambda m: bot.log(f'  {m}'))


class EnterCourse(Task):
    def __init__(self, bot):
        Task.__init__(self, label='enter course')
        self.bot = bot

    # Never once north of the Gate: the gate leads back south, and clicking the ridge from inside derails the
    # script. In the approach's corridor it's south of the Door, which keeps it from going in again from the rocks.
    def validate(self):
        here = game.tile()
        if here is None or on_course(here):
            return False
        if not near_course_entry(here) and not at_ridge_approach(here, 4):
            return False
        return south_of_ridge(here)

    def execute(self):
        yield from attempt_ridge_crossing(self.bot, '')


class RunLap(Task):
    def __init__(self, bot):
        Task.__init__(self, label='run lap')
        self.bot = bot
        self.stuck = 0
        self.logged_out_of_food = False

    def find(self, name):
        return locs.query().where(lambda l: (l.name or '').lower() == name and l.distance() <= SEARCH_RADIUS and len(l.actions()) > 0).nearest()

    # Why: the lap zone is north of the Gate, and the entered flag covers the moment after the ridge. It stays on
    # after a pit climb too, so the walk to the next start happens even while the ladder's exit reads off the course.
    def validate(self):
        bot = self.bot
        here = game.tile()
        if here is None:
            return False
        if bot.just_escaped_pit:
            return True
        return bot.entered or on_course(here)

    def near_start(self, name, radius):
        start = get_start_tile(name)
        here = game.tile()
        return start is not None and here is not None and near_tile(here, start, radius)

    def walk_to_start_tile(self, name):
        """Use with yield from."""
        bot = self.bot
        start = get_start_tile(name)
        if start is None:
            bot.log(f"no starting side for '{name}' — retrying in place")
            bot.status = f'retrying {name}'
            yield from execution.delay_ticks(2)
            return False
        bot.status = f'walking to {name} starting side ({start.x},{start.z})'
        here = game.tile()
        if here is not None and near_tile(here, start, 1):
            bot.log(f"already near starting side for '{name}'")
            yield from execution.delay_ticks(1)
            return True
        # A bounded walk, so a bad path can't hang the lap with nothing logged.
        walked = yield from traversal.walk_to(start, radius=1, timeout_ms=45000)
        if not walked:
            bot.log(f"could not reach starting side for '{name}' — path unreachable")
        return walked

    def execute(self):
        bot = self.bot
        name = bot.current_name()
        # Food runs out mid-session, and only a death restocks: it keeps running, eating whenever it can.
        if food_count(bot) == 0:
            if not self.logged_out_of_food:
                self.logged_out_of_food = True
                bot.log(f"out of '{bot.food}' — continuing course until death (death recovery restocks)")
        else:
            self.logged_out_of_food = False
        # Why: the walk to the start comes before finding, clicking and timing the obstacle. A pit's ladder exit and
        # the lap's wrap (rocks to the pipe) are far from the next start, and counting that walk against the timeout
        # made false "no progress" retries.
        escaped_pit = bot.just_escaped_pit
        if escaped_pit:
            bot.just_escaped_pit = False
            bot.log(f"just escaped pit — walking to '{name}' starting side before clicking")
        if escaped_pit or not self.near_start(name, 2):
            # Why: an aborted wait can leave it on a tile it can't path from, so an obstacle it can click from here
            # is clicked rather than failing to walk to the start over and over.
            already_here = not escaped_pit and self.find(name) is not None
            if not already_here:
                bot.log(f"walking to '{name}' starting side")
                walked = yield from self.walk_to_start_tile(name)
                if bot.died or event_signal.pending() or chat_dialog.can_continue():
                    return
                # Still in a pit, after a failed climb or a new fall: PitEscape's.
                here = game.tile()
                if here is not None and in_pit(here):
                    return
                if not walked and not self.near_start(name, 2) and self.find(name) is None:
                    self.stuck += 1
                    if self.stuck >= LAP_RETRY_LIMIT:
                        bot.log(f"'{name}' start unreachable after {self.stuck} tries — moving on to the next obstacle")
                        self.stuck = 0
                        bot.advance()
                    else:
                        bot.log(f"could not reach '{name}' start — will retry ({self.stuck}/{LAP_RETRY_LIMIT})")
                        yield from execution.delay_ticks(2)
                    return
        obstacle = self.find(name)
        if obstacle is None:
            # The first obstacle in sight in the course's order, not the nearest, so death recovery by the entrance
            # doesn't jump to the rocks.
            for course_name in COURSE_OBSTACLES:
                if self.find(course_name) is not None and bot.resync_to(course_name):
                    obstacle = self.find(course_name)
                    self.stuck = 0
                    break
        if obstacle is None:
            bot.status = f'waiting: no {bot.current_name()} within {SEARCH_RADIUS} tiles'
            bot.log(f"waiting: no '{bot.current_name()}' within {SEARCH_RADIUS} tiles")
            yield from execution.delay_ticks(2)
            return
        actions = obstacle.actions()
        op = actions[0] if len(actions) > 0 else None
        if not op:
            bot.log(f"'{obstacle.name}' has no actions — retrying")
            yield from execution.delay_ticks(2)
            return
        # Only a note: the click never waits for a gap after a recovery walk.
        gap_ticks = game.tick() - bot.last_cleared_tick
        if not escaped_pit and gap_ticks > bot.obstacle_timeout_ticks * 2:
            bot.log(f'gap {gap_ticks} ticks since last obstacle')
        mark = game_messages.mark()
        before = skills.xp('agility')
        ot = obstacle.tile()
        bot.status = f'{op} {obstacle.name} at {ot.x},{ot.z}'
        bot.log(f"{op} '{bot.current_name()}' @ {ot.x},{ot.z}")
        if not obstacle.interact(op):
            bot.log(f"interact('{op}') on '{bot.current_name()}' failed — retrying")
            yield from execution.delay_ticks(2)
            return
        # Why: the timeout starts at the click. A hard wall-clock bound is needed too, since counting idle ticks
        # alone stalls forever while combat or pathing jitter keeps the player animating or moving.
        click_tick = game.tick()
        wait_deadline = now_ms() + bot.obstacle_timeout_ticks * 600 + 3000
        idle_ticks = 0
        waited_ticks = 0
        low_hp = False
        last_tile = game.tile()
        while idle_ticks < bot.obstacle_timeout_ticks and now_ms() < wait_deadline:
            t = game.tile()
            if (skills.xp('agility') > before or (t is not None and in_pit(t)) or game_messages.saw_since(mark, CANT_REACH)
                    or game_messages.saw_since(mark, course_wrong_side) or game_messages.saw_since(mark, pit_fall)
                    or event_signal.pending() or chat_dialog.can_continue()):
                break
            # Why: this gives way to EatFood while the skeletons by the rocks hit it, after a few ticks so stray damage
            # doesn't abort the click, and never with no food, since aborting mid-obstacle strands it on the log or pipe.
            if waited_ticks >= 3 and need_eat(bot):
                low_hp = True
                break
            yield from execution.delay_ticks(1)
            waited_ticks += 1
            # Idle time counts toward the timeout; the wall clock covers endless animating or moving.
            now = game.tile()
            moved = now is not None and last_tile is not None and (now.x != last_tile.x or now.z != last_tile.z or now.level != last_tile.level)
            if not game.animating() and not moved:
                idle_ticks += 1
            if now is not None:
                last_tile = now
        here_after = game.tile()
        reason = classify_obstacle(skills.xp('agility') > before, here_after is not None and in_pit(here_after), game_messages.saw_since(mark, CANT_REACH),
                                   game_messages.saw_since(mark, course_wrong_side), game_messages.saw_since(mark, pit_fall),
                                   event_signal.pending() or chat_dialog.can_continue(), low_hp)
        if reason == 'interrupted':
            bot.status = 'random event — handling'
            return
        if reason == 'pit':
            bot.log(f"fell into the pit during '{bot.current_name()}' — escaping")
            bot.status = 'in the pit — escaping'
            # A fall is an outcome, not a stuck click, so recovery doesn't inherit a half-spent retry count.
            self.stuck = 0
            return
        if reason == 'timeout':
            bot.status = f'timeout waiting for {obstacle.name} ({idle_ticks} idle / {waited_ticks} total ticks)'
            bot.log(f"'{bot.current_name()}' timed out after {waited_ticks} ticks ({idle_ticks} idle) — no xp/chat")
        if reason == 'xp':
            self.stuck = 0
            bot.cleared += 1
            elapsed = game.tick() - click_tick
            bot.log(f"cleared '{bot.current_name()}' in {elapsed} ticks")
            bot.obstacle_times.append(elapsed)
            if len(bot.obstacle_times) > 20:
                bot.obstacle_times.pop(0)
            bot.last_cleared_tick = game.tick()
            bot.advance()
            # A short human pause only: waiting on the animation hung the next lap when combat kept it animating.
            yield from execution.delay(int(reaction_ms()))
            return
        # Low HP gives way to EatFood without spending a retry: combat damage isn't the obstacle failing.
        if reason == 'low_hp':
            bot.log(f"yielding '{bot.current_name()}' for food ({round(skills.hp_fraction() * 100)}% hp, {food_count(bot)} left)")
            return
        if reason == 'wrong_side':
            bot.log(f"'{bot.current_name()}' wrong side error — walking to starting side")
            yield from self.walk_to_start_tile((obstacle.name or bot.current_name()).lower())
            return
        if reason == 'pit_fall_msg':
            bot.log(f"'{bot.current_name()}' fell (no pit) — retrying")
            self.stuck = 0
            yield from execution.delay_ticks(1)
            return
        # It doesn't web-walk at the obstacle: its tile is deliberately unpathable.
        if reason == 'cant_reach':
            bot.status = f'out of range for {obstacle.name} — retrying'
            bot.log(f"'{bot.current_name()}' can't reach — retrying")
        # The first time it retries in place, the second it walks back to the start, and past the limit it skips.
        self.stuck += 1
        if self.stuck > LAP_RETRY_LIMIT:
            skipped = bot.current_name()
            bot.log(f"'{skipped}' isn't completing from here after {self.stuck} tries — moving on to the next obstacle")
            self.stuck = 0
            bot.advance()
            # A skip that wrapped onto the same or the first obstacle walks to the first start, breaking a loop in
            # the wrong place, such as at the rocks.
            first = COURSE_OBSTACLES[0]
            if bot.current_name() == skipped or bot.current_name() == first:
                bot.log(f"obstacle skip wrapped lap — walking to '{first}' starting side")
                yield from self.walk_to_start_tile(first)
        elif self.stuck >= 2:
            bot.log(f"'{bot.current_name()}' no progress — walking back to starting side ({self.stuck}/{LAP_RETRY_LIMIT})")
            walked = yield from self.walk_to_start_tile((obstacle.name or bot.current_name()).lower())
            if not walked:
                bot.log(f"'{bot.current_name()}' starting side unreachable — advancing to next obstacle")
                self.stuck = 0
                bot.advance()
        else:
            bot.status = f'retrying {obstacle.name}'
            bot.log(f"'{bot.current_name()}' no progress — retrying ({self.stuck}/{LAP_RETRY_LIMIT})")
            yield from execution.delay_ticks(2)


class WildyAgility(TaskBot):
    def on_start(self):
        self.loop_delay = 600
        self.step = 0
        self.laps = 0
        self.cleared = 0
        self.eats = 0
        self.deaths = 0
        self.status = 'starting'
        self.died = False
        self.entered = False
        self.just_escaped_pit = False
        self.obstacle_times = []
        yield from execution.delay_until(lambda: game.ingame() and game.tile() is not None, 0)
        s = self.settings
        self.food = (s.str('food', '').strip() or script_food(s, 'Lobster')).lower()
        self.food_withdraw = s.num('food_withdraw', 20)
        self.min_food = s.num('min_food', 1)
        acquire_at_start = s.bool('acquire_food_at_start', True)
        self.obstacle_timeout_ticks = s.num('obstacle_timeout_ticks', 24)
        agility = skills.level('agility')
        if agility < RIDGE_MIN_AGILITY:
            self.log(f'WildyAgility needs Agility {RIDGE_MIN_AGILITY} to cross the ridge (have {agility}) — stopping.')
            raise RuntimeError(f'WildyAgility: Agility {RIDGE_MIN_AGILITY} required')
        self.started_at = time.time()
        self.xp_at_start = skills.xp('agility')
        self.last_cleared_tick = game.tick()
        here = game.tile()
        self.entered = on_course(here)
        self.on('chat_message', self.heard)
        ensure_retaliate_off(self.log)
        # Why: below min_food at the start it banks before walking to the wilderness, unless it's on the course or in
        # a pit already: only a death restocks mid-session, since there's no safe way out of the lap zone.
        starting = food_count(self)
        if (self.min_food > 0 and starting < self.min_food) or (acquire_at_start and starting == 0):
            if self.entered or in_pit(here):
                self.log(f"only {starting} '{self.food}' (min {self.min_food}) but already on course, continuing until death")
            else:
                # Why: with min_food 0 and acquiring at the start, the floor is 1. The retries wait on the bank
                # opening, not on food_count() < min_food, which is never true at 0 and would skip the bank.
                required = self.min_food if self.min_food > 0 else 1
                self.log(f"only {starting} '{self.food}' (min {self.min_food}), banking before heading to the course")
                opened = False
                for attempt in range(6):
                    opened = yield from self.bank_for_food('startup')
                    if opened:
                        break
                    self.log(f'startup bank open failed (attempt {attempt + 1}/6), retrying')
                    yield from execution.delay_ticks(2)
                if not opened or food_count(self) < required:
                    self.status = f"out of '{self.food}' in bank, stopped"
                    self.request_finish(f"only {food_count(self)} '{self.food}' after bank (need {required})")
                    return
        self.log(f"WildyAgility starting — lap [{' -> '.join(COURSE_OBSTACLES)}], food '{self.food}' x{food_count(self)} (min {self.min_food}, withdraw {self.food_withdraw}), bank {BANK_TILE.x},{BANK_TILE.z}, approach {RIDGE_APPROACH.x},{RIDGE_APPROACH.z}, timeout {self.obstacle_timeout_ticks} ticks")
        self.add(ContinueDialog(), DeathRecovery(self, RIDGE_APPROACH, 6, on_death=self.died_now, on_recovered=self.recovered, walk_back=self.recover_and_return),
                 EatFood(self), PitEscape(self), TravelToCourse(self), EnterCourse(self), RunLap(self))

    def heard(self, e):
        if is_death(e.text or ''):
            self.died = True

    def died_now(self):
        self.deaths += 1
        self.entered = False
        self.just_escaped_pit = False
        self.last_cleared_tick = game.tick()
        self.status = 'died — recovering'
        self.log('died in the wilderness — banking (food-only) and returning')
        ensure_retaliate_off(self.log)

    def recovered(self):
        self.died = False
        self.status = 'recovered — re-entering the course'

    def recovery_anchor(self):
        return RIDGE_APPROACH

    def recover_and_return(self):
        """Use with yield from."""
        banked = yield from self.bank_for_food('death')
        if not banked:
            return False
        self.status = 'recovering: returning to the ridge approach'
        # South of the Door, so the next EnterCourse's click owns the ridge.
        walked = yield from traversal.walk_resilient(RIDGE_APPROACH, radius=2, attempts=6, timeout_ms=120000, log=lambda m: self.log(f'  {m}'))
        return walked

    # Why: at the start when below min_food off the course, and after a death in the wilderness.
    def bank_for_food(self, reason):
        """Walks to Edgeville's bank, deposits the pack and withdraws food_withdraw of the food; False when the bank
        wouldn't open. Use with yield from."""
        self.status = f'{reason}: walking to the bank'
        yield from traversal.walk_resilient(BANK_TILE, radius=4, attempts=4, timeout_ms=120000, log=lambda m: self.log(f'  {m}'))
        opened = yield from bank.open_nearest('Bank booth', 'Use-quickly')
        if not opened:
            self.log('could not open the bank — will retry next loop')
            return False
        yield from bank.deposit_inventory()
        yield from execution.delay_ticks(1)
        yield from self.withdraw_food()
        self.log(f"{reason}: restocked {food_count(self)} '{self.food}'")
        return True

    def withdraw_food(self):
        """Use with yield from."""
        for _ in range(int(self.food_withdraw) * 2):
            if food_count(self) >= self.food_withdraw:
                return
            banked = [it for it in bank.items() if is_food_item(it.name, self.food)]
            if len(banked) == 0 or not banked[0].name:
                self.log(f"no '{self.food}' left in the bank")
                return
            before = food_count(self)
            if not bank.withdraw(banked[0].name, 'Withdraw-1'):
                return
            took = yield from execution.delay_until(lambda: food_count(self) > before, 2000)
            if not took:
                return

    def mark_escaped_pit(self):
        self.just_escaped_pit = True
        # The climb isn't idle time between obstacles, so the gap and timeout start from the recovery, not the fall.
        self.last_cleared_tick = game.tick()

    def current_name(self):
        return COURSE_OBSTACLES[self.step]

    def advance(self):
        self.step += 1
        if self.step >= len(COURSE_OBSTACLES):
            self.step = 0
            self.laps += 1
            self.log(f'lap {self.laps} complete')

    def resync_to(self, name):
        if name not in COURSE_OBSTACLES:
            return False
        idx = COURSE_OBSTACLES.index(name)
        self.log(f'lap re-sync: step {self.step} ({self.current_name()}) -> {idx} ({name})')
        self.step = idx
        return True

    def on_progress_report(self):
        avg = f'{sum(self.obstacle_times) / len(self.obstacle_times):.1f}' if len(self.obstacle_times) > 0 else '—'
        return {'Status': self.status, 'Laps': self.laps, 'Cleared': self.cleared, 'Agility xp': skills.xp('agility') - self.xp_at_start,
                'Food': food_count(self), 'Ate': self.eats, 'Deaths': self.deaths, 'Next': self.current_name(), 'Avg ticks': avg}


BOT = define_bot(
    name='WildyAgility',
    create=WildyAgility,
    description='Runs the Wilderness Agility Course, eats while running, and on death banks (food-only) then returns — needs Agility 52 + carried food (start at the entrance)',
    category='Agility',
    tags=['course', 'wilderness', 'food', 'death-recovery'],
    settings_schema=SETTINGS,
)
