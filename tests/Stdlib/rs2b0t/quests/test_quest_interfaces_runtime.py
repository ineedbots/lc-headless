"""Exercise quest journal, banking and card interfaces."""
import _core
from rs2004 import execution
from rs2004.game import reader, game as maze_game
from rs2004.tabs import quests
from rs2004.dialogue import modals
from rs2004.items import inventory
from rs2004.messages import game_messages
from rs2004.quests.defs import def_by_id
from rs2004.quests.exec.steps import run_maybe
from rs2004.quests.engine.types import QuestSnapshot
from rs2004.quests.defs.dragonslayer import stock, ORACLE_CHARMS
from rs2004.quests.barcrawl.run_barcrawl import read_card


def journal_case(id, line, stage):
    def run():
        text = line
        state = {'modal': 123, 'closed': 0}
        def journal(name):
            return [text]
            yield
        def close():
            state['modal'] = -1
            state['closed'] += 1
            return True
        spy_on(quests, 'status', returns='in_progress')
        spy_on(quests, 'journal', impl=journal)
        spy_on(reader, 'modals', impl=lambda: Fake(main=state['modal']))
        spy_on(_core, 'close_interfaces', impl=close)
        spy_on(execution, 'delay_ticks', impl=instant_ticks)
        module = def_by_id(id)
        result = run_wait(run_maybe(module.read_progress()))
        expect(result.stage).to_be(stage)
        expect(state['closed']).to_be(1)
    return run


test('Arrav reads a live journal and closes its main modal', journal_case('blackarmgang',
     'He directed me to speak to Katrine in the gang HQ', 21))
test('Dragon Slayer reads a live journal and closes its main modal', journal_case('dragon',
     'I should speak to Oziach', 1))


def banked_charms():
    snap = QuestSnapshot(bank_known=True, bank_ids={301:1}, inv_ids={})
    step = stock(snap, ORACLE_CHARMS)
    expect(step.kind).to_be('withdraw')
    expect(step.items[0]['id']).to_be(301)
    expect(step.items[0]['qty']).to_be(1)


test('banked supplies produce the dictionary rows the executor consumes', banked_charms)


def drunken_card():
    spy_on(inventory, 'first', returns=Fake(interact=lambda op: True))
    spy_on(modals, 'close_if_open', impl=instant_ticks)
    spy_on(reader, 'modals', returns=Fake(main=-1))
    spy_on(game_messages, 'mark', returns=10)
    seen = []
    def saw(mark, pattern):
        seen.append(pattern)
        return pattern in 'you are too drunk to be able to read the barcrawl card'
    spy_on(game_messages, 'saw_since', impl=saw)
    spy_on(execution, 'delay_until', impl=instant_until)
    spy_on(execution, 'delay_ticks', impl=instant_ticks)
    result = run_wait(read_card())
    expect(result.done).to_be(True)
    expect(result.remaining).to_equal([])
    expect(seen).to_equal(['too drunk to be able to read'])


test('a fully signed card finishes when Read answers too drunk', drunken_card)


def main_modal_lines():
    state = {'id': -1}
    spy_on(_core, 'get_main_modal', impl=lambda: state['id'])
    texts = spy_on(_core, 'get_texts', impl=lambda id: ['the chest is empty'] if id == 123 else [])
    expect(reader.main_modal_texts()).to_equal([])
    expect(len(texts.calls)).to_be(0)
    state['id'] = 123
    expect(reader.main_modal_texts()).to_equal(['the chest is empty'])
    state['id'] = -1
    expect(reader.main_modal_texts()).to_equal([])


test('main modal text reads only the currently open interface', main_modal_lines)


def supplier_preparation():
    from bots import arrav_supplier as supplier
    from rs2004.settings import settings_store
    stages = [0, 1, 8]
    steps = []
    saved = []
    def progress():
        return Fake(stage=stages.pop(0), flags=set())
        yield
    def execute(step, hops, log):
        steps.append(step.name)
        return True
        yield
    spy_on(settings_store, 'saved', returns=None)
    spy_on(settings_store, 'save', impl=lambda ns, key, value: saved.append([key, value]))
    spy_on(supplier, 'read_shield_of_arrav_progress', impl=progress)
    spy_on(supplier, 'execute_step', impl=execute)
    spy_on(inventory, 'items', returns=[])
    bot = supplier.ArravSupplier()
    spy_on(bot, 'log', impl=lambda *args: None)
    expect(run_wait(bot._prepare_phoenix())).to_be(True)
    expect(steps).to_equal(['ask Reldo for a quest', 'check the palace bookcase'])
    expect(saved).to_equal([['mission', True]])


test('the supplier stops Phoenix preparation at the mission, before joining', supplier_preparation)


def supplier_katrine_refusal():
    from bots import arrav_supplier as supplier
    bot = supplier.ArravSupplier()
    bot._black_arm_proven = False
    spy_on(supplier, 'clear_boxes', impl=instant_ticks)
    def arrived(*args):
        return True
        yield
    def refused(*args):
        return False
        yield
    spy_on(supplier, 'goto_npc', impl=arrived)
    talks = spy_on(supplier, 'talk_strict', impl=refused)
    expect(run_wait(bot._ensure_katrine_task(lambda m: None))).to_be(False)
    expect(len(talks.calls)).to_be(1)


test('the supplier retries a failed mission dialogue before raiding the store', supplier_katrine_refusal)


def maze_upkeep():
    from rs2004.quests.defs.dragonslayer.maze import kill_for, npcs, ground_items, event_signal, sustain
    state = {'upkeep': 0, 'tick': 0, 'attacks': 0}
    def upkeep():
        state['upkeep'] += 1
        yield
    def attack(op):
        state['attacks'] += 1
        return True
    def tick(n=1):
        state['tick'] += n
        yield
    target = Fake(id=748, name='Giant rat', actions=lambda: ['Attack'], distance=lambda: 1,
                  targets_me=lambda: True, interact=attack, valid=lambda: state['upkeep'] < 10)
    spy_on(npcs, 'query', impl=querying(lambda: [target]))
    spy_on(ground_items, 'query', impl=querying(lambda: []))
    spy_on(inventory, 'items', returns=[])
    spy_on(execution, 'delay_until', impl=instant_until)
    spy_on(event_signal, 'pending', returns=False)
    spy_on(sustain, 'run', impl=upkeep)
    spy_on(execution, 'delay_ticks', impl=tick)
    spy_on(maze_game, 'tick', impl=lambda: state['tick'])
    spy_on(_core, 'step_time', returns=0)
    run_wait(kill_for(Fake(npc_id=748, key_id=1543, what='the giant rat'), lambda m: None))
    expect(state['upkeep']).to_be(10)
    expect(state['attacks']).to_be(2)


test('maze combat pumps upkeep and resumes attacks stopped by Melzar', maze_upkeep)


def maze_food():
    from rs2004.quests.defs.dragonslayer import decide
    from rs2004.geometry import Tile
    snap = QuestSnapshot(journal='in_progress', progress=Fake(stage=2, flags=set()),
        inv={'trout':3}, inv_ids={1542:1}, bank={'trout':20}, bank_ids={}, bank_known=True,
        tile=Tile(2941,3248,0), free_slots=20)
    step = decide(snap)
    expect(step.kind).to_be('withdraw')
    expect(step.items).to_equal([{'name':'Trout','qty':9}])
    snap.tile = Tile(2940,3248,0)
    snap.bank_known = False
    snap.bank = None
    snap.bank_ids = None
    expect(decide(snap).name).to_be("Melzar's Maze")


test('the maze takes banked food before entry and keeps fighting inside', maze_food)


def ship_supply_food():
    from rs2004.quests.defs.dragonslayer import decide
    from rs2004.geometry import Tile
    snap = QuestSnapshot(journal='in_progress', progress=Fake(stage=3,flags=set()),
        bank_known=True, bank={'trout':20}, free_slots=28, tile=Tile(3093,3243,0))
    expect(decide(snap).items).to_equal([{'name':'Trout','qty':3}])


test('a restart during ship supplies restores the travel food float', ship_supply_food)


def banked_captains_map():
    from rs2004.quests.defs.dragonslayer import decide
    from rs2004.geometry import Tile
    for stage in [3,7]:
        snap = QuestSnapshot(journal='in_progress', progress=Fake(stage=stage,flags=set()),
            bank_known=True, bank_ids={1538:1}, free_slots=28, tile=Tile(3101,3257,0))
        expect(decide(snap).items).to_equal([{'name':'Crandor map','qty':1,'id':1538}])


test('ship phases retrieve a banked assembled map before asking Ned to sail', banked_captains_map)


def bank_behind_neds_door():
    import rs2004.bank as banks
    from rs2004.geometry import Tile
    stand = Tile(3093,3243,0)
    spy_on(banks.game, 'tile', returns=Tile(3098,3257,0))
    spy_on(banks.bank, 'is_open', returns=False)
    spy_on(banks, '_real_booth', returns=Fake(distance=lambda: 10))
    spy_on(banks, 'nearest_bank', returns={'name':'Draynor','tile':stand})
    spy_on(banks, 'locked_bank_at', returns=None)
    def refused(*args):
        return False
        yield
    def arrived(*args, **kwargs):
        return True
        yield
    spy_on(banks.bank, 'open_nearest_access', impl=refused)
    walked = spy_on(banks.traversal, 'walk_resilient', impl=arrived)
    opened = spy_on(banks.bank, 'open_booth', impl=arrived)
    expect(run_wait(banks.banking.open(stand))).to_be(True)
    expect(len(walked.calls)).to_be(1)
    expect(len(opened.calls)).to_be(1)


test('a nearby bank blocked by Ned\'s door falls back to the world route', bank_behind_neds_door)


def recover_combat_gear():
    from rs2004.quests.defs.dragonslayer import combat_gear
    from rs2004.game import skills
    spy_on(skills, 'level', returns=40)
    snap = QuestSnapshot(attack=40, ranged=1, bank_known=True, bank_ids={1331:1, 1101:1})
    step = combat_gear(snap)
    expect(step.items).to_equal([{'name':'Adamant scimitar','qty':1,'id':1331}])
    snap.inv_ids = {1277:1}
    expect(combat_gear(snap).items).to_equal([{'name':'Adamant scimitar','qty':1,'id':1331}])
    snap.inv_ids = {1331:1}
    expect(combat_gear(snap).item).to_be('Adamant scimitar')
    snap.worn_ids = set([1331])
    expect(combat_gear(snap).items).to_equal([{'name':'Iron chainbody','qty':1,'id':1101}])
    expect(combat_gear(snap, False)).to_be(None)


test('a death recovers banked combat gear and never requests it inside the maze', recover_combat_gear)


def ore_room():
    from rs2004.quests.defs.dragonslayer import supplies
    from rs2004.quests.food import quest_food
    state = {'food': 12, 'deposits': 0}
    food = quest_food.name
    def opened(*args):
        return True
        yield
    def deposit(name):
        state['food'] -= 1
        state['deposits'] += 1
        return True
    spy_on(inventory, 'count', impl=lambda name: state['food'] if name == food else 0)
    spy_on(supplies, 'open_bank_leg', impl=opened)
    spy_on(supplies.bank, 'deposit', impl=deposit)
    spy_on(execution, 'delay_until', impl=instant_until)
    expect(run_wait(supplies.smith_nails(12, lambda m: None))).to_be(False)
    expect(state['food']).to_be(3)
    expect(state['deposits']).to_be(9)


test('nail production banks surplus maze food before loading eighteen ores', ore_room)


def noted_coal_is_not_ore():
    from rs2004.quests.defs.dragonslayer import supplies
    spy_on(inventory, 'items', returns=[Fake(id=453,name='Coal',count=1,noted=False),
                                       Fake(id=454,name='Coal',count=100,noted=True)])
    expect(supplies._material_count('Coal')).to_be(1)
    expect(run_wait(supplies.mine_for([], 'Coal', 2, None, lambda m: None))).to_be(False)


test('noted random-event coal does not satisfy the mining or smelting count', noted_coal_is_not_ore)


def bank_ore_notes():
    from rs2004.quests.defs.dragonslayer import supplies
    from rs2004.geometry import Tile
    spy_on(inventory, 'items', returns=[Fake(id=454,name='Coal',count=1,noted=True)])
    def opened(*args):
        return True
        yield
    selected = []
    def deposit(predicate):
        selected.append(predicate('Coal',454))
        selected.append(predicate('Coal',453))
        return True
        yield
    spy_on(supplies, 'open_bank_leg', impl=opened)
    spy_on(supplies.bank, 'deposit_all_matching', impl=deposit)
    expect(run_wait(supplies.smith_nails(12, lambda m: None))).to_be(False)
    expect(selected).to_equal([True,False])


test('ore preparation banks notes even when their names match required materials', bank_ore_notes)


def crandor_walk_upkeep():
    import rs2004.quests.defs.dragonslayer as dragon
    from rs2004.geometry import Tile
    state = {'upkeep': 0}
    def route(*args, **kwargs):
        yield 1
        yield 2
        return True
    def upkeep():
        state['upkeep'] += 1
        yield
    spy_on(dragon.traversal, 'walk_resilient', impl=route)
    spy_on(dragon.event_signal, 'pending', returns=False)
    spy_on(dragon.sustain, 'run', impl=upkeep)
    expect(run_wait(dragon.walk(Tile(2836,9600,0), lambda m: None))).to_be(True)
    expect(state['upkeep']).to_be(2)


test('Crandor walking sustains between route waits and preserves the route result', crandor_walk_upkeep)


def full_bone_batch():
    import rs2004.quests.defs.demonslayer as demon
    from rs2004.geometry import Tile
    spy_on(demon.game, 'tile', returns=Tile(3144,3231,0))
    spy_on(demon, 'held_id', impl=lambda id: id == demon.ROVIN_KEY_ID)
    spy_on(inventory, 'count', returns=25)
    spy_on(inventory, 'is_full', returns=False)
    def climbed(*args, **kwargs):
        return 'done'
        yield
    stairs = spy_on(demon.reach, 'loc_op', impl=climbed)
    expect(run_wait(demon.key_hunt(lambda m: None))).to_be(False)
    expect(len(stairs.calls)).to_be(1)


test('twenty-five bones go to Traiborn even with a spare pack slot', full_bone_batch)


def banked_traiborn_key():
    from rs2004.quests.defs.demonslayer import decide
    snap = QuestSnapshot(journal='in_progress', bank_known=True, bank_ids={2399:1}, inv_ids={2400:1})
    step = decide(snap)
    expect(step.kind).to_be('withdraw')
    expect(step.items).to_equal([{'name':'Key','id':2399,'qty':1}])


test('a parked Demon Slayer withdraws Traiborn\'s banked key before collecting more bones', banked_traiborn_key)


def tracked_mail_target():
    import rs2004.quests.defs.goblindiplomacy as goblins
    from rs2004.geometry import Tile
    state = {'combat':False, 'attacks':0}
    def attack(op):
        state['attacks'] += 1
        state['combat'] = True
        return True
    target = Fake(index=1, name='Goblin', health=1, max_health=1, in_combat=False,
        actions=lambda: ['Talk-to','Attack'], distance=lambda: 1, tile=lambda: goblins.GOBLIN_FARM,
        targets_me=lambda: state['combat'], targets_another_player=lambda: False,
        valid=lambda: True, interact=attack)
    spy_on(goblins.game, 'tile', returns=goblins.GOBLIN_FARM)
    spy_on(goblins.game, 'my_name', returns='tester')
    spy_on(goblins.game, 'in_combat', impl=lambda: state['combat'])
    spy_on(goblins.npcs, 'all', returns=[target])
    spy_on(goblins.npcs, 'query', impl=querying(lambda: [target]))
    spy_on(goblins.ground_items, 'query', impl=querying(lambda: []))
    spy_on(goblins.reachability, 'can_reach', impl=lambda *args, **kwargs: True)
    spy_on(goblins.sustain, 'run', impl=instant_ticks)
    spy_on(execution, 'delay_ticks', impl=instant_ticks)
    spy_on(_core, 'step_time', returns=100000)
    goblins.reset_goblin_mail_combat()
    run_wait(goblins._farm_goblin_mail_tick(lambda m: None))
    run_wait(goblins._farm_goblin_mail_tick(lambda m: None))
    expect(state['attacks']).to_be(1)
    expect(goblins.goblin_mail_target_index).to_be(1)
    expect(goblins.goblin_mail_target_engaged).to_be(True)
    goblins.reset_goblin_mail_combat()


test('mail farming retains its live target across generator steps', tracked_mail_target)


def mail_grace_attempt():
    import rs2004.quests.defs.goblindiplomacy as goblins
    state = {'calls':0, 'mail':0}
    def tick(log):
        state['calls'] += 1
        if state['calls'] == 2:
            state['mail'] = 1
        return False
        yield
    spy_on(goblins, '_farm_goblin_mail_tick', impl=tick)
    spy_on(inventory, 'count', impl=lambda name: state['mail'])
    spy_on(goblins.sustain, 'run', impl=instant_ticks)
    spy_on(execution.event_signal, 'pending', returns=False)
    spy_on(execution, 'delay_ticks', impl=instant_ticks)
    spy_on(_core, 'step_time', returns=0)
    expect(run_wait(goblins.farm_goblin_mail(lambda m: None))).to_be(True)
    expect(state['calls']).to_be(2)


test('mail gathering keeps grace waits inside one attempt until a drop lands', mail_grace_attempt)


def sustained_elvarg():
    import rs2004.quests.defs.dragonslayer as dragon
    state = {'upkeep':0, 'tick':0, 'attacks':0}
    def arrived(*args):
        return True
        yield
    def upkeep():
        state['upkeep'] += 1
        yield
    def attack(op):
        state['attacks'] += 1
        return True
    def tick(n=1):
        state['tick'] += n
        yield
    target = Fake(name='Elvarg', actions=lambda: ['Attack'], distance=lambda: 1,
        valid=lambda: state['upkeep'] < 10, interact=attack)
    spy_on(dragon, 'reach_elvarg', impl=arrived)
    spy_on(dragon.equipment, 'contains', returns=True)
    spy_on(dragon.npcs, 'query', impl=querying(lambda: [target]))
    spy_on(dragon.event_signal, 'pending', returns=False)
    spy_on(dragon.sustain, 'run', impl=upkeep)
    spy_on(dragon.game, 'tick', impl=lambda: state['tick'])
    spy_on(dragon.quests, 'status', impl=lambda name: 'complete' if state['upkeep'] >= 10 else 'in_progress')
    spy_on(execution, 'delay_ticks', impl=tick)
    spy_on(_core, 'step_time', returns=0)
    expect(run_wait(dragon.kill_elvarg(lambda m: None))).to_be(True)
    expect(state['upkeep']).to_be(10)
    expect(state['attacks']).to_be(2)


test('Elvarg combat sustains and resumes attacks without reopening the journal', sustained_elvarg)
