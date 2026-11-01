"""Ported from rs2b0t's test/api/ai/quests/defs/elementalworkshop.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestProgress, QuestSnapshot
from rs2004.quests.defs.elementalworkshop import COAL_NEED, EW_FLAG, EW_ITEM, EW_STAGE, decide, elementalworkshop, ew_area, has_held_slash_tool, has_slash_tool, has_weapon, parse_elemental_workshop_journal, surface_loadout

SEERS = Record({'x': 2725, 'z': 3491, 'level': 0})
WORKSHOP = Record({'x': 2716, 'z': 9888, 'level': 0})
BRONZE_PICK = 1265
STEEL_SCIM = 1325


def inv_ids(*entries):
    return {_k: _v for _k, _v in entries}


def inv_names(*names):
    map = {}
    for name in names:
        key = name.lower()
        _v1 = map.get(key)
        map[key] = ((_v1 if _v1 is not None else 0)) + 1
    return map


def progress(stage, flags=None):
    if flags is None:
        flags = []
    return QuestProgress(stage, set(flags))


def snap(options=None):
    if options is None:
        options = Record({})
    stage = (options.stage if options.stage is not None else EW_STAGE.NOT_STARTED)
    return QuestSnapshot(**{
        'journal': (options.journal if options.journal is not None else (('not_started' if stage == EW_STAGE.NOT_STARTED else 'in_progress'))),
        'inv': inv_names(*((options.inv if options.inv is not None else []))),
        'inv_ids': inv_ids(*((options.inv_ids if options.inv_ids is not None else []))),
        'worn': set([n.lower() for n in ((options.worn if options.worn is not None else []))]),
        'worn_ids': set((options.worn_ids if options.worn_ids is not None else [])),
        'no_progress': 0,
        'bank_coins': 2000000,
        'stage': stage,
        'progress': progress(stage, (options.flags if options.flags is not None else [])),
        'bank': {_k: _v for _k, _v in [[n.lower(), q] for n, q in ((options.bank if options.bank is not None else []))]},
        'bank_ids': inv_ids(*((options.bank_ids if options.bank_ids is not None else []))),
        'bank_known': (options.bank_known if options.bank_known is not None else True),
        'tile': (SEERS if options.tile is None else options.tile),
        'attack': (options.attack if options.attack is not None else 60),
        'free_slots': (options.free_slots if options.free_slots is not None else 20),
    })


def realistic_bank():
    """Full bank kit for a realistic low-level EW account (tools not held)."""
    return Record({
        'bank_ids': [
        [EW_ITEM.KNIFE.id, 1],
        [EW_ITEM.HAMMER.id, 1],
        [BRONZE_PICK, 1],
        [EW_ITEM.THREAD.id, 2],
        [EW_ITEM.LEATHER.id, 1],
        [EW_ITEM.NEEDLE.id, 1],
        [EW_ITEM.COAL.id, 8],
        [STEEL_SCIM, 1],
        [EW_ITEM.COINS.id, 50000],
    ],
        'bank': [
        ['knife', 1],
        ['hammer', 1],
        ['bronze pickaxe', 1],
        ['thread', 2],
        ['leather', 1],
        ['needle', 1],
        ['coal', 8],
        ['lobster', 20],
        ['steel scimitar', 1],
        ['coins', 50000],
    ],
    })


def custom_name(step):
    return (step.name if step.kind == 'custom' else None)


def _fn3():
    def _fn4():
        expect((parse_elemental_workshop_journal('@dbl@I can start this quest by reading a|@dre@book@dbl@ found in @dre@Seers village@dbl@.').stage if parse_elemental_workshop_journal('@dbl@I can start this quest by reading a|@dre@book@dbl@ found in @dre@Seers village@dbl@.') is not None else None)).to_be(EW_STAGE.NOT_STARTED)
    test('maps not-started journal text', _fn4)

    def _fn5():
        expect((parse_elemental_workshop_journal('@str@I have found a battered book in a house in Seers Village.|@str@It tells of magic ore and a workshop created to fashion it.||@dbl@Where is this workshop and how do I get in?').stage if parse_elemental_workshop_journal('@str@I have found a battered book in a house in Seers Village.|@str@It tells of magic ore and a workshop created to fashion it.||@dbl@Where is this workshop and how do I get in?') is not None else None)).to_be(EW_STAGE.READ_BOOK)
    test('maps read-book journal text', _fn5)

    def _fn6():
        expect((parse_elemental_workshop_journal('@str@I have found a battered book in a house in Seers Village.|@str@Cutting open the spine of the book with a blade,|@str@I found a key hidden under the leather binding.||@dbl@Where is this workshop and how do I get in?').stage if parse_elemental_workshop_journal('@str@I have found a battered book in a house in Seers Village.|@str@Cutting open the spine of the book with a blade,|@str@I found a key hidden under the leather binding.||@dbl@Where is this workshop and how do I get in?') is not None else None)).to_be(EW_STAGE.SLASHED)
    test('maps slashed-book journal text', _fn6)

    def _fn7():
        expect((parse_elemental_workshop_journal('@str@I have found a secret door in the Seers Village smithy.||@str@Where is this workshop and how do I get in?||@dbl@There is obviously lots to do here.').stage if parse_elemental_workshop_journal('@str@I have found a secret door in the Seers Village smithy.||@str@Where is this workshop and how do I get in?||@dbl@There is obviously lots to do here.') is not None else None)).to_be(EW_STAGE.ENTERED)
    test('maps entered-workshop journal text', _fn7)

    def _fn8():
        expect((parse_elemental_workshop_journal('@red@QUEST COMPLETE!').stage if parse_elemental_workshop_journal('@red@QUEST COMPLETE!') is not None else None)).to_be(EW_STAGE.COMPLETE)
    test('maps quest complete journal text', _fn8)

    def _fn9():
        text = '|'.join([
        'I have found a secret door in the Seers Village smithy.',
        'I managed to get the waterwheel in the northern water area going by turning some valves and pulling a lever.',
        'The bellows in the eastern air area are now fixed, I just needed to stitch some leather over that hole.',
        'I lit the furnace with lava taken from the trough, using the stone bowl I found.',
        'I have made a bar from the elemental ore.',
        'Now I just need to make something from it.',
    ])
        p = parse_elemental_workshop_journal(text)
        expect((p.stage if p is not None else None)).to_be(EW_STAGE.ENTERED)
        expect((EW_FLAG.WATER in (p.flags if p is not None else None))).to_be(True)
        expect((EW_FLAG.BELLOWS in (p.flags if p is not None else None))).to_be(True)
        expect((EW_FLAG.FURNACE in (p.flags if p is not None else None))).to_be(True)
        expect((EW_FLAG.MADE_BAR in (p.flags if p is not None else None))).to_be(True)
    test('parses machinery flags while inside the entered branch', _fn9)

    def _fn10():
        expect(parse_elemental_workshop_journal(['Elemental Workshop', 'Loading…'])).to_be_undefined()
    test('does not invent a stage from unrecognized text', _fn10)


describe('Elemental Workshop journal parsing', _fn3)


def _fn11():
    def _fn12():
        expect(ew_area(SEERS)).to_be('seers')
        expect(ew_area(WORKSHOP)).to_be('workshop')
        expect(ew_area(Record({'x': 3200, 'z': 3200, 'level': 0}))).to_be('elsewhere')
        expect(ew_area(None)).to_be('unknown')
    test('classifies seers, workshop, and unknown tiles', _fn12)


describe('Elemental Workshop area classification', _fn11)


def _fn13():
    def _fn14():
        expect(elementalworkshop.record.id).to_be('elemental_workshop')
        expect(elementalworkshop.owns_inventory).to_be(True)
    test('module is registered with the AIO record', _fn14)

    def _fn15():
        expect(decide(snap(Record({'journal': 'complete', 'stage': EW_STAGE.COMPLETE}))).kind).to_be('done')
        expect(decide(snap(Record({'journal': 'unknown'}))).kind).to_be('wait')
    test('complete and unknown short-circuit', _fn15)

    def _fn16():
        expect(custom_name(decide(snap(Record({'stage': EW_STAGE.NOT_STARTED}))))).to_be('search Seers bookcase for the Battered book')
    test('not started searches the bookcase when the book is missing', _fn16)

    def _fn17():
        expect(custom_name(decide(snap(Record({'stage': EW_STAGE.NOT_STARTED, 'inv_ids': [[EW_ITEM.BATTERED_BOOK.id, 1]]}))))).to_be('read the Battered book')
    test('not started reads a held battered book', _fn17)

    def _fn18():
        need_knife = decide(snap(Record({'stage': EW_STAGE.READ_BOOK, 'inv_ids': [[EW_ITEM.BATTERED_BOOK.id, 1]]})))
        expect(need_knife.kind == 'grab_ground' or need_knife.kind == 'withdraw' or need_knife.kind == 'wait').to_be(True)
        expect(custom_name(decide(snap(Record({'stage': EW_STAGE.READ_BOOK, 'inv_ids': [[EW_ITEM.BATTERED_BOOK.id, 1], [EW_ITEM.KNIFE.id, 1]]}))))).to_be('slash the Battered book for the key')
    test('after reading, sources a knife then slashes the book', _fn18)

    def _fn19():
        kit = realistic_bank()
        step = decide(snap(Record({
        'stage': EW_STAGE.SLASHED,
        'inv_ids': [[EW_ITEM.BATTERED_KEY.id, 1], [EW_ITEM.BATTERED_BOOK.id, 1]],
        'bank_ids': kit.bank_ids,
        'bank': kit.bank,
    })))
        # Hammer/thread/coal/pickaxe/food/weapon withdrawals come before enter.
        expect(step.kind).to_be('withdraw')
    test('with key, provisions tools from the bank before entering', _fn19)

    def _fn20():
        step = decide(snap(Record({
        'stage': EW_STAGE.SLASHED,
        'inv_ids': [[EW_ITEM.BATTERED_KEY.id, 1], [EW_ITEM.BATTERED_BOOK.id, 1]],
        'bank_known': False,
    })))
        expect(step.kind).to_be('scan_bank')
    test('empty pack + bank kit scans bank when bank is unknown', _fn20)

    def _fn21():
        step = decide(snap(Record({
        'stage': EW_STAGE.SLASHED,
        'inv_ids': [
        [EW_ITEM.BATTERED_KEY.id, 1],
        [EW_ITEM.BATTERED_BOOK.id, 1],
        [EW_ITEM.KNIFE.id, 1],
        [EW_ITEM.HAMMER.id, 1],
        [EW_ITEM.THREAD.id, 1],
        [EW_ITEM.COAL.id, COAL_NEED],
        [STEEL_SCIM, 1],
    ],
        'bank_known': True,
        'bank_ids': [],
        'bank': [],
    })))
        expect(step.kind).to_be('wait')
        expect('pickaxe' in step.reason.lower()).to_be(True)
    test('waits when bank is known empty of a pickaxe', _fn21)

    def _fn22():
        # Journal already entered: odd wall Push works without the Battered key.
        step = decide(snap(Record({
        'stage': EW_STAGE.ENTERED,
        'flags': [],
        'inv_ids': [
        [EW_ITEM.BATTERED_BOOK.id, 1],
        [EW_ITEM.KNIFE.id, 1],
        [EW_ITEM.HAMMER.id, 1],
        [EW_ITEM.THREAD.id, 1],
        [EW_ITEM.LEATHER.id, 1],
        [EW_ITEM.NEEDLE.id, 1],
        [EW_ITEM.COAL.id, COAL_NEED],
        [BRONZE_PICK, 1],
        [STEEL_SCIM, 1],
    ],
        'inv': ['lobster', 'lobster', 'lobster'],
        'bank_known': True,
        'bank_ids': [],
        'bank': [],
    })))
        expect(custom_name(step)).to_be('enter the Elemental Workshop')
    test('after death (ENTERED, no key on surface) still re-enters via Push when loadout is ready', _fn22)

    def _fn23():
        # Journal can already be SLASHED while the key was lost before first entry,
        # re-cut the spine rather than hard-wait (Push only works after ENTERED).
        step = decide(snap(Record({
        'stage': EW_STAGE.SLASHED,
        'inv_ids': [[EW_ITEM.BATTERED_BOOK.id, 1], [EW_ITEM.KNIFE.id, 1]],
        'bank_known': True,
        'bank_ids': [],
        'bank': [],
    })))
        expect(custom_name(step)).to_be('slash the Battered book for the key')
    test('before ENTERED, missing key re-slashes the book when a knife is held', _fn23)

    def _fn24():
        step = decide(snap(Record({
        'stage': EW_STAGE.READ_BOOK,
        'inv_ids': [[EW_ITEM.BATTERED_BOOK.id, 1]],
        'bank_ids': [[STEEL_SCIM, 1]],
        'bank': [['steel scimitar', 1]],
    })))
        expect(step.kind).to_be('withdraw')
        if step.kind == 'withdraw':
            expect(any([i.get('id') == STEEL_SCIM or ('scimitar' in i['name'].lower()) for i in step.items])).to_be(True)
    test('after reading, withdraws steel scimitar from bank when knife is missing', _fn24)

    def _fn25():
        expect(custom_name(decide(snap(Record({
        'stage': EW_STAGE.ENTERED,
        'flags': [],
        'tile': WORKSHOP,
        'inv_ids': [
        [EW_ITEM.BATTERED_KEY.id, 1],
        [EW_ITEM.BATTERED_BOOK.id, 1],
        [EW_ITEM.HAMMER.id, 1],
        [EW_ITEM.COAL.id, 4],
        [1265, 1],
    ],
    }))))).to_be('start the water wheel')
    test('inside workshop without water flag starts the water wheel', _fn25)

    def _fn26():
        expect(custom_name(decide(snap(Record({
        'stage': EW_STAGE.ENTERED,
        'flags': [EW_FLAG.WATER],
        'tile': WORKSHOP,
        'inv_ids': [[EW_ITEM.THREAD.id, 1]],
    }))))).to_be('search crates for leather/needle')
    test('after water, searches crates when leather/needle are missing for bellows', _fn26)

    def _fn27():
        expect(custom_name(decide(snap(Record({
        'stage': EW_STAGE.ENTERED,
        'flags': [EW_FLAG.WATER],
        'tile': WORKSHOP,
        'inv_ids': [[EW_ITEM.LEATHER.id, 1], [EW_ITEM.NEEDLE.id, 1], [EW_ITEM.THREAD.id, 1]],
    }))))).to_be('fix the bellows')
    test('fixes bellows when leather, needle, and thread are held', _fn27)

    def _fn28():
        expect(custom_name(decide(snap(Record({
        'stage': EW_STAGE.ENTERED,
        'flags': [EW_FLAG.WATER, EW_FLAG.BELLOWS],
        'tile': WORKSHOP,
        'inv_ids': [[EW_ITEM.STONE_BOWL.id, 1]],
    }))))).to_be('light the furnace with lava')
    test('lights the furnace after bellows when a bowl is held', _fn28)

    def _fn29():
        expect(custom_name(decide(snap(Record({
        'stage': EW_STAGE.ENTERED,
        'flags': [EW_FLAG.WATER, EW_FLAG.BELLOWS, EW_FLAG.FURNACE],
        'tile': WORKSHOP,
        'inv_ids': [[1265, 1], [EW_ITEM.COAL.id, 4]],
    }))))).to_be('mine Elemental ore from the Earth elemental')
    test('mines ore once the furnace is lit', _fn29)

    def _fn30():
        expect(custom_name(decide(snap(Record({
        'stage': EW_STAGE.ENTERED,
        'flags': [EW_FLAG.WATER, EW_FLAG.BELLOWS, EW_FLAG.FURNACE],
        'tile': WORKSHOP,
        'inv_ids': [[EW_ITEM.ELEMENTAL_ORE.id, 1], [EW_ITEM.COAL.id, 4]],
    }))))).to_be('smelt Elemental metal at the furnace')
    test('smelts once ore and coal are held', _fn30)

    def _fn31():
        expect(custom_name(decide(snap(Record({
        'stage': EW_STAGE.ENTERED,
        'flags': [EW_FLAG.WATER, EW_FLAG.BELLOWS, EW_FLAG.FURNACE],
        'tile': WORKSHOP,
        'inv_ids': [[EW_ITEM.ELEMENTAL_METAL.id, 1], [EW_ITEM.BATTERED_BOOK.id, 1], [EW_ITEM.HAMMER.id, 1]],
    }))))).to_be('smith the Elemental shield')
    test('smiths the shield when elemental metal is held with book and hammer', _fn31)

    def _fn32():
        expect(EW_ITEM.STONE_BOWL.name).to_be(EW_ITEM.STONE_BOWL_FULL.name)
        expect(EW_ITEM.STONE_BOWL.id).not_.to_be(EW_ITEM.STONE_BOWL_FULL.id)
    test('empty and full stone bowls share a display name, so ids must differ', _fn32)


describe('Elemental Workshop decide()', _fn13)


def _fn33():
    def _fn34():
        s = snap(Record({'inv_ids': [[EW_ITEM.KNIFE.id, 1]], 'inv': ['Knife']}))
        expect(has_held_slash_tool(s)).to_be(True)
        expect(has_slash_tool(s)).to_be(True)
        expect(has_weapon(s)).to_be(False)
    test('knife counts as slash tool but not as combat weapon', _fn34)

    def _fn35():
        s = snap(Record({'worn': ['Steel scimitar'], 'worn_ids': [STEEL_SCIM]}))
        expect(has_held_slash_tool(s)).to_be(False)
        expect(has_slash_tool(s)).to_be(True)
        expect(has_weapon(s)).to_be(True)
    test('worn scimitar counts as slash/weapon but not held slash for book useOn', _fn35)

    def _fn36():
        kit = realistic_bank()
        step = surface_loadout(snap(Record({
        'stage': EW_STAGE.SLASHED,
        'inv_ids': [[EW_ITEM.BATTERED_KEY.id, 1], [EW_ITEM.BATTERED_BOOK.id, 1]],
        'bank_ids': kit.bank_ids,
        'bank': kit.bank,
        'free_slots': 28,
    })), True, True)
        expect((step.kind if step is not None else None)).to_be('withdraw')
        if (step.kind if step is not None else None) == 'withdraw':
            names = [i['name'].lower() for i in step.items]
            expect(any([('hammer' in n) for n in names])).to_be(True)
            expect(any([('pickaxe' in n) for n in names])).to_be(True)
            expect(any([('coal' in n) for n in names])).to_be(True)
            expect(any([('lobster' in n) for n in names])).to_be(True)
            expect(any([('scimitar' in n) or n == 'knife' for n in names])).to_be(True)
    test('surfaceLoadout withdraws a full entry kit from a realistic bank seed', _fn36)

    def _fn37():
        kit = realistic_bank()
        step = surface_loadout(snap(Record({
        'stage': EW_STAGE.SLASHED,
        'inv_ids': [[EW_ITEM.BATTERED_KEY.id, 1]],
        'inv': ['Bones', 'Bones', 'Bones'],
        'bank_ids': kit.bank_ids,
        'bank': kit.bank,
        'free_slots': 2,
    })), True, True)
        expect((step.kind if step is not None else None)).to_be('deposit')
    test('surfaceLoadout deposits junk when free slots cannot fit the kit', _fn37)


describe('Elemental Workshop supplies helpers', _fn33)
