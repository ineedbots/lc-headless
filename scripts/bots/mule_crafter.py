# Runecrafting with mules: the Crafter holds the talisman and crafts at the altar, and each Mule ferries essence
# to the ruins and the runes back to the bank, trading at the ruins: rs2b0t's MuleCrafter (MIT, see
# thirdparty/rs2b0t). Several mules take turns, named comma-separated in the crafter's partner setting.

import time

from rs2004.catalogs import DEFAULT_RUNE, RUNES, RUNE_OPTIONS, ContinueDialog, Record

# MuleCrafterLogic.ts

def bank_tile(bank_name):
    for b in BANK_LOCATIONS:
        if b['name'] == bank_name:
            t = b['tile']
            return Tile(t['x'], t['z'], t['level'])
    raise RuntimeError(f"bankTile: unknown bank '{bank_name}'")


TRADE_CAP = 27


def essence_per_trade(_inv_size=28, _holds_talisman=True):
    return TRADE_CAP


# pocketpy reads no \u escapes.
NO_BREAK_SPACE = chr(0xA0)


def _clean_name(name):
    """A player name as compared: lower case, a no-break space or an underscore read as a space."""
    return name.lower().replace(NO_BREAK_SPACE, ' ').replace('_', ' ').strip()


def is_configured_partner(name, configured_partners):
    if not name or len(configured_partners) == 0:
        return False
    clean_name = _clean_name(name)
    return len([p for p in configured_partners if _clean_name(p) == clean_name]) > 0


def classify_mule_state(their_offer):
    total_essence = sum([item.count for item in their_offer if (item.name or '').lower() == 'rune essence'])
    return ('has-essence' if total_essence > 0 else 'empty')

# MuleCrafter.ts

# Why: each crafter-mule trade gives all runes and receives 27 essence, after which the crafter enters the altar again; it walks back to the bank only after every mule has traded.
ESSENCE = 'Rune essence'
ESSENCE_ID = 1436
RUINS = 'Mysterious ruins'
ALTAR = Record({'name': 'Altar', 'op': 'Craft-rune'})
PORTAL = Record({'name': 'Portal', 'op': 'Use'})
BOOTH = Record({'name': 'Bank booth', 'op': 'Use-quickly'})


def now_ms():
    return time.time() * 1000
TEMPLE_Z = 4000
SETTINGS = {
    'rune': SettingDef('string', DEFAULT_RUNE, 'Rune', options=RUNE_OPTIONS, help='which rune the pair crafts. Air = Falador East bank; Mind = Edgeville bank.'),
    'mode': SettingDef('string', 'Crafter', 'Mode', options=['Crafter', 'Mule'], help='Crafter has the talisman, crafts at the altar, trades runes at ruins. Mule carries essence to the ruins and runes back to the bank.'),
    'partner': SettingDef('string', '', 'Partner name(s) (Optional for Crafter)', help='Crafter: optional mule name(s) to trade with, comma-separated (blank = solo mode). Mule: required crafter to trade with.'),
    'bank_fill': SettingDef('boolean', True, 'Fill essence at bank', help='When enabled, crafter withdraws essence from bank. When disabled, mules bring all essence (blank rune mode). Only applies to Crafter mode.'),
}


def item_id_named(items, name):
    """The id of the first item of that name, without regard to case, or -1."""
    for i in items:
        if (i.name or '').lower() == name.lower():
            return i.id
    return -1


def in_temple():
    t = game.tile()
    return t is not None and t.z > TEMPLE_Z


def ess_count():
    return sum([i.count for i in inventory.items() if i.id == ESSENCE_ID])


def is_at_tile(tile, radius=3):
    t = game.tile()
    return t is not None and tile.distance_to(t) <= radius


class MuleCrafter(TaskBot):
    loop_delay = 600

    def on_start(self):
        yield from execution.delay_until(lambda: game.ingame() and game.tile() is not None, 0)
        self._crafted = 0
        self._trades = 0
        self._status = 'starting'
        self._mode = self.settings.str('mode', 'Crafter')
        self._rune = self.settings.str('rune', DEFAULT_RUNE)
        _v1 = RUNES.get(self._rune)
        self._conf = (_v1 if _v1 is not None else RUNES.get(DEFAULT_RUNE))
        self._bank_tile = bank_tile(self._conf.bank)
        self._partners = [_x for _x in [s.strip() for s in self.settings.str('partner', '').split(',')] if _x]
        self._bank_fill = self.settings.bool('bank_fill', True)
        self._started_at = time.time()
        self._xp_at_start = skills.xp('runecraft')
        self._traded_mules = set()
        if self._mode == 'Mule':
            if len(self._partners) == 0:
                self.log('MuleCrafter: no partner names set for Mule mode. The mule needs the crafter name. Stopping.')
                raise RuntimeError('MuleCrafter: no partner configured for mule mode')
            self.log(f"MuleCrafter mule starting — ferrying essence for {self._rune} to [{', '.join(self._partners)}]")
            yield from self._clean_mule_inventory()
            self.add(ContinueDialog(), MuleWalkToRuins(self), MuleTradeWithCrafter(self), MuleTradeExecute(self), MuleGoBank(self))
            return
        # Crafter mode.
        if len(self._partners) == 0:
            self._bank_fill = True
            self.log('MuleCrafter: No partners configured. Running in Solo Crafter mode.')
        else:
            self.log(f"MuleCrafter crafter starting — {self._rune}, accepting essence from [{', '.join(self._partners)}]{(', banking for essence' if self._bank_fill else ', mules bring all essence')}")
        yield from self._clean_crafter_inventory()
        self.add(ContinueDialog(), CrafterAtBank(self), CrafterWalkToRuins(self), EnterAltar(self), CraftRunes(self), ExitAltar(self), CrafterRequestTrade(self), CrafterWaitAtRuins(self), CrafterTradeAtRuins(self), CrafterGoBank(self))

    def _clean_crafter_inventory(self):
        has_extra_items = len([i for i in inventory.items() if i.name and i.id != ESSENCE_ID and i.name.lower() != self._conf.talisman.lower()]) > 0
        has_talisman = inventory.contains(self._conf.talisman)
        if has_extra_items or not has_talisman:
            self.log('Crafter inventory contains unauthorized items or missing talisman. Opening bank to clean inventory...')
            yield from self.walk_to(self._bank_tile, 3)
            opened = yield from bank.open_booth(self._bank_tile, BOOTH.name, BOOTH.op)
            if not opened:
                opened = yield from bank.open_nearest(BOOTH.name, BOOTH.op)
            if not opened:
                raise RuntimeError('MuleCrafter: Failed to open bank for initial inventory cleanup.')
            talisman_id = item_id_named(bank.items(), self._conf.talisman)
            rune_id = item_id_named(inventory.items(), self._conf.rune)
            if rune_id == -1:
                rune_id = item_id_named(bank.items(), self._conf.rune)
            crafter_keep = set([id for id in [talisman_id, ESSENCE_ID, rune_id] if id != -1])
            yield from bank.deposit_all_matching(lambda name, id: len(name) > 0 and not (id in crafter_keep))
            yield from execution.delay_ticks(1)
            if not inventory.contains(self._conf.talisman):
                tal = ([i for i in bank.items() if (i.name or '').lower() == self._conf.talisman.lower()] or [None])[0]
                if tal and tal.name:
                    bank.withdraw(self._conf.talisman, 'Withdraw 1')
                    yield from execution.delay_until(lambda: inventory.contains(self._conf.talisman), 3000)
                    self.log(f'withdrew {self._conf.talisman} from bank')
                else:
                    self.log(f'MuleCrafter: no {self._conf.talisman} in inventory or bank. Stopping.')
                    raise RuntimeError(f'MuleCrafter: {self._conf.talisman} not found')

    def _clean_mule_inventory(self):
        has_extra_items = len([i for i in inventory.items() if i.name and i.id != ESSENCE_ID]) > 0
        if has_extra_items:
            self.log('Mule inventory contains unauthorized items. Opening bank to clean inventory...')
            yield from self.walk_to(self._bank_tile, 3)
            opened = yield from bank.open_booth(self._bank_tile, BOOTH.name, BOOTH.op)
            if not opened:
                opened = yield from bank.open_nearest(BOOTH.name, BOOTH.op)
            if not opened:
                raise RuntimeError('MuleCrafter: Failed to open bank for initial inventory cleanup.')
            rune_id = item_id_named(inventory.items(), self._conf.rune)
            if rune_id == -1:
                rune_id = item_id_named(bank.items(), self._conf.rune)
            mule_keep = set([id for id in [ESSENCE_ID, rune_id] if id != -1])
            yield from bank.deposit_all_matching(lambda name, id: len(name) > 0 and not (id in mule_keep))
            yield from execution.delay_ticks(1)

    def on_progress_report(self):
        minutes = int((time.time() - self._started_at) / 60)
        return {'Status': f'{self._mode} — {self._status}', 'Runtime': f'{minutes}m', 'Rune': self._rune, 'Crafted': self._crafted,
                'Trades': self._trades, 'Essence': ess_count(), 'Runecraft xp': skills.xp('runecraft') - self._xp_at_start}

    def cfg(self):
        return self._conf

    def get_mode(self):
        return self._mode

    def get_bank_tile(self):
        return self._bank_tile

    def fill_bank(self):
        return self._bank_fill

    def set_status(self, s):
        self._status = s

    def count_craft(self, n):
        self._crafted += n

    def count_trade(self):
        self._trades += 1

    def has_partners(self):
        return len(self._partners) > 0

    def is_partner(self, name):
        return is_configured_partner(name, self._partners)

    def partner_names(self):
        return self._partners

    def nearest_partner(self):
        if not self.has_partners():
            return None
        return players.query().name(*self._partners).nearest()

    def mark_mule_traded(self, name):
        self._traded_mules.add(name.lower())

    def remaining_mules(self):
        return [p for p in self._partners if p.lower() not in self._traded_mules]

    def has_all_mules_traded(self):
        return len(self.remaining_mules()) == 0

    def reset_traded_mules(self):
        self._traded_mules.clear()

    def walk_to(self, dest, radius=2):
        here = game.tile()
        if here and dest.distance_to(here) <= radius:
            return
        if not game.ingame():
            self.log('walkTo: not ingame, waiting...')
            yield from execution.delay_until(lambda: game.ingame(), 30000)
        yield from traversal.walk_resilient(dest, radius=radius, attempts=6, timeout_ms=240000, log=lambda m: self.log(f'  {m}'))


# ── Crafter: at bank - ensure talisman + essence ────────────────────────────────
class CrafterAtBank(Task):
    def __init__(self, bot):
        super().__init__()
        self._bot = bot
        self._empty_reads = 0

    def validate(self):
        return self._bot.get_mode() == 'Crafter' and not in_temple() and not trade.active() and is_at_tile(self._bot.get_bank_tile(), 6) and (not inventory.contains(self._bot.cfg().talisman) or ess_count() == 0)

    def execute(self):
        self._bot.set_status('at bank - preparing')
        opened = yield from bank.open_booth(self._bot.get_bank_tile(), BOOTH.name, BOOTH.op)
        if not opened:
            opened = yield from bank.open_nearest(BOOTH.name, BOOTH.op)
        if not opened:
            self._bot.log('could not open the bank — retrying')
            return
        if not inventory.contains(self._bot.cfg().talisman):
            tal = ([i for i in bank.items() if (i.name or '').lower() == self._bot.cfg().talisman.lower()] or [None])[0]
            if tal and tal.name:
                bank.withdraw(self._bot.cfg().talisman, 'Withdraw 1')
                yield from execution.delay_until(lambda: inventory.contains(self._bot.cfg().talisman), 3000)
                self._bot.log(f'withdrew {self._bot.cfg().talisman}')
        has_ess = ess_count() > 0
        if not has_ess:
            yield from execution.delay_until(lambda: bank.loaded(), 3000)
            banked = bank.count(ESSENCE)
            if banked == 0:
                self._empty_reads += 1
                if self._empty_reads >= 3:
                    self._bot.request_finish('MuleCrafter: no essence left in the bank (three reads)')
                return
            self._empty_reads = 0
            max_take = min(inventory.free(), essence_per_trade(28, True), banked)
            yield from bank.withdraw_x(ESSENCE, max_take)
            yield from execution.delay_until(lambda: ess_count() > 0, 4000)
            self._bot.log(f'withdrew {ess_count()} essence from the bank')


# ── Crafter: walk to ruins ─────────────────────────────────────────────────────
class CrafterWalkToRuins(Task):
    def __init__(self, bot):
        super().__init__()
        self._bot = bot

    def validate(self):
        return self._bot.get_mode() == 'Crafter' and not in_temple() and not trade.active() and not is_at_tile(self._bot.cfg().ruins, 3)

    def execute(self):
        self._bot.set_status('walking to the ruins')
        yield from self._bot.walk_to(self._bot.cfg().ruins, 2)


# ── Crafter: enter altar ───────────────────────────────────────────────────────
class EnterAltar(Task):
    def __init__(self, bot):
        super().__init__()
        self._bot = bot
        self._fails = 0

    def validate(self):
        return self._bot.get_mode() == 'Crafter' and not in_temple() and ess_count() > 0 and not trade.active()

    def execute(self):
        self._bot.set_status('entering the altar')
        yield from self._bot.walk_to(self._bot.cfg().ruins, 1)
        ruins = locs.query().name(RUINS).nearest()
        talisman = inventory.first(self._bot.cfg().talisman)
        if not ruins or not talisman:
            yield from execution.delay_ticks(2)
            return
        self._bot.log(f'using the {self._bot.cfg().talisman} on the mysterious ruins')
        if not (talisman.use_on(ruins)):
            yield from execution.delay_ticks(2)
            return
        entered = yield from execution.delay_until(lambda: in_temple(), 10000)
        if entered:
            self._bot.log('entered the altar')
            self._fails = 0
            return
        self._fails += 1
        if self._fails >= 3:
            self._bot.request_finish("MuleCrafter: the talisman didn't teleport into the altar")


# ── Crafter: craft runes ────────────────────────────────────────────────────────
class CraftRunes(Task):
    def __init__(self, bot):
        super().__init__()
        self._bot = bot

    def validate(self):
        return self._bot.get_mode() == 'Crafter' and in_temple() and ess_count() > 0

    def execute(self):
        altar = locs.query().name(ALTAR.name).action(ALTAR.op).nearest()
        if not altar:
            self._bot.log('CraftRunes: no altar found')
            yield from execution.delay_ticks(2)
            return
        self._bot.set_status('crafting runes')
        before = ess_count()
        self._bot.log(f'crafting {before} essence at the altar')
        if not (altar.interact(ALTAR.op)):
            self._bot.log('CraftRunes: altar interact failed')
            yield from execution.delay_ticks(2)
            return
        yield from execution.delay_until(lambda: ess_count() == 0, 8000)
        made = before - ess_count()
        self._bot.count_craft(made)
        self._bot.log(f'crafted {made} {self._bot.cfg().rune}s - exiting temple')


# ── Crafter: exit altar (take portal back to ruins) ──────────────────────────────
class ExitAltar(Task):
    def __init__(self, bot):
        super().__init__()
        self._bot = bot

    def validate(self):
        return self._bot.get_mode() == 'Crafter' and in_temple() and ess_count() == 0

    def execute(self):
        self._bot.set_status('taking the portal out')
        self._bot.log('taking the portal back to the ruins')
        for i in range(15):
            if not in_temple():
                break
            if chat_dialog.can_continue():
                yield from chat_dialog.continue_()
                continue
            portal = locs.query().name(PORTAL.name).action(PORTAL.op).nearest()
            if portal:
                portal.interact(PORTAL.op)
            yield from execution.delay_ticks(1)
        if not in_temple():
            self._bot.log('back at the mysterious ruins')


# ── Crafter: wait at ruins for mule to arrive and trade ─────────────────────────────
class CrafterWaitAtRuins(Task):
    def __init__(self, bot):
        super().__init__()
        self._bot = bot

    def validate(self):
        return self._bot.get_mode() == 'Crafter' and not in_temple() and not trade.active() and is_at_tile(self._bot.cfg().ruins, 4) and inventory.count(self._bot.cfg().rune) > 0 and not self._bot.has_all_mules_traded()

    def execute(self):
        remaining = self._bot.remaining_mules()
        self._bot.set_status(f"waiting for mules: {', '.join(remaining)}")
        self._bot.log(f"CrafterWaitAtRuins: waiting for {', '.join(remaining)} — runes={inventory.count(self._bot.cfg().rune)}, traded={','.join(list(self._bot._traded_mules))}")
        yield from execution.delay_ticks(2)


# ── Crafter: request trade with next mule at ruins ──────────────────────────────────
class CrafterRequestTrade(Task):
    def __init__(self, bot):
        super().__init__()
        self._bot = bot

    def validate(self):
        return self._bot.get_mode() == 'Crafter' and not in_temple() and not trade.active() and is_at_tile(self._bot.cfg().ruins, 4) and inventory.count(self._bot.cfg().rune) > 0 and not self._bot.has_all_mules_traded()

    def execute(self):
        remaining = self._bot.remaining_mules()
        if len(remaining) == 0:
            return
        mule_name = remaining[0]
        mule = players.query().name(mule_name).nearest()
        if not mule or not mule.name:
            self._bot.set_status(f'waiting for {mule_name} at ruins')
            yield from execution.delay_ticks(2)
            return
        self._bot.set_status(f'requesting trade with {mule_name}')
        requested = trade.request(mule_name)
        self._bot.log(f'CrafterRequestTrade: Trade.request({mule_name}) returned {requested}')
        done = yield from execution.delay_until(lambda: trade.active(), 4000)
        if done:
            self._bot.log(f'CrafterRequestTrade: trade became active with {mule_name}')
        else:
            self._bot.log('CrafterRequestTrade: trade did not become active within 4s')


# ── Crafter: trade with ONE mule at ruins ───────────────────────────────────────
class CrafterTradeAtRuins(Task):
    def __init__(self, bot):
        super().__init__()
        self._bot = bot

    def validate(self):
        return self._bot.get_mode() == 'Crafter' and trade.active() and self._bot.has_partners()

    def execute(self):
        if trade.on_confirm_screen():
            self._bot.set_status('confirming trade')
            before_ess = ess_count()
            accepted = trade.accept()
            self._bot.log(f'CrafterTradeAtRuins: confirm-screen accept returned {accepted}')
            done = yield from execution.delay_until(lambda: not trade.active(), 3000)
            if done:
                got = ess_count() - before_ess
                self._bot.log(f'CrafterTradeAtRuins: trade closed, essCount went {before_ess} -> {ess_count()} (delta {got})')
                if got > 0:
                    self._bot.count_trade()
                    self._bot.log(f'received {got} essence')
                    who = trade.partner()
                    if who:
                        self._bot.mark_mule_traded(who)
                        self._bot.log(f'marked {who} as traded (confirm complete)')
                else:
                    self._bot.log('CrafterTradeAtRuins: trade closed but got 0 essence — trade may have failed')
            else:
                self._bot.log('CrafterTradeAtRuins: trade still active after 3s wait on confirm')
            return
        if not trade.on_offer_screen():
            self._bot.set_status('waiting for trade screen')
            yield from execution.delay_ticks(1)
            return
        who = trade.partner()
        if who is None:
            self._bot.set_status('reading trade partner')
            yield from execution.delay_ticks(1)
            return
        if not self._bot.is_partner(who):
            self._bot.set_status(f'declining trade from {who}')
            self._bot.log(f'declining a trade from \'{who}\' — not a configured mule')
            yield from trade.decline()
            return
        state = classify_mule_state(trade.their_offer())
        self._bot.log(f'CrafterTradeAtRuins: offer screen with {who}, their offer state={state}, my runes={inventory.count(self._bot.cfg().rune)}, my ess={ess_count()}')
        if state == 'has-essence':
            talisman_name = self._bot.cfg().talisman
            to_offer = [i for i in inventory.items() if i.name and i.name.lower() != talisman_name.lower()]
            unique_names = list(set([i.name for i in to_offer]))
            if len(unique_names) > 0:
                self._bot.set_status(f'offering {len(unique_names)} item type(s) to {who}')
                for name in unique_names:
                    ok = trade.offer_all(name)
                    self._bot.log(f'CrafterTradeAtRuins: offered {name} returned {ok}')
                    yield from execution.delay_ticks(1)
            else:
                self._bot.set_status(f'accepting essence from {who} (nothing to offer)')
            accepted = trade.accept()
            self._bot.log(f'CrafterTradeAtRuins: offer-screen accept returned {accepted}')
            return
        self._bot.set_status(f'waiting for {who}\'s offer')
        self._bot.log(f'CrafterTradeAtRuins: waiting for {who} to offer essence (their offer: {[(i.name, i.count) for i in trade.their_offer()]})')
        yield from execution.delay_ticks(1)


# ── Crafter: go to the bank ─────────────────────────────────────────────────────
class CrafterGoBank(Task):
    def __init__(self, bot):
        super().__init__()
        self._bot = bot
        self._empty_reads = 0

    def validate(self):
        return self._bot.get_mode() == 'Crafter' and not in_temple() and not trade.active() and (is_at_tile(self._bot.get_bank_tile(), 6) or (inventory.count(self._bot.cfg().rune) > 0 and not is_at_tile(self._bot.cfg().ruins, 4) and self._bot.has_partners()) or (ess_count() == 0 and not self._bot.has_partners()) or (self._bot.has_partners() and self._bot.has_all_mules_traded() and is_at_tile(self._bot.cfg().ruins, 4)))

    def execute(self):
        if not self._bot.fill_bank():
            self._bot.reset_traded_mules()
            self._bot.set_status('resetting traded mules (bankFill=false)')
            return
        if not is_at_tile(self._bot.get_bank_tile(), 6):
            self._bot.set_status('walking to the bank')
            yield from self._bot.walk_to(self._bot.get_bank_tile(), 3)
        self._bot.set_status('banking')
        opened = yield from bank.open_booth(self._bot.get_bank_tile(), BOOTH.name, BOOTH.op)
        if not opened:
            opened = yield from bank.open_nearest(BOOTH.name, BOOTH.op)
        if not opened:
            self._bot.log('could not open the bank — retrying')
            return
        runes_held = inventory.count(self._bot.cfg().rune)
        yield from bank.deposit_all_matching(lambda name, id: name == self._bot.cfg().rune)
        yield from execution.delay_ticks(1)
        if runes_held > 0:
            self._bot.log(f'deposited {runes_held} {self._bot.cfg().rune}s')

        tid = item_id_named(bank.items(), self._bot.cfg().talisman)
        crafter_keep_ids = set([id for id in [tid, ESSENCE_ID] if id != -1])
        before_clean = inventory.used()
        yield from bank.deposit_all_matching(lambda name, id: len(name) > 0 and not (id in crafter_keep_ids))
        if inventory.used() < before_clean:
            self._bot.log(f'cleared {before_clean - inventory.used()} slot(s)')
        if not inventory.contains(self._bot.cfg().talisman):
            tal = ([i for i in bank.items() if (i.name or '').lower() == self._bot.cfg().talisman.lower()] or [None])[0]
            if tal and tal.name:
                bank.withdraw(self._bot.cfg().talisman, 'Withdraw 1')
                yield from execution.delay_until(lambda: inventory.contains(self._bot.cfg().talisman), 3000)
        if self._bot.fill_bank() and ess_count() == 0:
            yield from execution.delay_until(lambda: bank.loaded(), 3000)
            banked = bank.count(ESSENCE)
            if banked == 0:
                if ess_count() == 0:
                    self._empty_reads += 1
                if ess_count() == 0 and self._empty_reads >= 3:
                    self._bot.request_finish('MuleCrafter: no essence left in the bank (three reads)')
                return
            self._empty_reads = 0
            max_take = min(inventory.free(), essence_per_trade(28, True), banked)
            yield from bank.withdraw_x(ESSENCE, max_take)
            yield from execution.delay_until(lambda: ess_count() > 0, 4000)
            self._bot.log(f'withdrew {ess_count()} essence from the bank')
        self._bot.reset_traded_mules()


# ── Mule: go to the bank ────────────────────────────────────────────────────────
class MuleGoBank(Task):
    def __init__(self, bot):
        super().__init__()
        self._bot = bot
        self._empty_reads = 0

    def validate(self):
        return self._bot.get_mode() == 'Mule' and not trade.active() and (inventory.count(self._bot.cfg().rune) > 0 or (ess_count() == 0 and not is_at_tile(self._bot.cfg().ruins, 5)) or (is_at_tile(self._bot.get_bank_tile(), 6) and (inventory.count(self._bot.cfg().rune) > 0 or ess_count() == 0)))

    def execute(self):
        if not is_at_tile(self._bot.get_bank_tile(), 6):
            self._bot.set_status('walking to the bank')
            yield from self._bot.walk_to(self._bot.get_bank_tile(), 3)
        self._bot.set_status('banking')
        opened = yield from bank.open_booth(self._bot.get_bank_tile(), BOOTH.name, BOOTH.op)
        if not opened:
            opened = yield from bank.open_nearest(BOOTH.name, BOOTH.op)
        if not opened:
            self._bot.log('could not open the bank — retrying')
            return
        runes_held = inventory.count(self._bot.cfg().rune)
        if runes_held > 0:
            bank.deposit(self._bot.cfg().rune, 'Deposit All')
            yield from execution.delay_ticks(1)
            self._bot.log(f'deposited {runes_held} {self._bot.cfg().rune}s')
            self._bot.count_trade()
        mule_keep = set([ESSENCE_ID])
        before = inventory.used()
        yield from bank.deposit_all_matching(lambda name, id: len(name) > 0 and not (id in mule_keep))
        if inventory.used() < before:
            self._bot.log(f'cleared {before - inventory.used()} slot(s)')
        yield from execution.delay_until(lambda: bank.loaded(), 3000)
        banked = bank.count(ESSENCE)
        if banked == 0 and ess_count() == 0:
            self._empty_reads += 1
            if self._empty_reads >= 3:
                self._bot.request_finish('MuleCrafter: out of essence in the bank (three reads)')
            return
        self._empty_reads = 0
        if ess_count() > 0:
            return
        max_take = min(inventory.free(), essence_per_trade(28, False), banked)
        yield from bank.withdraw_x(ESSENCE, max_take)
        yield from execution.delay_until(lambda: ess_count() > 0, 4000)
        self._bot.log(f'withdrew {ess_count()} essence from the bank')


# ── Mule: walk to ruins ─────────────────────────────────────────────────────────
class MuleWalkToRuins(Task):
    def __init__(self, bot):
        super().__init__()
        self._bot = bot

    def validate(self):
        return self._bot.get_mode() == 'Mule' and not trade.active() and not is_at_tile(self._bot.cfg().ruins, 3) and ess_count() > 0

    def execute(self):
        self._bot.set_status('walking to the ruins')
        yield from self._bot.walk_to(self._bot.cfg().ruins, 2)


# ── Mule: initiate trade with Crafter at ruins ──────────────────────────────────
class MuleTradeWithCrafter(Task):
    def __init__(self, bot):
        super().__init__()
        self._bot = bot

    def validate(self):
        return self._bot.get_mode() == 'Mule' and not trade.active() and is_at_tile(self._bot.cfg().ruins, 4) and ess_count() > 0

    def execute(self):
        crafter = self._bot.nearest_partner()
        if not crafter or not crafter.name:
            self._bot.set_status('waiting for crafter at ruins')
            yield from execution.delay_ticks(2)
            return
        self._bot.set_status(f'requesting trade with {crafter.name}')
        requested = trade.request(crafter.name)
        self._bot.log(f'MuleTradeWithCrafter: Trade.request({crafter.name}) returned {requested}')
        done = yield from execution.delay_until(lambda: trade.active(), 4000)
        if done:
            self._bot.log(f'MuleTradeWithCrafter: trade became active with {crafter.name}')
        else:
            self._bot.log('MuleTradeWithCrafter: trade did not become active within 4s')


# ── Mule: handle an active trade window (offer essence, accept, confirm) ─────────
class MuleTradeExecute(Task):
    def __init__(self, bot):
        super().__init__()
        self._bot = bot
        self._before_ess = 0

    def validate(self):
        return self._bot.get_mode() == 'Mule' and trade.active()

    def execute(self):
        if trade.on_offer_screen():
            who = trade.partner()
            if who is None:
                self._bot.set_status('reading trade partner')
                yield from execution.delay_ticks(1)
                return
            if not self._bot.is_partner(who):
                self._bot.set_status(f'declining trade from {who}')
                self._bot.log(f'declining a trade from \'{who}\' — not the crafter')
                yield from trade.decline()
                return
            self._bot.log(f'MuleTradeExecute: offer screen with {who}, myOffer.length={len(trade.my_offer())}, ess={ess_count()}, runes={inventory.count(self._bot.cfg().rune)}')
            if len(trade.my_offer()) == 0:
                held = ess_count()
                if held <= 0:
                    self._bot.set_status('no essence to offer')
                    self._bot.log('MuleTradeExecute: held 0 essence, waiting')
                    yield from execution.delay_ticks(1)
                    return
                self._before_ess = held
                self._bot.set_status('offering essence')
                self._bot.log(f'MuleTradeExecute: trade open — offering {held} essence')
                offered = trade.offer_all(ESSENCE, lambda i: i.id == ESSENCE_ID)
                self._bot.log(f'MuleTradeExecute: Trade.offerAll returned {offered}')
            else:
                self._bot.set_status('accepting the offer')
                accepted = trade.accept()
                self._bot.log(f'MuleTradeExecute: offer-screen accept returned {accepted}')
            return
        if trade.on_confirm_screen():
            self._bot.set_status('confirming the trade')
            self._bot.log(f'MuleTradeExecute: confirm screen, beforeEss={self._before_ess}')
            accepted = trade.accept()
            self._bot.log(f'MuleTradeExecute: confirm-screen accept returned {accepted}')
            done = yield from execution.delay_until(lambda: not trade.active(), 2500)
            if done and self._before_ess > 0:
                delivered = self._before_ess - ess_count()
                self._bot.log(f'MuleTradeExecute: trade closed, delivered {delivered} essence (beforeEss={self._before_ess}, ess now={ess_count()})')
                if delivered > 0:
                    self._bot.count_trade()
                    self._bot.log(f'delivered {delivered} essence to the crafter')
                self._before_ess = 0
            else:
                self._bot.log('MuleTradeExecute: trade still active or beforeEss was 0 after confirm accept')


BOT = define_bot(
    name='MuleCrafter',
    create=MuleCrafter,
    description='Crafter + mule runecrafting loop — both run bank→ruins→bank each cycle. Crafter has the talisman, crafts at the altar, trades runes for essence at the ruins. Mule ferries essence to the ruins and runes back to the bank. Dry mule signals at the bank and the crafter shares 1/N essence. Multi-mule round-robin with comma-separated partner names.',
    category='Runecrafting',
    tags=['runecrafting', 'trade', 'crafter', 'mule', 'falador', 'edgeville'],
    settings_schema=SETTINGS,
)
