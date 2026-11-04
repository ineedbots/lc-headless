"""Quest provisioning validates bank state, material chains and skill advisories."""

from rs2004.catalogs.record import Record
from rs2004.execution import event_signal
from rs2004.game import skills
from rs2004.geometry import Tile
from rs2004.items import equipment
from rs2004.quests.defs.elementalworkshop import supplies as workshop
from rs2004.quests.defs.familycrest import supplies as crest
from rs2004.quests.defs.fishingcontest import supplies as fishing
from rs2004.quests.defs.horror import supplies as horror
from rs2004.quests.defs.legends import supplies as legends
from rs2004.quests.defs.observatory import supplies as observatory
from rs2004.quests.defs.treegnome import supplies as tree
from rs2004.quests.defs.upass import supplies as upass
from rs2004.quests.defs.watchtower import supplies as watchtower
from rs2004.quests.engine.types import QuestSnapshot
from rs2004.quests.food import quest_food
from rs2004.quests.gear import quest_loadout


def answer(value):
    def wait(*args, **kwargs):
        return value
        yield
    return wait


def give(scene, id, name='Material'):
    def effect(*args):
        scene.item(id, name)
        return True
    return effect


def readiness():
    scene = Scene()
    for fn in [workshop.warn_elemental_workshop_readiness, crest.warn_family_crest_readiness,
               horror.warn_horror_readiness, legends.warn_legends_readiness]:
        for stat in ['mining', 'smithing', 'crafting', 'magic', 'prayer', 'attack', 'strength',
                     'defence', 'hitpoints', 'agility', 'herblore', 'thieving', 'woodcutting']:
            scene.stats[stat] = 1
        expect(fn() is not None).to_be(True)
        for stat in list(scene.stats.keys()):
            scene.stats[stat] = 99
        expect(fn()).to_be_null()
        for stat in ['attack', 'strength', 'defence', 'hitpoints']:
            scene.stats[stat] = 1
        if fn == horror.warn_horror_readiness:
            scene.stats['magic'] = 14
            scene.stats['prayer'] = 1
        expect(fn() is not None).to_be(True)
    scene.stats['attack'] = 45
    scene.stats['strength'] = 45
    scene.stats['defence'] = 30
    scene.stats['hitpoints'] = 45
    expect(workshop.warn_elemental_workshop_readiness()).to_contain('below proven floor')


test('readiness distinguishes official requirements, failed combat profiles and proven floors', readiness)


def workshop_loadout():
    snap = QuestSnapshot(bank_known=True, inv_ids={}, bank_ids={}, inv={}, bank={}, worn=set(), worn_ids=set(), attack=99)
    expect(workshop.has_weapon(snap)).to_be(False)
    expect(workshop.has_slash_tool(snap)).to_be(False)
    snap.worn = set(['odd dagger'])
    expect(workshop.has_slash_tool(snap)).to_be(True)
    snap.worn = set()
    snap.inv = {'odd sword': 1}
    expect(workshop.has_held_slash_tool(snap)).to_be(True)
    snap.inv = {}
    for fn, reason in [[lambda: workshop.surface_loadout(snap, True, True), 'pickaxe'],
                       [lambda: workshop.surface_loadout(snap, False, False), 'Hammer']]:
        expect(fn().reason).to_contain(reason)
    snap.inv_ids[workshop.PICKAXES[0].id] = 1
    snap.inv_ids[workshop.EW_ITEM.HAMMER.id] = 1
    expect(workshop.surface_loadout(snap, True, True).reason).to_contain('Coal')
    snap.inv_ids[workshop.EW_ITEM.COAL.id] = 4
    expect(workshop.surface_loadout(snap, True, True).reason).to_contain('Thread')
    snap.inv_ids[workshop.EW_ITEM.THREAD.id] = 1
    expect(workshop.surface_loadout(snap, True, True).reason).to_contain('melee weapon')
    snap.inv = {'odd sword': 1}
    expect(workshop.surface_loadout(snap, True, True)).to_be_null()
    snap.inv_ids = {}
    snap.inv = {'rubbish': 1}
    snap.free_slots = 0
    expect(workshop.surface_loadout(snap, True, True).kind).to_be('deposit')
    snap.inv = {}
    snap.free_slots = 28
    snap.bank_ids = {workshop.EW_ITEM.KNIFE.id: 1, workshop.EW_ITEM.HAMMER.id: 1,
                     workshop.EW_ITEM.COAL.id: 4, workshop.EW_ITEM.THREAD.id: 1,
                     workshop.EW_ITEM.LEATHER.id: 1, workshop.EW_ITEM.NEEDLE.id: 1,
                     workshop.PICKAXES[0].id: 1}
    snap.bank = {'lobster': 8, 'rune scimitar': 1}
    snap.bank_ids[1333] = 1
    step = workshop.surface_loadout(snap, True, True)
    expect(step.kind).to_be('withdraw')
    expect(any([item['name'] == 'Lobster' for item in step.items])).to_be(True)
    expect(any([item['name'] == 'Rune scimitar' for item in step.items])).to_be(True)


test('workshop batches food and tools and waits with precise reasons when critical materials are absent', workshop_loadout)


def crest_bank():
    snap = QuestSnapshot(bank_known=False, inv_ids={}, bank_ids={}, inv={}, bank={}, worn=set(), worn_ids=set(), attack=99)
    expect(crest.has_weapon(snap)).to_be(False)
    expect(crest.wield_weapon(snap).kind).to_be('scan_bank')
    expect(crest.food_top_up(snap).kind).to_be('scan_bank')
    expect(crest.coin_top_up(snap).kind).to_be('scan_bank')
    expect(crest.teleport_kit_plan(snap).kind).to_be('scan_bank')
    snap.bank_known = True
    expect(crest.food_top_up(snap)).to_be_null()
    expect(crest.wield_weapon(snap)).to_be_null()
    snap.bank = {'lobster': 20, 'rune scimitar': 1}
    expect(crest.food_top_up(snap).items[0]['qty']).to_be(crest.FOOD_WITHDRAW)
    snap.bank_ids = {1333: 1}
    expect(crest.best_bank_weapon(snap) is not None).to_be(True)
    expect(crest.wield_weapon(snap).kind).to_be('withdraw')
    for want in crest.TELEPORT_KIT:
        snap.inv_ids[want.item.id] = want.qty
    snap.inv_ids[crest.DUEL_RING_IDS[0]] = 1
    expect(crest.teleport_kit_plan(snap)).to_be_null()
    expect(crest.buy(Record({'id': 1, 'name': 'Supply'}), 2, None, 10).qty).to_be(2)


test('Family Crest scans before withdrawing food, weapons and teleport supplies', crest_bank)


def exact_material_use():
    scene = Scene(Tile(3000, 3000, 0))
    for module in [horror, observatory]:
        expect(run_wait(module.use_on_loc_from(scene.at, 1, 'Furnace', lambda: True, scene.log))).to_be(True)
        scene.walk_ok = False
        expect(run_wait(module.use_on_loc_from(scene.at, 1, 'Furnace', lambda: False, scene.log))).to_be(False)
        scene.walk_ok = True
        expect(run_wait(module.use_on_loc_from(scene.at, 1, 'Furnace', lambda: False, scene.log))).to_be(False)
        scene.loc('Furnace')
        scene.item(1, 'Material', on_use=lambda target: False)
        expect(run_wait(module.use_on_loc_from(scene.at, 1, 'Furnace', lambda: False, scene.log))).to_be(False)
        scene.take(1)
        scene.item(1, 'Material', on_use=give(scene, 2))
        expect(run_wait(module.use_on_loc_from(scene.at, 1, 'Furnace', lambda: scene.has(2), scene.log))).to_be(True)
        scene.pack = []
        scene.locs = []
    for fn in [horror.cook_seaweed, horror.smelt_glass, horror.fill_sand,
               observatory.smelt_bronze_run, observatory.cook_seaweed, observatory.smelt_glass_run]:
        expect(run_wait(fn(scene.log))).to_be(False)
    expect(observatory.nearest_plank_spawn() is not None).to_be(True)


test('furnace and range recipes stand on the required side and verify the material produced', exact_material_use)


def horror_supplies():
    scene = Scene()
    snap = QuestSnapshot(bank_known=False, inv_ids={}, bank_ids={}, inv={}, bank={}, worn=set(), worn_ids=set())
    expect(horror.nails(snap).kind).to_be('scan_bank')
    snap.bank_known = True
    expect(horror.nails(snap).kind).to_be('custom')
    snap.bank_ids[horror.HD_ID.STEEL_BAR] = 4
    expect(horror.nails(snap).kind).to_be('withdraw')
    snap.bank_ids = {horror.PICKAXES[0].id: 1}
    snap.attack = 99
    expect(horror.nails(snap).kind).to_be('withdraw')
    snap.inv_ids[horror.HD_ID.NAILS] = 8
    expect(horror.nails(snap).kind).to_be('wait')
    spy_on(horror, 'melee_weapon_name', returns='Rune scimitar')
    stub(horror, melee_gave_up=False, wield_tries=0)
    snap.bank_known = False
    expect(horror.melee_weapon(snap).kind).to_be('scan_bank')
    snap.bank_known = True
    snap.bank = {'rune scimitar': 1}
    expect(horror.melee_weapon(snap).kind).to_be('withdraw')
    snap.inv = {'rune scimitar': 1}
    step = horror.melee_weapon(snap)
    equip = spy_on(equipment, 'equip', impl=answer(False))
    for i in range(3):
        expect(run_wait(step.run(scene.log))).to_be(False)
    expect(horror.melee_gave_up).to_be(True)
    expect(horror.melee_weapon(snap)).to_be_null()
    equip.mock_implementation(scene._equip)
    scene.item(1, 'Rune scimitar')
    expect(run_wait(horror.wield_melee('Rune scimitar', scene.log))).to_be(True)
    expect(run_wait(horror.wield_melee('Rune scimitar', scene.log))).to_be(True)
    expect(horror.melee_ready()).to_be(True)
    stub(horror, melee_gave_up=False)
    snap.inv = {}
    snap.bank = {}
    expect(horror.melee_weapon(snap)).to_be_null()
    expect(horror.melee_gave_up).to_be(True)
    stub(quest_food, name='Lobster')
    snap.inv = {'junk': 1}
    snap.free_slots = 0
    expect(horror.make_room(snap, 2).kind).to_be('deposit')
    snap.inv = {'lobster': 1}
    expect(horror.make_room(snap, 2)).to_be_null()


test('Horror sources steel before smithing and bounds weapon refusals before using magic alone', horror_supplies)


def tree_supplies():
    scene = Scene(tree.TG_TILE.TREES)
    stub(quest_food, name='Lobster')
    snap = QuestSnapshot(bank_known=False, inv_ids={}, bank_ids={}, inv={}, bank={}, worn=set(), worn_ids=set())
    expect(tree.top_up_food(snap).kind).to_be('scan_bank')
    snap.bank_known = True
    expect(tree.top_up_food(snap)).to_be_null()
    snap.bank = {'lobster': 30}
    expect(tree.top_up_food(snap).items[0]['qty']).to_be(tree.FOOD_TARGET)
    snap.inv = {'lobster': 10}
    expect(tree.top_up_food(snap)).to_be_null()
    stub(quest_food, name='')
    expect(tree.top_up_food(snap)).to_be_null()
    snap.bank_ids[tree.AXES[0].id] = 1
    expect(tree.source_axe(snap).kind).to_be('withdraw')
    scene.walk_ok = False
    expect(run_wait(tree.chop_logs(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(tree.chop_logs(scene.log))).to_be(False)
    scene.loc('Tree', ['Chop down'], effect=lambda op: False)
    expect(run_wait(tree.chop_logs(scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Tree', ['Chop down'], effect=give(scene, tree.TG_ITEM.LOGS.id, tree.TG_ITEM.LOGS.name))
    expect(run_wait(tree.chop_logs(scene.log))).to_be(True)
    from rs2004.items import inventory
    expect(inventory.count_by_id(tree.TG_ITEM.LOGS.id)).to_be(tree.LOGS_WANTED)
    stub(tree, unwearable=set())
    stub(quest_loadout, current=None)
    snap.bank = {'rune scimitar': 1}
    snap.inv = {'rune scimitar': 1}
    step = tree.arm_for_the_warlord(snap)
    expect(step.kind).to_be('custom')
    expect(run_wait(step.run(scene.log))).to_be(True)
    expect('rune scimitar' in tree.unwearable).to_be(True)
    expect(tree.arm_for_the_warlord(snap)).to_be_null()


test('Tree Gnome provisions food, waits out stumps and remembers unusable warlord gear', tree_supplies)


def worms():
    scene = Scene(fishing.FC_TILE.VINES)
    pending = spy_on(event_signal, 'pending', returns=True)
    expect(run_wait(fishing.dig_worms(2, scene.log))).to_be(False)
    pending.mock_return_value(False)
    scene.walk_ok = False
    expect(run_wait(fishing.dig_worms(2, scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(fishing.dig_worms(2, scene.log))).to_be(False)
    scene.loc('Vine', ['Check'], id=fishing.RED_VINE_LOCS[0], effect=lambda op: False)
    expect(run_wait(fishing.dig_worms(2, scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Vine', ['Check'], id=fishing.RED_VINE_LOCS[0])
    expect(run_wait(fishing.dig_worms(2, scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Vine', ['Check'], id=fishing.RED_VINE_LOCS[0], effect=give(scene, fishing.FC_ID.RED_VINE_WORM))
    expect(run_wait(fishing.dig_worms(2, scene.log))).to_be(True)
    expect(run_wait(fishing.dig_worms(2, scene.log))).to_be(True)
    snap = QuestSnapshot(bank_known=True, inv_ids={}, bank_ids={fishing.FC_ID.RED_VINE_WORM: 10})
    expect(fishing.source_worms(snap, 2).kind).to_be('withdraw')


test('red-worm gathering retries different vines and clears refused positions after a successful dig', worms)


def legends_materials():
    snap = QuestSnapshot(bank_known=False, inv_ids={}, bank_ids={}, inv={}, bank={}, worn=set(), worn_ids=set(), attack=99)
    item = Record({'id': 1, 'name': 'Material'})
    expect(legends.source(snap, item, 2, None, 20).kind).to_be('scan_bank')
    expect(legends.coin_top_up(snap).kind).to_be('scan_bank')
    expect(legends.food_top_up(snap).kind).to_be('scan_bank')
    expect(legends.potion_top_up(snap, 3).kind).to_be('scan_bank')
    expect(legends.source_gems(snap).kind).to_be('scan_bank')
    expect(legends.source_pickaxe(snap).kind).to_be('scan_bank')
    expect(legends.source_gold_bars(snap).kind).to_be('scan_bank')
    expect(legends.provision(snap).kind).to_be('scan_bank')
    snap.bank_known = True
    expect(legends.source(snap, item, 2, None, 20, stock=10).qty).to_be(10)
    expect(legends.source_pickaxe(snap).kind).to_be('buy')
    snap.bank_ids[legends.PICKAXES[0].id] = 1
    expect(legends.source_pickaxe(snap).kind).to_be('withdraw')
    expect(legends.source_gold_bars(snap).kind).to_be('withdraw')
    snap.inv_ids[legends.PICKAXES[0].id] = 1
    expect(legends.source_gold_bars(snap).kind).to_be('mine_rock')
    snap.inv = {'gold ore': 1}
    expect(legends.source_gold_bars(snap).kind).to_be('custom')
    snap.bank_ids[legends.LQ_ID.GOLD_BAR] = 2
    expect(legends.source_gold_bars(snap).kind).to_be('withdraw')
    gem = legends.GEM_ROCKS[0]
    snap.bank_ids[gem.id] = 1
    expect(legends.source_gems(snap).kind).to_be('withdraw')
    snap.bank_ids = {}
    rough = legends.GEM_CUTS[0]
    snap.bank_ids[rough.uncut] = 1
    expect(legends.source_gems(snap).kind).to_be('withdraw')
    snap.bank_ids = {}
    snap.inv_ids[rough.uncut] = 1
    expect(legends.source_gems(snap).kind).to_be('buy')
    snap.inv_ids[legends.LQ_ID.CHISEL] = 1
    expect(legends.source_gems(snap).kind).to_be('use_on')
    snap.inv = {'coins': 5000, 'shark': 14}
    expect(legends.food_top_up(snap)).to_be_null()
    snap.inv_ids[legends.PRAYER_POTIONS[0].id] = 3
    expect(legends.potion_top_up(snap, 3)).to_be_null()


test('Legends resumes the gold and seven-gem chains at bank, tool, ore and cutting stages', legends_materials)


def pass_and_tower_supplies():
    scene = Scene()
    snap = QuestSnapshot(bank_known=False, inv_ids={}, bank_ids={}, inv={}, bank={}, worn=set(), worn_ids=set())
    expect(upass.first_bow(None)).to_be_null()
    expect(upass.source_bow(snap).kind).to_be('scan_bank')
    expect(upass.from_bank(snap, upass.UP_ITEM.SPADE, 1).kind).to_be('scan_bank')
    snap.bank_known = True
    bow = list(upass.BOW_IDS)[0]
    snap.bank_ids[bow] = 1
    expect(upass.source_bow(snap).items[0]['id']).to_be(bow)
    stub(upass, unwearable=set(), refusals={})
    stub(quest_loadout, current=None)
    snap.inv = {'rune scimitar': 1}
    step = upass.wear_gear(snap)
    expect(step.kind).to_be('custom')
    for attempt in range(upass.REFUSALS_TO_WRITE_OFF):
        expect(run_wait(step.run(scene.log))).to_be(True)
    expect('rune scimitar' in upass.unwearable).to_be(True)
    upass.unwearable.clear()
    scene.item(1333, 'Rune scimitar')
    expect(run_wait(upass.wear_gear(snap).run(scene.log))).to_be(True)
    expect(run_wait(upass.draw_gear(snap).run(scene.log))).to_be(True)
    expect(upass.needs_equip(QuestSnapshot(inv_ids={upass.UP_ITEM.SPADE.id: 1}), upass.UP_ITEM.SPADE)).to_be(True)
    snap.inv = {}
    snap.bank_known = False
    expect(watchtower.bank_only(snap, watchtower.WT_ITEM.PESTLE).kind).to_be('scan_bank')
    expect(watchtower.source_coins(snap, 100).kind).to_be('scan_bank')
    expect(watchtower.source_food(snap, 10).kind).to_be('scan_bank')
    snap.bank_known = True
    expect(watchtower.source_coins(snap, 100).kind).to_be('wait')
    expect(watchtower.source_vial(snap).kind).to_be('buy')
    expect(watchtower.source_pestle(snap).kind).to_be('buy')
    expect(watchtower.source_light_source(snap).kind).to_be('grab_ground')
    snap.bank_ids[watchtower.WT_ITEM.LIT_CANDLE.id] = 1
    expect(watchtower.source_light_source(snap).kind).to_be('withdraw')
    snap.bank_ids[watchtower.WT_ITEM.PESTLE.id] = 1
    expect(watchtower.source_pestle(snap).kind).to_be('withdraw')
    expect(watchtower.bank_only(snap, watchtower.WT_ITEM.PESTLE).kind).to_be('withdraw')
    snap.inv_ids[watchtower.WT_ITEM.PESTLE.id] = 1
    snap.inv_ids[watchtower.WT_ITEM.COINS.id] = 100
    expect(watchtower.bank_only(snap, watchtower.WT_ITEM.PESTLE)).to_be_null()
    expect(watchtower.source_coins(snap, 100)).to_be_null()


test('Pass equipment refusals and Watchtower drop-only supplies use bounded recovery and bank-first sourcing', pass_and_tower_supplies)


def glass_chain():
    scene = Scene()
    snap = QuestSnapshot(bank_known=True, inv_ids={horror.HD_ID.SODA_ASH: 1}, bank_ids={})
    expect(horror.molten_glass(snap).kind).to_be('buy')
    snap.inv_ids[horror.HD_ID.BUCKET] = 1
    step = horror.molten_glass(snap)
    expect(step.kind).to_be('custom')
    expect(run_wait(step.run(scene.log))).to_be(False)
    snap.inv_ids = {horror.HD_ID.SEAWEED: 1}
    expect(horror.molten_glass(snap).kind).to_be('custom')
    snap.inv_ids = {horror.HD_ID.SODA_ASH: 1, horror.HD_ID.BUCKET_OF_SAND: 1}
    expect(horror.molten_glass(snap).kind).to_be('custom')
    snap.inv_ids[horror.HD_ID.MOLTEN_GLASS] = 1
    expect(horror.molten_glass(snap).kind).to_be('wait')
    spy_on(horror, 'rune_kit', returns=None)
    spy_on(horror, 'melee_weapon', returns=None)
    spy_on(horror, 'prayer_potions', returns=None)
    snap.inv_ids = {horror.HD_ID.TINDERBOX: 1, horror.HD_ID.BUCKET: 1, horror.HD_ID.DAGGER: 1,
                    horror.HD_ID.ARROW: 1}
    expect(horror.dungeon_kit(snap, True).kind).to_be('grab_ground')
    snap.inv_ids[horror.HD_ID.SWAMP_TAR] = 1
    expect(horror.dungeon_kit(snap, True).kind).to_be('grab_ground')
    snap.inv_ids[horror.HD_ID.MOLTEN_GLASS] = 1
    expect(horror.dungeon_kit(snap, True)).to_be_null()


test('Horror glass and dungeon kits resume at the first material still missing', glass_chain)
