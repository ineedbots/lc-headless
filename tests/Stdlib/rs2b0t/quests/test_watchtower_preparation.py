"""Watch Tower recovery keeps the kit for the current phase and the safe exit."""

import rs2004.quests.defs.watchtower as wt
from rs2004.quests.defs.watchtower import caves, enclave, gutanoth, loadout, supplies
from rs2004.quests.defs.watchtower.areas import WT_ITEM as I, CRYSTALS, WT_LOC
from rs2004.quests.engine.types import QuestProgress, QuestSnapshot
from rs2004.execution import event_signal
from rs2004.quests.defs.tbwt import supplies as tb_supplies


def result(value):
    yield from ()
    return value


def snap(stage, ids=None, flags=None):
    return QuestSnapshot(stage=stage, progress=QuestProgress(stage, set(flags or [])),
                         inv_ids=ids or {}, bank_ids={}, bank={}, bank_known=True,
                         inv={}, tile=Tile(2544, 3090), worn=set(), worn_ids=set())


def phase_kit():
    expect(tb_supplies.keep_names(snap(6))).to_contain('lobster')
    expect([i.id for i in loadout.phase_items(snap(6))]).to_contain(I.LIT_CANDLE.id)
    expect([i.id for i in loadout.phase_items(snap(7, {I.NIGHTSHADE.id: 1}))]).to_equal([I.NIGHTSHADE.id])
    expect([i.id for i in loadout.phase_items(snap(9))]).to_contain(I.BAT_BONES.id)
    expect(loadout.phase_items(snap(9, {I.OGRE_POTION.id: 1}))).to_equal([I.OGRE_POTION])
    expect([i.id for i in loadout.phase_items(snap(9, {I.GUAM_JANGER_VIAL.id: 1, I.GROUND_BAT_BONES.id: 1}))]).to_equal([I.GUAM_JANGER_VIAL.id, I.GROUND_BAT_BONES.id])
    ids = {I.CRYSTAL3.id: 1, I.CRYSTAL4.id: 1}
    expect(loadout.phase_items(snap(10, ids, ['shamans-left:0']))).to_equal([I.ROPE])
    ids[I.CRYSTAL1.id] = 1
    expect(loadout.phase_items(snap(10, ids, ['shamans-left:0']))).to_equal([I.SKAVID_MAP, I.LIT_CANDLE])
    for stage in [6, 9, 10]:
        pack = [Fake(id=I.GOLD_BAR.id, name=I.GOLD_BAR.name, count=2, noted=False)]
        plan = loadout.retain_watchtower_loadout(snap(stage), pack)
        if stage == 6:
            expect(plan.keep_ids).to_contain(I.GOLD_BAR.id)
            expect(plan.caps[0].qty).to_be(1)
        else:
            expect(plan.keep_ids).to_equal([])
    expect(caves.next_skavid_cave(QuestProgress(6))).to_be(5)
    flags = set(['learning-skavid'])
    for index in [1, 2, 3, 4]:
        expect(caves.next_skavid_cave(QuestProgress(6, flags))).to_be(index)
        flags.add(caves.WORD_FLAG[index])
    expect(caves.next_skavid_cave(QuestProgress(6, flags))).to_be(6)
    full = snap(6).with_fields({'free_slots': 0, 'inv': {'junk': 28}})
    expect(supplies.make_room(full).kind).to_be('deposit')
    expect(supplies.source_food(full, 8).kind).to_be('wait')


test('phase kits retain cave light, gate payment and the current potion ingredients', phase_kit)


def exits_and_relics():
    scene = Scene()
    area = ['lowerCity']
    spy_on(wt, 'watchtower_area', impl=lambda tile: area[0])
    leave = spy_on(wt, 'leave_cave', impl=lambda log: result(False))
    step = wt.escape_pocket('skavidCaves', 'yanille')
    expect(run_wait(step.run(scene.log))).to_be(False)
    leave.mock_implementation(lambda log: result(True))
    spy_on(wt, 'leave_city', impl=lambda log: result(True))
    expect(run_wait(step.run(scene.log))).to_be(True)
    area[0] = 'yanille'
    expect(run_wait(step.run(scene.log))).to_be(True)
    expect(wt.escape_pocket('surface', 'yanille')).to_be(None)
    s = snap(3).with_fields({'bank_known': False})
    expect(wt.stage_relic_gate(s, 'yanille').kind).to_be('scan_bank')
    s.bank_known = True
    s.bank_ids[I.OGRE_RELIC.id] = 1
    expect(wt.stage_relic_gate(s, 'yanille').items[0]['id']).to_be(I.OGRE_RELIC.id)
    expect(run_wait(wt.asking(I.RELIC_PART1.id, lambda log: result(True))(scene.log))).to_be(True)
    expect(I.RELIC_PART1.id in wt.relic_state.asked).to_be(True)
    wt.relic_state.asked.clear()
    ids = {I.CRYSTAL1.id: 1, I.CRYSTAL3.id: 1, I.CRYSTAL4.id: 1}
    expect(wt.recover_crystals(snap(10, ids), 'yanille').kind).to_be('wait')
    ids[I.SKAVID_MAP.id], ids[I.LIT_CANDLE.id] = 1, 1
    expect(wt.recover_crystals(snap(10, ids), 'skavidCaves').kind).to_be('custom')
    ids[I.CRYSTAL2.id] = 1
    ids.pop(I.CRYSTAL4.id)
    expect(wt.recover_crystals(snap(10, ids), 'enclave').name).to_contain('mine')


test('recovery leaves sealed pockets and retrieves banked or lost relics and crystals', exits_and_relics)


def enclave_reserve():
    scene = Scene()
    spy_on(enclave, 'leave_enclave', impl=lambda log: result(True))
    expect(run_wait(enclave.safe_to_continue(scene.log))).to_be(False)
    spy_on(enclave.skills, 'effective', returns=10)
    sustain = spy_on(enclave.sustain, 'run', impl=lambda: result(True))
    expect(run_wait(enclave.safe_to_continue(scene.log))).to_be(False)
    expect(len(sustain.calls)).to_be(1)
    def interrupted_meal():
        spy_on(event_signal, 'pending', returns=True)
        yield from ()
    sustain.mock_implementation(interrupted_meal)
    expect(run_wait(enclave.safe_to_continue(scene.log))).to_be(False)
    spy_on(event_signal, 'pending', returns=True)
    expect(run_wait(enclave.safe_to_continue(scene.log))).to_be(False)
    expect(run_wait(enclave.enter_enclave(scene.log))).to_be(False)
    expect(run_wait(enclave.mine_dalgroth(scene.log))).to_be(False)
    expect(run_wait(enclave.search_shaman_robe(scene.log))).to_be(False)


test('enclave work retreats when its food reserve is exhausted and respects interruptions', enclave_reserve)


def paid_gate():
    scene = Scene(Tile(2540, 3030))
    spy_on(gutanoth.game, 'my_name', returns='Review gate test')
    gutanoth.remember_gate_payment(False)
    spy_on(gutanoth, 'past_east_gate', impl=lambda: scene.at.z <= 3027)
    gate = scene.loc('Gate', ['Open'], id=WT_LOC.GATE_EAST, effect=lambda op: False)
    expect(run_wait(gutanoth.cross_east_gate(scene.log))).to_be(False)
    scene.locs = []
    def crossed(op):
        scene.at = Tile(2540, 3027)
        return True
    scene.loc('Gate', ['Open'], id=WT_LOC.GATE_EAST, effect=crossed)
    expect(run_wait(gutanoth.cross_east_gate(scene.log))).to_be(True)
    expect(gutanoth.gold_gate_needs_payment()).to_be(False)
    spy_on(gutanoth, 'leave_east_gate', impl=lambda log: result(True))
    expect(run_wait(gutanoth.leave_city(scene.log))).to_be(True)
    gutanoth.gate_payments.pop('Review gate test')


test('a previously paid east gate opens without another gold bar', paid_gate)


def supplies_before_special_areas():
    scene = Scene()
    s = snap(6, {I.SKAVID_MAP.id: 1, I.LIT_CANDLE.id: 1}, ['learning-skavid', 'learned-nod', 'learned-ig', 'learned-ar', 'learned-cur'])
    spy_on(wt, 'gold_gate_needs_payment', returns=True)
    s.bank_ids[I.GOLD_BAR.id] = 1
    expect(wt.stage_caves(s, 'yanille').items[0]['id']).to_be(I.GOLD_BAR.id)
    s = snap(6)
    s.bank_ids[I.SKAVID_MAP.id] = 1
    expect(wt.need_cave_kit(s, 'yanille').kind).to_be('withdraw')
    s = snap(9, {I.GUAM_VIAL.id: 1})
    s.bank_ids[I.JANGERBERRIES.id] = 1
    expect(wt.stage_potion(s, 'yanille').items[0]['id']).to_be(I.JANGERBERRIES.id)
    s.inv_ids[I.JANGERBERRIES.id] = 1
    s.bank_ids[I.GROUND_BAT_BONES.id] = 1
    expect(wt.stage_potion(s, 'yanille').items[0]['id']).to_be(I.GROUND_BAT_BONES.id)
    s = snap(10)
    spy_on(wt, 'in_dragon_lair', returns=True)
    expect(wt.decide_next(s).name).to_be('leave the dragon lair')
    spy_on(wt, 'in_dragon_lair', returns=False)
    spy_on(wt, 'dragon_bank_pending', returns=True)
    expect(wt.decide_next(s).name).to_contain('refresh the bank')
    spy_on(wt, 'dragon_bank_pending', returns=False)
    spy_on(wt, 'watchtower_area', returns='mirrorTower')
    s.journal = 'complete'
    s.inv_ids[I.WATCHTOWER_SPELL.id] = 1
    expect(wt.decide_next(s).name).to_contain('read the Watchtower spell')
    s.journal, s.stage = 'in_progress', -1
    spy_on(wt, 'watchtower_area', returns='yanille')
    expect(wt.decide_next(s).kind).to_be('wait')


test('banked cave payments and potion ingredients are withdrawn before reissuing supplies', supplies_before_special_areas)
