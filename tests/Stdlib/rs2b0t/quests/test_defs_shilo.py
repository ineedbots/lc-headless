"""rs2b0t's test/api/ai/quests/defs/shilo.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.bank import bank, banking
from rs2004.catalogs.record import Record
from rs2004.items import equipment
from rs2004.quests.defs.shilo import decide, shilo
from rs2004.quests.defs.shilo.areas import SV_ITEM, in_dolmen_room, shilo_area
from rs2004.quests.defs.shilo.gear import combat_gear, reset_combat_gear
from rs2004.quests.defs.shilo.journal import SV_STAGE, parse_shilo_journal
from rs2004.quests.eligibility import evaluate
from rs2004.quests.engine.types import QuestProgress, QuestSnapshot, flag_value, has_flag
from rs2004.quests.exec.steps import execute_step
from rs2004.quests.food import quest_food
from rs2004.quests.gear import quest_loadout

# Why: spec.py restores what stub() set after each test, so only the gear rejections need clearing by hand.
def _fn1():
    stub(quest_loadout, current=None)
    reset_combat_gear()


before_each(_fn1)


def _fn2():
    reset_combat_gear()


after_each(_fn2)


def at(x, z, level=0):
    return (Record({'x': x, 'z': z, 'level': level}))


KARAMJA = at(2809, 3086)
MAINLAND = at(2616, 3332)


def progress(stage, flags=None):
    if flags is None:
        flags = []
    # The parser emits one counted flag of each kind, so defaults are only
    # filled in when the caller has not named its own.
    counted = [key for key in ['bones-placed', 'naza'] if not any([f.startswith(key + ':') for f in flags])]
    return QuestProgress(stage, set([f'{key}:0' for key in counted] + list(flags)))


def option(o, key, fallback):
    value = o.get(key)
    return value if value is not None else fallback


# Why: the overrides are a plain dict, since a Record can't hold the id-keyed maps.
def snapshot(o=None):
    if o is None:
        o = {}
    progress_ = o.get('progress')
    return QuestSnapshot(**{
        'journal': option(o, 'journal', 'in_progress'),
        'inv': option(o, 'inv', {}),
        'inv_ids': option(o, 'inv_ids', {}),
        'worn': option(o, 'worn', set()),
        'worn_ids': option(o, 'worn_ids', set()),
        'no_progress': 0,
        'bank_coins': option(o, 'bank_coins', 0),
        'stage': option(o, 'stage', None if progress_ is None else progress_.stage),
        'progress': progress_,
        'bank': option(o, 'bank', {}),
        'bank_ids': option(o, 'bank_ids', {}),
        'bank_known': option(o, 'bank_known', True),
        'tile': o['tile'] if 'tile' in o else KARAMJA,
        'free_slots': option(o, 'free_slots', 28),
    })


PROVISIONED = {_k: _v for _k, _v in [[SV_ITEM.COINS.id, 5000], [SV_ITEM.BONES.id, 3]]}
FOOD_BANK = {_k: _v for _k, _v in [['lobster', 20]]}


def carrying(*pairs):
    return {_k: _v for _k, _v in list(PROVISIONED.items()) + list(pairs)}


def name(s):
    return ((s.name if s.kind == 'custom' else s.kind))


def withdrawn(s):
    return ((s.items if s.kind == 'withdraw' else None))


def _fn3():
    def _fn4():
        expect(shilo_area(at(2898, 9401))).to_be('ahZaRhoonNorth')
        expect(shilo_area(at(2888, 9283))).to_be('ahZaRhoonSouth')
        expect(shilo_area(at(2760, 9389))).to_be('berviriusTomb')
        expect(shilo_area(at(2929, 9525))).to_be('rashEntry')
        expect(shilo_area(at(2929, 9515))).to_be('rashLedge')
        expect(shilo_area(at(2928, 9511))).to_be('rashInner')
        expect(shilo_area(at(2852, 2954))).to_be('shiloVillage')
    test('classifies each sealed pocket by a tile inside it', _fn4)

    def _fn5():
        # Collapsing it into either neighbour makes the gate open and re-open forever.
        expect(shilo_area(at(2929, 9516))).to_be('rashEntry')
        expect(shilo_area(at(2929, 9515))).to_be('rashLedge')
        expect(shilo_area(at(2928, 9512))).to_be('rashLedge')
        expect(shilo_area(at(2928, 9511))).to_be('rashInner')
        expect(shilo_area(at(2892, 9487))).to_be('rashInner')
        expect(shilo_area(at(2892, 9480))).to_be('rashInner')
    test('the ledge between the gate and the rocks is its own area', _fn5)

    def _fn6():
        expect(shilo_area(at(2921, 2999))).to_be('karamja')
        expect(shilo_area(at(2916, 3090))).to_be('karamja')
        expect(shilo_area(KARAMJA)).to_be('karamja')
        expect(shilo_area(MAINLAND)).to_be('karamja')
    test('the east jungle and Tai Bwo Wannai are one open region', _fn6)

    def _fn7():
        expect(shilo_area(None)).to_be('unknown')
        expect(shilo_area(None)).to_be('unknown')
    test('a null tile is unknown, never a default area', _fn7)


describe('shiloArea', _fn3)


def _fn8():
    def _fn9():
        expect((parse_shilo_journal('@dbl@I can start this quest by speaking to @dre@Mosol Rei@dbl@').stage if parse_shilo_journal('@dbl@I can start this quest by speaking to @dre@Mosol Rei@dbl@') is not None else None)).to_be(SV_STAGE.NOT_STARTED)
    test('not started', _fn9)

    def _fn10():
        expect((parse_shilo_journal('@red@QUEST COMPLETE!').stage if parse_shilo_journal('@red@QUEST COMPLETE!') is not None else None)).to_be(SV_STAGE.COMPLETE)
    test('complete', _fn10)

    def _fn11():
        p = parse_shilo_journal([
        '@str@I spoke to Mosol Rei in South Karamja, and have agreed to|',
        "@str@help his village. He gave me a 'Wampum belt'.|",
        "|@dbl@I need to find the location of '@dre@Ah Za Rhoon@dbl@'.",
    ])
        expect((p.stage if p is not None else None)).to_be(SV_STAGE.STARTED)
    test('started, looking for Ah Za Rhoon', _fn11)

    def _fn12():
        found = ["@str@I need to find the location of 'Ah Za Rhoon'.|"]
        expect((parse_shilo_journal(list(found) + ["@dbl@I've found a @dre@mound of earth@dbl@ in the jungle which seems curious."]).stage if parse_shilo_journal(list(found) + ["@dbl@I've found a @dre@mound of earth@dbl@ in the jungle which seems curious."]) is not None else None)).to_be(SV_STAGE.SEARCHED_MOUND)
        expect((parse_shilo_journal(list(found) + ["@str@I've found a mound of earth in the jungle which seems|", "@str@curious. I've used a spade to excavate the mound of earth.|"]).stage if parse_shilo_journal(list(found) + ["@str@I've found a mound of earth in the jungle which seems|", "@str@curious. I've used a spade to excavate the mound of earth.|"]) is not None else None)).to_be(SV_STAGE.DUG_MOUND)
        expect((parse_shilo_journal(list(found) + ["@str@I've used a spade to excavate the mound of earth.|", '@str@I illuminated the fissure and saw it was a long way down.|']).stage if parse_shilo_journal(list(found) + ["@str@I've used a spade to excavate the mound of earth.|", '@str@I illuminated the fissure and saw it was a long way down.|']) is not None else None)).to_be(SV_STAGE.LIT_MOUND)
        expect((parse_shilo_journal(list(found) + ['@str@I illuminated the fissure and saw it was a long way down.|', '@str@I attached a rope to the start of the fissure.|']).stage if parse_shilo_journal(list(found) + ['@str@I illuminated the fissure and saw it was a long way down.|', '@str@I attached a rope to the start of the fissure.|']) is not None else None)).to_be(SV_STAGE.ROPED_MOUND)
    test('each mound step outranks the history above it', _fn12)

    def _fn13():
        p = parse_shilo_journal([
        '@str@I climbed down the rope into some sort of underground cavern|',
        '@str@system, I need to identify this place.|',
        "@str@I've read the tattered scroll, it gives details about Bervirius|",
        "@str@who was Rashiliyia's son.|",
    ])
        expect((p.stage if p is not None else None)).to_be(SV_STAGE.ENTERED_AH_ZA_RHOON)
        expect(has_flag(p, 'read-tattered')).to_be(True)
        expect(has_flag(p, 'read-crumpled')).to_be(False)
        expect(has_flag(p, 'pommel-taken')).to_be(False)
    test('the cavern block reports which scrolls have been read', _fn13)

    def _fn14():
        p = parse_shilo_journal([
        '@str@I climbed down the rope into some sort of underground cavern|',
        '@str@I searched the dolmen in Bervirius tomb and found a crystal,|',
        '@str@some notes and a bone sword pommel.|',
    ])
        expect((p.stage if p is not None else None)).to_be(SV_STAGE.ENTERED_AH_ZA_RHOON)
        expect(has_flag(p, 'pommel-taken')).to_be(True)
    test('searching the Bervirius dolmen is the pommel flag, and does not move the stage', _fn14)

    def _fn15():
        p = parse_shilo_journal([
        '@str@I climbed down the rope into some sort of underground cavern|',
        '@str@I searched the dolmen in Bervirius tomb and found a crystal,|',
        "@str@I've found a door in the jungle to the North of Ah Za Rhoon|",
        '@str@which I cannot get past. The lock is made out of bone!|',
    ])
        expect(has_flag(p, 'found-door')).to_be(True)
        expect((p.stage if p is not None else None)).to_be(SV_STAGE.ENTERED_AH_ZA_RHOON)
    test('the bone lock line is the found-door flag', _fn15)

    def _fn16():
        p = parse_shilo_journal([
        "@str@I've found a door in the jungle to the North of Ah Za Rhoon|",
        '@str@which I cannot get past. The lock is made out of bone! I|',
        '@str@made a bone key from the bone shard that Zadimus gave|',
        '@str@me and I managed to get past the door.|',
    ])
        expect((p.stage if p is not None else None)).to_be(SV_STAGE.UNLOCKED_RASH_TOMB)
    test('the bone key line moves the stage past the carved doors', _fn16)

    def _fn17():
        one = parse_shilo_journal([
        '@str@I made a bone key from the bone shard that Zadimus gave|',
        "@dbl@I've placed one @dre@bone@dbl@ in one of the @dre@recesses@dbl@.|",
    ])
        expect((one.stage if one is not None else None)).to_be(SV_STAGE.UNLOCKED_RASH_TOMB)
        expect(flag_value(one, 'bones-placed')).to_be(1)
        two = parse_shilo_journal([
        '@str@I made a bone key from the bone shard that Zadimus gave|',
        "@dbl@I've placed two @dre@bones@dbl@ in the door @dre@recesses@dbl@.|",
    ])
        expect(flag_value(two, 'bones-placed')).to_be(2)
        three = parse_shilo_journal(["@str@I've placed three bones in each of the|", '@str@recesses this seemed to unlock the door.|'])
        expect((three.stage if three is not None else None)).to_be(SV_STAGE.UNLOCKED_TOMBDOOR)
        expect(flag_value(three, 'bones-placed')).to_be(3)
    test('partial bone placements are counted', _fn17)

    def _fn18():
        base = ["@str@I've placed three bones in each of the recesses.|"]
        expect(flag_value(parse_shilo_journal(base), 'naza')).to_be(0)
        expect(flag_value(parse_shilo_journal(list(base) + ['@str@a Zombie Nazastarool attacked me. I managed to slay the|']), 'naza')).to_be(1)
        expect(flag_value(parse_shilo_journal(list(base) + ['@str@a Zombie Nazastarool attacked me which I slayed. A skeletal|', '@str@Nazastarool appeared after this but I managed to slay this|']), 'naza')).to_be(2)
        expect(flag_value(parse_shilo_journal(list(base) + ['@str@The third and final guardian was a ghostly Nazastarool and|', '@str@after an epic battle, I defeated it.|']), 'naza')).to_be(3)
    test('the kill paragraphs are cumulative rewrites, so the newest wins', _fn18)

    def _fn19():
        expect(parse_shilo_journal('some other quest entirely')).to_be_undefined()
    test('unrecognised text yields nothing rather than a guess', _fn19)


describe('parseShiloJournal', _fn8)


def _fn20():
    def _fn21():
        expect(decide(snapshot(({'journal': 'complete'}))).kind).to_be('done')
    test('a complete journal in the open is done', _fn21)

    def _fn22():
        expect(decide(snapshot(({'stage': SV_STAGE.COMPLETE}))).kind).to_be('done')
    test('stage 15 is done even before the journal colour catches up', _fn22)

    def _fn23():
        step = decide(snapshot(({'journal': 'complete', 'tile': at(2929, 9525)})))
        expect(step.kind).to_be('custom')
        expect(name(step)).to_contain('exit')
    test('completing inside the tomb still climbs out first', _fn23)

    def _fn24():
        expect(decide(snapshot(({'journal': 'unknown'}))).kind).to_be('wait')
    test('an unloaded journal waits — it is not notStarted', _fn24)

    def _fn25():
        expect(decide(snapshot(({'stage': None}))).kind).to_be('wait')
    test('a missing stage waits rather than guessing', _fn25)

    def _fn26():
        expect(decide(snapshot(({'stage': SV_STAGE.STARTED, 'tile': None}))).kind).to_be('wait')
    test('an unknown location waits rather than acting on a guess', _fn26)


describe('shilo decide — terminal cases', _fn20)


def _fn27():
    def _fn28():
        step = decide(snapshot(({'journal': 'not_started', 'stage': SV_STAGE.NOT_STARTED, 'tile': MAINLAND})))
        expect(step.kind).to_be('wait')
        expect(step.kind == 'wait' and step.reason).to_contain('gp')
    test('on the mainland with an empty bank, it parks honestly rather than crossing', _fn28)

    def _fn29():
        step = decide(snapshot(({
        'journal': 'not_started',
        'stage': SV_STAGE.NOT_STARTED,
        'tile': MAINLAND,
        'bank_ids': {_k: _v for _k, _v in [[SV_ITEM.COINS.id, 2000000]]},
    })))
        expect(step.kind).to_be('withdraw')
    test('on the mainland it fills the purse before the crossing', _fn29)

    def _fn30():
        step = decide(snapshot(({
        'journal': 'not_started',
        'stage': SV_STAGE.NOT_STARTED,
        'tile': MAINLAND,
        'inv_ids': {_k: _v for _k, _v in [[SV_ITEM.COINS.id, 5000]]},
    })))
        expect(name(step)).to_contain('bones')
    test('on the mainland with coins but no bones, it fetches the bones', _fn30)

    def _fn31():
        step = decide(snapshot(({
        'journal': 'not_started',
        'stage': SV_STAGE.NOT_STARTED,
        'tile': MAINLAND,
        'inv_ids': {_k: _v for _k, _v in PROVISIONED.items()},
        'bank': FOOD_BANK,
    })))
        expect(withdrawn(step)).to_equal([Record({'name': 'Lobster', 'qty': 8})])
    test('on the mainland it takes the food float along with the coins and bones', _fn31)

    def _fn32():
        step = decide(snapshot(({
        'journal': 'not_started',
        'stage': SV_STAGE.NOT_STARTED,
        'tile': MAINLAND,
        'inv_ids': {_k: _v for _k, _v in PROVISIONED.items()},
    })))
        expect(name(step)).to_contain('Mosol Rei')
    test('an empty larder never holds up the legs before the tomb', _fn32)

    def _fn33():
        step = decide(snapshot(({'journal': 'not_started', 'stage': SV_STAGE.NOT_STARTED, 'tile': KARAMJA})))
        expect(name(step)).to_contain('Mosol Rei')
    test('once on Karamja it never walks back for supplies', _fn33)


describe('shilo decide — provisioning', _fn27)


def _fn34():
    def _fn35():
        expect(name(decide(snapshot(({'journal': 'not_started', 'stage': SV_STAGE.NOT_STARTED, 'inv_ids': PROVISIONED}))))).to_contain('Mosol Rei')
    test('not started asks Mosol Rei for the belt', _fn35)

    def _fn36():
        expect(name(decide(snapshot(({'journal': 'not_started', 'stage': SV_STAGE.NOT_STARTED, 'inv_ids': carrying([SV_ITEM.WAMPUM_BELT.id, 1])}))))).to_contain('Trufitus')
    test('holding the belt shows it to Trufitus instead', _fn36)

    def _fn37():
        step = decide(snapshot(({
        'journal': 'not_started',
        'stage': SV_STAGE.NOT_STARTED,
        'inv_ids': PROVISIONED,
        'bank_ids': {_k: _v for _k, _v in [[SV_ITEM.WAMPUM_BELT.id, 1]]},
    })))
        expect(step.kind).to_be('withdraw')
    test('a belt left in the bank is withdrawn, not asked for again', _fn37)


describe('shilo decide — the opening', _fn34)


def _fn38():
    def _fn39():
        step = decide(snapshot(({'progress': progress(SV_STAGE.STARTED), 'inv_ids': PROVISIONED})))
        expect(step.kind).to_be('custom')
        # Everything the rest of the quest needs from a shop, not one item per crossing.
        for want in ['Spade', 'Candle', 'Tinderbox', 'Rope', 'Chisel', 'Bronze bar', 'Hammer']:
            expect(name(step)).to_contain(want)
    test('an empty pack buys the whole outstanding kit in one Jiminua trip', _fn39)
    KIT = [
        [SV_ITEM.SPADE.id, 1],
        [SV_ITEM.CANDLE.id, 1],
        [SV_ITEM.TINDERBOX.id, 1],
        [SV_ITEM.ROPE.id, 1],
        [SV_ITEM.CHISEL.id, 1],
        [SV_ITEM.BRONZE_BAR.id, 1],
        [SV_ITEM.HAMMER.id, 1],
    ]

    def _fn40():
        step = decide(snapshot(({'progress': progress(SV_STAGE.STARTED), 'inv_ids': carrying(*KIT)})))
        expect(name(step)).to_contain('dig')
    test('with the kit it digs', _fn40)

    def _fn41():
        no_candle = decide(snapshot(({'progress': progress(SV_STAGE.DUG_MOUND), 'inv_ids': PROVISIONED})))
        expect(name(no_candle)).to_contain('Candle')
        expect(name(no_candle)).to_contain('Tinderbox')
        both = decide(snapshot(({'progress': progress(SV_STAGE.DUG_MOUND), 'inv_ids': carrying(*KIT)})))
        expect(name(both)).to_be('light the candle')
        lit = decide(snapshot(({'progress': progress(SV_STAGE.DUG_MOUND), 'inv_ids': carrying(*KIT, [SV_ITEM.LIT_CANDLE.id, 1])})))
        expect(name(lit)).to_contain('fissure')
    test('the light source is bought unlit and lit with a tinderbox', _fn41)

    def _fn42():
        expect(name(decide(snapshot(({'progress': progress(SV_STAGE.LIT_MOUND), 'inv_ids': PROVISIONED}))))).to_contain('Rope')
        expect(name(decide(snapshot(({'progress': progress(SV_STAGE.LIT_MOUND), 'inv_ids': carrying(*KIT)}))))).to_contain('rope')
    test('the rope is bought before the fissure is tied', _fn42)

    def _fn43():
        expect(name(decide(snapshot(({'progress': progress(SV_STAGE.ROPED_MOUND), 'inv_ids': PROVISIONED}))))).to_contain('climb down the fissure')
    test('roped, it climbs in', _fn43)


describe('shilo decide — the mound', _fn38)


def _fn44():
    def middle(flags, ids=None, tile=None):
        if ids is None:
            ids = []
        if tile is None:
            tile = KARAMJA
        return decide(snapshot(({'progress': progress(SV_STAGE.ENTERED_AH_ZA_RHOON, flags), 'inv_ids': carrying(*ids), 'tile': tile})))

    def _fn45():
        expect(name(middle([]))).to_contain('tattered scroll')
        expect(name(middle([], [[SV_ITEM.TATTERED_SCROLL.id, 1]]))).to_be('read the tattered scroll')
    test('the tattered scroll is fetched, then read', _fn45)

    def _fn46():
        expect(name(middle(['read-tattered']))).to_contain('old sacks')
        expect(name(middle(['read-tattered'], [[SV_ITEM.CRUMPLED_SCROLL.id, 1]]))).to_be('read the crumpled scroll')
    test('the crumpled scroll follows, then read', _fn46)

    def _fn47():
        both = ['read-tattered', 'read-crumpled']
        expect(name(middle(both))).to_contain('gallows')
        expect(name(middle(both, [[SV_ITEM.ZADIMUS_CORPSE.id, 1]]))).to_contain('bury Zadimus')
    test('the gallows corpse is buried on the sacred ground', _fn47)

    def _fn48():
        step = middle(['read-tattered', 'read-crumpled'], [[SV_ITEM.BONE_SHARD.id, 1]])
        expect(name(step)).to_contain("Bervirius' tomb")
    test('with the shard in hand it goes for the Bervirius dolmen', _fn48)

    def _fn49():
        step = middle(['read-tattered', 'read-crumpled', 'pommel-taken'], [], at(2898, 9401))
        expect(name(step)).to_contain('climb out of Ah Za Rhoon')
    test('inside the caves it climbs out before any of the mainland crafts', _fn49)

    def _fn50():
        step = middle(['read-tattered', 'read-crumpled', 'pommel-taken'], [[SV_ITEM.SWORD_POMMEL.id, 1]])
        expect(name(step)).to_contain('carved doors')
    test('after the pommel it searches the carved doors for the lock', _fn50)

    def _fn51():
        flags = ['read-tattered', 'read-crumpled', 'pommel-taken', 'found-door']
        # One trip: the chisel cuts both, and the bar and hammer are the wire.
        no_chisel = middle(flags, [[SV_ITEM.BONE_SHARD.id, 1], [SV_ITEM.SWORD_POMMEL.id, 1]])
        for want in ['Chisel', 'Bronze bar', 'Hammer']:
            expect(name(no_chisel)).to_contain(want)
        CRAFT = [[SV_ITEM.CHISEL.id, 1], [SV_ITEM.BRONZE_BAR.id, 1], [SV_ITEM.HAMMER.id, 1]]
        key = middle(flags, list(CRAFT) + [[SV_ITEM.BONE_SHARD.id, 1], [SV_ITEM.SWORD_POMMEL.id, 1]])
        expect(name(key)).to_contain('bone shard into a key')
        beads = middle(flags, list(CRAFT) + [[SV_ITEM.BONE_KEY.id, 1], [SV_ITEM.SWORD_POMMEL.id, 1]])
        expect(name(beads)).to_contain('ivory pommel')
    test('the key comes before the necklace, and both need a chisel', _fn51)

    def _fn52():
        flags = ['read-tattered', 'read-crumpled', 'pommel-taken', 'found-door']
        no_bar = middle(flags, [[SV_ITEM.CHISEL.id, 1], [SV_ITEM.BONE_KEY.id, 1], [SV_ITEM.BONE_BEADS.id, 1]])
        expect(name(no_bar)).to_contain('Bronze bar')
        expect(name(no_bar)).to_contain('Hammer')
        bar = middle(flags, [
        [SV_ITEM.CHISEL.id, 1],
        [SV_ITEM.BONE_KEY.id, 1],
        [SV_ITEM.BONE_BEADS.id, 1],
        [SV_ITEM.BRONZE_BAR.id, 1],
        [SV_ITEM.HAMMER.id, 1],
    ])
        expect(name(bar)).to_contain('smith the bronze bar')
    test('the necklace needs bronze wire, which is smithed rather than bought', _fn52)

    def _fn53():
        step = middle(['read-tattered', 'read-crumpled', 'pommel-taken', 'found-door'], [[SV_ITEM.BONE_KEY.id, 1], [SV_ITEM.DEAD_BEADS.id, 1]])
        expect(name(step)).to_contain('unlock the carved doors')
    test('with the key and the beads it unlocks the carved doors', _fn53)


describe('shilo decide — Ah Za Rhoon and the crafts', _fn44)


def _fn54():
    def tomb(ids, tile=None, worn_ids=None, flags=None):
        if tile is None:
            tile = KARAMJA
        if worn_ids is None:
            worn_ids = []
        if flags is None:
            flags = []
        return decide(snapshot(({
            'progress': progress(SV_STAGE.UNLOCKED_RASH_TOMB, flags),
            'inv_ids': carrying(*ids),
            'worn_ids': set(worn_ids),
            'bank': FOOD_BANK,
            'tile': tile,
        })))

    def _fn55():
        step = tomb([[SV_ITEM.BONE_KEY.id, 1], [SV_ITEM.DEAD_BEADS.id, 1]])
        expect(step.kind).to_be('equip')
        expect(step.kind == 'equip' and step.item).to_be('Beads of the dead')
    test('the beads go on before the tomb is entered', _fn55)

    def _fn56():
        food = tomb([[SV_ITEM.BONE_KEY.id, 1]], KARAMJA, [SV_ITEM.DEAD_BEADS.id])
        expect(withdrawn(food)).to_equal([Record({'name': 'Lobster', 'qty': 8})])
        inv = {_k: _v for _k, _v in list(PROVISIONED.items()) + [[SV_ITEM.BONE_KEY.id, 1]]}
        step = decide(snapshot(({
        'progress': progress(SV_STAGE.UNLOCKED_RASH_TOMB),
        'inv_ids': inv,
        'inv': {_k: _v for _k, _v in [['lobster', 8]]},
        'bank': FOOD_BANK,
        'worn_ids': set([SV_ITEM.DEAD_BEADS.id]),
        'tile': KARAMJA,
    })))
        expect(name(step)).to_contain("enter Rashiliyia's tomb")
    test('wearing them, it draws the float and enters', _fn56)

    def _fn57():
        step = tomb([[SV_ITEM.BONE_KEY.id, 1]], at(2929, 9525), [SV_ITEM.DEAD_BEADS.id])
        expect(name(step)).to_contain('ancient gate')
    test('in the entry corridor it opens the ancient gate', _fn57)

    def _fn58():
        step = tomb([[SV_ITEM.BONE_KEY.id, 1]], at(2929, 9515), [SV_ITEM.DEAD_BEADS.id])
        expect(name(step)).to_contain('climb down')
    test('on the ledge past the gate it climbs down, never re-opens the gate', _fn58)

    def _fn59():
        step = tomb([[SV_ITEM.BONE_KEY.id, 1]], at(2892, 9482), [SV_ITEM.DEAD_BEADS.id])
        expect(name(step)).to_contain('place a bone')
    test('in the chamber it feeds the door one bone at a time', _fn59)

    def _fn60():
        step = decide(snapshot(({
        'progress': progress(SV_STAGE.UNLOCKED_RASH_TOMB),
        'inv_ids': {_k: _v for _k, _v in [[SV_ITEM.COINS.id, 5000], [SV_ITEM.BONE_KEY.id, 1]]},
        'worn_ids': set([SV_ITEM.DEAD_BEADS.id]),
        'tile': at(2892, 9479),
    })))
        expect(name(step)).to_contain('leave the tomb chamber')
    test('short of bones inside the tomb, it leaves rather than looping at the door', _fn60)

    def _fn61():
        step = decide(snapshot(({
        'progress': progress(SV_STAGE.UNLOCKED_RASH_TOMB, ['bones-placed:3']),
        'inv_ids': {_k: _v for _k, _v in [[SV_ITEM.COINS.id, 5000], [SV_ITEM.BONE_KEY.id, 1]]},
        'worn_ids': set([SV_ITEM.DEAD_BEADS.id]),
        'tile': at(2892, 9482),
    })))
        expect(step.kind).to_be('wait')
    test('all three placed, it waits — the third bone opens the doors itself', _fn61)

    def _fn62():
        step = decide(snapshot(({
        'progress': progress(SV_STAGE.UNLOCKED_TOMBDOOR),
        'inv_ids': carrying(),
        'worn_ids': set([SV_ITEM.DEAD_BEADS.id]),
        'tile': at(2892, 9480),
    })))
        expect(name(step)).to_contain('tomb dolmen')
    test('pushed south of the doors, the dolmen step crosses back on its own', _fn62)


describe('shilo decide — the tomb', _fn54)


def _fn63():
    def _fn64():
        step = decide(snapshot(({
        'progress': progress(SV_STAGE.UNLOCKED_TOMBDOOR),
        'inv_ids': carrying(),
        'worn_ids': set([SV_ITEM.DEAD_BEADS.id]),
        'tile': at(2892, 9487),
    })))
        expect(name(step)).to_contain('tomb dolmen')
    test('in the chamber it works the dolmen, which summons or yields', _fn64)

    def _fn65():
        gate = decide(snapshot(({
        'progress': progress(SV_STAGE.UNLOCKED_TOMBDOOR),
        'inv_ids': carrying(),
        'worn_ids': set([SV_ITEM.DEAD_BEADS.id]),
        'tile': at(2929, 9525),
    })))
        expect(name(gate)).to_contain('ancient gate')
        ledge = decide(snapshot(({
        'progress': progress(SV_STAGE.UNLOCKED_TOMBDOOR),
        'inv_ids': carrying(),
        'worn_ids': set([SV_ITEM.DEAD_BEADS.id]),
        'tile': at(2929, 9515),
    })))
        expect(name(ledge)).to_contain('climb down')
    test('in the entry corridor it passes the gate; on the ledge it climbs down', _fn65)

    def _fn66():
        inside = decide(snapshot(({
        'progress': progress(SV_STAGE.UNLOCKED_TOMBDOOR),
        'inv_ids': carrying([SV_ITEM.RASH_CORPSE.id, 1]),
        'worn_ids': set([SV_ITEM.DEAD_BEADS.id]),
        'tile': at(2892, 9487),
    })))
        expect(name(inside)).to_contain('leave the tomb chamber')
        outside = decide(snapshot(({
        'progress': progress(SV_STAGE.UNLOCKED_TOMBDOOR),
        'inv_ids': carrying([SV_ITEM.RASH_CORPSE.id, 1]),
        'worn_ids': set([SV_ITEM.DEAD_BEADS.id]),
        'tile': KARAMJA,
    })))
        expect(name(outside)).to_contain("Bervirius' dolmen")
    test('holding the remains it climbs out and delivers them to Bervirius', _fn66)

    def _fn67():
        step = decide(snapshot(({
        'progress': progress(SV_STAGE.UNLOCKED_TOMBDOOR),
        'inv_ids': carrying(),
        'bank_ids': {_k: _v for _k, _v in [[SV_ITEM.RASH_CORPSE.id, 1]]},
        'tile': KARAMJA,
    })))
        expect(step.kind).to_be('withdraw')
    test('remains left in the bank are withdrawn rather than re-fought', _fn67)


describe('shilo decide — the boss and the ending', _fn63)


def _fn68():
    def _fn69():
        expect(shilo.owns_inventory).to_be(True)
    test('it owns its inventory — Karamja has no bank until this quest opens one', _fn69)

    def _fn70():
        expect(shilo.bank).to_match_object(Record({'x': 2616, 'z': 3332}))
    test('it banks at Ardougne West, the nearest bank to the Brimhaven ship', _fn70)

    def _fn71():
        expect(shilo.record.requirements.quests).to_equal(['junglepotion'])
    test('the record carries the Jungle Potion prerequisite the engine enforces', _fn71)

    def _fn72():
        expect(shilo.record.items).to_equal([])
    test('the record names no mustHave items — the module buys its own kit', _fn72)

    def _fn73():
        expect(SV_ITEM.RASH_CORPSE.name).to_be('Rashiliya corpse')
        expect(SV_ITEM.DEAD_BEADS.name).to_be('Beads of the dead')
    test('the engine names that differ from the wiki are recorded exactly', _fn73)


describe('shilo module', _fn68)


def _fn74():
    def _fn75():
        # The doors stay unlocked, and the tomb exit refuses to open for anyone
        # still carrying the key, so a replacement would be a wasted trip.
        step = decide(snapshot(({
        'progress': progress(SV_STAGE.UNLOCKED_RASH_TOMB),
        'inv_ids': carrying([SV_ITEM.CHISEL.id, 1]),
        'worn_ids': set([SV_ITEM.DEAD_BEADS.id]),
        'tile': KARAMJA,
    })))
        expect(name(step)).not_.to_contain('bone shard')
        expect(name(step)).not_.to_contain('gallows')
    test('past the carved doors it never re-cuts a lost bone key', _fn75)

    def _fn76():
        step = decide(snapshot(({
        'progress': progress(SV_STAGE.ENTERED_AH_ZA_RHOON, ['read-tattered', 'read-crumpled', 'pommel-taken', 'found-door']),
        'inv_ids': carrying([SV_ITEM.CHISEL.id, 1], [SV_ITEM.BRONZE_BAR.id, 1], [SV_ITEM.HAMMER.id, 1]),
        'tile': KARAMJA,
    })))
        expect(name(step)).to_contain('gallows')
    test('before the carved doors a lost key is re-cut', _fn76)


describe('shilo decide — recovery', _fn74)


def _fn77():
    def _fn78():
        # searchBerviriusDolmen crawls in on its own; escaping unconditionally would
        # climb straight back out of the tomb it entered, forever.
        step = decide(snapshot(({
        'progress': progress(SV_STAGE.ENTERED_AH_ZA_RHOON, ['read-tattered', 'read-crumpled']),
        'inv_ids': carrying([SV_ITEM.BONE_SHARD.id, 1]),
        'tile': at(2765, 9370),
    })))
        expect(name(step)).to_contain('search the dolmen')
    test("standing in Bervirius' tomb it searches the dolmen, it does not climb out", _fn78)

    def _fn79():
        step = decide(snapshot(({
        'progress': progress(SV_STAGE.UNLOCKED_TOMBDOOR),
        'inv_ids': carrying([SV_ITEM.RASH_CORPSE.id, 1]),
        'tile': at(2765, 9370),
    })))
        expect(name(step)).to_contain('lay the remains')
    test("delivering the remains works from inside Bervirius' tomb too", _fn79)

    def _fn80():
        step = decide(snapshot(({
        'progress': progress(SV_STAGE.UNLOCKED_TOMBDOOR),
        'inv_ids': carrying([SV_ITEM.RASH_CORPSE.id, 1]),
        'tile': at(2892, 9487),
    })))
        expect(name(step)).to_contain('leave the tomb chamber')
    test('from any other pocket it still escapes first', _fn80)


describe('shilo decide — pockets a step enters itself', _fn77)


def _fn81():
    def ready_for_tomb(food, bank=None):
        if bank is None:
            bank = FOOD_BANK
        return decide(snapshot(({
            'progress': progress(SV_STAGE.UNLOCKED_RASH_TOMB),
            'inv_ids': carrying([SV_ITEM.BONE_KEY.id, 1]),
            'inv': {_k: _v for _k, _v in [['lobster', food]]},
            'bank': bank,
            'worn_ids': set([SV_ITEM.DEAD_BEADS.id]),
            'tile': KARAMJA,
        })))

    def _fn82():
        expect(withdrawn(ready_for_tomb(0))).to_equal([Record({'name': 'Lobster', 'qty': 8})])
    test('an empty pack draws food before the tomb', _fn82)

    def _fn83():
        expect(name(ready_for_tomb(4))).to_contain("enter Rashiliyia's tomb")
    test('four is enough to go in, a top-up is a return crossing', _fn83)

    def _fn84():
        chosen = quest_food.name
        quest_food.name = 'Shark'
        try:
            step = ready_for_tomb(0, {_k: _v for _k, _v in [['lobster', 20], ['shark', 20]]})
            expect(withdrawn(step)).to_equal([Record({'name': 'Shark', 'qty': 8})])
        except Exception as e:
            quest_food.name = chosen
            raise e
        quest_food.name = chosen
    test('the food the script was given wins over the fallbacks', _fn84)

    def _fn85():
        step = ready_for_tomb(0, {})
        expect(step.kind).to_be('wait')
        expect(step.kind == 'wait' and step.reason).to_contain('no food')
    test('a bank with none of it waits at the door rather than entering', _fn85)

    def _fn86():
        expect(withdrawn(ready_for_tomb(0, {_k: _v for _k, _v in [['tuna', 3]]}))).to_equal([Record({'name': 'Tuna', 'qty': 3})])
    test('it draws what the bank has when that is short of the float', _fn86)


describe('shilo decide — the tomb larder', _fn81)


def _fn87():
    def _fn88():
        # It runs up to z=9511 on the *southern* side, so a plain z test would put
        # the foot of the climbing rocks behind the doors.
        expect(in_dolmen_room(at(2928, 9511))).to_be(False)
        expect(in_dolmen_room(at(2892, 9479))).to_be(False)
        expect(in_dolmen_room(at(2892, 9480))).to_be(False)
    test('the corridor east of the skeletal doors is not the dolmen room', _fn88)

    def _fn89():
        expect(in_dolmen_room(at(2892, 9481))).to_be(True)
        expect(in_dolmen_room(at(2891, 9487))).to_be(True)
        expect(in_dolmen_room(at(2892, 9482))).to_be(True)
    test('the room itself, from the door landing to the dolmen', _fn89)

    def _fn90():
        expect(in_dolmen_room(None)).to_be(False)
        expect(in_dolmen_room(None)).to_be(False)
    test('a null tile is never in the room', _fn90)


describe('inDolmenRoom', _fn87)


def _fn91():
    def _fn92():
        # The engine enforces this twice, Mosol Rei will not hand over the belt and
        # Trufitus will not take it, so the queue must not offer Shilo first.
        maxed = {_k: _v for _k, _v in [[s, 99] for s in ['crafting', 'agility', 'smithing', 'mining']]}
        player = Record({'quest_points': 20, 'skill_levels': maxed, 'completed_quests': set()})
        items = Record({'counts': {}})
        blocked = evaluate(shilo.record, player, items, 'not_started')
        expect(blocked.status).to_be('BLOCKED')
        expect(' '.join(blocked.reasons)).to_contain('junglepotion')
        _merged93 = {}
        for _k, _v in (player._fields if isinstance(player, Record) else player).items():
            _merged93[_k] = _v
        for _k, _v in {'completed_quests': set(['junglepotion'])}.items():
            _merged93[_k] = _v
        ready = evaluate(shilo.record, Record(_merged93), items, 'not_started')
        expect(ready.status).to_be('READY')
    test('Shilo Village is blocked until Jungle Potion is complete', _fn92)


describe('shilo eligibility', _fn91)


def _fn94():
    def _fn95():
        s = snapshot(({
        'progress': progress(SV_STAGE.ROPED_MOUND),
        'inv_ids': carrying(),
        'bank': {_k: _v for _k, _v in [['steel scimitar', 1], ['steel chainbody', 1]]},
    }))
        expect(withdrawn(decide(s))).to_equal([Record({'name': 'Steel scimitar', 'qty': 1}), Record({'name': 'Steel chainbody', 'qty': 1})])
    test('withdraws a banked weapon and armour before entering Ah Za Rhoon', _fn95)

    def _fn96():
        s = snapshot(({
        'progress': progress(SV_STAGE.ENTERED_AH_ZA_RHOON),
        'inv_ids': carrying([SV_ITEM.TATTERED_SCROLL.id, 1]),
        'inv': {_k: _v for _k, _v in [['steel scimitar', 1]]},
        'tile': at(2898, 9401),
    }))
        expect(name(decide(s))).to_contain('wear Steel scimitar')
    test('equips carried gear before reading scrolls in the cave', _fn96)

    def _fn97():
        s = snapshot(({
        'progress': progress(SV_STAGE.ENTERED_AH_ZA_RHOON),
        'inv_ids': carrying([SV_ITEM.TATTERED_SCROLL.id, 1]),
        'bank': {_k: _v for _k, _v in [['steel scimitar', 1]]},
        'tile': at(2898, 9401),
    }))
        expect(name(decide(s))).to_be('climb out of Ah Za Rhoon')
    test('leaves the cave before retrieving banked gear', _fn97)

    def _fn98():
        s = snapshot(({
        'progress': progress(SV_STAGE.ENTERED_AH_ZA_RHOON),
        'inv_ids': carrying([SV_ITEM.TATTERED_SCROLL.id, 1]),
        'bank': {_k: _v for _k, _v in [['steel scimitar', 1]]},
        'worn': set(['rune scimitar', 'beads of the dead']),
    }))
        expect(name(decide(s))).to_be('read the tattered scroll')
    test('keeps an equipped weapon and the Beads of the dead', _fn98)


describe('Shilo combat provisioning', _fn94)


def _fn99():
    s = snapshot(({
        'progress': progress(SV_STAGE.ENTERED_AH_ZA_RHOON),
        'inv_ids': carrying([SV_ITEM.TATTERED_SCROLL.id, 1]),
        'bank': {_k: _v for _k, _v in [['steel kiteshield', 1]]},
        'worn': set(['rune 2h sword']),
    }))
    expect(name(decide(s))).to_be('read the tattered scroll')


test('Shilo keeps a two-handed weapon equipped when a shield is banked', _fn99)


def _fn100():
    s = snapshot(({
        'progress': progress(SV_STAGE.ENTERED_AH_ZA_RHOON),
        'inv': {_k: _v for _k, _v in [['steel scimitar', 1]]},
        'bank': {_k: _v for _k, _v in [['rune scimitar', 1]]},
        'free_slots': 0,
    }))
    expect(name(decide(s))).to_be('wear Steel scimitar')


test('Shilo equips carried gear before withdrawing a higher banked tier into a full pack', _fn100)


def refuse_equip(name):
    return False
    yield


def open_bank(*_args, **_kwargs):
    return True
    yield


def _fn101():
    spy_on(equipment, 'contains', returns=False)
    spy_on(equipment, 'equip', impl=refuse_equip)
    s = snapshot(({
        'inv': {_k: _v for _k, _v in [['rune scimitar', 1], ['tattered scroll', 1]]},
        'bank': {_k: _v for _k, _v in [['steel scimitar', 1]]},
        'free_slots': 0,
    }))
    first = combat_gear(s)
    expect((first.kind if first is not None else None)).to_be('custom')
    if (first.kind if first is not None else None) == 'custom':
        yield from first.run(lambda *_args: None)
    next_ = combat_gear(s)
    expect((next_.kind if next_ is not None else None)).to_be('deposit')
    if (next_.kind if next_ is not None else None) == 'deposit':
        expect(next_.keep).to_equal(['tattered scroll'])


test('Shilo banks rejected gear to free room for a usable replacement', _fn101)


def _fn103():
    step = combat_gear(snapshot(({
        'inv': {_k: _v for _k, _v in [['rope', 1], ['lobster', 27]]},
        'bank': {_k: _v for _k, _v in [['steel scimitar', 1]]},
        'free_slots': 0,
    })))
    expect((step.kind if step is not None else None)).to_be('deposit')
    if (step.kind if step is not None else None) == 'deposit':
        expect(step.keep).to_equal(['rope'])


test('Shilo can bank food to make room without depositing quest tools', _fn103)


def _fn104():
    step = combat_gear(snapshot(({'bank': {_k: _v for _k, _v in [['steel scimitar', 1], ['steel chainbody', 1]]}, 'free_slots': 1})))
    expect((step.kind if step is not None else None)).to_be('withdraw')
    if (step.kind if step is not None else None) == 'withdraw':
        expect(step.items).to_equal([Record({'name': 'Steel scimitar', 'qty': 1})])


test('Shilo withdraws only the gear that fits before equipping it', _fn104)
def continues_reading_with(weapon):
    def _fn105():
        s = snapshot(({
        'progress': progress(SV_STAGE.ENTERED_AH_ZA_RHOON),
        'inv_ids': {_k: _v for _k, _v in [[SV_ITEM.TATTERED_SCROLL.id, 1], [SV_ITEM.ROPE.id, 1]]},
        'worn': set([weapon, 'steel chainbody', 'steel platelegs', 'steel full helm'] + list(((['steel kiteshield'] if weapon == 'steel scimitar' else [])))),
        'bank_known': False,
        'tile': at(2898, 9401),
    }))
        expect(name(decide(s))).to_be('read the tattered scroll')
    return _fn105


for weapon in ['steel scimitar', 'rune 2h sword']:
    test(f'Shilo continues reading with {weapon} equipped before any bank scan', continues_reading_with(weapon))


def _fn106():
    expect((combat_gear(snapshot(({'bank_known': False}))).kind if combat_gear(snapshot(({'bank_known': False}))) is not None else None)).to_be('scan_bank')


test('Shilo scans an unknown bank when combat slots still need gear', _fn106)


def _fn107():
    deposited = []
    s = snapshot(({
        'inv': {_k: _v for _k, _v in [['rune warhammer', 1], ['hammer', 1], ['tattered scroll', 1], ['lobster', 25]]},
        'bank': {_k: _v for _k, _v in [['steel scimitar', 1]]},
        'free_slots': 0,
    }))

    def _fn110(predicate, *_args):
        for item in list(s.inv.keys()):
            if predicate(item, 0):
                deposited.append(item)
        if False:
            yield
    spy_on(equipment, 'contains', returns=False)
    spy_on(equipment, 'equip', impl=refuse_equip)
    spy_on(banking, 'open', impl=open_bank)
    spy_on(bank, 'deposit_all_matching', impl=_fn110)
    wear = combat_gear(s)
    expect((wear.kind if wear is not None else None)).to_be('custom')
    if (wear.kind if wear is not None else None) == 'custom':
        yield from wear.run(lambda *_args: None)
    deposit = combat_gear(s)
    expect((deposit.kind if deposit is not None else None)).to_be('deposit')
    if (deposit.kind if deposit is not None else None) != 'deposit':
        raise RuntimeError('expected gear deposit')
    fields = {}
    for key in deposit.keys():
        fields[key] = deposit.get(key)
    fields['leave_open'] = True
    _w112 = yield from execute_step(Record(fields), [], lambda *_args: None)
    expect(_w112).to_be(True)
    expect(deposited).to_equal(['rune warhammer'])


test('Shilo deposits a rejected warhammer while preserving the quest hammer', _fn107)
