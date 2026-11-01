"""Ported from rs2b0t's test/api/ai/quests/regicidePack.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestProgress, QuestSnapshot
from rs2004.quests.defs.regicide.areas import RG_ITEM
from rs2004.quests.defs.regicide.pack import manage_pack

def counts(stacks):
    return {_k: _v for _k, _v in stacks}


def snapshot(over=None):
    if over is None:
        over = Record({})
    carried = over.carried if over.carried is not None else []
    banked = over.banked if over.banked is not None else []
    free_slots = over.free_slots if over.free_slots is not None else 28
    bank_known = over.bank_known if over.bank_known is not None else True
    used = sum([q for _1, q in carried])
    _merged2 = {}
    for _k, _v in {
        'journal': 'in_progress',
        'inv': {},
        'inv_ids': counts(carried),
        'worn': set(),
        'worn_ids': set(),
        'no_progress': 0,
        'bank_coins': 1000000,
        'bank': {},
        'bank_ids': counts(banked),
        'bank_known': bank_known,
        'free_slots': (over.free_slots if over.free_slots is not None else 28 - used),
        'tile': Record({'x': 2655, 'z': 3283, 'level': 0}),
    }.items():
        _merged2[_k] = _v
    return QuestSnapshot(**_merged2)


PLAN = Record({
    'what': 'the coal run',
    'allow': [RG_ITEM.BARREL_TAR.id, RG_ITEM.PICKAXE.id, RG_ITEM.COAL.id],
    'caps': [Record({'item': RG_ITEM.SHARK, 'qty': 4})],
    'free_needed': 12,
})


def _fn3():
    def _fn4():
        step = manage_pack(snapshot(Record({'bank_known': False})), PLAN)
        expect((step.kind if step is not None else None)).to_be('scan_bank')
    test('an unread bank is scanned before anything is moved', _fn4)

    # Why: the forest kit does not belong on the coal run.
    def _fn5():
        step = manage_pack(snapshot(Record({'carried': [[RG_ITEM.SPADE.id, 1], [RG_ITEM.BARREL_TAR.id, 1]]})), PLAN)
        expect((step.kind if step is not None else None)).to_be('deposit')
        expect((step.kind if step is not None else None) == 'deposit' and step.keep_ids).to_contain(RG_ITEM.BARREL_TAR.id)
        expect((step.kind if step is not None else None) == 'deposit' and step.keep_ids).not_.to_contain(RG_ITEM.SPADE.id)
    test('anything the leg has no use for is banked', _fn5)

    # Why: deposits are all-or-nothing, so shed surplus and redraw the target count.
    def _fn6():
        step = manage_pack(snapshot(Record({'carried': [[RG_ITEM.SHARK.id, 11]]})), PLAN)
        expect((step.kind if step is not None else None)).to_be('deposit')
        expect((step.kind if step is not None else None) == 'deposit' and step.keep_ids).not_.to_contain(RG_ITEM.SHARK.id)
    test('an item over its cap is left out of the keep list entirely', _fn6)

    def _fn7():
        step = manage_pack(snapshot(Record({'carried': [], 'banked': [[RG_ITEM.SHARK.id, 40]]})), PLAN)
        expect((step.kind if step is not None else None)).to_be('withdraw')
        expect((step.kind if step is not None else None) == 'withdraw' and step.items[0]['qty']).to_be(4)
    test('an item under its cap is drawn back to it', _fn7)

    def _fn8():
        expect(manage_pack(snapshot(Record({'carried': [], 'banked': []})), PLAN)).to_be_null()
    test('a bank with none of it does not stall the leg', _fn8)

    def _fn9():
        snap = snapshot(Record({'carried': [[RG_ITEM.BARREL_TAR.id, 1], [RG_ITEM.PICKAXE.id, 1], [RG_ITEM.SHARK.id, 4]]}))
        expect(manage_pack(snap, PLAN)).to_be_null()
    test('a pack already in shape asks for nothing', _fn9)

    # Why: the plan must settle after shed, draw, and done.
    def _fn10():
        carried = [[RG_ITEM.SPADE.id, 1], [RG_ITEM.SHARK.id, 11], [RG_ITEM.BARREL_TAR.id, 1]]
        banked = [[RG_ITEM.SHARK.id, 40]]
        kinds = []
        for cycle in range(4):
            step = manage_pack(snapshot(Record({'carried': carried, 'banked': banked})), PLAN)
            if step is None:
                kinds.append('settled')
                break
            kinds.append(step.kind)
            if step.kind == 'deposit':
                keep = set((step.keep_ids if step.keep_ids is not None else []))
                carried = [(id, _2) for id, _2 in carried if (id in keep)]
            if step.kind == 'withdraw':
                carried = list(carried) + [[RG_ITEM.SHARK.id, step.items[0]['qty']]]
        expect(kinds).to_equal(['deposit', 'withdraw', 'settled'])
    test('shedding a surplus and drawing it back settles', _fn10)

    def _fn12():
        snap = snapshot(Record({'carried': [[RG_ITEM.COAL.id, 20]], 'free_slots': 2}))
        step = manage_pack(snap, PLAN)
        expect((step.kind if step is not None else None)).to_be('wait')
        expect((step.kind if step is not None else None) == 'wait' and step.reason).to_contain('12 free slot')
    test('a pack that cannot make room says so rather than retrying', _fn12)


describe('regicide pack planning', _fn3)


# Why: plans are whitelists, so keep costly quest items unless a leg spends them.
def _fn13():
    BARE = Record({'what': 'a plan that names nothing', 'allow': []})
    COSTLY = [
        ["Iorwerth's letter", RG_ITEM.MESSAGE],
        ['the crystal pendant', RG_ITEM.PENDANT],
        ['an empty barrel', RG_ITEM.BARREL],
        ['a barrel of coal-tar', RG_ITEM.BARREL_TAR],
        ['a barrel of naphtha', RG_ITEM.BARREL_NAPHTHA],
        ['a sealed barrel bomb', RG_ITEM.BARREL_LID],
        ['a fused barrel bomb', RG_ITEM.BARREL_FUSED],
        ['the fuse cloth', RG_ITEM.CLOTH],
    ]

    def _fn14(_what, item):
        expect(manage_pack(snapshot(Record({'carried': [[item.id, 1]]})), BARE)).to_be_null()
    test_each(COSTLY)('%s survives a plan that does not name it', _fn14)

    # Why: the messenger scroll is never read after it advances `%regicide_quest`.
    def _fn15():
        step = manage_pack(snapshot(Record({'carried': [[RG_ITEM.SUMMONS.id, 1]]})), BARE)
        expect((step.kind if step is not None else None)).to_be('deposit')
        expect((step.kind if step is not None else None) == 'deposit' and step.keep_ids).not_.to_contain(RG_ITEM.SUMMONS.id)
    test("the King's message is banked by a plan that does not name it", _fn15)

    def _fn16():
        snap = snapshot(Record({'carried': [[RG_ITEM.BARREL_FUSED.id, 1], [RG_ITEM.SPADE.id, 1]]}))
        step = manage_pack(snap, Record({'what': 'the coal run', 'allow': [RG_ITEM.COAL.id]}))
        expect((step.kind if step is not None else None)).to_be('deposit')
        expect((step.kind if step is not None else None) == 'deposit' and step.keep_ids).to_contain(RG_ITEM.BARREL_FUSED.id)
        expect((step.kind if step is not None else None) == 'deposit' and step.keep_ids).not_.to_contain(RG_ITEM.SPADE.id)
    test('a bomb is kept even while junk is being shed', _fn16)


describe('what a plan keeps without being asked', _fn13)


# Why: release the scroll slot after King Lathas consumes it.
def _fn17():
    def _fn18():
        snap = snapshot(Record({'carried': [[RG_ITEM.MESSAGE.id, 1], [RG_ITEM.SHARK.id, 1]]}))
        step = manage_pack(snap, Record({'what': 'after the king', 'allow': [RG_ITEM.SHARK.id], 'shed': [RG_ITEM.MESSAGE.id]}))
        expect((step.kind if step is not None else None)).to_be('deposit')
        expect((step.kind if step is not None else None) == 'deposit' and step.keep_ids).not_.to_contain(RG_ITEM.MESSAGE.id)
    test('a plan that sheds the letter banks it', _fn18)

    def _fn19():
        snap = snapshot(Record({'carried': [[RG_ITEM.MESSAGE.id, 1]]}))
        expect(manage_pack(snap, Record({'what': 'before the king', 'allow': []}))).to_be_null()
    test('a plan that does not shed it keeps it', _fn19)


describe('shedding what a leg is finished with', _fn17)


# Why: the catapult silently requires both the rabbit and the guard-set flag.
def _fn20():
    def _fn21(_what, item):
        expect(manage_pack(snapshot(Record({'carried': [[item.id, 1]]})), Record({'what': 'the walk back', 'allow': []}))).to_be_null()
    test_each([['raw', RG_ITEM.RAW_RABBIT], ['cooked', RG_ITEM.COOKED_RABBIT]])('a %s rabbit survives a plan that does not name it', _fn21)


describe('the rabbit is the catapult gate, not food', _fn20)

