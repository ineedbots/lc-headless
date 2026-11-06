"""Redberries fall back from shop stock to bounded ground respawns."""

import rs2004.quests.defs.goblindiplomacy_redberries as berries


def reply(value):
    return value
    yield


def acquisition(mode):
    def run():
        behavior = mode
        scene = Scene(berries.SPAWNS[0] if mode == 'near' else Tile(3000, 3200, 0))
        if mode == 'held':
            scene.item(1951, 'Redberries', 3)
        if mode == 'full':
            spy_on(berries.inventory, 'is_full', returns=True)
        if mode == 'interrupted':
            spy_on(berries.event_signal, 'pending', returns=True)
        count = [0]
        def execute(step, hops, log):
            count[0] += 1
            if behavior == 'shop' or (behavior in ['near', 'fallback'] and step.kind == 'grab_ground'):
                scene.item(1951, 'Redberries', 3)
            elif behavior == 'partial' and count[0] == 2:
                scene.item(1951, 'Redberries', 1)
            elif behavior == 'fills':
                spy_on(berries.inventory, 'is_full', returns=True)
            elif behavior == 'during':
                spy_on(berries.event_signal, 'pending', returns=True)
            return True
            yield
        spy_on(berries, 'execute_step', impl=execute)
        expect(run_wait(berries.acquire_redberries(scene.log))).to_be(mode in ['held', 'shop', 'near', 'fallback', 'partial'])
        if mode == 'empty':
            expect(count[0]).to_be(13)
            expect(scene.logged('redberry acquisition stopped')).to_be(True)
        if mode == 'near':
            expect(count[0]).to_be(1)
    return run


for mode in ['held', 'full', 'interrupted', 'shop', 'near', 'fallback', 'partial', 'fills', 'during', 'empty']:
    test('redberry acquisition handles ' + mode, acquisition(mode))


def interruptions():
    for pending_at in [2, 3, 4, 8, 10, 11]:
        scene = Scene(berries.SPAWNS[0])
        calls = [0]
        def pending():
            calls[0] += 1
            return calls[0] >= pending_at
        spy_on(berries.event_signal, 'pending', impl=pending)
        spy_on(berries, 'execute_step', impl=lambda *args: reply(False))
        expect(run_wait(berries.acquire_redberries(scene.log))).to_be(False)
    scene = Scene(berries.SPAWNS[0])
    calls = [0]
    def full():
        calls[0] += 1
        return calls[0] >= 3
    spy_on(berries.inventory, 'is_full', impl=full)
    expect(run_wait(berries.acquire_redberries(scene.log))).to_be(False)


test('redberry spawn walks and respawn waits stop immediately for events or a filled pack', interruptions)
