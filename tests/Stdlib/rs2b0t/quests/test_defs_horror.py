"""Ported from rs2b0t's test/api/ai/quests/defs/horror.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestProgress, QuestSnapshot
from rs2004.quests.defs.horror import decide, horror
from rs2004.quests.defs.horror.areas import HD_ID, HD_STAGE
from rs2004.quests.defs.horror.fight import FORM_ELEMENT, IMMUNE_FORMS, MOTHER_IDS, spell_tier
from rs2004.quests.defs.horror.journal import HD_FLAG
from rs2004.quests.defs.horror.supplies import NAILS_NEEDED, PLANKS_NEEDED, kit, make_room, prayer_potions, rune_kit
from rs2004.quests.defs import QUEST_DEFS
from rs2004.quests.food import quest_food

# QuestFood is a live module-level object several quest defs read, so restore it
# or this file silently changes whichever test file bun runs next.
original_food = quest_food.name


def _fn1():
    quest_food.name = 'Lobster'


before_each(_fn1)


def _fn2():
    quest_food.name = original_food


after_each(_fn2)
CAUSEWAY = Record({'x': 2508, 'z': 3634, 'level': 0})
QUEST_LIGHTHOUSE = Record({'x': 2445, 'z': 4597, 'level': 0})
BASEMENT = Record({'x': 2519, 'z': 4619, 'level': 1})
CAVERN = Record({'x': 2518, 'z': 4634, 'level': 0})


def snap(options=None):
    """Fully kitted by default, so every case exercises the branch it names."""
    if options is None:
        options = Record({})
    stage = (options.stage if options.stage is not None else HD_STAGE.NOT_STARTED)
    flags = set((options.flags if options.flags is not None else []))
    kitted = [
        [HD_ID.COINS, 50000],
        [HD_ID.HAMMER, 1],
        [HD_ID.TINDERBOX, 1],
        [HD_ID.SWAMP_TAR, 1],
        [HD_ID.MOLTEN_GLASS, 1],
        [HD_ID.DAGGER, 1],
        [HD_ID.ARROW, 5],
        [HD_ID.AIR_RUNE, 300],
        [HD_ID.WATER_RUNE, 200],
        [HD_ID.EARTH_RUNE, 200],
        [HD_ID.FIRE_RUNE, 250],
        [HD_ID.DEATH_RUNE, 150],
        [HD_ID.CHAOS_RUNE, 150],
    ]
    return QuestSnapshot(**{
        'journal': (options.journal if options.journal is not None else (('not_started' if stage == HD_STAGE.NOT_STARTED else 'in_progress'))),
        'inv': {_k: _v for _k, _v in [['lobster', (options.food if options.food is not None else 15)]]},
        'inv_ids': {_k: _v for _k, _v in list(kitted) + list(((options.inv_ids if options.inv_ids is not None else [])))},
        'worn': set(),
        'worn_ids': set(),
        'no_progress': 0,
        'bank_coins': 2000000,
        'stage': stage,
        'progress': QuestProgress(stage, flags),
        'bank': {},
        'bank_ids': {_k: _v for _k, _v in (options.bank_ids if options.bank_ids is not None else [])},
        'bank_known': (options.bank_known if options.bank_known is not None else True),
        'tile': (options.tile if options.tile is not None else CAUSEWAY),
        'free_slots': 6,
    })


def step(options=None):
    if options is None:
        options = Record({})
    return decide(snap(options))


def talk_to(s):
    return ((s.stop.npc if s.kind == 'talk' else None))


def custom_name(s):
    return ((s.name if s.kind == 'custom' else None))


def _fn3():
    def _fn4():
        # 'unknown' is not 'not_started': the quest list is blank for a moment
        # after login, and restarting a finished quest is the worst outcome.
        expect(step(Record({'journal': 'unknown'})).kind).to_be('wait')
    test('waits while the journal is unknown', _fn4)

    def _fn5():
        expect(step(Record({'journal': 'complete', 'stage': HD_STAGE.COMPLETE})).kind).to_be('done')
    test('is done once the journal is green', _fn5)

    def _fn6():
        # Why: Larrissa is at the lighthouse and the bridge kit is in Varrock, so talking first buys a second crossing of the map.
        expect(step().kind).not_.to_be('talk')
    test('gathers the bridge kit before starting the quest', _fn6)

    def _fn7():
        # The ordinary account already owns this, every step of the kit reads
        # the bank first, so the common case is one walk to the lighthouse.
        stocked = step(Record({'inv_ids': [[HD_ID.HAMMER, 1], [HD_ID.NAILS, NAILS_NEEDED], [HD_ID.PLANK, PLANKS_NEEDED]]}))
        expect(talk_to(stocked)).to_be('Larrissa')
    test('talks to Larrissa the moment the kit is in hand', _fn7)

    def _fn8():
        s = step(Record({'stage': HD_STAGE.STARTED, 'food': 0}))
        expect(s.kind).to_be('withdraw')
    test('tops the pack up with food before anything else', _fn8)

    def _fn9():
        # Preparation stops at the door: a top-up mid-cavern walks the character
        # back out of a fight it cannot re-enter without redoing the wall.
        s = step(Record({'stage': HD_STAGE.DEFEATED_DAGJR, 'food': 0, 'tile': CAVERN}))
        expect(s.kind).to_be('custom')
    test('never banks from inside a sealed pocket', _fn9)


describe('Horror from the Deep decide()', _fn3)


def _fn10():
    started = Record({'stage': HD_STAGE.STARTED})

    def _fn11():
        _merged12 = {}
        for _k, _v in (started._fields if isinstance(started, Record) else started).items():
            _merged12[_k] = _v
        for _k, _v in {'inv_ids': [[HD_ID.HAMMER, 0]]}.items():
            _merged12[_k] = _v
        s = step(Record(_merged12))
        expect(s.kind).to_be('buy')
        expect(s.kind == 'buy' and s.item).to_be('Hammer')
    test('buys a hammer before anything is smithed', _fn11)

    def _fn13():
        # Strict order on purpose: the smithing leg banks the pack to make room
        # for ore, and a plank banked mid-leg is a plank fetched twice.
        s = step(started)
        expect(custom_name(s)).to_contain('nails')
    test('smiths the nails before fetching the planks', _fn13)

    def _fn14():
        _merged15 = {}
        for _k, _v in (started._fields if isinstance(started, Record) else started).items():
            _merged15[_k] = _v
        for _k, _v in {'inv_ids': [[HD_ID.NAILS, NAILS_NEEDED]]}.items():
            _merged15[_k] = _v
        s = step(Record(_merged15))
        expect(s.kind).to_be('grab_ground')
        expect(s.kind == 'grab_ground' and s.item).to_be('Plank')
    test('fetches planks once the nails are in', _fn14)

    def _fn16():
        _merged17 = {}
        for _k, _v in (started._fields if isinstance(started, Record) else started).items():
            _merged17[_k] = _v
        for _k, _v in {'inv_ids': [[HD_ID.NAILS, NAILS_NEEDED], [HD_ID.PLANK, PLANKS_NEEDED]]}.items():
            _merged17[_k] = _v
        s = step(Record(_merged17))
        expect(custom_name(s)).to_contain('bridge')
    test('repairs the bridge once both are in', _fn16)

    def _fn18():
        _merged19 = {}
        for _k, _v in (started._fields if isinstance(started, Record) else started).items():
            _merged19[_k] = _v
        for _k, _v in {'bank_ids': [[HD_ID.NAILS, 100]]}.items():
            _merged19[_k] = _v
        s = step(Record(_merged19))
        expect(s.kind).to_be('withdraw')
    test('prefers banked nails to the anvil', _fn18)

    def _fn20():
        # An unread bank is not an empty bank: bankIds is empty until a booth has
        # been opened, and "no nails banked" would send the bot to the mine.
        _merged21 = {}
        for _k, _v in (started._fields if isinstance(started, Record) else started).items():
            _merged21[_k] = _v
        for _k, _v in {'bank_known': False}.items():
            _merged21[_k] = _v
        s = step(Record(_merged21))
        expect(s.kind).to_be('scan_bank')
    test('scans the bank before deciding nothing is banked', _fn20)


describe('Horror from the Deep — the bridge', _fn10)


def _fn22():
    bridged = Record({'stage': HD_STAGE.STARTED, 'flags': [HD_FLAG.BRIDGE]})

    def _fn23():
        _merged24 = {}
        for _k, _v in (bridged._fields if isinstance(bridged, Record) else bridged).items():
            _merged24[_k] = _v
        for _k, _v in {'bank_ids': [[HD_ID.KEY, 1]]}.items():
            _merged24[_k] = _v
        expect(step(Record(_merged24))).to_match_object(Record({'kind': 'withdraw', 'items': [Record({'name': 'Lighthouse key', 'id': HD_ID.KEY, 'qty': 1})]}))
    test('withdraws the existing lighthouse key instead of requesting a duplicate', _fn23)

    def _fn25():
        _merged26 = {}
        for _k, _v in (bridged._fields if isinstance(bridged, Record) else bridged).items():
            _merged26[_k] = _v
        for _k, _v in {'bank_known': False}.items():
            _merged26[_k] = _v
        expect(step(Record(_merged26)).kind).to_be('scan_bank')
    test('a funded resume still scans an unread bank for the lighthouse key', _fn25)

    def _fn27():
        expect(custom_name(step(bridged))).to_contain('barcrawl')
    test('runs the barcrawl and Gunnjorn once the bridge is up', _fn27)

    def _fn28():
        _merged29 = {}
        for _k, _v in (bridged._fields if isinstance(bridged, Record) else bridged).items():
            _merged29[_k] = _v
        for _k, _v in {'inv_ids': [[HD_ID.COINS, 10]]}.items():
            _merged29[_k] = _v
        s = step(Record(_merged29))
        expect(s.kind).to_be('withdraw')
    test('draws coin for the tour before walking it', _fn28)

    def _fn30():
        # One causeway crossing instead of three: everything the lighthouse and
        # the cavern want is bought while the character is still mainland-side.
        _merged31 = {}
        for _k, _v in (bridged._fields if isinstance(bridged, Record) else bridged).items():
            _merged31[_k] = _v
        for _k, _v in {'inv_ids': [[HD_ID.KEY, 1], [HD_ID.DEATH_RUNE, 0]]}.items():
            _merged31[_k] = _v
        s = step(Record(_merged31))
        expect(s.kind).to_be('buy')
    test('completes the dungeon load before the last word with Larrissa', _fn30)

    def _fn32():
        _merged33 = {}
        for _k, _v in (bridged._fields if isinstance(bridged, Record) else bridged).items():
            _merged33[_k] = _v
        for _k, _v in {'inv_ids': [[HD_ID.KEY, 1]]}.items():
            _merged33[_k] = _v
        expect(talk_to(step(Record(_merged33)))).to_be('Larrissa')
    test('talks to Larrissa once key and load are both in', _fn32)


describe('Horror from the Deep — the key and the door', _fn22)


def _fn34():
    def _fn35():
        s = step(Record({'stage': HD_STAGE.ENTERED_LIGHTHOUSE, 'inv_ids': [[HD_ID.KEY, 1]]}))
        expect(custom_name(s)).to_contain('enter')
    test('walks in through the doorway when outside and loaded', _fn35)

    def _fn36():
        s = step(Record({'stage': HD_STAGE.ENTERED_LIGHTHOUSE, 'inv_ids': [[HD_ID.TINDERBOX, 0]]}))
        expect(s.kind).to_be('buy')
    test('re-buys a missing load rather than entering short', _fn36)

    def _fn37():
        s = step(Record({'stage': HD_STAGE.ENTERED_LIGHTHOUSE, 'tile': QUEST_LIGHTHOUSE}))
        expect(custom_name(s)).to_contain('light')
    test('repairs the light once inside', _fn37)

    def _fn38():
        # Past the repair the tinderbox, tar and glass are spent; asking again is
        # a trip to Lumbridge swamp and Catherby beach for nothing.
        s = step(Record({
        'stage': HD_STAGE.REPAIRED_LIGHTHOUSE,
        'inv_ids': [[HD_ID.TINDERBOX, 0], [HD_ID.SWAMP_TAR, 0], [HD_ID.MOLTEN_GLASS, 0]],
    }))
        expect(custom_name(s)).to_contain('enter')
    test('does not re-source the lamp kit after the lamp is lit', _fn38)

    def _fn39():
        s = step(Record({'stage': HD_STAGE.REPAIRED_LIGHTHOUSE, 'tile': BASEMENT}))
        expect(custom_name(s)).to_contain('wall')
    test('opens the strange wall from the basement', _fn39)

    def _fn40():
        s = step(Record({'stage': HD_STAGE.REPAIRED_LIGHTHOUSE, 'tile': CAVERN}))
        expect(custom_name(s)).to_contain('junior')
    test('fights the junior in the cavern', _fn40)

    def _fn41():
        s = step(Record({'stage': HD_STAGE.DEFEATED_DAGJR, 'tile': CAVERN}))
        expect(custom_name(s)).to_contain('mother')
    test('fights the mother once the junior is down', _fn41)

    def _fn42():
        s = step(Record({'stage': HD_STAGE.DEFEATED_DAGJR, 'tile': Record({'x': 3222, 'z': 3218, 'level': 0})}))
        expect(s.kind).to_be('custom')
    test('walks back to the lighthouse when a death drops it mainland-side', _fn42)


describe('Horror from the Deep — the lighthouse and the cavern', _fn34)


def _fn43():
    def _fn44():
        expect(any([d.record.id == 'horror' for d in QUEST_DEFS])).to_be(True)
    test('is registered in the queue', _fn44)

    def _fn45():
        # Without it the engine provisions record.items up front and never lets
        # decide() acquire anything at the stage that needs it.
        expect(horror.owns_inventory).to_be(True)
    test('owns its own inventory', _fn45)

    def _fn46():
        # A quest that buys anything and omits coins parks on "need gp" forever.
        expect(horror.tools).to_contain('coins')
    test('keeps coins in its tools', _fn46)


describe('Horror from the Deep module', _fn43)


def _fn47():
    def _fn48():
        # Why: `npc_max_dealt` zeroes any hit off the current form's weakness, so a form missing from both tables stalls the fight with no message.
        for id in MOTHER_IDS:
            expect(FORM_ELEMENT.get(id) is not None or (id in IMMUNE_FORMS)).to_be(True)
    test('every form the npc can take is either answerable or named immune', _fn48)

    def _fn49():
        expect(FORM_ELEMENT.get(1351)).to_be('Wind')
        expect(FORM_ELEMENT.get(1352)).to_be('Water')
        expect(FORM_ELEMENT.get(1353)).to_be('Fire')
        expect(FORM_ELEMENT.get(1354)).to_be('Earth')
    test('the four elemental forms map to their own element', _fn49)

    def _fn50():
        expect(spell_tier(99)).to_be('blast')
        expect(spell_tier(59)).to_be('blast')
        expect(spell_tier(58)).to_be('bolt')
        expect(spell_tier(35)).to_be('bolt')
        expect(spell_tier(13)).to_be('strike')
        # Below Fire Strike four of her six forms cannot be answered at all.
        expect(spell_tier(12)).to_be_null()
    test('the spell tier follows the magic level', _fn50)


describe('Dagannoth mother forms', _fn47)


def _fn51():
    banked_law = [[HD_ID.LAW_RUNE, 500]]

    def law_in(s):
        return s is not None and s.kind == 'withdraw' and any([i.get('id') == HD_ID.LAW_RUNE for i in s.items])

    def _fn52():
        # A* only injects a hop the *live inventory* can pay for, so the
        # difference between "can plan a Camelot hop" and "does" is this fetch.
        expect(law_in(rune_kit(snap(Record({'bank_ids': banked_law})), True))).to_be(True)
    test('draws law when nav teleports are on and the bank has them', _fn52)

    def _fn53():
        expect(law_in(rune_kit(snap(Record({'bank_ids': banked_law})), False))).to_be(False)
    test('does not ask for law when the toggle is off', _fn53)

    def _fn54():
        # Only the Magic Guild (66 magic) and the Mage Arena stock it, so an
        # empty bank is the ordinary case, and the answer is the walk.
        expect(law_in(rune_kit(snap(Record({'bank_ids': [[HD_ID.LAW_RUNE, 0]]})), True))).to_be(False)
    test('walks rather than detouring when the bank has no law', _fn54)

    def _fn55():
        s = rune_kit(snap(Record({'inv_ids': [[HD_ID.LAW_RUNE, 40]], 'bank_ids': banked_law})), True)
        expect(law_in(s)).to_be(False)
    test('leaves a part-spent stack alone', _fn55)

    def _fn56():
        expect((rune_kit(snap(Record({'bank_known': False})), True).kind if rune_kit(snap(Record({'bank_known': False})), True) is not None else None)).to_be('scan_bank')
    test('scans the bank before deciding law is not there', _fn56)

    def _fn57():
        # `smithNails` banks the pack for ore and law is not on its keep-list, so
        # a per-tick law top-up and the nails leg undo each other forever.
        expect(kit(snap(Record({'bank_ids': banked_law})), None)).to_be_null()
    test('never rides the coin trip — that loop parks the quest', _fn57)


describe('Horror from the Deep — teleport kit', _fn51)


def _fn58():
    # Why: the barcrawl is the leg the hops pay for, so a resume past the bridge still has to provision runes.
    bridged = Record({'stage': HD_STAGE.STARTED, 'flags': [HD_FLAG.BRIDGE], 'bank_ids': [[HD_ID.LAW_RUNE, 500]]})

    def _fn59():
        s = rune_kit(snap(bridged), True)
        expect(s is not None and s.kind == 'withdraw' and any([i.get('id') == HD_ID.LAW_RUNE for i in s.items])).to_be(True)
    test('provisions runes before the tour when the bridge is already repaired', _fn59)

    def _fn60():
        _merged61 = {}
        for _k, _v in (bridged._fields if isinstance(bridged, Record) else bridged).items():
            _merged61[_k] = _v
        for _k, _v in {'inv_ids': [
        [HD_ID.LAW_RUNE, 60],
        [HD_ID.AIR_RUNE, 350],
        [HD_ID.WATER_RUNE, 120],
        [HD_ID.EARTH_RUNE, 120],
        [HD_ID.FIRE_RUNE, 130],
        [HD_ID.DEATH_RUNE, 80],
        [HD_ID.CHAOS_RUNE, 80],
        [HD_ID.COINS, 20000],
    ]}.items():
            _merged61[_k] = _v
        stocked = snap(Record(_merged61))
        expect(rune_kit(stocked, True)).to_be_null()
    test('still reaches the barcrawl once the kit is aboard', _fn60)


describe('Horror from the Deep — teleport kit on a resumed run', _fn58)


def _fn62():
    # Why: the prep branch reads the bank before the shop, so an owned hammer is not bought twice.
    banked = [[HD_ID.HAMMER, 1], [HD_ID.NAILS, 50], [HD_ID.PLANK, 10]]

    def _fn63():
        s = step(Record({'inv_ids': [[HD_ID.HAMMER, 0]], 'bank_ids': banked}))
        expect(s.kind).to_be('withdraw')
        expect(s.kind == 'withdraw' and s.items[0].get('id')).to_be(HD_ID.HAMMER)
    test('withdraws the hammer instead of buying one', _fn63)

    def _fn64():
        s = step(Record({'inv_ids': [[HD_ID.HAMMER, 1]], 'bank_ids': banked}))
        expect(s.kind).to_be('withdraw')
        expect(s.kind == 'withdraw' and s.items[0].get('id')).to_be(HD_ID.NAILS)
    test('withdraws nails instead of mining and smithing them', _fn64)

    def _fn65():
        s = step(Record({'inv_ids': [[HD_ID.HAMMER, 1], [HD_ID.NAILS, NAILS_NEEDED], [HD_ID.PLANK, 1]], 'bank_ids': banked}))
        expect(s.kind == 'withdraw' and s.items[0].get('qty')).to_be(PLANKS_NEEDED - 1)
    test('takes only the planks it is short of', _fn65)


describe('Horror from the Deep — an account that already owns the kit', _fn62)


def _food_fits_the_pack():
    wanted = Record({'name': 'Lobster', 'held': 3, 'target': 8, 'low': 4})
    capped = kit(snap().with_fields({'free_slots': 2, 'inv_ids': {HD_ID.COINS: 50000}}), wanted)
    expect(capped.items[0]['qty']).to_be(2)
    carrying = snap().with_fields({'free_slots': 0, 'inv': {'iron ore': 5, 'air rune': 300, 'lobster': 3}})
    room = make_room(carrying, HD_STAGE.ENTERED_LIGHTHOUSE)
    expect(room.kind).to_be('deposit')
    expect('iron ore' in room.keep).to_be(False)
    expect('air rune' in room.keep).to_be(True)
    expect(decide(carrying.with_fields({'progress': QuestProgress(HD_STAGE.ENTERED_LIGHTHOUSE, set()), 'tile': CAUSEWAY})).kind).to_be('deposit')
    # The nails leg still wants its ore before the bridge is built.
    expect(make_room(carrying.with_fields({'inv': {'iron ore': 5, 'lobster': 3}}), HD_STAGE.STARTED)).to_be_null()
    nothing_spare = carrying.with_fields({'inv': {'air rune': 300, 'lobster': 3}})
    expect(make_room(nothing_spare, HD_STAGE.ENTERED_LIGHTHOUSE)).to_be_null()
    expect(make_room(carrying.with_fields({'free_slots': 1}), HD_STAGE.ENTERED_LIGHTHOUSE)).to_be_null()


test('a full pack banks its leftovers for food and never asks for more than fits', _food_fits_the_pack)


def _draws_prayer_doses():
    banked = snap().with_fields({'bank_ids': {2434: 10}, 'bank_known': True})
    step = prayer_potions(banked)
    expect(step.items[0]['id']).to_be(2434)
    expect(step.items[0]['qty']).to_be(3)
    held = banked.with_fields({'inv_ids': {2434: 3}})
    expect(prayer_potions(held)).to_be_null()
    expect(prayer_potions(snap().with_fields({'bank_ids': {}, 'bank_known': True}))).to_be_null()


test('the dungeon load carries prayer doses when the bank has them', _draws_prayer_doses)
