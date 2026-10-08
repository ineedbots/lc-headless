# Walks a loop of tiles: the smallest useful script.
#
# Settings (optional):
#   points  [[x, z], ...] to visit in order           default a square from the start
#   size    the default square's side, in tiles        default 5
#   run     True to run between them                  default False
#   laps    log out after this many laps; 0 for never  default 0
#   teleport  a ::tele argument for staff accounts, used on start, e.g. "0,50,51,29,34"
#
# The server walks each step in a straight line and stops at the first obstacle, so keep the points
# in sight of each other.

points = []
index = 0
laps = 0


def on_start():
    global points
    start_x, start_z = get_x(), get_z()
    size = settings.get('size', 5)
    square = [[start_x + size, start_z], [start_x + size, start_z + size], [start_x, start_z + size], [start_x, start_z]]
    points = settings.get('points', square)
    log('Walking between', points)
    if settings.get('teleport'):
        command('tele ' + settings.teleport)


def on_reconnect():
    log('Reconnected at', get_x(), get_z(), 'after', laps, 'laps')


def loop():
    global index, laps
    x, z = points[index]
    if at(x, z):
        index = (index + 1) % len(points)
        if index == 0:
            laps += 1
            log('Lap', laps, 'done')
            if laps == settings.get('laps', 0):
                stop_account()
        return 0

    if not is_moving():
        walk_to(x, z, run=settings.get('run', False))

    return 600
