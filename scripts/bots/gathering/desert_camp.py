"""The route into and out of the Desert Mining Camp: through Shantay Pass, the camp's gate with the Metal key, and
down to the deep mine in a slave's disguise with the Wrought iron key, recovering the keys and the disguise when
they're lost. rs2b0t's scripts/GatheringBot/DesertMiningCampRoute.ts (MIT, see thirdparty/rs2b0t). It needs The
Tourist Trap."""

import time

from rs2004.catalogs import Record, sustain

from bots.gathering.miner_logic import desert_camp_food_reserve_depleted

COINS = 'Coins'
PASS = 'Shantay pass'
DISCLAIMER = 'Shantay disclaimer'
CELL_KEY = 'Cell door key'
METAL_KEY = 'Metal key'
WROUGHT_KEY = 'Wrought iron key'
DESERT_OUTFIT = ['Desert shirt', 'Desert robe', 'Desert boots']
SLAVE_OUTFIT = ["Slaves' shirt", 'Slave robe', 'Slave boots']
DESERT_CAMP_UNDERGROUND_NAME = 'Desert Mining Camp'
DESERT_CAMP_SURFACE_NAME = 'Desert Mining Camp Surface'
DESERT_CAMP_KEEP_NAMES = [PASS, DISCLAIMER, CELL_KEY, METAL_KEY, WROUGHT_KEY] + SLAVE_OUTFIT
DESERT_SHOP_BUDGET = {'Desert shirt': 43, 'Desert robe': 43, 'Desert boots': 21}
FIXED_PASS_COST = 5
SHANTAY_SHOP = Tile(3304, 3123, 0)
SHANTAY_BANK = Tile(3308, 3120, 0)
SHANTAY_NORTH = Tile(3304, 3118, 0)
SHANTAY_SOUTH = Tile(3304, 3114, 0)
CAPTAIN = Tile(3270, 3029, 0)
CAMP_OUTSIDE = Tile(3273, 3029, 0)
CAMP_INSIDE = Tile(3274, 3029, 0)
MALE_SLAVE = Tile(3302, 3016, 0)
SIAD_DESK = Tile(3290, 3033, 1)
DESERT_CAMP_MINE_ANCHOR = Tile(3323, 9458, 0)
MALE_SLAVE_ID = 825
ESCAPED_SLAVE_ID = 826
MERCENARY_CAPTAIN_ID = 830
SIAD_DESK_ID = 2679
CAPTAIN_WAIT_MS = 245000
DUEL_MS = 180000
CAPTAIN_KEY_DUEL = [
    'Wow! A real captain!',
    "I'd love to work for a tough guy like you!",
    "Can't I do something for a strong Captain like you?",
    "Sorry Sir, I don't think I can do that.",
    "It's a funny captain who can't fight his own battles!",
]


def is_desert_camp_location(name):
    return name == DESERT_CAMP_UNDERGROUND_NAME or name == DESERT_CAMP_SURFACE_NAME


def desert_camp_destination_for(name):
    return 'campSurface' if name == DESERT_CAMP_SURFACE_NAME else 'mineDeep'


def desert_camp_keep_names(destination):
    return [PASS, DISCLAIMER, METAL_KEY] + DESERT_OUTFIT if destination == 'campSurface' else DESERT_CAMP_KEEP_NAMES


def in_rect(tile, x0, x1, z0, z1):
    return tile.x >= x0 and tile.x <= x1 and tile.z >= z0 and tile.z <= z1


def desert_camp_route_area(tile):
    if tile is None:
        return 'unsupported'
    if tile.level == 1 and in_rect(tile, 3274, 3306, 3011, 3043):
        return 'campSurface'
    if tile.level != 0 or in_rect(tile, 3284, 3286, 3032, 3036):
        return 'unsupported'
    if in_rect(tile, 3274, 3306, 3011, 3043):
        return 'campSurface'
    if in_rect(tile, 3264, 3327, 9408, 9471):
        if tile.x <= 3282:
            return 'mineEntrance'
        if in_rect(tile, 3285, 3292, 9429, 9452):
            return 'unsupported'
        return 'mineDeep' if tile.z >= 9449 else 'mineLower'
    if tile.z >= 6400:
        return 'unsupported'
    if in_rect(tile, 3288, 3320, 3117, 3140):
        return 'shantayNorth'
    if tile.x >= 3136 and tile.x <= 3375 and tile.z >= 2880 and tile.z < 3117:
        return 'desert'
    return 'mainland'


def desert_camp_bank_trip_direction(bank_trip, needs_bank):
    latched = bank_trip or needs_bank
    return Record({'bank_trip': latched, 'direction': 'exit' if latched else 'enter'})


def desert_camp_bank_catch_needed(bank_trip, startup_bank, restock, full_with_deposit):
    return bank_trip or startup_bank or restock or full_with_deposit


def desert_camp_route_phase(direction, area, destination='mineDeep'):
    if area == 'unsupported':
        return 'unsupported'
    mine = area == 'mineEntrance' or area == 'mineLower' or area == 'mineDeep'
    if direction == 'enter':
        if area == 'mainland' or area == 'shantayNorth':
            return 'prepareAndCrossShantay'
        if area == 'desert':
            return 'enterCamp'
        if destination == 'campSurface':
            if area == 'campSurface':
                return 'done'
            return 'exitMine' if mine else 'unsupported'
        if area == 'campSurface':
            return 'enterMine'
        return 'done' if area == 'mineDeep' else 'enterMine'
    if mine:
        return 'exitMine'
    if area == 'campSurface':
        return 'exitCamp'
    if area == 'desert':
        return 'crossShantayNorth'
    return 'done'


# Why: a Record makes its dict fields Records too, so the counts are read through keys() and get(), which both have.
def count_of(counts, name):
    wanted = name.lower()
    return sum([counts.get(key, 0) for key in counts.keys() if key.lower() == wanted])


def owned(snap, name):
    return count_of(snap.inventory, name) + count_of(snap.equipment, name) > 0


def available(snap, name):
    return count_of(snap.inventory, name) + count_of(snap.equipment, name) + count_of(snap.bank, name)


def plan_desert_camp_supplies(snap, destination='mineDeep'):
    """What to withdraw, buy and recover for the trip from the bank's, the pack's and the gear's counts
    (snap.inventory, snap.equipment, snap.bank, dicts of name to count, and snap.free_slots)."""
    withdraw = []
    buy_outfit = []
    missing = []
    surface = destination == 'campSurface'
    recover_slave_outfit = not surface and len([name for name in SLAVE_OUTFIT if available(snap, name) == 0]) > 0
    if not surface and not recover_slave_outfit:
        for name in SLAVE_OUTFIT:
            if not owned(snap, name):
                withdraw.append(Record({'name': name, 'qty': 1}))
    # Why: an underground trip banks the desert clothes, and withdraws them only to buy a new slave disguise; a
    # surface trip wears them for the heat.
    desert_target = 1 if surface or recover_slave_outfit else 0
    for name in DESERT_OUTFIT:
        held = count_of(snap.inventory, name) + count_of(snap.equipment, name)
        needed = max(0, desert_target - held)
        banked = min(needed, count_of(snap.bank, name))
        if banked > 0:
            withdraw.append(Record({'name': name, 'qty': banked}))
        for _ in range(banked, needed):
            buy_outfit.append(name)

    def needs_key(name):
        """Whether the key must be recovered; a banked one is withdrawn."""
        if owned(snap, name):
            return False
        if count_of(snap.bank, name) > 0:
            withdraw.append(Record({'name': name, 'qty': 1}))
            return False
        return True

    recover_metal_key = needs_key(METAL_KEY)
    recover_wrought_key = False if surface else needs_key(WROUGHT_KEY)
    buy_pass = False
    if count_of(snap.inventory, PASS) == 0:
        if count_of(snap.bank, PASS) > 0:
            withdraw.append(Record({'name': PASS, 'qty': 1}))
        else:
            buy_pass = True
    coin_target = sum([DESERT_SHOP_BUDGET[name] for name in buy_outfit]) + (FIXED_PASS_COST if buy_pass else 0)
    shortage = max(0, coin_target - count_of(snap.inventory, COINS))
    if shortage > count_of(snap.bank, COINS):
        missing.append(f'{coin_target} {COINS} for Shantay purchases')
    elif shortage > 0:
        withdraw.append(Record({'name': COINS, 'qty': shortage}))
    required_slots = 0
    for step in withdraw:
        if step.name == COINS:
            required_slots += 0 if count_of(snap.inventory, COINS) > 0 else 1
        else:
            required_slots += step.qty
    required_slots += len(buy_outfit)
    if buy_pass:
        required_slots += 1
    # The desk awards every missing key, so recovering the metal key on the surface still takes three slots.
    if recover_metal_key and (recover_wrought_key or surface):
        required_slots += 3
    elif recover_wrought_key:
        required_slots += 1 if count_of(snap.inventory, CELL_KEY) > 0 else 2
    elif recover_metal_key:
        required_slots += 1
    if required_slots > snap.free_slots:
        missing.append(f'{required_slots - snap.free_slots} free inventory slot(s)')
    return Record({
        'ok': len(missing) == 0, 'withdraw': withdraw, 'buy_outfit': buy_outfit, 'buy_pass': buy_pass, 'recover_slave_outfit': recover_slave_outfit,
        'recover_metal_key': recover_metal_key, 'recover_wrought_key': recover_wrought_key, 'coin_target': coin_target, 'required_slots': required_slots,
        'missing': missing,
    })


def metal_key_duel_needs_retreat(food_count, captain_alive):
    return captain_alive and desert_camp_food_reserve_depleted(food_count)


def metal_key_captain_available(captain):
    return captain is not None and not captain.in_combat and not captain.targets_another_player()


def metal_key_retreat_after_sustain(has_key, food_count, captain_alive):
    return not has_key and metal_key_duel_needs_retreat(food_count, captain_alive)


def metal_key_captain_claim_acknowledged(chat_open, captain_targets_me, has_key):
    return chat_open or captain_targets_me or has_key


def live_counts(items):
    out = {}
    for item in items:
        if item.name:
            out[item.name] = out.get(item.name, 0) + max(1, item.count)
    return out


def equipment_count(name):
    wanted = name.lower()
    return sum([item.count for item in equipment.items() if (item.name or '').lower() == wanted])


def quest_complete():
    return quests.status('The Tourist Trap') == 'complete' or quests.status('Tourist Trap') == 'complete'


def pickaxe_name(items):
    for item in items:
        if (item.name or '').lower().endswith('pickaxe'):
            return item.name
    return None


def now_ms():
    return time.time() * 1000


def has_all(names):
    return len([name for name in names if not inventory.contains(name) and not equipment.contains(name)]) == 0


def normalize(value):
    return ' '.join(value.strip().lower().split())


def facing_npc(index):
    return game.facing() == ('npc', index)


def captain_alive(npc):
    return npc is not None and (npc.health != 0 or npc.max_health <= 0)


def captain_note(npc):
    return f'combat={npc.in_combat},otherPlayer={npc.targets_another_player()}' if npc is not None else 'absent'


def slave_near():
    return npcs.query().where(lambda n: (n.id == MALE_SLAVE_ID or n.id == ESCAPED_SLAVE_ID) and talk_op_of(n) is not None).within_of(MALE_SLAVE, 6).nearest()


def talk_op_of(npc):
    for a in npc.actions():
        if a.lower().startswith('talk'):
            return a
    return None


def free_captain():
    return npcs.query().where(lambda n: n.id == MERCENARY_CAPTAIN_ID and metal_key_captain_available(n)).action('Talk-to').within_of(CAPTAIN, 10).nearest()


def targeting_captain():
    return npcs.query().where(lambda n: n.id == MERCENARY_CAPTAIN_ID and n.targets_me()).action('Attack').within_of(CAPTAIN, 10).nearest()


def any_captain():
    return npcs.query().where(lambda n: n.id == MERCENARY_CAPTAIN_ID).within_of(CAPTAIN, 10).nearest()


def captain_at(index, action='Attack'):
    if index is None:
        return None
    query = npcs.query().where(lambda n: n.index == index and n.id == MERCENARY_CAPTAIN_ID)
    if action:
        query = query.action(action)
    return query.within_of(CAPTAIN, 10).nearest()


def siad_desk():
    return locs.query().where(lambda l: l.id == SIAD_DESK_ID and l.tile().distance_to(SIAD_DESK) <= 3).action('Search').nearest()


class DesertMiningCampRoute:
    def __init__(self, host, destination='mineDeep'):
        self.host = host
        self.destination = destination

    def area(self):
        return desert_camp_route_area(game.tile())

    def phase(self, direction):
        return desert_camp_route_phase(direction, self.area(), self.destination)

    def needs_step(self, direction):
        return self.phase(direction) != 'done'

    def plan_supplies_at_open_bank(self):
        if not bank.is_open() or not bank.snapshot_ready():
            raise RuntimeError('desert camp: supply planning requires an authoritative open bank snapshot')
        snap = Record({'inventory': live_counts(inventory.items()), 'equipment': live_counts(equipment.items()), 'bank': live_counts(bank.items()),
                       'free_slots': inventory.free()})
        return plan_desert_camp_supplies(snap, self.destination)

    def withdraw_planned_supplies_at_open_bank(self, plan):
        """Use with yield from."""
        if not bank.is_open() or not bank.snapshot_ready():
            return self.fail('desert camp: route withdrawal requires an authoritative open bank snapshot')
        for step in plan.withdraw:
            before = inventory.count(step.name)
            took = yield from bank.withdraw_x(step.name, step.qty)
            if not took:
                return self.fail(f'desert camp: failed to withdraw {step.qty} {step.name}')
            landed = yield from execution.delay_until_ticks(lambda: inventory.count(step.name) >= before + step.qty, 7)
            if not landed:
                return self.fail(f'desert camp: withdrawal did not land for {step.name}')
        if self.destination == 'mineDeep' and not plan.recover_slave_outfit:
            banked = yield from self.bank_optional_desert_outfit()
            if not banked:
                return False
        withdrawn = ', '.join([f'{step.qty} {step.name}' for step in plan.withdraw]) or 'none'
        self.host.log(f"desert camp: route supplies ready; withdraw={withdrawn}; buyOutfit={', '.join(plan.buy_outfit) or 'none'}; buyPass={plan.buy_pass}; "
                      + f'recoverSlave={plan.recover_slave_outfit}; recoverMetal={plan.recover_metal_key}; recoverWrought={plan.recover_wrought_key}; slots={plan.required_slots}')
        return True

    def deposit_desert_pack_copies(self):
        """Use with yield from."""
        if not bank.is_open():
            self.host.log('desert camp: reopening Shantay bank after removing a worn desert item')
            opened = yield from banking.open(stand=SHANTAY_BANK, log=lambda m: self.host.log(f'  {m}'))
            if not opened:
                return self.fail('desert camp: could not reopen Shantay bank for the removed desert outfit')
            ready = yield from execution.delay_until_ticks(bank.snapshot_ready, 7)
            if not ready:
                return self.fail('desert camp: reopened Shantay bank did not produce an authoritative item snapshot')
        desert = [n.lower() for n in DESERT_OUTFIT]
        yield from bank.deposit_all_matching(lambda name, *_args: name.lower() in desert)
        gone = yield from execution.delay_until_ticks(lambda: len([n for n in DESERT_OUTFIT if inventory.contains(n)]) == 0, 7)
        if not gone:
            return self.fail(f"desert camp: bank did not accept optional desert outfit: {', '.join([n for n in DESERT_OUTFIT if inventory.contains(n)])}")
        return True

    def bank_optional_desert_outfit(self):
        """Use with yield from."""
        was_held = len([n for n in DESERT_OUTFIT if inventory.contains(n) or equipment.contains(n)]) > 0
        deposited = yield from self.deposit_desert_pack_copies()
        if not deposited:
            return False
        for name in DESERT_OUTFIT:
            if not equipment.contains(name):
                continue
            if bank.is_open():
                closed = yield from bank.close()
                if not closed:
                    return self.fail(f"desert camp: could not close Shantay bank before removing optional '{name}'")
            shut = yield from execution.delay_until_ticks(lambda: not bank.is_open(), 5)
            if not shut:
                return self.fail(f"desert camp: Shantay bank stayed open before removing optional '{name}'")
            if inventory.free() < 1:
                return self.fail(f"desert camp: no free slot to remove optional '{name}' at Shantay bank")
            removed = yield from equipment.unequip(name)
            if not removed:
                return self.fail(f"desert camp: could not remove optional '{name}' at Shantay bank")
            landed = yield from execution.delay_until_ticks(lambda: inventory.contains(name), 7)
            if not landed:
                return self.fail(f"desert camp: removed optional '{name}' did not reach the backpack")
            deposited = yield from self.deposit_desert_pack_copies()
            if not deposited:
                return False
        if not bank.is_open():
            return self.fail('desert camp: Shantay bank closed while removing the optional desert outfit')
        if was_held:
            self.host.log('desert camp: banked optional desert outfit; normal trips wear the slave disguise')
        return True

    def run_step(self, direction):
        """One step of the route, 'enter' or 'exit'. Use with yield from."""
        if quests.status('The Tourist Trap') == 'unknown' and quests.status('Tourist Trap') == 'unknown':
            self.host.log('desert camp: Tourist Trap status unavailable — waiting for the quest list')
            yield from execution.delay_ticks(1)
            return False
        if not quest_complete():
            return self.fail('desert camp: The Tourist Trap must be complete')
        area = self.area()
        phase = desert_camp_route_phase(direction, area, self.destination)
        self.host.log(f'desert camp: route {direction}; dest={self.destination}; area={area}; phase={phase}; tile={self.tile_label()}')
        self.host.set_status(f'desert camp: {phase}')
        if phase == 'unsupported':
            return self.fail(f'desert camp: unsupported route tile {self.tile_label()}')
        if phase == 'done':
            return True
        if direction == 'enter' and phase != 'exitMine':
            done = yield from self.enter(area)
            return done
        done = yield from self.exit(area)
        return done

    def walked(self, label, done):
        if done:
            self.host.log(f'desert camp: shared walk completed {label}; tile={self.tile_label()}')
        return done

    def enter(self, area):
        """Use with yield from."""
        if area == 'mainland' or area == 'shantayNorth':
            ok = yield from self.finish_shantay_provisioning()
            if ok:
                ok = yield from self.wear_travel_outfit()
            if ok:
                ok = yield from self.walk(SHANTAY_SOUTH, 1, 'Kharidian desert', 'desert')
            return self.walked('Shantay south', ok)
        if area == 'desert':
            ok = yield from self.wear_travel_outfit()
            if ok and not inventory.contains(METAL_KEY):
                ok = yield from self.recover_metal_key()
            if ok:
                ok = yield from self.walk(CAMP_INSIDE, 0, 'mining-camp surface', 'campSurface')
            return self.walked('outer gate in', ok)
        if area == 'campSurface':
            if self.destination == 'campSurface':
                ok = True
                if not inventory.contains(METAL_KEY):
                    ok = yield from self.recover_desk_keys()
                if ok:
                    ok = yield from self.wear(DESERT_OUTFIT, 'desert travel outfit')
                if ok:
                    self.host.log(f'desert camp: surface destination reached; tile={self.tile_label()}')
                return ok
            ok = True
            if not inventory.contains(WROUGHT_KEY):
                ok = yield from self.recover_desk_keys()
            if ok and not has_all(SLAVE_OUTFIT):
                ok = yield from self.recover_slave_outfit()
            if ok:
                ok = yield from self.wear(SLAVE_OUTFIT, 'slave disguise')
            if ok:
                ok = yield from self.walk(DESERT_CAMP_MINE_ANCHOR, 4, 'deep mine', 'mineDeep')
            return self.walked('camp surface → deep mine', ok)
        if area == 'mineEntrance' or area == 'mineLower':
            ok = yield from self.wear(SLAVE_OUTFIT, 'slave disguise')
            if not ok:
                return False
            if not inventory.contains(WROUGHT_KEY):
                return self.fail(f"desert camp: '{WROUGHT_KEY}' is required from inside the mine")
            ok = yield from self.walk(DESERT_CAMP_MINE_ANCHOR, 4, 'deep mine', 'mineDeep')
            return self.walked(f'resumed {area} → deep mine', ok)
        return self.fail(f"desert camp: unhandled enter area '{area}' at {self.tile_label()}")

    def exit(self, area):
        """Use with yield from."""
        if area == 'mineDeep' or area == 'mineLower' or area == 'mineEntrance':
            ok = yield from self.wear(SLAVE_OUTFIT, 'slave disguise', False)
            if ok:
                ok = yield from self.walk(CAMP_INSIDE, 3, 'mining-camp surface', 'campSurface')
            return self.walked('mine → camp surface', ok)
        if area == 'campSurface':
            ok = True
            if not inventory.contains(METAL_KEY):
                ok = yield from self.recover_desk_keys()
            if ok:
                if self.destination == 'mineDeep':
                    ok = yield from self.wear(SLAVE_OUTFIT, 'slave disguise')
                else:
                    ok = yield from self.wear(DESERT_OUTFIT, 'desert travel outfit')
            if ok:
                ok = yield from self.walk(CAMP_OUTSIDE, 0, 'outside mining-camp gate', 'desert')
            return self.walked('outer gate out', ok)
        if area == 'desert':
            ok = yield from self.walk(SHANTAY_NORTH, 1, 'Shantay bank side', 'shantayNorth')
            return self.walked('Shantay north', ok)
        return self.fail(f"desert camp: unhandled exit area '{area}' at {self.tile_label()}")

    def finish_shantay_provisioning(self):
        """Use with yield from."""
        target = 1 if self.destination == 'campSurface' or not has_all(SLAVE_OUTFIT) else 0
        missing = []
        for name in DESERT_OUTFIT:
            for _ in range(max(0, target - inventory.count(name) - equipment_count(name))):
                missing.append(name)
        if len(missing) > 0:
            bought = yield from self.buy_desert_outfit(missing)
            if not bought:
                return False
        if not inventory.contains(PASS):
            if inventory.count(COINS) < FIXED_PASS_COST:
                return self.fail('desert camp: no Shantay pass and fewer than 5 Coins after bank provisioning')
            bought = yield from self.buy_pass()
            if not bought:
                return False
        return True

    def wear_travel_outfit(self):
        """Use with yield from."""
        if self.destination == 'campSurface':
            worn = yield from self.wear(DESERT_OUTFIT, 'desert travel outfit')
        elif has_all(SLAVE_OUTFIT):
            worn = yield from self.wear(SLAVE_OUTFIT, 'slave disguise')
        else:
            worn = yield from self.wear(DESERT_OUTFIT, 'slave-disguise recovery outfit')
        return worn

    def recover_slave_outfit(self):
        """Trades a desert outfit to the male slave for his disguise. Use with yield from."""
        short = [n for n in DESERT_OUTFIT if inventory.count(n) + equipment_count(n) < 1]
        if len(short) > 0:
            return self.fail(f"desert camp: slave-outfit recovery needs one complete desert outfit; short {', '.join(short)}")
        ok = yield from self.wear(DESERT_OUTFIT, 'desert outfit')
        if ok:
            ok = yield from self.walk(MALE_SLAVE, 3, 'male slave')
        if not ok:
            return False
        loaded = yield from execution.delay_until(lambda: slave_near() is not None, 8000)
        if not loaded:
            return self.fail(f'desert camp: no male slave 825/826 loaded near {self.tile_label()}')
        slave = slave_near()
        talk = talk_op_of(slave) if slave is not None else None
        if slave is None or not talk or not slave.interact(talk):
            return self.fail(f'desert camp: could not talk to the male slave at {self.tile_label()}')
        opened = yield from execution.delay_until(lambda: chat_dialog.is_open() or chat_dialog.can_continue(), 8000)
        if not opened:
            return self.fail('desert camp: slave-outfit recovery dialogue did not open')
        self.host.log('desert camp: trading one desert outfit to replace the missing slave disguise')
        drained = yield from self.drain_interaction_dialog(["Yes, I'll trade."], lambda: has_all(SLAVE_OUTFIT))
        if not drained:
            return False
        if not has_all(SLAVE_OUTFIT):
            lacking = [n for n in SLAVE_OUTFIT if not inventory.contains(n) and not equipment.contains(n)]
            return self.fail(f"desert camp: slave trade ended without {', '.join(lacking)}")
        self.host.log('desert camp: recovered complete slave disguise')
        return True

    def claim_captain(self):
        """Queues for the Mercenary Captain until one is ours: the duel's captain's index, -1 with the key in hand, or
        None when it gave up. Use with yield from."""
        deadline = now_ms() + CAPTAIN_WAIT_MS
        last_wait_log_at = 0
        while now_ms() < deadline:
            if inventory.contains(METAL_KEY):
                return -1
            if metal_key_duel_needs_retreat(self.host.food_count(), True):
                yield from self.retreat_from_metal_key_duel('the Mercenary Captain wait consumed the food reserve')
                return None
            resumed = targeting_captain()
            if resumed is not None:
                self.host.log('desert camp: resuming the existing Mercenary Captain duel')
                return resumed.index
            captain = free_captain()
            if captain is not None and captain.interact('Talk-to'):
                acknowledged = yield from execution.delay_until(lambda: metal_key_captain_claim_acknowledged(chat_dialog.is_open() or chat_dialog.can_continue(), targeting_captain() is not None,
                                                                                                           inventory.contains(METAL_KEY)), 8000)
                if acknowledged:
                    if inventory.contains(METAL_KEY):
                        return -1
                    if chat_dialog.is_open() or chat_dialog.can_continue():
                        drained = yield from self.drain_interaction_dialog(CAPTAIN_KEY_DUEL)
                        if not drained:
                            return None
                    claimed = yield from execution.delay_until(lambda: targeting_captain() is not None or inventory.contains(METAL_KEY), 8000)
                    if claimed:
                        if inventory.contains(METAL_KEY):
                            return -1
                        ours = targeting_captain()
                        if ours is not None:
                            return ours.index
                    self.host.log('desert camp: another bot won the Mercenary Captain challenge — returning to the queue')
                else:
                    self.host.log('desert camp: Mercenary Captain interaction was not acknowledged — returning to the queue')
            if now_ms() - last_wait_log_at >= 30000:
                self.host.log(f'desert camp: waiting up to 245s for Mercenary Captain; observed={captain_note(any_captain())}')
                last_wait_log_at = now_ms()
            if event_signal.pending():
                self.host.log('desert camp: Captain wait interrupted by a random event — route will resume')
                return None
            yield from sustain.run()
            yield from execution.delay_ticks(1)
        self.fail(f'desert camp: Mercenary Captain unavailable after 245s; observed={captain_note(any_captain())}')
        return None

    def recover_metal_key(self):
        """Wins the Metal key from the Mercenary Captain, in a duel with Auto Retaliate off. Use with yield from."""
        if metal_key_duel_needs_retreat(self.host.food_count(), True):
            done = yield from self.retreat_from_metal_key_duel('fewer than 2 configured food items remain before the duel')
            return done
        if inventory.free() < 1:
            return self.fail('desert camp: no reserved slot for Metal key recovery')
        arrived = yield from self.walk(CAPTAIN, 5, 'Mercenary Captain')
        if not arrived:
            return False
        index = yield from self.claim_captain()
        if index is None:
            return False
        attacks = 0
        hp_xp_before = skills.xp('hitpoints')
        last_hp_xp = hp_xp_before
        last_hit_at = now_ms()
        if not inventory.contains(METAL_KEY):
            duel = targeting_captain()
            if duel is None or not duel.interact('Attack'):
                return self.fail('desert camp: could not retaliate against the attacking Mercenary Captain')
            index = duel.index
            attacks = 1
            self.host.log('desert camp: accepted Mercenary Captain duel; retaliating with Auto Retaliate off')
            facing = yield from execution.delay_until(lambda: facing_npc(index), 8000)
            if not facing:
                return self.fail('desert camp: retaliatory Attack was accepted but the Mercenary Captain did not become our target')
        deadline = now_ms() + DUEL_MS
        while not inventory.contains(METAL_KEY) and now_ms() < deadline:
            if metal_key_duel_needs_retreat(self.host.food_count(), captain_alive(captain_at(index))):
                done = yield from self.retreat_from_metal_key_duel('the Metal key duel reached its final configured food item')
                return done
            yield from sustain.run()
            has_key = inventory.contains(METAL_KEY)
            if has_key:
                break
            live = captain_at(index)
            if metal_key_retreat_after_sustain(has_key, self.host.food_count(), captain_alive(live)):
                done = yield from self.retreat_from_metal_key_duel('the Metal key duel consumed its food reserve')
                return done
            if not game.ingame():
                self.host.log('desert camp: Metal key duel ended by logout — waiting for the client to recover')
                return False
            if event_signal.pending():
                self.host.log('desert camp: Metal key recovery interrupted by a random event — route will resume')
                return False
            if self.area() != 'desert':
                return self.fail(f'desert camp: left the Mercenary Captain area during Metal key recovery; tile={self.tile_label()}')
            if live is not None:
                hp_xp = skills.xp('hitpoints')
                if hp_xp > last_hp_xp:
                    last_hp_xp = hp_xp
                    last_hit_at = now_ms()
                if captain_alive(live) and live.targets_me() and not facing_npc(live.index):
                    if not live.interact('Attack'):
                        return self.fail('desert camp: could not re-engage challenged Mercenary Captain after our target cleared')
                    attacks += 1
                    self.host.log(f'desert camp: re-engaged challenged Mercenary Captain after our target cleared; attack={attacks}')
            yield from execution.delay_ticks(1)
        if not inventory.contains(METAL_KEY):
            live = captain_at(index, None)
            health = f'{live.health}/{live.max_health}' if live is not None else 'absent'
            return self.fail(f"desert camp: Metal key recovery timed out after 180s; tile={self.tile_label()}; inCombat={game.in_combat()}; attackAttempts={attacks}; "
                             + f"hitpointsXp={skills.xp('hitpoints') - hp_xp_before}; lastHitAgo={round((now_ms() - last_hit_at) / 1000)}s; selfFace={game.facing()}; captain={health}")
        settled = yield from self.drain_owned_chat_until(lambda: inventory.contains(METAL_KEY))
        if not settled:
            return self.fail('desert camp: Metal key arrived but its reward modal did not settle')
        self.host.log(f"desert camp: recovered Metal key from Mercenary Captain; tile={self.tile_label()}; attacks={attacks}; hitpointsXp={skills.xp('hitpoints') - hp_xp_before}")
        return True

    def retreat_from_metal_key_duel(self, reason):
        """Runs for Shantay to refill before trying again; always False, so the route goes round again. Use with
        yield from."""
        self.host.set_status('desert camp: emergency food retreat')
        self.host.log(f'desert camp: {reason}; retreating to Shantay before continuing combat')
        yield from sustain.run()
        if inventory.contains(METAL_KEY):
            self.host.log('desert camp: Metal key arrived while preparing the emergency retreat — continuing the route')
            return False
        escaped = yield from traversal.walk_resilient(SHANTAY_NORTH, radius=2, attempts=12, timeout_ms=180000, log=lambda m: self.host.log(f'  {m}'))
        if not escaped and event_signal.pending():
            self.host.log('desert camp: emergency food retreat interrupted by a random event — route will resume')
            return False
        if not escaped or desert_camp_route_area(game.tile()) != 'shantayNorth':
            return self.fail(f'desert camp: emergency food retreat failed; tile={self.tile_label()}')
        if inventory.contains(METAL_KEY):
            self.host.log('desert camp: Metal key arrived during the emergency retreat; safely reached Shantay')
            return False
        self.host.log(f'desert camp: {reason}; safely retreated to Shantay — refilling before retrying')
        return False

    def recover_desk_keys(self):
        """Searches Captain Siad's desk, which awards every key missing. Use with yield from."""
        wanted = [METAL_KEY] if self.destination == 'campSurface' else [CELL_KEY, METAL_KEY, WROUGHT_KEY]
        awards = [n for n in [CELL_KEY, METAL_KEY, WROUGHT_KEY] if not inventory.contains(n)]
        if inventory.free() < len(awards):
            return self.fail(f'desert camp: Captain Siad desk needs {len(awards)} free slot(s), only {inventory.free()} available')
        arrived = yield from self.walk(SIAD_DESK, 2, "Captain Siad's desk")
        if not arrived:
            return False
        loaded = yield from execution.delay_until(lambda: siad_desk() is not None, 8000)
        if not loaded:
            return self.fail(f"desert camp: Captain Siad's exact desk did not load near {self.tile_label()}")
        desk = siad_desk()
        if desk is None or not desk.interact('Search'):
            return self.fail(f"desert camp: Captain Siad's desk has no usable Search action at {self.tile_label()}")
        settled = yield from self.drain_owned_chat_until(lambda: len([n for n in awards if not inventory.contains(n)]) == 0)
        if not settled:
            return self.fail(f"desert camp: Captain Siad's desk did not award {', '.join(awards)}")
        lacking = [n for n in wanted if not inventory.contains(n)]
        if len(lacking) > 0:
            return self.fail(f"desert camp: Captain Siad's desk recovery finished without {', '.join(lacking)}")
        key = 'Metal key' if self.destination == 'campSurface' else 'Wrought iron key'
        self.host.log(f"desert camp: recovered {key} from Captain Siad's desk; tile={self.tile_label()}")
        return True

    def buy_desert_outfit(self, items):
        """Use with yield from."""
        arrived = yield from self.walk(SHANTAY_SHOP, 3, 'Shantay shop')
        if not arrived:
            return False
        opened = yield from shop.open('Shantay')
        if not opened:
            return self.fail('desert camp: could not open the Shantay Pass Shop')
        stock = shop.stock()
        for name in items:
            entries = [i for i in stock if (i.name or '').lower() == name.lower() and i.count > 0]
            if len(entries) == 0:
                yield from shop.close()
                return self.fail(f"desert camp: Shantay shop has no '{name}' in stock")
        for name in items:
            before = inventory.count(name)
            bought = yield from shop.buy(name, 1)
            if bought != 1 or inventory.count(name) != before + 1:
                yield from shop.close()
                return self.fail(f"desert camp: failed to buy required '{name}' (bought {bought})")
            self.host.log(f'desert camp: bought required {name}')
        yield from shop.close()
        return True

    def buy_pass(self):
        """Buys a pass from Shantay himself, at the fixed 5gp. Use with yield from."""
        if inventory.free() < 1:
            return self.fail('desert camp: need 1 free inventory slot before buying a Shantay pass')
        arrived = yield from self.walk(SHANTAY_SHOP, 3, 'Shantay shop')
        if not arrived:
            return False
        before = inventory.count(COINS)
        shantay = npcs.query().name('Shantay').action('Talk-to').nearest()
        if shantay is None or not shantay.interact('Talk-to'):
            return self.fail('desert camp: could not talk to Shantay for a fixed-price pass')
        opened = yield from execution.delay_until(lambda: chat_dialog.is_open() or chat_dialog.can_continue(), 8000)
        if not opened:
            return self.fail('desert camp: Shantay pass dialogue did not open')
        drained = yield from self.drain_interaction_dialog(['I want to buy a shantay pass for 5 gold coins.'])
        if not drained:
            return False
        settled = yield from self.drain_owned_chat_until(lambda: inventory.contains(PASS))
        if not settled:
            return self.fail('desert camp: Shantay pass confirmation did not complete')
        landed = yield from execution.delay_until_ticks(lambda: inventory.contains(PASS) and inventory.count(COINS) == before - FIXED_PASS_COST, 8)
        if not landed:
            return self.fail('desert camp: fixed-price Shantay pass purchase did not land')
        self.host.log('desert camp: bought 1 Shantay pass for 5 Coins')
        return True

    def wear(self, items, label, require_pickaxe=True):
        """Use with yield from."""
        for name in items:
            if equipment.contains(name):
                continue
            if not inventory.contains(name):
                return self.fail(f"desert camp: missing required {label} item '{name}'")
            worn = yield from equipment.equip(name)
            if not worn:
                self.host.log(f"desert camp: {label} item '{name}' not yet confirmed — waiting for the live equipment state")
                later = yield from execution.delay_until_ticks(lambda: equipment.contains(name), 10)
                if not later:
                    return self.fail(f"desert camp: could not equip required {label} item '{name}'")
                self.host.log(f"desert camp: {label} item '{name}' confirmed after a delayed equipment update")
        if require_pickaxe and pickaxe_name(equipment.items()) is None and pickaxe_name(inventory.items()) is None:
            return self.fail('desert camp: no pickaxe equipped or in the inventory')
        return True

    def walk(self, destination, radius, label, expected_area=None):
        """Use with yield from."""
        here = game.tile()
        if here is not None and here.level == destination.level and destination.distance_to(here) <= radius and (expected_area is None or self.area() == expected_area):
            return True
        self.host.log(f'desert camp: shared walk to {label} {destination}; from={self.tile_label()}')
        arrived = yield from traversal.walk_resilient(destination, radius=radius, attempts=12, timeout_ms=180000, log=lambda m: self.host.log(f'  {m}'))
        if not arrived and event_signal.pending():
            self.host.log(f'desert camp: {label} interrupted by a random event — route will resume afterward')
            return False
        if not arrived:
            return self.fail(f'desert camp: could not reach {label} {destination}; from={self.tile_label()}')
        if expected_area is not None and self.area() != expected_area:
            return self.fail(f'desert camp: {label} walk ended in area={self.area()}, expected={expected_area}; tile={self.tile_label()}')
        return True

    def drain_owned_chat_until(self, done):
        """Continues the chat until done() holds with it shut for two ticks running. Use with yield from."""
        quiet = False
        for _ in range(30):
            if not chat_dialog.is_open():
                if done():
                    if quiet:
                        return True
                    quiet = True
                else:
                    quiet = False
                yield from execution.delay_ticks(1)
                continue
            quiet = False
            if not chat_dialog.can_continue():
                return False
            continued = yield from chat_dialog.continue_()
            if not continued:
                return False
        return not chat_dialog.is_open() and done() and quiet

    def drain_interaction_dialog(self, allowed_options, done=None):
        """Drives a dialogue through only the options allowed. Use with yield from."""
        allowed = [normalize(o) for o in allowed_options]
        reached_done = False
        for _ in range(140):
            if event_signal.pending():
                return False
            if done is not None and done():
                reached_done = True
            if chat_dialog.can_continue():
                continued = yield from chat_dialog.continue_()
                if not continued:
                    return self.fail('desert camp: dialogue Continue failed')
                yield from execution.delay_ticks(1)
                continue
            options = chat_dialog.options()
            if len(options) > 0:
                choices = [o for o in options if normalize(o) in allowed]
                if len(choices) == 0:
                    return self.fail(f"desert camp: unexpected dialogue options [{' | '.join(options)}]")
                chose = yield from chat_dialog.choose_option(choices[0])
                if not chose:
                    return self.fail(f"desert camp: could not choose dialogue option '{choices[0]}'")
                yield from execution.delay_ticks(1)
                continue
            if not chat_dialog.is_open():
                if done is None or reached_done:
                    return True
            yield from execution.delay_ticks(1)
        return self.fail('desert camp: dialogue exceeded 140 steps')

    def tile_label(self):
        tile = game.tile()
        return f'({tile.x},{tile.z},{tile.level})' if tile is not None else '(unavailable)'

    def fail(self, reason):
        self.host.log(reason)
        self.host.set_status(f'{reason} — stopped')
        self.host.stop(reason)
        return False
