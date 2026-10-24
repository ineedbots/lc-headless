"""The queen's drops, one collector at a time: rs2b0t's scripts/JiveKQ/loot.ts (MIT, see thirdparty/rs2b0t). A
step sends at most one click and never waits, so the fight keeps its tick."""

import time

from rs2004.catalogs import Record, drop_db
from bots.jivekq.loadout import ARROWS, FOOD
from bots.jivekq.policy import in_lair, near
from bots.jivekq.recovery import tile_message

DROPS = set(drop_db().get('Kalphite Queen') or [])
EQUIPMENT = set(['Dragon chainbody', 'Dragon spear', 'Shield left half', 'Rune chainbody', 'Lava battlestaff', 'Rune warhammer', 'Rune spear', 'Rune axe',
                 'Amulet of power', 'Adamant spear'])


def loot_priority(name):
    if name in EQUIPMENT:
        return 0
    return 2 if name == 'Rune arrow' else 1


def eligible_loot(name, recover_arrows=False):
    return (recover_arrows and name == 'Rune arrow') or (name in DROPS and 'arrow' not in name.lower())


def _key(id, tile):
    return f'{id}:{tile.x}:{tile.z}:{tile.level}'


def _stacks(id):
    if inventory.count_by_id(id) == 0:
        return False
    kind = reader.item_type(id)
    return kind is not None and kind.stackable


def _room(id, name):
    return not inventory.is_full() or _stacks(id) or inventory.first('Vial') is not None or (loot_priority(name) == 0 and inventory.count_by_id(FOOD) > 2)


class LootClaim:
    """The drop an account has its eye on, and whether it's the one picking it up."""

    def __init__(self, id, name, tile, collecting):
        self.id = id
        self.name = name
        self.tile = tile
        self.collecting = collecting

    def to_message(self):
        return {'id': self.id, 'name': self.name, 'tile': tile_message(self.tile), 'collecting': self.collecting}


def now_ms():
    return time.time() * 1000


def step_to(tile):
    """One walk click, not waited on."""
    return direct_navigator.walk(tile)


class LootResult:
    def __init__(self, busy, collected=None):
        self.busy = busy
        self.collected = collected


class _Target:
    def __init__(self, claim, tick, here):
        self.claim = claim
        self.offered = tick
        self.started = tick
        self.progress = tick
        self.position = here
        self.before = None
        self.attempt = -1
        self.attempts = 0
        self.missing = None
        self.used_food = False
        self.room = None


class LootCollector:
    def __init__(self):
        self.target = None
        self.backoff = {}

    def claim(self):
        return self.target.claim if self.target is not None else None

    def clear(self):
        self.target = None
        self.backoff = {}

    def _release(self, tick):
        if self.target is not None:
            c = self.target.claim
            self.backoff[_key(c.id, c.tile)] = tick + 20
        self.target = None
        return LootResult(False)

    def step(self, party, trip, excluded, ready, eat_for_space=None, recover_arrows=False):
        """Advances the claim one tick. ready() says whether the fight lets a click go now; eat_for_space() sends an
        Eat click for room and returns whether it went."""
        tick = game.tick()
        try:
            return self._advance(party, trip, excluded, ready, tick, eat_for_space, recover_arrows)
        except Exception:
            return self._release(tick)

    def _advance(self, party, trip, excluded, ready, tick, eat_for_space, recover_arrows):
        here = game.tile()
        if here is None or not in_lair(here):
            self.clear()
            return LootResult(False)
        for k in [k for k, until in self.backoff.items() if tick >= until]:
            del self.backoff[k]
        drops = ground_items.query().where(lambda g: eligible_loot(g.name or '', recover_arrows) and in_lair(g.tile())
                                           and not any([near(g.tile(), p, 0) for p in excluded])).results()
        target = self.target
        if target is not None and target.before is not None:
            count = inventory.count_by_id(target.claim.id) - target.before
            if count > 0:
                collected = Record({'id': target.claim.id, 'name': target.claim.name, 'count': count})
                self._release(tick)
                return LootResult(recover_arrows, collected)
        if target is not None and not eligible_loot(target.claim.name, recover_arrows):
            return self._release(tick)
        if target is not None and target.claim.id == ARROWS \
                and any([g.id != ARROWS and _key(g.id, g.tile()) not in self.backoff and _room(g.id, g.name) for g in drops]):
            if target.claim.collecting:
                step_to(here)
            self._release(tick)
            return LootResult(True)
        if target is None:
            free = [g for g in drops if _key(g.id, g.tile()) not in self.backoff and _room(g.id, g.name)]
            free.sort(key=lambda g: (loot_priority(g.name), g.distance()))
            if not free:
                return LootResult(False)
            drop = free[0]
            self.target = _Target(LootClaim(drop.id, drop.name, drop.tile(), False), tick, here)
            return LootResult(recover_arrows)
        drop = None
        for g in drops:
            if g.id == target.claim.id and near(g.tile(), target.claim.tile, 0):
                drop = g
                break
        if drop is None:
            if target.missing is None:
                target.missing = tick
            return self._release(tick) if tick - target.missing >= 3 else LootResult(target.claim.collecting)
        target.missing = None
        if tick == target.offered:
            return LootResult(recover_arrows)
        elected = party.loot_collector(trip, now_ms())
        if elected is None or elected.name != party.self_name:
            if target.claim.id == ARROWS and target.claim.collecting:
                step_to(here)
                self._release(tick)
                return LootResult(True)
            target.claim.collecting = False
            target.started = tick
            target.progress = tick
            return LootResult(recover_arrows)
        if not _room(drop.id, drop.name):
            return self._release(tick)
        target.claim.collecting = True
        if tick - target.started >= 60 or (target.attempts >= 4 and tick - target.attempt >= 4):
            return self._release(tick)
        allowed = ready()
        if self.target is not target:
            return LootResult(False)
        if not allowed:
            return LootResult(True)
        if target.room is not None:
            if inventory.count_by_id(target.room[0]) >= target.room[1]:
                return self._release(tick) if tick - target.room[2] >= 6 else LootResult(True)
            target.room = None
        if inventory.is_full() and not _stacks(drop.id):
            vial = inventory.first('Vial')
            if vial is not None:
                target.room = (vial.id, inventory.count_by_id(vial.id), tick)
                vial.interact('Drop')
            else:
                if eat_for_space is None or loot_priority(drop.name) != 0 or target.used_food or inventory.count_by_id(FOOD) <= 2:
                    return self._release(tick)
                target.room = (FOOD, inventory.count_by_id(FOOD), tick)
                target.used_food = True
                if not eat_for_space():
                    target.room = None
                    target.used_food = False
            return LootResult(True)
        if not near(here, target.position, 0):
            target.position = here
            target.progress = tick
        if target.attempt >= 0 and (tick - target.attempt < 4 or (not near(here, target.claim.tile, 1) and tick - target.progress < 6)):
            return LootResult(True)
        if target.before is None:
            target.before = inventory.count_by_id(drop.id)
        target.attempt = tick
        target.attempts += 1
        drop.interact('Take')
        return LootResult(True)
