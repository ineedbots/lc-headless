"""GatheringBot's tasks: rs2b0t's scripts/GatheringBot/GatheringBotTasks.ts (MIT, see thirdparty/rs2b0t)."""

import math
import random

import _core

from rs2004.catalogs import BROKEN_AXE, BROKEN_PICKAXE, COINS, ENT_LIFE_TICKS, ENT_NPC_IDS, GAS_ROCK_IDS, GAS_ROCK_TICKS, WHIRLPOOL_IDS, beyond_leash, best_pickaxe
from rs2004.catalogs import buy_plans_cost, fishing_gear_shop_cart, fishing_restock_plan, pick_bucket_nearest, plan_gather_tool_acquire, rock_tier_by_id
from rs2004.catalogs import should_cooldown_gather_tile, should_soft_home_from_gather_miss, sustain, tile_within_leash
from rs2004.catalogs import DEFAULT_TRADE_RANGE, count_offer_matching, drive_active_partner_trade, trade_screen_state
from rs2004.random_events import step_off_candidates

from bots.gathering.camp import gather_hunt_radius, gather_spot_range_origin, resource_within_camp, spot_within_gather_range
from bots.gathering.fish_cook import bank_pace_ticks, cook_filter_label, cook_pace_ticks, is_burnt_fish_name, is_cooked_fish_name, should_cook_then_bank
from bots.gathering.logic import ent_abort_action, feather_coins_to_draw, fishing_session_broken, hostile_attacker_nearby, loc_gather_should_yield
from bots.gathering.logic import should_flee_combat
from bots.gathering.tick_manip import TICK_MANIP_KNIFE, combat_breaks_gather, extra_delay_logs_to_drop, farmer_willow_phase, is_fletchable_log_name, is_shortbow_name
from bots.gathering.tick_manip import knife_delay_phase, next_gather_click_tick, should_cook_for_tannerfish, should_eat_for_tannerfish

STARTUP_PROVISION_RETRIES = 3
SWEEP_WALK_MS = 30000
SHOP_WALK_MS = 60000
FLEE_STEP = 12
FLEE_STEP_HARD = 20
LOCAL_MINE_PREFER_RADIUS = 12
OVENS = ['Fire', 'Range', 'Cooking range']


def key_of(t):
    return f'{t.x},{t.z}'


def first_where(items, test):
    for i in items:
        if test(i):
            return i
    return None


# Why: an npc's in_combat is its own hit clock, and with auto retaliate off nothing hits it back, so a dark wizard
# casting from range never read as an attacker and FleeCombat never ran; rs2b0t's has the same gap. The face
# target is the attack, and FleeCombat's game.in_combat() is the proof something landed.
def attacking_me(n):
    return n.targets_me() and 'Attack' in n.actions()


def attacking_beside(n):
    return n.in_combat and not n.targets_another_player() and 'Attack' in n.actions() and n.distance() <= 2


def face_attacker():
    """An NPC attacking the player, or fighting at its side."""
    return npcs.query().where(attacking_me).nearest() or npcs.query().where(attacking_beside).nearest()


def nearest_oven():
    return locs.query().name(*OVENS).where(lambda l: l.distance() <= 8).nearest() or locs.query().name(*OVENS).nearest()


def drop_each(test, limit=28):
    """Drops items matching test one at a time, and gives how many slots it freed. Use with yield from."""
    dropped = 0
    for _ in range(limit):
        item = first_where(inventory.items(), test)
        if item is None:
            break
        before = inventory.used()
        item.interact('Drop')
        freed = yield from execution.delay_until_ticks(lambda: inventory.used() < before, 5)
        if not freed:
            break
        dropped += before - inventory.used()
    return dropped


def is_fletch_byproduct_name(name):
    """Fletching leftovers from the knife delay's Make X: not the product logs."""
    n = (name or '').lower()
    return 'shaft' in n or n == 'headless arrow' or 'stock' in n or (('shortbow' in n or 'longbow' in n) and '(u)' in n)


def drop_burnt(bot):
    """Use with yield from."""
    bot.set_status('cook: dropping burnt')
    dropped = yield from drop_each(lambda i: is_burnt_fish_name(i.name), 30)
    if dropped > 0:
        bot.log(f'cook: dropped {dropped} burnt (session {bot.burnt})')


def drop_excess_cooked(bot, keep=3):
    """Drops cooked fish above keep: Tannerfishing's food buffer. Use with yield from."""
    dropped = 0
    for _ in range(28):
        if bot.cooked_fish_count() <= keep:
            break
        n = yield from drop_each(lambda i: is_cooked_fish_name(i.name), 1)
        if n == 0:
            break
        dropped += n
    if dropped > 0:
        bot.log(f'tick: dropped {dropped} excess cooked (keep {keep})')


def drop_fletch_byproducts(bot):
    """Drops the knife's shafts and unstrung bows, so the knife delay can't soft-lock. Use with yield from."""
    dropped = yield from drop_each(lambda i: is_fletch_byproduct_name(i.name))
    if dropped > 0:
        bot.log(f'tick: dropped {dropped} fletch byproduct(s)')


def withdraw_step(bot, name, qty, all_at=0):
    """Withdraws a restock step's quantity. Use with yield from."""
    found = [i for i in bank.items() if (i.name or '').lower() == name.lower()]
    if len(found) == 0:
        return
    item = found[0]
    before = inventory.count(name)
    if qty == 1:
        bot.log(f'restock: withdraw 1× {name}')
        bank.withdraw(name, withdraw_op(item.actions(), '1') or 'Withdraw-1')
    else:
        everything = withdraw_op(item.actions(), 'all') if all_at > 0 and qty >= all_at else None
        if everything and bank.count(name) <= qty:
            bot.log(f'restock: withdraw all {name} ({bank.count(name)})')
            bank.withdraw(name, everything)
        else:
            bot.log(f'restock: withdraw {qty}× {name}')
            yield from bank.withdraw_x(name, qty)
    yield from execution.delay_until_ticks(lambda: inventory.count(name) > before or bank.count(name) == 0, 7)
    yield from execution.delay_ticks(bank_pace_ticks())


def strict_deposit(bot, deposit, before, log, stop, what):
    """Deposits with Shantay's checks: the backpack matches and the stock updates. Use with yield from."""
    expected = [item for item in before if not deposit(item.name or '')]
    generation = bank.snapshot_generation()
    yield from bank.deposit_all_matching(deposit)
    ready = yield from bank.backpack_ready(expected, log)
    if not ready:
        stop(f'Shantay {what} did not produce the expected backpack')
        return False
    if len(expected) < len(before):
        moved = yield from bank.wait_snapshot_after(generation)
        if not moved:
            stop(f'Shantay bank stock did not update after {what}')
            return False
    return True


class EnsureShortbowRapid(Task):
    """Keeps an empty shortbow wielded, in rapid, for 3t shortbow woodcutting; set again after a login, since the
    style isn't saved."""

    def __init__(self, bot):
        Task.__init__(self, label='ensure shortbow rapid')
        self.bot = bot
        self.fails = 0
        self.retry_at_tick = 0

    def validate(self):
        if not self.bot.tick_manip.shortbow_rapid or game.tick() < self.retry_at_tick:
            return False
        need_bow = len([i for i in equipment.items() if is_shortbow_name(i.name)]) == 0
        return game.combat_mode() != parse_range_style('rapid') or need_bow

    def back_off(self, message):
        self.fails += 1
        if self.fails >= 3:
            self.fails = 0
            self.retry_at_tick = game.tick() + 25
            self.bot.log(message)

    def execute(self):
        bot = self.bot
        bowed = yield from bot.ensure_shortbow_equipped()
        if not bowed:
            self.back_off('combat: no shortbow in pack — bring one for 3t rapid')
            return
        rapid = parse_range_style('rapid')
        if game.combat_mode() == rapid:
            self.fails = 0
            return
        bot.set_status('tick: set rapid style')
        game.set_combat_mode(rapid)
        ok = yield from execution.delay_until_ticks(lambda: game.combat_mode() == rapid, 5)
        if ok:
            self.fails = 0
            bot.log('combat: range style → rapid (3t shortbow)')
        else:
            self.back_off('combat: could not set rapid style — retrying later')


class TrimKnifeDelayLogs(Task):
    """Keeps the knife delay's pack at one fletchable log, so Make X doesn't queue several."""

    def __init__(self, bot):
        Task.__init__(self, label='trim knife delay logs')
        self.bot = bot

    def validate(self):
        if not self.bot.tick_manip.use_knife_delay or event_signal.pending() or bank.is_open():
            return False
        total = sum([max(1, i.count) for i in inventory.items() if is_fletchable_log_name(i.name)])
        return extra_delay_logs_to_drop(total, 1) > 0

    def execute(self):
        yield from self.bot.trim_delay_logs(1)


# Why: it runs above Gather, so combat ticks can heal without leaving the pier, and gives way to DropProduct with the
# pack full and no oven in the scene.
class TannerfishSustain(Task):
    """Tannerfishing: eats cooked catch at low HP, and cooks raw on a fire or range nearby."""

    def __init__(self, bot):
        Task.__init__(self, label='tannerfish sustain')
        self.bot = bot

    def validate(self):
        bot = self.bot
        if not bot.tick_manip.cook_eat_interleave or event_signal.pending() or bank.is_open() or chat_dialog.can_continue():
            return False
        if should_eat_for_tannerfish(skills.hp_fraction(), bot.cooked_fish_count() > 0):
            return True
        if chat_dialog.is_make_menu() and bot.cookable_raw_count() > 0:
            return True
        if not should_cook_for_tannerfish(bot.cookable_raw_count(), bot.cooked_fish_count(), inventory.free(), skills.hp_fraction()):
            return False
        return nearest_oven() is not None

    def execute(self):
        bot = self.bot
        if should_eat_for_tannerfish(skills.hp_fraction(), bot.cooked_fish_count() > 0):
            yield from bot.tanner_eat_one()
            return
        # Burnt fish go, so the pack stays usable.
        if bot.burnt_fish_count() > 0:
            yield from drop_burnt(bot)
        yield from bot.tanner_cook_one()


class MinerEatFood(Task):
    """The miner's smart eating: at the full-heal boundary, or for one more ore's slot."""

    def __init__(self, bot):
        Task.__init__(self, label='miner eat food')
        self.bot = bot

    def validate(self):
        bot = self.bot
        return bot.miner_food is not None and not bank.is_open() and not event_signal.pending() and not chat_dialog.can_continue() and bot.should_eat_miner_food()

    def execute(self):
        yield from self.bot.eat_miner_food()


class DesertMiningCampTravel(Task):
    """Every leg of the gated Desert Mining Camp round trip but the bank."""

    def __init__(self, bot):
        Task.__init__(self, label='desert mining camp travel')
        self.bot = bot

    def validate(self):
        return self.bot.desert_mining_camp_travel_needed()

    def execute(self):
        yield from self.bot.run_desert_mining_camp_travel()


class MaintainWildernessMinerStance(Task):
    """Keeps a hostile camp's miner from retaliating, after going in or a login."""

    def __init__(self, bot):
        Task.__init__(self, label='maintain wilderness miner stance')
        self.bot = bot

    def validate(self):
        return self.bot.wilderness_miner_stance_needed()

    def execute(self):
        self.bot.set_status('combat: Auto Retaliate off')
        if game.set_auto_retaliate(False):
            self.bot.log('combat: Miner re-asserted Auto Retaliate off')
        # One toggle a run: it waits for the varp before the task can validate again.
        yield from execution.delay_until_ticks(lambda: not game.auto_retaliate_on(), 3)


class WaitStickyCombat(Task):
    """Sticky combat state with no attacker: waits rather than kiting east, so burning or gathering go on once it
    drains instead of deadlocking."""

    def __init__(self, bot):
        Task.__init__(self, label='wait sticky combat')
        self.bot = bot

    def validate(self):
        bot = self.bot
        return bot.mob_flee_enabled() and game.in_combat() and not event_signal.pending() and not should_flee_combat(True, False, face_attacker() is not None or bot.wilderness_miner_player_attack())

    def execute(self):
        game.set_auto_retaliate(False)
        self.bot.set_status('combat: waiting clear (no attacker)')
        yield from execution.delay_until_ticks(lambda: not game.in_combat() or face_attacker() is not None, 5)


# Why: random events are the guardian's. Auto retaliate is off from the start, so walking away ends a fight rather
# than trading hits; the kite heads away from the attacker, never back onto the camp while spiders sit on it, and
# east when the direction is unclear, which is the Lava Maze's way out. Sticky combat state with no face target is
# WaitStickyCombat's, since kiting east blind froze burning and pier gathering for a minute or more.
class FleeCombat(Task):
    """Breaks multi-combat pulls from aggressive NPCs such as the lava maze's spiders and dark wizards."""

    def __init__(self, bot):
        Task.__init__(self, label='flee combat')
        self.bot = bot

    def validate(self):
        bot = self.bot
        if not bot.mob_flee_enabled():
            return False
        return should_flee_combat(game.in_combat(), event_signal.pending(), face_attacker() is not None or bot.wilderness_miner_player_attack())

    def flee_tile(self, here, attacker, step):
        if attacker is None:
            # No face target: east first, for the Lava Maze's spiders and the wilderness's approach.
            return Tile(here.x + step, here.z, here.level)
        at = attacker.tile()
        dx = here.x - at.x
        dz = here.z - at.z
        # Stacked on the attacker, east by default, for the named wilderness camps.
        if dx == 0 and dz == 0:
            dx = 1
        sx = 0 if dx == 0 else (1 if dx > 0 else -1)
        sz = 0 if dz == 0 else (1 if dz > 0 else -1)
        # A kite straight north or south leans east, so it doesn't walk back into the spiders.
        ox = 1 if sx == 0 else sx
        return Tile(here.x + ox * step, here.z + sz * step, here.level)

    def execute(self):
        bot = self.bot
        # Set again, in case a death or a login restored the default.
        game.set_auto_retaliate(False)
        # A kite ends the fire load: walking off the plot burning soft-locked it.
        if bot.burn_enabled() and bot.burning_load:
            bot.log('burn: combat flee — ending fire load to re-camp after clear')
            bot.end_burning_load()
        here = game.tile()
        if here is None:
            yield from execution.delay_ticks(1)
            return
        player_attack = bot.wilderness_miner_player_attack()
        # The policy knows a player attacks, not where it stands, so it takes the step that doesn't depend on that.
        attacker = None if player_attack else face_attacker()
        if attacker is None and not player_attack:
            bot.set_status('combat: waiting clear (no attacker)')
            yield from execution.delay_until_ticks(lambda: not game.in_combat() or face_attacker() is not None, 7)
            return
        # Holds the camp's return and gathering, so it doesn't walk back onto the pack.
        bot.note_combat_flee(20)
        dest = self.flee_tile(here, attacker, FLEE_STEP)
        who = 'player attacker' if player_attack else (attacker.name or 'attacker')
        bot.set_status(f'combat: fleeing {who} → {dest.x},{dest.z}')
        bot.log(f'combat: under attack by {who} — walking off to {dest.x},{dest.z}')
        yield from traversal.walk_to(dest, radius=2, timeout_ms=16000)
        yield from execution.delay_until_ticks(lambda: not game.in_combat(), 17)
        if game.in_combat():
            still = game.tile()
            again_by = face_attacker()
            if still is not None and again_by is not None:
                again = self.flee_tile(still, again_by, FLEE_STEP_HARD)
                bot.log(f'combat: still in combat — second kite to {again.x},{again.z}')
                bot.note_combat_flee(24)
                yield from traversal.walk_to(again, radius=2, timeout_ms=12000)
                yield from execution.delay_until_ticks(lambda: not game.in_combat(), 14)
        # Hostiles still on it after the kite hold the camp longer.
        if game.in_combat() or hostile_attacker_nearby(npcs.query().action('Attack').within(6).results(), 6):
            bot.note_combat_flee(17)


class ClearPackJunk(Task):
    """Clears the random events' leftovers that take pack slots."""

    def __init__(self, bot):
        Task.__init__(self, label='clear pack junk')
        self.bot = bot

    # Power mode and burning don't bank a full pack with the haul; banking mode deposits junk already.
    def validate(self):
        bot = self.bot
        if event_signal.pending() or bot.pack_junk_policy == 'off':
            return False
        if not bot.burn_enabled() and not bot.power_mode:
            return False
        if len(bot.pack_junk_items()) == 0:
            return False
        free = inventory.free()
        return inventory.is_full() or free <= (6 if bot.burn_enabled() else 2)

    def execute(self):
        bot = self.bot
        junk_n = len(bot.pack_junk_items())
        if bot.pack_junk_policy == 'bank' and not bot.power_mode:
            bot.set_status('bank: event junk')
            log = lambda m: bot.log(f'  {m}')
            opened = yield from bot.open_script_bank(log)
            if opened:
                yield from bank.deposit_all_matching(lambda name, id: bot.is_pack_junk(name, id))
                yield from execution.delay_ticks(1)
                if bank.is_open():
                    yield from bot.close_script_bank(log)
                left = len(bot.pack_junk_items())
                bot.log(f'bank: deposited event junk ({junk_n - left} stack(s); {left} left)')
                if left == 0:
                    return
                bot.log('bank: some junk still held — falling back to drop')
            else:
                bot.log('bank: could not open for event junk — falling back to drop')
        bot.set_status('dropping junk')
        dropped = yield from drop_each(lambda i: bot.is_pack_junk(i.name, i.id))
        if dropped > 0:
            bot.log(f'drop: cleared {dropped} random/common junk stack(s) (pack space)')


class DropProduct(Task):
    def __init__(self, bot):
        Task.__init__(self, label='drop product')
        self.bot = bot

    def validate(self):
        bot = self.bot
        if not inventory.is_full():
            return False
        profile = bot.tick_manip
        if profile.cook_eat_interleave:
            # Burnt always goes, the raw haul drops, and cooked past the food buffer.
            return bot.burnt_fish_count() > 0 or len(bot.products()) > 0 or bot.cooked_fish_count() > 4
        if (profile.use_knife_delay or profile.farmer_willow_cycle) and len([i for i in inventory.items() if is_fletch_byproduct_name(i.name)]) > 0:
            return True
        return len(bot.products()) > 0

    def execute(self):
        bot = self.bot
        profile = bot.tick_manip
        # Burnt first while Tannerfishing, so there's room to cook and eat.
        if profile.cook_eat_interleave and bot.burnt_fish_count() > 0:
            yield from drop_burnt(bot)
        # The knife's Make X leftovers go, so shafts can't soft-lock the pack.
        if profile.use_knife_delay or profile.farmer_willow_cycle:
            yield from drop_fletch_byproducts(bot)
        yield from bot.drop_products()
        if profile.cook_eat_interleave and inventory.is_full():
            yield from drop_excess_cooked(bot, 3)


class BankCatch(Task):
    def __init__(self, bot):
        Task.__init__(self, label='bank catch')
        self.bot = bot

    def validate(self):
        bot = self.bot
        if bot.bank_catch_blocked_by_cook() or bot.bank_catch_blocked_by_burn():
            return False
        if bot.strict_desert_camp_banking():
            return bank.is_open() or bot.desert_camp_bank_catch_needed()
        return bot.miner_food_restock_needed() or bot.full_haul_needs_bank()

    def refresh_raw(self):
        """Use with yield from."""
        bot = self.bot
        if not (bot.fishing and bot.cook_mode == 'bank-raw-then-cook'):
            return
        yield from execution.delay_until_ticks(bank.loaded, 5)
        yield from execution.delay_ticks(1)
        total = bot.refresh_bank_raw_total()
        bot.log(f'bank: raw {cook_filter_label(bot.cook_fish_filter)} {total}/{bot.bank_raw_target}')

    def execute(self):
        bot = self.bot
        # The cooked count, after cooking then banking: products() is only raw.
        had = max(len(bot.products()), bot.cooked_fish_count() + (bot.burnt_fish_count() if bot.burnt_policy == 'bank' else 0))
        log = lambda m: bot.log(f'  {m}')
        deposit = lambda name, *_args: bot.should_deposit(name)
        strict = bot.strict_desert_camp_banking()
        before_open = None
        if strict:
            before_open = yield from bot.shantay_backpack_before_open(log)
            if before_open is None:
                bot.stop_strict_bank_failure('desert camp: normal backpack was unreadable before Shantay bank')
                return
        bot.set_status('bank: heading to bank')
        opened = yield from bot.open_script_bank(log)
        if not opened:
            if strict:
                bot.stop_strict_bank_failure('desert camp: Shantay chest is unreachable')
                return
            bot.set_status('bank: nearest bank')
            banked = yield from banking.bank_nearest(deposit, log=log, after_deposit=self.refresh_raw)
            if not banked:
                bot.set_status('bank: unreachable — dropping')
                bot.log('bank: unreachable — dropping')
                yield from bot.drop_products()
                return
        else:
            if strict:
                ready = yield from bot.wait_bank_ready(log)
                if not ready:
                    bot.stop_strict_bank_failure('desert camp: Shantay bank item list did not load')
                    return
                ready = yield from bank.backpack_ready(before_open, log)
                if not ready:
                    bot.stop_strict_bank_failure('desert camp: Shantay side backpack did not load')
                    return
            yield from execution.delay_ticks(bank_pace_ticks())
            if strict:
                deposited = yield from strict_deposit(bot, deposit, before_open, log, lambda r: bot.stop_strict_bank_failure(f'desert camp: {r}'), 'deposit')
                if not deposited:
                    return
            else:
                yield from bank.deposit_all_matching(deposit)
            yield from execution.delay_ticks(1)
            yield from self.refresh_raw()
        if strict:
            yield from execution.delay_until_ticks(lambda: len(bot.desert_camp_deposit_residue()) == 0 or not bank.is_open(), 9)
            residue = bot.desert_camp_deposit_residue()
            if len(residue) > 0:
                bot.stop_strict_bank_failure(f"desert camp: Shantay deposit incomplete; still holding {', '.join(residue)}")
                return
            ready = yield from bot.wait_bank_ready(log)
            if not ready:
                bot.stop_strict_bank_failure('desert camp: Shantay bank item list did not reload after deposit')
                return
        healed = yield from bot.heal_miner_at_bank(log)
        if not healed:
            return
        route_plan = bot.desert_camp_route.plan_supplies_at_open_bank() if bot.desert_camp_route is not None else None
        if route_plan is not None and not route_plan.ok:
            bot.stop_strict_bank_failure(f"desert camp: missing supplies: {', '.join(route_plan.missing)}")
            return
        # The crossing swaps a pass for a disclaimer, so provisioning leaves its own ore slot.
        reserved = desert_camp_reserved(route_plan)
        if reserved > 0:
            bot.log(f'desert camp: reserving {reserved} pack slot(s) for route supplies')
        if had > 0:
            bot.count_trip(had)
            bot.log(f'bank: deposited {had} {bot.product_label()}')
        elif bot.miner_food is not None:
            bot.log('bank: preparing Miner food trip (no haul to deposit)')
        # In the same visit: bait and feathers back up toward the target.
        if bot.fishing and bot.needs_fishing_bait_top_up():
            yield from bot.top_up_fishing_bait_at_bank(log)
        if bot.miner_food is not None:
            topped = yield from bot.top_up_miner_food_at_bank(log, reserved)
            if not topped:
                return
        if route_plan is not None:
            supplied = yield from bot.desert_camp_route.withdraw_planned_supplies_at_open_bank(route_plan)
            if not supplied:
                return
        # In the same visit: coins and the teleport's runes.
        yield from bot.withdraw_trip_provisions_at_bank(log)
        # A tool upgrade while banking anyway, never pulled away mid-chop.
        upgraded = yield from bot.try_upgrade_gather_tool_at_bank(log)
        if upgraded:
            return
        if bank.is_open():
            closed = yield from bot.close_script_bank(log, not strict)
            if not closed and strict:
                bot.stop_strict_bank_failure('desert camp: Shantay bank did not close')
                return
        bot.complete_desert_camp_bank_trip()
        # Why: after depositing, the long legs back need the full walk, unless a cook batch stays on purpose.
        if not bot.in_cook_batch:
            bot.set_status('bank: returning to camp')
            home = yield from bot.walk_home_if_needed(log)
            if not home:
                bot.log('bank: walk home incomplete — will retry via gather/return')


def desert_camp_reserved(route_plan):
    if route_plan is None:
        return 0
    return max(0, math.floor(route_plan.required_slots)) + 1


class FishCookDialog(Task):
    def __init__(self, bot):
        Task.__init__(self, label='fish cook dialog')
        self.bot = bot

    def validate(self):
        return self.bot.cook_enabled() and chat_dialog.is_make_menu()

    def execute(self):
        bot = self.bot
        bot.set_status('cook: choosing product')
        raw = bot.last_raw_fish()
        # This revision has no Make X: the largest fixed amount, often 1.
        made = yield from chat_dialog.make(raw.name if raw is not None else None)
        if not made:
            yield from chat_dialog.make()
        yield from execution.delay_ticks(1)


class FishCookLoad(Task):
    def __init__(self, bot):
        Task.__init__(self, label='fish cook load')
        self.bot = bot

    def validate(self):
        bot = self.bot
        if not bot.cook_enabled() or chat_dialog.is_open() or event_signal.pending() or game.in_combat():
            return False
        cookable = bot.cookable_raw_count()
        if cookable <= 0:
            return False
        if bot.cooking_load:
            return True
        if bot.cook_mode == 'cook-then-bank' and should_cook_then_bank(bot.cook_mode, inventory.is_full(), cookable):
            return True
        return bot.cook_mode == 'bank-raw-then-cook' and bot.in_cook_batch

    def find_range(self):
        bot = self.bot
        names = [bot.range_name, 'Range', 'Cooking range', 'Fire', 'Fireplace']
        near = locs.query().name(*names).where(lambda l: l.tile().distance_to(bot.range_stand) <= bot.range_search_radius).nearest()
        return near if near is not None else locs.query().name(*names).nearest()

    def open_door_near(self, what):
        """Use with yield from."""
        bot = self.bot
        obs = bot.cook_obstacles
        shut = locs.query().where(lambda l: is_openable_obstacle(l.name, l.actions(), obs) and l.distance() <= 3).nearest()
        if shut is None:
            return False
        op = open_op(shut.actions())
        if not op:
            return False
        bot.log(f'cook: opening {shut.name} {what}')
        shut.interact(op)
        yield from execution.delay_ticks(2)
        return True

    # Why: curated stands walk to the approach (outside the door) and then inside; a street-side stand paths with no
    # door, and the use then clicks the oven through a wall.
    def walk_to_oven(self, why):
        """Use with yield from."""
        bot = self.bot
        approach = bot.range_approach
        obs = bot.cook_obstacles
        say = lambda m: bot.log(m)
        bot.set_status(f"cook: walking to range{f' ({why})' if why else ''}")
        if approach is not None:
            at = game.tile()
            if at is None or approach.distance_to(at) > 2:
                bot.log(f"cook: walking to approach {approach}{f' — {why}' if why else ''}")
                yield from walk_opening(approach, 1, obs, say)
            # A Large door or house Door, opened from its approach.
            yield from self.open_door_near('at approach')
        yield from walk_opening(bot.range_stand, 0, obs, say)
        if self.find_range() is None and bot.range_loc_tile is not None:
            bot.log(f'cook: no oven in leash — closing on loc {bot.range_loc_tile}')
            yield from walk_opening(bot.range_loc_tile, 1, obs, say)
        # A door still shut beside it: a street-side stand outside a house.
        opened = yield from self.open_door_near('near stand')
        if opened:
            yield from walk_opening(bot.range_stand, 0, obs, say)

    def quit_now(self):
        return chat_dialog.is_make_menu() or chat_dialog.can_continue() or event_signal.pending() or game.in_combat()

    def wait_one_fish(self, before):
        """Waits out one fish on ticks. Use with yield from."""
        bot = self.bot
        for _ in range(10):
            if bot.cookable_raw_count() < before or self.quit_now():
                break
            yield from execution.delay_ticks(1)

    def execute(self):
        bot = self.bot
        stand = bot.range_stand
        if stand is None:
            return
        bot.cooking_load = True
        here = game.tile()
        if here is None or stand.distance_to(here) > 1 or self.find_range() is None:
            yield from self.walk_to_oven('approach→stand' if bot.range_approach is not None else '')
            # A door leaves the range unready for a tick or two.
            yield from execution.delay_ticks(2)
        # Why: this revision has no Make X, so each use (and a make-menu button) cooks one fish; every wait is on ticks,
        # since using it again mid-animation cancels the cook. It's bounded by attempts, one fish or stall each.
        wall_recoveries = 0
        skip_probe = False
        for _ in range(48):
            if bot.cookable_raw_count() <= 0 or self.quit_now():
                if self.quit_now():
                    return
                break
            # Back after the make menu, a cook may be under way already: it's waited out on ticks.
            if not skip_probe:
                idle_raw = bot.cookable_raw_count()
                idle_xp = skills.xp('cooking')
                progressed = False
                for _ in range(4):
                    if bot.cookable_raw_count() < idle_raw or skills.xp('cooking') > idle_xp or bot.cookable_raw_count() == 0 or self.quit_now():
                        progressed = True
                        break
                    yield from execution.delay_ticks(1)
                if bot.cookable_raw_count() == 0:
                    break
                if self.quit_now():
                    return
                if progressed:
                    # Only the xp moved: the fish is finished first.
                    yield from self.wait_one_fish(idle_raw)
                    wall_recoveries = 0
                    yield from execution.delay_ticks(1)
                    skip_probe = True
                    continue
            skip_probe = False
            raw = bot.last_raw_fish()
            oven = self.find_range()
            if raw is None or oven is None:
                bot.log(f"cook: cannot cook (raw={raw.name if raw is not None else 'none'} oven={'yes' if oven is not None else 'no'})")
                if wall_recoveries < 3:
                    wall_recoveries += 1
                    yield from self.walk_to_oven('no oven')
                    continue
                yield from execution.delay_ticks(2)
                return
            bot.set_status(f'cook: {raw.name} ({bot.cookable_raw_count()} left)')
            before_raw = bot.cookable_raw_count()
            before_xp = skills.xp('cooking')
            if not raw.use_on(oven):
                yield from execution.delay_ticks(2)
                continue
            # A short wait on a street-side stand, a little longer after a door, before calling it a stall.
            reacted = False
            for _ in range(8):
                if bot.cookable_raw_count() < before_raw or skills.xp('cooking') > before_xp or chat_dialog.is_make_menu() or chat_dialog.can_continue():
                    reacted = True
                    break
                yield from execution.delay_ticks(1)
            # The dialogue picks the product; the next run waits the cook out above.
            if chat_dialog.is_make_menu() or chat_dialog.can_continue():
                return
            if not reacted:
                at = game.tile()
                at_stand = at is not None and stand.distance_to(at) <= 2
                # A gentle click again at the stand first, then the full walk: three walks thrashed doors for 80s.
                if at_stand and wall_recoveries < 2:
                    wall_recoveries += 1
                    bot.log(f'cook: useOn no progress at stand — soft re-click (try {wall_recoveries})')
                    yield from execution.delay_ticks(2)
                    continue
                if at_stand and wall_recoveries < 4:
                    wall_recoveries += 1
                    bot.log(f'cook: useOn produced no cook progress at stand — re-path (try {wall_recoveries})')
                    yield from self.walk_to_oven('useOn stall')
                    continue
                yield from execution.delay_ticks(1)
                continue
            # A cook with no menu: this fish is waited out on ticks, then the next.
            wall_recoveries = 0
            yield from self.wait_one_fish(before_raw)
            if self.quit_now():
                return
            if bot.cookable_raw_count() < before_raw:
                yield from execution.delay_ticks(1)
                skip_probe = True
        if bot.cookable_raw_count() == 0:
            if bot.burnt_policy == 'drop' and bot.burnt_fish_count() > 0:
                yield from drop_burnt(bot)
            yield from execution.delay_ticks(1)


class FishBankCooked(Task):
    def __init__(self, bot):
        Task.__init__(self, label='fish bank cooked')
        self.bot = bot

    def validate(self):
        bot = self.bot
        if not bot.cook_enabled() or event_signal.pending() or game.in_combat():
            return False
        return bot.cooking_load and bot.cookable_raw_count() == 0

    def after_deposit(self):
        """Use with yield from."""
        if self.bot.cook_mode == 'bank-raw-then-cook':
            self.bot.refresh_bank_raw_total()
        if False:
            yield

    def execute(self):
        bot = self.bot
        if bot.burnt_policy == 'drop' and bot.burnt_fish_count() > 0:
            yield from drop_burnt(bot)
        cooked = bot.cooked_fish_count()
        log = lambda m: bot.log(f'  {m}')
        deposit = lambda name, *_args: bot.should_deposit_cook_result(name)
        if len([i for i in inventory.items() if bot.should_deposit_cook_result(i.name or '')]) > 0:
            bot.set_status('bank: cooked fish')
            opened = yield from bot.open_script_bank(log)
            if opened:
                yield from execution.delay_ticks(bank_pace_ticks())
                yield from bank.deposit_all_matching(deposit)
                yield from execution.delay_until_ticks(bank.loaded, 5)
                yield from execution.delay_ticks(1)
                yield from self.after_deposit()
                bot.count_trip(cooked)
                bot.log(f'bank: deposited {cooked} cooked (burnt={bot.burnt_policy})')
            else:
                # A long cooking-to-bank leg sometimes fails to open once, so the nearest booth stops a soft-lock.
                bot.log('bank: script bank open failed — trying nearest')
                banked = yield from banking.bank_nearest(deposit, common_junk=False, log=log, after_deposit=self.after_deposit)
                if not banked:
                    bot.log('bank: could not open for cooked — will retry')
                    return
                bot.count_trip(cooked)
                bot.log(f'bank: deposited {cooked} cooked via nearest (burnt={bot.burnt_policy})')
        else:
            bot.log('cook: load finished, nothing to bank')
        if bot.cook_mode == 'bank-raw-then-cook':
            bot.finish_cook_cycle()
            if bot.in_cook_batch or bot.after_cook == 'stop':
                return
        else:
            bot.cooking_load = False
        yield from bot.walk_home_if_needed(log)


class FishWithdrawCookBatch(Task):
    def __init__(self, bot):
        Task.__init__(self, label='fish withdraw cook batch')
        self.bot = bot

    def validate(self):
        bot = self.bot
        if not bot.cook_enabled() or bot.cook_mode != 'bank-raw-then-cook' or not bot.in_cook_batch or bot.cooking_load:
            return False
        return bot.cookable_raw_count() == 0 and not event_signal.pending() and not game.in_combat()

    def end_batch(self, log, message):
        """Use with yield from."""
        bot = self.bot
        bot.log(message)
        bot.finish_cook_cycle()
        if not bot.in_cook_batch and bot.after_cook == 'continue':
            yield from bot.walk_home_if_needed(log)

    def execute(self):
        bot = self.bot
        log = lambda m: bot.log(f'  {m}')
        bot.set_status('cook: withdrawing raw')
        opened = yield from bot.open_script_bank(log)
        if not opened:
            bot.log('cook: could not open bank for withdraw — will retry')
            return
        yield from execution.delay_until_ticks(bank.loaded, 5)
        yield from execution.delay_ticks(1)
        bot.refresh_bank_raw_total()
        raws = [i for i in bank.items() if i.name is not None and bot.is_cookable_raw(i.name)]
        if len(raws) == 0:
            bot.bank_raw_in_bank = 0
            yield from self.end_batch(log, f'cook: no {cook_filter_label(bot.cook_fish_filter)} left in bank — ending batch')
            return
        name = raws[0].name
        ops = raws[0].actions()
        everything = withdraw_op(ops, 'all')
        if everything:
            bot.log(f'cook: withdraw all {name} (bank had {bot.bank_raw_in_bank})')
            bank.withdraw(name, everything)
            yield from execution.delay_until_ticks(lambda: bot.cookable_raw_count() > 0 or bank.count(name) == 0, 7)
        else:
            ten = withdraw_op(ops, '10') or withdraw_op(ops, 'any') or 'Withdraw-10'
            for _ in range(4):
                if inventory.is_full() or bank.count(name) <= 0:
                    break
                before = bot.cookable_raw_count()
                bank.withdraw(name, ten)
                took = yield from execution.delay_until_ticks(lambda: bot.cookable_raw_count() > before or inventory.is_full(), 5)
                if not took:
                    break
                yield from execution.delay_ticks(cook_pace_ticks())
        yield from execution.delay_until_ticks(bank.loaded, 4)
        bot.refresh_bank_raw_total()
        if bot.cookable_raw_count() == 0:
            if bot.bank_raw_in_bank == 0 or len([i for i in bank.items() if i.name is not None and bot.is_cookable_raw(i.name)]) == 0:
                bot.bank_raw_in_bank = 0
            yield from self.end_batch(log, 'cook: withdraw empty — ending batch')
            return
        bot.cooking_load = True
        bot.log(f'cook: withdrew {bot.cookable_raw_count()} {name} (bank left {bot.bank_raw_in_bank})')


class RepairBrokenGatherTool(Task):
    """A broken pickaxe or axe: Nurmof's or Bob's repair when tool acquisition is on, else the bank for a
    replacement pickaxe; a broken axe without it falls through to the restock."""

    def __init__(self, bot):
        Task.__init__(self, label='repair broken gather tool')
        self.bot = bot

    def validate(self):
        bot = self.bot
        if event_signal.pending() or game.in_combat() or (bot.burn_enabled() and bot.burning_load):
            return False
        return bot.has_broken_gather_tool()

    def execute(self):
        bot = self.bot
        log = lambda m: bot.log(f'  {m}')
        broken_pick = equipment.contains(BROKEN_PICKAXE) or inventory.first(BROKEN_PICKAXE) is not None
        broken_axe = equipment.contains(BROKEN_AXE) or inventory.first(BROKEN_AXE) is not None
        if bot.tool_acquire_enabled() and bot.acquire_ready():
            plan = plan_gather_tool_acquire(bot.tool_reqs, bot.acquire_world(), upgrade=False)
            if plan is not None and plan.kind == 'repair':
                ok = yield from bot.execute_tool_acquire_plan(plan, log)
                if ok:
                    yield from bot.walk_home_if_needed(log)
                    return
                bot.log('acquire: repair failed — falling back to bank/buy')
        if broken_pick:
            yield from self.replace_pickaxe(log)
            return
        if broken_axe:
            if equipment.contains(BROKEN_AXE) and not inventory.is_full():
                yield from equipment.unequip(BROKEN_AXE)
            opened = yield from bot.open_script_bank(log)
            if opened:
                yield from bank.deposit_all_matching(lambda n, *_args: n.lower() == BROKEN_AXE.lower())
                yield from execution.delay_until_ticks(bank.loaded, 4)
                if bank.is_open():
                    yield from bot.close_script_bank(log)
            bot.log('axe: deposited broken — restock/acquire will fetch a usable axe')

    def replace_pickaxe(self, log):
        """Deposits the broken one and withdraws the best banked. Use with yield from."""
        bot = self.bot
        bot.set_status('pickaxe: fetching replacement')
        bot.log('pickaxe: broken — power mode nearest-bank replacement' if bot.power_mode else 'pickaxe: broken — banking for best replacement')
        if equipment.contains(BROKEN_PICKAXE) and not inventory.is_full():
            yield from equipment.unequip(BROKEN_PICKAXE)
        strict = bot.strict_desert_camp_banking()
        stop = lambda reason: bot.stop_missing_gear(reason, ['pickaxe'])
        before_open = None
        if strict:
            before_open = yield from bot.shantay_backpack_before_open(log)
            if before_open is None:
                stop('normal backpack unreadable before Shantay bank')
                return
        opened = yield from bot.open_script_bank(log)
        if not opened:
            if bot.power_mode or strict:
                stop('could not open nearest bank for pickaxe')
                return
            bot.log('pickaxe: could not open bank — will retry')
            return
        if strict:
            ready = yield from bot.wait_bank_ready(log)
            if ready:
                ready = yield from bank.backpack_ready(before_open, log)
            if not ready:
                stop('Shantay bank did not become transaction-ready')
                return
        restock = bot.restock_deposit_matcher()
        deposit = lambda name, *_args: restock(name) or name.lower() == BROKEN_PICKAXE.lower()
        if strict:
            deposited = yield from strict_deposit(bot, deposit, before_open, log, stop, 'replacement deposit')
            if not deposited:
                return
        else:
            yield from bank.deposit_all_matching(deposit)
        yield from execution.delay_until_ticks(bank.loaded, 5)
        pick = best_pickaxe(skills.level('mining'), lambda name: bank.count(name) > 0)
        if pick is None:
            if bot.tool_acquire_enabled() and bot.acquire_ready():
                buy = plan_gather_tool_acquire(bot.tool_reqs, bot.acquire_world_with_bank(), upgrade=False)
                if buy is not None and buy.kind != 'repair':
                    if bank.is_open():
                        yield from bot.close_script_bank(log, False)
                    ok = yield from bot.execute_tool_acquire_plan(buy, log)
                    if ok:
                        yield from bot.walk_home_if_needed(log)
                        return
            bot.request_finish('pickaxe: no usable pick in bank')
            return
        found = [i for i in bank.items() if (i.name or '').lower() == pick.lower()]
        one = (withdraw_op(found[0].actions(), '1') if len(found) > 0 else None) or 'Withdraw-1'
        bank.withdraw(pick, one)
        landed = yield from execution.delay_until_ticks(lambda: inventory.first(pick) is not None, 5)
        if not landed:
            if bot.power_mode or strict:
                bot.stop_missing_gear('pickaxe withdraw failed', [pick])
                return
            bot.log('pickaxe: withdraw did not land — will retry')
            return
        bot.log(f'pickaxe: replaced with {pick}')
        # Closed once, then wielded: the replacement may push out the broken one or other gear.
        if bank.is_open():
            yield from bot.close_script_bank(log)
        yield from bot.equip_tools([pick], log, True)
        yield from bot.walk_home_if_needed(log)


class EnsureGatherToolEquipped(Task):
    """Wields axes and pickaxes already in the pack: has_gear holds while they're held unworn."""

    def __init__(self, bot):
        Task.__init__(self, label='ensure gather tool equipped')
        self.bot = bot

    def validate(self):
        bot = self.bot
        if bot.fishing or len(bot.tool_reqs) == 0 or event_signal.pending() or game.in_combat():
            return False
        if (bot.burn_enabled() and bot.burning_load) or bot.has_broken_gather_tool():
            return False
        return len(bot.tools_to_equip()) > 0

    def execute(self):
        need = self.bot.tools_to_equip()
        self.bot.set_status(f"equip: {' + '.join(need)}")
        self.bot.log(f"equip: wielding {', '.join(need)}")
        yield from self.bot.equip_tools(need)


class RestockFishingGear(Task):
    def __init__(self, bot):
        Task.__init__(self, label='restock fishing gear')
        self.bot = bot

    # Gear lost on the spot still allows the trip: missing gear is fatal otherwise.
    def validate(self):
        bot = self.bot
        if not bot.fishing or bot.has_gear() or event_signal.pending() or game.in_combat():
            return False
        if bot.cook_enabled() and (bot.cooking_load or bot.in_cook_batch):
            return False
        return bot.fish_method is not None

    def try_cart(self, log, funded=None):
        """Buys the vendor's cart, and heads home after a buy. Use with yield from."""
        bot = self.bot
        cart = fishing_gear_shop_cart(bot.fish_method, bot.acquire_world_with_bank(), bot.fishing_vendor_near(), bot.bait_qty)
        if len(cart) == 0:
            return None
        prepared = funded if funded is not None else inventory.count(COINS) >= buy_plans_cost(cart)
        if bank.is_open():
            yield from bot.close_script_bank(log, False)
        ok = yield from bot.execute_fishing_gear_shop_cart(cart, log, prepared)
        if ok:
            # A full or partial cart leaves the shop for the camp: partial carts soft-locked on Gerrant's tile.
            bot.set_status('restock: returning to camp')
            yield from bot.walk_home_if_needed(log)
        return ok

    def execute(self):
        bot = self.bot
        method = bot.fish_method
        missing = bot.missing_gear_names()
        power = bot.power_mode
        what = ', '.join(missing) or bot.gear_label()
        bot.set_status(f"restock: {' + '.join(missing) or bot.gear_label()}")
        bot.log(f'restock: power mode — nearest bank for {what}' if power else f'restock: missing {what}')
        log = lambda m: bot.log(f'  {m}')
        # Why: coins that cover the shop cart skip the bank and go straight to Gerrant or Harry, so held gp doesn't
        # send it off to glance at an empty booth.
        if bot.tool_acquire_enabled() and bot.acquire_ready() and len(missing) > 0:
            cart = fishing_gear_shop_cart(method, bot.acquire_world_with_bank(), bot.fishing_vendor_near(), bot.bait_qty)
            if len(cart) > 0 and inventory.count(COINS) >= buy_plans_cost(cart):
                bot.log('restock: coins held for shop cart — skipping bank, heading to vendor')
                ok = yield from self.try_cart(log, True)
                if ok:
                    return
        opened = yield from bot.open_script_bank(log)
        if not opened:
            if power:
                bot.stop_missing_gear('could not open nearest bank', missing)
                return
            bot.log('restock: could not open bank — will retry')
            yield from execution.delay_ticks(3)
            return
        yield from execution.delay_ticks(bank_pace_ticks())
        yield from execution.delay_until_ticks(lambda: bank.loaded() or not bank.is_open(), 5)
        # Everything that isn't gear goes first, the haul and junk with it.
        if power or bot.away_from_gather_spot():
            bot.log('restock: depositing non-gear first')
        yield from bank.deposit_all_matching(bot.restock_deposit_matcher())
        yield from execution.delay_until_ticks(bank.loaded, 5)
        yield from execution.delay_ticks(1)
        plan = fishing_restock_plan(method, inventory.count, bank.count)
        if len(plan) == 0:
            still = bot.missing_gear_names()
            if len(still) == 0:
                bot.log('restock: gear already topped up')
                if bank.is_open():
                    yield from bot.close_script_bank(log)
                return
            if bot.tool_acquire_enabled() and bot.acquire_ready():
                ok = yield from self.try_cart(log)
                if ok:
                    return
                if ok is None:
                    bot.log(f"restock: acquire on but cannot fund/shop {' / '.join(still)} — need coins or stock")
                    bot.mark_acquire_backoff(50)
            if power:
                bot.stop_missing_gear('bank has no required fishing gear', still)
                return
            bot.set_status(f"restock: missing in bank {' + '.join(still)}")
            bot.log(f"restock: bank has no {' / '.join(still)} — deposit gear or switch method")
            yield from execution.delay_ticks(8)
            return
        for name, qty in plan:
            yield from withdraw_step(bot, name, qty, 50)
        if not bot.has_gear():
            still = bot.missing_gear_names()
            if bot.tool_acquire_enabled() and bot.acquire_ready():
                ok = yield from self.try_cart(log)
                if ok:
                    return
            if power:
                bot.stop_missing_gear('incomplete after withdraw', still)
                return
            bot.set_status(f"restock: still missing {' + '.join(still)}")
            bot.log(f"restock: incomplete — need {', '.join(still)}")
            yield from execution.delay_ticks(5)
            return
        if bank.is_open():
            yield from bot.close_script_bank(log)
        bot.log(f'restock: gear ok ({bot.gear_label()})')
        bot.set_status('restock: returning to camp')
        yield from bot.walk_home_if_needed(log)


class RestockGatherTool(Task):
    def __init__(self, bot):
        Task.__init__(self, label='restock gather tool')
        self.bot = bot

    def validate(self):
        bot = self.bot
        if bot.fishing or bot.has_gear() or len(bot.tool_reqs) == 0 or event_signal.pending() or game.in_combat():
            return False
        return not bot.has_broken_gather_tool() and not (bot.burn_enabled() and bot.burning_load)

    def try_acquire(self, log):
        """Buys, repairs or smiths what's missing. Use with yield from."""
        bot = self.bot
        buy = plan_gather_tool_acquire(bot.tool_reqs, bot.acquire_world_with_bank(), upgrade=False)
        if buy is None:
            return None
        # After depositing all but gear, the bars and hammer, or the shop's gp, stay when the keep list has them.
        prepared = bot.acquire_materials_held(buy)
        if bank.is_open():
            yield from bot.close_script_bank(log, False)
        ok = yield from bot.execute_tool_acquire_plan(buy, log, prepared)
        if ok:
            yield from bot.walk_home_if_needed(log)
        return ok

    def execute(self):
        bot = self.bot
        missing = bot.missing_gear_names()
        label = ' + '.join(missing) or bot.gear_label()
        power = bot.power_mode
        strict = bot.strict_desert_camp_banking()
        bot.set_status(f'restock: {label}')
        bot.log(f'restock: power mode — nearest bank for {label}' if power else f'restock: missing {label}')
        log = lambda m: bot.log(f'  {m}')
        stop = lambda reason: bot.stop_missing_gear(reason, missing)
        # Why: with the hammer and bar, the shop's gp or a broken tool in the pack, the camp's bank is skipped, since
        # walking Draynor first spends the walk's budget before the anvil.
        if bot.tool_acquire_enabled() and bot.acquire_ready() and len(missing) > 0:
            pre = plan_gather_tool_acquire(bot.tool_reqs, bot.acquire_world_with_bank(), upgrade=False)
            if pre is not None and bot.acquire_materials_held(pre):
                bot.log(f'restock: materials held for {pre.kind} — skipping bank')
                ok = yield from bot.execute_tool_acquire_plan(pre, log, True)
                if ok:
                    yield from bot.walk_home_if_needed(log)
                    return
                # Why: a failed walk or a random event with the materials held mustn't thrash the camp's bank; the
                # backoff stays off, so the next run tries again.
                bot.log(f'restock: {pre.kind} failed with materials still held — retry without bank')
                yield from execution.delay_ticks(3)
                return
        before_open = None
        if strict:
            before_open = yield from bot.shantay_backpack_before_open(log)
            if before_open is None:
                stop('normal backpack unreadable before Shantay bank')
                return
        opened = yield from bot.open_script_bank(log)
        if not opened:
            if power or strict:
                stop('could not open nearest bank')
                return
            bot.log(f'restock: could not open bank for {label} — will retry')
            yield from execution.delay_ticks(3)
            return
        if strict:
            ready = yield from bot.wait_bank_ready(log)
            if ready:
                ready = yield from bank.backpack_ready(before_open, log)
            if not ready:
                stop('Shantay bank did not become transaction-ready')
                return
        yield from execution.delay_ticks(bank_pace_ticks())
        yield from execution.delay_until_ticks(lambda: bank.loaded() or not bank.is_open(), 5)
        if power or bot.away_from_gather_spot():
            bot.log('restock: depositing non-gear first')
        deposit = bot.restock_deposit_matcher()
        if strict:
            deposited = yield from strict_deposit(bot, deposit, before_open, log, stop, 'restock deposit')
            if not deposited:
                return
        else:
            yield from bank.deposit_all_matching(deposit)
        yield from execution.delay_until_ticks(bank.loaded, 5)
        yield from execution.delay_ticks(1)
        plan = bot.gather_tool_restock_plan()
        if len(plan) == 0:
            still = bot.missing_gear_names()
            if len(still) == 0:
                bot.log('restock: tools already topped up')
                # Anything held unworn is wielded too, once out of the bank.
                leftover = bot.tools_to_equip()
                if bank.is_open():
                    yield from bot.prepare_worn_surplus_for_deposit(log)
                    yield from bot.deposit_surplus_gather_tools(log)
                    yield from bot.close_script_bank(log)
                if len(leftover) > 0:
                    yield from bot.equip_tools(leftover, log, False)
                return
            if bot.tool_acquire_enabled() and bot.acquire_ready():
                ok = yield from self.try_acquire(log)
                if ok:
                    return
                if ok is None:
                    bot.log(f"restock: acquire on but cannot fund/shop {' / '.join(still)} — need coins or materials")
                    bot.mark_acquire_backoff(50)
            if power or strict:
                bot.stop_missing_gear('bank has no required tools', still)
                return
            bot.set_status(f"restock: no {' / '.join(still) or label} in bank")
            bot.log(f"restock: bank has no {' / '.join(still)} — deposit tools and restart")
            yield from execution.delay_ticks(8)
            return
        for step in plan:
            yield from withdraw_step(bot, step.name, step.qty)
        # In the same visit: the surplus is taken off and deposited, the bank closed once, then the tools wielded.
        yield from bot.prepare_worn_surplus_for_deposit(log)
        yield from bot.deposit_surplus_gather_tools(log)
        to_equip = [s.name for s in plan if s.equip] + bot.tools_to_equip()
        if bank.is_open():
            yield from bot.close_script_bank(log)
        if len(to_equip) > 0:
            yield from bot.equip_tools(to_equip, log, False)
        if not bot.has_gear():
            still = bot.missing_gear_names()
            if bot.tool_acquire_enabled() and bot.acquire_ready():
                ok = yield from self.try_acquire(log)
                if ok:
                    return
            if power or strict:
                bot.stop_missing_gear('incomplete after withdraw', still)
                return
            bot.set_status(f"restock: still missing {' + '.join(still)}")
            bot.log(f"restock: incomplete — need {', '.join(still)}")
            yield from execution.delay_ticks(5)
            return
        bot.log(f'restock: tools ok ({bot.gear_label()})')
        yield from bot.walk_home_if_needed(log)


# Why: at the start it walks to the bank once for a better tier banked (steel while bronze is wielded), even burning,
# which has no BankCatch; after that only when at the bank already, never walking there just for a shop's upgrade,
# which read as a hang and pulled players off their trees. BankCatch also tries the upgrade after depositing.
class UpgradeGatherTool(Task):
    """A bank, shop or smith upgrade, when tool acquisition is on."""

    def __init__(self, bot):
        Task.__init__(self, label='upgrade gather tool')
        self.bot = bot

    def validate(self):
        bot = self.bot
        if not bot.tool_acquire_enabled() or bot.fishing or len(bot.tool_reqs) == 0 or bot.has_broken_gather_tool():
            return False
        if event_signal.pending() or game.in_combat() or (bot.burn_enabled() and bot.burning_load):
            return False
        if bot.startup_tool_bank_sync_needed():
            return True
        return bot.acquire_ready() and bot.has_gear() and bot.near_script_bank()

    def execute(self):
        yield from self.bot.try_upgrade_gather_tool_at_bank(lambda m: self.bot.log(f'  {m}'))


class StartupProvision(Task):
    """A bank visit at the start for the configured coins and teleport runes. Why: before the first walk to the camp,
    since an edge that charges coins would strand the run; it gives up after three tries, so an empty bank doesn't
    thrash."""

    def __init__(self, bot):
        Task.__init__(self, label='startup provision')
        self.bot = bot
        self.attempts = 0

    def validate(self):
        return self.bot.startup_provision_pending

    def execute(self):
        log = lambda m: self.bot.log(f'  {m}')
        self.attempts += 1
        if self.attempts > STARTUP_PROVISION_RETRIES:
            # Why: missing coins stays fatal, since a coin-charging edge strands the run; the runes are optional.
            yield from self.bot.give_up_startup_provision(log)
            return
        yield from self.bot.run_startup_provision(log)


def whirlpool(n):
    return n is not None and n.id in WHIRLPOOL_IDS


class Gather(Task):
    def __init__(self, bot):
        Task.__init__(self, label='gather')
        self.bot = bot
        self.active_fish_index = None
        self.active_mine_tile = None

    # Fishing spots.

    def fish_spot_origin(self):
        """Where fishing spots are ranked from."""
        bot = self.bot
        here = game.tile()
        if gather_spot_range_origin(bot.is_npc() and bot.location is None, here is not None, bot.location is not None) == 'player' and here is not None:
            return here
        return bot.anchor

    def freeform_hunt_radius(self):
        return gather_hunt_radius(self.bot.leash_radius)

    def fish_spot_base_ok(self, n):
        bot = self.bot
        return bot.usable(key_of(n.tile())) and not whirlpool(n) and bot.matches_spot(n.actions())

    # Why: a named camp takes any spot in the camp, with no wall on the player's distance; freeform takes one within
    # the hunt of the player or of the start's anchor, so a river hop is walked rather than idling.
    def fish_spot_in_range(self, spot):
        bot = self.bot
        if bot.avoids_spot(spot):
            return False
        if bot.location is not None:
            return resource_within_camp(bot.anchor.distance_to(spot), bot.leash_radius)
        hunt = self.freeform_hunt_radius()
        if spot_within_gather_range(self.fish_spot_origin().distance_to(spot), hunt):
            return True
        return spot_within_gather_range(bot.anchor.distance_to(spot), hunt)

    def find_fish_spot(self):
        return npcs.query().name(self.bot.target).where(lambda n: self.fish_spot_base_ok(n) and self.fish_spot_in_range(n.tile())).nearest()

    # Rocks and trees.

    def rock_ok(self, l):
        bot = self.bot
        return tile_within_leash(bot, l.tile()) and bot.matches_rock(l.id) and l.id not in GAS_ROCK_IDS and bot.usable(key_of(l.tile()))

    def rock_query(self):
        # Why: the camp's fence, the leash from the anchor, and the ore or tree filters come first.
        return locs.query().name(self.bot.target).action(self.bot.action).where(self.rock_ok)

    def find_rock(self, tile=None):
        query = self.rock_query()
        if tile is not None:
            query = query.within_of(tile, 0)
        return query.nearest_prefer_local(LOCAL_MINE_PREFER_RADIUS)

    def pick_rock(self):
        query = self.rock_query()
        if not self.bot.mining():
            return query.nearest_prefer_local(LOCAL_MINE_PREFER_RADIUS)
        rocks = query.results()
        best = pick_bucket_nearest(rocks, lambda l: rock_tier_by_id(l.id), lambda l: l.distance()) if len(rocks) > 0 else None
        if best is None:
            return None
        if random.random() < 0.1:
            # Why: variety across the tied rocks, never a lower tier.
            tier = rock_tier_by_id(best.id)
            tied = [l for l in rocks if rock_tier_by_id(l.id) == tier]
            return tied[math.floor(random.random() * len(tied))]
        return best

    def validate(self):
        bot = self.bot
        # Combat stops only AFK gathering; the retaliating tick methods go on.
        if inventory.is_full() or event_signal.pending() or combat_breaks_gather(game.in_combat(), bot.allow_combat_gather()):
            return False
        # After a flee, it doesn't walk back onto the spiders while the hold lasts.
        if bot.should_suppress_camp_reentry():
            return False
        if bot.cook_enabled() and (bot.cooking_load or bot.in_cook_batch):
            return False
        if bot.burn_enabled() and bot.burning_load:
            return False
        if not bot.has_gear():
            return bot.power_mode
        if bot.fishing and game.animating():
            return True
        if bot.is_npc():
            # Freeform fishing ranges from the player, but still yields past the start's leash so ReturnToAnchor
            # bounds the wander rather than chasing the river.
            if bot.location is None and beyond_leash(bot, game.tile(), 4):
                return False
            if self.find_fish_spot() is not None:
                return True
            # No spot in range: it stays on near the pier to say so, and yields when it's wandered off.
            return not beyond_leash(bot, game.tile(), 4)
        # Why: it stays on near the anchor to log "no trees/rocks" rather than idle silently, and yields past the
        # leash and slack so ReturnToAnchor can pull it back.
        if self.find_rock() is not None:
            return True
        return not beyond_leash(bot, game.tile(), 4)

    def gas_at(self, t):
        return locs.query().within_of(t, 0).where(lambda l: l.id in GAS_ROCK_IDS).nearest() is not None

    def ent_at(self, t):
        return npcs.query().within_of(t, 0).where(lambda n: n.id in ENT_NPC_IDS).nearest() is not None

    def spot_by_index(self, index):
        return npcs.query().where(lambda n: n.index == index).nearest()

    def fishing_broken(self, index, start_tile):
        live = self.spot_by_index(index)
        return fishing_session_broken(event_signal.pending(), inventory.is_full(), chat_dialog.can_continue(), game.in_combat(), live is None,
                                      live is not None and not live.tile() == start_tile, whirlpool(live), self.bot.allow_combat_gather())

    # Why: the cheap checks come before the scene queries, which ran on every poll.
    def should_yield_mine(self, tile):
        bot = self.bot
        if event_signal.pending() or inventory.is_full() or chat_dialog.can_continue():
            return True
        return loc_gather_should_yield(False, False, False, game.in_combat(), bot.allow_combat_gather(), bot.miner_food is not None and bot.should_eat_miner_food(),
                                       self.gas_at(tile) or self.ent_at(tile), self.find_rock(tile) is None)

    def flee_gas(self, key, tile):
        """Use with yield from."""
        self.active_mine_tile = None
        self.bot.log(f'mine: smoking rock @ {tile} — backing off')
        self.bot.set_status('mine: smoking rock')
        self.bot.cooldown(key, GAS_ROCK_TICKS + 10)
        direct_navigator.walk(self.bot.anchor)
        yield from execution.delay_ticks(2)

    def flee_whirlpool(self, tile):
        """Use with yield from."""
        self.bot.log(f'fish: whirlpool @ {tile} — stepping off')
        self.bot.set_status('fish: whirlpool')
        self.bot.cooldown(key_of(tile), 70)
        direct_navigator.walk(self.bot.anchor)
        yield from execution.delay_ticks(2)

    def abort_ent(self, key, tile):
        """Why: leaving the animation's wait doesn't stop the swing, so a new action does. Use with yield from."""
        bot = self.bot
        bot.log(f'gather: ent @ {tile} — switching tree')
        bot.set_status('gather: ent')
        bot.cooldown(key, ENT_LIFE_TICKS + 10)
        neighbour = self.find_rock()
        here = game.tile()
        neighbour_tile = neighbour.tile() if neighbour is not None else None
        in_reach = neighbour_tile is not None and here is not None and here.distance_to(neighbour_tile) <= 1
        action = ent_abort_action(in_reach, neighbour is not None)
        if action == 'chop-neighbour':
            neighbour.interact(bot.action)
            self.active_mine_tile = neighbour_tile
            return
        self.active_mine_tile = None
        if action == 'walk-to-neighbour':
            direct_navigator.walk(neighbour_tile)
        elif here is not None:
            steps = step_off_candidates(here, tile)
            if len(steps) > 0:
                direct_navigator.walk(steps[0])
        yield from execution.delay_ticks(2)

    def execute(self):
        bot = self.bot
        if not bot.has_gear():
            self.active_mine_tile = None
            bot.set_status(f'gather: missing {bot.gear_label()}')
            bot.log(f'gather: missing {bot.gear_label()}')
            yield from execution.delay_ticks(5)
            return
        if event_signal.pending() or combat_breaks_gather(game.in_combat(), bot.allow_combat_gather()):
            self.active_mine_tile = None
            return
        if bot.fishing:
            yield from self.execute_fish()
            return
        yield from self.execute_mine()

    def after_roll_tick_manip(self, reclick):
        """After a resource's roll: arms the knife delay or times the click again. True when the caller skips its
        usual wait this beat. Use with yield from."""
        bot = self.bot
        profile = bot.tick_manip
        if profile.method == 'off':
            return False
        bot.note_gather_roll()
        if profile.use_knife_delay:
            if not bot.has_knife_delay_kit() and not chat_dialog.is_make_menu():
                bot.log('tick: knife delay needs Knife + 1 fletchable log')
                return False
            # The knife and Make-1 arm two ticks, the resource is clicked again, and the delay runs out to the roll.
            if knife_delay_phase(game.tick(), bot.last_roll_tick) == 'delay-action' or chat_dialog.is_make_menu():
                armed = yield from bot.arm_knife_delay()
                if not armed and not chat_dialog.is_make_menu():
                    bot.log('tick: knife delay arm failed')
                    return False
            # It doesn't wait for the fletched product: the click goes the next tick.
            yield from execution.delay_until_ticks(lambda: game.tick() >= bot.last_roll_tick + 1, 2)
            reclick()
            return True
        # The farmer's six ticks are execute_farmer_willow's; only the roll is stamped here.
        if profile.farmer_willow_cycle:
            return False
        # A timed click again: 4t fly, the pickaxe's iron rate, and the retaliating methods with a known cycle.
        cycle = bot.gather_cycle_ticks()
        if cycle is not None and cycle >= 1 and (profile.timed_reclick or profile.method == 'iron-cadence' or profile.allow_combat or profile.native_cycle_ticks is not None):
            due = next_gather_click_tick(bot.last_roll_tick, cycle)
            bot.set_status(f'tick: wait {cycle}t reclick')
            interrupted = lambda: inventory.is_full() or event_signal.pending() or combat_breaks_gather(game.in_combat(), bot.allow_combat_gather())
            yield from execution.delay_until_ticks(lambda: game.tick() >= due or interrupted(), max(1, due - game.tick() + 2))
            if not interrupted():
                reclick()
            return True
        return False

    def reclick_fish(self, index):
        live = self.spot_by_index(index)
        if live is None or whirlpool(live):
            return False
        self.bot.set_status(f'tick: reclick {self.bot.action}')
        return live.interact(self.bot.action)

    def reclick_mine(self, tile):
        rock = self.find_rock(tile) or self.pick_rock()
        if rock is None:
            self.active_mine_tile = None
            return False
        self.bot.set_status(f'tick: reclick {self.bot.action}')
        clicked = rock.interact(self.bot.action)
        self.active_mine_tile = rock.tile() if clicked else None
        return clicked

    def off_camp_miss(self, status):
        """No target: back to the camp when clearly off it, not the tight disk around it. Use with yield from."""
        bot = self.bot
        here = game.tile()
        if here is not None and should_soft_home_from_gather_miss(bot.anchor.distance_to(here), bot.leash_radius):
            bot.set_status(status)
            yield from bot.walk_home_if_needed(lambda m: bot.log(f'  {m}'))
            return True
        return False

    def execute_fish(self):
        """Use with yield from."""
        bot = self.bot
        target = self.find_fish_spot()
        if target is None:
            self.active_fish_index = None
            # A short wait for the last cast, waking if a spot comes back.
            if game.animating():
                bot.set_status('fish: finishing cast (no spot)')
                yield from execution.delay_until_ticks(lambda: not game.animating() or self.find_fish_spot() is not None or event_signal.pending() or inventory.is_full()
                                                       or combat_breaks_gather(game.in_combat(), bot.allow_combat_gather()) or chat_dialog.can_continue(), 5)
                return
            homed = yield from self.off_camp_miss('fish: returning to camp')
            if homed:
                return
            stop = bot.next_sweep_stop()
            if stop is not None:
                bot.set_status(f'fish: sweeping to {stop}')
                yield from traversal.walk_resilient(stop, radius=1, attempts=2, timeout_ms=SWEEP_WALK_MS, log=lambda m: bot.log(f'  {m}'))
                return
            bot.set_status(f'fish: no spots in camp (r{bot.leash_radius} of home)' if bot.location is not None else f'fish: no spots within {self.freeform_hunt_radius()} of you/start')
            yield from execution.delay_ticks(2)
            return
        # A spot more than a few tiles off is walked to, a pier hop or a camp scan.
        here = game.tile()
        if here is not None and here.distance_to(target.tile()) > 2:
            bot.set_status(f'fish: walking to spot @ {target.tile()}')
            yield from traversal.walk_to(target.tile(), radius=1, timeout_ms=20000)
            # Found again after the walk, since the spot may have moved.
            target = self.find_fish_spot()
            if target is None:
                self.active_fish_index = None
                return
        yield from self.fish_at(target)

    def fish_ended(self, index, start_tile):
        """Whether the session's over, stepping off a whirlpool when that's why. Use with yield from."""
        if not self.fishing_broken(index, start_tile):
            return False
        self.active_fish_index = None
        live = self.spot_by_index(index)
        if whirlpool(live):
            yield from self.flee_whirlpool(live.tile())
        return True

    def fish_at(self, target):
        """Use with yield from."""
        bot = self.bot
        index = target.index
        start_tile = target.tile()
        key = key_of(start_tile)
        # Why: a fresh click cancels a leftover cast's animation, so there's no waiting it out first.
        if not game.animating() or self.active_fish_index != index:
            bot.set_status(f'{bot.action} {bot.target} at {start_tile}')
            before = inventory.used()
            if not target.interact(bot.action):
                bot.log(f"no '{bot.action}' op on {bot.target}? ops=[{', '.join(target.actions())}]")
                self.active_fish_index = None
                yield from execution.delay_ticks(2)
                return
            yield from execution.delay_until_ticks(lambda: inventory.used() > before or game.animating() or self.fishing_broken(index, start_tile), 20)
            live = self.spot_by_index(index)
            if whirlpool(live):
                self.active_fish_index = None
                yield from self.flee_whirlpool(live.tile())
                return
            if inventory.used() == before and not game.animating():
                self.active_fish_index = None
                if self.fishing_broken(index, start_tile):
                    if chat_dialog.can_continue():
                        bot.reject(key)
                else:
                    bot.cooldown(key, 4)
                return
            self.active_fish_index = index
            if inventory.used() > before:
                timed = yield from self.after_roll_tick_manip(lambda: self.reclick_fish(index))
                if timed:
                    return
        for _ in range(200):
            ended = yield from self.fish_ended(index, start_tile)
            if ended:
                return
            mark = inventory.used()
            yield from execution.delay_until_ticks(lambda: inventory.used() > mark or not game.animating() or self.fishing_broken(index, start_tile), 14)
            ended = yield from self.fish_ended(index, start_tile)
            if ended:
                return
            if inventory.used() > mark:
                timed = yield from self.after_roll_tick_manip(lambda: self.reclick_fish(index))
                if timed:
                    return
                continue
            if not game.animating():
                break
        self.active_fish_index = None

    def hazard_check(self, key, tile):
        """Backs off a smoking rock or an ent: True when it did. Use with yield from."""
        if self.gas_at(tile):
            yield from self.flee_gas(key, tile)
            return True
        if self.ent_at(tile):
            yield from self.abort_ent(key, tile)
            return True
        return False

    def execute_mine(self):
        """Use with yield from."""
        bot = self.bot
        # The farmer's willows run their own six-tick loop.
        if bot.tick_manip.farmer_willow_cycle:
            yield from self.execute_farmer_willow()
            return
        active = self.active_mine_tile
        if active is not None and game.animating() and self.ent_at(active):
            yield from self.abort_ent(key_of(active), active)
            return
        target = self.find_rock(active) if active is not None else None
        if target is None:
            if active is not None and self.ent_at(active):
                yield from self.abort_ent(key_of(active), active)
                return
            self.active_mine_tile = None
            target = self.pick_rock()
        if target is None:
            # Near the anchor with nothing to gather: it says why it's idle.
            if game.animating():
                bot.set_status(f'{bot.action}: finishing')
                yield from execution.delay_until_ticks(lambda: not game.animating() or self.find_rock() is not None or event_signal.pending() or inventory.is_full()
                                                       or combat_breaks_gather(game.in_combat(), bot.allow_combat_gather()) or chat_dialog.can_continue(), 5)
                return
            homed = yield from self.off_camp_miss('gather: returning to camp')
            if homed:
                return
            kind = 'trees' if bot.woodcutting() else 'rocks'
            bot.set_status(f'gather: no {bot.target} in leash')
            bot.log(f"gather: no '{bot.target}' ({bot.action}) {kind} within leash {bot.leash_radius} of {bot.anchor}")
            yield from execution.delay_ticks(3)
            return
        tile = target.tile()
        here = game.tile()
        # Why: a click on scenery can succeed with no route to a target off screen, which clicked forever in broad camps.
        if here is not None and here.distance_to(tile) > 2:
            bot.set_status(f'gather: walking to {bot.target} @ {tile}')
            reached = yield from traversal.walk_to(tile, radius=1, timeout_ms=45000, log=lambda m: bot.log(f'  {m}'))
            if not reached:
                bot.log(f'gather: could not approach {bot.target} @ {tile} from {here}')
                self.active_mine_tile = None
                return
            target = self.find_rock(tile)
            if target is None or self.should_yield_mine(tile):
                self.active_mine_tile = None
                return
        key = key_of(tile)
        if not game.animating() or self.active_mine_tile is None or not self.active_mine_tile == tile:
            bot.set_status(f'{bot.action} {bot.target} at {tile}')
            before = inventory.used()
            if not target.interact(bot.action):
                self.active_mine_tile = None
                bot.log(f"no '{bot.action}' op on {bot.target}? ops=[{', '.join(target.actions())}]")
                yield from execution.delay_ticks(2)
                return
            self.active_mine_tile = tile
            yield from execution.delay_until_ticks(lambda: inventory.used() > before or game.animating() or self.should_yield_mine(tile), 20)
            yield from sustain.run()
            fled = yield from self.hazard_check(key, tile)
            if fled:
                return
            if inventory.used() == before and not game.animating():
                self.active_mine_tile = None
                if chat_dialog.can_continue():
                    bot.reject(key)
                elif should_cooldown_gather_tile(False, self.find_rock(tile) is not None):
                    # A failed click with other targets about: a short skip.
                    bot.cooldown(key)
                return
            if inventory.used() > before:
                timed = yield from self.after_roll_tick_manip(lambda: self.reclick_mine(tile))
                if timed:
                    return
        for _ in range(200):
            yield from sustain.run()
            if self.should_yield_mine(tile):
                self.active_mine_tile = None
                yield from self.hazard_check(key, tile)
                return
            mark = inventory.used()
            yield from execution.delay_until_ticks(lambda: inventory.used() > mark or not game.animating() or self.should_yield_mine(tile), 14)
            yield from sustain.run()
            fled = yield from self.hazard_check(key, tile)
            if fled:
                return
            if inventory.used() > mark:
                timed = yield from self.after_roll_tick_manip(lambda: self.reclick_mine(tile))
                if timed:
                    return
                continue
            # Why: an emptied rock or a stump drops out of find_rock already, so a natural end needs no cooldown, and
            # iron comes back faster than one would last.
            if not game.animating():
                break
        self.active_mine_tile = None

    # Why: the cycle is a click on the tree, three ticks' wait, the knife on a log, the log dropped, and again;
    # retaliating stays on, so the bot may die. It needs a knife and willow logs.
    def execute_farmer_willow(self):
        """The farmer's willows, a six-tick cycle. Use with yield from."""
        bot = self.bot
        if event_signal.pending() or inventory.is_full() or chat_dialog.can_continue():
            return
        active = self.active_mine_tile
        if active is not None and game.animating() and self.ent_at(active):
            yield from self.abort_ent(key_of(active), active)
            return
        # The cycle's clock is set again when unset or stale, after a login or a long wait.
        now = game.tick()
        start = bot.farmer_cycle_start
        if start < 0 or now - start > 18:
            bot.farmer_cycle_start = now
            start = now
        phase = farmer_willow_phase(game.tick(), start)
        if phase == 'click-tree':
            yield from self.farmer_click_tree()
            return
        if phase == 'cut-log':
            yield from self.farmer_cut_log()
            return
        if phase == 'drop-log':
            yield from self.farmer_drop_log()
            return
        # The waits: until the cut, the drop or the next click.
        bot.set_status('farmer: wait')

        def done():
            if event_signal.pending() or inventory.is_full() or chat_dialog.can_continue():
                return True
            if self.active_mine_tile is not None and self.ent_at(self.active_mine_tile):
                return True
            return farmer_willow_phase(game.tick(), bot.farmer_cycle_start) != 'wait'

        yield from execution.delay_until_ticks(done, 7)
        if self.active_mine_tile is not None and self.ent_at(self.active_mine_tile):
            yield from self.abort_ent(key_of(self.active_mine_tile), self.active_mine_tile)

    def farmer_click_tree(self):
        """Use with yield from."""
        bot = self.bot
        tree = self.find_rock()
        if tree is None:
            homed = yield from self.off_camp_miss('farmer: returning to camp')
            if not homed:
                bot.set_status('farmer: no tree in leash')
                yield from execution.delay_ticks(2)
            return
        tile = tree.tile()
        bot.set_status(f'farmer t1: chop {bot.target} @ {tile}')
        # Stamped on the click's beat, so the cycle's first phase stays aligned.
        bot.farmer_cycle_start = game.tick()
        before = inventory.used()
        if not tree.interact(bot.action):
            bot.log(f"farmer: no '{bot.action}' on tree")
            yield from execution.delay_ticks(1)
            return
        self.active_mine_tile = tile
        # A short wait for the animation or a log: the cut is processed at t5.
        yield from execution.delay_until_ticks(lambda: inventory.used() > before or game.animating() or event_signal.pending() or inventory.is_full() or self.ent_at(tile), 3)
        if self.ent_at(tile):
            yield from self.abort_ent(key_of(tile), tile)
            return
        if inventory.used() > before:
            bot.note_gather_roll()
        yield from execution.delay_until_ticks(lambda: farmer_willow_phase(game.tick(), bot.farmer_cycle_start) != 'wait', 8)

    def farmer_cut_log(self):
        """The knife on the newest log, which arms the delay and processes the roll. Use with yield from."""
        bot = self.bot
        if chat_dialog.is_make_menu():
            bot.set_status('farmer t5: make-x')
            yield from bot.arm_knife_delay()
            return
        log_item = first_where(inventory.items(), lambda i: bot.is_product(i.name) and is_fletchable_log_name(i.name)) or bot.delay_log_item()
        knife = inventory.first(TICK_MANIP_KNIFE)
        if knife is None or log_item is None:
            bot.set_status('farmer t5: need knife + log')
            bot.log('farmer: cut-log needs Knife + a fletchable log')
            yield from execution.delay_ticks(1)
            return
        bot.set_status(f'farmer t5: knife {log_item.name}')
        if not knife.use_on(log_item):
            yield from execution.delay_ticks(1)
            return
        yield from execution.delay_until_ticks(lambda: chat_dialog.is_make_menu() or chat_dialog.can_continue() or not game.animating(), 3)
        if chat_dialog.is_make_menu():
            yield from bot.arm_knife_delay()
        yield from execution.delay_until_ticks(lambda: farmer_willow_phase(game.tick(), bot.farmer_cycle_start) == 'drop-log', 4)

    def farmer_drop_log(self):
        """Use with yield from."""
        bot = self.bot
        bot.set_status('farmer t6: drop log')
        dropped = yield from bot.drop_one_product_log()
        if not dropped:
            # Nothing to drop: the clock goes on regardless.
            bot.log('farmer: drop-log with empty product slot')

        def next_cycle():
            s = bot.farmer_cycle_start
            return game.tick() - s >= 6 or farmer_willow_phase(game.tick(), s) == 'click-tree'

        yield from execution.delay_until_ticks(next_cycle, 4)
        # The start rolls on by whole cycles, so the first phase lands on the next click's beat.
        s = bot.farmer_cycle_start
        if game.tick() - s >= 6:
            bot.farmer_cycle_start = s + 6 * ((game.tick() - s) // 6)


# Mule and partner trades (the policy is rs2004.catalogs' partner).

MULE_TRADE_GRACE_MS = 2000


def _signed(delta):
    return f"{'+' if delta >= 0 else ''}{delta}"


class HandleGatherMuleTrade(Task):
    """Owns the loop while a mule trade's window is open, since movement cancels it, as giver or receiver."""

    def __init__(self, bot):
        Task.__init__(self, label='Handle gather mule trade')
        self.bot = bot
        self.partner_wait = 0
        # Holds the task through the frame-long "no screen" blips between the trade's screens.
        self.own_trade_until = 0
        # Across beats, to tell why a window went.
        self.last_screen = 'closed'
        self.open_used = 0
        self.saw_confirm = False
        self.transferred = False

    def validate(self):
        if self.bot.mule_mode == 'off':
            self.own_trade_until = 0
            return False
        if trade.active():
            self.own_trade_until = _core.step_time() + MULE_TRADE_GRACE_MS
            return True
        # Why: the offer-to-confirm swap and the final teardown each report no screen for a frame, and yielding there
        # lets gathering click under a window still up, so ownership is held through a short grace.
        return _core.step_time() < self.own_trade_until

    def missing_partner(self):
        self.partner_wait += 1
        if self.partner_wait == 1:
            self.bot.log('trade: offer screen up but the partner header is still blank — waiting')
        if self.partner_wait > 8:
            self.partner_wait = 0
            return 'decline'
        return 'wait'

    def can_accept(self, count):
        if inventory.free() > 0:
            return True
        return (False, 'mule: pack full — cannot accept product (bank/cook first)')

    def product_match(self, name):
        if self.bot.is_mule_cooker():
            return self.bot.should_deposit_raw_catch(name) or self.bot.should_deposit(name)
        return self.bot.should_deposit(name)

    def completed(self, delta):
        # The receiver gains slots used; the giver loses product.
        ok = delta > 0 if self.receiver else delta < 0
        if not ok:
            self.bot.log(f'mule: trade closed without transfer (inv Δ{_signed(delta)}) — not counting')
            return
        self.transferred = True
        self.bot.mule_trades += 1
        self.bot.log(f'mule: trade complete (inv Δ{_signed(delta)}, trades={self.bot.mule_trades})')

    def execute(self):
        bot = self.bot
        self.receiver = bot.is_mule_receiver() or bot.is_mule_cooker()
        giver = not self.receiver
        self.transferred = False
        screen_at_entry = trade_screen_state()
        if screen_at_entry == 'offer' and self.last_screen == 'closed':
            self.open_used = inventory.used()
            self.saw_confirm = False
            bot.log('trade: new handshake — offer screen up')
        elif screen_at_entry == 'confirm':
            self.saw_confirm = True
        yield from drive_active_partner_trade(
            'receiver' if self.receiver else 'giver', bot.mule_partners, self.product_match, bot.depositable_product_names, bot.set_status, bot.log,
            on_complete=self.completed,
            on_decline=lambda reason: bot.log(f'trade: we declined the trade ({reason})'),
            on_missing_partner=self.missing_partner,
            receiver_can_accept=self.can_accept if self.receiver else None,
            my_offer_ready=(lambda: count_offer_matching(trade.my_offer(), bot.should_deposit) > 0) if giver else None,
            baseline=lambda: self.open_used,
            verify_giver_partner=giver,
            labels={'accepting': 'mule: accepting raw for cook' if bot.is_mule_cooker() else 'mule: accepting product'})
        if trade.partner() is not None:
            self.partner_wait = 0
        # Why: screens up at the last beat's end and gone now, with no confirm and no transfer, means the partner
        # dropped it; the driver accounts for closes mid-beat.
        screen_now = trade_screen_state()
        if screen_at_entry == 'closed' and self.last_screen != 'closed' and not self.saw_confirm and not self.transferred:
            d = inventory.used() - self.open_used
            bot.log(f'trade: window closed between beats without reaching confirm or us declining — the partner most likely declined, walked away or logged out (inv Δ{_signed(d)})')
        if screen_now != 'closed':
            self.last_screen = screen_now
        elif not trade.active():
            self.last_screen = 'closed'
        # Why: a closed report isn't proof of a settled pack, so the giver checks the traded items left before
        # gathering resumes; the receiver's gain is its proof.
        if self.transferred and giver:
            cleared = yield from execution.delay_until(lambda: len(bot.depositable_product_names()) == 0, 3000)
            if cleared:
                bot.log('mule: verified — pack cleared of traded items')
            else:
                bot.log(f"mule: VERIFY FAILED — still holding {', '.join(bot.depositable_product_names()) or 'unknown items'}")
        if trade.active():
            self.own_trade_until = _core.step_time() + MULE_TRADE_GRACE_MS


class MuleGoMeet(Task):
    def __init__(self, bot):
        Task.__init__(self, label='Mule go meet')
        self.bot = bot

    def validate(self):
        bot = self.bot
        if trade.active() or event_signal.pending() or bot.at_mule_meet():
            return False
        if bot.is_mule_gatherer() or bot.is_mule_supplier():
            return inventory.is_full() and bot.has_depositable()
        if bot.is_mule_receiver():
            # The mule goes back to the meet with an empty pack, after banking.
            return not bot.has_depositable() or not inventory.is_full()
        if bot.is_mule_cooker():
            # Idle and empty goes to the meet; holding raw, the cook tasks own the loop.
            return bot.cookable_raw_count() == 0 and bot.cooked_fish_count() == 0
        return False

    def execute(self):
        meet = self.bot.get_meet_tile()
        self.bot.set_status(f'mule: walking to meet {meet}')
        yield from traversal.walk_resilient(meet, radius=2, timeout_ms=90000, log=lambda m: self.bot.log(f'  {m}'))


class MuleRequestOrWait(Task):
    def __init__(self, bot):
        Task.__init__(self, label='Mule request or wait')
        self.bot = bot

    def validate(self):
        bot = self.bot
        if trade.active() or event_signal.pending() or not bot.at_mule_meet():
            return False
        if bot.is_mule_gatherer() or bot.is_mule_supplier():
            return inventory.is_full() and bot.has_depositable()
        if bot.is_mule_receiver() or bot.is_mule_cooker():
            # Idle at the meet waiting for the gatherer or supplier; a cooker holding raw cooks.
            if bot.is_mule_cooker() and bot.cookable_raw_count() > 0:
                return False
            return not bot.has_depositable() or bot.is_mule_cooker()
        return False

    def execute(self):
        bot = self.bot
        partner = bot.nearest_mule_partner()
        if partner is None or partner.distance() > DEFAULT_TRADE_RANGE:
            msg = 'mule: waiting for gatherer'
            if bot.is_mule_gatherer() or bot.is_mule_supplier():
                msg = 'mule: waiting for partner at meet'
            elif bot.is_mule_cooker():
                msg = 'mule: cooker waiting for raw'
            bot.set_status(msg)
            bot.log(msg)
            yield from execution.delay_ticks(2)
            return
        name = partner.name or (bot.mule_partners[0] if len(bot.mule_partners) > 0 else '')
        bot.set_status(f"mule: requesting trade with {name or 'partner'}")
        trade.request(name)
        # Wall-clock: a two-player Trade with isn't tied to this client's tick rate.
        yield from execution.delay_until(lambda: trade.active() or event_signal.pending(), 5000)


class SupplierWithdrawRaw(Task):
    """The supplier: the bank's raw fish, a pack of it withdrawn, to the meet and traded to the cooker. The bank raw
    before cook setting is the "N ready" gate before a trip starts."""

    def __init__(self, bot):
        Task.__init__(self, label='Supplier withdraw raw')
        self.bot = bot

    def validate(self):
        bot = self.bot
        if not bot.is_mule_supplier() or trade.active() or event_signal.pending():
            return False
        # Already carrying raw for the hand-off.
        return bot.raw_fish_count() == 0

    def execute(self):
        bot = self.bot
        log = lambda m: bot.log(f'  {m}')
        target = max(1, bot.bank_raw_target or 28)
        bot.set_status(f'mule: supplier withdraw raw (need bank ≥{target})')
        opened = yield from bot.open_script_bank(log)
        if not opened:
            bot.log('mule: supplier bank open failed — retry')
            return
        yield from execution.delay_ticks(1)
        bank_raw = sum([max(1, i.count) for i in bank.items() if bot.is_cookable_raw(i.name)])
        if bank_raw < target:
            bot.log(f'mule: supplier bank raw {bank_raw} < {target} — waiting')
            if bank.is_open():
                yield from bank.close()
            yield from execution.delay_ticks(8)
            return
        bot.log(f'mule: supplier withdrawing raw (bank {bank_raw})')
        for i in range(40):
            if inventory.free() <= 0:
                break
            stacks = [it for it in bank.items() if bot.is_cookable_raw(it.name) and it.count > 0]
            if len(stacks) == 0 or not stacks[0].name:
                break
            name = stacks[0].name
            before = bot.raw_fish_count()
            bank.withdraw(name, 'Withdraw All')
            yield from execution.delay_until_ticks(lambda: bot.raw_fish_count() > before or inventory.is_full(), 5)
            if bot.raw_fish_count() == before:
                # A single one, when All didn't land.
                bank.withdraw(name, 'Withdraw 1')
                yield from execution.delay_until_ticks(lambda: bot.raw_fish_count() > before or inventory.is_full(), 4)
                if bot.raw_fish_count() == before:
                    break
        if bank.is_open():
            yield from bank.close()
        bot.log(f'mule: supplier pack raw={bot.raw_fish_count()} free={inventory.free()}')


class MuleBankHaul(Task):
    def __init__(self, bot):
        Task.__init__(self, label='Mule bank haul')
        self.bot = bot

    def validate(self):
        bot = self.bot
        if not bot.is_mule_receiver() or trade.active() or event_signal.pending():
            return False
        return bot.has_depositable()

    def execute(self):
        bot = self.bot
        log = lambda m: bot.log(f'  {m}')
        had = len(bot.products())
        bot.set_status('mule: banking haul')
        opened = yield from bot.open_script_bank(log)
        if not opened:
            bot.log('mule: bank open failed — will retry')
            return
        yield from execution.delay_ticks(1)
        yield from bank.deposit_all_matching(lambda name, id: bot.should_deposit(name))
        yield from execution.delay_until_ticks(lambda: not bot.has_depositable() or not bank.is_open(), 9)
        if bank.is_open():
            yield from bank.close()
        bot.count_trip(had)
        bot.log(f'mule: deposited haul ({had} stacks, trades={bot.mule_trades})')
        # Back toward the meet, at the camp.
        yield from bot.walk_home_if_needed(log)


# The guild's feathers and Shilo's supplies.


class BuyGuildFeathers(Task):
    """Why: Roachey's feathers come back one a tick toward 1500, so a bought-out stack is fifteen minutes from full and
    the trip is worth taking on that clock, not only when the pack runs dry. The shop is a short walk from the guild
    pier, and the run banks nothing on the way."""

    def __init__(self, bot):
        Task.__init__(self, label='Buy guild feathers')
        self.bot = bot

    def validate(self):
        if event_signal.pending() or game.in_combat() or inventory.is_full():
            return False
        vendor = self.bot.bait_vendor()
        return vendor is not None and vendor.keeper != 'Fernahei' and self.bot.guild_feather_trip_due()

    def execute(self):
        bot = self.bot
        vendor = bot.bait_vendor()
        if vendor is None:
            return
        log = lambda m: bot.log(f'  {m}')
        # Why: the clock starts on the attempt rather than the sale, or a shop that won't open is retried every loop.
        bot.note_guild_feather_trip()
        if inventory.count(COINS) < vendor.price:
            bot.set_status('feathers: drawing coins')
            opened = yield from bot.open_script_bank(log)
            if not opened:
                bot.log('feathers: could not open the bank for coins, will try again next round')
                return
            yield from execution.delay_until_ticks(lambda: bank.loaded() or not bank.is_open(), 5)
            yield from bank.deposit_all_matching(bot.restock_deposit_matcher())
            draw = feather_coins_to_draw(inventory.count(COINS), bank.count(COINS), vendor.price)
            if draw > 0:
                bot.log(f'feathers: drawing {draw}gp of the {bank.count(COINS)}gp banked')
                yield from bank.withdraw_x(COINS, draw)
            yield from bot.close_script_bank(log, False)
        coins = inventory.count(COINS)
        if coins < vendor.price:
            bot.log(f'feathers: only {coins}gp on hand or banked, skipping {vendor.keeper} this round')
            return
        bot.set_status(f'feathers: walking to {vendor.keeper}')
        arrived = yield from traversal.walk_resilient(vendor.stand, radius=2, attempts=3, timeout_ms=SHOP_WALK_MS, log=log)
        if not arrived:
            bot.log(f'feathers: could not reach {vendor.keeper}, will try again next round')
            return
        opened = yield from shop.open(vendor.keeper)
        if not opened:
            bot.log(f"feathers: could not open {vendor.keeper}'s shop")
            return
        bot.set_status('feathers: buying out the stack')
        before = inventory.count(vendor.item)
        stock = 0
        for line in shop.stock():
            if line.name == vendor.item:
                stock = line.count
                break
        yield from shop.buy(vendor.item, min(stock, coins // vendor.price))
        yield from shop.close()
        got = inventory.count(vendor.item) - before
        bot.log(f'feathers: bought {got} from {vendor.keeper} (holding {inventory.count(vendor.item)})' if got > 0 else f'feathers: {vendor.keeper} had none to sell')
        bot.set_status('feathers: back to the water')
        yield from bot.walk_home_if_needed(log)


class BuyShiloSupplies(Task):
    def __init__(self, bot):
        Task.__init__(self, label='Buy shilo supplies')
        self.bot = bot

    def validate(self):
        if event_signal.pending() or game.in_combat():
            return False
        vendor = self.bot.bait_vendor()
        return vendor is not None and vendor.keeper == 'Fernahei' and (self.bot.shilo_supply_trip.active or self.bot.guild_feather_trip_due())

    def execute(self):
        yield from self.bot.shilo_supply_trip.step(self.bot)
