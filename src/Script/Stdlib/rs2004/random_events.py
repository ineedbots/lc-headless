"""Random events: telling one has come for you, and answering it. Mirrors rs2b0t's
runtime/RandomEventGuardian.ts, randomevents/RandomEvents.ts and eventEvade.ts (MIT, see thirdparty/rs2b0t).

The host asks the guardian once a server tick. When an event needs answering, the bot's step in progress is
dropped, the guardian's solver runs to the end, and loop() starts afresh. A bot can leave events alone with
ignored_randoms(), leave its own fight alone with grind_targets(), and choose the lamp's skill with
lamp_skill().
"""

import _core
from rs2004 import execution
from rs2004 import random_solvers as solvers
from rs2004.dialogue import chat_dialog
from rs2004.entities import ground_items, local_tile, locs, npcs
from rs2004.game import direct_navigator, game
from rs2004.geometry import Tile
from rs2004.items import equipment, inventory

__all__ = ['random_events']

DIALOG_EVENT_NPCS = ['genie', 'drunken dwarf', 'mysterious old man', 'sandwich lady', 'frog']
PICK_EVENT_NPCS = ['strange plant']
# The strange plant spawns beside whoever it's for and never moves.
PLANT_REACH = 3
DIALOG_REACH = 6
HOSTILE_EVENT_NPC_IDS = list(range(391, 397)) + [408, 411] + list(range(413, 437)) + list(range(438, 444))
HOSTILE_ENGAGE_DISTANCE = 8
# An event monster chases until you're past its maxrange of 15 from where it spawned, beside you; rs2b0t's 12
# leaves it chasing.
EVADE_DISTANCE = 20
ENT_NPC_IDS = list(range(444, 453))
ENT_LIFE_MS = 60 * 600
GAS_CHEST_LOC_ID = 2141
SMOKING_ROCK_IDS = list(range(2119, 2139))
WHIRLPOOL_NPC_IDS = [403, 404, 405, 406]
HAZARD_STEP = 4
FISHING_GEAR = ['small fishing net', 'big fishing net', 'fishing rod', 'oily fishing rod', 'fly fishing rod', 'harpoon', 'lobster pot']
GEAR_LOSS_WINDOW_MS = 90000
GEAR_RECOVERY_RANGE = 10
MAX_ATTEMPTS = 4
GIVE_UP_COOLDOWN_MS = 45000
PICK_WAIT_MS = 80000
# The maze and the mime hold you; a box or a lamp can't be dropped. These are retried rather than given up on.
TRAPPED_KINDS = ['maze', 'mime', 'box', 'lamp']
COMPASS = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]
MIN_FLEE_DIST = 4
RING_STEP = 2


def _chebyshev(ax, az, bx, bz):
    return max(abs(ax - bx), abs(az - bz))


def step_off_candidates(here, away):
    """The tiles beside here, furthest from away first."""
    tiles = [Tile(here.x + dx, here.z + dz, here.level) for dx, dz in COMPASS]
    tiles.sort(key=lambda t: -_chebyshev(t.x, t.z, away.x, away.z))
    return tiles


def flee_candidates(here, threat, dist):
    """Tiles in rings round here, out to dist and in to 4, furthest from the threat first."""
    seen = []
    tiles = []
    d = dist
    while d >= MIN_FLEE_DIST:
        for dx, dz in COMPASS:
            key = (here.x + dx * d, here.z + dz * d)
            if key in seen:
                continue
            seen.append(key)
            tiles.append(Tile(key[0], key[1], here.level))
        d -= RING_STEP
    tiles.sort(key=lambda t: -_chebyshev(t.x, t.z, threat.x, threat.z))
    return tiles


def plant_strategy(actions):
    """'pick' while the plant's fruit can be taken, 'evade' once it can only be attacked."""
    lowered = [a.lower() for a in actions if a is not None]
    can_pick = len([a for a in lowered if 'pick' in a or 'take' in a]) > 0
    can_attack = len([a for a in lowered if 'attack' in a]) > 0
    return 'evade' if not can_pick and can_attack else 'pick'


def targets_another_player(npc, pid):
    """An event NPC following someone else, whose Talk-to would only say it's busy."""
    target = npc.target
    return pid >= 0 and target is not None and target[0] == 'player' and target[1] != pid


PROTECTED_WORDS = ['handle', 'axe', 'pick', 'hammer', 'chisel', 'knife', 'tinderbox', 'rod', 'net', 'harpoon']


def pick_sacrificial(names):
    """The item to drop to make room: the most numerous one that isn't a tool."""
    counts = {}
    for name in names:
        if not name:
            continue
        lower = name.lower()
        protected = lower.endswith('head') or len([w for w in PROTECTED_WORDS if w in lower]) > 0
        if not protected:
            counts[name] = counts.get(name, 0) + 1
    best = None
    best_count = 0
    for name, count in counts.items():
        if count > best_count:
            best = name
            best_count = count
    return best


def _is_handle(name):
    lower = (name or '').lower()
    return lower.endswith('axe handle') or lower.endswith('pickaxe handle')


def handle_location(inventory_names, worn_names):
    """Where a tool's bare handle is, after its head flew off: 'worn', 'inventory' or None."""
    if len([n for n in worn_names if _is_handle(n)]) > 0:
        return 'worn'
    if len([n for n in inventory_names if _is_handle(n)]) > 0:
        return 'inventory'
    return None


def is_hostile_event(npc_id, distance, damaged):
    """A hostile event monster near you that has really hit you."""
    return damaged and npc_id in HOSTILE_EVENT_NPC_IDS and distance <= HOSTILE_ENGAGE_DISTANCE


def is_ent_hijack(npc_id, npc_index, distance, my_target, animating):
    """The ent you're chopping: beside you, faced and being chopped."""
    if npc_id not in ENT_NPC_IDS or distance > 1 or not animating:
        return False
    return my_target is not None and my_target[0] == 'npc' and my_target[1] == npc_index


class GearLossTracker:
    """Notices fishing gear that left the backpack while fishing, as the big fish's knock takes it."""

    def __init__(self, window_ms=90000):
        self.window_ms = window_ms
        self.held = []
        self.lost = {}
        self.was_suppressed = False
        self.last_fishing_tick = -1000000
        self.can_recover = False

    def update(self, held_now, suppressed_now, now_ms, fishing_nearby, tick):
        if fishing_nearby:
            self.last_fishing_tick = tick
        self.can_recover = tick >= self.last_fishing_tick and tick - self.last_fishing_tick <= 1 and not suppressed_now and not self.was_suppressed
        now = [name.lower() for name in held_now if name is not None and name.lower() in FISHING_GEAR]
        for gear in now:
            if gear in self.lost:
                del self.lost[gear]
        if self.can_recover:
            for gear in self.held:
                if gear not in now:
                    self.lost[gear] = now_ms
        self.held = now
        self.was_suppressed = suppressed_now

    def recently_lost(self, gear, now_ms):
        at = self.lost.get(gear.lower())
        return self.can_recover and at is not None and now_ms - at <= self.window_ms


class Event:
    """kind, name and, for a hazard, the tile it's on."""

    def __init__(self, kind, name, tile=None):
        self.kind = kind
        self.name = name
        self.tile = tile

    def key(self):
        return f'{self.kind}:{self.name}'

    def __repr__(self):
        return f'Event({repr(self.kind)}, {repr(self.name)})'


class _RandomEvents:
    """The guardian. detect() says which event needs answering, if any; handle(event) answers it."""

    def __init__(self):
        self.gear_loss = GearLossTracker()
        self.attempts = {}
        self.cooldown_until = {}
        self.handling = False
        self.ignored = []
        self.grind_targets = []
        self.lamp_skill = 'strength'
        self._last_tick = -1

    def configure(self, bot):
        """Reads the bot's choices: ignored_randoms(), grind_targets() and lamp_skill()."""
        self.ignored = [name.lower() for name in bot.ignored_randoms()]
        self.grind_targets = [name.lower() for name in bot.grind_targets()]
        self.lamp_skill = bot.lamp_skill()

    def _cooled_down(self, key):
        until = self.cooldown_until.get(key)
        return until is not None and _core.step_time() < until

    def detect(self):
        """The event that needs answering, or None. An ignored one, or one given up on a while ago, isn't."""
        try:
            event = self._detect_raw()
        except Exception:
            return None
        if event is None or event.name in self.ignored or self._cooled_down(event.key()):
            return None
        return event

    def check(self, bot):
        """Once a server tick: the event to take over for, or None."""
        if self.handling or not _core.is_placed():
            return None
        tick = _core.tick()
        if tick == self._last_tick:
            return None
        self._last_tick = tick
        self.configure(bot)
        return self.detect()

    def _detect_raw(self):
        if solvers.in_square(solvers.MIME_SQUARE):
            return Event('mime', 'mime')
        if solvers.in_square(solvers.MAZE_SQUARE):
            return Event('maze', 'maze')
        scene = self._detect_scene()
        if scene is not None:
            return scene
        if handle_location([i.name for i in inventory.items()], [i.name for i in equipment.items()]) is not None:
            return Event('lost-tool', 'lost tool')
        if inventory.contains('Strange box'):
            return Event('box', 'strange box')
        if inventory.contains('Lamp'):
            return Event('lamp', 'lamp')
        return None

    def _detect_scene(self):
        near = npcs.query().within(12).results()
        held = [i.name for i in inventory.items() if i.name is not None]
        fishing = len([n for n in near if n.distance() <= GEAR_RECOVERY_RANGE and ((n.name or '').lower() == 'fishing spot' or n.id in WHIRLPOOL_NPC_IDS)]) > 0
        self.gear_loss.update(held, _core.get_main_modal() != -1, _core.step_time(), fishing, _core.tick())

        pid = _core.get_pid()
        for npc in near:
            name = (npc.name or '').lower()
            if name in DIALOG_EVENT_NPCS and npc.distance() <= DIALOG_REACH and not targets_another_player(npc, pid):
                return Event('dialog', name)
            if name in PICK_EVENT_NPCS and npc.distance() <= PLANT_REACH and plant_strategy(npc.actions()) == 'pick':
                return Event('pick', name)

        damaged = _core.took_damage(4)
        for npc in near:
            if (npc.name or '').lower() in self.grind_targets:
                continue
            if is_hostile_event(npc.id, npc.distance(), damaged):
                return Event('evade', (npc.name or 'event monster').lower())

        me = _core.get_local_player()
        animating = me.animation != -1
        for npc in near:
            if is_ent_hijack(npc.id, npc.index, npc.distance(), me.target, animating):
                return Event('hijack', 'ent')

        gas = locs.query().id(GAS_CHEST_LOC_ID).within(1).nearest()
        if gas is not None:
            return Event('hazard', 'poisonous gas', gas.tile())
        rock = locs.query().id(SMOKING_ROCK_IDS).within(2).nearest()
        if rock is not None:
            return Event('hazard', 'smoking rock', rock.tile())
        for npc in near:
            if npc.id in WHIRLPOOL_NPC_IDS and npc.distance() <= 3:
                return Event('hazard', 'whirlpool', npc.tile())

        for gear in FISHING_GEAR:
            if not self.gear_loss.recently_lost(gear, _core.step_time()) or inventory.contains(gear):
                continue
            if ground_items.query().where(lambda g: (g.name or '').lower() == gear).within(GEAR_RECOVERY_RANGE).nearest() is not None:
                return Event('lost-gear', gear)
        return None

    def handle(self, event, log=None):
        """Answers the event. Use with yield from; it never raises into the bot."""
        say = log if log is not None else (lambda message: _core_log(message))
        self.handling = True
        try:
            acted = yield from self._handle(event, say)
        except Exception as e:
            self.handling = False
            raise e
        self.handling = False
        return acted

    def _handle(self, event, say):
        key = event.key()
        n = self.attempts.get(key, 0) + 1
        self.attempts[key] = n
        if n > MAX_ATTEMPTS:
            if event.kind in TRAPPED_KINDS:
                say(f'random event: {event.name}, attempt {n}; still here, so trying again')
            else:
                del self.attempts[key]
                self.cooldown_until[key] = _core.step_time() + GIVE_UP_COOLDOWN_MS
                say(f'random event: gave up on {event.name} after {MAX_ATTEMPTS} attempts; ignoring it for {GIVE_UP_COOLDOWN_MS // 1000}s')
                return False
        acted = False
        if event.kind == 'dialog':
            acted = yield from self._dialog(event.name, say)
        elif event.kind == 'pick':
            acted = yield from self._pick(event.name, say)
        elif event.kind == 'evade':
            acted = yield from self._evade(event.name, say)
        elif event.kind == 'hazard':
            acted = yield from self._hazard(event.name, event.tile, say)
        elif event.kind == 'hijack':
            acted = yield from self._hijack(say)
        elif event.kind == 'mime':
            acted = yield from solvers.perform_mime(say)
        elif event.kind == 'maze':
            acted = yield from solvers.solve_maze(say)
        elif event.kind == 'lost-tool':
            acted = yield from self._lost_tool(say)
        elif event.kind == 'lost-gear':
            acted = yield from self._lost_gear(event.name, say)
        elif event.kind == 'box':
            acted = yield from solvers.solve_all_boxes(say)
        elif event.kind == 'lamp':
            acted = yield from solvers.rub_lamp(self.lamp_skill, say)
        after = None
        try:
            after = self._detect_raw()
        except Exception:
            after = None
        if after is None or after.key() != key:
            if key in self.attempts:
                del self.attempts[key]
        return acted

    def _named(self, name):
        return npcs.query().where(lambda n: (n.name or '').lower() == name).nearest()

    def _dialog(self, name, say):
        say(f'random event: {name}, talking it through')
        npc = self._named(name)
        if npc is None:
            return False
        npc.interact('Talk-to')
        yield from execution.delay_until(lambda: chat_dialog.is_open(), 5000)
        for i in range(25):
            if not chat_dialog.is_open():
                break
            if chat_dialog.options():
                yield from chat_dialog.choose_option()
            elif chat_dialog.can_continue():
                yield from chat_dialog.continue_()
            else:
                yield from execution.delay_ticks(1)
            if self._named(name) is None and not chat_dialog.is_open():
                break
        say(f'random event: {name} answered')
        return True

    def _pick(self, name, say):
        deadline = _core.step_time() + PICK_WAIT_MS
        while _core.step_time() < deadline:
            plant = self._named(name)
            if plant is None:
                return True
            if plant_strategy(plant.actions()) == 'evade':
                if is_hostile_event(plant.id, plant.distance(), _core.took_damage(4)):
                    evaded = yield from self._evade(name, say)
                    return evaded
                return True
            ops = [a for a in plant.actions() if 'pick' in a.lower() or 'take' in a.lower()]
            if ops:
                before = inventory.count('Strange fruit')
                mark = _core.message_mark()
                plant.interact(ops[0])
                index = plant.index
                yield from execution.delay_until(lambda: inventory.count('Strange fruit') > before or _plant_changed(index) or _not_ours(mark), 6000)
                if _not_ours(mark):
                    self.cooldown_until[f'pick:{name}'] = _core.step_time() + GIVE_UP_COOLDOWN_MS
                    say(f"random event: the {name} isn't ours; ignoring it for a while")
                    return True
                if inventory.count('Strange fruit') > before or self._named(name) is None:
                    say(f'random event: {name}, fruit picked')
                    return True
            index = plant.index
            yield from execution.delay_until(lambda: _plant_changed(index), 2400)
        say(f'random event: {name}, the fruit never ripened; trying again')
        return True

    def _evade(self, name, say):
        here = local_tile()
        threat = self._named(name)
        if threat is None:
            return False
        say(f'random event: {name} attacking; moving away until it goes')
        flee = None
        for tile in flee_candidates(here, threat.tile(), EVADE_DISTANCE):
            if _core.is_reachable(tile.x, tile.z):
                flee = tile
                break
        if flee is None:
            say('random event: nowhere to run to; waiting')
            yield from execution.delay_ticks(10)
            return False
        yield from direct_navigator.walk_to(flee, 2, 30000, True)
        gone = yield from execution.delay_until(lambda: self._named(name) is None, 45000)
        say(f'random event: {name} gone' if gone else f'random event: {name} still here')
        yield from direct_navigator.walk_to(here, 3, 40000)
        return True

    def _hazard(self, name, at, say):
        here = local_tile()
        say(f'random event: {name}, stepping away')
        source = at if at is not None else here
        for tile in flee_candidates(here, source, HAZARD_STEP):
            if _core.is_reachable(tile.x, tile.z):
                yield from direct_navigator.walk_to(tile, 1, 15000)
                break
        yield from execution.delay_ticks(60)
        return True

    def _hijack(self, say):
        here = local_tile()
        ent = npcs.query().where(lambda n: n.id in ENT_NPC_IDS and n.distance() <= 1).nearest()
        if ent is None:
            return False
        say('random event: ent, stopping the chop')
        candidates = step_off_candidates(here, ent.tile())
        step = candidates[0]
        for tile in candidates:
            if _core.is_reachable(tile.x, tile.z):
                step = tile
                break
        _core.walk_to(step.x, step.z, False)
        yield from execution.delay_ticks(1)
        self.cooldown_until['hijack:ent'] = _core.step_time() + ENT_LIFE_MS + 4000
        return True

    def _free_slot(self, say):
        if not inventory.is_full():
            return
        drop = pick_sacrificial([i.name for i in inventory.items()])
        if drop is None:
            say('random event: the backpack is full and nothing in it can go')
            return
        item = inventory.first(drop)
        before = inventory.used()
        say(f'random event: dropping a {drop} to make room')
        item.interact('Drop')
        yield from execution.delay_until(lambda: inventory.used() < before, 4000)

    def _lost_tool(self, say):
        say('random event: the tool lost its head; putting it back')
        where = handle_location([i.name for i in inventory.items()], [i.name for i in equipment.items()])
        if where is None:
            return False
        worn = where == 'worn'
        if worn:
            handle = [i for i in equipment.items() if _is_handle(i.name)]
            yield from self._free_slot(say)
            if handle:
                removed = yield from equipment.unequip(handle[0].name)
                if not removed:
                    return False
        head = ground_items.query().where(lambda g: (g.name or '').lower().endswith('axe head')).within(12).nearest()
        if head is not None:
            yield from self._free_slot(say)
            before = inventory.used()
            head.interact('Take')
            yield from execution.delay_until(lambda: inventory.used() > before, 6000)
        heads = [i for i in inventory.items() if (i.name or '').lower().endswith('axe head')]
        handles = [i for i in inventory.items() if _is_handle(i.name)]
        if not heads or not handles:
            say('random event: the head or the handle is still missing')
            return True
        before = inventory.used()
        heads[0].use_on(handles[0])
        joined = yield from execution.delay_until(lambda: inventory.used() < before, 5000)
        if joined and worn:
            tools = [i for i in inventory.items() if (i.name or '').lower().endswith('axe') and ('Wield' in i.actions() or 'Wear' in i.actions())]
            if tools:
                yield from equipment.equip(tools[0].name)
        say('random event: tool mended' if joined else 'random event: the tool did not mend')
        return True

    def _lost_gear(self, name, say):
        drop = ground_items.query().where(lambda g: (g.name or '').lower() == name).within(GEAR_RECOVERY_RANGE).nearest()
        if drop is None:
            return False
        say(f'random event: picking our {name} back up')
        before = inventory.used()
        drop.interact('Take')
        got = yield from execution.delay_until(lambda: inventory.used() > before, 8000)
        say(f'random event: {name} recovered' if got else f'random event: could not pick up the {name}')
        return True


def _plant_changed(index):
    current = _core.get_npc(index)
    return current is None or plant_strategy(current.actions()) != 'pick'


def _not_ours(mark):
    for seq, text in _core.game_messages_since(mark):
        if 'not here for you' in text.lower():
            return True
    return False


def _core_log(message):
    log(message)


random_events = _RandomEvents()
