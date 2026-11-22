"""Exercise the collector's actual grind task, including pack exhaustion and refused clicks."""

from bots.herblore_secondaries import Grind, HerbloreSecondaries, secondary_by_name
from rs2004.geometry import Tile
from rs2004.bank import bank
from rs2004.execution import event_signal
from rs2004.game import game


def collector(scene):
    spy_on(game, 'ingame', returns=True)
    spy_on(game, 'scene_ready', returns=True)
    spy_on(event_signal, 'pending', returns=False)
    spy_on(bank, 'is_open', returns=False)
    bot = HerbloreSecondaries()
    bot.secondary = secondary_by_name('Unicorn horn dust')
    bot.gathered = 0
    bot.log = lambda message: scene.lines.append(message)
    return bot


def grind_pack():
    scene = Scene(Tile(3185, 3440, 0))
    bot = collector(scene)
    clicks = []

    def grind(target):
        if target not in scene.pack:
            return False
        clicks.append(target.slot)
        scene.drop_item(target)
        scene.item(235, 'Unicorn horn dust')
        return True

    scene.item(233, 'Pestle and mortar', on_use=grind)
    for slot in range(7):
        horn = scene.item(237, 'Unicorn horn')
        horn.slot = slot + 1
    run_wait(Grind(bot).execute())
    expect(bot.gathered).to_be(7)
    expect(bot.grind_left()).to_be(0)
    expect(bot.product_count()).to_be(7)
    expect(clicks).to_equal([7, 6, 5, 4, 3, 2, 1])


def refused_grind():
    scene = Scene(Tile(3185, 3440, 0))
    bot = collector(scene)
    scene.item(233, 'Pestle and mortar', on_use=lambda target: False)
    horn = scene.item(237, 'Unicorn horn')
    horn.slot = 1
    run_wait(Grind(bot).execute())
    expect(bot.gathered).to_be(0)
    expect(bot.grind_left()).to_be(1)


test('the secondary grind task consumes its whole pack and counts the dust', grind_pack)
test('a refused grind leaves the source and gathered count intact', refused_grind)
