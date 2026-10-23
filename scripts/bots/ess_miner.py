# Mines rune essence: Aubury's teleport into the mine, a full pack, the portal back, and the Varrock East bank:
# rs2b0t's EssMiner (MIT, see thirdparty/rs2b0t). It needs Rune Mysteries, uses the best pickaxe it owns, and buys
# the best one it can use from Nurmof when the bank's coins cover it.

import time

from rs2004.catalogs import COINS, NURMOF_VENDOR, PICKAXE_SHOP_COSTS, ContinueDialog, in_ess_mine

ESS_ITEM = 'Rune essence'
BEST_AVAILABLE = 'Best available'


class PickTier:
    def __init__(self, tier, item, level):
        self.tier = tier
        self.item = item
        self.level = level


PICK_TIERS = [
    PickTier('Rune', 'Rune pickaxe', 41),
    PickTier('Adamant', 'Adamant pickaxe', 31),
    PickTier('Mithril', 'Mithril pickaxe', 21),
    PickTier('Steel', 'Steel pickaxe', 6),
    PickTier('Iron', 'Iron pickaxe', 1),
    PickTier('Bronze', 'Bronze pickaxe', 1),
]
PICK_OPTIONS = [BEST_AVAILABLE] + [t.tier for t in PICK_TIERS]

BANK_STAND = Tile(3251, 3420, 0)
BOOTH_NAME = 'Bank booth'
BOOTH_OP = 'Use-quickly'
AUBURY_TILE = Tile(3253, 3402, 0)
AUBURY = 'Aubury'
TELEPORT_OP = 'Teleport'
ESS_LOC = 'Rune Essence'
MINE_OP = 'Mine'
PORTAL_LOC = 'Portal'
PORTAL_OP = 'Use'
AUBURY_LEASH = 8
STALL_MS = 20000
MAX_TELEPORT_FAILS = 3
MAX_BANK_FAILS = 6
RUNE_MYSTERIES = 'Rune Mysteries Quest'
QUEST_REFUSED = 'need to have completed the rune mysteries'

SETTINGS = {
    'pickaxe': SettingDef('string', BEST_AVAILABLE, 'Pickaxe', options=PICK_OPTIONS,
                          help="Best available walks Rune→Bronze against your Mining level (worn → inventory → bank withdraw); a specific tier stops if you can't use or don't own it"),
    'purge_pack_on_start': SettingDef('boolean', True, 'Bank junk on start',
                                      help='If the pack holds anything other than a usable pickaxe, bank it at Varrock East before mining (start from anywhere).'),
}


def tier_named(selection):
    for t in PICK_TIERS:
        if t.tier.lower() == selection.strip().lower():
            return t
    return None


def required_mining_level(selection):
    t = tier_named(selection)
    return t.level if t is not None else None


def desired_pickaxe(selection, mining_level):
    """The tier EssMiner should own: the one chosen, or the best the level can use."""
    specific = tier_named(selection)
    if specific is not None:
        return specific if mining_level >= specific.level else None
    for t in PICK_TIERS:
        if mining_level >= t.level:
            return t
    return None


def needs_pickaxe_check(last_checked_item, selection, mining_level):
    """Whether a setting or a Mining level changed the tier wanted since the last look."""
    wanted = desired_pickaxe(selection, mining_level)
    return last_checked_item != (wanted.item if wanted is not None else None)


def resolve_pick(selection, mining_level, held, banked):
    """('held', item), ('withdraw', item) or ('stop', reason)."""
    def has(names, item):
        return len([n for n in names if n.lower() == item.lower()]) > 0

    specific = tier_named(selection)
    if specific is not None and mining_level < specific.level:
        return ('stop', f'Mining {specific.level} required for the {specific.item} (have {mining_level})')
    candidates = [specific] if specific is not None else [t for t in PICK_TIERS if mining_level >= t.level]
    for t in candidates:
        if has(held, t.item):
            return ('held', t.item)
    for t in candidates:
        if has(banked, t.item):
            return ('withdraw', t.item)
    want = specific.item if specific is not None else f"usable pickaxe ({', '.join([t.item for t in candidates])})"
    return ('stop', f'no {want} in inventory, equipment, or bank')


def held_pickaxe_to_keep(selection, mining_level, held):
    """The pickaxe a bank trip keeps in the pack."""
    kind, item = resolve_pick(selection, mining_level, held, [])
    return item if kind == 'held' else None


def ess_count():
    return inventory.count(ESS_ITEM)


def held_names():
    return [i.name for i in equipment.items() + inventory.items() if i.name]


def in_mine():
    t = game.tile()
    return t is not None and in_ess_mine(t.x, t.z)


class EssMiner(TaskBot):
    loop_delay = 600

    def on_start(self):
        yield from execution.delay_until(lambda: game.ingame() and game.tile() is not None, 0)
        self.trips = 0
        self.banked = 0
        self.mined = 0
        self.bank_fails = 0
        self.status = 'starting'
        self.started_at = time.time()
        self.checked_pickaxe = None
        self.quest_refused = False
        self.pick_choice = self.settings.str('pickaxe', BEST_AVAILABLE)
        self.xp_at_start = skills.xp('mining')
        self.log(f"EssMiner starting — pickaxe '{self.pick_choice}', bank {BANK_STAND}, Aubury {AUBURY_TILE}")
        # The purge comes before the quest check, so a junk pack is cleaned even without Rune Mysteries.
        if self.settings.bool('purge_pack_on_start', True):
            keep = held_pickaxe_to_keep(self.pick_choice, skills.level('mining'), held_names())
            yield from purge_pack_at_bank([keep] if keep else [], stand=BANK_STAND, booth_name=BOOTH_NAME, booth_op=BOOTH_OP, log=self.log)
        if quests.status(RUNE_MYSTERIES) != 'complete':
            self.log("EssMiner needs Rune Mysteries completed for Aubury's teleport — complete it with the AIOQuester bot first.")
            raise RuntimeError('EssMiner: Rune Mysteries required')
        gate = required_mining_level(self.pick_choice)
        if gate is not None and skills.level('mining') < gate:
            self.log(f"EssMiner: Mining {gate} required for the {self.pick_choice} pickaxe (have {skills.level('mining')}) — stopping.")
            raise RuntimeError('EssMiner: unusable pickaxe selection')
        self.on('chat_message', self.heard)
        self.add(ContinueDialog(), MineEss(self), UsePortal(self), BankEss(self), AcquireBestPick(self), GetPick(self), TeleportIn(self))

    def heard(self, e):
        if e.type == 'game' and QUEST_REFUSED in (e.text or '').lower():
            self.quest_refused = True

    def bank_deposit(self):
        keep = held_pickaxe_to_keep(self.pick_choice, skills.level('mining'), held_names())
        return deposit_all_except([keep] if keep else [])

    def set_status(self, s):
        self.status = s

    def count_bank_fail(self):
        self.bank_fails += 1
        return self.bank_fails

    def needs_best_pick_check(self):
        return needs_pickaxe_check(self.checked_pickaxe, self.pick_choice, skills.level('mining'))

    def walk_to(self, dest, radius=2):
        """Use with yield from."""
        here = game.tile()
        if here is not None and dest.distance_to(here) <= radius:
            return
        yield from traversal.walk_resilient(dest, radius=radius, attempts=6, timeout_ms=240000, log=lambda m: self.log(f'  {m}'))

    def open_bank(self, why):
        """Opens the Varrock East booth: False, and after MAX_BANK_FAILS a stop, when it can't. Use with yield from."""
        yield from self.walk_to(BANK_STAND)
        opened = bank.is_open()
        if not opened:
            opened = yield from bank.open_booth(BANK_STAND, BOOTH_NAME, BOOTH_OP)
        if opened:
            self.bank_fails = 0
            return True
        if self.count_bank_fail() >= MAX_BANK_FAILS:
            self.status = 'cannot reach the bank — stopped'
            self.request_finish(f'EssMiner: could not reach the Varrock East bank {why}')
        else:
            self.log('could not open the bank — will retry')
        return False

    def on_progress_report(self):
        minutes = (time.time() - self.started_at) / 60
        gained = skills.xp('mining') - self.xp_at_start
        return {'Status': self.status, 'Mining': skills.level('mining'), 'XP/hr': f'{gained / minutes * 60 / 1000:.1f}k' if minutes > 0.5 else '—',
                'Trips': self.trips, 'Banked': self.banked, 'Pack': ess_count(), 'Mined': self.mined}


class AcquireBestPick(Task):
    """Before a trip, gets the best pickaxe the level can use: from the bank, or from Nurmof when the coins
    cover it."""

    def __init__(self, bot):
        Task.__init__(self, label='best pickaxe')
        self.bot = bot

    def validate(self):
        return not in_mine() and ess_count() == 0 and self.bot.needs_best_pick_check()

    def execute(self):
        bot = self.bot
        target = desired_pickaxe(bot.pick_choice, skills.level('mining'))
        if target is None:
            bot.checked_pickaxe = None
            return
        if len([n for n in held_names() if n.lower() == target.item.lower()]) > 0:
            bot.checked_pickaxe = target.item
            return
        bot.set_status(f'checking bank for {target.item}')
        opened = yield from bot.open_bank('to check for the best pickaxe')
        if not opened:
            return
        yield from execution.delay_until(lambda: bank.loaded() or not bank.is_open(), 4000)
        if not bank.is_open():
            return
        found = [i for i in bank.items() if (i.name or '').lower() == target.item.lower()]
        if found:
            if inventory.is_full():
                yield from bank.deposit_all_matching(bot.bank_deposit())
                yield from execution.delay_ticks(1)
            op = withdraw_op(found[0].actions(), '1')
            before = inventory.count(target.item)
            if op is not None and bank.withdraw(target.item, op):
                yield from execution.delay_until(lambda: inventory.count(target.item) > before, 4000)
            if inventory.count(target.item) > before:
                bot.log(f'withdrew best usable {target.item}')
                bot.checked_pickaxe = target.item
            yield from bank.close()
            return
        cost = PICKAXE_SHOP_COSTS.get(target.item)
        held_coins = inventory.count(COINS)
        bank_coins = bank.count(COINS)
        if cost is None or held_coins + bank_coins < cost:
            bot.log(f"best usable {target.item} costs {cost if cost is not None else '?'}gp; bank + pack has {held_coins + bank_coins}gp — using the best pickaxe already owned")
            bot.checked_pickaxe = target.item
            yield from bank.close()
            return
        need = max(0, cost - held_coins)
        if need > 0:
            bot.log(f'withdrawing {need}gp for {target.item}')
            took = yield from bank.withdraw_x(COINS, need)
            if not took:
                bot.log('could not withdraw pickaxe coins — will retry')
                yield from bank.close()
                return
            yield from execution.delay_until(lambda: inventory.count(COINS) >= cost, 4000)
        yield from bank.close()
        if inventory.count(COINS) < cost:
            return
        yield from self.buy(target, cost)

    def buy(self, target, cost):
        """Use with yield from."""
        bot = self.bot
        bot.set_status(f'buying {target.item} from Nurmof')
        vendor = NURMOF_VENDOR
        here = game.tile()
        if vendor.hop_from is not None and here is not None and here.z < 9000:
            bot.log(f'heading to the Dwarven Mine for {target.item}')
            arrived = yield from traversal.walk_resilient(vendor.hop_from, radius=2, timeout_ms=120000, log=lambda m: bot.log(f'  {m}'))
            if not arrived:
                return
            trapdoor = locs.query().name(vendor.hop_loc).action(vendor.hop_action).nearest()
            if trapdoor is None or not trapdoor.interact(vendor.hop_action):
                bot.log('could not enter the Dwarven Mine — will retry')
                return
            down = yield from execution.delay_until(lambda: (game.tile().z if game.tile() is not None else 0) >= 9000, 10000)
            if not down:
                return
        arrived = yield from traversal.walk_resilient(vendor.stand, radius=4, timeout_ms=120000, log=lambda m: bot.log(f'  {m}'))
        if not arrived:
            return
        opened = yield from shop.open(vendor.keeper)
        if not opened:
            bot.log("could not open Nurmof's shop — will retry")
            return
        before = inventory.count(target.item)
        bought = yield from shop.buy(target.item, 1)
        yield from shop.close()
        if bought > 0 or inventory.count(target.item) > before:
            bot.log(f'bought best usable {target.item} from Nurmof for {cost}gp')
        else:
            bot.log(f'{target.item} was out of stock at Nurmof — using the best pickaxe already owned')
        bot.checked_pickaxe = target.item


class MineEss(Task):
    def __init__(self, bot):
        Task.__init__(self, label='mine essence')
        self.bot = bot

    def validate(self):
        return in_mine() and not inventory.is_full()

    def execute(self):
        bot = self.bot
        rock = locs.query().name(ESS_LOC).action(MINE_OP).nearest()
        if rock is None:
            yield from execution.delay_ticks(2)
            return
        bot.set_status('mining rune essence')
        if not rock.interact(MINE_OP):
            yield from execution.delay_ticks(2)
            return
        bot.log('mining rune essence')
        count = ess_count()
        last_gain = time.time()
        while not inventory.is_full():
            if event_signal.pending() or chat_dialog.can_continue() or not in_mine():
                return
            now = ess_count()
            if now > count:
                bot.mined += now - count
                count = now
                last_gain = time.time()
            if (time.time() - last_gain) * 1000 > STALL_MS:
                return
            yield from execution.delay_ticks(2)
        bot.log(f'pack full ({ess_count()} rune essence)')


class UsePortal(Task):
    def __init__(self, bot):
        Task.__init__(self, label='portal back')
        self.bot = bot

    def validate(self):
        return in_mine() and inventory.is_full()

    def execute(self):
        portal = locs.query().name(PORTAL_LOC).action(PORTAL_OP).nearest()
        if portal is None:
            yield from execution.delay_ticks(2)
            return
        self.bot.set_status('taking the portal back')
        self.bot.log('taking the portal back')
        if not portal.interact(PORTAL_OP):
            yield from execution.delay_ticks(2)
            return
        yield from execution.delay_until(lambda: not in_mine(), 15000)


class BankEss(Task):
    def __init__(self, bot):
        Task.__init__(self, label='bank essence')
        self.bot = bot

    def validate(self):
        return not in_mine() and ess_count() > 0

    def execute(self):
        bot = self.bot
        bot.set_status('banking the essence')
        opened = yield from bot.open_bank('— start with a pickaxe equipped or in your inventory, or start nearer Varrock')
        if not opened:
            return
        n = ess_count()
        yield from bank.deposit_all_matching(bot.bank_deposit())
        yield from execution.delay_ticks(1)
        bot.trips += 1
        bot.banked += n
        bot.log(f'banked {n} rune essence (trip {bot.trips})')


class GetPick(Task):
    def __init__(self, bot):
        Task.__init__(self, label='get pickaxe')
        self.bot = bot

    def validate(self):
        return not in_mine() and resolve_pick(self.bot.pick_choice, skills.level('mining'), held_names(), [])[0] != 'held'

    def execute(self):
        bot = self.bot
        bot.set_status('getting a pickaxe from the bank')
        opened = yield from bot.open_bank('— start with a pickaxe equipped or in your inventory, or start nearer Varrock')
        if not opened:
            return
        if inventory.is_full():
            yield from bank.deposit_all_matching(bot.bank_deposit())
            yield from execution.delay_ticks(1)
        banked = [i.name for i in bank.items() if i.name]
        kind, what = resolve_pick(bot.pick_choice, skills.level('mining'), held_names(), banked)
        if kind == 'stop':
            bot.set_status('no usable pickaxe — stopped')
            bot.request_finish(f'EssMiner: {what}')
            return
        if kind == 'withdraw':
            found = [i for i in bank.items() if (i.name or '').lower() == what.lower()]
            op = withdraw_op(found[0].actions(), '1') if found else None
            if op is None:
                bot.log(f'no withdraw op on {what} — will retry')
                return
            before = inventory.used()
            if not bank.withdraw(what, op):
                bot.log(f'could not withdraw {what} — will retry')
                return
            yield from execution.delay_until(lambda: inventory.used() > before, 3000)
            bot.log(f'withdrew {what}')


class TeleportIn(Task):
    def __init__(self, bot):
        Task.__init__(self, label='teleport in')
        self.bot = bot
        self.fails = 0

    def find(self):
        return npcs.query().name(AUBURY).action(TELEPORT_OP).where(lambda n: n.distance() <= AUBURY_LEASH).nearest()

    def validate(self):
        return not in_mine() and ess_count() == 0 and not inventory.is_full() and resolve_pick(self.bot.pick_choice, skills.level('mining'), held_names(), [])[0] == 'held'

    def execute(self):
        bot = self.bot
        aubury = self.find()
        if aubury is None:
            bot.set_status('heading to Aubury')
            yield from bot.walk_to(AUBURY_TILE)
            aubury = self.find()
        if aubury is None:
            yield from execution.delay_ticks(3)
            return
        bot.set_status('teleporting to the essence mine')
        bot.log('teleporting to the essence mine')
        bot.quest_refused = False
        if not aubury.interact(TELEPORT_OP):
            yield from execution.delay_ticks(2)
            return
        arrived = yield from execution.delay_until(in_mine, 15000)
        if arrived:
            self.fails = 0
            # The portal leads back to Aubury, so a walk from inside plans that exit.
            essence_session.note_entry('aubury')
            return
        self.fails += 1
        if bot.quest_refused or self.fails >= MAX_TELEPORT_FAILS:
            bot.set_status('teleport failed — stopped')
            bot.request_finish('Aubury refused the teleport — Rune Mysteries is not complete on the server' if bot.quest_refused else f'teleport did not land after {self.fails} attempts')
            return
        bot.log('teleport did not land — retrying')


BOT = define_bot(
    name='EssMiner',
    create=EssMiner,
    description='Rune essence loop — Aubury teleport, one-click mine to a full pack, portal back, bank at Varrock East. Needs Rune Mysteries; uses your best pickaxe and buys the exact best usable tier from Nurmof when banked coins cover it',
    category='Mining',
    tags=['varrock', 'mining', 'banking', 'afk'],
    settings_schema=SETTINGS,
)
