"""Quest entry-point workflows, readiness messages and runtime diagnostics."""

import rs2004.quests.defs.biohazard as bio
import rs2004.quests.defs.digsite as dig
import rs2004.quests.defs.dwarfcannon as cannon
import rs2004.quests.defs.familycrest as crest
import rs2004.quests.defs.fremenniktrials as fremennik
import rs2004.quests.defs.horror as horror
import rs2004.quests.defs.ikov as ikov
import rs2004.quests.defs.legends as legends
import rs2004.quests.defs.observatory as observatory
import rs2004.quests.defs.regicide as regicide
import rs2004.quests.defs.scorpcatcher as scorpion
import rs2004.quests.defs.treegnome as tree
import rs2004.quests.defs.witchshouse as witch
from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.quests.defs.familycrest.areas import ANTIPOISON_IDS, FC_NPC
from rs2004.quests.defs.heroquest import partner
from rs2004.quests.engine.types import QuestProgress, QuestSnapshot
from rs2004.reach import reach


def answer(value):
    def wait(*args, **kwargs):
        return value
        yield
    return wait


WORKFLOWS = [
    [ikov, ikov.talk_to_winelda, ['escape_pocket', 'wear_fear_pendant', 'temple_walk', 'talk_strict']],
    [ikov, ikov.finish_for_armadyl, ['leave_the_far_side', 'kill_lucien']],
    [legends, legends.book_leg, ['enter_shaman_cave', 'descend_to_gem_room', 'take_book_of_binding']],
    [legends, legends.descend_leg, ['drink_bravery', 'enter_shaman_cave', 'descend_to_winch', 'climb_down_winch']],
    [legends, legends.dagger_to_ungadulu, ['climb_ledges', 'climb_out_of_trials', 'enter_shaman_cave', 'enter_octagram', 'trade_dagger_for_spell']],
    [legends, legends.cross_and_rouse, ['cross_barrier', 'take_black_dagger']],
]


def workflow(module, fn, steps):
    scene = Scene()
    for name in steps:
        step = spy_on(module, name, impl=answer(False))
        expect(run_wait(fn(scene.log))).to_be(False)
        step.mock_implementation(answer(True))
    expect(run_wait(fn(scene.log))).to_be(True)


test_each(WORKFLOWS)('quest workflow stops at every failed prerequisite: %s %s', workflow)


def legends_runtime_upkeep():
    scene = Scene()
    expect(run_wait(legends.ditch([123])(scene.log))).to_be(False)
    scene.item(123, 'Spent item', effect=lambda op: scene.take(123))
    expect(run_wait(legends.ditch([123])(scene.log))).to_be(True)
    expect(scene.has(123)).to_be(False)
    expect(run_wait(legends.eat_one(scene.log))).to_be(False)
    food = legends.FOOD_FOR_SLOT[0]
    scene.item(food.id, food.name, effect=lambda op: scene.take(food.id))
    expect(run_wait(legends.eat_one(scene.log))).to_be(True)
    expect(run_wait(legends.drink_bravery(scene.log))).to_be(True)
    scene.item(legends.LQ_ID.BRAVERY_POTION, 'Potion', effect=lambda op: False)
    expect(run_wait(legends.drink_bravery(scene.log))).to_be(False)
    scene.pack = []
    scene.item(legends.LQ_ID.BRAVERY_POTION, 'Potion', effect=lambda op: scene.take(legends.LQ_ID.BRAVERY_POTION))
    expect(run_wait(legends.drink_bravery(scene.log))).to_be(True)
    summon = spy_on(legends, 'summon_demon', impl=answer(False))
    expect(run_wait(legends.summon_and_fight(scene.log))).to_be(False)
    summon.mock_implementation(answer(True))

    def fight(plan, log):
        expect(plan.npc).to_be(legends.LQ_NPC.NEZIKCHENED)
        expect(plan.done()).to_be(True)
        return True
        yield

    spy_on(legends, 'fight', impl=fight)
    expect(run_wait(legends.summon_and_fight(scene.log))).to_be(True)
    snap = QuestSnapshot(stage=-1, journal='in_progress', bank_known=True, inv_ids={}, bank_ids={})
    spy_on(legends, 'legends_area', returns='jungle')
    expect(legends.choose(snap).kind).to_be('wait')
    expect(legends.stage_grow(snap).run).to_be(legends.ask_for_more_seeds)
    snap.inv_ids[legends.LQ_ID.YOMMI_SEEDS] = 1
    snap.inv_ids[legends.LQ_ID.GOLD_BOWL_BLESSED_PURE] = 1
    expect(legends.stage_grow(snap).run).to_be(legends.germinate_seeds)


test('Legends drops spent items, frees food slots, drinks bravery and verifies summoned demons are gone', legends_runtime_upkeep)


def observations():
    scene = Scene()
    spy_on(game, 'weight', returns=0)
    snap = QuestSnapshot(inv_ids={}, bank_ids={}, worn_ids=set())
    wait = Fake(kind='wait')
    custom = Fake(kind='custom', name='test errand')
    for module in [dig.digsite, ikov.ikov, legends.legends, regicide.regicide, witch.witchshouse]:
        lines = module.observe(snap, wait)
        expect(len(lines) > 0).to_be(True)
        expect('?' in ' '.join(lines)).to_be(True)
        snap.stage = 1
        snap.tile = Tile(2725, 3352, 0)
        lines = module.observe(snap, custom)
        expect('1' in ' '.join(lines)).to_be(True)
        snap.stage = None
        snap.tile = None
    for at, expected in [[dig.DIG_TILE.TABLET, 'altar cave'], [dig.DIG_TILE.ARCENIA_WEST, 'west shaft'],
                          [dig.DIG_TILE.BRICK_STAND, 'east shaft'], [None, 'surface']]:
        expect(dig.region(QuestSnapshot(tile=at))).to_be(expected)
    for at, expected in [[None, 'off-scene'], [witch.WH_TILE.BALL, 'shed'],
                          [witch.WH_TILE.FOUNTAIN, 'garden'], [Tile(1, 2, 0), '1,2,L0']]:
        expect(witch.where(QuestSnapshot(tile=at))).to_be(expected)
    expect(legends.inside_legends(None)).to_be(False)
    expect(regicide.inside_regicide(None)).to_be(False)
    scene.say('The server said hello')
    expect(legends.observe(snap, wait)[1]).to_contain('hello')
    expect(regicide.observe(snap, wait)[2]).to_contain('hello')


test('quest diagnostics handle unloaded state, named pockets and recent server messages', observations)


def readiness():
    scene = Scene()
    expect(cannon.warn_dwarf_cannon_readiness()).to_be_null()
    expect(observatory.warn_observatory_readiness()).to_be_null()
    expect(scorpion.warn_readiness()).to_be_null()
    expect(fremennik.readiness()).to_contain('raw shark')
    for skill in ['crafting', 'smithing', 'hitpoints', 'prayer', 'woodcutting', 'fletching', 'attack', 'strength', 'defence']:
        scene.stats[skill] = 1
    expect(cannon.warn_dwarf_cannon_readiness()).to_contain('below 40')
    expect(observatory.warn_observatory_readiness()).to_contain('below the proven profile')
    expect(scorpion.warn_readiness()).to_contain('Prayer 1')
    expect(fremennik.readiness()).to_contain('needs')
    scene.stats['prayer'] = 99
    expect(scorpion.warn_readiness()).to_contain('melee 1')
    expect(tree.warn_readiness()).to_contain('warlord')


test('readiness explains low skills before entering quest fights', readiness)


def crest_npcs():
    scene = Scene(FC_NPC.AVAN)
    scene.walk_ok = False
    expect(run_wait(crest.talk_to_avan([], scene.log))).to_be(False)
    expect(run_wait(crest.cure_johnathon(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(crest.talk_to_avan([], scene.log))).to_be(False)
    scene.npc('Man', id=FC_NPC.AVAN_NPC_ID)
    op = spy_on(reach, 'entity_op', impl=answer('unreachable'))
    expect(run_wait(crest.talk_to_avan([], scene.log))).to_be(False)
    op.mock_implementation(answer('done'))
    expect(run_wait(crest.talk_to_avan([], scene.log))).to_be(True)
    expect(run_wait(crest.cure_johnathon(scene.log))).to_be(False)
    scene.npc('Johnathon')
    scene.item(ANTIPOISON_IDS[0], 'Antipoison', on_use=lambda target: False)
    expect(run_wait(crest.cure_johnathon(scene.log))).to_be(False)
    scene.pack = []
    scene.item(ANTIPOISON_IDS[0], 'Antipoison')
    scene.chat.pages = ['continue']
    expect(run_wait(crest.cure_johnathon(scene.log))).to_be(True)


test('Avan is selected by id and any antipoison dose cures Johnathon', crest_npcs)


def hero_handoffs():
    scene = Scene()
    partner.reset_hero_handoff_state()
    leave = spy_on(partner, 'return_to_street', impl=answer(False))
    expect(run_wait(partner.run_hero_handoff('give-key', scene.log))).to_be(False)
    leave.mock_implementation(answer(True))
    trade = spy_on(partner, 'run_partner_handoff', impl=answer(False))
    expect(run_wait(partner.run_hero_handoff('give-key', scene.log))).to_be(False)
    expect(partner.hero_handoff_state.gave_key).to_be(False)
    trade.mock_implementation(answer(True))
    for handoff, giving in [['give-key', True], ['take-key', False], ['give-candlestick', True], ['take-candlestick', False]]:
        expect(run_wait(partner.hero_handoff_step(handoff).run(scene.log))).to_be(True)
        expect(trade.calls[-1][0].giving).to_be(giving)
    expect(partner.hero_handoff_state.gave_key).to_be(True)
    expect(partner.hero_handoff_state.lure_failures).to_be(0)


test('partner handoffs leave sealed rooms and latch only a successful spare-key trade', hero_handoffs)
