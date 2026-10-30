"""Search and identify Rogues purse: rs2b0t's RoguesPurse (MIT, see thirdparty/rs2b0t)."""
import _core
from rs2004.catalogs.record import Record
from rs2004.navigation import navigator
from rs2004.traversal import BANK_LOCATIONS, bank_unlocked
from rs2004.bank import open_bank_access
from rs2004.quests.defs.junglepotion import JUNGLE_HERBS, POTHOLE_ENTRANCE, enter_pothole, in_caves, leave_pothole, read_jungle_progress
from rs2004.quests.exec.prompts import settle_scene
from bots.roguespurse.logic import COINS, FARE, FARE_FLOAT, IDENTIFY_XP, bank_tile, check_gates, is_level_refusal, is_stage_refusal, plan_cycle, rank_banks_by_detour

PURSE = [h for h in JUNGLE_HERBS if h.key == 'rogues purse'][0]
ANCHOR_SLACK = 3
DEAD_SEARCHES = 30
SETTINGS = {'mode': SettingDef('string', 'drop', 'Herb destination', options=['drop', 'bank'], help='drop for the original Herblore cycle, or bank full loads')}


class RoguesPurse(LoopingBot):
    loop_delay = 0

    def on_start(self):
        self.status = 'starting'
        self.xp_start = skills.xp('herblore')
        self.searches = 0
        self.dead_searches = 0
        self.deaths = 0
        self.refusal = None
        self.need_fare = False
        self.banked = 0
        progress = yield from read_jungle_progress()
        gate = check_gates(Record({'herblore_level': skills.level('herblore'), 'stage': progress.stage if progress else None}))
        if not gate.ok:
            self.request_finish('RoguesPurse: ' + gate.reason)
            return
        self.on('chat_message', self.heard)

    def heard(self, line):
        if is_stage_refusal(line.text):
            self.refusal = 'the wall found nothing; Jungle Potion is not far enough along'
        elif is_level_refusal(line.text):
            self.refusal = 'the herb refused to identify; Herblore level too low'

    def on_death(self):
        self.deaths += 1
        self.need_fare = True
        self.dead_searches = 0
        self.status = 'died; recovering'

    def at_wall(self):
        here = game.tile()
        return here is not None and in_caves(here) and PURSE.stand.distance_to(here) <= ANCHOR_SLACK

    def loop(self):
        if self.refusal:
            self.request_finish('RoguesPurse: ' + self.refusal)
            return
        if self.settings.str('mode', 'drop') == 'bank' and inventory.is_full():
            yield from self.bank_load()
        elif not self.at_wall():
            yield from self.travel()
        else:
            wall = locs.query().name(PURSE.loc).action(PURSE.op).where(lambda loc: loc.tile().distance_to(PURSE.at) <= 2).nearest()
            if wall:
                yield from self.cycle(wall)
            else:
                self.status = 'waiting for the scene'
                yield from settle_scene()
        yield from execution.delay_ticks(1)

    def cycle(self, wall):
        unid = [item for item in inventory.items() if item.id == PURSE.unid_id]
        herbs = [item for item in inventory.items() if item.id == PURSE.id]
        if unid or herbs:
            self.dead_searches = 0
        self.status = 'identifying'
        dropping = self.settings.str('mode', 'drop') == 'drop'
        plan = plan_cycle(Record({'continue_pending': chat_dialog.can_continue(), 'unids': len(unid), 'identified': len(herbs) if dropping else 0, 'free_slots': inventory.free()}))
        for action in plan:
            if action == 'continue':
                _core.continue_dialogue()
            elif action == 'identify':
                unid[0].interact('Identify')
            elif action == 'drop':
                herbs[0].interact('Drop')
            elif action == 'search' and wall.interact(PURSE.op):
                self.searches += 1
                self.dead_searches += 1
                if self.dead_searches >= DEAD_SEARCHES:
                    self.refusal = f'{DEAD_SEARCHES} searches in a row found no herb'
        if False:
            yield

    def travel(self):
        if not in_caves(game.tile()):
            if self.need_fare and inventory.count(COINS) < FARE:
                funded = yield from self.fetch_fare()
                if not funded:
                    return
            self.need_fare = False
            self.status = 'walking to the pothole'
            walked = yield from traversal.walk_resilient(POTHOLE_ENTRANCE.stand, radius=2, attempts=4, timeout_ms=300000, log=self.log)
            if not walked:
                if traversal.last_outcome == 'unreachable' and inventory.count(COINS) < FARE:
                    yield from self.fetch_fare()
                return
            entered = yield from enter_pothole(self.log)
            if not entered and not in_caves(game.tile()):
                return
        self.status = 'walking to the wall'
        walked = yield from traversal.walk_resilient(PURSE.stand, radius=1, attempts=4, timeout_ms=180000, log=self.log)
        if walked:
            yield from settle_scene()

    def reachable_bank(self):
        here = game.tile()
        if here is None:
            return None
        candidates = [row for row in BANK_LOCATIONS if bank_tile(row).level == here.level and bank_unlocked(row)]
        for row in rank_banks_by_detour(here, POTHOLE_ENTRANCE.stand, candidates)[:4]:
            if navigator.find_path(here, bank_tile(row), max_expansions=300000).ok:
                return row
        return None

    def fetch_fare(self):
        self.status = 'banking for the boat fare'
        destination = self.reachable_bank()
        if destination is None:
            return False
        walked = yield from traversal.walk_resilient(bank_tile(destination), radius=4, attempts=4, timeout_ms=300000, log=self.log)
        if not walked:
            return False
        opened = yield from open_bank_access(destination, {'name': 'Bank booth', 'op': 'Use-quickly'}, self.log)
        if not opened:
            return False
        funded = False
        try:
            ready = yield from execution.delay_until(lambda: bank.loaded(), 4000)
            if ready:
                have = bank.count(COINS)
                if have < FARE:
                    self.refusal = f'no boat fare; needs {FARE}gp for the Karamja ship'
                else:
                    yield from bank.withdraw_x(COINS, min(FARE_FLOAT, have))
                    funded = inventory.count(COINS) >= FARE
        except Exception as error:
            yield from bank.close()
            raise error
        yield from bank.close()
        return funded

    def bank_load(self):
        self.status = 'banking herbs'
        # The search's objbox suspends the cave script until it is acknowledged.
        if chat_dialog.can_continue():
            yield from chat_dialog.continue_()
        while inventory.count_by_id(PURSE.unid_id) > 0:
            unid = [item for item in inventory.items() if item.id == PURSE.unid_id][0]
            before = inventory.count_by_id(PURSE.unid_id)
            if not unid.interact('Identify'):
                return False
            identified = yield from execution.delay_until(lambda: inventory.count_by_id(PURSE.unid_id) < before, 6000)
            if not identified:
                return False
        escaped = yield from leave_pothole(self.log)
        if not escaped:
            return False
        opened = yield from banking.open(log=self.log)
        if not opened:
            return False
        before = inventory.count_by_id(PURSE.id)
        try:
            yield from bank.deposit_all_matching(lambda name, id: id == PURSE.id)
        except Exception as error:
            yield from bank.close()
            raise error
        yield from bank.close()
        deposited = max(0, before - inventory.count_by_id(PURSE.id))
        self.banked += deposited
        self.need_fare = True
        return deposited > 0

    def recovery_anchor(self):
        return PURSE.stand

    def on_progress_report(self):
        return {'Status': self.status, 'Identified': round((skills.xp('herblore') - self.xp_start) / IDENTIFY_XP), 'Searches': self.searches, 'Deaths': self.deaths, 'Banked': self.banked}


BOT = define_bot(name='RoguesPurse', create=RoguesPurse, settings_schema=SETTINGS, description='Searches and identifies Rogues purse under the Karamja jungle. Drops herbs by default, or banks full loads. Needs Herblore 3 and Jungle Potion at the Rogues purse stage.', category='Herblore', tags=['herblore', 'karamja', 'members', 'afk'])
