"""Recovery cases from rs2b0t #905, #907 and #908 (MIT, see thirdparty/rs2b0t)."""

import rs2004.quests.defs.demonslayer as demon
import rs2004.quests.defs.restlessghost as ghost
import rs2004.quests.defs.lostcity as lost
import rs2004.quests.defs.scorpcatcher as scorpion
import rs2004.quests.defs.holygrail as grail
import rs2004.quests.defs.holygrail.legs as bell
import rs2004.quests.defs.gertrudescat as cat
import rs2004.quests.defs.ikov.gear as ikov
import rs2004.quests.defs.elementalworkshop.supplies as workshop
from rs2004.quests.engine.types import QuestProgress, QuestSnapshot
from rs2004.catalogs.record import Record


def snapshot(**fields):
    snap = QuestSnapshot(journal='in_progress', inv_ids={}, bank_ids={}, bank={}, bank_known=True, free_slots=20, worn_ids=set())
    for key, value in fields.items():
        setattr(snap, key, value)
    return snap


def bone_withdrawal():
    snap = snapshot(inv_ids={demon.ROVIN_KEY_ID: 1}, bank_ids={demon.BONES_ID: 25}, free_slots=7)
    step = demon.decide(snap)
    expect(step.kind).to_be('withdraw')
    expect(step.items).to_equal([{'name': 'Bones', 'id': demon.BONES_ID, 'qty': 7}])
    snap.bank_known = False
    expect(demon.decide(snap).kind).to_be('scan_bank')
    snap.bank_known = True
    snap.bank_ids = {}
    expect(demon.decide(snap).kind).to_be('custom')
    snap.bank_ids = {demon.BONES_ID: 25}
    snap.inv_ids[demon.BONES_ID] = 25
    expect(demon.decide(snap).kind).to_be('custom')


test('Demon Slayer uses banked bones before hunting and never withdraws more than fits', bone_withdrawal)


def amulet_recovery():
    snap = snapshot(bank_known=False)
    expect(ghost.decide(snap).kind).to_be('scan_bank')
    snap.bank_known = True
    snap.bank_ids = {ghost.AMULET_ID: 1}
    step = ghost.decide(snap)
    expect(step.kind).to_be('withdraw')
    expect(step.items[0]['id']).to_be(552)
    expect(step.bank.equals(ghost.DRAYNOR_BANK)).to_be(True)
    snap.bank_ids = {}
    expect(ghost.decide(snap).stop.npc).to_be('Father Urhney')


test('Restless Ghost checks for a banked amulet before asking for another', amulet_recovery)


def coal_sources():
    snap = snapshot()
    expect(workshop.gather_coal(snap, 20).kind).to_be('wait')
    step = workshop.gather_coal(snap, 30)
    expect(step.kind).to_be('grab_ground')
    expect(step.item).to_be('Bronze pickaxe')
    snap.bank_ids = {1275: 1, 1265: 1}
    step = workshop.gather_coal(snap, 30)
    expect(step.items[0]['id']).to_be(1265)
    snap.inv_ids = {1265: 1}
    step = workshop.gather_coal(snap, 30)
    expect(step.kind).to_be('mine_rock')
    expect(step.qty).to_be(4)
    snap.inv_ids[453] = 2
    expect(workshop.gather_coal(snap, 30).qty).to_be(2)
    snap.bank_ids = {453: 1}
    expect(workshop.gather_coal(snap, 30).items[0]['qty']).to_be(1)
    snap.bank_ids = {453: 2}
    expect(workshop.gather_coal(snap, 30)).to_be(None)
    snap.bank_ids = {}
    snap.inv_ids[453] = 4
    expect(workshop.gather_coal(snap, 30)).to_be(None)
    snap.inv_ids = {}
    snap.free_slots = 1
    step = workshop.gather_coal(snap, 30)
    expect(step.kind).to_be('deposit')
    expect(step.exact_keep).to_be(True)
    snap.inv_ids = {1265: 1}
    expect(1265 in workshop.gather_coal(snap, 30).keep_ids).to_be(True)
    snap.free_slots = 20
    snap.inv_ids = {}
    snap.worn_ids = set([1265])
    expect(workshop.gather_coal(snap, 30).kind).to_be('mine_rock')
    spy_on(workshop.skills, 'level', returns=30)
    expect(workshop.surface_loadout(snap, False, True).kind).to_be('mine_rock')


test('Elemental Workshop sources missing coal with a usable pickaxe and enough space', coal_sources)


def excalibur_sources():
    snap = snapshot(inv={'excalibur': 1}, bank_known=False)
    expect(grail.excalibur_plan(snap).kind).to_be('equip')
    snap.inv = {}
    snap.worn.add('excalibur')
    expect(grail.excalibur_plan(snap).kind).to_be('equip')
    snap.worn.clear()
    expect(grail.excalibur_plan(snap).kind).to_be('scan_bank')


test('Holy Grail equips owned Excalibur before consulting the bank', excalibur_sources)


def bell_landing(teleport):
    def run():
        lands = teleport
        state = Record({'tile': Tile(2763, 4693, 0), 'rings': 0, 'dialog': False})
        def ring(op):
            state.rings += 1
            state.dialog = True
            return True
        def drive(prefer, log):
            state.dialog = False
            if lands:
                state.tile = bell.GRAIL_TILE.CASTLE_LANDING
            return True
            yield
        patch(bell, 'inside_castle', False)
        spy_on(bell, 'walk_to', impl=lambda *args: result(True))
        spy_on(bell, 'drive_dialog', impl=drive)
        spy_on(bell.game, 'tile', impl=lambda: state.tile)
        spy_on(bell.npcs, 'query', impl=querying(lambda: [Fake(name='Grail Maiden', tile=lambda: Tile(2762, 4693, 0))]))
        spy_on(bell.inventory, 'first', returns=Fake(interact=ring))
        spy_on(bell.chat_dialog, 'is_open', impl=lambda: state.dialog)
        spy_on(bell.chat_dialog, 'can_continue', returns=False)
        spy_on(bell.execution, 'delay_until', impl=instant_until)
        expect(run_wait(bell.ring_bell(lambda message: None))).to_be(lands)
        expect(state.rings).to_be(1 if lands else bell.RING_ATTEMPTS)
        expect(bell.inside_castle).to_be(lands)
    return run


def result(value):
    return value
    yield


test('Holy Grail waits for the exact landing after answering the bell dialogue', bell_landing(True))
test('standing beside the Grail castle never counts as a successful teleport', bell_landing(False))


def entrana_bounds():
    expect(lost.lost_city_area(Tile(2850, 3391, 0))).to_be('entrana')
    expect(lost.lost_city_area(Tile(2850, 3392, 0))).to_be('mainland')
    expect(lost.lost_city_area(Tile(2850, 3430, 0))).to_be('mainland')


test('Lost City does not treat the coast north of Entrana as the island', entrana_bounds)


def worn_ikov_gear():
    expect(ikov.stocked(snapshot(worn=set(['rune scimitar'])), 'Rune scimitar')).to_be(1)


test('Ikov counts worn gear when selecting the best available equipment', worn_ikov_gear)


def barcrawl_card():
    snap = snapshot(inv_ids={scorpion.CAGE_ID.EMPTY: 1}, progress=QuestProgress(scorpion.SC_STAGE.FIRST_HINT))
    # The first scorpion has already been caught; the Barbarian Outpost scorpion is next.
    snap.inv_ids = {scorpion.CAGE_ID.A: 1}
    snap.bank_known = False
    expect(scorpion.decide(snap).kind).to_be('scan_bank')
    snap.bank_known = True
    snap.bank = {scorpion.BARCRAWL_CARD.lower(): 1}
    step = scorpion.decide(snap)
    expect(step.kind).to_be('withdraw')
    expect(step.items[0]['name']).to_be(scorpion.BARCRAWL_CARD)
    snap.bank = {}
    expect(scorpion.decide(snap).kind).to_be('custom')


test('Scorpion Catcher recovers its banked barcrawl card', barcrawl_card)
