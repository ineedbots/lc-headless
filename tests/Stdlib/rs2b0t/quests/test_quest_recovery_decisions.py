"""Quest decisions preserve partially completed recipes and recover sealed pockets."""

import rs2004.quests.defs.elementalworkshop as workshop
import rs2004.quests.defs.horror as horror
import rs2004.quests.defs.watchtower as tower
from rs2004.quests.defs.horror.barcrawl import barcrawl_funds
from rs2004.quests.engine.types import QuestProgress, QuestSnapshot


def answer(value):
    def wait(*args, **kwargs):
        return value
        yield
    return wait


def horror_key():
    scene = Scene()
    crawl = spy_on(horror, 'ensure_barcrawl', impl=answer(False))
    expect(run_wait(horror.fetch_key(scene.log))).to_be(False)
    crawl.mock_implementation(answer(True))
    scene.walk_ok = False
    expect(run_wait(horror.fetch_key(scene.log))).to_be(False)
    scene.walk_ok = True
    talk = spy_on(horror, 'talk_through', impl=answer(False))
    expect(run_wait(horror.fetch_key(scene.log))).to_be(False)
    talk.mock_implementation(answer(True))
    expect(run_wait(horror.fetch_key(scene.log))).to_be(False)
    scene.item(horror.HD_ID.KEY, 'Key')
    expect(run_wait(horror.fetch_key(scene.log))).to_be(True)
    climb = spy_on(horror, 'climb_to_light', impl=answer(False))
    spy_on(horror, 'repair_light', impl=answer(True))
    expect(run_wait(horror._climb_and_repair(set(), scene.log))).to_be(False)
    climb.mock_implementation(answer(True))
    expect(run_wait(horror._climb_and_repair(set(), scene.log))).to_be(True)
    snap = QuestSnapshot(bank_known=False, inv_ids={}, bank_ids={})
    expect(barcrawl_funds(snap).kind).to_be('scan_bank')
    snap.bank_known = True
    expect(barcrawl_funds(snap).kind).to_be('withdraw')
    snap.inv_ids[horror.HD_ID.COINS] = 100000
    expect(barcrawl_funds(snap)).to_be_null()
    spy_on(horror, 'teleport_runes', returns=None)
    snap.progress = QuestProgress(stage=1, flags=set([horror.HD_FLAG.BRIDGE]))
    snap.bank_ids[horror.HD_ID.BARCRAWL_CARD] = 1
    expect(horror.before_the_door(snap).items[0]['id']).to_be(horror.HD_ID.BARCRAWL_CARD)
    spy_on(horror, 'sealed_area', returns=False)
    spy_on(horror, 'dungeon_kit', returns=None)
    expect(horror.inside(snap, True, lambda: None).name).to_be('enter the lighthouse')
    spy_on(horror, 'sealed_area', returns=True)
    spy_on(horror, 'in_cavern', returns=False)
    spy_on(horror, 'in_basement', returns=False)
    spy_on(horror, 'in_quest_lighthouse', returns=False)
    expect(horror.reach_the_cavern(snap, None).name).to_be('enter the lighthouse')


test('Horror key fetch and light repair stop at every failed prerequisite', horror_key)


def tower_caves_and_potion():
    snap = QuestSnapshot(bank_known=True, inv_ids={}, bank_ids={}, progress=QuestProgress(stage=7, flags=set()))
    spy_on(tower, 'need_cave_kit', returns=None)
    cave = spy_on(tower, 'next_skavid_cave', returns=5)
    expect(tower.stage_caves(snap, 'yanille').run).to_be(tower.learn_from_scared_skavid)
    cave.mock_return_value(2)
    word = spy_on(tower, 'learn_word', impl=answer(True))
    scene = Scene()
    expect(run_wait(tower.stage_caves(snap, 'yanille').run(scene.log))).to_be(True)
    expect(word.calls[0][0]).to_be(2)
    cave.mock_return_value(6)
    expect(tower.stage_caves(snap, 'yanille').run).to_be(tower.answer_mad_skavid)
    snap.inv_ids[tower.WT_ITEM.GOLD_BAR.id] = 1
    expect(tower.stage_caves(snap, 'yanille').run).to_be(tower.answer_mad_skavid)
    expect(tower.stage_enclave_entry(snap, 'enclave').run).to_be(tower.leave_enclave)
    expect(tower.stage_enclave_entry(snap, 'yanille').run).to_be(tower.take_nightshade)
    snap.inv_ids[tower.WT_ITEM.NIGHTSHADE.id] = 1
    spy_on(tower, 'source_food', returns=None)
    expect(tower.stage_enclave_entry(snap, 'yanille').run).to_be(tower.enter_enclave)
    snap.inv_ids = {tower.WT_ITEM.OGRE_POTION.id: 1}
    expect(tower.stage_potion(snap, 'yanille').run).to_be(tower.infuse_potion)
    snap.inv_ids = {}
    expect(tower.stage_potion(snap, 'enclave').run).to_be(tower.leave_enclave)
    expect(tower.stage_potion(snap, 'yanille').kind).to_be('wait')
    snap.inv_ids[tower.WT_ITEM.GUAM_LEAF.id] = 1
    expect(tower.stage_potion(snap, 'yanille').kind).to_be('buy')
    snap.inv_ids[tower.WT_ITEM.VIAL_WATER.id] = 1
    expect(tower.stage_potion(snap, 'yanille').kind).to_be('buy')
    snap.inv_ids[tower.WT_ITEM.ROPE.id] = 1
    expect(tower.stage_potion(snap, 'yanille').run).to_be(tower.pick_jangerberries)
    snap.inv_ids[tower.WT_ITEM.JANGERBERRIES.id] = 1
    expect(tower.stage_potion(snap, 'yanille').kind).to_be('wait')
    snap.inv_ids[tower.WT_ITEM.BAT_BONES.id] = 1
    expect(tower.stage_potion(snap, 'yanille').kind).to_be('buy')
    snap.inv_ids[tower.WT_ITEM.PESTLE.id] = 1
    expect(tower.stage_potion(snap, 'yanille').run).to_be(tower.grind_bat_bones)
    snap.inv_ids[tower.WT_ITEM.GROUND_BAT_BONES.id] = 1
    expect(tower.stage_potion(snap, 'yanille').run).to_be(tower.brew_ogre_potion)


test('Watchtower cave lessons and potion decisions resume from the materials actually held', tower_caves_and_potion)


def tower_shamans():
    snap = QuestSnapshot(bank_known=True, inv_ids={}, bank_ids={}, progress=QuestProgress(stage=11, flags=set()))
    left = spy_on(tower, 'flag_value', returns=6)
    spy_on(tower, 'source_food', returns=None)
    spy_on(tower, 'need_cave_kit', returns=None)
    expect(tower.stage_shamans(snap, 'enclave').run).to_be(tower.leave_enclave)
    expect(tower.stage_shamans(snap, 'yanille').kind).to_be('wait')
    snap.inv_ids[tower.WT_ITEM.MAGIC_OGRE_POTION.id] = 1
    expect(tower.stage_shamans(snap, 'yanille').run).to_be(tower.take_nightshade)
    snap.inv_ids[tower.WT_ITEM.NIGHTSHADE.id] = 1
    pick = spy_on(tower, 'source_pickaxe', returns=None)
    expect(tower.stage_shamans(snap, 'yanille').run).to_be(tower.dissolve_shamans)
    left.mock_return_value(0)
    expect(tower.stage_shamans(snap, 'yanille').run).to_be(tower.mine_dalgroth)
    snap.inv_ids[tower.WT_ITEM.CRYSTAL4.id] = 1
    expect(tower.stage_shamans(snap, 'yanille').run).to_be(tower.search_shaman_robe)
    snap.inv_ids.pop(tower.WT_ITEM.NIGHTSHADE.id)
    expect(tower.stage_shamans(snap, 'yanille').run).to_be(tower.take_nightshade)
    snap.inv_ids.pop(tower.WT_ITEM.CRYSTAL4.id)
    expect(tower.stage_shamans(snap, 'yanille').run).to_be(tower.take_nightshade)
    from rs2004.catalogs.record import Record
    pick.mock_return_value(Record({'kind': 'buy'}))
    expect(tower.stage_shamans(snap, 'yanille').kind).to_be('buy')
    snap.inv_ids[tower.WT_ITEM.CRYSTAL4.id] = 1
    snap.inv_ids[tower.WT_ITEM.CRYSTAL3.id] = 1
    expect(tower.stage_shamans(snap, 'enclave').run).to_be(tower.leave_enclave)
    snap.inv_ids[tower.WT_ITEM.ROPE.id] = 1
    expect(tower.stage_shamans(snap, 'yanille').run).to_be(tower.talk_to_grew)
    for crystal in tower.CRYSTALS:
        snap.inv_ids[crystal.id] = 1
    expect(tower.stage_shamans(snap, 'yanille').run).to_be(tower.show_crystals_to_wizard)
    snap.inv_ids = {}
    snap.bank_known = False
    expect(tower.recover_crystals(snap, 'yanille').kind).to_be('scan_bank')
    snap.bank_known = True
    snap.bank_ids[tower.CRYSTALS[0].id] = 1
    expect(tower.recover_crystals(snap, 'yanille').kind).to_be('withdraw')


test('Watchtower shamans retain food for return visits and recover crystals before requesting duplicates', tower_shamans)


def workshop_recovery():
    snap = QuestSnapshot(journal='in_progress', stage=None, progress=None, bank_known=True,
                         inv_ids={}, bank_ids={}, inv={}, bank={}, worn=set(), worn_ids=set())
    expect(workshop.decide(snap).kind).to_be('wait')
    area = spy_on(workshop, 'ew_area', returns='workshop')
    snap.stage = workshop.EW_STAGE.COMPLETE
    expect(workshop.decide(snap).kind).to_be('done')
    snap.stage = workshop.EW_STAGE.ENTERED
    snap.inv_ids[workshop.EW_ITEM.ELEMENTAL_SHIELD.id] = 1
    expect(workshop.decide(snap).kind).to_be('wait')
    snap.inv_ids = {}
    snap.stage = workshop.EW_STAGE.NOT_STARTED
    expect(workshop.decide(snap).run).to_be(workshop.leave_workshop)
    snap.stage = workshop.EW_STAGE.READ_BOOK
    expect(workshop.decide(snap).run).to_be(workshop.search_bookcase)
    snap.inv_ids[workshop.EW_ITEM.BATTERED_BOOK.id] = 1
    expect(workshop.decide(snap).kind).to_be('grab_ground')
    snap.inv_ids[workshop.EW_ITEM.KNIFE.id] = 1
    expect(workshop.decide(snap).run).to_be(workshop.slash_book_for_key)
    snap.stage = workshop.EW_STAGE.ENTERED
    snap.inv_ids[workshop.EW_ITEM.ELEMENTAL_METAL.id] = 1
    snap.inv_ids = {workshop.EW_ITEM.ELEMENTAL_METAL.id: 1}
    expect(workshop.decide(snap).run).to_be(workshop.leave_workshop)
    snap.inv_ids[workshop.EW_ITEM.BATTERED_BOOK.id] = 1
    expect(workshop.decide(snap).run).to_be(workshop.leave_workshop)
    area.mock_return_value('surface')
    spy_on(workshop, 'surface_loadout', returns=None)
    expect(workshop.decide(snap).run).to_be(workshop.enter_workshop)
    snap.inv_ids = {}
    expect(workshop.decide(snap).kind).to_be('wait')
    snap.inv_ids[workshop.supplies.PICKAXES[0].id] = 1
    expect(workshop.decide(snap).run).to_be(workshop.enter_workshop)
    area.mock_return_value('workshop')
    from rs2004.quests.engine.types import QuestProgress
    snap.progress = QuestProgress(workshop.EW_STAGE.ENTERED, set([workshop.EW_FLAG.WATER]))
    snap.inv_ids[workshop.EW_ITEM.LEATHER.id] = 1
    snap.inv_ids[workshop.EW_ITEM.NEEDLE.id] = 1
    expect(workshop.decide(snap).run).to_be(workshop.leave_workshop)
    snap.progress.flags.add(workshop.EW_FLAG.BELLOWS)
    snap.progress.flags.add(workshop.EW_FLAG.FURNACE)
    expect(workshop.decide(snap).run).to_be(workshop.mine_elemental_ore)
    snap.inv_ids[workshop.EW_ITEM.ELEMENTAL_ORE.id] = 1
    expect(workshop.decide(snap).run).to_be(workshop.leave_workshop)
    snap.inv_ids[workshop.EW_ITEM.COAL.id] = workshop.COAL_NEED
    expect(workshop.decide(snap).run).to_be(workshop.smelt_elemental_bar)


test('workshop resumes missing books, keys, hammers and surface loadouts after interrupted visits', workshop_recovery)
