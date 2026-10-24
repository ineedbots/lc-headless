"""rs2b0t's test/api/bank/bankQuestJunk.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs import Record
from rs2004.banksort import QUEST_JUNK, find_quest_junk


entry = QUEST_JUNK[0]
QUEST_TAB = set([
    "Black Knight's Fortress",
    "Cook's Assistant",
    'Demon Slayer',
    'Rune Mysteries Quest',
    "Doric's Quest",
    'The Restless Ghost',
    'Goblin Diplomacy',
    'Ernest the Chicken',
    'Imp Catcher',
    "Pirate's Treasure",
    'Prince Ali Rescue',
    'Romeo & Juliet',
    'Sheep Shearer',
    'Shield of Arrav',
    "The Knight's Sword",
    'Vampire Slayer',
    "Witch's Potion",
    'Watch Tower',
    'Waterfall Quest',
    "Witch's House",
    'Biohazard',
    'Clock Tower',
    'Digsite Quest',
    'Big Chompy Bird Hunting',
    'Dwarf Cannon',
    'Family Crest',
    'Fight Arena',
    'Fishing Contest',
    "Gertrude's Cat",
    'The Grand Tree',
    'Hazeel Cult',
    "Hero's Quest",
    'Jungle Potion',
    'Legends Quest',
    'Lost City',
    "Merlin's Crystal",
    "Monk's Friend",
    'Murder Mystery',
    'Observatory Quest',
    'Plague City',
    'Scorpion Catcher',
    'Sea Slug Quest',
    'Sheep Herder',
    'Shilo Village',
    'Temple of Ikov',
    'The Tourist Trap',
    'Tree Gnome Village',
    'Tribal Totem',
    'Underground Pass',
    'Dragon Slayer',
    'Elemental Workshop',
    'Druidic Ritual',
    'Priest in Peril',
    'Nature Spirit',
    'Death Plateau',
    'Troll Stronghold',
    "Eadgar's Ruse",
    'Tai Bwo Wannai Trio',
    'Regicide',
    'Shades of Mortton',
    'Throne of Miscellania',
    'The Fremennik Trials',
    'Holy Grail',
    'Horror from the Deep',
    'Haunted Mine',
    'Monkey Madness',
    'Troll Romance',
    'In Search of the Myreque',
])


def statuses(by_quest):
    return lambda quest: by_quest.get(quest, 'unknown')


def _fn1():
    def _fn2():
        found = find_quest_junk([Record({'id': entry.id})], statuses({entry.quest: 'complete'}))
        expect(found).to_have_length(1)
        expect(found[0].droppable).to_be(True)
    test('a complete quest makes its leftover droppable', _fn2)

    def _fn3():
        found = find_quest_junk([Record({'id': entry.id})], statuses({entry.quest: 'inProgress'}))
        expect(found[0].droppable).to_be(False)
    test('an in-progress quest is reported but never droppable', _fn3)

    def _fn4():
        found = find_quest_junk([Record({'id': entry.id})], statuses({entry.quest: 'notStarted'}))
        expect(found[0].droppable).to_be(False)
    test('a not-started quest is reported but never droppable', _fn4)

    def _fn5():
        found = find_quest_junk([Record({'id': entry.id})], statuses({}))
        expect(found[0].status).to_be('unknown')
        expect(found[0].droppable).to_be(False)
    test('an unknown status is reported but never droppable', _fn5)

    def _fn6():
        expect(find_quest_junk([Record({'id': 31337})], statuses({}))).to_equal([])
    test('items not on the list are ignored', _fn6)

    def _fn7():
        expect(find_quest_junk([], statuses({}))).to_equal([])
    test('an empty bank finds nothing', _fn7)

    def _fn8():
        found = find_quest_junk([Record({'id': 2399}), Record({'id': 300})], statuses({'Demon Slayer': 'complete', "Witch's Potion": 'inProgress'}))
        expect((([f for f in found if f.id == 2399] or [None])[0].droppable if ([f for f in found if f.id == 2399] or [None])[0] is not None else None)).to_be(True)
        expect((([f for f in found if f.id == 300] or [None])[0].droppable if ([f for f in found if f.id == 300] or [None])[0] is not None else None)).to_be(False)
    test('only the finished quests leftover is droppable', _fn8)


describe('findQuestJunk', _fn1)


def _fn9():
    def _fn10():
        expect(len(set([e.id for e in QUEST_JUNK]))).to_be(len(QUEST_JUNK))
    test('the list has no duplicate ids', _fn10)

    def _fn11():
        tail = ([item for item in QUEST_JUNK if item.id == 300] or [None])[0]
        expect((tail.name if tail is not None else None)).to_be("Rat's tail")
        expect((tail.quest if tail is not None else None)).to_be("Witch's Potion")
    test("Witch's Potion leftover is id 300 Rat's tail", _fn11)

    def _fn12():
        for item in QUEST_JUNK:
            expect(item.id).to_be_greater_than_or_equal(0)
            expect(len(item.name)).to_be_greater_than(0)
            expect(len(item.quest)).to_be_greater_than(0)
            expect((item.quest in QUEST_TAB), item.quest).to_be(True)
    test('every entry names an item and a quest-tab row', _fn12)

    def _fn13():
        keys = [item for item in QUEST_JUNK if item.name == 'Key']
        expect(len(keys)).to_be_greater_than(1)
        expect(len(set([item.id for item in keys]))).to_be(len(keys))
    test('same display names stay distinct by id', _fn13)

    def _fn14():
        expect(([item for item in QUEST_JUNK if item.id == 0] or [None])[0]).to_equal(Record({'id': 0, 'name': 'Dwarf remains', 'quest': 'Dwarf Cannon'}))
        expect((([item for item in QUEST_JUNK if item.id == 2399] or [None])[0].quest if ([item for item in QUEST_JUNK if item.id == 2399] or [None])[0] is not None else None)).to_be('Demon Slayer')
        expect((([item for item in QUEST_JUNK if item.id == 600] or [None])[0].name if ([item for item in QUEST_JUNK if item.id == 600] or [None])[0] is not None else None)).to_be('Astrology book')
        expect((([item for item in QUEST_JUNK if item.id == 415] or [None])[0].name if ([item for item in QUEST_JUNK if item.id == 415] or [None])[0] is not None else None)).to_be('Ethanea')
        expect((([item for item in QUEST_JUNK if item.id == 78] or [None])[0].name if ([item for item in QUEST_JUNK if item.id == 78] or [None])[0] is not None else None)).to_be('Ice arrows')
        expect((([item for item in QUEST_JUNK if item.id == 3] or [None])[0].name if ([item for item in QUEST_JUNK if item.id == 3] or [None])[0] is not None else None)).to_be("Nulodion's notes.")
        expect((([item for item in QUEST_JUNK if item.id == 3102] or [None])[0].quest if ([item for item in QUEST_JUNK if item.id == 3102] or [None])[0] is not None else None)).to_be('Death Plateau')
    test('Recycling Centre leftovers that exist at 289 are on the list', _fn14)

    def _fn15():
        ids = set([item.id for item in QUEST_JUNK])
        for id in [4, 79, 80, 81, 82, 85, 88, 294, 617]:
            expect((id in ids), str(id)).to_be(False)
    test('skips noted variants, dummy ice-arrow stacks, fake coins and later-quest keys', _fn15)


describe('QUEST_JUNK', _fn9)
