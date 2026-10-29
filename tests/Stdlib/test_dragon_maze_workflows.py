"""Maze doors consume the right key and the route resumes from observed position."""

import rs2004.quests.defs.dragonslayer.maze as maze
from rs2004.geometry import Tile
from helpers import FakeModule
from quest_world import QuestObject
from test_dragon_execution_workflows import DragonWorld


def test_maze_key_pickup_handles_missing_refused_far_and_late_drop():
    for mode in ['missing', 'walk_failed', 'refused', 'silent', 'taken']:
        with DragonWorld() as w:
            key = QuestObject(w, 'Key', 123, at=Tile(3005, 3000), effect=lambda: w.hold('Key', id=123))
            key.accept = mode != 'refused'
            w.scene = [] if mode == 'missing' else [key]
            w.can_walk = mode != 'walk_failed'
            w.respond = mode != 'silent'
            assert w.run(maze.take_key(123, w.logs.append)) == (mode == 'taken')


def test_maze_kill_tracks_missing_target_rejected_attack_interruption_and_dropped_key():
    leg = [l for l in maze.MAZE_LEGS if l.kind == 'kill'][0]
    for mode in ['held', 'missing', 'walk_failed', 'refused', 'event', 'dead', 'timeout']:
        with DragonWorld() as w:
            w.position = leg.at
            if mode == 'held':
                w.hold('Key', id=leg.key_id)
            npc = QuestObject(w, 'Rat', leg.npc_id, ['Attack'])
            npc.accept = mode != 'refused'
            w.scene = [QuestObject(w, 'Scenery')] if mode in ['missing', 'walk_failed'] else [npc]
            w.can_walk = mode != 'walk_failed'
            if mode == 'event':
                npc.effect = lambda: setattr(w, 'interrupted', True)
            elif mode == 'dead':
                key = QuestObject(w, 'Key', leg.key_id, effect=lambda: w.hold('Key', id=leg.key_id))
                def die():
                    npc.alive = False
                    w.scene = [key]
                npc.effect = die
            assert w.run(maze.kill_for(leg, w.logs.append)) == (mode in ['held', 'dead'])


def test_maze_coloured_doors_require_key_scene_and_acknowledged_consumption():
    leg = [l for l in maze.MAZE_LEGS if l.kind == 'door'][1]
    for mode in ['no_key', 'walk_failed', 'no_scene', 'no_door', 'refused', 'silent', 'crossed']:
        with DragonWorld() as w:
            w.position = leg.stand
            key = w.hold('Key', id=leg.key_id, effect=lambda: setattr(w, 'pack', []))
            key.accept = mode != 'refused'
            if mode == 'no_key':
                w.pack = []
            w.scene = [QuestObject(w, 'Door', at=leg.door)]
            if mode == 'no_scene':
                w.scene = []
            elif mode == 'no_door':
                w.scene = [QuestObject(w, 'Scenery')]
            w.can_walk = mode != 'walk_failed'
            w.respond = mode != 'silent'
            assert w.run(maze.open_door(leg, w.logs.append)) == (mode == 'crossed')


def test_maze_ladders_require_floor_change_and_chests_require_search_after_open():
    leg = [l for l in maze.MAZE_LEGS if l.kind == 'climb'][0]
    for mode in ['walk_failed', 'no_scene', 'missing', 'refused', 'silent', 'climbed']:
        with DragonWorld() as w:
            w.position = leg.stand
            ladder = w.seam('Ladder', leg.ladder, leg.op, leg.land)
            ladder.accept = mode != 'refused'
            if mode == 'no_scene':
                w.scene = []
            elif mode == 'missing':
                w.scene = [QuestObject(w, 'Scenery')]
            w.can_walk = mode != 'walk_failed'
            w.respond = mode != 'silent'
            assert w.run(maze.climb(leg, w.logs.append)) == (mode == 'climbed')
    for mode in ['refused_open', 'refused_search', 'silent', 'looted']:
        with DragonWorld() as w:
            chest = QuestObject(w, 'Chest', ops=['Open'])
            search = QuestObject(w, 'Chest', ops=['Search'], effect=lambda: w.hold('Map part', id=maze.DS_ID.MAP_MELZAR))
            search.accept = mode != 'refused_search'
            chest.effect = lambda: setattr(w, 'scene', [search])
            chest.accept = mode != 'refused_open'
            w.scene = [chest]
            w.respond = mode != 'silent'
            assert w.run(maze.loot_chest(maze.DS_ID.MAP_MELZAR, w.logs.append)) == (mode == 'looted')


def test_maze_exit_climbs_cellar_then_opens_one_way_and_front_doors():
    for start, at, name, op, dest in [
        (Tile(2935, 9656), Tile(2939, 9657), 'Ladder', 'Climb-up', Tile(2939, 3257)),
        (Tile(2939, 3257), Tile(2938, 3252), 'Door', 'Open', Tile(2937, 3252))]:
        for mode in ['walk_failed', 'no_scene', 'missing', 'refused', 'silent', 'left']:
            with DragonWorld() as w:
                w.position = start
                obj = w.seam(name, at, op, dest)
                obj.accept = mode != 'refused'
                if mode == 'no_scene':
                    w.scene = []
                elif mode == 'missing':
                    w.scene = [QuestObject(w, 'Scenery', at=at)]
                w.can_walk = mode != 'walk_failed'
                w.respond = mode != 'silent'
                assert w.run(maze.leave_maze(w.logs.append)) == (mode == 'left')
    front = maze.MAZE_LEGS[0]
    for mode in ['missing', 'refused', 'left']:
        with DragonWorld() as w:
            w.position = front.land
            key = w.hold('Maze key', id=maze.DS_ID.MAZE_KEY, effect=lambda: setattr(w, 'position', Tile(2942, 3248)))
            key.accept = mode != 'refused'
            w.scene = [QuestObject(w, 'Scenery' if mode == 'missing' else 'Door', at=front.door)]
            assert w.run(maze.leave_maze(w.logs.append)) == (mode == 'left')


def test_maze_runner_resumes_ladders_and_chest_and_recognises_finished_map():
    with DragonWorld() as w:
        runner = maze.MazeRun()
        w.position = None
        assert not w.run(runner.step(w.logs.append))
        assert maze.MazeRun.key_ids() == maze.KEY_IDS
        ladder_index = [i for i, l in enumerate(maze.MAZE_LEGS) if l.kind == 'climb'][0]
        leg = maze.MAZE_LEGS[ladder_index]
        w.position = leg.stand
        runner._index = ladder_index
        w.seam('Ladder', leg.ladder, leg.op, leg.land)
        assert w.run(runner.step(w.logs.append))
        runner._index = len(maze.MAZE_LEGS) - 1
        chest_leg = maze.MAZE_LEGS[-1]
        w.position = chest_leg.stand
        w.scene = [QuestObject(w, 'Chest', ops=['Search'],
                              effect=lambda: w.hold('Map part', id=maze.DS_ID.MAP_MELZAR))]
        assert w.run(runner.step(w.logs.append))
        assert w.run(runner.step(w.logs.append))
        assert w.run(maze.leave_maze(w.logs.append)) is False
        w.position = None
        assert w.run(maze.leave_maze(w.logs.append))
