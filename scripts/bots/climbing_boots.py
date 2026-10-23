# Buys climbing boots from Tenzing in Burthorpe and banks them at Falador West, withdrawing exactly the gp a pack
# of boots costs so the last pair takes the coin stack's slot: rs2b0t's ClimbingBoots (MIT, see thirdparty/rs2b0t).
# Falador teleport runes for the way back are optional. It needs Death Plateau complete.

import time

from rs2004.catalogs import STAFF_RUNES

SCRIPT_NAME = 'ClimbingBoots'
BOOT_COST = 12
BOOTS = 'Climbing boots'
COINS = 'Coins'
TENZING = 'Tenzing'
PACK_SIZE = 28
FALADOR_TELE_LEVEL = 37
DEATH_PLATEAU_QUEST = 'Death Plateau'
# (rune, per cast)
FALADOR_TELE_RUNES = [('Law rune', 1), ('Air rune', 3), ('Water rune', 1)]
MILKMAN_PREFER = ["I'm not the milkman", 'I need your help', 'Nothing, thanks!']
BANK_STAND = Tile(2946, 3369, 0)
TENZING_INSIDE = Tile(2820, 3556, 0)
TENZING_DOOR = Tile(2823, 3555, 0)
FALADOR_LANDING = Tile(2965, 3378, 0)
WALK_ATTEMPTS = 4
WALK_TIMEOUT_MS = 300000

SETTINGS = {
    'use_teleport': SettingDef('boolean', True, 'Falador teleport back to bank',
                               help='carry Falador tele runes and cast after a full pack; off walks back to Falador West instead'),
    'rune_stock': SettingDef('number', 50, 'Falador teles of runes to carry', 1, 1000,
                             help='Law and Water x this, Air x 3x this. They stay in the pack; the last boot buy spends the coin stack into that slot',
                             show_if={'key': 'use_teleport', 'any_of': ['true']}),
}


# The pure decisions, kept apart from the game so they can be tested without a client.

def provided_runes(worn_names):
    """The runes the worn staves stand in for."""
    out = []
    for name in worn_names:
        wanted = name.lower()
        for staff, runes in STAFF_RUNES.items():
            if staff.lower() == wanted:
                out.extend(runes)
    return out


def carried_tele_runes(provided):
    return [(rune, per_cast) for rune, per_cast in FALADOR_TELE_RUNES if rune not in provided]


def trip_qty(pack_size, rune_stacks):
    return max(0, pack_size - max(0, rune_stacks))


def trip_gp(qty):
    return max(0, qty) * BOOT_COST


def remaining_gp(boots, qty):
    return max(0, qty - boots) * BOOT_COST


def rune_withdraw(per_cast, casts, held):
    return max(0, per_cast * max(0, casts) - max(0, held))


def other_slots(used, coins, boots, rune_stacks_held):
    return used - (1 if coins > 0 else 0) - boots - rune_stacks_held


def still_buying(coins, boots, qty, used, pack_size):
    if coins < BOOT_COST or boots >= qty:
        return False
    if used < pack_size:
        return True
    return coins == BOOT_COST


def can_finish_trip(coins, boots, used, qty, rune_stacks_held):
    if other_slots(used, coins, boots, rune_stacks_held) > 0:
        return False
    if boots >= qty:
        return False
    return coins == remaining_gp(boots, qty) and coins >= BOOT_COST


def trip_complete(boots, qty):
    return boots >= qty


def shop_prefer(buying):
    return ['Can I buy some Climbing boots?', 'OK, sounds good.'] if buying else ['Nothing, thanks!']


def pick_shop_option(options, prefer):
    for want in prefer:
        for option in options:
            if want.lower() in option.lower():
                return option
    return None


def hut_door_op(loc):
    acts = loc.actions()
    for prefix in ['open', 'knock']:
        for a in acts:
            if a.lower().startswith(prefix):
                return a
    return None


def in_tenzing_hut(tile):
    return tile is not None and tile.level == TENZING_INSIDE.level and TENZING_INSIDE.distance_to(tile) <= 1


def dialog_up():
    return chat_dialog.is_open() or chat_dialog.can_continue()


class ClimbingBoots(LoopingBot):
    def on_start(self):
        self.loop_delay = 600
        self.status = 'starting'
        self.trips = 0
        self.bought = 0
        self.stopped = False
        self.started_at = time.time()
        yield from execution.delay_until(lambda: game.ingame() and game.tile() is not None, 0)
        self.use_teleport = self.settings.bool('use_teleport', True)
        self.rune_stock = self.settings.num('rune_stock', 50)
        yield from execution.delay_until(lambda: quests.status(DEATH_PLATEAU_QUEST) != 'unknown', 5000)
        quest = quests.status(DEATH_PLATEAU_QUEST)
        if quest != 'complete':
            self.log(f'{SCRIPT_NAME} will not run because Death Plateau is not finished (status: {quest})')
            self.stop(f'{SCRIPT_NAME}: Death Plateau is not finished')
            return
        if not self.use_teleport:
            self.log(f'{SCRIPT_NAME}: Falador West bank, walking back, {BOOT_COST}gp a pair from Tenzing')
        elif skills.level('magic') < FALADOR_TELE_LEVEL:
            self.log(f"{SCRIPT_NAME}: Magic {skills.level('magic')} is below {FALADOR_TELE_LEVEL}; bank trips will walk until you can Falador teleport")
        else:
            self.log(f'{SCRIPT_NAME}: Falador West bank, {self.rune_stock} Falador teles of runes, {BOOT_COST}gp a pair from Tenzing')

    def stop(self, reason):
        self.stopped = True
        self.request_finish(reason)

    def loop(self):
        if not game.ingame() or game.tile() is None or not game.scene_ready():
            yield from execution.delay_ticks(2)
            return
        if self.stopped:
            yield from execution.delay_ticks(8)
            return
        # The settings can change while it runs.
        self.use_teleport = self.settings.bool('use_teleport', True)
        self.rune_stock = self.settings.num('rune_stock', 50)
        qty = self.plan_qty()
        if trip_complete(inventory.count(BOOTS), qty) or not self.ready_to_buy(qty):
            if trip_complete(inventory.count(BOOTS), qty):
                back = yield from self.return_to_bank()
                if not back:
                    return
            kitted = yield from self.bank_leg(qty)
            if not kitted:
                return
        if trip_complete(inventory.count(BOOTS), qty) or not self.ready_to_buy(qty):
            return
        yield from self.buy_leg(qty)

    def worn_names(self):
        return [item.name for item in equipment.items() if item.name]

    def carried(self):
        return carried_tele_runes(provided_runes(self.worn_names())) if self.use_teleport else []

    def plan_qty(self):
        return trip_qty(PACK_SIZE, len(self.carried()))

    def rune_stacks_held(self):
        return len([rune for rune, _ in self.carried() if inventory.count(rune) > 0])

    def ready_to_buy(self, qty):
        return can_finish_trip(inventory.count(COINS), inventory.count(BOOTS), inventory.used(), qty, self.rune_stacks_held())

    def walk_to(self, dest, radius, what):
        """Use with yield from."""
        here = game.tile()
        if here is not None and here.level == dest.level and dest.distance_to(here) <= radius:
            return True
        self.status = f'walking to {what}'
        walked = yield from traversal.walk_resilient(dest, radius=radius, attempts=WALK_ATTEMPTS, timeout_ms=WALK_TIMEOUT_MS, log=lambda m: self.log(f'  {m}'))
        return walked

    def open_hut_door(self):
        """Use with yield from."""
        door = locs.query().name('Door').where(lambda l: l.distance() <= 6 and hut_door_op(l) is not None).nearest()
        if door is None:
            return False
        op = hut_door_op(door)
        if not op:
            return False
        self.log(f"{op} {door.name} into Tenzing's hut")
        door.interact(op)
        talked = yield from execution.delay_until(dialog_up, 2500)
        if talked:
            yield from self.drive_milkman()
        yield from execution.delay_ticks(2)
        return True

    def drive_milkman(self):
        """Use with yield from."""
        for _ in range(20):
            if chat_dialog.can_continue():
                yield from chat_dialog.continue_()
                yield from execution.delay_ticks(1)
                continue
            opts = chat_dialog.options()
            if len(opts) > 0:
                yield from chat_dialog.choose_option(pick_shop_option(opts, MILKMAN_PREFER) or opts[len(opts) - 1])
                yield from execution.delay_ticks(2)
                continue
            if not chat_dialog.is_open():
                return
            yield from execution.delay_ticks(1)

    def bank_leg(self, qty):
        """Banks for the trip's kit: the runes and exactly the gp. Use with yield from."""
        gp = trip_gp(qty)
        here = game.tile()
        if here is None or BANK_STAND.distance_to(here) > 8:
            arrived = yield from self.walk_to(BANK_STAND, 3, 'Falador West bank')
            if not arrived:
                return False
        self.status = 'banking'
        opened = yield from banking.open(stand=BANK_STAND, log=lambda m: self.log(f'  {m}'))
        if not opened:
            self.log('could not open the bank, retrying')
            return False
        keep = [rune.lower() for rune, _ in self.carried()]
        yield from bank.deposit_all_matching(lambda name, *_args: name.lower() not in keep)
        for rune, per_cast in self.carried():
            need = rune_withdraw(per_cast, self.rune_stock, inventory.count(rune))
            if need <= 0:
                continue
            take = min(need, bank.count(rune))
            if take <= 0:
                if inventory.count(rune) < per_cast:
                    self.log(f'{SCRIPT_NAME}: bank has no {rune} for Falador teleport')
                    self.stop(f'{SCRIPT_NAME}: bank has no {rune} for Falador teleport')
                    return False
                continue
            took = yield from bank.withdraw_x(rune, take)
            if not took:
                self.log(f'could not withdraw {take} {rune}, retrying')
                return False
        have = inventory.count(COINS)
        if have != gp:
            if have > 0:
                yield from bank.deposit_all_matching(lambda name, *_args: name.lower() == COINS.lower())
            if bank.count(COINS) < gp:
                self.log(f'{SCRIPT_NAME}: need {gp}gp for {qty} pairs at {BOOT_COST}gp, bank has {bank.count(COINS)}')
                self.stop(f'{SCRIPT_NAME}: need {gp}gp, bank has {bank.count(COINS)}')
                return False
            took = yield from bank.withdraw_x(COINS, gp)
            if not took:
                self.log(f'could not withdraw {gp}gp, retrying')
                return False
        yield from bank.close()
        runes = ', '.join([rune for rune, _ in self.carried()])
        self.log(f'trip kit: {gp}gp + {runes} -> {qty} {BOOTS}' if runes else f'trip kit: {gp}gp -> {qty} {BOOTS}')
        return self.ready_to_buy(qty)

    def buy_leg(self, qty):
        """Use with yield from."""
        before = inventory.count(BOOTS)
        reached = yield from self.reach_tenzing()
        if not reached:
            return False
        self.status = f'buying {qty} {BOOTS}'
        shopped = yield from self.drive_shop(qty)
        if not shopped:
            return False
        got = inventory.count(BOOTS) - before
        if got > 0:
            self.bought += got
            self.log(f'bought {got} {BOOTS} ({inventory.count(BOOTS)}/{qty} this trip)')
        if trip_complete(inventory.count(BOOTS), qty):
            self.trips += 1
        return got > 0 or trip_complete(inventory.count(BOOTS), qty)

    def return_to_bank(self):
        """Use with yield from."""
        if self.use_teleport:
            teleported = yield from self.falador_teleport()
            if teleported:
                return True
            self.log('Falador teleport did not fire, walking back to the bank')
        walked = yield from self.walk_to(BANK_STAND, 3, 'Falador West bank')
        return walked

    def falador_teleport(self):
        """Use with yield from."""
        if not self.use_teleport or skills.level('magic') < FALADOR_TELE_LEVEL:
            return False
        for rune, per_cast in self.carried():
            if inventory.count(rune) < per_cast:
                return False
        here = game.tile()
        if here is not None and FALADOR_LANDING.distance_to(here) <= 20:
            return True
        self.status = 'Falador teleport'
        if not game.teleport('Falador'):
            return False
        landed = yield from execution.delay_until(lambda: game.tile() is not None and FALADOR_LANDING.distance_to(game.tile()) <= 20, 8000)
        return landed

    def reach_tenzing(self):
        """Use with yield from."""
        if in_tenzing_hut(game.tile()) and npcs.query().name(TENZING).within(3).nearest() is not None:
            return True
        self.status = "walking into Tenzing's hut"
        walked = yield from self.walk_to(TENZING_INSIDE, 1, 'Tenzing')
        if walked:
            return in_tenzing_hut(game.tile())
        self.log('path into the hut failed, opening the front door')
        at_door = yield from self.walk_to(TENZING_DOOR, 2, "Tenzing's door")
        if not at_door:
            return False
        yield from self.open_hut_door()
        walked = yield from self.walk_to(TENZING_INSIDE, 1, 'Tenzing')
        return walked

    def talk_to_tenzing(self):
        """Use with yield from."""
        if dialog_up():
            return True
        if not in_tenzing_hut(game.tile()):
            self.log('Tenzing is inside the hut, walking in before talking')
            reached = yield from self.reach_tenzing()
            if not reached:
                return False
        npc = npcs.query().name(TENZING).nearest()
        if npc is None:
            self.log(f'no {TENZING} nearby to talk to')
            return False
        if npc.distance() > 2:
            self.log(f'{TENZING} is {npc.distance()}t away, stepping closer')
            walked = yield from self.walk_to(TENZING_INSIDE, 1, 'Tenzing')
            if not walked:
                return False
        npc.interact(talk_op(npc.actions()) or 'Talk-to')
        talked = yield from execution.delay_until(dialog_up, 5000)
        if talked:
            return True
        self.log('talk did not open, opening the hut door and retrying')
        yield from self.open_hut_door()
        walked = yield from self.walk_to(TENZING_INSIDE, 1, 'Tenzing')
        if not walked:
            return False
        retry = npcs.query().name(TENZING).nearest()
        if retry is None:
            return False
        retry.interact(talk_op(retry.actions()) or 'Talk-to')
        talked = yield from execution.delay_until(dialog_up, 5000)
        return talked

    def drive_shop(self, qty):
        """Use with yield from."""
        def buying():
            return still_buying(inventory.count(COINS), inventory.count(BOOTS), qty, inventory.used(), PACK_SIZE)

        if not buying() and trip_complete(inventory.count(BOOTS), qty):
            return True
        talked = yield from self.talk_to_tenzing()
        if not talked:
            self.log(f'could not talk to {TENZING}, retrying')
            return False
        for _ in range(240):
            want_buy = buying()
            if chat_dialog.can_continue():
                yield from chat_dialog.continue_()
                yield from execution.delay_ticks(1)
                continue
            opts = chat_dialog.options()
            if len(opts) > 0:
                pick = pick_shop_option(opts, shop_prefer(want_buy))
                if not pick:
                    self.log(f'{TENZING} is not selling {BOOTS}, Death Plateau must be complete')
                    self.stop(f'{SCRIPT_NAME}: {TENZING} did not offer Climbing boots')
                    return False
                yield from chat_dialog.choose_option(pick)
                yield from execution.delay_ticks(2)
                continue
            # A message box in the main area, such as a purchase's.
            if modals.is_open():
                yield from modals.close()
                yield from execution.delay_ticks(1)
                continue
            if not chat_dialog.is_open():
                if trip_complete(inventory.count(BOOTS), qty):
                    return True
                if want_buy:
                    talked = yield from self.talk_to_tenzing()
                    if not talked:
                        return False
                    continue
                return trip_complete(inventory.count(BOOTS), qty)
            yield from execution.delay_ticks(1)
        return trip_complete(inventory.count(BOOTS), qty)

    def on_progress_report(self):
        return {'Status': self.status, 'Bought': self.bought, 'Trips': self.trips, 'Boots': inventory.count(BOOTS), 'Coins': inventory.count(COINS)}


BOT = define_bot(
    name='ClimbingBoots',
    create=ClimbingBoots,
    description='Falador West to Tenzing climbing-boot buyer. Withdraws exact gp so the last pair replaces the coin stack. Optional Falador teleport runes for the walk back. Needs Death Plateau complete.',
    category='Money making',
    tags=['tenzing', 'climbing boots', 'burthorpe', 'falador', 'bank', 'teleport'],
    settings_schema=SETTINGS,
)
