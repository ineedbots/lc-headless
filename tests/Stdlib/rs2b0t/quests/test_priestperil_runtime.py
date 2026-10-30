"""Test Priest in Peril's key, water and essence handoffs across reruns."""
import rs2004.quests.defs.priestperil as priest
from rs2004 import execution


def result(value):
    return value
    yield


def key_swap():
    state = {'iron': False, 'tile': priest.MONUMENTS[0], 'uses': 0}
    spy_on(priest, 'try_open', impl=lambda *args: result(True))
    spy_on(priest, 'held_id', impl=lambda id: state['iron'] if id == priest.IRON_KEY_ID else False)
    def walk(tile, radius, log):
        state['tile'] = tile
        return True
        yield
    spy_on(priest, 'walk_to', impl=walk)
    def use(target):
        state['uses'] += 1
        state['iron'] = state['uses'] == 2
        return True
    spy_on(priest.inventory, 'items', returns=[Fake(id=priest.GOLDEN_KEY_ID, use_on=use)])
    def monuments():
        position = state['tile']
        return [Fake(name='Monument', tile=lambda: position)]
    spy_on(priest.locs, 'query', impl=querying(monuments))
    spy_on(execution, 'delay_ticks', impl=instant_ticks)
    expect(run_wait(priest.monument_leg(lambda message: None))).to_be(False)
    expect(state['iron']).to_be(True)
    expect(state['uses']).to_be(2)


test('Priest swaps the golden key at successive monuments and stops once the iron key arrives', key_swap)


def water_chain():
    state = {'water': priest.MURKY_ID, 'reported': False}
    spy_on(priest.game, 'tile', returns=priest.CELL_DOOR_STAND)
    spy_on(priest, 'enter_temple', impl=lambda *args: result(True))
    spy_on(priest, 'try_open', impl=lambda *args: result(True))
    spy_on(priest, 'walk_to', impl=lambda *args: result(True))
    spy_on(priest, 'held_id', impl=lambda id: state['water'] == id)
    drezel = Fake(name='Drezel', distance=lambda: 1)
    coffin = Fake(name='Coffin', tile=lambda: priest.COFFIN, distance=lambda: 1)
    spy_on(priest.npcs, 'query', impl=querying(lambda: [drezel]))
    spy_on(priest.locs, 'query', impl=querying(lambda: [coffin]))
    def use(target):
        if state['water'] == priest.MURKY_ID:
            assert target is drezel
            state['water'] = priest.BLESSED_ID
        else:
            assert target is coffin
            state['water'] = 0
        return True
    def items():
        return [Fake(id=state['water'], use_on=use)]
    spy_on(priest.inventory, 'items', impl=items)
    spy_on(execution, 'delay_until', impl=instant_until)
    def report(stop, log):
        assert stop is priest.DREZEL_CELL and state['water'] == 0
        state['reported'] = True
        return True
        yield
    spy_on(priest, 'reach_and_talk', impl=report)
    log = lambda message: None
    expect(run_wait(priest.water_leg(log))).to_be(False)
    expect(state['water']).to_be(priest.BLESSED_ID)
    expect(state['reported']).to_be(False)
    expect(run_wait(priest.water_leg(log))).to_be(False)
    expect(state['water']).to_be(0)
    expect(state['reported']).to_be(True)


test('Priest blesses murky water then pours it on the coffin before reporting to Drezel', water_chain)


def essence_delivery(finishes):
    def run():
        state = {'essence': 27, 'done': False, 'post_talks': 0}
        final_load = finishes
        spy_on(priest, 'journal_complete', impl=lambda: state['done'])
        spy_on(priest.inventory, 'count', impl=lambda name: state['essence'])
        spy_on(priest.inventory, 'contains', impl=lambda name: name == 'Wolfbane' and state['done'])
        spy_on(priest, 'try_open', impl=lambda *args: result(True))
        spy_on(priest, 'walk_to', impl=lambda *args: result(True))
        def hand_in(name, prefer, log):
            assert name == 'Drezel'
            state['essence'] = 0
            state['done'] = final_load
            return True
            yield
        spy_on(priest, 'talk_through', impl=hand_in)
        def post_talk(stop, log):
            assert stop is priest.DREZEL_MAUS
            state['post_talks'] += 1
            return True
            yield
        spy_on(priest, 'reach_and_talk', impl=post_talk)
        spy_on(execution, 'delay_until', impl=instant_until)
        spy_on(execution, 'delay_ticks', impl=instant_ticks)
        expect(run_wait(priest.essence_leg(lambda message: None))).to_be(finishes)
        expect(state['essence']).to_be(0)
        expect(state['post_talks']).to_be(1 if finishes else 0)
    return run


test('Priest returns to collect another load after a partial essence hand-in', essence_delivery(False))
test('Priest follows the final essence hand-in with the barrier-access conversation', essence_delivery(True))


def completed_barrier():
    spy_on(priest, 'journal_complete', returns=True)
    state = {'talks': 0}
    spy_on(priest.inventory, 'contains', impl=lambda name: state['talks'] == 2)
    def talk(stop, log):
        state['talks'] += 1
        return True
        yield
    spy_on(priest, 'reach_and_talk', impl=talk)
    expect(run_wait(priest.essence_leg(lambda message: None))).to_be(True)
    expect(state['talks']).to_be(2)


test('Priest performs both post-quest talks when Wolfbane was banked', completed_barrier)


def essence_restock(bank_has_essence):
    def run():
        state = {'essence': 0}
        available = bank_has_essence
        spy_on(priest, 'journal_complete', returns=False)
        spy_on(priest.inventory, 'count', impl=lambda name: state['essence'])
        spy_on(priest, 'free_slots', returns=19)
        spy_on(priest, 'walk_to', impl=lambda *args: result(True))
        def withdraw(step, hops, log):
            expect(step.items).to_equal([{'name': 'Rune essence', 'qty': 18}])
            assert step.bank is priest.VARROCK_EAST_BANK
            state['essence'] = 18 if available else 0
            return available
            yield
        spy_on(priest, 'execute_step', impl=withdraw)
        mined = spy_on(priest, 'mine_essence', impl=lambda log: result(False))
        expect(run_wait(priest.essence_leg(lambda message: None))).to_be(False)
        expect(len(mined.calls)).to_be(0 if bank_has_essence else 1)
    return run


test('Priest reserves a pack slot when withdrawing the next banked essence load', essence_restock(True))
test('Priest falls back to mining when the bank cannot supply essence', essence_restock(False))


def mining_trip():
    state = {'tile': priest.AUBURY_TILE, 'pick': False, 'full': False, 'operations': []}
    spy_on(priest.game, 'tile', impl=lambda: state['tile'])
    spy_on(priest, 'in_ess_mine', impl=lambda x, z: z == 10000)
    spy_on(priest.inventory, 'items', impl=lambda: [Fake(name='Bronze pickaxe')] if state['pick'] else [])
    def withdraw(step, hops, log):
        assert step.items[0]['name'] == 'Bronze pickaxe'
        state['pick'] = True
        return True
        yield
    spy_on(priest, 'execute_step', impl=withdraw)
    spy_on(priest, 'walk_to', impl=lambda *args: result(True))
    def teleport(op):
        assert op == 'Teleport'
        state['operations'].append(op)
        state['tile'] = Tile(2900, 10000)
        return True
    aubury = Fake(name='Aubury', actions=lambda: ['Teleport'], distance=lambda: 1, interact=teleport)
    spy_on(priest.npcs, 'query', impl=querying(lambda: [aubury]))
    def mine(op):
        assert op == 'Mine'
        state['operations'].append(op)
        state['full'] = True
        return True
    def leave(op):
        assert op == 'Use'
        state['operations'].append(op)
        state['tile'] = priest.AUBURY_TILE
        return True
    rock = Fake(name='Rune Essence', actions=lambda: ['Mine'], interact=mine)
    portal = Fake(name='Portal', actions=lambda: ['Use'], interact=leave)
    spy_on(priest.locs, 'query', impl=querying(lambda: [rock, portal]))
    spy_on(priest, 'free_slots', impl=lambda: 0 if state['full'] else 1)
    spy_on(execution, 'delay_until', impl=instant_until)
    expect(run_wait(priest.mine_essence(lambda message: None))).to_be(False)
    expect(state['operations']).to_equal(['Teleport', 'Mine', 'Use'])
    expect(state['tile']).to_be(priest.AUBURY_TILE)


test('Priest equips its mining trip with a banked pickaxe, teleports, fills the pack and leaves through the portal', mining_trip)


def missing_mining_tools():
    spy_on(priest.game, 'tile', returns=priest.AUBURY_TILE)
    spy_on(priest.inventory, 'items', returns=[])
    attempts = spy_on(priest, 'execute_step', impl=lambda *args: result(False))
    expect(run_wait(priest.mine_essence(lambda message: None))).to_be(False)
    expect(len(attempts.calls)).to_be(3)


test('Priest parks after all three banked pickaxe choices fail', missing_mining_tools)
