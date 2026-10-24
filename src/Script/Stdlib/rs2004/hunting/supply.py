"""Supplying a hunt: dose plans for antipoison, prayer and antifire, escape runes, entering and leaving a lair,
the bank run, and the dusty key from Velrak's cell. Ported from rs2b0t's api/combat/hunting/supply.ts (MIT, see
thirdparty/rs2b0t).

Each function that walks or waits is used with yield from. The host h is the bot: a JiveHost in rs2b0t, with log,
vlog (optional), set_status, park_for, count_bank_trip, style, food_name, food_withdraw, weapon_name, pick_weapon
(optional), ammo_name, spell_name, keep_extra and leave_by_walk."""

import _core
from rs2004 import execution
from rs2004.bank import bank, deposit_all_except
from rs2004.catalogs.combat import casts_available, combat_keep_names, food_count as _food_count_in, is_edible_food, rune_withdraw_list
from rs2004.catalogs.record import Record
from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import chat_dialog, modals
from rs2004.entities import ground_items, locs, npcs
from rs2004.execution import event_signal
from rs2004.game import direct_navigator, game, reader, skills
from rs2004.geometry import Tile
from rs2004.items import equipment, inventory
from rs2004.messages import game_messages
from rs2004.navigation import reachability
from rs2004.quests.exec.primitives import drive_dialog
from rs2004.reach import talk_op
from rs2004.routeplan import teleport_by_id
from rs2004.traversal import traversal
from rs2004.hunting.logic import key_status, next_approach_index, shield_gate
from rs2004.hunting.sites import needs_shield

__all__ = ['FlaskPlan', 'BankOpts', 'EscapeSpell', 'SHIELD', 'POISONED', 'ANTIPOISON_LABEL', 'ANTIPOISON_DOSES', 'antipoison_plan', 'PRAYER_LABEL', 'PRAYER_DOSES', 'prayer_plan', 'ANTIFIRE_LABEL', 'ANTIFIRE_DOSES', 'antifire_plan', 'dose_to_drink', 'COINS', 'escape_runes_for', 'wait_fed', 'walk_approach', 'fee_prepaid', 'enter_lair', 'teleport_out', 'leave_lair', 'bank_routine', 'withdraw_to', 'in_cell', 'leave_cell', 'acquire_key']



class FlaskPlan:
    """A dose family to carry: flask, the dose form the bank run draws; doses, every form, so a part-used flask
    still counts; want, the flasks per trip."""

    def __init__(self, flask, doses, want):
        self.flask = flask
        self.doses = doses
        self.want = want

    def __repr__(self):
        return f'FlaskPlan({repr(self.flask)}, {self.want})'


class BankOpts:
    """How a bank run restocks. withdraw_food; deposit_inventory, everything rather than the loot; rune_casts and
    rune_buffer, the spell's casts and spare runes of each type; ammo; escape_stock, escape casts on top of the
    one to leave; heal_to, the hp fraction to eat back to; potions, boost PotionPlans; flasks, FlaskPlans topped up
    by count; wear, gear worn every trip on top of the weapon and ammo; carry, items in the pack every trip; leave,
    how the trip leaves the lair, leave_lair when None."""

    def __init__(self, withdraw_food=False, deposit_inventory=False, rune_casts=None, rune_buffer=None, ammo=None, escape_stock=None,
                 heal_to=None, potions=None, flasks=None, wear=None, carry=None, leave=None):
        self.withdraw_food = withdraw_food
        self.deposit_inventory = deposit_inventory
        self.rune_casts = rune_casts
        self.rune_buffer = rune_buffer
        self.ammo = ammo
        self.escape_stock = escape_stock
        self.heal_to = heal_to
        self.potions = potions
        self.flasks = flasks
        self.wear = wear
        self.carry = carry
        self.leave = leave


class EscapeSpell:
    """A teleport's runes, as (rune, count) pairs, its magic level, and its label."""

    def __init__(self, runes, level, label):
        self.runes = runes
        self.level = level
        self.label = label

SHIELD = 'Dragonfire shield'
# poison_player's opening line, printed once per fresh poisoning; matched without regard to case.
POISONED = 'you have been poisoned'
ANTIPOISON_LABEL = 'Superantipoison'
ANTIPOISON_DOSES = [f'{ANTIPOISON_LABEL}({d})' for d in [4, 3, 2, 1]]


def antipoison_plan(want):
    return FlaskPlan(ANTIPOISON_DOSES[0], ANTIPOISON_DOSES, want)


PRAYER_LABEL = 'Prayer potion'
PRAYER_DOSES = [f'{PRAYER_LABEL}({d})' for d in [4, 3, 2, 1]]


def prayer_plan(want):
    return FlaskPlan(PRAYER_DOSES[0], PRAYER_DOSES, want)


ANTIFIRE_LABEL = 'Antifire potion'
ANTIFIRE_DOSES = [f'{ANTIFIRE_LABEL}({d})' for d in [4, 3, 2, 1]]


def antifire_plan(want):
    return FlaskPlan(ANTIFIRE_DOSES[0], ANTIFIRE_DOSES, want)


def dose_to_drink(count, doses=None):
    """The first dose form held, smallest flask first so a part-used one goes before a full one."""
    if doses is None:
        doses = ANTIPOISON_DOSES
    for name in reversed(list(doses)):
        if count(name) > 0:
            return name
    return None


COINS = 'Coins'
BOOTH = 'Bank booth'
BOOTH_OP = 'Use-quickly'
JAIL_DOOR = Tile(2931, 9690, 0)
JAIL_DOOR_INSIDE = Tile(2931, 9689, 0)
JAIL_KEY = 'Jail key'
JAIL_KEY_ID = 1591
JAIL_DOOR_LOC = 2631
JAILER = 'Jailer'
VELRAK = 'Velrak the explorer'
VELRAK_PREFER = ['So... do you know anywhere good to explore?', 'Yes please!']
CELL = Record({'min_x': 2928, 'max_x': 2934, 'min_z': 9683, 'max_z': 9689})
WALK_MS = 300000
KILL_MS = 90000
DOOR_MS = 8000
HEAL_TO = 0.9
RUNE_CASTS = 150
RUNE_BUFFER = 300
AMMO_WITHDRAW = 500
ESCAPE_STOCK = 2


def say(h):
    return lambda m: h.log(f'  {m}')


def escape_runes_for(teleport_id):
    """The runes and magic level a catalog teleport needs."""
    dest = teleport_by_id(teleport_id)
    requires = (dest.get('requires') if dest is not None else None) or {}
    items = requires.get('items') or []
    level = 0
    for skill in requires.get('skills') or []:
        if skill.get('name') == 'magic':
            level = skill.get('level', 0)
    return EscapeSpell([(i['name'], i['count']) for i in items], level, dest.get('label', teleport_id) if dest is not None else teleport_id)


def escape_shortfall(esc):
    """Why the escape teleport cannot be cast right now, or null when it can."""
    magic = skills.level('magic')
    if magic < esc.level:
        return f'magic {magic} is below the {esc.level} it needs'
    short = [rune for rune, count in esc.runes if inventory.count(rune) < count]
    return f"no {' and '.join(short)}" if len(short) > 0 else None


def hp_frac():
    return skills.hp_fraction()


def food_count(h):
    return _food_count_in(inventory.items(), h.food_name())


def wielded_names():
    return [(i.name if i.name is not None else '') for i in equipment.items()]


def casts_left(h):
    return casts_available(h.spell_name(), wielded_names(), lambda rune: inventory.count(rune))


def ammo_left(h):
    wanted = h.ammo_name().lower()
    worn = ([i for i in equipment.items() if ((i.name if i.name is not None else '')).lower() == wanted] or [None])[0]
    _v4 = (worn.count if worn is not None else None)
    return inventory.count(h.ammo_name()) + ((_v4 if _v4 is not None else 0))


def loc_by_id(id, within=5):
    return locs.query().where(lambda l: l.id == id).within(within).nearest()


# Why: Sustain is call-driven, so a wait that stands still in hostile ground never eats unless it pumps the hook itself.
def wait_fed(cond, ms):
    """Wait for `cond`, feeding the sustain hook every tick."""
    deadline = _core.step_time() + ms
    while _core.step_time() < deadline:
        if cond():
            return True
        yield from sustain.run()
        yield from execution.delay_ticks(1)
    return cond()


def walk_near(dest, radius, log):
    me = game.tile()
    if me is not None and dest.distance_to(me) <= radius:
        return True
    _result5 = yield from traversal.walk_resilient(dest, radius=radius, attempts=4, timeout_ms=WALK_MS, log=log)
    return _result5


# Why: walkResilient's arrival probe accepts the closest reachable point when the destination is sealed or an npc stands on it, so an exact stand is only proved by reading the position back.
def walk_exact(dest, log):
    """Walk onto `dest` itself, not near it."""
    yield from walk_near(dest, 0, log)
    me = game.tile()
    return me is not None and dest.distance_to(me) == 0


APPROACH_LEG_MS = 120000


# Why: the stops are one obstacle apart on a site like Brimhaven, so a walk that always began at the first would recross every obstacle whenever the bot drifted past the last; and a stand the loaded scene already reaches needs no stop at all.
def walk_approach(h, site, stand=None):
    """Walk the site's approach stops from the nearest one on, unless `stand` is already reachable from here."""
    here = game.tile()
    if here is None or len(site.approach) == 0:
        return
    if stand is not None and reachability.can_reach(stand, adjacent_ok=True, max_steps=6000):
        return
    from_ = next_approach_index(site.approach, here)
    for stop in site.approach[from_:]:
        me = game.tile()
        if me is not None and stop.distance_to(me) <= 1:
            continue
        yield from traversal.walk_resilient(stop, radius=0, attempts=3, timeout_ms=APPROACH_LEG_MS, log=lambda m: h.log(f'  {m}'))


PAY_MS = 20000
DIALOGUE_QUIET_TICKS = 3
# Why: the varbit the tree reads survives a click that never went through, so a payment the entrance did not follow is kept here, and the next attempt goes to the tree rather than to the bank for a fee it has already paid.
fee_paid_for = None


def fee_prepaid(site):
    """Whether the site's fee was paid on an attempt whose entrance did not follow."""
    return fee_paid_for == site.key


# Why: Saniboch's reply is three pages and the coins leave on the first, so a check that stops at the coins clicks the tree behind the last page, where the op waits and times out; the drive runs on until the chat has been shut for a few ticks.
def settle_dialogue():
    quiet = 0
    i = 0
    while i < 40 and quiet < DIALOGUE_QUIET_TICKS and not event_signal.pending():
        if chat_dialog.can_continue():
            yield from chat_dialog.continue_()
            quiet = 0
        elif reader.modals().main != -1:
            yield from modals.close()
            quiet = 0
        else:
            if chat_dialog.is_open():
                quiet = 0
            else:
                quiet += 1
        yield from execution.delay_ticks(1)
        i += 1


# Why: the Pay op runs a player line, an objbox and Saniboch's reply before the varbit is set, and the box is a main modal that suspends the script until it is clicked, so the drive answers boxes as well as chat pages and stops on the line the payment prints; a second Pay on a set varbit prints the prepaid line and moves nothing.
def pay_and_enter(h, site):
    """Pay the doorman, unless the fee is already paid, and take the entrance loc through."""
    global fee_paid_for
    fee = site.fee_gate
    if not fee_prepaid(site) and inventory.count(COINS) < fee.coins:
        h.log(f'the way in costs {fee.coins} coins and the pack holds {inventory.count(COINS)}. Banking for more.')
        return False
    h.set_status(f'walking to {fee.npc}')
    _w6 = yield from traversal.walk_resilient(fee.stand, radius=2, attempts=5, timeout_ms=300000, log=say(h))
    if not (_w6):
        return False
    if fee_prepaid(site):
        h.log(f'{fee.npc} is already paid from the last attempt, going straight to the entrance')
    else:
        doorman = npcs.query().name(fee.npc).action(fee.op).nearest()
        if not doorman:
            h.log(f'no {fee.npc} in the scene to pay. Retrying.')
            yield from execution.delay_ticks(2)
            return False
        h.set_status(f'paying {fee.npc}')
        mark = game_messages.mark()
        before = inventory.count(COINS)
        if not (doorman.interact(fee.op)):
            return False

        def paid():
            return game_messages.saw_since(mark, fee.paid_line) or game_messages.saw_since(mark, fee.prepaid_line) or inventory.count(COINS) < before

        deadline = _core.step_time() + PAY_MS
        while _core.step_time() < deadline and not event_signal.pending() and not paid():
            if chat_dialog.can_continue():
                yield from chat_dialog.continue_()
            elif reader.modals().main != -1:
                yield from modals.close()
            yield from execution.delay_ticks(1)
        if not paid():
            h.log(f'{fee.npc} took no payment. Retrying.')
            return False
        fee_paid_for = site.key
        h.log((f'{fee.npc} says the fee is already paid' if game_messages.saw_since(mark, fee.prepaid_line) else f'paid {fee.npc} {fee.coins} coins'))
    yield from settle_dialogue()
    door = loc_by_id(fee.entrance.loc_id, 8)
    if not door or not (door.interact(fee.entrance.op)):
        h.log('the dungeon entrance is not in the scene yet. Retrying.')
        return False
    _w7 = yield from wait_fed(lambda: site.in_area(game.tile()), DOOR_MS)
    if not (_w7):
        h.log('the entrance did not let us through. Retrying.')
        return False
    fee_paid_for = None
    h.log('inside the dungeon')
    h.set_status('walking in to the dragons')
    yield from walk_approach(h, site)
    return True


# Why: the guard answers with a two-option chat and only the first option runs the teleport, so the talk is driven to that option rather than clicked through; the reply moves the player, which is what inArea then proves.
def talk_past_guard(h, site):
    talk = site.talk_gate
    h.set_status(f'walking to the {talk.npc}')
    _w8 = yield from traversal.walk_resilient(talk.stand, radius=2, attempts=5, timeout_ms=300000, log=lambda m: h.log(f'  {m}'))
    if not (_w8):
        return False
    for attempt in range(3):
        if site.in_area(game.tile()):
            break
        guard = npcs.query().name(talk.npc).action(talk.op).nearest()
        if not guard:
            h.log(f'no {talk.npc} in the scene to talk past. Retrying.')
            yield from execution.delay_ticks(2)
            continue
        h.set_status(f'talking past the {talk.npc}')
        if not (guard.interact(talk.op)):
            continue
        yield from drive_dialog([talk.choose], say(h))
        _w9 = yield from wait_fed(lambda: site.in_area(game.tile()), DOOR_MS)
        if _w9:
            h.log(f'the {talk.npc} let us past')
            yield from walk_approach(h, site)
            return True
    h.log(f'the {talk.npc} did not let us past. It needs Watch Tower complete. Retrying.')
    return False


def enter_lair(h, site):
    if site.in_area(game.tile()):
        return True
    if site.talk_gate:
        _result10 = yield from talk_past_guard(h, site)
        return _result10
    if site.fee_gate:
        _result11 = yield from pay_and_enter(h, site)
        return _result11
    gate = site.gate
    # Why: a gateless site is reached by transports and doors the graph already carries, so the approach walk is the way in and inArea is the only proof it landed.
    if not gate:
        h.set_status('walking into the dungeon')
        yield from walk_approach(h, site)
        if not site.in_area(game.tile()):
            h.log('the walk in did not reach the dungeon. Retrying.')
            return False
        h.log('inside the dragon lair')
        return True
    h.set_status('walking to the dungeon gate')
    _w12 = yield from traversal.walk_resilient(gate.outside, radius=0, attempts=5, timeout_ms=300000, log=lambda m: h.log(f'  {m}'))
    if not (_w12):
        return False
    yield from execution.delay_ticks(2)
    door = locs.query().where(lambda l: l.id == gate.loc_id).within(5).nearest()
    key = (None if site.key_item is None else ([i for i in inventory.items() if i.id == site.key_item.id] or [None])[0])
    if not door or (site.key_item is not None and not key):
        h.log('the gate is not in the scene yet, or the key is gone. Retrying.')
        return False
    h.set_status('unlocking the dungeon gate')
    if not (key.use_on(door) if key else door.interact(gate.op)):
        return False
    _w14 = yield from execution.delay_until(lambda: site.in_area(game.tile()), 8000)
    if not (_w14):
        h.log('the gate did not let us through. Retrying.')
        return False
    h.log('inside the dragon lair')
    yield from walk_approach(h, site)
    return True


def teleport_out(h, site):
    """Cast the escape teleport, up to three times. Null once outside the lair, else why the cast will not fire."""
    esc = escape_runes_for(site.escape_teleport_id)
    why = escape_shortfall(esc)
    i = 0
    while why is None and i < 3 and site.in_area(game.tile()):
        h.set_status(f'teleporting to {esc.label}')
        _c15 = game.teleport(site.escape_teleport_id)
        if _c15:
            _w16 = yield from wait_fed(lambda: not site.in_area(game.tile()), DOOR_MS)
            _c15 = _w16
        if _c15:
            h.log(f'teleported out to {esc.label}')
            return None
        yield from execution.delay_ticks(3)
        why = escape_shortfall(esc)
        i += 1
    return (((why if why is not None else 'the cast never landed')) if site.in_area(game.tile()) else None)


def leave_lair(h, site):
    """Teleport out of the lair, or walk out through the gate when the cast will not fire."""
    if not site.in_area(game.tile()):
        return True
    if h.leave_by_walk():
        _result17 = yield from walk_out_of_lair(h, site)
        return _result17
    why = yield from teleport_out(h, site)
    if why is None:
        return True
    h.log(f"the {escape_runes_for(site.escape_teleport_id).label} will not fire ({why}). Walking out {('the way we came in' if site.gate is None else 'through the gate')} instead.")
    _result18 = yield from walk_out_of_lair(h, site)
    return _result18


# Why: the gate takes the key on the way in only, and answers a plain Open from the inside.
# Why: no path leaves the Enclave, so the way out is the cave's own op, which teleports to the hillside; walking to walkOut from inside would plan a route the cave does not have.
def leave_by_loc(h, site):
    exit = site.exit
    h.set_status('walking to the cave mouth')
    yield from walk_near(exit.stand, 2, say(h))
    yield from execution.delay_ticks(1)
    cave = loc_by_id(exit.loc_id)
    if not cave or not (cave.interact(exit.op)):
        h.log('the cave mouth is not in the scene yet. Retrying.')
        return False
    _w19 = yield from wait_fed(lambda: not site.in_area(game.tile()), DOOR_MS)
    if not (_w19):
        h.log('the cave mouth did not let us out. Retrying.')
        return False
    h.log('out of the dragon lair')
    return True


def walk_out_of_lair(h, site):
    if site.exit:
        _result20 = yield from leave_by_loc(h, site)
        return _result20
    gate = site.gate
    # Why: with no gate the way out is the way in run backwards, so walking to walkOut climbs the ladder and opens the doors above it on its own.
    if not gate:
        h.set_status('walking out of the dungeon')
        yield from walk_near(site.walk_out, 3, say(h))
        if site.in_area(game.tile()):
            h.log('the walk out did not leave the dungeon. Retrying.')
            return False
        h.log('out of the dragon lair')
        return True
    h.set_status('walking back to the dungeon gate')
    # Why: the inside stand is the one gap in the lair wall, so requiring it would seal the bot in whenever a player or an npc parks on it.
    _w21 = yield from walk_exact(gate.inside, say(h))
    if not (_w21):
        h.log('the inside of the gate is occupied. Opening it from wherever the walk stopped.')
        yield from walk_near(gate.inside, 2, say(h))
    yield from execution.delay_ticks(2)
    door = loc_by_id(gate.loc_id)
    if not door or not (door.interact(gate.op)):
        h.log('the gate is not in the scene yet. Retrying.')
        return False
    _w22 = yield from wait_fed(lambda: not site.in_area(game.tile()), DOOR_MS)
    if not (_w22):
        h.log('the gate did not let us out. Retrying.')
        return False
    h.log('out of the dragon lair')
    _result23 = yield from walk_near(site.walk_out, 3, say(h))
    return _result23


def keep_names(h, site):
    extra = [SHIELD, JAIL_KEY] + [rune for rune, count in escape_runes_for(site.escape_teleport_id).runes] + list(h.keep_extra())
    if site.key_item is not None:
        extra.append(site.key_item.name)
    if site.coins is not None:
        extra.append(COINS)
    return combat_keep_names(h.food_name(), h.style(), spell=h.spell_name(), ammo=h.ammo_name(), weapon=h.weapon_name(), extra=extra)


def open_site_bank(h, site):
    _w24 = yield from walk_near(site.bank, 3, say(h))
    if not (_w24):
        h.log('walk to the bank failed. Will retry.')
        return False
    _w25 = yield from bank.open_nearest(BOOTH, BOOTH_OP)
    if not (_w25):
        h.log('could not open the bank. Will retry.')
        return False
    _result26 = yield from execution.delay_until(lambda: bank.is_open() and bank.loaded(), 5000)
    return _result26


def deposit_loot(h, site):
    deposit = deposit_all_except(keep_names(h, site))
    notes = set([i.id for i in [i for i in inventory.items() if i.noted]])
    yield from bank.deposit_all_matching(lambda name, id: (id in notes) or deposit(name))


def bank_routine(h, site, opts):
    """Bank the load, restock, heal, and end the trip ready for the next one."""
    _w27 = yield from ((opts.leave if opts.leave is not None else leave_lair))(h, site)
    if not (_w27):
        return
    _w28 = yield from open_site_bank(h, site)
    if not (_w28):
        return
    # Why: the pick has to land before the deposit, or a weapon the pack already holds goes into the bank and straight back out.
    if h.style() == 'melee' and getattr(h, 'pick_weapon', None) is not None:
        h.pick_weapon([(i.name if i.name is not None else '') for i in list(bank.items()) + list(inventory.items()) + list(equipment.items())])
    if opts.deposit_inventory:
        yield from bank.deposit_all_matching(lambda name, id: True)
    else:
        yield from deposit_loot(h, site)
    if opts.withdraw_food:
        yield from withdraw_food_to(h)
    yield from withdraw_key(h, site)
    _w29 = yield from withdraw_gear(h, site, opts.wear, opts.carry)
    if not (_w29):
        yield from bank.close()
        return
    yield from withdraw_coins(h, site)
    yield from withdraw_style_supplies(h, opts)
    yield from withdraw_escape_runes(h, site, opts)
    yield from withdraw_flasks(h, list([as_flask(_x) for _x in ((opts.potions if opts.potions is not None else []))]) + list(((opts.flasks if opts.flasks is not None else []))))
    # Why: Equipment.equip shuts the bank to get the backpack ops back, so every withdrawal has to land before anything is worn.
    yield from equip_gear(h, site, opts.wear)
    _w31 = yield from heal_up(h, (opts.heal_to if opts.heal_to is not None else HEAL_TO))
    _c30 = _w31 and opts.withdraw_food
    if _c30:
        _w32 = yield from open_site_bank(h, site)
        _c30 = _w32
    if _c30:
        yield from withdraw_food_to(h)
    yield from bank.close()
    h.count_bank_trip()
    h.set_status(f'restocked, heading back to the {site.target.lower()}s')


def withdraw_food_to(h):
    h.set_status(f'withdrawing {h.food_name()}')
    want = h.food_withdraw()
    guard = 0
    while guard < 12 and food_count(h) < want and not inventory.is_full():
        before = food_count(h)
        need = want - before
        bank.withdraw(h.food_name(), ('Withdraw-10' if need >= 10 else ('Withdraw-5' if need >= 5 else 'Withdraw-1')))
        _w33 = yield from execution.delay_until(lambda: food_count(h) > before, 2500)
        if not (_w33):
            break
        guard += 1
    if food_count(h) == 0:
        h.log(f'WARNING: no \'{h.food_name()}\' in the bank. Deposit food to resume eating.')


def withdraw_key(h, site):
    """Take the site's key out of the bank when the trip is starting without it."""
    item = site.key_item
    if item is None or inventory.count_by_id(item.id) > 0:
        return True
    if bank.count_by_id(item.id) == 0:
        h.log(f'no \'{item.name}\' in the bank or in the pack. Velrak has to hand out another one.')
        return False
    h.set_status(f'withdrawing the {item.name}')
    bank.withdraw_by_id(item.id, 'Withdraw-1')
    _result34 = yield from execution.delay_until(lambda: inventory.count_by_id(item.id) > 0, 2500)
    return _result34


def need_one(h, name):
    if name == '' or equipment.contains(name) or inventory.first(name) is not None:
        return
    _w35 = yield from withdraw_to(name, 1)
    if _w35 > 0:
        h.log(f'withdrew {name}')
    else:
        h.log(f'WARNING: no \'{name}\' in the bank. Carrying on with the gear already worn.')


def withdraw_gear(h, site, wear=None, carry=None):
    if wear is None:
        wear = []
    if carry is None:
        carry = []
    if not bank.is_open() or not bank.loaded():
        return False
    if needs_shield(site, h.style()):
        if not equipment.contains(SHIELD) and inventory.count(SHIELD) == 0 and bank.count(SHIELD) > 0 and inventory.is_full():
            food = ([i for i in inventory.items() if is_edible_food(i, h.food_name())] or [None])[0]
            used = inventory.used()
            if not (food.name if food is not None else None) or not (bank.deposit(food.name, 'Deposit-1')):
                return False
            _w36 = yield from execution.delay_until(lambda: bank.is_open() and bank.loaded() and inventory.used() < used, 2500)
            if not (_w36):
                return False
        yield from need_one(h, SHIELD)
    yield from need_one(h, h.weapon_name())
    for name in list(wear) + list(carry):
        yield from need_one(h, name)
    if not bank.is_open() or not bank.loaded():
        return False
    gate = shield_gate(h.style(), site.fire_at_range == True, equipment.contains(SHIELD) or inventory.count(SHIELD) > 0 or bank.count(SHIELD) > 0)
    if gate is not None:
        h.park_for(gate)
        return False
    return not needs_shield(site, h.style()) or equipment.contains(SHIELD) or inventory.count(SHIELD) > 0


# Why: the fee and the fares are spent every trip, so the pile is topped back up to the site's figure rather than stocked once.
def withdraw_coins(h, site):
    if site.coins is None or inventory.count(COINS) >= site.coins:
        return
    h.set_status('withdrawing coins')
    got = yield from withdraw_to(COINS, site.coins)
    if got > 0:
        h.log(f'withdrew {got} coins ({inventory.count(COINS)}/{site.coins})')
    else:
        _v38 = (site.fee_gate.coins if site.fee_gate is not None else None)
        if inventory.count(COINS) < ((_v38 if _v38 is not None else 0)):
            _v39 = (site.fee_gate.coins if site.fee_gate is not None else None)
            h.log(f'WARNING: the bank cannot cover the {(_v39 if _v39 is not None else site.coins)} coins the way in costs. Deposit coins to resume.')


def equip_gear(h, site, extra=None):
    if extra is None:
        extra = []
    shield = ([SHIELD] if needs_shield(site, h.style()) else [])
    wear = list(shield) + [h.weapon_name(), (h.ammo_name() if h.style() == 'range' else '')] + list(extra)
    for name in wear:
        _c40 = name != '' and not equipment.contains(name) and inventory.first(name) is not None
        if _c40:
            _w41 = yield from equipment.equip(name)
            _c40 = _w41
        if _c40:
            h.log(f'wearing {name}')


def withdraw_style_supplies(h, opts):
    if h.style() == 'mage':
        h.set_status('withdrawing runes')
        for row in rune_withdraw_list(h.spell_name(), wielded_names(), opts.rune_casts if opts.rune_casts is not None else RUNE_CASTS):
            rune = row['rune']
            count = row['count']
            target = count + ((opts.rune_buffer if opts.rune_buffer is not None else RUNE_BUFFER))
            if inventory.count(rune) < target:
                got = yield from withdraw_to(rune, target)
                h.log(f'withdrew {got} {rune} ({inventory.count(rune)}/{target})')
        if casts_left(h) < 1:
            h.log(f'WARNING: the bank cannot supply a single \'{h.spell_name()}\' cast. Deposit runes to resume.')
    elif h.style() == 'range':
        h.set_status(f'withdrawing {h.ammo_name()}')
        got = yield from withdraw_to(h.ammo_name(), (opts.ammo if opts.ammo is not None else AMMO_WITHDRAW))
        if got > 0:
            h.log(f'withdrew {got} {h.ammo_name()}')
        elif ammo_left(h) == 0:
            h.log(f'WARNING: no \'{h.ammo_name()}\' in the bank. Deposit ammo to resume.')


def withdraw_escape_runes(h, site, opts):
    esc = escape_runes_for(site.escape_teleport_id)
    for rune, count in esc.runes:
        target = count * (((opts.escape_stock if opts.escape_stock is not None else ESCAPE_STOCK)) + 1)
        if inventory.count(rune) < target:
            yield from withdraw_to(rune, target)
    why = escape_shortfall(esc)
    if why is not None:
        h.log(f'WARNING: the {esc.label} cannot be cast ({why}). The next trip walks out through the gate.')


def as_flask(plan):
    return FlaskPlan(plan.flask, plan.potion.doses, plan.want)


def flasks_held(plan):
    return sum([inventory.count(dose) for dose in plan.doses])


# Why: a flask is counted across every dose form, so a part-used one carried back from the last trip is topped up rather than stocked on top of.
def withdraw_flasks(h, plans):
    """Top each dose family up to its flask count."""
    for plan in plans:
        start = flasks_held(plan)
        guard = 0
        while guard < 12 and flasks_held(plan) < plan.want and not inventory.is_full():
            before = flasks_held(plan)
            bank.withdraw(plan.flask, 'Withdraw-1')
            _w44 = yield from execution.delay_until(lambda: flasks_held(plan) > before, 2500)
            if not (_w44):
                break
            guard += 1
        got = flasks_held(plan) - start
        if got > 0:
            h.log(f'withdrew {got} {plan.flask}')
        elif flasks_held(plan) == 0:
            h.log(f'WARNING: no \'{plan.flask}\' in the bank. The trip goes without.')


def eat_once(h):
    food = ([i for i in inventory.items() if is_edible_food(i, h.food_name())] or [None])[0]
    if not food:
        return False
    before = skills.effective('hitpoints')
    id = food.id
    count = inventory.count_by_id(id)
    if not (food.interact('Eat')):
        return False
    _result45 = yield from execution.delay_until_ticks(lambda: inventory.count_by_id(id) < count or skills.effective('hitpoints') > before, 2)
    return _result45


# Why: the walk back is long, so the heal happens at the booth and the food it spends is topped up before leaving.
def heal_up(h, to):
    if hp_frac() >= to or food_count(h) == 0:
        return False
    _c46 = bank.is_open()
    if _c46:
        _w47 = yield from bank.close()
        _c46 = not (_w47)
    if _c46:
        return False
    h.set_status('eating up before the trip back')
    from_ = round(hp_frac() * 100)
    # Why: eating has a cooldown, so one refused bite is normal and only a run of them means the food is gone.
    misses = 0
    i = 0
    while i < 24 and hp_frac() < to and food_count(h) > 0 and misses < 3:
        _w48 = yield from eat_once(h)
        if _w48:
            misses = 0
        else:
            misses += 1
            yield from execution.delay_ticks(2)
        i += 1
    h.log(f'healed {from_}% to {round(hp_frac() * 100)}% before heading back')
    return True


def withdraw_to(name, target):
    """Top the pack up to `target` of `name`, returning how many arrived."""
    start = inventory.count(name)
    guard = 0
    while guard < 40 and inventory.count(name) < target and not inventory.is_full():
        before = inventory.count(name)
        need = target - before
        _c49 = need > 10
        if _c49:
            _w50 = yield from bank.withdraw_x(name, need)
            _c49 = (_w50)
        if _c49:
            if inventory.count(name) > before:
                guard += 1
                continue
            break
        bank.withdraw(name, ('Withdraw-10' if need >= 10 else ('Withdraw-5' if need >= 5 else 'Withdraw-1')))
        _w51 = yield from execution.delay_until(lambda: inventory.count(name) > before, 2500)
        if not (_w51):
            break
        guard += 1
    return inventory.count(name) - start


def in_cell():
    """Standing inside Velrak's cell, which is a dead end."""
    me = game.tile()
    return me is not None and me.level == 0 and me.x >= CELL.min_x and me.x <= CELL.max_x and me.z >= CELL.min_z and me.z <= CELL.max_z


# Why: the jail key lies on the floor for 100 ticks against the usual two minutes, so a slow pickup means killing the Jailer again.
def take_jail_key(h):
    for attempt in range(3):
        drop = ground_items.query().where(lambda g: g.id == JAIL_KEY_ID).within(12).nearest()
        if not drop:
            yield from execution.delay_ticks(2)
            continue
        if drop.distance() > 1:
            yield from traversal.walk_resilient(drop.tile(), radius=1, attempts=2, timeout_ms=30000, log=say(h))
        again = ground_items.query().where(lambda g: g.id == JAIL_KEY_ID).within(12).nearest()
        _c52 = again and again.interact('Take')
        if _c52:
            _w53 = yield from wait_fed(lambda: inventory.count_by_id(JAIL_KEY_ID) > 0, DOOR_MS)
            _c52 = _w53
        if _c52:
            return True
    h.log('the jail key was gone before it was picked up. Killing the Jailer again.')
    return False


# Why: the Jailer has no huntmode so he never opens the fight, and nothing polls Sustain for a loop that stands and swings.
JAILER_RESPAWN_MS = 75000


def nearest_jailer():
    return npcs.query().name(JAILER).action('Attack').within(14).nearest()


def kill_jailer(h):
    jailer = nearest_jailer()
    if not jailer:
        h.set_status(f'waiting for the {JAILER} to respawn')
        h.log(f'no {JAILER} in the prison corridor. Waiting out his respawn where we stand.')
        _w54 = yield from wait_fed(lambda: nearest_jailer() is not None, JAILER_RESPAWN_MS)
        if not (_w54):
            return False
        jailer = nearest_jailer()
    if not jailer:
        return False
    index = jailer.index

    def live():
        return any([npc.index == index and npc.name == JAILER for npc in npcs.all()])

    if not (jailer.interact('Attack')):
        return False
    h.set_status(f'fighting the {JAILER} for his key')
    deadline = _core.step_time() + KILL_MS
    while _core.step_time() < deadline and not event_signal.pending():
        yield from sustain.run()
        if inventory.count_by_id(JAIL_KEY_ID) > 0:
            return True
        if not live():
            _result55 = yield from take_jail_key(h)
            return _result55
        yield from execution.delay_ticks(1)
    h.log(f'the {JAILER} outlived {KILL_MS // 1000}s of combat.')
    return False


def unlock_cell(h):
    yield from execution.delay_ticks(2)
    door = loc_by_id(JAIL_DOOR_LOC)
    key = ([i for i in inventory.items() if i.id == JAIL_KEY_ID] or [None])[0]
    if not door or not key:
        h.log('no cell door in reach, or the jail key is gone. Retrying.')
        return False
    h.set_status('unlocking the cell')
    if not key.use_on(door):
        return False
    _w56 = yield from wait_fed(lambda: in_cell(), DOOR_MS)
    if not (_w56):
        h.log('the cell door did not let us in. Retrying.')
        return False
    return True


# Why: the talk ends wherever Velrak drifted, and 8 of the cell's 33 tiles are further from the door than locById searches, so a query taken from there reads it as absent forever.
def leave_cell(h):
    """Open the cell door from the inside. True when the run is back in the corridor."""
    if not in_cell():
        return True
    h.set_status('walking back to the cell door')
    _w57 = yield from walk_exact(JAIL_DOOR_INSIDE, say(h))
    if not (_w57):
        h.log('the inside of the cell door is occupied. Opening it from wherever the walk stopped.')
        yield from walk_near(JAIL_DOOR_INSIDE, 2, say(h))
    yield from execution.delay_ticks(2)
    door = loc_by_id(JAIL_DOOR_LOC)
    if not door or not (door.interact('Open')):
        h.log('no cell door to open from the inside. Retrying.')
        return False
    _w58 = yield from wait_fed(lambda: not in_cell(), DOOR_MS)
    if not (_w58):
        h.log('the cell door did not let us out. Retrying.')
        return False
    return True


# Why: Velrak has no wanderrange, so he drifts around a cell whose walls make that a walk, and the shared talk primitives answer an out-of-reach npc by opening the door in front of it, which here is the cell door.
def talk_in_cell(h):
    yield from execution.delay_ticks(2)

    def find():
        return npcs.query().name(VELRAK).where(lambda npc: talk_op(npc.actions()) is not None).nearest()

    velrak = find()
    if not velrak:
        h.log(f'no {VELRAK} in the cell. Retrying.')
        return False
    if velrak.distance() > 1:
        yield from direct_navigator.walk_to(velrak.tile(), 1, 20000)
        velrak = find()
    op = (None if velrak is None else talk_op(velrak.actions()))
    if velrak is None or op is None or not (velrak.interact(op)):
        h.log(f'{VELRAK} refused the talk. Retrying.')
        return False
    _w59 = yield from wait_fed(lambda: chat_dialog.is_open() or chat_dialog.can_continue(), DOOR_MS)
    if not (_w59):
        h.log(f'{VELRAK} never opened a dialogue. Retrying.')
        return False
    _result60 = yield from drive_dialog(VELRAK_PREFER, say(h))
    return _result60


def fetch_from_velrak(h, key_id):
    if not in_cell():
        _w61 = yield from walk_near(JAIL_DOOR, 1, say(h))
        if not (_w61):
            return False
        _c62 = inventory.count_by_id(JAIL_KEY_ID) == 0
        if _c62:
            _w63 = yield from kill_jailer(h)
            _c62 = not (_w63)
        if _c62:
            return False
        # Why: npcs block tiles, and the client's own path search fails every click at a stand the Jailer is standing on.
        _w64 = yield from walk_exact(JAIL_DOOR, say(h))
        if not (_w64):
            h.log('could not stand at the cell door. Retrying.')
            return False
        _w65 = yield from unlock_cell(h)
        if not (_w65):
            return False
    _w67 = yield from talk_in_cell(h)
    _c66 = _w67
    if _c66:
        _w68 = yield from execution.delay_until(lambda: inventory.count_by_id(key_id) > 0, DOOR_MS)
        _c66 = _w68
    got = _c66
    if not got:
        h.log('Velrak handed over no key. Retrying.')
    # Why: the cell is a dead end, so the run has to be back in the corridor before anything else routes from here.
    out = yield from leave_cell(h)
    return got and out


def acquire_key(h, site):
    """Put the site's key in the pack, from the bank when it's there and from Velrak when it isn't: 'held', or
    where the next one comes from, 'bank' or 'fetch'."""
    item = site.key_item
    if item is None:
        return 'held'

    def state():
        return key_status(inventory.count_by_id(item.id), bank.count_by_id(item.id))

    if state() == 'held':
        return 'held'
    _c69 = site.in_area(game.tile())
    if _c69:
        _w70 = yield from leave_lair(h, site)
        _c69 = not (_w70)
    if _c69:
        return state()
    h.set_status(f'fetching the {item.name}')
    # Why: reader.bankItems() is empty whenever the bank modal is shut, so a key sitting in the bank reads as no key at all and would cost a needless Jailer kill.
    # Why: the fetch also needs a free slot for the key and walks into a fight, so a bank stop that never happened is a reason to stop rather than press on.
    _w71 = yield from open_site_bank(h, site)
    if not (_w71):
        return state()
    yield from deposit_loot(h, site)
    from_bank = yield from withdraw_key(h, site)
    # Why: this leg walks into the Jailer fight and on into the lair, so the gear leaves the booth with the key rather than waiting for a bank run that only comes after the first kill.
    _w72 = yield from withdraw_gear(h, site)
    if not (_w72):
        yield from bank.close()
        return state()
    if not from_bank:
        yield from withdraw_food_to(h)
    yield from bank.close()
    yield from equip_gear(h, site)
    if from_bank:
        h.log(f'took the {item.name} out of the bank')
        return state()
    h.set_status(f'fetching the {item.name} from Velrak')
    # Why: the jail key is already earned and kept, so a failure inside the cell is retried here rather than paid for with another walk and another kill.
    attempt = 0
    while attempt < 3 and state() != 'held' and not event_signal.pending():
        _w73 = yield from fetch_from_velrak(h, item.id)
        if _w73:
            h.log(f'Velrak handed over the {item.name}')
        attempt += 1
    return state()

