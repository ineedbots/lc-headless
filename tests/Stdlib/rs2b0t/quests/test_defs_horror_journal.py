"""Ported from rs2b0t's test/api/ai/quests/defs/horror-journal.test.ts (MIT, see thirdparty/rs2b0t)."""

import rs2004.quests.defs.horror.journal as hj
from rs2004.catalogs.record import Record
from rs2004.quests.defs.horror.areas import HD_STAGE
from rs2004.quests.defs.horror.journal import HD_FLAG, parse_horror_journal

NOT_STARTED = [
    'Close Window',
    '@dre@Horror from the Deep',
    '@dbl@I can start this quest by speaking to @dre@Larrissa@dbl@ at the',
    '@dbl@@dre@Lighthouse@dbl@ to the @dre@North@dbl@ of the @dre@Barbarian Outpost@dbl@.',
    '@dbl@@dbl@To complete this quest I need:',
    '@dbl@@dre@Level 35 agility',
    '@dre@Level 13 or higher magic will be an advantage',
    '@dre@I must also be able to defeat strong level 100 enemies',
]
# Why: `~quest_journal` word-wraps through `split_init` and re-emits the active tags per line, so `@str@@bla@` appears only in client output, never in horror_journal.rs2.
STARTED_NOTHING_DONE = [
    'Close Window',
    '@dre@Horror from the Deep',
    '@dbl@Larrissa is very worried about her boyfriend Jossik.',
    '@dbl@I need to @dre@repair the bridge@dbl@ leading to Rellekka.',
    '@dbl@I also need to get the @dre@lighthouse key@dbl@ from her cousin',
    '@dre@@dre@Gunnjorn@dbl@.',
]
STARTED_BRIDGE_AND_KEY = [
    'Close Window',
    '@dre@Horror from the Deep',
    '@dbl@Larrissa is very worried about her boyfriend Jossik.',
    '@str@@bla@I need to repair the bridge leading to Rellekka.',
    '@dbl@I also need to use the key I got from Gunnjorn to enter',
    '@dbl@@dbl@the lighthouse.',
]
BRIDGE_AND_KEY_DONE = [
    'Close Window',
    '@dre@Horror from the Deep',
    '@str@I repaired the bridge leading to Rellekka and got a key',
    '@str@from Gunnjorn so I could enter the lighthouse.',
]
INSIDE_LIGHTHOUSE = list(BRIDGE_AND_KEY_DONE) + ['@dbl@Now I need to find some way of @dre@fixing@dbl@ the @dre@lighthouse @dre@lamp@dbl@.']
INSIDE_PART_REPAIRED = list(BRIDGE_AND_KEY_DONE) + ['@str@I have fixed the lighthouse lens.', '@str@I have re-tarred the lighthouse torch.', '@dbl@Now I need to find some way of @dre@fixing@dbl@ the @dre@lighthouse @dre@lamp@dbl@.']
LIGHT_REPAIRED = list(BRIDGE_AND_KEY_DONE) + ['@str@I managed to repair the lighthouse light with some molten', '@str@glass, some swamp tar and a tinderbox.', '@dbl@I must @dre@search this place@dbl@ and find out what has happened to', "@dbl@@dbl@Larrissa's boyfriend @dre@Jossik@dbl@!"]
FOUND_JOSSIK = list(BRIDGE_AND_KEY_DONE) + ['@str@I managed to repair the lighthouse light with some molten', '@str@glass, some swamp tar and a tinderbox.', '@str@I found Jossik in an underground cavern, behind a strange', '@str@wall where he had been attacked by some sea @str@creatures.', '@dbl@I must defeat these sea monsters to save him!']
COMPLETE = [
    '@str@I travelled to an isolated lighthouse north of the Barbarian|',
    '@str@outpost, to find a Fremennik girl called Larrissa locked|',
    '@str@outside, and worried about her boyfriend Jossik.|',
    "@str@I recovered a spare key from Larrissa's cousin Gunnjorn and ",
    '@str@repaired the bridge to Rellekka with some planks.|',
    '@str@After I killed some strange sea monsters, I managed to|',
    '@str@get Jossik out of the cavern and back to the lighthouse.|||',
    '@red@QUEST COMPLETE!',
]


def _fn1():
    def _fn2():
        expect((parse_horror_journal(NOT_STARTED).stage if parse_horror_journal(NOT_STARTED) is not None else None)).to_be(HD_STAGE.NOT_STARTED)
    test('reads the not-started page', _fn2)

    def _fn3():
        progress = parse_horror_journal(STARTED_NOTHING_DONE)
        expect((progress.stage if progress is not None else None)).to_be(HD_STAGE.STARTED)
        expect((HD_FLAG.BRIDGE in (progress.flags if progress is not None else None))).to_be(False)
        expect((HD_FLAG.KEY in (progress.flags if progress is not None else None))).to_be(False)
    test('reads a freshly started quest', _fn3)

    def _fn4():
        # Both branches print the same sentence; only @str@ against @dbl@ says
        # whether it is struck out, so this flag is read before tags are stripped.
        progress = parse_horror_journal(STARTED_BRIDGE_AND_KEY)
        expect((progress.stage if progress is not None else None)).to_be(HD_STAGE.STARTED)
        expect((HD_FLAG.BRIDGE in (progress.flags if progress is not None else None))).to_be(True)
        expect((HD_FLAG.KEY in (progress.flags if progress is not None else None))).to_be(True)
    test('reads the bridge off the colour tag, not the words', _fn4)

    def _fn5():
        progress = parse_horror_journal(INSIDE_LIGHTHOUSE)
        expect((progress.stage if progress is not None else None)).to_be(HD_STAGE.ENTERED_LIGHTHOUSE)
        # The bridge line is gone by now, folded into one struck-out summary,
        # re-asserting it is what stops later stages reading it as unbuilt.
        expect((HD_FLAG.BRIDGE in (progress.flags if progress is not None else None))).to_be(True)
    test('reads the lighthouse stage', _fn5)

    def _fn6():
        progress = parse_horror_journal(INSIDE_PART_REPAIRED)
        expect((progress.stage if progress is not None else None)).to_be(HD_STAGE.ENTERED_LIGHTHOUSE)
        expect((HD_FLAG.GLASS in (progress.flags if progress is not None else None))).to_be(True)
        expect((HD_FLAG.TAR in (progress.flags if progress is not None else None))).to_be(True)
        expect((HD_FLAG.LIGHT in (progress.flags if progress is not None else None))).to_be(False)
    test('reads part-finished lamp work', _fn6)

    def _fn7():
        progress = parse_horror_journal(LIGHT_REPAIRED)
        expect((progress.stage if progress is not None else None)).to_be(HD_STAGE.REPAIRED_LIGHTHOUSE)
        expect((HD_FLAG.LIGHT in (progress.flags if progress is not None else None))).to_be(True)
    test('reads the repaired lighthouse', _fn7)

    def _fn8():
        expect((parse_horror_journal(FOUND_JOSSIK).stage if parse_horror_journal(FOUND_JOSSIK) is not None else None)).to_be(HD_STAGE.DEFEATED_DAGJR)
    test('reads the stage after the junior dies', _fn8)

    def _fn9():
        expect((parse_horror_journal(COMPLETE).stage if parse_horror_journal(COMPLETE) is not None else None)).to_be(HD_STAGE.COMPLETE)
    test('reads the completed page', _fn9)

    def _fn10():
        expect(parse_horror_journal(['@dbl@Something else entirely.'])).to_be_undefined()
    test('returns undefined for a page it does not recognise', _fn10)


describe('Horror from the Deep journal', _fn1)


def _reads_the_tags_off_the_open_page():
    """quests.journal's lines have lost their colour tags, as phase 17f's live run found: it read the bridge as unbuilt
    after building it, and went to mine for more nails."""
    page = [Record({'text': '@str@@bla@I need to repair the bridge leading to Rellekka.', 'visible': True}),
            Record({'text': '@dbl@Larrissa is very worried about her boyfriend Jossik.', 'visible': True}),
            Record({'text': 'hidden', 'visible': False})]

    def stripped(name):
        return ['I need to repair the bridge leading to Rellekka.', 'Larrissa is very worried about her boyfriend Jossik.']
        yield

    spy_on(hj.quests, 'status', returns='in_progress')
    spy_on(hj.quests, 'journal', impl=stripped)
    spy_on(hj.reader, 'modals', returns=Record({'main': 275}))
    spy_on(hj._core, 'get_interface', returns=page)
    spy_on(hj._core, 'close_interfaces', returns=None)
    spy_on(hj.execution, 'delay_ticks', impl=instant_ticks)
    progress = run_wait(hj.read_horror_progress())
    expect(HD_FLAG.BRIDGE in progress.flags).to_be(True)


test('the live read keeps the struck bridge line', _reads_the_tags_off_the_open_page)
