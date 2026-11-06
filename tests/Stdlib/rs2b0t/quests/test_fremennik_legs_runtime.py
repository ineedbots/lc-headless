"""Fremennik trial runtime: bard, hunter, maze, reveller, seer and warrior."""

import _core
from rs2004.execution import event_signal
from rs2004.game import game, reader
from rs2004.geometry import Tile
from rs2004.quests.defs.fremenniktrials import bard, hunter, merchant, navigator, reveller, seer, supplies, warrior
from rs2004.quests.defs.fremenniktrials.areas import FT_ID, FT_LOC, FT_TILE, MAZE_ROUTE
from rs2004.quests.engine.types import QuestProgress, QuestSnapshot
from rs2004.tabs import prayer


def answer(value):
    def wait(*args, **kwargs):
        return value
        yield
    return wait


def trial_restarts():
    scene = world()
    snap = QuestSnapshot(inv_ids={}, progress=QuestProgress(1, set()))
    spy_on(hunter, 'combat_kit', returns=None)
    expect(hunter.hunter_step(snap).kind).to_be('talk')
    snap.progress.flags.add('hunter-started')
    snap.inv_ids[FT_ID.TALISMAN] = 1
    expect(hunter.hunter_step(snap).run).to_be(hunter.hunt)
    snap.inv_ids[FT_ID.TALISMAN_CHARGED] = 1
    expect(hunter.hunter_step(snap).kind).to_be('talk')
    expect(warrior.warrior_step(snap).kind).to_be('talk')
    snap.progress.flags.add('warrior-started')
    snap.tile = FT_TILE.MAZE_ENTRY
    snap.inv = {}
    snap.worn = set()
    spy_on(warrior, 'in_battleground', returns=True)
    expect(warrior.warrior_step(snap).run).to_be(warrior.fight_koschei)
    expect(navigator.navigator_step(snap).kind).to_be('talk')
    snap.progress.flags.add('navigator-started')
    expect(navigator.navigator_step(snap).run).to_be(navigator.run_maze)
    expect(merchant.merchant_step(snap).kind).to_be('talk')
    walk = spy_on(merchant, 'walk_to', impl=answer(False))
    talk = spy_on(merchant, 'talk_through', impl=answer(False))
    expect(run_wait(merchant.open_chain(scene.log))).to_be(False)
    walk.mock_implementation(answer(True))
    expect(run_wait(merchant.open_chain(scene.log))).to_be(False)
    talk.mock_implementation(answer(True))
    expect(run_wait(merchant.open_chain(scene.log))).to_be(True)
    snap.progress.flags.add('warrior-done')
    expect(warrior.warrior_step(snap)).to_be_null()
    scene.at = FT_TILE.MAZE_ENTRY
    spy_on(navigator, 'in_maze', returns=True)
    from rs2004.reach import reach

    def portal(name, op, at, goal, **kwargs):
        expect(goal()).to_be(False)
        return 'unreachable'
        yield

    spy_on(reach, 'loc_op', impl=portal)
    expect(run_wait(navigator.run_maze(scene.log))).to_be(False)


test('Fremennik trial restarts route charged talismans and unfinished maze, combat and trading errands', trial_restarts)


def give(scene, id):
    def effect(*args):
        scene.item(id, 'Quest item')
    return effect


def world():
    scene = Scene(FT_TILE.LONGHALL)
    for module in [bard, navigator, reveller, seer, supplies, warrior]:
        spy_on(module, 'walk_to', impl=scene._walk)
    spy_on(event_signal, 'pending', returns=False)
    return scene


def bard_errands():
    scene = world()
    bard.reset_bard_latch()
    scene.walk_ok = False
    expect(run_wait(bard.ask_lalli(scene.log))).to_be(False)
    scene.walk_ok = True
    talk = spy_on(bard, 'talk_through', impl=answer(False))
    expect(run_wait(bard.ask_lalli(scene.log))).to_be(False)
    talk.mock_implementation(answer(True))
    expect(run_wait(bard.ask_lalli(scene.log))).to_be(True)
    expect(bard.lalli_asked).to_be(True)
    until = spy_on(bard, 'talk_until', impl=answer(False))
    expect(run_wait(bard.take_pet_rock(scene.log))).to_be(False)
    expect(bard.lalli_asked).to_be(False)
    until.mock_implementation(answer(True))
    expect(run_wait(bard.take_pet_rock(scene.log))).to_be(True)
    use = spy_on(bard, 'use_on_loc', impl=answer(False))
    scene.item(FT_ID.PET_ROCK, 'Rock')
    expect(run_wait(bard.stone_soup(scene.log))).to_be(False)
    use.mock_implementation(answer(True))
    expect(run_wait(bard.stone_soup(scene.log))).to_be(True)
    expect(run_wait(bard.offer_shark(scene.log))).to_be(True)
    scene.walk_ok = False
    expect(run_wait(bard.spin_fleece(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(bard.spin_fleece(scene.log))).to_be(False)
    scene.loc('Spinning wheel')
    scene.item(FT_ID.GOLDEN_FLEECE, 'Fleece', on_use=lambda target: False)
    expect(run_wait(bard.spin_fleece(scene.log))).to_be(False)
    scene.take(FT_ID.GOLDEN_FLEECE)
    scene.item(FT_ID.GOLDEN_FLEECE, 'Fleece', on_use=give(scene, FT_ID.GOLDEN_WOOL))
    expect(run_wait(bard.spin_fleece(scene.log))).to_be(True)


test('the bard asks Lalli, takes a pet rock, makes stone soup and spins the golden fleece', bard_errands)


def performance():
    scene = world()
    backstage = spy_on(bard, 'past_backstage', returns=False)
    stage = spy_on(bard, 'on_stage', returns=False)
    scene.loc_op_status = 'unreachable'
    expect(run_wait(bard.perform(scene.log))).to_be(False)
    scene.loc_op_status = 'done'
    scene.walk_ok = False
    expect(run_wait(bard.perform(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(bard.perform(scene.log))).to_be(False)
    scene.item(FT_ID.ENCHANTED_LYRE, 'Lyre', effect=lambda op: False)
    expect(run_wait(bard.perform(scene.log))).to_be(False)
    scene.pack = []
    scene.item(FT_ID.ENCHANTED_LYRE, 'Lyre', effect=lambda op: scene.say(bard.TRIAL_WON))
    expect(run_wait(bard.perform(scene.log))).to_be(True)


test('the bard performance waits for the final verse vote rather than the initial Play click', performance)


def hunt():
    scene = world()
    expect(run_wait(hunter.locate())).to_be('lost')
    scene.item(FT_ID.TALISMAN, 'Talisman', effect=lambda op: False)
    expect(run_wait(hunter.locate())).to_be('lost')
    scene.pack = []
    scene.item(FT_ID.TALISMAN, 'Talisman')
    expect(run_wait(hunter.locate())).to_be('lost')
    scene.pack = []
    scene.item(FT_ID.TALISMAN, 'Talisman', effect=lambda op: scene.say(hunter.GUIDE + 'north-east'))
    expect(run_wait(hunter.locate())).to_be('north-east')
    scene.pack = []
    scene.item(FT_ID.TALISMAN, 'Talisman', effect=lambda op: scene.say(hunter.HERE))
    expect(run_wait(hunter.locate())).to_be('here')
    fight = spy_on(hunter, 'fight', impl=answer(False))
    expect(run_wait(hunter.hunt(scene.log))).to_be(False)
    fight.mock_implementation(answer(True))
    expect(run_wait(hunter.hunt(scene.log))).to_be(True)
    locate = spy_on(hunter, 'locate', impl=answer('north'))
    scene.at = None
    expect(run_wait(hunter.hunt(scene.log))).to_be(False)
    scene.at = Tile(2700, 3600, 0)
    scene.walk_ok = False
    expect(run_wait(hunter.hunt(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(hunter.hunt(scene.log))).to_be(False)
    scene.item(FT_ID.TALISMAN_CHARGED, 'Charged talisman')
    expect(run_wait(hunter.hunt(scene.log))).to_be(True)


test('the talisman reads bearings, reopens a drifting search box and fights the surfaced Draugen', hunt)


def maze():
    scene = world()
    inside = spy_on(navigator, 'in_maze', returns=False)
    scene.loc_op_status = 'unreachable'
    expect(run_wait(navigator.run_maze(scene.log))).to_be(False)
    scene.loc_op_status = 'done'
    expect(run_wait(navigator.run_maze(scene.log))).to_be(False)
    scene.loc('Escape rope', ['Climb-up'], effect=lambda op: False)
    expect(run_wait(navigator.escape(scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Escape rope', ['Climb-up'])
    expect(run_wait(navigator.escape(scene.log))).to_be(True)
    scene.at = FT_TILE.MAZE_ENTRY
    scene.loc_op_status = 'unreachable'
    expect(run_wait(navigator.run_maze(scene.log))).to_be(False)
    scene.loc_op_status = 'done'
    expect(run_wait(navigator.run_maze(scene.log))).to_be(False)

    def cross(name, op):
        if name == 'Portal':
            leg = navigator.leg_at()
            scene.at = MAZE_ROUTE[leg].land

    scene.loc_op_effect = cross
    scene.walk_ok = False
    expect(run_wait(navigator.run_maze(scene.log))).to_be(False)
    scene.at = FT_TILE.MAZE_ENTRY
    scene.walk_ok = True
    expect(run_wait(navigator.run_maze(scene.log))).to_be(True)
    expect(scene.logged('through portal 7')).to_be(True)


test('Swensen maze resumes each portal landing and escapes a scattered room', maze)


def keg_swap():
    scene = world()
    inside = spy_on(reveller, 'in_longhall', returns=False)
    scene.item(FT_ID.FIRECRACKER, 'Strange object')
    scene.walk_ok = False
    expect(run_wait(reveller.swap_keg(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(reveller.swap_keg(scene.log))).to_be(False)
    scene.item(1, 'Tinderbox', on_use=lambda target: False)
    expect(run_wait(reveller.swap_keg(scene.log))).to_be(False)
    scene.take(1)
    scene.item(1, 'Tinderbox')
    expect(run_wait(reveller.swap_keg(scene.log))).to_be(False)
    scene.item(FT_ID.FIRECRACKER_LIT, 'Lit object')
    scene.loc_op_status = 'unreachable'
    expect(run_wait(reveller.swap_keg(scene.log))).to_be(False)
    scene.loc_op_status = 'done'
    scene.loc_op_effect = lambda *args: scene.take(FT_ID.FIRECRACKER_LIT)
    expect(run_wait(reveller.swap_keg(scene.log))).to_be(False)
    inside.mock_return_value(True)
    scene.pack = []
    expect(run_wait(reveller.swap_keg(scene.log))).to_be(False)
    scene.item(FT_ID.LOW_ALCOHOL_KEG, 'Low alcohol keg')
    scene.item(FT_ID.BEER_KEG, 'Keg', on_use=lambda target: False)
    expect(run_wait(reveller.swap_keg(scene.log))).to_be(False)
    scene.take(FT_ID.BEER_KEG)
    scene.item(FT_ID.BEER_KEG, 'Keg')
    expect(run_wait(reveller.swap_keg(scene.log))).to_be(False)
    scene.take(FT_ID.BEER_KEG)
    scene.item(FT_ID.BEER_KEG, 'Keg', on_use=lambda target: scene.take(FT_ID.LOW_ALCOHOL_KEG))
    expect(run_wait(reveller.swap_keg(scene.log))).to_be(True)
    until = spy_on(reveller, 'talk_until', impl=answer(True))
    for fn in [reveller.buy_low_alcohol_keg, reveller.buy_beer, reveller.drinking_contest]:
        expect(run_wait(fn(scene.log))).to_be(True)
    expect(len(until.calls)).to_be(3)


test('the reveller lights and places the firecracker then swaps kegs inside the longhall', keg_swap)


def seer_containers_and_exit():
    scene = world()
    expect(run_wait(seer.open_container(1, 2, scene.at, scene.log))).to_be_null()
    scene.loc('Container', ['Open'], id=1, effect=lambda op: scene.loc('Open', id=2))
    run_wait(seer.open_container(1, 2, scene.at, scene.log))
    run_wait(seer.open_container(1, 2, scene.at, scene.log))
    expect(run_wait(seer.search_chest().run(scene.log))).to_be(True)
    expect(run_wait(seer.open_cupboard().run(scene.log))).to_be(True)
    expect(run_wait(seer.climb_west(scene.log))).to_be(True)
    expect(run_wait(seer.climb_east(scene.log))).to_be(True)
    scene.walk_ok = False
    expect(run_wait(seer.go_down_east(scene.log))).to_be(False)
    expect(run_wait(seer.unlock_exit(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(seer.go_down_east(scene.log))).to_be(False)
    expect(run_wait(seer.unlock_exit(scene.log))).to_be(False)
    scene.loc('Door', id=FT_LOC.SEER_DOOR2)
    scene.item(FT_ID.SEERS_KEY, 'Key', on_use=lambda target: False)
    expect(run_wait(seer.unlock_exit(scene.log))).to_be(False)
    scene.take(FT_ID.SEERS_KEY)
    scene.item(FT_ID.SEERS_KEY, 'Key', on_use=lambda target: scene.take(FT_ID.SEERS_KEY))
    expect(run_wait(seer.unlock_exit(scene.log))).to_be(True)
    scene.loc('Trapdoor', ['Open'], id=FT_LOC.TRAPDOOR_SHUT, effect=lambda op: False)
    expect(run_wait(seer.go_down_east(scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Trapdoor', ['Open'], id=FT_LOC.TRAPDOOR_SHUT)
    expect(run_wait(seer.go_down_east(scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Trapdoor', ['Climb-down'], id=FT_LOC.TRAPDOOR_OPEN, effect=lambda op: False)
    expect(run_wait(seer.go_down_east(scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Trapdoor', ['Climb-down'], id=FT_LOC.TRAPDOOR_OPEN,
              effect=lambda op: setattr(scene, 'at', FT_TILE.MURAL_STAND))
    expect(run_wait(seer.go_down_east(scene.log))).to_be(True)
    spy_on(seer, 'use_on_loc', impl=answer(True))
    expect(run_wait(seer.press_disk(scene.log))).to_be(True)


test('Peer containers transform before searching and the key unlocks the far exit', seer_containers_and_exit)


def dials():
    scene = world()
    scene.letter = 'A'
    spy_on(reader, 'component_text', impl=lambda id: scene.letter)
    click = spy_on(_core, 'click_component', returns=False)
    expect(run_wait(seer.set_dial(0, 'A', scene.log))).to_be(True)
    scene.letter = ''
    expect(run_wait(seer.set_dial(0, 'B', scene.log))).to_be(False)
    scene.letter = 'A'
    expect(run_wait(seer.set_dial(0, 'B', scene.log))).to_be(False)
    click.mock_return_value(True)
    expect(run_wait(seer.set_dial(0, 'B', scene.log))).to_be(False)

    def dial(id):
        scene.letter = 'Z'
        return True

    click.mock_implementation(dial)
    expect(run_wait(seer.set_dial(0, 'Z', scene.log))).to_be(True)
    expect(click.calls[-1]).to_equal((seer.COMBO.DOWN[0],))
    scene.chat.pages = [['Unknown']]
    expect(run_wait(seer.read_riddle(scene.log))).to_be_null()
    scene.chat.pages = []
    expect(run_wait(seer.read_riddle(scene.log))).to_be_null()
    scene.chat.shown = ['my first is in mage, but not in wizard']
    scene.chat.pages = ['continue', ['Read the riddle']]
    scene.later(lambda: setattr(scene, 'main_modal', seer.COMBO.ROOT))
    expect(run_wait(seer.read_riddle(scene.log))).to_contain('mage')


test('Peer dials choose the shortest direction and the riddle reader rejects unknown menus', dials)


def riddle_door():
    scene = world()
    west = spy_on(seer, 'in_seer_west', returns=False)
    scene.walk_ok = False
    expect(run_wait(seer.solve_riddle_and_enter(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(seer.solve_riddle_and_enter(scene.log))).to_be(False)
    scene.loc('Door', ['Open'], id=FT_LOC.SEER_DOOR1, effect=lambda op: False)
    expect(run_wait(seer.solve_riddle_and_enter(scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Door', ['Open'], id=FT_LOC.SEER_DOOR1)
    riddle = spy_on(seer, 'read_riddle', impl=answer(None))
    expect(run_wait(seer.solve_riddle_and_enter(scene.log))).to_be(False)
    riddle.mock_implementation(answer('unknown plaque'))
    expect(run_wait(seer.solve_riddle_and_enter(scene.log))).to_be(False)
    riddle.mock_implementation(answer('my first is in mage, but not in wizard'))
    dial = spy_on(seer, 'set_dial', impl=answer(False))
    expect(run_wait(seer.solve_riddle_and_enter(scene.log))).to_be(False)
    dial.mock_implementation(answer(True))
    click = spy_on(_core, 'click_component', returns=False)
    expect(run_wait(seer.solve_riddle_and_enter(scene.log))).to_be(False)
    click.mock_return_value(True)
    expect(run_wait(seer.solve_riddle_and_enter(scene.log))).to_be(False)

    def entered(id):
        scene.say('You solved the riddle')
        west.mock_return_value(True)
        return True

    click.mock_implementation(entered)
    expect(run_wait(seer.solve_riddle_and_enter(scene.log))).to_be(True)
    expect(run_wait(seer.solve_riddle_and_enter(scene.log))).to_be(True)


test('Peer door reads the plaque, dials all four letters and confirms the accepted answer', riddle_door)


def koschei():
    scene = world()
    spy_on(game, 'set_auto_retaliate', returns=None)
    spy_on(prayer, 'points', returns=0)
    scene.loc_op_status = 'unreachable'
    expect(run_wait(warrior.enter_battleground(scene.log))).to_be(False)
    scene.loc_op_status = 'done'
    expect(run_wait(warrior.enter_battleground(scene.log))).to_be(True)
    expect(run_wait(warrior.fight_koschei(scene.log))).to_be(False)
    scene.at = FT_TILE.WARRIOR_LOFT
    expect(run_wait(warrior.fight_koschei(scene.log))).to_be(True)
    inside = spy_on(warrior, 'in_battleground', returns=True)
    pending = spy_on(event_signal, 'pending', returns=True)
    expect(run_wait(warrior.fight_koschei(scene.log))).to_be(False)
    pending.mock_return_value(False)
    spy_on(warrior, 'attackable', returns=None)
    expect(run_wait(warrior.fight_koschei(scene.log))).to_be(False)
    target = scene.npc(warrior.KOSCHEI, ['Attack'], effect=lambda op: inside.mock_return_value(False))
    spy_on(warrior, 'attackable', returns=target)
    expect(run_wait(warrior.fight_koschei(scene.log))).to_be(True)
    scene.walk_ok = False
    expect(run_wait(warrior.leave_loft(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(warrior.leave_loft(scene.log))).to_be(True)


test('Koschei distinguishes the honourable loft landing from a real death and yields to events', koschei)
