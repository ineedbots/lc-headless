from bots.gnome_course import AgilityBot


def course_exit():
    bot = AgilityBot()
    bot.step = 4
    spy_on(game, 'tile', returns=Tile(2483, 3420, 2))
    assert not bot.can_leave()
    spy_on(game, 'tile', returns=Tile(2487, 3420, 0))
    assert not bot.can_leave()
    bot.step = 0
    spy_on(game, 'tile', returns=Tile(2483, 3420, 2))
    assert not bot.can_leave()
    spy_on(game, 'tile', returns=Tile(2484, 3437, 0))
    assert bot.can_leave()


test('gnome course permits a bank handoff after the last obstacle has settled on the ground', course_exit)
