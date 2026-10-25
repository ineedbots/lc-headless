"""rs2b0t's test/api/ai/quests/strike.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot
from rs2004.quests.strike import prepare_strikes, strike_spell


def snapshot(extra=None):
    base = QuestSnapshot(journal='in_progress', inv={}, worn=set(), no_progress=0, bank_coins=10000, magic=1, bank_known=True, bank={},
                         free_slots=20)
    return base.with_fields(extra or {})


def spell_at(magic, spell):
    def body():
        expect(strike_spell(magic)).to_be(spell)
    return body


def _fn2():
    for _magic, _spell in [[1, 'Wind Strike'], [5, 'Water Strike'], [9, 'Earth Strike'], [13, 'Fire Strike']]:
        test(f'Magic {_magic} selects {_spell}', spell_at(_magic, _spell))

    def _fn4():
        expect(prepare_strikes(snapshot({'bank_known': False}))).to_equal(Record({'kind': 'scan_bank'}))
    test('reads an unknown bank before buying runes', _fn4)

    def _fn5():
        step = prepare_strikes(snapshot({
            'magic': 13,
            'inv': {'mind rune': 20, 'air rune': 100},
            'bank': {'mind rune': 200, 'air rune': 500, 'fire rune': 1000},
        }))
        expect(step).to_match_object(Record({
            'kind': 'withdraw',
            'items': [{'name': 'Mind rune', 'qty': 130}, {'name': 'Fire rune', 'qty': 450}, {'name': 'Air rune', 'qty': 200}],
        }))
    test('withdraws only missing runes for 150 casts', _fn5)

    def _fn6():
        step = prepare_strikes(snapshot({'inv': {'mind rune': 150, 'air rune': 40}}))
        expect(step).to_match_object(Record({'kind': 'buy', 'item': 'Air rune', 'qty': 110, 'shop': Record({'npc': 'Betty'})}))
    test('buys the shortfall after draining available bank stacks', _fn6)

    def _fn7():
        expect(prepare_strikes(snapshot({'bank_known': False, 'inv': {'mind rune': 150, 'air rune': 150}}))).to_be_null()
    test('a full budget proceeds without a bank trip', _fn7)

    def _fn8():
        held = {'mind rune': 5, 'air rune': 5}
        expect(strike_spell(13, lambda name: held.get(name.lower(), 0))).to_be('Wind Strike')
    test('does not switch to an unsupplied spell after gaining a level', _fn8)

    def _fn9():
        expect(strike_spell(13, lambda name: 0)).to_be_null()
    test('no runes means no castable spell', _fn9)


describe('quest Strike supplies', _fn2)
