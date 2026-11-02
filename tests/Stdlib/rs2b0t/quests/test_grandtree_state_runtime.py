"""Grand Tree's live journal boundary, cached stages and quest diagnostics."""

import rs2004.quests.defs.grandtree as tree
from rs2004.quests.defs.grandtree import journal
from rs2004.quests.defs.grandtree.areas import GT_OBJ, GT_STAGE, GT_TILE
from rs2004.quests.engine.types import QuestSnapshot
from rs2004.quests.food import quest_food
from rs2004.tabs import quests

after_each(journal.reset_grand_tree_stage)


def journal_world():
    scene = Scene(GT_TILE.narnode)
    scene.journal_lines = []
    journal.reset_grand_tree_stage()

    def read(name):
        expect(name).to_be(journal.QUEST)
        return list(scene.journal_lines)
        yield

    scene.journal_reads = spy_on(quests, 'journal', impl=read)
    return scene


def journal_status():
    scene = journal_world()
    scene.status = 'unknown'
    expect(run_wait(journal.read_grand_tree_stage())).to_be_null()
    scene.status = 'not_started'
    expect(run_wait(journal.read_grand_tree_stage())).to_be(GT_STAGE.NOT_STARTED)
    scene.status = 'complete'
    expect(run_wait(journal.read_grand_tree_stage())).to_be(GT_STAGE.COMPLETE)
    expect(scene.journal_reads.calls).to_equal([])
    expect(scene.ticks).to_be(0)
    scene.status = 'unknown'
    expect(run_wait(journal.read_grand_tree_stage())).to_be_null()


test('Grand Tree reads quest-list status without opening a journal and rejects unknown status', journal_status)


def cached_journal():
    scene = journal_world()
    scene.journal_lines = ['Loading...']
    expect(run_wait(journal.read_grand_tree_stage())).to_be_null()
    scene.journal_lines = ['@dbl@He has asked me to take a sample.']
    scene.main_modal = 123
    expect(run_wait(journal.read_grand_tree_stage())).to_be(GT_STAGE.STARTED)
    expect(scene.main_modal).to_be(-1)
    expect(scene.ticks).to_be(1)
    scene.journal_lines = ['Loading...']
    expect(run_wait(journal.read_grand_tree_stage())).to_be(GT_STAGE.STARTED)
    expect(scene.ticks).to_be(1)
    scene.journal_lines = ['@str@He has asked me to take a sample.', '@dbl@King Narnode has seen the light.']
    expect(run_wait(journal.read_grand_tree_stage())).to_be(GT_STAGE.SEARCHING_DACONIA)
    scene.journal_lines = []
    expect(run_wait(journal.read_grand_tree_stage())).to_be(GT_STAGE.SEARCHING_DACONIA)
    journal.reset_grand_tree_stage()
    expect(run_wait(journal.read_grand_tree_stage())).to_be_null()
    expect(len(scene.journal_reads.calls)).to_be(6)


test('Grand Tree closes its journal, advances the cached stage and survives unreadable pages', cached_journal)


def diagnostics():
    snap = QuestSnapshot()
    lines = tree.grandtree.observe(snap, Fake(kind='wait'))
    expect(lines).to_have_length(2)
    expect(lines[0]).to_contain('stage=? step=wait caves=False')
    expect(lines[1]).to_contain('twigs=0/4 rock=0')
    snap.stage = GT_STAGE.SEARCHING_DACONIA
    snap.tile = GT_TILE.cave_landing
    snap.inv_ids = {GT_OBJ.TWIG_T: 1, GT_OBJ.TWIG_Z: 1, GT_OBJ.DACONIA: 1}
    lines = tree.grandtree.observe(snap, Fake(kind='custom'))
    expect(lines[0]).to_contain('stage=150 step=custom caves=True')
    expect(lines[0]).to_contain('stronghold=False karamja=False')
    expect(lines[1]).to_contain('twigs=2/4 rock=1')


test('Grand Tree diagnostics distinguish unloaded state from cave inventory and progress', diagnostics)


def decision_boundaries():
    snap = QuestSnapshot(journal='in_progress', stage=999)
    step = tree.decide(snap)
    expect(step.kind).to_be('wait')
    expect(step.reason).to_be('unhandled Grand Tree stage 999')
    stub(quest_food, name=None)
    snap = QuestSnapshot(journal='in_progress', stage=GT_STAGE.UNLOCKED_TRAPDOOR,
                         tile=GT_TILE.glough_house_foot, magic=1, inv={'mind rune': 150, 'air rune': 300})
    expect(tree.demon_kit(snap)).to_be_null()
    step = tree.decide(snap)
    expect(step.kind).to_be('custom')
    expect(step.run).to_be(tree.fight_black_demon)


test('Grand Tree waits on unknown stages and skips food stocking when no food is configured', decision_boundaries)
