"""Ported from rs2b0t's src/bot/scripts/AccountLeveler/supplies.ts (MIT, see thirdparty/rs2b0t)."""

from bots.account_leveler.record import Record
from rs2004.catalogs.shops import unit_price
from rs2004.bank import bank as bank_api
from rs2004.traversal import nearest_bank_reachable
from bots.account_leveler.travel import leveler_travel_zones
from bots.account_leveler.zanaris import cut_travel_diamond, enter_dragon_shop, game_zanaris_port, in_dragon_market, in_zanaris, leave_zanaris, open_zanaris_bank

__all__ = ['SupplyUnavailableError', 'SupplyStockError', 'stock_counts', 'game_supply_port', 'provision']

from bots.account_leveler.offers import purchase_budget, supply_offer, supply_offers
from bots.account_leveler.shopping import SHOPPING_RESERVE, shopping_stops
from bots.account_leveler.types import requirement_key
from bots.account_leveler.vials import fill_supply_vials, VIAL_FOUNTAIN
class SupplyUnavailableError(Exception):
    def __init__(self, message, items):
        Exception.__init__(self, message + '\nUnavailable items: ' + '|'.join(sorted(set([item.lower() for item in items]))))

    @property
    def items(self):
        return str(self).split('\nUnavailable items: ')[1].split('|')


class SupplyStockError(SupplyUnavailableError):
    pass


def stock_counts(items):
    result = Record({})
    for item in items:
        if item.noted:
            continue
        for key in [f'#{item.id}'] + list((([item.name.lower()] if item.name else []))):
            value = result.get(key)
            result[key] = ((value if value is not None else 0)) + item.count
    return result


def game_supply_port(log):
    def open_bank():
        if in_dragon_market(game.tile()):
            returned = yield from leave_zanaris(game_zanaris_port(log))
            if not returned:
                return False
        if in_zanaris(game.tile()):
            opened = yield from open_zanaris_bank(log)
            if not opened:
                return False
            yield from bank_api.set_note_mode(False)
            return True
        if bank_api.ready():
            return True
        destination = nearest_bank_reachable(game.tile(), navigator)
        if destination is None:
            return False
        tile = destination['tile']
        stand = Tile(tile['x'], tile['z'], tile.get('level', 0))
        opened = yield from banking.open(stand=stand, prefer_nearby=False, log=log, avoid_zones=leveler_travel_zones())
        if not opened:
            return False
        ready = yield from bank_api.wait_ready()
        if not ready:
            return False
        yield from bank_api.set_note_mode(False)
        return True

    def deposit():
        yield from bank_api.deposit_inventory()
        emptied = yield from execution.delay_until(lambda: inventory.used() == 0, 4000)
        if not emptied:
            raise RuntimeError('Inventory did not empty at the bank')

    def count_held(name):
        return stock_counts(inventory.items()).get(name.lower(), 0)

    def count_worn(name):
        return stock_counts(equipment.items()).get(name.lower(), 0)

    def withdraw(name, count):
        if name.startswith('#'):
            result = yield from bank_api.withdraw_x_by_id(int(name[1:]), count)
            return result
        result = yield from bank_api.withdraw_x(name, count)
        return result

    def shop_stock(name):
        # The facade finds the open shop's inventory for every revision.
        for item in shop.stock():
            if item.id == int(name[1:]) if name.startswith('#') else item.name.lower() == name.lower():
                return item.count
        return 0

    def buy(name, count):
        if name.startswith('#'):
            result = yield from shop.buy_by_id(int(name[1:]), count)
            return result
        result = yield from shop.buy(name, count)
        return result

    def equip(name):
        if not name.startswith('#'):
            result = yield from equipment.equip(name)
            return result
        id = int(name[1:])
        if any([item.id == id for item in equipment.items()]):
            return True
        for item in inventory.items():
            if item.id != id or item.noted:
                continue
            for op in item.actions():
                if op.lower() in ['wield', 'wear', 'equip'] and item.interact(op):
                    result = yield from execution.delay_until(lambda: any([piece.id == id for piece in equipment.items()]), 3000)
                    return result
        return False

    def walk(tile):
        if not in_zanaris(tile):
            returned = yield from leave_zanaris(game_zanaris_port(log))
            if not returned:
                return False
        result = yield from traversal.walk_resilient(Tile.from_tile(tile), radius=3, timeout_ms=120000, avoid_zones=leveler_travel_zones(), log=log)
        return result

    return Record({
        'bank': open_bank, 'deposit': deposit,
        'stock': lambda: stock_counts(bank_api.items()),
        'held': count_held, 'worn': count_worn,
        'equipment': lambda: [item.name for item in equipment.items() if item.name],
        'unequip': lambda name: equipment.unequip(name), 'withdraw': withdraw,
        'close_bank': lambda: bank_api.close(),
        'walk': walk,
        'shop': lambda keeper: shop.open(keeper), 'shop_stock': shop_stock,
        'buy': buy, 'close_shop': lambda: shop.close(),
        'fill_vials': lambda count: fill_supply_vials(count, log),
        'equip': equip, 'log': log,
        'dragon_shop': Record({
            'ready': lambda: skills.level('attack') >= 60 and quests.status('Lost City') == 'complete',
            'enter': lambda: enter_dragon_shop(game_zanaris_port(log)),
            'leave': lambda: leave_zanaris(game_zanaris_port(log)),
            'cut_diamond': cut_travel_diamond,
        }),
    })


def bank(port):
    result = yield from port.bank()
    if not (result):
        raise RuntimeError('Could not open a loaded bank')


def rebase_consumables(plan, stock):
    consumables = [need for need in plan.needs if ((need.minimum if need.minimum is not None else 0)) > 0]

    def units(need):
        return (min(need.count, (stock.get(requirement_key(need).lower()) if stock.get(requirement_key(need).lower()) is not None else 0)) // need.minimum)

    missing = [need for need in consumables if units(need) == 0]
    if len(missing):
        raise SupplyStockError(f"No usable stock of {', '.join([need.item for need in missing])}", [need.item for need in missing])
    mage = plan.script == 'AutoFighter' and plan.settings['combat_style'] == 'mage'
    batch = (min([units(_x) for _x in consumables]) if mage else float('inf'))
    carried = (min(batch, *[(((need.carry if need.carry is not None else need.count)) // need.minimum) for need in consumables]) if mage else float('inf'))
    for need in consumables:
        need.count = min(units(need), batch) * need.minimum
        if need.carry is not None:
            need.carry = min(need.count, (need.carry // need.minimum) * need.minimum, carried * need.minimum)
        if plan.script == 'AutoFighter' and need.item == 'Bronze arrow':
            plan.settings['ammo_withdraw'] = (need.carry if need.carry is not None else need.count)
        if plan.script == 'LeatherCrafter' and need.item == 'Thread':
            plan.settings['thread_per_trip'] = (need.carry if need.carry is not None else need.count)
        if plan.script == 'Fisher' and need.item == 'Feather':
            plan.settings['bait_qty'] = (need.carry if need.carry is not None else need.count)
    if mage and len(consumables):
        plan.settings['runes_withdraw'] = carried


def provision(plan, port, on_progress=None, best_effort=None):
    def report(id, message, destination=None, state='running'):
        if on_progress:
            on_progress(Record({'id': id, 'message': message, 'destination': destination, 'state': state}))
        else:
            port.log(message)

    report('bank:start', 'Opening bank to prepare supplies')
    yield from bank(port)
    report('bank:start', 'Depositing inventory before checking supplies')
    yield from port.deposit()
    result = yield from port.close_bank()
    if not (result):
        raise RuntimeError('Could not close bank to remove equipment')
    for name in port.equipment():
        report('bank:start', f'Removing {name} before banking equipment')
        result = yield from port.unequip(name)
        if not (result):
            raise RuntimeError(f'Could not remove {name}')
    report('bank:start', 'Banking equipment and checking the shopping list')
    yield from bank(port)
    yield from port.deposit()
    report('bank:start', 'Bank inventory checked', None, 'done')
    for need in plan.needs:
        key = requirement_key(need)
        value = port.stock().get(key.lower())
        if ((value if value is not None else 0)) < need.count and not supply_offer(need.item):
            if not best_effort:
                raise RuntimeError(f'Need {need.count} {need.item} in bank before {plan.label}')
            report('bank:start', f'Skipping {need.item}: no shop available', None, 'done')

    def has_alternatives(need):
        return len(supply_offers(need.item)) > 1

    water = ([need for need in plan.needs if need.item.lower() == 'vial of water'] or [None])[0]
    keep_empty = max([0] + [need.count for need in plan.needs if need.item.lower() == 'vial'])
    if water and port.fill_vials:
        for attempt in range(12):
            travel_food = (plan.food if plan.food and ((port.stock().get(plan.food.lower()) if port.stock().get(plan.food.lower()) is not None else 0)) >= 3 else None)
            stock = port.stock()
            count = min(24 if travel_food else 27, water.count - stock.get(requirement_key(water).lower(), 0), stock.get('vial', 0) - keep_empty)
            if count <= 0:
                break
            report('vials:fill', f'Filling {count} banked vials at Falador fountain', VIAL_FOUNTAIN)
            value = port.stock().get('coins')
            coins = min(SHOPPING_RESERVE, (value if value is not None else 0))
            condition = coins > 0
            if condition:
                result = yield from port.withdraw('Coins', coins)
                condition = not (result)
            if condition:
                raise RuntimeError('Could not withdraw travel coins for filling vials')
            condition = travel_food
            if condition:
                result = yield from port.withdraw(travel_food, 3)
                condition = not (result)
            if condition:
                raise RuntimeError('Could not withdraw food for filling vials')
            result = yield from port.withdraw('Vial', count)
            if not (result):
                raise RuntimeError('Could not withdraw empty vials')
            result = yield from port.close_bank()
            if not (result):
                raise RuntimeError('Bank did not close before filling vials')
            before = port.held('Vial of water')
            yield from port.fill_vials(count)
            filled = port.held('Vial of water') - before
            yield from bank(port)
            yield from port.deposit()
            if filled < count:
                report('vials:fill', f'Only {filled}/{count} vials filled; trying shops')
                break
    for stop in shopping_stops(plan.needs, port.stock()):
        if stop.keeper == 'Jakut':
            yield from provision_dragon_stop(stop, port, report)
            continue
        id = f'shop:{stop.keeper}'

        def missing(need):
            return max(0, need.count - ((port.stock().get(requirement_key(need).lower()) if port.stock().get(requirement_key(need).lower()) is not None else 0)))

        allowance = {}

        def remaining(need):
            return min(missing(need), (allowance.get(requirement_key(need)) if allowance.get(requirement_key(need)) is not None else float('inf')))

        attempts = 0
        while any([remaining(need) > 0 for need in stop.needs]):
            attempts += 1
            if attempts > 12:
                if best_effort:
                    break
                raise RuntimeError(f'Supply batch exceeded at {stop.keeper}')
            travel_food = (plan.food if plan.food and ((port.stock().get(plan.food.lower()) if port.stock().get(plan.food.lower()) is not None else 0)) >= 3 else None)
            slots = (24 if travel_food else 27)

            batch = []
            for need in stop.needs:
                offer = [offer for offer in supply_offers(need.item) if offer.keeper == stop.keeper][0]
                if offer.fill_vials and not port.fill_vials:
                    allowance[requirement_key(need)] = 0
                    continue
                count = min(remaining(need), (1000 if offer.item.stackable else slots) if slots > 0 else 0)
                if count <= 0:
                    continue
                slots -= 1 if offer.item.stackable else count
                batch.append(Record({'need': need, 'offer': offer, 'count': count, 'banked': need.count - missing(need)}))
            if not len(batch):
                break
            to_fill = 0
            budget = sum([purchase_budget(entry.offer, entry.count) for entry in batch])
            coins = budget + SHOPPING_RESERVE
            value = port.stock().get('coins')
            if ((value if value is not None else 0)) < coins:
                usable = all([missing(need) == 0 or need.minimum and need.count - missing(need) >= need.minimum for need in stop.needs])
                if not best_effort and not usable:
                    raise RuntimeError(f'Not enough Coins for {stop.keeper} (budget {budget}, travel reserve {SHOPPING_RESERVE})')
                report(id, f'Skipping {stop.keeper}: insufficient Coins for budget {budget} plus travel reserve')
                break
            report(id, f"Withdrawing {coins} Coins for {stop.keeper}: {', '.join([f'{entry.count} {entry.need.item}' for entry in batch])}")
            condition = travel_food
            if condition:
                result = yield from port.withdraw(travel_food, 3)
                condition = not (result)
            if condition:
                raise RuntimeError('Could not withdraw food for shopping')
            result = yield from port.withdraw('Coins', coins)
            if not (result) or port.held('Coins') < coins:
                raise RuntimeError('Coin withdrawal did not land')
            result = yield from port.close_bank()
            if not (result):
                raise RuntimeError('Bank did not close before shopping')
            report(id, f"Travelling to {stop.keeper} for {', '.join([f'{entry.count} {entry.need.item}' for entry in batch])}", stop.tile)
            try:
                result = yield from port.walk(stop.tile)
                if not (result):
                    raise SupplyUnavailableError(f'Cannot reach {stop.keeper}', [need.item for need in stop.needs])
                reserve = max(0, SHOPPING_RESERVE - max(0, coins - port.held('Coins')))
                available_budget = min(budget, port.held('Coins') - reserve)
                report(id, f'Opening {stop.keeper}\'s shop', stop.tile)
                result = yield from port.shop(stop.keeper)
                if not (result):
                    raise SupplyUnavailableError(f'Cannot trade {stop.keeper}', [need.item for need in stop.needs])
                try:
                    for _item38 in batch:
                        need = _item38.need
                        offer = _item38.offer
                        count = _item38.count
                        banked = _item38.banked
                        key = requirement_key(need)
                        purchase_key = (offer.item.name if offer.fill_vials else key)
                        available = port.shop_stock(purchase_key)
                        limited = best_effort or need.minimum or has_alternatives(need)
                        if limited and not (key in allowance):
                            allowance[key] = available
                        if available <= 0:
                            if not limited:
                                raise SupplyStockError(f'{stop.keeper} has no stock of {need.item}', [need.item])
                            allowance[key] = 0
                            report(id, f'Skipping {need.item}: {stop.keeper} has no stock', stop.tile)
                            continue
                        amount = min(count, available)
                        cost = 0
                        for i in range(amount):
                            cost += unit_price(offer.item, offer.shop, available - i)
                        if cost > available_budget or cost > port.held('Coins') - reserve:
                            if not best_effort:
                                raise RuntimeError(f'Cannot afford {amount} {need.item} at current shop stock')
                            allowance[key] = 0
                            report(id, f'Skipping {need.item}: current shop price exceeds the purchase budget', stop.tile)
                            continue
                        report(id, f'Buying {amount} {offer.item.name} from {stop.keeper} ({banked}/{need.count} banked)', stop.tile)
                        before = port.held(purchase_key)
                        before_coins = port.held('Coins')
                        yield from port.buy(purchase_key, amount)
                        bought = max(0, port.held(purchase_key) - before)
                        if offer.fill_vials:
                            to_fill += bought
                        if not limited and bought == 0:
                            raise SupplyStockError(f'Purchase of {need.item} did not arrive', [need.item])
                        if limited:
                            allowance[key] = (0 if bought < amount else max(0, allowance.get(key) - bought))
                            if bought < amount:
                                report(id, f'Skipping the remaining {need.item}: only {bought}/{amount} purchased', stop.tile)
                        available_budget -= max(0, before_coins - port.held('Coins'))
                except Exception as e:
                    yield from port.close_shop()
                    raise e

                yield from port.close_shop()
            except Exception as error:
                fallback = isinstance(error, SupplyUnavailableError) and all([any([need.item.lower() == item and has_alternatives(need) for need in plan.needs]) for item in error.items])
                if not best_effort and not fallback and isinstance(error, SupplyStockError):
                    yield from bank(port)
                    yield from port.deposit()
                    raise error
                if (not best_effort and not fallback) or not (isinstance(error, SupplyUnavailableError)):
                    raise error
                report(id, f'{str(error)}; trying remaining suppliers')
                for need in stop.needs:
                    allowance[requirement_key(need)] = 0
            if to_fill > 0 and port.fill_vials:
                report(id, f'Filling {to_fill} vials at Falador fountain', VIAL_FOUNTAIN)
                before = port.held('Vial of water')
                yield from port.fill_vials(to_fill)
                filled = port.held('Vial of water') - before
                if filled < to_fill:
                    for need in stop.needs:
                        if need.item.lower() == 'vial of water':
                            allowance[requirement_key(need)] = 0
                    report(id, f'Only {filled}/{to_fill} vials filled; trying remaining suppliers')
            report(id, f'Banking purchases from {stop.keeper}')
            yield from bank(port)
            yield from port.deposit()
        shortages = [need for need in stop.needs if missing(need) > 0]
        if len(shortages):
            report(id, f"Deferred: {', '.join([f'{missing(need)} {need.item}' for need in shortages])}")
        report(id, f"{stop.keeper} supplies banked: {', '.join([f'{need.count - missing(need)}/{need.count} {need.item}' for need in stop.needs])}", None, 'done')
    if best_effort:
        result = yield from port.close_bank()
        if not (result):
            raise RuntimeError('Bank did not close after shopping')
        return
    shortages = [need for need in plan.needs if has_alternatives(need) and ((port.stock().get(requirement_key(need).lower()) if port.stock().get(requirement_key(need).lower()) is not None else 0)) < ((need.minimum if need.minimum is not None else need.count))]
    if len(shortages):
        raise SupplyStockError(f"Suppliers exhausted: {', '.join([need.item for need in shortages])}", [need.item for need in shortages])
    rebase_consumables(plan, port.stock())
    report('loadout', f'Packing supplies for {plan.label}')
    for need in plan.needs:
        count = (need.carry if need.carry is not None else 0)
        key = requirement_key(need)
        if count > 0:
            report('loadout', f'Withdrawing {count} {need.item} for {plan.label}')
        condition = count > 0
        if condition:
            result = yield from port.withdraw(key, count)
            condition = (not (result) or port.held(key) < count)
        if condition:
            raise RuntimeError(f'Could not withdraw {count} usable {need.item}')
    result = yield from port.close_bank()
    if not (result):
        raise RuntimeError('Bank did not close after provisioning')
    report('loadout', f'Supplies packed for {plan.label}', None, 'done')
    report('equip', f'Preparing equipment for {plan.label}')
    for need in [n for n in plan.needs if n.equip]:
        key = requirement_key(need)
        report('equip', f'Equipping {need.item}')
        result = yield from port.equip(key)
        if not (result) or port.worn(key) < ((need.carry if need.carry is not None else 1)):
            raise RuntimeError(f'Failed to equip {need.item}')
    report('equip', 'Equipment ready', None, 'done')


def provision_dragon_stop(stop, port, report):
    dragon = port.dragon_shop
    items = [need.item for need in stop.needs]
    if not dragon or not dragon.ready():
        raise SupplyUnavailableError('Dragon weapons require Attack 60 and completed Lost City', items)
    try:
        yield from buy_dragon_weapons(stop, port, report)
    except Exception as error:
        returned = yield from dragon.leave()
        if returned:
            yield from bank(port)
            yield from port.deposit()
        raise error
    returned = yield from dragon.leave()
    if not returned:
        raise SupplyUnavailableError('Could not return from Zanaris after shopping', items)
    yield from bank(port)
    yield from port.deposit()
    report('shop:Jakut', 'Jakut supplies banked', None, 'done')


def buy_dragon_weapons(stop, port, report):
    items = [need.item for need in stop.needs]
    budget = sum([purchase_budget(supply_offer(need.item), max(0, need.count - port.stock().get(requirement_key(need).lower(), 0))) for need in stop.needs])
    coins = budget + SHOPPING_RESERVE
    if port.stock().get('coins', 0) < coins:
        raise RuntimeError('Not enough Coins for Jakut and the travel reserve')
    cut = port.stock().get('diamond', 0) <= 0
    kit = ['Dramen staff'] + (['Uncut diamond', 'Chisel'] if cut else ['Diamond'])
    for item in kit:
        packed = yield from port.withdraw(item, 1)
        if not packed:
            raise SupplyUnavailableError(f'Need {item} to reach Jakut', items)
    packed = yield from port.withdraw('Coins', coins)
    if not packed or port.held('Coins') < coins:
        raise RuntimeError('Coin withdrawal did not land')
    closed = yield from port.close_bank()
    if not closed:
        raise RuntimeError('Bank did not close before shopping')
    equipped = yield from port.equip('Dramen staff')
    if not equipped:
        raise SupplyUnavailableError('Could not prepare Dramen staff for Jakut', items)
    if cut:
        cut_ok = yield from port.dragon_shop.cut_diamond()
        if not cut_ok:
            raise SupplyUnavailableError('Could not cut a Diamond for Jakut', items)
    entered = yield from port.dragon_shop.enter()
    if not entered:
        raise SupplyUnavailableError('Cannot reach Jakut', items)
    opened = yield from port.shop('Jakut')
    if not opened:
        raise SupplyUnavailableError('Cannot trade Jakut', items)
    try:
        for need in stop.needs:
            key = requirement_key(need)
            amount = max(0, need.count - port.stock().get(key.lower(), 0))
            if amount == 0:
                continue
            offer = supply_offer(need.item)
            available = port.shop_stock(key)
            if available < amount:
                raise SupplyStockError(f'Jakut has no stock of {need.item}', [need.item])
            cost = sum([unit_price(offer.item, offer.shop, available - index) for index in range(amount)])
            if cost > port.held('Coins') - SHOPPING_RESERVE:
                raise RuntimeError(f'Cannot afford {need.item} at current shop stock')
            report('shop:Jakut', f'Buying {amount} {need.item} from Jakut', stop.tile)
            before = port.held(key)
            yield from port.buy(key, amount)
            if port.held(key) - before < amount:
                raise SupplyStockError(f'Purchase of {need.item} did not arrive', [need.item])
    except Exception as error:
        yield from port.close_shop()
        raise error
    yield from port.close_shop()
