"""rs2b0t's test/api/ai/quests/defs/grandtree.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs.record import Record
from rs2004.quests.defs.grandtree import decide, grandtree
from rs2004.quests.defs.grandtree.areas import GT_OBJ, GT_STAGE, GT_TILE, NARNODE_TRANSLATION
from rs2004.quests.engine.types import QuestSnapshot
from rs2004.quests.food import quest_food

STRONGHOLD = Record({'x': 2466, 'z': 3497, 'level': 0})
KARAMJA = Record({'x': 2999, 'z': 3043, 'level': 0})
CAVES = Record({'x': 2491, 'z': 9864, 'level': 0})


def counts(names):
    out = {}
    for name in names:
        key = name.lower()
        _v1 = out.get(key)
        out[key] = ((_v1 if _v1 is not None else 0)) + 1
    return out


def id_counts(ids):
    out = {}
    for id in ids:
        _v2 = out.get(id)
        out[id] = ((_v2 if _v2 is not None else 0)) + 1
    return out


def snap(options=None):
    if options is None:
        options = Record({})
    return QuestSnapshot(**{
        'journal': (options.journal if options.journal is not None else 'in_progress'),
        'inv': {_k: _v for _k, _v in list(counts((options.inv if options.inv is not None else [])).items()) + [['mind rune', 150], ['air rune', 150]]},
        'inv_ids': id_counts((options.inv_ids if options.inv_ids is not None else [])),
        'worn': set([n.lower() for n in ((options.worn if options.worn is not None else []))]),
        'no_progress': 0,
        'bank_coins': 2000000,
        'stage': options.stage,
        'bank': counts((options.bank if options.bank is not None else [])),
        'bank_known': (options.bank_known if options.bank_known is not None else True),
        'tile': (options.tile if options.tile is not None else STRONGHOLD),
        'free_slots': (options.free_slots if options.free_slots is not None else 20),
    })


def talk_target(step):
    return (step.stop.npc if step.kind == 'talk' else None)


def custom_name(step):
    return (step.name if step.kind == 'custom' else None)


def _fn3():
    quest_food.name = 'Trout'


after_each(_fn3)


def _fn4():
    def _fn5():
        expect(decide(snap(Record({'journal': 'complete'}))).kind).to_be('done')
        expect(decide(snap(Record({'journal': 'unknown'}))).kind).to_be('wait')
    test('a green quest list is done and a blank one waits', _fn5)

    def _fn6():
        step = decide(snap(Record({'stage': None})))
        expect(step.kind).to_be('wait')
        expect(step.kind == 'wait' and step.reason).to_contain('stage unavailable')
    test('an unreadable journal waits rather than restarting the quest', _fn6)

    def _fn7():
        expect(custom_name(decide(snap(Record({'journal': 'not_started', 'stage': GT_STAGE.NOT_STARTED}))))).to_be('start the quest with King Narnode')
    test('starts by talking to King Narnode', _fn7)

    def _fn8():
        step = decide(snap(Record({'stage': GT_STAGE.NOT_STARTED, 'free_slots': 1})))
        expect(step.kind).to_be('deposit')
        expect(step.kind == 'deposit' and step.keep).to_contain('bark sample')
    test('banks junk when the pack has no room for the bark sample and the book', _fn8)

    def _fn9():
        expect(talk_target(decide(snap(Record({'stage': GT_STAGE.STARTED, 'inv_ids': [GT_OBJ.BARK]}))))).to_be('Hazelmere')
        expect(talk_target(decide(snap(Record({'stage': GT_STAGE.SPOKEN_HAZELMERE}))))).to_be('King Narnode Shareen')
    test('carries the bark sample to Hazelmere, then the message back to the King', _fn9)

    def _fn10():
        expect(talk_target(decide(snap(Record({'stage': GT_STAGE.STARTED}))))).to_be('King Narnode Shareen')
    test('a lost bark sample goes back to the King for another rather than to Hazelmere', _fn10)

    def _fn11():
        expect(talk_target(decide(snap(Record({'stage': GT_STAGE.RELAYED_MESSAGE}))))).to_be('Glough')
        expect(talk_target(decide(snap(Record({'stage': GT_STAGE.SPOKEN_GLOUGH}))))).to_be('King Narnode Shareen')
    test('relays the message to Glough and reports back', _fn11)

    def _fn12():
        expect(talk_target(decide(snap(Record({'stage': GT_STAGE.FOUND_PRISONER}))))).to_be('Charlie')
        expect(custom_name(decide(snap(Record({'stage': GT_STAGE.SPOKEN_PRISONER}))))).to_be("search Glough's cupboard")
    test('visits the prisoner, then searches the cupboard he points at', _fn12)

    def _fn13():
        expect(custom_name(decide(snap(Record({'stage': GT_STAGE.FOUND_JOURNAL}))))).to_be('confront Glough and get out of his cage')
    test('takes the journal back to Glough and expects the cage', _fn13)

    def _fn14():
        expect(custom_name(decide(snap(Record({'stage': GT_STAGE.RELEASED_PRISON, 'tile': STRONGHOLD}))))).to_be('take the glider to Karamja')
        expect(custom_name(decide(snap(Record({'stage': GT_STAGE.RELEASED_PRISON, 'tile': KARAMJA}))))).to_be('get the lumber order from the foreman')
    test('stage 80 flies out of the stronghold, and talks to the foreman once it lands', _fn14)

    def _fn15():
        expect(custom_name(decide(snap(Record({'stage': GT_STAGE.OBTAINED_LUMBER_ORDER, 'tile': KARAMJA}))))).to_be("ride Femi's cart into the stronghold")
        expect(talk_target(decide(snap(Record({'stage': GT_STAGE.OBTAINED_LUMBER_ORDER, 'tile': STRONGHOLD}))))).to_be('Charlie')
    test('stage 90 rides the cart back in from outside, and talks to Charlie once inside', _fn15)

    def _fn16():
        expect(custom_name(decide(snap(Record({'stage': GT_STAGE.CLUE_CHARLIE}))))).to_be('ask Anita for the chest key')
        expect(custom_name(decide(snap(Record({'stage': GT_STAGE.CLUE_CHARLIE, 'inv_ids': [GT_OBJ.KEY]}))))).to_be("unlock Glough's chest")
    test('stage 100 fetches the key before it opens the chest', _fn16)

    def _fn17():
        holding = Record({'stage': GT_STAGE.FOUND_INVASION_PLANS, 'inv_ids': [GT_OBJ.INVASION_PLANS]})
        cramped = Record({'stage': GT_STAGE.FOUND_INVASION_PLANS, 'inv_ids': [GT_OBJ.INVASION_PLANS], 'free_slots': 3})
        expect(decide(snap(cramped)).kind).to_be('deposit')
        expect(talk_target(decide(snap(holding)))).to_be('King Narnode Shareen')
    test('the plans need four free slots for the twigs the King answers with', _fn17)

    def _fn19():
        expect(custom_name(decide(snap(Record({'stage': GT_STAGE.FOUND_INVASION_PLANS, 'inv_ids': [GT_OBJ.KEY]}))))).to_be("unlock Glough's chest")
    test('plans lost after the chest was opened re-run the chest instead of parking', _fn19)

    def _fn20():
        expect(custom_name(decide(snap(Record({'stage': GT_STAGE.DEFEATED_BLACK_DEMON, 'tile': STRONGHOLD}))))).to_be('drop back into the root caves')
        expect(custom_name(decide(snap(Record({'stage': GT_STAGE.SEARCHING_DACONIA, 'tile': STRONGHOLD}))))).to_be('drop back into the root caves')
    test('the caves are re-entered before anything past the demon is attempted', _fn20)

    def _fn21():
        all_ = snap(Record({'stage': GT_STAGE.GIVEN_TWIGS, 'inv_ids': [GT_OBJ.TWIG_T, GT_OBJ.TWIG_U, GT_OBJ.TWIG_Z, GT_OBJ.TWIG_O]}))
        expect(custom_name(decide(all_))).to_be('lay twig 1 of 4 on its pillar')
        two_left = snap(Record({'stage': GT_STAGE.GIVEN_TWIGS, 'inv_ids': [GT_OBJ.TWIG_Z, GT_OBJ.TWIG_O]}))
        expect(custom_name(decide(two_left))).to_be('lay twig 3 of 4 on its pillar')
    test('lays each held twig on its own pillar, in the order the trapdoor checks them', _fn21)

    def _fn22():
        expect(talk_target(decide(snap(Record({'stage': GT_STAGE.GIVEN_TWIGS}))))).to_be('King Narnode Shareen')
    test('an empty pack at stage 120 asks the King for another set rather than waiting', _fn22)

    def _fn23():
        quest_food.name = 'Lobster'
        step = decide(snap(Record({'stage': GT_STAGE.UNLOCKED_TRAPDOOR, 'bank': ['lobster', 'lobster', 'lobster']})))
        expect(step.kind).to_be('withdraw')
        expect(step.kind == 'withdraw' and step.items[0]['name']).to_be('Lobster')
    test('kits up for the demon while the trapdoor is still shut', _fn23)

    def _fn24():
        quest_food.name = 'Lobster'
        step = decide(snap(Record({'stage': GT_STAGE.GIVEN_TWIGS, 'inv_ids': [GT_OBJ.TWIG_T], 'bank': ['lobster', 'lobster', 'lobster']})))
        expect(step.kind).to_be('withdraw')
    test('the kit is bought at stage 120, before the first climb to the pillars', _fn24)

    def _fn25():
        quest_food.name = 'Lobster'
        pillars = Record({'x': 2486, 'z': 3465, 'level': 2})
        expect(custom_name(decide(snap(Record({'stage': GT_STAGE.GIVEN_TWIGS, 'tile': pillars, 'bank': ['lobster']}))))).to_be("climb down out of Glough's tree for the kit")
        expect(custom_name(decide(snap(Record({'stage': GT_STAGE.UNLOCKED_TRAPDOOR, 'tile': pillars, 'bank': ['lobster']}))))).to_be("climb down out of Glough's tree for the kit")
    test('a kit still owed from the pillar floor climbs down for it rather than banking in the pocket', _fn25)

    def _fn26():
        quest_food.name = 'Lobster'
        step = decide(snap(Record({'stage': GT_STAGE.UNLOCKED_TRAPDOOR, 'bank_known': False})))
        expect(step.kind).to_be('scan_bank')
    test('an unknown bank is scanned before the demon rather than guessed at', _fn26)

    def _fn27():
        quest_food.name = 'Lobster'
        stocked = ['Lobster'] * 10
        expect(custom_name(decide(snap(Record({'stage': GT_STAGE.UNLOCKED_TRAPDOOR, 'inv': stocked}))))).to_be('take the trapdoor and kill the Black Demon')
    test('once the pack is stocked, stage 130 goes down the trapdoor', _fn27)

    def _fn28():
        quest_food.name = 'Lobster'
        step = decide(snap(Record({'stage': GT_STAGE.UNLOCKED_TRAPDOOR, 'tile': CAVES, 'bank': ['lobster']})))
        expect(custom_name(step)).to_be('take the trapdoor and kill the Black Demon')
    test('preparation stops at the door — inside the caves nothing banks', _fn28)

    def _fn29():
        expect(talk_target(decide(snap(Record({'stage': GT_STAGE.DEFEATED_BLACK_DEMON, 'tile': CAVES}))))).to_be('King Narnode Shareen')
        expect(custom_name(decide(snap(Record({'stage': GT_STAGE.SEARCHING_DACONIA, 'tile': CAVES}))))).to_be('search the roots for the Daconia rock')
        expect(custom_name(decide(snap(Record({'stage': GT_STAGE.SEARCHING_DACONIA, 'tile': CAVES, 'inv_ids': [GT_OBJ.DACONIA]}))))).to_be('give the King the Daconia rock')
    test('reports the fight to the King underground, then hunts the roots', _fn29)

    def _fn30():
        step = decide(snap(Record({'stage': GT_STAGE.DEFEATED_BLACK_DEMON, 'tile': CAVES})))
        expect(step.kind == 'talk' and step.stop.anchor.z).to_be(GT_TILE.narnode_under.z)
    test('the underground King is the one stage 140 walks to', _fn30)


describe('The Grand Tree decide()', _fn4)


def _fn31():
    def _fn32():
        expect(grandtree.tools).to_contain('twigs')
        expect(grandtree.tools).to_contain('daconia rock')
    test('keeps every quest item off the spillover deposit', _fn32)

    def _fn33():
        expect(grandtree.bank).to_be('nearest')
    test('banks wherever it is standing, since the quest crosses three kingdoms', _fn33)

    def _fn34():
        expect(grandtree.coin_float).to_be_greater_than_or_equal(1030)
    test("carries a float Femi's 1000gp cart fare and the Brimhaven fare both fit inside", _fn34)

    def _fn35():
        expect((NARNODE_TRANSLATION.index('None of the above.') if 'None of the above.' in NARNODE_TRANSLATION else -1)).to_be_greater_than((NARNODE_TRANSLATION.index("A man came to me with the King's seal.") if "A man came to me with the King's seal." in NARNODE_TRANSLATION else -1))
        expect((NARNODE_TRANSLATION.index('None of the above.') if 'None of the above.' in NARNODE_TRANSLATION else -1)).to_be_greater_than((NARNODE_TRANSLATION.index('And Daconia rocks will kill the tree!') if 'And Daconia rocks will kill the tree!' in NARNODE_TRANSLATION else -1))
    test('the translation answers are ordered so the two "None of the above." pages fall through', _fn35)


describe('The Grand Tree module', _fn31)
