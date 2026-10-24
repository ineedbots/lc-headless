"""rs2b0t's test/scripts/WanderLooter/WanderLooterLogic.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe,
test and expect. WanderLooterTasks.test.ts drives the bot through the client adapter's reader, which has no
counterpart here; the registry test reads the bot's own definition."""

from bots.wanderlooter.logic import LOOT_BLACKLIST_MS, LOOT_STUCK_MS, LootBlacklist, matches_loot, pick_wander_tile, should_bank_loot
from bots.wanderlooter.logic import should_deposit_on_bank, should_idle_bank
import bots.wander_looter as wander_looter

HERE = Tile(3200, 3200)


class Clock:
    def __init__(self, now):
        self.now = now

    def read(self):
        return self.now


class Counter:
    def __init__(self, accept):
        self.checked = 0
        self.accept = accept

    def navigable(self, tile):
        self.checked += 1
        return self.accept(tile)


def const(value):
    return lambda: value


describe('loot matching and banking rules', lambda: [
    test('loot names are exact, trimmed and case-insensitive', lambda: [
        expect(matches_loot('Pumpkin', ['pumpkin'])).to_be(True),
        expect(matches_loot('  PUMPKIN  ', ['Pumpkin'])).to_be(True),
        expect(matches_loot('Pumpkin pie', ['Pumpkin'])).to_be(False),
        expect(matches_loot(None, ['Pumpkin'])).to_be(False),
    ]),
    test('banking keeps coins and only the desired food amount', lambda: [
        expect(should_deposit_on_bank('Coins', 'Trout', 50, 10)).to_be(False),
        expect(should_deposit_on_bank('Pumpkin', 'Trout', 5, 10)).to_be(True),
        expect(should_deposit_on_bank('Trout', 'Trout', 5, 10)).to_be(False),
        expect(should_deposit_on_bank('Trout', 'Trout', 15, 10)).to_be(True),
    ]),
    test('banking triggers at the slot threshold or a full pack with loot', lambda: [
        expect(should_bank_loot(0, 28, True)).to_be(False),
        expect(should_bank_loot(27, 28, False)).to_be(False),
        expect(should_bank_loot(28, 28, False)).to_be(True),
        expect(should_bank_loot(1, 28, True)).to_be(True),
    ]),
    test('idle banking uses the last loot time', lambda: [
        expect(should_idle_bank(600000, 0, 600000)).to_be(True),
        expect(should_idle_bank(599999, 0, 600000)).to_be(False),
    ]),
])


def unreachable_is_blocked_at_once():
    clock = Clock(1000)
    blacklist = LootBlacklist(clock.read)
    expect(blacklist.failure(1, HERE, 'unreachable')).to_be('blacklisted')
    expect(blacklist.blocked(1, HERE)).to_be(True)
    expect(blacklist.blocked(1, HERE.translate(1, 0))).to_be(False)
    clock.now += LOOT_BLACKLIST_MS - 1
    expect(blacklist.blocked(1, HERE)).to_be(True)
    clock.now += 1
    expect(blacklist.blocked(1, HERE)).to_be(False)


def stuck_failures_wait_thirty_seconds():
    clock = Clock(1000)
    blacklist = LootBlacklist(clock.read)
    expect(blacklist.failure(1, HERE, 'retry')).to_be('retrying')
    clock.now += LOOT_STUCK_MS - 1
    expect(blacklist.failure(1, HERE, 'retry')).to_be('retrying')
    clock.now += 1
    expect(blacklist.failure(1, HERE, 'retry')).to_be('blacklisted')
    expect(blacklist.blocked(1, HERE)).to_be(True)


def damage_marks_unsafe():
    blacklist = LootBlacklist(const(1000))
    blacklist.mark_unsafe(1, HERE)
    expect(blacklist.blocked(1, HERE)).to_be(True)
    expect(blacklist.count()).to_be(1)


def success_clears_everything():
    clock = Clock(1000)
    blacklist = LootBlacklist(clock.read)
    blacklist.failure(1, HERE, 'retry')
    clock.now += LOOT_STUCK_MS
    blacklist.failure(1, HERE, 'retry')
    expect(blacklist.blocked(1, HERE)).to_be(True)
    blacklist.success(1, HERE)
    expect(blacklist.blocked(1, HERE)).to_be(False)


describe('loot blacklist', lambda: [
    test('unreachable loot is blocked immediately for 30 minutes', unreachable_is_blocked_at_once),
    test('ambiguous failures only blacklist after 30 seconds of stuck attempts', stuck_failures_wait_thirty_seconds),
    test('damage near a pickup marks its item+tile unsafe immediately', damage_marks_unsafe),
    test('a successful pickup clears both the stuck timer and the blacklist', success_clears_everything),
])


def prefers_full_distance():
    counter = Counter(lambda tile: tile.distance_to(HERE) == 30)
    target = pick_wander_tile(HERE, 30, counter.navigable, const(0.5))
    expect(counter.checked).to_be(1)
    expect(target.distance_to(HERE)).to_be(30)


def steps_down_from_upstairs():
    upstairs = Tile(3200, 3200, 1)
    for roll in [0, 0.5, 0.99]:
        expect(pick_wander_tile(upstairs, 30, lambda tile: tile.level == 0, const(roll))).to_equal(Tile(3200, 3200, 0))


def no_navigable_target():
    counter = Counter(lambda tile: False)
    expect(pick_wander_tile(HERE, 30, counter.navigable, const(0.5))).to_be_null()
    expect(counter.checked).to_be(24)


describe('wander targets', lambda: [
    test('prefers a navigable 30-step target', prefers_full_distance),
    test('falls back to a shorter navigable hop', lambda: expect(
        pick_wander_tile(HERE, 30, lambda tile: tile.distance_to(HERE) == 15, const(0.25)).distance_to(HERE)).to_be(15)),
    test('always steps down to level 0 instead of wandering upstairs', steps_down_from_upstairs),
    test('never chooses an upper floor from ground level', lambda: expect(pick_wander_tile(HERE, 30, lambda tile: True, const(0)).level).to_be(0)),
    test('avoids doubling back while forward targets remain navigable', lambda: expect(
        pick_wander_tile(HERE, 30, lambda tile: True, const(0.5), (0, -1)).z).to_be_less_than_or_equal(HERE.z)),
    test('allows a backwards hop when it is the only navigable option', lambda: expect(
        pick_wander_tile(HERE, 30, lambda tile: tile.z > HERE.z, const(0.5), (0, -1))).not_.to_be_null()),
    test('returns null instead of walking to an unnavigable tile', no_navigable_target),
])


describe('registry', lambda: [
    test('WanderLooter registers under Money making with its settings schema', lambda: [
        expect(wander_looter.BOT.name).to_be('WanderLooter'),
        expect(wander_looter.BOT.category).to_be('Money making'),
        expect(wander_looter.SETTINGS['loot'].default).to_equal(['Pumpkin']),
        expect(wander_looter.SETTINGS['bank_at_loot_slots'].default).to_be(28),
    ]),
])
