"""A hard dig's guardian, and the kit it's fought with: rs2b0t's api/ai/clues/Guardian.ts, guardianKit.ts and
hardCluePreparation.ts (MIT, see thirdparty/rs2b0t). The Waits are used with yield from.

The first dig at a guarded coordinate spawns a wizard instead of the casket, which comes only on a dig after it dies.
The encounter is an object the executor keeps, so a step dropped by an interruption resumes it rather than digging
again."""

import time

from rs2004 import execution
from rs2004.bank import bank
from rs2004.catalogs.tasks import sustain
from rs2004.entities import npcs
from rs2004.execution import event_signal
from rs2004.game import game, skills
from rs2004.geometry import Tile
from rs2004.items import equipment, inventory
from rs2004.messages import game_messages
from rs2004.navigation import reachability
from rs2004.routeplan import is_entrana_restricted_gear
from rs2004.tabs import PROTECT_FROM_MAGIC, WEAPON_SLOT, prayer, quests, special
from rs2004.traversal import NAV_PURE_WALK, traversal
from rs2004.clues.bank_access import reopen_clue_bank
from rs2004.clues.plan import GUARDIAN_FOOD_RESERVE, GUARDIAN_MIN_SHARKS, GUARDIAN_WEAPON_IDS, MIN_SHARKS, SHARK_ID, SUPERANTI, HardKitSnapshot
from rs2004.clues.plan import hard_clue_kit, hard_trail_food_target, ranged_weapon_id, superanti_doses

AMMO_SLOT = 13
SPAWN_RADIUS = 12
OWNED_RADIUS = 32
SPAWN_WAIT_TICKS = 10
FIGHT_MS = 180000
REATTACK_TICKS = 8
RANGED_REACH = 7
NOT_YOURS = 'not after you'
SOMEONE_ELSE = 'someone else is fighting'
POISONED = 'you have been poisoned'
# The words of the death message, "Oh dear, you are dead!", each matched on its own.
GUARDIAN_DEATH = ('oh dear', 'you are dead')
IMMUNITY_TICKS = 570
REFRESH_TICKS = 540


def _now_ms():
    return time.time() * 1000


def died_since(mark):
    """Whether "Oh dear, you are dead!" came since mark."""
    for message in game_messages.since(mark):
        text = (message.text or '').lower()
        if all([words in text for words in GUARDIAN_DEATH]):
            return True
    return False


class _LiveWait:
    def now(self):
        return _now_ms()

    def pump(self):
        yield from sustain.run()

    def tick(self):
        yield from execution.delay_ticks(1)


_LIVE_WAIT = _LiveWait()


def sustain_until(cond, ms, deps=None):
    """Waits for cond, running the sustain hook every tick, and at least once. deps (now(), and the Waits pump() and
    tick()) stand in for the clock, sustain and the tick, for a test. Use with yield from."""
    wait = deps if deps is not None else _LIVE_WAIT
    until = wait.now() + ms
    while True:
        yield from wait.pump()
        if cond():
            return True
        if wait.now() >= until:
            return False
        yield from wait.tick()


# The hard kit, read off the account

def hard_kit_snapshot(include_bank=False, ranged=None):
    items = inventory.items() + equipment.items() + (bank.items() if include_bank and bank.ready() else [])
    return HardKitSnapshot(skills.level('attack'), quests.status('Lost City') == 'complete', [i for i in items if not i.noted], ranged)


def hard_kit_fingerprint(include_bank=False, ranged=None):
    """A string that changes when anything the hard kit checks changes, so a blocked kit is retried only then."""
    kit = hard_kit_snapshot(include_bank, ranged)
    ids = GUARDIAN_WEAPON_IDS + [d['id'] for d in SUPERANTI] + [SHARK_ID]

    def of_id(id):
        return sum([i.count for i in kit.items if i.id == id])

    def named(name):
        return sum([i.count for i in kit.items if (i.name or '').lower() == name])

    reach = ''
    if ranged is not None:
        weapons = of_id(ranged_weapon_id(ranged.weapon))
        ammo = named(ranged.ammo.lower())
        reach = f'{ranged.weapon}:{weapons}:{ranged.ammo}:{ammo}'
    counts = ','.join([str(of_id(id)) for id in ids])
    return f'{kit.attack}:{kit.lost_city}:{counts}:{reach}'


def _worn_in(slot, test):
    return any([i.slot == slot and i.count > 0 and test(i) for i in equipment.items()])


def guardian_weapon_worn(ranged=None):
    if ranged is not None:
        weapon = ranged_weapon_id(ranged.weapon)
        ammo = ranged.ammo.lower()
        return _worn_in(WEAPON_SLOT, lambda i: i.id == weapon) and _worn_in(AMMO_SLOT, lambda i: (i.name or '').lower() == ammo)
    return _worn_in(WEAPON_SLOT, lambda i: i.id in GUARDIAN_WEAPON_IDS)


def _wears_id(id):
    return _worn_in(WEAPON_SLOT, lambda i: i.id == id)


def _ammo_worn(name):
    wanted = name.lower()
    return sum([i.count for i in equipment.items() if i.slot == AMMO_SLOT and (i.name or '').lower() == wanted])


def equip_guardian_weapon(ranged=None):
    """Wears the guardian weapon from the pack, and for a ranged loadout the ammo on top."""
    if ranged is not None:
        if bank.is_open():
            closed = yield from bank.close()
            if not closed:
                return False
        weapon_id = ranged_weapon_id(ranged.weapon)
        worn = lambda: _wears_id(weapon_id)
        if not worn():
            weapon = None
            for i in inventory.items():
                if i.id == weapon_id and not i.noted:
                    weapon = i
                    break
            if weapon is None or not weapon.interact('Wield'):
                return False
            on = yield from execution.delay_until(worn, 2500)
            if not on:
                return False
        ammo = inventory.first(ranged.ammo)
        if ammo is not None and not ammo.noted:
            target = _ammo_worn(ranged.ammo) + ammo.count
            if not ammo.interact('Wield'):
                return False
            on = yield from execution.delay_until(lambda: _ammo_worn(ranged.ammo) >= target, 2500)
            if not on:
                return False
        return guardian_weapon_worn(ranged)
    if guardian_weapon_worn():
        return True
    weapon = None
    for id in GUARDIAN_WEAPON_IDS:
        for i in inventory.items():
            if i.id == id and i.count > 0:
                weapon = i
                break
        if weapon is not None:
            break
    if weapon is None or not weapon.name:
        return False
    on = yield from equipment.equip(weapon.name)
    return on and guardian_weapon_worn()


def stock_hard_weapon(entrana, remember, preferred_weapon=None, minimum_sharks=15, ranged=None):
    """At an open bank, wears the guardian weapon (or the ranged loadout) for a hard trail. remember(name) is told
    the weapon it replaced. For Entrana the melee weapon goes back in the bank."""
    if not bank.ready() or hard_clue_kit(hard_kit_snapshot(True, ranged), minimum_sharks) != 'ready':
        return False
    current = None
    for i in equipment.items():
        if i.slot == WEAPON_SLOT and i.count > 0:
            current = i
            break
    if ranged is not None:
        if entrana:
            return True
        if current is not None and current.name and current.name.lower() != ranged.weapon.lower():
            remember(current.name)
        weapon_id = ranged_weapon_id(ranged.weapon)
        if weapon_id is None:
            return False
        if not any([i.id == weapon_id and not i.noted and i.count > 0 for i in inventory.items() + equipment.items()]):
            if not bank.withdraw_by_id(weapon_id, 'Withdraw 1'):
                return False
            took = yield from execution.delay_until(lambda: inventory.count_by_id(weapon_id) > 0, 2500)
            if not took:
                return False
        ammo = ranged.ammo.lower()
        owned = sum([i.count for i in inventory.items() + equipment.items() if (i.name or '').lower() == ammo])
        target = min(max(1, ranged.quantity), owned + bank.count(ranged.ammo))
        if owned < target:
            took = yield from bank.withdraw_x(ranged.ammo, target - owned)
            if not took:
                return False
        on = yield from equip_guardian_weapon(ranged)
        if not on:
            return False
        opened = yield from reopen_clue_bank()
        return opened
    available = [i for i in inventory.items() + bank.items() if i.id in GUARDIAN_WEAPON_IDS and i.count > 0]
    weapon = None
    if current is not None and current.id in GUARDIAN_WEAPON_IDS:
        weapon = current
    if weapon is None and preferred_weapon:
        for i in available:
            if (i.name or '').lower() == preferred_weapon.lower():
                weapon = i
                break
    if weapon is None:
        for id in GUARDIAN_WEAPON_IDS:
            for i in available:
                if i.id == id:
                    weapon = i
                    break
            if weapon is not None:
                break
    if weapon is None or not weapon.name:
        return False
    name = weapon.name
    if current is not None and current.name and current.id not in GUARDIAN_WEAPON_IDS:
        remember(current.name)
    if not equipment.contains(name) and inventory.first(name) is None:
        bank.withdraw(name, 'Withdraw 1')
        took = yield from execution.delay_until(lambda: inventory.first(name) is not None, 2500)
        if not took:
            return False
    if not guardian_weapon_worn():
        on = yield from equipment.equip(name)
        if not on:
            return False
    if not guardian_weapon_worn():
        return False
    if entrana:
        off = yield from equipment.unequip(name)
        if not off:
            return False
    opened = yield from reopen_clue_bank()
    if not opened:
        return False
    if entrana:
        yield from bank.deposit_all_matching(lambda item, id: is_entrana_restricted_gear(item))
    return True


def stock_hard_supplies(reserve_slots, bankable_items, minimum_sharks=15):
    """At an open bank: a Superantipoison dose and the hard trail's sharks."""
    if not bank.ready():
        return False
    dose_ids = [d['id'] for d in SUPERANTI]
    if not any([i.id in dose_ids for i in inventory.items()]):
        dose = None
        for d in SUPERANTI:
            if bank.count_by_id(d['id']) > 0:
                dose = d
                break
        if dose is None:
            return False
        bank.withdraw(dose['name'], 'Withdraw 1')
        took = yield from execution.delay_until(lambda: any([i.id == dose['id'] for i in inventory.items()]), 2500)
        if not took:
            return False

    def target():
        return hard_trail_food_target(inventory.count('Shark'), inventory.free(), reserve_slots, minimum_sharks)

    available = min(minimum_sharks, inventory.count('Shark') + bank.count_by_id(SHARK_ID))
    if (target() or 0) < available:
        yield from bank.deposit_all_matching(lambda name, id: name in bankable_items)
    want = target()
    if want is None:
        return False
    for _ in range(20):
        before = inventory.count('Shark')
        if before >= want:
            break
        need = want - before
        bank.withdraw('Shark', 'Withdraw 10' if need >= 10 else ('Withdraw 5' if need >= 5 else 'Withdraw 1'))
        took = yield from execution.delay_until(lambda: inventory.count('Shark') > before, 2500)
        if not took:
            break
    return inventory.count('Shark') >= minimum_sharks


# The protection: Superantipoison against the Saradomin wizard's poison, and the weapon (guardianKit.ts)

class GuardianProtection:
    def __init__(self, guardian='Saradomin Wizard', ranged=None):
        self.guardian = guardian
        self.ranged = ranged
        self.drank_at = None
        self.poison_mark = game_messages.mark()

    def weapon_ready(self):
        return guardian_weapon_worn(self.ranged)

    def prepare(self):
        """Wears the weapon and, for the Saradomin wizard, drinks a dose. A Wait."""
        needs_antipoison = self.guardian == 'Saradomin Wizard'
        if hard_clue_kit(hard_kit_snapshot(False, self.ranged), GUARDIAN_MIN_SHARKS, needs_antipoison) != 'ready':
            return False
        on = yield from equip_guardian_weapon(self.ranged)
        if not on:
            return False
        if needs_antipoison:
            drank = yield from self._drink(3)
            if not drank:
                return False
        return self.weapon_ready() and inventory.count('Shark') >= GUARDIAN_MIN_SHARKS

    def _dose(self):
        ids = [d['id'] for d in SUPERANTI]
        for i in inventory.items():
            if i.id in ids:
                return i
        return None

    def _drink(self, attempts=1):
        before = superanti_doses(inventory.items())
        if before == 0:
            return False
        tick = game.tick()
        confirmed = False
        for attempt in range(attempts):
            if attempt > 0:
                yield from execution.delay_ticks(2)
                if event_signal.pending():
                    return False
                yield from sustain.run()
            if event_signal.pending():
                return False
            confirmed = superanti_doses(inventory.items()) < before
            if confirmed:
                break
            if attempts > 1 and (hard_clue_kit(hard_kit_snapshot(False, self.ranged), GUARDIAN_MIN_SHARKS) != 'ready' or not self.weapon_ready()):
                return False
            potion = self._dose()
            if potion is None:
                return False
            if potion.interact('Drink'):
                confirmed = yield from execution.delay_until_ticks(lambda: superanti_doses(inventory.items()) < before, 2)
            if confirmed:
                break
        if not confirmed:
            return False
        self.drank_at = tick
        self.poison_mark = game_messages.mark()
        # Why: the potion's message_delay holds the player until tick+2, and a held op sent while delayed is dropped,
        # so a Dig sent the tick after the dose never fires.
        yield from execution.delay_ticks(3)
        return True

    def maintain(self):
        """'ready', 'drank' or 'supplies-needed'. A Wait."""
        if self.guardian != 'Saradomin Wizard':
            return 'ready'
        age = None if self.drank_at is None else game.tick() - self.drank_at
        poisoned = game_messages.saw_since(self.poison_mark, POISONED)
        if age is not None and 0 <= age < REFRESH_TICKS and not poisoned:
            return 'ready'
        drank = yield from self._drink()
        if drank:
            return 'drank'
        return 'ready' if not poisoned and age is not None and 0 <= age < IMMUNITY_TICKS else 'supplies-needed'


# The fight (Guardian.ts)

def _find_guardian(name):
    def candidate(n):
        return (n.distance() <= SPAWN_RADIUS or (n.targets_me() and n.distance() <= OWNED_RADIUS)) and not n.targets_another_player()

    found = npcs.query().name(name).action('Attack').where(candidate).results()
    for n in found:
        if n.targets_me():
            return n
    return found[0] if found else None


def _ranged_stand(target, here):
    tile = target.tile()
    candidates = []
    for dx in range(-RANGED_REACH, RANGED_REACH + 1):
        for dz in range(-RANGED_REACH, RANGED_REACH + 1):
            if dx != 0 or dz != 0:
                candidates.append(Tile(tile.x + dx, tile.z + dz, tile.level))
    candidates.sort(key=lambda p: p.distance_to(here))
    for p in candidates:
        if reachability.line_of_sight(p, tile, target.size) and reachability.can_reach(p, max_steps=2048):
            return p
    return None


def _melee_stand(tile, here):
    sides = [Tile(tile.x + dx, tile.z + dz, tile.level) for dx, dz in [(1, 0), (-1, 0), (0, 1), (0, -1)]]
    sides = [p for p in sides if reachability.can_step(p, tile) and reachability.can_reach(p, max_steps=2048)]
    sides.sort(key=lambda p: p.distance_to(here))
    return sides[0] if sides else None


class GuardianEncounter:
    """One guardian, from its spawn to its death: 'killed', 'yield', 'supplies-needed', 'dead' or 'guardian-lost'."""

    def __init__(self, name, protection=None):
        self.name = name
        self.protection = protection if protection is not None else GuardianProtection(name)
        self.mark = game_messages.mark()
        self.first = None
        self.spawn_ticks = 0
        self.saw_death = False
        self.owned = False

    def _dead(self):
        return died_since(self.mark) or skills.effective('hitpoints') <= 0

    def _live(self, first):
        index = first.index
        id = first.id
        found = npcs.query().name(self.name).where(lambda n: n.index == index and n.id == id).results()
        return found[0] if found else None

    def fight(self, log):
        """A Wait. Prays Protect from Magic for the fight and stops praying after it."""
        while self.first is None and self.spawn_ticks < SPAWN_WAIT_TICKS:
            if self._dead():
                return 'dead'
            self.first = _find_guardian(self.name)
            if event_signal.pending():
                return 'yield'
            if self.first is not None:
                break
            yield from sustain.run()
            yield from execution.delay_ticks(1)
            self.spawn_ticks += 1
        if self._dead():
            return 'dead'
        if self.first is None:
            self.first = _find_guardian(self.name)
        if event_signal.pending():
            return 'yield'
        if self.first is None:
            return 'guardian-lost'
        prayed = yield from prayer.set(PROTECT_FROM_MAGIC, True)
        outcome = yield from self._rounds(log)
        if prayed:
            yield from prayer.set(PROTECT_FROM_MAGIC, False)
        return outcome

    def _too_far(self, n):
        return n.distance() > (OWNED_RADIUS if self.owned or n.targets_me() else SPAWN_RADIUS)

    def _rounds(self, log):
        name = self.name
        first = self.first
        protection = self.protection
        self.owned = self.owned or first.targets_me()
        attacked_at = None
        deadline = _now_ms() + FIGHT_MS
        while _now_ms() < deadline:
            if self._dead():
                return 'dead'
            if event_signal.pending():
                return 'yield'
            target = self._live(first)
            if target is None:
                return 'killed' if self.saw_death and self.owned else 'guardian-lost'
            if target.targets_another_player() or self._too_far(target) or game_messages.saw_since(self.mark, NOT_YOURS) \
                    or game_messages.saw_since(self.mark, SOMEONE_ELSE):
                return 'guardian-lost'
            self.owned = self.owned or target.targets_me()
            self.saw_death = self.saw_death or (self.owned and target.health == 0 and target.max_health > 0)
            if self.saw_death:
                yield from sustain.run()
                yield from execution.delay_ticks(1)
                continue
            if not protection.weapon_ready() or inventory.count('Shark') <= GUARDIAN_FOOD_RESERVE:
                return 'supplies-needed'
            yield from sustain.run()
            yield from execution.delay_ticks(1)
            if self._dead():
                return 'dead'
            if event_signal.pending():
                return 'yield'
            kept = yield from protection.maintain()
            if kept == 'supplies-needed':
                return 'supplies-needed'
            if kept == 'drank':
                continue
            if event_signal.pending():
                return 'yield'
            current = self._live(first)
            if current is None or current.targets_another_player() or self._too_far(current):
                continue
            if current.targets_me() and current.health == 0 and current.max_health > 0:
                self.owned = True
                self.saw_death = True
                continue
            if not protection.weapon_ready() or inventory.count('Shark') <= GUARDIAN_FOOD_RESERVE:
                return 'supplies-needed'
            tile = current.tile()
            here = game.tile()
            probeable = here is not None and reachability.probeable(tile)
            blocked_adjacent = current.distance() == 1 and probeable and not reachability.can_step(here, tile)
            can_shoot = protection.ranged is not None and here is not None and current.distance() <= RANGED_REACH \
                and (not probeable or reachability.line_of_sight(here, tile, current.size))
            out_of_reach = (not can_shoot) if protection.ranged is not None else (current.distance() > 1 or blocked_adjacent)
            if out_of_reach:
                if probeable:
                    stand = _ranged_stand(current, here) if protection.ranged is not None else _melee_stand(tile, here)
                else:
                    stand = tile
                if stand is None:
                    log(f"{name}: no reachable {'ranged' if protection.ranged is not None else 'melee'} tile near ({tile.x},{tile.z},{tile.level})")
                    return 'guardian-lost'
                log(f'{name}: approaching guardian at ({tile.x},{tile.z},{tile.level}), {current.distance()} tiles away')
                radius = 0 if probeable else (RANGED_REACH if protection.ranged is not None else 1)
                reached = yield from traversal.walk_to(stand, radius=radius, timeout_ms=10000, log=log, use_teleport_catalog=False,
                                                       policy=NAV_PURE_WALK['policy'])
                if self._dead():
                    return 'dead'
                if event_signal.pending():
                    return 'yield'
                if not reached:
                    return 'guardian-lost'
                continue
            if protection.ranged is not None and game.combat_mode() != protection.ranged.mode:
                if not game.set_combat_mode(protection.ranged.mode):
                    return 'supplies-needed'
                yield from execution.delay_ticks(1)
                continue
            if special.ready(special.wielded()) and not special.armed():
                armed = yield from special.arm()
                if armed:
                    yield from execution.delay_ticks(1)
                    continue
            if attacked_at is None or game.tick() - attacked_at >= REATTACK_TICKS or not (game.in_combat() and current.targets_me()):
                if current.interact('Attack'):
                    attacked_at = game.tick()
        log(f'{name}: encounter timed out; stopping without another dig')
        return 'guardian-lost'


def fight_guardian(name, log, protection=None):
    outcome = yield from GuardianEncounter(name, protection).fight(log)
    return outcome
