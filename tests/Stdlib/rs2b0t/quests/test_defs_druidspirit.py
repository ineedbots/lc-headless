"""rs2b0t's test/api/ai/quests/defs/druidspirit.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestProgress, QuestSnapshot
from rs2004.quests.defs.druidspirit import decide, druidspirit
from rs2004.quests.defs.druidspirit.areas import BLOOM_MAX_COST, NS_ID, NS_STAGE
from rs2004.quests.defs.druidspirit.journal import NS_FLAG
from rs2004.quests.defs import QUEST_DEFS

CAMP = Record({'x': 3440, 'z': 3336, 'level': 0})
GROTTO = Record({'x': 3442, 'z': 9734, 'level': 0})
BANK = Record({'x': 3253, 'z': 3420, 'level': 0})


def snap(options=None):
    if options is None:
        options = Record({})
    stage = (options.stage if options.stage is not None else NS_STAGE.NOT_STARTED)
    return QuestSnapshot(**{
        'journal': (options.journal if options.journal is not None else (('not_started' if stage == NS_STAGE.NOT_STARTED else 'in_progress'))),
        'inv': {},
        'inv_ids': {_k: _v for _k, _v in [[NS_ID.COINS, 50000]] + list(((options.inv_ids if options.inv_ids is not None else [])))},
        'worn': set(),
        'worn_ids': set((options.worn_ids if options.worn_ids is not None else [NS_ID.GHOSTSPEAK])),
        'no_progress': 0,
        'bank_coins': 2000000,
        'stage': stage,
        'progress': QuestProgress(stage, set((options.flags if options.flags is not None else []))),
        'bank': {},
        'bank_ids': {_k: _v for _k, _v in (options.bank_ids if options.bank_ids is not None else [])},
        'bank_known': True,
        'tile': (options.tile if options.tile is not None else CAMP),
        'prayer': options.prayer,
        'free_slots': 20,
    })


def step(options=None):
    if options is None:
        options = Record({})
    return decide(snap(options))


def named(s):
    return ((s.name if s.kind == 'custom' else s.kind))


def _fn1():
    def _fn2():
        expect(step(Record({'journal': 'unknown'}))).to_equal(Record({'kind': 'wait', 'reason': 'quest journal not loaded'}))
    test('an unloaded journal waits rather than restarting the quest', _fn2)

    def _fn3():
        expect(step(Record({'journal': 'complete', 'stage': NS_STAGE.COMPLETE}))).to_equal(Record({'kind': 'done'}))
    test('a complete journal is done', _fn3)

    def _fn4():
        s = step()
        expect(s.kind).to_be('talk')
        expect(s.kind == 'talk' and s.stop.npc).to_be('Drezel')
    test('not started talks to Drezel', _fn4)

    def _fn5():
        s = step(Record({'worn_ids': []}))
        expect(s.kind).to_be('talk')
        expect(s.kind == 'talk' and s.stop.npc).to_be('Father Urhney')
    test('the amulet is fetched before the quest is even started', _fn5)

    def _fn6():
        expect(step(Record({'stage': NS_STAGE.STARTED, 'worn_ids': [], 'inv_ids': [[NS_ID.GHOSTSPEAK, 1]]}))).to_equal(Record({'kind': 'equip', 'item': 'Ghostspeak amulet'}))
    test('the amulet is worn before the spirit is approached', _fn6)

    def _fn7():
        expect(named(step(Record({'stage': NS_STAGE.STARTED})))).to_be('find Filliman')
    test('started walks to the camp and talks', _fn7)

    def _fn8():
        expect(named(step(Record({'stage': NS_STAGE.FAILED_TALK})))).to_be('find Filliman')
    test('a failed talk is the same leg once the amulet is on', _fn8)

    def _fn9():
        expect(named(step(Record({'stage': NS_STAGE.SPOKEN_FILLIMAN})))).to_be('mirror')
    test('spoken means fetch the mirror', _fn9)

    def _fn10():
        expect(named(step(Record({'stage': NS_STAGE.SHOWN_MIRROR})))).to_be("Tarlock's journal")
    test('shown the mirror means fetch the journal', _fn10)

    def _fn11():
        expect(named(step(Record({'stage': NS_STAGE.GIVEN_JOURNAL})))).to_be('offer to help')
    test('journal handed over means ask how to help', _fn11)

    def _fn12():
        s = step(Record({'stage': NS_STAGE.RECEIVED_SPELL}))
        expect(s.kind).to_be('talk')
        expect(s.kind == 'talk' and s.stop.npc).to_be('Drezel')
    test('holding the spell means get blessed', _fn12)

    def _fn13():
        expect(named(step(Record({'stage': NS_STAGE.BLESSED, 'inv_ids': [[NS_ID.SPELL, 1]]})))).to_be('bloom the swamp for a fungus')
    test('blessed casts the bloom scroll', _fn13)

    def _fn14():
        expect(named(step(Record({'stage': NS_STAGE.BLESSED})))).to_be('ask for another bloom scroll')
    test('a lost scroll is re-issued by Filliman rather than parking', _fn14)

    def _fn15():
        expect(named(step(Record({'stage': NS_STAGE.BLESSED, 'inv_ids': [[NS_ID.SPELL_USED, 1]]})))).to_be('ask for another bloom scroll')
    test('a spent scroll cannot be cast again, so another is asked for', _fn15)

    def _fn16():
        expect(named(step(Record({'stage': NS_STAGE.CASTED_SPELL, 'inv_ids': [[NS_ID.SPELL, 1]]})))).to_be('bloom the swamp for a fungus')
    test('cast but no fungus blooms again rather than hunting a reverted log', _fn16)

    def _fn17():
        expect(named(step(Record({'stage': NS_STAGE.BLESSED, 'inv_ids': [[NS_ID.FUNGI, 1], [NS_ID.SPELL_USED, 1]]})))).to_be('feed the ritual stones')
    test('a held fungus outranks a journal that has not caught up', _fn17)

    def _fn18():
        expect(named(step(Record({'stage': NS_STAGE.PICKED_FUNGI, 'inv_ids': [[NS_ID.SPELL, 1]]})))).to_be('bloom the swamp for a fungus')
    test('resuming at the fungus stage with an empty pack blooms again', _fn18)

    def _fn19():
        expect(named(step(Record({'stage': NS_STAGE.PICKED_FUNGI, 'inv_ids': [[NS_ID.FUNGI, 1], [NS_ID.SPELL_USED, 1]]})))).to_be('feed the ritual stones')
    test('with the fungus and no stones fed, the stones come first', _fn19)

    def _fn20():
        expect(named(step(Record({'stage': NS_STAGE.SPOKEN_FILLIMAN2, 'flags': [NS_FLAG.NATURE], 'inv_ids': [[NS_ID.SPELL_USED, 1]]})))).to_be('feed the ritual stones')
    test('one stone fed still feeds the other', _fn20)

    def _fn21():
        expect(named(step(Record({'stage': NS_STAGE.SPOKEN_FILLIMAN2, 'flags': [NS_FLAG.NATURE, NS_FLAG.SPIRIT]})))).to_be('solve the ritual')
    test('both stones fed stands on the faith stone and solves the puzzle', _fn21)

    def _fn22():
        expect(named(step(Record({'stage': NS_STAGE.PERFORMED_RITUAL})))).to_be('enter the grotto')
    test('ritual done enters the grotto', _fn22)

    def _fn23():
        expect(named(step(Record({'stage': NS_STAGE.ENTERED_GROTTO, 'tile': GROTTO})))).to_be('watch the transformation')
    test('inside the grotto, the transformation is a talk', _fn23)

    def _fn24():
        expect(step(Record({'stage': NS_STAGE.FULL_TRANSFORM, 'tile': BANK})).kind).to_be('buy')
    test('transformed sources the sickle before returning', _fn24)

    def _fn25():
        expect(named(step(Record({'stage': NS_STAGE.FULL_TRANSFORM, 'tile': GROTTO})))).to_be('leave the grotto')
    test('a sourcing step taken from inside the grotto leaves the pocket first', _fn25)

    def _fn26():
        expect(named(step(Record({'stage': NS_STAGE.FULL_TRANSFORM, 'inv_ids': [[NS_ID.SICKLE, 1]]})))).to_be('hand over the sickle')
    test('transformed with a sickle held hands it over', _fn26)

    def _fn27():
        expect(named(step(Record({'stage': NS_STAGE.BLESSED_SICKLE, 'inv_ids': [[NS_ID.SICKLE_BLESSED, 1], [NS_ID.POUCH_EMPTY, 1]]})))).to_be('harvest natures bounty')
    test('a blessed sickle blooms the swamp', _fn27)

    # Why: the grotto's Altar of nature is on the level the door only teleports to once the quest is
    # over, so mid-quest the recharge is Paterdomus, the temple the swamp route already passes.
    def _fn28():
        kit = [[NS_ID.SICKLE_BLESSED, 1], [NS_ID.POUCH_EMPTY, 1]]
        for prayer in [0, 1, BLOOM_MAX_COST - 1]:
            expect(named(step(Record({'stage': NS_STAGE.BLESSED_SICKLE, 'inv_ids': kit, 'prayer': prayer})))).to_be('recharge prayer at the Paterdomus altar')
    test('a bloom needs prayer, so a short bar goes to the Paterdomus altar first', _fn28)

    def _fn29():
        kit = [[NS_ID.SICKLE_BLESSED, 1], [NS_ID.POUCH_EMPTY, 1]]
        for prayer in [BLOOM_MAX_COST, 43]:
            expect(named(step(Record({'stage': NS_STAGE.BLESSED_SICKLE, 'inv_ids': kit, 'prayer': prayer})))).to_be('harvest natures bounty')
    test('a bar that covers the dearest cast harvests instead of walking to the altar', _fn29)

    def _fn30():
        expect(named(step(Record({'stage': NS_STAGE.BLESSED_SICKLE, 'inv_ids': [[NS_ID.SICKLE_BLESSED, 1], [NS_ID.POUCH_EMPTY, 1]]})))).to_be('harvest natures bounty')
    test('a snapshot that does not report prayer harvests as before', _fn30)

    def _fn31():
        expect(named(step(Record({'stage': NS_STAGE.ADDED_POUCH, 'inv_ids': [[NS_ID.SICKLE_BLESSED, 1], [NS_ID.POUCH, 6]], 'prayer': 0})))).to_be('kill a ghast')
    test('a full pouch hunts rather than recharging — only a bloom costs prayer', _fn31)

    def _fn32():
        expect(step(Record({
        'stage': NS_STAGE.ADDED_POUCH,
        'inv_ids': [[NS_ID.SICKLE_BLESSED, 1]],
        'bank_ids': [[NS_ID.POUCH_EMPTY, 1]],
    }))).to_match_object(Record({'kind': 'withdraw', 'items': [Record({'name': 'Druid pouch', 'id': NS_ID.POUCH_EMPTY, 'qty': 1})]}))
    test('a resumed ghast hunt withdraws the empty pouch left in the bank', _fn32)

    def _fn33():
        expect(step(Record({
        'stage': NS_STAGE.ADDED_POUCH,
        'inv_ids': [[NS_ID.SICKLE_BLESSED, 1]],
        'bank_ids': [[NS_ID.POUCH_EMPTY, 1], [NS_ID.POUCH, 3]],
    }))).to_match_object(Record({'kind': 'withdraw', 'items': [Record({'name': 'Druid pouch', 'id': NS_ID.POUCH, 'qty': 3})]}))
    test('banked charges outrank an empty pouch on a resumed ghast hunt', _fn33)

    def _fn34():
        expect(named(step(Record({
        'stage': NS_STAGE.PICKED_SICKLE,
        'inv_ids': [[NS_ID.SICKLE_BLESSED, 1], [NS_ID.POUCH_EMPTY, 1], [NS_ID.PEAR, 3]],
        'prayer': 0,
    })))).to_be('fill the druid pouch')
    test('three harvests fill the pouch on an empty bar — filling costs no prayer', _fn34)

    def _fn35():
        expect(named(step(Record({'stage': NS_STAGE.BLESSED_SICKLE, 'inv_ids': [[NS_ID.SICKLE, 1]]})))).to_be('bless the sickle')
    test('a lost blessed sickle is re-dipped in the grotto', _fn35)

    def _fn36():
        expect(named(step(Record({
        'stage': NS_STAGE.PICKED_SICKLE,
        'inv_ids': [[NS_ID.SICKLE_BLESSED, 1], [NS_ID.POUCH_EMPTY, 1], [NS_ID.PEAR, 3]],
    })))).to_be('fill the druid pouch')
    test('three harvests fill the pouch', _fn36)

    def _fn37():
        expect(named(step(Record({'stage': NS_STAGE.ADDED_POUCH, 'inv_ids': [[NS_ID.SICKLE_BLESSED, 1], [NS_ID.POUCH, 6]]})))).to_be('kill a ghast')
    test('a charged pouch hunts a ghast', _fn37)

    def _fn38():
        expect(named(step(Record({'stage': NS_STAGE.KILLED_GHAST1, 'inv_ids': [[NS_ID.SICKLE_BLESSED, 1], [NS_ID.POUCH_EMPTY, 1]]})))).to_be('harvest natures bounty')
    test('the charged pouch is read by id, never by its shared display name', _fn38)

    def _fn39():
        expect(named(step(Record({'stage': NS_STAGE.KILLED_GHAST3, 'inv_ids': [[NS_ID.SICKLE_BLESSED, 1]]})))).to_be('claim the reward')
    test('three ghasts down reports back', _fn39)

    def _fn40():
        ids = [d.record.id for d in QUEST_DEFS]
        expect(ids).to_contain('druidspirit')
        expect((ids.index('druidspirit') if 'druidspirit' in ids else -1)).to_be_greater_than((ids.index('priestperil') if 'priestperil' in ids else -1))
        expect((ids.index('druidspirit') if 'druidspirit' in ids else -1)).to_be_greater_than((ids.index('priest') if 'priest' in ids else -1))
    test('the module is registered in the queue after its prerequisites', _fn40)

    def _fn41():
        expect(druidspirit.owns_inventory).to_be(True)
        expect(druidspirit.record.id).to_be('druidspirit')
        expect(druidspirit.record.name).to_be('Nature Spirit')
    test('the module owns its own inventory', _fn41)


describe('nature spirit decide', _fn1)
