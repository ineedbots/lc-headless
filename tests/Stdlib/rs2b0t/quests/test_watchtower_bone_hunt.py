"""A dragon-bone hunt cleans up on success, interruption, failed preparation and exceptions."""

import rs2004.quests.defs.watchtower.bones as hunt
from rs2004.catalogs.record import Record
from rs2004.geometry import Tile


def result(value):
    return value
    yield


def hunt_world(mode):
    scene = Scene(Tile(2946, 3369, 0))
    scene.cancelled = False
    scene.left = 0
    scene.fights = 0
    scene.bank_opened = 0
    scene.stats['hitpoints'] = 50
    scene.wear(hunt.SHIELD)
    scene.wear('Rune scimitar')
    scene.item(379, 'Lobster', count=12)
    spy_on(hunt._core, 'step_time', impl=lambda: scene.clock)
    spy_on(hunt.event_signal, 'pending', impl=lambda: scene.cancelled)
    patch(hunt, 'bank_pending', False)
    spy_on(hunt, 'in_cell', returns=False)
    spy_on(hunt.game, 'set_combat_style', returns=mode != 'style')
    spy_on(hunt.game, 'set_auto_retaliate', returns=True)
    behavior = mode
    def bank(host, site, options):
        if behavior == 'exception':
            raise RuntimeError('bank failed')
        if behavior != 'weapon':
            host.pick_weapon(['Rune scimitar'])
        if behavior == 'food':
            scene.pack.clear()
        if behavior == 'interrupt':
            scene.cancelled = True
        return True
        yield
    def enter(host, site):
        scene.at = site.melee_anchor
        return behavior != 'entry'
        yield
    def leave(host, site):
        scene.left += 1
        scene.at = Tile(2946, 3369, 0)
        return behavior != 'exit'
        yield
    def deposit(predicate, log=None):
        scene.pack = [item for item in scene.pack if not predicate(item.name, item.id)]
        return True
        yield
    def fight():
        scene.fights += 1
        scene.on_ground(hunt.WT_ITEM.DRAGON_BONES.id, 'Dragon bones')
        return True
        yield
    spy_on(hunt, 'bank_routine', impl=bank)
    spy_on(hunt, 'acquire_key', impl=lambda *args: result('missing' if behavior == 'key' else 'held'))
    spy_on(hunt, 'enter_lair', impl=enter)
    spy_on(hunt, 'leave_lair', impl=leave)
    spy_on(hunt.banking, 'open', impl=lambda **kwargs: result(behavior != 'bank'))
    spy_on(hunt.bank, 'deposit_all_matching', impl=deposit)
    spy_on(hunt.Fight, 'validate', returns=True)
    spy_on(hunt.Fight, 'blocks_loot', returns=False)
    spy_on(hunt.Fight, 'execute', impl=fight)
    spy_on(hunt.Retreat, 'validate', returns=False)
    return scene


def completes():
    scene = hunt_world('success')
    expect(run_wait(hunt.hunt_dragon_bones('Lobster', scene.log))).to_be(True)
    expect(scene.fights).to_be(1)
    expect(scene.left).to_be(1)
    expect(hunt.dragon_bank_pending()).to_be(False)
    expect([item.name for item in scene.pack]).to_equal(['Dragon bones'])


test('Watchtower kills once, takes the bones, exits and refreshes its bank view', completes)


def fails(mode):
    def run():
        scene = hunt_world(mode)
        expect(run_wait(hunt.hunt_dragon_bones('Lobster', scene.log))).to_be(False)
        expect(scene.left).to_be(0 if mode == 'interrupt' else 1)
        expect(hunt.dragon_bank_pending()).to_be(mode in ['interrupt', 'exit', 'bank'])
    return run


for mode in ['weapon', 'food', 'key', 'style', 'entry', 'interrupt', 'exit', 'bank']:
    test('Watchtower leaves a failed hunt safely: ' + mode, fails(mode))


def exceptions():
    scene = hunt_world('exception')
    raised = False
    try:
        run_wait(hunt.hunt_dragon_bones('Lobster', scene.log))
    except RuntimeError:
        raised = True
    expect(raised).to_be(True)
    expect(scene.left).to_be(1)
    expect(hunt.dragon_bank_pending()).to_be(False)


test('a raised hunt failure still attempts the exit and bank refresh', exceptions)


def escape_and_resume():
    scene = hunt_world('success')
    scene.item(hunt.WT_ITEM.DRAGON_BONES.id, 'Dragon bones')
    expect(run_wait(hunt.hunt_dragon_bones('Lobster', scene.log))).to_be(True)
    scene.cancelled = True
    expect(run_wait(hunt.leave_dragon_lair(scene.log))).to_be(False)
    expect(run_wait(hunt.refresh_dragon_bank(scene.log))).to_be(False)
    expect(run_wait(hunt.hunt_dragon_bones('Lobster', scene.log))).to_be(False)
    scene.cancelled = False
    spy_on(hunt, 'in_cell', returns=True)
    spy_on(hunt, 'leave_cell', impl=lambda *args: result(False))
    expect(run_wait(hunt.leave_dragon_lair(scene.log))).to_be(False)
    scene.pack.clear()
    expect(run_wait(hunt.hunt_dragon_bones('Lobster', scene.log))).to_be(False)


test('a restarted hunt escapes with held bones and yields to events or a locked cell', escape_and_resume)


def combat_stops(mode):
    def run():
        scene = hunt_world('success')
        behavior = mode
        if mode == 'retreat':
            spy_on(hunt.Retreat, 'validate', returns=True)
            def retreat():
                scene.stats['hitpoints'] = 1
                return True
                yield
            spy_on(hunt.Retreat, 'execute', impl=retreat)
            spy_on(hunt.DragonHost, 'need_eat', returns=True)
            spy_on(hunt.DragonHost, 'eat_once', impl=lambda: result(False))
        elif mode == 'weak':
            spy_on(hunt.DragonHost, 'hp_fraction', returns=0.2)
            spy_on(hunt.DragonHost, 'need_eat', returns=False)
        elif mode in ['drop', 'full']:
            drop = scene.on_ground(hunt.WT_ITEM.DRAGON_BONES.id, 'Dragon bones')
            if mode == 'drop':
                drop._fields['interact'] = lambda op: False
            else:
                spy_on(hunt.inventory, 'is_full', returns=True)
                spy_on(hunt.DragonHost, 'eat_once', impl=lambda: result(False))
        elif mode == 'walk':
            spy_on(hunt.Fight, 'validate', returns=False)
            scene.walk_ok = False
        elif mode == 'event':
            def upkeep():
                scene.cancelled = True
                return True
                yield
            spy_on(hunt.sustain, 'run', impl=upkeep)
        elif mode == 'after-key':
            def key(*args):
                scene.pack.clear()
                return 'held'
                yield
            spy_on(hunt, 'acquire_key', impl=key)
        expect(run_wait(hunt.hunt_dragon_bones('Lobster', scene.log))).to_be(False)
    return run


for mode in ['retreat', 'weak', 'drop', 'full', 'walk', 'event', 'after-key']:
    test('Watchtower stops unsafe combat and cleans up: ' + mode, combat_stops(mode))
