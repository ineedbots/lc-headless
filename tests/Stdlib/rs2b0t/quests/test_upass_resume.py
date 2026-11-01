"""Ported from rs2b0t's test/api/ai/quests/upassResume.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestProgress, QuestSnapshot
from rs2004.quests.defs.upass import decide
from rs2004.quests.defs.upass.areas import UP_ITEM
from rs2004.quests.defs.upass.journal import UP_FLAG, UP_STAGE

# Why: sweep every reachable stage and pocket because `decide()` is pure over a snapshot.
def counts(stacks):
    return {_k: _v for _k, _v in [((s if isinstance(s, list) else [s, 1])) for s in stacks]}


KIT = [
    [UP_ITEM.ROPE.id, 3],
    UP_ITEM.SHORTBOW.id,
    [UP_ITEM.BRONZE_ARROW.id, 50],
    UP_ITEM.TINDERBOX.id,
    UP_ITEM.SPADE.id,
    UP_ITEM.BUCKET.id,
    [UP_ITEM.LOBSTER.id, 14],
]
WHERE = Record({
    'mainland': Record({'x': 2655, 'z': 3283, 'level': 0}),
    'westardougne': Record({'x': 2500, 'z': 3300, 'level': 0}),
    'area1': Record({'x': 2450, 'z': 9716, 'level': 0}),
    'area2': Record({'x': 2400, 'z': 9620, 'level': 0}),
    'gridpit': Record({'x': 2400, 'z': 9560, 'level': 0}),
    'main': Record({'x': 2173, 'z': 4725, 'level': 1}),
    'temple': Record({'x': 2161, 'z': 4642, 'level': 1}),
    'witch': Record({'x': 2136, 'z': 4579, 'level': 1}),
    'dwarves': Record({'x': 2323, 'z': 9804, 'level': 0}),
    'kalrag': Record({'x': 2356, 'z': 9911, 'level': 0}),
})


def snapshot(stage, flags, tile):
    carried = list(KIT)
    # Why: past the chest the doll is what every remaining step is keyed on, so a resume there holds one.
    if stage >= UP_STAGE.FOUND_DOLL and stage < UP_STAGE.DEFEATED_IBAN:
        carried.extend([UP_ITEM.DOLL.id, UP_ITEM.GAUNTLETS.id])
    return QuestSnapshot(**{
        'journal': 'in_progress',
        'inv': {},
        'inv_ids': counts(carried),
        'worn': set(['rune scimitar']),
        'worn_ids': set(),
        'no_progress': 0,
        'bank_coins': 0,
        'bank': {},
        'bank_ids': {},
        'bank_known': True,
        'stage': stage,
        'progress': QuestProgress(stage, set(flags)),
        'tile': tile,
    })


# Why: the pass is one-way, so only test stage and pocket pairs the quest can produce.
REACHABLE = {
    UP_STAGE.NOT_STARTED: ['mainland', 'westardougne'],
    UP_STAGE.SPOKEN_KOFTIK: ['mainland', 'westardougne', 'area1'],
    UP_STAGE.PASSED_BRIDGE: ['area1'],
    UP_STAGE.ENTERED_SECOND_AREA: ['area1', 'area2', 'gridpit'],
    UP_STAGE.KILLED_UNICORN: ['area2', 'gridpit'],
    UP_STAGE.ENTERED_MAIN_AREA: ['main', 'witch', 'temple', 'dwarves'],
    UP_STAGE.SPOKEN_NILHOOF: ['main', 'witch', 'temple', 'dwarves'],
    UP_STAGE.FOUND_DOLL: ['main', 'witch', 'temple', 'dwarves', 'kalrag'],
    UP_STAGE.CONFRONTED_IBAN: ['main', 'witch', 'temple', 'dwarves', 'kalrag'],
    UP_STAGE.DEFEATED_IBAN: ['area2', 'area1', 'westardougne', 'mainland'],
}
STAGES = [
    UP_STAGE.NOT_STARTED,
    UP_STAGE.SPOKEN_KOFTIK,
    UP_STAGE.PASSED_BRIDGE,
    UP_STAGE.ENTERED_SECOND_AREA,
    UP_STAGE.KILLED_UNICORN,
    UP_STAGE.ENTERED_MAIN_AREA,
    UP_STAGE.SPOKEN_NILHOOF,
    UP_STAGE.FOUND_DOLL,
    UP_STAGE.CONFRONTED_IBAN,
    UP_STAGE.DEFEATED_IBAN,
]
DOLL_FLAGS = [UP_FLAG.ASHES_ON_DOLL, UP_FLAG.BLOOD_ON_DOLL, UP_FLAG.DOVE_ON_DOLL, UP_FLAG.SHADOW_ON_DOLL]


def doll_states():
    """Every element subset plus the completed journal line."""
    out = []
    for mask in range(16):
        flags = [flag for bit, flag in enumerate(DOLL_FLAGS) if (mask & (1 << bit)) != 0]
        out.append((list(flags) + [UP_FLAG.DOLL_COMPLETE] if mask == 15 else flags))
    return out


# Why: only an unsafe pack or impossible position may stop a resumed run.
ALLOWED = ['not equipped for the pass', 'reached from mainland', 'reached from westardougne']


def kind_of(step):
    return (step).kind


def reason_of(step):
    return ((step).reason if (step).reason is not None else '')


def _fn1():
    def _fn2():
        parked = []
        for stage in STAGES:
            for name in REACHABLE[stage]:
                step = decide(snapshot(stage, [UP_FLAG.STARTED], WHERE.get(name)))
                if kind_of(step) == 'wait' and not any([ok in reason_of(step) for ok in ALLOWED]):
                    parked.append(f'stage {stage} in {name}: {reason_of(step)}')
        expect(parked).to_equal([])
    test('every stage in every pocket has something to do', _fn2)

    def _fn3():
        parked = []
        for flags in doll_states():
            for stage in [UP_STAGE.FOUND_DOLL, UP_STAGE.CONFRONTED_IBAN]:
                for name in REACHABLE[stage]:
                    step = decide(snapshot(stage, [UP_FLAG.STARTED] + list(flags), WHERE.get(name)))
                    if kind_of(step) == 'wait' and not any([ok in reason_of(step) for ok in ALLOWED]):
                        parked.append(f'{len(flags)} element(s) at stage {stage} in {name}: {reason_of(step)}')
        expect(parked).to_equal([])
    test('every combination of the four elements has a next step', _fn3)

    # Why: a complete doll means the robes and the temple, and the gear step has to stand down over that
    # stretch or it re-wears the armour the doors refuse, every tick, forever.
    def _fn4():
        for stage in [UP_STAGE.FOUND_DOLL, UP_STAGE.CONFRONTED_IBAN]:
            for name in REACHABLE[stage]:
                step = decide(snapshot(stage, [UP_FLAG.STARTED] + list(DOLL_FLAGS) + [UP_FLAG.DOLL_COMPLETE], WHERE.get(name)))
                _v5 = (step).name
                expect((_v5 if _v5 is not None else '').startswith('wear ')).to_be(False)
    test('a complete doll never asks for armour back until Iban is dead', _fn4)


describe('Underground Pass resumability', _fn1)

