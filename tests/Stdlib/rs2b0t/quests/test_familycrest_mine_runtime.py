"""Family Crest's mine lever chain, perfect metalwork and Chronozon's final crest."""

import rs2004.quests.defs.familycrest.chronozon as demon
from rs2004.dialogue import chat_dialog
from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.quests.defs.familycrest import mine
from rs2004.quests.defs.familycrest.areas import FC_ID, FC_ITEM, FC_LOC, FC_NPC


def answer(value):
    def wait(*args, **kwargs):
        return value
        yield
    return wait


def give(scene, id, name='Quest item'):
    def effect(*args):
        scene.item(id, name)
    return effect


def lever():
    scene = Scene(FC_LOC.MINE_LANDING)
    scene.walk_ok = False
    expect(run_wait(mine.set_lever('north', 'up', scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(mine.set_lever('north', 'up', scene.log))).to_be(False)
    scene.loc('Lever', ['Pull'], id=mine.LEVER_LOC.north.down, effect=lambda op: False)
    expect(run_wait(mine.set_lever('north', 'up', scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Lever', ['Pull'], id=mine.LEVER_LOC.north.down)
    expect(run_wait(mine.set_lever('north', 'up', scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Lever', ['Pull'], id=mine.LEVER_LOC.north.down, effect=lambda op: scene.say('The lever is now down.'))
    expect(run_wait(mine.set_lever('north', 'up', scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Lever', ['Pull'], id=mine.LEVER_LOC.north.down, effect=lambda op: scene.say('The lever is now up.'))
    expect(run_wait(mine.set_lever('north', 'up', scene.log))).to_be(True)
    expect(scene.logged('north lever is now up')).to_be(True)


test('lever state is confirmed by the server message rather than the temporary loc model', lever)


def doors():
    scene = Scene(FC_LOC.MINE_LANDING)
    door = mine.DOOR.i2h1
    expect(run_wait(mine.cross_door(door, 'outside', scene.log))).to_be('failed')
    scene.walk_ok = False
    expect(run_wait(mine.cross_door(door, 'main', scene.log))).to_be('failed')
    scene.walk_ok = True
    expect(run_wait(mine.cross_door(door, 'main', scene.log))).to_be('failed')
    scene.loc('Door', ['Open'], effect=lambda op: False)
    expect(run_wait(mine.cross_door(door, 'main', scene.log))).to_be('failed')
    scene.locs = []
    scene.loc('Door', ['Open'])
    expect(run_wait(mine.cross_door(door, 'main', scene.log))).to_be('failed')
    scene.locs = []
    scene.loc('Door', ['Open'], effect=lambda op: scene.say('This door is locked'))
    expect(run_wait(mine.cross_door(door, 'main', scene.log))).to_be('locked')
    scene.locs = []
    scene.loc('Door', ['Open'], effect=lambda op: setattr(scene, 'at', Tile(2730, 9690, 0)))
    expect(run_wait(mine.cross_door(door, 'main', scene.log))).to_be('crossed')


test('mine doors distinguish failed clicks, locked combinations and a crossed region', doors)


def lever_chain():
    scene = Scene(FC_LOC.MINE_LANDING)
    scene.region = 'main'
    patch(mine, 'mine_region', lambda tile: scene.region)
    calls = []
    scene.fail_at = 1

    def lever(key, state, log):
        calls.append(('lever', key, state))
        return len(calls) < scene.fail_at
        yield

    def cross(door, region, log):
        calls.append(('door', door.label, region))
        return 'crossed' if len(calls) < scene.fail_at else 'locked'
        yield

    spy_on(mine, 'set_lever', impl=lever)
    spy_on(mine, 'cross_door', impl=cross)
    for failure in range(1, 14):
        calls.clear()
        scene.fail_at = failure
        expect(run_wait(mine.reach_perfect_gold(scene.log))).to_be(False)
        expect(len(calls) >= failure).to_be(True)
    scene.fail_at = 100
    calls.clear()
    expect(run_wait(mine.reach_perfect_gold(scene.log))).to_be(True)
    expect(calls[0]).to_equal(('lever', 'north', 'up'))
    expect(calls[-1]).to_equal(('door', mine.DOOR.i2h1.label, 'main'))
    for region, expected in [['gold', True], ['outside', False], ['north_room', True], ['south', True]]:
        scene.region = region
        calls.clear()
        expect(run_wait(mine.reach_perfect_gold(scene.log))).to_be(expected)


test('the perfect-gold route checks every lever and door and recovers from either side room', lever_chain)


def mine_entry_exit():
    scene = Scene(FC_LOC.MINE_LANDING)
    scene.region = 'outside'
    patch(mine, 'mine_region', lambda tile: scene.region)
    scene.loc_op_status = 'unreachable'
    expect(run_wait(mine.enter_gold_mine(scene.log))).to_be(False)
    scene.loc_op_status = 'done'
    expect(run_wait(mine.enter_gold_mine(scene.log))).to_be(False)
    scene.loc_op_effect = lambda *args: setattr(scene, 'region', 'main')
    expect(run_wait(mine.enter_gold_mine(scene.log))).to_be(True)
    expect(run_wait(mine.enter_gold_mine(scene.log))).to_be(True)
    cross = spy_on(mine, 'cross_door', impl=answer('locked'))
    for region in ['gold', 'north_room', 'south']:
        scene.region = region
        expect(run_wait(mine.leave_gold_mine(scene.log))).to_be(False)
    scene.region = 'main'
    scene.loc_op_effect = lambda *args: setattr(scene, 'region', 'outside')
    expect(run_wait(mine.leave_gold_mine(scene.log))).to_be(True)
    expect(run_wait(mine.leave_gold_mine(scene.log))).to_be(True)


test('the mine ladder can be used only after returning to its main region', mine_entry_exit)


def ore_and_bars():
    scene = Scene(FC_LOC.MINE_LANDING)
    route = spy_on(mine, 'reach_perfect_gold', impl=answer(False))
    expect(run_wait(mine.mine_perfect_gold(scene.log))).to_be(False)
    route.mock_implementation(answer(True))
    inside = spy_on(mine, 'in_perfect_gold_zone', returns=False)
    scene.walk_ok = False
    expect(run_wait(mine.mine_perfect_gold(scene.log))).to_be(False)
    scene.walk_ok = True
    inside.mock_return_value(True)
    expect(run_wait(mine.mine_perfect_gold(scene.log))).to_be(False)
    scene.loc('Rock', ['Mine'], id=2098, effect=lambda op: False)
    expect(run_wait(mine.mine_perfect_gold(scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Rock', ['Mine'], id=2098, effect=give(scene, FC_ID.PERFECT_GOLD_ORE))
    expect(run_wait(mine.mine_perfect_gold(scene.log))).to_be(True)
    expect(run_wait(mine.mine_perfect_gold(scene.log))).to_be(True)
    scene.walk_ok = False
    expect(run_wait(mine.smelt_perfect_bars(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(mine.smelt_perfect_bars(scene.log))).to_be(False)
    scene.loc('Furnace')
    expect(run_wait(mine.smelt_perfect_bars(scene.log))).to_be(False)
    scene.take(FC_ID.PERFECT_GOLD_ORE)

    def smelt(target):
        scene.take(FC_ID.PERFECT_GOLD_ORE)
        scene.item(FC_ID.PERFECT_GOLD_BAR, FC_ITEM.PERFECT_GOLD_BAR)

    scene.item(FC_ID.PERFECT_GOLD_ORE, 'Ore', on_use=smelt)
    expect(run_wait(mine.smelt_perfect_bars(scene.log))).to_be(True)
    expect(run_wait(mine.smelt_perfect_bars(scene.log))).to_be(True)


test('perfect gold is mined inside its zone and smelting consumes the ore', ore_and_bars)


def jewellery():
    scene = Scene(mine.FURNACE_STAND)
    expect(run_wait(mine.craft_perfect_jewellery(scene.log))).to_be(False)
    scene.item(FC_ID.PERFECT_GOLD_BAR, 'Bar')
    expect(run_wait(mine.craft_perfect_jewellery(scene.log))).to_be(False)
    scene.item(FC_ID.RUBY, 'Ruby')
    scene.walk_ok = False
    expect(run_wait(mine.craft_perfect_jewellery(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(mine.craft_perfect_jewellery(scene.log))).to_be(False)
    scene.loc('Furnace')
    expect(run_wait(mine.craft_perfect_jewellery(scene.log))).to_be(False)
    spy_on(chat_dialog, 'is_main_make_panel', returns=True)
    make = spy_on(chat_dialog, 'make_from_panel', impl=answer(False))
    spy_on(chat_dialog, 'main_make_products', returns=['Gold ring'])
    expect(run_wait(mine.craft_perfect_jewellery(scene.log))).to_be(False)
    make.mock_implementation(answer(True))
    expect(run_wait(mine.craft_perfect_jewellery(scene.log))).to_be(False)

    def crafted(product, op):
        expect(op).to_be('Make')
        id = FC_ID.PERFECT_RUBY_RING if product == 'Ruby ring' else FC_ID.PERFECT_RUBY_NECKLACE
        scene.item(id, product)
        return True
        yield

    make.mock_implementation(crafted)
    expect(run_wait(mine.craft_perfect_jewellery(scene.log))).to_be(True)
    expect(run_wait(mine.craft_perfect_jewellery(scene.log))).to_be(True)


test('perfect jewellery selects Ruby ring and Ruby necklace and checks the actual output ids', jewellery)


def chronozon_finish():
    scene = Scene(demon.SAFESPOT)
    spy_on(game, 'set_auto_retaliate', returns=None)
    expect(run_wait(demon.combine_crest(scene.log))).to_be(False)
    scene.item(FC_ID.CREST_FROM_CALEB, 'Part', on_use=lambda target: False)
    scene.item(FC_ID.CREST_FROM_AVAN, 'Part')
    expect(run_wait(demon.combine_crest(scene.log))).to_be(False)
    scene.take(FC_ID.CREST_FROM_CALEB)
    scene.item(FC_ID.CREST_FROM_CALEB, 'Part', on_use=give(scene, FC_ID.FAMILY_CREST))
    expect(run_wait(demon.combine_crest(scene.log))).to_be(True)
    expect(run_wait(demon.combine_crest(scene.log))).to_be(True)
    take = spy_on(demon, 'take_safespot', impl=answer(False))
    walk = spy_on(demon, 'walk_to_chronozon', impl=answer(False))
    expect(run_wait(demon.fight_chronozon(scene.log))).to_be(False)
    take.mock_implementation(answer(True))
    blast = spy_on(demon, '_cast_blast', impl=answer('nospell'))
    expect(run_wait(demon.fight_chronozon(scene.log))).to_be(False)
    blast.mock_implementation(answer('gone'))
    expect(run_wait(demon.fight_chronozon(scene.log))).to_be(False)
    blast.mock_implementation(answer('blocked'))
    expect(run_wait(demon.fight_chronozon(scene.log))).to_be(False)
    blast.mock_implementation(answer('missed'))
    expect(run_wait(demon.fight_chronozon(scene.log))).to_be(False)
    blast.mock_implementation(answer('landed'))
    scene.on_ground(FC_ID.CREST_FROM_CHRONOZON, FC_ITEM.CREST_PART)
    expect(run_wait(demon.fight_chronozon(scene.log))).to_be(True)
    expect(scene.has(FC_ID.CREST_FROM_CHRONOZON)).to_be(True)
    expect(run_wait(demon.fight_chronozon(scene.log))).to_be(True)


test('Chronozon requires landed blasts and the last crest before all fragments combine', chronozon_finish)
