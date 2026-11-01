"""Ported from rs2b0t's test/api/ai/quests/regicideDecide.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestProgress, QuestSnapshot
from rs2004.quests.defs.regicide import decide
from rs2004.quests.defs.regicide.areas import RG_ITEM
from rs2004.quests.defs.regicide.journal import RG_FLAG, RG_STAGE
from rs2004.quests.defs.regicide.supplies import ARROW_TARGET, COAL_TARGET, FOOD_TARGET, RETURN_KIT, ROPE_TARGET, STILL_FOOD, WOOL_TARGET
from rs2004.quests.gear import quest_loadout

# Why: decide() reads only a snapshot, so the routing table is testable end to end without a client.
def counts(stacks):
    return {_k: _v for _k, _v in [((s if isinstance(s, list) else [s, 1])) for s in stacks]}


def _fn1():
    quest_loadout.current = None


after_each(_fn1)
ARDOUGNE = Record({'x': 2655, 'z': 3283, 'level': 0})
ELF_CAMP = Record({'x': 2205, 'z': 3252, 'level': 0})
PASS = Record({'x': 2450, 'z': 9716, 'level': 0})
KIT = [
    [RG_ITEM.BALL_OF_WOOL.id, WOOL_TARGET],
    RG_ITEM.PICKAXE.id,
    RG_ITEM.PESTLE.id,
    [RG_ITEM.ROPE.id, ROPE_TARGET],
    RG_ITEM.SHORTBOW.id,
    [RG_ITEM.BRONZE_ARROW.id, ARROW_TARGET],
    RG_ITEM.TINDERBOX.id,
    RG_ITEM.SPADE.id,
    [RG_ITEM.SHARK.id, FOOD_TARGET],
]
WEAPON = 'rune scimitar'


NAMED = ['stage', 'flags', 'carried', 'banked', 'worn_names']


def snapshot(over=None):
    if over is None:
        over = Record({})
    stage = over.stage if over.stage is not None else RG_STAGE.NOT_STARTED
    flags = over.flags if over.flags is not None else []
    carried = over.carried if over.carried is not None else KIT
    banked = over.banked if over.banked is not None else []
    worn_names = over.worn_names if over.worn_names is not None else [WEAPON]
    _merged2 = {}
    for _k, _v in {
        'journal': 'in_progress',
        'inv': {},
        'inv_ids': counts(carried),
        'worn': set(worn_names),
        'worn_ids': set(),
        'no_progress': 0,
        'bank_coins': 2000000,
        'bank': {},
        'bank_ids': counts(banked),
        'bank_known': True,
        'stage': stage,
        'progress': QuestProgress(stage, set(flags)),
        'tile': ELF_CAMP,
    }.items():
        _merged2[_k] = _v
    for _k in over.keys():
        if _k not in NAMED:
            _merged2[_k] = over.get(_k)
    return QuestSnapshot(**_merged2)


def name(step):
    return (step.name if step.kind == 'custom' else (f'wait: {step.reason}' if step.kind == 'wait' else step.kind))


def _palisade_waits(item):
    def check():
        short = [s for s in KIT if ((s[0] if isinstance(s, list) else s)) != item.id]
        step = decide(snapshot(Record({'stage': RG_STAGE.SPOKEN_LATHAS, 'tile': PASS, 'carried': short})))
        expect(step.kind).to_be('wait')
        expect(step.kind == 'wait' and step.reason.lower()).to_contain(('bow' if item.id == 841 else item.name.lower()))
    return check


def _fn3():
    def _fn4():
        expect(decide(snapshot(Record({'journal': 'complete'}))).kind).to_be('done')
    test('a finished journal is done', _fn4)

    def _fn5():
        expect(decide(snapshot(Record({'journal': 'unknown'}))).kind).to_be('wait')
    test('an unread journal waits rather than guessing a stage', _fn5)

    def _fn6():
        expect(name(decide(snapshot(Record({'stage': RG_STAGE.NOT_STARTED, 'tile': ARDOUGNE}))))).to_contain('messenger')
    test('the messenger is waited for before anything else', _fn6)

    def _fn7():
        step = decide(snapshot(Record({'stage': RG_STAGE.SPOKEN_LATHAS, 'tile': PASS, 'carried': []})))
        expect(step.kind).to_be('wait')
        expect(step.kind == 'wait' and step.reason).to_contain('not equipped for Tirannwn')
    test('a pack short of the kit is stopped on the mainland, not at the palisade', _fn7)

    def _fn8():
        expect(name(decide(snapshot(Record({'stage': RG_STAGE.SPOKEN_LATHAS, 'tile': PASS}))))).to_contain('Underground Pass')
    test('a kitted pack outside Tirannwn walks the pass', _fn8)
    # Why: `upass_bridge` writes no permanent state and its lever only sends the player east, so a finished Underground Pass still owes a fire arrow on every westbound walk, a pack without one crosses nothing.
    BRIDGE_KIT = [RG_ITEM.SHORTBOW, RG_ITEM.BRONZE_ARROW, RG_ITEM.TINDERBOX, RG_ITEM.SPADE]
    for item in BRIDGE_KIT:
        test(f'the palisade waits for the {item.name.lower()}', _palisade_waits(item))

    def _fn10():
        step = decide(snapshot(Record({'stage': RG_STAGE.SPOKEN_LATHAS, 'tile': PASS, 'worn_names': []})))
        expect(step.kind == 'wait' and step.reason).to_contain('melee weapon')
    test('a melee weapon is part of what the palisade waits for', _fn10)
    # Why: the gate is re-asked every cycle and the pass is walked with the pack in hand, so anything keyed on the full float blocks the moment the pass spends some of it, the run parked at the bridge's west foot, across the chasm, on "have 49" of fifty arrows.
    SPENT = [
        ['an arrow on the guide-rope shot', [RG_ITEM.BRONZE_ARROW.id, ARROW_TARGET - 1]],
        ['a rope on the rock swing', [RG_ITEM.ROPE.id, 1]],
        ['sharks on the traps', [RG_ITEM.SHARK.id, 1]],
    ]

    def _fn11(_what, left):
        spent = [((left if ((s[0] if isinstance(s, list) else s)) == left[0] else s)) for s in KIT]
        expect(name(decide(snapshot(Record({'stage': RG_STAGE.SPOKEN_LATHAS, 'tile': PASS, 'carried': spent}))))).to_contain('Underground Pass')
    test_each(SPENT)('a pack that spent %s still walks on', _fn11)

    def _fn12():
        step = decide(snapshot(Record({
        'stage': RG_STAGE.SPOKEN_LATHAS,
        'tile': ARDOUGNE,
        'carried': [],
        'worn_names': [],
        'banked': KIT,
        'bank': {_k: _v for _k, _v in [
        ['rune scimitar', 1],
        ['rune chainbody', 1],
        ['rune platelegs', 1],
        ['rune full helm', 1],
        ['rune kiteshield', 1],
    ]},
    })))
        expect(step.kind).to_be('withdraw')
        drawn = ([i['name'].lower() for i in step.items] if step.kind == 'withdraw' else [])
        expect(drawn).to_equal(['rune scimitar'])
        expect(drawn).not_.to_contain(RG_ITEM.SHARK.name.lower())
    test('a missing combat weapon is drawn without requiring bank armour', _fn12)

    def _fn13():
        expect(name(decide(snapshot(Record({'stage': RG_STAGE.SPOKEN_LATHAS}))))).to_contain('elf scouts')
    test('the scouts are waited for inside the forest', _fn13)

    def _fn14():
        expect(name(decide(snapshot(Record({'stage': RG_STAGE.SPOKEN_TRACKER}))))).to_contain('Lord Iorwerth')
    test('the tracker is asked for proof before the pendant exists', _fn14)

    def _fn15():
        step = decide(snapshot(Record({'stage': RG_STAGE.SPOKEN_TRACKER, 'carried': list(KIT) + [RG_ITEM.PENDANT.id]})))
        expect(name(step)).to_contain('tracker')
    test('the pendant in the pack sends the player back to the tracker', _fn15)

    def _fn16():
        step = decide(snapshot(Record({'stage': RG_STAGE.SPOKEN_TRACKER, 'flags': [RG_FLAG.PENDANT]})))
        expect(name(step)).to_contain('tracker')
    test('a journal that records the pendant is enough, even once it has been handed over', _fn16)


describe('Regicide decide()', _fn3)


def _fn17():
    def at_stage(carried):
        return decide(snapshot(Record({'stage': RG_STAGE.SPOKEN_IORWERTH2, 'carried': list(KIT) + list(carried)})))

    def _fn18():
        expect(name(at_stage([]))).to_contain('weave')
    test('the cloth is woven first, while the wool is still in the pack', _fn18)

    # Why: the pot is taken while the loom is still in sight, because the elf camp is four crossings from the swamp and eight from the palisade, going back for it is the forest crossed twice over.
    def _fn19():
        expect(name(at_stage([RG_ITEM.CLOTH.id]))).to_contain('pot')
    test('the pot is taken while the pack is still in the elf camp', _fn19)

    def _fn20():
        expect(name(at_stage([RG_ITEM.CLOTH.id, RG_ITEM.POT.id]))).to_contain('empty barrel')
    test('the barrel comes next, off the same floor', _fn20)

    def _fn21():
        expect(name(at_stage([RG_ITEM.CLOTH.id, RG_ITEM.POT.id, RG_ITEM.BARREL.id]))).to_contain('coal-tar')
    test('a barrel in hand is filled rather than a second one fetched', _fn21)
    FOREST_KIT = [RG_ITEM.CLOTH.id, RG_ITEM.POT.id, RG_ITEM.BARREL_TAR.id]

    def _fn22():
        expect(name(at_stage(FOREST_KIT))).to_contain('rabbit')
    test('a barrel already full of tar is not refilled', _fn22)

    def _fn23():
        expect(name(at_stage(list(FOREST_KIT) + [RG_ITEM.RAW_RABBIT.id]))).to_contain('sulphur')
    test('the sulphur is broken off once the rabbit is caught', _fn23)

    def _fn24():
        expect(name(at_stage(list(FOREST_KIT) + [RG_ITEM.RAW_RABBIT.id, RG_ITEM.SULPHUR.id]))).to_contain('grind')
    test('a lump of sulphur is ground rather than a second one taken', _fn24)

    # Why: the quarry is past the palisade, so from inside the forest the limestone is a crossing before it is a rock. A `mineRock` emitted from the elf camp anchors a plain walk, which answers "no path to (2323,3269): unreachable" and mines nothing.
    def _fn25():
        step = at_stage(list(FOREST_KIT) + [RG_ITEM.RAW_RABBIT.id, RG_ITEM.SULPHUR_DUST.id])
        expect(name(step)).to_contain('Arandar quarry')
    test('limestone is a crossing while the pack is still in the forest', _fn25)

    def _fn26():
        step = decide(snapshot(Record({
        'stage': RG_STAGE.SPOKEN_IORWERTH2,
        'carried': list(KIT) + list(FOREST_KIT) + [RG_ITEM.RAW_RABBIT.id, RG_ITEM.SULPHUR_DUST.id],
        'tile': Record({'x': 2323, 'z': 3266, 'level': 0}),
    })))
        expect(step.kind).to_be('mine_rock')
        expect(step.kind == 'mine_rock' and step.rock).to_be('Limestone')
    test('limestone is a rock once the quarry is in reach', _fn26)

    def _fn27():
        step = at_stage(list(FOREST_KIT) + [RG_ITEM.RAW_RABBIT.id, RG_ITEM.SULPHUR_DUST.id, RG_ITEM.LIMESTONE.id])
        expect(name(step)).to_contain('Arandar')
    test('a full pack leaves through the palisade', _fn27)

    # Why: the mainland half is keyed on the same pack, so the same snapshot with a mainland tile has to pick up where the forest left off.
    def on_mainland(carried):
        return decide(snapshot(Record({'stage': RG_STAGE.SPOKEN_IORWERTH2, 'tile': ARDOUGNE, 'carried': list(KIT) + list(carried)})))
    CARRIED_OUT = [RG_ITEM.CLOTH.id, RG_ITEM.POT.id, RG_ITEM.BARREL_TAR.id, RG_ITEM.SULPHUR_DUST.id]

    def _fn28():
        expect(name(on_mainland(list(CARRIED_OUT) + [RG_ITEM.RAW_RABBIT.id, RG_ITEM.LIMESTONE.id]))).to_contain('cook')
    test('the raw rabbit is cooked before anything else on the mainland', _fn28)

    def _fn29():
        step = on_mainland(list(CARRIED_OUT) + [RG_ITEM.COOKED_RABBIT.id, RG_ITEM.LIMESTONE.id])
        expect(name(step)).to_contain('burn the limestone')
    test('the limestone is burned at a furnace the forest does not have', _fn29)

    def _fn30():
        step = on_mainland(list(CARRIED_OUT) + [RG_ITEM.COOKED_RABBIT.id, RG_ITEM.QUICKLIME.id])
        expect(name(step)).to_contain('grind the quicklime')
    test('the quicklime is ground into the pot carried out of the forest', _fn30)

    # Why: the pass kit is seven slots and coal does not stack, so the bank trip comes first, a pack still holding the spade, the ropes, the bow and the arrows runs out of room at four coal and swings at a full inventory for the rest of the leg.
    def _fn31():
        step = on_mainland(list(CARRIED_OUT) + [RG_ITEM.COOKED_RABBIT.id, RG_ITEM.QUICKLIME_DUST.id])
        expect(step.kind).to_be('deposit')
        expect(step.kind == 'deposit' and step.keep_ids).not_.to_contain(RG_ITEM.SPADE.id)
        expect(step.kind == 'deposit' and step.keep_ids).to_contain(RG_ITEM.BARREL_TAR.id)
    test('the pass kit is banked before the coal is mined', _fn31)

    # Why: the pack shaped to the coal run, the chain, the two tools and a short food float. Anything else and the plan sends it to the bank first.
    def _fn32():
        shaped = [
        RG_ITEM.BARREL_TAR.id,
        RG_ITEM.CLOTH.id,
        RG_ITEM.SULPHUR_DUST.id,
        RG_ITEM.QUICKLIME_DUST.id,
        RG_ITEM.POT.id,
        RG_ITEM.COOKED_RABBIT.id,
        RG_ITEM.PICKAXE.id,
        RG_ITEM.PESTLE.id,
        [RG_ITEM.SHARK.id, STILL_FOOD],
    ]
        step = decide(snapshot(Record({'stage': RG_STAGE.SPOKEN_IORWERTH2, 'tile': ARDOUGNE, 'carried': shaped})))
        expect(step.kind).to_be('mine_rock')
        expect(step.kind == 'mine_rock' and step.rock).to_be('Coal')
    test('coal is sourced once the pack is shaped for it', _fn32)

    def _fn33():
        step = on_mainland(list(CARRIED_OUT) + [RG_ITEM.COOKED_RABBIT.id, RG_ITEM.QUICKLIME_DUST.id, [RG_ITEM.COAL.id, 20]])
        expect(name(step)).to_contain('distil')
    test('a pack with coal distils', _fn33)

    def _fn34():
        step = on_mainland([
        RG_ITEM.CLOTH.id,
        RG_ITEM.SULPHUR_DUST.id,
        RG_ITEM.QUICKLIME_DUST.id,
        RG_ITEM.BARREL_NAPHTHA.id,
        RG_ITEM.COOKED_RABBIT.id,
    ])
        expect(name(step)).to_contain('mix')
    test('naphtha is mixed with the powders', _fn34)

    def _fn35():
        step = on_mainland([RG_ITEM.CLOTH.id, RG_ITEM.SULPHUR_DUST.id, RG_ITEM.MIX_QUICKLIME.id, RG_ITEM.COOKED_RABBIT.id])
        expect(name(step)).to_contain('mix')
    test('a half-mixed barrel is still the mixing step', _fn35)

    def _fn36():
        expect(name(on_mainland([RG_ITEM.CLOTH.id, RG_ITEM.BARREL_LID.id, RG_ITEM.COOKED_RABBIT.id]))).to_contain('fuse')
    test('a sealed barrel takes the fuse', _fn36)

    # Why: the recipe is still in the pack at this point, the wool, the pickaxe and the pestle, and none of it crosses. The bomb waits for a bank trip rather than carrying nine dead slots into the pass.
    def _fn37():
        expect(on_mainland([RG_ITEM.BARREL_FUSED.id, RG_ITEM.COOKED_RABBIT.id]).kind).to_be('deposit')
    test('a fused bomb beside the spent recipe is shaped before it crosses', _fn37)

    # Why: `regicide_cross_over3` clears the given-rabbit bit inside mapsquare 34_49, which the walk to the catapult crosses, so the guard is fed after arriving, and never before setting out.
    def _fn38():
        expect(name(at_stage([RG_ITEM.BARREL_FUSED.id, RG_ITEM.COOKED_RABBIT.id]))).to_contain('catapult guard')
    test('the guard is fed after the bomb is back in the forest', _fn38)

    def _fn39():
        expect(name(at_stage([RG_ITEM.BARREL_FUSED.id]))).to_contain('fire the barrel bomb')
    test('with the rabbit handed over, the catapult fires', _fn39)


describe('Regicide bomb chain', _fn17)


def _fn40():
    def _fn41():
        expect(name(decide(snapshot(Record({'stage': RG_STAGE.KILLED_TYRAS}))))).to_contain('Lord Iorwerth')
    test('the deed is reported to Iorwerth before leaving', _fn41)

    def _fn42():
        expect(name(decide(snapshot(Record({'stage': RG_STAGE.REPORTED_IORWERTH}))))).to_contain('Arandar')
    test('the letter is carried out through the palisade', _fn42)

    def _fn43():
        expect(name(decide(snapshot(Record({'stage': RG_STAGE.REPORTED_IORWERTH, 'tile': ARDOUGNE}))))).to_contain('Arianwyn')
    test('on the mainland the Ardougne road is walked for Arianwyn', _fn43)

    def _fn44():
        expect(name(decide(snapshot(Record({'stage': RG_STAGE.SPOKEN_ARIANWYN, 'tile': ARDOUGNE}))))).to_contain('King Lathas')
    test('once Arianwyn has spoken, the letter goes to King Lathas', _fn44)


describe('Regicide endgame', _fn40)


# Why: the bomb is built, so the recipe is spent. The wool is cloth and the limestone is dust. A second crossing that redraws the full kit puts nine dead slots beside a barrel bomb that has to fit as well.
def _fn45():
    CROSSINGS = [RG_ITEM.SPADE, RG_ITEM.ROPE, RG_ITEM.SHORTBOW, RG_ITEM.BRONZE_ARROW, RG_ITEM.TINDERBOX, RG_ITEM.SHARK]
    RECIPE = [RG_ITEM.BALL_OF_WOOL, RG_ITEM.PICKAXE, RG_ITEM.PESTLE]

    def _fn46():
        for item in CROSSINGS:
            expect(any([supply.item.id == item.id for supply in RETURN_KIT])).to_be(True)
    test('the return kit keeps every crossing', _fn46)

    def _fn47():
        for item in RECIPE:
            expect(any([supply.item.id == item.id for supply in RETURN_KIT])).to_be(False)
    test('the return kit drops the recipe', _fn47)

    def _fn48():
        step = decide(snapshot(Record({
        'stage': RG_STAGE.SPOKEN_IORWERTH2,
        'tile': ARDOUGNE,
        'carried': [
        RG_ITEM.BARREL_FUSED.id,
        RG_ITEM.SPADE.id,
        [RG_ITEM.ROPE.id, ROPE_TARGET],
        RG_ITEM.SHORTBOW.id,
        [RG_ITEM.BRONZE_ARROW.id, ARROW_TARGET],
        RG_ITEM.TINDERBOX.id,
        [RG_ITEM.SHARK.id, FOOD_TARGET],
    ],
    })))
        expect(name(step)).to_contain('Underground Pass')
    test('a bomb in the pack is not sent back for wool', _fn48)


describe('the walk back through the pass', _fn45)


# Why: coal accumulates in the pack, so the room the plan asks for is what is left to mine. Asking for the full float once half of it is already held parks a leg that is one swing from finishing.
def _fn49():
    CHAIN = [
        RG_ITEM.BARREL_TAR.id,
        RG_ITEM.CLOTH.id,
        RG_ITEM.SULPHUR_DUST.id,
        RG_ITEM.QUICKLIME_DUST.id,
        RG_ITEM.POT.id,
        RG_ITEM.PICKAXE.id,
        RG_ITEM.PESTLE.id,
        [RG_ITEM.SHARK.id, STILL_FOOD],
    ]

    def _fn50():
        step = decide(snapshot(Record({
        'stage': RG_STAGE.SPOKEN_IORWERTH2,
        'tile': ARDOUGNE,
        'carried': list(CHAIN) + [[RG_ITEM.COAL.id, 6]],
        'free_slots': 11,
    })))
        expect(step.kind).to_be('mine_rock')
    test('a pack part way through the coal keeps mining', _fn50)

    def _fn51():
        step = decide(snapshot(Record({
        'stage': RG_STAGE.SPOKEN_IORWERTH2,
        'tile': ARDOUGNE,
        'carried': list(CHAIN) + [[RG_ITEM.COAL.id, COAL_TARGET]],
        'free_slots': 5,
    })))
        expect(name(step)).to_contain('distil')
    test('a pack with the float already mined moves on to the still', _fn51)


describe('room for the coal', _fn49)


# Why: the still leaves coal and a full food float in the pack, and `sourceKit` only ever adds, so the walk back crossed with no room and `make_clotharrow` answered "You don't have space to do that." at the bridge, an hour from the nearest bank.
def _fn52():
    LEFTOVERS = [
        RG_ITEM.BARREL_FUSED.id,
        RG_ITEM.SPADE.id,
        [RG_ITEM.ROPE.id, ROPE_TARGET],
        RG_ITEM.SHORTBOW.id,
        [RG_ITEM.BRONZE_ARROW.id, ARROW_TARGET],
        RG_ITEM.TINDERBOX.id,
        [RG_ITEM.SHARK.id, FOOD_TARGET],
        [RG_ITEM.COAL.id, 5],
        RG_ITEM.PICKAXE.id,
        RG_ITEM.PESTLE.id,
    ]

    def _fn53():
        step = decide(snapshot(Record({'stage': RG_STAGE.SPOKEN_IORWERTH2, 'tile': ARDOUGNE, 'carried': LEFTOVERS, 'free_slots': 0})))
        expect(step.kind).to_be('deposit')
        expect(step.kind == 'deposit' and step.keep_ids).not_.to_contain(RG_ITEM.COAL.id)
        expect(step.kind == 'deposit' and step.keep_ids).to_contain(RG_ITEM.BARREL_FUSED.id)
    test('the leftover coal and tools are banked before crossing', _fn53)

    def _fn54():
        shaped = [
        RG_ITEM.BARREL_FUSED.id,
        RG_ITEM.SPADE.id,
        [RG_ITEM.ROPE.id, ROPE_TARGET],
        RG_ITEM.SHORTBOW.id,
        [RG_ITEM.BRONZE_ARROW.id, ARROW_TARGET],
        RG_ITEM.TINDERBOX.id,
        [RG_ITEM.SHARK.id, FOOD_TARGET],
    ]
        step = decide(snapshot(Record({'stage': RG_STAGE.SPOKEN_IORWERTH2, 'tile': ARDOUGNE, 'carried': shaped})))
        expect(name(step)).to_contain('Underground Pass')
    test('a shaped pack with room for the fire arrow crosses', _fn54)


describe('shaping the pack for the walk back', _fn52)


# Why: nothing in the content deletes the King's message, the messenger's `inv_add` is the only site that touches its count, and King Lathas reads `%regicide_quest` rather than the pack. It would otherwise ride the pass twice and the coal run as a dead slot. Iorwerth's letter is the opposite: Lathas takes that one, so it stays.
def _fn55():
    CHAIN = [
        RG_ITEM.BARREL_TAR.id,
        RG_ITEM.CLOTH.id,
        RG_ITEM.SULPHUR_DUST.id,
        RG_ITEM.QUICKLIME_DUST.id,
        RG_ITEM.POT.id,
        RG_ITEM.PICKAXE.id,
        RG_ITEM.PESTLE.id,
        [RG_ITEM.SHARK.id, STILL_FOOD],
    ]

    def _fn56():
        step = decide(snapshot(Record({'stage': RG_STAGE.SPOKEN_IORWERTH2, 'tile': ARDOUGNE, 'carried': list(CHAIN) + [RG_ITEM.SUMMONS.id]})))
        expect(step.kind).to_be('deposit')
        expect(step.kind == 'deposit' and step.keep_ids).not_.to_contain(RG_ITEM.SUMMONS.id)
    test('the coal run banks it', _fn56)

    def _fn57():
        shaped = [
        RG_ITEM.BARREL_FUSED.id,
        RG_ITEM.MESSAGE.id,
        RG_ITEM.SPADE.id,
        [RG_ITEM.ROPE.id, ROPE_TARGET],
        RG_ITEM.SHORTBOW.id,
        [RG_ITEM.BRONZE_ARROW.id, ARROW_TARGET],
        RG_ITEM.TINDERBOX.id,
        [RG_ITEM.SHARK.id, FOOD_TARGET],
    ]
        step = decide(snapshot(Record({'stage': RG_STAGE.SPOKEN_IORWERTH2, 'tile': ARDOUGNE, 'carried': shaped})))
        expect(name(step)).to_contain('Underground Pass')
    test("the walk back keeps Iorwerth's letter, which Lathas does take", _fn57)


describe("the King's message is a prop the quest never reclaims", _fn55)


def _fn58():
    without_bow = [s for s in KIT if ((s[0] if isinstance(s, list) else s)) != 841]
    bows = [841, 839, 843, 845, 849, 847, 853, 851, 857, 855, 861, 859, 2883]

    def _fn59(id):
        step = decide(snapshot(Record({'stage': RG_STAGE.SPOKEN_LATHAS, 'tile': PASS, 'carried': list(without_bow) + [id]})))
        expect(name(step)).to_contain('Underground Pass')
    test_each(bows)('accepts bow %i in the pack on the first crossing', _fn59)

    def _fn60(id):
        step = decide(snapshot(Record({
        'stage': RG_STAGE.SPOKEN_LATHAS,
        'tile': ARDOUGNE,
        'carried': list(without_bow) + [id, 592],
        'free_slots': 1,
    })))
        expect(step.kind).to_be('deposit')
        if step.kind == 'deposit':
            expect(step.keep_ids).to_contain(id)
            expect(step.keep_ids).not_.to_contain(592)
    test_each(bows)('keeps bow %i when shedding junk before departure', _fn60)

    def _fn61():
        step = decide(snapshot(Record({'stage': RG_STAGE.SPOKEN_LATHAS, 'tile': PASS, 'carried': without_bow, 'worn_ids': set([859])})))
        expect(name(step)).to_contain('Underground Pass')
    test('an equipped magic longbow satisfies the crossing kit', _fn61)

    def _fn62():
        step = decide(snapshot(Record({'stage': RG_STAGE.SPOKEN_LATHAS, 'tile': ARDOUGNE, 'carried': without_bow, 'banked': [845]})))
        expect(step.kind).to_be('withdraw')
        if step.kind == 'withdraw':
            expect(step.items).to_equal([Record({'id': 845, 'name': 'Oak longbow', 'qty': 1})])
    test('withdraws a banked oak longbow instead of buying a plain shortbow', _fn62)

    def _fn63(id):
        step = decide(snapshot(Record({'stage': RG_STAGE.SPOKEN_LATHAS, 'tile': PASS, 'carried': list(without_bow) + [id]})))
        expect(step.kind).to_be('wait')
        if step.kind == 'wait':
            expect(step.reason.lower()).to_contain('bow')
    test_each([837, 842])('rejects crossbows and noted bows (%i)', _fn63)

    def _fn64():
        carried = [[s.item.id, s.qty] for s in [s for s in RETURN_KIT if s.item.id != 841]]
        step = decide(snapshot(Record({
        'stage': RG_STAGE.SPOKEN_IORWERTH2,
        'tile': ARDOUGNE,
        'carried': list(carried) + [857, RG_ITEM.BARREL_FUSED.id, RG_ITEM.COOKED_RABBIT.id],
        'banked': [841],
    })))
        expect(name(step)).to_contain('Underground Pass')
    test('keeps the chosen bow for the return crossing without withdrawing a spare shortbow', _fn64)

    def _fn65():
        carried = [[s.item.id, s.qty] for s in [s for s in RETURN_KIT if s.item.id != 841]]
        step = decide(snapshot(Record({
        'stage': RG_STAGE.SPOKEN_IORWERTH2,
        'tile': ARDOUGNE,
        'carried': list(carried) + [RG_ITEM.BARREL_FUSED.id, RG_ITEM.COOKED_RABBIT.id],
        'banked': [861],
    })))
        expect(step.kind).to_be('withdraw')
        if step.kind == 'withdraw':
            expect(step.items).to_equal([Record({'id': 861, 'name': 'Magic shortbow', 'qty': 1})])
    test('retrieves the banked bow after the coal run for the return crossing', _fn65)


describe('Regicide bow choices', _fn58)


def _fn66():
    def _fn68(row):
        step = decide(snapshot(Record({
        'stage': RG_STAGE.SPOKEN_LATHAS,
        'tile': ARDOUGNE,
        'worn_names': [WEAPON] + list(row.armour),
        'bank': {_k: _v for _k, _v in [['rune chainbody', 1], ['rune full helm', 1], ['rune kiteshield', 1]]},
    })))
        expect(name(step)).to_contain('Underground Pass')
    test_each([
        Record({'armour': ['leather body', 'leather chaps', 'coif']}),
        Record({'armour': ["monk's robe", 'wizard hat']}),
        Record({'armour': []}),
    ])('does not draw metal armour over the worn setup %j', _fn68)

    def _fn70():
        step = decide(snapshot(Record({
        'stage': RG_STAGE.SPOKEN_LATHAS,
        'tile': ELF_CAMP,
        'worn_names': [WEAPON, 'leather body'],
        'inv': {_k: _v for _k, _v in [['rune chainbody', 1]]},
    })))
        expect(name(step)).to_contain('elf scouts')
    test('does not put packed metal armour on over the chosen outfit', _fn70)


describe('Regicide keeps chosen armour', _fn66)


def _fn71(location):
    carried = [s for s in KIT if ((s[0] if isinstance(s, list) else s)) != 841]
    step = decide(snapshot(Record({
        'stage': RG_STAGE.SPOKEN_LATHAS,
        'tile': ARDOUGNE,
        'ranged': 25,
        'carried': (list(carried) + [861] if location == 'pack' else carried),
        'banked': ([861] if location == 'bank' else []),
    })))
    expect(step.kind).to_be('buy')
    if step.kind == 'buy':
        expect(step.item).to_be('Shortbow')


test_each(['bank', 'pack'])('sources a usable bow when the only bow in the %s needs a higher Ranged level', _fn71)


def _fn73(row):
    id = row.id
    level = row.level
    carried = list([s for s in KIT if ((s[0] if isinstance(s, list) else s)) != 841]) + [id]
    expect(name(decide(snapshot(Record({'stage': RG_STAGE.SPOKEN_LATHAS, 'tile': PASS, 'carried': carried, 'ranged': level}))))).to_contain('Underground Pass')
    expect(decide(snapshot(Record({'stage': RG_STAGE.SPOKEN_LATHAS, 'tile': PASS, 'carried': carried, 'ranged': level - 1}))).kind).to_be('wait')


test_each([
    Record({'id': 843, 'level': 5}),
    Record({'id': 849, 'level': 20}),
    Record({'id': 853, 'level': 30}),
    Record({'id': 857, 'level': 40}),
    Record({'id': 859, 'level': 50}),
    Record({'id': 2883, 'level': 30}),
])('accepts a bow at its wield level and blocks below it: %j', _fn73)


def _fn75():
    quest_loadout.current = Record({'name': 'melee', 'worn': Record({'torso': 'Rune chainbody', 'hat': 'Rune full helm'}), 'carry': []})
    step = decide(snapshot(Record({
        'stage': RG_STAGE.SPOKEN_LATHAS,
        'tile': ARDOUGNE,
        'worn_names': [WEAPON, 'leather body', 'coif'],
        'bank': {_k: _v for _k, _v in [['rune chainbody', 1], ['rune full helm', 1]]},
    })))
    expect(name(step)).to_contain('Underground Pass')


test('a saved loadout does not replace the armour already worn for Regicide', _fn75)

