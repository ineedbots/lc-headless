"""Solving the clue held, leg by leg, to the casket: rs2b0t's api/ai/clues/ClueExecutor.ts (MIT, see
thirdparty/rs2b0t). The Waits are used with yield from.

rs2b0t keeps the trail's state in module globals around one ClueExecutor object; here it's a class, and SolveClue
owns the instance, so the guardian encounter lives on the object the host bot keeps and a step an interruption
dropped resumes it."""

import json
import time

from rs2004 import execution
from rs2004.catalogs.combat import FOOD_OPTIONS, is_edible_food
from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import chat_dialog, modals
from rs2004.duel import fight_arena_at, in_duel_challenge_area, leave_clue_duel
from rs2004.entities import ground_items, locs, npcs
from rs2004.execution import event_signal
from rs2004.game import game, reader
from rs2004.items import equipment, inventory
from rs2004.messages import game_messages
from rs2004.quests.exec import primitives
from rs2004.reach import reach
from rs2004.routeplan import names_have_entrana_restricted_gear
from rs2004.settings import settings_store
from rs2004.tabs import quests
from rs2004.traversal import traversal
from rs2004.clues import puzzle_box
from rs2004.clues.acquire import ensure_coord_tools, ensure_extra_items, ensure_gate_items, ensure_spade
from rs2004.clues.data import CASKET_IDS, CLUE_DB, DIG_ANCHORS, KILL_ANCHORS, TALK_ANCHORS, challenge_answer, clue_gate, identify_step
from rs2004.clues.guardian import GuardianEncounter, GuardianProtection, died_since, hard_kit_snapshot, sustain_until
from rs2004.clues.plan import GUARDIAN_MIN_SHARKS, ClueTrace, hard_clue_kit, push_trace_ring
from rs2004.clues.steps import HANS_WAIT_SPOT, PILOT_CLUE, solve_hans, solve_mountain_pilot
from rs2004.clues.tools import SPADE_NAME
from rs2004.clues.travel import ARRIVE_RADIUS, DUEL_CLUE_ID, KHARAZI_CLUES, WALK_TIMEOUT_MS, crosses_clue_duel, crosses_kharazi, crosses_tirannwn
from rs2004.clues.travel import jungle_kit_missing, reset_clue_duel_search, trail_walk_opts, walk_across_clue_duel, walk_across_kharazi
from rs2004.clues.travel import walk_across_tirannwn

COORD_ITEMS = ['Sextant', 'Watch', 'Chart']
SEARCH_OPS = ['Search', 'Open']
STEP_ATTEMPTS = 4
PROGRESS_MS = 6000
MAX_STEPS = 20
OUTER_GUARD = 1000
REWARD_WAIT_MS = 2000
REWARD_CLOSE_TRIES = 5
TRAIL_COMPLETE = 'completed the treasure trail'
CHALLENGE_REPLY_MS = 3000
KEY_WALK_RADIUS = 5
KEY_HUNT_MS = 120000
KEY_ENGAGE_MS = 3000
# Black Heather respawns in 100 ticks; other riddle targets respawn sooner.
KEY_RESPAWN_MS = 70000
LOOT_WAIT_MS = 3000
# Why: player_combat.rs2 drops the attack op for several single-way ownership conflicts, so the op is sent again after
# its refusal message.
ATTACK_REFUSED = ['already under attack', 'someone else is fighting', 'not after you']
TRACE_STORAGE_NAMESPACE = 'ClueTrace'
TRACE_STORAGE_KEY = 'ring'
# The Entrana box the boat refuses weapons and armour on.
ENTRANA = (2802, 2878, 3329, 3393)


def _now_ms():
    return time.time() * 1000


def short_clue_name(obj):
    name = obj[len('trail_clue_'):] if obj.startswith('trail_clue_') else obj
    return name.replace('_', ' ')


def step_target(step):
    """Where a step's leg goes: the dig or search coord, or the NPC's anchor; None for a casket."""
    if step['type'] == 'open-casket':
        return None
    if step['type'] == 'talk':
        if step.get('npc') == 'Hans':
            return HANS_WAIT_SPOT
        return TALK_ANCHORS.get(step['id'])
    anchor = DIG_ANCHORS.get(step['id']) if step['type'] == 'dig' else None
    return anchor if anchor is not None else step.get('coord')


def tiles_to(target):
    me = game.tile() if target is not None else None
    return max(abs(me.x - target.x), abs(me.z - target.z)) if me is not None and target is not None else None


def tracked_id(step):
    return step['casket_id'] if step['type'] == 'open-casket' else step['id']


def describe_step(step):
    if step['type'] == 'open-casket':
        return f"{step['casket_obj']} (open-casket)"
    if step['type'] == 'talk':
        return f"{step['obj']} (talk {step.get('npc') or '?'})"
    c = step_target(step)
    where = f' at ({c.x},{c.z},{c.level})' if c is not None else ''
    return f"{step['obj']} ({step['type']}){where}"


def _held_ids():
    return [i.id for i in inventory.items()]


def _held_counts():
    counts = {}
    for i in inventory.items():
        counts[i.id] = counts.get(i.id, 0) + i.count
    return counts


# Why: only gains count; comparing the whole pack made every bite of food read as progress, so an idle leg reported
# step done and burned the trail's budget. A step also counts as progressed when it picks up something it needed, a
# riddle key or a tool.
def _gained_since(before):
    for id, count in _held_counts().items():
        if count > before.get(id, 0):
            return True
    return False


def _pick_search_loc(coord):
    """The loc to Search or Open on the coord, nearest first, Search before Open."""
    best = None
    for loc in locs.query().results():
        tile = loc.tile()
        if tile.level != coord.level:
            continue
        dist = tile.distance_to(coord)
        if dist > ARRIVE_RADIUS:
            continue
        ops = [a.lower() for a in loc.actions()]
        rank = -1
        for i in range(len(SEARCH_OPS)):
            if SEARCH_OPS[i].lower() in ops:
                rank = i
                break
        if rank == -1:
            continue
        if best is None or dist < best[2] or (dist == best[2] and rank < best[3]):
            best = (loc, SEARCH_OPS[rank], dist, rank)
    return (best[0], best[1]) if best is not None else None


def _drain_chat():
    for _ in range(10):
        if not chat_dialog.can_continue():
            break
        yield from chat_dialog.continue_()


def _eat_one_for_room():
    """Frees a slot by eating; the trail's other items stay."""
    edible = None
    for i in inventory.items():
        if 'eat' in [a.lower() for a in i.actions()]:
            edible = i
            break
    if edible is None:
        return False
    before = inventory.used()
    edible.interact('Eat')
    freed = yield from execution.delay_until(lambda: inventory.used() < before, 3000)
    return freed


def _refused_since(mark):
    return any([game_messages.saw_since(mark, line) for line in ATTACK_REFUSED])


def _answer_challenge_if_open(step, log):
    if step['type'] != 'talk' or not reader.count_dialog_open():
        return False
    n = challenge_answer(step['id'])
    if n is None:
        log(f"challenge count dialog open but no answer for clue {step['id']}: leaving it (the step will abandon)")
        return False
    chat_dialog.answer_count(n)
    log(f'challenge answered: {n}')
    replied = yield from execution.delay_until(lambda: chat_dialog.is_open() or chat_dialog.can_continue(), CHALLENGE_REPLY_MS)
    if not replied:
        log('challenge reply page never opened: leaving it to the next attempt')
        return True
    yield from _drain_chat()
    return True


class ClueProgress:
    """The leg under way, for a status line: the clue, the step, the leg and attempt, when it started, where it's
    going and how far that was when the leg began."""

    def __init__(self, clue_id, name, step, leg, attempt, started_at, target, start_dist):
        self.clue_id = clue_id
        self.name = name
        self.step = step
        self.leg = leg
        self.attempt = attempt
        self.started_at = started_at
        self.target = target
        self.start_dist = start_dist


class _StorageRing:
    """push_trace_ring's storage, on the account's settings_store, as rs2b0t's localStorage."""

    def get_item(self, key):
        raw = settings_store.saved(TRACE_STORAGE_NAMESPACE, key)
        return raw if isinstance(raw, str) else None

    def set_item(self, key, value):
        settings_store.save(TRACE_STORAGE_NAMESPACE, key, value)


class ClueExecutor:
    def __init__(self):
        self.current = None
        self.trace = ClueTrace(pos=_position)
        self.session_active = False
        self.session_legs = 0
        self.acquire_tries = 0
        self.recovery = None
        self.post_kill_clue = None
        self.guardian_halt = None
        self.guardian_encounter = None
        self.reward_collection = None

    def reset_session(self):
        reset_clue_duel_search()
        self.session_active = False
        self.reward_collection = None
        self.session_legs = 0
        self.acquire_tries = 0
        self.current = None
        self.recovery = None
        self.retry_guardian()

    def retry_guardian(self):
        self.guardian_halt = None
        self.guardian_encounter = None
        self.post_kill_clue = None

    def note_death(self):
        self.guardian_halt = 'dead'
        self.guardian_encounter = None
        self.post_kill_clue = None

    # Walking a leg

    def walk_leg(self, dest, log, radius=1):
        """Walks a clue leg, treating an unpayable toll as a shopping trip. Why: the walker names what the route was
        short of, and the desert's one entrance eats a Shantay pass, so a leg short a 5gp ticket buys one."""
        if crosses_clue_duel(dest):
            arrived = yield from walk_across_clue_duel(dest, radius, log)
            return arrived
        if crosses_tirannwn(dest):
            arrived = yield from walk_across_tirannwn(dest, radius, log, trail_walk_opts(log, radius))
            return arrived
        if crosses_kharazi(dest):
            arrived = yield from walk_across_kharazi(dest, radius, log)
            return arrived
        arrived = yield from traversal.walk_resilient(dest, **trail_walk_opts(log, radius))
        if arrived:
            return True
        short = traversal.last_missing_gate_items
        if len(short) == 0:
            return False
        bought = yield from ensure_gate_items(short, log)
        if not bought:
            return False
        arrived = yield from traversal.walk_resilient(dest, **trail_walk_opts(log, radius))
        return arrived

    # The riddle key

    # Why: Attack is refused outright whenever the server thinks the fight is somebody else's, so the op is sent
    # again until it takes; riddle001's keeper stands in the Bandit Camp, where aggressive bandits keep us flagged.
    def _acquire_riddle_key(self, kf, hunt_tile, log):
        """Kills the keeper of a riddle key and picks the key up."""
        key_id = kf['key_id']
        npc_name = kf['npc']

        def have_key():
            return any([i.id == key_id for i in inventory.items()])

        def key_on_ground():
            return _ground_item(key_id)

        def find_target():
            up = npcs.query().name(npc_name).action('Attack').where(lambda n: not n.targets_another_player()).results()
            for n in up:
                if n.targets_me():
                    return n
            return up[0] if up else None

        def take_key():
            key = key_on_ground()
            if key is None:
                return False
            if inventory.is_full():
                ate = yield from _eat_one_for_room()
                if not ate:
                    log(f"kill-for-key: the '{npc_name}' key is on the ground but the pack is full with nothing to eat")
                    return False
            if key.distance() > 1:
                yield from traversal.walk_resilient(key.tile(), radius=1, attempts=2, timeout_ms=WALK_TIMEOUT_MS, log=log)
            key.interact('Take')
            got = yield from execution.delay_until(have_key, LOOT_WAIT_MS)
            return got

        if have_key():
            return True
        there = yield from self.walk_leg(hunt_tile, log, KEY_WALK_RADIUS)
        if not there:
            log(f"kill-for-key: could not reach the '{npc_name}' spawn at ({hunt_tile.x},{hunt_tile.z}): abandoning riddle")
            return False
        deadline = _now_ms() + KEY_HUNT_MS
        refused = 0
        while _now_ms() < deadline:
            if event_signal.pending():
                return False
            yield from sustain.run()
            took = yield from take_key()
            if took:
                return True
            target = find_target()
            if target is None:
                log(f"kill-for-key: no '{npc_name}' up at ({hunt_tile.x},{hunt_tile.z}): waiting out the respawn")
                waited = yield from sustain_until(lambda: find_target() is not None or key_on_ground() is not None,
                                                  min(KEY_RESPAWN_MS, deadline - _now_ms()))
                if not waited:
                    log(f"kill-for-key: '{npc_name}' never respawned: abandoning riddle")
                    return False
                continue
            if target.distance() > 1 and not game.in_combat():
                yield from traversal.walk_resilient(target.tile(), radius=1, attempts=2, timeout_ms=WALK_TIMEOUT_MS, log=log)
                target = find_target() or target
            mark = game_messages.mark()
            target.interact('Attack')
            yield from sustain_until(lambda: game.in_combat() or key_on_ground() is not None or _refused_since(mark), KEY_ENGAGE_MS)
            if _refused_since(mark):
                refused += 1
                if refused == 1:
                    log(f"kill-for-key: the server refused the attack on '{npc_name}': sending it again until the flag clears")
                yield from execution.delay_ticks(2)
                continue
            # Why: riding the fight out on the tick keeps food going in, and falling through when we never engaged lets
            # the loop send again rather than park on an op the server quietly dropped.
            yield from sustain_until(lambda: have_key() or key_on_ground() is not None or not game.in_combat(), max(0, deadline - _now_ms()))
        took = yield from take_key()
        if took:
            return True
        if not have_key():
            refusals = f' ({refused} refused attacks)' if refused > 0 else ''
            log(f"kill-for-key: gave up on '{npc_name}' after {KEY_HUNT_MS // 1000}s{refusals}")
        return have_key()

    # One attempt at a step

    def _dispatch(self, step, log, ranged):
        target = step_target(step)
        if target is not None and crosses_tirannwn(target):
            yield from walk_across_tirannwn(target, ARRIVE_RADIUS, log, trail_walk_opts(log))
        kind = step['type']
        if kind == 'search':
            coord = step.get('coord')
            if coord is None:
                return None
            kf = step.get('key_from')
            if kf:
                hunt = KILL_ANCHORS.get(step['id']) or coord
                got = yield from self._acquire_riddle_key(kf, hunt, log)
                if not got:
                    return None
            there = yield from self.walk_leg(coord, log)
            if not there:
                return None
            pick = _pick_search_loc(coord)
            if pick is not None:
                pick[0].interact(pick[1])
            else:
                log(f'no searchable loc at ({coord.x},{coord.z},{coord.level})')
            return None
        if kind == 'dig':
            stopped = yield from self._dig(step, log, ranged)
            return stopped
        if kind == 'talk':
            if step.get('npc') == 'Hans':
                result = yield from solve_hans(step['id'], lambda tile: self.walk_leg(tile, log, 0), log)
                return result
            if step['id'] == PILOT_CLUE:
                result = yield from solve_mountain_pilot(lambda tile: self.walk_leg(tile, log, 0), log)
                return result
            anchor = TALK_ANCHORS.get(step['id'])
            npc = step.get('npc')
            if anchor is None or not npc:
                return None
            puzzle = step.get('puzzle')
            if puzzle and any([i.id == puzzle['id'] for i in inventory.items()]):
                # The solved box is handed back by talking again.
                yield from puzzle_box.solve_held(puzzle['id'], log)
            if chat_dialog.is_open() or chat_dialog.can_continue():
                yield from primitives.talk_through(npc, [], log)
                return None
            state = yield from reach.npc_dialog(npc, anchor, log=log)
            if state == 'done':
                yield from primitives.talk_through(npc, [], log)
            return None
        if kind == 'open-casket':
            casket_id = step['casket_id']
            casket = None
            for i in inventory.items():
                if i.id == casket_id:
                    casket = i
                    break
            if casket is None:
                return None
            mark = game_messages.mark()
            casket.interact('Open')
            gone = yield from execution.delay_until(lambda: all([i.id != casket_id for i in inventory.items()]), REWARD_WAIT_MS)
            if not gone:
                return None
            # Why: a hard trail is four to six caskets and the server keeps the count, so the only sign the trail ended
            # is that no scroll came back.
            if any([id in CLUE_DB for id in _held_ids()]):
                return None
            if game_messages.saw_since(mark, TRAIL_COMPLETE):
                log('the trail is complete')
            return None
        return None

    def _dig(self, step, log, ranged):
        coord = step.get('coord')
        if coord is None:
            return None
        anchor = DIG_ANCHORS.get(step['id'])
        spot = anchor if anchor is not None else coord
        death_mark = game_messages.mark()
        executor = self

        def died():
            return executor.guardian_halt == 'dead' or died_since(death_mark)

        def stand_on_it():
            there = yield from executor.walk_leg(spot, log, 0 if anchor is not None else ARRIVE_RADIUS)
            return there

        def dig():
            if died():
                return
            spade = inventory.first(SPADE_NAME)
            if spade is not None:
                spade.interact('Dig')
            return
            yield

        encounter = self.guardian_encounter
        if encounter is None or encounter[0] != step['id']:
            there = yield from stand_on_it()
            if not there:
                if died():
                    return 'dead'
                if step['id'] == DUEL_CLUE_ID and in_duel_challenge_area(game.tile()):
                    return 'yield'
                return None
        if died():
            return 'dead'
        if self.post_kill_clue == step['id']:
            yield from dig()
            return None
        guardian = step.get('guardian')
        encounter = self.guardian_encounter
        if encounter is None or encounter[0] != step['id']:
            protection = GuardianProtection(guardian, ranged) if guardian else None
            prepared = True
            if protection is not None:
                prepared = yield from protection.prepare()
            if died():
                return 'dead'
            if event_signal.pending():
                return 'yield'
            if not prepared:
                return 'supplies-needed'
            if guardian:
                self.guardian_encounter = (step['id'], GuardianEncounter(guardian, protection))
            yield from dig()
        # Why: a guarded coord yields the wizard on the first dig and the casket only on a dig after it dies, so both
        # happen in one attempt; the fight chases, so the bot walks back before the second dig.
        encounter = self.guardian_encounter
        if guardian and encounter is not None and encounter[0] == step['id']:
            if died_since(death_mark):
                return 'dead'
            outcome = yield from encounter[1].fight(log)
            if outcome != 'killed':
                return outcome
            self.guardian_encounter = None
            self.post_kill_clue = step['id']
            there = yield from stand_on_it()
            if there:
                if died():
                    return 'dead'
                yield from dig()
            if died():
                return 'dead'
        return None

    # Whether a step can go

    def _block_reason(self, step):
        kind = step['type']
        if kind != 'open-casket':
            gated = clue_gate(step['id'], quests.status)
            if gated:
                return gated
        if kind == 'dig' and inventory.first(SPADE_NAME) is None:
            return 'no Spade held'
        if kind == 'talk' and (not step.get('npc') or step['id'] not in TALK_ANCHORS):
            return f"no anchor for NPC '{step.get('npc') or '?'}'"
        if kind == 'dig' and step.get('needs_sextant'):
            missing = [n for n in COORD_ITEMS if inventory.first(n) is None]
            if missing:
                return f"coordinate clue needs {'+'.join(missing)} (not held)"
        extras = [n for n in (step.get('items') or []) if inventory.first(n) is None]
        if extras:
            return f"needs {'+'.join(extras)} (not held)"
        return None

    def _try_acquire(self, step, log):
        if step['type'] == 'open-casket':
            return False
        # A row's extras (Baxtorian's rope) come first: bank prep only withdraws them when the bank has one.
        extras = [n for n in (step.get('items') or []) if inventory.first(n) is None]
        if extras:
            bought = yield from ensure_extra_items(extras, log)
            if bought:
                return True
        if step['type'] != 'dig':
            return False
        if inventory.first(SPADE_NAME) is None:
            got = yield from ensure_spade(log)
            return got
        if step.get('needs_sextant') and any([inventory.first(n) is None for n in COORD_ITEMS]):
            got = yield from ensure_coord_tools(log)
            return got
        return False

    def _solve_step(self, step, log, on_attempt, ranged):
        """True when the step progressed, False when it didn't, or why it stopped."""
        tracked = tracked_id(step)
        before = _held_counts()
        guarded = step['type'] == 'dig' and bool(step.get('guardian'))

        def progressed():
            return tracked not in _held_ids() or (not guarded and _gained_since(before))

        for attempt in range(STEP_ATTEMPTS):
            if self.guardian_halt is not None:
                return self.guardian_halt
            if progressed():
                return True
            if event_signal.pending():
                return False
            yield from sustain.run()
            if needs_puzzle_room(step):
                return 'supplies-needed'
            on_attempt(attempt + 1)
            yield from _drain_chat()
            answered = yield from _answer_challenge_if_open(step, log)
            if not answered:
                stopped = yield from self._dispatch(step, log, ranged)
                if stopped:
                    return stopped
            moved = yield from execution.delay_until(progressed, PROGRESS_MS)
            if moved:
                return True
        return progressed()

    # The reward

    def _dismiss_reward_modal(self):
        yield from execution.delay_until(lambda: reader.main_modal() != -1, REWARD_WAIT_MS)
        for _ in range(REWARD_CLOSE_TRIES):
            if reader.main_modal() == -1:
                break
            yield from modals.close()
            yield from execution.delay_ticks(1)
        return reader.main_modal() == -1

    def _collect_reward(self, log):
        """Takes the casket's reward off the floor, where whatever didn't fit the pack was rolled."""
        if self.reward_collection is None:
            tile = game.tile()
            if tile is None:
                return False
            self.reward_collection = (tile, set())
        here, discarded = self.reward_collection
        dismissed = yield from self._dismiss_reward_modal()
        if not dismissed:
            return False
        yield from execution.delay_ticks(2)

        def on_tile(g):
            t = g.tile()
            return t.x == here.x and t.z == here.z and t.level == here.level and g.id not in discarded

        for _ in range(28):
            drop = ground_items.query().where(on_tile).nearest()
            if drop is None:
                self.reward_collection = None
                return True
            name = drop.name or ''
            kind = reader.item_type(drop.id)
            stacks = inventory.count_by_id(drop.id) > 0 and kind is not None and kind.stackable
            if inventory.is_full() and not stacks:
                food = None
                for i in inventory.items():
                    if any([is_edible_food(i, f) for f in FOOD_OPTIONS]):
                        food = i
                        break
                if food is None:
                    log(f"WARNING: '{name}' is left on the ground, the pack is full with no food to drop")
                    return False
                used = inventory.used()
                discarded.add(food.id)
                if not food.interact('Drop'):
                    return False
                dropped = yield from execution.delay_until(lambda: inventory.used() < used, LOOT_WAIT_MS)
                if not dropped:
                    return False
            drop_id = drop.id
            count = _held_counts().get(drop_id, 0)
            collected = lambda: _held_counts().get(drop_id, 0) > count and _ground_item_on(drop_id, here, discarded) is None
            if not drop.interact('Take'):
                return False
            took = yield from execution.delay_until(collected, LOOT_WAIT_MS)
            if not took:
                return False
            log(f"took '{name}' from the treasure trail")
        return False

    # The trail

    def _end(self, outcome, log, reason=None):
        reset_clue_duel_search()
        if outcome == 'abandon':
            self._dump_failure(reason or 'unknown', log)
        self.session_active = False
        self.reward_collection = None
        self.session_legs = 0
        self.acquire_tries = 0
        self.post_kill_clue = None
        self.recovery = None
        self.current = None
        return outcome

    def solve_held_clue(self, log, needs_bank=None, ranged=None):
        """Solves the trail the pack holds, to its reward. 'done', 'abandon', 'yield', 'reset-needed',
        'supplies-needed', 'dead' or 'guardian-lost'. A Wait."""
        if self.guardian_halt is not None:
            return self.guardian_halt
        trace = self.trace

        def tlog(m):
            trace.note(m)
            log(m)

        for _ in range(OUTER_GUARD):
            if event_signal.pending():
                trace.note('yield: random event pending')
                return 'yield'
            yield from sustain.run()
            if needs_puzzle_room(identify_step(_held_ids())):
                return 'supplies-needed'
            yield from _drain_chat()
            if event_signal.pending():
                return 'yield'
            if fight_arena_at(game.tile()) is not None and inventory.count_by_id(DUEL_CLUE_ID) == 0:
                left = yield from leave_clue_duel(tlog)
                if not left:
                    return 'yield'
            step = identify_step(_held_ids())
            if step is None:
                if self.session_active:
                    collected = yield from self._collect_reward(tlog)
                    if not collected:
                        return 'yield'
                tlog('trail complete')
                return self._end('done', log)
            if needs_bank is not None and needs_bank():
                return 'supplies-needed'
            clue_id = tracked_id(step)
            if self.recovery is None or self.recovery[0] != clue_id:
                self.recovery = [clue_id, False]
            leg_recovery = self.recovery
            name = short_clue_name(step['casket_obj'] if step['type'] == 'open-casket' else step['obj'])
            if not self.session_active:
                trace.begin(clue_id, name)
                self.session_active = True
                self.session_legs = 0
                self.acquire_tries = 0
            target = step_target(step)
            current = self.current
            same_leg = current is not None and current.clue_id == clue_id
            if not same_leg:
                self.acquire_tries = 0
            # The leg keeps its first distance across retries, so a progress bar doesn't reset every attempt.
            start_dist = current.start_dist if same_leg else (tiles_to(target) or 0)
            started_at = current.started_at if current is not None else _now_ms()
            self.current = ClueProgress(clue_id, name, describe_step(step), self.session_legs + 1, 0, started_at, target, start_dist)
            if self.session_legs >= MAX_STEPS:
                reason = f'exceeded {MAX_STEPS} steps'
                tlog(f'abandoning {describe_step(step)}: {reason}')
                return self._end('abandon', log, reason)
            guardian = step.get('guardian') if step['type'] == 'dig' else None
            encounter = self.guardian_encounter
            if guardian and (encounter is None or encounter[0] != step['id']) and self.post_kill_clue != step['id'] \
                    and hard_clue_kit(hard_kit_snapshot(False, ranged), GUARDIAN_MIN_SHARKS, guardian == 'Saradomin Wizard') != 'ready':
                return 'supplies-needed'
            coord = step.get('coord') if step['type'] != 'open-casket' else None
            if coord is not None and coord.level == 0 and ENTRANA[0] <= coord.x <= ENTRANA[1] and ENTRANA[2] <= coord.z <= ENTRANA[3] \
                    and (len(equipment.items()) > 0 or names_have_entrana_restricted_gear([i.name or '' for i in inventory.items()])):
                return 'supplies-needed'
            if step['type'] != 'open-casket' and step['id'] in KHARAZI_CLUES:
                missing = jungle_kit_missing()
                if missing:
                    tlog(f"Kharazi jungle needs {'+'.join(missing)}; banking for tools")
                    return 'supplies-needed'
            blocked = self._block_reason(step)
            if blocked:
                if self.acquire_tries < 2:
                    acquired = yield from self._try_acquire(step, tlog)
                    if acquired:
                        self.acquire_tries += 1
                        continue
                tlog(f'abandoning {describe_step(step)}: {blocked}')
                return self._end('abandon', log, blocked)
            tlog(f'leg {self.session_legs + 1}: solving {describe_step(step)} [{clue_id}]')
            executor = self

            def on_attempt(n):
                if executor.current is not None:
                    executor.current.attempt = n
                if n > 1:
                    trace.note(f'attempt {n}/{STEP_ATTEMPTS}')

            result = yield from self._solve_step(step, tlog, on_attempt, ranged)
            if isinstance(result, str) and result != 'guardian-lost':
                if result == 'dead':
                    self.guardian_halt = result
                    self.guardian_encounter = None
                    self.post_kill_clue = None
                return result
            if not result or result == 'guardian-lost':
                if event_signal.pending():
                    trace.note('yield: event fired mid-step')
                    return 'yield'
                if not leg_recovery[1]:
                    leg_recovery[1] = True
                    if result == 'guardian-lost':
                        self.guardian_encounter = None
                    self.acquire_tries = 0
                    self.current = None
                    why = 'guardian missing or unreachable' if result == 'guardian-lost' else f'no progress after {STEP_ATTEMPTS} attempts'
                    tlog(f'{why}; resetting at the nearest bank before retrying this clue')
                    yield from modals.close()
                    traversal.request_repath('clue recovery')
                    yield from execution.delay_ticks(2)
                    return 'reset-needed'
                reason = 'guardian still missing or unreachable after a reset' if result == 'guardian-lost' \
                    else f'no progress after {STEP_ATTEMPTS} attempts following a reset'
                tlog(f'abandoning {describe_step(step)}: {reason}')
                return self._end('abandon', log, reason)
            tlog('step done')
            self.session_legs += 1
        tlog('abandoning: loop guard reached (stuck?)')
        return self._end('abandon', log, 'loop guard reached')

    def _dump_failure(self, reason, log):
        """The abandoned trail's trace, to the account's log and the last five kept in settings_store."""
        dump = self.trace.dump(reason, self.session_legs)
        legs = 'leg' if dump['legs'] == 1 else 'legs'
        clue = dump['clue_id'] if dump['clue_id'] is not None else '?'
        log(f"==== clue trace (abandon: {reason}): {dump['name']} [{clue}], {dump['legs']} {legs} solved ====")
        lines = dump['lines']
        t0 = lines[0]['t'] if lines else dump['started_at']
        for i in range(len(lines)):
            line = lines[i]
            log(f"  {i + 1}. +{((line['t'] - t0) / 1000):.1f}s @{line['pos']} {line['m']}")
        log('==== end clue trace ====')
        try:
            push_trace_ring(_StorageRing(), TRACE_STORAGE_KEY, dump)
        except Exception:
            pass


def _ground_item(id):
    return ground_items.query().where(lambda g: g.id == id).nearest()


def _ground_item_on(id, tile, discarded):
    """The ground item of that id on the tile, unless it's one the reward pickup dropped for room."""
    return ground_items.query().where(lambda g: g.id == id and g.id not in discarded and g.tile().equals(tile)).nearest()


def _position():
    me = game.tile()
    return f'{me.x},{me.z},{me.level}' if me is not None else '?'


def needs_puzzle_room(step):
    """Whether a talk step's puzzle box is due and there's no slot for it."""
    if step is None or step['type'] != 'talk':
        return False
    puzzle = step.get('puzzle')
    return puzzle is not None and inventory.count_by_id(puzzle['id']) == 0 and inventory.is_full()
