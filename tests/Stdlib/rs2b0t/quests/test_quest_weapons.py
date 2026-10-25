"""rs2b0t's test/api/ai/quests/questWeapons.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs.record import Record
from rs2004.quests.weapons import MELEE_WEAPONS, banked_weapon, held_weapon, wieldable, PICKAXES, banked_pickaxe

def done(quest=None):
    return True


def none(quest=None):
    return False


def name_of(w):
    return ((w.name if w is not None else None) if (w.name if w is not None else None) is not None else None)


def _fn1():
    def _fn2():
        expect((wieldable(60, done) or [None])[0].tier).to_be('Dragon')
    test('60 attack reaches dragon', _fn2)

    def _fn3():
        for level in [40, 59]:
            expect((wieldable(level, done) or [None])[0].tier).to_be('Rune')
    test('40 to 59 stops at rune', _fn3)

    def _fn4():
        expect((wieldable(39, done) or [None])[0].tier).to_be('Adamant')
        expect((wieldable(30, done) or [None])[0].tier).to_be('Adamant')
        expect((wieldable(29, done) or [None])[0].tier).to_be('Mithril')
        expect((wieldable(19, done) or [None])[0].tier).to_be('Black')
        expect((wieldable(9, done) or [None])[0].tier).to_be('Steel')
        expect((wieldable(4, done) or [None])[0].tier).to_be('Iron')
        expect((wieldable(1, done) or [None])[0].tier).to_be('Iron')
    test('each band stops at its own tier', _fn4)

    def _fn5():
        rune = [w.name for w in [w for w in MELEE_WEAPONS if w.tier == 'Rune']]
        expect(rune).to_contain('Rune scimitar')
        expect(rune).to_contain('Rune longsword')
        expect(rune).to_contain('Rune battleaxe')
        expect(len(rune)).to_be_greater_than(3)
    test('a tier offers every weapon type the item db knows, not one hard-coded pick', _fn5)


describe('the tier a level buys', _fn1)


def _fn6():
    def _fn7():
        expect((wieldable(60, none) or [None])[0].tier).to_be('Rune')
    test('60 attack without the quests falls back to rune', _fn7)

    def _fn8():
        lost_city = [w.name for w in [w for w in wieldable(60, lambda q: q == 'Lost City') if w.tier == 'Dragon']]
        expect(lost_city).to_equal(['Dragon longsword', 'Dragon dagger'])
        heroes = [w.name for w in [w for w in wieldable(60, lambda q: q == "Hero's Quest") if w.tier == 'Dragon']]
        expect(heroes).to_equal(['Dragon battleaxe', 'Dragon mace'])
    test("Lost City unlocks the longsword and dagger, Hero's Quest the mace and battleaxe", _fn8)


describe('dragon melee is gated on a quest as well as the level', _fn6)


def _fn9():
    def weapon_id(name):
        return ([w for w in MELEE_WEAPONS if w.name == name] or [None])[0].id

    def _fn10():
        bank = {_k: _v for _k, _v in [[weapon_id('Bronze scimitar'), 1], [weapon_id('Rune scimitar'), 1], [weapon_id('Dragon longsword'), 1]]}
        expect(name_of(banked_weapon(bank, 60, done))).to_be('Dragon longsword')
        expect(name_of(banked_weapon(bank, 40, done))).to_be('Rune scimitar')
        expect(name_of(banked_weapon(bank, 1, done))).to_be('Bronze scimitar')
    test('the bank gives up its best wieldable weapon', _fn10)

    def _fn11():
        bank = {_k: _v for _k, _v in [[weapon_id('Dragon longsword'), 1], [weapon_id('Mithril scimitar'), 1]]}
        expect(name_of(banked_weapon(bank, 59, done))).to_be('Mithril scimitar')
    test('a banked weapon the level cannot reach is skipped, not withdrawn', _fn11)

    def _fn12():
        bank = {_k: _v for _k, _v in [[weapon_id('Dragon longsword'), 1], [weapon_id('Rune scimitar'), 1]]}
        expect(name_of(banked_weapon(bank, 60, none))).to_be('Rune scimitar')
    test('a dragon weapon without its quest is skipped even at 60', _fn12)

    def _fn13():
        expect(banked_weapon({}, 60, done)).to_be_null()
        expect(banked_weapon(None, 60, done)).to_be_null()
    test('an empty bank yields nothing rather than a default', _fn13)

    def _fn14():
        expect(name_of(held_weapon(None, set([weapon_id('Rune scimitar')]), 60, done))).to_be('Rune scimitar')
        expect(name_of(held_weapon({_k: _v for _k, _v in [[weapon_id('Rune scimitar'), 1]]}, None, 60, done))).to_be('Rune scimitar')
    test('a worn weapon counts as held', _fn14)


describe('picking from what the account actually has', _fn9)


def _fn15():
    def pickaxe_id(name):
        return ([p for p in PICKAXES if p.name == name] or [None])[0].id

    def _fn16():
        expect(banked_pickaxe({_k: _v for _k, _v in [[pickaxe_id('Rune pickaxe'), 1]]}, 40)).to_match_object(Record({'name': 'Rune pickaxe'}))
        expect(banked_pickaxe({_k: _v for _k, _v in [[pickaxe_id('Rune pickaxe'), 1]]}, 39)).to_be_null()
    test('the attack level buys the pickaxe tier, the way it buys a scimitar', _fn16)

    def _fn17():
        bank = {_k: _v for _k, _v in [[pickaxe_id('Bronze pickaxe'), 1], [pickaxe_id('Rune pickaxe'), 1], [pickaxe_id('Steel pickaxe'), 1]]}
        expect(banked_pickaxe(bank, 40)).to_match_object(Record({'name': 'Rune pickaxe'}))
        expect(banked_pickaxe(bank, 30)).to_match_object(Record({'name': 'Steel pickaxe'}))
        expect(banked_pickaxe(bank, 1)).to_match_object(Record({'name': 'Bronze pickaxe'}))
    test('the best banked pickaxe wins over the cheapest', _fn17)

    def _fn18():
        expect(banked_pickaxe({}, 40)).to_be_null()
    test('an empty bank yields nothing rather than a bronze default', _fn18)

    def _fn19():
        expect(any([('pickaxe' in w.name) for w in MELEE_WEAPONS])).to_be(False)
    test('a pickaxe is never offered as a weapon to fight with', _fn19)


describe('pickaxes ride the same tiers', _fn15)
