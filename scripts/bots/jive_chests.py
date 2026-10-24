# Opens the crystal chest in Taverley with seven keys a trip from Falador West: rs2b0t's JiveChests, with its
# CombineKeys.ts (MIT, see thirdparty/rs2b0t). It keeps the low-priority rewards unless a full pack blocks valuable
# ground loot, collects the overflow most valuable first, banks when full and comes back for what's left, and
# teleports home when it has the runes. A second mode only combines key halves at the bank.

import time

from bots.jivechests.logic import CHEST, CHEST_STAND, JUNK, KEY, KEYS_PER_TRIP, NOT_LOOT, PackState, decide, junk_held, keys_to_withdraw
from bots.jivechests.logic import loot_priority
from rs2004.catalogs import STAFF_RUNES, ContinueDialog
from rs2004.hunting.supply import escape_runes_for

# The Falador West booths, the nearest bank to both the chest and the teleport.
BANK_STAND = Tile(2946, 3369, 0)
BOOTH = 'Bank booth'
BOOTH_OP = 'Use-quickly'
TELEPORT_ID = 'falador'
TELEPORT_CASTS = 10
CHEST_REACH = 6
WALK_MS = 180000
# The chest's reward runs on the tick after the use, so the pack settles inside this.
REWARD_MS = 4000
TELE_LAND_MS = 6000

# The key halves and the key they make.
TOOTH = 985
LOOP = 987
CRYSTAL_KEY = 989
PAIRS_PER_LOAD = 14
PAIRS_PER_BATCH = 5

SETTINGS = {
    'combine_keys': SettingDef('boolean', False, 'Combine crystal keys at the bank',
                               help='withdraws up to 14 tooth halves and 14 loop halves, combines them and banks the keys. Repeats until either half runs out; does not open the chest'),
    'teleport_home': SettingDef('boolean', True, 'Teleport back to Falador', show_if={'key': 'combine_keys', 'any_of': ['false']},
                                help='stocks up to 10 Falador return teleports, using equipped elemental staffs for free runes. Teleports from the chest when banking and walks from the bank to the chest. Walks home when runes or Magic are short'),
}


def census():
    """Each name's count in the pack, a slot counting at least one."""
    out = {}
    for item in inventory.items():
        name = item.name or ''
        out[name] = out.get(name, 0) + max(1, item.count)
    return out


def gained_since(before):
    out = {}
    for name, count in census().items():
        delta = count - before.get(name, 0)
        if delta > 0 and name != '':
            out[name] = delta
    return out


def home_spell():
    """The Falador teleport's runes, less those an elemental staff worn gives."""
    spell = escape_runes_for(TELEPORT_ID)
    worn = set([(i.name or '').lower() for i in equipment.items()])
    supplied = set()
    for staff, runes in STAFF_RUNES.items():
        if staff.lower() in worn:
            for rune in runes:
                supplied.add(rune)
    return (spell, [(rune, count) for rune, count in spell.runes if rune not in supplied])


class CombineKeys(Task):
    """The bank-only mode: withdraws up to 14 pairs of key halves, combines them five at a time and banks the keys,
    until either half runs out."""

    def __init__(self, bot):
        Task.__init__(self, label='combine keys')
        self.bot = bot
        self.banking = True
        self.done = False
        self.failures = 0
        self.pending_deposit = None

    def validate(self):
        return not self.done and game.ingame()

    def execute(self):
        bot = self.bot
        if not self.banking:
            if bank.is_open():
                yield from bank.close()
                return
            pack = inventory.items()
            teeth = [i for i in pack if i.id == TOOTH and not i.noted]
            loops = [i for i in pack if i.id == LOOP and not i.noted]
            pairs = min(PAIRS_PER_BATCH, len(teeth), len(loops))
            if pairs > 0:
                bot.status = 'combining crystal keys'
                before = inventory.count_by_id(CRYSTAL_KEY)
                sent = 0
                for i in range(pairs):
                    if teeth[i].use_on(loops[i]):
                        sent += 1
                if sent > 0:
                    yield from execution.delay_until_ticks(lambda: inventory.count_by_id(CRYSTAL_KEY) >= before + sent, 3)
                made = inventory.count_by_id(CRYSTAL_KEY) - before
                if made > 0:
                    bot.combined += made
                    self.failures = 0
                else:
                    self.failures += 1
                    if self.failures >= 3:
                        self._finish('could not combine key halves after three attempts')
                return
            self.banking = True
        bot.status = 'banking crystal keys'
        opened = yield from banking.open(log=lambda m: bot.log(m))
        if not opened:
            return
        ready = yield from bank.wait_ready()
        if not ready:
            return
        pack_ready = yield from bank.backpack_ready()
        if not pack_ready:
            return
        if self.pending_deposit is None:
            self.pending_deposit = {}
            for id in [TOOTH, LOOP, CRYSTAL_KEY]:
                if inventory.count_by_id(id) > 0:
                    self.pending_deposit[id] = bank.count_by_id(id) + inventory.count_by_id(id)
        yield from bank.deposit_inventory()
        if inventory.used() > 0:
            return
        expected = self.pending_deposit

        def deposited():
            if not bank.is_open():
                return False
            for id, count in expected.items():
                if bank.count_by_id(id) < count:
                    return False
            return True

        landed = yield from execution.delay_until(deposited, 4000)
        if not landed:
            return
        self.pending_deposit = None
        pairs = min(PAIRS_PER_LOAD, bank.count_by_id(TOOTH), bank.count_by_id(LOOP))
        if pairs == 0:
            closed = yield from bank.close()
            if closed:
                self._finish('no matching key halves left in the bank')
            return
        bot.status = f'withdrawing {pairs} pairs of key halves'
        yield from bank.set_note_mode(False)
        self.pending_deposit = {TOOTH: bank.count_by_id(TOOTH), LOOP: bank.count_by_id(LOOP)}
        teeth_out = yield from bank.withdraw_x_by_id(TOOTH, pairs)
        if not teeth_out:
            return
        loops_out = yield from bank.withdraw_x_by_id(LOOP, pairs)
        if not loops_out:
            return
        self.pending_deposit = None
        self.banking = False
        bot.trips += 1
        yield from bank.close()

    def _finish(self, reason):
        self.done = True
        self.bot.status = reason
        self.bot.log(f'[chests] {reason}; combined {self.bot.combined} crystal keys')
        self.bot.request_finish(reason)


class CollectLoot(Task):
    def __init__(self, bot):
        Task.__init__(self, label='collect loot')
        self.bot = bot

    def validate(self):
        return self.bot.step() == 'loot'

    def execute(self):
        bot = self.bot
        item = None
        for drop in bot.ground_loot():
            if bot.can_loot(drop):
                item = drop
                break
        if item is None:
            return
        before = inventory.count_by_id(item.id)
        bot.status = f'picking up {item.name}'
        took = item.interact('Take')
        if took:
            took = yield from execution.delay_until(lambda: inventory.count_by_id(item.id) > before, REWARD_MS)
        if not took:
            bot.log(f'[chests] could not pick up {item.name}, retrying')
            return
        gained = inventory.count_by_id(item.id) - before
        bot.note_loot({item.name: gained})
        bot.log(f'[chests] picked up {gained} {item.name}')


class DropJunk(Task):
    def __init__(self, bot):
        Task.__init__(self, label='drop junk')
        self.bot = bot

    def validate(self):
        return self.bot.step() == 'drop'

    def execute(self):
        bot = self.bot
        for name in JUNK:
            item = inventory.first(name)
            if item is None:
                continue
            before = inventory.count(name)
            bot.status = f'dropping {name}'
            if not item.interact('Drop'):
                bot.log(f'[chests] could not drop {name}')
                return
            dropped = yield from execution.delay_until(lambda: inventory.count(name) < before, 3000)
            if dropped:
                bot.dropped += before - inventory.count(name)
            return


# Why: the chest answers its first op with "securely locked shut" and only opens to a key used on it.
class OpenChest(Task):
    def __init__(self, bot):
        Task.__init__(self, label='open chest')
        self.bot = bot

    def validate(self):
        return self.bot.step() == 'open'

    def execute(self):
        bot = self.bot
        chest = locs.query().name(CHEST).within_of(CHEST_STAND, CHEST_REACH).nearest()
        key = inventory.first(KEY)
        if chest is None or key is None:
            yield from execution.delay_ticks(2)
            return
        before = census()
        keys = bot.keys_held()
        bot.status = 'opening the chest'
        if not key.use_on(chest):
            bot.log('[chests] the key would not go on the chest, retrying')
            yield from execution.delay_ticks(2)
            return
        took = yield from execution.delay_until(lambda: bot.keys_held() < keys, REWARD_MS)
        if not took:
            bot.log('[chests] the chest took no key, retrying')
            return
        # Why: the reward lands a tick after the key goes, so the pack is read once it has settled.
        yield from execution.delay_ticks(2)
        gained = gained_since(before)
        bot.opened += 1
        bot.note_loot(gained)
        rewards = ', '.join([f'{c} {n}' for n, c in gained.items()]) or 'nothing new'
        bot.log(f'[chests] opened the chest: {rewards}')


class Travel(Task):
    def __init__(self, bot):
        Task.__init__(self, label='travel')
        self.bot = bot

    def validate(self):
        return self.bot.step() == 'travel'

    def execute(self):
        bot = self.bot
        bot.status = 'returning for chest loot' if bot.pending_loot else 'walking to the chest'
        arrived = yield from traversal.walk_resilient(CHEST_STAND, radius=0, attempts=4, timeout_ms=WALK_MS, use_teleport_catalog=False,
                                                      policy={'use_teleports': False}, log=lambda m: bot.log(f'  {m}'))
        if not arrived:
            bot.log('[chests] the walk to the chest failed, will retry')


class BankTrip(Task):
    def __init__(self, bot):
        Task.__init__(self, label='bank trip')
        self.bot = bot

    def validate(self):
        return self.bot.step() == 'bank'

    def execute(self):
        bot = self.bot
        bot.banking = True
        if bot.at_chest() and not bank.is_open() and bot.teleport_home:
            home = yield from self._cast_home()
            if home:
                return
        bot.status = 'walking to the bank'
        say = lambda m: bot.log(f'  {m}')
        arrived = yield from traversal.walk_resilient(BANK_STAND, radius=3, attempts=4, timeout_ms=WALK_MS, use_teleport_catalog=False,
                                                      policy={'use_teleports': False}, log=say)
        if not arrived:
            bot.log('[chests] the walk to the bank failed, will retry')
            return
        opened = yield from bank.open_booth(BANK_STAND, BOOTH, BOOTH_OP)
        if not opened:
            bot.log('[chests] could not open the bank, will retry')
            return
        bot.status = 'banking the haul'
        spell, runes = home_spell()
        keep = set([KEY.lower()] + ([rune.lower() for rune, count in runes] if bot.teleport_home else []))
        yield from bank.deposit_all_matching(lambda name, id: name.lower() not in keep)
        if len([i for i in inventory.items() if (i.name or '').lower() not in keep]) > 0:
            bot.log('[chests] the haul is still in the pack, retrying')
            return
        loaded = yield from execution.delay_until(lambda: bank.is_open() and bank.loaded(), 5000)
        if not loaded:
            bot.log('[chests] the bank list has not filled in, retrying' if bank.is_open() else '[chests] the bank window closed, retrying')
            return
        want = 0 if bot.pending_loot else keys_to_withdraw(bot.keys_held(), bank.count(KEY))
        if not bot.pending_loot and want < 1 and bot.keys_held() < 1:
            closed = yield from bank.close()
            if not closed:
                return
            bot.banking = False
            bot.status = 'stopped'
            bot.request_finish(f'[chests] no {KEY}s left in the bank; {bot.opened} chest(s) opened over {bot.trips} trip(s)')
            return
        if want > 0:
            bot.status = f'withdrawing {want} {KEY}s'
            taken = yield from bank.withdraw_x(KEY, want)
            if not taken:
                bot.log(f'[chests] could not withdraw {want} {KEY}s, retrying')
                return
        if bot.teleport_home and skills.level('magic') >= spell.level:
            for rune, count in runes:
                missing = min(count * TELEPORT_CASTS - inventory.count(rune), bank.count(rune))
                if missing > 0:
                    taken = yield from bank.withdraw_x(rune, missing)
                    if not taken:
                        bot.log(f'[chests] could not withdraw {rune}, retrying')
                        return
        closed = yield from bank.close()
        if not closed:
            bot.log('[chests] the bank would not close, retrying')
            return
        bot.banking = False
        bot.trips += 1
        bot.log(f'[chests] banked the haul and took {bot.keys_held()} {KEY}s')

    def _cast_home(self):
        """Casts the way home; False when the runes or the level are short and the walk has to do it."""
        bot = self.bot
        spell, runes = home_spell()
        short = None
        for rune, count in runes:
            if inventory.count(rune) < count:
                short = rune
                break
        if skills.level('magic') < spell.level or short is not None:
            bot.log(f"[chests] {spell.label} is short {short if short is not None else f'Magic {spell.level}'}, walking back instead")
            return False
        before = game.tile()
        bot.status = f'casting {spell.label}'
        if not game.teleport(TELEPORT_ID):
            return False

        def landed():
            now = game.tile()
            return now is not None and before is not None and BANK_STAND.distance_to(now) < BANK_STAND.distance_to(before)

        home = yield from execution.delay_until(landed, TELE_LAND_MS)
        return home


class JiveChests(TaskBot):
    loop_delay = 600

    def on_start(self):
        self.status = 'starting'
        self.opened = 0
        self.combined = 0
        self.trips = 0
        self.dropped = 0
        self.loot_by_name = {}
        self.banking = False
        self.pending_loot = False
        yield from execution.delay_until(lambda: game.ingame() and game.tile() is not None, 0)
        self.teleport_home = self.settings.bool('teleport_home', True)
        self.combine_keys = self.settings.bool('combine_keys', False)
        self.started_at = time.time()
        self.xp_start = skills.xp('crafting')
        if self.combine_keys:
            self.loop_delay = 100
            self.log('[chests] combining 14 pairs of key halves per load at the nearest bank')
            self.add(CombineKeys(self))
            return
        home = escape_runes_for(TELEPORT_ID).label if self.teleport_home else 'the walk back'
        self.log(f'[chests] {KEYS_PER_TRIP} {KEY}s a trip from Falador West, opening the chest at {CHEST_STAND.x},{CHEST_STAND.z}, '
                 + f'dropping low-priority rewards only for ground loot, home by {home}')
        self.add(ContinueDialog(), DropJunk(self), CollectLoot(self), OpenChest(self), Travel(self), BankTrip(self))

    def recovery_anchor(self):
        return None if self.combine_keys else BANK_STAND

    def on_progress_report(self):
        minutes = (time.time() - self.started_at) / 60
        if self.combine_keys:
            return {'Status': self.status, 'Combined': self.combined, 'Loads': self.trips,
                    'Keys/hr': round(self.combined * 60 / minutes) if minutes > 0.5 else '-'}
        top = sorted(self.loot_by_name.items(), key=lambda pair: -pair[1])[:3]
        return {
            'Status': self.status,
            'Opened': self.opened,
            'Trips': self.trips,
            'Keys': self.keys_held(),
            'Dropped': self.dropped,
            'Chests/hr': round(self.opened * 60 / minutes) if minutes > 0.5 else '-',
            'Top loot': ', '.join([f'{n}x {name}' for name, n in top]) or '-',
        }

    def keys_held(self):
        return inventory.count(KEY)

    def junk_in_pack(self):
        return junk_held(lambda n: inventory.count(n))

    def ground_loot(self):
        drops = ground_items.query().within_of(CHEST_STAND, 0).where(
            lambda item: item.tile().level == CHEST_STAND.level and loot_priority(item.name) < NOT_LOOT).results()
        drops.sort(key=lambda item: loot_priority(item.name))
        return drops

    def can_loot(self, item):
        if inventory.free() > 0:
            return True
        if inventory.count_by_id(item.id) == 0:
            return False
        kind = reader.item_type(item.id)
        return kind is not None and kind.stackable

    def at_chest(self):
        here = game.tile()
        return here is not None and here.level == CHEST_STAND.level and CHEST_STAND.distance_to(here) == 0

    def pack(self):
        at_chest = self.at_chest()
        drops = self.ground_loot() if at_chest and not self.banking else []
        if at_chest and not self.banking:
            self.pending_loot = len(drops) > 0
        return PackState(self.keys_held(), self.junk_in_pack(), inventory.free(), at_chest, len(drops) > 0,
                         len([item for item in drops if self.can_loot(item)]) > 0, self.pending_loot, self.banking)

    def step(self):
        return decide(self.pack())

    def note_loot(self, gained):
        for name, n in gained.items():
            self.loot_by_name[name] = self.loot_by_name.get(name, 0) + n


BOT = define_bot(
    name='JiveChests',
    create=JiveChests,
    description='Opens the Taverley crystal chest with seven keys per trip from Falador West. Keeps food and low-priority rewards unless a full pack blocks valuable ground loot. Collects overflow in priority order: dragonstones, key halves, runite bars, diamonds, rubies, rune legs or skirts, then other rewards. Banks when full and returns for remaining loot before opening again. Walks to the chest and optionally teleports home from it, stocking up to ten Falador casts and accounting for equipped elemental staffs. Stops after the keys are exhausted and remaining loot is collected and banked. Optional bank-only mode withdraws 14 of each key half, combines up to five pairs at a time and deposits the crystal keys, repeating until either half runs out.',
    category='Money making',
    tags=['chest', 'taverley', 'banking', 'looting', 'afk'],
    settings_schema=SETTINGS,
)
