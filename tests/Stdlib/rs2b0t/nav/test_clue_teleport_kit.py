"""rs2b0t's test/api/ai/clues/teleportKit.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and
expect. It reads the walker's teleport catalog, so it runs with the real cache."""

from rs2004.clues.teleports import is_teleport_item, teleport_kit_for


def state(members=False, skills=None, quests=None):
    return {'members': members, 'skills': skills or {}, 'quests': quests or {}, 'items': {}, 'worn': {}, 'free_slots': 20,
            'entrana_restricted_gear': False}


def rune_names(kit):
    return sorted([name for name, _ in kit.runes])


def per_cast(kit, name):
    for rune, count in kit.runes:
        if rune == name:
            return count
    return 0


def varrock_only():
    kit = teleport_kit_for(state(skills={'magic': 25}))
    expect(rune_names(kit)).to_equal(['Air rune', 'Fire rune', 'Law rune'])
    expect(kit.usable).to_equal(['varrock'])
    expect(per_cast(kit, 'Air rune')).to_be(3)
    expect(per_cast(kit, 'Law rune')).to_be(1)


def ardougne_gate():
    no_quest = teleport_kit_for(state(True, {'magic': 51}))
    expect(no_quest.usable).not_.to_contain('ardougne')
    done = teleport_kit_for(state(True, {'magic': 51}, {'Plague City': 'complete'}))
    expect(done.usable).to_contain('ardougne')
    expect(per_cast(done, 'Law rune')).to_be(2)


def maxed():
    kit = teleport_kit_for(state(True, {'magic': 99}, {'Plague City': 'complete', 'Watch Tower': 'complete', "Eadgar's Ruse": 'complete'}))
    for id in ['varrock', 'lumbridge', 'falador', 'camelot', 'ardougne', 'watchtower', 'trollheim']:
        expect(kit.usable).to_contain(id)
    expect(rune_names(kit)).to_equal(['Air rune', 'Earth rune', 'Fire rune', 'Law rune', 'Water rune'])


describe('teleport_kit_for: magic level', lambda: [
    test('a magic-1 account gets no runes at all', lambda: [
        expect(teleport_kit_for(state(skills={'magic': 1})).runes).to_equal([]),
        expect(teleport_kit_for(state(skills={'magic': 1})).usable).to_equal([]),
    ]),
    test('magic 24 is still one level short of Varrock', lambda: expect(teleport_kit_for(state(skills={'magic': 24})).runes).to_equal([])),
    test('magic 25 unlocks Varrock only: fire, air, law', varrock_only),
    test('no water or earth runes until Falador and Lumbridge are castable', lambda: [
        expect(rune_names(teleport_kit_for(state(skills={'magic': 25})))).not_.to_contain('Water rune'),
        expect(rune_names(teleport_kit_for(state(skills={'magic': 31})))).to_contain('Earth rune'),
        expect(rune_names(teleport_kit_for(state(skills={'magic': 31})))).not_.to_contain('Water rune'),
        expect(rune_names(teleport_kit_for(state(skills={'magic': 37})))).to_contain('Water rune'),
    ]),
])

describe('teleport_kit_for: members and quest gates', lambda: [
    test('Camelot lifts the air-rune count to 5, but only on a members world', lambda: [
        expect(per_cast(teleport_kit_for(state(skills={'magic': 45})), 'Air rune')).to_be(3),
        expect(per_cast(teleport_kit_for(state(True, {'magic': 45})), 'Air rune')).to_be(5),
    ]),
    test('Ardougne stays out until Plague City is complete', ardougne_gate),
    test('a maxed members account gets the whole spellbook', maxed),
])

describe('teleport_kit_for: jewellery', lambda: [
    test('glory and the dueling ring need no magic, so a level-1 account still keeps them', lambda: [
        expect(teleport_kit_for(state(skills={'magic': 1})).jewellery_prefixes).to_contain('amulet of glory('),
        expect(teleport_kit_for(state(skills={'magic': 1})).jewellery_prefixes).to_contain('ring of dueling'),
    ]),
    test('the games necklace drops out on a free world', lambda: [
        expect(teleport_kit_for(state()).jewellery_prefixes).not_.to_contain('games necklace'),
        expect(teleport_kit_for(state(True)).jewellery_prefixes).to_contain('games necklace'),
    ]),
])

describe('is_teleport_item', lambda: [
    test('a rune no spell can pay for is not kit, so the bank stop deposits it', lambda: [
        expect(is_teleport_item('Law rune', teleport_kit_for(state(skills={'magic': 25})))).to_be(True),
        expect(is_teleport_item('Water rune', teleport_kit_for(state(skills={'magic': 25})))).to_be(False),
        expect(is_teleport_item('Earth rune', teleport_kit_for(state(skills={'magic': 25})))).to_be(False),
    ]),
    test('a magic-1 account keeps no runes but still keeps a charged glory', lambda: [
        expect(is_teleport_item('Law rune', teleport_kit_for(state(skills={'magic': 1})))).to_be(False),
        expect(is_teleport_item('Amulet of glory(4)', teleport_kit_for(state(skills={'magic': 1})))).to_be(True),
    ]),
])
