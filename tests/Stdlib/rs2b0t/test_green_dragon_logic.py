"""rs2b0t's test/scripts/GreenDragon/GreenDragonLogic.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe,
test and expect."""

from rs2004.catalogs import Record
from bots.greendragon.logic import WILDY_MIN_Z, LootFilter, escape_needed, gear_candidates, gear_to_keep, in_wilderness, is_clue_like
from bots.greendragon.logic import is_grind_foreign, pack_forces_bank, slot_freeing_action, under_player_attack, wants_ground_item

# trail_clue_hard_sextant001 and its casket.
HARD_CLUE = 2723
HARD_CASKET = 2724

DRAGON_LOOT = set(['dragon bones', 'dragonhide', 'herb'])


def filter(loot_set=None, bank_common=True, solve_clues=True, bury_bones=False, bone_name=None):
    return LootFilter(loot_set if loot_set is not None else DRAGON_LOOT, bank_common, solve_clues, bury_bones, bone_name)


def item(id, name):
    return Record({'id': id, 'name': name})


def slots(pack_full=True, loot_present=True, food_count=25, food_reserve=4, hp_fraction=0.6, loot_stacks_into_pack=False):
    return slot_freeing_action(pack_full, loot_present, food_count, food_reserve, hp_fraction, loot_stacks_into_pack)


def esc(threat=False, hp_fraction=0.1, panic_hp=0.3, has_food=False, at_bank=False):
    return escape_needed(threat, hp_fraction, panic_hp, has_food, at_bank)


describe('in_wilderness', lambda: [
    test('the ditch row itself is not wilderness', lambda: expect(in_wilderness(WILDY_MIN_Z)).to_be(False)),
    test('one row north is', lambda: expect(in_wilderness(WILDY_MIN_Z + 1)).to_be(True)),
    test('the dragon field is, the Edgeville bank is not', lambda: [expect(in_wilderness(3814)).to_be(True), expect(in_wilderness(3493)).to_be(False)]),
])

describe('under_player_attack', lambda: [
    test('retaliating at a player in the wilderness is an attack', lambda: expect(under_player_attack(3814, True)).to_be(True)),
    test('fighting only dragons is not', lambda: expect(under_player_attack(3814, False)).to_be(False)),
    test('players in Varrock on a clue trail are not', lambda: expect(under_player_attack(3424, True)).to_be(False)),
    test('an unknown position is never an attack', lambda: expect(under_player_attack(None, True)).to_be(False)),
])

ARMOUR = ['Rune platebody', 'Rune platelegs', 'Rune full helm']

describe('gear_candidates', lambda: [
    test('armour worn at start is kept and re-equipped, not just the weapon and shield', lambda: expect(gear_candidates('Rune scimitar', 'Dragonfire shield', ARMOUR)).to_equal(
        ['Rune scimitar', 'Dragonfire shield', 'Rune platebody', 'Rune platelegs', 'Rune full helm'])),
    test('the configured weapon and shield are not duplicated when also worn at start', lambda: expect(gear_candidates('Rune scimitar', 'Dragonfire shield', ['rune scimitar', 'Rune platebody'])).to_equal(
        ['Rune scimitar', 'Dragonfire shield', 'Rune platebody'])),
    test('an empty weapon or shield slot contributes nothing', lambda: [
        expect(gear_candidates('', '', ARMOUR)).to_equal(ARMOUR),
        expect(gear_candidates('', '', [])).to_equal([]),
    ]),
])

HELM = 'Adamant full helm'
KIT = ['Rune scimitar', 'Anti-dragon shield', HELM]


def worn(*names):
    return lambda n: len([w for w in names if w.lower() == n.lower()]) > 0


describe('gear_to_keep', lambda: [
    test('gear that is already on needs no keep slot', lambda: expect(gear_to_keep(KIT, worn(*KIT))).to_equal([])),
    test('gear stripped into the pack is kept so it can be re-equipped', lambda: expect(gear_to_keep(KIT, worn('Rune scimitar', 'Anti-dragon shield'))).to_equal([HELM])),
    test('a looted duplicate of worn armour still banks', lambda: expect(deposit_all_except(
        gear_to_keep(gear_candidates('Rune scimitar', 'Anti-dragon shield', [HELM]), worn(*KIT)))(HELM)).to_be(True)),
    test('the stripped original is not banked out from under the re-equip', lambda: expect(deposit_all_except(
        gear_to_keep(gear_candidates('Rune scimitar', 'Anti-dragon shield', [HELM]), worn('Rune scimitar')))(HELM)).to_be(False)),
])

describe('is_clue_like', lambda: [
    test('a hard clue scroll and its casket both match', lambda: [expect(is_clue_like(HARD_CLUE)).to_be(True), expect(is_clue_like(HARD_CASKET)).to_be(True)]),
    test('dragon loot does not', lambda: expect(is_clue_like(536)).to_be(False)),
])


def burying_bones():
    no_bones = filter(loot_set=set(['dragonhide']))
    expect(wants_ground_item(item(536, 'Dragon bones'), no_bones)).to_be(False)
    expect(wants_ground_item(item(536, 'Dragon bones'), filter(loot_set=set(['dragonhide']), bury_bones=True, bone_name='Dragon bones'))).to_be(True)


describe('wants_ground_item', lambda: [
    test('takes loot named in the loot set', lambda: expect(wants_ground_item(item(536, 'Dragon bones'), filter())).to_be(True)),
    test('ignores loot the user unchecked', lambda: expect(wants_ground_item(item(1753, 'Dragon spear'), filter())).to_be(False)),
    test('takes a clue even though it is absent from the loot set', lambda: expect(wants_ground_item(item(HARD_CLUE, 'Clue scroll'), filter())).to_be(True)),
    test('leaves the clue when clue solving is off', lambda: expect(wants_ground_item(item(HARD_CLUE, 'Clue scroll'), filter(solve_clues=False))).to_be(False)),
    test('an emptied loot set still takes clues', lambda: [
        expect(wants_ground_item(item(HARD_CLUE, 'Clue scroll'), filter(loot_set=set(), bank_common=False))).to_be(True),
        expect(wants_ground_item(item(536, 'Dragon bones'), filter(loot_set=set(), bank_common=False))).to_be(False),
    ]),
    test('common junk follows its own toggle', lambda: [
        expect(wants_ground_item(item(1623, 'Uncut sapphire'), filter())).to_be(True),
        expect(wants_ground_item(item(1623, 'Uncut sapphire'), filter(bank_common=False))).to_be(False),
    ]),
    test('an unnamed ground item is never taken', lambda: expect(wants_ground_item(item(4242, None), filter())).to_be(False)),
    test('burying forces bones to be looted even when unchecked', burying_bones),
    test('burying does not drag in bones the bot was not told to bury', lambda: expect(wants_ground_item(item(526, 'Bones'),
        filter(loot_set=set(), bank_common=False, bury_bones=True, bone_name='Dragon bones'))).to_be(False)),
])

describe('escape_needed', lambda: [
    test('flees when starving and hurt out in the field', lambda: expect(esc()).to_be(True)),
    test('stops once it reaches the bank — otherwise it re-walks forever', lambda: expect(esc(at_bank=True)).to_be(False)),
    test('a threat still overrides, even at the bank', lambda: expect(esc(threat=True, at_bank=True)).to_be(True)),
    test('food in the pack means eat, not flee', lambda: expect(esc(has_food=True)).to_be(False)),
    test('healthy and foodless is not a panic', lambda: expect(esc(hp_fraction=0.9)).to_be(False)),
])

describe('pack_forces_bank', lambda: [
    test('a pack full of food is NOT a reason to bank — it gets eaten', lambda: expect(pack_forces_bank(True, 25, 4)).to_be(False)),
    test('banks once the food is down to the reserve and cannot free a slot', lambda: [
        expect(pack_forces_bank(True, 4, 4)).to_be(True),
        expect(pack_forces_bank(True, 0, 4)).to_be(True),
    ]),
    test('a pack with room never forces a bank', lambda: expect(pack_forces_bank(False, 0, 4)).to_be(False)),
])

KEEP = set(['lobster', 'rune scimitar', 'dragonfire shield'])


def foreign(id, name):
    return is_grind_foreign(item(id, name), KEEP, filter())


describe('is_grind_foreign', lambda: [
    test('trail kit left over from a clue is foreign', lambda: [expect(foreign(9001, n)).to_be(True) for n in ['Spade', 'Sextant', 'Watch', 'Chart']]),
    test('grind gear and food are not foreign', lambda: [expect(foreign(1333, 'Rune scimitar')).to_be(False), expect(foreign(379, 'Lobster')).to_be(False)]),
    test('intended loot is not foreign', lambda: [expect(foreign(536, 'Dragon bones')).to_be(False), expect(foreign(1623, 'Uncut sapphire')).to_be(False)]),
    test('a clue is never foreign — SolveClue owns it', lambda: [expect(foreign(HARD_CLUE, 'Clue scroll')).to_be(False), expect(foreign(HARD_CASKET, 'Casket')).to_be(False)]),
    test('an unnamed item is never foreign', lambda: expect(foreign(9001, None)).to_be(False)),
])

describe('slot_freeing_action', lambda: [
    test('eats when the heal is not wasted', lambda: expect(slots(hp_fraction=0.6)).to_be('eat')),
    test('drops at full hp rather than eating for nothing', lambda: expect(slots(hp_fraction=1)).to_be('drop')),
    test('the 25-lobster case frees a slot instead of banking', lambda: expect(slots(food_count=25, hp_fraction=1)).to_be('drop')),
    test('does nothing when the pack has room', lambda: expect(slots(pack_full=False)).to_be('none')),
    test('does nothing when there is no loot to make room for', lambda: expect(slots(loot_present=False)).to_be('none')),
    test('never digs into the reserve', lambda: [
        expect(slots(food_count=5, food_reserve=4)).to_be('eat'),
        expect(slots(food_count=4, food_reserve=4)).to_be('none'),
        expect(slots(food_count=3, food_reserve=4)).to_be('none'),
    ]),
    test('a zero reserve still needs one food to spend', lambda: [
        expect(slots(food_count=1, food_reserve=0)).to_be('eat'),
        expect(slots(food_count=0, food_reserve=0)).to_be('none'),
    ]),
    test('does not burn food for loot that stacks into the pack', lambda: expect(slots(loot_stacks_into_pack=True)).to_be('none')),
])
