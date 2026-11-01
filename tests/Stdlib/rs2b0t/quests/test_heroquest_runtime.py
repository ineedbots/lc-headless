"""Hero's Quest's game legs, against what phase 17g's live run found."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.entities import ground_items, npcs
from rs2004.traversal import traversal
from rs2004.items import inventory
from rs2004.quests.defs.heroquest import feather, shops
from rs2004.quests.defs.heroquest.areas import HERO_SHOP


def nothing(log):
    return True
    yield


def buying_with(coins):
    """The steps a purchase of a 100000 gp item runs with coins in the pack."""
    kinds = []

    def run(step, hops, log):
        kinds.append(step)
        return True
        yield

    spy_on(shops, 'return_to_street', impl=nothing)
    spy_on(shops, 'execute_step', impl=run)
    spy_on(inventory, 'count', returns=coins)
    item = Record({'name': 'Rune platelegs', 'qty': 1, 'sources': [shops.priced(HERO_SHOP.SCAVVO, 100000)]})
    run_wait(shops.buy_from_any(item, lambda line: None))
    return kinds


def draws_the_shortfall():
    steps = buying_with(30000)
    expect([step.kind for step in steps]).to_equal(['withdraw', 'buy'])
    expect(steps[0].items[0]['qty']).to_be(70000)


test("a purse short of the stockist's price draws the difference before the shop", draws_the_shortfall)


def enough_goes_straight():
    expect([step.kind for step in buying_with(100000)]).to_equal(['buy'])


test('a purse that covers the price goes straight to the shop', enough_goes_straight)


def walked(*args, **kw):
    return True
    yield


def waits_for_the_queen():
    waits = []

    def delay_until(cond, ms):
        waits.append(ms)
        return False
        yield

    spy_on(traversal, 'walk_resilient', impl=walked)
    spy_on(npcs, 'query', returns=FakeQuery([]))
    spy_on(ground_items, 'query', returns=FakeQuery([]))
    spy_on(execution, 'delay_until', impl=delay_until)
    lines = []
    expect(run_wait(feather.kill_ice_queen(lines.append))).to_be(False)
    expect(waits).to_equal([feather.ICE_QUEEN_RESPAWN_MS])
    expect('the Ice Queen never respawned' in lines).to_be(True)


test("a Queen the partner has just killed is waited for, not read as a win with no drop", waits_for_the_queen)
