"""Quest supply plans from rs2b0t's AIOQuester/supplyProducers.ts (MIT, see thirdparty/rs2b0t)."""

from bots.account_leveler.record import Record
from bots.account_leveler.combat import combat_plan
from bots.account_leveler.types import stock_of
from bots.brimhaven_agility import ARENA_ENTRANCE, TICKET_NAME, TRIP_COINS
from rs2004.catalogs.thieving import STAND
from rs2004.geometry import Tile

__all__ = ['quest_supply_producer']

def quest_supply_producer(s, need, memory, random):
    _case1 = need.item.lower()
    if _case1 == 'agility potion(3)':
        missing = need.count - stock_of(s, need.item)
        unfinished = min(missing, stock_of(s, '#3002'))
        herbs = missing - unfinished
        return Record({
            'id': 'quest-agility-potions',
            'label': 'Brew Agility potions',
            'objective': 'herblore',
            'script': 'PotionMaker',
            'settings': Record({'herb': 'Toadflax', 'secondary': "Toad's legs", 'output_id': 3034, 'output_count': need.count}),
            'output': Record({'item': need.item, 'count': need.count}),
            'needs': list(([
            Record({'item': 'Toadflax', 'count': herbs, 'carry': 0}),
            Record({'item': 'Vial of water', 'count': herbs, 'carry': 0}),
        ] if herbs > 0 else [])) + list(([Record({'item': 'Unfinished potion', 'id': 3002, 'count': unfinished, 'carry': 0})] if unfinished > 0 else [])) + [Record({'item': "Toad's legs", 'count': missing, 'carry': 0})],
        })
    elif _case1 == 'toadflax':
        tickets = (need.count - stock_of(s, 'Toadflax')) * 3
        return Record({
            'id': 'quest-toadflax',
            'label': 'Trade Brimhaven tickets for Toadflax',
            'objective': 'supplies',
            'script': 'QuestToadflax',
            'settings': Record({}),
            'travel': Tile.from_tile(ARENA_ENTRANCE),
            'output': Record({'item': 'Toadflax', 'count': need.count}),
            'needs': [
            Record({'item': TICKET_NAME, 'count': tickets, 'carry': tickets}),
            Record({'item': 'Coins', 'count': 60, 'carry': 60}),
        ],
        })
    elif _case1 == 'agility arena ticket':
        return Record({
            'id': 'quest-arena-tickets',
            'label': 'Earn Brimhaven Agility tickets',
            'objective': 'agility',
            'script': 'QuestArenaTickets',
            'settings': Record({
            'count': need.count,
            'food': 'Lobster',
            'food_withdraw': 12,
            'bank_at_tickets': need.count,
            'steal_restock': False,
        }),
            'food': 'Lobster',
            'output': Record({'item': TICKET_NAME, 'count': need.count}),
            'needs': [
            Record({'item': 'Coins', 'count': TRIP_COINS, 'carry': TRIP_COINS}),
            Record({'item': 'Lobster', 'count': 12, 'carry': 12}),
        ],
        })
    elif _case1 == "toad's legs":
        return Record({
            'id': 'quest-toad-legs',
            'label': 'Gather swamp toad legs',
            'objective': 'supplies',
            'script': 'HerbloreSecondaries',
            'settings': Record({'secondary': "Toad's legs", 'food_withdraw': 0}),
            'needs': [],
            'output': Record({'item': "Toad's legs", 'count': need.count}),
        })
    elif _case1 == 'cake':
        return Record({
            'id': 'quest-cakes',
            'label': 'Steal quest cakes',
            'objective': 'thieving',
            'script': 'QuestCakeSupply',
            'settings': Record({'count': need.count}),
            'needs': [],
            'travel': STAND,
            'output': Record({'item': 'Cake', 'count': need.count}),
        })
    elif _case1 == 'seaweed':
        return Record({
            'id': 'quest-seaweed',
            'label': 'Gather coastal seaweed',
            'objective': 'supplies',
            'script': 'QuestGroundSupply',
            'settings': Record({'item': 'Seaweed'}),
            'needs': [],
            'travel': Tile(2708, 3728, 0),
            'output': Record({'item': 'Seaweed', 'count': need.count}),
        })
    elif _case1 == 'bat bones':
        plan = combat_plan(s, 'attack', memory, random)
        if not plan:
            return None
        tile = Tile(2589, 3478, 0)
        _merged2 = {}
        for _k, _v in (plan.settings._fields if isinstance(plan.settings, Record) else plan.settings).items():
            _merged2[_k] = _v
        for _k, _v in {
            'target': 'Giant bat',
            'coordinates': tile,
            'loot': ['Bat bones'],
            'bury_bones': False,
            'bury_big_bones': False,
        }.items():
            _merged2[_k] = _v
        _merged3 = {}
        for _k, _v in (plan._fields if isinstance(plan, Record) else plan).items():
            _merged3[_k] = _v
        for _k, _v in {
            'id': 'quest-bat-bones',
            'label': 'Gather Giant bat bones',
            'travel': tile,
            'output': Record({'item': 'Bat bones', 'count': need.count}),
            'settings': Record(_merged2),
        }.items():
            _merged3[_k] = _v
        return Record(_merged3)
    else:
        return None
