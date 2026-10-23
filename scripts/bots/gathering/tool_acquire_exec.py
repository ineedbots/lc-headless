"""Carrying out a tool acquisition plan: repairing a broken tool, buying from a vendor, or smithing an axe at
Varrock's anvil. rs2b0t's scripts/GatheringBot/ToolAcquireExec.ts (MIT, see thirdparty/rs2b0t). The host is the
GatheringBot, which banks, paces and equips for it."""

from rs2004.catalogs import COINS, HAMMER, acquire_keep_names, best_pickaxe, buy_plans_cost, can_wield_tool, tool_attack_level, walk_to_tool_vendor

INVENTORY_TAB = 3


def keep_matcher(keep):
    kept = [n.lower() for n in keep]
    return lambda name, *_args: len(name) > 0 and name.lower() not in kept


def close_bank(host, log):
    """Use with yield from."""
    yield from host.close_script_bank(log, False)


def deposit_for(host, plan, log, extra=None):
    """Deposits all but what the plan keeps, and the surplus tools. Use with yield from."""
    keep = acquire_keep_names(plan, extra if extra is not None else host.gear_keep_names_list())
    yield from bank.deposit_all_matching(keep_matcher(keep))
    yield from execution.delay_until_ticks(lambda: bank.loaded() or not bank.is_open(), 5)
    yield from host.bank_pace()
    yield from host.prepare_worn_surplus_for_deposit(log, keep)
    yield from host.deposit_surplus_gather_tools(log, keep)


def execute_tool_acquire_plan(host, plan, log=None, bank_prepared=False):
    """Use with yield from."""
    log = log or (lambda m: host.log(f'  {m}'))
    if plan.kind == 'repair':
        done = yield from execute_repair_plan(host, plan, log)
        return done
    if plan.kind == 'buy':
        done = yield from execute_buy_plans(host, [plan], log, bank_prepared)
        return done
    done = yield from execute_smith_plan(host, plan, log, bank_prepared)
    return done


def execute_fishing_gear_shop_cart(host, plans, log=None, bank_prepared=False):
    """Buys several pieces of fishing gear from one vendor, in one bank trip and one visit. Use with yield from."""
    log = log or (lambda m: host.log(f'  {m}'))
    if len(plans) == 0:
        return False
    done = yield from execute_buy_plans(host, plans, log, bank_prepared)
    return done


def execute_repair_plan(host, plan, log):
    """Use with yield from."""
    vendor = plan.vendor
    host.set_status(f'repair: {plan.broken_name} @ {vendor.keeper}')
    host.log(f'acquire: repair {plan.broken_name} via {vendor.keeper}')
    if equipment.contains(plan.broken_name) and not inventory.is_full():
        yield from equipment.unequip(plan.broken_name)
    opened = yield from host.open_bank_at(vendor.bank_stand, log)
    if not opened:
        log('acquire: could not open bank before repair — trying vendor with what we hold')
    else:
        ready = yield from host.wait_bank_ready(log)
        if ready:
            yield from deposit_for(host, plan, log)
            # Nurmof's repairs cost gp, so it doesn't walk without the float when the withdraw fails.
            funded = yield from host.withdraw_coins_for(1000, log)
            if not funded:
                if inventory.count(COINS) < 1:
                    log('acquire: no repair float in pack after bank — abort (will buy if affordable)')
                    host.mark_acquire_backoff(50)
                    yield from close_bank(host, log)
                    return False
                log('acquire: coin withdraw short — continuing with held coins (Bob free / partial float)')
            yield from close_bank(host, log)
            # The broken tool comes off once the pack has room.
            if equipment.contains(plan.broken_name) and not inventory.is_full():
                yield from equipment.unequip(plan.broken_name)
                yield from execution.delay_ticks(1)
    if host.held_count(plan.broken_name) <= 0:
        log(f'acquire: no {plan.broken_name} held after bank — abort repair')
        host.mark_acquire_backoff(35)
        return False
    reached = yield from walk_vendor(host, vendor, log)
    if not reached:
        log(f'acquire: could not reach {vendor.keeper}')
        host.mark_acquire_backoff(75)
        return False
    broken = inventory.first(plan.broken_name)
    if broken is None:
        log(f'acquire: {plan.broken_name} not in pack to use on {vendor.keeper}')
        host.mark_acquire_backoff(35)
        return False
    keeper = npcs.query().name(vendor.keeper).within(12).nearest()
    if keeper is None:
        log(f"acquire: no '{vendor.keeper}' nearby for repair")
        host.mark_acquire_backoff(50)
        return False
    before = host.held_count(plan.broken_name)
    log(f'acquire: use {plan.broken_name} on {vendor.keeper}')
    if not broken.use_on(keeper):
        log(f'acquire: use-on {vendor.keeper} failed — will retry / buy')
        host.mark_acquire_backoff(25)
        return False
    talked = yield from execution.delay_until_ticks(lambda: chat_dialog.is_open() or chat_dialog.can_continue(), 14)
    if not talked:
        log(f'acquire: {vendor.keeper} never opened repair dialogue')
        host.mark_acquire_backoff(50)
        return False
    driven = yield from host.drive_dialog(plan.prefer, log)
    if not driven:
        log(f'acquire: repair dialogue with {vendor.keeper} failed — will retry / buy')
        host.mark_acquire_backoff(35)
        return False
    yield from execution.delay_ticks(2)
    if host.held_count(plan.broken_name) < before:
        host.log(f'acquire: repaired {plan.broken_name} at {vendor.keeper}')
        return True
    if plan.label == 'pickaxe' and best_pickaxe(host.mining_level(), lambda n: host.held_count(n) > 0):
        host.log(f'acquire: usable pick after {vendor.keeper} repair')
        return True
    log(f'acquire: {vendor.keeper} did not repair — try buy path')
    host.mark_acquire_backoff(25)
    return False


def walk_vendor(host, vendor, log):
    """Use with yield from."""
    reached = yield from walk_to_tool_vendor(vendor, log)
    return reached


def execute_buy_plans(host, plans, log, bank_prepared=False):
    """Funds them once at the vendor's bank, opens the shop once and buys every line; every plan must have the same
    vendor. Use with yield from."""
    if len(plans) == 0:
        return False
    vendor = plans[0].vendor
    for p in plans:
        if p.vendor.keeper != vendor.keeper:
            log(f'acquire: multi-buy mixed vendors ({p.vendor.keeper} vs {vendor.keeper}) — abort')
            return False
    total = buy_plans_cost(plans)
    label = ' + '.join([f'{p.qty}× {p.name}' for p in plans])
    host.set_status(f'buy: {label}')
    host.log(f'acquire: {plans[0].reason} @ {vendor.keeper} ({total}gp)' if len(plans) == 1 else f'acquire: multi-buy {label} @ {vendor.keeper} ({total}gp)')
    if bank_prepared and inventory.count(COINS) >= total:
        log('acquire: bank already prepared — heading to shop')
        if bank.is_open():
            yield from close_bank(host, log)
    else:
        opened = yield from host.open_bank_at(vendor.bank_stand, log)
        if not opened:
            log('acquire: could not open bank for coins')
            return False
        ready = yield from host.wait_bank_ready(log)
        if not ready:
            log('acquire: bank did not load for coin withdraw')
            return False
        yield from deposit_for(host, plans[0], log, host.gear_keep_names_list() + [p.name for p in plans])
        if inventory.count(COINS) + bank.count(COINS) < total:
            log(f'acquire: not enough coins for {label} ({total}gp)')
            host.mark_acquire_backoff(100)
            yield from close_bank(host, log)
            return False
        funded = yield from host.withdraw_coins_for(total, log)
        if not funded:
            host.mark_acquire_backoff(50)
            yield from close_bank(host, log)
            return False
        yield from close_bank(host, log)
    reached = yield from walk_vendor(host, vendor, log)
    if not reached:
        log(f'acquire: could not reach {vendor.keeper}')
        host.mark_acquire_backoff(75)
        return False
    opened = yield from shop.open(vendor.keeper)
    if not opened:
        log(f"acquire: could not open {vendor.keeper}'s shop")
        host.mark_acquire_backoff(50)
        return False
    any_bought = False
    to_equip = []
    attack = host.attack_level()
    for plan in plans:
        before = inventory.count(plan.name)
        bought = yield from shop.buy(plan.name, plan.qty)
        got = bought if bought > 0 else max(0, inventory.count(plan.name) - before)
        if got <= 0:
            log(f'acquire: bought 0× {plan.name} — stock/coins')
            continue
        any_bought = True
        host.log(f'acquire: bought {got}× {plan.name}')
        if plan.equip and can_wield_tool(plan.name, attack):
            to_equip.append(plan.name)
        elif plan.equip:
            log(f'equip: skip {plan.name} (need Attack {tool_attack_level(plan.name)})')
    # The shop closes before wielding: the pack's options are Sell while it's open.
    yield from shop.close()
    yield from execution.delay_until_ticks(lambda: not shop.is_open(), 5)
    yield from execution.delay_ticks(1)
    yield from game.open_side_tab(INVENTORY_TAB)
    yield from execution.delay_ticks(1)
    if len(to_equip) > 0:
        yield from host.equip_tools(to_equip, log, False)
    if not any_bought:
        host.mark_acquire_backoff(35)
        return False
    return True


def withdraw_one(host, name, log):
    """Withdraws one of name; False when the bank has none. Use with yield from."""
    found = [i for i in bank.items() if (i.name or '').lower() == name.lower()]
    if len(found) == 0:
        return False
    op = withdraw_op(found[0].actions(), '1') or 'Withdraw-1'
    yield from host.bank_pace()
    bank.withdraw(name, op)
    yield from execution.delay_until_ticks(lambda: inventory.count(name) > 0, 5)
    yield from host.bank_pace()
    return True


def execute_smith_plan(host, plan, log, bank_prepared=False):
    """Use with yield from."""
    host.set_status(f'smith: {plan.name}')
    host.log(f'acquire: {plan.reason} @ Varrock anvil')
    held = inventory.count(HAMMER) >= 1 and inventory.count(plan.bar) >= 1
    # A prepared bank is honoured when the materials are in the pack, as it is for buying.
    if held or bank_prepared:
        log('acquire: smith materials already held — heading to anvil')
        if bank.is_open():
            yield from close_bank(host, log)
    else:
        opened = yield from host.open_bank_at(plan.vendor_bank, log)
        if not opened:
            log('acquire: could not open bank for smith materials')
            return False
        ready = yield from host.wait_bank_ready(log)
        if not ready:
            log('acquire: bank did not load for smith materials')
            return False
        yield from deposit_for(host, plan, log)
        for name, missing in [(HAMMER, 'no hammer for smithing'), (plan.bar, f'no {plan.bar} in bank')]:
            if inventory.count(name) >= 1:
                continue
            took = yield from withdraw_one(host, name, log)
            if not took:
                log(f'acquire: {missing}')
                host.mark_acquire_backoff(100)
                yield from close_bank(host, log)
                return False
        yield from close_bank(host, log)
    if inventory.count(HAMMER) < 1 or inventory.count(plan.bar) < 1:
        log(f'acquire: missing hammer or {plan.bar} before anvil walk')
        host.mark_acquire_backoff(50)
        return False
    arrived = yield from traversal.walk_resilient(plan.anvil_stand, radius=2, timeout_ms=90000, log=log)
    if not arrived:
        log('acquire: could not reach anvil')
        return False
    bar = inventory.first(plan.bar)
    anvil = locs.query().name('Anvil').nearest()
    if bar is None or anvil is None:
        log('acquire: missing bar or anvil')
        return False
    before = inventory.count(plan.name)
    if not bar.use_on(anvil):
        return False
    yield from execution.delay_until_ticks(lambda: chat_dialog.is_main_make_panel() or chat_dialog.can_continue(), 10)
    if chat_dialog.is_main_make_panel():
        # The exact product first: a bare 'Axe' also matches Battleaxe.
        made = yield from chat_dialog.make_from_panel_max(plan.name)
        if not made:
            yield from chat_dialog.make_from_panel_max('Axe')
    yield from execution.delay_until_ticks(lambda: inventory.count(plan.name) > before or not game.animating(), 20)
    if inventory.count(plan.name) <= before:
        log(f'acquire: smith did not produce {plan.name}')
        host.mark_acquire_backoff(35)
        return False
    host.log(f'acquire: smithed {plan.name}')
    if chat_dialog.is_main_make_panel() or chat_dialog.is_open():
        yield from execution.delay_until_ticks(lambda: not chat_dialog.is_main_make_panel() and not chat_dialog.is_open(), 5)
        yield from execution.delay_ticks(1)
    yield from game.open_side_tab(INVENTORY_TAB)
    yield from execution.delay_ticks(1)
    if plan.equip and can_wield_tool(plan.name, host.attack_level()):
        equipped = yield from host.equip_tools([plan.name], log, False)
        if not equipped and inventory.first(plan.name) is not None and not equipment.contains(plan.name):
            log(f'equip: retry {plan.name} after smith')
            yield from execution.delay_ticks(2)
            yield from game.open_side_tab(INVENTORY_TAB)
            yield from host.equip_tools([plan.name], log, False)
    elif plan.equip:
        log(f'equip: skip {plan.name} (need Attack {tool_attack_level(plan.name)})')
    return True
