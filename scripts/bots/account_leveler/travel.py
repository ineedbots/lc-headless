"""Ported from rs2b0t's src/bot/scripts/AccountLeveler/travel.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.traversal import wilderness_level_at

__all__ = ['leveler_travel_zones']

def leveler_travel_zones(destination=None, wilderness=False):
    return ['white-wolf-mountain'] + list((([] if wilderness and destination and wilderness_level_at(destination) > 0 else [
        {'min_x': 2944, 'max_x': 3391, 'min_z': 3520, 'max_z': 6399},
        {'min_x': 2944, 'max_x': 3391, 'min_z': 9920, 'max_z': 12799, 'level': 0},
    ])))
