"""Earn a blocked training budget without an up-front shop or travel allowance."""

from bots.account_leveler.record import Record
from bots.account_leveler.types import stock_of
from bots.account_leveler.shopping import SHOPPING_RESERVE
from rs2004.geometry import Tile


def coin_plan(snapshot, objective, budget):
    farmer = snapshot.levels.get('thieving', 0) >= 10
    west = snapshot.tile is not None and snapshot.tile.x < 2840
    food = ([name for name in ['Shark', 'Lobster', 'Salmon', 'Trout', 'Shrimps', 'Bread'] if stock_of(snapshot, name) > 0] or [None])[0]
    carried = min(12, stock_of(snapshot, food)) if food else 0
    if west:
        travel = Tile(2645, 3367, 0) if farmer else Tile(2694, 3497, 0)
    else:
        travel = Tile(3227, 3290, 0) if farmer else Tile(3221, 3219, 0)
    return Record({
        'id': 'earn-coins-farmers' if farmer else 'earn-coins-men-women',
        'label': 'Pickpocket farmers for training coins' if farmer else 'Pickpocket men and women for training coins',
        'objective': objective,
        'script': 'Thiever',
        'settings': {
            'target': 'Farmer' if farmer else 'Man / Woman',
            'action': 'Pickpocket', 'banking': 'None', 'loadout': '',
            'food': food if carried else '', 'suicide': False,
        },
        'needs': [{'item': food, 'count': carried, 'carry': carried}] if carried else [],
        'food': food if carried else None,
        'travel': travel,
        'output': {'item': 'Coins', 'count': budget + SHOPPING_RESERVE},
        'funding': True,
    })
