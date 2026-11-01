"""Ported from rs2b0t's test/api/ai/quests/defs/digsite.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestProgress, QuestSnapshot
from rs2004.quests.defs.digsite import decide, digsite
from rs2004.quests.defs.digsite.areas import DIG_ID, DIG_TILE
from rs2004.quests.defs.digsite.journal import DIG_STAGE
from rs2004.quests.defs.digsite.supplies import digsite_state, reset_digsite_state
from rs2004.quests.defs import QUEST_DEFS

def ids(list_):
    out = {}
    for id in list_:
        _v1 = out.get(id)
        out[id] = ((_v1 if _v1 is not None else 0)) + 1
    return out


def snap(o=None):
    if o is None:
        o = Record({})
    return QuestSnapshot(**{
        'journal': (o.journal if o.journal is not None else 'in_progress'),
        'inv': {},
        'inv_ids': ids((o.inv_ids if o.inv_ids is not None else [])),
        'worn': set(),
        'worn_ids': set(),
        'no_progress': 0,
        'bank_coins': 0,
        'stage': o.stage,
        'progress': (None if o.stage is None else QuestProgress(o.stage, set((o.flags if o.flags is not None else [])))),
        'bank': {},
        'bank_ids': ids((o.bank_ids if o.bank_ids is not None else [])),
        'bank_known': (o.bank_known if o.bank_known is not None else True),
        'tile': ((o.tile if o.tile is not None else Record({'x': 3358, 'z': 3410, 'level': 0}))),
        'free_slots': 20,
    })


def label(step):
    return ((f'custom:{step.name}' if step.kind == 'custom' else step.kind))


WEST_SHAFT = Record({'x': 3353, 'z': 9818, 'level': 0})
EAST_SHAFT = Record({'x': 3370, 'z': 9828, 'level': 0})
ALTAR_CAVE = Record({'x': 3368, 'z': 9767, 'level': 0})
NITRATE_AND_NITRO = [DIG_ID.AMMONIUM_NITRATE, DIG_ID.NITROGLYCERIN, DIG_ID.ARCENIA_ROOT, DIG_ID.COINS]


def _fn2():
    reset_digsite_state()


before_each(_fn2)


def _fn3():
    def _fn4():
        expect(decide(snap(Record({'journal': 'complete'}))).kind).to_be('done')
    test('a complete journal is done', _fn4)

    def _fn5():
        expect(decide(snap(Record({'journal': 'unknown'}))).kind).to_be('wait')
    test('an unloaded journal waits rather than restarting the quest', _fn5)

    def _fn6():
        expect(decide(snap(Record({'stage': None}))).kind).to_be('wait')
    test('an unreadable stage waits', _fn6)

    def _fn7():
        step = decide(snap(Record({'stage': DIG_STAGE.FIRST_EXAM, 'bank_known': False})))
        expect(step.kind).to_be('scan_bank')
    test('an unread bank is read before anything else', _fn7)


describe('Digsite decide — gates', _fn3)


def _fn8():
    def _fn9():
        expect(label(decide(snap(Record({'stage': DIG_STAGE.NOT_STARTED, 'inv_ids': [DIG_ID.COINS]}))))).to_be('custom:ask the Examiner about the Earth Sciences exams')
    test('an unstarted quest opens with the Examiner', _fn9)

    def _fn10():
        expect(label(decide(snap(Record({'stage': DIG_STAGE.STAMPING, 'inv_ids': [DIG_ID.COINS, DIG_ID.PLAIN_LETTER]}))))).to_be('custom:have the Curator stamp the letter')
    test('an unstamped letter goes to the Curator', _fn10)

    def _fn11():
        expect(label(decide(snap(Record({'stage': DIG_STAGE.STAMPING, 'inv_ids': [DIG_ID.COINS, DIG_ID.STAMPED_LETTER]}))))).to_be('custom:hand the stamped letter to the Examiner')
    test('a stamped letter goes back to the Examiner', _fn11)

    def _fn12():
        step = decide(snap(Record({'stage': DIG_STAGE.STAMPING, 'inv_ids': [DIG_ID.COINS], 'bank_ids': [DIG_ID.STAMPED_LETTER]})))
        expect(step.kind).to_be('withdraw')
    test('a banked letter is withdrawn rather than asked for again', _fn12)

    def _fn13():
        expect(label(decide(snap(Record({'stage': DIG_STAGE.STAMPING, 'inv_ids': [DIG_ID.COINS]}))))).to_be('custom:ask the Examiner to replace the lost letter')
    test('no letter anywhere asks the Examiner for a replacement', _fn13)

    def _fn14():
        expect(label(decide(snap(Record({'stage': DIG_STAGE.FIRST_EXAM, 'inv_ids': [DIG_ID.COINS]}))))).to_be("custom:pickpocket the workmen for the green student's sample")
    test('the first exam starts by stealing the green sample', _fn14)

    def _fn15():
        expect(label(decide(snap(Record({'stage': DIG_STAGE.FIRST_EXAM, 'inv_ids': [DIG_ID.COINS, DIG_ID.ROCK_SAMPLE_GREEN]}))))).to_be("custom:return the green student's rock sample")
    test('a held green sample is delivered before anything else', _fn15)

    def _fn16():
        expect(label(decide(snap(Record({'stage': DIG_STAGE.FIRST_EXAM, 'flags': ['green-answered'], 'inv_ids': [DIG_ID.COINS]}))))).to_be("custom:search the bush for the purple student's sample")
    test('the purple errand is the bush', _fn16)

    def _fn17():
        expect(label(decide(snap(Record({'stage': DIG_STAGE.FIRST_EXAM, 'flags': ['green-answered', 'purple-answered'], 'inv_ids': [DIG_ID.COINS]}))))).to_be("custom:pan the river for the orange student's sample")
    test('the orange errand is the river', _fn17)

    def _fn18():
        expect(label(decide(snap(Record({'stage': DIG_STAGE.FIRST_EXAM, 'flags': ['exam-ready'], 'inv_ids': [DIG_ID.COINS]}))))).to_be('custom:sit the first Earth Sciences exam')
    test('all three answered sits the exam', _fn18)

    def _fn19():
        expect(label(decide(snap(Record({'stage': DIG_STAGE.SECOND_EXAM, 'inv_ids': [DIG_ID.COINS]}))))).to_be('custom:revise with the three students for exam 2')
    test('the second exam is three conversations', _fn19)

    def _fn20():
        expect(label(decide(snap(Record({'stage': DIG_STAGE.THIRD_EXAM, 'inv_ids': [DIG_ID.COINS]}))))).to_be('custom:pan the river for an opal')
    test('the third exam needs an opal before the students are worth talking to', _fn20)

    def _fn21():
        step = decide(snap(Record({'stage': DIG_STAGE.THIRD_EXAM, 'inv_ids': [DIG_ID.COINS, DIG_ID.UNCUT_OPAL, DIG_ID.CHISEL]})))
        expect(step.kind).to_be('use_on')
        expect(step.kind == 'use_on' and step.product).to_be('Opal')
    test('an uncut opal is cut before it is given away', _fn21)

    def _fn22():
        step = decide(snap(Record({'stage': DIG_STAGE.THIRD_EXAM, 'inv_ids': [DIG_ID.COINS, DIG_ID.UNCUT_OPAL]})))
        expect(step.kind).to_be('buy')
        expect(step.kind == 'buy' and step.item).to_be('Chisel')
    test('cutting an opal without a chisel buys one', _fn22)

    def _fn23():
        expect(label(decide(snap(Record({'stage': DIG_STAGE.THIRD_EXAM, 'inv_ids': [DIG_ID.COINS, DIG_ID.OPAL]}))))).to_be('custom:revise with the three students for exam 3')
    test('a cut opal in the pack sends the bot back to the students', _fn23)


describe('Digsite decide — exams', _fn8)


def _fn24():
    def orange_outstanding(inv_ids):
        return decide(snap(Record({'stage': DIG_STAGE.FIRST_EXAM, 'flags': ['green-answered', 'purple-answered'], 'inv_ids': inv_ids})))

    def _fn25():
        expect(label(orange_outstanding([DIG_ID.COINS]))).to_be("custom:pan the river for the orange student's sample")
    test('the first pan is attempted without asking anyone', _fn25)

    def _fn26():
        digsite_state.tea_wanted = True
        step = orange_outstanding([DIG_ID.COINS])
        expect(step.kind).to_be('buy')
        expect(step.kind == 'buy' and step.item).to_be('Cup of tea')
    test('a refused pan sends the bot to the tea seller', _fn26)

    def _fn27():
        digsite_state.tea_wanted = True
        expect(label(orange_outstanding([DIG_ID.COINS, DIG_ID.CUP_OF_TEA]))).to_be("custom:pan the river for the orange student's sample")
    test('tea in the pack goes back to the water rather than buying another', _fn27)


describe('Digsite decide — panning rights', _fn24)


def _fn28():
    def _fn29():
        expect(label(decide(snap(Record({'stage': DIG_STAGE.IMPRESS_EXPERT, 'inv_ids': [DIG_ID.COINS]}))))).to_be('custom:ask the Examiner for another trowel')
    test('the level 3 dig needs a trowel first', _fn29)

    def _fn30():
        expect(label(decide(snap(Record({'stage': DIG_STAGE.IMPRESS_EXPERT, 'inv_ids': [DIG_ID.COINS, DIG_ID.TROWEL]}))))).to_be('custom:search the sacks for a specimen jar')
    test('a trowel without a jar searches the sacks', _fn30)

    def _fn31():
        expect(label(decide(snap(Record({'stage': DIG_STAGE.IMPRESS_EXPERT, 'inv_ids': [DIG_ID.COINS, DIG_ID.TROWEL, DIG_ID.SPECIMEN_JAR]}))))).to_be('custom:pickpocket the workmen for a specimen brush')
    test('a jar without a brush picks a pocket', _fn31)

    def _fn32():
        expect(label(decide(snap(Record({
        'stage': DIG_STAGE.IMPRESS_EXPERT,
        'inv_ids': [DIG_ID.COINS, DIG_ID.TROWEL, DIG_ID.SPECIMEN_JAR, DIG_ID.SPECIMEN_BRUSH],
    }))))).to_be('custom:dig the level 3 site for a find')
    test('a full dig kit digs', _fn32)

    def _fn33():
        expect(label(decide(snap(Record({'stage': DIG_STAGE.IMPRESS_EXPERT, 'inv_ids': [DIG_ID.COINS, DIG_ID.TALISMAN]}))))).to_be('custom:show the Zarosian talisman to the expert')
    test('a talisman goes to the expert', _fn33)

    def _fn34():
        expect(label(decide(snap(Record({'stage': DIG_STAGE.IMPRESS_EXPERT, 'inv_ids': [DIG_ID.COINS, DIG_ID.EXPERT_SCROLL]}))))).to_be('custom:show the invitation letter to a workman')
    test('the invitation letter goes to a workman', _fn34)


describe('Digsite decide — the find and the permit', _fn28)


def _fn35():
    SHOPPED = [DIG_ID.COINS, DIG_ID.TINDERBOX, DIG_ID.VIAL, DIG_ID.PESTLE]

    def permit(inv_ids, tile=None):
        return decide(snap(Record({'stage': DIG_STAGE.MINESHAFT_PERMIT, 'inv_ids': inv_ids, 'tile': tile})))

    def _fn36():
        expect(label(permit([DIG_ID.COINS]))).to_be('custom:pickpocket the workmen for 2 ropes')
    test('with no key and no root, the rope comes first', _fn36)

    def _fn37():
        expect(label(permit([DIG_ID.COINS, DIG_ID.ROPE]))).to_be('custom:beg the cave workman for the chest key')
    test('with a rope, the west shaft is the first trip', _fn37)

    def _fn38():
        expect(label(permit([DIG_ID.COINS], WEST_SHAFT))).to_be('custom:beg the cave workman for the chest key')
    test('standing in the west shaft does the shaft work rather than climbing out', _fn38)

    def _fn39():
        expect(label(permit([DIG_ID.COINS], EAST_SHAFT))).to_be('custom:climb out of the dig shaft')
    test('standing in the east shaft with shaft work outstanding climbs out', _fn39)

    def _fn40():
        step = permit([DIG_ID.COINS, DIG_ID.CHEST_KEY, DIG_ID.ARCENIA_ROOT])
        expect(step.kind).to_be('buy')
        expect(step.kind == 'buy' and step.item).to_be('Tinderbox')
    test('the shaft work done, the tinderbox is bought before anything walks back east', _fn40)

    def _fn41():
        expect(label(permit([DIG_ID.COINS, DIG_ID.TINDERBOX, DIG_ID.CHEST_KEY, DIG_ID.ARCENIA_ROOT]))).to_be('custom:buy Vial and Pestle and mortar from Jatix')
    test('the vial and the pestle are bought on one trip', _fn41)

    def _fn42():
        expect(label(permit(list(SHOPPED) + [DIG_ID.CHEST_KEY, DIG_ID.ARCENIA_ROOT]))).to_be('custom:unlock and search the digsite chest')
    test('a key and a root move on to the chest', _fn42)

    def _fn43():
        expect(label(permit(list(SHOPPED) + [DIG_ID.POWDER, DIG_ID.ARCENIA_ROOT]))).to_be('custom:have the expert identify the powder')
    test('the powder is identified by the expert', _fn43)

    def _fn44():
        expect(label(permit(list(SHOPPED) + [DIG_ID.AMMONIUM_NITRATE, DIG_ID.ARCENIA_ROOT, DIG_ID.TROWEL]))).to_be('custom:lever the barrel open and fill a vial')
    test('with nitrate and a vial, the trowel opens the barrel', _fn44)

    def _fn45():
        expect(label(permit(list(SHOPPED) + [DIG_ID.AMMONIUM_NITRATE, DIG_ID.ARCENIA_ROOT]))).to_be('custom:ask the Examiner for another trowel')
    test('without a trowel the Examiner is asked for one', _fn45)

    def _fn46():
        expect(label(permit(list(SHOPPED) + [DIG_ID.AMMONIUM_NITRATE, DIG_ID.ARCENIA_ROOT, DIG_ID.LIQUID]))).to_be('custom:have the expert identify the liquid')
    test('a filled vial is identified by the expert', _fn46)

    def _fn47():
        expect(label(permit(list(SHOPPED) + list(NITRATE_AND_NITRO)))).to_be('custom:mix the nitrate into the nitroglycerin')
    test('nitrate and nitroglycerin are mixed', _fn47)

    def _fn48():
        expect(label(permit(list(SHOPPED) + [DIG_ID.PRE_CHARCOAL, DIG_ID.ARCENIA_ROOT, DIG_ID.TROWEL]))).to_be('custom:dig the training site for charcoal')
    test('the half mixture wants charcoal next', _fn48)

    def _fn49():
        expect(label(permit(list(SHOPPED) + [DIG_ID.PRE_CHARCOAL, DIG_ID.ARCENIA_ROOT, DIG_ID.CHARCOAL]))).to_be('custom:grind the charcoal to a powder')
    test('charcoal and a pestle are ground', _fn49)

    def _fn50():
        expect(label(permit(list(SHOPPED) + [DIG_ID.PRE_CHARCOAL, DIG_ID.ARCENIA_ROOT, DIG_ID.GROUND_CHARCOAL]))).to_be('custom:mix the ground charcoal in')
    test('ground charcoal is mixed in', _fn50)

    def _fn51():
        expect(label(permit(list(SHOPPED) + [DIG_ID.POST_CHARCOAL, DIG_ID.ARCENIA_ROOT]))).to_be('custom:mix the arcenia root in')
    test('the root is last into the mixture', _fn51)

    def _fn52():
        step = permit([DIG_ID.COINS, DIG_ID.COMPOUND, DIG_ID.ROPE])
        expect(step.kind).to_be('buy')
        expect(step.kind == 'buy' and step.item).to_be('Tinderbox')
    test('a finished compound needs a tinderbox before the shaft', _fn52)

    def _fn53():
        expect(label(permit([DIG_ID.COINS, DIG_ID.COMPOUND, DIG_ID.TINDERBOX, DIG_ID.ROPE]))).to_be('custom:pour the compound over the blocked bricks')
    test('compound, tinderbox and rope go and pour it', _fn53)


describe('Digsite decide — the chemical chain', _fn35)


def _fn54():
    def _fn55():
        expect(label(decide(snap(Record({'stage': DIG_STAGE.POURED_COMPOUND, 'inv_ids': [DIG_ID.COINS, DIG_ID.TINDERBOX, DIG_ID.ROPE]}))))).to_be('custom:light the explosive compound')
    test('a poured compound is lit', _fn55)

    def _fn56():
        expect(label(decide(snap(Record({'stage': DIG_STAGE.POURED_COMPOUND, 'inv_ids': [DIG_ID.COINS], 'tile': ALTAR_CAVE}))))).to_be('custom:take the Zarosian stone tablet')
    test('a blast that already went off looks for the tablet', _fn56)

    def _fn57():
        expect(label(decide(snap(Record({'stage': DIG_STAGE.REMOVED_BLOCKAGE, 'inv_ids': [DIG_ID.COINS], 'tile': ALTAR_CAVE}))))).to_be('custom:take the Zarosian stone tablet')
    test('the altar cave is searched for the tablet', _fn57)

    def _fn58():
        expect(label(decide(snap(Record({'stage': DIG_STAGE.REMOVED_BLOCKAGE, 'inv_ids': [DIG_ID.COINS, DIG_ID.STONE_TABLET], 'tile': ALTAR_CAVE}))))).to_be('custom:climb out of the dig shaft')
        expect(label(decide(snap(Record({'stage': DIG_STAGE.REMOVED_BLOCKAGE, 'inv_ids': [DIG_ID.COINS, DIG_ID.STONE_TABLET]}))))).to_be('custom:show the stone tablet to the expert')
    test('a held tablet goes to the expert, climbing out first', _fn58)


describe('Digsite decide — the blast and the tablet', _fn54)


def _fn59():
    def _fn60():
        expect([d for d in QUEST_DEFS if d.record.id == 'itexam']).to_have_length(1)
    test('the module is in the queue exactly once', _fn60)

    def _fn61():
        expect(digsite.owns_inventory).to_be(True)
        expect(digsite.bank).to_be(DIG_TILE.VARROCK_BANK)
    test('it owns its own inventory and pins the Varrock booth', _fn61)

    def _fn62():
        expect(digsite.read_progress is not None).to_be(True)
        expect(digsite.read_stage).to_be_undefined()
    test('it reads progress from the journal rather than a varp', _fn62)

    def _fn63():
        for stage in [
        DIG_STAGE.NOT_STARTED,
        DIG_STAGE.STAMPING,
        DIG_STAGE.FIRST_EXAM,
        DIG_STAGE.SECOND_EXAM,
        DIG_STAGE.THIRD_EXAM,
        DIG_STAGE.IMPRESS_EXPERT,
    ]:
            expect(label(decide(snap(Record({'stage': stage, 'inv_ids': [DIG_ID.COINS], 'tile': WEST_SHAFT}))))).to_be('custom:climb out of the dig shaft')
    test('every surface leg escapes a shaft first', _fn63)


describe('Digsite module wiring', _fn59)
