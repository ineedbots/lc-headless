"""Temple of Ikov's game legs, against what phase 17g's live run found."""

import _core
from rs2004 import execution
from rs2004.dialogue import chat_dialog
from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.items import equipment, inventory
from rs2004.quests.defs.ikov import dungeon, supplies
from rs2004.traversal import traversal
from rs2004.quests.defs.ikov.areas import IKOV_OBJ


class FakeItem:
    def __init__(self, id):
        self.id = id

    def use_on(self, target):
        return True


def fletch_asks_for_the_caption():
    asked = []

    def make_one(name):
        asked.append(name)
        return False
        yield

    spy_on(chat_dialog, 'make_one', impl=make_one)
    spy_on(chat_dialog, 'is_make_menu', returns=True)
    spy_on(chat_dialog, 'make_products', returns=['Yew Short Bow', 'Yew Long Bow'])
    spy_on(inventory, 'items', returns=[FakeItem(IKOV_OBJ.KNIFE), FakeItem(IKOV_OBJ.YEW_LOGS)])
    run_wait(supplies.fletch_bow(lambda line: None))
    expect(asked).to_equal(['Yew Short Bow'])


test("the fletch menu's product is asked for by its caption, not the item's name", fletch_asks_for_the_caption)


def bridge_is_one_click():
    clicks = []
    here = Tile(2651, 9828, 0)
    spy_on(equipment, 'contains', returns=True)
    spy_on(game, 'weight', returns=-2)

    def walked(*args, **kw):
        return True
        yield

    spy_on(traversal, 'walk_resilient', impl=walked)

    def click(x, z, run):
        clicks.append([x, z])
        return True

    patch(_core, 'walk_to', click)
    tiles = [here]

    def tile():
        return tiles[0]

    spy_on(game, 'tile', impl=tile)

    def delay_until(cond, ms):
        tiles[0] = Tile(2647, 9828, 0)
        return cond()
        yield

    spy_on(execution, 'delay_until', impl=delay_until)
    expect(run_wait(dungeon.cross_bridge(True, lambda line: None))).to_be(True)
    expect(clicks).to_equal([[2650, 9828]])


test('the lava bridge is stepped on with one click, since a re-click from the far side carries the bot back', bridge_is_one_click)


def armour_comes_off_for_the_bridge():
    off = []

    def nothing(log):
        return False
        yield

    def unequip(name):
        off.append(name)
        return True
        yield

    spy_on(dungeon, 'escape_pocket', impl=lambda log: walked_true())
    spy_on(dungeon, 'enter_ice_cavern', impl=nothing)
    spy_on(equipment, 'contains', returns=True)
    spy_on(equipment, 'items', returns=[Fake(name='Studded body')])
    spy_on(equipment, 'unequip', impl=unequip)
    spy_on(game, 'weight', returns=9)
    expect(run_wait(dungeon.unlock_south_gate(lambda line: None))).to_be(False)
    expect(off).to_equal(['Studded body'])


def walked_true():
    return True
    yield


test('armour worn at a shut gate comes off before the lever is fetched across the bridge', armour_comes_off_for_the_bridge)
