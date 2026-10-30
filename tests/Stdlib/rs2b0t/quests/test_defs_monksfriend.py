"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/monksfriend.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot

from rs2004.quests.defs.monksfriend import BLANKET_OBJ, MF_STAGE, decide, monksfriend, parse_monks_friend_journal
# Pages built from content/scripts/quests/quest_drunkmonk/scripts/drunkmonk_journal.rs2.
NOT_STARTED = '@dbl@I can start this quest by speaking to @dre@Brother Omad@dbl@ in the|@dre@Monastery@dbl@ south of @dre@Ardougne'
SPOKEN_TO_OMAD = "@dre@Brother Omad@dbl@ asked me to recover a @dre@child's blanket@dbl@.|" + 'I need to find a @dre@secret cave@dbl@ that is hidden under a @dre@ring of' + '|@dre@stones@dbl@ in the @dre@forest@dbl@ south of @dre@Ardougne'
BLANKET_LINE = "@str@Brother Omad asked me to recover a child's blanket.|@str@I found the secret cave and gave back the blanket."
RETRIEVED_BLANKET = BLANKET_LINE
LOOKING_CEDRIC = BLANKET_LINE + '||@dbl@I agreed to find @dre@Brother Cedric@dbl@. He is somewhere in the|@dre@forest@dbl@ south of @dre@Ardougne'
FINDING_WATER = BLANKET_LINE + '||@str@I found Brother Cedric in the forest south of Ardougne.|@dbl@I need to take him a @dre@jug of water'
MENDING_CART = BLANKET_LINE + '||@str@I found Brother Cedric in the forest south of Ardougne. I|@str@sobered him up.|' + '@dbl@He needs some @dre@wood@dbl@ for his cart'
FIXED_CART = BLANKET_LINE + '||@str@I found Brother Cedric in the forest south of Ardougne. I|@str@sobered him up and I helped him fix his cart.|' + '@dre@Brother Cedric@dbl@ said that I should tell @dre@Brother Omad@dbl@ that|he is on the way.'
COMPLETE = BLANKET_LINE + '||@str@I found Brother Cedric in the forest south of Ardougne. I|@str@sobered him up and I helped him fix his cart.||' + '@str@I had a party with the Monks. There were party balloons|@str@and we danced the night away!||@red@QUEST COMPLETE!'


def counts(names):
    result = {}
    for name in names:
        key = name.lower()
        _v1 = result.get(key)
        result[key] = ((_v1 if _v1 is not None else 0)) + 1
    return result


def id_counts(ids):
    result = {}
    for id in ids:
        _v2 = result.get(id)
        result[id] = ((_v2 if _v2 is not None else 0)) + 1
    return result


def snap(options=None):
    if options is None:
        options = Record({})
    stage = (options.stage if 'stage' in options._fields else MF_STAGE.NOT_STARTED)
    return QuestSnapshot(**{
        'journal': (options.journal if options.journal is not None else 'in_progress'),
        'inv': counts((options.inv if options.inv is not None else [])),
        'inv_ids': id_counts((options.inv_ids if options.inv_ids is not None else [])),
        'worn': set(),
        'no_progress': 0,
        'bank_coins': 2000000,
        'stage': stage,
        'progress': (None if stage is None else Record({'stage': stage, 'flags': set()})),
        'bank': counts((options.bank if options.bank is not None else [])),
        'bank_known': (options.bank_known if options.bank_known is not None else True),
        'free_slots': 28,
    })


def custom_name(step):
    return (step.name if step.kind == 'custom' else None)


def talk_to(step):
    return (step.stop.npc if step.kind == 'talk' else None)


def _fn3():
    def _fn4():
        expect(parse_monks_friend_journal(NOT_STARTED)).to_be(MF_STAGE.NOT_STARTED)
    test('reads the not-started page as stage 0', _fn4)

    def _fn5():
        expect(parse_monks_friend_journal(SPOKEN_TO_OMAD)).to_be(MF_STAGE.SPOKEN_TO_OMAD)
    test('reads the blanket hunt as spoken-to-Omad', _fn5)

    def _fn6():
        expect(parse_monks_friend_journal(RETRIEVED_BLANKET)).to_be(MF_STAGE.RETRIEVED_BLANKET)
    test('reads the returned blanket as stage 20', _fn6)

    def _fn7():
        expect(parse_monks_friend_journal(LOOKING_CEDRIC)).to_be(MF_STAGE.LOOKING_CEDRIC)
    test('separates the Cedric search from the blanket page they share', _fn7)

    def _fn8():
        expect(parse_monks_friend_journal(FINDING_WATER)).to_be(MF_STAGE.FINDING_WATER)
    test('reads the water errand as stage 40', _fn8)

    def _fn9():
        expect(parse_monks_friend_journal(MENDING_CART)).to_be(MF_STAGE.MENDING_CART)
    test('reads the wood errand as the mending-cart stage', _fn9)

    def _fn10():
        expect(parse_monks_friend_journal(FIXED_CART)).to_be(MF_STAGE.FIXED_CART)
    test('reads the fixed cart as stage 70', _fn10)

    def _fn11():
        expect(parse_monks_friend_journal(COMPLETE)).to_be(MF_STAGE.COMPLETE)
    test('reads the finished page as complete', _fn11)

    def _fn12():
        expect(parse_monks_friend_journal('some other quest entirely')).to_be_undefined()
    test('returns undefined for a page it cannot place', _fn12)


describe("Monk's Friend journal parsing", _fn3)


def _fn13():
    def _fn14():
        expect(decide(snap(Record({'journal': 'unknown'})))).to_equal(Record({'kind': 'wait', 'reason': 'quest journal not loaded'}))
    test('waits while the quest list is still loading', _fn14)

    def _fn15():
        expect(decide(snap(Record({'journal': 'complete'}))).kind).to_be('done')
    test('is done once the quest list turns green', _fn15)

    def _fn16():
        expect(decide(snap(Record({'stage': None}))).kind).to_be('wait')
    test('waits rather than guessing when the journal stage is unavailable', _fn16)

    def _fn17():
        step = decide(snap(Record({'journal': 'not_started'})))
        expect(talk_to(step)).to_be('Brother Omad')
        expect(step.kind == 'talk' and step.stop.prefer).to_contain('Can I help at all?')
    test('opens with Brother Omad when the quest has not started', _fn17)

    def _fn18():
        expect(custom_name(decide(snap(Record({'stage': MF_STAGE.SPOKEN_TO_OMAD}))))).to_be("fetch the child's blanket")
    test('goes down the hidden ladder for the blanket once Omad has asked', _fn18)

    def _fn19():
        step = decide(snap(Record({'stage': MF_STAGE.SPOKEN_TO_OMAD, 'inv': ["Child's blanket"], 'inv_ids': [BLANKET_OBJ]})))
        expect(talk_to(step)).to_be('Brother Omad')
    test('hands a carried blanket back, since the journal still says to find the cave', _fn19)

    def _fn20():
        step = decide(snap(Record({'stage': MF_STAGE.RETRIEVED_BLANKET})))
        expect(talk_to(step)).to_be('Brother Omad')
        expect(step.kind == 'talk' and step.stop.prefer).to_contain('Where should I look?')
    test('asks Omad where to look once the blanket is returned', _fn20)

    def _fn21():
        expect(talk_to(decide(snap(Record({'stage': MF_STAGE.LOOKING_CEDRIC}))))).to_be('Brother Cedric')
    test('finds Cedric in the forest once Omad names him', _fn21)

    def _fn22():
        expect(decide(snap(Record({'stage': MF_STAGE.FINDING_WATER, 'bank_known': False}))).kind).to_be('scan_bank')
    test('reads the bank before believing it has no jug', _fn22)

    def _fn23():
        step = decide(snap(Record({'stage': MF_STAGE.FINDING_WATER, 'bank': ['Jug of water']})))
        expect(step.kind).to_be('withdraw')
        expect(step.kind == 'withdraw' and step.items[0]['name']).to_be('Jug of water')
    test('takes a banked jug of water rather than buying another', _fn23)

    def _fn24():
        step = decide(snap(Record({'stage': MF_STAGE.FINDING_WATER})))
        expect(step.kind).to_be('buy')
        expect(step.kind == 'buy' and step.item).to_be('Jug')
        expect(step.kind == 'buy' and step.shop.npc).to_be('Shop keeper')
    test('buys a jug at Port Khazard when nothing is banked', _fn24)

    def _fn25():
        expect(custom_name(decide(snap(Record({'stage': MF_STAGE.FINDING_WATER, 'inv': ['Jug']}))))).to_be('fill the jug at the guardhouse sink')
    test('fills an empty jug at the guardhouse sink', _fn25)

    def _fn26():
        expect(talk_to(decide(snap(Record({'stage': MF_STAGE.FINDING_WATER, 'inv': ['Jug of water']}))))).to_be('Brother Cedric')
    test('sobers Cedric up once the water is carried', _fn26)

    def _fn27():
        step = decide(snap(Record({'stage': MF_STAGE.MENDING_CART, 'bank': ['Rune axe']})))
        expect(step.kind).to_be('withdraw')
        expect(step.kind == 'withdraw' and step.items[0]['name']).to_be('Rune axe')
    test('takes a banked axe rather than buying one', _fn27)

    def _fn28():
        step = decide(snap(Record({'stage': MF_STAGE.MENDING_CART})))
        expect(step.kind).to_be('buy')
        expect(step.kind == 'buy' and step.item).to_be('Iron axe')
    test('buys an iron axe in East Ardougne when none is banked', _fn28)

    def _fn29():
        expect(custom_name(decide(snap(Record({'stage': MF_STAGE.MENDING_CART, 'inv': ['Iron axe']}))))).to_be('chop logs for the cart')
    test('chops a forest tree once an axe is in the pack', _fn29)

    def _fn30():
        step = decide(snap(Record({'stage': MF_STAGE.MENDING_CART, 'inv': ['Bronze pickaxe']})))
        expect(step.kind).to_be('buy')
    test('does not mistake a pickaxe for a woodcutting axe', _fn30)

    def _fn31():
        expect(talk_to(decide(snap(Record({'stage': MF_STAGE.MENDING_CART, 'inv': ['Logs']}))))).to_be('Brother Cedric')
    test('hands the logs over once they are cut', _fn31)

    def _fn32():
        expect(custom_name(decide(snap(Record({'stage': MF_STAGE.FIXED_CART}))))).to_be('tell Omad that Cedric is on his way')
    test('reports back to Omad once the cart is fixed', _fn32)


describe("Monk's Friend decide", _fn13)


def _fn33():
    def _fn34():
        expect(monksfriend.record.items).to_equal([])
    test('lists no required items, since the jug, axe and logs are all sourced mid-quest', _fn34)

    def _fn35():
        expect(monksfriend.record.requirements).to_equal(Record({}))
    test('is standalone — no quest or skill gates', _fn35)

    def _fn36():
        for tool in ["child's blanket", 'jug', 'logs', 'axe', 'coins']:
            expect(monksfriend.tools).to_contain(tool)
    test('keeps every quest consumable off the deposit list', _fn36)

    def _fn37():
        stands = [f'{h.stand.x},{h.stand.z}' for h in ((monksfriend.hops if monksfriend.hops is not None else []))]
        expect(sorted(stands)).to_equal(['2561,9622', '2562,3222'])
    test('hops name the ring of stones and the cave ladder back out', _fn37)


describe("Monk's Friend module", _fn33)
