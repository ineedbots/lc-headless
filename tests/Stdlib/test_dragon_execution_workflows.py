"""Dragon Slayer's map, ship and island seams require acknowledged transitions."""

import rs2004.quests.defs.dragonslayer as ds
import rs2004.quests.defs.dragonslayer.maze as maze
from rs2004.geometry import Tile
from helpers import FakeModule
from quest_world import QuestWorld, QuestObject


class DragonWorld(QuestWorld):
    def __init__(self):
        QuestWorld.__init__(self)
        self.completed = False
        self.wearing_shield = True

    def __enter__(self):
        QuestWorld.__enter__(self)
        self.install(ds)
        self.install(maze)
        for module in [ds, maze]:
            self.patch(module, '_core', self)
            self.patch(module, 'sustain', FakeModule(run=self.upkeep))
            self.patch(module, 'game', FakeModule(tile=lambda: self.position, tick=self.tick))
        self.patch(ds, 'equipment', FakeModule(contains=lambda n: self.wearing_shield,
                                               equip=lambda n: self.reply(True)))
        self.patch(ds, 'quests', FakeModule(status=lambda n: 'complete' if self.completed else 'in_progress'))
        return self

    def upkeep(self):
        if False:
            yield

    def seam(self, name, at, op, land):
        def arrive():
            self.position = land
            self.scene.append(QuestObject(self, 'Scenery', at=land))
        obj = QuestObject(self, name, ops=[op], at=at, effect=arrive)
        self.scene = [obj]
        return obj


def test_oziach_conversation_requires_all_four_answers_and_handles_refusal():
    for mode in ['unreachable', 'no_dialogue', 'event', 'unmatched', 'answered']:
        with DragonWorld() as w:
            w.patch(ds, 'goto_npc', lambda *a: w.reply(mode != 'unreachable'))
            w.patch(ds, 'open_dialogue', lambda *a: w.reply(mode != 'no_dialogue'))
            if mode == 'answered':
                w.pages = []
                for goal in ds.OZIACH_GOALS:
                    w.pages += [('options', [goal.ask, 'Leave']), ('continue', [goal.heard])]
                w.pages += [('options', [ds.FAREWELL])]
            elif mode == 'unmatched':
                w.pages = [('options', ['Fight me'])]
            w.interrupted = mode == 'event'
            assert w.run(ds.talk_oziach(w.logs.append)) == (mode == 'answered')
            if mode == 'answered':
                assert len([line for line in w.logs if 'Oziach answered' in line]) == 4


def test_wormbrain_map_requires_cash_arrival_dialogue_and_piece():
    for mode in ['held', 'no_cash', 'walk_failed', 'refused', 'silent', 'bought']:
        with DragonWorld() as w:
            w.hold('Coins', 0 if mode == 'no_cash' else ds.WORMBRAIN_PRICE)
            if mode == 'held':
                w.hold('Map part', id=ds.DS_ID.MAP_WORMBRAIN)
            w.can_walk = mode != 'walk_failed'
            got = lambda: w.hold('Map part', id=ds.DS_ID.MAP_WORMBRAIN)
            w.patch(ds, 'talk_through', lambda *a: w.reply(mode != 'refused', got if mode == 'bought' else None))
            assert w.run(ds.buy_map_from_wormbrain(w.logs.append)) == (mode in ['held', 'bought'])


def test_oracle_magic_door_checks_scene_arrival_action_and_correct_side():
    for mode in ['no_scene', 'walk_failed', 'missing', 'refused', 'silent', 'crossed']:
        for east in [True, False]:
            with DragonWorld() as w:
                w.position = ds.DS_LOC.ORACLE_DOOR_STAND if east else Tile(3053, 9840)
                dest = Tile(3052, 9840) if east else Tile(3050, 9840)
                leaf = w.seam('Door', ds.DS_LOC.ORACLE_DOOR, 'Open', dest)
                leaf.accept = mode != 'refused'
                w.can_walk = mode != 'walk_failed'
                w.respond = mode != 'silent'
                if mode == 'no_scene':
                    w.scene = []
                elif mode == 'missing':
                    w.scene = [QuestObject(w, 'Scenery', at=ds.DS_LOC.ORACLE_DOOR)]
                assert w.run(ds.open_oracle_magic_door(w.logs.append, east)) == (mode == 'crossed')


def test_oracle_map_loots_chest_and_leaves_the_sealed_room():
    with DragonWorld() as w:
        w.position = Tile(3053, 9840)
        w.patch(ds, 'open_oracle_magic_door', lambda log, east: w.reply(True))
        w.scene = [QuestObject(w, 'Chest', ops=['Search'], at=ds.DS_LOC.ORACLE_CHEST_STAND,
                              effect=lambda: w.hold('Map part', id=ds.DS_ID.MAP_ORACLE))]
        assert w.run(ds.oracle_chest(w.logs.append))
        assert w.count_by_id(ds.DS_ID.MAP_ORACLE) == 1
        assert w.run(ds.oracle_chest(w.logs.append))
        w.position = Tile(3000, 3000)
        assert w.run(ds.oracle_chest(w.logs.append))
        w.pack = []
        assert w.run(ds.oracle_chest(w.logs.append))
        w.can_walk = False
        assert not w.run(ds.oracle_chest(w.logs.append))


def test_map_combination_requires_both_pieces_and_inventory_result():
    for mode in ['missing', 'refused', 'silent', 'combined']:
        with DragonWorld() as w:
            first = w.hold('Map part', id=ds.DS_ID.MAP_MELZAR, effect=lambda: w.hold('Crandor map', id=ds.DS_ID.MAP))
            first.accept = mode != 'refused'
            if mode != 'missing':
                w.hold('Map part', id=ds.DS_ID.MAP_WORMBRAIN)
            w.respond = mode != 'silent'
            assert w.run(ds.combine_map(w.logs.append)) == (mode == 'combined')


def test_ship_boarding_crosses_gangplank_then_climbs_into_hold():
    with DragonWorld() as w:
        deck = Tile(3048, 3208, 1)
        hold = Tile(3048, 9640)
        ladder = QuestObject(w, 'Ladder', ops=['Climb-down'], at=deck, effect=lambda: setattr(w, 'position', hold))
        plank = QuestObject(w, 'Gangplank', ops=['Cross'], at=ds.DS_LOC.GANGPLANK_STAND)
        def board():
            w.position = deck
            w.scene = [ladder]
        plank.effect = board
        w.scene = [plank]
        assert w.run(ds.go_below_decks(w.logs.append)) and w.position == hold
        assert w.run(ds.go_below_decks(w.logs.append))
        assert w.run(ds.board_for_crandor(w.logs.append))
        w.position = Tile(3048, 3208, 3)
        assert w.run(ds.board_for_crandor(w.logs.append))


def test_ship_boarding_rejects_missing_seams_failed_walks_and_unanswered_clicks():
    for deck in [True, False]:
        for mode in ['walk_failed', 'missing', 'refused', 'silent']:
            with DragonWorld() as w:
                w.position = Tile(3048, 3208, 1) if deck else ds.DS_LOC.GANGPLANK_STAND
                obj = w.seam('Ladder' if deck else 'Gangplank', w.position,
                             'Climb-down' if deck else 'Cross', Tile(3048, 9640) if deck else Tile(3048, 3208, 1))
                obj.accept = mode != 'refused'
                w.respond = mode != 'silent'
                w.can_walk = mode != 'walk_failed'
                if mode == 'missing':
                    w.scene = [QuestObject(w, 'Scenery')]
                if not deck or mode != 'walk_failed':
                    assert not w.run(ds.go_below_decks(w.logs.append))
                if not deck:
                    assert not w.run(ds.go_below_decks(w.logs.append, True))


def test_ship_repair_requires_a_hole_a_plank_and_consumption():
    for mode in ['not_aboard', 'no_hole', 'no_plank', 'refused', 'silent', 'repaired']:
        with DragonWorld() as w:
            w.position = Tile(3048, 9640)
            if mode == 'not_aboard':
                w.position = Tile(3000, 3000)
                w.can_walk = False
            if mode != 'no_plank':
                plank = w.hold('Plank', id=ds.DS_ID.PLANK, effect=lambda: setattr(w, 'pack', []))
                plank.accept = mode != 'refused'
            w.scene = [QuestObject(w, 'Scenery' if mode == 'no_hole' else 'Hole')]
            w.respond = mode != 'silent'
            assert w.run(ds.repair_ship(w.logs.append)) == (mode == 'repaired')


def test_ship_exit_climbs_from_hold_and_crosses_from_deck():
    for start, name, op, dest in [(Tile(3048, 9640), 'Ladder', 'Climb-up', Tile(3048, 3208, 1)),
                                  (Tile(3048, 3208, 1), 'Gangplank', 'Cross', Tile(3044, 3200))]:
        for mode in ['missing', 'refused', 'silent', 'left']:
            with DragonWorld() as w:
                w.position = start
                obj = w.seam(name, start, op, dest)
                obj.accept = mode != 'refused'
                w.respond = mode != 'silent'
                if mode == 'missing':
                    w.scene = []
                assert w.run(ds.leave_ship(w.logs.append)) == (mode == 'left')
    with DragonWorld() as w:
        assert w.run(ds.leave_ship(w.logs.append))


def test_crandor_entry_and_exit_use_the_surface_rock_lair_gate_and_secret_wall():
    cases = [(ds.descend_crandor, ds.DS_LOC.CRANDOR_ROCK, 'Rock opening', 'Climb-down', Tile(2839, 9635)),
             (ds.reach_elvarg, ds.DS_LOC.ELVARG_GATE_STAND, 'Gate', 'Open', Tile(2855, 9635)),
             (ds.leave_crandor, ds.DS_LOC.ELVARG_GATE_INSIDE, 'Gate', 'Open', ds.DS_LOC.ELVARG_GATE_STAND),
             (ds.cross_secret_wall, ds.DS_LOC.SECRET_WALL_KARAMJA_STAND, 'Wall', 'Open', Tile(2835, 9602))]
    for run, stand, name, op, dest in cases:
        for mode in ['walk_failed', 'missing', 'refused', 'silent', 'crossed']:
            with DragonWorld() as w:
                w.position = stand
                at = ds.DS_LOC.CRANDOR_SECRET_DOOR if name == 'Wall' else stand
                obj = w.seam(name, at, op, dest)
                obj.accept = mode != 'refused'
                w.can_walk = mode != 'walk_failed'
                w.respond = mode != 'silent'
                if mode == 'missing':
                    w.scene = [QuestObject(w, 'Scenery')]
                assert w.run(run(w.logs.append)) == (mode == 'crossed'), (run, mode, w.logs)


def test_crandor_shortcut_is_opened_before_fighting_and_reentry_is_proven():
    with DragonWorld() as w:
        w.patch(ds, 'shortcut_opened', False)
        w.position = ds.DS_LOC.CRANDOR_SECRET_DOOR
        wall = w.seam('Wall', ds.DS_LOC.CRANDOR_SECRET_DOOR, 'Open', ds.DS_LOC.SECRET_WALL_KARAMJA_STAND)
        assert not w.run(ds.unlock_shortcut(w.logs.append))
        wall.effect = lambda: setattr(w, 'position', Tile(2835, 9602))
        assert w.run(ds.unlock_shortcut(w.logs.append)) and ds.shortcut_opened


def test_elvarg_requires_shield_and_tracks_event_death_and_quest_completion():
    for mode in ['no_shield', 'equip', 'unreachable', 'missing', 'refused', 'event', 'despawn', 'dead', 'timeout']:
        with DragonWorld() as w:
            w.position = Tile(2855, 9635)
            w.wearing_shield = mode not in ['no_shield', 'equip']
            if mode == 'equip':
                w.hold(ds.DS_ITEM.SHIELD)
            w.patch(ds, 'reach_elvarg', lambda *a: w.reply(mode != 'unreachable'))
            npc = QuestObject(w, 'Elvarg', ops=['Attack'])
            npc.accept = mode != 'refused'
            w.scene = [] if mode == 'missing' else [npc]
            if mode == 'event':
                npc.effect = lambda: setattr(w, 'interrupted', True)
            elif mode == 'dead':
                npc.effect = lambda: setattr(w, 'completed', True)
            elif mode == 'despawn':
                npc.effect = lambda: setattr(npc, 'alive', False)
            assert w.run(ds.kill_elvarg(w.logs.append)) == (mode == 'dead')


def test_crandor_surface_and_wall_exits_and_missing_position():
    with DragonWorld() as w:
        assert w.run(ds.leave_crandor(w.logs.append))
        w.position = None
        assert not w.run(ds.descend_crandor(w.logs.append))
        w.position = Tile(2855, 9635)
        assert w.run(ds.reach_elvarg(w.logs.append))
        w.position = Tile(2835, 9602)
        wall = w.seam('Wall', ds.DS_LOC.CRANDOR_SECRET_DOOR, 'Open', ds.DS_LOC.SECRET_WALL_KARAMJA_STAND)
        assert w.run(ds.leave_crandor(w.logs.append))
        w.position = ds.DS_LOC.CRANDOR_ROCK
        w.seam('Rock opening', ds.DS_LOC.CRANDOR_ROCK, 'Climb-down', Tile(2835, 9602))
        assert w.run(ds.leave_crandor(w.logs.append))
        w.position = ds.DS_LOC.SECRET_WALL_KARAMJA_STAND
        w.seam('Wall', ds.DS_LOC.CRANDOR_SECRET_DOOR, 'Open', Tile(2835, 9602))
        assert w.run(ds.descend_crandor(w.logs.append))
