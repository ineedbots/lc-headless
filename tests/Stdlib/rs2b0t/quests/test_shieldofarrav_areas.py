"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/shieldofarrav-areas.test.ts (MIT, see thirdparty/rs2b0t)."""
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot
from rs2004.quests.defs.shieldofarrav.areas import BARAEK, CURATOR, KATRINE_JOIN, RELDO, ROALD, SOA_ID, SOA_LOC, SOA_TILE, STRAVEN_JOIN, TRAMP, in_black_arm_upper, in_phoenix_hq, in_weapon_store

def tile(x, z, level):
    return Fake(**{'x': x, 'z': z, 'level': level})

def _fn1():

    def _fn2():
        expect(SOA_ID.BOOK).to_be(757)
        expect(SOA_ID.STORE_KEY).to_be(759)
        expect(SOA_ID.REPORT).to_be(761)
        expect(SOA_ID.SHIELD_PHOENIX).to_be(763)
        expect(SOA_ID.SHIELD_BLACKARM).to_be(765)
        expect(SOA_ID.CROSSBOW).to_be(767)
        expect(SOA_ID.CERTIFICATE).to_be(769)
    test('object ids match the content pack', _fn2)

    def _fn3():
        expect(SOA_LOC.BOOKCASE).to_be(2402)
        expect(SOA_LOC.PHOENIX_DOOR).to_be(2397)
        expect(SOA_LOC.STORE_DOOR).to_be(2398)
        expect(SOA_LOC.BLACKARM_DOOR).to_be(2399)
        expect(SOA_LOC.CUPBOARD_SHUT).to_be(2400)
        expect(SOA_LOC.CUPBOARD_OPEN).to_be(2401)
        expect(SOA_LOC.CHEST_SHUT).to_be(2403)
        expect(SOA_LOC.CHEST_OPEN).to_be(2404)
    test('loc ids match the map placements', _fn3)

    def _fn4():
        expect(RELDO.npc).to_be('Reldo')
        expect(BARAEK.npc).to_be('Baraek')
        expect(TRAMP.npc).to_be('Tramp')
        expect(STRAVEN_JOIN.npc).to_be('Straven')
        expect(KATRINE_JOIN.npc).to_be('Katrine')
        expect(CURATOR.npc).to_be('Curator')
        expect(ROALD.npc).to_be('King Roald')
    test('every stop names the npc exactly as varrock.npc does', _fn4)

    def _fn5():
        expect(RELDO.prefer).to_contain("I'm in search of a quest.")
        expect(BARAEK.prefer).to_contain('Can you tell me where I can find the Phoenix Gang?')
        expect(BARAEK.prefer).to_contain('Okay. Have 20 gold coins.')
        expect(TRAMP.prefer).to_contain('Is there anything down this alleyway?')
        expect(TRAMP.prefer).to_contain('Do you think they would let me join?')
        expect(STRAVEN_JOIN.prefer).to_contain('I know who you are!')
        expect(STRAVEN_JOIN.prefer).to_contain("I'd like to offer you my services.")
        expect(KATRINE_JOIN.prefer).to_contain("I've heard you're the Black Arm Gang.")
        expect(KATRINE_JOIN.prefer).to_contain('I want to become a member of your gang.')
        expect(KATRINE_JOIN.prefer).to_contain('Ok, no problem.')
    test('every stop prefers a line that exists in the content script', _fn5)

    def _fn6():
        for stop in [RELDO, BARAEK, TRAMP, STRAVEN_JOIN, KATRINE_JOIN, CURATOR, ROALD]:
            for i in range(len(stop.prefer)):
                for j in range(i + 1, len(stop.prefer)):
                    expect(stop.prefer[i] in stop.prefer[j]).to_be(False)
    test('no prefer entry is a substring of a later entry in the same list', _fn6)

    def _fn7():
        expect(in_phoenix_hq(tile(3240, 9770, 0))).to_be(True)
        expect(in_phoenix_hq(SOA_TILE.CHEST_STAND)).to_be(True)
        expect(in_phoenix_hq(tile(3244, 3383, 0))).to_be(False)
        expect(in_weapon_store(tile(3246, 3384, 1))).to_be(True)
        expect(in_weapon_store(tile(3246, 3384, 0))).to_be(False)
        expect(in_black_arm_upper(tile(3188, 3386, 1))).to_be(True)
        expect(in_black_arm_upper(tile(3188, 3386, 0))).to_be(False)
    test('pocket tests name the three sealed areas', _fn7)

    def _fn8():
        expect(in_phoenix_hq(None)).to_be(False)
        expect(in_weapon_store(None)).to_be(False)
        expect(in_black_arm_upper(None)).to_be(False)
    test('pocket tests are null-safe', _fn8)
describe('arrav areas', _fn1)

def snapshot_fields(**fields):
    for name in ['inv', 'inv_ids', 'bank', 'bank_ids']:
        if isinstance(fields.get(name), (Record, Fake)):
            fields[name] = fields[name]._fields
    return QuestSnapshot(**fields)
