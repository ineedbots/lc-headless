"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/dragonslayerJournal.test.ts (MIT, see thirdparty/rs2b0t)."""
from rs2004.quests.defs.dragonslayer.journal import DRAGON_STAGE, parse_dragon_journal
INTRO = "@str@The Guildmaster of the Champions' Guild said his friend|@str@Oziach could help me with a Rune Plate mail body.|"
OZIACH_SELLS = '@dre@Oziach@dbl@ will sell me @dre@Rune Plate Mail@dbl@ if I can prove myself|worthy by killing the @dre@Dragon Elvarg@dbl@ who lives on @dre@Crandor@dbl@|'
NEEDS_BRIEFING = '@dbl@I should return to @dre@Oziach@dbl@ for more detailed instructions.'
OBJECTIVES = "@dbl@To defeat the dragon I will need to find a @dre@map@dbl@ to|Crandor, a @dre@ship@dbl@, a @dre@captain@dbl@ to take me there and some kind|@dbl@of @dre@protection@dbl@ against the dragon's breath.|"
NEED_MELZAR = "@dbl@One-third of the map is in @dre@Melzar's Maze@dbl@, near|@dre@Rimmington@dbl@.|"
NEED_ORACLE = '@dbl@One-third of the map is hidden, and only the @dre@Oracle@dbl@ on @dre@Ice|Mountain@dbl@ will know where it is.|'
NEED_GOBLIN = '@dbl@One-third of the map was stolen by a @dre@goblin@dbl@ from the|@dre@Goblin Village@dbl@.|'
GOT_MELZAR = "@str@I found the piece of the map that was hidden in Melzar's|@str@Maze.|"
GOT_ORACLE = '@str@I found the piece of the map that was hidden in beneath Ice|@str@Mountain.|'
GOT_GOBLIN = '@str@I found the piece of the map that the goblin, Wormbrain,|@str@stole.|'
NEED_SHIELD = '@dbl@I should ask the @dre@Duke of Lumbridge@dbl@ for an @dre@anti-|dragonbreath shield@dbl@.|'
GOT_SHIELD = '@str@The Duke of Lumbridge gave me an anti-dragonbreath|@str@shield.|'
SHIP_FOR_SALE = '@dbl@I should see if there is a @dre@ship@dbl@ for sale in @dre@Port Sarim@dbl@.|'
BOUGHT_SHIP = '@str@I bought a ship in Port Sarim called the Lady Lumbridge.|'
NEEDS_REPAIR = '@dbl@My ship will need some repairs, using @dre@wooden planks@dbl@ and|@dre@steel nails@dbl@, before it is seaworthy again.|'
REPAIRED = '@str@I have repaired my ship using wooden planks and steel|@str@nails.|'
NEED_CAPTAIN = '@dbl@I still need to find a @dre@captain@dbl@ for my ship.|'
NED_HIRED = '@str@Captain Ned from Draynor Village has agreed to sail the|@str@ship to Crandor for me.|'
SET_SAIL = '@dbl@Now I should go to my ship in @dre@Port Sarim@dbl@ and set sail for|@dre@Crandor@dbl@!'
KILL_DRAGON = '@dbl@Now all I need to do is kill the @dre@dragon@dbl@!'
ORACLE_RHYME = "@dbl@I asked the @dre@Oracle@dbl@ about the lost map piece, and she told|me the following rhyme:|@dre@The map's behind a door below,|but entering is rather tough.|"
SECRET_PASSAGE = "@str@Now that I have found the secret passage leading from|@str@Karamja to Crandor I don't need to worry about having a|@str@seaworthy ship or a captain fit to sail it anymore.|"

def stage_of(text):
    return parse_dragon_journal(text).stage if parse_dragon_journal(text) is not None else None

def flags_of(text):
    return (parse_dragon_journal(text).flags if parse_dragon_journal(text) is not None else None) if (parse_dragon_journal(text).flags if parse_dragon_journal(text) is not None else None) is not None else set()

def _fn1():

    def _fn2():
        text = "@dbl@I can start this quest by speaking to the @dre@Guildmaster@dbl@ in|the @dre@Champions' Guild@dbl@, south-west of Varrock.|"
        expect(stage_of(text)).to_be(DRAGON_STAGE.NOT_STARTED)
    test('not started', _fn2)

    def _fn3():
        text = INTRO + '@dbl@I should speak to @dre@Oziach@dbl@, who lives by the cliffs to the|west of @dre@Edgeville@dbl@.'
        expect(stage_of(text)).to_be(DRAGON_STAGE.SPOKEN_GUILDMASTER)
    test('spoken to the guildmaster', _fn3)

    def _fn4():
        text = INTRO + OZIACH_SELLS + NEEDS_BRIEFING
        expect(stage_of(text)).to_be(DRAGON_STAGE.SPOKEN_OZIACH)
        expect('needs-briefing' in flags_of(text)).to_be(True)
    test('spoken to Oziach but not yet briefed', _fn4)

    def _fn5():
        text = INTRO + OZIACH_SELLS + OBJECTIVES + NEED_MELZAR + NEED_ORACLE + NEED_GOBLIN + NEED_SHIELD + SHIP_FOR_SALE
        expect(stage_of(text)).to_be(DRAGON_STAGE.SPOKEN_OZIACH)
        expect('needs-briefing' in flags_of(text)).to_be(False)
    test('briefed, gathering map pieces', _fn5)

    def _fn6():
        text = INTRO + OZIACH_SELLS + OBJECTIVES + GOT_MELZAR + GOT_ORACLE + GOT_GOBLIN + GOT_SHIELD + BOUGHT_SHIP + NEEDS_REPAIR + NEED_CAPTAIN
        expect(stage_of(text)).to_be(DRAGON_STAGE.BOUGHT_SHIP)
    test('ship bought but not repaired', _fn6)

    def _fn7():
        text = INTRO + OZIACH_SELLS + OBJECTIVES + GOT_MELZAR + GOT_ORACLE + GOT_GOBLIN + GOT_SHIELD + BOUGHT_SHIP + REPAIRED + NEED_CAPTAIN
        expect(stage_of(text)).to_be(DRAGON_STAGE.REPAIRED_SHIP)
    test('ship repaired, still no captain', _fn7)

    def _fn8():
        text = INTRO + OZIACH_SELLS + GOT_MELZAR + GOT_ORACLE + GOT_GOBLIN + GOT_SHIELD + BOUGHT_SHIP + REPAIRED + NED_HIRED + SET_SAIL
        expect(stage_of(text)).to_be(DRAGON_STAGE.NED_GIVEN_MAP)
    test('Ned hired and the map handed over', _fn8)

    def _fn9():
        text = INTRO + OZIACH_SELLS + GOT_MELZAR + GOT_ORACLE + GOT_GOBLIN + GOT_SHIELD + NED_HIRED + REPAIRED + KILL_DRAGON
        expect(stage_of(text)).to_be(DRAGON_STAGE.SAILED_TO_CRANDOR)
    test('landed on Crandor', _fn9)

    def _fn10():
        expect(stage_of(INTRO + GOT_MELZAR + '@red@QUEST COMPLETE!')).to_be(DRAGON_STAGE.COMPLETE)
    test('complete', _fn10)

    def _fn11():
        expect(parse_dragon_journal('@dbl@Something else entirely.')).to_be_undefined()
    test('an unrecognised journal yields no stage', _fn11)
describe('parseDragonJournal stages', _fn1)

def _fn12():

    def _fn13():
        none = flags_of(INTRO + OBJECTIVES + NEED_MELZAR + NEED_ORACLE + NEED_GOBLIN + SHIP_FOR_SALE)
        expect('map-melzar' in none).to_be(False)
        expect('map-ice' in none).to_be(False)
        expect('map-wormbrain' in none).to_be(False)
        some = flags_of(INTRO + OBJECTIVES + GOT_MELZAR + NEED_ORACLE + GOT_GOBLIN + SHIP_FOR_SALE)
        expect('map-melzar' in some).to_be(True)
        expect('map-ice' in some).to_be(False)
        expect('map-wormbrain' in some).to_be(True)
    test('tracks each map piece independently', _fn13)

    def _fn14():
        expect('has-shield' in flags_of(INTRO + NEED_SHIELD + SHIP_FOR_SALE)).to_be(False)
        expect('has-shield' in flags_of(INTRO + GOT_SHIELD + SHIP_FOR_SALE)).to_be(True)
    test('separates having the shield from being told to fetch it', _fn14)

    def _fn15():
        expect('asked-oracle' in flags_of(INTRO + OBJECTIVES + NEED_ORACLE + SHIP_FOR_SALE)).to_be(False)
        expect('asked-oracle' in flags_of(INTRO + OBJECTIVES + ORACLE_RHYME + SHIP_FOR_SALE)).to_be(True)
    test('notices the oracle rhyme', _fn15)

    def _fn16():
        text = INTRO + BOUGHT_SHIP + REPAIRED + NED_HIRED + SET_SAIL
        expect('ship-repaired' in flags_of(text)).to_be(True)
        expect('ned-hired' in flags_of(text)).to_be(True)
    test('notices the repaired ship and the hired captain', _fn16)

    def _fn17():
        text = INTRO + GOT_MELZAR + GOT_ORACLE + GOT_GOBLIN + SECRET_PASSAGE + KILL_DRAGON
        expect(stage_of(text)).to_be(DRAGON_STAGE.SAILED_TO_CRANDOR)
        expect('secret-passage' in flags_of(text)).to_be(True)
    test('notices the Karamja passage once it replaces the ship', _fn17)
describe('parseDragonJournal flags', _fn12)

def snapshot_fields(**fields):
    for name in ['inv', 'inv_ids', 'bank', 'bank_ids']:
        if isinstance(fields.get(name), (Record, Fake)):
            fields[name] = fields[name]._fields
    return QuestSnapshot(**fields)
