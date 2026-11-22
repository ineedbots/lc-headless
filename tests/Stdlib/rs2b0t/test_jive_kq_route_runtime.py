"""rs2b0t jivekq-route.test.ts on the headless dialogue/item facades (MIT, see thirdparty/rs2b0t)."""

from bots.jivekq import route
from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.dialogue import chat_dialog
from rs2004.trade import shop


def completed(value):
    return value
    yield


class ShopStock:
    def __init__(self, id, name, count):
        self.id = id
        self.name = name
        self.count = count


def refused_choice(option):
    return False
    yield


def disclaimer(confirmed):
    scene = Scene(Tile(3304, 3116))
    scene.item(route.PASS, 'Shantay pass')
    clicks = []

    def drop(op):
        clicks.append(op)
        if confirmed:
            scene.take(route.DISCLAIMER)
        return True

    scene.item(route.DISCLAIMER, 'Shantay disclaimer', actions=['Drop'], effect=drop)
    expect(run_wait(route.pass_gate(scene.log))).to_be(confirmed)
    if not confirmed:
        expect(run_wait(route.pass_gate(scene.log))).to_be(False)
    expect(clicks).to_equal(['Drop'] if confirmed else ['Drop', 'Drop'])
    expect(scene.has(route.PASS)).to_be(True)


test_each([True, False])('Shantay disclaimer drop must be confirmed and preserves the pass: %s', disclaimer)


def pass_shop_restock():
    scene = Scene(Tile(3304, 3120))
    scene.npc('Shantay', ['Talk-to', 'Trade'])
    stock_count = [0]
    purchases = []

    def stock():
        return [ShopStock(route.PASS, 'Shantay pass', stock_count[0])]

    def buy(name, count):
        purchases.append((name, count))

        if len(purchases) == 1:
            return completed(0)

        scene.item(route.PASS, 'Shantay pass')
        return completed(1)

    scene.later(lambda: stock_count.__setitem__(0, 1))
    spy_on(shop, 'open', impl=lambda keeper: completed(True))
    spy_on(shop, 'stock', impl=stock)
    spy_on(shop, 'buy', impl=buy)
    spy_on(shop, 'is_open', returns=True)
    spy_on(shop, 'stock_com', returns=3900)
    spy_on(shop, 'side_com', returns=3823)
    spy_on(shop, 'close', impl=lambda: completed(True))

    expect(run_wait(route.buy_pass(scene.log))).to_be(True)
    expect(purchases).to_equal([('Shantay pass', 1), ('Shantay pass', 1)])
    expect(scene.has(route.PASS)).to_be(True)
    expect(scene.logged('stock=[1854:Shantay passx0]')).to_be(True)
    expect(scene.logged('stock is empty')).to_be(True)
    expect(scene.logged('stock returned; retrying purchase')).to_be(True)


test('Shantay pass purchase waits for empty shop stock to return', pass_shop_restock)


def camelot():
    scene = Scene(Tile(3493, 9493))
    casts = spy_on(game, 'teleport', returns=True)
    scene.later(lambda: setattr(scene, 'at', route.CAMELOT))
    expect(run_wait(route.camelot())).to_be(True)
    expect(casts.calls).to_equal([('Camelot',)])


test('combat escape casts Camelot without a ring dialogue', camelot)


def interrupted_ring(critical):
    scene = Scene(Tile(3493, 9493))
    scene.stats['hitpoints'] = 49
    rubs = []
    scene.item(route.DUELING_RINGS[0], 'Ring of dueling(8)', actions=['Rub'], effect=lambda op: rubs.append(op) or True)

    def damage():
        scene.stats['hitpoints'] = 29 if critical else 48
        if critical:
            scene.chat.pages = [[route.DUEL_ARENA_OPTION]]

    scene.later(damage)
    if not critical:
        spy_on(chat_dialog, 'choose_option', impl=refused_choice)
    expect(run_wait(route.duel_arena())).to_be(False)
    expect(rubs).to_equal(['Rub'])
    expect(scene.chat.chosen).to_equal([])
    expect(scene.clock <= 1800).to_be(True)


test_each([False, True])('ring dialogue yields promptly to incoming damage, critical=%s', interrupted_ring)


def existing_ring_prompt():
    scene = Scene(Tile(3493, 9493))
    scene.chat.pages = [[route.DUEL_ARENA_OPTION]]

    def arrived(option):
        scene.at = route.DUEL_ARENA

    scene.chat.on_choose = arrived
    expect(run_wait(route.duel_arena())).to_be(True)
    expect(scene.chat.chosen).to_equal([route.DUEL_ARENA_OPTION])


test('an existing ring prompt completes without another rub', existing_ring_prompt)


def damaged_arrival():
    scene = Scene(Tile(3493, 9493))
    scene.stats['hitpoints'] = 49
    spy_on(game, 'teleport', returns=True)
    scene.later(lambda: scene.stats.update({'hitpoints': 48}))
    expect(run_wait(route.camelot())).to_be(False)
    expect(scene.clock <= 2400).to_be(True)


test('damage interrupts an unconfirmed teleport arrival so the caller can heal', damaged_arrival)


def rope_retry():
    scene = Scene(Tile(3485, 9509, 2))
    clicks = []
    scene.loc('Rope', ['Climb-down'], id=route.ROPE_TIED['upper'], effect=lambda op: clicks.append(op) or True)
    expect(run_wait(route.descend('upper'))).to_be(False)
    expect(run_wait(route.descend('upper'))).to_be(False)
    expect(clicks).to_equal(['Climb-down', 'Climb-down'])
    expect(scene.clock).to_be(3600)


test('an unacknowledged rope descent retries after three ticks without a five-second sleep', rope_retry)
