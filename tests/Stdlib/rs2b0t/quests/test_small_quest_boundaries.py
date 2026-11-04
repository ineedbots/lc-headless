"""Small quest boundaries: cached journals, prerequisite failures and restart decisions."""

import rs2004.quests.defs.biohazard as bio
import rs2004.quests.defs.fightarena as arena
import rs2004.quests.defs.holygrail as grail
import rs2004.quests.defs.lostcity as lostcity
import rs2004.quests.defs.waterfall as waterfall
import rs2004.quests.defs.familycrest as family
import rs2004.quests.defs.ikov as ikov
import rs2004.quests.defs.upass as upass
import rs2004.quests.defs.digsite as digsite
from rs2004.quests.defs.digsite import supplies as dig_supplies
from rs2004.quests.defs.elementalworkshop import supplies as workshop
from rs2004.quests.defs.regicide import isafdar, pockets, supplies as reg_supplies, bomb
from rs2004.dialogue import modals
from rs2004.catalogs.record import Record
from rs2004.quests.defs.familycrest import journal as crest
from rs2004.quests.defs.horror import journal as horror
from rs2004.quests.defs.murder import evidence, journal as murder, poison
from rs2004.quests.defs.shilo import scene as shilo
from rs2004.quests.defs.upass import spent
from rs2004.quests.defs.witchshouse import patrol
from rs2004.quests.engine.types import QuestSnapshot
from rs2004.quests.food import quest_food
from rs2004.geometry import Tile
from rs2004.tabs import quests


def answer(value):
    def wait(*args, **kwargs):
        return value
        yield
    return wait


def journal_edges():
    scene = Scene()
    status = spy_on(quests, 'status', returns='complete')
    for module, fn, stages in [[murder, murder.read_murder_progress, murder.MURDER_STAGE],
                               [horror, horror.read_horror_progress, horror.HD_STAGE]]:
        status.mock_return_value('complete')
        expect(run_wait(fn()).stage).to_be(stages.COMPLETE)
        status.mock_return_value('not_started')
        expect(run_wait(fn()).stage).to_be(stages.NOT_STARTED)
        status.mock_return_value('unknown')
        expect(run_wait(fn())).to_be_null()
    stub(crest.journal_read, stage=3, cached=True, failures=2, reads=4)
    expect(crest.describe_journal()).to_contain('CACHED')
    expect(crest.describe_journal()).to_contain('failures=2')
    stub(crest.journal_read, stage=None, cached=False, failures=0)
    expect(crest.describe_journal()).to_be('stage=?')
    expect(crest.read_stage('gave me his crest piece in return for a ruby ring')).to_be(crest.FC_STAGE.AVAN_PIECE)


test('journal readers short circuit status and describe cached failures without inventing a stage', journal_edges)


def murder_prerequisites():
    scene = Scene(evidence.MURDER_TILE.STUDY)
    scene.walk_ok = False
    expect(run_wait(evidence.take_dagger(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(evidence.take_dagger(scene.log))).to_be(False)
    scene.on_ground(evidence.MURDER_OBJ.DAGGER, 'Dagger', effect=lambda op: False)
    expect(run_wait(evidence.take_dagger(scene.log))).to_be(False)
    scene.item(evidence.MURDER_OBJ.DAGGER, 'Dagger')
    expect(run_wait(evidence.take_dagger(scene.log))).to_be(True)
    for name in ['take_dagger', 'flour_onto', 'lift_print']:
        stage = spy_on(evidence, name, impl=answer(False))
        expect(run_wait(evidence.take_prints([], scene.log))).to_be(False)
        stage.mock_implementation(answer(True))
    suspect = Fake(silver=1001, dust=1002, print=1003, barrel=None)
    for name in ['search_barrel', 'flour_onto', 'lift_print']:
        stage = spy_on(evidence, name, impl=answer(False))
        expect(run_wait(evidence.test_suspect(suspect, scene.log))).to_be(False)
        stage.mock_implementation(answer(True))
    target = Fake(near=scene.at, id=1004, name='Evidence')
    scene.walk_ok = False
    expect(run_wait(poison.investigate(target, scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(poison.investigate(target, scene.log))).to_be(False)
    scene.loc('Evidence', ['Investigate'], id=1004, effect=lambda op: False)
    expect(run_wait(poison.investigate(target, scene.log))).to_be(False)


test('murder evidence stops when dagger, dusting, print lifting or poison investigation cannot proceed', murder_prerequisites)


def small_decisions():
    scene = Scene()
    leave = spy_on(bio, 'leave_quarter', impl=answer(False))
    step = bio.outside('errand', answer(True))
    expect(run_wait(step.run(scene.log))).to_be(False)
    leave.mock_implementation(answer(True))
    expect(run_wait(step.run(scene.log))).to_be(True)
    scene.walk_ok = False
    expect(run_wait(arena._fn1(scene.log))).to_be(False)
    scene.walk_ok = True
    spy_on(arena, 'talk_strict', impl=answer(True))
    expect(run_wait(arena._fn1(scene.log))).to_be(True)
    expect(grail.decide(QuestSnapshot(journal='in_progress', stage=None), food='Lobster').kind).to_be('wait')
    expect(shilo.here()).to_be(shilo.shilo_area(scene.at))
    expect(spent.cell_of(16, 24, 1)).to_be('2,3,1')
    journey = spent.new_journey()
    expect(len(journey.visited)).to_be(0)
    expect(journey.sides).to_equal({})
    scene.at = Tile(2902, 3461, 0)
    expect(run_wait(patrol.walk_garden(patrol.FOUNTAIN_STAND, scene.log))).to_be(False)
    expect(scene.logged('outside the guarded garden corridor')).to_be(True)


test('small quest entry points preserve failure boundaries and fresh navigation memory', small_decisions)


def supply_boundaries():
    scene = Scene()
    snap = QuestSnapshot(bank_known=False, inv={}, inv_ids={}, bank={}, bank_ids={}, worn=set(), worn_ids=set(), free_slots=28)
    expect(lostcity.source_mainland_axe(snap).kind).to_be('scan_bank')
    snap.bank_known = True
    expect(lostcity.source_mainland_axe(snap).kind).to_be('wait')
    snap.bank = {'coins': 2000}
    expect(lostcity.source_mainland_axe(snap).kind).to_be('withdraw')
    snap.inv = {'coins': 100}
    expect(lostcity.source_mainland_axe(snap).kind).to_be('buy')
    expect(waterfall.scan_bank().kind).to_be('scan_bank')
    expect(waterfall.withdraw_exact(Record({'id': 1, 'name': 'Supply'}), 1).kind).to_be('withdraw')
    spy_on(waterfall, 'funding_man', returns=None)
    spy_on(waterfall, 'reach_funding_man', impl=answer(True))
    expect(run_wait(waterfall.pickpocket_funding_man(scene.at, scene.log))).to_be(False)
    stub(quest_food, name='Lobster')
    snap.bank = {'lobster': 20}
    snap.bank_ids = {dig_supplies.DIG_ID.COINS: 10000}
    expect(len(dig_supplies.kit(snap).items)).to_be(2)
    item = Record({'id': 123, 'name': 'Tool', 'qty': 1})
    snap.bank_ids = {}
    expect(family.source(snap, item, 1, None).kind).to_be('wait')
    snap.bank_known = False
    expect(family.source(snap, item, 1, None).kind).to_be('scan_bank')
    expect(family.source_antipoison(snap, 1).kind).to_be('scan_bank')
    expect(ikov.withdraw_for(snap, [item]).kind).to_be('scan_bank')
    snap.bank_known = True
    expect(ikov.withdraw_for(snap, [item])).to_be_null()
    expect(ikov.decide(QuestSnapshot(journal='in_progress', stage=None)).kind).to_be('wait')
    expect(ikov.roots_trim_step(snap)).to_be_null()
    expect(workshop.owned(snap, 123)).to_be(0)
    expect(workshop.best_bank_weapon(snap)).to_be_null()
    expect(reg_supplies.scan_bank().kind).to_be('scan_bank')
    expect(workshop.best_held_pickaxe(snap)).to_be_null()
    expect(family.decide(QuestSnapshot(journal='in_progress', stage=None)).kind).to_be('wait')
    expect(family.decide(QuestSnapshot(journal='in_progress', stage=family.FC_STAGE.COMPLETE)).kind).to_be('done')
    snap.progress = None
    snap.stage = -1
    expect(digsite.plan(snap, -1, False).kind).to_be('wait')
    snap.bank_ids[digsite.DIG_ID.ROPE] = 1
    expect(digsite.rope_step(snap).kind).to_be('withdraw')


test('quest supplies distinguish unread banks, empty banks and affordable replacement tools', supply_boundaries)


def travel_boundaries():
    scene = Scene(isafdar.RG_TILE.ARDOUGNE_BANK)
    spy_on(isafdar, 'travel_tirannwn', impl=answer(True))
    expect(run_wait(isafdar.walk_to(scene.at, 1, 13, scene.log))).to_be(True)
    expect(run_wait(isafdar.walk_to(isafdar.RG_TILE.OLD_CAMP_WEST, 1, 13, scene.log))).to_be(True)
    scene.at = Tile(2400, 9500, 0)
    expect(run_wait(pockets.climb_out_of_pit(scene.log))).to_be(False)
    spy_on(modals, 'close', impl=answer(False))
    spy_on(bomb, 'still_button_id', returns=123)
    import _core
    spy_on(_core, 'click_component', returns=True)
    expect(run_wait(bomb.close_still())).to_be(True)
    snap = QuestSnapshot(inv_ids={}, inv={}, worn=set(), worn_ids=set())
    expect(upass.bridge_leg(snap, 'unknown').kind).to_be('wait')
    expect(upass.finish_leg('unknown').kind).to_be('wait')
    for item, fn in [[upass.UP_ITEM.ASHES, upass.rub_ashes], [upass.UP_ITEM.SHADOW, upass.rub_shadow],
                     [upass.UP_ITEM.DOVE, upass.rub_dove]]:
        snap.inv_ids = {item.id: 1}
        expect(upass.doll_leg(snap, 'main').run).to_be(fn)
    snap.tile = upass.UP_TILE.WITCH_DOOR
    snap.inv_ids = {}
    expect(upass.witch_leg(snap, 'witch').run).to_be(upass.loot_witch_chest)
    snap.inv_ids[upass.UP_ITEM.WITCH_CAT.id] = 1
    expect(upass.witch_leg(snap, 'witch').run).to_be(upass.distract_witch)
    scene.loc('Rocks', ['Climb'], id=pockets.HAND_HOLDS)
    expect(run_wait(pockets.climb_out_of_pit(scene.log))).to_be(False)
    import rs2004.quests.defs.regicide as regicide
    spy_on(regicide, 'draw_gear', returns=None)
    expect(regicide.stage_step(snap, 'tirannwn', -1).kind).to_be('wait')
    for stage, fn in [[regicide.RG_STAGE.SHOWN_PENDANT, regicide.follow_tracks],
                      [regicide.RG_STAGE.SPOKEN_TRACKER2, regicide.kill_soldier],
                      [regicide.RG_STAGE.DEFEATED_GUARD, regicide.enter_camp]]:
        expect(regicide.stage_step(snap, 'tirannwn', stage).run).to_be(fn)


test('quest travel short circuits arrival, handles missing pit exits and resumes each doll ingredient', travel_boundaries)
