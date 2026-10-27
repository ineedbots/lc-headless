"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/shieldofarrav-journal.test.ts (MIT, see thirdparty/rs2b0t)."""
from rs2004.quests.defs.shieldofarrav.journal import SOA_STAGE, parse_shield_of_arrav_journal
NOT_STARTED = ["@dbl@I can start this quest by speaking to @dre@Reldo@dbl@ in @dre@Varrock's|Palace Library@dbl@, or by speaking to the @dre@Tramp@dbl@ near|", '@dbl@the @dre@Blue Moon Inn@dbl@ in @dre@Varrock@dbl@.|']
TOLD_OF_BOOK = ['@dre@Reldo@dbl@ says there is a @dre@quest@dbl@ hidden in one of the books in|his @dre@library somewhere. I should look for it and see.|']
READ_BOOK = ['@str@I read about a valuable shield stolen long ago by a gang of|@str@thieves with an outstanding reward upon it.|', '@dbl@I should ask @dre@Reldo@dbl@ in the @dre@Varrock palace library@dbl@ if he knows anything more about this.|']
SENT_TO_BARAEK = ['@str@I read about a valuable shield stolen long ago by a gang of|@str@thieves with an outstanding reward upon it.|', '@dbl@Reldo told me that the fur trader in @dre@Varrock@dbl@, named|@dre@Baraek@dbl@, knows about the @dre@Phoenix Gang@dbl@. I should speak to|him next.|']
FIND_STRAVEN = ['@str@I read about a valuable shield stolen long ago by a gang of|@str@thieves with an outstanding reward upon it.|', "@dbl@Baraek told me that the @dre@'Phoenix Gang'@dbl@ have a hideout in|the @dre@south-eastern part of Varrock@dbl@, disguising themselves|", '@dbl@as the @dre@VTAM Corporation@dbl@. I should find them and join.|']
KILL_JONNY_NO_REPORT = ['@str@as the VTAM Corporation.|', '@dbl@I spoke to @dre@Straven@dbl@ in the @dre@Phoenix Gang Headquarters|@dbl@south east of the @dre@Blue Moon Inn@dbl@. He offered to let me|', '@dbl@join the @dre@Gang@dbl@ in return for killing @dre@Jonny the Beard@dbl@ and|recovering an @dre@Intelligence Report@dbl@ from him. I can find|', '@dre@Jonny@dbl@ in the @dre@Blue Moon Inn@dbl@.|']
KILL_JONNY_REPORT_HELD = ['@str@join the Gang in return for killing Jonny the Beard and|@str@recovering an Intelligence Report from him.|', '@dbl@I confronted and killed @dre@Jonny the Beard@dbl@ in the @dre@Blue|Moon Inn@dbl@ and took an @dre@Intelligence Report@dbl@ from him. I|', '@dbl@should take this @dre@Report@dbl@ to @dre@Straven@dbl@.|']
PHOENIX_JOINED_NO_HALF = ['@dbl@gave this @dre@Report@dbl@ to @dre@Straven@dbl@ and he allowed me to join the|@dre@Phoenix Gang@dbl@. I can now search the @dre@Gang Headquarters|', '@dbl@ for the @dre@Shield of Arrav@dbl@.']
PHOENIX_OWN_HALF = ['@str@gave this Report to Straven and he allowed me to join the|@str@Phoenix Gang.|', '@dbl@I searched the @dre@Phoenix Gang Headquarters@dbl@ and found|what seems to be half of the @dre@Shield of Arrav@dbl@. I should|', '@dbl@see if a @dre@Fellow Adventurer@dbl@ can find the other @dre@Shield Half@dbl@|and take them both to the @dre@Curator@dbl@ in @dre@Varrock Museum|']
PHOENIX_BOTH_HALVES = ['@str@gave this Report to Straven and he allowed me to join the|@str@Phoenix Gang.|', '@dre@Fellow Adventurer@dbl@ also found a @dre@Shield Half@dbl@ and gave it to|me. I should take them both to the @dre@Curator@dbl@ in @dre@Varrock|']
PHOENIX_TWO_CERTS = ['@str@gave this Report to Straven and he allowed me to join the|@str@Phoenix Gang.|', '@dbl@who confirmed they were genuine. The @dre@Curator@dbl@ gave me|two @dre@Certificates@dbl@. I should now give one to a @dre@Fellow|', '@dre@Adventurer@dbl@ and take my @dre@Certificate@dbl@ to @dre@King Roald|@dbl@in @dre@Varrock Palace@dbl@ to collect my reward.']
TRAMP_TOLD = ['@str@To start this quest, I spoke to the Tramp in Varrock.|@str@He gave me the location of the Black Arm Gang HQ.|', '@dbl@He directed me to speak to @dre@Katrine@dbl@ in the @dre@gang HQ@dbl@.|']
KATRINE_TASK = ['@str@He directed me to speak to Katrine in the Gang|@str@Headquarters.|', '@dbl@I spoke to @dre@Katrine@dbl@ in the @dre@Black Arm Gang Headquarters.|@dbl@She offered to let me join the gang in return for|', '@dbl@stealing two @dre@Phoenix Crossbows@dbl@ from the @dre@Phoenix Gang.@dbl@|', '@dbl@I should seek help by asking a @dre@Fellow Adventurer@dbl@ to|infiltrate the Phoenix Gang@dbl@.|']
KATRINE_TASK_KEY_HELD = ['@dbl@stealing two @dre@Phoenix Crossbows@dbl@ from the @dre@Phoenix Gang.@dbl@|', "@dbl@With the help of a @dre@Fellow Adventurer@dbl@, I was able to obtain a|@dre@Key@dbl@ to the @dre@Phoenix Gang's Weapon Stash@dbl@ south east of|", '@dbl@the @dre@Blue Moon Inn@dbl@. I should now be able to steal the @dre@Crossbows|']
KATRINE_TASK_CROSSBOWS = ['@dbl@stealing two @dre@Phoenix Crossbows@dbl@ from the @dre@Phoenix Gang.@dbl@|', '@dbl@With the help of a @dre@Fellow Adventurer@dbl@, I was able to obtain|these @dre@Crossbows@dbl@. @dbl@I should now return them to @dre@Katrine@dbl@.|']
BLACKARM_JOINED = ['@dbl@allowed me to join the @dre@Black Arm Gang@dbl@. I can now search|the @dre@Gang Headquarters@dbl@ for the @dre@Shield of Arrav@dbl@.|']
COMPLETE = ['@str@and he rewarded me for helping to return the Shield of|@str@Arrav.||', '@red@QUEST COMPLETE!']

def _fn1():

    def _fn2():
        expect(parse_shield_of_arrav_journal([])).to_be_undefined()
        expect(parse_shield_of_arrav_journal(['@dbl@'])).to_be_undefined()
    test('an unrendered page yields no progress', _fn2)

    def _fn3():
        expect(parse_shield_of_arrav_journal(NOT_STARTED).stage if parse_shield_of_arrav_journal(NOT_STARTED) is not None else None).to_be(SOA_STAGE.NOT_STARTED)
        expect(parse_shield_of_arrav_journal(TOLD_OF_BOOK).stage if parse_shield_of_arrav_journal(TOLD_OF_BOOK) is not None else None).to_be(SOA_STAGE.TOLD_OF_BOOK)
        expect(parse_shield_of_arrav_journal(READ_BOOK).stage if parse_shield_of_arrav_journal(READ_BOOK) is not None else None).to_be(SOA_STAGE.READ_BOOK)
        expect(parse_shield_of_arrav_journal(SENT_TO_BARAEK).stage if parse_shield_of_arrav_journal(SENT_TO_BARAEK) is not None else None).to_be(SOA_STAGE.SENT_TO_BARAEK)
        expect(parse_shield_of_arrav_journal(FIND_STRAVEN).stage if parse_shield_of_arrav_journal(FIND_STRAVEN) is not None else None).to_be(SOA_STAGE.FIND_STRAVEN)
        expect(parse_shield_of_arrav_journal(KILL_JONNY_NO_REPORT).stage if parse_shield_of_arrav_journal(KILL_JONNY_NO_REPORT) is not None else None).to_be(SOA_STAGE.KILL_JONNY)
        expect(parse_shield_of_arrav_journal(PHOENIX_JOINED_NO_HALF).stage if parse_shield_of_arrav_journal(PHOENIX_JOINED_NO_HALF) is not None else None).to_be(SOA_STAGE.PHOENIX_JOINED)
    test('phoenix stages read in order', _fn3)

    def _fn4():
        expect(parse_shield_of_arrav_journal(TRAMP_TOLD).stage if parse_shield_of_arrav_journal(TRAMP_TOLD) is not None else None).to_be(SOA_STAGE.TRAMP_TOLD)
        expect(parse_shield_of_arrav_journal(KATRINE_TASK).stage if parse_shield_of_arrav_journal(KATRINE_TASK) is not None else None).to_be(SOA_STAGE.KATRINE_TASK)
        expect(parse_shield_of_arrav_journal(BLACKARM_JOINED).stage if parse_shield_of_arrav_journal(BLACKARM_JOINED) is not None else None).to_be(SOA_STAGE.BLACKARM_JOINED)
    test('black arm stages read in order', _fn4)

    def _fn5():
        for page in [PHOENIX_JOINED_NO_HALF, PHOENIX_OWN_HALF, PHOENIX_BOTH_HALVES, PHOENIX_TWO_CERTS]:
            expect(parse_shield_of_arrav_journal(page).stage if parse_shield_of_arrav_journal(page) is not None else None).to_be(SOA_STAGE.PHOENIX_JOINED)
    test('every phoenix joined page reads as joined, whatever is carried', _fn5)

    def _fn6():
        for page in [KATRINE_TASK, KATRINE_TASK_KEY_HELD, KATRINE_TASK_CROSSBOWS]:
            expect(parse_shield_of_arrav_journal(page).stage if parse_shield_of_arrav_journal(page) is not None else None).to_be(SOA_STAGE.KATRINE_TASK)
    test('every katrine task page reads as the task, whatever is carried', _fn6)

    def _fn7():
        expect(parse_shield_of_arrav_journal(COMPLETE).stage if parse_shield_of_arrav_journal(COMPLETE) is not None else None).to_be(SOA_STAGE.COMPLETE)
    test('complete outranks every other needle on the page', _fn7)

    def _fn8():
        expect('report-held' in (parse_shield_of_arrav_journal(KILL_JONNY_NO_REPORT).flags if parse_shield_of_arrav_journal(KILL_JONNY_NO_REPORT) is not None else None)).to_be(False)
        expect('report-held' in (parse_shield_of_arrav_journal(KILL_JONNY_REPORT_HELD).flags if parse_shield_of_arrav_journal(KILL_JONNY_REPORT_HELD) is not None else None)).to_be(True)
    test('the report flag separates the two kill-jonny pages', _fn8)

    def _fn9():
        joined = ['@str@I confronted and killed Jonny the Beard in the Blue|@str@Moon Inn and took an Intelligence Report from him. I|', '@str@gave this Report to Straven and he allowed me to join the|@str@Phoenix Gang.|']
        expect('report-held' in (parse_shield_of_arrav_journal(joined).flags if parse_shield_of_arrav_journal(joined) is not None else None)).to_be(False)
    test('the struck-through killed-jonny line is not read as a held report once joined', _fn9)

    def _fn10():
        expect('key-held' in (parse_shield_of_arrav_journal(KATRINE_TASK).flags if parse_shield_of_arrav_journal(KATRINE_TASK) is not None else None)).to_be(False)
        expect('key-held' in (parse_shield_of_arrav_journal(KATRINE_TASK_KEY_HELD).flags if parse_shield_of_arrav_journal(KATRINE_TASK_KEY_HELD) is not None else None)).to_be(True)
        expect('crossbows-held' in (parse_shield_of_arrav_journal(KATRINE_TASK_CROSSBOWS).flags if parse_shield_of_arrav_journal(KATRINE_TASK_CROSSBOWS) is not None else None)).to_be(True)
    test('the key and crossbow flags separate the three katrine-task pages', _fn10)

    def _fn11():
        expect(len(parse_shield_of_arrav_journal(PHOENIX_JOINED_NO_HALF).flags if parse_shield_of_arrav_journal(PHOENIX_JOINED_NO_HALF) is not None else None)).to_be(0)
        expect('own-half-only' in (parse_shield_of_arrav_journal(PHOENIX_OWN_HALF).flags if parse_shield_of_arrav_journal(PHOENIX_OWN_HALF) is not None else None)).to_be(True)
        expect('both-halves' in (parse_shield_of_arrav_journal(PHOENIX_BOTH_HALVES).flags if parse_shield_of_arrav_journal(PHOENIX_BOTH_HALVES) is not None else None)).to_be(True)
        expect('two-certificates' in (parse_shield_of_arrav_journal(PHOENIX_TWO_CERTS).flags if parse_shield_of_arrav_journal(PHOENIX_TWO_CERTS) is not None else None)).to_be(True)
    test('the half and certificate flags separate the four joined pages', _fn11)

    def _fn12():
        tagged = ['@dbl@stealing two @dre@Phoenix Crossbows@dbl@ from the @dre@Phoenix Gang.@dbl@|']
        expect(parse_shield_of_arrav_journal(tagged).stage if parse_shield_of_arrav_journal(tagged) is not None else None).to_be(SOA_STAGE.KATRINE_TASK)
    test('a colour tag next to punctuation does not split a needle', _fn12)
describe('arrav journal', _fn1)

def snapshot_fields(**fields):
    for name in ['inv', 'inv_ids', 'bank', 'bank_ids']:
        if isinstance(fields.get(name), (Record, Fake)):
            fields[name] = fields[name]._fields
    return QuestSnapshot(**fields)
