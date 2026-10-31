"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/lostcity.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.entities import locs
from rs2004.items import inventory
from rs2004.traversal import traversal
from rs2004.quests.defs.lostcity import LOST_CITY_FOOD_TARGET, LOST_CITY_STAFF_TARGET, LOST_CITY_STAGE, decide, lost_city_area, lostcity, parse_lost_city_journal
from rs2004.quests.food import quest_food
from rs2004.geometry import Tile
from rs2004.quests.engine.types import QuestSnapshot

MAINLAND = Tile(3200, 3200, 0)
ENTRANA_SHIP = Tile(2834, 3334, 1)
ENTRANA = Tile(2820, 3374, 0)
DUNGEON = Tile(2822, 9774, 0)
ZANARIS = Tile(3220, 9592, 0)
COMBAT_FOOD = ['Lobster'] * LOST_CITY_FOOD_TARGET


def counts(names):
    result = {}
    for name in names:
        key = name.lower()
        _v1 = result.get(key)
        result[key] = ((_v1 if _v1 is not None else 0)) + 1
    return result


def snap(options=None):
    if options is None:
        options = Record({})
    return QuestSnapshot(**{
        'journal': (options.journal if options.journal is not None else 'in_progress'),
        'inv': counts((options.inv if options.inv is not None else [])),
        'worn': set([name.lower() for name in ((options.worn if options.worn is not None else []))]),
        'no_progress': 0,
        'bank_coins': 0,
        'stage': (options.stage if options.stage is not None else LOST_CITY_STAGE.NOT_STARTED),
        'bank': counts((options.bank if options.bank is not None else [])),
        'bank_known': (options.bank_known if options.bank_known is not None else True),
        'tile': (MAINLAND if options.tile is None else options.tile),
        'magic': (options.magic if options.magic is not None else 1),
        'free_slots': options.free_slots,
    })


def custom_name(step):
    return (step.name if step.kind == 'custom' else None)


def _fn2():
    quest_food.name = 'Lobster'


before_each(_fn2)


def _fn3():
    def _fn4(text, stage):
        expect(parse_lost_city_journal(text)).to_be(stage)
    test_each([
        ['@dbl@I can start this quest by speaking to the Adventurers', 0],
        ['@dbl@Apparently there is a @dre@leprechaun@dbl@ hiding in a @dre@tree', 1],
        ['I found a Leprechaun.|@dbl@I can find a @dre@Dramen Tree@dbl@ in a cave', 2],
        ['@dbl@With the @dre@Spirit@dbl@ defeated I can cut a @dre@branch@dbl@ from the tree', 3],
        [
        'I cut a branch from the tree.|@dbl@I should @dre@craft@dbl@ the @dre@branch@dbl@ from the tree into a @dre@staff',
        4,
    ],
        ['I cut a branch from the tree and crafted a Dramen Staff.', 5],
        ['@red@QUEST COMPLETE!', 6],
    ])('maps rendered journal text to exact stage %i', _fn4)

    def _fn5():
        expect(parse_lost_city_journal(['Lost City', 'Loading…'])).to_be_undefined()
    test('does not infer a stage from unrecognized text', _fn5)


describe('Lost City journal stage parsing', _fn3)


def _fn6():
    def _fn7():
        expect(lost_city_area(MAINLAND)).to_be('mainland')
        expect(lost_city_area(ENTRANA_SHIP)).to_be('entranaShip')
        expect(lost_city_area(ENTRANA)).to_be('entrana')
        expect(lost_city_area(DUNGEON)).to_be('dungeon')
        expect(lost_city_area(ZANARIS)).to_be('zanaris')
        expect(lost_city_area(None)).to_be('unknown')
    test('recognizes each quest region and a missing player tile', _fn7)


describe('Lost City area classification', _fn6)


def _fn8():
    def _fn9():
        expect(decide(snap(Record({'stage': 0, 'bank_known': False}))).kind).to_be('scan_bank')
    test('stage 0 checks an unknown bank before sourcing tools', _fn9)

    def _fn10():
        step = decide(snap(Record({'stage': 0})))
        expect(step.kind).to_be('grab_ground')
        expect(step.kind == 'grab_ground' and step.item).to_be('Knife')
        expect(step.kind == 'grab_ground' and step.wait_if_missing).to_be(True)
    test('stage 0 sources a missing Knife once the bank is known empty', _fn10)

    def _fn11():
        step = decide(snap(Record({'stage': 0, 'inv': ['Coins', 'Bones'], 'free_slots': 0})))
        expect(step.kind).to_be('deposit')
        expect(step.kind == 'deposit' and step.keep).to_contain('knife')
        expect(step.kind == 'deposit' and step.exact_keep).to_be(True)
    test('a full mainland pack is cleaned before acquiring another quest item', _fn11)

    def _fn12():
        knife = decide(snap(Record({'stage': 0, 'bank': ['Knife']})))
        expect(knife.kind == 'withdraw' and knife.items).to_equal([Record({'name': 'Knife', 'qty': 1})])
        axe = decide(snap(Record({'stage': 0, 'inv': ['Knife'], 'bank': ['Rune axe']})))
        expect(axe.kind == 'withdraw' and axe.items).to_equal([Record({'name': 'Rune axe', 'qty': 1})])
        start = decide(snap(Record({'stage': 0, 'inv': ['Knife', 'Bronze axe']})))
        expect(start.kind == 'talk' and start.stop.npc).to_be('Warrior')
    test('stage 0 withdraws known bank tools and then starts with the Warrior', _fn12)

    def _fn13():
        step = decide(snap(Record({'stage': 1, 'inv': ['Knife'], 'worn': ['Bronze axe']})))
        expect(custom_name(step)).to_be('reveal Shamus and learn about the staff')
    test('stage 1 reveals Shamus after ensuring the same mainland tools', _fn13)

    def _fn14():
        spillover = decide(snap(Record({'stage': 2, 'inv': ['Knife', 'Bronze axe']})))
        expect(spillover.kind).to_be('deposit')
        expect(spillover.kind == 'deposit' and spillover.keep).to_contain('knife')
        expect(spillover.kind == 'deposit' and spillover.exact_keep).to_be(True)
        lookalike = decide(snap(Record({'stage': 2, 'inv': ['Knife', 'Bronze knife']})))
        expect(lookalike.kind).to_be('deposit')
        equipment = decide(snap(Record({'stage': 2, 'inv': ['Knife'], 'worn': ['Leather body']})))
        expect(custom_name(equipment)).to_be('remove Entrana-restricted equipment')
        food = decide(snap(Record({'stage': 2, 'inv': ['Knife'], 'bank': COMBAT_FOOD})))
        expect(food.kind == 'withdraw' and food.items).to_equal([Record({'name': 'Lobster', 'qty': LOST_CITY_FOOD_TARGET})])
        ready = decide(snap(Record({'stage': 2, 'inv': ['Knife'] + list(COMBAT_FOOD) + list(['Mind rune'] * 200) + list(['Air rune'] * 200)})))
        expect(custom_name(ready)).to_be('sail from Port Sarim to Entrana')
    test('stage 2 strips Entrana-forbidden inventory and equipment before sailing', _fn14)

    def _fn15():
        quest_food.name = None
        blank = decide(snap(Record({'stage': 2, 'inv': ['Knife']})))
        expect(blank.kind == 'wait' and blank.reason).to_contain('select a food item')
        quest_food.name = 'Lobster'
        short = decide(snap(Record({'stage': 2, 'inv': ['Knife'], 'bank': ['Lobster'] * 3})))
        expect(short.kind == 'wait' and short.reason).to_contain(f'{LOST_CITY_FOOD_TARGET} combat food total')
        expect(repr(plain(short))).not_.to_contain('Kebab')
    test('requires the configured food without falling back to Kebabs', _fn15)

    def _fn16():
        step = decide(snap(Record({'stage': 2, 'inv': ['Knife'], 'bank': COMBAT_FOOD, 'free_slots': LOST_CITY_FOOD_TARGET - 1})))
        expect(step.kind).to_be('wait')
        expect(step.kind == 'wait' and step.reason).to_contain(f'{LOST_CITY_FOOD_TARGET} free inventory slots')
    test('reserves enough inventory space for all configured combat food', _fn16)

    def _fn17():
        expect(custom_name(decide(snap(Record({'stage': 2, 'tile': ENTRANA_SHIP}))))).to_be('disembark on Entrana')
        expect(custom_name(decide(snap(Record({'stage': 2, 'tile': ENTRANA}))))).to_be('descend the one-way Entrana ladder')
    test('stage 2 resumes aboard the ship and on Entrana', _fn17)

    def _fn18():
        missing = decide(snap(Record({'stage': 2, 'tile': DUNGEON})))
        expect(custom_name(missing)).to_be('get an axe from Entrana Zombies')
        held = decide(snap(Record({'stage': 2, 'tile': DUNGEON, 'inv': ['Bronze axe']})))
        expect(held.kind == 'equip' and held.item).to_be('Bronze axe')
        equipped = decide(snap(Record({'stage': 2, 'tile': DUNGEON, 'worn': ['Bronze axe']})))
        expect(custom_name(equipped)).to_be('defeat the Tree Spirit')
    test('stage 2 dungeon restart obtains, equips, then uses a dropped axe', _fn18)

    def _fn19():
        ready = decide(snap(Record({'stage': 3, 'tile': DUNGEON, 'worn': ['Iron axe']})))
        expect(custom_name(ready)).to_be('cut a Dramen branch')
        restarted = decide(snap(Record({'stage': 3, 'tile': DUNGEON})))
        expect(custom_name(restarted)).to_be('get an axe from Entrana Zombies')
    test('stage 3 cuts a branch in the dungeon and can recover an axe after restart', _fn19)


describe('Lost City stages 0-3', _fn8)


def _fn20():
    def _fn21():
        collect = decide(snap(Record({'stage': 4, 'inv': ['Knife', 'Dramen branch'], 'worn': ['Iron axe'], 'tile': DUNGEON})))
        expect(custom_name(collect)).to_be('cut a Dramen branch')
        inventory = ['Knife'] + list(['Dramen branch'] * LOST_CITY_STAFF_TARGET)
        stage = LOST_CITY_STAGE.BRANCH_CUT
        for made in range(LOST_CITY_STAFF_TARGET):
            step = decide(snap(Record({'stage': stage, 'inv': inventory, 'worn': ['Iron axe'], 'tile': DUNGEON})))
            expect(step.kind).to_be('use_on')
            if step.kind == 'use_on':
                expect(step.item).to_be('Knife')
                expect(step.target).to_be('Dramen branch')
                expect(step.product).to_be('Dramen staff')
            inventory = [name for index, name in enumerate(inventory) if name != 'Dramen branch' or index != (inventory.index('Dramen branch') if 'Dramen branch' in inventory else -1)]
            inventory.append('Dramen staff')
            stage = LOST_CITY_STAGE.STAFF_MADE
        expect(custom_name(decide(snap(Record({'stage': stage, 'inv': inventory, 'worn': ['Iron axe'], 'tile': DUNGEON}))))).to_be('exit through the Wilderness portal')
    test('collects five branches before crafting all five staves', _fn21)

    def _fn22():
        step = decide(snap(Record({'stage': 4, 'inv': ['Dramen branch'] * LOST_CITY_STAFF_TARGET, 'tile': DUNGEON})))
        expect(custom_name(step)).to_be('leave the dungeon to replace the Knife')
    test('leaves the dungeon if five held branches have outlived the Knife', _fn22)

    def _fn23():
        expect(decide(snap(Record({'stage': 4, 'bank_known': False}))).kind).to_be('scan_bank')
        bank = ['Knife'] + list(['Dramen staff'] * 2) + list(['Dramen branch'] * 3)
        knife = decide(snap(Record({'stage': 4, 'bank': bank})))
        expect(knife.kind == 'withdraw' and knife.items).to_equal([Record({'name': 'Knife', 'qty': 1})])
        materials = decide(snap(Record({'stage': 4, 'inv': ['Knife'], 'bank': bank})))
        expect(materials.kind == 'withdraw' and materials.items).to_equal([Record({'name': 'Dramen staff', 'qty': 2}), Record({'name': 'Dramen branch', 'qty': 3})])
    test('scans an unknown bank, then restores a mixed five-staff batch', _fn23)

    def _fn24():
        mainland = decide(snap(Record({'stage': 4, 'inv': ['Knife'] + list(COMBAT_FOOD)})))
        expect(custom_name(mainland)).to_be('sail from Port Sarim to Entrana')
        dungeon = decide(snap(Record({'stage': 4, 'tile': DUNGEON, 'worn': ['Bronze axe']})))
        expect(custom_name(dungeon)).to_be('cut a Dramen branch')
    test('recovers a lost branch by returning to Entrana and cutting another', _fn24)


describe('Lost City stage 4 branch recovery', _fn20)


def _fn25():
    def _fn26():
        expect(decide(snap(Record({'stage': 5, 'bank_known': False}))).kind).to_be('scan_bank')
        step = decide(snap(Record({'stage': 5, 'bank': ['Dramen staff'] * LOST_CITY_STAFF_TARGET})))
        expect(step.kind == 'withdraw' and step.items).to_equal([Record({'name': 'Dramen staff', 'qty': LOST_CITY_STAFF_TARGET})])
    test('stage 5 scans first, then restores five banked staves', _fn26)

    def _fn27():
        step = decide(snap(Record({'stage': 5, 'inv': ['Knife', 'Dramen staff'] + list(COMBAT_FOOD)})))
        expect(step.kind).to_be('deposit')
        expect(step.kind == 'deposit' and step.keep).not_.to_contain('dramen staff')
    test('stage 5 does not equip or finish with only one staff', _fn27)

    def _fn28():
        equip = decide(snap(Record({'stage': 5, 'inv': ['Dramen staff'] * LOST_CITY_STAFF_TARGET, 'bank_known': False})))
        expect(equip.kind == 'equip' and equip.item).to_be('Dramen staff')
        enter = decide(snap(Record({'stage': 5, 'inv': ['Dramen staff'] * (LOST_CITY_STAFF_TARGET - 1), 'worn': ['Dramen staff']})))
        expect(custom_name(enter)).to_be('enter Zanaris through the swamp shed')
    test('stage 5 equips only after holding five staves and then enters Zanaris', _fn28)

    def _fn29():
        step = decide(snap(Record({'stage': 5, 'inv': ['Dramen staff'] * LOST_CITY_STAFF_TARGET, 'worn': ['Iron axe'], 'tile': DUNGEON})))
        expect(custom_name(step)).to_be('exit through the Wilderness portal')
    test('stage 5 exits the dungeon after all five staves are made', _fn29)

    def _fn30():
        mainland = decide(snap(Record({'stage': 5, 'inv': ['Knife'] + list(COMBAT_FOOD)})))
        expect(custom_name(mainland)).to_be('sail from Port Sarim to Entrana')
        dungeon = decide(snap(Record({'stage': 5, 'tile': DUNGEON})))
        expect(custom_name(dungeon)).to_be('get an axe from Entrana Zombies')
    test('stage 5 recovers a completely lost staff, including an axe-less dungeon restart', _fn30)

    def _fn31():
        expect(decide(snap(Record({'stage': 6}))).kind).to_be('done')
        expect(decide(snap(Record({'stage': 0, 'journal': 'complete'}))).kind).to_be('done')
    test('stage 6 is done even before the journal cache updates', _fn31)

    def _fn32():
        expect(decide(snap(Record({'stage': 2, 'journal': 'unknown'}))).kind).to_be('wait')
    test('unknown journal remains safely idle', _fn32)

    def _fn33():
        # 0.5, not 0.9; the tree spirit fight was burning food every tick (#393).
        expect(lostcity.sustain).to_equal(Record({'foods': [], 'eat_below_hp': 0.5}))
    test('uses the AIO-selected food at the quest-safe combat threshold', _fn33)


describe('Lost City stages 5-6', _fn25)


def ready(magic, inventory=None, bank=None):
    if inventory is None:
        inventory = {}
    if bank is None:
        bank = {}
    state = snap(Record({'stage': 2, 'magic': magic, 'inv': ['Knife'] + list(COMBAT_FOOD), 'free_slots': 19}))
    for name, count in inventory.items():
        state.inv[name.lower()] = count
    state.bank = {_k: _v for _k, _v in [[name.lower(), count] for name, count in list(bank.items())]}
    return state


def provisions_batch(magic, wanted):
    def run():
        step = decide(ready(magic, {}, {'Mind rune': 1000, 'Air rune': 1000, 'Water rune': 1000, 'Earth rune': 1000, 'Fire rune': 1000}))
        expect(step.kind).to_be('withdraw')
        if step.kind == 'withdraw':
            expect({item['name']: item['qty'] for item in step.items}).to_equal(wanted)
    return run


def _fn34():
    for magic, wanted in [
        [1, {'Mind rune': 150, 'Air rune': 150}],
        [5, {'Mind rune': 150, 'Air rune': 150, 'Water rune': 150}],
        [9, {'Mind rune': 150, 'Air rune': 150, 'Earth rune': 300}],
        [13, {'Mind rune': 150, 'Air rune': 300, 'Fire rune': 450}],
    ]:
        test(f'provisions the highest Strike batch at Magic {magic}', provisions_batch(magic, wanted))

    def _fn37():
        state = ready(13, {'Mind rune': 150, 'Air rune': 150})
        state.bank_known = False
        expect(decide(state).kind).to_be('scan_bank')
    test('waits for the bank snapshot before choosing a weaker held spell', _fn37)

    def _fn38():
        step = decide(ready(13, {}, {'Mind rune': 150, 'Air rune': 300, 'Fire rune': 3, 'Earth rune': 300}))
        expect(step.kind == 'withdraw' and step.items).to_equal([
        Record({'name': 'Mind rune', 'qty': 150}),
        Record({'name': 'Fire rune', 'qty': 3}),
        Record({'name': 'Air rune', 'qty': 300}),
    ])
    test('withdraws available runes before buying the stronger element shortfall', _fn38)

    def _fn39():
        state = ready(13, {'Mind rune': 149, 'Air rune': 299, 'Fire rune': 449}, {'Mind rune': 1, 'Air rune': 1, 'Fire rune': 1})
        state.free_slots = 0
        step = decide(state)
        expect(step.kind == 'withdraw' and step.items).to_equal([
        Record({'name': 'Mind rune', 'qty': 1}),
        Record({'name': 'Fire rune', 'qty': 1}),
        Record({'name': 'Air rune', 'qty': 1}),
    ])
    test('tops up existing rune stacks without requiring free inventory slots', _fn39)

    def _fn40():
        state = ready(1, {}, {'Mind rune': 150, 'Air rune': 150})
        state.free_slots = 0
        step = decide(state)
        expect(step.kind == 'wait' and step.reason).to_contain('2 free inventory slots')
    test('waits for room for new stacks in a full preserved pack', _fn40)

    def _fn41():
        for stage in [0, 2]:
            state = snap(Record({
            'stage': stage,
            'inv': ['Bones', 'Air rune', 'Mind rune', 'Water rune', 'Earth rune', 'Fire rune'],
            'free_slots': 0,
        }))
            step = decide(state)
            expect(step.kind).to_be('deposit')
            if step.kind == 'deposit':
                for rune in ['air rune', 'mind rune', 'water rune', 'earth rune', 'fire rune']:
                    expect(step.keep).to_contain(rune)
    test('keeps all Strike runes when clearing mainland and Entrana packs', _fn41)

    def _fn42():
        step = decide(ready(13, {'Mind rune': 149, 'Air rune': 149}))
        expect(step).to_match_object(Record({'kind': 'buy', 'item': 'Mind rune', 'qty': 1}))
    test('does not sail with an incomplete Strike batch', _fn42)

    def _fn43():
        state = ready(13, {'Mind rune': 150, 'Air rune': 300, 'Fire rune': 450})
        state.bank_known = False
        expect(custom_name(decide(state))).to_be('sail from Port Sarim to Entrana')
    test('a complete held Fire Strike batch sails without an unnecessary bank scan', _fn43)

    def _fn44(stage):
        state = ready(1)
        state.stage = stage
        expect(custom_name(decide(state))).to_be('sail from Port Sarim to Entrana')
    test_each([3, 4, 5])('post-spirit stage %i can sail without rune provisions', _fn44)


describe('Lost City Strike provisions', _fn34)
class PackItem:
    """An inventory item of the full branch pack, which records what it's asked to do."""

    def __init__(self, pack, slot, name):
        self.pack = pack
        self.id = slot
        self.slot = slot
        self.name = name

    def actions(self):
        return ['Eat', 'Drop'] if self.name == 'Lobster' else ['Drop']

    def interact(self, op):
        self.pack.interactions.append(f'{op} {self.name}')
        if self.pack.scenario != 'pending':
            self.pack.items.remove(self)
        return True


class BranchPack:
    """A full pack at the Dramen tree: the tree's Chop down adds a branch once a slot is free."""

    def __init__(self, scenario):
        self.scenario = scenario
        names = ['Knife', 'Air rune', 'Mind rune', 'Fire rune'] + ['Dramen branch'] * 4 + ['Lobster'] * 20
        if scenario == 'junk':
            names[len(names) - 1] = 'Bones'
        self.items = [PackItem(self, slot, name) for slot, name in enumerate(names)]
        self.interactions = []
        self.tree = Fake(id=1292, name='Dramen tree', actions=lambda: ['Chop down'], distance=lambda: 1, interact=self.chop)

    def chop(self, op):
        self.interactions.append(op)
        self.items.append(PackItem(self, 27, 'Dramen branch'))
        return True

    def count(self, name):
        return len([item for item in self.items if item.name == name])


def walked(*args, **kwargs):
    return True
    yield


def branch_pack_scenario(scenario):
    def run():
        pack = BranchPack(scenario)
        spy_on(inventory, 'items', lambda: pack.items)
        spy_on(inventory, 'is_full', lambda: len(pack.items) >= 28)
        spy_on(inventory, 'count', pack.count)
        spy_on(locs, 'query', querying(lambda: [pack.tree]))
        spy_on(traversal, 'walk_resilient', walked)
        patch(execution, 'delay_until', instant_until)
        names = [item.name for item in pack.items]
        step = decide(snap(Record({'stage': 3, 'tile': DUNGEON, 'inv': names, 'worn': ['Iron axe'], 'free_slots': 0})))
        expect(step.kind).to_be('custom')
        done = yield from step.run(lambda *args: None)
        expect(done).to_be(scenario != 'pending')
        expect(pack.interactions).to_equal(['Eat Lobster'] if scenario == 'pending' else ['Drop Bones' if scenario == 'junk' else 'Eat Lobster', 'Chop down'])
        expect([item.name for item in pack.items if item.name.endswith('rune')]).to_equal(['Air rune', 'Mind rune', 'Fire rune'])
        expect(pack.count('Dramen branch')).to_be(4 if scenario == 'pending' else 5)
    return run


for scenario in ['food', 'junk', 'pending']:
    test(f'full branch pack frees a slot through {scenario}', branch_pack_scenario(scenario))
