"""rs2b0t's test/api/ai/quests/defs/touristtrap.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

import json
from rs2004.catalogs.record import Record
from rs2004.execution import event_signal
from rs2004.messages import game_messages
from rs2004.quests.defs.touristtrap import TOURIST_TRAP_STAGE, decide, forge_bar_wasted_since, observe_tourist_trap, parse_tourist_trap_journal, run_surface_rescue_checkpoint, strict_tourist_trap_choice, tourist_trap_area, waterskin_doses
from rs2004.quests.engine.types import QuestSnapshot
from rs2004.quests.food import quest_food
from rs2004.quests.defs.touristtrap import ITEM, leave_camp

def tile(x, z, level=0):
    return (Record({'x': x, 'z': z, 'level': level}))


IRENA = tile(3303, 3113)
CAPTAIN = tile(3270, 3029)
CAMP_SURFACE = tile(3280, 3020)
CAMP_UPPER = tile(3280, 3020, 1)
MINE_ENTRANCE = tile(3279, 9420)
MINE_LOWER = tile(3303, 9415)
MINE_DEEP = tile(3302, 9466)
BEDABIN = tile(3171, 3025)
MAINLAND = tile(3200, 3200)
SURFACE_JAIL = tile(3285, 3034)
UNDERGROUND_JAIL = tile(3288, 9437)
DESERT_OUTFIT = ['Desert shirt', 'Desert robe', 'Desert boots']
SLAVE_OUTFIT = ["Slaves' shirt", 'Slave robe', 'Slave boots']
DESERT_WORN = list(DESERT_OUTFIT) + ['Bronze pickaxe']
SLAVE_WORN = list(SLAVE_OUTFIT) + ['Bronze pickaxe']


def count_map(entries=None):
    if entries is None:
        entries = []
    return {_k: _v for _k, _v in [[name.lower(), count] for name, count in entries]}


def snap(options=None):
    if options is None:
        options = Record({})
    inv = count_map(options.inv)
    has_charged_skin = any([((inv.get(name) if inv.get(name) is not None else 0)) > 0 for name in ['waterskin(4)', 'waterskin(3)', 'waterskin(2)', 'waterskin(1)']])
    skins = (options.skins if options.skins is not None else 0)
    if not has_charged_skin and skins > 0:
        inv['waterskin(4)'] = skins
    kebabs = (options.kebabs if options.kebabs is not None else 8)
    _v2 = inv.get('kebab')
    if ((_v2 if _v2 is not None else 0)) == 0 and kebabs > 0:
        inv['kebab'] = kebabs
    food = (options.food if options.food is not None else 8)
    _v3 = inv.get('trout')
    if ((_v3 if _v3 is not None else 0)) == 0 and food > 0:
        inv['trout'] = food
    coins = (options.coins if options.coins is not None else 200)
    _v4 = inv.get('coins')
    if ((_v4 if _v4 is not None else 0)) == 0 and coins > 0:
        inv['coins'] = coins
    return QuestSnapshot(**{
        'journal': (options.journal if options.journal is not None else 'in_progress'),
        'inv': inv,
        'worn': set([name.lower() for name in ((options.worn if options.worn is not None else []))]),
        'no_progress': 0,
        'bank_coins': 0,
        'stage': (options.stage if 'stage' in options.keys() else TOURIST_TRAP_STAGE.NOT_STARTED),
        'bank': count_map(options.bank),
        'bank_known': (options.bank_known if options.bank_known is not None else True),
        'tile': (options.tile if 'tile' in options.keys() else IRENA),
        'free_slots': (options.free_slots if options.free_slots is not None else 8),
    })


def _fn5():
    quest_food.name = 'Trout'
    event_signal.set_interrupt(None)


after_each(_fn5)


def custom_name(step):
    return (step.name if step.kind == 'custom' else None)


def camp_recovery(stage, upstairs):
    snapshot = snap(Record({'stage': stage, 'tile': CAMP_UPPER if upstairs else CAMP_SURFACE,
                            'inv': [[ITEM.METAL_KEY, 1], [ITEM.PLANS, 1], [ITEM.BAR, 1], [ITEM.FEATHER, 10], [ITEM.HAMMER, 1]],
                            'worn': SLAVE_WORN}))
    step = decide(snapshot)
    expect(step.kind).to_be('custom')
    expect(step.name).to_be('climb down before item recovery' if upstairs else 'leave the camp safely for item recovery')
    if not upstairs:
        expect(step.run).to_be(leave_camp)


test_each([[10, False], [10, True], [12, False], [12, True]])(
    'pineapple/plans stage %s uses the shared safe camp recovery, upstairs=%s', camp_recovery)


def classifies(world_tile, expected):
    def check():
        expect(tourist_trap_area(world_tile)).to_be(expected)
    return check


def decides(fixture):
    def check():
        expect(custom_name(decide(fixture.snapshot))).to_be(fixture.action)
    return check


def jailed(stage, cell, action):
    def check():
        expect(custom_name(decide(snap(Record({'stage': stage, 'tile': cell}))))).to_be(action)
    return check


def banks_expendables(stage):
    def check():
        step = decide(snap(Record({'stage': stage, 'tile': MAINLAND, 'inv': [['Shantay pass', 1], ['Kebab', 8]], 'free_slots': 0})))
        expect(step.kind).to_be('deposit')
    return check


def routes_rescue(stage, world_tile, inventory, free_slots, action):
    def check():
        expect(custom_name(decide(snap(Record({'stage': stage, 'tile': world_tile, 'inv': inventory, 'worn': SLAVE_WORN, 'free_slots': free_slots}))))).to_be(action)
    return check


def maps_journal(page, expected):
    def check():
        expect(parse_tourist_trap_journal(page)).to_be(expected)
    return check


def _fn6():
    fixtures = [
        [
        '@dbl@I can start this quest by speaking to @dre@Irena@dbl@ after I have|gone through the @dre@Shantay Pass, South of Al-Kharid.|',
        TOURIST_TRAP_STAGE.NOT_STARTED,
    ],
        [
        '@str@Irena was distraught that her daughter Ana had vanished|@str@somewhere in the desert, and I agreed to help find her.|@dbl@I need to head into @dre@the desert@dbl@ and search for @dre@Ana',
        TOURIST_TRAP_STAGE.STARTED,
    ],
        [
        "@str@I found some suspicious guards in the desert, who I think|@str@may know something about Ana's disappearance.|@dbl@I have a feeling @dre@Ana@dbl@ must be around here somewhere...",
        TOURIST_TRAP_STAGE.APPROACHED_CAPTAIN,
    ],
        [
        "@str@I've killed the Mercenary Captain, I found a metal key on his|@str@body.|@dbl@I believe that @dre@Ana@dbl@ may be inside a desert @dre@mining camp@dbl@. I|should try to find a way inside.",
        TOURIST_TRAP_STAGE.KILLED_CAPTAIN,
    ],
        [
        '@str@The key I took from the mercenary captain allowed me to|@str@gain access to the desert mining camp.|@dbl@I should look around this desert @dre@mining camp@dbl@ and see if I|can find @dre@Ana@dbl@. She could be anywhere.',
        TOURIST_TRAP_STAGE.ENTERED_CAMP,
    ],
        [
        "@str@I've found a slave who says he's going to escape. I've made|@str@a deal with the salve. If I can crack the locks on his|@str@chains, he'll trade me his slaves clothes for the desert|@str@robes. Hopefully, whenn I'm dressed in slaves clothes I'll|@str@be able to get deeper in to the mining cave system.|@dbl@I should try to undo the @dre@locks@dbl@ on the @dre@slave@dbl@ in @dre@east@dbl@ end of|the desert @dre@mining camp@dbl@.",
        TOURIST_TRAP_STAGE.SPOKEN_SLAVE,
    ],
        [
        '@str@I managed to pick the locks on the slaves chains. He|@str@seemed quite pleased.|@dbl@I need to trade my @dre@desert robes@dbl@ for the @dre@used slaves|clothes@dbl@. These will help me to move around clandestinely in|the underground mine area.',
        TOURIST_TRAP_STAGE.FREED_SLAVE,
    ],
        [
        "@str@I've managed to swap the desert robes for slave robes.|@dbl@I think I should head into the @dre@mine@dbl@ and look for @dre@Ana.",
        TOURIST_TRAP_STAGE.TRADED_CLOTHES,
    ],
        [
        "@str@I've managed to into the underground mine area and the|@str@guards haven't stopped me yet.|@dbl@I think I should head deeper into the @dre@mine@dbl@ and look for @dre@Ana.",
        TOURIST_TRAP_STAGE.ENTERED_MINE,
    ],
        [
        "@str@I tried to enter the mines but my way was blocked by a|@str@guard. I was sure I had to get deeper into the mines.|@dbl@I need to get the mine guard a @dre@'Tenti' pineapple@dbl@ somehow.",
        TOURIST_TRAP_STAGE.FINDING_PINEAPPLE,
    ],
        [
        "@dbl@I need to get the mine guard a @dre@'Tenti' pineapple@dbl@ somehow.|Al Shabim@dbl@ will give me a @dre@'Tenti' pineapple@dbl@ if I can steal the|@dre@plans@dbl@ for a @dre@new secret weapon@dbl@ for him",
        TOURIST_TRAP_STAGE.BEDABIN_KEY,
    ],
        [
        "|@str@I managed to distract captain Siad and have stolen the|@str@plans.|@dbl@I need to get the mine guard a @dre@'Tenti' pineapple@dbl@ somehow.|@dre@Al Shabim@dbl@ will give me a @dre@'Tenti' pineapple@dbl@ if I can steal the|@dre@plans@dbl@ for a @dre@new secret weapon@dbl@ for him",
        TOURIST_TRAP_STAGE.RETRIEVED_PLANS,
    ],
        [
        "@dbl@I need to get the mine guard a @dre@'Tenti' pineapple@dbl@ somehow.|@dre@Al Shabim@dbl@ will give me a @dre@'Tenti' pineapple@dbl@ if I make him a|@dre@prototype@dbl@ of the @dre@new secret throwing weapon.|@dbl@To make the weapon, I will need the following:-|@dre@Hammer|@dre@Feathers|@dre@Bronze bar|",
        TOURIST_TRAP_STAGE.SHOWN_PLANS,
    ],
        [
        "@dbl@I've made the prototype dart tip, I should now add|feathers to it.",
        TOURIST_TRAP_STAGE.MADE_DART_TIP,
    ],
        [
        "@dbl@I've made a @dre@prototype dart @dbl@, I should now take it to|@dre@Al Shabim@dbl@.",
        TOURIST_TRAP_STAGE.FINISHED_DART,
    ],
        [
        "@dbl@I need to get the mine guard a @dre@'Tenti' pineapple@dbl@ somehow.||@dbl@Now I have a @dre@pineapple@dbl@, I should take it to the @dre@guard@dbl@.",
        TOURIST_TRAP_STAGE.LEARNED_DARTS,
    ],
        [
        '@dre@Al Shabim@dbl@ gave me a @dre@Tenti pineapple@dbl@, but I seem to have|@dre@misplaced it@dbl@, perhaps I should get @dre@another one@dbl@?',
        TOURIST_TRAP_STAGE.LEARNED_DARTS,
    ],
        [
        '@str@After helping the Bedabin people get a new weapon, they|@str@gave me a pineapple which I used to bribe the mine guard|@str@into allowing me further access into the mines.|@dbl@I am sure @dre@Ana@dbl@ is down here somewhere...|I should find her.',
        TOURIST_TRAP_STAGE.GIVEN_PINEAPPLE,
    ],
        [
        '@dbl@I have to find some way of getting @dre@Ana@dbl@ out of here...',
        TOURIST_TRAP_STAGE.USED_MINE_CART,
    ],
        [
        '@str@I found Ana working as a slave in the mine. Luckily I had a|@str@cunning plan to get her out, and stuck her in a barrel.|@dbl@I need to get @dre@Ana@dbl@ (and her barrel) out of this mine camp!',
        TOURIST_TRAP_STAGE.RESCUE,
    ],
        [
        '@str@I managed to smuggle her out from under the noses of the|@str@mine guards, secure her in a barrel, and take a cart ride to|@str@freedom outside the mining camp.|@dbl@I should talk to @dre@Irena@dbl@ at the @dre@shantay pass@dbl@ for my @dre@reward.',
        TOURIST_TRAP_STAGE.REWARD,
    ],
        [
        '@str@I returned Ana to her mother Irena, who was so grateful|@str@for all of my help that she rewarded me with some training.||@dre@QUEST COMPLETE!',
        TOURIST_TRAP_STAGE.COMPLETE,
    ],
    ]
    for index in range(len(fixtures)):
        page, expected = fixtures[index]
        test(f'maps exact source journal fixture {index + 1} to stage {expected}', maps_journal(page, expected))

    def _fn8():
        cumulative = [
        '@dbl@I need to head into @dre@the desert@dbl@ and search for @dre@Ana',
        "@str@I've killed the Mercenary Captain, I found a metal key on his|@str@body.",
        "@str@I've managed to swap the desert robes for slave robes.",
        "@dbl@I've made a @dre@prototype dart @dbl@, I should now take it to|@dre@Al Shabim@dbl@.",
    ]
        expect(parse_tourist_trap_journal(cumulative)).to_be(TOURIST_TRAP_STAGE.FINISHED_DART)
    test('uses the newest milestone in a cumulative rendered journal', _fn8)

    def _fn9():
        expect(parse_tourist_trap_journal(['Tourist Trap', 'Loading…'])).to_be_undefined()
        expect(parse_tourist_trap_journal('I spoke to Captain Siad about some plans.')).to_be_undefined()
    test('does not silently infer a stage from unknown or partially loaded text', _fn9)


describe('Tourist Trap journal stage parsing', _fn6)


def _fn10():
    fixtures = [
        [tile(3284, 3032), 'surfaceJail'],
        [tile(3286, 3036), 'surfaceJail'],
        [tile(3283, 3032), 'surfaceJail'],
        [tile(3282, 3037), 'surfaceJail'],
        [tile(3279, 3038), 'surfaceJail'],
        [tile(3277, 3039), 'surfaceJail'],
        [tile(3275, 3040), 'surfaceJail'],
        [tile(3280, 3018), 'campSurface'],
        [tile(3287, 3036), 'campSurface'],
        [tile(3284, 3031), 'campSurface'],
        [tile(3284, 3037), 'campSurface'],
        [tile(3285, 9430), 'undergroundJail'],
        [tile(3295, 9443), 'mineDeep'],
        [tile(3288, 9431), 'undergroundJail'],
        [tile(3288, 9442), 'undergroundJail'],
        [tile(3282, 9437), 'mineEntrance'],
        [tile(3296, 9437), 'mineDeep'],
        [tile(3288, 9429), 'undergroundJail'],
        [tile(3288, 9444), 'undergroundJail'],
        [tile(3269, 9447), 'mineEntrance'],
        [tile(3274, 3011), 'campSurface'],
        [tile(3306, 3043), 'campSurface'],
        [tile(3274, 3011, 1), 'campUpper'],
        [tile(3306, 3043, 1), 'campUpper'],
        [tile(3303, 9415), 'mineLower'],
        [tile(3279, 9420), 'mineEntrance'],
        [tile(3292, 9423), 'mineLower'],
        [tile(3313, 9416), 'mineLower'],
        [tile(3303, 9427), 'mineLower'],
        [tile(3307, 9447), 'mineDeep'],
        [tile(3308, 9447), 'mineDeep'],
        [tile(3307, 9448), 'mineDeep'],
        [tile(3315, 9427), 'mineDeep'],
        [tile(3293, 9434), 'mineDeep'],
        [tile(3299, 9447), 'mineDeep'],
        [tile(3318, 9430), 'mineDeep'],
        [tile(3302, 9466), 'mineDeep'],
        [tile(3287, 9429), 'undergroundJail'],
        [tile(3288, 9446), 'undergroundJail'],
        [tile(3292, 9435), 'undergroundJail'],
        [tile(3286, 9444), 'undergroundJail'],
        [tile(3171, 3048), 'bedabinTent'],
        [tile(3169, 3045), 'bedabin'],
        [tile(3169, 3046), 'bedabinTent'],
        [tile(3150, 2990), 'bedabin'],
        [tile(3200, 3070), 'bedabin'],
        [tile(3300, 3109), 'irena'],
        [tile(3314, 3116), 'irena'],
        [tile(3288, 3117), 'shantayNorth'],
        [tile(3320, 3140), 'shantayNorth'],
        [tile(3250, 3050), 'desert'],
        [tile(3200, 3200), 'mainland'],
        [tile(3200, 3200, 1), 'unknown'],
    ]
    for world_tile, expected in fixtures:
        test(f'classifies ({world_tile.x}, {world_tile.z}, level {world_tile.level}) as {expected}', classifies(world_tile, expected))

    def _fn12():
        expect(tourist_trap_area(None)).to_be('unknown')
    test('returns unknown when the player tile is unavailable', _fn12)


describe('Tourist Trap area classification', _fn10)


def _fn13():
    def _fn14():
        expect(strict_tourist_trap_choice(['No thanks.', "  YES,   I'LL BEND THE BAR.  "], ["Yes, I'll bend the bar."])).to_be("  YES,   I'LL BEND THE BAR.  ")
    test('matches only an explicitly allowed option while normalizing case and whitespace', _fn14)

    def _fn15():
        expect(strict_tourist_trap_choice(['Yes, bend these bars for me.', 'No, leave the window alone.'], ["Yes, I'll bend the bar.", "Yes, I'll bend the bar again."])).to_be_null()
    test('returns no match for an unknown menu instead of guessing a plausible choice', _fn15)

    def _fn16():
        expect(strict_tourist_trap_choice(["Yes I'll bend the bar"], ["Yes, I'll bend the bar."])).to_be_null()
        expect(strict_tourist_trap_choice(["Yes, I'll bend"], ["Yes, I'll bend the bar."])).to_be_null()
    test('does not accept punctuation drift or a partial label', _fn16)

    def _fn17():
        expect(strict_tourist_trap_choice(["Yes, I'll trade.", "It's funny you should say that"], ["It's funny you should say that", "Yes, I'll trade."])).to_be("Yes, I'll trade.")
    test('returns the displayed option when several allowed labels are present', _fn17)


describe('Tourist Trap strict dialogue selector', _fn13)


def _fn18():
    prepared_inventory = [
        ['Coins', 1000],
        ['Kebab', 8],
        ['Desert shirt', 1],
        ['Desert robe', 1],
        ['Desert boots', 1],
        ['Bronze bar', 3],
        ['Feather', 50],
        ['Hammer', 1],
        ['Shantay pass', 1],
    ]
    spare_desert_outfit = [[name, 1] for name in DESERT_OUTFIT]
    cases = [Record({
        'name': 'stage 0 starts with Irena only after the complete loadout is ready and worn',
        'snapshot': snap(Record({'stage': 0, 'tile': IRENA, 'inv': prepared_inventory, 'worn': DESERT_WORN})),
        'action': 'start Tourist Trap with Irena',
    }), Record({
        'name': 'stage 1 challenges the captain from the desert',
        'snapshot': snap(Record({'stage': 1, 'tile': CAPTAIN, 'worn': DESERT_WORN})),
        'action': 'provoke the Mercenary Captain',
    }), Record({
        'name': 'stage 3 resumes through the dialogue-provoked solo fight',
        'snapshot': snap(Record({'stage': 3, 'tile': CAPTAIN, 'worn': DESERT_WORN})),
        'action': 'provoke and defeat the Mercenary Captain',
    }), Record({
        'name': 'stage 4 enters camp with the recovered metal key',
        'snapshot': snap(Record({'stage': 4, 'tile': CAPTAIN, 'inv': [['Metal key', 1]], 'worn': DESERT_WORN})),
        'action': 'unlock the desert mining camp',
    })] + list([(Record({
        'name': f'stage {stage} resumes the slave unlock/trade transaction',
        'snapshot': snap(Record({
        'stage': stage,
        'tile': CAMP_SURFACE,
        'inv': list(spare_desert_outfit) + [['Metal key', 1]],
        'worn': DESERT_WORN,
    })),
        'action': 'free the slave and trade the spare desert outfit',
    })) for stage in [5, 6, 7]]) + [Record({
        'name': 'stage 8 enters the mine in the complete slave disguise',
        'snapshot': snap(Record({'stage': 8, 'tile': CAMP_SURFACE, 'inv': [['Metal key', 1]], 'worn': SLAVE_WORN})),
        'action': 'open the slave-only mine doors',
    }), Record({
        'name': 'stage 9 asks the inner guard about the cave',
        'snapshot': snap(Record({'stage': 9, 'tile': MINE_ENTRANCE, 'worn': SLAVE_WORN})),
        'action': 'learn the cave guard wants a Tenti pineapple',
    }), Record({
        'name': 'stage 10 accepts the pineapple deal from Al Shabim',
        'snapshot': snap(Record({'stage': 10, 'tile': BEDABIN})),
        'action': "accept Al Shabim's pineapple deal",
    }), Record({
        'name': 'stage 11 uses the Bedobin key to recover the plans',
        'snapshot': snap(Record({'stage': 11, 'tile': CAMP_SURFACE, 'inv': [['Bedobin key', 1], ['Metal key', 1]], 'worn': DESERT_WORN})),
        'action': 'distract Captain Siad and steal the plans',
    }), Record({
        'name': 'stage 12 shows held technical plans to Al Shabim',
        'snapshot': snap(Record({
        'stage': 12,
        'tile': BEDABIN,
        'inv': [['Technical plans', 1], ['Bronze bar', 1], ['Feather', 10], ['Hammer', 1]],
    })),
        'action': 'show the technical plans to Al Shabim',
    }), Record({
        'name': 'stage 13 forges a tip when the plans, hammer, and bar are held',
        'snapshot': snap(Record({'stage': 13, 'tile': BEDABIN, 'inv': [['Technical plans', 1], ['Hammer', 1], ['Bronze bar', 1]]})),
        'action': 'forge the prototype dart tip',
    }), Record({
        'name': 'stage 14 attaches ten feathers to a held tip',
        'snapshot': snap(Record({'stage': 14, 'tile': BEDABIN, 'inv': [['Prototype dart tip', 1], ['Feather', 10]]})),
        'action': 'attach feathers to the prototype dart tip',
    }), Record({
        'name': 'stage 15 gives the completed prototype to Al Shabim',
        'snapshot': snap(Record({'stage': 15, 'tile': BEDABIN, 'inv': [['Prototype dart', 1]]})),
        'action': 'give the prototype dart to Al Shabim',
    }), Record({
        'name': 'stage 16 gives the pineapple to the cave guard',
        'snapshot': snap(Record({'stage': 16, 'tile': MINE_ENTRANCE, 'inv': [['Tenti pineapple', 1]], 'worn': SLAVE_WORN})),
        'action': 'give the cave guard his Tenti pineapple',
    }), Record({
        'name': 'stage 17 takes the empty mining barrel',
        'snapshot': snap(Record({'stage': 17, 'tile': MINE_LOWER, 'worn': SLAVE_WORN, 'free_slots': 1})),
        'action': 'take an empty mining barrel',
    }), Record({
        'name': 'stage 18 catches Ana after arriving in the deep mine with a barrel',
        'snapshot': snap(Record({'stage': 18, 'tile': MINE_DEEP, 'inv': [['Barrel', 1]], 'worn': SLAVE_WORN})),
        'action': 'put Ana safely in the barrel',
    }), Record({
        'name': 'collapsed stages 19-26 advance a visible deep-mine Ana barrel through the cart',
        'snapshot': snap(Record({'stage': 19, 'tile': MINE_DEEP, 'inv': [['Ana in a barrel', 1]], 'worn': SLAVE_WORN})),
        'action': 'move Ana through the deep-to-lower cart checkpoint',
    }), Record({
        'name': 'collapsed stages 27-29 claim the two reward choices with Irena',
        'snapshot': snap(Record({'stage': 27, 'tile': IRENA})),
        'action': 'claim both Tourist Trap skill rewards',
    })]
    for fixture in cases:
        test(fixture.name, decides(fixture))

    def _fn20():
        expect(decide(snap(Record({'stage': 30}))).kind).to_be('done')
    test('stage 30 is complete', _fn20)

    def _fn21():
        after_crossing = list([(name, _2) for name, _2 in prepared_inventory if name != 'Coins' and name != 'Shantay pass']) + list([['Coins', 990], ['Shantay disclaimer', 1]])
        expect(custom_name(decide(snap(Record({'stage': 0, 'tile': IRENA, 'inv': after_crossing, 'worn': DESERT_WORN}))))).to_be('start Tourist Trap with Irena')
    test('stage 0 keeps the disclaimer received while crossing south instead of routing back to bank', _fn21)

    def _fn23():
        expect(decide(snap(Record({'stage': 2}))).kind).to_be('wait')
        expect(decide(snap(Record({'stage': None}))).kind).to_be('wait')
        expect(decide(snap(Record({'journal': 'unknown', 'stage': 19, 'tile': MINE_DEEP}))).kind).to_be('wait')
    test('an unsupported numeric stage and an unavailable journal both fail closed', _fn23)


describe('Tourist Trap visible-stage decision matrix', _fn18)


def _fn24():
    active_stages = [0, 1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 27]
    for stage in active_stages:
        test(f'stage {stage} escapes a surface jail before its ordinary route', jailed(stage, SURFACE_JAIL, 'escape the surface jail through the rocks'))
        test(f'stage {stage} escapes the punishment mine before its ordinary route', jailed(stage, UNDERGROUND_JAIL, 'mine 15 punishment rocks and escape'))

    def _fn27():
        expect(decide(snap(Record({'stage': 30, 'tile': UNDERGROUND_JAIL}))).kind).to_be('done')
    test('completion remains terminal even if the stale player tile points at a jail', _fn27)


describe('Tourist Trap jail precedence', _fn24)


def _fn28():
    def _fn29():
        expect(custom_name(decide(snap(Record({'stage': 4, 'tile': CAPTAIN, 'inv': [['Metal key', 1]], 'worn': DESERT_WORN}))))).to_be('unlock the desert mining camp')
        expect(custom_name(decide(snap(Record({'stage': 4, 'tile': CAPTAIN, 'bank': [['Metal key', 1]], 'worn': DESERT_WORN}))))).to_be('cross the Shantay Pass north for supplies')
        banked = decide(snap(Record({'stage': 4, 'tile': MAINLAND, 'bank': [['Metal key', 1]], 'worn': DESERT_WORN})))
        expect(banked.kind == 'withdraw' and banked.items).to_equal([Record({'name': 'Metal key', 'qty': 1})])
        expect(custom_name(decide(snap(Record({'stage': 4, 'tile': CAPTAIN, 'worn': DESERT_WORN}))))).to_be('provoke and defeat the respawned Mercenary Captain')
        expect(custom_name(decide(snap(Record({'stage': 4, 'tile': CAPTAIN, 'bank_known': False}))))).to_be('cross the Shantay Pass north for supplies')
        expect(decide(snap(Record({'stage': 4, 'tile': MAINLAND, 'bank_known': False}))).kind).to_be('scan_bank')
    test('metal key recovery checks held, then bank, then safely re-fights the captain', _fn29)

    def _fn30():
        expect(custom_name(decide(snap(Record({'stage': 11, 'tile': CAMP_SURFACE, 'inv': [['Bedobin key', 1], ['Metal key', 1]], 'worn': DESERT_WORN}))))).to_be('distract Captain Siad and steal the plans')
        expect(custom_name(decide(snap(Record({'stage': 11, 'tile': BEDABIN, 'bank': [['Bedobin key', 1]]}))))).to_be('cross the Shantay Pass north for supplies')
        banked = decide(snap(Record({'stage': 11, 'tile': MAINLAND, 'bank': [['Bedobin key', 1]]})))
        expect(banked.kind == 'withdraw' and banked.items).to_equal([Record({'name': 'Bedobin key', 'qty': 1})])
        expect(custom_name(decide(snap(Record({'stage': 11, 'tile': BEDABIN}))))).to_be('ask Al Shabim for a replacement key')
        expect(custom_name(decide(snap(Record({'stage': 11, 'tile': BEDABIN, 'bank_known': False}))))).to_be('cross the Shantay Pass north for supplies')
        expect(decide(snap(Record({'stage': 11, 'tile': MAINLAND, 'bank_known': False}))).kind).to_be('scan_bank')
    test('Bedobin key recovery distinguishes held, banked, missing, and an unknown bank', _fn30)

    def _fn31():
        expect(custom_name(decide(snap(Record({
        'stage': 12,
        'tile': BEDABIN,
        'inv': [['Technical plans', 1], ['Bronze bar', 1], ['Feather', 10], ['Hammer', 1]],
    }))))).to_be('show the technical plans to Al Shabim')
        expect(custom_name(decide(snap(Record({'stage': 12, 'tile': BEDABIN, 'bank': [['Technical plans', 1]]}))))).to_be('cross the Shantay Pass north for supplies')
        banked = decide(snap(Record({'stage': 12, 'tile': MAINLAND, 'bank': [['Technical plans', 1]]})))
        expect(banked.kind == 'withdraw' and banked.items).to_equal([Record({'name': 'Technical plans', 'qty': 1})])
        expect(custom_name(decide(snap(Record({'stage': 12, 'tile': BEDABIN}))))).to_be('ask Al Shabim to replace the plans key')
        expect(custom_name(decide(snap(Record({'stage': 12, 'tile': BEDABIN, 'bank_known': False}))))).to_be('cross the Shantay Pass north for supplies')
        expect(decide(snap(Record({'stage': 12, 'tile': MAINLAND, 'bank_known': False}))).kind).to_be('scan_bank')
    test('technical plans recovery uses held plans, banked plans, or the source-authored replacement path', _fn31)

    def _fn32():
        base = [['Technical plans', 1]]
        expect(custom_name(decide(snap(Record({'stage': 12, 'tile': BEDABIN, 'inv': base}))))).to_be('cross the Shantay Pass north for supplies')
        bar = decide(snap(Record({'stage': 12, 'tile': MAINLAND, 'inv': base})))
        expect(bar.kind == 'buy' and bar.item).to_be('Bronze bar')
        feathers = decide(snap(Record({'stage': 12, 'tile': MAINLAND, 'inv': list(base) + [['Bronze bar', 1]]})))
        expect(feathers.kind == 'buy' and feathers.item).to_be('Feather')
        hammer = decide(snap(Record({'stage': 12, 'tile': MAINLAND, 'inv': list(base) + [['Bronze bar', 1], ['Feather', 10]]})))
        expect(hammer.kind == 'buy' and hammer.item).to_be('Hammer')
    test('stage 12 sources every item required for Al Shabim to advance the journal', _fn32)

    def _fn33():
        expect(custom_name(decide(snap(Record({'stage': 12, 'tile': CAMP_SURFACE, 'inv': [['Technical plans', 1]], 'free_slots': 2}))))).to_be("recover the mining-camp keys from Captain Siad's desk")
        expect(custom_name(decide(snap(Record({'stage': 12, 'tile': CAMP_SURFACE, 'inv': [['Technical plans', 1]], 'free_slots': 0}))))).to_be('free a slot for mining-camp key recovery')
    test("a confiscated camp key is recovered locally from Captain Siad's desk", _fn33)

    def _fn34():
        expect(custom_name(decide(snap(Record({'stage': 12, 'tile': CAPTAIN, 'inv': [['Bedobin key', 1], ['Metal key', 1]], 'worn': DESERT_WORN}))))).to_be('unlock the desert mining camp')
    test('a held Bedobin key routes back to the chest when only the plans are missing', _fn34)

    def _fn35():
        expect(custom_name(decide(snap(Record({'stage': 16, 'tile': MINE_ENTRANCE, 'inv': [['Tenti pineapple', 1]], 'worn': SLAVE_WORN}))))).to_be('give the cave guard his Tenti pineapple')
        expect(custom_name(decide(snap(Record({'stage': 16, 'tile': BEDABIN, 'bank': [['Tenti pineapple', 1]]}))))).to_be('cross the Shantay Pass north for supplies')
        banked = decide(snap(Record({'stage': 16, 'tile': MAINLAND, 'bank': [['Tenti pineapple', 1]]})))
        expect(banked.kind == 'withdraw' and banked.items).to_equal([Record({'name': 'Tenti pineapple', 'qty': 1})])
        expect(custom_name(decide(snap(Record({'stage': 16, 'tile': BEDABIN}))))).to_be('replace the Tenti pineapple at Al Shabim')
        expect(custom_name(decide(snap(Record({'stage': 16, 'tile': BEDABIN, 'bank_known': False}))))).to_be('cross the Shantay Pass north for supplies')
        expect(decide(snap(Record({'stage': 16, 'tile': MAINLAND, 'bank_known': False}))).kind).to_be('scan_bank')
    test('Tenti pineapple recovery distinguishes held, banked, missing, and an unknown bank', _fn35)

    def _fn36():
        banked = decide(snap(Record({
        'stage': 13,
        'tile': MAINLAND,
        'inv': [['Technical plans', 1], ['Hammer', 1]],
        'bank': [['Bronze bar', 1]],
    })))
        expect(banked.kind == 'withdraw' and banked.items).to_equal([Record({'name': 'Bronze bar', 'qty': 1})])
        missing = decide(snap(Record({'stage': 13, 'tile': MAINLAND, 'inv': [['Technical plans', 1], ['Hammer', 1]]})))
        expect(missing.kind == 'buy' and missing.item).to_be('Bronze bar')
    test('a consumed crafting input is withdrawn from bank or re-bought without losing the plans', _fn36)

    def _fn37():
        expect(custom_name(decide(snap(Record({'stage': 15, 'tile': BEDABIN, 'bank': [['Prototype dart', 1]]}))))).to_be('cross the Shantay Pass north for supplies')
        dart = decide(snap(Record({'stage': 15, 'tile': MAINLAND, 'bank': [['Prototype dart', 1]]})))
        expect(dart.kind == 'withdraw' and dart.items).to_equal([Record({'name': 'Prototype dart', 'qty': 1})])
        tip = decide(snap(Record({'stage': 14, 'tile': MAINLAND, 'bank': [['Prototype dart tip', 1]]})))
        expect(tip.kind == 'withdraw' and tip.items).to_equal([Record({'name': 'Prototype dart tip', 'qty': 1})])
    test('banked prototype products are recovered before trying to forge a duplicate', _fn37)
    for stage in [10, 11, 16]:
        test(f'stage {stage} banks expendables before crossing south for a full-pack Al reward', banks_expendables(stage))

    def _fn39():
        step = decide(snap(Record({
        'stage': 13,
        'tile': MAINLAND,
        'inv': [['Technical plans', 1], ['Hammer', 1], ['Kebab', 8]],
        'bank': [['Bronze bar', 1]],
        'free_slots': 0,
    })))
        expect(step.kind).to_be('deposit')
    test('crafting recovery banks expendables instead of waiting with a full pack', _fn39)


describe('Tourist Trap held, banked, and missing critical-item recovery', _fn28)


def _fn40():
    def _fn41():
        for mask in range(8):
            worn_pieces = [SLAVE_OUTFIT[index] for index in range(3) if (mask & (1 << index)) != 0]
            held_pieces = list([[name, 1] for name in [SLAVE_OUTFIT[index] for index in range(3) if (mask & (1 << index)) == 0]]) + [['Metal key', 1]]
            step = decide(snap(Record({'stage': 8, 'tile': CAMP_SURFACE, 'inv': held_pieces, 'worn': list(worn_pieces) + ['Bronze pickaxe']})))
            expect(custom_name(step)).to_be(('open the slave-only mine doors' if mask == 7 else 'wear the slave disguise'))
    test('all eight slave-outfit worn subsets either finish dressing or enter the mine', _fn41)

    def _fn42():
        for mask in range(8):
            worn_pieces = [DESERT_OUTFIT[index] for index in range(3) if (mask & (1 << index)) != 0]
            held_pieces = [[name, 1] for name in [DESERT_OUTFIT[index] for index in range(3) if (mask & (1 << index)) == 0]]
            step = decide(snap(Record({'stage': 1, 'tile': CAPTAIN, 'inv': held_pieces, 'worn': list(worn_pieces) + ['Bronze pickaxe']})))
            expect(custom_name(step)).to_be(('provoke the Mercenary Captain' if mask == 7 else 'wear the camp-safe desert loadout'))
    test('all eight desert-outfit worn subsets either finish dressing or challenge the captain', _fn42)

    def _fn43():
        expect(custom_name(decide(snap(Record({'stage': 9, 'tile': MINE_LOWER, 'worn': SLAVE_WORN}))))).to_be('cross back to the cave guards')
        expect(custom_name(decide(snap(Record({'stage': 17, 'tile': MINE_ENTRANCE, 'worn': SLAVE_WORN, 'free_slots': 1}))))).to_be('walk through the guarded mine cave')
        expect(custom_name(decide(snap(Record({'stage': 19, 'tile': MINE_ENTRANCE, 'worn': SLAVE_WORN}))))).to_be('leave the mine to resolve the surface checkpoint')
    test('mine transport direction follows the verified west/east cave components', _fn43)

    def _fn44():
        for world_tile in [MINE_ENTRANCE, MINE_LOWER, MINE_DEEP]:
            expect(custom_name(decide(snap(Record({'stage': 17, 'tile': world_tile}))))).to_be('return to the punishment mine to recover the slave disguise')
    test('a lost slave outfit deliberately returns to the punishment component for deterministic recovery', _fn44)

    def _fn45():
        held_outfit = [[name, 1] for name in SLAVE_OUTFIT]
        expect(custom_name(decide(snap(Record({'stage': 9, 'tile': MINE_LOWER, 'inv': held_outfit}))))).to_be('wear the slave disguise')
        expect(custom_name(decide(snap(Record({'stage': 17, 'tile': MINE_ENTRANCE, 'inv': held_outfit, 'free_slots': 1}))))).to_be('wear the slave disguise')
    test('a recovered backpack disguise is worn before traversing the guarded cave', _fn45)

    def _fn46():
        supplies = [['Technical plans', 1], ['Hammer', 1], ['Bronze bar', 1], ['Metal key', 1]]
        expect(custom_name(decide(snap(Record({'stage': 13, 'tile': CAMP_UPPER, 'inv': supplies}))))).to_be('climb down before item recovery')
        expect(custom_name(decide(snap(Record({'stage': 13, 'tile': CAMP_SURFACE, 'inv': supplies, 'worn': DESERT_WORN}))))).to_be('leave the camp safely for item recovery')
    test('prototype recovery leaves the keyed camp before walking to the Bedabin anvil', _fn46)
    rescue_fixtures = [
        [17, MINE_LOWER, [], 0, 'free one slot for the rescue barrel'],
        [17, MINE_LOWER, [], 1, 'take an empty mining barrel'],
        [17, MINE_LOWER, [['Barrel', 1]], 0, 'ride the mine cart and catch Ana in the barrel'],
        [18, MINE_LOWER, [], 0, 'free one slot for the rescue barrel'],
        [18, MINE_LOWER, [], 1, 'take an empty mining barrel'],
        [18, MINE_LOWER, [['Barrel', 1]], 0, 'ride back to Ana with the empty barrel'],
        [18, MINE_DEEP, [['Barrel', 1]], 0, 'put Ana safely in the barrel'],
        [19, MINE_DEEP, [['Barrel', 1]], 0, 'reset the rescue state by catching original Ana'],
        [19, MINE_DEEP, [['Ana in a barrel', 1]], 0, 'move Ana through the deep-to-lower cart checkpoint'],
        [19, MINE_LOWER, [], 0, 'free one slot for the lower barrel probe'],
        [19, MINE_LOWER, [], 1, 'resolve the lower barrel/lift checkpoint'],
        [19, MINE_LOWER, [['Ana in a barrel', 1]], 0, 'lift Ana and retrieve her at the surface checkpoint'],
        [19, CAMP_SURFACE, [['Ana in a barrel', 1]], 0, 'resolve the surface winch/cart checkpoint'],
        [19, CAMP_UPPER, [], 1, 'climb down to the surface rescue machinery'],
        [19, CAPTAIN, [['Ana in a barrel', 1]], 0, 'return Ana to Irena'],
        [19, IRENA, [['Ana in a barrel', 1]], 0, 'return Ana to Irena'],
    ]
    for index in range(len(rescue_fixtures)):
        stage, world_tile, inventory, free_slots, action = rescue_fixtures[index]
        test(f'routes rescue checkpoint fixture {index + 1}: stage {stage} -> {action}', routes_rescue(stage, world_tile, inventory, free_slots, action))

    def _fn48():
        for free_slots in [0, 1, 8]:
            failed_cart = snap(Record({
            'stage': TOURIST_TRAP_STAGE.RESCUE,
            'tile': MINE_LOWER,
            'inv': [['Barrel', 1]],
            'worn': SLAVE_WORN,
            'free_slots': free_slots,
        }))
            first_decision = custom_name(decide(failed_cart))
            repeated_decision = custom_name(decide(failed_cart))
            expect(first_decision).to_be('retry the lower mine cart with the empty barrel')
            expect(repeated_decision).to_be(first_decision)
    test('retries the failed stage-19 lower cart in place with an ordinary barrel', _fn48)

    def _fn49():
        step = decide(snap(Record({
        'stage': TOURIST_TRAP_STAGE.RESCUE,
        'tile': MINE_LOWER,
        'inv': [
        ['Barrel', 1],
        ['Coins', 606],
        ['Metal key', 1],
        ['Desert shirt', 1],
        ['Desert robe', 1],
        ['Desert boots', 1],
    ],
        'worn': SLAVE_WORN,
        'free_slots': 8,
    })))
        expect(custom_name(step)).to_be('retry the lower mine cart with the empty barrel')
    test('irrelevant screenshot inventory does not change failed-cart recovery', _fn49)

    def _fn50():
        step = decide(snap(Record({'stage': 18, 'tile': MINE_DEEP, 'worn': SLAVE_WORN, 'free_slots': 1})))
        expect((custom_name(step).lower() if custom_name(step) is not None else None)).to_contain('lower')
    test('does not attempt the impossible deep-mine Ana interaction without an empty barrel', _fn50)

    def _fn51():
        step = decide(snap(Record({'stage': 19, 'tile': CAMP_SURFACE, 'worn': SLAVE_WORN, 'free_slots': 1})))
        expect(custom_name(step)).to_be('resolve the surface winch/cart checkpoint')
    test('a missing visible Ana barrel at the surface safely probes the collapsed transport stages first', _fn51)

    def _fn52():
        spare_desert = [[name, 1] for name in DESERT_OUTFIT]
        recovery = decide(snap(Record({
        'stage': 19,
        'tile': CAMP_SURFACE,
        'inv': list(spare_desert) + [['Metal key', 1]],
        'worn': DESERT_WORN,
        'free_slots': 8,
    })))
        expect(custom_name(recovery)).to_be('replace the slave disguise')
        already_surface = decide(snap(Record({'stage': 19, 'tile': CAMP_SURFACE, 'inv': [['Ana in a barrel', 1]], 'free_slots': 1})))
        expect(custom_name(already_surface)).to_be('resolve the surface winch/cart checkpoint')
    test('surface rescue reacquires a lost slave garment before its cleared-state mine reset', _fn52)

    def _fn53():
        trade = decide(snap(Record({'stage': 19, 'tile': CAMP_SURFACE, 'inv': [['Metal key', 1]], 'worn': DESERT_WORN, 'free_slots': 8})))
        expect(custom_name(trade)).to_be('replace the slave disguise')
        enter = decide(snap(Record({'stage': 19, 'tile': CAPTAIN, 'inv': [['Metal key', 1]], 'worn': DESERT_WORN, 'free_slots': 8})))
        expect(custom_name(enter)).to_be('unlock the desert mining camp')
    test('surface rescue re-trades the worn desert outfit without sourcing a redundant copy', _fn53)

    def _fn54():
        step = decide(snap(Record({
        'stage': 8,
        'tile': CAMP_SURFACE,
        'inv': [['Metal key', 1]],
        'worn': list(SLAVE_WORN) + ['Rune kiteshield'],
    })))
        expect(custom_name(step)).to_be('open the slave-only mine doors')
    test('the mine-entry composite re-sanitizes forbidden extra equipment before moving', _fn54)

    def _fn55():
        step = decide(snap(Record({'stage': 4, 'tile': CAPTAIN, 'worn': DESERT_WORN, 'free_slots': 0})))
        expect(custom_name(step)).not_.to_contain('defeat')
    test('a full pack never starts a key-producing captain fight', _fn55)


describe('Tourist Trap disguise and rescue restart matrix', _fn40)


class RescueHarness:
    """rs2b0t's surface-rescue harness: scripted lift, cart and recapture results, and every call they took."""

    def __init__(self, ana, lift, cart, recapture, interrupt_after_cart):
        self.ana = ana
        self.lift = lift
        self.cart = cart
        self.recapture = recapture
        self.interrupt_after_cart = interrupt_after_cart
        self.cart_index = 0
        self.upkeeps = 0
        self.calls = []
        self.logs = []
        self.operations = Fake(**{
            'has_ana_barrel': lambda: self.ana,
            'retrieve_lift': self.retrieve_lift,
            'escape_by_cart': self.escape_by_cart,
            'recapture_ana': self.recapture_ana,
            'current_area': lambda: 'campSurface',
            'maintain_survival': self.maintain_survival,
            'wait_between_attempts': self.wait_between_attempts,
        })

    def retrieve_lift(self, *_args):
        if False:
            yield
        self.calls.append('lift')
        self.ana = self.lift if self.lift is not None else False
        return self.ana

    def escape_by_cart(self, *_args):
        if False:
            yield
        self.calls.append('cart')
        index = self.cart_index
        self.cart_index += 1
        result = self.cart[index] if self.cart is not None and index < len(self.cart) else False
        if self.cart_index == self.interrupt_after_cart:
            event_signal.set_interrupt(lambda: True)
        return result

    def recapture_ana(self, *_args):
        if False:
            yield
        self.calls.append('recapture')
        return self.recapture if self.recapture is not None else False

    def maintain_survival(self):
        if False:
            yield
        self.upkeeps += 1

    def wait_between_attempts(self):
        if False:
            yield
        self.calls.append('wait')

    def upkeep(self):
        return self.upkeeps

    def log(self, message):
        self.logs.append(message)


def _fn56():
    def harness(ana=None, lift=None, cart=None, recapture=None, interrupt_after_cart=None):
        return RescueHarness(ana if ana is not None else False, lift, cart, recapture, interrupt_after_cart)

    def _fn63():
        run = harness(lift=True)
        _w64 = yield from run_surface_rescue_checkpoint(run.operations, run.log)
        expect(_w64).to_be(True)
        expect(run.calls).to_equal(['lift'])
    test('lift recovery short-circuits cart and recapture probes', _fn63)

    def _fn65():
        run = harness(ana=True, cart=[True])
        _w66 = yield from run_surface_rescue_checkpoint(run.operations, run.log)
        expect(_w66).to_be(True)
        expect(run.calls).to_equal(['cart'])
        expect(run.logs).to_contain('surface cart attempt 1/3')
    test('an existing Ana barrel skips the lift and escapes by cart', _fn65)

    def _fn67():
        run = harness(cart=[False, True])
        _w68 = yield from run_surface_rescue_checkpoint(run.operations, run.log)
        expect(_w68).to_be(True)
        expect(run.calls).to_equal(['lift', 'cart', 'wait', 'cart'])
        expect(run.logs).to_contain('surface cart attempt 2/3')
    test('retries a bounded surface cart probe before succeeding', _fn67)

    def _fn69():
        run = harness(cart=[False, False, False], recapture=True)
        _w70 = yield from run_surface_rescue_checkpoint(run.operations, run.log)
        expect(_w70).to_be(True)
        expect(run.calls).to_equal(['lift', 'cart', 'wait', 'cart', 'wait', 'cart', 'recapture'])
        expect(run.logs).to_contain('surface lift/cart state is clear; starting the canonical deep-mine replay')
    test('starts one canonical deep-mine replay only after all surface probes fail', _fn69)

    def _fn71():
        run = harness(ana=True, cart=[False, False, False], recapture=True)
        _w72 = yield from run_surface_rescue_checkpoint(run.operations, run.log)
        expect(_w72).to_be(False)
        expect(run.calls).to_equal(['cart', 'wait', 'cart', 'wait', 'cart'])
        expect(run.logs).to_contain('surface cart unresolved while carrying Ana; retrying this checkpoint in place')
    test('does not take Ana back underground after a transient surface-cart failure', _fn71)

    def _fn73():
        run = harness(cart=[False, False, False], recapture=False)
        _w74 = yield from run_surface_rescue_checkpoint(run.operations, run.log)
        expect(_w74).to_be(False)
        expect(run.logs).to_contain('deep-mine recapture did not complete; current area=campSurface')
    test('reports an unresolved deep-mine recapture', _fn73)

    def _fn75():
        run = harness(cart=[False, True])
        _w76 = yield from run_surface_rescue_checkpoint(run.operations, run.log)
        expect(_w76).to_be(True)
        expect(run.upkeep()).to_be(5)
    test('runs survival upkeep around retries', _fn75)

    def _fn77():
        run = harness(cart=[False, True], recapture=True, interrupt_after_cart=1)
        _w78 = yield from run_surface_rescue_checkpoint(run.operations, run.log)
        expect(_w78).to_be(False)
        expect(run.calls).to_equal(['lift', 'cart'])
    test('an interrupt after a failed cart stops every later attempt and recapture', _fn77)


describe('Tourist Trap surface rescue orchestration', _fn56)


def _upstream_fn84():
    def _upstream_fn85():
        s = snap(Record({
        'stage': TOURIST_TRAP_STAGE.STARTED,
        'tile': CAPTAIN,
        'inv': [['Waterskin(4)', 2], ['Shantay pass', 1], ['Coins', 900]],
        'worn': list(DESERT_WORN),
    }))
        step = decide(s)
        lines = observe_tourist_trap(s, step)
        expect(any([('stage=1' in l) for l in lines])).to_be(True)
        expect(any([('area=desert' in l) or ('area=' in l) for l in lines])).to_be(True)
        expect(any([('food=Trout:8' in l) for l in lines])).to_be(True)
        expect(any([l.startswith('tt: decide→') for l in lines])).to_be(True)
        expect(any([('WARN' in l) and ('waterskin' in l) for l in lines])).to_be(False)
    test('dumps stage, area, food, and decide step', _upstream_fn85)

    def _upstream_fn86():
        s = snap(Record({
        'stage': TOURIST_TRAP_STAGE.STARTED,
        'tile': CAPTAIN,
        'inv': [['Coins', 100]],
        'worn': list(DESERT_WORN),
        'skins': 0,
    }))
        lines = observe_tourist_trap(s, Record({'kind': 'wait', 'reason': 'death'}))
        expect(any([('WARN' in l) and ('waterskin' in l) for l in lines])).to_be(False)
        expect(any([('death dump' in l) for l in lines])).to_be(True)
    test('does not warn about missing waterskins', _upstream_fn86)

    def _upstream_fn87():
        step = decide(snap(Record({
        'stage': TOURIST_TRAP_STAGE.LEARNED_DARTS,
        'tile': MAINLAND,
        'inv': [['Coins', 200], ['Shantay pass', 1]],
        'skins': 0,
    })))
        expect(custom_name(step)).to_be('cross the Shantay Pass')
    test('re-enters the desert without waterskins after death recovery', _upstream_fn87)

    def _upstream_fn88():
        s = snap(Record({'stage': TOURIST_TRAP_STAGE.LEARNED_DARTS, 'tile': IRENA, 'inv': [['Coins', 50]], 'skins': 0}))
        expect(custom_name(decide(s))).to_be('replace the Tenti pineapple at Al Shabim')
    test('already south with no waterskins continues pineapple recovery', _upstream_fn88)

    def _upstream_fn89():
        expect(custom_name(decide(snap(Record({
        'stage': TOURIST_TRAP_STAGE.KILLED_CAPTAIN,
        'tile': CAPTAIN,
        'inv': [['Coins', 50], ['Bronze pickaxe', 1], ['Trout', 16]],
        'worn': list(DESERT_WORN),
        'kebabs': 0,
        'food': 0,
    }))))).to_be('provoke and defeat the respawned Mercenary Captain')
    test('configured food permits captain recovery without kebabs', _upstream_fn89)


describe('Tourist Trap observe (logging pilot)', _upstream_fn84)


def surplus_food_case(food):
    def _upstream_fn94():
        quest_food.name = food
        rations = ([['Cake', 8], ['2/3 cake', 4], ['Slice of cake', 4]] if food == 'Cake' else [[(food if food is not None else 'Kebab'), 16]])
        inventory = list(rations) + [['Metal key', 1], ['Cell door key', 1], ['Bedobin key', 1], ['Technical plans', 1], ['Bronze bar', 1], ['Hammer', 1], ['Feather', 10]]
        step = decide(snap(Record({
    'stage': TOURIST_TRAP_STAGE.SHOWN_PLANS,
    'tile': MAINLAND,
    'inv': inventory,
    'food': 0,
    'kebabs': 0,
    'free_slots': 0,
})))
        expect(step.kind).to_be('deposit')
        if step.kind != 'deposit':
            return
        expect(step.exact_keep).to_be(True)
        for name, _2 in rations:
            expect(step.keep).not_.to_contain(name.lower())
        for name, _2 in inventory[len(rations):]:
            expect(step.keep).to_contain(name.lower())
        remaining = [(name, _2) for name, _2 in inventory if (name.lower() in step.keep)]
        restock = decide(snap(Record({
    'stage': TOURIST_TRAP_STAGE.SHOWN_PLANS,
    'tile': MAINLAND,
    'inv': remaining,
    'bank': rations,
    'food': 0,
    'kebabs': 0,
    'free_slots': 16,
})))
        expect(restock.kind == 'withdraw' and restock.items).to_equal([Record({'name': (food if food is not None else 'Kebab'), 'qty': 8})])

    return _upstream_fn94


def waterskin_case(skins):
    def _upstream_fn107():
        step = decide(snap(Record({
    'stage': TOURIST_TRAP_STAGE.LEARNED_DARTS,
    'tile': MAINLAND,
    'inv': list(skins) + [['Tenti pineapple', 1], ['Shantay pass', 1], ['Metal key', 1]] + list([[name, 1] for name in SLAVE_OUTFIT]),
    'worn': DESERT_WORN,
    'bank': [['Waterskin(4)', 50]],
    'skins': 0,
})))
        expect(custom_name(step)).to_be('cross the Shantay Pass')

    return _upstream_fn107


def _upstream_fn90():
    def _upstream_fn91():
        step = decide(snap(Record({
        'stage': TOURIST_TRAP_STAGE.STARTED,
        'tile': MAINLAND,
        'bank': [['Trout', 16], ['Kebab', 50]],
        'food': 0,
        'kebabs': 0,
        'free_slots': 20,
    })))
        expect(step.kind == 'withdraw' and step.items).to_equal([Record({'name': 'Trout', 'qty': 8})])
    test('withdraws only the configured food', _upstream_fn91)

    def _upstream_fn92():
        inventory = list([[name, 1] for name in DESERT_OUTFIT]) + list([[name, 1] for name in SLAVE_OUTFIT]) + [['Bronze pickaxe', 1], ['Coins', 1000], ['Shantay pass', 1], ['Waterskin(4)', 4], ['Metal key', 1], ['Bedobin key', 1], ['Technical plans', 1], ['Bronze bar', 1], ['Hammer', 1], ['Feather', 10]]
        free_slots = 28 - sum([((1 if (name in ['Coins', 'Feather', 'Shantay pass']) else count)) for name, count in inventory])
        step = decide(snap(Record({
        'stage': TOURIST_TRAP_STAGE.SHOWN_PLANS,
        'tile': MAINLAND,
        'inv': inventory,
        'bank': [['Trout', 100]],
        'food': 0,
        'kebabs': 0,
        'free_slots': free_slots,
    })))
        expect(step.kind).to_be('withdraw')
        if step.kind != 'withdraw':
            return
        expect(step.items).to_equal([Record({'name': 'Trout', 'qty': 8})])
        expect(free_slots - sum([item.get('qty') for item in step.items])).to_be_greater_than_or_equal(1)
    test('leaves space for quest pickups after provisioning a forge loadout', _upstream_fn92)
    for food in ['Trout', 'Cake', None]:
        def _upstream_fn94():
            quest_food.name = food
            rations = ([['Cake', 8], ['2/3 cake', 4], ['Slice of cake', 4]] if food == 'Cake' else [[(food if food is not None else 'Kebab'), 16]])
            inventory = list(rations) + [['Metal key', 1], ['Cell door key', 1], ['Bedobin key', 1], ['Technical plans', 1], ['Bronze bar', 1], ['Hammer', 1], ['Feather', 10]]
            step = decide(snap(Record({
        'stage': TOURIST_TRAP_STAGE.SHOWN_PLANS,
        'tile': MAINLAND,
        'inv': inventory,
        'food': 0,
        'kebabs': 0,
        'free_slots': 0,
    })))
            expect(step.kind).to_be('deposit')
            if step.kind != 'deposit':
                return
            expect(step.exact_keep).to_be(True)
            for name, _2 in rations:
                expect(step.keep).not_.to_contain(name.lower())
            for name, _2 in inventory[len(rations):]:
                expect(step.keep).to_contain(name.lower())
            remaining = [(name, _2) for name, _2 in inventory if (name.lower() in step.keep)]
            restock = decide(snap(Record({
        'stage': TOURIST_TRAP_STAGE.SHOWN_PLANS,
        'tile': MAINLAND,
        'inv': remaining,
        'bank': rations,
        'food': 0,
        'kebabs': 0,
        'free_slots': 16,
    })))
            expect(restock.kind == 'withdraw' and restock.items).to_equal([Record({'name': (food if food is not None else 'Kebab'), 'qty': 8})])
        test(f"banks an oversized {(food if food is not None else 'Kebab')} loadout and preserves quest items", surplus_food_case(food))

    def _upstream_fn96():
        step = decide(snap(Record({
        'stage': TOURIST_TRAP_STAGE.GIVEN_PINEAPPLE,
        'tile': MINE_DEEP,
        'inv': [['Metal key', 1]],
        'worn': SLAVE_WORN,
        'food': 16,
        'kebabs': 0,
        'free_slots': 0,
    })))
        expect(custom_name(step)).to_be('ride back to the lower mine for item recovery')
    test('leaves the mine before banking excess food from a full pack', _upstream_fn96)

    def _upstream_fn97():
        step = decide(snap(Record({'stage': TOURIST_TRAP_STAGE.REWARD, 'tile': IRENA, 'food': 16, 'kebabs': 0, 'free_slots': 0})))
        expect(custom_name(step)).to_be('claim both Tourist Trap skill rewards')
    test('claims the reward without a food-banking detour', _upstream_fn97)

    def _upstream_fn98():
        step = decide(snap(Record({
        'stage': TOURIST_TRAP_STAGE.RESCUE,
        'tile': CAMP_SURFACE,
        'inv': [['Ana in a barrel', 1]],
        'worn': SLAVE_WORN,
        'food': 16,
        'kebabs': 0,
        'free_slots': 0,
    })))
        expect(custom_name(step)).to_be('resolve the surface winch/cart checkpoint')
    test('does not interrupt the rescue while carrying Ana to bank excess food', _upstream_fn98)

    def _upstream_fn99():
        step = decide(snap(Record({
        'stage': TOURIST_TRAP_STAGE.RESCUE,
        'tile': MAINLAND,
        'bank': [['Trout', 8]],
        'food': 3,
        'kebabs': 0,
        'free_slots': 20,
    })))
        expect(step.kind == 'withdraw' and step.items).to_equal([Record({'name': 'Trout', 'qty': 5})])
    test('tops up a partial configured loadout while already on the mainland', _upstream_fn99)

    def _upstream_fn100():
        step = decide(snap(Record({
        'stage': TOURIST_TRAP_STAGE.STARTED,
        'tile': MAINLAND,
        'bank': [['Trout', 7], ['Kebab', 50]],
        'food': 0,
        'kebabs': 0,
        'free_slots': 20,
    })))
        expect(step).to_equal(Record({
        'kind': 'wait',
        'reason': "configured Tourist Trap food 'Trout' unavailable: need 8, carried 0, banked 7",
    }))
    test('fails explicitly when the configured food target is unavailable', _upstream_fn100)

    def _upstream_fn101():
        quest_food.name = 'Cake'
        step = decide(snap(Record({
        'stage': TOURIST_TRAP_STAGE.STARTED,
        'tile': CAPTAIN,
        'inv': [['Cake', 1], ['2/3 cake', 2], ['Slice of cake', 1], ['Bronze pickaxe', 1]],
        'worn': list(DESERT_WORN),
        'food': 0,
        'kebabs': 0,
    })))
        expect(custom_name(step)).to_be('provoke the Mercenary Captain')
    test('recognizes every configured Cake form', _upstream_fn101)

    def _upstream_fn102():
        quest_food.name = None
        expect(custom_name(decide(snap(Record({'stage': TOURIST_TRAP_STAGE.RESCUE, 'tile': MAINLAND, 'kebabs': 3, 'food': 0}))))).to_be('buy 5 Kebabs')
        expect(custom_name(decide(snap(Record({
        'stage': TOURIST_TRAP_STAGE.KILLED_CAPTAIN,
        'tile': CAPTAIN,
        'inv': [['Bronze pickaxe', 1]],
        'worn': list(DESERT_WORN),
        'kebabs': 8,
        'food': 0,
    }))))).to_be('provoke and defeat the respawned Mercenary Captain')
    test('quest-ration mode tops up to eight on the mainland and accepts eight in the desert', _upstream_fn102)

    def _upstream_fn103():
        quest_food.name = None
        step = decide(snap(Record({
        'stage': TOURIST_TRAP_STAGE.RESCUE,
        'tile': tile(3302, 3118),
        'inv': list([[name, 1] for name in SLAVE_OUTFIT]) + [['Waterskin(4)', 3], ['Waterskin(3)', 1], ['Metal key', 1]],
        'worn': DESERT_WORN,
        'kebabs': 7,
        'food': 0,
        'skins': 0,
        'coins': 200,
        'free_slots': 4,
    })))
        expect(step).to_match_object(Record({'kind': 'buy', 'item': 'Shantay pass', 'qty': 1}))
    test('entry hysteresis does not detour for one consumed food', _upstream_fn103)

    def _upstream_fn104():
        quest_food.name = None
        rescue_pack = list([[name, 1] for name in SLAVE_OUTFIT]) + [['Waterskin(4)', 3], ['Waterskin(3)', 1], ['Metal key', 1], ['Shantay pass', 1]]
        step = decide(snap(Record({
        'stage': TOURIST_TRAP_STAGE.RESCUE,
        'tile': tile(3308, 3120),
        'inv': rescue_pack,
        'worn': DESERT_WORN,
        'kebabs': 8,
        'food': 0,
        'skins': 0,
        'coins': 195,
        'free_slots': 0,
    })))
        expect(custom_name(step)).to_be('cross the Shantay Pass')
    test('does not refill the rescue float after buying a pass while at the 100-coin cart floor', _upstream_fn104)

    def _upstream_fn105():
        quest_food.name = None
        step = decide(snap(Record({
        'stage': TOURIST_TRAP_STAGE.RESCUE,
        'tile': MAINLAND,
        'inv': [[name, 1] for name in SLAVE_OUTFIT],
        'worn': DESERT_WORN,
        'bank': [['Coins', 500]],
        'kebabs': 8,
        'food': 0,
        'coins': 99,
        'free_slots': 8,
    })))
        expect(step.kind == 'withdraw' and step.items).to_equal([Record({'name': 'Coins', 'qty': 40})])
    test('refills to the rescue target below the 100-coin cart floor', _upstream_fn105)

    def _upstream_fn106():
        quest_food.name = None
        shared_inventory = [['Desert shirt', 2], ['Desert robe', 2], ["Slaves' shirt", 1], ['Bronze pickaxe', 1]]
        first_boot = decide(snap(Record({
        'stage': TOURIST_TRAP_STAGE.ENTERED_CAMP,
        'tile': MAINLAND,
        'inv': shared_inventory,
        'kebabs': 8,
        'food': 0,
        'coins': 160,
        'free_slots': 1,
    })))
        expect(first_boot).to_match_object(Record({'kind': 'buy', 'item': 'Desert boots', 'qty': 1, 'est_gp': 25}))
        make_space = decide(snap(Record({
        'stage': TOURIST_TRAP_STAGE.ENTERED_CAMP,
        'tile': MAINLAND,
        'inv': list(shared_inventory) + [['Desert boots', 1]],
        'kebabs': 8,
        'food': 0,
        'coins': 135,
        'free_slots': 0,
    })))
        expect(custom_name(make_space)).to_be('wear the first desert outfit to free recovery slots')
    test('rebuilds a two-copy desert outfit through a one-slot recovery pack', _upstream_fn106)
    for skins in [[], [['Waterskin(1)', 4]], [['Waterskin(4)', 1]]]:
        def _upstream_fn107():
            step = decide(snap(Record({
        'stage': TOURIST_TRAP_STAGE.LEARNED_DARTS,
        'tile': MAINLAND,
        'inv': list(skins) + [['Tenti pineapple', 1], ['Shantay pass', 1], ['Metal key', 1]] + list([[name, 1] for name in SLAVE_OUTFIT]),
        'worn': DESERT_WORN,
        'bank': [['Waterskin(4)', 50]],
        'skins': 0,
    })))
            expect(custom_name(step)).to_be('cross the Shantay Pass')
        test(f'does not restock water before returning to the mine with {json.dumps(skins)}', waterskin_case(skins))

    def _upstream_fn108():
        step = decide(snap(Record({
        'stage': TOURIST_TRAP_STAGE.NOT_STARTED,
        'tile': MAINLAND,
        'inv': [['Waterskin(4)', 4], ['Waterskin(0)', 1], ['Metal key', 1]],
        'worn': DESERT_WORN,
        'coins': 1000,
        'kebabs': 0,
    })))
        expect(step.kind).to_be('deposit')
        if step.kind != 'deposit':
            return
        expect(step.keep).not_.to_contain('waterskin(4)')
        expect(step.keep).not_.to_contain('waterskin(0)')
        expect(step.keep).to_contain('metal key')
        expect(step.keep).to_contain('trout')
    test('banks existing waterskins instead of reserving loadout space for them', _upstream_fn108)

    def _upstream_fn109():
        step = decide(snap(Record({
        'stage': TOURIST_TRAP_STAGE.RESCUE,
        'tile': MINE_ENTRANCE,
        'inv': [["Slaves' shirt", 1]],
        'food': 0,
        'skins': 0,
        'coins': 0,
    })))
        expect(custom_name(step)).to_be('return to the punishment mine to recover the slave disguise')
    test('recovers a missing slave garment locally before trying to restock', _upstream_fn109)

    def _upstream_fn110():
        step = decide(snap(Record({'stage': TOURIST_TRAP_STAGE.ENTERED_CAMP, 'tile': MAINLAND, 'coins': 0})))
        expect(custom_name(step)).to_be('earn 90 gp (Al Kharid Man + Kebabs)')
    test('funds only the exact cost of a missing trade outfit purchase', _upstream_fn110)

    def _upstream_fn111():
        step = decide(snap(Record({
        'stage': TOURIST_TRAP_STAGE.RETRIEVED_PLANS,
        'tile': MAINLAND,
        'inv': [['Technical plans', 1]],
        'coins': 0,
    })))
        expect(custom_name(step)).to_be('earn 8 gp (Al Kharid Man + Kebabs)')
    test('funds only the exact cost of a missing crafting consumable', _upstream_fn111)


describe('Tourist Trap survival accounting', _upstream_fn90)


def _fn101():
    def _fn102():
        messages = []
        spy_on(game_messages, 'mark', impl=lambda: len(messages))
        spy_on(game_messages, 'since', impl=lambda mark: [Fake(text=t) for t in messages[mark:]])
        messages.append('You have an unlucky accident and waste the bronze bar.')
        current_attempt = game_messages.mark()
        expect(forge_bar_wasted_since(current_attempt)).to_be(False)
        messages.append('You have an unlucky accident and waste the bronze bar.')
        expect(forge_bar_wasted_since(current_attempt)).to_be(True)
    test('ignores an old wasted-bar message and recognizes only the current attempt', _fn102)


describe('Tourist Trap prototype forge attempts', _fn101)


# The live run's fixes, each a departure from rs2b0t.
def _fn105():
    from rs2004.quests.defs.touristtrap import FOOD_ENTRY_FLOOR, critical_slot_keep, in_sealed_area, make_critical_item_space, route_south, touristtrap

    def _fn106():
        keep = critical_slot_keep()
        for name in ['bronze bar', 'feather', 'hammer', 'shantay pass']:
            expect(keep).to_contain(name)
    test('the prototype materials and the pass survive a make-room deposit', _fn106)

    def _fn107():
        expect(critical_slot_keep()).not_.to_contain('kebab')
        quest_food.name = ''
        expect(critical_slot_keep()).to_contain('kebab')
    test('kebabs are kept only when they are the rations', _fn107)

    def _fn108():
        step = make_critical_item_space(snap(Record({'tile': MAINLAND, 'free_slots': 0, 'kebabs': 0, 'food': FOOD_ENTRY_FLOOR + 4})), 1)
        expect(step.kind).to_be('custom')
        expect(custom_name(step)).to_contain('bank food down to')
    test('a pack of only kept items banks food above the entry floor', _fn108)

    def _fn109():
        step = make_critical_item_space(snap(Record({'tile': MAINLAND, 'free_slots': 0, 'kebabs': 0, 'food': FOOD_ENTRY_FLOOR})), 1)
        expect(step.kind).to_be('wait')
    test('at the food floor it waits instead of banking food it would draw back', _fn109)

    def _fn110():
        step = route_south(snap(Record({'tile': MAINLAND, 'free_slots': 0, 'kebabs': 0, 'food': FOOD_ENTRY_FLOOR + 4})))
        expect(step.kind).not_.to_be('buy')
        expect(step.kind).not_.to_be('withdraw')
    test('a full pack makes room before the pass is bought or withdrawn', _fn110)

    def _fn111():
        expect(touristtrap.resume_at).to_be(in_sealed_area)
        expect(in_sealed_area(SURFACE_JAIL)).to_be(True)
        expect(in_sealed_area(MINE_DEEP)).to_be(True)
        expect(in_sealed_area(MAINLAND)).to_be(False)
    test('a resumed queue escapes the jail and the camp before generic banking', _fn111)


describe('Tourist Trap live fixes', _fn105)
