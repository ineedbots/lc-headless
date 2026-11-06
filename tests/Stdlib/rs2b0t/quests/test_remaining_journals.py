"""Restart recovery uses journal stages instead of transient flags."""

import rs2004.quests.defs.blackknight as bk
import rs2004.quests.defs.runemysteries as rm
import rs2004.quests.defs.merlinscrystal as mc
from rs2004.quests.engine.types import QuestSnapshot


def reply(value):
    return value
    yield


def journals():
    scene = Scene()
    for module, reader, complete in [(bk, bk.read_stage, 4), (rm, rm.read_stage, 6), (mc, mc.read_merlin_stage, 7)]:
        for status, expected in [('complete', complete), ('not_started', 0), ('unknown', None)]:
            spy_on(module.quests, 'status', returns=status)
            expect(run_wait(reader())).to_be(expected)
        spy_on(module.quests, 'status', returns='in_progress')
        samples = [("asked me to investigate", 1), ('I eavesdropped on a witch', 2), ("now that I have sabotaged the witch's potion", 3), ('Quest complete!', 4)] if module is bk else ([(text, i) for i, text in enumerate(['i can start this quest by speaking to', 'i need to find the head wizard', 'i should talk to the head wizard again', 'i should take this research package', 'i should speak to aubury again', 'i should take the notes to sedridor', 'quest complete!'])] if module is rm else [(text, i) for i, text in enumerate(['i can start this quest', 'i should ask the', 'impenetrable fortress', 'delivery by sea', 'in return for sparing her son', 'i summoned the spirit thrantax', 'i freed merlin by shattering', 'quest complete!'])])
        for text, expected in samples + [('unrecognized journal', None)]:
            spy_on(module.quests, 'journal', impl=lambda name: reply([text]))
            expect(run_wait(reader())).to_be(expected)


test('Black Knight, Rune Mysteries and Merlin restore each journal stage', journals)


def fortress_sources():
    state = QuestSnapshot(journal='in_progress', stage=1, bank_known=False)
    expect(bk.source_item(state, 'Cabbage').kind).to_be('scan_bank')
    state.bank_known = True
    state.bank_ids = {1965: 1}
    expect(bk.source_item(state, 'Cabbage').items[0]['id']).to_be(1965)
    state.bank_ids = {}
    expect(bk.source_item(state, 'Cabbage').name).to_be('pick cabbage')
    expect(bk.source_item(state, bk.IRON_CHAINBODY).shop.npc).to_be('Wayne')
    expect(bk.source_item(state, bk.BRONZE_MED_HELM).shop.npc).to_be('Peksa')
    state.bank = {'iron chainbody': 1}
    expect(bk.source_item(state, bk.IRON_CHAINBODY).kind).to_be('withdraw')
    state.stage = None
    expect(bk.decide(state).kind).to_be('wait')
    state.stage = 3
    expect(bk.decide(state).stop).to_be(bk.SIR_AMIK)


test('fortress preparation distinguishes ordinary cabbage and banked or shop armor', fortress_sources)


def merlin_restart_steps():
    scene = Scene()
    state = QuestSnapshot(journal='in_progress', stage=None, bank_known=True, tile=Tile(2758, 3508, 0))
    expect(mc.decide(state).kind).to_be('wait')
    state.stage = 3
    expect(mc.decide(state).name).to_be('fortress (Mordred + Morgan)')
    state.stage = 4
    state.tile = Tile(2770, 3400, 0)
    expect(mc.decide(state).name).to_be('leave Mordred fortress')
    state.tile = Tile(2758, 3508, 0)
    state.stage = 6
    expect(mc.decide(state).stop).to_be(mc.KING_ARTHUR)
    state.stage = 5
    state.bank_known = False
    expect(mc.decide(state).kind).to_be('scan_bank')
    state.bank_known = True
    state.bank = {'excalibur': 1}
    expect(mc.decide(state).kind).to_be('withdraw')
    state.bank = {}
    state.inv = {'excalibur': 1}
    expect(mc.decide(state).name).to_be('summon Thrantax + break the crystal')
    state.inv = {}
    expect(mc.decide(state).name).to_be('get Excalibur (Lady of the Lake + Beggar)')
    state.stage = 1
    state.worn = set(['iron chainbody', 'bronze med helm'])
    expect(bk.decide(state).name).to_be('pick cabbage')


test('Merlin restarts route to the keep, banked sword, ritual or final hand-in', merlin_restart_steps)
