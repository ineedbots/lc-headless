"""Waterfall preserves chosen food and cheap substitutes while resuming."""

import rs2004.quests.defs.waterfall as wf
from rs2004.quests.engine.types import QuestSnapshot


def supply_policy():
    scene = Scene()
    state = QuestSnapshot(journal='in_progress', bank_known=False, free_slots=28, tile=wf.ARDOUGNE_BANK, inv_ids={})
    expect(wf.source_food(state).kind).to_be('scan_bank')
    expect(wf.source_rope(state).kind).to_be('scan_bank')
    expect(wf.source_puzzle_runes(state).kind).to_be('scan_bank')
    state.bank_known = True
    state.free_slots = 0
    expect(wf.source_food(state).kind).to_be('wait')
    state.free_slots = 28
    state.inv_ids = {995: 500}
    expect(wf.ensure_coins(state)).to_be(None)
    expect(wf.source_rope(state).kind).to_be('buy')
    state.inv_ids = None
    state.inv = {'trout': 8, 'cake': 1}
    expect(wf.inventory_has_outside_ids(state, [333, 1891])).to_be(False)
    state.inv['junk'] = 1
    expect(wf.inventory_has_outside_ids(state, [333, 1891])).to_be(True)
    stub(wf.quest_food, name='')
    expect(wf.food_item()).to_be(None)
    for area in ['hudonMound', 'fallsLedge', 'fallsTreeBank', 'tgvDungeon', 'glarialTomb', 'waterfallDungeon', 'puzzleRoom', 'raisedRoom']:
        expect(wf.escape_unexpected_area(area) is not None).to_be(True)
    expect(wf.escape_unexpected_area('mainland')).to_be(None)


test('Waterfall supply and exit policy retains configured food and respects one-way pockets', supply_policy)
