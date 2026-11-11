"""Quest supply activities from rs2b0t's AIOQuester (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004.catalogs.thieving import FLEE_TILE, STAND, steal_cakes
from bots.brimhaven_agility import BrimhavenAgility, SETTINGS as AGILITY_SETTINGS, TICKET_NAME, in_arena


def in_quest_arena():
    tile = game.tile()
    return tile is not None and in_arena(tile.x, tile.z)


def exit_quest_arena(log):
    if not in_quest_arena():
        return
    bot = BrimhavenAgility()
    bot.bind_log(log)
    deadline = _core.step_time() + 180000
    while bot.in_arena_now():
        if _core.step_time() >= deadline:
            raise RuntimeError('Could not leave Brimhaven Agility Arena')
        yield from bot.leave_arena()
        yield from execution.delay_ticks(1)


class QuestGroundSupply(LoopingBot):
    def loop(self):
        name = self.settings.str('item', '')
        item = ground_items.query().name(name).within(8).nearest()
        if item is None:
            yield from execution.delay_ticks(2)
            return
        before = inventory.count(name)
        if item.interact('Take'):
            yield from execution.delay_until(lambda: inventory.count(name) > before, 4000)


class QuestToadflax(LoopingBot):
    def loop(self):
        if inventory.count(TICKET_NAME) < 3:
            self.request_finish('No tickets left for Toadflax')
            return
        if modals.main() != 8292:
            if modals.is_open():
                closed = yield from modals.close()
                if not closed:
                    return
            trader = npcs.query().where(lambda npc: npc.id == 1055).nearest()
            if trader is not None and trader.interact('Trade'):
                yield from execution.delay_until(lambda: modals.main() == 8292, 5000)
            return
        before = inventory.count_by_id(2998)
        tickets = inventory.count(TICKET_NAME)
        if interfaces.click(8382):
            yield from execution.delay_until(lambda: inventory.count_by_id(2998) > before and inventory.count(TICKET_NAME) <= tickets - 3, 5000)


class QuestArenaTickets(BrimhavenAgility):
    def __init__(self, total):
        self.total = total

    def loop(self):
        if self.total() >= self.settings.num('count', 6):
            if self.in_arena_now():
                yield from self.leave_arena()
            return
        yield from super().loop()


class QuestCakeSupply(LoopingBot):
    def __init__(self, count, bank):
        self.count = count
        self.bank_cakes = bank
        self.stopped = False

    def on_stop(self, reason):
        self.stopped = True

    def food(self):
        foods = [item for item in inventory.items() if not item.noted and 'Eat' in item.actions() and item.name.lower() in ['cake', '2/3 cake', 'slice of cake', 'bread', 'chocolate slice']]
        foods.sort(key=lambda item: item.name.lower() == 'cake')
        return foods[0] if foods else None

    def hungry(self):
        return skills.hp_fraction() <= 0.65 and self.food() is not None

    def abort(self):
        return self.stopped or self.count() >= self.settings.num('count', 8) or self.hungry()

    def loop(self):
        if self.stopped:
            return
        if game.in_combat():
            yield from traversal.walk_resilient(FLEE_TILE, radius=1, attempts=3, timeout_ms=30000)
            yield from execution.delay_until(lambda: not game.in_combat(), 10000)
            return
        if self.count() >= self.settings.num('count', 8):
            return
        if self.hungry():
            self.food().interact('Eat')
            yield from execution.delay_ticks(1)
            return
        if inventory.is_full():
            yield from self.bank_cakes()
            returned = yield from traversal.walk_resilient(STAND, radius=2, attempts=3, timeout_ms=120000)
            if not returned:
                raise RuntimeError('Cannot return to the cake stall')
            return
        yield from steal_cakes(self.abort, lambda message: None, self.log, should_eat=self.hungry)


def ground_supply_activity():
    return define_bot(name='QuestGroundSupply', create=QuestGroundSupply, settings_schema={'item': SettingDef('string', 'Seaweed')})


def toadflax_supply_activity():
    return define_bot(name='QuestToadflax', create=QuestToadflax)


def ticket_supply_activity(total):
    schema = {key: value for key, value in AGILITY_SETTINGS.items()}
    schema['count'] = SettingDef('number', 6, min=1)
    schema['food'] = SettingDef('string', 'Lobster')
    return define_bot(name='QuestArenaTickets', create=lambda: QuestArenaTickets(total), settings_schema=schema)


def cake_supply_activity(count, bank):
    return define_bot(name='QuestCakeSupply', create=lambda: QuestCakeSupply(count, bank), settings_schema={'count': SettingDef('number', 8, min=1)})
