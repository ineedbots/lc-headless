"""The quest engine, a Task: rs2b0t's api/ai/quests/engine/QuestEngine.ts (MIT, see thirdparty/rs2b0t), and its
docs/reference/quest-engine.md.

Each pass it reads the quest list, picks the first picked quest that's READY, banks the pack to nothing before a quest
starts, provisions it bank-first, asks its module for a step, runs it, and watches for progress. A quest that makes
none is parked, and one parked three times is given up for the session. A finished quest walks back to a bank.

The host is the bot driving it, and has log(m), verbose(), food_item(), picked_ids(), skip_pending(), consume_skip(),
consume_death(), note_state(rows, running_id, step_desc, no_progress, parked) and finish(reason)."""

import time

from rs2004 import execution
from rs2004.bank import bank
from rs2004.bot import Task
from rs2004.catalogs.record import Record
from rs2004.dialogue import chat_dialog, modals
from rs2004.execution import event_signal
from rs2004.game import game, skills
from rs2004.geometry import Tile
from rs2004.items import equipment, inventory
from rs2004.messages import game_messages
from rs2004.quests.data import QUESTS
from rs2004.quests.defs import QUEST_DEFS, def_by_id
from rs2004.quests.eligibility import evaluate
from rs2004.quests.engine.provisioning import COIN_FLOAT, coin_float_plan, deposit_plan, float_draw_plan, plan_provisioning
from rs2004.quests.engine.provisioning import should_freshen_pack
from rs2004.quests.engine.queue import QueueRow, next_quest, queue_rows
from rs2004.quests.engine.trace import FAIL_WARN, StepTracker, format_duration, format_tile, inv_delta
from rs2004.quests.engine.types import QuestSnapshot, quest_step
from rs2004.quests.engine.watchdog import NO_PROGRESS_PARK, NO_PROGRESS_WARN, ProgressWatchdog, progress_signature
from rs2004.quests.exec.steps import execute_step, run_maybe
from rs2004.quests.prayer import PRAYER_POTION, prayer_upkeep
from rs2004.quests.types import BankInventorySnapshot, PlayerState
from rs2004.tabs import quests

__all__ = ['PROVISION_BANK', 'COIN_FLOAT', 'describe_step', 'QuestEngine']

PARK_GIVE_UP = 3

WAIT_PARK = 15
COMBAT_STALL_MS = 60000

# Walks back to a bank to try before leaving the character where it finished.
RETREAT_GIVE_UP = 4

# Bank trips to try emptying the pack before a quest starts on whatever it's carrying.
FRESH_GIVE_UP = 3

PROVISION_BANK = Tile(3093, 3243, 0)

# Main-modal roots the engine mustn't close: Harold's dice in Death Plateau (death_dice), and the combination in the
# IOU's handwriting (messagescroll_handwriting). Ids from content/pack/interface.pack.
INTERACTIVE_QUEST_MAIN = set([6675, 8119])


def _now_ms():
    return time.time() * 1000


def bank_for(module):
    """None for 'nearest', which lets the step work it out from where the bot stands."""
    if module.bank == 'nearest':
        return None
    return module.bank if module.bank is not None else PROVISION_BANK


def advances_world(step):
    return step.kind != 'wait' and step.kind != 'done'


def describe_step(step):
    kind = step.kind
    if kind == 'talk':
        return f'talk to {step.stop.npc}'
    if kind == 'grab_ground':
        return f'grab {step.item}'
    if kind == 'pick_loc' or kind == 'interact_loc':
        return f'{step.op} {step.loc}'
    if kind == 'use_on':
        return f'use {step.item} on {step.target}'
    if kind == 'equip':
        return f'equip {step.item}'
    if kind == 'scan_bank':
        return 'check the bank'
    if kind == 'withdraw':
        return 'withdraw ' + ', '.join([f"{i['name']}×{i['qty']}" for i in step.items])
    if kind == 'deposit':
        # Family Crest banks its coin float mid-quest, so this isn't always previous-quest spillover.
        return f'bank all but {len(step.keep)} kept item type(s)'
    if kind == 'mine_rock':
        return f'mine {step.item}'
    if kind == 'buy':
        return f'buy {step.qty}× {step.item} from {step.shop.npc}'
    if kind == 'custom':
        return step.name
    if kind == 'wait':
        return step.reason
    return 'done'


def _counts_by_name(items):
    out = {}
    for it in items:
        if it.name:
            key = it.name.lower()
            out[key] = out.get(key, 0) + it.count
    return out


def _counts_by_id(items):
    out = {}
    for it in items:
        out[it.id] = out.get(it.id, 0) + it.count
    return out


class _SubLog:
    """A step's log: in verbose mode every line, else each distinct line once per announced step."""

    def __init__(self, engine, verbose):
        self.engine = engine
        self.verbose = verbose

    def __call__(self, m):
        # Verbose keeps the repeats: a sub-log that fires once per rock is the record of a mining leg.
        if self.verbose:
            self.engine.host.log(f'  {m}')
            return
        if m not in self.engine._step_sub_log:
            self.engine.host.log(f'  {m}')
            self.engine._step_sub_log.add(m)


class QuestEngine(Task):
    def __init__(self, host):
        Task.__init__(self, label='quest engine')
        self.host = host
        self._order = [d.record.id for d in QUEST_DEFS]
        self._records = [d.record for d in QUEST_DEFS]
        self._watchdog = ProgressWatchdog()
        self._failed_watchdog = ProgressWatchdog()
        self._pending_failed_signature = None
        self._no_progress_count = 0
        self._combat_idle_since = None
        self._combat_xp = 0
        self._parked = set()
        self._park_counts = {}
        self._parked_reasons = {}
        self._provisioned = set()
        self._retreated = set()
        self._retreat_tries = {}
        self._deposited = set()
        self._freshened = set()
        self._freshen_tries = {}
        self._food_drawn = set()
        self._potions_drawn = set()
        self._coins_drawn = set()
        self._blocked = {}
        # Modules that have already given their warn_readiness.
        self._readiness_warned = set()
        self._last_bank_counts = {}
        self._last_bank_id_counts = {}
        self._bank_known = False
        self.running_id = None
        self._wait_key = ''
        self._wait_count = 0
        self._last_step_logged = ''
        self._step_sub_log = set()
        self._tracker = StepTracker()
        self._tick = 0
        self._fail_streak = 0

    def _log(self, m):
        self.host.log(f'  {m}')

    def validate(self):
        return not chat_dialog.can_continue() and game.tile() is not None

    def execute(self):
        # Death participates in the event signal, so it's consumed before the signal is checked.
        recovered = yield from self._recover_death_if_pending()
        if recovered:
            return
        # Skip is applied before the random-event yield, so a mid-walk interrupt lands on the next quest instead of
        # spinning on event_signal.pending().
        skip_early = self.host.skip_pending()
        if not skip_early and event_signal.pending():
            yield from execution.delay_ticks(1)
            return
        # Bank-aware steps leave the bank open so this task can read it before the interface closes.
        if not skip_early and bank.is_open():
            yield from execution.delay_until(lambda: bank.loaded(), 3000)
            self._refresh_bank_counts(True)
            yield from modals.close()
            return
        # Why: quest-complete scrolls and similar leftovers sit on main and block the next decide() tick.
        # Why: interactive quest UIs also use main and must stay open (the Death Plateau dice and the combination
        # handwriting were being killed mid-step).
        main_modal = modals.main()
        if (not skip_early and main_modal != -1 and not bank.is_open() and not chat_dialog.is_make_menu()
                and not chat_dialog.is_main_make_panel() and main_modal not in INTERACTIVE_QUEST_MAIN):
            closed = yield from modals.close()
            if closed:
                self.host.log('closed a leftover main modal (quest-complete scroll)')
                return

        picked = self.host.picked_ids()
        self._refresh_bank_counts()
        player = self._read_player_state()
        item_snap = self._read_item_snapshot()
        elig = {}
        for r in self._records:
            elig[r.id] = evaluate(r, player, item_snap, quests.status(r.name))

        skip = self.host.consume_skip()
        if skip and self.running_id is not None:
            self._apply_user_skip(self.running_id, elig)

        if self.running_id is None:
            selectable = set([id for id in picked if id not in self._blocked])
            self.running_id = next_quest(self._order, selectable, elig, self._parked)
        rows = self._apply_blocked(queue_rows(self._order, picked, elig, self._parked, self.running_id))

        if self.running_id is None:
            self.host.note_state(rows, None, 'queue drained', self._no_progress_count, len(self._parked))
            for r in rows:
                why = ' — ' + '; '.join(r.reasons) if len(r.reasons) > 0 else ''
                self.host.log(f'  {r.name}: {r.status}{why}')
            self.host.finish('quest queue drained — nothing left to run (per-quest status logged above)')
            return

        id = self.running_id
        module = def_by_id(id)
        if module is None:
            self.host.log(f"ERROR: no module for '{id}' — blocking")
            self._block(id, ['internal: no module'])
            self.running_id = None
            return
        if id not in self._readiness_warned:
            self._readiness_warned.add(id)
            if module.on_start is not None:
                module.on_start()
            note = module.warn_readiness() if module.warn_readiness is not None else None
            if note:
                self.host.log(f'{module.record.name}: {note}')
        stage, progress = yield from self._read_stage(module)
        snap = self._build_snapshot(module, stage, progress)
        combat_active = self._combat_advancing(snap)

        if self._pending_failed_signature is not None:
            if not combat_active and progress_signature(snap) == self._pending_failed_signature:
                self.host.log(f'no progress after {self._no_progress_count} steps on {module.record.name}')
                self._park_or_give_up(id, module.record.name)
                self._reset_watchdog()
                self.running_id = None
                return
            self._pending_failed_signature = None
            self._failed_watchdog.reset()
            self._no_progress_count = 0
            snap.no_progress = 0

        # Why: a fight shaped as a step returns here every pass, so this is the only place its prayer can be held.
        # Why: the server runs one op per tick, so a pass that prays yields instead of also swinging.
        prayed = yield from prayer_upkeep()
        if prayed:
            return

        freshened = yield from self._freshen_pack(module, id, snap, rows)
        if freshened:
            return

        if module.owns_inventory:
            # Some quests have one-way, bankless areas, so their stage oracle runs before any generic spillover banking
            # or provisioning on the mainland.
            self._deposited.add(id)
            self._provisioned.add(id)

        if snap.journal == 'complete':
            # Why: quests end in lairs, the wilderness and dungeons, and a bot left standing there dies there.
            # Why: the job is done when the character is standing at a bank.
            if id not in self._retreated:
                retreated = yield from self._retreat_to_bank(module, id, rows)
                if not retreated:
                    return
            self.host.log(f'{module.record.name} COMPLETE — {quests.points()} QP')
            self._parked.discard(id)
            for table in [self._parked_reasons, self._park_counts, self._freshen_tries, self._blocked]:
                if id in table:
                    del table[id]
            for latch in [self._provisioned, self._deposited, self._freshened, self._food_drawn, self._potions_drawn, self._coins_drawn]:
                latch.discard(id)
            self._reset_watchdog()
            self.running_id = None
            done = self._apply_blocked(queue_rows(self._order, picked, elig, self._parked, None))
            self.host.note_state(done, None, f'{module.record.name} complete', 0, len(self._parked))
            return

        step = None
        if id not in self._deposited:
            food_name = self.host.food_item()
            keep = [i.name.lower() for i in module.record.items] + [t.lower() for t in (module.tools or [])]
            if food_name:
                keep.append(food_name.lower())
            spillover = deposit_plan(snap.inv, keep)
            if len(spillover) == 0:
                self._deposited.add(id)
            else:
                self.host.note_state(rows, id, 'banking spillover', self._no_progress_count, len(self._parked))
                banked = yield from execute_step(quest_step('deposit', keep=keep, bank=bank_for(module), leave_open=True), module.hops or [], self._log)
                if banked:
                    self._deposited.add(id)
                yield from execution.delay_until(lambda: bank.loaded(), 3000)
                self._refresh_bank_counts(True)
                yield from modals.close_if_open()
                return
        if id not in self._provisioned:
            step = self._provision_step(module, id, snap, picked, elig)
            if step is None:
                return
        else:
            step = module.decide(snap)

        step_desc = describe_step(step)
        self.host.note_state(rows, id, step_desc, self._no_progress_count, len(self._parked))

        verbose = self.host.verbose()
        now = _now_ms()
        attempt = self._tracker.open(f'{id}|{step_desc}', now)
        step_line = f'{module.record.name}: {step_desc}'
        fresh = step_line != self._last_step_logged
        # Why: re-deciding the same step is how this engine loops, so repeats are silent by default.
        # Why: the heartbeat stops a long mine, smelt and hammer chain, all called 'smith 8 nails', from looking like a
        # hang.
        announce = verbose or fresh or self._tracker.beat(now)
        if announce:
            stage_text = snap.stage if snap.stage is not None else '?'
            context = f'stage {stage_text} · {format_tile(snap.tile)} · {snap.free_slots} free'
            repeat = f' — attempt {attempt}, {format_duration(self._tracker.elapsed(now))} on this step' if attempt > 1 else ''
            prefix = ''
            if verbose:
                self._tick += 1
                prefix = f'[t{self._tick}] '
            self.host.log(f'{prefix}{step_line}{repeat} · {context}')
            self._last_step_logged = step_line
            self._step_sub_log = set()
            if module.observe is not None:
                for line in module.observe(snap, step):
                    self.host.log(f'  {line}')

        if step.kind == 'wait':
            key = f'{id}|{step.reason}'
            self._wait_count = self._wait_count + 1 if key == self._wait_key else 1
            self._wait_key = key
            if self._wait_count >= WAIT_PARK:
                self.host.log(f"{module.record.name} waiting on '{step.reason}' with no way to resolve it — parking")
                self._parked_reasons[id] = [f'waiting: {step.reason}']
                self._park_or_give_up(id, module.record.name)
                self._reset_watchdog()
                self.running_id = None
                self._wait_key = ''
                self._wait_count = 0
                return
        else:
            self._wait_key = ''
            self._wait_count = 0

        run_step = step
        if step.kind == 'withdraw' or step.kind == 'deposit':
            run_step = self._with_field(step, 'leave_open', True)
        started_at = _now_ms()
        ok = yield from execute_step(run_step, module.hops or [], _SubLog(self, verbose))
        took = _now_ms() - started_at

        # Why: a cooperative step may have returned because death interrupted it.
        recovered = yield from self._recover_death_if_pending()
        if recovered:
            return

        if announce or not ok:
            after = self._build_snapshot(module, stage, progress)
            self.host.log(f"  → {'ok' if ok else 'FAILED'} in {format_duration(took)} · {inv_delta(snap.inv, after.inv)}")
            if not ok and module.observe is not None:
                for line in module.observe(after, step):
                    self.host.log(f'  {line}')

        if ok:
            self._fail_streak = 0
            self._failed_watchdog.reset()
        else:
            self._fail_streak += 1
            if self._fail_streak % FAIL_WARN == 0:
                self.host.log(f"WARN: '{step_desc}' has failed {self._fail_streak}x in a row over {format_duration(self._tracker.elapsed(_now_ms()))}")

        if bank.is_open():
            yield from execution.delay_until(lambda: bank.loaded(), 3000)
            self._refresh_bank_counts(True)
            yield from modals.close()

        if advances_world(step):
            after = self._build_snapshot(module, stage, progress)
            signature = progress_signature(after)
            combat_active = self._combat_advancing(after)
            if combat_active:
                self._watchdog.reset()
                self._failed_watchdog.reset()
            if combat_active:
                count = 0
            elif ok:
                count = self._watchdog.note(signature)
            else:
                count = self._failed_watchdog.note_failure(progress_signature(snap), signature)
            self._no_progress_count = count
            if count == NO_PROGRESS_WARN:
                self.host.log(f'WARN: {count} steps with no progress on {module.record.name} — check the decide()/prefer lists')
            elif count >= NO_PROGRESS_PARK and not ok and (module.read_progress is not None or module.read_stage is not None):
                # Why: journal oracles can open and close modals; confirm on the next normal read, not with an extra
                # post-step action.
                self._pending_failed_signature = signature
            elif count >= NO_PROGRESS_PARK:
                self.host.log(f'no progress after {count} steps on {module.record.name}')
                self._park_or_give_up(id, module.record.name)
                self._reset_watchdog()
                self.running_id = None

        self._refresh_bank_counts()
        yield from execution.delay_ticks(1)

    @staticmethod
    def _with_field(step, key, value):
        """A copy of the step with one field set."""
        fields = {}
        for k in step.keys():
            fields[k] = getattr(step, k)
        fields[key] = value
        return Record(fields)

    def _read_stage(self, module):
        """(stage, progress) from the module's oracle, either of them None. Use with yield from."""
        progress = None
        if module.read_progress is not None:
            progress = yield from run_maybe(module.read_progress())
        if progress is not None:
            return progress.stage, progress
        stage = None
        if module.read_stage is not None:
            stage = yield from run_maybe(module.read_stage())
        return stage, None

    def _provision_step(self, module, id, snap, picked, elig):
        """The provisioning block's step, or None when it parked or blocked the quest this pass."""
        # Why: a quest restarted mid-way may be wearing what it provisioned, Black Knights' Fortress its disguise, and
        # counting the pack alone read the worn pieces as missing and gave the quest up; rs2b0t counts the pack alone.
        held = {name: snap.inv[name] for name in snap.inv}
        for name in snap.worn:
            held[name] = held.get(name, 0) + 1
        plan = plan_provisioning(module.record.items, held, self._last_bank_counts)
        # Why: restoring the float after every purchase made a 10gp gate emit withdraw Coins every tick while egg,
        # milk and flour were outstanding.
        coin_target = module.coin_float if module.coin_float is not None else COIN_FLOAT
        coin_plan = coin_float_plan(snap.inv.get('coins', 0), self._last_bank_counts.get('coins', 0), coin_target, id in self._coins_drawn)
        extras = []
        if coin_plan['drawn']:
            self._coins_drawn.add(id)
        elif coin_plan['qty'] > 0:
            extras.append({'name': 'Coins', 'qty': coin_plan['qty']})
        food_item = self.host.food_item()
        # Only withdraw food once the bank is known; a guessed shortfall forces a failed booth trip and can scramble a
        # full pack.
        food_ready = module.food_ready(snap) if module.food_ready is not None else True
        if module.food and food_item and self._bank_known and food_ready:
            key = food_item.lower()
            food_plan = float_draw_plan(snap.inv.get(key, 0), self._last_bank_counts.get(key, 0), module.food, id in self._food_drawn)
            if food_plan['drawn']:
                self._food_drawn.add(id)
            elif food_plan['qty'] > 0:
                extras.append({'name': food_item, 'qty': food_plan['qty']})
        potions = module.pray.potions if module.pray is not None else None
        if potions and self._bank_known:
            key = PRAYER_POTION.lower()
            potion_plan = float_draw_plan(snap.inv.get(key, 0), self._last_bank_counts.get(key, 0), potions, id in self._potions_drawn)
            if potion_plan['drawn']:
                self._potions_drawn.add(id)
            elif potion_plan['qty'] > 0:
                extras.append({'name': PRAYER_POTION, 'qty': potion_plan['qty']})
        food_short = (food_ready and food_item and module.food and id not in self._food_drawn
                      and snap.inv.get(food_item.lower(), 0) < module.food)
        potions_short = potions and id not in self._potions_drawn and snap.inv.get(PRAYER_POTION.lower(), 0) < potions
        needs_bank_snapshot = len(plan.blocked) > 0 or not coin_plan['drawn'] or food_short or potions_short
        if not self._bank_known and needs_bank_snapshot:
            return quest_step('scan_bank', bank=bank_for(module))
        if len(plan.blocked) > 0 and len(plan.withdraw) == 0:
            name = module.record.name
            self.host.log(f"{name} short on items: {', '.join(plan.blocked)} — parking")
            self._parked_reasons[id] = [f'missing: {b}' for b in plan.blocked]
            self._park_or_give_up(id, name)
            self._reset_watchdog()
            self.running_id = None
            blk = self._apply_blocked(queue_rows(self._order, picked, elig, self._parked, None))
            self.host.note_state(blk, None, f"parked: {', '.join(plan.blocked)}", self._no_progress_count, len(self._parked))
            return None
        if len(plan.withdraw) > 0 or len(extras) > 0:
            return quest_step('withdraw', items=plan.withdraw + extras, bank=bank_for(module))
        if plan.satisfied:
            # Why: with food held back the quest isn't provisioned yet, and closing the block here would retire it for
            # the run.
            if food_ready:
                self._provisioned.add(id)
            return module.decide(snap)
        want = plan.gather[0]
        gather_fn = module.gather.get(want['name'].lower()) if module.gather is not None else None
        if gather_fn is None:
            self.host.log(f"ERROR: {module.record.name} needs '{want['name']}' but has no gather fn (def bug)")
            self._block(id, [f"def bug: no gather for {want['name']}"])
            self.running_id = None
            bug = self._apply_blocked(queue_rows(self._order, picked, elig, self._parked, None))
            self.host.note_state(bug, None, f"def bug: no gather for {want['name']}", self._no_progress_count, len(self._parked))
            return None
        return gather_fn(snap, want['need'])

    def _recover_death_if_pending(self):
        """True when a death was consumed this pass. Use with yield from."""
        if not self.host.consume_death():
            return False
        if self.running_id is None:
            self.host.log('died before a quest step was active — restarting quest selection')
            self._forget_step()
            return True
        dead_id = self.running_id
        dead_module = def_by_id(dead_id)
        name = dead_module.record.name if dead_module is not None else dead_id
        self.host.log(f'died during {name} — re-provisioning and resuming')
        chat = game_messages.recent(10)
        if len(chat) > 0:
            self.host.log('  chat: ' + ' | '.join([m.text for m in chat]))
        if dead_module is not None and dead_module.observe is not None:
            stage, progress = yield from self._read_stage(dead_module)
            death_snap = self._build_snapshot(dead_module, stage, progress)
            for line in dead_module.observe(death_snap, quest_step('wait', reason='death')):
                self.host.log(f'  {line}')
        for latch in [self._provisioned, self._deposited, self._food_drawn, self._potions_drawn, self._coins_drawn]:
            latch.discard(dead_id)
        self._forget_step()
        return True

    def _forget_step(self):
        self._reset_watchdog()
        self._step_sub_log = set()
        self._last_step_logged = ''
        self._wait_key = ''
        self._wait_count = 0

    def _freshen_pack(self, module, id, snap, rows):
        """Banks the pack to nothing before a quest opens; True when the pass should yield after the trip. Use with
        yield from."""
        carried = inventory.used()
        if snap.journal == 'not_started' and carried == 0:
            self._freshened.add(id)
        if not should_freshen_pack(snap.journal, carried, id in self._freshened):
            return False
        tries = self._freshen_tries.get(id, 0) + 1
        self._freshen_tries[id] = tries
        self.host.note_state(rows, id, 'banking the pack to nothing', self._no_progress_count, len(self._parked))
        self.host.log(f'{module.record.name} not started, banking {carried} carried slot(s) so it provisions from empty ({tries}/{FRESH_GIVE_UP})')
        emptied = yield from execute_step(quest_step('deposit', keep=[], bank=bank_for(module), leave_open=True), module.hops or [], self._log)
        if emptied or tries >= FRESH_GIVE_UP:
            self._freshened.add(id)
        if not emptied and tries >= FRESH_GIVE_UP:
            self.host.log(f'{module.record.name}: no bank reachable after {FRESH_GIVE_UP} tries — starting on the pack as it stands')
        yield from execution.delay_until(lambda: bank.loaded(), 3000)
        self._refresh_bank_counts(True)
        yield from modals.close_if_open()
        return True

    # Why: exit comes first for the quests whose last step leaves them somewhere the walker has no route out of.
    # Why: the bank walk itself is a scan_bank, so it picks the nearest reachable bank like every other bank leg.
    # Why: bounded, since a bot parked on the wrong side of a broken route still finishes its queue.
    def _retreat_to_bank(self, module, id, rows):
        """Drives a finished quest's character back to a bank before the queue moves on. Use with yield from."""
        tries = self._retreat_tries.get(id, 0) + 1
        self._retreat_tries[id] = tries
        if tries > RETREAT_GIVE_UP:
            self.host.log(f'{module.record.name}: no way back to a bank after {RETREAT_GIVE_UP} tries — leaving the character where it finished')
            self._retreated.add(id)
            return True
        self.host.note_state(rows, id, 'walking back to a bank', self._no_progress_count, len(self._parked))
        self.host.log(f'{module.record.name} finished — walking back to a bank ({tries}/{RETREAT_GIVE_UP})')
        if module.exit is not None:
            out = yield from run_maybe(module.exit(self._log))
            if not out:
                return False
        banked = yield from execute_step(quest_step('scan_bank', bank=bank_for(module)), module.hops or [], self._log)
        if not banked:
            return False
        self._retreated.add(id)
        return True

    def _reset_watchdog(self):
        self._watchdog.reset()
        self._failed_watchdog.reset()
        self._pending_failed_signature = None
        self._no_progress_count = 0
        self._tracker.reset()
        self._fail_streak = 0
        self._combat_idle_since = None

    def _combat_advancing(self, snap):
        if not game.in_combat():
            self._combat_idle_since = None
            return False
        xp = snap.combat_xp or 0
        if self._combat_idle_since is None or xp != self._combat_xp:
            self._combat_idle_since = _now_ms()
        self._combat_xp = xp
        return _now_ms() - self._combat_idle_since < COMBAT_STALL_MS

    def _apply_user_skip(self, id, elig):
        """The console's skip: stops the running quest for this session and moves on. A park is temporary (retried
        later); a skip blocks the quest for the session."""
        name = elig[id].name if id in elig else id
        self.host.log(f'skip requested — blocking {name} for this session')
        self._block(id, ['skipped by user this session'])
        self._parked.discard(id)
        for table in [self._parked_reasons, self._park_counts, self._freshen_tries, self._retreat_tries]:
            if id in table:
                del table[id]
        for latch in [self._provisioned, self._deposited, self._freshened, self._food_drawn, self._potions_drawn,
                      self._coins_drawn, self._retreated]:
            latch.discard(id)
        self._wait_key = ''
        self._wait_count = 0
        self._step_sub_log = set()
        self._last_step_logged = ''
        self.running_id = None

    def _block(self, id, reasons):
        self._blocked[id] = reasons
        self._reset_watchdog()

    def _park_or_give_up(self, id, name):
        count = self._park_counts.get(id, 0) + 1
        self._park_counts[id] = count
        if count >= PARK_GIVE_UP:
            self.host.log(f'{name} parked {PARK_GIVE_UP}x with no progress — giving up')
            self._block(id, [f'parked {PARK_GIVE_UP}x with no progress — giving up'])
            return
        self.host.log(f'parking {name} (park {count}/{PARK_GIVE_UP})')
        self._parked.add(id)

    def _apply_blocked(self, rows):
        out = []
        for r in rows:
            blocked = self._blocked.get(r.id)
            if blocked is not None:
                out.append(QueueRow(r.id, r.name, 'BLOCKED', blocked))
                continue
            reasons = self._parked_reasons.get(r.id)
            if reasons is not None and r.status == 'PARKED':
                out.append(QueueRow(r.id, r.name, r.status, reasons))
                continue
            out.append(r)
        return out

    def _build_snapshot(self, module, stage=None, progress=None):
        held = inventory.items()
        worn = equipment.items()
        combat_xp = 0
        for skill in ['attack', 'strength', 'defence', 'ranged', 'magic', 'hitpoints']:
            combat_xp += skills.xp(skill)
        return QuestSnapshot(
            journal=quests.status(module.record.name),
            inv=_counts_by_name(held),
            inv_ids=_counts_by_id(held),
            worn=set([it.name.lower() for it in worn if it.name]),
            worn_ids=set([it.id for it in worn]),
            no_progress=self._no_progress_count,
            bank_coins=self._last_bank_counts.get('coins', 0),
            stage=stage,
            progress=progress,
            bank={k: v for k, v in self._last_bank_counts.items()},
            bank_ids={k: v for k, v in self._last_bank_id_counts.items()},
            bank_known=self._bank_known,
            tile=game.tile(),
            prayer=skills.effective('prayer'),
            attack=skills.level('attack'),
            ranged=skills.level('ranged'),
            magic=skills.effective('magic'),
            free_slots=inventory.free(),
            combat_xp=combat_xp,
        )

    def _read_player_state(self):
        skill_names = set()
        for r in self._records:
            for s in r.requirements.skills or []:
                skill_names.add(s.skill)
        skill_levels = {}
        for name in skill_names:
            skill_levels[name] = skills.level(name)
        # Why: completion is read from every known quest, so a prerequisite without a module yet (Biohazard for
        # Underground Pass, Heroes' Quest for Legends) can still be satisfied.
        completed = set()
        for r in QUESTS:
            if quests.status(r.name) == 'complete':
                completed.add(r.id)
        return PlayerState(quests.points(), skill_levels, completed)

    def _read_item_snapshot(self):
        wanted = set()
        for r in self._records:
            for it in r.items:
                wanted.add(it.name)
        worn = [it.name.lower() for it in equipment.items() if it.name]
        counts = {}
        for name in wanted:
            key = name.lower()
            counts[key] = inventory.count(name) + len([w for w in worn if w == key]) + self._last_bank_counts.get(key, 0)
        return BankInventorySnapshot(counts, self._bank_known)

    def _refresh_bank_counts(self, accept_settled_empty=False):
        if not bank.is_open() or (not bank.ready() and not accept_settled_empty):
            return
        items = bank.items()
        self._last_bank_counts = _counts_by_name(items)
        self._last_bank_id_counts = _counts_by_id(items)
        self._bank_known = True
