"""Run preparation activities with bounded retries, from rs2b0t (MIT, see thirdparty/rs2b0t)."""

import _core
import json
from rs2004.activity import ScriptActivity
from rs2004.catalogs import sustain
from bots.account_leveler.record import Record
from bots.account_leveler.planner import enabled_skills, empty_memory
from bots.account_leveler.stock import LevelerStock
from bots.account_leveler.supplies import game_supply_port, provision
from bots.account_leveler.types import requirement_key, stock_of
from bots.account_leveler.manifests import manifest_for
from bots.account_leveler.zanaris import game_zanaris_port, in_zanaris, leave_zanaris
from bots.account_leveler.travel import leveler_travel_zones
from bots.aioquester.preparation import plan_preparation
from bots.aioquester.supply_activities import exit_quest_arena, in_quest_arena
from bots.aioquester.supply_activities import cake_supply_activity, ground_supply_activity, ticket_supply_activity, toadflax_supply_activity


class PreparationError(Exception):
    pass


class GameEnvironment:
    def __init__(self, log, wilderness=False):
        self.log = log
        self.wilderness = wilderness
        self.stock = LevelerStock()
        port = game_supply_port(log)
        self.supplies = Record(port._fields)
        self.supplies.walk = self.walk

    def walk(self, tile):
        if not in_zanaris(tile):
            left = yield from leave_zanaris(game_zanaris_port(self.log))
            if not left:
                return False
        reached = yield from traversal.walk_resilient(Tile.from_tile(tile), radius=3, attempts=4, timeout_ms=120000, avoid_zones=leveler_travel_zones(tile, self.wilderness), log=self.log)
        return reached

    def observe(self, event=None):
        self.stock.observe(bank.items(), bank.ready())

    def snapshot(self):
        self.observe()
        return Record({'levels': {skill: skills.level(skill) for skill in enabled_skills}, 'stock': self.stock.total(inventory.items() + equipment.items()), 'bank_ready': self.stock.ready, 'quests': {q.name: q.status == 'complete' for q in quests.all()}, 'target': 99, 'wilderness': self.wilderness, 'now': _core.step_time(), 'quest_points': quests.points()})

    def bank(self):
        yield from exit_quest_arena(self.log)
        opened = yield from self.supplies.bank()
        if not opened:
            raise PreparationError('Cannot open bank for quest preparation')
        self.observe()

    def prepare(self, plan):
        yield from provision(plan, self.supplies, lambda event: self.log(event.message))
        if plan.travel:
            arrived = yield from self.walk(plan.travel)
            if not arrived:
                raise PreparationError(f'Cannot reach {plan.label}')

    def invalidate(self):
        self.stock.invalidate()

    def progress(self, plan):
        targets = plan.prerequisite_levels or {plan.objective: 0}
        return json.dumps([{skill: skills.xp(skill) for skill in targets.keys()}, stock_of(self.snapshot(), plan.output.item) if plan.output else None])

    def can_stop(self):
        return not game.in_combat() and not in_quest_arena()

    def eat(self, food=None):
        if food and skills.hp_fraction() <= 0.65 and not bank.is_open():
            items = [item for item in inventory.items() if not item.noted and item.name.lower() == food.lower() and 'Eat' in item.actions()]
            if items:
                items[0].interact('Eat')
                yield from execution.delay_ticks(1)

    def now(self):
        return _core.step_time()

    def dispose(self):
        pass

    def bank_cakes(self):
        yield from self.bank()
        yield from self.supplies.deposit()
        self.observe()
        closed = yield from self.supplies.close_bank()
        if not closed:
            raise PreparationError('Cannot close bank after storing cakes')

    def meta(self, name):
        if name == 'QuestGroundSupply':
            return ground_supply_activity()
        if name == 'QuestToadflax':
            return toadflax_supply_activity()
        if name == 'QuestArenaTickets':
            return ticket_supply_activity(lambda: stock_of(self.snapshot(), 'Agility arena ticket'))
        if name == 'QuestCakeSupply':
            return cake_supply_activity(lambda: stock_of(self.snapshot(), 'Cake'), self.bank_cakes)
        return manifest_for(name)


class QuestPreparation:
    def __init__(self, log, restore_hooks=None, environment=None, wilderness=False):
        self.log = log
        self.restore_hooks = restore_hooks
        self.environment = environment if environment is not None else GameEnvironment(log, wilderness)
        self.activity = ScriptActivity(log)
        self.memory = empty_memory()
        self.plan = None
        self.request = ''
        self.signature = ''
        self.progress_at = 0
        self.failures = 0
        self.interruption = None
        self.stopped = False
        self.generation = 0
        self.status = ''
        self.queue = []

    @property
    def child(self):
        return self.activity.child

    def set_status(self, message):
        if message != self.status:
            self.log(message)
        self.status = message

    def reset(self):
        self.generation += 1
        self.activity.stop()
        self.plan = None
        self.environment.invalidate()
        sustain.set(None)
        if self.restore_hooks is not None:
            self.restore_hooks()

    def fail(self, reason):
        self.reset()
        self.failures += 1
        self.set_status(f'Quest preparation attempt {self.failures}/3: {reason}')
        if self.failures >= 3:
            raise PreparationError(self.status)
        return 'working'

    def tick(self, request):
        if self.stopped:
            raise PreparationError('Quest preparation stopped')
        key = json.dumps({'skills': [(r.skill, r.level) for r in request.skills or []], 'items': [(r.item, r.id, r.count) for r in request.items or []], 'food': (request.food.item, request.food.count) if request.food else None})
        if key != self.request:
            self.reset()
            self.request = key
            self.failures = 0
        generation = self.generation
        try:
            if self.interruption:
                reason = self.interruption
                self.interruption = None
                return self.fail(reason)
            if self.plan is not None:
                plan = self.plan
                s = self.environment.snapshot()
                progress = self.environment.progress(plan)
                if progress != self.signature:
                    self.signature = progress
                    self.progress_at = self.environment.now()
                    self.failures = 0
                reached = stock_of(s, plan.output.item) >= plan.output.count if plan.output else bool(plan.prerequisite_levels) and all([s.levels.get(skill, 0) >= level for skill, level in plan.prerequisite_levels.items()])
                if reached and self.environment.can_stop():
                    self.memory.recent = (self.memory.recent + [plan.id])[-6:]
                    self.reset()
                    self.set_status(f'Completed {plan.label}; checking remaining quest requirements')
                    return 'working'
                if self.activity.outcome is not None:
                    return self.fail(self.activity.outcome.reason)
                if self.environment.now() - self.progress_at > 180000:
                    return self.fail(f'No progress for three minutes: {plan.label}')
                yield from self.environment.eat(plan.food)
                yield from self.activity.loop()
                if self.interruption:
                    reason = self.interruption
                    self.interruption = None
                    return self.fail(reason)
                if self.child is None and self.restore_hooks is not None:
                    self.restore_hooks()
                return 'working'
            self.set_status('Checking bank for quest preparation')
            yield from self.environment.bank()
            if generation != self.generation:
                return 'working'
            decision = plan_preparation(self.environment.snapshot(), request, self.memory)
            if decision.kind == 'blocked':
                raise PreparationError(decision.reason)
            if decision.kind == 'refresh':
                return self.fail('Bank contents did not load')
            if decision.kind == 'complete':
                self.queue = []
                self.set_status('Quest requirements ready')
                if self.restore_hooks is not None:
                    self.restore_hooks()
                return 'ready'
            self.queue = [p.label for p in decision.queue]
            self.plan = decision.plan
            self.set_status('Preparing ' + self.queue[0])
            sustain.set(self.upkeep)
            yield from self.environment.prepare(self.plan)
            if generation != self.generation:
                return 'working'
            if not self.plan.script:
                yield from self.environment.bank()
                if generation != self.generation:
                    return 'working'
                supplied = self.environment.snapshot()
                missing = [need for need in self.plan.needs if stock_of(supplied, requirement_key(need)) < need.count]
                if missing:
                    return self.fail('Supplies still missing: ' + ', '.join([need.item for need in missing]))
                self.reset()
                return 'working'
            if self.plan.script == 'AIOQuester':
                raise PreparationError('Recursive quest preparation is unsupported')
            manifest = self.environment.meta(self.plan.script)
            self.signature = self.environment.progress(self.plan)
            self.progress_at = self.environment.now()
            settings = self.plan.settings._fields if isinstance(self.plan.settings, Record) else self.plan.settings
            yield from self.activity.start(manifest, settings)
            if self.child is None and self.restore_hooks is not None:
                self.restore_hooks()
            return 'working'
        except PreparationError:
            self.reset()
            raise
        except Exception as error:
            return self.fail(str(error))

    def upkeep(self):
        yield from self.environment.eat(self.plan.food if self.plan else None)

    def interrupt(self, reason):
        self.generation += 1
        self.interruption = reason
        self.activity.interrupt(reason)

    def stop(self):
        self.stopped = True
        self.reset()
        self.environment.dispose()

    def pause(self):
        hook = getattr(self.child, 'on_pause', None)
        if hook is not None:
            hook()

    def resume(self):
        self.progress_at = self.environment.now()
        hook = getattr(self.child, 'on_resume', None)
        if hook is not None:
            hook()
