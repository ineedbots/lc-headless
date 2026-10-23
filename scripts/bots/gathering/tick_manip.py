"""GatheringBot's optional tick manipulation, on this revision's server timings: rs2b0t's
scripts/GatheringBot/TickManipLogic.ts (MIT, see thirdparty/rs2b0t). The client can't read the server's action
delay, so a profile infers it from xp, the inventory and tick edges. It hasn't shipped in rs2b0t: every setting
resolves to Off."""

import math

from rs2004.catalogs import Record

TICK_MANIP_SHIPPED = False
TICK_MANIP_KNIFE = 'Knife'
FLETCHABLE_LOG_NAMES = ['Logs', 'Oak logs', 'Willow logs', 'Maple logs', 'Yew logs', 'Magic logs']
# Why: oak and up offer only bows, so arming the knife delay falls back to the first product; Make X is never used
# to arm it.
KNIFE_DELAY_MAKE_MATCH = 'shaft'
FISH_TICK_MANIP_OPTIONS = ['Off', '4t fly reclick', 'Knife delay (+2)', 'Tannerfishing']
MINE_TICK_MANIP_OPTIONS = ['Off', 'Iron cadence (pick-aware)']
WC_TICK_MANIP_OPTIONS = ['Off', 'Knife delay (+2)', '2t retaliate oaks', '3t farmer willows', '3t willows shortbow rapid']
TICK_MANIP_UNSHIPPED_HELP = 'Tick methods are not shipped yet (WIP). Leave Off — AFK gather only. Non-Off values in saved settings are ignored.'
SHORTBOW_NAMES = ['Shortbow', 'Oak shortbow', 'Willow shortbow', 'Maple shortbow', 'Yew shortbow', 'Magic shortbow']
TANNERFISH_EAT_HP = 0.55


def profile(skill, overrides=None):
    """A profile: Off, with overrides."""
    fields = {
        'skill': skill, 'method': 'off', 'label': 'Off', 'combat': 'flee', 'allow_combat': False, 'use_knife_delay': False, 'timed_reclick': False,
        'shortbow_rapid': False, 'native_cycle_ticks': None, 'farmer_willow_cycle': False, 'cook_eat_interleave': False, 'may_die': False,
    }
    for k, v in (overrides or {}).items():
        fields[k] = v
    return Record(fields)


def off_profile(skill):
    return profile(skill)


MAY_DIE = {'combat': 'retaliate-may-die', 'allow_combat': True, 'may_die': True}


def with_fields(base, more):
    out = {}
    for k, v in base.items():
        out[k] = v
    for k, v in more.items():
        out[k] = v
    return out


def parse_fish_tick_manip(label):
    n = label.strip().lower()
    if n in ['4t fly reclick', '4t fly', '4t-fly']:
        return '4t-fly'
    if n in ['knife delay (+2)', 'knife delay', 'knife-delay', '3t knife']:
        return 'knife-delay'
    if n in ['tannerfishing', 'tannerfish', 'gnome stronghold']:
        return 'tannerfish'
    return 'off'


def parse_mine_tick_manip(label):
    n = label.strip().lower()
    if n in ['iron cadence (pick-aware)', 'iron cadence', '4t iron', '4t-iron', 'iron-cadence']:
        return 'iron-cadence'
    return 'off'


def parse_wc_tick_manip(label):
    n = label.strip().lower()
    if n in ['knife delay (+2)', 'knife delay', 'knife-delay']:
        return 'knife-delay'
    if n in ['2t retaliate oaks', '2t oaks', '2t-oaks']:
        return '2t-oaks'
    if n in ['3t farmer willows', '3t farmer', '3t-farmer']:
        return '3t-farmer'
    if n in ['3t willows shortbow rapid', '3t shortbow', '3t-shortbow', 'shortbow rapid']:
        return '3t-shortbow'
    return 'off'


def method_label(skill, method):
    if method == 'off':
        return 'Off'
    if skill == 'fish':
        options, parse = FISH_TICK_MANIP_OPTIONS, parse_fish_tick_manip
    elif skill == 'mine':
        options, parse = MINE_TICK_MANIP_OPTIONS, parse_mine_tick_manip
    else:
        options, parse = WC_TICK_MANIP_OPTIONS, parse_wc_tick_manip
    for o in options:
        if parse(o) == method:
            return o
    return method


def fish_tick_manip_profile(method, label=None):
    named = {'method': method, 'label': label if label is not None else method_label('fish', method)}
    if method == '4t-fly':
        return profile('fish', with_fields(named, {'timed_reclick': True, 'native_cycle_ticks': 4}))
    if method == 'knife-delay':
        return profile('fish', with_fields(named, {'use_knife_delay': True, 'native_cycle_ticks': 4}))
    if method == 'tannerfish':
        return profile('fish', with_fields(with_fields(named, MAY_DIE), {'cook_eat_interleave': True, 'native_cycle_ticks': 4}))
    return off_profile('fish')


def mine_tick_manip_profile(method, label=None):
    if method == 'iron-cadence':
        return profile('mine', {'method': method, 'label': label if label is not None else method_label('mine', method), 'timed_reclick': True})
    return off_profile('mine')


def wc_tick_manip_profile(method, label=None):
    named = {'method': method, 'label': label if label is not None else method_label('wc', method)}
    if method == 'knife-delay':
        return profile('wc', with_fields(named, {'use_knife_delay': True, 'native_cycle_ticks': 3}))
    if method == '2t-oaks':
        return profile('wc', with_fields(with_fields(named, MAY_DIE), {'native_cycle_ticks': 2}))
    if method == '3t-farmer':
        return profile('wc', with_fields(with_fields(named, MAY_DIE), {'farmer_willow_cycle': True, 'native_cycle_ticks': 6}))
    if method == '3t-shortbow':
        return profile('wc', with_fields(with_fields(named, MAY_DIE), {'shortbow_rapid': True, 'native_cycle_ticks': 3}))
    return off_profile('wc')


def tick_manip_ui_options(full):
    """A skill's settings options: only Off until tick manipulation ships."""
    return list(full) if TICK_MANIP_SHIPPED else ['Off']


# Why: while it hasn't shipped this is always Off and the label is ignored; tests of the methods call the profile
# builders directly.
def profile_for_setting(skill, label):
    """The runtime profile a settings label resolves to."""
    if not TICK_MANIP_SHIPPED:
        return off_profile(skill)
    name = label.strip() or 'Off'
    if skill == 'fish':
        return fish_tick_manip_profile(parse_fish_tick_manip(label), name)
    if skill == 'mine':
        return mine_tick_manip_profile(parse_mine_tick_manip(label), name)
    return wc_tick_manip_profile(parse_wc_tick_manip(label), name)


def mining_rate_for_pickaxe(pick_name):
    """A pickaxe's mining_rate, from the server's pickaxes.obj; bare hands are as slow as bronze."""
    n = (pick_name or '').lower()
    for metal, rate in [('rune', 2), ('adamant', 3), ('mithril', 4), ('steel', 5), ('iron', 6)]:
        if metal in n:
            return rate
    return 7


# Why: the server sets the delay to its clock plus N when it's run out, and rolls when they're equal, so the click
# lands on the roll's tick, or the one after when the client is a beat late.
def next_gather_click_tick(roll_tick, cycle_ticks, late_slack=0):
    """When to click the resource again after a roll at roll_tick, for a fixed cycle."""
    return math.floor(roll_tick) + max(1, math.floor(cycle_ticks)) + max(0, math.floor(late_slack))


# Why: at the arm tick the knife goes on a log with Make-1, which sets the delay two ticks out; the tick after, the
# resource is clicked again while the delay holds; the tick after that it runs out and the roll opens. The arm
# tick is often stamped at the last roll, when the bot reacts on that tick.
def knife_delay_phase(now_tick, arm_tick):
    now = math.floor(now_tick)
    arm = math.floor(arm_tick)
    if now == arm + 1:
        return 'reclick'
    # At or before the arm tick, or past the click's window: arm again rather than idle.
    return 'delay-action'


def farmer_willow_phase(now_tick, cycle_start_tick):
    phase = ((math.floor(now_tick) - math.floor(cycle_start_tick)) % 6 + 6) % 6
    if phase == 0:
        return 'click-tree'
    if phase == 4:
        return 'cut-log'
    if phase == 5:
        return 'drop-log'
    return 'wait'


def combat_breaks_gather(in_combat, allow_combat):
    """Whether combat interrupts a gather wait for the profile."""
    return in_combat and not allow_combat


def is_fletchable_log_name(name):
    n = (name or '').strip().lower()
    return n in [l.lower() for l in FLETCHABLE_LOG_NAMES]


def extra_delay_logs_to_drop(log_count, keep=1):
    """The delay logs to drop, keeping one."""
    return max(0, max(0, math.floor(log_count)) - max(0, math.floor(keep)))


def is_shortbow_name(name):
    return 'shortbow' in (name or '').lower()


def should_eat_for_tannerfish(hp_fraction, has_cooked):
    """Whether Tannerfishing spends a beat eating cooked fish."""
    return has_cooked and hp_fraction < TANNERFISH_EAT_HP


def should_cook_for_tannerfish(raw_count, cooked_count, free_slots, hp_fraction):
    """Whether to cook a raw catch, for space or a small buffer of food."""
    if raw_count <= 0:
        return False
    # Room is tight: at least one.
    if free_slots <= 2:
        return True
    # A small cooked buffer while HP isn't full.
    if cooked_count < 2 and hp_fraction < 0.9:
        return True
    # Otherwise, with several raw.
    return raw_count >= 3 and cooked_count < 4
