"""rs2b0t jivekq-route.test.ts on the headless dialogue/item facades (MIT, see thirdparty/rs2b0t)."""

from bots.jivekq import route
from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.dialogue import chat_dialog


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
