"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/treegnome-journal.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.quests.defs.treegnome.journal import TG_STAGE, parse_tree_gnome_journal

NOT_STARTED = '@dbl@I can start this quest by speaking to @dre@Bolren@dbl@ at the center of the @dre@Tree Gnome maze@dbl@, West of @dre@Port Khazard' + '||@dbl@I need to be able to defeat a @dre@level 112 Warlord'
OPENING = '@str@I spoke to King Bolren who told me that one of their orbs of|@str@protection has been stolen by Khazard troops.'
MONTAI = '||@str@I spoke to Montai. The orb was in the Khazard stronghold|@str@North of the battlefield, but it was secure in there.'
LOGS = '||@str@I brought Montai logs to help fortify their defences.'
BALLISTA_READY = '|@str@Now their defences were secure, they were ready to use the|@str@Gnome Ballista to break through the enemy defences.'
TRACKERS = '||@str@I found the three trackers and used their coordinates to fire|@str@the ballista straight into the Khazard stronghold.'
BREACHED = '|@str@With the stronghold breached by ballista fire, I was able to|@str@make my way inside and recover the orb of protection.'
FIRST_ORB = '||@str@I returned the orb to King Bolren, but while I was busy getting|@str@it the Khazard troops invaded the village and stole the|@str@remaining two orbs before heading north.'
WARLORD = "||@str@After a fierce battle I defeated the warlord who'd stolen|@str@the orbs, and reclaimed them for the gnome people."
REWARDED = '||@str@I returned them to King Bolren, and was rewarded for all|@str@of my help to the Gnome people in recovering the orbs.'
COMPLETE = '||@red@QUEST COMPLETE!'


def page(*parts):
    return ''.join(parts)


def _fn1():
    def _fn2():
        expect((parse_tree_gnome_journal(NOT_STARTED).stage if parse_tree_gnome_journal(NOT_STARTED) is not None else None)).to_be(TG_STAGE.NOT_STARTED)
    test('reads the unopened page as not started', _fn2)

    def _fn3():
        expect((parse_tree_gnome_journal(page(OPENING, '||@dbl@Commander Montai@dbl@, @dre@North@dbl@ of the maze, can help me get it')).stage if parse_tree_gnome_journal(page(OPENING, '||@dbl@Commander Montai@dbl@, @dre@North@dbl@ of the maze, can help me get it')) is not None else None)).to_be(TG_STAGE.STARTED)
    test('reads the opening page as started', _fn3)

    def _fn4():
        expect((parse_tree_gnome_journal(page(OPENING, MONTAI, '||@dbl@I need to bring Montai @dre@logs')).stage if parse_tree_gnome_journal(page(OPENING, MONTAI, '||@dbl@I need to bring Montai @dre@logs')) is not None else None)).to_be(TG_STAGE.SPOKEN_MONTAI)
    test('reads Montai asking for wood as spoken to Montai', _fn4)

    def _fn5():
        expect((parse_tree_gnome_journal(page(OPENING, MONTAI, LOGS, '|@dbl@I should speak to @dre@Montai@dbl@ again')).stage if parse_tree_gnome_journal(page(OPENING, MONTAI, LOGS, '|@dbl@I should speak to @dre@Montai@dbl@ again')) is not None else None)).to_be(TG_STAGE.GAVE_LOGS)
    test('reads the handed-over logs as the logs stage', _fn5)

    def _fn6():
        expect((parse_tree_gnome_journal(page(OPENING, MONTAI, LOGS, BALLISTA_READY, '||@dbl@I need to head into the @dre@Battlefield')).stage if parse_tree_gnome_journal(page(OPENING, MONTAI, LOGS, BALLISTA_READY, '||@dbl@I need to head into the @dre@Battlefield')) is not None else None)).to_be(TG_STAGE.FINDING_TRACKERS)
    test('reads the ballista briefing as the tracker stage', _fn6)

    def _fn7():
        expect((parse_tree_gnome_journal(page(OPENING, MONTAI, LOGS, BALLISTA_READY, TRACKERS, '|@dbl@With the @dre@Khazard stronghold@dbl@ exposed')).stage if parse_tree_gnome_journal(page(OPENING, MONTAI, LOGS, BALLISTA_READY, TRACKERS, '|@dbl@With the @dre@Khazard stronghold@dbl@ exposed')) is not None else None)).to_be(TG_STAGE.BALLISTA_FIRED)
    test('reads the fired ballista as the breach stage', _fn7)

    def _fn8():
        expect((parse_tree_gnome_journal(page(OPENING, MONTAI, LOGS, BALLISTA_READY, TRACKERS, BREACHED, '||@dbl@I should return the @dre@orb')).stage if parse_tree_gnome_journal(page(OPENING, MONTAI, LOGS, BALLISTA_READY, TRACKERS, BREACHED, '||@dbl@I should return the @dre@orb')) is not None else None)).to_be(TG_STAGE.RETRIEVED_ORB)
    test('reads the recovered orb as the return stage', _fn8)

    def _fn9():
        expect((parse_tree_gnome_journal(page(OPENING, MONTAI, LOGS, BALLISTA_READY, TRACKERS, BREACHED, FIRST_ORB, '||@dbl@I should retrieve the @dre@two remaining orbs')).stage if parse_tree_gnome_journal(page(OPENING, MONTAI, LOGS, BALLISTA_READY, TRACKERS, BREACHED, FIRST_ORB, '||@dbl@I should retrieve the @dre@two remaining orbs')) is not None else None)).to_be(TG_STAGE.RETURNED_FIRST_ORB)
    test('reads the raided village as the warlord hunt', _fn9)

    def _fn10():
        expect((parse_tree_gnome_journal(page(OPENING, MONTAI, LOGS, BALLISTA_READY, TRACKERS, BREACHED, FIRST_ORB, WARLORD, '||@dbl@I should return them now')).stage if parse_tree_gnome_journal(page(OPENING, MONTAI, LOGS, BALLISTA_READY, TRACKERS, BREACHED, FIRST_ORB, WARLORD, '||@dbl@I should return them now')) is not None else None)).to_be(TG_STAGE.DEFEATED_WARLORD)
    test('reads the dead warlord as the hand-back stage', _fn10)

    def _fn11():
        expect((parse_tree_gnome_journal(page(OPENING, MONTAI, LOGS, BALLISTA_READY, TRACKERS, BREACHED, FIRST_ORB, WARLORD, REWARDED, COMPLETE)).stage if parse_tree_gnome_journal(page(OPENING, MONTAI, LOGS, BALLISTA_READY, TRACKERS, BREACHED, FIRST_ORB, WARLORD, REWARDED, COMPLETE)) is not None else None)).to_be(TG_STAGE.COMPLETE)
    test('reads the finished page as complete', _fn11)

    def _fn12():
        expect(parse_tree_gnome_journal('some other quest entirely')).to_be_undefined()
    test('returns undefined for a page it cannot place', _fn12)


describe('Tree Gnome Village journal parsing', _fn1)
