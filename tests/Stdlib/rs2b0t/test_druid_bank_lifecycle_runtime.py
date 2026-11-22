import bots.chaos_druid_killer as druids
from rs2004.bank import bank
from rs2004.geometry import Tile


def result(value):
    return value
    yield


def world():
    scene = Scene(druids.CHAOS_DRUID_FIELD)
    bot = druids.ChaosDruidKiller()
    bot.spot = druids.DRUID_SPOTS['Edgeville Dungeon']
    bot.location_name = 'Edgeville Dungeon'
    bot.trip_prepared = True
    bot.last_area = 'druid-dungeon'
    bot.died = False
    bot.deaths = 0
    bot.trips = 0
    bot.parked = False
    bot.food_name = 'Lobster'
    bot.food_withdraw = 12
    bot.panic_hp_fraction = 0.35
    spy_on(bot, 'log', impl=scene.log)
    opened = [False]

    def open_bank(stand, name, op):
        opened[0] = True
        return True
        yield

    def deposit():
        scene.pack = []
        yield

    def withdraw(name, amount):
        for _ in range(amount):
            scene.item(379, name)
        return True
        yield

    def close():
        opened[0] = False
        return True
        yield

    def up(op):
        scene.at = druids.TRAPDOOR_STAND

    def down(op):
        scene.at = druids.LADDER_STAND

    scene.loc('Ladder', ['Climb-up'], tile=druids.LADDER_STAND, effect=up, dist=None)
    scene.loc('Trapdoor', ['Climb-down'], tile=druids.TRAPDOOR_STAND, effect=down, dist=None)
    spy_on(bank, 'is_open', impl=lambda: opened[0])
    spy_on(bank, 'open_booth', impl=open_bank)
    spy_on(bank, 'deposit_inventory', impl=deposit)
    spy_on(bank, 'loaded', returns=True)
    spy_on(bank, 'count', returns=100)
    spy_on(bank, 'withdraw_x', impl=withdraw)
    spy_on(bank, 'close', impl=close)
    return scene, bot


def normal_bank_cycle():
    scene, bot = world()
    for _ in range(28):
        scene.item(199, 'Herb')
    task = druids.BankRun(bot)
    expect(task.validate()).to_be(True)
    run_wait(task.execute())
    expect(bot.trips).to_be(1)
    expect(bot.food_count()).to_be(12)
    expect(scene.at).to_equal(bot.spot.bank_stand)
    # Observe only after banking, just as the next task selection does live.
    expect(task.validate()).to_be(False)
    expect(bot.deaths).to_be(0)
    expect(bot.trip_prepared).to_be(True)
    run_wait(druids.GoToField(bot).execute())
    bot.observe_lifecycle()
    expect(bot.in_field()).to_be(True)
    expect(task.validate()).to_be(False)
    expect(bot.deaths).to_be(0)
    expect(bot.trips).to_be(1)


def missed_death_message():
    scene, bot = world()
    scene.at = Tile(3222, 3218, 0)
    expect(druids.bank_reason(bot)).to_be('prepare-trip')
    expect(bot.deaths).to_be(1)
    expect(bot.died).to_be(True)
    bot.observe_lifecycle()
    expect(bot.deaths).to_be(1)
    run_wait(druids.BankRun(bot).execute())
    expect(bot.food_count()).to_be(12)
    expect(bot.trip_prepared).to_be(True)
    expect(bot.died).to_be(False)
    expect(bot.deaths).to_be(1)
    expect(druids.BankRun(bot).validate()).to_be(False)


test('a real dungeon-bank-dungeon workflow does not infer a death after restocking', normal_bank_cycle)
test('an unexpected surface respawn without a death message still restocks exactly once', missed_death_message)
