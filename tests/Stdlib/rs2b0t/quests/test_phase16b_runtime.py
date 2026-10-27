"""Exercise the live journal boundary and garlic source used by phase 16b."""
import _core
from rs2004 import execution
from rs2004.game import reader, game
from rs2004.tabs import quests
from rs2004.items import inventory
from rs2004.entities import locs, npcs
from rs2004.traversal import traversal
from rs2004.geometry import Tile
from rs2004.quests.defs import def_by_id
from rs2004.quests.exec.steps import run_maybe
from rs2004.quests.exec.garlic import take_garlic
from rs2004.quests.journal_text import normalize_journal

def normalize_loading():
    expect(normalize_journal(['Quest', 'Loading…'])).to_be('quest loading...')
    expect(normalize_journal('@dbl@Drink the @dre@potion@dbl@.|Next')).to_be('drink the potion . next')
    expect(normalize_journal('unclosed @dbl and @mail@')).to_be('unclosed @dbl and @mail@')
test('normalizes loading text, tags and punctuation before indexing Unicode', normalize_loading)

def journal_reader(id, text, expected):
    def run():
        journal_text = text
        state = {'modal': 123, 'closed': 0}
        spy_on(quests, 'status', returns='in_progress')
        def journal(name):
            return [journal_text]
            yield
        def close():
            state['modal'] = -1
            state['closed'] += 1
            return True
        spy_on(quests, 'journal', impl=journal)
        spy_on(reader, 'modals', impl=lambda: Fake(main=state['modal']))
        spy_on(_core, 'close_interfaces', impl=close)
        spy_on(execution, 'delay_ticks', impl=instant_ticks)
        spy_on(execution, 'delay_until', impl=instant_until)
        module = def_by_id(id)
        read = module.read_progress or module.read_stage
        result = run_wait(run_maybe(read()))
        expect(result.stage if module.read_progress else result).to_be(expected)
        expect(state['closed']).to_be(1)
    return run

for id, text, stage in [
    ['doric', 'I have spoken to Doric. I need to collect some items', 10],
    ['squire', 'The Squire suggests I speak to Reldo', 1],
    ['haunted', 'I discovered Ernest is a chicken', 2],
    ['hunt', 'I have spoken to Redbeard Frank. He has agreed to tell me. I need to go and buy some rum', 1],
    ['prince', 'I should go and speak to Osman', 10],
    ['vampire', 'I need to speak to Dr Harlow', 1],
]:
    test('reads and closes the journal for ' + id, journal_reader(id, text, stage))

def garlic_source():
    state = {'level': 0, 'open': False, 'garlic': 0, 'ops': []}
    spy_on(game, 'tile', impl=lambda: Tile(3100,3266,state['level']))
    spy_on(inventory, 'contains', impl=lambda name: state['garlic'] > 0)
    spy_on(inventory, 'count', impl=lambda name: state['garlic'])
    spy_on(execution, 'delay_until', impl=instant_until)
    spy_on(execution, 'delay_ticks', impl=instant_ticks)
    def walk(*args, **kwargs):
        return True
        yield
    spy_on(traversal, 'walk_resilient', impl=walk)
    def climb(op):
        state['ops'].append(op)
        state['level'] = 1
        return True
    def open_cupboard(op):
        state['ops'].append(op)
        state['open'] = True
        return True
    def search(op):
        state['ops'].append(op)
        state['garlic'] += 1
        return True
    stairs = Fake(id=1,name='Staircase',distance=lambda:1,actions=lambda:['Climb-up'],interact=climb)
    shut = Fake(id=2612,name='Cupboard',distance=lambda:1,actions=lambda:['Open'],interact=open_cupboard)
    opened = Fake(id=2613,name='Cupboard',distance=lambda:1,actions=lambda:['Search'],interact=search)
    spy_on(locs,'query',impl=querying(lambda:[stairs, opened if state['open'] else shut]))
    expect(run_wait(take_garlic(lambda m:None))).to_be(False)
    expect(run_wait(take_garlic(lambda m:None))).to_be(False)
    expect(run_wait(take_garlic(lambda m:None))).to_be(True)
    expect(run_wait(take_garlic(lambda m:None))).to_be(True)
    expect(state['ops']).to_equal(['Climb-up','Open','Search'])
test('climbs, opens, searches and resumes from held garlic', garlic_source)

def imp_idle_sweep():
    from rs2004.quests.defs import impcatcher as imp
    from rs2004.catalogs.record import Record
    walked = []
    spy_on(game, 'tile', returns=Tile(2632,3222,0))
    spy_on(execution, 'delay_until', impl=instant_until)
    spy_on(imp, 'imp_candidates', returns=[])
    spy_on(imp, 'scene_reachable', returns=True)
    def walk(tile, **kwargs):
        walked.append(tile)
        return True
        yield
    spy_on(traversal, 'walk_resilient', impl=walk)
    census = Record({'scene':0,'in_field':0,'free':0,'reachable':0,'nearest_refused':None})
    spy_on(npcs, 'query', impl=querying(lambda: []))
    expect(run_wait(imp.search_for_imps(census, lambda m: None))).to_be(True)
    expect(len(walked)).to_be(1)
test('an idle imp farmer sweeps with the module random source', imp_idle_sweep)

def blurite_interrupted_swing():
    from rs2004.catalogs.tasks import sustain
    from rs2004.quests.defs.knightssword import dungeon
    state = {'ore':0,'ticks':0,'mines':0,'sustain':0,'retaliate':[]}
    spy_on(game,'tile',returns=Tile(3049,9566,0))
    spy_on(game,'set_auto_retaliate',impl=lambda on: state['retaliate'].append(on))
    spy_on(inventory,'count_by_id',impl=lambda id: state['ore'])
    def rock_position(log):
        return Tile(3049,9566,0)
        yield
    spy_on(dungeon,'nearest_reachable_rock',impl=rock_position)
    def mine(op):
        state['mines'] += 1
        return True
    def tick(n):
        state['ticks'] += n
        if state['mines'] >= 2 and state['ticks'] >= 14:
            state['ore'] = 1
        yield
    def upkeep():
        state['sustain'] += 1
        yield
    spy_on(execution,'delay_ticks',impl=tick)
    spy_on(sustain,'run',impl=upkeep)
    rock = Fake(id=list(dungeon.BLURITE_IDS)[0],name='Rocks',distance=lambda:1,actions=lambda:['Mine'],interact=mine)
    spy_on(locs,'query',impl=querying(lambda:[rock]))
    expect(run_wait(dungeon.mine_blurite(lambda m:None))).to_be(True)
    expect(state['mines']).to_be(2)
    expect(state['sustain']).to_be_greater_than_or_equal(14)
    expect(state['retaliate']).to_equal([False,True])
test('blurite mining pumps sustain through an interrupted swing and retries', blurite_interrupted_swing)

def blurite_exception_cleanup():
    from rs2004.quests.defs.knightssword import dungeon
    changed = []
    spy_on(inventory,'count_by_id',returns=0)
    spy_on(game,'set_auto_retaliate',impl=lambda on: changed.append(on))
    def fail(log):
        raise ValueError('mine failed')
        yield
    spy_on(dungeon,'run',impl=fail)
    try:
        run_wait(dungeon.mine_blurite(lambda m:None))
        raise AssertionError('expected mine error')
    except ValueError:
        pass
    expect(changed).to_equal([False,True])
test('a mining exception restores auto-retaliate', blurite_exception_cleanup)

def lever_message_oracle():
    from rs2004.catalogs.tasks import sustain
    from rs2004.quests.defs.ernest import basement
    for letter in 'ABCDEF':
        expect(basement.PULLED('You pull lever ' + letter + ' down.')).to_be(True)
        expect(basement.PULLED_UP('You pull lever ' + letter + ' up.')).to_be(True)
        expect(basement.PULLED_UP('You pull lever ' + letter + ' down.')).to_be(False)
    expect(basement.PULLED('You hear a clunk.')).to_be(False)
    state = {'up':True,'messages':[],'pulls':0}
    def pull(op):
        state['up'] = not state['up']
        state['pulls'] += 1
        state['messages'].append('You pull lever B ' + ('up.' if state['up'] else 'down.'))
        state['messages'].append('You hear a clunk.')
        return True
    def walk(*args, **kwargs):
        return True
        yield
    lever = Fake(id=1,name='Lever B',distance=lambda:1,actions=lambda:['Pull'],interact=pull)
    spy_on(locs,'query',impl=querying(lambda:[lever]))
    spy_on(traversal,'walk_resilient',impl=walk)
    spy_on(sustain,'run',impl=instant_ticks)
    spy_on(execution,'delay_until',impl=instant_until)
    spy_on(execution,'delay_ticks',impl=instant_ticks)
    spy_on(_core,'message_mark',impl=lambda:len(state['messages']))
    spy_on(_core,'game_messages_since',impl=lambda mark:[(i+1,state['messages'][i]) for i in range(mark,len(state['messages']))])
    expect(run_wait(basement.set_lever('B','down',lambda m:None))).to_be(True)
    expect(state['pulls']).to_be(1)
    expect(run_wait(basement.set_lever('B','down',lambda m:None))).to_be(True)
    expect(state['pulls']).to_be(3)
    expect(state['up']).to_be(False)
test('lever pulls read server messages and force the requested state', lever_message_oracle)


def puzzle_door_crossing():
    from rs2004.quests.defs.ernest import basement
    move = basement.CHAIN[-1]
    state = {'tile': Tile(3102,9755,0), 'opens': 0}
    def walk(destination, **options):
        # An exact walk onto the door opens it as a navigation obstacle. Its teleport
        # then makes that exact tile unreachable; the puzzle must own this crossing.
        if options['radius'] == 0:
            state['tile'] = move.arrive
            return False
        state['tile'] = Tile(3101,9755,0)
        return True
        yield
    def open_door(op):
        state['opens'] += 1
        state['tile'] = move.arrive
        return True
    door = Fake(id=1,name='Door',distance=lambda:1,actions=lambda:['Open'],interact=open_door)
    spy_on(game,'tile',impl=lambda:state['tile'])
    spy_on(traversal,'walk_resilient',impl=walk)
    spy_on(locs,'query',impl=querying(lambda:[door]))
    spy_on(execution,'delay_until',impl=instant_until)
    spy_on(execution,'delay_ticks',impl=instant_ticks)
    expect(run_wait(basement.cross_door(move,lambda m:None))).to_be('crossed')
    expect(state['opens']).to_be(1)
    expect(basement.basement_region(state['tile'])).to_be('r9')

test('the oil room door is crossed explicitly from beside its blocked tile', puzzle_door_crossing)


def puzzle_retry_reset():
    from rs2004.catalogs.tasks import sustain
    from rs2004.quests.defs.ernest import basement
    visits = []
    def leave(log):
        visits.append('exit')
        return True
        yield
    def enter(log):
        visits.append('enter')
        return True
        yield
    def fail(*args):
        return False
        yield
    spy_on(inventory,'count_by_id',returns=0)
    spy_on(game,'tile',returns=Tile(3116,9754,0))
    spy_on(sustain,'run',impl=instant_ticks)
    spy_on(basement,'leave_basement',impl=leave)
    spy_on(basement,'enter_basement',impl=enter)
    spy_on(basement,'run_move',impl=fail)
    spy_on(basement,'unwind',impl=instant_ticks)
    expect(run_wait(basement.fetch_oil_can(lambda m:None))).to_be(False)
    expect(visits).to_equal(['exit','enter','exit','enter','exit','enter'])

test('each failed maze pass exits through the lever reset ladder even from entry', puzzle_retry_reset)


def absent_vyvin():
    from rs2004.quests.defs.knightssword import portrait
    spy_on(npcs,'query',impl=querying(lambda:[]))
    expect(portrait.vyvin_tile()).to_be(None)

test('a missing Sir Vyvin leaves the portrait approach free', absent_vyvin)


def goblin_disappears_after_attack():
    from rs2004.catalogs.tasks import sustain
    from rs2004.entities import ground_items
    from rs2004.quests.defs import goblindiplomacy as gd
    from rs2004.navigation import reachability
    gd.reset_goblin_mail_combat()
    state = {'gone':False}
    def attack(op):
        state['gone'] = True
        return True
    goblin = Fake(index=1,name='Goblin',in_combat=False,health=12,max_health=12,
                  actions=lambda:['Attack'],distance=lambda:1,tile=lambda:Tile(2958,3508,0),
                  targets_me=lambda:False,targets_another_player=lambda:False,valid=lambda:True,interact=attack)
    blocked = Fake(index=2,name='Goblin',in_combat=False,actions=lambda:['Attack'],distance=lambda:0,
                   tile=lambda:Tile(2957,3507,0),targets_me=lambda:False,targets_another_player=lambda:False,
                   interact=lambda op: False)
    spy_on(npcs,'query',impl=querying(lambda:[blocked,goblin]))
    spy_on(npcs,'all',impl=lambda:[] if state['gone'] else [blocked,goblin])
    spy_on(reachability,'can_reach',impl=lambda tile, **options:tile.x == 2958)
    spy_on(ground_items,'query',impl=querying(lambda:[]))
    spy_on(game,'tile',returns=Tile(2958,3507,0))
    spy_on(game,'my_name',returns='vanishing-target')
    spy_on(game,'in_combat',returns=False)
    spy_on(_core,'step_time',returns=10000)
    spy_on(sustain,'run',impl=instant_ticks)
    expect(run_wait(gd.farm_goblin_mail(lambda m:None))).to_be(False)
    expect(state['gone']).to_be(True)
    expect(gd.goblin_mail_target_index).to_be(None)

test('goblin farming skips a nearer blocked enemy and releases one disappearing after Attack', goblin_disappears_after_attack)


def wyson_leaves():
    from rs2004.quests.defs import goblindiplomacy as gd
    # Wyson's spawn in the 289 map, m47_52: local (19,51). The old anchor
    # (3013,3377) arrived outside his dialogue leash and retried without moving.
    wyson_tile = Tile(3027,3379,0)
    state = {'tile':Tile(3093,3243,0),'leaves':0}
    wyson = Fake(name='Wyson the gardener',distance=lambda:state['tile'].distance_to(wyson_tile))
    def walk(destination, **options):
        state['tile'] = destination
        return True
        yield
    def buy(npc, prefer, log):
        expect(state['tile'].distance_to(wyson_tile)).to_be_less_than(10)
        state['leaves'] = 2
        yield
    spy_on(game,'tile',impl=lambda:state['tile'])
    spy_on(npcs,'query',impl=querying(lambda:[wyson]))
    spy_on(traversal,'walk_resilient',impl=walk)
    spy_on(inventory,'contains',returns=False)
    spy_on(inventory,'count',impl=lambda name:state['leaves'] if name == 'Woad leaf' else 100)
    spy_on(gd,'talk_through',impl=buy)
    expect(run_wait(gd.make_blue_dye(lambda m:None))).to_be(False)
    expect(state['leaves']).to_be(2)

test('the blue dye leg reaches Wyson at his 289 spawn and buys both leaves', wyson_leaves)
