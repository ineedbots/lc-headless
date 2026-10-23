"""The fisher's cooking decisions: rs2b0t's scripts/GatheringBot/FishCookLogic.ts (MIT, see thirdparty/rs2b0t)."""

import math
import random

from bots.gathering.camp import is_number

COOK_MODE_OPTIONS = ['Off', 'Cook then bank', 'Bank raw then cook']
BURNT_POLICY_OPTIONS = ['Drop', 'Bank']
AFTER_COOK_OPTIONS = ['Stop', 'Continue']
COOK_FISH_OPTIONS = ['All raw', 'Tuna', 'Swordfish', 'Lobster', 'Shark', 'Salmon', 'Trout', 'Shrimps', 'Anchovies', 'Custom']
COOKED_FISH_NAMES = ['shrimps', 'anchovies', 'sardine', 'herring', 'mackerel', 'trout', 'cod', 'pike', 'salmon', 'tuna', 'lobster', 'bass', 'swordfish',
                     'shark', 'manta ray', 'sea turtle', 'karambwan']


def parse_cook_mode(label):
    n = label.strip().lower()
    if n == 'cook then bank':
        return 'cook-then-bank'
    if n == 'bank raw then cook':
        return 'bank-raw-then-cook'
    return 'off'


def parse_burnt_policy(label):
    return 'bank' if label.strip().lower() == 'bank' else 'drop'


def parse_after_cook_cycle(label):
    return 'continue' if label.strip().lower() == 'continue' else 'stop'


def resolve_cook_fish_filter(option, custom):
    o = option.strip().lower()
    if o == '' or o == 'all raw' or o == 'all':
        return ''
    if o == 'custom':
        return custom.strip()
    return option.strip()


def parse_positive_int(raw, fallback):
    if is_number(raw):
        return max(1, math.floor(raw))
    if isinstance(raw, str):
        digits = raw.strip().replace(',', '').replace('_', '').replace(' ', '')
        if len(digits) > 0 and len([c for c in digits if c not in '0123456789']) == 0 and int(digits) > 0:
            return int(digits)
    return max(1, math.floor(fallback))


def is_raw_fish_name(name):
    n = (name or '').lower()
    return n.startswith('raw ') or 'raw fish' in n


def is_burnt_fish_name(name):
    n = (name or '').lower()
    return n.startswith('burnt ') or n == 'burnt fish'


def is_cooked_fish_name(name):
    if is_raw_fish_name(name) or is_burnt_fish_name(name):
        return False
    n = (name or '').strip().lower()
    if len(n) == 0:
        return False
    if n in COOKED_FISH_NAMES:
        return True
    if n.startswith('cooked '):
        rest = n[len('cooked '):]
        return rest in COOKED_FISH_NAMES or rest == 'fish'
    return False


def strip_raw(text):
    t = text.strip()
    return t[4:].strip() if t.lower().startswith('raw ') else t


def raw_matches_cook_filter(name, filter):
    if not is_raw_fish_name(name):
        return False
    f = filter.strip().lower()
    if len(f) == 0:
        return True
    n = (name or '').lower()
    bare = strip_raw(f)
    return f in n or (len(bare) > 0 and bare in n)


def count_matching(items, pred):
    return len([i for i in items if pred(i.name)])


def last_matching_index(items, pred):
    for i in range(len(items) - 1, -1, -1):
        if pred(items[i].name):
            return i
    return -1


def count_raw_in_bank(items, filter):
    return sum([i.count for i in items if raw_matches_cook_filter(i.name, filter)])


def should_cook_then_bank(mode, inventory_full, cookable_raw_count):
    return mode == 'cook-then-bank' and inventory_full and cookable_raw_count > 0


def should_finish_cook_load(mode, cooking, cookable_raw_count):
    return mode != 'off' and cooking and cookable_raw_count > 0


def should_start_bank_raw_cook_batch(mode, bank_raw_total, target):
    return mode == 'bank-raw-then-cook' and target > 0 and bank_raw_total >= target


def should_keep_draining_cook_batch(in_cook_batch, bank_raw_remaining):
    return in_cook_batch and bank_raw_remaining > 0


def cook_batch_after_load(bank_raw_remaining, after_cook):
    if bank_raw_remaining > 0:
        return 'drain-more'
    return 'fish-again' if after_cook == 'continue' else 'stop'


def cook_pace_ticks(_rand=None):
    """A tick between cooking single fish: this revision has no Make X."""
    return 1


def bank_pace_ticks(rand=None):
    """One or two ticks between bank steps, as bank_pace_ticks."""
    return 2 if (rand or random.random)() < 0.35 else 1


def cooked_name_from_raw(raw_name):
    return strip_raw(raw_name)


def cook_filter_label(filter):
    return 'all raw' if len(filter.strip()) == 0 else filter.strip()
