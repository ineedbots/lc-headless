"""Ported from rs2b0t's test/api/ai/quests/defs/legends.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.defs import QUEST_DEFS
from rs2004.quests.defs.legends import decide, legends, spent_now
from rs2004.quests.defs.legends.areas import LQ_ID, LQ_STAGE, LQ_TILE, in_jungle_band, in_octagram, jungle_section, legends_area
from rs2004.quests.defs.legends.pockets import legends_pocket
from rs2004.quests.defs.legends.supplies import FOOD_FOR_SLOT, KEEP_IDS, LQ_FOODS, PRAYER_POTIONS, SHOP_GP, coin_top_up
from rs2004.quests.engine.types import QuestSnapshot


def counts(names):
    out = {}
    for name in names:
        key = name.lower()
        out[key] = out.get(key, 0) + (20000 if key == 'coins' else 1)
    return out


def ids(rows):
    out = {}
    for id in rows:
        out[id] = out.get(id, 0) + 1
    return out


KARAMJA = Record({'x': 2850, 'z': 2960, 'level': 0})
FULL_KIT = [LQ_ID.MAP_COMPLETE, LQ_ID.BULLROARER, LQ_ID.RUNE_AXE, LQ_ID.MACHETE, LQ_ID.LOCKPICK, LQ_ID.UNPOWERED_ORB, LQ_ID.RUNE_PICKAXE, LQ_ID.HAMMER, LQ_ID.KNIFE, LQ_ID.ROPE, LQ_ID.CHISEL, LQ_ID.VIAL_WATER, LQ_ID.SOUL_RUNE, LQ_ID.MIND_RUNE, LQ_ID.EARTH_RUNE, LQ_ID.LAW_RUNE, LQ_ID.LAW_RUNE, LQ_ID.OPAL, LQ_ID.JADE, LQ_ID.RED_TOPAZ, LQ_ID.SAPPHIRE, LQ_ID.EMERALD, LQ_ID.RUBY, LQ_ID.DIAMOND, LQ_ID.COSMIC_RUNE, LQ_ID.COSMIC_RUNE, LQ_ID.COSMIC_RUNE] + [LQ_ID.WATER_RUNE] * 30 + [LQ_ID.GOLD_BAR, LQ_ID.GOLD_BAR] + [LQ_ID.PAPYRUS] * 6 + [LQ_ID.CHARCOAL] * 6
WORN_KIT = [LQ_ID.RUNE_SCIMITAR, 1113, 1079, 1163, 1201, 1704]


def snap(o=None):
    if o is None:
        o = Record({})
    return QuestSnapshot(
        journal=o.journal if o.journal is not None else 'in_progress',
        inv=counts(o.inv if o.inv is not None else []),
        inv_ids=ids(o.inv_ids if o.inv_ids is not None else []),
        worn=set([n.lower() for n in (o.worn if o.worn is not None else [])]),
        worn_ids=set(o.worn_ids if o.worn_ids is not None else WORN_KIT),
        stage=o.stage,
        bank=counts(o.bank if o.bank is not None else []),
        bank_ids=ids(o.bank_ids if o.bank_ids is not None else []),
        bank_known=o.bank_known if o.bank_known is not None else True,
        tile=o.tile if o.tile is not None else KARAMJA,
        free_slots=8,
    )


def kitted(o=None):
    """Kitted out on Karamja: coins, food and every sourceable item already in the pack."""
    if o is None:
        o = Record({})
    fields = {}
    for key in o.keys():
        fields[key] = getattr(o, key)
    fields['inv'] = list(o.inv if o.inv is not None else []) + ['Coins'] + ['Lobster'] * 14
    fields['inv_ids'] = list(o.inv_ids if o.inv_ids is not None else []) + list(FULL_KIT) + [LQ_ID.COINS]
    return snap(Record(fields))


def name(step):
    return ((f'custom:{step.name}' if step.kind == 'custom' else step.kind))


def without(base, shed):
    """The same pack minus what a death dropped."""
    kept = {}
    for id in base.inv_ids.keys():
        if id not in shed:
            kept[id] = base.inv_ids[id]
    return base.with_fields({'inv_ids': kept})


def at_the_gem_rocks(gems):
    """Re-mining the seven gems after a death: the trials kit is intact, the map supplies are long gone."""
    shed = [LQ_ID.PAPYRUS, LQ_ID.CHARCOAL] + list(GEM_IDS)
    kit = [id for id in FULL_KIT if not (id in shed)]
    return snap(Record({
        'stage': LQ_STAGE.SUMMONED_NEZI_FIRE,
        'inv_ids': list(kit) + list(gems) + [LQ_ID.LOBSTER, LQ_ID.LOBSTER, LQ_ID.COINS],
        'inv': ['Coins', 'Lobster', 'Lobster'],
        'tile': Record({'x': 2825, 'z': 2997, 'level': 0}),
    }))


GEM_IDS = [LQ_ID.OPAL, LQ_ID.JADE, LQ_ID.RED_TOPAZ, LQ_ID.SAPPHIRE, LQ_ID.EMERALD, LQ_ID.RUBY, LQ_ID.DIAMOND]


def _fn6():
    def _fn7():
        expect(legends_area(Record({'x': 2790, 'z': 2910, 'level': 0}))).to_be('jungle')
        expect(legends_area(Record({'x': 2790, 'z': 2960, 'level': 0}))).to_be('mainland')
    test('the Kharazi Jungle is its own world', _fn7)

    def _fn8():
        expect(legends_area(Record({'x': 2773, 'z': 9341, 'level': 0}))).to_be('shaman_caves')
        expect(legends_area(Record({'x': 2400, 'z': 4710, 'level': 0}))).to_be('viyeldi_caves')
    test('the shaman caves and the Viyeldi caves are separate complexes', _fn8)

    def _fn9():
        expect(legends_area(None)).to_be('unknown')
    test('a missing tile is unknown rather than mainland', _fn9)

    def _fn10():
        expect(jungle_section(Record({'x': 2790, 'z': 2910, 'level': 0}))).to_be('west')
        expect(jungle_section(Record({'x': 2840, 'z': 2910, 'level': 0}))).to_be('middle')
        expect(jungle_section(Record({'x': 2900, 'z': 2910, 'level': 0}))).to_be('east')
        expect(jungle_section(Record({'x': 2790, 'z': 2960, 'level': 0}))).to_be_null()
    test('the jungle splits into the three thirds the map is drawn in', _fn10)


describe('legendsArea', _fn6)


def _fn11():
    def _fn12():
        expect(in_jungle_band(Record({'x': 2816, 'z': 2936, 'level': 0}))).to_be(False)
        expect(in_jungle_band(Record({'x': 2816, 'z': 2937, 'level': 0}))).to_be(True)
        expect(in_jungle_band(Record({'x': 2816, 'z': 2939, 'level': 0}))).to_be(True)
        expect(in_jungle_band(Record({'x': 2816, 'z': 2940, 'level': 0}))).to_be(False)
    test('covers the three blocked rows and neither open tile', _fn12)


describe('inJungleBand', _fn11)


def _fn13():
    def _fn14():
        expect(in_octagram(LQ_TILE.OCTAGRAM_OUTSIDE)).to_be(False)
        expect(in_octagram(LQ_TILE.OCTAGRAM_INSIDE)).to_be(True)
    test('the wall tile is outside and the tile past it is inside', _fn14)

    def _fn15():
        expect(in_octagram(Record({'x': 2792, 'z': 9327, 'level': 0}))).to_be(True)
    test("Ungadulu's own tile is inside", _fn15)


describe('inOctagram', _fn13)


# Why: every one of these is a crossing the module drives, so a tile that lands in the wrong pocket runs the wrong leg.
POCKET_CASES = [
    ['the cave landing', 2773, 9341, 'shaman_cave'],
    ['inside the flames', 2792, 9328, 'octagram'],
    ['past the bookcase crevice', 2800, 9340, 'crevice'],
    ['north of the outer gate', 2809, 9333, 'crevice'],
    ['south of the outer gate', 2809, 9331, 'outer_gate'],
    ['between the first two boulders', 2809, 9325, 'boulder_one'],
    ['between the last two boulders', 2809, 9321, 'boulder_two'],
    ['north of the inner gate', 2809, 9315, 'inner_gate'],
    ['south of the inner gate', 2809, 9313, 'trials'],
    ['south of the jagged wall', 2790, 9295, 'trials'],
    ['north of the jagged wall', 2789, 9296, 'wall_room'],
    ['the gem room', 2774, 9301, 'gem_room'],
    ['the winch room', 2760, 9328, 'winch_room'],
    ['the rope landing', 2377, 4712, 'viyeldi_ledge'],
    ['the Viyeldi cave floor', 2400, 4710, 'viyeldi_main'],
    ['past the barrier', 2387, 4689, 'viyeldi_source'],
    ['open jungle', 2790, 2910, None],
]


def pocket_case(x, z, want):
    return lambda: expect(legends_pocket(Record({'x': x, 'z': z, 'level': 0}))).to_be(want)


describe('legendsPocket', lambda: [test(f"{row[0]} is {row[3] if row[3] is not None else 'open ground'}", pocket_case(row[1], row[2], row[3])) for row in POCKET_CASES])


# Why: both counters are a sea crossing from everything the quest then does, and sourcing per leg alternated between them and the bank across the length of stage 8, Ardougne bank, Jiminua's on Karamja, then a gold rock back on the mainland, three regions in three consecutive steps.
# Why: `estGp` is what the buy step tops the pack up to before it opens a counter, so a padded estimate is money carried through three demon fights rather than headroom.
def _fn18():
    def _fn19():
        # two soul at 1250, four law at 40, two mind at 3, two earth at 4, 150 water at 4, about 3.8k with depletion.
        expect(SHOP_GP.MAGIC_GUILD).to_be_less_than(20000)
        expect(SHOP_GP.MAGIC_GUILD).to_be_greater_than(5000)
    test('the guild estimate is headroom over the list, not a round number', _fn19)

    def _fn20():
        bank = ['Coins']
        low = snap(Record({'stage': LQ_STAGE.STARTED, 'inv': [], 'inv_ids': [], 'bank': bank, 'bank_ids': [LQ_ID.COINS]}))
        expect((coin_top_up(low).kind if coin_top_up(low) is not None else None)).to_be('withdraw')
        floored = snap(Record({
        'stage': LQ_STAGE.STARTED,
        'inv': ['Coins'],
        'inv_ids': [LQ_ID.COINS],
        'bank': bank,
        'bank_ids': [LQ_ID.COINS],
    }))
        expect(coin_top_up(floored)).to_be_null()
    test('the coin float is restored from a floor, not from half of itself', _fn20)


describe('what the counters cost', _fn18)


def _fn21():
    # Why: the coin and food floats run ahead of the stage switch, so a fixture under either of them never reaches the provisioning branch at all.
    FLOAT = Record({'inv': ['Coins'] + ['Lobster'] * 4, 'bank': ['Coins']})

    def bare(o=None):
        fields = {'stage': LQ_STAGE.NOT_STARTED, 'journal': 'not_started', 'inv': FLOAT.inv, 'bank': FLOAT.bank}
        fields['inv_ids'] = [LQ_ID.COINS] + [LQ_ID.LOBSTER] * 4
        fields['bank_ids'] = [LQ_ID.COINS]
        if o is not None:
            for key in o.keys():
                fields[key] = getattr(o, key)
        return snap(Record(fields))

    def _fn23():
        step = decide(bare())
        expect(step.kind).to_be('buy')
        expect(step.kind == 'buy' and step.shop.npc).to_be('Magic Store owner')
    test('the first errand is the Magic Guild counter, not Radimus', _fn23)

    def _fn24():
        bought = bare(Record({'inv_ids': [LQ_ID.COINS] + [LQ_ID.LOBSTER] * 4 + [LQ_ID.SOUL_RUNE, LQ_ID.MIND_RUNE, LQ_ID.EARTH_RUNE, LQ_ID.LAW_RUNE, LQ_ID.LAW_RUNE] + [LQ_ID.WATER_RUNE] * 30}))
        step = decide(bought)
        expect(step.kind).to_be('deposit')
        expect(step.kind == 'deposit' and (step.bank.x if step.bank is not None else None)).to_be(2612)
    test('the guild list is banked before the walk to Jiminua', _fn24)

    def _fn25():
        stocked = bare(Record({'bank_ids': [LQ_ID.COINS, LQ_ID.SOUL_RUNE, LQ_ID.MIND_RUNE, LQ_ID.EARTH_RUNE, LQ_ID.LAW_RUNE, LQ_ID.LAW_RUNE] + [LQ_ID.WATER_RUNE] * 30 + [LQ_ID.MACHETE] + [LQ_ID.PAPYRUS] * 8 + [LQ_ID.CHARCOAL] * 8 + [LQ_ID.KNIFE, LQ_ID.ROPE, LQ_ID.HAMMER, LQ_ID.CHISEL, LQ_ID.VIAL_WATER]}))
        expect(name(decide(stocked))).to_be('custom:ask Radimus Erkle for the quest')
    test('a stocked bank walks straight to Radimus', _fn25)

    # Why: Jiminua's is a shared counter with `allstock=no`, and a shopping list that parks on one empty shelf blocks a run the per-leg sourcing could still finish.
    def _fn26():
        expect(name(decide(bare().with_fields({'no_progress': 3})))).to_be('custom:ask Radimus Erkle for the quest')
    test('a counter that will not sell falls through to the quest rather than parking', _fn26)

    # Why: the Magic Guild stocks no cosmic rune at all, the only counter in the game that sells one is the Mage Arena's, which is deep Wilderness and behind a setting.
    def _fn28():
        asked = []
        cur = bare()
        for i in range(20):
            step = decide(cur)
            if step.kind != 'buy':
                break
            asked.append(step.item)
            bought = BUY_ID.get(step.item)
            if bought is None:
                break
            pack = {}
            for held in cur.inv_ids.keys():
                pack[held] = cur.inv_ids[held]
            pack[bought] = pack.get(bought, 0) + step.qty
            cur = cur.with_fields({'inv_ids': pack})
        expect(asked).not_.to_contain('Cosmic rune')
        expect(len(asked)).to_be_greater_than(0)
    test('cosmic runes are never asked of a counter', _fn28)


describe('provisioning before the quest starts', _fn21)
BUY_ID = {
    'Soul rune': LQ_ID.SOUL_RUNE,
    'Mind rune': LQ_ID.MIND_RUNE,
    'Earth rune': LQ_ID.EARTH_RUNE,
    'Law rune': LQ_ID.LAW_RUNE,
    'Water rune': LQ_ID.WATER_RUNE,
    'Machete': LQ_ID.MACHETE,
    'Papyrus': LQ_ID.PAPYRUS,
    'Charcoal': LQ_ID.CHARCOAL,
    'Knife': LQ_ID.KNIFE,
    'Rope': LQ_ID.ROPE,
    'Hammer': LQ_ID.HAMMER,
    'Chisel': LQ_ID.CHISEL,
    'Vial of water': LQ_ID.VIAL_WATER,
}


def _fn32():
    expect(decide(snap(Record({'journal': 'complete'}))).kind).to_be('done')
test('a complete journal is done', _fn32)

def _fn33():
    expect(decide(snap(Record({'journal': 'unknown'}))).kind).to_be('wait')
test('an unloaded journal waits rather than restarting the quest', _fn33)

def _fn34():
    expect(decide(snap(Record({'stage': None}))).kind).to_be('wait')
test('an unreadable stage waits', _fn34)

def _fn35():
    step = decide(snap(Record({'journal': 'complete', 'tile': Record({'x': 2774, 'z': 9301, 'level': 0})})))
    expect(name(step)).to_be('custom:climb back out of the caves')
test('a complete quest still climbs out of the caves before it stops', _fn35)

# Why: the shopping now runs ahead of Radimus, so an empty bank shops first, the walk to him is what happens once both counters have been emptied into it.
def _fn36():
    step = decide(snap(Record({'journal': 'not_started', 'stage': LQ_STAGE.NOT_STARTED})))
    expect(step.kind).to_be('buy')
test('not started shops before it asks Radimus for the quest', _fn36)

# Why: `quest_legends.rs2` counts the bank as well as the pack, "I hear that you have enough machetes in your bank to start your own store" and it hands over nothing, so the cupboard step failed for ever against a banked one.
def _fn37():
    step = decide(snap(Record({'stage': LQ_STAGE.STARTED, 'bank_ids': [LQ_ID.MACHETE], 'bank': ['Machete']})))
    expect(step.kind).to_be('withdraw')
    expect(step.kind == 'withdraw' and step.items[0]['name']).to_be('Machete')
test('a banked machete is withdrawn rather than asked of the cupboard', _fn37)

def _fn38():
    step = decide(snap(Record({'stage': LQ_STAGE.STARTED})))
    expect(name(step)).to_be("custom:take the machete from Radimus' cupboard")
test('started with no machete takes one from the cupboard', _fn38)

# Why: the kit fixture carries the finished copy, which is the one thing that means the mapping is over, so a snapshot about to map holds the blank notes instead.
def _fn39():
    blank = kitted(Record({'stage': LQ_STAGE.STARTED}))
    notes = without(blank, [LQ_ID.MAP_COMPLETE])
    notes.inv_ids[LQ_ID.MAP] = 1
    expect(name(decide(notes))).to_be('custom:map all three thirds of the Kharazi Jungle')
test('started with the kit and blank notes maps the jungle', _fn39)

# Why: `radimus_notes.rs2` swaps the notes for the copy and only then advances the stage, and it clears the three section bits as it goes, so the copy in the pack with the stage still at one is a state the loop can reach, and `mapJungle` answers true in no time at all from there, which the engine hands straight back for ever.
def _fn41():
    done = kitted(Record({'stage': LQ_STAGE.STARTED}))
    expect(name(decide(done))).not_.to_be('custom:map all three thirds of the Kharazi Jungle')
test('the finished copy ends the mapping whatever the stage says', _fn41)

def _fn42():
    mapped = snap(Record({
    'stage': LQ_STAGE.MAPPED_JUNGLE,
    'inv_ids': [LQ_ID.MAP_COMPLETE, LQ_ID.MACHETE, LQ_ID.RUNE_AXE, LQ_ID.COINS],
    'inv': ['Lobster'] * 14 + ['Coins'],
}))
    expect(name(decide(mapped))).to_be('custom:trade a copy of the map for the bull roarer')
test('a mapped jungle trades the copy for the bull roarer', _fn42)

# Why: a death drops the roarer and the map together, at a stage where the trade branch is long behind the run.
def _fn43():
    bare = without(kitted(Record({'stage': LQ_STAGE.POOL_DRIED})), [LQ_ID.BULLROARER])
    expect(name(decide(bare))).to_be('custom:trade a copy of the map for the bull roarer')
test('a roarer lost after the trade is replaced wherever the run has got to', _fn43)

# Why: the forester wants a map to copy, and Radimus only offers a replacement while neither map is held.
def _fn44():
    bare = without(kitted(Record({'stage': LQ_STAGE.POOL_DRIED})), [LQ_ID.BULLROARER, LQ_ID.MAP_COMPLETE, LQ_ID.MAP])
    expect(name(decide(bare))).to_be('custom:buy a replacement map from Radimus')
test('a roarer and a map both lost buy the map back first', _fn44)

def _fn45():
    step = decide(kitted(Record({'stage': LQ_STAGE.GOT_BULLROARER, 'inv_ids': [LQ_ID.BULLROARER]})))
    expect(name(step)).to_be('custom:swing the bull roarer and befriend Gujuo')
test('with the roarer in hand the next step is Gujuo', _fn45)

def _fn46():
    step = decide(kitted(Record({'stage': LQ_STAGE.ACCEPTED_RESCUE, 'inv_ids': [LQ_ID.BULLROARER]})))
    expect(name(step)).to_be('custom:find Ungadulu and talk through the flames')
test('the rescue stage goes to the shaman cave', _fn46)

def _fn47():
    step = decide(kitted(Record({'stage': LQ_STAGE.SPOKE_UNGADULU, 'inv_ids': [LQ_ID.BULLROARER]})))
    expect(name(step)).to_be('custom:ask Gujuo where the sacred water is')
test('after Ungadulu the quest asks Gujuo about the water', _fn47)

def _fn48():
    step = decide(kitted(Record({'stage': LQ_STAGE.ASKED_GUJUO_WATER, 'inv_ids': [LQ_ID.GOLD_BOWL_SKETCH]})))
    expect(name(step)).to_be('custom:hammer two gold bars into a golden bowl')
test('with the sketch and two bars the bowl is forged', _fn48)

def _fn49():
    step = decide(kitted(Record({'stage': LQ_STAGE.ASKED_GUJUO_WATER, 'inv_ids': [LQ_ID.GOLD_BOWL]})))
    expect(name(step)).to_be('custom:have Gujuo bless the golden bowl')
test('an unblessed bowl goes to Gujuo', _fn49)

def _fn50():
    step = decide(kitted(Record({'stage': LQ_STAGE.ASKED_GUJUO_WATER, 'inv_ids': [LQ_ID.GOLD_BOWL_BLESSED]})))
    expect(name(step)).to_be('custom:cut a hollow reed at the sacred pool')
test('a blessed bowl and no reed cuts one', _fn50)

def _fn51():
    step = decide(kitted(Record({'stage': LQ_STAGE.ASKED_GUJUO_WATER, 'inv_ids': [LQ_ID.GOLD_BOWL_BLESSED, LQ_ID.HOLLOW_REED]})))
    expect(name(step)).to_be('custom:syphon the sacred pool into the blessed bowl')
test('a reed and a blessed bowl fill it at the pool', _fn51)

def _fn52():
    step = decide(kitted(Record({'stage': LQ_STAGE.FILLED_BOWL, 'inv_ids': [LQ_ID.GOLD_BOWL_BLESSED_PURE]})))
    expect(name(step)).to_be('custom:fetch the Book of Binding from the gem room')
test('a full bowl and no book goes down the trials', _fn52)

def _fn53():
    step = decide(kitted(Record({
    'stage': LQ_STAGE.FILLED_BOWL,
    'inv_ids': [LQ_ID.GOLD_BOWL_BLESSED_PURE, LQ_ID.BOOK_OF_BINDING, PRAYER_POTIONS[0].id],
})))
    expect(name(step)).to_be('custom:open the Book of Binding on Ungadulu')
test('book plus water opens it on Ungadulu', _fn53)

def _fn54():
    step = decide(kitted(Record({'stage': LQ_STAGE.DEFEATED_NEZI_FIRE})))
    expect(name(step)).to_be('custom:ask Ungadulu for the Yommi tree seeds')
test('the freed shaman is asked for seeds', _fn54)

def _fn55():
    step = decide(kitted(Record({'stage': LQ_STAGE.DEFEATED_NEZI_FIRE, 'inv_ids': [LQ_ID.YOMMI_SEEDS, LQ_ID.GOLD_BOWL_BLESSED_PURE]})))
    expect(name(step)).to_be('custom:germinate the seeds in the bowl of sacred water')
test('raw seeds and a full bowl germinate', _fn55)

def _fn56():
    step = decide(kitted(Record({'stage': LQ_STAGE.GERMINATED_SEEDS, 'inv_ids': [LQ_ID.YOMMI_SEEDS_GERM]})))
    expect(name(step)).to_be('custom:find the sacred pool fouled')
test('germinated seeds go looking for the fouled pool', _fn56)

def _fn57():
    step = decide(kitted(Record({'stage': LQ_STAGE.POOL_DRIED})))
    expect(name(step)).to_be('custom:ask Gujuo for the bravery potion recipe')
test('a dried pool asks Gujuo for the potion recipe', _fn57)

def _fn58():
    step = decide(kitted(Record({'stage': LQ_STAGE.TALK_GUJUO_POOL})))
    expect(name(step)).to_be('custom:pick the Snake weed')
test('the potion stage picks the first herb it is missing', _fn58)

def _fn59():
    step = decide(kitted(Record({'stage': LQ_STAGE.TALK_GUJUO_POOL, 'inv_ids': [LQ_ID.UNID_SNAKE_WEED]})))
    expect(name(step)).to_be('custom:identify the Snake weed')
test('an unidentified herb is identified before the next one is picked', _fn59)

def _fn60():
    step = decide(kitted(Record({'stage': LQ_STAGE.TALK_GUJUO_POOL, 'inv_ids': [LQ_ID.SNAKE_WEED, LQ_ID.ARDRIGAL]})))
    expect(step.kind).to_be('use_on')
test('both herbs and a vial mix the snakeweed first', _fn60)

def _fn61():
    step = decide(kitted(Record({'stage': LQ_STAGE.TALK_GUJUO_POOL, 'inv_ids': [LQ_ID.SNAKEWEED_MIXTURE, LQ_ID.ARDRIGAL]})))
    expect(step.kind).to_be('use_on')
    expect(step.kind == 'use_on' and step.product).to_be('Bravery potion')
test('a mixture and ardrigal finish the potion', _fn61)

def _fn62():
    step = decide(kitted(Record({'stage': LQ_STAGE.TALK_GUJUO_POOL, 'inv_ids': [LQ_ID.BRAVERY_POTION]})))
    expect(name(step)).to_be('custom:climb down the winch into the Viyeldi caves')
test('the potion in the pack climbs down the winch', _fn62)

def _fn63():
    step = decide(kitted(Record({'stage': LQ_STAGE.ENTER_LOWER_DUNGEON, 'tile': Record({'x': 2400, 'z': 4710, 'level': 0})})))
    expect(name(step)).to_be('custom:take the dragon heart off the three guardians')
test('the lower dungeon fights the three guardians', _fn63)

def _fn64():
    step = decide(kitted(Record({
    'stage': LQ_STAGE.CRYSTAL_SMELTED,
    'inv_ids': [LQ_ID.HEART_CRYSTAL],
    'tile': Record({'x': 2400, 'z': 4710, 'level': 0}),
})))
    expect(name(step)).to_be("custom:charge the heart on the dragon's eye")
test('a fused heart is charged on the dragon eye', _fn64)

def _fn65():
    step = decide(kitted(Record({
    'stage': LQ_STAGE.CRYSTAL_SMELTED,
    'inv_ids': [LQ_ID.HEART_CRYSTAL_GLOW],
    'tile': Record({'x': 2400, 'z': 4710, 'level': 0}),
})))
    expect(name(step)).to_be('custom:slot the glowing heart into the recess')
test('a glowing heart goes into the recess', _fn65)

def _fn66():
    step = decide(kitted(Record({
    'stage': LQ_STAGE.RECEIVED_DAGGER,
    'inv_ids': [LQ_ID.DEATH_DAGGER],
    'tile': Record({'x': 2387, 'z': 4689, 'level': 0}),
})))
    expect(name(step)).to_be('custom:take the black dagger to Ungadulu')
test('the black dagger goes up to Ungadulu rather than into Viyeldi', _fn66)

def _fn67():
    step = decide(kitted(Record({
    'stage': LQ_STAGE.RECEIVED_DAGGER,
    'inv_ids': [LQ_ID.HOLY_FORCE],
    'tile': Record({'x': 2387, 'z': 4689, 'level': 0}),
})))
    expect(name(step)).to_be('custom:read the Holy Force at the spirit and kill it')
test('the Holy Force is read at the spirit', _fn67)

def _fn68():
    step = decide(kitted(Record({
    'stage': LQ_STAGE.DEFEATED_NEZI_WATER,
    'inv_ids': [LQ_ID.GOLD_BOWL_BLESSED],
    'tile': Record({'x': 2387, 'z': 4689, 'level': 0}),
})))
    expect(name(step)).to_be('custom:shift the boulder and fill the bowl at the source')
test('the source is bottled once the demon is down', _fn68)

def _fn69():
    step = decide(kitted(Record({'stage': LQ_STAGE.SACRED_WATER, 'inv_ids': [LQ_ID.GOLD_BOWL_BLESSED_PURE, LQ_ID.YOMMI_SEEDS_GERM]})))
    expect(name(step)).to_be('custom:grow a Yommi tree and carve a totem pole')
test('sacred water and germinated seeds grow the tree', _fn69)

def _fn70():
    step = decide(kitted(Record({'stage': LQ_STAGE.COLLECTED_TOTEM, 'inv_ids': [PRAYER_POTIONS[0].id, LQ_ID.TOTEM_POLE]})))
    expect(name(step)).to_be('custom:replace the evil totem and kill what comes out')
test('a carved pole is taken to an evil totem', _fn70)

def _fn71():
    step = decide(kitted(Record({'stage': LQ_STAGE.DEFEATED_NEZI_FINAL})))
    expect(name(step)).to_be('custom:collect the gilded totem from Gujuo')
test('with the pole gone the gift comes from Gujuo', _fn71)

def _fn72():
    step = decide(kitted(Record({'stage': LQ_STAGE.GOT_GILDED_TOTEM, 'inv_ids': [LQ_ID.GILDED_TOTEM]})))
    expect(name(step)).to_be('custom:take the gilded totem to Radimus')
test('the gilded totem goes back to Radimus', _fn72)

def _fn73():
    for stage in [
    LQ_STAGE.RETURNED_TO_RADIMUS,
    LQ_STAGE.TRAINING_1,
    LQ_STAGE.TRAINING_2,
    LQ_STAGE.TRAINING_3,
    LQ_STAGE.TRAINING_4,
]:
        expect(name(decide(kitted(Record({'stage': stage}))))).to_be("custom:take Radimus' four training sessions")
test('the last stages take the four training sessions', _fn73)

# Why: `jungle_tree` boils a filled bowl dry on every chop, so the last errand off the island runs before the pool.
def _fn74():
    jungle = Record({'x': 2820, 'z': 2915, 'level': 0})
    bare = snap(Record({'stage': LQ_STAGE.FILLED_BOWL, 'inv_ids': [LQ_ID.GOLD_BOWL_BLESSED], 'tile': jungle}))
    expect(name(decide(bare))).to_be('custom:cut back out of the Kharazi Jungle')
    ready = kitted(Record({
    'stage': LQ_STAGE.FILLED_BOWL,
    'inv_ids': [LQ_ID.GOLD_BOWL_BLESSED, LQ_ID.BOOK_OF_BINDING, PRAYER_POTIONS[0].id],
    'tile': jungle,
}))
    expect(name(decide(ready))).to_be('custom:cut a hollow reed at the sacred pool')
test('the trials kit is fetched before the bowl is filled', _fn74)

# Why: `potsFor` answers zero the moment the bowl is blessed, which is stage 8, and the spent list is a DROP, so a live run threw the flask on the floor at a booth with three demon fights still ahead.
def _fn75():
    mid_quest = kitted(Record({'stage': LQ_STAGE.ASKED_GUJUO_WATER, 'inv_ids': [LQ_ID.GOLD_BOWL_BLESSED, PRAYER_POTIONS[0].id]}))
    expect(PRAYER_POTIONS[0].id in spent_now(mid_quest.with_fields({'free_slots': 1}))).to_be(False)
test('a prayer flask is not spent while a demon is still alive', _fn75)

# Why: once the last demon is dead the flask is a slot and nothing else.
def _fn77():
    done = kitted(Record({'stage': LQ_STAGE.DEFEATED_NEZI_FINAL, 'inv_ids': [PRAYER_POTIONS[0].id, LQ_ID.SWAMP_ROCK]}))
    step = decide(done.with_fields({'free_slots': 1}))
    expect(name(step)).to_be('custom:drop what the quest has finished with')
test('a prayer flask is spent once the last demon is dead', _fn77)

# Why: `stageBowl` fetches the fight kit while the bowl is empty, so a run arriving here with it already filled never went through that, and the octagram is in the caves, where `choose` never reaches its upkeep.
def _fn79():
    dry = kitted(Record({
    'stage': LQ_STAGE.FILLED_BOWL,
    'inv_ids': [LQ_ID.GOLD_BOWL_BLESSED_PURE, LQ_ID.BOOK_OF_BINDING],
    'bank_ids': [PRAYER_POTIONS[0].id, PRAYER_POTIONS[0].id, PRAYER_POTIONS[0].id],
    'bank': ['Prayer potion(4)', 'Coins'],
}))
    expect(name(decide(dry))).not_.to_be('custom:open the Book of Binding on Ungadulu')
test('a filled bowl and no flask goes for the flask before the book', _fn79)

# Why: `stat_sub(prayer, 0, 90)` runs as the book opens, and `potionTopUp` answers null when the bank is empty, which walked a filled bowl and an empty prayer book into the demon and said nothing.
def _fn80():
    jungle = Record({'x': 2820, 'z': 2915, 'level': 0})
    dry = kitted(Record({
    'stage': LQ_STAGE.FILLED_BOWL,
    'inv_ids': [LQ_ID.GOLD_BOWL_BLESSED, LQ_ID.BOOK_OF_BINDING],
    'tile': jungle,
}))
    step = decide(dry)
    expect(step.kind).to_be('wait')
    expect(step.kind == 'wait' and step.reason).to_contain('prayer potion')
test('no flask in the pack or the bank parks before the book is opened', _fn80)

def _fn81():
    step = decide(kitted(Record({'stage': LQ_STAGE.FILLED_BOWL, 'inv_ids': [LQ_ID.GOLD_BOWL_BLESSED_PURE]})))
    expect(name(step)).to_be('custom:fetch the Book of Binding from the gem room')
test('a filled bowl on the mainland is never sent back to a booth', _fn81)

# Why: three aggressive guardians wait at the bottom of the winch and the trials float of five lobsters is what died to them.
def _fn82():
    lean = snap(Record({
    'stage': LQ_STAGE.ENTER_LOWER_DUNGEON,
    'inv_ids': [LQ_ID.RUNE_AXE],
    'bank': ['Lobster'] * 30,
}))
    step = decide(lean.with_fields({'free_slots': 12}))
    expect(step.kind).to_be('withdraw')
    expect(step.kind == 'withdraw' and step.items[0]['qty']).to_be(9)
test('the winch stages take the fight float, not the trials one', _fn82)

# Why: a death drops the machete and the axe, and every leg past the map has to cross the band to get anywhere.
def _fn84():
    lean = snap(Record({
    'stage': LQ_STAGE.DEFEATED_NEZI_FIRE,
    'inv_ids': [LQ_ID.RUNE_AXE],
    'inv': ['Lobster'] * 14,
    'bank_ids': [LQ_ID.MACHETE],
}))
    step = decide(lean)
    expect(step.kind).to_be('withdraw')
    expect(step.kind == 'withdraw' and step.items[0]['name']).to_be('Machete')
test('a lost machete is replaced like food', _fn84)

# Why: the octagram demon is level 187 with 150 hitpoints and the trials float of five lobsters is what died to him.
def _fn85():
    lean = snap(Record({
    'stage': LQ_STAGE.FILLED_BOWL,
    'inv_ids': [LQ_ID.GOLD_BOWL_BLESSED, LQ_ID.BOOK_OF_BINDING],
    'bank': ['Lobster'] * 30,
}))
    step = decide(lean.with_fields({'free_slots': 12}))
    expect(step.kind).to_be('withdraw')
    expect(step.kind == 'withdraw' and step.items[0]['qty']).to_be(9)
    # Why: the ask is what the pack can take rather than what the leg wanted, after a death the kit comes back at once and nine lobsters have nowhere to go.
    tight = decide(lean.with_fields({'free_slots': 3}))
    expect(tight.kind == 'withdraw' and tight.items[0]['qty']).to_be(3)
test('the book in the pack raises the float to the fight numbers', _fn85)

# Why: `stat_sub(prayer, 0, 90)` runs as Nezikchened is summoned, so the fight opens on a tenth of the bar and Protect from Melee is only armour if there is a dose to put it back. A pack topped up on lobsters first has no slot to put one in.
def _fn88():
    lean = snap(Record({
    'stage': LQ_STAGE.FILLED_BOWL,
    'inv_ids': [LQ_ID.GOLD_BOWL_BLESSED, LQ_ID.BOOK_OF_BINDING],
    'bank_ids': [PRAYER_POTIONS[0].id, PRAYER_POTIONS[0].id, PRAYER_POTIONS[0].id],
    'bank': ['Lobster'] * 30,
}))
    step = decide(lean.with_fields({'free_slots': 12}))
    expect(step.kind).to_be('withdraw')
    expect(step.kind == 'withdraw' and step.items[0]['name']).to_be(PRAYER_POTIONS[0].name)
test('a banked prayer flask is fetched before the fight food', _fn88)

# Why: replacing the totem spawns Nezikchened on the spot, and the totems stand in the jungle where the upkeep branch never runs, so the kit is asked for at the step or the demon gets what the fight before it left.
def _fn90():
    bare = snap(Record({
    'stage': LQ_STAGE.COLLECTED_TOTEM,
    'inv_ids': [LQ_ID.TOTEM_POLE, LQ_ID.COINS],
    'inv': ['Coins'],
    'bank_ids': [LQ_ID.COINS, PRAYER_POTIONS[0].id] + [LQ_ID.SHARK] * 20,
    'bank': ['Coins', 'Prayer potion(4)', 'Shark'],
}))
    expect(name(decide(bare))).not_.to_be('custom:replace the evil totem and kill what comes out')
test('the last demon is kitted for before the totem is replaced', _fn90)

# Why: nothing after the last demon is a fight, so a flask fetched on the way to hand the totem in is a bank trip for something the quest will never drink.
def _fn91():
    done = kitted(Record({
    'stage': LQ_STAGE.GOT_GILDED_TOTEM,
    'inv_ids': [LQ_ID.GILDED_TOTEM],
    'bank_ids': [PRAYER_POTIONS[0].id],
    'bank': ['Prayer potion(4)', 'Coins'],
}))
    expect(name(decide(done))).to_be('custom:take the gilded totem to Radimus')
test('the gilded totem is walked to Radimus, not taken shopping', _fn91)

# Why: the outer gate shuts behind whoever picked it and the boulders drop back down, so a second descent is paid for in full.
def _fn92():
    kit = [
    LQ_ID.RUNE_AXE,
    LQ_ID.MACHETE,
    LQ_ID.BULLROARER,
    LQ_ID.YOMMI_SEEDS_GERM,
    LQ_ID.UNPOWERED_ORB,
    LQ_ID.COSMIC_RUNE,
    LQ_ID.COSMIC_RUNE,
    LQ_ID.COSMIC_RUNE,
]
    lean = snap(Record({
    'stage': LQ_STAGE.SACRED_WATER,
    'inv_ids': list(kit) + [LQ_ID.WATER_RUNE] * 30,
    'inv': ['Lobster'] * 14,
    'bank_ids': [LQ_ID.LOCKPICK, LQ_ID.RUNE_PICKAXE],
}))
    step = decide(lean)
    expect(step.kind).to_be('withdraw')
    expect(step.kind == 'withdraw' and step.items[0]['name']).to_be('Lockpick')
test('a re-descent fetches the lockpick and pickaxe again', _fn92)

# Why: the Holy Force trade happens inside the octagram, and the descent it is followed by has not been paid for yet.
def _fn93():
    octagram = Record({'x': 2792, 'z': 9327, 'level': 0})
    lean = snap(Record({
    'stage': LQ_STAGE.DEFEATED_NEZI_WATER,
    'inv_ids': [LQ_ID.RUNE_AXE, LQ_ID.MACHETE, LQ_ID.GOLD_BOWL_BLESSED],
    'inv': ['Lobster'] * 14,
    'bank_ids': [LQ_ID.LOCKPICK, LQ_ID.UNPOWERED_ORB],
    'tile': octagram,
}))
    expect(name(decide(lean))).to_be('custom:climb back out of the caves')
test('a leg that starts beside Ungadulu still fetches the descent kit', _fn93)

# Why: the magic gate eats the orb as it lets you through, so the same check made from the winch room turns a finished descent back round.
def _fn94():
    winch_room = Record({'x': 2763, 'z': 9320, 'level': 0})
    lean = snap(Record({
    'stage': LQ_STAGE.SACRED_WATER,
    'inv_ids': [LQ_ID.RUNE_AXE, LQ_ID.MACHETE, LQ_ID.YOMMI_SEEDS_GERM, LQ_ID.LOCKPICK, LQ_ID.RUNE_PICKAXE],
    'inv': ['Lobster'] * 14,
    'bank_ids': [LQ_ID.UNPOWERED_ORB],
    'tile': winch_room,
}))
    expect(name(decide(lean))).to_be('custom:climb back down to the Viyeldi caves')
test('a spent orb below the gate does not send the run back up for another', _fn94)

# Why: a full pack is the normal state of this quest, so only a pending withdraw is a reason to walk to a booth.
def _fn95():
    pool = Record({'x': 2836, 'z': 2917, 'level': 0})
    full = kitted(Record({
    'stage': LQ_STAGE.FILLED_BOWL,
    'inv_ids': [LQ_ID.GOLD_BOWL_BLESSED, LQ_ID.BOOK_OF_BINDING, 2434, 2434],
    'tile': pool,
}))
    step = decide(full.with_fields({'free_slots': 0}))
    expect(step.kind).to_be('custom')
    expect(step.kind).not_.to_be('deposit')
test('a full pack alone does not send the run to a booth', _fn95)

# Why: a sketch, a spell and a set of seeds are all handed over into a pack that has to have room for them.
def _fn97():
    cave = Record({'x': 2791, 'z': 9334, 'level': 0})
    full = kitted(Record({'stage': LQ_STAGE.RECEIVED_DAGGER, 'inv_ids': [LQ_ID.DEATH_DAGGER, 594, 594, 594], 'tile': cave}))
    expect(name(decide(full.with_fields({'free_slots': 0})))).to_be('custom:drop what the quest has finished with')
test('a full pack drops the spent supplies rather than banking them', _fn97)

# Why: the sketch and the flask are both spent the moment the bowl is blessed, and the trials kit is one rune stack short of the pack without their slots.
def _fn99():
    spent = kitted(Record({'stage': LQ_STAGE.ASKED_GUJUO_WATER, 'inv_ids': [LQ_ID.GOLD_BOWL_BLESSED, LQ_ID.GOLD_BOWL_SKETCH, 2434]}))
    expect(name(decide(spent.with_fields({'free_slots': 0})))).to_be('custom:drop what the quest has finished with')
test('the sketch and the used flask are spent once the bowl is blessed', _fn99)

# Why: the flask is the blessing's until the blessing happens, and dropping it there is a bank trip and a re-buy for nothing.
def _fn101():
    plain = snap(Record({
    'stage': LQ_STAGE.ASKED_GUJUO_WATER,
    'inv_ids': [LQ_ID.GOLD_BOWL, 2434, LQ_ID.MACHETE, LQ_ID.RUNE_AXE, LQ_ID.COINS],
    'inv': ['Lobster'] * 14 + ['Coins'],
}))
    expect(name(decide(plain.with_fields({'free_slots': 0})))).not_.to_be('custom:drop what the quest has finished with')
test('the flask is not spent while the bowl is still plain', _fn101)

# Why: a shop counter is not a booth, so a full pack at one has nothing to deposit and the buy failed a hundred and thirty times in a row.
def _fn103():
    full = snap(Record({
    'stage': LQ_STAGE.ASKED_GUJUO_WATER,
    'inv_ids': [LQ_ID.GOLD_BOWL_BLESSED, LQ_ID.MACHETE, LQ_ID.RUNE_AXE, LQ_ID.COINS, LQ_ID.LOBSTER],
    'inv': ['Lobster'] * 14 + ['Coins'],
    'bank_ids': [LQ_ID.LOCKPICK],
    'bank': ['Coins'],
}))
    expect(decide(full.with_fields({'free_slots': 0})).kind).to_be('custom')
test('a full pack at a counter with nothing bankable still makes room', _fn103)

# Why: a withdraw decided with no room fails for ever, and the trials and the band both hand back things the keep list does not want.
# Why: the reserve rather than the last slot is the trigger, a step already opening the bank pays nothing to empty the pack there, and every hand-over this quest makes wants a slot a pack shed only when full does not have.
def _fn105():
    full = snap(Record({
    'stage': LQ_STAGE.SACRED_WATER,
    'inv_ids': [LQ_ID.RUNE_AXE, LQ_ID.MACHETE, LQ_ID.YOMMI_SEEDS_GERM, 1511, 1511],
    'inv': ['Lobster'] * 14,
    'bank_ids': [LQ_ID.LOCKPICK, LQ_ID.UNPOWERED_ORB],
    'bank': ['Coins'],
}))
    expect(decide(full.with_fields({'free_slots': 0})).kind).to_be('deposit')
    expect(decide(full.with_fields({'free_slots': 3})).kind).to_be('deposit')
    expect(decide(full.with_fields({'free_slots': 20})).kind).to_be('withdraw')
test('a pack down to its reserve banks the junk at the booth the withdraw was going to', _fn105)

# Why: a junk item the bank will not take leaves the free count where it was, so a deposit chosen on "any junk at all" would be chosen again in place of the withdraw for ever.
def _fn109():
    roomy = snap(Record({
    'stage': LQ_STAGE.SACRED_WATER,
    'inv_ids': [LQ_ID.RUNE_AXE, LQ_ID.MACHETE, LQ_ID.YOMMI_SEEDS_GERM, 1511],
    'inv': ['Lobster'] * 14,
    'bank_ids': [LQ_ID.LOCKPICK, LQ_ID.UNPOWERED_ORB],
    'bank': ['Coins'],
}))
    expect(decide(roomy.with_fields({'free_slots': 20})).kind).to_be('withdraw')
test('junk well clear of the reserve rides along rather than costing a deposit', _fn109)

# Why: a live run withdrew five lobsters into its last five slots and dropped four lumps of rock on the next pass, the float came out four short and the drop bought nothing.
def _fn111():
    rocky = snap(Record({
    'stage': LQ_STAGE.TALK_GUJUO_POOL,
    'inv_ids': [LQ_ID.RUNE_AXE, LQ_ID.MACHETE, LQ_ID.COINS] + [LQ_ID.SWAMP_ROCK] * 4,
    'inv': ['Coins'],
    'bank_ids': [LQ_ID.COINS] + [LQ_ID.LOBSTER] * 20,
    'bank': ['Coins', 'Lobster'],
}))
    expect(name(decide(rocky.with_fields({'free_slots': 5})))).to_be('custom:drop what the quest has finished with')
test('what the quest is finished with goes out before the bank hands anything over', _fn111)

# Why: a random event's gift takes the slot the reed wants, and nothing is walking to a bank to be rid of it.
def _fn113():
    jungle = Record({'x': 2836, 'z': 2917, 'level': 0})
    full = snap(Record({
    'stage': LQ_STAGE.ASKED_GUJUO_WATER,
    'inv_ids': [LQ_ID.GOLD_BOWL_BLESSED, LQ_ID.MACHETE, LQ_ID.COINS, 4566],
    'inv': ['Lobster'] * 14 + ['Coins'],
    'tile': jungle,
}))
    expect(name(decide(full.with_fields({'free_slots': 0})))).to_be('custom:drop what the quest has no use for')
    expect(name(decide(full.with_fields({'free_slots': 3})))).not_.to_be('custom:drop what the quest has no use for')
test('a full pack drops a random event gift when the step is not going to a bank', _fn113)

# Why: twenty-eight wanted things leave no slot for the herb the step is about to pick, and there is nothing spent or junk to shed.
def _fn116():
    jungle = Record({'x': 2836, 'z': 2917, 'level': 0})
    full = snap(Record({
    'stage': LQ_STAGE.ASKED_GUJUO_WATER,
    'inv_ids': [LQ_ID.GOLD_BOWL_BLESSED, LQ_ID.MACHETE, LQ_ID.COINS, LQ_ID.LOBSTER],
    'inv': ['Lobster'] * 14 + ['Coins'],
    'tile': jungle,
}))
    expect(name(decide(full.with_fields({'free_slots': 0})))).to_be('custom:eat a lobster to make room')
    expect(name(decide(full.with_fields({'free_slots': 3})))).not_.to_be('custom:eat a lobster to make room')
test('a full pack of wanted things eats a lobster for the slot', _fn116)

# Why: the rock rolls opal 60/128, so the wait for the last gem fills the pack with uncut opals the keep list protects and the deposit will not take.
def _fn119():
    full = at_the_gem_rocks([LQ_ID.OPAL, LQ_ID.UNCUT_OPAL, LQ_ID.UNCUT_OPAL])
    expect(name(decide(full.with_fields({'free_slots': 0})))).to_be('custom:drop what the quest has no use for')
    expect(name(decide(full.with_fields({'free_slots': 3})))).to_be('custom:mine a gem (6 of seven still missing)')
test('a full pack drops the uncut gems whose cut stone is already in hand', _fn119)

# Why: an uncut gem whose stone has not been cut yet is the chisel step's input, not junk, and dropping it re-mines the rarest roll on the rock.
def _fn122():
    full = at_the_gem_rocks([LQ_ID.UNCUT_DIAMOND])
    expect(name(decide(full.with_fields({'free_slots': 0})))).not_.to_be('custom:drop what the quest has no use for')
test('the uncut gem still waiting on the chisel is not dropped', _fn122)

# Why: the trance takes five prayer points on every miss and refuses below forty-two, so seventy runs out before the bowl is blessed unless a flask goes with it.
def _fn124():
    with_bowl = snap(Record({
    'stage': LQ_STAGE.ASKED_GUJUO_WATER,
    'inv_ids': [LQ_ID.GOLD_BOWL, LQ_ID.MACHETE, LQ_ID.RUNE_AXE, LQ_ID.COINS],
    'inv': ['Coins'] + ['Lobster'] * 14,
    'bank_ids': [2434],
    'bank': ['Prayer potion(4)', 'Coins'],
}))
    step = decide(with_bowl)
    expect(step.kind).to_be('withdraw')
    expect(step.items[0]['name']).to_be('Prayer potion(4)')
test('the plain golden bowl takes a prayer flask to the blessing', _fn124)

# Why: once the bowl is blessed the flask is the demon's, not the blessing's, and asking for one here is a bank trip the leg does not need.
def _fn125():
    blessed = kitted(Record({
    'stage': LQ_STAGE.ASKED_GUJUO_WATER,
    'inv_ids': [LQ_ID.GOLD_BOWL_BLESSED],
    'bank_ids': [2434],
    'bank': ['Prayer potion(4)'],
}))
    expect(name(decide(blessed))).not_.to_be('withdraw')
test('the blessed bowl asks for no flask of its own', _fn125)

# Why: the book is gone from the pack once it is read, which is not the same as never having had it.
def _fn126():
    jungle = Record({'x': 2820, 'z': 2915, 'level': 0})
    bare = snap(Record({
    'stage': LQ_STAGE.DEFEATED_NEZI_FIRE,
    'inv_ids': [LQ_ID.GOLD_BOWL_BLESSED, LQ_ID.YOMMI_SEEDS, LQ_ID.KNIFE],
    'inv': ['Lobster'] * 14,
    'tile': jungle,
}))
    expect(name(decide(bare))).to_be('custom:cut a hollow reed at the sacred pool')
test('the trials kit is not re-bought after the book has been read', _fn126)

# Why: every leg below the winch stands on a tile no surface path reaches, so a resumed run has to climb down before it acts.
def _fn127():
    surface = Record({'x': 2800, 'z': 3000, 'level': 0})
    stages = [
    LQ_STAGE.ENTER_LOWER_DUNGEON,
    LQ_STAGE.CRYSTAL_SMELTED,
    LQ_STAGE.HEART_IN_RECESS,
    LQ_STAGE.PUSHED_BOULDER,
    LQ_STAGE.DEFEATED_NEZI_WATER,
]
    for stage in stages:
        step = decide(kitted(Record({'stage': stage, 'inv_ids': [LQ_ID.GOLD_BOWL_BLESSED], 'tile': surface})))
        expect(name(step)).to_be('custom:climb back down to the Viyeldi caves')
test('every Viyeldi leg descends first when the run is on the surface', _fn127)

def _fn128():
    surface = Record({'x': 2800, 'z': 3000, 'level': 0})
    step = decide(kitted(Record({'stage': LQ_STAGE.RECEIVED_DAGGER, 'inv_ids': [LQ_ID.DEATH_DAGGER], 'tile': surface})))
    expect(name(step)).to_be('custom:take the black dagger to Ungadulu')
test('the dagger hand-in climbs up to Ungadulu rather than back down', _fn128)

# Why: a branch that acts from inside a sealed pocket sends the walker at a tile on the wrong side of a one-way crossing.
def _fn129():
    in_caves = Record({'x': 2774, 'z': 9301, 'level': 0})
    for stage in [LQ_STAGE.NOT_STARTED, LQ_STAGE.GOT_GILDED_TOTEM, LQ_STAGE.TRAINING_1]:
        step = decide(kitted(Record({'stage': stage, 'inv_ids': [LQ_ID.GILDED_TOTEM, LQ_ID.YOMMI_SEEDS_GERM], 'tile': in_caves})))
        expect(name(step)).to_be('custom:climb back out of the caves')
test('every mainland leg escapes the caves first', _fn129)

def _fn130():
    step = decide(snap(Record({'stage': LQ_STAGE.STARTED, 'tile': Record({'x': 100, 'z': 9000, 'level': 0})})))
    expect(step.kind).to_be('wait')
test('an unknown location waits rather than guessing', _fn130)




def _fn131():
    def _fn132():
        expect(any([def_.record.id == 'legends' for def_ in QUEST_DEFS])).to_be(True)
    test('is registered in the quest list', _fn132)

    def _fn133():
        expect(legends.owns_inventory).to_be(True)
        expect(legends.coin_float).to_be(0)
    test('owns its own inventory and carries no engine coin float', _fn133)

    # Why: the float is drawn best-first, since every fight in this quest is one it has to outlast.
    def _fn134():
        expect(list(LQ_FOODS)).to_equal(['Shark', 'Swordfish', 'Lobster', 'Tuna'])
        expect(legends.sustain.foods[0]).to_be('Shark')
    test('prefers shark, then swordfish, then lobster, then tuna', _fn134)

    # Why: a slot is bought with the worst food held, which is the opposite order. The point is to keep the heal the demon needs.
    def _fn135():
        expect([f.name for f in FOOD_FOR_SLOT]).to_equal(['Tuna', 'Lobster', 'Swordfish', 'Shark'])
    test('buys a slot with the worst food, not the best', _fn135)

    def _fn136():
        for id in [
        LQ_ID.MAP,
        LQ_ID.MAP_COMPLETE,
        LQ_ID.BULLROARER,
        LQ_ID.GOLD_BOWL_BLESSED_PURE,
        LQ_ID.BOOK_OF_BINDING,
        LQ_ID.YOMMI_SEEDS_GERM,
        LQ_ID.HEART_CRYSTAL_GLOW,
        LQ_ID.DEATH_DAGGER,
        LQ_ID.HOLY_FORCE,
        LQ_ID.TOTEM_POLE,
        LQ_ID.GILDED_TOTEM,
        LQ_ID.RUNE_AXE,
        LQ_ID.LOCKPICK,
        LQ_ID.UNPOWERED_ORB,
        LQ_ID.COSMIC_RUNE,
    ]:
            expect(KEEP_IDS).to_contain(id)
    test('the keep list holds every quest item the deposit would otherwise lose', _fn136)

    def _fn137():
        wanted = [item.name for item in legends.record.items]
        expect(wanted).to_contain('Rune axe')
        expect(wanted).to_contain('Lockpick')
        expect(wanted).to_contain('Unpowered orb')
        expect(wanted).to_contain('Cosmic rune')
        # Why: eligibility runs before a booth has ever been opened, so a `mustHave` would block the quest at startup.
        expect(all([item.kind == 'acquirable' for item in legends.record.items])).to_be(True)
    test('the record lists everything with no counter and no rock', _fn137)


describe('the module', _fn131)


# Why: every Viyeldi climb rolls `stat_random(agility, 110, 250)` and a miss drops the climber down the rock, so a descent lands anywhere from the next pocket to the cave floor, and the stands above are one-way behind it.
def _fn138():
    def at(x, z):
        found = legends_pocket(Record({'x': x, 'z': z, 'level': 0}))
        return found if found is not None else '—'

    def _fn139():
        expect(at(2385, 4730)).to_be('viyeldi_main')
        expect(at(2386, 4727)).to_be('descent_three')
        expect(at(2388, 4728)).to_be('descent_four')
    test('the cave floor is a different pocket from the ledge stands above it', _fn139)

    # Why: this is the tile a live run ground on, three tiles from the character and in a pocket the fall had already put behind it.
    def _fn140():
        expect(at(2385, 4730)).not_.to_be(at(2386, 4727))
    test('a guardian standing above the floor is not in the pocket the floor can walk to', _fn140)


describe('the Viyeldi descent after a fall', _fn138)
