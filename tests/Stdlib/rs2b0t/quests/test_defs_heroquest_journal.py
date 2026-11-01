"""Ported from rs2b0t's test/api/ai/quests/defs/heroquest-journal.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.quests.defs.heroquest.journal import HERO_STAGE, parse_hero_quest_journal

def _flat(blocks):
    out = []
    for block in blocks:
        out.extend(block)
    return out


NOT_STARTED = [
    '@dbl@I can start this quest by speaking to @dre@Achietties@dbl@ at the|',
    "@dbl@entrance to the @dre@Heroes' Guild@dbl@ in @dre@Burthorpe@dbl@.",
]
HEADER = ["@dre@Achietties@dbl@ will let me into the @dre@Heroes' Guild@dbl@ if I can get:|"]
NO_FEATHER = [
    '@dbl@1) An @dre@Entranan firebird feather@dbl@.|',
    '@dbl@I should check if anyone important on @dre@Entrana@dbl@ knows|',
    '@dbl@where I can find an Entrana firebird.|',
]
HAVE_FEATHER = [
    '@str@1) An Entranan firebird feather - I now have one!|',
    '@str@The high priest on Entrana confirmed that a firebird exists|',
]
NO_EEL = ['@dbl@2) A @dre@cooked lava eel.|', '@dbl@I should speak to a @dre@fishing expert@dbl@.|']
HAVE_EEL = ['@str@2) A cooked lava eel - I now have one!|']
NO_ARMBAND = ["@dbl@3) A @dre@master thief's armband.|"]
HAVE_ARMBAND = ["@str@3) A master thief's armband - I now have one!|"]
PHOENIX_INTRO = [
    '@dbl@I worked with the @dre@Phoenix Gang@dbl@ when I was searching for the|',
    '@dre@Shield of Arrav@dbl@. I should visit their hideout, maybe they can|',
    '@dbl@help me.|',
]
SPOKE_STRAVEN = ['@str@I spoke to Straven about the Master Thieves Armband.|']
TOLD_ALFONSE = ["@str@Then I told Alfonse the password 'Gherkin'.|"]
CHARLIE_DOOR = [
    "@str@Charlie told me about a secret door into Scarface Pete's|",
    "@str@hideout, but he couldn't find a way of getting through it.|",
]
RIVAL_COLLECTED = [
    '@str@A rival gang member collected a candlestick for me after I|',
    '@str@killed Grip and got the Treasure Room key for them.|',
]
SPOKE_KATRINE = [
    "@str@I spoke to Katrine about the master thief's armband. She|",
    "@str@told me I can get one by stealing one of Pete's candlesticks.|",
]
USED_PASSWORD = [
    '@str@I used the Black Arm password to enter the Brimhaven Black|',
    '@str@Arm hideout, south-east of the Shrimp and Parrot.|',
]
TROBERT_PAPERS = [
    '@str@Trobert, the Brimhaven Black Arm leader, told me that the|',
    "@str@key to the treasure room is carried by Grip, Scarface Pete's|",
    "@str@head guard. He provided me with the ID papers of Grip's new|",
    "@str@deputy, a deserter from the Black Knight's Fortress.|",
]
PASSED_AS_HARTIGEN = [
    '@str@I managed to pass myself off as Hartigen the Black|',
    "@str@Knight and enter Scarface Pete's mansion.|",
]
PRESENTED_TO_GRIP = ['@str@I presented myself to Grip, who has the key to the|', '@str@treasure room.|']
HELPED_BY_PHOENIX = [
    '@str@With the help of a Phoenix Gang member who killed Grip|',
    '@str@for me, I managed to get a candlestick from the chest in|',
    "@str@the treasure room of Scarface Pete's mansion.|",
]


def page(*blocks):
    return list(HEADER) + list(NO_FEATHER) + list(NO_EEL) + list(NO_ARMBAND) + _flat(blocks)


def _fn1():
    def _fn2():
        expect((parse_hero_quest_journal(NOT_STARTED).stage if parse_hero_quest_journal(NOT_STARTED) is not None else None)).to_be(HERO_STAGE.NOT_STARTED)
    test('the opening page is the not-started page', _fn2)

    def _fn3():
        expect((parse_hero_quest_journal(page(PHOENIX_INTRO)).stage if parse_hero_quest_journal(page(PHOENIX_INTRO)) is not None else None)).to_be(HERO_STAGE.STARTED)
    test('started, before Straven, is the gang intro alone', _fn3)

    def _fn4():
        lines = page(PHOENIX_INTRO, SPOKE_STRAVEN, [
        "@dbl@He told me that I can get one by stealing @dre@Pete's Candlestick|",
        '@dbl@I should use the password he gave me at @dre@Brimhaven',
    ])
        expect((parse_hero_quest_journal(lines).stage if parse_hero_quest_journal(lines) is not None else None)).to_be(HERO_STAGE.PHOENIX_SPOKEN)
    test('Straven names the Brimhaven password', _fn4)

    def _fn5():
        lines = page(PHOENIX_INTRO, SPOKE_STRAVEN, TOLD_ALFONSE, ['@dbl@He said I should speak to @dre@Charlie@dbl@ round the back'])
        expect((parse_hero_quest_journal(lines).stage if parse_hero_quest_journal(lines) is not None else None)).to_be(HERO_STAGE.PHOENIX_ALFONSE)
    test('Alfonse sends you round the back', _fn5)

    def _fn6():
        lines = page(PHOENIX_INTRO, SPOKE_STRAVEN, TOLD_ALFONSE, CHARLIE_DOOR, ['@dbl@Maybe @dre@another player@dbl@ can help me get through this @dre@door@dbl@?'])
        expect((parse_hero_quest_journal(lines).stage if parse_hero_quest_journal(lines) is not None else None)).to_be(HERO_STAGE.PHOENIX_CHARLIE)
    test('Charlie leaves the door as the open question', _fn6)

    def _fn7():
        lines = page(PHOENIX_INTRO, SPOKE_STRAVEN, TOLD_ALFONSE, CHARLIE_DOOR, RIVAL_COLLECTED, [
        '@dbl@As soon as they have given me my @dre@candlestick@dbl@ I should|',
        '@dbl@head back to @dre@Varrock@dbl@ and give it to @dre@Straven@dbl@ for my @dre@reward',
    ])
        expect((parse_hero_quest_journal(lines).stage if parse_hero_quest_journal(lines) is not None else None)).to_be(HERO_STAGE.PHOENIX_KILLED_GRIP)
    test('after the kill the page waits on the candlestick', _fn7)

    def _fn8():
        lines = list(HEADER) + list(NO_FEATHER) + list(NO_EEL) + list(HAVE_ARMBAND) + list(SPOKE_STRAVEN) + list(TOLD_ALFONSE) + list(CHARLIE_DOOR) + list(RIVAL_COLLECTED) + ["@str@I gave Straven Scarface Pete's candlestick, and in reward|", '@str@he gave me a Master Thieves Armband to prove my skills.|']
        progress = parse_hero_quest_journal(lines)
        expect((progress.stage if progress is not None else None)).to_be(HERO_STAGE.PHOENIX_ARMBAND)
        expect(('armband' in (progress.flags if progress is not None else None))).to_be(True)
    test('Straven hands the armband over', _fn8)


describe('parseHeroQuestJournal — Phoenix side', _fn1)


def _fn9():
    def _fn10():
        lines = page([
        '@dre@Katrine@dbl@ (the leader of the @dre@Black Arm Gang@dbl@ in @dre@south-west|',
        '@dre@Varrock@dbl@) can help me.',
    ])
        expect((parse_hero_quest_journal(lines).stage if parse_hero_quest_journal(lines) is not None else None)).to_be(HERO_STAGE.STARTED)
    test('started, before Katrine, names her as the contact', _fn10)

    def _fn11():
        lines = page(SPOKE_KATRINE, [
        '@dbl@I should say the password she gave me at @dbl@the @dre@Black|',
        "@dre@Arm hideout@dbl@ in @dre@Brimhaven@dbl@. @dbl@It's located @dre@south-east@dbl@ of|",
        '@dbl@the @dre@Shrimp and Parrot@dbl@.',
    ])
        expect((parse_hero_quest_journal(lines).stage if parse_hero_quest_journal(lines) is not None else None)).to_be(HERO_STAGE.BLACKARM_SPOKEN)
    test('Katrine names the Brimhaven password', _fn11)

    def _fn12():
        lines = page(SPOKE_KATRINE, USED_PASSWORD, ['@dbl@I should speak to other gang members in the hideout for', '@dbl@help.'])
        expect((parse_hero_quest_journal(lines).stage if parse_hero_quest_journal(lines) is not None else None)).to_be(HERO_STAGE.BLACKARM_HQ)
    test('inside the hideout the page points at the other gang members', _fn12)

    def _fn13():
        lines = page(SPOKE_KATRINE, USED_PASSWORD, TROBERT_PAPERS, [
        '@dbl@I need to disguise myself as @dre@Hartigen the Black Knight@dbl@ in|',
        "@dbl@order to get inside @dre@Scarface Pete's mansion.",
    ])
        expect((parse_hero_quest_journal(lines).stage if parse_hero_quest_journal(lines) is not None else None)).to_be(HERO_STAGE.BLACKARM_PAPERS)
    test('with the papers the page asks for the disguise', _fn13)

    def _fn14():
        lines = page(SPOKE_KATRINE, USED_PASSWORD, TROBERT_PAPERS, PASSED_AS_HARTIGEN, ['@dbl@Now I need to present myself to @dre@Grip@dbl@, the head guard.'])
        expect((parse_hero_quest_journal(lines).stage if parse_hero_quest_journal(lines) is not None else None)).to_be(HERO_STAGE.BLACKARM_MANSION)
    test('inside the mansion the page asks for Grip', _fn14)

    # Why: the struck-through "I presented myself to Grip" line is on every later page, and a needle
    # without the leading "need to" would read stage 10 for the rest of the quest.
    def _fn15():
        lines = page(SPOKE_KATRINE, USED_PASSWORD, TROBERT_PAPERS, PASSED_AS_HARTIGEN, PRESENTED_TO_GRIP, [
        "@dbl@I can move around the hideout, but now I need @dre@Grip's key|",
        '@dbl@ to get into the @dre@treasure room@dbl@ and get the @dre@candlestick@dbl@.|',
        '@dbl@Maybe @dre@another player@dbl@ can help me discreetly defeat @dre@Grip@dbl@?|',
    ])
        expect((parse_hero_quest_journal(lines).stage if parse_hero_quest_journal(lines) is not None else None)).to_be(HERO_STAGE.BLACKARM_PAPERS_GIVEN)
    test('after the papers the page waits on the key', _fn15)

    def _fn16():
        lines = page(SPOKE_KATRINE, USED_PASSWORD, TROBERT_PAPERS, PASSED_AS_HARTIGEN, PRESENTED_TO_GRIP, HELPED_BY_PHOENIX, [
        '@dbl@After rewarding the player who assisted me, I should take|',
        "@dre@the Pete's candlestick@dbl@ to @dre@Katrine@dbl@ for my @dre@master thief's|",
        '@dre@armband@dbl@.|',
    ])
        expect((parse_hero_quest_journal(lines).stage if parse_hero_quest_journal(lines) is not None else None)).to_be(HERO_STAGE.BLACKARM_LOOTED)
    test('after the chest the page owes the rival a candlestick', _fn16)

    def _fn17():
        lines = list(HEADER) + list(NO_FEATHER) + list(NO_EEL) + list(HAVE_ARMBAND) + list(SPOKE_KATRINE) + list(USED_PASSWORD) + list(TROBERT_PAPERS) + list(PASSED_AS_HARTIGEN) + list(PRESENTED_TO_GRIP) + list(HELPED_BY_PHOENIX) + ["@str@I gave Scarface Pete's candlestick to Katrine, and in|", "@str@reward she gave me a master thief's armband.|"]
        expect((parse_hero_quest_journal(lines).stage if parse_hero_quest_journal(lines) is not None else None)).to_be(HERO_STAGE.BLACKARM_ARMBAND)
    test('Katrine hands the armband over', _fn17)


describe('parseHeroQuestJournal — Black Arm side', _fn9)


def _fn18():
    def _fn19():
        lines = [
        '@str@I gave Achietties an Entranan firebird feather, a cooked|',
        '@str@lava eel from a dangerous fishing spot and (after some|',
        "@str@difficulty) a master thief's armband, and proved myself|",
        "@str@worthy of entrance to the Heroes' Guild.|",
        '@dre@QUEST COMPLETE!',
    ]
        expect((parse_hero_quest_journal(lines).stage if parse_hero_quest_journal(lines) is not None else None)).to_be(HERO_STAGE.COMPLETE)
    test('the completed page is complete', _fn19)

    def _fn20():
        lines = list(HEADER) + list(HAVE_FEATHER) + list(HAVE_EEL) + list(HAVE_ARMBAND) + list(SPOKE_KATRINE) + list(USED_PASSWORD) + list(TROBERT_PAPERS) + list(PASSED_AS_HARTIGEN) + list(PRESENTED_TO_GRIP) + list(HELPED_BY_PHOENIX) + ["@str@I gave Scarface Pete's candlestick to Katrine, and in|", "@str@reward she gave me a master thief's armband.|", '@dbl@I have @dre@all required items@dbl@. I should give them to @dre@Achietties@dbl@ at|', "@dbl@the entrance to the @dre@Heroes' Guild@dbl@ in @dre@Burthorpe@dbl@."]
        progress = parse_hero_quest_journal(lines)
        _v21 = (progress.flags if progress is not None else None)
        expect(sorted(list(((_v21 if _v21 is not None else []))))).to_equal(['armband', 'eel', 'feather', 'ready-to-hand-in'])
    test('each held item raises its own flag', _fn20)

    def _fn22():
        expect(parse_hero_quest_journal([])).to_be_undefined()
        expect(parse_hero_quest_journal(['@dbl@something else entirely'])).to_be_undefined()
    test('an unreadable page is not a stage', _fn22)


describe('parseHeroQuestJournal — items and completion', _fn18)
