"""Ported from rs2b0t's src/bot/../../test/scripts/accountLevelerZanaris.test.ts (MIT, see thirdparty/rs2b0t)."""
from bots.account_leveler.record import Record
from bots.account_leveler.zanaris import enter_dragon_shop, game_zanaris_port, leave_zanaris
from bots.account_leveler.dragon_weapons import audit_dragon_weapons
from bots.account_leveler.planner import enabled_skills

def snapshot():
    return Record({'levels': {_k: _v for _k, _v in [[skill, 60] for skill in enabled_skills]}, 'target': 60, 'now': 1000, 'bank_ready': True, 'wilderness': False, 'quests': Record({'Lost City': True}), 'stock': Record({'coins': 1000000, 'diamond': 1, 'dramen staff': 1})})

def _fn1(*_args):
    s = snapshot()
    s.stock['coins'] = 150000
    expect(audit_dragon_weapons(s).needs).to_equal([Record({'item': 'Dragon longsword', 'count': 1}), Record({'item': 'Dragon dagger', 'count': 1})])
    expect(audit_dragon_weapons(s).budget + audit_dragon_weapons(s).reserve).to_be_less_than_or_equal(s.stock.get('coins'))
    s.stock['dragon dagger'] = 1
    expect(audit_dragon_weapons(s).needs).to_equal([Record({'item': 'Dragon longsword', 'count': 1})])
    s.stock['dragon longsword'] = 1
    expect(audit_dragon_weapons(s).needs).to_equal([])
test('weapon audit buys both once at Attack 60 while preserving the existing cash reserve', _fn1)

def _fn2(*_args):
    s = snapshot()
    s.levels['attack'] = 59
    expect(audit_dragon_weapons(s).needs).to_equal([])
    s.levels['attack'] = 60
    s.quests['Lost City'] = False
    expect(audit_dragon_weapons(s).needs).to_equal([])
    s.quests['Lost City'] = True
    s.stock.pop('diamond', None)
    expect(' '.join(audit_dragon_weapons(s).skipped)).to_contain('Diamond')
    s.stock['diamond'] = 1
    s.stock['coins'] = 200
    expect(audit_dragon_weapons(s).needs).to_equal([])
    s.stock['coins'] = 1000000
    s.unavailable_items = ['dragon dagger', 'dragon longsword']
    expect(audit_dragon_weapons(s).needs).to_equal([])
test('weapon audit defers locked, inaccessible, failed and unaffordable purchases', _fn2)

def _fn3(*_args):
    s = snapshot()
    s.stock.pop('diamond', None)
    s.stock['uncut diamond'] = 1
    expect(audit_dragon_weapons(s).needs).to_equal([Record({'item': 'Chisel', 'count': 1}), Record({'item': 'Dragon longsword', 'count': 1}), Record({'item': 'Dragon dagger', 'count': 1})])
    s.levels['crafting'] = 42
    expect(audit_dragon_weapons(s).needs).to_equal([])
test('a usable uncut Diamond adds affordable chisel preparation before buying weapons', _fn3)

def fixture(start=None):
    state = Record({'tile': start or Tile(3200, 3169), 'diamond': 1, 'completed': True, 'teleport': False, 'staff': False})
    events = []

    def equip():
        state.staff = True
        events.append('staff')
        return True
        yield

    def teleport():
        if state.teleport:
            state.tile = Tile(3210, 3424)
            events.append('teleport')
        return state.teleport
        yield

    def walk(target):
        state.tile = target
        events.append(f'walk:{target.x},{target.z}')
        return True
        yield

    def interact(id, action=None):
        events.append(f'open:{id}')
        if id == 2406:
            state.tile = Tile(3220, 9592)
        return True
        yield

    def dialog(prefer):
        events.append(prefer[0])
        if prefer[0] == 'Okay...':
            state.diamond -= 1
            state.tile = Tile(3238, 9558)
        else:
            state.tile = Tile(3260, 3171)
        return True
        yield

    def lock():
        state.completed = False

    def no_diamond():
        state.diamond = 0

    def enable_teleport():
        state.teleport = True
    port = Record({'tile': lambda: state.tile, 'complete': lambda: state.completed, 'held': lambda name: (state.diamond if name == 'Diamond' else 1), 'wearing_staff': lambda: state.staff, 'equip_staff': equip, 'prepare_exit': lambda: resolved_wait(True), 'teleport': teleport, 'walk': walk, 'interact': interact, 'dialog': dialog, 'wait': lambda condition: resolved_wait(condition())})
    return Record({'port': port, 'events': events, 'lock': lock, 'no_diamond': no_diamond, 'teleport': enable_teleport})

def _fn11(*_args):
    f = fixture()
    _w12 = yield from enter_dragon_shop(f.port)
    expect(_w12).to_be(True)
    _w13 = yield from leave_zanaris(f.port)
    expect(_w13).to_be(True)
    expect(f.events).to_equal(['staff', 'walk:3201,3169', 'open:2406', 'walk:3237,9558', 'open:2411', 'Okay...', 'walk:3252,9572', 'walk:3253,9592', 'open:2410', "Yes, I'm ready to leave."])
test('shop access equips the staff, pays one gate tax and leaves through the dialogue ladder', _fn11)

def _fn14(*_args):
    f = fixture(Record({'x': 3252, 'z': 9572, 'level': 0}))
    f.no_diamond()
    _w15 = yield from enter_dragon_shop(f.port)
    expect(_w15).to_be(True)
    expect(f.events).to_equal(['walk:3252,9572'])
test('an account already inside the market does not pay another diamond', _fn14)

def _fn16(*_args):
    locked = fixture()
    locked.lock()
    _w17 = yield from enter_dragon_shop(locked.port)
    expect(_w17).to_be(False)
    expect(locked.events).to_equal([])
    no_tax = fixture(Record({'x': 3220, 'z': 9592, 'level': 0}))
    no_tax.no_diamond()
    _w18 = yield from enter_dragon_shop(no_tax.port)
    expect(_w18).to_be(False)
    expect(no_tax.events).to_equal([])
test('unknown completion never enters Zanaris and missing tax never opens the market door', _fn16)

def _fn19(*_args):
    f = fixture(Record({'x': 3220, 'z': 9592, 'level': 0}))
    f.teleport()
    f.no_diamond()
    _w20 = yield from leave_zanaris(f.port)
    expect(_w20).to_be(True)
    expect(f.events).to_equal(['teleport'])
test('a prepared teleport leaves the city without spending a Diamond', _fn19)

def _fn21(*_args):
    pack = [Record({'Logs': 27, 'Tinderbox': 1})]
    used = [28]

    def _fn22():
        pack[0] = Record({})
        used[0] = 0
        if False:
            yield

    def _fn23(name, count):
        if used[0] == 28:
            return False
        pack[0][name] = count
        used[0] += 1
        return True
        if False:
            yield

    def _fn24(condition, *_args):
        return condition()
        if False:
            yield
    patches = [spy_on(quests, 'status').mock_return_value('complete'), spy_on(bank, 'is_open').mock_return_value(True), spy_on(bank, 'wait_ready').mock_implementation(lambda *args, **kwargs: resolved_wait(True)), spy_on(bank, 'set_note_mode').mock_implementation(lambda *args, **kwargs: resolved_wait(None)), spy_on(bank, 'deposit_inventory').mock_implementation(_fn22), spy_on(bank, 'count').mock_implementation(lambda name: (1 if name == 'Diamond' else 0)), spy_on(bank, 'withdraw_x').mock_implementation(_fn23), spy_on(bank, 'close').mock_implementation(lambda *args, **kwargs: resolved_wait(True)), spy_on(inventory, 'used').mock_implementation(lambda: used[0]), spy_on(inventory, 'count').mock_implementation(lambda name: (pack[0].get(name) if pack[0].get(name) is not None else 0)), spy_on(skills, 'level').mock_return_value(1), spy_on(execution, 'delay_until').mock_implementation(_fn24)]
    try:
        _w25 = yield from game_zanaris_port(lambda *_args: None).prepare_exit()
        expect(_w25).to_be(True)
        expect(pack[0]).to_equal(Record({'Diamond': 1}))
    except Exception as e:
        for patch in patches:
            restore_all()
        raise e
    for patch in patches:
        restore_all()
test('exit preparation banks a full pack before withdrawing its travel item', _fn21)

def resolved_wait(value):
    if False:
        yield
    return value
