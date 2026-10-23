# GatheringBot: rs2b0t's scripts/GatheringBot/GatheringBot.ts (MIT, see thirdparty/rs2b0t), the bot behind the Miner,
# Woodcutter and Fisher. Each entry script's settings pick the skill: rocks for the miner, tree_name for the
# woodcutter, fish_method for the fisher. It gathers at a named camp or freeform around its start, banks the haul or
# drops it, cooks the catch, burns the logs, and keeps its tools, buying, repairing or smithing them. The mule
# hand-offs and the guild feather and Shilo supply runs aren't ported yet.

import math
import random
import time

from rs2004.catalogs import AcquireWorld, buy_plans_cost
from rs2004.catalogs import AXE_BAR_FOR, BROKEN_AXE, BROKEN_PICKAXE, COINS, DEFAULT_CHASE_RADIUS, FISHING_METHOD_OPTIONS, FORGETFUL_BANK_ODDS, HAMMER
from rs2004.catalogs import HOME_ARRIVE_RADIUS, NONE_LEGACY, ROCK_OPTIONS, TINDERBOX, ContinueDialog, axe_req, best_axe, best_held_tool_names, best_pickaxe
from rs2004.catalogs import can_fund_plan, can_wield_tool, cook_surface_for_fish_camp, count_food, create_return_to_anchor_task, expand_local_fire_plot
from rs2004.catalogs import firemaking_level_for_logs, fishing_gear_shop_cart, fishing_restock_plan, food_forms, food_heal_amount, gear_keep_names, gear_label
from rs2004.catalogs import has_all_tools, has_fishing_gear, is_fishing_bait_piece, is_food_item, local_fire_plot, logs_for_tree, missing_fishing_gear
from rs2004.catalogs import missing_tool_labels, parse_burn_mode, parse_tool_acquire_mode, pickaxe_req, plan_gather_tool_acquire, resolve_camp_radius
from rs2004.catalogs import resolve_chase_radius, resolve_fire_spot, resolve_fish_camp_cook_surface, resolve_fish_method, resolve_fishing_location
from rs2004.catalogs import resolve_mining_location, resolve_rock_ids, resolve_run_anchor, resolve_woodcutting_location, should_burn_full_load
from rs2004.catalogs import should_walk_home_to_gather_anchor, spot_matches_method, surplus_held_tool_names, sustain, tile_within_leash, tinderbox_req
from rs2004.catalogs import tool_attack_level, tool_keep_names, tool_kit_label, tool_restock_plan, tools_needing_equip, with_bait_target, Record
from rs2004.quests.exec.primitives import drive_dialog

from bots.gathering.camp import NAMED_CAMP_LEASH_FLOOR, effective_gather_leash, is_auto_location, is_custom_location, spot_avoided, sweep_stop_for
from bots.gathering.chop_burn import create_chop_burn_tasks
from bots.gathering.desert_camp import DesertMiningCampRoute, desert_camp_bank_catch_needed, desert_camp_bank_trip_direction, desert_camp_destination_for
from bots.gathering.desert_camp import desert_camp_keep_names, is_desert_camp_location
from bots.gathering.fish_cook import cook_batch_after_load, cook_filter_label, count_raw_in_bank, is_burnt_fish_name, is_cooked_fish_name, is_raw_fish_name
from bots.gathering.fish_cook import last_matching_index, parse_after_cook_cycle, parse_burnt_policy, parse_cook_mode, parse_positive_int, raw_matches_cook_filter
from bots.gathering.fish_cook import resolve_cook_fish_filter, should_cook_then_bank, should_start_bank_raw_cook_batch
from bots.gathering.logic import gathering_combat_policy, hostile_attacker_nearby, incoming_player_attacker, wilderness_miner_at, wilderness_miner_stance_needed
from bots.gathering.miner_logic import desert_camp_food_reserve_depleted, miner_food_config, miner_food_restock_needed, plan_miner_food_withdrawal
from bots.gathering.miner_logic import should_eat_miner_food, unsupported_camp_ores
from bots.gathering.tasks import STARTUP_PROVISION_RETRIES, BankCatch, ClearPackJunk, DesertMiningCampTravel, DropProduct, EnsureGatherToolEquipped
from bots.gathering.tasks import EnsureShortbowRapid, FishBankCooked, FishCookDialog, FishCookLoad, FishWithdrawCookBatch, FleeCombat, Gather
from bots.gathering.tasks import MaintainWildernessMinerStance, MinerEatFood, RepairBrokenGatherTool, RestockFishingGear, RestockGatherTool, StartupProvision
from bots.gathering.tasks import TannerfishSustain, TrimKnifeDelayLogs, UpgradeGatherTool, WaitStickyCombat
from bots.gathering.tick_manip import FLETCHABLE_LOG_NAMES, KNIFE_DELAY_MAKE_MATCH, SHORTBOW_NAMES, TICK_MANIP_KNIFE, extra_delay_logs_to_drop
from bots.gathering.tick_manip import is_fletchable_log_name, is_shortbow_name, mining_rate_for_pickaxe, profile_for_setting
from bots.gathering import tool_acquire_exec

LOCAL_BURN_HALF = 8
INVENTORY_TAB = 3


class BankTeleport:
    def __init__(self, name, level, runes):
        self.name = name
        self.level = level
        # (rune, per cast)
        self.runes = runes


BANK_TELEPORTS = {
    'Varrock': BankTeleport('Varrock', 25, [('Fire rune', 1), ('Air rune', 3), ('Law rune', 1)]),
    'Lumbridge': BankTeleport('Lumbridge', 31, [('Earth rune', 1), ('Air rune', 3), ('Law rune', 1)]),
    'Falador': BankTeleport('Falador', 37, [('Water rune', 1), ('Air rune', 3), ('Law rune', 1)]),
    'Camelot': BankTeleport('Camelot', 45, [('Air rune', 5), ('Law rune', 1)]),
    'Ardougne': BankTeleport('Ardougne', 51, [('Water rune', 2), ('Law rune', 2)]),
    'Watchtower': BankTeleport('Watchtower', 58, [('Earth rune', 2), ('Law rune', 2)]),
    'Trollheim': BankTeleport('Trollheim', 61, [('Fire rune', 2), ('Law rune', 2)]),
}
BANK_TELEPORT_NON_ZERO = list(BANK_TELEPORTS)
BANK_TELEPORT_OPTIONS = ['Off'] + BANK_TELEPORT_NON_ZERO
BANK_TELEPORT_OPTION_LABELS = {}
for _key in BANK_TELEPORT_NON_ZERO:
    BANK_TELEPORT_OPTION_LABELS[_key] = f'{BANK_TELEPORTS[_key].name} teleport'

GATHERING_SETTINGS = {
    'target_type': SettingDef('string', 'loc', "Target type ('loc' or 'npc')", help='loc = scenery (rocks/trees), npc = fishing spots'),
    'target': SettingDef('string', 'Rocks', 'Target name', help='in-game name, e.g. Rocks / Tree / Fishing spot'),
    'action': SettingDef('string', 'Mine', 'Action', help='right-click op, e.g. Mine / Chop down / Net'),
    'drop_match': SettingDef('string', 'ore', 'Drop items containing', help='when full, drop items whose name contains this (the gathered product)'),
    'leash_radius': SettingDef('number', 10, 'Leash radius (tiles)', 2, 64,
                               help='Camp/start membership radius (ReturnToAnchor). Only Location Use Closest / Use Start Position / Use Custom Position use this as-is (freeform and unverified chunk snaps). Named camps floor to 64. Fishing spots at named camps chase from the player inside the camp, not from this pin disk alone.'),
    'custom_location': SettingDef('tile', [3200, 3200, 0], 'Custom position (x,z)', show_if={'key': 'location', 'any_of': ['Use Custom Position']},
                                  help='when Location is Use Custom Position, gather around this tile instead of your start tile — like AutoFighter Use Custom Position'),
    'bank': SettingDef('boolean', True, 'Bank haul', group='Banking',
                       help='true = bank when full (uses Bank location below). false = power mode: drop the haul in a batch, keeping tools and food; bank for missing supplies. Legacy None location also power-mines.'),
    'bank_location': SettingDef('string', 'Auto', 'Bank location', options=['Auto', 'Nearest'] + [b['name'] for b in BANK_LOCATIONS], group='Banking',
                                show_if={'key': 'bank', 'any_of': ['true']},
                                help="Shown only when Bank haul is on. Auto = the camp's own bank stand for Use Closest / named camps; the nearest bank for Use Start Position / Use Custom Position. Nearest = always the nearest usable bank. A named choice forces that exact bank (quest/skill locked choices fall back to the nearest)."),
    'purge_pack_on_start': SettingDef('boolean', True, 'Bank junk on start', group='Banking',
                                      help='Deposit non-tool stacks at the camp bank before gathering so you can start with a junk pack. Skipped when Bank=false (power mode), Cooker (raw pack), and Supplier.'),
    'pack_junk': SettingDef('string', 'Bank', 'Event junk while gathering', options=['Bank', 'Drop', 'Off'], group='Banking',
                            help='When random-event loot (caskets, fruit, gems, …) steals pack slots under chop-then-burn or power mode: Bank at the camp (default), Drop, or Off. Bank=false has no camp bank — Bank falls back to Drop. (Future: shared API helper for other scripts.)'),
    'withdraw_coins': SettingDef('number', 0, 'Coins to withdraw at bank', 0, group='Banking',
                                 help='Top coins up to this many at each bank trip so the pack always has spending money (shops, cart rail). 0 = never withdraw. The coins are kept out of the deposit, so they carry from bank trip to bank trip.'),
    'bank_teleport': SettingDef('string', 'Off', 'Teleport runes', options=BANK_TELEPORT_OPTIONS, option_labels=BANK_TELEPORT_OPTION_LABELS, group='Banking',
                                help='Withdraw and keep the runes needed for one chosen spell teleport, so a manual/bot escape is always funded. Off = never withdraw. The rune stack is kept out of the deposit.'),
    'tele_casts': SettingDef('number', 1, 'Teleport casts to stock', 1, group='Banking', show_if={'key': 'bank_teleport', 'any_of': BANK_TELEPORT_NON_ZERO},
                             help='Shown when Teleport runes is not Off. How many casts worth of the chosen teleport runes to withdraw at once, but only when a single cast can no longer be made from the pack, so runes do not drain on partial top-ups.'),
}


def now_ms():
    return time.time() * 1000


def first_where(items, test):
    for i in items:
        if test(i):
            return i
    return None


def item_at_slot(slot):
    for i in inventory.items():
        if i.slot == slot:
            return i
    return None


def is_tiered_tool(reqs, name):
    key = name.lower()
    for r in reqs:
        if r.kind == 'tiered' and len([t for t in r.tiers if t.name.lower() == key]) > 0:
            return True
    return False


class GatheringBot(TaskBot):
    def on_start(self):
        self.loop_delay = 600
        self.started_at = time.time()
        self.status = 'starting'
        self.gathered = 0
        self.gems = 0
        self.cooked = 0
        self.burnt = 0
        self.banked = 0
        self.trips = 0
        self.fires = 0
        self.pair_op = ''
        self.location = None
        self.fish_method = None
        self.fishing = False
        self.chopping = False
        self.rock_ids = []
        self.product_keywords = []
        self.selected_rock_names = []
        self.tool_reqs = []
        self.miner_food = None
        self.miner_food_startup_pending = False
        self.miner_food_eaten = 0
        self.desert_camp_route = None
        self.desert_camp_startup_bank_pending = False
        self.desert_camp_bank_trip = False
        self.cook_mode = 'off'
        self.burnt_policy = 'drop'
        self.after_cook = 'stop'
        self.bank_raw_target = 56
        self.bank_raw_in_bank = 0
        self.cook_fish_filter = ''
        self.cooking_load = False
        self.in_cook_batch = False
        self.range_stand = None
        self.range_approach = None
        self.range_loc_tile = None
        self.range_name = 'Range'
        self.range_search_radius = 14
        self.cook_obstacles = ['door', 'gate']
        self.power_mode = False
        self.burn_mode = 'off'
        self.burn_plot = None
        self.burn_spot_name = ''
        self.burn_logs = 'Logs'
        self.burning_load = False
        self.burn_lane_left = 0
        self.burn_local = False
        self.last_roll_tick = -1
        self.farmer_cycle_start = -1
        self.tool_acquire = 'off'
        self.acquire_backoff_until_tick = 0
        # Why: burning never banks, and a cold start can wield bronze with steel banked.
        self.startup_tool_bank_sync_pending = False
        self.startup_provision_pending = False
        self.forgetful_bank = False
        self.bait_qty = 1000
        self.sweep_index = 0
        # Why: after a kite off a pack, the camp's return and gathering are held so it doesn't walk back onto them.
        self.combat_clear_until_tick = 0
        self.rejected = []
        self.cooldown_until = {}
        self.xp_start = {}
        self.tick_manip = profile_for_setting('mine', 'Off')
        yield from execution.delay_until(lambda: game.ingame() and game.tile() is not None, 0)
        s = self.settings
        raw = s.raw()
        self.target_type = s.str('target_type', 'loc').lower()
        self.target = s.str('target', 'Rocks')
        self.action = s.str('action', 'Mine')
        self.drop_match = s.str('drop_match', 'ore').lower()
        # The leash is settled once the location is.
        self.leash_radius = s.num('leash_radius', 10)
        self.configure_skill(raw)
        here = game.tile() or Tile(0, 0, 0)
        loc_setting = s.str('location', 'Auto')
        self.location_setting = loc_setting
        # Each skill has its own camps, so the miner and woodcutter never resolve a fishing pier.
        if self.fishing:
            self.location = resolve_fishing_location(loc_setting, here)
        elif self.mining():
            self.location = resolve_mining_location(loc_setting, here)
        elif self.woodcutting():
            self.location = resolve_woodcutting_location(loc_setting, here)
        # Why: a resolved camp takes the camp's own extent, never the freeform leash, which clipped its scan; freeform
        # takes the start's or custom tile's leash from the settings.
        if self.location is not None and self.location.spot is not None:
            self.anchor = resolve_run_anchor(here, self.location.spot)
            self.leash_radius = resolve_camp_radius(self.location.camp_radius, NAMED_CAMP_LEASH_FLOOR)
        elif is_custom_location(loc_setting):
            custom = s.tile('custom_location', here)
            self.anchor = Tile(custom.x, custom.z, custom.level)
            self.leash_radius = effective_gather_leash(self.leash_radius, loc_setting)
            self.log(f'location: Use Custom Position {self.anchor.x},{self.anchor.z} r{self.leash_radius}; bank nearest to custom')
        else:
            self.anchor = Tile(here.x, here.z, here.level)
            self.leash_radius = effective_gather_leash(self.leash_radius, loc_setting)
        desert_camp = self.location if self.location is not None and is_desert_camp_location(self.location.name) else None
        if desert_camp is not None:
            if not desert_camp.resources:
                raise RuntimeError(f'{desert_camp.name} has no configured ore types')
            unsupported = unsupported_camp_ores(self.selected_rock_names, desert_camp.resources)
            if len(unsupported) > 0:
                self.stop_with(f"{desert_camp.name} supports {', '.join(desert_camp.resources)}; selected {', '.join(unsupported)}")
                return
        # Why: after a teleport or a load the scene reads empty for a moment; blank isn't absent, so it waits.
        if self.fishing:
            yield from execution.delay_until_ticks(lambda: len(npcs.query().results()) > 0, 9)
        else:
            yield from execution.delay_until_ticks(lambda: len(locs.query().results()) > 0, 9)
        self.power_mode = not s.bool('bank', True)
        if loc_setting.strip().lower() == NONE_LEGACY.lower():
            self.log(f"location: legacy '{loc_setting}' — power mode (drop); set Bank=false from now on")
            self.power_mode = True
        self.bank_location = s.str('bank_location', 'Auto').strip() or 'Auto'
        forced = first_where(BANK_LOCATIONS, lambda b: b['name'].lower() == self.bank_location.lower())
        self.forced_bank = forced if forced is not None and not self.power_mode and bank_unlocked(forced) else None
        if forced is not None and self.forced_bank is None:
            why = 'disabled in power mode' if self.power_mode else 'locked (quest/skill) — using auto/nearest'
            self.log(f"bank: {forced['name']} {why}")
        self.configure_tick_manip(raw)
        self.configure_cooking()
        self.configure_burning(raw, here)
        self.tool_acquire = parse_tool_acquire_mode(s.str('tool_acquire', 'Off'))
        self.forgetful_bank = s.bool('forgetful_bank', False)
        self.withdraw_coins_target = max(0, math.floor(s.num('withdraw_coins', 0)))
        self.bank_teleport = s.str('bank_teleport', 'Off').strip()
        self.tele_casts = max(1, math.floor(s.num('tele_casts', 1)))
        if self.bank_teleport != 'Off' and self.bank_teleport not in BANK_TELEPORTS:
            self.log(f"bank: unknown teleport '{self.bank_teleport}' - treating as Off")
            self.bank_teleport = 'Off'
        if self.bank_teleport != 'Off':
            tele = BANK_TELEPORTS[self.bank_teleport]
            self.log(f'bank: keeping {tele.name} teleport runes (magic {tele.level}, {self.tele_casts} cast(s)); coins target {self.withdraw_coins_target}gp')
        elif self.withdraw_coins_target > 0:
            self.log(f'bank: coins target {self.withdraw_coins_target}gp')
        if desert_camp is not None and self.tool_acquire == 'on':
            self.stop_with(f'{desert_camp.name} does not support Tool acquire Buy/repair')
            return
        if self.tool_acquire == 'on':
            self.log('tools: acquire Buy/repair enabled (shops + broken repair + mith+ axe smith when bars ready)')
            if self.fishing and len([g for g in self.fish_method.gear if is_fishing_bait_piece(g)]) > 0:
                self.log(f'tools: bait/feather buy-up-to {self.bait_qty} when bank+inv are short')
            # One look in the bank at the start, so banked steel beats wielded bronze even burning, which never banks.
            if (self.mining() or self.woodcutting()) and len(self.tool_reqs) > 0:
                self.startup_tool_bank_sync_pending = True
                self.log('tools: will check bank once for a better axe/pick before gathering')
        if desert_camp is not None:
            if self.miner_food is None:
                self.stop_with(f'{desert_camp.name} requires Food to withdraw greater than 0')
                return
            if desert_camp_food_reserve_depleted(self.miner_food.target):
                self.stop_with(f'{desert_camp.name} requires Food to withdraw of at least 2')
                return
            destination = desert_camp_destination_for(desert_camp.name)
            self.desert_camp_route = DesertMiningCampRoute(self, destination)
            self.desert_camp_startup_bank_pending = True
            self.anchor = desert_camp.spot
            self.log(f'desert camp: dedicated gated route enabled; dest={destination}; initial provisioning bank required')
            sustain.set(self.desert_sustain)
        if self.forgetful_bank:
            self.log(f'bank: forgetful exits on (~1/{FORGETFUL_BANK_ODDS} chance after close)')
        self.gear_keep = self.rebuild_gear_keep()
        self.capture_xp_start()
        junk = s.str('pack_junk', 'Bank').strip().lower()
        self.pack_junk_policy = 'drop' if junk == 'drop' else ('off' if junk == 'off' else 'bank')
        if self.pack_junk_policy != 'off' and (self.burn_enabled() or self.power_mode):
            note = ' (Bank=false → drop if no bank)' if self.power_mode and self.pack_junk_policy == 'bank' else ''
            self.log(f'pack junk: {self.pack_junk_policy}{note}')
        # Junk is banked, so gathering can start with a pack full of trash; never in power mode.
        self.startup_provision_pending = not self.power_mode and not self.strict_desert_camp_banking() and self.bank_provision_needed()
        purge = s.bool('purge_pack_on_start', True)
        if purge and not self.startup_provision_pending and not self.power_mode and self.desert_camp_route is None:
            keep = list(self.gear_keep) + tool_keep_names(self.tool_reqs)
            if self.fish_method is not None:
                keep = keep + [g.name for g in self.fish_method.gear]
            stand, destination = self.script_bank_target()
            loc = self.location
            yield from purge_pack_at_bank(keep, stand=stand, destination=destination, prefer_nearby=self.forced_bank is None,
                                          booth_name=loc.booth_name if loc is not None and loc.booth_name else 'Bank booth',
                                          booth_op=loc.booth_op if loc is not None and loc.booth_op else 'Use-quickly',
                                          obstacles=(loc.obstacles if loc is not None else None) or ['door', 'gate'], log=self.log)
        self.configure_combat()
        self.log_start(loc_setting)
        self.on('inventory_changed', self.inventory_changed)
        self.add_tasks()

    def stop_with(self, message):
        self.status = f'{message} — stopped'
        self.log(message)
        self.request_finish(message)

    def configure_skill(self, raw):
        """The skill, from which entry script's settings these are."""
        s = self.settings
        if 'rocks' in raw:
            chosen = s.list('rocks')
            self.selected_rock_names = chosen
            rocks = chosen if len(chosen) > 0 else ROCK_OPTIONS
            self.target_type = 'loc'
            self.target = 'Rocks'
            self.action = 'Mine'
            self.rock_ids = resolve_rock_ids(rocks)
            self.product_keywords = [r.strip().lower() for r in rocks]
            self.tool_reqs = [pickaxe_req()]
            self.miner_food = miner_food_config(s.str('food', 'Lobster'), s.num('food_withdraw', 0))
            self.miner_food_startup_pending = self.miner_food is not None and self.miner_food_count() < self.miner_food.target
            if self.miner_food is not None:
                self.log(f'food: {self.miner_food.name} x{self.miner_food.target}; eat to heal; bank mode also eats for ore slots')
            # An empty choice falls back to every rock, which is logged, so a wrong ore is obvious.
            note = ' [defaulted — multi-select empty]' if len(chosen) == 0 else ''
            self.log(f"rocks: {', '.join(rocks) or '(none)'} → {len(self.rock_ids)} loc id(s){note}")
        elif 'fish_method' in raw:
            method = resolve_fish_method(s.str('fish_method', FISHING_METHOD_OPTIONS[0]))
            self.target_type = 'npc'
            self.target = 'Fishing spot'
            self.action = method.op
            self.pair_op = method.pair
            self.bait_qty = max(1, math.floor(s.num('bait_qty', 1000)))
            # The bait and feather targets apply only to the pieces that need them; tools stay at one.
            self.fish_method = Record({'name': method.name, 'op': method.op, 'pair': method.pair, 'gear': with_bait_target(method, self.bait_qty)})
            self.fishing = True
            self.product_keywords = ['raw']
            self.cook_mode = parse_cook_mode(s.str('cook_mode', 'Off'))
            self.burnt_policy = parse_burnt_policy(s.str('burnt_policy', 'Drop'))
            self.after_cook = parse_after_cook_cycle(s.str('after_cook_cycle', 'Stop'))
            self.bank_raw_target = parse_positive_int(raw.get('bank_raw_before_cook', 56), 56)
            self.cook_fish_filter = resolve_cook_fish_filter(s.str('cook_fish', 'All raw'), s.str('cook_fish_custom', ''))
        elif 'tree_name' in raw:
            # Every tree is Chop down.
            self.chopping = True
            self.target_type = 'loc'
            self.target = s.str('tree_name', 'Tree')
            self.action = 'Chop down'
            self.drop_match = 'log'
            self.tool_reqs = [axe_req()]
            self.product_keywords = ['log']
        else:
            self.product_keywords = [self.drop_match]
            act = self.action.lower()
            tgt = self.target.lower()
            if 'chop' in act or 'tree' in tgt or 'log' in self.drop_match:
                self.chopping = True
                self.target_type = 'loc'
                self.action = 'Chop down'
                self.tool_reqs = [axe_req()]
                self.product_keywords = [self.drop_match] if 'log' in self.drop_match else ['log']
            elif 'mine' in act or 'rock' in tgt:
                self.tool_reqs = [pickaxe_req()]

    def configure_tick_manip(self, raw):
        """Each skill's tick manipulation, off in power mode."""
        skill = 'fish' if self.fishing else ('mine' if self.mining() else ('wc' if self.woodcutting() else None))
        label = self.settings.str('tick_manip', 'Off') if skill is not None and 'tick_manip' in raw else 'Off'
        self.tick_manip = profile_for_setting(skill or 'mine', label)
        if self.tick_manip.method == 'off':
            return
        if self.power_mode:
            self.log(f"tick manip: '{self.tick_manip.label}' disabled under Bank=false (power)")
            self.tick_manip = profile_for_setting(skill or 'mine', 'Off')
            return
        p = self.tick_manip
        notes = [(p.may_die, ' (may die — retaliate / no flee)'), (p.use_knife_delay, ' [knife+log delay]'), (p.timed_reclick, ' [timed reclick]'),
                 (p.shortbow_rapid, ' [shortbow rapid]'), (p.farmer_willow_cycle, ' [farmer 6t]'), (p.cook_eat_interleave, ' [cook/eat interleave]')]
        self.log(f"tick manip: {p.label}{''.join([text for on, text in notes if on])}")

    def configure_cooking(self):
        if self.cook_mode != 'off' and self.power_mode:
            self.log('cook: disabled under Bank=false (power mode — drop only)')
            self.cook_mode = 'off'
        if self.cook_mode == 'off' or not self.fishing:
            return
        self.resolve_cook_scene()
        if self.range_stand is None:
            self.log('cook: no Range in scene/location — disabled until one is nearby')
            return
        batch = f'; bank {self.bank_raw_target} raw then cook; after={self.after_cook}' if self.cook_mode == 'bank-raw-then-cook' else ''
        self.log(f'cook: {self.cook_mode} @ {self.range_name} {self.range_stand}; burnt={self.burnt_policy}; cook {cook_filter_label(self.cook_fish_filter)}{batch}')

    def configure_burning(self, raw, here):
        if not self.chopping or 'burn_mode' not in raw:
            return
        self.burn_mode = parse_burn_mode(self.settings.str('burn_mode', 'Off'))
        self.burn_logs = logs_for_tree(self.target)
        if self.burn_mode != 'off' and self.power_mode:
            self.log('burn: disabled under Bank=false (power mode — drop only)')
            self.burn_mode = 'off'
        if self.burn_mode == 'off':
            return
        need_fm = firemaking_level_for_logs(self.burn_logs) or 1
        have_fm = skills.level('firemaking')
        if have_fm < need_fm:
            self.log(f'burn: {self.burn_logs} need FM {need_fm} (have {have_fm}) — disabled')
            self.burn_mode = 'off'
            return
        spot = self.settings.str('fire_spot', 'Auto')
        if spot.lower() == 'auto':
            # It burns near where it started, walking again or growing the plot as the tiles fill.
            half = int(max(LOCAL_BURN_HALF, min(self.leash_radius, 12)))
            self.burn_spot_name = 'Auto (start)'
            self.burn_plot = local_fire_plot(here, half)
            self.burn_local = True
            self.log(f'burn: chop-then-burn {self.burn_logs} near start {here.x},{here.z} r={half} (need tinderbox + FM {need_fm})')
        else:
            resolved = resolve_fire_spot(spot)
            if resolved is None:
                self.log(f"burn: unknown fire spot '{spot}' — disabled")
                self.burn_mode = 'off'
                return
            self.burn_spot_name, self.burn_plot = resolved
            self.burn_local = False
            self.log(f'burn: chop-then-burn {self.burn_logs} @ {self.burn_spot_name} (need tinderbox + FM {need_fm})')
        if len([r for r in self.tool_reqs if r.kind == 'exact' and r.name == TINDERBOX]) == 0:
            self.tool_reqs = self.tool_reqs + [tinderbox_req()]

    # Why: the retaliating tick methods fight with no flee and may die; a wilderness or desert camp's miner holds its
    # ground against the residents but flees a player; freeform is expert and may die, so combat is left alone; a
    # named camp or power mode fights nothing, walking its hits off.
    def configure_combat(self):
        if self.tick_manip.allow_combat:
            self.log('combat: Auto Retaliate ON (tick manip — may die)' if game.set_auto_retaliate(True) else 'combat: could not enable Auto Retaliate (controls missing?)')
        elif wilderness_miner_at(self.mining(), game.tile()):
            # MaintainWildernessMinerStance owns the toggle, waiting for its varp, after going in or a login too.
            self.log('combat: Wilderness Miner holds ground against NPCs; player attacks still flee')
        elif self.desert_camp_route is not None:
            self.log('combat: Desert Camp Miner holds ground against NPCs; player attacks still flee')
        elif not is_auto_location(self.location_setting):
            self.log('combat: Auto Retaliate off (gather — flee, do not fight)' if game.set_auto_retaliate(False) else 'combat: could not toggle Auto Retaliate (controls missing?)')
        else:
            self.log(f'combat: Location {self.location_setting} — mob flee off (may die)')

    def log_start(self, loc_setting):
        loc = self.location
        if loc is not None:
            auto = f' ({loc_setting})' if is_auto_location(loc_setting) else ''
            self.log(f'location: {loc.name}{auto}; bank {loc.bank_stand}')
            if not loc.verified:
                self.log(f'location: {loc.name} coords unverified — watch first bank run')
        elif not self.power_mode:
            self.log('location: no preset — nearest bank')
        if self.forced_bank is not None:
            self.log(f"bank: Bank location = {self.forced_bank['name']}")
        elif self.bank_location.lower() == 'nearest':
            self.log('bank: Bank location = Nearest')
        if self.power_mode:
            self.log('location: Bank=false (power): batch-drop ore, keep food for healing; restock when empty' if self.miner_food is not None
                     else 'location: Bank=false (power) — drop haul; bank only to fetch missing tools (nearest bank)')
        pair = f" + pair '{self.pair_op}'" if self.pair_op else ''
        self.log(f"gather: '{self.target}' ({self.action}{pair}) leash {self.leash_radius} @ {self.anchor}; {self.full_inventory_note()}")

    def add_tasks(self):
        gather_tools = (self.mining() or self.woodcutting() or len(self.tool_reqs) > 0) and not self.fishing
        # Why: the miner always carries the combat tasks, so a wilderness camp's policy can switch from holding against
        # the residents to fleeing a player; other gatherers flee only at a named camp.
        mob_flee = self.mining() or (not is_auto_location(self.location_setting) and not self.tick_manip.allow_combat)
        # Tannerfishing trains with the power: it cooks and eats on the pier and drops the haul.
        tanner_power = self.tick_manip.cook_eat_interleave
        cook_tasks = self.fishing and self.cook_mode != 'off' and self.range_stand is not None
        bank_catch = BankCatch(self)
        food_loop = self.miner_food is not None
        tasks = []
        tasks.append(ContinueDialog())
        if food_loop:
            tasks.append(MinerEatFood(self))
        if mob_flee:
            tasks = tasks + [WaitStickyCombat(self), FleeCombat(self)]
        tasks = tasks + [MaintainWildernessMinerStance(self), StartupProvision(self)]
        if self.desert_camp_route is not None:
            tasks.append(DesertMiningCampTravel(self))
        if self.tick_manip.shortbow_rapid:
            tasks.append(EnsureShortbowRapid(self))
        if self.tick_manip.cook_eat_interleave:
            tasks.append(TannerfishSustain(self))
        if self.tick_manip.use_knife_delay:
            tasks.append(TrimKnifeDelayLogs(self))
        if self.mining() or self.woodcutting():
            tasks.append(RepairBrokenGatherTool(self))
        if self.fishing:
            tasks.append(RestockFishingGear(self))
        if gather_tools:
            tasks = tasks + [EnsureGatherToolEquipped(self), RestockGatherTool(self), UpgradeGatherTool(self)]
        if cook_tasks:
            tasks = tasks + [FishCookDialog(self), FishCookLoad(self), FishBankCooked(self), FishWithdrawCookBatch(self)]
        tasks.append(ClearPackJunk(self))
        if self.burn_enabled():
            tasks = tasks + create_chop_burn_tasks(self)
        if food_loop:
            tasks.append(bank_catch)
        if self.power_mode or tanner_power:
            tasks.append(DropProduct(self))
        elif not food_loop:
            tasks.append(bank_catch)
        tasks.append(Gather(self))
        tasks.append(create_return_to_anchor_task(self, slack=4, long_range_tiles=24, suppress=lambda: (self.burn_enabled() and self.burning_load) or self.should_suppress_camp_reentry()))
        self.add(*tasks)

    def desert_sustain(self):
        """Use with yield from."""
        if not bank.is_open() and not event_signal.pending() and reader.modals().main == -1 and not chat_dialog.is_open() and not chat_dialog.can_continue() and self.should_eat_miner_food():
            yield from self.eat_miner_food()

    def inventory_changed(self, e):
        # Gains only, a new stack or a count up; the bank's withdraws don't count.
        if e.id == -1 or bank.is_open():
            return
        gained = max(1, e.count) if e.previous_id != e.id else max(0, e.count - e.previous_count)
        if gained <= 0:
            return
        name = e.name
        if self.cook_enabled() and is_burnt_fish_name(name):
            self.burnt += gained
            self.log(f'burnt: {name} (+{gained}, {self.burnt} this run)')
            return
        if self.cook_enabled() and is_cooked_fish_name(name):
            self.cooked += gained
            return
        if self.is_product(name):
            self.gathered += gained
            # The roll's tick, for the knife delay's and timed clicks' planners.
            if self.tick_manip.method != 'off':
                self.note_gather_roll()
        elif self.mining() and (name or '').lower().startswith('uncut '):
            self.gems += gained
            self.log(f'gem: {name} ({self.gems} this run)')

    def set_status(self, s):
        self.status = s

    def recovery_anchor(self):
        return self.anchor

    def note_combat_flee(self, hold_ticks=24):
        """Holds the camp's re-entry for hold_ticks after a kite."""
        self.combat_clear_until_tick = max(self.combat_clear_until_tick, game.tick() + max(0, hold_ticks))

    def should_suppress_camp_reentry(self):
        """Whether to stay off the camp after fleeing a pack, or while a hostile is still on it."""
        combat = self.combat_policy()
        # A player's kite holds even after its face target clears.
        if game.tick() < self.combat_clear_until_tick:
            return True
        # A wilderness camp's aggressive residents are expected, so they don't keep the miner off its rocks.
        if combat.mode == 'wilderness-miner-npc' or not combat.flee:
            return False
        return hostile_attacker_nearby(npcs.query().action('Attack').within(10).results(), 10)

    def rebuild_gear_keep(self):
        names = tool_keep_names(self.tool_reqs)
        if self.desert_camp_route is not None:
            names = names + desert_camp_keep_names(self.desert_camp_route.destination)
        if self.miner_food is not None:
            names = names + food_forms(self.miner_food.name)
        if self.fish_method is not None:
            names = names + gear_keep_names(self.fish_method)
        # The knife and one delay log, for the knife delay and the farmer's six ticks.
        if self.tick_manip.use_knife_delay or self.tick_manip.farmer_willow_cycle:
            names.append(TICK_MANIP_KNIFE)
            names = names + ([logs_for_tree(self.target)] if self.chopping else FLETCHABLE_LOG_NAMES)
        if self.tick_manip.shortbow_rapid:
            names = names + SHORTBOW_NAMES
        if self.tool_acquire == 'on':
            # Smithing's bars survive the restock's deposit too, or a camp's bank takes the bar before it's used.
            names = names + [COINS, BROKEN_PICKAXE, BROKEN_AXE, HAMMER] + list(AXE_BAR_FOR.values())
        if self.withdraw_coins_target > 0:
            names.append(COINS)
        if self.bank_teleport != 'Off':
            names = names + [rune for rune, _ in BANK_TELEPORTS[self.bank_teleport].runes]
        out = []
        for n in names:
            if n not in out:
                out.append(n)
        return out

    # Provisions: coins and the teleport's runes.

    def teleport_runes(self):
        tele = BANK_TELEPORTS.get(self.bank_teleport)
        return tele.runes if tele is not None else []

    def teleport_one_cast_ready(self):
        """Whether the pack has one cast; runes restock only when it hasn't, never topping up."""
        if self.bank_teleport == 'Off':
            return True
        return len([1 for rune, count in self.teleport_runes() if inventory.count(rune) < count]) == 0

    def coins_provision_needed(self):
        return self.withdraw_coins_target > 0 and inventory.count(COINS) < self.withdraw_coins_target

    def bank_provision_needed(self):
        return self.coins_provision_needed() or (self.bank_teleport != 'Off' and not self.teleport_one_cast_ready())

    def run_startup_provision(self, log=None):
        """Use with yield from."""
        log = log or (lambda m: self.log(f'  {m}'))
        opened = yield from banking.open(log=log)
        if opened:
            opened = yield from self.wait_bank_ready(log)
        if not opened:
            log('bank: could not load startup bank - will retry')
            return
        yield from bank.deposit_all_matching(self.restock_deposit_matcher())
        for _ in range(STARTUP_PROVISION_RETRIES):
            if not self.bank_provision_needed():
                break
            yield from self.withdraw_trip_provisions_at_bank(log)
        if bank.is_open():
            closed = yield from self.close_script_bank(log, False)
            if not closed:
                log('bank: startup provision left the bank open - will retry')
                return
        if self.bank_provision_needed():
            yield from self.give_up_startup_provision(log)
        else:
            self.startup_provision_pending = False

    def give_up_startup_provision(self, log=None):
        """The last give-up, once the retries are spent. Use with yield from."""
        log = log or (lambda m: self.log(f'  {m}'))
        self.startup_provision_pending = False
        if bank.is_open():
            self.stop_strict_bank_failure('startup provisioning could not close the bank')
            return
        if self.coins_provision_needed():
            need = self.withdraw_coins_target - inventory.count(COINS)
            self.stop_missing_gear(f'could not withdraw {self.withdraw_coins_target}gp of startup coins after {STARTUP_PROVISION_RETRIES} tries', [f'{need} gp'])
            return
        log('bank: giving up on startup teleport runes - continuing without')
        if False:
            yield

    def withdraw_trip_provisions_at_bank(self, log=None):
        """Coins and the teleport's runes, in the bank already open: the runes only when one cast can't be made, the
        coins whenever they're short. Use with yield from."""
        log = log or (lambda m: self.log(f'  {m}'))
        if not bank.is_open():
            return
        ready = yield from bank.wait_ready(4000)
        if not ready:
            return
        if self.withdraw_coins_target > 0:
            have = inventory.count(COINS)
            if have < self.withdraw_coins_target:
                ok = yield from self.withdraw_coins_for(self.withdraw_coins_target, log)
                log(f'bank: coins {have} → {inventory.count(COINS)}gp' if ok else f'bank: coins under {self.withdraw_coins_target}gp but bank has none')
        if self.bank_teleport != 'Off' and not self.teleport_one_cast_ready():
            for rune, count in self.teleport_runes():
                target = count * self.tele_casts
                if inventory.count(rune) < target:
                    got = yield from self.withdraw_to(rune, target)
                    log(f'bank: withdrew {got} {rune} ({inventory.count(rune)}/{target}) for {self.bank_teleport} teleport')

    def withdraw_to(self, name, target):
        """Withdraws up to target held. Use with yield from."""
        start = inventory.count(name)
        for _ in range(40):
            if inventory.count(name) >= target or (inventory.is_full() and inventory.count(name) == 0) or not bank.is_open():
                break
            before = inventory.count(name)
            need = target - before
            if need > 10:
                took = yield from bank.withdraw_x(name, need)
                if took:
                    if inventory.count(name) > before:
                        continue
                    break
            if not bank.is_open():
                break
            bank.withdraw(name, 'Withdraw-10' if need >= 10 else ('Withdraw-5' if need >= 5 else 'Withdraw-1'))
            landed = yield from execution.delay_until(lambda: inventory.count(name) > before, 2500)
            if not landed:
                break
        return inventory.count(name) - start

    # Tools.

    def skill_level(self, skill):
        return skills.level(skill)

    def held_count(self, name):
        want = name.lower()
        return sum([item.count for item in equipment.items() if (item.name or '').lower() == want]) + inventory.count(name)

    def tool_acquire_enabled(self):
        return self.tool_acquire == 'on'

    def acquire_world(self):
        return AcquireWorld(self.skill_level, self.held_count, inventory.count, lambda name: bank.count(name) if bank.is_open() or bank.loaded() else 0, equipment.contains)

    def acquire_world_with_bank(self):
        """Bank counts need an open, loaded bank."""
        return AcquireWorld(self.skill_level, self.held_count, inventory.count, bank.count, equipment.contains)

    def has_broken_gather_tool(self):
        return self.held_count(BROKEN_PICKAXE) > 0 or self.held_count(BROKEN_AXE) > 0

    # Why: a longer cooldown already set is never shortened.
    def mark_acquire_backoff(self, ticks=25):
        self.acquire_backoff_until_tick = max(self.acquire_backoff_until_tick, game.tick() + max(0, ticks))

    def acquire_ready(self):
        return self.tool_acquire == 'on' and game.tick() >= self.acquire_backoff_until_tick

    # The ToolAcquireExec host.

    def gear_keep_names_list(self):
        return self.gear_keep

    def attack_level(self):
        return skills.level('attack')

    def mining_level(self):
        return skills.level('mining')

    def drive_dialog(self, prefer, log):
        """Use with yield from."""
        done = yield from drive_dialog(list(prefer), log)
        return done

    def execute_tool_acquire_plan(self, plan, log=None, bank_prepared=False):
        """Use with yield from."""
        done = yield from tool_acquire_exec.execute_tool_acquire_plan(self, plan, log or (lambda m: self.log(f'  {m}')), bank_prepared)
        return done

    def execute_fishing_gear_shop_cart(self, plans, log=None, bank_prepared=False):
        """Buys several pieces of gear in one visit: the fly rod and feathers at Gerrant mustn't bank between. Use with
        yield from."""
        done = yield from tool_acquire_exec.execute_fishing_gear_shop_cart(self, plans, log or (lambda m: self.log(f'  {m}')), bank_prepared)
        return done

    def bank_pace(self, log=None):
        """Use with yield from."""
        yield from bank_pace(log)

    def wait_bank_ready(self, log=None):
        """Use with yield from."""
        log = log or (lambda m: self.log(f'  {m}'))
        ready = yield from wait_bank_ready(log)
        if not ready or self.desert_camp_route is None:
            return ready
        yield from execution.delay_until(lambda: not bank.is_open() or bank.snapshot_ready(), 4000)
        if bank.snapshot_ready():
            return True
        log('bank: Shantay item snapshot did not arrive — refusing to read stock')
        return False

    def shantay_backpack_before_open(self, log=None):
        """The normal backpack's snapshot before Shantay's bank opens, or None. Use with yield from."""
        log = log or (lambda m: self.log(f'  {m}'))
        if bank.is_open():
            closed = yield from self.close_script_bank(log, False)
            if not closed:
                log('bank: could not close Shantay bank before capturing the backpack')
                return None
        yield from execution.delay_until(lambda: bank.is_open() or bank.normal_backpack_snapshot() is not None, 4000)
        snapshot = bank.normal_backpack_snapshot()
        if snapshot is None:
            log('bank: normal 28-slot backpack did not become readable before opening Shantay bank')
        return snapshot

    def withdraw_coins_for(self, need, log=None):
        """Use with yield from."""
        done = yield from withdraw_coins(need, inventory.count(COINS), bank.count(COINS) if bank.is_open() else 0, COINS, log or (lambda m: self.log(f'  {m}')))
        return done

    def tool_keep(self, extra_keep):
        keep = [n.lower() for n in best_held_tool_names(self.tool_reqs, self.skill_level, self.held_count)] + [n.lower() for n in extra_keep] + [COINS.lower()]
        return keep + [r.name.lower() for r in self.tool_reqs if r.kind == 'exact']

    def deposit_surplus_gather_tools(self, log=None, extra_keep=None):
        """Deposits worse tiers of tool, keeping the best held of each, coins and extras such as the hammer, a bar or a
        broken tool. Use with yield from."""
        log = log or (lambda m: self.log(f'  {m}'))
        if not bank.is_open() or len(self.tool_reqs) == 0:
            return
        keep = self.tool_keep(extra_keep or [])
        surplus = [n for n in surplus_held_tool_names(self.tool_reqs, self.skill_level, self.held_count) if inventory.first(n) is not None or equipment.contains(n)]
        if len(surplus) == 0:
            # A tier in the pack that isn't kept, after wielding moved it there.
            surplus = []
            for i in inventory.items():
                n = i.name or ''
                if n and is_tiered_tool(self.tool_reqs, n) and n.lower() not in keep and n not in surplus:
                    surplus.append(n)
            if len(surplus) == 0:
                return
        log(f"bank: depositing surplus tools ({', '.join(surplus)})")
        yield from self.bank_pace()
        # Only known tiers of tool: never loot here.
        yield from bank.deposit_all_matching(lambda name, *_args: bool(name) and name.lower() not in keep and is_tiered_tool(self.tool_reqs, name))
        yield from execution.delay_until_ticks(lambda: bank.loaded() or not bank.is_open(), 5)
        yield from self.bank_pace()

    # Why: wielding a tool can push the old axe or pick, a weapon or a shield into the pack, which is deposited so
    # gear isn't lost mid-run; prepare_worn_surplus_for_deposit in the bank already open avoids opening it again.
    def bank_displaced_after_equip(self, displaced, log=None):
        """Opens the bank again if needed and deposits gear a wield pushed out. Use with yield from."""
        log = log or (lambda m: self.log(f'  {m}'))
        names = []
        for n in [d.strip() for d in displaced] + surplus_held_tool_names(self.tool_reqs, self.skill_level, inventory.count):
            if len(n) > 0 and n not in names and inventory.first(n) is not None:
                names.append(n)
        if len(names) == 0:
            return
        if not bank.is_open():
            log(f"bank: re-open to store displaced ({', '.join(names)})")
            opened = yield from self.open_script_bank(log)
            if not opened:
                log(f"bank: could not re-open — leaving {', '.join(names)} in pack")
                return
            ready = yield from self.wait_bank_ready(log)
            if not ready:
                return
        else:
            yield from self.bank_pace()
        want = [n.lower() for n in names]
        log(f"bank: depositing displaced ({', '.join(names)})")
        yield from bank.deposit_all_matching(lambda name, *_args: (name or '').lower() in want)
        yield from execution.delay_until_ticks(lambda: bank.loaded() or not bank.is_open(), 5)
        yield from self.bank_pace()

    # Why: unequipping doesn't need the bank shut, so the surplus is deposited in the same visit.
    def prepare_worn_surplus_for_deposit(self, log=None, extra_keep=None):
        """Takes worse tiers of tool off into the pack while the bank's open. Use with yield from."""
        log = log or (lambda m: self.log(f'  {m}'))
        if len(self.tool_reqs) == 0:
            return
        keep = self.tool_keep(extra_keep or [])
        for item in equipment.items():
            name = item.name or ''
            if not name or name.lower() in keep or not is_tiered_tool(self.tool_reqs, name):
                continue
            if inventory.is_full():
                log(f'bank: pack full — cannot unequip surplus {name}')
                break
            log(f'bank: unequip surplus {name} for deposit')
            yield from equipment.unequip(name)
            yield from execution.delay_until_ticks(lambda: not equipment.contains(name) or inventory.first(name) is not None, 5)
            yield from self.bank_pace()

    def close_script_bank(self, log=None, allow_forgetful=True):
        """Closes the bank. With forgetful banking, about one time in FORGETFUL_BANK_ODDS it steps out and opens it
        again for a moment, as if it forgot something. Use with yield from."""
        log = log or (lambda m: self.log(f'  {m}'))
        if not bank.is_open():
            return True
        yield from self.bank_pace()
        closed = yield from bank.close()
        if not closed:
            log('bank: close did not dismiss the bank modal')
            return False
        yield from execution.delay_ticks(1)
        if not allow_forgetful or not self.forgetful_bank or math.floor(random.random() * FORGETFUL_BANK_ODDS) != 0:
            return True
        here = game.tile()
        if here is None:
            return True
        log(f'bank: forgot something — stepping out then back (1/{FORGETFUL_BANK_ODDS})')
        stand, destination = self.script_bank_target()
        if stand is None and destination is not None:
            t = destination['tile']
            stand = Tile(t['x'], t['z'], t['level'])
        stand = stand or here
        # A few tiles off the booth, not a trip home.
        away = Tile(here.x + (-3 if random.random() < 0.5 else 3), here.z + (-2 if random.random() < 0.5 else 2), here.level)
        yield from traversal.walk_resilient(away, radius=1, timeout_ms=12000, log=log)
        yield from execution.delay_ticks(1)
        opened = yield from self.open_script_bank(log)
        if opened:
            yield from self.wait_bank_ready(log)
            # A glance only, the double take.
            yield from self.bank_pace()
            if bank.is_open():
                closed = yield from bank.close()
                if not closed:
                    log('bank: forgetful close did not dismiss the bank modal')
                    return False
        # Back toward the booth, so a walk home doesn't start sideways.
        yield from traversal.walk_resilient(stand, radius=3, timeout_ms=12000, log=log)
        return True

    def bank_obstacles(self):
        if self.cook_enabled():
            return self.cook_obstacles
        return (self.location.obstacles if self.location is not None else None) or []

    def open_bank_at(self, stand, log=None):
        """Use with yield from."""
        loc = self.location
        opened = yield from banking.open(stand=stand, booth_name=loc.booth_name if loc is not None and loc.booth_name else 'Bank booth',
                                         booth_op=loc.booth_op if loc is not None and loc.booth_op else 'Use-quickly', obstacles=self.bank_obstacles(),
                                         log=log or (lambda m: self.log(f'  {m}')))
        return opened

    def script_bank_target(self):
        """(stand, destination) of the bank the settings point at: the camp's stand, the nearest, or one forced."""
        if self.forced_bank is not None:
            t = self.forced_bank['tile']
            return (Tile(t['x'], t['z'], t['level']), self.forced_bank)
        if self.bank_location.lower() == 'nearest' or self.location is None or self.location.bank_stand is None:
            return (None, None)
        return (self.location.bank_stand, None)

    def open_script_bank(self, log=None):
        """Use with yield from."""
        loc = self.location
        stand, destination = self.script_bank_target()
        opened = yield from banking.open(stand=stand, booth_name=loc.booth_name if loc is not None and loc.booth_name else 'Bank booth',
                                         booth_op=loc.booth_op if loc is not None and loc.booth_op else 'Use-quickly', obstacles=self.bank_obstacles(),
                                         destination=destination, prefer_nearby=self.forced_bank is None, log=log or (lambda m: self.log(f'  {m}')))
        return opened

    # Cooking.

    def resolve_cook_scene(self):
        loc = self.location if self.fishing else None
        # Banking raw then cooking uses the bank's surface; cooking then banking the pier's, unless the player is much
        # nearer a separate oven by the bank.
        role = 'bank' if self.cook_mode == 'bank-raw-then-cook' else 'pier'
        if loc is not None and role == 'pier':
            pier = cook_surface_for_fish_camp(loc.name, 'pier')
            by_bank = cook_surface_for_fish_camp(loc.name, 'bank')
            here = game.tile()
            if here is not None and pier is not None and by_bank is not None and (pier.stand.x != by_bank.stand.x or pier.stand.z != by_bank.stand.z):
                if max(abs(here.x - by_bank.stand.x), abs(here.z - by_bank.stand.z)) + 12 < max(abs(here.x - pier.stand.x), abs(here.z - pier.stand.z)):
                    role = 'bank'
        if loc is not None:
            origin = loc.bank_stand if role == 'bank' and loc.bank_stand is not None else (loc.spot or self.anchor)
            curated = resolve_fish_camp_cook_surface(loc.name, origin, 64, role)
            if curated is not None:
                self.range_stand = curated.stand
                self.range_approach = curated.approach
                self.range_loc_tile = curated.loc
                self.range_name = curated.loc_name
                self.cook_obstacles = loc.obstacles or ['door', 'gate']
                approach = f' approach={curated.approach}' if curated.approach is not None else ''
                self.log(f'cook: {role} surface {curated.label or curated.loc_name} stand={curated.stand}{approach}')
                return
        self.range_approach = None
        self.range_loc_tile = None
        if loc is not None and loc.range_stand is not None:
            self.range_stand = loc.range_stand
            self.range_name = loc.range_name or 'Range'
            self.cook_obstacles = loc.obstacles or ['door', 'gate']
            return
        oven = locs.query().name('Range', 'Cooking range', 'Fire', 'Fireplace').nearest()
        if oven is not None:
            self.range_stand = oven.tile()
            self.range_loc_tile = oven.tile()
            self.range_name = oven.name or 'Range'
            self.cook_obstacles = (self.location.obstacles if self.location is not None else None) or ['door', 'gate']
            self.log(f'cook: found {self.range_name} @ {self.range_stand}')

    def cook_enabled(self):
        return self.fishing and self.cook_mode != 'off' and self.range_stand is not None

    def refresh_bank_raw_total(self):
        if self.cook_mode != 'bank-raw-then-cook':
            return self.bank_raw_in_bank
        total = count_raw_in_bank(bank.items(), self.cook_fish_filter)
        self.bank_raw_in_bank = total
        if not self.in_cook_batch and should_start_bank_raw_cook_batch(self.cook_mode, total, self.bank_raw_target):
            self.in_cook_batch = True
            self.log(f'cook: bank holds {total} {cook_filter_label(self.cook_fish_filter)} (target {self.bank_raw_target}) — starting batch')
        return total

    def finish_cook_cycle(self):
        self.cooking_load = False
        outcome = cook_batch_after_load(self.bank_raw_in_bank, self.after_cook)
        if outcome == 'drain-more':
            self.in_cook_batch = True
            self.log(f'cook: load done; bank still has {self.bank_raw_in_bank} {cook_filter_label(self.cook_fish_filter)} — withdraw next')
            self.status = 'cook: withdrawing next load'
            return
        self.in_cook_batch = False
        if outcome == 'stop':
            self.status = 'cook: batch complete — stopped'
            self.request_finish(f'cook: batch drained (bank raw {self.bank_raw_in_bank}/{self.bank_raw_target})')
            return
        self.log(f'cook: batch drained (bank raw {self.bank_raw_in_bank}/{self.bank_raw_target}) — fish for next +{self.bank_raw_target}')
        self.status = 'cook: batch done — fishing'

    def raw_fish_count(self):
        return len([i for i in inventory.items() if is_raw_fish_name(i.name)])

    def cookable_raw_count(self):
        return len([i for i in inventory.items() if raw_matches_cook_filter(i.name, self.cook_fish_filter)])

    def cooked_fish_count(self):
        return len([i for i in inventory.items() if is_cooked_fish_name(i.name)])

    def burnt_fish_count(self):
        return len([i for i in inventory.items() if is_burnt_fish_name(i.name)])

    def last_raw_fish(self):
        items = inventory.items()
        idx = last_matching_index(items, lambda n: raw_matches_cook_filter(n, self.cook_fish_filter))
        return items[idx] if idx >= 0 else None

    def is_cookable_raw(self, name):
        return raw_matches_cook_filter(name, self.cook_fish_filter)

    def kept(self, name):
        return len(self.gear_keep) > 0 and not deposit_all_except(self.gear_keep)(name)

    def should_deposit_cook_result(self, name):
        if self.kept(name):
            return False
        if is_raw_fish_name(name):
            # The filter's leftovers, such as shrimps while cooking only lobster.
            return not raw_matches_cook_filter(name, self.cook_fish_filter)
        if is_burnt_fish_name(name):
            return self.burnt_policy == 'bank'
        return is_cooked_fish_name(name)

    def bank_catch_blocked_by_cook(self):
        if not self.cook_enabled():
            return False
        if self.cooking_load or self.in_cook_batch:
            return True
        return self.cook_mode == 'cook-then-bank' and should_cook_then_bank(self.cook_mode, inventory.is_full(), self.cookable_raw_count())

    # Burning.

    def burn_enabled(self):
        return self.chopping and self.burn_mode == 'chop-then-burn' and self.burn_plot is not None

    def begin_burning_load(self):
        self.burning_load = True

    def end_burning_load(self):
        self.burning_load = False
        self.burn_lane_left = 0

    def burn_plot_or_none(self):
        return self.burn_plot

    def is_local_burn(self):
        return self.burn_local

    def burn_log_name(self):
        return self.burn_logs

    def has_tinderbox(self):
        return self.held_count(TINDERBOX) > 0

    def log_count(self):
        return inventory.count(self.burn_logs)

    def bank_catch_blocked_by_burn(self):
        if not self.burn_enabled():
            return False
        return self.burning_load or should_burn_full_load(self.burn_mode, inventory.is_full(), self.log_count(), self.has_tinderbox())

    def try_expand_burn_plot(self):
        if not self.burn_local or self.burn_plot is None:
            return False
        grown = expand_local_fire_plot(self.burn_plot, 4, 24)
        if grown is None:
            return False
        self.burn_plot = grown
        self.log(f'burn: expanded local plot to r={(grown.x1 - grown.x0) // 2}')
        return True

    # What's gathered.

    def is_npc(self):
        return self.target_type == 'npc'

    def mining(self):
        return len(self.rock_ids) > 0

    def woodcutting(self):
        return self.chopping

    def is_product(self, name):
        n = (name or '').lower()
        if self.mining():
            return len([ore for ore in self.product_keywords if n == (ore if ore == 'clay' or ore == 'coal' else f'{ore} ore')]) > 0
        return len([k for k in self.product_keywords if k in n]) > 0

    def matches_rock(self, id):
        return len(self.rock_ids) == 0 or id in self.rock_ids

    def matches_spot(self, actions):
        return spot_matches_method(actions, self.fish_method)

    def product_label(self):
        return '/'.join(self.product_keywords)

    def products(self):
        return [i for i in inventory.items() if self.is_product(i.name)]

    def avoids_spot(self, tile):
        return spot_avoided(tile, (self.location.avoid_spots if self.location is not None else None) or [])

    def next_sweep_stop(self):
        sweep = (self.location.sweep if self.location is not None else None) or []
        step = sweep_stop_for(sweep, self.sweep_index, game.tile())
        self.sweep_index = step.index
        return step.stop

    def fishing_vendor_near(self):
        """The tile that picks Harry or Gerrant: the camp's spot or anchor before where the player stands."""
        return (self.location.spot if self.location is not None else None) or self.anchor or game.tile()

    def needs_fishing_bait_top_up(self):
        """Whether a bait or feather stack is below its target and the bank, or the shop with acquisition on, can top
        it up."""
        method = self.fish_method
        if method is None:
            return False
        for g in method.gear:
            if not is_fishing_bait_piece(g):
                continue
            held = inventory.count(g.name)
            if held >= g.restock:
                continue
            if bank.is_open() or bank.loaded():
                if bank.count(g.name) > 0 or (self.tool_acquire == 'on' and held + bank.count(g.name) < g.restock):
                    return True
            elif held < g.min or self.tool_acquire == 'on':
                return True
        return False

    def top_up_fishing_bait_at_bank(self, log=None):
        """Bait and feathers toward the target from the bank already open, the shop selling the rest with acquisition
        on. Use with yield from."""
        log = log or (lambda m: self.log(f'  {m}'))
        method = self.fish_method
        if method is None or not bank.is_open():
            return False
        yield from execution.delay_until_ticks(lambda: bank.loaded() or not bank.is_open(), 5)
        if not bank.is_open():
            return False
        bait = [g.name.lower() for g in method.gear if is_fishing_bait_piece(g)]
        for name, qty in fishing_restock_plan(method, inventory.count, bank.count):
            if name.lower() not in bait:
                continue
            found = first_where(bank.items(), lambda i: (i.name or '').lower() == name.lower())
            if found is None:
                continue
            before = inventory.count(name)
            log(f'bait: withdraw {qty}× {name}')
            if qty == 1:
                bank.withdraw(name, withdraw_op(found.actions(), '1') or 'Withdraw-1')
            else:
                yield from bank.withdraw_x(name, qty)
            yield from execution.delay_until_ticks(lambda: inventory.count(name) > before or bank.count(name) == 0, 7)
            yield from self.bank_pace()
        # The shop for what's still short, one vendor's cart in one visit.
        if self.tool_acquire_enabled() and self.acquire_ready():
            cart = [p for p in fishing_gear_shop_cart(method, self.acquire_world_with_bank(), self.fishing_vendor_near(), self.bait_qty) if p.name.lower() in bait]
            if len(cart) > 0:
                funded = inventory.count(COINS) >= buy_plans_cost(cart)
                if bank.is_open():
                    yield from self.close_script_bank(log, False)
                ok = yield from self.execute_fishing_gear_shop_cart(cart, log, funded)
                if not ok:
                    self.mark_acquire_backoff(35)
                return ok
        return True

    # Gear.

    def has_gear(self):
        if self.fish_method is not None:
            return has_fishing_gear(self.fish_method, inventory.count)
        if len(self.tool_reqs) > 0:
            return has_all_tools(self.tool_reqs, self.skill_level, self.held_count)
        return len([g for g in self.gear_keep if self.held_count(g) == 0]) == 0

    def gear_label(self):
        if self.fish_method is not None:
            return gear_label(self.fish_method)
        if len(self.tool_reqs) > 0:
            return tool_kit_label(self.tool_reqs, self.skill_level, self.held_count)
        return ' + '.join(self.gear_keep) or 'gear'

    def missing_gear_names(self):
        if self.fish_method is not None:
            return [g.name for g in missing_fishing_gear(self.fish_method, inventory.count)]
        if len(self.tool_reqs) > 0:
            return missing_tool_labels(self.tool_reqs, self.skill_level, self.held_count)
        return [g for g in self.gear_keep if self.held_count(g) == 0]

    def acquire_materials_held(self, plan):
        """Whether the pack holds what the plan needs already, so the restock skips a second bank."""
        if plan.kind == 'buy':
            return inventory.count(COINS) >= plan.cost
        if plan.kind == 'smith':
            return inventory.count(HAMMER) >= 1 and inventory.count(plan.bar) >= 1
        return self.held_count(plan.broken_name) > 0

    def gather_tool_restock_plan(self):
        return tool_restock_plan(self.tool_reqs, self.skill_level, self.held_count, bank.count)

    def tools_to_equip(self):
        """The axes and pickaxes held but not worn."""
        if len(self.tool_reqs) == 0:
            return []
        return tools_needing_equip(self.tool_reqs, self.skill_level, self.held_count, equipment.contains)

    # Why: never with the bank open, where the pack's options are Deposit. bank_displaced, on by default, opens the
    # bank again to deposit gear a wield pushed out; off when the surplus went in the same visit.
    def equip_tools(self, names, log=None, bank_displaced=True):
        """Shuts the bank, then wields each tool: False when any didn't. Use with yield from."""
        log = log or (lambda m: self.log(f'  {m}'))
        attack = skills.level('attack')
        unique = []
        for n in names:
            if not n or n in unique:
                continue
            # A tool it can't wield still works from the pack for mining and woodcutting.
            if not can_wield_tool(n, attack):
                log(f'equip: skip {n} (need Attack {tool_attack_level(n)}, have {attack})')
                continue
            unique.append(n)
        if len(unique) == 0:
            return True
        bank_displaced = bank_displaced and self.desert_camp_route is None
        if bank.is_open():
            closed = yield from bank.close()
            if not closed:
                log('equip: could not close bank')
                return False
            yield from execution.delay_ticks(1)
        # Make X, a shop or a dialogue can leave the main window open, and wielding fails until it clears.
        if chat_dialog.is_main_make_panel() or chat_dialog.is_open():
            yield from execution.delay_until_ticks(lambda: not chat_dialog.is_main_make_panel() and not chat_dialog.is_open(), 5)
            yield from execution.delay_ticks(1)
        # The backpack tab, so its options are live after an anvil's or shop's window.
        yield from game.open_side_tab(INVENTORY_TAB)
        yield from execution.delay_ticks(1)
        # What was worn before, since an axe or pick can push the old weapon into the pack.
        worn_before = [(i.name or '').lower() for i in equipment.items() if i.name]
        ok = True
        for name in unique:
            if equipment.contains(name):
                continue
            if inventory.first(name) is None:
                log(f'equip: {name} not in inventory')
                ok = False
                continue
            equipped = yield from equipment.equip(name)
            # One more try at once: the first click often races a smith's or shop's close.
            if not equipped and inventory.first(name) is not None and not equipment.contains(name):
                yield from execution.delay_ticks(1)
                yield from game.open_side_tab(INVENTORY_TAB)
                equipped = yield from equipment.equip(name)
            if equipped:
                log(f'equipped {name}')
            else:
                item = inventory.first(name)
                log(f"equip failed: {name} (ops=[{','.join(item.actions()) if item is not None else 'missing'}])")
                ok = False
            yield from execution.delay_ticks(1)
        if not bank_displaced:
            return ok
        keep_worn = [n.lower() for n in unique]
        displaced = [i.name for i in inventory.items() if i.name and i.name.lower() not in keep_worn and i.name.lower() in worn_before]
        displaced = displaced + surplus_held_tool_names(self.tool_reqs, self.skill_level, inventory.count)
        if len(displaced) > 0:
            yield from self.bank_displaced_after_equip(displaced, log)
            if bank.is_open():
                yield from self.close_script_bank(log, False)
        return ok

    def restock_deposit_matcher(self):
        """Deposits all but the gear, in banking and power mode alike."""
        return deposit_all_except(self.gear_keep)

    def stop_missing_gear(self, reason, missing):
        need = ' + '.join(missing) or self.gear_label()
        self.status = f'restock: stop — {need}'
        self.request_finish(f'restock: {reason} — need {need}')

    def stop_strict_bank_failure(self, reason):
        self.stop_with(reason)

    def stop(self, reason):
        """The desert camp route's stop."""
        self.request_finish(reason)

    def startup_tool_bank_sync_needed(self):
        return self.startup_tool_bank_sync_pending and self.tool_acquire == 'on'

    # Why: Draynor's bank is within the willows' slack, so being off the spot alone could pull a cold start away for an
    # upgrade.
    def near_script_bank(self, radius=8):
        """Whether it's at the script's bank, or the bank's open."""
        if bank.is_open():
            return True
        here = game.tile()
        if here is None:
            return False
        stand, destination = self.script_bank_target()
        if stand is None:
            known = destination or nearest_bank(here)
            if known is None:
                return False
            t = known['tile']
            stand = Tile(t['x'], t['z'], t['level'])
        # Tight: Draynor's willows are about 12 from the stand, which mustn't count as the bank.
        return here.distance_to(stand) <= radius

    # Why: the worse tier is deposited in the same visit with nothing wielded here, so one upgrade never opens and
    # shuts the bank three times; the bank must be open and loaded, and the names returned are wielded once it's shut.
    def withdraw_better_gather_tools_from_bank(self, log=None):
        """Withdraws better tiers banked, steel while bronze is held: (withdrew, to_equip). Use with yield from."""
        log = log or (lambda m: self.log(f'  {m}'))
        if not bank.is_open() or len(self.tool_reqs) == 0:
            return (False, [])
        upgrades = [step for step in self.gather_tool_restock_plan() if is_tiered_tool(self.tool_reqs, step.name)]
        if len(upgrades) == 0:
            return (False, [])
        for step in upgrades:
            before = self.held_count(step.name)
            found = first_where(bank.items(), lambda i: (i.name or '').lower() == step.name.lower())
            if found is None:
                continue
            log(f'bank: withdraw better {step.name}')
            bank.withdraw(step.name, withdraw_op(found.actions(), '1') or 'Withdraw-1')
            yield from execution.delay_until_ticks(lambda: self.held_count(step.name) > before or bank.count(step.name) == 0, 7)
            yield from self.bank_pace()
        # The bronze, or whatever, comes off into the pack while the bank's open, then goes in.
        yield from self.prepare_worn_surplus_for_deposit(log)
        yield from self.deposit_surplus_gather_tools(log)
        attack = skills.level('attack')
        to_equip = []
        for name in [s.name for s in upgrades if s.equip and can_wield_tool(s.name, attack)] + self.tools_to_equip():
            if name not in to_equip:
                to_equip.append(name)
        self.log(f'tools: banked better gear ready ({self.gear_label()})')
        return (True, to_equip)

    def finish_upgrade(self, log, did_work, withdrew, to_equip):
        """Use with yield from."""
        if bank.is_open():
            yield from self.close_script_bank(log)
        if len(to_equip) > 0:
            # The surplus went in during the visit, so the bank isn't opened again for it.
            yield from self.equip_tools(to_equip, log, False)
        if did_work or withdrew:
            yield from self.walk_home_if_needed(log)
        return did_work or withdrew

    # Why: a better tool banked comes before a shop or smith, in one visit: withdraw, take the surplus off, deposit,
    # coins, shut once, wield. True means a bank or shop trip was tried, succeeding or backing off.
    def try_upgrade_gather_tool_at_bank(self, log=None):
        """A better tool from the bank, or an affordable one, when tool acquisition is on. Use with yield from."""
        log = log or (lambda m: self.log(f'  {m}'))
        startup = self.startup_tool_bank_sync_needed()
        if not self.tool_acquire_enabled():
            return False
        # The start's look in the bank runs through a backoff, so banked steel is used from the start.
        if not startup and not self.acquire_ready():
            return False
        if self.fishing or len(self.tool_reqs) == 0:
            if startup:
                self.startup_tool_bank_sync_pending = False
            return False
        if self.has_broken_gather_tool():
            return False
        # Missing gear is RestockGatherTool's, but the start still opens the bank once.
        if not self.has_gear() and not startup:
            return False
        self.status = 'tools: startup bank check' if startup else 'acquire: checking tool upgrades'
        self.log('tools: startup bank check for better axe/pick' if startup else 'acquire: checking tool upgrades at bank')
        opened = bank.is_open()
        if not opened:
            opened = yield from self.open_script_bank(log)
        if opened:
            opened = yield from self.wait_bank_ready(log)
        if not opened:
            if startup:
                self.startup_tool_bank_sync_pending = False
            self.mark_acquire_backoff(35)
            return True
        withdrew, to_equip = yield from self.withdraw_better_gather_tools_from_bank(log)
        if startup:
            self.startup_tool_bank_sync_pending = False
        # While it's here the worse tools go in, and only then is the shop's upgrade planned, on the bank's gp.
        if not withdrew:
            yield from self.prepare_worn_surplus_for_deposit(log)
            yield from self.deposit_surplus_gather_tools(log)
        if not self.acquire_ready():
            done = yield from self.finish_upgrade(log, withdrew, withdrew, to_equip)
            return done
        plan = plan_gather_tool_acquire(self.tool_reqs, self.acquire_world_with_bank(), upgrade=True)
        if plan is None or plan.kind == 'repair':
            # Nothing better in the shop: a cooldown, so it doesn't look every bank trip.
            self.mark_acquire_backoff(200)
            self.log('acquire: bank tool upgraded; no better shop tool right now' if withdrew else 'acquire: no better tool affordable right now')
            done = yield from self.finish_upgrade(log, withdrew, withdrew, to_equip)
            return done
        # The shop's gp comes out in the same visit, before the walk to the vendor.
        if plan.kind == 'buy':
            if not can_fund_plan(plan, inventory.count(COINS), bank.count(COINS)):
                log(f'acquire: not enough coins for {plan.name} ({plan.cost}gp)')
                self.mark_acquire_backoff(100)
                done = yield from self.finish_upgrade(log, withdrew, withdrew, to_equip)
                return done
            funded = yield from self.withdraw_coins_for(plan.cost, log)
            if not funded:
                self.mark_acquire_backoff(50)
                done = yield from self.finish_upgrade(log, withdrew, withdrew, to_equip)
                return done
        if bank.is_open():
            yield from self.close_script_bank(log, False)
        if len(to_equip) > 0:
            yield from self.equip_tools(to_equip, log, False)
        self.log(f'acquire: upgrade opportunity — {plan.reason}')
        # The coins and surplus are dealt with, so the buy skips its own bank visit.
        ok = yield from self.execute_tool_acquire_plan(plan, log, plan.kind == 'buy')
        self.mark_acquire_backoff(150 if ok else 75)
        # Always home after an attempt, so BankCatch can return early.
        yield from self.walk_home_if_needed(log)
        return True

    # Combat.

    def allow_combat_gather(self):
        return self.combat_policy().allow_gather

    def mob_flee_enabled(self):
        return self.combat_policy().flee

    def wilderness_miner_player_attack(self):
        """A player's attack, for the miners that otherwise hold their ground."""
        mode = self.combat_policy().mode
        return mode == 'wilderness-miner-player' or mode == 'desert-camp-miner-player'

    def wilderness_miner_stance_needed(self):
        return wilderness_miner_stance_needed(self.mining(), game.tile(), self.tick_manip.allow_combat, game.auto_retaliate_on(), self.desert_camp_route is not None)

    def combat_policy(self):
        return gathering_combat_policy(self.mining(), game.tile(), incoming_player_attacker(players.query().results()), is_auto_location(self.location_setting),
                                       self.tick_manip.allow_combat, self.desert_camp_route is not None)

    # Tick manipulation.

    def note_gather_roll(self, tick=None):
        self.last_roll_tick = math.floor(tick if tick is not None else game.tick())

    def gather_cycle_ticks(self):
        """The resource's cycle in ticks: the pickaxe's rate for iron, the profile's otherwise."""
        if self.tick_manip.method == 'iron-cadence':
            return mining_rate_for_pickaxe(best_pickaxe(skills.level('mining'), lambda n: self.held_count(n) > 0))
        return self.tick_manip.native_cycle_ticks

    def has_knife_delay_kit(self):
        return self.tick_manip.use_knife_delay and inventory.count(TICK_MANIP_KNIFE) >= 1 and self.delay_log_item() is not None

    def delay_log_item(self):
        """The tree's own log first, else any fletchable one."""
        if self.chopping:
            exact = inventory.first(logs_for_tree(self.target))
            if exact is not None:
                return exact
        for name in FLETCHABLE_LOG_NAMES:
            item = inventory.first(name)
            if item is not None:
                return item
        return first_where(inventory.items(), lambda i: is_fletchable_log_name(i.name))

    # Why: the server sets the delay only after a make's confirm, and the count dialog fails tick manipulation, so
    # it's always Make-1; the product finishing is incidental, the resource being clicked again the next tick.
    def arm_knife_delay(self):
        """Arms the knife and log's delay, two server ticks. Use with yield from."""
        if chat_dialog.is_make_menu():
            done = yield from self.confirm_knife_delay_make()
            return done
        knife = inventory.first(TICK_MANIP_KNIFE)
        log_item = self.delay_log_item()
        if knife is None or log_item is None:
            return False
        self.status = 'tick: knife delay'
        if not knife.use_on(log_item):
            return False
        # A short wait for the make menu, not a whole fletch.
        yield from execution.delay_until_ticks(lambda: chat_dialog.is_make_menu() or chat_dialog.can_continue(), 2)
        if chat_dialog.is_make_menu():
            done = yield from self.confirm_knife_delay_make()
            return done
        return False

    def confirm_knife_delay_make(self):
        """Make-1 only: shafts when offered, else the first product. Never Make X. Use with yield from."""
        made = yield from chat_dialog.make_one(KNIFE_DELAY_MAKE_MATCH)
        if made:
            return True
        products = chat_dialog.make_products()
        if len(products) > 0 and products[0]:
            made = yield from chat_dialog.make_one(products[0])
            if made:
                return True
        self.log(f"tick: knife Make-1 failed (menu: [{', '.join(products)}]) — never Make-X")
        return False

    def trim_delay_logs(self, keep=1):
        """Drops spare fletchable logs, so the knife delay keeps one; the tree's own type goes last. Use with yield
        from."""
        if not self.tick_manip.use_knife_delay:
            return 0
        prefer = logs_for_tree(self.target).lower() if self.chopping else ''
        dropped = 0
        for _ in range(12):
            logs = [i for i in inventory.items() if is_fletchable_log_name(i.name)]
            if extra_delay_logs_to_drop(sum([max(1, i.count) for i in logs]), keep) <= 0:
                break
            item = first_where(logs, lambda i: (i.name or '').lower() != prefer) or logs[-1]
            before = inventory.used()
            item.interact('Drop')
            freed = yield from execution.delay_until_ticks(lambda: inventory.used() < before, 5)
            if not freed:
                break
            dropped += before - inventory.used()
        if dropped > 0:
            self.log(f'tick: dropped {dropped} extra delay log(s)')
        return dropped

    def held_shortbow_name(self):
        """The best shortbow worn or held, for 3t rapid."""
        for n in SHORTBOW_NAMES:
            if equipment.contains(n) or inventory.count(n) > 0:
                return n
        loose = first_where(inventory.items(), lambda i: is_shortbow_name(i.name))
        return loose.name if loose is not None else None

    def ensure_shortbow_equipped(self):
        """Use with yield from."""
        if not self.tick_manip.shortbow_rapid or len([i for i in equipment.items() if is_shortbow_name(i.name)]) > 0:
            return True
        name = self.held_shortbow_name()
        if name is None:
            return False
        self.status = 'tick: equip shortbow'
        worn = yield from equipment.equip(name)
        return worn

    def tanner_cook_one(self):
        """Tannerfishing: cooks one raw fish on the nearest fire or range in the scene, staying by the pier. Use with
        yield from."""
        if not self.tick_manip.cook_eat_interleave:
            return False
        raw = self.last_raw_fish()
        if chat_dialog.is_make_menu():
            made = yield from chat_dialog.make(raw.name if raw is not None else None)
            if not made:
                yield from chat_dialog.make()
            yield from execution.delay_ticks(1)
            return True
        if raw is None:
            return False
        oven = locs.query().name('Fire', 'Range', 'Cooking range').where(lambda l: l.distance() <= 8).nearest() or locs.query().name('Fire', 'Range', 'Cooking range').nearest()
        if oven is None:
            self.log('tick: tannerfish — no Fire/Range in scene (light a fire or stand near one)')
            return False
        self.status = f'tick: cook {raw.name}'
        before = self.cookable_raw_count()
        if not raw.use_on(oven):
            return False
        yield from execution.delay_until_ticks(lambda: self.cookable_raw_count() < before or chat_dialog.is_make_menu() or chat_dialog.can_continue(), 9)
        if chat_dialog.is_make_menu():
            made = yield from chat_dialog.make(raw.name)
            if not made:
                yield from chat_dialog.make()
            yield from execution.delay_ticks(1)
        return True

    def tanner_eat_one(self):
        """Tannerfishing: eats a cooked fish at low HP. Use with yield from."""
        if not self.tick_manip.cook_eat_interleave:
            return False
        food = first_where(inventory.items(), lambda i: is_cooked_fish_name(i.name))
        if food is None:
            return False
        self.status = f'tick: eat {food.name}'
        before = skills.effective('hitpoints')
        if not food.interact('Eat'):
            return False
        yield from execution.delay_until_ticks(lambda: skills.effective('hitpoints') > before, 5)
        return True

    def drop_one_product_log(self):
        """Drops one product log, for the farmer's sixth tick. Use with yield from."""
        item = first_where(inventory.items(), lambda i: self.is_product(i.name) and is_fletchable_log_name(i.name)) or first_where(inventory.items(), lambda i: self.is_product(i.name))
        if item is None:
            return False
        self.status = f'tick: drop {item.name}'
        before = inventory.used()
        item.interact('Drop')
        dropped = yield from execution.delay_until_ticks(lambda: inventory.used() < before, 5)
        return dropped

    # The miner's food.

    def is_power_mode(self):
        return self.power_mode

    def food_count(self):
        """The desert camp route's food."""
        return self.miner_food_count()

    def keep_miner_food(self):
        return self.power_mode or self.desert_camp_route is not None

    def full_haul_needs_bank(self):
        return not self.power_mode and inventory.is_full() and self.has_depositable()

    def miner_food_count(self):
        return count_food(inventory.items(), self.miner_food.name) if self.miner_food is not None else 0

    def miner_food_restock_needed(self):
        startup = self.miner_food_startup_pending or (self.power_mode and inventory.is_full() and len(self.products()) == 0)
        return miner_food_restock_needed(self.miner_food is not None, self.miner_food_count(), startup)

    def should_eat_miner_food(self):
        config = self.miner_food
        if config is None:
            return False
        return should_eat_miner_food(skills.effective('hitpoints'), skills.level('hitpoints'), food_heal_amount(config.name), self.miner_food_count(), inventory.is_full(),
                                     self.keep_miner_food(), 9 if self.desert_camp_route is not None else None)

    def eat_miner_food(self, food_name=None):
        """Use with yield from."""
        name = food_name or (self.miner_food.name if self.miner_food is not None else None)
        if not name or bank.is_open():
            return False
        if self.desert_camp_route is not None and self.full_haul_needs_bank():
            self.desert_camp_bank_trip = True
        food = first_where(inventory.items(), lambda i: is_food_item(i.name, name))
        if food is None:
            return False
        hp = skills.effective('hitpoints')
        used = inventory.used()
        count = self.miner_food_count()
        slot, fid, fname = food.slot, food.id, food.name
        reason = 'ore room' if inventory.is_full() and not self.keep_miner_food() else 'full heal'
        self.status = f'food: eating {food.name} ({reason})'
        self.log(f"food: eat {food.name} ({reason}; hp {hp}/{skills.level('hitpoints')}, pack {used}/28)")
        if not food.interact('Eat'):
            self.log(f"food: '{food.name}' has no usable Eat action")
            return False

        def consumed():
            same = item_at_slot(slot)
            return (skills.effective('hitpoints') > hp or inventory.used() < used or self.miner_food_count() < count or same is None or same.id != fid
                    or same.name != fname)

        ate = yield from execution.delay_until_ticks(consumed, 6)
        if ate:
            self.miner_food_eaten += 1
        else:
            self.log(f'food: {food.name} did not change the pack or HP — will retry')
        return ate

    def heal_miner_at_bank(self, log):
        """Eats the food setting's fish at the bank up to near full HP, then deposits the leftovers. Use with yield
        from."""
        if not self.mining():
            return True
        name = self.settings.str('food', 'Lobster').strip()
        if not name:
            return True
        heal = food_heal_amount(name)
        missing_hp = lambda: skills.level('hitpoints') - skills.effective('hitpoints')
        bites = missing_hp() // heal if heal > 0 else 0
        if bites <= 0 or skills.effective('hitpoints') <= 0:
            return True
        holding = lambda: len([i for i in inventory.items() if is_food_item(i.name, name)]) > 0
        eaten = 0
        while eaten < bites and missing_hp() >= heal:
            if not holding():
                opened = yield from self.reopen_bank(log)
                if not opened:
                    return self.heal_failed(log, 'food: bank did not open for healing')
                form = first_where(food_forms(name), lambda f: bank.count(f) > 0)
                if form is None:
                    return self.heal_failed(log, f'food: no {name} available for bank healing')
                took = inventory.free() > 0
                if took:
                    took = yield from bank.withdraw_x(form, 1)
                if not took:
                    return self.heal_failed(log, f'food: could not withdraw {name} for bank healing')
                landed = yield from execution.delay_until_ticks(holding, 7)
                if not landed:
                    return self.heal_failed(log, f'food: {name} withdrawal did not reach the backpack')
            expected = [(i.slot, i.id) for i in inventory.items() if is_food_item(i.name, name)]
            closed = yield from self.close_script_bank(log, False)
            if not closed:
                return self.heal_failed(log, 'food: bank did not close for healing')
            updated = yield from execution.delay_until_ticks(lambda: bank.normal_backpack_snapshot() is not None and len([1 for slot, fid in expected if first_where(inventory.items(), lambda i: i.slot == slot and i.id == fid) is None]) == 0, 6)
            if not updated:
                return self.heal_failed(log, 'food: normal backpack did not update after closing the bank')
            if missing_hp() < heal:
                break
            hp = skills.effective('hitpoints')
            ate = yield from self.eat_miner_food(name)
            if ate:
                ate = yield from execution.delay_until_ticks(lambda: skills.effective('hitpoints') > hp, 6)
            if not ate:
                return self.heal_failed(log, f'food: {name} did not restore HP at the bank')
            yield from execution.delay_ticks(3)
            eaten += 1
        opened = yield from self.reopen_bank(log)
        if not opened:
            return self.heal_failed(log, 'food: bank did not reopen after healing')
        yield from bank.deposit_all_matching(lambda n, *_args: self.should_deposit(n))
        cleared = yield from execution.delay_until_ticks(lambda: len([i for i in inventory.items() if self.should_deposit(i.name or '')]) == 0, 6)
        if not cleared:
            return self.heal_failed(log, 'food: bank did not accept healing leftovers')
        return True

    def heal_failed(self, log, reason):
        self.status = f'{reason} - stopped'
        log(reason)
        self.request_finish(reason)
        return False

    def reopen_bank(self, log):
        """Use with yield from."""
        if bank.is_open():
            ready = yield from self.wait_bank_ready(log)
            return ready
        yield from execution.delay_until_ticks(lambda: bank.normal_backpack_snapshot() is not None, 6)
        expected = bank.normal_backpack_snapshot()
        if expected is None:
            return False
        opened = yield from self.open_script_bank(log)
        if opened:
            opened = yield from self.wait_bank_ready(log)
        if opened:
            opened = yield from bank.backpack_ready(expected, log)
        return opened

    def top_up_miner_food_at_bank(self, log, reserved_slots):
        """The miner's food back to its target, while BankCatch has the bank open. Use with yield from."""
        config = self.miner_food
        if config is None:
            return True
        yield from execution.delay_until_ticks(lambda: bank.snapshot_ready() if self.desert_camp_route is not None else bank.loaded(), 6)
        yield from execution.delay_ticks(1)
        held = self.miner_food_count()
        forms = food_forms(config.name) if self.desert_camp_route is not None else [config.name]
        banked = sum([bank.count(f) for f in forms])
        reserved = max(reserved_slots, 1 if self.power_mode else 0)
        plan = plan_miner_food_withdrawal(config.target, held, banked, inventory.free(), reserved)
        if not plan.ok:
            if plan.reason == 'bank-stock':
                detail = f'bank + pack are short by {plan.missing}'
            elif reserved > 0:
                detail = f'pack needs {plan.missing} more free slot(s) after reserving {reserved} for supplies and gathering'
            else:
                detail = f'pack needs {plan.missing} more free slot(s)'
            yield from self.stop_food(log, f'food: cannot prepare {config.target} {config.name} ({detail})')
            return False
        if plan.withdraw > 0:
            self.status = f'food: withdrawing {plan.withdraw} {config.name}'
            log(f'food: withdraw {plan.withdraw} {config.name} ({held} → {config.target})')
            remaining = plan.withdraw
            for form in forms:
                take = min(remaining, bank.count(form))
                if take <= 0:
                    continue
                took = yield from bank.withdraw_x(form, take)
                if not took:
                    remaining = -1
                    break
                remaining -= take
                if remaining == 0:
                    break
            if remaining != 0:
                yield from self.stop_food(log, f'food: withdraw failed for {plan.withdraw} {config.name}')
                return False
            yield from execution.delay_until_ticks(lambda: self.miner_food_count() >= config.target, 7)
        after = self.miner_food_count()
        if after < config.target:
            yield from self.stop_food(log, f'food: restock verification failed ({after}/{config.target} {config.name})')
            return False
        self.miner_food_startup_pending = False
        self.log(f'food: trip ready with {after} {config.name}')
        return True

    def stop_food(self, log, message):
        """Use with yield from."""
        self.status = f'{message} — stopped'
        self.log(f'{message}; stopping')
        if bank.is_open():
            yield from self.close_script_bank(log, False)
        self.request_finish(message)

    # The desert camp.

    def desert_camp_direction(self):
        route = self.desert_camp_route
        needs_bank = (self.full_haul_needs_bank() or self.miner_food_restock_needed() or (route is not None and desert_camp_food_reserve_depleted(self.miner_food_count()))
                      or self.desert_camp_startup_bank_pending or self.startup_tool_bank_sync_needed() or not has_all_tools(self.tool_reqs, self.skill_level, self.held_count))
        state = desert_camp_bank_trip_direction(self.desert_camp_bank_trip, needs_bank)
        self.desert_camp_bank_trip = state.bank_trip
        return state.direction

    def desert_mining_camp_travel_needed(self):
        if self.desert_camp_route is None or bank.is_open() or event_signal.pending():
            return False
        direction = self.desert_camp_direction()
        if direction == 'enter' and self.should_suppress_camp_reentry():
            return False
        return self.desert_camp_route.needs_step(direction)

    def run_desert_mining_camp_travel(self):
        """Use with yield from."""
        if self.desert_camp_route is None:
            raise RuntimeError('Desert Mining Camp travel ran without an initialized route')
        direction = self.desert_camp_direction()
        if direction == 'enter' and self.should_suppress_camp_reentry():
            self.status = 'combat: holding outside camp after player attack'
            return False
        done = yield from self.desert_camp_route.run_step(direction)
        return done

    def desert_camp_bank_catch_needed(self):
        return desert_camp_bank_catch_needed(self.desert_camp_bank_trip, self.desert_camp_startup_bank_pending, self.miner_food_restock_needed(), self.full_haul_needs_bank())

    def complete_desert_camp_bank_trip(self):
        self.desert_camp_startup_bank_pending = False
        self.desert_camp_bank_trip = False

    def desert_camp_deposit_residue(self):
        if self.desert_camp_route is None:
            return []
        return [i.name or f'item {i.id}' for i in inventory.items() if self.should_deposit(i.name or '')]

    def strict_desert_camp_banking(self):
        return self.desert_camp_route is not None

    # The camp and its bank.

    def away_from_gather_spot(self, slack=4):
        return not tile_within_leash(self, game.tile() or self.anchor, slack)

    # Why: the walk is skipped within the arrive radius, not the whole leash: a camp's bank stand can sit within the
    # leash far from the resources.
    def walk_home_if_needed(self, log=None, arrive_radius=None):
        """Back toward the anchor after a bank, shop or repair. Use with yield from."""
        log = log or (lambda m: self.log(f'  {m}'))
        arrive_radius = HOME_ARRIVE_RADIUS if arrive_radius is None else arrive_radius
        if self.desert_camp_route is not None:
            done = yield from self.run_desert_mining_camp_travel()
            return done
        here = game.tile()
        if here is not None and not should_walk_home_to_gather_anchor(self.anchor.distance_to(here), arrive_radius):
            return True
        self.status = 'returning to camp'
        walked = yield from traversal.walk_resilient(self.anchor, radius=arrive_radius, log=log)
        return walked

    def should_deposit(self, name):
        if self.kept(name):
            return False
        # Why: cooked, and banked burnt, stay depositable through BankCatch, a safety net when FishBankCooked never ran.
        if self.cook_enabled() and not self.cooking_load and not self.in_cook_batch and self.cook_mode != 'off':
            if is_cooked_fish_name(name) or is_burnt_fish_name(name):
                return self.should_deposit_cook_result(name)
            # Raw the filter doesn't cook is banked as it is.
            if is_raw_fish_name(name) and not raw_matches_cook_filter(name, self.cook_fish_filter):
                return True
        if len(self.gear_keep) > 0:
            return deposit_all_except(self.gear_keep)(name)
        if self.mining():
            return self.is_product(name) or name.lower().startswith('uncut ')
        return self.is_product(name)

    def has_depositable(self):
        if len([i for i in inventory.items() if self.should_deposit(i.name or '')]) > 0:
            return True
        # The cooked haul after a load: the product's keyword is only "raw".
        return self.cook_enabled() and not self.cooking_load and not self.in_cook_batch and len([i for i in inventory.items() if self.should_deposit_cook_result(i.name or '')]) > 0

    def drop_products(self):
        """Use with yield from."""
        self.status = 'dropping'

        def droppable():
            keep = None
            if self.tick_manip.use_knife_delay:
                log_item = first_where(inventory.items(), lambda i: is_fletchable_log_name(i.name))
                keep = log_item.slot if log_item is not None else None
            return [i for i in self.products() if i.slot != keep]

        for _ in range(3):
            items = droppable()
            if len(items) == 0:
                return
            for item in items:
                item.interact('Drop')
            cleared = yield from execution.delay_until(lambda: len(droppable()) == 0, 6000)
            if cleared:
                self.log('drop: haul cleared')
                return
        raise RuntimeError('Gathering bot could not clear the haul after three drop batches')

    def is_pack_junk(self, name, id=-1):
        """Random events' and common junk that shouldn't keep pack slots while burning, when BankCatch can't run."""
        if not name or self.kept(name):
            return False
        n = name.lower()
        if n == TINDERBOX.lower() or (self.burn_enabled() and n == self.burn_logs.lower()):
            return False
        if self.fish_method is not None and len([g for g in self.fish_method.gear if g.name.lower() == n]) > 0:
            return False
        # The ore or raw catch in banking mode is wanted; only true junk drops.
        if not self.power_mode and not self.burn_enabled() and self.is_product(name):
            return False
        return is_disposable_gather_junk(name, id)

    def pack_junk_items(self):
        return [i for i in inventory.items() if self.is_pack_junk(i.name, i.id)]

    def count_trip(self, n):
        self.trips += 1
        self.banked += n

    def reject(self, key):
        if key not in self.rejected:
            self.rejected.append(key)
            self.log(f"skipping {self.target} at {key} (can't {self.action.lower()} it)")

    def cooldown(self, key, ticks=8):
        self.cooldown_until[key] = game.tick() + ticks

    def usable(self, key):
        if key in self.rejected:
            return False
        until = self.cooldown_until.get(key)
        return until is None or game.tick() >= until

    # Reporting.

    def tracked_skills(self):
        out = []
        if self.fishing:
            out.append('fishing')
        if self.mining():
            out.append('mining')
        if self.woodcutting():
            out.append('woodcutting')
        if self.fishing and self.cook_mode != 'off':
            out.append('cooking')
        if self.chopping and self.burn_mode != 'off':
            out.append('firemaking')
        return out

    def capture_xp_start(self):
        self.xp_start = {}
        for skill in self.tracked_skills():
            self.xp_start[skill] = skills.xp(skill)

    def full_inventory_note(self):
        if self.burn_mode == 'chop-then-burn':
            return f'burning {self.burn_logs} when full'
        if self.power_mode:
            return f'Bank=false: batch dropping {self.product_label()} when full'
        if self.miner_food is not None:
            if self.desert_camp_route is not None:
                return f'banking when full; retaining {self.miner_food.name} for Desert Camp travel'
            return f'eating {self.miner_food.name} for ore slots, then banking to restock'
        if self.tick_manip.cook_eat_interleave:
            return 'tannerfishing: cook/eat on pier; drop haul when full (may die)'
        if self.fishing and self.cook_mode == 'cook-then-bank':
            if self.cook_fish_filter:
                return f'cook {cook_filter_label(self.cook_fish_filter)} then bank (other raw banked as-is) when full'
            return 'cook then bank when full'
        if self.fishing and self.cook_mode == 'bank-raw-then-cook':
            return f'bank {cook_filter_label(self.cook_fish_filter)} to {self.bank_raw_target} then cook batches'
        return f'banking {self.product_label()} when full'

    def on_progress_report(self):
        minutes = (time.time() - self.started_at) / 60
        report = {'Status': self.status, 'Location': self.location.name if self.location is not None else ('Bank=false (power)' if self.power_mode else 'nearest bank'),
                  'Gathered': self.gathered, 'Banked': self.banked, 'Trips': self.trips}
        for skill in self.tracked_skills():
            gained = max(0, skills.xp(skill) - self.xp_start.get(skill, skills.xp(skill)))
            label = skill[0].upper() + skill[1:]
            report[f'{label} xp'] = gained
            report[f'{label} xp/hr'] = f'{gained / minutes * 60 / 1000:.1f}k' if minutes > 0.5 else '—'
        if self.mining():
            report['Gems'] = self.gems
        if self.cook_enabled():
            report['Cooked'] = self.cooked
            report['Burnt'] = self.burnt
        if self.burn_enabled():
            report['Fires'] = self.fires
        if self.miner_food is not None:
            report['Food'] = self.miner_food_count()
        return report
