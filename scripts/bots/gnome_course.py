# Walks to and runs the Gnome Stronghold agility course, or any course whose obstacles you list: rs2b0t's
# AgilityBot, registered as GnomeCourse (MIT, see thirdparty/rs2b0t).

from rs2004.catalogs import ContinueDialog

GNOME_COURSE_START = Tile(2474, 3436, 0)
GNOME_COURSE_RADIUS = 20
STUCK_LIMIT = 6


def at_gnome_course(here, start=None, radius=None):
    """Within the course's footprint, which spans the ground and the obstacles above it."""
    start = start if start is not None else GNOME_COURSE_START
    radius = radius if radius is not None else GNOME_COURSE_RADIUS
    return max(abs(here.x - start.x), abs(here.z - start.z)) <= radius


SETTINGS = {
    'obstacles': SettingDef('string', 'Log balance,Obstacle net,Tree branch,Balancing rope,Tree branch,Obstacle net,Obstacle pipe', 'Obstacles (lap order)',
                            help='comma-separated obstacle loc names in lap order, repeats allowed; each step uses the nearest loc with that name and advances when agility xp is awarded'),
    'search_radius': SettingDef('number', 20, 'Obstacle search radius (tiles)', 4, 64),
}


class TravelToCourse(Task):
    def __init__(self, bot):
        Task.__init__(self, label='Travel to course')
        self.bot = bot

    def validate(self):
        here = game.tile()
        return here is not None and not at_gnome_course(here)

    def execute(self):
        self.bot.status = 'walking to the Gnome Stronghold agility course'
        self.bot.log(f'web-walking to the course start {GNOME_COURSE_START}')
        yield from traversal.walk_resilient(GNOME_COURSE_START, radius=2, attempts=6, timeout_ms=240000, log=lambda m: self.bot.log(f'  {m}'))


class DoObstacle(Task):
    def __init__(self, bot):
        Task.__init__(self, label='Do obstacle')
        self.bot = bot
        self.stuck = 0

    def find(self, name):
        within = self.bot.radius
        return locs.query().where(lambda l: l.name is not None and l.name.lower() == name and l.distance() <= within and len(l.actions()) > 0).nearest()

    def validate(self):
        return True

    def reposition_for_retry(self, obstacle):
        t = obstacle.tile()
        me = game.tile()
        faces = [Tile(t.x, t.z - 1, t.level), Tile(t.x, t.z + 1, t.level), Tile(t.x - 1, t.z, t.level), Tile(t.x + 1, t.z, t.level)]
        usable = [f for f in faces if not (me is not None and me.x == f.x and me.z == f.z) and reachability.walkable(f) and reachability.can_reach(f)]
        if len(usable) == 0:
            return
        dest = usable[(self.stuck - 1) % len(usable)]
        self.bot.log(f"no xp from '{obstacle.name}'; repositioning to its ({dest.x},{dest.z}) face and retrying")
        self.bot.status = 'repositioning at the obstacle'
        yield from direct_navigator.walk_to(dest, 0, 10000)

    def execute(self):
        bot = self.bot
        obstacle = self.find(bot.current_name())
        if obstacle is None:
            seen = []
            for name in bot.course:
                if name in seen:
                    continue
                seen.append(name)
                if self.find(name) is not None and bot.resync_to(name):
                    obstacle = self.find(name)
                    break
        if obstacle is None:
            bot.status = f'waiting: no {bot.current_name()} within {bot.radius} tiles'
            yield from execution.delay_ticks(2)
            return

        actions = obstacle.actions()
        op = actions[0] if len(actions) > 0 else None
        if not op:
            return

        before = skills.xp('agility')
        bot.status = f'{op} {obstacle.name} at {obstacle.tile()}'
        clicked = obstacle.interact(op)
        cleared = False
        if clicked:
            cleared = yield from execution.delay_until(lambda: skills.xp('agility') > before or event_signal.pending(), 15000)
        else:
            yield from execution.delay_ticks(2)

        if event_signal.pending():
            bot.status = 'random event; handling'
            return

        last = game.tile()
        for _ in range(25):
            yield from execution.delay_ticks(1)
            if chat_dialog.can_continue():
                break
            now = game.tile()
            if now is not None and last is not None and now.x == last.x and now.z == last.z and not game.animating():
                break
            last = now

        if cleared:
            self.stuck = 0
            bot.obstacles_cleared += 1
            bot.advance()
        else:
            self.stuck += 1
            if self.stuck >= STUCK_LIMIT:
                bot.log(f"step '{bot.current_name()}' gave no xp after {self.stuck} attempts; skipping")
                self.stuck = 0
                bot.advance()
            else:
                yield from self.reposition_for_retry(obstacle)


class AgilityBot(TaskBot):
    loop_delay = 600

    def on_start(self):
        self.course = [s.strip().lower() for s in self.settings.str('obstacles', '').split(',') if s.strip()]
        self.radius = self.settings.num('search_radius', 20)
        self.step = 0
        self.laps = 0
        self.obstacles_cleared = 0
        self.status = 'starting'
        self.xp_at_start = skills.xp('agility')
        self.log(f"running agility course: [{' -> '.join(self.course)}] within {self.radius} tiles")
        self.add(ContinueDialog(), TravelToCourse(self), DoObstacle(self))

    def current_name(self):
        return self.course[self.step] if self.step < len(self.course) else None

    def advance(self):
        self.step += 1
        if self.step >= len(self.course):
            self.step = 0
            self.laps += 1
            self.log(f'lap {self.laps} complete')

    def resync_to(self, name):
        if name not in self.course:
            return False
        index = self.course.index(name)
        self.log(f'course re-sync: step {self.step} ({self.current_name()}) -> {index} ({name})')
        self.step = index
        return True

    def on_progress_report(self):
        return {'Status': self.status, 'Laps': self.laps, 'Obstacles': self.obstacles_cleared,
                'Agility xp': skills.xp('agility') - self.xp_at_start, 'Step': self.current_name() or '-'}


BOT = define_bot(
    name='GnomeCourse',
    create=AgilityBot,
    description='Travels to and runs the Gnome Stronghold agility course',
    category='Agility',
    tags=['course', 'gnome'],
    settings_schema=SETTINGS,
)
