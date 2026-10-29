"""Public facade dispatch, equipment acknowledgements and scheduler boundaries."""

import rs2004.items as items
import rs2004.interfaces as ui
import rs2004.bot as bots
import rs2004.geometry as geometry
from rs2004 import execution
from rs2004.console import Command, console
from rs2004.entities import Npc, Player, Loc, GroundItem
from helpers import FakeModule, raises
from coverage_world import PatchWorld


class EquipmentWorld(PatchWorld):
    def __init__(self):
        PatchWorld.__init__(self)
        self.pack = []
        self.worn = []
        self.accept = True
        self.arrives = True
        self.pending_equip = None
        self.ops = []

    def __enter__(self):
        PatchWorld.__enter__(self)
        self.patch(items, '_core', self)
        return self

    def get_inventory(self, com):
        return self.pack

    def get_equipment(self):
        return self.worn

    def item(self, ops):
        item = items.InvItem()
        item.id, item.name, item.count, item.slot = 1, 'Test gear', 1, 0
        item.com, item._ops, item._button = 3214, ops, False
        return item

    def item_op(self, item, op):
        self.ops.append(('equip', op))
        if self.accept:
            self.pending_equip = ('equip', item)
        return self.accept

    def inv_button(self, item, op):
        self.ops.append(('remove', op))
        if self.accept:
            self.pending_equip = ('remove', item)
        return self.accept

    def advance(self):
        PatchWorld.advance(self)
        if self.pending_equip is not None and self.arrives:
            op, item = self.pending_equip
            source = self.pack if op == 'equip' else self.worn
            target = self.worn if op == 'equip' else self.pack
            source.remove(item)
            target.append(item)
            self.pending_equip = None


def test_equipment_each_supported_action_waits_for_worn_item():
    for op in ['Wield', 'Wear', 'Equip']:
        with EquipmentWorld() as world:
            world.pack = [world.item([op])]
            assert world.run(items.equipment.equip(' TEST GEAR '))
            assert world.pack == [] and len(world.worn) == 1 and world.now == 500


def test_equipment_missing_item_or_equip_action_does_nothing():
    with EquipmentWorld() as world:
        assert world.run(items.equipment.equip('missing')) is False
        world.pack = [world.item(['Drop'])]
        assert world.run(items.equipment.equip('Test gear')) is False
        assert world.ops == [] and world.waits == []


def test_equipment_rejected_equip_and_missing_acknowledgement():
    for accept in [False, True]:
        with EquipmentWorld() as world:
            world.pack = [world.item(['Wear'])]
            world.accept, world.arrives = accept, False
            assert world.run(items.equipment.equip('Test gear')) is False
            assert world.now == (3000 if accept else 0) and world.worn == []


def test_equipment_remove_waits_for_backpack_arrival():
    with EquipmentWorld() as world:
        world.worn = [world.item(['Remove'])]
        assert world.run(items.equipment.unequip('Test gear'))
        assert world.worn == [] and len(world.pack) == 1
        assert world.ops == [('remove', items.REMOVE_OPTION)]


def test_equipment_missing_rejected_and_unacknowledged_removal():
    with EquipmentWorld() as world:
        assert world.run(items.equipment.unequip('missing')) is False
        world.worn = [world.item(['Remove'])]
        world.accept = False
        assert world.run(items.equipment.unequip('Test gear')) is False and world.now == 0
        world.accept, world.arrives = True, False
        assert world.run(items.equipment.unequip('Test gear')) is False and world.now == 3000


def test_inventory_button_move_and_entity_target_dispatch():
    calls = []
    with EquipmentWorld() as world:
        item = world.item(['Use'])
        item._button = True
        assert item.interact('Use')
        world.patch(items, '_core', FakeModule(
            move_item=lambda *args: calls.append(('move', args)),
            use_item_on_npc=lambda a, b: calls.append(('npc', b)) or True,
            use_item_on_player=lambda a, b: calls.append(('player', b)) or True,
            use_item_on_loc=lambda a, id, x, z: calls.append(('loc', (id, x, z))) or True,
            use_item_on_ground_item=lambda a, b: calls.append(('ground', b)) or True))
        assert item.move_to(4, True) and calls[-1] == ('move', (3214, 0, 4, True))
        for target, kind in [(Npc(), 'npc'), (Player(), 'player'), (GroundItem(), 'ground')]:
            assert item.use_on(target) and calls[-1] == (kind, target)
        loc = Loc()
        loc.id, loc._x, loc._z = 7, 3000, 3001
        assert item.use_on(loc) and calls[-1] == ('loc', (7, 3000, 3001))
        assert 'Test gear' in repr(item)


def test_interface_facade_passes_ids_filters_and_click_results():
    calls = []
    component = ui.Component()
    component.id, component.type, component.button, component.text = 12, 'text', 'ok', 'Accept'
    with PatchWorld() as world:
        world.patch(ui, '_core', FakeModule(
            get_component=lambda id: component if id == 12 else None,
            get_interface=lambda id: [component] if id == 10 else [],
            get_open_interfaces=lambda: [10], get_tab_interface=lambda n: 10 if n == 3 else -1,
            find_components=lambda *args: calls.append(args) or [component],
            click_component=lambda id: id == 12))
        assert ui.interfaces.component(12) is component and ui.interfaces.component(-1) is None
        assert ui.interfaces.root(10) == [component] and ui.interfaces.open() == [10]
        assert ui.interfaces.tab(3) == 10 and ui.interfaces.tab(2) == -1
        assert ui.interfaces.find('Accept', 'ok', 10) == [component]
        assert calls == [('Accept', 'ok', 10)]
        assert component.click() and ui.interfaces.click(12) and not ui.interfaces.click(-1)
        assert 'Accept' in repr(component)
        component.text = ''
        assert repr(component) == 'Component(id=12, type=text, button=ok)'


def test_polygon_sampling_stays_inside_and_preserves_level():
    area = geometry.Area.polygon([(0, 0), (8, 0), (0, 8)], 2)
    for i in range(30):
        tile = area.get_random_tile()
        assert area.contains(tile) and tile.level == 2
    assert 'polygon' in repr(area)
    assert 'rectangular' in repr(geometry.Area.rectangular((0, 0), (2, 2)))
    assert 'circular' in repr(geometry.Area.circular((0, 0), 2))
    assert geometry.Tile(1, 2).__ne__('tile') is NotImplemented
    assert raises(NotImplementedError, lambda: geometry.Area().contains((0, 0))) == ''
    assert raises(NotImplementedError, geometry.Area().get_random_tile) == ''


def test_wait_validation_repr_and_tick_timeout():
    assert repr(execution.Update(300)) == 'Update(300)'
    assert repr(execution.Ticks(2)) == 'Ticks(2)'
    for value in [0, -1, True, 1.5]:
        assert 'count' in raises(ValueError, lambda: execution.Ticks(value))
    with PatchWorld() as world:
        assert world.run(execution.delay_until_ticks(lambda: False, 2)) is False
        assert world.now == 1000


def test_bot_abstract_contracts_and_invalid_manifest_arguments():
    bot = bots.AbstractBot()
    assert bot.grind_targets() == [] and bot.ignored_randoms() == [] and bot.recovery_anchor() is None
    calls = [bots.LoopingBot().loop, bots.Task().validate, bots.Task().execute,
             bots.BranchTask().validate, bots.BranchTask().success, bots.BranchTask().failure,
             bots.LeafTask().execute, bots.TreeBot().root]
    for call in calls:
        assert 'must define' in raises(NotImplementedError, call)
    assert 'name' in raises(ValueError, lambda: bots.define_bot('', bots.LoopingBot))
    assert 'create' in raises(TypeError, lambda: bots.define_bot('invalid', 1))
    assert repr(bots.define_bot('test', bots.LoopingBot)) == "BotManifest('test')"
    assert 'task' in raises(TypeError, lambda: bots.TaskBot().add(object()))


class EmptyTree(bots.TreeBot):
    def root(self):
        return 3


class WaitingLeaf(bots.LeafTask):
    def execute(self):
        yield execution.Ticks(1)


class WaitingTree(bots.TreeBot):
    def root(self):
        return WaitingLeaf()


def test_task_generator_guard_and_empty_task_list():
    def ready():
        yield execution.Ticks(1)
        return True
    calls = []
    bot = bots.TaskBot()
    with PatchWorld() as world:
        assert world.run(bot.loop()) is None and bot.active_task_name is None
        bot.add(bots.Task(ready, lambda: calls.append('ran'), 'waiting'))
        world.run(bot.loop())
        assert calls == ['ran'] and bot.active_task_name is None
        assert world.run(WaitingTree().loop()) is None
        assert 'BranchTask or a LeafTask' in raises(TypeError, lambda: world.run(EmptyTree().loop()))


def test_console_rejects_blank_name_and_non_text_help():
    assert 'name' in raises(ValueError, lambda: console.command('', lambda cmd: None))
    assert 'help' in raises(TypeError, lambda: console.command('invalidhelp', lambda cmd: None, 3))
    assert 'hi' in repr(Command('hi', 'hi there', ['hi', 'there']))
