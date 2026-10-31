"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/scorpcatcher.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.barcrawl.barcrawl_logic import BARCRAWL_GP
from rs2004.quests.defs.scorpcatcher import decide, scorpcatcher
from rs2004.quests.defs.scorpcatcher.areas import ANTIPOISON_DOSES, ANTIPOISON_GP, CAGE_ID, SC_STAGE
from rs2004.quests.engine.types import QuestSnapshot
from rs2004.quests.engine.types import QuestProgress

def id_counts(ids):
    out = {}
    for id in ids:
        _v1 = out.get(id)
        out[id] = ((_v1 if _v1 is not None else 0)) + 1
    return out


def snap(options=None):
    if options is None:
        options = Record({})
    return QuestSnapshot(**{
        'journal': (options.journal if options.journal is not None else 'in_progress'),
        'inv': {},
        'inv_ids': id_counts((options.inv_ids if options.inv_ids is not None else [])),
        'worn': set(),
        'worn_ids': set(),
        'no_progress': 0,
        'bank_coins': 5000,
        'progress': (None if options.no_progress else QuestProgress((options.stage if options.stage is not None else SC_STAGE.FIRST_HINT), set())),
        'bank': {},
        'bank_ids': id_counts((options.bank_ids if options.bank_ids is not None else [])),
        'bank_known': (options.bank_known if options.bank_known is not None else True),
        'free_slots': 20,
    })


def talk_target(step):
    return (step.stop.npc if step.kind == 'talk' else f'({step.kind})')


def _fn2():
    def _fn3():
        expect(decide(snap(Record({'journal': 'complete'}))).kind).to_be('done')
    test('a green journal is done', _fn3)

    def _fn4():
        expect(decide(snap(Record({'journal': 'unknown'}))).kind).to_be('wait')
    test('an unloaded journal waits', _fn4)

    def _fn5():
        expect(talk_target(decide(snap(Record({'journal': 'not_started'}))))).to_be('Thormac')
    test('an unstarted quest walks to Thormac', _fn5)

    def _fn6():
        expect(decide(snap(Record({'bank_known': False}))).kind).to_be('scan_bank')
    test('an unread bank is scanned before the cage is called lost', _fn6)

    # Why: the engine banks spillover on the first pass of every quest, and a cage left in the bank is the caught scorpions left in the bank with it.
    def _fn7():
        step = decide(snap(Record({'bank_ids': [CAGE_ID.AB]})))
        expect(step.kind).to_be('withdraw')
        expect(step.kind == 'withdraw' and (step.items[0]['id'] if step.items[0] is not None else None)).to_be(CAGE_ID.AB)
    test('a banked cage is withdrawn by its exact id', _fn7)

    def _fn8():
        expect(talk_target(decide(snap()))).to_be('Thormac')
    test('no cage anywhere goes back to Thormac for another', _fn8)

    def _fn9():
        expect(talk_target(decide(snap(Record({'inv_ids': [CAGE_ID.FULL], 'stage': SC_STAGE.SECOND_HINT}))))).to_be('Thormac')
    test('a full cage is handed in to Thormac', _fn9)

    # Why: the Seer's own leg drives the conversation, because `seer_looking_glass` shuts the chat and spends three `p_delay(3)` lines before reopening it.
    def _fn10():
        step = decide(snap(Record({'inv_ids': [CAGE_ID.EMPTY], 'stage': SC_STAGE.STARTED})))
        expect(step.kind).to_be('custom')
        expect(step.kind == 'custom' and step.name).to_contain('Seer')
    test('an empty cage before the first hint walks to the Seer', _fn10)

    def _fn11():
        expect(decide(snap(Record({'inv_ids': [CAGE_ID.EMPTY], 'no_progress': True}))).kind).to_be('wait')
    test('a missing journal stage waits rather than guessing', _fn11)

    def _fn12():
        step = decide(snap(Record({'inv_ids': [CAGE_ID.EMPTY]})))
        expect(step.kind).to_be('custom')
        expect(step.kind == 'custom' and step.name).to_contain('Barbarian Outpost')
    test('an empty cage after the first hint catches the outpost scorpion first', _fn12)

    def _fn13():
        step = decide(snap(Record({'inv_ids': [CAGE_ID.B]})))
        expect(step.kind == 'custom' and step.name).to_contain('Taverley')
    test('a cage holding the outpost scorpion moves on to Taverley', _fn13)

    def _fn14():
        step = decide(snap(Record({'inv_ids': [CAGE_ID.AB], 'stage': SC_STAGE.SECOND_HINT})))
        expect(step.kind == 'custom' and step.name).to_contain('monastery')
    test('a cage holding two moves on to the monastery', _fn14)

    # Why: a run that catches Taverley's scorpion first is legal, the cage's switch table takes them in any order, so the leg picker has to read the cage rather than a counter.
    def _fn15():
        step = decide(snap(Record({'inv_ids': [CAGE_ID.AC], 'stage': SC_STAGE.SECOND_HINT})))
        expect(step.kind == 'custom' and step.name).to_contain('Barbarian Outpost')
    test('a cage holding Taverley and the monastery goes back for the outpost', _fn15)


describe('Scorpion Catcher decide', _fn2)


def _fn16():
    def _fn17():
        expect(scorpcatcher.record.id).to_be('scorpcatcher')
        expect(scorpcatcher.record.name).to_be('Scorpion Catcher')
    test('it is the scorpcatcher record', _fn17)

    # Why: the engine banks everything outside this list before the first step, and a deposited cage takes the caught scorpions with it.
    def _fn18():
        tools = [t.lower() for t in ((scorpcatcher.tools if scorpcatcher.tools is not None else []))]
        expect(tools).to_contain('scorpion cage')
        expect(tools).to_contain('dusty key')
        expect(tools).to_contain('jail key')
    test('the cage and both keys survive the spillover deposit', _fn18)

    def _fn19():
        expect((scorpcatcher.food if scorpcatcher.food is not None else 0)).to_be_greater_than(0)
    test('it carries food for the dragons between the gate and the coffins', _fn19)

    # Why: a drink turns (3) into (2), so a keep-list naming only the bought dose banks the rest of the potion on the next spillover.
    def _fn20():
        tools = [t.lower() for t in ((scorpcatcher.tools if scorpcatcher.tools is not None else []))]
        for dose in ANTIPOISON_DOSES:
            expect(tools).to_contain(dose.lower())
    test('every antipoison dose survives the spillover deposit', _fn20)

    def _fn21():
        expect((scorpcatcher.coin_float if scorpcatcher.coin_float is not None else 0)).to_be_greater_than_or_equal(BARCRAWL_GP + ANTIPOISON_GP)
    test('the coin float covers the barcrawl and the Karamja trip together', _fn21)


describe('Scorpion Catcher module', _fn16)
