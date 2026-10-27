"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/vampireslayer.test.ts (MIT, see thirdparty/rs2b0t)."""
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot

def _each_run(fn, row):
    def run():
        return fn(*row) if isinstance(row, list) else fn(row)
    return run

def _each(rows, label, fn):
    for row in rows:
        test(label + ' ' + str(row), _each_run(fn, row))


def _snapshot(**fields):
    for name in ['inv', 'inv_ids', 'bank', 'bank_ids']:
        if isinstance(fields.get(name), (Record, Fake)):
            fields[name] = fields[name]._fields
    return QuestSnapshot(**fields)
from rs2004.quests.defs.vampireslayer import decide, parse_vampire_slayer_journal, vampire_slayer_area, VAMPIRE_SLAYER_STAGE
MAINLAND = Fake(**{'x': 3093, 'z': 3243, 'level': 0})
MORGAN_UPPER = Fake(**{'x': 3096, 'z': 3268, 'level': 1})
CRYPT = Fake(**{'x': 3077, 'z': 9775, 'level': 0})
FOOD = ['Trout'] * 20

def counts(names):
    out = {}
    for name in names:
        key = name.lower()
        _v1 = out.get(key)
        out[key] = (_v1 if _v1 is not None else 0) + 1
    return out

def snap(options=None):
    if options is None:
        options = Fake(**{})
    bank = counts(options.bank if options.bank is not None else [])
    _v2 = bank.get('coins')
    return _snapshot(**{'journal': options.journal if options.journal is not None else 'in_progress', 'inv': counts(options.inv if options.inv is not None else []), 'worn': set([name.lower() for name in (options.worn if options.worn is not None else [])]), 'no_progress': 0, 'bank_coins': _v2 if _v2 is not None else 0, 'stage': options.stage if 'stage' in options._fields else VAMPIRE_SLAYER_STAGE.NOT_STARTED, 'bank': bank, 'bank_known': options.bank_known if options.bank_known is not None else True, 'tile': MAINLAND if options.tile is None else options.tile, 'free_slots': options.free_slots if options.free_slots is not None else 28})

def custom_name(step):
    return step.name if step.kind == 'custom' else None

def _fn3():

    def _fn4(text, phase):
        expect(parse_vampire_slayer_journal(text)).to_be(phase)
    _each([['@dbl@I can start this quest by speaking to @dre@Morgan@dbl@ who is in @dre@Draynor Village.', 0], ['@str@I spoke to Morgan in Draynor Village.||@dbl@I need to speak to @dre@Dr Harlow@dbl@ who can normally be found in the Jolly Boar Inn.', 1], ['@str@I have spoken to Dr Harlow. He seemed terribly drunk, and|@str@he kept asking me to buy him drinks.', 2], ["@str@Dr Harlow gave me a stake to finish off the Vampire when|I'm fighting it.", 2], ['@str@I have killed the Vampire, Count Draynor.||@red@QUEST COMPLETE!', 3]], 'maps source-authored journal text to phase %i', _fn4)

    def _fn5():
        expect(parse_vampire_slayer_journal(['Vampire Slayer', 'Loading…'])).to_be_undefined()
    test('fails closed on an incomplete or unrelated journal', _fn5)
describe('Vampire Slayer journal phase parsing', _fn3)

def _fn6():

    def _fn7():
        expect(vampire_slayer_area(MAINLAND)).to_be('mainland')
        expect(vampire_slayer_area(MORGAN_UPPER)).to_be('morganUpper')
        expect(vampire_slayer_area(CRYPT)).to_be('crypt')
        expect(vampire_slayer_area(Fake(**{'x': 3200, 'z': 3200, 'level': 2}))).to_be('unknown')
        expect(vampire_slayer_area(None)).to_be('unknown')
    test('recognizes every quest-specific area', _fn7)
describe('Vampire Slayer area classification', _fn6)

def _fn8():

    def _fn9():
        expect(decide(snap(Fake(**{'stage': 0, 'bank_known': False}))).kind).to_be('scan_bank')
    test('scans an unknown bank before starting from an empty pack', _fn9)

    def _fn10():
        step = decide(snap(Fake(**{'stage': 0, 'inv': ['Bones']})))
        expect(step.kind).to_be('deposit')
        expect(step.kind == 'deposit' and step.exact_keep).to_be(True)
    test('banks unrelated spillover before speaking to Morgan', _fn10)

    def _fn11():
        step = decide(snap(Fake(**{'stage': 0})))
        expect(step.kind == 'talk' and step.stop.npc).to_be('Morgan')
    test('starts with Morgan once the bank and pack are known', _fn11)

    def _fn12():
        step = decide(snap(Fake(**{'stage': 1, 'bank': ['Garlic']})))
        expect(step.kind == 'withdraw' and step.items).to_equal([Fake(**{'name': 'Garlic', 'qty': 1})])
    test('stage 1 recovers banked garlic before visiting Harlow', _fn12)

    def _fn13():
        expect(custom_name(decide(snap(Fake(**{'stage': 1}))))).to_be("take garlic from Morgan's cupboard")
        ready = decide(snap(Fake(**{'stage': 1, 'inv': ['Garlic']})))
        expect(ready.kind == 'talk' and ready.stop.npc).to_be('Dr Harlow')
    test('stage 1 sources missing garlic and then visits Harlow', _fn13)

    def _fn14():
        expect(custom_name(decide(snap(Fake(**{'stage': 1, 'tile': MORGAN_UPPER}))))).to_be("take garlic from Morgan's cupboard")
        expect(custom_name(decide(snap(Fake(**{'stage': 1, 'tile': MORGAN_UPPER, 'inv': ['Garlic']}))))).to_be("leave Morgan's upper floor")
    test('an upstairs restart searches or leaves according to held garlic', _fn14)
describe('Vampire Slayer start and Harlow phases', _fn8)

def _fn15():

    def _fn16():
        step = decide(snap(Fake(**{'stage': 2, 'bank': ['Stake']})))
        expect(step.kind == 'withdraw' and step.items).to_equal([Fake(**{'name': 'Stake', 'qty': 1})])
    test('recovers a banked stake without buying another beer', _fn16)

    def _fn17():
        step = decide(snap(Fake(**{'stage': 2, 'inv': ['Trout'] * 28, 'bank': ['Stake'], 'free_slots': 0})))
        expect(step.kind).to_be('deposit')
        expect(step.kind == 'deposit' and step.keep).to_equal(['coins'])
    test('banks an oversized valid loadout and rebuilds instead of parking', _fn17)

    def _fn18():
        coins = decide(snap(Fake(**{'stage': 2, 'bank': ['Coins'] * 5000})))
        expect(coins.kind == 'withdraw' and coins.items).to_equal([Fake(**{'name': 'Coins', 'qty': 5000})])
        expect(custom_name(decide(snap(Fake(**{'stage': 2, 'inv': ['Coins'] * 5000}))))).to_be('buy Dr Harlow a Beer')
        beer = decide(snap(Fake(**{'stage': 2, 'inv': ['Beer']})))
        expect(beer.kind == 'talk' and beer.stop.npc).to_be('Dr Harlow')
    test('withdraws coins, buys a beer, then returns it to Harlow', _fn18)

    def _fn19():
        step = decide(snap(Fake(**{'stage': 2, 'inv': ['Stake', 'Garlic'] + list(['Coins'] * 4998)})))
        expect(step.kind == 'buy' and step.item).to_be('Hammer')
    test('does not cross the map to top up a still-safe coin reserve', _fn19)

    def _fn20():
        step = decide(snap(Fake(**{'stage': 2, 'bank': ['Beer']})))
        expect(step.kind == 'withdraw' and step.items).to_equal([Fake(**{'name': 'Beer', 'qty': 1})])
    test('recovers banked beer before buying a replacement', _fn20)

    def _fn21():
        garlic = decide(snap(Fake(**{'stage': 2, 'inv': ['Stake'], 'bank': ['Garlic']})))
        expect(garlic.kind == 'withdraw' and garlic.items).to_equal([Fake(**{'name': 'Garlic', 'qty': 1})])
        hammer = decide(snap(Fake(**{'stage': 2, 'inv': ['Stake', 'Garlic'], 'bank': ['Hammer']})))
        expect(hammer.kind == 'withdraw' and hammer.items).to_equal([Fake(**{'name': 'Hammer', 'qty': 1})])
        buy_hammer = decide(snap(Fake(**{'stage': 2, 'inv': ['Stake', 'Garlic'] + list(['Coins'] * 5000)})))
        expect(buy_hammer.kind == 'buy' and buy_hammer.item).to_be('Hammer')
    test('recovers or sources each post-Harlow quest item in order', _fn21)

    def _fn22():
        base = ['Stake', 'Garlic', 'Hammer']
        banked = decide(snap(Fake(**{'stage': 2, 'inv': base, 'bank': ['Steel sword']})))
        expect(banked.kind == 'withdraw' and banked.items).to_equal([Fake(**{'name': 'Steel sword', 'qty': 1})])
        equip = decide(snap(Fake(**{'stage': 2, 'inv': list(base) + ['Steel sword']})))
        expect(equip.kind == 'equip' and equip.item).to_be('Steel sword')
        buy = decide(snap(Fake(**{'stage': 2, 'inv': list(base) + list(['Coins'] * 5000)})))
        expect(buy.kind == 'buy' and buy.item).to_be('Black sword')
    test('uses a banked safe weapon, equips it, and buys one only as fallback', _fn22)

    def _fn23():
        base = ['Stake', 'Garlic', 'Hammer']
        banked = decide(snap(Fake(**{'stage': 2, 'inv': base, 'worn': ['Black sword'], 'bank': ['Trout'] * 20})))
        expect(custom_name(banked)).to_be('enter the crypt and defeat Count Draynor')
        rich = decide(snap(Fake(**{'stage': 2, 'inv': list(base) + list(['Coins'] * 5000), 'worn': ['Black sword']})))
        expect(custom_name(rich)).to_be('enter the crypt and defeat Count Draynor')
    test('never withdraws or buys food, whatever the bank or the purse holds', _fn23)

    def _fn24():
        step = decide(snap(Fake(**{'stage': 2, 'inv': ['Stake', 'Garlic', 'Hammer'], 'worn': ['Black sword']})))
        expect(custom_name(step)).to_be('enter the crypt and defeat Count Draynor')
    test('enters the crypt on stake, garlic, hammer and a weapon, with no food among them', _fn24)

    def _fn25():
        expect(custom_name(decide(snap(Fake(**{'stage': 2, 'tile': CRYPT, 'inv': ['Stake']}))))).to_be('leave the crypt to recover supplies')
        ready = decide(snap(Fake(**{'stage': 2, 'tile': CRYPT, 'inv': ['Stake', 'Garlic', 'Hammer'] + list(FOOD), 'worn': ['Black sword']})))
        expect(custom_name(ready)).to_be('enter the crypt and defeat Count Draynor')
    test('a crypt restart leaves when incomplete and resumes combat when complete', _fn25)
describe('Vampire Slayer stake and supply recovery', _fn15)

def _fn26():

    def _fn27():
        expect(decide(snap(Fake(**{'stage': 3}))).kind).to_be('done')
        expect(decide(snap(Fake(**{'stage': 0, 'journal': 'complete'}))).kind).to_be('done')
    test('completion is terminal even before the journal colour catches up', _fn27)

    def _fn28():
        expect(decide(snap(Fake(**{'journal': 'unknown'}))).kind).to_be('wait')
        expect(decide(snap(Fake(**{'stage': None}))).kind).to_be('wait')
        expect(decide(snap(Fake(**{'stage': 2, 'tile': Fake(**{'x': 3200, 'z': 3200, 'level': 2})}))).kind).to_be('wait')
    test('unknown journal, stage, and area all fail closed', _fn28)
describe('Vampire Slayer terminal and defensive states', _fn26)

