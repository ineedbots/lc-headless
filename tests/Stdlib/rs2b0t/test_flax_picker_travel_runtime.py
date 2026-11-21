from bots.flax_picker import DEFAULT_FIELD, FlaxPicker, GoToField, Pick


def visible_field_from_bank():
    scene = Scene(Tile(2725, 3491, 0))
    bot = FlaxPicker()
    bot.field_tile = DEFAULT_FIELD
    spy_on(bot, 'nearest_flax', returns=Fake())
    travel = GoToField(bot)
    pick = Pick(bot)
    expect(pick.validate()).to_be(False)
    expect(travel.validate()).to_be(True)

    def arrive(dest, radius):
        expect(dest).to_equal(DEFAULT_FIELD)
        scene.at = dest
        return True
        yield

    spy_on(bot, 'travel_to', impl=arrive)
    run_wait(travel.execute())
    expect(pick.validate()).to_be(True)
    expect(travel.validate()).to_be(False)
    for id in range(28):
        scene.item(id, 'Flax')
    expect(pick.validate()).to_be(False)
    expect(travel.validate()).to_be(False)


test('FlaxPicker travels to visible flax outside its picking radius and leaves a full pack to banking', visible_field_from_bank)
