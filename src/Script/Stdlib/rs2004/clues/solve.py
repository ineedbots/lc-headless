"""The task a bot runs to solve the clues it picks up: rs2b0t's api/ai/clues/SolveClue.ts and bankAccess.ts (MIT,
see thirdparty/rs2b0t). The Waits are used with yield from.

SolveClue(host) is a Task: it validates while a clue or casket is held, banks the pack down to the trail's kit,
solves the trail through a ClueExecutor and puts the host's gear back after. The host is the bot, which gives:

    log(message), set_status(text), is_food(name), food_name(), food_withdraw()

and, as it has them, hard_food_target (an attribute), weapon_name(), ranged_loadout() (a GuardianRangedLoadout),
enabled(), prepare_initial_bank() (a Wait that walks to the first bank with the host's own upkeep, False to block),
restore_prayer() and use_teleports()."""

from rs2004 import execution
from rs2004.bank import bank
from rs2004.bot import Task
from rs2004.catalogs.combat import food_heal_amount, should_eat_to_use_food
from rs2004.catalogs.places import nearest_altar
from rs2004.catalogs.tasks import sustain
from rs2004.entities import locs
from rs2004.execution import event_signal
from rs2004.game import game, skills
from rs2004.geometry import Tile
from rs2004.items import equipment, inventory
from rs2004.routeplan import is_entrana_restricted_gear, names_have_entrana_restricted_gear
from rs2004.tabs import WEAPON_SLOT, prayer
from rs2004.traversal import nearest_bank, traversal, world_state
from rs2004.clues.bank_access import open_clue_bank, reopen_clue_bank
from rs2004.clues.acquire import ensure_coord_tools, has_all_trio, has_coord_clue_held
from rs2004.clues.data import CASKET_IDS, CLUE_DB
from rs2004.clues.executor import ClueExecutor
from rs2004.clues.guardian import hard_kit_fingerprint, hard_kit_snapshot, stock_hard_supplies, stock_hard_weapon, sustain_until
from rs2004.clues.plan import COORD_TOOL_SLOTS, GUARDIAN_WEAPON_IDS, SHARK_ID, hard_clue_kit, teleport_rune_target, trail_food_target, weapon_needed
from rs2004.clues.teleports import is_teleport_item, teleport_kit_for
from rs2004.clues.tools import SPADE_NAME, trail_kit
from rs2004.clues.travel import KHARAZI_CLUES, MACHETE, RADIMUS_NOTES, crosses_clue_duel, crosses_kharazi, crosses_tirannwn, has_jungle_map, held_axe
from rs2004.clues.travel import jungle_axe, jungle_keep_names, jungle_kit_missing, set_trail_teleports, trail_walk_opts, walk_across_clue_duel
from rs2004.clues.travel import walk_across_kharazi, walk_across_tirannwn

CLUE_COINS = 1000
ALTAR_OP = 'Pray-at'
ALTAR_RADIUS = 2
ALTAR_WALK_MS = 180000
ALTAR_RESTORE_MS = 6000
EAT_CONFIRM_TICKS = 2
ROTTEN_FOOD_ID = 2959
SHANTAY_PASS = 'Shantay pass'
# The desert clue whose route eats a Shantay pass.
SHANTAY_CLUE = 3552


def held_clue_like_id():
    """The id of a held clue scroll or casket, or None."""
    for i in inventory.items():
        if i.id in CLUE_DB or i.id in CASKET_IDS:
            return i.id
    return None


def held_clue_scroll_id():
    for i in inventory.items():
        if i.id in CLUE_DB:
            return i.id
    return None


def _is_hard(id):
    if id is None:
        return False
    row = CLUE_DB.get(id)
    name = row['obj'] if row is not None else CASKET_IDS.get(id)
    return name is not None and '_hard_' in name


def is_entrana_clue_coord(c):
    """The hard-riddle drawers on Entrana, where the boat refuses weapons and armour."""
    return c is not None and c.level == 0 and 2802 <= c.x <= 2878 and 3329 <= c.z <= 3393


def _held_clue_needs_entrana_strip():
    id = held_clue_scroll_id()
    return id is not None and is_entrana_clue_coord(CLUE_DB[id].get('coord'))


def _bank_tile(near):
    t = near['tile']
    return Tile(t['x'], t['z'], t['level'])


# Why: the nearest bank from the elf camp routes across Isafdar, which the graph doesn't hold, so the trail leaves
# Tirannwn first, and one that dug in the Kharazi Jungle has to cut back out before any bank is on the graph.
def walk_to_bank(tile, log):
    if crosses_clue_duel(tile):
        arrived = yield from walk_across_clue_duel(tile, 3, log)
        return arrived
    if crosses_tirannwn(tile):
        arrived = yield from walk_across_tirannwn(tile, 3, log, trail_walk_opts(log, 3))
        return arrived
    if crosses_kharazi(tile):
        arrived = yield from walk_across_kharazi(tile, 3, log)
        return arrived
    opts = trail_walk_opts(log, 3)
    opts['attempts'] = 6
    opts['timeout_ms'] = 300000
    arrived = yield from traversal.walk_resilient(tile, **opts)
    return arrived


def _deposit_unprotected(protected):
    yield from bank.deposit_all_matching(lambda name, id: name.lower() not in protected)


class SolveClueHost:
    """A host built from functions, for a bot whose own names don't fit: SolveClue(SolveClueHost(log=..., ...)).
    The ones left None are the ones the host doesn't have."""

    def __init__(self, log=None, set_status=None, is_food=None, food_name=None, food_withdraw=None, weapon_name=None, enabled=None,
                 hard_food_target=None, ranged_loadout=None, prepare_initial_bank=None, restore_prayer=None, use_teleports=None):
        self.log = log
        self.set_status = set_status
        self.is_food = is_food
        self.food_name = food_name
        self.food_withdraw = food_withdraw
        self.weapon_name = weapon_name
        self.enabled = enabled
        self.hard_food_target = hard_food_target
        self.ranged_loadout = ranged_loadout
        self.prepare_initial_bank = prepare_initial_bank
        self.restore_prayer = restore_prayer
        self.use_teleports = use_teleports


def _host(host, name, default=None):
    """An optional member of the host, called when it's a method."""
    value = getattr(host, name, None)
    return default if value is None else value


class SolveClue(Task):
    def __init__(self, host):
        Task.__init__(self, label='solve clue')
        self.host = host
        self.executor = ClueExecutor()
        self.executor.reset_session()
        self.hard_trail = False
        self.blocked_kit = None
        self.blocked_bank_kit = None
        self.death_blocked = False
        self.restoring = False
        self.retreat_pending = False
        self.initial_bank_visited = False
        self.completion_pending = False
        self.collecting_rewards = False
        self.trail_weapon = None
        self.banked_this_solve = False
        self.recovery_pending = False
        # One restock trip per dry spell, cleared as soon as food is held again.
        self.tried_food_restock = False
        self.abandoned_clue_id = None
        self.stripped_gear = []
        self.stripped_counts = {}
        self.entrana_stripped = False
        self.status = 'idle'

    # The host's optional members

    def _log(self, m):
        self.host.log(f'[clue] {m}')

    def _ranged(self):
        loadout = _host(self.host, 'ranged_loadout')
        return loadout() if loadout is not None else None

    def _weapon_name(self):
        weapon = _host(self.host, 'weapon_name')
        return weapon() if weapon is not None else ''

    def _hard_food_target(self):
        return _host(self.host, 'hard_food_target', 15)

    def _use_teleports(self):
        use = _host(self.host, 'use_teleports')
        return use() if use is not None else True

    # Guards

    def _retreat_from_guardian(self):
        here = game.tile()
        near = nearest_bank(here) if here is not None else None
        walked = False
        if near is not None:
            walked = yield from walk_to_bank(_bank_tile(near), self._log)
        calm = False
        if walked:
            calm = yield from sustain_until(lambda: not game.in_combat(), 6000)
        if not walked or not calm:
            self.status = 'guardian retreat blocked'
            self._log('no safe bank route completed; guardian retry and host handoff remain blocked')
            return False
        self.retreat_pending = False
        return True

    def _preparation_fingerprint(self, include_bank=False):
        kit = hard_kit_fingerprint(include_bank, self._ranged())
        if held_clue_scroll_id() not in KHARAZI_CLUES:
            return kit
        items = inventory.items() + equipment.items() + (bank.items() if include_bank and bank.ready() else [])
        tools = [sum([i.count for i in items if i.name == name]) for name in jungle_keep_names()]
        return f"{kit}:{','.join([str(t) for t in tools])}:{has_jungle_map()}"

    def _kit_blocked(self):
        return self.blocked_kit is not None and self.blocked_kit == self._preparation_fingerprint() \
            and not (bank.ready() and self.blocked_bank_kit is not None and self.blocked_bank_kit != self._preparation_fingerprint(True))

    def _block_hard_kit(self):
        self.blocked_kit = self._preparation_fingerprint()
        if bank.ready():
            self.blocked_bank_kit = self._preparation_fingerprint(True)

    def retry(self):
        """Clears every block, as after the operator fixed the kit."""
        self.executor.retry_guardian()
        self.blocked_kit = None
        self.blocked_bank_kit = None
        self.death_blocked = False
        self.abandoned_clue_id = None
        self.banked_this_solve = False
        self.initial_bank_visited = False

    def owns_equipment(self):
        """Whether the trail has the host's gear in hand, so the host mustn't re-gear."""
        return (self.recovery_pending and not self._kit_blocked()) or self.retreat_pending or self.collecting_rewards \
            or len(self.stripped_gear) > 0 or (self.hard_trail and self.banked_this_solve)

    def clue_status(self):
        return self.status

    def note_death(self):
        self.recovery_pending = False
        self.collecting_rewards = False
        self.banked_this_solve = False
        id = held_clue_scroll_id()
        if not self.hard_trail and not _is_hard(id):
            return
        self.executor.note_death()
        self.death_blocked = True
        self.retreat_pending = False
        self.restoring = True

    def validate(self):
        if self.collecting_rewards or self.completion_pending or self.retreat_pending:
            return True
        if len(self.stripped_gear) > 0 and (self.restoring or held_clue_like_id() is None):
            return True
        if self.death_blocked:
            return False
        if self.blocked_kit is not None:
            if self._kit_blocked():
                return False
            self.blocked_kit = None
        if self.recovery_pending:
            return True
        enabled = _host(self.host, 'enabled')
        if (enabled is not None and not enabled()) or event_signal.pending():
            return False
        id = held_clue_like_id()
        if self.abandoned_clue_id is not None and id != self.abandoned_clue_id:
            self.abandoned_clue_id = None
        return id is not None and id != self.abandoned_clue_id

    # Upkeep

    def _held_food(self):
        if self.hard_trail:
            return [i for i in inventory.items() if i.id == SHARK_ID]
        return [i for i in inventory.items() if not i.noted and self.host.is_food(i.name or '')]

    def _eat_if_hurt(self):
        food = self._held_food()
        top = skills.level('hitpoints')
        hp = skills.effective('hitpoints')
        heal = food_heal_amount('Shark' if self.hard_trail else self.host.food_name())
        if not food or not should_eat_to_use_food(hp, top, heal, len(food)):
            return
        self._log(f'eating {food[0].name} ({hp}/{top} hp)')
        food[0].interact('Eat')
        # Why: a guardian's hit lands in the same tick as the heal, so hp can end below where it started; a bite
        # that lands confirms on the next tick, and one the server dropped needs sending again.
        count = len(food)
        landed = yield from execution.delay_until_ticks(lambda: len(self._held_food()) < count or skills.effective('hitpoints') > hp,
                                                        EAT_CONFIRM_TICKS)
        if not landed:
            self._log(f'the bite never left the pack ({len(self._held_food())} left): sending it again')

    def _upkeep(self):
        yield from self._eat_if_hurt()
        for i in inventory.items():
            if i.id == ROTTEN_FOOD_ID:
                i.interact('Drop')
                break

    def _with_upkeep(self, gen):
        """Runs gen with the trail's upkeep as the sustain hook, and puts the host's back after."""
        before = sustain.hook
        sustain.set(self._upkeep)
        try:
            result = yield from gen
        except Exception as e:
            sustain.set(before)
            raise e
        sustain.set(before)
        return result

    # The task

    def execute(self):
        set_trail_teleports(self._use_teleports())
        if not self.collecting_rewards and (not self.recovery_pending or self.restoring) and (self.completion_pending or self.retreat_pending
                                                                                               or (len(self.stripped_gear) > 0 and (self.restoring or held_clue_like_id() is None))):
            yield from self._with_upkeep(self._wind_down())
            return
        if self.death_blocked or self._kit_blocked():
            return
        held = held_clue_like_id()
        hard = _is_hard(held)
        if held is not None and self.trail_weapon is None:
            original = None
            for i in equipment.items():
                if i.slot == WEAPON_SLOT:
                    original = i
                    break
            self.trail_weapon = original.name if original is not None and original.name else self._weapon_name()
            if self.trail_weapon != '' and (original is not None or hard) and self.trail_weapon not in self.stripped_gear:
                self.stripped_gear.append(self.trail_weapon)
        if held is not None:
            self.hard_trail = hard
        prepare = None
        if not self.banked_this_solve and not self.initial_bank_visited and held_clue_scroll_id() is not None:
            prepare = _host(self.host, 'prepare_initial_bank')
        if prepare is not None:
            ready = yield from prepare()
            if not ready:
                self.status = 'bank preparation blocked'
                self.host.set_status('clue: could not reach the initial bank')
                return
            self.initial_bank_visited = True
        yield from self._with_upkeep(self._run_trail(prepare is not None))

    def _wind_down(self):
        if self.retreat_pending:
            retreated = yield from self._retreat_from_guardian()
            if not retreated:
                return
        yield from self._restore_stripped_gear()
        if self.blocked_kit is not None:
            self._block_hard_kit()
        if self.completion_pending and not self.restoring:
            self._finish_trail()

    # Why: a trail banks once at the start, so a long one runs dry and walks the rest (often the Wilderness) with
    # nothing to eat; one restock trip per dry spell, so an empty bank can't loop it.
    def _needs_food(self):
        if (self.host.food_name() or '') == '':
            return False
        if any([not i.noted and self.host.is_food(i.name or '') for i in inventory.items()]):
            self.tried_food_restock = False
            return False
        return not self.tried_food_restock

    def _solve(self):
        result = yield from self.executor.solve_held_clue(self._log, lambda: self.entrana_stripped and held_clue_scroll_id() is not None
                                                          and not _held_clue_needs_entrana_strip(), self._ranged())
        return result

    def _blocked_after_bank(self):
        if self.hard_trail and self.blocked_kit is not None:
            yield from bank.close()
            self.restoring = True
            yield from self._restore_stripped_gear()
            self._block_hard_kit()

    def _run_trail(self, initial_bank_prepared=False):
        if self.recovery_pending:
            self.retreat_pending = self.retreat_pending or game.in_combat()
            if self.retreat_pending:
                retreated = yield from self._retreat_from_guardian()
                if not retreated:
                    return
            banked = yield from self._bank_first(False, True)
            if not banked:
                yield from self._blocked_after_bank()
                return
            self.recovery_pending = False
            self.banked_this_solve = True
        restock = self.banked_this_solve and not self.hard_trail and self._needs_food()
        if held_clue_scroll_id() is not None and (not self.banked_this_solve or restock):
            if restock:
                self.tried_food_restock = True
                self._log(f'out of {self.host.food_name()} mid-trail: banking to restock')
            banked = yield from self._bank_first(initial_bank_prepared)
            if not banked:
                yield from self._blocked_after_bank()
                return
            self.banked_this_solve = True
        self.status = 'solving'
        self.host.set_status('solving clue trail')
        outcome = yield from self._solve()
        if outcome == 'supplies-needed':
            self.banked_this_solve = False
            self.retreat_pending = game.in_combat()
            restocked_clue = held_clue_scroll_id()
            banked = yield from self._bank_first()
            if banked:
                self.retreat_pending = False
                self.banked_this_solve = True
                outcome = yield from self._solve()
            elif self.blocked_kit is None:
                self.status = 'waiting for hard kit bank'
                return
            if outcome == 'supplies-needed':
                self.retreat_pending = self.retreat_pending or game.in_combat()
                if self.retreat_pending:
                    retreated = yield from self._retreat_from_guardian()
                    if not retreated:
                        return
                if held_clue_scroll_id() != restocked_clue:
                    self.status = 'next guardian needs supplies'
                    return
                self._block_hard_kit()
                self.restoring = True
                yield from self._restore_stripped_gear()
                self._block_hard_kit()
                self.status = 'hard kit blocked'
                return
        if outcome == 'reset-needed':
            self.recovery_pending = True
            self.banked_this_solve = False
            self.initial_bank_visited = True
            self.tried_food_restock = False
            self.status = 'resetting at nearest bank'
            self.host.set_status('clue: resetting at nearest bank')
            return
        self.collecting_rewards = outcome == 'yield' and held_clue_like_id() is None and self.executor.current is not None
        if outcome == 'dead' or outcome == 'guardian-lost':
            if outcome == 'dead':
                self.note_death()
            else:
                self.death_blocked = True
            self.banked_this_solve = False
            self.restoring = True
            if outcome == 'guardian-lost':
                self.retreat_pending = True
                retreated = yield from self._retreat_from_guardian()
                if not retreated:
                    return
            yield from self._restore_stripped_gear()
            self.status = outcome
            return
        if outcome == 'yield':
            self.status = 'event: yielding'
            return
        if self.trail_weapon and self.trail_weapon in self.stripped_gear and not equipment.contains(self.trail_weapon):
            worn = [i.name for i in equipment.items() if i.slot == WEAPON_SLOT]
            self._log(f"{outcome}: restoring starting weapon '{self.trail_weapon}' (equipped: '{worn[0] if worn else 'none'}')")
        if outcome == 'abandon':
            self.abandoned_clue_id = held_clue_like_id()
            self.banked_this_solve = False
            self.initial_bank_visited = False
            self.restoring = True
            self.retreat_pending = game.in_combat()
            if self.retreat_pending:
                retreated = yield from self._retreat_from_guardian()
                if not retreated:
                    return
            yield from self._restore_stripped_gear()
            self.status = 'abandoned'
            self._log(f"abandoned {self.abandoned_clue_id if self.abandoned_clue_id is not None else '?'}: leaving it in the pack")
            return
        self.banked_this_solve = False
        self.initial_bank_visited = False
        self.restoring = True
        self.completion_pending = True
        yield from self._restore_stripped_gear()
        if self.restoring:
            return
        self._finish_trail()

    def _finish_trail(self):
        self.completion_pending = False
        self.hard_trail = False
        self.status = 'idle'
        self.host.set_status('clue solved')
        self._log('trail complete')

    # The host's gear

    def _wanted_count(self, name):
        return self.stripped_counts.get(name, 1)

    def _equipped(self, name):
        wanted = name.lower()
        for i in equipment.items():
            if (i.name or '').lower() == wanted:
                return i.count
        return 0

    def _restored(self, name):
        return self._equipped(name) >= self._wanted_count(name)

    def _restore_stripped_gear(self, preserve_trail=False):
        """Wears again the gear the trail took off, from the pack or the nearest bank."""
        self.restoring = not preserve_trail
        for name in self.stripped_gear:
            if not self._restored(name) and self._equipped(name) + inventory.count(name) >= self._wanted_count(name):
                yield from equipment.equip(name)
        want = [n for n in self.stripped_gear if not self._restored(n)]
        if len(want) == 0:
            if not preserve_trail:
                self.stripped_gear = []
                self.trail_weapon = None
            self.restoring = False
            self.entrana_stripped = False
            self.stripped_counts = {}
            return True
        here = game.tile()
        near = nearest_bank(here) if here is not None else None
        if near is None:
            self._log(f"no bank nearby to reclaim {', '.join(want)}: will retry after the next trail")
            return False
        self.status = 'restoring gear'
        self.host.set_status('clue: reclaiming stripped gear')
        self._log(f"reclaiming trail gear: {', '.join(want)}")
        walked = yield from walk_to_bank(_bank_tile(near), lambda m: self.host.log(f'  {m}'))
        if not walked:
            self._log('walk to the bank failed: gear stays banked, will retry')
            return False
        opened = yield from open_clue_bank()
        if not opened:
            self._log('could not open the bank: gear stays banked, will retry')
            return False
        ready = yield from bank.wait_ready()
        if not ready:
            return False
        if inventory.free() < len([n for n in want if inventory.first(n) is None]):
            yield from bank.deposit_all_matching(lambda name, id: name not in want and id not in CLUE_DB and id not in CASKET_IDS)
        for name in want:
            needed = self._wanted_count(name) - self._equipped(name) - inventory.count(name)
            if needed > 0:
                if needed > 1:
                    yield from bank.withdraw_x(name, needed)
                else:
                    bank.withdraw(name, 'Withdraw 1')
                took = yield from execution.delay_until(lambda: self._equipped(name) + inventory.count(name) >= self._wanted_count(name), 2500)
                if not took:
                    return False
        closed = yield from bank.close()
        if not closed:
            return False
        for name in want:
            if not self._restored(name) and inventory.first(name) is not None:
                yield from equipment.equip(name)
                yield from execution.delay_until(lambda: self._restored(name), 2500)
        missing = [n for n in self.stripped_gear if not self._restored(n)]
        if not preserve_trail:
            self.stripped_gear = missing
        self.restoring = not preserve_trail and len(missing) > 0
        if missing:
            self._log(f"could not re-equip {', '.join(missing)}: will retry")
            return False
        self.entrana_stripped = False
        self.stripped_counts = {}
        if not preserve_trail:
            self.trail_weapon = None
        return True

    # The bank stop

    # Why: start_chop_jungle wants a machete, an axe and Radimus's notes, the bank is the only source, and
    # woodcutting_axe_checker reads the pack and the right hand, so the axe has to come out of the bank too.
    def _stock_jungle_kit(self):
        if not bank.is_open() or not bank.ready() or event_signal.pending():
            return 'retry'
        want = []
        if inventory.first(MACHETE) is None and not equipment.contains(MACHETE):
            want.append(MACHETE)
        if held_axe() is None:
            axe = jungle_axe()
            if axe is None:
                self._log('no axe in the pack or the bank: the Kharazi band cannot be cut')
                return 'missing'
            want.append(axe)
        if not has_jungle_map():
            want.append(RADIMUS_NOTES)
        for name in want:
            if not bank.is_open() or not bank.ready() or event_signal.pending():
                return 'retry'
            if bank.count(name) < 1:
                self._log(f"no '{name}' in the bank: keeping the Kharazi clue")
                return 'missing'
            bank.withdraw(name, 'Withdraw 1')
            took = yield from execution.delay_until(lambda: inventory.first(name) is not None, 2500)
            if not took:
                self._log(f"'{name}' withdrawal did not land: will retry")
                return 'retry'
            self._log(f'took {name} for the Kharazi Jungle')
        return 'ready' if len(jungle_kit_missing()) == 0 else 'retry'

    def _bank_entrana_equipment(self, protected):
        self._log('Entrana destination: clearing the pack and banking all equipment')

        def deposit():
            yield from _deposit_unprotected(protected)

        yield from deposit()
        worn = equipment.items()
        if len(worn) > 0:
            self.entrana_stripped = True
        if not bank.is_open() or inventory.free() < len(worn):
            return False
        if len(worn) > 0:
            closed = yield from bank.close()
            if not closed:
                return False
            for item in worn:
                name = item.name
                if not name or event_signal.pending():
                    return False
                if (not self.hard_trail or item.id not in GUARDIAN_WEAPON_IDS) and not any([n.lower() == name.lower() for n in self.stripped_gear]):
                    self.stripped_gear.append(name)
                if name in self.stripped_gear:
                    self.stripped_counts[name] = item.count
                off = yield from equipment.unequip(name)
                if not off:
                    return False
            opened = yield from open_clue_bank()
            if not opened:
                return False
            ready = yield from bank.wait_ready()
            if not ready:
                return False
            yield from deposit()
        return bank.is_open() and len(equipment.items()) == 0 and all([(i.name or '').lower() in protected for i in inventory.items()])

    def _bank_first(self, initial_bank_prepared=False, rebuild=False):
        """Banks the pack down to the trail's kit and stocks it: the spade, the trio, coins, teleport runes, food,
        and for a hard trail the guardian's weapon and sharks. False to try again later."""
        self.status = 'banking'
        self.host.set_status('clue: banking loot before the trail')
        if not initial_bank_prepared:
            here = game.tile()
            near = nearest_bank(here) if here is not None else None
            if near is None:
                self._log('no known bank; hard kit preparation blocked' if self.hard_trail else 'no known bank to prep at: solving with the pack as-is')
                return not self.hard_trail and not rebuild
            self._log(f"banking loot at the {near['name']} bank ({_bank_tile(near)}) before solving")
            walked = yield from walk_to_bank(_bank_tile(near), lambda m: self.host.log(f'  {m}'))
            if not walked:
                self._log('walk to the bank failed: will retry')
                return False
        scroll_id = held_clue_scroll_id()
        entrana_strip = _held_clue_needs_entrana_strip()
        opened = yield from open_clue_bank(lambda m: self.host.log(f'  {m}'))
        if not opened:
            self._log('could not open the bank: will retry')
            return False
        if (initial_bank_prepared or rebuild or self.hard_trail) and not bank.ready():
            self.status = 'bank preparation blocked'
            self.host.set_status('clue: initial bank is not ready')
            return False
        ranged = self._ranged()
        if self.hard_trail:
            kit = hard_clue_kit(hard_kit_snapshot(True, ranged), self._hard_food_target())
            if kit != 'ready':
                self.status = f'hard kit: {kit}'
                self._block_hard_kit()
                yield from bank.close()
                return False
        row = CLUE_DB.get(scroll_id) if scroll_id is not None else None
        puzzle_id = row['puzzle']['id'] if row is not None and row.get('puzzle') else None
        key_id = row['key_from']['key_id'] if row is not None and row.get('key_from') else None
        protected = set()
        for it in inventory.items():
            if (it.id in CLUE_DB or it.id in CASKET_IDS or it.id == puzzle_id or it.id == key_id) and it.name:
                protected.add(it.name.lower())
        if entrana_strip:
            stripped = yield from self._bank_entrana_equipment(protected)
            if not stripped:
                return False
        if not entrana_strip and self.entrana_stripped:
            back = yield from self._restore_stripped_gear(True)
            if not back:
                return False
            reopened = yield from reopen_clue_bank()
            if not reopened:
                return False
        weapon = (self.trail_weapon if self.trail_weapon is not None else self._weapon_name()).lower()
        coord_items = set(['sextant', 'watch', 'chart'])
        row_items = set([n.lower() for n in ((row or {}).get('items') or [])])
        # Why: one snapshot per bank stop; a spell this account can't cast shouldn't reserve a pack slot.
        kit = teleport_kit_for(world_state())
        keep_teleports = self._use_teleports()
        needs_pass = scroll_id == SHANTAY_CLUE
        jungle_clue = scroll_id in KHARAZI_CLUES
        jungle_keep = set([n.lower() for n in jungle_keep_names()]) if jungle_clue else set()

        def keep(name):
            n = name.lower()
            if rebuild:
                return n in protected
            if entrana_strip and is_entrana_restricted_gear(name):
                return False
            # Why: a grind-sized food load fills the pack, so food is banked here and comes back capped below.
            return n in protected or 'clue' in n or 'casket' in n or n == SPADE_NAME.lower() or n == 'coins' \
                or (needs_pass and n == SHANTAY_PASS.lower()) or n in coord_items or n in row_items or n in jungle_keep \
                or (not entrana_strip and weapon != '' and n == weapon) or (keep_teleports and is_teleport_item(name, kit))

        yield from bank.deposit_all_matching(lambda name, id: not keep(name))
        if (initial_bank_prepared or rebuild) and (not bank.is_open() or any([not keep(i.name or '') for i in inventory.items()])):
            self.status = 'bank preparation blocked'
            self.host.set_status('clue: loot deposit incomplete')
            return False
        if puzzle_id is not None and inventory.count_by_id(puzzle_id) == 0 and bank.count_by_id(puzzle_id) > 0:
            bank.withdraw_by_id(puzzle_id, 'Withdraw 1')
            took = yield from execution.delay_until(lambda: inventory.count_by_id(puzzle_id) > 0, 2500)
            if not took:
                return False
        for item in trail_kit(scroll_id):
            if entrana_strip and is_entrana_restricted_gear(item):
                continue
            if inventory.first(item) is None:
                bank.withdraw(item, 'Withdraw 1')
                took = yield from execution.delay_until(lambda: inventory.first(item) is not None, 2500)
                if not took:
                    self._log(f"no '{item}' in the bank")
        weapon_name = self.trail_weapon if self.trail_weapon is not None else self._weapon_name()
        if not self.hard_trail and not entrana_strip and weapon_needed(weapon_name, inventory.first(weapon_name) is not None, equipment.contains(weapon_name)):
            bank.withdraw(weapon_name, 'Withdraw 1')
            yield from execution.delay_until(lambda: inventory.first(weapon_name) is not None, 2500)
        if self.hard_trail:
            solve = self

            def remember(name):
                if name not in solve.stripped_gear:
                    solve.stripped_gear.append(name)

            armed = yield from stock_hard_weapon(entrana_strip, remember, self._weapon_name(), self._hard_food_target(), ranged)
            if not armed:
                self._block_hard_kit()
                return False
        if entrana_strip and (len(equipment.items()) > 0 or names_have_entrana_restricted_gear([i.name or '' for i in inventory.items() + equipment.items()])):
            self._log('still holding Entrana-banned gear after bank prep: will retry')
            yield from bank.close()
            return False
        coins_short = CLUE_COINS - inventory.count('Coins')
        if coins_short > 0:
            took = yield from bank.withdraw_x('Coins', coins_short)
            if not took:
                self._log('no Coins in the bank: toll-gate routes will detour')
        if needs_pass and inventory.count(SHANTAY_PASS) < 1:
            if not bank.withdraw(SHANTAY_PASS, 'Withdraw 1'):
                self._log('no Shantay pass in the bank; desert routes will buy one from Shantay')
            else:
                landed = yield from execution.delay_until(lambda: inventory.count(SHANTAY_PASS) >= 1, 2500)
                if not landed:
                    self._log('Shantay pass withdraw did not land')
        if jungle_clue:
            stocked = yield from self._stock_jungle_kit()
            if stocked != 'ready':
                self.host.set_status(f"[clue] needs {', '.join(jungle_kit_missing())}")
                if stocked == 'missing':
                    self._block_hard_kit()
                return False
        scroll_is_coord = row is not None and row.get('needs_sextant') == True
        fetching_coord_tools = scroll_is_coord and not has_all_trio() and has_coord_clue_held()
        # Runes before food: both loops stop on a full pack and food is the bulky one.
        yield from self._stock_teleports(kit)
        food = self.host.food_name()
        puzzle_slots = 1 if puzzle_id is not None and inventory.count_by_id(puzzle_id) == 0 else 0
        if self.hard_trail:
            bankable = self.stripped_gear + (['Sextant', 'Watch', 'Chart'] if puzzle_id is not None else [])
            supplied = yield from stock_hard_supplies((COORD_TOOL_SLOTS if fetching_coord_tools else 0) + puzzle_slots, bankable, self._hard_food_target())
            if not supplied:
                self._block_hard_kit()
                return False
        elif food != '':
            target = trail_food_target(self.host.food_withdraw(), inventory.count(food), inventory.free(), COORD_TOOL_SLOTS if fetching_coord_tools else 0)
            self.host.set_status(f'clue: withdrawing {food}')
            self._log(f'taking {target} {food} for the trail (a grind load is {self.host.food_withdraw()})')
            for _ in range(12):
                if inventory.count(food) >= target or inventory.is_full():
                    break
                need = target - inventory.count(food)
                before = inventory.count(food)
                bank.withdraw(food, 'Withdraw 10' if need >= 10 else ('Withdraw 5' if need >= 5 else 'Withdraw 1'))
                took = yield from execution.delay_until(lambda: inventory.count(food) > before, 2500)
                if not took:
                    break
            if inventory.count(food) == 0 and target > 0:
                self._log(f"WARNING: no '{food}' came back out of the bank: running the trail without food")
        self._log(f'trail pack: {inventory.count(food)} {food}, {self._describe_teleports(kit)}, {inventory.free()} slots free')
        if fetching_coord_tools:
            self.host.set_status('clue: acquiring coordinate tools')
            yield from ensure_coord_tools(self._log)
        if self.hard_trail:
            yield from bank.close()
            if not entrana_strip and hard_clue_kit(hard_kit_snapshot(False, ranged), self._hard_food_target()) != 'ready':
                return False
        yield from self._top_up_prayer(scroll_id)
        return True

    def _describe_teleports(self, kit):
        if not self._use_teleports():
            return 'teleports off'
        if len(kit.usable) == 0:
            return f"no castable teleport (magic {skills.level('magic')})"
        stocked = len([name for name, _ in kit.runes if inventory.count(name) > 0])
        return f"{stocked}/{len(kit.runes)} runes for {'/'.join(kit.usable)}"

    # Why: only castable spells are stocked, since a hard casket needs six free slots; jewellery is kept when carried
    # but never fetched, since charges make the names inexact; and a missing rune isn't fatal, the walker walks.
    def _stock_teleports(self, kit):
        if not self._use_teleports():
            return
        for name, per_cast in kit.runes:
            want = teleport_rune_target(per_cast)
            for _ in range(6):
                if inventory.count(name) >= want or inventory.is_full():
                    break
                before = inventory.count(name)
                took = yield from bank.withdraw_x(name, want - before)
                if not took:
                    break
                landed = yield from execution.delay_until(lambda: inventory.count(name) > before, 2500)
                if not landed:
                    break

    # Why: any leg of a hard trail can be a guarded dig, so prayer is topped up at an altar first; low prayer never
    # blocks a trail, the fight runs without a protection prayer.
    def _top_up_prayer(self, scroll_id):
        restore = _host(self.host, 'restore_prayer')
        if not _is_hard(scroll_id) or (restore is not None and not restore()) or prayer.max() == 0 or prayer.full():
            return
        here = game.tile()
        altar = nearest_altar(here) if here is not None else None
        if altar is None:
            self._log('prayer is low but no known altar to restore at')
            return
        self.status = 'restoring prayer'
        self.host.set_status(f'clue: restoring prayer at {altar.name}')
        self._log(f'prayer {prayer.points()}/{prayer.max()}: praying at the {altar.name} altar ({altar.tile})')
        opts = trail_walk_opts(lambda m: self.host.log(f'  {m}'), ALTAR_RADIUS)
        opts['attempts'] = 4
        opts['timeout_ms'] = ALTAR_WALK_MS
        walked = yield from traversal.walk_resilient(altar.tile, **opts)
        if not walked:
            self._log('could not reach the altar: starting the trail with the prayer we have')
            return
        loc = locs.query().name(altar.loc).action(ALTAR_OP).nearest()
        if loc is None:
            self._log(f"no '{altar.loc}' to pray at here: starting the trail with the prayer we have")
            return
        loc.interact(ALTAR_OP)
        yield from execution.delay_until(lambda: prayer.full(), ALTAR_RESTORE_MS)
        self._log(f'prayer now {prayer.points()}/{prayer.max()}')

