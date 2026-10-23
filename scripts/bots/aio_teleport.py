# Casts a standard teleport over and over for Magic xp, banking for law and elemental runes in batches, and in
# progressive mode moving up to the best teleport the level allows: rs2b0t's AIOTeleport (MIT, see thirdparty/rs2b0t).
# An elemental staff stands in for its rune.

import math
import time

BOOTH_NAME = 'Bank booth'
BOOTH_OP = 'Use-quickly'
LAW = 'Law rune'
# What counts as a staff's unlimited supply of its rune.
STAFF_SUPPLY = 99999


class TeleportMethod:
    def __init__(self, name, rune_cost, level_required, spell_name, bank):
        self.name = name
        self.rune_cost = rune_cost
        self.level_required = level_required
        self.spell_name = spell_name
        # The bank by the destination.
        self.bank = bank


TELEPORTS = {
    'varrock': TeleportMethod('Varrock Teleport', {'Law rune': 1, 'Air rune': 3, 'Fire rune': 1}, 25, 'Varrock', Tile(3252, 3420, 0)),
    'lumbridge': TeleportMethod('Lumbridge Teleport', {'Law rune': 1, 'Air rune': 3, 'Earth rune': 1}, 31, 'Lumbridge', Tile(3092, 3245, 0)),
    'falador': TeleportMethod('Falador Teleport', {'Law rune': 1, 'Air rune': 3, 'Water rune': 1}, 37, 'Falador', Tile(2946, 3368, 0)),
    'camelot': TeleportMethod('Camelot Teleport', {'Law rune': 1, 'Air rune': 5}, 45, 'Camelot', Tile(2727, 3493, 0)),
    'ardougne': TeleportMethod('Ardougne Teleport', {'Law rune': 2, 'Water rune': 2}, 51, 'Ardougne', Tile(2655, 3283, 0)),
    'watchtower': TeleportMethod('Watchtower Teleport', {'Law rune': 2, 'Earth rune': 2}, 58, 'Watchtower', Tile(2547, 3111, 0)),
}
ALL_BANKS = [
    ('Varrock', Tile(3252, 3420, 0)),
    ('Lumbridge', Tile(3092, 3245, 0)),
    ('Falador', Tile(2946, 3368, 0)),
    ('Camelot', Tile(2727, 3493, 0)),
    ('Ardougne', Tile(2655, 3283, 0)),
    ('Watchtower', Tile(2547, 3111, 0)),
]
# Progressive mode stops at Camelot.
PROGRESSION = [(25, 'varrock'), (31, 'lumbridge'), (37, 'falador'), (45, 'camelot')]
STAFFS = {
    'Air staff': 'Air rune', 'Staff of air': 'Air rune',
    'Fire staff': 'Fire rune', 'Staff of fire': 'Fire rune',
    'Water staff': 'Water rune', 'Staff of water': 'Water rune',
    'Earth staff': 'Earth rune', 'Staff of earth': 'Earth rune',
    'Lava staff': 'Fire rune', 'Staff of lava': 'Fire rune',
    'Mud staff': 'Water rune', 'Staff of mud': 'Water rune',
    'Steam staff': 'Water rune', 'Staff of steam': 'Water rune',
    'Dust staff': 'Earth rune', 'Staff of dust': 'Earth rune',
    'Smoke staff': 'Fire rune', 'Staff of smoke': 'Fire rune',
    'Mystic air staff': 'Air rune', 'Mystic fire staff': 'Fire rune', 'Mystic water staff': 'Water rune', 'Mystic earth staff': 'Earth rune',
}

SETTINGS = {
    'teleport_name': SettingDef('string', 'progressive', 'Teleport Destination', options=['progressive', 'varrock', 'lumbridge', 'falador', 'camelot', 'ardougne', 'watchtower'],
                                option_labels={
                                    'progressive': '⚡ Progressive (Best for your level)',
                                    'varrock': 'Varrock Teleport (Lvl 25)',
                                    'lumbridge': 'Lumbridge Teleport (Lvl 31)',
                                    'falador': 'Falador Teleport (Lvl 37)',
                                    'camelot': 'Camelot Teleport (Lvl 45)',
                                    'ardougne': 'Ardougne Teleport (Lvl 51)',
                                    'watchtower': 'Watchtower Teleport (Lvl 58)',
                                },
                                help='Select a teleport or choose Progressive for best XP progression'),
    'law_batch_size': SettingDef('number', 1000, 'Law Rune Batch Size', 10, 10000, help='How many law runes to withdraw from bank at a time'),
    'min_law_runes': SettingDef('number', 100, 'Minimum Law Runes', 10, 1000, help='Stop script if total law runes fall below this amount'),
    'use_staff_runes': SettingDef('boolean', True, 'Use Staff Runes', help='Allow equipped staffs to provide elemental runes (Air staff, Fire staff, etc.)'),
}


def chebyshev(a, b):
    return max(abs(a.x - b.x), abs(a.z - b.z))


def format_time(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = math.floor(seconds % 60)
    if hours > 0:
        return f'{hours}h {minutes}m {secs}s'
    if minutes > 0:
        return f'{minutes}m {secs}s'
    return f'{secs}s'


def format_number(num):
    if num >= 1000000:
        return f'{num / 1000000:.1f}M'
    if num >= 1000:
        return f'{num / 1000:.1f}k'
    return str(num)


def best_teleport_for_level(level):
    best = 'varrock'
    for need, key in PROGRESSION:
        if level >= need:
            best = key
    return best


class AIOTeleport(LoopingBot):
    def on_start(self):
        self.teleport_method = None
        self.teleport_key = 'varrock'
        self.teleports_completed = 0
        self.total_runes_used = 0
        self.teleport_delay = 0
        self.need_banking = False
        self.equipped_staff = None
        self.batch_left = 0
        self.bank_name = None
        self.bank_tile = None
        yield from execution.delay_until(lambda: game.ingame() and game.tile() is not None, 0)
        self.load_settings()
        self.check_staff_runes()
        self.update_bank_location()
        self.xp_at_start = skills.xp('magic')
        self.started_at = time.time()
        method = self.teleport_method
        self.log('=== AIO Teleport Started ===')
        self.log(f'Target: {method.name}')
        self.log(f"Magic Level: {skills.level('magic')}")
        self.log(f'Law batch size: {self.law_batch_size}')
        self.log(f'Minimum law runes: {self.min_law_runes}')
        self.log(f"Staff rune support: {'Enabled' if self.use_staff_runes else 'Disabled'}")
        self.log(f"Progressive mode: {'Enabled (stops at Camelot)' if self.progressive else 'Disabled'}")
        if self.equipped_staff:
            self.log(f'✓ Equipped: {self.equipped_staff} (provides {STAFFS[self.equipped_staff]})')
        if skills.level('magic') < method.level_required:
            self.log(f"⚠️ WARNING: Magic level {skills.level('magic')} is below required {method.level_required}")
            self.log('You may fail to cast this spell!')
        self.log(f'Initial law runes: {inventory.count(LAW)}')
        if self.has_required_runes():
            self.log('✓ Already have required runes in inventory! Starting teleport directly.')
            self.batch_left = inventory.count(LAW)
            self.log(f'Batch size set to {self.batch_left} law runes (will bank for more when depleted)')
        else:
            self.log('Missing required runes! Banking...')
            self.need_banking = True
        self.log('✓ Bot ready!')

    def load_settings(self):
        s = self.settings
        selected = s.str('teleport_name', 'progressive')
        self.law_batch_size = s.num('law_batch_size', 1000)
        self.min_law_runes = s.num('min_law_runes', 100)
        self.use_staff_runes = s.bool('use_staff_runes', True)
        self.progressive = selected == 'progressive'
        # Progressive mode picks the best teleport unlocked.
        key = best_teleport_for_level(skills.level('magic')) if self.progressive else selected
        if key not in TELEPORTS:
            self.log(f'❌ Unknown teleport: {selected}, using default')
            key = 'varrock'
        self.teleport_key = key
        self.teleport_method = TELEPORTS[key]
        if self.progressive:
            self.log(f"⚡ Progressive mode: Using {self.teleport_method.name} (level {skills.level('magic')})")

    def update_progressive_teleport(self):
        if not self.progressive:
            return
        level = skills.level('magic')
        best = best_teleport_for_level(level)
        if best == self.teleport_key:
            return
        old = self.teleport_method.name if self.teleport_method else 'None'
        self.teleport_method = TELEPORTS[best]
        self.teleport_key = best
        self.log(f'🔁 Progressive switch: {old} → {self.teleport_method.name} (level {level})')
        # The new teleport is kept only once its runes are in hand.
        if not self.has_required_runes():
            self.log(f'📦 Missing runes for {self.teleport_method.name}, banking...')
            self.need_banking = True

    def check_staff_runes(self):
        self.equipped_staff = None
        for item in equipment.items():
            if not item or not item.name:
                continue
            for staff in STAFFS:
                if staff in item.name:
                    self.equipped_staff = staff
                    return

    def staff_rune(self):
        return STAFFS.get(self.equipped_staff) if self.use_staff_runes and self.equipped_staff else None

    def has_rune(self, rune, amount):
        return inventory.count(rune) >= amount or self.staff_rune() == rune

    def rune_count(self, rune):
        count = inventory.count(rune)
        return count + STAFF_SUPPLY if self.staff_rune() == rune else count

    def has_required_runes(self):
        if not self.teleport_method:
            return False
        for rune, needed in self.teleport_method.rune_cost.items():
            if not self.has_rune(rune, needed):
                return False
        return True

    def update_bank_location(self):
        here = game.tile()
        if here is None:
            self.bank_name = None
            self.bank_tile = None
            self.log('⚠️ No bank found nearby!')
            return
        nearest = None
        for name, tile in ALL_BANKS:
            if nearest is None or chebyshev(here, tile) < chebyshev(here, nearest[1]):
                nearest = (name, tile)
        if self.bank_name != nearest[0]:
            self.log(f'📍 Using nearest bank: {nearest[0]} at {nearest[1].x},{nearest[1].z}')
        self.bank_name = nearest[0]
        self.bank_tile = nearest[1]

    def loop(self):
        self.check_staff_runes()
        self.update_progressive_teleport()
        if self.teleport_delay > 0:
            self.teleport_delay -= 1
            yield from execution.delay_ticks(1)
            return
        if self.need_banking:
            # The nearest bank and the progressive teleport may have changed.
            self.update_bank_location()
            self.update_progressive_teleport()
            yield from self.perform_banking()
            return
        if not self.teleport_method:
            self.log('❌ No teleport method selected!')
            return
        if inventory.count(LAW) < self.teleport_method.rune_cost.get(LAW, 0):
            self.log('⚠️ Out of law runes! Banking...')
            self.need_banking = True
            yield from self.perform_banking()
            return
        if self.batch_left <= 0:
            self.log('📦 Batch empty, going to bank for more...')
            self.need_banking = True
            yield from self.perform_banking()
            return
        if not self.has_required_runes():
            self.log('Missing required runes! Banking...')
            self.need_banking = True
            yield from self.perform_banking()
            return
        # Why: rs2b0t clicks the middle of the canvas to close a bank left open; this closes it.
        if bank.is_open():
            yield from bank.close()
        yield from self.perform_teleport()

    def withdraw(self, item_name, amount):
        """Withdraws amount of item_name. Use with yield from."""
        self.log(f'Withdrawing {amount} {item_name} using Withdraw X...')
        in_bank = bank.count(item_name)
        if in_bank == 0:
            self.log(f'❌ No {item_name} found in bank!')
            return False
        if in_bank < amount:
            self.log(f'⚠️ Only {in_bank} {item_name} in bank, need {amount}')
            return False
        before = inventory.count(item_name)
        # Why: rs2b0t types the Withdraw-X amount on the canvas; withdraw_x does the same through the dialog.
        yield from bank.withdraw_x(item_name, amount)
        yield from execution.delay_ticks(2)
        withdrawn = inventory.count(item_name) - before
        self.log(f'✓ Withdrew {withdrawn} {item_name}')
        return withdrawn > 0

    def stop(self, reason):
        self.log(f'Stopping script - {reason}')
        self.request_finish(reason)

    def perform_banking(self):
        """Use with yield from."""
        self.log('=== Banking ===')
        if self.bank_tile is None:
            self.log('No bank found! Stopping...')
            self.request_finish('no bank found')
            return
        self.log(f'Walking to nearest bank at {self.bank_tile.x},{self.bank_tile.z}...')
        yield from traversal.walk_to(self.bank_tile, radius=3, timeout_ms=60000)
        self.log('Opening bank...')
        opened = yield from bank.open_nearest(BOOTH_NAME, BOOTH_OP)
        if not opened:
            self.log('❌ Failed to open bank!')
            return
        self.log('✓ Bank opened successfully')
        self.log('Depositing all inventory...')
        yield from bank.deposit_inventory()
        yield from execution.delay_ticks(2)
        # Banking may unlock the next progressive teleport.
        self.update_progressive_teleport()
        banked = bank.count(LAW)
        self.log(f'Law runes in bank: {banked}')
        cost = self.teleport_method.rune_cost.get(LAW, 0)
        # Why: rs2b0t logs these stops and goes back to banking; this stops instead of banking forever.
        if banked < cost:
            self.log(f'❌ Not enough law runes in bank! Have {banked}, need at least {cost}')
            self.stop('need more law runes')
            return
        if banked < self.min_law_runes:
            self.log(f'⚠️ Below minimum law runes ({banked} < {self.min_law_runes})')
            self.stop('add more law runes to bank')
            return
        withdrew = yield from self.withdraw(LAW, min(self.law_batch_size, banked))
        if not withdrew:
            self.log('Withdraw X failed, using Withdraw All...')
            bank.withdraw(LAW, 'Withdraw All')
            yield from execution.delay_ticks(2)
        self.batch_left = inventory.count(LAW)
        self.log(f'✓ Batch set to {self.batch_left} law runes')
        yield from self.withdraw_elemental_runes()
        yield from execution.delay_ticks(2)
        yield from bank.close()
        self.need_banking = False
        self.log('✓ Banking complete!')
        self.log(f'Current law runes: {inventory.count(LAW)}')
        self.log(f'Batch remaining: {self.batch_left}/{self.law_batch_size}')

    def withdraw_elemental_runes(self):
        """Use with yield from."""
        for rune, per_cast in self.teleport_method.rune_cost.items():
            if rune == LAW:
                continue
            current = self.rune_count(rune)
            needed = self.law_batch_size * per_cast
            short = max(0, needed - current)
            self.log(f'Need {short} {rune} (have {current}, {per_cast} per teleport x {self.law_batch_size} teleports = {needed} total)')
            if short <= 0:
                self.log(f'✓ Already have enough {rune} ({current})')
                continue
            in_bank = bank.count(rune)
            if in_bank > 0:
                yield from self.withdraw(rune, min(short, in_bank))
            else:
                self.log(f'⚠️ No {rune} in bank!')
                if self.equipped_staff:
                    self.log(f'   Your staff provides {STAFFS[self.equipped_staff]} but you need {rune}')

    def perform_teleport(self):
        """Use with yield from."""
        method = self.teleport_method
        if not self.has_required_runes():
            self.log('Missing required runes!')
            self.need_banking = True
            return
        law_before = inventory.count(LAW)
        if not game.teleport(method.spell_name):
            self.log('❌ Teleport failed')
            if inventory.count(LAW) < 1:
                self.need_banking = True
            self.teleport_delay = 1
            return
        # The cast's click is sent; the runes go once it lands.
        yield from execution.delay_until(lambda: inventory.count(LAW) < law_before, 3000)
        self.update_bank_location()
        used = law_before - inventory.count(LAW)
        if used > 0:
            self.teleports_completed += 1
            self.total_runes_used += used
            self.batch_left = max(0, self.batch_left - used)
            self.log(f'✓ Teleport #{self.teleports_completed} ({self.batch_left}/{self.law_batch_size} remaining)')
            if self.batch_left <= 0:
                self.log('📦 Batch empty, going to bank for more...')
                self.need_banking = True
        self.teleport_delay = 0

    def on_stop(self, reason=None):
        runtime = int(time.time() - self.started_at)
        self.log('=== AIO Teleport Stopped ===')
        self.log(f'Runtime: {format_time(runtime)}')
        self.log(f'Teleports: {self.teleports_completed}')
        self.log(f'Law runes used: {self.total_runes_used}')
        self.log(f"Magic XP gained: {format_number(skills.xp('magic') - self.xp_at_start)}")
        self.log(f"Magic level: {skills.level('magic')}")

    def on_progress_report(self):
        return {'Teleport': self.teleport_method.name if self.teleport_method else 'None', 'Teleports': self.teleports_completed,
                'Law runes used': self.total_runes_used, 'Batch left': self.batch_left, 'Magic xp': skills.xp('magic') - self.xp_at_start,
                'Bank': self.bank_name or 'None'}


BOT = define_bot(
    name='AIO Teleport',
    create=AIOTeleport,
    description='Automated teleportation with intelligent banking and safety features',
    category='Magic',
    tags=['teleport', 'magic', 'banking', 'aio'],
    settings_schema=SETTINGS,
)
