"""Gear, potions, food and the bank trip that lays out the shared loadout: rs2b0t's scripts/JiveKQ/supply.ts (MIT,
see thirdparty/rs2b0t). The Wait functions are used with yield from."""

from rs2004.catalogs import boost_faded
from bots.jivekq.loadout import AIR, ARROWS, BOW, DUELING_RINGS, FOOD, GEAR, LAW, PASS, trip_pack
from bots.jivekq.policy import BANK, Supplies
from bots.jivekq.route import buy_pass

BOOSTS = [('defence', 'Super defence'), ('attack', 'Super attack'), ('strength', 'Super strength')]
COINS = 995
PRAYER_POTION = 2434


def worn(id):
    return any([i.id == id for i in equipment.items()])


def _wield_op(item):
    for op in item.actions():
        lower = op.lower()
        if 'wield' in lower or 'wear' in lower:
            return op
    return None


def send_equip(id):
    """Sends the wield click for an item in the pack, not waited on."""
    item = None
    for i in inventory.items():
        if i.id == id:
            item = i
            break
    op = _wield_op(item) if item is not None else None
    return op is not None and item.interact(op)


def equip(id):
    if worn(id):
        return True
    if bank.is_open():
        closed = yield from bank.close()
        if not closed:
            return False
    if not send_equip(id):
        return False
    on = yield from execution.delay_until(lambda: worn(id), 2500)
    return on


def _dose_count(name):
    open_at = name.find('(')
    if open_at < 0 or open_at + 2 >= len(name) or name[open_at + 2] != ')':
        return 0
    digit = name[open_at + 1]
    return int(digit) if digit in '0123456789' else 0


def doses(prefix):
    return sum([_dose_count(i.name) * i.count for i in inventory.items() if (i.name or '').startswith(prefix)])


def drink(prefix):
    flasks = [i for i in inventory.items() if (i.name or '').startswith(prefix) and 'Drink' in i.actions()]
    flasks.sort(key=lambda i: i.id)
    if not flasks:
        return False
    before = doses(prefix)
    if not flasks[0].interact('Drink'):
        return False
    drank = yield from execution.delay_until_ticks(lambda: doses(prefix) < before, 3)
    if not drank:
        return False
    yield from execution.delay_ticks(2)
    return True


def send_eat():
    """Sends an Eat click on a shark, not waited on."""
    for i in inventory.items():
        if i.id == FOOD:
            return i.interact('Eat')
    return False


def eat():
    before = inventory.count_by_id(FOOD)
    if not send_eat():
        return False
    ate = yield from execution.delay_until_ticks(lambda: inventory.count_by_id(FOOD) < before, 2)
    return ate


def boost(melee):
    """Drinks the first super potion whose boost has faded; only defence when the phase is ranged."""
    for skill, potion in BOOSTS:
        if not melee and skill != 'defence':
            continue
        if boost_faded(skills.level(skill), skills.effective(skill)) and doses(potion) > 0:
            drank = yield from drink(potion)
            return drank
    return False


def boosts_ready():
    return all([skills.effective(skill) > skills.level(skill) * 1.1 for skill, _ in BOOSTS])


def quiver_count():
    for i in equipment.items():
        if i.id == ARROWS:
            return i.count
    return 0


def supplies():
    escape = any([i.id in DUELING_RINGS for i in inventory.items()]) and inventory.count_by_id(AIR) >= 5 and inventory.count_by_id(LAW) >= 1
    return Supplies(hp=skills.effective('hitpoints'), food=inventory.count_by_id(FOOD), prayer=prayer.points(), prayer_doses=doses('Prayer potion'),
                    escape=escape, arrows=quiver_count())


class BankInterrupted(Exception):
    pass


class BankShortage(Exception):
    pass


def _open(log):
    opened = yield from banking.open(stand=BANK, prefer_nearby=False, log=log)
    if not opened:
        return False
    ready = yield from bank.wait_ready(5000)
    return ready


def _bank_ready():
    ready = yield from bank.wait_ready(5000)
    if not ready:
        raise BankInterrupted()


def _withdraw(id, count):
    yield from _bank_ready()
    need = count - inventory.count_by_id(id)
    if need <= 0:
        return
    if bank.count_by_id(id) < need:
        raise BankShortage(f'KQ bank needs {need} more of item {id}')
    took = yield from bank.withdraw_x_by_id(id, need)
    if not took:
        yield from _bank_ready()
        raise RuntimeError(f'KQ could not withdraw item {id}')


def provision(slot, log, wait_for_gear=False):
    """Lays out the trip; False to try again. With wait_for_gear, a bank short of gear another account is still
    carrying home waits rather than stopping."""
    try:
        done = yield from _prepare(slot, log, wait_for_gear)
        return done
    except BankShortage:
        if wait_for_gear:
            return False
        raise
    except BankInterrupted:
        log('bank: interrupted, retrying KQ supplies')
        return False


def _deposit_all():
    yield from bank.deposit_all_matching(lambda name, id: True)


def _prepare(slot, log, wait_for_gear):
    pack = trip_pack(slot)
    food = [count for id, count in pack if id == FOOD][0]
    yield from prayer.clear()
    opened = yield from _open(log)
    if not opened:
        return False
    yield from _deposit_all()
    if wait_for_gear and any([not worn(id) and bank.count_by_id(id) == 0 for id in GEAR + [BOW]]):
        return False
    yield from bank.close()
    for item in equipment.items():
        if item.id not in GEAR:
            off = yield from equipment.unequip(item.name or '')
            if not off:
                raise RuntimeError(f'Cannot remove {item.name}')
    opened = yield from _open(log)
    if not opened:
        return False
    yield from _deposit_all()
    yield from bank.set_note_mode(False)
    for id in GEAR:
        if not worn(id):
            yield from _withdraw(id, 250 if id == ARROWS else 1)
    yield from bank.close()
    for id in GEAR:
        on = yield from equip(id)
        if not on:
            raise RuntimeError(f'Cannot equip KQ item {id}; check level and quest requirements')
    while skills.effective('hitpoints') < skills.level('hitpoints') - 5 or prayer.points() < prayer.max() - 5:
        opened = yield from _open(log)
        if not opened:
            return False
        if skills.effective('hitpoints') < skills.level('hitpoints') - 5:
            yield from _withdraw(FOOD, 1)
        if prayer.points() < prayer.max() - 5:
            yield from _withdraw(PRAYER_POTION, 1)
        yield from bank.close()
        if inventory.count_by_id(FOOD) > 0:
            ate = yield from eat()
            if not ate:
                return False
        if prayer.points() < prayer.max() - 5:
            drank = yield from drink('Prayer potion')
            if not drank:
                return False
    opened = yield from _open(log)
    if not opened:
        return False
    yield from _deposit_all()
    arrows = quiver_count()
    if arrows < 250:
        yield from _withdraw(ARROWS, 250 - arrows)
    for id, count in pack:
        yield from _bank_ready()
        if id == PASS:
            if bank.count_by_id(PASS) > 0:
                yield from _withdraw(PASS, 1)
            else:
                yield from _withdraw(COINS, 100)
        elif id == DUELING_RINGS[0]:
            ring = None
            for r in reversed(DUELING_RINGS):
                if bank.count_by_id(r) > 0:
                    ring = r
                    break
            if ring is None:
                raise BankShortage('KQ bank needs a charged Ring of dueling')
            yield from _withdraw(ring, 1)
        else:
            yield from _withdraw(id, food - 1 if id == FOOD else count)
    yield from bank.close()
    if inventory.count_by_id(ARROWS) > 0:
        send_equip(ARROWS)
        yield from execution.delay_until(lambda: inventory.count_by_id(ARROWS) == 0, 3000)
    bought = yield from buy_pass(log)
    if not bought:
        return False
    opened = yield from _open(log)
    if not opened:
        return False
    yield from bank.deposit_all_matching(lambda name, id: name == 'Coins')
    yield from _withdraw(FOOD, food)
    yield from bank.close()
    stocked = all([supplies().escape if id == DUELING_RINGS[0] else inventory.count_by_id(id) >= count for id, count in pack])
    return inventory.count_by_id(COINS) == 0 and all([worn(id) for id in GEAR]) and stocked
