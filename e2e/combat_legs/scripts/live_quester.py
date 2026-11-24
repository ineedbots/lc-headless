"""Run real quest legs with AIOQuester's actual food and prayer upkeep."""

import json
import _core
from bots.aio_quester import AIOQuester, AIO_SETTINGS
from rs2004 import execution
from rs2004.game import chat, game, skills
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.quests.defs.heroquest.feather import kill_ice_queen
from rs2004.quests.defs.heroquest.areas import HERO_ID
from rs2004.quests.defs.regicide.areas import RG_TILE
from rs2004.quests.defs.regicide.isafdar import kill_soldier
from rs2004.quests.defs.regicide.pass_ import leave_tirannwn
from rs2004.quests.defs.legends.viyeldi import forge_heart_crystal
from rs2004.quests.defs.legends.areas import LQ_ID
from rs2004.quests.food import quest_food
from rs2004.quests.prayer import set_quest_prayer
from rs2004.catalogs.record import Record
from rs2004.traversal import traversal


class LegQuester(AIOQuester):
    def on_start(self):
        yield from AIOQuester.on_start(self)
        case = self.settings.str('e2e_case', '')
        self.running_id = {'hq': 'hero', 'rg': 'regicide', 'lq': 'legends'}[case]
        quest_food.name = self.food_item()
        if case != 'lq':
            set_quest_prayer(Record({'protect': 'melee'}), self.log)
        chat.command('infiniterun')
        yield from execution.delay_ticks(2)
        started = _core.step_time()
        if case == 'hq':
            ok = yield from kill_ice_queen(self.log)
            ok = ok and inventory.count_by_id(HERO_ID.ICE_GLOVES) > 0
            if ok:
                self.log('Ice Queen goal reached; returning to Catherby bank before logout')
                ok = yield from traversal.walk_resilient(Tile(2807, 3441, 0), radius=3, attempts=3, timeout_ms=180000, log=self.log)
        elif case == 'rg':
            ok = yield from kill_soldier(self.log)
            if ok:
                ok = yield from leave_tirannwn(RG_TILE.QUARRY, 11, self.log)
        else:
            ok = yield from forge_heart_crystal(self.log)
            ok = ok and inventory.count_by_id(LQ_ID.HEART_CRYSTAL) > 0
        yield from execution.delay_ticks(20)
        self.log('E2E_RESULT ' + json.dumps({'case': case, 'name': game.my_name(),
            'passed': bool(ok and self.deaths == 0), 'deaths': self.deaths,
            'elapsed_ms': _core.step_time() - started, 'hp': skills.effective('hitpoints'),
            'tile': str(game.tile())}))
        stop_account()


SCHEMA = {key: value for key, value in AIO_SETTINGS.items()}
SCHEMA['e2e_case'] = SettingDef('string', '')
SCHEMA['e2e_infinite_run'] = SettingDef('boolean', True)
BOT = define_bot(name='AIOQuester', create=LegQuester, settings_schema=SCHEMA)
