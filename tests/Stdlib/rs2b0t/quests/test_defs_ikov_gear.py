"""Ported from rs2b0t's test/api/ai/quests/defs/ikov-gear.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestProgress, QuestSnapshot
from rs2004.quests.defs.ikov.gear import melee_weapon_step, ranged_armour_step

def snap(where=None):
    if where is None:
        where = Record({})
    return QuestSnapshot(**{
        'journal': 'in_progress',
        'inv': {_k: _v for _k, _v in (where.inv if where.inv is not None else [])},
        'inv_ids': {},
        'worn': set((where.worn if where.worn is not None else [])),
        'worn_ids': set(),
        'no_progress': 0,
        'bank_coins': 0,
        'stage': 10,
        'bank': {_k: _v for _k, _v in (where.bank if where.bank is not None else [])},
        'bank_ids': {},
        'bank_known': (where.bank_known if where.bank_known is not None else True),
        'tile': Record({'x': 2677, 'z': 3406, 'level': 0}),
        'free_slots': 20,
    })


def names(step):
    return ([i['name'] for i in step.items] if (step.kind if step is not None else None) == 'withdraw' else [])


def _fn1():
    def _fn2():
        expect(ranged_armour_step(snap(Record({'bank_known': False, 'bank': [['studded body', 1]]})))).to_be_null()
    test('an unread bank dresses nothing rather than guessing at what is in it', _fn2)

    def _fn3():
        expect(ranged_armour_step(snap())).to_be_null()
    test('an empty bank is not a step', _fn3)

    def _fn4():
        step = ranged_armour_step(snap(Record({'bank': [['coif', 1], ['studded body', 1], ['studded chaps', 1], ['leather gloves', 1]]})))
        expect(sorted(names(step))).to_equal(['Coif', 'Leather gloves', 'Studded body', 'Studded chaps'])
    test('what the bank holds is withdrawn, one piece a slot', _fn4)

    # Why: the ladder is what makes this "the best it has" rather than "the first it finds".
    def _fn5():
        step = ranged_armour_step(snap(Record({'bank': [['leather body', 1], ['studded body', 1], ['hardleather body', 1], ['dragonhide body', 1]]})))
        expect(names(step)).to_equal(['Dragonhide body'])
    test('a slot takes its best entry and leaves the rest', _fn5)

    def _fn6():
        step = ranged_armour_step(snap(Record({'bank': [['leather body', 1], ['leather chaps', 1]]})))
        expect(names(step)).to_equal(['Leather body', 'Leather chaps'])
    test('leather stands in when nothing better is banked', _fn6)

    # Why: a mid-run swap costs a bank trip to gain a point of defence, so a dressed slot is left alone.
    def _fn7():
        step = ranged_armour_step(snap(Record({'worn': ['leather body'], 'bank': [['studded body', 1]]})))
        expect(step).to_be_null()
    test('a slot already worn is not upgraded', _fn7)

    def _fn8():
        step = ranged_armour_step(snap(Record({'inv': [['studded body', 1]], 'bank': [['studded body', 1]]})))
        expect((step.kind if step is not None else None)).to_be('custom')
        expect((step.kind if step is not None else None) == 'custom' and step.name).to_be('wear Studded body')
    test('pieces already in the pack are worn rather than withdrawn again', _fn8)

    # Why: the boots of lightness are what the lava bridge is crossed in and the bow is what the Fire Warrior demands, so neither slot is the armour's to fill.
    def _fn9():
        step = ranged_armour_step(snap(Record({'bank': [['leather boots', 1], ['shortbow', 1], ['studded body', 1]]})))
        expect(names(step)).to_equal(['Studded body'])
    test('the feet and the weapon are left to the quest', _fn9)


describe('Temple of Ikov ranged armour', _fn1)


def _fn10():
    def _fn11():
        expect(melee_weapon_step(snap())).to_be_null()
    test('an empty bank arms nothing, and the axe fallback stands', _fn11)

    def _fn12():
        step = melee_weapon_step(snap(Record({'bank': [['bronze sword', 1], ['rune scimitar', 1], ['steel longsword', 1], ['mithril scimitar', 1]]})))
        expect(names(step)).to_equal(['Rune scimitar'])
    test('the best tier in the bank is the one withdrawn', _fn12)

    # Why: a hobgoblin has 1 stab and 1 slash defence, so the faster weapon of a tier wins rather than the heavier one.
    def _fn13():
        step = melee_weapon_step(snap(Record({'bank': [['adamant longsword', 1], ['adamant scimitar', 1]]})))
        expect(names(step)).to_equal(['Adamant scimitar'])
    test('within a tier the scimitar beats the longsword', _fn13)

    def _fn14():
        step = melee_weapon_step(snap(Record({'inv': [['rune scimitar', 1]], 'bank': [['rune scimitar', 1]]})))
        expect((step.kind if step is not None else None) == 'custom' and step.name).to_be('wield Rune scimitar')
    test('a weapon already in the pack is wielded rather than withdrawn again', _fn14)

    def _fn15():
        expect(melee_weapon_step(snap(Record({'worn': ['rune scimitar'], 'bank': [['rune scimitar', 1]]})))).to_be_null()
    test('the weapon already worn is left alone', _fn15)

    def _fn16():
        expect(melee_weapon_step(snap(Record({'bank_known': False, 'bank': [['rune scimitar', 1]]})))).to_be_null()
    test('an unread bank arms nothing rather than guessing', _fn16)

    def worn_beats_a_spare():
        expect(melee_weapon_step(snap(Record({'worn': ['rune scimitar'], 'inv': [['bronze sword', 1]]})))).to_be_null()
    test('a worn weapon is not swapped for a worse spare, which would trade them forever', worn_beats_a_spare)

    def better_replaces_worn():
        step = melee_weapon_step(snap(Record({'worn': ['bronze sword'], 'bank': [['rune scimitar', 1]]})))
        expect(names(step)).to_equal(['Rune scimitar'])
    test('a better weapon in the bank still replaces the one worn', better_replaces_worn)


describe('Temple of Ikov melee weapon', _fn10)
