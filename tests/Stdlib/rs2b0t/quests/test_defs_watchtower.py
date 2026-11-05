"""rs2b0t's test/api/ai/quests/defs/watchtower.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs.record import Record
from rs2004.quests.defs.watchtower import decide, watchtower
from rs2004.quests.defs.watchtower.areas import CRYSTALS, WT_ITEM, WT_NPC, watchtower_area
from rs2004.quests.defs.watchtower.journal import WATCHTOWER_STAGE, parse_watchtower_journal
from rs2004.quests.engine.types import QuestProgress, QuestSnapshot, flag_value, has_flag
from rs2004.quests.food import quest_food

def mentions(text, *words):
    """rs2b0t's toMatch(/a|b/i): whether text holds any of words, ignoring case."""
    if not isinstance(text, str):
        return False
    lowered = text.lower()
    return any([word.lower() in lowered for word in words])


def at(x, z, level=0):
    return (Record({'x': x, 'z': z, 'level': level}))


def _fn1():
    def _fn2():
        expect(watchtower_area(at(2544, 3112, 2))).to_be('towerFloor')
        expect(watchtower_area(at(2513, 3084))).to_be('grewIsland')
        expect(watchtower_area(at(2576, 3027))).to_be('tobanCamp')
        expect(watchtower_area(at(2526, 3018))).to_be('lowerCity')
        expect(watchtower_area(at(2541, 3029))).to_be('cityGuard')
        expect(watchtower_area(at(2504, 9441))).to_be('skavidCaves')
        expect(watchtower_area(at(2588, 9410))).to_be('enclave')
        expect(watchtower_area(at(2928, 4715, 2))).to_be('mirrorTower')
    test('classifies each sealed pocket by a tile inside it', _fn2)

    def _fn3():
        expect(watchtower_area(at(2530, 3029))).to_be('cityGuard')
        expect(watchtower_area(at(2531, 3026))).to_be('lowerCity')
    test('the city-guard pocket is not swallowed by the lower city', _fn3)

    def _fn4():
        expect(watchtower_area(at(2544, 3112, 0))).to_be('yanille')
        expect(watchtower_area(at(2544, 3112, 1))).to_be('yanille')
    test('the tower floor is level 2 only — the ground below it is Yanille', _fn4)

    def _fn5():
        expect(watchtower_area(at(2612, 3092))).to_be('yanille')
        expect(watchtower_area(at(2544, 3134))).to_be('yanille')
        expect(watchtower_area(at(2505, 3023))).to_be('yanille')
        expect(watchtower_area(at(2506, 3116))).to_be('yanille')
    test('everything else on the surface is yanille', _fn5)

    def _fn6():
        expect(watchtower_area(None)).to_be('unknown')
        expect(watchtower_area(None)).to_be('unknown')
    test('a null tile is unknown, never a default area', _fn6)


describe('watchtowerArea', _fn1)


def _fn7():
    def _fn8():
        expect(len(set([c.name for c in CRYSTALS]))).to_be(1)
        expect(len(set([c.id for c in CRYSTALS]))).to_be(4)
    test('all four crystals share one display name, so ids are the only safe key', _fn8)

    def _fn9():
        expect(WT_ITEM.FINGERNAILS.name).to_be('Finger nails')
        expect(WT_ITEM.STOLEN_GOLD.name).to_be('Gold')
        expect(WT_ITEM.OGRE_POTION.name).to_be('Potion')
        expect(WT_ITEM.GUAM_VIAL.name).to_be('Unfinished potion')
        expect(WT_ITEM.GUAM_JANGER_VIAL.name).to_be('Vial')
    test('the engine names that differ from the wiki are recorded exactly', _fn9)


describe('watchtower items', _fn7)


def _fn10():
    def _fn11():
        p = parse_watchtower_journal('@dbl@I can start this quest by speaking to the @dre@Watchtower wizard')
        expect((p.stage if p is not None else None)).to_be(WATCHTOWER_STAGE.NOT_STARTED)
    test('not started', _fn11)

    def _fn12():
        expect((parse_watchtower_journal([
        '@dbl@I accepted the challenge of finding the lost @dre@crystals.',
        '@dbl@I need to @dre@find evidence@dbl@ of what has happened.',
    ]).stage if parse_watchtower_journal([
        '@dbl@I accepted the challenge of finding the lost @dre@crystals.',
        '@dbl@I need to @dre@find evidence@dbl@ of what has happened.',
    ]) is not None else None)).to_be(WATCHTOWER_STAGE.STARTED)
        expect((parse_watchtower_journal([
        '@dbl@I accepted the challenge of finding the lost @dre@crystals.',
        '@dbl@I found some @dre@fingernails@dbl@ as evidence.',
    ]).stage if parse_watchtower_journal([
        '@dbl@I accepted the challenge of finding the lost @dre@crystals.',
        '@dbl@I found some @dre@fingernails@dbl@ as evidence.',
    ]) is not None else None)).to_be(WATCHTOWER_STAGE.STARTED)
    test('started, before and after the fingernails are found', _fn12)

    def _fn13():
        p = parse_watchtower_journal([
        '@str@I found some fingernails as evidence.',
        '|@dbl@Now I need to @dre@deal with the tribal ogres.||',
        "@str@I returned Og's stolen gold.",
        "@dbl@Grew wants me to give him @dre@one of Gorad's teeth.",
        '@dbl@Toban wants the @dre@bones of an adult dragon.',
    ])
        expect((p.stage if p is not None else None)).to_be(WATCHTOWER_STAGE.GIVEN_FINGERNAILS)
        expect(has_flag(p, 'helped-og')).to_be(True)
        expect(has_flag(p, 'spoken-og')).to_be(True)
        expect(has_flag(p, 'spoken-grew')).to_be(True)
        expect(has_flag(p, 'helped-grew')).to_be(False)
        expect(has_flag(p, 'spoken-toban')).to_be(True)
        expect(has_flag(p, 'helped-toban')).to_be(False)
    test('the tribal block reports which tribes are helped', _fn13)

    def _fn14():
        p = parse_watchtower_journal([
        '@str@I found some fingernails as evidence.',
        '|@dbl@Now I need to @dre@deal with the tribal ogres.||',
        "@str@I returned Og's stolen gold.",
        '@dbl@Some guards gave me a @dre@puzzle to solve.',
    ])
        expect((p.stage if p is not None else None)).to_be(WATCHTOWER_STAGE.GIVEN_RIDDLE)
    test('newest entry wins: the riddle line outranks the tribal block', _fn14)

    def _fn15():
        p = parse_watchtower_journal([
        '|@str@I was given a map by the guard.|',
        '@dbl@I have it with me now, so I can navigate the skavid caves.|',
        '|@dbl@I have been taught a few words of the skavid language:|',
        "|@dre@'Cur bidith' - 'Ig'|",
        "|@dre@'Gor cur' - 'Ar'|",
    ])
        expect((p.stage if p is not None else None)).to_be(WATCHTOWER_STAGE.SOLVED_RIDDLE)
        expect(has_flag(p, 'has-map')).to_be(True)
        expect(has_flag(p, 'learning-skavid')).to_be(True)
        expect(has_flag(p, 'learned-ig')).to_be(True)
        expect(has_flag(p, 'learned-ar')).to_be(True)
        expect(has_flag(p, 'learned-cur')).to_be(False)
        expect(has_flag(p, 'learned-nod')).to_be(False)
    test('the map block reports whether the map is carried and which words are known', _fn15)

    def _fn16():
        p = parse_watchtower_journal([
        '|@str@I was given a map by the guard.|',
        '@dbl@I do not have the map with me now, so I cannot navigate the caves.|',
    ])
        expect((p.stage if p is not None else None)).to_be(WATCHTOWER_STAGE.SOLVED_RIDDLE)
        expect(has_flag(p, 'has-map')).to_be(False)
    test('a map left in the bank is reported as not carried', _fn16)

    def _fn17():
        p = parse_watchtower_journal([
        '|@str@I have made the ogre potion.|',
        '@str@I gave the potion to the wizard.|',
        '@str@He infused it into a magic ogre potion.|',
        '@str@I need to defeat the ogre shamans.|',
        '|@dbl@Now I need to @dre@kill 4 ogre shaman(s).|',
    ])
        expect((p.stage if p is not None else None)).to_be(WATCHTOWER_STAGE.MADE_POTION)
        expect(flag_value(p, 'shamans-left')).to_be(4)
    test('the potion block counts the shamans still standing', _fn17)

    def _fn18():
        p = parse_watchtower_journal([
        '|@str@I have made the ogre potion.|',
        '@str@He infused it into a magic ogre potion.|',
        '|@str@I killed all the ogre shamans.||',
        '@dbl@I have @dre@mined the sacred rock@dbl@ and have taken the last @dre@crystal.|',
    ])
        expect(flag_value(p, 'shamans-left')).to_be(0)
        expect(has_flag(p, 'mined-rock')).to_be(True)
    test('all shamans dead reports zero left, and the mined rock', _fn18)

    def _fn19():
        p = parse_watchtower_journal([
        '|@str@I need to return all the crystals to the Watchtower wizard.|',
        '|@dbl@I have taken the crystals to the Watchtower wizard. Now I need to throw the @dre@lever@dbl@ to @dre@activate the shield@dbl@.',
    ])
        expect((p.stage if p is not None else None)).to_be(WATCHTOWER_STAGE.FOUND_ALL_CRYSTALS)
    test('stage 11 is reported once the crystals are handed over', _fn19)

    def _fn20():
        p = parse_watchtower_journal(['@str@My task here is done.|', '|@dre@QUEST COMPLETE!|'])
        expect((p.stage if p is not None else None)).to_be(WATCHTOWER_STAGE.COMPLETE)
    test('complete', _fn20)

    def _fn21():
        expect(parse_watchtower_journal(['something else entirely'])).to_be_undefined()
    test('unrecognised journal text yields undefined, never a default stage', _fn21)


describe('parseWatchtowerJournal', _fn10)


def snapshot(o=None):
    if o is None:
        o = Fake(**{})
    return QuestSnapshot(**{
        'journal': (o.journal if o.journal is not None else 'in_progress'),
        'inv': (o.inv if o.inv is not None else {}),
        'inv_ids': (o.inv_ids if o.inv_ids is not None else {}),
        'worn': (o.worn if o.worn is not None else set()),
        'worn_ids': (o.worn_ids if o.worn_ids is not None else set()),
        'no_progress': 0,
        'bank_coins': (o.bank_coins if o.bank_coins is not None else 0),
        'stage': (o.stage if o.stage is not None else (o.progress.stage if o.progress is not None else None)),
        'progress': o.progress,
        'bank': (o.bank if o.bank is not None else {}),
        'bank_ids': (o.bank_ids if o.bank_ids is not None else {}),
        'bank_known': (o.bank_known if o.bank_known is not None else True),
        'tile': (o.tile if 'tile' in o._fields else Record({'x': 2612, 'z': 3092, 'level': 0})),
        'free_slots': (o.free_slots if o.free_slots is not None else 28),
        'magic': o.magic,
    })


def _fn22():
    def _fn23():
        expect(decide(snapshot(Fake(**{'journal': 'complete'}))).kind).to_be('done')
    test('a complete journal is done', _fn23)

    def _fn24():
        expect(decide(snapshot(Fake(**{'stage': WATCHTOWER_STAGE.COMPLETE}))).kind).to_be('done')
    test('stage 13 is done even before the journal colour catches up', _fn24)

    def _fn25():
        expect(decide(snapshot(Fake(**{'journal': 'unknown'}))).kind).to_be('wait')
    test('an unloaded journal waits — it is not notStarted', _fn25)

    def _fn26():
        expect(decide(snapshot(Fake(**{'stage': None}))).kind).to_be('wait')
    test('a missing stage waits rather than guessing', _fn26)

    def _fn27():
        expect(decide(snapshot(Fake(**{'stage': 2, 'tile': None}))).kind).to_be('wait')
    test('an unknown location waits rather than acting on a guess', _fn27)

    def _fn28():
        expect(watchtower.owns_inventory).to_be(True)
        expect(watchtower.read_progress).to_be_defined()
        expect(watchtower.record.id).to_be('itwatchtower')
        expect(watchtower.record.name).to_be('Watch Tower')
    test('the module owns its inventory and reads progress, not a bare stage', _fn28)

    def _fn29():
        expect(sorted([i.name for i in watchtower.record.items])).to_equal(['Bat bones', 'Dragon bones', 'Gold bar', 'Guam leaf'])
        expect(all([i.kind == ('acquirable' if i.name == 'Dragon bones' else 'mustHave') for i in watchtower.record.items])).to_be(True)
    test('the record allows dragon-bone acquisition and retains the other required items', _fn29)


describe('watchtower decide — terminal cases', _fn22)


def _fn30():
    def _fn31():
        step = decide(snapshot(Fake(**{'stage': WATCHTOWER_STAGE.NOT_STARTED})))
        expect(step.kind).to_be('custom')
        expect(mentions(step.kind == 'custom' and step.name, 'wizard')).to_be(True)
    test('stage 0 goes to the wizard', _fn31)

    def _fn32():
        step = decide(snapshot(Fake(**{'stage': WATCHTOWER_STAGE.STARTED})))
        expect(step.kind).to_be('custom')
        expect(mentions(step.kind == 'custom' and step.name, 'bush', 'evidence')).to_be(True)
    test('stage 1 without fingernails searches the bush', _fn32)

    def _fn33():
        step = decide(snapshot(Fake(**{'stage': WATCHTOWER_STAGE.STARTED, 'inv_ids': {_k: _v for _k, _v in [[WT_ITEM.FINGERNAILS.id, 1]]}})))
        expect(step.kind).to_be('custom')
        expect(mentions(step.kind == 'custom' and step.name, 'fingernails', 'finger nails')).to_be(True)
    test('stage 1 holding fingernails hands them in', _fn33)

    def _fn34():
        step = decide(snapshot(Fake(**{'stage': WATCHTOWER_STAGE.STARTED, 'tile': Record({'x': 2544, 'z': 3112, 'level': 2})})))
        expect(step.kind).to_be('custom')
        expect(mentions(step.kind == 'custom' and step.name, 'down')).to_be(True)
    test('stranded on the wizard floor at stage 1 without evidence, it climbs down', _fn34)


describe('watchtower decide — the tower', _fn30)


def P(stage, *flags):
    return QuestProgress(stage, set(flags))


def _fn35():
    def _fn36():
        step = decide(snapshot(Fake(**{'progress': P(2)})))
        expect(mentions(step.kind == 'custom' and step.name, 'og')).to_be(True)
    test('stage 2 with nothing done talks to Og first', _fn36)

    def _fn37():
        step = decide(snapshot(Fake(**{'progress': P(2, 'spoken-og'), 'inv_ids': {_k: _v for _k, _v in [[WT_ITEM.TOBAN_KEY.id, 1]]}})))
        expect(mentions(step.kind == 'custom' and step.name, 'chest', 'gold')).to_be(True)
    test('holding the key, it goes for the chest', _fn37)

    def _fn38():
        step = decide(snapshot(Fake(**{'progress': P(2, 'spoken-og'), 'inv_ids': {_k: _v for _k, _v in [[WT_ITEM.STOLEN_GOLD.id, 1]]}})))
        expect(mentions(step.kind == 'custom' and step.name, 'og')).to_be(True)
    test('holding the stolen gold, it returns to Og', _fn38)

    def _fn39():
        step = decide(snapshot(Fake(**{'progress': P(2, 'helped-og'), 'inv_ids': {_k: _v for _k, _v in [[WT_ITEM.DRAGON_BONES.id, 1]]}})))
        expect(mentions(step.kind == 'custom' and step.name, 'toban')).to_be(True)
    test('Toban is next once Og is helped, and is spoken to before he wants bones', _fn39)

    def _fn40():
        step = decide(snapshot(Fake(**{
        'progress': P(2, 'helped-og', 'spoken-toban'),
        'bank_ids': {_k: _v for _k, _v in [[WT_ITEM.DRAGON_BONES.id, 1]]},
    })))
        expect(step.kind).to_be('withdraw')
    test('once Toban has asked, the banked dragon bones are withdrawn', _fn40)

    def _fn41():
        step = decide(snapshot(Fake(**{'progress': P(2, 'helped-og', 'spoken-toban')})))
        expect(step.kind).to_be('custom')
        expect(mentions(step.name, 'dragon bones')).to_be(True)
    test('with no dragon bones anywhere it hunts a blue dragon', _fn41)

    def _fn42():
        step = decide(snapshot(Fake(**{'progress': P(2, 'helped-og', 'helped-toban'), 'inv_ids': {_k: _v for _k, _v in [[WT_ITEM.ROPE.id, 1]]}})))
        expect(mentions(step.kind == 'custom' and step.name, 'grew')).to_be(True)
    test('Grew is spoken to before Gorad is attacked', _fn42)

    def _fn43():
        step = decide(snapshot(Fake(**{'progress': P(2, 'helped-og', 'helped-toban', 'spoken-grew')})))
        expect(mentions(step.kind == 'custom' and step.name, 'gorad', 'tooth')).to_be(True)
    test('once Grew has asked for the tooth, it goes for Gorad', _fn43)

    def _fn44():
        step = decide(snapshot(Fake(**{
        'progress': P(2, 'helped-og', 'helped-toban', 'spoken-grew'),
        'inv_ids': {_k: _v for _k, _v in [[WT_ITEM.OGRE_TOOTH.id, 1], [WT_ITEM.ROPE.id, 1]]},
    })))
        expect(mentions(step.kind == 'custom' and step.name, 'grew')).to_be(True)
    test('holding the tooth, it returns to Grew', _fn44)

    def _fn45():
        step = decide(snapshot(Fake(**{'progress': P(2, 'helped-og', 'helped-toban'), 'bank_ids': {_k: _v for _k, _v in [[WT_ITEM.ROPE.id, 5]]}})))
        expect(step.kind).to_be('withdraw')
    test('it withdraws rope before swinging to Grew', _fn45)

    def _fn46():
        step = decide(snapshot(Fake(**{'progress': P(2, 'helped-og', 'helped-toban'), 'tile': Record({'x': 2513, 'z': 3084, 'level': 0})})))
        expect(mentions(step.kind == 'custom' and step.name, 'grew')).to_be(True)
    test('already on the island, no rope is needed', _fn46)

    def _fn47():
        step = decide(snapshot(Fake(**{
        'progress': P(2, 'helped-og', 'helped-toban', 'helped-grew'),
        'tile': Record({'x': 2513, 'z': 3084, 'level': 0}),
    })))
        expect(mentions(step.kind == 'custom' and step.name, 'jangerberr')).to_be(True)
    test('it picks jangerberries once the tribes are done', _fn47)

    def _fn48():
        step = decide(snapshot(Fake(**{
        'progress': P(2, 'helped-og', 'helped-toban', 'helped-grew'),
        'inv_ids': {_k: _v for _k, _v in [[WT_ITEM.RELIC_PART1.id, 1], [WT_ITEM.JANGERBERRIES.id, 2]]},
    })))
        expect(mentions(step.kind == 'custom' and step.name, 'relic part')).to_be(True)
    test('holding a relic part with every tribe helped, it takes it to the wizard', _fn48)

    # This port asks the tribes for lost parts first (see 'lost relic parts come back from the tribes'), so the
    # park comes once every tribe has been asked.
    def _fn49():
        from rs2004.quests.defs.watchtower.tower import relic_state
        relic_state.asked = set([WT_ITEM.RELIC_PART1.id, WT_ITEM.RELIC_PART2.id, WT_ITEM.RELIC_PART3.id])
        step = decide(snapshot(Fake(**{
        'progress': P(2, 'helped-og', 'helped-toban', 'helped-grew'),
        'inv_ids': {_k: _v for _k, _v in [[WT_ITEM.JANGERBERRIES.id, 2]]},
    })))
        relic_state.asked = set()
        expect(step.kind).to_be('wait')
    test('with the tribes done and no parts left it parks rather than looping', _fn49)


describe('watchtower decide — the tribes', _fn35)


def _fn50():
    def _fn51():
        step = decide(snapshot(Fake(**{'progress': P(3), 'inv_ids': {_k: _v for _k, _v in [[WT_ITEM.OGRE_RELIC.id, 1]]}})))
        expect(mentions(step.kind == 'custom' and step.name, 'guard')).to_be(True)
    test('stage 3 holding the relic shows it to the north-west guard', _fn51)

    def _fn52():
        step = decide(snapshot(Fake(**{'progress': P(3), 'bank_ids': {_k: _v for _k, _v in [[WT_ITEM.OGRE_RELIC.id, 1]]}})))
        expect(step.kind).to_be('withdraw')
    test('stage 3 with the relic banked withdraws it', _fn52)

    def _fn53():
        step = decide(snapshot(Fake(**{'progress': P(3)})))
        expect(mentions(step.kind == 'custom' and step.name, 'wizard', 'another', 'copy')).to_be(True)
    test('stage 3 with no relic anywhere asks the wizard for a copy', _fn53)


describe('watchtower decide — the relic gate', _fn50)


def _fn54():
    def _fn55():
        step = decide(snapshot(Fake(**{'progress': P(4, 'market-asked')})))
        expect(mentions(step.kind == 'custom' and step.name, 'rock cake', 'steal')).to_be(True)
    test('stage 4 with no rock cake steals one', _fn55)

    def _fn56():
        step = decide(snapshot(Fake(**{'progress': P(4, 'market-asked'), 'inv_ids': {_k: _v for _k, _v in [[WT_ITEM.ROCK_CAKE.id, 1]]}})))
        expect(mentions(step.kind == 'custom' and step.name, 'battlement', 'guard')).to_be(True)
    test('stage 4 holding the cake gives it to the battlement guard', _fn56)

    def _fn57():
        step = decide(snapshot(Fake(**{
        'progress': P(4, 'market-paid'),
        'tile': Record({'x': 2526, 'z': 3018, 'level': 0}),
        'inv_ids': {_k: _v for _k, _v in [[WT_ITEM.COINS.id, 500]]},
    })))
        expect(mentions(step.kind == 'custom' and step.name, 'chasm', 'jump', 'guard')).to_be(True)
    test('with the market paid and coins in hand, it heads for the chasm', _fn57)

    def _fn58():
        step = decide(snapshot(Fake(**{
        'progress': P(4, 'market-paid'),
        'tile': Record({'x': 2526, 'z': 3018, 'level': 0}),
        'inv_ids': {},
        'bank_ids': {_k: _v for _k, _v in [[WT_ITEM.COINS.id, 100000]]},
    })))
        expect(mentions(step.kind == 'custom' and step.name, 'battlement')).to_be(True)
    test('short of the toll inside the lower city, it climbs out toward the bank', _fn58)

    def _fn59():
        step = decide(snapshot(Fake(**{
        'progress': P(4, 'market-paid'),
        'inv_ids': {},
        'bank_ids': {_k: _v for _k, _v in [[WT_ITEM.COINS.id, 100000]]},
    })))
        expect(step.kind).to_be('withdraw')
    test('short of the toll on the mainland, it withdraws it', _fn59)

    def _fn60():
        step = decide(snapshot(Fake(**{
        'progress': P(4, 'market-paid'),
        'tile': Record({'x': 2541, 'z': 3029, 'level': 0}),
        'inv_ids': {_k: _v for _k, _v in [[WT_ITEM.COINS.id, 500]]},
    })))
        expect(mentions(step.kind == 'custom' and step.name, 'riddle', 'passage', 'guard')).to_be(True)
    test('already in the pocket, it asks the guard for passage', _fn60)

    def _fn61():
        step = decide(snapshot(Fake(**{
        'progress': P(5),
        'tile': Record({'x': 2541, 'z': 3029, 'level': 0}),
        'inv_ids': {_k: _v for _k, _v in [[WT_ITEM.DEATH_RUNE.id, 1], [WT_ITEM.COINS.id, 500]]},
    })))
        expect(mentions(step.kind == 'custom' and step.name, 'riddle', 'rune')).to_be(True)
    test('stage 5 holding a death rune answers the riddle', _fn61)

    def _fn62():
        step = decide(snapshot(Fake(**{'progress': P(5), 'inv_ids': {_k: _v for _k, _v in [[WT_ITEM.COINS.id, 5000]]}})))
        expect(step.kind).to_be('buy')
    test('stage 5 without a death rune buys one', _fn62)


describe('watchtower decide — into the city guard pocket', _fn54)


def _fn63():
    def _fn64():
        step = decide(snapshot(Fake(**{
        'progress': P(2, 'spoken-og'),
        'inv_ids': {_k: _v for _k, _v in [[WT_ITEM.STOLEN_GOLD.id, 1]]},
        'tile': Record({'x': 2576, 'z': 3027, 'level': 0}),
    })))
        expect(mentions(step.kind == 'custom' and step.name, 'leave Toban')).to_be(True)
    test('holding the stolen gold inside Toban camp, it leaves before seeking Og', _fn64)

    def _fn65():
        step = decide(snapshot(Fake(**{
        'progress': P(2, 'helped-og', 'helped-toban', 'helped-grew'),
        'inv_ids': {_k: _v for _k, _v in [[WT_ITEM.RELIC_PART2.id, 1], [WT_ITEM.JANGERBERRIES.id, 2]]},
        'tile': Record({'x': 2513, 'z': 3084, 'level': 0}),
    })))
        expect(mentions(step.kind == 'custom' and step.name, 'swing back')).to_be(True)
    test('stranded on Grew island with nothing left to do there, it swings out first', _fn65)

    def _fn66():
        POCKETS = [
        ['grewIsland', Record({'x': 2513, 'z': 3084, 'level': 0})],
        ['tobanCamp', Record({'x': 2576, 'z': 3027, 'level': 0})],
        ['cityGuard', Record({'x': 2541, 'z': 3029, 'level': 0})],
        ['skavidCaves', Record({'x': 2504, 'z': 9441, 'level': 0})],
        ['enclave', Record({'x': 2588, 'z': 9410, 'level': 0})],
        ['towerFloor', Record({'x': 2544, 'z': 3112, 'level': 2})],
        ['lowerCity', Record({'x': 2526, 'z': 3018, 'level': 0})],
    ]
        for stage in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]:
            for name, tile in POCKETS:
                step = decide(snapshot(Fake(**{'progress': P(stage), 'tile': tile, 'bank_known': True})))
                expect(f'{stage}/{name}={step.kind}').not_.to_contain('=wait')
    test('no stage leaves the bot parked merely because it woke in a pocket', _fn66)


describe('watchtower decide — never act from the wrong pocket', _fn63)


def _fn67():
    tribes_done = ['helped-og', 'helped-toban', 'helped-grew']

    def _fn68():
        step = decide(snapshot(Fake(**{
        'progress': P(2, *tribes_done),
        'inv_ids': {_k: _v for _k, _v in [[WT_ITEM.RELIC_PART2.id, 1]]},
        'tile': Record({'x': 2513, 'z': 3084, 'level': 0}),
    })))
        expect(mentions(step.kind == 'custom' and step.name, 'jangerberr')).to_be(True)
    test('standing on the island short of berries, it picks them before leaving', _fn68)

    def _fn69():
        step = decide(snapshot(Fake(**{
        'progress': P(2, *tribes_done),
        'inv_ids': {_k: _v for _k, _v in [[WT_ITEM.RELIC_PART2.id, 1], [WT_ITEM.ROPE.id, 1]]},
    })))
        expect(mentions(step.kind == 'custom' and step.name, 'relic part')).to_be(True)
    test('off the island, relic parts are delivered before a berry trip', _fn69)

    def _fn70():
        step = decide(snapshot(Fake(**{
        'progress': P(2, *tribes_done),
        'inv_ids': {_k: _v for _k, _v in [[WT_ITEM.JANGERBERRIES.id, 2], [WT_ITEM.RELIC_PART2.id, 1]]},
        'tile': Record({'x': 2513, 'z': 3084, 'level': 0}),
    })))
        expect(mentions(step.kind == 'custom' and step.name, 'swing back')).to_be(True)
    test('on the island with berries already, it leaves instead of loitering', _fn70)


describe('watchtower decide — jangerberries without a wasted rope', _fn67)


def _fn71():
    def _fn72():
        step = decide(snapshot(Fake(**{
        'progress': P(2, 'helped-og', 'helped-toban', 'helped-grew'),
        'inv_ids': {_k: _v for _k, _v in [[WT_ITEM.RELIC_PART2.id, 1], [WT_ITEM.JANGERBERRIES.id, 2]]},
        'tile': Record({'x': 2544, 'z': 3112, 'level': 2}),
    })))
        expect(mentions(step.kind == 'custom' and step.name, 'give Relic part')).to_be(True)
    test('a relic part is handed over without climbing down first', _fn72)

    def _fn73():
        step = decide(snapshot(Fake(**{'progress': P(11), 'tile': Record({'x': 2544, 'z': 3112, 'level': 2})})))
        expect(mentions(step.kind == 'custom' and step.name, 'lever')).to_be(True)
    test('the lever is pulled from the wizard floor, not after a climb down', _fn73)

    def _fn74():
        step = decide(snapshot(Fake(**{'progress': P(11), 'tile': Record({'x': 2576, 'z': 3027, 'level': 0})})))
        expect(mentions(step.kind == 'custom' and step.name, 'leave Toban')).to_be(True)
    test('a wizard step still escapes a genuinely wrong pocket', _fn74)


describe('watchtower decide — wizard steps stay on the wizard floor', _fn71)


def _fn75():
    tribes_done = ['helped-og', 'helped-toban', 'helped-grew']

    def _fn76():
        step = decide(snapshot(Fake(**{
        'progress': P(WATCHTOWER_STAGE.GIVEN_FINGERNAILS, *tribes_done),
        'inv_ids': {_k: _v for _k, _v in [[WT_ITEM.OGRE_RELIC.id, 1]]},
    })))
        expect(mentions(step.kind == 'custom' and step.name, 'north-west ogre guard')).to_be(True)
    test('the journal cannot tell 2 from 3, so owning the relic decides it', _fn76)

    def _fn77():
        step = decide(snapshot(Fake(**{
        'progress': P(WATCHTOWER_STAGE.GIVEN_FINGERNAILS, *tribes_done),
        'bank_ids': {_k: _v for _k, _v in [[WT_ITEM.OGRE_RELIC.id, 1]]},
    })))
        expect(step.kind).to_be('withdraw')
    test('a relic sitting in the bank also counts, and is withdrawn', _fn77)

    def _fn78():
        step = decide(snapshot(Fake(**{
        'progress': P(WATCHTOWER_STAGE.GIVEN_FINGERNAILS, 'helped-og', 'helped-toban'),
        'inv_ids': {_k: _v for _k, _v in [[WT_ITEM.ROPE.id, 1]]},
    })))
        expect(mentions(step.kind == 'custom' and step.name, 'grew')).to_be(True)
    test('without a relic it is still the tribal stage', _fn78)


describe('watchtower decide — stage 3 hides inside stage 2', _fn75)


def _fn79():
    def _fn80():
        expect(WT_NPC.SKAVID).to_be('Skavid')
        expect(WT_NPC.SCARED_SKAVID).to_be('Scared skavid')
        expect(WT_NPC.MAD_SKAVID).to_be('Mad skavid')
    test('only the four language talkers are plain Skavid', _fn80)

    def _fn81():
        expect(WT_NPC.OGRE_GUARD).to_be('Ogre guard')
        expect(WT_NPC.CITY_GUARD).to_be('City guard')
        expect(WT_NPC.ENCLAVE_GUARD).to_be('Enclave guard')
    test('all four ogre guards share one name, so they are told apart by where we stand', _fn81)


describe('watchtower npc names', _fn79)


def _fn82():
    def _fn83():
        step = decide(snapshot(Fake(**{
        'progress': P(WATCHTOWER_STAGE.GIVEN_RIDDLE),
        'tile': Record({'x': 2541, 'z': 3029, 'level': 0}),
        'bank_known': False,
    })))
        expect(mentions(step.kind == 'custom' and step.name, 'jump back')).to_be(True)
    test('stage 5 inside the city-guard pocket jumps out before checking the bank', _fn83)

    def _fn84():
        step = decide(snapshot(Fake(**{'progress': P(WATCHTOWER_STAGE.GIVEN_RIDDLE), 'bank_known': False})))
        expect(step.kind).to_be('scan_bank')
    test('stage 5 outside may go to the bank', _fn84)

    def _fn85():
        step = decide(snapshot(Fake(**{
        'progress': P(WATCHTOWER_STAGE.SOLVED_RIDDLE, 'has-map'),
        'inv_ids': {_k: _v for _k, _v in [[WT_ITEM.SKAVID_MAP.id, 1]]},
        'tile': Record({'x': 2504, 'z': 9441, 'level': 0}),
        'bank_ids': {_k: _v for _k, _v in [[WT_ITEM.LIT_CANDLE.id, 1]]},
    })))
        expect(mentions(step.kind == 'custom' and step.name, 'leave the skavid cave')).to_be(True)
    test('stage 6 in a cave leaves before withdrawing a light source', _fn85)


describe('watchtower decide — banking never starts from a sealed pocket', _fn82)


def _fn86():
    def _fn87():
        p = parse_watchtower_journal([
        '|@str@I need to defeat the ogre shamans and find the other|',
        '@str@crystals.|',
        '@str@I tried to defeat the shamans, but they are protected|',
        '@str@by powerful magics!|',
        '|@dbl@I have made the @dre@ogre potion@dbl@. I need to get it enchanted by the Watchtower wizard.|',
    ])
        expect((p.stage if p is not None else None)).to_be(WATCHTOWER_STAGE.LEARNED_POTION)
    test('stage 9 with the brewed potion is not mistaken for stage 8', _fn87)

    def _fn88():
        p = parse_watchtower_journal([
        '|@str@I need to defeat the ogre shamans and find the other|',
        '@str@crystals.|',
        '@dbl@I need to make the @dre@potion@dbl@ that will @dre@defeat the ogre @dre@shamans@dbl@.',
    ])
        expect((p.stage if p is not None else None)).to_be(WATCHTOWER_STAGE.LEARNED_POTION)
    test('stage 9 before brewing also reads as 9, not 8', _fn88)

    def _fn89():
        p = parse_watchtower_journal([
        '@str@I used some cave nightshade to distract the guard.|',
        '@dbl@I need to @dre@defeat the ogre shamans@dbl@ and @dre@find the other crystals.|',
    ])
        expect((p.stage if p is not None else None)).to_be(WATCHTOWER_STAGE.FED_NIGHTSHADE)
    test('stage 8 itself still reads as 8', _fn89)


describe('parseWatchtowerJournal — colour tags leave a space before punctuation', _fn86)


def _fn90():
    def _fn91():
        step = decide(snapshot(Fake(**{
        'progress': P(WATCHTOWER_STAGE.MADE_POTION, 'shamans-left:6'),
        'inv': {_k: _v for _k, _v in [['tuna', 10]]},
        'inv_ids': {_k: _v for _k, _v in [[WT_ITEM.MAGIC_OGRE_POTION.id, 1], [WT_ITEM.LIT_CANDLE.id, 1]]},
    })))
        expect(mentions(step.kind == 'custom' and step.name, 'skavid map')).to_be(True)
    test('stage 10 fetching nightshade without the map re-asks the city guard', _fn91)

    def _fn92():
        step = decide(snapshot(Fake(**{
        'progress': P(WATCHTOWER_STAGE.MADE_POTION, 'shamans-left:6'),
        'inv': {_k: _v for _k, _v in [['tuna', 10]]},
        'inv_ids': {_k: _v for _k, _v in [[WT_ITEM.MAGIC_OGRE_POTION.id, 1], [WT_ITEM.LIT_CANDLE.id, 1]]},
        'bank_ids': {_k: _v for _k, _v in [[WT_ITEM.SKAVID_MAP.id, 1]]},
    })))
        expect(step.kind).to_be('withdraw')
    test('with the map banked it is withdrawn rather than re-asked', _fn92)

    def _fn93():
        step = decide(snapshot(Fake(**{
        'progress': P(WATCHTOWER_STAGE.MADE_POTION, 'shamans-left:6'),
        'inv': {_k: _v for _k, _v in [['tuna', 10]]},
        'inv_ids': {_k: _v for _k, _v in [[WT_ITEM.MAGIC_OGRE_POTION.id, 1], [WT_ITEM.SKAVID_MAP.id, 1], [WT_ITEM.LIT_CANDLE.id, 1]]},
    })))
        expect(mentions(step.kind == 'custom' and step.name, 'nightshade')).to_be(True)
    test('with map and light in hand it goes for the nightshade', _fn93)


describe('watchtower decide — a cave trip needs the map and a light', _fn90)


def _fn94():
    def _fn95():
        step = decide(snapshot(Fake(**{
        'progress': P(WATCHTOWER_STAGE.MADE_POTION, 'shamans-left:6'),
        'inv_ids': {_k: _v for _k, _v in [[WT_ITEM.MAGIC_OGRE_POTION.id, 1], [WT_ITEM.NIGHTSHADE.id, 1]]},
        'bank': {_k: _v for _k, _v in [['tuna', 100]]},
    })))
        expect(step.kind).to_be('withdraw')
    test('stage 10 with no food withdraws some before going in', _fn95)

    def _fn96():
        step = decide(snapshot(Fake(**{
        'progress': P(WATCHTOWER_STAGE.MADE_POTION, 'shamans-left:6'),
        'inv_ids': {_k: _v for _k, _v in [[WT_ITEM.MAGIC_OGRE_POTION.id, 1], [WT_ITEM.NIGHTSHADE.id, 1]]},
    })))
        expect(step.kind).to_be('wait')
        expect(mentions(step.kind == 'wait' and step.reason, 'food')).to_be(True)
    test('with no food anywhere it parks naming the problem', _fn96)


describe('watchtower decide — the enclave is never entered without food', _fn94)


def _fn97():
    all_four = {_k: _v for _k, _v in [[WT_ITEM.CRYSTAL1.id, 1], [WT_ITEM.CRYSTAL2.id, 1], [WT_ITEM.CRYSTAL3.id, 1], [WT_ITEM.CRYSTAL4.id, 1]]}

    def _fn98():
        step = decide(snapshot(Fake(**{
        'progress': P(WATCHTOWER_STAGE.MADE_POTION, 'shamans-left:0'),
        'inv': {_k: _v for _k, _v in [['tuna', 10]]},
        'inv_ids': all_four,
        'bank_known': False,
    })))
        expect(mentions(step.kind == 'custom' and step.name, 'crystals to the wizard')).to_be(True)
    test('goes straight to the wizard without a bank trip', _fn98)

    def _fn99():
        partial = {_k: _v for _k, _v in all_four.items()}
        partial.pop(WT_ITEM.CRYSTAL2.id, None)
        step = decide(snapshot(Fake(**{
        'progress': P(WATCHTOWER_STAGE.MADE_POTION, 'shamans-left:0'),
        'inv': {_k: _v for _k, _v in [['tuna', 10]]},
        'inv_ids': partial,
        'bank_known': False,
    })))
        expect(step.kind).to_be('scan_bank')
    test('a missing crystal still consults the bank first', _fn99)


describe('watchtower decide — holding all four crystals', _fn97)


def _fn100():
    all_four = {_k: _v for _k, _v in [[WT_ITEM.CRYSTAL1.id, 1], [WT_ITEM.CRYSTAL2.id, 1], [WT_ITEM.CRYSTAL3.id, 1], [WT_ITEM.CRYSTAL4.id, 1]]}

    def _fn101():
        step = decide(snapshot(Fake(**{'progress': P(WATCHTOWER_STAGE.MADE_POTION, 'shamans-left:0'), 'inv_ids': all_four})))
        expect(mentions(step.kind == 'custom' and step.name, 'crystals to the wizard')).to_be(True)
    test('carrying every crystal with no food, it still reaches the wizard', _fn101)

    def _fn102():
        step = decide(snapshot(Fake(**{
        'progress': P(WATCHTOWER_STAGE.MADE_POTION, 'shamans-left:6'),
        'inv_ids': {_k: _v for _k, _v in [[WT_ITEM.MAGIC_OGRE_POTION.id, 1], [WT_ITEM.NIGHTSHADE.id, 1]]},
    })))
        expect(step.kind).to_be('wait')
        expect(mentions(step.kind == 'wait' and step.reason, 'food')).to_be(True)
    test('but a trip back in without food still parks', _fn102)


describe('watchtower decide — food is only demanded for trips that re-enter', _fn100)


def _fn103():
    def _fn104():
        step = decide(snapshot(Fake(**{
        'progress': P(WATCHTOWER_STAGE.FOUND_ALL_CRYSTALS),
        'tile': Record({'x': 2928, 'z': 4715, 'level': 2}),
        'inv_ids': {_k: _v for _k, _v in [[WT_ITEM.WATCHTOWER_SPELL.id, 1]]},
    })))
        expect(mentions(step.kind == 'custom' and step.name, 'scroll')).to_be(True)
    test('standing in region 45_73 with the scroll, it reads it', _fn104)

    def _fn105():
        step = decide(snapshot(Fake(**{'progress': P(WATCHTOWER_STAGE.FOUND_ALL_CRYSTALS), 'tile': Record({'x': 2928, 'z': 4715, 'level': 2})})))
        expect(mentions(step.kind == 'custom' and step.name, 'climb down')).to_be(True)
    test('without the scroll it climbs down rather than retrying the lever', _fn105)


describe('watchtower decide — the mirror tower means done', _fn103)


def _fn106():
    def mining(over=None):
        if over is None:
            over = Fake(**{})
        _merged107 = {}
        for _k, _v in {
            'progress': P(WATCHTOWER_STAGE.MADE_POTION, 'shamans-left:0'),
            'inv': {_k: _v for _k, _v in [['tuna', 10]]},
            'inv_ids': {_k: _v for _k, _v in [[WT_ITEM.NIGHTSHADE.id, 1], [WT_ITEM.SKAVID_MAP.id, 1], [WT_ITEM.LIT_CANDLE.id, 1]]},
        }.items():
            _merged107[_k] = _v
        for _k, _v in over._fields.items():
            _merged107[_k] = _v
        return decide(snapshot(Fake(**_merged107)))

    def _fn108():
        step = mining()
        expect(step.kind).to_be('buy')
        expect(step.kind == 'buy' and step.item).to_be(WT_ITEM.PICKAXE.name)
    test('with no pickaxe anywhere it buys one rather than mining bare-handed', _fn108)

    def _fn109():
        step = mining(Fake(**{'bank_ids': {_k: _v for _k, _v in [[WT_ITEM.PICKAXE.id, 1]]}}))
        expect(step.kind).to_be('withdraw')
    test('a banked pickaxe is withdrawn instead of bought', _fn109)

    def _fn110():
        step = mining(Fake(**{'tile': Record({'x': 2589, 'z': 9450, 'level': 0})}))
        expect(mentions(step.kind == 'custom' and step.name, 'leave the shaman enclave')).to_be(True)
    test('standing in the enclave with no pickaxe it leaves to get one', _fn110)

    def _fn111():
        step = decide(snapshot(Fake(**{
        'progress': P(WATCHTOWER_STAGE.MADE_POTION, 'shamans-left:6'),
        'inv': {_k: _v for _k, _v in [['tuna', 10]]},
        'inv_ids': {_k: _v for _k, _v in [[WT_ITEM.MAGIC_OGRE_POTION.id, 1], [WT_ITEM.NIGHTSHADE.id, 1]]},
    })))
        expect(step.kind).to_be('buy')
        expect(step.kind == 'buy' and step.item).to_be(WT_ITEM.PICKAXE.name)
    test('the pickaxe is carried in with the shaman trip, not fetched after', _fn111)

    def _fn112():
        step = mining(Fake(**{'inv_ids': {_k: _v for _k, _v in [
        [WT_ITEM.NIGHTSHADE.id, 1],
        [WT_ITEM.SKAVID_MAP.id, 1],
        [WT_ITEM.LIT_CANDLE.id, 1],
        [WT_ITEM.PICKAXE.id, 1],
    ]}}))
        expect(mentions(step.kind == 'custom' and step.name, 'Rock of Dalgroth')).to_be(True)
    test('with a pickaxe carried it goes and mines', _fn112)


describe('watchtower decide — the Rock of Dalgroth needs a pickaxe', _fn106)


def _fn113():
    def enclave_trip(bank, inv=None):
        if inv is None:
            inv = []
        return snapshot(Fake(**{
            'progress': P(WATCHTOWER_STAGE.MADE_POTION, 'shamans-left:6'),
            'inv': {_k: _v for _k, _v in inv},
            'inv_ids': {_k: _v for _k, _v in [[WT_ITEM.MAGIC_OGRE_POTION.id, 1], [WT_ITEM.NIGHTSHADE.id, 1]]},
            'bank': {_k: _v for _k, _v in bank},
        }))

    def _fn114():
        quest_food.name = 'Lobster'
    after_each(_fn114)

    def _fn115():
        quest_food.name = 'Shark'
        step = decide(enclave_trip([['shark', 100]]))
        expect(step.kind).to_be('withdraw')
        expect(step.kind == 'withdraw' and step.items[0]['name']).to_be('Shark')
    test('the configured food is withdrawn when the bank holds only that', _fn115)

    def _fn116():
        quest_food.name = 'Shark'
        expect(decide(enclave_trip([['shark', 100]], [['shark', 8]])).kind).not_.to_be('withdraw')
    test('food already carried counts, whatever the player chose', _fn116)

    def _fn117():
        quest_food.name = 'Lobster'
        step = decide(enclave_trip([['lobster', 100]]))
        expect(step.kind).to_be('withdraw')
        expect(step.kind == 'withdraw' and step.items[0]['name']).to_be('Lobster')
    test('the listed foods still work when the player chose one of them', _fn117)


describe('the enclave food is whatever the player chose to eat', _fn113)


def _fn118():
    FULL_BANK = {_k: _v for _k, _v in [['lobster', 100]]}

    def bank_ids():
        return {_k: _v for _k, _v in [
            [WT_ITEM.COINS.id, 50000],
            [WT_ITEM.ROPE.id, 1],
            [WT_ITEM.VIAL_WATER.id, 1],
            [WT_ITEM.PESTLE.id, 1],
            [WT_ITEM.PICKAXE.id, 1],
            [WT_ITEM.DEATH_RUNE.id, 5],
            [WT_ITEM.GUAM_LEAF.id, 1],
            [WT_ITEM.BAT_BONES.id, 1],
            [WT_ITEM.DRAGON_BONES.id, 1],
            [WT_ITEM.GOLD_BAR.id, 1],
            [WT_ITEM.SKAVID_MAP.id, 1],
            [WT_ITEM.LIT_CANDLE.id, 1],
        ]}

    def started(o=None):
        if o is None:
            o = Fake(**{})
        _merged119 = {}
        for _k, _v in {
            'progress': P(WATCHTOWER_STAGE.STARTED),
            'bank_known': True,
            'bank': FULL_BANK,
            'bank_ids': bank_ids(),
        }.items():
            _merged119[_k] = _v
        for _k, _v in o._fields.items():
            _merged119[_k] = _v
        return snapshot(Fake(**_merged119))

    def _fn120():
        step = decide(started())
        expect(step.kind).to_be('withdraw')
        names = ([i['name'] for i in step.items] if step.kind == 'withdraw' else [])
        for want in [
        'Coins',
        'Rope',
        'Vial of water',
        'Pestle and mortar',
        'Bronze pickaxe',
        'Death rune',
        'Guam leaf',
        'Bat bones',
        'Dragon bones',
        'Gold bar',
        'Skavid map',
        'Lit candle',
    ]:
            expect(names).to_contain(want)
    test('one withdraw carries the whole banked kit, not one item per trip', _fn120)

    def _fn121():
        step = decide(started())
        names = ([i['name'] for i in step.items] if step.kind == 'withdraw' else [])
        expect(names).to_contain('Lobster')
    test('the configured food rides along in the same trip', _fn121)

    def _fn122():
        step = decide(started(Fake(**{'bank_ids': {_k: _v for _k, _v in [[WT_ITEM.ROPE.id, 1]]}, 'bank': {}})))
        names = ([i['name'] for i in step.items] if step.kind == 'withdraw' else [])
        expect(names).to_equal(['Rope'])
    test('what the bank does not hold is left to the shop and the quest', _fn122)

    def _fn123():
        held = {_k: _v for _k, _v in bank_ids().items()}
        step = decide(started(Fake(**{'inv_ids': held, 'inv': {_k: _v for _k, _v in [['lobster', 8]]}})))
        expect(step.kind).not_.to_be('withdraw')
    test('nothing is drawn twice — a full pack moves the quest on', _fn123)

    def _fn124():
        gear = {_k: _v for _k, _v in bank_ids().items()}
        gear.pop(WT_ITEM.COINS.id, None)
        step = decide(started(Fake(**{
        'inv_ids': {_k: _v for _k, _v in list(gear.items()) + [[WT_ITEM.COINS.id, 1977]]},
        'inv': {_k: _v for _k, _v in [['lobster', 8]]},
    })))
        expect(step.kind).not_.to_be('withdraw')
    test('a purse a few coins short does not buy another bank trip', _fn124)

    def _fn125():
        step = decide(started(Fake(**{'inv_ids': {_k: _v for _k, _v in bank_ids().items()}, 'inv': {_k: _v for _k, _v in [['lobster', 5]]}})))
        expect(step.kind).not_.to_be('withdraw')
    test('food eaten down does not buy another bank trip', _fn125)

    def _fn126():
        short = {_k: _v for _k, _v in bank_ids().items()}
        short.pop(WT_ITEM.ROPE.id, None)
        short[WT_ITEM.COINS.id] = 1977
        step = decide(started(Fake(**{'inv_ids': short, 'inv': {_k: _v for _k, _v in [['lobster', 5]]}})))
        expect(step.kind).to_be('withdraw')
        names = ([i['name'] for i in step.items] if step.kind == 'withdraw' else [])
        expect(names).to_contain('Rope')
        expect(names).to_contain('Coins')
        expect(names).to_contain('Lobster')
    test('a missing piece of gear still brings the purse and the food with it', _fn126)

    def _fn127():
        expect(decide(started(Fake(**{'bank_known': False}))).kind).not_.to_be('withdraw')
    test('an unread bank is left alone, so a quest wanting nothing takes no trip', _fn127)


describe('the kit comes out of the bank in one trip', _fn118)


# Live: Watch Tower resumed after The Grand Tree with a full pack, and Aemad refused the rope 30 times.
def _fn128():
    def _fn129():
        step = decide(snapshot(Fake(**{
            'stage': WATCHTOWER_STAGE.GIVEN_FINGERNAILS,
            'inv': {'bark sample': 1, 'lobster': 20, 'dragon bones': 1, 'coins': 500},
            'inv_ids': {783: 1, 379: 20, WT_ITEM.DRAGON_BONES.id: 1, WT_ITEM.COINS.id: 500},
            'free_slots': 0,
        })))
        expect(step.kind).to_be('deposit')
        expect(step.keep_ids).to_contain(WT_ITEM.DRAGON_BONES.id)
        expect(step.keep_ids).to_contain(WT_ITEM.COINS.id)
        expect([k.lower() for k in step.keep]).to_contain('lobster')
    test('a full pack of another quest\'s leftovers banks them, keeping the kit and the food', _fn129)

    def _fn130():
        step = decide(snapshot(Fake(**{
            'stage': WATCHTOWER_STAGE.GIVEN_FINGERNAILS,
            'inv': {'lobster': 26, 'dragon bones': 1, 'coins': 500},
            'inv_ids': {379: 26, WT_ITEM.DRAGON_BONES.id: 1, WT_ITEM.COINS.id: 500},
            'free_slots': 0,
        })))
        expect(step.kind).not_.to_be('deposit')
    test('a full pack of only kit and food has nothing to bank, so it takes no trip', _fn130)

    def _fn131():
        step = decide(snapshot(Fake(**{
            'stage': WATCHTOWER_STAGE.GIVEN_FINGERNAILS,
            'inv': {'bark sample': 1},
            'inv_ids': {783: 1},
            'free_slots': 27,
        })))
        expect(step.kind).not_.to_be('deposit')
    test('a pack with room keeps its leftovers', _fn131)


describe('a full pack makes room before the kit', _fn128)


# Live: a death in Toban's camp took the parts after every tribe was helped, and the stage parked 3x.
def _fn132():
    from rs2004.quests.defs.watchtower.tower import relic_state
    tribes_done = P(2, 'helped-og', 'helped-toban', 'helped-grew')
    berries = [WT_ITEM.JANGERBERRIES.id, 2]

    def fresh():
        relic_state.asked = set()
        relic_state.refused = set()

    def _fn133():
        fresh()
        step = decide(snapshot(Fake(**{'progress': tribes_done, 'inv_ids': {_k: _v for _k, _v in [berries]}})))
        expect(step.kind).to_be('custom')
        expect(mentions(step.name, 'ask og ')).to_be(True)
    test('lost parts with every tribe helped ask Og for another first', _fn133)

    def _fn134():
        fresh()
        relic_state.asked.add(WT_ITEM.RELIC_PART1.id)
        step = decide(snapshot(Fake(**{'progress': tribes_done, 'inv_ids': {_k: _v for _k, _v in [berries]}})))
        expect(mentions(step.name, 'ask toban ')).to_be(True)
    test('once Og has been asked, Toban is next', _fn134)

    def _fn135():
        fresh()
        relic_state.asked.add(WT_ITEM.RELIC_PART1.id)
        relic_state.asked.add(WT_ITEM.RELIC_PART3.id)
        step = decide(snapshot(Fake(**{'progress': tribes_done, 'inv_ids': {_k: _v for _k, _v in [berries]}})))
        expect(step.kind).to_be('buy')
        expect(step.item).to_be('Rope')
    test('Grew goes last, and costs a rope', _fn135)

    def _fn136():
        fresh()
        relic_state.refused.add(WT_ITEM.RELIC_PART1.id)
        relic_state.asked.add(WT_ITEM.RELIC_PART1.id)
        step = decide(snapshot(Fake(**{'progress': tribes_done, 'inv_ids': {_k: _v for _k, _v in [berries, [WT_ITEM.RELIC_PART1.id, 1]]}})))
        expect(mentions(step.name, 'give')).to_be(False)
        expect(mentions(step.name, 'ask toban ')).to_be(True)
    test('a part the wizard already holds is not offered again', _fn136)

    def _fn137():
        fresh()
        for part in [WT_ITEM.RELIC_PART1, WT_ITEM.RELIC_PART2, WT_ITEM.RELIC_PART3]:
            relic_state.asked.add(part.id)
        step = decide(snapshot(Fake(**{'progress': tribes_done, 'inv_ids': {_k: _v for _k, _v in [berries]}})))
        fresh()
        expect(step.kind).to_be('wait')
    test('with every tribe asked it still waits rather than looping', _fn137)


describe('lost relic parts come back from the tribes', _fn132)


# Live: the Magic Guild's door turned a Magic 21 account away, and the riddle's death rune parked the quest.
def _fn138():
    def riddle(magic):
        return decide(snapshot(Fake(**{'stage': WATCHTOWER_STAGE.GIVEN_RIDDLE, 'magic': magic, 'inv_ids': {WT_ITEM.COINS.id: 500}})))

    def _fn139():
        step = riddle(21)
        expect(step.kind).to_be('buy')
        expect(step.shop.npc).to_be('Aubury')
    test('under Magic 66 the death rune comes from Aubury', _fn139)

    def _fn140():
        step = riddle(66)
        expect(step.kind).to_be('buy')
        expect(step.shop.npc).to_be('Magic Store owner')
    test('at Magic 66 the guild sells it', _fn140)


describe("the riddle's death rune is bought where the account can enter", _fn138)


# Live: 8 lobsters wanted into 3 free slots drew 3, then asked for 5 into a full pack until the quest parked.
def _fn141():
    from rs2004.quests.defs.watchtower.supplies import source_food

    def pack(free, lobsters):
        return snapshot(Fake(**{'free_slots': free, 'inv': {'lobster': lobsters}, 'bank': {'lobster': 100}}))

    def _fn142():
        step = source_food(pack(3, 0), 8)
        expect(step.kind).to_be('withdraw')
        expect(step.items[0]['qty']).to_be(3)
    test('the food draw stops at the free slots', _fn142)

    def _fn143():
        expect(source_food(pack(0, 3), 8)).to_be(None)
    test('a full pack with some food goes on with what it carries', _fn143)

    def _fn144():
        expect(source_food(pack(0, 0), 8).kind).to_be('wait')
    test('a full pack with no food waits rather than retrying the bank', _fn144)


describe('the enclave food fits the pack', _fn141)
