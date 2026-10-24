# Plays the Ranging Guild's archery competition for tickets and trades every 2000 for 50 rune arrows: rs2b0t's
# RangingGuild (MIT, see thirdparty/rs2b0t). It pays the judge 200 coins a round, shoots the ten arrows from behind
# the haystacks, and banks at Seers' Village for coins and the best bow. Ranged 40 for the guild's door.

import time

from bots.rangingguild.logic import ARCHERY_TICKET, BOWS, BRONZE_ARROW, BRONZE_ARROW_NAME, COINS, COINS_NAME, ENTRY_FEE, FIRE_OP, JUDGE
from bots.rangingguild.logic import JUDGE_PREFS, JUDGE_STAND, MERCHANT, MERCHANT_STAND, RANGED_REQUIRED, RUNE_ARROW, RUNE_ARROWS_PER_TRADE
from bots.rangingguild.logic import SEERS_BANK, SHOTS_PER_ROUND, STAND, TARGET, TICKET_NAME, TICKETS_PER_RUNE_ARROWS, VARP_TARGET_COUNT
from bots.rangingguild.logic import VARP_TARGET_HIT, VARP_TARGET_SCORE, WorldView, best_bow, classify_shot, decide, hit_label, hit_points
from bots.rangingguild.logic import is_bow, pick_option

SETTINGS = {
    'coins_per_trip': SettingDef('number', 10000, 'Coins per bank trip', ENTRY_FEE, 1000000,
                                 help='200 coins buys a round of ten shots; the bot banks for more when the pack runs dry'),
}

KEEP = [b.name for b in BOWS] + [COINS_NAME, TICKET_NAME, BRONZE_ARROW_NAME]
CHAT_MS = 20000
CHAT_IDLE_TICKS = 3
SHOT_MS = 6000
MODAL_MS = 1500
SHOP_MS = 5000
MAX_FAILURES = 12
# Recovery passes with no progress between them before the script gives up for good.
MAX_RECOVERIES = 3
MAX_BANK_FAILS = 4
TARGET_RANGE = 12

# The screens, found by their text: a shot's result, and the ticket shop with its rune arrows.
TARGET_RESULT_TEXT = 'Target View.'
TICKET_SHOP_TEXT = 'What would you like to buy with your tickets?'
RUNE_ARROWS_TEXT = '50 Rune Arrows'
RUNE_ARROWS_OPTION = 'buy for 2,000 tickets'


def now_ms():
    return time.time() * 1000


def main_has_text(text):
    main = reader.main_modal()
    return main >= 0 and len(interfaces.find(text, None, main)) > 0


def target_result_open():
    return main_has_text(TARGET_RESULT_TEXT)


def ticket_shop_open():
    return main_has_text(TICKET_SHOP_TEXT)


def rune_arrows_button():
    """The ticket shop's buy button beside the rune arrows: the shop has two at 2,000 tickets, so it's the one
    nearest their label."""
    main = reader.main_modal()
    labels = interfaces.find(RUNE_ARROWS_TEXT, None, main) if main >= 0 else []
    if not labels:
        return None
    label = labels[0]
    best = None
    best_distance = -1
    for component in interfaces.find(None, None, main):
        options = [o.lower() for o in (component.options or []) if o]
        if len([o for o in options if o.startswith(RUNE_ARROWS_OPTION)]) == 0:
            continue
        dx = component.x - label.x
        dy = component.y - label.y
        distance = dx * dx + dy * dy
        if best is None or distance < best_distance:
            best = component
            best_distance = distance
    return best


class RangingGuild(LoopingBot):
    loop_delay = 0

    def on_start(self):
        self.status = 'starting'
        self.rounds = 0
        self.shots = 0
        self.round_points = 0
        self.tickets_earned = 0
        self.arrows_bought = 0
        self.trips = 0
        self.failures = 0
        self.recoveries = 0
        self.pending_recovery = None
        self.bank_fails = 0
        yield from execution.delay_until(lambda: game.ingame() and game.tile() is not None, 0)
        self.started_at = time.time()
        self.xp_start = skills.xp('ranged')
        level = skills.level('ranged')
        if level < RANGED_REQUIRED:
            self.log(f'RangingGuild: the guild door needs Ranged {RANGED_REQUIRED} (have {level}). Stopping.')
            raise RuntimeError('RangingGuild: Ranged level too low')
        self.log(f'RangingGuild: {ENTRY_FEE} coins a round, {TICKETS_PER_RUNE_ARROWS} tickets per {RUNE_ARROWS_PER_TRADE} rune arrows, '
                 + f'{self.coins_per_trip()} coins per bank trip')

    def recovery_anchor(self):
        return STAND

    def on_progress_report(self):
        minutes = (time.time() - self.started_at) / 60
        xp = skills.xp('ranged') - self.xp_start
        return {
            'Status': self.status,
            'Rounds': self.rounds,
            'Shots': self.shots,
            'Tickets earned': self.tickets_earned,
            'Tickets held': inventory.count_by_id(ARCHERY_TICKET),
            'Rune arrows bought': self.arrows_bought,
            'Bank trips': self.trips,
            'Ranged xp/hr': f'{(xp / minutes * 60 / 1000):.1f}k' if minutes > 0.5 else '-',
        }

    def loop(self):
        if self.pending_recovery is not None:
            message = self.pending_recovery
            self.pending_recovery = None
            yield from self.recover(message)
            return
        yield from self.settle()
        action = decide(self.view())
        if action == 'redeem':
            yield from self.redeem()
        elif action == 'collect':
            yield from self.collect()
        elif action == 'wield-bow':
            yield from self.wield_bow()
        elif action == 'wield-arrows':
            yield from self.wield_arrows()
        elif action == 'shoot':
            yield from self.shoot()
        elif action == 'restock-arrows':
            yield from self.restock_arrows()
        elif action == 'enter':
            yield from self.enter()
        elif action == 'bank':
            yield from self.bank_trip()
        yield from execution.delay_ticks(1)

    def coins_per_trip(self):
        return self.settings.num('coins_per_trip', 10000)

    def view(self):
        worn = equipment.items()
        return WorldView(
            target_count=reader.varp(VARP_TARGET_COUNT),
            tickets=inventory.count_by_id(ARCHERY_TICKET),
            coins=inventory.count_by_id(COINS),
            bow_worn=len([i for i in worn if is_bow(i.name)]) > 0,
            bow_held=len([i for i in inventory.items() if is_bow(i.name)]) > 0,
            bronze_worn=sum([i.count for i in worn if i.id == BRONZE_ARROW]),
            bronze_held=inventory.count_by_id(BRONZE_ARROW),
        )

    # Why: a Ranged level-up box lands between shots, and the judge talk retries on sight of any open chat, so twelve
    # talks in a row failed live against one box nobody clicked through.
    def settle(self):
        """A result box, an idle ticket shop or a level-up page left up from the last pass swallows the next click."""
        if target_result_open() or (ticket_shop_open() and inventory.count_by_id(ARCHERY_TICKET) < TICKETS_PER_RUNE_ARROWS):
            yield from modals.close()
        yield from self.drain_chat()

    def enter(self):
        self.status = 'paying the judge'
        opened = yield from self.open_judge()
        if not opened:
            return
        started = yield from self.drive_chat(lambda: reader.varp(VARP_TARGET_COUNT) >= 1)
        if not started:
            self.fail('the judge did not start a round')
            return
        self.progress()
        self.round_points = 0
        self.log(f'paid {ENTRY_FEE} coins for a round of {SHOTS_PER_ROUND} ({inventory.count_by_id(COINS)} coins left)')

    def restock_arrows(self):
        self.status = 'buying arrows from the judge'
        opened = yield from self.open_judge()
        if not opened:
            return

        def restocked():
            v = self.view()
            return v.bronze_held + v.bronze_worn > 0

        sold = yield from self.drive_chat(restocked)
        if not sold:
            self.fail('the judge did not sell more arrows')
            return
        self.progress()
        self.log('bought 10 bronze arrows from the judge')

    def collect(self):
        self.status = 'collecting tickets'
        score = reader.varp(VARP_TARGET_SCORE)
        before = inventory.count_by_id(ARCHERY_TICKET)
        opened = yield from self.open_judge()
        if not opened:
            return
        paid = yield from self.drive_chat(lambda: reader.varp(VARP_TARGET_COUNT) == 0)
        if not paid:
            self.fail('the judge did not pay out')
            return
        yield from execution.delay_until(lambda: inventory.count_by_id(ARCHERY_TICKET) > before, 2000)
        gained = inventory.count_by_id(ARCHERY_TICKET) - before
        self.rounds += 1
        self.tickets_earned += gained
        self.progress()
        execution.note_progress()
        self.log(f'round {self.rounds}: scored {score}, +{gained} tickets ({inventory.count_by_id(ARCHERY_TICKET)} held)')

    def open_judge(self):
        arrived = yield from self.walk_to(JUDGE_STAND, 3)
        if not arrived:
            self.fail('could not reach the judge')
            return False
        yield from self.drain_chat()
        status = yield from reach.npc_dialog(JUDGE, JUDGE_STAND, log=lambda m: self.log(f'  {m}'))
        if status != 'done':
            self.fail(f'could not talk to the judge ({status})')
            return False
        return True

    def drive_chat(self, goal):
        deadline = now_ms() + CHAT_MS
        idle = 0
        while now_ms() < deadline:
            if goal():
                yield from self.drain_chat()
                return True
            options = chat_dialog.options()
            if len(options) > 0:
                pick = pick_option(options, JUDGE_PREFS)
                if pick == -1:
                    self.log(f"judge offered [{' | '.join(options)}], none of it wanted")
                    return False
                yield from chat_dialog.choose_option(options[pick])
                continue
            if chat_dialog.can_continue():
                yield from chat_dialog.continue_()
                continue
            if not chat_dialog.is_open():
                idle += 1
                if idle >= CHAT_IDLE_TICKS:
                    return goal()
            yield from execution.delay_ticks(1)
        return goal()

    def drain_chat(self):
        for _ in range(6):
            if not chat_dialog.can_continue():
                break
            yield from chat_dialog.continue_()

    def wield_bow(self):
        bow = None
        for item in inventory.items():
            if is_bow(item.name):
                bow = item.name
                break
        if bow is None:
            return
        self.status = f'wielding the {bow}'
        wielded = yield from equipment.equip(bow)
        if not wielded:
            self.fail(f'could not wield the {bow}')
            return
        self.log(f'wielded the {bow}')

    def wield_arrows(self):
        self.status = 'wielding bronze arrows'
        wielded = yield from equipment.equip(BRONZE_ARROW_NAME)
        if not wielded:
            self.fail('could not wield the bronze arrows')
            return
        self.log(f'wielded {self.view().bronze_worn} bronze arrows')

    def shoot(self):
        if not self.at(STAND, 1):
            self.status = 'walking to the range'
            yield from self.walk_to(STAND, 1)
            return
        self.status = 'shooting'
        target = locs.query().name(TARGET).action(FIRE_OP).within(TARGET_RANGE).nearest()
        if target is None:
            self.fail('no target in the scene')
            yield from execution.delay_ticks(2)
            return
        count = reader.varp(VARP_TARGET_COUNT)
        mark = game_messages.mark()
        if not target.interact(FIRE_OP):
            self.fail('Fire-at was not sent')
            yield from execution.delay_ticks(2)
            return
        refusal = [None]

        def landed_or_refused():
            if reader.varp(VARP_TARGET_COUNT) > count:
                return True
            refusal[0] = classify_shot([m.text for m in game_messages.since(mark)])
            return refusal[0] is not None

        yield from execution.delay_until(landed_or_refused, SHOT_MS)
        if reader.varp(VARP_TARGET_COUNT) > count:
            hit = reader.varp(VARP_TARGET_HIT)
            points = hit_points(hit)
            self.shots += 1
            self.round_points += points
            self.progress()
            execution.note_progress()
            self.log(f'shot {count}/{SHOTS_PER_ROUND}: {hit_label(hit)} +{points} (round {self.round_points})')
            yield from execution.delay_until(lambda: target_result_open(), MODAL_MS)
            yield from modals.close_if_open()
            yield from self.drain_chat()
            return
        if refusal[0] is None:
            self.fail('the shot never landed')
            return
        if refusal[0] == 'too-close' or refusal[0] == 'unreachable':
            self.fail(f'shot refused: {refusal[0]}')
            return
        self.log(f'shot refused: {refusal[0]}')

    def redeem(self):
        self.status = 'buying rune arrows'
        if not ticket_shop_open():
            if not self.at(MERCHANT_STAND, 3):
                yield from self.walk_to(MERCHANT_STAND, 3)
                return
            status = yield from reach.entity_op(lambda: npcs.query().name(MERCHANT).nearest(), 'Talk-to', lambda: ticket_shop_open(),
                                                expect_ms=SHOP_MS, what=MERCHANT, log=lambda m: self.log(f'  {m}'))
            if status != 'done':
                self.fail(f'could not open the ticket shop ({status})')
            return
        arrows = inventory.count_by_id(RUNE_ARROW)
        button = rune_arrows_button()
        if button is None or not interfaces.click(button.id):
            self.fail('the rune arrow button was not sent')
            return
        bought = yield from execution.delay_until(lambda: inventory.count_by_id(RUNE_ARROW) >= arrows + RUNE_ARROWS_PER_TRADE, SHOP_MS)
        if not bought:
            self.fail('the ticket shop did not hand over the arrows')
            return
        self.arrows_bought += RUNE_ARROWS_PER_TRADE
        self.progress()
        execution.note_progress()
        self.log(f'bought {RUNE_ARROWS_PER_TRADE} rune arrows for {TICKETS_PER_RUNE_ARROWS} tickets ({inventory.count_by_id(ARCHERY_TICKET)} tickets, '
                 + f'{inventory.count_by_id(RUNE_ARROW)} rune arrows held)')

    def bank_trip(self):
        self.status = 'banking at Seers'
        opened = yield from banking.open(SEERS_BANK, log=lambda m: self.log(f'  {m}'))
        if not opened:
            self.bank_fails += 1
            if self.bank_fails >= MAX_BANK_FAILS:
                self.stop('could not open the Seers bank')
                return
            self.log('could not open the bank, will retry')
            return
        self.bank_fails = 0
        self.trips += 1
        yield from self.restock()
        yield from bank.close()

    def restock(self):
        yield from bank.deposit_all_matching(deposit_all_except(KEEP))
        yield from execution.delay_ticks(1)
        view = self.view()
        if not view.bow_worn and not view.bow_held:
            bow = best_bow(skills.level('ranged'), lambda name: bank.count(name) > 0)
            if bow is None:
                self.stop('no bow held, worn or banked')
                return
            if not bank.withdraw(bow):
                self.fail(f'could not withdraw the {bow}')
                return
            self.log(f'withdrew a {bow}')
        want = self.coins_per_trip() - inventory.count_by_id(COINS)
        banked = bank.count_by_id(COINS)
        if want > 0 and banked > 0:
            taken = min(want, banked)
            ok = yield from bank.withdraw_x_by_id(COINS, taken)
            if not ok:
                self.fail('could not withdraw coins')
                return
            yield from execution.delay_ticks(1)
            self.log(f'withdrew {taken} coins ({banked - taken} left in the bank)')
        if inventory.count_by_id(COINS) < ENTRY_FEE and inventory.count_by_id(ARCHERY_TICKET) < TICKETS_PER_RUNE_ARROWS:
            self.stop(f'out of coins, {inventory.count_by_id(ARCHERY_TICKET)} tickets held, {self.arrows_bought} rune arrows bought')

    def progress(self):
        self.failures = 0
        self.recoveries = 0

    # Why: twelve misses in a row live were one level-up page and a stop, so a run of failures clears whatever is
    # up, walks back to the range and tries again, and only three such passes with nothing landing between them end
    # the script.
    def fail(self, message):
        self.failures += 1
        self.log(f'{message} ({self.failures}/{MAX_FAILURES})')
        if self.failures >= MAX_FAILURES:
            self.pending_recovery = message

    def recover(self, message):
        self.recoveries += 1
        if self.recoveries > MAX_RECOVERIES:
            self.stop(f'gave up after {MAX_RECOVERIES} recoveries: {message}')
            return
        self.status = f'recovering ({self.recoveries}/{MAX_RECOVERIES})'
        self.log(f'recovering after {MAX_FAILURES} failures ({self.recoveries}/{MAX_RECOVERIES}): {message}')
        yield from modals.close_if_open()
        yield from self.drain_chat()
        yield from self.walk_to(STAND, 1)
        self.failures = 0

    def stop(self, reason):
        self.status = f'stopped: {reason}'
        self.request_finish(f'RangingGuild: {reason}')

    def at(self, dest, radius):
        here = game.tile()
        return here is not None and dest.distance_to(here) <= radius

    def walk_to(self, dest, radius):
        if self.at(dest, radius):
            return True
        arrived = yield from traversal.walk_resilient(dest, radius=radius, attempts=6, timeout_ms=300000, log=lambda m: self.log(f'  {m}'))
        return arrived


BOT = define_bot(
    name='RangingGuild',
    create=RangingGuild,
    description='Plays the Ranging Guild archery competition for tickets and trades every 2000 for 50 rune arrows. Pays the judge 200 coins a round, shoots the ten arrows from behind the haystacks, banks at Seers for coins and the best bow',
    category='Money making',
    tags=['ranging guild', 'minigame', 'archery', 'tickets', 'rune arrows', 'seers', 'afk'],
    settings_schema=SETTINGS,
)
