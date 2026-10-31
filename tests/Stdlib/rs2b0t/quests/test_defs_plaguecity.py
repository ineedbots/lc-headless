"""Ported from rs2b0t's test/api/ai/quests/defs/plaguecity.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.defs.plaguecity import decide, plaguecity
from rs2004.quests.defs.plaguecity.areas import PC_ITEM
from rs2004.quests.defs.plaguecity.journal import PC_STAGE
from rs2004.quests.engine.types import QuestSnapshot

EAST = Record({'x': 2616, 'z': 3332, 'level': 0})
WEST = Record({'x': 2540, 'z': 3305, 'level': 0})
SEWER = Record({'x': 2530, 'z': 9703, 'level': 0})
PURSE = {_k: _v for _k, _v in [[PC_ITEM.COINS.id, 100000]]}


def option(o, key, default):
    value = o.get(key)
    return default if value is None else value


# Why: the overrides are a plain dict, since a Record can't hold the id-keyed maps.
def snapshot(options=None):
    o = options if options is not None else {}
    return QuestSnapshot(**{
        'journal': option(o, 'journal', 'in_progress'),
        'inv': option(o, 'inv', {}),
        'inv_ids': option(o, 'inv_ids', {}),
        'worn': option(o, 'worn', set()),
        'worn_ids': option(o, 'worn_ids', set()),
        'no_progress': 0,
        'bank_coins': option(o, 'bank_coins', 0),
        'stage': o.get('stage'),
        'progress': o.get('progress'),
        'bank': option(o, 'bank', {}),
        'bank_ids': option(o, 'bank_ids', PURSE),
        'bank_known': option(o, 'bank_known', True),
        'tile': EAST if 'tile' not in o else o['tile'],
        'free_slots': option(o, 'free_slots', 28),
    })


def carrying(*items):
    return {_k: _v for _k, _v in [[item.id, qty] for item, qty in items]}


def name(step):
    return ((step.name if step.kind == 'custom' else step.kind))


KIT = carrying([PC_ITEM.SPADE, 1], [PC_ITEM.GAS_MASK, 1])


def _fn2():
    def _fn3():
        expect(decide(snapshot({'journal': 'complete'})).kind).to_be('done')
    test('a complete journal on the mainland is done', _fn3)

    def _fn4():
        step = decide(snapshot({'journal': 'complete', 'inv_ids': carrying([PC_ITEM.ARDOUGNE_SCROLL, 1])}))
        expect(name(step)).to_be('read the Ardougne teleport scroll')
    test('a complete journal holding the reward scroll reads it before finishing', _fn4)

    def _fn5():
        expect(name(decide(snapshot({'journal': 'complete', 'tile': WEST})))).to_be('walk back to East Ardougne')
    test('a complete journal inside West Ardougne walks out first', _fn5)

    def _fn6():
        expect(decide(snapshot({'journal': 'unknown'})).kind).to_be('wait')
    test('an unloaded journal waits — it is not notStarted', _fn6)

    def _fn7():
        expect(decide(snapshot({'tile': None, 'stage': PC_STAGE.STARTED})).kind).to_be('wait')
    test('an unknown tile waits rather than guessing an area', _fn7)

    def _fn8():
        expect(decide(snapshot({'stage': None})).kind).to_be('wait')
    test('an unreadable stage waits', _fn8)

    def _fn9():
        step = decide(snapshot({'stage': PC_STAGE.STARTED, 'free_slots': 2}))
        expect(step.kind).to_be('deposit')
    test('a nearly full pack banks spillover before the next pickup', _fn9)


describe('plague city decide — terminal and guard cases', _fn2)


def _fn10():
    def _fn11():
        float_ = decide(snapshot({'stage': PC_STAGE.NOT_STARTED}))
        expect(float_.kind == 'withdraw' and float_.items[0]['name']).to_be(PC_ITEM.COINS.name)
        expect(float_.kind == 'withdraw' and float_.items[0]['qty']).to_be(2000)
        ask = decide(snapshot({'stage': PC_STAGE.NOT_STARTED, 'inv_ids': carrying([PC_ITEM.COINS, 2000])}))
        expect(name(ask)).to_be('ask Edmond about his daughter')
    test('stage 0 draws the shopping float, then asks Edmond about his daughter', _fn11)

    def _fn12():
        step = decide(snapshot({'stage': PC_STAGE.NOT_STARTED, 'bank_ids': {}}))
        expect(name(step)).to_be('ask Edmond about his daughter')
    test('an empty bank does not park the quest on its first step', _fn12)

    def _fn13():
        fetch = decide(snapshot({'stage': PC_STAGE.STARTED}))
        expect(fetch.kind).to_be('grab_ground')
        expect(fetch.kind == 'grab_ground' and fetch.item).to_be(PC_ITEM.DWELLBERRIES.name)
        give = decide(snapshot({'stage': PC_STAGE.STARTED, 'inv_ids': carrying([PC_ITEM.DWELLBERRIES, 1])}))
        expect(name(give)).to_be('give Alrena the dwellberries')
    test('stage 1 fetches dwellberries, then hands them to Alrena', _fn13)

    def _fn14():
        step = decide(snapshot({'stage': PC_STAGE.STARTED, 'bank_ids': {_k: _v for _k, _v in [[PC_ITEM.DWELLBERRIES.id, 3]]}}))
        expect(step.kind).to_be('withdraw')
    test('banked dwellberries are withdrawn rather than picked', _fn14)

    def _fn15():
        expect(name(decide(snapshot({'stage': PC_STAGE.GASMASK})))).to_be('ask Edmond about the way into West Ardougne')
    test('stage 2 asks Edmond about the way in', _fn15)

    def _fn16():
        empty = decide(snapshot({'stage': PC_STAGE.MUD_START, 'bank_ids': {}}))
        expect(empty.kind).to_be('grab_ground')
        short = decide(snapshot({'stage': PC_STAGE.MUD_START, 'bank_ids': {}, 'inv_ids': carrying([PC_ITEM.BUCKET, 2])}))
        expect(short.kind == 'grab_ground' and short.item).to_be(PC_ITEM.BUCKET.name)
        fill = decide(snapshot({'stage': PC_STAGE.MUD_START, 'inv_ids': carrying([PC_ITEM.BUCKET, 4])}))
        expect(name(fill)).to_be('fill buckets at the Ardougne fountain')
        pour = decide(snapshot({'stage': PC_STAGE.MUD_START, 'inv_ids': carrying([PC_ITEM.BUCKET_WATER, 4])}))
        expect(name(pour)).to_be('pour water on the garden soil')
    test('the water block gathers four buckets, fills them, then pours them', _fn16)

    def _fn17():
        step = decide(snapshot({'stage': PC_STAGE.MUD_START, 'inv_ids': carrying([PC_ITEM.BUCKET_WATER, 2], [PC_ITEM.BUCKET, 2])}))
        expect(name(step)).to_be('fill buckets at the Ardougne fountain')
    test('a part-filled pack tops the water up before it walks to the garden', _fn17)

    def _fn18():
        step = decide(snapshot({'stage': PC_STAGE.SPOKEN_BRAVEK, 'inv_ids': carrying([PC_ITEM.COINS, 2000], [PC_ITEM.BUCKET, 1])}))
        expect(step.kind == 'use_on' and step.product).to_be(PC_ITEM.BUCKET_MILK.name)
    test('the milk bucket is sourced one at a time, not four', _fn18)

    def _fn19():
        step = decide(snapshot({'stage': PC_STAGE.MUD_START, 'bank_ids': {_k: _v for _k, _v in [[PC_ITEM.BUCKET.id, 9]]}}))
        expect(step.kind == 'withdraw' and step.items[0]['qty']).to_be(4)
    test('a stocked bank fills the pack with buckets in one trip', _fn19)

    def _fn20():
        spade = decide(snapshot({'stage': PC_STAGE.MUD_SOFT, 'bank_ids': {}}))
        expect(name(spade)).to_be("take the spade from Edmond's house")
        rope = decide(snapshot({'stage': PC_STAGE.MUD_SOFT, 'inv_ids': carrying([PC_ITEM.SPADE, 1], [PC_ITEM.COINS, 2000])}))
        expect(rope.kind == 'buy' and rope.item).to_be(PC_ITEM.ROPE.name)
        dig = decide(snapshot({'stage': PC_STAGE.MUD_SOFT, 'inv_ids': carrying([PC_ITEM.SPADE, 1], [PC_ITEM.ROPE, 1])}))
        expect(name(dig)).to_be('drop into the Ardougne sewer')
    test('stage 7 buys the spade and the rope before it digs', _fn20)

    def _fn21():
        buy = decide(snapshot({'stage': PC_STAGE.TUNNEL, 'inv_ids': carrying([PC_ITEM.COINS, 2000])}))
        expect(buy.kind == 'buy' and buy.item).to_be(PC_ITEM.ROPE.name)
        tie = decide(snapshot({'stage': PC_STAGE.TUNNEL, 'tile': SEWER, 'inv_ids': carrying([PC_ITEM.ROPE, 1])}))
        expect(name(tie)).to_be('tie the rope to the sewer grill')
    test('stage 8 buys the rope on the mainland and ties it in the sewer', _fn21)

    def _fn22():
        step = decide(snapshot({'stage': PC_STAGE.TUNNEL}))
        expect(step.kind == 'withdraw' and step.items[0]['name']).to_be(PC_ITEM.COINS.name)
    test('the rope purse is withdrawn before the shop trip', _fn22)

    def _fn23():
        step = decide(snapshot({'stage': PC_STAGE.ROPE_TIED, 'tile': SEWER, 'inv_ids': carrying([PC_ITEM.SPADE, 1])}))
        expect(name(step)).to_be('pull the grill off with Edmond')
    test('a rope carried into the sewer is tied without another shop trip', _fn23)

    def _fn24():
        step = decide(snapshot({'stage': PC_STAGE.ROPE_TIED, 'inv_ids': carrying([PC_ITEM.SPADE, 1])}))
        expect(name(step)).to_be('drop into the Ardougne sewer')
    test('stage 9 on the mainland digs back down rather than talking to the wrong Edmond', _fn24)

    def _fn25():
        expect(name(decide(snapshot({'stage': PC_STAGE.FREED_ELENA})))).to_be('tell Edmond his daughter is safe')
    test('stage 28 reports back to Edmond', _fn25)


describe('plague city decide — East Ardougne', _fn10)


def _fn26():
    def _fn27():
        step = decide(snapshot({'stage': PC_STAGE.PIPE_OPEN, 'bank_ids': {}, 'inv_ids': KIT}))
        expect(name(step)).to_be("take the picture from Edmond's house")
    test('the picture comes off the floor of Edmond house before the crossing', _fn27)

    def _fn28():
        step = decide(snapshot({
        'stage': PC_STAGE.PIPE_OPEN,
        'bank_ids': {},
        'inv_ids': carrying([PC_ITEM.PICTURE, 1], [PC_ITEM.SPADE, 1]),
    }))
        expect(name(step)).to_be("search Alrena's cupboard for the spare gas mask")
    test('a missing gas mask is searched out of the cupboard, never skipped', _fn28)

    def _fn29():
        step = decide(snapshot({
        'stage': PC_STAGE.PIPE_OPEN,
        'bank_ids': {},
        'inv_ids': carrying([PC_ITEM.PICTURE, 1], [PC_ITEM.SPADE, 1]),
        'worn_ids': set([PC_ITEM.GAS_MASK.id]),
    }))
        expect(name(step)).to_be('cross into West Ardougne')
    test('a worn gas mask counts as held', _fn29)

    def _fn30():
        cross = decide(snapshot({'stage': PC_STAGE.PIPE_OPEN, 'inv_ids': {_k: _v for _k, _v in list(KIT.items()) + [[PC_ITEM.PICTURE.id, 1]]}}))
        expect(name(cross)).to_be('cross into West Ardougne')
        ask = decide(snapshot({
        'stage': PC_STAGE.PIPE_OPEN,
        'tile': WEST,
        'inv_ids': {_k: _v for _k, _v in list(KIT.items()) + [[PC_ITEM.PICTURE.id, 1]]},
    }))
        expect(name(ask)).to_be("show Jethick Elena's picture")
    test('the full kit crosses, and Jethick is asked once inside', _fn30)


describe('plague city decide — crossing into West Ardougne', _fn26)


def _fn31():
    def west(stage, inv_ids=None):
        if inv_ids is None:
            inv_ids = {}
        return decide(snapshot({'stage': stage, 'tile': WEST, 'inv_ids': inv_ids}))

    # Stages 20 and 21 render the same journal line, so one leg covers both.
    def _fn32():
        expect(name(west(PC_STAGE.SHOWN_PICTURE, carrying([PC_ITEM.TURNIP_BOOK, 1])))).to_be('get into the Rehnison house and ask about Elena')
        expect(name(west(PC_STAGE.SHOWN_PICTURE))).to_be('get into the Rehnison house and ask about Elena')
    test('stage 20 runs the Rehnison leg with or without the book in the pack', _fn32)

    def _fn33():
        expect(name(west(PC_STAGE.RETURNED_BOOK))).to_be('ask the Rehnisons about Elena')
        expect(name(west(PC_STAGE.SPOKEN_PARENTS))).to_be('ask Milli what she saw')
        expect(name(west(PC_STAGE.SPOKEN_MILLI))).to_be('ask the mourner about the plague house')
    test('stages 21 to 23 walk the Rehnison chain and then the plague house door', _fn33)

    def _fn34():
        expect(name(west(PC_STAGE.NEED_CLEARANCE))).to_be('get an audience with Bravek')
        expect(name(west(PC_STAGE.SPOKEN_CLERK))).to_be('get an audience with Bravek')
    test('both clearance stages run the one clerk-then-Bravek leg', _fn34)

    def _fn35():
        expect(name(west(PC_STAGE.CURED_BRAVEK, carrying([PC_ITEM.WARRANT, 1])))).to_be('free Elena from the plague house')
        expect(name(west(PC_STAGE.CURED_BRAVEK))).to_be('ask Bravek for another warrant')
    test('stage 27 rescues Elena with the warrant and asks for another without one', _fn35)

    def _fn36():
        step = decide(snapshot({
        'stage': PC_STAGE.CURED_BRAVEK,
        'tile': WEST,
        'bank_ids': {_k: _v for _k, _v in [[PC_ITEM.WARRANT.id, 1]]},
    }))
        expect(name(step)).to_be('walk back to East Ardougne')
        east = decide(snapshot({'stage': PC_STAGE.CURED_BRAVEK, 'bank_ids': {_k: _v for _k, _v in [[PC_ITEM.WARRANT.id, 1]]}}))
        expect(east.kind == 'withdraw' and east.items[0]['name']).to_be(PC_ITEM.WARRANT.name)
    test('a banked warrant is withdrawn rather than asked for again', _fn36)

    def _fn37():
        step = decide(snapshot({'stage': PC_STAGE.SHOWN_PICTURE, 'bank_ids': {_k: _v for _k, _v in [[PC_ITEM.TURNIP_BOOK.id, 1]]}}))
        expect(step.kind == 'withdraw' and step.items[0]['name']).to_be(PC_ITEM.TURNIP_BOOK.name)
    test('a banked book is withdrawn rather than asked for again', _fn37)


describe('plague city decide — West Ardougne', _fn31)


def _fn38():
    def cure(inv_ids):
        return decide(snapshot({'stage': PC_STAGE.SPOKEN_BRAVEK, 'inv_ids': inv_ids}))
    MILK = carrying([PC_ITEM.COINS, 2000], [PC_ITEM.BUCKET_MILK, 1])

    def _fn39():
        step = cure({})
        expect(step.kind == 'withdraw' and step.items[0]['name']).to_be(PC_ITEM.COINS.name)
        expect(step.kind == 'withdraw' and step.bank).to_be_undefined()
    test('the shopping float is drawn in Ardougne, before the eastward loop', _fn39)

    def _fn40():
        bucket = cure(carrying([PC_ITEM.COINS, 2000]))
        expect(bucket.kind == 'grab_ground' and bucket.item).to_be(PC_ITEM.BUCKET.name)
        cow = cure(carrying([PC_ITEM.COINS, 2000], [PC_ITEM.BUCKET, 1]))
        expect(cow.kind == 'use_on' and cow.product).to_be(PC_ITEM.BUCKET_MILK.name)
        grass = cure(MILK)
        expect(grass.kind == 'grab_ground' and grass.item).to_be(PC_ITEM.SNAPE_GRASS.name)
        pestle = cure({_k: _v for _k, _v in list(MILK.items()) + [[PC_ITEM.SNAPE_GRASS.id, 1]]})
        expect(pestle.kind == 'buy' and pestle.item).to_be(PC_ITEM.PESTLE.name)
        bar = cure({_k: _v for _k, _v in list(MILK.items()) + [[PC_ITEM.SNAPE_GRASS.id, 1], [PC_ITEM.PESTLE.id, 1]]})
        expect(bar.kind == 'buy' and bar.item).to_be(PC_ITEM.CHOCOLATE_BAR.name)
    test('every raw ingredient is gathered before the first mix', _fn40)

    def _fn41():
        full = {_k: _v for _k, _v in list(MILK.items()) + [[PC_ITEM.SNAPE_GRASS.id, 1], [PC_ITEM.PESTLE.id, 1], [PC_ITEM.CHOCOLATE_BAR.id, 1]]}
        grind = cure(full)
        expect(grind.kind == 'use_on' and grind.product).to_be(PC_ITEM.CHOCOLATE_DUST.name)
        mix = cure(carrying([PC_ITEM.CHOCOLATE_DUST, 1], [PC_ITEM.BUCKET_MILK, 1]))
        expect(mix.kind == 'use_on' and mix.product).to_be(PC_ITEM.CHOCOLATY_MILK.name)
        finish = cure(carrying([PC_ITEM.CHOCOLATY_MILK, 1], [PC_ITEM.SNAPE_GRASS, 1]))
        expect(finish.kind == 'use_on' and finish.product).to_be(PC_ITEM.HANGOVER_CURE.name)
    test('a full ingredient set grinds, mixes and finishes in order', _fn41)

    def _fn42():
        grass = cure(carrying([PC_ITEM.CHOCOLATY_MILK, 1]))
        expect(grass.kind == 'grab_ground' and grass.item).to_be(PC_ITEM.SNAPE_GRASS.name)
        milk = cure(carrying([PC_ITEM.CHOCOLATE_DUST, 1], [PC_ITEM.BUCKET, 1]))
        expect(milk.kind == 'use_on' and milk.product).to_be(PC_ITEM.BUCKET_MILK.name)
    test('a lost ingredient is re-sourced rather than mixed with nothing', _fn42)

    def _fn43():
        step = decide(snapshot({'stage': PC_STAGE.SPOKEN_BRAVEK, 'tile': WEST, 'inv_ids': carrying([PC_ITEM.HANGOVER_CURE, 1])}))
        expect(name(step)).to_be('give Bravek the hangover cure')
    test('a finished cure is carried to Bravek', _fn43)


describe('plague city decide — the hangover cure chain', _fn38)


def _fn44():
    def _fn45():
        expect(plaguecity.record.id).to_be('elena')
        expect(plaguecity.owns_inventory).to_be(True)
        expect(plaguecity.record.items).to_equal([])
        expect(plaguecity.bank).to_equal(Record({'x': 2616, 'z': 3332, 'level': 0}))
    test('it owns its inventory and banks in north Ardougne', _fn45)


describe('plaguecity module', _fn44)
