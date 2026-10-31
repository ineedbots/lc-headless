"""Ported from rs2b0t's test/api/ai/quests/defs/biohazard.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot
from rs2004.quests.defs.biohazard import biohazard, decide
from rs2004.quests.defs.biohazard.areas import BIO_ITEM, VIALS, bio_area, in_guidor_quarter, in_pigeon_zone
from rs2004.quests.defs.biohazard.journal import BIO_STAGE
from rs2004.quests.defs.biohazard.supplies import FOOD

ARDOUGNE = Record({'x': 2616, 'z': 3332, 'level': 0})
WEST = Record({'x': 2529, 'z': 3304, 'level': 0})
HQ = Record({'x': 2551, 'z': 3321, 'level': 0})
HQ_TOP = Record({'x': 2550, 'z': 3326, 'level': 1})
QUARTER = Record({'x': 3270, 'z': 3390, 'level': 0})
RIMMINGTON = Record({'x': 2934, 'z': 3211, 'level': 0})
PURSE = {_k: _v for _k, _v in [[BIO_ITEM.COINS.id, 2000000]]}


# Why: the overrides are a plain dict, since a Record can't hold the id-keyed maps.
def option(o, key, default):
    value = o.get(key)
    return default if value is None else value


def snapshot(o=None):
    if o is None:
        o = {}
    return QuestSnapshot(**{
        'journal': option(o, 'journal', 'in_progress'),
        'inv': option(o, 'inv', {}),
        'inv_ids': option(o, 'inv_ids', {}),
        'worn': option(o, 'worn', set()),
        'worn_ids': option(o, 'worn_ids', set()),
        'no_progress': option(o, 'no_progress', 0),
        'bank_coins': option(o, 'bank_coins', 0),
        'stage': o.get('stage'),
        'progress': o.get('progress'),
        'bank': option(o, 'bank', {}),
        'bank_ids': option(o, 'bank_ids', PURSE),
        'bank_known': option(o, 'bank_known', True),
        'tile': ARDOUGNE if 'tile' not in o else o['tile'],
        'free_slots': option(o, 'free_slots', 28),
    })


def carrying(*items):
    return {_k: _v for _k, _v in [[item.id, qty] for item, qty in items]}


def name(step):
    return ((step.name if step.kind == 'custom' else step.kind))


PROVISIONED = carrying([FOOD, 5], [BIO_ITEM.COINS, 5000])
ALL_VIALS = carrying(*[[vial, 1] for vial in VIALS])
KIT = {_k: _v for _k, _v in list(ALL_VIALS.items()) + [[BIO_ITEM.PLAGUE_SAMPLE.id, 1], [BIO_ITEM.TOUCH_PAPER.id, 1], [BIO_ITEM.PRIEST_GOWN.id, 1], [BIO_ITEM.PRIEST_ROBE.id, 1]]}


def _fn2():
    def _fn3():
        expect(bio_area(HQ)).to_be('hq')
        expect(bio_area(WEST)).to_be('west')
        expect(bio_area(HQ_TOP)).to_be('hqUpstairs')
    test('the headquarters building is its own area, not West Ardougne', _fn3)

    def _fn4():
        expect(bio_area(Record({'x': 2559, 'z': 3266, 'level': 0}))).to_be('mainland')
        expect(bio_area(Record({'x': 2556, 'z': 3266, 'level': 0}))).to_be('west')
    test('Omart stands on the mainland and Kilron on the West Ardougne side', _fn4)

    def _fn5():
        expect(bio_area(Record({'x': 2578, 'z': 3293, 'level': 1}))).to_be('castleUpstairs')
    test("King Lathas's floor is not mistaken for the mainland", _fn5)

    def _fn6():
        expect(in_pigeon_zone(Record({'x': 2564, 'z': 3303, 'level': 0}))).to_be(True)
        expect(in_pigeon_zone(Record({'x': 2558, 'z': 3303, 'level': 0}))).to_be(False)
        expect(in_pigeon_zone(Record({'x': 2564, 'z': 3308, 'level': 0}))).to_be(False)
    test('the pigeon-release box is the one the cage script checks', _fn6)

    def _fn7():
        expect(in_guidor_quarter(QUARTER)).to_be(True)
        expect(in_guidor_quarter(Record({'x': 3285, 'z': 3381, 'level': 0}))).to_be(True)
        expect(in_guidor_quarter(Record({'x': 3212, 'z': 3428, 'level': 0}))).to_be(False)
    test("Guidor's quarter excludes Varrock proper, where the gate would take the vials", _fn7)


describe('biohazard areas', _fn2)


def _fn8():
    def _fn9():
        expect(decide(snapshot({'journal': 'complete'})).kind).to_be('done')
    test('a complete journal is done', _fn9)

    def _fn10():
        expect(decide(snapshot({'journal': 'unknown'})).kind).to_be('wait')
    test('an unloaded journal waits — it is not notStarted', _fn10)

    def _fn11():
        expect(decide(snapshot({'tile': None, 'stage': BIO_STAGE.STARTED})).kind).to_be('wait')
    test('an unknown tile waits rather than guessing an area', _fn11)

    def _fn12():
        expect(decide(snapshot({'stage': None})).kind).to_be('wait')
    test('an unreadable stage waits', _fn12)

    def _fn13():
        expect(decide(snapshot({'stage': BIO_STAGE.STARTED, 'bank_known': False})).kind).to_be('scan_bank')
    test('an unread bank is scanned before any stage decides', _fn13)

    def _fn14():
        expect(decide(snapshot({'stage': BIO_STAGE.STARTED, 'free_slots': 2})).kind).to_be('deposit')
    test('a nearly full pack banks spillover on the mainland', _fn14)

    def _fn15():
        step = decide(snapshot({
        'stage': BIO_STAGE.POISONED_STEW,
        'tile': HQ_TOP,
        'free_slots': 1,
        'inv_ids': carrying([BIO_ITEM.DOCTOR_GOWN, 1], [BIO_ITEM.MOURNER_KEY, 1]),
    }))
        expect(step.kind).not_.to_be('deposit')
    test('a full pack inside the headquarters does not try to bank there', _fn15)


describe('biohazard decide — terminal and guard cases', _fn8)


def _fn16():
    def _fn17():
        expect(name(decide(snapshot({'stage': BIO_STAGE.NOT_STARTED})))).to_be('ask Elena about her distillator')
    test('the quest starts with Elena', _fn17)

    def _fn18():
        expect(name(decide(snapshot({'stage': BIO_STAGE.STARTED})))).to_be('ask Jerico how to cross the wall')
    test('a started quest asks Jerico', _fn18)

    def _fn19():
        expect(name(decide(snapshot({'stage': BIO_STAGE.SPOKEN_JERICO, 'inv_ids': PROVISIONED})))).to_be("take bird feed from Jerico's cupboard")
    test('the seed comes before the birds', _fn19)

    def _fn20():
        step = decide(snapshot({
        'stage': BIO_STAGE.SPOKEN_JERICO,
        'inv_ids': PROVISIONED,
        'bank_ids': {_k: _v for _k, _v in list(PURSE.items()) + [[BIO_ITEM.BIRDFEED.id, 1]]},
    }))
        expect(step.kind).to_be('withdraw')
    test('banked bird feed is withdrawn, as the cupboard refuses a second bag', _fn20)

    def _fn21():
        step = decide(snapshot({
        'stage': BIO_STAGE.SPOKEN_JERICO,
        'inv_ids': {_k: _v for _k, _v in list(PROVISIONED.items()) + [[BIO_ITEM.BIRDFEED.id, 1]]},
    }))
        expect(name(step)).to_be("take a pigeon cage from behind Jerico's house")
    test('the birds are fetched before the tower is fed', _fn21)

    def _fn22():
        step = decide(snapshot({
        'stage': BIO_STAGE.SPOKEN_JERICO,
        'inv_ids': {_k: _v for _k, _v in list(PROVISIONED.items()) + [[BIO_ITEM.BIRDFEED.id, 1], [BIO_ITEM.PIGEONS.id, 1]]},
    }))
        expect(name(step)).to_be('throw the bird feed onto the watchtower')
    test('with seed and birds in the pack the tower gets fed', _fn22)

    def _fn23():
        step = decide(snapshot({'stage': BIO_STAGE.SPOKEN_JERICO, 'inv_ids': carrying([FOOD, 5])}))
        expect(step.kind).to_be('withdraw')
    test("the priest suit's coins come out beside the Ardougne booth, not beside Thessalia", _fn23)

    def _fn24():
        step = decide(snapshot({'stage': BIO_STAGE.USED_BIRDFEED, 'inv_ids': carrying([BIO_ITEM.PIGEONS, 1])}))
        expect(name(step)).to_be('open the pigeon cage by the wall')
    test('a fed tower releases the pigeons', _fn24)

    def _fn25():
        expect(name(decide(snapshot({'stage': BIO_STAGE.USED_BIRDFEED})))).to_be("take a pigeon cage from behind Jerico's house")
    test('a lost cage is re-fetched rather than opened', _fn25)

    def _fn26():
        bank = {_k: _v for _k, _v in list(PURSE.items()) + [[FOOD.id, 20]]}
        expect(decide(snapshot({'stage': BIO_STAGE.SPOKEN_JERICO, 'bank_ids': bank})).kind).to_be('withdraw')
    test('the meal comes out at Jerico, nine tiles from the booth, not at the wall', _fn26)

    def _fn27():
        step = decide(snapshot({'stage': BIO_STAGE.SPOKEN_JERICO, 'bank_ids': {}}))
        expect(name(step)).to_be("take bird feed from Jerico's cupboard")
    test('an empty larder and an empty purse never block the distraction leg', _fn27)

    def _fn28():
        expect(name(decide(snapshot({'stage': BIO_STAGE.RELEASED_PIGEONS})))).to_be("cross the wall on Omart's rope ladder")
    test('released pigeons go straight to the ladder', _fn28)


describe('biohazard decide — the wall crossing', _fn16)


def _fn29():
    def _fn30():
        expect(name(decide(snapshot({'stage': BIO_STAGE.CLIMBED_LADDER, 'tile': WEST})))).to_be('take the rotten apples in West Ardougne')
    test('the apples come before the cauldron', _fn30)

    def _fn31():
        step = decide(snapshot({'stage': BIO_STAGE.CLIMBED_LADDER, 'tile': WEST, 'inv_ids': carrying([BIO_ITEM.ROTTEN_APPLES, 1])}))
        expect(name(step)).to_be("poison the mourners' stew")
    test('holding the apples, the stew is poisoned', _fn31)

    def _fn32():
        expect(name(decide(snapshot({'stage': BIO_STAGE.CLIMBED_LADDER})))).to_be("cross the wall on Omart's rope ladder")
    test('a poisoned stew on the mainland crosses back west first', _fn32)

    def _fn33():
        expect(name(decide(snapshot({'stage': BIO_STAGE.POISONED_STEW, 'tile': WEST})))).to_be("search the nurse's cupboard for a doctors' gown")
    test('the gown comes from the nurse when nobody owns one', _fn33)

    def _fn34():
        step = decide(snapshot({
        'stage': BIO_STAGE.POISONED_STEW,
        'bank_ids': {_k: _v for _k, _v in list(PURSE.items()) + [[BIO_ITEM.DOCTOR_GOWN.id, 1]]},
    }))
        expect(step.kind).to_be('withdraw')
    test('a banked gown is withdrawn, as the cupboard checks the bank too', _fn34)

    def _fn35():
        step = decide(snapshot({'stage': BIO_STAGE.POISONED_STEW, 'tile': WEST, 'worn_ids': set([BIO_ITEM.DOCTOR_GOWN.id])}))
        expect(name(step)).to_be('take the key off the sick mourner')
    test('a worn gown counts as owned and the key leg starts', _fn35)

    def _fn36():
        step = decide(snapshot({
        'stage': BIO_STAGE.POISONED_STEW,
        'tile': HQ_TOP,
        'worn_ids': set([BIO_ITEM.DOCTOR_GOWN.id]),
        'inv_ids': carrying([BIO_ITEM.MOURNER_KEY, 1]),
    }))
        expect(name(step)).to_be("search the crate for Elena's distillator")
    test('with the key in hand the crate is searched', _fn36)

    def _fn37():
        step = decide(snapshot({'stage': BIO_STAGE.FOUND_DISTILLATOR, 'tile': HQ_TOP, 'inv_ids': carrying([BIO_ITEM.DISTILLATOR, 1])}))
        expect(name(step)).to_be('leave for the East Ardougne side')
    test('the distillator goes back to Elena over the wall', _fn37)

    def _fn38():
        step = decide(snapshot({'stage': BIO_STAGE.FOUND_DISTILLATOR, 'inv_ids': carrying([BIO_ITEM.DISTILLATOR, 1]), 'free_slots': 4}))
        expect(step.kind).to_be('deposit')
    test("Elena's four-item hand-back gets the slots it needs first", _fn38)

    def _fn39():
        step = decide(snapshot({'stage': BIO_STAGE.FOUND_DISTILLATOR, 'inv_ids': carrying([BIO_ITEM.DISTILLATOR, 1])}))
        expect(name(step)).to_be('hand Elena her distillator')
    test('with room in the pack the distillator is handed over', _fn39)

    def _fn40():
        expect(name(decide(snapshot({'stage': BIO_STAGE.FOUND_DISTILLATOR, 'tile': HQ})))).to_be("search the crate for Elena's distillator")
    test('a lost distillator is looked for in the crate again', _fn40)


describe('biohazard decide — West Ardougne', _fn29)


def _fn41():
    def held_kit(extra=None):
        kit = {}
        for id, qty in KIT.items():
            kit[id] = qty
        for id, qty in (extra or {}).items():
            kit[id] = qty if qty is not None else 0
        return kit

    def _fn43():
        step = decide(snapshot({
        'stage': BIO_STAGE.GIVEN_DISTILLATOR,
        'inv_ids': {_k: _v for _k, _v in list(ALL_VIALS.items()) + [[BIO_ITEM.PLAGUE_SAMPLE.id, 1]]},
    }))
        expect(name(step)).to_be('ask the chemist for touch paper')
    test('the chemist is asked for touch paper once Elena has handed the vials over', _fn43)

    def _fn44():
        expect(name(decide(snapshot({'stage': BIO_STAGE.GIVEN_DISTILLATOR})))).to_be('ask Elena to replace the sample she gave me')
    test('a sample nobody has is asked back from Elena rather than walked to Rimmington', _fn44)

    def _fn45():
        step = decide(snapshot({
        'stage': BIO_STAGE.SPOKEN_CHEMIST,
        'inv_ids': carrying([BIO_ITEM.PLAGUE_SAMPLE, 1], [BIO_ITEM.TOUCH_PAPER, 1]),
        'bank_ids': {_k: _v for _k, _v in list(PURSE.items()) + [[BIO_ITEM.ETHENEA.id, 1]]},
    }))
        expect(step.kind).to_be('withdraw')
    test('a banked vial is withdrawn before Elena is asked for another', _fn45)

    def _fn46():
        step = decide(snapshot({'stage': BIO_STAGE.SPOKEN_CHEMIST, 'tile': RIMMINGTON, 'inv_ids': held_kit()}))
        expect(name(step)).to_be('give the errand boys their vials')
    test('vials in the pack outside the quarter go to the errand boys', _fn46)

    def _fn47():
        step = decide(snapshot({
        'stage': BIO_STAGE.SPOKEN_CHEMIST,
        'tile': RIMMINGTON,
        'inv_ids': carrying([BIO_ITEM.PLAGUE_SAMPLE, 1], [BIO_ITEM.TOUCH_PAPER, 1]),
    }))
        expect(step.kind).to_be('withdraw')
    test('an empty purse is filled before the walk to Thessalia', _fn47)

    def _fn48():
        step = decide(snapshot({
        'stage': BIO_STAGE.SPOKEN_CHEMIST,
        'tile': RIMMINGTON,
        'inv_ids': carrying([BIO_ITEM.PLAGUE_SAMPLE, 1], [BIO_ITEM.TOUCH_PAPER, 1], [BIO_ITEM.COINS, 5000]),
    }))
        expect(name(step)).to_be('buy a priest gown from Thessalia')
    test('with the vials away and coins in hand the priest suit is bought before the gate', _fn48)

    def _fn49():
        step = decide(snapshot({
        'stage': BIO_STAGE.SPOKEN_CHEMIST,
        'tile': RIMMINGTON,
        'inv_ids': carrying([BIO_ITEM.PLAGUE_SAMPLE, 1], [BIO_ITEM.TOUCH_PAPER, 1], [BIO_ITEM.PRIEST_GOWN, 1], [BIO_ITEM.PRIEST_ROBE, 1]),
    }))
        expect(name(step)).to_be("walk through the gate to Varrock's east quarter")
    test('a robed bot with no vials crosses into the quarter', _fn49)

    def _fn50():
        step = decide(snapshot({
        'stage': BIO_STAGE.SPOKEN_CHEMIST,
        'tile': QUARTER,
        'inv_ids': carrying([BIO_ITEM.PLAGUE_SAMPLE, 1], [BIO_ITEM.TOUCH_PAPER, 1], [BIO_ITEM.PRIEST_GOWN, 1], [BIO_ITEM.PRIEST_ROBE, 1]),
    }))
        expect(name(step)).to_be('collect the vials at the Dancing Donkey')
    test('inside the quarter the vials are collected from the inn', _fn50)

    def _fn51():
        step = decide(snapshot({
        'stage': BIO_STAGE.SPOKEN_CHEMIST,
        'tile': QUARTER,
        'no_progress': 3,
        'inv_ids': carrying([BIO_ITEM.PLAGUE_SAMPLE, 1], [BIO_ITEM.TOUCH_PAPER, 1], [BIO_ITEM.PRIEST_GOWN, 1], [BIO_ITEM.PRIEST_ROBE, 1]),
    }))
        expect(name(step)).to_be('ask Elena to replace the vials the errand boys ruined')
    test('boys who keep coming back empty send the bot to Elena for replacements', _fn51)

    def _fn52():
        step = decide(snapshot({'stage': BIO_STAGE.SPOKEN_CHEMIST, 'tile': QUARTER, 'inv_ids': held_kit()}))
        expect(name(step)).to_be('take the kit to Guidor')
    test('the kit in the quarter goes to Guidor', _fn52)

    def _fn53():
        step = decide(snapshot({
        'stage': BIO_STAGE.SPOKEN_CHEMIST,
        'tile': QUARTER,
        'inv_ids': carrying([BIO_ITEM.PLAGUE_SAMPLE, 1], [BIO_ITEM.TOUCH_PAPER, 1]),
        'bank_ids': {_k: _v for _k, _v in list(PURSE.items()) + [[BIO_ITEM.ETHENEA.id, 1]]},
    }))
        expect(step.kind).not_.to_be('withdraw')
        expect(name(step)).to_be('collect the vials at the Dancing Donkey')
    test('a banked vial is never withdrawn inside the quarter — the gate would take it back', _fn53)

    def _fn54():
        step = decide(snapshot({
        'stage': BIO_STAGE.POISONED_STEW,
        'tile': Record({'x': 2551, 'z': 3321, 'level': 0}),
        'bank_known': False,
    }))
        expect(name(step)).to_be('leave for the East Ardougne side')
    test('a bank leg decided inside the sealed headquarters leaves first', _fn54)

    def _fn55():
        step = decide(snapshot({
        'stage': BIO_STAGE.SPOKEN_CHEMIST,
        'tile': QUARTER,
        'inv_ids': {_k: _v for _k, _v in list(ALL_VIALS.items()) + [[BIO_ITEM.PLAGUE_SAMPLE.id, 1]]},
    }))
        expect(name(step)).to_be('ask the chemist for touch paper')
    test('lost touch paper is asked for again before anything else', _fn55)


describe('biohazard decide — the smuggle to Varrock', _fn41)


def _fn56():
    def _fn57():
        expect(name(decide(snapshot({'stage': BIO_STAGE.FOUND_SECRET})))).to_be('tell Elena what Guidor found')
    test("Guidor's findings are reported to Elena", _fn57)

    def _fn58():
        expect(name(decide(snapshot({'stage': BIO_STAGE.REPORTED_ELENA})))).to_be('confront King Lathas about the plague')
    test('a reported hoax is taken to King Lathas', _fn58)

    def _fn59():
        expect(name(decide(snapshot({'stage': BIO_STAGE.FOUND_SECRET, 'tile': Record({'x': 2578, 'z': 3293, 'level': 1})})))).to_be('leave for the East Ardougne side')
    test('a stage past the ladder reached from the castle floor walks out first', _fn59)


describe('biohazard decide — the ending', _fn56)


def _fn60():
    def _fn61():
        expect(biohazard.record.id).to_be('biohazard')
        expect(biohazard.record.requirements.quests).to_contain('elena')
    test('the record is the Biohazard row and requires Plague City', _fn61)

    def _fn62():
        expect(biohazard.owns_inventory).to_be(True)
        expect(biohazard.bank).to_be('nearest')
    test('the module owns its inventory, as three towns supply it', _fn62)


describe('biohazard module wiring', _fn60)
