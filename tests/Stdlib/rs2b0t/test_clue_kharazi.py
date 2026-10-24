"""rs2b0t's test/api/ai/clues/kharaziJungle.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and
expect. The band check plans over the real map, so it's in nav/test_clue_kharazi_band.py. tirannwnTravel.test.ts
isn't ported yet: its cases drive Regicide's seams and Legends' Quest's jungle code, which phase 17 brings."""

from rs2004.clues.data import CLUE_DB, PACK_UNREACHABLE
from rs2004.clues.travel import KHARAZI_CLUES, crosses_kharazi, has_jungle_map, in_kharazi, jungle_axe, jungle_crossing, jungle_kit_missing

KHARAZI_IDS = sorted(list(KHARAZI_CLUES))
CHEST_DIG = 3536
JUNGLE_LANDING = Tile(2816, 2936, 0)
KARAMJA_MAINLAND = Tile(2946, 3050, 0)


def exactly_inside():
    inside = sorted([id for id in CLUE_DB.keys() if in_kharazi(CLUE_DB[id].get('coord'))])
    expect(inside).to_equal(KHARAZI_IDS)


def chest_dig():
    expect(CHEST_DIG in KHARAZI_CLUES).to_be(True)
    c = CLUE_DB[CHEST_DIG]['coord']
    expect([c.x, c.z, c.level]).to_equal([2950, 2902, 0])


def diagnosed():
    for id in KHARAZI_IDS:
        expect(PACK_UNREACHABLE.get(id) or '').to_contain('machete')


describe('the Kharazi clue set', lambda: [
    test('is exactly the clues whose dig is inside the jungle', exactly_inside),
    test('08 05 South 15 56 East is one of them, and digs at (2950,2902)', chest_dig),
    test('each one still tells the pack audit why it cannot be routed to', diagnosed),
])


def stub_pack(at, inv=None, worn=None, banked=None, legends='started'):
    held = set([n.lower() for n in (inv or [])])
    wearing = set([n.lower() for n in (worn or [])])
    stored = set([n.lower() for n in (banked or [])])
    spy_on(game, 'tile', lambda: at)
    spy_on(inventory, 'first', lambda name: Fake(id=0, count=1) if name.lower() in held else None)
    spy_on(equipment, 'contains', lambda name: name.lower() in wearing)
    spy_on(bank, 'count', lambda name: 1 if name.lower() in stored else 0)
    spy_on(skills, 'level', lambda name: 60)
    spy_on(quests, 'status', lambda name: legends)


def direction():
    dig = CLUE_DB[CHEST_DIG]['coord']
    expect(jungle_crossing(dig, KARAMJA_MAINLAND)).to_be('enter')
    expect(jungle_crossing(KARAMJA_MAINLAND, dig)).to_be('leave')
    expect(jungle_crossing(dig, JUNGLE_LANDING)).to_be('none')
    expect(jungle_crossing(KARAMJA_MAINLAND, KARAMJA_MAINLAND)).to_be('none')
    # Why: an unknown tile reads as outside, so a walk to a dig still cuts its way in rather than giving up.
    expect(jungle_crossing(dig, None)).to_be('enter')


def crossing():
    dig = CLUE_DB[CHEST_DIG]['coord']
    stub_pack(KARAMJA_MAINLAND)
    expect(crosses_kharazi(dig)).to_be(True)
    stub_pack(JUNGLE_LANDING)
    expect(crosses_kharazi(dig)).to_be(False)
    expect(crosses_kharazi(KARAMJA_MAINLAND)).to_be(True)


def empty_kit():
    stub_pack(KARAMJA_MAINLAND)
    expect(jungle_kit_missing()).to_equal(['Machete', 'an axe', "Radimus notes (Legends' Quest reads started)"])


def enough():
    stub_pack(KARAMJA_MAINLAND, ['Machete', 'Bronze axe', 'Radimus notes'])
    expect(jungle_kit_missing()).to_equal([])


def finished_legends():
    stub_pack(KARAMJA_MAINLAND, ['Iron axe'], ['Machete'], None, 'complete')
    expect(has_jungle_map()).to_be(True)
    expect(jungle_kit_missing()).to_equal([])


def best_axe():
    stub_pack(KARAMJA_MAINLAND, None, None, ['Bronze axe', 'Mithril axe', 'Adamant axe'])
    expect(jungle_axe()).to_be('Adamant axe')


def no_axe():
    stub_pack(KARAMJA_MAINLAND)
    expect(jungle_axe()).to_be(None)


describe('cutting into the jungle', lambda: [
    test('the direction to cut follows which end is inside', direction),
    test('a dig inside is a crossing from the mainland and not from inside', crossing),
    test('the kit the server checks is reported item by item when the pack is empty', empty_kit),
    test('a machete, any axe and the notes are enough', enough),
    test('a finished Legends account needs no notes, and a worn machete counts', finished_legends),
    test('the bank supplies the best axe it has, not the first', best_axe),
    test('no axe anywhere reads as none', no_axe),
])
