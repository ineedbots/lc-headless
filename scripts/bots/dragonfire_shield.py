"""Ported from rs2b0t's src/bot/scripts/DragonfireShield/DragonfireShield.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.bank import bank
from rs2004.bot import TaskBot
from rs2004.catalogs.record import Record
from rs2004.catalogs.tasks import ContinueDialog
from rs2004.dialogue import chat_dialog, modals
from rs2004.entities import ground_items, npcs
from rs2004.execution import event_signal
from rs2004.game import game, reader
from rs2004.geometry import Tile
from bots.dragonfireshield.logic import BOOTH, BOOTH_OP, SHIELD, COINS_ID
from bots.dragonfireshield.logic import BANK_REACH, BANK_STAND, DUKE, DUKE_STAND, GATE_FEE, MAX_TALK_GUARD
from bots.dragonfireshield.logic import PRINCE_ALI_QUEST, SHIELD_ID, STAND_REACH, decide
from rs2004.items import equipment, inventory
from rs2004.reach import talk_op
from rs2004.tabs import quests
from rs2004.traversal import traversal

__all__ = ['SETTINGS', 'DragonfireShield']




TALK_OPEN_MS = 8000
RECEIVE_MS = 6000
WALK_MS = 180000
SETTINGS = {
    'trip_secs': SettingDef('number', 50, min=20, max=600, label='Farm seconds per trip', help='How long each trip keeps taking free shields from Duke Horacio before looting the floor pile and banking'),
    'carry_notes': SettingDef('boolean', True, label='Carry noted shields', help='Withdraws the banked noted Dragonfire shield stack to carry to the Duke each trip'),
}


def shield_is_note(item):
    return item.id != SHIELD_ID


class DragonfireShield(TaskBot):
    loop_delay = 600
    _status = 'starting'
    farmed = 0
    trips = 0
    trip_active = False
    trip_deadline = 0
    first_drop_at = 0
    redropped_at = 0
    note_id = -1
    trip_secs = 50
    carry_notes = True
    gate_fee = 0
    initial_setup_done = False
    has_banked_shields = False

    def __init__(self):
        self._started_at = _core.step_time()

    def on_start(self):
        yield from execution.delay_until(lambda: game.ingame() and game.tile() is not None, 0)
        self._started_at = _core.step_time()
        self.trip_secs = self.settings.num('trip_secs', 50)
        self.carry_notes = self.settings.bool('carry_notes', True)
        self.note_id = self.find_note_id()
        yield from execution.delay_until(lambda: quests.status(PRINCE_ALI_QUEST) != 'unknown', 5000)
        self.gate_fee = (0 if quests.status(PRINCE_ALI_QUEST) == 'complete' else GATE_FEE)
        self.log(f"DragonfireShield: {self.trip_secs}s trips, carrying notes: {self.carry_notes}, note obj {('(none)' if self.note_id == -1 else f'#{self.note_id}')}, " + f'Prince Ali Rescue={quests.status(PRINCE_ALI_QUEST)} gate fee={self.gate_fee}')
        self.add(ContinueDialog(), LootShields(self), FarmShields(self), BankTrip(self), GoToDuke(self))

    def recovery_anchor(self):
        return BANK_STAND


    def on_progress_report(self):
        return {'status': self._status, 'farmed': self.farmed, 'trips': self.trips}

    def set_status(self, s):
        self._status = s

    def find_note_id(self):
        note = ([o for o in reader.obj_catalog() if o.note_of == SHIELD_ID] or [None])[0]
        return (note.id if note else -1)

    def at_stand(self):
        here = game.tile()
        return here is not None and here.level == DUKE_STAND.level and DUKE_STAND.distance_to(here) <= STAND_REACH

    def at_bank(self):
        here = game.tile()
        return here is not None and here.level == BANK_STAND.level and BANK_STAND.distance_to(here) <= BANK_REACH

    def notes_held(self):
        return (0 if self.note_id == -1 else inventory.count_by_id(self.note_id))

    def junk_held(self):
        used = inventory.used()
        un_noted = inventory.count_by_id(SHIELD_ID)
        coins = inventory.count_by_id(COINS_ID)
        return max(0, used - un_noted - min(used, (1 if self.notes_held() > 0 else 0)) - min(used, (1 if coins > 0 else 0)))

    def ground_shields(self):
        return ground_items.query().within_of(DUKE_STAND, 1).where(lambda g: g.tile().level == DUKE_STAND.level and (g.id == SHIELD_ID or g.id == self.note_id)).results()

    def can_loot(self, g):
        if inventory.free() > 0:
            return True
        held = inventory.count_by_id(g.id) > 0
        stacks = any([o.id == g.id and (o.stackable or o.stack_variant) for o in reader.obj_catalog()])
        return held and stacks

    def close_modals_once(self):
        for i in range(3):
            if not (modals.is_open()):
                break
            yield from modals.close()

    def drop_by_id(self, id):
        for guard in range(40):
            it = ([i for i in inventory.items() if i.id == id] or [None])[0]
            if not it:
                return
            before = inventory.count_by_id(id)
            clicked = it.interact('Drop')
            dropped = yield from execution.delay_until(lambda: inventory.count_by_id(id) < before, 3000)
            self.log(f'drop #{id}: {before} -> {inventory.count_by_id(id)} (clicked={clicked} dropped={dropped})')
            if not clicked:
                yield from execution.delay_ticks(1)

    def drop_farm_cargo(self):
        """Drop every farm item (notes and un-noted shields) so the pack is clear to keep receiving."""
        yield from self.drop_by_id(SHIELD_ID)
        if self.note_id != -1:
            yield from self.drop_by_id(self.note_id)

    def open_duke(self):
        npc = npcs.query().name(DUKE).where(lambda n: talk_op(n.actions()) is not None).nearest()
        if not npc:
            self.log('openDuke: no Duke Horacio in the scene')
            return False
        op = talk_op(npc.actions())
        t = npc.tile()
        self.log(f'openDuke: interact \'{op}\' @ {t.x},{t.z},{t.level}')
        npc.interact(op)
        opened = yield from execution.delay_until(lambda: chat_dialog.is_open() or chat_dialog.can_continue(), TALK_OPEN_MS)
        self.log(f'openDuke: opened={opened} canContinue={chat_dialog.can_continue()} options={len(chat_dialog.options())}')
        return opened

    def duke_gives_shield(self):
        """Drive one full Duke conversation, picking the "I seek a shield..." option, until the dialogue closes."""
        steps = 0
        saw_options = []
        for i in range(MAX_TALK_GUARD):
            if chat_dialog.can_continue():
                steps += 1
                yield from chat_dialog.continue_()
                yield from execution.delay_ticks(1)
                continue
            opts = chat_dialog.options()
            if len(opts) > 0:


                pick = ([o for o in opts if ('shield' in o.lower())] or [None])[0]
                saw_options = opts
                self.log(f"duke dialog: options=[{' | '.join(opts)}] pick='{(pick if pick is not None else opts[0])}'")
                yield from chat_dialog.choose_option((pick if pick is not None else opts[0]))
                yield from execution.delay_ticks(2)
                continue
            if not chat_dialog.is_open():
                break
            yield from execution.delay_ticks(1)
        modals_before = modals.is_open()
        yield from self.close_modals_once()
        self.log(f'duke dialog: done steps={steps} optionsSeen={len(saw_options)} modals {modals_before}->{modals.is_open()}')
        return not chat_dialog.is_open()

    def pack(self):
        un_noted = inventory.count_by_id(SHIELD_ID)
        notes = self.notes_held()
        coins = inventory.count_by_id(COINS_ID)
        used = inventory.used()
        return Record({
            'at_stand': self.at_stand(),
            'at_bank': self.at_bank(),
            'full': inventory.is_full(),
            'free': inventory.free(),
            'un_noted': un_noted,
            'notes': notes,
            'junk': max(0, used - un_noted - min(used, (1 if notes > 0 else 0)) - min(used, (1 if coins > 0 else 0))),
            'ground': (len(self.ground_shields()) if self.at_stand() and not self.trip_active else 0),
            'trip_active': self.trip_active,
            'want_notes': self.carry_notes,
            'has_banked_shields': self.has_banked_shields,
        })

    def step(self):
        return decide(self.pack())


class FarmShields:
    def __init__(self, bot):
        self._bot = bot

    def validate(self):
        p = self._bot.pack()
        if not p.at_stand or p.full:
            return False
        if p.trip_active:
            return True
        # Why: the floor pile is the depot, so the farm keeps adding to it across windows; only the pack has to be clear.
        if p.un_noted > 0 or p.junk > 0:
            return False
        return p.free >= 1

    def execute(self):
        bot = self._bot
        here = game.tile()
        bot.log(f"FarmShields: start @ {(f'{here.x},{here.z},{here.level}' if here else '?')} free={inventory.free()} unNoted={inventory.count_by_id(SHIELD_ID)} notes={bot.notes_held()} ground={len(bot.ground_shields())}")
        if not bot.trip_active:
            bot.set_status('starting a farm trip')
            yield from bot.drop_farm_cargo()
            bot.trip_active = True
            bot.first_drop_at = 0
            bot.trip_deadline = _core.step_time() + bot.trip_secs * 1000
            bot.log(f'FarmShields: trip {bot.trip_secs}s window (anchored to the first drop), pack now free={inventory.free()}')
        cycles = 0
        while bot.trip_active and _core.step_time() < bot.trip_deadline and not inventory.is_full():
            if event_signal.pending() or not bot.at_stand() or chat_dialog.is_open():
                bot.log(f'FarmShields: breaking cycle (event={event_signal.pending()} atStand={bot.at_stand()} dialog={chat_dialog.is_open()})')
                break
            # Why: a ground pile that can already fill the pack makes more farming pointless, so end the trip and loot.
            if len(bot.ground_shields()) >= inventory.free():
                bot.log(f'FarmShields: ground pile can fill the pack ({len(bot.ground_shields())} >= {inventory.free()} free) — ending trip early')
                bot.trip_active = False
                break
            if equipment.contains(SHIELD):
                bot.log('FarmShields: shield is equipped — unequipping')
                yield from equipment.unequip(SHIELD)
            yield from bot.close_modals_once()
            if inventory.count_by_id(SHIELD_ID) > 0:
                yield from bot.drop_by_id(SHIELD_ID)
            before = inventory.count_by_id(SHIELD_ID)
            _c1 = bot.at_stand()
            if _c1:
                _w2 = yield from bot.open_duke()
                _c1 = (_w2)
            opened = _c1
            if not opened:
                bot.log(f'FarmShields: duke did not open a dialog (before={before}) — retry')
                yield from execution.delay_ticks(2)
                continue
            _w3 = yield from bot.duke_gives_shield()
            if not (_w3):
                bot.log('FarmShields: duke dialogue did not finish cleanly')
            got = yield from execution.delay_until(lambda: inventory.count_by_id(SHIELD_ID) > before, RECEIVE_MS)
            if not got:
                bot.log(f'FarmShields: no shield received (inv still {inventory.count_by_id(SHIELD_ID)}) — retry')
                yield from execution.delay_ticks(2)
                continue
            bot.log(f'FarmShields: shield received (inv {before} -> {inventory.count_by_id(SHIELD_ID)})')
            yield from bot.drop_by_id(SHIELD_ID)
            if bot.first_drop_at == 0:
                bot.first_drop_at = _core.step_time()
                bot.trip_deadline = bot.first_drop_at + bot.trip_secs * 1000
                bot.log(f'FarmShields: first drop @ +0s, window ends in {bot.trip_secs}s')
            bot.farmed += 1
            cycles += 1
            bot.set_status(f'farming ({bot.farmed} shields)')
        bot.trip_active = False
        bot.log(f'FarmShields: trip ended after {cycles} cycle(s), {bot.farmed} farmed, pack free={inventory.free()}')


class LootShields:
    def __init__(self, bot):
        self._bot = bot

    def validate(self):
        p = self._bot.pack()
        if not p.at_stand or p.trip_active or p.ground == 0:
            return False
        # Why: once the pack is full there is no room to pick up anything, so loot must let the bank take over.
        if p.full:
            return False
        # Why: after redropping a partial load, let the farm start the next window instead of
        # immediately re-picking the pile it just put down.
        return _core.step_time() - self._bot.redropped_at > 3000

    def execute(self):
        bot = self._bot
        bot.set_status('looting the shield pile')
        bot.log(f'LootShields: {len(bot.ground_shields())} ground stack(s), free={inventory.free()}')
        taken = 0
        for guard in range(80):
            pile = bot.ground_shields()
            if len(pile) == 0:
                break
            drop = pile[0]
            if not bot.can_loot(drop):
                bot.log(f'LootShields: cannot pick up #{drop.id} (pack free={inventory.free()}) — bank instead')
                break
            before = inventory.count_by_id(drop.id)
            clicked = drop.interact('Take')

            def _fn4():
                now = inventory.count_by_id(drop.id)
                still_there = any([g.id == drop.id and g.tile().x == drop.tile().x and g.tile().z == drop.tile().z for g in bot.ground_shields()])
                return now > before or not still_there
            got = yield from execution.delay_until(_fn4, 4000)
            bot.log(f'LootShields: take #{drop.id} clicked={clicked} got={got} inv={inventory.count_by_id(drop.id)}')
            taken += 1
        bot.log(f'LootShields: picked {taken} stack(s), free={inventory.free()}')
        # Why: a coin stack and any junk each cost a slot, so a full load is 28 minus those.
        capacity = 28 - ((1 if inventory.count_by_id(COINS_ID) > 0 else 0)) - bot.junk_held()
        used = inventory.used()
        if used >= capacity or inventory.is_full():
            bot.log(f'LootShields: pack {used}/{capacity} — full load, taking it to the bank')
            return
        bot.log(f'LootShields: pack {used}/{capacity} — partial, redropping to pile for another window')
        yield from bot.drop_farm_cargo()
        bot.redropped_at = _core.step_time()
        bot.log(f'LootShields: redropped, pack free={inventory.free()} ground={len(bot.ground_shields())}')


class BankTrip:
    def __init__(self, bot):
        self._bot = bot

    def validate(self):
        p = self._bot.pack()
        if p.full:
            return True
        # Why: a fresh start is bank-first, so the toll coins and noted shields are loaded before the first farm trip.
        if not self._bot.initial_setup_done:
            return True
        if p.at_stand and not p.trip_active and p.ground == 0 and (p.un_noted > 0 or p.notes > 0 or p.junk > 0):
            return True
        if p.at_bank and (p.un_noted > 0 or p.junk > 0 or (p.want_notes and p.has_banked_shields and p.notes == 0 and p.free > 0)):
            return True
        return False

    def execute(self):
        bot = self._bot
        bot.set_status('banking')
        bot.log(f'BankTrip: start atBank={bot.at_bank()} free={inventory.free()} unNoted={inventory.count_by_id(SHIELD_ID)} notes={bot.notes_held()}')
        if equipment.contains(SHIELD):
            bot.log('BankTrip: shield is equipped — unequipping')
            yield from equipment.unequip(SHIELD)
        if not bot.at_bank():
            walked = yield from traversal.walk_resilient(BANK_STAND, radius=2, attempts=4, timeout_ms=WALK_MS, log=lambda m: bot.log(f'  {m}'))
            bot.log(f'BankTrip: walk to Al Kharid bank = {walked}')
            if not walked:
                return
        _w6 = yield from bank.open_booth(BANK_STAND, BOOTH, BOOTH_OP)
        _c5 = (_w6)
        if not _c5:
            _w7 = yield from bank.open_nearest(BOOTH, BOOTH_OP)
            _c5 = (_w7)
        opened = _c5
        bot.log(f'BankTrip: bank open = {opened}')
        if not opened:
            return
        bot.initial_setup_done = True
        yield from bank.deposit_all_matching(lambda name, id: True)
        bot.log(f'BankTrip: deposited, pack free={inventory.free()}')
        banked = bank.count_by_id(SHIELD_ID) + ((0 if bot.note_id == -1 else bank.count_by_id(bot.note_id)))
        bot.has_banked_shields = banked > 0
        if bot.carry_notes and bot.note_id != -1:
            if banked > 0:
                yield from bank.set_note_mode(True)
                ok = True
                if bank.count_by_id(SHIELD_ID) > 0:
                    _w8 = yield from bank.withdraw_x_by_id(SHIELD_ID, bank.count_by_id(SHIELD_ID), bot.note_id)
                    ok = (_w8) and ok
                if bank.count_by_id(bot.note_id) > 0:
                    _w9 = yield from bank.withdraw_x_by_id(bot.note_id, bank.count_by_id(bot.note_id), bot.note_id)
                    ok = (_w9) and ok
                bot.log(f'BankTrip: bring all banked shields as notes ok={ok} notesHeld={bot.notes_held()} (bank had {banked})')
            else:
                bot.log('BankTrip: no shields in the bank to bring (farming from scratch)')
        elif bot.carry_notes and bot.note_id == -1:
            bot.log('BankTrip: no noted shield row found — farming without notes')
        if bot.gate_fee > 0:
            held_coins = inventory.count_by_id(COINS_ID)
            short = max(0, bot.gate_fee - held_coins)
            if short > 0:
                yield from bank.set_note_mode(False)
                bank_coins = bank.count_by_id(COINS_ID)
                took = min(short, bank_coins)
                if took > 0:
                    ok = yield from bank.withdraw_x_by_id(COINS_ID, took)
                    bot.log(f'BankTrip: gate fee {bot.gate_fee} - withdrew {took} coins (pack {inventory.count_by_id(COINS_ID)}) ok={ok}')
                else:
                    bot.log(f'BankTrip: gate fee {bot.gate_fee} but NO coins in the bank')
            else:
                bot.log(f'BankTrip: gate fee {bot.gate_fee} already held ({held_coins} coins)')
        yield from bank.close()
        yield from execution.delay_ticks(1)
        bot.trips += 1
        bot.log(f'trip {bot.trips}: total {bot.farmed} shield(s) farmed')


class GoToDuke:
    def __init__(self, bot):
        self._bot = bot

    def validate(self):
        p = self._bot.pack()
        if p.full:
            return False
        if p.at_stand:
            return False
        if p.at_bank and (p.un_noted > 0 or p.junk > 0 or (p.want_notes and p.has_banked_shields and p.notes == 0 and p.free > 0)):
            return False
        return True

    def execute(self):
        bot = self._bot
        bot.set_status('walking to Duke Horacio')
        walked = yield from traversal.walk_resilient(DUKE_STAND, radius=1, attempts=6, timeout_ms=WALK_MS, log=lambda m: bot.log(f'  {m}'))
        here = game.tile()
        bot.log(f"GoToDuke: walk done={walked} @ {(f'{here.x},{here.z},{here.level}' if here else '?')} atStand={bot.at_stand()}")


BOT = define_bot(
    name='DragonfireShield',
    description='Farms free anti-dragonbreath shields from Duke Horacio in Lumbridge Castle (requires the %dragon_shield var, unlocked by Oziach in the Dark Slayer quest) — drop-mode: un-noted shields are dropped at the Duke, looted and banked; noted shields are carried to seed the pile and freely drop-safe to the floor',
    category='Quest',
    tags=['dark slayer', 'dragonfire shield', 'antidragonbreath shield', 'duke horacio', 'certificates', 'faucet'],
    settings_schema=SETTINGS,
    create=DragonfireShield,
)
