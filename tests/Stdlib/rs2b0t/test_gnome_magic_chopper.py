"""rs2b0t's test/scripts/GnomeMagicChopper/GnomeMagicChopper.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's
describe, test and expect. rs2b0t stubs the bot's loc query; this checks the bank stair pins find_climb_loc filters by."""

from bots.gnome_magic_chopper import is_allowed_bank_stair_tile

test('accepts the real north bank staircase from the northern approach', lambda: expect(is_allowed_bank_stair_tile(Tile(2445, 3434, 0))).to_be(True))
test('keeps the southern bank staircase available', lambda: expect(is_allowed_bank_stair_tile(Tile(2444, 3414, 0))).to_be(True))
test('rejects stairs outside the bank pins', lambda: expect(is_allowed_bank_stair_tile(Tile(2445, 3443, 0))).to_be(False))
