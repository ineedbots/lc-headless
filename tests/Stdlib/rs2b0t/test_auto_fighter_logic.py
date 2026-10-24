"""The pure halves of rs2b0t's test/scripts/AutoFighter/bigBones.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's
describe, test and expect. The rest of AutoFighter's tests, and bigBones' task cases, stub the client's facades, which
pocketpy can't."""

from bots.autofighter.data import wants_auto_fighter_loot
from bots.auto_fighter import should_keep_bank_item

test('Big bones stay untouched by default and with only regular burial enabled', lambda: [
    expect(wants_auto_fighter_loot('Big bones', [], True)).to_be(False),
    expect(should_keep_bank_item('Big bones', 532, 'Trout', True, [], [], True)).to_be(False),
])

test('the Big bones option forces their loot and protects them during banking independently', lambda: [
    expect(wants_auto_fighter_loot('Big bones', [], False, True)).to_be(True),
    expect(wants_auto_fighter_loot('Bones', [], False, True)).to_be(False),
    expect(wants_auto_fighter_loot('Dragon bones', [], True, True)).to_be(False),
    expect(should_keep_bank_item('Big bones', 532, 'Trout', True, [], [], False, True)).to_be(True),
    expect(should_keep_bank_item('Bones', 526, 'Trout', True, [], [], False, True)).to_be(False),
])

test('banking deposits noted regular and Big bones even when burial is enabled', lambda: [
    expect(should_keep_bank_item('Bones', 527, 'Trout', True, [], [], True, True)).to_be(False),
    expect(should_keep_bank_item('Big bones', 533, 'Trout', True, [], [], True, True)).to_be(False),
    expect(should_keep_bank_item('Bones', 526, 'Trout', True, [], [], True, True)).to_be(True),
    expect(should_keep_bank_item('Big bones', 532, 'Trout', True, [], [], True, True)).to_be(True),
])
