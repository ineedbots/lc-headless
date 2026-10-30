"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/seaslug.test.ts (MIT, see thirdparty/rs2b0t)."""


from rs2004.quests.defs.seaslug.areas import SS_OBJ, SS_TILE
from rs2004.quests.defs.seaslug import decide, seaslug, source_paste, torch_step
from rs2004.quests.defs.seaslug.journal import SS_STAGE, parse_sea_slug_journal
CAROLINE_LINE = '@str@I have spoken to Caroline and agreed to help.||'
PASTE_LINE = '@str@I gave Holgart the Swamp Paste and his boat is now|@str@ready to take me to the Fishing Platform.||'
KENNITH_LINE = "@str@I've found Kennith, he's hiding behind some boxes.||"
KENT_LINE = "@str@I've found Kent on a small island.||"
TORCH_LINE = '@str@I should find a way of lighting this damp torch.|'
SLUGS_LINE = "@dre@Kennith@dbl@ won't go near the @dre@Sea Slugs@dbl@.|I need to find another way to get him out."
OPENING_LINE = "@str@I've created an opening to let Kenneth escape.||"
DOWNSTAIRS_LINE = "@str@Kennith can't get downstairs without some help.||"
CRANE_LINE = "@str@I've used the Crane to lower Kennith into the boat.||"
PAGE = Obj({
    SS_STAGE.NOT_STARTED: '@dbl@I can start this quest by speaking to @dre@Caroline@dbl@ who is @dre@East of Ardougne||' + "@dbl@Requirements:|@dbl@You'll need level 30 @dre@Firemaking",
    SS_STAGE.STARTED: CAROLINE_LINE + "@dbl@I need to talk to @dre@Holgart@dbl@ He'll take me to the @dre@Fishing Platform@dbl@.||" + "@dbl@I need to get to the @dre@Fishing Platform@dbl@ and find out what's happened to @dre@Kent@dbl@ and @dre@Kennith@dbl@.",
    SS_STAGE.SPOKEN_HOLGART: CAROLINE_LINE + "@dbl@I've spoken to @dre@Holgart@dbl@, but his boat is broken.|He needs me to bring him some @dre@Swamp Paste@dbl@.||" + '@dbl@I can find @dre@Swamp Tar@dbl@ in the @dre@Swamp South of Lumbridge@dbl@.||',
    SS_STAGE.BOAT_REPAIRED: CAROLINE_LINE + PASTE_LINE + '@dbl@I need to find @dre@Kent@dbl@ and @dre@Kennith@dbl@.',
    SS_STAGE.SPOKEN_KENNITH: CAROLINE_LINE + PASTE_LINE + KENNITH_LINE + '@dbl@I need to find @dre@Kent.',
    SS_STAGE.SPOKEN_KENT: CAROLINE_LINE + PASTE_LINE + KENNITH_LINE + KENT_LINE + TORCH_LINE,
    SS_STAGE.LIT_TORCH: CAROLINE_LINE + PASTE_LINE + KENNITH_LINE + KENT_LINE + TORCH_LINE + SLUGS_LINE,
    SS_STAGE.KENNITH_NEED_ESCAPE: CAROLINE_LINE + PASTE_LINE + KENNITH_LINE + KENT_LINE + TORCH_LINE + OPENING_LINE + SLUGS_LINE,
    SS_STAGE.NEED_KENNITH_PATH: CAROLINE_LINE + PASTE_LINE + KENNITH_LINE + KENT_LINE + TORCH_LINE + OPENING_LINE + DOWNSTAIRS_LINE + SLUGS_LINE,
    SS_STAGE.SAVED_KENNITH: CAROLINE_LINE + PASTE_LINE + KENNITH_LINE + KENT_LINE + TORCH_LINE + OPENING_LINE + DOWNSTAIRS_LINE + CRANE_LINE + '@dbl@I need to take the boat back to shore and talk to @dre@Caroline@dbl@.',
    SS_STAGE.COMPLETE: CAROLINE_LINE + PASTE_LINE + KENNITH_LINE + KENT_LINE + TORCH_LINE + OPENING_LINE + DOWNSTAIRS_LINE + CRANE_LINE + "@str@I've spoken to Caroline and she thanked me for rescuing|@str@her family from the Sea Slugs.|@red@QUEST COMPLETE!",
})
PASTE_HELD = '@str@I have spoken to Caroline and agreed to help.||' + "@dbl@I need to take the @dre@Swamp Paste@dbl@ to @dre@Holgart@dbl@ He's near @dre@Caroline@dbl@, they're @dre@East of Ardougne@dbl@.||"
ON_SHORE = Obj({'x': 2716, 'z': 3302, 'level': 0})
ON_DECK = Obj({'x': 2782, 'z': 3276, 'level': 0})
UPPER_DECK = Obj({'x': 2784, 'z': 3286, 'level': 1})
ON_ISLAND = Obj({'x': 2797, 'z': 3320, 'level': 0})


def id_counts(ids):
    out = {}
    for id in ids:
        _v1 = out.get(id)
        out[id] = ((_v1 if _v1 is not None else 0)) + 1
    return out


def counts(names):
    out = {}
    for name in names:
        _v2 = out.get(name.lower())
        out[name.lower()] = ((_v2 if _v2 is not None else 0)) + 1
    return out


def snap(options=None):
    if options is None:
        options = Obj({})
    stage = (options.stage if options.stage is not None else SS_STAGE.STARTED)
    progress = (options.progress if 'progress' in options else Obj({'stage': stage, 'flags': set()}))
    return Obj({
        'journal': (options.journal if options.journal is not None else 'in_progress'),
        'inv': {},
        'inv_ids': id_counts((options.inv_ids if options.inv_ids is not None else [])),
        'worn': set(),
        'no_progress': 0,
        'bank_coins': 2000000,
        'stage': (progress.stage if progress is not None else None),
        'progress': progress,
        'bank': counts((options.bank if options.bank is not None else [])),
        'bank_known': (options.bank_known if options.bank_known is not None else True),
        'tile': ((options.tile if options.tile is not None else ON_SHORE)),
        'free_slots': 28,
    })


def custom_name(step):
    return (step.name if step.kind == 'custom' else None)


def _fn3():
    for stage, page in PAGE.items():
        def _fn4():
            expect((parse_sea_slug_journal(page).stage if parse_sea_slug_journal(page) is not None else None)).to_be(float(stage))
        test(f'reads the stage {stage} page back as stage {stage}', _fn4)

    def _fn5():
        expect((parse_sea_slug_journal(PASTE_HELD).stage if parse_sea_slug_journal(PASTE_HELD) is not None else None)).to_be(SS_STAGE.SPOKEN_HOLGART)
    test('reads the swamp-paste-in-hand variant as the same stage as the broken-boat one', _fn5)

    def _fn6():
        expect(('kennith-or-kent' in (parse_sea_slug_journal(PAGE[SS_STAGE.SPOKEN_KENNITH]).flags if parse_sea_slug_journal(PAGE[SS_STAGE.SPOKEN_KENNITH]) is not None else None))).to_be(True)
        expect(('panel-or-call' in (parse_sea_slug_journal(PAGE[SS_STAGE.KENNITH_NEED_ESCAPE]).flags if parse_sea_slug_journal(PAGE[SS_STAGE.KENNITH_NEED_ESCAPE]) is not None else None))).to_be(True)
    test('flags the pair of stages the scroll writes one page for', _fn6)

    def _fn7():
        _v8 = (parse_sea_slug_journal(PAGE[SS_STAGE.LIT_TORCH]).flags if parse_sea_slug_journal(PAGE[SS_STAGE.LIT_TORCH]) is not None else None)
        expect(list(((_v8 if _v8 is not None else [])))).to_equal([])
    test('leaves the unambiguous pages without a flag', _fn7)

    def _fn9():
        expect(parse_sea_slug_journal('some other quest entirely')).to_be_undefined()
    test('returns undefined for a page it cannot place', _fn9)


describe('Sea Slug journal parsing', _fn3)


def _fn10():
    def _fn11():
        expect(decide(snap(Obj({'journal': 'unknown'})))).to_equal(Obj({'kind': 'wait', 'reason': 'quest journal not loaded'}))
    test('waits while the quest list is still loading', _fn11)

    def _fn12():
        expect(decide(snap(Obj({'journal': 'complete'}))).kind).to_be('done')
    test('is done once the quest list turns green', _fn12)

    def _fn13():
        step = decide(snap(Obj({'journal': 'not_started'})))
        expect(step.kind == 'talk' and step.stop.npc).to_be('Caroline')
    test('opens with Caroline when the quest has not started', _fn13)

    def _fn14():
        expect(decide(snap(Obj({'progress': None}))).kind).to_be('wait')
    test('waits rather than guessing when the journal stage is unavailable', _fn14)

    def _fn15():
        step = decide(snap(Obj({'stage': SS_STAGE.STARTED})))
        expect(step.kind == 'talk' and step.stop.npc).to_be('Holgart')
    test('asks Holgart for the ride once Caroline has been spoken to', _fn15)

    def _fn16():
        expect(decide(snap(Obj({'stage': SS_STAGE.SPOKEN_HOLGART, 'bank_known': False}))).kind).to_be('scan_bank')
    test('reads the bank before believing it has no swamp paste', _fn16)

    def _fn17():
        step = decide(snap(Obj({'stage': SS_STAGE.SPOKEN_HOLGART, 'bank': ['Swamp paste']})))
        expect(step.kind == 'withdraw' and step.items[0]['name']).to_be('Swamp paste')
    test('takes banked swamp paste rather than walking to Port Khazard', _fn17)

    def _fn18():
        step = decide(snap(Obj({'stage': SS_STAGE.SPOKEN_HOLGART})))
        expect(step.kind).to_be('buy')
        expect(step.kind == 'buy' and step.item).to_be('Swamp paste')
        expect(step.kind == 'buy' and step.shop.anchor).to_be(SS_TILE.KHAZARD_SHOP)
    test('buys the swamp paste from the Khazard counter when nothing is banked', _fn18)

    def _fn19():
        step = decide(snap(Obj({'stage': SS_STAGE.SPOKEN_HOLGART, 'inv_ids': [SS_OBJ.SWAMP_PASTE]})))
        expect(step.kind == 'talk' and step.stop.npc).to_be('Holgart')
    test('hands the paste over once it is in the pack', _fn19)

    def _fn20():
        expect(custom_name(decide(snap(Obj({'stage': SS_STAGE.BOAT_REPAIRED}))))).to_be('call to Kennith behind the crates')
    test('calls to Kennith once the boat is repaired', _fn20)

    def _fn21():
        for stage in [SS_STAGE.SPOKEN_KENNITH, SS_STAGE.SAILED_KENT]:
            expect(custom_name(decide(snap(Obj({'stage': stage}))))).to_be('find Kent on the island')
    test('runs one leg for both of the stages the Kennith page covers', _fn21)

    def _fn22():
        step = decide(snap(Obj({'stage': SS_STAGE.SPOKEN_KENT})))
        expect(custom_name(step)).to_be('sail to the fishing platform')
    test('sails to the platform before hunting for a torch', _fn22)

    def _fn23():
        step = decide(snap(Obj({'stage': SS_STAGE.SPOKEN_KENT, 'tile': ON_DECK})))
        expect(step.kind == 'talk' and step.stop.npc).to_be('Bailey')
    test('asks Bailey for the torch on the deck', _fn23)

    def _fn24():
        step = decide(snap(Obj({'stage': SS_STAGE.SPOKEN_KENT, 'tile': ON_DECK, 'inv_ids': [SS_OBJ.TORCH_UNLIT]})))
        expect(step.kind == 'grab_ground' and step.item).to_be('Damp sticks')
    test('grabs the damp sticks before the glass', _fn24)

    def _fn25():
        step = decide(snap(Obj({'stage': SS_STAGE.SPOKEN_KENT, 'tile': ON_DECK, 'inv_ids': [SS_OBJ.TORCH_UNLIT, SS_OBJ.DAMP_STICKS]})))
        expect(step.kind == 'grab_ground' and step.item).to_be('Broken glass')
    test('grabs the broken glass once the sticks are held', _fn25)

    def _fn26():
        step = decide(snap(Obj({
        'stage': SS_STAGE.SPOKEN_KENT,
        'tile': ON_DECK,
        'inv_ids': [SS_OBJ.TORCH_UNLIT, SS_OBJ.DAMP_STICKS, SS_OBJ.BROKEN_GLASS],
    })))
        expect(step.kind).to_be('use_on')
        expect(step.kind == 'use_on' and step.item).to_be('Broken glass')
        expect(step.kind == 'use_on' and step.target).to_be('Damp sticks')
    test('dries the sticks with the glass rather than the other way round', _fn26)

    def _fn27():
        step = decide(snap(Obj({'stage': SS_STAGE.SPOKEN_KENT, 'tile': ON_DECK, 'inv_ids': [SS_OBJ.TORCH_UNLIT, SS_OBJ.DRY_STICKS]})))
        expect(custom_name(step)).to_be('rub the dry sticks together')
    test('rubs the dry sticks once they are dry', _fn27)

    def _fn28():
        step = decide(snap(Obj({'stage': SS_STAGE.SPOKEN_KENT, 'tile': ON_DECK, 'inv_ids': [SS_OBJ.TORCH_LIT, SS_OBJ.DRY_STICKS]})))
        expect(custom_name(step)).to_be('rub the dry sticks together')
    test('still rubs on stage 6 when the torch is already lit', _fn28)

    def _fn29():
        step = decide(snap(Obj({'stage': SS_STAGE.SPOKEN_KENT, 'tile': UPPER_DECK})))
        expect(custom_name(step)).to_be('climb down to the lower deck')
    test('climbs down before working the torch chain from the upper deck', _fn29)

    def _fn30():
        step = decide(snap(Obj({'stage': SS_STAGE.LIT_TORCH, 'tile': ON_DECK, 'inv_ids': [SS_OBJ.TORCH_LIT]})))
        expect(custom_name(step)).to_be('show Kennith the lit torch')
    test('shows Kennith the lit torch on stage 7', _fn30)

    def _fn31():
        step = decide(snap(Obj({'stage': SS_STAGE.LIT_TORCH, 'tile': ON_DECK, 'inv_ids': [SS_OBJ.TORCH_UNLIT]})))
        expect(step.kind == 'grab_ground' and step.item).to_be('Damp sticks')
    test('relights a torch that went out rather than climbing into the fishermen', _fn31)

    def _fn32():
        for stage in [SS_STAGE.KENNITH_NEED_ESCAPE, SS_STAGE.PANEL_OPENED]:
            step = decide(snap(Obj({'stage': stage, 'tile': ON_DECK, 'inv_ids': [SS_OBJ.TORCH_LIT]})))
            expect(custom_name(step)).to_be('kick the panel open and call Kennith through')
    test('runs one leg for both of the stages the opening page covers', _fn32)

    def _fn33():
        step = decide(snap(Obj({'stage': SS_STAGE.NEED_KENNITH_PATH, 'tile': UPPER_DECK, 'inv_ids': [SS_OBJ.TORCH_LIT]})))
        expect(custom_name(step)).to_be('swing the crane over to Kennith')
    test('swings the crane once Kennith is waiting for a way down', _fn33)

    def _fn34():
        step = decide(snap(Obj({'stage': SS_STAGE.NEED_KENNITH_PATH, 'tile': ON_DECK})))
        expect(step.kind).to_be('wait')
    test('stops rather than looping when stage 10 has no torch to climb with', _fn34)

    def _fn35():
        step = decide(snap(Obj({'stage': SS_STAGE.SAVED_KENNITH, 'tile': ON_DECK, 'inv_ids': [SS_OBJ.TORCH_LIT]})))
        expect(custom_name(step)).to_be('sail back to the Ardougne shore')
    test('sails home from the platform once Kennith is in the boat', _fn35)

    def _fn36():
        step = decide(snap(Obj({'stage': SS_STAGE.SAVED_KENNITH, 'tile': ON_ISLAND})))
        expect(custom_name(step)).to_be('sail back to the Ardougne shore')
    test('sails home from the island too, rather than walking at Caroline', _fn36)

    def _fn37():
        step = decide(snap(Obj({'stage': SS_STAGE.SAVED_KENNITH, 'tile': ON_SHORE})))
        expect(step.kind == 'talk' and step.stop.npc).to_be('Caroline')
    test('claims the reward from Caroline once ashore', _fn37)


describe('Sea Slug decide', _fn10)


def _fn38():
    def _fn39():
        expect(seaslug.record.requirements.skills).to_equal([Obj({'skill': 'firemaking', 'level': 30})])
    test('gates on the Firemaking the rub needs', _fn39)

    def _fn40():
        expect(seaslug.record.items).to_equal([])
    test('carries no bank list, so a resume past Holgart fetches no second paste', _fn40)

    def _fn41():
        for tool in ['torch', 'damp sticks', 'dry sticks', 'broken glass', 'swamp paste', 'coins']:
            expect(seaslug.tools).to_contain(tool)
    test('keeps every quest item off the deposit list', _fn41)

    def _fn42():
        expect(seaslug.bank).to_be(SS_TILE.BANK)
    test("banks in East Ardougne, the only bank on this quest's side of the map", _fn42)

    def _fn43():
        expect(source_paste(snap(Obj({'inv_ids': [SS_OBJ.SWAMP_PASTE]})))).to_be_null()
    test('sourcePaste stands down once the paste is carried', _fn43)

    def _fn44():
        expect(custom_name(torch_step(snap(Obj({'stage': SS_STAGE.SPOKEN_KENT}))))).to_be('sail to the fishing platform')
    test('torchStep sails first from anywhere off the platform', _fn44)


describe('Sea Slug module', _fn38)
