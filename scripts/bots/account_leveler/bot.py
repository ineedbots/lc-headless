"""Ported from rs2b0t's src/bot/scripts/AccountLeveler/AccountLeveler.ts (MIT, see thirdparty/rs2b0t)."""

import _core
import json
import math
from rs2004.catalogs import sustain
from rs2004.execution import event_signal
from rs2004.settings import settings_store
from bots.account_leveler.manifests import manifest_for
from bots.potion_maker import herb_by_name
import random
from bots.account_leveler.record import Record

__all__ = ['SETTINGS', 'AccountLeveler']

from bots.account_leveler.market import SeersAxeBuyer
from bots.account_leveler.catalog import refresh_consumables
from bots.account_leveler.combat import COMBAT_CAMPS
from bots.account_leveler.combat_progression import combat_level
from bots.account_leveler.equipment import gathering_tool
from bots.account_leveler.planner import empty_memory, enabled_skills, plan_next, resolve_activity
from bots.account_leveler.session import LevelerSession, uses_activity_cooldown
from bots.account_leveler.stock import LevelerStock
from bots.account_leveler.supplies import game_supply_port, provision, SupplyUnavailableError, SupplyStockError
from bots.account_leveler.shopping import audit_supplies
from bots.account_leveler.actions import ActionQueue, activity_actions, describe_activity
from bots.account_leveler.priority import can_resume_objective, training_priority
from bots.account_leveler.types import requirement_key, stock_of
from bots.account_leveler.dragon_weapons import audit_dragon_weapons, DRAGON_SHOP_COOLDOWN
from bots.account_leveler.dragons import DRAGON_CAMPS, dragon_ready
from bots.account_leveler.zanaris import game_zanaris_port, in_zanaris, leave_zanaris
from bots.account_leveler.travel import leveler_travel_zones
from rs2004.quests.defs.dragonslayer.journal import read_dragon_progress
class ActivityTravelError(Exception):
    pass


SETTINGS = {
    'target_level': SettingDef('number', 60, min=2, max=60, label='Target level', help='Train every enabled skill to at least this level.'),
    'market_axes': SettingDef('boolean', True, label='Try Seers market axes', help='One optional Rune axe purchase from seers market when near Seers on World 1. Falls back to available tools.'),
    'market_axe_budget': SettingDef('number', 50000, min=0, max=1000000, label='Market axe price limit', help='Also capped at 10% of banked gold; keeps 200 coins for travel.'),
    'wilderness': SettingDef('boolean', True, label='Allow Wilderness training', help='Include suitable Wilderness combat camps and Edgeville monkey bars from Agility 15.'),
}


class AccountLeveler(LoopingBot):
    loop_delay = 100
    _display_plan = None
    _shopping_checked = False
    _market_checked = False
    _last_failure = None
    _shopping_budget = 0
    _detail = ''
    _last_saved_at = 0
    _status = 'starting'
    _phase = 'bank'
    _stop_observing = None
    _died = False
    _last_tile = None
    _death_tile = None
    _retry = None
    _reset_count = 0
    _waiting_until = 0
    _target = 60
    _wilderness = True
    _dragon_stage = None

    def __init__(self):
        self._session = LevelerSession(empty_memory())
        self._activity = ScriptActivity(lambda message: self._set_detail(message))
        _merged1 = {}
        for _k, _v in (game_supply_port(lambda message: self._set_detail(message))._fields if isinstance(game_supply_port(lambda message: self._set_detail(message)), Record) else game_supply_port(lambda message: self._set_detail(message))).items():
            _merged1[_k] = _v
        for _k, _v in {'walk': self._walk}.items():
            _merged1[_k] = _v
        self._supplies = Record(_merged1)
        self._actions = ActionQueue()
        self._pending_plans = []
        self._market_buyer = SeersAxeBuyer()
        self._unavailable_items = set()
        self._temporarily_unavailable = {}
        self._started_at = _core.step_time()
        self._last_logged_at = _core.step_time()
        self._stock = LevelerStock()

    def _walk(self, tile):
        if not in_zanaris(tile):
            returned = yield from leave_zanaris(game_zanaris_port(self._set_detail))
            if not returned:
                return False
        arrived = yield from traversal.walk_resilient(Tile.from_tile(tile), radius=3, attempts=4, timeout_ms=120000, avoid_zones=leveler_travel_zones(tile, self._wilderness), log=self._set_detail)
        return arrived

    def on_start(self):
        self.log('Waiting for the game scene before checking bank supplies')
        yield from execution.delay_until(lambda: game.scene_ready(), 0)
        self._target = max(2, min(60, self.settings.num('target_level', 60)))
        self._wilderness = self.settings.bool('wilderness', True)
        self._load()

        self.log(f"training {len(enabled_skills)} skills to {self._target}; Wilderness {('enabled' if self._wilderness else 'disabled')}")

    def on_tick(self, tick):
        self._stock.observe(bank.items(), bank.ready())
        self._session.sample_work(_core.step_time(), self._phase == 'train' and not bank.is_open() and (game.animating() or game.in_combat()))
        if _core.step_time() - self._last_logged_at >= 30000:
            tile = game.tile()
            self.log(f'Still {self._status}; {self._detail}; position {tile}')

    def on_death(self):
        self._died = True
        self._death_tile = self._last_tile
        self._activity.interrupt('player died')

    def log(self, message):
        self._last_logged_at = _core.step_time()
        super().log(message)

    def loop(self):
        if not game.scene_ready():
            return
        if _core.step_time() < self._waiting_until:
            return
        self._last_tile = game.tile()
        try:
            if self._died:
                self._died = False
                if self._phase == 'bank':
                    self._session.memory.deaths += 1
                    self._fail('Player died while preparing supplies')
                    return
                previous = self._session.plan
                decision = self._session.death(_core.step_time())
                if (previous.death_walk if previous is not None else None):
                    self._actions.note(f'Death walk: restocking for {previous.label}')
                else:
                    self._record_failure('Player died')
                self._retry = (previous if decision == 'reset' else None)
                if decision == 'rotate':
                    self._pending_plans = []
                self._activity.stop()
                self._phase = 'bank'
                self._stock.invalidate()
                self._set_status('recovering from death at the nearest bank')
                self._save()
            if self._phase == 'bank':
                yield from self._select_and_start()
                return
            plan = self._session.plan
            if not plan:
                self._phase = 'bank'
                return
            snapshot = self._snapshot()
            if plan.death_walk and combat_level(snapshot.levels) >= 15 and not game.in_combat():
                self._activity.stop()
                self._session.resupply(_core.step_time())
                self._retry = None
                self._pending_plans = []
                self._phase = 'bank'
                self._stock.invalidate()
                self._set_status('Combat 15 reached; banking to prepare food for stronger targets')
                self._save()
                return
            reached = self._reached(plan, snapshot)
            pending_potions = plan.script == 'PotionMaker' and inventory.count_by_id(((herb_by_name(str(plan.settings.get('herb'))).unf_id if herb_by_name(str(plan.settings.get('herb'))) is not None else None) if (herb_by_name(str(plan.settings.get('herb'))).unf_id if herb_by_name(str(plan.settings.get('herb'))) is not None else None) is not None else 91)) > 0
            exhausted = not pending_potions and any([(stock_of(snapshot, requirement_key(need)) < need.minimum if need.minimum is not None else not need.equip and need.count > 1 and stock_of(snapshot, requirement_key(need)) == 0) for need in plan.needs])
            depleted_on_finish = (self._activity.outcome.kind if self._activity.outcome is not None else None) == 'finished' and any([stock_of(snapshot, requirement_key(need)) < need.count for need in plan.needs])
            session_expired = self._session.remaining_ms <= 0 and not (plan.script == 'EssMiner' and plan.output)
            if not game.in_combat() and (reached or exhausted or depleted_on_finish or session_expired):
                self._activity.stop()
                if not reached and (exhausted or depleted_on_finish):
                    self._session.resupply(_core.step_time())
                    self._retry = plan
                    self._set_status(f'Supplies exhausted for {plan.label}; checking bank before continuing')
                else:
                    self._report(Record({
                        'id': 'train',
                        'message': (f'Completed: {describe_activity(plan)}' if reached else f'Training session finished: {plan.label}'),
                        'state': 'done',
                    }))
                    self._session.complete(_core.step_time(), reached)
                    if not reached:
                        self._pending_plans = []
                self._phase = 'bank'
                self._stock.invalidate()
                self._save()
                return
            if self._activity.outcome or self._session.stalled(_core.step_time()):
                _v4 = (self._activity.outcome.reason if self._activity.outcome is not None else None)
                self._fail((_v4 if _v4 is not None else 'no progress for three minutes'))
                return
            yield from self._eat()
            yield from self._activity.loop()
            self._observe()
        except Exception as error:
            if isinstance(error, ActivityTravelError) and self._session.plan and self._session.plan.combat:
                now = _core.step_time()
                self._record_failure(str(error))
                self._activity.stop()
                self._session.memory.cooldowns[self._session.plan.id] = now + 15 * 60000
                self._session.resupply(now)
                self._retry = None
                self._pending_plans = []
                self._phase = 'bank'
                self._stock.invalidate()
                self._actions.fail(str(error))
                self._set_status(f'{str(error)}; trying another combat camp')
                self._waiting_until = now + 3000
                self._save()
                return
            if isinstance(error, SupplyStockError):
                for item in error.items:
                    self._temporarily_unavailable[item] = _core.step_time() + 60000

                self._activity.stop()
                self._session.resupply(_core.step_time())
                self._retry = None
                self._pending_plans = []
                self._phase = 'bank'
                self._stock.invalidate()
                self._set_status(f'{str(error)}; checking available alternatives while the shop restocks')
                self._waiting_until = _core.step_time() + 3000
                self._save()
                return
            if isinstance(error, SupplyUnavailableError):
                for item in error.items:
                    self._unavailable_items.add(item)

                self._activity.stop()
                self._session.resupply(_core.step_time())
                self._retry = None
                self._pending_plans = []
                self._phase = 'bank'
                self._stock.invalidate()
                self._actions.fail(str(error))
                self._set_status(f'{str(error)}; checking available alternatives at the bank')
                self._waiting_until = _core.step_time() + 3000
                return
            self._fail(str(error))

    def on_pause(self):
        _fn5 = getattr(self._activity.child, 'on_pause', None)
        if _fn5 is not None:
            _fn5()

    def on_resume(self):
        self._session.observe(f'resumed:{_core.step_time()}', _core.step_time())
        self._session.sample_work(_core.step_time(), False)
        _fn6 = getattr(self._activity.child, 'on_resume', None)
        if _fn6 is not None:
            _fn6()

    def on_stop(self, reason=None):
        if self._stop_observing is not None:
            self._stop_observing()
        self._stop_observing = None
        self._activity.stop()
        sustain.set(None)
        self._save()

    def grind_targets(self):
        _v7 = (self._activity.child.grind_targets() if self._activity.child is not None else None)
        return (_v7 if _v7 is not None else [])

    def ignored_randoms(self):
        _v8 = (self._activity.child.ignored_randoms() if self._activity.child is not None else None)
        return (_v8 if _v8 is not None else [])

    def recovery_anchor(self):
        tile = (self._session.plan.travel if self._session.plan is not None else None)
        _fn9 = getattr(self._activity.child, 'recovery_anchor', None)
        return (Tile(tile.x, tile.z, tile.level) if tile else ((_fn9() if _fn9 is not None else None) if (_fn9() if _fn9 is not None else None) is not None else None))


    def _snapshot(self):
        self._stock.observe(bank.items(), bank.ready())
        return Record({
            'levels': {_k: _v for _k, _v in [[skill, skills.level(skill)] for skill in enabled_skills]},
            'stock': self._stock.total(list(inventory.items()) + list(equipment.items())),
            'bank_ready': self._stock.ready,
            'quests': {quest.name: quest.status == 'complete' for quest in quests.all()},
            'dragon_stage': self._dragon_stage,
            'quest_points': quests.points(),
            'target': self._target,
            'wilderness': self._wilderness,
            'now': _core.step_time(),
            'unavailable_items': list(self._unavailable_items) + list([item for item, _2 in [(_1, until) for _1, until in list(self._temporarily_unavailable.items()) if until > _core.step_time()]]),
        })

    def _select_and_start(self):
        self._actions.destination = None
        self._shopping_budget = 0
        self._set_status('checking supplies at the nearest bank')
        _w12 = yield from self._supplies.bank()
        if not (_w12):
            raise RuntimeError('Nearest bank could not be opened')
        snapshot = self._snapshot()
        if dragon_ready(snapshot) and quests.status('Dragon Slayer') == 'in_progress':
            yield from bank.close()
            progress = yield from read_dragon_progress()
            self._dragon_stage = progress.stage if progress else None
            opened = yield from self._supplies.bank()
            if not opened:
                raise RuntimeError('Could not reopen bank after reading Dragon Slayer progress')
            snapshot = self._snapshot()
        upgraded = yield from self._try_dragon_weapons(snapshot)
        if upgraded:
            snapshot = self._snapshot()
        if in_zanaris(game.tile()):
            self._set_status('Leaving Zanaris before preparing the next activity')
            returned = yield from leave_zanaris(game_zanaris_port(self._set_detail))
            if not returned:
                raise RuntimeError('Could not leave Zanaris before preparing the next activity')
            opened = yield from self._supplies.bank()
            if not opened:
                raise RuntimeError('Could not reopen a mainland bank after leaving Zanaris')
            snapshot = self._snapshot()
        if not self._shopping_checked:
            audit = audit_supplies(snapshot)
            self._shopping_budget = audit.budget
            if len(audit.needs):
                plan = Record({
                    'id': 'stock-up',
                    'label': 'Stock up for unfinished skills',
                    'objective': (self._session.memory.objective if self._session.memory.objective is not None else 'supplies'),
                    'script': '',
                    'settings': Record({}),
                    'needs': audit.needs,
                })
                self._display_plan = plan
                self._actions.reset(activity_actions(plan, snapshot, [], True))
                self._shopping_checked = True
                self._set_status(f'Bank audit: {len(audit.needs)} supplies to stock; budget {audit.budget}gp plus travel reserve')
                if len(audit.skipped):
                    self._set_detail(f"Deferred purchases: {'; '.join(audit.skipped)}")
                try:
                    yield from provision(plan, self._supplies, lambda event: self._report(event), True)
                except Exception as e:
                    self._shopping_budget = 0
                    raise e

                self._shopping_budget = 0
                _w13 = yield from self._supplies.bank()
                if not (_w13):
                    raise RuntimeError('Could not reopen bank after stocking supplies')
                snapshot = self._snapshot()
            else:
                self._set_detail((f"Bank audit: deferred {'; '.join(audit.skipped)}" if len(audit.skipped) else 'Bank audit: supplies already stocked for unfinished skills'))
            self._shopping_checked = True
            self._shopping_budget = 0
        requested = (self._retry if self._retry is not None else (self._pending_plans.pop(0) if self._pending_plans else None))
        if (requested.death_walk if requested is not None else None) and combat_level(snapshot.levels) >= 15:
            self._set_detail('Combat 15 reached; replacing the queued death walk with food-backed training')
            self._pending_plans = []
            requested = None
        if requested and not can_resume_objective(snapshot.levels, snapshot.target, requested.objective):
            self._set_detail(f'{training_priority(snapshot.levels, snapshot.target).label}; replanning queued {requested.objective} work')
            self._pending_plans = []
            requested = None
        if requested:
            requested = refresh_consumables(snapshot, requested)
        decision = (resolve_activity(snapshot, requested, self._session.memory, random.random) if requested else plan_next(snapshot, self._session.memory))
        self._retry = None
        if decision.kind == 'blocked':
            self._set_detail(f'Replanning: {decision.reason}')
            self._pending_plans = []
            decision = plan_next(snapshot, self._session.memory)
        if decision.kind == 'complete':
            yield from bank.close()
            self.request_finish(f'All {len(enabled_skills)} enabled skills reached {self._target}')
            return
        if decision.kind == 'refresh':
            return
        if decision.kind == 'blocked':
            now = _core.step_time()
            cooldown = min([time for time in list(list(self._session.memory.cooldowns.values())) + list(list(self._temporarily_unavailable.values())) if time > now])
            self._waiting_until = min(cooldown, now + 30000)
            self._unavailable_items.clear()
            self._stock.invalidate()
            self._set_status(f'waiting for another method: {decision.reason}; rechecking in {math.ceil((self._waiting_until - now) / 1000)}s')
            yield from bank.close()
            return
        plan = decision.plan
        _c14 = plan.script == 'Woodcutter'
        if _c14:
            _w15 = yield from self._try_market_axe(snapshot)
            _c14 = _w15
        if _c14:
            snapshot = self._snapshot()


            plan.needs = [(gathering_tool(snapshot, 'axe') if (need.item.lower().endswith(' axe')) else need) for need in plan.needs]
        self._pending_plans = list(decision.queue[1:]) + list(self._pending_plans)
        self._display_plan = plan
        self._actions.reset(activity_actions(plan, snapshot, self._pending_plans))
        meta = manifest_for(plan.script)
        if not meta:
            raise RuntimeError(f'Missing activity script {plan.script}')
        self._session.start(plan, _core.step_time(), random.random)
        self._save()
        self._set_status(f'preparing {plan.label} for {plan.objective}')
        sustain.set(lambda: self._eat())
        yield from provision(plan, self._supplies, lambda event: self._report(event))
        yield from self._recover_nearby_drops(plan)
        if plan.travel:
            here = game.tile()
            if here and (here.x < 2840) != (plan.travel.x < 2840) and inventory.count('Coins') < 60:
                raise RuntimeError('Need 60 Coins for the coastal boat route before crossing between eastern and western training sites')
            self._report(Record({
                'id': 'travel',
                'message': f'Travelling to {plan.label}',
                'state': 'running',
                'destination': plan.travel,
            }))
            _w16 = yield from self._supplies.walk(plan.travel)
            if not (_w16):
                raise ActivityTravelError(f'Cannot reach {plan.label}')
            self._report(Record({
                'id': 'travel',
                'message': f'Arrived at {plan.label}',
                'state': 'done',
                'destination': plan.travel,
            }))
        self._report(Record({
            'id': 'train',
            'message': f'{describe_activity(plan)} using {plan.script}',
            'state': 'running',
            'destination': plan.travel,
        }))
        yield from self._activity.start(meta, {key: value for key, value in plan.settings.items()})
        self._session.sample_work(_core.step_time(), False)
        self._phase = 'train'
        self._reset_count = 0
        self._observe()

    def _try_market_axe(self, snapshot):
        if self._market_checked or not self.settings.bool('market_axes', True) or stock_of(snapshot, 'Rune axe') > 0:
            return False
        world = game.world()
        if world != 1:
            return False
        here = game.tile()
        if not here or Tile(2725, 3491, 0).distance_to(here) > 128:
            return False
        self._market_checked = True
        budget = math.floor(min(self.settings.num('market_axe_budget', 50000), stock_of(snapshot, 'Coins') * 0.1, stock_of(snapshot, 'Coins') - 200))
        if budget < 1:
            return False
        self._set_status(f'Checking seers market for a Rune axe; limit {budget} coins')
        yield from self._supplies.deposit()
        _w17 = yield from self._supplies.withdraw('Coins', budget + 200)
        if not (_w17):
            return False
        _w18 = yield from self._supplies.close_bank()
        if not (_w18):
            return False
        bought = yield from self._market_buyer.buy(Record({
            'item': 'Rune axe',
            'max_price': budget,
            'world': world,
            'log': lambda message: self._set_detail(message),
        }))
        _w19 = yield from self._supplies.bank()
        if not (_w19):
            raise RuntimeError('Could not bank after checking Seers market')
        yield from self._supplies.deposit()
        self._set_detail(('Rune axe banked; preparing woodcutting supplies' if bought else 'Seers market upgrade unavailable; using available axe'))
        return bought

    def _try_dragon_weapons(self, snapshot):
        if self._session.memory.cooldowns.get(DRAGON_SHOP_COOLDOWN, 0) > snapshot.now:
            return False
        audit = audit_dragon_weapons(snapshot)
        if not audit.needs:
            if audit.skipped:
                self._set_detail('; '.join(audit.skipped))
            return False
        self._session.memory.cooldowns[DRAGON_SHOP_COOLDOWN] = snapshot.now + 900000
        plan = Record({'id': DRAGON_SHOP_COOLDOWN, 'label': 'Buy dragon weapons in Zanaris', 'objective': 'attack', 'script': '', 'settings': {}, 'needs': audit.needs})
        self._display_plan = plan
        self._actions.reset(activity_actions(plan, snapshot, [], True))
        self._shopping_budget = audit.budget
        self._set_status(f'Buying dragon weapons; budget {audit.budget} coins')
        self._save()
        try:
            yield from provision(plan, self._supplies, self._report)
        except Exception as error:
            self._set_detail(f'Dragon weapon purchase deferred for 15 minutes: {str(error)}')
        self._shopping_budget = 0
        opened = yield from self._supplies.bank()
        if not opened:
            raise RuntimeError('Could not return to a bank after checking dragon weapons')
        yield from self._supplies.deposit()
        return True

    def _reached(self, plan, snapshot):
        if plan.script == 'EssMiner' and plan.output and (not bank.is_open() or not bank.ready() or inventory.count(plan.output.item) > 0):
            return False
        if plan.output:
            return stock_of(snapshot, plan.output.item) >= plan.output.count
        if plan.prerequisite_levels:
            return all([snapshot.levels.get(skill) >= level for skill, level in list(plan.prerequisite_levels.items())])
        if plan.quest:
            return snapshot.quests.get(plan.quest) == True
        return snapshot.levels.get(plan.objective) >= snapshot.target

    def _observe(self):
        tile = game.tile()
        signature = json.dumps([
            [skills.xp(skill) for skill in enabled_skills],
            serializable(tile),
            [[i.id, i.count] for i in inventory.items()],
            quests.points(),
        ])
        self._session.observe(signature, _core.step_time())

    def _record_failure(self, reason):
        _v21 = (self._session.plan.label if self._session.plan is not None else None)
        _v22 = (_v21 if _v21 is not None else (self._display_plan.label if self._display_plan is not None else None))
        self._last_failure = Record({
            'at': _core.step_time(),
            'activity': (_v22 if _v22 is not None else 'preparation'),
            'phase': self._phase,
            'reason': reason,
            'detail': self._detail,
        })
        self._save()

    def _fail(self, reason):
        now = _core.step_time()
        previous = self._session.plan
        self._record_failure(reason)
        self._activity.stop()
        preparing = self._phase == 'bank' or not previous
        if preparing:
            self._reset_count += 1

        decision = (('reset' if self._reset_count < 3 else 'rotate') if preparing else self._session.failure(now))
        self._actions.fail(reason)
        if preparing and decision == 'rotate':
            if previous and uses_activity_cooldown(previous):
                self._session.memory.cooldowns[previous.id] = now + 15 * 60000
            self._session.resupply(now)
        self._retry = (previous if decision == 'reset' else None)
        if decision == 'rotate':
            self._pending_plans = []
        delay = (min(60000, 3000 * 2 ** min(self._reset_count - 1, 5)) if preparing else (30000 if decision == 'rotate' else 3000))
        self._set_status(f"{reason}; {('resetting at the nearest bank' if decision == 'reset' else 'replanning at the nearest bank')} in {delay / 1000}s")
        self._phase = 'bank'
        self._stock.invalidate()
        self._waiting_until = now + delay
        self._save()

    def _eat(self):
        food = (self._session.plan.food if self._session.plan is not None else None)
        if not food or skills.hp_fraction() > 0.65 or bank.is_open():
            return
        item = ([i for i in inventory.items() if not i.noted and (i.name.lower() if i.name is not None else None) == food.lower() and ('Eat' in i.actions())] or [None])[0]
        if item:
            item.interact('Eat')
            yield from execution.delay_ticks(1)

    def _recover_nearby_drops(self, plan):
        death = self._death_tile
        self._death_tile = None
        here = game.tile()
        if not death or not here or death.level != here.level or plan.wilderness or max(abs(death.x - here.x), abs(death.z - here.z)) > 64:
            return
        _w23 = yield from traversal.walk_resilient(Tile.from_tile(death), radius=3, timeout_ms=30000, avoid_zones=leveler_travel_zones(death, self._wilderness))
        if not (_w23):
            return
        wanted = set([n.item.lower() for n in plan.needs])
        for tries in range(10):
            if not (not inventory.is_full()):
                break
            item = ground_items.query().where(lambda i: i.distance() <= 8 and (((i.name.lower() if i.name is not None else None) if (i.name.lower() if i.name is not None else None) is not None else '') in wanted)).nearest()
            if not item:
                break
            before = inventory.used()
            item.interact('Take')
            _w24 = yield from execution.delay_until(lambda: inventory.used() > before, 2000)
            if not (_w24):
                break

    def _set_status(self, message):
        if message != self._status:
            self.log(message)
            self._actions.changed_at = _core.step_time()
        self._status = message
        self._actions.current = message
        self._actions.note(message)
        self._save()

    def _report(self, event):
        self._actions.update(event)
        self._set_status(event.message)

    def _set_detail(self, message):
        self._detail = message
        self._actions.note(message)
        self.log(message)
        if _core.step_time() - self._last_saved_at > 5000:
            self._save()

    def _load(self):
        saved = settings_store.saved('AccountLevelerState', 'progress')
        memory = empty_memory()
        if not isinstance(saved, dict):
            self._session = LevelerSession(memory)
            return
        objective = saved.get('objective')
        memory.objective = objective if isinstance(objective, str) and objective in enabled_skills else None
        recent = saved.get('recent')
        memory.recent = [entry for entry in recent if isinstance(entry, str)][-6:] if isinstance(recent, list) else []
        # step_time is process-relative. Persist attempts as relative ordering, and cooldowns as durations.
        now = _core.step_time()
        for field in ['attempted', 'cooldowns']:
            values = saved.get(field)
            if not isinstance(values, dict):
                continue
            for key, value in values.items():
                if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
                    continue
                if field == 'cooldowns' and not key.startswith('quest-') and key != 'ranging-guild' and key not in DRAGON_CAMPS and not any([camp.id == key for camp in COMBAT_CAMPS]):
                    continue
                memory[field][key] = now + min(900000, max(0, value)) if field == 'cooldowns' else value
        deaths = saved.get('deaths', 0)
        memory.deaths = max(0, int(deaths)) if isinstance(deaths, (int, float)) and math.isfinite(deaths) else 0
        self._session = LevelerSession(memory)
        diagnostics = saved.get('diagnostics', {})
        if isinstance(diagnostics, dict):
            self._last_failure = diagnostics.get('failure')
            history = diagnostics.get('history', [])
            if isinstance(history, list):
                self._actions.history = [Record(row) for row in history[-20:] if isinstance(row, dict) and isinstance(row.get('message'), str)]

    def _save(self):
        memory = self._session.memory
        now = _core.step_time()
        saved = {
            'objective': memory.objective, 'recent': memory.recent,
            'deaths': memory.deaths,
            'attempted': {entry[0]: index for index, entry in enumerate(sorted(memory.attempted.items(), key=lambda entry: entry[1]))},
            'cooldowns': {key: max(0, value - now) for key, value in memory.cooldowns.items()},
            'diagnostics': {
                'action': self._status, 'detail': self._detail,
                'plan': self._display_plan.label if self._display_plan else None,
                'failure': serializable(self._last_failure),
                'tile': serializable(game.tile()),
                'destination': serializable(self._actions.destination),
                'queue': serializable(self._actions.items),
                'history': serializable(self._actions.history[-20:]),
            },
        }
        settings_store.save('AccountLevelerState', 'progress', saved)
        self._last_saved_at = now

    def on_progress_report(self):
        return {'Status': self._status, 'Detail': self._detail, 'Deaths': self._session.memory.deaths,
                'Activity': self._session.plan.label if self._session.plan else 'Preparing',
                'Remaining work (minutes)': round(self._session.remaining_ms / 60000, 1)}


def serializable(value):
    if isinstance(value, Record):
        return {key: serializable(entry) for key, entry in value.items()}
    if isinstance(value, (list, tuple)):
        return [serializable(entry) for entry in value]
    if isinstance(value, Tile):
        return [value.x, value.z, value.level]
    return value


BOT = define_bot(
    name='AccountLeveler',
    description='Trains melee first, then remaining combat skills, then other enabled members skills to 60. Stocks essence in batches of 1,000 and uses Edgeville monkey bars from Agility 15. Buys supplies, runs required quests, and recovers from death. Wilderness training is optional and enabled by default.',
    category='General',
    tags=['training', 'combat', 'skilling', 'quests', 'banking', 'death-recovery'],
    settings_schema=SETTINGS,
    create=AccountLeveler,
)
