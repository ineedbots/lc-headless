"""Ported from rs2b0t's test/api/ai/quests/regicideBridgeGear.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.game import game, skills
from rs2004.geometry import Tile
from rs2004.items import equipment, inventory
from rs2004.quests.defs.regicide import pass_ as rg_pass


def item(id, name, slot):
    return Fake(id=id, name=name, slot=slot, count=1)


def succeed(log, *rest):
    return True
    yield


def fail(log, *rest):
    return False
    yield


def install(state):
    spy_on(equipment, 'items', impl=lambda: state.worn)
    spy_on(inventory, 'items', impl=lambda: state.pack)
    spy_on(game, 'tile', impl=lambda: state.tile)
    spy_on(skills, 'level', returns=99)
    patch(rg_pass, 'make_fire_arrow', succeed)

    def arm(log, bows):
        state.pack = list(state.pack) + [i for i in state.worn if i.slot == 3 or i.slot == 5]
        state.worn = [i for i in state.worn if i.slot != 3 and i.slot != 5] + [item(859, 'Magic longbow', 3)]
        return True
        yield

    patch(rg_pass, 'arm_fire_arrow', arm)

    def equip(name):
        if state.locked or not any([i.name == name for i in state.pack]):
            return False
        restored = item(1333, name, 3) if name == 'Rune scimitar' else item(1189, name, 5)
        state.pack = [i for i in state.pack if i.name != name]
        state.worn = [i for i in state.worn if i.slot != restored.slot] + [restored]
        return True
        yield

    spy_on(equipment, 'equip', impl=equip)
    rg_pass.bridge_gear = []


def names(state):
    return sorted([i.name for i in state.worn])


def _fn1(crossed):
    state = Record({
        'worn': [item(1333, 'Rune scimitar', 3), item(1189, 'Bronze kiteshield', 5), item(1129, 'Leather body', 4)],
        'pack': [item(942, 'Lit arrows', 0)],
        'tile': Tile(2450, 9716, 0),
        'locked': False,
    })
    install(state)
    patch(rg_pass, 'shoot_guiderope', succeed if crossed else fail)
    result = yield from rg_pass.enter_tirannwn(lambda *args: None)
    expect(result).to_be(crossed)
    expect(names(state)).to_equal(['Bronze kiteshield', 'Leather body', 'Rune scimitar'])


test_each([True, False])('restores the chosen weapon and shield after the bridge shot returns %s', _fn1)


def _fn2(missing):
    state = Record({
        'worn': [item(1333, 'Rune scimitar', 3), item(1189, 'Bronze kiteshield', 5)],
        'pack': [item(942, 'Lit arrows', 0)],
        'tile': Tile(2450, 9716, 0),
        'locked': True,
    })
    install(state)
    patch(rg_pass, 'cross_grid', fail)
    patch(rg_pass, 'shoot_guiderope', fail)
    first = yield from rg_pass.enter_tirannwn(lambda *args: None)
    expect(first).to_be(False)
    state.locked = False
    if missing:
        state.worn = [item(1333, 'Rune scimitar', 3)]
        state.pack = []
    state.tile = Tile(2442, 9716, 0)
    second = yield from rg_pass.enter_tirannwn(lambda *args: None)
    expect(second).to_be(True)
    expect(names(state)).to_equal((['Rune scimitar'] if missing else ['Bronze kiteshield', 'Rune scimitar']))


test_each([False, True])('recovers after a bridge equip lock, with the shield subsequently missing: %s', _fn2)
