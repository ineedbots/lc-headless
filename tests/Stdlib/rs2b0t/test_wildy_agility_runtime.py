"""WildyAgility's per-tick clicks and bounded retries from rs2b0t #875 (MIT, see thirdparty/rs2b0t)."""

import bots.wildy_agility as wildy
from rs2004.dialogue import chat_dialog
from rs2004.execution import event_signal
from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.settings import SettingsBag


def lap_world(step=0):
    scene = Scene(wildy.get_start_tile(wildy.COURSE_OBSTACLES[step]))
    scene.stats['agility'] = 100
    scene.item(379, 'Lobster')
    bot = wildy.WildyAgility()
    bot.step = step
    bot.laps = 0
    bot.cleared = 0
    bot.died = False
    bot.entered = True
    bot.just_escaped_pit = False
    bot.food = 'lobster'
    bot.obstacle_timeout_ticks = 5
    bot.last_cleared_tick = 0
    bot.obstacle_times = []
    spy_on(bot, 'log', impl=scene.log)
    spy_on(wildy, 'now_ms', impl=lambda: scene.clock)
    spy_on(game, 'animating', returns=False)
    spy_on(event_signal, 'pending', returns=False)
    return scene, bot, wildy.RunLap(bot)


def obstacle(scene, bot, effect):
    clicks = []

    def click(op):
        clicks.append(scene.ticks)
        return effect(op, len(clicks))

    scene.loc(bot.current_name(), actions=['Cross'], effect=click)
    return clicks


def lost_click_recovers():
    scene, bot, task = lap_world()

    def click(op, count):
        if count == 2:
            scene.stats['agility'] += 10
        return True

    clicks = obstacle(scene, bot, click)
    task.stuck = 2
    run_wait(task.execute())
    expect(clicks).to_equal([0, 1])
    expect(bot.cleared).to_be(1)
    expect(bot.step).to_be(1)
    expect(task.stuck).to_be(0)
    expect(scene.ticks).to_be(2)
    expect(len([line for line in scene.lines if 'again every tick' in line])).to_be(1)


test('a dropped click recovers on the next tick without spending a timeout or adding a settle delay', lost_click_recovers)


def stops_at_xp():
    scene, bot, task = lap_world()
    clicks = obstacle(scene, bot, lambda op, count: True)
    scene.later(lambda: None)
    scene.later(lambda: None)
    scene.later(lambda: scene.stats.update({'agility': 110}))
    run_wait(task.execute())
    expect(clicks).to_equal([0, 1, 2])
    expect(bot.obstacle_times).to_equal([3])
    expect(bot.last_cleared_tick).to_be(3)
    expect(bot.cleared).to_be(1)


test('clicks occur once per waiting tick and stop before clicking after XP arrives', stops_at_xp)


def late_refusal_after_clear(message):
    scene, bot, task = lap_world()
    clicks = obstacle(scene, bot, lambda op, count: True)
    task.stuck = 1

    def clear():
        scene.stats['agility'] += 10
        scene.say(message)

    scene.later(clear)
    run_wait(task.execute())
    expect(clicks).to_equal([0])
    expect(bot.step).to_be(1)
    expect(bot.cleared).to_be(1)
    expect(task.stuck).to_be(0)
    expect(scene.walks).to_equal([])


test_each(['You cannot do that from here.', "I can't reach that!"])(
    'XP wins over a late refusal from a click arriving as traversal finishes: %s', late_refusal_after_clear)


def failed_click_ladder():
    scene, bot, task = lap_world()
    clicks = obstacle(scene, bot, lambda op, count: False)
    run_wait(task.execute())
    expect(task.stuck).to_be(1)
    expect(bot.step).to_be(0)
    run_wait(task.execute())
    expect(task.stuck).to_be(2)
    expect(scene.logged('walking back to starting side')).to_be(True)
    run_wait(task.execute())
    expect(bot.step).to_be(1)
    expect(bot.cleared).to_be(0)
    expect(task.stuck).to_be(0)
    expect(len(clicks)).to_be(3)


test('unsent initial clicks retry in place, walk back, then skip instead of looping forever', failed_click_ladder)


def disappearing_actions():
    scene, bot, task = lap_world()
    loc = scene.loc(bot.current_name(), actions=[])
    spy_on(task, 'find', returns=loc)
    for _ in range(3):
        run_wait(task.execute())
    expect(scene.logged('has no actions')).to_be(True)
    expect(scene.logged('walking back to starting side')).to_be(True)
    expect(bot.step).to_be(1)
    expect(bot.cleared).to_be(0)


test('actions disappearing between the scene query and click use the retry ladder', disappearing_actions)


def skip_wrap_walks_to_pipe():
    scene, bot, task = lap_world(4)
    obstacle(scene, bot, lambda op, count: False)
    task.stuck = 2
    run_wait(task.execute())
    expect(bot.step).to_be(0)
    expect(bot.laps).to_be(1)
    expect(bot.cleared).to_be(0)
    expect(scene.walks).to_equal([wildy.get_start_tile('obstacle pipe')])


test('a failed-click skip at the rocks wraps and walks to the first starting side', skip_wrap_walks_to_pipe)


def unreachable_retry_start():
    scene, bot, task = lap_world()
    obstacle(scene, bot, lambda op, count: False)
    scene.at = Tile(2998, 3938)
    scene.walk_ok = False
    task.stuck = 1
    run_wait(task.execute())
    expect(bot.step).to_be(1)
    expect(task.stuck).to_be(0)
    expect(scene.logged('starting side unreachable')).to_be(True)


test('a failed walk back advances instead of resetting into an impossible click', unreachable_retry_start)


def timeouts_share_retry_budget():
    scene, bot, task = lap_world()
    obstacle(scene, bot, lambda op, count: True)
    run_wait(task.execute())
    expect(task.stuck).to_be(1)
    expect(scene.logged('5 ticks (5 idle, 4 re-clicks)')).to_be(True)
    scene.locs[0]._fields['interact'] = lambda op: False
    run_wait(task.execute())
    expect(task.stuck).to_be(2)
    expect(scene.logged('walking back to starting side')).to_be(True)
    run_wait(task.execute())
    expect(bot.step).to_be(1)
    expect(bot.cleared).to_be(0)


test('timeouts and failed sends share one retry budget and keep the configured idle bound', timeouts_share_retry_budget)


def animating_is_wall_clock_bounded():
    scene, bot, task = lap_world()
    clicks = obstacle(scene, bot, lambda op, count: True)
    spy_on(game, 'animating', returns=True)
    run_wait(task.execute())
    expect(scene.logged('10 ticks (0 idle, 9 re-clicks)')).to_be(True)
    expect(len(clicks)).to_be(10)
    expect(task.stuck).to_be(1)


test('endless animation cannot keep per-tick re-clicking past the wall-clock bound', animating_is_wall_clock_bounded)


def interruption(kind):
    scene, bot, task = lap_world()
    clicks = obstacle(scene, bot, lambda op, count: True)
    task.stuck = 1

    def interrupt():
        if kind == 'death':
            bot.died = True
        elif kind == 'dialogue':
            spy_on(chat_dialog, 'can_continue', returns=True)
        else:
            spy_on(event_signal, 'pending', returns=True)

    scene.later(interrupt)
    run_wait(task.execute())
    expect(clicks).to_equal([0])
    expect(task.stuck).to_be(1)
    expect(bot.step).to_be(0)
    expect(bot.cleared).to_be(0)


test_each(['death', 'dialogue', 'random event'])('stops re-clicks for %s without spending a retry', interruption)


def falls_stop_clicks(kind):
    scene, bot, task = lap_world()
    clicks = obstacle(scene, bot, lambda op, count: True)
    task.stuck = 1

    def fall():
        if kind == 'pit tile':
            scene.at = Tile(3000, 9900)
        else:
            scene.say('You lose your footing and fall into the lava.')

    scene.later(fall)
    run_wait(task.execute())
    expect(clicks).to_equal([0])
    expect(task.stuck).to_be(0)
    expect(bot.step).to_be(0)


test_each(['pit tile', 'fall message'])('stops re-clicks for %s and leaves recovery a fresh retry budget', falls_stop_clicks)


def food_takes_priority():
    scene, bot, task = lap_world()
    clicks = obstacle(scene, bot, lambda op, count: True)
    spy_on(wildy, 'need_eat', returns=True)
    task.stuck = 1
    run_wait(task.execute())
    expect(clicks).to_equal([0, 1, 2])
    expect(scene.ticks).to_be(3)
    expect(task.stuck).to_be(1)
    expect(bot.step).to_be(0)


test('food yields after three ticks without another click or retry charge', food_takes_priority)


def refusal_stops_reclicks(message):
    scene, bot, task = lap_world()
    clicks = obstacle(scene, bot, lambda op, count: True)
    scene.later(lambda: scene.say(message))
    run_wait(task.execute())
    expect(clicks).to_equal([0])
    expect(bot.cleared).to_be(0)
    expect(bot.step).to_be(0)
    expect(task.stuck).to_be(1 if "reach" in message else 0)


test_each(["I can't reach that!", 'You cannot do that from here.'])('stops re-clicks on refusal: %s', refusal_stops_reclicks)


def startup_settings(configured):
    scene, bot, task = lap_world()
    scene.stats['agility'] = 52
    spy_on(game, 'ingame', returns=True)
    spy_on(game, 'auto_retaliate_on', returns=False)
    spy_on(bot, 'on', returns=None)
    bot.settings = SettingsBag({'food_withdraw': 20, 'obstacle_timeout_ticks': 12} if configured else {})
    run_wait(bot.on_start())
    expect(bot.food_withdraw).to_be(20 if configured else 28)
    expect(bot.obstacle_timeout_ticks).to_be(12 if configured else 24)
    expect(bot.entered).to_be(True)
    expect(scene.walks).to_equal([])


test_each([False, True])('startup preserves existing food/timeout settings and otherwise fills the pack: %s', startup_settings)
