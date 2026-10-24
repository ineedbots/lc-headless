"""rs2b0t's test/scripts/JiveChests/logic.test.ts and settings.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's
describe, test and expect. combine.test.ts and runtime.test.ts stub the client's facades, which pocketpy can't."""

from bots.jivechests.logic import CHEST_STAND, JUNK, KEY, KEYS_PER_TRIP, PackState, decide, junk_held, keys_to_withdraw
import bots.jive_chests as jive_chests


def at(keys=7, junk=0, free=20, at_chest=True, ground_loot=False, can_loot=False, pending_loot=False, banking=False):
    return PackState(keys, junk, free, at_chest, ground_loot, can_loot, pending_loot, banking)


COUNTS = {'Raw swordfish': 5, 'Body rune': 50, 'Adamant sq shield': 1, 'Uncut dragonstone': 3}

describe('the junk list', lambda: [
    test('includes the unwanted chest rewards', lambda: expect(JUNK).to_equal(['Raw swordfish', 'Body rune', 'Spinach roll', 'Adamant sq shield'])),
    test('names them as the client does, so a drop can find them', lambda: [
        expect(JUNK).not_.to_contain('Swordfish'),
        expect(JUNK).not_.to_contain('Body runes'),
    ]),
    test('junk_held counts every junk line in the pack', lambda: [
        expect(junk_held(lambda n: COUNTS.get(n, 0))).to_be(56),
        expect(junk_held(lambda n: 0)).to_be(0),
    ]),
])

describe('keys_to_withdraw', lambda: [
    test('tops the pack up to the trip size', lambda: [
        expect(keys_to_withdraw(0, 100)).to_be(KEYS_PER_TRIP),
        expect(keys_to_withdraw(3, 100)).to_be(KEYS_PER_TRIP - 3),
        expect(keys_to_withdraw(7, 100)).to_be(0),
    ]),
    test('takes what the bank has when it is short, and nothing when it is empty', lambda: [
        expect(keys_to_withdraw(0, 3)).to_be(3),
        expect(keys_to_withdraw(0, 0)).to_be(0),
    ]),
])

describe('decide', lambda: [
    test('keeps food unless a full pack blocks valuable ground loot', lambda: [
        expect(decide(at(junk=1))).to_be('open'),
        expect(decide(at(junk=1, keys=0, at_chest=False))).to_be('bank'),
        expect(decide(at(junk=1, free=0))).to_be('bank'),
        expect(decide(at(junk=1, free=0, ground_loot=True))).to_be('drop'),
        expect(decide(at(junk=1, free=0, ground_loot=True, can_loot=True))).to_be('loot'),
    ]),
    test('opens the chest while a key is held and we are standing at it', lambda: expect(decide(at())).to_be('open')),
    test('walks to the chest while a key is held and we are not', lambda: expect(decide(at(at_chest=False))).to_be('travel')),
    test('goes home once the keys are spent', lambda: expect(decide(at(keys=0))).to_be('bank')),
    test('keeps opening after a rune reward instead of reserving twelve empty slots', lambda: [
        expect(decide(at(keys=6, free=11))).to_be('open'),
        expect(decide(at(free=1))).to_be('open'),
        expect(decide(at(free=0))).to_be('bank'),
    ]),
    test('collects overflow before using another key or leaving after the last key', lambda: [
        expect(decide(at(ground_loot=True, can_loot=True))).to_be('loot'),
        expect(decide(at(keys=0, ground_loot=True, can_loot=True))).to_be('loot'),
        expect(decide(at(free=0, ground_loot=True, can_loot=False))).to_be('bank'),
    ]),
    test('returns for overflow even when all keys have been used', lambda: expect(decide(at(keys=0, at_chest=False, pending_loot=True))).to_be('travel')),
    test('finishes banking when teleporting has freed inventory slots', lambda: expect(decide(at(banking=True, at_chest=False, keys=3, free=3, pending_loot=True))).to_be('bank')),
])

describe('the chest stand', lambda: [
    test('is the requested player stand tile south of the chest at (2914, 3452)', lambda: expect([CHEST_STAND.x, CHEST_STAND.z, CHEST_STAND.level]).to_equal([2914, 3451, 0])),
    test('the key is the one the chest takes', lambda: expect(KEY).to_be('Crystal key')),
])

SETTINGS = jive_chests.SETTINGS

describe('JiveChests settings', lambda: [
    test('keeps chest trips as the default and offers bank-only key combining', lambda: [
        expect(list(SETTINGS.keys())).to_equal(['combine_keys', 'teleport_home']),
        expect(SETTINGS['combine_keys'].default).to_be(False),
        expect(SETTINGS['teleport_home'].default).to_be(True),
        expect(SETTINGS['teleport_home'].show_if).to_equal({'key': 'combine_keys', 'any_of': ['false']}),
    ]),
    test('no key count or tile is offered, since the trip size and the chest are fixed', lambda: [
        expect('keys' in SETTINGS).to_be(False),
        expect('chest_tile' in SETTINGS).to_be(False),
        expect('bank_stand' in SETTINGS).to_be(False),
    ]),
])

describe('JiveChests registration', lambda: [
    test('is a Money making script with the chest tags', lambda: [
        expect(jive_chests.BOT.category).to_be('Money making'),
        expect(jive_chests.BOT.tags).to_contain('chest'),
        expect(jive_chests.BOT.tags).to_contain('taverley'),
        expect(jive_chests.BOT.settings_schema is SETTINGS).to_be(True),
    ]),
])
