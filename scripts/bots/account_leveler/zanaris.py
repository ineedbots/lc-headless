from rs2004.geometry import Tile
"""Ported from rs2b0t's src/bot/scripts/AccountLeveler/zanaris.ts (MIT, see thirdparty/rs2b0t)."""

from bots.account_leveler.record import Record
from rs2004.quests.exec.primitives import drive_dialog

__all__ = ['in_zanaris', 'in_dragon_market', 'open_zanaris_bank', 'cut_travel_diamond', 'game_zanaris_port', 'enter_dragon_shop', 'leave_zanaris']

from bots.account_leveler.travel import leveler_travel_zones
SHED = Tile(3201, 3169, 0)
GATE = Tile(3237, 9558, 0)
SHOP = Tile(3252, 9572, 0)
LADDER = Tile(3253, 9592, 0)
BANK = Tile(3153, 9576, 0)
TELEPORT_RUNES = [
    Record({'name': 'Law rune', 'count': 1}),
    Record({'name': 'Air rune', 'count': 3}),
    Record({'name': 'Fire rune', 'count': 1}),
]


def in_zanaris(tile):
    return tile is not None and tile.level == 0 and tile.x >= 3150 and tile.x <= 3300 and tile.z >= 9450 and tile.z <= 9700


def in_dragon_market(tile):
    return in_zanaris(tile) and tile.x >= 3238


def open_zanaris_bank(log):
    if quests.status('Lost City') != 'complete':
        return False
    if bank.is_open():
        _result1 = yield from bank.wait_ready()
        return _result1
    _w2 = yield from traversal.walk_resilient(BANK, radius=3, timeout_ms=120000, avoid_zones=leveler_travel_zones(), log=log)
    if not (_w2):
        return False
    _w4 = yield from bank.open_npc_access({'name': 'Banker', 'op': 'Bank'}, log)
    _c3 = _w4
    if _c3:
        _w5 = yield from bank.wait_ready()
        _c3 = _w5
    return _c3


def cut_travel_diamond():
    if inventory.count('Diamond') > 0:
        return True
    if skills.level('crafting') < 43:
        return False
    chisel = ([item for item in inventory.items() if item.name == 'Chisel' and not item.noted] or [None])[0]
    uncut = ([item for item in inventory.items() if item.name == 'Uncut diamond' and not item.noted] or [None])[0]
    _c6 = not not chisel and not not uncut and chisel.use_on(uncut)
    if _c6:
        _w7 = yield from execution.delay_until(lambda: inventory.count('Diamond') > 0, 5000)
        _c6 = _w7
    return _c6


def game_zanaris_port(log):
    def _fn8():
        _w9 = yield from open_zanaris_bank(log)
        if not (_w9):
            return False
        yield from bank.set_note_mode(False)
        yield from bank.deposit_inventory()
        _w10 = yield from execution.delay_until(lambda: inventory.used() == 0, 4000)
        if not (_w10):
            return False
        teleport = skills.level('magic') >= 25 and all([inventory.count(item.name) + bank.count(item.name) >= item.count for item in TELEPORT_RUNES])
        needs = (TELEPORT_RUNES if teleport else ([Record({'name': 'Diamond', 'count': 1})] if bank.count('Diamond') + inventory.count('Diamond') > 0 else ([Record({'name': 'Chisel', 'count': 1}), Record({'name': 'Uncut diamond', 'count': 1})] if skills.level('crafting') >= 43 else [])))
        if not len(needs):
            log('Cannot leave Zanaris: need a Diamond or Varrock teleport runes and Magic 25')
            return False
        for need in needs:
            missing = need.count - inventory.count(need.name)
            _c11 = missing > 0
            if _c11:
                _w12 = yield from bank.withdraw_x(need.name, missing)
                _c11 = not (_w12)
            if _c11:
                log(f'Cannot leave Zanaris: missing {need.name}')
                return False
        _w13 = yield from bank.close()
        if not (_w13):
            return False
        _c14 = teleport
        if not _c14:
            _w15 = yield from cut_travel_diamond()
            _c14 = _w15
        return _c14

    def _fn16():
        if skills.level('magic') < 25 or not all([inventory.count(item.name) >= item.count for item in TELEPORT_RUNES]):
            return False
        result = yield from game.teleport('Varrock')
        return result
        if False:
            yield


    def _fn17(id, action):
        loc = locs.query().where(lambda loc: loc.id == id).action(action).within(5).nearest()
        return not not loc and loc.interact(action)
        if False:
            yield

    return Record({
        'tile': lambda: game.tile(),
        'complete': lambda: quests.status('Lost City') == 'complete',
        'held': lambda name: inventory.count(name),
        'wearing_staff': lambda: any([item.name == 'Dramen staff' for item in equipment.items()]),
        'equip_staff': lambda: equipment.equip('Dramen staff'),
        'prepare_exit': _fn8,
        'teleport': _fn16,
        'walk': lambda tile: traversal.walk_resilient(Tile.from_tile(tile), radius=0, attempts=2, timeout_ms=120000, avoid_zones=leveler_travel_zones(), log=log),
        'interact': _fn17,
        'dialog': lambda prefer: drive_dialog(prefer, log),
        'wait': lambda condition: execution.delay_until(condition, 15000),
    })


def enter_market(port):
    if in_dragon_market(port.tile()):
        return True
    _c18 = not port.complete() or port.held('Diamond') < 1
    if not _c18:
        _w19 = yield from port.walk(GATE)
        _c18 = not (_w19)
    if _c18:
        return False
    _w21 = yield from port.interact(2411, 'Open')
    _c20 = not (_w21)
    if not _c20:
        _w22 = yield from port.dialog(['Okay...'])
        _c20 = not (_w22)
    if _c20:
        return False
    _result23 = yield from port.wait(lambda: in_dragon_market(port.tile()))
    return _result23


def enter_dragon_shop(port):
    if not port.complete():
        return False
    if not in_zanaris(port.tile()):
        _c24 = not port.wearing_staff()
        if _c24:
            _c25 = port.held('Dramen staff') < 1
            if not _c25:
                _w26 = yield from port.equip_staff()
                _c25 = not (_w26)
            _c24 = (_c25)
        if _c24:
            return False
        _w29 = yield from port.walk(SHED)
        _c28 = not (_w29)
        if not _c28:
            _w30 = yield from port.interact(2406, 'Open')
            _c28 = not (_w30)
        _c27 = _c28
        if not _c27:
            _w31 = yield from port.wait(lambda: in_zanaris(port.tile()))
            _c27 = not (_w31)
        if _c27:
            return False
    _w33 = yield from enter_market(port)
    _c32 = _w33
    if _c32:
        _w34 = yield from port.walk(SHOP)
        _c32 = _w34
    return _c32


def leave_zanaris(port):
    if not in_zanaris(port.tile()):
        return True
    _c35 = not in_dragon_market(port.tile()) and port.held('Diamond') < 1
    if _c35:
        _w36 = yield from port.prepare_exit()
        _c35 = not (_w36)
    if _c35:
        return False
    _w37 = yield from port.teleport()
    if _w37:
        _result38 = yield from port.wait(lambda: not in_zanaris(port.tile()))
        return _result38
    _w41 = yield from enter_market(port)
    _c40 = not (_w41)
    if not _c40:
        _w42 = yield from port.walk(LADDER)
        _c40 = not (_w42)
    _c39 = _c40
    if not _c39:
        _w43 = yield from port.interact(2410, 'Climb-up')
        _c39 = not (_w43)
    if _c39:
        return False
    _w44 = yield from port.dialog(["Yes, I'm ready to leave."])
    if not (_w44):
        return False
    _result45 = yield from port.wait(lambda: not in_zanaris(port.tile()))
    return _result45
