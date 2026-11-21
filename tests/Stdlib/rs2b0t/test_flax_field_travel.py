import bots.flax_aio as flax
from bots.flax_aio import FIELD, GoToFieldTask, PickTask


def visible_field_from_bank():
    here = [Tile(2724, 3493, 0)]
    spy_on(game, 'tile', impl=lambda: here[0])
    spy_on(inventory, 'is_full', returns=False)
    spy_on(flax, 'nearest_flax', returns=Fake())
    bot = Fake(picking=True, status='starting')
    travel = GoToFieldTask(bot)
    pick = PickTask(bot)
    assert not pick.validate()
    assert travel.validate()

    def walk(bot, dest, radius):
        assert dest == FIELD
        here[0] = dest
        return True
        yield

    spy_on(flax, 'travel_to', impl=walk)
    run_wait(travel.execute())
    assert pick.validate()
    assert not travel.validate()
    spy_on(inventory, 'is_full', returns=True)
    assert not pick.validate()
    assert not travel.validate()


test('visible flax beyond the picking radius still triggers travel from the bank', visible_field_from_bank)
