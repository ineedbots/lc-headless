"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/tribaltotem.test.ts (MIT, see thirdparty/rs2b0t)."""


from rs2004.quests.defs.tribaltotem import COMBINATION, LABEL_OBJ, TOTEM_OBJ, TOTEM_STAGE, decide, in_mansion, parse_tribal_totem_journal, tribaltotem
NOT_STARTED = '@dbl@I can start this quest by speaking to @dre@Kangai Mau@dbl@ in @dre@the Shrimp & Parrot@dbl@ restaurant in @dre@Brimhaven|' + '@dbl@To complete this quest I need:|@dre@Level 21 Thieving'
PREAMBLE = '@str@I agreed to help Kangai Mau on Brimhaven recover the|@str@tribal totem stolen from his village by Lord Handelmort.|'
SWAPPED = '@str@I found a package due for delivery to Lord Handelmort at|@str@the R.P.D.T. depot, and swapped the label for the Wizard|' + "@str@Cromperty's experimental teleport block.|"
STARTED = PREAMBLE + '@dbl@I need to get into @dre@Lord Handelmorts Mansion@dbl@ in @dre@Ardougne'
CRATE_MARKED = PREAMBLE + SWAPPED + '@dbl@I should get the @dre@R.P.D.T. men@dbl@ to deliver the crate now.'
CRATE_DELIVERED = PREAMBLE + SWAPPED + '@str@I got the R.P.D.T. men to deliver the teleport block.|' + '@dbl@I should get @dre@Wizard Cromperty@dbl@ to teleport me inside now.'
INSIDE = PREAMBLE + SWAPPED + '@str@I got the R.P.D.T. men to deliver the teleport block to Lord|@str@Handelmort and teleported myself inside.|'
LOCKED_OUT = INSIDE + '@dbl@I need to find the combination for the @dre@security door@dbl@.|'
COMBO_KNOWN = INSIDE + '@str@I worked out the combination for the door.|' + '@dbl@I should find the @dre@Tribal Totem@dbl@ and return it!'
CARRYING = INSIDE + '@str@I worked out the combination for the door.|' + '@dbl@I should take the @dre@tribal totem@dbl@ back to @dre@Kangai Mau in Brimhaven@dbl@ and claim my @dre@reward'
COMPLETE = PREAMBLE + SWAPPED + '@str@I got the R.P.D.T. men to deliver the teleport block to Lord|@str@Handelmort and teleported myself inside.|' + '@str@After bypassing the traps and security inside the|@str@mansion I was able to reclaim the totem, and take it|' + '@str@back to Kangai Mau, who rewarded me for all of my help.||@red@QUEST COMPLETE!'


def id_counts(ids):
    result = {}
    for id in ids:
        _v1 = result.get(id)
        result[id] = ((_v1 if _v1 is not None else 0)) + 1
    return result


def snap(options=None):
    if options is None:
        options = Obj({})
    progress = (options.progress if 'progress' in options else Obj({
        'stage': (options.stage if options.stage is not None else TOTEM_STAGE.STARTED),
        'flags': set((['combo'] if options.combo == True else [])),
    }))
    return Obj({
        'journal': (options.journal if options.journal is not None else 'in_progress'),
        'inv': {},
        'inv_ids': id_counts((options.inv_ids if options.inv_ids is not None else [])),
        'worn': set(),
        'no_progress': 0,
        'bank_coins': 2000000,
        'stage': (progress.stage if progress is not None else None),
        'progress': progress,
        'bank': {},
        'bank_known': True,
        'tile': (Obj({'x': 2638, 'z': 3321, 'level': 0}) if options.tile is None else options.tile),
        'free_slots': 28,
    })


def custom_name(step):
    return (step.name if step.kind == 'custom' else None)


def npc_name(step):
    return (step.stop.npc if step.kind == 'talk' else None)


def _fn2():
    def _fn3():
        expect((parse_tribal_totem_journal(NOT_STARTED).stage if parse_tribal_totem_journal(NOT_STARTED) is not None else None)).to_be(TOTEM_STAGE.NOT_STARTED)
    test('reads the not-started page as stage 0', _fn3)

    def _fn4():
        expect((parse_tribal_totem_journal(STARTED).stage if parse_tribal_totem_journal(STARTED) is not None else None)).to_be(TOTEM_STAGE.STARTED)
    test('reads the mansion hint as started', _fn4)

    def _fn5():
        expect((parse_tribal_totem_journal(CRATE_MARKED).stage if parse_tribal_totem_journal(CRATE_MARKED) is not None else None)).to_be(TOTEM_STAGE.CRATE_MARKED)
    test('reads the delivery prompt as the crate being relabelled', _fn5)

    def _fn6():
        expect((parse_tribal_totem_journal(CRATE_DELIVERED).stage if parse_tribal_totem_journal(CRATE_DELIVERED) is not None else None)).to_be(TOTEM_STAGE.CRATE_DELIVERED)
    test('reads the Cromperty prompt as the crate being delivered', _fn6)

    # Why: every page repeats the sentences above it, so a parser that tests the oldest line first pins the stage too low.
    def _fn7():
        expect((parse_tribal_totem_journal(CRATE_DELIVERED).stage if parse_tribal_totem_journal(CRATE_DELIVERED) is not None else None)).not_.to_be(TOTEM_STAGE.TELEPORTED)
        expect((parse_tribal_totem_journal(CRATE_MARKED).stage if parse_tribal_totem_journal(CRATE_MARKED) is not None else None)).not_.to_be(TOTEM_STAGE.CRATE_DELIVERED)
    test('the crate pages do not read as the teleport page', _fn7)

    def _fn8():
        progress = parse_tribal_totem_journal(LOCKED_OUT)
        expect((progress.stage if progress is not None else None)).to_be(TOTEM_STAGE.TELEPORTED)
        expect(('combo' in (progress.flags if progress is not None else None))).to_be(False)
    test('reads the teleported page with no combination flag while the door is unsolved', _fn8)

    def _fn9():
        expect(('combo' in (parse_tribal_totem_journal(COMBO_KNOWN).flags if parse_tribal_totem_journal(COMBO_KNOWN) is not None else None))).to_be(True)
        expect(('combo' in (parse_tribal_totem_journal(CARRYING).flags if parse_tribal_totem_journal(CARRYING) is not None else None))).to_be(True)
    test('flags the combination once the page says it was worked out', _fn9)

    def _fn10():
        expect((parse_tribal_totem_journal(COMPLETE).stage if parse_tribal_totem_journal(COMPLETE) is not None else None)).to_be(TOTEM_STAGE.COMPLETE)
    test('reads the finished page as complete', _fn10)

    def _fn11():
        expect(parse_tribal_totem_journal('some other quest entirely')).to_be_undefined()
    test('returns undefined for a page it cannot place', _fn11)


describe('Tribal Totem journal parsing', _fn2)


def _fn12():
    def _fn13():
        expect(in_mansion(Obj({'x': 2638, 'z': 3321, 'level': 0}))).to_be(True)
        expect(in_mansion(Obj({'x': 2631, 'z': 3325, 'level': 0}))).to_be(True)
        expect(in_mansion(Obj({'x': 2638, 'z': 3323, 'level': 1}))).to_be(True)
    test('the teleport landing, the stairs room and the upper floor are inside', _fn13)

    # Why: the porch is south of the inner door and open to the garden, so a bot standing in it needs teleporting rather than a walk to the stairs.
    def _fn14():
        expect(in_mansion(Obj({'x': 2635, 'z': 3321, 'level': 0}))).to_be(False)
        expect(in_mansion(Obj({'x': 2629, 'z': 3320, 'level': 0}))).to_be(False)
        expect(in_mansion(Obj({'x': 2640, 'z': 3320, 'level': 0}))).to_be(False)
        expect(in_mansion(Obj({'x': 2637, 'z': 3312, 'level': 0}))).to_be(False)
    test('the porch, the garden alcoves and the garden are outside', _fn14)

    def _fn15():
        expect(in_mansion(None)).to_be(False)
        expect(in_mansion(None)).to_be(False)
    test('a missing tile reads as outside', _fn15)


describe('Tribal Totem mansion boxes', _fn12)


def _fn16():
    def _fn17():
        expect(decide(snap(Obj({'journal': 'unknown'})))).to_equal(Obj({'kind': 'wait', 'reason': 'quest journal not loaded'}))
    test('waits while the quest list is still loading', _fn17)

    def _fn18():
        expect(decide(snap(Obj({'journal': 'complete'}))).kind).to_be('done')
    test('is done once the quest list turns green', _fn18)

    def _fn19():
        expect(npc_name(decide(snap(Obj({'journal': 'not_started'}))))).to_be('Kangai Mau')
    test('opens with Kangai Mau when the quest has not started', _fn19)

    def _fn20():
        expect(decide(snap(Obj({'progress': None}))).kind).to_be('wait')
    test('waits rather than guessing when the journal stage is unavailable', _fn20)

    def _fn21():
        expect(custom_name(decide(snap(Obj({'stage': TOTEM_STAGE.STARTED}))))).to_be('take the address label off the mansion crate')
    test('takes the address label before anything else once started', _fn21)

    def _fn22():
        step = decide(snap(Obj({'stage': TOTEM_STAGE.STARTED, 'inv_ids': [LABEL_OBJ]})))
        expect(custom_name(step)).to_be("relabel the crate bound for the Wizards' Tower")
    test('relabels the crate once the label is held', _fn22)

    def _fn23():
        expect(npc_name(decide(snap(Obj({'stage': TOTEM_STAGE.CRATE_MARKED}))))).to_be('RPDT employee')
    test('asks the R.P.D.T. to deliver once the crate is marked', _fn23)

    def _fn24():
        expect(npc_name(decide(snap(Obj({'stage': TOTEM_STAGE.CRATE_DELIVERED}))))).to_be('Wizard Cromperty')
    test('goes back to Cromperty for the ride in once the crate is delivered', _fn24)

    def _fn25():
        step = decide(snap(Obj({'stage': TOTEM_STAGE.TELEPORTED})))
        expect(custom_name(step)).to_be('work out the security door combination')
    test('works out the combination first when inside with the door unsolved', _fn25)

    def _fn26():
        step = decide(snap(Obj({'stage': TOTEM_STAGE.TELEPORTED, 'combo': True})))
        expect(custom_name(step)).to_be('take the totem from the mansion chest')
    test('goes for the chest once the combination is known', _fn26)

    # Why: nothing walks into the mansion, the inner door only opens outward, so a resume outside it has to be teleported back in.
    def _fn27():
        outside = snap(Obj({'stage': TOTEM_STAGE.TELEPORTED, 'combo': True, 'tile': Obj({'x': 2655, 'z': 3283, 'level': 0})}))
        expect(npc_name(decide(outside))).to_be('Wizard Cromperty')
    test('rides Cromperty back in when the teleported stage finds the bot outside', _fn27)

    def _fn28():
        step = decide(snap(Obj({'stage': TOTEM_STAGE.TELEPORTED, 'combo': True, 'inv_ids': [TOTEM_OBJ]})))
        expect(npc_name(step)).to_be('Kangai Mau')
    test('carries the totem straight back to Kangai Mau', _fn28)


describe('Tribal Totem decide', _fn16)


# Why: the issue asks for a quest that resumes from any point, and `decide()` being pure is what lets that be proved without a client.
def _fn29():
    STAGES = [TOTEM_STAGE.STARTED, TOTEM_STAGE.CRATE_MARKED, TOTEM_STAGE.CRATE_DELIVERED, TOTEM_STAGE.TELEPORTED]
    TILES = [
        Obj({'x': 2638, 'z': 3321, 'level': 0}),
        Obj({'x': 2638, 'z': 3323, 'level': 1}),
        Obj({'x': 2655, 'z': 3283, 'level': 0}),
        Obj({'x': 2791, 'z': 3182, 'level': 0}),
        Obj({'x': 2640, 'z': 9719, 'level': 0}),
    ]

    def _fn30():
        stuck = []
        for stage in STAGES:
            for combo in [False, True]:
                for held in [[], [LABEL_OBJ], [TOTEM_OBJ]]:
                    for tile in TILES:
                        step = decide(snap(Obj({'stage': stage, 'combo': combo, 'inv_ids': held, 'tile': tile})))
                        if step.kind == 'wait':
                            stuck.append(f'stage {stage} combo={combo} held=[{held}] at {tile.x},{tile.z},{tile.level}: {step.reason}')
        expect(stuck).to_equal([])
    test('every reachable state names a step rather than waiting', _fn30)

    def _fn31():
        sewers = snap(Obj({'stage': TOTEM_STAGE.TELEPORTED, 'combo': True, 'tile': Obj({'x': 2640, 'z': 9719, 'level': 0})}))
        expect(npc_name(decide(sewers))).to_be('Wizard Cromperty')
    test('a bot dumped in the sewers by the stairs trap rides Cromperty back in', _fn31)


describe('Tribal Totem resumability', _fn29)


def _fn32():
    def _fn33():
        expect(tribaltotem.record.items).to_equal([])
        expect(tribaltotem.record.requirements.skills).to_equal([Obj({'skill': 'thieving', 'level': 21})])
    test('needs 21 Thieving and no items', _fn33)

    def _fn34():
        for tool in ['address label', 'totem', 'coins']:
            expect(tribaltotem.tools).to_contain(tool)
    test('keeps the label, the totem and the ferry fare off the deposit list', _fn34)

    def _fn35():
        expect([tribaltotem.bank.x, tribaltotem.bank.z, tribaltotem.bank.level]).to_equal([2655, 3283, 0])
    test('banks in Ardougne East, the only bank on either side of the crossing', _fn35)

    def _fn36():
        expect(COMBINATION).to_be('KURT')
    test('spells the gardener-leaked combination', _fn36)


describe('Tribal Totem module', _fn32)
