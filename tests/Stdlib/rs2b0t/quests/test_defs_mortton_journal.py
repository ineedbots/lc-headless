"""rs2b0t's test/api/ai/quests/defs/mortton-journal.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs.record import Record
from rs2004.quests.defs.mortton.areas import SM_STAGE
from rs2004.quests.defs.mortton.journal import parse_mortton_journal

HISTORY = Record({
    'read_diary': "@str@I can start this quest by exploring the town of Mort'ton|@str@which is accessible from the southern edge of Mort Myre.|",
    'made_serum': "@str@I made my way down through Mort Myre and found the town|@str@of Mort'ton. I discovered a diary which had some notes on|@str@a special serum in it. I made the serum.|",
    'kill_shades': "@str@I made serum 207 from tarromin, water and ashes by using|@str@Herbi Flax's diary. I wonder what the serum is used for?|" + "@str@I used the serum on a local NPC and I've been able to ask|@str@a few questions about the place.|" + '@str@I talked to Razmire Keelgan and he asked me to kill five|@str@shades for him. He seems to hate them!|',
    'to_razmire': "@str@I've killed five shades and showed the remains to Razmire.|@str@Razmire told me to show the remains to Ulsquire.|",
    'to_ulsquire': '@str@I showed Ulsquire the shade remains and he gave me some|@str@information which may be useful.|',
    'rebuild': "@str@Ulsquire seems to know a lot about this area, he's quite|@str@interested in 'Flaemtaer temple' and wishes he could|@str@rebuild it.|",
    'can_light': '@str@I helped rebuild the temple using limestone bricks, wooden|@str@planks and nails.|',
    'sacred_oil': '@str@When all of the temple walls were rebuilt, a fire altar|@str@appeared. The flame from the altar was sacred.|@str@I placed a flask of olive oil in the flame and it became|@str@sacred oil.|',
    'pyre_logs': '@str@I used sacred oil on logs turning them into pyre logs.|',
    'on_pyre': '@str@I placed some pyre logs onto a funeral pyre.|',
    'lit_pyre': '@str@I placed the shade remains on the pyre and set it on fire in|@str@order to put the Shades to rest.|',
})
NOT_STARTED = "@dbl@I can start this quest by exploring the town of @dre@Mort'ton@dbl@ which is accessible from the southern edge of @dre@Mort Myre@dbl@."


def page(history, current):
    return history + current


def _fn1():
    def _fn2():
        expect(parse_mortton_journal(NOT_STARTED)).to_be(SM_STAGE.NOT_STARTED)
    test('an unstarted quest', _fn2)

    def _fn3():
        text = page(HISTORY.read_diary, "@dbl@I made my way down through @dre@Mort Myre@dbl@ and I found the town of @dre@Mort'ton@dbl@. I've found a @dre@diary@dbl@ which has some interesting @dre@notes@dbl@ in it. Perhaps this can help me?")
        expect(parse_mortton_journal(text)).to_be(SM_STAGE.READ_DIARY)
    test('the diary has been read', _fn3)

    def _fn4():
        text = page(HISTORY.read_diary + HISTORY.made_serum, "@dbl@I made @dre@serum 207@dbl@ from tarromin, water and ashes by using @dre@Herbi Flax's@dbl@ diary. I wonder what the @dre@serum@dbl@ is used for?")
        expect(parse_mortton_journal(text)).to_be(SM_STAGE.MADE_SERUM)
    test('the serum is brewed but unused', _fn4)

    def _fn5():
        text = page(HISTORY.read_diary + HISTORY.made_serum, "@str@I made serum 207 from tarromin, water and ashes by|@str@using Herbi Flax's diary. I wonder what the serum is used|@str@for?|" + "@dbl@I used the @dre@serum@dbl@ on a local NPC and I've been able to ask a few questions about the place.")
        expect(parse_mortton_journal(text)).to_be(SM_STAGE.MADE_SERUM)
    test('the serum has been used on a villager', _fn5)

    def _fn6():
        base = HISTORY.read_diary + HISTORY.made_serum + HISTORY.kill_shades
        counted = [
        ['@dbl@I have to kill @dre@five@dbl@ shades.', SM_STAGE.KILL_SHADES],
        ["@dbl@I've killed @dre@one@dbl@ shade, I need to kill another @dre@four@dbl@.", SM_STAGE.KILLED_1],
        ["@dbl@I've killed @dre@two@dbl@ shades, I need to kill another @dre@three@dbl@.", SM_STAGE.KILLED_2],
        ["@dbl@I've killed @dre@three@dbl@ shades, I need to kill another @dre@two@dbl@.", SM_STAGE.KILLED_3],
        ["@dbl@I've killed @dre@four@dbl@ shades, I need to kill another @dre@one@dbl@.", SM_STAGE.KILLED_4],
        [
        "@dbl@I've killed all @dre@five shades@dbl@, I should return to @dre@Razmire@dbl@ now.",
        SM_STAGE.KILLED_5,
    ],
    ]
        for current, stage in counted:
            expect(parse_mortton_journal(page(base, current))).to_be(stage)
    test('the shade hunt counts up', _fn6)

    def _fn7():
        text = page(HISTORY.read_diary + HISTORY.made_serum + HISTORY.kill_shades + HISTORY.to_razmire, '@dbl@I should show the @dre@shade@dbl@ remains to @dre@Ulsquire@dbl@.')
        expect(parse_mortton_journal(text)).to_be(SM_STAGE.SHADES_TO_RAZMIRE)
    test('the remains are owed to Ulsquire', _fn7)

    def _fn8():
        text = page(HISTORY.read_diary + HISTORY.made_serum + HISTORY.kill_shades + HISTORY.to_razmire + HISTORY.to_ulsquire, '@dre@Ulsquire@dbl@ seems to know a lot about this area, maybe if I @dre@investigate@dbl@ around here a little more I can help the locals.')
        expect(parse_mortton_journal(text)).to_be(SM_STAGE.SHADES_TO_ULSQUIRE)
    test('Ulsquire has studied the remains', _fn8)

    def _fn9():
        text = page(HISTORY.read_diary + HISTORY.made_serum + HISTORY.kill_shades + HISTORY.to_razmire + HISTORY.to_ulsquire, "@dre@Ulsquire@dbl@ seems to know a lot about this area, he's quite interested in @dre@'Flaemtaer temple'@dbl@ and wishes he could rebuild it.")
        expect(parse_mortton_journal(text)).to_be(SM_STAGE.ULSQUIRE_TEMPLE)
    test('the temple has been named', _fn9)

    def _fn10():
        text = page(HISTORY.read_diary + HISTORY.made_serum + HISTORY.kill_shades + HISTORY.to_razmire + HISTORY.to_ulsquire + HISTORY.rebuild, "@dbl@I've started @dre@rebuilding@dbl@ the @dre@temple@dbl@ using @dre@limestone bricks@dbl@, @dre@wooden planks@dbl@ and @dre@nails@dbl@. I wonder what @dre@power@dbl@ the @dre@temple@dbl@ has, if any?|")
        expect(parse_mortton_journal(text)).to_be(SM_STAGE.REBUILD_TEMPLE)
    test('the rebuild has started', _fn10)

    def _fn11():
        text = page(HISTORY.read_diary + HISTORY.made_serum + HISTORY.kill_shades + HISTORY.to_razmire + HISTORY.to_ulsquire + HISTORY.rebuild + HISTORY.can_light, '@dbl@There must be some way to make use of the @dre@altar@dbl@ that appears in the @dre@middle@dbl@ of the @dre@temple@dbl@.')
        expect(parse_mortton_journal(text)).to_be(SM_STAGE.CAN_LIGHT_ALTAR)
    test('the altar can be lit', _fn11)

    def _fn12():
        text = page(HISTORY.read_diary + HISTORY.made_serum + HISTORY.kill_shades + HISTORY.to_razmire + HISTORY.to_ulsquire + HISTORY.rebuild + HISTORY.can_light + HISTORY.sacred_oil, '@dre@Ulsquire@dbl@ said something about putting the @dre@Shades@dbl@ to rest by giving them a @dre@holy cremation@dbl@, maybe this @dre@oil@dbl@ can help?')
        expect(parse_mortton_journal(text)).to_be(SM_STAGE.CREATED_SACRED_OIL)
    test('the oil has been sanctified', _fn12)

    def _fn13():
        text = page(HISTORY.read_diary + HISTORY.made_serum + HISTORY.kill_shades + HISTORY.to_razmire + HISTORY.to_ulsquire + HISTORY.rebuild + HISTORY.can_light + HISTORY.sacred_oil + HISTORY.pyre_logs, '@dbl@I have some @dre@Shade@dbl@ remains and I have some @dre@pyre logs@dbl@, I can now try to put a @dre@shades@dbl@ spirit to rest.')
        expect(parse_mortton_journal(text)).to_be(SM_STAGE.CREATED_PYRE_LOGS)
    test('the pyre logs exist', _fn13)

    def _fn14():
        text = page(HISTORY.read_diary + HISTORY.made_serum + HISTORY.kill_shades + HISTORY.to_razmire + HISTORY.to_ulsquire + HISTORY.rebuild + HISTORY.can_light + HISTORY.sacred_oil + HISTORY.pyre_logs + HISTORY.on_pyre, '@dbl@I need to put the @dre@shade remains@dbl@ on the @dre@funeral pyre@dbl@ and then @dre@light@dbl@ it in order to put the@dre@ shade spirit@dbl@ to rest.')
        expect(parse_mortton_journal(text)).to_be(SM_STAGE.LOGS_ON_PYRE)
    test('the logs are on the pyre', _fn14)

    def _fn15():
        text = page(HISTORY.read_diary + HISTORY.made_serum + HISTORY.kill_shades + HISTORY.to_razmire + HISTORY.to_ulsquire + HISTORY.rebuild + HISTORY.can_light + HISTORY.sacred_oil + HISTORY.pyre_logs + HISTORY.on_pyre + HISTORY.lit_pyre, '@dbl@The @dre@shades spirit@dbl@ was released, I should tell @dre@Ulsquire@dbl@.')
        expect(parse_mortton_journal(text)).to_be(SM_STAGE.LIT_PYRE)
    test('the pyre is lit', _fn15)

    def _fn16():
        text = "@str@I travelled to the town of Mort'ton where the people had an|@str@affliction.|@red@QUEST COMPLETE!"
        expect(parse_mortton_journal(text)).to_be(SM_STAGE.COMPLETE)
    test('the completed page', _fn16)

    def _fn17():
        expect(parse_mortton_journal([])).to_be_undefined()
    test('an empty page is not a stage', _fn17)

    def _fn18():
        expect(parse_mortton_journal(['@dbl@I have to kill @dre@five@dbl@ shades.'])).to_be(SM_STAGE.KILL_SHADES)
    test('the page arrives as lines and reads the same', _fn18)


describe('mortton journal stages', _fn1)
