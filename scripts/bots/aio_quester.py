# Runs a queue of quests, in the order that puts prerequisites first: rs2b0t's AIOQuester (MIT, see thirdparty/rs2b0t).
# The quest engine (rs2004.quests.engine) picks the next quest the account can start, banks the pack, provisions it,
# and steps it to the end; a quest that stops making progress is parked with its reason and the queue goes on. The
# console's skip command gives up the running quest for the session.

import time
import _core
import json
from bots.aioquester.preparation_runtime import QuestPreparation
from bots.aioquester.quest_selection import plan_quest_selection
from bots.aioquester.partnerships import PartnerCoordinator, PARTNER_QUESTS, established_quest_gang
from bots.aioquester.supply_activities import exit_quest_arena
from rs2004.quests.engine.preparation_policy import quest_food_request
from rs2004.quests.defs.shieldofarrav.config import arrav_config, resolve_gang
from rs2004.quests.defs.heroquest.config import hero_config
from rs2004.quests.defs.shieldofarrav.areas import SOA_ID
from rs2004.quests.defs.heroquest.areas import HERO_ID
from rs2004.catalogs.record import Record

from rs2004.catalogs import FOOD_OPTIONS, LOADOUT_SETTING, ContinueDialog, selected_loadout, sustain
from rs2004.quests.defs import QUEST_DEFS, def_by_id
from rs2004.quests.engine.quest_engine import QuestEngine
from rs2004.quests.food import quest_food
from rs2004.quests.gear import quest_loadout
from rs2004.quests.prayer import prayer_upkeep, set_quest_prayer
from bots.aioquester.logic import blocked_entries, quest_clock_restarts, queue_summary, resolve_sustain_policy
from bots.aioquester.logic import select_sustain_consumable
from rs2004.quests.defs.legends.config import LEGENDS_REWARD_OPTIONS
from bots.aioquester.logic import ARRAV_GANG_OPTIONS, apply_arrav_settings, apply_hero_settings, apply_legends_settings

QUEST_OPTION_LABELS = {}
for _d in QUEST_DEFS:
    QUEST_OPTION_LABELS[_d.record.id] = _d.record.name

# Why: the picker is sorted by name to be searchable by eye; the engine runs QUEST_DEFS order, so the order quests are
# ticked in can't reorder the run.
QUEST_OPTION_IDS = sorted([d.record.id for d in QUEST_DEFS], key=lambda id: QUEST_OPTION_LABELS[id])

FALLBACK_FOOD = 'Lobster'

AIO_SETTINGS = {
    'gather_wilderness_planks': SettingDef('boolean', True, 'Gather Wilderness planks', help='Dragon Slayer gathers missing planks in the Wilderness; disable to require banked planks'),
    'arrav_gang': SettingDef('string', 'random', 'Shield of Arrav gang', options=ARRAV_GANG_OPTIONS),
    'arrav_partner': SettingDef('string', '', 'Shield of Arrav partner', help='character name of the partner in the other gang'),
    'arrav_certs': SettingDef('number', 2, 'Arrav certificates', min=1, help='certificates to mint before splitting with the partner'),
    'hero_partner': SettingDef('string', '', "Hero's Quest partner", help='character name of the bot running the other gang; the master thief armband cannot be earned alone, and the gang itself comes from the Shield of Arrav setting'),
    'legends_reward': SettingDef('string', 'Prayer', 'Legends Quest reward', options=LEGENDS_REWARD_OPTIONS,
                                 help="which skill Radimus' four training sessions go into; Prayer by default, as the quest's own three demon fights are survived on Protect from Melee"),
    'quests': SettingDef('string[]', [], 'Quest queue (empty = all)', options=QUEST_OPTION_IDS, option_labels=QUEST_OPTION_LABELS,
                         help='which implemented quests to complete; leave empty to run every implemented quest. Tick order does not matter, the queue runs the built-in order that puts prerequisites first'),
    'loadout': LOADOUT_SETTING,
    'food': SettingDef('string', FALLBACK_FOOD, 'Food', options=FOOD_OPTIONS,
                       help='what the engine withdraws for any quest declaring a food count, and what the bot eats; this wins over any food the chosen loadout carries'),
    'verbose': SettingDef('boolean', True, 'Verbose step log',
                          help='log every engine tick with the step, attempt count, elapsed time and inventory delta, and stop de-duplicating sub-steps; off still heartbeats a repeating step'),
}


def now_ms():
    return time.time() * 1000


def minutes(ms):
    return f'{round(ms / 60000)}m'


class EatFood(Task):
    def __init__(self, bot):
        Task.__init__(self, label='eat food')
        self.bot = bot

    def validate(self):
        return self.bot.should_eat()

    def execute(self):
        yield from self.bot.eat_once()


class AIOQuester(TaskBot):
    partnership_paused = False
    preparation = None
    preparation_unsubscribe = None
    running_id = None
    loop_delay = 600

    def on_start(self):
        from rs2004.quests.defs.dragonslayer.supplies import DragonSupplies
        self.previous_wilderness_planks = DragonSupplies.wilderness_planks
        DragonSupplies.wilderness_planks = self.settings.bool('gather_wilderness_planks', True)
        self.status = 'starting'
        self.rows = []
        self.running_id = None
        self.step_desc = ''
        self.no_progress = 0
        self.parked_count = 0
        self.skip_requested = False
        self.restart_requested = False
        self.preparation = None
        self.partner_coordinator = None
        self.partnership_paused = False
        self.last_partner_update = -1000
        self.preparation_unsubscribe = None
        self.established_gang = None
        self.died = False
        self.deaths = 0
        self.qp_at_start = None
        self.completed = 0
        yield from execution.delay_until(lambda: game.ingame() and game.tile() is not None, 0)
        self.started_at = now_ms()
        self.step_since = self.started_at
        # Why: the queue runs one quest after another in a single session, so a runtime clock answers "how long has
        # the bot been up" and nothing answers "how long has this quest taken", which says whether a quest is slow or
        # stuck.
        self.quest_since = self.started_at

        every = [d.record.id for d in QUEST_DEFS]
        choices = self.settings.list('quests', [])
        excluded = set([value.strip()[1:].lower() for value in choices if value.strip().startswith('-')])
        self.picked = plan_quest_selection(set(selected_options(choices, every)), excluded, [d.record for d in QUEST_DEFS], set([d.record.id for d in QUEST_DEFS if quests.status(d.record.name) == 'complete']), quests.points())

        self.on('chat_message', self.heard)
        self.command('restart', self.request_restart, help='retreat and rebuild the current quest loadout')
        self.on('bot_message', self.receive_partner_message)
        self.on('tick', self.refresh_partners)
        self.command('skip', self.request_skip, help='give up the running quest for this session and go on with the queue')

        quest_loadout.current = selected_loadout(self.settings)
        apply_arrav_settings(Record({'gang': self.settings.str('arrav_gang', 'random'),
                                    'partner': self.settings.str('arrav_partner', ''),
                                    'certs': self.settings.num('arrav_certs', 2)}))
        apply_hero_settings(Record({'partner': self.settings.str('hero_partner', '')}))
        apply_legends_settings(Record({'reward': self.settings.str('legends_reward', 'Prayer')}))
        quest_food.name = self.food_item()
        # Why: the server runs one op per tick and drops the rest, so a pass spends its tick on food or on prayer, never
        # both, and food wins, as the fight it's losing is measured in hitpoints.
        sustain.set(self.upkeep)
        # A death must release the active quest operation before the engine can recover it.
        event_signal.set_interrupt(lambda: self.skip_requested or self.restart_requested or self.died)

        names = [d.record.name for d in QUEST_DEFS if d.record.id in self.picked]
        self.log(f"AIOQuester, queue: {', '.join(names) or '(none)'}")
        self.engine = QuestEngine(self)
        self.partner_coordinator = PartnerCoordinator(str(_core.step_time()) + ':' + str(time.time()) + ':' + (game.my_name() or ''), {'blackarmgang': arrav_config.partner, 'hero': hero_config.partner}, _core.step_time())
        self.refresh_partners()
        self.add(ContinueDialog(), EatFood(self), self.engine)

    def on_stop(self, reason):
        self.partnership_paused = True
        self.last_partner_update = -1000
        self.refresh_partners()
        from rs2004.quests.defs.dragonslayer.supplies import DragonSupplies
        DragonSupplies.wilderness_planks = getattr(self, 'previous_wilderness_planks', True)
        self.stop_preparation()
        self.partner_coordinator = None
        arrav_config.partner = self.settings.str('arrav_partner', '')
        hero_config.partner = self.settings.str('hero_partner', '')
        arrav_config.partner_stage = None
        arrav_config.partner_has_key = None
        hero_config.partner_stage = None
        hero_config.partner_has_key = None
        event_signal.set_interrupt(None)
        sustain.set(None)
        set_quest_prayer(None, None)

    def heard(self, e):
        text = (e.text or '').lower()
        if 'oh dear' in text and 'you are dead' in text:
            self.died = True
            self.deaths += 1
            if self.preparation is not None:
                self.preparation.interrupt('player died')

    def upkeep(self):
        if self.should_eat():
            yield from self.eat_once()
            return
        yield from prayer_upkeep()

    # Why: the setting is the answer for quests: a loadout built for a training script carries whatever that script
    # eats, and letting it override sent the queue out on food the player never chose.
    def food_item(self):
        configured = self.settings.str('food', FALLBACK_FOOD)
        module = def_by_id(self.running_id) if self.running_id else None
        request = quest_food_request(module, configured) if module else None
        return request.item if request else configured

    def verbose(self):
        return self.settings.bool('verbose', True)

    def food_held(self):
        food = self.food_item()
        return inventory.count(food) if food else 0

    def sustain_policy(self):
        quest = def_by_id(self.running_id) if self.running_id is not None else None
        return resolve_sustain_policy(self.food_item(), quest.sustain if quest is not None else None)

    def select_food(self):
        return select_sustain_consumable(inventory.items(), self.sustain_policy().foods, skills.effective('hitpoints'), skills.level('hitpoints'))

    def should_eat(self):
        return self.preparation is None and self.select_food() is not None

    def eat_once(self):
        # Re-evaluated at execution, so a packet received after validation can't leave it acting on a stale slot or
        # hitpoints decision.
        selected = self.select_food()
        if selected is None:
            return
        self.status = f'consuming {selected.item.name} ({round(skills.hp_fraction() * 100)}% hp)'
        before = skills.effective('hitpoints')
        name = selected.item.name
        before_slots = len([item for item in inventory.items() if item.name == name])
        if not selected.item.interact(selected.action):
            return
        # Incoming damage can hide the heal in the same update. The consumed food still proves the action landed.
        yield from execution.delay_until(lambda: skills.effective('hitpoints') > before or
            len([item for item in inventory.items() if item.name == name]) < before_slots, 3000)
        yield from execution.delay_ticks(1)

    def grind_targets(self):
        if self.preparation is not None and self.preparation.child is not None:
            return self.preparation.child.grind_targets()
        if self.running_id is None:
            return []
        quest = def_by_id(self.running_id)
        return (quest.grind or []) if quest is not None else []

    # The quest engine's host

    def picked_ids(self):
        return self.picked

    def note_state(self, rows, running_id, step_desc, no_progress, parked):
        if step_desc != self.step_desc:
            self.step_since = now_ms()
        if quest_clock_restarts(self.running_id, running_id):
            self.quest_since = now_ms()
        if running_id != self.running_id:
            quest = def_by_id(running_id) if running_id is not None else None
            name = quest.record.name if quest is not None else 'quest'
            set_quest_prayer(quest.pray if quest is not None else None, lambda m: self.log(f'{name}: {m}'))
        # Why: the engine reports no completion event, so completions are counted as DONE rows appearing.
        done = len([r for r in rows if r.status == 'DONE'])
        was_done = len([r for r in self.rows if r.status == 'DONE'])
        if len(self.rows) > 0 and done > was_done:
            self.completed += done - was_done
        self.rows = rows
        self.running_id = running_id
        quest_food.name = self.food_item()
        self.refresh_partners()
        self.step_desc = step_desc
        self.no_progress = no_progress
        self.parked_count = parked
        running = [r for r in rows if r.id == running_id]
        self.status = f'running {running[0].name}' if len(running) > 0 else step_desc

    def request_skip(self, cmd=None):
        if self.skip_requested:
            return
        self.skip_requested = True
        if self.preparation is not None:
            self.preparation.interrupt('skip requested')
        running = [r.name for r in self.rows if r.id == self.running_id]
        name = running[0] if len(running) > 0 else (self.running_id or 'current quest')
        self.log(f'Skip quest, abandoning {name} after the current step yields')

    def skip_pending(self):
        """True while a skip is asked for and the engine hasn't applied it yet."""
        return self.skip_requested

    def consume_skip(self):
        s = self.skip_requested
        self.skip_requested = False
        return s

    def consume_death(self):
        d = self.died
        self.died = False
        return d

    def restore_quest_hooks(self):
        sustain.set(self.upkeep)
        event_signal.set_interrupt(lambda: self.skip_requested or self.restart_requested or self.died)

    def automatic_recovery(self):
        return True

    def consume_restart(self):
        requested = self.restart_requested
        self.restart_requested = False
        return requested

    def request_restart(self, command=None):
        self.restart_requested = True
        if self.preparation is not None:
            self.preparation.interrupt('restart requested')
        self.log('Restart requested; retreating and rebuilding the current quest loadout')

    def prepare(self, request):
        if self.preparation is None:
            self.preparation = QuestPreparation(self.log, restore_hooks=self.restore_quest_hooks)
            from rs2004.events import events
            self.preparation_unsubscribe = events.on('tick', self.preparation.environment.observe)
        result = yield from self.preparation.tick(request)
        return result

    def preparation_status(self):
        return self.preparation.status if self.preparation is not None else 'preparing quest requirements'

    def exit_preparation(self):
        yield from exit_quest_arena(self.log)

    def stop_preparation(self):
        if self.preparation_unsubscribe is not None:
            self.preparation_unsubscribe()
            self.preparation_unsubscribe = None
        if self.preparation is not None:
            self.preparation.stop()
            self.preparation = None
        self.restore_quest_hooks()

    def receive_partner_message(self, sender, message):
        if self.partner_coordinator is not None and isinstance(message, dict) and message.get('type') == 'quest-partner-v1':
            self.partner_coordinator.receive(message.get('member'), _core.step_time())

    def refresh_partners(self, tick=None):
        coordinator = getattr(self, 'partner_coordinator', None)
        now = _core.step_time()
        if coordinator is None or now - self.last_partner_update < 1000:
            return
        self.last_partner_update = now
        progress = self.engine.coordination_progress()
        for id in ['hero', 'blackarmgang']:
            observed = established_quest_gang(id, progress[id].stage if id in progress else None)
            if observed:
                self.established_gang = observed
                arrav_config.gang = observed
                break
        gang = self.established_gang or resolve_gang(arrav_config.gang, game.my_name())
        entries = {}
        for id in PARTNER_QUESTS:
            entries[id] = {'stage': progress[id].stage if id in progress else None, 'has_key': inventory.count_by_id(SOA_ID.STORE_KEY if id == 'blackarmgang' else HERO_ID.MISC_KEY) > 0, 'eligible': id in progress and id in self.picked and self.running_id == id and (self.preparation is None or bool(coordinator.partner(id)))}
        snapshot = {'name': game.my_name() or '', 'world': str(game.world()), 'gang': gang, 'quests': entries, 'active_quest': self.running_id, 'available': game.ingame() and skills.effective('hitpoints') > 0 and not self.died and not self.skip_requested and not self.restart_requested and not self.partnership_paused, 'trade_active': trade.active()}
        message = coordinator.update(snapshot, now)
        try:
            send_bot_message('*', {'type': 'quest-partner-v1', 'member': message})
        except ValueError:
            # Single-account hosts and embedded test hosts can omit the messenger.
            pass
        for id in PARTNER_QUESTS:
            config = arrav_config if id == 'blackarmgang' else hero_config
            previous = config.partner
            config.partner = coordinator.partner(id)
            peer = coordinator.peer(id, now)
            details = peer['quests'].get(id, {}) if peer else {}
            config.partner_stage = details.get('stage')
            config.partner_has_key = details.get('has_key')
            if previous != config.partner and config.partner:
                if id == 'blackarmgang':
                    from rs2004.quests.defs.shieldofarrav.partner import arrav_handoff_state
                    arrav_handoff_state.halves_given = 0
                    arrav_handoff_state.gave_cert = False
                else:
                    from rs2004.quests.defs.heroquest.partner import reset_hero_handoff_state
                    reset_hero_handoff_state()
                self.log(id + ': partner ' + config.partner)

    def waiting_for_partner(self, id):
        return self.partner_coordinator is not None and self.partner_coordinator.has_live_partner(id, _core.step_time())

    def partner_progress_key(self, id):
        peer = self.partner_coordinator.peer(id, _core.step_time()) if self.partner_coordinator is not None else None
        return json.dumps([peer['session'], peer['quests'].get(id)]) if peer else ''

    def on_pause(self):
        self.partnership_paused = True
        self.last_partner_update = -1000
        self.refresh_partners()
        if self.preparation is not None:
            self.preparation.pause()

    def on_resume(self):
        self.partnership_paused = False
        self.last_partner_update = -1000
        self.refresh_partners()
        if self.preparation is not None:
            self.preparation.resume()

    def finish(self, reason):
        self.request_finish(reason)

    def on_progress_report(self):
        qp = quests.points()
        if self.qp_at_start is None and qp > 0:
            self.qp_at_start = qp
        summary = queue_summary(self.rows)
        now = now_ms()
        report = {
            'Status': self.status,
            'Quest': self.status[8:] if self.status.startswith('running ') else '—',
            'Step': self.step_desc,
            'On step': minutes(now - self.step_since),
            'On quest': minutes(now - self.quest_since),
            'Queue': f"done {summary['done']}/{summary['total']} · stuck {summary['stuck']}",
            'QP': f'{qp} (+{qp - self.qp_at_start if self.qp_at_start is not None else 0})',
            'Completed': self.completed,
            'Deaths': self.deaths,
            'No-progress': self.no_progress,
            'Parked': self.parked_count,
            'Food': f'{self.food_item() or "none"} x{self.food_held()}',
        }
        stuck = blocked_entries(self.rows)
        if len(stuck) > 0:
            report['Blocked'] = '; '.join([f"{e['name']}: {', '.join(e['reasons'])}" for e in stuck])
        # Why: a long walk logs little, so where it stands is what tells a walk from a stall.
        report['At'] = str(game.tile())
        return report


BOT = define_bot(
    name='AIOQuester',
    create=AIOQuester,
    description='Completes a queue of quests: banks the pack, provisions each quest from the bank, gathers what it needs, and steps it to the end. Parks a quest that stops progressing and moves on.',
    category='Quests',
    tags=['quests', 'banking'],
    settings_schema=AIO_SETTINGS,
)
