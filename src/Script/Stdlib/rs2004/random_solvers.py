"""The puzzles random events set: the mime's emotes, the strange box, the genie's lamp and the maze. Mirrors
rs2b0t's runtime/randomevents/solvers/ and maze/ (MIT, see third_party/rs2b0t). Each interface is found by
what it shows, and the maze is read from the cache's own map, not a table.
"""

import _core
from rs2004 import execution
from rs2004.dialogue import chat_dialog, modals
from rs2004.entities import local_tile, locs, npcs
from rs2004.geometry import Tile
from rs2004.interfaces import interfaces
from rs2004.items import inventory

__all__ = []

# The mime: copy each emote he performs, by the label of its button.

MIME_SQUARE = (31, 74)
# The mime's animation for each emote, and the label on the button that performs it.
MIME_EMOTES = {
    860: 'Cry',
    857: 'Think',
    861: 'Laugh',
    866: 'Dance',
    1130: 'Climb Rope',
    1129: 'Lean on air',
    1128: 'Glass Wall',
    1131: 'Glass Box',
}


def mime_answer(animation):
    """The label of the emote that copies the mime's animation, or None."""
    if animation is None:
        return None
    return MIME_EMOTES.get(animation)


def in_square(square):
    here = local_tile()
    return here.level == 0 and here.x // 64 == square[0] and here.z // 64 == square[1]


def _mime_buttons_open():
    chat = _core.get_chat_modal()
    if chat < 0:
        return False
    texts = _core.get_texts(chat)
    return 'Think' in texts and 'Glass Box' in texts


def perform_mime(log):
    """Copies the mime until the show is over. Use with yield from."""
    log('random event: mime, copying the performance')
    last = None
    deadline = _core.step_time() + 180000
    while in_square(MIME_SQUARE) and _core.step_time() < deadline:
        mime = npcs.query().name('Mime').nearest()
        if mime is not None and mime_answer(mime.animation) is not None:
            last = mime.animation
        if _mime_buttons_open():
            label = mime_answer(last)
            if label is not None:
                _core.click_text(label, _core.get_chat_modal())
                log(f'mime: performed {label}')
                last = None
                yield from execution.delay_until(lambda: not _mime_buttons_open() or not in_square(MIME_SQUARE), 10000)
                continue
        if chat_dialog.can_continue():
            yield from chat_dialog.continue_()
            continue
        yield from execution.delay_ticks(1)
    log('random event: mime, still on stage' if in_square(MIME_SQUARE) else 'random event: mime solved')
    return True


# The strange box: three parts, each a shape in a colour, and a question about one of them.

SHAPES = ['Triangle', 'Square', 'Circle', 'Star', 'Halfmoon']
COLOURS = ['Red', 'Blue', 'Yellow']
# The parts' item ids, red, blue and yellow of each shape in turn.
CUBE_PARTS = {}
for _shape in range(len(SHAPES)):
    for _colour in range(len(COLOURS)):
        CUBE_PARTS[3063 + 2 * (_shape * 3 + _colour)] = (SHAPES[_shape], COLOURS[_colour])


def _plain(text):
    return text.replace(' ', '').lower()


def solve_cube(question, parts):
    """The index of the part that answers the question, from the parts' item ids: "What colour is the Star?"
    is the star's place, and "Which shape is Blue?" the blue one's. None when it can't be told."""
    known = [CUBE_PARTS.get(part) if part is not None else None for part in parts]
    if None in known:
        return None
    lower = question.lower().strip()
    if lower.startswith('what colour is the ') and lower.endswith('?'):
        shape = _plain(lower[len('what colour is the '):-1])
        for i in range(len(known)):
            if _plain(known[i][0]) == shape:
                return i
        return None
    if lower.startswith('which shape is ') and lower.endswith('?'):
        colour = _plain(lower[len('which shape is '):-1])
        for i in range(len(known)):
            if _plain(known[i][1]) == colour:
                return i
    return None


def cube_label(question, parts, index):
    """The answer label to click: the part's colour for a colour question, else its shape."""
    shape, colour = CUBE_PARTS[parts[index]]
    return colour if question.lower().startswith('what colour') else shape


def _cube_screen():
    """(question, parts) when the strange box is open, else None."""
    main = _core.get_main_modal()
    if main < 0:
        return None
    components = _core.get_interface(main)
    parts = [c.item for c in components if c.type == 'model' and c.item is not None and c.item in CUBE_PARTS]
    questions = [c.text for c in components if c.type == 'text' and c.text.endswith('?')]
    if len(parts) != 3 or not questions:
        return None
    return (questions[0], parts)


def _close_bank_and_shop(log):
    if modals.is_open():
        log('random event: closing the open interface first')
        closed = yield from modals.close()
        return closed
    return True


def solve_all_boxes(log):
    """Opens and answers every strange box in the backpack. Use with yield from."""
    solved = 0
    for i in range(30):
        if not inventory.contains('Strange box'):
            break
        ready = yield from _close_bank_and_shop(log)
        if not ready:
            break
        box = inventory.first('Strange box')
        before = inventory.count('Strange box')
        box.interact('Open')
        opened = yield from execution.delay_until(lambda: _cube_screen() is not None, 5000)
        if not opened:
            log('random event: the strange box did not open')
            break
        question, parts = _cube_screen()
        answer = solve_cube(question, parts)
        if answer is None:
            log(f'random event: could not answer the strange box: {question} {parts}')
            yield from modals.close()
            break
        _core.click_text(cube_label(question, parts, answer), _core.get_main_modal())
        used = yield from execution.delay_until(lambda: inventory.count('Strange box') < before, 4000)
        if not used:
            log('random event: the strange box answer was not taken')
            break
        solved += 1
    log(f'random event: solved {solved} strange box' + ('' if solved == 1 else 'es'))
    return solved > 0


# The genie's lamp: choose a skill, then Confirm.

LAMP_SKILLS = [
    'attack', 'strength', 'ranged', 'magic', 'defence', 'hitpoints', 'prayer', 'agility', 'herblore', 'thieving',
    'crafting', 'runecraft', 'mining', 'smithing', 'fishing', 'cooking', 'firemaking', 'woodcutting', 'fletching',
]


def _lamp_button(skill):
    """The lamp interface's button for the skill: the one that sets its choice to the skill's place."""
    main = _core.get_main_modal()
    if main < 0 or 'Confirm' not in _core.get_texts(main):
        return None
    wanted = skill.lower()
    value = LAMP_SKILLS.index(wanted) + 1 if wanted in LAMP_SKILLS else 2
    for component in _core.get_interface(main):
        if component.button == 'ok' and component.value == value and component.varp is not None:
            return component.id
    return None


def rub_lamp(skill, log):
    """Rubs the lamp and spends it on the skill. Use with yield from."""
    if not inventory.contains('Lamp'):
        return False
    ready = yield from _close_bank_and_shop(log)
    if not ready:
        return False
    lamp = inventory.first('Lamp')
    lamp.interact('Rub')
    opened = yield from execution.delay_until(lambda: _lamp_button(skill) is not None, 5000)
    if not opened:
        log('random event: the lamp interface did not open')
        return False
    _core.click_component(_lamp_button(skill))
    yield from execution.delay_ticks(1)
    _core.click_text('Confirm', _core.get_main_modal())
    used = yield from execution.delay_until(lambda: not inventory.contains('Lamp'), 4000)
    log(f'random event: rubbed the lamp for {skill}' if used else 'random event: the lamp was not used')
    return True


# The maze: a route of doors to the shrine, read from the square's walls and doors in the cache.

MAZE_SQUARE = (45, 71)
MAZE_ORIGIN = (45 * 64, 71 * 64)
MAZE_SHRINE = (2911, 4575)
MAZE_SHRINE_SIZE = 3
MAZE_SHRINE_DOOR = (2910, 4576)
MAZE_SHRINE_LOC = 3634
WALL_ID = 3626
# Each door's direction: 0 opens from either side, 1 from the side its axis runs through, 2 from the other.
DOOR_DIRS = {3628: 0, 3629: 1, 3630: 2, 3631: 2, 3632: 1}
WALL_L_ANGLES = {0: [1, 0], 1: [1, 2], 2: [3, 2], 3: [3, 0]}
CARDINAL = [(1, 0), (-1, 0), (0, 1), (0, -1)]


def edge_key(ax, az, bx, bz):
    if ax < bx or az < bz:
        return (ax, az, bx, bz)
    return (bx, bz, ax, az)


def _straight_edge(x, z, angle):
    if angle == 0:
        return (x, z, x - 1, z)
    if angle == 1:
        return (x, z, x, z + 1)
    if angle == 2:
        return (x, z, x + 1, z)
    return (x, z, x, z - 1)


class MazeGraph:
    """The maze's walled edges and its doors, keyed by the edge each closes, with its bounds."""

    def __init__(self):
        self.walls = {}
        self.doors = {}
        self.min_x = None
        self.max_x = None
        self.min_z = None
        self.max_z = None


def build_maze(maze_locs, origin=None):
    """The graph from (lx, lz, id, shape, angle) locs in the square at origin, the maze's by default."""
    if origin is None:
        origin = MAZE_ORIGIN
    graph = MazeGraph()
    for lx, lz, id, shape, angle in maze_locs:
        x = origin[0] + lx
        z = origin[1] + lz
        if id == WALL_ID:
            graph.min_x = x if graph.min_x is None else min(graph.min_x, x)
            graph.max_x = x if graph.max_x is None else max(graph.max_x, x)
            graph.min_z = z if graph.min_z is None else min(graph.min_z, z)
            graph.max_z = z if graph.max_z is None else max(graph.max_z, z)
            if shape == 0:
                a, b, c, d = _straight_edge(x, z, angle)
                graph.walls[edge_key(a, b, c, d)] = True
            elif shape == 2:
                for side in WALL_L_ANGLES[angle]:
                    a, b, c, d = _straight_edge(x, z, side)
                    graph.walls[edge_key(a, b, c, d)] = True
        elif id in DOOR_DIRS:
            a, b, c, d = _straight_edge(x, z, angle)
            graph.doors[edge_key(a, b, c, d)] = {'x': x, 'z': z, 'id': id, 'angle': angle}
    return graph


def door_passable(door, from_x, from_z):
    """Whether the door opens from that side."""
    direction = DOOR_DIRS[door['id']]
    if direction == 0:
        return True
    on_axis = from_z == door['z'] if door['angle'] == 1 or door['angle'] == 3 else from_x == door['x']
    return on_axis if direction == 1 else not on_axis


def _in_shrine(x, z, shrine):
    return shrine[0] <= x and x < shrine[0] + MAZE_SHRINE_SIZE and shrine[1] <= z and z < shrine[1] + MAZE_SHRINE_SIZE


def _touch_stand(graph, x, z, shrine):
    """Outside the shrine and sharing an edge without a wall with it."""
    if _in_shrine(x, z, shrine):
        return False
    for dx, dz in CARDINAL:
        if _in_shrine(x + dx, z + dz, shrine) and edge_key(x, z, x + dx, z + dz) not in graph.walls:
            return True
    return False


def solve_maze_route(graph, spawn, shrine=None):
    """The doors, as (x, z), to open in turn from spawn to a tile beside the shrine, ending with the shrine's
    own door when the route comes in through it; empty when there's no route."""
    if shrine is None:
        shrine = MAZE_SHRINE
    if graph.min_x is not None:
        lo_x = graph.min_x - 2
        lo_z = graph.min_z - 2
        hi_x = graph.max_x + 2
        hi_z = graph.max_z + 2
    else:
        lo_x = min(spawn[0], shrine[0]) - 2
        lo_z = min(spawn[1], shrine[1]) - 2
        hi_x = max(spawn[0], shrine[0]) + 2
        hi_z = max(spawn[1], shrine[1]) + 2
    came = {spawn: None}
    queue = [spawn]
    head = 0
    while head < len(queue):
        x, z = queue[head]
        head += 1
        if _touch_stand(graph, x, z, shrine):
            doors = []
            node = came[(x, z)]
            while node is not None:
                px, pz, door = node
                if door is not None:
                    doors.insert(0, (door['x'], door['z']))
                node = came[(px, pz)]
            for dx, dz in CARDINAL:
                if not _in_shrine(x + dx, z + dz, shrine):
                    continue
                door = graph.doors.get(edge_key(x, z, x + dx, z + dz))
                if door is not None and (door['x'], door['z']) not in doors:
                    doors.append((door['x'], door['z']))
            return doors
        for dx, dz in CARDINAL:
            nx = x + dx
            nz = z + dz
            if nx < lo_x or nx > hi_x or nz < lo_z or nz > hi_z or _in_shrine(nx, nz, shrine) or (nx, nz) in came:
                continue
            key = edge_key(x, z, nx, nz)
            door = graph.doors.get(key)
            if door is not None:
                if not door_passable(door, x, z):
                    continue
            elif key in graph.walls:
                continue
            came[(nx, nz)] = (x, z, door)
            queue.append((nx, nz))
    return []


_maze = None


def maze_graph():
    global _maze
    if _maze is None:
        _maze = build_maze(_core.square_locs(MAZE_SQUARE[0], MAZE_SQUARE[1], 0))
    return _maze


def _walk_towards(target, onto):
    """Walks next to (or onto) the tile in the maze. True once there."""
    def there():
        here = local_tile()
        if onto:
            return here.x == target[0] and here.z == target[1]
        return max(abs(here.x - target[0]), abs(here.z - target[1])) <= 1

    still = 0
    for leg in range(40):
        if not in_square(MAZE_SQUARE):
            break
        if there():
            return True
        before = local_tile()
        _core.walk_to(target[0], target[1], False)
        moved = yield from execution.delay_until(lambda: local_tile() != before, 1500)
        if not moved:
            still += 1
            if still >= 3:
                return there()
            continue
        still = 0
        yield from execution.delay_until(lambda: there() or max(abs(local_tile().x - before.x), abs(local_tile().z - before.z)) >= 2, 4000)
    return there()


def _clear_messages():
    for i in range(6):
        if not chat_dialog.can_continue():
            break
        yield from chat_dialog.continue_()


def _open_maze_door(target, log):
    yield from _clear_messages()
    tx = target[0]
    tz = target[1]
    door = locs.query().where(lambda l: l.id in DOOR_DIRS and l.tile().x == tx and l.tile().z == tz).nearest()
    if door is None:
        log(f'random event: maze, the door at {target} is not in view')
        return
    before = local_tile()
    door.interact('Open')
    yield from execution.delay_until(lambda: chat_dialog.can_continue() or max(abs(local_tile().x - before.x), abs(local_tile().z - before.z)) >= 2, 3000)
    if chat_dialog.can_continue():
        yield from _clear_messages()


def solve_maze(log):
    """Opens the route's doors to the shrine and touches it. Use with yield from."""
    yield from _clear_messages()
    start = local_tile()
    doors = solve_maze_route(maze_graph(), (start.x, start.z))
    if not doors:
        log(f'random event: maze, no route from {start}')
        return True
    log(f'random event: maze, {len(doors)} doors from {start}')
    i = 0
    retries = 0
    while i < len(doors) and in_square(MAZE_SQUARE):
        reached = yield from _walk_towards(doors[i], False)
        if reached:
            yield from _open_maze_door(doors[i], log)
            i += 1
            retries = 0
            continue
        if i == 0 or retries >= 3:
            log(f'random event: maze, door {i} at {doors[i]} is walled off; starting over')
            return True
        retries += 1
        back = yield from _walk_towards(doors[i - 1], False)
        if back:
            yield from _open_maze_door(doors[i - 1], log)
    if in_square(MAZE_SQUARE) and (not doors or doors[-1] != MAZE_SHRINE_DOOR):
        yield from _walk_towards(MAZE_SHRINE_DOOR, False)
        yield from _open_maze_door(MAZE_SHRINE_DOOR, log)
    for attempt in range(6):
        if not in_square(MAZE_SQUARE):
            break
        yield from _clear_messages()
        shrine = locs.query().id(MAZE_SHRINE_LOC).within(8).nearest()
        if shrine is None:
            yield from execution.delay_ticks(3)
            continue
        actions = shrine.actions()
        op = actions[0] if actions else 'Touch'
        for action in actions:
            if 'touch' in action.lower():
                op = action
        yield from execution.delay_ticks(1)
        shrine.interact(op)
        left = yield from execution.delay_until(lambda: not in_square(MAZE_SQUARE), 12000)
        if left:
            break
    log('random event: maze, still inside' if in_square(MAZE_SQUARE) else 'random event: maze solved')
    return True
