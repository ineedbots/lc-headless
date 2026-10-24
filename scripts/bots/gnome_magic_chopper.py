# Chops the Magic trees of the Tree Gnome Stronghold, running to whichever is up and hopping between the three
# when none are, banking at the gnome booths upstairs, and fletching magic bows at 80 and 85 when that's on:
# rs2b0t's GnomeMagicChopper (MIT, see thirdparty/rs2b0t). After a death it takes the Lumbridge knife, 500gp and a
# steel axe from Bob, and sails back through Karamja and Ardougne.

import time

from rs2004.catalogs import AXES, best_axe, can_wield_tool

SETTINGS = {
    'fletch_logs': SettingDef('boolean', True, 'Fletch logs into bows', group='Fletching',
                              help='When on: fletch magic shortbows at 80 / longbows at 85 (needs a Knife), then bank those. When off: bank the logs. Missing Knife at the gnome bank stops the script.'),
}


class TreePin:
    def __init__(self, id, name, tile):
        self.id = id
        self.name = name
        self.tile = tile


TREE_PINS = [
    TreePin('west', 'west magics (terrorbirds)', Tile(2372, 3425, 0)),
    TreePin('bank', 'south-bank magics', Tile(2433, 3410, 0)),
    TreePin('east', 'east magics (agility)', Tile(2491, 3413, 0)),
]
GNOME_ENTRANCE = Tile(2461, 3381, 0)
TREE_NAME = 'Magic tree'
SHORTBOW_LEVEL = 80
LONGBOW_LEVEL = 85
CHOP_REACH = 8
TREE_SEARCH_REACH = 80
BANK_STAND = Tile(2445, 3425, 1)
BANK_STAIR_SOUTH = Tile(2444, 3416, 0)
BANK_STAIR_NORTH = Tile(2445, 3434, 0)
BANK_STAIR_PINS = [BANK_STAIR_SOUTH, BANK_STAIR_NORTH]
BANK_STAIR_RADIUS = 5
BANK_BOOTH_REACH = 6
GEAR_BOB_STAND = Tile(3231, 3203, 0)
GEAR_KNIFE_SPAWN = Tile(3224, 3202, 0)
GEAR_STEEL_AXE = 'Steel axe'
GEAR_STEEL_COST = 250
GEAR_BROKEN_AXE = 'Broken axe'
DEATH_GP = 500
PICKPOCKET_OP = 'Pickpocket'
TALK_OP = 'Talk-to'
STUN_TICKS = 9
GP_TARGET = 60
BOAT_FARE = 30
MIN_HP = 5
LUMBY_MEN = Tile(3222, 3218, 0)
LUMBY_LEASH = 16
PORT_SARIM_DOCK = Tile(3029, 3217, 0)
BRIMHAVEN_DOCK = Tile(2772, 3227, 0)
SARIM_SAILORS = ['Captain Tobias', 'Seaman Lorris', 'Seaman Thresnor']
BRIM_SAILORS = ['Customs officer', 'Customs Officer', 'Captain Barnaby']
KARAMJA_DIALOG_PREFER = ['musa point', 'karamja', 'yes please', 'yes']
ARDOUGNE_DIALOG_PREFER = ['search away', 'nothing to hide', 'can i journey', 'journey on this ship', 'ardougne', "i'd like to go to ardougne", 'ok', 'okay', 'yes please', 'yes']
FEMI_DIALOG_PREFER = ['yes', 'ok', 'okay', 'help', 'please']
DIALOG_AVOID = ['no, thank', 'no thank', "i'm good", 'nowhere', 'rimmington', 'pandemonium', 'actually, i don', 'pay you nothing', 'not bother',
                'unusual customs', 'personal use', "you're not putting", 'why?']
# The trip back after a death, by boat: SneakyArdougne.
PHASE_THIEVE = 'thieve'
PHASE_WALK_SARIM = 'walk_sarim'
PHASE_BOAT_KARAMJA = 'boat_karamja'
PHASE_WALK_BRIMHAVEN = 'walk_brimhaven'
PHASE_BOAT_ARDOUGNE = 'boat_ardougne'
PHASE_DONE = 'done'
# The recovery after a death.
RECOVER_NONE = 'none'
RECOVER_KNIFE = 'knife'
RECOVER_BANK_GP = 'bank_gp'
RECOVER_BUY_AXE = 'buy_axe'
RECOVER_BANK_TOOLS = 'bank_tools'
RECOVER_TRAVEL = 'travel'
RECOVER_RESTOCK = 'restock'
KEEP_KNIFE = 'knife'
KEEP_BROKEN_AXE = 'broken axe'


def in_box(tile, x0, z0, x1, z1):
    if tile is None:
        return False
    return tile.x >= min(x0, x1) and tile.x <= max(x0, x1) and tile.z >= min(z0, z1) and tile.z <= max(z0, z1)


def cheb(a, b):
    return max(abs(a.x - b.x), abs(a.z - b.z))


def player_floor(tile=None):
    t = tile if tile is not None else game.tile()
    return t.level if t is not None else 0


def is_upstairs(tile=None):
    return player_floor(tile) >= 1


def in_gnome_area(tile):
    """The Tree Gnome Stronghold, its south gate included."""
    return in_box(tile, 2360, 3375, 2520, 3520)


def in_tree_band(tile):
    """The band that holds the three Magic trees."""
    return tile is not None and player_floor(tile) == 0 and in_box(tile, 2360, 3395, 2515, 3455)


def region_of(tile):
    if tile is None:
        return 'unknown'
    if in_gnome_area(tile):
        return 'gnome'
    if in_box(tile, 2650, 3360, 2760, 3520):
        return 'seers'
    if in_box(tile, 2600, 3260, 2730, 3360):
        return 'ardougne'
    if in_box(tile, 2740, 3140, 2820, 3290):
        return 'brimhaven'
    if in_box(tile, 2880, 3100, 2985, 3200):
        return 'musa'
    if in_box(tile, 3005, 3175, 3060, 3260):
        return 'sarim'
    if in_box(tile, 3185, 3185, 3265, 3265):
        return 'lumbridge'
    if in_box(tile, 2820, 3100, 2985, 3290):
        return 'karamja'
    return 'unknown'


def same_stair_pin(a, b):
    return a is not None and b is not None and a.x == b.x and a.z == b.z


def nearest_bank_stair_pin(tile, skip_pin=None):
    if tile is None:
        return BANK_STAIR_SOUTH if same_stair_pin(BANK_STAIR_NORTH, skip_pin) else BANK_STAIR_NORTH
    best = None
    best_d = 999
    for pin in BANK_STAIR_PINS:
        if same_stair_pin(pin, skip_pin):
            continue
        d = cheb(tile, pin)
        if d < best_d:
            best = pin
            best_d = d
    return best if best is not None else BANK_STAIR_NORTH


def dist_to_booths(tile):
    return cheb(tile, BANK_STAND) if tile is not None else 999


def dist_to_nearest_bank_stair(tile):
    return cheb(tile, nearest_bank_stair_pin(tile)) if tile is not None else 999


def is_allowed_bank_stair_tile(tile):
    return tile is not None and dist_to_nearest_bank_stair(tile) <= BANK_STAIR_RADIUS


def at_gnome_bank_floor(tile=None):
    t = tile if tile is not None else game.tile()
    return is_upstairs(t) and (dist_to_booths(t) <= 8 or dist_to_nearest_bank_stair(t) <= 12)


def loc_name(loc):
    return (loc.name or '').lower() if loc is not None else ''


def is_bank_booth_loc(loc):
    n = loc_name(loc)
    return 'bank booth' in n or 'bank chest' in n


def first_action(acts, test):
    for a in acts:
        if test(a.lower()):
            return a
    return None


def booth_op(loc):
    acts = loc.actions()
    return first_action(acts, lambda a: 'use-quickly' in a) or first_action(acts, lambda a: a == 'bank') or first_action(acts, lambda a: 'bank' in a)


def is_climb_loc(loc):
    n = loc_name(loc)
    return 'stair' in n or 'ladder' in n


def climb_op(loc, direction):
    acts = loc.actions()
    return first_action(acts, lambda a: a.startswith('climb') and direction in a) or first_action(acts, lambda a: a == 'climb')


def open_op(loc):
    return first_action(loc.actions(), lambda a: a.startswith('open'))


def is_shut_door(loc):
    name = loc_name(loc)
    return ('door' in name or 'gate' in name) and open_op(loc) is not None


def dialog_avoid(opt):
    low = (opt or '').lower()
    return len([a for a in DIALOG_AVOID if a in low]) > 0


def pick_boat_option(options, prefer):
    usable = [o for o in options if not dialog_avoid(o)]
    pool = usable if len(usable) > 0 else options
    for p in prefer:
        for o in pool:
            if p.lower() in (o or '').lower():
                return o
    for o in pool:
        if (o or '').lower().startswith('yes'):
            return o
    return pool[0] if len(pool) > 0 else None


def dialog_open():
    return chat_dialog.can_continue() or (chat_dialog.is_open() and len(chat_dialog.options()) > 0)


def npc_talk_op(npc):
    return first_action(npc.actions(), lambda a: a.startswith('talk')) or TALK_OP


def gear_has_knife():
    return inventory.count('Knife') > 0


def gear_inv_coins():
    return sum([max(0, i.count) for i in inventory.items() if (i.name or '').lower() == 'coins'])


def gear_axe_count(name):
    return inventory.count(name) + (1 if equipment.contains(name) else 0)


def gear_best_held_axe():
    return best_axe(skills.level('woodcutting'), lambda n: gear_axe_count(n) > 0)


def axe_rank(name):
    for i in range(len(AXES)):
        if AXES[i].name.lower() == name.lower():
            return i
    return -1


def gear_has_steel_or_better():
    steel = axe_rank(GEAR_STEEL_AXE)
    for i in range(len(AXES)):
        if i > steel:
            continue
        name = AXES[i].name
        if gear_axe_count(name) > 0 or (bank.is_open() and bank.count(name) > 0):
            return True
    return False


def gear_has_broken_axe():
    return equipment.contains(GEAR_BROKEN_AXE) or inventory.count(GEAR_BROKEN_AXE) > 0


def gear_wait_bank_loaded():
    """Use with yield from."""
    yield from execution.delay_until(lambda: bank.loaded() or len(bank.items()) > 0, 3000)
    yield from execution.delay_ticks(1)


def chop_op(acts):
    return first_action(acts, lambda a: 'chop' in a)


def is_magic_tree_loc(loc):
    n = loc_name(loc)
    if 'magic' not in n or 'tree' not in n or 'stump' in n or 'seed' in n or 'patch' in n:
        return False
    return chop_op(loc.actions()) is not None


def other_players_near(tile, dist=2):
    if tile is None:
        return 0
    return players.query().where(lambda p: p.tile().distance_to(tile) <= dist).count()


def is_keep_tool(name):
    if not name:
        return False
    n = name.lower()
    if n == KEEP_KNIFE or n == KEEP_BROKEN_AXE:
        return True
    active = gear_best_held_axe()
    return active is not None and n == active.lower()


def has_essentials_after_bank(need_knife=True):
    if need_knife and not gear_has_knife():
        return False
    return gear_has_broken_axe() or gear_best_held_axe() is not None


def nearest_tree_pin(tile):
    if tile is None:
        return TREE_PINS[1]
    best = TREE_PINS[1]
    best_d = 9999
    for pin in TREE_PINS:
        d = tile.distance_to(pin.tile)
        if d < best_d:
            best = pin
            best_d = d
    return best


def next_tree_pin(current_id):
    for i in range(len(TREE_PINS)):
        if TREE_PINS[i].id == current_id:
            return TREE_PINS[(i + 1) % len(TREE_PINS)]
    return TREE_PINS[0]


def pin_by_id(id):
    for p in TREE_PINS:
        if p.id == id:
            return p
    return TREE_PINS[1]


def norm_name(name):
    return ' '.join((name or '').lower().split())


def is_fletched_shortbow(name):
    n = norm_name(name)
    return 'magic' in n and 'short' in n and 'bow' in n


def is_fletched_longbow(name):
    n = norm_name(name)
    return 'magic' in n and 'long' in n and 'bow' in n


def is_bankable_bow(name):
    return is_fletched_shortbow(name) or is_fletched_longbow(name)


def is_magic_log(name):
    n = norm_name(name)
    return n == 'magic logs' or n == 'magic log'


class FletchPlan:
    def __init__(self, id, menu_match, label, fletch):
        self.id = id
        self.menu_match = menu_match
        self.label = label
        self.bank = True
        self.fletch = fletch


def fletch_plan(level, fletch_on=True):
    if not fletch_on or level < SHORTBOW_LEVEL:
        return FletchPlan('logs', '', 'Magic logs (bank)', False)
    if level < LONGBOW_LEVEL:
        return FletchPlan('magic-shortbow', 'short', 'Magic shortbow', True)
    return FletchPlan('magic-longbow', 'long', 'Magic longbow', True)


def match_make_product(products, menu_match):
    want = menu_match.lower()
    magicish = [p for p in products if 'magic' in (p or '').lower()]
    pool = magicish if len(magicish) > 0 else products
    for p in pool:
        if want in (p or '').lower():
            return p
    return None


def stack_total(test):
    return sum([max(1, i.count) for i in inventory.items() if test(i.name)])


def log_count():
    return stack_total(is_magic_log)


def bow_count():
    return stack_total(is_bankable_bow)


def shortbow_count():
    return stack_total(is_fletched_shortbow)


def knife_item():
    for i in inventory.items():
        if 'knife' in (i.name or '').lower():
            return i
    return None


def last_log():
    logs = [i for i in inventory.items() if is_magic_log(i.name)]
    return logs[-1] if len(logs) > 0 else None


def needs_bank_trip(plan):
    if log_count() > 0 and plan.fletch:
        return False
    if plan.bank and bow_count() > 0:
        return True
    if plan.fletch and log_count() == 0 and bow_count() > 0:
        return True
    return not plan.fletch and log_count() > 0 and inventory.is_full()


def moved_far(source, tiles):
    now = game.tile()
    return source is not None and now is not None and source.distance_to(now) >= tiles


def tree_on_ground(l):
    t = l.tile()
    return in_tree_band(t) and t.level == 0


def booth_on_floor(l, floor):
    return is_bank_booth_loc(l) and l.tile().level == floor


def sailor_like(n):
    nm = (n.name or '').lower()
    return 'captain' in nm or 'seaman' in nm or 'sailor' in nm


class GnomeMagicChopper(LoopingBot):
    def on_start(self):
        self.status = 'starting'
        self.chopped = 0
        self.fletched = 0
        self.bank_trips = 0
        self.hops = 0
        self.trees_up = 0
        self.deaths = 0
        self.died = False
        self.gear_ready = False
        self.recover_phase = RECOVER_NONE
        self.travel_phase = PHASE_DONE
        self.stunned_until_tick = 0
        self.blocked_stair_pin = None
        yield from execution.delay_until(lambda: game.ingame() and game.tile() is not None, 0)
        traversal.preload()
        self.started_at = time.time()
        self.wc_xp_at_start = skills.xp('woodcutting')
        self.fletch_xp_at_start = skills.xp('fletching')
        self.plan_id = self.current_plan().id
        self.tree_pin_id = nearest_tree_pin(game.tile()).id
        self.on('chat_message', self.heard)
        self.on('skill_level', self.levelled)
        plan = self.current_plan()
        pins = ' / '.join([f'{p.tile.x},{p.tile.z}' for p in TREE_PINS])
        making = f"fletching {skills.level('fletching')} → {plan.label}" if self.fletch_enabled() else 'banking logs (fletch off)'
        self.log(f'GnomeMagicChopper, magics at {pins}, {making}')
        if skills.level('woodcutting') < 75:
            self.log(f"WARNING: Woodcutting {skills.level('woodcutting')} < 75, Magic trees may refuse chops")
        self.status = 'ready'

    def heard(self, e):
        t = (e.text or '').lower()
        if 'oh dear' in t and 'you are dead' in t and not self.died:
            self.died = True
            self.deaths += 1
            self.recover_phase = RECOVER_KNIFE
            self.travel_phase = None
            self.gear_ready = False
            self.status = 'dead'
            self.log(f'died (#{self.deaths}), knife spawn → 500gp → Bob → SneakyArdougne → gnome magics')
        if 'been stunned' in t or 'fail to pick' in t:
            self.stunned_until_tick = game.tick() + STUN_TICKS

    def levelled(self, e):
        if e.name == 'fletching':
            plan = self.plan_at(e.level)
            self.log(f'fletching {e.previous} → {e.level}, now making {plan.label}')
            self.plan_id = plan.id
        if e.name == 'woodcutting':
            self.log(f'woodcutting {e.previous} → {e.level}')

    def fletch_enabled(self):
        return self.settings.bool('fletch_logs', True)

    def plan_at(self, level):
        return fletch_plan(level, self.fletch_enabled())

    def current_plan(self):
        return self.plan_at(skills.level('fletching'))

    def loop(self):
        if not game.ingame():
            yield from execution.delay_ticks(5)
            return
        if self.died:
            yield from self.wait_for_respawn()
            return
        if self.recover_phase != RECOVER_NONE:
            yield from self.recover_from_death()
            return
        if chat_dialog.can_continue():
            self.status = 'continue dialog'
            yield from chat_dialog.continue_()
            return
        handled = yield from self.handle_femi_dialog()
        if handled:
            return
        if is_upstairs() and not needs_bank_trip(self.current_plan()) and self.gear_ready:
            self.status = 'leaving bank stairs'
            yield from self.leave_bank_stairs()
            return
        prepped = yield from self.prep_wc_gear()
        if prepped:
            return
        if shop.is_open():
            yield from shop.close()
            return
        if bank.is_open():
            yield from bank.close()
            return
        plan = self.current_plan()
        self.plan_id = plan.id
        if chat_dialog.is_make_menu():
            if plan.fletch:
                yield from self.choose_make_product(plan)
            return
        if plan.fletch and log_count() > 0 and inventory.is_full():
            yield from self.fletch_logs(plan)
            return
        if plan.fletch and log_count() > 0 and game.animating() and bow_count() == 0 and self.find_tree_within(2) is None:
            self.status = f'fletching {plan.label}'
            yield from execution.delay_ticks(1)
            return
        if needs_bank_trip(plan):
            yield from self.bank_products_and_return()
            return
        here = game.tile()
        if here is None:
            yield from execution.delay_ticks(2)
            return
        if is_upstairs(here):
            yield from self.leave_bank_stairs()
            return
        if not in_gnome_area(here):
            self.status = 'walking to Gnome Stronghold'
            self.log(f'outside gnome, walking to gate {GNOME_ENTRANCE.x},{GNOME_ENTRANCE.z}')
            yield from traversal.walk_resilient(GNOME_ENTRANCE, radius=3, log=lambda m: self.log(f'  {m}'))
            yield from self.open_nearby_door(6)
            return
        if game.animating():
            self.status = 'chopping'
            yield from execution.delay_ticks(1)
            return
        tree = self.find_tree()
        if tree is None:
            yield from self.hop_tree_pin()
            return
        t = tree.tile()
        self.tree_pin_id = nearest_tree_pin(t).id
        if tree.distance() > CHOP_REACH:
            self.status = f'running to magic ({tree.distance()}t)'
            self.log(f'running to Magic tree @ {t.x},{t.z}')
            yield from traversal.walk_resilient(t, radius=2, log=lambda m: self.log(f'  {m}'))
            yield from self.open_nearby_door(5)
            return
        op = chop_op(tree.actions())
        if not op:
            self.log(f"Magic tree has no chop action: [{', '.join(tree.actions())}]")
            yield from execution.delay_ticks(2)
            return
        before = log_count()
        contested = other_players_near(t, 2)
        self.status = f'chopping contested ({tree.distance()}t)' if contested else f'chopping ({tree.distance()}t)'
        joining = f' ({contested} other player(s) on it, joining)' if contested else ''
        self.log(f'chopping Magic tree @ {t.x},{t.z}{joining}')
        tree.interact(op)
        started = yield from execution.delay_until(lambda: log_count() > before or game.animating() or chat_dialog.can_continue(), 8000)
        if log_count() > before:
            self.chopped += log_count() - before
        elif started and game.animating():
            yield from execution.delay_until(lambda: log_count() > before or not game.animating() or chat_dialog.can_continue(), 20000)
            if log_count() > before:
                self.chopped += log_count() - before

    def recovering(self):
        return self.died or self.recover_phase != RECOVER_NONE

    def stunned(self):
        return game.tick() <= self.stunned_until_tick

    def stop_no_knife(self, context):
        self.status = 'no knife, stopped'
        self.log(f'{context}: no Knife in inventory or gnome bank, stopping (withdraw a Knife, then restart)')
        self.request_finish(f'{context}: no Knife in inventory or gnome bank')

    def stop_no_axe(self, context):
        self.status = 'no axe, stopped'
        self.log(f'{context}: no usable axe in pack or gnome bank, stopping (withdraw an axe your Woodcutting can use, then restart)')
        self.request_finish(f'{context}: no usable axe in pack or gnome bank')

    def prep_wc_gear(self):
        """Whether this loop spent itself readying the gear. Use with yield from."""
        if chat_dialog.is_make_menu():
            return False
        if self.gear_ready and self.fletch_enabled() and not gear_has_knife():
            self.log('gear: Knife missing, checking gnome bank')
            self.gear_ready = False
        if self.gear_ready and gear_best_held_axe() is None and not gear_has_broken_axe():
            self.log('gear: axe missing, checking gnome bank')
            self.gear_ready = False
        if self.gear_ready:
            return False
        if shop.is_open():
            yield from shop.close()
            return True
        yield from self.bootstrap_wc_gear()
        return True

    def bootstrap_wc_gear(self):
        """Use with yield from."""
        self.status = 'gear: bank'
        if not in_gnome_area(game.tile()) and not is_upstairs():
            self.log('gear: walking to gnome bank')
            yield from traversal.walk_resilient(GNOME_ENTRANCE, radius=3, log=lambda m: self.log(f'  {m}'))
            return
        if not bank.is_open():
            self.log('gear: opening gnome bank for best axe / knife')
            opened = yield from self.open_gnome_bank()
            if not opened:
                self.log('gear: could not open gnome bank, retrying')
                yield from execution.delay_ticks(3)
                return
        yield from gear_wait_bank_loaded()
        self.log('gear: depositing all except Knife')
        yield from bank.deposit_all_matching(lambda name, *_args: name.lower() != 'knife')
        yield from execution.delay_ticks(1)
        best = best_axe(skills.level('woodcutting'), lambda n: gear_axe_count(n) > 0 or bank.count(n) > 0)
        if best is None:
            yield from bank.close()
            self.stop_no_axe('gear')
            return
        if gear_axe_count(best) == 0 and bank.count(best) > 0:
            self.log(f'gear: withdrawing {best}')
            took = yield from bank.withdraw_x(best, 1)
            if not took:
                self.log(f'gear: withdraw failed for {best}')
                yield from execution.delay_ticks(2)
                return
            yield from execution.delay_ticks(1)
        if self.fletch_enabled() and not gear_has_knife():
            if bank.count('Knife') == 0:
                yield from bank.close()
                self.stop_no_knife('gear')
                return
            self.log('gear: withdrawing Knife')
            yield from bank.withdraw_x('Knife', 1)
            yield from execution.delay_ticks(1)
        yield from bank.close()
        yield from execution.delay_ticks(1)
        yield from self.wield_best_axe()
        if self.fletch_enabled() and not gear_has_knife():
            self.stop_no_knife('gear')
            return
        if gear_best_held_axe() is None:
            self.log('gear: still missing axe after bank')
            yield from execution.delay_ticks(5)
            return
        self.gear_ready = True
        self.log(f'gear: ready, {gear_best_held_axe()}')
        yield from self.leave_bank_stairs()

    def wield_best_axe(self):
        """Use with yield from."""
        held = gear_best_held_axe()
        if held is None or equipment.contains(held):
            return
        if can_wield_tool(held, skills.level('attack')):
            self.status = f'gear: wield {held}'
            self.log(f'gear: wielding {held}')
            yield from equipment.equip(held)
            yield from execution.delay_ticks(1)
        else:
            self.log(f'gear: keeping {held} in pack (Attack too low to wield)')

    def find_climb_loc(self, near_tile, max_dist=12, direction=None):
        pin = near_tile if near_tile is not None else game.tile()
        want_floor = pin.level if pin is not None else player_floor()
        pool = locs.query().where(is_climb_loc).results()
        best = None
        best_d = 99
        for loc in pool:
            t = loc.tile()
            if not is_allowed_bank_stair_tile(t) or t.level != want_floor:
                continue
            if direction is not None and climb_op(loc, direction) is None:
                continue
            d = cheb(t, pin) if pin is not None else loc.distance()
            if d < best_d:
                best = loc
                best_d = d
        return best if best is not None and best_d <= max_dist else None

    def open_nearby_door(self, within=4):
        """Use with yield from."""
        door = locs.query().where(lambda l: is_shut_door(l) and l.distance() <= within).nearest()
        if door is None:
            return False
        self.status = f'opening {door.name}'
        self.log(f'opening {door.name}')
        door.interact(open_op(door))
        yield from execution.delay_ticks(2)
        return True

    def step_dialog(self, prefer, what='dialog'):
        """One step of a dialogue: continues, or picks by prefer. Use with yield from."""
        if chat_dialog.can_continue():
            self.status = 'continue dialog'
            yield from chat_dialog.continue_()
            yield from execution.delay_ticks(1)
            return True
        if chat_dialog.is_open() and len(chat_dialog.options()) > 0:
            opts = chat_dialog.options()
            pick = pick_boat_option(opts, prefer)
            self.status = f"dialog: {pick or '?'}"
            self.log(f"{what} → {pick}  [{' | '.join(opts)}]")
            yield from chat_dialog.choose_option(pick)
            yield from execution.delay_ticks(2)
            return True
        return False

    def handle_femi_dialog(self):
        """Use with yield from."""
        here = game.tile()
        if here is None or here.distance_to(GNOME_ENTRANCE) > 12:
            return False
        stepped = yield from self.step_dialog(FEMI_DIALOG_PREFER, 'gate dialog')
        return stepped

    def climb_bank_stairs(self, direction):
        """Use with yield from."""
        before_floor = player_floor()
        if (direction == 'up' and before_floor >= 1) or (direction == 'down' and before_floor <= 0):
            return True
        pin = nearest_bank_stair_pin(game.tile())
        stand = Tile(pin.x, pin.z, before_floor)
        loc = self.find_climb_loc(game.tile(), 8, direction) or self.find_climb_loc(stand, 8, direction)
        if loc is None:
            yield from self.open_nearby_door()
            loc = self.find_climb_loc(game.tile(), 8, direction) or self.find_climb_loc(stand, 8, direction)
        if loc is None:
            self.log(f'no allowed bank staircase to climb-{direction} (only {BANK_STAIR_SOUTH.x},{BANK_STAIR_SOUTH.z} or {BANK_STAIR_NORTH.x},{BANK_STAIR_NORTH.z})')
            yield from execution.delay_ticks(2)
            return False
        op = climb_op(loc, direction)
        if not op:
            self.log(f"{loc.name} has no Climb-{direction}: [{', '.join(loc.actions())}]")
            yield from execution.delay_ticks(2)
            return False
        self.status = f'{op} {loc.name}'
        self.log(f'{op} {loc.name} @ {loc.tile().x},{loc.tile().z} (bank stairs only)')
        loc.interact(op)
        moved = yield from execution.delay_until(lambda: player_floor() > before_floor if direction == 'up' else player_floor() < before_floor, 8000)
        if not moved:
            self.log(f'climb {direction} did not finish, retrying')
            yield from self.open_nearby_door()
            return False
        yield from execution.delay_ticks(1)
        return is_upstairs() if direction == 'up' else not is_upstairs()

    def walk_to_bank_stairs(self, skip_blocked=False):
        """Use with yield from."""
        here = game.tile()
        pin = nearest_bank_stair_pin(here, self.blocked_stair_pin if skip_blocked else None)
        if here is not None and cheb(here, pin) <= 2:
            return True
        self.status = 'walking to bank stairs'
        self.log(f'walking to bank stairs {pin.x},{pin.z} (only {BANK_STAIR_SOUTH.x},{BANK_STAIR_SOUTH.z} or {BANK_STAIR_NORTH.x},{BANK_STAIR_NORTH.z})')
        ok = yield from traversal.walk_resilient(Tile(pin.x, pin.z, player_floor(here)), radius=1, log=lambda m: self.log(f'  {m}'))
        if not ok:
            self.log('path to bank stairs failed, retrying')
            return False
        now = game.tile()
        return now is not None and cheb(now, pin) <= 3

    def walk_to_gnome_booths(self):
        """Use with yield from."""
        if not is_upstairs():
            return False
        if dist_to_booths(game.tile()) <= 3:
            return True
        self.status = 'walking to gnome booths'
        self.log(f'walking to central bank booths {BANK_STAND.x},{BANK_STAND.z},{BANK_STAND.level}')
        ok = yield from traversal.walk_resilient(BANK_STAND, radius=2, log=lambda m: self.log(f'  {m}'))
        if not ok:
            self.log('path to central booths failed, will try the other staircase')
            return False
        return is_upstairs() and dist_to_booths(game.tile()) <= 4

    def enter_bank_stairs(self):
        """Use with yield from."""
        if is_upstairs():
            return True
        at = yield from self.walk_to_bank_stairs(True)
        if not at:
            return False
        yield from self.open_nearby_door()
        up = yield from self.climb_bank_stairs('up')
        if up:
            self.log('upstairs, walking to central booths 2445,3425')
        return up

    def leave_bank_stairs(self):
        """Use with yield from."""
        if not is_upstairs():
            return True
        if dist_to_nearest_bank_stair(game.tile()) > 2:
            at = yield from self.walk_to_bank_stairs()
            if not at:
                return False
        self.status = 'climbing down bank stairs'
        self.log('climbing down allowed bank staircase')
        down = yield from self.climb_bank_stairs('down')
        if down:
            self.log('back on the ground, heading to magics')
        return down

    def open_gnome_bank(self):
        """Use with yield from."""
        if bank.is_open():
            if at_gnome_bank_floor():
                return True
            self.log('wrong bank open, closing')
            yield from bank.close()
            yield from execution.delay_ticks(1)
        entered = yield from self.enter_bank_stairs()
        if not entered or not is_upstairs():
            return False
        at = yield from self.walk_to_gnome_booths()
        if not at:
            self.blocked_stair_pin = nearest_bank_stair_pin(game.tile())
            self.log(f'could not reach booths {BANK_STAND.x},{BANK_STAND.z},1 from this staircase, will use the other allowed stairs next')
            yield from self.leave_bank_stairs()
            return False
        opened = yield from self.open_upstairs_booth()
        if opened:
            return True
        self.blocked_stair_pin = nearest_bank_stair_pin(game.tile())
        self.log('booths did not open, climbing down to try the other allowed staircase')
        yield from self.leave_bank_stairs()
        return False

    def find_gnome_booth(self):
        floor = player_floor()
        best = None
        best_d = 99
        for loc in locs.query().where(lambda l: booth_on_floor(l, floor)).results():
            d = cheb(loc.tile(), BANK_STAND)
            if booth_op(loc) and d < best_d and d <= BANK_BOOTH_REACH:
                best = loc
                best_d = d
        return best

    def open_upstairs_booth(self):
        """Use with yield from."""
        booth = self.find_gnome_booth()
        if booth is not None:
            op = booth_op(booth)
            t = booth.tile()
            self.status = f'opening {booth.name}'
            self.log(f'{op} {booth.name} @ {t.x},{t.z},{t.level}')
            booth.interact(op)
            opened = yield from execution.delay_until(bank.is_open, 8000)
            if opened:
                return True
        self.status = 'opening gnome bank'
        self.log(f'opening bank booth at {BANK_STAND.x},{BANK_STAND.z},{BANK_STAND.level}')
        opened = yield from bank.open_booth(BANK_STAND, 'Bank booth', 'Use-quickly')
        return opened

    def visible_magic_trees(self):
        trees = locs.query().where(lambda l: is_magic_tree_loc(l) and tree_on_ground(l)).results()
        if len(trees) == 0:
            one = locs.query().where(is_magic_tree_loc).within(TREE_SEARCH_REACH).nearest()
            if one is not None and in_tree_band(one.tile()):
                trees = [one]
        self.trees_up = len(trees)
        return trees

    def pick_tree(self, trees):
        """The nearest tree, one another player is on first: chopping alongside keeps it up no longer."""
        if len(trees) == 0:
            return None
        contested = [t for t in trees if other_players_near(t.tile(), 2) > 0]
        pool = contested if len(contested) > 0 else list(trees)
        pool.sort(key=lambda a: a.distance())
        return pool[0]

    def find_tree(self):
        return self.pick_tree(self.visible_magic_trees())

    def find_tree_within(self, max_dist):
        return self.pick_tree([t for t in self.visible_magic_trees() if t.distance() <= max_dist])

    def hop_tree_pin(self):
        """No magics in view: runs to the next of the three. Use with yield from."""
        pin = next_tree_pin(self.tree_pin_id)
        self.tree_pin_id = pin.id
        self.hops += 1
        self.status = f'no magics, {pin.name}'
        self.log(f'no Magic trees in view, running to {pin.name} {pin.tile.x},{pin.tile.z}')
        yield from traversal.walk_resilient(pin.tile, radius=3, log=lambda m: self.log(f'  {m}'))
        yield from self.open_nearby_door(5)

    def fletch_logs(self, plan):
        """Use with yield from."""
        if not plan.fletch or log_count() == 0:
            return
        if chat_dialog.is_make_menu():
            yield from self.choose_make_product(plan)
            return
        knife = knife_item()
        last = last_log()
        if knife is None:
            self.gear_ready = False
            self.log('WARNING: no Knife in inventory, will check gnome bank')
            yield from execution.delay_ticks(2)
            return
        if last is None:
            return
        self.status = f'fletching {plan.label}'
        self.log(f'knife → magic logs ({log_count()} left) for {plan.label}')
        before = log_count()
        if not knife.use_on(last):
            yield from execution.delay_ticks(2)
            return
        opened = yield from execution.delay_until(lambda: chat_dialog.is_make_menu() or log_count() < before or chat_dialog.can_continue() or game.animating(), 8000)
        if chat_dialog.is_make_menu():
            yield from self.choose_make_product(plan)
            return
        if not opened and log_count() >= before:
            self.log('fletch useOn did not start, retrying')

    def choose_make_product(self, plan):
        """Use with yield from."""
        if not plan.fletch:
            return
        products = chat_dialog.make_products()
        choice = match_make_product(products, plan.menu_match)
        if choice is None:
            self.log(f"make menu missing '{plan.label}' (have: [{', '.join(products)}]), closing")
            yield from execution.delay_ticks(2)
            return
        start = log_count()
        self.status = f'make {plan.label}'
        self.log(f"selecting '{choice}' x{start}")
        picked = yield from chat_dialog.make_x(choice, max(1, min(start, 30)))
        if not picked:
            picked = yield from chat_dialog.make(choice)
        if not picked:
            self.log(f"could not pick '{choice}' from make menu")
            yield from execution.delay_ticks(1)
            return
        yield from execution.delay_until(lambda: not chat_dialog.is_make_menu() and (game.animating() or log_count() < start or chat_dialog.can_continue()), 5000)
        mark = log_count()
        idle = 0
        for _ in range(400):
            if log_count() == 0 or chat_dialog.can_continue() or chat_dialog.is_make_menu():
                return
            yield from execution.delay_ticks(1)
            now = log_count()
            if now < mark:
                self.fletched += mark - now
                mark = now
                idle = 0
            elif game.animating():
                idle = 0
            else:
                idle += 1
                if idle >= 12:
                    return

    def bank_products_and_return(self):
        """Use with yield from."""
        bows = bow_count()
        shorts = shortbow_count()
        logs = log_count()
        self.status = 'banking'
        parts = (f' {shorts} Magic shortbow' if shorts else '') + (f' {bows - shorts} Magic longbow' if bows - shorts > 0 else '') + (f' {logs} Magic logs' if logs else '')
        self.log(f"banking{parts} (fletching {skills.level('fletching')})")
        if not bank.is_open():
            opened = yield from self.open_gnome_bank()
            if not opened:
                self.log('could not open gnome bank, retrying')
                yield from execution.delay_ticks(3)
                return
        yield from gear_wait_bank_loaded()
        yield from bank.deposit_all_matching(lambda name, *_args: not is_keep_tool(name))
        yield from execution.delay_ticks(1)
        yield from self.restock_essentials_from_open_bank()
        yield from bank.close()
        yield from execution.delay_ticks(1)
        self.bank_trips += 1
        self.status = 'returning to magics'
        yield from self.leave_bank_stairs()

    def restock_essentials_from_open_bank(self):
        """Use with yield from."""
        need_knife = self.fletch_enabled()
        if bank.is_open():
            yield from execution.delay_until(lambda: bank.loaded() or not bank.is_open(), 3000)
        if not bank.is_open():
            return has_essentials_after_bank(need_knife)
        if need_knife and not gear_has_knife():
            if bank.count('Knife') == 0:
                if self.recovering():
                    self.log('death: Knife not in this bank, will retry restock')
                else:
                    self.stop_no_knife('banking')
                return False
            self.log('gear: withdrawing Knife')
            yield from bank.withdraw_x('Knife', 1)
            yield from execution.delay_ticks(1)
        if not gear_has_broken_axe() and gear_best_held_axe() is None:
            wc = skills.level('woodcutting')
            best = best_axe(wc, lambda n: bank.count(n) > 0)
            if best is not None:
                self.log(f'gear: withdrawing {best}')
                yield from bank.withdraw_x(best, 1)
                yield from execution.delay_ticks(1)
            else:
                self.log(f'gear: WARNING, no usable axe in bank for WC {wc}')
        return has_essentials_after_bank(need_knife)

    # After a death.

    def wait_for_respawn(self):
        """Use with yield from."""
        self.status = 'waiting for respawn'
        ready = yield from execution.delay_until(lambda: game.ingame() and game.tile() is not None, 20000)
        if not ready:
            self.log('still waiting for respawn...')
            return
        yield from execution.delay_ticks(3)
        self.died = False
        self.recover_phase = RECOVER_KNIFE
        here = game.tile()
        self.log(f'respawned at {here.x},{here.z} ({region_of(here)}), grab Knife, 500gp, Steel axe, then SneakyArdougne back to gnome magics')
        self.status = 'death: knife spawn'

    def recover_from_death(self):
        """Use with yield from."""
        phase = self.recover_phase
        if shop.is_open() and phase != RECOVER_BUY_AXE:
            yield from shop.close()
            return
        if phase == RECOVER_KNIFE:
            yield from self.recover_pickup_knife()
        elif phase == RECOVER_BANK_GP:
            yield from self.recover_withdraw_gp()
        elif phase == RECOVER_BUY_AXE:
            yield from self.recover_buy_steel()
        elif phase == RECOVER_BANK_TOOLS:
            yield from self.recover_bank_tools()
        elif phase == RECOVER_TRAVEL:
            yield from self.return_via_sneaky()
        elif phase == RECOVER_RESTOCK:
            yield from self.recover_restock()
        else:
            self.recover_phase = RECOVER_KNIFE
            yield from execution.delay_ticks(1)

    def recover_pickup_knife(self):
        """Use with yield from."""
        if gear_has_knife():
            self.log('death: already have Knife, nearest bank for 500gp')
            self.recover_phase = RECOVER_BANK_GP
            return
        self.status = 'death: knife spawn'
        self.log('death: walking to Lumbridge knife spawn (beside castle / behind Bob)')
        yield from traversal.walk_resilient(GEAR_KNIFE_SPAWN, radius=1, log=lambda m: self.log(f'  {m}'))
        ground = ground_items.query().name('Knife').within(6).nearest()
        if ground is None:
            yield from execution.delay_ticks(3)
            ground = ground_items.query().name('Knife').within(6).nearest()
        if ground is None:
            self.log('death: Knife not on ground yet, waiting')
            yield from execution.delay_ticks(5)
            return
        if inventory.is_full():
            self.log('death: inventory full, banking first')
            self.recover_phase = RECOVER_BANK_GP
            return
        self.log('death: taking Knife')
        ground.interact('Take')
        yield from execution.delay_until(gear_has_knife, 8000)
        if gear_has_knife():
            self.log('death: Knife acquired, nearest bank for 500gp')
            self.recover_phase = RECOVER_BANK_GP

    def recover_withdraw_gp(self):
        """Use with yield from."""
        self.status = 'death: 500gp'
        if not bank.is_open():
            self.log('death: opening nearest bank for 500gp')
            opened = yield from banking.open(log=lambda m: self.log(f'  {m}'))
            if not opened:
                self.log('death: could not open bank, retrying')
                yield from execution.delay_ticks(3)
                return
        yield from gear_wait_bank_loaded()
        yield from bank.deposit_all_matching(lambda name, *_args: name.lower() != 'knife' and name.lower() != 'coins')
        yield from execution.delay_ticks(1)
        have = gear_inv_coins()
        if have < DEATH_GP:
            banked = bank.count('Coins')
            if banked <= 0:
                self.log(f'death: only {have}gp on us and none in bank, taking what we have')
            else:
                take = min(DEATH_GP - have, banked)
                self.log(f'death: withdrawing {take}gp ({have} held, need {DEATH_GP})')
                yield from bank.withdraw_x('Coins', take)
                yield from execution.delay_ticks(1)
        else:
            self.log(f'death: already holding {have}gp')
        coins = gear_inv_coins()
        own_steel = gear_has_steel_or_better()
        yield from bank.close()
        yield from execution.delay_ticks(1)
        if own_steel:
            self.log('death: already own steel+ axe, banking Knife then boats')
            self.recover_phase = RECOVER_BANK_TOOLS
            return
        if coins < GEAR_STEEL_COST:
            self.log(f'death: only {coins}gp (need {GEAR_STEEL_COST} for Steel axe), will retry bank')
            yield from execution.delay_ticks(5)
            return
        self.log(f'death: {coins}gp in pack, buying Steel axe from Bob')
        self.recover_phase = RECOVER_BUY_AXE

    def recover_buy_steel(self):
        """Use with yield from."""
        if gear_has_steel_or_better():
            self.recover_phase = RECOVER_BANK_TOOLS
            return
        if not shop.is_open():
            self.status = 'death: Bob'
            self.log('death: walking to Bob for Steel axe')
            yield from traversal.walk_resilient(GEAR_BOB_STAND, radius=2, log=lambda m: self.log(f'  {m}'))
            opened = yield from shop.open('Bob')
            if not opened:
                self.log("death: could not open Bob's shop")
                yield from execution.delay_ticks(3)
                return
        yield from self.buy_steel_at_open_shop()
        if gear_has_steel_or_better():
            self.recover_phase = RECOVER_BANK_TOOLS

    def buy_steel_at_open_shop(self):
        """Use with yield from."""
        if gear_has_steel_or_better():
            self.log('gear: already own steel+ axe, closing Bob')
            yield from shop.close()
            return
        self.status = 'gear: buy steel'
        before = gear_axe_count(GEAR_STEEL_AXE)
        bought = yield from shop.buy(GEAR_STEEL_AXE, 1)
        got = bought if bought > 0 else max(0, gear_axe_count(GEAR_STEEL_AXE) - before)
        if got <= 0:
            self.log('gear: Steel axe buy failed (stock/coins?)')
            yield from shop.close()
            yield from execution.delay_ticks(5)
            return
        self.log('gear: bought Steel axe from Bob')
        yield from shop.close()
        yield from execution.delay_ticks(1)
        if not equipment.contains(GEAR_STEEL_AXE) and can_wield_tool(GEAR_STEEL_AXE, skills.level('attack')):
            yield from equipment.equip(GEAR_STEEL_AXE)

    def recover_bank_tools(self):
        """Banks the axe and knife, keeping the coins for the boats. Use with yield from."""
        self.status = 'death: bank tools'
        held = gear_best_held_axe()
        if held is not None and equipment.contains(held) and not inventory.is_full():
            self.log(f'death: unequipping {held} to bank it')
            yield from equipment.unequip(held)
            yield from execution.delay_ticks(1)
        if not bank.is_open():
            self.log('death: banking Steel axe + Knife (keep coins for boats)')
            opened = yield from banking.open(log=lambda m: self.log(f'  {m}'))
            if not opened:
                yield from execution.delay_ticks(3)
                return
        yield from gear_wait_bank_loaded()
        yield from bank.deposit_all_matching(lambda name, *_args: name.lower() != 'coins')
        yield from execution.delay_ticks(1)
        knife_banked = bank.count('Knife') > 0
        axe_banked = gear_has_steel_or_better()
        coins = gear_inv_coins()
        yield from bank.close()
        yield from execution.delay_ticks(1)
        if not knife_banked:
            if gear_has_knife():
                self.log('death: Knife still in pack, retrying deposit')
                return
            self.log('death: Knife not in bank, grabbing another from the spawn')
            self.recover_phase = RECOVER_KNIFE
            return
        if not axe_banked:
            self.log('death: no steel+ axe in bank, buying from Bob')
            self.recover_phase = RECOVER_BUY_AXE
            return
        if coins < GP_TARGET:
            self.log(f'death: only {coins}gp for boats, withdrawing more')
            self.recover_phase = RECOVER_BANK_GP
            return
        self.log(f'death: tools banked, {coins}gp for boats, SneakyArdougne to gnome')
        self.travel_phase = self.infer_travel_phase()
        self.recover_phase = RECOVER_TRAVEL

    def infer_travel_phase(self):
        region = region_of(game.tile())
        coins = gear_inv_coins()
        if region == 'gnome' or region == 'ardougne' or region == 'seers':
            return PHASE_DONE
        if region == 'brimhaven':
            return PHASE_BOAT_ARDOUGNE
        if region == 'musa' or region == 'karamja':
            return PHASE_WALK_BRIMHAVEN
        if region == 'sarim':
            return PHASE_BOAT_KARAMJA if coins >= BOAT_FARE else PHASE_WALK_SARIM
        return PHASE_WALK_SARIM if coins >= GP_TARGET else PHASE_THIEVE

    def arrived_kandarin(self):
        self.travel_phase = PHASE_DONE
        self.recover_phase = RECOVER_RESTOCK

    def return_via_sneaky(self):
        """Use with yield from."""
        if self.travel_phase is None or self.travel_phase == PHASE_DONE:
            self.travel_phase = self.infer_travel_phase()
            self.log(f'death: SneakyArdougne, phase {self.travel_phase} · {gear_inv_coins()}gp')
        prefer = ARDOUGNE_DIALOG_PREFER if self.travel_phase == PHASE_BOAT_ARDOUGNE or region_of(game.tile()) == 'brimhaven' else KARAMJA_DIALOG_PREFER
        stepped = yield from self.step_dialog(prefer)
        if stepped:
            return
        if self.travel_phase != PHASE_THIEVE:
            inferred = self.infer_travel_phase()
            if inferred == PHASE_DONE or (inferred == PHASE_WALK_BRIMHAVEN and self.travel_phase == PHASE_BOAT_KARAMJA) or (inferred == PHASE_BOAT_ARDOUGNE and self.travel_phase == PHASE_WALK_BRIMHAVEN):
                self.travel_phase = inferred
        region = region_of(game.tile())
        if self.travel_phase == PHASE_DONE or region == 'ardougne' or region == 'seers' or region == 'gnome':
            self.arrived_kandarin()
            self.status = 'death: arrived Kandarin'
            self.log('death: arrived via boats, walk to gnome, withdraw Steel axe + Knife')
            return
        phase = self.travel_phase
        if phase == PHASE_THIEVE:
            yield from self.do_thieve()
        elif phase == PHASE_WALK_SARIM:
            yield from self.do_walk_sarim()
        elif phase == PHASE_BOAT_KARAMJA:
            yield from self.do_boat_karamja()
        elif phase == PHASE_WALK_BRIMHAVEN:
            yield from self.do_walk_brimhaven()
        elif phase == PHASE_BOAT_ARDOUGNE:
            yield from self.do_boat_ardougne()
        else:
            self.travel_phase = self.infer_travel_phase()
            yield from execution.delay_ticks(2)

    def talk_sailor_and_ride(self, npc, prefer, arrived):
        """Use with yield from."""
        before = game.tile()
        self.status = f"Talk-to {npc.name or 'sailor'}"
        self.log(f'Talk-to {npc.name} @ dock ({gear_inv_coins()}gp), navigating dialogue')
        if not npc.interact(npc_talk_op(npc)):
            yield from execution.delay_ticks(2)
            return False
        opened = yield from execution.delay_until(lambda: dialog_open() or arrived() or moved_far(before, 15), 8000)
        if not opened:
            self.log('sailor dialog did not open, retrying')
            return False
        for _ in range(40):
            if self.died:
                return False
            if arrived():
                return True
            if not dialog_open():
                came = yield from execution.delay_until(lambda: arrived() or moved_far(before, 15) or dialog_open(), 6000)
                if came and (arrived() or dialog_open()):
                    if arrived():
                        return True
                    continue
                break
            stepped = yield from self.step_dialog(prefer)
            if not stepped:
                yield from execution.delay_ticks(1)
        if arrived():
            return True
        yield from self.cross_gangplank()
        return arrived()

    def do_thieve(self):
        """Use with yield from."""
        if gear_inv_coins() >= GP_TARGET:
            self.log(f'have {gear_inv_coins()}gp (≥ {GP_TARGET}), heading to Port Sarim')
            self.travel_phase = PHASE_WALK_SARIM
            self.status = 'walk Port Sarim'
            return
        if skills.effective('hitpoints') < MIN_HP:
            self.status = f"HP {skills.effective('hitpoints')}, regen to {MIN_HP}"
            yield from execution.delay_ticks(2)
            return
        if self.stunned():
            self.status = 'stunned'
            yield from execution.delay_ticks(1)
            return
        here = game.tile()
        if here is None:
            yield from execution.delay_ticks(2)
            return
        if here.distance_to(LUMBY_MEN) > LUMBY_LEASH:
            self.status = 'walking to Lumbridge Men'
            yield from traversal.walk_resilient(LUMBY_MEN, radius=4, log=lambda m: self.log(f'  {m}'))
            return
        if game.in_combat():
            self.status = 'in combat, waiting'
            yield from execution.delay_ticks(2)
            return
        man = npcs.query().name('Man').action(PICKPOCKET_OP).within(LUMBY_LEASH + 4).where(lambda n: not n.in_combat).nearest()
        if man is None:
            self.status = 'waiting for Man'
            yield from traversal.walk_to(LUMBY_MEN, radius=3, timeout_ms=8000)
            yield from self.open_nearby_door()
            yield from execution.delay_ticks(2)
            return
        before_xp = skills.xp('thieving')
        coins_before = gear_inv_coins()
        t = man.tile()
        self.status = f'pickpocket Man ({man.distance()}t) · {coins_before}gp'
        self.log(f"Pickpocket Man @ {t.x},{t.z} · {coins_before}gp · HP {skills.effective('hitpoints')}")
        if not man.interact(PICKPOCKET_OP):
            yield from self.open_nearby_door()
            yield from execution.delay_ticks(1)
            return
        yield from execution.delay_until(lambda: skills.xp('thieving') > before_xp or self.stunned() or game.in_combat() or chat_dialog.can_continue()
                                         or gear_inv_coins() > coins_before or self.died, 4000)

    def do_walk_sarim(self):
        """Use with yield from."""
        here = game.tile()
        if here is not None and PORT_SARIM_DOCK.distance_to(here) <= 6:
            self.travel_phase = PHASE_BOAT_KARAMJA
            self.status = 'boat to Karamja'
            return
        self.status = 'walking to Port Sarim'
        self.log(f'walking to Port Sarim dock @ {PORT_SARIM_DOCK.x},{PORT_SARIM_DOCK.z}')
        yield from traversal.walk_resilient(PORT_SARIM_DOCK, radius=4, log=lambda m: self.log(f'  {m}'))
        after = game.tile()
        if after is not None and PORT_SARIM_DOCK.distance_to(after) <= 6:
            self.travel_phase = PHASE_BOAT_KARAMJA

    def at_karamja(self):
        r = region_of(game.tile())
        return r == 'musa' or r == 'karamja'

    def in_ardougne(self):
        return region_of(game.tile()) == 'ardougne'

    def ride(self, sailor_finder, dock, prefer, arrived, landed):
        """Takes the boat from the dock: through an open dialogue, else from a sailor found there. Use with yield from."""
        if dialog_open():
            for _ in range(40):
                if not dialog_open() or arrived() or self.died:
                    break
                yield from self.step_dialog(prefer)
            if arrived():
                landed()
            return
        sailor = sailor_finder()
        if sailor is None:
            self.status = 'looking for sailor'
            yield from traversal.walk_resilient(dock, radius=3, timeout_ms=10000, log=lambda m: self.log(f'  {m}'))
            yield from execution.delay_ticks(2)
            return
        ok = yield from self.talk_sailor_and_ride(sailor, prefer, arrived)
        if ok or arrived():
            landed()

    def landed_karamja(self):
        self.travel_phase = PHASE_WALK_BRIMHAVEN
        self.log('boat landed on Karamja')

    def landed_ardougne(self):
        self.arrived_kandarin()
        self.log('boat landed in Ardougne')

    def do_boat_karamja(self):
        """Use with yield from."""
        if self.at_karamja():
            self.log('arrived Musa Point / Karamja, walking to Brimhaven')
            self.travel_phase = PHASE_WALK_BRIMHAVEN
            return
        if gear_inv_coins() < BOAT_FARE:
            self.status = 'need 30gp for Sarim boat'
            self.log(f'WARNING: only {gear_inv_coins()}gp, need 30 for Port Sarim → Karamja')
            self.travel_phase = PHASE_THIEVE
            yield from execution.delay_ticks(5)
            return
        yield from self.ride(self.find_sarim_sailor, PORT_SARIM_DOCK, KARAMJA_DIALOG_PREFER, self.at_karamja, self.landed_karamja)

    def find_sarim_sailor(self):
        for name in SARIM_SAILORS:
            npc = npcs.query().name(name).within(18).nearest()
            if npc is not None:
                return npc
        return npcs.query().within(18).where(sailor_like).nearest()

    def do_walk_brimhaven(self):
        """Use with yield from."""
        here = game.tile()
        if (here is not None and BRIMHAVEN_DOCK.distance_to(here) <= 8) or region_of(here) == 'brimhaven':
            self.travel_phase = PHASE_BOAT_ARDOUGNE
            self.status = 'boat to Ardougne'
            return
        self.status = 'walking to Brimhaven'
        self.log(f'walking Musa/Karamja → Brimhaven dock @ {BRIMHAVEN_DOCK.x},{BRIMHAVEN_DOCK.z}')
        yield from traversal.walk_resilient(BRIMHAVEN_DOCK, radius=5, log=lambda m: self.log(f'  {m}'))
        yield from self.open_nearby_door()
        after = game.tile()
        if after is not None and (BRIMHAVEN_DOCK.distance_to(after) <= 8 or region_of(after) == 'brimhaven'):
            self.travel_phase = PHASE_BOAT_ARDOUGNE

    def do_boat_ardougne(self):
        """Use with yield from."""
        if self.in_ardougne():
            self.log('arrived Ardougne')
            self.arrived_kandarin()
            return
        if gear_inv_coins() < BOAT_FARE:
            self.status = 'need 30gp for Brimhaven boat'
            self.log(f'WARNING: only {gear_inv_coins()}gp, need 30 for Brimhaven → Ardougne')
            yield from execution.delay_ticks(8)
            return
        yield from self.ride(self.find_brim_sailor, BRIMHAVEN_DOCK, ARDOUGNE_DIALOG_PREFER, self.in_ardougne, self.landed_ardougne)

    def find_brim_sailor(self):
        for name in BRIM_SAILORS:
            npc = npcs.query().name(name).within(18).nearest()
            if npc is not None:
                return npc
        customs = npcs.query().within(18).where(lambda n: 'customs' in (n.name or '').lower()).nearest()
        if customs is not None:
            return customs
        return npcs.query().within(18).where(sailor_like).nearest()

    def cross_gangplank(self):
        """Use with yield from."""
        plank = locs.query().within(10).where(lambda l: 'gangplank' in (l.name or '').lower()).nearest()
        if plank is None:
            return False
        acts = plank.actions()
        op = first_action(acts, lambda a: 'cross' in a or 'walk' in a or 'climb' in a) or (acts[0] if len(acts) > 0 else None)
        if not op:
            return False
        before = game.tile()
        self.status = f'cross {plank.name}'
        self.log(f'crossing {plank.name} ({op})')
        if not plank.interact(op):
            return False
        yield from execution.delay_until(lambda: moved_far(before, 3), 6000)
        return True

    def recover_restock(self):
        """Use with yield from."""
        here = game.tile()
        if not in_gnome_area(here) and not is_upstairs(here):
            self.status = 'death: walk to gnome'
            self.log(f'death: walking to Gnome Stronghold gate {GNOME_ENTRANCE.x},{GNOME_ENTRANCE.z}')
            yield from traversal.walk_resilient(GNOME_ENTRANCE, radius=3, log=lambda m: self.log(f'  {m}'))
            yield from self.open_nearby_door(6)
            yield from self.handle_femi_dialog()
            return
        self.status = 'death: withdraw axe + knife'
        self.log('death: gnome bank, withdraw Steel axe + Knife, then chop')
        if not bank.is_open():
            opened = yield from self.open_gnome_bank()
            if not opened:
                self.log('death: could not open gnome bank, retrying')
                yield from execution.delay_ticks(3)
                return
        yield from gear_wait_bank_loaded()
        yield from bank.deposit_all_matching(lambda name, *_args: not is_keep_tool(name))
        yield from execution.delay_ticks(1)
        yield from self.restock_essentials_from_open_bank()
        yield from bank.close()
        yield from execution.delay_ticks(1)
        if not has_essentials_after_bank(self.fletch_enabled()):
            self.log('death: restock incomplete, will retry gnome bank')
            yield from execution.delay_ticks(5)
            return
        yield from self.wield_best_axe()
        self.gear_ready = True
        self.recover_phase = RECOVER_NONE
        self.travel_phase = PHASE_DONE
        self.tree_pin_id = 'bank'
        self.log('death: restocked axe + Knife, resuming gnome magics')
        self.status = 'returning to magics'
        yield from self.leave_bank_stairs()

    def on_stop(self, reason=None):
        self.log(f'stopped, chopped ~{self.chopped}, fletched ~{self.fletched}, bank trips {self.bank_trips}, hops {self.hops}, deaths {self.deaths} ({self.status})')

    def on_progress_report(self):
        minutes = (time.time() - self.started_at) / 60
        wc = skills.xp('woodcutting') - self.wc_xp_at_start
        return {'Status': self.status, 'Chopped': self.chopped, 'Fletched': self.fletched, 'Woodcutting xp': wc,
                'WC xp/hr': f'{wc / minutes * 60 / 1000:.1f}k' if minutes > 0.5 else '—', 'Fletching xp': skills.xp('fletching') - self.fletch_xp_at_start,
                'Bank trips': self.bank_trips, 'Hops': self.hops, 'Trees up': self.trees_up, 'Deaths': self.deaths, 'Plan': self.plan_id}


BOT = define_bot(
    name='GnomeMagicChopper',
    create=GnomeMagicChopper,
    description='Locates every Magic tree in Tree Gnome Stronghold (west 2372,3425 / south-bank 2433,3410 / east 2491,3413), runs to the nearest one that is up, and chops it. If none are up it hops to the next pin. Banks at the upstairs gnome booths (stairs 2444,3416 and 2445,3443 only). If fletching is on: magic shortbows at 80 / longbows at 85. On death: Lumbridge knife spawn, 500gp, Steel axe from Bob, SneakyArdougne boats, then gnome restock.',
    category='Woodcutting',
    tags=['woodcutting', 'fletching', 'magic', 'gnome', 'stronghold', 'shortbow', 'longbow', 'death-recovery'],
    settings_schema=SETTINGS,
)
