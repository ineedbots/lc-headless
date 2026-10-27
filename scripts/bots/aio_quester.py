# Runs a queue of quests, in the order that puts prerequisites first: rs2b0t's AIOQuester (MIT, see thirdparty/rs2b0t).
# The quest engine (rs2004.quests.engine) picks the next quest the account can start, banks the pack, provisions it,
# and steps it to the end; a quest that stops making progress is parked with its reason and the queue goes on. The
# console's skip command gives up the running quest for the session.

import time
from rs2004.catalogs.record import Record

from rs2004.catalogs import FOOD_OPTIONS, LOADOUT_SETTING, ContinueDialog, selected_loadout, sustain
from rs2004.quests.defs import QUEST_DEFS, def_by_id
from rs2004.quests.engine.quest_engine import QuestEngine
from rs2004.quests.food import quest_food
from rs2004.quests.gear import quest_loadout
from rs2004.quests.prayer import prayer_upkeep, set_quest_prayer
from bots.aioquester.logic import blocked_entries, quest_clock_restarts, queue_summary, resolve_sustain_policy
from bots.aioquester.logic import select_sustain_consumable
from bots.aioquester.logic import ARRAV_GANG_OPTIONS, apply_arrav_settings

QUEST_OPTION_LABELS = {}
for _d in QUEST_DEFS:
    QUEST_OPTION_LABELS[_d.record.id] = _d.record.name

# Why: the picker is sorted by name to be searchable by eye; the engine runs QUEST_DEFS order, so the order quests are
# ticked in can't reorder the run.
QUEST_OPTION_IDS = sorted([d.record.id for d in QUEST_DEFS], key=lambda id: QUEST_OPTION_LABELS[id])

FALLBACK_FOOD = 'Lobster'

AIO_SETTINGS = {
    'arrav_gang': SettingDef('string', 'random', 'Shield of Arrav gang', options=ARRAV_GANG_OPTIONS),
    'arrav_partner': SettingDef('string', '', 'Shield of Arrav partner', help='character name of the partner in the other gang'),
    'arrav_certs': SettingDef('number', 2, 'Arrav certificates', min=1, help='certificates to mint before splitting with the partner'),
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
    loop_delay = 600

    def on_start(self):
        self.status = 'starting'
        self.rows = []
        self.running_id = None
        self.step_desc = ''
        self.no_progress = 0
        self.parked_count = 0
        self.skip_requested = False
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
        chosen = [id for id in self.settings.list('quests', []) if id in every]
        self.picked = set(chosen if len(chosen) > 0 else every)

        self.on('chat_message', self.heard)
        self.command('skip', self.request_skip, help='give up the running quest for this session and go on with the queue')

        quest_loadout.current = selected_loadout(self.settings)
        apply_arrav_settings(Record({'gang': self.settings.str('arrav_gang', 'random'),
                                    'partner': self.settings.str('arrav_partner', ''),
                                    'certs': self.settings.num('arrav_certs', 2)}))
        quest_food.name = self.food_item()
        # Why: the server runs one op per tick and drops the rest, so a pass spends its tick on food or on prayer, never
        # both, and food wins, as the fight it's losing is measured in hitpoints.
        sustain.set(self.upkeep)
        # A death must release the active quest operation before the engine can recover it.
        event_signal.set_interrupt(lambda: self.skip_requested or self.died)

        names = [d.record.name for d in QUEST_DEFS if d.record.id in self.picked]
        self.log(f"AIOQuester, queue: {', '.join(names) or '(none)'}")
        self.engine = QuestEngine(self)
        self.add(ContinueDialog(), EatFood(self), self.engine)

    def on_stop(self, reason):
        event_signal.set_interrupt(None)
        sustain.set(None)
        set_quest_prayer(None, None)

    def heard(self, e):
        text = (e.text or '').lower()
        if 'oh dear' in text and 'you are dead' in text:
            self.died = True
            self.deaths += 1

    def upkeep(self):
        if self.should_eat():
            yield from self.eat_once()
            return
        yield from prayer_upkeep()

    # Why: the setting is the answer for quests: a loadout built for a training script carries whatever that script
    # eats, and letting it override sent the queue out on food the player never chose.
    def food_item(self):
        return self.settings.str('food', FALLBACK_FOOD)

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
        return self.select_food() is not None

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
        self.step_desc = step_desc
        self.no_progress = no_progress
        self.parked_count = parked
        running = [r for r in rows if r.id == running_id]
        self.status = f'running {running[0].name}' if len(running) > 0 else step_desc

    def request_skip(self, cmd=None):
        if self.skip_requested:
            return
        self.skip_requested = True
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
