"""Ported from rs2b0t's test/api/ai/quests/defs/eadgar.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.loadout import Loadout
from rs2004.catalogs.record import Record
from rs2004.quests.defs.eadgar import decide, eadgar
from rs2004.quests.defs.eadgar.areas import ER_ITEM
from rs2004.quests.defs.eadgar.journal import EADGAR_FLAG, EADGAR_STAGE
from rs2004.quests.engine.types import QuestProgress, QuestSnapshot
from rs2004.quests.food import quest_food
from rs2004.quests.gear import quest_loadout
from rs2004.tabs import quests

FALADOR = Record({'x': 2946, 'z': 3369, 'level': 0})
ARDOUGNE = Record({'x': 2616, 'z': 3332, 'level': 0})
CAVE = Record({'x': 2890, 'z': 10086, 'level': 2})
STRONGHOLD = Record({'x': 2844, 'z': 10057, 'level': 1})
WEAPON = 'Rune scimitar'


def stacks(list_, food):
    names = {}
    ids = {}
    for item, qty in list_:
        _v1 = names.get(item.name.lower())
        names[item.name.lower()] = ((_v1 if _v1 is not None else 0)) + qty
        _v2 = ids.get(item.id)
        ids[item.id] = ((_v2 if _v2 is not None else 0)) + qty
    if food > 0:
        names['lobster'] = food
    # Why: a Record can't hold the id-keyed map.
    return {'names': names, 'ids': ids}


def snap(options=None):
    if options is None:
        options = Record({})
    stage = (options.stage if options.stage is not None else EADGAR_STAGE.STARTED)
    pack = stacks((options.inv if options.inv is not None else []), (options.food if options.food is not None else 0))
    vault = stacks((options.bank if options.bank is not None else []), (options.bank_food if options.bank_food is not None else 0))
    flags = set((options.flags if options.flags is not None else [EADGAR_FLAG.EADGAR_FREED]))
    _v3 = vault['ids'].get(ER_ITEM.COINS.id)
    return QuestSnapshot(**{
        'journal': (options.journal if options.journal is not None else (('not_started' if stage == EADGAR_STAGE.NOT_STARTED else 'in_progress'))),
        'inv': pack['names'],
        'inv_ids': pack['ids'],
        'worn': set([item.name.lower() for item in ((options.worn if options.worn is not None else []))]),
        'worn_ids': set([item.id for item in ((options.worn if options.worn is not None else []))]),
        'no_progress': 0,
        'bank_coins': (_v3 if _v3 is not None else 0),
        'stage': stage,
        'progress': QuestProgress(stage, flags),
        'bank': vault['names'],
        'bank_ids': vault['ids'],
        'bank_known': (options.bank_known if options.bank_known is not None else True),
        'tile': (FALADOR if options.tile is None else options.tile),
        'free_slots': 28,
    })


def ready(options=None):
    """A pack `prepare()` is finished with: boots on, coin float drawn, food aboard."""
    if options is None:
        options = Record({})
    _merged4 = {}
    for _k, _v in {'food': 8, 'worn': [ER_ITEM.CLIMBING_BOOTS]}.items():
        _merged4[_k] = _v
    for _k, _v in (options._fields if isinstance(options, Record) else options).items():
        _merged4[_k] = _v
    for _k, _v in {'inv': [[ER_ITEM.COINS, 1000]] + list(((options.inv if options.inv is not None else [])))}.items():
        _merged4[_k] = _v
    return snap(Record(_merged4))


def custom_name(step):
    return ((step.name if step.kind == 'custom' else None))


# Why: the mountain-side talks are custom steps so the crossing can hold a protection prayer, and
# they keep the `talk to <npc>` label a plain `talk` step would have printed.
def talked_to(step):
    if step.kind == 'talk':
        return step.stop.npc
    return (step.name[len('talk to '):] if step.kind == 'custom' and step.name.startswith('talk to ') else None)


def _fn5():
    quest_food.name = 'Lobster'
    quest_loadout.current = Loadout('quest', {'righthand': WEAPON}, [])


before_each(_fn5)


def _fn6():
    def _fn7():
        expect(eadgar.record.id).to_be('eadgar')
        expect(eadgar.record.name).to_be("Eadgar's Ruse")
        expect(eadgar.owns_inventory).to_be(True)
        expect(eadgar.read_progress).to_be_defined()
    test('is registered against the quest record and owns its own inventory', _fn7)

    def _fn8():
        for item in [ER_ITEM.get(key) for key in ER_ITEM.keys()]:
            expect(eadgar.tools).to_contain(item.name.lower())
    test('keeps every quest item through a deposit', _fn8)


describe("Eadgar's Ruse module wiring", _fn6)


def _fn9():
    def _fn10():
        expect(decide(snap(Record({'journal': 'complete', 'stage': EADGAR_STAGE.COMPLETE}))).kind).to_be('done')
    test('a complete journal is done', _fn10)

    def _fn11():
        expect(decide(snap(Record({'journal': 'unknown'})))).to_equal(Record({'kind': 'wait', 'reason': 'quest journal not loaded'}))
    test('an unread journal waits rather than guessing a stage', _fn11)

    def _fn12():
        base = snap()
        step = decide((base).with_fields({'stage': None, 'progress': None}))
        expect(step.kind == 'wait' and step.reason).to_contain('journal stage unavailable')
    test('a stage the parser could not read waits', _fn12)

    # Why: Troll Stronghold finishes on Godric alone, and the Cave Entrance then drops the character
    # into an empty room, so the cell is opened before any leg that needs Eadgar.
    def _fn14():
        step = decide(ready(Record({'stage': EADGAR_STAGE.NEEDS_PARROT, 'flags': []})))
        expect(custom_name(step)).to_be('free Mad Eadgar from the troll prison')
    test('an unfreed Mad Eadgar is freed before anything else', _fn14)


describe("Eadgar's Ruse decide — guards", _fn9)


def _fn15():
    def _fn16():
        expect(decide(snap(Record({'bank_known': False}))).kind).to_be('scan_bank')
    test('reads the bank before deciding anything about supplies', _fn16)

    # Why: surface-bank distance is meaningless from the cave's z offset near 10,000.
    def _fn17():
        def bank_of(tile):
            step = decide(snap(Record({'bank_known': False, 'tile': tile})))
            if step.kind != 'scan_bank':
                return step.kind
            return (f'{step.bank.x},{step.bank.z},{step.bank.level}' if step.bank else 'nearest')
        expect(bank_of(CAVE)).to_be('2946,3369,0')
        expect(bank_of(STRONGHOLD)).to_be('2946,3369,0')
        expect(bank_of(ARDOUGNE)).to_be('nearest')
    test('pins Falador West from above the stile and stays on nearest below it', _fn17)

    def _fn18():
        base = ready()
        base.inv['bones'] = 1
        expect(decide(base).kind).to_be('deposit')
    test('banks anything that is not part of the loadout', _fn18)

    def _fn19():
        step = decide(snap(Record({'food': 8, 'worn': [ER_ITEM.CLIMBING_BOOTS], 'bank': [[ER_ITEM.COINS, 5000]]})))
        expect(step.kind == 'withdraw' and (step.items[0]['name'] if step.items[0] is not None else None)).to_be(ER_ITEM.COINS.name)
    test('draws the coin float from the bank before walking anywhere', _fn19)

    def _fn20():
        step = decide(snap(Record({'food': 8, 'inv': [[ER_ITEM.COINS, 1000]], 'bank': [[ER_ITEM.CLIMBING_BOOTS, 1]]})))
        expect(step.kind == 'withdraw' and (step.items[0]['name'] if step.items[0] is not None else None)).to_be(ER_ITEM.CLIMBING_BOOTS.name)
    test('withdraws banked climbing boots rather than buying a second pair', _fn20)

    def _fn21():
        step = decide(snap(Record({'food': 8, 'inv': [[ER_ITEM.COINS, 1000]]})))
        expect(custom_name(step)).to_contain('Climbing boots from Tenzing')
    test('buys the boots from Tenzing when the bank has none', _fn21)

    def _fn22():
        step = decide(snap(Record({'food': 8, 'inv': [[ER_ITEM.COINS, 1000], [ER_ITEM.CLIMBING_BOOTS, 1]]})))
        expect(custom_name(step)).to_be(f'wear {ER_ITEM.CLIMBING_BOOTS.name}')
    test('wears the boots it is carrying', _fn22)

    # Why: past the stile a bank trip means climbing back down the secret way, so only a spent pack
    # or missing boots is worth the walk.
    def _fn23():
        step = decide(ready(Record({'stage': EADGAR_STAGE.NEEDS_PARROT_BACK, 'tile': STRONGHOLD, 'food': 3})))
        expect(custom_name(step)).to_be('fetch the parrot back from under the rack')
    test('does not walk back down the mountain for a top-up', _fn23)


describe("Eadgar's Ruse decide — loadout", _fn15)


def _fn24():
    # Why: Sanfew's offer is gated on Troll Stronghold, and the journal reads notStarted either way,
    # so a queue that runs this quest early would otherwise walk to Taverley on every tick.
    def _fn25():
        status = spy_on(quests, 'status', returns='in_progress')
        blocked = decide(ready(Record({'stage': EADGAR_STAGE.NOT_STARTED, 'journal': 'in_progress'})))
        expect(blocked.kind == 'wait' and blocked.reason).to_contain('Troll Stronghold must be complete')
        status.mock_return_value('complete')
        step = decide(ready(Record({'stage': EADGAR_STAGE.NOT_STARTED, 'journal': 'in_progress'})))
        expect(talked_to(step)).to_be('Sanfew')
    test('stage 0 waits on Troll Stronghold, and asks Sanfew once it is complete', _fn25)

    def _fn26():
        expect(talked_to(decide(ready(Record({'stage': EADGAR_STAGE.STARTED}))))).to_be('Eadgar')
        expect(talked_to(decide(ready(Record({'stage': EADGAR_STAGE.SPOKE_EADGAR}))))).to_be('Burntmeat')
        expect(talked_to(decide(ready(Record({'stage': EADGAR_STAGE.SPOKE_BURNTMEAT}))))).to_be('Eadgar')
        expect(talked_to(decide(ready(Record({'stage': EADGAR_STAGE.SPOKE_BURNTMEAT_FIRST}))))).to_be('Eadgar')
    test('stage 10 walks to Eadgar and stage 15 to Burntmeat', _fn26)

    # Why: the axe is sold one ladder above the fruit and the vodka, and the parrot leg ends four
    # hundred tiles away in Ardougne, so the axe is bought first, on the trip that is happening anyway.
    def _fn27():
        empty = decide(ready(Record({'stage': EADGAR_STAGE.NEEDS_PARROT, 'tile': ARDOUGNE})))
        expect(empty.kind == 'buy' and empty.item).to_be(ER_ITEM.AXE.name)

        def kit(*inv):
            return decide(ready(Record({'stage': EADGAR_STAGE.NEEDS_PARROT, 'tile': ARDOUGNE, 'inv': [[ER_ITEM.AXE, 1]] + list(inv)})))
        no_fruit = kit()
        expect(no_fruit.kind == 'buy' and no_fruit.item).to_be(ER_ITEM.KNIFE.name)
        with_knife = kit([ER_ITEM.KNIFE, 1])
        expect(with_knife.kind == 'buy' and with_knife.item).to_be(ER_ITEM.PINEAPPLE.name)
        expect(custom_name(kit([ER_ITEM.KNIFE, 1], [ER_ITEM.PINEAPPLE, 1]))).to_be('dice the pineapple')
        with_chunks = kit([ER_ITEM.PINEAPPLE_CHUNKS, 1])
        expect(with_chunks.kind == 'buy' and with_chunks.item).to_be(ER_ITEM.VODKA.name)
        expect(custom_name(kit([ER_ITEM.PINEAPPLE_CHUNKS, 1], [ER_ITEM.VODKA, 1]))).to_contain('catch a parrot')
        expect(talked_to(kit([ER_ITEM.DRUNK_PARROT, 1]))).to_be('Eadgar')
    test('stage 30 buys the axe, then the fruit, then the liquor, then catches the parrot', _fn27)

    # Why: the aviary refuses a second parrot while one is in the bank, so the banked one is the
    # only one this account will ever get.
    def _fn28():
        step = decide(ready(Record({'stage': EADGAR_STAGE.NEEDS_PARROT, 'inv': [[ER_ITEM.AXE, 1]], 'bank': [[ER_ITEM.DRUNK_PARROT, 1]]})))
        expect(step.kind == 'withdraw' and (step.items[0]['id'] if step.items[0] is not None else None)).to_be(ER_ITEM.DRUNK_PARROT.id)
    test('a banked parrot is withdrawn rather than caught again', _fn28)

    def _fn29():
        with_parrot = decide(ready(Record({'stage': EADGAR_STAGE.EXPLAINED_PLAN, 'inv': [[ER_ITEM.DRUNK_PARROT, 1]]})))
        expect(custom_name(with_parrot)).to_be('hide the parrot under the prison rack')
        lost = decide(ready(Record({'stage': EADGAR_STAGE.EXPLAINED_PLAN})))
        expect(talked_to(lost)).to_be('Eadgar')
    test('stage 50 hides the parrot, and re-asks Eadgar when it is nowhere', _fn29)

    def _fn30():
        empty = decide(ready(Record({'stage': EADGAR_STAGE.HID_PARROT, 'tile': ARDOUGNE})))
        expect(empty.kind == 'buy' and empty.item).to_be(ER_ITEM.AXE.name)
        with_axe = decide(ready(Record({'stage': EADGAR_STAGE.HID_PARROT, 'tile': ARDOUGNE, 'inv': [[ER_ITEM.AXE, 1]]})))
        expect(custom_name(with_axe)).to_be('chop 1 logs')
        with_logs = decide(ready(Record({'stage': EADGAR_STAGE.HID_PARROT, 'tile': ARDOUGNE, 'inv': [[ER_ITEM.LOGS, 1]]})))
        expect(custom_name(with_logs)).to_contain('kill chickens')
        with_chickens = decide(ready(Record({'stage': EADGAR_STAGE.HID_PARROT, 'tile': ARDOUGNE, 'inv': [[ER_ITEM.LOGS, 1], [ER_ITEM.RAW_CHICKEN, 5]]})))
        expect(with_chickens.kind == 'pick_loc' and with_chickens.loc).to_be('Wheat')
        stocked = decide(ready(Record({
        'stage': EADGAR_STAGE.HID_PARROT,
        'inv': [[ER_ITEM.LOGS, 1], [ER_ITEM.RAW_CHICKEN, 5], [ER_ITEM.GRAIN, 10]],
    })))
        expect(talked_to(stocked)).to_be('Eadgar')
    test('stage 60 gathers the whole scarecrow before it walks up the mountain', _fn30)

    def _fn31():
        step = decide(ready(Record({
        'stage': EADGAR_STAGE.HID_PARROT,
        'inv': [[ER_ITEM.LOGS, 1], [ER_ITEM.RAW_CHICKEN, 5]],
        'bank': [[ER_ITEM.GRAIN, 10]],
    })))
        expect(step.kind == 'withdraw' and (step.items[0]['name'] if step.items[0] is not None else None)).to_be(ER_ITEM.GRAIN.name)
    test('stage 60 prefers a banked sheaf over a walk to the wheat field', _fn31)

    # Why: Tegid only parts with a robe while the quest sits at stage 70, so the journal's needs
    # list is what says whether the trip is still owed.
    def _fn32():
        robe_only = decide(ready(Record({'stage': EADGAR_STAGE.NEEDS_ITEMS, 'flags': [EADGAR_FLAG.EADGAR_FREED, EADGAR_FLAG.NEED_CLOTHES]})))
        expect(talked_to(robe_only)).to_be('Tegid')
        grain_only = decide(ready(Record({
        'stage': EADGAR_STAGE.NEEDS_ITEMS,
        'flags': [EADGAR_FLAG.EADGAR_FREED, f'{EADGAR_FLAG.NEED_GRAIN}:3'],
        'tile': ARDOUGNE,
    })))
        expect(grain_only.kind == 'pick_loc' and grain_only.loc).to_be('Wheat')
        nothing_left = decide(ready(Record({'stage': EADGAR_STAGE.NEEDS_ITEMS})))
        expect(talked_to(nothing_left)).to_be('Eadgar')
    test('stage 70 fetches only what the journal still lists', _fn32)

    def _fn33():
        step = decide(ready(Record({
        'stage': EADGAR_STAGE.NEEDS_ITEMS,
        'flags': [EADGAR_FLAG.EADGAR_FREED, EADGAR_FLAG.NEED_CLOTHES],
        'bank': [[ER_ITEM.DIRTY_ROBE, 1]],
    })))
        expect(step.kind == 'withdraw' and (step.items[0]['id'] if step.items[0] is not None else None)).to_be(ER_ITEM.DIRTY_ROBE.id)
    test('stage 70 withdraws a banked robe rather than asking Tegid twice', _fn33)

    # Why: the thistle only grows on Trollheim and everything that processes it is bought at the
    # bottom, so an empty pack shops before it climbs.
    def _fn34():
        fresh = decide(ready(Record({'stage': EADGAR_STAGE.NEEDS_POTION, 'tile': CAVE})))
        expect(fresh.kind == 'buy' and fresh.item).to_be(ER_ITEM.TINDERBOX.name)
        kitted = decide(ready(Record({
        'stage': EADGAR_STAGE.NEEDS_POTION,
        'tile': CAVE,
        'inv': [[ER_ITEM.TINDERBOX, 1], [ER_ITEM.LOGS, 1], [ER_ITEM.PESTLE, 1], [ER_ITEM.RANARR_VIAL, 1]],
    })))
        expect(custom_name(kitted)).to_be('pick a Troll Thistle')
    test('stage 80 buys the whole kit before it picks anything', _fn34)

    def _fn35():
        picked = decide(ready(Record({
        'stage': EADGAR_STAGE.NEEDS_POTION,
        'tile': CAVE,
        'inv': [[ER_ITEM.THISTLE, 1], [ER_ITEM.TINDERBOX, 1], [ER_ITEM.LOGS, 1]],
    })))
        expect(custom_name(picked)).to_be('dry the thistle over a fire')
        dried = decide(ready(Record({
        'stage': EADGAR_STAGE.NEEDS_POTION,
        'tile': CAVE,
        'inv': [[ER_ITEM.DRIED_THISTLE, 1], [ER_ITEM.PESTLE, 1]],
    })))
        expect(custom_name(dried)).to_be('grind the dried thistle')
        ground = decide(ready(Record({
        'stage': EADGAR_STAGE.NEEDS_POTION,
        'tile': CAVE,
        'inv': [[ER_ITEM.GROUND_THISTLE, 1], [ER_ITEM.RANARR_VIAL, 1]],
    })))
        expect(custom_name(ground)).to_be('mix the troll truth potion')
        brewed = decide(ready(Record({'stage': EADGAR_STAGE.NEEDS_POTION, 'inv': [[ER_ITEM.TROLL_POTION, 1]]})))
        expect(talked_to(brewed)).to_be('Eadgar')
    test('stage 80 walks the thistle chain in order', _fn35)

    def _fn36():
        needs_herb = decide(ready(Record({'stage': EADGAR_STAGE.NEEDS_POTION, 'inv': [[ER_ITEM.GROUND_THISTLE, 1]], 'bank': [[ER_ITEM.RANARR, 1]]})))
        expect(needs_herb.kind == 'withdraw' and (needs_herb.items[0]['id'] if needs_herb.items[0] is not None else None)).to_be(ER_ITEM.RANARR.id)
        needs_vial = decide(ready(Record({'stage': EADGAR_STAGE.NEEDS_POTION, 'inv': [[ER_ITEM.GROUND_THISTLE, 1], [ER_ITEM.RANARR, 1]]})))
        expect(needs_vial.kind == 'buy' and needs_vial.item).to_be(ER_ITEM.VIAL_WATER.name)
        can_mix = decide(ready(Record({
        'stage': EADGAR_STAGE.NEEDS_POTION,
        'inv': [[ER_ITEM.GROUND_THISTLE, 1], [ER_ITEM.RANARR, 1], [ER_ITEM.VIAL_WATER, 1]],
    })))
        expect(custom_name(can_mix)).to_be('mix a ranarr potion (unf)')
    test('stage 80 mixes the unfinished potion from a banked ranarr weed', _fn36)

    # Why: no 2004 shop sells a ranarr weed or a ranarr potion (unf), so an empty bank is a park
    # with a reason rather than a walk that will never find one.
    def _fn37():
        step = decide(ready(Record({'stage': EADGAR_STAGE.NEEDS_POTION, 'inv': [[ER_ITEM.GROUND_THISTLE, 1]]})))
        expect(step.kind == 'wait' and step.reason).to_contain('no Ranarr weed')
    test('stage 80 parks honestly when there is no ranarr weed anywhere', _fn37)

    def _fn38():
        expect(custom_name(decide(ready(Record({'stage': EADGAR_STAGE.NEEDS_PARROT_BACK}))))).to_be('fetch the parrot back from under the rack')
        expect(talked_to(decide(ready(Record({'stage': EADGAR_STAGE.GOT_PARROT_BACK}))))).to_be('Eadgar')
        expect(talked_to(decide(ready(Record({'stage': EADGAR_STAGE.GOT_FAKE_MAN, 'inv': [[ER_ITEM.FAKE_MAN, 1]]}))))).to_be('Burntmeat')
    test('stages 85 to 87 run the parrot back through Eadgar to Burntmeat', _fn38)

    def _fn39():
        no_key = decide(ready(Record({'stage': EADGAR_STAGE.GOT_BURNT_MEAT, 'tile': STRONGHOLD})))
        expect(custom_name(no_key)).to_contain('kitchen drawers')
        with_key = decide(ready(Record({'stage': EADGAR_STAGE.GOT_BURNT_MEAT, 'tile': STRONGHOLD, 'inv': [[ER_ITEM.STOREROOM_KEY, 1]]})))
        expect(custom_name(with_key)).to_be('unlock the troll storeroom')
    test('stage 90 searches the drawers, then unlocks the door with what it found', _fn39)

    def _fn40():
        empty = decide(ready(Record({'stage': EADGAR_STAGE.UNLOCKED_STOREROOM, 'tile': STRONGHOLD})))
        expect(custom_name(empty)).to_contain('goutweed')
        carrying = decide(ready(Record({'stage': EADGAR_STAGE.UNLOCKED_STOREROOM, 'tile': STRONGHOLD, 'inv': [[ER_ITEM.GOUTWEED, 1]]})))
        expect(talked_to(carrying)).to_be('Sanfew')
    test('stage 100 takes the goutweed, then carries it to Sanfew', _fn40)

    # Why: decide() is pure, so a bot killed mid-quest re-derives its leg from the same snapshot.
    def _fn41():
        mid_scarecrow = ready(Record({
        'stage': EADGAR_STAGE.NEEDS_ITEMS,
        'flags': [EADGAR_FLAG.EADGAR_FREED, f'{EADGAR_FLAG.NEED_CHICKENS}:2'],
        'tile': ARDOUGNE,
        'inv': [[ER_ITEM.RAW_CHICKEN, 2], [ER_ITEM.GRAIN, 10]],
    }))
        expect(talked_to(decide(mid_scarecrow))).to_be('Eadgar')
    test('resumes from a half-full pack without repeating a finished leg', _fn41)


describe("Eadgar's Ruse decide — the quest legs", _fn24)
