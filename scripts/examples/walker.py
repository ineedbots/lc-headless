# Walks a loop of tiles: the smallest useful script. Without BOT = define_bot(...), its module-level
# loop() and on_* functions run as a LoopingBot, and without a settings schema its settings aren't checked.
#
# Settings (optional):
#   points  [[x, z], ...] to visit in order           default a square from the start
#   size    the default square's side, in tiles        default 5
#   run     True to run between them                  default False
#   laps    log out after this many laps; 0 for never  default 0
#   teleport  a ::tele argument for staff accounts, used on start, e.g. "0,50,51,29,34"
#   partner   the username of another account in this process, told about each lap
#
# Console commands: "laps [n]" tells the laps done, or sets how many to walk before logging out. Every
# script also has "pause" and "resume", which call on_pause and on_resume; with several accounts,
# "@<account> pause" pauses just one.
#
# The server walks each step in a straight line and stops at the first obstacle, so keep the points
# in sight of each other.

points = []
index = 0
laps = 0
lap_limit = settings.get('laps', 0)


def set_laps(command):
    global lap_limit
    if command.args:
        # An exception in a handler stops the script, so a typo is only logged.
        try:
            lap_limit = int(command.args[0])
        except ValueError:
            log('laps takes a number, not', command.args[0])
            return
    if lap_limit > 0:
        log(laps, 'laps done; logging out after', lap_limit)
    else:
        log(laps, 'laps done, with no limit')


console.command('laps', set_laps, 'Tells the laps done; "laps 3" logs out after 3, "laps 0" never')


def on_start():
    global points
    start = game.tile()
    start_x, start_z = start.x, start.z
    size = settings.get('size', 5)
    square = [[start_x + size, start_z], [start_x + size, start_z + size], [start_x, start_z + size], [start_x, start_z]]
    points = settings.get('points', square)
    log('Walking between', points)
    if settings.get('teleport'):
        chat.command('tele ' + settings.teleport)


def on_pause():
    log('Paused after', laps, 'laps')


def on_reconnect():
    log('Reconnected at', game.tile(), 'after', laps, 'laps')


def on_progress_report():
    return {'Laps': laps, 'Position': game.tile()}


def on_bot_message(sender, message):
    log(sender, 'finished lap', message['lap'])


def loop():
    global index, laps
    x, z = points[index]
    if game.tile().distance_to((x, z)) == 0:
        index = (index + 1) % len(points)
        if index == 0:
            laps += 1
            log('Lap', laps, 'done')
            if settings.get('partner'):
                send_bot_message(settings.partner, {'lap': laps})
            if lap_limit > 0 and laps >= lap_limit:
                stop_account()
        return 0

    if not game.moving():
        direct_navigator.walk((x, z), run=settings.get('run', False))

    # 600 means the next server tick, as rs2b0t reads it; any other number is milliseconds.
    return 600
