"""Game facade commands preserve targets, style choices and navigation outcomes."""

import rs2004.game as api
import rs2004.entities as entities
from rs2004.geometry import Tile
from helpers import FakeModule, raises
from coverage_world import PatchWorld


def test_game_scene_energy_appearance_and_combat_reads():
    calls = []
    me = FakeModule(animation=1, target=('player', 2))
    with PatchWorld() as world:
        world.patch(api, '_core', FakeModule(is_placed=lambda: True, get_run_energy=lambda: 65,
            set_run=lambda enabled: calls.append(enabled) or True, get_weight=lambda: 7,
            is_appearance_screen_open=lambda: True, set_appearance=lambda *args: calls.append(args) or True,
            get_local_player=lambda: me, get_varp=lambda id: 0, in_combat=lambda: True,
            click_component=lambda id: calls.append(id) or True))
        assert api.game.scene_ready() and api.game.scene_state() == 2
        assert world.run(api.game.open_side_tab(3))
        assert api.game.energy() == 65 and api.game.weight() == 7 and api.game.set_run(True)
        assert api.game.appearance_screen_open() and api.game.set_appearance(False, [1] * 7, [0] * 5)
        assert calls[-1] == (False, [1] * 7, [0] * 5)
        assert api.game.animating() and api.game.attacked_by_player() and api.game.auto_retaliate_on()
        world.patch(api, 'combat_styles', lambda: [(0, '(Accurate)'), (1, '(Aggressive)'), (2, '(Defensive)')])
        world.patch(api, '_select_button', lambda varp, mode: FakeModule(id=100 + mode) if mode < 3 else None)
        assert api.game.has_combat_style('attack')
        assert api.game.set_combat_style('strength') and calls[-1] == 101
        assert api.game.set_combat_style(2) and calls[-1] == 102
        assert not api.game.set_combat_mode(9)
        assert api.game.set_auto_retaliate(False) and calls[-1] == 101
        assert 'combat style' in raises(ValueError, lambda: api.game.set_combat_style('invalid'))


def test_game_spells_dispatch_targets_and_missing_spells_send_nothing():
    calls = []
    with PatchWorld() as world:
        world.patch(api, 'spell_button', lambda name: 42 if name == 'Wind strike' else -1)
        world.patch(api, '_core', FakeModule(
            cast_on_npc=lambda *args: calls.append(('npc', args)) or True,
            cast_on_player=lambda *args: calls.append(('player', args)) or True,
            cast_on_loc=lambda *args: calls.append(('loc', args)),
            cast_on_ground_item=lambda *args: calls.append(('ground', args)) or True))
        target = FakeModule(id=5, _x=10, _z=20)
        for cast, kind in [(api.game.cast_on_npc, 'npc'), (api.game.cast_on_player, 'player'),
                           (api.game.cast_on_ground_item, 'ground')]:
            assert cast('Wind strike', target) and calls[-1] == (kind, (42, target))
            before = len(calls)
            assert cast('missing', target) is False and len(calls) == before
        assert api.game.cast_on_loc('Wind strike', target) and calls[-1] == ('loc', (42, 5, 10, 20))
        assert api.game.cast_on_loc('missing', target) is False


def test_reader_catalog_caches_records_and_preserves_note_links():
    calls = []
    rows = [(1, 'Logs', 2, False, False, False, -1, 0), (2, 'Logs', 2, True, False, False, 1, 0)]
    with PatchWorld() as world:
        world.patch(api, '_core', FakeModule(get_item_catalog=lambda: calls.append('catalog') or rows,
            find_type_ids=lambda kind, name: calls.append((kind, name)) or [1, 2],
            get_main_modal=lambda: 10, get_side_modal=lambda: 20, get_chat_modal=lambda: -1,
            get_max_stat=lambda skill: 0))
        reader = api._Reader()
        catalog = reader.obj_catalog()
        assert reader.obj_catalog() is catalog and calls == ['catalog']
        assert catalog[0].note_of is None and catalog[1].note_of == 1
        assert 'Logs' in repr(catalog[0])
        assert reader.item_ids('Logs') == [1, 2] and calls[-1] == ('item', 'Logs')
        assert reader.npc_ids('Guard') == [1, 2] and calls[-1] == ('npc', 'Guard')
        assert reader.loc_ids('Door') == [1, 2] and calls[-1] == ('loc', 'Door')
        modals = reader.modals()
        assert (modals.main, modals.side, modals.chat) == (10, 20, -1)
        assert repr(modals) == 'Modals(10, 20, -1)' and api.skills.hp_fraction() == 1
        assert 'tile' in repr(api.HintArrow('tile', -1, Tile(1, 2)))


def test_social_facades_forward_names_and_messages():
    calls = []
    def record(*args):
        calls.append(args)
        return True
    with PatchWorld() as world:
        world.patch(api, '_core', FakeModule(say=record, send_pm=record, command=record,
            add_friend=record, remove_friend=record, add_ignore=record, remove_ignore=record))
        assert api.chat.say('Hello') and calls[-1] == ('Hello',)
        assert api.chat.send_pm('Alice', 'Hello') and calls[-1] == ('Alice', 'Hello')
        assert api.chat.command('test') and calls[-1] == ('test',)
        for op in [api.friends.add, api.friends.remove, api.ignores.add, api.ignores.remove]:
            assert op('Alice') and calls[-1] == ('Alice',)


class DirectWorld(PatchWorld):
    def __init__(self):
        PatchWorld.__init__(self)
        self.position = Tile(0, 0)
        self.accept = True
        self.arrive = True
        self.pending_walk = None
        self.clicks = []

    def __enter__(self):
        PatchWorld.__enter__(self)
        self.patch(api, '_core', FakeModule(step_time=self.step_time, get_level=lambda: 0, walk_to=self.walk))
        self.patch(api, 'local_tile', lambda: self.position)
        return self

    def walk(self, x, z, run):
        self.clicks.append((x, z, run))
        if self.accept:
            self.pending_walk = Tile(x, z)
        return self.accept

    def advance(self):
        PatchWorld.advance(self)
        if self.arrive and self.pending_walk is not None:
            self.position = self.pending_walk
            self.pending_walk = None


def test_direct_walk_arrival_rejection_and_timeout_outcomes():
    for accept, arrive, outcome in [(True, True, 'arrived'), (False, True, 'unreachable'), (True, False, 'timeout')]:
        with DirectWorld() as world:
            world.accept, world.arrive = accept, arrive
            nav = api._DirectNavigator()
            assert world.run(nav.walk_to((10, 10), 0, 2000, True)) == (outcome == 'arrived')
            assert nav.last_outcome == outcome and world.clicks[0] == (10, 10, True)
            if outcome == 'timeout':
                assert len(world.clicks) > 1 and world.now == 2000


def test_player_entity_menu_validity_targets_and_waypoint_interaction():
    calls = []
    player = entities.Player()
    player.index, player.name, player.target = 2, 'Alice', ('player', 7)
    player._x, player._z, player._plane = 1, 2, 0
    with PatchWorld() as world:
        world.patch(entities, '_core', FakeModule(get_player_menu=lambda: ['Trade with', None, 'Follow'],
            interact_player=lambda *args: calls.append(args) or True, get_players=lambda: [player],
            get_pid=lambda: 7, interact_loc_via=lambda *args: calls.append(args) or True,
            get_npc=lambda index: None))
        assert player.actions() == ['Trade with', 'Follow'] and player.interact(3)
        assert calls[-1] == (2, 3) and not player.interact(2)
        assert player.valid() and player.targets_me() and 'Alice' in repr(player)
        world.patch(entities, '_core', FakeModule(get_players=lambda: []))
        assert not player.valid()
        # Restore the command core for scenery dispatch.
        world.patch(entities, '_core', FakeModule(interact_loc_via=lambda *args: calls.append(args) or True))
        loc = entities.Loc()
        loc.id, loc.name, loc._x, loc._z, loc._plane, loc.layer, loc._ops = 4, 'Door', 1, 2, 0, 0, ['Open']
        assert loc.interact_via([(1, 1)], 'Open') and calls[-1] == ([(1, 1)], 4, 1, 2, 1)
        assert not loc.interact_via([], 'Missing') and 'Door' in repr(loc)
        npc = entities.Npc()
        npc._x, npc._z, npc._plane = 1, 2, 0
        assert npc.network_tile() == Tile(1, 2)
    assert entities.matches_entity_name(' Guard ', 'guard')
    assert not entities.matches_entity_name(None, 'guard')
