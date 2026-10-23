# Walks to a tile and opens the nearest shut door or gate beside it every tick: rs2b0t's DoorOpener (MIT, see
# thirdparty/rs2b0t).

from rs2004.catalogs import ContinueDialog

DEFAULT_STAND = Tile(3215, 3212, 0)
DEFAULT_OBSTACLE = 'door, gate'

SETTINGS = {
    'stand': SettingDef('tile', DEFAULT_STAND, 'Stand tile (x,z)', help='walk here, then open the nearest adjacent shut door every tick'),
    'leash_radius': SettingDef('number', 8, 'Door search radius (tiles)', 1, 20),
    'obstacle': SettingDef('string', DEFAULT_OBSTACLE, 'Openable names (contains)', help='comma-separated name fragments, e.g. door, gate'),
}


def obstacle_list(raw):
    return [s.strip().lower() for s in raw.split(',') if s.strip()]


def name_matches(name, obstacle):
    # Why: a plain 'door' in the name matches Trapdoor, which is not a door.
    if obstacle == 'door':
        return name == 'door' or name.endswith(' door')
    return obstacle in name


def is_shut_door(name, ops, obstacles):
    n = (name or '').strip().lower()
    if not n or len([k for k in obstacles if name_matches(n, k)]) == 0:
        return False
    return len([o for o in ops if o is not None and o.lower().startswith('open')]) > 0


def nearest_shut_door(candidates, obstacles):
    """The nearest candidate that's still shut (it offers Open) and is named like one of the obstacles; each
    candidate has name, ops and distance."""
    best = None
    for candidate in candidates:
        if is_shut_door(candidate.name, candidate.ops, obstacles) and (best is None or candidate.distance < best.distance):
            best = candidate
    return best


class Candidate:
    def __init__(self, loc, stand):
        self.loc = loc
        self.name = loc.name
        self.ops = loc.actions()
        self.distance = loc.tile().distance_to(stand)


class OpenNearest(Task):
    def __init__(self, bot):
        Task.__init__(self, label='open nearest')
        self.bot = bot

    def validate(self):
        return True

    def execute(self):
        if event_signal.pending():
            return
        stand = self.bot.stand
        here = game.tile()
        if here is None or stand.distance_to(here) > 1:
            self.bot.status = 'walking to stand'
            yield from walk_opening(stand, 1, self.bot.obstacles, self.bot.log)
            return
        candidates = [Candidate(loc, stand) for loc in locs.query().within_of(stand, self.bot.leash).results()]
        pick = nearest_shut_door(candidates, self.bot.obstacles)
        if pick is None or pick.loc.tile().distance_to(here) > 1:
            self.bot.status = 'waiting for a shut door'
            return
        door = pick.loc
        dt = door.tile()
        op = open_op(door.actions())
        if op is None:
            return
        name = door.name or 'door'
        self.bot.log(f'opening {name} at {dt.x},{dt.z}')
        self.bot.status = f'opening {name} at {dt.x},{dt.z}'
        if not door.interact(op):
            self.bot.log(f'could not {op} {name}; retrying')
            return
        self.bot.opens += 1


class DoorOpener(TaskBot):
    loop_delay = 600

    def on_start(self):
        self.stand = self.settings.tile('stand', DEFAULT_STAND)
        self.leash = self.settings.num('leash_radius', 8)
        self.obstacles = obstacle_list(self.settings.str('obstacle', DEFAULT_OBSTACLE))
        self.opens = 0
        self.status = 'starting'
        if len(self.obstacles) == 0:
            self.request_finish('DoorOpener: obstacle names are empty')
            return
        self.log(f"DoorOpener at {self.stand}; nearest shut {'/'.join(self.obstacles)} within {self.leash}")
        self.add(ContinueDialog(), OpenNearest(self))

    def recovery_anchor(self):
        return self.stand

    def on_progress_report(self):
        return {'Status': self.status, 'Opens': self.opens, 'Stand': f'{self.stand.x},{self.stand.z}', 'Radius': self.leash}


BOT = define_bot(
    name='DoorOpener',
    create=DoorOpener,
    description='Walks to a chosen tile and opens the nearest shut door every tick',
    category='Navigation',
    tags=['door', 'gate', 'utility', 'afk'],
    settings_schema=SETTINGS,
)
