"""Ported from rs2b0t's test/api/ai/quests/defs/heroquest-supplies.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestProgress, QuestSnapshot
from rs2004.game import skills
from rs2004.quests.defs.heroquest.areas import HERO_ID, HERO_NAMED
from rs2004.quests.defs.heroquest.blackarm import disguise_owned, disguise_step
from rs2004.quests.defs.heroquest.eel import eel_step
from rs2004.quests.defs.heroquest.feather import combat_kit_step, feather_step
from rs2004.quests.defs.heroquest.phoenix import snipe_kit_owned, snipe_kit_step
from rs2004.quests.food import quest_food

def snap(over=None):
    if over is None:
        over = Fake()
    _merged1 = {}
    for _k, _v in {
        'journal': 'in_progress',
        'inv': {},
        'inv_ids': {},
        'worn': set(),
        'worn_ids': set(),
        'no_progress': 0,
        'bank_coins': 2000000,
        'bank': {},
        'bank_ids': {},
        'bank_known': True,
        'tile': Record({'x': 3210, 'z': 3490, 'level': 0}),
        'free_slots': 20,
    }.items():
        _merged1[_k] = _v
    for _k, _v in over._fields.items():
        _merged1[_k] = _v
    return QuestSnapshot(**_merged1)


def name(step):
    return repr(step._fields) if step is not None else '{}'


def _fn2():
    def _fn3():
        expect(name(disguise_step(snap()))).to_contain(HERO_NAMED.BLACK_PLATEBODY)
    test('an empty pack buys the platebody first', _fn3)

    def _fn4():
        expect(disguise_step(snap(Fake(**{'inv_ids': {_k: _v for _k, _v in [[HERO_ID.BLACK_PLATEBODY, 1]]}})))).to_match_object(Record({'kind': 'equip', 'item': HERO_NAMED.BLACK_PLATEBODY}))
    test('a bought piece is worn rather than bought again', _fn4)

    def _fn5():
        expect(disguise_step(snap(Fake(**{'bank_ids': {_k: _v for _k, _v in [[HERO_ID.BLACK_PLATEBODY, 1]]}})))).to_match_object(Record({'kind': 'withdraw'}))
    test('a banked piece is withdrawn', _fn5)

    def _fn6():
        worn = set([HERO_ID.BLACK_PLATEBODY, HERO_ID.BLACK_PLATELEGS, HERO_ID.BLACK_FULL_HELM])
        expect(disguise_step(snap(Fake(**{'worn_ids': worn})))).to_be_null()
        expect(disguise_owned(snap(Fake(**{'worn_ids': worn})))).to_be(True)
    test('all three worn is nothing left to do', _fn6)


describe('the Black Arm disguise', _fn2)


# Why: `World.restock` skips a null slot, so a shared shop that sells its last unit is a one-shot
# source, the legs list both stockists and the buy leg falls through to the second.
def _fn7():
    def _fn8():
        step = disguise_step(snap(Fake(**{'worn_ids': set([HERO_ID.BLACK_PLATEBODY])})))
        expect(name(step)).to_contain(HERO_NAMED.BLACK_PLATELEGS)
        expect(step).to_match_object(Record({'kind': 'custom'}))
    test('the legs name both stockists', _fn8)


describe('the Black Arm platelegs', _fn7)


def _fn9():
    def _fn10():
        expect(name(snipe_kit_step(snap()))).to_contain(HERO_NAMED.OAK_LONGBOW)
    test('an empty pack buys the bow first', _fn10)

    def _fn11():
        expect(name(snipe_kit_step(snap(Fake(**{'worn_ids': set([HERO_ID.OAK_LONGBOW])}))))).to_contain(HERO_NAMED.STEEL_ARROW)
    test('a worn bow moves on to the arrows', _fn11)

    def _fn12():
        worn = set([HERO_ID.OAK_LONGBOW, HERO_ID.STEEL_ARROW])
        expect(snipe_kit_step(snap(Fake(**{'worn_ids': worn})))).to_be_null()
        expect(snipe_kit_owned(snap(Fake(**{'worn_ids': worn})))).to_be(True)
    test('bow and arrows worn is nothing left to do', _fn12)


describe('the Phoenix snipe kit', _fn9)


# Why: each branch reads what is carried, so a restart anywhere in the chain picks it up where it
# stopped rather than starting the herb grind again.
def _fn13():
    def _fn14():
        expect(eel_step(snap(Fake(**{'bank_ids': {_k: _v for _k, _v in [[HERO_ID.LAVA_EEL, 1]]}})))).to_be_null()
    test('a cooked eel anywhere ends the chain', _fn14)

    def _fn15():
        expect(name(eel_step(snap(Fake(**{'inv_ids': {_k: _v for _k, _v in [[HERO_ID.RAW_LAVA_EEL, 1]]}}))))).to_contain('cook')
    test('a raw eel is cooked', _fn15)

    def _fn16():
        expect(eel_step(snap(Fake(**{'inv_ids': {_k: _v for _k, _v in [[HERO_ID.OILY_ROD, 1]]}})))).to_match_object(Record({'kind': 'buy', 'item': HERO_NAMED.FISHING_BAIT}))
    test('an oiled rod with no bait buys bait', _fn16)

    # Why: the lava spots are behind `deepdungeondoor`, which opens only to the dusty key.
    def _fn17():
        step = eel_step(snap(Fake(**{'inv_ids': {_k: _v for _k, _v in [[HERO_ID.OILY_ROD, 1], [HERO_ID.FISHING_BAIT, 40]]}})))
        expect(name(step)).to_contain('Jailer')
    test('an oiled rod with bait and no keys goes for the Jailer', _fn17)

    def _fn18():
        step = eel_step(snap(Fake(**{'inv_ids': {_k: _v for _k, _v in [[HERO_ID.OILY_ROD, 1], [HERO_ID.FISHING_BAIT, 40], [HERO_ID.JAIL_KEY, 1]]}})))
        expect(name(step)).to_contain('Velrak')
    test('the jail key frees Velrak', _fn18)

    def _fn19():
        expect(eel_step(snap(Fake(**{
        'inv_ids': {_k: _v for _k, _v in [[HERO_ID.OILY_ROD, 1], [HERO_ID.FISHING_BAIT, 40]]},
        'bank_ids': {_k: _v for _k, _v in [[HERO_ID.DUSTY_KEY, 1]]},
    })))).to_match_object(Record({'kind': 'withdraw'}))
    test('a banked dusty key is withdrawn rather than re-earned', _fn19)

    def _fn20():
        step = eel_step(snap(Fake(**{'inv_ids': {_k: _v for _k, _v in [[HERO_ID.OILY_ROD, 1], [HERO_ID.FISHING_BAIT, 40], [HERO_ID.DUSTY_KEY, 1]]}})))
        expect(name(step)).to_contain('fish a lava eel')
    test('an oiled rod with bait and the dusty key fishes', _fn20)

    def _fn21():
        step = eel_step(snap(Fake(**{'inv_ids': {_k: _v for _k, _v in [[HERO_ID.BLAMISH_OIL, 1], [HERO_ID.FISHING_ROD, 1]]}})))
        expect(name(step)).to_contain('rub the blamish oil')
    test('oil plus a rod makes the oiled rod', _fn21)

    def _fn22():
        expect(eel_step(snap(Fake(**{'inv_ids': {_k: _v for _k, _v in [[HERO_ID.BLAMISH_OIL, 1]]}})))).to_match_object(Record({'kind': 'buy', 'item': HERO_NAMED.FISHING_ROD}))
    test('oil with no rod buys a rod', _fn22)

    def _fn23():
        expect(name(eel_step(snap(Fake(**{'inv_ids': {_k: _v for _k, _v in [[HERO_ID.HARRALANDER_VIAL, 1]]}}))))).to_contain('Gerrant')
    test('an unfinished potion with no slime asks Gerrant for one', _fn23)

    def _fn24():
        step = eel_step(snap(Fake(**{'inv_ids': {_k: _v for _k, _v in [[HERO_ID.HARRALANDER_VIAL, 1], [HERO_ID.SLIME, 1]]}})))
        expect(name(step)).to_contain('mix the slime')
    test('an unfinished potion and slime makes the oil', _fn24)

    def _fn25():
        expect(eel_step(snap(Fake(**{'inv_ids': {_k: _v for _k, _v in [[HERO_ID.HARRALANDER, 1]]}})))).to_match_object(Record({'kind': 'buy', 'item': HERO_NAMED.VIAL_WATER}))
    test('a clean harralander with no vial buys one', _fn25)

    def _fn26():
        expect(name(eel_step(snap(Fake(**{'inv_ids': {_k: _v for _k, _v in [[HERO_ID.UNID_HARRALANDER, 1]]}}))))).to_contain('identify')
    test('a grimy herb is identified', _fn26)

    # Why: twenty-five level-13 druids add up with no food in the pack.
    def _fn27():
        quest_food.name = 'Lobster'
        expect(eel_step(snap())).to_match_object(Record({'kind': 'withdraw'}))
    test('an empty pack withdraws food before the druids', _fn27)

    # Why: nothing sells harralander and it has no ground spawn, so the druids are the only source.
    def _fn28():
        quest_food.name = 'Lobster'
        expect(name(eel_step(snap(Fake(**{'inv': {_k: _v for _k, _v in [['lobster', 16]]}}))))).to_contain('chaos druids')
    test('a fed pack farms chaos druids', _fn28)


describe('the lava eel chain', _fn13)


def _fn29():
    def _fn30():
        spy_on(skills, 'level').mock_return_value(50)
    before_each(_fn30)

    def _fn31():
        expect(feather_step(snap(Fake(**{'bank_ids': {_k: _v for _k, _v in [[HERO_ID.FEATHER, 1]]}})))).to_be_null()
    test('a feather anywhere ends the chain', _fn31)

    def _fn32():
        expect(name(feather_step(snap()))).to_contain('Rune chainbody')
    test('without gloves it buys the Ice Queen kit first', _fn32)

    def _fn33():
        expect(feather_step(snap(Fake(**{'bank_ids': {_k: _v for _k, _v in [[HERO_ID.ICE_GLOVES, 1]]}})))).to_match_object(Record({'kind': 'withdraw'}))
    test('banked gloves are withdrawn rather than fought for', _fn33)

    def _fn34():
        quest_food.name = 'Lobster'
        step = feather_step(snap(Fake(**{
        'worn_ids': set([1113, 1079, 1303]),
        'inv_ids': {_k: _v for _k, _v in [[1265, 1]]},
        'inv': {_k: _v for _k, _v in [['lobster', 12]]},
    })))
        expect(name(step)).to_contain('Ice Queen')
    test('kitted and fed, it goes for the Ice Queen', _fn34)

    # Why: Entrana's monks refuse every `armour_*` and `weapon_*` category; the gloves carry none.
    def _fn35():
        expect(feather_step(snap(Fake(**{
        'inv_ids': {_k: _v for _k, _v in [[HERO_ID.ICE_GLOVES, 1]]},
        'inv': {_k: _v for _k, _v in [['ice gloves', 1], ['rune longsword', 1]]},
    })))).to_match_object(Record({'kind': 'deposit'}))
    test('holding the gloves, a full pack is banked before the ferry', _fn35)

    def _fn36():
        step = feather_step(snap(Fake(**{
        'inv_ids': {_k: _v for _k, _v in [[HERO_ID.ICE_GLOVES, 1]]},
        'inv': {_k: _v for _k, _v in [['ice gloves', 1], ['coins', 1000]]},
    })))
        expect(name(step)).to_contain('Entrana')
    test('a stripped pack sails', _fn36)

    # Why: the engine lower-cases `worn`, so a display-cased comparison strips forever.
    def _fn37():
        step = feather_step(snap(Fake(**{
        'inv_ids': {_k: _v for _k, _v in [[HERO_ID.ICE_GLOVES, 1]]},
        'inv': {_k: _v for _k, _v in [['ice gloves', 1]]},
        'worn': set(['ice gloves']),
        'worn_ids': set([HERO_ID.ICE_GLOVES]),
    })))
        expect(name(step)).to_contain('Entrana')
    test('the gloves alone are not something to strip', _fn37)

    def _fn38():
        step = feather_step(snap(Fake(**{
        'inv_ids': {_k: _v for _k, _v in [[HERO_ID.ICE_GLOVES, 1]]},
        'inv': {_k: _v for _k, _v in [['ice gloves', 1]]},
        'worn': set(['rune platelegs']),
        'worn_ids': set([1079]),
    })))
        expect(name(step)).to_contain('strip')
    test('worn armour is stripped before the ferry', _fn38)

    def _fn39():
        step = feather_step(snap(Fake(**{
        'inv_ids': {_k: _v for _k, _v in [[HERO_ID.ICE_GLOVES, 1]]},
        'inv': {_k: _v for _k, _v in [['ice gloves', 1]]},
        'tile': Record({'x': 2847, 'z': 3387, 'level': 0}),
    })))
        expect(name(step)).to_contain('feather')
    test('on the island it takes the feather', _fn39)

    def _fn40():
        step = feather_step(snap(Fake(**{
        'inv_ids': {_k: _v for _k, _v in [[HERO_ID.FEATHER, 1]]},
        'tile': Record({'x': 2847, 'z': 3387, 'level': 0}),
    })))
        expect(name(step)).to_contain('sail back')
    test('holding the feather on the island, it sails home', _fn40)

    def _fn41():
        expect(name(combat_kit_step(snap()))).to_contain('buy')
        expect(combat_kit_step(snap(Fake(**{'worn_ids': set([1113, 1079, 1303])})))).to_be_null()
    test('the combat kit is bought once and worn after', _fn41)


describe('the firebird feather chain', _fn29)


def _fn42():
    spy_on(skills, 'level').mock_return_value(50)
    expect(feather_step(snap(Fake(**{'worn_ids': set([1113, 1079, 1303]), 'bank_ids': {_k: _v for _k, _v in [[1275, 1]]}})))).to_match_object(Record({'kind': 'withdraw', 'items': [{'name': 'Rune pickaxe', 'qty': 1, 'id': 1275}]}))


test('the Ice Queen leg withdraws a banked pickaxe without replacing the combat weapon', _fn42)


def _fn43():
    spy_on(skills, 'level').mock_return_value(50)
    expect(feather_step(snap(Fake(**{'worn_ids': set([1113, 1079, 1303])})))).to_match_object(Record({'kind': 'grab_ground', 'item': 'Bronze pickaxe', 'wait_if_missing': True}))


test('the Ice Queen leg acquires a free bronze pickaxe when none is owned', _fn43)


def _fn44():
    spy_on(skills, 'level').mock_return_value(49)
    step = feather_step(snap())
    expect(step.kind).to_be('wait')
    expect(step.reason).to_contain('50 Mining')


test('the Ice Queen leg reports the Mining requirement before buying equipment', _fn44)
